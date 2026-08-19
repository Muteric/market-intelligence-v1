"""Simulation-only signal intelligence contracts.

This module contains scoring, instrument specifications, candidates, trailing stops,
and outcome recording. It deliberately has no broker or order-placement code.
"""
from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


class SimulationMode(str, Enum):
    AGGRESSIVE = "AGGRESSIVE"
    MODERATE = "MODERATE"
    SWING = "SWING"

    @classmethod
    def normalize(cls, value: str | "SimulationMode") -> "SimulationMode":
        if isinstance(value, cls):
            return value
        normalized = str(value).strip().upper().replace("/", "_")
        if normalized in {"SLOW", "SLOW_SWING", "SLOW/SWING"}:
            normalized = "SWING"
        return cls(normalized)


@dataclass(frozen=True)
class PipSpecification:
    """Broker-overridable simulation point specification for an instrument."""
    symbol: str
    pip_size: float
    point_size: float
    digits: int

    def __post_init__(self) -> None:
        if self.pip_size <= 0 or self.point_size <= 0:
            raise ValueError("pip_size and point_size must be positive")

    def price_delta(self, pips: float) -> float:
        return float(pips) * self.pip_size


# Defaults are explicit simulation specifications, not broker execution metadata.
# A future MT5 adapter must replace these with symbol_info.point/digits-derived values.
DEFAULT_PIP_SPECS: Dict[str, PipSpecification] = {
    "BTCUSD": PipSpecification("BTCUSD", pip_size=1.0, point_size=0.01, digits=2),
    "XAUUSD": PipSpecification("XAUUSD", pip_size=0.1, point_size=0.01, digits=2),
}

MODE_TARGET_PIPS = {
    SimulationMode.AGGRESSIVE: (10.0, 25.0),
    SimulationMode.MODERATE: (20.0, 50.0),
    SimulationMode.SWING: (100.0, 200.0),
}


@dataclass
class TradeCandidate:
    asset: str
    direction: str
    confidence: float
    mode: str
    entry: Optional[float]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    expected_move: Optional[float]
    risk_reward: Optional[float]
    reasons: List[str] = field(default_factory=list)
    supporting_timeframes: List[str] = field(default_factory=list)
    supporting_indicators: List[str] = field(default_factory=list)
    signal_score: float = 0.0
    accepted: bool = False
    rejection_reason: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class SignalScore:
    score: float
    direction: str
    components: Dict[str, float]
    confirmations: List[str]
    reasons: List[str]


def _finite(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def calculate_signal_score(
    direction: str,
    *,
    trend: Optional[str] = None,
    momentum: Optional[float] = None,
    mtf_alignment: Optional[float] = None,
    structure_direction: Optional[str] = None,
    pattern_direction: Optional[str] = None,
    volatility: Optional[str] = None,
    ohlcv_confidence: Optional[float] = None,
    spot_consensus: Optional[float] = None,
    provider_diversity: Optional[float] = None,
) -> SignalScore:
    """Score only evidence that is present and directionally relevant."""
    direction = str(direction).upper()
    components: Dict[str, float] = {}
    confirmations: List[str] = []
    reasons: List[str] = []

    def directional(name: str, value: Optional[str], weight: float) -> None:
        if value is None or str(value).upper() in {"NONE", "UNAVAILABLE", "NEUTRAL"}:
            return
        value_upper = str(value).upper()
        expected = "BULLISH" if direction == "BUY" else "BEARISH"
        if expected in value_upper:
            components[name] = weight
            confirmations.append(name)
            reasons.append(f"{name}: {value}")
        elif "BULLISH" in value_upper or "BEARISH" in value_upper:
            components[name] = -weight
            reasons.append(f"{name} conflicts: {value}")

    directional("trend", trend, 20.0)
    directional("market_structure", structure_direction, 15.0)
    directional("pattern", pattern_direction, 15.0)

    numeric = _finite(momentum)
    if numeric is not None:
        contribution = max(-1.0, min(1.0, numeric if abs(numeric) <= 1 else numeric / 100.0)) * 15.0
        contribution = contribution if direction == "BUY" else -contribution
        components["momentum"] = contribution
        if contribution > 0:
            confirmations.append("momentum")
        reasons.append(f"momentum: {numeric:.3f}")

    numeric = _finite(mtf_alignment)
    if numeric is not None:
        normalized = max(0.0, min(1.0, numeric if numeric <= 1 else numeric / 5.0))
        components["multi_timeframe"] = normalized * 15.0
        if normalized >= 0.6:
            confirmations.append("multi_timeframe")
        reasons.append(f"multi-timeframe alignment: {normalized:.0%}")

    for name, value, weight in (
        ("ohlcv_confidence", ohlcv_confidence, 10.0),
        ("spot_consensus", spot_consensus, 5.0),
        ("provider_diversity", provider_diversity, 5.0),
    ):
        numeric = _finite(value)
        if numeric is not None:
            normalized = max(0.0, min(1.0, numeric if numeric <= 1 else numeric / 100.0))
            components[name] = normalized * weight
            if normalized >= 0.6:
                confirmations.append(name)

    if volatility is not None and str(volatility).lower() not in {"high", "unavailable"}:
        components["volatility"] = 5.0
        reasons.append(f"volatility: {volatility}")

    score = max(0.0, min(100.0, 50.0 + sum(components.values()) - len([v for v in components.values() if v < 0]) * 5.0))
    return SignalScore(score, direction, components, confirmations, reasons)


def build_trade_candidate(
    asset: str,
    direction: str,
    entry: Optional[float],
    score: SignalScore,
    *,
    mode: SimulationMode = SimulationMode.MODERATE,
    spec: Optional[PipSpecification] = None,
    stop_loss_pips: float = 50.0,
    min_score: float = 65.0,
    min_confirmations: int = 3,
) -> TradeCandidate:
    mode = SimulationMode.normalize(mode)
    spec = spec or DEFAULT_PIP_SPECS.get(asset)
    entry_value = _finite(entry)
    accepted = direction in {"BUY", "SELL"} and entry_value is not None
    rejection: Optional[str] = None
    if not accepted:
        rejection = "direction or entry unavailable"
    elif score.score < min_score:
        accepted = False
        rejection = f"score below minimum ({score.score:.1f} < {min_score:.1f})"
    elif len(score.confirmations) < min_confirmations:
        accepted = False
        rejection = f"insufficient confirmations ({len(score.confirmations)} < {min_confirmations})"

    stop = target = expected = rr = None
    if accepted and spec is not None:
        low, high = MODE_TARGET_PIPS[mode]
        target_pips = (low + high) / 2.0
        stop_delta = spec.price_delta(stop_loss_pips)
        target_delta = spec.price_delta(target_pips)
        if direction == "BUY":
            stop, target = entry_value - stop_delta, entry_value + target_delta
        else:
            stop, target = entry_value + stop_delta, entry_value - target_delta
        expected = target_delta
        rr = target_pips / stop_loss_pips if stop_loss_pips > 0 else None

    return TradeCandidate(
        asset=asset, direction=direction, confidence=score.score / 100.0,
        mode=mode.value, entry=entry_value, stop_loss=stop, take_profit=target,
        expected_move=expected, risk_reward=rr, reasons=score.reasons,
        supporting_timeframes=["5M", "15M", "1H", "4H", "Daily"] if "multi_timeframe" in score.confirmations else [],
        supporting_indicators=score.confirmations, signal_score=score.score,
        accepted=accepted, rejection_reason=rejection,
    )


class TrailingStopManager:
    def __init__(self, activation_pips: float = 20.0, step_pips: float = 10.0):
        self.activation_pips = float(activation_pips)
        self.step_pips = float(step_pips)

    def initial_stop(self, entry: float, direction: str, spec: PipSpecification, stop_loss_pips: float = 50.0) -> float:
        delta = spec.price_delta(stop_loss_pips)
        return float(entry) - delta if str(direction).upper() == "BUY" else float(entry) + delta

    def update(self, entry: float, current: float, existing_stop: float, direction: str, spec: PipSpecification) -> float:
        favorable = (float(current) - float(entry)) if str(direction).upper() == "BUY" else (float(entry) - float(current))
        favorable_pips = favorable / spec.pip_size
        if favorable_pips < self.activation_pips:
            return float(existing_stop)
        steps = math.floor((favorable_pips - self.activation_pips) / self.step_pips) + 1
        lock_pips = (steps * self.step_pips)
        proposed = float(entry) + spec.price_delta(lock_pips) if str(direction).upper() == "BUY" else float(entry) - spec.price_delta(lock_pips)
        return max(float(existing_stop), proposed) if str(direction).upper() == "BUY" else min(float(existing_stop), proposed)


class SignalOutcomeTracker:
    """Records candidates and resolves outcomes; it never places orders."""
    TARGETS = (10.0, 20.0, 50.0, 100.0, 200.0)

    def __init__(self, path: str = "data/signal_outcomes.json"):
        self.path = Path(path)
        self.records: List[Dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        try:
            if self.path.exists():
                loaded = json.loads(self.path.read_text(encoding="utf-8"))
                self.records = loaded if isinstance(loaded, list) else []
        except (OSError, ValueError):
            self.records = []

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.records, indent=2), encoding="utf-8")

    def record(self, candidate: TradeCandidate, conditions: Optional[Dict[str, Any]] = None) -> str:
        record_id = f"candidate-{len(self.records) + 1}"
        payload = asdict(candidate)
        payload.update({"id": record_id, "conditions": conditions or {}, "resolved": False})
        self.records.append(payload)
        self._save()
        return record_id

    def resolve(self, record_id: str, prices: Iterable[float], spec: PipSpecification) -> Optional[Dict[str, Any]]:
        record = next((item for item in self.records if item.get("id") == record_id), None)
        if record is None or record.get("resolved"):
            return record
        entry = _finite(record.get("entry"))
        if entry is None:
            return record
        direction = record.get("direction")
        excursions = [((float(price) - entry) if direction == "BUY" else (entry - float(price))) / spec.pip_size for price in prices]
        record["targets_reached"] = {str(target): any(move >= target for move in excursions) for target in self.TARGETS}
        stop_pips = abs(entry - float(record.get("stop_loss"))) / spec.pip_size if record.get("stop_loss") is not None else None
        record["initial_stop_hit"] = stop_pips is not None and any(move <= -stop_pips for move in excursions)
        record["resolved"] = True
        self._save()
        return record

    def learning_status(self) -> Dict[str, Any]:
        resolved = [item for item in self.records if item.get("resolved")]
        wins = [item for item in resolved if item.get("targets_reached", {}).get("20.0") and not item.get("initial_stop_hit")]
        return {
            "candidates_evaluated": len(self.records),
            "outcomes_resolved": len(resolved),
            "win_rate": len(wins) / len(resolved) if resolved else None,
            "enough_observations_for_adaptive_weighting": len(resolved) >= 30,
        }
"""Persistent paper-trading audit records and period reporting.

The JSONL audit is append-only and is deliberately separate from runtime
SQLite state.  It is suitable for PAPER now and MT5_DEMO/MT5_LIVE later.
"""
from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, fields
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

TRADE_SCHEMA_VERSION = 1
REPORT_SCHEMA_VERSION = 1
VALID_SOURCES = {"PAPER", "MT5_DEMO", "MT5_LIVE"}
VALID_DIRECTIONS = {"BUY", "SELL"}
VALID_ASSETS = {"BTCUSD", "XAUUSD", "XAGUSD"}


def _utc(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        result = value
    else:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return (result if result.tzinfo else result.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)


def _json_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {str(k): _json_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(v) for v in value]
    return value


@dataclass
class TradeOutcomeRecord:
    trade_id: str
    source: str
    asset: str
    direction: str
    mode: Optional[str] = None
    broker_symbol: Optional[str] = None
    candidate_id: Optional[str] = None
    signal_id: Optional[str] = None
    entry_price: Optional[float] = None
    entry_time_utc: Optional[str] = None
    initial_stop_loss: Optional[float] = None
    final_stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    exit_price: Optional[float] = None
    exit_time_utc: Optional[str] = None
    exit_reason: Optional[str] = None
    allocated_capital: Optional[float] = None
    margin_used: Optional[float] = None
    notional_value: Optional[float] = None
    leverage: Optional[float] = None
    pip_size: Optional[float] = None
    point_size: Optional[float] = None
    risk_pips: Optional[float] = None
    target_pips: Optional[float] = None
    realized_pips: Optional[float] = None
    realized_pnl: Optional[float] = None
    fees: Optional[float] = None
    commission: Optional[float] = None
    swap: Optional[float] = None
    net_pnl: Optional[float] = None
    roi_percent: Optional[float] = None
    R_multiple: Optional[float] = None
    trade_duration_seconds: Optional[float] = None
    highest_favorable_price: Optional[float] = None
    lowest_adverse_price: Optional[float] = None
    maximum_favorable_excursion: Optional[float] = None
    maximum_adverse_excursion: Optional[float] = None
    breakeven_activated: Optional[bool] = None
    trailing_stop_activated: Optional[bool] = None
    number_of_trailing_moves: Optional[int] = None
    signal_score: Optional[float] = None
    confidence: Optional[float] = None
    market_regime: Optional[str] = None
    trend: Optional[str] = None
    momentum: Optional[float] = None
    volatility: Optional[str] = None
    mtf_alignment_score: Optional[float] = None
    supporting_timeframes: Optional[list[str]] = None
    conflicting_timeframes: Optional[list[str]] = None
    chart_patterns: Optional[list[Any]] = None
    market_structure: Optional[Any] = None
    data_quality_score: Optional[float] = None
    provider_count: Optional[int] = None
    ohlcv_provider: Optional[str] = None
    entry_reason: Optional[str] = None
    exit_reason_code: Optional[str] = None
    winning_trade: Optional[bool] = None
    losing_trade: Optional[bool] = None
    breakeven_trade: Optional[bool] = None
    created_at_utc: Optional[str] = None
    updated_at_utc: Optional[str] = None
    trade_schema_version: int = TRADE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.trade_id:
            raise ValueError("trade_id is required")
        if self.source not in VALID_SOURCES:
            raise ValueError("source must be PAPER, MT5_DEMO, or MT5_LIVE")
        if self.asset not in VALID_ASSETS:
            raise ValueError("unsupported asset")
        if self.direction not in VALID_DIRECTIONS:
            raise ValueError("direction must be BUY or SELL")
        now = datetime.now(timezone.utc).isoformat()
        self.created_at_utc = self.created_at_utc or now
        self.updated_at_utc = self.updated_at_utc or now

    def to_dict(self) -> dict[str, Any]:
        return _json_value(asdict(self))


class TradeHistoryStore:
    """Idempotent append-only JSONL store for finalized outcomes."""
    def __init__(self, root: str | Path = "data"):
        self.root = Path(root)
        self.directory = self.root / "trade_history"

    def _path(self, year: int) -> Path:
        return self.directory / f"trades_{year}.jsonl"

    def _existing_ids(self) -> set[str]:
        result: set[str] = set()
        for path in self.directory.glob("trades_*.jsonl"):
            for line in path.read_text(encoding="utf-8").splitlines():
                try:
                    item = json.loads(line)
                    if item.get("trade_id"):
                        result.add(item["trade_id"])
                except json.JSONDecodeError:
                    continue
        return result

    def append(self, record: TradeOutcomeRecord) -> bool:
        entry = _utc(record.exit_time_utc or record.entry_time_utc or record.created_at_utc)
        if entry is None:
            raise ValueError("trade requires a valid timestamp")
        if record.trade_id in self._existing_ids():
            return False
        self.directory.mkdir(parents=True, exist_ok=True)
        with self._path(entry.year).open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record.to_dict(), separators=(",", ":"), allow_nan=False) + "\n")
        return True

    def records(self, source: Optional[str] = None) -> list[dict[str, Any]]:
        result = []
        for path in sorted(self.directory.glob("trades_*.jsonl")):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    item = json.loads(line)
                    if source is None or item.get("source") == source:
                        result.append(item)
        return result


class PerformanceAggregator:
    def __init__(self, records: Iterable[dict[str, Any]]):
        self.records = list(records)

    def summarize(self) -> dict[str, Any]:
        pnl = [float(r.get("net_pnl", r.get("realized_pnl", 0)) or 0) for r in self.records]
        wins = [x for x in pnl if x > 0]
        losses = [x for x in pnl if x < 0]
        rs = [float(r["R_multiple"]) for r in self.records if r.get("R_multiple") is not None]
        gross_loss = abs(sum(losses))
        return {
            "trades": len(pnl), "wins": len(wins), "losses": len(losses),
            "breakevens": len(pnl) - len(wins) - len(losses),
            "win_rate": len(wins) / len(pnl) if pnl else None,
            "realized_pnl": sum(pnl),
            "profit_factor": sum(wins) / gross_loss if gross_loss else None,
            "average_winner": sum(wins) / len(wins) if wins else None,
            "average_loser": sum(losses) / len(losses) if losses else None,
            "average_R": sum(rs) / len(rs) if rs else None,
            "largest_win": max(wins) if wins else None,
            "largest_loss": min(losses) if losses else None,
            "by_asset": self._group("asset"), "by_mode": self._group("mode"),
            "by_direction": self._group("direction"), "by_regime": self._group("market_regime"),
        }

    def _group(self, key: str) -> dict[str, Any]:
        groups = {}
        for value in sorted({r.get(key) for r in self.records} - {None}):
            groups[value] = PerformanceAggregator(r for r in self.records if r.get(key) == value).summarize_basic()
        return groups

    def summarize_basic(self) -> dict[str, Any]:
        pnl = [float(r.get("net_pnl", r.get("realized_pnl", 0)) or 0) for r in self.records]
        wins = sum(1 for x in pnl if x > 0)
        return {"trades": len(pnl), "wins": wins, "losses": sum(1 for x in pnl if x < 0), "realized_pnl": sum(pnl), "win_rate": wins / len(pnl) if pnl else None}


class TradingReportService:
    def __init__(self, store: TradeHistoryStore, report_root: str | Path = "data/reports"):
        self.store, self.report_root = store, Path(report_root)

    def _period(self, kind: str, year: int, month: Optional[int] = None, week: Optional[int] = None) -> tuple[datetime, datetime, Path]:
        if kind == "daily":
            start = datetime(year, month, week, tzinfo=timezone.utc); end = start + timedelta(days=1); path = self.report_root / kind / str(year) / f"{start:%Y-%m-%d}.json"
        elif kind == "weekly":
            start = datetime.fromisocalendar(year, week, 1).replace(tzinfo=timezone.utc); end = start + timedelta(days=7); path = self.report_root / kind / str(year) / f"{year}-W{week:02d}.json"
        elif kind == "monthly":
            start = datetime(year, month, 1, tzinfo=timezone.utc); end = datetime(year + (month == 12), 1 if month == 12 else month + 1, 1, tzinfo=timezone.utc); path = self.report_root / kind / str(year) / f"{year}-{month:02d}.json"
        else:
            start = datetime(year, 1, 1, tzinfo=timezone.utc); end = datetime(year + 1, 1, 1, tzinfo=timezone.utc); path = self.report_root / kind / f"{year}.json"
        return start, end, path

    def generate(self, kind: str, year: int, month: Optional[int] = None, week: Optional[int] = None, force: bool = False) -> dict[str, Any]:
        start, end, path = self._period(kind, year, month, week)
        if path.exists() and not force:
            return json.loads(path.read_text(encoding="utf-8"))
        records = [r for r in self.store.records() if (t := _utc(r.get("exit_time_utc"))) and start <= t < end]
        metrics = PerformanceAggregator(records).summarize()
        report = {"report_schema_version": REPORT_SCHEMA_VERSION, "period": kind, "start_utc": start.isoformat(), "end_utc": end.isoformat(), "scope": "PAPER/DEMO/LIVE", "metrics": metrics, "trade_ids": [r["trade_id"] for r in records], "telegram_sent": False, "telegram_attempts": 0}
        path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(_json_value(report), indent=2, allow_nan=False), encoding="utf-8")
        return report

    def reconcile(self, report: dict[str, Any]) -> dict[str, Any]:
        records = [r for r in self.store.records() if r.get("trade_id") in report.get("trade_ids", [])]
        raw = PerformanceAggregator(records).summarize()["realized_pnl"]
        return {"ok": abs(raw - report["metrics"]["realized_pnl"]) < 1e-9, "raw_pnl": raw, "reported_pnl": report["metrics"]["realized_pnl"]}

    def lifetime(self) -> dict[str, Any]:
        return PerformanceAggregator(self.store.records()).summarize()

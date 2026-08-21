from datetime import datetime, timezone, timedelta

from signal_intelligence import (
    SimulationMode, TrailingStopManager,
    build_trade_candidate, calculate_signal_score, SignalOutcomeTracker, infer_candidate_direction, select_simulation_mode,
    DEFAULT_PIP_SPECS,
)
from technical_indicators import TechnicalIndicators
from asset_manager import AssetManager
from configuration_manager import AssetConfig, PortfolioConfig, TradingConfig
from trade_execution_simulator import TradeExecutionSimulator
from mt5_bridge import PaperExecutionAdapter


def test_unavailable_indicator_is_none_not_zero():
    indicators = TechnicalIndicators()
    indicators.update_price_data("BTCUSD", 100.0, 1.0, 101.0, 99.0)
    assert indicators._calculate_rsi("BTCUSD").rsi is None
    assert indicators._calculate_atr("BTCUSD").atr is None


def test_signal_score_ignores_missing_evidence_and_is_bounded():
    score = calculate_signal_score("BUY", trend="bullish", momentum=None, mtf_alignment=None)
    assert 0 <= score.score <= 100
    assert "momentum" not in score.components


def test_candidate_modes_use_instrument_spec_and_confirmation_gate():
    score = calculate_signal_score("BUY", trend="bullish", structure_direction="bullish", pattern_direction="bullish", mtf_alignment=1.0)
    candidate = build_trade_candidate("XAUUSD", "BUY", 2000.0, score, mode=SimulationMode.SWING, min_confirmations=2)
    assert candidate.accepted
    assert candidate.take_profit > candidate.entry
    assert candidate.stop_loss < candidate.entry


def test_trailing_stop_only_moves_forward():
    manager = TrailingStopManager()
    spec = DEFAULT_PIP_SPECS["XAUUSD"]
    initial = manager.initial_stop(2000.0, "BUY", spec)
    moved = manager.update(2000.0, 2000.0 + 25 * spec.pip_size, initial, "BUY", spec)
    assert moved > initial
    assert manager.update(2000.0, 2000.0 + 15 * spec.pip_size, moved, "BUY", spec) == moved


def test_outcome_tracker_records_and_resolves(tmp_path):
    score = calculate_signal_score("BUY", trend="bullish", structure_direction="bullish", mtf_alignment=1.0)
    candidate = build_trade_candidate("BTCUSD", "BUY", 100.0, score, min_confirmations=2)
    tracker = SignalOutcomeTracker(str(tmp_path / "outcomes.json"))
    record_id = tracker.record(candidate, {"regime": "TRENDING"})
    tracker.resolve(record_id, [100.0, 110.0, 120.0], DEFAULT_PIP_SPECS["BTCUSD"])
    assert tracker.learning_status()["candidates_evaluated"] == 1
    assert tracker.learning_status()["outcomes_resolved"] == 1
import pytest

@pytest.mark.parametrize("asset", ["BTCUSD", "XAUUSD"])
def test_valid_evidence_produces_candidate_even_when_final_decision_is_hold(asset):
    direction = infer_candidate_direction("bullish", "bullish", "bullish", 0.8)
    score = calculate_signal_score(direction, trend="bullish", structure_direction="bullish", pattern_direction="bullish", momentum=0.8, mtf_alignment=0.8, ohlcv_confidence=1.0, spot_consensus=1.0, provider_diversity=1.0)
    candidate = build_trade_candidate(asset, direction, 100.0, score, min_score=65, min_confirmations=3)
    assert candidate.status == "BUY"
    assert candidate.entry == 100.0
    assert candidate.accepted


def test_weak_and_conflicting_setups_are_rejected_or_watched():
    weak = calculate_signal_score("WATCH", trend="neutral", momentum=0.0, mtf_alignment=0.2)
    weak_candidate = build_trade_candidate("BTCUSD", "WATCH", 100.0, weak, min_score=90, min_confirmations=4)
    assert weak_candidate.status in {"WATCH", "NO-TRADE"}
    conflicting = calculate_signal_score("BUY", trend="bullish", structure_direction="bearish", pattern_direction="bearish", mtf_alignment=0.8)
    conflict_candidate = build_trade_candidate("XAUUSD", "BUY", 100.0, conflicting, structure_confirmed=False)
    assert "conflicting market structure" in conflict_candidate.rejection_reason


def test_candidate_lifecycle_records_trailing_and_outcome(tmp_path):
    score = calculate_signal_score("BUY", trend="bullish", structure_direction="bullish", mtf_alignment=1.0)
    candidate = build_trade_candidate("BTCUSD", "BUY", 100.0, score, min_confirmations=2)
    tracker = SignalOutcomeTracker(str(tmp_path / "lifecycle.json"))
    record_id = tracker.record(candidate, {"market_regime": "TRENDING", "mtf_alignment": "5/5"})
    assert tracker.open_candidate(record_id)["lifecycle_state"] == "OPEN"
    tracker.update_trailing(record_id, 125.0, DEFAULT_PIP_SPECS["BTCUSD"])
    closed = tracker.close_candidate(record_id, 130.0, DEFAULT_PIP_SPECS["BTCUSD"], "take profit")
    assert closed["lifecycle_state"] == "CLOSED"
    assert closed["outcome"] == "WIN"
def test_minimum_rr_rejects_candidate_with_machine_reason():
    score = calculate_signal_score("BUY", trend="bullish", structure_direction="bullish", mtf_alignment=1.0)
    candidate = build_trade_candidate("BTCUSD", "BUY", 100.0, score, mode=SimulationMode.MODERATE, min_confirmations=2, minimum_risk_reward=1.5, stop_loss_pips=50.0)
    assert not candidate.accepted
    assert candidate.candidate_status == "REJECTED"
    assert candidate.risk_validation == "FAIL"
    assert candidate.reason_code == "RR_BELOW_MINIMUM"


def test_dynamic_modes_and_no_trade_selection():
    aggressive_score = calculate_signal_score("BUY", trend="bullish", momentum=1.0, mtf_alignment=0.6, ohlcv_confidence=1.0)
    assert select_simulation_mode(score=aggressive_score, adx=22, mtf_alignment=0.6) in {SimulationMode.AGGRESSIVE, SimulationMode.MODERATE}
    swing_score = calculate_signal_score("BUY", trend="bullish", structure_direction="bullish", pattern_direction="bullish", mtf_alignment=1.0, momentum=0.8)
    assert select_simulation_mode(score=swing_score, adx=35, mtf_alignment=1.0) == SimulationMode.SWING
    neutral_score = calculate_signal_score("WATCH", trend="neutral", mtf_alignment=0.2)
    assert select_simulation_mode(score=neutral_score, mtf_alignment=0.2) == SimulationMode.NONE


def test_trailing_moves_to_breakeven_then_profits():
    manager = TrailingStopManager()
    spec = DEFAULT_PIP_SPECS["BTCUSD"]
    initial = manager.initial_stop(100.0, "BUY", spec)
    at_activation = manager.update(100.0, 120.0, initial, "BUY", spec)
    at_next = manager.update(100.0, 130.0, at_activation, "BUY", spec)
    assert at_activation == 100.0
    assert at_next == 110.0
    assert manager.update(100.0, 105.0, at_next, "BUY", spec) == at_next


def test_learning_threshold_is_configurable(tmp_path):
    tracker = SignalOutcomeTracker(str(tmp_path / "learning.json"), minimum_outcomes=2)
    assert tracker.learning_status()["adaptive_weighting_enabled"] is False
    tracker.records = [{"resolved": True, "outcome": "WIN"}, {"resolved": True, "outcome": "LOSS"}]
    assert tracker.learning_status()["adaptive_weighting_enabled"] is True
def _ready_paper_candidate():
    score = calculate_signal_score("BUY", trend="bullish", structure_direction="bullish", pattern_direction="bullish", momentum=0.8, mtf_alignment=1.0, ohlcv_confidence=1.0)
    return build_trade_candidate("BTCUSD", "BUY", 100.0, score, mode=SimulationMode.SWING, target_pips=120, min_confirmations=2, minimum_risk_reward=1.5)


def test_paper_position_opens_and_resolves_tp(tmp_path):
    candidate = _ready_paper_candidate()
    tracker = SignalOutcomeTracker(str(tmp_path / "positions.json"))
    record_id = tracker.record(candidate)
    tracker.open_candidate(record_id)
    open_record = tracker.records[0]
    assert open_record["lifecycle_state"] == "OPEN"
    closed = tracker.update_open_positions("BTCUSD", 220.0, DEFAULT_PIP_SPECS["BTCUSD"])
    assert closed[0]["exit_reason"] == "TAKE_PROFIT"
    assert closed[0]["outcome"] == "WIN"
    assert closed[0]["pips_realized"] == 120.0


def test_paper_adapter_uses_existing_asset_sizing_and_limits():
    assets = {"BTCUSD": AssetConfig("BTCUSD", allocation_percentage=0.5), "XAUUSD": AssetConfig("XAUUSD", allocation_percentage=0.5)}
    manager = AssetManager(100.0, assets, 0.5, 0.25, 3)
    simulator = TradeExecutionSimulator(manager, PortfolioConfig(), TradingConfig())
    paper = PaperExecutionAdapter(simulator)
    trade = paper.open_candidate(_ready_paper_candidate())
    assert trade is not None
    assert trade.status == "OPEN"
    assert trade.capital_used == 25.0
    assert trade.notional_value == 25.0 * 400.0

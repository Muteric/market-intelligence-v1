from datetime import datetime, timedelta, timezone

from configuration_manager import SystemConfig
from market_data_aggregator import MarketDataAggregator, normalize_market_timestamp
from signal_intelligence import SimulationMode, build_trade_candidate, calculate_signal_score, DEFAULT_PIP_SPECS


def candle(timestamp):
    return {"timestamp": timestamp, "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.5, "volume": 10.0}


def test_timestamp_normalization_handles_utc_epoch_and_milliseconds():
    expected = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)
    assert normalize_market_timestamp(expected.isoformat()) == expected
    assert normalize_market_timestamp(expected.replace(tzinfo=None)) == expected
    assert normalize_market_timestamp(int(expected.timestamp())) == expected
    assert normalize_market_timestamp(int(expected.timestamp() * 1000)) == expected


def test_future_candle_outside_clock_skew_is_rejected():
    aggregator = MarketDataAggregator(system_config=SystemConfig(max_future_timestamp_seconds=120))
    future = datetime.now(timezone.utc) + timedelta(hours=10)
    assert aggregator._normalize_ohlcv([candle(future.isoformat())], "Twelve Data") is None


def test_future_candle_inside_clock_skew_is_allowed():
    aggregator = MarketDataAggregator(system_config=SystemConfig(max_future_timestamp_seconds=120))
    future = datetime.now(timezone.utc) + timedelta(seconds=30)
    assert aggregator._normalize_ohlcv([candle(future.isoformat())], "Twelve Data")


def test_each_mode_can_pass_minimum_rr_with_mode_aware_risk():
    score = calculate_signal_score("BUY", trend="bullish", structure_direction="bullish", pattern_direction="bullish", mtf_alignment=1.0, momentum=0.8, ohlcv_confidence=1.0)
    for mode in (SimulationMode.AGGRESSIVE, SimulationMode.MODERATE, SimulationMode.SWING):
        candidate = build_trade_candidate("BTCUSD", "BUY", 100000.0, score, mode=mode, min_confirmations=2, minimum_risk_reward=1.5)
        assert candidate.accepted, (mode, candidate.rejection_reason)
        assert candidate.risk_reward >= 1.5
        assert candidate.entry > candidate.stop_loss
        assert candidate.take_profit > candidate.entry


def test_explicit_legacy_wide_stop_still_rejects_bad_rr():
    score = calculate_signal_score("BUY", trend="bullish", structure_direction="bullish", mtf_alignment=1.0)
    candidate = build_trade_candidate("BTCUSD", "BUY", 100000.0, score, mode=SimulationMode.MODERATE, stop_loss_pips=50, minimum_risk_reward=1.5, min_confirmations=2)
    assert not candidate.accepted
    assert candidate.reason_code == "RR_BELOW_MINIMUM"
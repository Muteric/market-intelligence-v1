"""Deterministic MT5 adapter and chart-pattern tests."""

from datetime import datetime, timezone
from types import SimpleNamespace

from chart_pattern_detector import ChartPatternDetector
from mt5_market_data import MT5MarketData
from multi_timeframe_analyzer import MultiTimeframeAnalyzer


def _candle(open_, high, low, close, index=0):
    return {
        "timestamp": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "open": open_, "high": high, "low": low, "close": close,
        "volume": 10 + index,
    }


def test_mt5_unavailable_is_safe():
    fake = SimpleNamespace(initialize=lambda: False)
    adapter = MT5MarketData(mt5_module=fake)
    assert adapter.available is False
    assert adapter.current_quote("XAUUSD") is None
    assert adapter.historical_candles("XAUUSD", "M5") == []


def test_mt5_quote_and_candles_are_normalized():
    fake = SimpleNamespace(
        TIMEFRAME_M5=5,
        initialize=lambda: True,
        symbol_select=lambda symbol, selected: symbol == "XAUUSDm",
        symbol_info_tick=lambda symbol: SimpleNamespace(bid=100.0, ask=101.0, last=100.5, time=1767225600, volume=3),
        copy_rates_from_pos=lambda symbol, timeframe, start, count: [
            {"time": 1767225600, "open": 100, "high": 102, "low": 99, "close": 101, "tick_volume": 20}
        ],
    )
    adapter = MT5MarketData({"XAUUSD": "XAUUSDm"}, fake)
    quote = adapter.current_quote("XAUUSD")
    candles = adapter.historical_candles("XAUUSD", "M5", 10)
    assert adapter.available
    assert quote.price == 100.5
    assert quote.bid == 100.0 and quote.ask == 101.0
    assert candles[0]["close"] == 101.0


def test_bullish_engulfing_and_bos_are_evidence():
    candles = [
        _candle(100, 101, 98, 99),
        _candle(98, 99, 95, 96),
        _candle(105, 106, 94, 96),
        _candle(95, 110, 94, 108),
    ]
    detector = ChartPatternDetector()
    patterns = detector.detect(candles, "15M")
    names = {pattern.pattern_name for pattern in patterns}
    assert "Bullish Engulfing" in names
    assert any(pattern.pattern_name == "Break of Structure" for pattern in patterns)


def test_timeframe_analyzer_exposes_pattern_evidence():
    analyzer = MultiTimeframeAnalyzer()
    candles = [_candle(100 + i, 101 + i, 99 + i, 100.5 + i, i) for i in range(8)]
    analyzer.set_timeframe_ohlcv("XAUUSD", "5M", candles)
    result = analyzer.analyze_multi_timeframe("XAUUSD")
    assert "5M" in result.patterns
    assert "5M" in result.market_structure

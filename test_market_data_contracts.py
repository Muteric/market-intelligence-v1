from datetime import datetime, timezone

from configuration_manager import PortfolioConfig, SystemConfig
from market_data_aggregator import MarketDataAggregator, MarketDataPoint
from profit_calculator import ProfitCalculator
from asset_manager import Trade


def test_ohlcv_normalization_handles_seconds_milliseconds_and_rejects_invalid():
    aggregator = MarketDataAggregator(system_config=SystemConfig())
    rows = [
        {"timestamp": 1700000000, "open": "10", "high": "12", "low": "9", "close": "11", "volume": "4"},
        {"timestamp": 1700000000000, "open": 10, "high": 12, "low": 9, "close": 11, "volume": 4},
        {"timestamp": "bad", "open": 1, "high": 0, "low": 1, "close": 1, "volume": 1},
    ]
    candles = aggregator._normalize_ohlcv(rows, "fixture")
    assert candles is not None
    assert len(candles) == 1
    assert candles[0]["volume"] == 4.0


def test_spot_provider_is_not_classified_as_ohlcv():
    point = MarketDataPoint(
        symbol="XAUUSD", price=4100, bid=4099, ask=4101, spread=2,
        volume=0, timestamp=datetime.now(timezone.utc), provider="GoldAPI", source="goldapi",
    )
    assert point.data_kind == "spot_only"


def test_twelvedata_symbol_mapping_is_provider_specific():
    aggregator = MarketDataAggregator(system_config=SystemConfig())
    assert aggregator._map_symbol_to_twelvedata("BTCUSD") == "BTC/USD"
    assert aggregator._map_symbol_to_twelvedata("XAUUSD") == "XAU/USD"


def test_empty_loss_set_has_finite_profit_factor():
    calculator = ProfitCalculator(PortfolioConfig())
    trade = Trade(asset="BTCUSD", entry_price=100, position_size=1, leverage=1, status="CLOSED", realized_pnl=5)
    metrics = calculator.calculate_portfolio_pnl([trade])
    assert metrics["profit_factor"] == 0.0

import pytest


def test_string_numeric_configuration_is_normalized():
    config = SystemConfig(
        xau_max_stale_seconds="60",
        max_price_deviation_percent="1.5",
        min_valid_providers="1",
        notification_dedupe_seconds="900",
    )
    assert config.xau_max_stale_seconds == 60
    assert isinstance(config.xau_max_stale_seconds, int)
    assert config.max_price_deviation_percent == 1.5
    assert config.min_valid_providers == 1


def test_invalid_numeric_configuration_has_clear_error():
    with pytest.raises(ValueError, match="MIN_CANDLES|xau_max_stale_seconds"):
        SystemConfig(xau_max_stale_seconds="not-a-number")


def test_numeric_string_provider_timestamp_is_normalized():
    aggregator = MarketDataAggregator(system_config=SystemConfig())
    point = aggregator._normalized_quote("XAUUSD", 4100, "fixture", "fixture", timestamp="1700000000")
    assert point.timestamp.tzinfo is not None
    assert point.timestamp.year == 2023


def test_runtime_configuration_updates_are_coerced_before_comparison(tmp_path):
    from configuration_manager import ConfigurationManager

    manager = ConfigurationManager(str(tmp_path / "config.json"))
    manager.update_config({
        "system": {
            "xau_max_stale_seconds": "60",
            "max_price_deviation_percent": "1.5",
        }
    })
    system = manager.get_system_config()
    assert system.xau_max_stale_seconds == 60
    assert isinstance(system.xau_max_stale_seconds, int)
    assert system.max_price_deviation_percent == 1.5

def test_market_data_numeric_boundaries_accept_string_inputs():
    from types import SimpleNamespace

    aggregator = MarketDataAggregator(system_config=SimpleNamespace(
        goldapi_min_interval_seconds="300",
        xau_max_stale_seconds="60",
        max_price_deviation_percent="1.5",
    ))
    assert aggregator._numeric_config(aggregator.system_config, "goldapi_min_interval_seconds", 300, int) == 300
    assert aggregator._numeric_config(aggregator.system_config, "xau_max_stale_seconds", 60, int) == 60
    assert aggregator._numeric_config(aggregator.system_config, "max_price_deviation_percent", 1.0, float) == 1.5

    candles = aggregator._normalize_ohlcv([{
        "timestamp": "1700000000000",
        "open": "10",
        "high": "12",
        "low": "9",
        "close": "11",
        "volume": "4",
    }], "fixture")
    assert candles is not None
    assert candles[0]["timestamp"].year == 2023
    assert candles[0]["close"] == 11.0


def test_market_data_numeric_configuration_rejects_invalid_strings():
    from types import SimpleNamespace
    import pytest

    aggregator = MarketDataAggregator(system_config=SimpleNamespace(
        max_price_deviation_percent="not-a-number",
    ))
    with pytest.raises(ValueError, match="max_price_deviation_percent"):
        aggregator._numeric_config(
            aggregator.system_config, "max_price_deviation_percent", 1.0, float
        )

def test_previous_price_string_does_not_reach_string_integer_comparison():
    from types import SimpleNamespace

    now = datetime.now(timezone.utc)
    aggregator = MarketDataAggregator(system_config=SimpleNamespace(
        price_consensus_method="median",
        max_price_deviation_percent=1.0,
    ))
    point = MarketDataPoint(
        symbol="BTCUSD",
        price=110.0,
        bid=109.0,
        ask=111.0,
        spread=2.0,
        volume=1.0,
        timestamp=now,
        provider="Twelve Data",
        source="twelvedata",
        previous_price="100.0",
    )
    result = aggregator._validate_and_consensus("BTCUSD", {"twelvedata": point})
    assert result.previous_price == 100.0

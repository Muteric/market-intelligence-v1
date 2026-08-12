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

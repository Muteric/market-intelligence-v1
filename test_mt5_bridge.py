from types import SimpleNamespace
from unittest.mock import Mock
from datetime import datetime, timezone

from mt5_bridge import MT5Connection, MT5MarketData, MT5PositionReader, MT5ExecutionAdapter, MT5SymbolMapper


def fake_mt5():
    mt5 = Mock()
    mt5.initialize.return_value = True
    mt5.symbol_select.return_value = True
    mt5.symbol_info.return_value = SimpleNamespace(point=0.01, digits=2, volume_min=0.01, volume_step=0.01, volume_max=10, trade_mode=1)
    mt5.symbol_info_tick.return_value = SimpleNamespace(bid="100.0", ask="100.5", last="100.2", volume="3", time=1700000000)
    mt5.TIMEFRAME_M5 = 5
    mt5.copy_rates_from_pos.return_value = [{"time": 1700000000, "open": "99", "high": "101", "low": "98", "close": "100", "tick_volume": "12"}]
    mt5.positions_get.return_value = []
    return mt5


def test_disabled_mt5_does_not_import_or_connect():
    connection = MT5Connection(enabled=False, module=Mock())
    assert not connection.connect()
    assert connection.last_error == "MT5 disabled"


def test_tick_and_ohlcv_are_normalized():
    module = fake_mt5()
    connection = MT5Connection(enabled=True, module=module)
    assert connection.connect()
    market = MT5MarketData(connection, MT5SymbolMapper({"BTCUSD": "BTCUSDm", "XAUUSD": "GOLD"}))
    tick = market.get_tick("BTCUSD")
    bars = market.get_ohlcv("BTCUSD", "M5", 100)
    assert tick["broker_symbol"] == "BTCUSDm"
    assert tick["spread"] == 0.5
    assert bars[0]["close"] == 100.0
    assert bars[0]["timestamp"].tzinfo == timezone.utc


def test_read_only_execution_is_refused():
    adapter = MT5ExecutionAdapter(MT5Connection(enabled=False, mode="READ_ONLY"))
    try:
        adapter.open_position("BTCUSD", "BUY")
    except RuntimeError as exc:
        assert "READ_ONLY" in str(exc)
    else:
        assert False
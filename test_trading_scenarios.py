"""Deterministic tests for portfolio allocation and simulated trade lifecycle."""

from datetime import datetime, timezone

from asset_manager import AssetManager, PositionDirection, Trade, TradeStatus
from configuration_manager import PortfolioConfig, TradingConfig, SystemConfig
from market_analyzer import MarketAnalysis
from signal_engine import SignalEngine
from trade_storage import TradeStorage


def _analysis(price: float) -> MarketAnalysis:
    return MarketAnalysis(
        symbol="BTCUSD",
        timestamp=datetime.now(timezone.utc),
        current_price=price,
        previous_price=price,
        price_change=0.0,
        price_change_percent=0.0,
        trend_direction="neutral",
        momentum_score=0.0,
        sentiment_score=0.0,
        volatility_score="medium",
        confidence_score=0.5,
        market_pressure=0.0,
        strength_score=0.0,
        trend_quality="Neutral",
        market_phase="Neutral",
        reasoning=["Deterministic scenario fixture"],
    )


def _engine():
    portfolio = PortfolioConfig()
    assets = AssetManager(portfolio.initial_balance)
    return assets, SignalEngine(assets, TradingConfig(), portfolio)


def test_portfolio_capital_is_allocated_per_asset():
    assets, _ = _engine()
    assert assets.get_asset_state("BTCUSD").balance == 50.0
    assert assets.get_asset_state("XAUUSD").balance == 50.0
    assert sum(asset.balance for asset in assets.get_all_assets().values()) == 100.0


def test_four_same_direction_signals_use_fifo_replacement():
    assets, engine = _engine()
    for price in (100.0, 101.0, 102.0, 103.0):
        engine.generate_signal("BTCUSD", _analysis(price), decision_override="BUY")

    state = assets.get_asset_state("BTCUSD")
    assert len(state.open_positions) == 3
    assert len(state.closed_trades) == 1
    assert state.closed_trades[0].entry_price == 100.0
    assert [trade.entry_price for trade in state.open_positions] == [101.0, 102.0, 103.0]


def test_reversal_closes_all_opposite_positions_and_opens_one():
    assets, engine = _engine()
    engine.generate_signal("BTCUSD", _analysis(100.0), decision_override="BUY")
    engine.generate_signal("BTCUSD", _analysis(101.0), decision_override="BUY")
    result = engine.generate_signal("BTCUSD", _analysis(102.0), decision_override="SELL")

    state = assets.get_asset_state("BTCUSD")
    assert len(state.open_positions) == 1
    assert state.open_positions[0].direction == PositionDirection.SELL.value
    assert len(state.closed_trades) == 2
    assert result.positions_closed == 2


def test_hold_does_not_change_positions():
    assets, engine = _engine()
    engine.generate_signal("BTCUSD", _analysis(100.0), decision_override="BUY")
    before = [trade.id for trade in assets.get_open_positions("BTCUSD")]
    result = engine.generate_signal("BTCUSD", _analysis(101.0), decision_override="HOLD")

    assert result.action_taken == "HOLD - No action taken"
    assert [trade.id for trade in assets.get_open_positions("BTCUSD")] == before
    assert not assets.get_asset_state("BTCUSD").closed_trades


def test_leveraged_pnl_uses_notional_exposure():
    assets, _ = _engine()
    trade = Trade(
        asset="BTCUSD",
        direction=PositionDirection.BUY.value,
        entry_price=118000.0,
        position_size=50.0,
        capital_used=50.0,
        leverage=400.0,
        notional_value=20000.0,
        status=TradeStatus.OPEN.value,
    )
    assert assets.restore_trade(trade)
    assets.update_floating_pnl("BTCUSD", 119180.0)
    assert round(trade.floating_pnl, 2) == 200.0
    closed = assets.close_position("BTCUSD", trade.id, 119180.0, "test")
    assert round(closed.realized_pnl, 2) == 200.0


def test_storage_restart_restores_open_and_closed_state(tmp_path):
    config = SystemConfig(data_directory=str(tmp_path), backup_enabled=False)
    storage = TradeStorage(config, "json")
    open_trade = Trade(
        asset="BTCUSD", direction="BUY", entry_price=100.0,
        position_size=25.0, capital_used=25.0, leverage=400.0,
        notional_value=10000.0,
    )
    closed_trade = Trade(
        asset="BTCUSD", direction="SELL", entry_price=100.0,
        exit_price=101.0, position_size=25.0, capital_used=25.0,
        leverage=400.0, notional_value=10000.0,
        realized_pnl=100.0, status=TradeStatus.CLOSED.value,
    )
    assert storage.save_trade(open_trade)
    assert storage.save_trade(closed_trade)

    restored_assets = AssetManager(100.0)
    for trade in TradeStorage(config, "json").get_trades():
        assert restored_assets.restore_trade(trade)

    state = restored_assets.get_asset_state("BTCUSD")
    assert len(state.open_positions) == 1
    assert len(state.closed_trades) == 1
    assert state.balance == 150.0

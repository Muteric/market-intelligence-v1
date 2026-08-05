"""
portfolio_analyzer.py

AI Trading Intelligence System
Portfolio Analysis Engine
"""

from dataclasses import dataclass
from typing import List
import logging

logger = logging.getLogger(__name__)


@dataclass
class PortfolioState:
    account_balance: float
    equity: float
    floating_pnl: float
    realized_pnl: float
    net_pnl: float
    win_rate: float
    profit_factor: float
    max_drawdown: float
    open_positions_count: int
    daily_trades: int
    weekly_trades: int
    monthly_trades: int


class PortfolioAnalyzer:

    def __init__(self, asset_manager):
        self.asset_manager = asset_manager

    def analyze_portfolio(self, symbol: str) -> PortfolioState:
        """
        Build a portfolio summary for the specified asset.
        This implementation is defensive and works even if some
        fields are not yet available in AssetManager.
        """

        try:

            balance = float(
                getattr(self.asset_manager, "account_balance", 100.0)
            )

            open_trades = getattr(
                self.asset_manager,
                "open_trades",
                {}
            )

            closed_trades = getattr(
                self.asset_manager,
                "closed_trades",
                {}
            )

            symbol_open = open_trades.get(symbol, [])
            symbol_closed = closed_trades.get(symbol, [])

            floating = sum(
                getattr(t, "floating_pnl", 0.0)
                for t in symbol_open
            )

            realized = sum(
                getattr(t, "profit", 0.0)
                for t in symbol_closed
            )

            equity = balance + floating

            wins = sum(
                1 for t in symbol_closed
                if getattr(t, "profit", 0.0) > 0
            )

            total_closed = len(symbol_closed)

            win_rate = (
                (wins / total_closed) * 100
                if total_closed > 0 else 0
            )

            gross_profit = sum(
                max(getattr(t, "profit", 0.0), 0)
                for t in symbol_closed
            )

            gross_loss = abs(sum(
                min(getattr(t, "profit", 0.0), 0)
                for t in symbol_closed
            ))

            profit_factor = (
                gross_profit / gross_loss
                if gross_loss > 0 else gross_profit
            )

            return PortfolioState(

                account_balance=balance,

                equity=equity,

                floating_pnl=floating,

                realized_pnl=realized,

                net_pnl=floating + realized,

                win_rate=win_rate,

                profit_factor=profit_factor,

                max_drawdown=0.0,

                open_positions_count=len(symbol_open),

                daily_trades=0,

                weekly_trades=0,

                monthly_trades=0

            )

        except Exception as ex:

            logger.exception(ex)

            return PortfolioState(

                account_balance=100.0,

                equity=100.0,

                floating_pnl=0.0,

                realized_pnl=0.0,

                net_pnl=0.0,

                win_rate=0.0,

                profit_factor=0.0,

                max_drawdown=0.0,

                open_positions_count=0,

                daily_trades=0,

                weekly_trades=0,

                monthly_trades=0

            )
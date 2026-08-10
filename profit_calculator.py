"""
Profit Calculator for AI Trading Intelligence Bot
Calculates PnL, ROI, and performance statistics for trades and portfolio.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple

from asset_manager import Trade, TradeStatus, PositionDirection
from configuration_manager import PortfolioConfig
from numeric_utils import round_finite

class ProfitMetricType(Enum):
    """Types of profit metrics"""
    FLOATING_PNL = "floating_pnl"
    REALIZED_PNL = "realized_pnl"
    TOTAL_PNL = "total_pnl"
    ROI = "roi"
    WIN_RATE = "win_rate"
    PROFIT_FACTOR = "profit_factor"
    AVERAGE_WINNER = "average_winner"
    AVERAGE_LOSER = "average_loser"
    SHARPE_RATIO = "sharpe_ratio"
    SORTINO_RATIO = "sortino_ratio"
    CALMAR_RATIO = "calmar_ratio"

@dataclass
class ProfitCalculation:
    """Profit calculation result"""
    trade_id: str
    symbol: str
    metric_type: str
    value: float
    timestamp: datetime
    details: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)
        if self.details is None:
            self.details = {}

@dataclass
class PerformanceMetrics:
    """Performance metrics for a set of trades"""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    total_realized_pnl: float = 0.0
    total_floating_pnl: float = 0.0
    net_pnl: float = 0.0
    average_winner: float = 0.0
    average_loser: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    profit_factor: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    average_trade_duration: float = 0.0
    max_drawdown: float = 0.0
    recovery_factor: float = 0.0
    risk_adjusted_return: float = 0.0

class ProfitCalculator:
    """Calculates profit and performance metrics"""
    
    def __init__(self, portfolio_config: PortfolioConfig):
        self.portfolio_config = portfolio_config
        self.profit_history: List[ProfitCalculation] = []
        self.performance_cache: Dict[str, PerformanceMetrics] = {}
    
    def calculate_trade_pnl(self, trade: Trade, current_price: float) -> ProfitCalculation:
        """Calculate PnL for a single trade"""
        if trade.status != TradeStatus.OPEN.value:
            # For closed trades, realized PnL is already calculated
            pnl = trade.realized_pnl
            metric_type = ProfitMetricType.REALIZED_PNL.value
        else:
            # For open trades, calculate floating PnL
            if trade.direction == PositionDirection.BUY.value:
                pnl = (current_price - trade.entry_price) * trade.position_size
            else:
                pnl = (trade.entry_price - current_price) * trade.position_size
            metric_type = ProfitMetricType.FLOATING_PNL.value
        
        # Calculate ROI
        if trade.position_size > 0 and trade.leverage > 0:
            roi = (pnl / (trade.position_size * trade.leverage)) * 100
        else:
            roi = 0.0
        
        # Create profit calculation
        profit_calc = ProfitCalculation(
            trade_id=trade.id,
            symbol=trade.asset,
            metric_type=metric_type,
            value=self._round_decimal(pnl),
            timestamp=datetime.now(timezone.utc),
            details={
                'entry_price': trade.entry_price,
                'current_price': current_price,
                'position_size': trade.position_size,
                'leverage': trade.leverage,
                'direction': trade.direction,
                'roi': self._round_decimal(roi)
            }
        )
        
        self.profit_history.append(profit_calc)
        return profit_calc
    
    def calculate_portfolio_pnl(self, all_trades: List[Trade]) -> Dict[str, Any]:
        """Calculate portfolio-level PnL metrics"""
        open_trades = [t for t in all_trades if t.status == TradeStatus.OPEN.value]
        closed_trades = [t for t in all_trades if t.status == TradeStatus.CLOSED.value]
        
        # Calculate basic metrics
        total_floating_pnl = sum(t.floating_pnl for t in open_trades)
        total_realized_pnl = sum(t.realized_pnl for t in closed_trades)
        net_pnl = total_floating_pnl + total_realized_pnl
        
        # Calculate win/loss statistics
        winning_trades = [t for t in closed_trades if t.realized_pnl > 0]
        losing_trades = [t for t in closed_trades if t.realized_pnl < 0]
        
        total_trades = len(closed_trades)
        winning_count = len(winning_trades)
        losing_count = len(losing_trades)
        
        win_rate = (winning_count / total_trades * 100) if total_trades > 0 else 0.0
        
        # Calculate profit factor
        total_profit = sum(t.realized_pnl for t in winning_trades)
        total_loss = abs(sum(t.realized_pnl for t in losing_trades))
        profit_factor = (total_profit / total_loss) if total_loss > 0 else float('inf')
        
        # Calculate average winner/loser
        average_winner = (total_profit / winning_count) if winning_count > 0 else 0.0
        average_loser = (total_loss / losing_count) if losing_count > 0 else 0.0
        
        # Track largest win/loss
        largest_win = max([t.realized_pnl for t in winning_trades] + [0]) if winning_trades else 0.0
        largest_loss = min([t.realized_pnl for t in losing_trades] + [0]) if losing_trades else 0.0
        
        # Calculate average trade duration
        if closed_trades:
            total_duration = sum(t.trade_duration for t in closed_trades)
            average_trade_duration = total_duration / total_trades
        else:
            average_trade_duration = 0.0
        
        return {
            'total_floating_pnl': self._round_decimal(total_floating_pnl),
            'total_realized_pnl': self._round_decimal(total_realized_pnl),
            'net_pnl': self._round_decimal(net_pnl),
            'win_rate': self._round_decimal(win_rate),
            'profit_factor': self._round_decimal(profit_factor),
            'average_winner': self._round_decimal(average_winner),
            'average_loser': self._round_decimal(average_loser),
            'largest_win': self._round_decimal(largest_win),
            'largest_loss': self._round_decimal(largest_loss),
            'average_trade_duration': self._round_decimal(average_trade_duration),
            'total_open_trades': len(open_trades),
            'total_closed_trades': total_trades,
            'winning_trades': winning_count,
            'losing_trades': losing_count
        }
    
    def calculate_period_performance(self, trades: List[Trade], 
                                    start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Calculate performance for a specific period"""
        # Filter trades by date
        period_trades = [
            t for t in trades 
            if (t.entry_time >= start_date and t.entry_time <= end_date) or
               (t.exit_time and t.exit_time >= start_date and t.exit_time <= end_date)
        ]
        
        if not period_trades:
            return self._get_empty_period_performance()
        
        # Calculate period metrics
        closed_period_trades = [t for t in period_trades if t.status == TradeStatus.CLOSED.value]
        
        winning_trades = [t for t in closed_period_trades if t.realized_pnl > 0]
        losing_trades = [t for t in closed_period_trades if t.realized_pnl < 0]
        
        total_trades = len(closed_period_trades)
        winning_count = len(winning_trades)
        losing_count = len(losing_trades)
        
        win_rate = (winning_count / total_trades * 100) if total_trades > 0 else 0.0
        
        total_profit = sum(t.realized_pnl for t in winning_trades)
        total_loss = abs(sum(t.realized_pnl for t in losing_trades))
        profit_factor = (total_profit / total_loss) if total_loss > 0 else float('inf')
        
        # Calculate period duration in days
        period_days = (end_date - start_date).days
        if period_days == 0:
            period_days = 1
        
        # Calculate daily average
        daily_pnl = total_profit / period_days
        
        return {
            'period_start': start_date.isoformat(),
            'period_end': end_date.isoformat(),
            'period_days': period_days,
            'total_trades': total_trades,
            'winning_trades': winning_count,
            'losing_trades': losing_count,
            'win_rate': self._round_decimal(win_rate),
            'total_pnl': self._round_decimal(total_profit),
            'total_loss': self._round_decimal(total_loss),
            'net_pnl': self._round_decimal(total_profit - total_loss),
            'profit_factor': self._round_decimal(profit_factor),
            'daily_average': self._round_decimal(daily_pnl),
            'average_win': self._round_decimal(total_profit / winning_count) if winning_count > 0 else 0.0,
            'average_loss': self._round_decimal(total_loss / losing_count) if losing_count > 0 else 0.0,
            'largest_win': self._round_decimal(max([t.realized_pnl for t in winning_trades] + [0])),
            'largest_loss': self._round_decimal(min([t.realized_pnl for t in losing_trades] + [0])),
            'total_volume': sum(t.position_size for t in period_trades)
        }
    
    def calculate_risk_adjusted_metrics(self, trades: List[Trade], risk_free_rate: float = 0.02) -> Dict[str, Any]:
        """Calculate risk-adjusted performance metrics"""
        closed_trades = [t for t in trades if t.status == TradeStatus.CLOSED.value]
        
        if not closed_trades:
            return self._get_empty_risk_adjusted_metrics()
        
        # Calculate returns
        returns = []
        for trade in closed_trades:
            if trade.position_size > 0 and trade.leverage > 0:
                trade_return = (trade.realized_pnl / (trade.position_size * trade.leverage)) * 100
                returns.append(trade_return)
        
        if not returns:
            return self._get_empty_risk_adjusted_metrics()
        
        # Calculate Sharpe ratio
        avg_return = sum(returns) / len(returns)
        std_dev = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5
        
        if std_dev > 0:
            sharpe_ratio = (avg_return - risk_free_rate) / std_dev
        else:
            sharpe_ratio = 0.0
        
        # Calculate Sortino ratio (downside deviation only)
        downside_returns = [r for r in returns if r < 0]
        if downside_returns:
            downside_std_dev = (sum((r - avg_return) ** 2 for r in downside_returns) / len(downside_returns)) ** 0.5
            if downside_std_dev > 0:
                sortino_ratio = (avg_return - risk_free_rate) / downside_std_dev
            else:
                sortino_ratio = 0.0
        else:
            sortino_ratio = float('inf') if avg_return > risk_free_rate else 0.0
        
        # Calculate Calmar ratio (return / max drawdown)
        max_drawdown = self._calculate_max_drawdown(closed_trades)
        if max_drawdown > 0:
            calmar_ratio = avg_return / max_drawdown
        else:
            calmar_ratio = float('inf')
        
        # Calculate risk-adjusted return
        risk_adjusted_return = avg_return - (risk_free_rate + std_dev * 0.5)  # Simplified
        
        return {
            'average_return': self._round_decimal(avg_return),
            'standard_deviation': self._round_decimal(std_dev),
            'sharpe_ratio': self._round_decimal(sharpe_ratio),
            'sortino_ratio': self._round_decimal(sortino_ratio),
            'calmar_ratio': self._round_decimal(calmar_ratio),
            'risk_adjusted_return': self._round_decimal(risk_adjusted_return),
            'total_trades': len(closed_trades),
            'positive_returns': len([r for r in returns if r > 0]),
            'negative_returns': len([r for r in returns if r < 0])
        }
    
    def calculate_consecutive_trades(self, trades: List[Trade]) -> Dict[str, Any]:
        """Calculate consecutive wins and losses"""
        closed_trades = [t for t in trades if t.status == TradeStatus.CLOSED.value]
        
        if not closed_trades:
            return {'consecutive_wins': 0, 'consecutive_losses': 0, 'max_consecutive_wins': 0, 'max_consecutive_losses': 0}
        
        consecutive_wins = 0
        consecutive_losses = 0
        max_consecutive_wins = 0
        max_consecutive_losses = 0
        
        for trade in reversed(closed_trades):
            if trade.realized_pnl > 0:
                consecutive_wins += 1
                consecutive_losses = 0
                max_consecutive_wins = max(max_consecutive_wins, consecutive_wins)
            elif trade.realized_pnl < 0:
                consecutive_losses += 1
                consecutive_wins = 0
                max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)
            else:
                consecutive_wins = 0
                consecutive_losses = 0
        
        return {
            'consecutive_wins': consecutive_wins,
            'consecutive_losses': consecutive_losses,
            'max_consecutive_wins': max_consecutive_wins,
            'max_consecutive_losses': max_consecutive_losses
        }
    
    def calculate_drawdown_metrics(self, trades: List[Trade]) -> Dict[str, Any]:
        """Calculate drawdown metrics"""
        closed_trades = [t for t in trades if t.status == TradeStatus.CLOSED.value]
        
        if not closed_trades:
            return self._get_empty_drawdown_metrics()
        
        # Calculate cumulative returns
        cumulative_returns = []
        cumulative = 0.0
        
        for trade in closed_trades:
            if trade.position_size > 0 and trade.leverage > 0:
                trade_return = (trade.realized_pnl / (trade.position_size * trade.leverage)) * 100
                cumulative += trade_return
                cumulative_returns.append(cumulative)
        
        if not cumulative_returns:
            return self._get_empty_drawdown_metrics()
        
        # Calculate maximum drawdown
        max_drawdown = 0.0
        peak = cumulative_returns[0]
        
        for value in cumulative_returns:
            if value > peak:
                peak = value
            else:
                drawdown = ((peak - value) / peak * 100) if peak > 0 else 0.0
                max_drawdown = max(max_drawdown, drawdown)
        
        # Calculate recovery factor
        recovery_factor = (cumulative_returns[-1] / max_drawdown) if max_drawdown > 0 else float('inf')
        
        return {
            'max_drawdown': self._round_decimal(max_drawdown),
            'recovery_factor': self._round_decimal(recovery_factor),
            'total_return': self._round_decimal(cumulative_returns[-1]),
            'number_of_drawdowns': self._count_drawdown_periods(cumulative_returns)
        }
    
    def _calculate_max_drawdown(self, trades: List[Trade]) -> float:
        """Calculate maximum drawdown from a list of trades"""
        if not trades:
            return 0.0
        
        # Calculate cumulative returns
        cumulative_returns = []
        cumulative = 0.0
        
        for trade in trades:
            if trade.position_size > 0 and trade.leverage > 0:
                trade_return = (trade.realized_pnl / (trade.position_size * trade.leverage)) * 100
                cumulative += trade_return
                cumulative_returns.append(cumulative)
        
        if not cumulative_returns:
            return 0.0
        
        # Calculate maximum drawdown
        max_drawdown = 0.0
        peak = cumulative_returns[0]
        
        for value in cumulative_returns:
            if value > peak:
                peak = value
            else:
                drawdown = ((peak - value) / peak * 100) if peak > 0 else 0.0
                max_drawdown = max(max_drawdown, drawdown)
        
        return max_drawdown
    
    def _count_drawdown_periods(self, cumulative_returns: List[float]) -> int:
        """Count number of drawdown periods"""
        if not cumulative_returns:
            return 0
        
        drawdown_count = 0
        in_drawdown = False
        
        for i in range(1, len(cumulative_returns)):
            if cumulative_returns[i] < cumulative_returns[i-1]:
                if not in_drawdown:
                    drawdown_count += 1
                    in_drawdown = True
            else:
                in_drawdown = False
        
        return drawdown_count
    
    def _get_empty_period_performance(self) -> Dict[str, Any]:
        """Get empty period performance"""
        return {
            'period_start': None,
            'period_end': None,
            'period_days': 0,
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0.0,
            'total_pnl': 0.0,
            'total_loss': 0.0,
            'net_pnl': 0.0,
            'profit_factor': 0.0,
            'daily_average': 0.0,
            'average_win': 0.0,
            'average_loss': 0.0,
            'largest_win': 0.0,
            'largest_loss': 0.0,
            'total_volume': 0.0
        }
    
    def _get_empty_risk_adjusted_metrics(self) -> Dict[str, Any]:
        """Get empty risk-adjusted metrics"""
        return {
            'average_return': 0.0,
            'standard_deviation': 0.0,
            'sharpe_ratio': 0.0,
            'sortino_ratio': 0.0,
            'calmar_ratio': 0.0,
            'risk_adjusted_return': 0.0,
            'total_trades': 0,
            'positive_returns': 0,
            'negative_returns': 0
        }
    
    def _get_empty_drawdown_metrics(self) -> Dict[str, Any]:
        """Get empty drawdown metrics"""
        return {
            'max_drawdown': 0.0,
            'recovery_factor': 0.0,
            'total_return': 0.0,
            'number_of_drawdowns': 0
        }
    
    def _round_decimal(self, value: float, decimals: int = 2) -> float:
        """Round decimal value to specified precision"""
        return round_finite(value, decimals) or 0.0

"""
Performance Tracker for AI Trading Intelligence Bot
Tracks and analyzes historical performance data for assets and portfolio.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal, ROUND_HALF_UP

from asset_manager import AssetManager, Trade, TradeStatus
from configuration_manager import PortfolioConfig

class PerformanceMetricType(Enum):
    """Types of performance metrics"""
    TOTAL_PNL = "total_pnl"
    REALIZED_PNL = "realized_pnl"
    FLOATING_PNL = "floating_pnl"
    WIN_RATE = "win_rate"
    PROFIT_FACTOR = "profit_factor"
    SHARPE_RATIO = "sharpe_ratio"
    SORTINO_RATIO = "sortino_ratio"
    CALMAR_RATIO = "calmar_ratio"
    MAX_DRAWDOWN = "max_drawdown"
    RECOVERY_FACTOR = "recovery_factor"
    AVG_TRADE_DURATION = "avg_trade_duration"
    AVG_WINNER = "avg_winner"
    AVG_LOSER = "avg_loser"
    LARGEST_WIN = "largest_win"
    LARGEST_LOSS = "largest_loss"
    CONSECUTIVE_WINS = "consecutive_wins"
    CONSECUTIVE_LOSSES = "consecutive_losses"
    DAILY_PNL = "daily_pnl"
    WEEKLY_PNL = "weekly_pnl"
    MONTHLY_PNL = "monthly_pnl"

@dataclass
class PerformancePeriod:
    """Performance data for a specific period"""
    id: str = None
    start_date: datetime = None
    end_date: datetime = None
    period_type: str = None  # daily, weekly, monthly, custom
    metrics: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4())
        if self.metrics is None:
            self.metrics = {}

@dataclass
class PerformanceBenchmark:
    """Performance benchmark"""
    id: str = None
    name: str = None
    benchmark_type: str = None  # market, asset, custom
    reference_value: float = None
    comparison_value: float = None
    performance_diff: float = None
    
    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4())

class PerformanceTracker:
    """Tracks and analyzes historical performance data"""
    
    def __init__(self, asset_manager: AssetManager, portfolio_config: PortfolioConfig):
        self.asset_manager = asset_manager
        self.portfolio_config = portfolio_config
        self.performance_history: List[PerformancePeriod] = []
        self.benchmarks: List[PerformanceBenchmark] = []
        self.performance_cache: Dict[str, Any] = {}
    
    def track_performance(self, symbol: str = None) -> Dict[str, Any]:
        """Track performance for an asset or entire portfolio"""
        if symbol:
            return self._track_asset_performance(symbol)
        else:
            return self._track_portfolio_performance()
    
    def _track_asset_performance(self, symbol: str) -> Dict[str, Any]:
        """Track performance for a specific asset"""
        asset_state = self.asset_manager.get_asset_state(symbol)
        if not asset_state:
            return {}
        
        # Get all trades for the asset
        all_trades = asset_state.closed_trades + asset_state.open_positions
        
        # Calculate performance metrics
        metrics = self._calculate_performance_metrics(all_trades)
        
        # Get current performance
        current_metrics = self._get_current_performance(asset_state)
        
        # Combine metrics
        performance_data = {
            'symbol': symbol,
            'total_trades': len(all_trades),
            'metrics': metrics,
            'current_metrics': current_metrics,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Store performance period
        period = PerformancePeriod(
            period_type='asset',
            metrics=performance_data
        )
        self.performance_history.append(period)
        
        return performance_data
    
    def _track_portfolio_performance(self) -> Dict[str, Any]:
        """Track performance for the entire portfolio"""
        all_assets = self.asset_manager.get_all_assets()
        
        # Get performance for each asset
        asset_performances = {}
        for symbol, asset_state in all_assets.items():
            asset_performances[symbol] = self._track_asset_performance(symbol)
        
        # Calculate portfolio-level metrics
        portfolio_metrics = self._calculate_portfolio_performance_metrics(all_assets)
        
        # Get current portfolio performance
        current_portfolio_metrics = self._get_current_portfolio_performance(all_assets)
        
        # Combine portfolio performance
        performance_data = {
            'total_assets': len(all_assets),
            'asset_performances': asset_performances,
            'portfolio_metrics': portfolio_metrics,
            'current_portfolio_metrics': current_portfolio_metrics,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Store performance period
        period = PerformancePeriod(
            period_type='portfolio',
            metrics=performance_data
        )
        self.performance_history.append(period)
        
        return performance_data
    
    def _calculate_performance_metrics(self, trades: List[Trade]) -> Dict[str, Any]:
        """Calculate performance metrics for a set of trades"""
        closed_trades = [t for t in trades if t.status == TradeStatus.CLOSED.value]
        
        if not closed_trades:
            return self._get_empty_performance_metrics()
        
        # Calculate basic metrics
        winning_trades = [t for t in closed_trades if t.realized_pnl > 0]
        losing_trades = [t for t in closed_trades if t.realized_pnl < 0]
        
        total_trades = len(closed_trades)
        winning_count = len(winning_trades)
        losing_count = len(losing_trades)
        
        win_rate = (winning_count / total_trades * 100) if total_trades > 0 else 0.0
        
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
        
        # Calculate consecutive wins/losses
        consecutive_wins, consecutive_losses = self._calculate_consecutive_trades(closed_trades)
        
        # Calculate drawdown metrics
        max_drawdown = self._calculate_max_drawdown(closed_trades)
        recovery_factor = self._calculate_recovery_factor(total_profit, max_drawdown)
        
        # Calculate risk-adjusted metrics
        sharpe_ratio = self._calculate_sharpe_ratio(closed_trades)
        sortino_ratio = self._calculate_sortino_ratio(closed_trades)
        calmar_ratio = self._calculate_calmar_ratio(total_profit, max_drawdown)
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_count,
            'losing_trades': losing_count,
            'win_rate': self._round_decimal(win_rate),
            'total_realized_pnl': self._round_decimal(total_profit),
            'total_loss': self._round_decimal(total_loss),
            'net_pnl': self._round_decimal(total_profit - total_loss),
            'profit_factor': self._round_decimal(profit_factor),
            'average_winner': self._round_decimal(average_winner),
            'average_loser': self._round_decimal(average_loser),
            'largest_win': self._round_decimal(largest_win),
            'largest_loss': self._round_decimal(largest_loss),
            'average_trade_duration': self._round_decimal(average_trade_duration),
            'consecutive_wins': consecutive_wins,
            'consecutive_losses': consecutive_losses,
            'max_drawdown': self._round_decimal(max_drawdown),
            'recovery_factor': self._round_decimal(recovery_factor),
            'sharpe_ratio': self._round_decimal(sharpe_ratio),
            'sortino_ratio': self._round_decimal(sortino_ratio),
            'calmar_ratio': self._round_decimal(calmar_ratio)
        }
    
    def _get_current_performance(self, asset_state) -> Dict[str, Any]:
        """Get current performance metrics for an asset"""
        open_positions = asset_state.open_positions
        closed_trades = asset_state.closed_trades
        
        # Calculate current PnL
        total_floating_pnl = sum(t.floating_pnl for t in open_positions)
        total_realized_pnl = sum(t.realized_pnl for t in closed_trades)
        net_pnl = total_floating_pnl + total_realized_pnl
        
        # Calculate current win rate
        winning_trades = [t for t in closed_trades if t.realized_pnl > 0]
        losing_trades = [t for t in closed_trades if t.realized_pnl < 0]
        
        total_trades = len(closed_trades)
        win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0.0
        
        return {
            'current_balance': asset_state.balance,
            'current_equity': asset_state.equity,
            'total_floating_pnl': self._round_decimal(total_floating_pnl),
            'total_realized_pnl': self._round_decimal(total_realized_pnl),
            'net_pnl': self._round_decimal(net_pnl),
            'win_rate': self._round_decimal(win_rate),
            'open_positions_count': len(open_positions),
            'closed_trades_count': len(closed_trades)
        }
    
    def _calculate_portfolio_performance_metrics(self, all_assets: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate portfolio-level performance metrics"""
        # Aggregate all trades across all assets
        all_trades = []
        for asset in all_assets.values():
            all_trades.extend(asset.closed_trades)
        
        # Calculate portfolio metrics
        portfolio_metrics = self._calculate_performance_metrics(all_trades)
        
        # Add portfolio-specific metrics
        total_balance = sum(asset.balance for asset in all_assets.values())
        total_equity = sum(asset.equity for asset in all_assets.values())
        
        portfolio_metrics.update({
            'total_balance': total_balance,
            'total_equity': total_equity,
            'total_assets': len(all_assets)
        })
        
        return portfolio_metrics
    
    def _get_current_portfolio_performance(self, all_assets: Dict[str, Any]) -> Dict[str, Any]:
        """Get current portfolio performance metrics"""
        total_balance = sum(asset.balance for asset in all_assets.values())
        total_equity = sum(asset.equity for asset in all_assets.values())
        
        # Calculate total PnL
        total_floating_pnl = sum(
            sum(trade.floating_pnl for trade in asset.open_positions)
            for asset in all_assets.values()
        )
        
        total_realized_pnl = sum(
            sum(trade.realized_pnl for trade in asset.closed_trades)
            for asset in all_assets.values()
        )
        
        net_pnl = total_floating_pnl + total_realized_pnl
        
        return {
            'current_balance': total_balance,
            'current_equity': total_equity,
            'total_floating_pnl': self._round_decimal(total_floating_pnl),
            'total_realized_pnl': self._round_decimal(total_realized_pnl),
            'net_pnl': self._round_decimal(net_pnl),
            'total_assets': len(all_assets)
        }
    
    def get_performance_report(self, symbol: str = None, period_days: int = 30) -> Dict[str, Any]:
        """Get performance report for an asset or portfolio"""
        if symbol:
            # Get asset performance
            asset_performance = self._track_asset_performance(symbol)
            
            # Get historical performance for the period
            historical_performance = self._get_historical_performance(symbol, period_days)
            
            return {
                'symbol': symbol,
                'current_performance': asset_performance,
                'historical_performance': historical_performance,
                'period_days': period_days
            }
        else:
            # Get portfolio performance
            portfolio_performance = self._track_portfolio_performance()
            
            # Get historical performance for the period
            historical_performance = self._get_historical_performance(None, period_days)
            
            return {
                'portfolio_performance': portfolio_performance,
                'historical_performance': historical_performance,
                'period_days': period_days
            }
    
    def add_benchmark(self, name: str, benchmark_type: str, 
                     reference_value: float, symbol: str = None) -> PerformanceBenchmark:
        """Add a performance benchmark"""
        benchmark = PerformanceBenchmark(
            name=name,
            benchmark_type=benchmark_type,
            reference_value=reference_value,
            symbol=symbol
        )
        
        self.benchmarks.append(benchmark)
        return benchmark
    
    def compare_with_benchmark(self, symbol: str = None) -> List[Dict[str, Any]]:
        """Compare performance with benchmarks"""
        comparisons = []
        
        for benchmark in self.benchmarks:
            if benchmark.symbol and symbol and benchmark.symbol != symbol:
                continue
            
            # Get performance data
            if symbol:
                performance = self._track_asset_performance(symbol)
            else:
                performance = self._track_portfolio_performance()
            
            # Calculate comparison
            if benchmark.benchmark_type == 'total_pnl':
                actual_value = performance['current_metrics']['net_pnl']
            elif benchmark.benchmark_type == 'win_rate':
                actual_value = performance['current_metrics']['win_rate']
            elif benchmark.benchmark_type == 'profit_factor':
                actual_value = performance['metrics']['profit_factor']
            else:
                actual_value = 0.0
            
            comparison_value = actual_value - benchmark.reference_value
            
            comparison = {
                'benchmark_name': benchmark.name,
                'benchmark_type': benchmark.benchmark_type,
                'reference_value': benchmark.reference_value,
                'actual_value': actual_value,
                'comparison_value': comparison_value,
                'performance_diff': comparison_value
            }
            
            comparisons.append(comparison)
        
        return comparisons
    
    def get_performance_history(self, symbol: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get performance history"""
        if symbol:
            # Filter performance periods for the specific asset
            history = [
                period.metrics for period in self.performance_history
                if period.metrics.get('symbol') == symbol
            ]
        else:
            # Get all portfolio performance periods
            history = [
                period.metrics for period in self.performance_history
                if period.metrics.get('total_assets', 0) > 0
            ]
        
        # Sort by timestamp
        history.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return history[:limit]
    
    def _get_historical_performance(self, symbol: str, period_days: int) -> List[Dict[str, Any]]:
        """Get historical performance for a specific period"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=period_days)
        
        # Filter performance periods by date
        historical_performance = [
            period.metrics for period in self.performance_history
            if datetime.fromisoformat(period.metrics.get('timestamp', '').replace('Z', '+00:00')) >= cutoff_date
        ]
        
        if symbol:
            # Filter for specific asset
            historical_performance = [
                perf for perf in historical_performance
                if perf.get('symbol') == symbol
            ]
        
        return historical_performance
    
    def _calculate_consecutive_trades(self, closed_trades: List[Trade]) -> Tuple[int, int]:
        """Calculate consecutive wins and losses"""
        if not closed_trades:
            return 0, 0
        
        consecutive_wins = 0
        consecutive_losses = 0
        
        for trade in reversed(closed_trades):
            if trade.realized_pnl > 0:
                consecutive_wins += 1
                consecutive_losses = 0
            elif trade.realized_pnl < 0:
                consecutive_losses += 1
                consecutive_wins = 0
            else:
                consecutive_wins = 0
                consecutive_losses = 0
        
        return consecutive_wins, consecutive_losses
    
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
    
    def _calculate_recovery_factor(self, total_profit: float, max_drawdown: float) -> float:
        """Calculate recovery factor"""
        if max_drawdown <= 0:
            return float('inf')
        
        recovery_factor = total_profit / max_drawdown
        return recovery_factor
    
    def _calculate_sharpe_ratio(self, trades: List[Trade]) -> float:
        """Calculate Sharpe ratio"""
        if not trades:
            return 0.0
        
        # Calculate returns
        returns = []
        for trade in trades:
            if trade.position_size > 0 and trade.leverage > 0:
                trade_return = (trade.realized_pnl / (trade.position_size * trade.leverage)) * 100
                returns.append(trade_return)
        
        if not returns:
            return 0.0
        
        # Calculate Sharpe ratio
        avg_return = sum(returns) / len(returns)
        std_dev = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5
        
        if std_dev == 0:
            return 0.0
        
        sharpe_ratio = avg_return / std_dev
        return sharpe_ratio
    
    def _calculate_sortino_ratio(self, trades: List[Trade]) -> float:
        """Calculate Sortino ratio"""
        if not trades:
            return 0.0
        
        # Calculate returns
        returns = []
        for trade in trades:
            if trade.position_size > 0 and trade.leverage > 0:
                trade_return = (trade.realized_pnl / (trade.position_size * trade.leverage)) * 100
                returns.append(trade_return)
        
        if not returns:
            return 0.0
        
        # Calculate Sortino ratio (downside deviation only)
        avg_return = sum(returns) / len(returns)
        downside_returns = [r for r in returns if r < 0]
        
        if not downside_returns:
            return float('inf') if avg_return > 0 else 0.0
        
        downside_std_dev = (sum((r - avg_return) ** 2 for r in downside_returns) / len(downside_returns)) ** 0.5
        
        if downside_std_dev == 0:
            return 0.0
        
        sortino_ratio = avg_return / downside_std_dev
        return sortino_ratio
    
    def _calculate_calmar_ratio(self, total_profit: float, max_drawdown: float) -> float:
        """Calculate Calmar ratio"""
        if max_drawdown <= 0:
            return float('inf')
        
        calmar_ratio = total_profit / max_drawdown
        return calmar_ratio
    
    def _get_empty_performance_metrics(self) -> Dict[str, Any]:
        """Get empty performance metrics"""
        return {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0.0,
            'total_realized_pnl': 0.0,
            'total_loss': 0.0,
            'net_pnl': 0.0,
            'profit_factor': 0.0,
            'average_winner': 0.0,
            'average_loser': 0.0,
            'largest_win': 0.0,
            'largest_loss': 0.0,
            'average_trade_duration': 0.0,
            'consecutive_wins': 0,
            'consecutive_losses': 0,
            'max_drawdown': 0.0,
            'recovery_factor': 0.0,
            'sharpe_ratio': 0.0,
            'sortino_ratio': 0.0,
            'calmar_ratio': 0.0
        }
    
    def _round_decimal(self, value: float, decimals: int = 2) -> float:
        """Round decimal value to specified precision"""
        return float(Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
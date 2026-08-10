"""
Portfolio Manager for AI Trading Intelligence Bot
Manages portfolio performance, metrics, and overall portfolio statistics.
"""

import uuid
import math
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple

from configuration_manager import PortfolioConfig, TradingConfig
from asset_manager import AssetManager, AssetState, Trade, TradeStatus
from signal_engine import SignalResult
from numeric_utils import round_finite

class PortfolioEventType(Enum):
    """Portfolio event types"""
    TRADE_OPENED = "TRADE_OPENED"
    TRADE_CLOSED = "TRADE_CLOSED"
    BALANCE_UPDATED = "BALANCE_UPDATED"
    EQUITY_UPDATED = "EQUITY_UPDATED"
    SIGNAL_GENERATED = "SIGNAL_GENERATED"

@dataclass
class PortfolioEvent:
    """Portfolio event"""
    id: str = None
    event_type: str = None
    timestamp: datetime = None
    symbol: str = None
    data: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4())
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)
        if self.data is None:
            self.data = {}

@dataclass
class PortfolioMetrics:
    """Portfolio metrics"""
    total_balance: float = 100.0
    total_equity: float = 100.0
    total_floating_pnl: float = 0.0
    total_realized_pnl: float = 0.0
    net_pnl: float = 0.0
    net_roi: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    average_winner: float = 0.0
    average_loser: float = 0.0
    average_trade_duration: float = 0.0
    current_exposure: float = 0.0
    open_risk: float = 0.0
    max_drawdown: float = 0.0
    floating_drawdown: float = 0.0
    consecutive_wins: int = 0
    consecutive_losses: int = 0
    recovery_factor: float = 0.0
    daily_profit: float = 0.0
    weekly_profit: float = 0.0
    monthly_profit: float = 0.0
    current_equity: float = 100.0
    balance: float = 100.0
    available_margin: float = 100.0
    used_margin: float = 0.0
    total_closed_trades: int = 0
    open_positions_count: int = 0

class PortfolioManager:
    """Manages portfolio performance and metrics"""
    
    def __init__(self, asset_manager: AssetManager, portfolio_config: PortfolioConfig, 
                 trading_config: TradingConfig):
        self.asset_manager = asset_manager
        self.portfolio_config = portfolio_config
        self.trading_config = trading_config
        self.events: List[PortfolioEvent] = []
        self.metrics_history: List[Dict[str, Any]] = []
        self.daily_pnl: Dict[str, float] = {}
        self.weekly_pnl: Dict[str, float] = {}
        self.monthly_pnl: Dict[str, float] = {}
    
    def update_portfolio(self) -> PortfolioMetrics:
        """Update portfolio metrics based on current state"""
        # Get all asset states
        all_assets = self.asset_manager.get_all_assets()
        
        # Calculate aggregate metrics
        total_balance = sum(asset.balance for asset in all_assets.values())
        total_equity = sum(asset.equity for asset in all_assets.values())
        total_initial_balance = sum(
            getattr(asset, "starting_balance", asset.balance)
            for asset in all_assets.values()
        )
        
        # Calculate PnL
        total_floating_pnl = sum(
            sum(trade.floating_pnl for trade in asset.open_positions)
            for asset in all_assets.values()
        )
        
        total_realized_pnl = sum(
            sum(trade.realized_pnl for trade in asset.closed_trades)
            for asset in all_assets.values()
        )
        
        net_pnl = total_floating_pnl + total_realized_pnl
        
        # Calculate win rate and profit factor
        all_closed_trades = []
        for asset in all_assets.values():
            all_closed_trades.extend(asset.closed_trades)
        
        winning_trades = [t for t in all_closed_trades if t.realized_pnl > 0]
        losing_trades = [t for t in all_closed_trades if t.realized_pnl < 0]
        
        total_trades = len(all_closed_trades)
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
        if all_closed_trades:
            total_duration = sum(t.trade_duration for t in all_closed_trades)
            average_trade_duration = total_duration / total_trades
        else:
            average_trade_duration = 0.0
        
        # Calculate exposure
        total_position_value = sum(
            sum((trade.position_size or 0.0) for trade in asset.open_positions)
            for asset in all_assets.values()
        )
        current_exposure = (total_position_value / total_balance * 100) if total_balance > 0 else 0.0
        
        # Calculate risk metrics
        open_risk = self._calculate_open_risk(all_assets)
        max_drawdown = self._calculate_max_drawdown()
        floating_drawdown = self._calculate_floating_drawdown(all_assets)
        
        # Calculate consecutive wins/losses
        consecutive_wins, consecutive_losses = self._calculate_consecutive_trades(all_closed_trades)
        
        # Calculate recovery factor
        recovery_factor = self._calculate_recovery_factor(total_realized_pnl, max_drawdown)
        
        # Calculate ROI
        net_roi = (net_pnl / total_initial_balance * 100) if total_initial_balance > 0 else 0.0
        
        # Calculate period profits
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        daily_profit = self.daily_pnl.get(today, 0.0)
        
        # Calculate weekly profit (simplified - last 7 days)
        weekly_profit = sum(self.daily_pnl.values()) if self.daily_pnl else 0.0
        
        # Calculate monthly profit (simplified - last 30 days)
        monthly_profit = sum(self.daily_pnl.values()) if self.daily_pnl else 0.0
        
        # Create metrics
        metrics = PortfolioMetrics(
            total_balance=self._round_decimal(total_balance),
            total_equity=self._round_decimal(total_equity),
            total_floating_pnl=self._round_decimal(total_floating_pnl),
            total_realized_pnl=self._round_decimal(total_realized_pnl),
            net_pnl=self._round_decimal(net_pnl),
            net_roi=self._round_decimal(net_roi),
            win_rate=self._round_decimal(win_rate),
            profit_factor=self._round_decimal(profit_factor),
            total_trades=total_trades,
            winning_trades=winning_count,
            losing_trades=losing_count,
            largest_win=self._round_decimal(largest_win),
            largest_loss=self._round_decimal(largest_loss),
            average_winner=self._round_decimal(average_winner),
            average_loser=self._round_decimal(average_loser),
            average_trade_duration=self._round_decimal(average_trade_duration),
            current_exposure=self._round_decimal(current_exposure),
            open_risk=self._round_decimal(open_risk),
            max_drawdown=self._round_decimal(max_drawdown),
            floating_drawdown=self._round_decimal(floating_drawdown),
            consecutive_wins=consecutive_wins,
            consecutive_losses=consecutive_losses,
            recovery_factor=self._round_decimal(recovery_factor),
            daily_profit=self._round_decimal(daily_profit),
            weekly_profit=self._round_decimal(weekly_profit),
            monthly_profit=self._round_decimal(monthly_profit),
            current_equity=self._round_decimal(total_equity),
            balance=self._round_decimal(total_balance),
            available_margin=self._round_decimal(total_balance),
            used_margin=self._round_decimal(total_position_value),
            total_closed_trades=total_trades,
            open_positions_count=sum(len(asset.open_positions) for asset in all_assets.values())
        )
        
        # Store metrics history
        self._store_metrics_history(metrics)
        
        return metrics
    
    def add_event(self, event_type: str, symbol: str = None, data: Dict[str, Any] = None) -> PortfolioEvent:
        """Add a portfolio event"""
        event = PortfolioEvent(
            event_type=event_type,
            symbol=symbol,
            data=data or {}
        )
        
        self.events.append(event)
        return event
    
    def update_daily_pnl(self, date: str, pnl: float) -> None:
        """Update daily PnL"""
        self.daily_pnl[date] = self._round_decimal(self.daily_pnl.get(date, 0.0) + pnl)
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get comprehensive portfolio summary"""
        metrics = self.update_portfolio()
        all_assets = self.asset_manager.get_all_assets()
        
        # Get asset-specific summaries
        asset_summaries = {}
        for symbol, asset_state in all_assets.items():
            asset_summaries[symbol] = self._get_asset_summary(symbol, asset_state)
        
        return {
            'portfolio_metrics': asdict(metrics),
            'asset_summaries': asset_summaries,
            'recent_events': self._get_recent_events(10),
            'metrics_history': self.metrics_history[-100:] if self.metrics_history else []  # Last 100 entries
        }
    
    def get_performance_report(self, period_days: int = 30) -> Dict[str, Any]:
        """Get performance report for a specific period"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=period_days)
        
        # Filter events by date
        period_events = [e for e in self.events if e.timestamp >= cutoff_date]
        
        # Calculate period metrics
        period_trades = []
        for event in period_events:
            if event.event_type == PortfolioEventType.TRADE_CLOSED.value:
                period_trades.append(event.data)
        
        # Calculate period statistics
        if period_trades:
            winning_trades = [t for t in period_trades if t.get('realized_pnl', 0) > 0]
            losing_trades = [t for t in period_trades if t.get('realized_pnl', 0) < 0]
            
            period_win_rate = (len(winning_trades) / len(period_trades) * 100) if period_trades else 0.0
            period_total_pnl = sum(t.get('realized_pnl', 0) for t in period_trades)
            
            return {
                'period_days': period_days,
                'total_trades': len(period_trades),
                'winning_trades': len(winning_trades),
                'losing_trades': len(losing_trades),
                'win_rate': self._round_decimal(period_win_rate),
                'total_pnl': self._round_decimal(period_total_pnl),
                'average_win': self._round_decimal(sum(t.get('realized_pnl', 0) for t in winning_trades) / len(winning_trades)) if winning_trades else 0.0,
                'average_loss': self._round_decimal(sum(t.get('realized_pnl', 0) for t in losing_trades) / len(losing_trades)) if losing_trades else 0.0,
                'largest_win': self._round_decimal(max([t.get('realized_pnl', 0) for t in winning_trades] + [0])),
                'largest_loss': self._round_decimal(min([t.get('realized_pnl', 0) for t in losing_trades] + [0])),
                'profit_factor': self._round_decimal(
                    (sum(t.get('realized_pnl', 0) for t in winning_trades) / 
                     abs(sum(t.get('realized_pnl', 0) for t in losing_trades)))
                    if sum(t.get('realized_pnl', 0) for t in losing_trades) != 0 else float('inf')
                )
            }
        
        return {
            'period_days': period_days,
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0.0,
            'total_pnl': 0.0,
            'average_win': 0.0,
            'average_loss': 0.0,
            'largest_win': 0.0,
            'largest_loss': 0.0,
            'profit_factor': 0.0
        }
    
    def _get_asset_summary(self, symbol: str, asset_state: AssetState) -> Dict[str, Any]:
        """Get summary for a specific asset"""
        open_positions = asset_state.open_positions
        closed_trades = asset_state.closed_trades
        
        # Calculate asset-specific metrics
        total_position_value = sum(p.position_size for p in open_positions)
        total_floating_pnl = sum(p.floating_pnl for p in open_positions)
        total_realized_pnl = sum(t.realized_pnl for t in closed_trades)
        
        # Calculate win rate
        winning_trades = [t for t in closed_trades if t.realized_pnl > 0]
        losing_trades = [t for t in closed_trades if t.realized_pnl < 0]
        
        win_rate = (len(winning_trades) / len(closed_trades) * 100) if closed_trades else 0.0
        
        return {
            'symbol': symbol,
            'balance': asset_state.balance,
            'equity': asset_state.equity,
            'open_positions_count': len(open_positions),
            'closed_trades_count': len(closed_trades),
            'total_position_value': total_position_value,
            'total_floating_pnl': total_floating_pnl,
            'total_realized_pnl': total_realized_pnl,
            'net_pnl': total_floating_pnl + total_realized_pnl,
            'win_rate': self._round_decimal(win_rate),
            'current_exposure': (total_position_value / asset_state.balance * 100) if asset_state.balance > 0 else 0.0
        }
    
    def _get_recent_events(self, limit: int) -> List[Dict[str, Any]]:
        """Get recent portfolio events"""
        recent_events = self.events[-limit:] if self.events else []
        return [
            {
                'id': event.id,
                'type': event.event_type,
                'timestamp': event.timestamp.isoformat(),
                'symbol': event.symbol,
                'data': event.data
            }
            for event in recent_events
        ]
    
    def _store_metrics_history(self, metrics: PortfolioMetrics) -> None:
        """Store metrics in history"""
        metrics_dict = asdict(metrics)
        metrics_dict['timestamp'] = datetime.now(timezone.utc).isoformat()
        
        self.metrics_history.append(metrics_dict)
        
        # Keep only last 1000 entries to prevent memory issues
        if len(self.metrics_history) > 1000:
            self.metrics_history = self.metrics_history[-1000:]
    
    def _calculate_open_risk(self, all_assets: Dict[str, AssetState]) -> float:
        """Calculate open position risk"""
        total_risk = 0.0
        
        for asset in all_assets.values():
            for trade in asset.open_positions:
                # Calculate risk based on position size and volatility
                risk = trade.position_size * 0.1  # Simplified risk calculation
                total_risk += risk
        
        return self._round_decimal(total_risk)
    
    def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown from metrics history"""
        if not self.metrics_history:
            return 0.0
        
        max_drawdown = 0.0
        peak = self.metrics_history[0]['total_equity']
        
        for metrics in self.metrics_history:
            current_equity = metrics['total_equity']
            
            if current_equity > peak:
                peak = current_equity
            
            drawdown = ((peak - current_equity) / peak * 100) if peak > 0 else 0.0
            max_drawdown = max(max_drawdown, drawdown)
        
        return self._round_decimal(max_drawdown)
    
    def _calculate_floating_drawdown(self, all_assets: Dict[str, AssetState]) -> float:
        """Calculate floating drawdown"""
        total_equity = sum(asset.equity for asset in all_assets.values())
        total_balance = sum(asset.balance for asset in all_assets.values())
        
        if total_balance <= 0:
            return 0.0
        
        drawdown = ((total_balance - total_equity) / total_balance * 100)
        return self._round_decimal(drawdown)
    
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
    
    def _calculate_recovery_factor(self, total_realized_pnl: float, max_drawdown: float) -> float:
        """Calculate recovery factor"""
        if max_drawdown <= 0:
            return float('inf')
        
        recovery_factor = total_realized_pnl / max_drawdown
        return self._round_decimal(recovery_factor)
    
    def _round_decimal(self, value: float, decimals: int = 2) -> float:
        """Round decimal value to specified precision"""
        return round_finite(value, decimals) or 0.0

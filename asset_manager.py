"""
Asset Manager for AI Trading Intelligence Bot
Manages independent state for each asset (BTCUSD, XAUUSD) with isolation.
"""

import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any
from decimal import Decimal, ROUND_HALF_UP
from numeric_utils import round_finite

class AssetSymbol(Enum):
    """Supported asset symbols"""
    BTCUSD = "BTCUSD"
    XAUUSD = "XAUUSD"

class TradeStatus(Enum):
    """Trade status enumeration"""
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    LIQUIDATED = "LIQUIDATED"
    STOPPED_OUT = "STOPPED_OUT"

class PositionDirection(Enum):
    """Position direction enumeration"""
    BUY = "BUY"
    SELL = "SELL"

@dataclass
class Trade:
    """Trade data structure"""
    id: str = None
    asset: str = None
    direction: str = None
    entry_price: float = None
    entry_time: datetime = None
    exit_price: float = None
    exit_time: datetime = None
    position_size: float = None
    capital_used: float = None
    notional_value: float = None
    leverage: float = None
    floating_pnl: float = 0.0
    realized_pnl: float = 0.0
    trade_duration: int = 0  # in hours
    roi: float = 0.0
    status: str = TradeStatus.OPEN.value
    stop_loss_price: float = None
    take_profit_price: float = None
    close_reason: str = None
    
    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4())
        if self.entry_time is None:
            self.entry_time = datetime.now(timezone.utc)
        if self.status is None:
            self.status = TradeStatus.OPEN.value

@dataclass
class AssetState:
    """State for a specific asset"""
    symbol: str
    balance: float = 100.0
    equity: float = 100.0
    open_positions: List[Trade] = None
    closed_trades: List[Trade] = None
    signal_history: List[Dict[str, Any]] = None
    performance_stats: Dict[str, Any] = None
    starting_balance: float = None
    
    def __post_init__(self):
        if self.open_positions is None:
            self.open_positions = []
        if self.closed_trades is None:
            self.closed_trades = []
        if self.signal_history is None:
            self.signal_history = []
        if self.performance_stats is None:
            self.performance_stats = self._initialize_performance_stats()
        if self.starting_balance is None:
            self.starting_balance = float(self.balance)
    
    def _initialize_performance_stats(self) -> Dict[str, Any]:
        """Initialize performance statistics"""
        return {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0.0,
            'profit_factor': 0.0,
            'total_realized_pnl': 0.0,
            'total_floating_pnl': 0.0,
            'largest_win': 0.0,
            'largest_loss': 0.0,
            'average_winner': 0.0,
            'average_loser': 0.0,
            'average_trade_duration': 0.0,
            'current_exposure': 0.0,
            'open_risk': 0.0,
            'max_drawdown': 0.0,
            'consecutive_wins': 0,
            'consecutive_losses': 0,
            'recovery_factor': 0.0,
            'daily_profit': 0.0,
            'weekly_profit': 0.0,
            'monthly_profit': 0.0,
            'net_roi': 0.0,
            'current_equity': self.equity,
            'balance': self.balance,
            'available_margin': self.balance,
            'used_margin': 0.0,
            'floating_drawdown': 0.0,
            'total_closed_trades': 0
        }

class AssetManager:
    """Manages independent state for each asset"""
    
    def __init__(self, initial_balance: float = 100.0,
                 asset_configs: Optional[Dict[str, Any]] = None,
                 base_position_size: float = 0.5,
                 scaling_position_size: float = 0.25,
                 max_positions: int = 3):
        if initial_balance < 0:
            raise ValueError("initial_balance must be non-negative")
        self.initial_balance = float(initial_balance)
        self.base_position_size = float(base_position_size)
        self.scaling_position_size = float(scaling_position_size)
        self.max_positions = int(max_positions)
        self.asset_configs = asset_configs or {}
        self.assets: Dict[str, AssetState] = {}
        self._initialize_assets()
    
    def _initialize_assets(self) -> None:
        """Initialize supported assets"""
        if self.asset_configs:
            symbols = [
                symbol for symbol, config in self.asset_configs.items()
                if getattr(config, "enabled", True)
            ]
            allocations = {
                symbol: float(getattr(self.asset_configs[symbol], "allocation_percentage", 0.0) or 0.0)
                for symbol in symbols
            }
            if not any(allocations.values()) and symbols:
                equal_allocation = 1.0 / len(symbols)
                allocations = {symbol: equal_allocation for symbol in symbols}
        else:
            symbols = [symbol.value for symbol in AssetSymbol]
            equal_allocation = 1.0 / len(symbols) if symbols else 0.0
            allocations = {symbol: equal_allocation for symbol in symbols}

        for symbol in symbols:
            balance = self.initial_balance * allocations.get(symbol, 0.0)
            self.assets[symbol] = AssetState(
                symbol=symbol,
                balance=balance,
                equity=balance,
            )
    
    def get_asset_state(self, symbol: str) -> Optional[AssetState]:
        """Get state for a specific asset"""
        return self.assets.get(symbol)
    
    def get_all_assets(self) -> Dict[str, AssetState]:
        """Get all asset states"""
        return self.assets.copy()
    
    def add_open_position(self, symbol: str, trade: Trade) -> bool:
        """Add an open position for an asset"""
        asset_state = self.get_asset_state(symbol)
        if not asset_state:
            return False
        
        # Check position limit
        if len(asset_state.open_positions) >= self.max_positions:
            return False
        
        # Calculate position size based on account balance
        if len(asset_state.open_positions) == 0:
            # First position: 50% of balance
            position_size = asset_state.balance * self.base_position_size
        else:
            # Additional positions: 25% of balance
            position_size = asset_state.balance * self.scaling_position_size

        trade.position_size = position_size
        trade.capital_used = position_size
        trade.notional_value = position_size * (trade.leverage or 1.0)
        trade.asset = symbol
        asset_state.open_positions.append(trade)
        return True
    
    def close_position(self, symbol: str, trade_id: str, exit_price: float, 
                      close_reason: str = None) -> Optional[Trade]:
        """Close a position for an asset"""
        asset_state = self.get_asset_state(symbol)
        if not asset_state:
            return None
        
        for trade in asset_state.open_positions:
            if trade.id == trade_id:
                # Calculate PnL
                capital_used = trade.capital_used if trade.capital_used is not None else trade.position_size
                leverage = trade.leverage or 1.0
                notional_value = trade.notional_value or (capital_used * leverage)
                price_return = (
                    (exit_price - trade.entry_price) / trade.entry_price
                    if trade.direction == PositionDirection.BUY.value
                    else (trade.entry_price - exit_price) / trade.entry_price
                )
                trade.realized_pnl = notional_value * price_return
                
                trade.exit_price = exit_price
                trade.exit_time = datetime.now(timezone.utc)
                trade.status = TradeStatus.CLOSED.value
                trade.close_reason = close_reason
                trade.trade_duration = int((trade.exit_time - trade.entry_time).total_seconds() / 3600)
                trade.roi = (trade.realized_pnl / capital_used) * 100 if capital_used > 0 else 0.0
                asset_state.balance += trade.realized_pnl
                
                # Move to closed trades
                asset_state.closed_trades.append(trade)
                asset_state.open_positions.remove(trade)
                
                # Update performance stats
                self._update_performance_stats(asset_state)
                
                return trade
        
        return None
    
    def update_floating_pnl(self, symbol: str, current_price: float) -> None:
        """Update floating PnL for all open positions"""
        asset_state = self.get_asset_state(symbol)
        if not asset_state:
            return
        
        for trade in asset_state.open_positions:
            capital_used = trade.capital_used if trade.capital_used is not None else trade.position_size
            notional_value = trade.notional_value or (capital_used * (trade.leverage or 1.0))
            price_return = (
                (current_price - trade.entry_price) / trade.entry_price
                if trade.direction == PositionDirection.BUY.value
                else (trade.entry_price - current_price) / trade.entry_price
            )
            trade.floating_pnl = notional_value * price_return
    
    def get_open_positions_count(self, symbol: str) -> int:
        """Get number of open positions for an asset"""
        asset_state = self.get_asset_state(symbol)
        return len(asset_state.open_positions) if asset_state else 0
    
    def get_open_positions(self, symbol: str) -> List[Trade]:
        """Get all open positions for an asset"""
        asset_state = self.get_asset_state(symbol)
        return asset_state.open_positions.copy() if asset_state else []

    def restore_trade(self, trade: Trade) -> bool:
        """Restore a persisted trade without recalculating its allocation."""
        asset_state = self.get_asset_state(trade.asset)
        if not asset_state:
            return False

        if trade.status == TradeStatus.OPEN.value:
            if len(asset_state.open_positions) >= self.max_positions:
                return False
            if trade.position_size is None:
                return False
            trade.capital_used = trade.capital_used or trade.position_size
            trade.notional_value = trade.notional_value or (
                trade.capital_used * (trade.leverage or 1.0)
            )
            asset_state.open_positions.append(trade)
        else:
            asset_state.closed_trades.append(trade)
            asset_state.balance += trade.realized_pnl or 0.0

        self._update_performance_stats(asset_state)
        return True
    
    def get_recent_signals(self, symbol: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent signals for an asset"""
        asset_state = self.get_asset_state(symbol)
        if not asset_state:
            return []
        
        return asset_state.signal_history[-limit:] if asset_state.signal_history else []
    
    def add_signal(self, symbol: str, signal_data: Dict[str, Any]) -> None:
        """Add a signal to an asset's history"""
        asset_state = self.get_asset_state(symbol)
        if asset_state:
            signal_data['timestamp'] = datetime.now(timezone.utc).isoformat()
            asset_state.signal_history.append(signal_data)
    
    def _update_performance_stats(self, asset_state: AssetState) -> None:
        """Update performance statistics for an asset"""
        stats = asset_state.performance_stats
        
        # Calculate basic stats from closed trades
        closed_trades = asset_state.closed_trades
        if closed_trades:
            winning_trades = [t for t in closed_trades if t.realized_pnl > 0]
            losing_trades = [t for t in closed_trades if t.realized_pnl < 0]
            
            stats['total_trades'] = len(closed_trades)
            stats['winning_trades'] = len(winning_trades)
            stats['losing_trades'] = len(losing_trades)
            stats['win_rate'] = (len(winning_trades) / len(closed_trades)) * 100 if closed_trades else 0
            
            # Calculate profit factor
            total_profit = sum(t.realized_pnl for t in winning_trades)
            total_loss = abs(sum(t.realized_pnl for t in losing_trades))
            stats['profit_factor'] = (total_profit / total_loss) if total_loss > 0 else 0.0
            
            # Calculate average winner/loser
            stats['average_winner'] = (total_profit / len(winning_trades)) if winning_trades else 0
            stats['average_loser'] = (total_loss / len(losing_trades)) if losing_trades else 0
            
            # Track largest win/loss
            if winning_trades:
                stats['largest_win'] = max(t.realized_pnl for t in winning_trades)
            if losing_trades:
                stats['largest_loss'] = min(t.realized_pnl for t in losing_trades)
            
            # Calculate average trade duration
            if closed_trades:
                total_duration = sum(t.trade_duration for t in closed_trades)
                stats['average_trade_duration'] = total_duration / len(closed_trades)
        
        # Update equity
        total_floating_pnl = sum(t.floating_pnl for t in asset_state.open_positions)
        total_realized_pnl = sum(t.realized_pnl for t in closed_trades)
        stats['total_floating_pnl'] = total_floating_pnl
        stats['total_realized_pnl'] = total_realized_pnl
        stats['current_equity'] = asset_state.balance + total_floating_pnl
        
        # Calculate exposure
        total_position_value = sum(t.position_size for t in asset_state.open_positions)
        stats['current_exposure'] = (total_position_value / asset_state.balance) * 100 if asset_state.balance > 0 else 0
        
        # Update balance and equity in asset state
        asset_state.equity = stats['current_equity']
    
    def round_decimal(self, value: float, decimals: int = 2) -> float:
        """Round decimal value to specified precision"""
        return round_finite(value, decimals) or 0.0

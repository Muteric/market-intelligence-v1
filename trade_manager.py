"""
Trade Manager for AI Trading Intelligence Bot
Manages trade execution, position sizing, and trade lifecycle.
"""

import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal, ROUND_HALF_UP

from configuration_manager import PortfolioConfig, TradingConfig
from asset_manager import AssetManager, Trade, TradeStatus, PositionDirection
from signal_engine import SignalResult

class OrderType(Enum):
    """Order types"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"

class OrderStatus(Enum):
    """Order status"""
    PENDING = "PENDING"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"

@dataclass
class Order:
    """Order data structure"""
    id: str = None
    symbol: str = None
    direction: str = None
    order_type: str = None
    quantity: float = None
    price: float = None
    stop_price: float = None
    status: str = None
    created_time: datetime = None
    filled_time: datetime = None
    
    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4())
        if self.created_time is None:
            self.created_time = datetime.now(timezone.utc)
        if self.status is None:
            self.status = OrderStatus.PENDING.value

@dataclass
class TradeExecution:
    """Trade execution result"""
    order_id: str
    symbol: str
    direction: str
    quantity: float
    price: float
    commission: float
    slippage: float
    execution_time: datetime
    profit_loss: float
    
    def __post_init__(self):
        if self.execution_time is None:
            self.execution_time = datetime.now(timezone.utc)

class TradeManager:
    """Manages trade execution and order processing"""
    
    def __init__(self, asset_manager: AssetManager, portfolio_config: PortfolioConfig, 
                 trading_config: TradingConfig):
        self.asset_manager = asset_manager
        self.portfolio_config = portfolio_config
        self.trading_config = trading_config
        self.orders: Dict[str, Order] = {}
        self.executions: List[TradeExecution] = []
        self.pending_orders: List[Order] = []
    
    def create_order(self, symbol: str, direction: str, order_type: str, 
                    quantity: float = None, price: float = None, 
                    stop_price: float = None) -> Order:
        """Create a new order"""
        order = Order(
            symbol=symbol,
            direction=direction,
            order_type=order_type,
            quantity=quantity,
            price=price,
            stop_price=stop_price
        )
        
        self.orders[order.id] = order
        self.pending_orders.append(order)
        
        return order
    
    def execute_order(self, order_id: str, current_price: float) -> Optional[TradeExecution]:
        """Execute an order at current price"""
        order = self.orders.get(order_id)
        if not order or order.status != OrderStatus.PENDING.value:
            return None
        
        # Calculate execution details
        execution_price = self._calculate_execution_price(order, current_price)
        commission = self._calculate_commission(order, execution_price)
        slippage = self._calculate_slippage(order, execution_price, current_price)
        
        # Create execution
        execution = TradeExecution(
            order_id=order_id,
            symbol=order.symbol,
            direction=order.direction,
            quantity=order.quantity,
            price=execution_price,
            commission=commission,
            slippage=slippage,
            execution_time=datetime.now(timezone.utc),
            profit_loss=0.0  # Will be calculated later
        )
        
        # Update order status
        order.status = OrderStatus.FILLED.value
        order.filled_time = execution.execution_time
        
        # Remove from pending orders
        if order in self.pending_orders:
            self.pending_orders.remove(order)
        
        self.executions.append(execution)
        
        return execution
    
    def calculate_position_size(self, symbol: str, direction: str, 
                               current_price: float) -> float:
        """Calculate position size based on portfolio rules"""
        asset_state = self.asset_manager.get_asset_state(symbol)
        if not asset_state:
            return 0.0
        
        # Get current open positions
        open_positions = asset_state.open_positions
        
        if len(open_positions) == 0:
            # First position: 50% of balance
            position_size = asset_state.balance * self.portfolio_config.base_position_size
        else:
            # Additional positions: 25% of balance
            position_size = asset_state.balance * self.portfolio_config.scaling_position_size
        
        # Calculate number of units
        if direction == PositionDirection.BUY.value:
            units = position_size / current_price
        else:
            units = position_size / current_price
        
        return self._round_decimal(units)
    
    def manage_positions(self, symbol: str, current_price: float) -> Dict[str, Any]:
        """Manage open positions (stop loss, take profit, trailing stop)"""
        asset_state = self.asset_manager.get_asset_state(symbol)
        if not asset_state:
            return {}
        
        actions_taken = []
        positions_closed = []
        
        for trade in asset_state.open_positions[:]:  # Copy list to avoid modification during iteration
            action = self._check_position_exit_conditions(trade, current_price)
            if action:
                closed_trade = self.asset_manager.close_position(
                    symbol, trade.id, current_price, action
                )
                if closed_trade:
                    positions_closed.append(closed_trade)
                    actions_taken.append(f"Closed position {trade.id}: {action}")
        
        return {
            'actions_taken': actions_taken,
            'positions_closed': positions_closed,
            'remaining_positions': len(asset_state.open_positions)
        }
    
    def _calculate_execution_price(self, order: Order, current_price: float) -> float:
        """Calculate execution price based on order type"""
        if order.order_type == OrderType.MARKET.value:
            # Market order executes at current price with small slippage
            return current_price * (1 + (0.0001 if order.direction == PositionDirection.BUY.value else -0.0001))
        elif order.order_type == OrderType.LIMIT.value:
            # Limit order executes at specified price if available
            return order.price if order.price else current_price
        elif order.order_type in [OrderType.STOP.value, OrderType.STOP_LIMIT.value]:
            # Stop order executes when price reaches stop price
            if current_price >= order.stop_price:
                return order.price if order.order_type == OrderType.STOP_LIMIT.value else current_price
            else:
                return 0.0  # Order not triggered
        
        return current_price
    
    def _calculate_commission(self, order: Order, execution_price: float) -> float:
        """Calculate commission for order execution"""
        if execution_price <= 0:
            return 0.0
        
        # Commission is typically a percentage of trade value
        commission_rate = 0.001  # 0.1%
        trade_value = order.quantity * execution_price
        
        return self._round_decimal(trade_value * commission_rate)
    
    def _calculate_slippage(self, order: Order, execution_price: float, 
                           current_price: float) -> float:
        """Calculate slippage for order execution"""
        if execution_price == 0:
            return 0.0
        
        slippage = abs(execution_price - current_price) / current_price
        return self._round_decimal(slippage * 100)  # As percentage
    
    def _check_position_exit_conditions(self, trade: Trade, current_price: float) -> Optional[str]:
        """Check if position should be closed based on exit conditions"""
        if trade.status != TradeStatus.OPEN.value:
            return None
        
        # Check stop loss
        if trade.stop_loss_price and current_price <= trade.stop_loss_price:
            return "STOP_LOSS"
        
        # Check take profit
        if trade.take_profit_price and current_price >= trade.take_profit_price:
            return "TAKE_PROFIT"
        
        # Check trailing stop
        if self.trading_config.trailing_stop_enabled and trade.stop_loss_price:
            # Calculate potential trailing stop based on current price
            if trade.direction == PositionDirection.BUY.value:
                new_stop_loss = current_price * (1 - self.trading_config.trailing_stop_percentage)
            else:
                new_stop_loss = current_price * (1 + self.trading_config.trailing_stop_percentage)
            
            if new_stop_loss > trade.stop_loss_price:
                trade.stop_loss_price = new_stop_loss
                return "TRAILING_STOP"
        
        return None
    
    def get_open_orders(self, symbol: str = None) -> List[Order]:
        """Get open orders, optionally filtered by symbol"""
        if symbol:
            return [order for order in self.pending_orders if order.symbol == symbol]
        return self.pending_orders.copy()
    
    def get_executions(self, symbol: str = None, limit: int = 10) -> List[TradeExecution]:
        """Get execution history, optionally filtered by symbol"""
        if symbol:
            symbol_executions = [e for e in self.executions if e.symbol == symbol]
            return symbol_executions[-limit:] if symbol_executions else []
        return self.executions[-limit:] if self.executions else []
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        order = self.orders.get(order_id)
        if not order or order.status != OrderStatus.PENDING.value:
            return False
        
        order.status = OrderStatus.CANCELLED.value
        
        if order in self.pending_orders:
            self.pending_orders.remove(order)
        
        return True
    
    def get_position_summary(self, symbol: str) -> Dict[str, Any]:
        """Get comprehensive position summary"""
        asset_state = self.asset_manager.get_asset_state(symbol)
        if not asset_state:
            return {}
        
        open_positions = asset_state.open_positions
        closed_trades = asset_state.closed_trades
        
        # Calculate position metrics
        total_position_value = sum(p.position_size for p in open_positions)
        total_floating_pnl = sum(p.floating_pnl for p in open_positions)
        total_realized_pnl = sum(t.realized_pnl for t in closed_trades)
        
        # Calculate average position size
        avg_position_size = (total_position_value / len(open_positions)) if open_positions else 0
        
        # Calculate position distribution by direction
        buy_positions = [p for p in open_positions if p.direction == PositionDirection.BUY.value]
        sell_positions = [p for p in open_positions if p.direction == PositionDirection.SELL.value]
        
        return {
            'symbol': symbol,
            'total_open_positions': len(open_positions),
            'buy_positions': len(buy_positions),
            'sell_positions': len(sell_positions),
            'total_position_value': total_position_value,
            'average_position_size': avg_position_size,
            'total_floating_pnl': total_floating_pnl,
            'total_realized_pnl': total_realized_pnl,
            'net_pnl': total_floating_pnl + total_realized_pnl,
            'win_rate': (len([t for t in closed_trades if t.realized_pnl > 0]) / len(closed_trades)) * 100 if closed_trades else 0,
            'open_orders_count': len([o for o in self.pending_orders if o.symbol == symbol]),
            'recent_executions': self.get_executions(symbol, limit=5)
        }
    
    def _round_decimal(self, value: float, decimals: int = 2) -> float:
        """Round decimal value to specified precision"""
        return float(Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
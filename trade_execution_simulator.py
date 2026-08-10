"""
Trade Execution Simulator for AI Trading Intelligence Bot
Simulates trade execution with PnL calculation, position management, and risk controls.
"""

import asyncio
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from enum import Enum
import uuid
import logging

from configuration_manager import PortfolioConfig, TradingConfig
from asset_manager import AssetManager, Trade, TradeStatus, PositionDirection

logger = logging.getLogger(__name__)

class ExecutionMode(Enum):
    """Execution modes"""
    SIMULATION = "simulation"
    LIVE = "live"
    PAPER = "paper"

@dataclass
class TradeExecution:
    """Trade execution result"""
    trade_id: str
    symbol: str
    direction: str
    entry_price: float
    exit_price: float
    position_size: float
    leverage: float
    entry_time: datetime
    exit_time: datetime
    pnl: float
    pnl_percent: float
    execution_time: float
    slippage: float
    commission: float
    status: str
    execution_type: str

@dataclass
class PortfolioMetrics:
    """Portfolio metrics"""
    total_balance: float
    total_equity: float
    floating_pnl: float
    realized_pnl: float
    net_pnl: float
    win_rate: float
    profit_factor: float
    max_drawdown: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    current_exposure: float
    daily_profit: float
    weekly_profit: float
    monthly_profit: float
    open_positions_count: int
    winning_trades: int
    losing_trades: int
    total_trades: int
    average_winner: float
    average_loser: float
    largest_win: float
    largest_loss: float
    average_trade_duration: float
    recovery_factor: float

@dataclass
class RiskLimits:
    """Risk limits for trading"""
    max_position_size: float
    max_portfolio_exposure: float
    max_daily_loss: float
    max_drawdown: float
    max_correlation: float
    min_account_balance: float
    max_leverage: float

class TradeExecutionSimulator:
    """Trade execution simulator with comprehensive risk management"""
    
    def __init__(self, asset_manager: AssetManager, portfolio_config: PortfolioConfig, 
                 trading_config: TradingConfig):
        self.asset_manager = asset_manager
        self.portfolio_config = portfolio_config
        self.trading_config = trading_config
        self.execution_history: List[TradeExecution] = []
        self.risk_limits = self._initialize_risk_limits()
        self.market_data_cache: Dict[str, Dict[str, Any]] = {}
        self.slippage_model = SlippageModel()
        self.commission_model = CommissionModel()
    
    def execute_trade(self, symbol: str, direction: str, current_price: float, 
                     confidence: float, market_analysis: Any) -> Optional[Trade]:
        """Execute a trade with comprehensive risk checks"""
        logger.info(f"Executing trade for {symbol} - {direction} at {current_price}")
        
        # Check if trade is allowed
        if not self._is_trade_allowed(symbol, direction, current_price, confidence):
            logger.warning(f"Trade not allowed for {symbol} - {direction}")
            return None
        
        # Calculate position size
        position_size = self._calculate_position_size(symbol, current_price, confidence)
        
        # Calculate entry price with slippage
        entry_price = self._calculate_entry_price(current_price, direction, position_size)
        
        # Calculate commission
        commission = self.commission_model.calculate_commission(symbol, position_size, entry_price)
        
        # Create trade
        trade = Trade(
            id=str(uuid.uuid4()),
            asset=symbol,
            direction=direction,
            entry_price=entry_price,
            entry_time=datetime.now(timezone.utc),
            position_size=position_size,
            leverage=self.portfolio_config.leverage,
            stop_loss_price=self._calculate_stop_loss(entry_price, direction, current_price),
            take_profit_price=self._calculate_take_profit(entry_price, direction, current_price),
            status=TradeStatus.OPEN.value
        )
        
        # Add to asset manager
        if self.asset_manager.add_open_position(symbol, trade):
            # Record execution
            execution = TradeExecution(
                trade_id=trade.id,
                symbol=symbol,
                direction=direction,
                entry_price=entry_price,
                exit_price=entry_price,  # Will be updated on exit
                position_size=position_size,
                leverage=self.portfolio_config.leverage,
                entry_time=trade.entry_time,
                exit_time=datetime.now(timezone.utc),
                pnl=0.0,
                pnl_percent=0.0,
                execution_time=0.1,  # Simulated execution time
                slippage=self._calculate_slippage(current_price, entry_price),
                commission=commission,
                status="EXECUTED",
                execution_type="MARKET"
            )
            
            self.execution_history.append(execution)
            
            logger.info(f"Trade executed successfully: {trade.id} - {symbol} {direction} {position_size} @ {entry_price}")
            return trade
        
        return None
    
    def close_trade(self, symbol: str, trade_id: str, current_price: float, 
                   close_reason: str = None) -> Optional[Trade]:
        """Close a trade with PnL calculation"""
        logger.info(f"Closing trade {trade_id} for {symbol} at {current_price}")
        
        # Close trade in asset manager
        closed_trade = self.asset_manager.close_position(symbol, trade_id, current_price, close_reason)
        
        if closed_trade:
            # Update execution record
            for execution in self.execution_history:
                if execution.trade_id == trade_id:
                    execution.exit_price = current_price
                    execution.exit_time = datetime.now(timezone.utc)
                    
                    # Calculate PnL
                    if closed_trade.direction == PositionDirection.BUY.value:
                        execution.pnl = (current_price - closed_trade.entry_price) * closed_trade.position_size
                    else:
                        execution.pnl = (closed_trade.entry_price - current_price) * closed_trade.position_size
                    
                    execution.pnl_percent = (execution.pnl / (closed_trade.position_size * closed_trade.leverage)) * 100 if closed_trade.position_size > 0 else 0
                    
                    execution.status = "CLOSED"
                    break
            
            logger.info(f"Trade closed successfully: {trade_id} - PnL: ${closed_trade.realized_pnl:.2f}")
            return closed_trade
        
        return None
    
    def update_portfolio_metrics(self) -> PortfolioMetrics:
        """Update and return portfolio metrics"""
        all_assets = self.asset_manager.get_all_assets()
        
        total_balance = sum(asset.balance for asset in all_assets.values())
        total_equity = sum(asset.equity for asset in all_assets.values())
        
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
        total_trades = sum(
            len(asset.closed_trades) for asset in all_assets.values()
        )
        
        winning_trades = sum(
            len([trade for trade in asset.closed_trades if trade.realized_pnl > 0])
            for asset in all_assets.values()
        )
        
        losing_trades = total_trades - winning_trades
        
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        # Calculate profit factor
        total_profit = sum(
            trade.realized_pnl for asset in all_assets.values()
            for trade in asset.closed_trades if trade.realized_pnl > 0
        )
        
        total_loss = abs(sum(
            trade.realized_pnl for asset in all_assets.values()
            for trade in asset.closed_trades if trade.realized_pnl < 0
        ))
        
        profit_factor = (total_profit / total_loss) if total_loss > 0 else float('inf')
        
        # Calculate maximum drawdown
        max_drawdown = self._calculate_max_drawdown(all_assets)
        
        # Calculate average winner/loser
        average_winner = (total_profit / winning_trades) if winning_trades > 0 else 0
        average_loser = (total_loss / losing_trades) if losing_trades > 0 else 0
        
        # Calculate largest win/loss
        largest_win = max(
            [trade.realized_pnl for asset in all_assets.values() for trade in asset.closed_trades if trade.realized_pnl > 0],
            default=0
        )
        
        largest_loss = min(
            [trade.realized_pnl for asset in all_assets.values() for trade in asset.closed_trades if trade.realized_pnl < 0],
            default=0
        )
        
        # Calculate average trade duration
        total_duration = sum(
            trade.trade_duration for asset in all_assets.values()
            for trade in asset.closed_trades
        )
        
        average_trade_duration = (total_duration / total_trades) if total_trades > 0 else 0
        
        # Calculate recovery factor
        recovery_factor = (total_equity - total_balance) / abs(max_drawdown) if max_drawdown != 0 else 0
        
        # Calculate current exposure
        total_position_value = sum(
            sum(trade.position_size for trade in asset.open_positions)
            for asset in all_assets.values()
        )
        
        current_exposure = (total_position_value / total_balance * 100) if total_balance > 0 else 0
        
        # Calculate daily/weekly/monthly profit (simplified)
        daily_profit = 0.0
        weekly_profit = 0.0
        monthly_profit = 0.0
        
        return PortfolioMetrics(
            total_balance=total_balance,
            total_equity=total_equity,
            floating_pnl=total_floating_pnl,
            realized_pnl=total_realized_pnl,
            net_pnl=net_pnl,
            win_rate=win_rate,
            profit_factor=profit_factor,
            max_drawdown=max_drawdown,
            sharpe_ratio=0.0,  # Would need more complex calculation
            sortino_ratio=0.0,  # Would need more complex calculation
            calmar_ratio=0.0,  # Would need more complex calculation
            current_exposure=current_exposure,
            daily_profit=daily_profit,
            weekly_profit=weekly_profit,
            monthly_profit=monthly_profit,
            open_positions_count=sum(len(asset.open_positions) for asset in all_assets.values()),
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            total_trades=total_trades,
            average_winner=average_winner,
            average_loser=average_loser,
            largest_win=largest_win,
            largest_loss=largest_loss,
            average_trade_duration=average_trade_duration,
            recovery_factor=recovery_factor
        )
    
    def _is_trade_allowed(self, symbol: str, direction: str, current_price: float, 
                         confidence: float) -> bool:
        """Check if trade is allowed based on various criteria"""
        # Check portfolio metrics
        portfolio_metrics = self.update_portfolio_metrics()
        
        # Check account balance
        if portfolio_metrics.total_balance < self.risk_limits.min_account_balance:
            return False
        
        # Check position limits
        if portfolio_metrics.open_positions_count >= 3:
            return False
        
        # Check confidence threshold
        if confidence < 0.5:
            return False
        
        # Check volatility (avoid trading in high volatility)
        # This would need market data access
        
        # Check correlation (avoid highly correlated positions)
        # This would need correlation matrix
        
        return True
    
    def _calculate_position_size(self, symbol: str, current_price: float, confidence: float) -> float:
        """Calculate position size based on risk management"""
        # Get current portfolio metrics
        portfolio_metrics = self.update_portfolio_metrics()
        
        # Base position size
        if portfolio_metrics.open_positions_count == 0:
            base_size = portfolio_metrics.total_balance * self.portfolio_config.base_position_size
        else:
            base_size = portfolio_metrics.total_balance * self.portfolio_config.scaling_position_size
        
        # Adjust based on confidence
        confidence_multiplier = 0.5 + (confidence * 1.5)  # 0.5 to 2.0
        
        # Adjust based on volatility (simplified)
        volatility_adjustment = 1.0
        
        # Calculate final position size
        position_size = base_size * confidence_multiplier * volatility_adjustment
        
        # Apply risk limits
        position_size = min(position_size, self.risk_limits.max_position_size)
        
        return position_size
    
    def _calculate_entry_price(self, current_price: float, direction: str, position_size: float) -> float:
        """Calculate entry price with slippage"""
        slippage = self.slippage_model.calculate_slippage(position_size, current_price)
        
        if direction == PositionDirection.BUY.value:
            return current_price * (1 + slippage)
        else:
            return current_price * (1 - slippage)
    
    def _calculate_stop_loss(self, entry_price: float, direction: str, current_price: float) -> float:
        """Calculate stop loss price"""
        stop_loss_percentage = self.trading_config.stop_loss_percentage
        
        if direction == PositionDirection.BUY.value:
            return entry_price * (1 - stop_loss_percentage)
        else:
            return entry_price * (1 + stop_loss_percentage)
    
    def _calculate_take_profit(self, entry_price: float, direction: str, current_price: float) -> float:
        """Calculate take profit price"""
        take_profit_percentage = self.trading_config.take_profit_percentage
        
        if direction == PositionDirection.BUY.value:
            return entry_price * (1 + take_profit_percentage)
        else:
            return entry_price * (1 - take_profit_percentage)
    
    def _calculate_slippage(self, current_price: float, entry_price: float) -> float:
        """Calculate slippage amount"""
        return abs(entry_price - current_price) / current_price
    
    def _calculate_max_drawdown(self, all_assets: Dict[str, Any]) -> float:
        """Calculate maximum drawdown"""
        # This would need historical equity curve data
        # For now, return a simplified calculation
        total_equity = sum(asset.equity for asset in all_assets.values())
        total_balance = sum(asset.balance for asset in all_assets.values())
        
        if total_balance == 0:
            return 0.0
        
        return ((total_balance - total_equity) / total_balance) * 100
    
    def _initialize_risk_limits(self) -> RiskLimits:
        """Initialize risk limits"""
        return RiskLimits(
            max_position_size=10000.0,  # Maximum position size in USD
            max_portfolio_exposure=50.0,  # Maximum portfolio exposure percentage
            max_daily_loss=1000.0,  # Maximum daily loss
            max_drawdown=20.0,  # Maximum drawdown percentage
            max_correlation=0.7,  # Maximum correlation between positions
            min_account_balance=100.0,  # Minimum account balance
            max_leverage=100.0  # Maximum leverage
        )

class SlippageModel:
    """Slippage calculation model"""
    
    def calculate_slippage(self, position_size: float, current_price: float) -> float:
        """Calculate slippage based on position size and market conditions"""
        # Base slippage
        base_slippage = 0.001  # 0.1%
        
        # Adjust based on position size
        size_multiplier = min(position_size / 1000.0, 2.0)  # Cap at 2x for large positions
        
        # Adjust based on liquidity (simplified)
        liquidity_factor = 1.0
        
        return base_slippage * size_multiplier * liquidity_factor

class CommissionModel:
    """Commission calculation model"""
    
    def calculate_commission(self, symbol: str, position_size: float, price: float) -> float:
        """Calculate commission for a trade"""
        # Commission rates (simplified)
        commission_rates = {
            'BTCUSD': 0.0005,  # 0.05%
            'XAUUSD': 0.0005,  # 0.05%
            'ETHUSD': 0.0006,  # 0.06%
            'default': 0.001   # 0.1%
        }
        
        rate = commission_rates.get(symbol, commission_rates['default'])
        
        # Calculate commission
        commission = position_size * rate
        
        # Minimum commission
        min_commission = 1.0
        
        return max(commission, min_commission)

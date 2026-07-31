"""
Signal Engine for AI Trading Intelligence Bot
Generates trading signals and manages position logic for each asset.
"""

import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal, ROUND_HALF_UP

from configuration_manager import TradingConfig, AssetConfig
from market_analyzer import MarketAnalysis, TrendDirection, MarketPhase
from asset_manager import AssetManager, Trade, PositionDirection, TradeStatus

class SignalDecision(Enum):
    """Trading signal decisions"""
    STRONG_BUY = "STRONG BUY"
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"
    AVOID_MARKET = "AVOID MARKET"

@dataclass
class SignalResult:
    """Signal generation result"""
    symbol: str
    timestamp: datetime
    decision: str
    confidence: float
    market_analysis: MarketAnalysis
    reasoning: List[str]
    action_taken: str
    positions_opened: int
    positions_closed: int
    new_positions: List[Trade]
    closed_positions: List[Trade]
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)

class SignalEngine:
    """Generates trading signals and manages position logic"""
    
    def __init__(self, asset_manager: AssetManager, trading_config: TradingConfig):
        self.asset_manager = asset_manager
        self.trading_config = trading_config
        self.signal_history: Dict[str, List[SignalResult]] = {}
    
    def generate_signal(self, symbol: str, market_analysis: MarketAnalysis) -> SignalResult:
        """Generate trading signal for an asset"""
        # Get current asset state
        asset_state = self.asset_manager.get_asset_state(symbol)
        if not asset_state:
            raise ValueError(f"Asset {symbol} not found")
        
        # Determine decision based on market analysis
        decision = self._determine_decision(market_analysis)
        
        # Calculate confidence
        confidence = market_analysis.confidence_score
        
        # Determine action based on decision and current positions
        action_taken, new_positions, closed_positions = self._execute_decision(
            symbol, decision, market_analysis.current_price, confidence
        )
        
        # Create signal result
        signal_result = SignalResult(
            symbol=symbol,
            timestamp=datetime.now(timezone.utc),
            decision=decision.value,
            confidence=confidence,
            market_analysis=market_analysis,
            reasoning=market_analysis.reasoning,
            action_taken=action_taken,
            positions_opened=len(new_positions),
            positions_closed=len(closed_positions),
            new_positions=new_positions,
            closed_positions=closed_positions
        )
        
        # Store signal in history
        if symbol not in self.signal_history:
            self.signal_history[symbol] = []
        self.signal_history[symbol].append(signal_result)
        
        # Add signal to asset state
        self._add_signal_to_asset_state(symbol, signal_result)
        
        return signal_result
    
    def _determine_decision(self, market_analysis: MarketAnalysis) -> SignalDecision:
        """Determine trading decision based on market analysis"""
        # Check for avoid market condition
        if market_analysis.volatility_score == "high" and market_analysis.confidence_score < 0.5:
            return SignalDecision.AVOID_MARKET
        
        # Check for strong bullish alignment
        bullish_alignment = (
            market_analysis.trend_direction == TrendDirection.BULLISH.value and
            market_analysis.sentiment_score > 0.0 and
            market_analysis.momentum_score >= 0.5
        )
        
        # Check for strong bearish alignment
        bearish_alignment = (
            market_analysis.trend_direction == TrendDirection.BEARISH.value and
            market_analysis.sentiment_score < 0.0 and
            market_analysis.momentum_score >= 0.5
        )
        
        # Check for moderate bullish
        moderate_bullish = (
            market_analysis.trend_direction == TrendDirection.BULLISH.value and
            market_analysis.sentiment_score >= 0.0 and
            market_analysis.momentum_score >= 0.35 and
            market_analysis.confidence_score >= 0.5
        )
        
        # Check for moderate bearish
        moderate_bearish = (
            market_analysis.trend_direction == TrendDirection.BEARISH.value and
            market_analysis.sentiment_score <= 0.0 and
            market_analysis.momentum_score >= 0.35 and
            market_analysis.confidence_score >= 0.5
        )
        
        # Make decision based on analysis
        if market_analysis.confidence_score > 0.75 and bullish_alignment:
            return SignalDecision.STRONG_BUY
        elif market_analysis.confidence_score > 0.75 and bearish_alignment:
            return SignalDecision.SELL
        elif moderate_bullish:
            return SignalDecision.BUY
        elif moderate_bearish:
            return SignalDecision.SELL
        else:
            return SignalDecision.HOLD
    
    def _execute_decision(self, symbol: str, decision: SignalDecision, 
                        current_price: float, confidence: float) -> Tuple[str, List[Trade], List[Trade]]:
        """Execute trading decision based on signal"""
        asset_state = self.asset_manager.get_asset_state(symbol)
        if not asset_state:
            return "NO ACTION", [], []
        
        open_positions = asset_state.open_positions
        new_positions = []
        closed_positions = []
        
        # Get current decision from asset state
        previous_decision = None
        if asset_state.signal_history:
            previous_decision = asset_state.signal_history[-1].get('decision')
        
        action_taken = "NO ACTION"
        
        if decision == SignalDecision.HOLD:
            action_taken = "HOLD - No action taken"
        
        elif decision == SignalDecision.STRONG_BUY:
            action_taken = self._handle_buy_signal(symbol, open_positions, current_price, new_positions)
        
        elif decision == SignalDecision.BUY:
            action_taken = self._handle_buy_signal(symbol, open_positions, current_price, new_positions)
        
        elif decision == SignalDecision.SELL:
            action_taken = self._handle_sell_signal(symbol, open_positions, current_price, closed_positions)
        
        elif decision == SignalDecision.AVOID_MARKET:
            action_taken = "AVOID MARKET - No trading"
        
        return action_taken, new_positions, closed_positions
    
    def _handle_buy_signal(self, symbol: str, open_positions: List[Trade], 
                          current_price: float, new_positions: List[Trade]) -> str:
        """Handle BUY signal"""
        if len(open_positions) < 3:
            # Open new position
            trade = Trade(
                asset=symbol,
                direction=PositionDirection.BUY.value,
                entry_price=current_price,
                leverage=self.trading_config.leverage,
                status=TradeStatus.OPEN.value
            )
            
            if self.asset_manager.add_open_position(symbol, trade):
                new_positions.append(trade)
                return f"BUY - Opened new position (Total: {len(open_positions) + 1}/3)"
            else:
                return "BUY - Failed to open position (limit reached)"
        else:
            # Use FIFO to close oldest position and open new one
            oldest_position = open_positions[0]
            self.asset_manager.close_position(symbol, oldest_position.id, current_price, "FIFO replacement")
            
            trade = Trade(
                asset=symbol,
                direction=PositionDirection.BUY.value,
                entry_price=current_price,
                leverage=self.trading_config.leverage,
                status=TradeStatus.OPEN.value
            )
            
            if self.asset_manager.add_open_position(symbol, trade):
                new_positions.append(trade)
                return f"BUY - Replaced oldest position (Total: 3/3)"
            else:
                return "BUY - Failed to replace position"
    
    def _handle_sell_signal(self, symbol: str, open_positions: List[Trade], 
                           current_price: float, closed_positions: List[Trade]) -> str:
        """Handle SELL signal"""
        if not open_positions:
            return "SELL - No positions to close"
        
        # Close all BUY positions
        buy_positions = [p for p in open_positions if p.direction == PositionDirection.BUY.value]
        for position in buy_positions:
            closed_trade = self.asset_manager.close_position(symbol, position.id, current_price, "SELL signal")
            if closed_trade:
                closed_positions.append(closed_trade)
        
        # Open new SELL position if needed
        if len(open_positions) < 3:
            trade = Trade(
                asset=symbol,
                direction=PositionDirection.SELL.value,
                entry_price=current_price,
                leverage=self.trading_config.leverage,
                status=TradeStatus.OPEN.value
            )
            
            if self.asset_manager.add_open_position(symbol, trade):
                return f"SELL - Closed {len(buy_positions)} BUY positions, opened new SELL position"
            else:
                return f"SELL - Closed {len(buy_positions)} BUY positions, failed to open new position"
        else:
            return f"SELL - Closed {len(buy_positions)} BUY positions (3 SELL positions maintained)"
    
    def _add_signal_to_asset_state(self, symbol: str, signal_result: SignalResult) -> None:
        """Add signal result to asset state"""
        asset_state = self.asset_manager.get_asset_state(symbol)
        if asset_state:
            signal_data = {
                'decision': signal_result.decision,
                'confidence': signal_result.confidence,
                'timestamp': signal_result.timestamp.isoformat(),
                'action_taken': signal_result.action_taken,
                'positions_opened': signal_result.positions_opened,
                'positions_closed': signal_result.positions_closed
            }
            asset_state.signal_history.append(signal_data)
    
    def get_signal_history(self, symbol: str, limit: int = 10) -> List[SignalResult]:
        """Get signal history for an asset"""
        if symbol not in self.signal_history:
            return []
        
        return self.signal_history[symbol][-limit:] if self.signal_history[symbol] else []
    
    def get_current_positions(self, symbol: str) -> List[Trade]:
        """Get current open positions for an asset"""
        return self.asset_manager.get_open_positions(symbol)
    
    def get_position_summary(self, symbol: str) -> Dict[str, Any]:
        """Get position summary for an asset"""
        asset_state = self.asset_manager.get_asset_state(symbol)
        if not asset_state:
            return {}
        
        open_positions = asset_state.open_positions
        closed_trades = asset_state.closed_trades
        
        # Calculate summary
        total_open_value = sum(p.position_size for p in open_positions)
        total_floating_pnl = sum(p.floating_pnl for p in open_positions)
        total_realized_pnl = sum(t.realized_pnl for t in closed_trades)
        
        return {
            'symbol': symbol,
            'open_positions_count': len(open_positions),
            'closed_trades_count': len(closed_trades),
            'total_open_value': total_open_value,
            'total_floating_pnl': total_floating_pnl,
            'total_realized_pnl': total_realized_pnl,
            'current_equity': asset_state.equity,
            'balance': asset_state.balance
        }
    
    def round_decimal(self, value: float, decimals: int = 2) -> float:
        """Round decimal value to specified precision"""
        return float(Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
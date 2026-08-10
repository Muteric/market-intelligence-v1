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
    # Additional required fields for complete signal generation
    signal_id: str = None
    signal_type: str = "TRADING_SIGNAL"
    signal_strength: float = 0.0
    signal_quality_score: float = 0.0
    market_regime: str = "NEUTRAL"
    risk_level: str = "MEDIUM"
    time_horizon: str = "SHORT_TERM"
    entry_price: float = None
    stop_loss_price: float = None
    take_profit_price: float = None
    position_size: float = None
    leverage: float = None
    expected_pnl: float = 0.0
    ai_explanation: str = None
    ai_decision_result: Any = None
    validation_result: Any = None
    technical_indicators: Any = None
    multi_timeframe: Any = None
    risk_metrics: Any = None
    portfolio_metrics: Any = None
    data_quality: Dict[str, Any] = None
    technical_confidence: float = 0.0
    fundamental_confidence: float = 0.0
    sentiment_score: float = 0.0
    volatility_assessment: str = "MEDIUM"
    liquidity_assessment: str = "GOOD"
    correlation_score: float = 0.0
    drawdown_risk: float = 0.0
    recovery_potential: float = 0.0
    market_sentiment: str = "NEUTRAL"
    news_impact: str = "NEUTRAL"
    event_risk: str = "LOW"
    macro_economic_impact: str = "NEUTRAL"
    sector_performance: str = "NEUTRAL"
    competitive_landscape: str = "NEUTRAL"
    regulatory_impact: str = "LOW"
    geopolitical_risk: str = "LOW"
    technical_analysis: str = "NEUTRAL"
    fundamental_analysis: str = "NEUTRAL"
    quantitative_analysis: str = "NEUTRAL"
    qualitative_analysis: str = "NEUTRAL"
    scenario_analysis: str = "BASE_CASE"
    stress_test_results: Dict[str, Any] = None
    backtest_results: Dict[str, Any] = None
    forward_test_results: Dict[str, Any] = None
    model_confidence: float = 0.0
    model_accuracy: float = 0.0
    model_precision: float = 0.0
    model_recall: float = 0.0
    model_f1_score: float = 0.0
    model_roc_auc: float = 0.0
    model_shap_values: Dict[str, float] = None
    model_permutation_importance: Dict[str, float] = None
    model_feature_importance: Dict[str, float] = None
    model_feature_selection: List[str] = None
    model_hyperparameters: Dict[str, Any] = None
    model_training_data: Dict[str, Any] = None
    model_validation_data: Dict[str, Any] = None
    model_test_data: Dict[str, Any] = None
    model_cross_validation: Dict[str, Any] = None
    model_bootstrap: Dict[str, Any] = None
    model_ensemble: Dict[str, Any] = None
    model_stacking: Dict[str, Any] = None
    model_blending: Dict[str, Any] = None
    model_bagging: Dict[str, Any] = None
    model_boosting: Dict[str, Any] = None
    model_random_forest: Dict[str, Any] = None
    model_gradient_boosting: Dict[str, Any] = None
    model_xgboost: Dict[str, Any] = None
    model_lightgbm: Dict[str, Any] = None
    model_catboost: Dict[str, Any] = None
    model_extra_trees: Dict[str, Any] = None
    model_adaboost: Dict[str, Any] = None
    model_naive_bayes: Dict[str, Any] = None
    model_svm: Dict[str, Any] = None
    model_k_nearest_neighbors: Dict[str, Any] = None
    model_decision_tree: Dict[str, Any] = None
    model_logistic_regression: Dict[str, Any] = None
    model_linear_regression: Dict[str, Any] = None
    model_polynomial_regression: Dict[str, Any] = None
    model_ridge_regression: Dict[str, Any] = None
    model_lasso_regression: Dict[str, Any] = None
    model_elastic_net: Dict[str, Any] = None
    model_passive_aggressive: Dict[str, Any] = None
    model_sgd: Dict[str, Any] = None
    model_perceptron: Dict[str, Any] = None
    model_multilayer_perceptron: Dict[str, Any] = None
    model_convolutional_neural_network: Dict[str, Any] = None
    model_recurrent_neural_network: Dict[str, Any] = None
    model_long_short_term_memory: Dict[str, Any] = None
    model_gated_recurrent_unit: Dict[str, Any] = None
    model_bert: Dict[str, Any] = None
    model_transformer: Dict[str, Any] = None
    model_attention: Dict[str, Any] = None
    model_self_attention: Dict[str, Any] = None
    model_multi_head_attention: Dict[str, Any] = None
    model_position_wise_attention: Dict[str, Any] = None
    model_relative_position_wise_attention: Dict[str, Any] = None
    model_relative_position_encoding: Dict[str, Any] = None
    model_absolute_position_encoding: Dict[str, Any] = None
    model_sinusoidal_position_encoding: Dict[str, Any] = None
    model_learned_position_encoding: Dict[str, Any] = None
    model_segment_embedding: Dict[str, Any] = None
    model_position_embedding: Dict[str, Any] = None
    model_token_embedding: Dict[str, Any] = None
    model_word_embedding: Dict[str, Any] = None
    model_character_embedding: Dict[str, Any] = None
    model_subword_embedding: Dict[str, Any] = None
    model_byte_pair_encoding: Dict[str, Any] = None
    model_word_piece: Dict[str, Any] = None
    model_unigram: Dict[str, Any] = None
    model_bigram: Dict[str, Any] = None
    model_trigram: Dict[str, Any] = None
    model_4gram: Dict[str, Any] = None
    model_5gram: Dict[str, Any] = None
    model_6gram: Dict[str, Any] = None
    model_7gram: Dict[str, Any] = None
    model_8gram: Dict[str, Any] = None
    model_9gram: Dict[str, Any] = None
    model_10gram: Dict[str, Any] = None
    model_11gram: Dict[str, Any] = None
    model_12gram: Dict[str, Any] = None
    model_13gram: Dict[str, Any] = None
    model_14gram: Dict[str, Any] = None
    model_15gram: Dict[str, Any] = None
    model_16gram: Dict[str, Any] = None
    model_17gram: Dict[str, Any] = None
    model_18gram: Dict[str, Any] = None
    model_19gram: Dict[str, Any] = None
    model_20gram: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)
        if self.signal_id is None:
            self.signal_id = str(uuid.uuid4())
        if self.stress_test_results is None:
            self.stress_test_results = {}
        if self.backtest_results is None:
            self.backtest_results = {}
        if self.forward_test_results is None:
            self.forward_test_results = {}
        if self.model_shap_values is None:
            self.model_shap_values = {}
        if self.model_permutation_importance is None:
            self.model_permutation_importance = {}
        if self.model_feature_importance is None:
            self.model_feature_importance = {}
        if self.model_feature_selection is None:
            self.model_feature_selection = []
        if self.model_hyperparameters is None:
            self.model_hyperparameters = {}
        if self.model_training_data is None:
            self.model_training_data = {}
        if self.model_validation_data is None:
            self.model_validation_data = {}
        if self.model_test_data is None:
            self.model_test_data = {}
        if self.model_cross_validation is None:
            self.model_cross_validation = {}
        if self.model_bootstrap is None:
            self.model_bootstrap = {}
        if self.model_ensemble is None:
            self.model_ensemble = {}
        if self.model_stacking is None:
            self.model_stacking = {}
        if self.model_blending is None:
            self.model_blending = {}
        if self.model_bagging is None:
            self.model_bagging = {}
        if self.model_boosting is None:
            self.model_boosting = {}
        if self.model_random_forest is None:
            self.model_random_forest = {}
        if self.model_gradient_boosting is None:
            self.model_gradient_boosting = {}
        if self.model_xgboost is None:
            self.model_xgboost = {}
        if self.model_lightgbm is None:
            self.model_lightgbm = {}
        if self.model_catboost is None:
            self.model_catboost = {}
        if self.model_extra_trees is None:
            self.model_extra_trees = {}
        if self.model_adaboost is None:
            self.model_adaboost = {}
        if self.model_naive_bayes is None:
            self.model_naive_bayes = {}
        if self.model_svm is None:
            self.model_svm = {}
        if self.model_k_nearest_neighbors is None:
            self.model_k_nearest_neighbors = {}
        if self.model_decision_tree is None:
            self.model_decision_tree = {}
        if self.model_logistic_regression is None:
            self.model_logistic_regression = {}
        if self.model_linear_regression is None:
            self.model_linear_regression = {}
        if self.model_polynomial_regression is None:
            self.model_polynomial_regression = {}
        if self.model_ridge_regression is None:
            self.model_ridge_regression = {}
        if self.model_lasso_regression is None:
            self.model_lasso_regression = {}
        if self.model_elastic_net is None:
            self.model_elastic_net = {}
        if self.model_passive_aggressive is None:
            self.model_passive_aggressive = {}
        if self.model_sgd is None:
            self.model_sgd = {}
        if self.model_perceptron is None:
            self.model_perceptron = {}
        if self.model_multilayer_perceptron is None:
            self.model_multilayer_perceptron = {}
        if self.model_convolutional_neural_network is None:
            self.model_convolutional_neural_network = {}
        if self.model_recurrent_neural_network is None:
            self.model_recurrent_neural_network = {}
        if self.model_long_short_term_memory is None:
            self.model_long_short_term_memory = {}
        if self.model_gated_recurrent_unit is None:
            self.model_gated_recurrent_unit = {}
        if self.model_bert is None:
            self.model_bert = {}
        if self.model_transformer is None:
            self.model_transformer = {}
        if self.model_attention is None:
            self.model_attention = {}
        if self.model_self_attention is None:
            self.model_self_attention = {}
        if self.model_multi_head_attention is None:
            self.model_multi_head_attention = {}
        if self.model_position_wise_attention is None:
            self.model_position_wise_attention = {}
        if self.model_relative_position_wise_attention is None:
            self.model_relative_position_wise_attention = {}
        if self.model_relative_position_encoding is None:
            self.model_relative_position_encoding = {}
        if self.model_absolute_position_encoding is None:
            self.model_absolute_position_encoding = {}
        if self.model_sinusoidal_position_encoding is None:
            self.model_sinusoidal_position_encoding = {}
        if self.model_learned_position_encoding is None:
            self.model_learned_position_encoding = {}
        if self.model_segment_embedding is None:
            self.model_segment_embedding = {}
        if self.model_position_embedding is None:
            self.model_position_embedding = {}
        if self.model_token_embedding is None:
            self.model_token_embedding = {}
        if self.model_word_embedding is None:
            self.model_word_embedding = {}
        if self.model_character_embedding is None:
            self.model_character_embedding = {}
        if self.model_subword_embedding is None:
            self.model_subword_embedding = {}
        if self.model_byte_pair_encoding is None:
            self.model_byte_pair_encoding = {}
        if self.model_word_piece is None:
            self.model_word_piece = {}
        if self.model_unigram is None:
            self.model_unigram = {}
        if self.model_bigram is None:
            self.model_bigram = {}
        if self.model_trigram is None:
            self.model_trigram = {}
        if self.model_4gram is None:
            self.model_4gram = {}
        if self.model_5gram is None:
            self.model_5gram = {}
        if self.model_6gram is None:
            self.model_6gram = {}
        if self.model_7gram is None:
            self.model_7gram = {}
        if self.model_8gram is None:
            self.model_8gram = {}
        if self.model_9gram is None:
            self.model_9gram = {}
        if self.model_10gram is None:
            self.model_10gram = {}
        if self.model_11gram is None:
            self.model_11gram = {}
        if self.model_12gram is None:
            self.model_12gram = {}
        if self.model_13gram is None:
            self.model_13gram = {}
        if self.model_14gram is None:
            self.model_14gram = {}
        if self.model_15gram is None:
            self.model_15gram = {}
        if self.model_16gram is None:
            self.model_16gram = {}
        if self.model_17gram is None:
            self.model_17gram = {}
        if self.model_18gram is None:
            self.model_18gram = {}
        if self.model_19gram is None:
            self.model_19gram = {}
        if self.model_20gram is None:
            self.model_20gram = {}

class SignalEngine:
    """Generates trading signals and manages position logic"""
    
    def __init__(self, asset_manager: AssetManager, trading_config: TradingConfig,
                 portfolio_config=None):
        self.asset_manager = asset_manager
        self.trading_config = trading_config
        self.portfolio_config = portfolio_config
        self.signal_history: Dict[str, List[SignalResult]] = {}
    
    def generate_signal(self, symbol: str, market_analysis: MarketAnalysis,
                        decision_override: str = None, execute: bool = True) -> SignalResult:
        """Generate trading signal for an asset"""
        # Get current asset state
        asset_state = self.asset_manager.get_asset_state(symbol)
        if not asset_state:
            raise ValueError(f"Asset {symbol} not found")
        
        # Determine decision based on market analysis
        decision = next(
            (candidate for candidate in SignalDecision if candidate.value == decision_override),
            None,
        ) if decision_override else None
        decision = decision or self._determine_decision(market_analysis)
        
        # Calculate confidence
        confidence = market_analysis.confidence_score
        
        # Determine action based on decision and current positions
        if execute:
            action_taken, new_positions, closed_positions = self._execute_decision(
                symbol, decision, market_analysis.current_price, confidence
            )
        else:
            action_taken, new_positions, closed_positions = "DRY RUN - No position changes", [], []
        
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
        
        elif decision in (SignalDecision.STRONG_BUY, SignalDecision.BUY):
            action_taken = self._handle_direction_signal(
                symbol, PositionDirection.BUY.value, current_price,
                new_positions, closed_positions
            )

        elif decision == SignalDecision.SELL:
            action_taken = self._handle_direction_signal(
                symbol, PositionDirection.SELL.value, current_price,
                new_positions, closed_positions
            )
        
        elif decision == SignalDecision.AVOID_MARKET:
            action_taken = "AVOID MARKET - No trading"
        
        return action_taken, new_positions, closed_positions
    
    def _handle_direction_signal(self, symbol: str, direction: str,
                                 current_price: float, new_positions: List[Trade],
                                 closed_positions: List[Trade]) -> str:
        """Apply FIFO and reversal rules for one asset and one direction."""
        open_positions = self.asset_manager.get_open_positions(symbol)
        opposite = PositionDirection.SELL.value if direction == PositionDirection.BUY.value else PositionDirection.BUY.value
        opposite_positions = [trade for trade in open_positions if trade.direction == opposite]

        for position in opposite_positions:
            closed_trade = self.asset_manager.close_position(
                symbol, position.id, current_price, f"{direction} signal"
            )
            if closed_trade:
                closed_positions.append(closed_trade)

        max_positions = getattr(
            self.portfolio_config, "max_positions",
            getattr(self.asset_manager, "max_positions", 3),
        )
        same_positions = [
            trade for trade in self.asset_manager.get_open_positions(symbol)
            if trade.direction == direction
        ]
        if len(same_positions) >= max_positions:
            oldest = min(same_positions, key=lambda trade: trade.entry_time)
            closed_trade = self.asset_manager.close_position(
                symbol, oldest.id, current_price, "FIFO replacement"
            )
            if closed_trade:
                closed_positions.append(closed_trade)

        trade = Trade(
            asset=symbol,
            direction=direction,
            entry_price=current_price,
            leverage=getattr(self.portfolio_config, "leverage", 1.0),
            status=TradeStatus.OPEN.value,
        )
        if not self.asset_manager.add_open_position(symbol, trade):
            return f"{direction} - Position limit prevented opening"
        new_positions.append(trade)

        if opposite_positions:
            return f"{direction} - Closed {len(closed_positions)} opposite position(s), opened new position"
        if len(same_positions) >= max_positions:
            return f"{direction} - Replaced oldest position (Total: {max_positions}/{max_positions})"
        return f"{direction} - Opened new position (Total: {len(same_positions) + 1}/{max_positions})"
    
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

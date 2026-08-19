"""
AI Decision Engine for AI Trading Intelligence Bot
Enhanced AI decision engine with comprehensive synthesis of market data, technical indicators, and portfolio state.
"""

import asyncio
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import math
import logging

from configuration_manager import TradingConfig, PortfolioConfig
from market_analyzer import MarketAnalysis
from portfolio_manager import PortfolioManager, PortfolioMetrics
from risk_calculator import RiskCalculator
from performance_tracker import (
    PerformanceTracker,
    PerformanceMetricType,
    PerformancePeriod,
    PerformanceBenchmark,
)
from technical_indicators import TechnicalIndicatorsResult
from market_regime_detector import (
    MarketRegimeDetector,
    MarketRegimeResult,
)
from multi_timeframe_analyzer import MultiTimeframeResult
from asset_manager import AssetManager, Trade, PositionDirection, TradeStatus
from signal_engine import SignalDecision

logger = logging.getLogger(__name__)

# Compatibility aliases keep existing imports working without defining duplicate models.
MarketRegime = MarketRegimeResult
RiskMetrics = __import__("risk_calculator").RiskMetrics
PortfolioState = PortfolioMetrics

@dataclass
class AIDecisionResult:
    """Complete AI decision result"""
    symbol: str
    timestamp: datetime
    decision: str
    confidence_score: float
    confidence_explanation: str
    trade_quality_score: float
    market_narrative: str
    recommended_action: str
    consensus_market_price: float
    previous_analysis_price: float
    price_change: float
    price_change_percent: float
    trend: str
    momentum: float
    volatility: str
    market_regime: MarketRegimeResult
    risk_metrics: RiskMetrics
    portfolio_state: PortfolioMetrics
    technical_indicators: TechnicalIndicatorsResult
    multi_timeframe: MultiTimeframeResult
    open_trades: List[Trade]
    historical_performance: Dict[str, Any]
    signal_accuracy: float
    ai_explanation: str
    confidence_reasons: List[str] = None
    pattern_evidence: Dict[str, Any] = None
    signal_score: float = 0.0
    trade_candidate: Any = None

class AIDecisionEngine:
    """Enhanced AI decision engine with comprehensive market analysis"""
    
    def __init__(self, asset_manager: AssetManager, trading_config: TradingConfig,
                 portfolio_config: PortfolioConfig = None,
                 performance_tracker: PerformanceTracker = None):
        self.asset_manager = asset_manager
        self.trading_config = trading_config
        self.portfolio_config = portfolio_config or PortfolioConfig()
        self.market_regime_detector = MarketRegimeDetector()
        self.risk_calculator = RiskCalculator(
            account_balance=self.portfolio_config.initial_balance,
            leverage=self.portfolio_config.leverage,
        )
        self.portfolio_manager = PortfolioManager(
            asset_manager, self.portfolio_config, trading_config
        )
        self.performance_tracker = performance_tracker or PerformanceTracker(
            asset_manager, self.portfolio_config
        )
    
    def generate_decision(self, symbol: str, market_analysis: MarketAnalysis, 
                         technical_indicators: TechnicalIndicatorsResult,
                         multi_timeframe: MultiTimeframeResult,
                         current_price: float, previous_price: float,
                         data_confidence: float = 1.0) -> AIDecisionResult:
        """Generate comprehensive AI trading decision"""
        logger.info(f"Generating AI decision for {symbol}")
        
        # Calculate portfolio state
        metrics = self.portfolio_manager.update_portfolio()
        
        # Detect market regime
        market_regime = self.market_regime_detector.detect_regime(symbol, market_analysis, technical_indicators)
        
        # Calculate risk metrics
        asset_state = self.asset_manager.get_asset_state(symbol)
        self.risk_calculator.account_balance = (
            asset_state.balance if asset_state else self.portfolio_config.initial_balance
        )
        risk_metrics = self.risk_calculator.calculate_risk_metrics(
            symbol, market_analysis, technical_indicators,
            direction=market_analysis.trend_direction,
        )
        
        # Synthesize market data
        consensus_market_price = self._calculate_consensus_price(symbol, current_price, previous_price)
        price_change = current_price - previous_price
        price_change_percent = (price_change / previous_price * 100) if previous_price > 0 else 0
        
        # Determine trend and momentum
        trend = self._determine_trend(market_analysis, technical_indicators, multi_timeframe)
        momentum = self._calculate_momentum(market_analysis, technical_indicators, multi_timeframe)
        
        # Generate AI decision
        decision = self._make_ai_decision(
            symbol, market_analysis, technical_indicators, multi_timeframe,
           metrics , market_regime, risk_metrics
        )
        if data_confidence < 0.4:
            decision = SignalDecision.HOLD.value
        
        # Calculate confidence scores
        confidence_score = self._calculate_confidence_score(
            symbol, market_analysis, technical_indicators, multi_timeframe,
            metrics, market_regime, risk_metrics, decision
        )
        confidence_score = min(confidence_score, max(0.0, min(1.0, data_confidence)))
        
        confidence_explanation = self._generate_confidence_explanation(
            symbol, market_analysis, technical_indicators, multi_timeframe,
            metrics, market_regime, risk_metrics, decision, confidence_score
        )
        
        # Calculate trade quality score
        trade_quality_score = self._calculate_trade_quality_score(
            symbol, decision, market_analysis, technical_indicators,metrics 
        )
        
        # Generate market narrative
        market_narrative = self._generate_market_narrative(
            symbol, market_analysis, technical_indicators, multi_timeframe,
            metrics, market_regime
        )
        
        # Generate AI explanation
        ai_explanation = self._generate_ai_explanation(
            symbol, market_analysis, technical_indicators, multi_timeframe,
           metrics, market_regime, risk_metrics, decision
        )
        
        # Get open trades
        open_trades = self.asset_manager.get_open_positions(symbol)
        
        # Get historical performance
        historical_performance = self.performance_tracker.get_historical_performance(symbol)
        
        # Get signal accuracy
        signal_accuracy = self.performance_tracker.get_signal_accuracy(symbol)
        pattern_evidence = self._pattern_evidence(multi_timeframe)
        if pattern_evidence["bullish"] and pattern_evidence["bearish"]:
            confidence_explanation += "; conflicting chart-pattern evidence"
        elif pattern_evidence["bullish"] and decision == SignalDecision.BUY.value:
            confidence_explanation += "; confirmed bullish chart-pattern evidence"
        elif pattern_evidence["bearish"] and decision == SignalDecision.SELL.value:
            confidence_explanation += "; confirmed bearish chart-pattern evidence"
        
        return AIDecisionResult(
            symbol=symbol,
            timestamp=datetime.now(timezone.utc),
            decision=decision,
            confidence_score=confidence_score,
            confidence_explanation=confidence_explanation,
            trade_quality_score=trade_quality_score,
            market_narrative=market_narrative,
            recommended_action=self._generate_recommended_action(decision, trade_quality_score, confidence_score),
            consensus_market_price=consensus_market_price,
            previous_analysis_price=previous_price,
            price_change=price_change,
            price_change_percent=price_change_percent,
            trend=trend,
            momentum=momentum,
            volatility=market_analysis.volatility_score,
            market_regime=market_regime,
            risk_metrics=risk_metrics,
            portfolio_state=metrics,
            technical_indicators=technical_indicators,
            multi_timeframe=multi_timeframe,
            open_trades=open_trades,
            historical_performance=historical_performance,
            signal_accuracy=signal_accuracy,
            ai_explanation=ai_explanation,
            confidence_reasons=[confidence_explanation],
            pattern_evidence=pattern_evidence
        )

    @staticmethod
    def _pattern_evidence(multi_timeframe: MultiTimeframeResult) -> Dict[str, Any]:
        patterns = getattr(multi_timeframe, "patterns", None) or {}
        bullish, bearish = [], []
        for timeframe_patterns in patterns.values():
            for pattern in timeframe_patterns or []:
                direction = pattern.get("direction") if isinstance(pattern, dict) else getattr(pattern, "direction", "")
                if direction == "bullish":
                    bullish.append(pattern)
                elif direction == "bearish":
                    bearish.append(pattern)
        return {"bullish": bullish, "bearish": bearish, "count": len(bullish) + len(bearish)}
    
    def _calculate_consensus_price(self, symbol: str, current_price: float, previous_price: float) -> float:
        """Calculate consensus market price"""
        # In production, this would use market data aggregator results
        # For now, use current price with some smoothing
        return current_price
    
    def _determine_trend(self, market_analysis: MarketAnalysis, 
                        technical_indicators: TechnicalIndicatorsResult,
                        multi_timeframe: MultiTimeframeResult) -> str:
        """Determine overall trend from multiple sources"""
        # Weight different trend sources
        trend_scores = {}
        
        # Market analysis trend
        if market_analysis.trend_direction == "bullish":
            trend_scores['market_analysis'] = 1.0
        elif market_analysis.trend_direction == "bearish":
            trend_scores['market_analysis'] = -1.0
        else:
            trend_scores['market_analysis'] = 0.0
        
        # Technical indicators trend
        if technical_indicators.overall_trend == "bullish":
            trend_scores['technical'] = 1.0
        elif technical_indicators.overall_trend == "bearish":
            trend_scores['technical'] = -1.0
        else:
            trend_scores['technical'] = 0.0
        
        # Multi-timeframe trend
        if multi_timeframe.overall_signal == "BUY":
            trend_scores['multi_timeframe'] = 1.0
        elif multi_timeframe.overall_signal == "SELL":
            trend_scores['multi_timeframe'] = -1.0
        else:
            trend_scores['multi_timeframe'] = 0.0
        
        # Calculate weighted average
        total_score = sum(trend_scores.values())
        if total_score > 0.5:
            return "bullish"
        elif total_score < -0.5:
            return "bearish"
        else:
            return "neutral"
    
    def _calculate_momentum(self, market_analysis: MarketAnalysis,
                           technical_indicators: TechnicalIndicatorsResult,
                           multi_timeframe: MultiTimeframeResult) -> float:
        """Calculate overall momentum score"""
        # Weight different momentum sources
        momentum_scores = []
        
        # Market analysis momentum
        momentum_scores.append(market_analysis.momentum_score)
        
        # Technical indicators momentum
        momentum_scores.append(technical_indicators.momentum_score)
        
        # Multi-timeframe momentum
        momentum_scores.append(multi_timeframe.momentum_alignment)
        
        # Calculate average
        return sum(momentum_scores) / len(momentum_scores) if momentum_scores else 0.0
    
    def _make_ai_decision(self, symbol: str, market_analysis: MarketAnalysis,
                         technical_indicators: TechnicalIndicatorsResult,
                         multi_timeframe: MultiTimeframeResult,
                         portfolio_state: PortfolioState,
                         market_regime: MarketRegime,
                         risk_metrics: RiskMetrics) -> str:
        """Make final AI decision based on all factors"""
        # Check for high-confidence conditions
        if self._is_high_confidence_buy_condition(symbol, market_analysis, 
                                                 technical_indicators, multi_timeframe,
                                                 portfolio_state, market_regime, risk_metrics):
            return SignalDecision.BUY.value
        
        if self._is_high_confidence_sell_condition(symbol, market_analysis,
                                                  technical_indicators, multi_timeframe,
                                                  portfolio_state, market_regime, risk_metrics):
            return SignalDecision.SELL.value
        
        # Check for hold conditions
        if self._is_hold_condition(symbol, market_analysis,
                                  technical_indicators, multi_timeframe,
                                  portfolio_state, market_regime, risk_metrics):
            return SignalDecision.HOLD.value
        
        # Default to hold
        return SignalDecision.HOLD.value
    
    def _is_high_confidence_buy_condition(self, symbol: str, market_analysis: MarketAnalysis,
                                         technical_indicators: TechnicalIndicatorsResult,
                                         multi_timeframe: MultiTimeframeResult,
                                         portfolio_state: PortfolioState,
                                         market_regime: MarketRegime,
                                         risk_metrics: RiskMetrics) -> bool:
        """Check if conditions are met for high-confidence BUY signal"""
        # Multiple timeframes must be aligned
        if multi_timeframe.trend_alignment not in ["BULLISH_ALIGNMENT", "BEARISH_ALIGNMENT"]:
            return False
        
        # Market analysis must be bullish
        if market_analysis.trend_direction != "bullish":
            return False
        
        # Technical indicators must be bullish
        if technical_indicators.overall_trend != "bullish":
            return False
        
        # RSI must not be overbought (avoid buying at peak)
        if technical_indicators.rsi.overbought:
            return False
        
        # Momentum must be positive
        if self._calculate_momentum(market_analysis, technical_indicators, multi_timeframe) <= 0:
            return False
        
        # Risk metrics must be acceptable
        if risk_metrics.overall_risk_score > 0.7:
            return False
        
        # Portfolio must have capacity for new positions
        if portfolio_state.open_positions_count >= 3:
            return False
        
        # Market regime must be favorable
        if market_regime.regime.value in ["High Volatility", "Capitulation", "Low Liquidity"]:
            return False
        
        return True
    
    def _is_high_confidence_sell_condition(self, symbol: str, market_analysis: MarketAnalysis,
                                          technical_indicators: TechnicalIndicatorsResult,
                                          multi_timeframe: MultiTimeframeResult,
                                          portfolio_state: PortfolioState,
                                          market_regime: MarketRegime,
                                          risk_metrics: RiskMetrics) -> bool:
        """Check if conditions are met for high-confidence SELL signal"""
        # Multiple timeframes must be aligned
        if multi_timeframe.trend_alignment not in ["BULLISH_ALIGNMENT", "BEARISH_ALIGNMENT"]:
            return False
        
        # Market analysis must be bearish
        if market_analysis.trend_direction != "bearish":
            return False
        
        # Technical indicators must be bearish
        if technical_indicators.overall_trend != "bearish":
            return False
        
        # Stochastic must be oversold (avoid selling at bottom)
        if technical_indicators.stochastic.oversold:
            return False
        
        # Momentum must be negative
        if self._calculate_momentum(market_analysis, technical_indicators, multi_timeframe) >= 0:
            return False
        
        # Risk metrics must be acceptable
        if risk_metrics.overall_risk_score > 0.7:
            return False
        
        # Market regime must be unfavorable
        if market_regime.regime.value in ["Strong Trending", "Expansion"]:
            return False
        
        return True
    
    def _is_hold_condition(self, symbol: str, market_analysis: MarketAnalysis,
                          technical_indicators: TechnicalIndicatorsResult,
                          multi_timeframe: MultiTimeframeResult,
                          portfolio_state: PortfolioState,
                          market_regime: MarketRegime,
                          risk_metrics: RiskMetrics) -> bool:
        """Check if conditions are met for HOLD signal"""
        # Mixed alignment across timeframes
        if multi_timeframe.trend_alignment == "MIXED_ALIGNMENT":
            return True
        
        # Neutral trend
        if market_analysis.trend_direction == "neutral":
            return True
        
        # High volatility
        if market_analysis.volatility_score == "high":
            return True
        
        # Market regime is uncertain
        if market_regime.regime.value in ["Neutral", "Consolidation", "Range Bound"]:
            return True
        
        # Risk metrics are too high
        if risk_metrics.overall_risk_score > 0.8:
            return True
        
        # Portfolio is at maximum capacity
        if portfolio_state.open_positions_count >= 3:
            return True
        
        return False
    
    def _calculate_confidence_score(self, symbol: str, market_analysis: MarketAnalysis,
                                   technical_indicators: TechnicalIndicatorsResult,
                                   multi_timeframe: MultiTimeframeResult,
                                   portfolio_state: PortfolioState,
                                   market_regime: MarketRegime,
                                   risk_metrics: RiskMetrics,
                                   decision: str) -> float:
        """Calculate confidence score for the decision"""
        confidence = 0.5  # Base confidence
        
        # Adjust based on trend alignment
        if multi_timeframe.trend_alignment in ["BULLISH_ALIGNMENT", "BEARISH_ALIGNMENT"]:
            confidence += 0.3
        elif multi_timeframe.trend_alignment == "MIXED_ALIGNMENT":
            confidence -= 0.2
        
        # Adjust based on trend strength
        confidence += multi_timeframe.trend_strength * 0.2
        
        # Adjust based on momentum alignment
        confidence += abs(multi_timeframe.momentum_alignment) * 0.15
        
        # Adjust based on market regime
        if market_regime.regime.value in ["Strong Trending", "Strong Bearish"]:
            confidence += 0.2
        elif market_regime.regime.value in ["High Volatility", "Capitulation"]:
            confidence -= 0.3
        
        # Adjust based on risk metrics
        confidence -= risk_metrics.overall_risk_score * 0.2
        
        # Adjust based on portfolio state
        if portfolio_state.open_positions_count >= 2:
            confidence -= 0.1
        
        # Adjust based on decision
        if decision == SignalDecision.BUY.value:
            if technical_indicators.rsi.overbought:
                confidence -= 0.2
        elif decision == SignalDecision.SELL.value:
            if technical_indicators.stochastic.oversold:
                confidence -= 0.2

        pattern_evidence = self._pattern_evidence(multi_timeframe)
        if pattern_evidence["bullish"] and pattern_evidence["bearish"]:
            confidence -= 0.10
        elif (decision == SignalDecision.BUY.value and pattern_evidence["bullish"]) or (
            decision == SignalDecision.SELL.value and pattern_evidence["bearish"]
        ):
            confidence += min(0.10, 0.03 * pattern_evidence["count"])
        
        # Ensure confidence is within bounds
        return max(0.0, min(1.0, confidence))
    
    def _generate_confidence_explanation(self, symbol: str, market_analysis: MarketAnalysis,
                                        technical_indicators: TechnicalIndicatorsResult,
                                        multi_timeframe: MultiTimeframeResult,
                                        portfolio_state: PortfolioState,
                                        market_regime: MarketRegime,
                                        risk_metrics: RiskMetrics,
                                        decision: str,
                                        confidence_score: float) -> str:
        """Generate explanation for confidence score"""
        explanation = []
        
        # Add factors that increased confidence
        if multi_timeframe.trend_alignment in ["BULLISH_ALIGNMENT", "BEARISH_ALIGNMENT"]:
            explanation.append("✅ Strong trend alignment across multiple timeframes")
        
        if multi_timeframe.trend_strength > 0.7:
            explanation.append("✅ High trend strength")
        
        if abs(multi_timeframe.momentum_alignment) > 0.5:
            explanation.append("✅ Strong momentum alignment")
        
        if market_regime.regime.value in ["Strong Trending", "Strong Bearish"]:
            explanation.append(f"✅ Favorable market regime: {market_regime.regime.value}")
        
        # Add factors that decreased confidence
        if multi_timeframe.trend_alignment == "MIXED_ALIGNMENT":
            explanation.append("⚠️ Mixed trend alignment across timeframes")
        
        if market_analysis.volatility_score == "high":
            explanation.append("⚠️ High market volatility")
        
        if risk_metrics.overall_risk_score > 0.7:
            explanation.append("⚠️ High risk metrics")
        
        if portfolio_state.open_positions_count >= 2:
            explanation.append("⚠️ Portfolio near capacity")
        
        # Add decision-specific factors
        if decision == SignalDecision.BUY.value:
            if technical_indicators.rsi.overbought:
                explanation.append("⚠️ RSI indicates overbought conditions")
        elif decision == SignalDecision.SELL.value:
            if technical_indicators.stochastic.oversold:
                explanation.append("⚠️ Stochastic indicates oversold conditions")
        
        # Add overall confidence level
        if confidence_score > 0.8:
            explanation.append("🎯 Very high confidence decision")
        elif confidence_score > 0.6:
            explanation.append("📈 High confidence decision")
        elif confidence_score > 0.4:
            explanation.append("⚖️ Moderate confidence decision")
        else:
            explanation.append("❓ Low confidence decision")
        
        return "; ".join(explanation)
    
    def _calculate_trade_quality_score(self, symbol: str, decision: str,
                                      market_analysis: MarketAnalysis,
                                      technical_indicators: TechnicalIndicatorsResult,
                                      portfolio_state: PortfolioState) -> float:
        """Calculate trade quality score"""
        score = 50.0  # Base score
        
        # Adjust based on decision
        if decision == SignalDecision.BUY.value:
            if market_analysis.trend_direction == "bullish":
                score += 20
            if technical_indicators.momentum_score > 0.5:
                score += 15
            if technical_indicators.volatility_score == "low":
                score += 10
        elif decision == SignalDecision.SELL.value:
            if market_analysis.trend_direction == "bearish":
                score += 20
            if technical_indicators.momentum_score < -0.5:
                score += 15
            if technical_indicators.volatility_score == "low":
                score += 10
        
        # Adjust based on portfolio state
        if portfolio_state.win_rate > 50:
            score += 10
        if portfolio_state.profit_factor > 1.5:
            score += 10
        
        # Ensure score is within bounds
        return max(0.0, min(100.0, score))
    
    def _generate_market_narrative(self, symbol: str, market_analysis: MarketAnalysis,
                                   technical_indicators: TechnicalIndicatorsResult,
                                   multi_timeframe: MultiTimeframeResult,
                                   portfolio_state: PortfolioState,
                                   market_regime: MarketRegime) -> str:
        """Generate market narrative"""
        narrative = f"{symbol} "
        
        # Add trend information
        if market_analysis.trend_direction == "bullish":
            narrative += "continues making higher highs. "
        elif market_analysis.trend_direction == "bearish":
            narrative += "is experiencing downward pressure. "
        else:
            narrative += "is trading in a range. "
        
        # Add momentum information
        if market_analysis.momentum_score > 0.5:
            narrative += "Momentum remains positive. "
        elif market_analysis.momentum_score < -0.5:
            narrative += "Momentum is negative. "
        else:
            narrative += "Momentum is neutral. "
        
        # Add technical information
        if technical_indicators.overall_trend == "bullish":
            narrative += "Technical indicators favor bullish continuation. "
        elif technical_indicators.overall_trend == "bearish":
            narrative += "Technical indicators favor bearish continuation. "
        
        # Add multi-timeframe information
        if multi_timeframe.trend_alignment == "BULLISH_ALIGNMENT":
            narrative += "Multiple timeframes show bullish alignment. "
        elif multi_timeframe.trend_alignment == "BEARISH_ALIGNMENT":
            narrative += "Multiple timeframes show bearish alignment. "
        
        # Add market regime information
        narrative += f"Current market regime: {market_regime.regime.value}. "
        
        # Add portfolio information
        if portfolio_state.total_floating_pnl > 0:
            narrative += f"Portfolio showing positive PnL: ${portfolio_state.total_floating_pnl:.2f}. "
        
        return narrative
    
    def _generate_ai_explanation(self, symbol: str, market_analysis: MarketAnalysis,
                                technical_indicators: TechnicalIndicatorsResult,
                                multi_timeframe: MultiTimeframeResult,
                                portfolio_state: PortfolioState,
                                market_regime: MarketRegime,
                                risk_metrics: RiskMetrics,
                                decision: str) -> str:
        """Generate AI explanation for the decision"""
        explanation = []
        
        # Add trend analysis
        if market_analysis.trend_direction == "bullish":
            explanation.append("Market analysis indicates bullish trend")
        elif market_analysis.trend_direction == "bearish":
            explanation.append("Market analysis indicates bearish trend")
        else:
            explanation.append("Market analysis indicates neutral trend")
        
        # Add technical analysis
        if technical_indicators.overall_trend == "bullish":
            explanation.append("Technical indicators support bullish outlook")
        elif technical_indicators.overall_trend == "bearish":
            explanation.append("Technical indicators support bearish outlook")
        
        # Add multi-timeframe analysis
        if multi_timeframe.trend_alignment == "BULLISH_ALIGNMENT":
            explanation.append("Multi-timeframe analysis shows bullish alignment")
        elif multi_timeframe.trend_alignment == "BEARISH_ALIGNMENT":
            explanation.append("Multi-timeframe analysis shows bearish alignment")
        
        # Add risk assessment
        if risk_metrics.overall_risk_score < 0.5:
            explanation.append("Risk metrics are favorable")
        else:
            explanation.append("Risk metrics require caution")
        
        # Add portfolio context
        if portfolio_state.open_positions_count > 0:
            explanation.append(f"Portfolio currently has {portfolio_state.open_positions_count} open positions")
        
        # Add final decision
        if decision == SignalDecision.BUY.value:
            explanation.append("AI recommends BUY signal")
        elif decision == SignalDecision.SELL.value:
            explanation.append("AI recommends SELL signal")
        else:
            explanation.append("AI recommends HOLD signal")
        
        return "; ".join(explanation)
    
    def _generate_recommended_action(self, decision: str, trade_quality_score: float, 
                                    confidence_score: float) -> str:
        """Generate recommended action based on decision and scores"""
        if decision == SignalDecision.BUY.value:
            if trade_quality_score > 80 and confidence_score > 0.7:
                return "Execute BUY order immediately"
            elif trade_quality_score > 60:
                return "Consider BUY with caution"
            else:
                return "Wait for better entry conditions"
        
        elif decision == SignalDecision.SELL.value:
            if trade_quality_score > 80 and confidence_score > 0.7:
                return "Execute SELL order immediately"
            elif trade_quality_score > 60:
                return "Consider SELL with caution"
            else:
                return "Wait for better exit conditions"
        
        else:
            return "Maintain current positions, monitor for changes"

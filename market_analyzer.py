"""
Market Analyzer for AI Trading Intelligence Bot
Analyzes market data for each asset to generate trading signals.
"""

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any
from decimal import Decimal, ROUND_HALF_UP

from configuration_manager import AssetConfig

class TrendDirection(Enum):
    """Market trend directions"""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"

class VolatilityScore(Enum):
    """Volatility scores"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class MarketPhase(Enum):
    """Market phases"""
    STRONG_BULLISH = "Strong Bullish"
    WEAK_BULLISH = "Weak Bullish"
    NEUTRAL = "Neutral"
    WEAK_BEARISH = "Weak Bearish"
    STRONG_BEARISH = "Strong Bearish"
    HIGH_VOLATILITY = "High Volatility"
    LOW_LIQUIDITY = "Low Liquidity"
    ACCUMULATION = "Accumulation"
    DISTRIBUTION = "Distribution"
    BREAKOUT = "Breakout"
    REVERSAL = "Reversal"
    RANGE_BOUND = "Range Bound"

@dataclass
class MarketAnalysis:
    """Market analysis results"""
    symbol: str
    timestamp: datetime
    current_price: float
    previous_price: float
    price_change: float
    price_change_percent: float
    trend_direction: str
    momentum_score: float
    sentiment_score: float
    volatility_score: str
    confidence_score: float
    market_pressure: float
    strength_score: float
    trend_quality: str
    market_phase: str
    reasoning: List[str]
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)

class MarketAnalyzer:
    """Analyzes market data for trading signals"""
    
    def __init__(self, asset_config: AssetConfig):
        self.asset_config = asset_config
        self.price_history: Dict[str, List[float]] = {}
        self.volume_history: Dict[str, List[float]] = {}
    
    def analyze_market(self, symbol: str, current_price: float, 
                      previous_price: float, volume: float = None) -> MarketAnalysis:
        """Analyze market data and generate trading signal"""
        # Update price history
        if symbol not in self.price_history:
            self.price_history[symbol] = []
        self.price_history[symbol].append(current_price)
        
        if volume is not None:
            if symbol not in self.volume_history:
                self.volume_history[symbol] = []
            self.volume_history[symbol].append(volume)
        
        # Calculate price change
        price_change = current_price - previous_price
        price_change_percent = self._round_decimal(
            ((price_change / previous_price) * 100) if previous_price > 0 else 0
        )
        
        # Analyze different aspects
        trend_direction = self._analyze_trend(symbol, current_price)
        momentum_score = self._analyze_momentum(symbol)
        sentiment_score = self._analyze_sentiment(symbol)
        volatility_score = self._analyze_volatility(symbol)
        market_pressure = self._analyze_market_pressure(symbol)
        strength_score = self._calculate_strength_score(trend_direction, momentum_score, sentiment_score)
        trend_quality = self._analyze_trend_quality(symbol)
        market_phase = self._identify_market_phase(trend_direction, volatility_score, momentum_score)
        
        # Calculate confidence
        confidence_score = self._calculate_confidence(
            trend_direction, momentum_score, sentiment_score, market_pressure, volatility_score
        )
        
        # Generate reasoning
        reasoning = self._generate_reasoning(
            trend_direction, momentum_score, sentiment_score, market_pressure, confidence_score
        )
        
        return MarketAnalysis(
            symbol=symbol,
            timestamp=datetime.now(timezone.utc),
            current_price=current_price,
            previous_price=previous_price,
            price_change=price_change,
            price_change_percent=price_change_percent,
            trend_direction=trend_direction.value,
            momentum_score=self._round_decimal(momentum_score),
            sentiment_score=self._round_decimal(sentiment_score),
            volatility_score=volatility_score.value,
            confidence_score=self._round_decimal(confidence_score),
            market_pressure=self._round_decimal(market_pressure),
            strength_score=self._round_decimal(strength_score),
            trend_quality=trend_quality,
            market_phase=market_phase.value,
            reasoning=reasoning
        )
    
    def _analyze_trend(self, symbol: str, current_price: float) -> TrendDirection:
        """Analyze price trend"""
        prices = self.price_history.get(symbol, [])
        if len(prices) < 5:
            return TrendDirection.NEUTRAL
        
        # Calculate moving averages
        sma_5 = sum(prices[-5:]) / 5
        sma_20 = sum(prices[-20:]) / 20 if len(prices) >= 20 else sma_5
        
        # Determine trend based on price action and moving averages
        if current_price > sma_5 and sma_5 > sma_20:
            return TrendDirection.BULLISH
        elif current_price < sma_5 and sma_5 < sma_20:
            return TrendDirection.BEARISH
        else:
            return TrendDirection.NEUTRAL
    
    def _analyze_momentum(self, symbol: str) -> float:
        """Analyze price momentum"""
        prices = self.price_history.get(symbol, [])
        if len(prices) < 2:
            return 0.0
        
        # Calculate rate of change
        if len(prices) >= 5:
            recent_change = (prices[-1] - prices[-5]) / prices[-5] * 100
        else:
            recent_change = (prices[-1] - prices[0]) / prices[0] * 100
        
        # Normalize to -1 to 1 range
        return max(-1.0, min(1.0, recent_change / 20))
    
    def _analyze_sentiment(self, symbol: str) -> float:
        """Analyze market sentiment"""
        # This would typically use news, social media, etc.
        # For now, use a simplified approach based on price action
        prices = self.price_history.get(symbol, [])
        if len(prices) < 3:
            return 0.0
        
        # Calculate volatility-based sentiment
        if len(prices) >= 3:
            returns = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
            avg_return = sum(returns) / len(returns)
            
            # Positive sentiment if average return is positive
            sentiment = max(-1.0, min(1.0, avg_return * 10))
            return sentiment
        
        return 0.0
    
    def _analyze_volatility(self, symbol: str) -> VolatilityScore:
        """Analyze price volatility"""
        prices = self.price_history.get(symbol, [])
        if len(prices) < 2:
            return VolatilityScore.LOW
        
        # Calculate standard deviation of returns
        returns = []
        for i in range(1, len(prices)):
            if prices[i-1] > 0:
                returns.append((prices[i] - prices[i-1]) / prices[i-1])
        
        if not returns:
            return VolatilityScore.LOW
        
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        std_dev = math.sqrt(variance)
        
        # Determine volatility level
        volatility_percent = std_dev * 100
        if volatility_percent > 5.0:
            return VolatilityScore.HIGH
        elif volatility_percent > 2.0:
            return VolatilityScore.MEDIUM
        else:
            return VolatilityScore.LOW
    
    def _analyze_market_pressure(self, symbol: str) -> float:
        """Analyze overall market pressure"""
        # This would typically use multiple data sources
        # For now, use a simplified approach
        prices = self.price_history.get(symbol, [])
        if len(prices) < 3:
            return 0.0
        
        # Calculate pressure based on price acceleration
        if len(prices) >= 3:
            recent_prices = prices[-3:]
            accelerations = []
            for i in range(1, len(recent_prices)):
                if recent_prices[i-1] > 0:
                    acceleration = (recent_prices[i] - recent_prices[i-1]) / recent_prices[i-1]
                    accelerations.append(acceleration)
            
            if accelerations:
                avg_acceleration = sum(accelerations) / len(accelerations)
                return max(-1.0, min(1.0, avg_acceleration * 5))
        
        return 0.0
    
    def _calculate_strength_score(self, trend: TrendDirection, momentum: float, 
                                 sentiment: float) -> float:
        """Calculate overall strength score"""
        # Weight different factors
        trend_weight = 0.4
        momentum_weight = 0.3
        sentiment_weight = 0.3
        
        # Convert trend to numeric value
        trend_value = 0.0
        if trend == TrendDirection.BULLISH:
            trend_value = 1.0
        elif trend == TrendDirection.BEARISH:
            trend_value = -1.0
        
        strength = (trend_value * trend_weight + 
                   momentum * momentum_weight + 
                   sentiment * sentiment_weight)
        
        return max(-1.0, min(1.0, strength))
    
    def _analyze_trend_quality(self, symbol: str) -> str:
        """Analyze quality of the current trend"""
        prices = self.price_history.get(symbol, [])
        if len(prices) < 5:
            return "Weak"
        
        # Check if trend is consistent
        recent_prices = prices[-5:]
        
        # Calculate slope
        x_values = list(range(len(recent_prices)))
        y_values = recent_prices
        
        n = len(x_values)
        if n < 2:
            return "Weak"
        
        sum_x = sum(x_values)
        sum_y = sum(y_values)
        sum_xy = sum(x * y for x, y in zip(x_values, y_values))
        sum_x2 = sum(x * x for x in x_values)
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        
        # Determine trend quality based on slope
        slope_percent = (slope / recent_prices[0]) * 100 if recent_prices[0] > 0 else 0
        
        if abs(slope_percent) > 2.0:
            return "Strong"
        elif abs(slope_percent) > 0.5:
            return "Moderate"
        else:
            return "Weak"
    
    def _identify_market_phase(self, trend: TrendDirection, volatility: VolatilityScore, 
                              momentum: float) -> MarketPhase:
        """Identify current market phase"""
        # Determine market phase based on multiple factors
        if volatility == VolatilityScore.HIGH:
            return MarketPhase.HIGH_VOLATILITY
        
        if trend == TrendDirection.BULLISH and momentum > 0.5:
            return MarketPhase.STRONG_BULLISH
        elif trend == TrendDirection.BULLISH and momentum > 0.2:
            return MarketPhase.WEAK_BULLISH
        elif trend == TrendDirection.BEARISH and momentum < -0.5:
            return MarketPhase.STRONG_BEARISH
        elif trend == TrendDirection.BEARISH and momentum < -0.2:
            return MarketPhase.WEAK_BEARISH
        elif trend == TrendDirection.NEUTRAL:
            if momentum > 0.2:
                return MarketPhase.ACCUMULATION
            elif momentum < -0.2:
                return MarketPhase.DISTRIBUTION
            else:
                return MarketPhase.RANGE_BOUND
        
        return MarketPhase.NEUTRAL
    
    def _calculate_confidence(self, trend: TrendDirection, momentum: float, 
                            sentiment: float, pressure: float, volatility: VolatilityScore) -> float:
        """Calculate confidence score for the analysis"""
        # Base confidence
        confidence = 0.5
        
        # Adjust based on trend alignment
        if trend == TrendDirection.BULLISH and momentum > 0.5 and sentiment > 0.5:
            confidence += 0.3
        elif trend == TrendDirection.BEARISH and momentum < -0.5 and sentiment < -0.5:
            confidence += 0.3
        
        # Adjust based on market pressure
        confidence += abs(pressure) * 0.1
        
        # Reduce confidence for high volatility
        if volatility == VolatilityScore.HIGH:
            confidence -= 0.2
        elif volatility == VolatilityScore.MEDIUM:
            confidence -= 0.1
        
        # Ensure confidence is within bounds
        return max(0.0, min(1.0, confidence))
    
    def _generate_reasoning(self, trend: TrendDirection, momentum: float, 
                           sentiment: float, pressure: float, confidence: float) -> List[str]:
        """Generate reasoning for the analysis"""
        reasoning = []
        
        # Add reasoning based on trend
        if trend == TrendDirection.BULLISH:
            reasoning.append("Bullish trend detected")
        elif trend == TrendDirection.BEARISH:
            reasoning.append("Bearish trend detected")
        else:
            reasoning.append("Neutral trend")
        
        # Add reasoning based on momentum
        if momentum > 0.5:
            reasoning.append("Strong positive momentum")
        elif momentum > 0.2:
            reasoning.append("Moderate positive momentum")
        elif momentum < -0.5:
            reasoning.append("Strong negative momentum")
        elif momentum < -0.2:
            reasoning.append("Moderate negative momentum")
        
        # Add reasoning based on sentiment
        if sentiment > 0.5:
            reasoning.append("Positive market sentiment")
        elif sentiment > 0.2:
            reasoning.append("Moderate positive sentiment")
        elif sentiment < -0.5:
            reasoning.append("Negative market sentiment")
        elif sentiment < -0.2:
            reasoning.append("Moderate negative sentiment")
        
        # Add reasoning based on pressure
        if pressure > 0.3:
            reasoning.append("Strong buying pressure")
        elif pressure > 0.1:
            reasoning.append("Moderate buying pressure")
        elif pressure < -0.3:
            reasoning.append("Strong selling pressure")
        elif pressure < -0.1:
            reasoning.append("Moderate selling pressure")
        
        # Add confidence note
        if confidence > 0.8:
            reasoning.append("High confidence in analysis")
        elif confidence > 0.6:
            reasoning.append("Medium confidence in analysis")
        else:
            reasoning.append("Low confidence in analysis")
        
        return reasoning
    
    def _round_decimal(self, value: float, decimals: int = 2) -> float:
        """Round decimal value to specified precision"""
        return float(Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))

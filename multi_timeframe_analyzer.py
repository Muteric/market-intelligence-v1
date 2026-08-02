"""
Multi-Timeframe Analyzer for AI Trading Intelligence Bot
Analyzes multiple timeframes (5M, 15M, 1H, 4H, Daily) to determine trend alignment and generate high-confidence signals.
"""

import asyncio
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

class Timeframe(Enum):
    """Timeframe enumeration"""
    FIVE_MINUTES = "5M"
    FIFTEEN_MINUTES = "15M"
    ONE_HOUR = "1H"
    FOUR_HOURS = "4H"
    DAILY = "Daily"

@dataclass
class TimeframeAnalysis:
    """Analysis for a single timeframe"""
    timeframe: str
    current_price: float
    price_change: float
    price_change_percent: float
    trend: str
    trend_strength: float
    momentum: float
    volume: float
    timestamp: datetime

@dataclass
class MultiTimeframeResult:
    """Complete multi-timeframe analysis result"""
    symbol: str
    timestamp: datetime
    timeframe_analyses: Dict[str, TimeframeAnalysis]
    overall_signal: str
    trend_alignment: str
    trend_strength: float
    momentum_alignment: float
    confidence_score: float
    key_levels: Dict[str, float]
    support_resistance: Dict[str, List[float]]

class MultiTimeframeAnalyzer:
    """Multi-timeframe analysis for trading signals"""
    
    def __init__(self):
        self.timeframe_data: Dict[str, Dict[str, List[float]]] = {}
        self.timeframe_volumes: Dict[str, Dict[str, List[float]]] = {}
        self.timeframe_highs: Dict[str, Dict[str, List[float]]] = {}
        self.timeframe_lows: Dict[str, Dict[str, List[float]]] = {}
    
    def update_timeframe_data(self, symbol: str, timeframe: str, price: float, 
                             volume: float, high: float = None, low: float = None) -> None:
        """Update data for a specific timeframe"""
        if symbol not in self.timeframe_data:
            self.timeframe_data[symbol] = {}
            self.timeframe_volumes[symbol] = {}
            self.timeframe_highs[symbol] = {}
            self.timeframe_lows[symbol] = {}
        
        if timeframe not in self.timeframe_data[symbol]:
            self.timeframe_data[symbol][timeframe] = []
            self.timeframe_volumes[symbol][timeframe] = []
            self.timeframe_highs[symbol][timeframe] = []
            self.timeframe_lows[symbol][timeframe] = []
        
        self.timeframe_data[symbol][timeframe].append(price)
        self.timeframe_volumes[symbol][timeframe].append(volume)
        
        if high is not None:
            self.timeframe_highs[symbol][timeframe].append(high)
        if low is not None:
            self.timeframe_lows[symbol][timeframe].append(low)
        
        # Keep only recent data (last 100 points per timeframe)
        max_points = 100
        for key in [self.timeframe_data, self.timeframe_volumes, self.timeframe_highs, self.timeframe_lows]:
            if len(key[symbol][timeframe]) > max_points:
                key[symbol][timeframe] = key[symbol][timeframe][-max_points:]
    
    def analyze_multi_timeframe(self, symbol: str) -> MultiTimeframeResult:
        """Analyze multiple timeframes for a symbol"""
        timeframe_analyses = {}
        
        for timeframe in Timeframe:
            tf_str = timeframe.value
            if tf_str in self.timeframe_data.get(symbol, {}):
                analysis = self._analyze_single_timeframe(symbol, tf_str)
                if analysis:
                    timeframe_analyses[tf_str] = analysis
        
        if not timeframe_analyses:
            raise ValueError(f"No timeframe data available for {symbol}")
        
        # Determine overall signal and alignment
        overall_signal = self._determine_overall_signal(timeframe_analyses)
        trend_alignment = self._determine_trend_alignment(timeframe_analyses)
        trend_strength = self._calculate_trend_strength(timeframe_analyses)
        momentum_alignment = self._calculate_momentum_alignment(timeframe_analyses)
        confidence_score = self._calculate_confidence_score(timeframe_analyses, overall_signal)
        
        # Calculate key levels and support/resistance
        key_levels = self._calculate_key_levels(symbol, timeframe_analyses)
        support_resistance = self._calculate_support_resistance(symbol, timeframe_analyses)
        
        return MultiTimeframeResult(
            symbol=symbol,
            timestamp=datetime.now(timezone.utc),
            timeframe_analyses=timeframe_analyses,
            overall_signal=overall_signal,
            trend_alignment=trend_alignment,
            trend_strength=trend_strength,
            momentum_alignment=momentum_alignment,
            confidence_score=confidence_score,
            key_levels=key_levels,
            support_resistance=support_resistance
        )
    
    def _analyze_single_timeframe(self, symbol: str, timeframe: str) -> Optional[TimeframeAnalysis]:
        """Analyze a single timeframe"""
        prices = self.timeframe_data.get(symbol, {}).get(timeframe, [])
        volumes = self.timeframe_volumes.get(symbol, {}).get(timeframe, [])
        highs = self.timeframe_highs.get(symbol, {}).get(timeframe, prices)
        lows = self.timeframe_lows.get(symbol, {}).get(timeframe, prices)
        
        if len(prices) < 3:
            return None
        
        # Calculate current price (last price)
        current_price = prices[-1]
        
        # Calculate price change
        if len(prices) >= 2:
            previous_price = prices[-2]
            price_change = current_price - previous_price
            price_change_percent = (price_change / previous_price * 100) if previous_price > 0 else 0
        else:
            price_change = 0.0
            price_change_percent = 0.0
        
        # Calculate trend
        trend = self._determine_timeframe_trend(prices, timeframe)
        
        # Calculate trend strength
        trend_strength = self._calculate_timeframe_trend_strength(prices, timeframe)
        
        # Calculate momentum
        momentum = self._calculate_timeframe_momentum(prices, timeframe)
        
        # Get volume
        volume = volumes[-1] if volumes else 0.0
        
        return TimeframeAnalysis(
            timeframe=timeframe,
            current_price=current_price,
            price_change=price_change,
            price_change_percent=price_change_percent,
            trend=trend,
            trend_strength=trend_strength,
            momentum=momentum,
            volume=volume,
            timestamp=datetime.now(timezone.utc)
        )
    
    def _determine_timeframe_trend(self, prices: List[float], timeframe: str) -> str:
        """Determine trend for a single timeframe"""
        if len(prices) < 5:
            return "neutral"
        
        # Calculate moving averages based on timeframe
        if timeframe == Timeframe.FIVE_MINUTES.value:
            sma_short = sum(prices[-5:]) / 5
            sma_long = sum(prices[-20:]) / 20 if len(prices) >= 20 else sma_short
        elif timeframe == Timeframe.FIFTEEN_MINUTES.value:
            sma_short = sum(prices[-3:]) / 3
            sma_long = sum(prices[-10:]) / 10 if len(prices) >= 10 else sma_short
        elif timeframe == Timeframe.ONE_HOUR.value:
            sma_short = sum(prices[-4:]) / 4
            sma_long = sum(prices[-12:]) / 12 if len(prices) >= 12 else sma_short
        elif timeframe == Timeframe.FOUR_HOURS.value:
            sma_short = sum(prices[-2:]) / 2
            sma_long = sum(prices[-8:]) / 8 if len(prices) >= 8 else sma_short
        else:  # Daily
            sma_short = sum(prices[-1:]) / 1
            sma_long = sum(prices[-5:]) / 5 if len(prices) >= 5 else sma_short
        
        # Determine trend based on price action and moving averages
        if len(prices) >= 2:
            current_price = prices[-1]
            previous_price = prices[-2]
            price_change = current_price - previous_price
            
            if price_change > 0:
                if current_price > sma_short and sma_short > sma_long:
                    return "bullish"
                elif current_price > sma_short:
                    return "moderately_bullish"
                else:
                    return "weak_bullish"
            elif price_change < 0:
                if current_price < sma_short and sma_short < sma_long:
                    return "bearish"
                elif current_price < sma_short:
                    return "moderately_bearish"
                else:
                    return "weak_bearish"
            else:
                return "neutral"
        
        return "neutral"
    
    def _calculate_timeframe_trend_strength(self, prices: List[float], timeframe: str) -> float:
        """Calculate trend strength for a single timeframe"""
        if len(prices) < 3:
            return 0.0
        
        # Calculate linear regression slope
        x_values = list(range(len(prices)))
        y_values = prices
        
        n = len(x_values)
        if n < 2:
            return 0.0
        
        sum_x = sum(x_values)
        sum_y = sum(y_values)
        sum_xy = sum(x * y for x, y in zip(x_values, y_values))
        sum_x2 = sum(x * x for x in x_values)
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        
        # Normalize slope based on timeframe
        if timeframe == Timeframe.FIVE_MINUTES.value:
            max_slope = 0.01
        elif timeframe == Timeframe.FIFTEEN_MINUTES.value:
            max_slope = 0.005
        elif timeframe == Timeframe.ONE_HOUR.value:
            max_slope = 0.002
        elif timeframe == Timeframe.FOUR_HOURS.value:
            max_slope = 0.001
        else:  # Daily
            max_slope = 0.0005
        
        # Calculate strength (0 to 1)
        strength = min(1.0, abs(slope) / max_slope) if max_slope > 0 else 0.0
        
        # Add direction
        if slope > 0:
            return strength
        else:
            return -strength
    
    def _calculate_timeframe_momentum(self, prices: List[float], timeframe: str) -> float:
        """Calculate momentum for a single timeframe"""
        if len(prices) < 3:
            return 0.0
        
        # Calculate rate of change
        if len(prices) >= 5:
            recent_change = (prices[-1] - prices[-5]) / prices[-5] * 100
        else:
            recent_change = (prices[-1] - prices[0]) / prices[0] * 100
        
        # Normalize to -1 to 1 range based on timeframe
        if timeframe == Timeframe.FIVE_MINUTES.value:
            max_change = 10.0
        elif timeframe == Timeframe.FIFTEEN_MINUTES.value:
            max_change = 5.0
        elif timeframe == Timeframe.ONE_HOUR.value:
            max_change = 2.0
        elif timeframe == Timeframe.FOUR_HOURS.value:
            max_change = 1.0
        else:  # Daily
            max_change = 0.5
        
        momentum = max(-1.0, min(1.0, recent_change / max_change))
        
        return momentum
    
    def _determine_overall_signal(self, timeframe_analyses: Dict[str, TimeframeAnalysis]) -> str:
        """Determine overall signal from all timeframes"""
        if not timeframe_analyses:
            return "INSUFFICIENT_DATA"
        
        # Count bullish and bearish signals
        bullish_count = 0
        bearish_count = 0
        
        for analysis in timeframe_analyses.values():
            if analysis.trend in ["bullish", "moderately_bullish", "weak_bullish"]:
                bullish_count += 1
            elif analysis.trend in ["bearish", "moderately_bearish", "weak_bearish"]:
                bearish_count += 1
        
        # Determine signal based on majority
        if bullish_count > bearish_count + 1:
            return "BUY"
        elif bearish_count > bullish_count + 1:
            return "SELL"
        else:
            return "HOLD"
    
    def _determine_trend_alignment(self, timeframe_analyses: Dict[str, TimeframeAnalysis]) -> str:
        """Determine trend alignment across timeframes"""
        if not timeframe_analyses:
            return "NEUTRAL"
        
        # Check if all timeframes have the same trend direction
        trends = []
        for analysis in timeframe_analyses.values():
            if analysis.trend.startswith("bullish"):
                trends.append("bullish")
            elif analysis.trend.startswith("bearish"):
                trends.append("bearish")
            else:
                trends.append("neutral")
        
        # Check for alignment
        if all(t == "bullish" for t in trends):
            return "BULLISH_ALIGNMENT"
        elif all(t == "bearish" for t in trends):
            return "BEARISH_ALIGNMENT"
        elif all(t == "neutral" for t in trends):
            return "NEUTRAL_ALIGNMENT"
        else:
            return "MIXED_ALIGNMENT"
    
    def _calculate_trend_strength(self, timeframe_analyses: Dict[str, TimeframeAnalysis]) -> float:
        """Calculate overall trend strength"""
        if not timeframe_analyses:
            return 0.0
        
        # Average trend strength
        total_strength = 0.0
        count = 0
        
        for analysis in timeframe_analyses.values():
            if analysis.trend_strength != 0:
                total_strength += abs(analysis.trend_strength)
                count += 1
        
        if count == 0:
            return 0.0
        
        return total_strength / count
    
    def _calculate_momentum_alignment(self, timeframe_analyses: Dict[str, TimeframeAnalysis]) -> float:
        """Calculate momentum alignment across timeframes"""
        if not timeframe_analyses:
            return 0.0
        
        # Average momentum
        total_momentum = 0.0
        count = 0
        
        for analysis in timeframe_analyses.values():
            if analysis.momentum != 0:
                total_momentum += analysis.momentum
                count += 1
        
        if count == 0:
            return 0.0
        
        return total_momentum / count
    
    def _calculate_confidence_score(self, timeframe_analyses: Dict[str, TimeframeAnalysis], 
                                   overall_signal: str) -> float:
        """Calculate confidence score for multi-timeframe analysis"""
        if not timeframe_analyses:
            return 0.0
        
        # Base confidence
        confidence = 0.5
        
        # Adjust based on number of timeframes analyzed
        num_timeframes = len(timeframe_analyses)
        confidence += (num_timeframes / 5) * 0.2  # Max 0.4 for 5 timeframes
        
        # Adjust based on trend alignment
        trend_alignment = self._determine_trend_alignment(timeframe_analyses)
        if trend_alignment in ["BULLISH_ALIGNMENT", "BEARISH_ALIGNMENT"]:
            confidence += 0.3
        elif trend_alignment == "MIXED_ALIGNMENT":
            confidence -= 0.2
        
        # Adjust based on trend strength
        trend_strength = self._calculate_trend_strength(timeframe_analyses)
        confidence += trend_strength * 0.2
        
        # Adjust based on momentum alignment
        momentum_alignment = self._calculate_momentum_alignment(timeframe_analyses)
        confidence += abs(momentum_alignment) * 0.15
        
        # Ensure confidence is within bounds
        return max(0.0, min(1.0, confidence))
    
    def _calculate_key_levels(self, symbol: str, timeframe_analyses: Dict[str, TimeframeAnalysis]) -> Dict[str, float]:
        """Calculate key price levels"""
        levels = {}
        
        # Calculate average price across all timeframes
        total_price = 0.0
        count = 0
        
        for analysis in timeframe_analyses.values():
            total_price += analysis.current_price
            count += 1
        
        if count > 0:
            levels['average_price'] = total_price / count
        
        # Calculate price range
        if timeframe_analyses:
            prices = [analysis.current_price for analysis in timeframe_analyses.values()]
            levels['price_range'] = max(prices) - min(prices)
            levels['price_volatility'] = (max(prices) - min(prices)) / levels['average_price'] * 100 if levels['average_price'] > 0 else 0
        
        return levels
    
    def _calculate_support_resistance(self, symbol: str, timeframe_analyses: Dict[str, TimeframeAnalysis]) -> Dict[str, List[float]]:
        """Calculate support and resistance levels"""
        support_levels = []
        resistance_levels = []
        
        # Simple support/resistance calculation based on price action
        for analysis in timeframe_analyses.values():
            price = analysis.current_price
            change = analysis.price_change
            
            if change > 0:
                # Potential resistance
                resistance_levels.append(price * 1.01)  # 1% above current price
            elif change < 0:
                # Potential support
                support_levels.append(price * 0.99)  # 1% below current price
        
        # Group nearby levels
        def group_levels(levels, tolerance=0.01):
            if not levels:
                return []
            
            sorted_levels = sorted(levels)
            grouped = [sorted_levels[0]]
            
            for level in sorted_levels[1:]:
                if level - grouped[-1] <= tolerance:
                    # Average the levels
                    grouped[-1] = sum(grouped) / len(grouped)
                else:
                    grouped.append(level)
            
            return grouped
        
        return {
            'support': group_levels(support_levels),
            'resistance': group_levels(resistance_levels)
        }
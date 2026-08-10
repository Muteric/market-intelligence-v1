"""
market_regime_detector.py

AI Trading Intelligence System
Market Regime Detection Module
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class MarketRegime(Enum):
    STRONG_BULLISH = "Strong Bullish"
    WEAK_BULLISH = "Weak Bullish"
    RANGE_BOUND = "Range Bound"
    ACCUMULATION = "Accumulation"
    DISTRIBUTION = "Distribution"
    BREAKOUT = "Breakout"
    REVERSAL = "Reversal"
    STRONG_BEARISH = "Strong Bearish"
    WEAK_BEARISH = "Weak Bearish"
    HIGH_VOLATILITY = "High Volatility"
    LOW_VOLATILITY = "Low Volatility"
    UNKNOWN = "Unknown"


@dataclass
class MarketRegimeResult:
    regime: MarketRegime
    confidence: float
    explanation: str


class MarketRegimeDetector:
    """
    Determines the current market regime from trend, momentum,
    volatility and technical indicators.
    """

    def detect_regime(
        self,
        symbol: str,
        market_analysis,
        technical_indicators
    ) -> MarketRegimeResult:

        try:

            trend = str(getattr(market_analysis, "trend_direction", "neutral")).lower()

            volatility = str(getattr(
                market_analysis,
                "volatility_score",
                "medium"
            )).lower()

            rsi_result = getattr(technical_indicators, "rsi", None)
            rsi = float(getattr(rsi_result, "rsi", rsi_result or 50.0))

            adx_result = getattr(technical_indicators, "adx", None)
            adx = float(getattr(adx_result, "adx", adx_result or 20.0))

            macd_result = getattr(technical_indicators, "macd", None)
            macd = float(getattr(macd_result, "macd", macd_result or 0.0))

            ema_result = getattr(technical_indicators, "ema", None)
            ema20 = getattr(ema_result, "ema_20", getattr(ema_result, "ema20", None))
            ema50 = getattr(ema_result, "ema_50", getattr(ema_result, "ema50", None))

            logger.info(f"{symbol}: Detecting market regime")

            # Strong Bull Trend
            if trend == "bullish":

                if adx >= 30:

                    return MarketRegimeResult(MarketRegime.STRONG_BULLISH, 0.9, "Strong bullish trend")

                return MarketRegimeResult(MarketRegime.WEAK_BULLISH, 0.6, "Weak bullish trend")

            # Strong Bear Trend
            if trend == "bearish":

                if adx >= 30:

                    return MarketRegimeResult(MarketRegime.STRONG_BEARISH, 0.9, "Strong bearish trend")

                return MarketRegimeResult(MarketRegime.WEAK_BEARISH, 0.6, "Weak bearish trend")

            # Breakout Detection
            if adx >= 35 and abs(macd) > 0:

                return MarketRegimeResult(MarketRegime.BREAKOUT, 0.8, "Breakout conditions")

            # Accumulation
            if rsi <= 30:

                return MarketRegimeResult(MarketRegime.ACCUMULATION, 0.7, "Oversold accumulation")

            # Distribution
            if rsi >= 70:

                return MarketRegimeResult(MarketRegime.DISTRIBUTION, 0.7, "Overbought distribution")

            # EMA crossover reversal
            if ema20 is not None and ema50 is not None:

                if abs(ema20 - ema50) / max(abs(ema50), 1) < 0.002:

                    return MarketRegimeResult(MarketRegime.REVERSAL, 0.6, "Possible reversal")

            # Volatility
            if volatility == "high":

                return MarketRegimeResult(MarketRegime.HIGH_VOLATILITY, 0.8, "High volatility")

            if volatility == "low":

                return MarketRegimeResult(MarketRegime.LOW_VOLATILITY, 0.4, "Low volatility")

            return MarketRegimeResult(MarketRegime.RANGE_BOUND, 0.5, "Range-bound market")

        except Exception as ex:

            logger.exception(
                f"{symbol}: Market regime detection failed: {ex}"
            )

            return MarketRegimeResult(MarketRegime.UNKNOWN, 0.0, "Unknown market regime")

    def describe(
        self,
        regime: MarketRegime
    ) -> str:
        """
        Human-readable explanation for Telegram reports.
        """

        descriptions = {

            MarketRegime.STRONG_BULLISH:
                "Strong upward trend confirmed across indicators.",

            MarketRegime.WEAK_BULLISH:
                "Bullish bias with limited strength.",

            MarketRegime.STRONG_BEARISH:
                "Strong downward trend confirmed.",

            MarketRegime.WEAK_BEARISH:
                "Bearish bias with limited momentum.",

            MarketRegime.BREAKOUT:
                "Price is breaking out of consolidation.",

            MarketRegime.REVERSAL:
                "Possible trend reversal developing.",

            MarketRegime.ACCUMULATION:
                "Oversold conditions suggest accumulation.",

            MarketRegime.DISTRIBUTION:
                "Overbought conditions suggest distribution.",

            MarketRegime.HIGH_VOLATILITY:
                "Market volatility is elevated.",

            MarketRegime.LOW_VOLATILITY:
                "Market volatility is subdued.",

            MarketRegime.RANGE_BOUND:
                "Market is trading sideways.",

            MarketRegime.UNKNOWN:
                "Market regime could not be determined."

        }

        return descriptions.get(
            regime,
            "Unknown market regime."
        )

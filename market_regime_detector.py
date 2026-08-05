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
    ) -> MarketRegime:

        try:

            trend = str(getattr(
                market_analysis,
                "trend",
                "Neutral"
            )).lower()

            volatility = str(getattr(
                market_analysis,
                "volatility",
                "Medium"
            )).lower()

            rsi = float(getattr(
                technical_indicators,
                "rsi",
                50.0
            ))

            adx = float(getattr(
                technical_indicators,
                "adx",
                20.0
            ))

            macd = float(getattr(
                technical_indicators,
                "macd",
                0.0
            ))

            ema20 = getattr(
                technical_indicators,
                "ema20",
                None
            )

            ema50 = getattr(
                technical_indicators,
                "ema50",
                None
            )

            logger.info(f"{symbol}: Detecting market regime")

            # Strong Bull Trend
            if trend == "bullish":

                if adx >= 30:

                    return MarketRegime.STRONG_BULLISH

                return MarketRegime.WEAK_BULLISH

            # Strong Bear Trend
            if trend == "bearish":

                if adx >= 30:

                    return MarketRegime.STRONG_BEARISH

                return MarketRegime.WEAK_BEARISH

            # Breakout Detection
            if adx >= 35 and abs(macd) > 0:

                return MarketRegime.BREAKOUT

            # Accumulation
            if rsi <= 30:

                return MarketRegime.ACCUMULATION

            # Distribution
            if rsi >= 70:

                return MarketRegime.DISTRIBUTION

            # EMA crossover reversal
            if ema20 is not None and ema50 is not None:

                if abs(ema20 - ema50) / max(abs(ema50), 1) < 0.002:

                    return MarketRegime.REVERSAL

            # Volatility
            if volatility == "high":

                return MarketRegime.HIGH_VOLATILITY

            if volatility == "low":

                return MarketRegime.LOW_VOLATILITY

            return MarketRegime.RANGE_BOUND

        except Exception as ex:

            logger.exception(
                f"{symbol}: Market regime detection failed: {ex}"
            )

            return MarketRegime.UNKNOWN

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
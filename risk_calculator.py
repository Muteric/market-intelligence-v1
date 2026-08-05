"""
risk_calculator.py

AI Trading Intelligence System
Professional Risk Management Engine
"""

from dataclasses import dataclass
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class RiskMetrics:
    risk_score: float
    position_size_percent: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    take_profit_3: float
    risk_reward_ratio: float
    volatility_risk: str
    drawdown_risk: str
    margin_used: float
    margin_available: float


class RiskCalculator:

    def __init__(
        self,
        account_balance: float = 100.0,
        leverage: int = 400
    ):

        self.account_balance = account_balance
        self.leverage = leverage

    def calculate_risk_metrics(
        self,
        symbol: str,
        market_analysis,
        technical_indicators
    ) -> RiskMetrics:

        logger.info(f"Calculating risk metrics for {symbol}")

        current_price = getattr(
            market_analysis,
            "current_price",
            0.0
        )

        atr = getattr(
            technical_indicators,
            "atr",
            current_price * 0.01
        )

        volatility = getattr(
            market_analysis,
            "volatility",
            "Medium"
        )

        trend_strength = getattr(
            market_analysis,
            "trend_strength",
            50
        )

        # ---------- Position Size ----------

        if trend_strength >= 80:
            position_percent = 50

        elif trend_strength >= 60:
            position_percent = 25

        else:
            position_percent = 10

        # ---------- Stop Loss ----------

        stop_loss = current_price - (atr * 2)

        # ---------- Take Profit ----------

        tp1 = current_price + (atr * 2)

        tp2 = current_price + (atr * 4)

        tp3 = current_price + (atr * 6)

        reward = tp3 - current_price

        risk = current_price - stop_loss

        rr = reward / risk if risk > 0 else 0

        # ---------- Risk Score ----------

        risk_score = 100

        if volatility == "High":

            risk_score -= 25

        elif volatility == "Medium":

            risk_score -= 10

        if trend_strength < 50:

            risk_score -= 20

        risk_score = max(0, min(100, risk_score))

        # ---------- Margin ----------

        capital = self.account_balance * (
            position_percent / 100
        )

        margin_used = capital

        buying_power = capital * self.leverage

        margin_available = (
            self.account_balance - capital
        )

        # ---------- Volatility ----------

        if volatility == "High":

            volatility_risk = "High"

        elif volatility == "Medium":

            volatility_risk = "Medium"

        else:

            volatility_risk = "Low"

        # ---------- Drawdown ----------

        if risk_score >= 80:

            drawdown = "Low"

        elif risk_score >= 60:

            drawdown = "Medium"

        else:

            drawdown = "High"

        return RiskMetrics(

            risk_score=risk_score,

            position_size_percent=position_percent,

            stop_loss=round(stop_loss, 2),

            take_profit_1=round(tp1, 2),

            take_profit_2=round(tp2, 2),

            take_profit_3=round(tp3, 2),

            risk_reward_ratio=round(rr, 2),

            volatility_risk=volatility_risk,

            drawdown_risk=drawdown,

            margin_used=round(margin_used, 2),

            margin_available=round(
                margin_available,
                2
            )

        )
"""
Technical Indicators Calculator for AI Trading Intelligence Bot
Comprehensive technical analysis with RSI, MACD, EMA, SMA, Bollinger Bands, ATR, ADX, Stochastic, VWAP, OBV, Ichimoku, Fibonacci, and Pivot Points.
"""

import math
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

class IndicatorType(Enum):
    """Technical indicator types"""
    RSI = "rsi"
    MACD = "macd"
    EMA = "ema"
    SMA = "sma"
    BOLLINGER_BANDS = "bollinger_bands"
    ATR = "atr"
    ADX = "adx"
    STOCHASTIC = "stochastic"
    VWAP = "vwap"
    OBV = "obv"
    ICHIMOKU = "ichimoku"
    FIBONACCI = "fibonacci"
    PIVOT_POINTS = "pivot_points"

@dataclass
class RSIResult:
    """RSI indicator result"""
    rsi: float
    overbought: bool
    oversold: bool
    trend: str

@dataclass
class MACDResult:
    """MACD indicator result"""
    macd: float
    signal: float
    histogram: float
    macd_histogram: float
    trend: str

@dataclass
class EMAResult:
    """EMA indicator result"""
    ema_20: float
    ema_50: float
    ema_100: float
    ema_200: float
    trend: str

@dataclass
class SMAResult:
    """SMA indicator result"""
    sma_50: float
    sma_200: float
    cross: str

@dataclass
class BollingerBandsResult:
    """Bollinger Bands indicator result"""
    upper_band: float
    middle_band: float
    lower_band: float
    bandwidth: float
    percent_b: float
    squeeze: bool

@dataclass
class ATRResult:
    """ATR indicator result"""
    atr: float
    normalized_atr: float
    volatility: str

@dataclass
class ADXResult:
    """ADX indicator result"""
    adx: float
    di_plus: float
    di_minus: float
    trend_strength: str
    trend_direction: str

@dataclass
class StochasticResult:
    """Stochastic indicator result"""
    k: float
    d: float
    overbought: bool
    oversold: bool
    trend: str

@dataclass
class VWAPResult:
    """VWAP indicator result"""
    vwap: float
    deviation: float
    trend: str

@dataclass
class OBVResult:
    """OBV indicator result"""
    obv: float
    obv_trend: str
    volume_trend: str

@dataclass
class IchimokuResult:
    """Ichimoku Cloud indicator result"""
    conversion_line: float
    base_line: float
    leading_span1: float
    leading_span2: float
    lagging_span: float
    cloud_thickness: float
    cloud_direction: str
    tenkan_sen: float
    kijun_sen: float

@dataclass
class FibonacciResult:
    """Fibonacci retracement result"""
    levels: Dict[str, float]
    current_price: float
    nearest_level: str
    nearest_distance: float

@dataclass
class PivotPointsResult:
    """Pivot points result"""
    pivot: float
    r1: float
    r2: float
    r3: float
    s1: float
    s2: float
    s3: float
    current_price: float
    position: str

@dataclass
class TechnicalIndicatorsResult:
    """Complete technical indicators result"""
    symbol: str
    timestamp: datetime
    rsi: RSIResult
    macd: MACDResult
    ema: EMAResult
    sma: SMAResult
    bollinger_bands: BollingerBandsResult
    atr: ATRResult
    adx: ADXResult
    stochastic: StochasticResult
    vwap: VWAPResult
    obv: OBVResult
    ichimoku: IchimokuResult
    fibonacci: FibonacciResult
    pivot_points: PivotPointsResult
    overall_trend: str
    momentum_score: float
    volatility_score: str
    confidence_score: float

class TechnicalIndicators:
    """Comprehensive technical indicators calculator"""
    
    def __init__(self):
        self.price_history: Dict[str, List[float]] = {}
        self.volume_history: Dict[str, List[float]] = {}
        self.high_history: Dict[str, List[float]] = {}
        self.low_history: Dict[str, List[float]] = {}
    
    def update_price_data(self, symbol: str, price: float, volume: float, 
                         high: float = None, low: float = None) -> None:
        """Update price and volume data for a symbol"""
        if symbol not in self.price_history:
            self.price_history[symbol] = []
            self.volume_history[symbol] = []
            self.high_history[symbol] = []
            self.low_history[symbol] = []
        
        self.price_history[symbol].append(price)
        self.volume_history[symbol].append(volume)
        
        if high is not None:
            self.high_history[symbol].append(high)
        if low is not None:
            self.low_history[symbol].append(low)
        
        # Keep only recent data (last 1000 points)
        max_points = 1000
        for key in [self.price_history, self.volume_history, self.high_history, self.low_history]:
            if len(key[symbol]) > max_points:
                key[symbol] = key[symbol][-max_points:]

    def set_ohlcv_data(self, symbol: str, candles: List[Dict[str, float]]) -> None:
        """Replace a symbol's history with validated observed OHLCV candles."""
        valid = [
            candle for candle in candles
            if all(candle.get(field) is not None for field in ("high", "low", "close"))
        ]
        if not valid:
            raise ValueError(f"DATA UNAVAILABLE: no valid OHLCV candles for {symbol}")
        self.price_history[symbol] = [float(candle["close"]) for candle in valid[-1000:]]
        self.volume_history[symbol] = [float(candle.get("volume", 0.0)) for candle in valid[-1000:]]
        self.high_history[symbol] = [float(candle["high"]) for candle in valid[-1000:]]
        self.low_history[symbol] = [float(candle["low"]) for candle in valid[-1000:]]
    
    def calculate_all_indicators(self, symbol: str) -> TechnicalIndicatorsResult:
        """Calculate all technical indicators for a symbol"""
        prices = self.price_history.get(symbol, [])
        volumes = self.volume_history.get(symbol, [])
        highs = self.high_history.get(symbol, [])
        lows = self.low_history.get(symbol, [])
        
        if len(prices) < 200 or len(highs) != len(prices) or len(lows) != len(prices):
            raise ValueError(
                f"DATA UNAVAILABLE: insufficient OHLCV history for {symbol} "
                f"(need 200 complete candles, received {len(prices)})"
            )
        
        # Calculate individual indicators
        rsi = self._calculate_rsi(symbol)
        macd = self._calculate_macd(symbol)
        ema = self._calculate_ema(symbol)
        sma = self._calculate_sma(symbol)
        bollinger_bands = self._calculate_bollinger_bands(symbol)
        atr = self._calculate_atr(symbol)
        adx = self._calculate_adx(symbol)
        stochastic = self._calculate_stochastic(symbol)
        vwap = self._calculate_vwap(symbol)
        obv = self._calculate_obv(symbol)
        ichimoku = self._calculate_ichimoku(symbol)
        fibonacci = self._calculate_fibonacci(symbol)
        pivot_points = self._calculate_pivot_points(symbol)
        
        # Calculate overall trend and scores
        overall_trend = self._determine_overall_trend(rsi, macd, ema, sma, adx, stochastic)
        momentum_score = self._calculate_momentum_score(rsi, macd, stochastic)
        volatility_score = self._calculate_volatility_score(atr, bollinger_bands)
        confidence_score = self._calculate_confidence_score(rsi, macd, adx, stochastic)
        
        return TechnicalIndicatorsResult(
            symbol=symbol,
            timestamp=datetime.now(timezone.utc),
            rsi=rsi,
            macd=macd,
            ema=ema,
            sma=sma,
            bollinger_bands=bollinger_bands,
            atr=atr,
            adx=adx,
            stochastic=stochastic,
            vwap=vwap,
            obv=obv,
            ichimoku=ichimoku,
            fibonacci=fibonacci,
            pivot_points=pivot_points,
            overall_trend=overall_trend,
            momentum_score=momentum_score,
            volatility_score=volatility_score,
            confidence_score=confidence_score
        )
    
    def _calculate_rsi(self, symbol: str) -> RSIResult:
        """Calculate RSI (Relative Strength Index)"""
        prices = self.price_history[symbol]
        if len(prices) < 14:
            return RSIResult(50.0, False, False, "neutral")
        
        # Calculate gains and losses
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        # Calculate average gain and loss
        avg_gain = sum(gains[-14:]) / 14
        avg_loss = sum(losses[-14:]) / 14
        
        if avg_loss == 0:
            rsi = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        
        # Determine RSI status
        overbought = rsi > 70
        oversold = rsi < 30
        
        if rsi > 70:
            trend = "overbought"
        elif rsi < 30:
            trend = "oversold"
        elif rsi > 50:
            trend = "bullish"
        elif rsi < 50:
            trend = "bearish"
        else:
            trend = "neutral"
        
        return RSIResult(rsi, overbought, oversold, trend)
    
    def _calculate_macd(self, symbol: str) -> MACDResult:
        """Calculate MACD (Moving Average Convergence Divergence)"""
        prices = self.price_history[symbol]
        if len(prices) < 26:
            return MACDResult(0.0, 0.0, 0.0, 0.0, "neutral")
        
        # Calculate EMA 12, EMA 26
        ema_12 = self._calculate_ema_n(prices, 12)
        ema_26 = self._calculate_ema_n(prices, 26)
        
        # Calculate MACD line
        macd = ema_12 - ema_26
        
        # Calculate signal line (EMA of MACD)
        macd_values = [self._calculate_ema_n(prices[-i:], 9) for i in range(1, min(10, len(prices)) + 1)]
        signal = macd_values[-1] if macd_values else 0.0
        
        # Calculate histogram
        histogram = macd - signal
        macd_histogram = histogram
        
        # Determine trend
        if macd > signal and macd > 0:
            trend = "bullish"
        elif macd < signal and macd < 0:
            trend = "bearish"
        else:
            trend = "neutral"
        
        return MACDResult(macd, signal, histogram, macd_histogram, trend)
    
    def _calculate_ema(self, symbol: str) -> EMAResult:
        """Calculate EMA (Exponential Moving Average)"""
        prices = self.price_history[symbol]
        if len(prices) < 200:
            return EMAResult(0.0, 0.0, 0.0, 0.0, "neutral")
        
        # Calculate EMAs
        ema_20 = self._calculate_ema_n(prices, 20)
        ema_50 = self._calculate_ema_n(prices, 50)
        ema_100 = self._calculate_ema_n(prices, 100)
        ema_200 = self._calculate_ema_n(prices, 200)
        
        # Determine trend based on EMA alignment
        if ema_20 > ema_50 > ema_100 > ema_200:
            trend = "strongly_bullish"
        elif ema_20 > ema_50 > ema_100:
            trend = "bullish"
        elif ema_20 > ema_50:
            trend = "moderately_bullish"
        elif ema_20 < ema_50 < ema_100 < ema_200:
            trend = "strongly_bearish"
        elif ema_20 < ema_50 < ema_100:
            trend = "bearish"
        elif ema_20 < ema_50:
            trend = "moderately_bearish"
        else:
            trend = "neutral"
        
        return EMAResult(ema_20, ema_50, ema_100, ema_200, trend)
    
    def _calculate_sma(self, symbol: str) -> SMAResult:
        """Calculate SMA (Simple Moving Average)"""
        prices = self.price_history[symbol]
        if len(prices) < 50:
            return SMAResult(0.0, 0.0, "neutral")
        
        # Calculate SMAs
        sma_50 = sum(prices[-50:]) / 50
        sma_200 = sum(prices[-200:]) / 200 if len(prices) >= 200 else sma_50
        
        # Determine crossover
        if sma_50 > sma_200:
            cross = "bullish_cross"
        elif sma_50 < sma_200:
            cross = "bearish_cross"
        else:
            cross = "neutral"
        
        return SMAResult(sma_50, sma_200, cross)
    
    def _calculate_bollinger_bands(self, symbol: str) -> BollingerBandsResult:
        """Calculate Bollinger Bands"""
        prices = self.price_history[symbol]
        if len(prices) < 20:
            return BollingerBandsResult(0.0, 0.0, 0.0, 0.0, 0.0, False)
        
        # Calculate SMA 20
        sma_20 = sum(prices[-20:]) / 20
        
        # Calculate standard deviation
        variance = sum((p - sma_20) ** 2 for p in prices[-20:]) / 20
        std_dev = variance ** 0.5
        
        # Calculate bands
        upper_band = sma_20 + (2 * std_dev)
        lower_band = sma_20 - (2 * std_dev)
        
        # Calculate bandwidth
        bandwidth = (upper_band - lower_band) / sma_20 * 100 if sma_20 > 0 else 0
        
        # Calculate %B
        current_price = prices[-1]
        percent_b = ((current_price - lower_band) / (upper_band - lower_band)) * 100 if (upper_band - lower_band) > 0 else 50
        
        # Determine squeeze
        squeeze = bandwidth < 10
        
        return BollingerBandsResult(upper_band, sma_20, lower_band, bandwidth, percent_b, squeeze)
    
    def _calculate_atr(self, symbol: str) -> ATRResult:
        """Calculate ATR (Average True Range)"""
        prices = self.price_history[symbol]
        highs = self.high_history.get(symbol) or prices
        lows = self.low_history.get(symbol) or prices
        
        if len(prices) < 14:
            return ATRResult(0.0, 0.0, "low")
        
        # Calculate True Range
        true_ranges = []
        for i in range(1, len(prices)):
            high = highs[i] if i < len(highs) else prices[i]
            low = lows[i] if i < len(lows) else prices[i]
            
            tr1 = high - low
            tr2 = abs(high - prices[i-1])
            tr3 = abs(low - prices[i-1])
            
            true_range = max(tr1, tr2, tr3)
            true_ranges.append(true_range)
        
        # Calculate ATR
        atr = sum(true_ranges[-14:]) / 14
        
        # Normalize ATR
        current_price = prices[-1]
        normalized_atr = (atr / current_price) * 100 if current_price > 0 else 0
        
        # Determine volatility
        if normalized_atr > 3:
            volatility = "high"
        elif normalized_atr > 1.5:
            volatility = "medium"
        else:
            volatility = "low"
        
        return ATRResult(atr, normalized_atr, volatility)
    
    def _calculate_adx(self, symbol: str) -> ADXResult:
        """Calculate ADX (Average Directional Index)"""
        prices = self.price_history[symbol]
        highs = self.high_history.get(symbol) or prices
        lows = self.low_history.get(symbol) or prices
        
        if len(prices) < 14:
            return ADXResult(0.0, 0.0, 0.0, "neutral", "neutral")
        
        # Calculate Directional Movement
        dm_plus = []
        dm_minus = []
        
        for i in range(1, len(prices)):
            high = highs[i] if i < len(highs) else prices[i]
            low = lows[i] if i < len(lows) else prices[i]
            
            up_move = high - prices[i-1]
            down_move = prices[i-1] - low
            
            if up_move > down_move and up_move > 0:
                dm_plus.append(up_move)
                dm_minus.append(0)
            elif down_move > up_move and down_move > 0:
                dm_plus.append(0)
                dm_minus.append(down_move)
            else:
                dm_plus.append(0)
                dm_minus.append(0)
        
        # Calculate smoothed values
        sm_dm_plus = sum(dm_plus[-14:]) / 14
        sm_dm_minus = sum(dm_minus[-14:]) / 14
        
        # Calculate TR (True Range) for normalization
        tr_values = []
        for i in range(1, len(prices)):
            high = highs[i] if i < len(highs) else prices[i]
            low = lows[i] if i < len(lows) else prices[i]
            
            tr1 = high - low
            tr2 = abs(high - prices[i-1])
            tr3 = abs(low - prices[i-1])
            
            tr_values.append(max(tr1, tr2, tr3))
        
        sm_tr = sum(tr_values[-14:]) / 14
        
        if sm_tr == 0:
            return ADXResult(0.0, 0.0, 0.0, "neutral", "neutral")
        
        # Calculate DI+
        di_plus = (sm_dm_plus / sm_tr) * 100
        di_minus = (sm_dm_minus / sm_tr) * 100
        
        # Calculate DX
        dx = abs(di_plus - di_minus) / ((di_plus + di_minus) / 2) * 100 if (di_plus + di_minus) > 0 else 0
        
        # Calculate ADX (smoothed DX)
        adx_values = [dx]  # Simplified - would need proper smoothing
        adx = sum(adx_values[-14:]) / 14
        
        # Determine trend strength
        if adx > 25:
            trend_strength = "strong"
        elif adx > 20:
            trend_strength = "moderate"
        else:
            trend_strength = "weak"
        
        # Determine trend direction
        if di_plus > di_minus:
            trend_direction = "bullish"
        elif di_minus > di_plus:
            trend_direction = "bearish"
        else:
            trend_direction = "neutral"
        
        return ADXResult(adx, di_plus, di_minus, trend_strength, trend_direction)
    
    def _calculate_stochastic(self, symbol: str) -> StochasticResult:
        """Calculate Stochastic Oscillator"""
        prices = self.price_history[symbol]
        highs = self.high_history.get(symbol) or prices
        lows = self.low_history.get(symbol) or prices
        
        if len(prices) < 14:
            return StochasticResult(50.0, 50.0, False, False, "neutral")
        
        # Find highest high and lowest low over last 14 periods
        recent_highs = highs[-14:] if len(highs) >= 14 else highs
        recent_lows = lows[-14:] if len(lows) >= 14 else lows
        
        highest_high = max(recent_highs)
        lowest_low = min(recent_lows)
        
        current_price = prices[-1]
        
        if highest_high == lowest_low:
            k = 50.0
        else:
            k = ((current_price - lowest_low) / (highest_high - lowest_low)) * 100
        
        # Calculate D (3-period SMA of K)
        k_values = []
        for i in range(1, min(16, len(prices)) + 1):
            price = prices[-i]
            high = highs[-i] if i <= len(highs) else price
            low = lows[-i] if i <= len(lows) else price
            
            if high == low:
                k_val = 50.0
            else:
                k_val = ((price - low) / (high - low)) * 100
            k_values.append(k_val)
        
        d = sum(k_values[-3:]) / 3 if len(k_values) >= 3 else k
        
        # Determine status
        overbought = k > 80
        oversold = k < 20
        
        if k > d and k > 50:
            trend = "bullish"
        elif k < d and k < 50:
            trend = "bearish"
        else:
            trend = "neutral"
        
        return StochasticResult(k, d, overbought, oversold, trend)
    
    def _calculate_vwap(self, symbol: str) -> VWAPResult:
        """Calculate VWAP (Volume Weighted Average Price)"""
        prices = self.price_history[symbol]
        volumes = self.volume_history[symbol]
        
        if len(prices) == 0 or len(volumes) == 0:
            return VWAPResult(0.0, 0.0, "neutral")
        
        # Calculate VWAP
        total_volume = sum(volumes)
        if total_volume == 0:
            return VWAPResult(0.0, 0.0, "neutral")
        
        vwap = sum(p * v for p, v in zip(prices, volumes)) / total_volume
        
        # Calculate deviation from current price
        current_price = prices[-1]
        deviation = ((current_price - vwap) / vwap) * 100 if vwap > 0 else 0
        
        # Determine trend
        if deviation > 1:
            trend = "above_vwap"
        elif deviation < -1:
            trend = "below_vwap"
        else:
            trend = "neutral"
        
        return VWAPResult(vwap, deviation, trend)
    
    def _calculate_obv(self, symbol: str) -> OBVResult:
        """Calculate OBV (On Balance Volume)"""
        prices = self.price_history[symbol]
        volumes = self.volume_history[symbol]
        
        if len(prices) < 2 or len(volumes) < 2:
            return OBVResult(0.0, "neutral", "neutral")
        
        # Calculate OBV
        obv_values = [0.0]
        for i in range(1, len(prices)):
            if prices[i] > prices[i-1]:
                obv_values.append(obv_values[-1] + volumes[i])
            elif prices[i] < prices[i-1]:
                obv_values.append(obv_values[-1] - volumes[i])
            else:
                obv_values.append(obv_values[-1])
        
        obv = obv_values[-1]
        
        # Determine OBV trend
        if len(obv_values) >= 5:
            recent_obv = obv_values[-5:]
            if all(obv_values[-i] > obv_values[-i-1] for i in range(1, 5)):
                obv_trend = "bullish"
            elif all(obv_values[-i] < obv_values[-i-1] for i in range(1, 5)):
                obv_trend = "bearish"
            else:
                obv_trend = "neutral"
        else:
            obv_trend = "neutral"
        
        # Determine volume trend
        if len(volumes) >= 5:
            recent_volumes = volumes[-5:]
            if all(recent_volumes[-i] > recent_volumes[-i-1] for i in range(1, 5)):
                volume_trend = "increasing"
            elif all(recent_volumes[-i] < recent_volumes[-i-1] for i in range(1, 5)):
                volume_trend = "decreasing"
            else:
                volume_trend = "neutral"
        else:
            volume_trend = "neutral"
        
        return OBVResult(obv, obv_trend, volume_trend)
    
    def _calculate_ichimoku(self, symbol: str) -> IchimokuResult:
        """Calculate Ichimoku Cloud"""
        prices = self.price_history[symbol]
        highs = self.high_history.get(symbol) or prices
        lows = self.low_history.get(symbol) or prices
        
        if len(prices) < 26:
            return IchimokuResult(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, "neutral", 0.0, 0.0)
        
        # Calculate Tenkan-sen (Conversion Line) - 9-period
        recent_highs = highs[-9:] if len(highs) >= 9 else highs
        recent_lows = lows[-9:] if len(lows) >= 9 else lows
        
        tenkan_sen = (max(recent_highs) + min(recent_lows)) / 2
        
        # Calculate Kijun-sen (Base Line) - 26-period
        recent_highs = highs[-26:] if len(highs) >= 26 else highs
        recent_lows = lows[-26:] if len(lows) >= 26 else lows
        
        kijun_sen = (max(recent_highs) + min(recent_lows)) / 2
        
        # Calculate Senkou Span A (Leading Span A) - (Tenkan + Kijun) / 2, shifted 26 periods
        senkou_span_a = (tenkan_sen + kijun_sen) / 2
        
        # Calculate Senkou Span B (Leading Span B) - 52-period high/low average, shifted 26 periods
        recent_highs = highs[-52:] if len(highs) >= 52 else highs
        recent_lows = lows[-52:] if len(lows) >= 52 else lows
        
        senkou_span_b = (max(recent_highs) + min(recent_lows)) / 2
        
        # Calculate Lagging Span (Lagging Span) - current price, shifted 26 periods
        lagging_span = prices[-1]
        
        # Calculate cloud thickness
        cloud_thickness = abs(senkou_span_a - senkou_span_b)
        
        # Determine cloud direction
        if senkou_span_a > senkou_span_b:
            cloud_direction = "bullish"
        elif senkou_span_a < senkou_span_b:
            cloud_direction = "bearish"
        else:
            cloud_direction = "neutral"
        
        return IchimokuResult(
            conversion_line=tenkan_sen,
            base_line=kijun_sen,
            leading_span1=senkou_span_a,
            leading_span2=senkou_span_b,
            lagging_span=lagging_span,
            cloud_thickness=cloud_thickness,
            cloud_direction=cloud_direction,
            tenkan_sen=tenkan_sen,
            kijun_sen=kijun_sen
        )
    
    def _calculate_fibonacci(self, symbol: str) -> FibonacciResult:
        """Calculate Fibonacci retracement levels"""
        prices = self.price_history[symbol]
        if len(prices) < 10:
            return FibonacciResult({0.0: 0.0, 0.236: 0.0, 0.382: 0.0, 0.5: 0.0, 0.618: 0.0, 0.786: 0.0}, 0.0, "none", 0.0)
        
        # Find recent swing high and low
        recent_prices = prices[-10:]  # Last 10 price points
        swing_high = max(recent_prices)
        swing_low = min(recent_prices)
        
        # Calculate Fibonacci levels
        price_range = swing_high - swing_low
        
        levels = {
            0.0: swing_high,
            0.236: swing_high - (price_range * 0.236),
            0.382: swing_high - (price_range * 0.382),
            0.5: swing_high - (price_range * 0.5),
            0.618: swing_high - (price_range * 0.618),
            0.786: swing_high - (price_range * 0.786)
        }
        
        current_price = prices[-1]
        
        # Find nearest level
        nearest_level = "none"
        nearest_distance = float('inf')
        
        for level, price in levels.items():
            distance = abs(current_price - price)
            if distance < nearest_distance:
                nearest_distance = distance
                nearest_level = str(level)
        
        return FibonacciResult(levels, current_price, nearest_level, nearest_distance)
    
    def _calculate_pivot_points(self, symbol: str) -> PivotPointsResult:
        """Calculate pivot points"""
        prices = self.price_history[symbol]
        highs = self.high_history.get(symbol) or prices
        lows = self.low_history.get(symbol) or prices
        
        if len(prices) < 1:
            return PivotPointsResult(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, "none")
        
        # Calculate pivot point
        current_high = highs[-1] if highs else prices[-1]
        current_low = lows[-1] if lows else prices[-1]
        current_close = prices[-1]
        
        pivot = (current_high + current_low + current_close) / 3
        
        # Calculate support and resistance levels
        r1 = 2 * pivot - current_low
        r2 = pivot + (current_high - current_low)
        r3 = current_high + 2 * (pivot - current_low)
        
        s1 = 2 * pivot - current_high
        s2 = pivot - (current_high - current_low)
        s3 = current_low - 2 * (current_high - pivot)
        
        # Determine position relative to pivot points
        if current_close > r1:
            position = "above_r1"
        elif current_close > pivot:
            position = "between_pivot_r1"
        elif current_close > s1:
            position = "between_s1_pivot"
        elif current_close > s2:
            position = "between_s2_s1"
        elif current_close > s3:
            position = "between_s3_s2"
        else:
            position = "below_s3"
        
        return PivotPointsResult(pivot, r1, r2, r3, s1, s2, s3, current_close, position)
    
    def _calculate_ema_n(self, prices: List[float], n: int) -> float:
        """Calculate EMA for a given period"""
        if len(prices) < n:
            return prices[-1]
        
        # Calculate SMA for first n values
        sma = sum(prices[:n]) / n
        
        # Calculate multiplier
        multiplier = 2 / (n + 1)
        
        # Calculate EMA
        ema = sma
        for price in prices[n:]:
            ema = (price - ema) * multiplier + ema
        
        return ema
    
    def _determine_overall_trend(self, rsi: RSIResult, macd: MACDResult, ema: EMAResult, 
                                 sma: SMAResult, adx: ADXResult, stochastic: StochasticResult) -> str:
        """Determine overall trend from all indicators"""
        bullish_count = 0
        bearish_count = 0
        
        # Count bullish indicators
        if rsi.trend in ["bullish", "overbought"]:
            bullish_count += 1
        elif rsi.trend in ["bearish", "oversold"]:
            bearish_count += 1
        
        if macd.trend == "bullish":
            bullish_count += 1
        elif macd.trend == "bearish":
            bearish_count += 1
        
        if ema.trend in ["bullish", "strongly_bullish", "moderately_bullish"]:
            bullish_count += 1
        elif ema.trend in ["bearish", "strongly_bearish", "moderately_bearish"]:
            bearish_count += 1
        
        if sma.cross in ["bullish_cross"]:
            bullish_count += 1
        elif sma.cross in ["bearish_cross"]:
            bearish_count += 1
        
        if adx.trend_direction == "bullish":
            bullish_count += 1
        elif adx.trend_direction == "bearish":
            bearish_count += 1
        
        if stochastic.trend == "bullish":
            bullish_count += 1
        elif stochastic.trend == "bearish":
            bearish_count += 1
        
        # Determine overall trend
        if bullish_count > bearish_count:
            return "bullish"
        elif bearish_count > bullish_count:
            return "bearish"
        else:
            return "neutral"
    
    def _calculate_momentum_score(self, rsi: RSIResult, macd: MACDResult, stochastic: StochasticResult) -> float:
        """Calculate momentum score from multiple indicators"""
        score = 0.0
        
        # RSI contribution
        if rsi.trend == "overbought":
            score += 1.0
        elif rsi.trend == "bullish":
            score += 0.5
        elif rsi.trend == "oversold":
            score -= 1.0
        elif rsi.trend == "bearish":
            score -= 0.5
        
        # MACD contribution
        if macd.trend == "bullish":
            score += 0.8
        elif macd.trend == "bearish":
            score -= 0.8
        
        # Stochastic contribution
        if stochastic.trend == "bullish":
            score += 0.6
        elif stochastic.trend == "bearish":
            score -= 0.6
        
        # Normalize to -1 to 1 range
        return max(-1.0, min(1.0, score / 2.4))
    
    def _calculate_volatility_score(self, atr: ATRResult, bollinger_bands: BollingerBandsResult) -> str:
        """Calculate volatility score"""
        if atr.volatility == "high":
            return "high"
        elif atr.volatility == "medium":
            return "medium"
        else:
            return "low"
    
    def _calculate_confidence_score(self, rsi: RSIResult, macd: MACDResult, adx: ADXResult, 
                                   stochastic: StochasticResult) -> float:
        """Calculate confidence score based on indicator alignment"""
        confidence = 0.5  # Base confidence
        
        # Check for alignment
        bullish_indicators = 0
        bearish_indicators = 0
        
        if rsi.trend in ["bullish", "overbought"]:
            bullish_indicators += 1
        elif rsi.trend in ["bearish", "oversold"]:
            bearish_indicators += 1
        
        if macd.trend == "bullish":
            bullish_indicators += 1
        elif macd.trend == "bearish":
            bearish_indicators += 1
        
        if adx.trend_direction == "bullish":
            bullish_indicators += 1
        elif adx.trend_direction == "bearish":
            bearish_indicators += 1
        
        if stochastic.trend == "bullish":
            bullish_indicators += 1
        elif stochastic.trend == "bearish":
            bearish_indicators += 1
        
        # Adjust confidence based on alignment
        if bullish_indicators >= 3 or bearish_indicators >= 3:
            confidence += 0.3
        elif bullish_indicators >= 2 or bearish_indicators >= 2:
            confidence += 0.15
        
        # Reduce confidence if indicators conflict
        if bullish_indicators > 0 and bearish_indicators > 0:
            confidence -= 0.2
        
        return max(0.0, min(1.0, confidence))

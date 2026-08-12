"""Optional MetaTrader 5 market-data adapter.

This module never imports MetaTrader5 at module load time.  GitHub Actions can
therefore import and test the bot without a terminal or the Windows package.
Returned candles use the existing normalized OHLCV dictionary structure.
"""

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from market_data_aggregator import MarketDataPoint

logger = logging.getLogger(__name__)


class MT5MarketData:
    TIMEFRAMES = {"M5": "TIMEFRAME_M5", "M15": "TIMEFRAME_M15", "H1": "TIMEFRAME_H1", "H4": "TIMEFRAME_H4", "D1": "TIMEFRAME_D1"}

    def __init__(self, symbol_map: Optional[Dict[str, str]] = None, mt5_module: Any = None):
        self.symbol_map = symbol_map or {
            "BTCUSD": os.getenv("MT5_BTCUSD_SYMBOL", "BTCUSD"),
            "XAUUSD": os.getenv("MT5_XAUUSD_SYMBOL", "XAUUSD"),
        }
        self.mt5 = mt5_module
        self.available = False
        if self.mt5 is None:
            try:
                import MetaTrader5 as mt5
                self.mt5 = mt5
            except ImportError:
                logger.info("MT5 provider: UNAVAILABLE (MetaTrader5 package not installed)")
                return
        self.available = self._initialize()
        logger.info("MT5 provider: %s", "AVAILABLE" if self.available else "UNAVAILABLE")

    def _initialize(self) -> bool:
        try:
            return bool(self.mt5.initialize())
        except Exception as error:
            logger.warning("MT5 provider unavailable: terminal initialization failed: %s", error)
            return False

    def _symbol(self, asset: str) -> Optional[str]:
        return self.symbol_map.get(asset)

    def current_quote(self, asset: str) -> Optional[MarketDataPoint]:
        if not self.available:
            return None
        symbol = self._symbol(asset)
        if not symbol or not self.mt5.symbol_select(symbol, True):
            return None
        tick = self.mt5.symbol_info_tick(symbol)
        if tick is None:
            return None
        bid = float(getattr(tick, "bid", 0.0) or 0.0)
        ask = float(getattr(tick, "ask", 0.0) or 0.0)
        last = float(getattr(tick, "last", 0.0) or 0.0) or (bid + ask) / 2
        if last <= 0:
            return None
        timestamp = datetime.fromtimestamp(float(getattr(tick, "time", 0) or 0), timezone.utc)
        return MarketDataPoint(asset, last, bid, ask, ask - bid, float(getattr(tick, "volume", 0) or 0), timestamp, "MT5", "mt5")

    def historical_candles(self, asset: str, timeframe: str, count: int = 1000) -> List[Dict[str, Any]]:
        if not self.available:
            return []
        symbol = self._symbol(asset)
        constant_name = self.TIMEFRAMES.get(timeframe)
        mt5_timeframe = getattr(self.mt5, constant_name, None) if constant_name else None
        if not symbol or mt5_timeframe is None or not self.mt5.symbol_select(symbol, True):
            return []
        rates = self.mt5.copy_rates_from_pos(symbol, mt5_timeframe, 0, count)
        if rates is None:
            return []
        candles = []
        for row in rates:
            try:
                candles.append({
                    "timestamp": datetime.fromtimestamp(float(row["time"]), timezone.utc),
                    "open": float(row["open"]), "high": float(row["high"]),
                    "low": float(row["low"]), "close": float(row["close"]),
                    "volume": float(row["tick_volume"]),
                })
            except (KeyError, TypeError, ValueError):
                continue
        return candles

    def health_check(self) -> Dict[str, Any]:
        return {"available": self.available, "provider": "MT5"}

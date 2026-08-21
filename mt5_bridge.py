"""Optional, read-only MetaTrader 5 bridge for Windows terminals.

The official MetaTrader5 package is imported conditionally.  This module never
places, modifies, or closes orders; READ_ONLY is enforced by the execution
adapter itself as a second safety boundary.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)

TIMEFRAMES = {"M1": "TIMEFRAME_M1", "M5": "TIMEFRAME_M5", "M15": "TIMEFRAME_M15", "H1": "TIMEFRAME_H1", "H4": "TIMEFRAME_H4", "D1": "TIMEFRAME_D1"}


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def normalize_timestamp(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        stamp = value
    elif isinstance(value, str):
        try:
            stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            try:
                value = float(value)
            except ValueError:
                return None
            return normalize_timestamp(value)
    elif isinstance(value, (int, float)):
        number = float(value)
        if number > 10**11:
            number /= 1000.0
        try:
            stamp = datetime.fromtimestamp(number, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    else:
        return None
    return stamp.replace(tzinfo=timezone.utc) if stamp.tzinfo is None else stamp.astimezone(timezone.utc)


def _field(row: Any, name: str, default: Any = None) -> Any:
    if isinstance(row, dict):
        return row.get(name, default)
    return getattr(row, name, default)


@dataclass(frozen=True)
class MT5SymbolMapper:
    mappings: Dict[str, str]

    @classmethod
    def from_environment(cls, config: Any = None) -> "MT5SymbolMapper":
        return cls({
            "BTCUSD": getattr(config, "mt5_btcusd_symbol", None) or os.getenv("MT5_BTCUSD_SYMBOL", "BTCUSD"),
            "XAUUSD": getattr(config, "mt5_xauusd_symbol", None) or os.getenv("MT5_XAUUSD_SYMBOL", "XAUUSD"),
        })

    def broker_symbol(self, asset: str) -> str:
        return self.mappings.get(asset, asset)


class MT5Connection:
    def __init__(self, enabled: Optional[bool] = None, mode: Optional[str] = None, terminal_path: Optional[str] = None, module: Any = None):
        self.enabled = self._bool(enabled if enabled is not None else os.getenv("MT5_ENABLED", "false"))
        self.mode = str(mode or os.getenv("MT5_MODE", "READ_ONLY")).upper()
        self.terminal_path = terminal_path if terminal_path is not None else os.getenv("MT5_TERMINAL_PATH", "")
        self.mt5 = module
        self.connected = False
        self.last_error: Optional[str] = None

    @staticmethod
    def _bool(value: Any) -> bool:
        return value is True or str(value).strip().lower() in {"1", "true", "yes", "on"}

    def _load(self) -> Any:
        if self.mt5 is None:
            try:
                import MetaTrader5 as mt5
                self.mt5 = mt5
            except ImportError:
                self.last_error = "MetaTrader5 package is not installed"
                return None
        return self.mt5

    def connect(self) -> bool:
        if not self.enabled:
            self.last_error = "MT5 disabled"
            return False
        mt5 = self._load()
        if mt5 is None:
            return False
        try:
            initialized = mt5.initialize(self.terminal_path) if self.terminal_path else mt5.initialize()
            if not initialized:
                self.last_error = "MT5 initialize failed"
                return False
            login = os.getenv("MT5_LOGIN", "").strip()
            password = os.getenv("MT5_PASSWORD", "").strip()
            server = os.getenv("MT5_SERVER", "").strip()
            if login:
                kwargs = {"login": int(login)}
                if password:
                    kwargs["password"] = password
                if server:
                    kwargs["server"] = server
                if not mt5.login(**kwargs):
                    self.last_error = "MT5 login failed"
                    mt5.shutdown()
                    return False
            self.connected = True
            self.last_error = None
            return True
        except Exception as exc:
            self.last_error = f"MT5 connection error: {type(exc).__name__}"
            self.connected = False
            return False

    def shutdown(self) -> None:
        if self.mt5 is not None:
            try:
                self.mt5.shutdown()
            except Exception:
                logger.exception("MT5 shutdown failed")
        self.connected = False

    def check_connection(self) -> Dict[str, Any]:
        terminal = self.mt5.terminal_info() if self.connected and self.mt5 else None
        account = self.mt5.account_info() if self.connected and self.mt5 else None
        return {"status": "CONNECTED" if self.connected else "DISCONNECTED", "terminal_connected": terminal is not None, "account_connected": account is not None, "error": self.last_error}


@dataclass
class ExecutionReference:
    broker_symbol: str
    bid: float
    ask: float
    spread: float
    point: float
    digits: int
    trade_mode: Any
    execution_mode: str
    minimum_volume: float
    volume_step: float
    maximum_volume: float


class MT5MarketData:
    def __init__(self, connection: MT5Connection, mapper: Optional[MT5SymbolMapper] = None):
        self.connection = connection
        self.mapper = mapper or MT5SymbolMapper.from_environment()

    def check_symbol(self, asset: str) -> Dict[str, Any]:
        symbol = self.mapper.broker_symbol(asset)
        info = self.connection.mt5.symbol_info(symbol) if self.connection.connected else None
        return {"asset": asset, "symbol": symbol, "available": info is not None, "error": None if info else "symbol unavailable"}

    def get_tick(self, asset: str) -> Optional[Dict[str, Any]]:
        if not self.connection.connected:
            return None
        symbol = self.mapper.broker_symbol(asset)
        if not self.connection.mt5.symbol_select(symbol, True):
            return None
        tick = self.connection.mt5.symbol_info_tick(symbol)
        if tick is None:
            return None
        bid, ask = _number(_field(tick, "bid")), _number(_field(tick, "ask"))
        last = _number(_field(tick, "last"), (bid + ask) / 2 if bid and ask else 0.0)
        return {"asset": asset, "broker_symbol": symbol, "bid": bid, "ask": ask, "last": last, "spread": ask - bid if ask and bid else 0.0, "volume": _number(_field(tick, "volume")), "timestamp": normalize_timestamp(_field(tick, "time"))}

    def get_ohlcv(self, asset: str, timeframe: str = "M5", count: int = 100) -> List[Dict[str, Any]]:
        if not self.connection.connected or timeframe not in TIMEFRAMES:
            return []
        symbol = self.mapper.broker_symbol(asset)
        if not self.connection.mt5.symbol_select(symbol, True):
            return []
        tf = getattr(self.connection.mt5, TIMEFRAMES[timeframe], None)
        if tf is None:
            return []
        rows = self.connection.mt5.copy_rates_from_pos(symbol, tf, 0, int(count)) or []
        result = []
        for row in rows:
            stamp = normalize_timestamp(_field(row, "time"))
            values = {"timestamp": stamp, "open": _number(_field(row, "open")), "high": _number(_field(row, "high")), "low": _number(_field(row, "low")), "close": _number(_field(row, "close")), "volume": _number(_field(row, "tick_volume", _field(row, "volume", 0.0)))}
            if stamp is None or values["open"] <= 0 or values["high"] <= 0 or values["low"] <= 0 or values["close"] <= 0 or values["high"] < values["low"]:
                continue
            result.append(values)
        return sorted(result, key=lambda row: row["timestamp"])

    def execution_reference(self, asset: str) -> Optional[ExecutionReference]:
        symbol = self.mapper.broker_symbol(asset)
        info = self.connection.mt5.symbol_info(symbol) if self.connection.connected else None
        tick = self.get_tick(asset)
        if info is None or tick is None:
            return None
        return ExecutionReference(symbol, tick["bid"], tick["ask"], tick["spread"], _number(_field(info, "point")), int(_number(_field(info, "digits"))), _field(info, "trade_mode"), self.connection.mode, _number(_field(info, "volume_min")), _number(_field(info, "volume_step")), _number(_field(info, "volume_max")))

    def check_market_data(self, asset: str, timeframe: str = "M5", count: int = 100) -> Dict[str, Any]:
        bars = self.get_ohlcv(asset, timeframe, count)
        return {"asset": asset, "timeframe": timeframe, "available": bool(bars), "candles": len(bars), "latest": bars[-1]["timestamp"].isoformat() if bars else None}


class MT5AccountReader:
    def __init__(self, connection: MT5Connection): self.connection = connection
    def read(self) -> Optional[Dict[str, Any]]:
        info = self.connection.mt5.account_info() if self.connection.connected else None
        if info is None: return None
        return {key: _field(info, key) for key in ("balance", "equity", "margin", "margin_free", "margin_level", "currency", "leverage")}
    def check_account(self) -> Dict[str, Any]: return {"available": self.read() is not None}


class MT5PositionReader:
    def __init__(self, connection: MT5Connection, mapper: Optional[MT5SymbolMapper] = None): self.connection, self.mapper = connection, mapper or MT5SymbolMapper.from_environment()
    def read(self, assets: Iterable[str] = ("BTCUSD", "XAUUSD")) -> List[Dict[str, Any]]:
        if not self.connection.connected: return []
        symbols = [self.mapper.broker_symbol(asset) for asset in assets]
        rows = self.connection.mt5.positions_get() or []
        result = []
        for row in rows:
            if _field(row, "symbol") not in symbols: continue
            result.append({"ticket": _field(row, "ticket"), "symbol": _field(row, "symbol"), "direction": "BUY" if _field(row, "type") == getattr(self.connection.mt5, "POSITION_TYPE_BUY", 0) else "SELL", "volume": _number(_field(row, "volume")), "entry_price": _number(_field(row, "price_open")), "current_price": _number(_field(row, "price_current")), "stop_loss": _number(_field(row, "sl")), "take_profit": _number(_field(row, "tp")), "profit": _number(_field(row, "profit")), "swap": _number(_field(row, "swap")), "magic": _field(row, "magic"), "comment": _field(row, "comment"), "open_time": normalize_timestamp(_field(row, "time"))})
        return result


class MT5HealthMonitor:
    def __init__(self, connection: MT5Connection, market_data: MT5MarketData, account: MT5AccountReader): self.connection, self.market_data, self.account = connection, market_data, account
    def report(self) -> Dict[str, Any]:
        status = self.connection.check_connection()
        return {"mt5": {"status": status["status"], "terminal": "CONNECTED" if status["terminal_connected"] else "DISCONNECTED", "account": "AVAILABLE" if status["account_connected"] else "UNAVAILABLE", "mode": self.connection.mode, "execution": "DISABLED", "symbols": {asset: self.market_data.check_symbol(asset)["available"] for asset in ("BTCUSD", "XAUUSD")}}}
    def check_connection(self): return self.connection.check_connection()
    def check_symbol(self, asset): return self.market_data.check_symbol(asset)
    def check_market_data(self, asset, timeframe="M5", count=100): return self.market_data.check_market_data(asset, timeframe, count)
    def check_account(self): return self.account.check_account()


class TradeExecutionInterface:
    def open_position(self, *args, **kwargs): raise NotImplementedError
    def close_position(self, *args, **kwargs): raise NotImplementedError
    def modify_position(self, *args, **kwargs): raise NotImplementedError


class PaperExecutionAdapter(TradeExecutionInterface):
    def __init__(self, simulator: Any = None): self.simulator = simulator
    def open_candidate(self, candidate: Any, market_analysis: Any = None):
        if self.simulator is None:
            return None
        return self.simulator.execute_candidate(candidate, market_analysis)
    def open_position(self, *args, **kwargs):
        if self.simulator is None: return None
        return self.simulator.execute_trade(*args, **kwargs)
    def close_position(self, *args, **kwargs): raise NotImplementedError("Use the existing simulator close path")
    def modify_position(self, *args, **kwargs): raise NotImplementedError("Use the existing simulator modify path")


class MT5ExecutionAdapter(TradeExecutionInterface):
    def __init__(self, connection: MT5Connection): self.connection = connection
    def _refuse(self): raise RuntimeError("MT5 execution is disabled; bridge is READ_ONLY")
    def open_position(self, *args, **kwargs): self._refuse()
    def close_position(self, *args, **kwargs): self._refuse()
    def modify_position(self, *args, **kwargs): self._refuse()
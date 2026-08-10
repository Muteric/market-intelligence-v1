"""Optional MT5 execution boundary.

The GitHub-hosted intelligence engine remains signal-only/simulation-only.  A
Windows-side adapter can implement this interface later without coupling the
market-data and decision engines to the MetaTrader5 package.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional


class ExecutionMode(Enum):
    SIGNAL_ONLY = "signal_only"
    SIMULATION = "simulation"
    PAPER = "paper"
    LIVE = "live"


class MT5ExecutionBridge(ABC):
    """Contract for a future Windows MT5 bridge; no live implementation here."""

    mode = ExecutionMode.SIGNAL_ONLY

    @abstractmethod
    def connect(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def get_account(self) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def get_symbol_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def open_buy(self, symbol: str, volume: float, **kwargs: Any) -> Any:
        raise NotImplementedError

    @abstractmethod
    def open_sell(self, symbol: str, volume: float, **kwargs: Any) -> Any:
        raise NotImplementedError

    @abstractmethod
    def close_position(self, position_id: str, **kwargs: Any) -> Any:
        raise NotImplementedError

    @abstractmethod
    def get_positions(self) -> List[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_trade_history(self) -> List[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        raise NotImplementedError

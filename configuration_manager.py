"""
Configuration Manager for AI Trading Intelligence Bot
Handles all configurable settings including portfolio parameters, trading rules, and asset configurations.
"""

import json
import os
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional
from pathlib import Path


def _coerce_int(name: str, value: Any) -> int:
    try:
        if isinstance(value, bool):
            raise ValueError
        return int(value)
    except (TypeError, ValueError):
        raise ValueError(f"Configuration error: {name} must be an integer, received {type(value).__name__}")


def _coerce_float(name: str, value: Any) -> float:
    try:
        if isinstance(value, bool):
            raise ValueError
        return float(value)
    except (TypeError, ValueError):
        raise ValueError(f"Configuration error: {name} must be numeric, received {type(value).__name__}")


def _coerce_bool(name: str, value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.strip().lower() in {"true", "1", "yes", "on"}:
        return True
    if isinstance(value, str) and value.strip().lower() in {"false", "0", "no", "off"}:
        return False
    raise ValueError(f"Configuration error: {name} must be boolean, received {type(value).__name__}")

def _environment_value(name: str, default: str = "") -> str:
    """Read process environment first, then an optional local .env file."""
    value = os.getenv(name)
    if value:
        return value
    dotenv = Path(".env")
    if dotenv.exists():
        for line in dotenv.read_text(encoding="utf-8").splitlines():
            key, separator, raw_value = line.partition("=")
            if separator and key.strip() == name:
                return raw_value.strip().strip('"').strip("'")
    return default

@dataclass
class PortfolioConfig:
    """Portfolio configuration settings"""
    initial_balance: float = 100.0
    base_position_size: float = 0.5  # 50% of account balance
    scaling_position_size: float = 0.25  # 25% of account balance
    leverage: float = 400.0
    max_positions: int = 3
    max_open_positions: int = 3

    def __post_init__(self) -> None:
        self.initial_balance = _coerce_float("initial_balance", self.initial_balance)
        self.base_position_size = _coerce_float("base_position_size", self.base_position_size)
        self.scaling_position_size = _coerce_float("scaling_position_size", self.scaling_position_size)
        self.leverage = _coerce_float("leverage", self.leverage)
        self.max_positions = _coerce_int("max_positions", self.max_positions)
        self.max_open_positions = _coerce_int("max_open_positions", self.max_open_positions)
@dataclass
class AssetConfig:
    """Asset-specific configuration"""
    symbol: str
    enabled: bool = True
    min_confidence: float = 0.5
    max_volatility: str = "high"  # low, medium, high
    analysis_interval_minutes: int = 15
    allocation_percentage: Optional[float] = None

    def __post_init__(self) -> None:
        self.min_confidence = _coerce_float("min_confidence", self.min_confidence)
        self.analysis_interval_minutes = _coerce_int("analysis_interval_minutes", self.analysis_interval_minutes)
        if self.allocation_percentage is not None:
            self.allocation_percentage = _coerce_float("allocation_percentage", self.allocation_percentage)
        self.enabled = _coerce_bool("enabled", self.enabled)
@dataclass
class TradingConfig:
    """Trading configuration settings"""
    confidence_change_threshold: float = 0.15
    max_daily_trades: int = 10
    max_weekly_trades: int = 50
    max_monthly_trades: int = 200
    stop_loss_percentage: float = 0.05  # 5%
    take_profit_percentage: float = 0.15  # 15%
    trailing_stop_enabled: bool = True
    trailing_stop_percentage: float = 0.03  # 3%

    def __post_init__(self) -> None:
        self.confidence_change_threshold = _coerce_float("confidence_change_threshold", self.confidence_change_threshold)
        self.max_daily_trades = _coerce_int("max_daily_trades", self.max_daily_trades)
        self.max_weekly_trades = _coerce_int("max_weekly_trades", self.max_weekly_trades)
        self.max_monthly_trades = _coerce_int("max_monthly_trades", self.max_monthly_trades)
        self.stop_loss_percentage = _coerce_float("stop_loss_percentage", self.stop_loss_percentage)
        self.take_profit_percentage = _coerce_float("take_profit_percentage", self.take_profit_percentage)
        self.trailing_stop_percentage = _coerce_float("trailing_stop_percentage", self.trailing_stop_percentage)
        self.trailing_stop_enabled = _coerce_bool("trailing_stop_enabled", self.trailing_stop_enabled)
@dataclass
class SystemConfig:
    """System-wide configuration"""
    telegram_token: str = ""
    telegram_chat_id: str = "843487976"
    alert_state_file: str = ".market_alert_state.json"
    trade_history_file: str = "trade_history.json"
    portfolio_stats_file: str = "portfolio_stats.json"
    log_file: str = "trading_bot.log"
    data_directory: str = "data"
    backup_enabled: bool = True
    auto_recovery: bool = True
    max_backup_files: int = 10
    xauusd_data_providers: str = "goldprice_dev,goldapi,mt5,itick"
    xauusd_provider_priority: str = "goldprice_dev,mt5,goldapi,itick"
    goldapi_enabled: bool = True
    goldapi_min_interval_seconds: int = 300
    goldprice_dev_enabled: bool = True
    itick_enabled: bool = True
    mt5_enabled: bool = True
    mt5_mode: str = "READ_ONLY"
    mt5_terminal_path: str = ""
    mt5_btcusd_symbol: str = "BTCUSD"
    mt5_xauusd_symbol: str = "XAUUSD"
    xau_max_stale_seconds: int = 60
    max_price_deviation_percent: float = 1.0
    min_valid_providers: int = 1
    price_consensus_method: str = "median"
    execution_mode: str = "simulation"
    notification_dedupe_seconds: int = 900
    signal_min_score: float = 65.0
    signal_min_confirmations: int = 3
    simulation_mode: str = "AUTO"
    trading_mode_enabled: bool = True
    aggressive_min_pips: float = 10.0
    aggressive_max_pips: float = 25.0
    moderate_min_pips: float = 20.0
    moderate_max_pips: float = 50.0
    slow_min_pips: float = 100.0
    slow_max_pips: float = 200.0
    simulation_stop_loss_pips: float = 50.0
    trailing_activation_pips: float = 20.0
    trailing_step_pips: float = 10.0
    candidate_watch_score: float = 50.0
    minimum_risk_reward: float = 1.5
    aggressive_min_score: float = 70.0
    moderate_min_score: float = 65.0
    slow_min_score: float = 75.0
    aggressive_min_confirmations: int = 3
    moderate_min_confirmations: int = 3
    slow_min_confirmations: int = 4
    adaptive_learning_min_outcomes: int = 30
    def __post_init__(self) -> None:
        self.max_backup_files = _coerce_int("max_backup_files", self.max_backup_files)
        self.goldapi_min_interval_seconds = _coerce_int("goldapi_min_interval_seconds", self.goldapi_min_interval_seconds)
        self.xau_max_stale_seconds = _coerce_int("xau_max_stale_seconds", self.xau_max_stale_seconds)
        self.max_price_deviation_percent = _coerce_float("max_price_deviation_percent", self.max_price_deviation_percent)
        self.min_valid_providers = _coerce_int("min_valid_providers", self.min_valid_providers)
        self.notification_dedupe_seconds = _coerce_int("notification_dedupe_seconds", self.notification_dedupe_seconds)
        self.trading_mode_enabled = _coerce_bool("trading_mode_enabled", self.trading_mode_enabled)
        for name in ("aggressive_min_pips", "aggressive_max_pips", "moderate_min_pips", "moderate_max_pips", "slow_min_pips", "slow_max_pips"):
            setattr(self, name, _coerce_float(name, getattr(self, name)))
        self.signal_min_score = _coerce_float("signal_min_score", self.signal_min_score)
        self.signal_min_confirmations = _coerce_int("signal_min_confirmations", self.signal_min_confirmations)
        self.simulation_stop_loss_pips = _coerce_float("simulation_stop_loss_pips", self.simulation_stop_loss_pips)
        self.trailing_activation_pips = _coerce_float("trailing_activation_pips", self.trailing_activation_pips)
        self.trailing_step_pips = _coerce_float("trailing_step_pips", self.trailing_step_pips)
        self.candidate_watch_score = _coerce_float("candidate_watch_score", self.candidate_watch_score)
        self.minimum_risk_reward = _coerce_float("minimum_risk_reward", self.minimum_risk_reward)
        self.aggressive_min_score = _coerce_float("aggressive_min_score", self.aggressive_min_score)
        self.moderate_min_score = _coerce_float("moderate_min_score", self.moderate_min_score)
        self.slow_min_score = _coerce_float("slow_min_score", self.slow_min_score)
        self.aggressive_min_confirmations = _coerce_int("aggressive_min_confirmations", self.aggressive_min_confirmations)
        self.moderate_min_confirmations = _coerce_int("moderate_min_confirmations", self.moderate_min_confirmations)
        self.slow_min_confirmations = _coerce_int("slow_min_confirmations", self.slow_min_confirmations)
        self.adaptive_learning_min_outcomes = _coerce_int("adaptive_learning_min_outcomes", self.adaptive_learning_min_outcomes)
        for field in ("backup_enabled", "auto_recovery", "goldapi_enabled", "goldprice_dev_enabled", "itick_enabled", "mt5_enabled"):
            setattr(self, field, _coerce_bool(field, getattr(self, field)))

@dataclass
class AppConfig:
    """Main application configuration"""
    portfolio: PortfolioConfig
    assets: Dict[str, AssetConfig]
    trading: TradingConfig
    system: SystemConfig

class ConfigurationManager:
    """Manages application configuration with persistence"""
    
    def __init__(self, config_file: str = "app_config.json"):
        self.config_file = config_file
        self._config = None
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from file or create default"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._config = self._deserialize_config(data)
            except (json.JSONDecodeError, OSError):
                self._config = self._create_default_config()
        else:
            self._config = self._create_default_config()
            self._save_config()
    
    def _create_default_config(self) -> AppConfig:
        """Create default configuration"""
        portfolio = PortfolioConfig()
        
        assets = {
            "BTCUSD": AssetConfig(
                symbol="BTCUSD",
                enabled=True,
                min_confidence=0.5,
                max_volatility="high",
                analysis_interval_minutes=15,
                allocation_percentage=0.5,
            ),
            "XAUUSD": AssetConfig(
                symbol="XAUUSD",
                enabled=True,
                min_confidence=0.5,
                max_volatility="high",
                analysis_interval_minutes=15,
                allocation_percentage=0.5,
            )
        }
        
        trading = TradingConfig()
        system = SystemConfig(
            telegram_token=_environment_value('TELEGRAM_TOKEN'),
            telegram_chat_id=_environment_value('TELEGRAM_CHAT_ID', '843487976'),
            xauusd_data_providers=_environment_value('XAUUSD_DATA_PROVIDERS', 'goldprice_dev,twelvedata,yahoo_finance,goldapi,mt5,itick'),
            xauusd_provider_priority=_environment_value('XAUUSD_PROVIDER_PRIORITY', 'goldprice_dev,twelvedata,yahoo_finance,goldapi,mt5,itick'),
            goldapi_enabled=_environment_value('GOLDAPI_ENABLED', 'true').lower() == 'true',
            goldprice_dev_enabled=_environment_value('GOLDPRICEDEV_ENABLED', 'true').lower() == 'true',
            itick_enabled=_environment_value('ITICK_ENABLED', 'true').lower() == 'true',
            mt5_enabled=_environment_value('MT5_ENABLED', 'false').lower() == 'true',
            mt5_mode=_environment_value('MT5_MODE', 'READ_ONLY'),
            mt5_terminal_path=_environment_value('MT5_TERMINAL_PATH', ''),
            mt5_btcusd_symbol=_environment_value('MT5_BTCUSD_SYMBOL', 'BTCUSD'),
            mt5_xauusd_symbol=_environment_value('MT5_XAUUSD_SYMBOL', 'XAUUSD'),
            xau_max_stale_seconds=int(_environment_value('XAU_MAX_STALE_SECONDS', '60')),
            max_price_deviation_percent=float(_environment_value('MAX_PRICE_DEVIATION_PERCENT', '1.0')),
            min_valid_providers=int(_environment_value('MIN_VALID_PROVIDERS', '1')),
            price_consensus_method=_environment_value('PRICE_CONSENSUS_METHOD', 'median'),
            execution_mode=_environment_value('EXECUTION_MODE', 'simulation'),
            notification_dedupe_seconds=int(_environment_value('NOTIFICATION_DEDUPE_SECONDS', '900')),
        )
        
        return AppConfig(
            portfolio=portfolio,
            assets=assets,
            trading=trading,
            system=system
        )
    
    def _deserialize_config(self, data: Dict[str, Any]) -> AppConfig:
        """Deserialize configuration from JSON"""
        portfolio_data = data.get('portfolio', {})
        portfolio = PortfolioConfig(
            initial_balance=float(portfolio_data.get('initial_balance', 100.0)),
            base_position_size=float(portfolio_data.get('base_position_size', 0.5)),
            scaling_position_size=float(portfolio_data.get('scaling_position_size', 0.25)),
            leverage=float(portfolio_data.get('leverage', 400.0)),
            max_positions=int(portfolio_data.get('max_positions', 3)),
            max_open_positions=int(portfolio_data.get('max_open_positions', 3))
        )
        
        assets_data = data.get('assets', {})
        assets = {}
        enabled_asset_count = sum(
            1 for asset_data in assets_data.values()
            if asset_data.get('enabled', True)
        )
        equal_allocation = 1.0 / enabled_asset_count if enabled_asset_count else 0.0
        for symbol, asset_data in assets_data.items():
            assets[symbol] = AssetConfig(
                symbol=symbol,
                enabled=asset_data.get('enabled', True),
                min_confidence=float(asset_data.get('min_confidence', 0.5)),
                max_volatility=asset_data.get('max_volatility', 'high'),
                analysis_interval_minutes=int(asset_data.get('analysis_interval_minutes', 15)),
                allocation_percentage=(
                    float(asset_data['allocation_percentage'])
                    if asset_data.get('allocation_percentage') is not None
                    else (equal_allocation if asset_data.get('enabled', True) else 0.0)
                )
            )
        
        trading_data = data.get('trading', {})
        trading = TradingConfig(
            confidence_change_threshold=float(trading_data.get('confidence_change_threshold', 0.15)),
            max_daily_trades=int(trading_data.get('max_daily_trades', 10)),
            max_weekly_trades=int(trading_data.get('max_weekly_trades', 50)),
            max_monthly_trades=int(trading_data.get('max_monthly_trades', 200)),
            stop_loss_percentage=float(trading_data.get('stop_loss_percentage', 0.05)),
            take_profit_percentage=float(trading_data.get('take_profit_percentage', 0.15)),
            trailing_stop_enabled=trading_data.get('trailing_stop_enabled', True),
            trailing_stop_percentage=float(trading_data.get('trailing_stop_percentage', 0.03))
        )
        
        system_data = data.get('system', {})
        configured_xau_providers = system_data.get('xauusd_data_providers', 'goldprice_dev,twelvedata,yahoo_finance,goldapi,mt5,itick')
        configured_xau_priority = system_data.get('xauusd_provider_priority', 'goldprice_dev,twelvedata,yahoo_finance,goldapi,mt5,itick')
        if configured_xau_providers == 'goldprice_dev,goldapi,mt5,itick':
            configured_xau_providers = 'goldprice_dev,twelvedata,yahoo_finance,goldapi,mt5,itick'
        if configured_xau_priority == 'goldprice_dev,mt5,goldapi,itick':
            configured_xau_priority = 'goldprice_dev,twelvedata,yahoo_finance,goldapi,mt5,itick'
        system = SystemConfig(
            telegram_token=system_data.get('telegram_token', '') or _environment_value('TELEGRAM_TOKEN'),
            telegram_chat_id=system_data.get('telegram_chat_id', '') or _environment_value('TELEGRAM_CHAT_ID', '843487976'),
            alert_state_file=system_data.get('alert_state_file', '.market_alert_state.json'),
            trade_history_file=system_data.get('trade_history_file', 'trade_history.json'),
            portfolio_stats_file=system_data.get('portfolio_stats_file', 'portfolio_stats.json'),
            log_file=system_data.get('log_file', 'trading_bot.log'),
            data_directory=system_data.get('data_directory', 'data'),
            backup_enabled=system_data.get('backup_enabled', True),
            auto_recovery=system_data.get('auto_recovery', True),
            max_backup_files=int(system_data.get('max_backup_files', 10)),
            xauusd_data_providers=configured_xau_providers,
            xauusd_provider_priority=configured_xau_priority,
            goldapi_enabled=bool(system_data.get('goldapi_enabled', True)),
            goldapi_min_interval_seconds=int(system_data.get('goldapi_min_interval_seconds', 300)),
            goldprice_dev_enabled=bool(system_data.get('goldprice_dev_enabled', True)),
            itick_enabled=bool(system_data.get('itick_enabled', True)),
            mt5_enabled=bool(system_data.get('mt5_enabled', False)),
            mt5_mode=system_data.get('mt5_mode', 'READ_ONLY'),
            mt5_terminal_path=system_data.get('mt5_terminal_path', ''),
            mt5_btcusd_symbol=system_data.get('mt5_btcusd_symbol', 'BTCUSD'),
            mt5_xauusd_symbol=system_data.get('mt5_xauusd_symbol', 'XAUUSD'),
            xau_max_stale_seconds=int(system_data.get('xau_max_stale_seconds', 60)),
            max_price_deviation_percent=float(system_data.get('max_price_deviation_percent', 1.0)),
            min_valid_providers=int(system_data.get('min_valid_providers', 1)),
            price_consensus_method=system_data.get('price_consensus_method', 'median'),
            execution_mode=system_data.get('execution_mode', 'simulation'),
            notification_dedupe_seconds=int(system_data.get('notification_dedupe_seconds', 900)),
            signal_min_score=float(system_data.get('signal_min_score', 65.0)),
            signal_min_confirmations=int(system_data.get('signal_min_confirmations', 3)),
            simulation_mode=system_data.get('simulation_mode', 'AUTO'),
            trading_mode_enabled=bool(system_data.get('trading_mode_enabled', True)),
            aggressive_min_pips=float(system_data.get('aggressive_min_pips', 10.0)),
            aggressive_max_pips=float(system_data.get('aggressive_max_pips', 25.0)),
            moderate_min_pips=float(system_data.get('moderate_min_pips', 20.0)),
            moderate_max_pips=float(system_data.get('moderate_max_pips', 50.0)),
            slow_min_pips=float(system_data.get('slow_min_pips', 100.0)),
            slow_max_pips=float(system_data.get('slow_max_pips', 200.0)),
            simulation_stop_loss_pips=float(system_data.get('simulation_stop_loss_pips', 50.0)),
            trailing_activation_pips=float(system_data.get('trailing_activation_pips', 20.0)),
            trailing_step_pips=float(system_data.get('trailing_step_pips', 10.0)),
            candidate_watch_score=float(system_data.get('candidate_watch_score', 50.0)),
            minimum_risk_reward=float(system_data.get('minimum_risk_reward', 1.5)),
            aggressive_min_score=float(system_data.get('aggressive_min_score', 70.0)),
            moderate_min_score=float(system_data.get('moderate_min_score', 65.0)),
            slow_min_score=float(system_data.get('slow_min_score', 75.0)),
            aggressive_min_confirmations=int(system_data.get('aggressive_min_confirmations', 3)),
            moderate_min_confirmations=int(system_data.get('moderate_min_confirmations', 3)),
            slow_min_confirmations=int(system_data.get('slow_min_confirmations', 4)),
            adaptive_learning_min_outcomes=int(system_data.get('adaptive_learning_min_outcomes', 30))
        )
        
        return AppConfig(
            portfolio=portfolio,
            assets=assets,
            trading=trading,
            system=system
        )
    
    def _serialize_config(self) -> Dict[str, Any]:
        """Serialize configuration to JSON"""
        return {
            'portfolio': asdict(self._config.portfolio),
            'assets': {symbol: asdict(asset) for symbol, asset in self._config.assets.items()},
            'trading': asdict(self._config.trading),
            'system': {
                **asdict(self._config.system),
                'telegram_token': '',
            }
        }
    
    def _save_config(self) -> None:
        """Save configuration to file"""
        # Ensure data directory exists
        os.makedirs(self._config.system.data_directory, exist_ok=True)
        
        config_path = os.path.join(self._config.system.data_directory, self.config_file)
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(self._serialize_config(), f, indent=2)
    
    def get_config(self) -> AppConfig:
        """Get current configuration"""
        return self._config
    
    def update_config(self, updates: Dict[str, Any]) -> None:
        """Update configuration with new values"""
        # This is a simplified implementation - in production, you'd want more robust updates
        if 'portfolio' in updates:
            for key, value in updates['portfolio'].items():
                setattr(self._config.portfolio, key, value)
        
        if 'assets' in updates:
            for symbol, asset_data in updates['assets'].items():
                if symbol in self._config.assets:
                    for key, value in asset_data.items():
                        setattr(self._config.assets[symbol], key, value)
        
        if 'trading' in updates:
            for key, value in updates['trading'].items():
                setattr(self._config.trading, key, value)
        
        if 'system' in updates:
            for key, value in updates['system'].items():
                setattr(self._config.system, key, value)
        
        # Re-apply dataclass boundary coercion after dictionary updates.
        self._config.portfolio.__post_init__()
        for asset in self._config.assets.values():
            asset.__post_init__()
        self._config.trading.__post_init__()
        self._config.system.__post_init__()
        self._save_config()
    
    def get_asset_config(self, symbol: str) -> AssetConfig:
        """Get configuration for a specific asset"""
        return self._config.assets.get(symbol)
    
    def get_portfolio_config(self) -> PortfolioConfig:
        """Get portfolio configuration"""
        return self._config.portfolio
    
    def get_trading_config(self) -> TradingConfig:
        """Get trading configuration"""
        return self._config.trading
    
    def get_system_config(self) -> SystemConfig:
        """Get system configuration"""
        return self._config.system
    
    def validate_config(self) -> list:
        """Validate configuration and return list of errors"""
        errors = []
        
        # Validate portfolio config
        portfolio = self._config.portfolio
        if portfolio.initial_balance <= 0:
            errors.append("Initial balance must be positive")
        if not (0 < portfolio.base_position_size <= 1):
            errors.append("Base position size must be between 0 and 1")
        if not (0 < portfolio.scaling_position_size <= 1):
            errors.append("Scaling position size must be between 0 and 1")
        if portfolio.leverage <= 0:
            errors.append("Leverage must be positive")
        if portfolio.max_positions < 1:
            errors.append("Max positions must be at least 1")
        
        # Validate assets
        for symbol, asset in self._config.assets.items():
            if not asset.enabled:
                continue
            if asset.min_confidence < 0 or asset.min_confidence > 1:
                errors.append(f"{symbol}: min_confidence must be between 0 and 1")
            if asset.max_volatility not in ["low", "medium", "high"]:
                errors.append(f"{symbol}: max_volatility must be 'low', 'medium', or 'high'")
            if asset.analysis_interval_minutes <= 0:
                errors.append(f"{symbol}: analysis_interval_minutes must be positive")

        enabled_assets = [asset for asset in self._config.assets.values() if asset.enabled]
        allocation_total = sum(asset.allocation_percentage or 0.0 for asset in enabled_assets)
        if enabled_assets and abs(allocation_total - 1.0) > 1e-6:
            errors.append(
                f"Enabled asset allocation percentages must total 1.0; got {allocation_total:.6f}"
            )
        for asset in enabled_assets:
            if asset.allocation_percentage is None or not 0 <= asset.allocation_percentage <= 1:
                errors.append(f"{asset.symbol}: allocation_percentage must be between 0 and 1")
        
        # Validate trading config
        trading = self._config.trading
        if trading.confidence_change_threshold < 0 or trading.confidence_change_threshold > 1:
            errors.append("confidence_change_threshold must be between 0 and 1")
        if trading.stop_loss_percentage <= 0 or trading.stop_loss_percentage >= 1:
            errors.append("stop_loss_percentage must be between 0 and 1")
        if trading.take_profit_percentage <= 0 or trading.take_profit_percentage >= 1:
            errors.append("take_profit_percentage must be between 0 and 1")
        
        # Validate system config
        system = self._config.system
        if not system.telegram_token:
            errors.append("Telegram token is required")
        
        return errors

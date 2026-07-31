"""
Configuration Manager for AI Trading Intelligence Bot
Handles all configurable settings including portfolio parameters, trading rules, and asset configurations.
"""

import json
import os
from dataclasses import dataclass, asdict
from typing import Dict, Any
from pathlib import Path

@dataclass
class PortfolioConfig:
    """Portfolio configuration settings"""
    initial_balance: float = 100.0
    base_position_size: float = 0.5  # 50% of account balance
    scaling_position_size: float = 0.25  # 25% of account balance
    leverage: float = 400.0
    max_positions: int = 3
    max_open_positions: int = 3

@dataclass
class AssetConfig:
    """Asset-specific configuration"""
    symbol: str
    enabled: bool = True
    min_confidence: float = 0.5
    max_volatility: str = "high"  # low, medium, high
    analysis_interval_minutes: int = 15

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
                analysis_interval_minutes=15
            ),
            "XAUUSD": AssetConfig(
                symbol="XAUUSD",
                enabled=True,
                min_confidence=0.5,
                max_volatility="high",
                analysis_interval_minutes=15
            )
        }
        
        trading = TradingConfig()
        system = SystemConfig()
        
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
        for symbol, asset_data in assets_data.items():
            assets[symbol] = AssetConfig(
                symbol=symbol,
                enabled=asset_data.get('enabled', True),
                min_confidence=float(asset_data.get('min_confidence', 0.5)),
                max_volatility=asset_data.get('max_volatility', 'high'),
                analysis_interval_minutes=int(asset_data.get('analysis_interval_minutes', 15))
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
        system = SystemConfig(
            telegram_token=system_data.get('telegram_token', ''),
            telegram_chat_id=system_data.get('telegram_chat_id', '843487976'),
            alert_state_file=system_data.get('alert_state_file', '.market_alert_state.json'),
            trade_history_file=system_data.get('trade_history_file', 'trade_history.json'),
            portfolio_stats_file=system_data.get('portfolio_stats_file', 'portfolio_stats.json'),
            log_file=system_data.get('log_file', 'trading_bot.log'),
            data_directory=system_data.get('data_directory', 'data'),
            backup_enabled=system_data.get('backup_enabled', True),
            auto_recovery=system_data.get('auto_recovery', True),
            max_backup_files=int(system_data.get('max_backup_files', 10))
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
            'system': asdict(self._config.system)
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
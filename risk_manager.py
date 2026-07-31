"""
Risk Manager for AI Trading Intelligence Bot
Manages risk calculations, exposure limits, and risk controls.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal, ROUND_HALF_UP

from asset_manager import AssetManager, Trade, TradeStatus, PositionDirection
from configuration_manager import PortfolioConfig, TradingConfig

class RiskLevel(Enum):
    """Risk levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class RiskType(Enum):
    """Risk types"""
    MARKET = "MARKET"
    CREDIT = "CREDIT"
    LIQUIDITY = "LIQUIDITY"
    OPERATIONAL = "OPERATIONAL"
    SYSTEM = "SYSTEM"

@dataclass
class RiskMetric:
    """Risk metric"""
    id: str = None
    type: str = None
    level: str = None
    value: float = None
    threshold: float = None
    timestamp: datetime = None
    description: str = None
    
    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4())
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)

@dataclass
class RiskLimit:
    """Risk limit"""
    id: str = None
    type: str = None
    symbol: str = None
    limit_value: float = None
    is_active: bool = True
    
    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4())

@dataclass
class RiskAlert:
    """Risk alert"""
    id: str = None
    type: str = None
    severity: str = None
    message: str = None
    timestamp: datetime = None
    asset: str = None
    
    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4())
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)

class RiskManager:
    """Manages risk calculations and controls"""
    
    def __init__(self, asset_manager: AssetManager, portfolio_config: PortfolioConfig, 
                 trading_config: TradingConfig):
        self.asset_manager = asset_manager
        self.portfolio_config = portfolio_config
        self.trading_config = trading_config
        self.risk_limits: List[RiskLimit] = []
        self.risk_metrics: List[RiskMetric] = []
        self.risk_alerts: List[RiskAlert] = []
        self.risk_history: List[Dict[str, Any]] = []
    
    def initialize_risk_limits(self) -> None:
        """Initialize default risk limits"""
        # Portfolio-level risk limits
        self.add_risk_limit("MAX_EXPOSURE", None, 1.0)  # 100% exposure
        self.add_risk_limit("MAX_DRAWDOWN", None, 0.2)  # 20% max drawdown
        self.add_risk_limit("MAX_POSITION_SIZE", None, 0.5)  # 50% of balance
        self.add_risk_limit("MAX_DAILY_LOSS", None, 0.1)  # 10% daily loss
        
        # Asset-specific risk limits
        for symbol in ["BTCUSD", "XAUUSD"]:
            self.add_risk_limit("MAX_POSITION_SIZE", symbol, 0.5)
            self.add_risk_limit("STOP_LOSS_PCT", symbol, trading_config.stop_loss_percentage)
            self.add_risk_limit("TAKE_PROFIT_PCT", symbol, trading_config.take_profit_percentage)
    
    def add_risk_limit(self, risk_type: str, symbol: str, limit_value: float) -> RiskLimit:
        """Add a risk limit"""
        risk_limit = RiskLimit(
            type=risk_type,
            symbol=symbol,
            limit_value=limit_value
        )
        
        self.risk_limits.append(risk_limit)
        return risk_limit
    
    def calculate_risk_metrics(self) -> Dict[str, Any]:
        """Calculate comprehensive risk metrics"""
        all_assets = self.asset_manager.get_all_assets()
        
        # Calculate portfolio-level risk metrics
        total_balance = sum(asset.balance for asset in all_assets.values())
        total_equity = sum(asset.equity for asset in all_assets.values())
        
        # Calculate exposure
        total_position_value = sum(
            sum(trade.position_size for trade in asset.open_positions)
            for asset in all_assets.values()
        )
        exposure_ratio = (total_position_value / total_balance) if total_balance > 0 else 0.0
        
        # Calculate risk metrics
        risk_metrics = {
            'portfolio_risk_score': self._calculate_portfolio_risk_score(all_assets),
            'total_exposure': total_position_value,
            'exposure_ratio': exposure_ratio,
            'max_single_position': self._calculate_max_single_position(all_assets),
            'concentration_risk': self._calculate_concentration_risk(all_assets),
            'liquidity_risk': self._calculate_liquidity_risk(all_assets),
            'market_risk': self._calculate_market_risk(all_assets),
            'credit_risk': self._calculate_credit_risk(all_assets),
            'operational_risk': self._calculate_operational_risk(),
            'system_risk': self._calculate_system_risk()
        }
        
        # Check risk limits
        risk_metrics['risk_limit_breaches'] = self._check_risk_limits(risk_metrics)
        
        # Store risk metrics
        self._store_risk_metrics(risk_metrics)
        
        return risk_metrics
    
    def check_risk_limits(self, symbol: str = None) -> List[RiskAlert]:
        """Check if any risk limits are breached"""
        all_assets = self.asset_manager.get_all_assets()
        
        if symbol:
            assets_to_check = {symbol: all_assets.get(symbol)}
        else:
            assets_to_check = all_assets
        
        alerts = []
        
        for asset_symbol, asset_state in assets_to_check.items():
            if not asset_state:
                continue
            
            # Check exposure limit
            exposure_ratio = self._calculate_asset_exposure(asset_state)
            if exposure_ratio > 1.0:  # 100% exposure limit
                alert = RiskAlert(
                    type="EXPOSURE_LIMIT",
                    severity="HIGH",
                    message=f"Asset {asset_symbol} exposure ratio {exposure_ratio:.2%} exceeds 100% limit",
                    asset=asset_symbol
                )
                alerts.append(alert)
            
            # Check position size limit
            for trade in asset_state.open_positions:
                position_size_ratio = trade.position_size / asset_state.balance
                if position_size_ratio > 0.5:  # 50% position size limit
                    alert = RiskAlert(
                        type="POSITION_SIZE_LIMIT",
                        severity="MEDIUM",
                        message=f"Asset {asset_symbol} position size {position_size_ratio:.2%} exceeds 50% limit",
                        asset=asset_symbol
                    )
                    alerts.append(alert)
            
            # Check stop loss
            for trade in asset_state.open_positions:
                if trade.stop_loss_price:
                    current_price = self._get_current_price(asset_symbol)
                    if current_price and trade.direction == PositionDirection.BUY.value:
                        if current_price <= trade.stop_loss_price:
                            alert = RiskAlert(
                                type="STOP_LOSS_TRIGGERED",
                                severity="CRITICAL",
                                message=f"Asset {asset_symbol} stop loss triggered at {trade.stop_loss_price}",
                                asset=asset_symbol
                            )
                            alerts.append(alert)
                    elif current_price and trade.direction == PositionDirection.SELL.value:
                        if current_price >= trade.stop_loss_price:
                            alert = RiskAlert(
                                type="STOP_LOSS_TRIGGERED",
                                severity="CRITICAL",
                                message=f"Asset {asset_symbol} stop loss triggered at {trade.stop_loss_price}",
                                asset=asset_symbol
                            )
                            alerts.append(alert)
        
        # Add alerts to list
        self.risk_alerts.extend(alerts)
        
        return alerts
    
    def calculate_var(self, confidence_level: float = 0.95, period_days: int = 1) -> float:
        """Calculate Value at Risk (VaR)"""
        all_assets = self.asset_manager.get_all_assets()
        
        # Get historical returns
        historical_returns = self._get_historical_returns(period_days)
        
        if not historical_returns:
            return 0.0
        
        # Calculate VaR using historical simulation
        sorted_returns = sorted(historical_returns)
        var_index = int((1 - confidence_level) * len(sorted_returns))
        
        if var_index >= len(sorted_returns):
            var_index = len(sorted_returns) - 1
        
        var = abs(sorted_returns[var_index])
        return self._round_decimal(var * 100)  # As percentage
    
    def calculate_conditional_var(self, confidence_level: float = 0.95, 
                                 period_days: int = 1) -> float:
        """Calculate Conditional Value at Risk (CVaR)"""
        all_assets = self.asset_manager.get_all_assets()
        
        # Get historical returns
        historical_returns = self._get_historical_returns(period_days)
        
        if not historical_returns:
            return 0.0
        
        # Calculate CVaR (expected loss given that loss exceeds VaR)
        sorted_returns = sorted(historical_returns)
        var_index = int((1 - confidence_level) * len(sorted_returns))
        
        if var_index >= len(sorted_returns):
            var_index = len(sorted_returns) - 1
        
        var_threshold = sorted_returns[var_index]
        cvar = abs(sum(r for r in sorted_returns if r <= var_threshold) / 
                  len([r for r in sorted_returns if r <= var_threshold]))
        
        return self._round_decimal(cvar * 100)  # As percentage
    
    def calculate_beta(self, symbol: str, market_returns: List[float]) -> float:
        """Calculate beta for an asset"""
        asset_returns = self._get_asset_returns(symbol)
        
        if not asset_returns or not market_returns:
            return 0.0
        
        # Calculate covariance and variance
        asset_mean = sum(asset_returns) / len(asset_returns)
        market_mean = sum(market_returns) / len(market_returns)
        
        covariance = sum((a - asset_mean) * (m - market_mean) 
                        for a, m in zip(asset_returns, market_returns)) / len(asset_returns)
        
        market_variance = sum((m - market_mean) ** 2 for m in market_returns) / len(market_returns)
        
        if market_variance == 0:
            return 0.0
        
        beta = covariance / market_variance
        return self._round_decimal(beta)
    
    def calculate_alpha(self, symbol: str, market_returns: List[float], 
                       risk_free_rate: float = 0.02) -> float:
        """Calculate alpha for an asset"""
        asset_returns = self._get_asset_returns(symbol)
        
        if not asset_returns or not market_returns:
            return 0.0
        
        # Calculate expected return using CAPM
        beta = self.calculate_beta(symbol, market_returns)
        
        # Get market return
        market_return = sum(market_returns) / len(market_returns)
        
        # Calculate alpha
        expected_return = risk_free_rate + beta * (market_return - risk_free_rate)
        actual_return = sum(asset_returns) / len(asset_returns)
        
        alpha = actual_return - expected_return
        return self._round_decimal(alpha * 100)  # As percentage
    
    def get_risk_report(self) -> Dict[str, Any]:
        """Get comprehensive risk report"""
        risk_metrics = self.calculate_risk_metrics()
        alerts = self.check_risk_limits()
        
        return {
            'risk_metrics': risk_metrics,
            'active_alerts': alerts,
            'risk_limits': self.risk_limits,
            'risk_history': self.risk_history[-100:] if self.risk_history else []
        }
    
    def _calculate_portfolio_risk_score(self, all_assets: Dict[str, Any]) -> float:
        """Calculate overall portfolio risk score"""
        if not all_assets:
            return 0.0
        
        # Calculate individual asset risk scores
        asset_scores = []
        for asset in all_assets.values():
            score = self._calculate_asset_risk_score(asset)
            asset_scores.append(score)
        
        # Calculate weighted average
        total_balance = sum(asset.balance for asset in all_assets.values())
        if total_balance == 0:
            return 0.0
        
        weighted_score = sum(
            score * asset.balance / total_balance 
            for score, asset in zip(asset_scores, all_assets.values())
        )
        
        return self._round_decimal(weighted_score)
    
    def _calculate_asset_risk_score(self, asset_state: Any) -> float:
        """Calculate risk score for a single asset"""
        score = 0.0
        
        # Factor in exposure
        exposure = self._calculate_asset_exposure(asset_state)
        score += exposure * 0.3
        
        # Factor in position concentration
        concentration = self._calculate_position_concentration(asset_state)
        score += concentration * 0.3
        
        # Factor in volatility (simplified)
        volatility = 0.5  # Placeholder
        score += volatility * 0.2
        
        # Factor in liquidity (simplified)
        liquidity = 0.5  # Placeholder
        score += liquidity * 0.2
        
        return self._round_decimal(score)
    
    def _calculate_asset_exposure(self, asset_state: Any) -> float:
        """Calculate exposure for a single asset"""
        total_position_value = sum(trade.position_size for trade in asset_state.open_positions)
        exposure = (total_position_value / asset_state.balance) if asset_state.balance > 0 else 0.0
        return min(exposure, 1.0)  # Cap at 100%
    
    def _calculate_max_single_position(self, all_assets: Dict[str, Any]) -> float:
        """Calculate maximum single position size"""
        max_position = 0.0
        
        for asset in all_assets.values():
            for trade in asset.open_positions:
                position_ratio = trade.position_size / asset.balance
                max_position = max(max_position, position_ratio)
        
        return self._round_decimal(max_position)
    
    def _calculate_concentration_risk(self, all_assets: Dict[str, Any]) -> float:
        """Calculate concentration risk"""
        if not all_assets:
            return 0.0
        
        # Calculate Herfindahl-Hirschman Index (HHI)
        total_balance = sum(asset.balance for asset in all_assets.values())
        if total_balance == 0:
            return 0.0
        
        hhi = sum((asset.balance / total_balance) ** 2 for asset in all_assets.values())
        
        # Convert HHI to risk score (higher HHI = higher concentration risk)
        concentration_risk = (hhi - 1.0 / len(all_assets)) / (1.0 - 1.0 / len(all_assets))
        return self._round_decimal(concentration_risk)
    
    def _calculate_liquidity_risk(self, all_assets: Dict[str, Any]) -> float:
        """Calculate liquidity risk"""
        # Simplified liquidity risk calculation
        # In reality, this would consider order book depth, market depth, etc.
        return 0.5  # Placeholder
    
    def _calculate_market_risk(self, all_assets: Dict[str, Any]) -> float:
        """Calculate market risk"""
        # Simplified market risk calculation
        # In reality, this would consider volatility, correlations, etc.
        return 0.5  # Placeholder
    
    def _calculate_credit_risk(self, all_assets: Dict[str, Any]) -> float:
        """Calculate credit risk"""
        # Simplified credit risk calculation
        # In reality, this would consider counterparty risk, etc.
        return 0.1  # Placeholder
    
    def _calculate_operational_risk(self) -> float:
        """Calculate operational risk"""
        # Simplified operational risk calculation
        # In reality, this would consider system failures, human errors, etc.
        return 0.2  # Placeholder
    
    def _calculate_system_risk(self) -> float:
        """Calculate system risk"""
        # Simplified system risk calculation
        # In reality, this would consider network failures, etc.
        return 0.2  # Placeholder
    
    def _calculate_position_concentration(self, asset_state: Any) -> float:
        """Calculate position concentration within an asset"""
        if not asset_state.open_positions:
            return 0.0
        
        # Calculate Herfindahl-Hirschman Index for positions
        total_position_value = sum(trade.position_size for trade in asset_state.open_positions)
        if total_position_value == 0:
            return 0.0
        
        hhi = sum((trade.position_size / total_position_value) ** 2 
                 for trade in asset_state.open_positions)
        
        return self._round_decimal(hhi)
    
    def _check_risk_limits(self, risk_metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check if risk limits are breached"""
        breaches = []
        
        for limit in self.risk_limits:
            if limit.symbol:  # Asset-specific limit
                # Check asset-specific limits
                asset_state = self.asset_manager.get_asset_state(limit.symbol)
                if asset_state:
                    if limit.type == "MAX_EXPOSURE":
                        exposure = self._calculate_asset_exposure(asset_state)
                        if exposure > limit.limit_value:
                            breaches.append({
                                'limit_type': limit.type,
                                'symbol': limit.symbol,
                                'current_value': exposure,
                                'limit_value': limit.limit_value,
                                'severity': 'HIGH' if exposure > limit.limit_value * 1.5 else 'MEDIUM'
                            })
            else:  # Portfolio-level limit
                if limit.type == "MAX_EXPOSURE":
                    exposure_ratio = risk_metrics.get('exposure_ratio', 0.0)
                    if exposure_ratio > limit.limit_value:
                        breaches.append({
                            'limit_type': limit.type,
                            'symbol': None,
                            'current_value': exposure_ratio,
                            'limit_value': limit.limit_value,
                            'severity': 'HIGH' if exposure_ratio > limit.limit_value * 1.5 else 'MEDIUM'
                        })
        
        return breaches
    
    def _get_current_price(self, symbol: str) -> float:
        """Get current price for an asset (placeholder)"""
        # In reality, this would fetch current price from market data
        return 100.0  # Placeholder
    
    def _get_historical_returns(self, period_days: int) -> List[float]:
        """Get historical returns (placeholder)"""
        # In reality, this would fetch historical price data
        return [0.01, -0.02, 0.03, -0.01, 0.02]  # Placeholder
    
    def _get_asset_returns(self, symbol: str) -> List[float]:
        """Get asset returns (placeholder)"""
        # In reality, this would fetch historical price data for the asset
        return [0.01, -0.02, 0.03, -0.01, 0.02]  # Placeholder
    
    def _store_risk_metrics(self, risk_metrics: Dict[str, Any]) -> None:
        """Store risk metrics in history"""
        risk_metrics['timestamp'] = datetime.now(timezone.utc).isoformat()
        
        self.risk_history.append(risk_metrics)
        
        # Keep only last 1000 entries to prevent memory issues
        if len(self.risk_history) > 1000:
            self.risk_history = self.risk_history[-1000:]
    
    def _round_decimal(self, value: float, decimals: int = 2) -> float:
        """Round decimal value to specified precision"""
        return float(Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
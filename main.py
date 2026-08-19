"""
AI Trading Intelligence Bot v2.0 - Main Application
Comprehensive trading system for BTCUSD and XAUUSD with modular architecture.
"""

import json
import logging
import time
import asyncio
import os
import hashlib
from urllib import parse, request
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple

from configuration_manager import ConfigurationManager, AppConfig
from asset_manager import AssetManager
from market_analyzer import MarketAnalyzer, MarketAnalysis
from signal_engine import SignalEngine, SignalResult
from trade_manager import TradeManager
from portfolio_manager import PortfolioManager
from profit_calculator import ProfitCalculator
from risk_manager import RiskManager
from trade_storage import TradeStorage
from performance_tracker import PerformanceTracker
from telegram_formatter import TelegramFormatter, ReportFormat
from market_data_aggregator import MarketDataAggregator, PriceValidationResult
from technical_indicators import TechnicalIndicators
from multi_timeframe_analyzer import MultiTimeframeAnalyzer
from ai_decision_engine import AIDecisionEngine
from trade_execution_simulator import TradeExecutionSimulator
from reliability_manager import ReliabilityManager
from mt5_bridge import MT5Connection, MT5MarketData, MT5AccountReader, MT5HealthMonitor, MT5SymbolMapper
from signal_intelligence import (DEFAULT_PIP_SPECS, SignalOutcomeTracker, SimulationMode, build_trade_candidate, calculate_signal_score, infer_candidate_direction, select_simulation_mode)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AITradingIntelligenceBot:
    """Main AI Trading Intelligence Bot application"""
    
    def __init__(self, config_file: str = "app_config.json"):
        self.config_manager = ConfigurationManager(config_file)
        self.config = self.config_manager.get_config()
        config_errors = self.config_manager.validate_config()
        if config_errors:
            raise RuntimeError(
                "STARTUP VALIDATION FAILED: " + "; ".join(config_errors)
            )
        
        # Initialize core components
        self.asset_manager = AssetManager(
            self.config.portfolio.initial_balance,
            self.config.assets,
            self.config.portfolio.base_position_size,
            self.config.portfolio.scaling_position_size,
            self.config.portfolio.max_positions,
        )
        self.market_analyzers: Dict[str, MarketAnalyzer] = {}
        self.signal_engine: Optional[SignalEngine] = None
        self.trade_manager: Optional[TradeManager] = None
        self.portfolio_manager: Optional[PortfolioManager] = None
        self.profit_calculator: Optional[ProfitCalculator] = None
        self.risk_manager: Optional[RiskManager] = None
        self.trade_storage: Optional[TradeStorage] = None
        self.performance_tracker: Optional[PerformanceTracker] = None
        self.telegram_formatter: Optional[TelegramFormatter] = None
        
        # Initialize enhanced components
        self.market_data_aggregator: Optional[MarketDataAggregator] = None
        self.technical_indicators: Optional[TechnicalIndicators] = None
        self.multi_timeframe_analyzer: Optional[MultiTimeframeAnalyzer] = None
        self.ai_decision_engine: Optional[AIDecisionEngine] = None
        self.trade_execution_simulator: Optional[TradeExecutionSimulator] = None
        self.reliability_manager: Optional[ReliabilityManager] = None
        self.market_data_status: Dict[str, Dict[str, Any]] = {}
        self.market_snapshots: Dict[str, Any] = {}
        self.last_reports: Dict[str, str] = {}
        self.telegram_delivery_failures = 0
        self._telegram_message_times: Dict[str, datetime] = {}
        self.mt5_health_monitor: Optional[MT5HealthMonitor] = None
        self.outcome_tracker = SignalOutcomeTracker(minimum_outcomes=self.config.system.adaptive_learning_min_outcomes)
        self.last_trade_candidates: Dict[str, Any] = {}
        
        # Initialize components
        self._initialize_components()
        
        # Initialize enhanced components
        self._initialize_enhanced_components()
        self._validate_startup()
        
        # Set up monitoring
        self.last_scan_time = datetime.now(timezone.utc)
        self.scan_interval = 15  # Default 15 minutes

        logger.info("AI Trading Intelligence Bot initialized successfully")
    
    def _initialize_components(self) -> None:
        """Initialize all components"""
        # Initialize market analyzers for each asset
        for symbol in self.config.assets:
            asset_config = self.config_manager.get_asset_config(symbol)
            if asset_config and asset_config.enabled:
                self.market_analyzers[symbol] = MarketAnalyzer(asset_config)
        
        # Initialize trade manager
        self.trade_manager = TradeManager(
            self.asset_manager,
            self.config.portfolio,
            self.config.trading
        )
        
        # Initialize portfolio manager
        self.portfolio_manager = PortfolioManager(
            self.asset_manager,
            self.config.portfolio,
            self.config.trading
        )
        
        # Initialize profit calculator
        self.profit_calculator = ProfitCalculator(self.config.portfolio)
        
        # Initialize risk manager
        self.risk_manager = RiskManager(
            self.asset_manager,
            self.config.portfolio,
            self.config.trading
        )
        
        # Initialize trade storage
        self.trade_storage = TradeStorage(self.config.system)
        
        # Initialize performance tracker
        self.performance_tracker = PerformanceTracker(
            self.asset_manager,
            self.config.portfolio
        )
        
        # Initialize signal engine
        self.signal_engine = SignalEngine(
            self.asset_manager,
            self.config.trading,
            self.config.portfolio,
        )
        
        # Initialize Telegram formatter
        self.telegram_formatter = TelegramFormatter(
            self.asset_manager,
            self.portfolio_manager,
            self.config.system
        )
        self.telegram_formatter.outcome_tracker = self.outcome_tracker
        self.telegram_formatter.mt5_health_monitor = self.mt5_health_monitor
        
        # Load existing data from storage
        self._load_existing_data()
    
    def _initialize_enhanced_components(self) -> None:
        """Initialize enhanced components for live market data verification"""
        logger.info("SYSTEM STARTING")
        # Initialize market data aggregator for live price verification
        self.market_data_aggregator = MarketDataAggregator(system_config=self.config.system)
        provider_status = self.market_data_aggregator.get_provider_status()
        logger.info("Market data engine initialized")
        mt5_connection = MT5Connection(enabled=self.config.system.mt5_enabled, mode=self.config.system.mt5_mode, terminal_path=self.config.system.mt5_terminal_path)
        mt5_market = MT5MarketData(mt5_connection, MT5SymbolMapper.from_environment(self.config.system))
        self.mt5_health_monitor = MT5HealthMonitor(mt5_connection, mt5_market, MT5AccountReader(mt5_connection))
        self.telegram_formatter.mt5_health_monitor = self.mt5_health_monitor
        logger.info("MT5 provider: %s", "ENABLED" if self.config.system.mt5_enabled else "UNAVAILABLE (disabled)")
        logger.info("Available providers: %s", ", ".join(k for k, v in provider_status.items() if v == "configured") or "none")
        logger.info("Unavailable providers: %s", ", ".join(k for k, v in provider_status.items() if v != "configured") or "none")
        
        # Initialize technical indicators for enhanced analysis
        self.technical_indicators = TechnicalIndicators()
        logger.info("Technical analysis initialized")
        
        # Initialize multi-timeframe analyzer for comprehensive analysis
        self.multi_timeframe_analyzer = MultiTimeframeAnalyzer()
        logger.info("Multi-timeframe analysis initialized")
        
        # Initialize AI decision engine for enhanced signal generation
        self.ai_decision_engine = AIDecisionEngine(
            self.asset_manager,
            self.config.trading,
            self.config.portfolio,
            self.performance_tracker,
        )
        logger.info("AI decision engine initialized")
        
        # Initialize trade execution simulator for testing
        self.trade_execution_simulator = TradeExecutionSimulator(
            self.asset_manager,
            self.config.portfolio,
            self.config.trading
        )
        
        # Initialize reliability manager for system monitoring
        self.reliability_manager = ReliabilityManager()
        logger.info("Portfolio manager initialized")
        logger.info("Telegram initialized")

    def _validate_startup(self) -> None:
        """Validate initialized components before a scan begins."""
        components = {
            "Configuration": self.config,
            "Asset manager": self.asset_manager,
            "Market analyzer": self.market_analyzers,
            "Signal engine": self.signal_engine,
            "AI decision engine": self.ai_decision_engine,
            "Trade manager": self.trade_manager,
            "Portfolio manager": self.portfolio_manager,
            "Performance tracker": self.performance_tracker,
            "Trade storage": self.trade_storage,
            "Telegram formatter": self.telegram_formatter,
        }
        missing = [name for name, value in components.items() if not value]
        if missing:
            details = ", ".join(missing)
            raise RuntimeError(f"STARTUP VALIDATION FAILED: {details}")
        for name in components:
            logger.info("[OK] %s loaded", name)
        logger.info("[OK] Telegram configuration loaded (token=%s)",
                    "available" if self.config.system.telegram_token else "not configured")
        logger.info("SYSTEM READY")
    
    def _get_live_market_data(self, symbol: str) -> Optional[Tuple[float, float]]:
        """Get live market data with consensus pricing from multiple sources"""
        try:
            # Fetch market data from all providers with validation
            validation_result = asyncio.run(
                self.market_data_aggregator.fetch_market_data(symbol)
            )
            self.market_snapshots[symbol] = validation_result
            
            # Log consensus pricing information
            logger.info(f"Live market data for {symbol}: "
                       f"Consensus Price: ${validation_result.consensus_price:,.2f}, "
                       f"Confidence: {validation_result.confidence_score:.1%}, "
                       f"Providers: {len(validation_result.provider_prices)}, "
                       f"Outliers: {len(validation_result.outlier_providers)}")
            self.market_data_status[symbol] = {
                "status": "validated",
                "provider_prices": validation_result.provider_prices,
                "outliers": validation_result.outlier_providers,
                "stale": validation_result.stale_providers,
                "confidence": validation_result.confidence_score,
                "timestamp": validation_result.validation_timestamp,
                "provider_total": validation_result.provider_count,
                "provider_status": validation_result.provider_status or {},
                "ohlcv_provider": validation_result.ohlcv_provider,
                "ohlcv_candles": len(validation_result.ohlcv or []),
                "execution_reference_price": validation_result.execution_reference_price,
            }
            logger.info("%s price validated", symbol)

            ohlcv = validation_result.ohlcv or []
            if len(ohlcv) < 200:
                raise ValueError(
                    f"DATA UNAVAILABLE: insufficient validated OHLCV for {symbol} "
                    f"(received {len(ohlcv)} candles)"
                )
            previous_price = validation_result.previous_price or float(ohlcv[-2]["close"])

            if self.technical_indicators:
                self.technical_indicators.set_ohlcv_data(symbol, ohlcv)

            if self.multi_timeframe_analyzer:
                for timeframe in ("5M", "15M", "1H", "4H", "Daily"):
                    self.multi_timeframe_analyzer.set_timeframe_ohlcv(
                        symbol, timeframe, ohlcv
                    )
            
            if previous_price is None:
                logger.warning("%s previous price unavailable; awaiting another validated observation", symbol)
                return None
            
            return validation_result.consensus_price, previous_price
            
        except TypeError as e:
            logger.exception("%s INTERNAL_ERROR during production market-data path: %s", symbol, e)
            reason = "internal market-data type error; see GitHub Actions traceback"
            self.market_data_status[symbol] = {
                "status": "internal_error", "classification": "INTERNAL_ERROR", "reason": reason
            }
            logger.warning("%s DATA UNAVAILABLE due to INTERNAL_ERROR; no signal generated", symbol)
            return None
        except ValueError as e:
            reason = str(e)
            if reason.startswith("Configuration error:"):
                logger.exception("%s CONFIGURATION_ERROR in production market-data path: %s", symbol, e)
                self.market_data_status[symbol] = {
                    "status": "configuration_error",
                    "classification": "CONFIGURATION_ERROR",
                    "reason": reason,
                }
                logger.warning("%s DATA UNAVAILABLE due to CONFIGURATION_ERROR; no signal generated", symbol)
                return None
            logger.error("%s market-data validation unavailable: %s", symbol, e)
            if "validation_result" in locals():
                statuses = getattr(validation_result, "provider_status", {}) or {}
                safe_status = ", ".join(f"{name}: {status}" for name, status in statuses.items())
                if safe_status:
                    reason = f"{reason}; providers: {safe_status}"
            self.market_data_status[symbol] = {"status": "unavailable", "reason": reason}
            logger.warning("%s DATA UNAVAILABLE; skipping tradeable analysis", symbol)
            return None
    
    def _load_existing_data(self) -> None:
        """Load existing data from storage"""
        try:
            # Load trades
            trades = self.trade_storage.get_trades()
            for trade in trades:
                if not self.asset_manager.restore_trade(trade):
                    logger.warning("Skipping invalid persisted trade %s", trade.id)
            
            # Load portfolio stats
            stats = self.trade_storage.get_portfolio_stats()
            for stat in stats:
                self.portfolio_manager.update_portfolio()
            
            # Load signals
            signals = self.trade_storage.get_signals()
            for signal in signals:
                # Process signal data
                pass
            
            logger.info("Existing data loaded successfully")
        except Exception as e:
            logger.error(f"Error loading existing data: {e}")
    
    def run_scan(self, execute_trades: bool = True) -> Dict[str, str]:
        """Run a complete scan cycle with enhanced features"""
        logger.info("Starting enhanced scan cycle")
        
        try:
            # Update portfolio metrics
            portfolio_metrics = self.portfolio_manager.update_portfolio()
            
            # Generate signals for each asset with enhanced analysis
            signal_results: Dict[str, SignalResult] = {}
            
            unavailable_assets = []
            for symbol, analyzer in self.market_analyzers.items():
                logger.info("%s analysis started", symbol)
                # Get current price from market data aggregator with live verification
                market_data = self._get_live_market_data(symbol)
                if market_data is None:
                    unavailable_assets.append(symbol)
                    continue
                current_price, previous_price = market_data
                
                # Analyze market with enhanced technical indicators
                market_analysis = analyzer.analyze_market(
                    symbol, current_price, previous_price
                )
                
                try:
                    technical_indicators = self.technical_indicators.calculate_all_indicators(symbol)
                    multi_timeframe = self.multi_timeframe_analyzer.analyze_multi_timeframe(symbol)
                    ai_decision = self.ai_decision_engine.generate_decision(
                        symbol, market_analysis, technical_indicators, multi_timeframe,
                        current_price, previous_price,
                        data_confidence=self.market_data_status[symbol].get("confidence", 0.0),
                    )
                    structure_values = list((getattr(multi_timeframe, "market_structure", None) or {}).values())
                    structure_direction = next((item.get("overall") for item in structure_values if item.get("overall") in {"bullish", "bearish"}), None)
                    pattern_values = [pattern for rows in (getattr(multi_timeframe, "patterns", None) or {}).values() for pattern in rows]
                    pattern_direction = next((item.get("direction") for item in pattern_values if item.get("direction") in {"bullish", "bearish"}), None)
                    validation = self._get_validation_result(symbol)
                    provider_count = len(getattr(validation, "provider_prices", {}) or {}) if validation else 0
                    provider_total = max(1, int(self.market_data_status[symbol].get("provider_total", provider_count)))
                    evidence_direction = ai_decision.decision if ai_decision.decision in {"BUY", "SELL"} else infer_candidate_direction(
                        ai_decision.trend, structure_direction, pattern_direction, ai_decision.momentum
                    )
                    score = calculate_signal_score(
                        evidence_direction,
                        trend=ai_decision.trend,
                        momentum=ai_decision.momentum,
                        mtf_alignment=getattr(multi_timeframe, "confidence_score", None),
                        structure_direction=structure_direction,
                        pattern_direction=pattern_direction,
                        volatility=ai_decision.volatility,
                        ohlcv_confidence=self.market_data_status[symbol].get("confidence"),
                        spot_consensus=validation.confidence_score if validation else None,
                        provider_diversity=provider_count / provider_total,
                    )
                    configured_mode = str(self.config.system.simulation_mode).upper()
                    if configured_mode == "AUTO":
                        selected_mode = select_simulation_mode(
                            score=score,
                            adx=getattr(technical_indicators, "adx", None),
                            mtf_alignment=getattr(multi_timeframe, "confidence_score", None),
                            volatility=ai_decision.volatility,
                        )
                    else:
                        selected_mode = SimulationMode.normalize(configured_mode)
                    candidate = build_trade_candidate(
                        symbol, evidence_direction, current_price, score,
                        mode=selected_mode,
                        spec=DEFAULT_PIP_SPECS.get(symbol),
                        stop_loss_pips=self.config.system.simulation_stop_loss_pips,
                        min_score=(self.config.system.aggressive_min_score if self.config.system.simulation_mode.upper() == "AGGRESSIVE" else self.config.system.slow_min_score if self.config.system.simulation_mode.upper() in {"SLOW", "SWING"} else self.config.system.moderate_min_score),
                        min_confirmations=(self.config.system.aggressive_min_confirmations if self.config.system.simulation_mode.upper() == "AGGRESSIVE" else self.config.system.slow_min_confirmations if self.config.system.simulation_mode.upper() in {"SLOW", "SWING"} else self.config.system.moderate_min_confirmations),
                        watch_score=self.config.system.candidate_watch_score,
                        minimum_risk_reward=self.config.system.minimum_risk_reward,
                        structure_confirmed=not (structure_direction and pattern_direction and structure_direction != pattern_direction),
                    )
                    ai_decision.signal_score = score.score
                    ai_decision.trade_candidate = candidate
                    self.last_trade_candidates[symbol] = candidate
                    if candidate.direction in {"BUY", "SELL", "WATCH"}:
                        self.outcome_tracker.record(candidate, {"trend": ai_decision.trend, "regime": getattr(getattr(ai_decision.market_regime, "regime", None), "value", getattr(ai_decision.market_regime, "regime", None)), "patterns": pattern_values})
                    signal_result = self.signal_engine.generate_signal(
                        symbol,
                        market_analysis,
                        decision_override=ai_decision.decision,
                        execute=execute_trades,
                    )
                    self.asset_manager.update_floating_pnl(symbol, current_price)
                    signal_result.ai_decision_result = ai_decision
                    signal_result.validation_result = self._get_validation_result(symbol)
                    signal_result.technical_indicators = technical_indicators
                    signal_result.multi_timeframe = multi_timeframe
                    signal_result.risk_metrics = ai_decision.risk_metrics
                    signal_result.portfolio_metrics = self.portfolio_manager.update_portfolio()
                    signal_result.data_quality = self.market_data_status.get(symbol, {})
                    signal_result.trade_candidate = candidate
                except TypeError as exc:
                    logger.exception("%s INTERNAL_ERROR during technical/decision path: %s", symbol, exc)
                    self.market_data_status[symbol] = {
                        "status": "internal_error",
                        "classification": "INTERNAL_ERROR",
                        "reason": "internal analysis type error; see GitHub Actions traceback",
                    }
                    unavailable_assets.append(symbol)
                    continue
                except Exception as exc:
                    logger.exception("%s analysis unavailable: %s", symbol, exc)
                    self.market_data_status[symbol] = {"status": "unavailable", "reason": str(exc)}
                    unavailable_assets.append(symbol)
                    continue
                
                signal_results[symbol] = signal_result
                logger.info("%s decision: %s", symbol, signal_result.decision)
                logger.info("%s confidence: %.0f%%", symbol, signal_result.confidence * 100)
                
                # Save signal to storage
                self._save_signal(signal_result)
            
            # Send enhanced Telegram reports
            self._send_enhanced_reports(signal_results, unavailable_assets)
            
            # Update performance tracker
            self.performance_tracker.track_performance()
            
            # Check risk limits
            risk_alerts = self.risk_manager.check_risk_limits()
            if risk_alerts:
                self._handle_risk_alerts(risk_alerts)
            
            # Save portfolio stats
            self._save_portfolio_stats()
            
            # Backup data
            self.trade_storage.backup_data()
            
            logger.info("Enhanced scan cycle completed successfully")
            return self.last_reports.copy()
            
        except Exception as e:
            logger.error(f"Error during enhanced scan cycle: {e}")
            # Send alert to Telegram
            self._send_telegram_message(f"⚠️ SCAN ERROR: {e}")
    
    def _get_validation_result(self, symbol: str) -> Optional[PriceValidationResult]:
        """Return the current validated result for report enrichment."""
        return self.market_data_aggregator.get_cached_validation(symbol)

    def _generate_data_unavailable_report(self, symbol: str) -> str:
        status = self.market_data_status.get(symbol, {})
        reason = status.get("reason", "No validated market data")
        snapshot = self.market_snapshots.get(symbol)
        current_price = getattr(snapshot, "consensus_price", None) if snapshot else None
        price_line = f"Current Price: ${current_price:,.2f}\n" if current_price else "Current Price: DATA UNAVAILABLE\n"
        return (
            f"{symbol}\nDecision: DATA UNAVAILABLE\nTradeable signal: NO\n"
            + price_line
            + "Technical Analysis: UNAVAILABLE\n"
            + f"Reason: {reason}\n"
            + "No price, projected PnL, BUY, or SELL has been invented."
        )

    def _save_signal(self, signal_result: SignalResult) -> None:
        """Save signal to storage"""
        try:
            signal_data = {
                'symbol': signal_result.symbol,
                'timestamp': signal_result.timestamp.isoformat(),
                'decision': signal_result.decision,
                'confidence': signal_result.confidence,
                'action_taken': signal_result.action_taken,
                'positions_opened': signal_result.positions_opened,
                'positions_closed': signal_result.positions_closed
            }
            
            self.trade_storage.save_signal(signal_data)
            
        except Exception as e:
            logger.error(f"Error saving signal: {e}")
    
    def _send_reports(self, signal_results: Dict[str, SignalResult]) -> None:
        """Send Telegram reports"""
        try:
            # Send signal report
            if signal_results:
                # Use the first signal result as reference
                first_symbol = list(signal_results.keys())[0]
                signal_result = signal_results[first_symbol]
                
                report = self.telegram_formatter.format_signal_report(
                    signal_result, ReportFormat.PROFESSIONAL
                )
                
                # Send to Telegram (placeholder)
                self._send_telegram_message(report)
            
            # Send portfolio report
            portfolio_report = self.telegram_formatter.format_portfolio_report(
                ReportFormat.PROFESSIONAL
            )
            
            # Send to Telegram (placeholder)
            self._send_telegram_message(portfolio_report)
            
        except Exception as e:
            logger.error(f"Error sending reports: {e}")
    
    def _send_enhanced_reports(self, signal_results: Dict[str, SignalResult], unavailable_assets: Optional[List[str]] = None) -> None:
        """Send one consolidated normal-cycle intelligence report."""
        try:
            parts = ["AI TRADING INTELLIGENCE BOT\n\nCONSOLIDATED ANALYSIS CYCLE"]
            for symbol, signal_result in signal_results.items():
                report = self._generate_enhanced_report(signal_result)
                parts.append(report)
                self.last_reports[symbol] = report
            for symbol in unavailable_assets or []:
                report = self._generate_data_unavailable_report(symbol)
                parts.append(report)
                self.last_reports[symbol] = report
            parts.append(self._generate_enhanced_portfolio_report())
            parts.append(self._generate_market_data_health_report())
            consolidated = "\n\n--------------------\n\n".join(parts)
            self._send_telegram_message(consolidated)
            self.last_reports["CONSOLIDATED"] = consolidated
            logger.info("Consolidated Telegram report sent")
        except Exception as e:
            logger.error("Error sending consolidated reports: %s", e)

    def _generate_market_data_health_report(self) -> str:
        lines = ["SYSTEM HEALTH"]
        valid = 0
        for symbol in self.market_analyzers:
            status = self.market_data_status.get(symbol, {})
            candles = int(status.get("ohlcv_candles", 0) or 0)
            has_price = bool(status.get("provider_prices"))
            if candles >= 200:
                state = "HEALTHY"; valid += 1
                detail = "validated OHLCV available"
            elif has_price:
                state = "DEGRADED"; detail = "spot/current price only"
            else:
                state = "UNAVAILABLE"; detail = "no validated market data"
            lines.append(f"{symbol} Data: {state} ({detail})")
        engine = "HEALTHY" if valid == len(self.market_analyzers) else ("DEGRADED" if valid else "UNAVAILABLE")
        lines.append(f"Market Data Engine: {engine}")
        lines.append("Signal Engine: ACTIVE" if valid else "Signal Engine: WAITING FOR MARKET DATA")
        lines.append("Database: CONNECTED")
        return "\n".join(lines)

    def _generate_enhanced_report(self, signal_result: SignalResult) -> str:
        """Generate enhanced intelligence report for a symbol"""
        return self.telegram_formatter.format_signal_report(signal_result, ReportFormat.PROFESSIONAL)
    
    def _generate_enhanced_portfolio_report(self) -> str:
        """Generate enhanced portfolio intelligence report"""
        return self.telegram_formatter.format_portfolio_report(ReportFormat.PROFESSIONAL)
    
    def _handle_risk_alerts(self, alerts: List[Any]) -> None:
        """Handle risk alerts"""
        for alert in alerts:
            logger.warning(f"Risk alert: {alert}")
            
            # Send alert to Telegram (placeholder)
            alert_message = f"⚠️ RISK ALERT: {alert}"
            self._send_telegram_message(alert_message)
    
    def _save_portfolio_stats(self) -> None:
        """Save portfolio statistics"""
        try:
            portfolio_metrics = self.portfolio_manager.update_portfolio()
            
            stats_data = {
                'total_balance': portfolio_metrics.total_balance,
                'total_equity': portfolio_metrics.total_equity,
                'total_floating_pnl': portfolio_metrics.total_floating_pnl,
                'total_realized_pnl': portfolio_metrics.total_realized_pnl,
                'net_pnl': portfolio_metrics.net_pnl,
                'win_rate': portfolio_metrics.win_rate,
                'profit_factor': portfolio_metrics.profit_factor,
                'total_trades': portfolio_metrics.total_trades,
                'winning_trades': portfolio_metrics.winning_trades,
                'losing_trades': portfolio_metrics.losing_trades,
                'max_drawdown': portfolio_metrics.max_drawdown,
                'recovery_factor': portfolio_metrics.recovery_factor
            }
            
            self.trade_storage.save_portfolio_stats(stats_data)
            
        except Exception as e:
            logger.error(f"Error saving portfolio stats: {e}")
    
    def _send_telegram_message(self, message: str) -> bool:
        """Send a report when Telegram credentials are available; otherwise log it."""
        if len(message) > 3900:
            chunks = [message[index:index + 3900] for index in range(0, len(message), 3900)]
            return all(self._send_telegram_message(chunk) for chunk in chunks)
        digest = hashlib.sha256(message.encode('utf-8')).hexdigest()
        now = datetime.now(timezone.utc)
        dedupe_seconds = self.config.system.notification_dedupe_seconds
        last_sent = self._telegram_message_times.get(digest)
        if last_sent and (now - last_sent).total_seconds() < dedupe_seconds:
            logger.info("Duplicate Telegram notification suppressed")
            return True
        token = self.config.system.telegram_token or os.getenv("TELEGRAM_TOKEN", "")
        chat_id = self.config.system.telegram_chat_id or os.getenv("TELEGRAM_CHAT_ID", "")
        if not token or not chat_id:
            logger.info("Telegram not configured; report generated locally (%d characters)", len(message))
            self._telegram_message_times[digest] = now
            return True
        try:
            payload = parse.urlencode({"chat_id": chat_id, "text": message}).encode()
            req = request.Request(
                f"https://api.telegram.org/bot{token}/sendMessage",
                data=payload,
                method="POST",
            )
            with request.urlopen(req, timeout=10) as response:
                success = 200 <= response.status < 300
                if success:
                    self._telegram_message_times[digest] = now
                return success
        except Exception as error:
            self.telegram_delivery_failures += 1
            logger.error("Telegram delivery failed (status=%s); credential value suppressed", getattr(error, "code", "unavailable"))
            return False
    
    def get_telegram_diagnostic(self) -> Dict[str, str]:
        """Return safe Telegram configuration/API status without sending a message."""
        token = self.config.system.telegram_token or os.getenv("TELEGRAM_TOKEN", "")
        chat_id = self.config.system.telegram_chat_id or os.getenv("TELEGRAM_CHAT_ID", "")
        if not token or not chat_id:
            return {"configured": "NO", "api_reachable": "NO", "authentication_accepted": "NO", "message_delivery": "NO"}
        try:
            req = request.Request(f"https://api.telegram.org/bot{token}/getMe", method="GET")
            with request.urlopen(req, timeout=10) as response:
                accepted = 200 <= response.status < 300
            return {"configured": "YES", "api_reachable": "YES", "authentication_accepted": "YES" if accepted else "NO", "message_delivery": "NOT_TESTED"}
        except Exception as error:
            logger.error("Telegram diagnostic failed (status=%s); credential value suppressed", getattr(error, "code", "unavailable"))
            return {"configured": "YES", "api_reachable": "NO", "authentication_accepted": "NO", "message_delivery": "NOT_TESTED"}
    def run_continuous(self, interval_minutes: int = 15) -> None:
        """Run the bot continuously"""
        logger.info(f"Starting continuous operation with {interval_minutes} minute intervals")
        
        while True:
            try:
                start_time = time.time()
                
                # Run scan cycle
                self.run_scan()
                
                # Calculate sleep time
                elapsed = time.time() - start_time
                sleep_time = (interval_minutes * 60) - elapsed
                
                if sleep_time > 0:
                    time.sleep(sleep_time)
                
            except KeyboardInterrupt:
                logger.info("Bot stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in continuous operation: {e}")
                time.sleep(60)  # Wait 1 minute before retrying
    
    def get_status(self) -> Dict[str, Any]:
        """Get current bot status"""
        status = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'assets': {},
            'portfolio': {},
            'risk': {},
            'performance': {}
        }
        
        # Get asset status
        for symbol, asset_state in self.asset_manager.get_all_assets().items():
            status['assets'][symbol] = {
                'balance': asset_state.balance,
                'equity': asset_state.equity,
                'open_positions': len(asset_state.open_positions),
                'closed_trades': len(asset_state.closed_trades)
            }
        
        # Get portfolio status
        portfolio_metrics = self.portfolio_manager.update_portfolio()
        status['portfolio'] = {
            'total_balance': portfolio_metrics.total_balance,
            'total_equity': portfolio_metrics.total_equity,
            'net_pnl': portfolio_metrics.net_pnl,
            'win_rate': portfolio_metrics.win_rate,
            'profit_factor': portfolio_metrics.profit_factor
        }
        
        # Get risk status
        risk_metrics = self.risk_manager.calculate_risk_metrics()
        status['risk'] = {
            'risk_score': risk_metrics.get('portfolio_risk_score', 0),
            'exposure_ratio': risk_metrics.get('exposure_ratio', 0),
            'max_drawdown': risk_metrics.get('max_drawdown', 0)
        }
        
        # Get performance status
        performance_data = self.performance_tracker.track_performance()
        status['performance'] = performance_data
        
        return status

def main() -> None:
    """Main entry point"""
    try:
        # Create and run the bot
        bot = AITradingIntelligenceBot()
        
        # Run a single scan cycle (GitHub Actions handles scheduling)
        bot.run_scan()
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise

if __name__ == "__main__":
    main()

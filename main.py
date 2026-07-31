"""
AI Trading Intelligence Bot v2.0 - Main Application
Comprehensive trading system for BTCUSD and XAUUSD with modular architecture.
"""

import json
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

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
        
        # Initialize core components
        self.asset_manager = AssetManager()
        self.market_analyzers: Dict[str, MarketAnalyzer] = {}
        self.signal_engine: Optional[SignalEngine] = None
        self.trade_manager: Optional[TradeManager] = None
        self.portfolio_manager: Optional[PortfolioManager] = None
        self.profit_calculator: Optional[ProfitCalculator] = None
        self.risk_manager: Optional[RiskManager] = None
        self.trade_storage: Optional[TradeStorage] = None
        self.performance_tracker: Optional[PerformanceTracker] = None
        self.telegram_formatter: Optional[TelegramFormatter] = None
        
        # Initialize components
        self._initialize_components()
        
        # Set up monitoring
        self.last_scan_time = datetime.now(timezone.utc)
        self.scan_interval = self.config.system.alert_state_file  # Using as placeholder
        
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
            self.config.trading
        )
        
        # Initialize Telegram formatter
        self.telegram_formatter = TelegramFormatter(
            self.asset_manager,
            self.portfolio_manager,
            self.config.system
        )
        
        # Load existing data from storage
        self._load_existing_data()
    
    def _load_existing_data(self) -> None:
        """Load existing data from storage"""
        try:
            # Load trades
            trades = self.trade_storage.get_trades()
            for trade in trades:
                self.asset_manager.add_open_position(trade.asset, trade)
            
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
    
    def run_scan(self) -> None:
        """Run a complete scan cycle"""
        logger.info("Starting scan cycle")
        
        try:
            # Update portfolio metrics
            portfolio_metrics = self.portfolio_manager.update_portfolio()
            
            # Generate signals for each asset
            signal_results: Dict[str, SignalResult] = {}
            
            for symbol, analyzer in self.market_analyzers.items():
                # Get current price (placeholder - would need real price data)
                current_price = 100000.0  # Placeholder
                previous_price = 99000.0  # Placeholder
                
                # Analyze market
                market_analysis = analyzer.analyze_market(
                    symbol, current_price, previous_price
                )
                
                # Generate signal
                signal_result = self.signal_engine.generate_signal(
                    symbol, market_analysis
                )
                
                signal_results[symbol] = signal_result
                
                # Save signal to storage
                self._save_signal(signal_result)
            
            # Send Telegram reports
            self._send_reports(signal_results)
            
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
            
            logger.info("Scan cycle completed successfully")
            
        except Exception as e:
            logger.error(f"Error during scan cycle: {e}")
    
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
        """Send message to Telegram (placeholder)"""
        # This would use the existing send_telegram_message function
        # For now, just log the message
        logger.info(f"Telegram message: {message}")
        return True
    
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
        
        # Run in continuous mode
        bot.run_continuous(interval_minutes=15)
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise

if __name__ == "__main__":
    main()

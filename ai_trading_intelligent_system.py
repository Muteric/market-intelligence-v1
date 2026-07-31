"""
AI Trading Intelligent System v3.0 - Enhanced Trading Intelligence Bot
Professional-grade trading system with advanced analytics, signal accuracy tracking, and multi-timeframe analysis.
"""

import json
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal, ROUND_HALF_UP

from configuration_manager import ConfigurationManager, AppConfig
from asset_manager import AssetManager, Trade, TradeStatus, PositionDirection
from market_analyzer import MarketAnalyzer, MarketAnalysis, TrendDirection, MarketPhase
from signal_engine import SignalEngine, SignalResult, SignalDecision
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

class SignalAccuracyTracker:
    """Tracks signal accuracy and performance metrics"""
    
    def __init__(self):
        self.signals_generated = 0
        self.signals_correct = 0
        self.buy_signals = 0
        self.buy_correct = 0
        self.sell_signals = 0
        self.sell_correct = 0
        self.hold_signals = 0
        self.hold_correct = 0
        self.signal_history: List[Dict[str, Any]] = []
    
    def record_signal(self, symbol: str, decision: str, was_correct: bool, 
                     market_analysis: MarketAnalysis) -> None:
        """Record a signal and its accuracy"""
        self.signals_generated += 1
        
        if was_correct:
            self.signals_correct += 1
        
        if decision == SignalDecision.BUY.value:
            self.buy_signals += 1
            if was_correct:
                self.buy_correct += 1
        elif decision == SignalDecision.SELL.value:
            self.sell_signals += 1
            if was_correct:
                self.sell_correct += 1
        elif decision == SignalDecision.HOLD.value:
            self.hold_signals += 1
            if was_correct:
                self.hold_correct += 1
        
        signal_record = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'symbol': symbol,
            'decision': decision,
            'was_correct': was_correct,
            'confidence': market_analysis.confidence_score,
            'trend': market_analysis.trend_direction,
            'momentum': market_analysis.momentum_score,
            'sentiment': market_analysis.sentiment_score,
            'volatility': market_analysis.volatility_score
        }
        
        self.signal_history.append(signal_record)
    
    def get_accuracy_report(self) -> Dict[str, Any]:
        """Get signal accuracy report"""
        accuracy = (self.signals_correct / self.signals_generated * 100) if self.signals_generated > 0 else 0.0
        
        buy_accuracy = (self.buy_correct / self.buy_signals * 100) if self.buy_signals > 0 else 0.0
        sell_accuracy = (self.sell_correct / self.sell_signals * 100) if self.sell_signals > 0 else 0.0
        hold_accuracy = (self.hold_correct / self.hold_signals * 100) if self.hold_signals > 0 else 0.0
        
        return {
            'signals_generated': self.signals_generated,
            'signals_correct': self.signals_correct,
            'overall_accuracy': accuracy,
            'buy_signals': self.buy_signals,
            'buy_correct': self.buy_correct,
            'buy_accuracy': buy_accuracy,
            'sell_signals': self.sell_signals,
            'sell_correct': self.sell_correct,
            'sell_accuracy': sell_accuracy,
            'hold_signals': self.hold_signals,
            'hold_correct': self.hold_correct,
            'hold_accuracy': hold_accuracy
        }
    
    def reset_daily(self) -> None:
        """Reset daily counters"""
        # Keep historical data but reset daily counters
        pass

class DynamicConfidenceCalculator:
    """Calculates dynamic confidence based on historical performance"""
    
    def __init__(self, signal_accuracy_tracker: SignalAccuracyTracker):
        self.signal_accuracy_tracker = signal_accuracy_tracker
    
    def calculate_dynamic_confidence(self, symbol: str, market_analysis: MarketAnalysis) -> float:
        """Calculate dynamic confidence based on multiple factors"""
        base_confidence = market_analysis.confidence_score
        
        # Adjust based on historical accuracy for this symbol
        symbol_signals = [s for s in self.signal_accuracy_tracker.signal_history if s['symbol'] == symbol]
        if symbol_signals:
            symbol_correct = sum(1 for s in symbol_signals if s['was_correct'])
            symbol_accuracy = (symbol_correct / len(symbol_signals)) * 100
            
            # Adjust confidence based on symbol-specific accuracy
            accuracy_factor = min(1.0, symbol_accuracy / 50.0)  # Cap at 2x adjustment
            base_confidence *= accuracy_factor
        
        # Adjust based on trend strength
        trend_strength = self._calculate_trend_strength(market_analysis.trend_direction, 
                                                       market_analysis.momentum_score)
        base_confidence *= trend_strength
        
        # Adjust based on volatility
        volatility_factor = self._calculate_volatility_factor(market_analysis.volatility_score)
        base_confidence *= volatility_factor
        
        # Adjust based on indicator conflict
        conflict_factor = self._calculate_conflict_factor(market_analysis)
        base_confidence *= conflict_factor
        
        # Ensure confidence is within bounds
        return max(0.0, min(1.0, base_confidence))
    
    def _calculate_trend_strength(self, trend: str, momentum: float) -> float:
        """Calculate trend strength factor"""
        if trend == "bullish":
            return 1.0 + (momentum * 0.5)
        elif trend == "bearish":
            return 1.0 + (-momentum * 0.5)
        else:
            return 0.8  # Neutral trend has lower confidence
    
    def _calculate_volatility_factor(self, volatility: str) -> float:
        """Calculate volatility factor"""
        factors = {
            "low": 1.2,
            "medium": 1.0,
            "high": 0.7
        }
        return factors.get(volatility, 1.0)
    
    def _calculate_conflict_factor(self, market_analysis: MarketAnalysis) -> float:
        """Calculate conflict factor based on indicator alignment"""
        # Simple conflict calculation based on sentiment vs momentum
        sentiment_momentum_diff = abs(market_analysis.sentiment_score - market_analysis.momentum_score)
        
        if sentiment_momentum_diff > 0.5:
            return 0.8  # High conflict
        elif sentiment_momentum_diff > 0.2:
            return 0.9  # Medium conflict
        else:
            return 1.0  # Low conflict

class TradeQualityCalculator:
    """Calculates trade quality scores"""
    
    def calculate_trade_quality(self, trade: Trade, market_analysis: MarketAnalysis) -> Dict[str, Any]:
        """Calculate quality score for a trade"""
        score = 100.0
        
        # Trend quality
        if market_analysis.trend_direction == "bullish" and trade.direction == PositionDirection.BUY.value:
            score += 20
        elif market_analysis.trend_direction == "bearish" and trade.direction == PositionDirection.SELL.value:
            score += 20
        
        # Momentum quality
        if abs(market_analysis.momentum_score) > 0.7:
            score += 15
        elif abs(market_analysis.momentum_score) > 0.4:
            score += 10
        
        # Volatility quality
        if market_analysis.volatility_score == "low":
            score += 10
        elif market_analysis.volatility_score == "medium":
            score += 5
        
        # Confidence quality
        score += (market_analysis.confidence_score * 20)
        
        # Trade duration quality (avoid too short trades)
        if trade.trade_duration > 24:  # More than 24 hours
            score += 10
        
        # PnL quality
        if trade.realized_pnl > 0:
            score += min(30, trade.roi)  # Cap at 30 points
        
        # Ensure score is within bounds
        score = max(0.0, min(100.0, score))
        
        # Generate reasons
        reasons = self._generate_quality_reasons(trade, market_analysis, score)
        
        return {
            'score': score,
            'reasons': reasons
        }
    
    def _generate_quality_reasons(self, trade: Trade, market_analysis: MarketAnalysis, score: float) -> List[str]:
        """Generate quality reasons"""
        reasons = []
        
        if score >= 90:
            reasons.append("Excellent trend")
            reasons.append("Strong momentum")
            reasons.append("Good volatility")
            reasons.append("Minimal conflict")
        elif score >= 80:
            reasons.append("Good trend")
            reasons.append("Moderate momentum")
            reasons.append("Acceptable volatility")
        elif score >= 70:
            reasons.append("Adequate trend")
            reasons.append("Weak momentum")
            reasons.append("High volatility")
        
        if trade.realized_pnl > 0:
            reasons.append(f"Profit: ${trade.realized_pnl:.2f}")
        
        return reasons

class MarketRegimeDetector:
    """Detects market regimes similar to institutional analysis"""
    
    def detect_regime(self, symbol: str, market_analysis: MarketAnalysis, 
                     price_history: List[float]) -> str:
        """Detect current market regime"""
        if len(price_history) < 10:
            return "Insufficient Data"
        
        # Calculate volatility
        volatility = self._calculate_volatility(price_history)
        
        # Calculate trend strength
        trend_strength = self._calculate_trend_strength(price_history)
        
        # Calculate momentum
        momentum = self._calculate_momentum(price_history)
        
        # Determine regime based on multiple factors
        if volatility > 0.05 and trend_strength > 0.7:
            if momentum > 0:
                return "Strong Trending"
            else:
                return "Strong Bearish"
        
        elif volatility > 0.03 and trend_strength > 0.4:
            if momentum > 0:
                return "Trending"
            else:
                return "Bearish"
        
        elif volatility < 0.02 and trend_strength < 0.3:
            return "Consolidation"
        
        elif volatility > 0.04 and trend_strength < 0.3:
            return "High Risk"
        
        elif momentum > 0.5:
            return "Expansion"
        
        elif momentum < -0.5:
            return "Capitulation"
        
        elif volatility < 0.01:
            return "Low Liquidity"
        
        else:
            return "Neutral"
    
    def _calculate_volatility(self, prices: List[float]) -> float:
        """Calculate price volatility"""
        if len(prices) < 2:
            return 0.0
        
        returns = []
        for i in range(1, len(prices)):
            if prices[i-1] > 0:
                returns.append((prices[i] - prices[i-1]) / prices[i-1])
        
        if not returns:
            return 0.0
        
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        
        return (variance ** 0.5) * 100  # As percentage
    
    def _calculate_trend_strength(self, prices: List[float]) -> float:
        """Calculate trend strength"""
        if len(prices) < 5:
            return 0.0
        
        # Calculate linear regression slope
        x_values = list(range(len(prices)))
        y_values = prices
        
        n = len(x_values)
        if n < 2:
            return 0.0
        
        sum_x = sum(x_values)
        sum_y = sum(y_values)
        sum_xy = sum(x * y for x, y in zip(x_values, y_values))
        sum_x2 = sum(x * x for x in x_values)
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        
        # Normalize slope
        avg_price = sum_y / n
        if avg_price > 0:
            return min(1.0, abs(slope) * 100 / avg_price)
        
        return 0.0
    
    def _calculate_momentum(self, prices: List[float]) -> float:
        """Calculate momentum"""
        if len(prices) < 3:
            return 0.0
        
        recent_prices = prices[-3:]
        
        # Calculate percentage change
        if recent_prices[0] > 0:
            momentum = (recent_prices[-1] - recent_prices[0]) / recent_prices[0]
            return max(-1.0, min(1.0, momentum * 10))  # Normalize to -1 to 1
        
        return 0.0

class MultiTimeframeAnalyzer:
    """Analyzes multiple timeframes"""
    
    def analyze_multi_timeframe(self, symbol: str, price_data: Dict[str, List[float]]) -> Dict[str, Any]:
        """Analyze multiple timeframes"""
        timeframes = ["5M", "15M", "1H", "4H", "Daily"]
        
        analysis = {}
        
        for timeframe in timeframes:
            if timeframe in price_data and len(price_data[timeframe]) >= 3:
                prices = price_data[timeframe]
                
                # Simple analysis for each timeframe
                if len(prices) >= 2:
                    current_price = prices[-1]
                    previous_price = prices[-2]
                    price_change = current_price - previous_price
                    price_change_pct = (price_change / previous_price * 100) if previous_price > 0 else 0
                    
                    # Determine trend
                    if price_change_pct > 0.5:
                        trend = "Bullish"
                    elif price_change_pct < -0.5:
                        trend = "Bearish"
                    else:
                        trend = "Neutral"
                    
                    analysis[timeframe] = {
                        'current_price': current_price,
                        'price_change': price_change,
                        'price_change_pct': price_change_pct,
                        'trend': trend
                    }
        
        # Determine overall signal
        overall_signal = self._determine_overall_signal(analysis)
        
        return {
            'timeframe_analysis': analysis,
            'overall_signal': overall_signal
        }
    
    def _determine_overall_signal(self, analysis: Dict[str, Any]) -> str:
        """Determine overall signal from timeframe analysis"""
        if not analysis:
            return "INSUFFICIENT_DATA"
        
        bullish_count = sum(1 for data in analysis.values() if data['trend'] == "Bullish")
        bearish_count = sum(1 for data in analysis.values() if data['trend'] == "Bearish")
        neutral_count = sum(1 for data in analysis.values() if data['trend'] == "Neutral")
        
        if bullish_count > bearish_count + 1:
            return "BUY"
        elif bearish_count > bullish_count + 1:
            return "SELL"
        else:
            return "HOLD"

class AIBotNarrativeGenerator:
    """Generates AI market narratives"""
    
    def generate_narrative(self, symbol: str, market_analysis: MarketAnalysis, 
                           trade_history: List[Trade]) -> str:
        """Generate a market narrative"""
        narrative = f"{symbol} "
        
        # Add trend information
        if market_analysis.trend_direction == "bullish":
            narrative += "continues making higher highs. "
        elif market_analysis.trend_direction == "bearish":
            narrative += "is experiencing downward pressure. "
        else:
            narrative += "is trading in a range. "
        
        # Add momentum information
        if market_analysis.momentum_score > 0.5:
            narrative += "Momentum remains positive. "
        elif market_analysis.momentum_score < -0.5:
            narrative += "Momentum is negative. "
        else:
            narrative += "Momentum is neutral. "
        
        # Add volume/sentiment information
        if market_analysis.sentiment_score > 0.5:
            narrative += "Bullish sentiment dominates. "
        elif market_analysis.sentiment_score < -0.5:
            narrative += "Bearish sentiment prevails. "
        
        # Add institutional implications
        if market_analysis.volatility_score == "high":
            narrative += "High volatility suggests institutional activity. "
        
        # Add conclusion
        if market_analysis.trend_direction == "bullish" and market_analysis.momentum_score > 0.5:
            narrative += "The probability favors continuation unless support breaks."
        elif market_analysis.trend_direction == "bearish" and market_analysis.momentum_score < -0.5:
            narrative += "The probability favors further downside unless resistance holds."
        else:
            narrative += "The market remains uncertain with mixed signals."
        
        return narrative

class TradeLifecycleTracker:
    """Tracks trade lifecycle and progress"""
    
    def track_trade_lifecycle(self, trade: Trade) -> Dict[str, Any]:
        """Track trade lifecycle and progress"""
        if trade.status != TradeStatus.OPEN.value:
            return {
                'status': 'CLOSED',
                'age': trade.trade_duration,
                'progress': 100.0,
                'floating_profit': 0.0
            }
        
        # Calculate age
        age_hours = trade.trade_duration
        
        # Calculate progress (simplified - based on age)
        progress = min(100.0, (age_hours / 24) * 100)  # Cap at 100%
        
        # Calculate floating profit
        floating_profit = trade.floating_pnl
        
        return {
            'status': 'OPEN',
            'age_hours': age_hours,
            'progress': progress,
            'floating_profit': floating_profit
        }

class PortfolioEquityCurve:
    """Maintains equity curve for portfolio analysis"""
    
    def __init__(self):
        self.equity_history: List[Dict[str, Any]] = []
    
    def record_equity(self, timestamp: datetime, balance: float, equity: float, 
                     trades: List[Trade]) -> None:
        """Record equity point"""
        total_pnl = equity - balance
        
        equity_point = {
            'timestamp': timestamp.isoformat(),
            'balance': balance,
            'equity': equity,
            'total_pnl': total_pnl,
            'trades_count': len(trades),
            'winning_trades': len([t for t in trades if t.realized_pnl > 0]),
            'losing_trades': len([t for t in trades if t.realized_pnl < 0])
        }
        
        self.equity_history.append(equity_point)
    
    def get_equity_curve(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get equity curve for specified period"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        return [
            point for point in self.equity_history
            if datetime.fromisoformat(point['timestamp'].replace('Z', '+00:00')) >= cutoff_date
        ]

class PerformanceBenchmark:
    """Compares AI performance against benchmarks"""
    
    def compare_with_benchmark(self, ai_return: float, benchmark_return: float, 
                              ai_trades: List[Trade], benchmark_trades: List[Trade]) -> Dict[str, Any]:
        """Compare AI performance with benchmark"""
        outperformance = ai_return - benchmark_return
        
        # Calculate Sharpe ratio (simplified)
        ai_volatility = self._calculate_volatility(ai_trades)
        benchmark_volatility = self._calculate_volatility(benchmark_trades)
        
        ai_sharpe = (ai_return - 0.02) / ai_volatility if ai_volatility > 0 else 0
        benchmark_sharpe = (benchmark_return - 0.02) / benchmark_volatility if benchmark_volatility > 0 else 0
        
        return {
            'ai_strategy': ai_return,
            'benchmark': benchmark_return,
            'outperformance': outperformance,
            'ai_sharpe': ai_sharpe,
            'benchmark_sharpe': benchmark_sharpe,
            'value_added': outperformance > 0
        }
    
    def _calculate_volatility(self, trades: List[Trade]) -> float:
        """Calculate volatility from trades"""
        if not trades:
            return 0.0
        
        returns = []
        for trade in trades:
            if trade.position_size > 0 and trade.leverage > 0:
                trade_return = (trade.realized_pnl / (trade.position_size * trade.leverage)) * 100
                returns.append(trade_return)
        
        if not returns:
            return 0.0
        
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        
        return (variance ** 0.5) / 100  # As decimal

class AITradingIntelligentSystem:
    """Enhanced AI Trading Intelligent System v3.0"""
    
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
        
        # Initialize enhanced components
        self.signal_accuracy_tracker = SignalAccuracyTracker()
        self.dynamic_confidence_calculator = DynamicConfidenceCalculator(self.signal_accuracy_tracker)
        self.trade_quality_calculator = TradeQualityCalculator()
        self.market_regime_detector = MarketRegimeDetector()
        self.multi_timeframe_analyzer = MultiTimeframeAnalyzer()
        self.ai_narrative_generator = AIBotNarrativeGenerator()
        self.trade_lifecycle_tracker = TradeLifecycleTracker()
        self.portfolio_equity_curve = PortfolioEquityCurve()
        self.performance_benchmark = PerformanceBenchmark()
        
        # Initialize components
        self._initialize_components()
        
        # Set up monitoring
        self.last_scan_time = datetime.now(timezone.utc)
        self.scan_interval = 15  # minutes
        
        logger.info("AI Trading Intelligent System v3.0 initialized successfully")
    
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
        """Run a complete scan cycle with enhanced features"""
        logger.info("Starting enhanced scan cycle")
        
        try:
            # Update portfolio metrics
            portfolio_metrics = self.portfolio_manager.update_portfolio()
            
            # Generate signals for each asset with enhanced analysis
            signal_results: Dict[str, SignalResult] = {}
            
            for symbol, analyzer in self.market_analyzers.items():
                # Get current price (placeholder - would need real price data)
                current_price = 100000.0  # Placeholder
                previous_price = 99000.0  # Placeholder
                
                # Analyze market
                market_analysis = analyzer.analyze_market(
                    symbol, current_price, previous_price
                )
                
                # Calculate dynamic confidence
                dynamic_confidence = self.dynamic_confidence_calculator.calculate_dynamic_confidence(
                    symbol, market_analysis
                )
                
                # Generate signal
                signal_result = self.signal_engine.generate_signal(
                    symbol, market_analysis
                )
                
                # Update signal result with dynamic confidence
                signal_result.confidence = dynamic_confidence
                
                signal_results[symbol] = signal_result
                
                # Record signal accuracy
                self.signal_accuracy_tracker.record_signal(
                    symbol, signal_result.decision, False, market_analysis  # Placeholder for correctness
                )
                
                # Save signal to storage
                self._save_signal(signal_result)
            
            # Send enhanced Telegram reports
            self._send_enhanced_reports(signal_results)
            
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
            
        except Exception as e:
            logger.error(f"Error during enhanced scan cycle: {e}")
    
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
    
    def _send_enhanced_reports(self, signal_results: Dict[str, SignalResult]) -> None:
        """Send enhanced Telegram reports"""
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
            logger.error(f"Error sending enhanced reports: {e}")
    
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
        """Get current bot status with enhanced metrics"""
        status = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'assets': {},
            'portfolio': {},
            'risk': {},
            'performance': {},
            'signal_accuracy': self.signal_accuracy_tracker.get_accuracy_report()
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
        # Create and run the enhanced bot
        bot = AITradingIntelligentSystem()
        
        # Run in continuous mode
        bot.run_continuous(interval_minutes=15)
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise

if __name__ == "__main__":
    main()

"""
Comprehensive test suite for the upgraded AI Trading Intelligence System
Tests all new components and their integration.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any
from unittest.mock import Mock, patch

from configuration_manager import ConfigurationManager, AppConfig, AssetConfig, PortfolioConfig, TradingConfig, SystemConfig
from asset_manager import AssetManager, Trade, TradeStatus, PositionDirection
from market_analyzer import MarketAnalyzer, MarketAnalysis, TrendDirection, VolatilityScore, MarketPhase
from signal_engine import SignalEngine, SignalResult, SignalDecision
from market_data_aggregator import MarketDataAggregator, MarketDataPoint, PriceValidationResult
from technical_indicators import TechnicalIndicators, TechnicalIndicatorsResult
from multi_timeframe_analyzer import MultiTimeframeAnalyzer, MultiTimeframeResult
from ai_decision_engine import AIDecisionEngine, AIDecisionResult, MarketRegime, RiskMetrics, PortfolioState
from trade_execution_simulator import TradeExecutionSimulator, TradeExecution, PortfolioMetrics
from reliability_manager import ReliabilityManager
from telegram_formatter import TelegramFormatter, ReportFormat

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestMarketDataAggregator:
    """Test Market Data Aggregator functionality"""
    
    def __init__(self):
        self.aggregator = MarketDataAggregator()
    
    async def test_multi_source_data_collection(self):
        """Test that data is collected from multiple sources"""
        logger.info("Testing multi-source data collection...")
        
        # Mock the provider fetch methods
        with patch.object(self.aggregator, '_fetch_from_provider') as mock_fetch:
            # Mock successful responses from multiple providers
            mock_fetch.side_effect = [
                self._create_mock_binance_data(),
                self._create_mock_coingecko_data(),
                self._create_mock_alphavantage_data(),
                self._create_mock_twelvedata_data(),
                self._create_mock_yahoo_finance_data()
            ]
            
            # Test data collection
            result = await self.aggregator.fetch_market_data("BTCUSD")
            
            # Verify data was collected from multiple sources
            assert len(result.provider_prices) >= 3, "Should have data from at least 3 providers"
            assert result.consensus_price > 0, "Should have valid consensus price"
            assert result.confidence_score > 0, "Should have confidence score"
            
            logger.info("✓ Multi-source data collection test passed")
    
    async def test_price_validation(self):
        """Test price validation and outlier detection"""
        logger.info("Testing price validation...")
        
        # Create mock data with outliers
        valid_data = {
            'binance': self._create_mock_binance_data(),
            'coingecko': self._create_mock_coingecko_data(),
            'alphavantage': self._create_mock_alphavantage_data(),
        }
        
        # Add outlier data
        outlier_data = self._create_mock_binance_data()
        outlier_data.price = 999999.0  # Extreme outlier
        valid_data['outlier'] = outlier_data
        
        # Test validation
        result = self.aggregator._validate_and_consensus("BTCUSD", valid_data)
        
        # Verify outliers were detected
        assert 'outlier' in result.outlier_providers, "Outlier should be detected"
        assert len(result.outlier_providers) == 1, "Should have exactly one outlier"
        
        logger.info("✓ Price validation test passed")
    
    def _create_mock_binance_data(self) -> MarketDataPoint:
        """Create mock Binance data"""
        return MarketDataPoint(
            symbol="BTCUSD",
            price=50000.0,
            bid=49999.0,
            ask=50001.0,
            spread=2.0,
            volume=1000.0,
            timestamp=datetime.now(timezone.utc),
            provider="Binance",
            source="binance"
        )
    
    def _create_mock_coingecko_data(self) -> MarketDataPoint:
        """Create mock CoinGecko data"""
        return MarketDataPoint(
            symbol="BTCUSD",
            price=50001.0,
            bid=50000.5,
            ask=50001.5,
            spread=1.0,
            volume=800.0,
            timestamp=datetime.now(timezone.utc),
            provider="CoinGecko",
            source="coingecko"
        )
    
    def _create_mock_alphavantage_data(self) -> MarketDataPoint:
        """Create mock Alpha Vantage data"""
        return MarketDataPoint(
            symbol="BTCUSD",
            price=49999.5,
            bid=49999.0,
            ask=50000.0,
            spread=1.0,
            volume=600.0,
            timestamp=datetime.now(timezone.utc),
            provider="Alpha Vantage",
            source="alphavantage"
        )
    
    def _create_mock_twelvedata_data(self) -> MarketDataPoint:
        """Create mock Twelve Data data"""
        return MarketDataPoint(
            symbol="BTCUSD",
            price=50000.5,
            bid=50000.0,
            ask=50001.0,
            spread=1.0,
            volume=700.0,
            timestamp=datetime.now(timezone.utc),
            provider="Twelve Data",
            source="twelvedata"
        )
    
    def _create_mock_yahoo_finance_data(self) -> MarketDataPoint:
        """Create mock Yahoo Finance data"""
        return MarketDataPoint(
            symbol="BTCUSD",
            price=50002.0,
            bid=50001.5,
            ask=50002.5,
            spread=1.0,
            volume=500.0,
            timestamp=datetime.now(timezone.utc),
            provider="Yahoo Finance",
            source="yahoo_finance"
        )

class TestTechnicalIndicators:
    """Test Technical Indicators functionality"""
    
    def __init__(self):
        self.indicators = TechnicalIndicators()
    
    def test_rsi_calculation(self):
        """Test RSI calculation"""
        logger.info("Testing RSI calculation...")
        
        # Add price data
        for i in range(20):
            self.indicators.update_price_data("BTCUSD", 50000.0 + i * 10, 1000.0)
        
        # Calculate indicators
        result = self.indicators.calculate_all_indicators("BTCUSD")
        
        # Verify RSI
        assert result.rsi.rsi > 0, "RSI should be positive"
        assert result.rsi.rsi <= 100, "RSI should be <= 100"
        assert isinstance(result.rsi.overbought, bool), "Overbought should be boolean"
        assert isinstance(result.rsi.oversold, bool), "Oversold should be boolean"
        
        logger.info("✓ RSI calculation test passed")
    
    def test_macd_calculation(self):
        """Test MACD calculation"""
        logger.info("Testing MACD calculation...")
        
        # Add price data
        for i in range(30):
            self.indicators.update_price_data("BTCUSD", 50000.0 + i * 10, 1000.0)
        
        # Calculate indicators
        result = self.indicators.calculate_all_indicators("BTCUSD")
        
        # Verify MACD
        assert result.macd.macd != 0, "MACD should not be zero"
        assert result.macd.signal != 0, "Signal should not be zero"
        assert result.macd.histogram != 0, "Histogram should not be zero"
        assert isinstance(result.macd.trend, str), "Trend should be string"
        
        logger.info("✓ MACD calculation test passed")
    
    def test_ema_calculation(self):
        """Test EMA calculation"""
        logger.info("Testing EMA calculation...")
        
        # Add price data
        for i in range(200):
            self.indicators.update_price_data("BTCUSD", 50000.0 + i * 10, 1000.0)
        
        # Calculate indicators
        result = self.indicators.calculate_all_indicators("BTCUSD")
        
        # Verify EMA
        assert result.ema.ema_20 > 0, "EMA 20 should be positive"
        assert result.ema.ema_50 > 0, "EMA 50 should be positive"
        assert result.ema.ema_100 > 0, "EMA 100 should be positive"
        assert result.ema.ema_200 > 0, "EMA 200 should be positive"
        assert isinstance(result.ema.trend, str), "Trend should be string"
        
        logger.info("✓ EMA calculation test passed")
    
    def test_bollinger_bands_calculation(self):
        """Test Bollinger Bands calculation"""
        logger.info("Testing Bollinger Bands calculation...")
        
        # Add price data
        for i in range(20):
            self.indicators.update_price_data("BTCUSD", 50000.0 + i * 10, 1000.0)
        
        # Calculate indicators
        result = self.indicators.calculate_all_indicators("BTCUSD")
        
        # Verify Bollinger Bands
        assert result.bollinger_bands.upper_band > result.bollinger_bands.middle_band, "Upper band should be above middle band"
        assert result.bollinger_bands.lower_band < result.bollinger_bands.middle_band, "Lower band should be below middle band"
        assert result.bollinger_bands.bandwidth > 0, "Bandwidth should be positive"
        assert result.bollinger_bands.percent_b > 0, "Percent B should be positive"
        assert isinstance(result.bollinger_bands.squeeze, bool), "Squeeze should be boolean"
        
        logger.info("✓ Bollinger Bands calculation test passed")

class TestMultiTimeframeAnalyzer:
    """Test Multi-Timeframe Analyzer functionality"""
    
    def __init__(self):
        self.analyzer = MultiTimeframeAnalyzer()
    
    def test_timeframe_data_collection(self):
        """Test timeframe data collection"""
        logger.info("Testing timeframe data collection...")
        
        # Add data for different timeframes
        self.analyzer.update_timeframe_data("BTCUSD", "5M", 50000.0, 1000.0)
        self.analyzer.update_timeframe_data("BTCUSD", "15M", 50100.0, 1200.0)
        self.analyzer.update_timeframe_data("BTCUSD", "1H", 50200.0, 1500.0)
        self.analyzer.update_timeframe_data("BTCUSD", "4H", 50300.0, 1800.0)
        self.analyzer.update_timeframe_data("BTCUSD", "Daily", 50400.0, 2000.0)
        
        # Analyze multi-timeframe
        result = self.analyzer.analyze_multi_timeframe("BTCUSD")
        
        # Verify results
        assert len(result.timeframe_analyses) == 5, "Should have 5 timeframes"
        assert result.overall_signal in ["BUY", "SELL", "HOLD"], "Overall signal should be valid"
        assert result.trend_alignment in ["BULLISH_ALIGNMENT", "BEARISH_ALIGNMENT", "MIXED_ALIGNMENT", "NEUTRAL_ALIGNMENT"], "Trend alignment should be valid"
        assert result.confidence_score > 0, "Confidence score should be positive"
        
        logger.info("✓ Timeframe data collection test passed")
    
    def test_trend_alignment(self):
        """Test trend alignment detection"""
        logger.info("Testing trend alignment...")
        
        # Add bullish data for all timeframes
        for timeframe in ["5M", "15M", "1H", "4H", "Daily"]:
            self.analyzer.update_timeframe_data("BTCUSD", timeframe, 50000.0 + 100, 1000.0)
        
        # Analyze multi-timeframe
        result = self.analyzer.analyze_multi_timeframe("BTCUSD")
        
        # Verify bullish alignment
        assert result.trend_alignment == "BULLISH_ALIGNMENT", "Should detect bullish alignment"
        
        logger.info("✓ Trend alignment test passed")

class TestAIDecisionEngine:
    """Test AI Decision Engine functionality"""
    
    def __init__(self):
        self.asset_manager = AssetManager()
        self.trading_config = TradingConfig()
        self.ai_engine = AIDecisionEngine(self.asset_manager, self.trading_config)
    
    def test_ai_decision_generation(self):
        """Test AI decision generation"""
        logger.info("Testing AI decision generation...")
        
        # Create mock market analysis
        market_analysis = MarketAnalysis(
            symbol="BTCUSD",
            timestamp=datetime.now(timezone.utc),
            current_price=50000.0,
            previous_price=49000.0,
            price_change=1000.0,
            price_change_percent=2.04,
            trend_direction="bullish",
            momentum_score=0.7,
            sentiment_score=0.6,
            volatility_score="medium",
            confidence_score=0.8,
            market_pressure=0.5,
            strength_score=0.7,
            trend_quality="Strong",
            market_phase="Strong Bullish",
            reasoning=["Bullish trend detected", "Strong positive momentum"]
        )
        
        # Create mock technical indicators
        technical_indicators = TechnicalIndicatorsResult(
            symbol="BTCUSD",
            timestamp=datetime.now(timezone.utc),
            rsi=Mock(rsi=60.0, overbought=False, oversold=False, trend="bullish"),
            macd=Mock(macd=100.0, signal=80.0, histogram=20.0, macd_histogram=20.0, trend="bullish"),
            ema=Mock(ema_20=50100.0, ema_50=50200.0, ema_100=50300.0, ema_200=50400.0, trend="bullish"),
            sma=Mock(sma_50=50000.0, sma_200=49800.0, cross="bullish_cross"),
            bollinger_bands=Mock(upper_band=50500.0, middle_band=50200.0, lower_band=49900.0, bandwidth=600.0, percent_b=0.5, squeeze=False),
            atr=Mock(atr=100.0, normalized_atr=0.2, volatility="medium"),
            adx=Mock(adx=25.0, di_plus=20.0, di_minus=10.0, trend_strength="strong", trend_direction="bullish"),
            stochastic=Mock(k=70.0, d=65.0, overbought=False, oversold=False, trend="bullish"),
            vwap=Mock(vwap=50100.0, deviation=0.1, trend="above_vwap"),
            obv=Mock(obv=1000000.0, obv_trend="bullish", volume_trend="increasing"),
            ichimoku=Mock(conversion_line=50100.0, base_line=50200.0, leading_span1=50300.0, leading_span2=50400.0, lagging_span=50000.0, cloud_thickness=100.0, cloud_direction="bullish", tenkan_sen=50100.0, kijun_sen=50200.0),
            fibonacci=Mock(levels={0.0: 50500.0, 0.236: 50300.0, 0.382: 50100.0, 0.5: 49900.0, 0.618: 49700.0, 0.786: 49500.0}, current_price=50000.0, nearest_level="0.382", nearest_distance=100.0),
            pivot_points=Mock(pivot=50000.0, r1=50500.0, r2=51000.0, r3=51500.0, s1=49500.0, s2=49000.0, s3=48500.0, current_price=50000.0, position="above_r1"),
            overall_trend="bullish",
            momentum_score=0.7,
            volatility_score="medium",
            confidence_score=0.8
        )
        
        # Create mock multi-timeframe result
        multi_timeframe = MultiTimeframeResult(
            symbol="BTCUSD",
            timestamp=datetime.now(timezone.utc),
            timeframe_analyses={},
            overall_signal="BUY",
            trend_alignment="BULLISH_ALIGNMENT",
            trend_strength=0.8,
            momentum_alignment=0.7,
            confidence_score=0.85,
            key_levels={"average_price": 50000.0, "price_range": 1000.0, "price_volatility": 2.0},
            support_resistance={"support": [49500.0], "resistance": [50500.0]}
        )
        
        # Create mock portfolio state
        portfolio_state = PortfolioState(
            total_balance=10000.0,
            total_equity=10500.0,
            floating_pnl=500.0,
            realized_pnl=200.0,
            net_pnl=700.0,
            win_rate=60.0,
            profit_factor=1.5,
            max_drawdown=10.0,
            open_positions_count=1,
            daily_trades=5,
            weekly_trades=25,
            monthly_trades=100
        )
        
        # Create mock market regime
        market_regime = MarketRegime(
            regime="Strong Bullish",
            strength=0.8,
            description="Strong bullish trend with high momentum"
        )
        
        # Create mock risk metrics
        risk_metrics = RiskMetrics(
            volatility_score=0.5,
            correlation_score=0.3,
            drawdown_score=0.2,
            exposure_score=0.4,
            overall_risk_score=0.35
        )
        
        # Generate AI decision
        result = self.ai_engine.generate_decision(
            "BTCUSD",
            market_analysis,
            technical_indicators,
            multi_timeframe,
            50000.0,
            49000.0
        )
        
        # Verify results
        assert result.decision in ["BUY", "SELL", "HOLD"], "Decision should be valid"
        assert result.confidence_score > 0, "Confidence score should be positive"
        assert result.trade_quality_score > 0, "Trade quality score should be positive"
        assert result.market_narrative is not None, "Market narrative should not be None"
        assert result.ai_explanation is not None, "AI explanation should not be None"
        
        logger.info("✓ AI decision generation test passed")

class TestTradeExecutionSimulator:
    """Test Trade Execution Simulator functionality"""
    
    def __init__(self):
        self.asset_manager = AssetManager()
        self.portfolio_config = PortfolioConfig()
        self.trading_config = TradingConfig()
        self.simulator = TradeExecutionSimulator(self.asset_manager, self.portfolio_config, self.trading_config)
    
    def test_trade_execution(self):
        """Test trade execution"""
        logger.info("Testing trade execution...")
        
        # Execute a buy trade
        trade = self.simulator.execute_trade("BTCUSD", "BUY", 50000.0, 0.8, None)
        
        # Verify trade execution
        assert trade is not None, "Trade should be executed"
        assert trade.asset == "BTCUSD", "Trade asset should be BTCUSD"
        assert trade.direction == "BUY", "Trade direction should be BUY"
        assert trade.entry_price > 0, "Entry price should be positive"
        assert trade.position_size > 0, "Position size should be positive"
        
        logger.info("✓ Trade execution test passed")
    
    def test_portfolio_metrics_calculation(self):
        """Test portfolio metrics calculation"""
        logger.info("Testing portfolio metrics calculation...")
        
        # Get portfolio metrics
        metrics = self.simulator.update_portfolio_metrics()
        
        # Verify metrics
        assert metrics.total_balance >= 0, "Total balance should be non-negative"
        assert metrics.total_equity >= 0, "Total equity should be non-negative"
        assert metrics.floating_pnl >= 0, "Floating PnL should be non-negative"
        assert metrics.realized_pnl >= 0, "Realized PnL should be non-negative"
        assert metrics.net_pnl >= 0, "Net PnL should be non-negative"
        assert metrics.win_rate >= 0, "Win rate should be non-negative"
        assert metrics.profit_factor >= 0, "Profit factor should be non-negative"
        assert metrics.max_drawdown >= 0, "Max drawdown should be non-negative"
        assert metrics.current_exposure >= 0, "Current exposure should be non-negative"
        
        logger.info("✓ Portfolio metrics calculation test passed")

class TestReliabilityManager:
    """Test Reliability Manager functionality"""
    
    def __init__(self):
        self.reliability_manager = ReliabilityManager()
    
    async def test_reliability_execution(self):
        """Test reliable execution with retry logic"""
        logger.info("Testing reliable execution...")
        
        # Create a mock function that fails twice then succeeds
        call_count = 0
        
        async def mock_function():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise Exception("Simulated failure")
            return "Success"
        
        # Execute with reliability
        result = await self.reliability_manager.execute_with_reliability(
            "test_component",
            mock_function
        )
        
        # Verify result
        assert result == "Success", "Should eventually succeed"
        assert call_count == 3, "Should have tried 3 times"
        
        logger.info("✓ Reliable execution test passed")
    
    def test_health_status(self):
        """Test health status tracking"""
        logger.info("Testing health status...")
        
        # Get health report
        report = self.reliability_manager.get_health_report()
        
        # Verify report
        assert report['timestamp'] is not None, "Timestamp should be present"
        assert 'components' in report, "Components should be present"
        assert 'overall_status' in report, "Overall status should be present"
        
        logger.info("✓ Health status test passed")

class TestTelegramFormatter:
    """Test Telegram Formatter functionality"""
    
    def __init__(self):
        self.asset_manager = AssetManager()
        self.portfolio_manager = Mock()
        self.system_config = SystemConfig()
        self.formatter = TelegramFormatter(self.asset_manager, self.portfolio_manager, self.system_config)
    
    def test_signal_report_formatting(self):
        """Test signal report formatting"""
        logger.info("Testing signal report formatting...")
        
        # Create mock signal result
        signal_result = Mock(
            symbol="BTCUSD",
            timestamp=datetime.now(timezone.utc),
            decision="BUY",
            confidence=0.8,
            market_analysis=Mock(
                current_price=50000.0,
                previous_price=49000.0,
                price_change=1000.0,
                price_change_percent=2.04,
                trend_direction="bullish",
                momentum_score=0.7,
                sentiment_score=0.6,
                volatility_score="medium",
                confidence_score=0.8,
                market_pressure=0.5,
                strength_score=0.7,
                trend_quality="Strong",
                market_phase="Strong Bullish",
                reasoning=["Bullish trend detected", "Strong positive momentum"]
            ),
            action_taken="BUY - Opened new position (Total: 1/3)",
            positions_opened=1,
            positions_closed=0
        )
        
        # Format signal report
        report = self.formatter.format_signal_report(signal_result, "professional")
        
        # Verify report
        assert isinstance(report, str), "Report should be a string"
        assert len(report) > 0, "Report should not be empty"
        assert "BTCUSD" in report, "Report should contain symbol"
        assert "BUY" in report, "Report should contain decision"
        
        logger.info("✓ Signal report formatting test passed")
    
    def test_portfolio_report_formatting(self):
        """Test portfolio report formatting"""
        logger.info("Testing portfolio report formatting...")
        
        # Format portfolio report
        report = self.formatter.format_portfolio_report("professional")
        
        # Verify report
        assert isinstance(report, str), "Report should be a string"
        assert len(report) > 0, "Report should not be empty"
        
        logger.info("✓ Portfolio report formatting test passed")

class TestIntegration:
    """Test integration of all components"""
    
    def __init__(self):
        self.config_manager = ConfigurationManager()
        self.config = self.config_manager.get_config()
        
        # Initialize all components
        self.asset_manager = AssetManager()
        self.market_data_aggregator = MarketDataAggregator()
        self.technical_indicators = TechnicalIndicators()
        self.multi_timeframe_analyzer = MultiTimeframeAnalyzer()
        self.ai_decision_engine = AIDecisionEngine(self.asset_manager, self.config.trading)
        self.trade_execution_simulator = TradeExecutionSimulator(self.asset_manager, self.config.portfolio, self.config.trading)
        self.reliability_manager = ReliabilityManager()
        self.telegram_formatter = TelegramFormatter(self.asset_manager, Mock(), self.config.system)
    
    async def test_complete_workflow(self):
        """Test complete workflow with all components"""
        logger.info("Testing complete workflow...")
        
        # Step 1: Market data aggregation
        price_validation = await self.market_data_aggregator.fetch_market_data("BTCUSD")
        assert price_validation.consensus_price > 0, "Should have valid consensus price"
        
        # Step 2: Technical indicators
        self.technical_indicators.update_price_data("BTCUSD", price_validation.consensus_price, 1000.0)
        technical_indicators = self.technical_indicators.calculate_all_indicators("BTCUSD")
        assert technical_indicators.overall_trend in ["bullish", "bearish", "neutral"], "Should have valid trend"
        
        # Step 3: Multi-timeframe analysis
        self.multi_timeframe_analyzer.update_timeframe_data("BTCUSD", "5M", price_validation.consensus_price, 1000.0)
        self.multi_timeframe_analyzer.update_timeframe_data("BTCUSD", "15M", price_validation.consensus_price, 1200.0)
        self.multi_timeframe_analyzer.update_timeframe_data("BTCUSD", "1H", price_validation.consensus_price, 1500.0)
        self.multi_timeframe_analyzer.update_timeframe_data("BTCUSD", "4H", price_validation.consensus_price, 1800.0)
        self.multi_timeframe_analyzer.update_timeframe_data("BTCUSD", "Daily", price_validation.consensus_price, 2000.0)
        
        multi_timeframe = self.multi_timeframe_analyzer.analyze_multi_timeframe("BTCUSD")
        assert multi_timeframe.overall_signal in ["BUY", "SELL", "HOLD"], "Should have valid signal"
        
        # Step 4: AI decision
        market_analysis = MarketAnalysis(
            symbol="BTCUSD",
            timestamp=datetime.now(timezone.utc),
            current_price=price_validation.consensus_price,
            previous_price=price_validation.consensus_price * 0.99,
            price_change=price_validation.consensus_price * 0.01,
            price_change_percent=1.0,
            trend_direction="bullish",
            momentum_score=0.6,
            sentiment_score=0.5,
            volatility_score="medium",
            confidence_score=0.7,
            market_pressure=0.4,
            strength_score=0.6,
            trend_quality="Moderate",
            market_phase="Trending",
            reasoning=["Bullish trend detected"]
        )
        
        ai_decision = self.ai_decision_engine.generate_decision(
            "BTCUSD",
            market_analysis,
            technical_indicators,
            multi_timeframe,
            price_validation.consensus_price,
            price_validation.consensus_price * 0.99
        )
        assert ai_decision.decision in ["BUY", "SELL", "HOLD"], "Should have valid decision"
        
        # Step 5: Trade execution
        trade = self.trade_execution_simulator.execute_trade(
            "BTCUSD",
            ai_decision.decision,
            price_validation.consensus_price,
            ai_decision.confidence_score,
            market_analysis
        )
        
        if trade:
            # Close trade
            self.trade_execution_simulator.close_trade("BTCUSD", trade.id, price_validation.consensus_price * 1.02)
        
        # Step 6: Portfolio metrics
        portfolio_metrics = self.trade_execution_simulator.update_portfolio_metrics()
        assert portfolio_metrics.total_balance >= 0, "Should have valid balance"
        
        # Step 7: Generate report
        report = self.telegram_formatter.format_signal_report(
            Mock(
                symbol="BTCUSD",
                timestamp=datetime.now(timezone.utc),
                decision=ai_decision.decision,
                confidence=ai_decision.confidence_score,
                market_analysis=market_analysis,
                action_taken=f"{ai_decision.decision} - Trade executed",
                positions_opened=1 if trade else 0,
                positions_closed=1 if trade else 0
            ),
            "professional"
        )
        
        assert isinstance(report, str), "Report should be a string"
        assert len(report) > 0, "Report should not be empty"
        
        logger.info("✓ Complete workflow test passed")

async def run_all_tests():
    """Run all tests"""
    logger.info("Starting comprehensive test suite...")
    
    # Test Market Data Aggregator
    market_data_tester = TestMarketDataAggregator()
    await market_data_tester.test_multi_source_data_collection()
    await market_data_tester.test_price_validation()
    
    # Test Technical Indicators
    technical_tester = TestTechnicalIndicators()
    technical_tester.test_rsi_calculation()
    technical_tester.test_macd_calculation()
    technical_tester.test_ema_calculation()
    technical_tester.test_bollinger_bands_calculation()
    
    # Test Multi-Timeframe Analyzer
    timeframe_tester = TestMultiTimeframeAnalyzer()
    timeframe_tester.test_timeframe_data_collection()
    timeframe_tester.test_trend_alignment()
    
    # Test AI Decision Engine
    ai_tester = TestAIDecisionEngine()
    ai_tester.test_ai_decision_generation()
    
    # Test Trade Execution Simulator
    execution_tester = TestTradeExecutionSimulator()
    execution_tester.test_trade_execution()
    execution_tester.test_portfolio_metrics_calculation()
    
    # Test Reliability Manager
    reliability_tester = TestReliabilityManager()
    await reliability_tester.test_reliability_execution()
    reliability_tester.test_health_status()
    
    # Test Telegram Formatter
    telegram_tester = TestTelegramFormatter()
    telegram_tester.test_signal_report_formatting()
    telegram_tester.test_portfolio_report_formatting()
    
    # Test Integration
    integration_tester = TestIntegration()
    await integration_tester.test_complete_workflow()
    
    logger.info("✓ All tests passed successfully!")

if __name__ == "__main__":
    asyncio.run(run_all_tests())
"""
Test Suite for AI Trading Intelligence Bot
Tests the system with both BTCUSD and XAUUSD assets.
"""

import unittest
import json
import tempfile
import os
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from configuration_manager import ConfigurationManager, AppConfig, PortfolioConfig, AssetConfig, TradingConfig, SystemConfig
from asset_manager import AssetManager, Trade, TradeStatus, PositionDirection
from market_analyzer import MarketAnalyzer, MarketAnalysis, TrendDirection, VolatilityScore
from signal_engine import SignalEngine, SignalResult, SignalDecision
from trade_manager import TradeManager
from portfolio_manager import PortfolioManager
from profit_calculator import ProfitCalculator
from risk_manager import RiskManager
from trade_storage import TradeStorage, StorageType
from performance_tracker import PerformanceTracker
from telegram_formatter import TelegramFormatter, ReportFormat

class TestConfigurationManager(unittest.TestCase):
    """Test ConfigurationManager"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "test_config.json")
    
    def tearDown(self):
        if os.path.exists(self.config_file):
            os.remove(self.config_file)
        os.rmdir(self.temp_dir)
    
    def test_default_config(self):
        """Test default configuration creation"""
        config_manager = ConfigurationManager(self.config_file)
        config = config_manager.get_config()
        
        self.assertIsInstance(config, AppConfig)
        self.assertIsInstance(config.portfolio, PortfolioConfig)
        self.assertIsInstance(config.assets, dict)
        self.assertIsInstance(config.trading, TradingConfig)
        self.assertIsInstance(config.system, SystemConfig)
        
        # Check default values
        self.assertEqual(config.portfolio.initial_balance, 100.0)
        self.assertEqual(config.portfolio.base_position_size, 0.5)
        self.assertEqual(config.portfolio.scaling_position_size, 0.25)
        self.assertEqual(config.portfolio.leverage, 400.0)
        self.assertEqual(config.portfolio.max_positions, 3)
        
        # Check assets
        self.assertIn("BTCUSD", config.assets)
        self.assertIn("XAUUSD", config.assets)
        
        btc_asset = config.assets["BTCUSD"]
        self.assertEqual(btc_asset.symbol, "BTCUSD")
        self.assertTrue(btc_asset.enabled)
        self.assertEqual(btc_asset.min_confidence, 0.5)
    
    def test_config_validation(self):
        """Test configuration validation"""
        config_manager = ConfigurationManager(self.config_file)
        
        # Test invalid portfolio config
        updates = {
            'portfolio': {
                'initial_balance': -100.0,  # Invalid: negative balance
                'base_position_size': 1.5,  # Invalid: > 1
                'scaling_position_size': 0.0,  # Invalid: 0
                'leverage': -1.0,  # Invalid: negative
                'max_positions': 0  # Invalid: < 1
            }
        }
        
        config_manager.update_config(updates)
        errors = config_manager.validate_config()
        
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("balance" in error.lower() for error in errors))
        self.assertTrue(any("position size" in error.lower() for error in errors))
        self.assertTrue(any("leverage" in error.lower() for error in errors))

class TestAssetManager(unittest.TestCase):
    """Test AssetManager"""
    
    def setUp(self):
        self.asset_manager = AssetManager()
    
    def test_asset_initialization(self):
        """Test asset initialization"""
        assets = self.asset_manager.get_all_assets()
        
        self.assertIn("BTCUSD", assets)
        self.assertIn("XAUUSD", assets)
        
        btc_asset = assets["BTCUSD"]
        self.assertEqual(btc_asset.symbol, "BTCUSD")
        self.assertEqual(btc_asset.balance, 100.0)
        self.assertEqual(btc_asset.equity, 100.0)
        self.assertEqual(len(btc_asset.open_positions), 0)
        self.assertEqual(len(btc_asset.closed_trades), 0)
    
    def test_add_open_position(self):
        """Test adding open positions"""
        # Add first position (50% of balance)
        trade1 = Trade(
            asset="BTCUSD",
            direction=PositionDirection.BUY.value,
            entry_price=50000.0,
            leverage=400.0
        )
        
        result = self.asset_manager.add_open_position("BTCUSD", trade1)
        self.assertTrue(result)
        
        btc_asset = self.asset_manager.get_asset_state("BTCUSD")
        self.assertEqual(len(btc_asset.open_positions), 1)
        self.assertEqual(btc_asset.open_positions[0].position_size, 50.0)  # 50% of 100
        
        # Add second position (25% of balance)
        trade2 = Trade(
            asset="BTCUSD",
            direction=PositionDirection.BUY.value,
            entry_price=51000.0,
            leverage=400.0
        )
        
        result = self.asset_manager.add_open_position("BTCUSD", trade2)
        self.assertTrue(result)
        
        self.assertEqual(len(btc_asset.open_positions), 2)
        self.assertEqual(btc_asset.open_positions[1].position_size, 25.0)  # 25% of 100
    
    def test_position_limit(self):
        """Test position limit enforcement"""
        # Add three positions (max limit)
        for i in range(3):
            trade = Trade(
                asset="BTCUSD",
                direction=PositionDirection.BUY.value,
                entry_price=50000.0 + i * 1000,
                leverage=400.0
            )
            result = self.asset_manager.add_open_position("BTCUSD", trade)
            self.assertTrue(result)
        
        # Try to add fourth position (should fail)
        trade4 = Trade(
            asset="BTCUSD",
            direction=PositionDirection.BUY.value,
            entry_price=54000.0,
            leverage=400.0
        )
        
        result = self.asset_manager.add_open_position("BTCUSD", trade4)
        self.assertFalse(result)  # Should fail due to position limit
    
    def test_close_position(self):
        """Test closing positions"""
        # Add a position
        trade = Trade(
            asset="BTCUSD",
            direction=PositionDirection.BUY.value,
            entry_price=50000.0,
            leverage=400.0
        )
        
        self.asset_manager.add_open_position("BTCUSD", trade)
        
        # Close the position
        closed_trade = self.asset_manager.close_position(
            "BTCUSD", trade.id, 52000.0, "Test close"
        )
        
        self.assertIsNotNone(closed_trade)
        self.assertEqual(closed_trade.status, TradeStatus.CLOSED.value)
        self.assertEqual(closed_trade.exit_price, 52000.0)
        self.assertEqual(closed_trade.realized_pnl, 1000.0)  # (52000 - 50000) * 50
        
        # Check that position is moved to closed trades
        btc_asset = self.asset_manager.get_asset_state("BTCUSD")
        self.assertEqual(len(btc_asset.open_positions), 0)
        self.assertEqual(len(btc_asset.closed_trades), 1)
    
    def test_floating_pnl_update(self):
        """Test floating PnL update"""
        # Add a position
        trade = Trade(
            asset="BTCUSD",
            direction=PositionDirection.BUY.value,
            entry_price=50000.0,
            leverage=400.0
        )
        
        self.asset_manager.add_open_position("BTCUSD", trade)
        
        # Update floating PnL at different prices
        self.asset_manager.update_floating_pnl("BTCUSD", 51000.0)
        self.assertEqual(trade.floating_pnl, 500.0)  # (51000 - 50000) * 50
        
        self.asset_manager.update_floating_pnl("BTCUSD", 49000.0)
        self.assertEqual(trade.floating_pnl, -500.0)  # (49000 - 50000) * 50

class TestMarketAnalyzer(unittest.TestCase):
    """Test MarketAnalyzer"""
    
    def setUp(self):
        from configuration_manager import AssetConfig
        self.asset_config = AssetConfig(
            symbol="BTCUSD",
            enabled=True,
            min_confidence=0.5,
            max_volatility="high",
            analysis_interval_minutes=15
        )
        self.market_analyzer = MarketAnalyzer(self.asset_config)
    
    def test_analyze_market(self):
        """Test market analysis"""
        analysis = self.market_analyzer.analyze_market(
            "BTCUSD", 50000.0, 49000.0, 1000000.0
        )
        
        self.assertIsInstance(analysis, MarketAnalysis)
        self.assertEqual(analysis.symbol, "BTCUSD")
        self.assertEqual(analysis.current_price, 50000.0)
        self.assertEqual(analysis.previous_price, 49000.0)
        self.assertEqual(analysis.price_change, 1000.0)
        self.assertEqual(analysis.price_change_percent, 2.04)  # (1000/49000) * 100
        
        # Check that trend is determined
        self.assertIn(analysis.trend_direction, ["bullish", "bearish", "neutral"])
        
        # Check that confidence is calculated
        self.assertGreaterEqual(analysis.confidence_score, 0.0)
        self.assertLessEqual(analysis.confidence_score, 1.0)
        
        # Check that reasoning is generated
        self.assertIsInstance(analysis.reasoning, list)
        self.assertGreater(len(analysis.reasoning), 0)
    
    def test_trend_analysis(self):
        """Test trend analysis"""
        # Add price history to influence trend
        self.market_analyzer.price_history["BTCUSD"] = [48000.0, 49000.0, 50000.0, 51000.0, 52000.0]
        
        analysis = self.market_analyzer.analyze_market(
            "BTCUSD", 52000.0, 51000.0, 1000000.0
        )
        
        # With increasing prices, trend should be bullish
        self.assertEqual(analysis.trend_direction, "bullish")
    
    def test_volatility_analysis(self):
        """Test volatility analysis"""
        # Add volatile price history
        self.market_analyzer.price_history["BTCUSD"] = [48000.0, 52000.0, 47000.0, 53000.0, 46000.0]
        
        analysis = self.market_analyzer.analyze_market(
            "BTCUSD", 46000.0, 53000.0, 1000000.0
        )
        
        # With high volatility, should be "high"
        self.assertEqual(analysis.volatility_score, "high")

class TestSignalEngine(unittest.TestCase):
    """Test SignalEngine"""
    
    def setUp(self):
        self.asset_manager = AssetManager()
        from configuration_manager import TradingConfig
        self.trading_config = TradingConfig()
        self.signal_engine = SignalEngine(self.asset_manager, self.trading_config)
    
    def test_determine_decision(self):
        """Test decision determination"""
        from market_analyzer import MarketAnalysis, TrendDirection
        
        # Create a bullish market analysis
        market_analysis = MarketAnalysis(
            symbol="BTCUSD",
            timestamp=datetime.now(timezone.utc),
            current_price=50000.0,
            previous_price=49000.0,
            price_change=1000.0,
            price_change_percent=2.04,
            trend_direction=TrendDirection.BULLISH.value,
            momentum_score=0.8,
            sentiment_score=0.7,
            volatility_score="medium",
            confidence_score=0.9,
            market_pressure=0.5,
            strength_score=0.8,
            trend_quality="Strong",
            market_phase="Strong Bullish",
            reasoning=["Bullish trend", "Strong momentum"]
        )
        
        decision = self.signal_engine._determine_decision(market_analysis)
        self.assertEqual(decision, SignalDecision.STRONG_BUY)
        
        # Test bearish decision
        market_analysis.trend_direction = TrendDirection.BEARISH.value
        market_analysis.momentum_score = 0.8
        market_analysis.sentiment_score = -0.7
        market_analysis.confidence_score = 0.9
        
        decision = self.signal_engine._determine_decision(market_analysis)
        self.assertEqual(decision, SignalDecision.SELL)
    
    def test_handle_buy_signal(self):
        """Test handling BUY signal"""
        # Add a position
        trade = Trade(
            asset="BTCUSD",
            direction=PositionDirection.BUY.value,
            entry_price=50000.0,
            leverage=400.0
        )
        
        self.asset_manager.add_open_position("BTCUSD", trade)
        
        # Handle BUY signal
        action_taken, new_positions, closed_positions = self.signal_engine._handle_buy_signal(
            "BTCUSD", [trade], 51000.0, []
        )
        
        self.assertIn("Opened new position", action_taken)
        self.assertEqual(len(new_positions), 1)
        self.assertEqual(len(closed_positions), 0)
    
    def test_handle_sell_signal(self):
        """Test handling SELL signal"""
        # Add a BUY position
        trade = Trade(
            asset="BTCUSD",
            direction=PositionDirection.BUY.value,
            entry_price=50000.0,
            leverage=400.0
        )
        
        self.asset_manager.add_open_position("BTCUSD", trade)
        
        # Handle SELL signal
        action_taken, new_positions, closed_positions = self.signal_engine._handle_sell_signal(
            "BTCUSD", [trade], 49000.0, []
        )
        
        self.assertIn("Closed", action_taken)
        self.assertEqual(len(closed_positions), 1)
        self.assertEqual(len(new_positions), 0)

class TestPortfolioManager(unittest.TestCase):
    """Test PortfolioManager"""
    
    def setUp(self):
        self.asset_manager = AssetManager()
        from configuration_manager import PortfolioConfig, TradingConfig
        self.portfolio_config = PortfolioConfig()
        self.trading_config = TradingConfig()
        self.portfolio_manager = PortfolioManager(self.asset_manager, self.portfolio_config, self.trading_config)
    
    def test_update_portfolio(self):
        """Test portfolio update"""
        # Add some trades
        trade1 = Trade(
            asset="BTCUSD",
            direction=PositionDirection.BUY.value,
            entry_price=50000.0,
            leverage=400.0
        )
        
        self.asset_manager.add_open_position("BTCUSD", trade1)
        
        # Update portfolio metrics
        metrics = self.portfolio_manager.update_portfolio()
        
        self.assertIsNotNone(metrics)
        self.assertEqual(metrics.total_balance, 100.0)
        self.assertEqual(metrics.total_equity, 100.0)
        self.assertEqual(metrics.total_floating_pnl, 0.0)
        self.assertEqual(metrics.total_realized_pnl, 0.0)
        
        # Update floating PnL
        self.asset_manager.update_floating_pnl("BTCUSD", 51000.0)
        
        # Update portfolio again
        metrics = self.portfolio_manager.update_portfolio()
        self.assertEqual(metrics.total_floating_pnl, 500.0)  # (51000 - 50000) * 50
    
    def test_performance_calculations(self):
        """Test performance calculations"""
        # Add some closed trades
        trade1 = Trade(
            asset="BTCUSD",
            direction=PositionDirection.BUY.value,
            entry_price=50000.0,
            leverage=400.0
        )
        trade1.status = TradeStatus.CLOSED.value
        trade1.realized_pnl = 1000.0
        trade1.trade_duration = 24
        
        trade2 = Trade(
            asset="BTCUSD",
            direction=PositionDirection.BUY.value,
            entry_price=51000.0,
            leverage=400.0
        )
        trade2.status = TradeStatus.CLOSED.value
        trade2.realized_pnl = -500.0
        trade2.trade_duration = 48
        
        # Add to asset manager
        self.asset_manager.add_open_position("BTCUSD", trade1)
        self.asset_manager.close_position("BTCUSD", trade1.id, 52000.0, "Test")
        self.asset_manager.add_open_position("BTCUSD", trade2)
        self.asset_manager.close_position("BTCUSD", trade2.id, 50500.0, "Test")
        
        # Update portfolio
        metrics = self.portfolio_manager.update_portfolio()
        
        # Check calculations
        self.assertEqual(metrics.total_trades, 2)
        self.assertEqual(metrics.winning_trades, 1)
        self.assertEqual(metrics.losing_trades, 1)
        self.assertEqual(metrics.win_rate, 50.0)  # 1/2 * 100
        self.assertEqual(metrics.total_realized_pnl, 500.0)  # 1000 - 500
        self.assertEqual(metrics.profit_factor, 2.0)  # 1000 / 500

class TestRiskManager(unittest.TestCase):
    """Test RiskManager"""
    
    def setUp(self):
        self.asset_manager = AssetManager()
        from configuration_manager import PortfolioConfig, TradingConfig
        self.portfolio_config = PortfolioConfig()
        self.trading_config = TradingConfig()
        self.risk_manager = RiskManager(self.asset_manager, self.portfolio_config, self.trading_config)
        self.risk_manager.initialize_risk_limits()
    
    def test_risk_metrics_calculation(self):
        """Test risk metrics calculation"""
        # Add some positions
        trade1 = Trade(
            asset="BTCUSD",
            direction=PositionDirection.BUY.value,
            entry_price=50000.0,
            leverage=400.0
        )
        
        self.asset_manager.add_open_position("BTCUSD", trade1)
        
        # Calculate risk metrics
        risk_metrics = self.risk_manager.calculate_risk_metrics()
        
        self.assertIsNotNone(risk_metrics)
        self.assertIn('portfolio_risk_score', risk_metrics)
        self.assertIn('total_exposure', risk_metrics)
        self.assertIn('exposure_ratio', risk_metrics)
        self.assertIn('max_single_position', risk_metrics)
        self.assertIn('concentration_risk', risk_metrics)
        
        # Check that exposure is calculated
        self.assertEqual(risk_metrics['total_exposure'], 50.0)  # 50% of balance
        self.assertEqual(risk_metrics['exposure_ratio'], 0.5)  # 50% of balance
    
    def test_risk_limit_breaches(self):
        """Test risk limit breaches"""
        # Add a large position (exceeds 50% limit)
        trade = Trade(
            asset="BTCUSD",
            direction=PositionDirection.BUY.value,
            entry_price=50000.0,
            leverage=400.0
        )
        
        # Manually set position size to exceed limit
        trade.position_size = 60.0  # 60% of balance
        
        self.asset_manager.add_open_position("BTCUSD", trade)
        
        # Check risk limits
        alerts = self.risk_manager.check_risk_limits("BTCUSD")
        
        # Should have position size limit breach
        position_alerts = [a for a in alerts if a.type == "POSITION_SIZE_LIMIT"]
        self.assertGreater(len(position_alerts), 0)

class TestTradeStorage(unittest.TestCase):
    """Test TradeStorage"""
    
    def setUp(self):
        from configuration_manager import SystemConfig
        self.system_config = SystemConfig(
            data_directory=tempfile.mkdtemp(),
            backup_enabled=False
        )
        self.trade_storage = TradeStorage(self.system_config, StorageType.JSON)
    
    def tearDown(self):
        import shutil
        if os.path.exists(self.system_config.data_directory):
            shutil.rmtree(self.system_config.data_directory)
    
    def test_save_and_load_trades(self):
        """Test saving and loading trades"""
        # Create a trade
        trade = Trade(
            asset="BTCUSD",
            direction=PositionDirection.BUY.value,
            entry_price=50000.0,
            leverage=400.0
        )
        
        # Save trade
        result = self.trade_storage.save_trade(trade)
        self.assertTrue(result)
        
        # Load trades
        loaded_trades = self.trade_storage.get_trades("BTCUSD")
        
        self.assertEqual(len(loaded_trades), 1)
        self.assertEqual(loaded_trades[0].asset, "BTCUSD")
        self.assertEqual(loaded_trades[0].direction, PositionDirection.BUY.value)
        self.assertEqual(loaded_trades[0].entry_price, 50000.0)
    
    def test_save_and_load_portfolio_stats(self):
        """Test saving and loading portfolio stats"""
        # Create stats
        stats = {
            'total_balance': 100.0,
            'total_equity': 105.0,
            'total_floating_pnl': 500.0,
            'total_realized_pnl': 1000.0,
            'net_pnl': 1500.0,
            'win_rate': 60.0,
            'profit_factor': 2.5,
            'total_trades': 10,
            'winning_trades': 6,
            'losing_trades': 4,
            'max_drawdown': 0.15,
            'recovery_factor': 1.5
        }
        
        # Save stats
        result = self.trade_storage.save_portfolio_stats(stats)
        self.assertTrue(result)
        
        # Load stats
        loaded_stats = self.trade_storage.get_portfolio_stats()
        
        self.assertEqual(len(loaded_stats), 1)
        self.assertEqual(loaded_stats[0]['total_balance'], 100.0)
        self.assertEqual(loaded_stats[0]['total_equity'], 105.0)
        self.assertEqual(loaded_stats[0]['net_pnl'], 1500.0)

class TestPerformanceTracker(unittest.TestCase):
    """Test PerformanceTracker"""
    
    def setUp(self):
        self.asset_manager = AssetManager()
        from configuration_manager import PortfolioConfig
        self.portfolio_config = PortfolioConfig()
        self.performance_tracker = PerformanceTracker(self.asset_manager, self.portfolio_config)
    
    def test_track_performance(self):
        """Test performance tracking"""
        # Add some trades
        trade1 = Trade(
            asset="BTCUSD",
            direction=PositionDirection.BUY.value,
            entry_price=50000.0,
            leverage=400.0
        )
        trade1.status = TradeStatus.CLOSED.value
        trade1.realized_pnl = 1000.0
        trade1.trade_duration = 24
        
        trade2 = Trade(
            asset="BTCUSD",
            direction=PositionDirection.BUY.value,
            entry_price=51000.0,
            leverage=400.0
        )
        trade2.status = TradeStatus.CLOSED.value
        trade2.realized_pnl = -500.0
        trade2.trade_duration = 48
        
        # Add to asset manager
        self.asset_manager.add_open_position("BTCUSD", trade1)
        self.asset_manager.close_position("BTCUSD", trade1.id, 52000.0, "Test")
        self.asset_manager.add_open_position("BTCUSD", trade2)
        self.asset_manager.close_position("BTCUSD", trade2.id, 50500.0, "Test")
        
        # Track performance
        performance = self.performance_tracker.track_performance("BTCUSD")
        
        self.assertIsNotNone(performance)
        self.assertEqual(performance['symbol'], "BTCUSD")
        self.assertEqual(performance['total_trades'], 2)
        self.assertEqual(performance['metrics']['total_trades'], 2)
        self.assertEqual(performance['metrics']['winning_trades'], 1)
        self.assertEqual(performance['metrics']['losing_trades'], 1)
        self.assertEqual(performance['metrics']['win_rate'], 50.0)
        self.assertEqual(performance['metrics']['total_realized_pnl'], 500.0)
    
    def test_performance_report(self):
        """Test performance report generation"""
        # Add some trades
        trade1 = Trade(
            asset="BTCUSD",
            direction=PositionDirection.BUY.value,
            entry_price=50000.0,
            leverage=400.0
        )
        trade1.status = TradeStatus.CLOSED.value
        trade1.realized_pnl = 1000.0
        trade1.trade_duration = 24
        
        self.asset_manager.add_open_position("BTCUSD", trade1)
        self.asset_manager.close_position("BTCUSD", trade1.id, 52000.0, "Test")
        
        # Get performance report
        report = self.performance_tracker.get_performance_report("BTCUSD", 30)
        
        self.assertIsNotNone(report)
        self.assertEqual(report['symbol'], "BTCUSD")
        self.assertIn('current_performance', report)
        self.assertIn('historical_performance', report)
        self.assertEqual(report['period_days'], 30)

class TestTelegramFormatter(unittest.TestCase):
    """Test TelegramFormatter"""
    
    def setUp(self):
        self.asset_manager = AssetManager()
        from configuration_manager import PortfolioConfig, TradingConfig, SystemConfig
        self.portfolio_config = PortfolioConfig()
        self.trading_config = TradingConfig()
        self.system_config = SystemConfig()
        
        self.portfolio_manager = PortfolioManager(self.asset_manager, self.portfolio_config, self.trading_config)
        self.telegram_formatter = TelegramFormatter(self.asset_manager, self.portfolio_manager, self.system_config)
    
    def test_format_signal_report(self):
        """Test signal report formatting"""
        from market_analyzer import MarketAnalysis, TrendDirection
        
        # Create a signal result
        market_analysis = MarketAnalysis(
            symbol="BTCUSD",
            timestamp=datetime.now(timezone.utc),
            current_price=50000.0,
            previous_price=49000.0,
            price_change=1000.0,
            price_change_percent=2.04,
            trend_direction=TrendDirection.BULLISH.value,
            momentum_score=0.8,
            sentiment_score=0.7,
            volatility_score="medium",
            confidence_score=0.9,
            market_pressure=0.5,
            strength_score=0.8,
            trend_quality="Strong",
            market_phase="Strong Bullish",
            reasoning=["Bullish trend", "Strong momentum"]
        )
        
        from signal_engine import SignalResult
        signal_result = SignalResult(
            symbol="BTCUSD",
            timestamp=datetime.now(timezone.utc),
            decision="BUY",
            confidence=0.9,
            market_analysis=market_analysis,
            reasoning=["Bullish trend", "Strong momentum"],
            action_taken="Opened new position",
            positions_opened=1,
            positions_closed=0,
            new_positions=[],
            closed_positions=[]
        )
        
        # Format report
        report = self.telegram_formatter.format_signal_report(signal_result)
        
        self.assertIsInstance(report, str)
        self.assertIn("AI TRADING INTELLIGENCE BOT", report)
        self.assertIn("BTCUSD", report)
        self.assertIn("BUY", report)
        self.assertIn("Market Analysis", report)
        self.assertIn("Position Management", report)
        self.assertIn("Trade Performance", report)
    
    def test_format_portfolio_report(self):
        """Test portfolio report formatting"""
        # Format portfolio report
        report = self.telegram_formatter.format_portfolio_report()
        
        self.assertIsInstance(report, str)
        self.assertIn("AI TRADING INTELLIGENCE BOT", report)
        self.assertIn("PORTFOLIO", report)
        self.assertIn("Portfolio Summary", report)
    
    def test_format_daily_report(self):
        """Test daily report formatting"""
        # Format daily report
        report = self.telegram_formatter.format_daily_report()
        
        self.assertIsInstance(report, str)
        self.assertIn("AI TRADING INTELLIGENCE BOT", report)
        self.assertIn("DAILY", report)
        self.assertIn("Daily Performance", report)

class TestMainApplication(unittest.TestCase):
    """Test main application"""
    
    def test_app_initialization(self):
        """Test application initialization"""
        from main import AITradingIntelligenceBot
        
        # Create bot
        bot = AITradingIntelligenceBot()
        
        # Check that components are initialized
        self.assertIsNotNone(bot.asset_manager)
        self.assertIsNotNone(bot.market_analyzers)
        self.assertIsNotNone(bot.signal_engine)
        self.assertIsNotNone(bot.trade_manager)
        self.assertIsNotNone(bot.portfolio_manager)
        self.assertIsNotNone(bot.profit_calculator)
        self.assertIsNotNone(bot.risk_manager)
        self.assertIsNotNone(bot.trade_storage)
        self.assertIsNotNone(bot.performance_tracker)
        self.assertIsNotNone(bot.telegram_formatter)
        
        # Check that assets are initialized
        self.assertIn("BTCUSD", bot.asset_manager.get_all_assets())
        self.assertIn("XAUUSD", bot.asset_manager.get_all_assets())
        
        # Check that market analyzers are initialized
        self.assertIn("BTCUSD", bot.market_analyzers)
        self.assertIn("XAUUSD", bot.market_analyzers)
    
    def test_get_status(self):
        """Test status retrieval"""
        from main import AITradingIntelligenceBot
        
        # Create bot
        bot = AITradingIntelligenceBot()
        
        # Get status
        status = bot.get_status()
        
        self.assertIsInstance(status, dict)
        self.assertIn('timestamp', status)
        self.assertIn('assets', status)
        self.assertIn('portfolio', status)
        self.assertIn('risk', status)
        self.assertIn('performance', status)
        
        # Check assets
        self.assertIn("BTCUSD", status['assets'])
        self.assertIn("XAUUSD", status['assets'])
        
        # Check portfolio
        self.assertIn('total_balance', status['portfolio'])
        self.assertIn('total_equity', status['portfolio'])
        self.assertIn('net_pnl', status['portfolio'])
        
        # Check risk
        self.assertIn('risk_score', status['risk'])
        self.assertIn('exposure_ratio', status['risk'])
        self.assertIn('max_drawdown', status['risk'])

if __name__ == '__main__':
    unittest.main()
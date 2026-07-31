"""
Demonstration of AI Trading Intelligence Bot v2.0
Shows the system working with both BTCUSD and XAUUSD assets.
"""

import time
from datetime import datetime, timezone
from main import AITradingIntelligenceBot

def main():
    """Run demonstration"""
    print("🧠 AI Trading Intelligence Bot v2.0 - Demonstration")
    print("=" * 60)
    
    # Create bot instance
    bot = AITradingIntelligenceBot()
    
    print("\n✅ System initialized successfully!")
    print(f"📊 Assets being monitored: {list(bot.asset_manager.get_all_assets().keys())}")
    
    # Show initial status
    status = bot.get_status()
    print(f"\n📈 Initial Portfolio Status:")
    print(f"   Account Balance: ${status['portfolio']['total_balance']:.2f}")
    print(f"   Current Equity: ${status['portfolio']['total_equity']:.2f}")
    print(f"   Net PnL: ${status['portfolio']['net_pnl']:.2f}")
    print(f"   Win Rate: {status['portfolio']['win_rate']:.1f}%")
    
    # Show asset-specific status
    print(f"\n💰 Asset Status:")
    for symbol, asset_status in status['assets'].items():
        print(f"   {symbol}:")
        print(f"     Balance: ${asset_status['balance']:.2f}")
        print(f"     Equity: ${asset_status['equity']:.2f}")
        print(f"     Open Positions: {asset_status['open_positions']}")
        print(f"     Closed Trades: {asset_status['closed_trades']}")
    
    # Show risk status
    print(f"\n⚠️  Risk Status:")
    print(f"   Risk Score: {status['risk']['risk_score']:.2f}")
    print(f"   Exposure Ratio: {status['risk']['exposure_ratio']:.2%}")
    print(f"   Max Drawdown: {status['risk']['max_drawdown']:.2%}")
    
    # Show performance status
    print(f"\n📊 Performance Status:")
    print(f"   Total Trades: {status['performance']['current_performance']['total_trades']}")
    print(f"   Winning Trades: {status['performance']['current_performance']['winning_trades']}")
    print(f"   Losing Trades: {status['performance']['current_performance']['losing_trades']}")
    print(f"   Win Rate: {status['performance']['current_performance']['win_rate']:.1f}%")
    
    # Demonstrate signal generation
    print(f"\n🔄 Demonstrating Signal Generation...")
    
    # Simulate a scan cycle
    bot.run_scan()
    
    # Show updated status
    status = bot.get_status()
    print(f"\n📈 Updated Portfolio Status:")
    print(f"   Account Balance: ${status['portfolio']['total_balance']:.2f}")
    print(f"   Current Equity: ${status['portfolio']['total_equity']:.2f}")
    print(f"   Net PnL: ${status['portfolio']['net_pnl']:.2f}")
    print(f"   Win Rate: {status['portfolio']['win_rate']:.1f}%")
    
    # Demonstrate report generation
    print(f"\n📄 Demonstrating Report Generation...")
    
    # Generate a sample signal report
    from market_analyzer import MarketAnalysis, TrendDirection
    from signal_engine import SignalResult
    
    # Create a sample market analysis for BTCUSD
    btc_market_analysis = MarketAnalysis(
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
        reasoning=["Bullish trend detected", "Strong momentum", "Positive sentiment"]
    )
    
    # Create a sample signal result
    btc_signal_result = SignalResult(
        symbol="BTCUSD",
        timestamp=datetime.now(timezone.utc),
        decision="BUY",
        confidence=0.9,
        market_analysis=btc_market_analysis,
        reasoning=["Bullish trend detected", "Strong momentum", "Positive sentiment"],
        action_taken="Opened new position",
        positions_opened=1,
        positions_closed=0,
        new_positions=[],
        closed_positions=[]
    )
    
    # Format signal report
    signal_report = bot.telegram_formatter.format_signal_report(btc_signal_result)
    print(f"\n📊 Sample Signal Report (BTCUSD):")
    print(signal_report[:500] + "..." if len(signal_report) > 500 else signal_report)
    
    # Generate portfolio report
    portfolio_report = bot.telegram_formatter.format_portfolio_report()
    print(f"\n📈 Sample Portfolio Report:")
    print(portfolio_report[:500] + "..." if len(portfolio_report) > 500 else portfolio_report)
    
    # Demonstrate performance tracking
    print(f"\n📊 Demonstrating Performance Tracking...")
    
    # Track performance
    performance_data = bot.performance_tracker.track_performance()
    print(f"   Performance tracked for {len(performance_data)} assets")
    
    # Show performance report
    performance_report = bot.performance_tracker.get_performance_report()
    print(f"   Performance report generated with {performance_report['total_trades']} trades")
    
    # Demonstrate risk management
    print(f"\n⚠️  Demonstrating Risk Management...")
    
    # Calculate risk metrics
    risk_metrics = bot.risk_manager.calculate_risk_metrics()
    print(f"   Risk metrics calculated:")
    print(f"     Risk Score: {risk_metrics['portfolio_risk_score']:.2f}")
    print(f"     Exposure Ratio: {risk_metrics['exposure_ratio']:.2%}")
    print(f"     Max Drawdown: {risk_metrics['max_drawdown']:.2%}")
    
    # Check risk limits
    risk_alerts = bot.risk_manager.check_risk_limits()
    print(f"   Risk alerts checked: {len(risk_alerts)} alerts")
    
    # Demonstrate trade storage
    print(f"\n💾 Demonstrating Trade Storage...")
    
    # Save some data
    bot.trade_storage.backup_data()
    print(f"   Data backed up successfully")
    
    # Load data
    trades = bot.trade_storage.get_trades()
    print(f"   {len(trades)} trades loaded from storage")
    
    # Demonstrate profit calculation
    print(f"\n💰 Demonstrating Profit Calculation...")
    
    # Calculate portfolio PnL
    portfolio_pnl = bot.profit_calculator.calculate_portfolio_pnl([])
    print(f"   Portfolio PnL calculated:")
    print(f"     Total Floating PnL: ${portfolio_pnl['total_floating_pnl']:.2f}")
    print(f"     Total Realized PnL: ${portfolio_pnl['total_realized_pnl']:.2f}")
    print(f"     Net PnL: ${portfolio_pnl['net_pnl']:.2f}")
    
    print(f"\n✅ Demonstration completed successfully!")
    print(f"\n🎯 Key Features Demonstrated:")
    print(f"   • Modular architecture with independent asset state")
    print(f"   • Signal generation for BTCUSD and XAUUSD")
    print(f"   • Position management with 50%/25% allocation")
    print(f"   • Portfolio performance tracking")
    print(f"   • Risk management and exposure control")
    print(f"   • Persistent data storage")
    print(f"   • Professional report generation")
    print(f"   • Performance analytics")
    
    print(f"\n🚀 The AI Trading Intelligence Bot v2.0 is ready for production!")

if __name__ == "__main__":
    main()
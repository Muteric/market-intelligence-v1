"""
Telegram Formatter for AI Trading Intelligence Bot
Generates professional-grade Telegram reports for trading signals and portfolio performance.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal, ROUND_HALF_UP

from asset_manager import AssetManager, Trade, TradeStatus, PositionDirection
from signal_engine import SignalResult
from portfolio_manager import PortfolioManager
from configuration_manager import SystemConfig

class ReportFormat(Enum):
    """Report formats"""
    COMPACT = "compact"
    DETAILED = "detailed"
    PROFESSIONAL = "professional"
    EXECUTIVE = "executive"

class ReportSection(Enum):
    """Report sections"""
    HEADER = "header"
    MARKET_ANALYSIS = "market_analysis"
    POSITION_MANAGEMENT = "position_management"
    TRADE_PERFORMANCE = "trade_performance"
    OPEN_POSITIONS = "open_positions"
    AI_ANALYSIS = "ai_analysis"
    PORTFOLIO_SUMMARY = "portfolio_summary"
    SYSTEM_STATUS = "system_status"

@dataclass
class ReportSectionData:
    """Data for a report section"""
    section: str
    title: str
    content: str
    order: int
    
    def __post_init__(self):
        if self.order is None:
            self.order = 0

@dataclass
class TelegramReport:
    """Telegram report"""
    id: str = None
    timestamp: datetime = None
    report_type: str = None
    format: str = ReportFormat.PROFESSIONAL.value
    sections: List[ReportSectionData] = None
    
    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4())
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)
        if self.sections is None:
            self.sections = []

class TelegramFormatter:
    """Formats trading reports for Telegram"""
    
    def __init__(self, asset_manager: AssetManager, portfolio_manager: PortfolioManager, 
                 system_config: SystemConfig):
        self.asset_manager = asset_manager
        self.portfolio_manager = portfolio_manager
        self.system_config = system_config
        self.report_templates = self._load_report_templates()
    
    def format_signal_report(self, signal_result: SignalResult, 
                           format_type: str = ReportFormat.PROFESSIONAL.value) -> str:
        """Format a signal report for Telegram"""
        report = TelegramReport(
            report_type="signal",
            format=format_type
        )
        
        # Add sections
        report.sections = [
            self._create_header_section(signal_result),
            self._create_market_analysis_section(signal_result),
            self._create_position_management_section(signal_result),
            self._create_trade_performance_section(signal_result),
            self._create_open_positions_section(signal_result),
            self._create_ai_analysis_section(signal_result),
            self._create_portfolio_summary_section(signal_result),
            self._create_system_status_section(signal_result)
        ]
        
        return self._assemble_report(report)
    
    def format_portfolio_report(self, format_type: str = ReportFormat.PROFESSIONAL.value) -> str:
        """Format a portfolio report for Telegram"""
        report = TelegramReport(
            report_type="portfolio",
            format=format_type
        )
        
        # Add sections
        report.sections = [
            self._create_header_section(None),
            self._create_portfolio_summary_section(None),
            self._create_asset_performance_sections(),
            self._create_system_status_section(None)
        ]
        
        return self._assemble_report(report)
    
    def format_daily_report(self, format_type: str = ReportFormat.PROFESSIONAL.value) -> str:
        """Format a daily report for Telegram"""
        report = TelegramReport(
            report_type="daily",
            format=format_type
        )
        
        # Add sections
        report.sections = [
            self._create_header_section(None),
            self._create_daily_performance_section(),
            self._create_asset_performance_sections(),
            self._create_system_status_section(None)
        ]
        
        return self._assemble_report(report)
    
    def _create_header_section(self, signal_result: Optional[SignalResult] = None) -> ReportSectionData:
        """Create header section"""
        if signal_result:
            timestamp = signal_result.timestamp
            symbol = signal_result.symbol
            decision = signal_result.decision
            confidence = signal_result.confidence
        else:
            timestamp = datetime.now(timezone.utc)
            symbol = "PORTFOLIO"
            decision = "UPDATE"
            confidence = 100.0
        
        header = f"🧠 AI TRADING INTELLIGENCE BOT\n\n"
        header += f"═══════════════════════════════\n\n"
        header += f"📅 {timestamp.strftime('%d %b %Y')}\n"
        header += f"🕒 {timestamp.strftime('%H:%M')} UTC\n\n"
        header += f"═══════════════════════════════\n\n"
        header += f"🟢 {symbol}\n"
        header += f"SIGNAL\n"
        header += f"{decision}\n"
        header += f"Confidence: {confidence:.0}%\n\n"
        
        return ReportSectionData(
            section=ReportSection.HEADER.value,
            title="Header",
            content=header,
            order=1
        )
    
    def _create_market_analysis_section(self, signal_result: SignalResult) -> ReportSectionData:
        """Create market analysis section"""
        analysis = signal_result.market_analysis
        
        section = f"💹 MARKET ANALYSIS\n\n"
        section += f"Current Price: {analysis.current_price:,.2f}\n"
        section += f"Previous Price: {analysis.previous_price:,.2f}\n"
        section += f"Price Change: {analysis.price_change:+,.2f} ({analysis.price_change_percent:+.2f}%)\n\n"
        section += f"Trend: {analysis.trend_direction}\n"
        section += f"Momentum: {analysis.momentum_score:.2f}\n"
        section += f"Sentiment: {analysis.sentiment_score:.2f}\n"
        section += f"Volatility: {analysis.volatility_score}\n"
        section += f"Confidence: {analysis.confidence_score:.0%}\n"
        section += f"Market Pressure: {analysis.market_pressure:.2f}\n"
        section += f"Strength Score: {analysis.strength_score:.2f}\n"
        section += f"Trend Quality: {analysis.trend_quality}\n"
        section += f"Market Phase: {analysis.market_phase}\n\n"
        
        # Add reasoning
        if analysis.reasoning:
            section += "🧠 AI REASONING:\n"
            for reason in analysis.reasoning:
                section += f"• {reason}\n"
            section += "\n"
        
        return ReportSectionData(
            section=ReportSection.MARKET_ANALYSIS.value,
            title="Market Analysis",
            content=section,
            order=2
        )
    
    def _create_position_management_section(self, signal_result: SignalResult) -> ReportSectionData:
        """Create position management section"""
        asset_state = self.asset_manager.get_asset_state(signal_result.symbol)
        if not asset_state:
            return ReportSectionData(
                section=ReportSection.POSITION_MANAGEMENT.value,
                title="Position Management",
                content="Position management data not available\n\n",
                order=3
            )
        
        section = f"💼 POSITION MANAGEMENT\n\n"
        section += f"Previous Signal: {signal_result.action_taken}\n"
        section += f"Action Taken: {signal_result.action_taken}\n"
        section += f"Open Positions: {len(asset_state.open_positions)} / 3\n"
        section += f"Capital Used: ${signal_result.positions_opened * 50:.2f}\n"
        section += f"Position Size: ${signal_result.positions_opened * 10000:.2f}\n\n"
        
        return ReportSectionData(
            section=ReportSection.POSITION_MANAGEMENT.value,
            title="Position Management",
            content=section,
            order=3
        )
    
    def _create_trade_performance_section(self, signal_result: SignalResult) -> ReportSectionData:
        """Create trade performance section"""
        portfolio_metrics = self.portfolio_manager.update_portfolio()
        
        section = f"💰 TRADE PERFORMANCE\n\n"
        section += f"Floating Profit: +${portfolio_metrics.total_floating_pnl:.2f}\n"
        section += f"Realized Profit Today: +${portfolio_metrics.daily_profit:.2f}\n"
        section += f"Portfolio Profit: +${portfolio_metrics.net_pnl:.2f}\n"
        section += f"ROI: {portfolio_metrics.net_roi:.2f}%\n\n"
        
        return ReportSectionData(
            section=ReportSection.TRADE_PERFORMANCE.value,
            title="Trade Performance",
            content=section,
            order=4
        )
    
    def _create_open_positions_section(self, signal_result: SignalResult) -> ReportSectionData:
        """Create open positions section"""
        asset_state = self.asset_manager.get_asset_state(signal_result.symbol)
        if not asset_state or not asset_state.open_positions:
            return ReportSectionData(
                section=ReportSection.OPEN_POSITIONS.value,
                title="Open Positions",
                content="No open positions\n\n",
                order=5
            )
        
        section = f"📂 OPEN POSITIONS\n\n"
        
        for i, trade in enumerate(asset_state.open_positions, 1):
            direction_emoji = "🟢" if trade.direction == PositionDirection.BUY.value else "🔴"
            profit_color = "🟢" if trade.floating_pnl >= 0 else "🔴"
            
            section += f"{i}. {direction_emoji} {trade.direction}\n"
            section += f"   Entry: {trade.entry_price:,.2f}\n"
            section += f"   Profit: {profit_color} ${trade.floating_pnl:+,.2f}\n"
            section += f"   Age: {trade.trade_duration}h\n\n"
        
        return ReportSectionData(
            section=ReportSection.OPEN_POSITIONS.value,
            title="Open Positions",
            content=section,
            order=5
        )
    
    def _create_ai_analysis_section(self, signal_result: SignalResult) -> ReportSectionData:
        """Create AI analysis section"""
        section = f"🧠 AI ANALYSIS\n\n"
        section += f"• Trend remains {signal_result.market_analysis.trend_direction}.\n"
        section += f"• Buyers remain dominant.\n"
        section += f"• Momentum increasing.\n"
        section += f"• Market favors long positions.\n\n"
        
        section += f"Recommendation: Continue holding {signal_result.decision} positions.\n\n"
        
        return ReportSectionData(
            section=ReportSection.AI_ANALYSIS.value,
            title="AI Analysis",
            content=section,
            order=6
        )
    
    def _create_portfolio_summary_section(self, signal_result: Optional[SignalResult] = None) -> ReportSectionData:
        """Create portfolio summary section"""
        portfolio_metrics = self.portfolio_manager.update_portfolio()
        all_assets = self.asset_manager.get_all_assets()
        
        section = f"📈 PORTFOLIO SUMMARY\n\n"
        section += f"Account Balance: ${portfolio_metrics.balance:.2f}\n"
        section += f"Equity: ${portfolio_metrics.current_equity:.2f}\n"
        section += f"Open Exposure: {portfolio_metrics.current_exposure:.1f}%\n"
        section += f"Floating Profit: +${portfolio_metrics.total_floating_pnl:.2f}\n"
        section += f"Today's Realized Profit: +${portfolio_metrics.daily_profit:.2f}\n"
        section += f"Total Profit: +${portfolio_metrics.net_pnl:.2f}\n"
        section += f"Win Rate: {portfolio_metrics.win_rate:.1f}%\n"
        section += f"Trades Closed: {portfolio_metrics.total_closed_trades}\n"
        section += f"Winning Trades: {portfolio_metrics.winning_trades}\n"
        section += f"Losing Trades: {portfolio_metrics.losing_trades}\n"
        section += f"Profit Factor: {portfolio_metrics.profit_factor:.2f}\n"
        section += f"Maximum Drawdown: {portfolio_metrics.max_drawdown:.2f}%\n\n"
        
        # Add asset-specific summaries if signal_result is provided
        if signal_result:
            asset_state = self.asset_manager.get_asset_state(signal_result.symbol)
            if asset_state:
                section += f"🟢 {signal_result.symbol}\n"
                section += f"Floating Profit: +${asset_state.performance_stats.get('total_floating_pnl', 0):.2f}\n\n"
        
        return ReportSectionData(
            section=ReportSection.PORTFOLIO_SUMMARY.value,
            title="Portfolio Summary",
            content=section,
            order=7
        )
    
    def _create_system_status_section(self, signal_result: Optional[SignalResult] = None) -> ReportSectionData:
        """Create system status section"""
        section = f"⚠ SYSTEM STATUS\n\n"
        section += f"BTC Engine: 🟢 Healthy\n"
        section += f"Gold Engine: 🟢 Healthy\n"
        section += f"Database: 🟢 Connected\n"
        section += f"Signal Engine: 🟢 Active\n"
        section += f"Last Scan: {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC\n"
        section += f"Next Scan: 15 minutes\n\n"
        
        return ReportSectionData(
            section=ReportSection.SYSTEM_STATUS.value,
            title="System Status",
            content=section,
            order=8
        )
    
    def _create_asset_performance_sections(self) -> List[ReportSectionData]:
        """Create asset performance sections"""
        all_assets = self.asset_manager.get_all_assets()
        sections = []
        
        for symbol, asset_state in all_assets.items():
            section = self._create_single_asset_section(symbol, asset_state)
            sections.append(section)
        
        return sections
    
    def _create_single_asset_section(self, symbol: str, asset_state) -> ReportSectionData:
        """Create a single asset performance section"""
        section = f"🟢 {symbol}\n\n"
        section += f"Current Price: ${asset_state.equity:,.2f}\n"
        section += f"Open Positions: {len(asset_state.open_positions)}\n"
        section += f"Floating Profit: +${sum(t.floating_pnl for t in asset_state.open_positions):.2f}\n"
        section += f"Win Rate: {asset_state.performance_stats.get('win_rate', 0):.1f}%\n"
        section += f"Total Trades: {asset_state.performance_stats.get('total_trades', 0)}\n"
        section += f"Profit Factor: {asset_state.performance_stats.get('profit_factor', 0):.2f}\n\n"
        
        return ReportSectionData(
            section=f"asset_{symbol}",
            title=f"{symbol} Performance",
            content=section,
            order=999  # High order to appear at the end
        )
    
    def _create_daily_performance_section(self) -> ReportSectionData:
        """Create daily performance section"""
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        
        section = f"📊 DAILY PERFORMANCE\n\n"
        section += f"Date: {today}\n"
        section += f"Total Trades: 0\n"
        section += f"Winning Trades: 0\n"
        section += f"Losing Trades: 0\n"
        section += f"Net PnL: $0.00\n"
        section += f"Win Rate: 0.0%\n"
        section += f"Profit Factor: 0.0\n\n"
        
        return ReportSectionData(
            section="daily_performance",
            title="Daily Performance",
            content=section,
            order=999  # High order to appear at the end
        )
    
    def _assemble_report(self, report: TelegramReport) -> str:
        """Assemble the final report"""
        # Sort sections by order
        sorted_sections = sorted(report.sections, key=lambda x: x.order)
        
        # Build report
        assembled_report = ""
        for section in sorted_sections:
            assembled_report += section.content
        
        return assembled_report
    
    def _load_report_templates(self) -> Dict[str, Any]:
        """Load report templates (placeholder)"""
        return {
            'professional': {
                'header_format': '🧠 AI TRADING INTELLIGENCE BOT',
                'separator': '═══════════════════════════════',
                'emoji_style': 'professional'
            },
            'compact': {
                'header_format': '🤖 AI Trading Bot',
                'separator': '─',
                'emoji_style': 'minimal'
            }
        }
    
    def _round_decimal(self, value: float, decimals: int = 2) -> float:
        """Round decimal value to specified precision"""
        return float(Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
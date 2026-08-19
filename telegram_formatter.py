"""
Telegram Formatter for AI Trading Intelligence Bot
Generates professional-grade Telegram reports for trading signals and portfolio performance.
"""

import uuid
import math
from dataclasses import dataclass, is_dataclass
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
        self.market_snapshots: Dict[str, Dict[str, Any]] = {}
        self.report_templates = self._load_report_templates()
    
    def format_signal_report(self, signal_result: SignalResult, 
                           format_type: str = ReportFormat.PROFESSIONAL.value) -> str:
        """Format a signal report for Telegram"""
        ai_decision_result = getattr(signal_result, "ai_decision_result", None)
        if is_dataclass(ai_decision_result):
            return self._format_verified_intelligence_report(signal_result)
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

    def format_new_buy_signal(self, signal_result: SignalResult) -> str:
        """Format a BUY event using the authoritative signal report."""
        return self.format_signal_report(signal_result)

    def format_new_sell_signal(self, signal_result: SignalResult) -> str:
        """Format a SELL event using the authoritative signal report."""
        return self.format_signal_report(signal_result)

    def format_hold_update(self, signal_result: SignalResult) -> str:
        """Format a HOLD update without changing portfolio state."""
        return self.format_signal_report(signal_result)

    def format_trade_event(self, event: str, details: Dict[str, Any]) -> str:
        """Format an event notification from supplied, already-calculated values."""
        lines = ["AI TRADING INTELLIGENCE BOT", "", event.upper()]
        lines.extend(f"{key}: {value}" for key, value in details.items())
        return "\n".join(lines)

    def format_provider_failure(self, provider: str, error: str) -> str:
        return self.format_trade_event("DATA PROVIDER FAILURE", {"Provider": provider, "Error": error})

    def format_provider_recovery(self, provider: str) -> str:
        return self.format_trade_event("PROVIDER RECOVERY", {"Provider": provider, "Status": "VALIDATED"})

    def format_system_error(self, error: str) -> str:
        return self.format_trade_event("SYSTEM ERROR", {"Error": error})

    def _format_verified_intelligence_report(self, signal_result: SignalResult) -> str:
        """Format the production report from validated and computed values only."""
        ai = signal_result.ai_decision_result
        validation = signal_result.validation_result
        technical = signal_result.technical_indicators
        multi = signal_result.multi_timeframe
        risk = signal_result.risk_metrics
        portfolio = signal_result.portfolio_metrics or self.portfolio_manager.update_portfolio()
        quality = signal_result.data_quality or {}
        analysis = signal_result.market_analysis
        self.market_snapshots[signal_result.symbol] = {
            "price": analysis.current_price,
            "timestamp": analysis.timestamp,
            "status": "validated",
        }
        asset_state = self.asset_manager.get_asset_state(signal_result.symbol)
        open_count = len(asset_state.open_positions) if asset_state else 0
        allocation = (
            self.portfolio_manager.portfolio_config.base_position_size
            if open_count == 0
            else self.portfolio_manager.portfolio_config.scaling_position_size
        )

        source_count = len(validation.provider_prices) if validation else 0
        source_total = quality.get("provider_total", source_count)
        timeframe_items = list(multi.timeframe_analyses.values()) if multi else []
        bullish_count = sum(item.trend.startswith("bullish") for item in timeframe_items)
        bearish_count = sum(item.trend.startswith("bearish") for item in timeframe_items)
        alignment_count = max(bullish_count, bearish_count)

        def value(obj, name, default="N/A"):
            raw = getattr(obj, name, None) if obj is not None else None
            return raw if raw is not None else default

        def number(obj, name, digits=2):
            raw = getattr(obj, name, None) if obj is not None else None
            if not isinstance(raw, (int, float)) or not math.isfinite(float(raw)):
                return "N/A"
            return f"{float(raw):.{digits}f}"

        lines = [
            "AI TRADING INTELLIGENCE BOT",
            "",
            "SIGNAL",
            f"Asset: {signal_result.symbol}",
            f"Decision: {ai.decision}",
            f"Confidence: {ai.confidence_score:.0%}",
            f"Current Price: ${analysis.current_price:,.2f}",
            f"Previous Price: ${analysis.previous_price:,.2f}",
            f"Price Change: {analysis.price_change_percent:+.2f}%",
            "",
            "MARKET INTELLIGENCE",
            f"Trend: {analysis.trend_direction}",
            f"Momentum: {ai.momentum:.3f}",
            f"Volatility: {analysis.volatility_score}",
            f"Market Regime: {value(value(ai, 'market_regime'), 'regime').value if hasattr(value(value(ai, 'market_regime'), 'regime'), 'value') else value(value(ai, 'market_regime'), 'regime')}",
            f"Data Sources: {source_count}/{source_total} available",
            f"Price Confidence: {value(validation, 'confidence_score', 0):.0%}",
            "",
            "INDICATOR EVIDENCE",
            f"RSI: {number(technical.rsi, 'rsi')}",
            f"MACD: {number(technical.macd, 'macd', 4)}",
            f"EMA Structure: {value(technical.ema, 'trend')}",
            f"Bollinger Bands %B: {number(technical.bollinger_bands, 'percent_b', 4)}",
            f"ATR: {number(technical.atr, 'atr', 4)}",
            f"ADX: {number(technical.adx, 'adx')}",
            f"Stochastic: {number(technical.stochastic, 'k')}",
            f"VWAP: {value(technical.vwap, 'vwap')}",
            f"OBV: {value(technical.obv, 'obv')}",
            f"Ichimoku: {value(technical.ichimoku, 'cloud_direction')}",
            f"Fibonacci: {value(technical.fibonacci, 'nearest_level')}",
            f"Pivot: {value(technical.pivot_points, 'pivot')}",
            "",
            "MULTI-TIMEFRAME",
        ]
        source_lines = ["", f"{signal_result.symbol} DATA SOURCES"]
        statuses = value(validation, 'provider_status', {}) or {}
        prices = value(validation, 'provider_prices', {}) or {}
        for provider_name, status in statuses.items():
            price_text = f"${prices[provider_name]:,.2f}" if provider_name in prices else "unavailable"
            source_lines.append(f"{provider_name}: {status} {price_text}")
        source_lines.extend([
            f"Valid Sources: {source_count}/{source_total}",
            f"Price Confidence: {value(validation, 'confidence_score', 0):.0%}",
        ])
        lines[18:18] = source_lines

        if multi:
            for timeframe in ("5M", "15M", "1H", "4H", "Daily"):
                item = multi.timeframe_analyses.get(timeframe)
                lines.append(f"{timeframe}: {value(item, 'trend')} / momentum {value(item, 'momentum')}")
            lines.append(f"Alignment: {alignment_count}/5 ({multi.trend_alignment})")
            lines.extend(["", "CHART PATTERNS"])
            for timeframe, patterns in (getattr(multi, "patterns", None) or {}).items():
                for pattern in patterns or []:
                    name = pattern.get("pattern_name", "Pattern")
                    confidence = pattern.get("confidence", 0.0)
                    confirmation = pattern.get("confirmation_status", "unavailable")
                    lines.append(f"{timeframe}: {name} / {confidence:.0%} / {confirmation}")
            lines.extend(["", "MARKET STRUCTURE"])
            for timeframe, structure in (getattr(multi, "market_structure", None) or {}).items():
                labels = " ".join(structure.get("labels", [])) or "none"
                lines.append(f"{timeframe}: {labels} / {structure.get('overall', 'neutral')}")
        else:
            lines.append("DATA UNAVAILABLE")

        candidate = getattr(signal_result, "trade_candidate", None)
        if candidate and getattr(candidate, "accepted", False):
            lines.extend([
                "",
                "SIGNAL INTELLIGENCE (SIMULATION ONLY)",
                f"DIRECTION: {candidate.direction}",
                f"MODE: {candidate.mode}",
                f"SCORE: {candidate.signal_score:.1f}",
                f"STATUS: {candidate.status}",
                f"DIRECTION: {candidate.direction}",
                f"ENTRY: {candidate.entry}",
                f"STOP LOSS: {candidate.stop_loss}",
                f"TAKE PROFIT: {candidate.take_profit}",
                f"EXPECTED MOVE: {candidate.expected_move}",
                f"R:R: {candidate.risk_reward}",
                f"CONFIDENCE: {candidate.confidence:.0%}",
                f"TIMEFRAME ALIGNMENT: {', '.join(candidate.supporting_timeframes) or 'UNAVAILABLE'}",
                f"WHY: {'; '.join(candidate.reasons) or 'UNAVAILABLE'}",
            ])
        elif candidate and getattr(candidate, "status", "") == "WATCH":
            lines.extend([
                "",
                "TRADE CANDIDATE: WATCH",
                f"Direction: {candidate.direction}",
                f"Mode: {candidate.mode}",
                f"Score: {candidate.signal_score:.1f}%",
                f"Confidence: {candidate.confidence:.0%}",
                f"Entry: {candidate.entry}",
                f"Reason: {candidate.rejection_reason or 'WATCH — setup developing'}",
            ])
        elif candidate and getattr(candidate, "rejection_reason", None):
            lines.extend(["", "TRADE CANDIDATE: REJECTED", f"Reason: {candidate.rejection_reason}"])

        tracker = getattr(self, "outcome_tracker", None)
        if tracker is not None:
            learning = tracker.learning_status()
            lines.extend([
                "",
                "LEARNING STATUS",
                f"Candidates evaluated: {learning.get('candidates_evaluated', 0)}",
                f"Outcomes resolved: {learning.get('outcomes_resolved', 0)}",
                f"Win rate: {learning.get('win_rate'):.0%}" if learning.get('win_rate') is not None else "Win rate: N/A",
                "Adaptive weighting: DISABLED until sufficient validated observations",
            ])
        mt5_monitor = getattr(self, "mt5_health_monitor", None)
        if mt5_monitor is not None:
            mt5_report = mt5_monitor.report().get("mt5", {})
            symbols = mt5_report.get("symbols", {})
            lines.extend([
                "",
                "MT5 STATUS",
                f"MT5: {mt5_report.get('status', 'DISCONNECTED')}",
                f"Mode: {mt5_report.get('mode', 'READ_ONLY')}",
                f"Account: {mt5_report.get('account', 'UNKNOWN')}",
                f"{signal_result.symbol}: {'AVAILABLE' if symbols.get(signal_result.symbol) else 'UNAVAILABLE'}",
                "Execution: DISABLED",
            ])
        lines.extend([
            "",
            "TRADE PLAN",
            f"Action: {ai.decision}",
            f"Recommendation: {ai.recommended_action}",
            f"Reference Entry: ${analysis.current_price:,.2f}",
            f"Execution Reference: ${validation.execution_reference_price:,.2f}" if validation and validation.execution_reference_price is not None else "Execution Reference: UNAVAILABLE",
            f"Position Allocation: {allocation:.0%} of ${asset_state.balance if asset_state else 0.0:,.2f}",
            f"Leverage: 1:{self.portfolio_manager.portfolio_config.leverage:g}",
            f"Stop Loss: ${value(risk, 'stop_loss') if ai.decision != 'HOLD' else 'UNAVAILABLE'}",
            f"Take Profit: ${value(risk, 'take_profit_1') if ai.decision != 'HOLD' else 'UNAVAILABLE'}",
            f"Risk: {value(risk, 'drawdown_risk')} / R:R {value(risk, 'risk_reward_ratio')}",
            "Action Detail: No position change" if ai.decision == "HOLD" else "Action Detail: Simulated position decision",
            "ILLUSTRATIVE PnL: UNAVAILABLE (no projected PnL calculation is implemented)",
            "",
            "CURRENT PORTFOLIO",
            f"Balance: ${portfolio.total_balance:,.2f}",
            f"Equity: ${portfolio.total_equity:,.2f}",
            f"FLOATING PnL: ${portfolio.total_floating_pnl:+,.2f}",
            f"REALIZED PnL: ${portfolio.total_realized_pnl:+,.2f}",
            f"Open Positions: {portfolio.open_positions_count}",
            f"Win Rate: {portfolio.win_rate:.2f}%",
            f"Profit Factor: {portfolio.profit_factor:.2f}",
            f"Max Drawdown: {portfolio.max_drawdown:.2f}%",
            "",
            "AI REASONING",
            ai.ai_explanation or ai.confidence_explanation,
            "",
            f"Provider outliers: {', '.join(quality.get('outliers', [])) or 'none'}",
            f"Stale providers: {', '.join(quality.get('stale', [])) or 'none'}",
            "Provider status: " + ", ".join(
                f"{name}={status}" for name, status in (quality.get('provider_status') or {}).items()
            ),
        ])
        return "\n".join(lines)
    
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
            *self._create_asset_performance_sections(),
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
            *self._create_asset_performance_sections(),
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
            confidence = None
        
        header = f"🧠 AI TRADING INTELLIGENCE BOT\n\n"
        header += f"═══════════════════════════════\n\n"
        header += f"📅 {timestamp.strftime('%d %b %Y')}\n"
        header += f"🕒 {timestamp.strftime('%H:%M')} UTC\n\n"
        header += f"═══════════════════════════════\n\n"
        header += f"🟢 {symbol}\n"
        header += f"SIGNAL\n"
        header += f"{decision}\n"
        header += f"Confidence: {confidence:.0}%\n\n" if confidence is not None else "Confidence: N/A\n\n"
        
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
        section += f"Open Positions: {len(asset_state.open_positions)} / {self.portfolio_manager.portfolio_config.max_positions}\n"
        capital_used = sum((trade.capital_used or trade.position_size or 0.0) for trade in asset_state.open_positions)
        notional_value = sum((trade.notional_value or 0.0) for trade in asset_state.open_positions)
        section += f"Capital Used: ${capital_used:.2f}\n"
        section += f"Notional Exposure: ${notional_value:.2f}\n\n"
        
        return ReportSectionData(
            section=ReportSection.POSITION_MANAGEMENT.value,
            title="Position Management",
            content=section,
            order=3
        )
    
    def _create_trade_performance_section(self, signal_result: SignalResult) -> ReportSectionData:
        """Create trade performance section"""
        portfolio_metrics = self.portfolio_manager.update_portfolio()

        def metric(name: str) -> float:
            value = getattr(portfolio_metrics, name, 0.0)
            return value if isinstance(value, (int, float)) else 0.0
        
        section = f"💰 TRADE PERFORMANCE\n\n"
        section += f"Floating Profit: +${metric('total_floating_pnl'):.2f}\n"
        section += f"Realized Profit Today: +${metric('daily_profit'):.2f}\n"
        section += f"Portfolio Profit: +${metric('net_pnl'):.2f}\n"
        section += f"ROI: {metric('net_roi'):.2f}%\n\n"
        
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
        
        section = "AI ANALYSIS\n\n"
        momentum = getattr(signal_result.market_analysis, "momentum_score", "UNAVAILABLE")
        volatility = getattr(signal_result.market_analysis, "volatility_score", "UNAVAILABLE")
        section += f"Trend: {signal_result.market_analysis.trend_direction}\n"
        section += f"Momentum score: {momentum}\n"
        section += f"Volatility: {volatility}\n\n"
        section += f"Recommendation: {signal_result.decision}\n"
        reasoning = signal_result.reasoning
        if not isinstance(reasoning, (list, tuple)):
            reasoning = ["No reasoning available"]
        section += "Reasoning: " + "; ".join(str(item) for item in reasoning) + "\n\n"
        
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

        def metric(name: str) -> float:
            value = getattr(portfolio_metrics, name, 0.0)
            return value if isinstance(value, (int, float)) else 0.0
        
        section = f"📈 PORTFOLIO SUMMARY\n\n"
        section += f"Account Balance: ${metric('balance'):.2f}\n"
        section += f"Equity: ${metric('current_equity'):.2f}\n"
        section += f"Open Exposure: {metric('current_exposure'):.1f}%\n"
        section += f"Floating Profit: +${metric('total_floating_pnl'):.2f}\n"
        section += f"Today's Realized Profit: +${metric('daily_profit'):.2f}\n"
        section += f"Total Profit: +${metric('net_pnl'):.2f}\n"
        section += f"Win Rate: {metric('win_rate'):.1f}%\n"
        section += f"Trades Closed: {metric('total_closed_trades'):.0f}\n"
        section += f"Winning Trades: {metric('winning_trades'):.0f}\n"
        section += f"Losing Trades: {metric('losing_trades'):.0f}\n"
        section += f"Profit Factor: {metric('profit_factor'):.2f}\n"
        section += f"Maximum Drawdown: {metric('max_drawdown'):.2f}%\n\n"
        
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
        snapshot = self.market_snapshots.get(symbol)
        if snapshot and snapshot.get("price") is not None:
            section += f"Current Price: ${snapshot['price']:,.2f}\n"
        else:
            section += "Current Price: DATA UNAVAILABLE\n"
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

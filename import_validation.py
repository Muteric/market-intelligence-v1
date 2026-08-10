"""Fail-fast validation for the bot's public module and class contracts."""

import importlib


REQUIRED = {
    "main": ["AITradingIntelligenceBot"],
    "ai_decision_engine": ["AIDecisionEngine"],
    "asset_manager": ["AssetManager", "Trade"],
    "market_analyzer": ["MarketAnalyzer"],
    "signal_engine": ["SignalEngine"],
    "trade_manager": ["TradeManager"],
    "portfolio_manager": ["PortfolioManager"],
    "performance_tracker": ["PerformanceTracker"],
    "trade_storage": ["TradeStorage"],
    "configuration_manager": ["ConfigurationManager"],
    "risk_manager": ["RiskManager"],
    "telegram_formatter": ["TelegramFormatter"],
    "market_regime_detector": ["MarketRegimeDetector"],
    "risk_calculator": ["RiskCalculator"],
}


def validate() -> None:
    failures = []
    for module_name, names in REQUIRED.items():
        try:
            module = importlib.import_module(module_name)
        except Exception as exc:
            failures.append(f"{module_name}: module import failed: {exc}")
            continue
        for name in names:
            if not hasattr(module, name):
                failures.append(f"{module_name}: missing {name}")
    if failures:
        raise RuntimeError("IMPORT VALIDATION FAILED\n" + "\n".join(failures))
    print("IMPORT VALIDATION PASSED")


if __name__ == "__main__":
    validate()

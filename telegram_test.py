"""Safe production-path Telegram verification; never executes positions."""

import logging
import os

from main import AITradingIntelligenceBot


logger = logging.getLogger(__name__)


def main() -> int:
    bot = AITradingIntelligenceBot()
    token = bot.config.system.telegram_token or os.getenv("TELEGRAM_TOKEN", "")
    if not token:
        logger.error("Telegram test cannot run: TELEGRAM_TOKEN is unavailable")
        return 2

    reports = bot.run_scan(execute_trades=False)
    if not reports:
        logger.error("Telegram test failed: no report was constructed")
        return 1
    if bot.telegram_delivery_failures:
        logger.error("Telegram test failed: %d delivery attempt(s) failed", bot.telegram_delivery_failures)
        return 1
    logger.info("Telegram test constructed %d report(s) without modifying positions", len(reports))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

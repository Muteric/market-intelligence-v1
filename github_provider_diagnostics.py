
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Any

from configuration_manager import SystemConfig
from market_data_aggregator import MarketDataAggregator, MarketDataPoint


PROVIDERS = {
    "BTCUSD": ["binance", "coingecko", "twelvedata", "alphavantage", "yahoo_finance"],
    "XAUUSD": [
        "goldapi",
        "goldprice_dev",
        "itick",
        "twelvedata",
        "alphavantage",
        "yahoo_finance",
        "mt5",
    ],
}
SECRET_NAMES = (
    "ALPHAVANTAGE_API_KEY",
    "COIN_GECKO_API",
    "GOLD_API",
    "ITICK_API_KEY",
    "TELEGRAM_TOKEN",
    "TWELVEDATA_API_KEY",
)


def _fmt_timestamp(value: Any) -> str:
    if not isinstance(value, datetime):
        return "N/A"
    return value.isoformat()


def _secret_status() -> str:
    return "\n".join(
        f"{name}: {'CONFIGURED' if os.getenv(name) else 'NOT CONFIGURED'}"
        for name in SECRET_NAMES
    )


def _safe_error(error: Exception) -> str:
    text = str(error)
    for name in SECRET_NAMES:
        secret = os.getenv(name)
        if secret:
            text = text.replace(secret, "[REDACTED]")
    return text[:240]


def _provider_status(aggregator: MarketDataAggregator, provider_name: str) -> tuple[str, str]:
    provider = aggregator.providers.get(provider_name, {})
    required_key = provider.get("required_key")
    if required_key and not os.getenv(required_key):
        return "UNAVAILABLE", "missing required credential"
    if provider_name == "mt5":
        try:
            import MetaTrader5  # noqa: F401
        except ImportError:
            return "UNAVAILABLE", "MetaTrader5 package unavailable"
    return "UNKNOWN", ""


async def _diagnose_symbol(aggregator: MarketDataAggregator, symbol: str) -> dict[str, Any]:
    reports: list[dict[str, Any]] = []
    provider_data: dict[str, MarketDataPoint] = {}

    for provider_name in PROVIDERS[symbol]:
        preflight_status, preflight_error = _provider_status(aggregator, provider_name)
        if preflight_status == "UNAVAILABLE":
            reports.append({
                "provider": provider_name,
                "status": preflight_status,
                "spot": False,
                "ohlcv": False,
                "candles": 0,
                "latest": "N/A",
                "fresh": "N/A",
                "used_consensus": False,
                "used_technical": False,
                "error": preflight_error,
            })
            continue

        try:
            point = await aggregator._fetch_from_provider(provider_name, symbol)
        except Exception as error:
            reports.append({
                "provider": provider_name,
                "status": "ERROR",
                "spot": False,
                "ohlcv": False,
                "candles": 0,
                "latest": "N/A",
                "fresh": "N/A",
                "used_consensus": False,
                "used_technical": False,
                "error": _safe_error(error),
            })
            continue

        if not point:
            reports.append({
                "provider": provider_name,
                "status": "ERROR",
                "spot": False,
                "ohlcv": False,
                "candles": 0,
                "latest": "N/A",
                "fresh": "N/A",
                "used_consensus": False,
                "used_technical": False,
                "error": "no valid response",
            })
            continue

        candles = point.ohlcv or []
        fresh = not aggregator._is_data_stale(point)
        provider_data[provider_name] = point
        reports.append({
            "provider": provider_name,
            "status": "VALID_OHLCV" if candles else "VALID_SPOT_ONLY",
            "spot": bool(point.price and point.price > 0),
            "ohlcv": bool(candles),
            "candles": len(candles),
            "latest": _fmt_timestamp(candles[-1].get("timestamp")) if candles else "N/A",
            "fresh": fresh,
            "used_consensus": False,
            "used_technical": False,
            "error": "",
        })

    validation = None
    validation_error = ""
    if provider_data:
        try:
            validation = aggregator._validate_and_consensus(symbol, provider_data)
        except Exception as error:
            validation_error = _safe_error(error)

    if validation:
        for report in reports:
            name = report["provider"]
            report["used_consensus"] = name in validation.provider_prices
            report["used_technical"] = name == validation.ohlcv_provider
            if name in validation.stale_providers:
                report["status"] = "STALE"
                report["fresh"] = False
            elif name in validation.outlier_providers:
                report["status"] = "OUTLIER"
                report["used_consensus"] = False

    selected = validation.ohlcv_provider if validation else None
    candles = len(validation.ohlcv or []) if validation else 0
    return {
        "symbol": symbol,
        "providers": reports,
        "ohlcv_source": selected or "NONE",
        "candles": candles,
        "technical_analysis": candles >= 200,
        "consensus_price": validation.consensus_price if validation else None,
        "validation_error": validation_error,
    }


def _text_report(results: list[dict[str, Any]]) -> str:
    lines = [
        "AI TRADING INTELLIGENCE SYSTEM",
        "GITHUB PROVIDER HEALTH CHECK",
        "",
        "SECRET STATUS",
        _secret_status(),
        "",
    ]
    for result in results:
        lines.extend([
            result["symbol"],
            "Provider | Status | Spot | OHLCV | Candles | Latest | Fresh | Consensus | Technical",
        ])
        for item in result["providers"]:
            lines.append(
                f'{item["provider"]} | {item["status"]} | '
                f'{ "YES" if item["spot"] else "NO" } | '
                f'{ "YES" if item["ohlcv"] else "NO" } | '
                f'{item["candles"]} | {item["latest"]} | {item["fresh"]} | '
                f'{ "YES" if item["used_consensus"] else "NO" } | '
                f'{ "YES" if item["used_technical"] else "NO" }'
            )
            if item["error"]:
                lines.append(f'  reason: {item["error"]}')
        lines.append(f'OHLCV source: {result["ohlcv_source"]}')
        lines.append(f'Technical analysis: {"AVAILABLE" if result["technical_analysis"] else "UNAVAILABLE"}')
        if result["validation_error"]:
            lines.append(f'Validation: {result["validation_error"]}')
        lines.append("")
    return "\n".join(lines).strip()


def _send_telegram(message: str) -> bool:
    token = os.getenv("TELEGRAM_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "843487976")
    if not token:
        print("Telegram: NOT CONFIGURED")
        return False
    if not chat_id:
        print("Telegram: NOT CONFIGURED (chat id missing)")
        return False

    import urllib.parse
    import urllib.request

    payload = urllib.parse.urlencode({"chat_id": chat_id, "text": message[:3900]}).encode()
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=payload,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            success = 200 <= response.status < 300
        print(f"Telegram: {'SENT' if success else 'FAILED'}")
        return success
    except Exception as error:
        logging.getLogger(__name__).error(
            "Telegram provider-health delivery failed: %s", type(error).__name__
        )
        print("Telegram: FAILED")
        return False


async def _run(send_telegram: bool) -> int:
    config = SystemConfig(
        xauusd_data_providers="goldapi,goldprice_dev,itick,twelvedata,alphavantage,yahoo_finance,mt5",
        xauusd_provider_priority="goldapi,goldprice_dev,itick,twelvedata,alphavantage,yahoo_finance,mt5",
    )
    aggregator = MarketDataAggregator(system_config=config)
    results = [await _diagnose_symbol(aggregator, symbol) for symbol in ("BTCUSD", "XAUUSD")]
    report = _text_report(results)
    print(report)
    if send_telegram and os.getenv("TELEGRAM_TOKEN"):
        return 0 if _send_telegram(report) else 1
    if send_telegram:
        print("Telegram: NOT CONFIGURED")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Sanitized GitHub provider health check")
    parser.add_argument("--send-telegram", action="store_true")
    args = parser.parse_args()
    try:
        return asyncio.run(_run(args.send_telegram))
    except Exception:
        logging.getLogger(__name__).exception("Provider diagnostics failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

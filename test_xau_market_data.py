"""Deterministic XAUUSD provider and validation coverage."""

import asyncio
import math
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from configuration_manager import SystemConfig
from market_data_aggregator import MarketDataAggregator, MarketDataPoint


def _point(source, price, timestamp=None):
    return MarketDataPoint(
        symbol="XAUUSD", price=price, bid=price - 0.1, ask=price + 0.1,
        spread=0.2, volume=10.0, timestamp=timestamp or datetime.now(timezone.utc),
        provider=source, source=source,
    )


def test_xau_provider_selection_and_consensus_without_network():
    aggregator = MarketDataAggregator(system_config=SystemConfig())
    assert aggregator._provider_names_for_symbol("XAUUSD") == [
        "goldprice_dev", "mt5", "goldapi", "itick"
    ]

    async def fixtures(name, symbol):
        return {
            "goldprice_dev": _point("GoldPriceDev", 4114.98),
            "goldapi": _point("GoldAPI", 4115.20),
            "mt5": _point("MT5", 4115.10),
            "itick": None,
        }[name]

    aggregator._fetch_from_provider = fixtures
    result = asyncio.run(aggregator.fetch_market_data("XAUUSD"))
    assert result.consensus_price == 4115.10
    assert result.provider_count == 4
    assert result.valid_provider_count == 3
    assert result.provider_status["itick"] == "unavailable"


def test_xau_validation_rejects_invalid_nonfinite_and_stale_data():
    aggregator = MarketDataAggregator(system_config=SystemConfig())
    now = datetime.now(timezone.utc)
    points = {
        "fresh": _point("fresh", 4115.0, now),
        "nan": _point("nan", math.nan, now),
        "stale": _point("stale", 4115.1, now - timedelta(seconds=61)),
    }
    result = aggregator._validate_and_consensus("XAUUSD", points)
    assert result.valid_provider_count == 1
    assert "stale" in result.stale_providers


def test_goldapi_normalizes_response_without_exposing_credentials(monkeypatch):
    aggregator = MarketDataAggregator(system_config=SystemConfig())
    captured = {}

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"price": 4115.2, "bid": 4115.1, "ask": 4115.3, "timestamp": 1700000000}

    def get(url, **kwargs):
        captured.update(kwargs)
        return Response()

    monkeypatch.setattr("market_data_aggregator.requests.get", get)
    monkeypatch.setenv("GOLD_API", "test-only-key")
    result = asyncio.run(aggregator._fetch_goldapi(aggregator.providers["goldapi"], "XAUUSD"))
    assert result.price == 4115.2
    assert captured["headers"]["x-access-token"] == "test-only-key"


def test_goldapi_missing_canonical_credential_is_unavailable(monkeypatch):
    aggregator = MarketDataAggregator(system_config=SystemConfig())
    monkeypatch.delenv("GOLD_API", raising=False)
    result = asyncio.run(aggregator._fetch_from_provider("goldapi", "XAUUSD"))
    assert result is None


def test_xau_all_providers_unavailable_is_data_unavailable(monkeypatch):
    aggregator = MarketDataAggregator(system_config=SystemConfig())

    async def unavailable(name, symbol):
        return None

    monkeypatch.setattr(aggregator, "_fetch_from_provider", unavailable)
    try:
        asyncio.run(aggregator.fetch_market_data("XAUUSD"))
    except ValueError as error:
        assert "DATA UNAVAILABLE" in str(error)
    else:
        raise AssertionError("XAUUSD must not produce a signal without provider data")

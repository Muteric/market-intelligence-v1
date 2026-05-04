from __future__ import annotations

import json
import os
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import requests

_cache: dict[str, tuple[Any, float]] = {}


COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"
BTC_PRICE_URL = f"{COINGECKO_BASE_URL}/simple/price"
MARKET_MOVERS_URL = f"{COINGECKO_BASE_URL}/coins/markets"
BINANCE_BASE_URL = "https://api.binance.com"
BINANCE_FUTURES_BASE_URL = "https://fapi.binance.com"
BINANCE_KLINES_URL = f"{BINANCE_BASE_URL}/api/v3/klines"
BINANCE_24HR_TICKER_URL = f"{BINANCE_BASE_URL}/api/v3/ticker/24hr"
BINANCE_PREMIUM_INDEX_URL = f"{BINANCE_FUTURES_BASE_URL}/fapi/v1/premiumIndex"
BINANCE_OPEN_INTEREST_URL = f"{BINANCE_FUTURES_BASE_URL}/fapi/v1/openInterest"
FEAR_GREED_URL = "https://api.alternative.me/fng/"
COINMARKETCAL_EVENTS_URL = "https://developers.coinmarketcal.com/v1/events"
COINMARKETCAL_API_KEY_ENV = "COINMARKETCAL_API_KEY"
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8431698430:AAGDVRr3hAWSWbm66eJ9xOWnt-os8q-_a1o")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "843487976")
CRYPTO_NEWS_SOURCES = (
    ("Cointelegraph", "https://cointelegraph.com/rss", 1.0),
    ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/", 1.2),
)
REQUEST_TIMEOUT_SECONDS = 10
NEWS_LIMIT_PER_SOURCE = 5
EVENT_LIMIT = 5
MOVER_LIMIT = 3
BINANCE_MOVER_LIMIT = 5
BINANCE_SYMBOL = "BTCUSDT"
BINANCE_INTERVAL = "1h"
BINANCE_CANDLE_LIMIT = 24
BINANCE_MOVER_QUOTE_ASSET = "USDT"

WORD_RE = re.compile(r"[A-Za-z][A-Za-z'-]*")
SENTIMENT_WEIGHTS = {
    "accumulation": 0.6,
    "advance": 0.6,
    "approval": 0.5,
    "ath": 0.8,
    "breakout": 0.8,
    "bull": 0.7,
    "bullish": 1.0,
    "climb": 0.6,
    "climbs": 0.6,
    "gain": 0.7,
    "gains": 0.7,
    "growth": 0.5,
    "high": 0.4,
    "inflow": 0.7,
    "inflows": 0.7,
    "jump": 0.7,
    "jumps": 0.7,
    "opportunity": 0.4,
    "positive": 0.6,
    "rally": 0.8,
    "recover": 0.6,
    "recovery": 0.6,
    "record": 0.5,
    "rise": 0.6,
    "rises": 0.6,
    "strong": 0.5,
    "surge": 0.8,
    "surges": 0.8,
    "up": 0.4,
    "bear": -0.7,
    "bearish": -1.0,
    "block": -0.3,
    "blocked": -0.4,
    "crackdown": -0.8,
    "crash": -1.0,
    "decline": -0.6,
    "drop": -0.7,
    "drops": -0.7,
    "exploit": -0.9,
    "fall": -0.6,
    "falls": -0.6,
    "frozen": -0.5,
    "hack": -0.9,
    "lawsuit": -0.6,
    "loss": -0.7,
    "losses": -0.7,
    "negative": -0.6,
    "outflow": -0.7,
    "outflows": -0.7,
    "plunge": -0.9,
    "risk": -0.5,
    "scam": -0.9,
    "sell": -0.5,
    "slump": -0.8,
    "weak": -0.5,
}


@dataclass(frozen=True)
class CoinMover:
    name: str
    change_24h: float


@dataclass(frozen=True)
class NewsItem:
    source: str
    title: str
    weight: float


@dataclass(frozen=True)
class FearGreedSnapshot:
    value: int | None
    classification: str | None


@dataclass(frozen=True)
class DerivativesSnapshot:
    funding_rate: float | None
    open_interest: float | None


@dataclass(frozen=True)
class SignalBreakdown:
    news: float
    event_catalysts: float
    fear_greed: float
    binance_spot: float
    derivatives: float
    market_movers: float
    binance_movers: float


@dataclass(frozen=True)
class BinanceCandle:
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: float


@dataclass(frozen=True)
class MarketSnapshot:
    btc_price: float | None
    news_items: list[NewsItem]
    news_sentiment: float
    event_catalysts: list[str]
    event_catalyst_score: float
    fear_greed: FearGreedSnapshot
    fear_greed_sentiment: float
    derivatives: DerivativesSnapshot
    derivatives_sentiment: float
    binance_sentiment: float
    binance_candles: list[BinanceCandle]
    gainers: list[CoinMover]
    losers: list[CoinMover]
    binance_gainers: list[CoinMover]
    binance_losers: list[CoinMover]


def fetch_url(
    url: str,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> bytes | None:
    if params:
        url = f"{url}?{urlencode(params)}"

    request_headers = {"User-Agent": "market-intelligence/1.0"}
    if headers:
        request_headers.update(headers)

    request = Request(url, headers=request_headers)
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            return response.read()
    except (HTTPError, URLError, TimeoutError) as error:
        print(f"Error fetching {url}: {error}")
        return None


def fetch_json(
    url: str,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> Any | None:
    content = fetch_url(url, params, headers)
    if content is None:
        return None

    try:
        return json.loads(content.decode("utf-8"))
    except json.JSONDecodeError as error:
        print(f"Error parsing JSON from {url}: {error}")
        return None


def send_telegram_message(message: str) -> None:
    if not TELEGRAM_TOKEN or TELEGRAM_TOKEN == "YOUR_NEW_BOT_TOKEN":
        print("Telegram token not configured; skipping Telegram alert.")
        return

    if not CHAT_ID:
        print("Telegram chat ID not configured; skipping Telegram alert.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
    }

    try:
        response = requests.post(url, data=payload, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        print("Telegram alert sent successfully.")
    except requests.RequestException as error:
        response_text = ""
        if getattr(error, "response", None) is not None:
            response_text = f" Response: {error.response.text}"
        print(f"Error sending Telegram message: {error}.{response_text}")


def get_btc_price() -> float | None:
    cache_key = "btc_price"

    # Use cached value for 60 seconds.
    if cache_key in _cache:
        value, timestamp = _cache[cache_key]
        if time.time() - timestamp < 60:
            return value

    data = fetch_json(
        BTC_PRICE_URL,
        params={"ids": "bitcoin", "vs_currencies": "usd"},
    )
    if not isinstance(data, dict):
        return _cache.get(cache_key, (None, 0.0))[0]

    price = data.get("bitcoin", {}).get("usd")
    if not isinstance(price, (int, float)):
        return _cache.get(cache_key, (None, 0.0))[0]

    price = float(price)
    _cache[cache_key] = (price, time.time())
    return price


def get_news_from_rss(source: str, url: str, weight: float, limit: int) -> list[NewsItem]:
    content = fetch_url(url)
    if content is None:
        return []

    try:
        root = ET.fromstring(content)
    except ET.ParseError as error:
        print(f"Error parsing RSS feed: {error}")
        return []

    items: list[NewsItem] = []
    for item in root.findall("./channel/item"):
        title = item.findtext("title", default="").strip()
        if title:
            items.append(NewsItem(source=source, title=title, weight=weight))
        if len(items) == limit:
            break

    return items


def get_crypto_news(limit_per_source: int = NEWS_LIMIT_PER_SOURCE) -> list[NewsItem]:
    news_items: list[NewsItem] = []
    for source, url, weight in CRYPTO_NEWS_SOURCES:
        news_items.extend(get_news_from_rss(source, url, weight, limit_per_source))
    return news_items


def analyze_sentiment(text: str) -> float:
    weights = [
        SENTIMENT_WEIGHTS[word.lower()]
        for word in WORD_RE.findall(text)
        if word.lower() in SENTIMENT_WEIGHTS
    ]
    if not weights:
        return 0.0

    return sum(weights) / len(weights)


def clamp(value: float, lower: float = -1.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def overall_sentiment(news_items: list[NewsItem]) -> float:
    if not news_items:
        return 0.0

    weighted_scores = [
        analyze_sentiment(item.title) * item.weight
        for item in news_items
    ]
    total_weight = sum(item.weight for item in news_items)
    return sum(weighted_scores) / total_weight if total_weight else 0.0


def get_market_movers(limit: int = MOVER_LIMIT) -> tuple[list[CoinMover], list[CoinMover]]:
    data = fetch_json(
        MARKET_MOVERS_URL,
        params={
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": 20,
            "page": 1,
        },
    )
    if not isinstance(data, list):
        return [], []

    coins: list[CoinMover] = []
    for coin in data:
        if not isinstance(coin, dict):
            continue

        name = coin.get("name")
        change = coin.get("price_change_percentage_24h")
        if isinstance(name, str) and isinstance(change, (int, float)):
            coins.append(CoinMover(name=name, change_24h=float(change)))

    gainers = sorted(coins, key=lambda coin: coin.change_24h, reverse=True)[:limit]
    losers = sorted(coins, key=lambda coin: coin.change_24h)[:limit]
    return gainers, losers


def get_binance_market_movers(
    limit: int = BINANCE_MOVER_LIMIT,
) -> tuple[list[CoinMover], list[CoinMover]]:
    data = fetch_json(BINANCE_24HR_TICKER_URL)
    if not isinstance(data, list):
        return [], []

    coins: list[CoinMover] = []
    for ticker in data:
        if not isinstance(ticker, dict):
            continue

        symbol = ticker.get("symbol")
        change = ticker.get("priceChangePercent")
        if not isinstance(symbol, str) or not symbol.endswith(BINANCE_MOVER_QUOTE_ASSET):
            continue

        try:
            coins.append(CoinMover(name=symbol, change_24h=float(change)))
        except (TypeError, ValueError):
            continue

    gainers = sorted(coins, key=lambda coin: coin.change_24h, reverse=True)[:limit]
    losers = sorted(coins, key=lambda coin: coin.change_24h)[:limit]
    return gainers, losers


def get_fear_greed_snapshot() -> FearGreedSnapshot:
    data = fetch_json(FEAR_GREED_URL, params={"limit": 1, "format": "json"})
    if not isinstance(data, dict):
        return FearGreedSnapshot(value=None, classification=None)

    values = data.get("data")
    if not isinstance(values, list) or not values:
        return FearGreedSnapshot(value=None, classification=None)

    latest = values[0]
    if not isinstance(latest, dict):
        return FearGreedSnapshot(value=None, classification=None)

    try:
        value = int(latest.get("value"))
    except (TypeError, ValueError):
        value = None

    classification = latest.get("value_classification")
    if not isinstance(classification, str):
        classification = None

    return FearGreedSnapshot(value=value, classification=classification)


def analyze_fear_greed(snapshot: FearGreedSnapshot) -> float:
    if snapshot.value is None:
        return 0.0

    # Extreme fear confirms downside risk; extreme greed warns of crowded longs.
    if snapshot.value <= 20:
        return -0.6
    if snapshot.value <= 35:
        return -0.3
    if snapshot.value >= 80:
        return -0.2
    if snapshot.value >= 65:
        return 0.2
    return 0.0


def get_derivatives_snapshot(symbol: str = BINANCE_SYMBOL) -> DerivativesSnapshot:
    premium_data = fetch_json(BINANCE_PREMIUM_INDEX_URL, params={"symbol": symbol})
    open_interest_data = fetch_json(BINANCE_OPEN_INTEREST_URL, params={"symbol": symbol})

    funding_rate: float | None = None
    if isinstance(premium_data, dict):
        try:
            funding_rate = float(premium_data.get("lastFundingRate"))
        except (TypeError, ValueError):
            funding_rate = None

    open_interest: float | None = None
    if isinstance(open_interest_data, dict):
        try:
            open_interest = float(open_interest_data.get("openInterest"))
        except (TypeError, ValueError):
            open_interest = None

    return DerivativesSnapshot(
        funding_rate=funding_rate,
        open_interest=open_interest,
    )


def analyze_derivatives(snapshot: DerivativesSnapshot, spot_sentiment: float) -> float:
    if snapshot.funding_rate is None:
        return 0.0

    funding_pct = snapshot.funding_rate * 100
    if spot_sentiment > 0 and funding_pct < 0.03:
        return 0.25
    if spot_sentiment > 0 and funding_pct > 0.08:
        return -0.35
    if spot_sentiment < 0 and funding_pct < -0.03:
        return -0.25
    if spot_sentiment < 0 and funding_pct > 0:
        return 0.15
    return 0.0


def get_event_catalysts(limit: int = EVENT_LIMIT) -> tuple[list[str], float]:
    api_key = os.getenv(COINMARKETCAL_API_KEY_ENV)
    if not api_key:
        return [], 0.0

    data = fetch_json(
        COINMARKETCAL_EVENTS_URL,
        params={
            "max": limit,
            "sortBy": "hot_events",
            "showOnly": "hot_events",
        },
        headers={"x-api-key": api_key},
    )
    if not isinstance(data, list):
        return [], 0.0

    events: list[str] = []
    scores: list[float] = []
    for event in data:
        if not isinstance(event, dict):
            continue

        title = event.get("title") or event.get("name")
        if isinstance(title, dict):
            title = title.get("en")
        if isinstance(title, str):
            events.append(title)

        score = event.get("score") or event.get("confidence") or event.get("votes")
        if isinstance(score, (int, float)):
            scores.append(min(float(score) / 100, 1.0))

    catalyst_score = sum(scores) / len(scores) if scores else 0.0
    return events[:limit], catalyst_score


def get_binance_klines(
    symbol: str = BINANCE_SYMBOL,
    interval: str = BINANCE_INTERVAL,
    limit: int = BINANCE_CANDLE_LIMIT,
) -> list[BinanceCandle]:
    data = fetch_json(
        BINANCE_KLINES_URL,
        params={"symbol": symbol, "interval": interval, "limit": limit},
    )
    if not isinstance(data, list):
        return []

    candles: list[BinanceCandle] = []
    for item in data:
        if not isinstance(item, list) or len(item) < 6:
            continue

        try:
            candles.append(
                BinanceCandle(
                    open_price=float(item[1]),
                    high_price=float(item[2]),
                    low_price=float(item[3]),
                    close_price=float(item[4]),
                    volume=float(item[5]),
                )
            )
        except (TypeError, ValueError):
            continue

    return candles


def analyze_binance_sentiment(candles: list[BinanceCandle]) -> float:
    if len(candles) < 2:
        return 0.0

    first_close = candles[0].close_price
    last_close = candles[-1].close_price
    if first_close <= 0:
        return 0.0

    price_change_pct = ((last_close - first_close) / first_close) * 100
    green_candles = sum(
        1
        for candle in candles
        if candle.close_price > candle.open_price
    )
    green_ratio = green_candles / len(candles)

    return (price_change_pct / 10) + (green_ratio - 0.5)


def average_mover_sentiment(gainers: list[CoinMover], losers: list[CoinMover]) -> float:
    mover_changes = [coin.change_24h for coin in gainers + losers]
    average_momentum = (
        sum(mover_changes) / len(mover_changes)
        if mover_changes
        else 0.0
    )
    return clamp(average_momentum / 10)


def get_signal_breakdown(snapshot: MarketSnapshot) -> SignalBreakdown:
    return SignalBreakdown(
        news=snapshot.news_sentiment,
        event_catalysts=snapshot.event_catalyst_score,
        fear_greed=snapshot.fear_greed_sentiment,
        binance_spot=snapshot.binance_sentiment,
        derivatives=snapshot.derivatives_sentiment,
        market_movers=average_mover_sentiment(snapshot.gainers, snapshot.losers),
        binance_movers=average_mover_sentiment(
            snapshot.binance_gainers,
            snapshot.binance_losers,
        ),
    )


def compute_market_pressure(snapshot: MarketSnapshot) -> float:
    breakdown = get_signal_breakdown(snapshot)
    weights = {
        "news": 1.2,
        "event_catalysts": 1.5,
        "fear_greed": 1.0,
        "binance_spot": 1.4,
        "derivatives": 1.1,
        "market_movers": 1.0,
        "binance_movers": 0.8,
    }
    weighted_score = (
        breakdown.news * weights["news"]
        + breakdown.event_catalysts * weights["event_catalysts"]
        + breakdown.fear_greed * weights["fear_greed"]
        + breakdown.binance_spot * weights["binance_spot"]
        + breakdown.derivatives * weights["derivatives"]
        + breakdown.market_movers * weights["market_movers"]
        + breakdown.binance_movers * weights["binance_movers"]
    )
    return weighted_score / sum(weights.values())


def compute_confidence(snapshot: MarketSnapshot, pressure: float) -> float:
    breakdown = get_signal_breakdown(snapshot)
    scores = [
        breakdown.news,
        breakdown.event_catalysts,
        breakdown.fear_greed,
        breakdown.binance_spot,
        breakdown.derivatives,
        breakdown.market_movers,
        breakdown.binance_movers,
    ]
    active_scores = [score for score in scores if abs(score) >= 0.05]
    if not active_scores:
        return 0.0

    pressure_direction = 1 if pressure > 0 else -1
    aligned = [
        score for score in active_scores
        if (score > 0 and pressure_direction > 0)
        or (score < 0 and pressure_direction < 0)
    ]
    agreement = len(aligned) / len(active_scores)
    coverage = len(active_scores) / len(scores)
    return (agreement * 0.7) + (coverage * 0.3)


def get_signal(snapshot: MarketSnapshot) -> str:
    pressure = compute_market_pressure(snapshot)
    confidence = compute_confidence(snapshot, pressure)

    if pressure > 0.45 and confidence > 0.65:
        return "Strong bullish momentum; capital inflow is likely."
    if pressure < -0.35 and confidence > 0.65:
        return "Strong bearish pressure; risk-off conditions are likely."
    if pressure > 0.12:
        return "Weak bullish bias; early accumulation is possible."
    if pressure < -0.12:
        return "Weak bearish bias."
    return "Neutral or choppy market."


def collect_market_snapshot() -> MarketSnapshot:
    news_items = get_crypto_news()
    binance_candles = get_binance_klines()
    binance_sentiment = analyze_binance_sentiment(binance_candles)
    fear_greed = get_fear_greed_snapshot()
    derivatives = get_derivatives_snapshot()
    gainers, losers = get_market_movers()
    binance_gainers, binance_losers = get_binance_market_movers()
    event_catalysts, event_catalyst_score = get_event_catalysts()
    return MarketSnapshot(
        btc_price=get_btc_price(),
        news_items=news_items,
        news_sentiment=overall_sentiment(news_items),
        event_catalysts=event_catalysts,
        event_catalyst_score=event_catalyst_score,
        fear_greed=fear_greed,
        fear_greed_sentiment=analyze_fear_greed(fear_greed),
        derivatives=derivatives,
        derivatives_sentiment=analyze_derivatives(derivatives, binance_sentiment),
        binance_sentiment=binance_sentiment,
        binance_candles=binance_candles,
        gainers=gainers,
        losers=losers,
        binance_gainers=binance_gainers,
        binance_losers=binance_losers,
    )


def print_price(price: float | None) -> None:
    if price is None:
        print("\nBTC price: unavailable")
        return

    print(f"\nBTC price: ${price:,.2f}")


def print_news_sentiment(news_items: list[NewsItem]) -> None:
    print("\nNews and sentiment:")
    if not news_items:
        print("No news data available.")
        return

    for item in news_items:
        print(
            f"- [{item.source}] {item.title} | "
            f"sentiment: {analyze_sentiment(item.title):.3f}"
        )

    print(f"\nOverall sentiment: {overall_sentiment(news_items):.3f}")


def print_event_catalysts(events: list[str], score: float) -> None:
    print("\nEvent catalysts:")
    if not events:
        print(f"No CoinMarketCal events available. Set {COINMARKETCAL_API_KEY_ENV} to enable.")
        return

    for event in events:
        print(f"- {event}")
    print(f"Event catalyst score: {score:.3f}")


def print_fear_greed(snapshot: FearGreedSnapshot, sentiment: float) -> None:
    print("\nFear and greed:")
    if snapshot.value is None:
        print("Fear and greed data unavailable.")
        return

    classification = snapshot.classification or "unclassified"
    print(f"- Index: {snapshot.value} ({classification})")
    print(f"- Regime sentiment: {sentiment:.3f}")


def print_derivatives(snapshot: DerivativesSnapshot, sentiment: float) -> None:
    print(f"\nBinance derivatives ({BINANCE_SYMBOL}):")
    if snapshot.funding_rate is None and snapshot.open_interest is None:
        print("Derivatives data unavailable.")
        return

    if snapshot.funding_rate is not None:
        print(f"- Funding rate: {snapshot.funding_rate * 100:.4f}%")
    if snapshot.open_interest is not None:
        print(f"- Open interest: {snapshot.open_interest:,.3f} {BINANCE_SYMBOL.removesuffix('USDT')}")
    print(f"- Derivatives sentiment: {sentiment:.3f}")


def print_market_movers(title: str, coins: list[CoinMover]) -> None:
    print(f"\n{title}:")
    if not coins:
        print("No market mover data available.")
        return

    for coin in coins:
        print(f"- {coin.name}: {coin.change_24h:.2f}%")


def print_binance_sentiment(candles: list[BinanceCandle], sentiment: float) -> None:
    print(f"\nBinance chart sentiment ({BINANCE_SYMBOL}, {BINANCE_INTERVAL}):")
    if len(candles) < 2:
        print("Not enough Binance candle data available.")
        return

    first_close = candles[0].close_price
    last_close = candles[-1].close_price
    price_change_pct = ((last_close - first_close) / first_close) * 100
    green_candles = sum(
        1
        for candle in candles
        if candle.close_price > candle.open_price
    )

    print(f"- Candles analyzed: {len(candles)}")
    print(f"- Price change: {price_change_pct:.2f}%")
    print(f"- Green candles: {green_candles}/{len(candles)}")
    print(f"- Binance sentiment: {sentiment:.3f}")


def print_signal_breakdown(snapshot: MarketSnapshot) -> None:
    breakdown = get_signal_breakdown(snapshot)
    print("\nSignal components:")
    print(f"- News sentiment: {breakdown.news:.3f}")
    print(f"- Event catalysts: {breakdown.event_catalysts:.3f}")
    print(f"- Fear/greed regime: {breakdown.fear_greed:.3f}")
    print(f"- Binance spot momentum: {breakdown.binance_spot:.3f}")
    print(f"- Binance derivatives: {breakdown.derivatives:.3f}")
    print(f"- Broad market movers: {breakdown.market_movers:.3f}")
    print(f"- Binance movers: {breakdown.binance_movers:.3f}")


def format_mover_names(coins: list[CoinMover], limit: int = 3) -> str:
    if not coins:
        return "- unavailable"

    return "\n".join(f"- {coin.name}: {coin.change_24h:.2f}%" for coin in coins[:limit])


def build_signal_message(snapshot: MarketSnapshot, pressure: float, confidence: float) -> str:
    price = (
        f"${snapshot.btc_price:,.2f}"
        if snapshot.btc_price is not None
        else "unavailable"
    )
    signal = get_signal(snapshot)

    return f"""
📊 MARKET SIGNAL

BTC Price: {price}
Overall Sentiment: {snapshot.news_sentiment:.3f}
Market Pressure: {pressure:.3f}
Signal Confidence: {confidence:.2f}

Signal: {signal}

Top Gainers:
{format_mover_names(snapshot.gainers)}

Top Losers:
{format_mover_names(snapshot.losers)}

Binance Top Gainers:
{format_mover_names(snapshot.binance_gainers)}

Binance Top Losers:
{format_mover_names(snapshot.binance_losers)}
""".strip()


def print_report(snapshot: MarketSnapshot) -> None:
    pressure = compute_market_pressure(snapshot)
    confidence = compute_confidence(snapshot, pressure)

    print_price(snapshot.btc_price)
    print_news_sentiment(snapshot.news_items)
    print_event_catalysts(snapshot.event_catalysts, snapshot.event_catalyst_score)
    print_fear_greed(snapshot.fear_greed, snapshot.fear_greed_sentiment)
    print_binance_sentiment(snapshot.binance_candles, snapshot.binance_sentiment)
    print_derivatives(snapshot.derivatives, snapshot.derivatives_sentiment)
    print_market_movers("Top gainers", snapshot.gainers)
    print_market_movers("Top losers", snapshot.losers)
    print_market_movers("Binance top gainers", snapshot.binance_gainers)
    print_market_movers("Binance top losers", snapshot.binance_losers)
    print_signal_breakdown(snapshot)
    print(f"\nMarket pressure score: {pressure:.3f}")
    print(f"Signal confidence: {confidence:.2f}")
    message = build_signal_message(snapshot, pressure, confidence)
    print(f"\n{message}")
    send_telegram_message(message)


def main() -> None:
    print_report(collect_market_snapshot())


if __name__ == "__main__":
    main()

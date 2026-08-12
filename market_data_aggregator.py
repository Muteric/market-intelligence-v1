"""
Market Data Aggregator for AI Trading Intelligence Bot
Multi-source market data aggregation with price validation and consensus calculation.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass
try:
    import requests
except ImportError:  # Optional at import time; requirements installs it in CI.
    requests = None
import random
import os
import math
from statistics import median
from urllib.parse import quote

from configuration_manager import AssetConfig

logger = logging.getLogger(__name__)

@dataclass
class MarketDataPoint:
    """Single market data point from a provider"""
    symbol: str
    price: float
    bid: float
    ask: float
    spread: float
    volume: float
    timestamp: datetime
    provider: str
    source: str
    status: str = "valid"
    previous_price: Optional[float] = None
    ohlcv: Optional[List[Dict[str, float]]] = None
    data_kind: str = 'spot_only'
    
@dataclass
class PriceValidationResult:
    """Result of price validation"""
    symbol: str
    consensus_price: float
    consensus_bid: float
    consensus_ask: float
    consensus_spread: float
    consensus_volume: float
    provider_prices: Dict[str, float]
    outlier_providers: List[str]
    stale_providers: List[str]
    validation_timestamp: datetime
    confidence_score: float
    previous_price: Optional[float] = None
    ohlcv: Optional[List[Dict[str, float]]] = None
    ohlcv_provider: Optional[str] = None
    provider_count: int = 0
    valid_provider_count: int = 0
    provider_status: Optional[Dict[str, str]] = None
    execution_reference_price: Optional[float] = None

class MarketDataAggregator:
    """Multi-source market data aggregation with price validation"""
    
    def __init__(self, config_file: str = "app_config.json", system_config: Any = None):
        self.config_file = config_file
        self.system_config = system_config
        self.providers = {}
        self.provider_configs = {}
        self.price_history = {}
        self.validation_cache = {}
        self.last_successful_fetch = {}
        self.provider_cache = {}
        self.provider_health = {}
        self._initialize_providers()
        
    def _initialize_providers(self) -> None:
        """Initialize market data providers"""
        # Binance API (primary)
        self.providers['binance'] = {
            'name': 'Binance',
            'base_url': 'https://api.binance.com/api/v3',
            'endpoints': {
                'ticker': '/ticker/24hr',
                'price': '/ticker/price'
                , 'klines': '/klines'
            },
            'priority': 1,
            'weight': 1.0
        }
        
        # CoinGecko API (independent validation)
        self.providers['coingecko'] = {
            'name': 'CoinGecko',
            'base_url': 'https://api.coingecko.com/api/v3',
            'endpoints': {
                'simple_price': '/simple/price',
                'global': '/global'
            },
            'priority': 2,
            'weight': 0.8
        }
        
        # Alpha Vantage API (gold, forex, additional market data)
        self.providers['alphavantage'] = {
            'name': 'Alpha Vantage',
            'base_url': 'https://www.alphavantage.co/query',
            'endpoints': {
                'global_quote': '/GLOBAL_QUOTE',
                'time_series': '/TIME_SERIES_DAILY'
            },
            'priority': 3,
            'weight': 0.7,
            'required_key': 'ALPHAVANTAGE_API_KEY'
        }
        
        # Twelve Data API (BTCUSD, XAUUSD, technical indicators)
        self.providers['twelvedata'] = {
            'name': 'Twelve Data',
            'base_url': 'https://api.twelvedata.com',
            'endpoints': {
                'time_series': '/time_series',
                'quote': '/quote'
            },
            'priority': 4,
            'weight': 0.7,
            'required_key': 'TWELVEDATA_API_KEY'
        }
        
        # Yahoo Finance API (community validation)
        self.providers['yahoo_finance'] = {
            'name': 'Yahoo Finance',
            'base_url': 'https://query1.finance.yahoo.com',
            'endpoints': {
                'quote': '/v7/finance/quote',
                'chart': '/v8/finance/chart'
            },
            'priority': 5,
            'weight': 0.6
        }

        self.providers['goldapi'] = {
            'name': 'GoldAPI', 'base_url': os.getenv('GOLDAPI_BASE_URL', 'https://www.goldapi.io/api'),
            'required_key': 'GOLD_API', 'weight': 1.0,
        }
        self.providers['goldprice_dev'] = {
            'name': 'GoldPriceDev', 'base_url': os.getenv('GOLDPRICEDEV_BASE_URL', 'https://api.goldprice.dev'),
            'required_key': None, 'weight': 0.9,
        }
        self.providers['mt5'] = {
            'name': 'MT5', 'required_key': None, 'weight': 1.1,
        }
        self.providers['itick'] = {
            'name': 'iTick', 'base_url': os.getenv('ITICK_BASE_URL', 'https://api.itick.org'),
            'required_key': 'ITICK_API_KEY', 'weight': 0.8,
        }
        
        # Initialize provider health tracking
        for provider_name in self.providers:
            self.provider_health[provider_name] = {
                'consecutive_failures': 0,
                'last_success': None,
                'total_requests': 0,
                'successful_requests': 0,
                'average_response_time': 0.0,
                'is_healthy': True
                , 'last_failure': None, 'request_count': 0, 'error_count': 0,
                'last_price': None, 'last_timestamp': None, 'stale': False,
            }
    
    async def fetch_market_data(self, symbol: str) -> PriceValidationResult:
        """Fetch market data from all providers and validate"""
        logger.info(f"Fetching market data for {symbol} from all providers")

        # Fetch data from all providers
        provider_data = {}
        for provider_name in self._provider_names_for_symbol(symbol):
            try:
                data = await self._fetch_from_provider(provider_name, symbol)
                if data:
                    provider_data[provider_name] = data
                    self.provider_cache[(symbol, provider_name)] = data
                    self._update_provider_health(provider_name, True)
                else:
                    self._update_provider_health(provider_name, False)
            except Exception as e:
                logger.error(f"Provider {provider_name} failed for {symbol}: {e}")
                self._update_provider_health(provider_name, False)
        
        if not provider_data:
            raise ValueError(f"DATA UNAVAILABLE: no market data available for {symbol} from configured providers")
        
        # Validate and calculate consensus
        validation_result = self._validate_and_consensus(symbol, provider_data)
        
        # Cache the result
        self._cache_validation_result(symbol, validation_result)
        
        return validation_result
    
    async def _fetch_from_provider(self, provider_name: str, symbol: str) -> Optional[MarketDataPoint]:
        """Fetch data from a specific provider"""
        if requests is None and provider_name != 'mt5':
            logger.warning("Provider %s unavailable: requests dependency is not installed", provider_name)
            return None
        provider = self.providers[provider_name]
        required_key = provider.get('required_key')
        if required_key and not self._secret_available(required_key):
            logger.info("Provider %s unavailable: missing %s", provider_name, required_key)
            return None
        cached = self.provider_cache.get((symbol, provider_name))
        if cached is not None and provider_name == 'goldapi':
            age = (datetime.now(timezone.utc) - cached.timestamp).total_seconds()
            interval = getattr(self.system_config, 'goldapi_min_interval_seconds', 300)
            if age < interval:
                logger.info('Using cached GoldAPI result for %s (age %.0fs)', symbol, age)
                return cached
        start_time = time.time()
        
        try:
            if provider_name == 'binance':
                data = await self._fetch_binance(provider, symbol)
            elif provider_name == 'coingecko':
                data = await self._fetch_coingecko(provider, symbol)
            elif provider_name == 'alphavantage':
                data = await self._fetch_alphavantage(provider, symbol)
            elif provider_name == 'twelvedata':
                data = await self._fetch_twelvedata(provider, symbol)
            elif provider_name == 'yahoo_finance':
                data = await self._fetch_yahoo_finance(provider, symbol)
            elif provider_name == 'goldapi':
                data = await self._fetch_goldapi(provider, symbol)
            elif provider_name == 'goldprice_dev':
                data = await self._fetch_goldprice_dev(provider, symbol)
            elif provider_name == 'mt5':
                data = await self._fetch_mt5(provider, symbol)
            elif provider_name == 'itick':
                data = await self._fetch_itick(provider, symbol)
            else:
                return None
            
            response_time = time.time() - start_time
            self._update_provider_response_time(provider_name, response_time)
            
            return data
            
        except Exception as e:
            logger.error(f"Error fetching from {provider_name}: {e}")
            return None
    
    def _normalized_quote(self, symbol: str, price: Any, provider: str, source: str,
                          timestamp: Any = None, bid: Any = None, ask: Any = None,
                          previous_price: Any = None, volume: Any = 0.0,
                          ohlcv: Optional[List[Dict[str, float]]] = None) -> MarketDataPoint:
        value = float(price)
        stamp = timestamp or datetime.now(timezone.utc)
        if isinstance(stamp, (int, float)):
            stamp = datetime.fromtimestamp(float(stamp) / (1000 if stamp > 10**11 else 1), timezone.utc)
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
        bid_value = float(bid) if bid is not None else value
        ask_value = float(ask) if ask is not None else value
        return MarketDataPoint(
            symbol=symbol, price=value, bid=bid_value, ask=ask_value,
            spread=ask_value - bid_value, volume=float(volume or 0.0),
            timestamp=stamp, provider=provider, source=source,
            previous_price=float(previous_price) if previous_price is not None else None,
            ohlcv=ohlcv,
            data_kind='ohlcv' if ohlcv else 'spot_only',
        )

    async def _fetch_goldapi(self, provider: Dict, symbol: str) -> Optional[MarketDataPoint]:
        if symbol != 'XAUUSD':
            return None
        response = requests.get(
            f"{provider['base_url']}/XAU/USD",
            headers={'x-access-token': self._secret_value('GOLD_API')}, timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        return self._normalized_quote(
            symbol, data.get('price'), provider['name'], 'goldapi',
            timestamp=data.get('timestamp'), bid=data.get('bid'), ask=data.get('ask'),
            previous_price=data.get('prev_close_price'), volume=data.get('volume', 0.0),
        )

    async def _fetch_goldprice_dev(self, provider: Dict, symbol: str) -> Optional[MarketDataPoint]:
        if symbol != 'XAUUSD':
            return None
        headers = {}
        key = self._secret_value('GOLDPRICEDEV_API_KEY') or self._secret_value('GP_KEY')
        if key:
            headers['Authorization'] = f'Bearer {key}'
        response = requests.get(
            f"{provider['base_url']}/v1/spot/XAU-USD", headers=headers, timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict) and 'price' in data:
            quote = data
        else:
            quote = (data.get('symbols') or [{}])[0]
        ohlcv = None
        try:
            bars_response = requests.get(
                f"{provider['base_url']}/v1/bars",
                params={'symbol': 'XAU-USD', 'interval': '5m', 'limit': 1000},
                headers=headers, timeout=10,
            )
            bars_response.raise_for_status()
            bars_data = bars_response.json()
            bars = bars_data.get('bars', bars_data.get('data', [])) if isinstance(bars_data, dict) else bars_data
            if isinstance(bars, list):
                ohlcv = [
                    {key: bar[key] for key in ('timestamp', 'open', 'high', 'low', 'close', 'volume') if key in bar}
                    for bar in bars if isinstance(bar, dict) and all(key in bar for key in ('open', 'high', 'low', 'close'))
                ] or None
        except Exception as error:
            logger.info('GoldPriceDev OHLCV unavailable for %s: %s', symbol, error)
        return self._normalized_quote(
            symbol, quote.get('price'), provider['name'], 'goldprice_dev',
            timestamp=quote.get('timestamp') or quote.get('updated_at'),
            bid=quote.get('bid'), ask=quote.get('ask'),
            ohlcv=ohlcv,
        )

    async def _fetch_mt5(self, provider: Dict, symbol: str) -> Optional[MarketDataPoint]:
        if symbol != 'XAUUSD' or not getattr(self.system_config, 'mt5_enabled', True):
            return None
        try:
            import MetaTrader5 as mt5
        except ImportError:
            logger.info('MT5 provider unavailable: MetaTrader5 package is not installed')
            return None
        mt5_symbol = getattr(self.system_config, 'mt5_xauusd_symbol', None) or os.getenv('MT5_XAUUSD_SYMBOL', 'XAUUSD')
        if not mt5.symbol_select(mt5_symbol, True):
            return None
        tick = mt5.symbol_info_tick(mt5_symbol)
        if tick is None:
            return None
        bid = float(getattr(tick, 'bid', 0.0) or 0.0)
        ask = float(getattr(tick, 'ask', 0.0) or 0.0)
        last = float(getattr(tick, 'last', 0.0) or 0.0) or (bid + ask) / 2
        return self._normalized_quote(
            symbol, last, provider['name'], 'mt5', timestamp=getattr(tick, 'time', None),
            bid=bid, ask=ask, volume=getattr(tick, 'volume', 0.0),
        )

    async def _fetch_itick(self, provider: Dict, symbol: str) -> Optional[MarketDataPoint]:
        if symbol != 'XAUUSD':
            return None
        key = self._secret_value('ITICK_API_KEY')
        if not key:
            return None
        response = requests.get(
            f"{provider['base_url']}/forex/ticks", params={'region': 'GB', 'codes': 'XAUUSD'},
            headers={'token': key, 'Authorization': f'Bearer {key}'}, timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        payload = data.get('data', data) if isinstance(data, dict) else data
        if isinstance(payload, dict) and 'XAUUSD' in payload:
            payload = payload['XAUUSD']
        if isinstance(payload, list):
            payload = payload[0] if payload else {}
        return self._normalized_quote(
            symbol, payload.get('price') or payload.get('last') or payload.get('close') or payload.get('ld'),
            provider['name'], 'itick', timestamp=payload.get('timestamp') or payload.get('time'),
            bid=payload.get('bid'), ask=payload.get('ask'), volume=payload.get('volume', payload.get('v', 0.0)),
        )

    async def _fetch_binance(self, provider: Dict, symbol: str) -> Optional[MarketDataPoint]:
        """Fetch data from Binance API"""
        # Map symbol to Binance format
        binance_symbol = self._map_symbol_to_binance(symbol)
        
        url = f"{provider['base_url']}{provider['endpoints']['ticker']}"
        params = {'symbol': binance_symbol}
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Parse Binance response
        price = float(data['lastPrice'])
        previous_price = float(data.get('prevClosePrice', 0)) or None
        bid = float(data['bidPrice'])
        ask = float(data['askPrice'])
        volume = float(data['volume'])
        ohlcv = self._fetch_binance_ohlcv(provider, binance_symbol)
        
        # Calculate spread
        spread = ask - bid
        
        return MarketDataPoint(
            symbol=symbol,
            price=price,
            bid=bid,
            ask=ask,
            spread=spread,
            volume=volume,
            timestamp=datetime.now(timezone.utc),
            provider=provider['name'],
            source='binance',
            previous_price=previous_price,
            ohlcv=ohlcv,
        )

    def _fetch_binance_ohlcv(self, provider: Dict, symbol: str) -> Optional[List[Dict[str, float]]]:
        """Fetch observed five-minute candles when the symbol is supported."""
        response = requests.get(
            f"{provider['base_url']}{provider['endpoints']['klines']}",
            params={"symbol": symbol, "interval": "5m", "limit": 1000},
            timeout=10,
        )
        response.raise_for_status()
        candles = []
        for row in response.json():
            candles.append({
                "timestamp": datetime.fromtimestamp(float(row[0]) / 1000, timezone.utc),
                "open": float(row[1]),
                "high": float(row[2]),
                "low": float(row[3]),
                "close": float(row[4]),
                "volume": float(row[5]),
            })
        return candles or None
    
    async def _fetch_coingecko(self, provider: Dict, symbol: str) -> Optional[MarketDataPoint]:
        """Fetch data from CoinGecko API"""
        # Map symbol to CoinGecko IDs
        coingecko_id = self._map_symbol_to_coingecko(symbol)
        
        url = f"{provider['base_url']}{provider['endpoints']['simple_price']}"
        params = {
            'ids': coingecko_id,
            'vs_currencies': 'usd',
            'include_24hr_vol': 'true',
            'include_24hr_change': 'true'
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if coingecko_id not in data:
            return None
        
        price_data = data[coingecko_id]
        
        # CoinGecko provides only price, need to estimate bid/ask
        price = price_data['usd']
        change = price_data.get('usd_24h_change')
        previous_price = price / (1 + (float(change) / 100)) if change is not None and float(change) != -100 else None
        
        # Estimate bid/ask with small spread
        spread_percent = 0.001  # 0.1% spread
        bid = price * (1 - spread_percent / 2)
        ask = price * (1 + spread_percent / 2)
        
        # Volume not directly available from simple price endpoint
        volume = 0.0
        
        return MarketDataPoint(
            symbol=symbol,
            price=price,
            bid=bid,
            ask=ask,
            spread=ask - bid,
            volume=volume,
            timestamp=datetime.now(timezone.utc),
            provider=provider['name'],
            source='coingecko',
            previous_price=previous_price
        )
    
    async def _fetch_alphavantage(self, provider: Dict, symbol: str) -> Optional[MarketDataPoint]:
        """Fetch data from Alpha Vantage API"""
        # Map symbol to Alpha Vantage format
        av_symbol = self._map_symbol_to_alphavantage(symbol)
        
        url = f"{provider['base_url']}{provider['endpoints']['global_quote']}"
        params = {
            'function': 'GLOBAL_QUOTE',
            'symbol': av_symbol,
            'apikey': self._get_api_key('alphavantage')
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if 'Global Quote' not in data or not data['Global Quote']:
            return None
        
        quote = data['Global Quote']
        
        price = float(quote['05. price'])
        volume = float(quote.get('06. volume') or 0.0)
        bid = float(quote.get('08. bid price') or price * 0.999)
        ask = float(quote.get('09. ask price') or price * 1.001)
        ohlcv = self._fetch_alphavantage_ohlcv(provider, symbol)
        
        spread = ask - bid
        
        return MarketDataPoint(
            symbol=symbol,
            price=price,
            bid=bid,
            ask=ask,
            spread=spread,
            volume=volume,
            timestamp=datetime.now(timezone.utc),
            provider=provider['name'],
            source='alphavantage',
            ohlcv=ohlcv,
            data_kind='ohlcv' if ohlcv else 'spot_only',
        )
    
    def _fetch_alphavantage_ohlcv(self, provider: Dict, symbol: str) -> Optional[List[Dict[str, float]]]:
        if symbol == 'XAUUSD':
            params = {'function': 'FX_INTRADAY', 'from_symbol': 'XAU', 'to_symbol': 'USD', 'interval': '5min', 'outputsize': 'full'}
            series_name = 'Time Series FX (5min)'
        elif symbol == 'BTCUSD':
            params = {'function': 'DIGITAL_CURRENCY_INTRADAY', 'symbol': 'BTC', 'market': 'USD', 'interval': '5min', 'outputsize': 'full'}
            series_name = 'Time Series Crypto (5min)'
        else:
            return None
        params['apikey'] = self._get_api_key('alphavantage')
        response = requests.get(provider['base_url'], params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        rows = []
        for timestamp, values in (data.get(series_name) or {}).items():
            rows.append({'timestamp': timestamp, 'open': values.get('1. open'), 'high': values.get('2. high'), 'low': values.get('3. low'), 'close': values.get('4. close'), 'volume': values.get('5. volume') or 0})
        return self._normalize_ohlcv(rows, 'Alpha Vantage')

    async def _fetch_twelvedata(self, provider: Dict, symbol: str) -> Optional[MarketDataPoint]:
        """Fetch data from Twelve Data API"""
        provider_symbol = self._map_symbol_to_twelvedata(symbol)
        url = f"{provider['base_url']}{provider['endpoints']['quote']}"
        params = {
            'symbol': provider_symbol,
            'apikey': self._get_api_key('twelvedata')
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if 'code' in data and data['code'] != 200:
            return None
        
        price_data = data.get('price', data)
        
        price = float(price_data.get('close') or price_data.get('price') or 0)
        if price <= 0:
            return None
        bid = float(price_data.get('bid', price * 0.999))
        ask = float(price_data.get('ask', price * 1.001))
        volume = float(price_data.get('volume', 0))
        previous_price = price_data.get('previous_close') or price_data.get('previousClose')
        ohlcv = self._fetch_twelvedata_ohlcv(provider, provider_symbol)
        
        spread = ask - bid
        
        return MarketDataPoint(
            symbol=symbol,
            price=price,
            bid=bid,
            ask=ask,
            spread=spread,
            volume=volume,
            timestamp=datetime.now(timezone.utc),
            provider=provider['name'],
            source='twelvedata',
            previous_price=previous_price,
            ohlcv=ohlcv,
            data_kind='ohlcv' if ohlcv else 'spot_only'
        )
    
    def _fetch_twelvedata_ohlcv(self, provider: Dict, symbol: str) -> Optional[List[Dict[str, float]]]:
        response = requests.get(
            f"{provider['base_url']}{provider['endpoints']['time_series']}",
            params={'symbol': symbol, 'interval': '5min', 'outputsize': 1000,
                    'apikey': self._get_api_key('twelvedata'), 'format': 'JSON'},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        values = data.get('values', []) if isinstance(data, dict) else []
        return self._normalize_ohlcv(values, 'Twelve Data')

    async def _fetch_yahoo_finance(self, provider: Dict, symbol: str) -> Optional[MarketDataPoint]:
        """Fetch data from Yahoo Finance API"""
        # Map symbol to Yahoo Finance format
        yahoo_symbol = self._map_symbol_to_yahoo(symbol)
        
        url = f"{provider['base_url']}{provider['endpoints']['quote']}"
        params = {
            'symbols': yahoo_symbol,
            'fields': 'regularMarketPrice,regularMarketChangePercent,regularMarketVolume,regularMarketDayHigh,regularMarketDayLow,regularMarketOpen,regularMarketPreviousClose,bid,ask'
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if 'quoteResponse' not in data or not data['quoteResponse']['result']:
            return None
        
        quote = data['quoteResponse']['result'][0]
        
        price = quote.get('regularMarketPrice', 0)
        bid = quote.get('bid', price * 0.999) if quote.get('bid') else price * 0.999
        ask = quote.get('ask', price * 1.001) if quote.get('ask') else price * 1.001
        volume = quote.get('regularMarketVolume', 0)
        ohlcv = self._fetch_yahoo_ohlcv(provider, yahoo_symbol, headers)
        
        spread = ask - bid
        
        return MarketDataPoint(
            symbol=symbol,
            price=price,
            bid=bid,
            ask=ask,
            spread=spread,
            volume=volume,
            timestamp=datetime.now(timezone.utc),
            provider=provider['name'],
            source='yahoo_finance',
            previous_price=quote.get('regularMarketPreviousClose'),
            ohlcv=ohlcv,
        )

    def _fetch_yahoo_ohlcv(self, provider: Dict, symbol: str, headers: Dict) -> Optional[List[Dict[str, float]]]:
        """Fetch observed Yahoo candles; missing history is not synthesized."""
        url = f"{provider['base_url']}{provider['endpoints']['chart']}/{quote(symbol)}"
        response = requests.get(
            url,
            params={"range": "5d", "interval": "5m", "events": "history"},
            headers=headers,
            timeout=10,
        )
        response.raise_for_status()
        result = response.json().get("chart", {}).get("result", [])
        if not result:
            return None
        chart = result[0]
        timestamps = chart.get('timestamp', [])
        quote_data = (chart.get('indicators', {}).get('quote', [{}]) or [{}])[0]
        candles = []
        for index, timestamp in enumerate(timestamps):
            values = {key: (quote_data.get(key) or [None] * len(timestamps))[index] for key in ('open', 'high', 'low', 'close', 'volume')}
            if all(values[k] is not None for k in ('open','high','low','close')):
                candles.append({'timestamp': datetime.fromtimestamp(float(timestamp), timezone.utc), **{k: float(v) for k,v in values.items() if v is not None}})
        return candles or None

    def _normalize_ohlcv(self, rows: Any, provider: str) -> Optional[List[Dict[str, float]]]:
        if not isinstance(rows, list): return None
        normalized = {}; rejected = 0
        for row in rows:
            try:
                if not isinstance(row, dict): raise ValueError('row is not an object')
                raw_time = row.get('timestamp', row.get('datetime', row.get('time', row.get('t'))))
                if isinstance(raw_time, str): stamp = datetime.fromisoformat(raw_time.replace('Z', '+00:00'))
                else:
                    value = float(raw_time)
                    stamp = datetime.fromtimestamp(value / (1000 if value > 10**11 else 1), timezone.utc)
                if stamp.tzinfo is None: stamp = stamp.replace(tzinfo=timezone.utc)
                values = {key: row.get(key, row.get(alias)) for key, alias in (('open','o'),('high','h'),('low','l'),('close','c'),('volume','v'))}
                if any(values[k] is None for k in ('open','high','low','close')): raise ValueError('missing OHLC')
                ohlc = {k: float(values[k]) for k in ('open','high','low','close')}; volume = float(values['volume'] or 0.0)
                if not all(math.isfinite(x) for x in (*ohlc.values(), volume)): raise ValueError('non-finite value')
                if min(ohlc.values()) <= 0 or ohlc['high'] < max(ohlc['open'], ohlc['close']) or ohlc['low'] > min(ohlc['open'], ohlc['close']): raise ValueError('invalid OHLC range')
                normalized[stamp] = {'timestamp': stamp, **ohlc, 'volume': volume}
            except (TypeError, ValueError, OverflowError): rejected += 1
        candles = [normalized[k] for k in sorted(normalized)]
        logger.info('%s OHLCV normalization: raw=%d valid=%d rejected=%d', provider, len(rows), len(candles), rejected)
        return candles or None

    def _map_symbol_to_twelvedata(self, symbol: str) -> str:
        return {'BTCUSD': 'BTC/USD', 'XAUUSD': 'XAU/USD'}.get(symbol, symbol)

    def _provider_names_for_symbol(self, symbol: str) -> List[str]:
        if symbol != 'XAUUSD':
            return [name for name in self.providers if name in {'binance', 'coingecko', 'alphavantage', 'twelvedata', 'yahoo_finance'}]
        configured = getattr(self.system_config, 'xauusd_data_providers', None) or os.getenv(
            'XAUUSD_DATA_PROVIDERS', 'goldprice_dev,goldapi,mt5,itick'
        )
        priority = getattr(self.system_config, 'xauusd_provider_priority', None) or os.getenv(
            'XAUUSD_PROVIDER_PRIORITY', 'goldprice_dev,mt5,goldapi,itick'
        )
        enabled = {
            'goldapi': getattr(self.system_config, 'goldapi_enabled', True),
            'goldprice_dev': getattr(self.system_config, 'goldprice_dev_enabled', True),
            'mt5': getattr(self.system_config, 'mt5_enabled', True),
            'itick': getattr(self.system_config, 'itick_enabled', True),
        }
        selected = [name.strip() for name in configured.split(',') if name.strip() in self.providers and enabled.get(name, True)]
        ordered = [name.strip() for name in priority.split(',') if name.strip() in selected]
        result = ordered + [name for name in selected if name not in ordered]
        return list(dict.fromkeys(result))
        timestamps = chart.get("timestamp", [])
        quote_data = (chart.get("indicators", {}).get("quote", [{}]) or [{}])[0]
        candles = []
        for index, timestamp in enumerate(timestamps):
            values = {
                key: (quote_data.get(key) or [None] * len(timestamps))[index]
                for key in ("open", "high", "low", "close", "volume")
            }
            if all(values[key] is not None for key in ("open", "high", "low", "close")):
                candles.append({
                    "timestamp": datetime.fromtimestamp(float(timestamp), timezone.utc),
                    **{key: float(value) for key, value in values.items() if value is not None},
                })
        return candles or None
    
    def _validate_and_consensus(self, symbol: str, provider_data: Dict[str, MarketDataPoint]) -> PriceValidationResult:
        """Validate data and calculate consensus price"""
        logger.info(f"Validating market data for {symbol} from {len(provider_data)} providers")
        
        if not provider_data:
            raise ValueError(f"No provider data available for {symbol}")
        
        # Extract prices from all providers
        prices = {}
        valid_data = {}
        stale_providers = []
        outlier_providers = []
        
        for provider_name, data_point in provider_data.items():
            # Check if data is stale (older than 1 minute)
            if self._is_data_stale(data_point):
                logger.warning(f"Data from {provider_name} for {symbol} is stale")
                stale_providers.append(provider_name)
                continue

            if not math.isfinite(float(data_point.price)) or data_point.price <= 0:
                logger.warning(f"Data from {provider_name} for {symbol} has an invalid price")
                continue
            
            # Check for outliers
            if self._is_outlier(data_point, prices):
                logger.warning(f"Data from {provider_name} for {symbol} is an outlier")
                outlier_providers.append(provider_name)
                continue
            
            prices[provider_name] = data_point.price
            valid_data[provider_name] = data_point
        
        if not valid_data:
            raise ValueError(f"DATA UNAVAILABLE: all provider data for {symbol} was stale or invalid")
        
        # Calculate consensus price (weighted average)
        if getattr(self.system_config, 'price_consensus_method', 'median') == 'median':
            consensus_price = float(median(prices.values()))
        else:
            consensus_price = self._calculate_consensus_price(prices)
        
        # Calculate consensus bid/ask (weighted average of bid/ask)
        consensus_bid = self._calculate_consensus_bid_ask(valid_data, 'bid')
        consensus_ask = self._calculate_consensus_bid_ask(valid_data, 'ask')
        consensus_spread = consensus_ask - consensus_bid
        
        # Calculate consensus volume (weighted average)
        consensus_volume = self._calculate_consensus_volume(valid_data)
        
        # Calculate validation confidence
        confidence_score = self._calculate_validation_confidence(
            valid_data, outlier_providers, len(self._provider_names_for_symbol(symbol))
        )
        previous_prices = {
            name: data.previous_price for name, data in valid_data.items()
            if data.previous_price is not None and math.isfinite(float(data.previous_price)) and data.previous_price > 0
        }
        previous_price = float(median(previous_prices.values())) if previous_prices else None
        
        ohlcv_provider = max((name for name, point in valid_data.items() if point.ohlcv), key=lambda name: len(valid_data[name].ohlcv or []), default=None)
        ohlcv = valid_data[ohlcv_provider].ohlcv if ohlcv_provider else None

        return PriceValidationResult(
            symbol=symbol,
            consensus_price=consensus_price,
            consensus_bid=consensus_bid,
            consensus_ask=consensus_ask,
            consensus_spread=consensus_spread,
            consensus_volume=consensus_volume,
            provider_prices=prices,
            outlier_providers=outlier_providers,
            stale_providers=stale_providers,
            validation_timestamp=datetime.now(timezone.utc),
            confidence_score=confidence_score,
            previous_price=previous_price,
            ohlcv=ohlcv,
            ohlcv_provider=ohlcv_provider,
            provider_count=len(self._provider_names_for_symbol(symbol)),
            valid_provider_count=len(valid_data),
            provider_status={
                name: ('valid_ohlcv' if name in valid_data and valid_data[name].ohlcv else 'valid_spot_only' if name in valid_data else 'stale' if name in stale_providers
                       else 'outlier' if name in outlier_providers else 'invalid')
                for name in self._provider_names_for_symbol(symbol)
                if name in provider_data
            } | {
                name: 'unavailable'
                for name in self._provider_names_for_symbol(symbol)
                if name not in provider_data
            },
            execution_reference_price=prices.get("mt5"),
        )
    
    def _is_data_stale(self, data_point: MarketDataPoint) -> bool:
        """Check if data is stale (older than 1 minute)"""
        age = datetime.now(timezone.utc) - data_point.timestamp
        threshold = getattr(self.system_config, 'xau_max_stale_seconds', 60) if data_point.symbol == 'XAUUSD' else 60
        return age.total_seconds() > threshold
    
    def _is_outlier(self, data_point: MarketDataPoint, prices: Dict[str, float]) -> bool:
        """Check if data point is an outlier"""
        if not prices:
            return False
        
        current_price = data_point.price
        max_deviation = getattr(self.system_config, 'max_price_deviation_percent', 1.0)
        reference = float(median(prices.values()))
        if reference > 0 and abs(current_price - reference) / reference * 100 > max_deviation:
            return True
        
        return False
    
    def _calculate_consensus_price(self, prices: Dict[str, float]) -> float:
        """Calculate weighted consensus price"""
        if not prices:
            return 0.0
        
        # Weight by provider priority and health
        weighted_sum = 0.0
        total_weight = 0.0
        
        for provider_name, price in prices.items():
            provider = self.providers.get(provider_name, {})
            weight = provider.get('weight', 1.0)
            
            # Adjust weight based on provider health
            health = self.provider_health.get(provider_name, {})
            if health.get('is_healthy', True):
                health_factor = 1.0
            else:
                health_factor = 0.5
            
            adjusted_weight = weight * health_factor
            weighted_sum += price * adjusted_weight
            total_weight += adjusted_weight
        
        if total_weight == 0:
            return sum(prices.values()) / len(prices)
        
        return weighted_sum / total_weight
    
    def _calculate_consensus_bid_ask(self, valid_data: Dict[str, MarketDataPoint], bid_ask: str) -> float:
        """Calculate consensus bid or ask price"""
        if not valid_data:
            return 0.0
        
        values = []
        for data_point in valid_data.values():
            if bid_ask == 'bid':
                values.append(data_point.bid)
            else:
                values.append(data_point.ask)
        
        if not values:
            return 0.0
        
        return sum(values) / len(values)
    
    def _calculate_consensus_volume(self, valid_data: Dict[str, MarketDataPoint]) -> float:
        """Calculate consensus volume"""
        if not valid_data:
            return 0.0
        
        volumes = [data_point.volume for data_point in valid_data.values()]
        return sum(volumes) / len(volumes)
    
    def _calculate_validation_confidence(self, valid_data: Dict[str, MarketDataPoint],
                                        outlier_providers: List[str], provider_total: int = None) -> float:
        """Calculate confidence score for validation"""
        if not valid_data:
            return 0.0
        
        # Base confidence on number of valid providers
        provider_total = provider_total or len(self.providers)
        base_confidence = min(len(valid_data) / provider_total, 1.0)
        
        # Adjust based on outlier providers
        outlier_penalty = min(len(outlier_providers) / provider_total, 0.5)
        
        # Adjust based on provider health
        healthy_providers = sum(1 for name in valid_data.keys() 
                               if self.provider_health.get(name, {}).get('is_healthy', True))
        health_factor = healthy_providers / len(valid_data) if valid_data else 0
        
        confidence = base_confidence * (1 - outlier_penalty) * health_factor
        
        return max(0.0, min(1.0, confidence))
    
    def _update_provider_health(self, provider_name: str, success: bool) -> None:
        """Update provider health status"""
        if provider_name not in self.provider_health:
            return
        
        health = self.provider_health[provider_name]
        health['total_requests'] += 1
        
        if success:
            health['successful_requests'] += 1
            health['consecutive_failures'] = 0
            health['last_success'] = datetime.now(timezone.utc)
        else:
            health['consecutive_failures'] += 1
            health['last_failure'] = datetime.now(timezone.utc)
            health['error_count'] += 1
        
        # Update health status
        if health['consecutive_failures'] >= 3:
            health['is_healthy'] = False
        else:
            health['is_healthy'] = True
        
        # Calculate success rate
        if health['total_requests'] > 0:
            success_rate = health['successful_requests'] / health['total_requests']
            health['success_rate'] = success_rate
    
    def _update_provider_response_time(self, provider_name: str, response_time: float) -> None:
        """Update provider response time"""
        if provider_name not in self.provider_health:
            return
        
        health = self.provider_health[provider_name]
        
        # Update average response time (exponential moving average)
        if health['average_response_time'] == 0:
            health['average_response_time'] = response_time
        else:
            health['average_response_time'] = (
                health['average_response_time'] * 0.9 + response_time * 0.1
            )
    
    def _cache_validation_result(self, symbol: str, result: PriceValidationResult) -> None:
        """Cache validation result"""
        self.validation_cache[symbol] = result
        
        # Keep only recent cache entries
        current_time = datetime.now(timezone.utc)
        stale_keys = []
        
        for cached_symbol, cached_result in self.validation_cache.items():
            age = current_time - cached_result.validation_timestamp
            if age.total_seconds() > 300:  # 5 minutes
                stale_keys.append(cached_symbol)
        
        for key in stale_keys:
            del self.validation_cache[key]
    
    def get_cached_validation(self, symbol: str) -> Optional[PriceValidationResult]:
        """Get cached validation result if recent"""
        if symbol not in self.validation_cache:
            return None
        
        result = self.validation_cache[symbol]
        age = datetime.now(timezone.utc) - result.validation_timestamp
        
        if age.total_seconds() <= 60:  # 1 minute cache
            return result
        
        return None
    
    def _map_symbol_to_binance(self, symbol: str) -> str:
        """Map symbol to Binance format"""
        mapping = {
            'BTCUSD': 'BTCUSDT',
            'XAUUSD': 'XAUUSDT'
        }
        return mapping.get(symbol, symbol)
    
    def _map_symbol_to_coingecko(self, symbol: str) -> str:
        """Map symbol to CoinGecko ID"""
        mapping = {
            'BTCUSD': 'bitcoin',
            'XAUUSD': 'gold'
        }
        return mapping.get(symbol, symbol.lower())
    
    def _map_symbol_to_alphavantage(self, symbol: str) -> str:
        """Map symbol to Alpha Vantage format"""
        mapping = {
            'BTCUSD': 'BTC',
            'XAUUSD': 'GOLD'
        }
        return mapping.get(symbol, symbol)
    
    def _map_symbol_to_yahoo(self, symbol: str) -> str:
        """Map symbol to Yahoo Finance format"""
        mapping = {
            'BTCUSD': 'BTC-USD',
            'XAUUSD': 'XAU-USD'
        }
        return mapping.get(symbol, symbol)
    
    def _get_api_key(self, provider_name: str) -> str:
        """Get API key for provider"""
        api_keys = {
            'alphavantage': 'ALPHAVANTAGE_API_KEY',
            'twelvedata': 'TWELVEDATA_API_KEY'
        }
        env_name = api_keys.get(provider_name)
        return self._secret_value(env_name) if env_name else ''

    @staticmethod
    def _secret_value(name: Optional[str]) -> str:
        if not name:
            return ''
        return os.getenv(name, '')

    @classmethod
    def _secret_available(cls, name: Optional[str]) -> bool:
        return bool(cls._secret_value(name))

    def get_provider_status(self) -> Dict[str, str]:
        """Return configured/available status without contacting providers."""
        status = {}
        for name, provider in self.providers.items():
            if requests is None:
                status[name] = "unavailable: requests dependency missing"
            elif provider.get('required_key') and not self._secret_available(provider['required_key']):
                status[name] = f"unavailable: missing {provider['required_key']}"
            elif name == 'mt5':
                try:
                    import MetaTrader5  # noqa: F401
                    status[name] = "configured"
                except ImportError:
                    status[name] = "unavailable: MetaTrader5 package missing"
            else:
                status[name] = "configured"
        return status

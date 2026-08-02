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
import requests
import random

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

class MarketDataAggregator:
    """Multi-source market data aggregation with price validation"""
    
    def __init__(self, config_file: str = "app_config.json"):
        self.config_file = config_file
        self.providers = {}
        self.provider_configs = {}
        self.price_history = {}
        self.validation_cache = {}
        self.last_successful_fetch = {}
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
            'weight': 0.7
        }
        
        # Twelve Data API (BTCUSD, XAUUSD, technical indicators)
        self.providers['twelvedata'] = {
            'name': 'Twelve Data',
            'base_url': 'https://api.twelvedata.com/v1',
            'endpoints': {
                'time_series': '/time_series',
                'quote': '/quote'
            },
            'priority': 4,
            'weight': 0.7
        }
        
        # Yahoo Finance API (community validation)
        self.providers['yahoo_finance'] = {
            'name': 'Yahoo Finance',
            'base_url': 'https://query1.finance.yahoo.com/v8',
            'endpoints': {
                'quote': '/quote',
                'chart': '/chart'
            },
            'priority': 5,
            'weight': 0.6
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
            }
    
    async def fetch_market_data(self, symbol: str) -> PriceValidationResult:
        """Fetch market data from all providers and validate"""
        logger.info(f"Fetching market data for {symbol} from all providers")
        
        # Fetch data from all providers
        provider_data = {}
        for provider_name in self.providers:
            try:
                data = await self._fetch_from_provider(provider_name, symbol)
                if data:
                    provider_data[provider_name] = data
                    self._update_provider_health(provider_name, True)
                else:
                    self._update_provider_health(provider_name, False)
            except Exception as e:
                logger.error(f"Provider {provider_name} failed for {symbol}: {e}")
                self._update_provider_health(provider_name, False)
        
        if not provider_data:
            raise Exception(f"No market data available for {symbol} from any provider")
        
        # Validate and calculate consensus
        validation_result = self._validate_and_consensus(symbol, provider_data)
        
        # Cache the result
        self._cache_validation_result(symbol, validation_result)
        
        return validation_result
    
    async def _fetch_from_provider(self, provider_name: str, symbol: str) -> Optional[MarketDataPoint]:
        """Fetch data from a specific provider"""
        provider = self.providers[provider_name]
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
            else:
                return None
            
            response_time = time.time() - start_time
            self._update_provider_response_time(provider_name, response_time)
            
            return data
            
        except Exception as e:
            logger.error(f"Error fetching from {provider_name}: {e}")
            return None
    
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
        bid = float(data['bidPrice'])
        ask = float(data['askPrice'])
        volume = float(data['volume'])
        
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
            source='binance'
        )
    
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
            source='coingecko'
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
        bid = float(quote['06. bid price']) if quote['06. bid price'] != '0.0' else price * 0.999
        ask = float(quote['07. ask price']) if quote['07. ask price'] != '0.0' else price * 1.001
        volume = float(quote['06. volume']) if quote['06. volume'] != '0.0' else 0.0
        
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
            source='alphavantage'
        )
    
    async def _fetch_twelvedata(self, provider: Dict, symbol: str) -> Optional[MarketDataPoint]:
        """Fetch data from Twelve Data API"""
        url = f"{provider['base_url']}{provider['endpoints']['quote']}"
        params = {
            'symbol': symbol,
            'apikey': self._get_api_key('twelvedata')
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if 'code' in data and data['code'] != 200:
            return None
        
        price_data = data.get('price', {})
        
        price = float(price_data.get('close', 0))
        bid = float(price_data.get('bid', price * 0.999))
        ask = float(price_data.get('ask', price * 1.001))
        volume = float(price_data.get('volume', 0))
        
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
            source='twelvedata'
        )
    
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
            source='yahoo_finance'
        )
    
    def _validate_and_consensus(self, symbol: str, provider_data: Dict[str, MarketDataPoint]) -> PriceValidationResult:
        """Validate data and calculate consensus price"""
        logger.info(f"Validating market data for {symbol} from {len(provider_data)} providers")
        
        if not provider_data:
            raise ValueError(f"No provider data available for {symbol}")
        
        # Extract prices from all providers
        prices = {}
        valid_data = {}
        
        for provider_name, data_point in provider_data.items():
            # Check if data is stale (older than 1 minute)
            if self._is_data_stale(data_point):
                logger.warning(f"Data from {provider_name} for {symbol} is stale")
                continue
            
            # Check for outliers
            if self._is_outlier(data_point, prices):
                logger.warning(f"Data from {provider_name} for {symbol} is an outlier")
                continue
            
            prices[provider_name] = data_point.price
            valid_data[provider_name] = data_point
        
        if not valid_data:
            # If all data is invalid, use the most recent valid data
            logger.warning(f"All provider data for {symbol} is invalid, using most recent")
            latest_data = max(provider_data.values(), key=lambda x: x.timestamp)
            prices = {list(provider_data.keys())[0]: latest_data.price}
            valid_data = {list(provider_data.keys())[0]: latest_data}
        
        # Calculate consensus price (weighted average)
        consensus_price = self._calculate_consensus_price(prices)
        
        # Calculate consensus bid/ask (weighted average of bid/ask)
        consensus_bid = self._calculate_consensus_bid_ask(valid_data, 'bid')
        consensus_ask = self._calculate_consensus_bid_ask(valid_data, 'ask')
        consensus_spread = consensus_ask - consensus_bid
        
        # Calculate consensus volume (weighted average)
        consensus_volume = self._calculate_consensus_volume(valid_data)
        
        # Identify outlier and stale providers
        outlier_providers = list(set(provider_data.keys()) - set(valid_data.keys()))
        
        # Calculate validation confidence
        confidence_score = self._calculate_validation_confidence(valid_data, outlier_providers)
        
        return PriceValidationResult(
            symbol=symbol,
            consensus_price=consensus_price,
            consensus_bid=consensus_bid,
            consensus_ask=consensus_ask,
            consensus_spread=consensus_spread,
            consensus_volume=consensus_volume,
            provider_prices=prices,
            outlier_providers=outlier_providers,
            stale_providers=[],  # Would need timestamp comparison
            validation_timestamp=datetime.now(timezone.utc),
            confidence_score=confidence_score
        )
    
    def _is_data_stale(self, data_point: MarketDataPoint) -> bool:
        """Check if data is stale (older than 1 minute)"""
        age = datetime.now(timezone.utc) - data_point.timestamp
        return age.total_seconds() > 60
    
    def _is_outlier(self, data_point: MarketDataPoint, prices: Dict[str, float]) -> bool:
        """Check if data point is an outlier"""
        if not prices:
            return False
        
        current_price = data_point.price
        
        # Calculate mean and standard deviation
        mean_price = sum(prices.values()) / len(prices)
        variance = sum((p - mean_price) ** 2 for p in prices.values()) / len(prices)
        std_dev = variance ** 0.5
        
        # Check if current price is more than 2 standard deviations from mean
        if std_dev > 0:
            z_score = abs(current_price - mean_price) / std_dev
            return z_score > 2.0
        
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
                                        outlier_providers: List[str]) -> float:
        """Calculate confidence score for validation"""
        if not valid_data:
            return 0.0
        
        # Base confidence on number of valid providers
        base_confidence = min(len(valid_data) / len(self.providers), 1.0)
        
        # Adjust based on outlier providers
        outlier_penalty = min(len(outlier_providers) / len(self.providers), 0.5)
        
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
        # In production, this would read from environment variables or config file
        api_keys = {
            'alphavantage': 'YOUR_ALPHA_VANTAGE_API_KEY',
            'twelvedata': 'YOUR_TWELVE_DATA_API_KEY'
        }
        return api_keys.get(provider_name, '')
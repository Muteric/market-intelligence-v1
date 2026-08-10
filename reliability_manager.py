"""
Reliability Manager for AI Trading Intelligence Bot
Manages retry logic, caching, rate limits, and fallback mechanisms for high availability.
"""

import asyncio
import time
import random
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class RetryStrategy(Enum):
    """Retry strategies"""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    CONSTANT = "constant"
    FIBONACCI = "fibonacci"

class CacheStrategy(Enum):
    """Cache strategies"""
    LRU = "lru"
    TTL = "ttl"
    ADAPTIVE = "adaptive"

@dataclass
class RetryConfig:
    """Retry configuration"""
    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0
    retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    retry_on_errors: List[str] = field(default_factory=lambda: ["unknown", "timeout", "connection_error", "rate_limit"])

@dataclass
class CacheEntry:
    """Cache entry"""
    key: str
    value: Any
    timestamp: datetime
    ttl: int
    access_count: int
    last_access: datetime

@dataclass
class RateLimitConfig:
    """Rate limit configuration"""
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    requests_per_day: int = 10000
    burst_capacity: int = 10

@dataclass
class FallbackConfig:
    """Fallback configuration"""
    enable_fallback: bool = True
    fallback_providers: List[str] = field(default_factory=list)
    fallback_timeout: float = 5.0
    degrade_gracefully: bool = True

@dataclass
class HealthStatus:
    """Health status for a component"""
    component: str
    status: str  # healthy, degraded, unhealthy
    last_check: datetime
    consecutive_failures: int
    total_requests: int
    successful_requests: int
    average_response_time: float
    error_rate: float

class ReliabilityManager:
    """Comprehensive reliability management for trading system"""
    
    def __init__(self, config_file: str = "app_config.json"):
        self.config_file = config_file
        self.retry_configs: Dict[str, RetryConfig] = {}
        self.cache_entries: Dict[str, CacheEntry] = {}
        self.rate_limits: Dict[str, RateLimitConfig] = {}
        self.fallback_configs: Dict[str, FallbackConfig] = {}
        self.health_status: Dict[str, HealthStatus] = {}
        self.request_history: List[Dict[str, Any]] = []
        self.cache_stats: Dict[str, Any] = {}
        
        self._initialize_configs()
        self._initialize_health_checks()
    
    def _initialize_configs(self) -> None:
        """Initialize reliability configurations"""
        # Market data aggregator retry config
        self.retry_configs['market_data'] = RetryConfig(
            max_retries=5,
            initial_delay=0.5,
            max_delay=30.0,
            backoff_multiplier=2.0,
            retry_strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            retry_on_errors=['timeout', 'connection_error', 'rate_limit']
        )
        
        # Signal engine retry config
        self.retry_configs['signal_engine'] = RetryConfig(
            max_retries=3,
            initial_delay=1.0,
            max_delay=15.0,
            backoff_multiplier=1.5,
            retry_strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            retry_on_errors=['calculation_error', 'insufficient_data']
        )
        
        # Telegram formatter retry config
        self.retry_configs['telegram'] = RetryConfig(
            max_retries=2,
            initial_delay=2.0,
            max_delay=10.0,
            backoff_multiplier=1.5,
            retry_strategy=RetryStrategy.LINEAR_BACKOFF,
            retry_on_errors=['network_error', 'api_error']
        )
        
        # Rate limits
        self.rate_limits['market_data'] = RateLimitConfig(
            requests_per_minute=120,
            requests_per_hour=3600,
            requests_per_day=10000,
            burst_capacity=20
        )
        
        self.rate_limits['signal_engine'] = RateLimitConfig(
            requests_per_minute=60,
            requests_per_hour=1800,
            requests_per_day=5000,
            burst_capacity=10
        )
        
        # Fallback configurations
        self.fallback_configs['market_data'] = FallbackConfig(
            enable_fallback=True,
            fallback_providers=['binance', 'coingecko', 'yahoo_finance'],
            fallback_timeout=5.0,
            degrade_gracefully=True
        )
        
        self.fallback_configs['signal_engine'] = FallbackConfig(
            enable_fallback=True,
            fallback_providers=['conservative', 'aggressive'],
            fallback_timeout=2.0,
            degrade_gracefully=True
        )
    
    def _initialize_health_checks(self) -> None:
        """Initialize health checks for all components"""
        components = ['market_data', 'signal_engine', 'telegram', 'portfolio', 'risk']
        
        for component in components:
            self.health_status[component] = HealthStatus(
                component=component,
                status='healthy',
                last_check=datetime.now(timezone.utc),
                consecutive_failures=0,
                total_requests=0,
                successful_requests=0,
                average_response_time=0.0,
                error_rate=0.0
            )
    
    async def execute_with_reliability(self, component: str, func, *args, **kwargs) -> Any:
        """Execute a function with reliability features"""
        start_time = time.time()
        
        # Update health status
        if component not in self.health_status:
            self.health_status[component] = HealthStatus(
                component=component,
                status='healthy',
                last_check=datetime.now(timezone.utc),
                consecutive_failures=0,
                total_requests=0,
                successful_requests=0,
                average_response_time=0.0,
                error_rate=0.0
            )
        
        health = self.health_status[component]
        health.total_requests += 1
        
        try:
            # Check rate limits
            if not self._check_rate_limit(component):
                raise Exception(f"Rate limit exceeded for {component}")
            
            # Check cache
            cache_key = self._generate_cache_key(component, args, kwargs)
            cached_result = self._get_from_cache(cache_key)
            if cached_result is not None:
                health.successful_requests += 1
                return cached_result
            
            # Execute with retry logic
            result = await self._execute_with_retry(component, func, *args, **kwargs)
            
            # Cache the result
            self._cache_result(cache_key, result)
            
            # Update health status
            response_time = time.time() - start_time
            self._update_health_status(component, True, response_time)
            
            return result
            
        except Exception as e:
            # Update health status
            response_time = time.time() - start_time
            self._update_health_status(component, False, response_time)
            
            # Try fallback if available
            fallback_config = self.fallback_configs.get(component, FallbackConfig())
            if fallback_config.enable_fallback and fallback_config.fallback_providers:
                try:
                    result = await self._execute_with_fallback(component, func, *args, **kwargs)
                    return result
                except Exception as fallback_error:
                    logger.error(f"Fallback also failed for {component}: {fallback_error}")
            
            raise e
    
    async def _execute_with_retry(self, component: str, func, *args, **kwargs) -> Any:
        """Execute function with retry logic"""
        retry_config = self.retry_configs.get(component, RetryConfig())
        
        for attempt in range(retry_config.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if attempt == retry_config.max_retries:
                    raise e
                
                # Check if error should trigger retry
                error_type = self._categorize_error(e)
                if error_type not in (retry_config.retry_on_errors or []):
                    raise e
                
                # Calculate delay
                delay = self._calculate_retry_delay(retry_config, attempt)
                
                logger.warning(f"Attempt {attempt + 1} failed for {component}, retrying in {delay:.2f}s: {e}")
                await asyncio.sleep(delay)
    
    async def _execute_with_fallback(self, component: str, func, *args, **kwargs) -> Any:
        """Execute function with fallback logic"""
        fallback_config = self.fallback_configs.get(component, FallbackConfig())
        
        # Try fallback providers
        for fallback_provider in (fallback_config.fallback_providers or []):
            try:
                # Modify function to use fallback provider
                modified_func = self._create_fallback_function(func, fallback_provider)
                return await modified_func(*args, **kwargs)
            except Exception as e:
                logger.warning(f"Fallback provider {fallback_provider} failed: {e}")
                continue
        
        # If all fallbacks fail, raise original error
        raise Exception(f"All fallback providers failed for {component}")
    
    def _check_rate_limit(self, component: str) -> bool:
        """Check if rate limit is exceeded"""
        rate_limit = self.rate_limits.get(component, RateLimitConfig())
        
        # Get recent requests
        now = datetime.now(timezone.utc)
        one_minute_ago = now - timedelta(minutes=1)
        one_hour_ago = now - timedelta(hours=1)
        one_day_ago = now - timedelta(days=1)
        
        recent_requests = [
            req for req in self.request_history
            if req['component'] == component and req['timestamp'] > one_minute_ago
        ]
        
        if len(recent_requests) >= rate_limit.requests_per_minute:
            return False
        
        recent_requests = [
            req for req in self.request_history
            if req['component'] == component and req['timestamp'] > one_hour_ago
        ]
        
        if len(recent_requests) >= rate_limit.requests_per_hour:
            return False
        
        recent_requests = [
            req for req in self.request_history
            if req['component'] == component and req['timestamp'] > one_day_ago
        ]
        
        if len(recent_requests) >= rate_limit.requests_per_day:
            return False
        
        return True
    
    def _generate_cache_key(self, component: str, args: tuple, kwargs: dict) -> str:
        """Generate cache key for function call"""
        # Create a deterministic key from component, args, and kwargs
        key_parts = [component]
        
        for arg in args:
            if isinstance(arg, (str, int, float, bool)):
                key_parts.append(str(arg))
            elif isinstance(arg, dict):
                key_parts.append(json.dumps(arg, sort_keys=True))
            else:
                # For complex objects, use their string representation
                key_parts.append(str(arg))
        
        for key, value in sorted(kwargs.items()):
            if isinstance(value, (str, int, float, bool)):
                key_parts.append(f"{key}={value}")
            elif isinstance(value, dict):
                key_parts.append(f"{key}={json.dumps(value, sort_keys=True)}")
            else:
                key_parts.append(f"{key}={str(value)}")
        
        return "|".join(key_parts)
    
    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """Get result from cache if available and not expired"""
        if cache_key not in self.cache_entries:
            return None
        
        cache_entry = self.cache_entries[cache_key]
        
        # Check if expired
        now = datetime.now(timezone.utc)
        age = (now - cache_entry.timestamp).total_seconds()
        
        if age > cache_entry.ttl:
            del self.cache_entries[cache_key]
            return None
        
        # Update access count
        cache_entry.access_count += 1
        cache_entry.last_access = now
        
        return cache_entry.value
    
    def _cache_result(self, cache_key: str, result: Any) -> None:
        """Cache result with TTL"""
        # Determine TTL based on component and result
        ttl = self._determine_ttl(cache_key, result)
        
        cache_entry = CacheEntry(
            key=cache_key,
            value=result,
            timestamp=datetime.now(timezone.utc),
            ttl=ttl,
            access_count=1,
            last_access=datetime.now(timezone.utc)
        )
        
        self.cache_entries[cache_key] = cache_entry
        
        # Update cache stats
        if 'cache_stats' not in self.cache_stats:
            self.cache_stats = {
                'hits': 0,
                'misses': 0,
                'evictions': 0,
                'size': 0
            }
        
        self.cache_stats['size'] += 1
    
    def _determine_ttl(self, cache_key: str, result: Any) -> int:
        """Determine TTL for cache entry"""
        # Base TTL
        base_ttl = 300  # 5 minutes
        
        # Adjust based on component
        if 'market_data' in cache_key:
            return 60  # 1 minute for market data
        elif 'signal' in cache_key:
            return 120  # 2 minutes for signals
        elif 'portfolio' in cache_key:
            return 300  # 5 minutes for portfolio data
        else:
            return base_ttl
    
    def _calculate_retry_delay(self, retry_config: RetryConfig, attempt: int) -> float:
        """Calculate retry delay based on strategy"""
        if retry_config.retry_strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = retry_config.initial_delay * (retry_config.backoff_multiplier ** attempt)
        elif retry_config.retry_strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = retry_config.initial_delay * (attempt + 1)
        elif retry_config.retry_strategy == RetryStrategy.FIBONACCI:
            # Fibonacci sequence
            fib_sequence = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55]
            if attempt < len(fib_sequence):
                delay = retry_config.initial_delay * fib_sequence[attempt]
            else:
                delay = retry_config.initial_delay * 55
        else:  # CONSTANT
            delay = retry_config.initial_delay
        
        # Cap at max delay
        return min(delay, retry_config.max_delay)
    
    def _categorize_error(self, error: Exception) -> str:
        """Categorize error for retry logic"""
        error_str = str(error).lower()
        
        if 'timeout' in error_str or 'timed out' in error_str:
            return 'timeout'
        elif 'connection' in error_str or 'network' in error_str:
            return 'connection_error'
        elif 'rate limit' in error_str or 'rate_limit' in error_str:
            return 'rate_limit'
        elif 'calculation' in error_str or 'insufficient' in error_str:
            return 'calculation_error'
        elif 'api' in error_str or 'telegram' in error_str:
            return 'api_error'
        else:
            return 'unknown'
    
    def _create_fallback_function(self, func, fallback_provider: str):
        """Create a fallback function that uses a different provider"""
        # This is a simplified implementation
        # In production, this would be more sophisticated
        async def fallback_wrapper(*args, **kwargs):
            # Modify kwargs to use fallback provider
            kwargs['fallback_provider'] = fallback_provider
            return await func(*args, **kwargs)
        
        return fallback_wrapper
    
    def _update_health_status(self, component: str, success: bool, response_time: float) -> None:
        """Update health status for a component"""
        if component not in self.health_status:
            return
        
        health = self.health_status[component]
        health.last_check = datetime.now(timezone.utc)
        
        if success:
            health.consecutive_failures = 0
            health.successful_requests += 1
        else:
            health.consecutive_failures += 1
        
        # Update average response time (exponential moving average)
        if health.average_response_time == 0:
            health.average_response_time = response_time
        else:
            health.average_response_time = (
                health.average_response_time * 0.9 + response_time * 0.1
            )
        
        # Calculate error rate
        if health.total_requests > 0:
            health.error_rate = 1.0 - (health.successful_requests / health.total_requests)
        
        # Update status based on consecutive failures
        if health.consecutive_failures >= 3:
            health.status = 'unhealthy'
        elif health.consecutive_failures >= 1:
            health.status = 'degraded'
        else:
            health.status = 'healthy'
    
    def log_request(self, component: str, success: bool, response_time: float, error: str = None) -> None:
        """Log a request for monitoring"""
        request_record = {
            'component': component,
            'timestamp': datetime.now(timezone.utc),
            'success': success,
            'response_time': response_time,
            'error': error
        }
        
        self.request_history.append(request_record)
        
        # Keep only recent history (last 24 hours)
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
        self.request_history = [
            req for req in self.request_history
            if req['timestamp'] > cutoff_time
        ]
    
    def get_health_report(self) -> Dict[str, Any]:
        """Get comprehensive health report"""
        report = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'components': {},
            'overall_status': 'healthy',
            'cache_stats': self.cache_stats,
            'rate_limit_stats': self._get_rate_limit_stats()
        }
        
        for component, health in self.health_status.items():
            report['components'][component] = {
                'status': health.status,
                'last_check': health.last_check.isoformat(),
                'consecutive_failures': health.consecutive_failures,
                'total_requests': health.total_requests,
                'successful_requests': health.successful_requests,
                'error_rate': health.error_rate,
                'average_response_time': health.average_response_time
            }
        
        # Determine overall status
        unhealthy_components = [
            comp for comp, health in self.health_status.items()
            if health.status == 'unhealthy'
        ]
        
        if unhealthy_components:
            report['overall_status'] = 'unhealthy'
        elif any(health.status == 'degraded' for health in self.health_status.values()):
            report['overall_status'] = 'degraded'
        
        return report
    
    def _get_rate_limit_stats(self) -> Dict[str, Any]:
        """Get rate limit statistics"""
        stats = {}
        
        for component, rate_limit in self.rate_limits.items():
            # Calculate current rate
            now = datetime.now(timezone.utc)
            one_minute_ago = now - timedelta(minutes=1)
            
            recent_requests = [
                req for req in self.request_history
                if req['component'] == component and req['timestamp'] > one_minute_ago
            ]
            
            stats[component] = {
                'requests_last_minute': len(recent_requests),
                'requests_per_minute_limit': rate_limit.requests_per_minute,
                'utilization_rate': len(recent_requests) / rate_limit.requests_per_minute if rate_limit.requests_per_minute > 0 else 0
            }
        
        return stats
    
    def cleanup_expired_cache(self) -> None:
        """Clean up expired cache entries"""
        now = datetime.now(timezone.utc)
        expired_keys = []
        
        for key, entry in self.cache_entries.items():
            age = (now - entry.timestamp).total_seconds()
            if age > entry.ttl:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.cache_entries[key]
        
        if expired_keys:
            self.cache_stats['evictions'] += len(expired_keys)
            self.cache_stats['size'] -= len(expired_keys)

#!/usr/bin/env python3
"""
Performance optimization utilities for Bella V3.
Implements caching, response optimization, and monitoring.
"""

import time
import logging
from typing import Dict, Any, Optional, Callable
from functools import wraps
from datetime import datetime, timedelta
import json
import hashlib

logger = logging.getLogger(__name__)

# In-memory cache for lightweight operations
_memory_cache: Dict[str, Dict] = {}
_cache_stats = {'hits': 0, 'misses': 0, 'evictions': 0}

class PerformanceCache:
    """High-performance caching system"""

    def __init__(self, default_ttl: int = 300, max_size: int = 1000):
        self.default_ttl = default_ttl
        self.max_size = max_size
        self.cache = {}
        self.access_times = {}

    def _generate_key(self, func_name: str, args: tuple, kwargs: dict) -> str:
        """Generate cache key from function and arguments"""
        content = f"{func_name}:{str(args)}:{json.dumps(kwargs, sort_keys=True)}"
        return hashlib.md5(content.encode(), usedforsecurity=False).hexdigest()

    def _is_expired(self, entry: dict) -> bool:
        """Check if cache entry is expired"""
        return time.time() > entry['expires_at']

    def _evict_if_needed(self):
        """Evict least recently used items if cache is full"""
        if len(self.cache) >= self.max_size:
            # Remove expired items first
            expired_keys = [k for k, v in self.cache.items() if self._is_expired(v)]
            for key in expired_keys:
                del self.cache[key]
                self.access_times.pop(key, None)
                _cache_stats['evictions'] += 1

            # If still full, remove LRU items
            while len(self.cache) >= self.max_size:
                lru_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
                del self.cache[lru_key]
                del self.access_times[lru_key]
                _cache_stats['evictions'] += 1

    def get(self, key: str) -> Optional[Any]:
        """Get item from cache"""
        if key in self.cache:
            entry = self.cache[key]
            if not self._is_expired(entry):
                self.access_times[key] = time.time()
                _cache_stats['hits'] += 1
                return entry['data']
            else:
                # Remove expired entry
                del self.cache[key]
                self.access_times.pop(key, None)

        _cache_stats['misses'] += 1
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set item in cache"""
        self._evict_if_needed()

        ttl = ttl or self.default_ttl
        self.cache[key] = {
            'data': value,
            'expires_at': time.time() + ttl,
            'created_at': time.time()
        }
        self.access_times[key] = time.time()

    def clear(self) -> None:
        """Clear all cache entries"""
        self.cache.clear()
        self.access_times.clear()

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = _cache_stats['hits'] + _cache_stats['misses']
        hit_rate = _cache_stats['hits'] / total_requests if total_requests > 0 else 0

        return {
            'hits': _cache_stats['hits'],
            'misses': _cache_stats['misses'],
            'evictions': _cache_stats['evictions'],
            'hit_rate': hit_rate,
            'cache_size': len(self.cache),
            'max_size': self.max_size
        }

# Global cache instance
performance_cache = PerformanceCache()

def cached(ttl: int = 300, cache_instance: Optional[PerformanceCache] = None):
    """
    Decorator for caching function results.

    Args:
        ttl: Time to live in seconds
        cache_instance: Custom cache instance (uses global if None)
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = cache_instance or performance_cache
            cache_key = cache._generate_key(func.__name__, args, kwargs)

            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_result

            # Execute function and cache result
            start_time = time.time()
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time

            # Only cache if execution took significant time
            if execution_time > 0.1:  # Cache calls that take >100ms
                cache.set(cache_key, result, ttl)
                logger.debug(f"Cached result for {func.__name__} (took {execution_time:.3f}s)")

            return result
        return wrapper
    return decorator

class ResponseOptimizer:
    """Optimize API responses for better performance"""

    @staticmethod
    def compress_json(data: Any) -> str:
        """Compress JSON response"""
        return json.dumps(data, separators=(',', ':'), ensure_ascii=False)

    @staticmethod
    def minimize_twiml(twiml: str) -> str:
        """Minimize TwiML response size"""
        import re
        # Remove extra whitespace
        twiml = re.sub(r'\s+', ' ', twiml)
        # Remove unnecessary spaces around tags
        twiml = re.sub(r'>\s+<', '><', twiml)
        return twiml.strip()

    @staticmethod
    def add_performance_headers(response_headers: Dict[str, str]) -> Dict[str, str]:
        """Add performance-optimized headers"""
        performance_headers = {
            'Cache-Control': 'no-cache, must-revalidate',  # For dynamic content
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains'
        }
        response_headers.update(performance_headers)
        return response_headers

class PerformanceMonitor:
    """Monitor and log performance metrics"""

    def __init__(self):
        self.metrics = {
            'request_count': 0,
            'total_response_time': 0.0,
            'slow_requests': 0,
            'cache_effectiveness': 0.0,
            'last_reset': time.time()
        }

    def record_request(self, response_time: float, endpoint: str = None):
        """Record a request's performance"""
        self.metrics['request_count'] += 1
        self.metrics['total_response_time'] += response_time

        if response_time > 1.0:  # Slow request threshold
            self.metrics['slow_requests'] += 1
            logger.warning(f"Slow request detected: {response_time:.3f}s for {endpoint}")

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        if self.metrics['request_count'] == 0:
            return {'status': 'no_data'}

        avg_response_time = self.metrics['total_response_time'] / self.metrics['request_count']
        slow_request_rate = self.metrics['slow_requests'] / self.metrics['request_count']
        cache_stats = performance_cache.stats()

        return {
            'avg_response_time': round(avg_response_time, 3),
            'request_count': self.metrics['request_count'],
            'slow_request_rate': round(slow_request_rate, 3),
            'cache_hit_rate': round(cache_stats['hit_rate'], 3),
            'cache_size': cache_stats['cache_size'],
            'uptime_hours': round((time.time() - self.metrics['last_reset']) / 3600, 2)
        }

    def reset_metrics(self):
        """Reset all metrics"""
        self.metrics = {
            'request_count': 0,
            'total_response_time': 0.0,
            'slow_requests': 0,
            'cache_effectiveness': 0.0,
            'last_reset': time.time()
        }

# Global performance monitor
performance_monitor = PerformanceMonitor()

def performance_middleware(func: Callable):
    """Middleware decorator to monitor performance"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()

        try:
            result = func(*args, **kwargs)
            response_time = time.time() - start_time

            # Record performance
            endpoint = getattr(func, '__name__', 'unknown')
            performance_monitor.record_request(response_time, endpoint)

            return result

        except Exception as e:
            response_time = time.time() - start_time
            performance_monitor.record_request(response_time, f"error_{func.__name__}")
            raise

    return wrapper

# Utility functions for common optimizations
def optimize_database_query(query_func: Callable):
    """Optimize database queries with caching"""
    return cached(ttl=300)(query_func)

def optimize_llm_call(llm_func: Callable):
    """Optimize LLM calls with aggressive caching"""
    return cached(ttl=3600)(llm_func)  # Cache for 1 hour

def optimize_external_api(api_func: Callable):
    """Optimize external API calls"""
    return cached(ttl=600)(api_func)  # Cache for 10 minutes

# Performance testing utilities
def benchmark_function(func: Callable, iterations: int = 100):
    """Benchmark a function's performance"""
    times = []

    for _ in range(iterations):
        start = time.time()
        try:
            func()
            end = time.time()
            times.append(end - start)
        except Exception as e:
            logger.error(f"Benchmark error: {e}")
            continue

    if not times:
        return {'error': 'No successful executions'}

    return {
        'min_time': min(times),
        'max_time': max(times),
        'avg_time': sum(times) / len(times),
        'iterations': len(times),
        'total_time': sum(times)
    }

# Export performance utilities
__all__ = [
    'PerformanceCache',
    'performance_cache',
    'cached',
    'ResponseOptimizer',
    'PerformanceMonitor',
    'performance_monitor',
    'performance_middleware',
    'optimize_database_query',
    'optimize_llm_call',
    'optimize_external_api',
    'benchmark_function'
]
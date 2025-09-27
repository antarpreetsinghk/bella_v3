"""
Performance metrics collection and monitoring for token-efficient debugging.
"""
import time
from collections import defaultdict, deque
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)

class MetricsCollector:
    """Collect and track application performance metrics."""

    def __init__(self, max_samples: int = 1000):
        self.max_samples = max_samples
        self.request_times = deque(maxlen=max_samples)
        self.endpoint_stats = defaultdict(lambda: {
            'count': 0,
            'total_time': 0.0,
            'error_count': 0,
            'slow_count': 0  # requests > 2s
        })
        self.active_sessions = set()
        self.error_rates = deque(maxlen=100)  # Last 100 intervals

    def track_request(self, endpoint: str, duration: float, success: bool = True):
        """Track request metrics."""
        self.request_times.append(duration)

        stats = self.endpoint_stats[endpoint]
        stats['count'] += 1
        stats['total_time'] += duration

        if not success:
            stats['error_count'] += 1

        if duration > 2.0:  # Slow request threshold
            stats['slow_count'] += 1
            logger.warning(
                "slow_request",
                endpoint=endpoint,
                duration=round(duration, 3),
                threshold=2.0
            )

    def add_session(self, session_id: str):
        """Track active session."""
        self.active_sessions.add(session_id)

    def remove_session(self, session_id: str):
        """Remove session from tracking."""
        self.active_sessions.discard(session_id)

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics summary."""
        if not self.request_times:
            return {
                "active_sessions": len(self.active_sessions),
                "total_requests": 0,
                "avg_response_time": 0,
                "error_rate": 0,
                "slow_requests": 0
            }

        total_requests = sum(stats['count'] for stats in self.endpoint_stats.values())
        total_errors = sum(stats['error_count'] for stats in self.endpoint_stats.values())
        total_slow = sum(stats['slow_count'] for stats in self.endpoint_stats.values())

        recent_times = list(self.request_times)[-100:]  # Last 100 requests
        avg_response_time = sum(recent_times) / len(recent_times) if recent_times else 0

        return {
            "active_sessions": len(self.active_sessions),
            "total_requests": total_requests,
            "avg_response_time": round(avg_response_time, 3),
            "error_rate": round((total_errors / max(total_requests, 1)) * 100, 2),
            "slow_requests": total_slow,
            "top_endpoints": self._get_top_endpoints()
        }

    def _get_top_endpoints(self) -> List[Dict[str, Any]]:
        """Get top endpoints by request count."""
        sorted_endpoints = sorted(
            self.endpoint_stats.items(),
            key=lambda x: x[1]['count'],
            reverse=True
        )[:5]

        return [
            {
                "endpoint": endpoint,
                "count": stats['count'],
                "avg_time": round(stats['total_time'] / max(stats['count'], 1), 3),
                "error_rate": round((stats['error_count'] / max(stats['count'], 1)) * 100, 1)
            }
            for endpoint, stats in sorted_endpoints
        ]

    def reset_metrics(self):
        """Reset all metrics (useful for testing)."""
        self.request_times.clear()
        self.endpoint_stats.clear()
        self.active_sessions.clear()
        self.error_rates.clear()

# Global metrics collector
metrics_collector = MetricsCollector()

def track_performance(func: Callable) -> Callable:
    """Decorator to track function performance."""
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = time.time()
        endpoint = getattr(func, '__name__', 'unknown')
        success = True

        try:
            result = await func(*args, **kwargs)
            return result
        except Exception as e:
            success = False
            logger.error(
                "endpoint_error",
                endpoint=endpoint,
                error=str(e)[:100],
                error_type=type(e).__name__
            )
            raise
        finally:
            duration = time.time() - start_time
            metrics_collector.track_request(endpoint, duration, success)

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = time.time()
        endpoint = getattr(func, '__name__', 'unknown')
        success = True

        try:
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            success = False
            logger.error(
                "endpoint_error",
                endpoint=endpoint,
                error=str(e)[:100],
                error_type=type(e).__name__
            )
            raise
        finally:
            duration = time.time() - start_time
            metrics_collector.track_request(endpoint, duration, success)

    # Simplified: just return async wrapper for async functions
    import inspect
    if inspect.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper

class PerformanceMonitor:
    """Monitor performance patterns and detect anomalies."""

    def __init__(self):
        self.baseline_response_time = 1.0  # seconds
        self.response_time_samples = deque(maxlen=50)

    def check_performance(self, current_time: float) -> Optional[Dict[str, Any]]:
        """Check if current performance is degraded."""
        self.response_time_samples.append(current_time)

        if len(self.response_time_samples) < 10:
            return None

        recent_avg = sum(list(self.response_time_samples)[-10:]) / 10
        overall_avg = sum(self.response_time_samples) / len(self.response_time_samples)

        # Check for performance degradation
        degradation_threshold = self.baseline_response_time * 2.0

        if recent_avg > degradation_threshold:
            return {
                "status": "degraded",
                "recent_avg": round(recent_avg, 3),
                "baseline": self.baseline_response_time,
                "degradation_factor": round(recent_avg / self.baseline_response_time, 1)
            }

        return None

# Global performance monitor
performance_monitor = PerformanceMonitor()

def get_performance_metrics() -> Dict[str, Any]:
    """Get comprehensive performance metrics."""
    base_metrics = metrics_collector.get_metrics()

    # Add performance monitoring
    if metrics_collector.request_times:
        recent_time = list(metrics_collector.request_times)[-1]
        perf_status = performance_monitor.check_performance(recent_time)
        if perf_status:
            base_metrics['performance_status'] = perf_status

    return base_metrics
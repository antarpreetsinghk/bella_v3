#!/usr/bin/env python3
"""
Performance monitoring API endpoints.
"""

from fastapi import APIRouter, Depends
from typing import Dict, Any

from app.core.performance import performance_monitor, performance_cache
from app.api.auth import require_api_key

router = APIRouter()

@router.get("/performance/stats")
async def performance_stats(api_key: str = Depends(require_api_key)) -> Dict[str, Any]:
    """Get performance statistics"""
    perf_summary = performance_monitor.get_performance_summary()
    cache_stats = performance_cache.stats()

    return {
        "performance": perf_summary,
        "cache": cache_stats,
        "status": "healthy" if perf_summary.get('avg_response_time', 0) < 1.0 else "degraded"
    }

@router.post("/performance/reset")
async def reset_performance_stats(api_key: str = Depends(require_api_key)) -> Dict[str, str]:
    """Reset performance metrics"""
    performance_monitor.reset_metrics()
    performance_cache.clear()

    return {"status": "reset", "message": "Performance metrics and cache cleared"}

@router.get("/performance/cache/clear")
async def clear_cache(api_key: str = Depends(require_api_key)) -> Dict[str, str]:
    """Clear performance cache"""
    performance_cache.clear()
    return {"status": "cleared", "message": "Performance cache cleared"}

@router.get("/performance/health")
async def performance_health() -> Dict[str, Any]:
    """Public performance health check (no auth required)"""
    perf_summary = performance_monitor.get_performance_summary()

    if perf_summary.get('status') == 'no_data':
        return {"status": "starting", "message": "Performance monitoring initializing"}

    avg_response = perf_summary.get('avg_response_time', 0)
    cache_hit_rate = perf_summary.get('cache_hit_rate', 0)

    if avg_response < 0.5 and cache_hit_rate > 0.3:
        status = "excellent"
    elif avg_response < 1.0:
        status = "good"
    elif avg_response < 3.0:
        status = "acceptable"
    else:
        status = "poor"

    return {
        "status": status,
        "avg_response_time": avg_response,
        "cache_hit_rate": cache_hit_rate,
        "uptime_hours": perf_summary.get('uptime_hours', 0)
    }
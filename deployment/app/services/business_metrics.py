#!/usr/bin/env python3
"""
Business metrics tracking and monitoring for Bella V3.
Tracks key performance indicators, call success rates, and business health.
"""

import asyncio
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict, deque
import logging
import redis.asyncio as redis

from app.core.config import settings

logger = logging.getLogger(__name__)

# Forward declaration for alerting integration
_alert_manager = None

def _get_alert_manager():
    """Get alert manager instance (lazy loading to avoid circular imports)"""
    global _alert_manager
    if _alert_manager is None:
        try:
            from app.services.alerting import alert_manager
            _alert_manager = alert_manager
        except ImportError:
            _alert_manager = None
    return _alert_manager

async def _create_metrics_alert(severity: str, component: str, message: str, details: Dict[str, Any]):
    """Create business metrics alert"""
    alert_mgr = _get_alert_manager()
    if alert_mgr:
        try:
            await alert_mgr.create_alert(
                component=component,
                severity=severity,
                message=message,
                details=details
            )
        except Exception as e:
            logger.warning(f"Failed to create business metrics alert: {e}")

@dataclass
class CallMetrics:
    """Metrics for a single call"""
    call_sid: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str = "in_progress"  # in_progress, completed, failed, abandoned
    success: bool = False
    response_time: float = 0.0
    steps_completed: int = 0
    total_steps: int = 5  # name, phone, service, time, confirmation
    error_type: Optional[str] = None
    user_satisfaction: Optional[int] = None  # 1-5 rating if available

@dataclass
class BusinessKPIs:
    """Key Performance Indicators for business monitoring"""
    # Call Success Metrics
    total_calls: int = 0
    completed_calls: int = 0
    failed_calls: int = 0
    abandoned_calls: int = 0

    # Performance Metrics
    avg_response_time: float = 0.0
    avg_call_duration: float = 0.0
    success_rate: float = 0.0
    completion_rate: float = 0.0

    # Service Quality Metrics
    speech_recognition_accuracy: float = 0.0
    ai_extraction_success_rate: float = 0.0
    fallback_usage_rate: float = 0.0

    # Cost Metrics
    cost_per_call: float = 0.0
    monthly_infrastructure_cost: float = 0.0
    whisper_api_calls: int = 0

    # Timestamp
    calculated_at: datetime = field(default_factory=lambda: datetime.utcnow())

class BusinessMetricsCollector:
    """Collects and analyzes business metrics in real-time"""

    def __init__(self):
        self._redis_client: Optional[redis.Redis] = None
        self._call_metrics: Dict[str, CallMetrics] = {}
        self._recent_kpis: deque = deque(maxlen=100)  # Keep last 100 KPI snapshots
        self._hourly_stats: Dict[str, Any] = defaultdict(lambda: defaultdict(int))

    async def get_redis_client(self) -> Optional[redis.Redis]:
        """Get Redis client for persistent metrics storage"""
        if self._redis_client is None:
            redis_url = settings.REDIS_URL
            if not redis_url:
                logger.info("Redis not available for business metrics - using memory only")
                return None

            try:
                self._redis_client = await redis.from_url(
                    redis_url,
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_timeout=1
                )
                await self._redis_client.ping()
            except Exception as e:
                logger.warning(f"Business metrics Redis connection failed: {e}")
                return None

        return self._redis_client

    async def start_call_tracking(self, call_sid: str) -> None:
        """Start tracking metrics for a new call"""
        call_metrics = CallMetrics(
            call_sid=call_sid,
            start_time=datetime.utcnow(),
            status="in_progress"
        )

        self._call_metrics[call_sid] = call_metrics
        logger.debug(f"Started tracking call: {call_sid[:8]}")

        # Store in Redis for persistence
        redis_client = await self.get_redis_client()
        if redis_client:
            try:
                await redis_client.setex(
                    f"call_metrics:{call_sid}",
                    3600,  # 1 hour TTL
                    json.dumps({
                        "call_sid": call_sid,
                        "start_time": call_metrics.start_time.isoformat(),
                        "status": call_metrics.status
                    })
                )
            except Exception as e:
                logger.warning(f"Failed to store call metrics in Redis: {e}")

    async def update_call_progress(self, call_sid: str, step_completed: str, success: bool = True) -> None:
        """Update call progress with step completion"""
        if call_sid not in self._call_metrics:
            await self.start_call_tracking(call_sid)

        metrics = self._call_metrics[call_sid]
        if success:
            metrics.steps_completed += 1

        logger.debug(f"Call {call_sid[:8]} progress: {metrics.steps_completed}/{metrics.total_steps} steps")

    async def complete_call(self,
                          call_sid: str,
                          success: bool,
                          error_type: Optional[str] = None) -> None:
        """Mark call as completed and calculate final metrics"""
        if call_sid not in self._call_metrics:
            await self.start_call_tracking(call_sid)

        metrics = self._call_metrics[call_sid]
        metrics.end_time = datetime.utcnow()
        metrics.success = success
        metrics.status = "completed" if success else "failed"
        metrics.error_type = error_type

        # Calculate call duration
        if metrics.end_time and metrics.start_time:
            duration = (metrics.end_time - metrics.start_time).total_seconds()
            metrics.response_time = duration

        logger.info(f"Call {call_sid[:8]} completed: success={success}, duration={metrics.response_time:.1f}s")

        # Update hourly statistics
        hour_key = metrics.start_time.strftime("%Y-%m-%d-%H")
        self._hourly_stats[hour_key]["total_calls"] += 1
        if success:
            self._hourly_stats[hour_key]["successful_calls"] += 1
        else:
            self._hourly_stats[hour_key]["failed_calls"] += 1

        # Trigger alerts for performance issues
        asyncio.create_task(self._check_call_performance_alerts(metrics, success, error_type))

    async def record_speech_recognition(self, call_sid: str, accuracy: float, fallback_used: bool = False) -> None:
        """Record speech recognition performance"""
        hour_key = datetime.utcnow().strftime("%Y-%m-%d-%H")
        self._hourly_stats[hour_key]["speech_recognitions"] += 1
        self._hourly_stats[hour_key]["speech_accuracy_sum"] += accuracy

        if fallback_used:
            self._hourly_stats[hour_key]["fallback_usage"] += 1

    async def record_ai_extraction(self, call_sid: str, success: bool, confidence: float) -> None:
        """Record AI extraction performance"""
        hour_key = datetime.utcnow().strftime("%Y-%m-%d-%H")
        self._hourly_stats[hour_key]["ai_extractions"] += 1
        if success:
            self._hourly_stats[hour_key]["successful_extractions"] += 1
        self._hourly_stats[hour_key]["extraction_confidence_sum"] += confidence

    async def record_cost_event(self, event_type: str, cost: float) -> None:
        """Record cost-related events (Whisper calls, infrastructure usage)"""
        hour_key = datetime.utcnow().strftime("%Y-%m-%d-%H")
        self._hourly_stats[hour_key][f"cost_{event_type}"] += cost

        if event_type == "whisper_api":
            self._hourly_stats[hour_key]["whisper_calls"] += 1

    async def calculate_current_kpis(self) -> BusinessKPIs:
        """Calculate current business KPIs"""
        now = datetime.utcnow()

        # Get metrics from last 24 hours
        recent_calls = [
            metrics for metrics in self._call_metrics.values()
            if (now - metrics.start_time).total_seconds() < 86400  # 24 hours
        ]

        if not recent_calls:
            return BusinessKPIs()

        # Calculate basic call metrics
        total_calls = len(recent_calls)
        completed_calls = len([c for c in recent_calls if c.status == "completed"])
        failed_calls = len([c for c in recent_calls if c.status == "failed"])
        successful_calls = len([c for c in recent_calls if c.success])

        # Calculate performance metrics
        completed_with_duration = [c for c in recent_calls if c.response_time > 0]
        avg_response_time = (
            sum(c.response_time for c in completed_with_duration) / len(completed_with_duration)
            if completed_with_duration else 0.0
        )

        # Calculate success rates
        success_rate = successful_calls / total_calls if total_calls > 0 else 0.0
        completion_rate = completed_calls / total_calls if total_calls > 0 else 0.0

        # Calculate hourly aggregates for last 24 hours
        last_24h = []
        for i in range(24):
            hour = now - timedelta(hours=i)
            hour_key = hour.strftime("%Y-%m-%d-%H")
            if hour_key in self._hourly_stats:
                last_24h.append(self._hourly_stats[hour_key])

        # Speech recognition accuracy
        total_recognitions = sum(h.get("speech_recognitions", 0) for h in last_24h)
        accuracy_sum = sum(h.get("speech_accuracy_sum", 0) for h in last_24h)
        speech_accuracy = accuracy_sum / total_recognitions if total_recognitions > 0 else 0.0

        # AI extraction success rate
        total_extractions = sum(h.get("ai_extractions", 0) for h in last_24h)
        successful_extractions = sum(h.get("successful_extractions", 0) for h in last_24h)
        extraction_success_rate = successful_extractions / total_extractions if total_extractions > 0 else 0.0

        # Fallback usage rate
        total_fallbacks = sum(h.get("fallback_usage", 0) for h in last_24h)
        fallback_rate = total_fallbacks / total_recognitions if total_recognitions > 0 else 0.0

        # Cost metrics
        whisper_calls = sum(h.get("whisper_calls", 0) for h in last_24h)
        total_whisper_cost = sum(h.get("cost_whisper_api", 0) for h in last_24h)

        kpis = BusinessKPIs(
            total_calls=total_calls,
            completed_calls=completed_calls,
            failed_calls=failed_calls,
            avg_response_time=avg_response_time,
            success_rate=success_rate,
            completion_rate=completion_rate,
            speech_recognition_accuracy=speech_accuracy,
            ai_extraction_success_rate=extraction_success_rate,
            fallback_usage_rate=fallback_rate,
            whisper_api_calls=whisper_calls,
            cost_per_call=total_whisper_cost / total_calls if total_calls > 0 else 0.0
        )

        # Cache the KPIs
        self._recent_kpis.append(kpis)

        return kpis

    async def get_hourly_trends(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get hourly trend data for visualization"""
        now = datetime.utcnow()
        trends = []

        for i in range(hours):
            hour = now - timedelta(hours=i)
            hour_key = hour.strftime("%Y-%m-%d-%H")
            hour_stats = self._hourly_stats.get(hour_key, {})

            trends.append({
                "hour": hour.isoformat(),
                "total_calls": hour_stats.get("total_calls", 0),
                "successful_calls": hour_stats.get("successful_calls", 0),
                "failed_calls": hour_stats.get("failed_calls", 0),
                "success_rate": (
                    hour_stats.get("successful_calls", 0) / max(hour_stats.get("total_calls", 1), 1)
                ),
                "speech_accuracy": (
                    hour_stats.get("speech_accuracy_sum", 0) / max(hour_stats.get("speech_recognitions", 1), 1)
                ),
                "cost": hour_stats.get("cost_whisper_api", 0)
            })

        return sorted(trends, key=lambda x: x["hour"])

    async def get_performance_alerts(self) -> List[Dict[str, Any]]:
        """Get performance alerts based on KPI thresholds"""
        kpis = await self.calculate_current_kpis()
        alerts = []

        # Success rate alerts
        if kpis.success_rate < 0.9 and kpis.total_calls >= 5:
            alerts.append({
                "type": "success_rate",
                "severity": "high" if kpis.success_rate < 0.8 else "medium",
                "message": f"Call success rate is {kpis.success_rate:.1%} (target: >90%)",
                "value": kpis.success_rate,
                "threshold": 0.9
            })

        # Response time alerts
        if kpis.avg_response_time > 3.0:
            alerts.append({
                "type": "response_time",
                "severity": "high" if kpis.avg_response_time > 5.0 else "medium",
                "message": f"Average response time is {kpis.avg_response_time:.1f}s (target: <2s)",
                "value": kpis.avg_response_time,
                "threshold": 2.0
            })

        # Speech recognition alerts
        if kpis.speech_recognition_accuracy < 0.85 and kpis.total_calls >= 3:
            alerts.append({
                "type": "speech_accuracy",
                "severity": "medium",
                "message": f"Speech recognition accuracy is {kpis.speech_recognition_accuracy:.1%} (target: >85%)",
                "value": kpis.speech_recognition_accuracy,
                "threshold": 0.85
            })

        # High fallback usage alerts
        if kpis.fallback_usage_rate > 0.2:
            alerts.append({
                "type": "fallback_usage",
                "severity": "medium",
                "message": f"Fallback usage rate is {kpis.fallback_usage_rate:.1%} (target: <20%)",
                "value": kpis.fallback_usage_rate,
                "threshold": 0.2
            })

        return alerts

    async def _check_call_performance_alerts(self, metrics: CallMetrics, success: bool, error_type: Optional[str]):
        """Check call performance and trigger alerts if needed"""

        # Alert for failed calls
        if not success:
            await _create_metrics_alert(
                severity="medium" if error_type else "high",
                component="call_performance",
                message=f"Call failed: {error_type or 'Unknown error'}",
                details={
                    "call_sid": metrics.call_sid,
                    "error_type": error_type,
                    "response_time": metrics.response_time,
                    "steps_completed": metrics.steps_completed,
                    "total_steps": metrics.total_steps
                }
            )

        # Alert for slow calls (over 5 seconds)
        if metrics.response_time > 5.0:
            await _create_metrics_alert(
                severity="medium",
                component="call_performance",
                message=f"Slow call detected: {metrics.response_time:.1f}s (target: <2s)",
                details={
                    "call_sid": metrics.call_sid,
                    "response_time": metrics.response_time,
                    "steps_completed": metrics.steps_completed,
                    "total_steps": metrics.total_steps
                }
            )

        # Alert for extremely slow calls (over 10 seconds)
        if metrics.response_time > 10.0:
            await _create_metrics_alert(
                severity="high",
                component="call_performance",
                message=f"CRITICAL: Very slow call: {metrics.response_time:.1f}s",
                details={
                    "call_sid": metrics.call_sid,
                    "response_time": metrics.response_time,
                    "steps_completed": metrics.steps_completed,
                    "total_steps": metrics.total_steps
                }
            )

        # Update SLA tracking for alerting system
        alert_mgr = _get_alert_manager()
        if alert_mgr:
            # Track call success for SLA monitoring
            await alert_mgr.track_service_status("call_success_rate", success)

            # Track response time SLA (target: 99% under 2s)
            response_time_sla_met = metrics.response_time <= 2.0
            await alert_mgr.track_service_status("response_time", response_time_sla_met)

    async def cleanup_old_data(self):
        """Clean up old metrics data to prevent memory leaks"""
        cutoff_time = datetime.utcnow() - timedelta(days=2)

        # Clean call metrics
        old_calls = [
            call_sid for call_sid, metrics in self._call_metrics.items()
            if metrics.start_time < cutoff_time
        ]

        for call_sid in old_calls:
            del self._call_metrics[call_sid]

        # Clean hourly stats (keep 7 days)
        cutoff_hour = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d-%H")
        old_hours = [
            hour for hour in self._hourly_stats.keys()
            if hour < cutoff_hour
        ]

        for hour in old_hours:
            del self._hourly_stats[hour]

        if old_calls or old_hours:
            logger.info(f"Cleaned up {len(old_calls)} old call metrics and {len(old_hours)} old hourly stats")

# Global business metrics collector
business_metrics = BusinessMetricsCollector()
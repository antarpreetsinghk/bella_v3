#!/usr/bin/env python3
"""
Cost optimization and auto-scaling service for Bella V3.
Monitors usage patterns and provides optimization recommendations.
"""

import asyncio
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import logging

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

async def _create_cost_alert(severity: str, component: str, message: str, details: Dict[str, Any]):
    """Create cost optimization alert"""
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
            logger.warning(f"Failed to create cost optimization alert: {e}")

@dataclass
class CostMetrics:
    """Cost tracking for different services"""
    whisper_api_cost: float = 0.0
    infrastructure_cost: float = 0.0
    storage_cost: float = 0.0
    network_cost: float = 0.0
    total_cost: float = 0.0
    period_start: datetime = field(default_factory=lambda: datetime.utcnow())
    period_end: Optional[datetime] = None

@dataclass
class UsagePattern:
    """Usage pattern analysis for scaling decisions"""
    avg_concurrent_calls: float = 0.0
    peak_concurrent_calls: int = 0
    avg_daily_calls: float = 0.0
    peak_hours: List[int] = field(default_factory=list)
    utilization_rate: float = 0.0
    growth_trend: float = 0.0  # Percentage growth week-over-week

@dataclass
class ScalingRecommendation:
    """Auto-scaling recommendation"""
    component: str  # "ecs_tasks", "database", "redis"
    current_capacity: int
    recommended_capacity: int
    reason: str
    potential_savings: float
    confidence: float  # 0.0 to 1.0

class CostOptimizer:
    """Cost optimization and monitoring service"""

    def __init__(self):
        self._cost_history: List[CostMetrics] = []
        self._usage_patterns: Dict[str, UsagePattern] = {}
        self._daily_costs: Dict[str, float] = {}  # date -> cost
        self._hourly_usage: Dict[str, int] = {}   # hour -> call count

        # Cost thresholds and targets
        self.monthly_budget = 50.0  # $50/month target
        self.cost_per_call_target = 0.10  # $0.10 per call target
        self.whisper_cost_per_minute = 0.006  # $0.006/minute

    async def track_cost_event(self,
                              service: str,
                              cost: float,
                              details: Dict[str, Any] = None) -> None:
        """Track a cost-incurring event"""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        self._daily_costs[today] = self._daily_costs.get(today, 0.0) + cost

        logger.debug(f"Cost event: {service} ${cost:.4f} - {details or {}}")

        # Update current period metrics
        current_period = self._get_current_period()
        if service == "whisper_api":
            current_period.whisper_api_cost += cost
        elif service == "infrastructure":
            current_period.infrastructure_cost += cost
        elif service == "storage":
            current_period.storage_cost += cost
        elif service == "network":
            current_period.network_cost += cost

        current_period.total_cost = (
            current_period.whisper_api_cost +
            current_period.infrastructure_cost +
            current_period.storage_cost +
            current_period.network_cost
        )

        # Check for budget alerts
        asyncio.create_task(self._check_budget_alerts(current_period))

    async def track_usage_event(self,
                               event_type: str,
                               concurrent_calls: int = 0,
                               details: Dict[str, Any] = None) -> None:
        """Track usage patterns for scaling analysis"""
        hour = datetime.utcnow().hour
        hour_key = f"{datetime.utcnow().strftime('%Y-%m-%d')}-{hour:02d}"

        if event_type == "call_start":
            self._hourly_usage[hour_key] = self._hourly_usage.get(hour_key, 0) + 1

        # Update usage patterns
        if "call_volume" not in self._usage_patterns:
            self._usage_patterns["call_volume"] = UsagePattern()

        pattern = self._usage_patterns["call_volume"]
        pattern.peak_concurrent_calls = max(pattern.peak_concurrent_calls, concurrent_calls)

        # Track peak hours
        if hour not in pattern.peak_hours and self._hourly_usage.get(hour_key, 0) > 5:
            pattern.peak_hours.append(hour)

    def _get_current_period(self) -> CostMetrics:
        """Get or create current billing period metrics"""
        now = datetime.utcnow()

        # Find current period (last 30 days)
        if not self._cost_history:
            period = CostMetrics(period_start=now)
            self._cost_history.append(period)
            return period

        current = self._cost_history[-1]
        if (now - current.period_start).days >= 30:
            # Start new period
            current.period_end = now
            new_period = CostMetrics(period_start=now)
            self._cost_history.append(new_period)
            return new_period

        return current

    async def get_cost_summary(self, days: int = 30) -> Dict[str, Any]:
        """Get cost summary for specified period"""
        current = self._get_current_period()

        # Calculate daily costs for the period
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        recent_costs = [
            cost for date_str, cost in self._daily_costs.items()
            if datetime.fromisoformat(date_str) >= cutoff_date
        ]

        total_recent_cost = sum(recent_costs)
        avg_daily_cost = total_recent_cost / days if days > 0 else 0.0
        projected_monthly = avg_daily_cost * 30

        return {
            "current_period": {
                "whisper_api_cost": current.whisper_api_cost,
                "infrastructure_cost": current.infrastructure_cost,
                "storage_cost": current.storage_cost,
                "network_cost": current.network_cost,
                "total_cost": current.total_cost,
                "period_days": (datetime.utcnow() - current.period_start).days
            },
            "recent_trends": {
                "total_cost_last_30d": total_recent_cost,
                "avg_daily_cost": avg_daily_cost,
                "projected_monthly": projected_monthly,
                "budget_utilization": projected_monthly / self.monthly_budget,
                "budget_remaining": max(0, self.monthly_budget - projected_monthly)
            },
            "cost_per_service": {
                "whisper_api_percentage": (current.whisper_api_cost / max(current.total_cost, 0.01)) * 100,
                "infrastructure_percentage": (current.infrastructure_cost / max(current.total_cost, 0.01)) * 100,
                "storage_percentage": (current.storage_cost / max(current.total_cost, 0.01)) * 100,
                "network_percentage": (current.network_cost / max(current.total_cost, 0.01)) * 100
            }
        }

    async def analyze_usage_patterns(self) -> Dict[str, Any]:
        """Analyze usage patterns for optimization opportunities"""
        if "call_volume" not in self._usage_patterns:
            return {"status": "insufficient_data"}

        pattern = self._usage_patterns["call_volume"]

        # Calculate usage statistics
        recent_hours = []
        now = datetime.utcnow()
        for i in range(168):  # Last 7 days (168 hours)
            hour = now - timedelta(hours=i)
            hour_key = f"{hour.strftime('%Y-%m-%d')}-{hour.hour:02d}"
            call_count = self._hourly_usage.get(hour_key, 0)
            recent_hours.append(call_count)

        avg_hourly_calls = sum(recent_hours) / len(recent_hours) if recent_hours else 0
        max_hourly_calls = max(recent_hours) if recent_hours else 0

        # Identify peak hours (hours with >150% of average)
        peak_threshold = avg_hourly_calls * 1.5
        peak_hours = []
        for i in range(24):
            hour_calls = [
                self._hourly_usage.get(f"{(now - timedelta(days=d)).strftime('%Y-%m-%d')}-{i:02d}", 0)
                for d in range(7)
            ]
            if sum(hour_calls) / 7 > peak_threshold:
                peak_hours.append(i)

        return {
            "usage_statistics": {
                "avg_hourly_calls": avg_hourly_calls,
                "max_hourly_calls": max_hourly_calls,
                "peak_concurrent_calls": pattern.peak_concurrent_calls,
                "peak_hours": peak_hours,
                "total_weekly_calls": sum(recent_hours)
            },
            "efficiency_metrics": {
                "utilization_rate": min(avg_hourly_calls / max(max_hourly_calls, 1), 1.0),
                "peak_to_average_ratio": max_hourly_calls / max(avg_hourly_calls, 1)
            }
        }

    async def generate_optimization_recommendations(self) -> List[ScalingRecommendation]:
        """Generate cost optimization and scaling recommendations"""
        recommendations = []

        cost_summary = await self.get_cost_summary()
        usage_analysis = await self.analyze_usage_patterns()

        current_cost = cost_summary["current_period"]["total_cost"]
        projected_monthly = cost_summary["recent_trends"]["projected_monthly"]

        # Budget optimization recommendations
        if projected_monthly > self.monthly_budget:
            over_budget = projected_monthly - self.monthly_budget
            recommendations.append(ScalingRecommendation(
                component="budget",
                current_capacity=int(projected_monthly),
                recommended_capacity=int(self.monthly_budget),
                reason=f"Projected monthly cost ${projected_monthly:.2f} exceeds budget ${self.monthly_budget:.2f}",
                potential_savings=over_budget,
                confidence=0.9
            ))

        # ECS scaling recommendations
        if "usage_statistics" in usage_analysis:
            stats = usage_analysis["usage_statistics"]
            avg_calls = stats["avg_hourly_calls"]
            max_calls = stats["max_hourly_calls"]

            # Recommend scaling based on utilization
            if avg_calls < 2 and max_calls < 5:
                # Under-utilized - recommend scaling down
                recommendations.append(ScalingRecommendation(
                    component="ecs_tasks",
                    current_capacity=2,  # Assumed current
                    recommended_capacity=1,
                    reason="Low call volume suggests single task is sufficient",
                    potential_savings=15.0,  # Estimated monthly savings
                    confidence=0.8
                ))
            elif max_calls > 10:
                # High load - recommend scaling up
                recommendations.append(ScalingRecommendation(
                    component="ecs_tasks",
                    current_capacity=1,  # Assumed current
                    recommended_capacity=2,
                    reason="Peak load suggests additional capacity needed",
                    potential_savings=-10.0,  # Additional cost for reliability
                    confidence=0.7
                ))

        # Whisper API optimization
        whisper_percentage = cost_summary["cost_per_service"]["whisper_api_percentage"]
        if whisper_percentage > 60:
            recommendations.append(ScalingRecommendation(
                component="whisper_api",
                current_capacity=100,
                recommended_capacity=80,
                reason="High Whisper API usage - consider caching optimizations",
                potential_savings=current_cost * 0.2,
                confidence=0.6
            ))

        return recommendations

    async def get_cost_alerts(self) -> List[Dict[str, Any]]:
        """Get cost-related alerts and warnings"""
        alerts = []
        cost_summary = await self.get_cost_summary()

        projected_monthly = cost_summary["recent_trends"]["projected_monthly"]
        budget_utilization = cost_summary["recent_trends"]["budget_utilization"]

        # Budget alerts
        if budget_utilization > 0.9:
            alerts.append({
                "type": "budget_exceeded",
                "severity": "high" if budget_utilization > 1.0 else "medium",
                "message": f"Monthly cost projection ${projected_monthly:.2f} is {budget_utilization:.1%} of budget",
                "value": projected_monthly,
                "threshold": self.monthly_budget
            })

        # Cost growth alerts
        current_total = cost_summary["current_period"]["total_cost"]
        if len(self._cost_history) > 1:
            previous_total = self._cost_history[-2].total_cost
            if current_total > previous_total * 1.2:  # 20% increase
                alerts.append({
                    "type": "cost_growth",
                    "severity": "medium",
                    "message": f"Cost increased {((current_total/previous_total-1)*100):.1f}% from previous period",
                    "value": current_total,
                    "threshold": previous_total * 1.2
                })

        # Whisper API cost alerts
        whisper_cost = cost_summary["current_period"]["whisper_api_cost"]
        if whisper_cost > 20:  # More than $20 on Whisper API
            alerts.append({
                "type": "whisper_cost",
                "severity": "medium",
                "message": f"Whisper API costs are ${whisper_cost:.2f} this period",
                "value": whisper_cost,
                "threshold": 20.0
            })

        return alerts

    async def estimate_call_cost(self, duration_minutes: float) -> float:
        """Estimate cost for a call of given duration"""
        whisper_cost = duration_minutes * self.whisper_cost_per_minute
        infrastructure_cost = 0.001  # Estimated per-call infrastructure cost
        return whisper_cost + infrastructure_cost

    async def _check_budget_alerts(self, current_period: CostMetrics):
        """Check budget thresholds and trigger alerts if needed"""
        # Calculate projected monthly cost
        period_days = (datetime.utcnow() - current_period.period_start).days
        if period_days > 0:
            daily_avg = current_period.total_cost / period_days
            projected_monthly = daily_avg * 30
        else:
            projected_monthly = current_period.total_cost

        # Budget alert thresholds
        budget_80_percent = self.monthly_budget * 0.8
        budget_90_percent = self.monthly_budget * 0.9

        # Alert for 80% budget usage
        if projected_monthly >= budget_80_percent and projected_monthly < budget_90_percent:
            await _create_cost_alert(
                severity="medium",
                component="cost_budget",
                message=f"Budget at 80%: Projected ${projected_monthly:.2f}/${self.monthly_budget:.2f}",
                details={
                    "projected_monthly": projected_monthly,
                    "budget": self.monthly_budget,
                    "utilization": projected_monthly / self.monthly_budget,
                    "current_total": current_period.total_cost,
                    "period_days": period_days
                }
            )

        # Alert for 90% budget usage
        elif projected_monthly >= budget_90_percent and projected_monthly < self.monthly_budget:
            await _create_cost_alert(
                severity="high",
                component="cost_budget",
                message=f"Budget at 90%: Projected ${projected_monthly:.2f}/${self.monthly_budget:.2f}",
                details={
                    "projected_monthly": projected_monthly,
                    "budget": self.monthly_budget,
                    "utilization": projected_monthly / self.monthly_budget,
                    "current_total": current_period.total_cost,
                    "period_days": period_days
                }
            )

        # Alert for budget exceeded
        elif projected_monthly >= self.monthly_budget:
            await _create_cost_alert(
                severity="critical",
                component="cost_budget",
                message=f"BUDGET EXCEEDED: Projected ${projected_monthly:.2f} exceeds ${self.monthly_budget:.2f}",
                details={
                    "projected_monthly": projected_monthly,
                    "budget": self.monthly_budget,
                    "utilization": projected_monthly / self.monthly_budget,
                    "overage": projected_monthly - self.monthly_budget,
                    "current_total": current_period.total_cost,
                    "period_days": period_days
                }
            )

        # Alert for high Whisper API costs
        whisper_percentage = (current_period.whisper_api_cost / max(current_period.total_cost, 0.01)) * 100
        if whisper_percentage > 70:
            await _create_cost_alert(
                severity="medium",
                component="cost_whisper",
                message=f"High Whisper API usage: {whisper_percentage:.1f}% of total costs",
                details={
                    "whisper_cost": current_period.whisper_api_cost,
                    "total_cost": current_period.total_cost,
                    "percentage": whisper_percentage,
                    "suggestion": "Consider caching or optimization"
                }
            )

    async def get_optimization_dashboard(self) -> Dict[str, Any]:
        """Get complete cost optimization dashboard data"""
        cost_summary = await self.get_cost_summary()
        usage_analysis = await self.analyze_usage_patterns()
        recommendations = await self.generate_optimization_recommendations()
        alerts = await self.get_cost_alerts()

        return {
            "cost_summary": cost_summary,
            "usage_patterns": usage_analysis,
            "recommendations": [
                {
                    "component": rec.component,
                    "current": rec.current_capacity,
                    "recommended": rec.recommended_capacity,
                    "reason": rec.reason,
                    "savings": rec.potential_savings,
                    "confidence": rec.confidence
                }
                for rec in recommendations
            ],
            "alerts": alerts,
            "optimization_score": min(100, max(0,
                100 - (cost_summary["recent_trends"]["budget_utilization"] * 50) - len(alerts) * 10
            )),
            "generated_at": datetime.utcnow().isoformat()
        }

# Global cost optimizer instance
cost_optimizer = CostOptimizer()
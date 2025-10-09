#!/usr/bin/env python3
"""
Production-grade alerting and SLA monitoring for Bella V3.
Provides real-time alerting, SLA tracking, and notification delivery.
"""

import asyncio
import json
import logging
import smtplib
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from email.message import EmailMessage
from collections import defaultdict, deque
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

@dataclass
class Alert:
    """Alert definition with severity and routing"""
    id: str
    severity: str  # critical, high, medium, low
    component: str
    message: str
    details: Dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.utcnow())
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    escalation_level: int = 0
    notification_channels: List[str] = field(default_factory=list)

@dataclass
class SLATarget:
    """SLA target definition"""
    name: str
    target_percentage: float  # e.g., 99.9 for 99.9% uptime
    measurement_window: int  # hours
    breach_threshold: float  # percentage below target that triggers alert
    critical_threshold: float  # percentage that triggers critical alert

@dataclass
class SLAMetrics:
    """Current SLA metrics"""
    name: str
    current_percentage: float
    target_percentage: float
    uptime_minutes: int
    downtime_minutes: int
    total_minutes: int
    breach_count: int
    last_breach: Optional[datetime] = None
    status: str = "healthy"  # healthy, warning, breach, critical

class AlertManager:
    """Production-grade alert management system"""

    def __init__(self):
        self._active_alerts: Dict[str, Alert] = {}
        self._alert_history: deque = deque(maxlen=1000)
        self._notification_queue: asyncio.Queue = asyncio.Queue()
        self._alert_rules: Dict[str, Callable] = {}
        self._escalation_rules: Dict[str, List[Dict]] = {}

        # SLA tracking
        self._sla_targets = self._initialize_sla_targets()
        self._sla_metrics: Dict[str, SLAMetrics] = {}
        self._service_status: Dict[str, bool] = defaultdict(lambda: True)
        self._uptime_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1440))  # 24h in minutes

        # Alert suppression and grouping
        self._suppression_rules: Dict[str, int] = {}  # component -> suppression_window_minutes
        self._alert_groups: Dict[str, List[str]] = {}  # group_id -> alert_ids

        self._setup_default_rules()

    def _initialize_sla_targets(self) -> Dict[str, SLATarget]:
        """Initialize SLA targets for monitoring"""
        return {
            "overall_uptime": SLATarget(
                name="Overall System Uptime",
                target_percentage=99.9,
                measurement_window=24,
                breach_threshold=0.1,  # Alert if below 99.8%
                critical_threshold=0.5  # Critical if below 99.4%
            ),
            "call_success_rate": SLATarget(
                name="Call Success Rate",
                target_percentage=95.0,
                measurement_window=1,
                breach_threshold=5.0,  # Alert if below 90%
                critical_threshold=10.0  # Critical if below 85%
            ),
            "response_time": SLATarget(
                name="API Response Time",
                target_percentage=99.0,  # 99% of requests under 2s
                measurement_window=1,
                breach_threshold=1.0,
                critical_threshold=3.0
            ),
            "openai_api_availability": SLATarget(
                name="OpenAI API Availability",
                target_percentage=99.5,
                measurement_window=1,
                breach_threshold=0.5,
                critical_threshold=1.0
            )
        }

    def _setup_default_rules(self):
        """Setup default alerting rules"""
        # Alert suppression windows (minutes)
        self._suppression_rules = {
            "openai_api": 5,  # Don't spam on API issues
            "database": 10,   # Database alerts less frequent
            "circuit_breaker": 3,  # Circuit breaker state changes
            "cost_budget": 60,    # Budget alerts hourly max
            "sla_breach": 15      # SLA breach alerts
        }

        # Escalation rules
        self._escalation_rules = {
            "critical": [
                {"level": 0, "delay_minutes": 0, "channels": ["slack", "email"]},
                {"level": 1, "delay_minutes": 5, "channels": ["slack", "email", "sms"]},
                {"level": 2, "delay_minutes": 15, "channels": ["slack", "email", "sms", "phone"]}
            ],
            "high": [
                {"level": 0, "delay_minutes": 0, "channels": ["slack"]},
                {"level": 1, "delay_minutes": 10, "channels": ["slack", "email"]},
                {"level": 2, "delay_minutes": 30, "channels": ["slack", "email", "sms"]}
            ],
            "medium": [
                {"level": 0, "delay_minutes": 0, "channels": ["slack"]},
                {"level": 1, "delay_minutes": 30, "channels": ["slack", "email"]}
            ],
            "low": [
                {"level": 0, "delay_minutes": 0, "channels": ["slack"]}
            ]
        }

    async def create_alert(self,
                         component: str,
                         severity: str,
                         message: str,
                         details: Dict[str, Any] = None,
                         alert_id: Optional[str] = None) -> str:
        """Create a new alert with intelligent deduplication"""
        details = details or {}

        # Generate alert ID if not provided
        if not alert_id:
            alert_id = f"{component}:{severity}:{abs(hash(message)) % 10000}"

        # Check for alert suppression
        if self._is_alert_suppressed(component, alert_id):
            logger.debug(f"Alert suppressed: {alert_id}")
            return alert_id

        # Check if similar alert already exists
        existing_alert = self._find_similar_alert(component, message)
        if existing_alert:
            logger.debug(f"Similar alert exists: {existing_alert.id}, updating count")
            existing_alert.details["occurrence_count"] = existing_alert.details.get("occurrence_count", 1) + 1
            existing_alert.timestamp = datetime.utcnow()
            return existing_alert.id

        # Create new alert
        alert = Alert(
            id=alert_id,
            severity=severity,
            component=component,
            message=message,
            details=details,
            notification_channels=self._get_notification_channels(severity, component)
        )

        self._active_alerts[alert_id] = alert
        self._alert_history.append(alert)

        logger.info(f"Alert created: {severity.upper()} - {component} - {message}")

        # Queue for notification
        await self._notification_queue.put(alert)

        return alert_id

    def _is_alert_suppressed(self, component: str, alert_id: str) -> bool:
        """Check if alert should be suppressed due to recent similar alerts"""
        suppression_window = self._suppression_rules.get(component, 5)
        cutoff_time = datetime.utcnow() - timedelta(minutes=suppression_window)

        # Check recent alerts for this component
        recent_alerts = [
            alert for alert in self._alert_history
            if (alert.component == component and
                alert.timestamp > cutoff_time and
                not alert.resolved)
        ]

        return len(recent_alerts) >= 3  # Suppress if 3+ recent alerts

    def _find_similar_alert(self, component: str, message: str) -> Optional[Alert]:
        """Find existing similar unresolved alert"""
        message_words = set(message.lower().split())

        for alert in self._active_alerts.values():
            if (alert.component == component and
                not alert.resolved):
                alert_words = set(alert.message.lower().split())
                # Check for 70% word overlap
                overlap = len(message_words & alert_words) / len(message_words | alert_words)
                if overlap > 0.7:
                    return alert
        return None

    def _get_notification_channels(self, severity: str, component: str) -> List[str]:
        """Determine notification channels based on severity and component"""
        channels = ["slack"]  # Always notify via Slack

        if severity in ["critical", "high"]:
            channels.append("email")

        if severity == "critical":
            channels.extend(["sms", "phone"])

        # Component-specific overrides
        if component in ["openai_api", "database"]:
            channels.append("email")

        return channels

    async def resolve_alert(self, alert_id: str, resolution_note: str = "") -> bool:
        """Resolve an active alert"""
        if alert_id not in self._active_alerts:
            return False

        alert = self._active_alerts[alert_id]
        alert.resolved = True
        alert.resolved_at = datetime.utcnow()
        alert.details["resolution_note"] = resolution_note

        logger.info(f"Alert resolved: {alert_id} - {resolution_note}")

        # Remove from active alerts
        del self._active_alerts[alert_id]

        return True

    async def track_service_status(self, service: str, is_up: bool):
        """Track service uptime for SLA monitoring"""
        current_minute = datetime.utcnow().replace(second=0, microsecond=0)

        # Update service status
        self._service_status[service] = is_up

        # Record uptime history (1 = up, 0 = down)
        self._uptime_history[service].append((current_minute, 1 if is_up else 0))

        # Check SLA thresholds
        await self._check_sla_violations(service)

    async def _check_sla_violations(self, service: str):
        """Check for SLA violations and create alerts"""
        if service not in self._sla_targets:
            return

        target = self._sla_targets[service]
        metrics = await self.calculate_sla_metrics(service)

        if metrics.current_percentage < (target.target_percentage - target.critical_threshold):
            await self.create_alert(
                component=f"sla_{service}",
                severity="critical",
                message=f"CRITICAL SLA breach: {service} at {metrics.current_percentage:.2f}% (target: {target.target_percentage}%)",
                details={
                    "service": service,
                    "current_sla": metrics.current_percentage,
                    "target_sla": target.target_percentage,
                    "downtime_minutes": metrics.downtime_minutes
                }
            )
        elif metrics.current_percentage < (target.target_percentage - target.breach_threshold):
            await self.create_alert(
                component=f"sla_{service}",
                severity="high",
                message=f"SLA breach: {service} at {metrics.current_percentage:.2f}% (target: {target.target_percentage}%)",
                details={
                    "service": service,
                    "current_sla": metrics.current_percentage,
                    "target_sla": target.target_percentage,
                    "downtime_minutes": metrics.downtime_minutes
                }
            )

    async def calculate_sla_metrics(self, service: str) -> SLAMetrics:
        """Calculate current SLA metrics for a service"""
        if service not in self._sla_targets:
            return SLAMetrics(service, 0.0, 0.0, 0, 0, 0, 0)

        target = self._sla_targets[service]
        history = self._uptime_history[service]

        if not history:
            return SLAMetrics(service, 100.0, target.target_percentage, 0, 0, 0, 0)

        # Calculate metrics for the measurement window
        cutoff_time = datetime.utcnow() - timedelta(hours=target.measurement_window)
        relevant_history = [
            (timestamp, status) for timestamp, status in history
            if timestamp >= cutoff_time
        ]

        if not relevant_history:
            return SLAMetrics(service, 100.0, target.target_percentage, 0, 0, 0, 0)

        total_minutes = len(relevant_history)
        uptime_minutes = sum(status for _, status in relevant_history)
        downtime_minutes = total_minutes - uptime_minutes

        current_percentage = (uptime_minutes / total_minutes * 100) if total_minutes > 0 else 100.0

        # Determine status
        status = "healthy"
        if current_percentage < (target.target_percentage - target.critical_threshold):
            status = "critical"
        elif current_percentage < (target.target_percentage - target.breach_threshold):
            status = "breach"
        elif current_percentage < target.target_percentage:
            status = "warning"

        return SLAMetrics(
            name=service,
            current_percentage=current_percentage,
            target_percentage=target.target_percentage,
            uptime_minutes=uptime_minutes,
            downtime_minutes=downtime_minutes,
            total_minutes=total_minutes,
            breach_count=len([s for _, s in relevant_history if s == 0]),
            status=status
        )

    async def get_sla_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive SLA dashboard data"""
        sla_data = {}

        for service_name in self._sla_targets.keys():
            metrics = await self.calculate_sla_metrics(service_name)
            sla_data[service_name] = {
                "current_sla": metrics.current_percentage,
                "target_sla": metrics.target_percentage,
                "status": metrics.status,
                "uptime_minutes": metrics.uptime_minutes,
                "downtime_minutes": metrics.downtime_minutes,
                "total_minutes": metrics.total_minutes,
                "breach_count": metrics.breach_count,
                "last_breach": metrics.last_breach.isoformat() if metrics.last_breach else None
            }

        # Overall system health score
        all_slas = [metrics["current_sla"] for metrics in sla_data.values()]
        overall_health = sum(all_slas) / len(all_slas) if all_slas else 100.0

        return {
            "overall_health_score": overall_health,
            "services": sla_data,
            "active_alerts": len(self._active_alerts),
            "critical_alerts": len([a for a in self._active_alerts.values() if a.severity == "critical"]),
            "generated_at": datetime.utcnow().isoformat()
        }

    async def send_notification(self, alert: Alert):
        """Send alert notification through configured channels"""
        for channel in alert.notification_channels:
            try:
                if channel == "slack":
                    await self._send_slack_notification(alert)
                elif channel == "email":
                    await self._send_email_notification(alert)
                elif channel == "sms":
                    await self._send_sms_notification(alert)
                # phone notifications would be implemented here

            except Exception as e:
                logger.error(f"Failed to send {channel} notification for alert {alert.id}: {e}")

    async def _send_slack_notification(self, alert: Alert):
        """Send Slack notification (webhook-based)"""
        slack_webhook = getattr(settings, 'SLACK_WEBHOOK_URL', None)
        if not slack_webhook:
            logger.warning("Slack webhook not configured")
            return

        # Color coding by severity
        color_map = {
            "critical": "#FF0000",
            "high": "#FF6600",
            "medium": "#FFCC00",
            "low": "#00FF00"
        }

        payload = {
            "text": f"🚨 {alert.severity.upper()} Alert",
            "attachments": [{
                "color": color_map.get(alert.severity, "#CCCCCC"),
                "fields": [
                    {"title": "Component", "value": alert.component, "short": True},
                    {"title": "Severity", "value": alert.severity.upper(), "short": True},
                    {"title": "Message", "value": alert.message, "short": False},
                    {"title": "Time", "value": alert.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"), "short": True}
                ]
            }]
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(slack_webhook, json=payload)
            response.raise_for_status()

    async def _send_email_notification(self, alert: Alert):
        """Send email notification"""
        smtp_host = getattr(settings, 'SMTP_HOST', None)
        smtp_port = getattr(settings, 'SMTP_PORT', 587)
        smtp_user = getattr(settings, 'SMTP_USER', None)
        smtp_password = getattr(settings, 'SMTP_PASSWORD', None)
        alert_email = getattr(settings, 'ALERT_EMAIL', None)

        if not all([smtp_host, smtp_user, smtp_password, alert_email]):
            logger.warning("Email notification not fully configured")
            return

        subject = f"[BELLA-{alert.severity.upper()}] {alert.component} Alert"

        body = f"""
Alert Details:
- Component: {alert.component}
- Severity: {alert.severity.upper()}
- Message: {alert.message}
- Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}
- Alert ID: {alert.id}

Additional Details:
{json.dumps(alert.details, indent=2)}

This is an automated alert from Bella V3 monitoring system.
        """

        msg = EmailMessage()
        msg['From'] = smtp_user
        msg['To'] = alert_email
        msg['Subject'] = subject
        msg.set_content(body)

        try:
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.send_message(msg)
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")

    async def _send_sms_notification(self, alert: Alert):
        """Send SMS notification (Twilio-based)"""
        # This would integrate with Twilio for SMS alerts
        # Implementation depends on having Twilio credentials configured
        logger.info(f"SMS notification would be sent for alert: {alert.id}")

    async def start_notification_worker(self):
        """Background worker to process notification queue"""
        logger.info("Starting alert notification worker")

        while True:
            try:
                # Wait for alerts with timeout
                alert = await asyncio.wait_for(
                    self._notification_queue.get(),
                    timeout=60.0
                )

                await self.send_notification(alert)
                self._notification_queue.task_done()

            except asyncio.TimeoutError:
                # Periodic health check when no alerts
                await self._periodic_health_check()
            except Exception as e:
                logger.error(f"Error in notification worker: {e}")
                await asyncio.sleep(5)

    async def _periodic_health_check(self):
        """Periodic system health check"""
        # This runs when no alerts are being processed
        # Check for stale alerts, SLA violations, etc.
        current_time = datetime.utcnow()

        # Check for alerts that need escalation
        for alert in self._active_alerts.values():
            time_since_alert = (current_time - alert.timestamp).total_seconds() / 60
            escalation_rules = self._escalation_rules.get(alert.severity, [])

            for rule in escalation_rules:
                if (alert.escalation_level == rule["level"] and
                    time_since_alert >= rule["delay_minutes"]):
                    alert.escalation_level += 1
                    alert.notification_channels = rule["channels"]
                    await self._notification_queue.put(alert)
                    logger.info(f"Escalated alert {alert.id} to level {alert.escalation_level}")
                    break

    def get_alert_summary(self) -> Dict[str, Any]:
        """Get current alert summary"""
        active_by_severity = defaultdict(int)
        for alert in self._active_alerts.values():
            active_by_severity[alert.severity] += 1

        recent_alerts = [
            alert for alert in self._alert_history
            if (datetime.utcnow() - alert.timestamp).total_seconds() < 3600  # Last hour
        ]

        return {
            "active_alerts": {
                "total": len(self._active_alerts),
                "critical": active_by_severity["critical"],
                "high": active_by_severity["high"],
                "medium": active_by_severity["medium"],
                "low": active_by_severity["low"]
            },
            "recent_alerts": len(recent_alerts),
            "oldest_unresolved": min(
                [alert.timestamp for alert in self._active_alerts.values()],
                default=datetime.utcnow()
            ).isoformat(),
            "notification_queue_size": self._notification_queue.qsize()
        }

# Global alert manager instance
alert_manager = AlertManager()
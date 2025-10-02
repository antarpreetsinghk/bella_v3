#!/usr/bin/env python3
"""
AWS CloudWatch integration for Bella V3 package-level monitoring.
Provides comprehensive monitoring, alerting, and dashboard configuration.
"""

import boto3
import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import os

from app.core.config import settings
from app.core.metrics import metrics_collector
from app.services.alerting import alert_manager

logger = logging.getLogger(__name__)

@dataclass
class CloudWatchMetric:
    """CloudWatch metric definition"""
    namespace: str
    metric_name: str
    value: float
    unit: str
    dimensions: Dict[str, str]
    timestamp: Optional[datetime] = None

@dataclass
class CloudWatchAlarm:
    """CloudWatch alarm configuration"""
    alarm_name: str
    description: str
    metric_name: str
    namespace: str
    statistic: str
    threshold: float
    comparison_operator: str
    evaluation_periods: int
    period: int
    dimensions: Dict[str, str] = None
    treat_missing_data: str = "breaching"

class CloudWatchMonitoring:
    """
    Production-grade CloudWatch monitoring for Bella V3 packages.
    Provides package-level metrics, alarms, and dashboards.
    """

    def __init__(self):
        self.cloudwatch = boto3.client('cloudwatch', region_name='ca-central-1')
        self.logs_client = boto3.client('logs', region_name='ca-central-1')

        # Package namespace mapping
        self.package_namespaces = {
            'api': 'Bella/API',
            'services': 'Bella/Services',
            'core': 'Bella/Core',
            'db': 'Bella/Database',
            'voice': 'Bella/Voice',
            'ai': 'Bella/AI',
            'admin': 'Bella/Admin'
        }

        # Metric definitions by package
        self.package_metrics = self._define_package_metrics()

        # Alarm configurations
        self.alarm_configs = self._define_alarm_configs()

    def _define_package_metrics(self) -> Dict[str, List[CloudWatchMetric]]:
        """Define metrics for each package"""
        return {
            'api': [
                'RequestCount', 'ResponseTime', 'ErrorRate', 'ActiveConnections',
                'TwilioWebhookLatency', 'AdminLoginCount', 'APIKeyUsage'
            ],
            'services': [
                'OpenAIAPILatency', 'OpenAITokenUsage', 'ExtractionAccuracy',
                'CalendarIntegrationLatency', 'SMSDeliveryRate', 'CacheHitRate'
            ],
            'core': [
                'SystemHealth', 'BusinessRuleViolations', 'ConfigurationErrors',
                'PerformanceDegradation', 'CircuitBreakerState'
            ],
            'db': [
                'ConnectionPoolUsage', 'QueryLatency', 'TransactionCount',
                'DatabaseErrors', 'MigrationStatus', 'DataIntegrity'
            ],
            'voice': [
                'CallVolume', 'SpeechRecognitionAccuracy', 'CallDuration',
                'VoiceProcessingLatency', 'CanadianEnglishProcessing'
            ],
            'ai': [
                'NameExtractionAccuracy', 'TimeParsingSuccess', 'PhoneNumberValidation',
                'ArtifactFilteringEffectiveness', 'LLMResponseTime'
            ],
            'admin': [
                'DashboardLoadTime', 'UserSessionDuration', 'AdminActionCount',
                'DataExportCount', 'SecurityEvents'
            ]
        }

    def _define_alarm_configs(self) -> List[CloudWatchAlarm]:
        """Define CloudWatch alarms for package monitoring"""
        return [
            # API Package Alarms
            CloudWatchAlarm(
                alarm_name="Bella-API-HighErrorRate",
                description="API error rate exceeds 5%",
                metric_name="ErrorRate",
                namespace="Bella/API",
                statistic="Average",
                threshold=5.0,
                comparison_operator="GreaterThanThreshold",
                evaluation_periods=2,
                period=300
            ),
            CloudWatchAlarm(
                alarm_name="Bella-API-HighLatency",
                description="API response time exceeds 2 seconds",
                metric_name="ResponseTime",
                namespace="Bella/API",
                statistic="Average",
                threshold=2000.0,
                comparison_operator="GreaterThanThreshold",
                evaluation_periods=3,
                period=300
            ),

            # Services Package Alarms
            CloudWatchAlarm(
                alarm_name="Bella-Services-OpenAI-Latency",
                description="OpenAI API latency exceeds 5 seconds",
                metric_name="OpenAIAPILatency",
                namespace="Bella/Services",
                statistic="Average",
                threshold=5000.0,
                comparison_operator="GreaterThanThreshold",
                evaluation_periods=2,
                period=300
            ),
            CloudWatchAlarm(
                alarm_name="Bella-Services-ExtractionAccuracy",
                description="Name extraction accuracy below 85%",
                metric_name="ExtractionAccuracy",
                namespace="Bella/Services",
                statistic="Average",
                threshold=85.0,
                comparison_operator="LessThanThreshold",
                evaluation_periods=3,
                period=600
            ),

            # Database Package Alarms
            CloudWatchAlarm(
                alarm_name="Bella-DB-ConnectionPool",
                description="Database connection pool usage exceeds 80%",
                metric_name="ConnectionPoolUsage",
                namespace="Bella/Database",
                statistic="Average",
                threshold=80.0,
                comparison_operator="GreaterThanThreshold",
                evaluation_periods=2,
                period=300
            ),
            CloudWatchAlarm(
                alarm_name="Bella-DB-QueryLatency",
                description="Database query latency exceeds 1 second",
                metric_name="QueryLatency",
                namespace="Bella/Database",
                statistic="Average",
                threshold=1000.0,
                comparison_operator="GreaterThanThreshold",
                evaluation_periods=3,
                period=300
            ),

            # Voice Processing Alarms
            CloudWatchAlarm(
                alarm_name="Bella-Voice-RecognitionAccuracy",
                description="Speech recognition accuracy below 90%",
                metric_name="SpeechRecognitionAccuracy",
                namespace="Bella/Voice",
                statistic="Average",
                threshold=90.0,
                comparison_operator="LessThanThreshold",
                evaluation_periods=3,
                period=600
            ),

            # AI Package Alarms
            CloudWatchAlarm(
                alarm_name="Bella-AI-ArtifactFiltering",
                description="Artifact filtering effectiveness below 95%",
                metric_name="ArtifactFilteringEffectiveness",
                namespace="Bella/AI",
                statistic="Average",
                threshold=95.0,
                comparison_operator="LessThanThreshold",
                evaluation_periods=2,
                period=600
            )
        ]

    async def publish_package_metrics(self, package: str, metrics_data: Dict[str, Any]):
        """Publish package-specific metrics to CloudWatch"""
        if package not in self.package_namespaces:
            logger.warning(f"Unknown package: {package}")
            return

        namespace = self.package_namespaces[package]
        timestamp = datetime.utcnow()

        metric_data = []

        # Convert metrics to CloudWatch format
        for metric_name, value in metrics_data.items():
            if not isinstance(value, (int, float)):
                continue

            metric_data.append({
                'MetricName': metric_name,
                'Value': float(value),
                'Unit': self._get_metric_unit(metric_name),
                'Timestamp': timestamp,
                'Dimensions': [
                    {'Name': 'Package', 'Value': package},
                    {'Name': 'Environment', 'Value': settings.APP_ENV},
                    {'Name': 'Service', 'Value': 'bella-v3'}
                ]
            })

        # Batch publish metrics (max 20 per call)
        for i in range(0, len(metric_data), 20):
            batch = metric_data[i:i+20]
            try:
                self.cloudwatch.put_metric_data(
                    Namespace=namespace,
                    MetricData=batch
                )
                logger.debug(f"Published {len(batch)} metrics to {namespace}")
            except Exception as e:
                logger.error(f"Failed to publish metrics to CloudWatch: {e}")

    def _get_metric_unit(self, metric_name: str) -> str:
        """Determine appropriate CloudWatch unit for metric"""
        unit_mapping = {
            'latency': 'Milliseconds',
            'time': 'Milliseconds',
            'duration': 'Milliseconds',
            'count': 'Count',
            'rate': 'Percent',
            'accuracy': 'Percent',
            'usage': 'Percent',
            'pool': 'Percent',
            'volume': 'Count',
            'errors': 'Count'
        }

        metric_lower = metric_name.lower()
        for key, unit in unit_mapping.items():
            if key in metric_lower:
                return unit

        return 'None'  # Default unit

    async def create_alarms(self):
        """Create CloudWatch alarms for package monitoring"""
        for alarm_config in self.alarm_configs:
            try:
                self.cloudwatch.put_metric_alarm(
                    AlarmName=alarm_config.alarm_name,
                    AlarmDescription=alarm_config.description,
                    MetricName=alarm_config.metric_name,
                    Namespace=alarm_config.namespace,
                    Statistic=alarm_config.statistic,
                    Threshold=alarm_config.threshold,
                    ComparisonOperator=alarm_config.comparison_operator,
                    EvaluationPeriods=alarm_config.evaluation_periods,
                    Period=alarm_config.period,
                    TreatMissingData=alarm_config.treat_missing_data,
                    Dimensions=alarm_config.dimensions or []
                )
                logger.info(f"Created CloudWatch alarm: {alarm_config.alarm_name}")
            except Exception as e:
                logger.error(f"Failed to create alarm {alarm_config.alarm_name}: {e}")

    async def create_dashboard(self) -> str:
        """Create comprehensive CloudWatch dashboard for package monitoring"""
        dashboard_body = {
            "widgets": [
                # API Package Widgets
                {
                    "type": "metric",
                    "x": 0, "y": 0, "width": 12, "height": 6,
                    "properties": {
                        "metrics": [
                            ["Bella/API", "RequestCount", "Package", "api"],
                            [".", "ErrorRate", ".", "."],
                            [".", "ResponseTime", ".", "."]
                        ],
                        "view": "timeSeries",
                        "stacked": False,
                        "region": "ca-central-1",
                        "title": "API Package - Core Metrics",
                        "period": 300
                    }
                },

                # Services Package Widgets
                {
                    "type": "metric",
                    "x": 12, "y": 0, "width": 12, "height": 6,
                    "properties": {
                        "metrics": [
                            ["Bella/Services", "OpenAIAPILatency", "Package", "services"],
                            [".", "ExtractionAccuracy", ".", "."],
                            [".", "CacheHitRate", ".", "."]
                        ],
                        "view": "timeSeries",
                        "stacked": False,
                        "region": "ca-central-1",
                        "title": "Services Package - AI & External APIs",
                        "period": 300
                    }
                },

                # Database Package Widgets
                {
                    "type": "metric",
                    "x": 0, "y": 6, "width": 12, "height": 6,
                    "properties": {
                        "metrics": [
                            ["Bella/Database", "ConnectionPoolUsage", "Package", "db"],
                            [".", "QueryLatency", ".", "."],
                            [".", "TransactionCount", ".", "."]
                        ],
                        "view": "timeSeries",
                        "stacked": False,
                        "region": "ca-central-1",
                        "title": "Database Package - Performance",
                        "period": 300
                    }
                },

                # Voice Processing Widgets
                {
                    "type": "metric",
                    "x": 12, "y": 6, "width": 12, "height": 6,
                    "properties": {
                        "metrics": [
                            ["Bella/Voice", "CallVolume", "Package", "voice"],
                            [".", "SpeechRecognitionAccuracy", ".", "."],
                            [".", "VoiceProcessingLatency", ".", "."]
                        ],
                        "view": "timeSeries",
                        "stacked": False,
                        "region": "ca-central-1",
                        "title": "Voice Package - Twilio Integration",
                        "period": 300
                    }
                },

                # AI Package Widgets
                {
                    "type": "metric",
                    "x": 0, "y": 12, "width": 12, "height": 6,
                    "properties": {
                        "metrics": [
                            ["Bella/AI", "NameExtractionAccuracy", "Package", "ai"],
                            [".", "ArtifactFilteringEffectiveness", ".", "."],
                            [".", "LLMResponseTime", ".", "."]
                        ],
                        "view": "timeSeries",
                        "stacked": False,
                        "region": "ca-central-1",
                        "title": "AI Package - Extraction & Processing",
                        "period": 300
                    }
                },

                # Admin Package Widgets
                {
                    "type": "metric",
                    "x": 12, "y": 12, "width": 12, "height": 6,
                    "properties": {
                        "metrics": [
                            ["Bella/Admin", "DashboardLoadTime", "Package", "admin"],
                            [".", "UserSessionDuration", ".", "."],
                            [".", "SecurityEvents", ".", "."]
                        ],
                        "view": "timeSeries",
                        "stacked": False,
                        "region": "ca-central-1",
                        "title": "Admin Package - Dashboard & Security",
                        "period": 300
                    }
                },

                # System Overview
                {
                    "type": "metric",
                    "x": 0, "y": 18, "width": 24, "height": 6,
                    "properties": {
                        "metrics": [
                            ["Bella/Core", "SystemHealth", "Package", "core"],
                            ["Bella/API", "RequestCount", "Package", "api"],
                            ["Bella/Database", "ConnectionPoolUsage", "Package", "db"],
                            ["Bella/Voice", "CallVolume", "Package", "voice"]
                        ],
                        "view": "timeSeries",
                        "stacked": False,
                        "region": "ca-central-1",
                        "title": "System Overview - All Packages",
                        "period": 300,
                        "stat": "Average"
                    }
                }
            ]
        }

        dashboard_name = f"Bella-V3-Package-Monitoring-{settings.APP_ENV}"

        try:
            self.cloudwatch.put_dashboard(
                DashboardName=dashboard_name,
                DashboardBody=json.dumps(dashboard_body)
            )
            logger.info(f"Created CloudWatch dashboard: {dashboard_name}")
            return dashboard_name
        except Exception as e:
            logger.error(f"Failed to create dashboard: {e}")
            return ""

    async def setup_log_groups(self):
        """Setup CloudWatch log groups for each package"""
        log_groups = [
            f"/bella/api/{settings.APP_ENV}",
            f"/bella/services/{settings.APP_ENV}",
            f"/bella/core/{settings.APP_ENV}",
            f"/bella/database/{settings.APP_ENV}",
            f"/bella/voice/{settings.APP_ENV}",
            f"/bella/ai/{settings.APP_ENV}",
            f"/bella/admin/{settings.APP_ENV}"
        ]

        for log_group in log_groups:
            try:
                self.logs_client.create_log_group(
                    logGroupName=log_group,
                    tags={
                        'Environment': settings.APP_ENV,
                        'Service': 'bella-v3',
                        'Purpose': 'package-monitoring'
                    }
                )

                # Set retention policy (30 days for prod, 7 days for dev)
                retention_days = 30 if settings.APP_ENV == 'production' else 7
                self.logs_client.put_retention_policy(
                    logGroupName=log_group,
                    retentionInDays=retention_days
                )

                logger.info(f"Created log group: {log_group}")
            except self.logs_client.exceptions.ResourceAlreadyExistsException:
                logger.debug(f"Log group already exists: {log_group}")
            except Exception as e:
                logger.error(f"Failed to create log group {log_group}: {e}")

    async def send_metric_to_cloudwatch(self, package: str, metric_name: str,
                                      value: float, unit: str = "Count"):
        """Send individual metric to CloudWatch"""
        if package not in self.package_namespaces:
            return

        namespace = self.package_namespaces[package]

        try:
            self.cloudwatch.put_metric_data(
                Namespace=namespace,
                MetricData=[{
                    'MetricName': metric_name,
                    'Value': value,
                    'Unit': unit,
                    'Timestamp': datetime.utcnow(),
                    'Dimensions': [
                        {'Name': 'Package', 'Value': package},
                        {'Name': 'Environment', 'Value': settings.APP_ENV}
                    ]
                }]
            )
        except Exception as e:
            logger.error(f"Failed to send metric {metric_name}: {e}")

    async def get_package_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of package metrics from CloudWatch"""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=1)

        summary = {}

        for package, namespace in self.package_namespaces.items():
            try:
                # Get basic metrics for each package
                response = self.cloudwatch.get_metric_statistics(
                    Namespace=namespace,
                    MetricName='RequestCount',
                    Dimensions=[
                        {'Name': 'Package', 'Value': package}
                    ],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=3600,
                    Statistics=['Sum']
                )

                datapoints = response.get('Datapoints', [])
                request_count = datapoints[0]['Sum'] if datapoints else 0

                summary[package] = {
                    'request_count': request_count,
                    'namespace': namespace,
                    'status': 'healthy'  # Would be determined by alarm states
                }

            except Exception as e:
                logger.error(f"Failed to get metrics for package {package}: {e}")
                summary[package] = {
                    'request_count': 0,
                    'namespace': namespace,
                    'status': 'unknown'
                }

        return summary

# Global CloudWatch monitoring instance
cloudwatch_monitor = CloudWatchMonitoring()

class PackageMetricsCollector:
    """Collect and send package-specific metrics to CloudWatch"""

    def __init__(self):
        self.monitor = cloudwatch_monitor

    async def collect_api_metrics(self):
        """Collect API package metrics"""
        base_metrics = metrics_collector.get_metrics()

        api_metrics = {
            'RequestCount': base_metrics['total_requests'],
            'ResponseTime': base_metrics['avg_response_time'],
            'ErrorRate': base_metrics['error_rate'],
            'ActiveConnections': base_metrics['active_sessions'],
            'SlowRequests': base_metrics['slow_requests']
        }

        await self.monitor.publish_package_metrics('api', api_metrics)

    async def collect_services_metrics(self):
        """Collect Services package metrics"""
        # These would be populated by actual service metrics
        services_metrics = {
            'OpenAIAPILatency': 1500,  # Placeholder
            'ExtractionAccuracy': 92.5,
            'CacheHitRate': 85.0,
            'CalendarIntegrationLatency': 800
        }

        await self.monitor.publish_package_metrics('services', services_metrics)

    async def collect_database_metrics(self):
        """Collect Database package metrics"""
        # These would come from actual database monitoring
        db_metrics = {
            'ConnectionPoolUsage': 45.0,
            'QueryLatency': 250,
            'TransactionCount': 150,
            'DatabaseErrors': 0
        }

        await self.monitor.publish_package_metrics('db', db_metrics)

    async def collect_all_package_metrics(self):
        """Collect metrics from all packages"""
        await asyncio.gather(
            self.collect_api_metrics(),
            self.collect_services_metrics(),
            self.collect_database_metrics()
        )

# Global package metrics collector
package_metrics_collector = PackageMetricsCollector()
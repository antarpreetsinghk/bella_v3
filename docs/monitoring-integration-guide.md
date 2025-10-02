# 🔍 CloudWatch Monitoring Integration Guide

## Overview

This guide provides comprehensive instructions for integrating CloudWatch monitoring into Bella V3 at the package level. It covers setup, configuration, best practices, and troubleshooting.

## 🚀 Quick Setup

### Prerequisites

1. **AWS CLI configured** with appropriate permissions
2. **Python dependencies** installed
3. **Environment variables** configured

```bash
# Required AWS permissions
aws iam attach-user-policy --user-name bella-monitoring \
  --policy-arn arn:aws:iam::aws:policy/CloudWatchFullAccess

# Install monitoring dependencies
pip install boto3 structlog

# Set environment variables
export AWS_DEFAULT_REGION=ca-central-1
export BELLA_API_KEY=your-api-key
export APP_ENV=production
```

### 1. Setup CloudWatch Infrastructure

```bash
# Make setup script executable
chmod +x scripts/setup-cloudwatch-monitoring.py

# Run full setup
python scripts/setup-cloudwatch-monitoring.py --action setup --environment production

# Verify setup
python scripts/setup-cloudwatch-monitoring.py --action verify
```

Expected output:
```
🚀 Starting CloudWatch monitoring setup for production
✅ Log groups created successfully
✅ CloudWatch alarms created successfully
✅ Dashboard created successfully: Bella-V3-Package-Monitoring-production
✅ Metrics collection test successful
🎉 Full monitoring setup completed successfully!
```

### 2. Start Metrics Collection Service

```bash
# Start the metrics collector as a background service
python scripts/metrics-collector.py --interval 60 --verbose &

# Check if service is running
ps aux | grep metrics-collector
```

## 📊 Package-Level Integration

### API Package Integration

**File**: `app/api/routes/twilio.py`

```python
from app.core.metrics import track_performance
from monitoring.cloudwatch_config import cloudwatch_monitor

@track_performance
async def voice_webhook(request: Request):
    """Enhanced with CloudWatch metrics"""
    start_time = time.time()

    try:
        # Your existing logic here
        result = await process_voice_call(request)

        # Send success metrics
        await cloudwatch_monitor.send_metric_to_cloudwatch(
            'api', 'TwilioWebhookSuccess', 1, 'Count'
        )

        return result

    except Exception as e:
        # Send error metrics
        await cloudwatch_monitor.send_metric_to_cloudwatch(
            'api', 'TwilioWebhookError', 1, 'Count'
        )
        raise
    finally:
        # Send latency metrics
        duration = (time.time() - start_time) * 1000
        await cloudwatch_monitor.send_metric_to_cloudwatch(
            'api', 'TwilioWebhookLatency', duration, 'Milliseconds'
        )
```

### Services Package Integration

**File**: `app/services/llm.py`

```python
from monitoring.cloudwatch_config import cloudwatch_monitor
import time

class LLMService:
    async def extract_appointment_info(self, transcript: str) -> dict:
        start_time = time.time()
        token_count = 0

        try:
            # Your existing LLM logic
            result = await self._call_openai_api(transcript)
            token_count = result.get('usage', {}).get('total_tokens', 0)

            # Calculate extraction accuracy
            accuracy = self._calculate_extraction_accuracy(result)

            # Send success metrics
            await cloudwatch_monitor.send_metric_to_cloudwatch(
                'services', 'ExtractionAccuracy', accuracy, 'Percent'
            )

            await cloudwatch_monitor.send_metric_to_cloudwatch(
                'services', 'OpenAITokenUsage', token_count, 'Count'
            )

            return result

        except Exception as e:
            # Send error metrics
            await cloudwatch_monitor.send_metric_to_cloudwatch(
                'services', 'OpenAIAPIError', 1, 'Count'
            )
            raise
        finally:
            # Send latency metrics
            duration = (time.time() - start_time) * 1000
            await cloudwatch_monitor.send_metric_to_cloudwatch(
                'services', 'OpenAIAPILatency', duration, 'Milliseconds'
            )
```

### Database Package Integration

**File**: `app/db/session.py`

```python
from monitoring.cloudwatch_config import cloudwatch_monitor
from app.core.logging import get_logger

logger = get_logger(__name__)

class DatabaseMonitor:
    def __init__(self, engine):
        self.engine = engine

    async def get_pool_metrics(self):
        """Get connection pool metrics"""
        pool = self.engine.pool

        pool_size = pool.size()
        checked_in = pool.checkedin()
        checked_out = pool.checkedout()

        usage_percentage = (checked_out / pool_size) * 100 if pool_size > 0 else 0

        # Send pool metrics
        await cloudwatch_monitor.send_metric_to_cloudwatch(
            'db', 'ConnectionPoolUsage', usage_percentage, 'Percent'
        )

        await cloudwatch_monitor.send_metric_to_cloudwatch(
            'db', 'ActiveConnections', checked_out, 'Count'
        )

        # Alert if pool usage is high
        if usage_percentage > 80:
            logger.warning(f"High database connection pool usage: {usage_percentage:.1f}%")

# Middleware for query monitoring
async def query_monitor_middleware(query_func):
    start_time = time.time()

    try:
        result = await query_func()

        # Send success metrics
        await cloudwatch_monitor.send_metric_to_cloudwatch(
            'db', 'QuerySuccess', 1, 'Count'
        )

        return result

    except Exception as e:
        # Send error metrics
        await cloudwatch_monitor.send_metric_to_cloudwatch(
            'db', 'QueryError', 1, 'Count'
        )
        raise
    finally:
        duration = (time.time() - start_time) * 1000
        await cloudwatch_monitor.send_metric_to_cloudwatch(
            'db', 'QueryLatency', duration, 'Milliseconds'
        )
```

### Core Package Integration

**File**: `app/core/metrics.py` (Enhanced)

```python
from monitoring.cloudwatch_config import cloudwatch_monitor

class EnhancedMetricsCollector(MetricsCollector):
    """Enhanced metrics collector with CloudWatch integration"""

    async def publish_to_cloudwatch(self):
        """Publish collected metrics to CloudWatch"""
        metrics = self.get_metrics()

        # Publish core metrics
        await cloudwatch_monitor.publish_package_metrics('core', {
            'SystemHealth': self._calculate_system_health(),
            'ActiveSessions': metrics['active_sessions'],
            'TotalRequests': metrics['total_requests'],
            'ErrorRate': metrics['error_rate'],
            'AverageResponseTime': metrics['avg_response_time'] * 1000
        })

    def _calculate_system_health(self) -> float:
        """Calculate overall system health score"""
        metrics = self.get_metrics()

        # Health factors
        error_rate = metrics['error_rate']
        avg_response_time = metrics['avg_response_time']

        # Health score calculation (0-100)
        health_score = 100

        # Deduct for high error rate
        if error_rate > 1:
            health_score -= min(error_rate * 10, 50)

        # Deduct for slow response times
        if avg_response_time > 1.0:
            health_score -= min((avg_response_time - 1.0) * 20, 30)

        return max(health_score, 0)
```

## 📈 Dashboard Configuration

### Production Dashboard

Access your dashboard at:
```
https://ca-central-1.console.aws.amazon.com/cloudwatch/home?region=ca-central-1#dashboards:name=Bella-V3-Package-Monitoring-production
```

### Custom Metrics Widgets

**Example: API Performance Widget**
```json
{
  "type": "metric",
  "properties": {
    "metrics": [
      ["Bella/API", "RequestCount", "Package", "api"],
      [".", "ResponseTime", ".", "."],
      [".", "ErrorRate", ".", "."]
    ],
    "period": 300,
    "stat": "Average",
    "region": "ca-central-1",
    "title": "API Performance Overview"
  }
}
```

## 🚨 Alerting Configuration

### Critical Alerts

**API Error Rate Alert**:
- **Threshold**: > 5%
- **Evaluation**: 2 periods of 5 minutes
- **Action**: SNS notification + Slack

**Database Connection Pool Alert**:
- **Threshold**: > 80%
- **Evaluation**: 2 periods of 5 minutes
- **Action**: SNS notification + Email

**OpenAI API Latency Alert**:
- **Threshold**: > 5 seconds
- **Evaluation**: 2 periods of 5 minutes
- **Action**: SNS notification

### Warning Alerts

**Response Time Alert**:
- **Threshold**: > 2 seconds
- **Evaluation**: 3 periods of 5 minutes
- **Action**: Slack notification

**Extraction Accuracy Alert**:
- **Threshold**: < 85%
- **Evaluation**: 3 periods of 10 minutes
- **Action**: Slack notification

## 🔧 Advanced Configuration

### Custom Metric Dimensions

Add custom dimensions to metrics for better filtering:

```python
# Add environment and version dimensions
await cloudwatch_monitor.send_metric_to_cloudwatch(
    package='api',
    metric_name='CustomMetric',
    value=100,
    unit='Count',
    dimensions={
        'Environment': settings.APP_ENV,
        'Version': '3.0.0',
        'Feature': 'voice-booking'
    }
)
```

### Log Insights Queries

**Query for API errors**:
```
fields @timestamp, @message, correlation_id, error
| filter @message like /ERROR/
| filter endpoint like /\/api\//
| sort @timestamp desc
| limit 100
```

**Query for slow requests**:
```
fields @timestamp, endpoint, duration, correlation_id
| filter duration > 2000
| sort @timestamp desc
| limit 50
```

### Cost Optimization

**Set metric filters to reduce costs**:
```python
# Only send metrics for significant events
if error_rate > 0.1 or response_time > 1.0:
    await cloudwatch_monitor.send_metric_to_cloudwatch(
        'api', 'SignificantEvent', 1, 'Count'
    )
```

**Use metric aggregation**:
```python
# Batch metrics to reduce API calls
metrics_batch = {
    'RequestCount': request_count,
    'ErrorCount': error_count,
    'ResponseTimeSum': total_response_time
}
await cloudwatch_monitor.publish_package_metrics('api', metrics_batch)
```

## 🛠️ Troubleshooting

### Common Issues

**1. Metrics not appearing in CloudWatch**

```bash
# Check AWS credentials
aws sts get-caller-identity

# Verify metric publication
python -c "
import asyncio
from monitoring.cloudwatch_config import cloudwatch_monitor
asyncio.run(cloudwatch_monitor.send_metric_to_cloudwatch('test', 'TestMetric', 1))
"
```

**2. High CloudWatch costs**

```bash
# Check metric usage
aws logs describe-metric-filters --region ca-central-1

# Review published metrics
aws cloudwatch list-metrics --namespace Bella/API --region ca-central-1
```

**3. Missing alarms**

```bash
# List current alarms
aws cloudwatch describe-alarms --alarm-name-prefix "Bella-" --region ca-central-1

# Recreate alarms
python scripts/setup-cloudwatch-monitoring.py --action setup
```

### Debug Mode

Enable debug logging for troubleshooting:

```python
# In your application
import logging
logging.getLogger('monitoring').setLevel(logging.DEBUG)

# Run metrics collector in debug mode
python scripts/metrics-collector.py --verbose
```

### Health Checks

Verify monitoring health:

```bash
# Check service health
curl http://localhost:8000/healthz

# Check metrics endpoint
curl http://localhost:8000/metrics

# Verify CloudWatch connectivity
python scripts/setup-cloudwatch-monitoring.py --action verify
```

## 📚 Best Practices

### 1. Metric Naming Conventions

- Use PascalCase: `ResponseTime`, `ErrorRate`
- Be descriptive: `TwilioWebhookLatency` vs `Latency`
- Include units in name if ambiguous: `ResponseTimeMs`

### 2. Dimension Strategy

- Use consistent dimension names across packages
- Limit dimensions to reduce costs
- Include Environment, Service, Version

### 3. Alerting Strategy

- Alert on symptoms, not causes
- Use composite alarms for complex conditions
- Include runbook links in alarm descriptions
- Test alert channels regularly

### 4. Dashboard Design

- Organize by audience (executive, technical, operational)
- Use consistent time ranges
- Include context and thresholds
- Keep widgets focused and simple

### 5. Cost Management

- Set retention policies on log groups
- Use metric filters to reduce volume
- Batch metric publications
- Regular cleanup of unused resources

## 🔄 Maintenance Tasks

### Daily

- Review alert status
- Check dashboard for anomalies
- Verify metrics collection service

### Weekly

- Review metric costs
- Update alarm thresholds if needed
- Check for new error patterns

### Monthly

- Review and update dashboards
- Optimize metric collection
- Update documentation
- Performance review of monitoring system

## 📞 Support and Escalation

### Internal Escalation

1. **Level 1**: Check dashboards and recent alerts
2. **Level 2**: Review CloudWatch logs and metrics
3. **Level 3**: Contact AWS support if infrastructure issue

### External Resources

- **AWS CloudWatch Documentation**: https://docs.aws.amazon.com/cloudwatch/
- **Bella V3 Monitoring Runbook**: [Internal Wiki]
- **On-call Contact**: monitoring@bella-dental.com

---

This monitoring integration provides comprehensive visibility into Bella V3's performance and health at the package level, enabling proactive issue detection and resolution.
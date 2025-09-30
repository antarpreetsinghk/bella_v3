# Bella V3 API Documentation

> **Complete API Reference for Bella V3 Voice Appointment Booking System**
> Enterprise-grade monitoring, alerting, and optimization APIs

## Table of Contents

- [Authentication](#authentication)
- [Unified Dashboard APIs](#unified-dashboard-apis)
- [Monitoring & Metrics](#monitoring--metrics)
- [Alerting System](#alerting-system)
- [Circuit Breakers](#circuit-breakers)
- [Cost Optimization](#cost-optimization)
- [Business Metrics](#business-metrics)
- [Voice Call Processing](#voice-call-processing)
- [Appointment Management](#appointment-management)
- [Error Handling](#error-handling)

---

## Authentication

All API endpoints (except public routes) require the `X-API-Key` header.

```bash
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/endpoint
```

### Public Endpoints (No Auth Required)
- `GET /healthz` - Basic health check
- `GET /readyz` - Database connectivity check
- `GET /metrics` - Internal metrics (monitoring)
- `POST /twilio/*` - Twilio webhook handlers (signature verified)

---

## Unified Dashboard APIs

### Get System Status
**Endpoint**: `GET /api/unified/status`
**Purpose**: Overall system health for dashboard header indicators

```bash
curl -H "X-API-Key: $API_KEY" http://localhost:8000/api/unified/status
```

**Response**:
```json
{
  "system": "healthy|warning|error",
  "performance": "healthy|warning|error",
  "redis": "healthy|warning",
  "circuit_breakers": "healthy|warning|error",
  "openai_service": "closed|half_open|open",
  "cost_aws_connected": true,
  "timestamp": "2025-09-30T14:30:00Z"
}
```

### Dashboard Tabs Data

#### Operations Tab
**Endpoint**: `GET /api/unified/operations`
```bash
curl -H "X-API-Key: $API_KEY" http://localhost:8000/api/unified/operations
```

**Response**:
```json
{
  "total_users": 42,
  "total_appts": 156,
  "today_appts": 8,
  "recent_appointments": [
    {
      "id": 123,
      "starts_at": "2025-09-30T15:00:00Z",
      "duration_min": 30,
      "status": "booked",
      "full_name": "John Smith",
      "mobile": "+1234567890"
    }
  ]
}
```

#### Analytics Tab
**Endpoint**: `GET /api/unified/analytics`
```bash
curl -H "X-API-Key: $API_KEY" http://localhost:8000/api/unified/analytics
```

**Response**:
```json
{
  "aws_available": false,
  "monthly_costs": {"Mock Service": 50.0},
  "total_monthly": 50.0,
  "optimization_potential": 0.4
}
```

#### System Tab
**Endpoint**: `GET /api/unified/system`
```bash
curl -H "X-API-Key: $API_KEY" http://localhost:8000/api/unified/system
```

**Response**:
```json
{
  "performance": {
    "avg_response_time": 0.213,
    "total_requests": 1420,
    "error_rate": 0.02
  },
  "cache": {
    "hit_rate": 0.85,
    "total_hits": 340,
    "total_misses": 60
  },
  "status": "healthy"
}
```

---

## Monitoring & Metrics

### Business Metrics
**Endpoint**: `GET /api/unified/business-metrics`
**Purpose**: Current business KPIs and performance metrics

```bash
curl -H "X-API-Key: $API_KEY" http://localhost:8000/api/unified/business-metrics
```

**Response**:
```json
{
  "total_calls": 450,
  "completed_calls": 428,
  "failed_calls": 22,
  "success_rate": 0.951,
  "avg_response_time": 1.8,
  "completion_rate": 0.951,
  "speech_recognition_accuracy": 0.89,
  "ai_extraction_success_rate": 0.94,
  "fallback_usage_rate": 0.12,
  "cost_per_call": 0.08,
  "whisper_api_calls": 450,
  "calculated_at": "2025-09-30T14:30:00Z"
}
```

### Performance Trends
**Endpoint**: `GET /api/unified/trends?hours={hours}`
**Purpose**: Hourly performance trends for visualization

```bash
curl -H "X-API-Key: $API_KEY" http://localhost:8000/api/unified/trends?hours=24
```

**Response**:
```json
{
  "trends": [
    {
      "hour": "2025-09-30T13:00:00Z",
      "total_calls": 12,
      "successful_calls": 11,
      "failed_calls": 1,
      "success_rate": 0.917,
      "speech_accuracy": 0.88,
      "cost": 0.96
    }
  ],
  "period_hours": 24
}
```

---

## Alerting System

### Get Active Alerts
**Endpoint**: `GET /api/unified/alerts`
**Purpose**: Current active alerts and alert summary

```bash
curl -H "X-API-Key: $API_KEY" http://localhost:8000/api/unified/alerts
```

**Response**:
```json
{
  "alert_summary": {
    "active_alerts": {
      "total": 2,
      "critical": 0,
      "high": 1,
      "medium": 1,
      "low": 0
    },
    "recent_alerts": 5,
    "oldest_unresolved": "2025-09-30T13:45:00Z",
    "notification_queue_size": 0
  },
  "sla_status": {
    "overall_health_score": 98.5,
    "services": {...}
  },
  "overall_health": 98.5
}
```

### Create Alert
**Endpoint**: `POST /api/unified/alerts`
**Purpose**: Create a manual alert

```bash
curl -X POST -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  http://localhost:8000/api/unified/alerts -d '{
    "component": "manual_intervention",
    "severity": "medium",
    "message": "Manual maintenance alert",
    "details": {
      "operator": "ops-team",
      "maintenance_type": "scheduled"
    }
  }'
```

**Response**:
```json
{
  "alert_id": "manual_intervention:medium:1234",
  "status": "created"
}
```

### Resolve Alert
**Endpoint**: `PATCH /api/unified/alerts/{alert_id}/resolve`
**Purpose**: Mark an alert as resolved

```bash
curl -X PATCH -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  http://localhost:8000/api/unified/alerts/alert_id_here/resolve -d '{
    "note": "Issue resolved by restarting service"
  }'
```

**Response**:
```json
{
  "status": "resolved",
  "alert_id": "alert_id_here"
}
```

### SLA Metrics
**Endpoint**: `GET /api/unified/sla-metrics`
**Purpose**: Detailed SLA metrics for all monitored services

```bash
curl -H "X-API-Key: $API_KEY" http://localhost:8000/api/unified/sla-metrics
```

**Response**:
```json
{
  "overall_health_score": 99.2,
  "services": {
    "overall_uptime": {
      "current_sla": 99.95,
      "target_sla": 99.9,
      "status": "healthy",
      "uptime_minutes": 1438,
      "downtime_minutes": 2,
      "total_minutes": 1440,
      "breach_count": 1,
      "last_breach": "2025-09-30T02:15:00Z"
    },
    "call_success_rate": {
      "current_sla": 96.2,
      "target_sla": 95.0,
      "status": "healthy",
      "uptime_minutes": 433,
      "downtime_minutes": 17,
      "total_minutes": 450,
      "breach_count": 3,
      "last_breach": null
    }
  },
  "active_alerts": 1,
  "critical_alerts": 0,
  "generated_at": "2025-09-30T14:30:00Z"
}
```

---

## Circuit Breakers

### Get Circuit Breaker Status
**Endpoint**: `GET /api/unified/circuit-breakers`
**Purpose**: Status of all circuit breakers protecting external services

```bash
curl -H "X-API-Key: $API_KEY" http://localhost:8000/api/unified/circuit-breakers
```

**Response**:
```json
{
  "openai_api": {
    "name": "openai_api",
    "state": "closed",
    "total_requests": 450,
    "successful_requests": 428,
    "failed_requests": 22,
    "success_rate": 0.951,
    "circuit_opened_count": 2,
    "current_failure_streak": 0,
    "last_failure_time": 1696084200.123,
    "last_success_time": 1696087800.456,
    "time_in_current_state": 3600.789
  },
  "twilio_api": {
    "name": "twilio_api",
    "state": "closed",
    "total_requests": 89,
    "successful_requests": 89,
    "failed_requests": 0,
    "success_rate": 1.0,
    "circuit_opened_count": 0,
    "current_failure_streak": 0,
    "last_failure_time": null,
    "last_success_time": 1696087800.123,
    "time_in_current_state": 7200.456
  },
  "database": {
    "name": "database",
    "state": "closed",
    "total_requests": 2840,
    "successful_requests": 2840,
    "failed_requests": 0,
    "success_rate": 1.0,
    "circuit_opened_count": 0,
    "current_failure_streak": 0,
    "last_failure_time": null,
    "last_success_time": 1696087800.789,
    "time_in_current_state": 14400.123
  }
}
```

**Circuit Breaker States**:
- `closed`: Normal operation (healthy)
- `half_open`: Testing recovery after failure
- `open`: Blocking requests due to repeated failures

---

## Cost Optimization

### Get Cost Optimization Dashboard
**Endpoint**: `GET /api/unified/cost-optimization`
**Purpose**: Complete cost analysis with recommendations

```bash
curl -H "X-API-Key: $API_KEY" http://localhost:8000/api/unified/cost-optimization
```

**Response**:
```json
{
  "cost_summary": {
    "current_period": {
      "whisper_api_cost": 32.40,
      "infrastructure_cost": 8.50,
      "storage_cost": 1.20,
      "network_cost": 2.90,
      "total_cost": 45.00,
      "period_days": 28
    },
    "recent_trends": {
      "total_cost_last_30d": 45.00,
      "avg_daily_cost": 1.61,
      "projected_monthly": 48.30,
      "budget_utilization": 0.966,
      "budget_remaining": 1.70
    },
    "cost_per_service": {
      "whisper_api_percentage": 72.0,
      "infrastructure_percentage": 18.9,
      "storage_percentage": 2.7,
      "network_percentage": 6.4
    }
  },
  "usage_patterns": {
    "usage_statistics": {
      "avg_hourly_calls": 2.8,
      "max_hourly_calls": 12,
      "peak_concurrent_calls": 3,
      "peak_hours": [9, 10, 11, 14, 15, 16],
      "total_weekly_calls": 470
    },
    "efficiency_metrics": {
      "utilization_rate": 0.23,
      "peak_to_average_ratio": 4.3
    }
  },
  "recommendations": [
    {
      "component": "whisper_api",
      "current": 100,
      "recommended": 80,
      "reason": "High Whisper API usage - consider caching optimizations",
      "savings": 6.48,
      "confidence": 0.6
    }
  ],
  "alerts": [],
  "optimization_score": 75,
  "generated_at": "2025-09-30T14:30:00Z"
}
```

---

## Business Metrics

### Get Performance Alerts
**Endpoint**: `GET /api/unified/alerts` (Legacy endpoint for business metrics alerts)

```bash
curl -H "X-API-Key: $API_KEY" http://localhost:8000/api/unified/alerts
```

**Response**:
```json
{
  "alerts": [
    {
      "type": "success_rate",
      "severity": "medium",
      "message": "Call success rate is 89.2% (target: >90%)",
      "value": 0.892,
      "threshold": 0.9
    },
    {
      "type": "response_time",
      "severity": "high",
      "message": "Average response time is 3.2s (target: <2s)",
      "value": 3.2,
      "threshold": 2.0
    }
  ],
  "alert_count": 2,
  "has_critical": false
}
```

---

## Voice Call Processing

### Twilio Webhook Endpoints
These endpoints are called by Twilio during voice calls. They use signature verification instead of API keys.

#### Voice Entry Point
**Endpoint**: `POST /twilio/voice`
**Purpose**: Initial call handling and greeting

**Twilio Parameters** (Form data):
- `CallSid`: Unique call identifier
- `From`: Caller's phone number
- `To`: Twilio number called

**Response**: TwiML XML for call flow

#### Speech Collection
**Endpoint**: `POST /twilio/voice/collect`
**Purpose**: Process speech input and extract appointment details

**Twilio Parameters**:
- `CallSid`: Call identifier
- `SpeechResult`: Transcribed speech (optional)
- `RecordingUrl`: Audio recording URL (optional)

**Response**: TwiML XML for next step or completion

---

## Appointment Management

### Create Appointment
**Endpoint**: `POST /appointments`
**Auth**: API Key required

```bash
curl -X POST -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  http://localhost:8000/appointments -d '{
    "user_id": 123,
    "starts_at": "2025-10-01T15:00:00Z",
    "duration_min": 30,
    "notes": "Follow-up appointment"
  }'
```

### Get Appointments
**Endpoint**: `GET /appointments`
**Auth**: API Key required

```bash
curl -H "X-API-Key: $API_KEY" http://localhost:8000/appointments?limit=10
```

### Update Appointment
**Endpoint**: `PUT /appointments/{id}`
**Auth**: API Key required

```bash
curl -X PUT -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  http://localhost:8000/appointments/123 -d '{
    "starts_at": "2025-10-01T16:00:00Z",
    "status": "confirmed"
  }'
```

---

## Error Handling

### Standard Error Response
```json
{
  "detail": "Error description",
  "error_code": "SPECIFIC_ERROR_CODE",
  "timestamp": "2025-09-30T14:30:00Z",
  "correlation_id": "abc123def456"
}
```

### HTTP Status Codes
- **200**: Success
- **201**: Created successfully
- **400**: Bad request (invalid parameters)
- **401**: Unauthorized (missing/invalid API key)
- **403**: Forbidden (Twilio signature validation failed)
- **404**: Resource not found
- **409**: Conflict (e.g., appointment time conflict)
- **422**: Unprocessable entity (validation errors)
- **500**: Internal server error
- **503**: Service unavailable (circuit breaker open)

### Common Error Scenarios

#### Invalid API Key
```bash
# Request without API key
curl http://localhost:8000/api/unified/status

# Response: 401
{
  "detail": "Invalid or missing API key"
}
```

#### Circuit Breaker Open
```bash
# When OpenAI service is down
curl -H "X-API-Key: $API_KEY" http://localhost:8000/api/some-endpoint

# Response: 503
{
  "detail": "Service 'openai_api' is currently unavailable",
  "error_code": "CIRCUIT_BREAKER_OPEN",
  "retry_after": 30
}
```

#### Validation Error
```bash
# Invalid appointment data
curl -X POST -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  http://localhost:8000/appointments -d '{"invalid": "data"}'

# Response: 422
{
  "detail": [
    {
      "loc": ["body", "starts_at"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

## Rate Limiting & Quotas

### Default Limits
- **API Requests**: 1000/hour per API key
- **Twilio Webhooks**: No limit (signature verified)
- **Cost Budget**: $50/month (configurable)
- **Circuit Breaker**: Service-specific failure thresholds

### Headers
Response includes rate limit headers:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1696087800
```

---

## Testing & Development

### Health Check Endpoints
```bash
# Basic health (no auth)
curl http://localhost:8000/healthz
# Response: {"ok": true}

# Database connectivity (no auth)
curl http://localhost:8000/readyz
# Response: {"db": "ok"}

# Full metrics (no auth)
curl http://localhost:8000/metrics
# Response: {...performance and error metrics...}
```

### Test Environment
Use `APP_ENV=development` or `APP_ENV=testing` to:
- Disable Twilio signature verification
- Enable debug logging
- Use in-memory storage fallbacks

### Mock Data
When external services aren't available:
- Cost tracking falls back to mock AWS data
- Redis failures fall back to in-memory storage
- Circuit breakers provide graceful degradation

---

**🎯 End of API Documentation**

For operational procedures, see the [Operations Runbook](./OPERATIONS.md).

*Last Updated: 2025-09-30*
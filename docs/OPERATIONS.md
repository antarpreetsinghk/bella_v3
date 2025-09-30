# Bella V3 Operations Runbook

> **Production-Ready Voice Appointment Booking System**
> Complete operational guide for monitoring, troubleshooting, and maintaining Bella V3

## Table of Contents

- [System Overview](#system-overview)
- [Quick Start](#quick-start)
- [Monitoring & Dashboards](#monitoring--dashboards)
- [Alerting](#alerting)
- [Circuit Breakers](#circuit-breakers)
- [Performance Management](#performance-management)
- [Cost Optimization](#cost-optimization)
- [Troubleshooting Guide](#troubleshooting-guide)
- [Emergency Procedures](#emergency-procedures)
- [Maintenance Tasks](#maintenance-tasks)

---

## System Overview

Bella V3 is an AI-powered voice appointment booking system with enterprise-grade monitoring, alerting, and cost optimization capabilities.

### Core Components
- **Voice Call Processing**: Twilio + OpenAI Whisper STT
- **AI Appointment Booking**: Natural language processing with appointment extraction
- **Circuit Breakers**: Automatic failover protection for external services
- **Business Metrics**: Real-time KPI tracking and performance monitoring
- **Cost Optimization**: Budget tracking and usage pattern analysis
- **Alerting System**: Multi-channel notifications with SLA monitoring

### Architecture
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Twilio        │───▶│   Bella V3       │───▶│   Database      │
│   Voice Calls   │    │   FastAPI App    │    │   (SQLite)      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │   OpenAI API     │
                       │   (Whisper STT)  │
                       └──────────────────┘
```

---

## Quick Start

### Prerequisites
- Python 3.10+
- Valid API keys: `BELLA_API_KEY`, `OPENAI_API_KEY`, `TWILIO_*`
- Optional: Redis for session storage, AWS credentials for cost tracking

### Starting the System
```bash
# Set environment variables
export BELLA_API_KEY="your-api-key"
export OPENAI_API_KEY="your-openai-key"
export DATABASE_URL="sqlite+aiosqlite:///./bella.db"

# Start the application
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Health Checks
```bash
# Basic health
curl http://localhost:8000/healthz

# Database connectivity
curl http://localhost:8000/readyz

# Full system status
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/unified/status
```

---

## Monitoring & Dashboards

### Unified Operations Dashboard
**URL**: `http://localhost:8000/`
**Auth**: API Key required (`X-API-Key` header or localStorage)

#### Dashboard Tabs
1. **📅 Operations**: Live appointments, user activity, system status
2. **💰 Analytics**: Cost tracking, budget utilization, optimization recommendations
3. **⚡ System**: Performance metrics, circuit breaker status, SLA monitoring

### Key Metrics to Monitor
- **System Health**: Overall uptime, response times, error rates
- **Call Success Rate**: Target >95%, alerts if <90%
- **Circuit Breaker Status**: All should be "closed" (healthy)
- **Budget Utilization**: Monitor for 80%/90%/100% thresholds
- **SLA Compliance**: 99.9% uptime, 99% calls under 2s response time

### API Endpoints
```bash
# System status
GET /api/unified/status

# Circuit breaker health
GET /api/unified/circuit-breakers

# Business metrics
GET /api/unified/business-metrics

# Active alerts
GET /api/unified/alerts

# SLA dashboard
GET /api/unified/sla-metrics

# Cost optimization
GET /api/unified/cost-optimization
```

---

## Alerting

### Alert Severity Levels
- **🔴 CRITICAL**: System failure, budget exceeded, SLA breach >1%
- **🟠 HIGH**: Service degradation, circuit breaker open, budget at 90%
- **🟡 MEDIUM**: Performance issues, budget at 80%, failed calls
- **🟢 LOW**: Service recovery, maintenance notifications

### Notification Channels
1. **Slack**: All alerts (configure `SLACK_WEBHOOK_URL`)
2. **Email**: High/Critical alerts (configure SMTP settings)
3. **SMS**: Critical alerts (Twilio integration)
4. **Phone**: Critical system failures

### Alert Management
```bash
# View active alerts
curl -H "X-API-Key: $API_KEY" http://localhost:8000/api/unified/alerts

# Create manual alert
curl -X POST -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  http://localhost:8000/api/unified/alerts -d '{
    "component": "manual",
    "severity": "medium",
    "message": "Manual maintenance alert",
    "details": {"operator": "ops-team"}
  }'

# Resolve alert
curl -X PATCH -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  http://localhost:8000/api/unified/alerts/ALERT_ID/resolve -d '{
    "note": "Issue resolved by ops team"
  }'
```

### Alert Configuration
Set these environment variables for notifications:
```bash
# Slack
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."

# Email (SMTP)
export SMTP_HOST="smtp.gmail.com"
export SMTP_PORT="587"
export SMTP_USER="alerts@yourcompany.com"
export SMTP_PASSWORD="your-app-password"
export ALERT_EMAIL="oncall@yourcompany.com"
```

---

## Circuit Breakers

### Purpose
Circuit breakers protect against cascading failures by automatically failing fast when external services are unhealthy.

### Configured Breakers
1. **openai_api**: Protects OpenAI Whisper STT calls
2. **twilio_api**: Protects Twilio API interactions
3. **database**: Protects database operations

### States
- **🟢 CLOSED**: Normal operation (healthy)
- **🟡 HALF_OPEN**: Testing recovery after failure
- **🔴 OPEN**: Blocking requests due to failures

### Thresholds
- **OpenAI**: 3 failures → open, 30s recovery timeout
- **Twilio**: 5 failures → open, 60s recovery timeout
- **Database**: 3 failures → open, 20s recovery timeout

### Monitoring
```bash
# Check all circuit breakers
curl -H "X-API-Key: $API_KEY" http://localhost:8000/api/unified/circuit-breakers

# Expected healthy output:
{
  "openai_api": {"state": "closed", "success_rate": 1.0},
  "twilio_api": {"state": "closed", "success_rate": 1.0},
  "database": {"state": "closed", "success_rate": 1.0}
}
```

### Troubleshooting Circuit Breakers
- **OPEN state**: Service is failing, check external service health
- **High failure rate**: Investigate API connectivity, credentials, timeouts
- **Frequent state changes**: Network issues or intermittent service problems

---

## Performance Management

### SLA Targets
- **Overall Uptime**: 99.9% (8.76 hours downtime/year)
- **Call Success Rate**: 95% minimum
- **API Response Time**: 99% of requests under 2 seconds
- **OpenAI API Availability**: 99.5% uptime

### Performance Monitoring
```bash
# Business metrics
curl -H "X-API-Key: $API_KEY" http://localhost:8000/api/unified/business-metrics

# Performance trends (last 24h)
curl -H "X-API-Key: $API_KEY" http://localhost:8000/api/unified/trends?hours=24

# Performance alerts
curl -H "X-API-Key: $API_KEY" http://localhost:8000/api/unified/alerts
```

### Performance Optimization
1. **Slow Calls (>5s)**: Check OpenAI API latency, network connectivity
2. **High Error Rate**: Review error logs, check external service status
3. **Memory Usage**: Monitor via `/metrics` endpoint, restart if needed
4. **Database Performance**: Check query performance, consider indexes

---

## Cost Optimization

### Budget Management
- **Monthly Target**: $50 (configurable in `cost_optimization.py`)
- **Whisper API**: $0.006/minute (primary cost driver)
- **Infrastructure**: AWS/hosting costs
- **Alert Thresholds**: 80%, 90%, 100% of budget

### Cost Monitoring
```bash
# Cost dashboard
curl -H "X-API-Key: $API_KEY" http://localhost:8000/api/unified/cost-optimization

# Expected output structure:
{
  "cost_summary": {
    "recent_trends": {
      "projected_monthly": 45.20,
      "budget_utilization": 0.904,
      "budget_remaining": 4.80
    }
  },
  "recommendations": [...],
  "optimization_score": 85
}
```

### Cost Alerts
- **80% Budget**: Medium alert, review usage patterns
- **90% Budget**: High alert, consider optimizations
- **100% Budget**: Critical alert, immediate action required

### Optimization Strategies
1. **Cache Whisper Results**: Reduce redundant transcription calls
2. **Right-size Infrastructure**: Scale based on usage patterns
3. **Peak Hour Analysis**: Optimize for high-traffic periods
4. **Service Limits**: Set usage caps to prevent runaway costs

---

## Troubleshooting Guide

### Common Issues

#### 🔴 High Call Failure Rate
**Symptoms**: Success rate <90%, multiple failed call alerts
**Investigation**:
```bash
# Check circuit breaker status
curl -H "X-API-Key: $API_KEY" http://localhost:8000/api/unified/circuit-breakers

# Review recent failed calls
curl -H "X-API-Key: $API_KEY" http://localhost:8000/api/unified/business-metrics
```
**Solutions**:
- If OpenAI circuit open: Check API key, quota, service status
- If database issues: Check connection, disk space, performance
- Network issues: Verify connectivity to external services

#### 🟡 Slow Response Times
**Symptoms**: Average response time >2s, timeout alerts
**Investigation**:
```bash
# Check performance metrics
curl -H "X-API-Key: $API_KEY" http://localhost:8000/api/unified/trends

# Review slow calls in logs
grep "SLOW" /var/log/bella/app.log
```
**Solutions**:
- Optimize OpenAI API calls (reduce audio size, use caching)
- Check network latency to external services
- Scale infrastructure if CPU/memory constrained

#### 💰 Budget Exceeded
**Symptoms**: Cost alerts, projected monthly >$50
**Investigation**:
```bash
# Review cost breakdown
curl -H "X-API-Key: $API_KEY" http://localhost:8000/api/unified/cost-optimization

# Check usage patterns
curl -H "X-API-Key: $API_KEY" http://localhost:8000/api/unified/trends?hours=168
```
**Solutions**:
- Implement Whisper result caching
- Set usage limits/quotas
- Optimize call handling efficiency
- Review and adjust monthly budget if needed

#### 🔧 Service Won't Start
**Symptoms**: Application fails to start, health checks fail
**Investigation**:
```bash
# Check logs for startup errors
python -m uvicorn app.main:app --log-level debug

# Verify environment variables
env | grep -E "(BELLA|OPENAI|TWILIO|DATABASE)"

# Test database connectivity
python -c "from app.db.session import get_engine; print('DB OK')"
```
**Solutions**:
- Fix missing environment variables
- Resolve database connection issues
- Check file permissions and dependencies

### Error Code Reference
- **401**: Invalid API key (`X-API-Key` header)
- **403**: Twilio signature validation failed
- **404**: Resource not found (appointments, users)
- **500**: Internal server error (check logs)
- **503**: Service unavailable (circuit breaker open)

---

## Emergency Procedures

### 🚨 System Down
1. **Check basic connectivity**: `curl http://localhost:8000/healthz`
2. **Review application logs**: Look for startup errors, exceptions
3. **Verify external services**: OpenAI API, Twilio, database
4. **Restart application**: With full logging enabled
5. **Check circuit breakers**: May need manual reset if stuck

### 🚨 High Error Rate
1. **Identify error pattern**: Check error aggregation in `/metrics`
2. **Review circuit breaker status**: May indicate specific service issues
3. **Check external service health**: OpenAI, Twilio status pages
4. **Scale resources**: If CPU/memory constrained
5. **Implement degraded mode**: Use fallbacks if possible

### 🚨 Budget Alert (Critical)
1. **Immediate**: Review current spend and usage patterns
2. **Short-term**: Implement emergency usage limits
3. **Medium-term**: Enable aggressive caching, optimize flows
4. **Communication**: Alert stakeholders about cost implications

### 📞 Escalation Contacts
- **Primary On-Call**: [Your team's contact info]
- **Engineering Lead**: [Lead engineer contact]
- **Operations Manager**: [Manager contact]
- **Emergency Hotline**: [24/7 support number]

---

## Maintenance Tasks

### Daily
- [ ] Review dashboard for alerts and anomalies
- [ ] Check SLA compliance (>99% uptime, <2s response)
- [ ] Monitor budget utilization and cost trends
- [ ] Verify all circuit breakers are healthy

### Weekly
- [ ] Review performance trends and optimization opportunities
- [ ] Clean up old metrics data (automated via cleanup job)
- [ ] Update cost projections and budget planning
- [ ] Review and resolve non-critical alerts

### Monthly
- [ ] Analyze monthly cost report and optimization recommendations
- [ ] Review SLA performance and adjust targets if needed
- [ ] Update alerting thresholds based on usage patterns
- [ ] Plan capacity and scaling for next month
- [ ] Security review: rotate API keys, review access logs

### Quarterly
- [ ] Comprehensive performance review and optimization
- [ ] Update monitoring thresholds and SLA targets
- [ ] Review and update emergency procedures
- [ ] Infrastructure and dependency updates
- [ ] Business review: usage patterns, cost optimization, feature planning

---

## Configuration Reference

### Environment Variables
```bash
# Core Application
BELLA_API_KEY="your-secure-api-key"
APP_ENV="production"  # or "development"
DATABASE_URL="sqlite+aiosqlite:///./bella.db"

# External Services
OPENAI_API_KEY="sk-..."
TWILIO_ACCOUNT_SID="AC..."
TWILIO_AUTH_TOKEN="auth-token"

# Optional: Redis
REDIS_URL="redis://localhost:6379"

# Optional: Alerting
SLACK_WEBHOOK_URL="https://hooks.slack.com/..."
SMTP_HOST="smtp.gmail.com"
SMTP_PORT="587"
SMTP_USER="alerts@company.com"
SMTP_PASSWORD="app-password"
ALERT_EMAIL="oncall@company.com"

# Optional: AWS Cost Tracking
AWS_ACCESS_KEY_ID="AKIA..."
AWS_SECRET_ACCESS_KEY="secret"
AWS_DEFAULT_REGION="us-east-1"
```

### Port Configuration
- **8000**: Primary application port
- **8001**: Development/staging
- **8002**: Testing/backup

### File Locations
- **Application**: `/home/user/Projects/bella_v3/`
- **Database**: `./bella.db` (relative to app directory)
- **Logs**: Console output (configure log shipping as needed)
- **Config**: Environment variables (no config files)

---

**🎯 End of Operations Runbook**

For additional support, check the [API Documentation](./API.md) and [Troubleshooting FAQ](./FAQ.md).

*Last Updated: 2025-09-30*
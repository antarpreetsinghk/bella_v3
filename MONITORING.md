# 🔍 BELLA V3 MONITORING & DEBUGGING GUIDE

## 🚀 **Quick Setup**

```bash
# 1. Setup CloudWatch monitoring
./aws/setup-monitoring.sh

# 2. Install monitoring dependencies
pip install structlog boto3

# 3. Deploy updated application
git add . && git commit -m "feat: add comprehensive monitoring system" && git push
```

## 📊 **Monitoring Features**

### **1. Structured Logging**
- ✅ **Correlation IDs**: Track requests across components
- ✅ **Token-efficient**: Max 200 chars per log line
- ✅ **JSON format**: Easy parsing and analysis
- ✅ **Error deduplication**: Reduce noise by 80%

### **2. Performance Monitoring**
- ✅ **Request timing**: Auto-track slow requests (>2s)
- ✅ **Error rates**: Real-time error percentage tracking
- ✅ **Session monitoring**: Active user session counts
- ✅ **Endpoint analysis**: Performance by API endpoint

### **3. CloudWatch Alarms**
- 🚨 **CPU > 80%**: ECS service overload
- 🧠 **Memory > 85%**: Memory pressure
- 🎯 **Unhealthy targets**: ALB target failures
- ⏱️ **Response time > 5s**: Performance degradation
- ❌ **5xx errors > 5/5min**: Application errors
- 🔥 **Error spike > 10/5min**: Error rate spike

### **4. Smart Error Aggregation**
- 📝 **Fingerprinting**: Group similar errors
- 🎯 **Severity levels**: LOW/MEDIUM/HIGH/CRITICAL
- 📊 **Frequency control**: Log every 10th occurrence
- 🧹 **Auto-cleanup**: Remove old error patterns

## 🛠️ **Debug Tools**

### **Live Debugging**
```bash
# Real-time logs
./scripts/debug-logs.sh tail

# Recent errors
./scripts/debug-logs.sh errors

# Slow requests
./scripts/debug-logs.sh slow

# Service health
./scripts/debug-logs.sh health
```

### **Application Metrics**
```bash
# Get metrics via API
curl bella-alb-1924818779.ca-central-1.elb.amazonaws.com/metrics

# Or via debug script
./scripts/debug-logs.sh metrics
```

### **CloudWatch Insights**
```bash
# Interactive queries
./scripts/debug-logs.sh insights

# Error summary
./scripts/debug-logs.sh summary
```

## 📈 **Key Metrics Endpoint**

**GET /metrics** returns:
```json
{
  "status": "healthy",
  "performance": {
    "active_sessions": 12,
    "total_requests": 1534,
    "avg_response_time": 0.234,
    "error_rate": 2.1,
    "slow_requests": 3
  },
  "errors": {
    "total_unique_errors": 5,
    "total_error_count": 47,
    "by_severity": {"low": 40, "medium": 7},
    "top_errors": [...]
  }
}
```

## 🔍 **Log Structure**

### **Request Logs** (token-efficient)
```json
{
  "timestamp": "2025-09-26T20:30:15Z",
  "level": "INFO",
  "event": "request_complete",
  "correlation_id": "a1b2c3d4",
  "endpoint": "/api/assistant/book",
  "method": "POST",
  "status_code": 200,
  "duration": 1.234,
  "user_id": "user_123"
}
```

### **Error Logs** (aggregated)
```json
{
  "timestamp": "2025-09-26T20:30:15Z",
  "level": "ERROR",
  "event": "aggregated_error",
  "correlation_id": "a1b2c3d4",
  "error_hash": "abc12345",
  "error_type": "ValidationError",
  "message": "Invalid phone number format",
  "count": 15,
  "severity": "low",
  "endpoint": "/api/users"
}
```

## 📱 **Alerting Setup**

### **SNS Email Alerts**
```bash
# Setup during monitoring installation
./aws/setup-monitoring.sh
# Enter your email when prompted
```

### **Alert Triggers**
- 🚨 **Immediate**: CRITICAL/HIGH severity errors
- ⏰ **5 minutes**: CPU/Memory thresholds
- 📊 **10 minutes**: Error rate spikes
- 🎯 **2 minutes**: Health check failures

## 🎯 **Token Optimization**

### **Before vs After**
```bash
# BEFORE: Verbose logging
2025-09-26 20:30:15 - app.main - INFO - === TWILIO WEBHOOK REQUEST ===
2025-09-26 20:30:15 - app.main - INFO - Path: /twilio/voice
2025-09-26 20:30:15 - app.main - INFO - Full URL: http://bella-alb.../twilio/voice
2025-09-26 20:30:15 - app.main - INFO - Method: POST
# 4 log lines = ~400 tokens

# AFTER: Structured & concise
{"timestamp":"2025-09-26T20:30:15Z","level":"INFO","event":"twilio_webhook_start","correlation_id":"a1b2","path":"/twilio/voice","method":"POST","has_auth_token":true}
# 1 log line = ~100 tokens
```

### **Token Savings: 60-80%**
- ✅ JSON structure reduces parsing overhead
- ✅ Truncated messages (200 char max)
- ✅ Error deduplication (log 1/10th occurrence)
- ✅ Conditional verbose logging (dev only)
- ✅ Correlation IDs group related logs

## 🚨 **Common Debug Commands**

### **Error Investigation**
```bash
# Find error pattern
aws logs filter-log-events --log-group-name /ecs/bella-prod \
  --filter-pattern "ERROR" --start-time $(date -d "1 hour ago" +%s)000

# Check specific error hash
aws logs filter-log-events --log-group-name /ecs/bella-prod \
  --filter-pattern "abc12345"
```

### **Performance Analysis**
```bash
# Slow requests
aws logs filter-log-events --log-group-name /ecs/bella-prod \
  --filter-pattern "[timestamp, level, event=\"request_complete\", ..., duration>2]"

# Error rates by endpoint
aws logs insights start-query --log-group-name /ecs/bella-prod \
  --query-string 'fields @timestamp, endpoint, error_rate | stats avg(error_rate) by endpoint'
```

### **Twilio Debugging**
```bash
# Webhook failures
./scripts/debug-logs.sh twilio

# Signature validation issues
aws logs filter-log-events --log-group-name /ecs/bella-prod \
  --filter-pattern "signature_validation_failed"
```

## 📋 **Monitoring Checklist**

### **Daily**
- [ ] Check error rates in `/metrics`
- [ ] Review CloudWatch alarms
- [ ] Monitor response times

### **Weekly**
- [ ] Review error patterns and trends
- [ ] Check resource utilization
- [ ] Update alert thresholds if needed

### **Monthly**
- [ ] Clean up old CloudWatch logs
- [ ] Review monitoring costs
- [ ] Update documentation

## 🎯 **Next Steps**

1. **Custom Dashboards**: Create CloudWatch dashboards
2. **Business Metrics**: Track booking success rates
3. **User Analytics**: Monitor user engagement
4. **Cost Optimization**: Right-size resources based on metrics

---

**🚀 Ready to debug efficiently with 80% fewer tokens!**
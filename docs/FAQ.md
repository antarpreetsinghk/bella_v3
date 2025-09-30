# Bella V3 Troubleshooting FAQ

> **Common Issues and Solutions for Bella V3 Operations**
> Quick fixes for monitoring, alerting, and performance problems

## Table of Contents

- [Quick Diagnostics](#quick-diagnostics)
- [System Issues](#system-issues)
- [Voice Call Problems](#voice-call-problems)
- [Circuit Breaker Issues](#circuit-breaker-issues)
- [Alerting Problems](#alerting-problems)
- [Performance Issues](#performance-issues)
- [Cost Management](#cost-management)
- [External Service Issues](#external-service-issues)
- [Configuration Problems](#configuration-problems)

---

## Quick Diagnostics

### 🔍 First Steps for Any Issue
```bash
# 1. Check overall system health
curl -H "X-API-Key: $API_KEY" http://localhost:8000/api/unified/status

# 2. Look for active alerts
curl -H "X-API-Key: $API_KEY" http://localhost:8000/api/unified/alerts

# 3. Check circuit breaker status
curl -H "X-API-Key: $API_KEY" http://localhost:8000/api/unified/circuit-breakers

# 4. Review performance metrics
curl -H "X-API-Key: $API_KEY" http://localhost:8000/api/unified/business-metrics
```

### 📊 Dashboard Not Loading
**Symptoms**: Dashboard shows loading spinner or errors

**Quick Check**:
```bash
# Test API connectivity
curl -H "X-API-Key: your-key" http://localhost:8000/api/unified/status
```

**Common Causes**:
- ❌ Invalid API key in browser localStorage
- ❌ Server not running on expected port
- ❌ Network connectivity issues

**Solutions**:
1. Clear browser localStorage: `localStorage.removeItem('bella_api_key')`
2. Verify server is running: `curl http://localhost:8000/healthz`
3. Check API key: Ensure `X-API-Key` header is correct
4. Try different port: Check if running on 8001 or 8002

---

## System Issues

### 🚨 Server Won't Start

#### Error: "Address already in use"
```bash
# Find process using port 8000
lsof -i :8000

# Kill process if needed
kill -9 <PID>

# Or use different port
uvicorn app.main:app --port 8001
```

#### Error: "Database connection failed"
```bash
# Check database file permissions
ls -la bella.db

# Test database connectivity
python -c "from app.db.session import get_engine; print('DB OK')"

# Reset database if corrupted
rm bella.db
python -c "from app.db.base import init_db; init_db()"
```

#### Error: "Missing environment variables"
```bash
# Check required variables
env | grep -E "(BELLA|OPENAI|TWILIO|DATABASE)"

# Set missing variables
export BELLA_API_KEY="your-api-key"
export OPENAI_API_KEY="sk-your-key"
export DATABASE_URL="sqlite+aiosqlite:///./bella.db"
```

### 🔄 High Memory Usage
**Symptoms**: System becomes slow, out of memory errors

**Investigation**:
```bash
# Check memory usage
ps aux | grep python
free -h

# Check for memory leaks in business metrics
curl -H "X-API-Key: $API_KEY" http://localhost:8000/metrics
```

**Solutions**:
1. Restart application: `systemctl restart bella` (or manual restart)
2. Increase cleanup frequency in `business_metrics.py`
3. Reduce metrics retention period
4. Add memory limits: `uvicorn app.main:app --limit-max-requests 1000`

---

## Voice Call Problems

### 📞 Calls Failing Immediately

#### Twilio Signature Validation Errors
**Error**: "403 Forbidden" or "Signature validation failed"

**Check**:
```bash
# Verify Twilio credentials
echo $TWILIO_AUTH_TOKEN
echo $TWILIO_ACCOUNT_SID

# Test with signature validation disabled (DEV ONLY)
export APP_ENV="development"
```

**Solutions**:
1. Verify `TWILIO_AUTH_TOKEN` is correct
2. Check webhook URL in Twilio console
3. Ensure HTTPS for production (HTTP OK for dev)
4. Review logs for detailed signature validation attempts

#### OpenAI Whisper Failures
**Error**: Circuit breaker shows OpenAI as "open"

**Check**:
```bash
# Test OpenAI API directly
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
     https://api.openai.com/v1/models

# Check circuit breaker status
curl -H "X-API-Key: $API_KEY" \
     http://localhost:8000/api/unified/circuit-breakers
```

**Solutions**:
1. Verify `OPENAI_API_KEY` is valid and has credits
2. Check OpenAI service status: https://status.openai.com/
3. Reset circuit breaker manually if needed
4. Implement audio caching to reduce API calls

### 🎤 Speech Recognition Issues

#### Low Confidence Scores
**Symptoms**: Extracted appointments are incorrect or empty

**Investigation**:
```bash
# Check recent call metrics
curl -H "X-API-Key: $API_KEY" \
     http://localhost:8000/api/unified/business-metrics | \
     jq '.speech_recognition_accuracy'
```

**Solutions**:
1. Check audio quality settings in Twilio
2. Implement confidence threshold filtering
3. Add fallback prompts for unclear speech
4. Consider alternative STT providers for backup

#### Appointment Extraction Failures
**Symptoms**: Speech recognized but appointment not extracted

**Check**:
```bash
# Test extraction with sample text
curl -X POST -H "X-API-Key: $API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"text": "I need an appointment tomorrow at 2pm"}' \
     http://localhost:8000/api/assistant/extract-appointment
```

**Solutions**:
1. Review and improve extraction prompts
2. Add more training examples for edge cases
3. Implement fuzzy date/time parsing
4. Add manual fallback flow for complex requests

---

## Circuit Breaker Issues

### ⚡ Circuit Breaker Stuck Open

#### OpenAI Circuit Won't Close
**Symptoms**: Circuit shows "open" state for extended period

**Investigation**:
```bash
# Check circuit details
curl -H "X-API-Key: $API_KEY" \
     http://localhost:8000/api/unified/circuit-breakers | \
     jq '.openai_api'

# Look for:
# - High failure_count
# - Recent last_failure_time
# - Time since last success
```

**Solutions**:
1. **Verify OpenAI service**: Check https://status.openai.com/
2. **Check API credits**: Ensure billing is current
3. **Manual reset**: Restart application to reset circuit
4. **Adjust thresholds**: Reduce failure_threshold if too sensitive

#### Frequent Circuit State Changes
**Symptoms**: Circuit rapidly switches between open/closed

**Investigation**:
- Check network stability to OpenAI
- Review timeout settings (currently 15s for OpenAI)
- Monitor concurrent request patterns

**Solutions**:
1. Increase timeout from 15s to 30s
2. Implement exponential backoff
3. Add jitter to prevent thundering herd
4. Consider caching successful results

### 🔧 Circuit Breaker Configuration

#### Adjusting Thresholds
```python
# In app/services/circuit_breaker.py
openai_config = CircuitBreakerConfig(
    failure_threshold=5,      # Increase from 3 if too sensitive
    recovery_timeout=60,      # Increase for slower recovery
    timeout=30.0,            # Increase for slow responses
    half_open_max_calls=3    # Test calls in recovery
)
```

#### Custom Fallback Functions
```python
# Add better fallback responses
async def smart_openai_fallback(*args, **kwargs) -> str:
    # Return contextual fallback based on call state
    return "I'm having trouble with voice processing. Let me transfer you to a representative."
```

---

## Alerting Problems

### 🚨 No Alerts Being Generated

#### Alert System Not Starting
**Check**:
```bash
# Verify alerting system started
grep "Alert notification worker started" /var/log/bella/app.log

# Test manual alert creation
curl -X POST -H "X-API-Key: $API_KEY" \
     -H "Content-Type: application/json" \
     -d '{
       "component": "test",
       "severity": "medium",
       "message": "Test alert"
     }' \
     http://localhost:8000/api/unified/alerts
```

**Solutions**:
1. Check startup logs for alerting initialization errors
2. Verify alert manager is imported correctly
3. Restart application to reinitialize alert worker
4. Check for circular import issues

#### Notifications Not Being Sent
**Check Slack Integration**:
```bash
# Test Slack webhook directly
curl -X POST -H "Content-Type: application/json" \
     -d '{"text": "Test message from Bella"}' \
     $SLACK_WEBHOOK_URL
```

**Check Email Setup**:
```bash
# Verify SMTP settings
echo $SMTP_HOST
echo $SMTP_USER
echo $ALERT_EMAIL

# Test email connectivity (if possible)
telnet $SMTP_HOST $SMTP_PORT
```

**Solutions**:
1. Verify `SLACK_WEBHOOK_URL` is correct
2. Check firewall/network access to SMTP server
3. Validate email credentials and permissions
4. Test with simple notification first

### 📢 Too Many Alerts

#### Alert Spam/Flooding
**Symptoms**: Hundreds of similar alerts generated

**Investigation**:
```bash
# Check alert summary
curl -H "X-API-Key: $API_KEY" \
     http://localhost:8000/api/unified/alerts | \
     jq '.alert_summary'

# Look for high alert counts or short notification queue
```

**Solutions**:
1. **Increase suppression windows** in `alerting.py`
2. **Adjust alert thresholds** - less sensitive triggers
3. **Implement alert grouping** for similar issues
4. **Review circuit breaker thresholds** - may be too sensitive

#### Alert Fatigue
**Prevention**:
1. Set different notification channels by severity
2. Implement escalation delays (5min → 15min → 1hr)
3. Auto-resolve alerts after successful recovery
4. Use summary alerts for multiple similar issues

---

## Performance Issues

### 🐌 Slow Response Times

#### API Endpoints Taking >2 seconds
**Investigation**:
```bash
# Check current performance
curl -H "X-API-Key: $API_KEY" \
     http://localhost:8000/api/unified/business-metrics | \
     jq '.avg_response_time'

# Check for slow endpoints
curl -H "X-API-Key: $API_KEY" \
     http://localhost:8000/api/unified/trends?hours=1
```

**Common Causes**:
- 🐌 OpenAI Whisper API latency
- 🗄️ Database query performance
- 🌐 Network connectivity issues
- 💾 Memory constraints

**Solutions**:
1. **Cache OpenAI results**: Implement audio fingerprinting
2. **Optimize database queries**: Add indexes, limit result sets
3. **Increase timeouts**: For external API calls
4. **Scale resources**: More CPU/memory if constrained

#### Voice Call Processing Slow
**Symptoms**: Users experience long delays during calls

**Check**:
```bash
# Review call processing times
curl -H "X-API-Key: $API_KEY" \
     http://localhost:8000/api/unified/business-metrics | \
     jq '.avg_response_time'

# Check OpenAI circuit status
curl -H "X-API-Key: $API_KEY" \
     http://localhost:8000/api/unified/circuit-breakers | \
     jq '.openai_api.success_rate'
```

**Solutions**:
1. **Preprocessing**: Reduce audio file size before OpenAI
2. **Parallel processing**: Process while user is speaking
3. **Fallback flows**: Faster alternatives for simple requests
4. **User feedback**: "Processing your request..." announcements

### 📈 High Error Rates

#### Success Rate Below 95%
**Investigation**:
```bash
# Check current success rate
curl -H "X-API-Key: $API_KEY" \
     http://localhost:8000/api/unified/business-metrics | \
     jq '.success_rate'

# Check SLA status
curl -H "X-API-Key: $API_KEY" \
     http://localhost:8000/api/unified/sla-metrics | \
     jq '.services.call_success_rate'
```

**Common Error Types**:
1. **OpenAI API failures**: Rate limits, timeouts, service issues
2. **Database errors**: Connection issues, lock timeouts
3. **Validation errors**: Invalid appointment times, user data
4. **Network issues**: External service connectivity

**Solutions**:
1. **Implement retries**: Exponential backoff for transient errors
2. **Better validation**: Catch and handle edge cases
3. **Graceful degradation**: Fallback flows for system issues
4. **Error categorization**: Different handling for different error types

---

## Cost Management

### 💰 Budget Alerts Triggering

#### Projected Costs Exceeding Budget
**Investigation**:
```bash
# Check current cost status
curl -H "X-API-Key: $API_KEY" \
     http://localhost:8000/api/unified/cost-optimization | \
     jq '.cost_summary.recent_trends'

# Review cost breakdown
curl -H "X-API-Key: $API_KEY" \
     http://localhost:8000/api/unified/cost-optimization | \
     jq '.cost_summary.recent_trends.whisper_api_cost'
```

**Cost Optimization Steps**:
1. **Implement caching**: Cache Whisper transcriptions
2. **Audio optimization**: Compress audio before processing
3. **Usage limits**: Set daily/hourly call limits
4. **Peak hour analysis**: Identify and optimize high-usage periods

#### Whisper API Costs Too High
**Symptoms**: >70% of budget spent on Whisper API

**Quick Fixes**:
1. **Audio preprocessing**: Remove silence, compress
2. **Result caching**: Cache by audio fingerprint
3. **Batch processing**: Group multiple short clips
4. **Alternative STT**: Use Google/Azure for cost comparison

**Long-term Solutions**:
1. **Self-hosted STT**: Consider Whisper local deployment
2. **Hybrid approach**: Local + cloud based on audio quality
3. **Usage-based scaling**: Dynamic quality adjustment

### 📊 Cost Tracking Not Working

#### AWS Cost Explorer Issues
**Error**: "AWS Cost Explorer not available"

**Check**:
```bash
# Test AWS credentials
aws sts get-caller-identity

# Test Cost Explorer access
aws ce get-cost-and-usage \
    --time-period Start=2025-09-29,End=2025-09-30 \
    --granularity DAILY \
    --metrics BlendedCost
```

**Solutions**:
1. **Enable Cost Explorer**: In AWS billing console
2. **IAM permissions**: Add `ce:GetCostAndUsage` permission
3. **Billing access**: Enable programmatic billing access
4. **Fallback mode**: Use manual cost tracking if AWS unavailable

---

## External Service Issues

### 🌐 OpenAI API Problems

#### Rate Limiting
**Error**: "Rate limit exceeded" or 429 HTTP status

**Solutions**:
1. **Implement backoff**: Exponential retry with jitter
2. **Queue requests**: Process calls sequentially during high traffic
3. **Upgrade plan**: Increase OpenAI rate limits
4. **Cache aggressively**: Reduce duplicate API calls

#### API Key Issues
**Error**: "Invalid API key" or 401 HTTP status

**Check**:
```bash
# Test API key
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
     https://api.openai.com/v1/models
```

**Solutions**:
1. **Regenerate key**: Create new API key in OpenAI dashboard
2. **Check billing**: Ensure account has available credits
3. **Rotate secrets**: Update key in environment variables

### ☎️ Twilio Integration Issues

#### Webhook Signature Failures
**Error**: "Signature validation failed"

**Debug Steps**:
```bash
# Check webhook URL configuration
curl -X GET "https://api.twilio.com/2010-04-01/Accounts/$TWILIO_ACCOUNT_SID/IncomingPhoneNumbers.json" \
     -u $TWILIO_ACCOUNT_SID:$TWILIO_AUTH_TOKEN
```

**Solutions**:
1. **Verify webhook URL**: Must match exactly in Twilio console
2. **HTTPS requirement**: Use HTTPS in production
3. **Token rotation**: Regenerate auth token if needed
4. **URL encoding**: Ensure proper encoding for special characters

#### Call Quality Issues
**Symptoms**: Poor audio quality, dropped calls

**Investigation**:
1. **Check Twilio console**: Review call logs and quality scores
2. **Network analysis**: Test from different networks
3. **Audio settings**: Review codec and quality settings

**Solutions**:
1. **Upgrade codec**: Use G.722 for better quality
2. **Network optimization**: Use CDN or edge locations
3. **Fallback numbers**: Multiple phone numbers for redundancy

---

## Configuration Problems

### ⚙️ Environment Variables

#### Missing Required Variables
**Symptoms**: Application fails to start or features don't work

**Check All Required Variables**:
```bash
# Core application
echo $BELLA_API_KEY
echo $DATABASE_URL
echo $APP_ENV

# External services
echo $OPENAI_API_KEY
echo $TWILIO_ACCOUNT_SID
echo $TWILIO_AUTH_TOKEN

# Optional features
echo $SLACK_WEBHOOK_URL
echo $SMTP_HOST
echo $REDIS_URL
```

**Template .env File**:
```bash
# Copy to .env and fill in values
BELLA_API_KEY="your-secure-api-key"
APP_ENV="production"
DATABASE_URL="sqlite+aiosqlite:///./bella.db"

OPENAI_API_KEY="sk-your-openai-key"
TWILIO_ACCOUNT_SID="ACyour-account-sid"
TWILIO_AUTH_TOKEN="your-auth-token"

# Optional
SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
REDIS_URL="redis://localhost:6379"
SMTP_HOST="smtp.gmail.com"
SMTP_PORT="587"
SMTP_USER="alerts@company.com"
SMTP_PASSWORD="app-password"
ALERT_EMAIL="oncall@company.com"
```

### 🔐 Security Configuration

#### API Key Security
**Best Practices**:
1. **Strong keys**: Use 32+ character random strings
2. **Rotation**: Change keys monthly
3. **Scope limitation**: Different keys for different environments
4. **Logging**: Don't log API keys in error messages

#### Production Security
**Checklist**:
- [ ] HTTPS enabled for all external endpoints
- [ ] Twilio signature validation enabled
- [ ] API rate limiting configured
- [ ] Database access restricted
- [ ] Secrets stored securely (not in code)
- [ ] Error messages don't expose sensitive data

---

## Emergency Contacts & Escalation

### 🆘 When to Escalate

#### Immediate Escalation (Critical Issues)
- System completely down (no voice calls working)
- Budget exceeded by >50%
- Security breach suspected
- Data loss or corruption

#### Standard Escalation (High Priority)
- Success rate <90% for >30 minutes
- Circuit breakers stuck open for >1 hour
- Critical alerts not being resolved
- Performance degradation affecting users

### 📞 Contact Information
```
Primary On-Call: [Your team contact]
Engineering Lead: [Lead engineer]
Operations Manager: [Manager contact]
Emergency Hotline: [24/7 support]

Vendor Support:
- OpenAI: https://help.openai.com/
- Twilio: https://support.twilio.com/
- AWS: https://aws.amazon.com/support/
```

### 🚨 Emergency Commands

#### Quick System Reset
```bash
# Stop application
pkill -f "uvicorn app.main:app"

# Clear any stuck processes
pkill -f "bella"

# Restart with full logging
export LOG_LEVEL="DEBUG"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level debug
```

#### Emergency Fallback Mode
```bash
# Disable external services temporarily
export OPENAI_API_KEY=""
export TWILIO_AUTH_TOKEN=""

# This will trigger fallback modes and allow basic functionality
```

#### Database Recovery
```bash
# Backup current database
cp bella.db bella.db.backup.$(date +%Y%m%d_%H%M%S)

# If corruption suspected, create fresh database
# (WARNING: This loses all data)
rm bella.db
python -c "from app.db.base import init_db; init_db()"
```

---

**🎯 End of Troubleshooting FAQ**

For detailed operational procedures, see [Operations Runbook](./OPERATIONS.md).
For API reference, see [API Documentation](./API.md).

*Last Updated: 2025-09-30*
*Emergency Hotline: [Your 24/7 contact]*
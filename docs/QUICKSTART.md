# Bella V3 Quick Start Guide

> **Get up and running with Bella V3 in 15 minutes**
> Essential setup for voice appointment booking with enterprise monitoring

## 🚀 15-Minute Setup

### Step 1: Prerequisites (2 minutes)
```bash
# Check Python version (3.10+ required)
python --version

# Check required tools
curl --version
git --version
```

### Step 2: Get API Keys (5 minutes)
1. **OpenAI API Key**:
   - Visit https://platform.openai.com/api-keys
   - Create new key starting with `sk-`
   - Ensure billing is set up

2. **Twilio Account**:
   - Sign up at https://www.twilio.com/
   - Get Account SID (starts with `AC`)
   - Get Auth Token from console
   - Purchase a phone number

3. **Bella API Key**:
   - Generate secure random string: `openssl rand -hex 32`

### Step 3: Installation (3 minutes)
```bash
# Clone and setup
git clone <repository-url>
cd bella_v3
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Step 4: Configuration (3 minutes)
```bash
# Create .env file
cat > .env << 'EOF'
BELLA_API_KEY="your-64-character-secure-api-key"
OPENAI_API_KEY="sk-your-openai-api-key"
TWILIO_ACCOUNT_SID="ACyour-twilio-account-sid"
TWILIO_AUTH_TOKEN="your-twilio-auth-token"
DATABASE_URL="sqlite+aiosqlite:///./bella.db"
APP_ENV="development"
EOF

# Load environment variables
source .env  # Windows: set in environment manually
```

### Step 5: First Run (2 minutes)
```bash
# Initialize database
python -c "from app.db.base import init_db; init_db()"

# Start application
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Verify in another terminal
curl http://localhost:8000/healthz
# Should return: {"ok": true}
```

## ✅ Verification Checklist

### Basic System Health
```bash
# 1. Health check
curl http://localhost:8000/healthz
# Expected: {"ok": true}

# 2. Database connectivity
curl http://localhost:8000/readyz
# Expected: {"db": "ok"}

# 3. API authentication
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/unified/status
# Expected: {"system": "healthy", ...}
```

### Dashboard Access
1. Open browser to `http://localhost:8000/`
2. Enter your API key when prompted
3. Verify all 3 tabs load:
   - 📅 **Operations**: Shows users/appointments
   - 💰 **Analytics**: Shows cost tracking
   - ⚡ **System**: Shows performance metrics

### Voice Call Testing
1. **Configure Twilio Webhook**:
   - Go to Twilio Console → Phone Numbers
   - Select your number
   - Set webhook URL: `https://your-domain.com/twilio/voice`
   - For local testing: Use ngrok or similar tunnel

2. **Test Call Flow**:
   - Call your Twilio number
   - Say: "I need an appointment tomorrow at 2pm"
   - Verify appointment gets created

## 🎛️ Essential Operations

### Monitoring Your System
```bash
# Check overall health
curl -H "X-API-Key: $BELLA_API_KEY" \
     http://localhost:8000/api/unified/status

# Monitor business metrics
curl -H "X-API-Key: $BELLA_API_KEY" \
     http://localhost:8000/api/unified/business-metrics

# Check circuit breakers
curl -H "X-API-Key: $BELLA_API_KEY" \
     http://localhost:8000/api/unified/circuit-breakers

# View active alerts
curl -H "X-API-Key: $BELLA_API_KEY" \
     http://localhost:8000/api/unified/alerts
```

### Daily Health Check Script
```bash
#!/bin/bash
# save as: daily_check.sh

API_KEY="your-bella-api-key"
BASE_URL="http://localhost:8000"

echo "=== Bella V3 Daily Health Check ==="
echo "Date: $(date)"
echo

# System health
echo "1. System Status:"
curl -s -H "X-API-Key: $API_KEY" "$BASE_URL/api/unified/status" | \
    jq -r '"System: " + .system + " | Performance: " + .performance'

# Circuit breakers
echo -e "\n2. Circuit Breakers:"
curl -s -H "X-API-Key: $API_KEY" "$BASE_URL/api/unified/circuit-breakers" | \
    jq -r 'to_entries[] | .key + ": " + .value.state'

# SLA status
echo -e "\n3. SLA Status:"
curl -s -H "X-API-Key: $API_KEY" "$BASE_URL/api/unified/sla-metrics" | \
    jq -r '"Overall Health: " + (.overall_health_score | tostring) + "%"'

# Active alerts
echo -e "\n4. Active Alerts:"
curl -s -H "X-API-Key: $API_KEY" "$BASE_URL/api/unified/alerts" | \
    jq -r '"Total Alerts: " + (.alert_summary.active_alerts.total | tostring)'

echo -e "\n=== End Health Check ===\n"
```

## 🔧 Essential Configuration

### Production Environment Variables
```bash
# Production .env template
BELLA_API_KEY="64-char-production-key"
APP_ENV="production"
DATABASE_URL="postgresql://user:pass@host:5432/bella_prod"

# External services
OPENAI_API_KEY="sk-production-key"
TWILIO_ACCOUNT_SID="AC-production-sid"
TWILIO_AUTH_TOKEN="production-auth-token"

# Optional: Alerting
SLACK_WEBHOOK_URL="https://hooks.slack.com/services/T.../B.../..."
SMTP_HOST="smtp.gmail.com"
SMTP_PORT="587"
SMTP_USER="alerts@yourcompany.com"
SMTP_PASSWORD="app-password"
ALERT_EMAIL="oncall@yourcompany.com"

# Optional: Redis
REDIS_URL="redis://localhost:6379"

# Optional: AWS Cost Tracking
AWS_ACCESS_KEY_ID="AKIA..."
AWS_SECRET_ACCESS_KEY="secret-key"
AWS_DEFAULT_REGION="us-east-1"
```

### Twilio Webhook Configuration
```bash
# Set webhook URL in Twilio Console:
# Voice URL: https://your-domain.com/twilio/voice
# HTTP Method: POST
# Voice Method: POST

# For local development, use ngrok:
ngrok http 8000
# Use the https URL provided by ngrok
```

### Cost Budget Configuration
```python
# Edit app/services/cost_optimization.py
class CostOptimizer:
    def __init__(self):
        self.monthly_budget = 100.0  # Adjust your monthly budget
        self.whisper_cost_per_minute = 0.006  # OpenAI pricing
```

## 📊 Understanding the Dashboard

### Operations Tab (📅)
- **KPI Cards**: Users, appointments, today's bookings, system status
- **Recent Appointments**: Last 10 appointments with status
- **Quick Actions**: Edit/delete appointments (coming soon)

### Analytics Tab (💰)
- **Cost Overview**: Monthly spend, budget utilization
- **Cost Breakdown**: Service-wise spending analysis
- **Optimization**: Savings recommendations
- **Trends**: Historical cost patterns

### System Tab (⚡)
- **Performance Metrics**: Response time, cache hit rate, uptime
- **Component Health**: API server, database, cache, external services
- **Circuit Breakers**: Service protection status
- **SLA Monitoring**: Real-time SLA compliance

## 🚨 Common Startup Issues

### "Address already in use"
```bash
# Find and kill process using port 8000
lsof -i :8000
kill -9 <PID>

# Or use different port
uvicorn app.main:app --port 8001
```

### "Database connection failed"
```bash
# Recreate database
rm bella.db
python -c "from app.db.base import init_db; init_db()"
```

### "Invalid API key" errors
```bash
# Check environment variable is set
echo $BELLA_API_KEY

# Check API key format (should be 32+ characters)
# Regenerate if needed: openssl rand -hex 32
```

### Dashboard won't load
1. Check API key is stored in browser localStorage
2. Open browser developer tools → Storage → Local Storage
3. Add key: `bella_api_key` = `your-api-key`
4. Refresh page

### OpenAI circuit breaker "open"
```bash
# Check OpenAI API key and credits
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
     https://api.openai.com/v1/models

# Check OpenAI service status
curl https://status.openai.com/api/v2/status.json
```

## 🎯 Next Steps

### For Operators
1. **Set up monitoring**: Configure Slack/email alerts
2. **Create dashboards**: Bookmark key URLs for quick access
3. **Establish procedures**: Daily checks, weekly reviews
4. **Document customizations**: Any local configuration changes

### For Developers
1. **Review codebase**: Understand service architecture
2. **Run tests**: `pytest tests/ -v`
3. **Set up development**: Use development environment variables
4. **Read documentation**: API docs, operations runbook

### For Production Deployment
1. **Security review**: HTTPS, strong keys, signature validation
2. **Infrastructure**: Load balancer, database, Redis, monitoring
3. **Backup strategy**: Database backups, configuration backups
4. **Monitoring setup**: External uptime monitoring, log aggregation

## 📚 Additional Resources

### Essential Documentation
- **[Operations Runbook](./OPERATIONS.md)**: Complete operational procedures
- **[API Documentation](./API.md)**: All endpoints and examples
- **[Troubleshooting FAQ](./FAQ.md)**: Common problems and solutions

### Useful Commands Reference
```bash
# Application management
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
python -c "from app.db.base import init_db; init_db()"

# Health checks
curl http://localhost:8000/healthz
curl -H "X-API-Key: $API_KEY" http://localhost:8000/api/unified/status

# Monitoring
curl -H "X-API-Key: $API_KEY" http://localhost:8000/api/unified/business-metrics
curl -H "X-API-Key: $API_KEY" http://localhost:8000/api/unified/circuit-breakers

# Database management
sqlite3 bella.db ".tables"
sqlite3 bella.db "SELECT COUNT(*) FROM appointments;"

# Environment debugging
env | grep -E "(BELLA|OPENAI|TWILIO)"
```

### Emergency Contacts
```
Primary Support: [Your team contact]
Emergency Hotline: [24/7 contact]
Vendor Support:
- OpenAI: https://help.openai.com/
- Twilio: https://support.twilio.com/
```

---

**🎯 You're Ready!**

Your Bella V3 system is now operational with enterprise-grade monitoring and alerting.

**Next Steps:**
1. Make a test voice call to verify end-to-end functionality
2. Set up production alerting channels (Slack/email)
3. Configure any additional monitoring or backup systems
4. Review the full [Operations Runbook](./OPERATIONS.md) for ongoing maintenance

*Need help? Check the [FAQ](./FAQ.md) or contact your support team.*

*Last Updated: 2025-09-30*
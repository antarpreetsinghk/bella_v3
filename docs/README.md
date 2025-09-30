# Bella V3 - Enterprise Voice Appointment Booking System

> **Production-Ready AI-Powered Voice Assistant with Enterprise Monitoring & Cost Optimization**

![Status](https://img.shields.io/badge/Status-Production_Ready-green)
![Version](https://img.shields.io/badge/Version-3.0-blue)
![License](https://img.shields.io/badge/License-Private-red)

Bella V3 is a sophisticated voice appointment booking system that combines AI-powered natural language processing with enterprise-grade monitoring, alerting, and cost optimization capabilities.

## 🌟 Key Features

### 🎤 **Voice Processing**
- **Twilio Integration**: Professional voice call handling
- **OpenAI Whisper STT**: Advanced speech-to-text processing
- **Natural Language Processing**: Intelligent appointment extraction
- **Multi-timezone Support**: Automatic timezone handling

### 🛡️ **Enterprise Reliability**
- **Circuit Breaker Pattern**: Automatic failover protection
- **SLA Monitoring**: 99.9% uptime targets with real-time tracking
- **Production Alerting**: Multi-channel notifications (Slack, Email, SMS)
- **Comprehensive Logging**: Structured logging with error aggregation

### 📊 **Business Intelligence**
- **Real-time KPIs**: Call success rates, response times, completion rates
- **Performance Trends**: Hourly/daily analysis with visualization
- **Cost Optimization**: Budget tracking with intelligent recommendations
- **Usage Analytics**: Peak hour analysis and scaling recommendations

### 🎛️ **Unified Operations Dashboard**
- **Multi-tab Interface**: Operations, Analytics, and System monitoring
- **Live Metrics**: Real-time performance and health indicators
- **Alert Management**: Create, track, and resolve alerts
- **Cost Tracking**: Budget utilization and optimization insights

## 🏗️ Architecture Overview

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

Enterprise Features:
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Circuit        │    │  Business        │    │  Alerting       │
│  Breakers       │    │  Metrics         │    │  System         │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Valid API keys for OpenAI and Twilio
- Optional: Redis for session storage, AWS for cost tracking

### Installation
```bash
# Clone repository
git clone <repository-url>
cd bella_v3

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export BELLA_API_KEY="your-secure-api-key"
export OPENAI_API_KEY="sk-your-openai-key"
export TWILIO_ACCOUNT_SID="ACyour-account-sid"
export TWILIO_AUTH_TOKEN="your-auth-token"
export DATABASE_URL="sqlite+aiosqlite:///./bella.db"

# Initialize database
python -c "from app.db.base import init_db; init_db()"

# Start the application
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Verification
```bash
# Test health
curl http://localhost:8000/healthz

# Test API access
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/unified/status

# Access dashboard
open http://localhost:8000/
```

## 📱 Usage

### Voice Calls
1. **Configure Twilio**: Set webhook URL to `https://your-domain.com/twilio/voice`
2. **Make Test Call**: Call your Twilio number
3. **Voice Interaction**: "I need an appointment tomorrow at 2pm"
4. **Automatic Processing**: System extracts details and books appointment

### Dashboard Access
- **URL**: `http://localhost:8000/`
- **Authentication**: API Key (stored in browser localStorage)
- **Tabs**: Operations, Analytics, System monitoring

### API Integration
```bash
# Create appointment via API
curl -X POST -H "X-API-Key: your-key" \
     -H "Content-Type: application/json" \
     -d '{
       "user_id": 1,
       "starts_at": "2025-10-01T14:00:00Z",
       "duration_min": 60,
       "notes": "Regular checkup"
     }' \
     http://localhost:8000/api/appointments

# Extract appointment from text
curl -X POST -H "X-API-Key: your-key" \
     -H "Content-Type: application/json" \
     -d '{
       "text": "I need an appointment tomorrow at 2pm"
     }' \
     http://localhost:8000/api/assistant/extract-appointment
```

## 🔧 Configuration

### Environment Variables
```bash
# Core Application
BELLA_API_KEY="your-secure-api-key"
APP_ENV="production"  # or "development"
DATABASE_URL="sqlite+aiosqlite:///./bella.db"

# External Services
OPENAI_API_KEY="sk-your-openai-key"
TWILIO_ACCOUNT_SID="ACyour-account-sid"
TWILIO_AUTH_TOKEN="your-auth-token"

# Optional: Redis Session Storage
REDIS_URL="redis://localhost:6379"

# Optional: Alerting (Slack)
SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."

# Optional: Email Alerts
SMTP_HOST="smtp.gmail.com"
SMTP_PORT="587"
SMTP_USER="alerts@yourcompany.com"
SMTP_PASSWORD="your-app-password"
ALERT_EMAIL="oncall@yourcompany.com"

# Optional: AWS Cost Tracking
AWS_ACCESS_KEY_ID="AKIA..."
AWS_SECRET_ACCESS_KEY="your-secret"
AWS_DEFAULT_REGION="us-east-1"
```

### Circuit Breaker Thresholds
```python
# app/services/circuit_breaker.py
openai_config = CircuitBreakerConfig(
    failure_threshold=3,      # Trip after 3 failures
    recovery_timeout=30,      # Try recovery after 30s
    timeout=15.0,            # 15s timeout for API calls
    half_open_max_calls=2    # Test with 2 calls during recovery
)
```

### Cost Optimization Settings
```python
# app/services/cost_optimization.py
monthly_budget = 50.0        # Monthly budget in USD
whisper_cost_per_minute = 0.006  # OpenAI Whisper pricing
```

## 📊 Monitoring & Operations

### Key Metrics
- **System Uptime**: Target 99.9% (monitored continuously)
- **Call Success Rate**: Target >95% (alerts if <90%)
- **Response Time**: Target 99% under 2 seconds
- **Cost per Call**: Target <$0.05 per successful call

### Dashboard Indicators
- 🟢 **Green**: System healthy, all metrics within targets
- 🟡 **Yellow**: Warning state, degraded performance
- 🔴 **Red**: Critical issues, immediate attention required

### Alert Severity Levels
- **🔴 CRITICAL**: System failure, SLA breach >1%, budget exceeded
- **🟠 HIGH**: Service degradation, circuit breaker open, budget at 90%
- **🟡 MEDIUM**: Performance issues, budget at 80%, failed calls
- **🟢 LOW**: Service recovery, maintenance notifications

### Operations Endpoints
```bash
# System health
GET /api/unified/status

# Business metrics
GET /api/unified/business-metrics

# Circuit breaker status
GET /api/unified/circuit-breakers

# Active alerts
GET /api/unified/alerts

# SLA dashboard
GET /api/unified/sla-metrics

# Cost optimization
GET /api/unified/cost-optimization
```

## 🔒 Security

### Authentication
- **API Key**: Required for all protected endpoints
- **Twilio Signature**: Webhook signature verification
- **HTTPS**: Required for production Twilio integration

### Best Practices
- Rotate API keys monthly
- Use strong, random API keys (32+ characters)
- Enable Twilio signature validation in production
- Store secrets in environment variables, not code
- Monitor for unauthorized access attempts

## 📈 Performance

### Optimization Features
- **Circuit Breaker Protection**: Prevents cascading failures
- **Response Caching**: Reduces redundant API calls
- **Efficient Database Queries**: Optimized with proper indexing
- **Background Processing**: Non-blocking alerting and metrics
- **Resource Monitoring**: Automatic cleanup of old data

### Scaling Considerations
- **Vertical Scaling**: Increase CPU/memory for higher call volumes
- **Database**: Consider PostgreSQL for >1000 concurrent users
- **Redis**: Recommended for session storage in production
- **Load Balancing**: Multiple instances behind load balancer
- **CDN**: Use CDN for dashboard assets in global deployments

## 💰 Cost Management

### Cost Tracking
- **Real-time Monitoring**: Track spending as it happens
- **Budget Alerts**: 80%, 90%, and 100% threshold notifications
- **Usage Analysis**: Peak hour and pattern identification
- **Optimization Recommendations**: Automated suggestions for cost reduction

### Cost Optimization Strategies
1. **Whisper API Caching**: Cache transcription results
2. **Audio Preprocessing**: Reduce file size before processing
3. **Peak Hour Management**: Scale based on usage patterns
4. **Alternative STT**: Consider self-hosted options for high volume

## 🛠️ Development

### Project Structure
```
bella_v3/
├── app/
│   ├── api/routes/          # API endpoints
│   ├── core/                # Core utilities (logging, errors)
│   ├── db/                  # Database models and session
│   └── services/            # Business logic services
├── docs/                    # Documentation
├── tests/                   # Test suite
└── requirements.txt         # Dependencies
```

### Key Services
- **`alerting.py`**: Production alerting and SLA monitoring
- **`business_metrics.py`**: KPI tracking and performance analytics
- **`circuit_breaker.py`**: Service protection and failover
- **`cost_optimization.py`**: Budget tracking and optimization
- **`whisper_stt.py`**: Speech-to-text processing
- **`dashboard_session.py`**: Session management for dashboard

### Development Commands
```bash
# Run with hot reload
uvicorn app.main:app --reload --log-level debug

# Run tests
pytest tests/ -v

# Format code
black app/ tests/

# Type checking
mypy app/

# Security scan
bandit -r app/
```

## 📚 Documentation

### Available Documentation
- **[Operations Runbook](./OPERATIONS.md)**: Complete operational procedures
- **[API Documentation](./API.md)**: Comprehensive API reference
- **[Troubleshooting FAQ](./FAQ.md)**: Common issues and solutions
- **[Quick Start Guide](./QUICKSTART.md)**: Getting started tutorial

### Documentation Structure
- **Operations**: Daily procedures, monitoring, emergency responses
- **API Reference**: All endpoints with examples and responses
- **Troubleshooting**: Common issues, error codes, solutions
- **Development**: Setup, testing, contribution guidelines

## 🎯 Production Checklist

### Before Deployment
- [ ] Set strong `BELLA_API_KEY`
- [ ] Configure Twilio webhook with HTTPS URL
- [ ] Set up OpenAI API key with sufficient credits
- [ ] Configure alerting channels (Slack, email)
- [ ] Set appropriate cost budget and thresholds
- [ ] Test voice call flow end-to-end
- [ ] Verify dashboard access and functionality
- [ ] Set up monitoring and log aggregation
- [ ] Configure backup and recovery procedures

### Production Environment
- [ ] Use PostgreSQL instead of SQLite for high volume
- [ ] Set up Redis for session storage
- [ ] Enable HTTPS for all endpoints
- [ ] Configure load balancer and multiple instances
- [ ] Set up log rotation and retention
- [ ] Monitor system resources (CPU, memory, disk)
- [ ] Implement automated backups
- [ ] Set up external monitoring/uptime checks

## 🚨 Support & Troubleshooting

### Quick Diagnostics
```bash
# Check overall health
curl -H "X-API-Key: $API_KEY" http://localhost:8000/api/unified/status

# Check for active alerts
curl -H "X-API-Key: $API_KEY" http://localhost:8000/api/unified/alerts

# Verify circuit breaker status
curl -H "X-API-Key: $API_KEY" http://localhost:8000/api/unified/circuit-breakers
```

### Common Issues
- **Dashboard not loading**: Check API key in localStorage
- **Voice calls failing**: Verify Twilio webhook signature
- **High costs**: Enable caching, check usage patterns
- **Circuit breaker open**: Check OpenAI service status
- **Performance issues**: Monitor response times and optimize

### Getting Help
1. **Check Documentation**: Start with [FAQ](./FAQ.md) for common issues
2. **Review Logs**: Check application logs for error details
3. **Monitor Dashboard**: Use unified dashboard for system status
4. **Test Components**: Isolate issues using individual API endpoints
5. **Emergency Contacts**: See [Operations Runbook](./OPERATIONS.md) for escalation

## 📊 System Specifications

### Performance Targets
- **Uptime**: 99.9% (8.76 hours downtime/year)
- **Response Time**: <2 seconds for 99% of requests
- **Call Success Rate**: >95% successful completions
- **Error Rate**: <5% of total requests
- **Cost per Call**: <$0.05 for successful appointments

### Resource Requirements
- **Minimum**: 2 CPU cores, 4GB RAM, 10GB disk
- **Recommended**: 4 CPU cores, 8GB RAM, 50GB disk
- **High Volume**: 8+ CPU cores, 16GB+ RAM, 100GB+ disk

### Supported Platforms
- **OS**: Linux (Ubuntu 20.04+), macOS, Windows
- **Python**: 3.10, 3.11, 3.12
- **Database**: SQLite (development), PostgreSQL (production)
- **Cache**: In-memory (development), Redis (production)

## 🏆 Version History

### v3.0 (Current) - 2025-09-30
- ✅ Complete enterprise monitoring and alerting system
- ✅ Circuit breaker pattern for service protection
- ✅ Comprehensive business metrics and KPI tracking
- ✅ Cost optimization with budget monitoring
- ✅ Unified operations dashboard
- ✅ Production-ready SLA monitoring
- ✅ Multi-channel alerting (Slack, Email, SMS)

### v2.0 (Previous)
- ✅ Voice call processing with Twilio
- ✅ OpenAI Whisper speech-to-text integration
- ✅ Appointment extraction and booking
- ✅ Basic monitoring and logging

### v1.0 (Initial)
- ✅ Core appointment management
- ✅ User management system
- ✅ Basic API endpoints

---

**🎯 Bella V3 - Production-Ready Enterprise Voice Assistant**

*Built with enterprise reliability, monitoring, and cost optimization in mind.*

**Quick Links:**
- 📖 [Operations Guide](./OPERATIONS.md)
- 🔧 [API Reference](./API.md)
- ❓ [Troubleshooting](./FAQ.md)
- 🚀 [Quick Start](./QUICKSTART.md)

*Last Updated: 2025-09-30*
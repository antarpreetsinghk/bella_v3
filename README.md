# Bella V3 - Intelligent Voice Appointment Booking System

[![CI/CD Pipeline](https://github.com/antarpreetsinghk/bella_v3/actions/workflows/ci.yml/badge.svg)](https://github.com/antarpreetsinghk/bella_v3/actions/workflows/ci.yml)
[![Production Status](https://img.shields.io/badge/production-live-green)](http://bella-alb-1924818779.ca-central-1.elb.amazonaws.com/)

> **🎯 Enterprise-grade voice appointment booking system with AI-powered natural language processing**

Bella V3 is a sophisticated voice-first appointment booking platform that combines Twilio voice services, OpenAI language processing, and robust AWS infrastructure to provide seamless appointment scheduling through natural conversation.

## 🌟 Key Features

### 🎙️ **Voice-First Experience**
- **Natural Language Processing**: "Monday at 3 PM", "tomorrow morning", "next Tuesday"
- **Canadian Time Zone Support**: Intelligent parsing with Edmonton/Calgary timezone handling
- **Interactive Voice Response**: Guided conversation flow with speech recognition
- **Twilio Integration**: Production-grade telephony with signature validation

### 🏗️ **Enterprise Architecture**
- **FastAPI Backend**: High-performance async Python web framework
- **PostgreSQL Database**: AWS RDS with connection pooling and transactions
- **Redis Caching**: Session management and performance optimization
- **AWS Cloud Deployment**: ECS, ALB, RDS, ElastiCache infrastructure

### 📊 **Monitoring & Observability**
- **Unified Operations Dashboard**: Real-time metrics, costs, and performance
- **Business Intelligence**: User growth, revenue tracking, appointment analytics
- **Cost Optimization**: AWS cost monitoring with budget alerts
- **Circuit Breakers**: Resilient external API integration (OpenAI, Twilio)

### 🔒 **Security & Compliance**
- **API Key Authentication**: Secure endpoint access control
- **Twilio Signature Validation**: Webhook request verification
- **AWS Secrets Manager**: Encrypted credential storage
- **CORS Protection**: Cross-origin request security
- **Rate Limiting**: DoS protection and quota management

### 🚀 **DevOps & CI/CD**
- **GitHub Actions**: Automated testing, building, and deployment
- **Docker Containerization**: Consistent environments across dev/staging/prod
- **Database Migrations**: Alembic-managed schema versioning
- **Health Checks**: Comprehensive monitoring and alerting
- **Rollback Capabilities**: Automated failure recovery

## 🏁 Quick Start

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- PostgreSQL (or use included Docker setup)
- Redis (or use included Docker setup)

### 1. Clone & Setup
```bash
git clone https://github.com/antarpreetsinghk/bella_v3.git
cd bella_v3

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration
```bash
# Copy template and configure
cp .env.template .env

# Edit .env with your credentials:
# - OPENAI_API_KEY=sk-your-openai-key
# - TWILIO_ACCOUNT_SID=AC-your-twilio-sid
# - TWILIO_AUTH_TOKEN=your-twilio-token
# - BELLA_API_KEY=your-secure-api-key
```

### 3. Database Setup
```bash
# Start local services
docker-compose up -d postgres redis

# Run migrations
alembic upgrade head
```

### 4. Start Development Server
```bash
# Run the application
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Access the dashboard
open http://localhost:8000
```

## 📱 Usage Examples

### Voice Call Flow
1. **Customer calls**: `+1-438-256-5719`
2. **System greets**: "Hi there! Thanks for calling. I'll help you book your appointment today."
3. **Name collection**: "What's your name?"
4. **Phone verification**: "Could you please give me your phone number?"
5. **Natural scheduling**: "When would you like your appointment?"
   - "Monday at 3 PM" ✅
   - "Tomorrow morning" ✅
   - "Next Tuesday at 2:30" ✅
6. **Confirmation**: "I have John Doe on Monday, October 2nd at 3:00 PM. Should I book it?"
7. **Booking completion**: "Thank you. Your appointment is booked!"

### API Integration
```python
import httpx

# Book appointment via API
response = httpx.post(
    "https://your-domain.com/api/v1/appointments",
    headers={"X-API-Key": "your-api-key"},
    json={
        "user_name": "John Doe",
        "phone": "+14165551234",
        "start_time": "2024-10-02T15:00:00Z",
        "duration_minutes": 30
    }
)
```

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Twilio Voice  │───▶│   AWS ALB        │───▶│   ECS Cluster   │
│   Webhooks      │    │   Load Balancer  │    │   (Fargate)     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         │
┌─────────────────┐    ┌──────────────────┐             │
│   Web Dashboard │───▶│   Route 53 DNS   │             │
│   Admin Panel   │    │   CloudFront CDN │             │
└─────────────────┘    └──────────────────┘             │
                                                         ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   OpenAI API    │◀───│   FastAPI App    │───▶│   RDS PostgreSQL│
│   GPT-4 Mini    │    │   (Bella V3)     │    │   Multi-AZ      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                         │
                                ▼                         │
                       ┌──────────────────┐              │
                       │  ElastiCache     │              │
                       │  Redis Cluster   │              │
                       └──────────────────┘              │
                                                         │
                       ┌──────────────────┐              │
                       │  AWS Secrets     │◀─────────────┘
                       │  Manager         │
                       └──────────────────┘
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `APP_ENV` | Environment mode | `production`, `development`, `testing` |
| `BELLA_API_KEY` | API authentication key | `your-secure-64-char-key` |
| `DATABASE_URL` | PostgreSQL connection | `postgresql+asyncpg://user:pass@host:5432/db` |
| `REDIS_URL` | Redis connection | `redis://host:6379/0` |
| `OPENAI_API_KEY` | OpenAI API access | `sk-proj-...` |
| `TWILIO_ACCOUNT_SID` | Twilio account ID | `AC...` |
| `TWILIO_AUTH_TOKEN` | Twilio auth token | `...` |
| `TWILIO_PHONE_NUMBER` | Your Twilio number | `+14382565719` |

### Production Secrets
Secrets are managed via AWS Secrets Manager in production:
```bash
# Retrieve production configuration
aws secretsmanager get-secret-value --secret-id bella-env --region ca-central-1
```

## 🚀 Deployment

### Local Development
```bash
# Full local stack
docker-compose up -d

# Development server with hot reload
python -m uvicorn app.main:app --reload
```

### AWS Production Deployment
```bash
# Deploy via GitHub Actions (automatic on push to main)
git push origin main

# Manual deployment
./scripts/production/deploy.sh

# Monitor deployment
aws ecs describe-services --cluster bella-prod-cluster --services bella-prod-service
```

### Infrastructure as Code
- **ECS Task Definition**: `aws/task-definition.json`
- **GitHub Actions**: `.github/workflows/ci.yml`
- **Docker Configuration**: `Dockerfile`, `docker-compose.yml`

## 📊 Monitoring & Operations

### Health Checks
- **Application Health**: `GET /healthz`
- **Database Health**: `GET /readyz`
- **CI/CD Health**: `POST /ci-health`

### Operations Dashboard
Access the unified dashboard at `/` for:
- 📈 **Business Metrics**: User growth, appointments, revenue
- 💰 **Cost Monitoring**: AWS spend tracking, budget alerts
- ⚡ **Performance**: Response times, error rates, throughput
- 🔧 **System Health**: Database status, external API health

### Alerting
- **Cost Alerts**: 80% and 90% budget thresholds
- **Performance Monitoring**: Circuit breaker status
- **Error Tracking**: Structured logging with severity levels

## 🧪 Testing

### Running Tests
```bash
# Unit tests
pytest tests/ -v

# Integration tests
python -m pytest tests/test_booking_service.py -v

# Load testing
python scripts/run_load_tests.py

# Security scanning
safety check
bandit -r app/
```

### CI/CD Pipeline
- ✅ **Unit Tests**: Automated testing with pytest
- ✅ **Security Scans**: SAST with bandit and safety
- ✅ **Docker Build**: Multi-stage optimized builds
- ✅ **Smoke Tests**: Production deployment validation
- ✅ **Rollback**: Automatic failure recovery

## 🔒 Security

### Security Features
- **API Authentication**: X-API-Key header validation
- **Webhook Validation**: Twilio signature verification
- **Input Sanitization**: SQL injection prevention
- **Rate Limiting**: DoS protection
- **CORS Policy**: Origin-based access control

### Security Scanning
```bash
# Vulnerability scanning
./scripts/security-setup.sh

# Dependency auditing
pip-audit

# Static analysis
bandit -r app/ -f json -o security-reports/bandit-report.json
```

## 📈 Performance

### Optimization Features
- **Connection Pooling**: Database connection management
- **Redis Caching**: Session and response caching
- **Circuit Breakers**: External API resilience
- **Async Processing**: Non-blocking I/O operations
- **Load Balancing**: AWS Application Load Balancer

### Performance Metrics
- **Response Time**: < 200ms for API calls
- **Uptime**: 99.9% availability target
- **Throughput**: 1000+ requests/minute capacity
- **Concurrent Users**: 100+ simultaneous calls

## 🤝 Contributing

### Development Workflow
1. **Fork** the repository
2. **Create** feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** changes (`git commit -m 'Add amazing feature'`)
4. **Push** to branch (`git push origin feature/amazing-feature`)
5. **Open** Pull Request

### Code Standards
- **Python**: PEP 8 compliance with black formatting
- **Type Hints**: Full type annotation coverage
- **Documentation**: Docstrings for all public functions
- **Testing**: Minimum 80% code coverage
- **Security**: No hardcoded secrets or credentials

### Development Setup
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Set up pre-commit hooks
pre-commit install

# Run code formatting
black app/ tests/
isort app/ tests/

# Type checking
mypy app/
```

## 📞 Support & Contact

### Production Support
- **Health Dashboard**: http://bella-alb-1924818779.ca-central-1.elb.amazonaws.com/
- **System Status**: Monitor via `/healthz` endpoint
- **Logs**: CloudWatch logs in AWS console

### Development Support
- **Issues**: [GitHub Issues](https://github.com/antarpreetsinghk/bella_v3/issues)
- **Documentation**: `/docs` folder contains detailed guides
- **API Docs**: Available at `/docs` when running locally

### Emergency Contacts
- **Production Issues**: Check AWS CloudWatch alarms
- **Database Issues**: RDS monitoring console
- **Twilio Issues**: Twilio console error logs

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Twilio**: Voice services and telephony infrastructure
- **OpenAI**: AI-powered natural language processing
- **AWS**: Cloud infrastructure and managed services
- **FastAPI**: High-performance web framework
- **PostgreSQL**: Reliable database engine

---

**Built with ❤️ by the Bella V3 team**

*Last updated: October 2025*
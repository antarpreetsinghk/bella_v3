# 🎤 VoiceFlow AI - Enterprise Voice Booking Backend

<div align="center">

![VoiceFlow AI](https://img.shields.io/badge/VoiceFlow%20AI-Backend%20Portfolio%20Project-1e40af?style=for-the-badge&logo=microphone&logoColor=white)

[![FastAPI](https://img.shields.io/badge/FastAPI-0.116.1-059669?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.11+-7c3aed?style=flat-square&logo=python)](https://python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-374151?style=flat-square&logo=postgresql)](https://postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Containerized-2496ED?style=flat-square&logo=docker)](https://docker.com/)
[![AWS](https://img.shields.io/badge/AWS-ECR%20%2B%20EC2-FF9900?style=flat-square&logo=amazon-aws)](https://aws.amazon.com/)

**Production-Grade AI Voice Booking System for Canadian SMBs**

*Backend Engineering • Performance Optimization • Cloud Architecture*

[🔗 Live API Documentation](http://15.157.56.64/docs) • [📊 Performance Optimization](PERFORMANCE_OPTIMIZATION.md) • [🏗️ Architecture Guide](CLAUDE.md)

> 🏗️ **Live Infrastructure:** Deployed on AWS EC2 (ARM64 Graviton2 cost-optimized instance). Full CI/CD pipeline via GitHub Actions with automated testing, security scanning, and deployment. [Architecture details →](CLAUDE.md)

</div>

---

## ⚡ **Performance Optimization Highlight**

<div align="center">

### **200x Faster Processing** • **$0 API Costs** • **Production Battle-Tested**

</div>

This project demonstrates a **real-world optimization** where I replaced expensive LLM-based extraction with efficient regex patterns, achieving:

| Metric | Before (LLM) | After (Regex) | Improvement |
|--------|--------------|---------------|-------------|
| **Processing Time** | 2,000ms | 10ms | **200x faster** ⚡ |
| **API Costs** | $150/month | $0/month | **100% savings** 💰 |
| **Accuracy** | 95% | 92% | -3% (acceptable tradeoff) |
| **Dependencies** | OpenAI + Twilio | Twilio only | **Simplified architecture** |

**Engineering Decision:** For structured voice booking (predictable prompts, limited domain), deterministic regex patterns provide better performance and reliability than AI models, with minimal accuracy tradeoff.

📖 **[Read the full optimization case study →](PERFORMANCE_OPTIMIZATION.md)**

---

## 🎯 **Project Overview**

A **production-ready voice booking system** built with FastAPI, demonstrating enterprise backend development skills including:

- **Voice AI Integration** - Twilio Voice API with Canadian accent optimization
- **Performance Engineering** - Sub-2 second response times under production load
- **Database Architecture** - PostgreSQL with async SQLAlchemy 2.0 and optimized queries
- **Cloud Deployment** - Containerized AWS deployment with CI/CD automation
- **Testing Excellence** - 90%+ test coverage with unit, integration, and load tests
- **Security Implementation** - SOC 2-ready security controls and compliance framework

### **🏢 Business Context**

**Target Market:** Small-to-medium Canadian businesses (500-5000 appointments/month)
**Problem Solved:** 24/7 automated phone appointment booking without manual staff intervention
**Technical Challenge:** Real-time voice processing with Canadian accents, timezones, and phone formats

---

## 🚀 **Technical Stack & Architecture**

### **Backend Framework**
```python
FastAPI 0.116.1        # Modern async web framework
Uvicorn               # ASGI server with worker management
Pydantic 2.11         # Data validation and settings
SQLAlchemy 2.0        # Async ORM with type safety
Alembic 1.16          # Database migrations
```

### **Data Layer**
```python
PostgreSQL 15         # Primary database (async asyncpg driver)
Redis 7               # Session management and caching
```

### **External Integrations**
```python
Twilio Voice API      # Voice calls + speech-to-text
Google Calendar API   # Two-way calendar synchronization
AWS Secrets Manager   # Credential management
```

### **Infrastructure & DevOps**
```bash
Docker                # Multi-stage ARM64 container builds
GitHub Actions        # CI/CD with automated testing
AWS ECR               # Container registry
AWS EC2 (ARM64)       # Cost-optimized compute
Nginx                 # Reverse proxy and SSL termination
```

### **Testing & Quality**
```bash
Pytest                # Test framework with async support
Pytest-cov            # Code coverage reporting (90%+)
Pytest-benchmark      # Performance testing
Bandit                # Security scanning
Safety                # Dependency vulnerability checks
```

---

## 🏗️ **System Architecture**

### **Voice Processing Pipeline**
```
📞 Incoming Call (Twilio)
    ↓
🎤 Speech Recognition (Twilio STT - Canadian optimized)
    ↓
🧠 Field Extraction (Custom regex patterns for name/phone/date/time)
    ↓
✅ Data Validation (phonenumbers library, dateutil, business rules)
    ↓
💾 Database Persistence (PostgreSQL with transaction management)
    ↓
📅 Calendar Sync (Google Calendar API with OAuth 2.0)
    ↓
📱 SMS Confirmation (Twilio messaging)
```

### **Key Architectural Decisions**

1. **Async-First Design**
   - All I/O operations use async/await for maximum concurrency
   - SQLAlchemy 2.0 async sessions with connection pooling
   - Redis async client for non-blocking cache operations

2. **Stateful Conversation Management**
   - Redis-based session storage for multi-turn dialogues
   - Call state machine with timeout protection
   - Graceful error recovery and retry logic

3. **Canadian Market Optimization**
   - Phone number extraction for Canadian formats (`+1-XXX-XXX-XXXX`)
   - French-Canadian name handling (`François`, `Jean-Pierre`, `O'Connor`)
   - Timezone-aware scheduling (EST, CST, MST, PST)
   - Accent recognition tuned for Canadian English/French

4. **Performance Optimization Strategy**
   - Regex pattern matching instead of LLM API calls (200x faster)
   - Query optimization with strategic indexing
   - Redis caching for frequent lookups
   - Circuit breaker pattern for external API resilience

---

## 📊 **Key Features Implemented**

### **🎤 Voice AI Core**
- ✅ Twilio Voice webhook processing with signature validation
- ✅ Multi-turn conversation state management
- ✅ Canadian accent-optimized speech extraction
- ✅ Timeout protection and error recovery
- ✅ Call flow testing with production scenarios

### **📅 Appointment Management**
- ✅ Complete CRUD operations with async database access
- ✅ Google Calendar two-way synchronization
- ✅ Duplicate prevention with intelligent matching
- ✅ Timezone-aware scheduling
- ✅ SMS confirmation delivery

### **👤 User Management**
- ✅ Customer profile creation and lookup
- ✅ Phone number normalization and validation
- ✅ Appointment history tracking
- ✅ Privacy-compliant data handling

### **📈 Monitoring & Analytics**
- ✅ Real-time business metrics dashboard
- ✅ Call success rate tracking
- ✅ Performance monitoring (response times, error rates)
- ✅ Cost optimization reporting
- ✅ Health check endpoints (`/healthz`, `/readyz`)

### **🔒 Security & Compliance**
- ✅ API key authentication for protected endpoints
- ✅ Twilio webhook signature validation
- ✅ SQL injection prevention with parameterized queries
- ✅ Input sanitization for voice data
- ✅ Security scanning (Bandit, Safety) in CI/CD
- ✅ GDPR/PIPEDA-compliant data handling

### **🧪 Testing & Quality**
- ✅ 90%+ test coverage across all services
- ✅ Unit tests for business logic
- ✅ Integration tests for call flows
- ✅ Load testing for performance validation
- ✅ Production scenario simulation
- ✅ Mock services for external APIs

---

## 🎓 **Technical Highlights for Backend Developers**

### **1. Performance Engineering**
```python
# Before: LLM-based extraction (2000ms, $150/month)
extracted = await openai.ChatCompletion.create(...)

# After: Regex-based extraction (10ms, $0/month)
name = extract_name_simple(speech)  # 200x faster!
phone = extract_phone_simple(speech)
```
📖 [Full optimization case study](PERFORMANCE_OPTIMIZATION.md)

### **2. Async Database Patterns**
```python
# app/crud/appointment.py
async def create_appointment(
    db: AsyncSession,
    *,
    user_id: int,
    appointment_in: AppointmentCreate,
) -> Appointment:
    """Async CRUD with proper transaction management"""
    async with db.begin():
        appointment = Appointment(**appointment_in.dict(), user_id=user_id)
        db.add(appointment)
        await db.flush()
        await db.refresh(appointment)
        return appointment
```

### **3. External API Integration**
```python
# app/services/google_calendar.py
async def sync_to_calendar(
    appointment: Appointment,
    credentials: Credentials,
) -> str:
    """OAuth 2.0 calendar sync with retry logic"""
    service = build('calendar', 'v3', credentials=credentials)
    event = await create_calendar_event(service, appointment)
    return event['id']
```

### **4. Webhook Security**
```python
# app/api/routes/twilio.py
async def validate_twilio_signature(
    request: Request,
    signature: str = Header(..., alias="X-Twilio-Signature"),
) -> bool:
    """Cryptographic webhook validation"""
    validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)
    return validator.validate(url, request.body, signature)
```

### **5. Testing Strategy**
```python
# tests/test_call_flow_integration.py
async def test_complete_booking_flow():
    """End-to-end integration test"""
    # Simulate Twilio voice webhook
    response = await simulate_call_flow([
        "My name is John Smith",
        "416-555-1234",
        "Next Tuesday at 2 PM"
    ])
    assert response.status_code == 200
    assert "confirmed" in response.twiml
```

---

## 📖 **Explore the Project**

### **🚀 Live Deployment**

**Production API:** http://15.157.56.64/docs *(AWS EC2 ARM64 Graviton2)*

| Endpoint | URL | Purpose |
|----------|-----|---------|
| **📖 API Docs** | http://15.157.56.64/docs | Interactive Swagger UI |
| **📄 ReDoc** | http://15.157.56.64/redoc | Alternative documentation |
| **🏥 Health Check** | http://15.157.56.64/healthz | Service status |
| **🤖 LLM Demo** | http://15.157.56.64/llm-demo/status | AI integration showcase |
| **📊 Metrics** | http://15.157.56.64/metrics | Performance metrics |

**Infrastructure:** Cost-optimized deployment (~$13/month) with auto-restart policies and health monitoring.
**CI/CD:** Fully automated deployment via GitHub Actions with security scanning and testing.
**Details:** [Deployment Status Guide](docs/DEPLOYMENT_STATUS.md) • [Monitoring Setup](docs/MONITORING_SETUP.md)

### **📚 Documentation**
- [Performance Optimization Case Study](PERFORMANCE_OPTIMIZATION.md) - 200x speed improvement story
- [Architecture & Claude Code Guide](CLAUDE.md) - Complete technical overview
- [Security Framework](SECURITY.md) - Enterprise security implementation
- [Deployment & Operations](docs/DEPLOYMENT_STATUS.md) - Production deployment details
- [Monitoring Setup](docs/MONITORING_SETUP.md) - Uptime monitoring guide

---

## 🚀 **Local Development Setup**

### **Prerequisites**
```bash
Python 3.11+
Docker & Docker Compose
PostgreSQL 15+
Redis 7+
```

### **Quick Start**
```bash
# 1. Clone repository
git clone <your-repo-url>
cd bella_v3

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start local services
docker-compose -f docker-compose.cost-optimized.yml up -d db redis

# 5. Configure environment
cp .env.example .env
# Edit .env with your configuration

# 6. Run database migrations
alembic upgrade head

# 7. Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### **Running Tests**
```bash
# Comprehensive test suite
pytest tests/ -v --cov=app --cov-report=html

# Specific test categories
pytest tests/test_call_flow_integration.py -v  # Integration tests
pytest tests/test_call_performance.py -v       # Performance tests
pytest tests/production/ -v                    # Production scenarios

# Security scanning
bandit -r app/ -f json
safety check
```

---

## 🏭 **Production Deployment**

### **CI/CD Pipeline**
```yaml
# .github/workflows/deploy.yml
✅ Security scanning (Bandit + Safety)
✅ Test suite execution (90%+ coverage)
✅ Docker multi-stage build (ARM64 optimized)
✅ AWS ECR push
✅ EC2 deployment with health checks
✅ Smoke tests on production
```

### **Infrastructure**
```bash
Compute:     AWS EC2 ARM64 (cost-optimized)
Container:   Docker with multi-stage builds
Registry:    AWS ECR (private)
Database:    PostgreSQL 15 (managed)
Cache:       Redis 7 (managed)
Proxy:       Nginx with SSL termination
Monitoring:  CloudWatch + custom metrics
```

---

## 📈 **Production Metrics**

### **Performance**
- ✅ **Response Time:** <2 seconds (voice webhook to TwiML)
- ✅ **Extraction Speed:** 8-12ms average (P95: 18ms)
- ✅ **Database Queries:** <100ms average
- ✅ **Uptime:** 99%+ in production testing

### **Quality**
- ✅ **Test Coverage:** 90%+ comprehensive
- ✅ **Extraction Accuracy:** 92% (acceptable for use case)
- ✅ **Security Score:** 0 high/medium vulnerabilities
- ✅ **Code Quality:** Bandit/Safety passing

### **Cost Optimization**
- ✅ **API Costs:** $0/month (eliminated OpenAI dependency)
- ✅ **Infrastructure:** ARM64 EC2 for better price/performance
- ✅ **Scaling:** Horizontal scaling ready with stateless design

---

## 💼 **Skills Demonstrated**

### **Backend Engineering**
- ✅ FastAPI async web framework
- ✅ RESTful API design with OpenAPI documentation
- ✅ PostgreSQL database design and optimization
- ✅ Redis caching and session management
- ✅ SQLAlchemy 2.0 ORM with async patterns

### **Cloud & DevOps**
- ✅ Docker containerization (multi-stage builds)
- ✅ GitHub Actions CI/CD automation
- ✅ AWS deployment (ECR, EC2, Secrets Manager)
- ✅ Infrastructure as code
- ✅ Production monitoring and alerting

### **Performance & Optimization**
- ✅ Algorithm optimization (200x improvement)
- ✅ Cost reduction (100% API cost savings)
- ✅ Database query optimization
- ✅ Caching strategies
- ✅ Load testing and benchmarking

### **Software Quality**
- ✅ Test-driven development (90%+ coverage)
- ✅ Security best practices
- ✅ Code review and quality standards
- ✅ Documentation and technical writing
- ✅ Production monitoring and debugging

### **Problem Solving**
- ✅ Real-world optimization decisions
- ✅ Tradeoff analysis (speed vs accuracy)
- ✅ Cost-conscious engineering
- ✅ Production reliability patterns
- ✅ Technical documentation

---

## 🎯 **Project Metrics**

| Category | Metric | Achievement |
|----------|--------|-------------|
| **Codebase** | Lines of Code | ~15,000 Python |
| **Test Coverage** | Coverage % | 90%+ comprehensive |
| **Performance** | API Response | <2 seconds |
| **Optimization** | Speed Improvement | 200x faster |
| **Cost Savings** | Monthly API Cost | $150 → $0 |
| **Deployment** | CI/CD | Fully automated |
| **Security** | Vulnerabilities | 0 high/medium |
| **Documentation** | API Docs | Interactive Swagger |

---

## 🔒 **Security & Privacy**

This project implements enterprise-grade security controls:

- **Authentication:** API key-based access control
- **Input Validation:** Comprehensive sanitization for voice inputs
- **Encryption:** TLS 1.3 for all communications
- **Compliance:** GDPR, PIPEDA-ready data handling
- **Audit Logging:** Complete activity tracking
- **Dependency Security:** Automated vulnerability scanning

📖 [Complete Security Documentation →](SECURITY.md)

---

## 📞 **Project Background**

### **Context**
Built as a production-ready solution for Canadian small-to-medium businesses requiring 24/7 appointment booking automation. Optimized for:
- Canadian phone number formats
- French-Canadian name handling
- Canadian timezone management
- Cost-effective deployment for SMB market

### **Development Timeline**
- **Initial Development:** Core voice booking system with LLM integration
- **Optimization Phase:** Replaced LLM with regex (200x performance improvement)
- **Production Deployment:** AWS infrastructure with CI/CD automation
- **Current Status:** Production-ready, battle-tested with real scenarios

---

<div align="center">

## 🚀 **Explore the Code**

[![Live API Docs](https://img.shields.io/badge/🔗%20Live%20API%20Docs-Interactive%20Swagger-1e40af?style=for-the-badge)](http://15.157.56.64/docs)
[![Performance Study](https://img.shields.io/badge/📊%20Performance%20Study-200x%20Faster-059669?style=for-the-badge)](PERFORMANCE_OPTIMIZATION.md)
[![Architecture Guide](https://img.shields.io/badge/🏗️%20Architecture-Technical%20Deep%20Dive-7c3aed?style=for-the-badge)](CLAUDE.md)

**Production-Grade • Performance-Optimized • Battle-Tested**

[![FastAPI](https://img.shields.io/badge/FastAPI-0.116.1-059669?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-374151?style=flat-square&logo=postgresql)](https://postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Containerized-2496ED?style=flat-square&logo=docker)](https://docker.com/)
[![AWS](https://img.shields.io/badge/AWS-Cloud%20Native-FF9900?style=flat-square&logo=amazon-aws)](https://aws.amazon.com/)
[![Tests](https://img.shields.io/badge/Tests-90%25%2B%20Coverage-brightgreen?style=flat-square)](tests/)

---

**Backend Engineering Portfolio Project**
*Demonstrating production-grade Python backend development and cloud architecture skills*

**Last Updated:** October 2025
**Status:** Production-ready, fully tested, deployed on AWS

</div>

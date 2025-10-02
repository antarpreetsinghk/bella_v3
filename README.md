# 🦷 Bella V3 - AI-Powered Dental Appointment System

<div align="center">

![Bella V3 Banner](https://img.shields.io/badge/Bella%20V3-AI%20Appointment%20System-4f46e5?style=for-the-badge&logo=calendar&logoColor=white)

[![Python](https://img.shields.io/badge/Python-3.11+-3776ab?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-336791?style=flat-square&logo=postgresql&logoColor=white)](https://postgresql.org)
[![AWS](https://img.shields.io/badge/AWS-ECS%20%7C%20RDS-ff9900?style=flat-square&logo=amazon-aws&logoColor=white)](https://aws.amazon.com)
[![Twilio](https://img.shields.io/badge/Twilio-Voice%20AI-f22f46?style=flat-square&logo=twilio&logoColor=white)](https://twilio.com)

**Modern Voice-Powered Appointment Booking System for Canadian Dental Practices**

[🚀 Live Demo](https://your-domain.com/admin) • [📚 API Docs](https://your-domain.com/docs) • [📞 Voice System](#voice-booking-system)

</div>

---

## 🌟 Overview

Bella V3 is a cutting-edge AI-powered appointment booking system designed specifically for Canadian dental practices. It combines advanced voice recognition, natural language processing, and intelligent scheduling to provide a seamless patient experience through phone-based booking.

### ✨ Key Features

- 🎤 **AI Voice Booking** - Natural language appointment scheduling via phone calls
- 🇨🇦 **Canadian Optimized** - Enhanced for Canadian English, names, and phone formats
- 🤖 **Smart Extraction** - Advanced name, phone, and time extraction with artifact filtering
- 📊 **Professional Dashboard** - Modern admin interface with real-time analytics
- 🔒 **Enterprise Security** - Session-based authentication with stateless tokens
- 📱 **Responsive Design** - Bootstrap 5 modern UI/UX across all devices
- ☁️ **Cloud Native** - AWS ECS deployment with auto-scaling and monitoring

---

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   📞 Customer   │───▶│   Twilio Voice  │───▶│   Bella V3 API  │
│     Calls       │    │   Recognition   │    │   Processing    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                       ┌─────────────────┐              │
                       │  🤖 AI Layer    │◀─────────────┤
                       │  • GPT-4        │              │
                       │  • Canadian NLP │              │
                       │  • Speech-to-Text│              │
                       └─────────────────┘              │
                                                        │
┌─────────────────┐    ┌─────────────────┐              │
│  📊 Admin       │◀───│  📱 Dashboard   │◀─────────────┤
│  Management     │    │  Bootstrap 5    │              │
└─────────────────┘    └─────────────────┘              │
                                                        │
┌─────────────────┐    ┌─────────────────┐              │
│  📅 Google      │◀───│  🗄️ PostgreSQL  │◀─────────────┘
│  Calendar       │    │  Database       │
└─────────────────┘    └─────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 16+
- Docker & Docker Compose
- Twilio Account
- OpenAI API Key
- AWS Account (for production)

### 🛠️ Local Development

```bash
# Clone the repository
git clone https://github.com/antarpreetsinghk/bella_v3.git
cd bella_v3

# Set up virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Start local database
docker-compose up -d db

# Run database migrations
alembic upgrade head

# Start the application
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 🐳 Docker Deployment

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Health check
curl http://localhost:8000/healthz
```

---

## 📞 Voice Booking System

### How It Works

1. **📱 Customer Calls** → Twilio receives the call
2. **🎤 Voice Capture** → AI-powered Canadian English speech recognition
3. **🧠 Smart Processing** → Multi-layered name, phone, and time extraction
4. **✅ Validation** → Business hours and conflict checking
5. **📅 Booking** → Automatic calendar integration and confirmation

### Supported Voice Patterns

```
✅ "Hi, my name is John Smith, I'd like to book for next Tuesday at 2 PM"
✅ "This is Sarah calling, can I get Thursday morning at 10?"
✅ "Je m'appelle Marie, appointment for tomorrow at 3?"  (Bilingual support)
✅ "416-555-1234, book me for Friday afternoon"
```

### Advanced Speech Processing

- **Canadian Name Recognition** - Optimized for multicultural Canadian names
- **Phone Number Intelligence** - Auto-formatting for Canadian/US numbers
- **Natural Time Parsing** - "next Tuesday", "tomorrow at 3", "Friday morning"
- **Artifact Filtering** - Prevents "so what", "um", "uh" from being saved as names

---

## 🎨 Admin Dashboard

### Professional Interface

<div align="center">

![Dashboard Preview](https://img.shields.io/badge/Modern%20UI-Bootstrap%205-7952b3?style=for-the-badge&logo=bootstrap&logoColor=white)

</div>

**Access**: Contact administrator for production URL

**Demo Credentials**:
- **Username**: `admin` **Password**: `admin123`
- **Username**: `manager` **Password**: `manager123`

### Dashboard Features

| Feature | Description | Status |
|---------|-------------|--------|
| 📊 **Analytics** | Real-time appointment metrics and trends | ✅ Live |
| 👥 **User Management** | Customer profiles and contact information | ✅ Live |
| 📅 **Appointments** | Booking management with status tracking | ✅ Live |
| 🔧 **Admin Tools** | Data cleanup and system maintenance | ✅ Live |
| 📱 **Responsive** | Mobile-optimized interface | ✅ Live |
| 🔒 **Security** | Session-based authentication | ✅ Live |

---

## 🛠️ Technology Stack

### Backend
- **Framework**: FastAPI 0.104+ (Modern Python web framework)
- **Database**: PostgreSQL 16+ with AsyncIO support
- **ORM**: SQLAlchemy 2.0+ with async capabilities
- **Authentication**: Stateless session tokens with HMAC signatures
- **API**: RESTful with automatic OpenAPI documentation

### AI & Voice Processing
- **Speech-to-Text**: Twilio Enhanced Voice Recognition
- **NLP**: OpenAI GPT-4 for intelligent extraction
- **Canadian NLP**: Custom extraction for Canadian contexts
- **Phone Processing**: Google phonenumbers library
- **Time Parsing**: Advanced natural language time processing

### Frontend
- **UI Framework**: Bootstrap 5.3+ with custom theming
- **Design System**: Modern card-based layouts with responsive grids
- **Icons**: Bootstrap Icons for consistent visual language
- **Interactive**: JavaScript for real-time updates

### Infrastructure
- **Cloud**: AWS ECS Fargate for container orchestration
- **Database**: AWS RDS PostgreSQL with automated backups
- **Load Balancer**: AWS Application Load Balancer
- **Monitoring**: AWS CloudWatch with custom metrics
- **CI/CD**: GitHub Actions with automated testing and deployment

---

## 📊 API Reference

### Core Endpoints

#### 🎤 Voice Booking
```http
POST /twilio/voice
Content-Type: application/x-www-form-urlencoded

CallSid=CA123&From=+15551234567
```

#### 📅 Appointments
```http
GET /appointments/
Authorization: Bearer {token}

POST /appointments/
Content-Type: application/json
{
  "user_id": 1,
  "starts_at": "2025-01-15T14:00:00Z",
  "duration_min": 30
}
```

#### 👥 Users
```http
GET /users/
Authorization: Bearer {token}

POST /users/
Content-Type: application/json
{
  "full_name": "John Smith",
  "mobile": "+15551234567"
}
```

#### 🤖 AI Processing
```http
POST /assistant/book
Content-Type: application/json
{
  "transcript": "Hi, this is John, book me for tomorrow at 2 PM",
  "from_number": "+15551234567"
}
```

### Authentication

```bash
# API Key Authentication
curl -H "X-API-Key: your-api-key" https://api.example.com/appointments/

# Admin Dashboard Session
curl -c cookies.txt -X POST /admin/login \
  -d "username=admin&password=admin123"
```

---

## 🚀 Production Deployment

### AWS Infrastructure

```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  api:
    image: bella-v3:latest
    environment:
      - APP_ENV=production
      - DATABASE_URL=${DATABASE_URL}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    deploy:
      replicas: 2
      resources:
        limits:
          memory: 512M
          cpus: '0.25'
```

### Environment Configuration

```bash
# Production Environment Variables
APP_ENV=production
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/bella
OPENAI_API_KEY=sk-...
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
BELLA_API_KEY=secure-random-key
```

### Health Monitoring

- **Health Check**: `/healthz` - Basic health status
- **Readiness**: `/readyz` - Database connectivity check
- **Metrics**: `/metrics` - Performance and error metrics

---

## 🧪 Testing

### Running Tests

```bash
# Unit tests
pytest tests/ -v

# Integration tests
pytest tests/integration/ -v

# Coverage report
pytest --cov=app --cov-report=html

# Load testing
locust -f tests/load_test.py --host=http://localhost:8000
```

### Test Categories

- **🔧 Unit Tests** - Individual component testing
- **🔗 Integration Tests** - API endpoint testing
- **🎤 Voice Tests** - Twilio webhook simulation
- **🤖 AI Tests** - LLM extraction accuracy
- **📊 Performance Tests** - Load and stress testing

---

## 🔒 Security

### Security Features

- **🔐 API Key Authentication** - Secure API access control
- **🍪 Session Management** - Stateless HMAC-signed tokens
- **🛡️ Input Validation** - Comprehensive request sanitization
- **🔍 Audit Logging** - Full request/response logging
- **🌐 CORS Protection** - Cross-origin request security
- **📱 Rate Limiting** - DoS protection (planned)

### Best Practices

- Environment variables for all secrets
- Secure database connections with SSL
- Regular security audits with automated tools
- Dependency vulnerability scanning

---

## 📈 Monitoring & Analytics

### Built-in Metrics

- **📞 Call Volume** - Voice booking statistics
- **⏱️ Response Times** - API performance monitoring
- **❌ Error Rates** - System health tracking
- **👥 User Activity** - Booking patterns and trends
- **🎯 Success Rates** - Voice recognition accuracy

### Alerting

- **🚨 Error Alerts** - Immediate notification for failures
- **📊 Performance Alerts** - Threshold-based monitoring
- **📞 Voice System Alerts** - Twilio integration monitoring

---

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Development Workflow

1. **🍴 Fork** the repository
2. **🌿 Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **✨ Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **🚀 Push** to the branch (`git push origin feature/amazing-feature`)
5. **📝 Open** a Pull Request

### Code Standards

- **Python**: Follow PEP 8 with Black formatting
- **API**: RESTful design with OpenAPI documentation
- **Testing**: Minimum 80% code coverage
- **Documentation**: Comprehensive docstrings and README updates

---

## 📋 Changelog

### v3.0.0 (Latest)
- ✨ Complete rewrite with modern FastAPI architecture
- 🎤 Enhanced Canadian voice processing
- 📊 Professional admin dashboard with Bootstrap 5
- 🔒 Stateless session authentication
- ☁️ AWS ECS production deployment
- 🤖 Advanced AI extraction with artifact filtering

### v2.0.0
- 🎯 Basic voice booking system
- 📱 Simple web interface
- 🗄️ SQLite database

### v1.0.0
- 📞 Initial Twilio integration
- 📅 Basic appointment management

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **🎤 Twilio** - Voice infrastructure and Canadian English optimization
- **🤖 OpenAI** - Advanced natural language processing capabilities
- **🎨 Bootstrap** - Modern UI framework and design system
- **☁️ AWS** - Reliable cloud infrastructure and deployment
- **🇨🇦 Canadian NLP Libraries** - Specialized language processing tools

---

<div align="center">

**Built with ❤️ for Canadian Dental Practices**

[![Made with Python](https://img.shields.io/badge/Made%20with-Python-3776ab?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Powered by AI](https://img.shields.io/badge/Powered%20by-AI-00a86b?style=flat-square&logo=openai&logoColor=white)](https://openai.com)
[![Deployed on AWS](https://img.shields.io/badge/Deployed%20on-AWS-ff9900?style=flat-square&logo=amazon-aws&logoColor=white)](https://aws.amazon.com)

[⭐ Star this repo](https://github.com/antarpreetsinghk/bella_v3) if you find it helpful!

</div>
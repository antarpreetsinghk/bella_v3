# SYSTEM ARCHITECTURE - Bella V3

## Overview
Comprehensive system design documentation for the Canadian voice appointment booking system.

## 🏗️ HIGH-LEVEL ARCHITECTURE

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Twilio Voice  │    │   Application   │    │   Data Layer    │
│                 │    │   Load Balancer │    │                 │
│ +1 438 256 5719 │◄───┤      (ALB)      ├───►│  PostgreSQL RDS │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   ECS Fargate   │
                       │                 │
                       │ ┌─────────────┐ │
                       │ │  FastAPI    │ │
                       │ │ Application │ │
                       │ └─────────────┘ │
                       └─────────────────┘
                                │
                       ┌─────────────────┐
                       │ Redis (Upstash) │
                       │ Session Storage │
                       └─────────────────┘
```

## 🔄 CONVERSATION FLOW ARCHITECTURE

### State Machine Design
```
┌─────────────┐    extract_name()     ┌─────────────┐
│  ask_name   ├───────────────────────┤ ask_mobile  │
└─────────────┘                       └─────────────┘
                                            │
                                            │ extract_phone()
                                            ▼
┌─────────────┐    book_appointment() ┌─────────────┐
│   confirm   ◄───────────────────────┤  ask_time   │
└─────────────┘                       └─────────────┘
                                            │
                                            │ extract_time()
                                            │ validate_hours()
                                            ▼
                                      ┌─────────────┐
                                      │  ask_time   │
                                      │ (retry if   │
                                      │ invalid)    │
                                      └─────────────┘
```

### Session State Management
```python
class ConversationState:
    current_step: str         # ask_name, ask_mobile, ask_time, confirm
    data: dict               # Extracted information
    duration_min: int        # Appointment duration (default: 30)
    full_name: str          # Extracted name
    mobile: str             # Extracted phone (E.164 format)
    starts_at_utc: datetime # Extracted and validated time
    created_at: datetime    # Session creation timestamp
    ttl: int               # Time to live (15 minutes)
```

## 🏢 INFRASTRUCTURE COMPONENTS

### AWS ECS Fargate
```yaml
Cluster: bella-prod-cluster
Service: bella-prod-service
Task Definition: bella-prod:22
CPU: 256 (.25 vCPU)
Memory: 512 MB
Networking: awsvpc mode
Public IP: Enabled
Auto Scaling: Min 1, Max 3
Health Check: /healthz endpoint
```

### Application Load Balancer
```yaml
Name: bella-alb
DNS: bella-alb-1924818779.ca-central-1.elb.amazonaws.com
Scheme: Internet-facing
IP Address Type: IPv4
Availability Zones: ca-central-1a, ca-central-1b
Target Group: bella-tg
Health Check: /healthz (HTTP 200)
```

### Database Layer
```yaml
Engine: PostgreSQL 15
Instance: db.t4g.micro
Storage: 20 GB gp2
Multi-AZ: No (cost optimization)
Backup: 7 days retention
Security Groups: ECS access only
```

### Session Storage
```yaml
Provider: Upstash Redis
Tier: Free (10,000 requests/day)
Region: us-east-1
SSL: Required
Persistence: In-memory fallback
TTL: 15 minutes per session
```

## 🎯 APPLICATION ARCHITECTURE

### FastAPI Application Structure
```
app/
├── main.py                 # Application entry point
├── api/
│   └── routes/
│       ├── twilio.py      # Webhook endpoints
│       ├── appointments.py # Appointment CRUD
│       ├── users.py       # User management
│       └── home.py        # Static pages
├── core/
│   ├── config.py          # Environment configuration
│   ├── business.py        # Business hours logic
│   ├── logging.py         # Structured logging
│   ├── errors.py          # Error handling
│   └── metrics.py         # Performance metrics
├── services/
│   ├── canadian_extraction.py  # Voice processing
│   ├── redis_session.py   # Session management
│   ├── booking.py         # Appointment logic
│   └── llm.py             # OpenAI integration
├── db/
│   ├── models/            # SQLAlchemy models
│   ├── session.py         # Database connection
│   └── base.py            # Base configuration
└── schemas/               # Pydantic validation
    ├── user.py
    ├── appointment.py
    └── assistant.py
```

### Key Components

#### 1. Twilio Integration (`app/api/routes/twilio.py`)
```python
@router.post("/voice")
async def voice_webhook():
    # Initial call handling
    # Returns TwiML for name collection

@router.post("/voice/collect")
async def voice_collect():
    # Process speech input
    # Extract information based on current step
    # Update session state
    # Return next TwiML response
```

#### 2. Canadian Extraction (`app/services/canadian_extraction.py`)
```python
async def extract_canadian_phone(speech: str) -> Optional[str]:
    # Layer 1: Direct phonenumbers parsing
    # Layer 2: Enhanced digit extraction + spelled-out
    # Layer 3: LLM fallback
    # Returns: E.164 format (+14165551234)

async def extract_canadian_time(speech: str) -> Optional[datetime]:
    # Preprocessing: Complex phrase handling
    # Layer 1: parsedatetime (Canadian English)
    # Layer 2: dateutil parser
    # Layer 3: LLM fallback
    # Returns: UTC datetime

async def extract_canadian_name(speech: str) -> Optional[str]:
    # Enhanced regex patterns
    # spaCy NER with timeout protection
    # LLM fallback
    # Returns: "First Last" format
```

#### 3. Session Management (`app/services/redis_session.py`)
```python
async def get_session(call_sid: str) -> ConversationState:
    # Try Redis first, fallback to in-memory
    # Create new session if not found

async def save_session(session: ConversationState):
    # Save to Redis with TTL
    # Fallback to in-memory storage

async def reset_session(call_sid: str):
    # Clear session from Redis and memory
```

#### 4. Business Hours (`app/core/business.py`)
```python
def is_within_hours(dt_local: datetime) -> bool:
    # Monday-Friday 9:00 AM - 5:00 PM (Edmonton)
    # Returns: True if within business hours

def next_opening(after_local: datetime) -> datetime:
    # Calculate next available business hour
    # Up to 2 weeks lookahead
```

## 🔌 EXTERNAL INTEGRATIONS

### Twilio Voice API
```yaml
Account SID: [Secrets Manager]
Auth Token: [Secrets Manager]
Phone Number: +1 438 256 5719
Webhooks:
  - Voice: /twilio/voice
  - Collect: /twilio/voice/collect
Voice Settings:
  - voice: "alice"
  - language: "en-CA"
  - enhanced: true
  - speechTimeout: 3
  - timeout: 6
```

### OpenAI Integration
```yaml
Model: gpt-4o-mini
API Key: [Secrets Manager]
Usage: LLM fallback for complex extractions
Rate Limits: Standard tier
Context: Minimal, extraction-focused prompts
```

### Redis (Upstash)
```yaml
Connection: SSL required
URL: [Secrets Manager]
Usage: ~1,000 operations/day
Limit: 10,000 requests/day (free tier)
Fallback: In-memory dictionary
```

## 🚀 CI/CD PIPELINE ARCHITECTURE

### GitHub Actions Workflow
```yaml
Triggers:
  - Push to main branch
  - Pull request to main

Jobs:
  1. unit-tests:
     - Python 3.11 setup
     - Install dependencies
     - Run pytest (if tests exist)

  2. compose-smoke:
     - Docker Buildx setup
     - Build containers
     - Start services (API + PostgreSQL)
     - Health check validation

  3. deploy-aws:
     - Configure AWS credentials
     - Build and push to ECR
     - Update ECS task definition
     - Deploy to ECS service
     - Validate deployment health
```

### Container Build Process
```dockerfile
# Multi-stage build
FROM python:3.11-slim as builder
# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim as runtime
# Copy application and dependencies
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY app/ /app/
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 📊 DATA ARCHITECTURE

### Database Schema
```sql
-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(255) NOT NULL,
    mobile VARCHAR(20) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Appointments table
CREATE TABLE appointments (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    starts_at_utc TIMESTAMP WITH TIME ZONE NOT NULL,
    duration_minutes INTEGER DEFAULT 30,
    status VARCHAR(50) DEFAULT 'scheduled',
    call_sid VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Session Data Structure
```json
{
  "call_sid": "CA1234567890",
  "current_step": "ask_mobile",
  "data": {
    "duration_min": 30,
    "full_name": "John Smith"
  },
  "created_at": "2025-09-27T20:00:00Z",
  "ttl": 900
}
```

## 🔒 SECURITY ARCHITECTURE

### Network Security
```yaml
VPC: Default VPC (ca-central-1)
Security Groups:
  - ECS Tasks: HTTP 8000 from ALB
  - ALB: HTTP 80/443 from Internet
  - RDS: PostgreSQL 5432 from ECS
Secrets: AWS Secrets Manager
SSL/TLS: ALB termination
```

### Application Security
```yaml
Authentication: None (public voice interface)
Input Validation: Pydantic schemas
Secrets: Environment variables from Secrets Manager
Logging: Structured with sanitized PII
Error Handling: Generic error responses
```

## 📈 PERFORMANCE CHARACTERISTICS

### Response Time Targets
```yaml
Health Check: < 100ms
Voice Webhook: < 2 seconds
Name Extraction: < 1 second
Phone Extraction: < 1 second
Time Extraction: < 2 seconds
Database Operations: < 500ms
```

### Scalability Design
```yaml
Auto Scaling: ECS service (1-3 tasks)
Database: Vertical scaling ready
Session Storage: Redis clustering ready
CDN: CloudFront ready
Load Balancing: ALB with multiple AZs
```

### Resource Utilization
```yaml
CPU: ~10-20% average per task
Memory: ~200-300 MB average per task
Database Connections: 1-2 per task
Redis Connections: 1 per task
```

## 🔧 EXTENSIBILITY POINTS

### Adding New Extraction Types
1. Create extraction function in `canadian_extraction.py`
2. Add to conversation state schema
3. Update conversation flow logic
4. Add test cases

### Multi-Language Support
1. Duplicate extraction services
2. Language detection in webhook
3. Route to appropriate extractor
4. Update TwiML voice settings

### Advanced Scheduling
1. Extend business hours logic
2. Add calendar integration
3. Implement conflict detection
4. Add rescheduling capabilities

---
*Last Updated: 2025-09-27*
*Version: 1.0*
*Architecture Status: Production Ready*
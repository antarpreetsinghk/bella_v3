# 🏗️ BELLA V3 - COMPLETE ARCHITECTURE DESIGN

## 📋 Executive Summary
Comprehensive architecture for a cost-optimized, scalable voice appointment booking system with optimal user experience and minimal operational overhead.

## 🎯 System Architecture Overview

### Core Principles
- **Cost-First Design**: Every component optimized for minimal AWS costs
- **User Experience First**: Sub-3-second call responses, 90%+ success rate
- **Operational Simplicity**: Minimal moving parts, easy debugging
- **Security by Design**: Zero-trust, encrypted everything
- **Scalability Ready**: Handle 1K-100K calls/month with same architecture

### Technology Stack
```
Frontend:     FastAPI + Jinja2 Templates (Admin Dashboard)
Backend:      FastAPI + AsyncIO + Pydantic
Database:     PostgreSQL (AWS RDS)
Cache/Session: Redis (AWS ElastiCache)
Voice/SMS:    Twilio
Speech:       OpenAI Whisper
Hosting:      AWS ECS Fargate
CI/CD:        GitHub Actions
Monitoring:   AWS CloudWatch + Custom Metrics
```

## 💻 Development Environment

### Local Setup
```bash
# 1. Repository Structure
bella_v3/
├── app/
│   ├── api/routes/         # API endpoints
│   ├── core/              # Configuration, security
│   ├── db/                # Database models, migrations
│   ├── services/          # Business logic
│   └── schemas/           # Pydantic models
├── tests/
│   ├── unit/              # Fast unit tests
│   ├── integration/       # API integration tests
│   └── load/              # Performance tests
├── deploy/
│   ├── docker/            # Multi-stage Dockerfiles
│   ├── terraform/         # Infrastructure as Code
│   └── scripts/           # Deployment helpers
├── docs/                  # Architecture, API docs
└── .github/workflows/     # CI/CD pipelines

# 2. Development Dependencies
- Python 3.11+ (performance optimized)
- Docker & Docker Compose (local services)
- Pre-commit hooks (code quality)
- pytest (testing framework)
- Redis local instance (session testing)
```

### Docker Development Setup
```dockerfile
# Dockerfile.dev - Fast development iteration
FROM python:3.11-slim
WORKDIR /app
COPY requirements-dev.txt .
RUN pip install -r requirements-dev.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0"]
```

```yaml
# docker-compose.dev.yml - Complete local environment
version: '3.8'
services:
  app:
    build:
      context: .
      dockerfile: Dockerfile.dev
    ports: ["8000:8000"]
    environment:
      - DATABASE_URL=postgresql://postgres:dev@postgres:5432/bella_dev
      - REDIS_URL=redis://redis:6379
      - ENVIRONMENT=development
    volumes: [".:/app"]
    depends_on: [postgres, redis]

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: bella_dev
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: dev
    ports: ["5432:5432"]
    volumes: ["postgres_data:/var/lib/postgresql/data"]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    command: redis-server --appendonly yes
    volumes: ["redis_data:/data"]

  # Twilio webhook tunnel for local testing
  ngrok:
    image: ngrok/ngrok:latest
    command: http app:8000
    environment:
      - NGROK_AUTHTOKEN=${NGROK_TOKEN}
    depends_on: [app]

volumes:
  postgres_data:
  redis_data:
```

## 🚀 Production Infrastructure

### AWS Services Selection (Cost-Optimized)
```
Core Services:
├── ECS Fargate (1 task, 0.5 vCPU, 1GB RAM)     ~$15/month
├── RDS PostgreSQL (t3.micro, 20GB)             ~$20/month
├── ElastiCache Redis (t3.micro)                ~$15/month
├── Application Load Balancer                   ~$20/month
├── Route 53 (hosted zone + queries)            ~$5/month
├── Secrets Manager (3 secrets)                 ~$3/month
├── CloudWatch (logs + metrics)                 ~$10/month
└── Data Transfer (minimal)                     ~$5/month

Total Fixed Infrastructure: ~$93/month
Variable Costs: Twilio + OpenAI (usage-based)
```

### Infrastructure as Code
```hcl
# terraform/main.tf - Complete infrastructure
terraform {
  backend "s3" {
    bucket = "bella-terraform-state"
    key    = "prod/terraform.tfstate"
    region = "ca-central-1"
  }
}

# VPC with public/private subnets
module "vpc" {
  source = "./modules/vpc"
  environment = var.environment
  availability_zones = ["ca-central-1a", "ca-central-1b"]
}

# ECS Cluster with Fargate
module "ecs" {
  source = "./modules/ecs"
  environment = var.environment
  vpc_id = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnet_ids
  target_group_arn = module.alb.target_group_arn
}

# Database with automated backups
module "database" {
  source = "./modules/rds"
  environment = var.environment
  vpc_id = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnet_ids
  backup_retention_period = 7
  deletion_protection = true
}

# Redis for session management
module "redis" {
  source = "./modules/elasticache"
  environment = var.environment
  vpc_id = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnet_ids
}
```

### Auto-Scaling Configuration
```json
{
  "service_name": "bella-prod-service",
  "auto_scaling": {
    "min_capacity": 1,
    "max_capacity": 5,
    "target_cpu_utilization": 70,
    "target_memory_utilization": 80,
    "scale_up_cooldown": "300s",
    "scale_down_cooldown": "900s"
  },
  "health_check": {
    "path": "/healthz",
    "interval": 30,
    "timeout": 5,
    "healthy_threshold": 2,
    "unhealthy_threshold": 3
  }
}
```

## 🔄 CI/CD Pipeline Optimization

### GitHub Actions Workflow
```yaml
# .github/workflows/ci-cd.yml
name: CI/CD Pipeline
on:
  push: { branches: [main, develop] }
  pull_request: { branches: [main] }

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test
          POSTGRES_DB: bella_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with: { python-version: '3.11' }
      - name: Install dependencies
        run: |
          pip install --upgrade pip
          pip install -r requirements.txt
          pip install -r requirements-test.txt
      - name: Run tests
        run: |
          pytest tests/ --cov=app --cov-report=xml
          pytest tests/load/ --tb=short
      - name: Security scan
        run: |
          bandit -r app/ -f json -o security-report.json
          safety check --json --output safety-report.json

  build:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v3
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ca-central-1
      - name: Build and push Docker image
        run: |
          # Multi-stage build for production optimization
          docker build -f Dockerfile.prod -t bella-app:${{ github.sha }} .
          aws ecr get-login-password | docker login --username AWS --password-stdin $ECR_URI
          docker tag bella-app:${{ github.sha }} $ECR_URI/bella-app:${{ github.sha }}
          docker push $ECR_URI/bella-app:${{ github.sha }}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to ECS
        run: |
          # Zero-downtime deployment
          aws ecs update-service \
            --cluster bella-prod-cluster \
            --service bella-prod-service \
            --task-definition bella-prod:$(aws ecs describe-task-definition \
              --task-definition bella-prod \
              --query 'taskDefinition.revision + 1')

          # Wait for deployment
          aws ecs wait services-stable \
            --cluster bella-prod-cluster \
            --services bella-prod-service
      - name: Run smoke tests
        run: |
          curl -f https://bella.yourdomain.com/healthz
          curl -f -X POST https://bella.yourdomain.com/twilio/voice \
            -d "CallSid=HEALTH_CHECK" -d "From=+15551234567"
```

### Production Dockerfile (Optimized)
```dockerfile
# Dockerfile.prod - Multi-stage production build
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.11-slim as runtime
RUN adduser --disabled-password --gecos '' appuser
WORKDIR /app
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Install only production dependencies
COPY app/ ./app/
COPY alembic.ini .
COPY alembic/ ./alembic/

# Pre-download ML models to avoid runtime delays
RUN python -c "
import spacy
spacy.cli.download('en_core_web_sm')
"

USER appuser
EXPOSE 8000

# Production server with optimized settings
CMD ["uvicorn", "app.main:app",
     "--host", "0.0.0.0",
     "--port", "8000",
     "--workers", "2",
     "--access-log",
     "--log-config", "logging.yaml"]
```

## 🧪 Testing Strategy

### Test Pyramid
```
           ┌─────────────────┐
           │   E2E Tests     │ ← 5% (Critical user journeys)
           │ (Voice Calls)   │
           └─────────────────┘
          ┌─────────────────────┐
          │ Integration Tests   │ ← 25% (API contracts, DB)
          │   (API Testing)     │
          └─────────────────────┘
         ┌─────────────────────────┐
         │     Unit Tests          │ ← 70% (Business logic)
         │ (Services, Models)      │
         └─────────────────────────┘
```

### Test Implementation
```python
# tests/unit/test_extractors.py
import pytest
from app.services.canadian_extraction import extract_canadian_phone

@pytest.mark.asyncio
async def test_phone_extraction():
    """Test phone number extraction accuracy"""
    test_cases = [
        ("My number is 416-555-1234", "+14165551234"),
        ("Call me at four one six five five five one two three four", "+14165551234"),
        ("416 555 1234", "+14165551234"),
        ("invalid phone", None),
    ]

    for input_text, expected in test_cases:
        result = await extract_canadian_phone(input_text)
        assert result == expected

# tests/integration/test_voice_flow.py
@pytest.mark.asyncio
async def test_complete_call_flow(test_client):
    """Test complete appointment booking flow"""
    # Step 1: Initial call
    response = await test_client.post("/twilio/voice", data={
        "CallSid": "test_call_123",
        "From": "+14165551234"
    })
    assert response.status_code == 200
    assert "What's your name?" in response.text

    # Step 2: Name collection
    response = await test_client.post("/twilio/voice/collect", data={
        "CallSid": "test_call_123",
        "SpeechResult": "John Smith",
        "From": "+14165551234"
    })
    assert "I have your number as" in response.text

    # Step 3: Time collection
    response = await test_client.post("/twilio/voice/collect", data={
        "CallSid": "test_call_123",
        "SpeechResult": "next Tuesday at 2 PM"
    })
    assert "confirm" in response.text.lower()

# tests/load/test_performance.py
import asyncio
import aiohttp
import time

async def test_concurrent_calls():
    """Test system under load"""
    async def make_call(session, call_id):
        start_time = time.time()
        async with session.post(
            "http://localhost:8000/twilio/voice",
            data={"CallSid": f"load_test_{call_id}", "From": "+15551234567"}
        ) as response:
            duration = time.time() - start_time
            return response.status, duration

    async with aiohttp.ClientSession() as session:
        tasks = [make_call(session, i) for i in range(50)]
        results = await asyncio.gather(*tasks)

    # Assertions
    success_rate = sum(1 for status, _ in results if status == 200) / len(results)
    avg_response_time = sum(duration for _, duration in results) / len(results)

    assert success_rate >= 0.95  # 95% success rate
    assert avg_response_time < 3.0  # Sub-3 second responses
```

### Voice Call Testing
```python
# tests/voice/test_twilio_integration.py
from twilio.rest import Client
import pytest

@pytest.mark.integration
def test_real_voice_call():
    """Test actual Twilio call (run manually or in staging)"""
    client = Client(TWILIO_SID, TWILIO_TOKEN)

    # Make actual call to staging environment
    call = client.calls.create(
        to=TEST_PHONE_NUMBER,
        from_=TWILIO_PHONE_NUMBER,
        url="https://staging.bella.com/twilio/voice",
        timeout=30
    )

    # Wait for call completion
    while call.status in ['queued', 'ringing', 'in-progress']:
        time.sleep(2)
        call = client.calls(call.sid).fetch()

    assert call.status == 'completed'
    assert call.duration is not None
```

## 🔒 Security Implementation

### Authentication & Authorization
```python
# app/core/security.py
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets
import hmac
import hashlib

# Basic Auth for admin dashboard
security = HTTPBasic()

async def verify_admin(credentials: HTTPBasicCredentials = Depends(security)):
    """Secure admin authentication"""
    correct_username = secrets.compare_digest(credentials.username, ADMIN_USER)
    correct_password = secrets.compare_digest(credentials.password, ADMIN_PASSWORD)

    if not (correct_username and correct_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return credentials

# Twilio webhook signature verification
def verify_twilio_signature(request: Request, body: bytes) -> bool:
    """Verify Twilio webhook authenticity"""
    signature = request.headers.get('X-Twilio-Signature', '')
    expected = base64.b64encode(
        hmac.new(
            TWILIO_AUTH_TOKEN.encode('utf-8'),
            (str(request.url) + body.decode()).encode('utf-8'),
            hashlib.sha1
        ).digest()
    ).decode()
    return secrets.compare_digest(signature, expected)

# API Key validation for external access
async def verify_api_key(api_key: str = Header(...)):
    """Validate API key for external integrations"""
    if not secrets.compare_digest(api_key, BELLA_API_KEY):
        raise HTTPException(status_code=401, detail="Invalid API key")
    return api_key
```

### Data Protection
```python
# app/core/encryption.py
from cryptography.fernet import Fernet
import os

class DataEncryption:
    """Encrypt sensitive data at rest"""

    def __init__(self):
        self.cipher = Fernet(os.getenv("ENCRYPTION_KEY").encode())

    def encrypt_pii(self, data: str) -> str:
        """Encrypt personally identifiable information"""
        return self.cipher.encrypt(data.encode()).decode()

    def decrypt_pii(self, encrypted_data: str) -> str:
        """Decrypt PII for processing"""
        return self.cipher.decrypt(encrypted_data.encode()).decode()

# Database model with encryption
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    full_name_encrypted = Column(String)  # Encrypted PII
    mobile_encrypted = Column(String)     # Encrypted PII
    created_at = Column(DateTime, default=datetime.utcnow)

    @property
    def full_name(self) -> str:
        return encryption.decrypt_pii(self.full_name_encrypted)

    @full_name.setter
    def full_name(self, value: str):
        self.full_name_encrypted = encryption.encrypt_pii(value)
```

### Compliance & Privacy
```python
# app/core/compliance.py
from datetime import datetime, timedelta

class GDPRCompliance:
    """GDPR/Privacy compliance features"""

    @staticmethod
    async def auto_delete_old_data():
        """Auto-delete data older than retention period"""
        cutoff_date = datetime.utcnow() - timedelta(days=365)  # 1 year retention

        async with get_session() as db:
            # Delete old call recordings
            await db.execute(
                delete(CallRecording).where(CallRecording.created_at < cutoff_date)
            )

            # Anonymize old user data
            old_users = await db.execute(
                select(User).where(User.last_activity < cutoff_date)
            )

            for user in old_users.scalars():
                user.full_name = "ANONYMIZED"
                user.mobile = "ANONYMIZED"
                user.notes = "DATA_PURGED"

            await db.commit()

    @staticmethod
    async def export_user_data(mobile: str) -> dict:
        """Export all user data (GDPR Article 20)"""
        async with get_session() as db:
            user = await get_user_by_mobile(db, mobile)
            if not user:
                return {}

            appointments = await db.execute(
                select(Appointment).where(Appointment.user_id == user.id)
            )

            return {
                "personal_data": {
                    "name": user.full_name,
                    "mobile": user.mobile,
                    "created": user.created_at.isoformat()
                },
                "appointments": [
                    {
                        "date": apt.starts_at.isoformat(),
                        "duration": apt.duration_min,
                        "status": apt.status
                    } for apt in appointments.scalars()
                ]
            }
```

## 💰 Cost Optimization Strategy

### Cost Monitoring
```python
# app/core/cost_monitoring.py
import boto3
from datetime import datetime, timedelta

class CostMonitor:
    """Monitor and optimize AWS costs"""

    def __init__(self):
        self.ce_client = boto3.client('ce')  # Cost Explorer
        self.cloudwatch = boto3.client('cloudwatch')

    async def get_monthly_costs(self) -> dict:
        """Get current month AWS costs by service"""
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now().replace(day=1)).strftime('%Y-%m-%d')

        response = self.ce_client.get_cost_and_usage(
            TimePeriod={'Start': start_date, 'End': end_date},
            Granularity='MONTHLY',
            Metrics=['UnblendedCost'],
            GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
        )

        costs = {}
        for result in response['ResultsByTime']:
            for group in result['Groups']:
                service = group['Keys'][0]
                cost = float(group['Metrics']['UnblendedCost']['Amount'])
                costs[service] = cost

        return costs

    async def optimize_ecs_scaling(self):
        """Auto-optimize ECS scaling based on usage"""
        # Get CPU/Memory utilization over past week
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=7)

        cpu_metrics = self.cloudwatch.get_metric_statistics(
            Namespace='AWS/ECS',
            MetricName='CPUUtilization',
            Dimensions=[
                {'Name': 'ServiceName', 'Value': 'bella-prod-service'},
                {'Name': 'ClusterName', 'Value': 'bella-prod-cluster'}
            ],
            StartTime=start_time,
            EndTime=end_time,
            Period=3600,  # 1 hour intervals
            Statistics=['Average']
        )

        avg_cpu = sum(dp['Average'] for dp in cpu_metrics['Datapoints']) / len(cpu_metrics['Datapoints'])

        # If CPU consistently low, recommend downsizing
        if avg_cpu < 25:
            logger.warning(f"ECS CPU utilization low ({avg_cpu:.1f}%) - consider downsizing")

        # If CPU consistently high, recommend scaling up
        elif avg_cpu > 80:
            logger.warning(f"ECS CPU utilization high ({avg_cpu:.1f}%) - consider scaling up")

# Cost alerts
async def setup_cost_alerts():
    """Setup CloudWatch alarms for cost overruns"""
    cloudwatch = boto3.client('cloudwatch')

    # Alert if monthly costs exceed $150
    cloudwatch.put_metric_alarm(
        AlarmName='BellaMonthlyCostAlert',
        ComparisonOperator='GreaterThanThreshold',
        EvaluationPeriods=1,
        MetricName='EstimatedCharges',
        Namespace='AWS/Billing',
        Period=86400,  # Daily
        Statistic='Maximum',
        Threshold=150.0,
        ActionsEnabled=True,
        AlarmActions=[SNS_TOPIC_ARN],
        AlarmDescription='Alert when Bella monthly costs exceed $150',
        Dimensions=[{'Name': 'Currency', 'Value': 'USD'}]
    )
```

### Resource Optimization
```yaml
# Cost optimization configuration
cost_optimization:
  ecs:
    # Use spot instances for dev/staging
    spot_instances: true  # 70% cost reduction for non-prod

    # Right-size production
    production:
      cpu: 512      # 0.5 vCPU (was 1024)
      memory: 1024  # 1GB RAM (was 2048)

  rds:
    # Use smaller instance for development
    development:
      instance_type: "db.t3.micro"
      allocated_storage: 10
    production:
      instance_type: "db.t3.micro"  # Start small, scale up
      allocated_storage: 20
      backup_retention_period: 7

  redis:
    # Single-node Redis for cost savings
    node_type: "cache.t3.micro"
    num_cache_nodes: 1

  # Auto-shutdown non-production environments
  auto_shutdown:
    development:
      shutdown_time: "20:00"  # 8 PM
      startup_time: "08:00"   # 8 AM
      timezone: "America/Toronto"
```

## 📞 Optimal Call Flow Design

### User Experience Journey
```
┌─────────────────────────────────────────────────────────────────┐
│                     OPTIMAL CALL FLOW                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  📞 User Dials → 🎤 "Hi! I'll help book your appointment.      │
│                      What's your name?"                        │
│                                                                 │
│  👤 "John Smith" → 🎤 "Perfect! I have your number as          │
│                        416-555-1234. When would you like      │
│                        your appointment?"                      │
│                                                                 │
│  📅 "Tomorrow 2PM" → 🎤 "Great! I'll book John Smith for       │
│                          Tuesday March 12th at 2:00 PM.       │
│                          Should I confirm this?"               │
│                                                                 │
│  ✅ "Yes" → 🎤 "Perfect! Your appointment is booked.           │
│               You'll receive a text confirmation.             │
│               Thank you!"                                       │
│                                                                 │
│  📱 SMS: "✅ Appointment confirmed: Tue Mar 12, 2:00 PM"      │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  🎯 Target Metrics:                                            │
│  • Call Duration: 45-90 seconds                                │
│  • Success Rate: 95%+                                          │
│  • Response Time: <2 seconds per step                         │
│  • Customer Satisfaction: 4.5+ stars                         │
└─────────────────────────────────────────────────────────────────┘
```

### Performance-Optimized Implementation
```python
# app/services/optimized_call_flow.py
from datetime import datetime
import asyncio

class OptimizedCallFlow:
    """Performance-optimized call processing"""

    def __init__(self):
        self.response_cache = {}  # Cache TwiML responses
        self.session_timeout = 300  # 5 minutes

    async def process_call_step(self, call_sid: str, step: str, input_data: dict) -> str:
        """Process call step with sub-2-second response"""
        start_time = datetime.utcnow()

        try:
            # Get session (with Redis fallback to in-memory)
            session = await self.get_session_fast(call_sid)

            # Process based on current step
            if step == "initial":
                response = await self.handle_initial_call(session, input_data)
            elif step == "name_collection":
                response = await self.handle_name_collection(session, input_data)
            elif step == "time_collection":
                response = await self.handle_time_collection(session, input_data)
            elif step == "confirmation":
                response = await self.handle_confirmation(session, input_data)
            else:
                response = await self.handle_error(session, "Unknown step")

            # Log performance
            duration = (datetime.utcnow() - start_time).total_seconds()
            if duration > 2.0:
                logger.warning(f"Slow response: {duration:.2f}s for step {step}")

            return response

        except Exception as e:
            logger.error(f"Call processing error: {e}")
            return self.generate_error_response()

    async def get_session_fast(self, call_sid: str) -> CallSession:
        """Get session with intelligent caching"""
        # Try memory cache first
        if call_sid in self.session_cache:
            return self.session_cache[call_sid]

        # Try Redis (with timeout)
        try:
            redis_session = await asyncio.wait_for(
                self.get_redis_session(call_sid),
                timeout=0.5  # 500ms timeout
            )
            if redis_session:
                self.session_cache[call_sid] = redis_session
                return redis_session
        except asyncio.TimeoutError:
            logger.warning(f"Redis timeout for session {call_sid}")

        # Fallback to new session
        new_session = CallSession(call_sid=call_sid)
        self.session_cache[call_sid] = new_session
        return new_session

    def generate_twiml_response(self, message: str, next_step: str = None) -> str:
        """Generate optimized TwiML response"""
        # Use cached responses for common phrases
        cache_key = f"{message}:{next_step}"
        if cache_key in self.response_cache:
            return self.response_cache[cache_key]

        if next_step:
            twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Gather input="speech"
          language="en-CA"
          method="POST"
          action="/twilio/voice/collect"
          speechTimeout="4"
          timeout="8"
          enhanced="true">
    <Say voice="alice" language="en-CA">{message}</Say>
  </Gather>
  <Say voice="alice">I didn't catch that. Let me transfer you to our office.</Say>
  <Dial>+1-416-555-0199</Dial>
</Response>'''
        else:
            twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="alice" language="en-CA">{message}</Say>
</Response>'''

        # Cache common responses
        self.response_cache[cache_key] = twiml
        return twiml
```

### Error Handling & Recovery
```python
# app/services/error_recovery.py
class ErrorRecoverySystem:
    """Intelligent error handling and recovery"""

    async def handle_speech_recognition_failure(self, session: CallSession, attempt: int):
        """Handle speech recognition failures gracefully"""
        if attempt == 1:
            return "I didn't catch that. Could you please repeat?"
        elif attempt == 2:
            return "I'm having trouble understanding. Could you speak slowly and clearly?"
        else:
            return "I'm having technical difficulties. Let me connect you to our office."

    async def handle_timeout_recovery(self, session: CallSession):
        """Recover from system timeouts"""
        # Resume from last known good state
        if session.data.get("full_name"):
            return f"Hi {session.data['full_name']}, I'm back. When would you like your appointment?"
        else:
            return "I apologize for the interruption. Let's start over. What's your name?"

    async def handle_database_failure(self, session: CallSession):
        """Handle database connectivity issues"""
        # Store in Redis temporarily
        await self.store_temp_booking(session)
        return "Your appointment is being processed. You'll receive a confirmation text shortly."

    async def store_temp_booking(self, session: CallSession):
        """Store booking temporarily when database is unavailable"""
        redis_client = get_redis_client()
        if redis_client:
            booking_data = {
                "name": session.data.get("full_name"),
                "mobile": session.data.get("mobile"),
                "requested_time": session.data.get("requested_time"),
                "timestamp": datetime.utcnow().isoformat()
            }
            redis_client.setex(
                f"temp_booking:{session.call_sid}",
                3600,  # 1 hour
                json.dumps(booking_data)
            )
```

## 📊 Monitoring & Observability

### Custom Metrics Dashboard
```python
# app/core/metrics.py
from datadog import initialize, statsd
import time

class BellaMetrics:
    """Custom application metrics"""

    def __init__(self):
        initialize(api_key=DATADOG_API_KEY, app_key=DATADOG_APP_KEY)

    def track_call_metrics(self, call_sid: str, duration: float, success: bool, step: str):
        """Track call performance metrics"""
        tags = [
            f"success:{success}",
            f"step:{step}",
            f"environment:{ENVIRONMENT}"
        ]

        # Response time
        statsd.histogram('bella.call.response_time', duration, tags=tags)

        # Success rate
        statsd.increment('bella.call.attempts', tags=tags)
        if success:
            statsd.increment('bella.call.success', tags=tags)
        else:
            statsd.increment('bella.call.failure', tags=tags)

    def track_cost_metrics(self, service: str, cost: float):
        """Track cost metrics"""
        statsd.gauge(f'bella.cost.{service}', cost, tags=[f"environment:{ENVIRONMENT}"])

    def track_business_metrics(self, appointments_booked: int, revenue: float):
        """Track business KPIs"""
        statsd.increment('bella.business.appointments', appointments_booked)
        statsd.gauge('bella.business.revenue', revenue)

# CloudWatch custom metrics
class CloudWatchMetrics:
    def __init__(self):
        self.cloudwatch = boto3.client('cloudwatch')

    def put_call_quality_metric(self, success_rate: float):
        """Track call success rate"""
        self.cloudwatch.put_metric_data(
            Namespace='Bella/Voice',
            MetricData=[{
                'MetricName': 'CallSuccessRate',
                'Value': success_rate,
                'Unit': 'Percent',
                'Timestamp': datetime.utcnow()
            }]
        )
```

### Alerting Configuration
```yaml
# monitoring/alerts.yml
alerts:
  critical:
    - name: "High Error Rate"
      condition: "error_rate > 5%"
      duration: "5m"
      action: "page_oncall"

    - name: "Response Time Degradation"
      condition: "avg_response_time > 3s"
      duration: "10m"
      action: "page_oncall"

    - name: "Service Down"
      condition: "health_check_failure"
      duration: "1m"
      action: "page_oncall"

  warning:
    - name: "Cost Spike"
      condition: "daily_cost > $15"
      duration: "1d"
      action: "notify_team"

    - name: "Low Success Rate"
      condition: "call_success_rate < 90%"
      duration: "15m"
      action: "notify_team"
```

## 🚀 Scalability & Future-Proofing

### Horizontal Scaling Strategy
```python
# Auto-scaling based on call volume
scaling_policy = {
    "metric_name": "bella.call.volume",
    "target_value": 10,  # calls per minute per instance
    "scale_up": {
        "threshold": 80,  # 80% of capacity
        "cooldown": 300,  # 5 minutes
        "max_instances": 10
    },
    "scale_down": {
        "threshold": 20,  # 20% of capacity
        "cooldown": 900,  # 15 minutes
        "min_instances": 1
    }
}
```

### Multi-Region Deployment (Future)
```
Primary Region (ca-central-1):
├── Full deployment
├── Read-write database
└── Primary traffic

Secondary Region (us-east-1):
├── Standby deployment
├── Read replica database
└── Failover traffic
```

### Feature Extensibility
```python
# Plugin architecture for future features
class FeaturePlugin:
    """Base class for feature plugins"""

    def __init__(self, name: str, version: str):
        self.name = name
        self.version = version
        self.enabled = False

    async def before_call(self, session: CallSession) -> None:
        """Hook: Before call processing"""
        pass

    async def after_call(self, session: CallSession, result: dict) -> None:
        """Hook: After call processing"""
        pass

# Example: SMS reminder plugin
class SMSReminderPlugin(FeaturePlugin):
    def __init__(self):
        super().__init__("sms_reminders", "1.0.0")

    async def after_call(self, session: CallSession, result: dict):
        if result.get("appointment_booked"):
            await self.schedule_reminder(session.data["mobile"], result["appointment_time"])

# Feature toggle management
class FeatureFlags:
    def __init__(self):
        self.flags = {
            "caller_id_optimization": True,
            "whisper_transcription": True,
            "smart_scheduling": False,  # Future feature
            "multilingual_support": False,  # Future feature
        }

    def is_enabled(self, feature: str, user_segment: str = "default") -> bool:
        return self.flags.get(feature, False)
```

---

## 📋 Implementation Roadmap

### Phase 1: Foundation (Week 1-2)
- ✅ Core infrastructure setup (AWS, ECS, RDS)
- ✅ Basic call flow implementation
- ✅ CI/CD pipeline setup
- ✅ Security baseline implementation

### Phase 2: Optimization (Week 3-4)
- 🔄 Performance optimization (current issues)
- 🔄 Redis networking fixes
- 🔄 Extractor optimization
- ⏳ Load testing and tuning

### Phase 3: Enhancement (Week 5-6)
- ⏳ Advanced error handling
- ⏳ Comprehensive monitoring
- ⏳ Cost optimization implementation
- ⏳ Documentation completion

### Phase 4: Scale Preparation (Week 7-8)
- ⏳ Multi-environment setup
- ⏳ Auto-scaling configuration
- ⏳ Disaster recovery planning
- ⏳ Performance benchmarking

---

## 💰 Total Cost Breakdown (Monthly)

### Fixed Infrastructure Costs
```
AWS Services:
├── ECS Fargate (1 task, 0.5 vCPU, 1GB)     $15/month
├── RDS PostgreSQL (t3.micro, 20GB)         $20/month
├── ElastiCache Redis (t3.micro)            $15/month
├── Application Load Balancer               $20/month
├── Route 53 + CloudWatch                   $10/month
└── Secrets Manager + misc                  $5/month
Total Fixed: $85/month

Variable Costs (per 1,000 calls):
├── Twilio Voice (avg 2 min/call)           $20/month
├── OpenAI Whisper (avg 2 min/call)         $12/month
└── Data transfer                           $3/month
Total Variable: $35/1K calls

Grand Total: $120/month for 1,000 calls
Scale Economics: $220/month for 10,000 calls
```

### Cost per Successful Booking
- **1,000 calls/month**: $0.12 per call
- **10,000 calls/month**: $0.022 per call
- **Target**: Under $0.05 per successful booking

---

This architecture delivers a production-ready, cost-optimized voice appointment booking system with enterprise-grade reliability, security, and scalability while maintaining operational simplicity and optimal user experience.
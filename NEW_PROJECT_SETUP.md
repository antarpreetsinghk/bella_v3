# Bella V3 - New Project Setup Guide

## 🔐 Authentication & Configuration Reference

### Core Environment Variables Required

```bash
# === CORE AI SERVICES ===
OPENAI_API_KEY=sk-...  # Get from: https://platform.openai.com/api-keys
OPENAI_MODEL=gpt-4o-mini
OPENAI_BASE_URL=  # Optional: custom endpoint
REQUEST_MAX_TOKENS=4000
RESPONSE_MAX_TOKENS=512

# === DATABASE ===
# Option 1: SQLite (Local Development)
DATABASE_URL=sqlite+aiosqlite:///./bella.db

# Option 2: PostgreSQL (Production)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=bella_db
POSTGRES_USER=bella_user
POSTGRES_PASSWORD=secure_password_here
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db

# === TWILIO VOICE INTEGRATION ===
TWILIO_ACCOUNT_SID=AC...  # Get from: https://console.twilio.com/
TWILIO_AUTH_TOKEN=...     # Get from: https://console.twilio.com/
TWILIO_PHONE_NUMBER=+1...  # Your Twilio phone number

# === SECURITY ===
BELLA_API_KEY=your-secure-api-key-here
ADMIN_USER=admin
ADMIN_PASS=secure_admin_password
CSRF_SECRET=random-secure-string-32-chars-min

# === REDIS (Optional - for sessions) ===
REDIS_URL=redis://localhost:6379/0

# === APPLICATION CONFIG ===
APP_ENV=development  # or production
LOG_LEVEL=INFO
LOG_REQUESTS=false
LOG_RESPONSES=false
PRODUCTION_BASE_URL=https://your-domain.com

# === GOOGLE CALENDAR INTEGRATION (Optional) ===
GOOGLE_CALENDAR_ENABLED=false
GOOGLE_SERVICE_ACCOUNT_JSON={"type": "service_account", ...}
GOOGLE_CALENDAR_ID=primary
BUSINESS_EMAIL=business@yourcompany.com

# === MONITORING & ALERTS (Optional) ===
ENABLE_CLOUDWATCH_METRICS=true
CLOUDWATCH_NAMESPACE=Bella/Application
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
SMTP_HOST=smtp.gmail.com
SMTP_USER=alerts@yourcompany.com
SMTP_PASSWORD=app_password_here
ALERT_EMAIL=oncall@yourcompany.com
```

## 🏗️ External Service Accounts Needed

### 1. OpenAI Account
- **Purpose**: AI conversation & speech-to-text
- **Signup**: https://platform.openai.com/
- **What you need**: API key with GPT-4 access
- **Cost**: ~$0.03-0.06 per API call

### 2. Twilio Account
- **Purpose**: Phone number & voice handling
- **Signup**: https://www.twilio.com/
- **What you need**: Account SID, Auth Token, Phone Number
- **Setup**: Configure webhook URL: `https://your-domain.com/twilio/voice`
- **Cost**: ~$1/month phone + $0.0085/min calls

### 3. AWS Account (Production)
- **Purpose**: Hosting & database
- **Services used**: ECS Fargate, RDS PostgreSQL, ElastiCache Redis, ALB
- **What you need**: AWS CLI configured with admin access
- **Cost**: ~$25-50/month (small instance)

### 4. Google Service Account (Optional)
- **Purpose**: Calendar integration
- **Console**: https://console.cloud.google.com/
- **What you need**: Service account JSON with Calendar API access

## 🖥️ Current Production Infrastructure

### AWS Resources (Account: 291878986264)
```
Region: ca-central-1

ECS Cluster: bella-prod-cluster
├── Service: bella-prod-service (currently scaled to 0)
├── Task Definition: bella-prod:75
└── Container: 291878986264.dkr.ecr.ca-central-1.amazonaws.com/bella-v3:latest

Database: bella-db (db.t4g.micro, PostgreSQL 17.4)
├── Endpoint: bella-db.cvc86oiqsam9.ca-central-1.rds.amazonaws.com:5432
└── Status: Available (currently stopped to save costs)

Cache: bella-redis (cache.t3.micro, Redis 7.0.7)
├── Status: Available
└── Subnet Group: bella-redis-subnet-group

Load Balancer: bella-alb
├── DNS: bella-alb-1924818779.ca-central-1.elb.amazonaws.com
└── Target Group: bella-tg

Secrets: bella-env-82YlZa (AWS Secrets Manager)
└── Contains all production environment variables
```

### Access & URLs
- **GitHub Repo**: https://github.com/antarpreetsinghk/bella_v3.git
- **Production Domain**: bella-alb-1924818779.ca-central-1.elb.amazonaws.com
- **Local Development**: http://localhost:8000
- **Health Check**: /healthz
- **API Docs**: /docs
- **Admin Dashboard**: / (requires basic auth)

## 🚀 Quick Start Steps

### 1. Clone & Setup
```bash
git clone https://github.com/antarpreetsinghk/bella_v3.git
cd bella_v3
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your credentials
```

### 2. Initialize Database
```bash
python -c "from app.db.base import init_db; init_db()"
```

### 3. Run Local Development
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Test Installation
```bash
curl http://localhost:8000/healthz
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/unified/status
```

## 🔑 Security Best Practices

1. **Never commit credentials** - Use .env files (gitignored)
2. **Use AWS Secrets Manager** for production
3. **Rotate API keys** regularly
4. **Enable MFA** on all service accounts
5. **Use least privilege** IAM policies

## 📊 Architecture Overview

```
Phone Call → Twilio → Webhook → FastAPI → OpenAI → PostgreSQL
                                    ↓
Admin Dashboard ← FastAPI ← Redis ← Session Store
```

## 💰 Cost Breakdown (Monthly)

- **OpenAI**: $10-30 (depends on usage)
- **Twilio**: $1-5 (phone + minutes)
- **AWS ECS**: $8-15 (Fargate compute)
- **AWS RDS**: $15-25 (db.t4g.micro)
- **AWS Redis**: $10-15 (cache.t3.micro)
- **AWS ALB**: $18 (fixed cost)
- **Total**: ~$62-108/month

## 🛠️ Useful Commands

```bash
# Restart production service
aws ecs update-service --cluster bella-prod-cluster --service bella-prod-service --desired-count 1 --region ca-central-1

# Stop production service (save costs)
aws ecs update-service --cluster bella-prod-cluster --service bella-prod-service --desired-count 0 --region ca-central-1

# Check database status
aws rds describe-db-instances --db-instance-identifier bella-db --region ca-central-1

# View production logs
aws logs tail /ecs/bella-prod --region ca-central-1 --follow

# Update secrets
aws secretsmanager update-secret --secret-id bella-env-82YlZa --secret-string file://secrets.json --region ca-central-1
```

## 📞 Emergency Contacts

- **GitHub**: antarpreetsinghk
- **AWS Account**: 291878986264
- **Primary Email**: info@bella-appointments.com
- **Security Email**: security@bella-appointments.com

---

⚠️ **Important**: This file contains configuration patterns only. Never include actual passwords, API keys, or sensitive data in documentation.
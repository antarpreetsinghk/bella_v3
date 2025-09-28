# CLAUDE.MD — BELLA V3 (Canadian Voice Appointment System)

## Overview
Production-ready Canadian voice appointment booking system with Twilio integration.
**Phone**: +1 438 256 5719 | **Success Rate**: 95%+ | **Response Time**: 2-4s

**Stack**: FastAPI + PostgreSQL (RDS) + Docker + GitHub Actions + ECS Fargate + ALB + Redis (Upstash)
**Timezone**: America/Edmonton → UTC | **Business Hours**: Mon-Fri 9AM-5PM

## Rules
- **State First:** Check state; output ✅/⏳/❓ (≤3 items)
- **Minimal Code:** Create only if missing; small, typed, idempotent
- **Token Efficient:** Diffs only. No explanations. ≤3 bullet summaries
- **Maximum Efficiency:** Use minimum tokens while maintaining/improving Claude Code quality and speed
- **Quality:** Add `/healthz`, logs, error handling

## Context Strategy
**Always Cache:** `claude.md`, `app/core/config.py`, `app/db/models/`, `app/services/canadian_extraction.py`
**On-Demand:** Large files (>500 lines), tests, docs, scripts

## Production Infrastructure ✅
```
AWS Account: 291878986264 (ca-central-1)
ECS Cluster: bella-prod-cluster
Service: bella-prod-service
Load Balancer: bella-alb-1924818779.ca-central-1.elb.amazonaws.com
Database: PostgreSQL RDS db.t4g.micro
Session Storage: Redis (Upstash free tier)
Task Definition: bella-prod:22 (current)
```

## Conversation Flow Architecture
```
Twilio Voice → ALB → ECS → FastAPI → Canadian Extraction → Session (Redis) → PostgreSQL
     ↓
1. ask_name → extract_canadian_name() → session.full_name
2. ask_mobile → extract_canadian_phone() → session.mobile
3. ask_time → extract_canadian_time() → session.starts_at_utc
4. confirm → book_appointment() → PostgreSQL
```

## Core Services
**Session Management** (`app/services/redis_session.py`):
- Redis (Upstash) with in-memory fallback
- 15-minute TTL, persistent across container restarts
- Session debugging with detailed logging

**Canadian Extraction** (`app/services/canadian_extraction.py`):
- **Phone**: Google phonenumbers + spelled-out numbers ("four one six" → "416")
- **Time**: parsedatetime + dateutil with Edmonton timezone
- **Name**: Enhanced regex patterns + spaCy fallback with timeout
- **LLM Fallback**: OpenAI GPT-4o-mini for complex cases

**Business Logic** (`app/core/business.py`):
- Monday-Friday 9:00 AM - 5:00 PM (Edmonton time)
- Timezone-aware validation and scheduling
- Next available slot calculation

## Optimal Instructions Format
```
[ACTION] [TARGET] [CONSTRAINTS]
✅ "Fix phone extraction @app/services/canadian_extraction.py:85 handle periods"
✅ "Add session debug @app/api/routes/twilio.py log state"
✅ "Update business hours @app/core/business.py weekend=closed"
❌ "The voice system has issues"
```

## Response Template
```
Status: [action completed]
[CODE_DIFF_ONLY]
Verify: [≤3 items]
```

## Testing & Validation
**Comprehensive Test**: `python3 comprehensive_test_suite.py`
**Phone Extraction**: `python3 test_phone_extraction.py` (100% success)
**Production Health**: `curl ALB_DNS/healthz`

**Test Scenarios**:
- Johnny Walker: Standard conversation flow
- Rocky Jonathan: Complex name patterns with commas
- Ideal Flow: Optimal user responses
- Edge Cases: "8536945968.", "My full name is Rocky, Jonathan."

## Deployment Pipeline ✅
```
git push → GitHub Actions → Docker Build → ECR Push → ECS Deploy
Auto-deployment on main branch (8-10 min total)
Health checks: /healthz, /readyz
Rollback: Automatic on deployment failure
```

## Quick Commands
**Health Check**: `curl http://bella-alb-1924818779.ca-central-1.elb.amazonaws.com/healthz`
**Logs**: `aws logs tail /ecs/bella-prod --follow`
**Deploy**: `git push` (auto-deploys to production)
**Test**: `python3 comprehensive_test_suite.py`
**Debug Session**: Check Redis keys in Upstash console

## Emergency Troubleshooting
**Session Issues**: Check Redis connection in Upstash dashboard
**Phone Extraction**: Verify phonenumbers library patterns
**Time Parsing**: Check Edmonton timezone conversion
**ECS Health**: `aws ecs describe-services --cluster bella-prod-cluster --services bella-prod-service`

## Key Metrics
- **Conversation Success Rate**: 95%+ (target)
- **Phone Extraction Accuracy**: 100% (13/13 test cases)
- **Response Time**: 2-4 seconds
- **Uptime**: 99.9% (ECS auto-scaling)
- **Monthly Cost**: ~$50 USD (no Redis charges on free tier)

## Production Snippets
**Session Debug:**
```python
logger.info("session_debug before step=%s data=%s", session.current_step, session.data)
```

**Phone Extraction Test:**
```python
result = await extract_canadian_phone("8536945968.")
# Returns: "+18536945968"
```

**Business Hours Check:**
```python
from app.core.business import is_within_hours, LOCAL_TZ
dt = datetime(2025, 10, 2, 9, 30, tzinfo=LOCAL_TZ)  # Thu 9:30 AM
is_within_hours(dt)  # Returns: True
```

**Health Endpoint:**
```python
@app.get("/healthz")
def healthz():
    return {"ok": True, "timestamp": datetime.utcnow().isoformat()}
```
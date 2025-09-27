# CLAUDE.MD — BELLA V3 (Lean)

## Overview
FastAPI + Postgres (RDS) + Docker + GH Actions + ECS Fargate + ALB. TZ: America/Edmonton → UTC.

## Rules
- **State First:** Check state; output ✅/⏳/❓ (≤3 items)
- **Minimal Code:** Create only if missing; small, typed, idempotent
- **Token Efficient:** Diffs only. No explanations. ≤3 bullet summaries
- **Quality:** Add `/healthz`, logs, error handling

## Context Strategy
**Always Cache:** `claude.md`, `app/core/config.py`, `app/db/models/`, `package.json`
**On-Demand:** Large files (>500 lines), tests, docs, scripts

## Optimal Instructions Format
```
[ACTION] [TARGET] [CONSTRAINTS]
✅ "Fix auth bug @app/api/auth.py:45 return 401"
✅ "Add rate limiting @/api/orders middleware"
❌ "The login system has problems"
```

## Response Template
```
Status: [action completed]
[CODE_DIFF_ONLY]
Verify: [≤3 items]
```

## Deployment Status
✅ CI pipeline, AWS setup, ECR, RDS, Secrets Manager, CloudWatch
⏳ Security groups, ALB, IAM roles, ECS task definition, ECS service
❓ Smoke test via ALB `/healthz`

## Progress Tracker
- [x] CI pipeline, AWS IAM + MFA, ECR repo + push, RDS setup, Secrets Manager, CloudWatch logs
- [ ] SG ECS ↔ RDS, ALB + TG + Listener, IAM Roles, Task Def, ECS Service
- [ ] Smoke test, Runbook, (Opt) HTTPS/Scaling

## Quick Commands
**Health:** `curl ALB_DNS/healthz`
**Logs:** `aws logs tail /ecs/bella-prod --follow`
**Deploy:** `git push` → GH Actions → ECR → ECS update

## Minimal Snippets
**FastAPI Health:**
```python
@app.get("/healthz")
def healthz(): return {"status": "ok"}
```

**Pydantic Config:**
```python
class Settings(BaseSettings):
    database_url: str
    model_config = SettingsConfigDict(env_file=".env")
```

**Docker Health:**
```dockerfile
HEALTHCHECK --interval=30s CMD curl -f http://localhost:8000/healthz || exit 1
```
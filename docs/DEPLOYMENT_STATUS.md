# 🚀 Deployment Status & Operations Guide

## Current Deployment

**Status:** 🟢 LIVE
**Environment:** Production
**Last Updated:** October 2025

---

## 📍 Deployment Details

### Infrastructure
```
Platform:        AWS EC2
Instance Type:   ARM64 Graviton2 (t4g.small)
Region:          ca-central-1 (Canada Central)
IP Address:      15.157.56.64
Cost:            ~$10-15/month (cost-optimized)
```

### Endpoints
```
API Documentation: http://15.157.56.64/docs
ReDoc View:        http://15.157.56.64/redoc
Health Check:      http://15.157.56.64/healthz
LLM Demo:          http://15.157.56.64/llm-demo/status
Metrics:           http://15.157.56.64/metrics
```

### Services
```yaml
Application: FastAPI (uvicorn)
  - Container: bella-app
  - Port: 8000
  - Restart: unless-stopped
  - Health: /healthz every 30s

Database: PostgreSQL 15
  - Container: bella-db
  - Port: 5432 (internal)
  - Restart: unless-stopped
  - Health: pg_isready every 10s

Cache: Redis 7
  - Container: bella-redis
  - Port: 6379
  - Restart: unless-stopped
  - Memory: 256MB (LRU eviction)
  - Health: redis-cli ping every 30s

Proxy: Nginx
  - Container: bella-nginx
  - Ports: 80, 443
  - Restart: unless-stopped
```

---

## 🎯 Performance Metrics

### Target SLAs
```
Uptime:           99%+ (allowing ~7 hours/month downtime)
Response Time:    <2 seconds for voice webhooks
API Latency:      <500ms for REST endpoints
Availability:     24/7 (auto-restart on failure)
```

### Actual Performance
```
Current Uptime:   Active (check UptimeRobot for %)
Avg Response:     Variable (production traffic dependent)
Last Incident:    N/A
Mean Time to Recovery: <5 minutes (auto-restart)
```

---

## 🔄 Deployment Process

### Automated CI/CD Pipeline

**Trigger:** Push to `main` branch

**Steps:**
1. ✅ Security scanning (Bandit + Safety)
2. ✅ Test suite (pytest with 90%+ coverage)
3. ✅ Docker build (multi-stage ARM64)
4. ✅ Push to AWS ECR
5. ✅ SSH to EC2 and deploy
6. ✅ Health check verification
7. ✅ Smoke tests

**Average Deploy Time:** 8-12 minutes

### Manual Deployment

If needed, deploy manually:

```bash
# 1. SSH to server
ssh -i ~/.ssh/bella-voice-app ubuntu@15.157.56.64

# 2. Pull latest code (if needed)
cd ~/bella_v3
git pull origin main

# 3. Pull latest Docker image
aws ecr get-login-password --region ca-central-1 | \
  docker login --username AWS --password-stdin YOUR_ECR_URL
docker pull YOUR_ECR_URL/bella-v3:latest

# 4. Restart services
docker-compose -f docker-compose.cost-optimized.yml down
docker-compose -f docker-compose.cost-optimized.yml up -d

# 5. Verify health
curl http://localhost:8000/healthz
```

---

## 🚨 Incident Response

### Quick Diagnostic

```bash
# From local machine
bash scripts/diagnose_deployment.sh
```

### Common Issues & Fixes

#### Issue: API Not Responding
```bash
# Check if containers are running
ssh ubuntu@15.157.56.64 "docker ps"

# If not running, start them
ssh ubuntu@15.157.56.64 "cd bella_v3 && docker-compose up -d"
```

#### Issue: EC2 Instance Stopped
```bash
# Use automated fix script
bash scripts/fix_deployment.sh

# Or manually via AWS Console
# EC2 → Instances → Select instance → Actions → Start
```

#### Issue: Application Crashed
```bash
# Check logs
ssh ubuntu@15.157.56.64 "docker logs bella-app --tail 100"

# Restart application container
ssh ubuntu@15.157.56.64 "docker restart bella-app"
```

#### Issue: Database Connection Errors
```bash
# Check database health
ssh ubuntu@15.157.56.64 "docker exec bella-db pg_isready"

# Restart database (data persists in volume)
ssh ubuntu@15.157.56.64 "docker restart bella-db"
```

#### Issue: Out of Memory
```bash
# Check memory usage
ssh ubuntu@15.157.56.64 "free -h"
ssh ubuntu@15.157.56.64 "docker stats --no-stream"

# Clear Redis cache if needed
ssh ubuntu@15.157.56.64 "docker exec bella-redis redis-cli FLUSHALL"
```

---

## 📊 Monitoring

### Automated Monitoring

**UptimeRobot** (Recommended):
- External health checks every 5 minutes
- Email alerts on downtime
- Public status page available
- Setup: See [MONITORING_SETUP.md](./MONITORING_SETUP.md)

**Docker Health Checks** (Built-in):
- Container-level health monitoring
- Automatic restart on health check failure
- Configured in docker-compose.yml

**AWS CloudWatch** (Optional):
- Application logs: `/bella/application`
- System metrics: CPU, memory, network
- Custom metrics: API response times, business metrics

### Manual Health Checks

```bash
# Quick health check
curl http://15.157.56.64/healthz

# Full endpoint test
curl http://15.157.56.64/docs    # Should return HTML
curl http://15.157.56.64/metrics # Should return JSON

# Container health
ssh ubuntu@15.157.56.64 "docker ps --format 'table {{.Names}}\t{{.Status}}'"
```

---

## 🔒 Security Considerations

### Current Security Measures

✅ **Network Security:**
- Security group restricts access to required ports only
- SSH key-based authentication (no passwords)
- Nginx reverse proxy for SSL termination (when configured)

✅ **Application Security:**
- API key authentication on protected endpoints
- Twilio webhook signature validation
- SQL injection protection (parameterized queries)
- Input validation for all voice data

✅ **Infrastructure Security:**
- Regular security scanning in CI/CD
- Dependency vulnerability checks (Safety)
- Code security analysis (Bandit)
- AWS Secrets Manager for sensitive credentials

⚠️ **Known Limitations (Portfolio Context):**
- HTTP not HTTPS (SSL cert not configured - cost optimization)
- Single instance (no load balancing - sufficient for demo traffic)
- Manual backup strategy (RDS would provide automated backups)

---

## 💰 Cost Breakdown

### Monthly Costs
```
EC2 Instance (t4g.small ARM64):  ~$12/month
  - Compute: $0.0168/hour × 730 hours = $12.26
  - Data Transfer: ~$1-3 (minimal for portfolio)

Total Infrastructure: ~$13-15/month
```

### Cost Optimization Strategies
```
✅ ARM64 Graviton2 (40% cheaper than x86)
✅ Single instance (vs auto-scaling group)
✅ On-demand (vs Reserved - flexible for portfolio)
✅ Regex extraction (vs LLM API costs)
✅ Self-managed DB (vs RDS - ~$30/month savings)
```

### Cost Comparison
```
Current Setup:          $13-15/month
Alternative (RDS+LB):   $50-80/month
Managed Platform:       $100-200/month

Savings: ~70-90% for portfolio deployment
```

---

## 🎓 Architecture Decisions

### Why This Stack?

**EC2 over Serverless (Lambda/Fargate):**
- ✅ Full control over environment
- ✅ Easier debugging and SSH access
- ✅ Cost-effective for always-on services
- ✅ Demonstrates infrastructure management skills

**ARM64 over x86:**
- ✅ 40% cost reduction
- ✅ Better price/performance ratio
- ✅ Same capabilities for Python workloads
- ✅ Shows cost-consciousness

**Self-Managed DB over RDS:**
- ✅ ~$30/month savings
- ✅ Demonstrates Docker and container orchestration
- ✅ Full control for learning
- ⚠️ Trade-off: Manual backup management

**Single Instance over Auto-Scaling:**
- ✅ Sufficient for portfolio traffic
- ✅ Simpler to manage
- ✅ Lower costs
- ⚠️ No high availability (acceptable for demo)

---

## 📋 Maintenance Checklist

### Weekly
- [ ] Check UptimeRobot dashboard for downtime events
- [ ] Review CloudWatch logs for errors
- [ ] Verify all endpoints responding

### Monthly
- [ ] Update dependencies (security patches)
- [ ] Review Docker image size and optimize if needed
- [ ] Check disk usage on EC2 instance
- [ ] Verify backups (if automated backup configured)
- [ ] Review AWS costs and optimize if possible

### Quarterly
- [ ] Security audit (update credentials, rotate keys)
- [ ] Load test to verify performance
- [ ] Review and update documentation
- [ ] Consider infrastructure improvements

---

## 🔗 Related Documentation

- [Monitoring Setup](./MONITORING_SETUP.md) - UptimeRobot configuration
- [Architecture Guide](../CLAUDE.md) - Complete technical architecture
- [Security Framework](../SECURITY.md) - Security implementation details
- [Performance Optimization](../PERFORMANCE_OPTIMIZATION.md) - Optimization case study

---

## 📞 Emergency Contacts

**For Downtime/Incidents:**
1. Run diagnostic script: `bash scripts/diagnose_deployment.sh`
2. Run fix script: `bash scripts/fix_deployment.sh`
3. Check GitHub Actions for deployment failures
4. SSH to server for manual investigation

**AWS Console Access:**
- Region: ca-central-1
- Service: EC2 → Instances
- Instance ID: i-09ab71843c2b3aea9

---

**Status:** Production-ready portfolio deployment
**Last Verified:** October 2025
**Next Review:** Monthly

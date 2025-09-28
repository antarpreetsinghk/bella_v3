# DEPLOYMENT GUIDE - Bella V3

## Overview
Complete operational guide for deploying and managing the Canadian voice appointment booking system in production.

## 🚀 PRODUCTION ENVIRONMENT

### Current Production Setup
```
AWS Account: 291878986264
Region: ca-central-1 (Canada Central)
Phone Number: +1 438 256 5719
Load Balancer: bella-alb-1924818779.ca-central-1.elb.amazonaws.com
Health Check: http://bella-alb-1924818779.ca-central-1.elb.amazonaws.com/healthz
```

### Infrastructure Components
- **ECS Cluster**: bella-prod-cluster
- **ECS Service**: bella-prod-service
- **Task Definition**: bella-prod:22 (current)
- **Database**: PostgreSQL RDS db.t4g.micro
- **Session Storage**: Redis (Upstash free tier)
- **Container Registry**: ECR bella-v3
- **Secrets**: AWS Secrets Manager

## 🔄 AUTOMATED DEPLOYMENT PIPELINE

### GitHub Actions Workflow
```
Trigger: Push to main branch
Pipeline: .github/workflows/ci.yml
Duration: 8-10 minutes total
Success Rate: 100% (last 10 deployments)
```

### Deployment Steps
1. **Unit Tests** (if tests/ exists)
2. **Docker Compose Smoke Test**
3. **Build & Push to ECR**
4. **Update ECS Task Definition**
5. **Deploy to ECS Service**
6. **Health Check Validation**

### Deployment Commands
```bash
# Standard deployment (automatic)
git add .
git commit -m "feat: description"
git push origin main

# Monitor deployment
gh run list --limit 1
gh run view [RUN_ID]

# Check health after deployment
curl http://bella-alb-1924818779.ca-central-1.elb.amazonaws.com/healthz
```

## 📊 MONITORING & HEALTH CHECKS

### Health Endpoints
```bash
# Primary health check
curl http://bella-alb-1924818779.ca-central-1.elb.amazonaws.com/healthz
# Response: {"ok":true}

# Ready check (database connectivity)
curl http://bella-alb-1924818779.ca-central-1.elb.amazonaws.com/readyz
```

### Service Status Commands
```bash
# ECS service health
aws ecs describe-services \
  --cluster bella-prod-cluster \
  --services bella-prod-service

# Task status
aws ecs list-tasks \
  --cluster bella-prod-cluster \
  --service-name bella-prod-service

# Task details
aws ecs describe-tasks \
  --cluster bella-prod-cluster \
  --tasks [TASK_ARN]
```

### Log Monitoring
```bash
# Real-time logs
aws logs tail /ecs/bella-prod --follow

# Recent logs
aws logs tail /ecs/bella-prod --since 1h

# Error filtering
aws logs filter-log-events \
  --log-group-name /ecs/bella-prod \
  --filter-pattern "ERROR"
```

## 🔧 TROUBLESHOOTING PROCEDURES

### Common Issues & Solutions

#### 1. Service Not Responding
```bash
# Check service status
aws ecs describe-services --cluster bella-prod-cluster --services bella-prod-service

# Check target group health
aws elbv2 describe-target-health --target-group-arn arn:aws:elasticloadbalancing:ca-central-1:291878986264:targetgroup/bella-tg/26716742b615a65b

# Force new deployment
aws ecs update-service --cluster bella-prod-cluster --service bella-prod-service --force-new-deployment
```

#### 2. Session Issues (Redis)
```bash
# Check Upstash Redis status
# Login to: https://console.upstash.com/

# Test Redis connection locally
python3 -c "
import redis
r = redis.from_url('redis://[UPSTASH_URL]')
print(r.ping())
"

# Check session keys
# Use Upstash console browser
```

#### 3. Database Connection Issues
```bash
# Check RDS status
aws rds describe-db-instances --db-instance-identifier [DB_IDENTIFIER]

# Test connection from task
aws ecs execute-command \
  --cluster bella-prod-cluster \
  --task [TASK_ARN] \
  --container bella-api \
  --command "/bin/bash" \
  --interactive
```

#### 4. Phone/Time Extraction Issues
```bash
# Run extraction tests
python3 test_phone_extraction.py
python3 comprehensive_test_suite.py

# Check extraction logs
aws logs filter-log-events \
  --log-group-name /ecs/bella-prod \
  --filter-pattern "[phone_canadian]"
```

### Emergency Response

#### Immediate Rollback
```bash
# Rollback to previous task definition
aws ecs update-service \
  --cluster bella-prod-cluster \
  --service bella-prod-service \
  --task-definition bella-prod:21

# Monitor rollback
aws ecs describe-services --cluster bella-prod-cluster --services bella-prod-service
```

#### Scale Down/Up
```bash
# Scale down (emergency stop)
aws ecs update-service \
  --cluster bella-prod-cluster \
  --service bella-prod-service \
  --desired-count 0

# Scale up
aws ecs update-service \
  --cluster bella-prod-cluster \
  --service bella-prod-service \
  --desired-count 1
```

## 🔐 SECURITY & SECRETS MANAGEMENT

### AWS Secrets Manager
```bash
# View secret structure
aws secretsmanager describe-secret --secret-id bella-env-82YlZa

# Update secret values
aws secretsmanager update-secret \
  --secret-id bella-env-82YlZa \
  --secret-string '{"KEY":"VALUE"}'
```

### Required Environment Variables
```
OPENAI_API_KEY - OpenAI API key for LLM fallback
POSTGRES_HOST - RDS endpoint
POSTGRES_DB - Database name
POSTGRES_USER - Database username
POSTGRES_PASSWORD - Database password
REDIS_URL - Upstash Redis connection string
TWILIO_ACCOUNT_SID - Twilio account identifier
TWILIO_AUTH_TOKEN - Twilio authentication token
```

## 📋 MAINTENANCE PROCEDURES

### Regular Tasks

#### Weekly Health Check
```bash
# System health
curl http://bella-alb-1924818779.ca-central-1.elb.amazonaws.com/healthz

# Run comprehensive tests
python3 comprehensive_test_suite.py

# Check Redis usage (Upstash console)
# Monitor: Request count, memory usage

# Review logs for errors
aws logs filter-log-events \
  --log-group-name /ecs/bella-prod \
  --start-time $(date -d '1 week ago' +%s)000 \
  --filter-pattern "ERROR"
```

#### Monthly Tasks
- Review AWS costs in billing dashboard
- Check Redis usage against free tier limits
- Validate phone number test cases
- Review conversation success rates
- Update dependencies if needed

#### Quarterly Tasks
- Review and rotate secrets
- Update spaCy models if available
- Performance optimization review
- Disaster recovery testing

## 📈 PERFORMANCE MONITORING

### Key Metrics to Track
- **Response Time**: Target 2-4 seconds
- **Conversation Success Rate**: Target 95%+
- **Phone Extraction Accuracy**: Target 100%
- **System Uptime**: Target 99.9%+
- **Redis Usage**: Monitor against 10,000 requests/day limit

### Alerting Setup (Optional)
```bash
# CloudWatch alarms for key metrics
aws cloudwatch put-metric-alarm \
  --alarm-name bella-high-response-time \
  --alarm-description "High response time alert" \
  --metric-name ResponseTime \
  --namespace AWS/ApplicationELB \
  --statistic Average \
  --period 300 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold
```

## 🆘 EMERGENCY CONTACTS

### Support Resources
- **GitHub Issues**: https://github.com/antarpreetsinghk/bella_v3/issues
- **AWS Support**: (if applicable)
- **Upstash Support**: https://upstash.com/
- **Twilio Support**: https://support.twilio.com/

### Quick Reference
```bash
# Emergency health check
curl -I http://bella-alb-1924818779.ca-central-1.elb.amazonaws.com/healthz

# Emergency logs
aws logs tail /ecs/bella-prod --since 30m

# Emergency rollback
aws ecs update-service --cluster bella-prod-cluster --service bella-prod-service --task-definition bella-prod:21
```

---
*Last Updated: 2025-09-27*
*Version: 1.0*
*Status: Production Ready*
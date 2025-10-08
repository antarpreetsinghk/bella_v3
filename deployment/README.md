# Bella Voice App - AWS Deployment Guide

## Overview
This guide covers deploying the Bella Voice App to AWS with cost optimization for 50 calls/day (1,500 calls/month).

## Architecture
- **AWS Lambda** + Function URLs (no API Gateway needed)
- **Aurora Serverless v2** (PostgreSQL) - 0.5 ACU minimum
- **DynamoDB** for session storage (pay-per-request)
- **CloudWatch** for monitoring
- **GitHub Actions** for CI/CD

**Estimated Monthly Cost: $25-30**

## Prerequisites

### 1. AWS Account Setup
```bash
# Install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Configure AWS credentials
aws configure
```

### 2. Terraform Installation
```bash
# Install Terraform
wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install terraform
```

### 3. GitHub Secrets Setup
Add these secrets to your GitHub repository:

```
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
DATABASE_URL=postgresql://bella_admin:password@endpoint:5432/bella
OPENAI_API_KEY=sk-...
BELLA_API_KEY=your-bella-api-key
TWILIO_AUTH_TOKEN=...
TWILIO_ACCOUNT_SID=AC...
TWILIO_PHONE_NUMBER=+15551234567
LAMBDA_EXECUTION_ROLE_ARN=arn:aws:iam::123456789012:role/bella-voice-app-lambda-role
```

## Deployment Steps

### 1. Infrastructure Setup with Terraform

```bash
# Navigate to terraform directory
cd deployment/terraform

# Copy and edit variables
cp terraform.tfvars.example terraform.tfvars
nano terraform.tfvars  # Fill in your actual values

# Initialize Terraform
terraform init

# Plan deployment
terraform plan

# Deploy infrastructure
terraform apply
```

### 2. GitHub Actions Deployment

Push to main branch to trigger automated deployment:

```bash
git add .
git commit -m "Deploy to AWS Lambda"
git push origin main
```

The CI/CD pipeline will:
1. Run tests
2. Create Lambda deployment package
3. Deploy to AWS Lambda
4. Run database migrations
5. Test deployment
6. Provide Twilio webhook URL

### 3. Twilio Configuration

After deployment, update your Twilio phone number webhook:

1. Go to [Twilio Console](https://console.twilio.com/us1/develop/phone-numbers/manage/incoming)
2. Select your phone number
3. Set webhook URL to: `https://your-lambda-url.lambda-url.us-east-1.on.aws/twilio/voice`
4. Set HTTP method to POST

## Manual Deployment (Alternative)

If you prefer manual deployment:

### 1. Create Deployment Package
```bash
# Install dependencies
pip install -r requirements.txt -t deployment/
pip install mangum -t deployment/

# Copy application
cp -r app deployment/
cp -r alembic deployment/
cp alembic.ini deployment/

# Create handler
cp deployment/lambda-adapter.py deployment/handler.py

# Create zip
cd deployment && zip -r ../bella-deployment.zip . && cd ..
```

### 2. Deploy to Lambda
```bash
# Create Lambda function
aws lambda create-function \
  --function-name bella-voice-app \
  --runtime python3.11 \
  --role arn:aws:iam::123456789012:role/lambda-execution-role \
  --handler handler.lambda_handler \
  --zip-file fileb://bella-deployment.zip \
  --timeout 30 \
  --memory-size 512

# Create function URL
aws lambda create-function-url-config \
  --function-name bella-voice-app \
  --auth-type NONE
```

## Cost Optimization Tips

### 1. Aurora Serverless Optimization
```sql
-- Monitor unused connections
SELECT count(*) as connection_count FROM pg_stat_activity;

-- Set aggressive connection limits
ALTER SYSTEM SET max_connections = 20;
```

### 2. Lambda Optimization
- Use ARM-based Graviton2 processors (cheaper)
- Optimize memory size (512MB should be sufficient)
- Monitor cold starts and adjust memory if needed

### 3. DynamoDB Optimization
- Use TTL for automatic session cleanup
- Monitor read/write capacity usage
- Consider switching to on-demand billing

### 4. CloudWatch Cost Control
```bash
# Set log retention to 7 days
aws logs put-retention-policy \
  --log-group-name /aws/lambda/bella-voice-app \
  --retention-in-days 7
```

## Monitoring and Debugging

### 1. CloudWatch Dashboard
Import the monitoring dashboard:
```bash
aws cloudwatch put-dashboard \
  --dashboard-name "BellaVoiceApp" \
  --dashboard-body file://deployment/monitoring-dashboard.json
```

### 2. Log Analysis
```bash
# View recent Lambda logs
aws logs tail /aws/lambda/bella-voice-app --follow

# Search for errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/bella-voice-app \
  --filter-pattern "ERROR"
```

### 3. Performance Testing
```bash
# Test Lambda function
aws lambda invoke \
  --function-name bella-voice-app \
  --payload '{"httpMethod":"GET","path":"/health"}' \
  response.json && cat response.json

# Simulate Twilio webhook
curl -X POST "https://your-lambda-url.lambda-url.us-east-1.on.aws/twilio/voice" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "CallSid=TEST123&From=+14165551234&To=+15551234567"
```

## Troubleshooting

### Common Issues

1. **Cold Start Latency**
   - Solution: Increase memory to 1024MB if response time > 5s
   - Cost impact: ~$5-10/month increase

2. **Database Connection Errors**
   - Check security groups and VPC configuration
   - Verify Lambda is in same VPC as RDS

3. **Twilio Webhook Timeouts**
   - Lambda timeout should be < 10 seconds for Twilio
   - Monitor duration metrics in CloudWatch

4. **High Costs**
   - Review Aurora ACU usage (should stay at 0.5)
   - Check DynamoDB read/write units
   - Verify log retention settings

### Environment Variables
```bash
# Lambda environment variables (set via Terraform or AWS Console)
APP_ENV=production
DATABASE_URL=postgresql://bella_admin:password@cluster.123.us-east-1.rds.amazonaws.com:5432/bella
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
BELLA_API_KEY=your-api-key
TWILIO_AUTH_TOKEN=...
TWILIO_ACCOUNT_SID=AC...
TWILIO_PHONE_NUMBER=+15551234567
GOOGLE_CALENDAR_ENABLED=true
DYNAMODB_TABLE_NAME=bella-voice-app-sessions
```

## Scaling Considerations

For higher call volumes:

### 50-200 calls/day
- Current setup handles this well
- Cost: $25-35/month

### 200-1000 calls/day
- Consider ECS on EC2 for better cost efficiency
- Add Redis for session storage
- Cost: $50-100/month

### 1000+ calls/day
- Move to ECS with Application Load Balancer
- Use RDS Multi-AZ for high availability
- Consider Aurora Serverless scaling up to 2-4 ACUs
- Cost: $100-300/month

## Security Best Practices

1. **IAM Roles**: Use least privilege principle
2. **Secrets**: Store in SSM Parameter Store (encrypted)
3. **VPC**: Lambda in private subnets with NAT Gateway
4. **WAF**: Consider AWS WAF for Lambda Function URLs
5. **Monitoring**: Set up CloudWatch alarms for security events

## Backup and Recovery

### Database Backups
- Aurora automatic backups: 7 days retention
- Point-in-time recovery available
- Backup window: 03:00-04:00 UTC (off-peak)

### Application Recovery
- Lambda function versions for rollback
- GitHub repository as source of truth
- Infrastructure as Code with Terraform state

## Cost Monitoring

Set up billing alerts:
```bash
# Create billing alarm
aws cloudwatch put-metric-alarm \
  --alarm-name "BellaVoiceApp-BillingAlarm" \
  --alarm-description "Billing alarm for Bella Voice App" \
  --metric-name EstimatedCharges \
  --namespace AWS/Billing \
  --statistic Maximum \
  --period 86400 \
  --threshold 50.0 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=Currency,Value=USD
```

## Support and Maintenance

### Regular Tasks
1. **Weekly**: Review CloudWatch metrics and costs
2. **Monthly**: Update dependencies and security patches
3. **Quarterly**: Review and optimize resource allocation

### Health Checks
```bash
# Automated health check script
#!/bin/bash
FUNCTION_URL="https://your-lambda-url.lambda-url.us-east-1.on.aws"

response=$(curl -s -o /dev/null -w "%{http_code}" "${FUNCTION_URL}/health")
if [ "$response" = "200" ]; then
  echo "✅ Health check passed"
else
  echo "❌ Health check failed: $response"
  # Send alert (SNS, email, Slack, etc.)
fi
```

This deployment provides a robust, cost-effective solution for handling 50 calls/day with room to scale as your business grows.
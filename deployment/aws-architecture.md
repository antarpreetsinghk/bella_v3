# AWS Architecture for Bella V3 - Cost Optimized for 50 Calls/Day

## Overview
This architecture is optimized for minimal AWS costs while handling 50 calls per day for a single business.

## Monthly Cost Estimate: ~$35-40/month

### Architecture Components

#### 1. Application Hosting: AWS Lambda + API Gateway
**Cost: ~$5/month**
- Lambda: 50 calls/day × 30 days = 1,500 calls/month
  - Average execution time: 2 seconds per call
  - Memory: 512MB
  - Cost: $0.00 (within free tier - 1M requests, 400,000 GB-seconds)
- API Gateway: REST API
  - 1,500 API calls/month
  - Cost: $3.50/month (minimum charge for REST API)
  - Alternative: Use Lambda Function URLs (free) if direct Twilio integration is possible

#### 2. Database: RDS Aurora Serverless v2 (PostgreSQL)
**Cost: ~$12/month**
- Minimum capacity: 0.5 ACUs
- Scale down to 0 ACUs when idle (if using Aurora Serverless v1)
- Storage: 10GB included
- Backups: 7-day retention
- Alternative for lower cost: Use DynamoDB (free tier: 25GB storage, 25 read/write units)

#### 3. Session Storage: ElastiCache Redis (t4g.micro)
**Cost: ~$12/month**
- Instance: t4g.micro (1 vCPU, 0.5 GiB)
- Single node, no replication
- Alternative: Use Lambda memory + DynamoDB TTL for sessions (~$0/month)

#### 4. Container Registry: Amazon ECR
**Cost: ~$1/month**
- Storage: 1GB for Docker images
- Data transfer: Minimal for 1-2 deployments/month

#### 5. Secrets Management: AWS Systems Manager Parameter Store
**Cost: $0/month**
- Standard parameters (free tier)
- Store API keys, database credentials

#### 6. Monitoring: CloudWatch
**Cost: ~$5/month**
- Basic metrics: Free
- 5GB logs ingestion/month: Free
- Custom metrics: 10 metrics × $0.30 = $3
- Alarms: 10 alarms × $0.10 = $1
- Dashboards: 1 dashboard = $0 (first 3 free)

#### 7. Static IP for Twilio Webhooks: Lambda Function URLs
**Cost: $0/month**
- Use Lambda Function URLs (no API Gateway needed)
- Persistent URL for Twilio webhooks

## Ultra-Low-Cost Alternative Architecture (~$15-20/month)

### Option A: Serverless-First
1. **Lambda + Function URLs**: $0
2. **DynamoDB**: $0 (free tier)
3. **S3 for static assets**: $0.23/month
4. **Parameter Store**: $0
5. **CloudWatch (basic)**: $0
6. **Total**: ~$1/month

### Option B: Single EC2 Instance
1. **EC2 t4g.nano** (2 vCPU, 0.5GB): $3/month
2. **EBS Storage** (8GB): $0.80/month
3. **Elastic IP**: $3.60/month (if not attached 24/7)
4. **PostgreSQL on same instance**: $0
5. **Redis on same instance**: $0
6. **Total**: ~$8/month

### Option C: ECS on EC2 (Recommended for this use case)
1. **EC2 t4g.small** (2 vCPU, 2GB): $12/month
2. **EBS Storage** (20GB): $2/month
3. **Application Load Balancer**: $18/month (can be avoided with direct EC2)
4. **RDS Aurora Serverless v2**: $12/month
5. **Total**: ~$26-44/month

## Recommended Architecture for 50 Calls/Day

### Primary Setup: Lambda + Aurora Serverless + DynamoDB Sessions
```
┌─────────────┐       ┌──────────────┐       ┌─────────────┐
│   Twilio    │──────▶│   Lambda     │──────▶│   Aurora    │
│  Webhooks   │       │  Functions   │       │ Serverless  │
└─────────────┘       └──────────────┘       └─────────────┘
                             │
                             ▼
                      ┌──────────────┐
                      │   DynamoDB   │
                      │  (Sessions)  │
                      └──────────────┘
```

**Monthly Cost Breakdown:**
- Lambda + API Gateway: $3.50
- Aurora Serverless v2 (0.5 ACU min): $12
- DynamoDB (sessions): $0 (free tier)
- CloudWatch: $2
- ECR: $1
- **Total: ~$18.50/month**

### Benefits:
- Zero infrastructure management
- Auto-scaling (though not needed for 50 calls/day)
- High availability
- Pay only for actual usage
- No idle compute costs

## Implementation Steps

### 1. Lambda Deployment Package
```python
# handler.py
import json
from mangum import Mangum
from app.main import app

# Wrap FastAPI with Mangum for Lambda
handler = Mangum(app)
```

### 2. Infrastructure as Code (Terraform)
```hcl
# main.tf
provider "aws" {
  region = "us-east-1"  # Cheapest region
}

# Lambda Function
resource "aws_lambda_function" "bella_app" {
  filename         = "deployment.zip"
  function_name    = "bella-voice-app"
  role            = aws_iam_role.lambda_role.arn
  handler         = "handler.handler"
  runtime         = "python3.11"
  timeout         = 30
  memory_size     = 512

  environment {
    variables = {
      DATABASE_URL = aws_ssm_parameter.db_url.value
      OPENAI_API_KEY = aws_ssm_parameter.openai_key.value
    }
  }
}

# Lambda Function URL (Free alternative to API Gateway)
resource "aws_lambda_function_url" "bella_url" {
  function_name      = aws_lambda_function.bella_app.function_name
  authorization_type = "NONE"  # Twilio will send auth token
}

# Aurora Serverless v2
resource "aws_rds_cluster" "bella_db" {
  engine             = "aurora-postgresql"
  engine_mode        = "provisioned"
  engine_version     = "15.4"
  database_name      = "bella"
  master_username    = "bella_admin"
  master_password    = random_password.db_password.result

  serverlessv2_scaling_configuration {
    max_capacity = 1
    min_capacity = 0.5
  }

  skip_final_snapshot = true
}
```

### 3. DynamoDB for Sessions
```python
# services/dynamodb_session.py
import boto3
from datetime import datetime, timedelta

class DynamoDBSessionManager:
    def __init__(self):
        self.table = boto3.resource('dynamodb').Table('bella_sessions')

    async def get_session(self, call_sid: str):
        response = self.table.get_item(Key={'call_sid': call_sid})
        return response.get('Item', {})

    async def save_session(self, call_sid: str, data: dict):
        self.table.put_item(
            Item={
                'call_sid': call_sid,
                'data': data,
                'ttl': int((datetime.now() + timedelta(hours=1)).timestamp())
            }
        )
```

## Cost Optimization Tips

1. **Use Spot Instances**: If using EC2, use Spot instances (70% cheaper)
2. **Reserved Capacity**: For Aurora, purchase reserved DB instances (30% savings)
3. **S3 for Recordings**: Store call recordings in S3 Glacier (~$0.004/GB/month)
4. **Scheduled Scaling**: Turn off non-critical resources during off-hours
5. **Use Free Tier**: Maximize AWS free tier benefits in first year

## Monitoring & Debugging

### CloudWatch Dashboards (Free)
```json
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["AWS/Lambda", "Duration", {"stat": "Average"}],
          [".", "Errors", {"stat": "Sum"}],
          [".", "Invocations", {"stat": "Sum"}]
        ],
        "period": 300,
        "stat": "Average",
        "region": "us-east-1",
        "title": "Lambda Performance"
      }
    }
  ]
}
```

### X-Ray Tracing (Optional - $5/month)
- Trace 100,000 traces free/month
- Then $5 per million traces
- Provides detailed request flow analysis

## Production Testing

### Load Testing Script
```bash
#!/bin/bash
# simulate_calls.sh
for i in {1..50}; do
  curl -X POST "https://your-lambda-url.lambda-url.us-east-1.on.aws/twilio/voice" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "CallSid=TEST_$i&From=+14165551234"
  sleep 30  # Spread calls throughout the day
done
```

## Monthly Cost Summary

### Minimal Setup (Lambda + DynamoDB)
- **Total: $15-20/month**
- Best for: Maximum cost savings
- Trade-off: Less familiar database (DynamoDB instead of PostgreSQL)

### Recommended Setup (Lambda + Aurora Serverless)
- **Total: $25-30/month**
- Best for: Balance of cost and functionality
- Trade-off: Slightly higher cost for PostgreSQL compatibility

### Traditional Setup (ECS on EC2)
- **Total: $35-45/month**
- Best for: Familiar deployment model
- Trade-off: Higher baseline cost

## Decision Matrix

| Factor | Lambda + DynamoDB | Lambda + Aurora | ECS on EC2 |
|--------|------------------|-----------------|------------|
| Monthly Cost | $15-20 | $25-30 | $35-45 |
| Setup Complexity | Medium | Low | High |
| Maintenance | None | Minimal | Regular |
| Scalability | Infinite | High | Manual |
| Cold Start | 1-2s | 1-2s | None |
| Database | NoSQL | PostgreSQL | PostgreSQL |

## Recommended: Lambda + Aurora Serverless v2
For 50 calls/day, the Lambda + Aurora Serverless v2 setup provides:
- **$25-30/month total cost**
- Zero infrastructure management
- PostgreSQL compatibility (no code changes needed)
- Automatic scaling (though not needed at this volume)
- Built-in high availability
- Pay-per-use pricing model
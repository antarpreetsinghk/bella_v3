#!/bin/bash
# Bella V3 - Step 4: Register ECS Task Definition
set -e

echo "📋 Registering ECS Task Definition for Bella V3..."

# Variables - UPDATED WITH YOUR VALUES
ACCOUNT_ID="REPLACE_WITH_YOUR_AWS_ACCOUNT_ID"                                                    # Your AWS Account ID
ECR_REPO_URI="REPLACE_WITH_YOUR_AWS_ACCOUNT_ID.dkr.ecr.ca-central-1.amazonaws.com/bella-v3"    # Your ECR repository URI
REGION="ca-central-1"

# Update task definition with actual account ID and ECR URI
echo "Updating task definition with your AWS Account ID and ECR URI..."

# Create updated task definition
cat > /tmp/task-definition-updated.json << EOF
{
  "family": "bella-prod",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "arn:aws:iam::${ACCOUNT_ID}:role/bella-ecs-execution-role",
  "taskRoleArn": "arn:aws:iam::${ACCOUNT_ID}:role/bella-ecs-task-role",
  "containerDefinitions": [
    {
      "name": "bella-api",
      "image": "${ECR_REPO_URI}:latest",
      "essential": true,
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "secrets": [
        {
          "name": "OPENAI_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:${REGION}:${ACCOUNT_ID}:secret:bella-env:OPENAI_API_KEY::"
        },
        {
          "name": "OPENAI_MODEL",
          "valueFrom": "arn:aws:secretsmanager:${REGION}:${ACCOUNT_ID}:secret:bella-env:OPENAI_MODEL::"
        },
        {
          "name": "REQUEST_MAX_TOKENS",
          "valueFrom": "arn:aws:secretsmanager:${REGION}:${ACCOUNT_ID}:secret:bella-env:REQUEST_MAX_TOKENS::"
        },
        {
          "name": "RESPONSE_MAX_TOKENS",
          "valueFrom": "arn:aws:secretsmanager:${REGION}:${ACCOUNT_ID}:secret:bella-env:RESPONSE_MAX_TOKENS::"
        },
        {
          "name": "POSTGRES_HOST",
          "valueFrom": "arn:aws:secretsmanager:${REGION}:${ACCOUNT_ID}:secret:bella-env:POSTGRES_HOST::"
        },
        {
          "name": "POSTGRES_PORT",
          "valueFrom": "arn:aws:secretsmanager:${REGION}:${ACCOUNT_ID}:secret:bella-env:POSTGRES_PORT::"
        },
        {
          "name": "POSTGRES_DB",
          "valueFrom": "arn:aws:secretsmanager:${REGION}:${ACCOUNT_ID}:secret:bella-env:POSTGRES_DB::"
        },
        {
          "name": "POSTGRES_USER",
          "valueFrom": "arn:aws:secretsmanager:${REGION}:${ACCOUNT_ID}:secret:bella-env:POSTGRES_USER::"
        },
        {
          "name": "POSTGRES_PASSWORD",
          "valueFrom": "arn:aws:secretsmanager:${REGION}:${ACCOUNT_ID}:secret:bella-env:POSTGRES_PASSWORD::"
        },
        {
          "name": "DATABASE_URL",
          "valueFrom": "arn:aws:secretsmanager:${REGION}:${ACCOUNT_ID}:secret:bella-env:DATABASE_URL::"
        },
        {
          "name": "BELLA_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:${REGION}:${ACCOUNT_ID}:secret:bella-env:BELLA_API_KEY::"
        },
        {
          "name": "ADMIN_USER",
          "valueFrom": "arn:aws:secretsmanager:${REGION}:${ACCOUNT_ID}:secret:bella-env:ADMIN_USER::"
        },
        {
          "name": "ADMIN_PASS",
          "valueFrom": "arn:aws:secretsmanager:${REGION}:${ACCOUNT_ID}:secret:bella-env:ADMIN_PASS::"
        },
        {
          "name": "CSRF_SECRET",
          "valueFrom": "arn:aws:secretsmanager:${REGION}:${ACCOUNT_ID}:secret:bella-env:CSRF_SECRET::"
        },
        {
          "name": "TWILIO_AUTH_TOKEN",
          "valueFrom": "arn:aws:secretsmanager:${REGION}:${ACCOUNT_ID}:secret:bella-env:TWILIO_AUTH_TOKEN::"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/bella-prod",
          "awslogs-region": "${REGION}",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/healthz || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
EOF

# Register the task definition
echo "Registering task definition..."
TASK_DEF_ARN=$(aws ecs register-task-definition \
    --cli-input-json file:///tmp/task-definition-updated.json \
    --region $REGION \
    --query 'taskDefinition.taskDefinitionArn' \
    --output text)

echo "✅ Task Definition registered successfully!"
echo "Task Definition ARN: $TASK_DEF_ARN"
echo ""
echo "📝 Save this for the next step:"
echo "export TASK_DEF_ARN=$TASK_DEF_ARN"

# Clean up
rm -f /tmp/task-definition-updated.json
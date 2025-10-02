#!/bin/bash
# Bella V3 - Step 3: Create IAM Roles for ECS
set -e

echo "🔑 Creating IAM Roles for Bella V3 ECS..."

# Variables - UPDATED WITH YOUR VALUES
REGION="ca-central-1"
ACCOUNT_ID="YOUR_AWS_ACCOUNT_ID"  # Your AWS Account ID (12 digits)

# Create ECS Task Execution Role
echo "Creating ECS Task Execution Role..."

# Trust policy for ECS tasks
cat > /tmp/ecs-task-execution-trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create the execution role
aws iam create-role \
    --role-name bella-ecs-execution-role \
    --assume-role-policy-document file:///tmp/ecs-task-execution-trust-policy.json

# Attach AWS managed policy for ECS task execution
aws iam attach-role-policy \
    --role-name bella-ecs-execution-role \
    --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

# Create custom policy for Secrets Manager access
cat > /tmp/secrets-manager-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": [
        "arn:aws:secretsmanager:ca-central-1:*:secret:bella-env*"
      ]
    }
  ]
}
EOF

# Create and attach custom policy
aws iam create-policy \
    --policy-name bella-secrets-manager-policy \
    --policy-document file:///tmp/secrets-manager-policy.json

aws iam attach-role-policy \
    --role-name bella-ecs-execution-role \
    --policy-arn arn:aws:iam::$ACCOUNT_ID:policy/bella-secrets-manager-policy

# Create ECS Task Role (for application permissions)
echo "Creating ECS Task Role..."

aws iam create-role \
    --role-name bella-ecs-task-role \
    --assume-role-policy-document file:///tmp/ecs-task-execution-trust-policy.json

# Create custom policy for application needs (CloudWatch logs, etc.)
cat > /tmp/task-role-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogStreams"
      ],
      "Resource": "arn:aws:logs:ca-central-1:*:log-group:/ecs/bella-prod*"
    }
  ]
}
EOF

aws iam create-policy \
    --policy-name bella-task-role-policy \
    --policy-document file:///tmp/task-role-policy.json

aws iam attach-role-policy \
    --role-name bella-ecs-task-role \
    --policy-arn arn:aws:iam::$ACCOUNT_ID:policy/bella-task-role-policy

# Clean up temp files
rm -f /tmp/ecs-task-execution-trust-policy.json
rm -f /tmp/secrets-manager-policy.json
rm -f /tmp/task-role-policy.json

echo "✅ IAM Roles created successfully!"
echo ""
echo "📝 Created roles:"
echo "Execution Role ARN: arn:aws:iam::$ACCOUNT_ID:role/bella-ecs-execution-role"
echo "Task Role ARN: arn:aws:iam::$ACCOUNT_ID:role/bella-ecs-task-role"
echo ""
echo "export EXECUTION_ROLE_ARN=arn:aws:iam::$ACCOUNT_ID:role/bella-ecs-execution-role"
echo "export TASK_ROLE_ARN=arn:aws:iam::$ACCOUNT_ID:role/bella-ecs-task-role"
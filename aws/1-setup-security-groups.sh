#!/bin/bash
# Bella V3 - Step 1: Create Security Groups
set -e

echo "🔐 Creating Security Groups for Bella V3..."

# Variables - UPDATED WITH YOUR VALUES
VPC_ID="vpc-03d48bacd018c678e"  # Your VPC ID where RDS is running
REGION="ca-central-1"

# Create ALB Security Group
echo "Creating ALB Security Group..."
ALB_SG_ID=$(aws ec2 create-security-group \
    --group-name bella-alb-sg \
    --description "Security group for Bella Application Load Balancer" \
    --vpc-id $VPC_ID \
    --region $REGION \
    --query 'GroupId' \
    --output text)

echo "ALB Security Group created: $ALB_SG_ID"

# Create ECS Security Group
echo "Creating ECS Security Group..."
ECS_SG_ID=$(aws ec2 create-security-group \
    --group-name bella-ecs-sg \
    --description "Security group for Bella ECS tasks" \
    --vpc-id $VPC_ID \
    --region $REGION \
    --query 'GroupId' \
    --output text)

echo "ECS Security Group created: $ECS_SG_ID"

# Configure ALB Security Group Rules
echo "Configuring ALB Security Group rules..."
aws ec2 authorize-security-group-ingress \
    --group-id $ALB_SG_ID \
    --protocol tcp \
    --port 80 \
    --cidr 0.0.0.0/0 \
    --region $REGION

aws ec2 authorize-security-group-ingress \
    --group-id $ALB_SG_ID \
    --protocol tcp \
    --port 443 \
    --cidr 0.0.0.0/0 \
    --region $REGION

# Configure ECS Security Group Rules
echo "Configuring ECS Security Group rules..."
aws ec2 authorize-security-group-ingress \
    --group-id $ECS_SG_ID \
    --protocol tcp \
    --port 8000 \
    --source-group $ALB_SG_ID \
    --region $REGION

# Update RDS Security Group (if you know the RDS SG ID)
# RDS_SG_ID="sg-xxxxxxxxx"  # UPDATE: Your RDS security group ID
# echo "Updating RDS Security Group to allow ECS access..."
# aws ec2 authorize-security-group-ingress \
#     --group-id $RDS_SG_ID \
#     --protocol tcp \
#     --port 5432 \
#     --source-group $ECS_SG_ID \
#     --region $REGION

echo "✅ Security Groups created successfully!"
echo "ALB_SG_ID: $ALB_SG_ID"
echo "ECS_SG_ID: $ECS_SG_ID"
echo ""
echo "📝 Save these IDs for the next steps:"
echo "export ALB_SG_ID=$ALB_SG_ID"
echo "export ECS_SG_ID=$ECS_SG_ID"
echo ""
echo "⚠️  IMPORTANT: Update your RDS security group manually to allow:"
echo "   Source: $ECS_SG_ID"
echo "   Port: 5432 (PostgreSQL)"
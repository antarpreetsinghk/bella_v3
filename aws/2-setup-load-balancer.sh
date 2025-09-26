#!/bin/bash
# Bella V3 - Step 2: Create Application Load Balancer
set -e

echo "⚖️ Creating Application Load Balancer for Bella V3..."

# Variables - UPDATED WITH YOUR VALUES
VPC_ID="vpc-03d48bacd018c678e"          # Your VPC ID
SUBNET_1="subnet-09818872232282d14"     # Public subnet 1 (ca-central-1a)
SUBNET_2="subnet-0e415b6cc28c8f442"     # Public subnet 2 (ca-central-1b)
ALB_SG_ID="$ALB_SG_ID"                  # From step 1 output (dynamic)
REGION="ca-central-1"

# Create Application Load Balancer
echo "Creating Application Load Balancer..."
ALB_ARN=$(aws elbv2 create-load-balancer \
    --name bella-alb \
    --subnets $SUBNET_1 $SUBNET_2 \
    --security-groups $ALB_SG_ID \
    --scheme internet-facing \
    --type application \
    --ip-address-type ipv4 \
    --region $REGION \
    --query 'LoadBalancers[0].LoadBalancerArn' \
    --output text)

echo "ALB created: $ALB_ARN"

# Get ALB DNS name
ALB_DNS=$(aws elbv2 describe-load-balancers \
    --load-balancer-arns $ALB_ARN \
    --region $REGION \
    --query 'LoadBalancers[0].DNSName' \
    --output text)

echo "ALB DNS: $ALB_DNS"

# Create Target Group
echo "Creating Target Group..."
TG_ARN=$(aws elbv2 create-target-group \
    --name bella-tg \
    --protocol HTTP \
    --port 8000 \
    --vpc-id $VPC_ID \
    --target-type ip \
    --health-check-enabled \
    --health-check-protocol HTTP \
    --health-check-path /healthz \
    --health-check-interval-seconds 30 \
    --health-check-timeout-seconds 5 \
    --healthy-threshold-count 2 \
    --unhealthy-threshold-count 3 \
    --region $REGION \
    --query 'TargetGroups[0].TargetGroupArn' \
    --output text)

echo "Target Group created: $TG_ARN"

# Create HTTP Listener (redirects to HTTPS if you have SSL later)
echo "Creating HTTP Listener..."
LISTENER_ARN=$(aws elbv2 create-listener \
    --load-balancer-arn $ALB_ARN \
    --protocol HTTP \
    --port 80 \
    --default-actions Type=forward,TargetGroupArn=$TG_ARN \
    --region $REGION \
    --query 'Listeners[0].ListenerArn' \
    --output text)

echo "HTTP Listener created: $LISTENER_ARN"

echo "✅ Load Balancer setup completed!"
echo ""
echo "📝 Save these values for the next steps:"
echo "export ALB_ARN=$ALB_ARN"
echo "export TG_ARN=$TG_ARN"
echo "export ALB_DNS=$ALB_DNS"
echo ""
echo "🌐 Your application will be available at: http://$ALB_DNS"
echo ""
echo "⏱️  Note: ALB may take 2-3 minutes to become active"
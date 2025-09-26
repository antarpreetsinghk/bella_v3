#!/bin/bash
# Bella V3 - Step 5: Create ECS Cluster and Service
set -e

echo "🚀 Creating ECS Cluster and Service for Bella V3..."

# Variables - UPDATED WITH YOUR VALUES
CLUSTER_NAME="bella-prod-cluster"
SERVICE_NAME="bella-prod-service"
SUBNET_1="subnet-09818872232282d14"  # Public subnet 1 (ca-central-1a)
SUBNET_2="subnet-0e415b6cc28c8f442"  # Public subnet 2 (ca-central-1b)
ECS_SG_ID="$ECS_SG_ID"               # From step 1 output (dynamic)
TG_ARN="$TG_ARN"                     # From step 2 output (dynamic)
TASK_DEF_ARN="$TASK_DEF_ARN"         # From step 4 output (dynamic)
REGION="ca-central-1"

# Create ECS Cluster
echo "Creating ECS Cluster..."
aws ecs create-cluster \
    --cluster-name $CLUSTER_NAME \
    --capacity-providers FARGATE \
    --default-capacity-provider-strategy capacityProvider=FARGATE,weight=1 \
    --region $REGION

echo "ECS Cluster '$CLUSTER_NAME' created successfully!"

# Create ECS Service
echo "Creating ECS Service..."
SERVICE_ARN=$(aws ecs create-service \
    --cluster $CLUSTER_NAME \
    --service-name $SERVICE_NAME \
    --task-definition $TASK_DEF_ARN \
    --desired-count 1 \
    --launch-type FARGATE \
    --platform-version LATEST \
    --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_1,$SUBNET_2],securityGroups=[$ECS_SG_ID],assignPublicIp=ENABLED}" \
    --load-balancers "targetGroupArn=$TG_ARN,containerName=bella-api,containerPort=8000" \
    --health-check-grace-period-seconds 300 \
    --region $REGION \
    --query 'service.serviceArn' \
    --output text)

echo "ECS Service created: $SERVICE_ARN"

# Enable auto-scaling (optional but recommended)
echo "Setting up auto-scaling..."
aws application-autoscaling register-scalable-target \
    --service-namespace ecs \
    --scalable-dimension ecs:service:DesiredCount \
    --resource-id service/$CLUSTER_NAME/$SERVICE_NAME \
    --min-capacity 1 \
    --max-capacity 3 \
    --region $REGION

# Create scaling policy for CPU utilization
aws application-autoscaling put-scaling-policy \
    --service-namespace ecs \
    --scalable-dimension ecs:service:DesiredCount \
    --resource-id service/$CLUSTER_NAME/$SERVICE_NAME \
    --policy-name bella-cpu-scaling-policy \
    --policy-type TargetTrackingScaling \
    --target-tracking-scaling-policy-configuration '{
        "TargetValue": 70.0,
        "PredefinedMetricSpecification": {
            "PredefinedMetricType": "ECSServiceAverageCPUUtilization"
        },
        "ScaleOutCooldown": 300,
        "ScaleInCooldown": 300
    }' \
    --region $REGION

echo "✅ ECS Service created successfully!"
echo ""
echo "📊 Service Details:"
echo "Cluster: $CLUSTER_NAME"
echo "Service: $SERVICE_NAME"
echo "Service ARN: $SERVICE_ARN"
echo ""
echo "⏱️  Service is starting up... This may take 2-5 minutes."
echo ""
echo "📝 Monitor deployment with:"
echo "aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME --region $REGION"
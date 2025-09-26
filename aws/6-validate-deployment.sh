#!/bin/bash
# Bella V3 - Step 6: Validate Deployment
set -e

echo "✅ Validating Bella V3 Deployment..."

# Variables - UPDATED WITH YOUR VALUES
CLUSTER_NAME="bella-prod-cluster"
SERVICE_NAME="bella-prod-service"
ALB_DNS="$ALB_DNS"                   # From step 2 output (dynamic)
REGION="ca-central-1"

echo "🔍 Checking ECS Service Status..."
SERVICE_STATUS=$(aws ecs describe-services \
    --cluster $CLUSTER_NAME \
    --services $SERVICE_NAME \
    --region $REGION \
    --query 'services[0].status' \
    --output text)

RUNNING_COUNT=$(aws ecs describe-services \
    --cluster $CLUSTER_NAME \
    --services $SERVICE_NAME \
    --region $REGION \
    --query 'services[0].runningCount' \
    --output text)

DESIRED_COUNT=$(aws ecs describe-services \
    --cluster $CLUSTER_NAME \
    --services $SERVICE_NAME \
    --region $REGION \
    --query 'services[0].desiredCount' \
    --output text)

echo "Service Status: $SERVICE_STATUS"
echo "Running Tasks: $RUNNING_COUNT"
echo "Desired Tasks: $DESIRED_COUNT"

if [ "$RUNNING_COUNT" -eq "$DESIRED_COUNT" ] && [ "$SERVICE_STATUS" = "ACTIVE" ]; then
    echo "✅ Service is healthy!"
else
    echo "⚠️  Service is not fully healthy yet. Checking task status..."

    # Get task details
    TASK_ARNS=$(aws ecs list-tasks \
        --cluster $CLUSTER_NAME \
        --service-name $SERVICE_NAME \
        --region $REGION \
        --query 'taskArns[]' \
        --output text)

    if [ -n "$TASK_ARNS" ]; then
        echo "📋 Task Details:"
        aws ecs describe-tasks \
            --cluster $CLUSTER_NAME \
            --tasks $TASK_ARNS \
            --region $REGION \
            --query 'tasks[0].{Status:lastStatus,Health:healthStatus,CreatedAt:createdAt}' \
            --output table
    fi
fi

echo ""
echo "🌐 Testing Application Endpoints..."

# Test health endpoint
echo "Testing /healthz endpoint..."
if curl -f -s "http://$ALB_DNS/healthz" > /tmp/healthz.json; then
    echo "✅ Health check passed!"
    cat /tmp/healthz.json
else
    echo "❌ Health check failed!"
    echo "ALB may still be warming up. Wait 2-3 minutes and try again."
fi

echo ""

# Test readiness endpoint
echo "Testing /readyz endpoint (database connectivity)..."
if curl -f -s "http://$ALB_DNS/readyz" > /tmp/readyz.json; then
    echo "✅ Readiness check passed! Database is connected."
    cat /tmp/readyz.json
else
    echo "❌ Readiness check failed!"
    echo "Check RDS security group allows ECS tasks on port 5432"
fi

echo ""

# Test admin dashboard
echo "Testing admin dashboard..."
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://$ALB_DNS/")
if [ "$HTTP_STATUS" = "401" ]; then
    echo "✅ Admin dashboard is protected (returns 401 - Basic Auth required)"
else
    echo "⚠️  Admin dashboard returned status: $HTTP_STATUS"
fi

echo ""
echo "📊 CloudWatch Logs..."
echo "View logs at: https://console.aws.amazon.com/cloudwatch/home?region=$REGION#logsV2:log-groups/log-group/%2Fecs%2Fbella-prod"

echo ""
echo "🎉 Deployment Validation Complete!"
echo ""
echo "🌍 Your application is available at:"
echo "   http://$ALB_DNS"
echo ""
echo "🔐 Admin Dashboard:"
echo "   http://$ALB_DNS/"
echo "   Username: antar"
echo "   Password: kam1234"
echo ""
echo "📋 API Endpoints:"
echo "   Health: http://$ALB_DNS/healthz"
echo "   Ready: http://$ALB_DNS/readyz"
echo "   Book: http://$ALB_DNS/assistant/book (POST with API key)"
echo ""
echo "🔑 API Key: kam1234"

# Clean up temp files
rm -f /tmp/healthz.json /tmp/readyz.json
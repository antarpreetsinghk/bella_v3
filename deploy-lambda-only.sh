#!/bin/bash
set -e

echo "🚀 Deploying Bella Voice App to AWS Lambda (Serverless)"
echo "=================================================="

# Configuration
FUNCTION_NAME="bella-voice-app"
REGION="us-east-1"
RUNTIME="python3.11"
TIMEOUT=30
MEMORY=512

echo "📦 Creating deployment package..."

# Create deployment directory
rm -rf lambda-deployment
mkdir lambda-deployment

# Install dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt -t lambda-deployment/
pip install mangum -t lambda-deployment/

# Copy application code
echo "Copying application code..."
cp -r app lambda-deployment/
cp -r alembic lambda-deployment/
cp alembic.ini lambda-deployment/

# Create Lambda handler
cat > lambda-deployment/handler.py << 'EOF'
import os
import sys
import logging

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

from mangum import Mangum
from app.main import app

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Lambda handler
handler = Mangum(app, lifespan="off")

def lambda_handler(event, context):
    """AWS Lambda handler"""
    try:
        logger.info(f"Processing event: {event}")
        return handler(event, context)
    except Exception as e:
        logger.error(f"Handler error: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "body": f'{{"error": "Internal server error: {str(e)}"}}',
            "headers": {"Content-Type": "application/json"}
        }
EOF

# Create deployment zip
echo "Creating deployment package..."
cd lambda-deployment
zip -r ../bella-lambda.zip . -x "*.pyc" "*__pycache__*" "*.git*"
cd ..

echo "📤 Deploying to AWS Lambda..."

# Get Lambda execution role ARN
ROLE_ARN=$(aws iam get-role --role-name bella-voice-app-lambda-role --query 'Role.Arn' --output text 2>/dev/null || echo "")

if [ -z "$ROLE_ARN" ]; then
    echo "❌ Lambda execution role not found. Please run Terraform first or create the role."
    exit 1
fi

# Check if function exists
FUNCTION_EXISTS=$(aws lambda get-function --function-name $FUNCTION_NAME --region $REGION 2>/dev/null || echo "")

if [ -n "$FUNCTION_EXISTS" ]; then
    echo "🔄 Updating existing Lambda function..."
    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --zip-file fileb://bella-lambda.zip \
        --region $REGION

    echo "⚙️ Updating function configuration..."
    aws lambda update-function-configuration \
        --function-name $FUNCTION_NAME \
        --environment Variables='{"APP_ENV":"production","DATABASE_URL":"sqlite+aiosqlite:////tmp/bella.db","OPENAI_API_KEY":"placeholder-openai-key","OPENAI_MODEL":"gpt-4o-mini","BELLA_API_KEY":"33333333333333333333333333","TWILIO_AUTH_TOKEN":"placeholder-twilio-token","TWILIO_ACCOUNT_SID":"ACtest123","TWILIO_PHONE_NUMBER":"+15559876543","GOOGLE_CALENDAR_ENABLED":"true","DYNAMODB_TABLE_NAME":"bella-voice-app-sessions","REDIS_URL":""}' \
        --timeout $TIMEOUT \
        --memory-size $MEMORY \
        --region $REGION
else
    echo "✨ Creating new Lambda function..."
    aws lambda create-function \
        --function-name $FUNCTION_NAME \
        --runtime $RUNTIME \
        --role $ROLE_ARN \
        --handler handler.lambda_handler \
        --zip-file fileb://bella-lambda.zip \
        --timeout $TIMEOUT \
        --memory-size $MEMORY \
        --environment Variables='{"APP_ENV":"production","DATABASE_URL":"sqlite+aiosqlite:////tmp/bella.db","OPENAI_API_KEY":"placeholder-openai-key","OPENAI_MODEL":"gpt-4o-mini","BELLA_API_KEY":"33333333333333333333333333","TWILIO_AUTH_TOKEN":"placeholder-twilio-token","TWILIO_ACCOUNT_SID":"ACtest123","TWILIO_PHONE_NUMBER":"+15559876543","GOOGLE_CALENDAR_ENABLED":"true","DYNAMODB_TABLE_NAME":"bella-voice-app-sessions","REDIS_URL":""}' \
        --region $REGION

    echo "🌐 Creating function URL..."
    FUNCTION_URL=$(aws lambda create-function-url-config \
        --function-name $FUNCTION_NAME \
        --auth-type NONE \
        --cors '{
            "AllowCredentials": false,
            "AllowHeaders": ["*"],
            "AllowMethods": ["*"],
            "AllowOrigins": ["*"],
            "ExposeHeaders": ["*"],
            "MaxAge": 86400
        }' \
        --region $REGION \
        --query 'FunctionUrl' --output text)
fi

# Wait for function to be updated
echo "⏳ Waiting for function to be ready..."
aws lambda wait function-updated --function-name $FUNCTION_NAME --region $REGION

# Get function URL
if [ -z "$FUNCTION_URL" ]; then
    FUNCTION_URL=$(aws lambda get-function-url-config --function-name $FUNCTION_NAME --region $REGION --query 'FunctionUrl' --output text 2>/dev/null || echo "")
fi

if [ -z "$FUNCTION_URL" ]; then
    echo "🌐 Creating function URL..."
    FUNCTION_URL=$(aws lambda create-function-url-config \
        --function-name $FUNCTION_NAME \
        --auth-type NONE \
        --cors '{
            "AllowCredentials": false,
            "AllowHeaders": ["*"],
            "AllowMethods": ["*"],
            "AllowOrigins": ["*"],
            "ExposeHeaders": ["*"],
            "MaxAge": 86400
        }' \
        --region $REGION \
        --query 'FunctionUrl' --output text)
fi

echo "🧪 Testing deployment..."
HEALTH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "${FUNCTION_URL}health" || echo "000")

echo ""
echo "🎉 Deployment Complete!"
echo "========================="
echo "📍 Function URL: $FUNCTION_URL"
echo "🔗 Twilio Webhook URL: ${FUNCTION_URL}twilio/voice"
echo "🏥 Health Check: HTTP $HEALTH_RESPONSE"
echo "💰 Estimated Cost: ~$5/month for 50 calls/day"
echo ""
echo "Next Steps:"
echo "1. Update Twilio webhook to: ${FUNCTION_URL}twilio/voice"
echo "2. Monitor via CloudWatch: https://console.aws.amazon.com/cloudwatch"
echo "3. View logs: aws logs tail /aws/lambda/$FUNCTION_NAME --follow"

# Cleanup
rm -rf lambda-deployment bella-lambda.zip

echo "✅ Deployment script completed!"
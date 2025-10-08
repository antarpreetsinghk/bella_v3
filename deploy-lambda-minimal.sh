#!/bin/bash
set -e

echo "🚀 Deploying Bella Voice App to AWS Lambda (Minimal)"
echo "============================================"

# Configuration
FUNCTION_NAME="bella-voice-app"
REGION="us-east-1"

echo "📦 Creating minimal deployment package..."

# Create deployment directory
rm -rf lambda-deployment-minimal
mkdir lambda-deployment-minimal

# Install only essential dependencies
echo "Installing minimal dependencies..."
pip install -r requirements-lambda.txt -t lambda-deployment-minimal/ --no-deps --disable-pip-version-check

# Install specific dependencies we need
pip install aiosqlite==0.20.0 -t lambda-deployment-minimal/ --no-deps
pip install anyio==3.7.1 -t lambda-deployment-minimal/ --no-deps

# Copy application code
echo "Copying application code..."
cp -r app lambda-deployment-minimal/

# Create optimized Lambda handler
cat > lambda-deployment-minimal/handler.py << 'EOF'
import os
import sys
import logging
import json

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

# Configure logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from mangum import Mangum
    from app.main import app

    # Lambda handler with proper error handling
    mangum_handler = Mangum(app, lifespan="off")

    def lambda_handler(event, context):
        """AWS Lambda handler with comprehensive error handling"""
        try:
            logger.info(f"Processing event type: {event.get('httpMethod', 'unknown')}")
            logger.info(f"Path: {event.get('path', 'unknown')}")

            # Call the mangum handler
            response = mangum_handler(event, context)
            logger.info(f"Response status: {response.get('statusCode', 'unknown')}")
            return response

        except Exception as handler_error:
            logger.error(f"Handler error: {str(handler_error)}", exc_info=True)
            return {
                "statusCode": 500,
                "body": json.dumps({"error": f"Internal server error: {str(handler_error)}"}),
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*"
                }
            }

except ImportError as import_error:
    logger.error(f"Import error: {str(import_error)}")

    def lambda_handler(event, context):
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Import error: {str(import_error)}"}),
            "headers": {"Content-Type": "application/json"}
        }

except Exception as general_error:
    logger.error(f"General error during import: {str(general_error)}")

    def lambda_handler(event, context):
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Startup error: {str(general_error)}"}),
            "headers": {"Content-Type": "application/json"}
        }
EOF

# Create deployment zip (exclude unnecessary files)
echo "Creating optimized deployment package..."
cd lambda-deployment-minimal

# Remove unnecessary files to reduce size
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.so" -delete 2>/dev/null || true
find . -name "tests" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "test_*" -delete 2>/dev/null || true

zip -r ../bella-lambda-minimal.zip . -x "*.git*" "*.DS_Store*"
cd ..

echo "📤 Deploying to AWS Lambda..."

# Update function code only
echo "🔄 Updating Lambda function code..."
aws lambda update-function-code \
    --function-name $FUNCTION_NAME \
    --zip-file fileb://bella-lambda-minimal.zip \
    --region $REGION

echo "⚙️ Updating function configuration..."
aws lambda update-function-configuration \
    --function-name $FUNCTION_NAME \
    --environment Variables='{
        "APP_ENV":"production",
        "DATABASE_URL":"sqlite+aiosqlite:////tmp/bella.db",
        "OPENAI_API_KEY":"placeholder-openai-key",
        "OPENAI_MODEL":"gpt-4o-mini",
        "BELLA_API_KEY":"33333333333333333333333333",
        "TWILIO_AUTH_TOKEN":"placeholder-twilio-token",
        "TWILIO_ACCOUNT_SID":"ACtest123",
        "TWILIO_PHONE_NUMBER":"+15559876543",
        "GOOGLE_CALENDAR_ENABLED":"false",
        "REDIS_URL":"",
        "TWILIO_WEBHOOK_URL":"https://bhcnf2i6eh3bxnr6lrnt4ubouy0obfjy.lambda-url.us-east-1.on.aws/twilio/voice"
    }' \
    --region $REGION

echo "✅ Lambda deployment completed!"
echo "Function URL: https://bhcnf2i6eh3bxnr6lrnt4ubouy0obfjy.lambda-url.us-east-1.on.aws/"

# Clean up
rm -rf lambda-deployment-minimal
rm bella-lambda-minimal.zip

echo "🧪 Testing deployment..."
curl -s "https://bhcnf2i6eh3bxnr6lrnt4ubouy0obfjy.lambda-url.us-east-1.on.aws/healthz" || echo "Health check failed"
#!/bin/bash
set -e

echo "🔧 Building Lambda dependencies with Pydantic V1 compatibility approach..."
echo "Using FastAPI 0.99.0 + Pydantic V1 (no pydantic-core issues)"

# Clean up any existing lambda-deployment-minimal directory
rm -rf lambda-deployment-compatible
mkdir lambda-deployment-compatible

# Install dependencies with correct platform for Lambda x86_64
echo "📦 Installing compatible dependencies for Lambda..."
pip install \
    --platform manylinux2014_x86_64 \
    --target lambda-deployment-compatible/ \
    --implementation cp \
    --python-version 3.11 \
    --only-binary=:all: \
    --upgrade \
    -r requirements-lambda-compatible.txt

# Copy application code
echo "📁 Copying application code..."
cp -r app lambda-deployment-compatible/

# Create Lambda handler
echo "⚙️ Creating Lambda handler..."
cat > lambda-deployment-compatible/handler.py << 'EOF'
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
    import_error_msg = str(import_error)

    def lambda_handler(event, context):
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Import error: {import_error_msg}"}),
            "headers": {"Content-Type": "application/json"}
        }

except Exception as general_error:
    logger.error(f"General error during import: {str(general_error)}")
    general_error_msg = str(general_error)

    def lambda_handler(event, context):
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Startup error: {general_error_msg}"}),
            "headers": {"Content-Type": "application/json"}
        }
EOF

# Remove unnecessary files to reduce size
echo "🧹 Cleaning up unnecessary files..."
find lambda-deployment-compatible -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find lambda-deployment-compatible -name "*.pyc" -delete
find lambda-deployment-compatible -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
find lambda-deployment-compatible -name "test_*" -delete 2>/dev/null || true

echo "✅ Compatible dependencies built successfully!"
echo "📊 Package size:"
du -sh lambda-deployment-compatible/

# Create deployment zip
echo "🗜️ Creating deployment package..."
cd lambda-deployment-compatible
zip -r ../bella-lambda-compatible.zip . -x "*.git*" "*.DS_Store*"
cd ..

echo "🚀 Ready for deployment: bella-lambda-compatible.zip"
echo "📦 Deployment package size:"
ls -lh bella-lambda-compatible.zip

echo ""
echo "💡 This package uses FastAPI 0.99.0 + Pydantic V1"
echo "💡 No pydantic-core dependencies - should work reliably in Lambda"
#!/bin/bash
set -e

echo "🔧 Building Lambda dependencies with platform-specific installation..."
echo "This approach uses pip with --platform to ensure Lambda compatibility"

# Clean up any existing lambda-deployment-minimal directory
rm -rf lambda-deployment-minimal
mkdir lambda-deployment-minimal

# Install dependencies with correct platform for Lambda x86_64
echo "📦 Installing dependencies for Lambda platform (manylinux2014_x86_64)..."
pip install \
    --platform manylinux2014_x86_64 \
    --target lambda-deployment-minimal/ \
    --implementation cp \
    --python-version 3.11 \
    --only-binary=:all: \
    --upgrade \
    -r requirements-lambda-minimal.txt

# Copy application code
echo "📁 Copying application code..."
cp -r app lambda-deployment-minimal/

# Create Lambda handler
echo "⚙️ Creating Lambda handler..."
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
find lambda-deployment-minimal -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find lambda-deployment-minimal -name "*.pyc" -delete
find lambda-deployment-minimal -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
find lambda-deployment-minimal -name "test_*" -delete 2>/dev/null || true

echo "✅ Dependencies built successfully with platform-specific installation!"
echo "📊 Package size:"
du -sh lambda-deployment-minimal/

# Create deployment zip
echo "🗜️ Creating deployment package..."
cd lambda-deployment-minimal
zip -r ../bella-lambda-platform-built.zip . -x "*.git*" "*.DS_Store*"
cd ..

echo "🚀 Ready for deployment: bella-lambda-platform-built.zip"
echo "📦 Deployment package size:"
ls -lh bella-lambda-platform-built.zip

echo ""
echo "💡 This package was built using pip with --platform manylinux2014_x86_64"
echo "💡 This should resolve the pydantic-core binary compatibility issue"
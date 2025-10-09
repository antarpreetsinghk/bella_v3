#!/bin/bash
set -e

echo "🐳 Building Lambda dependencies with Docker..."

# Build the Docker image
docker build -f Dockerfile.lambda-deps -t lambda-deps-builder .

# Create a container and extract packages
echo "📦 Extracting built packages..."

# Create temporary container
CONTAINER_ID=$(docker create lambda-deps-builder)

# Clean up any existing lambda-deployment-minimal directory
rm -rf lambda-deployment-minimal

# Create fresh directory
mkdir lambda-deployment-minimal

# Copy built packages from container
docker cp ${CONTAINER_ID}:/lambda-packages/. lambda-deployment-minimal/

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

# Clean up container
docker rm ${CONTAINER_ID}

echo "✅ Dependencies built successfully with Docker!"
echo "📊 Package size:"
du -sh lambda-deployment-minimal/

# Create deployment zip
echo "🗜️ Creating deployment package..."
cd lambda-deployment-minimal
zip -r ../bella-lambda-docker-built.zip . -x "*.git*" "*.DS_Store*"
cd ..

echo "🚀 Ready for deployment: bella-lambda-docker-built.zip"
echo "📦 Deployment package size:"
ls -lh bella-lambda-docker-built.zip
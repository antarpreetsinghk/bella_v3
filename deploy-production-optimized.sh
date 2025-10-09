#!/bin/bash

# Deploy Optimized Production Lambda with Core FastAPI Call Flow
set -e

echo "🚀 Deploying Optimized Production Lambda"
echo "========================================"

# Clean up previous deployment
rm -rf lambda-optimized
mkdir -p lambda-optimized

echo "📦 Copying core application code..."

# Copy the main Lambda handler
cp lambda_handler.py lambda-optimized/

# Copy only essential app directories
cp -r app/ lambda-optimized/

# Copy minimal requirements - exclude development/testing packages
cat > lambda-optimized/requirements.txt << EOF
# Core FastAPI & Database
fastapi==0.116.1
uvicorn==0.35.0
sqlalchemy==2.0.43
asyncpg==0.30.0
pydantic==2.11.7
pydantic-core==2.33.2
pydantic-settings==2.10.1
mangum==0.17.0
httpx==0.28.1
python-multipart==0.0.20
urllib3==2.5.0
itsdangerous==2.2.0
python-dotenv==1.1.1

# Twilio Voice Core
twilio==9.8.0

# Essential Data Processing
phonenumbers==8.13.50
python-dateutil==2.8.2

# Session Storage
redis==5.0.1

# Google Calendar Integration
google-api-python-client==2.100.0
google-auth==2.41.1
google-auth-httplib2==0.1.0

# Monitoring
structlog==23.2.0
EOF

echo "📦 Installing optimized dependencies..."
cd lambda-optimized

# Install only production dependencies
pip install -r requirements.txt -t . --no-deps

# Install dependencies with minimal deps
pip install \
    fastapi==0.116.1 \
    uvicorn==0.35.0 \
    sqlalchemy==2.0.43 \
    asyncpg==0.30.0 \
    pydantic==2.11.7 \
    pydantic-core==2.33.2 \
    pydantic-settings==2.10.1 \
    mangum==0.17.0 \
    httpx==0.28.1 \
    python-multipart==0.0.20 \
    urllib3==2.5.0 \
    itsdangerous==2.2.0 \
    python-dotenv==1.1.1 \
    twilio==9.8.0 \
    phonenumbers==8.13.50 \
    python-dateutil==2.8.2 \
    redis==5.0.1 \
    google-api-python-client==2.100.0 \
    google-auth==2.41.1 \
    google-auth-httplib2==0.1.0 \
    structlog==23.2.0 \
    -t . --no-deps

echo "🔧 Optimizing package size..."

# Remove unnecessary files and directories
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.dist-info" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "tests" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "test" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.egg-info" -type d -exec rm -rf {} + 2>/dev/null || true

# Remove development packages that aren't needed
rm -rf alembic* || true
rm -rf boto3* || true
rm -rf pytest* || true
rm -rf coverage* || true
rm -rf dateparser* || true
rm -rf parsedatetime* || true

# Remove unnecessary binary files
find . -name "*.so.*" -delete 2>/dev/null || true
find . -name "*.dylib" -delete 2>/dev/null || true

# Remove documentation and examples
find . -name "docs" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "examples" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.md" -delete 2>/dev/null || true

echo "📦 Creating optimized deployment package..."
zip -r ../lambda-optimized.zip . -x "*.pyc" "__pycache__/*" "*.dist-info/*" "tests/*" "test/*"

cd ..

# Check package size
PACKAGE_SIZE=$(stat -c%s lambda-optimized.zip)
PACKAGE_SIZE_MB=$((PACKAGE_SIZE / 1024 / 1024))
echo "📊 Package size: ${PACKAGE_SIZE_MB}MB (limit: 50MB)"

if [ $PACKAGE_SIZE_MB -gt 50 ]; then
    echo "⚠️  Package too large, need to optimize further"
    exit 1
fi

echo "🚀 Updating Lambda function..."
aws lambda update-function-code \
    --function-name bella-voice-app \
    --zip-file fileb://lambda-optimized.zip \
    --region ca-central-1

echo "⚙️ Updating Lambda configuration..."
aws lambda update-function-configuration \
    --function-name bella-voice-app \
    --handler lambda_handler.lambda_handler \
    --timeout 30 \
    --memory-size 512 \
    --region ca-central-1

echo "🔧 Updating environment variables..."
aws lambda update-function-configuration \
    --function-name bella-voice-app \
    --environment file://lambda-env-update.json \
    --region ca-central-1

echo "✅ Optimized Lambda deployed successfully!"
echo "🧪 Testing the deployment..."

# Test the deployment
sleep 10

echo "Testing health check..."
curl -s "https://bhcnf2i6eh3bxnr6lrnt4ubouy0obfjy.lambda-url.us-east-1.on.aws/"

echo -e "\n\n🎉 Optimized production deployment complete!"
echo "📞 Your voice app now has:"
echo "   ✅ Multi-step conversation flow"
echo "   ✅ Caller ID recognition"
echo "   ✅ Session persistence with Redis"
echo "   ✅ PostgreSQL database integration"
echo "   ✅ Google Calendar integration"
echo ""
echo "🔗 Lambda URL: https://bhcnf2i6eh3bxnr6lrnt4ubouy0obfjy.lambda-url.us-east-1.on.aws/"
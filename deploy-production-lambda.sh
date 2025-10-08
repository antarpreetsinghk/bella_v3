#!/bin/bash

# Deploy Production Lambda with Full FastAPI Call Flow
set -e

echo "🚀 Deploying Production Lambda with Full Call Flow"
echo "=================================================="

# Clean up previous deployment
rm -rf lambda-production
mkdir -p lambda-production

echo "📦 Copying application code..."

# Copy the main Lambda handler
cp lambda_handler.py lambda-production/

# Copy the entire app directory
cp -r app/ lambda-production/

# Copy alembic for database migrations
cp -r alembic/ lambda-production/
cp alembic.ini lambda-production/

# Copy requirements
cp requirements.txt lambda-production/

echo "📦 Installing production dependencies..."
cd lambda-production

# Install all dependencies for production
pip install -r requirements.txt -t .

echo "🔧 Setting Lambda configuration..."

# Create __init__.py files to ensure proper imports
find . -type d -name "app" -exec touch {}/__init__.py \;
find . -type d -name "api" -exec touch {}/__init__.py \;
find . -type d -name "routes" -exec touch {}/__init__.py \;
find . -type d -name "services" -exec touch {}/__init__.py \;
find . -type d -name "core" -exec touch {}/__init__.py \;
find . -type d -name "db" -exec touch {}/__init__.py \;
find . -type d -name "models" -exec touch {}/__init__.py \;
find . -type d -name "crud" -exec touch {}/__init__.py \;

# Remove unnecessary files to reduce package size
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.dist-info" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "tests" -type d -exec rm -rf {} + 2>/dev/null || true

echo "📦 Creating deployment package..."
zip -r ../lambda-production.zip . -x "*.pyc" "__pycache__/*" "*.dist-info/*" "tests/*"

cd ..

echo "🚀 Updating Lambda function..."
aws lambda update-function-code \
    --function-name bella-voice-app \
    --zip-file fileb://lambda-production.zip \
    --region us-east-1

echo "⚙️ Updating Lambda configuration..."
aws lambda update-function-configuration \
    --function-name bella-voice-app \
    --handler lambda_handler.lambda_handler \
    --timeout 30 \
    --memory-size 512 \
    --region us-east-1

echo "🔧 Updating environment variables..."
aws lambda update-function-configuration \
    --function-name bella-voice-app \
    --environment file://lambda-env-update.json \
    --region us-east-1

echo "✅ Production Lambda deployed successfully!"
echo "🧪 Testing the deployment..."

# Test the deployment
sleep 10

echo "Testing health check..."
curl -s "https://bhcnf2i6eh3bxnr6lrnt4ubouy0obfjy.lambda-url.us-east-1.on.aws/"

echo -e "\n\n🎉 Production deployment complete!"
echo "📞 Your voice app now has:"
echo "   ✅ Multi-step conversation flow"
echo "   ✅ Caller ID recognition"
echo "   ✅ Calendar availability checking"
echo "   ✅ Session persistence with Redis"
echo "   ✅ PostgreSQL database integration"
echo "   ✅ Google Calendar integration"
echo ""
echo "🔗 Lambda URL: https://bhcnf2i6eh3bxnr6lrnt4ubouy0obfjy.lambda-url.us-east-1.on.aws/"
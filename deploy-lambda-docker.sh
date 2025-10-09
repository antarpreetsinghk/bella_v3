#!/bin/bash
set -e

echo "🚀 Deploying Docker-built Lambda package..."

# Build dependencies with Docker
./build-lambda-deps.sh

# Test the built dependencies locally
echo "🧪 Testing built dependencies..."
python3 test-docker-deps.py

if [ $? -ne 0 ]; then
    echo "❌ Local testing failed! Aborting deployment."
    exit 1
fi

# Deploy to AWS Lambda
echo "☁️ Deploying to AWS Lambda..."
aws lambda update-function-code \
    --function-name bella-voice-app \
    --zip-file fileb://bella-lambda-docker-built.zip \
    --region us-east-1

echo "✅ Deployment completed!"

# Wait a moment for Lambda to process the update
sleep 5

# Test the deployed function
echo "🧪 Testing deployed function..."
echo "Testing health endpoint:"
curl -s "https://bhcnf2i6eh3bxnr6lrnt4ubouy0obfjy.lambda-url.us-east-1.on.aws/healthz"
echo ""

echo "Testing Twilio webhook endpoint:"
curl -s -X POST "https://bhcnf2i6eh3bxnr6lrnt4ubouy0obfjy.lambda-url.us-east-1.on.aws/twilio/voice" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "From=%2B15559876543&To=%2B15559876543&CallSid=TEST_CALL_123"
echo ""

echo "🎉 Docker-based deployment complete!"
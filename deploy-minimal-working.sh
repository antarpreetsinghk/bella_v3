#!/bin/bash

# Deploy minimal working Lambda handler
set -e

echo "🚀 Deploying Minimal Working Lambda Handler"
echo "==========================================="

# Clean up previous deployment
rm -rf lambda-minimal-working
mkdir -p lambda-minimal-working

# Copy minimal handler
cp minimal_handler.py lambda-minimal-working/handler.py

# Create minimal requirements
cat > lambda-minimal-working/requirements.txt << EOF
google-api-python-client==2.100.0
google-auth==2.41.1
google-auth-httplib2==0.1.0
EOF

echo "📦 Installing minimal dependencies..."
cd lambda-minimal-working

# Install dependencies
pip install -r requirements.txt -t .

# Create deployment package
echo "📦 Creating deployment package..."
zip -r ../lambda-minimal-working.zip . -x "*.pyc" "__pycache__/*" "*.dist-info/*"

cd ..

# Upload to Lambda
echo "🚀 Updating Lambda function..."
aws lambda update-function-code \
    --function-name bella-voice-app \
    --zip-file fileb://lambda-minimal-working.zip \
    --region us-east-1

echo "✅ Minimal working Lambda deployed successfully!"
echo "🧪 Testing the deployment..."

# Test the deployment
sleep 5
curl -s "https://bhcnf2i6eh3bxnr6lrnt4ubouy0obfjy.lambda-url.us-east-1.on.aws/"

echo -e "\n🎉 Deployment complete!"
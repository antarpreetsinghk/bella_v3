#!/bin/bash
# Quick deployment script for urgent fixes

echo "🚀 Quick Fix Deployment for Call Flow..."

# Build and deploy on EC2 directly
ssh -i ~/.ssh/bella-voice-app -o StrictHostKeyChecking=no ubuntu@15.157.56.64 << 'EOF'
cd ~/bella_v3

# Pull latest code
git pull origin main

# Stop containers
sudo docker-compose -f docker-compose.prod.yml down

# Rebuild with latest code
sudo docker-compose -f docker-compose.prod.yml build --no-cache

# Start containers
sudo docker-compose -f docker-compose.prod.yml up -d

# Wait and check health
sleep 30
curl -f http://localhost:8000/healthz && echo "✅ Health check passed"

# Test webhook
curl -s -X POST "http://localhost:80/twilio/voice" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "CallSid=TEST_FIX&From=%2B14382565719" | head -1

echo "🎉 Quick fix deployment complete!"
EOF
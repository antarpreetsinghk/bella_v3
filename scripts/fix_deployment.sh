#!/bin/bash
# Quick Fix Script for Deployment
# Run this to restart your EC2 deployment

set -e

EC2_IP="15.157.56.64"
AWS_REGION="ca-central-1"

echo "🚀 VoiceFlow API Deployment Fix Script"
echo "======================================"
echo ""

# Check if AWS CLI is installed and configured
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found"
    echo ""
    echo "📋 Manual Fix Steps:"
    echo "===================="
    echo ""
    echo "1. Go to AWS Console: https://ca-central-1.console.aws.amazon.com/ec2/home?region=ca-central-1#Instances:"
    echo ""
    echo "2. Find your instance (IP: 15.157.56.64 or tag: bella-v3)"
    echo ""
    echo "3. Check instance state:"
    echo "   • If STOPPED → Right-click → Start Instance"
    echo "   • If TERMINATED → You need to redeploy (run CI/CD pipeline)"
    echo "   • If RUNNING but unreachable → Check security groups"
    echo ""
    echo "4. Wait 2-3 minutes for instance to boot"
    echo ""
    echo "5. Test health endpoint:"
    echo "   curl http://15.157.56.64:8000/healthz"
    echo ""
    echo "6. If still not working, check security group:"
    echo "   • Port 8000: Open to 0.0.0.0/0 (HTTP)"
    echo "   • Port 22: Open to your IP (SSH)"
    echo ""
    exit 1
fi

echo "✅ AWS CLI found"
echo ""

# Try to find the EC2 instance
echo "🔍 Searching for EC2 instance..."

INSTANCE_ID=$(aws ec2 describe-instances \
    --region $AWS_REGION \
    --filters "Name=ip-address,Values=$EC2_IP" "Name=instance-state-name,Values=running,stopped" \
    --query 'Reservations[0].Instances[0].InstanceId' \
    --output text 2>&1 || echo "NOT_FOUND")

if [[ "$INSTANCE_ID" == "NOT_FOUND" ]] || [[ "$INSTANCE_ID" == "None" ]]; then
    echo "❌ Cannot find EC2 instance with IP $EC2_IP"
    echo ""
    echo "💡 Possible reasons:"
    echo "   1. Instance was terminated"
    echo "   2. IP address changed (Elastic IP not assigned)"
    echo "   3. Instance is in different region"
    echo "   4. AWS credentials not configured"
    echo ""
    echo "🔧 To find your instance:"
    aws ec2 describe-instances \
        --region $AWS_REGION \
        --filters "Name=tag:Name,Values=*bella*" \
        --query 'Reservations[*].Instances[*].[InstanceId,State.Name,PublicIpAddress,Tags[?Key==`Name`].Value|[0]]' \
        --output table 2>&1 || echo "Error querying instances"
    echo ""
    exit 1
fi

echo "✅ Found instance: $INSTANCE_ID"

# Check instance state
INSTANCE_STATE=$(aws ec2 describe-instances \
    --region $AWS_REGION \
    --instance-ids $INSTANCE_ID \
    --query 'Reservations[0].Instances[0].State.Name' \
    --output text)

echo "📊 Current state: $INSTANCE_STATE"
echo ""

if [[ "$INSTANCE_STATE" == "running" ]]; then
    echo "✅ Instance is already running!"
    echo ""
    echo "🔍 But not responding to HTTP requests. Checking further..."
    echo ""
    echo "💡 Possible causes:"
    echo "   1. Docker containers are stopped"
    echo "   2. Security group blocking port 8000"
    echo "   3. Application crashed"
    echo ""
    echo "🔧 Next steps:"
    echo "   1. SSH into server: ssh -i ~/.ssh/bella-voice-app ubuntu@$EC2_IP"
    echo "   2. Check containers: docker ps -a"
    echo "   3. Restart if needed: docker-compose up -d"
    echo ""

elif [[ "$INSTANCE_STATE" == "stopped" ]]; then
    echo "⚠️  Instance is STOPPED"
    echo ""
    read -p "🚀 Would you like to start it? (y/n): " -n 1 -r
    echo ""

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🚀 Starting instance..."
        aws ec2 start-instances --region $AWS_REGION --instance-ids $INSTANCE_ID > /dev/null

        echo "⏳ Waiting for instance to start (this takes 1-2 minutes)..."
        aws ec2 wait instance-running --region $AWS_REGION --instance-ids $INSTANCE_ID

        echo "✅ Instance started!"
        echo ""
        echo "⏳ Waiting an additional 30 seconds for application to boot..."
        sleep 30

        echo ""
        echo "🧪 Testing health endpoint..."
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 "http://$EC2_IP:8000/healthz" || echo "000")

        if [[ "$HTTP_CODE" == "200" ]]; then
            echo "✅ SUCCESS! Application is now responding!"
            echo ""
            echo "📍 Your API is live at:"
            echo "   • Docs: http://$EC2_IP:8000/docs"
            echo "   • Redoc: http://$EC2_IP:8000/redoc"
            echo "   • Health: http://$EC2_IP:8000/healthz"
            echo "   • LLM Demo: http://$EC2_IP:8000/llm-demo/status"
        else
            echo "⚠️  Instance started but application not responding (HTTP $HTTP_CODE)"
            echo ""
            echo "🔧 Manual intervention needed:"
            echo "   ssh -i ~/.ssh/bella-voice-app ubuntu@$EC2_IP"
            echo "   cd ~/bella_v3"
            echo "   docker-compose -f docker-compose.cost-optimized.yml up -d"
        fi
    else
        echo "❌ User cancelled. Instance remains stopped."
    fi

elif [[ "$INSTANCE_STATE" == "terminated" ]]; then
    echo "❌ Instance has been TERMINATED"
    echo ""
    echo "💡 You need to redeploy from scratch:"
    echo "   1. Push code to GitHub"
    echo "   2. GitHub Actions will deploy to new EC2"
    echo "   3. Update IP address in README.md"
    echo ""

else
    echo "⚠️  Unknown instance state: $INSTANCE_STATE"
fi

echo ""
echo "======================================"

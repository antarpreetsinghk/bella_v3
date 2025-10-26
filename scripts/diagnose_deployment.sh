#!/bin/bash
# Server Diagnostic Script
# Checks EC2 instance, Docker containers, and application health

set -e

EC2_IP="15.157.56.64"
SSH_KEY="$HOME/.ssh/bella-voice-app"
SSH_USER="ubuntu"

echo "🔍 VoiceFlow API Deployment Diagnostic"
echo "======================================="
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Check if EC2 is reachable
echo "📡 Test 1: Checking EC2 Connectivity..."
if ping -c 1 -W 2 $EC2_IP > /dev/null 2>&1; then
    echo -e "${GREEN}✅ EC2 instance is reachable${NC}"
else
    echo -e "${RED}❌ EC2 instance is NOT reachable${NC}"
    echo "   💡 Possible causes:"
    echo "      - EC2 instance is stopped"
    echo "      - Security group blocking ICMP"
    echo "      - Instance terminated"
    echo ""
    echo "   🔧 Fix: Check AWS Console → EC2 → Instances"
    exit 1
fi
echo ""

# Test 2: Check if SSH works
echo "🔐 Test 2: Checking SSH Access..."
if ssh -i "$SSH_KEY" -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$SSH_USER@$EC2_IP" "echo 'SSH OK'" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ SSH access works${NC}"
else
    echo -e "${RED}❌ SSH access FAILED${NC}"
    echo "   💡 Possible causes:"
    echo "      - SSH key not configured"
    echo "      - Security group blocking port 22"
    echo "      - Wrong username (try 'ec2-user' or 'ubuntu')"
    echo ""
    echo "   🔧 Fix: Check security group inbound rules"
    exit 1
fi
echo ""

# Test 3: Check Docker containers
echo "🐳 Test 3: Checking Docker Containers..."
DOCKER_STATUS=$(ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$SSH_USER@$EC2_IP" \
    "docker ps --format '{{.Names}}: {{.Status}}' 2>&1" || echo "DOCKER_ERROR")

if [[ "$DOCKER_STATUS" == *"DOCKER_ERROR"* ]]; then
    echo -e "${RED}❌ Cannot check Docker containers${NC}"
    echo "   💡 Docker might not be installed or not running"
    echo ""
    echo "   🔧 Fix: SSH in and run: sudo systemctl start docker"
elif [[ "$DOCKER_STATUS" == "" ]]; then
    echo -e "${YELLOW}⚠️  No Docker containers running${NC}"
    echo "   💡 Application is not deployed"
    echo ""
    echo "   🔧 Fix: Run deployment script or docker-compose up"
else
    echo -e "${GREEN}✅ Docker containers found:${NC}"
    echo "$DOCKER_STATUS" | while read line; do
        echo "   - $line"
    done
fi
echo ""

# Test 4: Check application health
echo "🏥 Test 4: Checking Application Health..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "http://$EC2_IP:8000/healthz" || echo "000")

if [[ "$HTTP_CODE" == "200" ]]; then
    echo -e "${GREEN}✅ Application is responding (HTTP $HTTP_CODE)${NC}"
    echo "   🎉 Server is HEALTHY!"
    echo ""
    echo "   📍 Live URLs:"
    echo "      - Docs: http://$EC2_IP:8000/docs"
    echo "      - Redoc: http://$EC2_IP:8000/redoc"
    echo "      - Health: http://$EC2_IP:8000/healthz"
elif [[ "$HTTP_CODE" == "000" ]]; then
    echo -e "${RED}❌ Application is NOT responding (timeout/connection refused)${NC}"
    echo "   💡 Possible causes:"
    echo "      - Application container stopped"
    echo "      - Port 8000 blocked in security group"
    echo "      - Application crashed"
    echo ""
    echo "   🔧 Fix: Check container logs and security group"
else
    echo -e "${YELLOW}⚠️  Application responding with HTTP $HTTP_CODE${NC}"
    echo "   💡 Server is running but may have issues"
fi
echo ""

# Test 5: Check security group (requires AWS CLI)
echo "🔒 Test 5: Checking Security Group..."
if command -v aws &> /dev/null; then
    SG_RULES=$(aws ec2 describe-security-groups \
        --filters "Name=ip-permission.from-port,Values=8000" \
        --query 'SecurityGroups[*].IpPermissions[?FromPort==`8000`]' \
        --output text 2>&1 || echo "AWS_CLI_ERROR")

    if [[ "$SG_RULES" == *"AWS_CLI_ERROR"* ]]; then
        echo -e "${YELLOW}⚠️  Cannot check security group (AWS CLI not configured)${NC}"
    elif [[ "$SG_RULES" == *"0.0.0.0/0"* ]]; then
        echo -e "${GREEN}✅ Port 8000 is open to public${NC}"
    else
        echo -e "${RED}❌ Port 8000 may not be accessible${NC}"
        echo "   🔧 Fix: AWS Console → EC2 → Security Groups → Add inbound rule:"
        echo "      Type: Custom TCP"
        echo "      Port: 8000"
        echo "      Source: 0.0.0.0/0 (or your IP)"
    fi
else
    echo -e "${YELLOW}⚠️  AWS CLI not installed (skipping security group check)${NC}"
fi
echo ""

# Summary and recommended actions
echo "======================================="
echo "📋 DIAGNOSTIC SUMMARY"
echo "======================================="
echo ""

if [[ "$HTTP_CODE" == "200" ]]; then
    echo -e "${GREEN}✅ ALL SYSTEMS OPERATIONAL${NC}"
    echo ""
    echo "Your deployment is working! No action needed."
else
    echo -e "${RED}⚠️  DEPLOYMENT ISSUES DETECTED${NC}"
    echo ""
    echo "🔧 RECOMMENDED FIXES (run in order):"
    echo ""
    echo "1. SSH into server:"
    echo "   ssh -i $SSH_KEY $SSH_USER@$EC2_IP"
    echo ""
    echo "2. Check container status:"
    echo "   docker ps -a"
    echo ""
    echo "3. If containers are stopped, restart them:"
    echo "   cd ~/bella_v3"
    echo "   docker-compose -f docker-compose.cost-optimized.yml up -d"
    echo ""
    echo "4. Check application logs:"
    echo "   docker logs bella-app --tail 50"
    echo ""
    echo "5. Verify health endpoint:"
    echo "   curl http://localhost:8000/healthz"
    echo ""
    echo "6. Check security group in AWS Console:"
    echo "   - Ensure port 8000 is open (0.0.0.0/0)"
    echo "   - Ensure port 22 is open for SSH"
fi
echo ""
echo "======================================="

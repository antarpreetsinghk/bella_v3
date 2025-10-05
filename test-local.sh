#!/bin/bash
# Local testing script for cost-optimized deployment

set -e

echo "🧪 Bella V3 - Local Cost-Optimized Testing"
echo "=========================================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check prerequisites
echo "🔍 Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    print_error "Docker not found. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose not found. Please install Docker Compose first."
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    print_error "Python3 not found. Please install Python 3.11+ first."
    exit 1
fi

print_status "Prerequisites check passed"

# Check .env file
if [ ! -f .env ]; then
    print_warning ".env file not found. Creating from template..."
    cp .env.example .env 2>/dev/null || print_error "No .env.example found"
fi

# Warn about configuration
print_warning "Important: Update your .env file with actual API keys:"
echo "  - OPENAI_API_KEY (required for speech processing)"
echo "  - TWILIO_ACCOUNT_SID (required for voice calls)"
echo "  - TWILIO_AUTH_TOKEN (required for voice calls)"
echo "  - TWILIO_PHONE_NUMBER (required for voice calls)"
echo ""
read -p "Have you updated your .env file with real API keys? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_warning "Please update .env file before continuing. The system will work but voice calls will fail without real Twilio credentials."
fi

# Initialize database
print_status "Initializing SQLite database..."
mkdir -p data logs/calls
python3 init_db.py

# Stop any existing containers
print_status "Stopping any existing containers..."
docker-compose -f docker-compose.cost-optimized.yml down 2>/dev/null || true

# Build the application
print_status "Building cost-optimized containers..."
docker build -f Dockerfile.cost-optimized -t bella-v3:cost-optimized .

# Start services
print_status "Starting services..."
docker-compose -f docker-compose.cost-optimized.yml up -d

# Wait for services
print_status "Waiting for services to start..."
sleep 30

# Health checks
echo ""
echo "🏥 Running health checks..."

# Check if containers are running
if ! docker-compose -f docker-compose.cost-optimized.yml ps | grep -q "Up"; then
    print_error "Containers failed to start"
    docker-compose -f docker-compose.cost-optimized.yml logs
    exit 1
fi

print_status "Containers are running"

# Check Redis
if ! docker exec bella-redis redis-cli ping | grep -q "PONG"; then
    print_error "Redis health check failed"
    exit 1
fi

print_status "Redis is healthy"

# Check application health
if ! curl -f http://localhost:8000/healthz &>/dev/null; then
    print_error "Application health check failed"
    echo "Application logs:"
    docker-compose -f docker-compose.cost-optimized.yml logs app | tail -20
    exit 1
fi

print_status "Application is healthy"

# Check database
if ! curl -f http://localhost:8000/readyz &>/dev/null; then
    print_warning "Database readiness check failed (this may be normal for first startup)"
else
    print_status "Database is ready"
fi

# Test basic endpoints
echo ""
echo "🔧 Testing endpoints..."

# Test health endpoint
HEALTH_RESPONSE=$(curl -s http://localhost:8000/healthz)
if echo "$HEALTH_RESPONSE" | grep -q "ok"; then
    print_status "Health endpoint working"
else
    print_error "Health endpoint failed: $HEALTH_RESPONSE"
fi

# Test Twilio webhook simulation
TWILIO_RESPONSE=$(curl -s -X POST http://localhost:8000/twilio/voice \
    -d "CallSid=test123&From=+15551234567" \
    -H "Content-Type: application/x-www-form-urlencoded")

if echo "$TWILIO_RESPONSE" | grep -q "Response"; then
    print_status "Twilio webhook endpoint working"
else
    print_warning "Twilio webhook test failed (may need real Twilio signature)"
fi

# Display results
echo ""
echo "🎉 Local deployment test complete!"
echo "=================================="
echo ""
echo "📊 Service Status:"
docker-compose -f docker-compose.cost-optimized.yml ps

echo ""
echo "🌐 Access URLs:"
echo "  • Application: http://localhost:8000"
echo "  • Health Check: http://localhost:8000/healthz"
echo "  • Admin Dashboard: http://localhost:8000/"
echo "  • API Docs: http://localhost:8000/docs"

echo ""
echo "🔧 Useful Commands:"
echo "  • View logs: docker-compose -f docker-compose.cost-optimized.yml logs -f"
echo "  • Stop services: docker-compose -f docker-compose.cost-optimized.yml down"
echo "  • Restart: docker-compose -f docker-compose.cost-optimized.yml restart"
echo "  • Analyze calls: python3 tools/analyze_calls.py"

echo ""
echo "📞 Next Steps for Production:"
echo "  1. Get an EC2 t4g.micro instance"
echo "  2. Copy this project to EC2"
echo "  3. Update DOMAIN in .env"
echo "  4. Run: ./deploy.sh"
echo "  5. Configure Twilio webhook: https://your-domain.com/twilio/voice"

echo ""
print_status "Ready for production deployment!"

# Ask if user wants to test call flow
read -p "🧪 Would you like to test the call flow locally? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [ -f "tools/call_flow_tester.py" ]; then
        python3 tools/call_flow_tester.py
    else
        print_warning "Call flow tester not found"
    fi
fi
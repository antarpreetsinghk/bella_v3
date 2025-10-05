# 🚀 Step-by-Step Execution Guide - Cost-Optimized Deployment

## ✅ **Completed Steps (Done by Claude)**

### Step 1: Environment Configuration ✅
- Updated `.env` with secure defaults
- Configured SQLite database path: `sqlite+aiosqlite:///./data/bella.db`
- Set Local Redis URL: `redis://redis:6379/0`
- Google Calendar integration ready
- Security credentials configured

### Step 2: Files Created ✅
- `docker-compose.cost-optimized.yml` - Single EC2 deployment
- `Dockerfile.cost-optimized` - Optimized container
- `nginx.conf` - Reverse proxy with security
- `init_db.py` - Database initialization
- `test-local.sh` - Testing script
- Cost optimization documentation

## 🎯 **Next Steps (For You to Execute)**

### Step 3: Build Docker Containers

**Run these commands on your machine:**

```bash
# Navigate to project directory
cd /path/to/bella_v3

# Build the cost-optimized image
docker build -f Dockerfile.cost-optimized -t bella-v3:cost-optimized .

# This will:
# - Install Python 3.11 and dependencies
# - Copy application code
# - Create necessary directories
# - Set up health checks
```

**Expected Output:**
```
Successfully built [container_id]
Successfully tagged bella-v3:cost-optimized
```

### Step 4: Start Services with Docker Compose

```bash
# Start all services in background
docker-compose -f docker-compose.cost-optimized.yml up -d

# This starts:
# - bella-app (FastAPI application)
# - bella-redis (Local Redis for sessions)
# - bella-nginx (Reverse proxy)
```

**Expected Output:**
```
Creating network "bella_v3_bella-network" with driver "bridge"
Creating volume "bella_v3_redis_data" with local driver
Creating bella-redis ... done
Creating bella-app   ... done
Creating bella-nginx ... done
```

### Step 5: Run Health Checks

```bash
# Check container status
docker-compose -f docker-compose.cost-optimized.yml ps

# Test health endpoints
curl http://localhost:8000/healthz
curl http://localhost:8000/readyz

# Check Redis
docker exec bella-redis redis-cli ping
```

**Expected Output:**
```
{"ok": true}                    # Health check
{"db": "ok"}                   # Database ready
PONG                           # Redis working
```

### Step 6: Test Key Endpoints

```bash
# Test Twilio webhook simulation
curl -X POST http://localhost:8000/twilio/voice \
  -d "CallSid=test123&From=+15551234567" \
  -H "Content-Type: application/x-www-form-urlencoded"

# Test admin dashboard
curl http://localhost:8000/

# Test API documentation
curl http://localhost:8000/docs
```

## 🧪 **Automated Testing Script**

**Run the complete test:**
```bash
# Make executable and run
chmod +x test-local.sh
./test-local.sh

# This will:
# 1. Check prerequisites
# 2. Initialize database
# 3. Build containers
# 4. Start services
# 5. Run health checks
# 6. Test endpoints
# 7. Show results
```

## 🔧 **Troubleshooting Commands**

### View Logs
```bash
# All services
docker-compose -f docker-compose.cost-optimized.yml logs -f

# Specific service
docker-compose -f docker-compose.cost-optimized.yml logs app
docker-compose -f docker-compose.cost-optimized.yml logs redis
docker-compose -f docker-compose.cost-optimized.yml logs nginx
```

### Restart Services
```bash
# Restart all
docker-compose -f docker-compose.cost-optimized.yml restart

# Restart specific service
docker-compose -f docker-compose.cost-optimized.yml restart app
```

### Stop and Clean Up
```bash
# Stop services
docker-compose -f docker-compose.cost-optimized.yml down

# Remove volumes (careful - deletes data!)
docker-compose -f docker-compose.cost-optimized.yml down -v
```

## 📊 **Expected Performance**

### Resource Usage (Single EC2 t4g.micro)
- **Memory**: ~300-400MB total
- **CPU**: <50% during normal operation
- **Disk**: ~2GB for application + logs
- **Network**: Minimal for 50 calls/day

### Response Times
- **Health Check**: <100ms
- **Voice Webhook**: <2 seconds
- **Calendar Check**: <1 second
- **Database Query**: <50ms

## 🎯 **Success Criteria**

✅ **All containers running healthy**
✅ **Health endpoints responding**
✅ **Redis accepting connections**
✅ **Database initialized with tables**
✅ **Twilio webhook responding with TwiML**
✅ **Admin dashboard accessible**

## 🚀 **After Local Testing Success**

### Deploy to EC2 Production
```bash
# On EC2 instance
export DOMAIN="your-domain.com"
export EMAIL="admin@your-domain.com"

# Run deployment
./deploy.sh

# Configure Twilio webhook
# URL: https://your-domain.com/twilio/voice
```

### Monitor Production
```bash
# Check status
./monitor.sh

# Analyze calls
python3 tools/analyze_calls.py --weekly

# View live logs
docker-compose -f docker-compose.cost-optimized.yml logs -f app
```

## 💰 **Cost Verification**

### Expected Monthly Costs
- **EC2 t4g.micro**: $6.00
- **Storage**: $1.60
- **Twilio**: $15.00 (50 calls/day)
- **OpenAI**: $1.00
- **Total**: **~$25/month**

### Cost Monitoring
```bash
# Check resource usage
docker stats

# Analyze call costs
python3 tools/analyze_calls.py --cost-analysis
```

---

**🎉 You're ready to execute! Start with `./test-local.sh` for automated testing.**
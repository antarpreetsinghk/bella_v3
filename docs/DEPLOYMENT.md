# Bella V3 Production Deployment Guide

> **Complete guide for deploying Bella V3 to production**
> Enterprise-grade deployment with monitoring, security, and scalability

## 🎯 Deployment Overview

### Deployment Architecture
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Load Balancer │───▶│   Bella V3       │───▶│   PostgreSQL    │
│   (Nginx/ALB)   │    │   Production     │    │   Database      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │   Redis Cache    │
                       │   Session Store  │
                       └──────────────────┘

External Services:
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Twilio        │    │   OpenAI API     │    │   AWS Services  │
│   Voice/SMS     │    │   Whisper STT    │    │   Cost Explorer │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Production Requirements
- **Server**: 4 CPU cores, 8GB RAM, 100GB SSD
- **Database**: PostgreSQL 14+
- **Cache**: Redis 6+
- **Load Balancer**: Nginx or AWS ALB
- **SSL Certificate**: Let's Encrypt or AWS Certificate Manager
- **Monitoring**: Recommended external monitoring service

---

## 📋 Pre-Deployment Checklist

### Infrastructure Requirements
- [ ] Production server provisioned (4 CPU, 8GB RAM, 100GB SSD)
- [ ] Domain name configured with DNS
- [ ] SSL certificate obtained
- [ ] PostgreSQL database server ready
- [ ] Redis server configured
- [ ] Load balancer configured (if multiple instances)
- [ ] Firewall rules configured (ports 80, 443, 22)

### Security Requirements
- [ ] Strong production API key generated (64+ characters)
- [ ] All secrets stored securely (not in code)
- [ ] Twilio webhook signature validation enabled
- [ ] Database access restricted to application server
- [ ] SSH key-based authentication configured
- [ ] Backup strategy implemented

### External Services
- [ ] OpenAI API key with production billing
- [ ] Twilio production account with phone number
- [ ] Slack workspace for alerts (optional)
- [ ] SMTP service for email alerts (optional)
- [ ] AWS account for cost tracking (optional)

---

## 🔧 Environment Configuration

### Production Environment Variables
Create `/opt/bella/production.env`:

```bash
# Core Application
BELLA_API_KEY="YOUR_64_CHARACTER_PRODUCTION_API_KEY"
APP_ENV="production"
DATABASE_URL="postgresql+asyncpg://bella_user:secure_password@localhost:5432/bella_prod"

# External Services
OPENAI_API_KEY="sk-YOUR_PRODUCTION_OPENAI_KEY"
TWILIO_ACCOUNT_SID="AC_YOUR_PRODUCTION_ACCOUNT_SID"
TWILIO_AUTH_TOKEN="YOUR_PRODUCTION_AUTH_TOKEN"

# Session Storage
REDIS_URL="redis://localhost:6379/0"

# Alerting Configuration
SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
SMTP_HOST="smtp.gmail.com"
SMTP_PORT="587"
SMTP_USER="alerts@yourcompany.com"
SMTP_PASSWORD="your_app_specific_password"
ALERT_EMAIL="oncall@yourcompany.com"

# Optional: AWS Cost Tracking
AWS_ACCESS_KEY_ID="AKIA_YOUR_ACCESS_KEY"
AWS_SECRET_ACCESS_KEY="YOUR_SECRET_ACCESS_KEY"
AWS_DEFAULT_REGION="us-east-1"

# Production Tuning
WORKERS=4
MAX_REQUESTS=1000
TIMEOUT=30
```

### Generate Secure Keys
```bash
# Generate production API key
openssl rand -hex 32

# Generate database password
openssl rand -base64 32

# Generate session secret
openssl rand -hex 16
```

---

## 🗄️ Database Setup

### PostgreSQL Installation & Configuration
```bash
# Install PostgreSQL
sudo apt update
sudo apt install postgresql postgresql-contrib

# Start and enable PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database and user
sudo -u postgres psql << 'EOF'
CREATE DATABASE bella_prod;
CREATE USER bella_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE bella_prod TO bella_user;
ALTER USER bella_user CREATEDB;
\q
EOF

# Configure PostgreSQL for production
sudo nano /etc/postgresql/14/main/postgresql.conf
# Edit these settings:
# max_connections = 100
# shared_buffers = 256MB
# effective_cache_size = 1GB
# work_mem = 4MB

# Configure authentication
sudo nano /etc/postgresql/14/main/pg_hba.conf
# Add line: local   bella_prod   bella_user   md5

# Restart PostgreSQL
sudo systemctl restart postgresql
```

### Database Schema Initialization
```bash
# Set environment variables
export DATABASE_URL="postgresql+asyncpg://bella_user:secure_password@localhost:5432/bella_prod"

# Initialize database schema
cd /opt/bella
python -c "from app.db.base import init_db; init_db()"

# Verify tables created
psql -h localhost -U bella_user -d bella_prod -c "\dt"
```

---

## 📦 Application Deployment

### Server Preparation
```bash
# Create application directory
sudo mkdir -p /opt/bella
sudo chown $USER:$USER /opt/bella

# Install Python 3.11
sudo apt update
sudo apt install software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt install python3.11 python3.11-venv python3.11-dev

# Install system dependencies
sudo apt install build-essential libpq-dev redis-server nginx supervisor
```

### Application Installation
```bash
# Clone application
cd /opt/bella
git clone https://github.com/yourorg/bella_v3.git .

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Install production WSGI server
pip install gunicorn

# Set up environment file
sudo cp production.env .env
sudo chown bella:bella .env
sudo chmod 600 .env
```

### Create Application User
```bash
# Create dedicated user for application
sudo useradd -r -s /bin/false -d /opt/bella bella
sudo chown -R bella:bella /opt/bella
sudo chmod -R 755 /opt/bella
sudo chmod 600 /opt/bella/.env
```

---

## 🔄 Process Management

### Supervisor Configuration
Create `/etc/supervisor/conf.d/bella.conf`:

```ini
[program:bella]
command=/opt/bella/venv/bin/gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 127.0.0.1:8000 --timeout 30 --max-requests 1000 --preload
directory=/opt/bella
user=bella
autostart=true
autorestart=true
stopasgroup=true
killasgroup=true
stdout_logfile=/var/log/bella/app.log
stderr_logfile=/var/log/bella/error.log
environment=PATH="/opt/bella/venv/bin"

[program:bella-worker]
command=/opt/bella/venv/bin/python -m app.workers.background
directory=/opt/bella
user=bella
autostart=true
autorestart=true
stopasgroup=true
killasgroup=true
stdout_logfile=/var/log/bella/worker.log
stderr_logfile=/var/log/bella/worker-error.log
environment=PATH="/opt/bella/venv/bin"
```

### Log Directory Setup
```bash
# Create log directory
sudo mkdir -p /var/log/bella
sudo chown bella:bella /var/log/bella

# Configure log rotation
sudo tee /etc/logrotate.d/bella << 'EOF'
/var/log/bella/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 bella bella
    postrotate
        supervisorctl restart bella
    endscript
}
EOF
```

### Start Services
```bash
# Reload supervisor configuration
sudo supervisorctl reread
sudo supervisorctl update

# Start Bella application
sudo supervisorctl start bella
sudo supervisorctl start bella-worker

# Check status
sudo supervisorctl status
```

---

## 🌐 Load Balancer Configuration

### Nginx Configuration
Create `/etc/nginx/sites-available/bella`:

```nginx
upstream bella_backend {
    server 127.0.0.1:8000;
    # Add more servers for load balancing:
    # server 127.0.0.1:8001;
    # server 127.0.0.1:8002;
}

# Rate limiting
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=dashboard:10m rate=5r/s;

server {
    listen 80;
    server_name bella.yourcompany.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name bella.yourcompany.com;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/bella.yourcompany.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/bella.yourcompany.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";

    # Logging
    access_log /var/log/nginx/bella_access.log;
    error_log /var/log/nginx/bella_error.log;

    # Main application
    location / {
        limit_req zone=dashboard burst=10 nodelay;
        proxy_pass http://bella_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 30s;
        proxy_connect_timeout 5s;
    }

    # API endpoints with higher rate limits
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://bella_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
        proxy_connect_timeout 10s;
    }

    # Twilio webhooks - no rate limiting
    location /twilio/ {
        proxy_pass http://bella_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 30s;
        proxy_connect_timeout 5s;

        # Allow Twilio IPs only (optional)
        # allow 54.172.60.0/23;
        # allow 54.244.51.0/24;
        # deny all;
    }

    # Health checks
    location /healthz {
        proxy_pass http://bella_backend;
        access_log off;
    }

    # Static files (if any)
    location /static/ {
        alias /opt/bella/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### Enable Nginx Site
```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/bella /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Start and enable Nginx
sudo systemctl start nginx
sudo systemctl enable nginx
```

---

## 🔒 SSL Certificate Setup

### Let's Encrypt with Certbot
```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d bella.yourcompany.com

# Test automatic renewal
sudo certbot renew --dry-run

# Set up automatic renewal
sudo systemctl enable certbot.timer
```

### Manual Certificate (Alternative)
If using a purchased certificate:
```bash
# Copy certificate files
sudo cp your-certificate.crt /etc/ssl/certs/bella.crt
sudo cp your-private-key.key /etc/ssl/private/bella.key
sudo chown root:root /etc/ssl/certs/bella.crt /etc/ssl/private/bella.key
sudo chmod 644 /etc/ssl/certs/bella.crt
sudo chmod 600 /etc/ssl/private/bella.key

# Update Nginx configuration to use these files
```

---

## 📊 Monitoring Setup

### External Health Monitoring
Create `/opt/bella/scripts/health_check.sh`:

```bash
#!/bin/bash
# External health monitoring script

API_KEY="your-production-api-key"
BASE_URL="https://bella.yourcompany.com"
SLACK_WEBHOOK="your-slack-webhook-url"

# Function to send alert
send_alert() {
    local message="$1"
    local status="$2"

    curl -X POST -H 'Content-type: application/json' \
        --data "{\"text\":\"🚨 Bella Production Alert: $message (Status: $status)\"}" \
        "$SLACK_WEBHOOK"
}

# Check basic health
health_response=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/healthz")
if [ "$health_response" != "200" ]; then
    send_alert "Health check failed" "$health_response"
    exit 1
fi

# Check API authentication
api_response=$(curl -s -H "X-API-Key: $API_KEY" -o /dev/null -w "%{http_code}" "$BASE_URL/api/unified/status")
if [ "$api_response" != "200" ]; then
    send_alert "API authentication failed" "$api_response"
    exit 1
fi

# Check SLA metrics
sla_score=$(curl -s -H "X-API-Key: $API_KEY" "$BASE_URL/api/unified/sla-metrics" | jq -r '.overall_health_score // 0')
if (( $(echo "$sla_score < 95" | bc -l) )); then
    send_alert "SLA score below 95%" "$sla_score%"
fi

echo "Health check passed - SLA: $sla_score%"
```

### Cron Job for Monitoring
```bash
# Make script executable
chmod +x /opt/bella/scripts/health_check.sh

# Add to cron (check every 5 minutes)
sudo crontab -e
# Add line:
# */5 * * * * /opt/bella/scripts/health_check.sh >> /var/log/bella/health_check.log 2>&1
```

### System Resource Monitoring
Create `/opt/bella/scripts/resource_monitor.sh`:

```bash
#!/bin/bash
# System resource monitoring

# Check disk space
disk_usage=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$disk_usage" -gt 80 ]; then
    echo "WARNING: Disk usage at $disk_usage%"
fi

# Check memory usage
memory_usage=$(free | awk '/Mem:/ {printf "%.0f", $3/$2 * 100}')
if [ "$memory_usage" -gt 80 ]; then
    echo "WARNING: Memory usage at $memory_usage%"
fi

# Check CPU load
cpu_load=$(uptime | awk -F'load average:' '{ print $2 }' | cut -d, -f1 | xargs)
if (( $(echo "$cpu_load > 2.0" | bc -l) )); then
    echo "WARNING: High CPU load: $cpu_load"
fi

# Check application process
if ! pgrep -f "gunicorn.*bella" > /dev/null; then
    echo "ERROR: Bella application not running"
    sudo supervisorctl restart bella
fi
```

---

## 🔧 Twilio Production Configuration

### Webhook URL Configuration
1. **Login to Twilio Console**: https://console.twilio.com/
2. **Navigate to Phone Numbers**: Phone Numbers → Manage → Active numbers
3. **Select your production number**
4. **Configure webhook**:
   - **Voice URL**: `https://bella.yourcompany.com/twilio/voice`
   - **HTTP Method**: `POST`
   - **Voice Method**: `POST`

### Production Voice Flow Testing
```bash
# Test webhook endpoint directly
curl -X POST "https://bella.yourcompany.com/twilio/voice" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "CallSid=CA1234567890&From=%2B1234567890&To=%2B0987654321"

# Should return TwiML XML response
```

---

## ✅ Production Validation

### Deployment Validation Checklist

#### System Health
```bash
# 1. Check application status
sudo supervisorctl status

# 2. Test health endpoints
curl https://bella.yourcompany.com/healthz
curl -H "X-API-Key: $API_KEY" https://bella.yourcompany.com/api/unified/status

# 3. Verify database connectivity
curl -H "X-API-Key: $API_KEY" https://bella.yourcompany.com/readyz

# 4. Check Redis connectivity
redis-cli ping

# 5. Test circuit breakers
curl -H "X-API-Key: $API_KEY" https://bella.yourcompany.com/api/unified/circuit-breakers
```

#### Dashboard Access
- [ ] Dashboard loads at https://bella.yourcompany.com/
- [ ] API key authentication works
- [ ] All 3 tabs load (Operations, Analytics, System)
- [ ] Real-time metrics display correctly
- [ ] No JavaScript errors in browser console

#### Voice Call Testing
- [ ] Test call to production Twilio number
- [ ] Webhook receives and processes calls
- [ ] Speech recognition works correctly
- [ ] Appointment extraction functions
- [ ] Database stores appointments correctly

#### Alerting System
```bash
# Test manual alert creation
curl -X POST -H "X-API-Key: $API_KEY" \
     -H "Content-Type: application/json" \
     -d '{
       "component": "production_test",
       "severity": "medium",
       "message": "Production deployment test alert"
     }' \
     https://bella.yourcompany.com/api/unified/alerts

# Verify alert appears in dashboard
curl -H "X-API-Key: $API_KEY" https://bella.yourcompany.com/api/unified/alerts

# Check if Slack notification was sent (if configured)
```

#### Performance Testing
```bash
# Load test with curl
for i in {1..10}; do
    curl -H "X-API-Key: $API_KEY" https://bella.yourcompany.com/api/unified/status &
done
wait

# Check response times
curl -w "@curl-format.txt" -H "X-API-Key: $API_KEY" https://bella.yourcompany.com/api/unified/business-metrics

# Create curl-format.txt:
cat > curl-format.txt << 'EOF'
     time_namelookup:  %{time_namelookup}\n
        time_connect:  %{time_connect}\n
     time_appconnect:  %{time_appconnect}\n
    time_pretransfer:  %{time_pretransfer}\n
       time_redirect:  %{time_redirect}\n
  time_starttransfer:  %{time_starttransfer}\n
                     ----------\n
          time_total:  %{time_total}\n
EOF
```

---

## 🔄 Backup and Recovery

### Database Backup Setup
```bash
# Create backup script
sudo tee /opt/bella/scripts/backup_db.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/bella/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="bella_prod"
DB_USER="bella_user"

mkdir -p $BACKUP_DIR

# Create backup
pg_dump -h localhost -U $DB_USER -d $DB_NAME | gzip > $BACKUP_DIR/bella_backup_$DATE.sql.gz

# Keep only last 30 days of backups
find $BACKUP_DIR -name "bella_backup_*.sql.gz" -mtime +30 -delete

echo "Backup completed: bella_backup_$DATE.sql.gz"
EOF

# Make executable
chmod +x /opt/bella/scripts/backup_db.sh

# Add to cron (daily at 2 AM)
sudo crontab -e
# Add line:
# 0 2 * * * /opt/bella/scripts/backup_db.sh >> /var/log/bella/backup.log 2>&1
```

### Application Backup
```bash
# Create application backup script
sudo tee /opt/bella/scripts/backup_app.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/bella/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup application code and configuration
tar -czf $BACKUP_DIR/bella_app_$DATE.tar.gz \
    --exclude=venv \
    --exclude=__pycache__ \
    --exclude=*.pyc \
    /opt/bella/

# Keep only last 7 days of app backups
find $BACKUP_DIR -name "bella_app_*.tar.gz" -mtime +7 -delete

echo "Application backup completed: bella_app_$DATE.tar.gz"
EOF

chmod +x /opt/bella/scripts/backup_app.sh
```

---

## 🚨 Emergency Procedures

### Rollback Plan
```bash
# 1. Stop current application
sudo supervisorctl stop bella bella-worker

# 2. Restore previous version
cd /opt/bella
git checkout previous-stable-tag

# 3. Restore environment if needed
cp .env.backup .env

# 4. Restart application
sudo supervisorctl start bella bella-worker

# 5. Verify health
curl https://bella.yourcompany.com/healthz
```

### Database Recovery
```bash
# Stop application
sudo supervisorctl stop bella bella-worker

# Restore database from backup
gunzip -c /opt/bella/backups/bella_backup_YYYYMMDD_HHMMSS.sql.gz | \
    psql -h localhost -U bella_user -d bella_prod

# Restart application
sudo supervisorctl start bella bella-worker
```

### Emergency Contacts
```
Primary On-Call: [Your contact]
Database Admin: [DBA contact]
Infrastructure: [Infrastructure team]
Emergency Escalation: [Manager contact]

Vendor Support:
- OpenAI: https://help.openai.com/
- Twilio: https://support.twilio.com/
- AWS: https://aws.amazon.com/support/
```

---

## 📋 Post-Deployment Tasks

### Day 1 Tasks
- [ ] Monitor application for 24 hours
- [ ] Verify all alerting channels work
- [ ] Test voice call flow multiple times
- [ ] Check cost tracking is active
- [ ] Review all logs for errors
- [ ] Test backup and restore procedures

### Week 1 Tasks
- [ ] Performance optimization based on real usage
- [ ] Fine-tune alerting thresholds
- [ ] Update monitoring scripts based on patterns
- [ ] Document any custom configurations
- [ ] Train operations team on procedures

### Month 1 Tasks
- [ ] Review cost optimization recommendations
- [ ] Analyze performance trends and optimize
- [ ] Update capacity planning based on usage
- [ ] Review and update backup retention policies
- [ ] Conduct disaster recovery test

---

**🎯 Production Deployment Complete!**

Your Bella V3 system is now deployed and ready for production use with enterprise-grade monitoring, alerting, and operational procedures.

For ongoing maintenance, refer to the [Operations Runbook](./OPERATIONS.md).

*Last Updated: 2025-09-30*
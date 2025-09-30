# 🚀 Bella V3 Production Deployment Guide

> **Complete step-by-step guide for deploying Bella V3 to production**
> From server setup to go-live with comprehensive monitoring

## 📋 Pre-Deployment Checklist

### Infrastructure Requirements ✅
- [ ] **Server**: Ubuntu 20.04+ with 4 CPU cores, 8GB RAM, 100GB SSD
- [ ] **Domain**: Registered domain with DNS configured
- [ ] **SSL Certificate**: Let's Encrypt or purchased certificate
- [ ] **Database**: PostgreSQL 14+ server (local or managed)
- [ ] **Cache**: Redis 6+ server (local or managed)
- [ ] **Firewall**: Ports 80, 443, 22 open

### External Services ✅
- [ ] **OpenAI**: Production API key with billing setup
- [ ] **Twilio**: Production account with phone number purchased
- [ ] **Slack**: Webhook URL for alerts (optional)
- [ ] **Email**: SMTP credentials for alerts (optional)
- [ ] **AWS**: Account for cost tracking (optional)

### Security Requirements ✅
- [ ] **SSH**: Key-based authentication only
- [ ] **API Keys**: Strong production keys generated
- [ ] **Database**: Secure passwords set
- [ ] **Backup**: Strategy and storage configured

---

## 🛠️ Step 1: Server Preparation

### Initial Server Setup
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install essential packages
sudo apt install -y \
    python3.11 python3.11-venv python3.11-dev \
    postgresql-client redis-tools \
    nginx supervisor git curl wget \
    build-essential libpq-dev \
    bc jq htop

# Create bella user
sudo useradd -r -s /bin/false -d /opt/bella bella

# Create directories
sudo mkdir -p /opt/bella /var/log/bella
sudo chown bella:bella /opt/bella /var/log/bella
```

### Security Hardening
```bash
# Configure SSH (disable password auth)
sudo sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo systemctl restart ssh

# Configure firewall
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

# Set up automatic security updates
sudo apt install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

---

## 🗄️ Step 2: Database Setup

### PostgreSQL Installation
```bash
# Install PostgreSQL
sudo apt install postgresql postgresql-contrib

# Start and enable service
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database and user
sudo -u postgres psql << 'EOF'
CREATE DATABASE bella_prod;
CREATE USER bella_user WITH PASSWORD 'your_very_secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE bella_prod TO bella_user;
ALTER USER bella_user CREATEDB;
\q
EOF
```

### PostgreSQL Configuration
```bash
# Edit PostgreSQL configuration
sudo nano /etc/postgresql/14/main/postgresql.conf

# Update these settings:
# max_connections = 100
# shared_buffers = 256MB
# effective_cache_size = 1GB
# work_mem = 4MB
# maintenance_work_mem = 64MB

# Configure authentication
sudo nano /etc/postgresql/14/main/pg_hba.conf
# Add: local   bella_prod   bella_user   md5

# Restart PostgreSQL
sudo systemctl restart postgresql
```

### Redis Setup
```bash
# Install Redis
sudo apt install redis-server

# Configure Redis
sudo nano /etc/redis/redis.conf
# Uncomment: requirepass your_redis_password

# Restart Redis
sudo systemctl restart redis-server
sudo systemctl enable redis-server
```

---

## 📦 Step 3: Application Deployment

### Automated Deployment
```bash
# Download and run deployment script
cd /tmp
wget https://raw.githubusercontent.com/yourorg/bella_v3/main/scripts/production/deploy.sh
chmod +x deploy.sh

# Run deployment (as root)
sudo ./deploy.sh
```

### Manual Deployment (Alternative)
```bash
# Clone application
sudo -u bella git clone https://github.com/yourorg/bella_v3.git /opt/bella

# Create virtual environment
cd /opt/bella
sudo -u bella python3.11 -m venv venv

# Install dependencies
sudo -u bella bash -c "
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    pip install gunicorn
"
```

### Environment Configuration
```bash
# Copy and edit environment file
sudo cp /opt/bella/production.env.template /opt/bella/production.env
sudo nano /opt/bella/production.env

# Set secure permissions
sudo chown bella:bella /opt/bella/production.env
sudo chmod 600 /opt/bella/production.env

# Create symlink
sudo ln -sf production.env /opt/bella/.env
```

**Required Environment Variables:**
```bash
# Generate secure API key
BELLA_API_KEY="$(openssl rand -hex 32)"

# Database connection
DATABASE_URL="postgresql+asyncpg://bella_user:your_password@localhost:5432/bella_prod"

# External services
OPENAI_API_KEY="sk-your-production-key"
TWILIO_ACCOUNT_SID="ACyour-account-sid"
TWILIO_AUTH_TOKEN="your-auth-token"

# Redis
REDIS_URL="redis://:your_redis_password@localhost:6379/0"

# Alerting (optional)
SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
SMTP_HOST="smtp.gmail.com"
SMTP_PORT="587"
SMTP_USER="alerts@yourcompany.com"
SMTP_PASSWORD="your-app-password"
ALERT_EMAIL="oncall@yourcompany.com"
```

### Database Initialization
```bash
# Initialize database schema
cd /opt/bella
sudo -u bella bash -c "
    source venv/bin/activate
    source production.env
    python -c 'from app.db.base import init_db; init_db()'
"
```

---

## 🔄 Step 4: Process Management

### Supervisor Configuration
```bash
# Create supervisor config
sudo tee /etc/supervisor/conf.d/bella.conf << 'EOF'
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
EOF

# Start services
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start bella bella-worker
```

---

## 🌐 Step 5: Load Balancer Setup

### Nginx Configuration
```bash
# Create Nginx site configuration
sudo tee /etc/nginx/sites-available/bella << 'EOF'
upstream bella_backend {
    server 127.0.0.1:8000;
}

limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=dashboard:10m rate=5r/s;

server {
    listen 80;
    server_name bella.yourcompany.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name bella.yourcompany.com;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/bella.yourcompany.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/bella.yourcompany.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";

    location / {
        limit_req zone=dashboard burst=10 nodelay;
        proxy_pass http://bella_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://bella_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /twilio/ {
        proxy_pass http://bella_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /healthz {
        proxy_pass http://bella_backend;
        access_log off;
    }
}
EOF

# Enable site
sudo ln -s /etc/nginx/sites-available/bella /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## 🔒 Step 6: SSL Certificate

### Let's Encrypt (Recommended)
```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d bella.yourcompany.com

# Verify auto-renewal
sudo certbot renew --dry-run
```

### Verification
```bash
# Test SSL
curl -I https://bella.yourcompany.com/healthz

# Check certificate
openssl s_client -connect bella.yourcompany.com:443 -servername bella.yourcompany.com
```

---

## 📊 Step 7: Monitoring Setup

### Health Monitoring
```bash
# Copy health monitoring script
sudo cp /opt/bella/scripts/production/health_monitor.sh /usr/local/bin/bella-health-check
sudo chmod +x /usr/local/bin/bella-health-check

# Add to cron (every 5 minutes)
sudo crontab -e
# Add: */5 * * * * /usr/local/bin/bella-health-check >> /var/log/bella/health_check.log 2>&1
```

### Backup Setup
```bash
# Copy backup script
sudo cp /opt/bella/scripts/production/backup.sh /usr/local/bin/bella-backup
sudo chmod +x /usr/local/bin/bella-backup

# Add to cron (daily at 2 AM)
sudo crontab -e
# Add: 0 2 * * * /usr/local/bin/bella-backup >> /var/log/bella/backup.log 2>&1
```

### Log Rotation
```bash
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
        supervisorctl restart bella bella-worker
    endscript
}
EOF
```

---

## ☎️ Step 8: Twilio Configuration

### Webhook Setup
1. **Login to Twilio Console**: https://console.twilio.com/
2. **Navigate to Phone Numbers**: Phone Numbers → Manage → Active numbers
3. **Select your production number**
4. **Configure webhook**:
   - **Voice URL**: `https://bella.yourcompany.com/twilio/voice`
   - **HTTP Method**: `POST`
   - **Voice Method**: `POST`

### Test Webhook
```bash
# Test webhook endpoint
curl -X POST "https://bella.yourcompany.com/twilio/voice" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "CallSid=CAtest123&From=%2B1234567890&To=%2B0987654321"
```

---

## ✅ Step 9: Production Validation

### System Health Checks
```bash
# 1. Check all services
sudo supervisorctl status

# 2. Test health endpoints
curl https://bella.yourcompany.com/healthz
# Expected: {"ok": true}

curl https://bella.yourcompany.com/readyz
# Expected: {"db": "ok"}

# 3. Test API authentication
curl -H "X-API-Key: your-api-key" https://bella.yourcompany.com/api/unified/status
# Expected: {"system": "healthy", ...}
```

### Dashboard Validation
1. **Open dashboard**: https://bella.yourcompany.com/
2. **Enter API key** when prompted
3. **Verify all tabs load**:
   - 📅 Operations: Shows users and appointments
   - 💰 Analytics: Shows cost tracking
   - ⚡ System: Shows performance metrics
4. **Check for JavaScript errors** in browser console

### Voice Call Testing
1. **Call your Twilio number**
2. **Test voice interaction**: "I need an appointment tomorrow at 2pm"
3. **Verify appointment creation** in dashboard
4. **Check logs for errors**:
   ```bash
   sudo tail -f /var/log/bella/app.log
   ```

### Alerting Validation
```bash
# Test manual alert
curl -X POST -H "X-API-Key: your-api-key" \
     -H "Content-Type: application/json" \
     -d '{
       "component": "production_test",
       "severity": "medium",
       "message": "Production deployment test alert"
     }' \
     https://bella.yourcompany.com/api/unified/alerts

# Verify alert in dashboard and Slack (if configured)
```

### Performance Testing
```bash
# Load test basic endpoints
for i in {1..10}; do
    curl -H "X-API-Key: your-api-key" https://bella.yourcompany.com/api/unified/status &
done
wait

# Check response times
curl -w "@curl-format.txt" -H "X-API-Key: your-api-key" \
     https://bella.yourcompany.com/api/unified/business-metrics

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

## 🚨 Step 10: Emergency Procedures

### Rollback Plan
```bash
# 1. Stop application
sudo supervisorctl stop bella bella-worker

# 2. Restore from backup
cd /opt/bella
sudo -u bella git checkout previous-stable-tag

# 3. Restore environment if needed
sudo cp .env.backup .env

# 4. Restart application
sudo supervisorctl start bella bella-worker
```

### Database Recovery
```bash
# 1. Stop application
sudo supervisorctl stop bella bella-worker

# 2. Restore database
gunzip -c /opt/bella/backups/bella_db_backup_YYYYMMDD_HHMMSS.sql.gz | \
    PGPASSWORD=your_password psql -h localhost -U bella_user -d bella_prod

# 3. Restart application
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

## 📋 Post-Deployment Checklist

### Day 1 ✅
- [ ] Monitor application for 24 hours continuously
- [ ] Verify all alerting channels work (Slack, email)
- [ ] Test voice call flow multiple times
- [ ] Check cost tracking is active and accurate
- [ ] Review all logs for errors or warnings
- [ ] Test backup and restore procedures
- [ ] Verify SSL certificate is working
- [ ] Check all monitoring scripts are running

### Week 1 ✅
- [ ] Performance optimization based on real usage patterns
- [ ] Fine-tune alerting thresholds to reduce noise
- [ ] Update monitoring scripts based on observed patterns
- [ ] Document any custom configurations made
- [ ] Train operations team on procedures
- [ ] Review security logs and access patterns
- [ ] Optimize database queries based on usage
- [ ] Update capacity planning based on actual usage

### Month 1 ✅
- [ ] Review cost optimization recommendations
- [ ] Analyze performance trends and optimize
- [ ] Update capacity planning based on growth
- [ ] Review and update backup retention policies
- [ ] Conduct disaster recovery test
- [ ] Security audit and penetration testing
- [ ] Review and update SLA targets
- [ ] Plan for scaling based on usage patterns

---

## 📊 Production Monitoring

### Key Metrics to Watch
- **System Health**: 99.9% uptime target
- **Response Time**: 99% under 2 seconds
- **Call Success Rate**: >95% target
- **Error Rate**: <5% of total requests
- **Cost per Call**: <$0.05 target

### Daily Operations
```bash
# Daily health check
/usr/local/bin/bella-health-check

# Check system resources
htop
df -h
free -h

# Review logs
sudo tail -100 /var/log/bella/app.log
sudo tail -100 /var/log/nginx/bella_error.log

# Check supervisor status
sudo supervisorctl status

# Verify SSL certificate
echo | openssl s_client -connect bella.yourcompany.com:443 -servername bella.yourcompany.com 2>/dev/null | openssl x509 -noout -dates
```

### Weekly Operations
```bash
# Run backup manually and verify
/usr/local/bin/bella-backup

# Update system packages
sudo apt update && sudo apt list --upgradable

# Review performance metrics
curl -H "X-API-Key: your-api-key" https://bella.yourcompany.com/api/unified/trends?hours=168 | jq

# Check certificate auto-renewal
sudo certbot certificates
```

---

## 🎯 Success Criteria

### Technical ✅
- ✅ Application responds to health checks
- ✅ Voice calls process successfully
- ✅ Dashboard loads and functions correctly
- ✅ Alerts are generated and delivered
- ✅ Backups run automatically
- ✅ SSL certificate is valid and auto-renewing
- ✅ All monitoring scripts are operational

### Business ✅
- ✅ Voice appointment booking works end-to-end
- ✅ Cost tracking is active and accurate
- ✅ SLA monitoring shows healthy metrics
- ✅ No critical alerts in first 24 hours
- ✅ Performance meets targets (>99% under 2s)
- ✅ Operations team trained and comfortable

---

**🎉 Congratulations! Bella V3 is now live in production!**

Your enterprise-grade voice appointment booking system is operational with:
- ✅ 99.9% SLA monitoring
- ✅ Multi-channel alerting
- ✅ Cost optimization
- ✅ Circuit breaker protection
- ✅ Comprehensive monitoring

For ongoing operations, refer to the [Operations Runbook](./docs/OPERATIONS.md).
For troubleshooting, see [FAQ](./docs/FAQ.md).

**Emergency Support:** [Your 24/7 contact]

*Last Updated: 2025-09-30*
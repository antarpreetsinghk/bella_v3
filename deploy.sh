#!/bin/bash
# Bella V3 Voice Assistant - Cost-Optimized EC2 Deployment
# Single instance deployment with SQLite + Local Redis (~$25/month)

set -e

echo "🚀 Bella V3 Voice Assistant - Cost-Optimized Deployment Starting..."

# Configuration
PROJECT_NAME="bella_v3"
DOMAIN="${DOMAIN:-your-domain.com}"
EMAIL="${EMAIL:-admin@${DOMAIN}}"
DEPLOY_MODE="${DEPLOY_MODE:-cost-optimized}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   print_error "This script should not be run as root for security reasons"
   exit 1
fi

# Update system packages
print_status "Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install required packages
print_status "Installing Docker and dependencies..."
sudo apt install -y \
    docker.io \
    docker-compose \
    git \
    curl \
    nginx \
    certbot \
    python3-certbot-nginx \
    fail2ban \
    ufw

# Add user to docker group
sudo usermod -aG docker $USER

# Start and enable services
print_status "Starting services..."
sudo systemctl start docker
sudo systemctl enable docker
sudo systemctl start nginx
sudo systemctl enable nginx
sudo systemctl start fail2ban
sudo systemctl enable fail2ban

# Configure firewall
print_status "Configuring firewall..."
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw --force enable

# Clone repository if not exists
if [ ! -d "$PROJECT_NAME" ]; then
    print_status "Cloning repository..."
    git clone https://github.com/${GITHUB_USERNAME:-YOUR_USERNAME}/${PROJECT_NAME}.git
else
    print_status "Updating repository..."
    cd $PROJECT_NAME
    git pull origin main
    cd ..
fi

cd $PROJECT_NAME

# Setup environment file
if [ ! -f .env ]; then
    print_status "Setting up environment configuration..."
    cp .env.example .env

    print_warning "IMPORTANT: Edit .env file with your actual credentials:"
    echo "  - OPENAI_API_KEY"
    echo "  - TWILIO_ACCOUNT_SID"
    echo "  - TWILIO_AUTH_TOKEN"
    echo "  - TWILIO_PHONE_NUMBER"
    echo "  - GOOGLE_SERVICE_ACCOUNT_JSON"
    echo "  - API_KEY"
    echo "  - ADMIN_PASS"
    echo ""
    echo "Press Enter when you've updated the .env file..."
    read -r
fi

# Create required directories
print_status "Creating application directories..."
mkdir -p data logs/calls ssl

# Setup SSL certificates with Let's Encrypt
if [ "$DOMAIN" != "your-domain.com" ]; then
    print_status "Setting up SSL certificates..."
    sudo certbot --nginx -d $DOMAIN --email $EMAIL --agree-tos --non-interactive --redirect
else
    print_warning "Skipping SSL setup - update DOMAIN variable for production"
fi

# Create Nginx configuration
print_status "Configuring Nginx..."
sudo tee /etc/nginx/sites-available/$PROJECT_NAME > /dev/null <<EOF
server {
    listen 80;
    server_name $DOMAIN;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";

    # Rate limiting
    limit_req_zone \$binary_remote_addr zone=api:10m rate=10r/m;
    limit_req zone=api burst=20 nodelay;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Health check endpoint
    location /healthz {
        proxy_pass http://localhost:8000/healthz;
        access_log off;
    }

    # Block common attack paths
    location ~ /\\.ht {
        deny all;
    }

    location ~ /\\.(git|env) {
        deny all;
    }
}
EOF

# Enable the site
sudo ln -sf /etc/nginx/sites-available/$PROJECT_NAME /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx

# Configure fail2ban for additional security
print_status "Configuring fail2ban..."
sudo tee /etc/fail2ban/jail.local > /dev/null <<EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true

[nginx-http-auth]
enabled = true

[nginx-limit-req]
enabled = true
filter = nginx-limit-req
action = iptables-multiport[name=ReqLimit, port="http,https", protocol=tcp]
logpath = /var/log/nginx/error.log
maxretry = 10
findtime = 600
bantime = 7200
EOF

sudo systemctl restart fail2ban

# Initialize database
print_status "Initializing SQLite database..."
mkdir -p data logs/calls

# Initialize database with existing models
python3 init_db.py

# Build and start the application
print_status "Building and starting the cost-optimized application..."

# Use cost-optimized docker-compose
if [ "$DEPLOY_MODE" = "cost-optimized" ]; then
    COMPOSE_FILE="docker-compose.cost-optimized.yml"
    DOCKERFILE="Dockerfile.cost-optimized"

    # Update nginx config with domain
    sed -i "s/your-domain.com/$DOMAIN/g" nginx.conf 2>/dev/null || true

    # Build with cost-optimized dockerfile
    docker build -f $DOCKERFILE -t bella-v3:cost-optimized .

    # Start with cost-optimized compose
    docker-compose -f $COMPOSE_FILE down 2>/dev/null || true
    docker-compose -f $COMPOSE_FILE up -d
else
    # Standard deployment
    docker-compose down 2>/dev/null || true
    docker-compose build
    docker-compose up -d
fi

# Wait for application to start
print_status "Waiting for application to start..."
sleep 30

# Health check
print_status "Performing health check..."
if curl -f http://localhost:8000/healthz >/dev/null 2>&1; then
    print_status "Application is healthy!"
else
    print_error "Health check failed!"
    echo "Check logs with: docker-compose logs"
    exit 1
fi

# Create backup script
print_status "Setting up automated backups..."
sudo tee /usr/local/bin/backup-bella.sh > /dev/null <<EOF
#!/bin/bash
# Backup script for Bella Voice Assistant

BACKUP_DIR="/home/$USER/backups"
DATE=\$(date +%Y%m%d_%H%M%S)
PROJECT_DIR="/home/$USER/$PROJECT_NAME"

mkdir -p \$BACKUP_DIR

# Backup database
cp \$PROJECT_DIR/data/bella.db \$BACKUP_DIR/bella_db_\$DATE.db

# Backup logs (last 7 days)
tar -czf \$BACKUP_DIR/logs_\$DATE.tar.gz -C \$PROJECT_DIR/logs .

# Backup environment config (without secrets)
grep -v -E "(API_KEY|TOKEN|SECRET|PASSWORD)" \$PROJECT_DIR/.env > \$BACKUP_DIR/env_template_\$DATE.txt

# Keep only last 30 backups
find \$BACKUP_DIR -name "bella_db_*.db" -mtime +30 -delete
find \$BACKUP_DIR -name "logs_*.tar.gz" -mtime +30 -delete

echo "Backup completed: \$DATE"
EOF

sudo chmod +x /usr/local/bin/backup-bella.sh

# Setup daily backup cron job
(crontab -l 2>/dev/null; echo "0 2 * * * /usr/local/bin/backup-bella.sh >> /var/log/backup-bella.log 2>&1") | crontab -

# Create monitoring script
print_status "Setting up monitoring..."
tee monitor.sh > /dev/null <<EOF
#!/bin/bash
# Simple monitoring script for Bella Voice Assistant

echo "🔍 Bella Voice Assistant - System Status"
echo "======================================"

# Check if containers are running
echo "📦 Docker Containers:"
docker-compose ps

echo ""
echo "💾 Disk Usage:"
df -h /

echo ""
echo "🔧 Service Status:"
sudo systemctl is-active docker nginx fail2ban

echo ""
echo "📊 Recent Call Stats:"
if [ -f "data/bella.db" ]; then
    echo "Total appointments in DB:"
    sqlite3 data/bella.db "SELECT COUNT(*) FROM appointments;" 2>/dev/null || echo "Database not accessible"
fi

echo ""
echo "📝 Recent Logs (last 10 lines):"
docker-compose logs --tail=10 app

echo ""
echo "🌐 Health Check:"
curl -f http://localhost:8000/healthz && echo " ✅ Healthy" || echo " ❌ Unhealthy"
EOF

chmod +x monitor.sh

# Display deployment summary
print_status "🎉 Deployment Complete!"
echo ""
echo "📋 Deployment Summary:"
echo "===================="
echo "🌐 Application URL: https://$DOMAIN (or http://localhost:8000)"
echo "📊 Health Check: https://$DOMAIN/healthz"
echo "📱 Twilio Webhook: https://$DOMAIN/twilio/voice"
echo "💾 Database: $PWD/data/bella.db"
echo "📝 Logs: $PWD/logs/calls/"
echo ""
echo "🛠️  Management Commands:"
echo "• View logs: docker-compose logs -f"
echo "• Restart app: docker-compose restart"
echo "• System status: ./monitor.sh"
echo "• Analyze calls: python tools/analyze_calls.py"
echo "• Backup data: sudo /usr/local/bin/backup-bella.sh"
echo ""
echo "🔧 Next Steps:"
echo "1. Update Twilio webhook URL to: https://$DOMAIN/twilio/voice"
echo "2. Test the system with a phone call"
echo "3. Monitor logs: docker-compose logs -f"
echo "4. Set up monitoring alerts (optional)"
echo ""

# Test call flow if requested
read -p "🧪 Would you like to test the call flow locally? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_status "Running call flow test..."
    python tools/call_flow_tester.py
fi

print_status "🎯 Bella Voice Assistant is ready for calls!"
echo "💰 Estimated monthly cost: ~\$25 for 50 calls/day"
echo "📞 Don't forget to configure your Twilio webhook URL!"
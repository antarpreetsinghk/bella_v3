#!/bin/bash
# Bella V3 Production Deployment Script
# This script deploys Bella V3 to a production server

set -e  # Exit on any error

# Configuration
APP_NAME="bella"
APP_USER="bella"
APP_DIR="/opt/bella"
VENV_DIR="$APP_DIR/venv"
BACKUP_DIR="$APP_DIR/backups"
LOG_DIR="/var/log/bella"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root"
        exit 1
    fi
}

check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check if required packages are installed
    local packages=("python3.11" "python3.11-venv" "postgresql-client" "redis-tools" "nginx" "supervisor" "git")

    for package in "${packages[@]}"; do
        if ! dpkg -l | grep -q "^ii.*$package"; then
            log_error "Required package '$package' is not installed"
            exit 1
        fi
    done

    log_success "All prerequisites met"
}

create_user() {
    log_info "Creating application user..."

    if ! id "$APP_USER" &>/dev/null; then
        useradd -r -s /bin/false -d "$APP_DIR" "$APP_USER"
        log_success "Created user: $APP_USER"
    else
        log_info "User $APP_USER already exists"
    fi
}

create_directories() {
    log_info "Creating application directories..."

    # Create directories
    mkdir -p "$APP_DIR" "$BACKUP_DIR" "$LOG_DIR"

    # Set ownership
    chown -R "$APP_USER:$APP_USER" "$APP_DIR" "$LOG_DIR"

    # Set permissions
    chmod 755 "$APP_DIR"
    chmod 755 "$LOG_DIR"

    log_success "Directories created and configured"
}

install_application() {
    log_info "Installing Bella V3 application..."

    # Backup current installation if it exists
    if [ -d "$APP_DIR/.git" ]; then
        log_info "Backing up current installation..."
        timestamp=$(date +%Y%m%d_%H%M%S)
        tar -czf "$BACKUP_DIR/bella_backup_$timestamp.tar.gz" \
            --exclude=venv \
            --exclude=__pycache__ \
            --exclude=*.pyc \
            --exclude=backups \
            -C "$APP_DIR" .
        log_success "Backup created: bella_backup_$timestamp.tar.gz"
    fi

    # Clone or update repository
    if [ ! -d "$APP_DIR/.git" ]; then
        log_info "Cloning repository..."
        # Note: Replace with your actual repository URL
        # git clone https://github.com/yourorg/bella_v3.git "$APP_DIR"
        # For now, copy from current directory
        cp -r . "$APP_DIR/"
        cd "$APP_DIR"
        git init
        git add .
        git commit -m "Initial production deployment"
    else
        log_info "Updating repository..."
        cd "$APP_DIR"
        git pull origin main
    fi

    # Set ownership
    chown -R "$APP_USER:$APP_USER" "$APP_DIR"

    log_success "Application code installed"
}

setup_python_environment() {
    log_info "Setting up Python virtual environment..."

    cd "$APP_DIR"

    # Create virtual environment
    if [ ! -d "$VENV_DIR" ]; then
        sudo -u "$APP_USER" python3.11 -m venv "$VENV_DIR"
        log_success "Virtual environment created"
    fi

    # Activate and install dependencies
    sudo -u "$APP_USER" bash -c "
        source '$VENV_DIR/bin/activate'
        pip install --upgrade pip
        pip install -r requirements.txt
        pip install gunicorn
    "

    log_success "Python dependencies installed"
}

configure_environment() {
    log_info "Configuring environment variables..."

    # Check if production.env exists
    if [ ! -f "$APP_DIR/production.env" ]; then
        log_warning "production.env not found. Copying template..."
        cp "$APP_DIR/production.env.template" "$APP_DIR/production.env"
        log_error "Please edit $APP_DIR/production.env with your production values before continuing"
        exit 1
    fi

    # Set proper permissions
    chown "$APP_USER:$APP_USER" "$APP_DIR/production.env"
    chmod 600 "$APP_DIR/production.env"

    # Create symlink to .env
    ln -sf production.env "$APP_DIR/.env"

    log_success "Environment configuration completed"
}

setup_database() {
    log_info "Setting up database..."

    # Source environment variables
    source "$APP_DIR/production.env"

    # Test database connection
    cd "$APP_DIR"
    sudo -u "$APP_USER" bash -c "
        source '$VENV_DIR/bin/activate'
        source production.env
        python -c 'from app.db.session import get_engine; print(\"Database connection test passed\")'
    "

    # Initialize database schema
    sudo -u "$APP_USER" bash -c "
        source '$VENV_DIR/bin/activate'
        source production.env
        python -c 'from app.db.base import init_db; init_db()'
    "

    log_success "Database setup completed"
}

configure_supervisor() {
    log_info "Configuring Supervisor..."

    # Create supervisor configuration
    cat > /etc/supervisor/conf.d/bella.conf << EOF
[program:bella]
command=$VENV_DIR/bin/gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 127.0.0.1:8000 --timeout 30 --max-requests 1000 --preload
directory=$APP_DIR
user=$APP_USER
autostart=true
autorestart=true
stopasgroup=true
killasgroup=true
stdout_logfile=$LOG_DIR/app.log
stderr_logfile=$LOG_DIR/error.log
environment=PATH="$VENV_DIR/bin"

[program:bella-worker]
command=$VENV_DIR/bin/python -m app.workers.background
directory=$APP_DIR
user=$APP_USER
autostart=true
autorestart=true
stopasgroup=true
killasgroup=true
stdout_logfile=$LOG_DIR/worker.log
stderr_logfile=$LOG_DIR/worker-error.log
environment=PATH="$VENV_DIR/bin"
EOF

    # Reload supervisor configuration
    supervisorctl reread
    supervisorctl update

    log_success "Supervisor configuration completed"
}

configure_nginx() {
    log_info "Configuring Nginx..."

    # Read domain from environment or use default
    source "$APP_DIR/production.env"
    DOMAIN="${DOMAIN:-bella.yourcompany.com}"

    # Create Nginx configuration
    cat > /etc/nginx/sites-available/bella << EOF
upstream bella_backend {
    server 127.0.0.1:8000;
}

limit_req_zone \$binary_remote_addr zone=api:10m rate=10r/s;
limit_req_zone \$binary_remote_addr zone=dashboard:10m rate=5r/s;

server {
    listen 80;
    server_name $DOMAIN;
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name $DOMAIN;

    # SSL Configuration (update paths as needed)
    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
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

    location / {
        limit_req zone=dashboard burst=10 nodelay;
        proxy_pass http://bella_backend;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 30s;
        proxy_connect_timeout 5s;
    }

    location /api/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://bella_backend;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 60s;
        proxy_connect_timeout 10s;
    }

    location /twilio/ {
        proxy_pass http://bella_backend;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 30s;
        proxy_connect_timeout 5s;
    }

    location /healthz {
        proxy_pass http://bella_backend;
        access_log off;
    }
}
EOF

    # Enable site
    ln -sf /etc/nginx/sites-available/bella /etc/nginx/sites-enabled/

    # Test configuration
    nginx -t

    log_success "Nginx configuration completed"
}

setup_monitoring() {
    log_info "Setting up monitoring scripts..."

    # Create monitoring scripts directory
    mkdir -p "$APP_DIR/scripts"

    # Create health check script
    cat > "$APP_DIR/scripts/health_check.sh" << 'EOF'
#!/bin/bash
# Production health monitoring script

source /opt/bella/production.env

API_KEY="$BELLA_API_KEY"
BASE_URL="https://bella.yourcompany.com"

# Function to send alert
send_alert() {
    local message="$1"
    local status="$2"

    if [ -n "$SLACK_WEBHOOK_URL" ]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"🚨 Bella Production Alert: $message (Status: $status)\"}" \
            "$SLACK_WEBHOOK_URL"
    fi
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

echo "Health check passed"
EOF

    # Make executable
    chmod +x "$APP_DIR/scripts/health_check.sh"
    chown "$APP_USER:$APP_USER" "$APP_DIR/scripts/health_check.sh"

    # Add to cron
    (crontab -l 2>/dev/null; echo "*/5 * * * * $APP_DIR/scripts/health_check.sh >> $LOG_DIR/health_check.log 2>&1") | crontab -

    log_success "Monitoring setup completed"
}

setup_logrotate() {
    log_info "Configuring log rotation..."

    cat > /etc/logrotate.d/bella << EOF
$LOG_DIR/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 $APP_USER $APP_USER
    postrotate
        supervisorctl restart bella bella-worker
    endscript
}
EOF

    log_success "Log rotation configured"
}

start_services() {
    log_info "Starting services..."

    # Start application
    supervisorctl start bella bella-worker

    # Restart Nginx
    systemctl restart nginx

    # Enable services
    systemctl enable supervisor
    systemctl enable nginx

    log_success "Services started"
}

run_health_checks() {
    log_info "Running post-deployment health checks..."

    # Wait for application to start
    sleep 10

    # Check supervisor status
    supervisorctl status

    # Check application health
    source "$APP_DIR/production.env"

    # Test health endpoint
    if curl -s http://localhost:8000/healthz | grep -q "ok"; then
        log_success "Health check passed"
    else
        log_error "Health check failed"
        exit 1
    fi

    # Test API endpoint
    if curl -s -H "X-API-Key: $BELLA_API_KEY" http://localhost:8000/api/unified/status | grep -q "healthy"; then
        log_success "API endpoint check passed"
    else
        log_error "API endpoint check failed"
        exit 1
    fi

    log_success "All health checks passed"
}

main() {
    log_info "Starting Bella V3 production deployment..."

    check_root
    check_prerequisites
    create_user
    create_directories
    install_application
    setup_python_environment
    configure_environment
    setup_database
    configure_supervisor
    configure_nginx
    setup_monitoring
    setup_logrotate
    start_services
    run_health_checks

    log_success "🎉 Bella V3 production deployment completed successfully!"
    log_info "Next steps:"
    log_info "1. Configure SSL certificate (certbot --nginx -d your-domain.com)"
    log_info "2. Update Twilio webhook URL to https://your-domain.com/twilio/voice"
    log_info "3. Test voice call functionality"
    log_info "4. Set up external monitoring"
    log_info ""
    log_info "Dashboard URL: https://your-domain.com/"
    log_info "Health Check: https://your-domain.com/healthz"
    log_info ""
    log_info "Logs location: $LOG_DIR/"
    log_info "Application directory: $APP_DIR/"
}

# Run main function
main "$@"
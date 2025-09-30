#!/bin/bash
# Bella V3 Production Backup Script
# Creates backups of database and application configuration

set -e

# Configuration
APP_DIR="/opt/bella"
BACKUP_DIR="/opt/bella/backups"
LOG_FILE="/var/log/bella/backup.log"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# Load environment variables
source "$APP_DIR/production.env"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

create_backup_directory() {
    mkdir -p "$BACKUP_DIR"
    chown bella:bella "$BACKUP_DIR"
}

backup_database() {
    log_info "Starting database backup..."

    # Extract database connection details
    DB_HOST=$(echo "$DATABASE_URL" | sed -n 's/.*@\([^:]*\).*/\1/p')
    DB_PORT=$(echo "$DATABASE_URL" | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
    DB_NAME=$(echo "$DATABASE_URL" | sed -n 's/.*\/\([^?]*\).*/\1/p')
    DB_USER=$(echo "$DATABASE_URL" | sed -n 's/.*:\/\/\([^:]*\):.*/\1/p')

    # Set default port if not specified
    DB_PORT=${DB_PORT:-5432}

    # Create database backup
    PGPASSWORD=$(echo "$DATABASE_URL" | sed -n 's/.*:\([^@]*\)@.*/\1/p') \
    pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
        --no-password \
        --verbose \
        | gzip > "$BACKUP_DIR/bella_db_backup_$DATE.sql.gz"

    if [ $? -eq 0 ]; then
        log_success "Database backup completed: bella_db_backup_$DATE.sql.gz"
    else
        log_error "Database backup failed"
        exit 1
    fi
}

backup_application() {
    log_info "Starting application backup..."

    # Create application backup
    tar -czf "$BACKUP_DIR/bella_app_backup_$DATE.tar.gz" \
        --exclude=venv \
        --exclude=__pycache__ \
        --exclude=*.pyc \
        --exclude=backups \
        --exclude=.git \
        -C "$APP_DIR" .

    if [ $? -eq 0 ]; then
        log_success "Application backup completed: bella_app_backup_$DATE.tar.gz"
    else
        log_error "Application backup failed"
        exit 1
    fi
}

backup_nginx_config() {
    log_info "Backing up Nginx configuration..."

    if [ -f "/etc/nginx/sites-available/bella" ]; then
        cp "/etc/nginx/sites-available/bella" "$BACKUP_DIR/nginx_bella_$DATE.conf"
        log_success "Nginx config backed up: nginx_bella_$DATE.conf"
    fi
}

backup_supervisor_config() {
    log_info "Backing up Supervisor configuration..."

    if [ -f "/etc/supervisor/conf.d/bella.conf" ]; then
        cp "/etc/supervisor/conf.d/bella.conf" "$BACKUP_DIR/supervisor_bella_$DATE.conf"
        log_success "Supervisor config backed up: supervisor_bella_$DATE.conf"
    fi
}

cleanup_old_backups() {
    log_info "Cleaning up backups older than $RETENTION_DAYS days..."

    # Remove old database backups
    find "$BACKUP_DIR" -name "bella_db_backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete

    # Remove old application backups
    find "$BACKUP_DIR" -name "bella_app_backup_*.tar.gz" -mtime +$RETENTION_DAYS -delete

    # Remove old config backups
    find "$BACKUP_DIR" -name "nginx_bella_*.conf" -mtime +$RETENTION_DAYS -delete
    find "$BACKUP_DIR" -name "supervisor_bella_*.conf" -mtime +$RETENTION_DAYS -delete

    log_success "Old backups cleaned up"
}

verify_backups() {
    log_info "Verifying backup integrity..."

    # Check database backup
    if [ -f "$BACKUP_DIR/bella_db_backup_$DATE.sql.gz" ]; then
        if gzip -t "$BACKUP_DIR/bella_db_backup_$DATE.sql.gz"; then
            log_success "Database backup integrity verified"
        else
            log_error "Database backup is corrupted"
            exit 1
        fi
    fi

    # Check application backup
    if [ -f "$BACKUP_DIR/bella_app_backup_$DATE.tar.gz" ]; then
        if tar -tzf "$BACKUP_DIR/bella_app_backup_$DATE.tar.gz" > /dev/null; then
            log_success "Application backup integrity verified"
        else
            log_error "Application backup is corrupted"
            exit 1
        fi
    fi
}

generate_backup_report() {
    log_info "Generating backup report..."

    REPORT_FILE="$BACKUP_DIR/backup_report_$DATE.txt"

    cat > "$REPORT_FILE" << EOF
Bella V3 Backup Report
=====================
Date: $(date)
Backup ID: $DATE

Database Backup:
- File: bella_db_backup_$DATE.sql.gz
- Size: $(du -h "$BACKUP_DIR/bella_db_backup_$DATE.sql.gz" | cut -f1)

Application Backup:
- File: bella_app_backup_$DATE.tar.gz
- Size: $(du -h "$BACKUP_DIR/bella_app_backup_$DATE.tar.gz" | cut -f1)

Configuration Backups:
$(ls -la "$BACKUP_DIR"/*_$DATE.conf 2>/dev/null || echo "No config files backed up")

Total Backup Size: $(du -sh "$BACKUP_DIR" | cut -f1)

Backup Status: SUCCESS
EOF

    log_success "Backup report generated: backup_report_$DATE.txt"
}

send_backup_notification() {
    if [ -n "$SLACK_WEBHOOK_URL" ]; then
        log_info "Sending backup notification to Slack..."

        BACKUP_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)

        curl -X POST -H 'Content-type: application/json' \
            --data "{
                \"text\": \"✅ Bella V3 Backup Completed\",
                \"attachments\": [{
                    \"color\": \"good\",
                    \"fields\": [
                        {\"title\": \"Date\", \"value\": \"$(date)\", \"short\": true},
                        {\"title\": \"Backup ID\", \"value\": \"$DATE\", \"short\": true},
                        {\"title\": \"Total Size\", \"value\": \"$BACKUP_SIZE\", \"short\": true},
                        {\"title\": \"Status\", \"value\": \"SUCCESS\", \"short\": true}
                    ]
                }]
            }" \
            "$SLACK_WEBHOOK_URL"

        log_success "Slack notification sent"
    fi
}

main() {
    log_info "Starting Bella V3 backup process..."

    create_backup_directory
    backup_database
    backup_application
    backup_nginx_config
    backup_supervisor_config
    verify_backups
    cleanup_old_backups
    generate_backup_report
    send_backup_notification

    log_success "🎉 Backup process completed successfully!"
    log_info "Backup location: $BACKUP_DIR"
    log_info "Backup ID: $DATE"
}

# Run main function
main "$@"
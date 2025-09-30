#!/bin/bash
# Bella V3 Production Health Monitoring Script
# Comprehensive health checks and alerting

set -e

# Configuration
APP_DIR="/opt/bella"
LOG_FILE="/var/log/bella/health_monitor.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

# Load environment variables
if [ -f "$APP_DIR/production.env" ]; then
    source "$APP_DIR/production.env"
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[$DATE][INFO]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[$DATE][SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[$DATE][WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[$DATE][ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

send_alert() {
    local severity="$1"
    local message="$2"
    local details="$3"

    if [ -n "$SLACK_WEBHOOK_URL" ]; then
        local color=""
        local emoji=""

        case "$severity" in
            "critical") color="#FF0000"; emoji="🚨" ;;
            "warning") color="#FFCC00"; emoji="⚠️" ;;
            "info") color="#00FF00"; emoji="ℹ️" ;;
        esac

        curl -s -X POST -H 'Content-type: application/json' \
            --data "{
                \"text\": \"$emoji Bella Production Alert\",
                \"attachments\": [{
                    \"color\": \"$color\",
                    \"fields\": [
                        {\"title\": \"Severity\", \"value\": \"$severity\", \"short\": true},
                        {\"title\": \"Time\", \"value\": \"$DATE\", \"short\": true},
                        {\"title\": \"Message\", \"value\": \"$message\", \"short\": false},
                        {\"title\": \"Details\", \"value\": \"$details\", \"short\": false}
                    ]
                }]
            }" \
            "$SLACK_WEBHOOK_URL"
    fi
}

check_system_resources() {
    log_info "Checking system resources..."

    # Check disk space
    local disk_usage=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
    if [ "$disk_usage" -gt 90 ]; then
        log_error "CRITICAL: Disk usage at $disk_usage%"
        send_alert "critical" "High disk usage" "Disk usage: $disk_usage%"
        return 1
    elif [ "$disk_usage" -gt 80 ]; then
        log_warning "WARNING: Disk usage at $disk_usage%"
        send_alert "warning" "Elevated disk usage" "Disk usage: $disk_usage%"
    else
        log_success "Disk usage OK: $disk_usage%"
    fi

    # Check memory usage
    local memory_info=$(free | awk '/Mem:/ {printf "%.0f %.0f", $3/$2 * 100, $2/1024/1024}')
    local memory_usage=$(echo $memory_info | cut -d' ' -f1)
    local total_memory=$(echo $memory_info | cut -d' ' -f2)

    if [ "$memory_usage" -gt 90 ]; then
        log_error "CRITICAL: Memory usage at $memory_usage%"
        send_alert "critical" "High memory usage" "Memory usage: $memory_usage% of ${total_memory}GB"
        return 1
    elif [ "$memory_usage" -gt 80 ]; then
        log_warning "WARNING: Memory usage at $memory_usage%"
        send_alert "warning" "Elevated memory usage" "Memory usage: $memory_usage% of ${total_memory}GB"
    else
        log_success "Memory usage OK: $memory_usage% of ${total_memory}GB"
    fi

    # Check CPU load
    local cpu_load=$(uptime | awk -F'load average:' '{ print $2 }' | cut -d, -f1 | xargs)
    local cpu_cores=$(nproc)
    local load_per_core=$(echo "scale=2; $cpu_load / $cpu_cores" | bc -l)

    if (( $(echo "$load_per_core > 2.0" | bc -l) )); then
        log_error "CRITICAL: High CPU load: $cpu_load (${load_per_core} per core)"
        send_alert "critical" "High CPU load" "Load: $cpu_load on $cpu_cores cores (${load_per_core} per core)"
        return 1
    elif (( $(echo "$load_per_core > 1.5" | bc -l) )); then
        log_warning "WARNING: Elevated CPU load: $cpu_load (${load_per_core} per core)"
        send_alert "warning" "Elevated CPU load" "Load: $cpu_load on $cpu_cores cores (${load_per_core} per core)"
    else
        log_success "CPU load OK: $cpu_load (${load_per_core} per core)"
    fi

    return 0
}

check_application_processes() {
    log_info "Checking application processes..."

    # Check if Bella application is running
    if ! pgrep -f "gunicorn.*bella" > /dev/null; then
        log_error "CRITICAL: Bella application not running"
        send_alert "critical" "Application down" "Bella gunicorn process not found"

        # Attempt to restart
        log_info "Attempting to restart application..."
        supervisorctl restart bella
        sleep 10

        if pgrep -f "gunicorn.*bella" > /dev/null; then
            log_success "Application restarted successfully"
            send_alert "info" "Application restarted" "Bella application has been restarted automatically"
        else
            log_error "Failed to restart application"
            return 1
        fi
    else
        log_success "Bella application running"
    fi

    # Check worker process
    if ! pgrep -f "python.*workers" > /dev/null; then
        log_warning "WARNING: Background worker not running"
        send_alert "warning" "Worker process down" "Background worker process not found"

        # Attempt to restart worker
        supervisorctl restart bella-worker
        sleep 5

        if pgrep -f "python.*workers" > /dev/null; then
            log_success "Background worker restarted"
        fi
    else
        log_success "Background worker running"
    fi

    return 0
}

check_application_health() {
    log_info "Checking application health endpoints..."

    local base_url="${APP_URL:-http://localhost:8000}"

    # Check basic health
    local health_response=$(curl -s -o /dev/null -w "%{http_code}" "$base_url/healthz")
    if [ "$health_response" != "200" ]; then
        log_error "CRITICAL: Health endpoint failed (HTTP $health_response)"
        send_alert "critical" "Health check failed" "Health endpoint returned HTTP $health_response"
        return 1
    else
        log_success "Health endpoint OK"
    fi

    # Check database connectivity
    local readyz_response=$(curl -s -o /dev/null -w "%{http_code}" "$base_url/readyz")
    if [ "$readyz_response" != "200" ]; then
        log_error "CRITICAL: Database connectivity failed (HTTP $readyz_response)"
        send_alert "critical" "Database connection failed" "Readyz endpoint returned HTTP $readyz_response"
        return 1
    else
        log_success "Database connectivity OK"
    fi

    # Check API authentication (if API key is available)
    if [ -n "$BELLA_API_KEY" ]; then
        local api_response=$(curl -s -H "X-API-Key: $BELLA_API_KEY" -o /dev/null -w "%{http_code}" "$base_url/api/unified/status")
        if [ "$api_response" != "200" ]; then
            log_error "CRITICAL: API authentication failed (HTTP $api_response)"
            send_alert "critical" "API authentication failed" "API endpoint returned HTTP $api_response"
            return 1
        else
            log_success "API authentication OK"
        fi
    fi

    return 0
}

check_external_services() {
    log_info "Checking external service connectivity..."

    # Check OpenAI API
    if [ -n "$OPENAI_API_KEY" ]; then
        local openai_response=$(curl -s -H "Authorization: Bearer $OPENAI_API_KEY" -o /dev/null -w "%{http_code}" "https://api.openai.com/v1/models")
        if [ "$openai_response" != "200" ]; then
            log_warning "WARNING: OpenAI API not accessible (HTTP $openai_response)"
            send_alert "warning" "OpenAI API issue" "OpenAI API returned HTTP $openai_response"
        else
            log_success "OpenAI API connectivity OK"
        fi
    fi

    # Check Redis connectivity
    if command -v redis-cli > /dev/null; then
        if redis-cli ping | grep -q "PONG"; then
            log_success "Redis connectivity OK"
        else
            log_warning "WARNING: Redis not responding"
            send_alert "warning" "Redis connectivity issue" "Redis ping failed"
        fi
    fi

    return 0
}

check_database_health() {
    log_info "Checking database health..."

    if [ -n "$DATABASE_URL" ]; then
        # Extract database connection details
        local db_host=$(echo "$DATABASE_URL" | sed -n 's/.*@\([^:]*\).*/\1/p')
        local db_port=$(echo "$DATABASE_URL" | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
        local db_name=$(echo "$DATABASE_URL" | sed -n 's/.*\/\([^?]*\).*/\1/p')
        local db_user=$(echo "$DATABASE_URL" | sed -n 's/.*:\/\/\([^:]*\):.*/\1/p')

        # Set default port if not specified
        db_port=${db_port:-5432}

        # Check database connectivity
        if PGPASSWORD=$(echo "$DATABASE_URL" | sed -n 's/.*:\([^@]*\)@.*/\1/p') \
           psql -h "$db_host" -p "$db_port" -U "$db_user" -d "$db_name" \
           -c "SELECT 1;" > /dev/null 2>&1; then
            log_success "Database connectivity OK"
        else
            log_error "CRITICAL: Database connection failed"
            send_alert "critical" "Database connection failed" "Unable to connect to PostgreSQL database"
            return 1
        fi

        # Check database size
        local db_size=$(PGPASSWORD=$(echo "$DATABASE_URL" | sed -n 's/.*:\([^@]*\)@.*/\1/p') \
                       psql -h "$db_host" -p "$db_port" -U "$db_user" -d "$db_name" \
                       -t -c "SELECT pg_size_pretty(pg_database_size('$db_name'));" | xargs)
        log_info "Database size: $db_size"

        # Check active connections
        local active_connections=$(PGPASSWORD=$(echo "$DATABASE_URL" | sed -n 's/.*:\([^@]*\)@.*/\1/p') \
                                  psql -h "$db_host" -p "$db_port" -U "$db_user" -d "$db_name" \
                                  -t -c "SELECT count(*) FROM pg_stat_activity WHERE state = 'active';" | xargs)
        log_info "Active database connections: $active_connections"

        if [ "$active_connections" -gt 80 ]; then
            log_warning "WARNING: High number of active database connections: $active_connections"
            send_alert "warning" "High database connections" "Active connections: $active_connections"
        fi
    fi

    return 0
}

check_sla_metrics() {
    log_info "Checking SLA metrics..."

    if [ -n "$BELLA_API_KEY" ]; then
        local base_url="${APP_URL:-http://localhost:8000}"
        local sla_response=$(curl -s -H "X-API-Key: $BELLA_API_KEY" "$base_url/api/unified/sla-metrics")

        if [ $? -eq 0 ]; then
            local health_score=$(echo "$sla_response" | jq -r '.overall_health_score // 0')

            if (( $(echo "$health_score < 95" | bc -l) )); then
                log_error "CRITICAL: SLA health score below 95%: $health_score%"
                send_alert "critical" "SLA breach" "Overall health score: $health_score%"
                return 1
            elif (( $(echo "$health_score < 98" | bc -l) )); then
                log_warning "WARNING: SLA health score below 98%: $health_score%"
                send_alert "warning" "SLA degradation" "Overall health score: $health_score%"
            else
                log_success "SLA health score OK: $health_score%"
            fi
        else
            log_error "Failed to retrieve SLA metrics"
            return 1
        fi
    fi

    return 0
}

check_log_errors() {
    log_info "Checking for recent errors in logs..."

    local error_count=0
    local log_files=("/var/log/bella/error.log" "/var/log/bella/app.log" "/var/log/nginx/bella_error.log")

    for log_file in "${log_files[@]}"; do
        if [ -f "$log_file" ]; then
            # Check for errors in the last 5 minutes
            local recent_errors=$(find "$log_file" -mmin -5 -exec grep -i "error\|exception\|failed\|critical" {} \; 2>/dev/null | wc -l)

            if [ "$recent_errors" -gt 10 ]; then
                log_error "High error rate in $log_file: $recent_errors errors in last 5 minutes"
                error_count=$((error_count + recent_errors))
            elif [ "$recent_errors" -gt 5 ]; then
                log_warning "Elevated error rate in $log_file: $recent_errors errors in last 5 minutes"
                error_count=$((error_count + recent_errors))
            fi
        fi
    done

    if [ "$error_count" -gt 20 ]; then
        send_alert "critical" "High error rate" "Total errors in last 5 minutes: $error_count"
        return 1
    elif [ "$error_count" -gt 10 ]; then
        send_alert "warning" "Elevated error rate" "Total errors in last 5 minutes: $error_count"
    else
        log_success "Error rate normal: $error_count errors in last 5 minutes"
    fi

    return 0
}

generate_health_report() {
    local status="$1"
    local report_file="/tmp/health_report_$(date +%Y%m%d_%H%M%S).txt"

    cat > "$report_file" << EOF
Bella V3 Health Report
=====================
Date: $DATE
Status: $status

System Resources:
- Disk Usage: $(df / | awk 'NR==2 {print $5}')
- Memory Usage: $(free | awk '/Mem:/ {printf "%.0f%%", $3/$2 * 100}')
- CPU Load: $(uptime | awk -F'load average:' '{ print $2 }' | cut -d, -f1 | xargs)

Application Status:
- Main Process: $(pgrep -f "gunicorn.*bella" > /dev/null && echo "Running" || echo "Stopped")
- Worker Process: $(pgrep -f "python.*workers" > /dev/null && echo "Running" || echo "Stopped")

Service Health:
- HTTP Health: $(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/healthz")
- Database: $(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/readyz")

Recent Logs:
$(tail -5 /var/log/bella/app.log 2>/dev/null || echo "No recent logs")

EOF

    log_info "Health report generated: $report_file"
}

main() {
    log_info "Starting comprehensive health check..."

    local overall_status="healthy"
    local checks_failed=0

    # Run all health checks
    check_system_resources || checks_failed=$((checks_failed + 1))
    check_application_processes || checks_failed=$((checks_failed + 1))
    check_application_health || checks_failed=$((checks_failed + 1))
    check_external_services || checks_failed=$((checks_failed + 1))
    check_database_health || checks_failed=$((checks_failed + 1))
    check_sla_metrics || checks_failed=$((checks_failed + 1))
    check_log_errors || checks_failed=$((checks_failed + 1))

    # Determine overall status
    if [ "$checks_failed" -gt 2 ]; then
        overall_status="critical"
        log_error "CRITICAL: Multiple health checks failed ($checks_failed)"
        send_alert "critical" "System health critical" "$checks_failed health checks failed"
    elif [ "$checks_failed" -gt 0 ]; then
        overall_status="degraded"
        log_warning "WARNING: Some health checks failed ($checks_failed)"
        send_alert "warning" "System health degraded" "$checks_failed health checks failed"
    else
        log_success "All health checks passed"
    fi

    generate_health_report "$overall_status"

    log_info "Health check completed with status: $overall_status"
    exit "$checks_failed"
}

# Run main function
main "$@"
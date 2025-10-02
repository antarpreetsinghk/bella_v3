#!/bin/bash
set -euo pipefail

# Debug script for monitoring Bella V3 logs and errors

LOG_GROUP="/ecs/bella-prod"
REGION="ca-central-1"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

function print_header() {
    echo -e "${BLUE}=== $1 ===${NC}"
}

function print_error() {
    echo -e "${RED}❌ $1${NC}"
}

function print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

function print_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

function show_help() {
    echo "Bella V3 Debug Logs Tool"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  errors         Show recent errors (last hour)"
    echo "  slow           Show slow requests (>2s)"
    echo "  tail           Live log tail"
    echo "  metrics        Show application metrics"
    echo "  health         Check service health"
    echo "  twilio         Show Twilio webhook logs"
    echo "  summary        Error summary with counts"
    echo "  insights       Run CloudWatch Insights queries"
    echo ""
}

function check_aws_cli() {
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI not found. Please install it first."
        exit 1
    fi
}

function show_recent_errors() {
    print_header "Recent Errors (Last Hour)"

    START_TIME=$(($(date +%s) - 3600))000  # 1 hour ago in milliseconds

    aws logs filter-log-events \
        --log-group-name "$LOG_GROUP" \
        --start-time "$START_TIME" \
        --filter-pattern "ERROR" \
        --query 'events[*].[timestamp,message]' \
        --output table \
        --region "$REGION" || {
        print_error "Failed to fetch error logs"
    }
}

function show_slow_requests() {
    print_header "Slow Requests (>2s)"

    START_TIME=$(($(date +%s) - 3600))000

    aws logs filter-log-events \
        --log-group-name "$LOG_GROUP" \
        --start-time "$START_TIME" \
        --filter-pattern "[timestamp, level, event=\"request_complete\", ..., duration>2]" \
        --query 'events[*].message' \
        --output table \
        --region "$REGION" || {
        print_warning "No slow requests found or query failed"
    }
}

function tail_logs() {
    print_header "Live Log Tail (Ctrl+C to stop)"

    aws logs tail "$LOG_GROUP" \
        --follow \
        --region "$REGION" \
        --format short || {
        print_error "Failed to tail logs"
    }
}

function show_metrics() {
    print_header "Application Metrics"

    # Get metrics from the /metrics endpoint
    ALB_DNS="your-production-alb.ca-central-1.elb.amazonaws.com"

    if curl -fsS "http://$ALB_DNS/metrics" | jq . 2>/dev/null; then
        print_success "Metrics retrieved successfully"
    else
        print_error "Failed to retrieve metrics from $ALB_DNS/metrics"

        # Fallback: check logs for metrics
        print_warning "Checking logs for metric data..."
        START_TIME=$(($(date +%s) - 300))000  # 5 minutes ago

        aws logs filter-log-events \
            --log-group-name "$LOG_GROUP" \
            --start-time "$START_TIME" \
            --filter-pattern "metrics" \
            --query 'events[-1].message' \
            --output text \
            --region "$REGION" 2>/dev/null || print_warning "No metrics found in logs"
    fi
}

function check_health() {
    print_header "Service Health Check"

    ALB_DNS="your-production-alb.ca-central-1.elb.amazonaws.com"

    # Check health endpoint
    if curl -fsS "http://$ALB_DNS/healthz" | jq . 2>/dev/null; then
        print_success "Health check passed"
    else
        print_error "Health check failed"
    fi

    # Check ECS service status
    print_header "ECS Service Status"
    aws ecs describe-services \
        --cluster bella-prod-cluster \
        --services bella-prod-service \
        --query 'services[0].{Status:status,Running:runningCount,Desired:desiredCount,Pending:pendingCount}' \
        --output table \
        --region "$REGION" || {
        print_error "Failed to get ECS service status"
    }

    # Check target group health
    print_header "Target Group Health"
    aws elbv2 describe-target-health \
        --target-group-arn "arn:aws:elasticloadbalancing:ca-central-1:YOUR_AWS_ACCOUNT_ID:targetgroup/your-tg/your-tg-id" \
        --query 'TargetHealthDescriptions[*].{Target:Target.Id,Port:Target.Port,Health:TargetHealth.State}' \
        --output table \
        --region "$REGION" || {
        print_error "Failed to get target group health"
    }
}

function show_twilio_logs() {
    print_header "Twilio Webhook Logs (Last Hour)"

    START_TIME=$(($(date +%s) - 3600))000

    aws logs filter-log-events \
        --log-group-name "$LOG_GROUP" \
        --start-time "$START_TIME" \
        --filter-pattern "twilio" \
        --query 'events[*].[timestamp,message]' \
        --output table \
        --region "$REGION" || {
        print_warning "No Twilio logs found"
    }
}

function show_error_summary() {
    print_header "Error Summary (Last Hour)"

    # Use CloudWatch Insights for better analysis
    START_TIME=$(date -d "1 hour ago" +%s)
    END_TIME=$(date +%s)

    QUERY_ID=$(aws logs start-query \
        --log-group-name "$LOG_GROUP" \
        --start-time "$START_TIME" \
        --end-time "$END_TIME" \
        --query-string 'fields @timestamp, level, error_type, error_hash, count
                        | filter level = "ERROR"
                        | stats count() as occurrences by error_type, error_hash
                        | sort occurrences desc
                        | limit 10' \
        --query 'queryId' \
        --output text \
        --region "$REGION")

    if [[ -n "$QUERY_ID" ]]; then
        print_success "Query started: $QUERY_ID"
        print_warning "Waiting for results..."
        sleep 3

        aws logs get-query-results \
            --query-id "$QUERY_ID" \
            --region "$REGION" \
            --query 'results' \
            --output table || {
            print_error "Query failed or no results"
        }
    else
        print_error "Failed to start CloudWatch Insights query"
    fi
}

function run_insights() {
    print_header "CloudWatch Insights Queries"

    START_TIME=$(date -d "1 hour ago" +%s)
    END_TIME=$(date +%s)

    echo "1. Top Error Types"
    echo "2. Slow Endpoints"
    echo "3. Request Volume by Endpoint"
    echo "4. Recent Twilio Activity"

    read -p "Select query (1-4): " choice

    case $choice in
        1)
            QUERY='fields @timestamp, error_type, count
                   | filter level = "ERROR"
                   | stats count() by error_type
                   | sort count desc'
            ;;
        2)
            QUERY='fields @timestamp, endpoint, duration
                   | filter duration > 2
                   | sort @timestamp desc
                   | limit 20'
            ;;
        3)
            QUERY='fields @timestamp, endpoint, method
                   | filter event = "request_complete"
                   | stats count() by endpoint
                   | sort count desc'
            ;;
        4)
            QUERY='fields @timestamp, message
                   | filter message like /twilio/
                   | sort @timestamp desc
                   | limit 20'
            ;;
        *)
            print_error "Invalid choice"
            return 1
            ;;
    esac

    QUERY_ID=$(aws logs start-query \
        --log-group-name "$LOG_GROUP" \
        --start-time "$START_TIME" \
        --end-time "$END_TIME" \
        --query-string "$QUERY" \
        --query 'queryId' \
        --output text \
        --region "$REGION")

    if [[ -n "$QUERY_ID" ]]; then
        print_success "Query started: $QUERY_ID"
        print_warning "Waiting for results..."
        sleep 5

        aws logs get-query-results \
            --query-id "$QUERY_ID" \
            --region "$REGION" \
            --query 'results' \
            --output table
    fi
}

# Main script
check_aws_cli

case "${1:-help}" in
    "errors")
        show_recent_errors
        ;;
    "slow")
        show_slow_requests
        ;;
    "tail")
        tail_logs
        ;;
    "metrics")
        show_metrics
        ;;
    "health")
        check_health
        ;;
    "twilio")
        show_twilio_logs
        ;;
    "summary")
        show_error_summary
        ;;
    "insights")
        run_insights
        ;;
    "help"|*)
        show_help
        ;;
esac
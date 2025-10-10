#!/bin/bash
#
# Production Log Monitoring Script
# Monitors application logs for appointment bookings and database operations
#
# Usage:
#   ./scripts/monitor_production_logs.sh [options]
#
# Options:
#   --appointments    Monitor appointment creation only
#   --database        Monitor database operations only
#   --errors          Monitor errors only
#   --all             Monitor all activity (default)
#   --follow          Follow logs in real-time (tail -f mode)
#   --last N          Show last N lines (default: 100)
#

set -e

# Configuration
PRODUCTION_HOST="${PRODUCTION_HOST:-15.157.56.64}"
SSH_USER="${SSH_USER:-root}"
CONTAINER_NAME="${CONTAINER_NAME:-bella_app}"
LINES=100
FOLLOW=false
FILTER="all"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --appointments)
            FILTER="appointments"
            shift
            ;;
        --database)
            FILTER="database"
            shift
            ;;
        --errors)
            FILTER="errors"
            shift
            ;;
        --all)
            FILTER="all"
            shift
            ;;
        --follow|-f)
            FOLLOW=true
            shift
            ;;
        --last)
            LINES="$2"
            shift 2
            ;;
        --help|-h)
            head -n 15 "$0" | tail -n 13
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  Production Log Monitor${NC}"
echo -e "${BLUE}================================================${NC}"
echo -e "Host:      $PRODUCTION_HOST"
echo -e "Container: $CONTAINER_NAME"
echo -e "Filter:    $FILTER"
echo -e "Lines:     $LINES"
echo -e "Follow:    $FOLLOW"
echo ""

# Build grep pattern based on filter
case $FILTER in
    appointments)
        GREP_PATTERN="appointment|booking|created|booked|scheduled|is_test_data"
        ;;
    database)
        GREP_PATTERN="database|INSERT|UPDATE|DELETE|appointment|user|created"
        ;;
    errors)
        GREP_PATTERN="ERROR|error|ERROR|Exception|Failed|failed"
        ;;
    all)
        GREP_PATTERN="."
        ;;
esac

# Build docker logs command
if [ "$FOLLOW" = true ]; then
    DOCKER_CMD="docker logs -f $CONTAINER_NAME 2>&1 | grep -iE '$GREP_PATTERN' --line-buffered"
else
    DOCKER_CMD="docker logs $CONTAINER_NAME --tail=$LINES 2>&1 | grep -iE '$GREP_PATTERN'"
fi

echo -e "${YELLOW}Connecting to production server...${NC}"
echo ""

# Execute monitoring
ssh -t "$SSH_USER@$PRODUCTION_HOST" "$DOCKER_CMD" | while IFS= read -r line; do
    # Color code based on content
    if echo "$line" | grep -qi "error\|exception\|failed"; then
        echo -e "${RED}$line${NC}"
    elif echo "$line" | grep -qi "appointment.*created\|booking.*success\|scheduled"; then
        echo -e "${GREEN}$line${NC}"
    elif echo "$line" | grep -qi "warning\|warn"; then
        echo -e "${YELLOW}$line${NC}"
    else
        echo "$line"
    fi
done

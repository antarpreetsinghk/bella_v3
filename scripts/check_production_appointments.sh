#!/bin/bash
#
# Check Production Appointments and Calendar Sync
# Queries production database via Docker and verifies calendar sync
#
# Usage:
#   ./scripts/check_production_appointments.sh [minutes]
#
# Arguments:
#   minutes - Look back this many minutes (default: 15)
#

set -e

# Configuration
PRODUCTION_HOST="${PRODUCTION_HOST:-15.157.56.64}"
SSH_USER="${SSH_USER:-ubuntu}"
DB_CONTAINER="${DB_CONTAINER:-bella-db}"
LOOKBACK_MINUTES="${1:-15}"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Production Appointment & Calendar Check${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "Host:        $PRODUCTION_HOST"
echo -e "Lookback:    $LOOKBACK_MINUTES minutes"
echo -e "Timestamp:   $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo ""

echo -e "${CYAN}Querying production database...${NC}"
echo ""

# SQL query to get recent appointments with user info and calendar sync status
SQL_QUERY="
SELECT
    a.id,
    u.full_name,
    u.mobile,
    a.starts_at,
    a.duration_min,
    a.status,
    a.is_test_data,
    a.google_event_id,
    a.created_at,
    EXTRACT(EPOCH FROM (NOW() - a.created_at))/60 as age_minutes
FROM appointments a
JOIN users u ON a.user_id = u.id
WHERE a.created_at >= NOW() - INTERVAL '$LOOKBACK_MINUTES minutes'
ORDER BY a.created_at DESC;
"

# Execute query on production database
RESULT=$(ssh -o ConnectTimeout=10 "$SSH_USER@$PRODUCTION_HOST" \
    "docker exec $DB_CONTAINER psql -U bella_user -d bella_db -t -A -F '|' -c \"$SQL_QUERY\"" 2>&1)

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to query production database${NC}"
    echo "$RESULT"
    exit 1
fi

# Check if any results
if [ -z "$RESULT" ] || [ "$RESULT" = "" ]; then
    echo -e "${YELLOW}⚠️  No appointments found in last $LOOKBACK_MINUTES minutes${NC}"
    echo -e "${CYAN}ℹ️  Try increasing the time window:${NC}"
    echo -e "   $0 30    # Look back 30 minutes"
    exit 0
fi

# Parse and display results
echo "$RESULT" | while IFS='|' read -r id name phone starts_at duration status is_test google_event created_at age; do
    [ -z "$id" ] && continue

    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}Appointment #$id${NC}"
    echo -e "User:         $name"
    echo -e "Phone:        $phone"
    echo -e "Starts At:    $starts_at"
    echo -e "Duration:     $duration minutes"
    echo -e "Status:       $status"
    echo -e "Test Data:    $is_test"
    echo -e "Created:      $created_at"
    echo -e "Age:          ${age%.*} minutes ago"
    echo ""

    # Check calendar sync
    if [ -n "$google_event" ] && [ "$google_event" != "" ]; then
        echo -e "${GREEN}✅ Synced to Google Calendar${NC}"
        echo -e "Event ID:     $google_event"
        echo -e "Calendar URL: https://calendar.google.com/calendar/event?eid=$google_event"
    else
        echo -e "${RED}❌ NOT synced to Google Calendar${NC}"
        echo -e "${CYAN}Check production logs for sync errors:${NC}"
        echo -e "  ssh $SSH_USER@$PRODUCTION_HOST \"docker logs bella_app --since ${LOOKBACK_MINUTES}m 2>&1 | grep -iE 'appointment.*$id|calendar.*$id|google_event'\""
    fi
    echo ""
done

# Summary count
COUNT=$(echo "$RESULT" | grep -c '^' || echo "0")
SYNCED=$(echo "$RESULT" | awk -F'|' '$8 != "" {count++} END {print count+0}')

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Summary${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "Total appointments:   $COUNT"
echo -e "Synced to calendar:   ${GREEN}$SYNCED${NC}"
echo -e "Not synced:           ${RED}$((COUNT - SYNCED))${NC}"
echo ""

if [ $SYNCED -lt $COUNT ]; then
    echo -e "${YELLOW}⚠️  Some appointments failed to sync to Google Calendar${NC}"
    echo -e "${CYAN}Check if GOOGLE_CALENDAR_ENABLED=true in production${NC}"
fi

echo -e "${GREEN}✅ Check complete${NC}"

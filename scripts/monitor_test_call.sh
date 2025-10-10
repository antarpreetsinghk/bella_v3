#!/bin/bash
#
# Monitor Production for Test Call
# Watches logs and database for appointment creation and calendar sync
#
# Usage:
#   ./scripts/monitor_test_call.sh
#

set -e

# Configuration
PRODUCTION_HOST="${PRODUCTION_HOST:-15.157.56.64}"
SSH_USER="${SSH_USER:-ubuntu}"
SSH_KEY="$HOME/.ssh/bella-voice-app"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Test Call Monitoring Dashboard${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${CYAN}Twilio Number:${NC} +14382565719"
echo -e "${CYAN}Production Server:${NC} $PRODUCTION_HOST"
echo -e "${CYAN}Monitoring:${NC} Real-time logs and database"
echo ""
echo -e "${YELLOW}📞 Ready to receive test call!${NC}"
echo -e "${YELLOW}Call +14382565719 now and complete the booking flow.${NC}"
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Function to check latest appointment
check_appointment() {
    ssh -i "$SSH_KEY" "$SSH_USER@$PRODUCTION_HOST" \
        "docker exec bella-db psql -U bella_user -d bella_db -t -A -F '|' -c \
        \"SELECT
            a.id,
            u.full_name,
            u.mobile,
            a.starts_at,
            a.google_event_id,
            EXTRACT(EPOCH FROM (NOW() - a.created_at)) as age_seconds
         FROM appointments a
         JOIN users u ON a.user_id = u.id
         ORDER BY a.created_at DESC
         LIMIT 1;\"" 2>/dev/null
}

# Get initial appointment count
INITIAL_COUNT=$(ssh -i "$SSH_KEY" "$SSH_USER@$PRODUCTION_HOST" \
    "docker exec bella-db psql -U bella_user -d bella_db -t -c 'SELECT COUNT(*) FROM appointments;'" 2>/dev/null | tr -d ' ')

echo -e "${CYAN}Initial appointment count:${NC} $INITIAL_COUNT"
echo ""
echo -e "${YELLOW}Waiting for new appointment...${NC}"
echo ""

# Monitor logs in background
ssh -i "$SSH_KEY" "$SSH_USER@$PRODUCTION_HOST" \
    "docker logs -f bella-app 2>&1" | \
    grep --line-buffered -iE 'voice.*webhook|appointment.*created|google.*event|calendar.*sync' | \
    while read -r line; do
        if echo "$line" | grep -qi "appointment.*created"; then
            echo -e "${GREEN}✅ $line${NC}"
        elif echo "$line" | grep -qi "google.*event\|calendar"; then
            echo -e "${CYAN}📅 $line${NC}"
        else
            echo -e "${YELLOW}📞 $line${NC}"
        fi
    done &

LOG_PID=$!

# Monitor database for new appointments
echo -e "${CYAN}[Monitoring] Watching for new appointments...${NC}"
echo ""

TIMEOUT=300  # 5 minutes timeout
ELAPSED=0
INTERVAL=3

while [ $ELAPSED -lt $TIMEOUT ]; do
    sleep $INTERVAL
    ELAPSED=$((ELAPSED + INTERVAL))

    # Check appointment count
    CURRENT_COUNT=$(ssh -i "$SSH_KEY" "$SSH_USER@$PRODUCTION_HOST" \
        "docker exec bella-db psql -U bella_user -d bella_db -t -c 'SELECT COUNT(*) FROM appointments;'" 2>/dev/null | tr -d ' ')

    if [ "$CURRENT_COUNT" -gt "$INITIAL_COUNT" ]; then
        echo ""
        echo -e "${GREEN}🎉 NEW APPOINTMENT DETECTED!${NC}"
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""

        # Get appointment details
        APPOINTMENT=$(check_appointment)

        ID=$(echo "$APPOINTMENT" | cut -d'|' -f1)
        NAME=$(echo "$APPOINTMENT" | cut -d'|' -f2)
        PHONE=$(echo "$APPOINTMENT" | cut -d'|' -f3)
        TIME=$(echo "$APPOINTMENT" | cut -d'|' -f4)
        CALENDAR_ID=$(echo "$APPOINTMENT" | cut -d'|' -f5)
        AGE=$(echo "$APPOINTMENT" | cut -d'|' -f6)

        echo -e "${CYAN}Appointment Details:${NC}"
        echo -e "  ID:           $ID"
        echo -e "  Customer:     $NAME"
        echo -e "  Phone:        $PHONE"
        echo -e "  Time:         $TIME"
        echo -e "  Created:      ${AGE%.*} seconds ago"
        echo ""

        # Check calendar sync
        if [ -n "$CALENDAR_ID" ] && [ "$CALENDAR_ID" != "" ]; then
            echo -e "${GREEN}✅ GOOGLE CALENDAR SYNC: SUCCESSFUL${NC}"
            echo -e "${CYAN}Calendar Event ID:${NC} $CALENDAR_ID"
            echo -e "${CYAN}View Event:${NC} https://calendar.google.com/calendar/event?eid=$CALENDAR_ID"
        else
            echo -e "${RED}❌ GOOGLE CALENDAR SYNC: FAILED or PENDING${NC}"
            echo -e "${YELLOW}Checking logs for sync errors...${NC}"

            # Check for calendar errors in last minute
            ERRORS=$(ssh -i "$SSH_KEY" "$SSH_USER@$PRODUCTION_HOST" \
                "docker logs bella-app --since 1m 2>&1 | grep -iE 'calendar.*error|google.*failed'" 2>/dev/null)

            if [ -n "$ERRORS" ]; then
                echo -e "${RED}Calendar sync errors found:${NC}"
                echo "$ERRORS"
            else
                echo -e "${YELLOW}No errors found. Calendar sync may be in progress...${NC}"
                echo -e "${YELLOW}Wait a few seconds and check again.${NC}"
            fi
        fi

        echo ""
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

        # Stop monitoring
        kill $LOG_PID 2>/dev/null
        exit 0
    fi

    # Show progress
    if [ $((ELAPSED % 15)) -eq 0 ]; then
        echo -e "${CYAN}[$(date +%H:%M:%S)] Still waiting... (${ELAPSED}s elapsed)${NC}"
    fi
done

echo ""
echo -e "${YELLOW}⏱️  Timeout reached (5 minutes)${NC}"
echo -e "${YELLOW}No new appointment detected.${NC}"
echo ""
echo -e "Did you complete the phone call?"
echo -e "Check appointment count: $CURRENT_COUNT (was $INITIAL_COUNT)"

# Stop log monitoring
kill $LOG_PID 2>/dev/null

exit 1

#!/bin/bash

# Permanent Speech Monitor Startup Script
# Usage: ./start_speech_monitor.sh [daemon|dashboard|report]

set -e

MODE=${1:-daemon}

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}🎙️  Bella V3 Permanent Speech Monitor${NC}"
echo "================================================"

# Check virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
    echo -e "${GREEN}✓${NC} Virtual environment activated"
else
    echo -e "${YELLOW}❌ Virtual environment not found. Run setup-dev.sh first.${NC}"
    exit 1
fi

# Check AWS CLI access
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo -e "${YELLOW}❌ AWS CLI not configured or no access${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} AWS access verified"

case $MODE in
    daemon)
        echo -e "${BLUE}🚀 Starting monitoring daemon...${NC}"
        echo "   This will run continuously and capture all speech data"
        echo "   Press Ctrl+C to stop"
        echo ""
        python permanent_speech_monitor.py --start-daemon
        ;;
    dashboard)
        echo -e "${BLUE}📊 Generating dashboard...${NC}"
        python permanent_speech_monitor.py --dashboard
        ;;
    report)
        echo -e "${BLUE}📋 Generating report...${NC}"
        python permanent_speech_monitor.py --report
        ;;
    *)
        echo "Usage: $0 [daemon|dashboard|report]"
        echo ""
        echo "Modes:"
        echo "  daemon    - Start continuous monitoring (default)"
        echo "  dashboard - Generate HTML dashboard"
        echo "  report    - Generate text report"
        echo ""
        echo "Examples:"
        echo "  ./start_speech_monitor.sh daemon"
        echo "  ./start_speech_monitor.sh dashboard"
        echo "  ./start_speech_monitor.sh report"
        ;;
esac
#!/bin/bash
#
# Developer Test Script - Ultra-fast feedback loop
# Optimized for immediate validation during development
#

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
FAST_MODE=${1:-auto}  # auto, smoke, essential, changed

echo -e "${BLUE}⚡ Developer Test Runner${NC}"
echo "========================="

start_time=$(date +%s)

case $FAST_MODE in
    "smoke")
        echo -e "${YELLOW}🚀 Running smoke tests only${NC}"
        ./scripts/smoke-tests.sh
        ;;

    "essential")
        echo -e "${YELLOW}🧪 Running essential tests${NC}"
        ./scripts/essential-tests.sh
        ;;

    "changed")
        echo -e "${YELLOW}🎯 Testing changed files only${NC}"
        ./scripts/test-changed-files.sh
        ;;

    "auto"|*)
        echo -e "${YELLOW}🤖 Auto-detecting best test strategy${NC}"

        # Check if there are uncommitted changes
        if ! git diff --quiet; then
            echo "Uncommitted changes detected - running smart file selection"
            ./scripts/test-changed-files.sh
        elif ! git diff --quiet HEAD~1; then
            echo "Recent commits detected - running essential tests"
            ./scripts/essential-tests.sh
        else
            echo "No recent changes - running smoke tests"
            ./scripts/smoke-tests.sh
        fi
        ;;
esac

end_time=$(date +%s)
duration=$((end_time - start_time))

echo -e "\n${BLUE}📊 Developer Test Summary${NC}"
echo "=========================="
echo "Test mode: $FAST_MODE"
echo "Duration: ${duration}s"

if [ $duration -lt 30 ]; then
    echo -e "${GREEN}🚀 Lightning fast! Perfect for rapid development${NC}"
elif [ $duration -lt 120 ]; then
    echo -e "${YELLOW}⚡ Good performance for development workflow${NC}"
else
    echo -e "${RED}⚠️  Consider using smoke tests for faster feedback${NC}"
fi

echo -e "\n${BLUE}💡 Next Steps${NC}"
echo "============="
echo "• Fast smoke test: ./scripts/dev-test.sh smoke"
echo "• Test your changes: ./scripts/dev-test.sh changed"
echo "• Pre-commit check: ./scripts/essential-tests.sh"
echo "• Full validation: ./scripts/comprehensive-tests.sh"
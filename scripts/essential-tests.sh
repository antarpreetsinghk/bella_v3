#!/bin/bash
#
# Essential Tests - Core functionality validation (< 2 minutes)
# Pre-commit and pre-deployment validation
#

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🧪 Running Essential Tests (< 2 minutes)${NC}"
echo "================================================"

start_time=$(date +%s)

# Run smoke and essential tests in parallel
if pytest -n auto -m "smoke or essential" \
    --tb=short \
    --disable-warnings \
    --cov=app \
    --cov-report=term-missing \
    --cov-fail-under=70 \
    tests/; then

    end_time=$(date +%s)
    duration=$((end_time - start_time))

    echo -e "\n${GREEN}✅ All essential tests passed in ${duration}s${NC}"

    if [ $duration -gt 120 ]; then
        echo -e "${YELLOW}⚠️  Warning: Essential tests took longer than 2min target${NC}"
        echo -e "${YELLOW}💡 Consider optimizing slow tests or moving them to comprehensive suite${NC}"
    fi

    exit 0
else
    end_time=$(date +%s)
    duration=$((end_time - start_time))

    echo -e "\n${RED}❌ Essential tests failed after ${duration}s${NC}"
    echo -e "${YELLOW}💡 Core functionality issues detected - do not commit/deploy${NC}"

    exit 1
fi
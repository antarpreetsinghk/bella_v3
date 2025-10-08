#!/bin/bash
#
# Smoke Tests - Ultra-fast validation (< 30 seconds)
# Critical path validation for immediate developer feedback
#

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🚀 Running Smoke Tests (< 30 seconds)${NC}"
echo "================================================"

start_time=$(date +%s)

# Run only smoke-marked tests in parallel
if pytest -n auto -m smoke \
    --tb=short \
    --quiet \
    --disable-warnings \
    --no-cov \
    tests/; then

    end_time=$(date +%s)
    duration=$((end_time - start_time))

    echo -e "\n${GREEN}✅ All smoke tests passed in ${duration}s${NC}"

    if [ $duration -gt 30 ]; then
        echo -e "${YELLOW}⚠️  Warning: Smoke tests took longer than 30s target${NC}"
    fi

    exit 0
else
    end_time=$(date +%s)
    duration=$((end_time - start_time))

    echo -e "\n${RED}❌ Smoke tests failed after ${duration}s${NC}"
    echo -e "${YELLOW}💡 Fix these critical issues before continuing${NC}"

    exit 1
fi
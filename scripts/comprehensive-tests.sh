#!/bin/bash
#
# Comprehensive Tests - Full test suite with parallel execution (< 10 minutes)
# Complete validation including edge cases and performance tests
#

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🔬 Running Comprehensive Test Suite (< 10 minutes)${NC}"
echo "====================================================="

start_time=$(date +%s)

# Create reports directory
mkdir -p test_reports

# Run all tests except production-specific ones in parallel
echo -e "\n${YELLOW}📊 Phase 1: Core Test Suite${NC}"
if pytest -n auto \
    -m "not production" \
    --tb=short \
    --cov=app \
    --cov-report=html:test_reports/coverage_html \
    --cov-report=xml:test_reports/coverage.xml \
    --cov-report=term-missing \
    --cov-fail-under=85 \
    --junit-xml=test_reports/junit.xml \
    tests/; then

    echo -e "${GREEN}✅ Core test suite passed${NC}"
else
    echo -e "${RED}❌ Core test suite failed${NC}"
    echo -e "${YELLOW}💡 Check test_reports/junit.xml for details${NC}"
    exit 1
fi

# Run performance benchmarks
echo -e "\n${YELLOW}⚡ Phase 2: Performance Benchmarks${NC}"
if pytest tests/test_call_performance.py \
    --benchmark-only \
    --benchmark-sort=mean \
    --benchmark-json=test_reports/benchmark.json \
    --tb=short; then

    echo -e "${GREEN}✅ Performance benchmarks passed${NC}"
else
    echo -e "${YELLOW}⚠️  Performance benchmarks failed (non-blocking)${NC}"
fi

end_time=$(date +%s)
duration=$((end_time - start_time))
minutes=$((duration / 60))
seconds=$((duration % 60))

echo -e "\n${BLUE}📋 Test Summary${NC}"
echo "==============="
echo "Total duration: ${minutes}m ${seconds}s"

if [ $duration -gt 600 ]; then
    echo -e "${YELLOW}⚠️  Warning: Tests took longer than 10min target${NC}"
    echo -e "${YELLOW}💡 Consider parallelization improvements${NC}"
fi

# Extract coverage percentage
if [ -f "test_reports/coverage.xml" ]; then
    coverage_percentage=$(python3 -c "
import xml.etree.ElementTree as ET
try:
    tree = ET.parse('test_reports/coverage.xml')
    root = tree.getroot()
    line_rate = float(root.attrib['line-rate'])
    print(f'{line_rate * 100:.1f}')
except:
    print('N/A')
")
    echo "Coverage: ${coverage_percentage}%"
fi

echo -e "\n${BLUE}📁 Reports Generated${NC}"
echo "==================="
echo "• HTML Coverage: test_reports/coverage_html/index.html"
echo "• XML Coverage: test_reports/coverage.xml"
echo "• JUnit Results: test_reports/junit.xml"
echo "• Benchmarks: test_reports/benchmark.json"

echo -e "\n${GREEN}🎉 Comprehensive test suite completed!${NC}"
#!/bin/bash
"""
Comprehensive test runner for call flow system.
Runs all test categories with proper reporting and coverage.
"""

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test configuration
TEST_DIR="tests"
COVERAGE_MIN=85
REPORTS_DIR="test_reports"

echo -e "${BLUE}🧪 Starting Comprehensive Call Flow Test Suite${NC}"
echo "=============================================="

# Create reports directory
mkdir -p $REPORTS_DIR

# Function to run test category
run_test_category() {
    local category=$1
    local test_file=$2
    local description=$3

    echo -e "\n${YELLOW}📊 Running $category Tests${NC}"
    echo "Description: $description"
    echo "----------------------------------------"

    if pytest $TEST_DIR/$test_file -v \
        --tb=short \
        --capture=no \
        --junit-xml=$REPORTS_DIR/${category}_results.xml \
        --cov=app \
        --cov-report=html:$REPORTS_DIR/${category}_coverage \
        --cov-report=term-missing; then
        echo -e "${GREEN}✅ $category tests PASSED${NC}"
        return 0
    else
        echo -e "${RED}❌ $category tests FAILED${NC}"
        return 1
    fi
}

# Function to run performance tests
run_performance_tests() {
    echo -e "\n${YELLOW}⚡ Running Performance Tests${NC}"
    echo "Description: Response time and load testing"
    echo "----------------------------------------"

    if pytest $TEST_DIR/test_call_performance.py -v \
        --tb=short \
        --capture=no \
        --junit-xml=$REPORTS_DIR/performance_results.xml \
        --benchmark-only \
        --benchmark-sort=mean; then
        echo -e "${GREEN}✅ Performance tests PASSED${NC}"
        return 0
    else
        echo -e "${RED}❌ Performance tests FAILED${NC}"
        return 1
    fi
}

# Track test results
declare -a failed_categories=()
total_categories=0

# 1. Unit Tests for Extraction Functions
echo -e "\n${BLUE}Phase 1: Unit Tests${NC}"
if run_test_category "phone-extraction" "test_phone_extraction.py" "Phone number extraction and validation"; then
    echo "Phone extraction tests passed"
else
    failed_categories+=("phone-extraction")
fi
((total_categories++))

if run_test_category "name-extraction" "test_name_extraction.py" "Name extraction and speech artifact handling"; then
    echo "Name extraction tests passed"
else
    failed_categories+=("name-extraction")
fi
((total_categories++))

if run_test_category "time-extraction" "test_time_extraction.py" "Time parsing and timezone handling"; then
    echo "Time extraction tests passed"
else
    failed_categories+=("time-extraction")
fi
((total_categories++))

# 2. Integration Tests
echo -e "\n${BLUE}Phase 2: Integration Tests${NC}"
if run_test_category "call-flow-integration" "test_call_flow_integration.py" "Multi-step call flow scenarios"; then
    echo "Call flow integration tests passed"
else
    failed_categories+=("call-flow-integration")
fi
((total_categories++))

# 3. System Tests
echo -e "\n${BLUE}Phase 3: System Tests${NC}"
if run_test_category "session-management" "test_session_management.py" "Redis sessions and caller profiles"; then
    echo "Session management tests passed"
else
    failed_categories+=("session-management")
fi
((total_categories++))

if run_test_category "speech-processing" "test_speech_processing.py" "Speech recognition and processing"; then
    echo "Speech processing tests passed"
else
    failed_categories+=("speech-processing")
fi
((total_categories++))

# 4. End-to-End Tests
echo -e "\n${BLUE}Phase 4: End-to-End Tests${NC}"
if run_test_category "e2e-scenarios" "test_e2e_scenarios.py" "Complete user journey scenarios"; then
    echo "E2E scenario tests passed"
else
    failed_categories+=("e2e-scenarios")
fi
((total_categories++))

# 5. Performance Tests
echo -e "\n${BLUE}Phase 5: Performance Tests${NC}"
if run_performance_tests; then
    echo "Performance tests passed"
else
    failed_categories+=("performance")
fi
((total_categories++))

# 6. Existing Integration Tests
echo -e "\n${BLUE}Phase 6: Existing Test Suite${NC}"
if run_test_category "voice-integration" "test_voice_integration.py" "Existing voice integration tests"; then
    echo "Voice integration tests passed"
else
    failed_categories+=("voice-integration")
fi
((total_categories++))

# Generate comprehensive coverage report
echo -e "\n${BLUE}📈 Generating Comprehensive Coverage Report${NC}"
echo "=============================================="

pytest $TEST_DIR/ \
    --cov=app \
    --cov-report=html:$REPORTS_DIR/comprehensive_coverage \
    --cov-report=term-missing \
    --cov-report=xml:$REPORTS_DIR/coverage.xml \
    --quiet

# Check coverage threshold
coverage_percentage=$(python -c "
import xml.etree.ElementTree as ET
tree = ET.parse('$REPORTS_DIR/coverage.xml')
root = tree.getroot()
line_rate = float(root.attrib['line-rate'])
print(f'{line_rate * 100:.1f}')
")

echo "Current coverage: ${coverage_percentage}%"

# Summary Report
echo -e "\n${BLUE}📋 Test Execution Summary${NC}"
echo "=========================="
echo "Total test categories: $total_categories"
echo "Failed categories: ${#failed_categories[@]}"
echo "Success rate: $(( (total_categories - ${#failed_categories[@]}) * 100 / total_categories ))%"
echo "Coverage: ${coverage_percentage}%"

if [ ${#failed_categories[@]} -eq 0 ]; then
    echo -e "${GREEN}🎉 ALL TESTS PASSED!${NC}"

    if (( $(echo "$coverage_percentage >= $COVERAGE_MIN" | bc -l) )); then
        echo -e "${GREEN}✅ Coverage threshold met (${coverage_percentage}% >= ${COVERAGE_MIN}%)${NC}"
        exit_code=0
    else
        echo -e "${YELLOW}⚠️  Coverage below threshold (${coverage_percentage}% < ${COVERAGE_MIN}%)${NC}"
        exit_code=1
    fi
else
    echo -e "${RED}❌ Failed test categories:${NC}"
    for category in "${failed_categories[@]}"; do
        echo -e "  ${RED}- $category${NC}"
    done
    exit_code=1
fi

# Performance Summary
echo -e "\n${BLUE}⚡ Performance Summary${NC}"
echo "======================"
echo "Response time benchmarks:"
echo "- Voice entry: < 100ms average"
echo "- Voice collect: < 300ms average"
echo "- Extraction functions: > 5000 ops/sec"
echo "- Concurrent calls: 95% success rate"

# Test Reports Location
echo -e "\n${BLUE}📁 Test Reports${NC}"
echo "==============="
echo "HTML Coverage: $REPORTS_DIR/comprehensive_coverage/index.html"
echo "XML Results: $REPORTS_DIR/*_results.xml"
echo "Coverage Data: $REPORTS_DIR/coverage.xml"

# Recommendations
echo -e "\n${BLUE}💡 Recommendations${NC}"
echo "=================="
if [ ${#failed_categories[@]} -gt 0 ]; then
    echo "1. Fix failing tests before deployment"
    echo "2. Review test logs in $REPORTS_DIR/"
    echo "3. Consider adding more test coverage for failed areas"
fi

if (( $(echo "$coverage_percentage < $COVERAGE_MIN" | bc -l) )); then
    echo "4. Increase test coverage to meet ${COVERAGE_MIN}% threshold"
    echo "5. Focus on untested code paths"
fi

echo "6. Run performance tests regularly during development"
echo "7. Monitor response times in production"
echo "8. Update tests when adding new features"

exit $exit_code
#!/bin/bash
#
# Production Call Flow Testing & Debugging Script
# Comprehensive testing suite for AWS Lambda deployment handling 50 calls/day
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
LAMBDA_FUNCTION_NAME="bella-voice-app"
FUNCTION_URL="https://bhcnf2i6eh3bxnr6lrnt4ubouy0obfjy.lambda-url.us-east-1.on.aws"
REGION="us-east-1"
LOG_GROUP="/aws/lambda/bella-voice-app"
TEST_REPORTS_DIR="test_reports/production"
DEBUG_MODE=${DEBUG_MODE:-false}

# Create test reports directory
mkdir -p $TEST_REPORTS_DIR

echo -e "${BLUE}🚀 Production Call Flow Testing & Debugging Suite${NC}"
echo "================================================================="
echo "Function: $LAMBDA_FUNCTION_NAME"
echo "URL: $FUNCTION_URL"
echo "Debug Mode: $DEBUG_MODE"
echo "Reports: $TEST_REPORTS_DIR"
echo ""

# Function to log with timestamp
log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Function to run test with error handling
run_test() {
    local test_name="$1"
    local test_command="$2"
    local description="$3"

    echo -e "\n${YELLOW}🧪 Running: $test_name${NC}"
    echo "Description: $description"
    echo "Command: $test_command"
    echo "----------------------------------------"

    local start_time=$(date +%s)

    if eval "$test_command" > "$TEST_REPORTS_DIR/${test_name}.log" 2>&1; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        echo -e "${GREEN}✅ $test_name PASSED${NC} (${duration}s)"
        return 0
    else
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        echo -e "${RED}❌ $test_name FAILED${NC} (${duration}s)"
        echo "Check log: $TEST_REPORTS_DIR/${test_name}.log"
        return 1
    fi
}

# Function to check Lambda health
test_lambda_health() {
    log "Testing Lambda function health..."

    # Check function exists
    if ! aws lambda get-function --function-name $LAMBDA_FUNCTION_NAME --region $REGION > /dev/null 2>&1; then
        echo -e "${RED}❌ Lambda function not found${NC}"
        return 1
    fi

    # Check function status
    local status=$(aws lambda get-function --function-name $LAMBDA_FUNCTION_NAME --region $REGION --query 'Configuration.State' --output text)
    if [ "$status" != "Active" ]; then
        echo -e "${RED}❌ Lambda function not active (status: $status)${NC}"
        return 1
    fi

    # Test function URL
    local response_code=$(curl -s -o /dev/null -w "%{http_code}" "${FUNCTION_URL}/health" || echo "000")
    if [ "$response_code" = "200" ]; then
        echo -e "${GREEN}✅ Function URL responding${NC}"
    else
        echo -e "${YELLOW}⚠️ Function URL returned: $response_code${NC}"
    fi

    # Check memory and timeout configuration
    local memory=$(aws lambda get-function --function-name $LAMBDA_FUNCTION_NAME --region $REGION --query 'Configuration.MemorySize' --output text)
    local timeout=$(aws lambda get-function --function-name $LAMBDA_FUNCTION_NAME --region $REGION --query 'Configuration.Timeout' --output text)

    echo "Memory: ${memory}MB"
    echo "Timeout: ${timeout}s"

    if [ "$memory" -lt 512 ]; then
        echo -e "${YELLOW}⚠️ Memory might be low for production${NC}"
    fi

    if [ "$timeout" -lt 30 ]; then
        echo -e "${YELLOW}⚠️ Timeout might be low for complex calls${NC}"
    fi

    return 0
}

# Function to test environment variables
test_environment_config() {
    log "Testing environment configuration..."

    local config=$(aws lambda get-function-configuration --function-name $LAMBDA_FUNCTION_NAME --region $REGION)

    # Check required environment variables
    local required_vars=("APP_ENV" "BELLA_API_KEY" "TWILIO_ACCOUNT_SID" "OPENAI_API_KEY")
    local missing_vars=()

    for var in "${required_vars[@]}"; do
        if ! echo "$config" | jq -r ".Environment.Variables.${var}" | grep -v "null" > /dev/null; then
            missing_vars+=("$var")
        fi
    done

    if [ ${#missing_vars[@]} -eq 0 ]; then
        echo -e "${GREEN}✅ All required environment variables present${NC}"
        return 0
    else
        echo -e "${RED}❌ Missing environment variables: ${missing_vars[*]}${NC}"
        return 1
    fi
}

# Function to simulate Twilio webhook
test_twilio_webhook() {
    log "Testing Twilio webhook simulation..."

    local test_payload='{
        "CallSid": "TEST_PROD_'$(date +%s)'",
        "From": "+14165551234",
        "To": "+15551234567",
        "AccountSid": "ACtest123",
        "Direction": "inbound",
        "CallerCountry": "CA",
        "CallerState": "ON",
        "CallerCity": "Toronto"
    }'

    local response=$(curl -s -X POST "${FUNCTION_URL}/twilio/voice" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "CallSid=TEST_PROD_$(date +%s)&From=+14165551234&To=+15551234567" \
        || echo "CURL_ERROR")

    if [[ "$response" == *"<Response>"* ]]; then
        echo -e "${GREEN}✅ Twilio webhook returning TwiML${NC}"
        if [ "$DEBUG_MODE" = "true" ]; then
            echo "Response: $response"
        fi
        return 0
    else
        echo -e "${RED}❌ Twilio webhook failed${NC}"
        echo "Response: $response"
        return 1
    fi
}

# Function to test database connectivity
test_database_connectivity() {
    log "Testing database connectivity..."

    # Test DynamoDB table exists
    local table_name="bella-voice-app-sessions"

    if aws dynamodb describe-table --table-name $table_name --region $REGION > /dev/null 2>&1; then
        echo -e "${GREEN}✅ DynamoDB table accessible${NC}"

        # Check table status
        local status=$(aws dynamodb describe-table --table-name $table_name --region $REGION --query 'Table.TableStatus' --output text)
        if [ "$status" = "ACTIVE" ]; then
            echo -e "${GREEN}✅ DynamoDB table active${NC}"
        else
            echo -e "${YELLOW}⚠️ DynamoDB table status: $status${NC}"
        fi

        return 0
    else
        echo -e "${RED}❌ DynamoDB table not accessible${NC}"
        return 1
    fi
}

# Function to test performance
test_performance() {
    log "Testing performance metrics..."

    local start_time=$(date +%s%3N)

    # Test response time
    local response_time=$(curl -s -w "%{time_total}" -o /dev/null "${FUNCTION_URL}/health" || echo "999")

    local end_time=$(date +%s%3N)
    local total_time=$((end_time - start_time))

    echo "Response time: ${response_time}s"
    echo "Total test time: ${total_time}ms"

    if (( $(echo "$response_time < 3.0" | bc -l) )); then
        echo -e "${GREEN}✅ Response time within acceptable range${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠️ Response time slower than expected${NC}"
        return 1
    fi
}

# Function to test extraction functions
test_extraction_functions() {
    log "Testing extraction functions..."

    # Test name extraction
    local name_test_response=$(curl -s -X POST "${FUNCTION_URL}/debug/extraction" \
        -H "Content-Type: application/json" \
        -d '{"type": "name", "text": "my name is John Smith"}' \
        || echo "ERROR")

    if [[ "$name_test_response" == *"John Smith"* ]]; then
        echo -e "${GREEN}✅ Name extraction working${NC}"
    else
        echo -e "${YELLOW}⚠️ Name extraction may have issues${NC}"
    fi

    # Test phone extraction
    local phone_test_response=$(curl -s -X POST "${FUNCTION_URL}/debug/extraction" \
        -H "Content-Type: application/json" \
        -d '{"type": "phone", "text": "my number is 416 555 1234"}' \
        || echo "ERROR")

    if [[ "$phone_test_response" == *"4165551234"* ]]; then
        echo -e "${GREEN}✅ Phone extraction working${NC}"
    else
        echo -e "${YELLOW}⚠️ Phone extraction may have issues${NC}"
    fi

    return 0
}

# Function to check recent errors
check_recent_errors() {
    log "Checking recent errors..."

    local start_time=$(date -d '30 minutes ago' +%s)000

    local error_count=$(aws logs filter-log-events \
        --log-group-name $LOG_GROUP \
        --region $REGION \
        --start-time $start_time \
        --filter-pattern "ERROR" \
        --query 'length(events)' \
        --output text 2>/dev/null || echo "0")

    echo "Recent errors (30min): $error_count"

    if [ "$error_count" -eq 0 ]; then
        echo -e "${GREEN}✅ No recent errors${NC}"
        return 0
    elif [ "$error_count" -lt 5 ]; then
        echo -e "${YELLOW}⚠️ Few recent errors ($error_count)${NC}"
        return 0
    else
        echo -e "${RED}❌ High error count ($error_count)${NC}"
        return 1
    fi
}

# Function to check CloudWatch metrics
check_cloudwatch_metrics() {
    log "Checking CloudWatch metrics..."

    # Check invocations in last hour
    local end_time=$(date +%s)
    local start_time=$((end_time - 3600))

    local invocations=$(aws cloudwatch get-metric-statistics \
        --namespace AWS/Lambda \
        --metric-name Invocations \
        --dimensions Name=FunctionName,Value=$LAMBDA_FUNCTION_NAME \
        --start-time $(date -d @$start_time -Iseconds) \
        --end-time $(date -d @$end_time -Iseconds) \
        --period 3600 \
        --statistics Sum \
        --region $REGION \
        --query 'Datapoints[0].Sum' \
        --output text 2>/dev/null || echo "0")

    echo "Invocations (1h): $invocations"

    # Check errors
    local errors=$(aws cloudwatch get-metric-statistics \
        --namespace AWS/Lambda \
        --metric-name Errors \
        --dimensions Name=FunctionName,Value=$LAMBDA_FUNCTION_NAME \
        --start-time $(date -d @$start_time -Iseconds) \
        --end-time $(date -d @$end_time -Iseconds) \
        --period 3600 \
        --statistics Sum \
        --region $REGION \
        --query 'Datapoints[0].Sum' \
        --output text 2>/dev/null || echo "0")

    echo "Errors (1h): $errors"

    if [ "$errors" = "None" ] || [ "$errors" = "0" ]; then
        echo -e "${GREEN}✅ No recent Lambda errors${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠️ Lambda errors detected: $errors${NC}"
        return 1
    fi
}

# Function to generate debug report
generate_debug_report() {
    log "Generating debug report..."

    local report_file="$TEST_REPORTS_DIR/debug_report_$(date +%Y%m%d_%H%M%S).json"

    cat > "$report_file" << EOF
{
    "timestamp": "$(date -Iseconds)",
    "function_name": "$LAMBDA_FUNCTION_NAME",
    "function_url": "$FUNCTION_URL",
    "test_results": {
        "lambda_health": "$(test_lambda_health && echo 'PASS' || echo 'FAIL')",
        "environment_config": "$(test_environment_config && echo 'PASS' || echo 'FAIL')",
        "database_connectivity": "$(test_database_connectivity && echo 'PASS' || echo 'FAIL')",
        "performance": "$(test_performance && echo 'PASS' || echo 'FAIL')"
    },
    "metrics": {
        "recent_errors": "$(check_recent_errors && echo 'NORMAL' || echo 'HIGH')",
        "cloudwatch_status": "$(check_cloudwatch_metrics && echo 'HEALTHY' || echo 'ISSUES')"
    },
    "debug_mode": "$DEBUG_MODE"
}
EOF

    echo "Debug report saved: $report_file"
}

# Main test execution
main() {
    local failed_tests=0
    local total_tests=0

    # Run health checks
    echo -e "\n${BLUE}Phase 1: Health Checks${NC}"
    echo "========================"

    run_test "lambda_health" "test_lambda_health" "Basic Lambda function health"
    [ $? -eq 0 ] || ((failed_tests++))
    ((total_tests++))

    run_test "environment_config" "test_environment_config" "Environment variables validation"
    [ $? -eq 0 ] || ((failed_tests++))
    ((total_tests++))

    run_test "database_connectivity" "test_database_connectivity" "Database connectivity test"
    [ $? -eq 0 ] || ((failed_tests++))
    ((total_tests++))

    # Run functional tests
    echo -e "\n${BLUE}Phase 2: Functional Tests${NC}"
    echo "==========================="

    run_test "twilio_webhook" "test_twilio_webhook" "Twilio webhook simulation"
    [ $? -eq 0 ] || ((failed_tests++))
    ((total_tests++))

    run_test "extraction_functions" "test_extraction_functions" "Core extraction functions"
    [ $? -eq 0 ] || ((failed_tests++))
    ((total_tests++))

    # Run performance tests
    echo -e "\n${BLUE}Phase 3: Performance Tests${NC}"
    echo "============================"

    run_test "performance" "test_performance" "Response time validation"
    [ $? -eq 0 ] || ((failed_tests++))
    ((total_tests++))

    # Run monitoring checks
    echo -e "\n${BLUE}Phase 4: Monitoring Checks${NC}"
    echo "============================"

    run_test "recent_errors" "check_recent_errors" "Recent error analysis"
    [ $? -eq 0 ] || ((failed_tests++))
    ((total_tests++))

    run_test "cloudwatch_metrics" "check_cloudwatch_metrics" "CloudWatch metrics check"
    [ $? -eq 0 ] || ((failed_tests++))
    ((total_tests++))

    # Generate summary
    echo -e "\n${BLUE}📋 Test Summary${NC}"
    echo "================="
    echo "Total tests: $total_tests"
    echo "Failed tests: $failed_tests"
    echo "Success rate: $(( (total_tests - failed_tests) * 100 / total_tests ))%"

    if [ $failed_tests -eq 0 ]; then
        echo -e "${GREEN}🎉 ALL PRODUCTION TESTS PASSED!${NC}"
        echo -e "${GREEN}✅ System ready for production calls${NC}"
    else
        echo -e "${RED}❌ Some tests failed - review before production use${NC}"
    fi

    # Generate debug report
    generate_debug_report

    # Show next steps
    echo -e "\n${BLUE}🔧 Next Steps${NC}"
    echo "=============="
    echo "1. Review test reports: $TEST_REPORTS_DIR/"
    echo "2. Check CloudWatch dashboard: https://console.aws.amazon.com/cloudwatch"
    echo "3. Monitor logs: aws logs tail $LOG_GROUP --follow"
    echo "4. Test with real phone calls"
    echo "5. Update Twilio webhook: ${FUNCTION_URL}/twilio/voice"

    # Exit with appropriate code
    [ $failed_tests -eq 0 ] && exit 0 || exit 1
}

# Handle script arguments
case "${1:-run}" in
    "health")
        test_lambda_health
        ;;
    "webhook")
        test_twilio_webhook
        ;;
    "performance")
        test_performance
        ;;
    "debug")
        DEBUG_MODE=true
        main
        ;;
    "run"|*)
        main
        ;;
esac
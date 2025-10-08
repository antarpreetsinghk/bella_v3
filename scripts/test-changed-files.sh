#!/bin/bash
#
# Smart Test Selection - Run tests based on changed files
# Dramatically reduces test time for targeted changes
#

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
BRANCH=${1:-main}  # Compare against this branch (default: main)

echo -e "${BLUE}🎯 Smart Test Selection Based on Changed Files${NC}"
echo "================================================="

# Get list of changed files
changed_files=$(git diff --name-only $BRANCH..HEAD | grep -E '\.(py)$' || true)

if [ -z "$changed_files" ]; then
    echo -e "${YELLOW}📂 No Python files changed, running smoke tests only${NC}"
    exec ./scripts/smoke-tests.sh
fi

echo -e "${YELLOW}📝 Changed files detected:${NC}"
echo "$changed_files" | while read file; do
    echo "  • $file"
done

# Map source files to test files
test_files=""

# Function to add test file if it exists
add_test_file() {
    local test_file="$1"
    if [ -f "$test_file" ]; then
        test_files="$test_files $test_file"
        echo "  → $test_file"
    fi
}

echo -e "\n${YELLOW}🔍 Mapping to relevant tests:${NC}"

for file in $changed_files; do
    echo "📄 $file"

    # Direct test file mapping
    if [[ $file == tests/* ]]; then
        add_test_file "$file"
    fi

    # App code to test mapping
    if [[ $file == app/* ]]; then
        # Remove app/ prefix and .py suffix, add test_ prefix
        base_name=$(basename "$file" .py)
        dir_name=$(dirname "$file" | sed 's|app/||')

        # Try different test file patterns
        add_test_file "tests/test_${base_name}.py"
        add_test_file "tests/${dir_name}/test_${base_name}.py"
        add_test_file "tests/integration/test_${base_name}.py"

        # Special mappings for key modules
        case "$file" in
            app/api/routes/twilio.py)
                add_test_file "tests/test_voice_integration.py"
                add_test_file "tests/test_call_flow_integration.py"
                add_test_file "tests/production/test_twilio_simulation.py"
                ;;
            app/services/simple_extraction.py)
                add_test_file "tests/test_name_extraction.py"
                add_test_file "tests/test_phone_extraction.py"
                add_test_file "tests/test_time_extraction.py"
                ;;
            app/services/booking.py)
                add_test_file "tests/test_call_flow_integration.py"
                add_test_file "tests/test_e2e_scenarios.py"
                ;;
            app/services/redis_session.py)
                add_test_file "tests/test_session_management.py"
                ;;
            app/crud/*)
                add_test_file "tests/test_call_flow_integration.py"
                ;;
        esac
    fi

    # Configuration changes - run smoke tests
    if [[ $file == *.ini || $file == requirements.txt || $file == alembic.ini ]]; then
        echo "  → Configuration change detected, will run smoke tests"
        test_files="$test_files SMOKE_TESTS"
    fi
done

# Remove duplicates and empty entries
test_files=$(echo $test_files | tr ' ' '\n' | sort -u | grep -v '^$' | tr '\n' ' ')

if [ -z "$test_files" ]; then
    echo -e "\n${YELLOW}🤔 No specific tests mapped, running essential tests${NC}"
    exec ./scripts/essential-tests.sh
fi

# Check if we should run smoke tests
if echo "$test_files" | grep -q "SMOKE_TESTS"; then
    echo -e "\n${YELLOW}🚀 Configuration changes detected, running smoke tests${NC}"
    exec ./scripts/smoke-tests.sh
fi

echo -e "\n${BLUE}🧪 Running targeted tests${NC}"
echo "========================="

start_time=$(date +%s)

# Run only the mapped test files in parallel
if pytest -n auto \
    --tb=short \
    --cov=app \
    --cov-report=term-missing \
    $test_files; then

    end_time=$(date +%s)
    duration=$((end_time - start_time))

    echo -e "\n${GREEN}✅ Targeted tests passed in ${duration}s${NC}"

    if [ $duration -lt 30 ]; then
        echo -e "${GREEN}🚀 Lightning fast! Consider this your new normal workflow${NC}"
    elif [ $duration -lt 120 ]; then
        echo -e "${YELLOW}⚡ Good performance for targeted testing${NC}"
    else
        echo -e "${YELLOW}⚠️  Consider running fewer tests or optimizing slow ones${NC}"
    fi

    echo -e "\n${BLUE}💡 Next steps:${NC}"
    echo "• Run './scripts/essential-tests.sh' before committing"
    echo "• Run './scripts/comprehensive-tests.sh' before pushing to main"

    exit 0
else
    end_time=$(date +%s)
    duration=$((end_time - start_time))

    echo -e "\n${RED}❌ Targeted tests failed after ${duration}s${NC}"
    echo -e "${YELLOW}💡 Your changes broke existing functionality${NC}"

    exit 1
fi
#!/bin/bash
#
# Safe Production Test Runner
#
# This script provides a safe way to run production database tests with:
# - Pre-flight safety checks
# - Environment validation
# - Automatic cleanup verification
# - Comprehensive error handling
# - Dry-run mode for validation
#
# Usage:
#   ./scripts/run_production_tests.sh [options]
#
# Options:
#   --dry-run           Run pre-flight checks only, don't execute tests
#   --skip-checks       Skip safety checks (NOT RECOMMENDED)
#   --verbose           Enable verbose output
#   --help              Show this help message
#
# Environment Variables Required:
#   PRODUCTION_DB_URL          Production/staging database URL
#   PRODUCTION_TEST_URL        Test environment URL (optional)
#   PRODUCTION_DB_TEST_MODE    Set to 'true' for extra safety (recommended)
#   TEST_DATA_AUTO_CLEANUP     Set to 'true' to enable auto-cleanup (recommended)
#

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DRY_RUN=false
SKIP_CHECKS=false
VERBOSE=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --skip-checks)
            SKIP_CHECKS=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --help)
            head -n 25 "$0" | tail -n 22
            exit 0
            ;;
        *)
            echo -e "${RED}❌ Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Logging functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_section() {
    echo ""
    echo -e "${BLUE}================================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}================================================${NC}"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Pre-flight safety checks
run_safety_checks() {
    log_section "PRE-FLIGHT SAFETY CHECKS"

    local checks_passed=true

    # Check 1: Database URL is set
    log_info "Checking database URL configuration..."
    if [ -z "$PRODUCTION_DB_URL" ]; then
        log_error "PRODUCTION_DB_URL environment variable is not set"
        checks_passed=false
    else
        # Verify it's NOT a production database (simple heuristic)
        if [[ "$PRODUCTION_DB_URL" == *"prod"* ]] && [[ "$PRODUCTION_DB_URL" != *"test"* ]] && [[ "$PRODUCTION_DB_URL" != *"staging"* ]]; then
            log_warning "Database URL contains 'prod' - are you sure this is a test database?"
            read -p "Continue anyway? (yes/no): " confirm
            if [ "$confirm" != "yes" ]; then
                log_error "Aborted by user"
                exit 1
            fi
        fi
        log_success "Database URL is configured"
    fi

    # Check 2: Test mode is enabled (recommended)
    log_info "Checking test mode configuration..."
    if [ "$PRODUCTION_DB_TEST_MODE" != "true" ]; then
        log_warning "PRODUCTION_DB_TEST_MODE is not set to 'true'"
        log_warning "Recommended: export PRODUCTION_DB_TEST_MODE=true"
    else
        log_success "Test mode is enabled"
    fi

    # Check 3: Auto-cleanup is enabled
    log_info "Checking auto-cleanup configuration..."
    if [ "$TEST_DATA_AUTO_CLEANUP" != "true" ]; then
        log_warning "TEST_DATA_AUTO_CLEANUP is not set to 'true'"
        log_warning "Test data may accumulate without cleanup"
    else
        log_success "Auto-cleanup is enabled"
    fi

    # Check 4: Required Python packages
    log_info "Checking Python environment..."
    if ! command_exists python; then
        log_error "Python is not installed or not in PATH"
        checks_passed=false
    else
        log_success "Python is available"
    fi

    # Check 5: pytest is available
    log_info "Checking pytest..."
    if ! python -m pytest --version >/dev/null 2>&1; then
        log_error "pytest is not installed"
        log_info "Install with: pip install pytest pytest-asyncio"
        checks_passed=false
    else
        log_success "pytest is available"
    fi

    # Check 6: Database migration status
    log_info "Checking database migration status..."
    cd "$PROJECT_ROOT"
    if ! command_exists alembic; then
        log_warning "Alembic is not installed - cannot verify migrations"
    else
        current_revision=$(alembic current 2>/dev/null | grep -oP '(?<=\()[a-z0-9]+(?=\))' | head -n1 || echo "none")
        if [ "$current_revision" == "none" ]; then
            log_warning "Could not determine current migration revision"
        else
            log_success "Current migration: $current_revision"
            # Check if is_test_data migration is applied
            if alembic history 2>/dev/null | grep -q "bf439ec8d57f"; then
                log_success "is_test_data migration is available"
            else
                log_warning "is_test_data migration (bf439ec8d57f) not found in history"
            fi
        fi
    fi

    # Check 7: Cleanup utilities are available
    log_info "Checking cleanup utilities..."
    if [ -f "$PROJECT_ROOT/tests/production/cleanup.py" ]; then
        log_success "Cleanup utilities are available"
    else
        log_error "Cleanup utilities not found at tests/production/cleanup.py"
        checks_passed=false
    fi

    # Check 8: Test files exist
    log_info "Checking test files..."
    if [ -f "$PROJECT_ROOT/tests/production/test_production_database_flow.py" ]; then
        log_success "Production database tests found"
    else
        log_error "Production database tests not found"
        checks_passed=false
    fi

    # Summary
    echo ""
    if [ "$checks_passed" = true ]; then
        log_success "All critical safety checks passed"
        return 0
    else
        log_error "Some safety checks failed"
        log_error "Review errors above before running tests"
        return 1
    fi
}

# Get baseline test data count
get_test_data_count() {
    log_info "Counting existing test data..."
    if command_exists python && [ -f "$PROJECT_ROOT/tests/production/cleanup.py" ]; then
        count=$(python "$PROJECT_ROOT/tests/production/cleanup.py" count --db-url="$PRODUCTION_DB_URL" 2>/dev/null | grep -oP '\d+' | tail -n1 || echo "0")
        echo "$count"
    else
        echo "unknown"
    fi
}

# Run the test suite
run_tests() {
    log_section "RUNNING PRODUCTION DATABASE TESTS"

    cd "$PROJECT_ROOT"

    local pytest_args="-v"

    if [ "$VERBOSE" = true ]; then
        pytest_args="$pytest_args -s"
    fi

    log_info "Test suite: tests/production/test_production_database_flow.py"
    log_info "Arguments: $pytest_args"
    echo ""

    # Run pytest
    if python -m pytest tests/production/test_production_database_flow.py $pytest_args; then
        log_success "Test suite completed successfully"
        return 0
    else
        log_error "Test suite failed"
        return 1
    fi
}

# Verify cleanup after tests
verify_cleanup() {
    log_section "POST-TEST CLEANUP VERIFICATION"

    log_info "Verifying test data cleanup..."

    if [ -f "$PROJECT_ROOT/tests/production/cleanup.py" ]; then
        # Get current count
        current_count=$(get_test_data_count)

        log_info "Current test data count: $current_count"

        # Run verification
        if python "$PROJECT_ROOT/tests/production/cleanup.py" verify --db-url="$PRODUCTION_DB_URL" >/dev/null 2>&1; then
            log_success "Cleanup verification completed"
        else
            log_warning "Cleanup verification returned errors"
        fi

        # Check for stale data
        if python "$PROJECT_ROOT/tests/production/cleanup.py" summary --db-url="$PRODUCTION_DB_URL" 2>&1 | grep -q "Cleanup Recommended: YES"; then
            log_warning "Stale test data detected"
            log_info "Run cleanup: python tests/production/cleanup.py cleanup --older-than=24 --no-dry-run"
        else
            log_success "No stale test data"
        fi
    else
        log_warning "Cleanup utilities not available - skipping verification"
    fi
}

# Generate test report
generate_report() {
    log_section "TEST EXECUTION REPORT"

    local end_count=$(get_test_data_count)

    echo ""
    echo "Test Execution Summary:"
    echo "  Start Time:           $start_time"
    echo "  End Time:             $(date '+%Y-%m-%d %H:%M:%S')"
    echo "  Test Data Before:     $baseline_count"
    echo "  Test Data After:      $end_count"
    echo "  Database URL:         ${PRODUCTION_DB_URL:0:50}..."
    echo "  Test Mode:            $PRODUCTION_DB_TEST_MODE"
    echo "  Auto Cleanup:         $TEST_DATA_AUTO_CLEANUP"
    echo ""

    if [ "$tests_passed" = true ]; then
        log_success "🎉 All tests passed successfully!"
    else
        log_error "Some tests failed - review output above"
    fi
}

# Cleanup function for script exit
cleanup_on_exit() {
    local exit_code=$?

    if [ $exit_code -ne 0 ]; then
        log_section "EMERGENCY CLEANUP"
        log_warning "Script exited with error code: $exit_code"
        log_info "Running emergency cleanup verification..."

        if [ -f "$PROJECT_ROOT/tests/production/cleanup.py" ]; then
            python "$PROJECT_ROOT/tests/production/cleanup.py" summary --db-url="$PRODUCTION_DB_URL" 2>/dev/null || true
        fi
    fi
}

# Register cleanup handler
trap cleanup_on_exit EXIT

# Main execution
main() {
    log_section "SAFE PRODUCTION DATABASE TEST RUNNER"

    local start_time=$(date '+%Y-%m-%d %H:%M:%S')
    local baseline_count=$(get_test_data_count)
    local tests_passed=false

    log_info "Start time: $start_time"
    log_info "Baseline test data count: $baseline_count"
    echo ""

    # Run safety checks (unless skipped)
    if [ "$SKIP_CHECKS" = false ]; then
        if ! run_safety_checks; then
            log_error "Safety checks failed. Aborting."
            log_info "Use --skip-checks to bypass (NOT RECOMMENDED)"
            exit 1
        fi
    else
        log_warning "Safety checks skipped (--skip-checks flag used)"
    fi

    # If dry-run, stop here
    if [ "$DRY_RUN" = true ]; then
        log_section "DRY RUN MODE"
        log_info "Pre-flight checks completed successfully"
        log_info "Actual tests would run here"
        log_success "Dry run completed - ready for actual test execution"
        exit 0
    fi

    # Run tests
    if run_tests; then
        tests_passed=true
    fi

    # Verify cleanup
    verify_cleanup

    # Generate report
    generate_report

    # Exit with appropriate code
    if [ "$tests_passed" = true ]; then
        exit 0
    else
        exit 1
    fi
}

# Run main function
main

#!/bin/bash

# Quick Real Calls Testing Script
# Usage: ./quick-test.sh [local|production] [test-name]

set -e

# Default values
ENVIRONMENT=${1:-local}
TEST_NAME=${2:-}

# Configuration
if [ "$ENVIRONMENT" = "production" ]; then
    BASE_URL="https://bella-alb-1924818779.ca-central-1.elb.amazonaws.com"
    echo "🌐 Testing PRODUCTION environment"
    echo "URL: $BASE_URL"
else
    BASE_URL="http://localhost:8000"
    echo "🏠 Testing LOCAL environment"
    echo "URL: $BASE_URL"
fi

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✓ Virtual environment activated"
else
    echo "❌ Virtual environment not found. Run setup-dev.sh first."
    exit 1
fi

# Check if server is running (for local)
if [ "$ENVIRONMENT" = "local" ]; then
    echo "🔍 Checking if local server is running..."
    if ! curl -s http://localhost:8000/healthz > /dev/null 2>&1; then
        echo "❌ Local server not running. Start with:"
        echo "   uvicorn app.main:app --reload"
        exit 1
    fi
    echo "✓ Local server is running"
fi

echo ""
echo "🧪 Starting Real Calls Tests..."
echo "================================================"

# Run tests based on parameters
if [ -n "$TEST_NAME" ]; then
    echo "Running specific test: $TEST_NAME"
    python real_calls_testing.py --environment "$ENVIRONMENT" --base-url "$BASE_URL" --test-case "$TEST_NAME"
else
    echo "Running all tests..."
    python real_calls_testing.py --environment "$ENVIRONMENT" --base-url "$BASE_URL" --run-all-tests --save-results
fi

echo ""
echo "🎉 Testing complete!"

# Show available commands
echo ""
echo "💡 Other useful commands:"
echo "  ./quick-test.sh local simple_booking     # Test specific case locally"
echo "  ./quick-test.sh production               # Test all cases in production"
echo "  python real_calls_testing.py --list-tests # Show all available tests"
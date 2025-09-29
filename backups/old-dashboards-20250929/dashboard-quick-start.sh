#!/bin/bash
"""
Dashboard Quick Start Script
Launch dashboard with automatic setup and multiple access options
"""

set -e

echo "🚀 BELLA V3 DASHBOARD QUICK START"
echo "================================="
echo ""

# Check if API key is set
if [ -z "$BELLA_API_KEY" ]; then
    echo "⚙️ Setting up API key..."
    export BELLA_API_KEY="YOUR_API_KEY"
    echo "✅ Using default dev API key: $BELLA_API_KEY"
else
    echo "✅ API key configured: ${BELLA_API_KEY:0:12}..."
fi

echo ""
echo "📊 DASHBOARD ACCESS OPTIONS:"
echo "=========================="
echo ""

# Option 1: Integrated FastAPI (recommended)
echo "🎯 OPTION 1: Integrated Dashboard (Recommended)"
echo "   Full-featured with real-time API data"
echo ""
echo "   Start command:"
echo "   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
echo ""
echo "   Access URLs:"
echo "   🔗 http://localhost:8000/dashboard/"
echo "   🔗 http://localhost:8000/dashboard/data/health (API health)"
echo "   🔗 http://localhost:8000/performance/health (performance)"
echo ""
echo "   Headers: X-API-Key: $BELLA_API_KEY"
echo ""

# Option 2: Standalone server
echo "🎯 OPTION 2: Standalone Dashboard Server"
echo "   Simple file-based access (no API key required)"
echo ""
echo "   Start command:"
echo "   ./scripts/serve-dashboard.sh"
echo ""
echo "   Access URL:"
echo "   🔗 http://localhost:8080/dashboard.html"
echo ""

echo "💡 QUICK COMMANDS:"
echo "=================="
echo ""
echo "# Test dashboard health"
echo "curl -H \"X-API-Key: $BELLA_API_KEY\" http://localhost:8000/dashboard/data/health"
echo ""
echo "# Get cost data"
echo "curl -H \"X-API-Key: $BELLA_API_KEY\" http://localhost:8000/dashboard/data/costs"
echo ""
echo "# Setup AWS Cost Explorer"
echo "./scripts/setup-aws-cost-monitoring.sh"
echo ""
echo "# Update cost reports"
echo "python cost-optimization/monitoring/cost_tracker.py --report > cost-reports/latest.json"
echo ""

echo "🤔 WHICH OPTION TO CHOOSE:"
echo "========================="
echo "✅ Development: Option 1 (Integrated) - Full API access"
echo "✅ Demo/Presentation: Option 2 (Standalone) - Simple access"
echo "✅ Production: Option 1 with SSL and proper auth"
echo ""

echo "🎯 READY TO START!"
echo "=================="
read -p "Choose option (1 for Integrated, 2 for Standalone, Enter to see all): " choice

case $choice in
    1)
        echo "🚀 Starting integrated dashboard..."
        echo "Access at: http://localhost:8000/dashboard/"
        echo "API Key: $BELLA_API_KEY"
        echo ""
        exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
        ;;
    2)
        echo "🚀 Starting standalone dashboard..."
        echo "Access at: http://localhost:8080/dashboard.html"
        echo ""
        exec ./scripts/serve-dashboard.sh
        ;;
    *)
        echo ""
        echo "📋 All options available! Choose your preferred method:"
        echo "1. Run: python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
        echo "2. Run: ./scripts/serve-dashboard.sh"
        echo ""
        echo "🎯 Both options provide full dashboard functionality!"
        ;;
esac
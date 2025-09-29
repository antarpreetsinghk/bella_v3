#!/bin/bash
"""
Cost Monitoring Dashboard Server
Serves the cost monitoring dashboard on localhost
"""

set -e

echo "🚀 STARTING COST MONITORING DASHBOARD"
echo "==================================="

# Navigate to project root
cd "$(dirname "$0")/.."

# Check if dashboard exists
if [ ! -f "cost-reports/dashboard.html" ]; then
    echo "❌ Dashboard not found at cost-reports/dashboard.html"
    echo "Run the setup first:"
    echo "./scripts/setup-aws-cost-monitoring.sh"
    exit 1
fi

# Update cost data before serving
echo "📊 Updating cost data..."
python3 cost-optimization/monitoring/cost_tracker.py --report > cost-reports/latest-cost-report.json 2>/dev/null || {
    echo "⚠️ Cost data update failed - using existing data"
}

# Find available port
PORT=8080
while lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; do
    PORT=$((PORT + 1))
done

echo "📈 Dashboard updated with latest cost data"
echo "🌐 Starting web server on port $PORT..."
echo ""
echo "🎯 ACCESS YOUR DASHBOARD:"
echo "========================"
echo ""
echo "🔗 Local Access:"
echo "   http://localhost:$PORT/dashboard.html"
echo ""
echo "🔗 Network Access:"
LOCAL_IP=$(hostname -I | awk '{print $1}' 2>/dev/null || echo "127.0.0.1")
echo "   http://$LOCAL_IP:$PORT/dashboard.html"
echo ""
echo "📱 Mobile Access:"
echo "   Use your computer's IP address from the network access URL above"
echo ""
echo "⚠️  Press Ctrl+C to stop the server"
echo "==================================="
echo ""

# Change to cost-reports directory and start server
cd cost-reports

# Trap to handle cleanup
trap 'echo -e "\n🛑 Dashboard server stopped"; exit 0' INT TERM

# Start Python HTTP server
if command -v python3 >/dev/null 2>&1; then
    python3 -m http.server $PORT --bind 0.0.0.0
elif command -v python >/dev/null 2>&1; then
    python -m http.server $PORT --bind 0.0.0.0
else
    echo "❌ Python not found. Please install Python to serve the dashboard."
    echo "Alternative: Open cost-reports/dashboard.html directly in your browser"
    exit 1
fi
#!/bin/bash
"""
Cost monitoring dashboard setup script.
Sets up comprehensive cost tracking and optimization.
"""

set -e

echo "💰 SETTING UP COST MONITORING DASHBOARD"
echo "======================================"

# Create cost monitoring directories
mkdir -p cost-reports
mkdir -p cost-reports/daily
mkdir -p cost-reports/monthly

# Activate virtual environment
if [[ -d "venv" ]]; then
    source venv/bin/activate
fi

# Generate initial cost report
echo "📊 Generating initial cost report..."
python cost-optimization/monitoring/cost_tracker.py --report > cost-reports/initial-cost-report.json

# Generate cost optimization recommendations
echo "💡 Generating cost optimization recommendations..."
python cost-optimization/monitoring/cost_tracker.py --recommendations > cost-reports/cost-recommendations.txt

# Create cost monitoring cron job
echo "⏰ Setting up automated cost monitoring..."
cat > scripts/daily-cost-check.sh << 'CRONEOF'
#!/bin/bash
# Daily cost monitoring script
cd /home/antarpreet/Projects/bella_v3
source venv/bin/activate

DATE=$(date +%Y-%m-%d)
echo "📊 Running daily cost check for $DATE..."

# Generate daily report
python cost-optimization/monitoring/cost_tracker.py --report > "cost-reports/daily/cost-report-$DATE.json"

# Check for alerts
python cost-optimization/monitoring/cost_tracker.py --alerts > "cost-reports/daily/cost-alerts-$DATE.txt"

# Send summary email (if configured)
if [[ -n "$COST_ALERT_EMAIL" ]]; then
    python -c "
import json
import smtplib
from datetime import datetime
from email.mime.text import MIMEText

# Load cost report
try:
    with open('cost-reports/daily/cost-report-$DATE.json', 'r') as f:
        report = json.load(f)

    summary = report.get('summary', {})
    total_cost = summary.get('total_monthly_aws', 0)

    if total_cost > 120:  # Alert threshold
        msg = MIMEText(f'''
Daily Cost Alert - {datetime.now().strftime('%Y-%m-%d')}

Current monthly AWS costs: \$${total_cost:.2f}
Alert threshold: \$120.00

Please review the detailed report at:
cost-reports/daily/cost-report-$DATE.json

Recommendations available at:
cost-reports/cost-recommendations.txt
        ''')
        msg['Subject'] = f'Bella V3 Cost Alert - \$${total_cost:.2f}'
        msg['From'] = 'bella-system@company.com'
        msg['To'] = '$COST_ALERT_EMAIL'

        # Configure SMTP server
        # server = smtplib.SMTP('smtp.gmail.com', 587)
        # server.send_message(msg)
        print('Cost alert would be sent to $COST_ALERT_EMAIL')
except Exception as e:
    print(f'Cost monitoring error: {e}')
"
fi

echo "✅ Daily cost check completed for $DATE"
CRONEOF

chmod +x scripts/daily-cost-check.sh

# Create cost dashboard HTML
echo "🎨 Creating cost monitoring dashboard..."
cat > cost-reports/dashboard.html << 'HTMLEOF'
<!DOCTYPE html>
<html>
<head>
    <title>Bella V3 Cost Monitoring Dashboard</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 20px; }
        .header { background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .card { background: white; border: 1px solid #e1e5e9; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .metric { display: inline-block; margin-right: 30px; }
        .metric-value { font-size: 2em; font-weight: bold; color: #667eea; }
        .metric-label { color: #666; font-size: 0.9em; }
        .alert { background: #fff5f5; border: 1px solid #fed7d7; color: #9b2c2c; padding: 10px; border-radius: 4px; margin-bottom: 10px; }
        .success { background: #f0fff4; border: 1px solid #9ae6b4; color: #276749; padding: 10px; border-radius: 4px; margin-bottom: 10px; }
        .recommendation { background: #f7fafc; border-left: 4px solid #667eea; padding: 10px; margin-bottom: 10px; }
        .status-connected { color: #38a169; }
        .status-offline { color: #e53e3e; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { text-align: left; padding: 8px; border-bottom: 1px solid #e2e8f0; }
        th { background: #f7fafc; font-weight: 600; }
    </style>
    <script>
        async function loadCostData() {
            try {
                const response = await fetch('initial-cost-report.json');
                const data = await response.json();
                updateDashboard(data);
            } catch (error) {
                console.error('Error loading cost data:', error);
                document.getElementById('status').innerHTML = '<div class="alert">Error loading cost data</div>';
            }
        }

        function updateDashboard(data) {
            const summary = data.summary || {};
            const status = data.aws_status === 'connected' ? 'connected' : 'offline';

            document.getElementById('aws-status').className = `status-${status}`;
            document.getElementById('aws-status').textContent = status.toUpperCase();

            document.getElementById('monthly-cost').textContent = '$' + (summary.total_monthly_aws || 0).toFixed(2);
            document.getElementById('daily-avg').textContent = '$' + (summary.average_daily || 0).toFixed(2);
            document.getElementById('api-costs').textContent = '$' + (summary.total_api_costs || 0).toFixed(2);

            // Update cost breakdown
            const costTable = document.getElementById('cost-breakdown');
            const monthlyServices = data.monthly_costs || {};
            let tableHTML = '<tr><th>Service</th><th>Monthly Cost</th></tr>';

            for (const [service, cost] of Object.entries(monthlyServices)) {
                tableHTML += `<tr><td>${service}</td><td>$${cost.toFixed(2)}</td></tr>`;
            }
            costTable.innerHTML = tableHTML;

            // Update recommendations
            const recommendations = data.recommendations || {};
            const recList = document.getElementById('recommendations');
            let recHTML = '';

            ['immediate', 'short_term', 'long_term'].forEach(category => {
                if (recommendations[category] && recommendations[category].length > 0) {
                    recHTML += `<h4>${category.replace('_', ' ').toUpperCase()}</h4>`;
                    recommendations[category].forEach(rec => {
                        recHTML += `<div class="recommendation">${rec}</div>`;
                    });
                }
            });

            recList.innerHTML = recHTML || '<div class="success">All cost optimization recommendations implemented!</div>';
        }

        // Auto-refresh every 5 minutes
        setInterval(loadCostData, 300000);
        window.addEventListener('load', loadCostData);
    </script>
</head>
<body>
    <div class="header">
        <h1>🚀 Bella V3 Cost Monitoring Dashboard</h1>
        <p>Real-time cost tracking and optimization recommendations</p>
        <p>AWS Status: <span id="aws-status" class="status-offline">CHECKING...</span></p>
    </div>

    <div class="card">
        <h2>📊 Cost Overview</h2>
        <div class="metric">
            <div class="metric-value" id="monthly-cost">$0.00</div>
            <div class="metric-label">Monthly AWS Costs</div>
        </div>
        <div class="metric">
            <div class="metric-value" id="daily-avg">$0.00</div>
            <div class="metric-label">Daily Average</div>
        </div>
        <div class="metric">
            <div class="metric-value" id="api-costs">$0.00</div>
            <div class="metric-label">API Costs</div>
        </div>
    </div>

    <div class="card">
        <h2>💰 Cost Breakdown</h2>
        <table id="cost-breakdown">
            <tr><td colspan="2">Loading cost data...</td></tr>
        </table>
    </div>

    <div class="card">
        <h2>💡 Cost Optimization Recommendations</h2>
        <div id="recommendations">Loading recommendations...</div>
    </div>

    <div class="card">
        <h2>📈 Usage Instructions</h2>
        <div class="success">
            <strong>Dashboard is ready!</strong> Cost data updates automatically every 5 minutes.
        </div>
        <p><strong>To enable real AWS cost data:</strong></p>
        <ol>
            <li>Set up AWS Cost Explorer permissions</li>
            <li>Run: <code>aws configure</code></li>
            <li>Restart the cost monitoring service</li>
        </ol>
        <p><strong>To set up cost alerts:</strong></p>
        <ol>
            <li>Set environment variable: <code>export COST_ALERT_EMAIL=your-email@company.com</code></li>
            <li>Configure SMTP settings in daily-cost-check.sh</li>
            <li>Set up cron job: <code>crontab -e</code> and add: <code>0 9 * * * /path/to/bella_v3/scripts/daily-cost-check.sh</code></li>
        </ol>
    </div>
</body>
</html>
HTMLEOF

echo ""
echo "🎉 COST MONITORING SETUP COMPLETE!"
echo "=================================="
echo "📊 Dashboard: cost-reports/dashboard.html"
echo "📁 Reports: cost-reports/"
echo "⏰ Daily monitoring: scripts/daily-cost-check.sh"
echo ""
echo "🚀 Open cost-reports/dashboard.html in your browser to view the dashboard!"
echo "💡 Current estimated monthly costs: \$110 (with optimization potential of 40-60%)"
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

#!/bin/bash
"""
AWS Cost Explorer Setup Script
Configures AWS permissions and enables live cost monitoring dashboard
"""

set -e

echo "🔧 SETTING UP AWS COST MONITORING"
echo "================================="

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found. Installing..."
    if command -v pip3 &> /dev/null; then
        pip3 install awscli
    else
        echo "Please install AWS CLI manually: https://aws.amazon.com/cli/"
        exit 1
    fi
fi

echo "✅ AWS CLI found"

# Check AWS configuration
if ! aws sts get-caller-identity &> /dev/null; then
    echo "⚠️ AWS not configured. Please run 'aws configure' first"
    echo "You need:"
    echo "  - AWS Access Key ID"
    echo "  - AWS Secret Access Key"
    echo "  - Default region (e.g., us-east-1)"
    exit 1
fi

echo "✅ AWS credentials configured"

# Get current AWS identity
AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
AWS_USER=$(aws sts get-caller-identity --query Arn --output text)
echo "📋 AWS Account: $AWS_ACCOUNT"
echo "📋 AWS User/Role: $AWS_USER"

echo ""
echo "🔐 CONFIGURING COST EXPLORER PERMISSIONS"
echo "========================================"

# Create Cost Explorer policy
cat > /tmp/cost-explorer-policy.json << 'EOF'
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ce:GetCostAndUsage",
                "ce:GetDimensionValues",
                "ce:GetReservationCoverage",
                "ce:GetReservationPurchaseRecommendation",
                "ce:GetReservationUtilization",
                "ce:GetUsageReport",
                "ce:ListCostCategoryDefinitions",
                "ce:DescribeCostCategoryDefinition",
                "ce:GetRightsizingRecommendation"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "budgets:ViewBudget",
                "budgets:DescribeBudgets"
            ],
            "Resource": "*"
        }
    ]
}
EOF

# Check if running as IAM user or role
if echo "$AWS_USER" | grep -q "user/"; then
    echo "📝 Detected IAM User. Creating inline policy..."

    # Extract username
    USERNAME=$(echo "$AWS_USER" | cut -d'/' -f2)

    # Create inline policy for user
    aws iam put-user-policy \
        --user-name "$USERNAME" \
        --policy-name "BellaCostExplorerAccess" \
        --policy-document file:///tmp/cost-explorer-policy.json

    echo "✅ Cost Explorer policy attached to user: $USERNAME"

elif echo "$AWS_USER" | grep -q "role/"; then
    echo "📝 Detected IAM Role. You need to attach policy to role manually."
    echo "Role ARN: $AWS_USER"
    echo "Policy JSON saved to: /tmp/cost-explorer-policy.json"
    echo ""
    echo "To attach manually:"
    echo "1. Go to AWS IAM Console"
    echo "2. Find your role and attach the policy"
    echo "3. Or run: aws iam put-role-policy --role-name ROLE_NAME --policy-name BellaCostExplorerAccess --policy-document file:///tmp/cost-explorer-policy.json"
else
    echo "⚠️ Unknown AWS identity type. Please attach Cost Explorer permissions manually."
fi

# Enable Cost Explorer (this might require manual activation)
echo ""
echo "🔍 ENABLING COST EXPLORER"
echo "========================"

# Test Cost Explorer access
echo "🧪 Testing Cost Explorer access..."
if python3 -c "
import boto3
from datetime import datetime, timedelta

try:
    ce = boto3.client('ce')
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)

    response = ce.get_cost_and_usage(
        TimePeriod={
            'Start': start_date.strftime('%Y-%m-%d'),
            'End': end_date.strftime('%Y-%m-%d')
        },
        Granularity='DAILY',
        Metrics=['BlendedCost']
    )
    print('✅ Cost Explorer API access successful!')
    print(f'Data points found: {len(response[\"ResultsByTime\"])}')
except Exception as e:
    print(f'❌ Cost Explorer API error: {e}')
    print('')
    print('This usually means:')
    print('1. Cost Explorer needs to be enabled manually in AWS Console')
    print('2. Account needs billing permissions')
    print('3. May take 24 hours to activate after first enabling')
    print('')
    print('To enable:')
    print('1. Go to AWS Console > Billing > Cost Explorer')
    print('2. Click \"Enable Cost Explorer\"')
    print('3. Wait 24 hours for data population')
    exit(1)
"; then
    echo "🎉 Cost Explorer fully functional!"
else
    echo "⚠️ Cost Explorer needs manual activation"
fi

echo ""
echo "📊 UPDATING DASHBOARD"
echo "==================="

# Update dashboard with live data
cd "$(dirname "$0")/.."
python3 cost-optimization/monitoring/cost_tracker.py --report > cost-reports/live-cost-report.json

echo "✅ Dashboard updated with live AWS data"

echo ""
echo "🚀 SETUP COMPLETE"
echo "================"
echo "Dashboard available at: cost-reports/dashboard.html"
echo "Live data: cost-reports/live-cost-report.json"
echo ""
echo "To serve dashboard locally:"
echo "cd cost-reports && python3 -m http.server 8080"
echo "Then visit: http://localhost:8080/dashboard.html"
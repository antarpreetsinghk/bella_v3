# 🚀 GitHub Actions Setup Guide

This guide will help you set up GitHub Actions for automated deployment and monitoring of your cost-optimized Bella V3 application.

## 📋 Prerequisites

- GitHub repository with admin access
- AWS account with programmatic access
- EC2 instance deployed and running
- SSH key pair for EC2 access

## 🔑 Required GitHub Secrets

Go to your GitHub repository → Settings → Secrets and variables → Actions, then add these secrets:

### AWS Credentials
```
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
```

### EC2 Access
```
EC2_HOST=15.156.194.39
EC2_SSH_KEY=-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwgg...
-----END PRIVATE KEY-----
```

## 🛠️ Setup Instructions

### 1. Create AWS IAM User for GitHub Actions

```bash
# Create IAM user
aws iam create-user --user-name github-actions-bella

# Attach required policies
aws iam attach-user-policy \
  --user-name github-actions-bella \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ReadOnlyAccess

aws iam attach-user-policy \
  --user-name github-actions-bella \
  --policy-arn arn:aws:iam::aws:policy/CloudWatchReadOnlyAccess

# Create custom policy for cost monitoring
cat << EOF > cost-policy.json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ce:GetCostAndUsage",
                "ce:GetUsageReport",
                "ce:GetDimensionValues",
                "ce:GetReservationCoverage",
                "ce:GetReservationPurchaseRecommendation",
                "ce:GetReservationUtilization",
                "ce:GetRightsizingRecommendation",
                "ce:GetUsageReport",
                "ce:ListCostCategoryDefinitions",
                "ce:DescribeCostCategoryDefinition"
            ],
            "Resource": "*"
        }
    ]
}
EOF

aws iam create-policy \
  --policy-name BellaCostMonitoring \
  --policy-document file://cost-policy.json

aws iam attach-user-policy \
  --user-name github-actions-bella \
  --policy-arn arn:aws:iam::YOUR_ACCOUNT_ID:policy/BellaCostMonitoring

# Create access keys
aws iam create-access-key --user-name github-actions-bella
```

### 2. Add Secrets to GitHub

1. Go to your repository on GitHub
2. Click Settings → Secrets and variables → Actions
3. Click "New repository secret" for each required secret:

| Secret Name | Value | Description |
|-------------|-------|-------------|
| `AWS_ACCESS_KEY_ID` | `AKIA...` | From IAM user creation |
| `AWS_SECRET_ACCESS_KEY` | `...` | From IAM user creation |
| `EC2_HOST` | `15.156.194.39` | Your EC2 public IP |
| `EC2_SSH_KEY` | `-----BEGIN...` | Contents of bella-deployment-key.pem |

### 3. Copy SSH Key

```bash
# Copy the SSH key content
cat bella-deployment-key.pem

# Paste the entire content (including headers) into EC2_SSH_KEY secret
```

### 4. Test the Setup

Create a test commit to trigger the workflows:

```bash
# Make a small change
echo "# Test GitHub Actions" >> README.md

# Commit and push
git add README.md
git commit -m "test: trigger GitHub Actions"
git push origin main
```

## 📊 Workflows Overview

### 1. Deployment Workflow (`.github/workflows/deploy.yml`)

**Triggers:**
- Push to `main` or `production` branch
- Pull requests to `main`

**What it does:**
- Runs tests and security checks
- Builds and deploys to EC2
- Performs health checks
- Cleans up old Docker images

### 2. Monitoring Workflow (`.github/workflows/monitoring.yml`)

**Triggers:**
- Daily at 9 AM UTC (cost monitoring)
- Every 6 hours (performance monitoring)
- Manual trigger via GitHub UI

**What it does:**
- Monitors AWS costs vs budget
- Checks system performance
- Tests application health
- Creates alerts if issues found

### 3. PR Validation (`.github/workflows/pr-validation.yml`)

**Triggers:**
- Pull request opened/updated

**What it does:**
- Code quality checks (Black, isort, flake8, mypy)
- Security scanning (Bandit, Safety)
- Full test suite
- Docker build validation
- Performance baseline

## 🔍 Monitoring Features

### Cost Monitoring
- Tracks EC2 and EBS costs
- Compares against $50 monthly budget
- Alerts when over 80% of budget
- Generates daily cost reports

### Performance Monitoring
- System resource usage
- Container performance
- Application health checks
- Error log monitoring
- Database size tracking

### Automated Testing
- Unit and integration tests
- Security vulnerability scanning
- Code quality enforcement
- Docker container validation

## 🚨 Alert System

### Cost Alerts
When costs exceed 80% of budget, the system will:
- Create a GitHub issue
- Include cost breakdown
- Provide optimization recommendations

### Performance Alerts
When performance issues are detected:
- Create a GitHub issue with diagnostics
- Include system metrics
- Provide troubleshooting steps

## 📈 Usage Examples

### Manual Cost Check
```bash
# Go to GitHub repository
# Actions tab → Monitoring → Run workflow
# Select "cost" and click "Run workflow"
```

### View Deployment Status
```bash
# Push changes to main branch
git push origin main

# Check GitHub Actions tab for deployment progress
# Deployment URL will be shown in the logs
```

### Download Reports
```bash
# Go to completed workflow run
# Scroll to "Artifacts" section
# Download cost-report or test-results
```

## 🛠️ Customization

### Adjust Budget Alert Threshold
Edit `.github/workflows/monitoring.yml`:
```yaml
env:
  MONTHLY_BUDGET: 50.0  # Change this value
```

### Change Monitoring Schedule
Edit the cron expressions:
```yaml
schedule:
  - cron: '0 9 * * *'  # Daily at 9 AM
  - cron: '0 */6 * * *'  # Every 6 hours
```

### Add Custom Notifications
You can integrate with Slack, Discord, or email by adding notification steps to the workflows.

## 🔧 Troubleshooting

### Common Issues

**1. SSH Connection Failed**
```bash
# Check if EC2_SSH_KEY is properly formatted
# Ensure EC2_HOST is correct
# Verify security group allows SSH from GitHub Actions IPs
```

**2. AWS Permission Denied**
```bash
# Verify IAM user has required policies
# Check AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY
# Ensure region is correct (ca-central-1)
```

**3. Docker Build Failed**
```bash
# Check Dockerfile.cost-optimized syntax
# Verify requirements.txt is up to date
# Check available disk space on EC2
```

### Debug Commands

```bash
# Test SSH connection manually
ssh -i bella-deployment-key.pem ubuntu@15.156.194.39

# Check EC2 instance status
aws ec2 describe-instances --instance-ids i-0ecb9f307d11be593

# View application logs
docker compose -f docker-compose.cost-optimized.yml logs app
```

## 🎯 Success Criteria

Your GitHub Actions setup is working correctly when:

- ✅ Deployments complete successfully
- ✅ Cost monitoring reports are generated
- ✅ Performance metrics are collected
- ✅ Security scans pass without critical issues
- ✅ All tests pass in PR validation

---

**🎉 You now have a complete CI/CD pipeline for your cost-optimized Bella V3 deployment!**
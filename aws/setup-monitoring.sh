#!/bin/bash
set -euo pipefail

echo "🔍 Setting up Bella V3 Monitoring & Alerting..."

# Configuration
CLUSTER_NAME="bella-prod-cluster"
SERVICE_NAME="bella-prod-service"
ALB_ARN="arn:aws:elasticloadbalancing:ca-central-1:REPLACE_WITH_YOUR_AWS_ACCOUNT_ID:loadbalancer/app/your-alb/your-alb-id"
TG_ARN="arn:aws:elasticloadbalancing:ca-central-1:REPLACE_WITH_YOUR_AWS_ACCOUNT_ID:targetgroup/your-tg/your-tg-id"
LOG_GROUP="/ecs/bella-prod"

# Create SNS topic for alerts
echo "📧 Creating SNS topic for alerts..."
SNS_TOPIC_ARN=$(aws sns create-topic --name bella-alerts --query 'TopicArn' --output text)
echo "SNS Topic ARN: $SNS_TOPIC_ARN"

# Subscribe to email (replace with your email)
read -p "Enter email for alerts: " EMAIL
aws sns subscribe --topic-arn "$SNS_TOPIC_ARN" --protocol email --notification-endpoint "$EMAIL"
echo "✅ Email subscription created (check your email to confirm)"

# ECS Service CPU Alarm
echo "🚨 Creating ECS CPU alarm..."
aws cloudwatch put-metric-alarm \
  --alarm-name "bella-high-cpu" \
  --alarm-description "Bella ECS CPU utilization > 80%" \
  --alarm-actions "$SNS_TOPIC_ARN" \
  --metric-name CPUUtilization \
  --namespace AWS/ECS \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=ServiceName,Value="$SERVICE_NAME" Name=ClusterName,Value="$CLUSTER_NAME" \
  --evaluation-periods 2 \
  --treat-missing-data notBreaching

# ECS Service Memory Alarm
echo "🧠 Creating ECS Memory alarm..."
aws cloudwatch put-metric-alarm \
  --alarm-name "bella-high-memory" \
  --alarm-description "Bella ECS Memory utilization > 85%" \
  --alarm-actions "$SNS_TOPIC_ARN" \
  --metric-name MemoryUtilization \
  --namespace AWS/ECS \
  --statistic Average \
  --period 300 \
  --threshold 85 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=ServiceName,Value="$SERVICE_NAME" Name=ClusterName,Value="$CLUSTER_NAME" \
  --evaluation-periods 2 \
  --treat-missing-data notBreaching

# ALB Target Health Alarm
echo "🎯 Creating ALB health alarm..."
aws cloudwatch put-metric-alarm \
  --alarm-name "bella-unhealthy-targets" \
  --alarm-description "Bella ALB has unhealthy targets" \
  --alarm-actions "$SNS_TOPIC_ARN" \
  --metric-name UnHealthyHostCount \
  --namespace AWS/ApplicationELB \
  --statistic Average \
  --period 60 \
  --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --dimensions Name=TargetGroup,Value="${TG_ARN##*/}" Name=LoadBalancer,Value="${ALB_ARN##*/}" \
  --evaluation-periods 2 \
  --treat-missing-data notBreaching

# ALB Response Time Alarm
echo "⏱️ Creating ALB response time alarm..."
aws cloudwatch put-metric-alarm \
  --alarm-name "bella-slow-response" \
  --alarm-description "Bella ALB response time > 5 seconds" \
  --alarm-actions "$SNS_TOPIC_ARN" \
  --metric-name TargetResponseTime \
  --namespace AWS/ApplicationELB \
  --statistic Average \
  --period 300 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=LoadBalancer,Value="${ALB_ARN##*/}" \
  --evaluation-periods 2 \
  --treat-missing-data notBreaching

# Error Rate Alarm (5xx responses)
echo "❌ Creating 5xx error alarm..."
aws cloudwatch put-metric-alarm \
  --alarm-name "bella-5xx-errors" \
  --alarm-description "Bella 5xx error rate > 5%" \
  --alarm-actions "$SNS_TOPIC_ARN" \
  --metric-name HTTPCode_Target_5XX_Count \
  --namespace AWS/ApplicationELB \
  --statistic Sum \
  --period 300 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=LoadBalancer,Value="${ALB_ARN##*/}" \
  --evaluation-periods 1 \
  --treat-missing-data notBreaching

# CloudWatch Logs Error Filter
echo "📝 Creating CloudWatch Logs error metric..."
aws logs put-metric-filter \
  --log-group-name "$LOG_GROUP" \
  --filter-name "bella-error-filter" \
  --filter-pattern "[timestamp, level=\"ERROR\", ...]" \
  --metric-transformations \
    metricName=BellaErrorCount,metricNamespace=Bella/Application,metricValue=1,defaultValue=0

# Error Count Alarm
echo "🔥 Creating error count alarm..."
aws cloudwatch put-metric-alarm \
  --alarm-name "bella-error-spike" \
  --alarm-description "Bella error count > 10 in 5 minutes" \
  --alarm-actions "$SNS_TOPIC_ARN" \
  --metric-name BellaErrorCount \
  --namespace Bella/Application \
  --statistic Sum \
  --period 300 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --treat-missing-data notBreaching

echo "✅ Monitoring setup complete!"
echo ""
echo "📊 CloudWatch Alarms created:"
echo "  - bella-high-cpu (>80%)"
echo "  - bella-high-memory (>85%)"
echo "  - bella-unhealthy-targets (≥1)"
echo "  - bella-slow-response (>5s)"
echo "  - bella-5xx-errors (>5 per 5min)"
echo "  - bella-error-spike (>10 errors per 5min)"
echo ""
echo "📧 SNS Topic: $SNS_TOPIC_ARN"
echo "📝 Log Group: $LOG_GROUP"
echo ""
echo "🔍 Monitor with:"
echo "  aws cloudwatch describe-alarms --alarm-names bella-high-cpu bella-high-memory"
echo "  aws logs tail $LOG_GROUP --follow"
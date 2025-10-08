#!/bin/bash
"""
CloudWatch Monitoring Setup Script
Sets up monitoring dashboard and alerts for production Bella Voice App
"""

set -e

# Configuration
FUNCTION_NAME="bella-voice-app"
REGION="us-east-1"
DASHBOARD_NAME="BellaVoiceAppProduction"
SNS_TOPIC_NAME="bella-voice-app-alerts"

echo "🔍 Setting up CloudWatch monitoring for Bella Voice App"
echo "=================================================="

# Create SNS topic for alerts
echo "📢 Creating SNS topic for alerts..."
SNS_TOPIC_ARN=$(aws sns create-topic --name $SNS_TOPIC_NAME --region $REGION --query 'TopicArn' --output text)
echo "SNS Topic ARN: $SNS_TOPIC_ARN"

# Create CloudWatch dashboard
echo "📊 Creating CloudWatch dashboard..."
aws cloudwatch put-dashboard \
    --dashboard-name $DASHBOARD_NAME \
    --dashboard-body file://monitoring/cloudwatch-dashboard.json \
    --region $REGION

# Create alarms
echo "🚨 Creating CloudWatch alarms..."

# Lambda error rate alarm
aws cloudwatch put-metric-alarm \
    --alarm-name "bella-voice-app-high-error-rate" \
    --alarm-description "Alert when Lambda error rate exceeds 5%" \
    --metric-name "Errors" \
    --namespace "AWS/Lambda" \
    --statistic "Sum" \
    --period 300 \
    --threshold 5 \
    --comparison-operator "GreaterThanThreshold" \
    --evaluation-periods 2 \
    --alarm-actions $SNS_TOPIC_ARN \
    --dimensions Name=FunctionName,Value=$FUNCTION_NAME \
    --region $REGION

# Lambda duration alarm
aws cloudwatch put-metric-alarm \
    --alarm-name "bella-voice-app-high-duration" \
    --alarm-description "Alert when Lambda duration exceeds 10 seconds" \
    --metric-name "Duration" \
    --namespace "AWS/Lambda" \
    --statistic "Average" \
    --period 300 \
    --threshold 10000 \
    --comparison-operator "GreaterThanThreshold" \
    --evaluation-periods 2 \
    --alarm-actions $SNS_TOPIC_ARN \
    --dimensions Name=FunctionName,Value=$FUNCTION_NAME \
    --region $REGION

# Lambda throttling alarm
aws cloudwatch put-metric-alarm \
    --alarm-name "bella-voice-app-throttling" \
    --alarm-description "Alert when Lambda function is throttled" \
    --metric-name "Throttles" \
    --namespace "AWS/Lambda" \
    --statistic "Sum" \
    --period 300 \
    --threshold 1 \
    --comparison-operator "GreaterThanOrEqualToThreshold" \
    --evaluation-periods 1 \
    --alarm-actions $SNS_TOPIC_ARN \
    --dimensions Name=FunctionName,Value=$FUNCTION_NAME \
    --region $REGION

# DynamoDB throttling alarm
aws cloudwatch put-metric-alarm \
    --alarm-name "bella-voice-app-dynamodb-throttling" \
    --alarm-description "Alert when DynamoDB requests are throttled" \
    --metric-name "ThrottledRequests" \
    --namespace "AWS/DynamoDB" \
    --statistic "Sum" \
    --period 300 \
    --threshold 1 \
    --comparison-operator "GreaterThanOrEqualToThreshold" \
    --evaluation-periods 1 \
    --alarm-actions $SNS_TOPIC_ARN \
    --dimensions Name=TableName,Value=bella-voice-app-sessions \
    --region $REGION

# Low call volume alarm (indicates potential issues)
aws cloudwatch put-metric-alarm \
    --alarm-name "bella-voice-app-low-call-volume" \
    --alarm-description "Alert when no calls received for 2 hours during business hours" \
    --metric-name "Invocations" \
    --namespace "AWS/Lambda" \
    --statistic "Sum" \
    --period 7200 \
    --threshold 1 \
    --comparison-operator "LessThanThreshold" \
    --evaluation-periods 1 \
    --alarm-actions $SNS_TOPIC_ARN \
    --dimensions Name=FunctionName,Value=$FUNCTION_NAME \
    --region $REGION

echo "✅ Monitoring setup complete!"
echo ""
echo "Dashboard URL: https://console.aws.amazon.com/cloudwatch/home?region=$REGION#dashboards:name=$DASHBOARD_NAME"
echo "SNS Topic ARN: $SNS_TOPIC_ARN"
echo ""
echo "To subscribe to alerts via email:"
echo "aws sns subscribe --topic-arn $SNS_TOPIC_ARN --protocol email --notification-endpoint your-email@example.com"
echo ""
echo "Alarms created:"
echo "- High error rate (>5%)"
echo "- High duration (>10s)"
echo "- Lambda throttling"
echo "- DynamoDB throttling"
echo "- Low call volume (no calls for 2h)"
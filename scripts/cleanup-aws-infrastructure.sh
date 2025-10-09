#!/bin/bash
set -e

echo "🧹 AWS Infrastructure Cleanup Script"
echo "===================================="
echo "⚠️  WARNING: This will DELETE AWS resources and cannot be undone!"
echo ""

# Configuration
REGION="ca-central-1"
LAMBDA_FUNCTION_NAME="bella-voice-app"

read -p "Are you sure you want to delete ALL AWS infrastructure? (type 'DELETE' to confirm): " confirm
if [ "$confirm" != "DELETE" ]; then
    echo "Cleanup cancelled."
    exit 0
fi

echo ""
echo "🗑️ Starting infrastructure cleanup..."

# 1. Delete Lambda Function
echo "1️⃣ Deleting Lambda function..."
if aws lambda get-function --function-name $LAMBDA_FUNCTION_NAME --region $REGION >/dev/null 2>&1; then
    # Delete function URL config first
    echo "   Deleting function URL configuration..."
    aws lambda delete-function-url-config --function-name $LAMBDA_FUNCTION_NAME --region $REGION 2>/dev/null || true

    # Delete function
    echo "   Deleting Lambda function..."
    aws lambda delete-function --function-name $LAMBDA_FUNCTION_NAME --region $REGION
    echo "   ✅ Lambda function deleted"
else
    echo "   ⏭️ Lambda function not found, skipping"
fi

# 2. Delete RDS Instance
echo "2️⃣ Deleting RDS instances..."
RDS_INSTANCES=$(aws rds describe-db-instances --region $REGION --query 'DBInstances[?contains(DBInstanceIdentifier, `bella`)].DBInstanceIdentifier' --output text 2>/dev/null || echo "")
if [ -n "$RDS_INSTANCES" ]; then
    for instance in $RDS_INSTANCES; do
        echo "   Deleting RDS instance: $instance"
        aws rds delete-db-instance \
            --db-instance-identifier $instance \
            --skip-final-snapshot \
            --delete-automated-backups \
            --region $REGION
        echo "   ✅ RDS instance $instance deletion initiated"
    done
else
    echo "   ⏭️ No Bella RDS instances found, skipping"
fi

# 3. Delete ElastiCache Redis
echo "3️⃣ Deleting ElastiCache Redis clusters..."
REDIS_CLUSTERS=$(aws elasticache describe-cache-clusters --region $REGION --query 'CacheClusters[?contains(CacheClusterId, `bella`)].CacheClusterId' --output text 2>/dev/null || echo "")
if [ -n "$REDIS_CLUSTERS" ]; then
    for cluster in $REDIS_CLUSTERS; do
        echo "   Deleting Redis cluster: $cluster"
        aws elasticache delete-cache-cluster \
            --cache-cluster-id $cluster \
            --region $REGION
        echo "   ✅ Redis cluster $cluster deletion initiated"
    done
else
    echo "   ⏭️ No Bella Redis clusters found, skipping"
fi

# 4. Delete Application Load Balancer
echo "4️⃣ Deleting Application Load Balancers..."
ALB_ARNS=$(aws elbv2 describe-load-balancers --region $REGION --query 'LoadBalancers[?contains(LoadBalancerName, `bella`)].LoadBalancerArn' --output text 2>/dev/null || echo "")
if [ -n "$ALB_ARNS" ]; then
    for alb_arn in $ALB_ARNS; do
        echo "   Deleting ALB: $alb_arn"
        aws elbv2 delete-load-balancer --load-balancer-arn $alb_arn --region $REGION
        echo "   ✅ ALB deletion initiated"
    done
else
    echo "   ⏭️ No Bella ALBs found, skipping"
fi

# 5. Delete Target Groups
echo "5️⃣ Deleting Target Groups..."
TG_ARNS=$(aws elbv2 describe-target-groups --region $REGION --query 'TargetGroups[?contains(TargetGroupName, `bella`)].TargetGroupArn' --output text 2>/dev/null || echo "")
if [ -n "$TG_ARNS" ]; then
    for tg_arn in $TG_ARNS; do
        echo "   Deleting Target Group: $tg_arn"
        aws elbv2 delete-target-group --target-group-arn $tg_arn --region $REGION
        echo "   ✅ Target Group deleted"
    done
else
    echo "   ⏭️ No Bella Target Groups found, skipping"
fi

# 6. Delete ECR Repository (optional - ask user)
echo "6️⃣ ECR Repository cleanup..."
read -p "Delete ECR repository 'bella-voice-app'? This will remove all Docker images. (y/N): " delete_ecr
if [ "$delete_ecr" = "y" ] || [ "$delete_ecr" = "Y" ]; then
    if aws ecr describe-repositories --repository-names bella-voice-app --region $REGION >/dev/null 2>&1; then
        echo "   Deleting ECR repository..."
        aws ecr delete-repository --repository-name bella-voice-app --force --region $REGION
        echo "   ✅ ECR repository deleted"
    else
        echo "   ⏭️ ECR repository not found, skipping"
    fi
else
    echo "   ⏭️ ECR repository preserved"
fi

# 7. Delete VPC and associated resources (if using default VPC, skip this)
echo "7️⃣ VPC cleanup..."
read -p "Delete VPC resources created for Bella? This includes subnets, security groups, etc. (y/N): " delete_vpc
if [ "$delete_vpc" = "y" ] || [ "$delete_vpc" = "Y" ]; then
    # Find VPCs with Bella tags
    VPC_IDS=$(aws ec2 describe-vpcs --region $REGION --filters "Name=tag:Project,Values=bella-voice-app" --query 'Vpcs[].VpcId' --output text 2>/dev/null || echo "")

    if [ -n "$VPC_IDS" ]; then
        for vpc_id in $VPC_IDS; do
            echo "   Cleaning up VPC: $vpc_id"

            # Delete associated resources first
            echo "     Deleting security groups..."
            aws ec2 describe-security-groups --filters "Name=vpc-id,Values=$vpc_id" --region $REGION --query 'SecurityGroups[?GroupName!=`default`].GroupId' --output text | xargs -r -n1 aws ec2 delete-security-group --group-id --region $REGION 2>/dev/null || true

            echo "     Deleting subnets..."
            aws ec2 describe-subnets --filters "Name=vpc-id,Values=$vpc_id" --region $REGION --query 'Subnets[].SubnetId' --output text | xargs -r -n1 aws ec2 delete-subnet --subnet-id --region $REGION 2>/dev/null || true

            echo "     Deleting route tables..."
            aws ec2 describe-route-tables --filters "Name=vpc-id,Values=$vpc_id" --region $REGION --query 'RouteTables[?length(Associations[?Main!=`true`]) > `0`].RouteTableId' --output text | xargs -r -n1 aws ec2 delete-route-table --route-table-id --region $REGION 2>/dev/null || true

            echo "     Deleting internet gateway..."
            IGW_ID=$(aws ec2 describe-internet-gateways --filters "Name=attachment.vpc-id,Values=$vpc_id" --region $REGION --query 'InternetGateways[].InternetGatewayId' --output text 2>/dev/null || echo "")
            if [ -n "$IGW_ID" ]; then
                aws ec2 detach-internet-gateway --internet-gateway-id $IGW_ID --vpc-id $vpc_id --region $REGION 2>/dev/null || true
                aws ec2 delete-internet-gateway --internet-gateway-id $IGW_ID --region $REGION 2>/dev/null || true
            fi

            echo "     Deleting VPC..."
            aws ec2 delete-vpc --vpc-id $vpc_id --region $REGION 2>/dev/null || true
            echo "   ✅ VPC cleanup completed"
        done
    else
        echo "   ⏭️ No Bella VPCs found, skipping"
    fi
else
    echo "   ⏭️ VPC resources preserved"
fi

# 8. Delete CloudWatch Log Groups
echo "8️⃣ Deleting CloudWatch Log Groups..."
LOG_GROUPS=$(aws logs describe-log-groups --region $REGION --log-group-name-prefix "/aws/lambda/$LAMBDA_FUNCTION_NAME" --query 'logGroups[].logGroupName' --output text 2>/dev/null || echo "")
if [ -n "$LOG_GROUPS" ]; then
    for log_group in $LOG_GROUPS; do
        echo "   Deleting log group: $log_group"
        aws logs delete-log-group --log-group-name $log_group --region $REGION
        echo "   ✅ Log group deleted"
    done
else
    echo "   ⏭️ No Lambda log groups found, skipping"
fi

# 9. Clean up IAM roles (optional)
echo "9️⃣ IAM Role cleanup..."
read -p "Delete IAM roles created for Bella (Lambda execution role, etc.)? (y/N): " delete_iam
if [ "$delete_iam" = "y" ] || [ "$delete_iam" = "Y" ]; then
    # List and delete Lambda execution roles
    LAMBDA_ROLES=$(aws iam list-roles --query 'Roles[?contains(RoleName, `bella`) || contains(RoleName, `lambda`)].RoleName' --output text 2>/dev/null || echo "")

    for role in $LAMBDA_ROLES; do
        echo "   Processing IAM role: $role"

        # Detach policies
        ATTACHED_POLICIES=$(aws iam list-attached-role-policies --role-name $role --query 'AttachedPolicies[].PolicyArn' --output text 2>/dev/null || echo "")
        for policy_arn in $ATTACHED_POLICIES; do
            aws iam detach-role-policy --role-name $role --policy-arn $policy_arn 2>/dev/null || true
        done

        # Delete inline policies
        INLINE_POLICIES=$(aws iam list-role-policies --role-name $role --query 'PolicyNames[]' --output text 2>/dev/null || echo "")
        for policy_name in $INLINE_POLICIES; do
            aws iam delete-role-policy --role-name $role --policy-name $policy_name 2>/dev/null || true
        done

        # Delete role
        aws iam delete-role --role-name $role 2>/dev/null || true
        echo "   ✅ IAM role $role cleaned up"
    done
else
    echo "   ⏭️ IAM roles preserved"
fi

echo ""
echo "🎉 Infrastructure cleanup completed!"
echo ""
echo "📊 Summary:"
echo "- Lambda function deleted"
echo "- RDS instances deletion initiated (takes 5-10 minutes)"
echo "- Redis clusters deletion initiated (takes 5-10 minutes)"
echo "- Load balancers and target groups deleted"
echo "- CloudWatch logs cleaned up"
echo "- ECR repository: $([ "$delete_ecr" = "y" ] && echo "deleted" || echo "preserved")"
echo "- VPC resources: $([ "$delete_vpc" = "y" ] && echo "cleaned up" || echo "preserved")"
echo "- IAM roles: $([ "$delete_iam" = "y" ] && echo "cleaned up" || echo "preserved")"
echo ""
echo "💰 Expected monthly cost after cleanup: $0"
echo ""
echo "⚠️  Notes:"
echo "- RDS and Redis deletions are asynchronous and may take several minutes"
echo "- Check AWS console to verify all resources have been deleted"
echo "- Some resources may have dependencies that prevent immediate deletion"
# 🚀 Bella V3 AWS ECS Fargate Deployment

Complete the remaining 35% of your AWS deployment with these step-by-step scripts.

## 📋 Prerequisites

Before running these scripts, ensure you have:

✅ **Completed Setup:**
- ECR repository `bella-v3` with your Docker image
- RDS PostgreSQL instance `bella-db`
- Secrets Manager secret `bella-env` with all environment variables
- CloudWatch log group `/ecs/bella-prod`
- AWS CLI configured with appropriate permissions

## 🎯 Deployment Steps

### **Step 1: Update Variables**

Before running any scripts, update these values in each file:

```bash
# In ALL scripts, update these variables:
VPC_ID="vpc-xxxxxxxxx"                    # Your VPC ID where RDS lives
SUBNET_1="subnet-xxxxxxxxx"               # Public subnet 1 (different AZ)
SUBNET_2="subnet-xxxxxxxxx"               # Public subnet 2 (different AZ)
ACCOUNT_ID="123456789012"                 # Your 12-digit AWS Account ID
ECR_REPO_URI="123456789012.dkr.ecr.ca-central-1.amazonaws.com/bella-v3"
```

### **Step 2: Run Deployment Scripts**

Execute these scripts in order:

```bash
# Make scripts executable
chmod +x aws/*.sh

# 1. Create Security Groups
./aws/1-setup-security-groups.sh

# 2. Create Load Balancer
./aws/2-setup-load-balancer.sh

# 3. Create IAM Roles
./aws/3-setup-iam-roles.sh

# 4. Register Task Definition
./aws/4-register-task-definition.sh

# 5. Create ECS Service
./aws/5-create-ecs-service.sh

# 6. Validate Deployment
./aws/6-validate-deployment.sh
```

### **Step 3: Manual RDS Security Group Update**

⚠️ **Important**: After Step 1, manually update your RDS security group:

1. Go to AWS Console → EC2 → Security Groups
2. Find your RDS security group
3. Add inbound rule:
   - **Type**: PostgreSQL (5432)
   - **Source**: Custom → `sg-xxxxxxxxx` (ECS security group from Step 1)

## 🔧 Configuration Details

### **Resource Specifications**

- **CPU**: 256 (0.25 vCPU)
- **Memory**: 512 MB
- **Auto-scaling**: 1-3 tasks based on CPU usage
- **Health Checks**: `/healthz` endpoint every 30s
- **Logging**: CloudWatch Logs with 30-day retention

### **Security**

- **Network**: Private subnets for ECS tasks
- **Secrets**: All sensitive data from AWS Secrets Manager
- **IAM**: Least-privilege roles for execution and tasks
- **SSL**: Ready for ACM certificate (add HTTPS listener later)

## 📊 Monitoring

### **CloudWatch Logs**
```bash
# View logs
aws logs describe-log-streams --log-group-name /ecs/bella-prod

# Tail logs
aws logs tail /ecs/bella-prod --follow
```

### **Service Health**
```bash
# Check service status
aws ecs describe-services --cluster bella-prod-cluster --services bella-prod-service

# Check task health
aws ecs list-tasks --cluster bella-prod-cluster --service-name bella-prod-service
```

## 🌍 Access Your Application

After successful deployment:

- **Application**: `http://YOUR-ALB-DNS`
- **Admin Dashboard**: `http://YOUR-ALB-DNS/` (Basic Auth required)
- **Health Check**: `http://YOUR-ALB-DNS/healthz`
- **API**: `http://YOUR-ALB-DNS/assistant/book` (with API key header)

### **Default Credentials**
- **Admin Username**: `antar`
- **Admin Password**: `kam1234`
- **API Key**: `kam1234`

## 🔧 Troubleshooting

### **Common Issues**

1. **Tasks not starting**: Check CloudWatch logs for container errors
2. **Health checks failing**: Verify security groups allow port 8000
3. **Database connection failed**: Ensure RDS security group allows ECS access
4. **503 errors**: Tasks may still be starting (wait 2-5 minutes)

### **Useful Commands**

```bash
# Force new deployment
aws ecs update-service --cluster bella-prod-cluster --service bella-prod-service --force-new-deployment

# Scale service
aws ecs update-service --cluster bella-prod-cluster --service bella-prod-service --desired-count 2

# Check ALB target health
aws elbv2 describe-target-health --target-group-arn YOUR-TARGET-GROUP-ARN
```

## 💰 **Expected AWS Costs**

- **Monthly cost**: ~$42-54 for single user
- **Production ready**: ~$65-85 for 10-50 users
- **Excellent margins**: 85%+ profit with $350/month pricing

## 🎉 Next Steps

After successful deployment:

1. **Domain & SSL**: Set up Route 53 + ACM certificate
2. **CI/CD**: Extend GitHub Actions for automated deployments
3. **Monitoring**: Add CloudWatch alarms and SNS notifications
4. **Backups**: Configure RDS automated backups
5. **Go Live**: Start customer trials!

---

**🚀 Ready to deploy? Update the variables and run the scripts!**
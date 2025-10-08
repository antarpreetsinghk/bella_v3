# Terraform configuration for Bella Voice App on AWS
# Optimized for 50 calls/day - Minimal cost setup

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.1"
    }
  }

  # Local state for initial deployment
  # backend "s3" {
  #   bucket = "bella-terraform-state"
  #   key    = "production/terraform.tfstate"
  #   region = "us-east-1"
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "bella-voice-app"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# Variables
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"  # Cheapest region
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "app_name" {
  description = "Application name"
  type        = string
  default     = "bella-voice-app"
}

# Random password for database
resource "random_password" "db_password" {
  length  = 32
  special = true
}

# SSM Parameters for secrets
resource "aws_ssm_parameter" "db_password" {
  name  = "/${var.app_name}/${var.environment}/db/password"
  type  = "SecureString"
  value = random_password.db_password.result
}

resource "aws_ssm_parameter" "openai_api_key" {
  name  = "/${var.app_name}/${var.environment}/openai/api_key"
  type  = "SecureString"
  value = var.openai_api_key
}

resource "aws_ssm_parameter" "bella_api_key" {
  name  = "/${var.app_name}/${var.environment}/bella/api_key"
  type  = "SecureString"
  value = var.bella_api_key
}

resource "aws_ssm_parameter" "twilio_auth_token" {
  name  = "/${var.app_name}/${var.environment}/twilio/auth_token"
  type  = "SecureString"
  value = var.twilio_auth_token
}

# Input variables for secrets (passed via terraform.tfvars or environment)
variable "openai_api_key" {
  description = "OpenAI API Key"
  type        = string
  sensitive   = true
}

variable "bella_api_key" {
  description = "Bella API Key"
  type        = string
  sensitive   = true
}

variable "twilio_auth_token" {
  description = "Twilio Auth Token"
  type        = string
  sensitive   = true
}

variable "twilio_account_sid" {
  description = "Twilio Account SID"
  type        = string
}

variable "twilio_phone_number" {
  description = "Twilio Phone Number"
  type        = string
}

# VPC (use default VPC to save costs)
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# IAM role for Lambda
resource "aws_iam_role" "lambda_role" {
  name = "${var.app_name}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# IAM policy for Lambda
resource "aws_iam_role_policy" "lambda_policy" {
  name = "${var.app_name}-lambda-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "rds:*",
          "rds-db:connect"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters",
          "ssm:GetParametersByPath"
        ]
        Resource = "arn:aws:ssm:${var.aws_region}:*:parameter/${var.app_name}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = aws_dynamodb_table.sessions.arn
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:CreateNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DeleteNetworkInterface"
        ]
        Resource = "*"
      }
    ]
  })
}

# Aurora Serverless v2 cluster
resource "aws_rds_cluster" "main" {
  cluster_identifier             = "${var.app_name}-cluster"
  engine                        = "aurora-postgresql"
  engine_mode                   = "provisioned"
  engine_version                = "15.4"
  database_name                 = "bella"
  master_username               = "bella_admin"
  master_password               = random_password.db_password.result
  backup_retention_period       = 7
  preferred_backup_window       = "03:00-04:00"
  preferred_maintenance_window  = "Mon:04:00-Mon:05:00"
  skip_final_snapshot          = true
  deletion_protection          = false

  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name   = aws_db_subnet_group.main.name

  serverlessv2_scaling_configuration {
    max_capacity = 1
    min_capacity = 0.5
  }

  tags = {
    Name = "${var.app_name}-aurora-cluster"
  }
}

# Aurora instance
resource "aws_rds_cluster_instance" "main" {
  count              = 1
  identifier         = "${var.app_name}-instance-${count.index}"
  cluster_identifier = aws_rds_cluster.main.id
  instance_class     = "db.serverless"
  engine             = aws_rds_cluster.main.engine
  engine_version     = aws_rds_cluster.main.engine_version

  performance_insights_enabled = false  # Save costs
  monitoring_interval         = 0       # Disable enhanced monitoring
}

# DB subnet group
resource "aws_db_subnet_group" "main" {
  name       = "${var.app_name}-subnet-group"
  subnet_ids = data.aws_subnets.default.ids

  tags = {
    Name = "${var.app_name}-subnet-group"
  }
}

# Security group for RDS
resource "aws_security_group" "rds" {
  name        = "${var.app_name}-rds-sg"
  description = "Security group for RDS database"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.app_name}-rds-sg"
  }
}

# Security group for Lambda
resource "aws_security_group" "lambda" {
  name        = "${var.app_name}-lambda-sg"
  description = "Security group for Lambda function"
  vpc_id      = data.aws_vpc.default.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.app_name}-lambda-sg"
  }
}

# DynamoDB table for session storage
resource "aws_dynamodb_table" "sessions" {
  name           = "${var.app_name}-sessions"
  billing_mode   = "PAY_PER_REQUEST"  # No provisioned capacity
  hash_key       = "call_sid"

  attribute {
    name = "call_sid"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = {
    Name = "${var.app_name}-sessions"
  }
}

# Lambda function (placeholder - actual deployment via GitHub Actions)
resource "aws_lambda_function" "app" {
  function_name = var.app_name
  role         = aws_iam_role.lambda_role.arn
  handler      = "handler.handler"
  runtime      = "python3.11"
  timeout      = 30
  memory_size  = 512

  # Dummy deployment package - will be replaced by CI/CD
  filename = "deployment.zip"

  vpc_config {
    subnet_ids         = data.aws_subnets.default.ids
    security_group_ids = [aws_security_group.lambda.id]
  }

  environment {
    variables = {
      APP_ENV                  = var.environment
      DATABASE_URL            = "postgresql://bella_admin:${random_password.db_password.result}@${aws_rds_cluster.main.endpoint}:5432/bella"
      OPENAI_MODEL            = "gpt-4o-mini"
      TWILIO_ACCOUNT_SID      = var.twilio_account_sid
      TWILIO_PHONE_NUMBER     = var.twilio_phone_number
      GOOGLE_CALENDAR_ENABLED = "true"
      DYNAMODB_TABLE_NAME     = aws_dynamodb_table.sessions.name
    }
  }

  depends_on = [
    aws_iam_role_policy.lambda_policy,
    aws_cloudwatch_log_group.lambda_logs,
  ]

  tags = {
    Name = var.app_name
  }

  lifecycle {
    ignore_changes = [
      filename,
      source_code_hash,
      environment
    ]
  }
}

# Lambda Function URL (free alternative to API Gateway)
resource "aws_lambda_function_url" "app" {
  function_name      = aws_lambda_function.app.function_name
  authorization_type = "NONE"

  cors {
    allow_credentials = false
    allow_headers     = ["*"]
    allow_methods     = ["*"]
    allow_origins     = ["*"]
    expose_headers    = ["*"]
    max_age          = 86400
  }
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${var.app_name}"
  retention_in_days = 7  # Save costs - only keep logs for 7 days
}

# CloudWatch Alarms for monitoring
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "${var.app_name}-lambda-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "This metric monitors lambda errors"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = aws_lambda_function.app.function_name
  }
}

resource "aws_cloudwatch_metric_alarm" "lambda_duration" {
  alarm_name          = "${var.app_name}-lambda-duration"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Average"
  threshold           = "25000"  # 25 seconds (close to 30s timeout)
  alarm_description   = "This metric monitors lambda duration"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = aws_lambda_function.app.function_name
  }
}

# SNS topic for alerts
resource "aws_sns_topic" "alerts" {
  name = "${var.app_name}-alerts"
}

# Outputs
output "lambda_function_url" {
  description = "URL for the Lambda function"
  value       = aws_lambda_function_url.app.function_url
}

output "database_endpoint" {
  description = "Aurora cluster endpoint"
  value       = aws_rds_cluster.main.endpoint
  sensitive   = true
}

output "database_url" {
  description = "Complete database URL"
  value       = "postgresql://bella_admin:${random_password.db_password.result}@${aws_rds_cluster.main.endpoint}:5432/bella"
  sensitive   = true
}

output "twilio_webhook_url" {
  description = "URL to configure in Twilio webhooks"
  value       = "${aws_lambda_function_url.app.function_url}twilio/voice"
}

output "sns_topic_arn" {
  description = "SNS topic ARN for alerts"
  value       = aws_sns_topic.alerts.arn
}
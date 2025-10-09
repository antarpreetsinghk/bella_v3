terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Data sources
data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# VPC
resource "aws_vpc" "bella_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = "bella-voice-vpc"
    Environment = "production"
    Project     = "bella-voice-app"
  }
}

# Internet Gateway
resource "aws_internet_gateway" "bella_igw" {
  vpc_id = aws_vpc.bella_vpc.id

  tags = {
    Name        = "bella-voice-igw"
    Environment = "production"
  }
}

# Public Subnet
resource "aws_subnet" "bella_public_subnet" {
  vpc_id                  = aws_vpc.bella_vpc.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = data.aws_availability_zones.available.names[0]
  map_public_ip_on_launch = true

  tags = {
    Name        = "bella-voice-public-subnet"
    Environment = "production"
  }
}

# Route Table
resource "aws_route_table" "bella_public_rt" {
  vpc_id = aws_vpc.bella_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.bella_igw.id
  }

  tags = {
    Name        = "bella-voice-public-rt"
    Environment = "production"
  }
}

# Route Table Association
resource "aws_route_table_association" "bella_public_rta" {
  subnet_id      = aws_subnet.bella_public_subnet.id
  route_table_id = aws_route_table.bella_public_rt.id
}

# Security Group
resource "aws_security_group" "bella_app_sg" {
  name_prefix = "bella-voice-app-"
  vpc_id      = aws_vpc.bella_vpc.id

  # HTTP
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # HTTPS
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # SSH
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.ssh_cidr_blocks]
  }

  # Application port (for direct access if needed)
  ingress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }

  # All outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "bella-voice-app-sg"
    Environment = "production"
  }
}

# Key Pair
resource "aws_key_pair" "bella_key" {
  key_name   = "bella-voice-app-key"
  public_key = var.public_key
}

# EC2 Instance
resource "aws_instance" "bella_app" {
  ami                     = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  key_name               = aws_key_pair.bella_key.key_name
  vpc_security_group_ids  = [aws_security_group.bella_app_sg.id]
  subnet_id              = aws_subnet.bella_public_subnet.id

  root_block_device {
    volume_type = "gp3"
    volume_size = var.root_volume_size
    encrypted   = true
  }

  user_data = base64encode(templatefile("${path.module}/user-data.sh", {
    aws_region = var.aws_region
  }))

  tags = {
    Name        = "bella-voice-app"
    Environment = "production"
    Project     = "bella-voice-app"
    Backup      = "daily"
  }
}

# Elastic IP
resource "aws_eip" "bella_eip" {
  domain   = "vpc"
  instance = aws_instance.bella_app.id

  tags = {
    Name        = "bella-voice-app-eip"
    Environment = "production"
  }

  depends_on = [aws_internet_gateway.bella_igw]
}

# ECR Repository
resource "aws_ecr_repository" "bella_app" {
  name = "bella-voice-app"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = {
    Environment = "production"
    Project     = "bella-voice-app"
  }
}

# ECR Lifecycle Policy
resource "aws_ecr_lifecycle_policy" "bella_app_policy" {
  repository = aws_ecr_repository.bella_app.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 10 images"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["v"]
          countType     = "imageCountMoreThan"
          countNumber   = 10
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 2
        description  = "Delete untagged images older than 1 day"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 1
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}
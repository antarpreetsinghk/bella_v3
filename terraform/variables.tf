variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "ca-central-1"
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.small"
}

variable "root_volume_size" {
  description = "Size of the root EBS volume in GB"
  type        = number
  default     = 20
}

variable "public_key" {
  description = "SSH public key for EC2 access"
  type        = string
}

variable "ssh_cidr_blocks" {
  description = "CIDR blocks allowed for SSH access"
  type        = string
  default     = "0.0.0.0/0"
}
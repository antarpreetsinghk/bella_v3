output "instance_id" {
  description = "ID of the EC2 instance"
  value       = aws_instance.bella_app.id
}

output "instance_public_ip" {
  description = "Public IP address of the EC2 instance"
  value       = aws_eip.bella_eip.public_ip
}

output "instance_public_dns" {
  description = "Public DNS name of the EC2 instance"
  value       = aws_instance.bella_app.public_dns
}

output "ecr_repository_url" {
  description = "URL of the ECR repository"
  value       = aws_ecr_repository.bella_app.repository_url
}

output "ssh_connection_command" {
  description = "SSH command to connect to the instance"
  value       = "ssh -i ~/.ssh/bella-voice-app ubuntu@${aws_eip.bella_eip.public_ip}"
}

output "application_urls" {
  description = "Application URLs"
  value = {
    health_check    = "https://${aws_eip.bella_eip.public_ip}/healthz"
    twilio_webhook = "https://${aws_eip.bella_eip.public_ip}/twilio/voice"
    base_url       = "https://${aws_eip.bella_eip.public_ip}"
  }
}
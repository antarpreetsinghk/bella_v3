# Security Policy

## Overview

This document outlines the security measures, policies, and procedures for the Bella V3 voice appointment booking system.

## Security Architecture

### 1. Application Security

#### Authentication & Authorization
- **API Key Protection**: All sensitive endpoints protected with `BELLA_API_KEY`
- **Twilio Webhook Verification**: Validates incoming Twilio requests (configurable)
- **CORS Configuration**: Controlled cross-origin access
- **Rate Limiting**: Prevents abuse and DDoS attacks

#### Input Validation
- **Pydantic Models**: All input data validated using Pydantic schemas
- **Phone Number Validation**: Uses `phonenumbers` library for international validation
- **SQL Injection Protection**: SQLAlchemy ORM with parameterized queries
- **XSS Prevention**: All user input sanitized and escaped

#### Data Protection
- **Environment Variables**: Sensitive data stored in environment variables
- **Secrets Management**: AWS Secrets Manager for production secrets
- **Database Encryption**: PostgreSQL with SSL/TLS encryption
- **Redis Security**: Connection encryption and authentication

### 2. Infrastructure Security

#### Container Security
- **Non-root User**: Application runs as unprivileged user (UID 1000)
- **Read-only Filesystem**: Container filesystem mounted as read-only where possible
- **Capability Dropping**: Minimal Linux capabilities (drop ALL, add only necessary)
- **Security Options**: `no-new-privileges` and seccomp profiles
- **Resource Limits**: CPU and memory constraints to prevent resource exhaustion

#### Network Security
- **VPC Isolation**: AWS VPC with private subnets
- **Security Groups**: Restrictive inbound/outbound rules
- **Load Balancer**: AWS ALB with security headers
- **TLS Termination**: HTTPS/TLS 1.2+ for all external traffic

#### Database Security
- **RDS Security**: AWS RDS with encryption at rest and in transit
- **Connection Security**: SSL-required connections
- **Network Isolation**: Database in private subnet
- **Backup Encryption**: Automated backups with encryption

### 3. CI/CD Security

#### Automated Security Scanning
- **Dependency Scanning**: Safety and pip-audit for known vulnerabilities
- **Static Analysis**: Bandit for Python security issues
- **Container Scanning**: Trivy for container vulnerabilities
- **Secret Detection**: Regex patterns and git hooks for exposed secrets

#### Secure Development
- **Branch Protection**: Main branch requires PR reviews
- **Signed Commits**: Encouraged for sensitive changes
- **Environment Isolation**: Separate staging and production environments
- **Deployment Approval**: Manual approval required for production

## Security Controls

### 1. Data Classification

| Classification | Examples | Protection |
|---------------|----------|------------|
| **Public** | Health endpoints, documentation | Standard web protection |
| **Internal** | Application logs, metrics | VPC isolation, authentication |
| **Confidential** | User data, appointments | Encryption, access controls |
| **Restricted** | API keys, passwords | Secrets management, rotation |

### 2. Access Controls

#### Production Access
- **AWS IAM**: Role-based access with minimal permissions
- **MFA Required**: Multi-factor authentication for all human access
- **Session Management**: Temporary credentials with time limits
- **Audit Logging**: All access logged and monitored

#### Development Access
- **Git Repository**: Branch protection and review requirements
- **Development Environment**: Local Docker containers with test data
- **API Testing**: Separate test keys and endpoints

### 3. Monitoring & Alerting

#### Security Monitoring
- **CloudWatch Logs**: Centralized logging with retention policies
- **Error Tracking**: Automated alerting for security-related errors
- **Performance Monitoring**: Unusual patterns that may indicate attacks
- **Dependency Alerts**: Automated notifications for vulnerable dependencies

#### Incident Response
- **Security Incidents**: Defined escalation procedures
- **Vulnerability Disclosure**: Responsible disclosure policy
- **Patch Management**: Regular updates and security patches
- **Backup & Recovery**: Encrypted backups with tested restore procedures

## Threat Model

### 1. External Threats

#### Network Attacks
- **DDoS Protection**: Rate limiting and AWS Shield
- **Man-in-the-Middle**: TLS encryption for all traffic
- **Injection Attacks**: Input validation and parameterized queries

#### Application Attacks
- **Authentication Bypass**: API key validation and secure storage
- **Data Exposure**: Minimal data collection and encryption
- **Code Injection**: Static analysis and secure coding practices

### 2. Internal Threats

#### Insider Threats
- **Access Controls**: Principle of least privilege
- **Audit Trails**: Comprehensive logging of all actions
- **Code Reviews**: Multiple eyes on all changes

#### Supply Chain
- **Dependency Management**: Automated vulnerability scanning
- **Container Security**: Base image scanning and updates
- **Third-party Services**: Security assessment and monitoring

## Compliance & Standards

### 1. Privacy Protection

#### Data Collection
- **Minimal Collection**: Only necessary data collected
- **Purpose Limitation**: Data used only for stated purposes
- **Retention Limits**: Automatic deletion of old data

#### User Rights
- **Access Rights**: Users can request their data
- **Correction Rights**: Users can update their information
- **Deletion Rights**: Users can request data deletion

### 2. Industry Standards

#### Security Frameworks
- **OWASP Top 10**: Regular assessment against common vulnerabilities
- **NIST Cybersecurity Framework**: Risk management approach
- **ISO 27001**: Information security management system

## Security Procedures

### 1. Vulnerability Management

#### Discovery
- **Automated Scanning**: Daily dependency and container scans
- **Manual Testing**: Regular penetration testing
- **Bug Bounty**: Responsible disclosure program

#### Response
- **Assessment**: Risk evaluation within 24 hours
- **Patching**: Critical issues addressed within 72 hours
- **Communication**: Stakeholder notification as appropriate

### 2. Incident Response

#### Preparation
- **Response Team**: Defined roles and responsibilities
- **Communication Plan**: Internal and external notification procedures
- **Recovery Procedures**: Step-by-step restoration processes

#### Detection & Analysis
- **Monitoring Systems**: Automated alerting for suspicious activity
- **Log Analysis**: Regular review of security logs
- **Threat Intelligence**: Integration with security feeds

#### Containment & Recovery
- **Isolation Procedures**: Network and system isolation
- **Evidence Preservation**: Forensic data collection
- **System Restoration**: Verified clean restoration

## Security Training

### 1. Developer Training
- **Secure Coding**: Regular training on secure development practices
- **Threat Awareness**: Understanding of common attack vectors
- **Tool Usage**: Proper use of security tools and frameworks

### 2. Operational Training
- **Incident Response**: Regular drills and simulations
- **Monitoring**: Effective use of security monitoring tools
- **Compliance**: Understanding of regulatory requirements

## Contact Information

### Security Team
- **Security Officer**: [security@company.com]
- **Incident Response**: [incident@company.com]
- **Vulnerability Reports**: [security@company.com]

### Emergency Contacts
- **24/7 Incident Line**: [phone number]
- **Escalation Contacts**: [management contacts]

---

**Document Version**: 1.0
**Last Updated**: 2025-09-29
**Next Review**: 2025-12-29
**Owner**: Security Team
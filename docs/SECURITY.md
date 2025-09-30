# Bella V3 Production Security Guide

> **Comprehensive security configuration and best practices for Bella V3**
> Enterprise security standards for voice appointment booking system

## 🔒 Security Overview

Bella V3 implements defense-in-depth security with multiple layers of protection:

### Security Layers
```
┌─────────────────────────────────────────────────────────────┐
│                    External Threats                        │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│               Network Security (Firewall/WAF)              │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│              Transport Security (TLS/HTTPS)                │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│            Application Security (Auth/Validation)          │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│              Data Security (Encryption/Access)             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🛡️ Authentication & Authorization

### API Key Security

#### Strong API Key Generation
```bash
# Generate cryptographically secure API key
openssl rand -hex 32

# Example output: 4a7c8b9e3f2d1a6b5c4e9f8a7b6c5d4e3f2a1b9c8d7e6f5a4b3c2d1e0f9a8b7c
```

#### API Key Management
```python
# app/core/security.py
import secrets
import hashlib
import time

class APIKeyManager:
    """Secure API key management"""

    @staticmethod
    def generate_key() -> str:
        """Generate cryptographically secure API key"""
        return secrets.token_hex(32)

    @staticmethod
    def hash_key(api_key: str) -> str:
        """Hash API key for storage"""
        return hashlib.sha256(api_key.encode()).hexdigest()

    @staticmethod
    def verify_key(provided_key: str, stored_hash: str) -> bool:
        """Verify API key against stored hash"""
        return secrets.compare_digest(
            hashlib.sha256(provided_key.encode()).hexdigest(),
            stored_hash
        )
```

#### API Key Rotation Policy
```bash
# Monthly API key rotation script
#!/bin/bash

# Generate new API key
NEW_KEY=$(openssl rand -hex 32)

# Update environment file
sed -i "s/BELLA_API_KEY=.*/BELLA_API_KEY=\"$NEW_KEY\"/" /opt/bella/production.env

# Restart application
supervisorctl restart bella bella-worker

# Log rotation
echo "$(date): API key rotated" >> /var/log/bella/security.log
```

### Twilio Webhook Security

#### Signature Validation
```python
# app/api/routes/twilio.py
from twilio.request_validator import RequestValidator

def validate_twilio_signature(request, body: bytes) -> bool:
    """Validate Twilio webhook signature"""

    if not TWILIO_AUTH_TOKEN:
        logger.warning("Twilio auth token not configured")
        return False

    signature = request.headers.get("X-Twilio-Signature", "")
    url = str(request.url)

    # Handle different URL schemes for validation
    validator = RequestValidator(TWILIO_AUTH_TOKEN)

    # Try multiple URL formats
    possible_urls = [
        url,
        url.replace("http://", "https://"),
        "https://bella.yourcompany.com/twilio/voice"
    ]

    for test_url in possible_urls:
        if validator.validate(test_url, dict(parse_qsl(body.decode())), signature):
            return True

    return False
```

#### IP Allowlisting (Optional)
```nginx
# /etc/nginx/sites-available/bella
location /twilio/ {
    # Allow Twilio IP ranges (optional additional security)
    allow 54.172.60.0/23;
    allow 54.244.51.0/24;
    allow 54.171.127.192/27;
    deny all;

    proxy_pass http://bella_backend;
    # ... other proxy settings
}
```

---

## 🔐 Data Protection

### Environment Variables Security

#### Secure Storage
```bash
# Set proper file permissions
chmod 600 /opt/bella/production.env
chown bella:bella /opt/bella/production.env

# Verify permissions
ls -la /opt/bella/production.env
# Should show: -rw------- 1 bella bella
```

#### Environment Variable Validation
```python
# app/core/config.py
import os
from typing import Optional

class SecurityConfig:
    """Security configuration validation"""

    @staticmethod
    def validate_api_key(api_key: str) -> bool:
        """Validate API key strength"""
        if len(api_key) < 32:
            raise ValueError("API key must be at least 32 characters")

        # Check for common weak patterns
        weak_patterns = ['password', '123456', 'abcdef']
        if any(pattern in api_key.lower() for pattern in weak_patterns):
            raise ValueError("API key contains weak patterns")

        return True

    @staticmethod
    def validate_database_url(url: str) -> bool:
        """Validate database URL security"""
        if 'password' in url.lower() and len(url.split(':')[2].split('@')[0]) < 16:
            raise ValueError("Database password is too weak")

        return True
```

### Database Security

#### Connection Security
```python
# app/db/session.py
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

def create_secure_engine(database_url: str):
    """Create database engine with security settings"""

    return create_engine(
        database_url,
        # Connection pooling
        poolclass=QueuePool,
        pool_size=20,
        max_overflow=30,
        pool_timeout=30,

        # Security settings
        connect_args={
            "sslmode": "require",  # Require SSL
            "connect_timeout": 10,
            "application_name": "bella_v3_prod"
        },

        # Logging (be careful not to log passwords)
        echo=False,
        echo_pool=False
    )
```

#### Database Access Control
```sql
-- PostgreSQL security configuration

-- Create read-only user for monitoring
CREATE USER bella_monitor WITH PASSWORD 'secure_monitor_password';
GRANT CONNECT ON DATABASE bella_prod TO bella_monitor;
GRANT USAGE ON SCHEMA public TO bella_monitor;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO bella_monitor;

-- Revoke unnecessary permissions
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO bella_user;

-- Enable row-level security (if needed)
ALTER TABLE appointments ENABLE ROW LEVEL SECURITY;

-- Create policies for data access
CREATE POLICY appointment_access_policy ON appointments
    FOR ALL TO bella_user
    USING (user_id = current_setting('app.current_user_id')::int);
```

---

## 🌐 Network Security

### Firewall Configuration

#### UFW (Ubuntu Firewall)
```bash
# Reset firewall to defaults
sudo ufw --force reset

# Default policies
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow essential services
sudo ufw allow 22/tcp comment 'SSH'
sudo ufw allow 80/tcp comment 'HTTP'
sudo ufw allow 443/tcp comment 'HTTPS'

# Limit SSH connections (prevent brute force)
sudo ufw limit 22/tcp

# Enable firewall
sudo ufw --force enable

# Check status
sudo ufw status verbose
```

#### Fail2Ban (Intrusion Prevention)
```bash
# Install Fail2Ban
sudo apt install fail2ban

# Configure Fail2Ban
sudo tee /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3

[nginx-http-auth]
enabled = true
filter = nginx-http-auth
port = http,https
logpath = /var/log/nginx/bella_error.log

[nginx-limit-req]
enabled = true
filter = nginx-limit-req
port = http,https
logpath = /var/log/nginx/bella_error.log
maxretry = 10
EOF

# Start and enable Fail2Ban
sudo systemctl start fail2ban
sudo systemctl enable fail2ban
```

### TLS/SSL Configuration

#### Strong TLS Configuration
```nginx
# /etc/nginx/sites-available/bella - SSL section
server {
    listen 443 ssl http2;
    server_name bella.yourcompany.com;

    # SSL Certificate
    ssl_certificate /etc/letsencrypt/live/bella.yourcompany.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/bella.yourcompany.com/privkey.pem;

    # Strong SSL Configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-SHA384;
    ssl_prefer_server_ciphers off;

    # SSL Session Settings
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_session_tickets off;

    # OCSP Stapling
    ssl_stapling on;
    ssl_stapling_verify on;
    ssl_trusted_certificate /etc/letsencrypt/live/bella.yourcompany.com/chain.pem;
    resolver 8.8.8.8 8.8.4.4 valid=300s;
    resolver_timeout 5s;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";
    add_header Referrer-Policy "strict-origin-when-cross-origin";
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'";

    # ... rest of configuration
}
```

#### SSL Certificate Monitoring
```bash
#!/bin/bash
# SSL certificate monitoring script

DOMAIN="bella.yourcompany.com"
ALERT_DAYS=30

# Check certificate expiration
EXPIRY_DATE=$(echo | openssl s_client -connect $DOMAIN:443 -servername $DOMAIN 2>/dev/null | openssl x509 -noout -enddate | cut -d= -f2)
EXPIRY_EPOCH=$(date -d "$EXPIRY_DATE" +%s)
CURRENT_EPOCH=$(date +%s)
DAYS_UNTIL_EXPIRY=$(( (EXPIRY_EPOCH - CURRENT_EPOCH) / 86400 ))

if [ $DAYS_UNTIL_EXPIRY -lt $ALERT_DAYS ]; then
    echo "WARNING: SSL certificate for $DOMAIN expires in $DAYS_UNTIL_EXPIRY days"

    # Send alert (if Slack webhook configured)
    if [ -n "$SLACK_WEBHOOK_URL" ]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"⚠️ SSL Certificate Alert: $DOMAIN expires in $DAYS_UNTIL_EXPIRY days\"}" \
            "$SLACK_WEBHOOK_URL"
    fi
fi
```

---

## 🔍 Security Monitoring

### Security Logging

#### Application Security Logs
```python
# app/core/security_logger.py
import logging
from datetime import datetime
from typing import Dict, Any

class SecurityLogger:
    """Security event logging"""

    def __init__(self):
        self.logger = logging.getLogger('security')
        handler = logging.FileHandler('/var/log/bella/security.log')
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def log_auth_attempt(self, success: bool, ip: str, endpoint: str):
        """Log authentication attempts"""
        status = "SUCCESS" if success else "FAILED"
        self.logger.info(
            f"AUTH_{status} - IP: {ip} - Endpoint: {endpoint}"
        )

    def log_suspicious_activity(self, activity: str, details: Dict[str, Any]):
        """Log suspicious activities"""
        self.logger.warning(
            f"SUSPICIOUS_ACTIVITY - {activity} - Details: {details}"
        )

    def log_security_event(self, event: str, details: Dict[str, Any]):
        """Log general security events"""
        self.logger.info(
            f"SECURITY_EVENT - {event} - Details: {details}"
        )

# Global security logger instance
security_logger = SecurityLogger()
```

#### Security Audit Script
```bash
#!/bin/bash
# Security audit script

echo "=== Bella V3 Security Audit ==="
echo "Date: $(date)"
echo

# Check file permissions
echo "1. File Permissions:"
echo "Environment file:"
ls -la /opt/bella/production.env

echo "Application directory:"
ls -la /opt/bella/ | head -5

# Check running processes
echo -e "\n2. Running Processes:"
ps aux | grep -E "(bella|gunicorn|nginx)" | grep -v grep

# Check open ports
echo -e "\n3. Open Ports:"
ss -tlnp | grep -E ":(80|443|8000|5432|6379)"

# Check failed login attempts
echo -e "\n4. Recent Failed SSH Attempts:"
grep "Failed password" /var/log/auth.log | tail -5

# Check SSL certificate
echo -e "\n5. SSL Certificate Status:"
echo | openssl s_client -connect bella.yourcompany.com:443 -servername bella.yourcompany.com 2>/dev/null | openssl x509 -noout -subject -dates

# Check firewall status
echo -e "\n6. Firewall Status:"
ufw status

# Check for suspicious API activity
echo -e "\n7. Recent API Activity:"
grep -E "(401|403|429)" /var/log/nginx/bella_access.log | tail -5

echo -e "\n=== Audit Complete ==="
```

### Intrusion Detection

#### Log Analysis for Anomalies
```bash
#!/bin/bash
# Anomaly detection script

LOG_FILE="/var/log/bella/security.log"
ALERT_THRESHOLD=10

# Check for authentication failures
AUTH_FAILURES=$(grep "AUTH_FAILED" $LOG_FILE | wc -l)
if [ $AUTH_FAILURES -gt $ALERT_THRESHOLD ]; then
    echo "WARNING: High number of authentication failures: $AUTH_FAILURES"
fi

# Check for suspicious patterns
SUSPICIOUS_IPS=$(grep "SUSPICIOUS_ACTIVITY" $LOG_FILE | awk '{print $5}' | sort | uniq -c | sort -nr | head -5)
if [ -n "$SUSPICIOUS_IPS" ]; then
    echo "WARNING: Suspicious activity from IPs:"
    echo "$SUSPICIOUS_IPS"
fi

# Check for rate limiting violations
RATE_LIMIT_VIOLATIONS=$(grep "rate limit exceeded" /var/log/nginx/bella_error.log | wc -l)
if [ $RATE_LIMIT_VIOLATIONS -gt 50 ]; then
    echo "WARNING: High number of rate limit violations: $RATE_LIMIT_VIOLATIONS"
fi
```

---

## 🔐 Secrets Management

### Environment Secrets

#### Secure Secret Storage
```bash
# Create secrets directory
sudo mkdir -p /opt/bella/secrets
sudo chown bella:bella /opt/bella/secrets
sudo chmod 700 /opt/bella/secrets

# Store individual secrets
echo "your-openai-key" | sudo tee /opt/bella/secrets/openai_key
echo "your-twilio-token" | sudo tee /opt/bella/secrets/twilio_token

# Set permissions
sudo chown bella:bella /opt/bella/secrets/*
sudo chmod 600 /opt/bella/secrets/*
```

#### Secret Loading in Application
```python
# app/core/secrets.py
import os
from pathlib import Path

class SecretManager:
    """Secure secret management"""

    def __init__(self, secrets_dir: str = "/opt/bella/secrets"):
        self.secrets_dir = Path(secrets_dir)

    def get_secret(self, name: str) -> str:
        """Load secret from file"""
        secret_file = self.secrets_dir / name

        if not secret_file.exists():
            raise FileNotFoundError(f"Secret {name} not found")

        # Check file permissions
        stat = secret_file.stat()
        if stat.st_mode & 0o077:
            raise PermissionError(f"Secret {name} has insecure permissions")

        return secret_file.read_text().strip()

    def rotate_secret(self, name: str, new_value: str):
        """Rotate a secret"""
        secret_file = self.secrets_dir / name

        # Backup old secret
        backup_file = self.secrets_dir / f"{name}.backup"
        if secret_file.exists():
            secret_file.rename(backup_file)

        # Write new secret
        secret_file.write_text(new_value)
        secret_file.chmod(0o600)

        # Log rotation
        logger.info(f"Secret {name} rotated")

# Usage in settings
secret_manager = SecretManager()
OPENAI_API_KEY = secret_manager.get_secret("openai_key")
```

### Database Credentials

#### Encrypted Database Passwords
```python
# app/core/crypto.py
from cryptography.fernet import Fernet
import base64
import os

class CredentialManager:
    """Encrypted credential management"""

    def __init__(self):
        # Load encryption key from environment
        key = os.getenv('BELLA_ENCRYPTION_KEY')
        if not key:
            raise ValueError("BELLA_ENCRYPTION_KEY not set")

        self.fernet = Fernet(key.encode())

    def encrypt_credential(self, credential: str) -> str:
        """Encrypt a credential"""
        encrypted = self.fernet.encrypt(credential.encode())
        return base64.b64encode(encrypted).decode()

    def decrypt_credential(self, encrypted_credential: str) -> str:
        """Decrypt a credential"""
        encrypted_bytes = base64.b64decode(encrypted_credential.encode())
        decrypted = self.fernet.decrypt(encrypted_bytes)
        return decrypted.decode()

# Generate encryption key
def generate_encryption_key() -> str:
    """Generate new encryption key"""
    return Fernet.generate_key().decode()
```

---

## 📋 Security Compliance

### Security Checklist

#### Infrastructure Security ✅
- [ ] Firewall configured with minimal open ports
- [ ] SSH key-based authentication only
- [ ] Regular security updates automated
- [ ] Intrusion detection system configured
- [ ] SSL/TLS with strong cipher suites
- [ ] Security headers implemented
- [ ] Rate limiting configured

#### Application Security ✅
- [ ] Strong API key authentication
- [ ] Twilio webhook signature validation
- [ ] Input validation and sanitization
- [ ] SQL injection prevention
- [ ] XSS protection headers
- [ ] Secrets properly managed
- [ ] Error messages don't leak information

#### Data Security ✅
- [ ] Database access restricted
- [ ] Environment variables secured
- [ ] Backup encryption enabled
- [ ] Log rotation configured
- [ ] Sensitive data not logged
- [ ] Data retention policies defined

#### Monitoring Security ✅
- [ ] Security event logging enabled
- [ ] Failed authentication tracking
- [ ] Suspicious activity detection
- [ ] SSL certificate monitoring
- [ ] Security audit scheduled
- [ ] Incident response plan documented

### Compliance Standards

#### GDPR Considerations
```python
# app/core/privacy.py
class PrivacyManager:
    """GDPR compliance utilities"""

    def anonymize_phone_number(self, phone: str) -> str:
        """Anonymize phone number for logging"""
        if len(phone) > 4:
            return phone[:3] + "****" + phone[-1:]
        return "****"

    def log_data_access(self, user_id: int, data_type: str, purpose: str):
        """Log data access for audit"""
        audit_logger.info(
            f"DATA_ACCESS - User: {user_id} - Type: {data_type} - Purpose: {purpose}"
        )

    def data_retention_cleanup(self):
        """Clean up old data per retention policy"""
        # Implementation for data cleanup
        pass
```

---

## 🚨 Incident Response

### Security Incident Procedures

#### Immediate Response
```bash
#!/bin/bash
# Emergency security response script

echo "=== SECURITY INCIDENT RESPONSE ==="

# 1. Stop application (if compromised)
echo "Stopping application..."
supervisorctl stop bella bella-worker

# 2. Block suspicious IPs
echo "Enter suspicious IP to block (or press Enter to skip):"
read SUSPICIOUS_IP
if [ -n "$SUSPICIOUS_IP" ]; then
    ufw insert 1 deny from $SUSPICIOUS_IP
    echo "Blocked IP: $SUSPICIOUS_IP"
fi

# 3. Preserve logs
echo "Preserving logs..."
INCIDENT_DIR="/var/log/bella/incident_$(date +%Y%m%d_%H%M%S)"
mkdir -p $INCIDENT_DIR
cp /var/log/bella/* $INCIDENT_DIR/
cp /var/log/nginx/bella_* $INCIDENT_DIR/

# 4. Change API keys
echo "Generating new API key..."
NEW_API_KEY=$(openssl rand -hex 32)
echo "New API key: $NEW_API_KEY"
echo "Update production.env with new key before restarting"

# 5. Check for unauthorized changes
echo "Checking for unauthorized changes..."
find /opt/bella -name "*.py" -mtime -1 -ls

echo "=== INCIDENT RESPONSE COMPLETE ==="
echo "Incident logs saved to: $INCIDENT_DIR"
echo "Manual verification required before restarting application"
```

#### Post-Incident Analysis
```bash
#!/bin/bash
# Post-incident analysis script

INCIDENT_DIR="$1"

if [ -z "$INCIDENT_DIR" ]; then
    echo "Usage: $0 <incident_directory>"
    exit 1
fi

echo "=== POST-INCIDENT ANALYSIS ==="

# Analyze authentication failures
echo "1. Authentication Failures:"
grep "AUTH_FAILED" $INCIDENT_DIR/security.log | head -10

# Analyze suspicious activities
echo -e "\n2. Suspicious Activities:"
grep "SUSPICIOUS_ACTIVITY" $INCIDENT_DIR/security.log

# Analyze network connections
echo -e "\n3. Network Analysis:"
grep -E "(403|401|429)" $INCIDENT_DIR/bella_access.log | awk '{print $1}' | sort | uniq -c | sort -nr | head -10

# Check for malicious payloads
echo -e "\n4. Potential Malicious Requests:"
grep -E "(script|union|select|drop|insert)" $INCIDENT_DIR/bella_access.log

echo -e "\n=== ANALYSIS COMPLETE ==="
```

### Recovery Procedures

#### System Recovery
```bash
#!/bin/bash
# System recovery after security incident

echo "=== SYSTEM RECOVERY ==="

# 1. Verify system integrity
echo "Checking system integrity..."
debsums -c 2>/dev/null | head -10

# 2. Update all packages
echo "Updating system packages..."
apt update && apt upgrade -y

# 3. Regenerate all secrets
echo "Regenerating secrets..."
NEW_API_KEY=$(openssl rand -hex 32)
NEW_DB_PASSWORD=$(openssl rand -base64 32)

echo "New API Key: $NEW_API_KEY"
echo "New DB Password: $NEW_DB_PASSWORD"

# 4. Update configurations
echo "Update production.env with new credentials"
echo "Update database password"
echo "Restart all services"

# 5. Verify security settings
echo "Verifying security settings..."
ufw status
systemctl status fail2ban

echo "=== RECOVERY CHECKLIST ==="
echo "[ ] Credentials rotated"
echo "[ ] Configuration updated"
echo "[ ] Services restarted"
echo "[ ] Monitoring verified"
echo "[ ] Access logs reviewed"
echo "[ ] Team notified"
```

---

## 📞 Emergency Contacts

### Security Team
```
Primary Security Contact: [Your security team]
Emergency Security Hotline: [24/7 security number]
Infrastructure Team: [Infrastructure contact]
Database Administrator: [DBA contact]
```

### Vendor Security Contacts
```
OpenAI Security: security@openai.com
Twilio Security: security@twilio.com
AWS Security: aws-security@amazon.com
```

---

## 📚 Security Resources

### Security Documentation
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CIS Controls](https://www.cisecurity.org/controls/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)

### Security Tools
- **Vulnerability Scanning**: `sudo apt install nmap nikto`
- **Log Analysis**: `sudo apt install logwatch`
- **Network Monitoring**: `sudo apt install tcpdump wireshark-cli`

### Regular Security Tasks
- **Daily**: Review security logs, check failed authentications
- **Weekly**: Update packages, review firewall logs
- **Monthly**: Rotate API keys, security audit, penetration testing
- **Quarterly**: Full security assessment, update incident response procedures

---

**🔒 Security is Everyone's Responsibility**

This security guide provides comprehensive protection for Bella V3 in production. Regular review and updates of security measures are essential to maintain protection against evolving threats.

*Last Updated: 2025-09-30*
*Next Security Review: 2025-12-30*
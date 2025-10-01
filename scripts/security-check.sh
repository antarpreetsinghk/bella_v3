#!/bin/bash
# Pre-commit security validation script
# Prevents committing sensitive files and data

set -e

echo "🔒 Running security validation checks..."

# Check for hardcoded production URLs
if git diff --cached --name-only | xargs grep -l "bella-alb-.*\.amazonaws\.com" 2>/dev/null; then
    echo "❌ SECURITY VIOLATION: Production AWS URLs found in staged files!"
    echo "   Production URLs must be stored in environment variables."
    exit 1
fi

# Check for hardcoded cluster names
if git diff --cached --name-only | xargs grep -l "bella-prod-" 2>/dev/null; then
    echo "❌ SECURITY VIOLATION: Production cluster names found in staged files!"
    echo "   Use environment variables for cluster/service names."
    exit 1
fi

# Check for secret patterns
SECRET_PATTERNS=(
    "sk-[a-zA-Z0-9]{32,}"           # OpenAI API keys
    "AC[a-z0-9]{32}"                # Twilio Account SID
    "[a-f0-9]{32}"                  # 32-char hex tokens
    "AKIA[A-Z0-9]{16}"              # AWS Access Keys
    "password.*=.*[^\"']"            # Hardcoded passwords
    "secret.*=.*[^\"']"             # Hardcoded secrets
)

for pattern in "${SECRET_PATTERNS[@]}"; do
    if git diff --cached | grep -E "$pattern" >/dev/null 2>&1; then
        echo "❌ SECURITY VIOLATION: Potential secret found!"
        echo "   Pattern: $pattern"
        echo "   Secrets must be stored in environment variables."
        exit 1
    fi
done

# Check for files that should never be committed
FORBIDDEN_FILES=(
    "*.env"
    "production*.env"
    "*prod*.env"
    "aws*.env"
    "*.key"
    "*.pem"
    "*secret*"
    "*password*"
    "*credential*"
    "*.db"
    "*.sqlite*"
    "*backup*"
    "*.sql"
    "*.dump"
)

for pattern in "${FORBIDDEN_FILES[@]}"; do
    if git diff --cached --name-only | grep -E "$pattern" >/dev/null 2>&1; then
        echo "❌ SECURITY VIOLATION: Forbidden file type detected!"
        echo "   Pattern: $pattern"
        echo "   These files should be in .gitignore."
        exit 1
    fi
done

echo "✅ Security validation passed!"
echo "🔐 Safe to commit - no sensitive data detected."
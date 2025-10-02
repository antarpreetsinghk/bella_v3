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

# Check for hardcoded cluster names (skip this script itself)
if git diff --cached --name-only | grep -v "security-check.sh" | xargs grep -l "bella-prod-" 2>/dev/null; then
    echo "❌ SECURITY VIOLATION: Production cluster names found in staged files!"
    echo "   Use environment variables for cluster/service names."
    exit 1
fi

# Check for secret patterns (skip .example files)
SECRET_PATTERNS=(
    "sk-[a-zA-Z0-9]{40,}"           # Real OpenAI API keys (longer)
    "AC[a-f0-9]{32}"                # Real Twilio Account SID
    "AKIA[A-Z0-9]{16}"              # AWS Access Keys
    "BEGIN PRIVATE KEY"             # Private keys
    "BEGIN RSA PRIVATE KEY"         # RSA Private keys
)

for pattern in "${SECRET_PATTERNS[@]}"; do
    if git diff --cached --name-only | grep -v "\.example$" | xargs git diff --cached | grep -E "$pattern" >/dev/null 2>&1; then
        echo "❌ SECURITY VIOLATION: Potential real secret found!"
        echo "   Pattern: $pattern"
        echo "   Real secrets must not be committed."
        exit 1
    fi
done

# Check for files that should never be committed (exclude .example files)
FORBIDDEN_PATTERNS=(
    "^\.env$"                    # .env file (not .env.example)
    "production.*\.env$"         # production.env files
    ".*prod.*\.env$"            # prod.env files
    "aws.*\.env$"               # aws.env files
    ".*\.key$"                  # Key files
    ".*\.pem$"                  # Certificate files
    ".*secret.*"                # Secret files (not in filenames)
    ".*password.*"              # Password files
    ".*credential.*"            # Credential files
    ".*\.db$"                   # Database files
    ".*\.sqlite.*$"             # SQLite files
    ".*backup.*"                # Backup files
    ".*\.sql$"                  # SQL dump files
    ".*\.dump$"                 # Dump files
)

staged_files=$(git diff --cached --name-only)
for file in $staged_files; do
    # Skip .example files
    if [[ "$file" == *.example ]]; then
        continue
    fi

    for pattern in "${FORBIDDEN_PATTERNS[@]}"; do
        if [[ "$file" =~ $pattern ]]; then
            echo "❌ SECURITY VIOLATION: Forbidden file detected!"
            echo "   File: $file"
            echo "   Pattern: $pattern"
            echo "   This file should be in .gitignore."
            exit 1
        fi
    done
done

echo "✅ Security validation passed!"
echo "🔐 Safe to commit - no sensitive data detected."
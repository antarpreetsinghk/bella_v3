#!/bin/bash
#
# Setup SSH Key Authentication for Production Server
# This script helps configure SSH key-based authentication to 15.157.56.64
#
# Usage:
#   ./scripts/setup_production_ssh.sh
#

set -e

# Configuration
PRODUCTION_HOST="15.157.56.64"
SSH_KEY_PATH="$HOME/.ssh/bella-voice-app"
SSH_PUB_KEY_PATH="$HOME/.ssh/bella-voice-app.pub"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Production SSH Key Setup${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Step 1: Check if SSH key exists
echo -e "${CYAN}[Step 1/4] Checking for SSH key...${NC}"
if [ -f "$SSH_KEY_PATH" ] && [ -f "$SSH_PUB_KEY_PATH" ]; then
    echo -e "${GREEN}✅ SSH key pair found${NC}"
    echo -e "   Private key: $SSH_KEY_PATH"
    echo -e "   Public key:  $SSH_PUB_KEY_PATH"
else
    echo -e "${RED}❌ SSH key not found${NC}"
    echo -e "${YELLOW}Generating new SSH key...${NC}"
    ssh-keygen -t rsa -b 4096 -f "$SSH_KEY_PATH" -C "bella-production-access" -N ""
    echo -e "${GREEN}✅ SSH key generated${NC}"
fi
echo ""

# Step 2: Display public key
echo -e "${CYAN}[Step 2/4] Your SSH Public Key:${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
cat "$SSH_PUB_KEY_PATH"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Step 3: Instructions to add key to production server
echo -e "${CYAN}[Step 3/4] Add this key to production server${NC}"
echo ""
echo -e "${YELLOW}Option A: Manual Copy (if you have password access)${NC}"
echo -e "1. Copy the public key above to your clipboard"
echo -e "2. SSH into production with password:"
echo -e "   ${BLUE}ssh <your-user>@$PRODUCTION_HOST${NC}"
echo -e "3. Create .ssh directory (if it doesn't exist):"
echo -e "   ${BLUE}mkdir -p ~/.ssh && chmod 700 ~/.ssh${NC}"
echo -e "4. Add the public key to authorized_keys:"
echo -e "   ${BLUE}echo '<paste-public-key-here>' >> ~/.ssh/authorized_keys${NC}"
echo -e "   ${BLUE}chmod 600 ~/.ssh/authorized_keys${NC}"
echo ""

echo -e "${YELLOW}Option B: Using ssh-copy-id (recommended if available)${NC}"
echo -e "1. Run this command (you'll need the password):"
echo -e "   ${BLUE}ssh-copy-id -i $SSH_PUB_KEY_PATH <your-user>@$PRODUCTION_HOST${NC}"
echo ""

echo -e "${YELLOW}Option C: Copy to clipboard for easy pasting${NC}"
echo -e "   ${BLUE}cat $SSH_PUB_KEY_PATH | xclip -selection clipboard${NC}  (if xclip is installed)"
echo -e "   ${BLUE}cat $SSH_PUB_KEY_PATH | wl-copy${NC}                    (if wl-clipboard is installed)"
echo ""

# Step 4: Test connection instructions
echo -e "${CYAN}[Step 4/4] After adding the key, test the connection:${NC}"
echo ""
echo -e "Test basic SSH access:"
echo -e "   ${BLUE}ssh -i $SSH_KEY_PATH <your-user>@$PRODUCTION_HOST \"echo 'SSH key authentication successful!'\"${NC}"
echo ""
echo -e "Test database access via SSH tunnel:"
echo -e "   ${BLUE}ssh -i $SSH_KEY_PATH -L 15432:localhost:5432 <your-user>@$PRODUCTION_HOST -N -f${NC}"
echo -e "   ${BLUE}export PRODUCTION_DB_URL=\"postgresql+asyncpg://bella_user:BellaPassword123@localhost:15432/bella_db\"${NC}"
echo -e "   ${BLUE}python scripts/verify_production_calendar.py${NC}"
echo ""

# Offer to configure SSH config
echo -e "${CYAN}[Optional] Configure SSH config for easier access?${NC}"
echo -e "Would you like to add production server to ~/.ssh/config? (y/N)"
read -r response

if [[ "$response" =~ ^[Yy]$ ]]; then
    echo ""
    echo -e "${YELLOW}What username do you use on the production server?${NC}"
    read -r username

    # Add to SSH config
    if ! grep -q "Host bella-production" ~/.ssh/config 2>/dev/null; then
        cat >> ~/.ssh/config <<EOF

# Bella Voice Production Server
Host bella-production
    HostName $PRODUCTION_HOST
    User $username
    IdentityFile $SSH_KEY_PATH
    ForwardAgent yes
    ServerAliveInterval 60
    ServerAliveCountMax 3
EOF
        echo -e "${GREEN}✅ Added to ~/.ssh/config${NC}"
        echo ""
        echo -e "${CYAN}You can now use: ${BLUE}ssh bella-production${NC}"
        echo -e "${CYAN}Port forwarding: ${BLUE}ssh -L 15432:localhost:5432 bella-production -N -f${NC}"
    else
        echo -e "${YELLOW}⚠️  Entry already exists in ~/.ssh/config${NC}"
    fi
fi

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✅ Setup guide complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${CYAN}Next steps:${NC}"
echo -e "1. Add the public key to production server"
echo -e "2. Test SSH connection"
echo -e "3. Run: ${BLUE}python scripts/verify_production_calendar.py${NC}"
echo ""

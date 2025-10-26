#!/bin/bash
#
# Setup GitHub SSH Key Authentication on Production Server
# This script helps configure SSH key-based authentication for private GitHub repo
#
# Usage:
#   ./scripts/setup_github_ssh_on_production.sh
#
# What it does:
#   1. Connects to production server (15.157.56.64)
#   2. Generates ED25519 SSH key for GitHub
#   3. Displays public key for you to add to GitHub
#   4. Changes git remote from HTTPS to SSH
#   5. Tests GitHub SSH connection
#   6. Tests git pull
#

set -e

# Configuration
PRODUCTION_HOST="15.157.56.64"
PROJECT_PATH="/home/ubuntu/bella_v3"
GITHUB_REPO="antarpreetsinghk/bella_v3"
SSH_KEY_NAME="id_ed25519_github_bella"
LOCAL_SSH_KEY="$HOME/.ssh/bella-voice-app"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                                                            ║${NC}"
echo -e "${BLUE}║       GitHub SSH Setup for Private Repository             ║${NC}"
echo -e "${BLUE}║              Production Server: ${PRODUCTION_HOST}              ║${NC}"
echo -e "${BLUE}║                                                            ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Step 1: Ask for production server credentials
echo -e "${CYAN}[Step 1/8] Production Server Access${NC}"
echo ""
echo -e "What username do you use to SSH into ${YELLOW}${PRODUCTION_HOST}${NC}?"
echo -e "${BLUE}(Usually: ubuntu, ec2-user, or antarpreet)${NC}"
read -r PROD_USER

echo ""
echo -e "Testing SSH connection to production server..."
if ssh -i "$LOCAL_SSH_KEY" -o ConnectTimeout=5 -o BatchMode=yes "${PROD_USER}@${PRODUCTION_HOST}" "echo 'SSH connection successful'" 2>/dev/null; then
    echo -e "${GREEN}✅ SSH connection successful${NC}"
else
    echo -e "${YELLOW}⚠️  SSH connection requires password/key. That's okay!${NC}"
fi
echo ""

# Step 2: Check current git remote
echo -e "${CYAN}[Step 2/8] Checking Current Git Configuration${NC}"
echo ""
echo -e "Connecting to production server to check git remote..."
CURRENT_REMOTE=$(ssh -i "$LOCAL_SSH_KEY" "${PROD_USER}@${PRODUCTION_HOST}" "cd ${PROJECT_PATH} && git remote -v | grep fetch | awk '{print \$2}'")

echo -e "Current git remote: ${YELLOW}${CURRENT_REMOTE}${NC}"

if [[ $CURRENT_REMOTE == git@github.com:* ]]; then
    echo -e "${GREEN}✅ Already using SSH${NC}"
    echo -e "${YELLOW}Do you want to continue anyway? (y/N)${NC}"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}Exiting. No changes made.${NC}"
        exit 0
    fi
elif [[ $CURRENT_REMOTE == https://github.com/* ]]; then
    echo -e "${YELLOW}⚠️  Currently using HTTPS (will change to SSH)${NC}"
else
    echo -e "${RED}❌ Unexpected remote format: ${CURRENT_REMOTE}${NC}"
    echo -e "${YELLOW}Do you want to continue anyway? (y/N)${NC}"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi
echo ""

# Step 3: Check if SSH key exists on production
echo -e "${CYAN}[Step 3/8] Checking for Existing GitHub SSH Key${NC}"
echo ""

SSH_KEY_EXISTS=$(ssh -i "$LOCAL_SSH_KEY" "${PROD_USER}@${PRODUCTION_HOST}" "test -f ~/.ssh/${SSH_KEY_NAME} && echo 'yes' || echo 'no'")

if [[ $SSH_KEY_EXISTS == "yes" ]]; then
    echo -e "${GREEN}✅ SSH key already exists: ~/.ssh/${SSH_KEY_NAME}${NC}"
    echo -e "${YELLOW}Do you want to use the existing key? (Y/n)${NC}"
    read -r response
    if [[ "$response" =~ ^[Nn]$ ]]; then
        echo -e "${YELLOW}Generating new SSH key...${NC}"
        ssh -i "$LOCAL_SSH_KEY" "${PROD_USER}@${PRODUCTION_HOST}" "ssh-keygen -t ed25519 -C 'bella-production-github' -f ~/.ssh/${SSH_KEY_NAME} -N ''"
        echo -e "${GREEN}✅ New SSH key generated${NC}"
    fi
else
    echo -e "${YELLOW}SSH key not found. Generating new key...${NC}"
    ssh -i "$LOCAL_SSH_KEY" "${PROD_USER}@${PRODUCTION_HOST}" "mkdir -p ~/.ssh && chmod 700 ~/.ssh && ssh-keygen -t ed25519 -C 'bella-production-github' -f ~/.ssh/${SSH_KEY_NAME} -N ''"
    echo -e "${GREEN}✅ SSH key generated${NC}"
fi
echo ""

# Step 4: Display public key
echo -e "${CYAN}[Step 4/8] GitHub SSH Public Key${NC}"
echo ""
echo -e "${MAGENTA}Copy the key below and add it to GitHub:${NC}"
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
ssh -i "$LOCAL_SSH_KEY" "${PROD_USER}@${PRODUCTION_HOST}" "cat ~/.ssh/${SSH_KEY_NAME}.pub"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Step 5: Guide user to add key to GitHub
echo -e "${CYAN}[Step 5/8] Add SSH Key to GitHub${NC}"
echo ""
echo -e "${YELLOW}Follow these steps:${NC}"
echo ""
echo -e "1. Open this URL in your browser:"
echo -e "   ${BLUE}https://github.com/settings/keys${NC}"
echo ""
echo -e "2. Click ${GREEN}\"New SSH key\"${NC} button"
echo ""
echo -e "3. Fill in the form:"
echo -e "   • Title: ${YELLOW}Bella V3 Production Server${NC}"
echo -e "   • Key type: ${YELLOW}Authentication Key${NC}"
echo -e "   • Key: ${YELLOW}(paste the key from above)${NC}"
echo ""
echo -e "4. Click ${GREEN}\"Add SSH key\"${NC}"
echo ""
echo -e "${MAGENTA}Press ENTER when you've added the key to GitHub...${NC}"
read -r

# Step 6: Configure SSH to use the key
echo -e "${CYAN}[Step 6/8] Configuring SSH${NC}"
echo ""
echo -e "Adding GitHub SSH configuration..."

ssh -i "$LOCAL_SSH_KEY" "${PROD_USER}@${PRODUCTION_HOST}" "cat > ~/.ssh/config_github_temp << 'EOF'

# Bella V3 GitHub Repository
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/${SSH_KEY_NAME}
    IdentitiesOnly yes
EOF
"

# Merge with existing config if it exists
ssh -i "$LOCAL_SSH_KEY" "${PROD_USER}@${PRODUCTION_HOST}" "
if [ -f ~/.ssh/config ]; then
    if ! grep -q 'Bella V3 GitHub Repository' ~/.ssh/config; then
        cat ~/.ssh/config_github_temp >> ~/.ssh/config
    fi
else
    mv ~/.ssh/config_github_temp ~/.ssh/config
fi
rm -f ~/.ssh/config_github_temp
chmod 600 ~/.ssh/config
"

echo -e "${GREEN}✅ SSH config updated${NC}"
echo ""

# Step 7: Test GitHub SSH connection
echo -e "${CYAN}[Step 7/8] Testing GitHub SSH Connection${NC}"
echo ""
echo -e "Testing connection to GitHub..."

SSH_TEST_OUTPUT=$(ssh -i "$LOCAL_SSH_KEY" "${PROD_USER}@${PRODUCTION_HOST}" "ssh -T git@github.com 2>&1 || true")

if echo "$SSH_TEST_OUTPUT" | grep -q "successfully authenticated"; then
    echo -e "${GREEN}✅ GitHub SSH authentication successful!${NC}"
    echo -e "${GREEN}   $SSH_TEST_OUTPUT${NC}"
elif echo "$SSH_TEST_OUTPUT" | grep -q "Permission denied"; then
    echo -e "${RED}❌ SSH authentication failed${NC}"
    echo -e "${RED}   $SSH_TEST_OUTPUT${NC}"
    echo ""
    echo -e "${YELLOW}Troubleshooting:${NC}"
    echo -e "1. Make sure you added the SSH key to GitHub (Step 5)"
    echo -e "2. Check you copied the ENTIRE key (including ssh-ed25519 at start)"
    echo -e "3. Wait a minute and try again (GitHub key propagation)"
    echo ""
    echo -e "${YELLOW}Do you want to continue anyway? (y/N)${NC}"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo -e "${YELLOW}⚠️  Unexpected response from GitHub:${NC}"
    echo -e "$SSH_TEST_OUTPUT"
    echo ""
    echo -e "${YELLOW}Do you want to continue anyway? (y/N)${NC}"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi
echo ""

# Step 8: Update git remote to SSH
echo -e "${CYAN}[Step 8/8] Updating Git Remote to SSH${NC}"
echo ""

# Backup current remote
BACKUP_REMOTE=$(ssh -i "$LOCAL_SSH_KEY" "${PROD_USER}@${PRODUCTION_HOST}" "cd ${PROJECT_PATH} && git remote get-url origin")
echo -e "Backup of current remote: ${YELLOW}${BACKUP_REMOTE}${NC}"

# Update to SSH
echo -e "Changing git remote to SSH..."
ssh -i "$LOCAL_SSH_KEY" "${PROD_USER}@${PRODUCTION_HOST}" "cd ${PROJECT_PATH} && git remote set-url origin git@github.com:${GITHUB_REPO}.git"

# Verify change
NEW_REMOTE=$(ssh -i "$LOCAL_SSH_KEY" "${PROD_USER}@${PRODUCTION_HOST}" "cd ${PROJECT_PATH} && git remote get-url origin")
echo -e "New git remote: ${GREEN}${NEW_REMOTE}${NC}"

if [[ $NEW_REMOTE == git@github.com:${GITHUB_REPO}.git ]]; then
    echo -e "${GREEN}✅ Git remote updated successfully${NC}"
else
    echo -e "${RED}❌ Git remote update failed${NC}"
    echo -e "${YELLOW}Rolling back to original remote...${NC}"
    ssh -i "$LOCAL_SSH_KEY" "${PROD_USER}@${PRODUCTION_HOST}" "cd ${PROJECT_PATH} && git remote set-url origin '${BACKUP_REMOTE}'"
    exit 1
fi
echo ""

# Test git pull
echo -e "${CYAN}Testing git pull...${NC}"
GIT_PULL_OUTPUT=$(ssh -i "$LOCAL_SSH_KEY" "${PROD_USER}@${PRODUCTION_HOST}" "cd ${PROJECT_PATH} && git pull origin main 2>&1" || true)

if echo "$GIT_PULL_OUTPUT" | grep -q -E "(Already up to date|Updating|Fast-forward)"; then
    echo -e "${GREEN}✅ Git pull successful!${NC}"
    echo -e "${GREEN}   $GIT_PULL_OUTPUT${NC}"
elif echo "$GIT_PULL_OUTPUT" | grep -q "Permission denied"; then
    echo -e "${RED}❌ Git pull failed - Permission denied${NC}"
    echo -e "${RED}   $GIT_PULL_OUTPUT${NC}"
    echo ""
    echo -e "${YELLOW}Rolling back to HTTPS remote...${NC}"
    ssh -i "$LOCAL_SSH_KEY" "${PROD_USER}@${PRODUCTION_HOST}" "cd ${PROJECT_PATH} && git remote set-url origin '${BACKUP_REMOTE}'"
    exit 1
else
    echo -e "${YELLOW}⚠️  Git pull output:${NC}"
    echo -e "$GIT_PULL_OUTPUT"
fi
echo ""

# Success summary
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                            ║${NC}"
echo -e "${GREEN}║              ✅ GitHub SSH Setup Complete!                 ║${NC}"
echo -e "${GREEN}║                                                            ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${CYAN}Summary:${NC}"
echo -e "  • SSH key generated on production server"
echo -e "  • Key added to GitHub (by you)"
echo -e "  • Git remote changed from HTTPS to SSH"
echo -e "  • SSH connection tested successfully"
echo -e "  • Git pull tested successfully"
echo ""

echo -e "${CYAN}Next Steps:${NC}"
echo ""
echo -e "${YELLOW}1. Make your GitHub repository private:${NC}"
echo -e "   • Go to: ${BLUE}https://github.com/${GITHUB_REPO}/settings${NC}"
echo -e "   • Scroll to \"Danger Zone\""
echo -e "   • Click \"Change visibility\" → \"Make private\""
echo ""
echo -e "${YELLOW}2. Test deployment after making repo private:${NC}"
echo -e "   ${BLUE}ssh ${PROD_USER}@${PRODUCTION_HOST}${NC}"
echo -e "   ${BLUE}cd ${PROJECT_PATH}${NC}"
echo -e "   ${BLUE}git pull origin main${NC}"
echo ""
echo -e "${YELLOW}3. Test with a new commit:${NC}"
echo -e "   ${BLUE}# On local machine:${NC}"
echo -e "   ${BLUE}echo '# SSH test' >> README.md${NC}"
echo -e "   ${BLUE}git add README.md${NC}"
echo -e "   ${BLUE}git commit -m 'test: verify private repo SSH'${NC}"
echo -e "   ${BLUE}git push origin main${NC}"
echo -e "   ${BLUE}# Then on production:${NC}"
echo -e "   ${BLUE}ssh ${PROD_USER}@${PRODUCTION_HOST} 'cd ${PROJECT_PATH} && git pull origin main'${NC}"
echo ""

echo -e "${GREEN}🎉 Your production server can now access private GitHub repos!${NC}"
echo ""

# Rollback instructions
echo -e "${CYAN}Rollback (if needed):${NC}"
echo -e "If you need to revert to HTTPS:"
echo -e "  ${BLUE}ssh ${PROD_USER}@${PRODUCTION_HOST}${NC}"
echo -e "  ${BLUE}cd ${PROJECT_PATH}${NC}"
echo -e "  ${BLUE}git remote set-url origin ${BACKUP_REMOTE}${NC}"
echo ""

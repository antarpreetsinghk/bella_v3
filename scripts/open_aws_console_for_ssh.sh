#!/bin/bash
#
# Open AWS Console for Manual SSH Key Addition
# Since automated methods failed, this guides you through manual process
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

clear

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                                                            ║${NC}"
echo -e "${BLUE}║        AWS Console SSH Setup (Manual Method)              ║${NC}"
echo -e "${BLUE}║        Instance: i-09ab71843c2b3aea9                       ║${NC}"
echo -e "${BLUE}║                                                            ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Show the key to copy
SSH_KEY=$(cat ~/.ssh/bella-voice-app.pub)

echo -e "${CYAN}STEP 1: Copy Your SSH Key${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo "$SSH_KEY"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}👆 Copy the entire line above (starts with 'ssh-rsa')${NC}"
echo ""

# Try to copy to clipboard
if command -v xclip &> /dev/null; then
    echo "$SSH_KEY" | xclip -selection clipboard
    echo -e "${GREEN}✅ Key copied to clipboard!${NC}"
elif command -v wl-copy &> /dev/null; then
    echo "$SSH_KEY" | wl-copy
    echo -e "${GREEN}✅ Key copied to clipboard!${NC}"
else
    echo -e "${YELLOW}⚠️  Clipboard tool not found. Please copy manually.${NC}"
fi

echo ""
echo -e "${CYAN}STEP 2: Opening AWS Console...${NC}"
echo ""

# Open browser
CONNECT_URL="https://ca-central-1.console.aws.amazon.com/ec2/home?region=ca-central-1#ConnectToInstance:instanceId=i-09ab71843c2b3aea9"

if xdg-open "$CONNECT_URL" 2>/dev/null; then
    echo -e "${GREEN}✅ Browser opened${NC}"
else
    echo -e "${YELLOW}Could not open browser automatically.${NC}"
    echo -e "Please open this URL: ${BLUE}${CONNECT_URL}${NC}"
fi

echo ""
echo -e "${CYAN}STEP 3: In the AWS Console Browser Window${NC}"
echo ""
echo -e "1. Click the orange ${GREEN}\"Connect\"${NC} button"
echo -e "2. Wait for browser terminal to open (~10 seconds)"
echo ""

echo -e "${CYAN}STEP 4: In the Browser Terminal, Run These Commands${NC}"
echo ""
echo -e "${YELLOW}First, check which user you are:${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}whoami${NC}"
echo -e "${GREEN}ls -la /home${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -e "${YELLOW}Then, add the SSH key (choose based on your user):${NC}"
echo ""

echo -e "${CYAN}Option A: If you're logged in as 'ubuntu':${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
cat << 'UBUNTU_COMMANDS'
mkdir -p ~/.ssh && chmod 700 ~/.ssh
echo 'PASTE_YOUR_KEY_HERE' >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys

# Also add for antarpreet user if it exists
sudo mkdir -p /home/antarpreet/.ssh
sudo bash -c "echo 'PASTE_YOUR_KEY_HERE' >> /home/antarpreet/.ssh/authorized_keys"
sudo chown -R antarpreet:antarpreet /home/antarpreet/.ssh
sudo chmod 700 /home/antarpreet/.ssh
sudo chmod 600 /home/antarpreet/.ssh/authorized_keys
UBUNTU_COMMANDS
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -e "${CYAN}Option B: If you're logged in as 'ec2-user' or other:${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
cat << 'OTHER_COMMANDS'
mkdir -p ~/.ssh && chmod 700 ~/.ssh
echo 'PASTE_YOUR_KEY_HERE' >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
OTHER_COMMANDS
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -e "${YELLOW}⚠️  Remember to replace 'PASTE_YOUR_KEY_HERE' with your actual key!${NC}"
echo ""

echo -e "${CYAN}STEP 5: Test SSH Connection${NC}"
echo ""
echo -e "After adding the key in AWS Console, come back here and press ENTER..."
read -r

echo ""
echo -e "${CYAN}Testing SSH connection...${NC}"
echo ""

# Test with different users
for USER in antarpreet ubuntu ec2-user; do
    echo -e "Trying ${YELLOW}$USER${NC}@15.157.56.64..."
    if ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no $USER@15.157.56.64 "echo '✅ SSH Connection Successful!'; echo ''; echo 'Server Info:'; whoami; hostname; uname -a" 2>/dev/null; then
        echo ""
        echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${GREEN}║                                                            ║${NC}"
        echo -e "${GREEN}║              ✅ SSH ACCESS WORKING!                        ║${NC}"
        echo -e "${GREEN}║                                                            ║${NC}"
        echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
        echo ""
        echo -e "${CYAN}Working credentials:${NC}"
        echo -e "  User: ${GREEN}$USER${NC}"
        echo -e "  Host: ${GREEN}15.157.56.64${NC}"
        echo -e "  Command: ${BLUE}ssh $USER@15.157.56.64${NC}"
        echo ""
        echo -e "${CYAN}Next steps:${NC}"
        echo -e "1. Test: ${BLUE}ssh $USER@15.157.56.64${NC}"
        echo -e "2. Run GitHub SSH setup: ${BLUE}./scripts/setup_github_ssh_on_production.sh${NC}"
        echo -e "3. Make repo private on GitHub"
        echo ""
        exit 0
    fi
done

echo ""
echo -e "${RED}❌ SSH still not working${NC}"
echo ""
echo -e "${YELLOW}Troubleshooting:${NC}"
echo -e "1. Make sure you copied the ENTIRE SSH key"
echo -e "2. Check you're adding key to the correct user's .ssh/authorized_keys"
echo -e "3. Verify permissions: ~/.ssh = 700, authorized_keys = 600"
echo -e "4. Try again with correct commands above"
echo ""

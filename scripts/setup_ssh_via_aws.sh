#!/bin/bash
#
# Setup SSH Access to Production Server Using AWS CLI
# Since direct SSH is not working, this script uses AWS to add your SSH key
#
# Instance: i-09ab71843c2b3aea9 (15.157.56.64)
# Region: ca-central-1
#

set -e

# Configuration
INSTANCE_ID="i-09ab71843c2b3aea9"
REGION="ca-central-1"
SSH_PUBLIC_KEY_PATH="$HOME/.ssh/bella-voice-app.pub"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                                                            ║${NC}"
echo -e "${BLUE}║        Setup SSH Access via AWS CLI                       ║${NC}"
echo -e "${BLUE}║        Instance: ${INSTANCE_ID}                ║${NC}"
echo -e "${BLUE}║                                                            ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check AWS CLI
echo -e "${CYAN}[Step 1/5] Checking AWS CLI Access${NC}"
if ! aws sts get-caller-identity --region $REGION >/dev/null 2>&1; then
    echo -e "${RED}❌ AWS CLI not configured or no access${NC}"
    exit 1
fi

ACCOUNT=$(aws sts get-caller-identity --query 'Account' --output text --region $REGION)
echo -e "${GREEN}✅ AWS Access confirmed (Account: ${ACCOUNT})${NC}"
echo ""

# Check SSH key exists
echo -e "${CYAN}[Step 2/5] Checking SSH Public Key${NC}"
if [ ! -f "$SSH_PUBLIC_KEY_PATH" ]; then
    echo -e "${RED}❌ SSH public key not found: $SSH_PUBLIC_KEY_PATH${NC}"
    exit 1
fi

echo -e "${GREEN}✅ SSH public key found${NC}"
SSH_KEY=$(cat "$SSH_PUBLIC_KEY_PATH")
echo -e "${BLUE}Key fingerprint:${NC}"
ssh-keygen -lf "$SSH_PUBLIC_KEY_PATH"
echo ""

# Check instance
echo -e "${CYAN}[Step 3/5] Checking EC2 Instance${NC}"
INSTANCE_STATE=$(aws ec2 describe-instances \
    --instance-ids $INSTANCE_ID \
    --region $REGION \
    --query 'Reservations[0].Instances[0].State.Name' \
    --output text)

echo -e "Instance state: ${YELLOW}${INSTANCE_STATE}${NC}"

if [ "$INSTANCE_STATE" != "running" ] && [ "$INSTANCE_STATE" != "stopped" ]; then
    echo -e "${RED}❌ Instance in unexpected state: $INSTANCE_STATE${NC}"
    exit 1
fi
echo ""

# Show available methods
echo -e "${CYAN}[Step 4/5] Available Methods${NC}"
echo ""
echo -e "${YELLOW}Method 1: AWS Console (Manual - Recommended)${NC}"
echo -e "1. Go to AWS EC2 Console:"
echo -e "   ${BLUE}https://ca-central-1.console.aws.amazon.com/ec2/home?region=ca-central-1#Instances:instanceId=${INSTANCE_ID}${NC}"
echo -e "2. Select instance → Actions → Connect → EC2 Instance Connect"
echo -e "3. Click 'Connect' (opens browser terminal)"
echo -e "4. In browser terminal, run:"
echo -e "   ${BLUE}mkdir -p ~/.ssh && chmod 700 ~/.ssh${NC}"
echo -e "   ${BLUE}echo '$SSH_KEY' >> ~/.ssh/authorized_keys${NC}"
echo -e "   ${BLUE}chmod 600 ~/.ssh/authorized_keys${NC}"
echo -e "5. Try SSH: ${BLUE}ssh antarpreet@15.157.56.64${NC}"
echo ""

echo -e "${YELLOW}Method 2: Add via User Data (Requires stop/start)${NC}"
echo -e "This will:"
echo -e "  • Stop the instance (⚠️  causes downtime)"
echo -e "  • Add user data script to add SSH key on next boot"
echo -e "  • Start the instance"
echo -e "  • ${RED}WARNING: Production will be down for ~2-3 minutes${NC}"
echo ""

echo -e "${YELLOW}Method 3: EC2 Instance Connect (Temporary - 60 seconds)${NC}"
echo -e "This sends your SSH key temporarily (lasts 60 seconds)"
echo -e "You must SSH within 60 seconds of sending the key"
echo -e "  • No downtime"
echo -e "  • ${YELLOW}Must be quick${NC}"
echo ""

echo -e "${CYAN}Which method would you like to use?${NC}"
echo -e "  ${GREEN}1${NC}) AWS Console (manual, safe, recommended)"
echo -e "  ${YELLOW}2${NC}) User Data (automated, requires restart)"
echo -e "  ${BLUE}3${NC}) Instance Connect (temporary, must be quick)"
echo -e "  ${RED}q${NC}) Quit"
echo ""
read -p "Enter choice (1/2/3/q): " choice

case $choice in
    1)
        echo ""
        echo -e "${GREEN}Opening AWS Console...${NC}"
        echo ""
        echo -e "1. Opening URL in browser..."
        xdg-open "https://ca-central-1.console.aws.amazon.com/ec2/home?region=ca-central-1#ConnectToInstance:instanceId=${INSTANCE_ID}" 2>/dev/null || \
            echo -e "   Please open: ${BLUE}https://ca-central-1.console.aws.amazon.com/ec2/home?region=ca-central-1#ConnectToInstance:instanceId=${INSTANCE_ID}${NC}"
        echo ""
        echo -e "2. ${YELLOW}Your SSH public key (copy this):${NC}"
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        cat "$SSH_PUBLIC_KEY_PATH"
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
        echo -e "3. In the browser terminal, run these commands:"
        echo -e "   ${BLUE}# Check which user you are${NC}"
        echo -e "   ${BLUE}whoami${NC}"
        echo -e "   ${BLUE}ls -la /home${NC}"
        echo ""
        echo -e "   ${BLUE}# Add SSH key${NC}"
        echo -e "   ${BLUE}mkdir -p ~/.ssh && chmod 700 ~/.ssh${NC}"
        echo -e "   ${BLUE}echo 'PASTE_YOUR_KEY_HERE' >> ~/.ssh/authorized_keys${NC}"
        echo -e "   ${BLUE}chmod 600 ~/.ssh/authorized_keys${NC}"
        echo ""
        echo -e "   ${BLUE}# If you're 'ubuntu' but need key for 'antarpreet':${NC}"
        echo -e "   ${BLUE}sudo mkdir -p /home/antarpreet/.ssh${NC}"
        echo -e "   ${BLUE}sudo bash -c \"echo 'PASTE_KEY' >> /home/antarpreet/.ssh/authorized_keys\"${NC}"
        echo -e "   ${BLUE}sudo chown -R antarpreet:antarpreet /home/antarpreet/.ssh${NC}"
        echo -e "   ${BLUE}sudo chmod 700 /home/antarpreet/.ssh${NC}"
        echo -e "   ${BLUE}sudo chmod 600 /home/antarpreet/.ssh/authorized_keys${NC}"
        echo ""
        echo -e "${YELLOW}Press ENTER when done...${NC}"
        read
        ;;

    2)
        echo ""
        echo -e "${RED}⚠️  WARNING: This will stop and restart the instance${NC}"
        echo -e "${RED}Production will be down for ~2-3 minutes${NC}"
        echo ""
        read -p "Are you sure? (yes/no): " confirm
        if [ "$confirm" != "yes" ]; then
            echo -e "${YELLOW}Cancelled${NC}"
            exit 0
        fi

        echo ""
        echo -e "${CYAN}[Step 5/5] Stopping instance...${NC}"
        aws ec2 stop-instances --instance-ids $INSTANCE_ID --region $REGION

        echo -e "${YELLOW}Waiting for instance to stop...${NC}"
        aws ec2 wait instance-stopped --instance-ids $INSTANCE_ID --region $REGION
        echo -e "${GREEN}✅ Instance stopped${NC}"

        echo ""
        echo -e "${CYAN}Creating user data script...${NC}"
        USER_DATA=$(cat <<EOF
#!/bin/bash
# Add SSH key for antarpreet user
mkdir -p /home/antarpreet/.ssh
chmod 700 /home/antarpreet/.ssh
echo '$SSH_KEY' >> /home/antarpreet/.ssh/authorized_keys
chmod 600 /home/antarpreet/.ssh/authorized_keys
chown -R antarpreet:antarpreet /home/antarpreet/.ssh
EOF
)

        USER_DATA_BASE64=$(echo "$USER_DATA" | base64 -w 0)

        echo -e "${CYAN}Modifying instance user data...${NC}"
        aws ec2 modify-instance-attribute \
            --instance-id $INSTANCE_ID \
            --user-data "$USER_DATA_BASE64" \
            --region $REGION
        echo -e "${GREEN}✅ User data updated${NC}"

        echo ""
        echo -e "${CYAN}Starting instance...${NC}"
        aws ec2 start-instances --instance-ids $INSTANCE_ID --region $REGION

        echo -e "${YELLOW}Waiting for instance to start...${NC}"
        aws ec2 wait instance-running --instance-ids $INSTANCE_ID --region $REGION
        echo -e "${GREEN}✅ Instance started${NC}"

        echo ""
        echo -e "${YELLOW}Waiting 30 seconds for user data to execute...${NC}"
        sleep 30
        ;;

    3)
        echo ""
        echo -e "${CYAN}[Step 5/5] Sending SSH key via EC2 Instance Connect${NC}"
        echo ""

        # Try both users
        for USER in ubuntu antarpreet; do
            echo -e "${YELLOW}Trying user: $USER${NC}"

            if aws ec2-instance-connect send-ssh-public-key \
                --instance-id $INSTANCE_ID \
                --availability-zone ca-central-1a \
                --instance-os-user $USER \
                --ssh-public-key "file://$SSH_PUBLIC_KEY_PATH" \
                --region $REGION 2>/dev/null; then

                echo -e "${GREEN}✅ Key sent for user: $USER${NC}"
                echo -e "${YELLOW}⏰ You have 60 seconds to SSH!${NC}"
                echo ""
                echo -e "Quick! Run this now in another terminal:"
                echo -e "${BLUE}ssh $USER@15.157.56.64 \"mkdir -p ~/.ssh && chmod 700 ~/.ssh && echo '$SSH_KEY' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys\"${NC}"
                echo ""

                # Try to SSH and add key permanently
                echo -e "${YELLOW}Attempting to add key permanently...${NC}"
                if ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no $USER@15.157.56.64 \
                    "mkdir -p ~/.ssh && chmod 700 ~/.ssh && echo '$SSH_KEY' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys && echo 'SSH key added successfully!'" 2>/dev/null; then
                    echo -e "${GREEN}✅ SSH key added permanently!${NC}"
                    break
                else
                    echo -e "${RED}❌ Failed to connect within 60 seconds${NC}"
                fi
            else
                echo -e "${YELLOW}⚠️  User $USER not available${NC}"
            fi
        done
        ;;

    q|Q)
        echo -e "${YELLOW}Exiting${NC}"
        exit 0
        ;;

    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

# Test SSH
echo ""
echo -e "${CYAN}Testing SSH connection...${NC}"
if ssh -o ConnectTimeout=5 -o BatchMode=yes -o StrictHostKeyChecking=no antarpreet@15.157.56.64 "echo '✅ SSH works!'; whoami" 2>/dev/null; then
    echo -e "${GREEN}✅ SSH connection successful!${NC}"
else
    echo -e "${YELLOW}⚠️  Could not test SSH (might still work, try manually)${NC}"
    echo -e "Try: ${BLUE}ssh antarpreet@15.157.56.64${NC}"
fi

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                            ║${NC}"
echo -e "${GREEN}║              SSH Setup Complete!                          ║${NC}"
echo -e "${GREEN}║                                                            ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${CYAN}Next steps:${NC}"
echo -e "1. Test SSH: ${BLUE}ssh antarpreet@15.157.56.64${NC}"
echo -e "2. Run GitHub SSH setup: ${BLUE}./scripts/setup_github_ssh_on_production.sh${NC}"
echo ""

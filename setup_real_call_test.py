#!/usr/bin/env python3
"""
Complete setup for real Twilio call testing.
"""
import boto3
import json

def setup_test_mode():
    """Set APP_ENV=test to bypass signature validation temporarily."""
    print("🧪 Setting up test mode for call flow testing...")

    try:
        client = boto3.client('secretsmanager', region_name='ca-central-1')

        # Get current secrets
        response = client.get_secret_value(SecretId='bella-env')
        current_secrets = json.loads(response['SecretString'])

        # Add test mode
        current_secrets['APP_ENV'] = 'test'

        # Update secrets
        client.update_secret(
            SecretId='bella-env',
            SecretString=json.dumps(current_secrets)
        )

        print("✅ Test mode enabled!")
        print("⚠️  IMPORTANT: This bypasses security for testing only")
        print("📞 You can now test with any webhook simulator")
        print()
        print("🔄 Restart the ECS service to pick up the change:")
        print("   aws ecs update-service --cluster bella-prod-cluster --service bella-prod-service --force-new-deployment")

        return True

    except Exception as e:
        print(f"❌ Failed to set test mode: {e}")
        return False

def setup_production_twilio():
    """Set up production Twilio configuration."""
    print("📞 Setting up production Twilio configuration...")
    print()

    # Get Twilio credentials
    print("You'll need your Twilio credentials:")
    print("1. Go to https://console.twilio.com/")
    print("2. Find your Account SID and Auth Token")
    print("3. Get or buy a phone number")
    print()

    account_sid = input("Enter your Twilio Account SID (starts with AC): ").strip()
    auth_token = input("Enter your Twilio Auth Token: ").strip()
    phone_number = input("Enter your Twilio phone number (e.g., +15551234567): ").strip()

    if not account_sid.startswith("AC"):
        print("❌ Invalid Account SID format")
        return False

    if not phone_number.startswith("+"):
        print("❌ Invalid phone number format")
        return False

    try:
        client = boto3.client('secretsmanager', region_name='ca-central-1')

        # Get current secrets
        response = client.get_secret_value(SecretId='bella-env')
        current_secrets = json.loads(response['SecretString'])

        # Add Twilio config
        current_secrets['TWILIO_ACCOUNT_SID'] = account_sid
        current_secrets['TWILIO_AUTH_TOKEN'] = auth_token
        current_secrets['TWILIO_PHONE_NUMBER'] = phone_number
        current_secrets['APP_ENV'] = 'production'  # Remove test mode

        # Update secrets
        client.update_secret(
            SecretId='bella-env',
            SecretString=json.dumps(current_secrets)
        )

        print("✅ Twilio configuration saved!")
        print()
        print("📋 Next steps:")
        print("1. Restart ECS service:")
        print("   aws ecs update-service --cluster bella-prod-cluster --service bella-prod-service --force-new-deployment")
        print()
        print("2. Configure webhook in Twilio Console:")
        print(f"   Phone Number: {phone_number}")
        print("   Webhook URL: https://bella-alb-1924818779.ca-central-1.elb.amazonaws.com/twilio/voice")
        print("   HTTP Method: POST")
        print()
        print("3. Test by calling your Twilio number!")

        return True

    except Exception as e:
        print(f"❌ Failed to save Twilio config: {e}")
        return False

def show_current_config():
    """Show current configuration."""
    print("🔍 Current Configuration:")
    print("=" * 50)

    try:
        client = boto3.client('secretsmanager', region_name='ca-central-1')
        response = client.get_secret_value(SecretId='bella-env')
        secrets = json.loads(response['SecretString'])

        print(f"APP_ENV: {secrets.get('APP_ENV', 'Not set')}")
        print(f"TWILIO_ACCOUNT_SID: {secrets.get('TWILIO_ACCOUNT_SID', 'Not set')}")
        print(f"TWILIO_AUTH_TOKEN: {'***' if secrets.get('TWILIO_AUTH_TOKEN') else 'Not set'}")
        print(f"TWILIO_PHONE_NUMBER: {secrets.get('TWILIO_PHONE_NUMBER', 'Not set')}")
        print()

        # Check if ready for testing
        has_twilio = all([
            secrets.get('TWILIO_ACCOUNT_SID'),
            secrets.get('TWILIO_AUTH_TOKEN'),
            secrets.get('TWILIO_PHONE_NUMBER')
        ])

        if has_twilio:
            print("✅ Ready for production call testing!")
        elif secrets.get('APP_ENV') == 'test':
            print("🧪 Test mode enabled - ready for webhook simulation")
        else:
            print("⚠️  Not configured for call testing")

    except Exception as e:
        print(f"❌ Failed to check config: {e}")

if __name__ == "__main__":
    print("🚀 Bella V3 Real Call Testing Setup")
    print("=" * 50)

    show_current_config()

    print("\nChoose setup option:")
    print("1. Enable test mode (bypass security for testing)")
    print("2. Configure production Twilio (full setup)")
    print("3. Show current config only")

    choice = input("\nEnter choice (1-3): ").strip()

    if choice == "1":
        setup_test_mode()
    elif choice == "2":
        setup_production_twilio()
    elif choice == "3":
        show_current_config()
    else:
        print("❌ Invalid choice")
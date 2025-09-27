#!/usr/bin/env python3
"""
Add missing Twilio configuration to AWS Secrets Manager.
"""
import boto3
import json

def update_twilio_config():
    """Add missing Twilio account SID and phone number to secrets."""

    print("🔧 Updating Twilio configuration in AWS Secrets Manager...")

    # You need to provide these values
    TWILIO_ACCOUNT_SID = input("Enter your Twilio Account SID (starts with AC): ").strip()
    TWILIO_PHONE_NUMBER = input("Enter your Twilio phone number (e.g., +15551234567): ").strip()

    if not TWILIO_ACCOUNT_SID.startswith("AC"):
        print("❌ Invalid Account SID format. Should start with 'AC'")
        return False

    if not TWILIO_PHONE_NUMBER.startswith("+"):
        print("❌ Invalid phone number format. Should start with '+'")
        return False

    try:
        # Get current secrets
        client = boto3.client('secretsmanager', region_name='ca-central-1')

        response = client.get_secret_value(SecretId='bella-env')
        current_secrets = json.loads(response['SecretString'])

        # Add new Twilio config
        current_secrets['TWILIO_ACCOUNT_SID'] = TWILIO_ACCOUNT_SID
        current_secrets['TWILIO_PHONE_NUMBER'] = TWILIO_PHONE_NUMBER

        # Update secrets
        client.update_secret(
            SecretId='bella-env',
            SecretString=json.dumps(current_secrets)
        )

        print("✅ Twilio configuration updated successfully!")
        print(f"   Account SID: {TWILIO_ACCOUNT_SID}")
        print(f"   Phone Number: {TWILIO_PHONE_NUMBER}")
        print("\n🚀 Next steps:")
        print("   1. Redeploy the application to pick up new config")
        print("   2. Configure Twilio webhook URL")
        print("   3. Test with real phone call")

        return True

    except Exception as e:
        print(f"❌ Failed to update secrets: {e}")
        return False

def show_webhook_config():
    """Show webhook configuration instructions."""

    print("\n📞 Twilio Webhook Configuration:")
    print("=" * 50)
    print("1. Go to Twilio Console > Phone Numbers")
    print("2. Click on your phone number")
    print("3. Set webhook URL to:")
    print("   https://bella-alb-1924818779.ca-central-1.elb.amazonaws.com/twilio/voice")
    print("4. Set HTTP method to: POST")
    print("5. Save configuration")
    print("\n⚠️  Note: You'll need HTTPS for production Twilio webhooks")
    print("   Consider setting up SSL certificate for the ALB")

if __name__ == "__main__":
    print("🚀 Bella V3 Twilio Configuration Tool")
    print("=" * 50)

    if update_twilio_config():
        show_webhook_config()
    else:
        print("❌ Configuration update failed")
#!/usr/bin/env python3
"""
Script to share the service account calendar with a personal Google account.
This allows the personal account to see all booking events in their Google Calendar.
"""

import sys
from typing import Optional

# Add app to Python path
sys.path.append('/home/antarpreet/Projects/bella_v3')

from dotenv import load_dotenv
from app.services.google_calendar import get_calendar_service

# Load environment variables
load_dotenv()

def share_calendar_with_user(user_email: str, role: str = 'reader') -> bool:
    """
    Share the service account's primary calendar with a user's email address.

    Args:
        user_email: The email address to share the calendar with
        role: The access role ('reader', 'writer', 'owner')

    Returns:
        True if successful, False otherwise
    """
    service = get_calendar_service()
    if not service:
        print("❌ Could not connect to Google Calendar service")
        return False

    try:
        # Create the ACL rule
        rule = {
            'scope': {
                'type': 'user',
                'value': user_email,
            },
            'role': role
        }

        print(f"🔗 Sharing calendar with {user_email} as {role}...")

        # Add the ACL rule to the primary calendar
        created_rule = service.acl().insert(
            calendarId='primary',
            body=rule
        ).execute()

        print(f"✅ Calendar successfully shared!")
        print(f"   Rule ID: {created_rule.get('id')}")
        print(f"   User: {user_email}")
        print(f"   Role: {role}")

        return True

    except Exception as e:
        print(f"❌ Error sharing calendar: {e}")
        return False

def list_calendar_acl() -> None:
    """List current access control rules for the calendar"""
    service = get_calendar_service()
    if not service:
        print("❌ Could not connect to Google Calendar service")
        return

    try:
        print("\n📋 Current calendar access permissions:")

        acl = service.acl().list(calendarId='primary').execute()

        for rule in acl.get('items', []):
            scope = rule.get('scope', {})
            role = rule.get('role', 'unknown')
            scope_type = scope.get('type', 'unknown')
            scope_value = scope.get('value', 'unknown')

            print(f"   - {scope_value} ({scope_type}): {role}")

    except Exception as e:
        print(f"❌ Error listing calendar ACL: {e}")

def main():
    print("📅 Google Calendar Sharing Tool")
    print("=" * 40)

    # Show current permissions
    list_calendar_acl()

    # Use the provided email directly
    user_email = "antarpreetsinghk@gmail.com"

    print(f"\n🔗 Sharing calendar with: {user_email}")
    print("   After sharing, you'll see all booking events in your Google Calendar.")

    success = share_calendar_with_user(user_email, 'reader')
    if success:
        print("\n🎉 Success! The calendar has been shared.")
        print("\n📱 Next steps:")
        print("   1. Refresh your Google Calendar")
        print("   2. Look for 'bella-calendar@bella-voice-booking.iam.gserviceaccount.com'")
        print("      in your 'Other calendars' section")
        print("   3. You should now see all booking events at the correct times!")
    else:
        print("\n❌ Failed to share calendar. Please check the error messages above.")

if __name__ == "__main__":
    main()
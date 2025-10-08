#!/usr/bin/env python3
"""
Fix calendar sharing to ensure the shared calendar appears in user's Google Calendar.
"""

import sys
import os
import json

# Add app to Python path
sys.path.append('/home/antarpreet/Projects/bella_v3')

# Load production environment variables
with open('/home/antarpreet/Projects/bella_v3/lambda-env-update.json', 'r') as f:
    lambda_config = json.load(f)

for key, value in lambda_config["Variables"].items():
    os.environ[key] = value

from app.services.google_calendar import get_calendar_service

def fix_calendar_sharing():
    """Fix calendar sharing with proper permissions"""
    print("🔧 Fixing Calendar Sharing")
    print("=" * 40)

    service = get_calendar_service()
    if not service:
        print("❌ Could not connect to Google Calendar service")
        return False

    shared_calendar_id = "9eed74c0f7616d1f8e1182f478d78b673df9f1575acfd965f4925a3f5fd5b0e5@group.calendar.google.com"
    user_email = "antarpreetsinghk@gmail.com"

    try:
        # First, check current calendar sharing
        print(f"📋 Checking current sharing for calendar: {shared_calendar_id}")

        # Get current ACL (Access Control List)
        try:
            acl_list = service.acl().list(calendarId=shared_calendar_id).execute()
            print(f"📊 Current sharing rules: {len(acl_list.get('items', []))}")

            for rule in acl_list.get('items', []):
                scope = rule.get('scope', {})
                print(f"   - {scope.get('type', 'unknown')}: {scope.get('value', 'unknown')} ({rule.get('role', 'unknown')})")
        except Exception as e:
            print(f"⚠️  Could not check current ACL: {e}")

        # Add or update sharing rule for user
        print(f"\n🔗 Sharing calendar with: {user_email}")

        rule = {
            'scope': {
                'type': 'user',
                'value': user_email,
            },
            'role': 'reader'  # Can view events but not edit
        }

        try:
            # Try to insert the ACL rule
            created_rule = service.acl().insert(
                calendarId=shared_calendar_id,
                body=rule
            ).execute()

            print(f"✅ Successfully shared calendar with {user_email}")
            print(f"   Rule ID: {created_rule.get('id')}")
            print(f"   Role: {created_rule.get('role')}")

        except Exception as acl_error:
            # If the rule already exists, try to update it
            if "already exists" in str(acl_error).lower():
                print(f"⚠️  Sharing rule already exists, attempting to update...")
                try:
                    # Update the existing rule
                    updated_rule = service.acl().update(
                        calendarId=shared_calendar_id,
                        ruleId=f"user:{user_email}",
                        body=rule
                    ).execute()
                    print(f"✅ Updated sharing rule for {user_email}")
                except Exception as update_error:
                    print(f"❌ Could not update sharing rule: {update_error}")
                    return False
            else:
                print(f"❌ Could not create sharing rule: {acl_error}")
                return False

        # Provide manual subscription instructions
        print(f"\n📅 Manual Calendar Subscription Instructions:")
        print(f"   1. Open Google Calendar in your browser")
        print(f"   2. On the left sidebar, click the + next to 'Other calendars'")
        print(f"   3. Select 'Subscribe to calendar'")
        print(f"   4. Enter this calendar ID:")
        print(f"      {shared_calendar_id}")
        print(f"   5. Click 'Add calendar'")

        print(f"\n🔗 Alternative: Use this URL to subscribe:")
        calendar_url = f"https://calendar.google.com/calendar/u/0?cid={shared_calendar_id.replace('@', '%40')}"
        print(f"   {calendar_url}")

        # Check if calendar is now accessible to user
        print(f"\n🔍 Verifying calendar access...")
        try:
            calendar_info = service.calendars().get(calendarId=shared_calendar_id).execute()
            print(f"✅ Calendar accessible: {calendar_info.get('summary')}")
            print(f"   Timezone: {calendar_info.get('timeZone')}")
            print(f"   Description: {calendar_info.get('description', 'No description')}")
            return True
        except Exception as e:
            print(f"❌ Could not access calendar: {e}")
            return False

    except Exception as e:
        print(f"❌ Error fixing calendar sharing: {e}")
        return False

if __name__ == "__main__":
    success = fix_calendar_sharing()
    if success:
        print(f"\n🎉 Calendar sharing fix completed successfully!")
        print(f"   Your calendar should now show 'Bella Booking Calendar' in subscribed calendars")
    else:
        print(f"\n❌ Calendar sharing fix failed")
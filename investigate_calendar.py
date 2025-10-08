#!/usr/bin/env python3
"""
Script to investigate Google Calendar API options for sharing events.
"""

import sys
from typing import List, Dict, Any

# Add app to Python path
sys.path.append('/home/antarpreet/Projects/bella_v3')

from dotenv import load_dotenv
from app.services.google_calendar import get_calendar_service

# Load environment variables
load_dotenv()

def list_all_calendars(service):
    """List all calendars accessible to the service account"""
    try:
        print("📅 All accessible calendars:")
        calendar_list = service.calendarList().list().execute()

        for calendar in calendar_list.get('items', []):
            cal_id = calendar.get('id')
            summary = calendar.get('summary', 'No summary')
            access_role = calendar.get('accessRole', 'unknown')
            primary = calendar.get('primary', False)

            print(f"   - ID: {cal_id}")
            print(f"     Summary: {summary}")
            print(f"     Access Role: {access_role}")
            print(f"     Primary: {primary}")
            print()

        return calendar_list.get('items', [])

    except Exception as e:
        print(f"❌ Error listing calendars: {e}")
        return []

def create_shared_calendar(service, calendar_name: str):
    """Create a new calendar that can be shared"""
    try:
        print(f"📅 Creating new calendar: {calendar_name}")

        calendar = {
            'summary': calendar_name,
            'description': 'Shared calendar for Bella booking appointments',
            'timeZone': 'America/Edmonton'
        }

        created_calendar = service.calendars().insert(body=calendar).execute()
        calendar_id = created_calendar['id']

        print(f"✅ Created calendar with ID: {calendar_id}")

        # Now try to share this new calendar
        rule = {
            'scope': {
                'type': 'user',
                'value': 'antarpreetsinghk@gmail.com',
            },
            'role': 'reader'
        }

        print(f"🔗 Sharing new calendar with antarpreetsinghk@gmail.com...")

        created_rule = service.acl().insert(
            calendarId=calendar_id,
            body=rule
        ).execute()

        print(f"✅ Calendar successfully shared!")
        print(f"   Rule ID: {created_rule.get('id')}")
        print(f"   Calendar ID: {calendar_id}")

        return calendar_id

    except Exception as e:
        print(f"❌ Error creating/sharing calendar: {e}")
        return None

def try_public_calendar(service):
    """Try making the primary calendar public"""
    try:
        print("🌐 Attempting to make primary calendar public...")

        rule = {
            'scope': {
                'type': 'default'
            },
            'role': 'reader'
        }

        created_rule = service.acl().insert(
            calendarId='primary',
            body=rule
        ).execute()

        print(f"✅ Calendar made public!")
        print(f"   Rule ID: {created_rule.get('id')}")

        return True

    except Exception as e:
        print(f"❌ Error making calendar public: {e}")
        return False

def main():
    print("🔍 Google Calendar Investigation Tool")
    print("=" * 50)

    # Get Google Calendar service
    service = get_calendar_service()
    if not service:
        print("❌ Could not connect to Google Calendar service")
        return

    print("✅ Connected to Google Calendar")

    # List all available calendars
    calendars = list_all_calendars(service)

    # Try making primary calendar public first
    print("\n" + "="*50)
    if try_public_calendar(service):
        print("\n📱 The calendar is now public! You can add it by:")
        print("   1. Go to Google Calendar")
        print("   2. Click 'Add other calendars' (+)")
        print("   3. Select 'From URL'")
        print("   4. Add: https://calendar.google.com/calendar/ical/bella-calendar%40bella-voice-booking.iam.gserviceaccount.com/public/basic.ics")
    else:
        # If public sharing fails, try creating a new shared calendar
        print("\n" + "="*50)
        calendar_id = create_shared_calendar(service, "Bella Appointments - Shared")

        if calendar_id:
            print(f"\n📱 New shared calendar created! Calendar ID: {calendar_id}")
            print("   This calendar should now appear in your 'Other calendars' section")
            print("   We'll need to update the booking service to use this calendar ID")

if __name__ == "__main__":
    main()
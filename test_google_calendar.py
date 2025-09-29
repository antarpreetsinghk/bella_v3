#!/usr/bin/env python3
"""
Test script for Google Calendar integration.
Run this after setting up the service account credentials.
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Add app to Python path
sys.path.append('/home/antarpreet/Projects/bella_v3')

from app.services.google_calendar import (
    create_calendar_event,
    delete_calendar_event,
    check_calendar_availability,
    get_calendar_service
)

LOCAL_TZ = ZoneInfo("America/Edmonton")

async def test_google_calendar():
    """Test Google Calendar integration functions"""

    print("🔗 Testing Google Calendar Integration")
    print("=" * 50)

    # Test 1: Check if service is available
    print("\n1. Testing service initialization...")
    service = get_calendar_service()
    if service:
        print("✅ Google Calendar service initialized successfully")
    else:
        print("❌ Google Calendar service not available")
        if not os.getenv("GOOGLE_CALENDAR_ENABLED"):
            print("   💡 Set GOOGLE_CALENDAR_ENABLED=true to enable")
        if not os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON"):
            print("   💡 Set GOOGLE_SERVICE_ACCOUNT_JSON with service account credentials")
        return

    # Test 2: Check calendar availability
    print("\n2. Testing calendar availability check...")
    test_time = datetime.now(LOCAL_TZ) + timedelta(hours=1)
    test_time_utc = test_time.astimezone(ZoneInfo("UTC"))

    try:
        is_available = await check_calendar_availability(test_time_utc, 30)
        print(f"✅ Calendar availability check: {'Available' if is_available else 'Busy'}")
    except Exception as e:
        print(f"❌ Calendar availability check failed: {e}")
        return

    # Test 3: Create a test event
    print("\n3. Testing event creation...")
    try:
        test_event = await create_calendar_event(
            user_name="Test User",
            user_mobile="+1-416-555-0123",
            starts_at_utc=test_time_utc,
            duration_min=30,
            notes="Test appointment created by Bella Voice System"
        )

        if test_event:
            print(f"✅ Event created successfully: {test_event['event_id']}")
            print(f"   📅 Event link: {test_event.get('event_link', 'N/A')}")

            # Test 4: Delete the test event
            print("\n4. Testing event deletion...")
            deleted = await delete_calendar_event(test_event['event_id'])
            if deleted:
                print("✅ Event deleted successfully")
            else:
                print("❌ Failed to delete event")

        else:
            print("❌ Event creation returned None")

    except Exception as e:
        print(f"❌ Event creation failed: {e}")

    print("\n" + "=" * 50)
    print("🏁 Google Calendar integration test completed")

def print_setup_instructions():
    """Print setup instructions for Google Calendar integration"""
    print("""
📋 Google Calendar Setup Instructions:

1. Create a Google Cloud Project:
   - Go to https://console.cloud.google.com/
   - Create a new project or select existing one

2. Enable Google Calendar API:
   - Go to APIs & Services > Library
   - Search for "Google Calendar API" and enable it

3. Create Service Account:
   - Go to APIs & Services > Credentials
   - Click "Create Credentials" > "Service Account"
   - Fill in service account name and description
   - Grant "Editor" role or create custom role with calendar access

4. Generate Service Account Key:
   - Click on the created service account
   - Go to "Keys" tab
   - Click "Add Key" > "Create new key" > "JSON"
   - Download the JSON file

5. Set Environment Variables:
   export GOOGLE_CALENDAR_ENABLED=true
   export GOOGLE_SERVICE_ACCOUNT_JSON='{"type": "service_account", "project_id": "your-project", ...}'
   export GOOGLE_CALENDAR_ID=your-calendar-id  # Optional: defaults to "primary"
   export BUSINESS_EMAIL=your-business@email.com  # Optional: for attendees

6. Share Calendar with Service Account:
   - In Google Calendar, go to calendar settings
   - Share calendar with service account email (from JSON)
   - Grant "Make changes to events" permission

7. Test the Integration:
   python test_google_calendar.py
""")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--setup":
        print_setup_instructions()
    else:
        asyncio.run(test_google_calendar())
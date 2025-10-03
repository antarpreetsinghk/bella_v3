#!/usr/bin/env python3
"""
Test Google Calendar integration with proper .env loading
"""
import os
import sys
import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Add app to Python path
sys.path.append('/home/antarpreet/Projects/bella_v3')

from app.services.google_calendar import (
    create_calendar_event,
    delete_calendar_event,
    check_calendar_availability,
    get_calendar_service
)

LOCAL_TZ = ZoneInfo("America/Edmonton")

async def test_calendar_integration():
    """Test Google Calendar integration with proper environment loading"""

    print("🔗 Testing Google Calendar Integration (with .env)")
    print("=" * 55)

    # Check environment variables
    print("📋 Environment Configuration:")
    print(f"   GOOGLE_CALENDAR_ENABLED: {os.getenv('GOOGLE_CALENDAR_ENABLED')}")
    print(f"   BUSINESS_EMAIL: {os.getenv('BUSINESS_EMAIL')}")
    print(f"   GOOGLE_CALENDAR_ID: {os.getenv('GOOGLE_CALENDAR_ID')}")
    print(f"   GOOGLE_SERVICE_ACCOUNT_JSON: {'✅ Set' if os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON') else '❌ Not set'}")
    print()

    # Test 1: Service initialization
    print("1. Testing service initialization...")
    service = get_calendar_service()
    if service:
        print("✅ Google Calendar service initialized successfully")
    else:
        print("❌ Google Calendar service not available")
        print("   Check your environment variables and service account JSON")
        return

    # Test 2: Calendar availability check
    print("\n2. Testing calendar availability check...")
    tomorrow = datetime.now(LOCAL_TZ) + timedelta(days=1)
    tomorrow = tomorrow.replace(hour=14, minute=0, second=0, microsecond=0)
    tomorrow_utc = tomorrow.astimezone(ZoneInfo("UTC"))

    try:
        is_available = await check_calendar_availability(tomorrow_utc, 30)
        if is_available:
            print("✅ Calendar availability check: Available")
        else:
            print("❌ Calendar availability check: Conflicting appointment found")
    except Exception as e:
        print(f"❌ Calendar availability check failed: {e}")
        return

    # Test 3: Event creation
    print("\n3. Testing event creation...")
    try:
        event_result = await create_calendar_event(
            user_name="Test Patient",
            user_mobile="+1-416-555-1234",
            starts_at_utc=tomorrow_utc,
            duration_min=30,
            notes="Test appointment from Bella integration"
        )

        if event_result:
            event_id = event_result.get('event_id')
            event_link = event_result.get('event_link', '')
            print(f"✅ Event created successfully: {event_id}")
            print(f"   📅 Event link: {event_link}")

            # Test 4: Event deletion
            print("\n4. Testing event deletion...")
            if event_id:
                deleted = await delete_calendar_event(event_id)
                if deleted:
                    print("✅ Event deleted successfully")
                else:
                    print("❌ Event deletion failed")

        else:
            print("❌ Event creation returned None")

    except Exception as e:
        print(f"❌ Event creation failed: {e}")

    print("\n" + "=" * 55)
    print("🏁 Google Calendar integration test completed")

if __name__ == "__main__":
    asyncio.run(test_calendar_integration())
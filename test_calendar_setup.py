#!/usr/bin/env python3
"""
Quick test script to verify Google Calendar integration setup
"""
import os
import sys
import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Add the app directory to Python path
sys.path.insert(0, '/home/antarpreet/Projects/bella_v3')

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

async def test_calendar_setup():
    """Test Google Calendar integration setup"""
    print("🧪 Testing Google Calendar Integration Setup")
    print("=" * 50)

    # Check environment variables
    print("📋 Environment Configuration:")
    print(f"   GOOGLE_CALENDAR_ENABLED: {os.getenv('GOOGLE_CALENDAR_ENABLED')}")
    print(f"   GOOGLE_CALENDAR_ID: {os.getenv('GOOGLE_CALENDAR_ID')}")
    print(f"   BUSINESS_EMAIL: {os.getenv('BUSINESS_EMAIL')}")

    has_json = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
    print(f"   GOOGLE_SERVICE_ACCOUNT_JSON: {'✅ Present' if has_json else '❌ Missing'}")

    if has_json:
        print(f"   JSON Length: {len(has_json)} characters")
        print(f"   Service Account Email: {has_json.find('bella-calendar-secure@') != -1}")

    print("\n🔌 Testing Google Calendar Service Connection:")

    try:
        from app.services.google_calendar import get_calendar_service

        # Test service creation
        service = get_calendar_service()

        if service is None:
            print("❌ Failed to create Google Calendar service")
            return False

        print("✅ Google Calendar service created successfully")

        # Test calendar access
        print("\n📅 Testing Calendar Access:")
        try:
            calendar_id = os.getenv('GOOGLE_CALENDAR_ID', 'primary')

            # Try to get calendar info
            calendar_info = service.calendars().get(calendarId=calendar_id).execute()
            print(f"✅ Calendar access successful")
            print(f"   Calendar Name: {calendar_info.get('summary', 'Unknown')}")
            print(f"   Calendar ID: {calendar_info.get('id', 'Unknown')}")
            print(f"   Time Zone: {calendar_info.get('timeZone', 'Unknown')}")

        except Exception as e:
            print(f"❌ Calendar access failed: {str(e)}")
            return False

        # Test creating a test event
        print("\n📝 Testing Event Creation:")
        try:
            from app.services.google_calendar import create_calendar_event

            # Create a test appointment for tomorrow
            test_time = datetime.now(ZoneInfo("America/Edmonton")) + timedelta(days=1, hours=10)
            test_time_utc = test_time.astimezone(ZoneInfo("UTC"))

            result = await create_calendar_event(
                user_name="Test User",
                user_mobile="+14035551234",
                starts_at_utc=test_time_utc,
                duration_min=30,
                notes="Test appointment from calendar setup verification"
            )

            if result:
                print("✅ Test event created successfully")
                print(f"   Event ID: {result.get('id', 'Unknown')}")
                print(f"   Event Link: {result.get('htmlLink', 'Unknown')}")

                # Clean up test event
                try:
                    service.events().delete(
                        calendarId=calendar_id,
                        eventId=result['id']
                    ).execute()
                    print("✅ Test event cleaned up")
                except:
                    print("⚠️  Test event cleanup failed (event may remain)")

            else:
                print("❌ Test event creation failed")
                return False

        except Exception as e:
            print(f"❌ Event creation test failed: {str(e)}")
            return False

        print("\n🎉 Google Calendar Integration Test: SUCCESS")
        print("📋 Next Steps:")
        print("   1. Update GitHub Secrets with calendar credentials")
        print("   2. Deploy via GitHub Actions")
        print("   3. Test production voice booking with calendar")

        return True

    except Exception as e:
        print(f"❌ Calendar service test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_calendar_setup())
    sys.exit(0 if result else 1)
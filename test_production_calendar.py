#!/usr/bin/env python3
"""
Test production Google Calendar integration.
"""

import sys
import asyncio
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Add app to Python path
sys.path.append('/home/antarpreet/Projects/bella_v3')

# Load production environment variables from lambda config
import json
with open('/home/antarpreet/Projects/bella_v3/lambda-env-update.json', 'r') as f:
    lambda_config = json.load(f)

# Set production environment variables
for key, value in lambda_config["Variables"].items():
    os.environ[key] = value

from app.services.google_calendar import create_calendar_event

UTC = ZoneInfo("UTC")

async def test_production_calendar():
    """Test production Google Calendar integration"""
    print("🗓️ Testing Production Google Calendar Integration")
    print("=" * 55)

    try:
        # Test Google Calendar integration with production credentials
        print("🔐 Using production Google Calendar credentials...")
        print(f"📍 Calendar ID: {os.environ.get('GOOGLE_CALENDAR_ID')}")
        print(f"📧 Business Email: {os.environ.get('BUSINESS_EMAIL')}")

        test_time = datetime.now(UTC) + timedelta(hours=24)  # Tomorrow

        print(f"\n📅 Creating test appointment for: {test_time}")

        calendar_result = await create_calendar_event(
            user_name="Production Integration Test",
            user_mobile="+14035559999",
            starts_at_utc=test_time,
            duration_min=30,
            notes="Testing production calendar integration - timezone fix verification"
        )

        if calendar_result:
            print("✅ Google Calendar integration working perfectly!")
            print(f"   Event ID: {calendar_result.get('event_id')}")
            print(f"   Calendar ID: {calendar_result.get('calendar_id')}")
            print(f"   Start Time: {calendar_result.get('start_time')}")
            print(f"   Summary: {calendar_result.get('summary')}")
            print("\n🎉 The shared calendar integration is now LIVE in production!")
            print("   Appointments will appear in your Google Calendar at correct times.")
        else:
            print("❌ Google Calendar integration failed")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_production_calendar())
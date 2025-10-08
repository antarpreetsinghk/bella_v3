#!/usr/bin/env python3
"""
Test direct calendar event creation in the shared calendar.
"""

import sys
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

# Add app to Python path
sys.path.append('/home/antarpreet/Projects/bella_v3')

from dotenv import load_dotenv
from app.services.google_calendar import create_calendar_event

# Load environment variables
load_dotenv()

UTC = ZoneInfo("UTC")

async def test_direct_calendar():
    """Test creating an event directly in the shared calendar"""
    print("🧪 Testing Direct Calendar Event Creation")
    print("=" * 50)

    # Create a test appointment
    starts_at_utc = datetime(2025, 10, 8, 22, 0, 0, tzinfo=UTC)  # 4 PM Mountain Time

    print(f"Creating test event for: {starts_at_utc}")

    result = await create_calendar_event(
        user_name="Direct Test User",
        user_mobile="+14035551999",
        starts_at_utc=starts_at_utc,
        duration_min=30,
        notes="Direct calendar test - should appear in shared calendar"
    )

    if result:
        print("✅ Calendar event created successfully!")
        print(f"   Event ID: {result.get('event_id')}")
        print(f"   Calendar ID: {result.get('calendar_id')}")
        print(f"   Start Time: {result.get('start_time')}")
        print(f"   Summary: {result.get('summary')}")
    else:
        print("❌ Failed to create calendar event")

if __name__ == "__main__":
    asyncio.run(test_direct_calendar())
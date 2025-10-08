#!/usr/bin/env python3
"""
Test production database connectivity and Google Calendar integration.
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

from app.db.session import AsyncSessionLocal
from app.crud.appointment import list_appointments
from app.services.google_calendar import create_calendar_event
from sqlalchemy import text

UTC = ZoneInfo("UTC")

async def test_production_connection():
    """Test production database and calendar connectivity"""
    print("🔧 Testing Production Database & Calendar Connection")
    print("=" * 60)

    try:
        # Test database connection
        print("📊 Testing PostgreSQL connection...")
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT 1 as test"))
            test_value = result.scalar()
            print(f"✅ Database connection successful! Test query returned: {test_value}")

            # Check existing appointments
            appointments = await list_appointments(session)
            print(f"📅 Found {len(appointments)} existing appointments in production")

            for appt in appointments[:3]:  # Show first 3
                print(f"   - {appt.user_name} ({appt.user_mobile}) at {appt.starts_at}")

        # Test Google Calendar integration
        print("\n🗓️ Testing Google Calendar integration...")
        test_time = datetime.now(UTC) + timedelta(days=1)

        calendar_result = await create_calendar_event(
            user_name="Production Test User",
            user_mobile="+14035551000",
            starts_at_utc=test_time,
            duration_min=30,
            notes="Production integration test"
        )

        if calendar_result:
            print("✅ Google Calendar integration working!")
            print(f"   Event ID: {calendar_result.get('event_id')}")
            print(f"   Calendar ID: {calendar_result.get('calendar_id')}")
        else:
            print("❌ Google Calendar integration failed")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_production_connection())
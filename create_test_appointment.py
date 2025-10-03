#!/usr/bin/env python3
"""
Create a test appointment to verify Google Calendar integration
"""
import os
import sys
import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
load_dotenv()

sys.path.append('/home/antarpreet/Projects/bella_v3')
from app.services.google_calendar import create_calendar_event

LOCAL_TZ = ZoneInfo("America/Edmonton")

async def create_test_appointment():
    """Create a test appointment in Google Calendar"""

    print("🧪 Creating Test Appointment")
    print("=" * 40)

    # Create appointment for 1 hour from now
    now = datetime.now(LOCAL_TZ)
    appointment_time = now + timedelta(hours=1)
    appointment_time = appointment_time.replace(second=0, microsecond=0)
    appointment_utc = appointment_time.astimezone(ZoneInfo("UTC"))

    print(f"📅 Appointment Time: {appointment_time.strftime('%A, %B %d at %I:%M %p %Z')}")
    print(f"📧 Service Account: bella-calendar@bella-voice-booking.iam.gserviceaccount.com")
    print()

    try:
        result = await create_calendar_event(
            user_name="TEST PATIENT - Please Delete",
            user_mobile="+1-416-555-TEST",
            starts_at_utc=appointment_utc,
            duration_min=30,
            notes="This is a test appointment created by Bella. You can delete this event."
        )

        if result:
            event_id = result.get('event_id')
            event_link = result.get('event_link', '')

            print("✅ Test appointment created successfully!")
            print(f"📋 Event ID: {event_id}")
            print(f"🔗 Event Link: {event_link}")
            print()
            print("🔍 TO SEE THIS APPOINTMENT:")
            print("1. Go to https://calendar.google.com")
            print("2. Look for 'Other calendars' on the left")
            print("3. Click '+' next to 'Other calendars'")
            print("4. Select 'Subscribe to calendar'")
            print("5. Enter: bella-calendar@bella-voice-booking.iam.gserviceaccount.com")
            print("6. The appointment will appear in the 'bella-calendar' section!")
            print()
            print("❌ To delete this test appointment later:")
            print(f"   Event ID: {event_id}")

        else:
            print("❌ Failed to create test appointment")

    except Exception as e:
        print(f"❌ Error creating test appointment: {e}")

if __name__ == "__main__":
    asyncio.run(create_test_appointment())
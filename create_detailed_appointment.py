#!/usr/bin/env python3
"""
Create an appointment with enhanced visibility settings
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

async def create_detailed_appointment():
    """Create an appointment with full visibility"""

    print("✨ Creating Enhanced Visibility Appointment")
    print("=" * 50)

    # Create appointment for 30 minutes from now
    now = datetime.now(LOCAL_TZ)
    appointment_time = now + timedelta(minutes=30)
    appointment_time = appointment_time.replace(second=0, microsecond=0)
    appointment_utc = appointment_time.astimezone(ZoneInfo("UTC"))

    print(f"📅 Appointment Time: {appointment_time.strftime('%A, %B %d at %I:%M %p %Z')}")
    print("🔓 Visibility: PUBLIC (details should be visible)")
    print()

    try:
        result = await create_calendar_event(
            user_name="Sarah Johnson",
            user_mobile="+1-416-555-0123",
            starts_at_utc=appointment_utc,
            duration_min=30,
            notes="Dental cleaning appointment. Patient is a regular customer, prefers morning appointments."
        )

        if result:
            event_id = result.get('event_id')
            event_link = result.get('event_link', '')

            print("✅ Enhanced appointment created successfully!")
            print(f"📋 Event ID: {event_id}")
            print(f"🔗 Direct Link: {event_link}")
            print()
            print("👆 **Click the direct link above** to see full details")
            print()
            print("📅 Expected Details:")
            print("   • Patient: Sarah Johnson")
            print("   • Phone: +1-416-555-0123")
            print("   • Duration: 30 minutes")
            print("   • Notes: Dental cleaning appointment...")
            print()
            print("🔍 In Google Calendar:")
            print("   1. Refresh your Google Calendar")
            print("   2. Look in the 'bella-calendar' section")
            print("   3. Click on the appointment")
            print("   4. You should now see full details!")

        else:
            print("❌ Failed to create enhanced appointment")

    except Exception as e:
        print(f"❌ Error creating appointment: {e}")

if __name__ == "__main__":
    asyncio.run(create_detailed_appointment())
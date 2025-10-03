#!/usr/bin/env python3
"""
Create a very obvious appointment to help locate the right calendar
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

async def create_obvious_appointment():
    """Create an appointment that's easy to spot"""

    print("🎯 Creating OBVIOUS Appointment for Easy Detection")
    print("=" * 55)

    # Create appointment for 1 hour from now with obvious details
    now = datetime.now(LOCAL_TZ)
    appointment_time = now + timedelta(hours=1)
    appointment_time = appointment_time.replace(second=0, microsecond=0)
    appointment_utc = appointment_time.astimezone(ZoneInfo("UTC"))

    time_display = appointment_time.strftime('%I:%M %p')

    print(f"📅 Creating appointment at: {time_display} MDT")
    print("🔍 This will be VERY easy to spot in Google Calendar")
    print()

    try:
        result = await create_calendar_event(
            user_name="🎯 VOICE BOOKING TEST - LOOK FOR THIS",
            user_mobile="+1-999-VOICE-BOOKING",
            starts_at_utc=appointment_utc,
            duration_min=60,  # 1 hour to make it very visible
            notes="🔍 THIS IS FROM BELLA VOICE BOOKING SYSTEM! If you can see this appointment with these details, the integration is working perfectly!"
        )

        if result:
            event_id = result.get('event_id')
            print("✅ OBVIOUS appointment created!")
            print()
            print("🔍 NOW LOOK FOR THIS IN GOOGLE CALENDAR:")
            print(f"   📅 Time: {time_display} MDT (1 hour duration)")
            print("   👤 Patient: 🎯 VOICE BOOKING TEST - LOOK FOR THIS")
            print("   📞 Phone: +1-999-VOICE-BOOKING")
            print("   💬 Notes: Integration working perfectly!")
            print()
            print("📍 WHERE TO LOOK:")
            print("   1. Refresh Google Calendar")
            print("   2. Look for 'Other calendars' section")
            print("   3. Find 'bella-calendar@bella-voice-booking.iam.gserviceaccount.com'")
            print("   4. Look for the appointment with 🎯 emoji")
            print()
            print("❓ If you DON'T see this appointment:")
            print("   - The bella-calendar subscription might not be added yet")
            print("   - Try adding it again with the email above")

        else:
            print("❌ Failed to create obvious appointment")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(create_obvious_appointment())
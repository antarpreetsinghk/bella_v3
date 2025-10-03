#!/usr/bin/env python3
"""
Check what appointments exist in the calendar and their details
"""
import os
import sys
import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
load_dotenv()

sys.path.append('/home/antarpreet/Projects/bella_v3')
from app.services.google_calendar import get_calendar_service

LOCAL_TZ = ZoneInfo("America/Edmonton")
UTC = ZoneInfo("UTC")

async def check_appointments():
    """Check existing appointments in the calendar"""

    print("🔍 Checking Existing Appointments")
    print("=" * 45)

    service = get_calendar_service()
    if not service:
        print("❌ Google Calendar service not available")
        return

    try:
        # Get calendar ID from environment
        calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "primary")
        print(f"📅 Calendar ID: {calendar_id}")
        print(f"📧 Service Account: bella-calendar@bella-voice-booking.iam.gserviceaccount.com")
        print()

        # Get events from yesterday to tomorrow
        yesterday = datetime.now(UTC) - timedelta(days=1)
        tomorrow = datetime.now(UTC) + timedelta(days=2)

        print(f"🔍 Searching for events from {yesterday.strftime('%Y-%m-%d')} to {tomorrow.strftime('%Y-%m-%d')}")
        print()

        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=yesterday.isoformat(),
            timeMax=tomorrow.isoformat(),
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])

        if not events:
            print("📭 No appointments found in this date range")
        else:
            print(f"📋 Found {len(events)} appointment(s):")
            print("=" * 45)

            for i, event in enumerate(events, 1):
                event_id = event.get('id', 'No ID')
                summary = event.get('summary', 'No title')
                description = event.get('description', 'No description')

                # Get start time
                start = event.get('start', {})
                if 'dateTime' in start:
                    start_dt = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
                    local_time = start_dt.astimezone(LOCAL_TZ)
                    time_str = local_time.strftime('%A, %B %d at %I:%M %p %Z')
                else:
                    time_str = "All day event"

                print(f"📅 Appointment {i}:")
                print(f"   Title: {summary}")
                print(f"   Time: {time_str}")
                print(f"   ID: {event_id}")
                print(f"   Description: {description[:100]}{'...' if len(description) > 100 else ''}")

                # Check visibility settings
                visibility = event.get('visibility', 'default')
                print(f"   Visibility: {visibility}")

                # Check if there are attendees
                attendees = event.get('attendees', [])
                print(f"   Attendees: {len(attendees)}")

                print()

    except Exception as e:
        print(f"❌ Error checking appointments: {e}")

if __name__ == "__main__":
    asyncio.run(check_appointments())
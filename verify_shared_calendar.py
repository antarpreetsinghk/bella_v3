#!/usr/bin/env python3
"""
Script to verify events are being created in the shared calendar.
"""

import sys
from datetime import datetime, timedelta

# Add app to Python path
sys.path.append('/home/antarpreet/Projects/bella_v3')

from dotenv import load_dotenv
from app.services.google_calendar import get_calendar_service

# Load environment variables
load_dotenv()

def check_calendar_events():
    """Check recent events in the shared calendar"""
    service = get_calendar_service()
    if not service:
        print("❌ Could not connect to Google Calendar service")
        return

    # The shared calendar ID from our investigation
    shared_calendar_id = "9eed74c0f7616d1f8e1182f478d78b673df9f1575acfd965f4925a3f5fd5b0e5@group.calendar.google.com"

    try:
        # Get events from the last day and next day
        time_min = (datetime.utcnow() - timedelta(days=1)).isoformat() + 'Z'
        time_max = (datetime.utcnow() + timedelta(days=1)).isoformat() + 'Z'

        print(f"🔍 Checking events in shared calendar...")
        print(f"   Calendar ID: {shared_calendar_id}")
        print(f"   Time range: {time_min} to {time_max}")

        events_result = service.events().list(
            calendarId=shared_calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])

        if not events:
            print("📝 No events found in the shared calendar")
        else:
            print(f"📅 Found {len(events)} events in shared calendar:")
            for event in events:
                summary = event.get('summary', 'No title')
                start = event.get('start', {}).get('dateTime', 'No start time')
                print(f"   - {summary} at {start}")

        # Also check the primary calendar for comparison
        print(f"\n🔍 Checking events in primary calendar...")
        events_result_primary = service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events_primary = events_result_primary.get('items', [])

        if not events_primary:
            print("📝 No events found in the primary calendar")
        else:
            print(f"📅 Found {len(events_primary)} events in primary calendar:")
            for event in events_primary:
                summary = event.get('summary', 'No title')
                start = event.get('start', {}).get('dateTime', 'No start time')
                print(f"   - {summary} at {start}")

    except Exception as e:
        print(f"❌ Error checking calendar events: {e}")

if __name__ == "__main__":
    check_calendar_events()
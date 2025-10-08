#!/usr/bin/env python3
"""
Script to cleanup wrong 3am Google Calendar events.
This script finds and deletes all "Bella" events that appear at 3am times.
"""

import asyncio
import sys
from datetime import datetime, time
from typing import List, Dict, Any

# Add app to Python path
sys.path.append('/home/antarpreet/Projects/bella_v3')

from dotenv import load_dotenv
from app.services.google_calendar import get_calendar_service

# Load environment variables
load_dotenv()

def find_3am_bella_events(service) -> List[Dict[str, Any]]:
    """Find all 'Bella' events that occur at 3am (wrong timezone events)"""
    try:
        # Get events from the past month and next month
        from datetime import datetime, timedelta
        import dateutil.parser

        time_min = (datetime.utcnow() - timedelta(days=60)).isoformat() + 'Z'
        time_max = (datetime.utcnow() + timedelta(days=60)).isoformat() + 'Z'

        events_result = service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])
        wrong_events = []

        for event in events:
            summary = event.get('summary', '')
            start = event.get('start', {})

            # Check if this is a Bella event
            if 'bella' in summary.lower() or 'appointment with' in summary.lower():
                # Check if it's a datetime event (not all-day)
                if 'dateTime' in start:
                    # Parse the start time
                    start_dt = dateutil.parser.parse(start['dateTime'])

                    # Check if it's at 3am in any timezone (likely wrong)
                    # Look for events at 03:00, 09:00 UTC (3am Mountain), etc.
                    hour = start_dt.hour
                    if hour == 3 or hour == 9 or hour == 15 or hour == 21:  # Potential wrong timezone hours
                        wrong_events.append(event)
                        print(f"Found suspicious event: '{summary}' at {start_dt}")

        return wrong_events

    except Exception as e:
        print(f"Error finding events: {e}")
        return []

def delete_events(service, events: List[Dict[str, Any]]) -> int:
    """Delete the specified events"""
    deleted_count = 0

    for event in events:
        try:
            event_id = event['id']
            summary = event.get('summary', 'Unknown')
            start = event.get('start', {}).get('dateTime', 'Unknown time')

            print(f"Deleting: '{summary}' at {start}")

            service.events().delete(
                calendarId='primary',
                eventId=event_id
            ).execute()

            deleted_count += 1
            print(f"✅ Deleted event: {summary}")

        except Exception as e:
            print(f"❌ Failed to delete event '{summary}': {e}")

    return deleted_count

def main():
    print("🗑️ Google Calendar Cleanup - Removing Wrong 3am Events")
    print("=" * 60)

    # Get Google Calendar service
    service = get_calendar_service()
    if not service:
        print("❌ Could not connect to Google Calendar service")
        return

    print("✅ Connected to Google Calendar")

    # Find wrong events
    print("\n🔍 Searching for wrong 3am events...")
    wrong_events = find_3am_bella_events(service)

    if not wrong_events:
        print("✅ No wrong 3am events found!")
        return

    print(f"\n📋 Found {len(wrong_events)} potentially wrong events:")
    for i, event in enumerate(wrong_events, 1):
        summary = event.get('summary', 'Unknown')
        start = event.get('start', {}).get('dateTime', 'Unknown time')
        print(f"   {i}. {summary} at {start}")

    # Ask for confirmation
    print(f"\n⚠️  WARNING: This will delete {len(wrong_events)} events!")
    response = input("Do you want to proceed? (yes/no): ").lower().strip()

    if response in ('yes', 'y'):
        print("\n🗑️ Deleting events...")
        deleted_count = delete_events(service, wrong_events)
        print(f"\n✅ Successfully deleted {deleted_count} out of {len(wrong_events)} events")
    else:
        print("\n❌ Operation cancelled")

if __name__ == "__main__":
    main()
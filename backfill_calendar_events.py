#!/usr/bin/env python3
"""
Backfill Google Calendar events for existing appointments that don't have them
"""
import requests
import json

def backfill_calendar_events():
    """Create Google Calendar events for existing appointments without them"""
    print("🔄 Backfilling Google Calendar Events for Existing Appointments")
    print("=" * 65)

    base_url = "http://bella-alb-1924818779.ca-central-1.elb.amazonaws.com"

    # Get appointments without calendar events
    print("1️⃣ Fetching appointments without Google Calendar events...")

    try:
        response = requests.get(f"{base_url}/api/appointments/missing-calendar", timeout=30)
        if response.status_code == 200:
            appointments = response.json()
            print(f"   Found {len(appointments)} appointments without calendar events")
        else:
            print(f"   ⚠️  Could not fetch appointments: {response.status_code}")
            return
    except Exception as e:
        print(f"   ⚠️  Error fetching appointments: {e}")
        return

    if not appointments:
        print("   ✅ All appointments already have Google Calendar events!")
        return

    # Create calendar events for each appointment
    success_count = 0
    for i, appointment in enumerate(appointments, 1):
        print(f"\n{i}️⃣ Creating calendar event for appointment {appointment['id']}...")
        print(f"   Patient: {appointment['patient_name']}")
        print(f"   Time: {appointment['appointment_time']}")

        try:
            # Call the backfill endpoint
            backfill_response = requests.post(
                f"{base_url}/api/appointments/{appointment['id']}/create-calendar-event",
                timeout=30
            )

            if backfill_response.status_code == 200:
                result = backfill_response.json()
                print(f"   ✅ Calendar event created: {result.get('event_id', 'Unknown ID')}")
                success_count += 1
            else:
                print(f"   ❌ Failed to create calendar event: {backfill_response.status_code}")
                if backfill_response.text:
                    print(f"   Error: {backfill_response.text[:100]}...")

        except Exception as e:
            print(f"   ❌ Error creating calendar event: {e}")

    print(f"\n📊 Backfill Summary:")
    print(f"   Total appointments: {len(appointments)}")
    print(f"   Successfully backfilled: {success_count}")
    print(f"   Failed: {len(appointments) - success_count}")

    if success_count > 0:
        print(f"\n🎉 {success_count} Google Calendar events have been created!")
        print("📅 Check your Google Calendar to see the new events")

if __name__ == "__main__":
    backfill_calendar_events()
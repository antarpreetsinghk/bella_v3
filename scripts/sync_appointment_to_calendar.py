#!/usr/bin/env python3
"""
Manually sync an appointment to Google Calendar
Usage: python scripts/sync_appointment_to_calendar.py <appointment_id>
"""
import sys
import asyncio
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.google_calendar import create_calendar_event
from app.db.session import get_db
from app.db.models.appointment import Appointment
from app.db.models.user import User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def sync_appointment(appointment_id: int):
    """Sync a specific appointment to Google Calendar"""

    # Get database session
    async for db in get_db():
        try:
            # Query appointment with user info
            stmt = (
                select(Appointment, User)
                .join(User)
                .where(Appointment.id == appointment_id)
            )
            result = await db.execute(stmt)
            row = result.first()

            if not row:
                print(f"❌ Appointment {appointment_id} not found")
                return False

            appointment, user = row

            print(f"\n📅 Syncing Appointment #{appointment.id}")
            print(f"   User: {user.full_name}")
            print(f"   Phone: {user.mobile}")
            print(f"   Time: {appointment.starts_at}")
            print(f"   Duration: {appointment.duration_min} minutes")
            print(f"   Notes: {appointment.notes}")

            # Check if already has calendar event
            if appointment.google_event_id:
                print(f"\n⚠️  Appointment already has Google event ID: {appointment.google_event_id}")
                print("   Skipping sync to avoid duplicate.")
                return True

            # Create calendar event
            print("\n🔄 Creating Google Calendar event...")
            calendar_event = await create_calendar_event(
                user_name=user.full_name,
                user_mobile=user.mobile,
                starts_at_utc=appointment.starts_at,
                duration_min=appointment.duration_min,
                notes=appointment.notes
            )

            if calendar_event:
                event_id = calendar_event.get('event_id')
                event_link = calendar_event.get('event_link')

                print(f"\n✅ Calendar event created successfully!")
                print(f"   Event ID: {event_id}")
                print(f"   Event Link: {event_link}")

                # Update appointment with google_event_id
                appointment.google_event_id = event_id
                await db.commit()
                print(f"\n✅ Appointment updated with google_event_id")

                return True
            else:
                print("\n❌ Failed to create calendar event")
                print("   Check application logs for details")
                return False

        except Exception as e:
            print(f"\n❌ Error syncing appointment: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/sync_appointment_to_calendar.py <appointment_id>")
        sys.exit(1)

    try:
        appointment_id = int(sys.argv[1])
    except ValueError:
        print(f"Error: Invalid appointment ID '{sys.argv[1]}'. Must be an integer.")
        sys.exit(1)

    success = asyncio.run(sync_appointment(appointment_id))
    sys.exit(0 if success else 1)

#!/usr/bin/env python3
"""
Production Calendar Sync Verification Script

Connects to production database and verifies Google Calendar synchronization
for recent appointments.

Usage:
    # Set up SSH port forwarding first:
    ssh -L 15432:localhost:5432 root@15.157.56.64 -N -f

    # Then run this script:
    export PRODUCTION_DB_URL="postgresql+asyncpg://bella_user:BellaPassword123@localhost:15432/bella_db"
    python scripts/verify_production_calendar.py [--minutes N]
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
import json

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.db.models.appointment import Appointment
from app.db.models.user import User

# Color codes
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
CYAN = '\033[0;36m'
NC = '\033[0m'  # No Color


def print_header(text):
    """Print colored header"""
    print(f"\n{BLUE}{'='*70}{NC}")
    print(f"{BLUE}  {text}{NC}")
    print(f"{BLUE}{'='*70}{NC}\n")


def print_success(text):
    """Print success message"""
    print(f"{GREEN}✅ {text}{NC}")


def print_error(text):
    """Print error message"""
    print(f"{RED}❌ {text}{NC}")


def print_info(text):
    """Print info message"""
    print(f"{CYAN}ℹ️  {text}{NC}")


def print_warning(text):
    """Print warning message"""
    print(f"{YELLOW}⚠️  {text}{NC}")


async def get_recent_appointments(
    session: AsyncSession,
    minutes: int = 15
) -> List[tuple]:
    """
    Get recent appointments from production database.

    Args:
        session: Database session
        minutes: Look back this many minutes

    Returns:
        List of (appointment, user) tuples
    """
    cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=minutes)

    query = (
        select(Appointment, User)
        .join(User, Appointment.user_id == User.id)
        .where(Appointment.created_at >= cutoff_time)
        .order_by(Appointment.created_at.desc())
    )

    result = await session.execute(query)
    return list(result.all())


async def verify_calendar_event(
    event_id: str,
    calendar_id: str = "primary"
) -> Optional[Dict]:
    """
    Verify a Google Calendar event exists.

    Args:
        event_id: Google Calendar event ID
        calendar_id: Calendar ID to check

    Returns:
        Event details if found, None otherwise
    """
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        # Load service account credentials
        service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
        if not service_account_json:
            print_warning("GOOGLE_SERVICE_ACCOUNT_JSON not set, skipping calendar verification")
            return None

        credentials_dict = json.loads(service_account_json)
        credentials = service_account.Credentials.from_service_account_info(
            credentials_dict,
            scopes=['https://www.googleapis.com/auth/calendar']
        )

        service = build('calendar', 'v3', credentials=credentials)

        # Get event from calendar
        event = service.events().get(
            calendarId=calendar_id,
            eventId=event_id
        ).execute()

        return {
            "id": event.get("id"),
            "summary": event.get("summary"),
            "start": event.get("start", {}).get("dateTime"),
            "end": event.get("end", {}).get("dateTime"),
            "status": event.get("status"),
            "htmlLink": event.get("htmlLink"),
            "attendees": event.get("attendees", [])
        }

    except ImportError:
        print_warning("Google Calendar libraries not available")
        return None
    except Exception as e:
        print_error(f"Calendar API error: {e}")
        return None


async def verify_production_sync(minutes: int = 15):
    """
    Main verification function.

    Args:
        minutes: Look back this many minutes for appointments
    """
    print_header("Production Calendar Sync Verification")

    # Get database URL
    db_url = os.getenv("PRODUCTION_DB_URL")
    if not db_url:
        print_error("PRODUCTION_DB_URL environment variable not set")
        print_info("Set up SSH port forwarding:")
        print("  ssh -L 15432:localhost:5432 root@15.157.56.64 -N -f")
        print("\nThen set database URL:")
        print('  export PRODUCTION_DB_URL="postgresql+asyncpg://bella_user:BellaPassword123@localhost:15432/bella_db"')
        return 1

    # Parse database host to show which database we're connecting to
    if "localhost:15432" in db_url or "127.0.0.1:15432" in db_url:
        db_location = "Production (via SSH tunnel)"
    elif "15.157.56.64" in db_url:
        db_location = "Production (direct)"
    else:
        db_location = "Unknown"

    print(f"Database: {db_location}")
    print(f"Looking back: {minutes} minutes")
    print(f"Timestamp: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print()

    # Connect to database
    try:
        print_info("Connecting to production database...")
        engine = create_async_engine(db_url, echo=False, pool_pre_ping=True)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        # Test connection
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            assert result.scalar() == 1

        print_success("Connected to production database")

    except Exception as e:
        print_error(f"Database connection failed: {e}")
        print_info("Make sure SSH port forwarding is active:")
        print("  ssh -L 15432:localhost:5432 root@15.157.56.64 -N -f")
        return 1

    # Query recent appointments
    async with async_session() as session:
        print_info(f"Querying appointments from last {minutes} minutes...")
        appointments = await get_recent_appointments(session, minutes)

        if not appointments:
            print_warning(f"No appointments found in last {minutes} minutes")
            print_info("Try increasing the time window with --minutes flag")
            return 0

        print_success(f"Found {len(appointments)} recent appointment(s)")
        print()

        # Display appointment details and verify calendar sync
        for i, (appointment, user) in enumerate(appointments, 1):
            print_header(f"Appointment #{i}")

            # Basic appointment info
            print(f"ID:           {appointment.id}")
            print(f"User:         {user.full_name}")
            print(f"Phone:        {user.mobile}")
            print(f"Starts At:    {appointment.starts_at.strftime('%Y-%m-%d %H:%M %Z')}")
            print(f"Duration:     {appointment.duration_min} minutes")
            print(f"Status:       {appointment.status}")
            print(f"Test Data:    {appointment.is_test_data}")
            print(f"Created:      {appointment.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            print()

            # Calendar sync status
            if appointment.google_event_id:
                print_success(f"Calendar Event ID: {appointment.google_event_id}")

                # Verify event exists in Google Calendar
                print_info("Verifying event in Google Calendar...")
                event = await verify_calendar_event(appointment.google_event_id)

                if event:
                    print_success("Calendar event verified!")
                    print(f"  Summary:  {event.get('summary')}")
                    print(f"  Start:    {event.get('start')}")
                    print(f"  Status:   {event.get('status')}")
                    if event.get('htmlLink'):
                        print(f"  Link:     {event.get('htmlLink')}")
                else:
                    print_warning("Could not verify calendar event (API check failed)")
            else:
                print_error("No Google Calendar event ID - sync failed or disabled")
                print_info("Check production logs for sync errors:")
                print(f'  ssh root@15.157.56.64 "docker logs bella_app --since {minutes}m 2>&1 | grep -iE \'calendar|google.*{appointment.id}\'"')

            print()

    await engine.dispose()

    print_header("Verification Complete")
    print_success(f"Checked {len(appointments)} appointment(s) from production database")

    return 0


async def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Verify Google Calendar sync for production appointments"
    )
    parser.add_argument(
        "--minutes",
        type=int,
        default=15,
        help="Look back this many minutes for appointments (default: 15)"
    )
    args = parser.parse_args()

    try:
        return await verify_production_sync(minutes=args.minutes)
    except KeyboardInterrupt:
        print_error("\nVerification interrupted by user")
        return 1
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

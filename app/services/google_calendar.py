# app/services/google_calendar.py
"""
Google Calendar integration for automatic appointment booking.
Creates calendar events when appointments are successfully booked.
"""
from __future__ import annotations

import json
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from zoneinfo import ZoneInfo

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

LOCAL_TZ = ZoneInfo("America/Edmonton")
UTC = ZoneInfo("UTC")

# Service account credentials for Google Calendar API
_calendar_service = None


def get_calendar_service():
    """Get or create Google Calendar service with service account authentication"""
    global _calendar_service

    if _calendar_service is not None:
        return _calendar_service

    try:
        # Check if Google Calendar is enabled via environment variable
        if not os.getenv("GOOGLE_CALENDAR_ENABLED", "").lower() in ("true", "1", "yes"):
            logger.info("Google Calendar integration disabled via GOOGLE_CALENDAR_ENABLED")
            return None

        # Get service account credentials from environment
        service_account_info = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
        if not service_account_info:
            logger.warning("GOOGLE_SERVICE_ACCOUNT_JSON not set, calendar integration disabled")
            return None

        # Parse the service account JSON
        try:
            credentials_info = json.loads(service_account_info)
        except json.JSONDecodeError as e:
            logger.error("Invalid JSON in GOOGLE_SERVICE_ACCOUNT_JSON: %s", e)
            return None

        # Create credentials
        credentials = service_account.Credentials.from_service_account_info(
            credentials_info,
            scopes=['https://www.googleapis.com/auth/calendar']
        )

        # Build the Calendar service
        _calendar_service = build('calendar', 'v3', credentials=credentials)
        logger.info("Google Calendar service initialized successfully")
        return _calendar_service

    except Exception as e:
        logger.error("Failed to initialize Google Calendar service: %s", e)
        return None


async def create_calendar_event(
    user_name: str,
    user_mobile: str,
    starts_at_utc: datetime,
    duration_min: int = 30,
    notes: Optional[str] = None,
    calendar_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Create a calendar event for the appointment.

    Args:
        user_name: Full name of the client
        user_mobile: Client's phone number
        starts_at_utc: Appointment start time in UTC
        duration_min: Duration in minutes
        notes: Additional notes for the appointment
        calendar_id: Calendar ID (defaults to primary calendar)

    Returns:
        Dict with event details if successful, None if failed
    """
    service = get_calendar_service()
    if not service:
        logger.debug("Google Calendar service not available, skipping event creation")
        return None

    try:
        # Calculate end time
        ends_at_utc = starts_at_utc + timedelta(minutes=duration_min)

        # Convert to local time for display
        local_start = starts_at_utc.astimezone(LOCAL_TZ)
        local_end = ends_at_utc.astimezone(LOCAL_TZ)

        # Use primary calendar if none specified
        if not calendar_id:
            calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "primary")

        # Prepare event data
        event_summary = f"Appointment with {user_name}"
        event_description = f"""
Appointment Details:
• Client: {user_name}
• Phone: {user_mobile}
• Duration: {duration_min} minutes
• Booked via Bella Voice System

{f"Notes: {notes}" if notes else ""}
        """.strip()

        event_body = {
            'summary': event_summary,
            'description': event_description,
            'start': {
                'dateTime': starts_at_utc.isoformat(),
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': ends_at_utc.isoformat(),
                'timeZone': 'UTC',
            },
            'attendees': [
                {
                    'email': os.getenv("BUSINESS_EMAIL", ""),
                    'displayName': "Bella Services",
                    'responseStatus': 'accepted'
                }
            ],
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},  # 1 day before
                    {'method': 'popup', 'minutes': 15},       # 15 minutes before
                ],
            },
            'colorId': '9',  # Blue color for appointments
        }

        # Create the event
        event = service.events().insert(
            calendarId=calendar_id,
            body=event_body
        ).execute()

        event_link = event.get('htmlLink', '')
        logger.info(
            "Calendar event created: %s for %s at %s",
            event.get('id'),
            user_name,
            local_start.strftime("%Y-%m-%d %H:%M %Z")
        )

        return {
            'event_id': event.get('id'),
            'event_link': event_link,
            'calendar_id': calendar_id,
            'start_time': starts_at_utc.isoformat(),
            'end_time': ends_at_utc.isoformat(),
            'summary': event_summary
        }

    except HttpError as e:
        logger.error("Google Calendar API error: %s", e)
        return None
    except Exception as e:
        logger.error("Failed to create calendar event: %s", e)
        return None


async def delete_calendar_event(
    event_id: str,
    calendar_id: Optional[str] = None
) -> bool:
    """
    Delete a calendar event by ID.

    Args:
        event_id: Google Calendar event ID
        calendar_id: Calendar ID (defaults to primary)

    Returns:
        True if successful, False otherwise
    """
    service = get_calendar_service()
    if not service:
        logger.debug("Google Calendar service not available")
        return False

    try:
        if not calendar_id:
            calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "primary")

        service.events().delete(
            calendarId=calendar_id,
            eventId=event_id
        ).execute()

        logger.info("Calendar event deleted: %s", event_id)
        return True

    except HttpError as e:
        if e.resp.status == 404:
            logger.warning("Calendar event not found: %s", event_id)
        else:
            logger.error("Google Calendar API error deleting event: %s", e)
        return False
    except Exception as e:
        logger.error("Failed to delete calendar event: %s", e)
        return False


async def update_calendar_event(
    event_id: str,
    user_name: str,
    user_mobile: str,
    starts_at_utc: datetime,
    duration_min: int = 30,
    notes: Optional[str] = None,
    calendar_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Update an existing calendar event.

    Args:
        event_id: Google Calendar event ID
        user_name: Full name of the client
        user_mobile: Client's phone number
        starts_at_utc: Appointment start time in UTC
        duration_min: Duration in minutes
        notes: Additional notes for the appointment
        calendar_id: Calendar ID (defaults to primary)

    Returns:
        Dict with updated event details if successful, None if failed
    """
    service = get_calendar_service()
    if not service:
        logger.debug("Google Calendar service not available")
        return None

    try:
        if not calendar_id:
            calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "primary")

        # Calculate end time
        ends_at_utc = starts_at_utc + timedelta(minutes=duration_min)

        # Prepare updated event data
        event_summary = f"Appointment with {user_name}"
        event_description = f"""
Appointment Details:
• Client: {user_name}
• Phone: {user_mobile}
• Duration: {duration_min} minutes
• Booked via Bella Voice System

{f"Notes: {notes}" if notes else ""}
        """.strip()

        # Get existing event
        existing_event = service.events().get(
            calendarId=calendar_id,
            eventId=event_id
        ).execute()

        # Update event fields
        existing_event.update({
            'summary': event_summary,
            'description': event_description,
            'start': {
                'dateTime': starts_at_utc.isoformat(),
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': ends_at_utc.isoformat(),
                'timeZone': 'UTC',
            },
        })

        # Update the event
        updated_event = service.events().update(
            calendarId=calendar_id,
            eventId=event_id,
            body=existing_event
        ).execute()

        logger.info("Calendar event updated: %s for %s", event_id, user_name)

        return {
            'event_id': updated_event.get('id'),
            'event_link': updated_event.get('htmlLink', ''),
            'calendar_id': calendar_id,
            'start_time': starts_at_utc.isoformat(),
            'end_time': ends_at_utc.isoformat(),
            'summary': event_summary
        }

    except HttpError as e:
        logger.error("Google Calendar API error updating event: %s", e)
        return None
    except Exception as e:
        logger.error("Failed to update calendar event: %s", e)
        return None


async def check_calendar_availability(
    starts_at_utc: datetime,
    duration_min: int = 30,
    calendar_id: Optional[str] = None
) -> bool:
    """
    Check if a time slot is available on the calendar.

    Args:
        starts_at_utc: Proposed start time in UTC
        duration_min: Duration in minutes
        calendar_id: Calendar ID (defaults to primary)

    Returns:
        True if available, False if conflicting appointment exists
    """
    service = get_calendar_service()
    if not service:
        logger.debug("Google Calendar service not available, assuming available")
        return True

    try:
        if not calendar_id:
            calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "primary")

        # Calculate end time
        ends_at_utc = starts_at_utc + timedelta(minutes=duration_min)

        # Query for events in the time range
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=starts_at_utc.isoformat(),
            timeMax=ends_at_utc.isoformat(),
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])

        # Check for conflicts
        for event in events:
            # Skip cancelled events
            if event.get('status') == 'cancelled':
                continue

            logger.info("Conflicting appointment found: %s", event.get('summary', 'Untitled'))
            return False

        return True

    except HttpError as e:
        logger.error("Google Calendar API error checking availability: %s", e)
        # Assume available if we can't check
        return True
    except Exception as e:
        logger.error("Failed to check calendar availability: %s", e)
        # Assume available if we can't check
        return True
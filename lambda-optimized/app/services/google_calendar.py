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

from app.utils.secrets import get_config_value, is_feature_enabled

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
        # Check if Google Calendar is enabled via configuration (env var or secrets)
        if not is_feature_enabled("GOOGLE_CALENDAR_ENABLED"):
            logger.info("Google Calendar integration disabled via GOOGLE_CALENDAR_ENABLED")
            return None

        # Get service account credentials from configuration (env var or secrets)
        service_account_info = get_config_value("GOOGLE_SERVICE_ACCOUNT_JSON")
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
            calendar_id = get_config_value("GOOGLE_CALENDAR_ID", "primary")

        # Prepare event data
        event_summary = f"Appointment with {user_name}"
        business_email = get_config_value("BUSINESS_EMAIL", "doctor@practice.com")
        event_description = f"""
Appointment Details:
• Client: {user_name}
• Phone: {user_mobile}
• Duration: {duration_min} minutes
• Contact: {business_email}
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
            # Note: Service accounts cannot invite attendees without Domain-Wide Delegation
            # The business email will be included in the description instead
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},  # 1 day before
                    {'method': 'popup', 'minutes': 15},       # 15 minutes before
                ],
            },
            'colorId': '9',  # Blue color for appointments
            'visibility': 'public',  # Make details visible to subscribers
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
        business_email = os.getenv("BUSINESS_EMAIL", "doctor@practice.com")
        event_description = f"""
Appointment Details:
• Client: {user_name}
• Phone: {user_mobile}
• Duration: {duration_min} minutes
• Contact: {business_email}
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


async def get_available_slots(
    date: datetime,
    duration_min: int = 30,
    business_hours: tuple = (9, 17),  # 9 AM to 5 PM
    slot_interval: int = 30,  # 30-minute intervals
    calendar_id: Optional[str] = None
) -> list[datetime]:
    """
    Get available time slots for a specific date.

    Args:
        date: Date to check (time will be ignored)
        duration_min: Required duration in minutes
        business_hours: Tuple of (start_hour, end_hour) in 24h format
        slot_interval: Interval between slots in minutes
        calendar_id: Calendar ID (defaults to primary)

    Returns:
        List of available start times in UTC
    """
    service = get_calendar_service()
    if not service:
        logger.debug("Google Calendar service not available")
        return []

    try:
        if not calendar_id:
            calendar_id = get_config_value("GOOGLE_CALENDAR_ID", "primary")

        # Convert date to local timezone and set business hours
        local_date = date.replace(tzinfo=LOCAL_TZ) if date.tzinfo is None else date.astimezone(LOCAL_TZ)
        start_time = local_date.replace(hour=business_hours[0], minute=0, second=0, microsecond=0)
        end_time = local_date.replace(hour=business_hours[1], minute=0, second=0, microsecond=0)

        # Convert to UTC for API calls
        start_utc = start_time.astimezone(UTC)
        end_utc = end_time.astimezone(UTC)

        # Get all events for the day
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=start_utc.isoformat(),
            timeMax=end_utc.isoformat(),
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])
        busy_slots = []

        # Extract busy time ranges
        for event in events:
            if event.get('status') == 'cancelled':
                continue

            event_start = datetime.fromisoformat(event['start'].get('dateTime', event['start'].get('date')))
            event_end = datetime.fromisoformat(event['end'].get('dateTime', event['end'].get('date')))

            # Ensure timezone awareness
            if event_start.tzinfo is None:
                event_start = event_start.replace(tzinfo=UTC)
            if event_end.tzinfo is None:
                event_end = event_end.replace(tzinfo=UTC)

            busy_slots.append((event_start, event_end))

        # Generate potential slots
        available_slots = []
        current_time = start_utc

        while current_time + timedelta(minutes=duration_min) <= end_utc:
            proposed_end = current_time + timedelta(minutes=duration_min)

            # Check if this slot conflicts with any busy periods
            is_available = True
            for busy_start, busy_end in busy_slots:
                # Check for overlap
                if (current_time < busy_end and proposed_end > busy_start):
                    is_available = False
                    break

            if is_available:
                available_slots.append(current_time)

            current_time += timedelta(minutes=slot_interval)

        logger.info("Found %d available slots for %s", len(available_slots), local_date.strftime("%Y-%m-%d"))
        return available_slots

    except Exception as e:
        logger.error("Failed to get available slots: %s", e)
        return []


async def suggest_alternative_times(
    requested_time: datetime,
    duration_min: int = 30,
    max_suggestions: int = 3,
    calendar_id: Optional[str] = None
) -> list[datetime]:
    """
    Suggest alternative appointment times when requested time is not available.

    Args:
        requested_time: Originally requested time
        duration_min: Required duration in minutes
        max_suggestions: Maximum number of suggestions to return
        calendar_id: Calendar ID (defaults to primary)

    Returns:
        List of suggested alternative times in UTC
    """
    try:
        # Check same day first
        same_day_slots = await get_available_slots(
            requested_time,
            duration_min=duration_min,
            calendar_id=calendar_id
        )

        suggestions = []

        # Filter same-day slots to only include times after the requested time
        requested_local = requested_time.astimezone(LOCAL_TZ)
        for slot in same_day_slots:
            slot_local = slot.astimezone(LOCAL_TZ)
            if slot_local >= requested_local:
                suggestions.append(slot)
                if len(suggestions) >= max_suggestions:
                    break

        # If we need more suggestions, check next few days
        if len(suggestions) < max_suggestions:
            for days_ahead in range(1, 8):  # Check up to a week ahead
                future_date = requested_time + timedelta(days=days_ahead)
                future_slots = await get_available_slots(
                    future_date,
                    duration_min=duration_min,
                    calendar_id=calendar_id
                )

                # Add first few slots from each day
                for slot in future_slots[:2]:  # Max 2 per day
                    suggestions.append(slot)
                    if len(suggestions) >= max_suggestions:
                        break

                if len(suggestions) >= max_suggestions:
                    break

        logger.info("Generated %d alternative time suggestions", len(suggestions))
        return suggestions[:max_suggestions]

    except Exception as e:
        logger.error("Failed to suggest alternative times: %s", e)
        return []


async def get_calendar_summary(
    calendar_id: Optional[str] = None,
    days_ahead: int = 7
) -> Dict[str, Any]:
    """
    Get a summary of calendar availability for voice prompts.

    Args:
        calendar_id: Calendar ID (defaults to primary)
        days_ahead: Number of days to look ahead

    Returns:
        Dictionary with availability summary
    """
    service = get_calendar_service()
    if not service:
        return {"available": True, "message": "Calendar checking unavailable"}

    try:
        if not calendar_id:
            calendar_id = get_config_value("GOOGLE_CALENDAR_ID", "primary")

        today = datetime.now(LOCAL_TZ).replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = today + timedelta(days=days_ahead)

        total_slots = 0
        available_slots = 0
        next_available = None

        for day_offset in range(days_ahead):
            check_date = today + timedelta(days=day_offset)

            # Skip weekends (assuming business doesn't operate weekends)
            if check_date.weekday() >= 5:  # Saturday = 5, Sunday = 6
                continue

            day_slots = await get_available_slots(check_date, duration_min=30, calendar_id=calendar_id)
            total_slots += 16  # Assuming 8-hour days with 30-min slots
            available_slots += len(day_slots)

            if day_slots and next_available is None:
                next_available = day_slots[0]

        availability_percentage = (available_slots / total_slots * 100) if total_slots > 0 else 0

        # Generate voice-friendly message
        if availability_percentage > 75:
            message = "We have plenty of availability this week."
        elif availability_percentage > 50:
            message = "We have good availability this week."
        elif availability_percentage > 25:
            message = "We have limited availability this week."
        else:
            message = "We're quite busy this week, but I can find you a time."

        if next_available:
            next_local = next_available.astimezone(LOCAL_TZ)
            if next_local.date() == today.date():
                message += f" The earliest available is today at {next_local.strftime('%I:%M %p')}."
            else:
                message += f" The earliest available is {next_local.strftime('%A at %I:%M %p')}."

        return {
            "available": available_slots > 0,
            "availability_percentage": availability_percentage,
            "total_slots": total_slots,
            "available_slots": available_slots,
            "next_available": next_available.isoformat() if next_available else None,
            "message": message
        }

    except Exception as e:
        logger.error("Failed to get calendar summary: %s", e)
        return {"available": True, "message": "I'll check our schedule for you."}


async def find_best_slot_for_preference(
    user_preferences: list[str],
    duration_min: int = 30,
    days_ahead: int = 14,
    calendar_id: Optional[str] = None
) -> Optional[datetime]:
    """
    Find the best available slot based on user preferences.

    Args:
        user_preferences: List of preferences like ["morning", "afternoon", "monday", "friday"]
        duration_min: Required duration in minutes
        days_ahead: Number of days to search ahead
        calendar_id: Calendar ID (defaults to primary)

    Returns:
        Best matching available slot in UTC, or None if none found
    """
    try:
        today = datetime.now(LOCAL_TZ).replace(hour=0, minute=0, second=0, microsecond=0)

        # Define time preferences
        time_slots = {
            "morning": (9, 12),    # 9 AM - 12 PM
            "afternoon": (12, 17), # 12 PM - 5 PM
            "evening": (17, 20)    # 5 PM - 8 PM (if available)
        }

        weekday_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

        best_slots = []

        for day_offset in range(days_ahead):
            check_date = today + timedelta(days=day_offset)
            weekday_name = weekday_names[check_date.weekday()]

            # Check if this day matches user's day preferences
            day_match = not any(day in user_preferences for day in weekday_names) or weekday_name in user_preferences

            if not day_match:
                continue

            # Get time preferences
            preferred_hours = (9, 17)  # Default business hours
            for pref in user_preferences:
                if pref in time_slots:
                    preferred_hours = time_slots[pref]
                    break

            # Get available slots for this day with preferred hours
            day_slots = await get_available_slots(
                check_date,
                duration_min=duration_min,
                business_hours=preferred_hours,
                calendar_id=calendar_id
            )

            for slot in day_slots:
                preference_score = 0

                # Score based on how well it matches preferences
                slot_local = slot.astimezone(LOCAL_TZ)
                hour = slot_local.hour

                # Time preference scoring
                for pref in user_preferences:
                    if pref in time_slots:
                        pref_start, pref_end = time_slots[pref]
                        if pref_start <= hour < pref_end:
                            preference_score += 10

                # Day preference scoring
                if weekday_name in user_preferences:
                    preference_score += 5

                # Prefer sooner dates (but not too heavily)
                preference_score += max(0, 14 - day_offset)

                best_slots.append((slot, preference_score))

        if best_slots:
            # Sort by preference score (highest first)
            best_slots.sort(key=lambda x: x[1], reverse=True)
            best_slot = best_slots[0][0]

            logger.info("Found preferred slot with score %d: %s",
                       best_slots[0][1], best_slot.astimezone(LOCAL_TZ).strftime("%A, %B %d at %I:%M %p"))
            return best_slot

        return None

    except Exception as e:
        logger.error("Failed to find best slot for preferences: %s", e)
        return None
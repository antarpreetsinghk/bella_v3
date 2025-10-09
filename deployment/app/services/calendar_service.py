"""
Calendar Service Integration
Wrapper around existing Google Calendar service for appointment booking
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class GoogleCalendarService:
    def __init__(self):
        pass

    async def check_availability(self, appointment_datetime: datetime, duration_minutes: int = 30) -> bool:
        """Check if the requested time slot is available"""
        try:
            # Use existing Google Calendar service
            from app.services.google_calendar import check_calendar_availability

            return await check_calendar_availability(
                starts_at_utc=appointment_datetime,
                duration_min=duration_minutes
            )

        except ImportError:
            logger.warning("Google Calendar service not available")
            return True  # Fallback: assume available
        except Exception as e:
            logger.error(f"Error checking calendar availability: {e}")
            return True  # Fallback: assume available

    async def create_appointment(self, appointment_data: Dict) -> Optional[str]:
        """Create a new appointment in Google Calendar"""
        try:
            # Use existing Google Calendar service
            from app.services.google_calendar import create_calendar_event

            result = await create_calendar_event(
                user_name=appointment_data.get('name', 'Customer'),
                user_mobile=appointment_data.get('phone', 'Not provided'),
                starts_at_utc=appointment_data['datetime'],
                duration_min=appointment_data.get('duration', 30),
                notes=appointment_data.get('notes')
            )

            if result:
                return result.get('event_id')
            return None

        except ImportError:
            logger.warning("Google Calendar service not available")
            return None
        except Exception as e:
            logger.error(f"Error creating calendar event: {e}")
            return None

    async def get_available_slots(self, date: datetime, duration_minutes: int = 30) -> List[datetime]:
        """Get available time slots for a specific date"""
        try:
            # Basic implementation - generate slots and check availability
            from app.core.config import settings

            start_hour = getattr(settings, 'BUSINESS_HOURS_START', 9)
            end_hour = getattr(settings, 'BUSINESS_HOURS_END', 17)

            available_slots = []
            current_time = date.replace(hour=start_hour, minute=0, second=0, microsecond=0)
            end_of_day = date.replace(hour=end_hour, minute=0, second=0, microsecond=0)

            # Generate 30-minute slots
            while current_time + timedelta(minutes=duration_minutes) <= end_of_day:
                if await self.check_availability(current_time, duration_minutes):
                    available_slots.append(current_time)
                current_time += timedelta(minutes=30)

            return available_slots

        except Exception as e:
            logger.error(f"Error getting available slots: {e}")
            return []

    async def update_appointment(self, event_id: str, appointment_data: Dict) -> bool:
        """Update an existing appointment"""
        try:
            # Use existing Google Calendar service
            from app.services.google_calendar import update_calendar_event

            result = await update_calendar_event(
                event_id=event_id,
                user_name=appointment_data.get('name', 'Customer'),
                user_mobile=appointment_data.get('phone', 'Not provided'),
                starts_at_utc=appointment_data['datetime'],
                duration_min=appointment_data.get('duration', 30),
                notes=appointment_data.get('notes')
            )

            return result is not None

        except ImportError:
            logger.warning("Google Calendar service not available")
            return False
        except Exception as e:
            logger.error(f"Error updating calendar event: {e}")
            return False

    async def cancel_appointment(self, event_id: str) -> bool:
        """Cancel an appointment"""
        try:
            # Use existing Google Calendar service
            from app.services.google_calendar import delete_calendar_event

            return await delete_calendar_event(event_id=event_id)

        except ImportError:
            logger.warning("Google Calendar service not available")
            return False
        except Exception as e:
            logger.error(f"Error canceling calendar event: {e}")
            return False
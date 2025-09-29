#!/usr/bin/env python3
"""
Tests for the booking service functionality.
"""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Add app to Python path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.booking import book_from_transcript, BookResult

UTC = ZoneInfo("UTC")
LOCAL_TZ = ZoneInfo("America/Edmonton")


@pytest.fixture
def mock_db_session():
    """Mock database session"""
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    return mock_session


@pytest.fixture
def sample_booking_transcript():
    """Sample booking transcript"""
    return "Hi, this is John Smith. I'd like to book an appointment for tomorrow at 2 PM. My number is 416-555-1234."


class TestBookingService:
    """Test booking service functionality"""

    @pytest.mark.asyncio
    @patch('app.services.booking.extract_appointment_fields', new_callable=AsyncMock)
    @patch('app.services.booking.get_user_by_mobile')
    @patch('app.services.booking.create_user')
    @patch('app.services.booking.create_appointment_unique')
    @patch('app.services.booking.create_calendar_event')
    async def test_successful_booking_new_user(
        self, mock_calendar, mock_create_appt, mock_create_user,
        mock_get_user, mock_extract, mock_db_session
    ):
        """Test successful booking for a new user"""
        # Mock LLM extraction (async function)
        mock_extracted = MagicMock()
        mock_extracted.model_dump.return_value = {
            'full_name': 'John Smith',
            'mobile': '+14165551234',
            'starts_at': '2025-09-30T14:00:00-04:00',
            'duration_min': 30,
            'notes': 'Regular appointment'
        }
        mock_extract.return_value = mock_extracted

        # Mock user lookup - not found
        mock_get_user.return_value = None

        # Mock user creation
        mock_new_user = MagicMock()
        mock_new_user.id = 123
        mock_new_user.full_name = 'John Smith'
        mock_new_user.mobile = '+14165551234'
        mock_create_user.return_value = mock_new_user

        # Mock appointment creation
        mock_appointment = MagicMock()
        mock_appointment.id = 456
        mock_appointment.starts_at = datetime(2025, 9, 30, 18, 0, 0, tzinfo=UTC)  # 2 PM EDT = 6 PM UTC
        mock_appointment.duration_min = 30
        mock_appointment.notes = 'Regular appointment'
        mock_create_appt.return_value = mock_appointment

        # Mock calendar integration
        mock_calendar.return_value = {
            'event_id': 'calendar_event_123',
            'event_link': 'https://calendar.google.com/event?eid=123'
        }

        # Execute booking
        result = await book_from_transcript(
            mock_db_session,
            transcript="John Smith, tomorrow at 2 PM, 416-555-1234"
        )

        # Verify results
        assert isinstance(result, BookResult)
        assert result.created is True
        assert "John Smith" in result.message_for_caller
        assert result.echo['appointment_id'] == 456
        assert result.echo['user_id'] == 123
        assert 'calendar_event' in result.echo

    @pytest.mark.asyncio
    @patch('app.services.booking.extract_appointment_fields', new_callable=AsyncMock)
    async def test_booking_missing_phone(self, mock_extract, mock_db_session):
        """Test booking with missing phone number"""
        # Mock LLM extraction - missing phone
        mock_extracted = MagicMock()
        mock_extracted.model_dump.return_value = {
            'full_name': 'John Smith',
            'mobile': None,
            'starts_at': '2025-09-30T14:00:00-04:00',
            'duration_min': 30,
            'notes': 'Regular appointment'
        }
        mock_extract.return_value = mock_extracted

        result = await book_from_transcript(
            mock_db_session,
            transcript="John Smith, tomorrow at 2 PM"
        )

        assert result.created is False
        assert "phone number" in result.message_for_caller.lower()
        assert "mobile" in result.echo['missing']

    @pytest.mark.asyncio
    @patch('app.services.booking.extract_appointment_fields', new_callable=AsyncMock)
    async def test_booking_missing_time(self, mock_extract, mock_db_session):
        """Test booking with missing time"""
        # Mock LLM extraction - missing time
        mock_extracted = MagicMock()
        mock_extracted.model_dump.return_value = {
            'full_name': 'John Smith',
            'mobile': '+14165551234',
            'starts_at': None,
            'duration_min': 30,
            'notes': None
        }
        mock_extract.return_value = mock_extracted

        result = await book_from_transcript(
            mock_db_session,
            transcript="John Smith, 416-555-1234"
        )

        assert result.created is False
        assert "date and time" in result.message_for_caller.lower()
        assert "starts_at" in result.echo['missing']

    @pytest.mark.asyncio
    @patch('app.services.booking.extract_appointment_fields', new_callable=AsyncMock)
    @patch('app.services.booking.get_user_by_mobile')
    @patch('app.services.booking.create_appointment_unique')
    async def test_booking_duplicate_appointment(
        self, mock_create_appt, mock_get_user, mock_extract, mock_db_session
    ):
        """Test booking with duplicate appointment conflict"""
        # Mock LLM extraction
        mock_extracted = MagicMock()
        mock_extracted.model_dump.return_value = {
            'full_name': 'John Smith',
            'mobile': '+14165551234',
            'starts_at': '2025-09-30T14:00:00-04:00',
            'duration_min': 30,
            'notes': 'Regular appointment'
        }
        mock_extract.return_value = mock_extracted

        # Mock existing user
        mock_user = MagicMock()
        mock_user.id = 123
        mock_user.full_name = 'John Smith'
        mock_user.mobile = '+14165551234'
        mock_get_user.return_value = mock_user

        # Mock appointment creation - conflict
        mock_create_appt.side_effect = ValueError("Appointment already exists at this time")

        result = await book_from_transcript(
            mock_db_session,
            transcript="John Smith, tomorrow at 2 PM, 416-555-1234"
        )

        assert result.created is False
        assert "already an appointment" in result.message_for_caller
        assert "error" in result.echo

    @pytest.mark.asyncio
    @patch('app.services.booking.extract_appointment_fields', new_callable=AsyncMock)
    @patch('app.services.booking.get_user_by_mobile')
    @patch('app.services.booking.create_user')
    @patch('app.services.booking.create_appointment_unique')
    @patch('app.services.booking.create_calendar_event')
    async def test_booking_calendar_integration_failure(
        self, mock_calendar, mock_create_appt, mock_create_user,
        mock_get_user, mock_extract, mock_db_session
    ):
        """Test booking when calendar integration fails"""
        # Mock successful booking setup
        mock_extracted = MagicMock()
        mock_extracted.model_dump.return_value = {
            'full_name': 'John Smith',
            'mobile': '+14165551234',
            'starts_at': '2025-09-30T14:00:00-04:00',
            'duration_min': 30,
            'notes': 'Regular appointment'
        }
        mock_extract.return_value = mock_extracted

        mock_get_user.return_value = None

        mock_user = MagicMock()
        mock_user.id = 123
        mock_user.full_name = 'John Smith'
        mock_user.mobile = '+14165551234'
        mock_create_user.return_value = mock_user

        mock_appointment = MagicMock()
        mock_appointment.id = 456
        mock_appointment.starts_at = datetime(2025, 9, 30, 18, 0, 0, tzinfo=UTC)
        mock_appointment.duration_min = 30
        mock_appointment.notes = 'Regular appointment'
        mock_create_appt.return_value = mock_appointment

        # Mock calendar integration failure
        mock_calendar.side_effect = Exception("Calendar API error")

        result = await book_from_transcript(
            mock_db_session,
            transcript="John Smith, tomorrow at 2 PM, 416-555-1234"
        )

        # Booking should succeed even if calendar fails
        assert result.created is True
        assert result.echo['appointment_id'] == 456
        # Calendar event should not be in echo due to failure
        assert 'calendar_event' not in result.echo

    @pytest.mark.asyncio
    @patch('app.services.booking.extract_appointment_fields', new_callable=AsyncMock)
    @patch('app.services.booking.get_user_by_mobile')
    @patch('app.services.booking.create_user')
    @patch('app.services.booking.create_appointment_unique')
    async def test_booking_with_caller_id_fallback(self, mock_create_appt, mock_create_user, mock_get_user, mock_extract, mock_db_session):
        """Test booking using caller ID as phone fallback"""
        # Mock LLM extraction - missing phone in transcript
        mock_extracted = MagicMock()
        mock_extracted.model_dump.return_value = {
            'full_name': 'John Smith',
            'mobile': None,  # Not in transcript
            'starts_at': '2025-09-30T14:00:00-04:00',
            'duration_min': 30,
            'notes': 'Regular appointment'
        }
        mock_extract.return_value = mock_extracted

        # Mock user lookup - not found (use caller ID)
        mock_get_user.return_value = None

        # Mock user creation with caller ID
        mock_new_user = MagicMock()
        mock_new_user.id = 123
        mock_new_user.full_name = 'John Smith'
        mock_new_user.mobile = '+14165551234'
        mock_create_user.return_value = mock_new_user

        # Mock appointment creation
        mock_appointment = MagicMock()
        mock_appointment.id = 456
        mock_create_appt.return_value = mock_appointment

        result = await book_from_transcript(
            mock_db_session,
            transcript="John Smith, tomorrow at 2 PM",
            from_number="+14165551234"  # Use caller ID
        )

        # Should succeed because from_number provides valid fallback for missing mobile
        assert result.created is True
        # The normalized phone should show the from_number was used successfully
        assert result.echo['normalized']['mobile'] == '+14165551234'

    @pytest.mark.asyncio
    @patch('app.services.booking.extract_appointment_fields', new_callable=AsyncMock)
    async def test_booking_invalid_time_format(self, mock_extract, mock_db_session):
        """Test booking with invalid time format"""
        # Mock LLM extraction - invalid time
        mock_extracted = MagicMock()
        mock_extracted.model_dump.return_value = {
            'full_name': 'John Smith',
            'mobile': '+14165551234',
            'starts_at': 'invalid_time_format',
            'duration_min': 30,
            'notes': 'Regular appointment'
        }
        mock_extract.return_value = mock_extracted

        result = await book_from_transcript(
            mock_db_session,
            transcript="John Smith, some invalid time, 416-555-1234"
        )

        assert result.created is False
        assert "starts_at" in result.echo['missing']


class TestBookingUtilityFunctions:
    """Test booking utility functions"""

    @pytest.mark.asyncio
    @patch('app.services.booking.get_user_by_mobile', new_callable=AsyncMock)
    @patch('app.services.booking.create_user', new_callable=AsyncMock)
    @patch('app.services.booking.create_appointment_unique', new_callable=AsyncMock)
    async def test_booking_with_different_locales(self, mock_create_appt, mock_create_user, mock_get_user, mock_db_session):
        """Test booking with different locale settings"""
        with patch('app.services.booking.extract_appointment_fields', new_callable=AsyncMock) as mock_extract:
            mock_extracted = MagicMock()
            mock_extracted.model_dump.return_value = {
                'full_name': 'Jean Dupont',
                'mobile': '+15145551234',  # Quebec number
                'starts_at': '2025-09-30T14:00:00-04:00',
                'duration_min': 30,
                'notes': 'Rendez-vous régulier'
            }
            mock_extract.return_value = mock_extracted

            # Mock user lookup - not found
            mock_get_user.return_value = None

            # Mock user creation
            mock_user = MagicMock()
            mock_user.id = 123
            mock_user.full_name = 'Jean Dupont'
            mock_user.mobile = '+15145551234'
            mock_create_user.return_value = mock_user

            # Mock appointment creation
            mock_appointment = MagicMock()
            mock_appointment.id = 456
            mock_appointment.starts_at = datetime(2025, 9, 30, 18, 0, 0, tzinfo=UTC)
            mock_appointment.duration_min = 30
            mock_appointment.notes = 'Rendez-vous régulier'
            mock_create_appt.return_value = mock_appointment

            result = await book_from_transcript(
                mock_db_session,
                transcript="Jean Dupont, demain à 14h, 514-555-1234",
                locale="fr-CA"
            )

            # Should succeed with proper mocking and locale should be passed
            assert result.created is True
            mock_extract.assert_called_once()

    def test_booking_result_structure(self):
        """Test BookResult data structure"""
        result = BookResult(
            created=True,
            message_for_caller="Test message",
            echo={"test": "data"}
        )

        assert result.created is True
        assert result.message_for_caller == "Test message"
        assert result.echo == {"test": "data"}
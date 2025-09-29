#!/usr/bin/env python3
"""
Tests for Google Calendar integration functionality.
"""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Add app to Python path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.google_calendar import (
    create_calendar_event,
    delete_calendar_event,
    check_calendar_availability,
    get_calendar_service
)

UTC = ZoneInfo("UTC")
LOCAL_TZ = ZoneInfo("America/Edmonton")


@pytest.fixture
def sample_event_data():
    """Sample event data for testing"""
    return {
        'user_name': 'John Smith',
        'user_mobile': '+14165551234',
        'starts_at_utc': datetime.now(UTC) + timedelta(hours=1),
        'duration_min': 30,
        'notes': 'Test appointment'
    }


class TestGoogleCalendarService:
    """Test Google Calendar service functionality"""

    @patch.dict(os.environ, {'GOOGLE_CALENDAR_ENABLED': 'false'})
    def test_get_calendar_service_disabled(self):
        """Test calendar service when disabled"""
        service = get_calendar_service()
        assert service is None

    @patch.dict(os.environ, {'GOOGLE_CALENDAR_ENABLED': 'true', 'GOOGLE_SERVICE_ACCOUNT_JSON': ''})
    def test_get_calendar_service_no_credentials(self):
        """Test calendar service with missing credentials"""
        service = get_calendar_service()
        assert service is None

    @patch.dict(os.environ, {
        'GOOGLE_CALENDAR_ENABLED': 'true',
        'GOOGLE_SERVICE_ACCOUNT_JSON': 'invalid_json'
    })
    def test_get_calendar_service_invalid_json(self):
        """Test calendar service with invalid JSON credentials"""
        service = get_calendar_service()
        assert service is None


class TestCalendarEventOperations:
    """Test calendar event CRUD operations"""

    @pytest.mark.asyncio
    @patch('app.services.google_calendar.get_calendar_service')
    async def test_create_calendar_event_service_disabled(self, mock_service, sample_event_data):
        """Test event creation when service is disabled"""
        mock_service.return_value = None

        result = await create_calendar_event(**sample_event_data)
        assert result is None

    @pytest.mark.asyncio
    @patch('app.services.google_calendar.get_calendar_service')
    async def test_create_calendar_event_success(self, mock_service, sample_event_data):
        """Test successful event creation"""
        # Mock Google Calendar service
        mock_calendar_service = MagicMock()
        mock_event_response = {
            'id': 'test_event_123',
            'htmlLink': 'https://calendar.google.com/event?eid=test123',
            'summary': 'Appointment with John Smith'
        }
        mock_calendar_service.events().insert().execute.return_value = mock_event_response
        mock_service.return_value = mock_calendar_service

        result = await create_calendar_event(**sample_event_data)

        assert result is not None
        assert result['event_id'] == 'test_event_123'
        assert result['event_link'] == 'https://calendar.google.com/event?eid=test123'
        assert 'start_time' in result
        assert 'end_time' in result

    @pytest.mark.asyncio
    @patch('app.services.google_calendar.get_calendar_service')
    async def test_create_calendar_event_api_error(self, mock_service, sample_event_data):
        """Test event creation with API error"""
        mock_calendar_service = MagicMock()
        mock_calendar_service.events().insert().execute.side_effect = Exception("API Error")
        mock_service.return_value = mock_calendar_service

        result = await create_calendar_event(**sample_event_data)
        assert result is None

    @pytest.mark.asyncio
    @patch('app.services.google_calendar.get_calendar_service')
    async def test_delete_calendar_event_success(self, mock_service):
        """Test successful event deletion"""
        mock_calendar_service = MagicMock()
        mock_calendar_service.events().delete().execute.return_value = None
        mock_service.return_value = mock_calendar_service

        result = await delete_calendar_event('test_event_123')
        assert result is True

    @pytest.mark.asyncio
    @patch('app.services.google_calendar.get_calendar_service')
    async def test_delete_calendar_event_not_found(self, mock_service):
        """Test event deletion when event not found"""
        from googleapiclient.errors import HttpError

        mock_calendar_service = MagicMock()
        mock_error = HttpError(
            resp=MagicMock(status=404),
            content=b'Not found'
        )
        mock_calendar_service.events().delete().execute.side_effect = mock_error
        mock_service.return_value = mock_calendar_service

        result = await delete_calendar_event('nonexistent_event')
        assert result is False

    @pytest.mark.asyncio
    @patch('app.services.google_calendar.get_calendar_service')
    async def test_check_calendar_availability_free(self, mock_service):
        """Test availability check when time slot is free"""
        mock_calendar_service = MagicMock()
        mock_calendar_service.events().list().execute.return_value = {'items': []}
        mock_service.return_value = mock_calendar_service

        test_time = datetime.now(UTC) + timedelta(hours=1)
        result = await check_calendar_availability(test_time, 30)
        assert result is True

    @pytest.mark.asyncio
    @patch('app.services.google_calendar.get_calendar_service')
    async def test_check_calendar_availability_busy(self, mock_service):
        """Test availability check when time slot is busy"""
        mock_calendar_service = MagicMock()
        mock_calendar_service.events().list().execute.return_value = {
            'items': [
                {
                    'id': 'existing_event',
                    'summary': 'Existing appointment',
                    'status': 'confirmed'
                }
            ]
        }
        mock_service.return_value = mock_calendar_service

        test_time = datetime.now(UTC) + timedelta(hours=1)
        result = await check_calendar_availability(test_time, 30)
        assert result is False

    @pytest.mark.asyncio
    @patch('app.services.google_calendar.get_calendar_service')
    async def test_check_calendar_availability_cancelled_event(self, mock_service):
        """Test availability check ignoring cancelled events"""
        mock_calendar_service = MagicMock()
        mock_calendar_service.events().list().execute.return_value = {
            'items': [
                {
                    'id': 'cancelled_event',
                    'summary': 'Cancelled appointment',
                    'status': 'cancelled'
                }
            ]
        }
        mock_service.return_value = mock_calendar_service

        test_time = datetime.now(UTC) + timedelta(hours=1)
        result = await check_calendar_availability(test_time, 30)
        assert result is True


class TestCalendarIntegrationFlow:
    """Test complete calendar integration flow"""

    @pytest.mark.asyncio
    @patch('app.services.google_calendar.get_calendar_service')
    async def test_booking_with_calendar_integration(self, mock_service, sample_event_data):
        """Test booking flow with calendar integration"""
        # Mock successful calendar service
        mock_calendar_service = MagicMock()
        mock_service.return_value = mock_calendar_service

        # Mock availability check - free
        mock_calendar_service.events().list().execute.return_value = {'items': []}

        # Check availability
        is_available = await check_calendar_availability(
            sample_event_data['starts_at_utc'],
            sample_event_data['duration_min']
        )
        assert is_available is True

        # Mock event creation
        mock_event_response = {
            'id': 'new_event_123',
            'htmlLink': 'https://calendar.google.com/event?eid=new123'
        }
        mock_calendar_service.events().insert().execute.return_value = mock_event_response

        # Create event
        result = await create_calendar_event(**sample_event_data)
        assert result is not None
        assert result['event_id'] == 'new_event_123'

    @pytest.mark.asyncio
    async def test_booking_with_calendar_disabled(self, sample_event_data):
        """Test booking flow with calendar integration disabled"""
        # When calendar is disabled, operations should return None gracefully
        result = await create_calendar_event(**sample_event_data)
        assert result is None

        availability = await check_calendar_availability(
            sample_event_data['starts_at_utc'],
            sample_event_data['duration_min']
        )
        assert availability is True  # Assume available when can't check

        delete_result = await delete_calendar_event('test_event')
        assert delete_result is False
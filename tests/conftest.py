#!/usr/bin/env python3
"""
Pytest configuration and shared fixtures for the test suite.
"""

import pytest
import os
import sys
from unittest.mock import patch

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up test environment variables"""
    test_env = {
        'APP_ENV': 'testing',
        'POSTGRES_HOST': 'localhost',
        'POSTGRES_PORT': '5432',
        'POSTGRES_DB': 'test_bella',
        'POSTGRES_USER': 'test_user',
        'POSTGRES_PASSWORD': 'test_password',
        'OPENAI_API_KEY': 'test_key',
        'OPENAI_MODEL': 'gpt-4o-mini',
        'BELLA_API_KEY': 'test_api_key',
        'REDIS_URL': '',  # Disable Redis in tests
        'GOOGLE_CALENDAR_ENABLED': 'false',
        'TWILIO_AUTH_TOKEN': 'test_token',
        'TWILIO_ACCOUNT_SID': 'test_sid',
        'TWILIO_PHONE_NUMBER': '+15551234567',
    }

    # Apply test environment
    with patch.dict(os.environ, test_env):
        yield


@pytest.fixture
def mock_database():
    """Mock database connections for testing"""
    with patch('app.database.get_async_session') as mock_session:
        yield mock_session


@pytest.fixture
def mock_redis():
    """Mock Redis connections for testing"""
    with patch('app.services.redis_session.get_redis_client') as mock_redis:
        mock_redis.return_value = None  # Simulate Redis disabled
        yield mock_redis


@pytest.fixture
def mock_openai():
    """Mock OpenAI API calls for testing"""
    with patch('app.services.llm.openai_client') as mock_client:
        # Mock a typical LLM response
        mock_response = type('MockResponse', (), {
            'choices': [
                type('MockChoice', (), {
                    'message': type('MockMessage', (), {
                        'content': '{"full_name": "John Smith", "mobile": "+14165551234", "starts_at": "2025-09-30T14:00:00", "duration_min": 30, "notes": "Regular appointment"}'
                    })()
                })()
            ]
        })()
        mock_client.chat.completions.create.return_value = mock_response
        yield mock_client


@pytest.fixture
def mock_google_calendar():
    """Mock Google Calendar integration for testing"""
    with patch('app.services.google_calendar.create_calendar_event') as mock_calendar:
        mock_calendar.return_value = None  # Simulate calendar disabled
        yield mock_calendar


@pytest.fixture
def sample_call_data():
    """Sample Twilio call data for testing"""
    return {
        'CallSid': 'TEST_CALL_SID_123',
        'From': '+14165551234',
        'To': '+15551234567',
        'AccountSid': 'TEST_ACCOUNT_SID',
        'Direction': 'inbound',
        'CallerCountry': 'CA',
        'CallerState': 'ON',
        'CallerCity': 'Toronto',
    }


@pytest.fixture
def sample_speech_data():
    """Sample speech recognition data for testing"""
    return {
        'SpeechResult': 'John Smith, tomorrow at 2 PM, 416-555-9876',
        'Confidence': '0.95',
        'CallSid': 'TEST_CALL_SID_123',
    }


@pytest.fixture
def sample_appointment_data():
    """Sample appointment data for testing"""
    return {
        'full_name': 'John Smith',
        'mobile': '+14165551234',
        'starts_at': '2025-09-30T14:00:00-04:00',
        'duration_min': 30,
        'notes': 'Regular appointment scheduled via voice'
    }
#!/usr/bin/env python3
"""
Voice integration tests for Twilio webhook endpoints.
Tests the voice call flow without making actual external calls.
"""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock

# Add app to Python path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client"""
    from app.main import app
    return TestClient(app)


@pytest.mark.essential
@pytest.mark.integration
def test_voice_entry_with_caller_id(client):
    """Test voice entry with valid caller ID"""
    response = client.post("/twilio/voice", data={
        "CallSid": "TEST_CALL_001",
        "From": "+14165551234",
        "AccountSid": "TEST_ACCOUNT"
    })

    assert response.status_code == 200
    assert "<Response>" in response.text
    assert "<Gather" in response.text
    assert "Thanks for calling" in response.text


@pytest.mark.essential
@pytest.mark.integration
def test_voice_entry_without_caller_id(client):
    """Test voice entry without caller ID"""
    response = client.post("/twilio/voice", data={
        "CallSid": "TEST_CALL_002",
        "From": "",
        "AccountSid": "TEST_ACCOUNT"
    })

    assert response.status_code == 200
    assert "<Response>" in response.text
    assert "<Gather" in response.text


@pytest.mark.essential
@pytest.mark.integration
def test_voice_entry_invalid_phone(client):
    """Test voice entry with invalid phone number"""
    response = client.post("/twilio/voice", data={
        "CallSid": "TEST_CALL_003",
        "From": "invalid_phone",
        "AccountSid": "TEST_ACCOUNT"
    })

    assert response.status_code == 200
    assert "<Response>" in response.text


@patch('app.services.redis_session.get_redis_client')
@pytest.mark.essential
@pytest.mark.integration
def test_voice_with_redis_disabled(mock_redis, client):
    """Test voice functionality when Redis is disabled"""
    # Mock Redis as disabled
    mock_redis.return_value = None

    response = client.post("/twilio/voice", data={
        "CallSid": "TEST_CALL_REDIS",
        "From": "+14165551234",
        "AccountSid": "TEST_ACCOUNT"
    })

    assert response.status_code == 200
    assert "<Response>" in response.text


@pytest.mark.essential
@pytest.mark.integration
def test_voice_collect_endpoint(client):
    """Test voice collection endpoint"""
    # First establish a session
    client.post("/twilio/voice", data={
        "CallSid": "TEST_COLLECT_001",
        "From": "+14165551234",
        "AccountSid": "TEST_ACCOUNT"
    })

    # Then test collection
    response = client.post("/twilio/voice/collect", data={
        "CallSid": "TEST_COLLECT_001",
        "SpeechResult": "John Smith",
        "Confidence": "0.95"
    })

    assert response.status_code == 200
    assert "<Response>" in response.text


@pytest.mark.essential
@pytest.mark.integration
def test_voice_collect_with_appointment_data(client):
    """Test voice collection with full appointment data"""
    # Establish session
    client.post("/twilio/voice", data={
        "CallSid": "TEST_COLLECT_002",
        "From": "+14165551234",
        "AccountSid": "TEST_ACCOUNT"
    })

    # Submit appointment details
    response = client.post("/twilio/voice/collect", data={
        "CallSid": "TEST_COLLECT_002",
        "SpeechResult": "John Smith, tomorrow at 2 PM, 416-555-9876",
        "Confidence": "0.85"
    })

    assert response.status_code == 200
    assert "<Response>" in response.text


@patch('app.services.booking.book_from_transcript')
@pytest.mark.essential
@pytest.mark.integration
async def test_voice_collect_booking_success(mock_booking, client):
    """Test successful appointment booking flow"""
    # Mock successful booking
    mock_result = MagicMock()
    mock_result.created = True
    mock_result.message_for_caller = "Appointment booked successfully!"
    mock_booking.return_value = mock_result

    # Establish session
    client.post("/twilio/voice", data={
        "CallSid": "TEST_BOOKING_001",
        "From": "+14165551234",
        "AccountSid": "TEST_ACCOUNT"
    })

    # Submit booking request
    response = client.post("/twilio/voice/collect", data={
        "CallSid": "TEST_BOOKING_001",
        "SpeechResult": "John Smith, tomorrow at 2 PM, 416-555-9876",
        "Confidence": "0.90"
    })

    assert response.status_code == 200
    assert "<Response>" in response.text


@pytest.mark.integration
@pytest.mark.slow
def test_voice_timeout_handling(client):
    """Test voice endpoint timeout handling"""
    response = client.post("/twilio/voice/collect", data={
        "CallSid": "TEST_TIMEOUT_001",
        "SpeechResult": "",  # Empty speech result (timeout)
        "Confidence": "0.0"
    })

    assert response.status_code == 200
    assert "<Response>" in response.text
    assert "<Say" in response.text  # Should have fallback speech


@pytest.mark.essential
@pytest.mark.integration
def test_voice_error_handling(client):
    """Test voice endpoint error handling"""
    response = client.post("/twilio/voice/collect", data={
        "CallSid": "",  # Invalid call SID
        "SpeechResult": "test",
    })

    # Should handle gracefully, not crash
    assert response.status_code in [200, 400, 422]


@patch('app.services.google_calendar.create_calendar_event')
@pytest.mark.essential
@pytest.mark.integration
async def test_voice_with_calendar_integration(mock_calendar, client):
    """Test voice flow with Google Calendar integration"""
    # Mock calendar integration (disabled by default)
    mock_calendar.return_value = None

    response = client.post("/twilio/voice", data={
        "CallSid": "TEST_CALENDAR_001",
        "From": "+14165551234",
        "AccountSid": "TEST_ACCOUNT"
    })

    assert response.status_code == 200
    assert "<Response>" in response.text


class TestVoiceFlowIntegration:
    """Integration tests for complete voice call flows"""

    @pytest.mark.essential
    @pytest.mark.integration
    def test_complete_happy_path(self, client):
        """Test a complete successful call flow"""
        call_sid = "TEST_HAPPY_PATH"

        # 1. Initial call
        response1 = client.post("/twilio/voice", data={
            "CallSid": call_sid,
            "From": "+14165551234",
            "AccountSid": "TEST_ACCOUNT"
        })
        assert response1.status_code == 200
        assert "Thanks for calling" in response1.text

        # 2. Provide name
        response2 = client.post("/twilio/voice/collect", data={
            "CallSid": call_sid,
            "SpeechResult": "John Smith",
            "Confidence": "0.95"
        })
        assert response2.status_code == 200

        # 3. Provide appointment details
        response3 = client.post("/twilio/voice/collect", data={
            "CallSid": call_sid,
            "SpeechResult": "tomorrow at 2 PM",
            "Confidence": "0.90"
        })
        assert response3.status_code == 200

    @pytest.mark.essential
    @pytest.mark.integration
    def test_call_with_retries(self, client):
        """Test call flow with speech recognition retries"""
        call_sid = "TEST_RETRIES"

        # Initial call
        client.post("/twilio/voice", data={
            "CallSid": call_sid,
            "From": "+14165551234",
            "AccountSid": "TEST_ACCOUNT"
        })

        # First attempt - low confidence
        response1 = client.post("/twilio/voice/collect", data={
            "CallSid": call_sid,
            "SpeechResult": "unintelligible",
            "Confidence": "0.3"
        })
        assert response1.status_code == 200
        assert "<Gather" in response1.text  # Should ask again

        # Second attempt - good confidence
        response2 = client.post("/twilio/voice/collect", data={
            "CallSid": call_sid,
            "SpeechResult": "John Smith",
            "Confidence": "0.9"
        })
        assert response2.status_code == 200
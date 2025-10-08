#!/usr/bin/env python3
"""
Mock external services for faster testing.
Reduces test execution time by avoiding real API calls.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, Optional
import json
import time
import httpx


class TwilioMock:
    """Mock Twilio API calls for testing"""

    def __init__(self):
        self.call_responses = {}
        self.webhook_requests = []

    def mock_twiml_response(self, content: str = None) -> str:
        """Generate mock TwiML response"""
        if content is None:
            content = '<Say voice="alice" language="en-CA">Hello, test response</Say>'

        return f'<?xml version="1.0" encoding="UTF-8"?>\n<Response>\n  {content}\n</Response>'

    def mock_webhook_request(self, call_sid: str, **kwargs) -> Dict[str, Any]:
        """Mock Twilio webhook request data"""
        default_data = {
            "CallSid": call_sid,
            "From": "+14165551234",
            "To": "+15559876543",
            "AccountSid": "ACtest123",
            "Direction": "inbound",
            "CallerCountry": "CA",
            "CallerState": "ON",
            "CallerCity": "Toronto"
        }
        default_data.update(kwargs)
        return default_data

    def record_webhook_call(self, call_sid: str, data: Dict[str, Any]):
        """Record webhook call for test verification"""
        self.webhook_requests.append({
            "call_sid": call_sid,
            "data": data,
            "timestamp": time.time()
        })


class OpenAIMock:
    """Mock OpenAI API calls for testing"""

    def __init__(self):
        self.api_calls = []

    def mock_completion_response(self, text: str) -> Dict[str, Any]:
        """Generate mock completion response"""
        return {
            "choices": [
                {
                    "message": {
                        "content": text
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "total_tokens": len(text.split())
            }
        }

    def mock_whisper_response(self, text: str) -> Dict[str, Any]:
        """Generate mock Whisper transcription response"""
        return {
            "text": text,
            "confidence": 0.95
        }


class GoogleCalendarMock:
    """Mock Google Calendar API calls for testing"""

    def __init__(self):
        self.events = []
        self.service_available = True

    def mock_service_unavailable(self):
        """Simulate service unavailable for testing error handling"""
        self.service_available = False

    def mock_create_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock event creation"""
        if not self.service_available:
            raise Exception("Service unavailable")

        event = {
            "id": f"test_event_{len(self.events)}",
            "summary": event_data.get("summary", "Test Event"),
            "start": event_data.get("start", {"dateTime": "2024-01-01T10:00:00Z"}),
            "end": event_data.get("end", {"dateTime": "2024-01-01T11:00:00Z"}),
            "htmlLink": "https://calendar.google.com/test"
        }
        self.events.append(event)
        return event


class RedisMock:
    """Mock Redis operations for testing"""

    def __init__(self):
        self.data = {}
        self.available = True

    def mock_unavailable(self):
        """Simulate Redis unavailable for testing fallback"""
        self.available = False

    def get(self, key: str) -> Optional[str]:
        """Mock Redis GET"""
        if not self.available:
            raise ConnectionError("Redis unavailable")
        return self.data.get(key)

    def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """Mock Redis SET"""
        if not self.available:
            raise ConnectionError("Redis unavailable")
        self.data[key] = value
        return True

    def delete(self, key: str) -> int:
        """Mock Redis DELETE"""
        if not self.available:
            raise ConnectionError("Redis unavailable")
        if key in self.data:
            del self.data[key]
            return 1
        return 0


class HTTPMock:
    """Mock HTTP client responses for testing"""

    def __init__(self):
        self.responses = {}
        self.requests = []

    def add_response(self, url: str, response_data: Dict[str, Any], status_code: int = 200):
        """Add mock response for specific URL"""
        self.responses[url] = {
            "status_code": status_code,
            "data": response_data,
            "headers": {"Content-Type": "application/json"}
        }

    def mock_request(self, method: str, url: str, **kwargs) -> Mock:
        """Mock HTTP request"""
        self.requests.append({
            "method": method,
            "url": url,
            "kwargs": kwargs,
            "timestamp": time.time()
        })

        if url in self.responses:
            response_config = self.responses[url]
            mock_response = Mock()
            mock_response.status_code = response_config["status_code"]
            mock_response.json.return_value = response_config["data"]
            mock_response.text = json.dumps(response_config["data"])
            mock_response.headers = response_config["headers"]
            mock_response.elapsed.total_seconds.return_value = 0.1  # Fast mock response
            return mock_response

        # Default 404 response
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"error": "Not found"}
        mock_response.text = '{"error": "Not found"}'
        mock_response.elapsed.total_seconds.return_value = 0.1
        return mock_response


# Global mock instances for test session
twilio_mock = TwilioMock()
openai_mock = OpenAIMock()
calendar_mock = GoogleCalendarMock()
redis_mock = RedisMock()
http_mock = HTTPMock()


@pytest.fixture
def mock_twilio():
    """Fixture to mock Twilio API calls"""
    return twilio_mock


@pytest.fixture
def mock_openai():
    """Fixture to mock OpenAI API calls"""
    with patch('openai.ChatCompletion.create') as mock_create:
        mock_create.return_value = openai_mock.mock_completion_response("Test response")
        yield openai_mock


@pytest.fixture
def mock_google_calendar():
    """Fixture to mock Google Calendar API"""
    return calendar_mock


@pytest.fixture
def mock_redis():
    """Fixture to mock Redis operations"""
    with patch('app.services.redis_session.get_redis_client') as mock_client:
        # Create async mock
        async_mock = AsyncMock()
        async_mock.get = AsyncMock(side_effect=redis_mock.get)
        async_mock.set = AsyncMock(side_effect=redis_mock.set)
        async_mock.delete = AsyncMock(side_effect=redis_mock.delete)
        mock_client.return_value = async_mock
        yield redis_mock


@pytest.fixture
def mock_http_client():
    """Fixture to mock HTTP client"""
    with patch('httpx.Client.request') as mock_request, \
         patch('httpx.AsyncClient.request') as mock_async_request:

        mock_request.side_effect = lambda method, url, **kwargs: http_mock.mock_request(method, url, **kwargs)
        mock_async_request.side_effect = lambda method, url, **kwargs: http_mock.mock_request(method, url, **kwargs)

        yield http_mock


@pytest.fixture
def fast_mocks(mock_twilio, mock_redis, mock_http_client):
    """Combination fixture for fastest possible tests"""
    # Reset all mocks
    twilio_mock.call_responses.clear()
    twilio_mock.webhook_requests.clear()
    redis_mock.data.clear()
    redis_mock.available = True
    http_mock.responses.clear()
    http_mock.requests.clear()

    return {
        "twilio": mock_twilio,
        "redis": mock_redis,
        "http": mock_http_client
    }


# Automatic mock patches for smoke tests
@pytest.fixture(autouse=True, scope="function")
def auto_mock_for_smoke_tests(request):
    """Automatically mock external services for smoke tests"""
    if request.node.get_closest_marker("smoke"):
        # Automatically mock all external services for smoke tests
        with patch('app.services.redis_session.get_redis_client') as mock_redis_client, \
             patch('httpx.Client') as mock_http, \
             patch('httpx.AsyncClient') as mock_async_http:

            # Mock Redis
            async_redis_mock = AsyncMock()
            async_redis_mock.get = AsyncMock(return_value=None)
            async_redis_mock.set = AsyncMock(return_value=True)
            async_redis_mock.delete = AsyncMock(return_value=1)
            mock_redis_client.return_value = async_redis_mock

            # Mock HTTP clients
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = '{"status": "ok"}'
            mock_response.json.return_value = {"status": "ok"}
            mock_response.elapsed.total_seconds.return_value = 0.05

            mock_http.return_value.__enter__.return_value.post.return_value = mock_response
            mock_http.return_value.__enter__.return_value.get.return_value = mock_response
            mock_async_http.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            mock_async_http.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            yield
    else:
        yield


# Performance optimization utilities
class TestDataFactory:
    """Factory for generating test data quickly"""

    @staticmethod
    def generate_call_session(call_sid: str = None) -> Dict[str, Any]:
        """Generate test call session data"""
        if call_sid is None:
            call_sid = f"TEST_{int(time.time())}"

        return {
            "call_sid": call_sid,
            "caller_phone": "+14165551234",
            "step": "collect_name",
            "name": None,
            "phone": None,
            "preferred_time": None,
            "retry_count": 0,
            "created_at": time.time()
        }

    @staticmethod
    def generate_appointment_data() -> Dict[str, Any]:
        """Generate test appointment data"""
        return {
            "name": "Test User",
            "phone": "+14165551234",
            "preferred_time": "tomorrow at 2 PM",
            "notes": "Test appointment"
        }

    @staticmethod
    def generate_speech_inputs() -> Dict[str, str]:
        """Generate common speech input variations for testing"""
        return {
            "clear_name": "My name is John Smith",
            "unclear_name": "um my name is uh John Smith",
            "clear_phone": "My phone number is 416 555 1234",
            "unclear_phone": "my number is four one six five five five one two three four",
            "clear_time": "I would like an appointment tomorrow at 2 PM",
            "unclear_time": "um maybe tomorrow sometime around 2 o'clock"
        }


# Session-scoped fixtures for expensive setup
@pytest.fixture(scope="session")
def test_data_factory():
    """Session-scoped test data factory"""
    return TestDataFactory()


# Marker-based automatic optimization
def pytest_collection_modifyitems(config, items):
    """Automatically optimize test collection based on markers"""
    for item in items:
        # Add timeout based on markers
        if item.get_closest_marker("smoke"):
            item.add_marker(pytest.mark.timeout(10))  # 10 second max for smoke tests
        elif item.get_closest_marker("essential"):
            item.add_marker(pytest.mark.timeout(30))  # 30 second max for essential tests
        elif item.get_closest_marker("slow"):
            item.add_marker(pytest.mark.timeout(300))  # 5 minute max for slow tests
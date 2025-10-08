#!/usr/bin/env python3
"""
Optimized pytest configuration and shared fixtures for fast test execution.
Includes automatic mocking, performance monitoring, and smart test optimization.
"""

import pytest
import pytest_asyncio
import os
import sys
import time
import asyncio
from unittest.mock import patch, Mock, AsyncMock
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Configure pytest-asyncio
pytest_asyncio.asyncio_mode = "auto"

# Test database configuration
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up optimized test environment variables"""
    test_env = {
        'APP_ENV': 'testing',
        'DATABASE_URL': TEST_DATABASE_URL,  # Use in-memory SQLite for speed
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


# Performance monitoring and auto-optimization
@pytest.fixture(autouse=True)
def auto_mock_for_fast_tests(request):
    """Automatically mock external services for smoke and unit tests"""
    node = request.node

    # Auto-mock for smoke and unit tests
    if node.get_closest_marker("smoke") or node.get_closest_marker("unit"):
        patches = []

        # Mock Redis
        redis_patch = patch('app.services.redis_session.get_redis_client')
        redis_mock = redis_patch.start()
        async_redis = AsyncMock()
        async_redis.get = AsyncMock(return_value=None)
        async_redis.set = AsyncMock(return_value=True)
        async_redis.delete = AsyncMock(return_value=1)
        redis_mock.return_value = async_redis
        patches.append(redis_patch)

        # Mock HTTP clients for external calls
        http_patch = patch('httpx.AsyncClient')
        http_mock = http_patch.start()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '{"status": "ok"}'
        mock_response.json.return_value = {"status": "ok"}
        mock_response.elapsed.total_seconds.return_value = 0.01
        http_mock.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
        http_mock.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        patches.append(http_patch)

        # Mock Google Calendar
        calendar_patch = patch('app.services.google_calendar.create_calendar_event')
        calendar_mock = calendar_patch.start()
        calendar_mock.return_value = {"id": "test_event", "htmlLink": "https://test.com"}
        patches.append(calendar_patch)

        yield

        # Clean up patches
        for patch_obj in patches:
            patch_obj.stop()
    else:
        yield


@pytest.fixture(autouse=True)
def monitor_test_performance(request):
    """Monitor test performance and warn about slow tests"""
    start_time = time.time()
    yield
    end_time = time.time()
    duration = end_time - start_time

    node = request.node
    test_name = node.name

    # Performance thresholds based on markers
    if node.get_closest_marker("smoke") and duration > 1.0:
        print(f"⚠️ Smoke test {test_name} took {duration:.2f}s (should be < 1s)")
    elif node.get_closest_marker("essential") and duration > 5.0:
        print(f"⚠️ Essential test {test_name} took {duration:.2f}s (should be < 5s)")
    elif not node.get_closest_marker("slow") and duration > 10.0:
        print(f"⚠️ Test {test_name} took {duration:.2f}s (consider marking as @pytest.mark.slow)")


# Pytest configuration hooks
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line("markers", "smoke: Quick validation tests (< 30 seconds total)")
    config.addinivalue_line("markers", "essential: Core functionality tests (< 2 minutes total)")
    config.addinivalue_line("markers", "slow: Long-running tests (> 30 seconds each)")
    config.addinivalue_line("markers", "production: Production environment tests")
    config.addinivalue_line("markers", "integration: Integration tests with external services")
    config.addinivalue_line("markers", "unit: Pure unit tests with no external dependencies")


def pytest_collection_modifyitems(config, items):
    """Optimize test collection and ordering"""
    # Sort tests by execution speed (smoke first, slow last)
    def test_priority(item):
        if item.get_closest_marker("smoke"):
            return 0
        elif item.get_closest_marker("essential"):
            return 1
        elif item.get_closest_marker("integration"):
            return 2
        elif item.get_closest_marker("slow"):
            return 3
        else:
            return 1  # Default to essential priority

    items[:] = sorted(items, key=test_priority)


def pytest_runtest_setup(item):
    """Setup logic for individual test runs"""
    # Skip production tests unless explicitly requested
    if item.get_closest_marker("production"):
        if not (os.environ.get("CI") or os.environ.get("RUN_PRODUCTION_TESTS")):
            pytest.skip("Production tests skipped (set RUN_PRODUCTION_TESTS=1 to run)")
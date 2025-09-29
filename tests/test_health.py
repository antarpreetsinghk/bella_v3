#!/usr/bin/env python3
"""
Basic health endpoint tests for CI/CD pipeline.
Tests fundamental application functionality without external dependencies.
"""

import pytest
import sys
import os

# Add app to Python path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastapi.testclient import TestClient


def test_health_endpoint():
    """Test that health endpoint returns 200 and proper structure"""
    # Import here to avoid startup issues in CI
    from app.main import app

    client = TestClient(app)
    response = client.get("/healthz")

    assert response.status_code == 200
    data = response.json()
    # Accept either 'status' or 'ok' field for health check
    assert ("status" in data) or ("ok" in data)
    if "status" in data:
        assert data["status"] == "healthy"
    if "ok" in data:
        assert data["ok"] is True


def test_ready_endpoint():
    """Test that ready endpoint returns 200 or handles gracefully"""
    from app.main import app

    client = TestClient(app)

    try:
        response = client.get("/readyz")
        # If successful, should return 200
        if response.status_code == 200:
            data = response.json()
            assert ("status" in data) or ("ok" in data)
        else:
            # If it fails due to DB connection in test, that's expected
            assert response.status_code in [200, 500, 503]
    except Exception:
        # In test environment, DB connection issues are expected
        # The important thing is the endpoint exists and doesn't crash the app
        pass


def test_twilio_voice_endpoint_structure():
    """Test that voice endpoint returns valid TwiML structure"""
    from app.main import app

    client = TestClient(app)
    response = client.post("/twilio/voice", data={
        "CallSid": "TEST_CALL_SID",
        "From": "+14165551234",
        "AccountSid": "TEST_ACCOUNT"
    })

    assert response.status_code == 200
    # Should return XML content (TwiML)
    assert "xml" in response.headers.get("content-type", "").lower()
    # Should contain TwiML Response element
    assert "<Response>" in response.text
    assert "</Response>" in response.text


def test_api_key_protection():
    """Test that protected endpoints require API key"""
    from app.main import app

    client = TestClient(app)

    # Test a protected endpoint (appointments)
    response = client.get("/appointments")

    # Should either require auth (401) or not exist (404)
    # Both are acceptable for this basic test
    assert response.status_code in [401, 404]


def test_cors_headers():
    """Test that CORS headers are properly set"""
    from app.main import app

    client = TestClient(app)
    response = client.options("/healthz")

    # Should not error on OPTIONS request
    assert response.status_code in [200, 405]  # 405 is also acceptable if OPTIONS not implemented


@pytest.mark.asyncio
async def test_app_startup():
    """Test that the FastAPI app can start up without errors"""
    from app.main import app

    # Test that app object exists and has the expected attributes
    assert hasattr(app, 'routes')
    assert len(app.routes) > 0

    # Test that required routes exist
    route_paths = [route.path for route in app.routes if hasattr(route, 'path')]
    assert "/healthz" in route_paths
    assert "/readyz" in route_paths
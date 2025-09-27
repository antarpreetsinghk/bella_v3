#!/usr/bin/env python3
"""
Test Twilio call flow without signature validation.
"""
import requests
import json

# Test configuration
ALB_URL = "http://bella-alb-1924818779.ca-central-1.elb.amazonaws.com"
TWILIO_AUTH_TOKEN = "11be258d711c0741531b6d4cddc8b0ae"  # From secrets

def test_voice_endpoint():
    """Test the /twilio/voice endpoint directly (bypasses signature validation in dev)."""

    print("🔍 Testing Twilio voice endpoint...")

    # Test data that Twilio would send
    test_data = {
        "CallSid": "CAtest123456789",
        "From": "+15551234567",
        "To": "+15559876543",
        "CallStatus": "ringing",
        "AccountSid": "ACtest123",
        "ApiVersion": "2010-04-01"
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "TwilioProxy/1.1"
    }

    try:
        # Test voice entry point
        print(f"📞 Testing {ALB_URL}/twilio/voice")
        response = requests.post(
            f"{ALB_URL}/twilio/voice",
            data=test_data,
            headers=headers,
            timeout=10
        )

        print(f"Status: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type', 'Not Set')}")
        print(f"Response: {response.text}")

        if response.status_code == 403:
            print("❌ Signature validation blocking test (expected)")
            print("💡 This is normal - Twilio webhooks require valid signatures")
            return False
        elif response.status_code == 200:
            print("✅ Endpoint responding correctly")
            return True
        else:
            print(f"⚠️  Unexpected status code: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Request failed: {e}")
        return False

def test_health_endpoints():
    """Test health and metrics endpoints."""

    print("\n🏥 Testing health endpoints...")

    endpoints = ["/healthz", "/metrics"]

    for endpoint in endpoints:
        try:
            print(f"Testing {ALB_URL}{endpoint}")
            response = requests.get(f"{ALB_URL}{endpoint}", timeout=5)

            if response.status_code == 200:
                print(f"✅ {endpoint}: OK")
                if endpoint == "/metrics":
                    try:
                        data = response.json()
                        print(f"   Active sessions: {data.get('performance', {}).get('active_sessions', 'N/A')}")
                        print(f"   Total requests: {data.get('performance', {}).get('total_requests', 'N/A')}")
                    except:
                        print(f"   Response length: {len(response.text)} chars")
                else:
                    print(f"   Response: {response.text}")
            else:
                print(f"❌ {endpoint}: {response.status_code}")

        except Exception as e:
            print(f"❌ {endpoint}: {e}")

def simulate_call_flow():
    """Simulate a complete call flow locally."""

    print("\n🎭 Simulating call flow logic...")

    # This would be the logic flow (without Twilio)
    steps = [
        "1. Caller dials Twilio number",
        "2. Twilio sends webhook to /twilio/voice",
        "3. App responds with TwiML to gather name",
        "4. Caller speaks name",
        "5. Twilio sends to /twilio/voice/collect",
        "6. App asks for phone number",
        "7. Caller provides phone",
        "8. App asks for appointment time",
        "9. Caller provides time",
        "10. App confirms details",
        "11. Caller confirms",
        "12. App books appointment and ends call"
    ]

    for step in steps:
        print(f"   {step}")

    print("\n🔧 Current Issue: Signature validation prevents testing")
    print("💡 Solutions:")
    print("   1. Use real Twilio phone number with valid webhook")
    print("   2. Temporarily disable signature validation for testing")
    print("   3. Use Twilio CLI to simulate webhooks")

if __name__ == "__main__":
    print("🚀 Bella V3 Call Flow Test")
    print("=" * 50)

    # Test health first
    test_health_endpoints()

    # Test voice endpoint
    test_voice_endpoint()

    # Show call flow
    simulate_call_flow()

    print("\n" + "=" * 50)
    print("✅ Test complete")
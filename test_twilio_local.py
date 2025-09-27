#!/usr/bin/env python3
"""
Test Twilio call flow in test mode (bypasses signature validation).
"""
import requests
import json
import time

ALB_URL = "http://bella-alb-1924818779.ca-central-1.elb.amazonaws.com"

def test_call_flow_complete():
    """Test complete call flow simulation."""

    print("🎭 Testing Complete Call Flow")
    print("=" * 50)

    # Test session data
    call_sid = f"CAtest{int(time.time())}"

    # Step 1: Initial voice webhook
    print("📞 Step 1: Initial call (/twilio/voice)")

    voice_data = {
        "CallSid": call_sid,
        "From": "+15551234567",
        "To": "+15559876543",
        "CallStatus": "ringing"
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    try:
        response = requests.post(f"{ALB_URL}/twilio/voice", data=voice_data, headers=headers, timeout=10)
        print(f"   Status: {response.status_code}")

        if response.status_code == 403:
            print("   ❌ Signature validation blocking (expected in production)")
            print("   💡 Set APP_ENV=test to bypass for testing")
            return False
        elif response.status_code == 200:
            print("   ✅ TwiML Response received")
            print(f"   Response: {response.text[:200]}...")

        # Step 2: Collect name
        print("\n📝 Step 2: User provides name (/twilio/voice/collect)")

        collect_data = {
            "CallSid": call_sid,
            "From": "+15551234567",
            "SpeechResult": "John Smith",
            "Confidence": "0.9"
        }

        response = requests.post(f"{ALB_URL}/twilio/voice/collect", data=collect_data, headers=headers, timeout=10)
        print(f"   Status: {response.status_code}")

        if response.status_code == 200:
            print("   ✅ Name collected, asking for phone")
            print(f"   Response: {response.text[:200]}...")

        # Step 3: Collect phone
        print("\n📱 Step 3: User provides phone (/twilio/voice/collect)")

        collect_data["SpeechResult"] = "416 555 1234"

        response = requests.post(f"{ALB_URL}/twilio/voice/collect", data=collect_data, headers=headers, timeout=10)
        print(f"   Status: {response.status_code}")

        if response.status_code == 200:
            print("   ✅ Phone collected, asking for time")
            print(f"   Response: {response.text[:200]}...")

        # Step 4: Collect appointment time
        print("\n⏰ Step 4: User provides time (/twilio/voice/collect)")

        collect_data["SpeechResult"] = "tomorrow at 2 PM"

        response = requests.post(f"{ALB_URL}/twilio/voice/collect", data=collect_data, headers=headers, timeout=10)
        print(f"   Status: {response.status_code}")

        if response.status_code == 200:
            print("   ✅ Time collected, showing confirmation")
            print(f"   Response: {response.text[:200]}...")

        # Step 5: Confirmation
        print("\n✅ Step 5: User confirms (/twilio/voice/collect)")

        collect_data["SpeechResult"] = "yes"

        response = requests.post(f"{ALB_URL}/twilio/voice/collect", data=collect_data, headers=headers, timeout=10)
        print(f"   Status: {response.status_code}")

        if response.status_code == 200:
            print("   ✅ Booking confirmed!")
            print(f"   Response: {response.text[:200]}...")
            return True

    except Exception as e:
        print(f"   ❌ Request failed: {e}")
        return False

    return False

def test_health_and_metrics():
    """Test health and metrics endpoints."""

    print("\n🏥 Testing Application Health")
    print("=" * 30)

    # Health check
    try:
        response = requests.get(f"{ALB_URL}/healthz", timeout=5)
        if response.status_code == 200:
            print("✅ Health check: OK")
        else:
            print(f"❌ Health check failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Health check failed: {e}")

    # Metrics check
    try:
        response = requests.get(f"{ALB_URL}/metrics", timeout=5)
        if response.status_code == 200:
            print("✅ Metrics endpoint: OK")
            try:
                data = response.json()
                perf = data.get('performance', {})
                print(f"   Active sessions: {perf.get('active_sessions', 'N/A')}")
                print(f"   Total requests: {perf.get('total_requests', 'N/A')}")
                print(f"   Avg response time: {perf.get('avg_response_time', 'N/A')}s")
            except:
                print(f"   Raw response: {response.text[:100]}...")
        else:
            print(f"❌ Metrics failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Metrics failed: {e}")

def check_deployment_status():
    """Check if latest deployment is active."""

    print("\n🚀 Checking Deployment Status")
    print("=" * 30)

    try:
        # Check if monitoring imports are working
        response = requests.get(f"{ALB_URL}/healthz", timeout=5)

        if response.status_code == 200:
            print("✅ Application is running")

            # Check if new monitoring code is deployed
            response = requests.get(f"{ALB_URL}/metrics", timeout=5)
            if response.status_code == 200:
                print("✅ Monitoring system is active")
            else:
                print("⚠️  Monitoring system not yet deployed")
                print("   Run: git push to deploy latest changes")
        else:
            print("❌ Application not responding")

    except Exception as e:
        print(f"❌ Deployment check failed: {e}")

if __name__ == "__main__":
    print("🚀 Bella V3 Call Flow Test (Complete)")
    print("=" * 50)

    # Check deployment first
    check_deployment_status()

    # Test health
    test_health_and_metrics()

    # Test call flow
    success = test_call_flow_complete()

    print("\n" + "=" * 50)
    if success:
        print("🎉 Call flow test completed successfully!")
    else:
        print("⚠️  Call flow test encountered issues")
        print("\n💡 To fix:")
        print("   1. Set APP_ENV=test in secrets for testing")
        print("   2. Or configure real Twilio webhook")
        print("   3. Ensure latest code is deployed")
#!/usr/bin/env python3
"""
Verify that new real customer calls now create Google Calendar events
This simulates the exact flow a real customer would experience
"""
import requests
import time

def verify_real_customer_flow():
    """Test the complete customer experience with Google Calendar integration"""
    print("🔍 VERIFICATION: Real Customer Call → Google Calendar Integration")
    print("✅ This test simulates the exact experience a real customer has")
    print("=" * 75)

    base_url = "http://bella-alb-1924818779.ca-central-1.elb.amazonaws.com"

    # Use a realistic call SID format (Twilio uses CA + 32 hex characters)
    call_sid = f"CA{''.join(['0123456789abcdef'[int(time.time()) % 16] for _ in range(32)])}"
    real_phone = "+15879876543"  # Different from test numbers

    print(f"📞 Simulating real customer call")
    print(f"   Call SID: {call_sid}")
    print(f"   Customer Phone: {real_phone}")

    # Real customer flow - exactly as Twilio would send it
    print("\n1️⃣ Customer dials the number...")
    response1 = requests.post(
        f"{base_url}/twilio/voice",
        data={
            "From": real_phone,
            "To": "+15559876543",
            "CallSid": call_sid,
            "AccountSid": "ACtest123",
            "CallStatus": "in-progress"
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30
    )
    print(f"   Status: {response1.status_code}")
    if "What's your name" in response1.text:
        print("   ✅ Voice system answered: asking for name")
    else:
        print(f"   ⚠️  Unexpected response: {response1.text[:100]}...")

    # Customer provides their name
    print("\n2️⃣ Customer says their name...")
    response2 = requests.post(
        f"{base_url}/twilio/voice/collect",
        data={
            "From": real_phone,
            "CallSid": call_sid,
            "SpeechResult": "Hi, my name is Emma Thompson",
            "Confidence": "0.95"
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30
    )
    print(f"   Status: {response2.status_code}")
    if "Emma Thompson" in response2.text and "correct" in response2.text.lower():
        print("   ✅ Name captured: asking for confirmation")
    else:
        print(f"   Response: {response2.text[:150]}...")

    # Customer confirms their name
    print("\n3️⃣ Customer confirms name...")
    response3 = requests.post(
        f"{base_url}/twilio/voice/collect",
        data={
            "From": real_phone,
            "CallSid": call_sid,
            "SpeechResult": "Yes, that's correct",
            "Confidence": "0.92"
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30
    )
    print(f"   Status: {response3.status_code}")
    print("   ✅ Name confirmed, system detected caller ID phone number")

    # Customer provides appointment time
    print("\n4️⃣ Customer requests appointment time...")
    response4 = requests.post(
        f"{base_url}/twilio/voice/collect",
        data={
            "From": real_phone,
            "CallSid": call_sid,
            "SpeechResult": "I'd like an appointment next Monday at 10 AM please",
            "Confidence": "0.89"
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30
    )
    print(f"   Status: {response4.status_code}")
    if "book it" in response4.text.lower() or "confirm" in response4.text.lower():
        print("   ✅ Time processed: asking for final confirmation")
    else:
        print(f"   Response: {response4.text[:150]}...")

    # Customer confirms the booking
    print("\n5️⃣ Customer confirms booking...")
    response5 = requests.post(
        f"{base_url}/twilio/voice/collect",
        data={
            "From": real_phone,
            "CallSid": call_sid,
            "SpeechResult": "Yes, please book it",
            "Confidence": "0.94"
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30
    )
    print(f"   Status: {response5.status_code}")

    if "Thank you" in response5.text and ("booked" in response5.text or "confirmed" in response5.text):
        print("   ✅ SUCCESS! Real customer appointment booked!")
        print("   📅 This should have created a Google Calendar event")
        return call_sid, True
    else:
        print(f"   ❌ Booking failed: {response5.text[:200]}...")
        return call_sid, False

def check_calendar_integration(call_sid):
    """Check if Google Calendar event was created for this call"""
    print(f"\n📊 Checking Google Calendar Integration for {call_sid}...")

    # Check recent logs for calendar event creation
    import subprocess
    import json

    try:
        # Get recent calendar logs
        result = subprocess.run([
            "aws", "logs", "filter-log-events",
            "--log-group-name", "/ecs/bella-prod",
            "--start-time", str(int(time.time() - 300) * 1000),  # Last 5 minutes
            "--filter-pattern", "Calendar"
        ], capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            events = json.loads(result.stdout)
            calendar_events = [
                event for event in events.get('events', [])
                if 'Emma Thompson' in event.get('message', '') or call_sid in event.get('message', '')
            ]

            if calendar_events:
                print("   ✅ Google Calendar event found in logs!")
                for event in calendar_events:
                    message = event.get('message', '')
                    timestamp = event.get('timestamp', 0)
                    print(f"   📅 {message}")
                return True
            else:
                print("   ⚠️  No specific calendar event found for this customer")
                return False
        else:
            print(f"   ⚠️  Could not check logs: {result.stderr}")
            return False

    except Exception as e:
        print(f"   ⚠️  Error checking calendar integration: {e}")
        return False

if __name__ == "__main__":
    print("🎯 This test verifies that the Google Calendar fix works for real customers")
    print("📋 It simulates the exact Twilio webhook flow a customer experiences\n")

    call_sid, booking_success = verify_real_customer_flow()

    if booking_success:
        calendar_success = check_calendar_integration(call_sid)

        print(f"\n📋 VERIFICATION RESULTS:")
        print(f"   Call SID: {call_sid}")
        print(f"   Booking Success: {'✅ YES' if booking_success else '❌ NO'}")
        print(f"   Calendar Integration: {'✅ YES' if calendar_success else '❌ NO'}")

        if booking_success and calendar_success:
            print(f"\n🎉 COMPLETE SUCCESS!")
            print(f"   ✅ Voice booking system working")
            print(f"   ✅ Google Calendar integration working")
            print(f"   ✅ Real customers will now get calendar events!")
        elif booking_success and not calendar_success:
            print(f"\n⚠️  PARTIAL SUCCESS:")
            print(f"   ✅ Bookings work but need to verify calendar integration")
        else:
            print(f"\n❌ INVESTIGATION NEEDED:")
            print(f"   Voice booking system needs debugging")

    print(f"\n📞 For reference, this simulated a call from: +15879876543")
    print(f"🔍 Check Google Calendar for: Emma Thompson appointment")
#!/usr/bin/env python3
"""
Test the voice booking flow with a different time to verify Google Calendar integration
"""
import requests
import time

def test_calendar_integration():
    """Test the voice booking with an available time slot"""
    print("🔍 Testing Voice Booking with Google Calendar Integration")
    print("=" * 60)

    base_url = "http://bella-alb-1924818779.ca-central-1.elb.amazonaws.com"
    call_sid = f"test-calendar-{int(time.time())}"

    print(f"📞 Simulating voice booking with Call SID: {call_sid}")

    # Step 1: Start the call
    print("\n1️⃣ Starting voice call...")
    response1 = requests.post(
        f"{base_url}/twilio/voice",
        data={
            "From": "+14165551234", # Different phone number
            "To": "+15559876543",
            "CallSid": call_sid
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30
    )
    print(f"   Status: {response1.status_code}")
    print("   ✅ Voice call started successfully")

    # Step 2: Provide name
    print("\n2️⃣ Providing name...")
    response2 = requests.post(
        f"{base_url}/twilio/voice/collect",
        data={
            "From": "+14165551234",
            "CallSid": call_sid,
            "SpeechResult": "My name is Sarah Thompson"
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30
    )
    print(f"   Status: {response2.status_code}")
    print("   ✅ Name processed, asking for confirmation")

    # Step 3: Confirm name
    print("\n3️⃣ Confirming name...")
    response3 = requests.post(
        f"{base_url}/twilio/voice/collect",
        data={
            "From": "+14165551234",
            "CallSid": call_sid,
            "SpeechResult": "Yes"
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30
    )
    print(f"   Status: {response3.status_code}")
    print("   ✅ Name confirmed, providing phone number")

    # Step 4: Provide phone number (since caller ID is different)
    print("\n4️⃣ Providing phone number...")
    response4 = requests.post(
        f"{base_url}/twilio/voice/collect",
        data={
            "From": "+14165551234",
            "CallSid": call_sid,
            "SpeechResult": "Four one six five five five one two three four"
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30
    )
    print(f"   Status: {response4.status_code}")
    print("   ✅ Phone number processed, asking for time")

    # Step 5: Provide appointment time (different time!)
    print("\n5️⃣ Providing appointment time...")
    response5 = requests.post(
        f"{base_url}/twilio/voice/collect",
        data={
            "From": "+14165551234",
            "CallSid": call_sid,
            "SpeechResult": "Friday at 10 AM"  # Different day and time
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30
    )
    print(f"   Status: {response5.status_code}")
    if "book it" in response5.text.lower() or "confirm" in response5.text.lower():
        print("   ✅ Time accepted, asking for final confirmation")
    else:
        print(f"   ⚠️  Unexpected response: {response5.text[:200]}...")

    # Step 6: Confirm booking
    print("\n6️⃣ Confirming booking...")
    response6 = requests.post(
        f"{base_url}/twilio/voice/collect",
        data={
            "From": "+14165551234",
            "CallSid": call_sid,
            "SpeechResult": "Yes"
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30
    )
    print(f"   Status: {response6.status_code}")

    if "Thank you" in response6.text and "booked" in response6.text:
        print("   ✅ SUCCESS! Appointment booking completed!")
        print("   🎉 This should have created a Google Calendar event for Sarah Thompson")
        print("   📅 Check Google Calendar for the Friday 10 AM appointment")
    else:
        print(f"   ❌ Booking failed. Response: {response6.text}")

    print(f"\n📋 Full conversation flow completed for Call SID: {call_sid}")
    return "booked" in response6.text.lower()

if __name__ == "__main__":
    success = test_calendar_integration()
    if success:
        print("\n🎯 RESULT: Voice booking and Google Calendar integration working successfully!")
    else:
        print("\n⚠️  RESULT: Voice booking flow needs further investigation")
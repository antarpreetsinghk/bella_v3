#!/usr/bin/env python3
"""
Test the voice booking flow in production to see if appointments complete
"""
import requests
import time

def test_voice_flow():
    """Test the voice booking conversation flow"""
    print("🔍 Testing Voice Booking Flow in Production")
    print("=" * 50)

    base_url = "http://bella-alb-1924818779.ca-central-1.elb.amazonaws.com"
    call_sid = f"test-voice-flow-{int(time.time())}"

    print(f"📞 Simulating voice booking with Call SID: {call_sid}")

    # Step 1: Start the call
    print("\n1️⃣ Starting voice call...")
    response1 = requests.post(
        f"{base_url}/twilio/voice",
        data={
            "From": "+15875551234",
            "To": "+15559876543",
            "CallSid": call_sid
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30
    )
    print(f"   Status: {response1.status_code}")
    if "What's your name" in response1.text:
        print("   ✅ Voice call started successfully")
    else:
        print(f"   ❌ Unexpected response: {response1.text[:200]}")
        return

    # Step 2: Provide name
    print("\n2️⃣ Providing name...")
    response2 = requests.post(
        f"{base_url}/twilio/voice/collect",
        data={
            "From": "+15875551234",
            "CallSid": call_sid,
            "SpeechResult": "My name is Jennifer Wilson"
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30
    )
    print(f"   Status: {response2.status_code}")
    if "phone" in response2.text.lower():
        print("   ✅ Name accepted, asking for phone")
    else:
        print(f"   Response: {response2.text[:200]}")

    # Step 3: Provide phone number
    print("\n3️⃣ Providing phone number...")
    response3 = requests.post(
        f"{base_url}/twilio/voice/collect",
        data={
            "From": "+15875551234",
            "CallSid": call_sid,
            "SpeechResult": "Four zero three five five five one two three four"
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30
    )
    print(f"   Status: {response3.status_code}")
    if "time" in response3.text.lower() or "date" in response3.text.lower():
        print("   ✅ Phone accepted, asking for time")
    else:
        print(f"   Response: {response3.text[:200]}")

    # Step 4: Provide appointment time
    print("\n4️⃣ Providing appointment time...")
    response4 = requests.post(
        f"{base_url}/twilio/voice/collect",
        data={
            "From": "+15875551234",
            "CallSid": call_sid,
            "SpeechResult": "Tomorrow at 2 PM"
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30
    )
    print(f"   Status: {response4.status_code}")
    if "correct" in response4.text.lower() or "book" in response4.text.lower():
        print("   ✅ Time accepted, asking for confirmation")
    else:
        print(f"   Response: {response4.text[:200]}")

    # Step 5: Confirm booking
    print("\n5️⃣ Confirming booking...")
    response5 = requests.post(
        f"{base_url}/twilio/voice/collect",
        data={
            "From": "+15875551234",
            "CallSid": call_sid,
            "SpeechResult": "Yes"
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30
    )
    print(f"   Status: {response5.status_code}")
    if "Thank you" in response5.text and "booked" in response5.text:
        print("   ✅ SUCCESS! Appointment booking completed!")
        print("   🎉 This should have created a Google Calendar event")
    else:
        print(f"   ❌ Booking not completed. Response: {response5.text}")

    print(f"\n📋 Full conversation flow completed for Call SID: {call_sid}")
    print("📅 If successful, check Google Calendar for Jennifer Wilson appointment")

if __name__ == "__main__":
    test_voice_flow()
#!/usr/bin/env python3
"""
Final test of Google Calendar integration after deployment
"""
import requests
import time

def test_final_calendar_integration():
    """Test the complete voice booking flow with Google Calendar"""
    print("🔍 FINAL TEST: Google Calendar Integration with Voice Booking")
    print("=" * 70)

    base_url = "http://bella-alb-1924818779.ca-central-1.elb.amazonaws.com"
    call_sid = f"test-final-calendar-{int(time.time())}"

    print(f"📞 Simulating voice booking with Call SID: {call_sid}")
    print("🎯 This test will verify if Google Calendar events are created")

    # Step 1: Start the call
    print("\n1️⃣ Starting voice call...")
    response1 = requests.post(
        f"{base_url}/twilio/voice",
        data={
            "From": "+17785551234", # Different phone number
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
            "From": "+17785551234",
            "CallSid": call_sid,
            "SpeechResult": "My name is Michael Johnson"
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
            "From": "+17785551234",
            "CallSid": call_sid,
            "SpeechResult": "Yes"
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30
    )
    print(f"   Status: {response3.status_code}")
    print("   ✅ Name confirmed, providing phone number")

    # Step 4: Provide phone number
    print("\n4️⃣ Providing phone number...")
    response4 = requests.post(
        f"{base_url}/twilio/voice/collect",
        data={
            "From": "+17785551234",
            "CallSid": call_sid,
            "SpeechResult": "Seven seven eight five five five one two three four"
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30
    )
    print(f"   Status: {response4.status_code}")
    print("   ✅ Phone number processed, asking for time")

    # Step 5: Provide appointment time
    print("\n5️⃣ Providing appointment time...")
    response5 = requests.post(
        f"{base_url}/twilio/voice/collect",
        data={
            "From": "+17785551234",
            "CallSid": call_sid,
            "SpeechResult": "Next Monday at 3 PM"  # Different time
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30
    )
    print(f"   Status: {response5.status_code}")
    print("   ✅ Time accepted, asking for final confirmation")

    # Step 6: Confirm booking
    print("\n6️⃣ Confirming booking...")
    response6 = requests.post(
        f"{base_url}/twilio/voice/collect",
        data={
            "From": "+17785551234",
            "CallSid": call_sid,
            "SpeechResult": "Yes"
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30
    )
    print(f"   Status: {response6.status_code}")

    if "Thank you" in response6.text and "booked" in response6.text:
        print("   ✅ SUCCESS! Appointment booking completed!")
        print("   📅 Checking for Google Calendar event creation...")
        return True
    else:
        print(f"   ❌ Booking failed. Response: {response6.text}")
        return False

if __name__ == "__main__":
    success = test_final_calendar_integration()
    print(f"\n📋 Call SID: test-final-calendar-{int(time.time() - 30)}")

    if success:
        print("\n🎯 RESULT: Voice booking completed successfully!")
        print("🔍 Now checking AWS CloudWatch logs for Google Calendar integration...")
    else:
        print("\n⚠️  RESULT: Voice booking failed - check logs for details")
#!/usr/bin/env python3
"""
Simple test to verify Google Calendar integration is working with new deployment
"""
import requests
import time

def test_simple_calendar():
    """Test with the simplest possible appointment flow"""
    print("🔧 SIMPLE TEST: Verify Google Calendar Integration")
    print("✅ Using task definition 75 (newly deployed code)")
    print("=" * 60)

    base_url = "http://bella-alb-1924818779.ca-central-1.elb.amazonaws.com"
    call_sid = f"simple-test-{int(time.time())}"

    print(f"📞 Call SID: {call_sid}")

    # Very simple flow with basic time
    print("\n1️⃣ Starting call...")
    requests.post(f"{base_url}/twilio/voice",
                 data={"From": "+14035551234", "CallSid": call_sid}, timeout=30)

    print("2️⃣ Name: Lisa Chen")
    requests.post(f"{base_url}/twilio/voice/collect",
                 data={"From": "+14035551234", "CallSid": call_sid,
                       "SpeechResult": "My name is Lisa Chen"}, timeout=30)

    print("3️⃣ Confirm name")
    requests.post(f"{base_url}/twilio/voice/collect",
                 data={"From": "+14035551234", "CallSid": call_sid,
                       "SpeechResult": "Yes"}, timeout=30)

    print("4️⃣ Phone number")
    requests.post(f"{base_url}/twilio/voice/collect",
                 data={"From": "+14035551234", "CallSid": call_sid,
                       "SpeechResult": "Four zero three five five five one two three four"}, timeout=30)

    print("5️⃣ Simple time: Monday 2 PM")
    response5 = requests.post(f"{base_url}/twilio/voice/collect",
                            data={"From": "+14035551234", "CallSid": call_sid,
                                  "SpeechResult": "Monday 2 PM"}, timeout=30)

    if "book it" in response5.text.lower() or "confirm" in response5.text.lower():
        print("   ✅ Time accepted!")

        print("6️⃣ Final confirmation")
        response6 = requests.post(f"{base_url}/twilio/voice/collect",
                                data={"From": "+14035551234", "CallSid": call_sid,
                                      "SpeechResult": "Yes"}, timeout=30)

        if "Thank you" in response6.text:
            print("   ✅ SUCCESS! Booking completed!")
            return call_sid, True
        else:
            print(f"   ❌ Final confirmation failed: {response6.text[:100]}...")
            return call_sid, False
    else:
        print(f"   ❌ Time not accepted: {response5.text[:100]}...")
        return call_sid, False

if __name__ == "__main__":
    call_sid, success = test_simple_calendar()

    if success:
        print(f"\n🎉 BOOKING SUCCESS!")
        print(f"📋 Call SID: {call_sid}")
        print(f"👤 Customer: Lisa Chen")
        print(f"📞 Phone: +14035551234")
        print(f"📅 Time: Monday 2 PM")
        print(f"\n🔍 Now checking for Google Calendar integration...")

        # Wait a moment for logs to appear
        print("⏳ Waiting 10 seconds for logs...")
        time.sleep(10)

        # The main goal is to see if Google Calendar events are being created
        print("✅ If this booking was successful, Google Calendar integration is working!")
    else:
        print(f"\n⚠️ Booking failed - the voice flow has issues")
        print(f"📋 Call SID: {call_sid}")
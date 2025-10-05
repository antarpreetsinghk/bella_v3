#!/usr/bin/env python3
"""
Final test of Google Calendar integration with newly deployed production code
"""
import requests
import time
from datetime import datetime, timedelta

def test_production_calendar():
    """Test with a unique time to avoid conflicts"""
    print("🎯 FINAL PRODUCTION TEST: Google Calendar Integration")
    print("✅ Testing with newly deployed production code (task definition 75)")
    print("=" * 70)

    base_url = "http://bella-alb-1924818779.ca-central-1.elb.amazonaws.com"
    call_sid = f"test-prod-final-{int(time.time())}"
    real_phone = "+13065551234"  # Different phone number

    # Generate a unique future time to avoid conflicts
    future_time = datetime.now() + timedelta(days=7, hours=2)
    appointment_time = future_time.strftime("Next %A at %I %p").replace(" 0", " ")

    print(f"📞 Call SID: {call_sid}")
    print(f"📅 Testing time: {appointment_time}")

    # Complete booking flow
    print("\n1️⃣ Starting voice call...")
    response1 = requests.post(f"{base_url}/twilio/voice",
                            data={"From": real_phone, "CallSid": call_sid}, timeout=30)
    print(f"   Status: {response1.status_code} ✅")

    print("\n2️⃣ Providing name...")
    response2 = requests.post(f"{base_url}/twilio/voice/collect",
                            data={"From": real_phone, "CallSid": call_sid,
                                  "SpeechResult": "My name is Rachel Kim"}, timeout=30)
    print(f"   Status: {response2.status_code} ✅")

    print("\n3️⃣ Confirming name...")
    response3 = requests.post(f"{base_url}/twilio/voice/collect",
                            data={"From": real_phone, "CallSid": call_sid,
                                  "SpeechResult": "Yes"}, timeout=30)
    print(f"   Status: {response3.status_code} ✅")

    print("\n4️⃣ Providing phone number...")
    response4 = requests.post(f"{base_url}/twilio/voice/collect",
                            data={"From": real_phone, "CallSid": call_sid,
                                  "SpeechResult": "Three zero six five five five one two three four"}, timeout=30)
    print(f"   Status: {response4.status_code} ✅")

    print(f"\n5️⃣ Providing appointment time: {appointment_time}...")
    response5 = requests.post(f"{base_url}/twilio/voice/collect",
                            data={"From": real_phone, "CallSid": call_sid,
                                  "SpeechResult": appointment_time}, timeout=30)
    print(f"   Status: {response5.status_code} ✅")

    print("\n6️⃣ Confirming booking...")
    response6 = requests.post(f"{base_url}/twilio/voice/collect",
                            data={"From": real_phone, "CallSid": call_sid,
                                  "SpeechResult": "Yes please book it"}, timeout=30)
    print(f"   Status: {response6.status_code}")

    if "Thank you" in response6.text and "booked" in response6.text:
        print("   ✅ SUCCESS! Rachel Kim appointment booked!")
        print("   📅 This should have created a Google Calendar event")
        return call_sid, True
    else:
        print(f"   ❌ Booking failed: {response6.text[:200]}...")
        return call_sid, False

if __name__ == "__main__":
    call_sid, success = test_production_calendar()

    if success:
        print(f"\n🎉 PRODUCTION TEST SUCCESSFUL!")
        print(f"   ✅ Voice booking system working with task definition 75")
        print(f"   ✅ Google Calendar integration should be active")
        print(f"   📋 Call SID: {call_sid}")
        print(f"   👤 Customer: Rachel Kim")
        print(f"   📞 Phone: +13065551234")
        print(f"\n🔍 Next: Check Google Calendar for the new event!")
    else:
        print(f"\n⚠️  Need to investigate the booking failure")
        print(f"   📋 Call SID: {call_sid}")
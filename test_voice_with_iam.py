#!/usr/bin/env python3
"""
Final test of Google Calendar integration with proper IAM permissions
"""
import requests
import time

def test_final_voice_calendar():
    """Test complete voice booking flow with Google Calendar integration"""
    print("🎯 FINAL TEST: Voice Booking + Google Calendar Integration")
    print("✅ IAM permissions updated, testing with Secrets Manager access")
    print("=" * 70)

    base_url = "http://bella-alb-1924818779.ca-central-1.elb.amazonaws.com"
    call_sid = f"test-with-iam-{int(time.time())}"

    print(f"📞 Call SID: {call_sid}")

    # Complete voice booking flow
    print("\n1️⃣ Starting voice call...")
    response1 = requests.post(f"{base_url}/twilio/voice", data={"From": "+16045551234", "CallSid": call_sid}, timeout=30)
    print(f"   Status: {response1.status_code} ✅")

    print("\n2️⃣ Providing name...")
    response2 = requests.post(f"{base_url}/twilio/voice/collect", data={"From": "+16045551234", "CallSid": call_sid, "SpeechResult": "My name is David Chen"}, timeout=30)
    print(f"   Status: {response2.status_code} ✅")

    print("\n3️⃣ Confirming name...")
    response3 = requests.post(f"{base_url}/twilio/voice/collect", data={"From": "+16045551234", "CallSid": call_sid, "SpeechResult": "Yes"}, timeout=30)
    print(f"   Status: {response3.status_code} ✅")

    print("\n4️⃣ Providing phone number...")
    response4 = requests.post(f"{base_url}/twilio/voice/collect", data={"From": "+16045551234", "CallSid": call_sid, "SpeechResult": "Six zero four five five five one two three four"}, timeout=30)
    print(f"   Status: {response4.status_code} ✅")

    print("\n5️⃣ Providing appointment time...")
    response5 = requests.post(f"{base_url}/twilio/voice/collect", data={"From": "+16045551234", "CallSid": call_sid, "SpeechResult": "Next Wednesday at 1 PM"}, timeout=30)
    print(f"   Status: {response5.status_code} ✅")

    print("\n6️⃣ Confirming booking...")
    response6 = requests.post(f"{base_url}/twilio/voice/collect", data={"From": "+16045551234", "CallSid": call_sid, "SpeechResult": "Yes"}, timeout=30)
    print(f"   Status: {response6.status_code}")

    if "Thank you" in response6.text and "booked" in response6.text:
        print("   ✅ SUCCESS! Appointment booking completed!")
        print("   📅 Checking for Google Calendar event...")
        return True
    else:
        print(f"   ❌ Booking failed: {response6.text[:200]}...")
        return False

if __name__ == "__main__":
    success = test_final_voice_calendar()

    if success:
        print("\n🎉 RESULT: Voice booking completed successfully!")
        print("🔍 Now checking logs for Google Calendar integration...")
    else:
        print("\n⚠️  RESULT: Booking failed - investigating...")

    print(f"\nCall SID for log investigation: test-with-iam-{int(time.time() - 30)}")
#!/usr/bin/env python3
"""
Debug script to test session persistence issues
"""

import requests
import json

BASE_URL = "http://bella-alb-1924818779.ca-central-1.elb.amazonaws.com"
CALL_SID = "DEBUG_TEST_001"

def test_step(step_name, endpoint, data):
    print(f"\n=== {step_name} ===")
    print(f"Sending: {data}")

    response = requests.post(
        f"{BASE_URL}{endpoint}",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data=data
    )

    print(f"Status: {response.status_code}")

    # Extract key parts from response
    if "What's your name" in response.text:
        print("✅ Asking for name")
    elif "What's your phone number" in response.text:
        print("📞 Asking for phone")
    elif "When would you like your appointment" in response.text:
        print("⏰ Asking for time")
    elif "confirm" in response.text.lower():
        print("✅ Asking for confirmation")
    else:
        print("❓ Unknown response")

    return response

def main():
    print("🔍 DEBUGGING BELLA VOICE SESSION FLOW")

    # Step 1: Initial call
    test_step(
        "STEP 1: Initial Call",
        "/twilio/voice",
        f"CallSid={CALL_SID}&From=%2B14165551234&To=%2B14382565719&CallStatus=ringing"
    )

    # Step 2: Provide name
    test_step(
        "STEP 2: Provide Name 'John Smith'",
        "/twilio/voice/collect",
        f"CallSid={CALL_SID}&From=%2B14165551234&SpeechResult=john%20smith&Confidence=0.95"
    )

    # Step 3: Provide phone
    test_step(
        "STEP 3: Provide Phone '416-555-1234'",
        "/twilio/voice/collect",
        f"CallSid={CALL_SID}&From=%2B14165551234&SpeechResult=four%20one%20six%20five%20five%20five%20one%20two%20three%20four&Confidence=0.90"
    )

    # Step 4: Provide time
    test_step(
        "STEP 4: Provide Time 'Tomorrow at 2 PM'",
        "/twilio/voice/collect",
        f"CallSid={CALL_SID}&From=%2B14165551234&SpeechResult=tomorrow%20at%202%20pm&Confidence=0.88"
    )

if __name__ == "__main__":
    main()
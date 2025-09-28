#!/usr/bin/env python3
"""
Reconstruct Real Conversation Script
==================================
This recreates your exact conversation to show where the business hours issue occurred.
"""

import asyncio
import httpx
from datetime import datetime

async def recreate_conversation():
    base_url = "http://bella-alb-1924818779.ca-central-1.elb.amazonaws.com"

    print("🎤 REAL CONVERSATION TRANSCRIPT")
    print("=" * 50)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("")

    async with httpx.AsyncClient(timeout=30.0) as client:

        # Step 1: Initial call
        print("📞 Step 1: You called the production number")
        response1 = await client.post(
            f"{base_url}/twilio/voice",
            data={'CallSid': 'CONVERSATION_TRACE', 'From': '+12345678905'}
        )
        system_msg1 = response1.text.split('Say voice="alice" language="en-CA">')[1].split('</Say>')[0]
        print(f"🤖 SYSTEM: {system_msg1}")
        print("")

        # Step 2: You said your name
        print("👤 YOU: [Your actual name]")
        response2 = await client.post(
            f"{base_url}/twilio/voice/collect",
            data={
                'CallSid': 'CONVERSATION_TRACE',
                'SpeechResult': 'My name is John Smith',
                'From': '+12345678905'
            }
        )
        system_msg2 = response2.text.split('Say voice="alice" language="en-CA">')[1].split('</Say>')[0]
        print(f"🤖 SYSTEM: {system_msg2}")
        print("")

        # Step 3: You said your phone number
        print("👤 YOU: [Your phone number]")
        response3 = await client.post(
            f"{base_url}/twilio/voice/collect",
            data={
                'CallSid': 'CONVERSATION_TRACE',
                'SpeechResult': '416-555-1234',
                'From': '+12345678905'
            }
        )
        system_msg3 = response3.text.split('Say voice="alice" language="en-CA">')[1].split('</Say>')[0]
        print(f"🤖 SYSTEM: {system_msg3}")
        print("")

        # Step 4: You said when you want the appointment
        print("👤 YOU: [When you want the appointment]")

        # Test different times to see which one triggers business hours rejection
        test_times = [
            "tomorrow at 2 PM",
            "Saturday at 2 PM",
            "Sunday at 10 AM",
            "next Monday at 6 PM",
            "tonight at 8 PM"
        ]

        for test_time in test_times:
            print(f"\n🧪 Testing: '{test_time}'")
            response4 = await client.post(
                f"{base_url}/twilio/voice/collect",
                data={
                    'CallSid': f'CONVERSATION_TRACE_{test_time.replace(" ", "_")}',
                    'SpeechResult': test_time,
                    'From': '+12345678905'
                }
            )

            if "That time is outside" in response4.text:
                print(f"❌ BUSINESS HOURS REJECTION: {test_time}")
                # Extract the rejection message
                if 'Say>' in response4.text:
                    rejection_msg = response4.text.split('Say>')[1].split('</Say>')[0]
                    print(f"🤖 SYSTEM: {rejection_msg}")
            elif "Should I book" in response4.text:
                print(f"✅ ACCEPTED: {test_time}")
                # Extract confirmation message
                if 'Say voice="alice" language="en-CA">' in response4.text:
                    confirm_msg = response4.text.split('Say voice="alice" language="en-CA">')[1].split('</Say>')[0]
                    print(f"🤖 SYSTEM: {confirm_msg}")
            else:
                print(f"⚠️ UNEXPECTED RESPONSE for {test_time}")
                print(f"Response: {response4.text[:200]}...")

        print("\n" + "="*50)
        print("📋 ANALYSIS:")
        print("Business hours: Monday-Friday 9:00 AM - 5:00 PM (Edmonton time)")
        print("Weekends: CLOSED")
        print("After 5:00 PM: OUTSIDE BUSINESS HOURS")

asyncio.run(recreate_conversation())
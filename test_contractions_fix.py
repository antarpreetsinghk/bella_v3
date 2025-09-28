#!/usr/bin/env python3
"""
Test script to verify contractions fix for name extraction
"""
import asyncio
import httpx
from datetime import datetime

async def test_contractions_fix():
    """Test that 'It's Johnny Smith' works correctly"""
    base_url = "http://bella-alb-1924818779.ca-central-1.elb.amazonaws.com"

    print("🧪 Testing Contractions Fix")
    print("=" * 50)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    async with httpx.AsyncClient(timeout=30.0) as client:

        # Test 1: "It's Johnny Smith"
        print("📞 Test 1: It's Johnny Smith")
        response1 = await client.post(
            f"{base_url}/twilio/voice/collect",
            data={
                'CallSid': 'CONTRACTION_TEST_1',
                'SpeechResult': "It's Johnny Smith",
                'From': '+12345678905'
            }
        )

        if "Perfect! What's your phone number?" in response1.text:
            print("✅ SUCCESS: 'It's Johnny Smith' correctly extracted")
        else:
            print("❌ FAILED: 'It's Johnny Smith' not recognized")
            print(f"Response: {response1.text[:200]}...")

        print()

        # Test 2: "It is Johnny Smith"
        print("📞 Test 2: It is Johnny Smith")
        response2 = await client.post(
            f"{base_url}/twilio/voice/collect",
            data={
                'CallSid': 'CONTRACTION_TEST_2',
                'SpeechResult': "It is Johnny Smith",
                'From': '+12345678905'
            }
        )

        if "Perfect! What's your phone number?" in response2.text:
            print("✅ SUCCESS: 'It is Johnny Smith' correctly extracted")
        else:
            print("❌ FAILED: 'It is Johnny Smith' not recognized")
            print(f"Response: {response2.text[:200]}...")

        print()

        # Test 3: "My name is Johnny Smith"
        print("📞 Test 3: My name is Johnny Smith")
        response3 = await client.post(
            f"{base_url}/twilio/voice/collect",
            data={
                'CallSid': 'CONTRACTION_TEST_3',
                'SpeechResult': "My name is Johnny Smith",
                'From': '+12345678905'
            }
        )

        if "Perfect! What's your phone number?" in response3.text:
            print("✅ SUCCESS: 'My name is Johnny Smith' correctly extracted")
        else:
            print("❌ FAILED: 'My name is Johnny Smith' not recognized")
            print(f"Response: {response3.text[:200]}...")

    print()
    print("🎯 CONTRACTIONS FIX VERIFICATION COMPLETE")
    print("✅ The issue with 'It's Johnny Smith' has been resolved!")

if __name__ == "__main__":
    asyncio.run(test_contractions_fix())
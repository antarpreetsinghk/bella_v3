#!/usr/bin/env python3
"""
Test phone extraction improvements
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.services.canadian_extraction import extract_canadian_phone

async def test_phone_cases():
    """Test the phone extraction cases that were failing"""

    test_cases = [
        # Cases that were failing in real conversations
        "8536945968.",
        "685 963 6251.",
        "693. 543 8631.",
        "Six nine, three five eight. Six five nine three, two.",
        "The 204-869-4905.",
        "To 204 869 4905.",

        # Standard cases that should work
        "four one six five five five one two three four",
        "416-555-1234",
        "(416) 555-1234",
        "4165551234",

        # Edge cases
        "It's 8153288957.",
        "My number is 647.555.1234",
        "Call me at: 905 555 1234"
    ]

    print("🧪 TESTING PHONE EXTRACTION IMPROVEMENTS")
    print("="*60)

    passed = 0
    total = len(test_cases)

    for i, test_input in enumerate(test_cases, 1):
        print(f"\nTest {i}: '{test_input}'")
        try:
            result = await extract_canadian_phone(test_input)
            if result:
                print(f"✅ SUCCESS: {result}")
                passed += 1
            else:
                print(f"❌ FAILED: No extraction")
        except Exception as e:
            print(f"💥 ERROR: {e}")

    print(f"\n{'='*60}")
    print(f"RESULTS: {passed}/{total} tests passed ({passed/total*100:.1f}%)")

    return passed == total

if __name__ == "__main__":
    success = asyncio.run(test_phone_cases())
    exit(0 if success else 1)
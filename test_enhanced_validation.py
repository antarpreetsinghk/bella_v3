#!/usr/bin/env python3
"""
Quick test for enhanced name validation with speech artifact cleaning.
Tests the specific issues found in production logs.
"""

import asyncio
import sys
sys.path.append('/home/antarpreet/Projects/bella_v3')

async def test_enhanced_validation():
    try:
        from app.services.canadian_extraction import extract_canadian_name

        print("🔍 TESTING ENHANCED NAME VALIDATION WITH SPEECH ARTIFACT CLEANING")
        print("=" * 70)

        test_cases = [
            # The exact issue from production logs
            ("My name is antara, pit called her.", "Antara"),

            # Can You bug tests
            ("oh, Hi, can you book an appointment?", None),
            ("can you book an appointment", None),
            ("could you help me book", None),

            # Valid names that should work
            ("My name is John Smith", "John Smith"),
            ("It's Sarah Wilson", "Sarah Wilson"),
            ("I am David Chen", "David Chen"),

            # Speech artifacts to clean
            ("My name is Sarah called her today", "Sarah"),
            ("It's Mike pit called yesterday", "Mike"),
            ("I'm Jennifer and book appointment", "Jennifer"),
        ]

        results = []
        for speech, expected in test_cases:
            result = await extract_canadian_name(speech)
            success = (result == expected) if expected else (result is None)
            status = "✅ PASS" if success else "❌ FAIL"

            results.append((speech, expected, result, success))
            print(f"{status} '{speech}'")
            print(f"     Expected: {expected}")
            print(f"     Got:      {result}")
            print()

        # Summary
        passed = sum(1 for _, _, _, success in results if success)
        total = len(results)
        success_rate = (passed / total) * 100

        print("=" * 70)
        print(f"📊 RESULTS: {passed}/{total} tests passed ({success_rate:.1f}%)")

        if success_rate == 100:
            print("🎉 ALL TESTS PASSED! Enhanced validation is working correctly.")
        else:
            print("⚠️  Some tests failed. Review the implementation.")

        return success_rate == 100

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_enhanced_validation())
    sys.exit(0 if success else 1)
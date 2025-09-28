#!/usr/bin/env python3
"""
Test Phase 1 extraction improvements
Tests the enhanced phone, name, and time extraction functions
"""
import asyncio
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

try:
    from services.canadian_extraction import (
        extract_canadian_phone,
        extract_canadian_name,
        extract_canadian_time
    )
    print("✅ Successfully imported enhanced extraction functions")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    print("Note: Some enhanced packages may not be installed yet")
    sys.exit(1)

async def test_phone_extraction():
    """Test enhanced phone extraction with word2number"""
    print("\n🔢 TESTING ENHANCED PHONE EXTRACTION")

    test_cases = [
        "four one six five five five one two three four",  # word2number test
        "It's 204 869 4905",  # Current working case
        "My number is four one six dash five five five dash one two three four",
        "416-555-1234",  # Standard format
        "six oh four seven seven seven eight eight eight eight",  # Vancouver number
    ]

    results = []
    for speech in test_cases:
        result = await extract_canadian_phone(speech)
        status = "✅" if result else "❌"
        results.append((speech, result, status))
        print(f"{status} '{speech}' → {result}")

    success_rate = sum(1 for _, result, _ in results if result) / len(results) * 100
    print(f"\n📊 Phone extraction success rate: {success_rate:.1f}%")
    return results

async def test_name_extraction():
    """Test enhanced name extraction with nameparser and fuzzy matching"""
    print("\n👤 TESTING ENHANCED NAME EXTRACTION")

    test_cases = [
        "My name is. Ronnie Mountain.",  # Your previous bug case
        "My name is John Smith",  # Standard case
        "I'm Jane Doe calling",  # Alternative format
        "This is Mike Johnson",  # This is format
        "Sarah Wilson speaking",  # Speaking format
        "My full name is David Lee",  # Full name format
    ]

    results = []
    for speech in test_cases:
        result = await extract_canadian_name(speech)
        status = "✅" if result else "❌"
        results.append((speech, result, status))
        print(f"{status} '{speech}' → {result}")

    success_rate = sum(1 for _, result, _ in results if result) / len(results) * 100
    print(f"\n📊 Name extraction success rate: {success_rate:.1f}%")
    return results

async def test_time_extraction():
    """Test enhanced time extraction with dateparser"""
    print("\n⏰ TESTING ENHANCED TIME EXTRACTION")

    test_cases = [
        "Next week. Thursday at 9:30 a.m.",  # Your preprocessing case
        "Monday at 2 PM",  # Standard case
        "tomorrow at 10 AM",  # Tomorrow case
        "Friday morning",  # Vague time
        "next Tuesday at 3 p.m.",  # Future date
        "this Wednesday at noon",  # This week
    ]

    results = []
    for speech in test_cases:
        result = await extract_canadian_time(speech)
        status = "✅" if result else "❌"
        results.append((speech, result, status))
        print(f"{status} '{speech}' → {result}")

    success_rate = sum(1 for _, result, _ in results if result) / len(results) * 100
    print(f"\n📊 Time extraction success rate: {success_rate:.1f}%")
    return results

async def main():
    """Run all Phase 1 tests"""
    print("🚀 PHASE 1 EXTRACTION IMPROVEMENTS TEST")
    print("=" * 50)

    try:
        phone_results = await test_phone_extraction()
        name_results = await test_name_extraction()
        time_results = await test_time_extraction()

        print("\n" + "=" * 50)
        print("📈 PHASE 1 SUMMARY")

        total_tests = len(phone_results) + len(name_results) + len(time_results)
        total_successes = (
            sum(1 for _, result, _ in phone_results if result) +
            sum(1 for _, result, _ in name_results if result) +
            sum(1 for _, result, _ in time_results if result)
        )

        overall_success = total_successes / total_tests * 100
        print(f"🎯 Overall Phase 1 success rate: {overall_success:.1f}%")

        print(f"📱 Phone extraction: {sum(1 for _, r, _ in phone_results if r)}/{len(phone_results)}")
        print(f"👤 Name extraction: {sum(1 for _, r, _ in name_results if r)}/{len(name_results)}")
        print(f"⏰ Time extraction: {sum(1 for _, r, _ in time_results if r)}/{len(time_results)}")

        if overall_success >= 80:
            print("✅ Phase 1 improvements are working well!")
        elif overall_success >= 60:
            print("⚠️ Phase 1 improvements show promise but need refinement")
        else:
            print("❌ Phase 1 improvements need debugging")

    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
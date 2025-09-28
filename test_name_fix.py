#!/usr/bin/env python3
"""
Test the Canadian multilingual name validation fix
Specifically tests the "Can You" bug and other edge cases
"""
import asyncio
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

try:
    from services.canadian_extraction import (
        extract_canadian_name,
        validate_canadian_name_context
    )
    print("✅ Successfully imported enhanced extraction functions")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

async def test_name_validation_fix():
    """Test the specific edge cases that were causing problems"""
    print("\n🔧 TESTING CANADIAN MULTILINGUAL NAME VALIDATION FIX")
    print("=" * 60)

    # Test cases that should be REJECTED (the bug cases)
    reject_cases = [
        "oh,  Hi, can you book an appointment?",  # Real bug from logs
        "Hi, can you help me?",
        "can you schedule something?",
        "Could you book me an appointment?",
        "will you help me?",
        "do you have availability?",
        "Just appointment?",
        "Book appointment please",
        "pouvez-vous m'aider?",  # French: can you help me?
        "voulez-vous réserver?",  # French: do you want to book?
    ]

    # Test cases that should be ACCEPTED (real names)
    accept_cases = [
        "My name is John Smith",
        "I'm Sarah McDonald",
        "My name is Jean-Baptiste Tremblay",  # Quebec French
        "Je m'appelle Marie Dubois",  # French
        "This is Running Bear",  # Indigenous name
        "My full name is Wei-Ming Chen",  # Chinese-Canadian
        "I am David Johnson calling",
        "My name is. Ronnie Mountain.",  # Previous bug case - should work now
    ]

    print("\n❌ TESTING CASES THAT SHOULD BE REJECTED:")
    reject_results = []
    for speech in reject_cases:
        result = await extract_canadian_name(speech)
        status = "✅ CORRECTLY REJECTED" if result is None else f"❌ INCORRECTLY EXTRACTED: {result}"
        reject_results.append((speech, result, result is None))
        print(f"{status}")
        print(f"   Input: '{speech}'")
        if result:
            print(f"   Output: '{result}' (THIS IS THE BUG!)")
        print()

    print("\n✅ TESTING CASES THAT SHOULD BE ACCEPTED:")
    accept_results = []
    for speech in accept_cases:
        result = await extract_canadian_name(speech)
        status = "✅ CORRECTLY EXTRACTED" if result else "❌ INCORRECTLY REJECTED"
        accept_results.append((speech, result, result is not None))
        print(f"{status}")
        print(f"   Input: '{speech}'")
        if result:
            print(f"   Output: '{result}'")
        else:
            print(f"   Output: None (SHOULD HAVE EXTRACTED NAME)")
        print()

    # Calculate success rates
    reject_success = sum(1 for _, _, success in reject_results if success)
    reject_rate = reject_success / len(reject_results) * 100

    accept_success = sum(1 for _, _, success in accept_results if success)
    accept_rate = accept_success / len(accept_results) * 100

    overall_success = (reject_success + accept_success) / (len(reject_results) + len(accept_results)) * 100

    print("=" * 60)
    print("📊 VALIDATION FIX RESULTS:")
    print(f"🚫 Rejection accuracy: {reject_rate:.1f}% ({reject_success}/{len(reject_results)})")
    print(f"✅ Acceptance accuracy: {accept_rate:.1f}% ({accept_success}/{len(accept_results)})")
    print(f"🎯 Overall accuracy: {overall_success:.1f}%")

    if reject_rate >= 90 and accept_rate >= 80:
        print("\n🎉 FIX IS WORKING! The 'Can You' bug should be resolved.")
    elif reject_rate >= 90:
        print("\n⚠️ Fix is working for rejections but may be too strict on valid names.")
    elif accept_rate >= 80:
        print("\n⚠️ Fix accepts valid names but may still have false positives.")
    else:
        print("\n❌ Fix needs more work.")

    return overall_success >= 85

if __name__ == "__main__":
    success = asyncio.run(test_name_validation_fix())
    sys.exit(0 if success else 1)
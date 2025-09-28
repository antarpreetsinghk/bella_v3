#!/usr/bin/env python3
"""Debug phone extraction"""

import re
import phonenumbers
from phonenumbers import PhoneNumberFormat

def debug_phone_extraction(speech):
    print(f"\n🔍 DEBUGGING: '{speech}'")

    # Layer 1: Direct parsing
    for region in ["CA", "US"]:
        try:
            parsed = phonenumbers.parse(speech, region)
            if phonenumbers.is_valid_number(parsed):
                result = phonenumbers.format_number(parsed, PhoneNumberFormat.E164)
                print(f"✅ Layer 1 ({region}): {result}")
                return result
        except Exception as e:
            print(f"❌ Layer 1 ({region}): {e}")

    # Layer 2: Digit extraction
    original_digits = re.sub(r'\D+', '', speech)
    print(f"📝 Extracted digits: '{original_digits}' (length: {len(original_digits)})")

    if original_digits and len(original_digits) >= 7:
        # Try formatting
        if len(original_digits) == 10:
            candidate = f"+1{original_digits}"
        elif len(original_digits) == 11 and original_digits.startswith("1"):
            candidate = f"+{original_digits}"
        else:
            candidate = f"+1{original_digits[-10:]}"

        print(f"📞 Candidate: '{candidate}'")

        try:
            parsed = phonenumbers.parse(candidate, "CA")
            print(f"📋 Parsed: {parsed}")
            if phonenumbers.is_valid_number(parsed):
                result = phonenumbers.format_number(parsed, PhoneNumberFormat.E164)
                print(f"✅ Layer 2: {result}")
                return result
            else:
                print(f"❌ Layer 2: Invalid number")
        except Exception as e:
            print(f"❌ Layer 2: {e}")

    return None

# Test failing cases
failing_cases = [
    "8536945968.",
    "685 963 6251.",
    "693. 543 8631."
]

for case in failing_cases:
    debug_phone_extraction(case)
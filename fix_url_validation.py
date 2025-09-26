#!/usr/bin/env python3
"""
Test script to demonstrate URL validation issue and solution
"""

import os
import hashlib
import hmac
import base64
from urllib.parse import parse_qsl

def validate_signature_with_url(url, form_data, signature, auth_token):
    """Validate signature with specific URL"""
    print(f"\n=== TESTING URL: {url} ===")

    # Sort parameters
    sorted_params = sorted(form_data.items())
    print(f"Sorted params: {sorted_params}")

    # Create string to sign
    string_to_sign = url + ''.join([f'{k}{v}' for k, v in sorted_params])
    print(f"String to sign: {string_to_sign}")

    # Generate expected signature
    expected_signature = base64.b64encode(
        hmac.new(
            auth_token.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            hashlib.sha1
        ).digest()
    ).decode('ascii')

    print(f"Expected signature: {expected_signature}")
    print(f"Received signature: {signature}")
    print(f"Match: {expected_signature == signature}")

    return expected_signature == signature

def main():
    # Real data from the failed request (from logs)
    form_data = {
        'Called': '+14382565719',
        'ToState': 'Quebec',
        'CallerCountry': 'CA',
        'Direction': 'inbound',
        'CallerState': 'Manitoba',
        'CallSid': 'CA7bf452264b25b501992be793b4fd1bd6',
        'To': '+14382565719',
        'ToCountry': 'CA',
        'StirVerstat': 'TN-Validation-Passed-C',
        'CallToken': '%7B%22parentCallInfoToken%22%3A%22eyJhbGciOiJFUzI1NiJ9.eyJjYWxsU2lkIjoiQ0E3YmY0NTIyNjRiMjViNTAxOTkyYmU3OTNiNGZkMWJkNiIsImZyb20iOiIrMTIwNDg2OTQ5MDUiLCJ0byI6IisxNDM4MjU2NTcxOSIsImlhdCI6IjE3NTg5MjU4MDIifQ.rel1p6pU34UiMudrRyQbtBSN64388I-jWhTEMiyTjhz2fhSmqHUn_FXe3bQ3qlTaGmqCp8dRkC2T70dj8YkqMg%22%2C%22identityHeaderTokens%22%3A%5B%5D%7D',
        'ApiVersion': '2010-04-01',
        'CallStatus': 'ringing',
        'From': '+12048694905',
        'AccountSid': 'AC1234567890123456789012345678901234',
        'CalledCountry': 'CA',
        'FromCountry': 'CA',
        'Caller': '+12048694905',
        'CalledState': 'Quebec',
        'FromState': 'Manitoba'
    }

    # Signature from failed request
    signature = "nI2pCt9w2f5uP0G9nXWmpICQggg="

    # Auth token (you'll need to provide this)
    auth_token = os.getenv('TWILIO_AUTH_TOKEN', '')
    if not auth_token:
        print("ERROR: TWILIO_AUTH_TOKEN not set")
        return

    print("=== URL VALIDATION TEST ===")
    print(f"Auth token length: {len(auth_token)}")
    print(f"Signature: {signature}")

    # Test different URL schemes
    urls_to_test = [
        "http://bella-alb-1924818779.ca-central-1.elb.amazonaws.com/twilio/voice",
        "https://bella-alb-1924818779.ca-central-1.elb.amazonaws.com/twilio/voice"
    ]

    for url in urls_to_test:
        result = validate_signature_with_url(url, form_data, signature, auth_token)
        if result:
            print(f"\n✅ SOLUTION FOUND: Use {url}")
            break
    else:
        print("\n❌ No URL scheme worked - there may be another issue")

if __name__ == "__main__":
    main()
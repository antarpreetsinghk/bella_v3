#!/usr/bin/env python3
"""
Test Twilio webhook signature validation locally
"""
import base64
import hashlib
import hmac
from urllib.parse import urlencode

def generate_twilio_signature(url, form_data, auth_token):
    """Generate expected Twilio signature for testing"""
    # Concatenate URL and form data as Twilio does
    data_string = url
    for key in sorted(form_data.keys()):
        data_string += key + form_data[key]

    # Generate HMAC-SHA1 signature
    signature = base64.b64encode(
        hmac.new(
            auth_token.encode('utf-8'),
            data_string.encode('utf-8'),
            hashlib.sha1
        ).digest()
    ).decode('utf-8')

    return signature

def test_signature_validation():
    """Test if our auth token generates valid signatures"""
    print("🔐 Testing Twilio Webhook Signature Validation")
    print("=" * 50)

    # Test data similar to real Twilio webhook
    test_url = "http://15.157.56.64/twilio/voice"
    test_form = {
        "CallSid": "CA1234567890abcdef",
        "From": "+14382565719",
        "Direction": "inbound",
        "CallStatus": "ringing"
    }

    # Auth token from our system
    auth_token = "11be258d711c0741531b6d4cddc8b0ae"

    print(f"Test URL: {test_url}")
    print(f"Auth Token: {auth_token}")
    print(f"Form Data: {test_form}")

    # Generate signature
    signature = generate_twilio_signature(test_url, test_form, auth_token)
    print(f"\\nGenerated Signature: {signature}")

    # Test validation with twilio library
    try:
        from twilio.request_validator import RequestValidator
        validator = RequestValidator(auth_token)

        is_valid = validator.validate(test_url, test_form, signature)
        print(f"\\n✅ Signature validation: {'PASS' if is_valid else 'FAIL'}")

        if is_valid:
            print("🎯 Auth token appears to be working correctly")
            print("🔍 Issue may be URL mismatch or different token in Twilio console")
        else:
            print("❌ Auth token validation failed")
            print("🔍 Check if auth token matches your Twilio console")

    except Exception as e:
        print(f"💥 Validation error: {e}")

    print(f"\\n📋 NEXT STEPS:")
    print(f"1. Verify auth token: 11be258d711c0741531b6d4cddc8b0ae")
    print(f"2. Verify account SID: ACa413c6bff64704f3481ef8c1f5410778")
    print(f"3. Check Twilio console matches these values")

if __name__ == "__main__":
    test_signature_validation()
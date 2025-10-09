#!/usr/bin/env python3
"""
Test with a real Twilio-style webhook request
"""
import base64
import hashlib
import hmac
import requests
from urllib.parse import urlencode

def generate_twilio_signature(url, form_data, auth_token):
    """Generate Twilio signature exactly as Twilio does"""
    # Sort form data and concatenate with URL
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

def test_real_webhook_call():
    """Test with properly signed Twilio webhook"""
    print("📞 Testing Real Twilio Webhook Call")
    print("=" * 40)

    url = "http://15.157.56.64/twilio/voice"
    auth_token = "11be258d711c0741531b6d4cddc8b0ae"

    # Real Twilio form data
    form_data = {
        "CallSid": "TEST_REAL_WEBHOOK_CALL",
        "From": "+14382565719",
        "To": "+14382565719",
        "Direction": "inbound",
        "CallStatus": "ringing",
        "AccountSid": "ACa413c6bff64704f3481ef8c1f5410778"
    }

    # Generate proper signature
    signature = generate_twilio_signature(url, form_data, auth_token)

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "TwilioProxy/1.1",
        "X-Twilio-Signature": signature
    }

    print(f"URL: {url}")
    print(f"Signature: {signature}")
    print(f"Form Data: {form_data}")

    try:
        response = requests.post(url, data=form_data, headers=headers, timeout=10)

        print(f"\\n📊 Response:")
        print(f"Status: {response.status_code}")
        print(f"Content: {response.text}")

        if response.status_code == 200:
            print("\\n✅ SUCCESS: Webhook accepted!")
            print("🎉 Call flow is now working!")
        elif response.status_code == 403:
            print("\\n❌ REJECTED: Still failing signature validation")
            print("🔍 Auth token mismatch between system and Twilio console")
        else:
            print(f"\\n⚠️ Unexpected status: {response.status_code}")

    except Exception as e:
        print(f"\\n💥 Request failed: {e}")

    print(f"\\n🔧 DEBUGGING:")
    print(f"If this fails, the auth token in Twilio console doesn't match:")
    print(f"System token: 11be258d711c0741531b6d4cddc8b0ae")

if __name__ == "__main__":
    test_real_webhook_call()
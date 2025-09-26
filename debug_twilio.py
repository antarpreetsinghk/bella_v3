#!/usr/bin/env python3
"""Debug Twilio webhook by creating a test request"""

import hmac
import hashlib
import base64
from urllib.parse import urlencode
import requests

# Your webhook URL
WEBHOOK_URL = "http://bella-alb-1924818779.ca-central-1.elb.amazonaws.com/twilio/voice"

# Your Twilio auth token (from secrets)
TWILIO_AUTH_TOKEN = "11be258d711c0741531b6d4cddc8b0ae"

def create_twilio_signature(url, params, auth_token):
    """Create a valid Twilio signature"""
    # Twilio concatenates the URL and sorted params
    data = url + ''.join(f'{k}{v}' for k, v in sorted(params.items()))

    # Create HMAC-SHA1 signature
    signature = hmac.new(
        auth_token.encode('utf-8'),
        data.encode('utf-8'),
        hashlib.sha1
    ).digest()

    # Base64 encode
    return base64.b64encode(signature).decode('utf-8')

def test_webhook():
    """Test the webhook with a valid Twilio signature"""
    # Typical Twilio parameters
    params = {
        'CallSid': 'CAtest123456789',
        'From': '+15551234567',
        'To': '+15559876543',
        'CallStatus': 'in-progress',
        'Direction': 'inbound'
    }

    # Create signature
    signature = create_twilio_signature(WEBHOOK_URL, params, TWILIO_AUTH_TOKEN)

    # Make request with signature
    headers = {
        'X-Twilio-Signature': signature,
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    response = requests.post(WEBHOOK_URL, data=params, headers=headers)

    print(f"Status Code: {response.status_code}")
    print(f"Content-Type: {response.headers.get('content-type')}")
    print(f"Response Body:")
    print(response.text)
    print(f"Response Headers: {dict(response.headers)}")

    return response

if __name__ == "__main__":
    print("Testing Twilio webhook with valid signature...")
    test_webhook()
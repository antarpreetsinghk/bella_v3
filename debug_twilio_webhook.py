#!/usr/bin/env python3
"""
Enhanced Twilio webhook debugging script
Captures detailed request information for troubleshooting signature validation
"""

import os
import json
import logging
from datetime import datetime
from urllib.parse import parse_qsl
import hashlib
import hmac
import base64

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/twilio_debug.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def log_environment():
    """Log all Twilio-related environment variables"""
    logger.info("=== ENVIRONMENT VARIABLES ===")
    twilio_vars = [
        'TWILIO_ACCOUNT_SID',
        'TWILIO_AUTH_TOKEN',
        'TWILIO_PHONE_NUMBER'
    ]

    for var in twilio_vars:
        value = os.getenv(var, 'NOT_SET')
        if 'TOKEN' in var and value != 'NOT_SET':
            masked = value[:4] + '*' * (len(value) - 8) + value[-4:] if len(value) > 8 else '*' * len(value)
            logger.info(f"{var}: {masked}")
        else:
            logger.info(f"{var}: {value}")

def validate_signature_detailed(url, form_data, signature, auth_token):
    """
    Detailed signature validation with step-by-step logging
    """
    logger.info("=== SIGNATURE VALIDATION DETAILS ===")
    logger.info(f"URL: {url}")
    logger.info(f"Auth Token: {auth_token[:4]}***{auth_token[-4:] if len(auth_token) > 8 else '***'}")
    logger.info(f"Received Signature: {signature}")

    # Step 1: Sort parameters
    sorted_params = sorted(form_data.items())
    logger.info(f"Sorted parameters: {sorted_params}")

    # Step 2: Create the string to sign
    string_to_sign = url + ''.join([f'{k}{v}' for k, v in sorted_params])
    logger.info(f"String to sign: {string_to_sign}")
    logger.info(f"String to sign (bytes): {string_to_sign.encode('utf-8')}")

    # Step 3: Create HMAC-SHA1 signature
    expected_signature = base64.b64encode(
        hmac.new(
            auth_token.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            hashlib.sha1
        ).digest()
    ).decode('ascii')

    logger.info(f"Expected signature: {expected_signature}")
    logger.info(f"Signatures match: {expected_signature == signature}")

    return expected_signature == signature

def simulate_webhook_request():
    """
    Simulate a typical Twilio webhook request for testing
    """
    logger.info("=== SIMULATING WEBHOOK REQUEST ===")

    # Typical Twilio voice webhook parameters
    form_data = {
        'AccountSid': 'AC1234567890123456789012345678901234',
        'ApiVersion': '2010-04-01',
        'CallSid': 'CA1234567890123456789012345678901234',
        'CallStatus': 'ringing',
        'Called': '+15551234567',
        'Caller': '+15559876543',
        'Direction': 'inbound',
        'From': '+15559876543',
        'To': '+15551234567'
    }

    url = "http://bella-alb-1924818779.ca-central-1.elb.amazonaws.com/twilio/voice"
    auth_token = os.getenv('TWILIO_AUTH_TOKEN', '')

    if not auth_token:
        logger.error("TWILIO_AUTH_TOKEN not set!")
        return

    # Create valid signature
    string_to_sign = url + ''.join([f'{k}{v}' for k, v in sorted(form_data.items())])
    signature = base64.b64encode(
        hmac.new(
            auth_token.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            hashlib.sha1
        ).digest()
    ).decode('ascii')

    logger.info(f"Generated test signature: {signature}")

    # Validate our own signature
    is_valid = validate_signature_detailed(url, form_data, signature, auth_token)
    logger.info(f"Self-validation result: {is_valid}")

def main():
    """Main debugging function"""
    logger.info(f"=== TWILIO WEBHOOK DEBUG SESSION STARTED ===")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")

    log_environment()
    simulate_webhook_request()

    logger.info("=== DEBUG SESSION COMPLETED ===")
    logger.info(f"Log file saved to: /tmp/twilio_debug.log")

if __name__ == "__main__":
    main()
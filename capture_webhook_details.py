#!/usr/bin/env python3
"""
Webhook request capture utility
Adds detailed logging middleware to capture all webhook requests
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any

class WebhookCapture:
    """Utility class to capture and log webhook details"""

    def __init__(self, log_file: str = "/tmp/webhook_capture.log"):
        self.log_file = log_file
        self.setup_logging()

    def setup_logging(self):
        """Setup detailed logging configuration"""
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - [%(name)s] - %(message)s'
        )

        # File handler
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)

        # Create logger
        self.logger = logging.getLogger('webhook_capture')
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def capture_request_details(self, request, body_bytes: bytes = None):
        """
        Capture comprehensive request details
        """
        self.logger.info("=" * 60)
        self.logger.info("NEW WEBHOOK REQUEST CAPTURED")
        self.logger.info("=" * 60)

        # Basic request info
        self.logger.info(f"Method: {request.method}")
        self.logger.info(f"URL: {str(request.url)}")
        self.logger.info(f"Path: {request.url.path}")
        self.logger.info(f"Query params: {dict(request.query_params)}")

        # Headers
        self.logger.info("Headers:")
        for name, value in request.headers.items():
            if 'signature' in name.lower() or 'authorization' in name.lower():
                self.logger.info(f"  {name}: {value}")
            else:
                self.logger.info(f"  {name}: {value}")

        # Body content
        if body_bytes:
            try:
                body_str = body_bytes.decode('utf-8')
                self.logger.info(f"Raw body: {body_str}")

                # Parse form data
                if request.headers.get('content-type', '').startswith('application/x-www-form-urlencoded'):
                    from urllib.parse import parse_qsl
                    form_data = dict(parse_qsl(body_str))
                    self.logger.info("Parsed form data:")
                    for key, value in form_data.items():
                        self.logger.info(f"  {key}: {value}")

            except Exception as e:
                self.logger.error(f"Error parsing body: {e}")
                self.logger.info(f"Raw body bytes: {body_bytes}")

        # Environment check
        import os
        self.logger.info("Environment check:")
        self.logger.info(f"  TWILIO_AUTH_TOKEN present: {bool(os.getenv('TWILIO_AUTH_TOKEN'))}")
        self.logger.info(f"  BELLA_API_KEY present: {bool(os.getenv('BELLA_API_KEY'))}")

        self.logger.info("=" * 60)

    def log_signature_validation(self, url: str, form_data: Dict[str, Any],
                                signature: str, auth_token: str, result: bool):
        """
        Log detailed signature validation process
        """
        self.logger.info("SIGNATURE VALIDATION PROCESS:")
        self.logger.info(f"  URL for validation: {url}")
        self.logger.info(f"  Form data keys: {list(form_data.keys())}")
        self.logger.info(f"  Signature header: {signature}")
        self.logger.info(f"  Auth token length: {len(auth_token) if auth_token else 0}")
        self.logger.info(f"  Validation result: {result}")

        if not result:
            self.logger.warning("SIGNATURE VALIDATION FAILED!")
            # Additional debugging for failed validation
            sorted_params = sorted(form_data.items())
            string_to_sign = url + ''.join([f'{k}{v}' for k, v in sorted_params])
            self.logger.debug(f"  String to sign: {string_to_sign}")

    def save_request_dump(self, request_data: Dict[str, Any]):
        """
        Save request dump to file for analysis
        """
        timestamp = datetime.now().isoformat()
        dump_file = f"/tmp/webhook_dump_{timestamp.replace(':', '-')}.json"

        try:
            with open(dump_file, 'w') as f:
                json.dump(request_data, f, indent=2, default=str)
            self.logger.info(f"Request dump saved to: {dump_file}")
        except Exception as e:
            self.logger.error(f"Failed to save request dump: {e}")

# Global instance for easy import
webhook_capture = WebhookCapture()
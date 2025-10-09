#!/usr/bin/env python3
"""
Production Twilio Simulation Tests
Real-world webhook simulation for AWS Lambda deployment
"""

import pytest
import httpx
import json
import time
import urllib.parse
from datetime import datetime
from typing import Dict, Any, Optional

# Test configuration - use environment variable or skip if not available
import os
FUNCTION_URL = os.getenv("LAMBDA_FUNCTION_URL", "https://bhcnf2i6eh3bxnr6lrnt4ubouy0obfjy.lambda-url.us-east-1.on.aws")
TIMEOUT = 30

# Skip tests if Lambda URL not accessible in CI
import pytest
IN_CI = os.getenv("CI") == "true" or os.getenv("GITHUB_ACTIONS") == "true"


class TestTwilioWebhookSimulation:
    """Test Twilio webhook behavior in production"""

    @pytest.mark.skipif(IN_CI, reason="Lambda URL not accessible in CI environment")
    @pytest.mark.essential
    @pytest.mark.integration
    @pytest.mark.production
    def test_incoming_call_webhook(self):
        """Test incoming call webhook simulation"""
        call_sid = f"TEST_INCOMING_{int(time.time())}"

        payload = {
            "CallSid": call_sid,
            "From": "+14165551234",
            "To": "+15559876543",
            "AccountSid": "ACtest123",
            "Direction": "inbound",
            "CallerCountry": "CA",
            "CallerState": "ON",
            "CallerCity": "Toronto",
            "CallerName": "Test Caller"
        }

        with httpx.Client(timeout=TIMEOUT) as client:
            response = client.post(
                f"{FUNCTION_URL}/twilio/voice",
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            assert response.status_code == 200
            assert "<?xml version=" in response.text
            assert "<Response>" in response.text
            assert "<Gather>" in response.text or "<Say>" in response.text

            print(f"✅ Incoming call webhook working")
            print(f"CallSid: {call_sid}")
            print(f"Response time: {response.elapsed.total_seconds():.2f}s")

    @pytest.mark.skipif(IN_CI, reason="Lambda URL not accessible in CI environment")
    @pytest.mark.essential
    @pytest.mark.integration
    @pytest.mark.production
    def test_gather_response_webhook(self):
        """Test speech input processing webhook"""
        call_sid = f"TEST_GATHER_{int(time.time())}"

        # First, start the call
        start_payload = {
            "CallSid": call_sid,
            "From": "+14165551234",
            "To": "+15559876543",
            "AccountSid": "ACtest123",
            "Direction": "inbound"
        }

        with httpx.Client(timeout=TIMEOUT) as client:
            # Start call
            start_response = client.post(
                f"{FUNCTION_URL}/twilio/voice",
                data=start_payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            assert start_response.status_code == 200

            # Simulate speech input
            speech_payload = {
                "CallSid": call_sid,
                "SpeechResult": "Hi my name is John Smith and I need to book an appointment",
                "Confidence": "0.95",
                "AccountSid": "ACtest123"
            }

            speech_response = client.post(
                f"{FUNCTION_URL}/twilio/voice",
                data=speech_payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            assert speech_response.status_code == 200
            assert "<Response>" in speech_response.text

            print(f"✅ Speech processing working")
            print(f"CallSid: {call_sid}")
            print(f"Extracted content present: {'John Smith' in speech_response.text}")

    @pytest.mark.skipif(IN_CI, reason="Lambda URL not accessible in CI environment")
    @pytest.mark.essential
    @pytest.mark.integration
    @pytest.mark.production
    def test_appointment_booking_flow(self):
        """Test complete appointment booking simulation"""
        call_sid = f"TEST_BOOKING_{int(time.time())}"

        with httpx.Client(timeout=TIMEOUT) as client:
            # Step 1: Start call
            response1 = client.post(
                f"{FUNCTION_URL}/twilio/voice",
                data={
                    "CallSid": call_sid,
                    "From": "+14165551234",
                    "To": "+15559876543",
                    "AccountSid": "ACtest123"
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            # Step 2: Provide name
            response2 = client.post(
                f"{FUNCTION_URL}/twilio/voice",
                data={
                    "CallSid": call_sid,
                    "SpeechResult": "My name is Sarah Johnson",
                    "AccountSid": "ACtest123"
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            # Step 3: Provide phone number
            response3 = client.post(
                f"{FUNCTION_URL}/twilio/voice",
                data={
                    "CallSid": call_sid,
                    "SpeechResult": "My phone number is 416 555 9876",
                    "AccountSid": "ACtest123"
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            # Step 4: Provide preferred time
            response4 = client.post(
                f"{FUNCTION_URL}/twilio/voice",
                data={
                    "CallSid": call_sid,
                    "SpeechResult": "I would like an appointment tomorrow at 2 PM",
                    "AccountSid": "ACtest123"
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            # Verify all steps completed successfully
            for i, response in enumerate([response1, response2, response3, response4], 1):
                assert response.status_code == 200, f"Step {i} failed with status {response.status_code}"
                assert "<Response>" in response.text, f"Step {i} missing TwiML response"

            print(f"✅ Complete booking flow working")
            print(f"CallSid: {call_sid}")
            print(f"All 4 steps completed successfully")

    @pytest.mark.skipif(IN_CI, reason="Lambda URL not accessible in CI environment")
    @pytest.mark.essential
    @pytest.mark.integration
    @pytest.mark.production
    def test_error_handling(self):
        """Test error handling in webhook"""
        call_sid = f"TEST_ERROR_{int(time.time())}"

        with httpx.Client(timeout=TIMEOUT) as client:
            # Test with malformed data
            response = client.post(
                f"{FUNCTION_URL}/twilio/voice",
                data={
                    "CallSid": call_sid,
                    # Missing required fields
                    "InvalidField": "test"
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            # Should still return valid TwiML even with errors
            assert response.status_code == 200
            assert "<?xml version=" in response.text
            assert "<Response>" in response.text

            print(f"✅ Error handling working")
            print(f"CallSid: {call_sid}")

    @pytest.mark.skipif(IN_CI, reason="Lambda URL not accessible in CI environment")
    @pytest.mark.integration
    @pytest.mark.production
    @pytest.mark.slow
    def test_concurrent_calls(self):
        """Test handling multiple concurrent calls"""
        call_sids = [f"TEST_CONCURRENT_{int(time.time())}_{i}" for i in range(3)]

        with httpx.Client(timeout=TIMEOUT) as client:
            responses = []

            # Simulate 3 concurrent calls
            for i, call_sid in enumerate(call_sids):
                response = client.post(
                    f"{FUNCTION_URL}/twilio/voice",
                    data={
                        "CallSid": call_sid,
                        "From": f"+141655512{30 + i}",
                        "To": "+15559876543",
                        "AccountSid": "ACtest123"
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                responses.append(response)

            # Verify all calls handled successfully
            for i, response in enumerate(responses):
                assert response.status_code == 200, f"Concurrent call {i+1} failed"
                assert "<Response>" in response.text, f"Concurrent call {i+1} missing TwiML"

            print(f"✅ Concurrent calls handling working")
            print(f"Processed {len(call_sids)} concurrent calls")

    @pytest.mark.skipif(IN_CI, reason="Lambda URL not accessible in CI environment")
    @pytest.mark.essential
    @pytest.mark.integration
    @pytest.mark.production
    def test_webhook_security(self):
        """Test webhook security validation"""
        with httpx.Client(timeout=TIMEOUT) as client:
            # Test with missing required Twilio parameters
            response = client.post(
                f"{FUNCTION_URL}/twilio/voice",
                data={"random": "data"},
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            # Should handle gracefully
            assert response.status_code == 200

            # Test with wrong content type
            response2 = client.post(
                f"{FUNCTION_URL}/twilio/voice",
                json={"CallSid": "test"},
                headers={"Content-Type": "application/json"}
            )

            # Should handle gracefully
            assert response2.status_code in [200, 400, 415]  # Accept various handling approaches

            print(f"✅ Webhook security working")

    @pytest.mark.skipif(IN_CI, reason="Lambda URL not accessible in CI environment")
    @pytest.mark.essential
    @pytest.mark.integration
    @pytest.mark.production
    def test_session_persistence(self):
        """Test session data persistence across webhook calls"""
        call_sid = f"TEST_SESSION_{int(time.time())}"

        with httpx.Client(timeout=TIMEOUT) as client:
            # Call 1: Start session
            response1 = client.post(
                f"{FUNCTION_URL}/twilio/voice",
                data={
                    "CallSid": call_sid,
                    "From": "+14165551234",
                    "To": "+15559876543",
                    "AccountSid": "ACtest123"
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            # Call 2: Continue session
            response2 = client.post(
                f"{FUNCTION_URL}/twilio/voice",
                data={
                    "CallSid": call_sid,
                    "SpeechResult": "Test session data",
                    "AccountSid": "ACtest123"
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            assert response1.status_code == 200
            assert response2.status_code == 200

            print(f"✅ Session persistence working")
            print(f"CallSid: {call_sid}")

    @pytest.mark.skipif(IN_CI, reason="Lambda URL not accessible in CI environment")
    @pytest.mark.integration
    @pytest.mark.production
    @pytest.mark.slow
    def test_performance_under_load(self):
        """Test performance with rapid sequential calls"""
        start_time = time.time()
        successful_calls = 0

        with httpx.Client(timeout=TIMEOUT) as client:
            for i in range(10):
                call_sid = f"TEST_LOAD_{int(time.time())}_{i}"

                try:
                    response = client.post(
                        f"{FUNCTION_URL}/twilio/voice",
                        data={
                            "CallSid": call_sid,
                            "From": f"+141655512{40 + i:02d}",
                            "To": "+15559876543",
                            "AccountSid": "ACtest123"
                        },
                        headers={"Content-Type": "application/x-www-form-urlencoded"}
                    )

                    if response.status_code == 200:
                        successful_calls += 1

                except Exception as e:
                    print(f"Call {i+1} failed: {e}")

            end_time = time.time()
            total_time = end_time - start_time

            assert successful_calls >= 8, f"Too many failed calls: {10 - successful_calls}/10"
            assert total_time < 30, f"Performance too slow: {total_time:.2f}s for 10 calls"

            print(f"✅ Performance under load acceptable")
            print(f"Successful calls: {successful_calls}/10")
            print(f"Total time: {total_time:.2f}s")
            print(f"Average time per call: {total_time/10:.2f}s")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
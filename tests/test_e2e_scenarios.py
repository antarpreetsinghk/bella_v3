#!/usr/bin/env python3
"""
End-to-end scenario tests for complete user journeys.
Tests realistic customer interactions from call start to appointment booking.
"""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Add app to Python path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.main import app


class TestCommonUserScenarios:
    """Test common real-world user scenarios"""

    @patch('app.services.canadian_extraction.extract_canadian_time')
    @patch('app.services.booking.book_from_transcript')
    @pytest.mark.essential
    @pytest.mark.unit
    def test_quick_booking_scenario(self, mock_booking, mock_time):
        """Test quick booking: customer knows exactly what they want"""
        client = TestClient(app)
        call_sid = "TEST_QUICK_BOOKING"

        # Mock time extraction
        tomorrow_2pm = datetime.now(ZoneInfo("UTC")) + timedelta(days=1)
        tomorrow_2pm = tomorrow_2pm.replace(hour=14, minute=0, second=0, microsecond=0)
        mock_time.return_value = tomorrow_2pm

        # Mock successful booking
        mock_result = MagicMock()
        mock_result.created = True
        mock_result.message_for_caller = "Perfect! Your appointment is booked for tomorrow at 2 PM."
        mock_booking.return_value = mock_result

        # Step 1: Call with caller ID
        response = client.post("/twilio/voice", data={
            "CallSid": call_sid,
            "From": "+14165551234",
            "AccountSid": "TEST_ACCOUNT"
        })
        assert response.status_code == 200

        # Step 2: Provide all info at once
        response = client.post("/twilio/voice/collect", data={
            "CallSid": call_sid,
            "SpeechResult": "Hi, this is John Smith, book me tomorrow at 2 PM please",
            "Confidence": "0.92"
        })
        assert response.status_code == 200

        # Should process the complete request efficiently

    @patch('app.services.canadian_extraction.extract_canadian_time')
    @pytest.mark.essential
    @pytest.mark.unit
    def test_step_by_step_booking_scenario(self, mock_time):
        """Test methodical step-by-step booking"""
        client = TestClient(app)
        call_sid = "TEST_STEP_BY_STEP"

        # Mock time extraction
        friday_10am = datetime.now(ZoneInfo("UTC")) + timedelta(days=4)
        friday_10am = friday_10am.replace(hour=10, minute=0, second=0, microsecond=0)
        mock_time.return_value = friday_10am

        # Step 1: Initial call
        response = client.post("/twilio/voice", data={
            "CallSid": call_sid,
            "From": "",  # No caller ID
            "AccountSid": "TEST_ACCOUNT"
        })
        assert response.status_code == 200
        assert "name" in response.text.lower()

        # Step 2: Provide name
        response = client.post("/twilio/voice/collect", data={
            "CallSid": call_sid,
            "SpeechResult": "Mary Johnson",
            "Confidence": "0.95"
        })
        assert response.status_code == 200
        assert "Mary Johnson" in response.text

        # Step 3: Confirm name
        response = client.post("/twilio/voice/collect", data={
            "CallSid": call_sid,
            "SpeechResult": "yes",
            "Confidence": "0.90"
        })
        assert response.status_code == 200
        assert "phone" in response.text.lower()

        # Step 4: Provide phone
        response = client.post("/twilio/voice/collect", data={
            "CallSid": call_sid,
            "SpeechResult": "416-555-9876",
            "Confidence": "0.88"
        })
        assert response.status_code == 200
        assert ("time" in response.text.lower() or "when" in response.text.lower())

        # Step 5: Provide time
        response = client.post("/twilio/voice/collect", data={
            "CallSid": call_sid,
            "SpeechResult": "Friday at 10 AM",
            "Confidence": "0.91"
        })
        assert response.status_code == 200
        # Should proceed to duration or confirmation

    @patch('app.services.redis_session.get_caller_profile')
    @patch('app.services.redis_session.get_personalized_greeting')
    @pytest.mark.essential
    @pytest.mark.unit
    def test_returning_customer_scenario(self, mock_greeting, mock_profile):
        """Test returning customer with profile recognition"""
        client = TestClient(app)
        call_sid = "TEST_RETURNING_CUSTOMER"

        # Mock returning customer profile
        mock_profile_obj = MagicMock()
        mock_profile_obj.mobile = "+14165551234"
        mock_profile_obj.full_name = "Sarah Davis"
        mock_profile_obj.is_returning = True
        mock_profile_obj.preferred_duration = 45
        mock_profile_obj.preferred_times = ["afternoon"]
        mock_profile_obj.call_count = 4
        mock_profile.return_value = mock_profile_obj

        mock_greeting.return_value = (
            "Hi Sarah! Welcome back. I see you've booked 4 appointments with us. "
            "Should I book your usual 45-minute appointment?"
        )

        # Step 1: Call with known number
        response = client.post("/twilio/voice", data={
            "CallSid": call_sid,
            "From": "+14165551234",
            "AccountSid": "TEST_ACCOUNT"
        })
        assert response.status_code == 200
        assert "Sarah" in response.text
        assert "Welcome back" in response.text
        assert "45-minute" in response.text

        # Should skip directly to scheduling with preferences

    @pytest.mark.essential
    @pytest.mark.unit
    def test_confused_customer_scenario(self):
        """Test customer who is confused or needs help"""
        client = TestClient(app)
        call_sid = "TEST_CONFUSED_CUSTOMER"

        # Step 1: Initial call
        client.post("/twilio/voice", data={
            "CallSid": call_sid,
            "From": "+14165551234",
            "AccountSid": "TEST_ACCOUNT"
        })

        # Step 2: Unclear response
        response = client.post("/twilio/voice/collect", data={
            "CallSid": call_sid,
            "SpeechResult": "um... I'm not sure... how does this work?",
            "Confidence": "0.60"
        })
        assert response.status_code == 200
        # Should provide helpful guidance

        # Step 3: Still confused
        response = client.post("/twilio/voice/collect", data={
            "CallSid": call_sid,
            "SpeechResult": "what?",
            "Confidence": "0.40"
        })
        assert response.status_code == 200
        # Should continue to help patiently

    @pytest.mark.essential
    @pytest.mark.unit
    def test_urgent_appointment_scenario(self):
        """Test customer needing urgent/same-day appointment"""
        client = TestClient(app)
        call_sid = "TEST_URGENT_APPOINTMENT"

        # Initial setup
        client.post("/twilio/voice", data={
            "CallSid": call_sid,
            "From": "+14165551234",
            "AccountSid": "TEST_ACCOUNT"
        })

        # Request urgent appointment
        response = client.post("/twilio/voice/collect", data={
            "CallSid": call_sid,
            "SpeechResult": "I need an appointment today if possible, it's urgent",
            "Confidence": "0.93"
        })
        assert response.status_code == 200
        # Should handle urgency appropriately


class TestDifficultScenarios:
    """Test challenging scenarios and edge cases"""

    @pytest.mark.essential
    @pytest.mark.unit
    def test_poor_connection_scenario(self):
        """Test handling of poor phone connection with low speech quality"""
        client = TestClient(app)
        call_sid = "TEST_POOR_CONNECTION"

        # Initial call
        client.post("/twilio/voice", data={
            "CallSid": call_sid,
            "From": "+14165551234",
            "AccountSid": "TEST_ACCOUNT"
        })

        # Multiple attempts with poor quality
        for attempt in range(3):
            response = client.post("/twilio/voice/collect", data={
                "CallSid": call_sid,
                "SpeechResult": "crackle static John noise Smith static",
                "Confidence": "0.25"  # Very low confidence
            })
            assert response.status_code == 200
            # Should ask to repeat or suggest alternatives

        # Finally clear speech
        response = client.post("/twilio/voice/collect", data={
            "CallSid": call_sid,
            "SpeechResult": "John Smith",
            "Confidence": "0.95"
        })
        assert response.status_code == 200
        assert "John Smith" in response.text

    @pytest.mark.essential
    @pytest.mark.unit
    def test_elderly_customer_scenario(self):
        """Test patient handling for elderly customers who speak slowly"""
        client = TestClient(app)
        call_sid = "TEST_ELDERLY_CUSTOMER"

        # Initial call
        client.post("/twilio/voice", data={
            "CallSid": call_sid,
            "From": "+14165551234",
            "AccountSid": "TEST_ACCOUNT"
        })

        # Slow, deliberate speech
        response = client.post("/twilio/voice/collect", data={
            "CallSid": call_sid,
            "SpeechResult": "Hello... my name... is... Dorothy... Smith",
            "Confidence": "0.85"
        })
        assert response.status_code == 200
        # Should handle slow speech patterns

    @pytest.mark.essential
    @pytest.mark.unit
    def test_accent_heavy_scenario(self):
        """Test handling of heavy accents"""
        client = TestClient(app)
        call_sid = "TEST_HEAVY_ACCENT"

        # Initial call
        client.post("/twilio/voice", data={
            "CallSid": call_sid,
            "From": "+14165551234",
            "AccountSid": "TEST_ACCOUNT"
        })

        # Name with accent-affected pronunciation
        response = client.post("/twilio/voice/collect", data={
            "CallSid": call_sid,
            "SpeechResult": "Rajesh Patel",  # Common name that might be mispronounced
            "Confidence": "0.70"
        })
        assert response.status_code == 200
        # Should handle international names

    @pytest.mark.essential
    @pytest.mark.unit
    def test_background_noise_scenario(self):
        """Test handling of significant background noise"""
        client = TestClient(app)
        call_sid = "TEST_BACKGROUND_NOISE"

        # Initial call
        client.post("/twilio/voice", data={
            "CallSid": call_sid,
            "From": "+14165551234",
            "AccountSid": "TEST_ACCOUNT"
        })

        # Speech with background noise
        response = client.post("/twilio/voice/collect", data={
            "CallSid": call_sid,
            "SpeechResult": "[car honking] Michael [traffic noise] Johnson [engine revving]",
            "Confidence": "0.55"
        })
        assert response.status_code == 200
        # Should extract name despite noise

    @pytest.mark.essential
    @pytest.mark.unit
    def test_multiple_people_scenario(self):
        """Test handling when multiple people are speaking"""
        client = TestClient(app)
        call_sid = "TEST_MULTIPLE_PEOPLE"

        # Initial call
        client.post("/twilio/voice", data={
            "CallSid": call_sid,
            "From": "+14165551234",
            "AccountSid": "TEST_ACCOUNT"
        })

        # Multiple voices
        response = client.post("/twilio/voice/collect", data={
            "CallSid": call_sid,
            "SpeechResult": "John Smith no wait Mary said her name is Mary Johnson",
            "Confidence": "0.65"
        })
        assert response.status_code == 200
        # Should handle confusion and ask for clarification


class TestBusinessScenarios:
    """Test business-specific scenarios"""

    @patch('app.core.business.is_within_hours')
    @pytest.mark.essential
    @pytest.mark.unit
    def test_after_hours_call_scenario(self, mock_business_hours):
        """Test customer calling outside business hours"""
        client = TestClient(app)
        call_sid = "TEST_AFTER_HOURS"

        # Mock as outside business hours
        mock_business_hours.return_value = False

        response = client.post("/twilio/voice", data={
            "CallSid": call_sid,
            "From": "+14165551234",
            "AccountSid": "TEST_ACCOUNT"
        })
        assert response.status_code == 200
        # Should still handle the call but might mention hours

    @patch('app.services.google_calendar.check_calendar_availability')
    @pytest.mark.essential
    @pytest.mark.unit
    def test_fully_booked_day_scenario(self, mock_availability):
        """Test when requested day is fully booked"""
        client = TestClient(app)
        call_sid = "TEST_FULLY_BOOKED"

        # Mock calendar as fully booked
        mock_availability.return_value = {
            "available": False,
            "reason": "No available slots",
            "alternative_slots": [
                {"date": "2025-10-08", "time": "10:00 AM"},
                {"date": "2025-10-08", "time": "2:00 PM"}
            ]
        }

        # Complete flow to time request
        client.post("/twilio/voice", data={
            "CallSid": call_sid,
            "From": "+14165551234",
            "AccountSid": "TEST_ACCOUNT"
        })

        response = client.post("/twilio/voice/collect", data={
            "CallSid": call_sid,
            "SpeechResult": "tomorrow at 2 PM",
            "Confidence": "0.90"
        })
        assert response.status_code == 200
        # Should suggest alternatives

    @patch('app.services.google_calendar.get_available_slots')
    @pytest.mark.essential
    @pytest.mark.unit
    def test_limited_availability_scenario(self, mock_slots):
        """Test when only limited time slots are available"""
        client = TestClient(app)
        call_sid = "TEST_LIMITED_AVAILABILITY"

        # Mock limited availability
        mock_slots.return_value = [
            {"start": "2025-10-08T09:00:00Z", "end": "2025-10-08T09:30:00Z"},
            {"start": "2025-10-08T16:30:00Z", "end": "2025-10-08T17:00:00Z"}
        ]

        # Request popular time
        response = client.post("/twilio/voice/collect", data={
            "CallSid": call_sid,
            "SpeechResult": "tomorrow afternoon",
            "Confidence": "0.85"
        })
        assert response.status_code == 200
        # Should offer available alternatives

    @pytest.mark.essential
    @pytest.mark.unit
    def test_holiday_scheduling_scenario(self):
        """Test scheduling around holidays"""
        client = TestClient(app)
        call_sid = "TEST_HOLIDAY_SCHEDULING"

        # Request appointment on holiday
        response = client.post("/twilio/voice/collect", data={
            "CallSid": call_sid,
            "SpeechResult": "Christmas Day at 10 AM",
            "Confidence": "0.90"
        })
        # Should handle holiday appropriately


class TestErrorRecoveryScenarios:
    """Test error recovery and resilience scenarios"""

    @patch('app.services.redis_session.get_redis_client')
    @pytest.mark.essential
    @pytest.mark.integration
    def test_redis_failure_scenario(self, mock_redis):
        """Test handling when Redis becomes unavailable mid-call"""
        client = TestClient(app)
        call_sid = "TEST_REDIS_FAILURE"

        # Start with Redis working
        mock_client = MagicMock()
        mock_redis.return_value = mock_client

        # Initial call
        client.post("/twilio/voice", data={
            "CallSid": call_sid,
            "From": "+14165551234",
            "AccountSid": "TEST_ACCOUNT"
        })

        # Redis fails mid-call
        mock_redis.return_value = None

        # Should continue working with in-memory fallback
        response = client.post("/twilio/voice/collect", data={
            "CallSid": call_sid,
            "SpeechResult": "John Smith",
            "Confidence": "0.95"
        })
        assert response.status_code == 200

    @patch('app.services.google_calendar.create_calendar_event')
    @pytest.mark.essential
    @pytest.mark.unit
    def test_calendar_service_failure_scenario(self, mock_calendar):
        """Test handling when Google Calendar service fails"""
        client = TestClient(app)
        call_sid = "TEST_CALENDAR_FAILURE"

        # Mock calendar service failure
        mock_calendar.side_effect = Exception("Calendar service unavailable")

        # Should still complete booking without calendar sync
        # (Implementation dependent)

    @pytest.mark.integration
    @pytest.mark.slow
    def test_database_timeout_scenario(self):
        """Test handling of database timeouts"""
        # Would require mocking database operations
        # Should gracefully handle and retry or provide alternatives

    @pytest.mark.essential
    @pytest.mark.unit
    def test_network_interruption_scenario(self):
        """Test handling of network interruptions"""
        client = TestClient(app)
        call_sid = "TEST_NETWORK_INTERRUPTION"

        # Simulate network issues with timeouts
        # Should handle gracefully and maintain session state


class TestComplexUserJourneys:
    """Test complex, multi-interaction user journeys"""

    @pytest.mark.essential
    @pytest.mark.unit
    def test_appointment_modification_journey(self):
        """Test customer calling to modify existing appointment"""
        client = TestClient(app)
        call_sid = "TEST_MODIFICATION_JOURNEY"

        # Customer wants to reschedule
        response = client.post("/twilio/voice/collect", data={
            "CallSid": call_sid,
            "SpeechResult": "I need to reschedule my appointment from tomorrow to Friday",
            "Confidence": "0.88"
        })
        assert response.status_code == 200
        # Should handle modification request

    @pytest.mark.essential
    @pytest.mark.unit
    def test_group_appointment_journey(self):
        """Test booking for multiple people"""
        client = TestClient(app)
        call_sid = "TEST_GROUP_APPOINTMENT"

        response = client.post("/twilio/voice/collect", data={
            "CallSid": call_sid,
            "SpeechResult": "I need to book for myself and my husband, two appointments",
            "Confidence": "0.85"
        })
        assert response.status_code == 200
        # Should handle group booking appropriately

    @pytest.mark.essential
    @pytest.mark.unit
    def test_special_requirements_journey(self):
        """Test customer with special requirements"""
        client = TestClient(app)
        call_sid = "TEST_SPECIAL_REQUIREMENTS"

        response = client.post("/twilio/voice/collect", data={
            "CallSid": call_sid,
            "SpeechResult": "I need extra time and a ground floor room please",
            "Confidence": "0.90"
        })
        assert response.status_code == 200
        # Should capture special requirements in notes

    @pytest.mark.essential
    @pytest.mark.unit
    def test_cancellation_journey(self):
        """Test appointment cancellation flow"""
        client = TestClient(app)
        call_sid = "TEST_CANCELLATION_JOURNEY"

        response = client.post("/twilio/voice/collect", data={
            "CallSid": call_sid,
            "SpeechResult": "I need to cancel my appointment for tomorrow",
            "Confidence": "0.92"
        })
        assert response.status_code == 200
        # Should handle cancellation appropriately


class TestPerformanceScenarios:
    """Test performance under various load conditions"""

    @pytest.mark.essential
    @pytest.mark.unit
    def test_peak_hour_simulation(self):
        """Test system behavior during peak calling hours"""
        client = TestClient(app)
        import threading
        import time

        results = []

        def simulate_call(call_id):
            try:
                start_time = time.time()
                response = client.post("/twilio/voice", data={
                    "CallSid": f"TEST_PEAK_{call_id}",
                    "From": f"+141655512{call_id:02d}",
                    "AccountSid": "TEST_ACCOUNT"
                })
                end_time = time.time()
                results.append({
                    "call_id": call_id,
                    "status": response.status_code,
                    "response_time": end_time - start_time
                })
            except Exception as e:
                results.append({
                    "call_id": call_id,
                    "status": "ERROR",
                    "error": str(e)
                })

        # Simulate 20 concurrent calls
        threads = []
        for i in range(20):
            thread = threading.Thread(target=simulate_call, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join(timeout=10)

        # Verify performance
        assert len(results) == 20
        successful_calls = [r for r in results if r["status"] == 200]
        assert len(successful_calls) >= 18  # Allow for some variance

        # Check response times
        avg_response_time = sum(r["response_time"] for r in successful_calls) / len(successful_calls)
        assert avg_response_time < 2.0  # Average under 2 seconds

    @pytest.mark.essential
    @pytest.mark.unit
    def test_long_call_session(self):
        """Test very long call session with many interactions"""
        client = TestClient(app)
        call_sid = "TEST_LONG_SESSION"

        # Initial call
        client.post("/twilio/voice", data={
            "CallSid": call_sid,
            "From": "+14165551234",
            "AccountSid": "TEST_ACCOUNT"
        })

        # Many interactions (simulating confused customer)
        for i in range(20):
            response = client.post("/twilio/voice/collect", data={
                "CallSid": call_sid,
                "SpeechResult": f"unclear response {i}",
                "Confidence": "0.30"
            })
            assert response.status_code == 200

        # Should maintain session throughout

    @pytest.mark.slow
    def test_memory_usage_under_load(self):
        """Test memory usage during high call volume"""
        import gc
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        client = TestClient(app)

        # Create many sessions
        for i in range(100):
            client.post("/twilio/voice", data={
                "CallSid": f"TEST_MEMORY_{i}",
                "From": f"+141655512{i:02d}",
                "AccountSid": "TEST_ACCOUNT"
            })

        # Force garbage collection
        gc.collect()

        final_memory = process.memory_info().rss
        memory_growth = final_memory - initial_memory

        # Memory growth should be reasonable (less than 100MB)
        assert memory_growth < 100 * 1024 * 1024


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
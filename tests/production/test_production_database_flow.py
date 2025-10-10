#!/usr/bin/env python3
"""
Production Database Flow Testing
End-to-end tests that validate call flows save correctly to production database.

These tests:
- Make real HTTP requests to voice webhook
- Validate database records are created correctly
- Check Google Calendar integration
- Verify data accuracy and integrity
- Test duplicate prevention
- Validate automatic cleanup

SAFETY:
- All appointments created are marked with is_test_data=True
- Automatic cleanup after each test
- No real customer data is affected
"""

import pytest
import pytest_asyncio
import httpx
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from app.db.models.appointment import Appointment
from app.db.models.user import User
from app.crud.user import get_user_by_mobile, create_user
from app.crud.appointment import get_user_appointments


# Test configuration
PRODUCTION_TEST_URL = os.getenv("PRODUCTION_TEST_URL", os.getenv("FUNCTION_URL", ""))
PRODUCTION_API_KEY = os.getenv("PRODUCTION_API_KEY", "")
TEST_TIMEOUT = int(os.getenv("PRODUCTION_TEST_TIMEOUT", "30"))

# Skip marker
skip_if_no_url = pytest.mark.skipif(
    not PRODUCTION_TEST_URL,
    reason="PRODUCTION_TEST_URL or FUNCTION_URL environment variable not set"
)


def get_request_headers(api_key: Optional[str] = None) -> Dict[str, str]:
    """Generate headers for production test requests"""
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    if api_key or PRODUCTION_API_KEY:
        headers["X-API-Key"] = api_key or PRODUCTION_API_KEY
    return headers


@pytest.mark.prod_db
@pytest.mark.prod_db_write
@pytest.mark.prod_e2e
class TestProductionCallFlowWithDatabase:
    """
    End-to-end tests that validate complete call flows with database persistence.

    Tests the full journey:
    1. Incoming call webhook
    2. User interaction (voice prompts)
    3. Data extraction and validation
    4. Database record creation
    5. Google Calendar sync (if enabled)
    6. Data cleanup
    """

    @skip_if_no_url
    async def test_complete_booking_saves_to_database(
        self,
        prod_db: AsyncSession,
        test_call_context: Dict[str, Any]
    ):
        """
        Test that a complete booking flow creates correct database records.

        Flow:
        1. New customer call
        2. Provide name, phone, appointment time
        3. Confirm booking
        4. Verify appointment in database
        5. Verify user profile created
        """
        # Arrange: Prepare test call data
        call_sid = test_call_context["call_sid"]
        from_number = test_call_context["from_number"]
        test_name = test_call_context["test_name"]

        # Future appointment time (tomorrow at 2 PM)
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        appointment_time = tomorrow.replace(hour=14, minute=0, second=0, microsecond=0)

        # Count existing test appointments before
        count_before = await prod_db.execute(
            select(func.count(Appointment.id)).where(Appointment.is_test_data == True)
        )
        initial_count = count_before.scalar() or 0

        # Act: Simulate call flow
        async with httpx.AsyncClient(timeout=TEST_TIMEOUT) as client:
            # 1. Initial call webhook
            response = await client.post(
                f"{PRODUCTION_TEST_URL}/twilio/voice",
                headers=get_request_headers(),
                data={
                    "CallSid": call_sid,
                    "From": from_number,
                    "To": "+14165551234",
                    "CallStatus": "in-progress",
                }
            )
            assert response.status_code == 200
            assert "text/xml" in response.headers["content-type"]

            # 2. Provide name
            response = await client.post(
                f"{PRODUCTION_TEST_URL}/twilio/voice",
                headers=get_request_headers(),
                data={
                    "CallSid": call_sid,
                    "SpeechResult": test_name,
                    "Confidence": "0.95",
                }
            )
            assert response.status_code == 200

            # 3. Confirm name
            response = await client.post(
                f"{PRODUCTION_TEST_URL}/twilio/voice",
                headers=get_request_headers(),
                data={
                    "CallSid": call_sid,
                    "SpeechResult": "yes",
                    "Confidence": "0.98",
                }
            )
            assert response.status_code == 200

            # 4. Provide appointment time
            time_phrase = "tomorrow at 2 PM"
            response = await client.post(
                f"{PRODUCTION_TEST_URL}/twilio/voice",
                headers=get_request_headers(),
                data={
                    "CallSid": call_sid,
                    "SpeechResult": time_phrase,
                    "Confidence": "0.92",
                }
            )
            assert response.status_code == 200

            # 5. Confirm booking
            response = await client.post(
                f"{PRODUCTION_TEST_URL}/twilio/voice",
                headers=get_request_headers(),
                data={
                    "CallSid": call_sid,
                    "SpeechResult": "yes",
                    "Confidence": "0.99",
                }
            )
            assert response.status_code == 200
            assert b"confirmed" in response.content.lower() or b"booked" in response.content.lower()

        # Assert: Verify database records
        # 1. Check user was created
        user = await get_user_by_mobile(prod_db, from_number)
        assert user is not None, "User should be created in database"
        assert user.full_name == test_name
        assert user.mobile_number == from_number

        # 2. Check appointment was created
        appointments = await get_user_appointments(prod_db, user.id, future_only=True)
        assert len(appointments) > 0, "Appointment should be created"

        appointment = appointments[0]
        assert appointment.is_test_data is True, "Appointment must be marked as test data"
        assert appointment.status == "booked"
        assert appointment.user_id == user.id

        # 3. Verify time is correct (within 1 hour tolerance)
        time_diff = abs((appointment.starts_at - appointment_time).total_seconds())
        assert time_diff < 3600, f"Appointment time should be close to requested time (diff: {time_diff}s)"

        # 4. Count test appointments increased
        count_after = await prod_db.execute(
            select(func.count(Appointment.id)).where(Appointment.is_test_data == True)
        )
        final_count = count_after.scalar() or 0
        assert final_count > initial_count, "Test appointment count should increase"

        # Track for cleanup
        prod_db.info["test_appointment_ids"].append(appointment.id)

    @skip_if_no_url
    async def test_duplicate_prevention_in_production(
        self,
        prod_db: AsyncSession,
        test_call_context: Dict[str, Any]
    ):
        """
        Test that duplicate appointments are prevented in production database.

        Flow:
        1. Create first appointment
        2. Attempt to create duplicate (same user, same time)
        3. Verify only one appointment exists
        """
        # Arrange: Create user and initial appointment
        from_number = test_call_context["from_number"]
        test_name = test_call_context["test_name"]

        user = await create_user(
            prod_db,
            mobile=from_number,
            full_name=test_name
        )

        # Future appointment time
        appointment_time = datetime.now(timezone.utc) + timedelta(days=2, hours=3)

        # Create first appointment directly in DB
        from app.crud.appointment import create_appointment_unique
        appointment1 = await create_appointment_unique(
            prod_db,
            user_id=user.id,
            starts_at_utc=appointment_time,
            is_test_data=True
        )
        prod_db.info["test_appointment_ids"].append(appointment1.id)

        # Act: Try to create duplicate via voice call
        call_sid = test_call_context["call_sid"]

        async with httpx.AsyncClient(timeout=TEST_TIMEOUT) as client:
            # Simulate booking flow for same time
            # Initial call
            await client.post(
                f"{PRODUCTION_TEST_URL}/twilio/voice",
                headers=get_request_headers(),
                data={
                    "CallSid": call_sid,
                    "From": from_number,
                    "To": "+14165551234",
                    "CallStatus": "in-progress",
                }
            )

            # Provide appointment time (same as existing)
            time_phrase = "in 2 days at 3 AM"
            response = await client.post(
                f"{PRODUCTION_TEST_URL}/twilio/voice",
                headers=get_request_headers(),
                data={
                    "CallSid": call_sid,
                    "SpeechResult": time_phrase,
                    "Confidence": "0.92",
                }
            )

            # System should detect duplicate
            assert response.status_code == 200
            # Response should indicate conflict or alternative
            content = response.content.decode().lower()
            assert "already" in content or "conflict" in content or "different" in content

        # Assert: Verify only one appointment exists at that time
        appointments = await get_user_appointments(prod_db, user.id, future_only=True)
        appointments_at_time = [
            a for a in appointments
            if abs((a.starts_at - appointment_time).total_seconds()) < 300  # 5 min window
        ]
        assert len(appointments_at_time) == 1, "Should only have one appointment at that time"

    @skip_if_no_url
    async def test_user_creation_and_reuse(
        self,
        prod_db: AsyncSession,
        test_call_context: Dict[str, Any]
    ):
        """
        Test that user profiles are created once and reused correctly.

        Flow:
        1. First call creates user
        2. Second call from same number reuses user
        3. Verify no duplicate users
        """
        # Arrange
        call_sid = test_call_context["call_sid"]
        from_number = test_call_context["from_number"]
        test_name = test_call_context["test_name"]

        # Count users with this phone before
        count_before = await prod_db.execute(
            select(func.count(User.id)).where(User.mobile_number == from_number)
        )
        initial_user_count = count_before.scalar() or 0

        # Act: Make two calls from same number
        async with httpx.AsyncClient(timeout=TEST_TIMEOUT) as client:
            # First call
            for i in range(2):
                call_sid_unique = f"{call_sid}_{i}"

                # Initial webhook
                await client.post(
                    f"{PRODUCTION_TEST_URL}/twilio/voice",
                    headers=get_request_headers(),
                    data={
                        "CallSid": call_sid_unique,
                        "From": from_number,
                        "To": "+14165551234",
                        "CallStatus": "in-progress",
                    }
                )

                # Provide name
                await client.post(
                    f"{PRODUCTION_TEST_URL}/twilio/voice",
                    headers=get_request_headers(),
                    data={
                        "CallSid": call_sid_unique,
                        "SpeechResult": f"{test_name} Call{i}",
                        "Confidence": "0.95",
                    }
                )

        # Assert: Should only create one user
        count_after = await prod_db.execute(
            select(func.count(User.id)).where(User.mobile_number == from_number)
        )
        final_user_count = count_after.scalar() or 0

        assert final_user_count == initial_user_count + 1, "Should only create one user for same phone"

    @skip_if_no_url
    async def test_appointment_data_accuracy(
        self,
        prod_db: AsyncSession,
        test_call_context: Dict[str, Any]
    ):
        """
        Test that appointment data is accurately stored in database.

        Validates:
        - Correct timezone handling
        - Accurate time extraction
        - Duration is set correctly
        - Status is properly initialized
        - Test data flag is set
        - Timestamps are timezone-aware
        """
        # Arrange
        from_number = test_call_context["from_number"]
        test_name = test_call_context["test_name"]

        user = await create_user(
            prod_db,
            mobile=from_number,
            full_name=test_name
        )

        # Act: Create appointment with specific time
        specific_time = datetime.now(timezone.utc) + timedelta(days=3, hours=10, minutes=30)

        from app.crud.appointment import create_appointment_unique
        appointment = await create_appointment_unique(
            prod_db,
            user_id=user.id,
            starts_at_utc=specific_time,
            duration_min=30,
            notes="Test appointment for data accuracy validation",
            is_test_data=True
        )
        prod_db.info["test_appointment_ids"].append(appointment.id)

        # Assert: Verify all fields
        assert appointment.user_id == user.id, "User ID should match"
        assert appointment.duration_min == 30, "Duration should be 30 minutes"
        assert appointment.status == "booked", "Initial status should be 'booked'"
        assert appointment.is_test_data is True, "Must be marked as test data"

        # Timezone validation
        assert appointment.starts_at.tzinfo is not None, "starts_at must be timezone-aware"
        assert appointment.created_at.tzinfo is not None, "created_at must be timezone-aware"

        # Time accuracy (should match within seconds)
        time_diff = abs((appointment.starts_at - specific_time).total_seconds())
        assert time_diff < 1, f"Time should be exact (diff: {time_diff}s)"

        # Created_at should be recent
        created_diff = abs((datetime.now(timezone.utc) - appointment.created_at).total_seconds())
        assert created_diff < 10, "created_at should be very recent"

        # Verify can query back from database
        refreshed = await prod_db.get(Appointment, appointment.id)
        assert refreshed is not None, "Should be able to retrieve appointment"
        assert refreshed.starts_at == appointment.starts_at, "Times should match after refresh"

    @skip_if_no_url
    @pytest.mark.skipif(
        not os.getenv("GOOGLE_CALENDAR_ENABLED", "").lower() == "true",
        reason="Google Calendar integration not enabled"
    )
    async def test_google_calendar_integration(
        self,
        prod_db: AsyncSession,
        test_call_context: Dict[str, Any]
    ):
        """
        Test that appointments sync correctly to Google Calendar.

        Flow:
        1. Create appointment
        2. Verify Google Calendar event_id is set
        3. Check event details are correct
        """
        # Arrange
        from_number = test_call_context["from_number"]
        test_name = test_call_context["test_name"]

        user = await create_user(
            prod_db,
            mobile=from_number,
            full_name=test_name,
            email=f"test_{test_call_context['timestamp']}@test.local"
        )

        # Act: Create appointment (should trigger calendar sync)
        appointment_time = datetime.now(timezone.utc) + timedelta(days=4, hours=14)

        from app.crud.appointment import create_appointment_unique
        appointment = await create_appointment_unique(
            prod_db,
            user_id=user.id,
            starts_at_utc=appointment_time,
            duration_min=30,
            notes="Test for Google Calendar sync",
            is_test_data=True
        )
        prod_db.info["test_appointment_ids"].append(appointment.id)

        # Allow time for async calendar sync
        import asyncio
        await asyncio.sleep(2)

        # Refresh to get updated data
        await prod_db.refresh(appointment)

        # Assert: Calendar event should be created
        assert appointment.google_event_id is not None, "Google Calendar event should be created"
        assert len(appointment.google_event_id) > 0, "Event ID should not be empty"

        # Event ID should be alphanumeric
        assert appointment.google_event_id.replace("_", "").isalnum(), "Event ID should be valid format"

    @skip_if_no_url
    async def test_concurrent_bookings_isolation(
        self,
        prod_db: AsyncSession,
        test_call_context: Dict[str, Any]
    ):
        """
        Test that concurrent calls don't interfere with each other.

        Flow:
        1. Simulate two concurrent calls from different numbers
        2. Verify both create separate appointments
        3. Ensure no data corruption
        """
        # Arrange: Two different callers
        from_number_1 = test_call_context["from_number"]
        from_number_2 = f"+1416555{str(test_call_context['timestamp'] + 1).zfill(4)[-4:]}"

        user1 = await create_user(prod_db, mobile=from_number_1, full_name="Test User 1")
        user2 = await create_user(prod_db, mobile=from_number_2, full_name="Test User 2")

        # Act: Create concurrent appointments
        appointment_time = datetime.now(timezone.utc) + timedelta(days=5, hours=10)

        from app.crud.appointment import create_appointment_unique
        import asyncio

        # Create both appointments concurrently
        results = await asyncio.gather(
            create_appointment_unique(
                prod_db, user_id=user1.id, starts_at_utc=appointment_time, is_test_data=True
            ),
            create_appointment_unique(
                prod_db, user_id=user2.id, starts_at_utc=appointment_time, is_test_data=True
            ),
            return_exceptions=True
        )

        # Assert: Both should succeed (different users, same time is OK)
        assert len(results) == 2
        assert not isinstance(results[0], Exception), "First appointment should succeed"
        assert not isinstance(results[1], Exception), "Second appointment should succeed"

        apt1, apt2 = results
        prod_db.info["test_appointment_ids"].extend([apt1.id, apt2.id])

        # Verify both appointments exist and are distinct
        assert apt1.id != apt2.id, "Should have different IDs"
        assert apt1.user_id != apt2.user_id, "Should belong to different users"
        assert apt1.is_test_data is True and apt2.is_test_data is True, "Both should be test data"


@pytest.mark.prod_db
class TestProductionDataCleanup:
    """Tests for production test data cleanup utilities"""

    async def test_cleanup_identifies_test_data(self, prod_db: AsyncSession):
        """Verify cleanup utilities can identify test data correctly"""
        from tests.production.cleanup import count_test_appointments, list_test_appointments

        # Count should work without errors
        count = await count_test_appointments(prod_db)
        assert isinstance(count, int), "Count should return integer"
        assert count >= 0, "Count should be non-negative"

        # List should work
        appointments = await list_test_appointments(prod_db, limit=10)
        assert isinstance(appointments, list), "Should return list"

        # All returned appointments should be test data
        for apt in appointments:
            assert apt.is_test_data is True, "All returned appointments should be test data"

    async def test_cleanup_respects_age_filter(self, prod_db: AsyncSession, test_call_context: Dict[str, Any]):
        """Verify cleanup age filtering works correctly"""
        from tests.production.cleanup import cleanup_test_appointments

        # Create a fresh test appointment
        from_number = test_call_context["from_number"]
        user = await create_user(prod_db, mobile=from_number, full_name="Age Test User")

        from app.crud.appointment import create_appointment_unique
        appointment = await create_appointment_unique(
            prod_db,
            user_id=user.id,
            starts_at_utc=datetime.now(timezone.utc) + timedelta(days=1),
            is_test_data=True
        )
        prod_db.info["test_appointment_ids"].append(appointment.id)

        # Try to clean up appointments older than 1 hour (dry run)
        results = await cleanup_test_appointments(
            prod_db,
            older_than_hours=1,
            dry_run=True
        )

        assert results["dry_run"] is True, "Should be dry run"
        # Fresh appointment should NOT be in cleanup list
        assert appointment.id not in results["deleted_ids"], "Fresh appointment should not be marked for cleanup"

    async def test_verify_cleanup_rules(self, prod_db: AsyncSession):
        """Test cleanup verification and reporting"""
        from tests.production.cleanup import verify_cleanup_rules, get_cleanup_summary

        # Verify should return comprehensive stats
        verification = await verify_cleanup_rules(prod_db)

        assert "total_test_appointments" in verification
        assert "active_test_appointments" in verification
        assert "age_distribution" in verification
        assert "stale_test_data" in verification
        assert "cleanup_recommended" in verification
        assert "timestamp" in verification

        # All counts should be non-negative
        assert verification["total_test_appointments"] >= 0
        assert verification["active_test_appointments"] >= 0

        # Summary should be a readable string
        summary = await get_cleanup_summary(prod_db)
        assert isinstance(summary, str)
        assert len(summary) > 0
        assert "Test Appointments" in summary

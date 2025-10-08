#!/usr/bin/env python3
"""
Unit tests for time extraction functions.
Tests various time formats, relative dates, and timezone handling.
"""

import pytest
import sys
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Add app to Python path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.canadian_extraction import extract_canadian_time


class TestTimeExtraction:
    """Test time extraction functions"""

    @pytest.mark.asyncio
    async def test_extract_time_basic_formats(self):
        """Test basic time format extraction"""
        # Specific times
        result = await extract_canadian_time("tomorrow at 2 PM")
        assert result is not None
        assert result.hour == 14  # 2 PM in 24-hour format

        result = await extract_canadian_time("next Tuesday at 10 AM")
        assert result is not None
        assert result.hour == 10

        result = await extract_canadian_time("Friday at 3:30 PM")
        assert result is not None
        assert result.hour == 15
        assert result.minute == 30

    @pytest.mark.asyncio
    async def test_extract_time_relative_dates(self):
        """Test relative date extraction"""
        now = datetime.now(ZoneInfo("America/Edmonton"))

        # Tomorrow
        result = await extract_canadian_time("tomorrow at 9 AM")
        assert result is not None
        expected_date = (now + timedelta(days=1)).date()
        assert result.astimezone(ZoneInfo("America/Edmonton")).date() == expected_date

        # Next week relative
        result = await extract_canadian_time("next Monday at 10 AM")
        assert result is not None
        assert result.hour == 10

        # Today
        result = await extract_canadian_time("today at 3 PM")
        assert result is not None
        assert result.astimezone(ZoneInfo("America/Edmonton")).date() == now.date()

    @pytest.mark.asyncio
    async def test_extract_time_specific_dates(self):
        """Test specific date extraction"""
        # Month and day
        result = await extract_canadian_time("December 15th at 2 PM")
        assert result is not None
        assert result.month == 12
        assert result.day == 15
        assert result.hour == 14

        # Different formats
        result = await extract_canadian_time("Oct 10 at 11 AM")
        assert result is not None
        assert result.month == 10
        assert result.day == 10
        assert result.hour == 11

    @pytest.mark.asyncio
    async def test_extract_time_12_hour_format(self):
        """Test 12-hour time format extraction"""
        # AM times
        result = await extract_canadian_time("tomorrow at 9 AM")
        assert result is not None
        assert result.hour == 9

        result = await extract_canadian_time("next Monday at 11:30 AM")
        assert result is not None
        assert result.hour == 11
        assert result.minute == 30

        # PM times
        result = await extract_canadian_time("Friday at 2 PM")
        assert result is not None
        assert result.hour == 14

        result = await extract_canadian_time("next week at 6:45 PM")
        assert result is not None
        assert result.hour == 18
        assert result.minute == 45

    @pytest.mark.asyncio
    async def test_extract_time_24_hour_format(self):
        """Test 24-hour time format extraction"""
        result = await extract_canadian_time("tomorrow at 14:30")
        assert result is not None
        assert result.hour == 14
        assert result.minute == 30

        result = await extract_canadian_time("next Friday at 09:00")
        assert result is not None
        assert result.hour == 9
        assert result.minute == 0

    @pytest.mark.asyncio
    async def test_extract_time_timezone_handling(self):
        """Test timezone conversion to UTC"""
        # All times should be returned in UTC
        result = await extract_canadian_time("tomorrow at 2 PM")
        assert result is not None
        assert result.tzinfo == ZoneInfo("UTC")

        # Local time should be converted properly
        local_time = ZoneInfo("America/Edmonton")
        result_local = result.astimezone(local_time)
        assert result_local.hour == 14  # 2 PM local time

    @pytest.mark.asyncio
    async def test_extract_time_business_hours(self):
        """Test extraction of business hour times"""
        business_times = [
            "9 AM",
            "10:30 AM",
            "2 PM",
            "4:30 PM",
            "5 PM"
        ]

        for time_str in business_times:
            result = await extract_canadian_time(f"tomorrow at {time_str}")
            assert result is not None
            local_hour = result.astimezone(ZoneInfo("America/Edmonton")).hour
            assert 9 <= local_hour <= 17  # Business hours

    @pytest.mark.asyncio
    async def test_extract_time_edge_cases(self):
        """Test edge cases and error scenarios"""
        # Empty input
        result = await extract_canadian_time("")
        assert result is None

        # Invalid time
        result = await extract_canadian_time("25:00")
        assert result is None

        # Unclear input
        result = await extract_canadian_time("sometime maybe")
        assert result is None

        # Past time (should be rejected or moved to future)
        now = datetime.now(ZoneInfo("America/Edmonton"))
        if now.hour < 8:  # If it's early morning
            result = await extract_canadian_time("yesterday at 2 PM")
            # Should either be None or moved to future
            if result is not None:
                assert result > datetime.now(ZoneInfo("UTC"))

    @pytest.mark.asyncio
    async def test_extract_time_natural_language(self):
        """Test natural language time expressions"""
        # Common expressions
        result = await extract_canadian_time("next Tuesday morning")
        assert result is not None

        result = await extract_canadian_time("Friday afternoon")
        assert result is not None
        local_hour = result.astimezone(ZoneInfo("America/Edmonton")).hour
        assert 12 <= local_hour <= 17  # Afternoon range

        result = await extract_canadian_time("Monday evening")
        assert result is not None
        local_hour = result.astimezone(ZoneInfo("America/Edmonton")).hour
        assert 17 <= local_hour <= 20  # Evening range

    @pytest.mark.asyncio
    async def test_extract_time_speech_variations(self):
        """Test speech-to-text variations"""
        # "Two" vs "2"
        result1 = await extract_canadian_time("tomorrow at two PM")
        result2 = await extract_canadian_time("tomorrow at 2 PM")
        if result1 and result2:
            assert result1.hour == result2.hour

        # "Thirty" vs "30"
        result1 = await extract_canadian_time("tomorrow at 2 thirty PM")
        result2 = await extract_canadian_time("tomorrow at 2:30 PM")
        if result1 and result2:
            assert result1.hour == result2.hour
            assert result1.minute == result2.minute

    @pytest.mark.asyncio
    async def test_extract_time_daylight_saving(self):
        """Test handling of daylight saving time transitions"""
        # This is a complex case - the function should handle DST correctly
        # We'll test that times are consistently converted
        result = await extract_canadian_time("next Monday at 10 AM")
        assert result is not None

        # Convert back to local time and verify
        local_time = result.astimezone(ZoneInfo("America/Edmonton"))
        assert local_time.hour == 10

    @pytest.mark.asyncio
    async def test_extract_time_performance(self):
        """Test that time extraction is fast enough for real-time use"""
        import time

        test_times = [
            "tomorrow at 2 PM",
            "next Tuesday at 10:30 AM",
            "Friday afternoon",
            "December 15th at 3 PM"
        ]

        start_time = time.time()
        for _ in range(50):  # Fewer iterations due to async nature
            for time_input in test_times:
                await extract_canadian_time(time_input)
        end_time = time.time()

        # Should complete 200 extractions in under 2 seconds
        assert (end_time - start_time) < 2.0


class TestTimeValidation:
    """Test time validation and business rules"""

    @pytest.mark.asyncio
    async def test_future_only_times(self):
        """Test that only future times are accepted"""
        now = datetime.now(ZoneInfo("America/Edmonton"))

        # Past times should be rejected or moved to future
        if now.hour > 10:  # If it's after 10 AM
            result = await extract_canadian_time("today at 9 AM")
            if result is not None:
                # Should be moved to tomorrow or rejected
                assert result > datetime.now(ZoneInfo("UTC"))

    @pytest.mark.asyncio
    async def test_business_hours_validation(self):
        """Test validation of business hours"""
        # Very early morning (outside business hours)
        result = await extract_canadian_time("tomorrow at 6 AM")
        if result is not None:
            local_hour = result.astimezone(ZoneInfo("America/Edmonton")).hour
            # Should either be rejected or moved to business hours
            # This depends on business rules implementation

        # Very late evening
        result = await extract_canadian_time("tomorrow at 11 PM")
        if result is not None:
            local_hour = result.astimezone(ZoneInfo("America/Edmonton")).hour
            # Should either be rejected or handled appropriately

    @pytest.mark.asyncio
    async def test_weekend_handling(self):
        """Test handling of weekend appointments"""
        result = await extract_canadian_time("next Saturday at 10 AM")
        # Behavior depends on business rules - might be accepted or rejected

        result = await extract_canadian_time("Sunday morning")
        # Behavior depends on business rules


class TestTimeExtractionIntegration:
    """Test integration with call flow context"""

    @pytest.mark.asyncio
    async def test_time_confirmation_flow(self):
        """Test times in the context of confirmation flow"""
        # Times that should be easily confirmable
        clear_times = [
            "tomorrow at 2 PM",
            "next Monday at 10 AM",
            "Friday at 3:30 PM"
        ]

        for time_str in clear_times:
            result = await extract_canadian_time(time_str)
            assert result is not None
            # Should be in the future
            assert result > datetime.now(ZoneInfo("UTC"))

    @pytest.mark.asyncio
    async def test_ambiguous_time_handling(self):
        """Test handling of ambiguous time expressions"""
        # "Next week" without specific day
        result = await extract_canadian_time("next week sometime")
        # Might return None or a default time

        # "Afternoon" without specific time
        result = await extract_canadian_time("tomorrow afternoon")
        if result is not None:
            local_hour = result.astimezone(ZoneInfo("America/Edmonton")).hour
            assert 12 <= local_hour <= 17

    @pytest.mark.asyncio
    async def test_time_with_duration_context(self):
        """Test time extraction when duration is mentioned"""
        # Time with duration information
        result = await extract_canadian_time("tomorrow at 2 PM for 30 minutes")
        assert result is not None
        assert result.hour == 14  # Should extract the start time

        result = await extract_canadian_time("next Monday at 10 for an hour")
        assert result is not None
        assert result.hour == 10

    @pytest.mark.asyncio
    async def test_realistic_speech_scenarios(self):
        """Test realistic speech-to-text scenarios"""
        # With hesitation
        result = await extract_canadian_time("um tomorrow at... 2 PM")
        if result is not None:
            assert result.hour == 14

        # With correction
        result = await extract_canadian_time("tomorrow at 3 no wait 2 PM")
        # Should ideally extract the corrected time (2 PM)

        # With extra context
        result = await extract_canadian_time("I'd like to book tomorrow at 2 PM please")
        if result is not None:
            assert result.hour == 14

    @pytest.mark.asyncio
    async def test_error_recovery_scenarios(self):
        """Test error recovery and fallback scenarios"""
        # Partial time information
        result = await extract_canadian_time("tomorrow at 2")
        # Might assume PM or ask for clarification

        # Missing date
        result = await extract_canadian_time("at 2 PM")
        # Might assume tomorrow or today

        # Missing time
        result = await extract_canadian_time("tomorrow")
        # Might return None or ask for time


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
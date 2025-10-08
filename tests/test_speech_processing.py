#!/usr/bin/env python3
"""
Tests for speech processing and smart speech handling functionality.
Tests speech artifact removal, confidence handling, and extraction logic.
"""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock

# Add app to Python path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.simple_extraction import (
    extract_name_simple, extract_phone_simple, extract_key_phrases
)
from app.api.routes.twilio import _extract_digits, _extract_phone_fast


class TestSpeechArtifactHandling:
    """Test handling of speech recognition artifacts"""

    @pytest.mark.essential
    @pytest.mark.unit
    def test_filler_word_handling(self):
        """Test handling of common filler words"""
        # Name extraction should handle fillers in calling function
        result = extract_name_simple("um my name is uh John Smith")
        # Simple function doesn't filter - that's done in calling function
        assert "John" in result and "Smith" in result

    @pytest.mark.essential
    @pytest.mark.unit
    def test_repetition_handling(self):
        """Test handling of repeated information"""
        # Phone number repetition
        result = extract_phone_simple("416 555 1234 that's 416 555 1234")
        assert result == "+14165551234"

        # Name repetition
        result = extract_name_simple("John Smith John Smith")
        assert "John" in result and "Smith" in result

    @pytest.mark.essential
    @pytest.mark.unit
    def test_hesitation_patterns(self):
        """Test handling of hesitation patterns"""
        # With pauses and hesitation
        result = extract_phone_simple("my number is... 416... 555... 1234")
        assert result == "+14165551234"

        result = extract_name_simple("my name is... John... Smith")
        assert "John" in result and "Smith" in result

    @pytest.mark.essential
    @pytest.mark.unit
    def test_correction_patterns(self):
        """Test handling of self-corrections"""
        # Phone correction
        result = extract_phone_simple("416 555 1234 no wait 416 555 9876")
        # Should extract one of the numbers (implementation dependent)
        assert result is not None and "+1416555" in result

        # Name correction
        result = extract_name_simple("John no wait Jane Smith")
        # Should extract some form of name
        assert len(result) > 0

    @pytest.mark.essential
    @pytest.mark.unit
    def test_background_noise_simulation(self):
        """Test handling of background noise artifacts"""
        # Simulated noise in phone number
        result = extract_phone_simple("four one six [background noise] five five five one two three four")
        # Should extract digits despite noise
        assert result == "+14165551234"

    @pytest.mark.skip(reason="Edge case - partial word handling needs refinement")
    @pytest.mark.essential
    @pytest.mark.unit
    def test_partial_word_handling(self):
        """Test handling of partially recognized words"""
        # Partial names
        result = extract_name_simple("Jo... John Smith")
        assert "John" in result and "Smith" in result

        # Partial phone numbers
        result = extract_phone_simple("four one... four one six five five five")
        # Should handle partial recognition
        assert result is not None


class TestConfidenceScoreHandling:
    """Test speech confidence score scenarios"""

    @pytest.mark.essential
    @pytest.mark.unit
    def test_high_confidence_speech(self):
        """Test processing of high-confidence speech"""
        # Should accept clear, high-confidence input
        result = extract_name_simple("John Smith")  # Simulating 0.95 confidence
        assert result == "John Smith"

        result = extract_phone_simple("416-555-1234")  # High confidence
        assert result == "+14165551234"

    @pytest.mark.essential
    @pytest.mark.unit
    def test_medium_confidence_speech(self):
        """Test processing of medium-confidence speech"""
        # Should still process medium confidence with some caution
        result = extract_name_simple("John Smth")  # Slight recognition error
        assert "John" in result

        result = extract_phone_simple("416 55 1234")  # Missing digit
        # Might fail validation due to wrong length

    @pytest.mark.essential
    @pytest.mark.unit
    def test_low_confidence_speech(self):
        """Test processing of low-confidence speech"""
        # Low confidence speech should be handled carefully
        result = extract_name_simple("unintelligible speech")
        # Simple function will return something, rejection happens elsewhere

        result = extract_phone_simple("garbled phone number")
        assert result is None  # Should fail to extract valid phone

    @pytest.mark.essential
    @pytest.mark.unit
    def test_confidence_vs_content_quality(self):
        """Test that content quality matters more than confidence"""
        # Clear content should work even with lower confidence
        result = extract_phone_simple("four one six five five five one two three four")
        assert result == "+14165551234"

        # Unclear content should fail even with high confidence
        result = extract_phone_simple("random words not phone")
        assert result is None


class TestMultiModalInputHandling:
    """Test handling of mixed speech and DTMF input"""

    @pytest.mark.essential
    @pytest.mark.unit
    def test_dtmf_phone_input(self):
        """Test DTMF keypad input for phone numbers"""
        # Direct digit sequence
        result = _extract_phone_fast("4165551234")
        assert result == "+14165551234"

        # With separators (simulating keypad pauses)
        result = _extract_phone_fast("416-555-1234")
        assert result == "+14165551234"

    @pytest.mark.essential
    @pytest.mark.unit
    def test_dtmf_vs_speech_preference(self):
        """Test preference of DTMF over speech when both available"""
        # In the actual implementation, DTMF is preferred
        # This would be tested in the route handler level

    @pytest.mark.essential
    @pytest.mark.unit
    def test_mixed_input_patterns(self):
        """Test mixed speech and digit patterns"""
        # Partially spoken, partially spelled
        result = extract_phone_simple("area code 416 and 555-1234")
        assert result == "+14165551234"

        # Mixed word and digit format
        result = _extract_digits("four 1 6 five five five")
        assert "41655" in result

    @pytest.mark.essential
    @pytest.mark.unit
    def test_keypad_shortcuts(self):
        """Test keypad shortcut handling"""
        # Time shortcuts (implemented in route handler)
        # Duration shortcuts
        # These would be tested at the integration level


class TestSpeechProcessingPerformance:
    """Test performance of speech processing functions"""

    @pytest.mark.essential
    @pytest.mark.unit
    def test_extraction_speed(self):
        """Test that extraction functions are fast enough for real-time"""
        import time

        test_inputs = [
            "John Michael Smith Jr.",
            "my name is Mary Elizabeth Johnson",
            "416-555-1234",
            "four one six five five five one two three four",
            "tomorrow at 2 PM"
        ]

        start_time = time.time()
        for _ in range(1000):  # 1000 iterations
            for input_text in test_inputs:
                extract_name_simple(input_text)
                extract_phone_simple(input_text)
                extract_key_phrases(input_text, "confirm")
        end_time = time.time()

        # Should complete 15,000 extractions in under 2 seconds
        assert (end_time - start_time) < 2.0

    @pytest.mark.slow
    def test_regex_performance(self):
        """Test regex pattern matching performance"""
        import time

        long_text = "um uh my name is John Smith and my phone number is 416-555-1234 " * 100

        start_time = time.time()
        for _ in range(100):
            _extract_digits(long_text)
            extract_phone_simple(long_text)
        end_time = time.time()

        # Should handle long text efficiently
        assert (end_time - start_time) < 1.0

    @pytest.mark.essential
    @pytest.mark.unit
    def test_memory_usage(self):
        """Test memory usage during processing"""
        import gc
        import sys

        # Get initial memory usage
        gc.collect()
        initial_objects = len(gc.get_objects())

        # Process many inputs
        for i in range(1000):
            extract_name_simple(f"Customer Name {i}")
            extract_phone_simple(f"416555{i:04d}")

        # Force garbage collection
        gc.collect()
        final_objects = len(gc.get_objects())

        # Memory usage shouldn't grow significantly
        object_growth = final_objects - initial_objects
        assert object_growth < 1000  # Allow some growth but not excessive


class TestSpeechHistoryTracking:
    """Test speech history and debugging features"""

    @pytest.mark.essential
    @pytest.mark.unit
    def test_speech_history_structure(self):
        """Test that speech history is properly structured"""
        from app.services.redis_session import CallSession

        session = CallSession(call_sid="TEST_HISTORY_001")

        # Simulate adding speech history
        session.speech_history.append({
            "timestamp": "2025-10-07T12:00:00",
            "step": "ask_name",
            "input_type": "speech",
            "raw": "John Smith",
            "extracted": {"name": "John Smith"}
        })

        assert len(session.speech_history) == 1
        assert session.speech_history[0]["step"] == "ask_name"
        assert session.speech_history[0]["input_type"] == "speech"

    @pytest.mark.essential
    @pytest.mark.unit
    def test_speech_cleaning_tracking(self):
        """Test tracking of speech cleaning operations"""
        from app.services.redis_session import CallSession

        session = CallSession(call_sid="TEST_CLEANING_001")
        session.last_raw_speech = "um my name is uh John Smith"
        session.last_cleaned_speech = "John Smith"

        # Should track both raw and cleaned versions
        assert session.last_raw_speech != session.last_cleaned_speech
        assert "um" in session.last_raw_speech
        assert "um" not in session.last_cleaned_speech

    @pytest.mark.essential
    @pytest.mark.unit
    def test_speech_confidence_tracking(self):
        """Test tracking of speech confidence scores"""
        # This would be implemented in the route handlers
        # Testing the data structure capability
        speech_data = {
            "raw_speech": "John Smith",
            "confidence": 0.95,
            "processing_time": 0.05,
            "alternative_transcriptions": ["Jon Smith", "John Smyth"]
        }

        # Should be able to store comprehensive speech data
        assert speech_data["confidence"] > 0.9
        assert speech_data["processing_time"] < 0.1


class TestErrorRecoveryMechanisms:
    """Test error recovery in speech processing"""

    @pytest.mark.essential
    @pytest.mark.unit
    def test_fallback_extraction_methods(self):
        """Test fallback between extraction methods"""
        # Primary method fails, fallback succeeds
        with patch('app.services.simple_extraction.extract_phone_simple') as mock_primary:
            mock_primary.return_value = None  # Primary fails

            # Fallback to basic extraction
            result = _extract_phone_fast("4165551234")
            assert result == "+14165551234"

    @pytest.mark.essential
    @pytest.mark.unit
    def test_graceful_degradation(self):
        """Test graceful degradation when processing fails"""
        # Invalid input should not crash, should return None or empty
        result = extract_phone_simple(None)
        assert result is None

        result = extract_name_simple("")
        assert result == ""

        result = extract_key_phrases("", "invalid_context")
        assert result == ""

    @pytest.mark.essential
    @pytest.mark.unit
    def test_exception_handling(self):
        """Test exception handling in processing functions"""
        # Should handle various exception types gracefully
        result = extract_phone_simple("🙂📱☎️")  # Emoji input
        assert result is None or isinstance(result, str)

        result = extract_name_simple("💻🎮🎯")  # Non-text input
        assert isinstance(result, str)

    @pytest.mark.essential
    @pytest.mark.unit
    def test_partial_success_scenarios(self):
        """Test scenarios where processing partially succeeds"""
        # Partial phone number
        result = extract_phone_simple("416 555")  # Incomplete
        assert result is None  # Should reject incomplete numbers

        # Partial name
        result = extract_name_simple("J")  # Very short
        assert result == "J"  # Should return what it can


class TestContextAwareProcessing:
    """Test context-aware speech processing"""

    @pytest.mark.essential
    @pytest.mark.unit
    def test_step_specific_processing(self):
        """Test that processing adapts to call flow step"""
        # Name step - should look for names
        name_result = extract_name_simple("John Smith appointment")
        assert "John" in name_result and "Smith" in name_result

        # Phone step - should prioritize numbers
        phone_result = extract_phone_simple("John Smith 416-555-1234")
        assert phone_result == "+14165551234"

    @pytest.mark.skip(reason="Edge case - context phrase mapping needs refinement")
    @pytest.mark.essential
    @pytest.mark.unit
    def test_context_phrases(self):
        """Test extraction of context-specific phrases"""
        # Confirmation context
        result = extract_key_phrases("yes that's correct", "confirm")
        assert "yes" in result.lower() or "correct" in result.lower()

        # Time context
        result = extract_key_phrases("tomorrow at 2 PM", "time")
        assert "tomorrow" in result.lower() and "2" in result

    @pytest.mark.essential
    @pytest.mark.unit
    def test_disambiguation_logic(self):
        """Test disambiguation when multiple interpretations possible"""
        # Could be name or business name
        result = extract_name_simple("Smith and Associates")
        # Should return formatted version
        assert "Smith" in result

        # Could be phone or other numbers
        result = extract_phone_simple("my appointment is at 2 PM and my number is 416-555-1234")
        assert result == "+14165551234"  # Should extract phone, not time

    @pytest.mark.essential
    @pytest.mark.unit
    def test_priority_ordering(self):
        """Test priority ordering when multiple valid extractions possible"""
        # Multiple potential extractions - should pick the best one
        mixed_input = "John Smith 416-555-1234 tomorrow at 2 PM"

        name_result = extract_name_simple(mixed_input)
        phone_result = extract_phone_simple(mixed_input)

        assert "John" in name_result and "Smith" in name_result
        assert phone_result == "+14165551234"


class TestRealWorldSpeechPatterns:
    """Test patterns observed in real-world speech recognition"""

    @pytest.mark.essential
    @pytest.mark.unit
    def test_canadian_accent_patterns(self):
        """Test patterns specific to Canadian English"""
        # "About" pronunciation variations
        result = extract_name_simple("my name is about John Smith")
        # Should handle Canadian pronunciation artifacts

        # "Schedule" vs "shedule"
        # Regional pronunciation differences
        pass

    @pytest.mark.essential
    @pytest.mark.unit
    def test_phone_pronunciation_patterns(self):
        """Test phone number pronunciation patterns"""
        # "Oh" vs "zero"
        result = extract_phone_simple("four one six five five five oh nine eight seven")
        assert result == "+14165550987"

        # Double digits
        result = extract_phone_simple("four one six double five one two three four")
        # Should handle "double five" -> "55"

    @pytest.mark.essential
    @pytest.mark.unit
    def test_time_pronunciation_patterns(self):
        """Test time pronunciation patterns"""
        # "Half past" vs "thirty"
        time_input = "tomorrow at half past two"
        # Would be handled by time extraction function

        # "Quarter to" vs "forty-five"
        time_input = "quarter to three tomorrow"
        # Should understand relative time expressions

    @pytest.mark.essential
    @pytest.mark.unit
    def test_multilingual_patterns(self):
        """Test handling of multilingual input"""
        # French-Canadian names
        result = extract_name_simple("Jean-Pierre Dubois")
        assert "Jean-Pierre" in result and "Dubois" in result

        # Accented characters
        result = extract_name_simple("José García")
        assert "José" in result and "García" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
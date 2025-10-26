# tests/test_llm_service.py
"""
Test suite for LLM fallback service
Tests OpenAI integration, circuit breaker, and extraction functions
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from app.services.llm_service import (
    get_openai_client,
    is_llm_fallback_enabled,
    llm_extract_phone,
    llm_extract_time,
    llm_extract_name,
    get_llm_status,
    circuit_breaker
)


class TestOpenAIClient:
    """Test OpenAI client initialization"""

    @patch('app.services.llm_service.settings')
    @patch('app.services.llm_service.OpenAI')
    def test_get_openai_client_configured(self, mock_openai, mock_settings):
        """Test client creation when API key is configured"""
        mock_settings.OPENAI_API_KEY = "sk-test-key-123"
        mock_settings.OPENAI_MODEL = "gpt-4o-mini"

        client = get_openai_client()

        assert client is not None
        mock_openai.assert_called_once_with(api_key="sk-test-key-123")

    @patch('app.services.llm_service.settings')
    def test_get_openai_client_not_configured(self, mock_settings):
        """Test client returns None when API key is not configured"""
        mock_settings.OPENAI_API_KEY = None

        client = get_openai_client()

        assert client is None

    @patch('app.services.llm_service.settings')
    @patch('app.services.llm_service.OpenAI')
    def test_get_openai_client_empty_key(self, mock_openai, mock_settings):
        """Test client returns None when API key is empty"""
        mock_settings.OPENAI_API_KEY = ""

        client = get_openai_client()

        assert client is None


class TestLLMFallbackEnabled:
    """Test LLM fallback enable/disable checks"""

    @patch('app.services.llm_service.settings')
    def test_is_enabled_true(self, mock_settings):
        """Test when LLM fallback is enabled"""
        mock_settings.ENABLE_LLM_FALLBACK = True
        mock_settings.OPENAI_API_KEY = "sk-test-key"

        assert is_llm_fallback_enabled() is True

    @patch('app.services.llm_service.settings')
    def test_is_enabled_false_setting(self, mock_settings):
        """Test when LLM fallback is disabled by setting"""
        mock_settings.ENABLE_LLM_FALLBACK = False
        mock_settings.OPENAI_API_KEY = "sk-test-key"

        assert is_llm_fallback_enabled() is False

    @patch('app.services.llm_service.settings')
    def test_is_enabled_false_no_key(self, mock_settings):
        """Test when LLM fallback is disabled due to missing API key"""
        mock_settings.ENABLE_LLM_FALLBACK = True
        mock_settings.OPENAI_API_KEY = None

        assert is_llm_fallback_enabled() is False


class TestLLMExtractPhone:
    """Test phone number extraction via LLM"""

    @pytest.mark.asyncio
    @patch('app.services.llm_service.settings')
    @patch('app.services.llm_service.get_openai_client')
    async def test_extract_phone_success(self, mock_get_client, mock_settings):
        """Test successful phone extraction"""
        mock_settings.ENABLE_LLM_FALLBACK = True
        mock_settings.LLM_FALLBACK_TIMEOUT = 10
        mock_settings.OPENAI_MODEL = "gpt-4o-mini"

        # Mock OpenAI client response
        mock_client = Mock()
        mock_completion = Mock()
        mock_completion.choices = [Mock(message=Mock(content="4165551234"))]
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)
        mock_get_client.return_value = mock_client

        result = await llm_extract_phone("my number is four one six five five five one two three four")

        assert result == "4165551234"
        mock_client.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.services.llm_service.settings')
    @patch('app.services.llm_service.get_openai_client')
    async def test_extract_phone_disabled(self, mock_get_client, mock_settings):
        """Test phone extraction when LLM is disabled"""
        mock_settings.ENABLE_LLM_FALLBACK = False

        result = await llm_extract_phone("my number is four one six")

        assert result is None
        mock_get_client.assert_not_called()

    @pytest.mark.asyncio
    @patch('app.services.llm_service.settings')
    @patch('app.services.llm_service.get_openai_client')
    async def test_extract_phone_no_client(self, mock_get_client, mock_settings):
        """Test phone extraction when OpenAI client is unavailable"""
        mock_settings.ENABLE_LLM_FALLBACK = True
        mock_get_client.return_value = None

        result = await llm_extract_phone("my number is 416 555 1234")

        assert result is None

    @pytest.mark.asyncio
    @patch('app.services.llm_service.settings')
    @patch('app.services.llm_service.get_openai_client')
    async def test_extract_phone_api_error(self, mock_get_client, mock_settings):
        """Test phone extraction handling API errors"""
        mock_settings.ENABLE_LLM_FALLBACK = True
        mock_settings.LLM_FALLBACK_TIMEOUT = 10
        mock_settings.OPENAI_MODEL = "gpt-4o-mini"

        # Mock OpenAI client that raises exception
        mock_client = Mock()
        mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API Error"))
        mock_get_client.return_value = mock_client

        result = await llm_extract_phone("my number is four one six")

        assert result is None

    @pytest.mark.asyncio
    @patch('app.services.llm_service.settings')
    @patch('app.services.llm_service.get_openai_client')
    async def test_extract_phone_empty_response(self, mock_get_client, mock_settings):
        """Test phone extraction with empty LLM response"""
        mock_settings.ENABLE_LLM_FALLBACK = True
        mock_settings.LLM_FALLBACK_TIMEOUT = 10
        mock_settings.OPENAI_MODEL = "gpt-4o-mini"

        # Mock OpenAI client response with empty/invalid content
        mock_client = Mock()
        mock_completion = Mock()
        mock_completion.choices = [Mock(message=Mock(content="NONE"))]
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)
        mock_get_client.return_value = mock_client

        result = await llm_extract_phone("I don't have a phone")

        assert result is None


class TestLLMExtractTime:
    """Test time/date extraction via LLM"""

    @pytest.mark.asyncio
    @patch('app.services.llm_service.settings')
    @patch('app.services.llm_service.get_openai_client')
    async def test_extract_time_success(self, mock_get_client, mock_settings):
        """Test successful time extraction"""
        mock_settings.ENABLE_LLM_FALLBACK = True
        mock_settings.LLM_FALLBACK_TIMEOUT = 10
        mock_settings.OPENAI_MODEL = "gpt-4o-mini"

        # Mock OpenAI client response
        mock_client = Mock()
        mock_completion = Mock()
        mock_completion.choices = [Mock(message=Mock(content="tomorrow at 2 PM"))]
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)
        mock_get_client.return_value = mock_client

        result = await llm_extract_time("can we do next Tuesday around mid-morning")

        assert result == "tomorrow at 2 PM"
        mock_client.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.services.llm_service.settings')
    @patch('app.services.llm_service.get_openai_client')
    async def test_extract_time_disabled(self, mock_get_client, mock_settings):
        """Test time extraction when LLM is disabled"""
        mock_settings.ENABLE_LLM_FALLBACK = False

        result = await llm_extract_time("tomorrow at 2 PM")

        assert result is None
        mock_get_client.assert_not_called()


class TestLLMExtractName:
    """Test name extraction via LLM"""

    @pytest.mark.asyncio
    @patch('app.services.llm_service.settings')
    @patch('app.services.llm_service.get_openai_client')
    async def test_extract_name_success(self, mock_get_client, mock_settings):
        """Test successful name extraction"""
        mock_settings.ENABLE_LLM_FALLBACK = True
        mock_settings.LLM_FALLBACK_TIMEOUT = 10
        mock_settings.OPENAI_MODEL = "gpt-4o-mini"

        # Mock OpenAI client response
        mock_client = Mock()
        mock_completion = Mock()
        mock_completion.choices = [Mock(message=Mock(content="Xiao-Ming O'Sullivan-Zhang"))]
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)
        mock_get_client.return_value = mock_client

        result = await llm_extract_name("my name is Xiao-Ming O'Sullivan-Zhang")

        assert result == "Xiao-Ming O'Sullivan-Zhang"
        mock_client.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.services.llm_service.settings')
    @patch('app.services.llm_service.get_openai_client')
    async def test_extract_name_disabled(self, mock_get_client, mock_settings):
        """Test name extraction when LLM is disabled"""
        mock_settings.ENABLE_LLM_FALLBACK = False

        result = await llm_extract_name("my name is John")

        assert result is None
        mock_get_client.assert_not_called()


class TestCircuitBreaker:
    """Test circuit breaker functionality"""

    def test_circuit_breaker_initial_state(self):
        """Test circuit breaker starts closed (allowing requests)"""
        assert circuit_breaker.state == "closed"
        assert circuit_breaker.failure_count == 0

    def test_circuit_breaker_failure_tracking(self):
        """Test circuit breaker tracks failures"""
        initial_count = circuit_breaker.failure_count

        # Record a failure
        circuit_breaker.record_failure()

        assert circuit_breaker.failure_count == initial_count + 1

    def test_circuit_breaker_success_reset(self):
        """Test circuit breaker resets on success"""
        # Record some failures
        circuit_breaker.failure_count = 2

        # Record success
        circuit_breaker.record_success()

        assert circuit_breaker.failure_count == 0

    @pytest.mark.asyncio
    @patch('app.services.llm_service.settings')
    @patch('app.services.llm_service.get_openai_client')
    async def test_circuit_breaker_multiple_failures(self, mock_get_client, mock_settings):
        """Test circuit breaker opens after multiple failures"""
        mock_settings.ENABLE_LLM_FALLBACK = True
        mock_settings.LLM_FALLBACK_TIMEOUT = 1
        mock_settings.OPENAI_MODEL = "gpt-4o-mini"

        # Reset circuit breaker
        circuit_breaker.failure_count = 0
        circuit_breaker.state = "closed"

        # Mock OpenAI client that always fails
        mock_client = Mock()
        mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API Error"))
        mock_get_client.return_value = mock_client

        # Make multiple calls that will fail
        for i in range(5):
            result = await llm_extract_phone("test")
            assert result is None

        # Circuit breaker should have recorded failures
        assert circuit_breaker.failure_count >= 3


class TestLLMStatus:
    """Test LLM status reporting"""

    @patch('app.services.llm_service.settings')
    def test_get_status_active(self, mock_settings):
        """Test status when LLM is fully active"""
        mock_settings.ENABLE_LLM_FALLBACK = True
        mock_settings.OPENAI_API_KEY = "sk-test-key"

        status = get_llm_status()

        assert status["enabled"] is True
        assert status["configured"] is True
        assert status["status"] == "active"

    @patch('app.services.llm_service.settings')
    def test_get_status_ready_to_enable(self, mock_settings):
        """Test status when LLM is configured but disabled"""
        mock_settings.ENABLE_LLM_FALLBACK = False
        mock_settings.OPENAI_API_KEY = "sk-test-key"

        status = get_llm_status()

        assert status["enabled"] is False
        assert status["configured"] is True
        assert status["status"] == "ready_to_enable"

    @patch('app.services.llm_service.settings')
    def test_get_status_awaiting_api_key(self, mock_settings):
        """Test status when API key is not configured"""
        mock_settings.ENABLE_LLM_FALLBACK = True
        mock_settings.OPENAI_API_KEY = None

        status = get_llm_status()

        assert status["enabled"] is True
        assert status["configured"] is False
        assert status["status"] == "awaiting_api_key"

    @patch('app.services.llm_service.settings')
    def test_get_status_disabled(self, mock_settings):
        """Test status when LLM is fully disabled"""
        mock_settings.ENABLE_LLM_FALLBACK = False
        mock_settings.OPENAI_API_KEY = None

        status = get_llm_status()

        assert status["enabled"] is False
        assert status["configured"] is False
        assert status["status"] == "disabled"


class TestEdgeCases:
    """Test edge cases and error conditions"""

    @pytest.mark.asyncio
    @patch('app.services.llm_service.settings')
    @patch('app.services.llm_service.get_openai_client')
    async def test_extract_with_special_characters(self, mock_get_client, mock_settings):
        """Test extraction with special characters in input"""
        mock_settings.ENABLE_LLM_FALLBACK = True
        mock_settings.LLM_FALLBACK_TIMEOUT = 10
        mock_settings.OPENAI_MODEL = "gpt-4o-mini"

        # Mock OpenAI client response
        mock_client = Mock()
        mock_completion = Mock()
        mock_completion.choices = [Mock(message=Mock(content="Jean-François O'Brien"))]
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)
        mock_get_client.return_value = mock_client

        result = await llm_extract_name("my name is Jean-François O'Brien")

        assert "Jean-François" in result
        assert "O'Brien" in result

    @pytest.mark.asyncio
    @patch('app.services.llm_service.settings')
    @patch('app.services.llm_service.get_openai_client')
    async def test_extract_with_very_long_input(self, mock_get_client, mock_settings):
        """Test extraction with very long input text"""
        mock_settings.ENABLE_LLM_FALLBACK = True
        mock_settings.LLM_FALLBACK_TIMEOUT = 10
        mock_settings.OPENAI_MODEL = "gpt-4o-mini"

        # Mock OpenAI client response
        mock_client = Mock()
        mock_completion = Mock()
        mock_completion.choices = [Mock(message=Mock(content="4165551234"))]
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)
        mock_get_client.return_value = mock_client

        # Very long rambling input
        long_input = "um so like " * 100 + "my number is four one six five five five one two three four"

        result = await llm_extract_phone(long_input)

        assert result == "4165551234"

    @pytest.mark.asyncio
    @patch('app.services.llm_service.settings')
    @patch('app.services.llm_service.get_openai_client')
    async def test_extract_with_empty_string(self, mock_get_client, mock_settings):
        """Test extraction with empty string input"""
        mock_settings.ENABLE_LLM_FALLBACK = True

        result = await llm_extract_phone("")

        # Should handle gracefully and return None
        assert result is None


class TestIntegration:
    """Integration tests for LLM service"""

    @pytest.mark.asyncio
    @patch('app.services.llm_service.settings')
    @patch('app.services.llm_service.get_openai_client')
    async def test_full_extraction_flow(self, mock_get_client, mock_settings):
        """Test complete extraction flow with all functions"""
        mock_settings.ENABLE_LLM_FALLBACK = True
        mock_settings.LLM_FALLBACK_TIMEOUT = 10
        mock_settings.OPENAI_MODEL = "gpt-4o-mini"

        # Mock OpenAI client
        mock_client = Mock()
        mock_client.chat.completions.create = AsyncMock()
        mock_get_client.return_value = mock_client

        # Mock responses for different extraction types
        responses = [
            Mock(choices=[Mock(message=Mock(content="John Smith"))]),  # name
            Mock(choices=[Mock(message=Mock(content="4165551234"))]),  # phone
            Mock(choices=[Mock(message=Mock(content="tomorrow at 2 PM"))]),  # time
        ]
        mock_client.chat.completions.create.side_effect = responses

        # Extract all fields
        name = await llm_extract_name("my name is John Smith")
        phone = await llm_extract_phone("my number is four one six five five five one two three four")
        time = await llm_extract_time("tomorrow at 2 PM works for me")

        assert name == "John Smith"
        assert phone == "4165551234"
        assert time == "tomorrow at 2 PM"
        assert mock_client.chat.completions.create.call_count == 3

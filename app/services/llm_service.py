# app/services/llm_service.py
"""
LLM fallback service for extraction when library methods fail.
Uses GPT-4o-mini for cost-effective fallback extraction.

This service is DISABLED by default. Enable via ENABLE_LLM_FALLBACK=true in .env
"""
import logging
from typing import Optional
from datetime import datetime
from openai import AsyncOpenAI
from app.core.config import settings
from app.services.circuit_breaker import circuit_manager

logger = logging.getLogger(__name__)

# Initialize OpenAI client (only if API key is configured)
_openai_client: Optional[AsyncOpenAI] = None

def get_openai_client() -> Optional[AsyncOpenAI]:
    """Get or create OpenAI client"""
    global _openai_client

    if not settings.OPENAI_API_KEY:
        logger.debug("[llm_service] OPENAI_API_KEY not configured, LLM fallback disabled")
        return None

    if _openai_client is None:
        _openai_client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
            timeout=settings.LLM_FALLBACK_TIMEOUT
        )
        logger.info("[llm_service] OpenAI client initialized (model: %s)", settings.OPENAI_MODEL)

    return _openai_client


async def llm_extract_phone(speech: str) -> Optional[str]:
    """
    Extract phone number using LLM fallback.

    Args:
        speech: Speech text containing phone number

    Returns:
        Phone number string for re-parsing, or None if not found

    Note:
        This returns a cleaned phone number string that will be re-parsed
        by extract_canadian_phone() using phonenumbers library.
    """
    client = get_openai_client()
    if not client or not settings.ENABLE_LLM_FALLBACK:
        return None

    logger.info("[llm_phone] attempting LLM extraction for: '%s'", speech[:50])

    try:
        # Use circuit breaker for OpenAI API
        breaker = circuit_manager.get_breaker("openai_api")

        async def _call_openai():
            response = await client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "Extract ONLY the phone number digits from the text. Return just the digits (10-11 digits for North American numbers). If no phone number found, return 'NONE'. Do not include formatting."
                    },
                    {
                        "role": "user",
                        "content": f"Extract phone number: {speech}"
                    }
                ],
                max_tokens=50,
                temperature=0
            )
            return response.choices[0].message.content.strip()

        result = await breaker.call(_call_openai)

        if result and result != "NONE" and len(result) >= 7:
            logger.info("[llm_phone] LLM extracted: '%s' -> '%s'", speech[:50], result)
            # Return for re-parsing by canadian_extraction
            return result

        logger.info("[llm_phone] LLM found no phone number in: '%s'", speech[:50])
        return None

    except Exception as e:
        logger.error("[llm_phone] LLM extraction failed: %s", e)
        return None


async def llm_extract_time(speech: str) -> Optional[str]:
    """
    Extract time/date using LLM fallback.

    Args:
        speech: Speech text containing time/date

    Returns:
        Natural language time expression for re-parsing, or None if not found

    Note:
        This returns a normalized time string that will be re-parsed
        by extract_canadian_time() using parsedatetime library.
    """
    client = get_openai_client()
    if not client or not settings.ENABLE_LLM_FALLBACK:
        return None

    logger.info("[llm_time] attempting LLM extraction for: '%s'", speech[:50])

    try:
        breaker = circuit_manager.get_breaker("openai_api")

        async def _call_openai():
            response = await client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "Extract ONLY the date/time from the text. Return in natural format like 'Monday at 2 PM' or 'tomorrow at 10:30 AM'. Use 12-hour format with AM/PM. If no time found, return 'NONE'."
                    },
                    {
                        "role": "user",
                        "content": f"Extract time: {speech}"
                    }
                ],
                max_tokens=50,
                temperature=0
            )
            return response.choices[0].message.content.strip()

        result = await breaker.call(_call_openai)

        if result and result != "NONE":
            logger.info("[llm_time] LLM extracted: '%s' -> '%s'", speech[:50], result)
            # Return for re-parsing by canadian_extraction
            return result

        logger.info("[llm_time] LLM found no time in: '%s'", speech[:50])
        return None

    except Exception as e:
        logger.error("[llm_time] LLM extraction failed: %s", e)
        return None


async def llm_extract_name(speech: str) -> Optional[str]:
    """
    Extract person name using LLM fallback.

    Args:
        speech: Speech text containing person's name

    Returns:
        Formatted name string for re-parsing, or None if not found

    Note:
        This returns a cleaned name string that will be re-validated
        by extract_canadian_name() using nameparser library.
    """
    client = get_openai_client()
    if not client or not settings.ENABLE_LLM_FALLBACK:
        return None

    logger.info("[llm_name] attempting LLM extraction for: '%s'", speech[:50])

    try:
        breaker = circuit_manager.get_breaker("openai_api")

        async def _call_openai():
            response = await client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "Extract ONLY the person's name from the text. Return in format 'FirstName LastName' or just 'FirstName' if only one name given. Handle multi-cultural names (European, Asian, hyphenated, etc). Remove greetings and extra words. If no name found, return 'NONE'."
                    },
                    {
                        "role": "user",
                        "content": f"Extract name: {speech}"
                    }
                ],
                max_tokens=30,
                temperature=0
            )
            return response.choices[0].message.content.strip()

        result = await breaker.call(_call_openai)

        if result and result != "NONE" and len(result) > 2:
            logger.info("[llm_name] LLM extracted: '%s' -> '%s'", speech[:50], result)
            # Return for re-validation by canadian_extraction
            return result

        logger.info("[llm_name] LLM found no name in: '%s'", speech[:50])
        return None

    except Exception as e:
        logger.error("[llm_name] LLM extraction failed: %s", e)
        return None


def is_llm_fallback_enabled() -> bool:
    """
    Check if LLM fallback is enabled and configured.

    Returns:
        True if LLM fallback is ready to use, False otherwise
    """
    enabled = (
        settings.ENABLE_LLM_FALLBACK and
        settings.OPENAI_API_KEY is not None and
        len(settings.OPENAI_API_KEY) > 0
    )

    if not enabled:
        logger.debug("[llm_service] LLM fallback disabled or not configured")

    return enabled


def get_llm_status() -> dict:
    """
    Get LLM service status for monitoring/dashboard.

    Returns:
        Dictionary with LLM service status information
    """
    has_api_key = bool(settings.OPENAI_API_KEY and len(settings.OPENAI_API_KEY) > 0)

    return {
        "enabled": settings.ENABLE_LLM_FALLBACK,
        "configured": has_api_key,
        "model": settings.OPENAI_MODEL if has_api_key else None,
        "timeout": settings.LLM_FALLBACK_TIMEOUT,
        "status": (
            "active" if (settings.ENABLE_LLM_FALLBACK and has_api_key) else
            "ready_to_enable" if has_api_key else
            "awaiting_api_key"
        ),
        "circuit_breaker": circuit_manager.get_breaker("openai_api").get_stats() if has_api_key else None
    }

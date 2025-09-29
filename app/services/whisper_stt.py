# app/services/whisper_stt.py
"""
Whisper-based Speech-to-Text service for Twilio audio processing.
Replaces the unified LLM approach with specialized transcription.
"""

import logging
import os
from typing import Optional
import httpx
from openai import AsyncOpenAI

logger = logging.getLogger("uvicorn.error")

# Initialize OpenAI client for Whisper
_openai_client: Optional[AsyncOpenAI] = None

def get_openai_client() -> AsyncOpenAI:
    """Get or create OpenAI client for Whisper STT."""
    global _openai_client
    if _openai_client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")

        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        _openai_client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=30.0
        )
        logger.info("OpenAI Whisper client initialized: %s", base_url)

    return _openai_client


async def transcribe_audio_url(audio_url: str, language: str = "en") -> str:
    """
    Transcribe audio from Twilio webhook URL using Whisper.

    Args:
        audio_url: Twilio recording URL (e.g., from RecordingUrl parameter)
        language: Language code (default: "en" for English)

    Returns:
        Transcribed text string
    """
    if not audio_url:
        raise ValueError("Audio URL is required")

    client = get_openai_client()

    try:
        # Download audio from Twilio
        async with httpx.AsyncClient(timeout=30.0) as http_client:
            response = await http_client.get(audio_url)
            response.raise_for_status()
            audio_data = response.content

        logger.info("[whisper] downloaded %d bytes from %s", len(audio_data), audio_url[:50] + "...")

        # Create file-like object for OpenAI
        audio_file = ("audio.wav", audio_data, "audio/wav")

        # Transcribe using Whisper
        transcript = await client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language=language,
            response_format="text",
            temperature=0.2  # Lower temperature for more consistent results
        )

        transcript_text = transcript.strip() if transcript else ""
        logger.info("[whisper] transcribed %d chars from %s: '%s'",
                   len(transcript_text), audio_url[:30] + "...", transcript_text[:100])

        return transcript_text

    except httpx.HTTPError as e:
        logger.error("[whisper] failed to download audio from %s: %s", audio_url, e)
        raise ValueError(f"Failed to download audio: {e}")
    except Exception as e:
        logger.error("[whisper] transcription failed for %s: %s", audio_url, e)
        raise ValueError(f"Transcription failed: {e}")


async def transcribe_speech_result(speech_result: str) -> str:
    """
    Process SpeechResult from Twilio Gather (already transcribed by Twilio).
    This is for compatibility - Twilio already provides transcription in SpeechResult.

    Args:
        speech_result: Text from Twilio's speech recognition

    Returns:
        Cleaned speech text
    """
    if not speech_result:
        return ""

    # Basic cleaning for Twilio speech results
    cleaned = speech_result.strip()

    # Log for monitoring
    logger.info("[whisper] processed speech result: '%s' -> '%s'",
               speech_result[:100], cleaned[:100])

    return cleaned


async def transcribe_with_cache(
    call_sid: str,
    audio_url: Optional[str] = None,
    speech_result: Optional[str] = None,
    redis_client=None,
    cache_ttl: int = 3600
) -> str:
    """
    Transcribe audio with Redis caching to prevent re-processing on webhook retries.

    Args:
        call_sid: Twilio call ID for cache key
        audio_url: Twilio recording URL (if available)
        speech_result: Pre-transcribed text from Twilio (if available)
        redis_client: Redis client for caching
        cache_ttl: Cache time-to-live in seconds

    Returns:
        Transcribed text
    """
    # Use speech_result if available (Twilio already transcribed)
    if speech_result and speech_result.strip():
        return await transcribe_speech_result(speech_result)

    # If no speech_result but have audio_url, use Whisper
    if audio_url:
        # Check cache first if Redis available
        if redis_client:
            cache_key = f"transcript:{call_sid}:{hash(audio_url)}"
            try:
                cached = redis_client.get(cache_key)
                if cached:
                    logger.info("[whisper] cache hit for %s", call_sid)
                    return cached.decode('utf-8')
            except Exception as e:
                logger.warning("[whisper] cache read failed: %s", e)

        # Transcribe with Whisper
        transcript = await transcribe_audio_url(audio_url)

        # Store in cache if Redis available
        if redis_client and transcript:
            try:
                redis_client.setex(cache_key, cache_ttl, transcript)
                logger.info("[whisper] cached transcript for %s", call_sid)
            except Exception as e:
                logger.warning("[whisper] cache write failed: %s", e)

        return transcript

    # No audio source available
    logger.warning("[whisper] no audio source provided for %s", call_sid)
    return ""


# Cost estimation helper
def estimate_whisper_cost(audio_duration_minutes: float) -> float:
    """
    Estimate Whisper API cost.
    Current pricing: $0.006 per minute
    """
    return audio_duration_minutes * 0.006


if __name__ == "__main__":
    # Test example
    import asyncio

    async def test():
        # Test with sample text (simulating Twilio speech result)
        result = await transcribe_speech_result("Hello, my name is John Smith")
        print(f"Processed: {result}")

    asyncio.run(test())
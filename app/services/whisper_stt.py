# app/services/whisper_stt.py
"""
Whisper-based Speech-to-Text service for Twilio audio processing.
Replaces the unified LLM approach with specialized transcription.
"""

import logging
import os
import time
from typing import Optional
import httpx
from openai import AsyncOpenAI
import asyncio

from app.services.circuit_breaker import circuit_manager, CircuitBreakerException

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
            timeout=15.0,  # Reduced from 30s to 15s
            max_retries=2  # Enable retries for reliability
        )
        logger.info("OpenAI Whisper client initialized: %s", base_url)

    return _openai_client


async def transcribe_audio_url(audio_url: str, language: str = "en", max_retries: int = 2) -> str:
    """
    Transcribe audio from Twilio webhook URL using Whisper with optimized performance.

    Args:
        audio_url: Twilio recording URL (e.g., from RecordingUrl parameter)
        language: Language code (default: "en" for English)
        max_retries: Maximum number of retry attempts

    Returns:
        Transcribed text string
    """
    if not audio_url:
        raise ValueError("Audio URL is required")

    client = get_openai_client()
    start_time = time.time()

    for attempt in range(max_retries + 1):
        try:
            # Optimized HTTP client with aggressive timeouts for sub-2s performance
            timeout_config = httpx.Timeout(
                connect=2.0,   # 2s to establish connection
                read=8.0,      # 8s to download audio (most Twilio recordings are <1MB)
                write=1.0,     # 1s to send request
                pool=1.0       # 1s for connection pooling
            )

            async with httpx.AsyncClient(
                timeout=timeout_config,
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
            ) as http_client:
                logger.debug("[whisper] attempt %d: downloading from %s", attempt + 1, audio_url[:50] + "...")

                # Use asyncio.wait_for for additional timeout protection
                download_task = http_client.get(audio_url)
                response = await asyncio.wait_for(download_task, timeout=10.0)
                response.raise_for_status()
                audio_data = response.content

            download_time = time.time() - start_time
            logger.info("[whisper] downloaded %d bytes in %.2fs from %s",
                       len(audio_data), download_time, audio_url[:50] + "...")

            # Create file-like object for OpenAI - detect format from content
            content_type = response.headers.get("content-type", "audio/wav")
            if "mp3" in content_type:
                audio_file = ("audio.mp3", audio_data, "audio/mp3")
            elif "mp4" in content_type or "m4a" in content_type:
                audio_file = ("audio.m4a", audio_data, "audio/mp4")
            else:
                audio_file = ("audio.wav", audio_data, "audio/wav")

            # Transcribe using Whisper with circuit breaker protection
            transcription_start = time.time()

            # Get circuit breaker for OpenAI API
            openai_breaker = circuit_manager.get_breaker("openai_api")
            if not openai_breaker:
                logger.error("OpenAI circuit breaker not found - proceeding without protection")

            async def _transcribe():
                return await client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language=language,
                    response_format="text",
                    temperature=0.0  # Fastest processing (no randomness)
                )

            # Execute through circuit breaker if available
            if openai_breaker:
                try:
                    transcript = await openai_breaker.call(_transcribe)
                except CircuitBreakerException as e:
                    logger.warning(f"Circuit breaker blocked OpenAI call: {e}")
                    # Return fallback response indicating manual assistance needed
                    return "I'm having trouble processing your request right now. Please hold while I get you connected to our staff."
            else:
                transcript = await _transcribe()

            transcription_time = time.time() - transcription_start
            total_time = time.time() - start_time

            transcript_text = transcript.strip() if transcript else ""
            logger.info("[whisper] transcribed %d chars in %.2fs (total: %.2fs) from %s: '%s'",
                       len(transcript_text), transcription_time, total_time,
                       audio_url[:30] + "...", transcript_text[:100])

            # Performance warning if over target
            if total_time > 2.0:
                logger.warning("[whisper] SLOW transcription: %.2fs (target: <2s)", total_time)

            return transcript_text

        except asyncio.TimeoutError:
            logger.warning("[whisper] attempt %d timed out for %s", attempt + 1, audio_url[:50] + "...")
            if attempt == max_retries:
                raise ValueError(f"Transcription timed out after {max_retries + 1} attempts")
        except httpx.HTTPError as e:
            logger.warning("[whisper] attempt %d HTTP error for %s: %s", attempt + 1, audio_url[:50] + "...", e)
            if attempt == max_retries:
                raise ValueError(f"Failed to download audio after {max_retries + 1} attempts: {e}")
        except Exception as e:
            logger.warning("[whisper] attempt %d failed for %s: %s", attempt + 1, audio_url[:50] + "...", e)
            if attempt == max_retries:
                raise ValueError(f"Transcription failed after {max_retries + 1} attempts: {e}")

        # Exponential backoff between retries (0.1s, 0.2s, 0.4s)
        if attempt < max_retries:
            backoff_time = 0.1 * (2 ** attempt)
            logger.debug("[whisper] retrying in %.1fs...", backoff_time)
            await asyncio.sleep(backoff_time)


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
    Transcribe audio with intelligent caching and performance optimization.

    Args:
        call_sid: Twilio call ID for cache key
        audio_url: Twilio recording URL (if available)
        speech_result: Pre-transcribed text from Twilio (if available)
        redis_client: Redis client for caching
        cache_ttl: Cache time-to-live in seconds

    Returns:
        Transcribed text
    """
    cache_start = time.time()

    # Use speech_result if available (Twilio already transcribed) - fastest path
    if speech_result and speech_result.strip():
        result = await transcribe_speech_result(speech_result)
        logger.info("[whisper] used Twilio speech result in %.3fs", time.time() - cache_start)
        return result

    # If no speech_result but have audio_url, use Whisper with caching
    if audio_url:
        # Generate cache key based on URL hash for consistency
        url_hash = abs(hash(audio_url)) % (10**8)  # Stable 8-digit hash
        cache_key = f"whisper:transcript:{call_sid}:{url_hash}"

        # Multi-level cache check for performance
        if redis_client:
            try:
                # Check cache with timeout protection
                cache_check = asyncio.create_task(
                    asyncio.to_thread(redis_client.get, cache_key)
                )
                cached = await asyncio.wait_for(cache_check, timeout=0.1)  # 100ms cache timeout

                if cached:
                    if isinstance(cached, bytes):
                        cached = cached.decode('utf-8')

                    cache_time = time.time() - cache_start
                    logger.info("[whisper] cache hit for %s in %.3fs", call_sid[:8], cache_time)
                    return cached

            except asyncio.TimeoutError:
                logger.warning("[whisper] cache check timed out for %s", call_sid[:8])
            except Exception as e:
                logger.warning("[whisper] cache read failed for %s: %s", call_sid[:8], e)

        logger.info("[whisper] cache miss for %s, transcribing...", call_sid[:8])

        # Transcribe with optimized Whisper
        transcript = await transcribe_audio_url(audio_url, max_retries=2)

        # Async cache write to avoid blocking response
        if redis_client and transcript:
            async def write_cache():
                try:
                    cache_write = asyncio.create_task(
                        asyncio.to_thread(redis_client.setex, cache_key, cache_ttl, transcript)
                    )
                    await asyncio.wait_for(cache_write, timeout=0.5)  # 500ms cache write timeout
                    logger.debug("[whisper] cached transcript for %s", call_sid[:8])
                except Exception as e:
                    logger.warning("[whisper] cache write failed for %s: %s", call_sid[:8], e)

            # Fire and forget cache write
            asyncio.create_task(write_cache())

        total_time = time.time() - cache_start
        logger.info("[whisper] transcription complete for %s in %.2fs", call_sid[:8], total_time)
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
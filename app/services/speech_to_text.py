"""
OpenAI Whisper Speech-to-Text Service
Integrates with existing whisper_stt.py for voice call transcription
"""

import openai
import tempfile
import os
import logging
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

class SpeechToTextService:
    def __init__(self):
        openai.api_key = settings.OPENAI_API_KEY

    async def transcribe_audio(self, audio_url: str, call_sid: str) -> str:
        """
        Transcribe audio using OpenAI Whisper API
        Integrates with existing whisper_stt service
        """
        try:
            # Use existing whisper service if available
            from app.services.whisper_stt import transcribe_with_cache
            from app.services.redis_session import get_redis_client

            redis_client = get_redis_client()

            # Use existing cached transcription service
            transcript = await transcribe_with_cache(
                call_sid=call_sid,
                speech_result=audio_url,  # Pass the audio URL
                redis_client=redis_client,
                cache_ttl=1800  # 30 minutes cache
            )

            return transcript.strip()

        except ImportError:
            # Fallback to direct OpenAI API if existing service not available
            return await self._direct_whisper_transcribe(audio_url, call_sid)
        except Exception as e:
            logger.error(f"Speech transcription failed for {call_sid}: {e}")
            return ""

    async def _direct_whisper_transcribe(self, audio_url: str, call_sid: str) -> str:
        """Direct OpenAI Whisper API call as fallback"""
        try:
            import aiohttp

            # Download audio from Twilio
            async with aiohttp.ClientSession() as session:
                async with session.get(audio_url) as response:
                    audio_data = await response.read()

            # Save to temp file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name

            try:
                # Transcribe with Whisper
                with open(temp_file_path, "rb") as audio_file:
                    transcript = openai.Audio.transcribe(
                        model="whisper-1",
                        file=audio_file,
                        language="en"
                    )

                return transcript.text.strip()

            finally:
                os.unlink(temp_file_path)

        except Exception as e:
            logger.error(f"Direct Whisper transcription failed for {call_sid}: {e}")
            return ""
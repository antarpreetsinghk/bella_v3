"""
Enhanced Call Handler for Voice Appointment Booking
Integrates with existing Twilio routes and services
"""

import logging
from datetime import datetime
from typing import Dict, Optional
from fastapi import Request
from twilio.twiml import VoiceResponse

# Import existing services
from app.services.speech_to_text import SpeechToTextService
from app.services.appointment_extractor import AppointmentExtractor
from app.services.calendar_service import GoogleCalendarService
from app.utils.debugging import debug_call_flow, CallLogger

# Import existing infrastructure
from app.services.redis_session import get_session as get_call_session, save_session
from app.services.booking import book_from_transcript
from app.core.config import settings

logger = logging.getLogger(__name__)

class EnhancedCallHandler:
    """
    Enhanced call handler that integrates with existing Bella services
    Provides additional functionality while leveraging existing infrastructure
    """

    def __init__(self):
        self.stt_service = SpeechToTextService()
        self.extractor = AppointmentExtractor()
        self.calendar = GoogleCalendarService()
        self.call_logger = CallLogger()

    @debug_call_flow("enhanced_voice_entry")
    async def enhanced_voice_entry(self, call_sid: str, from_number: str) -> str:
        """Enhanced voice entry point with automatic caller ID capture"""
        # Start business metrics tracking
        try:
            from app.services.business_metrics import business_metrics
            await business_metrics.start_call_tracking(call_sid)
        except ImportError:
            pass

        sess = get_call_session(call_sid)

        # Automatic caller ID capture using existing phone extraction
        caller_phone = None
        if from_number and from_number.strip():
            try:
                from app.api.routes.twilio import _extract_phone_fast
                caller_phone = _extract_phone_fast(from_number)
                if caller_phone:
                    sess.data["mobile"] = caller_phone
                    sess.data["mobile_source"] = "caller_id"
                    save_session(sess)
                    logger.info(f"[enhanced_voice] captured caller ID {call_sid}")
            except Exception as e:
                logger.warning(f"Failed to extract caller ID: {e}")

        # Enhanced greeting with existing TwiML format
        response = VoiceResponse()

        gather = response.gather(
            input='speech dtmf',
            timeout=10,
            action='/twilio/voice/collect',
            method='POST',
            speech_timeout='auto',
            language='en-CA',
            enhanced='true'
        )

        # Personalized greeting if we have caller ID
        if caller_phone:
            gather.say("Hi! Thanks for calling back. I'll help you book your appointment today. What's your name?",
                      voice="alice", language="en-CA")
        else:
            gather.say("Hi there! Thanks for calling. I'll help you book your appointment today. What's your name?",
                      voice="alice", language="en-CA")

        response.say("I didn't hear anything. Please try again.", voice="alice", language="en-CA")
        response.redirect('/twilio/voice')

        await self.call_logger.log_call_event(call_sid, "enhanced_call_started", {
            "from": from_number,
            "caller_id_captured": bool(caller_phone)
        })

        return str(response)

    @debug_call_flow("enhanced_speech_processing")
    async def enhanced_speech_processing(self, call_sid: str, speech_result: str) -> Dict:
        """Enhanced speech processing with multiple extraction methods"""

        # Use existing Whisper service for transcription
        cleaned_speech = speech_result  # Already transcribed by Twilio

        try:
            from app.services.whisper_stt import transcribe_with_cache
            from app.services.redis_session import get_redis_client

            redis_client = get_redis_client()
            cleaned_speech = await transcribe_with_cache(
                call_sid=call_sid,
                speech_result=speech_result,
                redis_client=redis_client,
                cache_ttl=1800
            )
        except ImportError:
            logger.info("Using direct speech result without Whisper enhancement")
        except Exception as e:
            logger.warning(f"Whisper enhancement failed: {e}")

        # Extract appointment information
        extracted_info = await self.extractor.extract_appointment_info(cleaned_speech)

        await self.call_logger.log_call_event(call_sid, "enhanced_speech_processed", {
            "original": speech_result[:100],
            "cleaned": cleaned_speech[:100],
            "extracted": extracted_info
        })

        return {
            "original_speech": speech_result,
            "cleaned_speech": cleaned_speech,
            "extracted_info": extracted_info
        }

    @debug_call_flow("enhanced_availability_check")
    async def enhanced_availability_check(self, appointment_datetime: datetime, duration: int = 30) -> Dict:
        """Enhanced availability checking with detailed response"""

        is_available = await self.calendar.check_availability(appointment_datetime, duration)

        result = {
            "is_available": is_available,
            "requested_time": appointment_datetime.isoformat(),
            "duration_minutes": duration
        }

        if not is_available:
            # Get alternative slots
            try:
                alternative_slots = await self.calendar.get_available_slots(
                    appointment_datetime.date(), duration
                )
                result["alternative_slots"] = [slot.isoformat() for slot in alternative_slots[:3]]
            except Exception as e:
                logger.error(f"Failed to get alternative slots: {e}")
                result["alternative_slots"] = []

        return result

    @debug_call_flow("enhanced_booking_completion")
    async def enhanced_booking_completion(self, db, sess_data: Dict, call_sid: str) -> Dict:
        """Enhanced booking completion with calendar integration"""

        try:
            # Extract data from session
            full_name = sess_data.get("full_name")
            mobile = sess_data.get("mobile")
            starts_at_utc = sess_data.get("starts_at_utc")
            duration_min = int(sess_data.get("duration_min", 30))

            if not all([full_name, mobile, starts_at_utc]):
                return {
                    "success": False,
                    "error": "Missing required booking information",
                    "missing_fields": [
                        field for field, value in [
                            ("name", full_name),
                            ("phone", mobile),
                            ("datetime", starts_at_utc)
                        ] if not value
                    ]
                }

            # Check availability one more time
            availability = await self.enhanced_availability_check(starts_at_utc, duration_min)
            if not availability["is_available"]:
                return {
                    "success": False,
                    "error": "Time slot no longer available",
                    "alternative_slots": availability.get("alternative_slots", [])
                }

            # Create booking transcript for existing booking service
            from zoneinfo import ZoneInfo
            LOCAL_TZ = ZoneInfo("America/Edmonton")

            booking_transcript = (
                f"Name: {full_name}, Phone: {mobile}, "
                f"Time: {starts_at_utc.astimezone(LOCAL_TZ).strftime('%A, %B %d at %I:%M %p')}, "
                f"Duration: {duration_min} minutes"
            )

            # Use existing booking service
            booking_result = await book_from_transcript(
                db,
                transcript=booking_transcript,
                from_number=mobile,
                locale="en-CA"
            )

            if not booking_result.created:
                return {
                    "success": False,
                    "error": "Database booking failed",
                    "message": booking_result.message_for_caller
                }

            # Create calendar event
            calendar_event_id = await self.calendar.create_appointment({
                "name": full_name,
                "phone": mobile,
                "datetime": starts_at_utc,
                "duration": duration_min,
                "notes": f"Booked via voice call {call_sid}"
            })

            await self.call_logger.log_call_event(call_sid, "enhanced_booking_completed", {
                "appointment_id": booking_result.appointment_id if hasattr(booking_result, 'appointment_id') else None,
                "calendar_event_id": calendar_event_id,
                "customer": full_name,
                "datetime": starts_at_utc.isoformat()
            })

            return {
                "success": True,
                "appointment_id": getattr(booking_result, 'appointment_id', None),
                "calendar_event_id": calendar_event_id,
                "booking_result": booking_result,
                "formatted_time": starts_at_utc.astimezone(LOCAL_TZ).strftime("%A, %B %d at %I:%M %p")
            }

        except Exception as e:
            logger.exception(f"Enhanced booking completion failed for {call_sid}")
            await self.call_logger.log_call_event(call_sid, "enhanced_booking_error", {
                "error": str(e),
                "session_data": sess_data
            })

            return {
                "success": False,
                "error": f"Booking system error: {str(e)}"
            }

    def generate_twiml_response(self, message: str, action: str = None, gather_input: str = "speech") -> str:
        """Generate TwiML response with consistent formatting"""
        response = VoiceResponse()

        if action:
            gather = response.gather(
                input=gather_input,
                timeout=10,
                action=action,
                method='POST',
                speech_timeout='auto',
                language='en-CA',
                enhanced='true'
            )
            gather.say(message, voice="alice", language="en-CA")

            response.say("I didn't catch that. Let me try again.", voice="alice", language="en-CA")
            response.redirect('/twilio/voice')
        else:
            response.say(message, voice="alice", language="en-CA")
            response.hangup()

        return str(response)
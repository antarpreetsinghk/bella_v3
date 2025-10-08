# app/api/routes/twilio.py
import json
import logging
import re
from datetime import datetime
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from zoneinfo import ZoneInfo

# Advanced extraction libraries
import phonenumbers
from phonenumbers import PhoneNumberFormat

# Canadian-optimized extraction
from app.services.canadian_extraction import (
    extract_canadian_phone,
    extract_canadian_time,
    extract_canadian_name,
    format_phone_for_speech
)

from app.db.session import get_session
from app.services.redis_session import get_session as get_call_session, reset_session, save_session, get_redis_client
from app.services.simple_extraction import (
    transcribe_with_cache,
    extract_appointment_fields,
    clean_and_enhance_speech,
    unified_appointment_extraction,
    extract_name_simple,
    extract_phone_simple,
    extract_key_phrases
)
from app.services.business_metrics import business_metrics
from app.services.booking import _parse_to_utc as parse_to_utc, book_from_transcript  # reuse future-only guard
from app.crud.user import get_user_by_mobile, create_user
from app.crud.appointment import create_appointment_unique
from app.core.performance import performance_middleware, ResponseOptimizer
from app.schemas.user import UserCreate

# Optional business-hours support (works if you added app/core/business.py)
try:
    from app.core.business import is_within_hours, next_opening, LOCAL_TZ
    HAVE_BH = True
except Exception:
    HAVE_BH = False
    LOCAL_TZ = ZoneInfo("America/Edmonton")

router = APIRouter(prefix="/twilio", tags=["twilio"])
TWIML_CT = "application/xml"

# Use uvicorn logger like your current file
logger = logging.getLogger("uvicorn.error")


def _twiml(xml: str) -> Response:
    return Response(content=xml, media_type=TWIML_CT)


def _mask_phone(s: str | None) -> str:
    if not s:
        return ""
    s = s.strip()
    if s.startswith("+") and len(s) > 4:
        return s[:3] + "****" + s[-3:]
    if len(s) > 4:
        return s[:2] + "****" + s[-2:]
    return s


def _gather_block(prompt: str, timeout: int = 10, include_dtmf: bool = False, dtmf_instructions: str = "") -> str:
    """
    Cost-optimized gathering with both speech and keypad support.
    Enhanced=true improves accuracy for Canadian English accents.
    """
    input_types = "speech dtmf" if include_dtmf else "speech"
    full_prompt = f"{prompt} {dtmf_instructions}" if dtmf_instructions else prompt

    return f"""
  <Gather input="{input_types}"
          language="en-CA"
          method="POST"
          action="/twilio/voice/collect"
          actionOnEmptyResult="true"
          speechTimeout="auto"
          timeout="{timeout}"
          numDigits="1"
          enhanced="true">
    <Say voice="alice" language="en-CA">{full_prompt}</Say>
  </Gather>
  <Say voice="alice" language="en-CA">Sorry, I didn't catch that.</Say>
  <Redirect method="POST">/twilio/voice</Redirect>
"""


def _gather_block_confirmation(prompt: str, timeout: int = 15) -> str:
    """
    Specialized gather block for confirmation prompts with optimized speech recognition.
    """
    return f"""
  <Gather input="speech"
          language="en-CA"
          method="POST"
          action="/twilio/voice/collect"
          actionOnEmptyResult="false"
          speechTimeout="auto"
          timeout="{timeout}"
          enhanced="true"
          hints="yes,no,yeah,yep,nope">
    <Say voice="alice" language="en-CA">{prompt}</Say>
  </Gather>
  <Say voice="alice" language="en-CA">I'm sorry, I didn't hear a clear yes or no. Let me ask again.</Say>
  <Redirect method="POST">/twilio/voice</Redirect>
"""


def _extract_digits(s: str) -> str:
    """Extract digits from string, handling both numeric and word formats."""
    if not s:
        return ""

    # First try direct digit extraction
    digits = re.sub(r"\D+", "", s)
    if digits:
        return digits

    # Handle word-to-digit conversion for speech-to-text
    word_to_digit = {
        "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4",
        "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
        "oh": "0"  # Common speech pattern for zero
    }

    words = s.lower().split()
    digit_result = ""
    for word in words:
        if word in word_to_digit:
            digit_result += word_to_digit[word]
        elif word.isdigit():
            digit_result += word

    logger.info("[extract_digits] input='%s' -> digits='%s'", s, digit_result)
    return digit_result


def _extract_phone_fast(raw: str) -> str | None:
    """Fast phone number extraction using Google's phonenumbers library."""
    if not raw:
        return None

    raw = raw.strip()
    logger.info("[phone_fast] processing: '%s'", raw)

    # Try direct phonenumbers parsing first (handles most formats)
    for region in ["US", "CA"]:  # North American regions
        try:
            parsed = phonenumbers.parse(raw, region)
            if phonenumbers.is_valid_number(parsed):
                result = phonenumbers.format_number(parsed, PhoneNumberFormat.E164)
                logger.info("[phone_fast] phonenumbers success: '%s' -> %s", raw, result)
                return result
        except phonenumbers.phonenumberutil.NumberParseException:
            continue

    # Fallback: extract digits and try again (for speech-to-text like "four one six...")
    digits = _extract_digits(raw)
    if digits and len(digits) >= 7:
        try:
            # Try as North American number
            if len(digits) == 10:
                candidate = f"+1{digits}"
            elif len(digits) == 11 and digits.startswith("1"):
                candidate = f"+{digits}"
            else:
                candidate = digits

            parsed = phonenumbers.parse(candidate, "US")
            if phonenumbers.is_valid_number(parsed):
                result = phonenumbers.format_number(parsed, PhoneNumberFormat.E164)
                logger.info("[phone_fast] digits fallback: '%s' -> %s", raw, result)
                return result
        except phonenumbers.phonenumberutil.NumberParseException:
            pass

    logger.warning("[phone_fast] failed to parse: '%s'", raw)
    return None


def _normalize_phone_for_ca_us(raw: str) -> str | None:
    """Legacy function - now uses fast extraction."""
    return _extract_phone_fast(raw)


def _summary(sess_data: dict) -> str:
    name = sess_data.get("full_name") or "Unknown"
    mobile_raw = sess_data.get("mobile") or "Unknown"
    mobile = format_phone_for_speech(mobile_raw) if mobile_raw != "Unknown" else "Unknown"
    when_local = "Unknown"
    if sess_data.get("starts_at_utc"):
        when_local = sess_data["starts_at_utc"].astimezone(LOCAL_TZ).strftime("%A, %B %d at %I:%M %p")
    return f"{name}, {mobile}, {when_local}"


def _followup_prompt(missing: list[str] | None) -> str:
    missing = missing or []
    if "mobile" in missing and "starts_at" in missing and "full_name" in missing:
        return "Could you please share your full name, your phone number, and the exact date and time you’d like?"
    if "mobile" in missing and "starts_at" in missing:
        return "Could you please share your phone number and the exact date and time you’d like?"
    if "full_name" in missing:
        return "Could you please tell me your full name for the booking?"
    if "mobile" in missing:
        return "Could you please share the best phone number to reach you?"
    if "starts_at" in missing:
        return "Could you please tell me the exact date and time you’d like for your appointment?"
    return "Could you please share your full name, phone number, and the exact date and time you’d like to book?"


@router.post("/voice")
async def voice_entry(
    CallSid: str = Form(default=""),
    From: str = Form(default="")
):
    """Enhanced voice entry with caller profiles and smart routing."""

    # Start business metrics tracking for this call
    await business_metrics.start_call_tracking(CallSid)

    sess = get_call_session(CallSid)

    # ENHANCED CALLER ID CAPTURE WITH PROFILE LOOKUP
    greeting_message = "Hi there! Thanks for calling. I'll help you book your appointment today."

    if From and From.strip():
        try:
            # Import enhanced session management
            from app.services.redis_session import enhance_session_with_caller_id, get_personalized_greeting

            # Enhance session with caller ID and profile
            sess = await enhance_session_with_caller_id(sess, From)
            save_session(sess)

            # Use personalized greeting for returning customers
            if sess.caller_profile and sess.caller_profile.is_returning:
                greeting_message = await get_personalized_greeting(sess.caller_profile)

                # Add calendar availability overview for returning customers
                try:
                    from app.services.google_calendar import get_calendar_summary
                    calendar_summary = await get_calendar_summary()
                    availability_msg = calendar_summary.get("message", "")
                    if availability_msg:
                        greeting_message += f" {availability_msg}"
                except Exception as e:
                    logger.warning("[voice] Failed to get calendar summary: %s", e)

                logger.info("[voice] returning customer call=%s name=%s", CallSid, sess.caller_profile.full_name)
            else:
                logger.info("[voice] new/unknown caller call=%s phone=%s", CallSid, _mask_phone(From))

        except Exception as e:
            logger.error("[voice] caller profile enhancement failed: %s", e)
            # Fall back to basic caller ID capture
            caller_phone = _extract_phone_fast(From)
            if caller_phone:
                sess.data["mobile"] = caller_phone
                sess.data["mobile_source"] = "caller_id"
                save_session(sess)

    # Determine next step based on caller profile
    if sess.step == "ask_time" and sess.caller_profile and sess.caller_profile.is_returning:
        # Enhanced time selection with smart suggestions for returning customers
        time_prompt = f"{greeting_message} What day and time would you like to book?"

        # Add intelligent suggestions based on user preferences
        if sess.caller_profile.preferred_times:
            try:
                from app.services.google_calendar import find_best_slot_for_preference
                best_slot = await find_best_slot_for_preference(
                    sess.caller_profile.preferred_times,
                    sess.caller_profile.preferred_duration,
                    days_ahead=7
                )

                if best_slot:
                    from datetime import datetime as dt
                    best_local = best_slot.astimezone(LOCAL_TZ)
                    if best_local.date() == dt.now(LOCAL_TZ).date():
                        suggestion = f"today at {best_local.strftime('%I:%M %p')}"
                    else:
                        suggestion = best_local.strftime("%A at %I:%M %p")

                    time_prompt += f" I have {suggestion} available, which matches your usual preferences."

            except Exception as e:
                logger.warning("[voice] Failed to get preference-based suggestions: %s", e)

        prompt = time_prompt
    else:
        # Standard flow for new customers
        prompt = f"{greeting_message} What's your name?"

    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
{_gather_block(prompt)}
</Response>"""

    logger.info("[voice] start call=%s step=%s profile=%s",
                CallSid, sess.step, "returning" if sess.caller_profile else "new")
    return _twiml(twiml)


@router.post("/voice/collect")
async def voice_collect(
    request: Request,
    db: AsyncSession = Depends(get_session),
    SpeechResult: str = Form(default=""),
    Digits: str = Form(default=""),
    From: str = Form(default=""),
    CallSid: str = Form(default=""),
):
    """
    Cost-optimized multi-turn stepper with smart speech handling:
      ask_name -> ask_mobile -> ask_time -> ask_duration -> confirm -> book
    Supports both speech and keypad input for better UX and cost control.
    """
    speech = (SpeechResult or "").strip()
    digits = (Digits or "").strip()
    from_num_masked = _mask_phone(From)
    sess = get_call_session(CallSid)

    # SMART SPEECH PROCESSING: Use simple extraction with fallback
    extracted_info = {}
    user_input = digits if digits else speech  # Prefer keypad input when available

    if user_input:
        try:
            # Step-specific extraction using simple, fast methods
            if sess.step == "ask_name":
                if digits:
                    # Keypad not useful for names, prompt for speech
                    extracted_info["name"] = None
                else:
                    extracted_name = extract_name_simple(speech)
                    extracted_info["name"] = extracted_name

            elif sess.step == "ask_mobile":
                if digits:
                    # Clean keypad input for phone
                    extracted_phone = _extract_phone_fast(digits)
                else:
                    extracted_phone = extract_phone_simple(speech)
                extracted_info["mobile"] = extracted_phone

            elif sess.step == "ask_time":
                if digits:
                    # Handle keypad shortcuts for common times
                    time_shortcuts = {
                        "1": "9:00 AM tomorrow",
                        "2": "10:00 AM tomorrow",
                        "3": "11:00 AM tomorrow",
                        "4": "2:00 PM tomorrow",
                        "5": "3:00 PM tomorrow",
                        "6": "4:00 PM tomorrow"
                    }
                    extracted_info["time"] = time_shortcuts.get(digits, digits)
                else:
                    # Use simple time parsing with key phrases
                    key_phrases = extract_key_phrases(speech, "time")
                    extracted_info["time"] = key_phrases if key_phrases else speech.strip()

            elif sess.step == "ask_duration":
                if digits:
                    # Direct keypad mapping for duration
                    duration_map = {"1": 30, "2": 45, "3": 60}
                    extracted_info["duration"] = duration_map.get(digits, 30)
                else:
                    # Extract duration from speech
                    if "45" in speech or "forty" in speech.lower():
                        extracted_info["duration"] = 45
                    elif "60" in speech or "hour" in speech.lower():
                        extracted_info["duration"] = 60
                    else:
                        extracted_info["duration"] = 30

            # Store simplified speech processing history
            sess.last_raw_speech = speech
            sess.last_cleaned_speech = user_input
            sess.speech_history.append({
                "timestamp": sess.updated_at.isoformat(),
                "step": sess.step,
                "input_type": "keypad" if digits else "speech",
                "raw": user_input[:100],  # Limit storage
                "extracted": extracted_info
            })
            save_session(sess)

            logger.info(
                "[smart_extract] call=%s step=%s input_type=%s input='%s' extracted=%s",
                CallSid, sess.step, "keypad" if digits else "speech",
                user_input[:50], extracted_info
            )

        except Exception as e:
            logger.warning("[smart_extract] failed: %s, using raw input", e)
            # Fallback to raw input
            sess.last_raw_speech = speech if speech else digits
            sess.last_cleaned_speech = user_input
            save_session(sess)

    logger.info(
        "[collect] call=%s step=%s from=%s speech=%s",
        CallSid, sess.step, from_num_masked, speech if speech else "<empty>",
    )

    # If nothing heard, gently reprompt the current step
    if not user_input:
        polite = {
            "ask_name": "I'm sorry—I didn't catch that. Could you please tell me your full name?",
            "confirm_name": "I'm sorry—I didn't catch that. Please say Yes if the name is correct, or No if it's wrong.",
            "ask_mobile": "I'm sorry—I didn't catch that. Could you please say your phone number, digit by digit?",
            "ask_time": "I'm sorry—I didn't catch that. Could you please say the exact date and time you'd like?",
            "ask_duration": "I'm sorry—I didn't catch that. Press 1 for 30 minutes, 2 for 45 minutes, or 3 for 60 minutes.",
            "confirm": "I'm sorry—I didn't catch that. Should I book it? Please say Yes or No.",
        }[sess.step]
        # Use DTMF for duration prompts
        include_dtmf = sess.step == "ask_duration"
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
{_gather_block(polite, include_dtmf=include_dtmf)}
</Response>"""
        return _twiml(twiml)

    # --- Step machine ---
    logger.info("[session_debug] before step=%s data=%s", sess.step, sess.data)

    if sess.step == "ask_name":
        # Use specialized name extractor result
        extracted_name = extracted_info.get("name")

        # Enhanced fallback logic for name extraction with comprehensive speech artifact rejection
        if not extracted_name and cleaned_speech:
            # Only use fallback if it looks like a reasonable name
            words = cleaned_speech.split()
            cleaned_lower = cleaned_speech.lower().strip()

            # Comprehensive bad word/phrase detection
            bad_patterns = [
                # Direct speech artifacts
                "so what", "sowhat", "so", "what", "what about", "how about",
                # Questions and responses
                "yes", "no", "yeah", "yep", "nope", "okay", "ok",
                # Greetings and politeness
                "hello", "hi", "hey", "thanks", "thank you", "please",
                # Appointment-related words
                "appointment", "book", "booking", "schedule", "time",
                # Speech fillers
                "um", "uh", "ah", "oh", "well", "like", "you know",
                # Common misinterpretations
                "called", "calling", "speaking", "pit", "pit called",
                "cold", "her", "him", "that", "this", "with", "for"
            ]

            # Check if the cleaned speech matches any bad patterns
            is_bad_speech = any(bad_pattern in cleaned_lower for bad_pattern in bad_patterns)

            # Additional check: if the entire phrase is just bad words
            all_words_bad = all(word.lower() in bad_patterns for word in words)

            # Check for question patterns that indicate non-name speech
            question_patterns = ["can you", "could you", "will you", "do you", "are you"]
            is_question = any(pattern in cleaned_lower for pattern in question_patterns)

            if (len(words) >= 1 and len(words) <= 4 and
                all(len(w) >= 2 and w.replace("'", "").isalpha() for w in words) and
                not is_bad_speech and not all_words_bad and not is_question):
                extracted_name = " ".join(words).title()
                logger.info("[ask_name] using fallback name extraction: '%s'", extracted_name)
            else:
                logger.info("[ask_name] fallback rejected, poor name quality: '%s' (bad_speech=%s, all_bad=%s, question=%s)",
                           cleaned_speech, is_bad_speech, all_words_bad, is_question)

        # Only proceed if we have a valid name
        if extracted_name and len(extracted_name.strip()) >= 2:
            sess.data["full_name"] = extracted_name
            logger.info("[ask_name] final name: '%s' (from speech: '%s')",
                       sess.data["full_name"], speech)

            # Move to name confirmation step
            sess.step = "confirm_name"
            save_session(sess)  # Persist state change
            logger.info("[session_debug] after ask_name step=%s data=%s", sess.step, sess.data)
            return _twiml(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
{_gather_block_confirmation(f"I heard '{sess.data['full_name']}'. Is that correct? Please say Yes or No.")}
</Response>""")
        else:
            # No valid name extracted, ask again
            logger.info("[ask_name] no valid name extracted from: '%s', asking again", speech)
            return _twiml(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
{_gather_block("I'm sorry—I didn't catch your name clearly. Could you please tell me your full name again?")}
</Response>""")

    if sess.step == "confirm_name":
        logger.info("[confirm_name] processing speech: '%s'", speech)
        speech_lower = speech.lower().strip()

        # Check for positive confirmation (flexible matching)
        if any(word in speech_lower for word in ["yes", "yeah", "yep", "correct", "right"]):
            # Name confirmed, check if we have caller ID for phone
            if sess.data.get("mobile") and sess.data.get("mobile_source") == "caller_id":
                # Skip phone collection, go straight to time
                sess.step = "ask_time"
                save_session(sess)
                caller_phone_formatted = format_phone_for_speech(sess.data["mobile"])
                logger.info("[confirm_name] name confirmed: '%s', using caller ID: %s",
                          sess.data["full_name"], _mask_phone(sess.data["mobile"]))
                return _twiml(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
{_gather_block(f"Perfect! I have your number as {caller_phone_formatted}. When would you like your appointment?")}
</Response>""")
            else:
                # No caller ID, proceed to ask for phone
                sess.step = "ask_mobile"
                save_session(sess)
                logger.info("[confirm_name] name confirmed: '%s', asking for phone", sess.data["full_name"])
                return _twiml(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
{_gather_block("Perfect! What's your phone number?")}
</Response>""")
        # Check for negative confirmation (flexible matching)
        elif any(word in speech_lower for word in ["no", "nope", "wrong", "incorrect", "not"]):
            # Name incorrect, ask again
            sess.step = "ask_name"
            sess.data.pop("full_name", None)  # Clear the incorrect name
            save_session(sess)
            logger.info("[confirm_name] name rejected, asking again")
            return _twiml(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
{_gather_block("Let me get that right. Please say your full name again, speaking slowly and clearly.")}
</Response>""")
        else:
            # Unclear response, ask for clarification
            return _twiml(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
{_gather_block_confirmation(f"I heard '{sess.data['full_name']}'. Please say Yes if that's correct, or No if it's wrong.")}
</Response>""")

    if sess.step == "ask_mobile":
        logger.info("[ask_mobile] processing speech: '%s'", speech)

        # Use specialized phone extractor result
        norm = extracted_info.get("mobile")

        # Fallback to fast phone extraction if specialized extractor failed
        if not norm and cleaned_speech:
            norm = _extract_phone_fast(cleaned_speech)
        elif not norm:
            norm = _extract_phone_fast(speech)

        if not norm:
            logger.warning("[ask_mobile] phone extraction failed for: '%s'", speech)
            return _twiml(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
{_gather_block("Sorry, I didn't catch that. Can you say your phone number again, including the area code?")}
</Response>""")

        logger.info("[ask_mobile] extracted '%s' -> '%s', advancing to ask_time", speech, norm)
        sess.data["mobile"] = norm
        sess.data["mobile_source"] = "speech"  # Mark as from speech input
        sess.step = "ask_time"
        save_session(sess)  # Persist state change
        logger.info("[session_debug] after ask_mobile step=%s data=%s", sess.step, sess.data)
        return _twiml(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
{_gather_block("Great! When would you like your appointment? You can say something like 'next Tuesday at 2' or 'Friday morning'.")}
</Response>""")

    if sess.step == "ask_time":
        logger.info("[ask_time] processing speech: '%s'", speech)

        # Try Canadian time extraction first (handles natural language)
        starts_at_utc = await extract_canadian_time(speech)

        if not starts_at_utc:
            # Fallback: check if LLM extraction provided an ISO format time
            starts_at_iso = extracted_info.get("time")
            if starts_at_iso:
                try:
                    starts_at_utc = datetime.fromisoformat(starts_at_iso.replace("Z", "+00:00"))
                    logger.info("[ask_time] used LLM ISO time: '%s' -> %s", starts_at_iso, starts_at_utc)
                except Exception as e:
                    logger.warning("[ask_time] failed to parse LLM ISO time '%s': %s", starts_at_iso, e)
                    starts_at_utc = None

        if not starts_at_utc:
            return _twiml(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
{_gather_block("I had trouble understanding that time. Could you please say it again, like Monday at 3 PM?")}
</Response>""")

        logger.info("[ask_time] parsed time '%s' -> %s", speech, starts_at_utc)

        if HAVE_BH:
            local_candidate = starts_at_utc.astimezone(LOCAL_TZ)
            if not is_within_hours(local_candidate):
                suggestion = next_opening(local_candidate) or local_candidate
                return _twiml(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>That time is outside our business hours.</Say>
{_gather_block(f"How about {suggestion.strftime('%A, %B %d at %I:%M %p')}? Or please say another time.")}
</Response>""")

        # ENHANCED: Check Google Calendar availability and suggest alternatives
        try:
            from app.services.google_calendar import check_calendar_availability, suggest_alternative_times

            # Get duration preference (default 30, but check if caller profile has preference)
            duration_preference = 30
            if sess.caller_profile and sess.caller_profile.preferred_duration:
                duration_preference = sess.caller_profile.preferred_duration

            # Check if requested time is available
            is_available = await check_calendar_availability(starts_at_utc, duration_preference)

            if not is_available:
                # Get alternative suggestions
                alternatives = await suggest_alternative_times(starts_at_utc, duration_preference, max_suggestions=2)

                if alternatives:
                    # Format alternatives for speech
                    alt_strings = []
                    for alt in alternatives:
                        alt_local = alt.astimezone(LOCAL_TZ)
                        if alt_local.date() == starts_at_utc.astimezone(LOCAL_TZ).date():
                            alt_strings.append(alt_local.strftime("%I:%M %p"))
                        else:
                            alt_strings.append(alt_local.strftime("%A at %I:%M %p"))

                    suggestion_text = " or ".join(alt_strings)
                    return _twiml(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>That time isn't available. How about {suggestion_text}?</Say>
{_gather_block("Please tell me which time works for you, or suggest a different time.")}
</Response>""")
                else:
                    # No alternatives found
                    return _twiml(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>That time isn't available. Let me check our schedule.</Say>
{_gather_block("What other day or time would work for you?")}
</Response>""")

        except Exception as e:
            logger.warning("[ask_time] Calendar availability check failed: %s", e)
            # Continue without calendar checking

        sess.data["starts_at_utc"] = starts_at_utc
        sess.step = "ask_duration"
        save_session(sess)  # Persist state change
        logger.info("[ask_time] time accepted, moving to ask_duration")
        logger.info("[session_debug] after ask_time step=%s data=%s", sess.step, sess.data)

        # Use keypad for duration selection for better UX
        duration_prompt = ("Perfect! How long would you like your appointment? "
                          "Press 1 for 30 minutes, 2 for 45 minutes, or 3 for 60 minutes. "
                          "Or just say the duration you prefer.")

        return _twiml(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
{_gather_block(duration_prompt, timeout=15, include_dtmf=True, dtmf_instructions="")}
</Response>""")

    if sess.step == "ask_duration":
        logger.info("[ask_duration] processing input: speech='%s' digits='%s'", speech, digits)

        # Get duration from extraction
        duration = extracted_info.get("duration", 30)

        # Validate duration
        if duration not in [30, 45, 60]:
            logger.warning("[ask_duration] invalid duration %s, defaulting to 30", duration)
            duration = 30

        sess.data["duration_min"] = duration
        sess.step = "confirm"
        save_session(sess)
        logger.info("[ask_duration] duration set to %d minutes, moving to confirm", duration)

        # Generate confirmation with all details
        name = sess.data.get("full_name", "Unknown")
        when_local = "Unknown"
        if sess.data.get("starts_at_utc"):
            when_local = sess.data["starts_at_utc"].astimezone(LOCAL_TZ).strftime("%A, %B %d at %I:%M %p")

        confirmation_text = (f"Perfect! I'll book a {duration}-minute appointment for {name} "
                           f"on {when_local}. Should I confirm this booking?")

        return _twiml(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
{_gather_block_confirmation(f"{confirmation_text} Please say Yes or No.")}
</Response>""")

    if sess.step == "confirm":
        ans = speech.lower()
        if any(k in ans for k in ["yes", "yeah", "yup", "confirm", "book", "sure"]):
            try:
                full_name = sess.data.get("full_name")
                mobile = sess.data.get("mobile")
                starts_at_utc = sess.data.get("starts_at_utc")

                # Validate all required data is present and valid
                if not (full_name and mobile and starts_at_utc):
                    missing = []
                    if not full_name: missing.append("full name")
                    if not mobile: missing.append("phone number")
                    if not starts_at_utc: missing.append("date and time")
                    sess.step = "ask_name" if not full_name else ("ask_mobile" if not mobile else "ask_time")
                    save_session(sess)
                    logger.warning("[confirm] missing data for call=%s: %s", CallSid, missing)
                    return _twiml(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
{_gather_block("I'm missing " + ", ".join(missing) + ". Let's try again.")}
</Response>""")

                # Additional validation: ensure datetime object is valid
                if not isinstance(starts_at_utc, datetime):
                    logger.warning("[confirm] invalid datetime object for call=%s: %s", CallSid, type(starts_at_utc))
                    sess.data.pop("starts_at_utc", None)
                    sess.step = "ask_time"
                    save_session(sess)
                    return _twiml(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
{_gather_block("I had trouble with that time. Could you please tell me the date and time again?")}
</Response>""")

                # Direct database booking (no LLM extraction needed)
                duration_min = int(sess.data.get("duration_min") or 30)
                notes = speech if sess.data.get("notes") is None else sess.data.get("notes")

                # Find or create user
                try:
                    user = await get_user_by_mobile(db, mobile)
                    if not user:
                        user = await create_user(db, UserCreate(full_name=full_name, mobile=mobile))
                        logger.info("[voice] User created: id=%s name=%s mobile=%s",
                                   user.id, user.full_name, _mask_phone(user.mobile))
                    else:
                        logger.info("[voice] User found: id=%s name=%s mobile=%s",
                                   user.id, user.full_name, _mask_phone(user.mobile))
                except Exception as e:
                    logger.exception("[voice] User creation/lookup failed for call=%s: %s", CallSid, e)
                    sess.data.pop("starts_at_utc", None)
                    sess.step = "ask_time"
                    save_session(sess)
                    return _twiml(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>I'm having trouble with your contact information. Let's try again.</Say>
{_gather_block("What date and time would you like for your appointment?")}
</Response>""")

                # Create appointment directly with our datetime object
                try:
                    appt = await create_appointment_unique(
                        db,
                        user_id=user.id,
                        starts_at_utc=starts_at_utc,
                        duration_min=duration_min,
                        notes=notes,
                    )
                    logger.info("[voice] Appointment created successfully: id=%s user=%s time=%s duration=%s",
                               appt.id, user.id, starts_at_utc, duration_min)

                    # Update caller profile with booking preferences
                    try:
                        from app.services.redis_session import create_or_update_profile, update_profile_appointment_info

                        # Create or update profile
                        profile = await create_or_update_profile(mobile, full_name)

                        # Update appointment preferences
                        appointment_time_str = starts_at_utc.astimezone(LOCAL_TZ).strftime("%A, %B %d at %I:%M %p")
                        await update_profile_appointment_info(mobile, duration_min, appointment_time_str)

                        logger.info("[voice] Updated caller profile for %s", _mask_phone(mobile))
                    except Exception as e:
                        logger.warning("[voice] Failed to update caller profile: %s", e)

                except ValueError as e:
                    # Time conflict - appointment already exists
                    logger.warning("[voice] Time conflict for call=%s: %s", CallSid, e)
                    sess.data.pop("starts_at_utc", None)
                    sess.step = "ask_time"
                    save_session(sess)
                    local = starts_at_utc.astimezone(LOCAL_TZ)
                    suggestion = local if not HAVE_BH else (next_opening(local) or local)
                    return _twiml(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>That time is not available.</Say>
{_gather_block(f"How about {suggestion.strftime('%A, %B %d at %I:%M %p')}? Or please say another time.")}
</Response>""")

                except Exception as e:
                    # Database or other errors
                    logger.exception("[voice] Database error for call=%s: %s", CallSid, e)
                    logger.error("[voice] Exception type: %s", type(e).__name__)
                    logger.error("[voice] Exception args: %s", getattr(e, 'args', 'No args'))
                    logger.error("[voice] Debug - starts_at_utc: type=%s value=%s repr=%s", type(starts_at_utc), starts_at_utc, repr(starts_at_utc))
                    logger.error("[voice] Debug - starts_at_utc timezone: %s", getattr(starts_at_utc, 'tzinfo', 'No tzinfo attr'))
                    logger.error("[voice] Debug - user_id=%s duration_min=%s", user.id if 'user' in locals() else 'None', duration_min)
                    logger.error("[voice] Debug - mobile=%s full_name=%s", _mask_phone(mobile) if 'mobile' in locals() else 'None', full_name if 'full_name' in locals() else 'None')
                    logger.error("[voice] Session data at error: %s", sess.data)
                    sess.data.pop("starts_at_utc", None)
                    sess.step = "ask_time"
                    save_session(sess)
                    return _twiml(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>I'm having trouble saving your appointment. Let's try a different time.</Say>
{_gather_block("What date and time would you like instead?")}
</Response>""")

                # Create Google Calendar event (non-blocking)
                calendar_event = None
                try:
                    from app.services.google_calendar import create_calendar_event
                    calendar_event = await create_calendar_event(
                        user_name=user.full_name,
                        user_mobile=user.mobile,
                        starts_at_utc=appt.starts_at,
                        duration_min=appt.duration_min,
                        notes=appt.notes
                    )
                    if calendar_event:
                        logger.info("[voice] Calendar event created: %s", calendar_event.get("event_id"))
                except Exception as e:
                    # Don't fail booking if calendar fails
                    logger.warning("[voice] Calendar integration failed: %s", e)

                # Success - appointment saved
                when = starts_at_utc.astimezone(LOCAL_TZ).strftime("%A, %B %d at %I:%M %p")
                reset_session(CallSid)
                return _twiml(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>Thank you. Your appointment is booked for {when}. We look forward to seeing you.</Say>
  <Hangup/>
</Response>""")

            except Exception as e:
                # Any other unexpected error during booking
                error_type = type(e).__name__
                error_msg = str(e)
                logger.exception("[confirm] Booking failed for call=%s, error_type=%s, error=%s, user_id=%s, starts_at=%s",
                               CallSid, error_type, error_msg, user.id if 'user' in locals() else None, starts_at_utc)
                sess.data.pop("starts_at_utc", None)
                sess.step = "ask_time"
                save_session(sess)
                return _twiml(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>I'm sorry, I'm having trouble saving your appointment. Let's try a different time.</Say>
{_gather_block("What date and time would you like for your appointment?")}
</Response>""")

        if any(k in ans for k in ["no", "nope", "cancel", "change"]):
            sess.step = "ask_time"
            return _twiml(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
{_gather_block("Okay—no problem. What date and time would you like instead?")}
</Response>""")

        # unclear → re-confirm without showing garbled speech
        summary = _summary(sess.data)
        # Only show speech if it's meaningful (more than 2 chars and contains actual words)
        speech_to_show = ""
        if cleaned_speech and len(cleaned_speech.strip()) > 2 and any(c.isalpha() for c in cleaned_speech):
            # Clean up the speech for display - remove very short words that might be noise
            words = cleaned_speech.split()
            meaningful_words = [w for w in words if len(w) > 1 or w.lower() in ['i', 'a']]
            if meaningful_words:
                speech_to_show = f"I heard: {' '.join(meaningful_words)}. "

        return _twiml(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
{_gather_block_confirmation(f"{speech_to_show}Should I book {summary}? Please say Yes or No.")}
</Response>""")

    # Fallback: reset to first step
    sess.step = "ask_name"
    return _twiml(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
{_gather_block("Let's start over. Could you please tell me your full name?")}
</Response>""")


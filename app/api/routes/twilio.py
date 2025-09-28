# app/api/routes/twilio.py
from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from fastapi import APIRouter, Depends, Form, Request, Response
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
from app.services.redis_session import get_session as get_call_session, reset_session, save_session
from app.services.llm import extract_appointment_fields
from app.services.booking import _parse_to_utc as parse_to_utc  # reuse future-only guard
from app.crud.user import get_user_by_mobile, create_user
from app.crud.appointment import create_appointment_unique
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


def _gather_block(prompt: str) -> str:
    """
    Canadian-optimized speech gathering with enhanced Twilio settings.
    Enhanced=true improves accuracy for Canadian English accents.
    """
    return f"""
  <Gather input="speech"
          language="en-CA"
          method="POST"
          action="/twilio/voice/collect"
          actionOnEmptyResult="true"
          speechTimeout="3"
          timeout="6"
          enhanced="true">
    <Say voice="alice" language="en-CA">{prompt}</Say>
  </Gather>
  <Say voice="alice" language="en-CA">Sorry, I didn't catch that.</Say>
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
async def voice_entry(CallSid: str = Form(default="")) -> Response:
    """Start the multi-turn wizard with a polite greeting."""
    # DON'T reset existing sessions - let them continue where they left off
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
{_gather_block("Hi there! Thanks for calling. I'll help you book your appointment today. What's your name?")}
</Response>"""
    logger.info("[voice] start call=%s", CallSid)
    return _twiml(twiml)


@router.post("/voice/collect")
async def voice_collect(
    request: Request,
    db: AsyncSession = Depends(get_session),
    SpeechResult: str = Form(default=""),
    From: str = Form(default=""),
    CallSid: str = Form(default=""),
) -> Response:
    """
    Multi-turn stepper:
      ask_name -> ask_mobile -> ask_time -> confirm -> book
    Also supports power-callers who say everything at once (we prefill via LLM).
    """
    speech = (SpeechResult or "").strip()
    from_num_masked = _mask_phone(From)
    sess = get_call_session(CallSid)

    logger.info(
        "[collect] call=%s step=%s from=%s speech=%s",
        CallSid, sess.step, from_num_masked, speech if speech else "<empty>",
    )

    # If nothing heard, gently reprompt the current step
    if not speech:
        polite = {
            "ask_name": "I’m sorry—I didn’t catch that. Could you please tell me your full name?",
            "ask_mobile": "I’m sorry—I didn’t catch that. Could you please say your phone number, digit by digit?",
            "ask_time": "I’m sorry—I didn’t catch that. Could you please say the exact date and time you’d like?",
            "confirm": "I’m sorry—I didn’t catch that. Should I book it? Please say Yes or No.",
        }[sess.step]
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
{_gather_block(polite)}
</Response>"""
        return _twiml(twiml)

    # Power-caller shortcut: try to extract information via LLM for any step
    extracted_info = {}
    if sess.step in ["ask_name", "ask_mobile", "ask_time"]:
        try:
            ex = await extract_appointment_fields(speech)
            exd = ex.model_dump()
            extracted_info = {
                "name": exd.get("full_name"),
                "mobile": exd.get("mobile"),
                "time": exd.get("starts_at")
            }
            logger.info("[llm_extract] step=%s speech='%s' extracted=%s", sess.step, speech, extracted_info)
        except Exception as e:
            logger.warning("[llm_extract] failed: %s", e)

    # --- Step machine ---
    logger.info("[session_debug] before step=%s data=%s", sess.step, sess.data)

    if sess.step == "ask_name":
        # CANADIAN OPTIMIZED: Try fast name extraction with LLM fallback
        async def llm_name_fallback(text):
            try:
                ex = await extract_appointment_fields(text)
                return ex.full_name
            except:
                return None

        extracted_name = await extract_canadian_name(speech, llm_name_fallback)

        # Also try LLM extracted name from earlier if direct extraction failed
        if not extracted_name and extracted_info.get("name"):
            extracted_name = await extract_canadian_name(extracted_info["name"])

        # Fallback to treating entire speech as name if extraction fails
        sess.data["full_name"] = extracted_name or " ".join(speech.split())
        logger.info("[ask_name] final name: '%s' (from speech: '%s')", sess.data["full_name"], speech)

        # Always proceed to ask_mobile step (no smart jumping)
        sess.step = "ask_mobile"
        save_session(sess)  # Persist state change
        logger.info("[session_debug] after ask_name step=%s data=%s", sess.step, sess.data)
        return _twiml(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
{_gather_block("Perfect! What's your phone number?")}
</Response>""")

    if sess.step == "ask_mobile":
        logger.info("[ask_mobile] processing speech: '%s'", speech)

        # CANADIAN OPTIMIZED: Try fast extraction with LLM fallback
        async def llm_phone_fallback(text):
            try:
                ex = await extract_appointment_fields(text)
                return ex.mobile
            except:
                return None

        norm = await extract_canadian_phone(speech, llm_phone_fallback)

        # Also try LLM extracted mobile from earlier if direct extraction failed
        if not norm and extracted_info.get("mobile"):
            norm = await extract_canadian_phone(extracted_info["mobile"])
            logger.info("[ask_mobile] used LLM extracted mobile: '%s' -> '%s'", extracted_info["mobile"], norm)

        if not norm:
            logger.warning("[ask_mobile] both fast and LLM extraction failed for: '%s'", speech)
            return _twiml(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
{_gather_block("Sorry, I didn't catch that. Can you say your phone number again?")}
</Response>""")

        logger.info("[ask_mobile] normalized '%s' -> '%s', advancing to ask_time", speech, norm)
        sess.data["mobile"] = norm
        sess.step = "ask_time"
        save_session(sess)  # Persist state change
        logger.info("[session_debug] after ask_mobile step=%s data=%s", sess.step, sess.data)
        return _twiml(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
{_gather_block("Great! When would you like your appointment? You can say something like 'next Tuesday at 2' or 'Friday morning'.")}
</Response>""")

    if sess.step == "ask_time":
        logger.info("[ask_time] processing speech: '%s'", speech)
        # CANADIAN OPTIMIZED: Try fast time extraction with LLM fallback
        async def llm_time_fallback(text):
            try:
                ex = await extract_appointment_fields(text)
                return ex.starts_at
            except:
                return None

        starts_at_utc = await extract_canadian_time(speech, llm_time_fallback)

        # Also try LLM extracted time from earlier if direct extraction failed
        if not starts_at_utc and extracted_info.get("time"):
            starts_at_utc = await extract_canadian_time(extracted_info["time"])
            logger.info("[ask_time] used LLM extracted time: '%s' -> %s", extracted_info["time"], starts_at_utc)

        if not starts_at_utc:
            return _twiml(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
{_gather_block("I didn't catch that. Could you please say a specific date and time, like next Tuesday at 2 PM?")}
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

        sess.data["starts_at_utc"] = starts_at_utc
        sess.step = "confirm"
        save_session(sess)  # Persist state change
        logger.info("[ask_time] time accepted, moving to confirm")
        logger.info("[session_debug] after ask_time step=%s data=%s", sess.step, sess.data)

        summary = _summary(sess.data)
        return _twiml(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
{_gather_block(f"I have {summary}. Should I book it? Please say Yes or No.")}
</Response>""")

    if sess.step == "confirm":
        ans = speech.lower()
        if any(k in ans for k in ["yes", "yeah", "yup", "confirm", "book", "sure"]):
            try:
                full_name = sess.data.get("full_name")
                mobile = sess.data.get("mobile")
                starts_at_utc = sess.data.get("starts_at_utc")
                if not (full_name and mobile and starts_at_utc):
                    missing = []
                    if not full_name: missing.append("full name")
                    if not mobile: missing.append("phone number")
                    if not starts_at_utc: missing.append("date and time")
                    sess.step = "ask_name" if not full_name else ("ask_mobile" if not mobile else "ask_time")
                    return _twiml(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
{_gather_block("I’m missing " + ", ".join(missing) + ". Let’s try again.")}
</Response>""")

                # Validate via Pydantic; create/fetch user; book appointment
                _ = UserCreate(full_name=full_name, mobile=mobile)
                user = await get_user_by_mobile(db, mobile)
                if not user:
                    user = await create_user(db, UserCreate(full_name=full_name, mobile=mobile))
                appt = await create_appointment_unique(
                    db,
                    user_id=user.id,
                    starts_at_utc=starts_at_utc,
                    duration_min=int(sess.data.get("duration_min") or 30),
                    notes=speech if sess.data.get("notes") is None else sess.data.get("notes"),
                )
                when = appt.starts_at.astimezone(LOCAL_TZ).strftime("%A, %B %d at %I:%M %p")
                reset_session(CallSid)
                return _twiml(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>Thank you. Your appointment is booked for {when}. We look forward to seeing you.</Say>
  <Hangup/>
</Response>""")
            except ValueError:
                # conflict or unique constraint → suggest another time
                local = (sess.data.get("starts_at_utc") or datetime.now(tz=ZoneInfo("UTC"))).astimezone(LOCAL_TZ)
                suggestion = local if not HAVE_BH else (next_opening(local) or local)
                sess.step = "ask_time"
                return _twiml(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>That time is not available.</Say>
{_gather_block(f"How about {suggestion.strftime('%A, %B %d at %I:%M %p')}? Or please say another time.")}
</Response>""")
            except Exception as e:
                logger.exception("[confirm] call=%s booking error: %r", CallSid, e)
                # Don't reset session - go back to ask_time instead of hanging up
                sess.step = "ask_time"
                return _twiml(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>I'm sorry, there was an issue with that booking. Let's try a different time.</Say>
{_gather_block("What date and time would you like instead?")}
</Response>""")

        if any(k in ans for k in ["no", "nope", "cancel", "change"]):
            sess.step = "ask_time"
            return _twiml(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
{_gather_block("Okay—no problem. What date and time would you like instead?")}
</Response>""")

        # unclear → re-confirm
        summary = _summary(sess.data)
        return _twiml(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
{_gather_block(f"I heard: {speech}. Should I book {summary}? Please say Yes or No.")}
</Response>""")

    # Fallback: reset to first step
    sess.step = "ask_name"
    return _twiml(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
{_gather_block("Let’s start over. Could you please tell me your full name?")}
</Response>""")

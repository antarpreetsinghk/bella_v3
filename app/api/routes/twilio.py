# app/api/routes/twilio.py
from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from fastapi import APIRouter, Depends, Form, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from zoneinfo import ZoneInfo

from app.db.session import get_session
from app.services.session import get_session as get_call_session, reset_session
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
    Reusable <Gather> that posts back to this collector.
    actionOnEmptyResult=true ensures Twilio still hits /collect if it heard nothing.
    """
    return f"""
  <Gather input="speech"
          language="en-CA"
          method="POST"
          action="/twilio/voice/collect"
          actionOnEmptyResult="true"
          speechTimeout="auto">
    <Say>{prompt}</Say>
  </Gather>
  <Say>Sorry, I didn’t catch that.</Say>
  <Redirect method="POST">/twilio/voice</Redirect>
"""


def _extract_digits(s: str) -> str:
    return re.sub(r"\D+", "", s or "")


def _normalize_phone_for_ca_us(raw: str) -> str | None:
    raw = (raw or "").strip()
    digits = _extract_digits(raw)
    if len(digits) == 10:
        return "+1" + digits
    if raw.startswith("+"):
        d = raw[1:]
        if d.isdigit() and 7 <= len(d) <= 15:
            return raw
    if digits.isdigit() and 7 <= len(digits) <= 15:
        return digits
    return None


def _summary(sess_data: dict) -> str:
    name = sess_data.get("full_name") or "Unknown"
    mobile = sess_data.get("mobile") or "Unknown"
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
    reset_session(CallSid)  # fresh start
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
{_gather_block("Hello and welcome. Thank you for calling. I’ll help you book your appointment. To start, could you please tell me your full name?")}
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

    # Power-caller shortcut: if we're at the first step and user says everything, try to prefill via LLM
    if sess.step == "ask_name":
        try:
            ex = await extract_appointment_fields(speech)
            exd = ex.model_dump()
            if exd.get("full_name"):
                sess.data["full_name"] = " ".join(exd["full_name"].split())
                sess.step = "ask_mobile"
            if exd.get("mobile"):
                norm = _normalize_phone_for_ca_us(exd["mobile"])
                if norm:
                    sess.data["mobile"] = norm
            if exd.get("starts_at"):
                try:
                    sess.data["starts_at_utc"] = parse_to_utc(exd["starts_at"])
                except Exception:
                    pass
        except Exception:
            pass

    # --- Step machine ---
    if sess.step == "ask_name":
        # treat any non-empty speech as a name
        sess.data["full_name"] = " ".join(speech.split())
        sess.step = "ask_mobile"
        return _twiml(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
{_gather_block("Thank you. Could you please say your phone number, digit by digit?")}
</Response>""")

    if sess.step == "ask_mobile":
        norm = _normalize_phone_for_ca_us(speech)
        if not norm:
            return _twiml(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
{_gather_block("Sorry, I didn’t get the number. Could you please say your phone number, digit by digit?")}
</Response>""")
        sess.data["mobile"] = norm
        sess.step = "ask_time"
        return _twiml(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
{_gather_block("Great, thank you. What date and time would you like? For example, Tuesday at 11 AM, or September 12 at 3 PM.")}
</Response>""")

    if sess.step == "ask_time":
        # Try LLM parsing for natural phrases; enforce future-only via parse_to_utc
        try:
            ex = await extract_appointment_fields(speech)
            exd = ex.model_dump()
            if not exd.get("starts_at"):
                raise ValueError("no time")
            starts_at_utc = parse_to_utc(exd["starts_at"])
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
        except Exception:
            return _twiml(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
{_gather_block("I couldn’t parse that time. Could you please say a specific date and time, like next Tuesday at 11 AM?")}
</Response>""")

        # Move to confirmation
        sess.step = "confirm"
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
                reset_session(CallSid)
                return _twiml(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>I’m sorry—something went wrong on our end. Please call again later.</Say>
  <Hangup/>
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

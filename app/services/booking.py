# app/services/booking.py
from __future__ import annotations

from datetime import datetime
from typing import Optional, Any

from sqlalchemy.ext.asyncio import AsyncSession
from zoneinfo import ZoneInfo
from pydantic import BaseModel, Field

from app.services.llm import extract_appointment_fields
from app.services.google_calendar import create_calendar_event
from app.crud.user import get_user_by_mobile, create_user
from app.crud.appointment import create_appointment_unique
from app.schemas.user import UserCreate

LOCAL_TZ = ZoneInfo("America/Edmonton")
UTC = ZoneInfo("UTC")


# ---------- Public contract returned to the route ----------

class BookResult(BaseModel):
    created: bool = Field(..., description="Whether an appointment was created")
    message_for_caller: str = Field(..., description="Plain sentence to speak back to caller")
    echo: dict = Field(default_factory=dict, description="Debug/extracted fields for client logs")


# ---------- Internal helpers ----------

def _jsonify(obj: Any) -> Any:
    """
    Make objects JSON-serializable for the echo payload:
    - datetime -> ISO string
    - dict/list -> walk recursively
    - ORM/other -> str()
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _jsonify(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_jsonify(v) for v in obj]
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    return str(obj)


def _parse_to_utc(s: str) -> datetime:
    """
    Accept ISO8601 with tz, or naive datetime treated as LOCAL_TZ.
    Mirrors logic in appointments route to avoid import cycles.
    """
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        raise ValueError("Invalid date/time. Please provide a specific date and time (e.g., 2025-09-10 10:00).")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=LOCAL_TZ)
    return dt.astimezone(UTC)


def _normalize_name_and_mobile(
    name: Optional[str],
    mobile: Optional[str],
) -> tuple[Optional[str], Optional[str], list[str], list[str]]:
    """
    Reuse Pydantic validators from UserCreate by instantiating it.
    Returns (clean_name, clean_mobile, missing_fields, errors)
    """
    missing: list[str] = []
    errors: list[str] = []

    clean_name = name
    clean_mobile = mobile

    # Validate/normalize via UserCreate validators when we have a mobile candidate.
    if clean_mobile is not None:
        try:
            tmp = UserCreate(full_name=(clean_name or "Unknown"), mobile=clean_mobile)
            clean_name = tmp.full_name
            clean_mobile = tmp.mobile
        except Exception:
            errors.append("mobile")
            clean_mobile = None

    if clean_mobile is None:
        missing.append("mobile")

    return clean_name, clean_mobile, missing, errors


def _compose_success_message(full_name: str, starts_at_utc: datetime, duration_min: int) -> str:
    local = starts_at_utc.astimezone(LOCAL_TZ)
    when = local.strftime("%A, %B %d at %I:%M %p")
    return f"Booked {duration_min}-minute appointment for {full_name} on {when}. See you then!"


def _compose_missing_message(missing: list[str]) -> str:
    if "mobile" in missing and "starts_at" in missing:
        return "I need your phone number and a specific date and time to book. Could you share both?"
    if "mobile" in missing:
        return "I need the phone number to confirm your booking. What's the best number to reach you?"
    if "starts_at" in missing:
        return "What exact date and time would you like for the appointment?"
    return "I’m missing some details. Could you repeat the phone number and the preferred date and time?"


# ---------- Core orchestration ----------

async def book_from_transcript(
    db: AsyncSession,
    *,
    transcript: str,
    from_number: Optional[str] = None,
    locale: str = "en-CA",
) -> BookResult:
    """
    One-shot booking orchestrator:
    1) Use LLM to extract fields
    2) Normalize/validate (name, phone, time)
    3) Upsert user and create appointment (unique)
    4) Return a friendly message and echo payload
    """
    # 1) Extract with GPT
    extracted = await extract_appointment_fields(transcript)
    ex = extracted.model_dump()

    # 2) Fallbacks
    mobile_candidate = ex.get("mobile") or from_number
    full_name_candidate = ex.get("full_name")
    duration_min = int(ex.get("duration_min") or 30)
    notes = ex.get("notes")

    # 3) Normalize name & phone
    clean_name, clean_mobile, missing_mobile, _mobile_errors = _normalize_name_and_mobile(
        full_name_candidate, mobile_candidate
    )

    # 4) Parse time to UTC
    starts_at_utc: Optional[datetime] = None
    missing_time: list[str] = []
    if ex.get("starts_at"):
        try:
            starts_at_utc = _parse_to_utc(ex["starts_at"])
        except Exception:
            missing_time.append("starts_at")
    else:
        missing_time.append("starts_at")

    # 5) Missing critical fields → no DB writes
    missing = list(set(missing_mobile + missing_time))
    if missing:
        msg = _compose_missing_message(missing)
        return BookResult(
            created=False,
            message_for_caller=msg,
            echo=_jsonify({
                "missing": missing,
                "extracted": ex,
                "normalized": {"full_name": clean_name, "mobile": clean_mobile, "starts_at_utc": None},
            }),
        )

    # 6) Find-or-create user
    user = await get_user_by_mobile(db, clean_mobile)  # type: ignore[arg-type]
    if not user:
        user = await create_user(db, UserCreate(full_name=(clean_name or "Unknown"), mobile=clean_mobile))  # type: ignore[arg-type]

    # Cache plain strings immediately to avoid async lazy-load later
    user_name = user.full_name
    user_mobile = user.mobile

    # 7) Attempt unique appointment insert
    try:
        appt = await create_appointment_unique(
            db,
            user_id=user.id,
            starts_at_utc=starts_at_utc,  # type: ignore[arg-type]
            duration_min=duration_min,
            notes=notes,
        )
    except ValueError as e:
        local = (starts_at_utc or datetime.now(tz=UTC)).astimezone(LOCAL_TZ)
        when = local.strftime("%A, %B %d at %I:%M %p")
        msg = (
            f"It looks like there's already an appointment for that time ({when}). "
            f"Would you like a different time on the same day or another day?"
        )
        # IMPORTANT: use cached strings (no ORM attribute access here)
        return BookResult(
            created=False,
            message_for_caller=msg,
            echo=_jsonify({
                "error": "time_conflict",
                "error_details": str(e),
                "requested_time": when,
                "extracted": ex,
                "normalized": {
                    "full_name": user_name,
                    "mobile": user_mobile,
                    "starts_at_utc": starts_at_utc,
                },
            }),
        )
    except Exception as e:
        # Database or other unexpected errors
        import logging
        logger = logging.getLogger(__name__)
        logger.exception("Unexpected error during appointment creation: %s", e)

        msg = "I'm having trouble saving your appointment right now. Please try again in a moment."
        return BookResult(
            created=False,
            message_for_caller=msg,
            echo=_jsonify({
                "error": "database_error",
                "error_details": str(e),
                "extracted": ex,
                "normalized": {
                    "full_name": user_name,
                    "mobile": user_mobile,
                    "starts_at_utc": starts_at_utc,
                },
            }),
        )

    # 8) Create Google Calendar event (non-blocking)
    calendar_event = None
    try:
        calendar_event = await create_calendar_event(
            user_name=user_name,
            user_mobile=user_mobile,
            starts_at_utc=appt.starts_at,
            duration_min=appt.duration_min,
            notes=appt.notes
        )
        if calendar_event:
            import logging
            logger = logging.getLogger(__name__)
            logger.info("Calendar event created for appointment %s: %s", appt.id, calendar_event.get('event_id'))
    except Exception as e:
        # Don't fail the booking if calendar integration fails
        import logging
        logger = logging.getLogger(__name__)
        logger.warning("Failed to create calendar event for appointment %s: %s", appt.id, e)

    # 9) Success response
    msg = _compose_success_message(user_name, appt.starts_at, appt.duration_min)
    echo_data = {
        "appointment_id": appt.id,
        "user_id": user.id,
        "normalized": {
            "full_name": user_name,
            "mobile": user_mobile,
            "starts_at_utc": appt.starts_at,
            "duration_min": appt.duration_min,
            "notes": appt.notes,
        },
        "extracted": ex,
    }

    # Include calendar event info if successfully created
    if calendar_event:
        echo_data["calendar_event"] = calendar_event

    return BookResult(
        created=True,
        message_for_caller=msg,
        echo=_jsonify(echo_data),
    )

# app/api/routes/assistant.py
from __future__ import annotations

import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.services.booking import book_from_transcript, BookResult
from app.schemas.assistant import BookRequest, BookResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.post("/book", response_model=BookResponse)
async def book_from_text(payload: BookRequest, db: AsyncSession = Depends(get_session)) -> BookResponse:
    """
    Webhook endpoint: given a raw transcript, try to book an appointment.
    Returns a BookResponse with caller-facing message and debug echo.
    """
    try:
        return await book_from_transcript(
            db,
            transcript=payload.transcript,
            from_number=payload.from_number,
            locale=payload.locale,
        )
    except Exception:
        logger.exception("/assistant/book failed")
        # Return a valid shape instead of a raw 500 so clients/Twilio don't break
        return BookResult(
            created=False,
            message_for_caller="Sorry, something went wrong. Please try again.",
            echo={"route": "assistant/book", "hint": "see server logs for traceback"},
        )

# app/schemas/assistant.py
from __future__ import annotations

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class BookRequest(BaseModel):
    """
    Incoming payload for /assistant/book
    Usually comes from Twilio or another telephony client.
    """
    transcript: str = Field(..., description="Caller speech transcript as plain text")
    call_sid: Optional[str] = Field(None, description="Unique call/session ID from provider")
    from_number: Optional[str] = Field(None, description="Caller phone number if available")
    locale: str = Field("en-CA", description="Locale code for parsing (default en-CA)")


class BookResponse(BaseModel):
    """
    Outgoing payload after attempting booking.
    """
    created: bool = Field(..., description="Whether an appointment was created")
    message_for_caller: str = Field(..., description="Plain sentence for caller (to play via TTS)")
    echo: Dict[str, Any] = Field(
        default_factory=dict,
        description="Debug payload: extracted fields, normalized values, etc."
    )

# app/services/session.py
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Any

TTL_MINUTES = 15  # session auto-expires

@dataclass
class CallSession:
    call_sid: str
    step: str = "ask_name"   # ask_name -> ask_mobile -> ask_time -> confirm
    data: Dict[str, Any] = field(default_factory=lambda: {"duration_min": 30})
    updated_at: datetime = field(default_factory=lambda: datetime.utcnow())

_sessions: Dict[str, CallSession] = {}

def get_session(call_sid: str) -> CallSession:
    """Get or create a session, and purge expired ones."""
    now = datetime.utcnow()
    expired = [k for k, s in _sessions.items() if now - s.updated_at > timedelta(minutes=TTL_MINUTES)]
    for k in expired:
        _sessions.pop(k, None)
    sess = _sessions.get(call_sid)
    if not sess:
        sess = CallSession(call_sid=call_sid)
        _sessions[call_sid] = sess
    sess.updated_at = now
    return sess

def reset_session(call_sid: str) -> None:
    _sessions.pop(call_sid, None)

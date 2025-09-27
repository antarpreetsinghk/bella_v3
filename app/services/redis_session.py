# app/services/redis_session.py
"""
Redis-based session storage for Twilio voice calls.
Replaces in-memory session storage to survive container restarts.
"""
from __future__ import annotations
import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import redis
import logging

logger = logging.getLogger(__name__)

TTL_MINUTES = 15  # session auto-expires

@dataclass
class CallSession:
    call_sid: str
    step: str = "ask_name"   # ask_name -> ask_mobile -> ask_time -> confirm
    data: Dict[str, Any] = field(default_factory=lambda: {"duration_min": 30})
    updated_at: datetime = field(default_factory=lambda: datetime.utcnow())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for Redis storage"""
        result = asdict(self)
        result["updated_at"] = self.updated_at.isoformat()
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CallSession":
        """Create from dict loaded from Redis"""
        if "updated_at" in data and isinstance(data["updated_at"], str):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        return cls(**data)

# Redis client singleton
_redis_client: Optional[redis.Redis] = None

def get_redis_client() -> redis.Redis:
    """Get or create Redis client"""
    global _redis_client
    if _redis_client is None:
        redis_url = os.getenv("REDIS_URL")
        if not redis_url:
            # Fallback to localhost for development
            redis_url = "redis://localhost:6379"
            logger.warning("REDIS_URL not set, using localhost fallback")

        try:
            # Parse URL to check if it's Upstash (requires TLS)
            is_upstash = "upstash.io" in redis_url

            _redis_client = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=10,
                socket_timeout=10,
                retry_on_timeout=True,
                ssl_cert_reqs=None if is_upstash else "required",
                ssl_check_hostname=False if is_upstash else True,
                ssl_ca_certs=None if is_upstash else None
            )
            # Test connection
            _redis_client.ping()
            logger.info("Redis connection established: %s", redis_url.split('@')[-1] if '@' in redis_url else redis_url)
        except Exception as e:
            logger.error("Redis connection failed: %s", e)
            # Fallback to in-memory for development/testing
            logger.warning("Falling back to in-memory session storage")
            return None

    return _redis_client

def get_session(call_sid: str) -> CallSession:
    """Get or create a session with Redis persistence"""
    redis_client = get_redis_client()

    if redis_client is None:
        # Fallback to in-memory storage
        return _get_session_memory(call_sid)

    try:
        # Try to get session from Redis
        session_key = f"call_session:{call_sid}"
        session_data = redis_client.get(session_key)

        if session_data:
            # Parse existing session
            data = json.loads(session_data)
            session = CallSession.from_dict(data)
            logger.debug("Loaded session from Redis: %s step=%s", call_sid[:8], session.step)
        else:
            # Create new session
            session = CallSession(call_sid=call_sid)
            logger.info("Created new session: %s", call_sid[:8])

        # Update timestamp and save back to Redis
        session.updated_at = datetime.utcnow()
        session_json = json.dumps(session.to_dict())
        redis_client.setex(session_key, TTL_MINUTES * 60, session_json)

        return session

    except Exception as e:
        logger.error("Redis session error: %s", e)
        # Fallback to in-memory
        return _get_session_memory(call_sid)

def save_session(session: CallSession) -> None:
    """Explicitly save session to Redis"""
    redis_client = get_redis_client()

    if redis_client is None:
        return  # In-memory fallback doesn't need explicit save

    try:
        session.updated_at = datetime.utcnow()
        session_key = f"call_session:{session.call_sid}"
        session_json = json.dumps(session.to_dict())
        redis_client.setex(session_key, TTL_MINUTES * 60, session_json)
        logger.debug("Saved session to Redis: %s step=%s", session.call_sid[:8], session.step)
    except Exception as e:
        logger.error("Failed to save session to Redis: %s", e)

def reset_session(call_sid: str) -> None:
    """Delete session from Redis"""
    redis_client = get_redis_client()

    if redis_client is None:
        _sessions_memory.pop(call_sid, None)
        return

    try:
        session_key = f"call_session:{call_sid}"
        redis_client.delete(session_key)
        logger.info("Reset session: %s", call_sid[:8])
    except Exception as e:
        logger.error("Failed to reset session: %s", e)

# Fallback in-memory storage for development
_sessions_memory: Dict[str, CallSession] = {}

def _get_session_memory(call_sid: str) -> CallSession:
    """Fallback in-memory session storage"""
    now = datetime.utcnow()
    # Clean expired sessions
    expired = [k for k, s in _sessions_memory.items()
               if now - s.updated_at > timedelta(minutes=TTL_MINUTES)]
    for k in expired:
        _sessions_memory.pop(k, None)

    session = _sessions_memory.get(call_sid)
    if not session:
        session = CallSession(call_sid=call_sid)
        _sessions_memory[call_sid] = session

    session.updated_at = now
    return session
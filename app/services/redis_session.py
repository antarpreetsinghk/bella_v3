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
class CallerProfile:
    """Caller profile for returning customers"""
    mobile: str
    full_name: str
    last_call_date: Optional[datetime] = None
    call_count: int = 0
    preferred_duration: int = 30  # minutes
    preferred_times: list = field(default_factory=list)  # ["morning", "afternoon", etc.]
    last_appointment_date: Optional[datetime] = None
    appointment_count: int = 0
    is_returning: bool = False

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "mobile": self.mobile,
            "full_name": self.full_name,
            "call_count": self.call_count,
            "preferred_duration": self.preferred_duration,
            "preferred_times": self.preferred_times,
            "appointment_count": self.appointment_count,
            "is_returning": self.is_returning
        }
        if self.last_call_date:
            result["last_call_date"] = self.last_call_date.isoformat()
        if self.last_appointment_date:
            result["last_appointment_date"] = self.last_appointment_date.isoformat()
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CallerProfile":
        if "last_call_date" in data and data["last_call_date"]:
            data["last_call_date"] = datetime.fromisoformat(data["last_call_date"])
        if "last_appointment_date" in data and data["last_appointment_date"]:
            data["last_appointment_date"] = datetime.fromisoformat(data["last_appointment_date"])
        return cls(**data)

@dataclass
class CallSession:
    call_sid: str
    step: str = "ask_name"   # ask_name -> ask_mobile -> ask_time -> confirm
    data: Dict[str, Any] = field(default_factory=lambda: {"duration_min": 30})
    updated_at: datetime = field(default_factory=lambda: datetime.utcnow())
    # Speech tracking for debugging and analysis
    last_raw_speech: Optional[str] = None      # Original Twilio speech
    last_cleaned_speech: Optional[str] = None  # LLM-cleaned speech
    speech_history: list = field(default_factory=list)  # Track speech cleaning over time
    # Caller profile for personalization
    caller_profile: Optional[CallerProfile] = None
    from_number: Optional[str] = None  # Caller ID from Twilio

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for Redis storage"""
        result = asdict(self)
        result["updated_at"] = self.updated_at.isoformat()

        # Handle datetime objects in data field
        if "data" in result and isinstance(result["data"], dict):
            for key, value in result["data"].items():
                if isinstance(value, datetime):
                    result["data"][key] = value.isoformat()

        # Handle caller profile safely (avoid mock objects in tests)
        if self.caller_profile:
            try:
                # Check if it's a mock object (for testing)
                if hasattr(self.caller_profile, '_mock_name'):
                    # Don't serialize mock objects, just skip them
                    result["caller_profile"] = None
                else:
                    result["caller_profile"] = self.caller_profile.to_dict()
            except Exception:
                # If serialization fails, skip the caller profile
                result["caller_profile"] = None

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CallSession":
        """Create from dict loaded from Redis"""
        if "updated_at" in data and isinstance(data["updated_at"], str):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])

        # Handle datetime objects in data field
        if "data" in data and isinstance(data["data"], dict):
            for key, value in data["data"].items():
                if isinstance(value, str) and "T" in value:
                    try:
                        # Try to parse any ISO datetime string (handles both +/- timezone offsets)
                        data["data"][key] = datetime.fromisoformat(value.replace("Z", "+00:00"))
                    except ValueError:
                        try:
                            # Fallback for other datetime formats
                            data["data"][key] = datetime.fromisoformat(value)
                        except ValueError:
                            pass  # Keep as string if not a valid datetime

        # Handle caller profile
        if "caller_profile" in data and data["caller_profile"]:
            data["caller_profile"] = CallerProfile.from_dict(data["caller_profile"])

        return cls(**data)

# Redis client singleton
_redis_client: Optional[redis.Redis] = None

def get_redis_client() -> redis.Redis:
    """Get or create Redis client with improved connection handling"""
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

            # Configure connection parameters with reduced timeouts
            connection_params = {
                "decode_responses": True,
                "socket_connect_timeout": 3,  # Reduced from 10s to 3s
                "socket_timeout": 2,          # Reduced from 10s to 2s
                "retry_on_timeout": True,
                "retry_on_error": [redis.ConnectionError, redis.TimeoutError],
                "health_check_interval": 30
            }

            # For Upstash, convert redis:// to rediss:// for SSL
            if is_upstash and redis_url.startswith("redis://"):
                redis_url = redis_url.replace("redis://", "rediss://", 1)
                logger.info("Converted Redis URL to SSL for Upstash")

            _redis_client = redis.from_url(redis_url, **connection_params)
            # Test connection with timeout protection
            try:
                _redis_client.ping()
                logger.info("Redis connection established: %s", redis_url.split('@')[-1] if '@' in redis_url else redis_url)
            except redis.TimeoutError:
                logger.warning("Redis ping timeout - using connection but with caution")
                # Continue with connection, will fallback on individual operation timeouts
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

# Caller Profile Management
PROFILE_TTL_DAYS = 365  # Keep profiles for 1 year

async def get_caller_profile(mobile: str) -> Optional[CallerProfile]:
    """Get caller profile by mobile number"""
    redis_client = get_redis_client()
    if redis_client is None:
        return None

    try:
        profile_key = f"caller_profile:{mobile}"
        profile_data = redis_client.get(profile_key)

        if profile_data:
            data = json.loads(profile_data)
            return CallerProfile.from_dict(data)
    except Exception as e:
        logger.error("Failed to get caller profile: %s", e)

    return None

async def save_caller_profile(profile: CallerProfile) -> None:
    """Save caller profile to Redis"""
    redis_client = get_redis_client()
    if redis_client is None:
        return

    try:
        profile_key = f"caller_profile:{profile.mobile}"
        profile_json = json.dumps(profile.to_dict())
        redis_client.setex(profile_key, PROFILE_TTL_DAYS * 24 * 60 * 60, profile_json)
        logger.debug("Saved caller profile: %s", profile.mobile)
    except Exception as e:
        logger.error("Failed to save caller profile: %s", e)

async def create_or_update_profile(mobile: str, full_name: str) -> CallerProfile:
    """Create new profile or update existing one"""
    profile = await get_caller_profile(mobile)
    now = datetime.utcnow()

    if profile:
        # Update existing profile
        profile.full_name = full_name  # Update name in case it changed
        profile.last_call_date = now
        profile.call_count += 1
        profile.is_returning = True
    else:
        # Create new profile
        profile = CallerProfile(
            mobile=mobile,
            full_name=full_name,
            last_call_date=now,
            call_count=1,
            is_returning=False
        )

    await save_caller_profile(profile)
    return profile

async def update_profile_appointment_info(mobile: str, duration_min: int, appointment_time: str) -> None:
    """Update profile with appointment preferences"""
    profile = await get_caller_profile(mobile)
    if not profile:
        return

    try:
        # Update preferred duration based on booking pattern
        if duration_min != 30:  # If not default
            profile.preferred_duration = duration_min

        # Extract time preference from appointment
        if "morning" in appointment_time.lower() or ("am" in appointment_time.lower() and "11" not in appointment_time):
            if "morning" not in profile.preferred_times:
                profile.preferred_times.append("morning")
        elif "afternoon" in appointment_time.lower() or "pm" in appointment_time.lower():
            if "afternoon" not in profile.preferred_times:
                profile.preferred_times.append("afternoon")

        # Update appointment tracking
        profile.last_appointment_date = datetime.utcnow()
        profile.appointment_count += 1

        await save_caller_profile(profile)
        logger.info("Updated profile preferences for %s", mobile)
    except Exception as e:
        logger.error("Failed to update profile appointment info: %s", e)

async def get_personalized_greeting(profile: CallerProfile) -> str:
    """Generate personalized greeting based on caller profile"""
    if not profile.is_returning:
        return f"Hi {profile.full_name.split()[0]}! Thanks for calling."

    greetings = []

    # Returning customer greeting
    first_name = profile.full_name.split()[0]
    greetings.append(f"Hi {first_name}! Welcome back.")

    # Add appointment history context
    if profile.appointment_count > 0:
        if profile.appointment_count == 1:
            greetings.append("I see you've booked with us before.")
        else:
            greetings.append(f"I see you've booked {profile.appointment_count} appointments with us.")

    # Suggest preferred duration if available
    if profile.preferred_duration != 30:
        greetings.append(f"Should I book your usual {profile.preferred_duration}-minute appointment?")
    else:
        greetings.append("Would you like to book another appointment?")

    return " ".join(greetings)

async def enhance_session_with_caller_id(session: CallSession, from_number: str) -> CallSession:
    """Enhance session with caller ID and profile information"""
    session.from_number = from_number

    # Clean and normalize phone number
    try:
        from app.services.simple_extraction import extract_phone_simple
        cleaned_phone = extract_phone_simple(from_number)

        if cleaned_phone:
            # Try to get existing caller profile
            profile = await get_caller_profile(cleaned_phone)
            if profile:
                session.caller_profile = profile
                # Pre-populate session data with known information
                session.data["mobile"] = cleaned_phone
                session.data["full_name"] = profile.full_name
                session.data["duration_min"] = profile.preferred_duration
                session.data["is_returning_customer"] = True

                # Skip name/phone collection for known customers
                if profile.is_returning:
                    session.step = "ask_time"

                logger.info("Enhanced session with returning customer profile: %s", cleaned_phone)
            else:
                # New customer - capture phone from caller ID
                session.data["mobile"] = cleaned_phone
                session.data["mobile_source"] = "caller_id"
                logger.info("Captured new caller ID: %s", cleaned_phone)
    except Exception as e:
        logger.error("Failed to enhance session with caller ID: %s", e)

    return session
#!/usr/bin/env python3
"""
Dashboard session management with Redis persistence.
Provides session state for the unified dashboard interface.
"""
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import redis.asyncio as redis
import logging
from dataclasses import dataclass, field, asdict

from app.core.config import settings

logger = logging.getLogger(__name__)

@dataclass
class DashboardSession:
    """Dashboard session data structure"""
    session_id: str
    user_id: Optional[str] = None
    active_tab: str = "status"  # status, analytics, system
    preferences: Dict[str, Any] = field(default_factory=dict)
    filters: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.utcnow())
    last_accessed: datetime = field(default_factory=lambda: datetime.utcnow())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for Redis storage"""
        result = asdict(self)
        result["created_at"] = self.created_at.isoformat()
        result["last_accessed"] = self.last_accessed.isoformat()
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DashboardSession":
        """Create from dict loaded from Redis"""
        if "created_at" in data and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if "last_accessed" in data and isinstance(data["last_accessed"], str):
            data["last_accessed"] = datetime.fromisoformat(data["last_accessed"])
        return cls(**data)

class DashboardSessionManager:
    """Async Redis-based session manager for dashboard"""

    def __init__(self):
        self._redis_client: Optional[redis.Redis] = None
        self.session_ttl = 86400  # 24 hours

    async def get_redis_client(self) -> Optional[redis.Redis]:
        """Get or create async Redis client with improved connection handling"""
        if self._redis_client is None:
            redis_url = settings.REDIS_URL
            if not redis_url:
                logger.warning("REDIS_URL not configured, using in-memory fallback")
                return None

            try:
                # Handle Upstash Redis (requires SSL)
                if "upstash.io" in redis_url and redis_url.startswith("redis://"):
                    redis_url = redis_url.replace("redis://", "rediss://", 1)
                    logger.info("Using SSL connection for Upstash Redis")

                # aioredis connection
                self._redis_client = await redis.from_url(
                    redis_url,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=3
                )

                # Test connection with timeout
                await self._redis_client.ping()
                logger.info("Dashboard Redis connection established successfully")

            except (redis.ConnectionError, ConnectionRefusedError) as e:
                logger.warning(f"Redis connection failed: {e}")
                logger.info("Falling back to in-memory session storage")
                return None
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}")
                logger.info("Falling back to in-memory session storage")
                return None

        return self._redis_client

    async def create_session(self, user_id: Optional[str] = None) -> DashboardSession:
        """Create a new dashboard session"""
        session_id = str(uuid.uuid4())
        session = DashboardSession(
            session_id=session_id,
            user_id=user_id
        )

        await self._save_session(session)
        logger.info(f"Created dashboard session: {session_id[:8]}")
        return session

    async def get_session(self, session_id: str) -> Optional[DashboardSession]:
        """Get session by ID"""
        redis_client = await self.get_redis_client()

        if redis_client is None:
            # Fallback to memory
            session = _memory_sessions.get(session_id)
            if session:
                session.last_accessed = datetime.utcnow()
            return session

        try:
            session_key = f"dashboard_session:{session_id}"
            session_data = await redis_client.get(session_key)

            if session_data:
                data = json.loads(session_data)
                session = DashboardSession.from_dict(data)
                session.last_accessed = datetime.utcnow()

                # Update last accessed time
                await self._save_session(session)
                return session

        except Exception as e:
            logger.error(f"Failed to get session from Redis: {e}")

        return None

    async def update_session(self, session_id: str, **updates) -> bool:
        """Update session with new data"""
        session = await self.get_session(session_id)
        if not session:
            return False

        # Update session attributes
        for key, value in updates.items():
            if hasattr(session, key):
                setattr(session, key, value)

        session.last_accessed = datetime.utcnow()
        await self._save_session(session)
        return True

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        redis_client = await self.get_redis_client()

        if redis_client is None:
            # Fallback to memory
            return _memory_sessions.pop(session_id, None) is not None

        try:
            session_key = f"dashboard_session:{session_id}"
            result = await redis_client.delete(session_key)
            logger.info(f"Deleted dashboard session: {session_id[:8]}")
            return result > 0
        except Exception as e:
            logger.error(f"Failed to delete session from Redis: {e}")
            return False

    async def _save_session(self, session: DashboardSession) -> None:
        """Save session to Redis or memory fallback"""
        redis_client = await self.get_redis_client()

        if redis_client is None:
            # Fallback to memory
            _memory_sessions[session.session_id] = session
            return

        try:
            session_key = f"dashboard_session:{session.session_id}"
            session_json = json.dumps(session.to_dict())
            await redis_client.setex(session_key, self.session_ttl, session_json)
            logger.debug(f"Saved dashboard session: {session.session_id[:8]}")
        except Exception as e:
            logger.error(f"Failed to save session to Redis: {e}")
            # Fallback to memory
            _memory_sessions[session.session_id] = session

    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions (memory fallback only)"""
        if not _memory_sessions:
            return 0

        now = datetime.utcnow()
        expired_threshold = now - timedelta(seconds=self.session_ttl)

        expired_sessions = [
            session_id for session_id, session in _memory_sessions.items()
            if session.last_accessed < expired_threshold
        ]

        for session_id in expired_sessions:
            del _memory_sessions[session_id]

        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired memory sessions")

        return len(expired_sessions)

    async def get_session_info(self) -> Dict[str, Any]:
        """Get information about session storage"""
        redis_client = await self.get_redis_client()

        info = {
            "storage_type": "redis" if redis_client else "memory",
            "session_ttl_hours": self.session_ttl / 3600,
        }

        if redis_client is None:
            info["memory_sessions_count"] = len(_memory_sessions)
        else:
            try:
                # Get Redis info
                redis_info = await redis_client.info()
                info["redis_connected"] = True
                info["redis_version"] = redis_info.get("redis_version", "unknown")
                info["redis_memory_usage"] = redis_info.get("used_memory_human", "unknown")
            except Exception as e:
                info["redis_connected"] = False
                info["redis_error"] = str(e)

        return info

# Global memory storage for fallback
_memory_sessions: Dict[str, DashboardSession] = {}

# Global session manager instance
dashboard_session_manager = DashboardSessionManager()
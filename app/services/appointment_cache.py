#!/usr/bin/env python3
"""
Intelligent caching service for common appointment patterns and responses.
Optimizes performance by caching frequently used appointment data and field extractions.
"""

import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import logging
from dataclasses import dataclass, asdict
import redis.asyncio as redis
import asyncio

from app.core.config import settings

logger = logging.getLogger(__name__)

@dataclass
class CachedExtraction:
    """Cached appointment field extraction result"""
    user_input: str
    extracted_fields: Dict[str, Any]
    confidence: float
    extracted_at: datetime
    usage_count: int = 1

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result["extracted_at"] = self.extracted_at.isoformat()
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CachedExtraction":
        if "extracted_at" in data and isinstance(data["extracted_at"], str):
            data["extracted_at"] = datetime.fromisoformat(data["extracted_at"])
        return cls(**data)

@dataclass
class CommonPattern:
    """Common appointment booking pattern"""
    pattern_text: str
    category: str  # "time", "service", "contact", "confirmation"
    response_template: str
    usage_frequency: int = 0
    last_used: datetime = None

class AppointmentCacheManager:
    """Manages caching for appointment booking optimization"""

    def __init__(self):
        self._redis_client: Optional[redis.Redis] = None
        self._pattern_cache: Dict[str, CommonPattern] = {}
        self._extraction_cache: Dict[str, CachedExtraction] = {}
        self.cache_ttl = 86400  # 24 hours
        self.pattern_ttl = 604800  # 7 days for patterns

    async def get_redis_client(self) -> Optional[redis.Redis]:
        """Get Redis client with connection pooling"""
        if self._redis_client is None:
            redis_url = settings.REDIS_URL
            if not redis_url:
                logger.info("REDIS_URL not configured, using in-memory fallback for appointment cache")
                return None

            try:
                self._redis_client = await redis.from_url(
                    redis_url,
                    decode_responses=True,
                    socket_connect_timeout=3,
                    socket_timeout=2,
                    retry_on_timeout=True
                )
                await self._redis_client.ping()
                logger.info("Appointment cache Redis connection established")
            except Exception as e:
                logger.warning(f"Appointment cache Redis connection failed: {e}")
                return None

        return self._redis_client

    def _generate_cache_key(self, user_input: str, context: str = "") -> str:
        """Generate consistent cache key for user input"""
        # Normalize input for consistent caching
        normalized = user_input.lower().strip()
        # Add context for better cache discrimination
        combined = f"{context}:{normalized}" if context else normalized
        # Create hash for consistent key length
        key_hash = hashlib.md5(combined.encode()).hexdigest()[:12]
        return f"appointment:extraction:{key_hash}"

    async def get_cached_extraction(
        self,
        user_input: str,
        context: str = ""
    ) -> Optional[CachedExtraction]:
        """Get cached appointment field extraction"""
        cache_key = self._generate_cache_key(user_input, context)

        # Try Redis first
        redis_client = await self.get_redis_client()
        if redis_client:
            try:
                cached_data = await asyncio.wait_for(
                    redis_client.get(cache_key),
                    timeout=0.1
                )
                if cached_data:
                    data = json.loads(cached_data)
                    extraction = CachedExtraction.from_dict(data)

                    # Update usage count
                    extraction.usage_count += 1
                    await self._update_cache_async(cache_key, extraction)

                    logger.info(f"Cache hit for extraction: {user_input[:50]}... (used {extraction.usage_count}x)")
                    return extraction

            except Exception as e:
                logger.debug(f"Redis cache miss for {user_input[:30]}...: {e}")

        # Fallback to memory cache
        if cache_key in self._extraction_cache:
            extraction = self._extraction_cache[cache_key]
            extraction.usage_count += 1
            logger.info(f"Memory cache hit for extraction: {user_input[:50]}...")
            return extraction

        return None

    async def cache_extraction(
        self,
        user_input: str,
        extracted_fields: Dict[str, Any],
        confidence: float,
        context: str = ""
    ) -> None:
        """Cache appointment field extraction result"""
        cache_key = self._generate_cache_key(user_input, context)
        extraction = CachedExtraction(
            user_input=user_input,
            extracted_fields=extracted_fields,
            confidence=confidence,
            extracted_at=datetime.utcnow()
        )

        # Store in Redis
        redis_client = await self.get_redis_client()
        if redis_client:
            try:
                await asyncio.wait_for(
                    redis_client.setex(
                        cache_key,
                        self.cache_ttl,
                        json.dumps(extraction.to_dict())
                    ),
                    timeout=0.5
                )
                logger.debug(f"Cached extraction for: {user_input[:50]}...")
            except Exception as e:
                logger.warning(f"Failed to cache extraction in Redis: {e}")

        # Store in memory fallback
        self._extraction_cache[cache_key] = extraction

        # Cleanup old memory entries to prevent memory leaks
        if len(self._extraction_cache) > 1000:
            await self._cleanup_memory_cache()

    async def _update_cache_async(self, cache_key: str, extraction: CachedExtraction) -> None:
        """Async update cache entry without blocking"""
        redis_client = await self.get_redis_client()
        if redis_client:
            try:
                await asyncio.wait_for(
                    redis_client.setex(
                        cache_key,
                        self.cache_ttl,
                        json.dumps(extraction.to_dict())
                    ),
                    timeout=0.2
                )
            except Exception as e:
                logger.debug(f"Failed to update cache: {e}")

    async def get_common_patterns(self, category: str = None) -> List[CommonPattern]:
        """Get common appointment patterns for faster responses"""
        patterns = []

        # Try Redis first
        redis_client = await self.get_redis_client()
        if redis_client:
            try:
                pattern_key = f"appointment:patterns:{category}" if category else "appointment:patterns:all"
                cached_patterns = await asyncio.wait_for(
                    redis_client.get(pattern_key),
                    timeout=0.1
                )
                if cached_patterns:
                    pattern_data = json.loads(cached_patterns)
                    patterns = [CommonPattern(**p) for p in pattern_data]
                    logger.debug(f"Retrieved {len(patterns)} patterns from cache")
                    return patterns
            except Exception as e:
                logger.debug(f"Failed to get patterns from Redis: {e}")

        # Return built-in common patterns as fallback
        return self._get_builtin_patterns(category)

    def _get_builtin_patterns(self, category: str = None) -> List[CommonPattern]:
        """Get built-in common appointment patterns"""
        all_patterns = [
            CommonPattern(
                pattern_text="tomorrow at 2pm",
                category="time",
                response_template="I'll book you for tomorrow at 2 PM. What's your phone number?",
                usage_frequency=50
            ),
            CommonPattern(
                pattern_text="next week monday morning",
                category="time",
                response_template="I'll book you for next Monday morning. What time works best?",
                usage_frequency=30
            ),
            CommonPattern(
                pattern_text="haircut",
                category="service",
                response_template="I'll book you for a haircut. What day and time work for you?",
                usage_frequency=40
            ),
            CommonPattern(
                pattern_text="manicure",
                category="service",
                response_template="I'll book you for a manicure. When would you like to come in?",
                usage_frequency=25
            ),
            CommonPattern(
                pattern_text="yes that works",
                category="confirmation",
                response_template="Perfect! Your appointment is confirmed. We'll see you then!",
                usage_frequency=60
            ),
            CommonPattern(
                pattern_text="cancel appointment",
                category="cancellation",
                response_template="I'll help you cancel your appointment. Can you provide your name or phone number?",
                usage_frequency=15
            )
        ]

        if category:
            return [p for p in all_patterns if p.category == category]
        return all_patterns

    async def find_similar_pattern(
        self,
        user_input: str,
        similarity_threshold: float = 0.7
    ) -> Optional[CommonPattern]:
        """Find similar pattern using fuzzy matching for quick responses"""
        patterns = await self.get_common_patterns()
        user_input_lower = user_input.lower().strip()

        best_match = None
        best_score = 0.0

        for pattern in patterns:
            # Simple token-based similarity
            pattern_tokens = set(pattern.pattern_text.lower().split())
            input_tokens = set(user_input_lower.split())

            if not pattern_tokens or not input_tokens:
                continue

            # Jaccard similarity
            intersection = len(pattern_tokens.intersection(input_tokens))
            union = len(pattern_tokens.union(input_tokens))
            similarity = intersection / union if union > 0 else 0.0

            if similarity > best_score and similarity >= similarity_threshold:
                best_score = similarity
                best_match = pattern

        if best_match:
            logger.info(f"Found similar pattern '{best_match.pattern_text}' for '{user_input}' (similarity: {best_score:.2f})")

        return best_match

    async def _cleanup_memory_cache(self) -> None:
        """Clean up old memory cache entries"""
        if len(self._extraction_cache) <= 500:
            return

        # Remove entries older than 1 hour
        cutoff_time = datetime.utcnow() - timedelta(hours=1)
        keys_to_remove = [
            key for key, extraction in self._extraction_cache.items()
            if extraction.extracted_at < cutoff_time
        ]

        for key in keys_to_remove:
            del self._extraction_cache[key]

        logger.info(f"Cleaned up {len(keys_to_remove)} old cache entries")

    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        redis_client = await self.get_redis_client()

        stats = {
            "memory_extractions": len(self._extraction_cache),
            "memory_patterns": len(self._pattern_cache),
            "cache_type": "redis" if redis_client else "memory"
        }

        if redis_client:
            try:
                info = await redis_client.info()
                stats.update({
                    "redis_connected": True,
                    "redis_memory_usage": info.get("used_memory_human", "unknown"),
                    "redis_keyspace_hits": info.get("keyspace_hits", 0),
                    "redis_keyspace_misses": info.get("keyspace_misses", 0)
                })
            except Exception as e:
                stats.update({
                    "redis_connected": False,
                    "redis_error": str(e)
                })

        return stats

# Global cache manager instance
appointment_cache_manager = AppointmentCacheManager()
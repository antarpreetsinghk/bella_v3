#!/usr/bin/env python3
"""
Circuit breaker pattern implementation for external service protection.
Provides automatic failover and recovery for critical services like OpenAI API.
"""

import asyncio
import time
import logging
from enum import Enum
from typing import Any, Callable, Optional, Dict, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Forward declaration for alerting integration
_alert_manager = None

def _get_alert_manager():
    """Get alert manager instance (lazy loading to avoid circular imports)"""
    global _alert_manager
    if _alert_manager is None:
        try:
            from app.services.alerting import alert_manager
            _alert_manager = alert_manager
        except ImportError:
            _alert_manager = None
    return _alert_manager

async def _create_circuit_alert(severity: str, component: str, message: str, details: Dict[str, Any]):
    """Create circuit breaker alert"""
    alert_mgr = _get_alert_manager()
    if alert_mgr:
        try:
            await alert_mgr.create_alert(
                component=component,
                severity=severity,
                message=message,
                details=details
            )
        except Exception as e:
            logger.warning(f"Failed to create circuit breaker alert: {e}")

class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Service failing, requests blocked
    HALF_OPEN = "half_open"  # Testing if service recovered

@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior"""
    failure_threshold: int = 5      # Failures before opening circuit
    recovery_timeout: int = 60      # Seconds before trying recovery
    expected_exception: type = Exception  # Exception type to monitor
    timeout: float = 30.0           # Request timeout
    half_open_max_calls: int = 3    # Max calls in half-open state

@dataclass
class CircuitBreakerStats:
    """Circuit breaker statistics"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    circuit_opened_count: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    current_failure_streak: int = 0

class CircuitBreaker:
    """Circuit breaker implementation for service protection"""

    def __init__(self,
                 name: str,
                 config: CircuitBreakerConfig,
                 fallback_func: Optional[Callable] = None):
        self.name = name
        self.config = config
        self.fallback_func = fallback_func

        self.state = CircuitState.CLOSED
        self.stats = CircuitBreakerStats()
        self.last_state_change = time.time()
        self.half_open_calls = 0

        logger.info(f"Circuit breaker '{name}' initialized in {self.state.value} state")

    def _should_attempt_reset(self) -> bool:
        """Check if circuit should attempt reset to half-open"""
        if self.state != CircuitState.OPEN:
            return False

        time_since_open = time.time() - self.last_state_change
        return time_since_open >= self.config.recovery_timeout

    def _reset_to_half_open(self):
        """Reset circuit to half-open state for testing"""
        self.state = CircuitState.HALF_OPEN
        self.last_state_change = time.time()
        self.half_open_calls = 0
        logger.info(f"Circuit '{self.name}' reset to HALF_OPEN state")

    def _trip_circuit(self):
        """Trip circuit to open state"""
        self.state = CircuitState.OPEN
        self.last_state_change = time.time()
        self.stats.circuit_opened_count += 1
        logger.warning(f"Circuit '{self.name}' tripped to OPEN state after {self.stats.current_failure_streak} failures")

        # Create alert for circuit breaker opening
        asyncio.create_task(_create_circuit_alert(
            severity="high",
            component=f"circuit_breaker_{self.name}",
            message=f"Circuit breaker '{self.name}' OPENED - service failing",
            details={
                "service": self.name,
                "failure_streak": self.stats.current_failure_streak,
                "total_failures": self.stats.failed_requests,
                "success_rate": self.stats.successful_requests / max(self.stats.total_requests, 1),
                "circuit_opened_count": self.stats.circuit_opened_count
            }
        ))

    def _close_circuit(self):
        """Close circuit back to normal operation"""
        self.state = CircuitState.CLOSED
        self.last_state_change = time.time()
        self.stats.current_failure_streak = 0
        logger.info(f"Circuit '{self.name}' closed - service recovered")

        # Create alert for circuit breaker recovery
        asyncio.create_task(_create_circuit_alert(
            severity="low",
            component=f"circuit_breaker_{self.name}",
            message=f"Circuit breaker '{self.name}' CLOSED - service recovered",
            details={
                "service": self.name,
                "total_requests": self.stats.total_requests,
                "success_rate": self.stats.successful_requests / max(self.stats.total_requests, 1),
                "circuit_opened_count": self.stats.circuit_opened_count
            }
        ))

    def _record_success(self):
        """Record successful request"""
        self.stats.total_requests += 1
        self.stats.successful_requests += 1
        self.stats.last_success_time = time.time()
        self.stats.current_failure_streak = 0

        # If half-open and enough successes, close circuit
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_calls += 1
            if self.half_open_calls >= self.config.half_open_max_calls:
                self._close_circuit()

    def _record_failure(self):
        """Record failed request"""
        self.stats.total_requests += 1
        self.stats.failed_requests += 1
        self.stats.last_failure_time = time.time()
        self.stats.current_failure_streak += 1

        # Check if should trip circuit
        if (self.state == CircuitState.CLOSED and
            self.stats.current_failure_streak >= self.config.failure_threshold):
            self._trip_circuit()
        elif self.state == CircuitState.HALF_OPEN:
            # If half-open test fails, go back to open
            self._trip_circuit()

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function through circuit breaker"""

        # Check if circuit should attempt reset
        if self._should_attempt_reset():
            self._reset_to_half_open()

        # Block requests if circuit is open
        if self.state == CircuitState.OPEN:
            if self.fallback_func:
                logger.info(f"Circuit '{self.name}' OPEN - using fallback")
                try:
                    return await self.fallback_func(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Fallback failed for '{self.name}': {e}")
                    raise CircuitBreakerException(f"Service unavailable and fallback failed: {e}")
            else:
                raise CircuitBreakerException(f"Service '{self.name}' is currently unavailable")

        # Limit calls in half-open state
        if (self.state == CircuitState.HALF_OPEN and
            self.half_open_calls >= self.config.half_open_max_calls):
            raise CircuitBreakerException(f"Service '{self.name}' is being tested for recovery")

        # Execute the function call
        try:
            # Add timeout protection
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.config.timeout
            )
            self._record_success()
            return result

        except self.config.expected_exception as e:
            self._record_failure()
            logger.warning(f"Circuit '{self.name}' recorded failure: {e}")
            raise
        except asyncio.TimeoutError:
            self._record_failure()
            logger.warning(f"Circuit '{self.name}' timeout after {self.config.timeout}s")
            raise CircuitBreakerException(f"Service '{self.name}' timed out")
        except Exception as e:
            # Unexpected exceptions are also considered failures
            self._record_failure()
            logger.error(f"Circuit '{self.name}' unexpected error: {e}")
            raise

    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics"""
        return {
            "name": self.name,
            "state": self.state.value,
            "total_requests": self.stats.total_requests,
            "successful_requests": self.stats.successful_requests,
            "failed_requests": self.stats.failed_requests,
            "success_rate": (
                self.stats.successful_requests / max(self.stats.total_requests, 1)
            ),
            "circuit_opened_count": self.stats.circuit_opened_count,
            "current_failure_streak": self.stats.current_failure_streak,
            "last_failure_time": self.stats.last_failure_time,
            "last_success_time": self.stats.last_success_time,
            "time_in_current_state": time.time() - self.last_state_change
        }

    def reset(self):
        """Manually reset circuit breaker"""
        self._close_circuit()
        self.stats = CircuitBreakerStats()
        logger.info(f"Circuit '{self.name}' manually reset")

class CircuitBreakerException(Exception):
    """Exception raised when circuit breaker blocks requests"""
    pass

class CircuitBreakerManager:
    """Manages multiple circuit breakers"""

    def __init__(self):
        self.breakers: Dict[str, CircuitBreaker] = {}

    def register_breaker(self,
                        name: str,
                        config: CircuitBreakerConfig,
                        fallback_func: Optional[Callable] = None) -> CircuitBreaker:
        """Register a new circuit breaker"""
        breaker = CircuitBreaker(name, config, fallback_func)
        self.breakers[name] = breaker
        return breaker

    def get_breaker(self, name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker by name"""
        return self.breakers.get(name)

    def get_all_stats(self) -> Dict[str, Any]:
        """Get statistics for all circuit breakers"""
        return {
            name: breaker.get_stats()
            for name, breaker in self.breakers.items()
        }

    def reset_all(self):
        """Reset all circuit breakers"""
        for breaker in self.breakers.values():
            breaker.reset()

# Global circuit breaker manager
circuit_manager = CircuitBreakerManager()

# Pre-configured fallback functions
async def openai_fallback(*args, **kwargs) -> str:
    """Fallback for OpenAI service failures"""
    logger.warning("OpenAI service unavailable - using fallback response")

    # Return a generic but helpful response
    return "I understand you'd like to make an appointment. Could you please tell me your name and phone number so I can help you manually?"

async def simple_text_fallback(*args, **kwargs) -> str:
    """Simple text fallback for text processing services"""
    return "I'm having trouble processing that right now. Could you please repeat that?"

# Initialize critical circuit breakers
def initialize_circuit_breakers():
    """Initialize circuit breakers for critical services"""

    # OpenAI API circuit breaker
    openai_config = CircuitBreakerConfig(
        failure_threshold=3,      # Trip after 3 failures
        recovery_timeout=30,      # Try recovery after 30s
        timeout=15.0,            # 15s timeout for OpenAI calls
        half_open_max_calls=2    # Test with 2 calls
    )

    circuit_manager.register_breaker(
        name="openai_api",
        config=openai_config,
        fallback_func=openai_fallback
    )

    # Twilio API circuit breaker
    twilio_config = CircuitBreakerConfig(
        failure_threshold=5,      # More tolerant for Twilio
        recovery_timeout=60,      # Longer recovery time
        timeout=10.0,            # 10s timeout
        half_open_max_calls=3
    )

    circuit_manager.register_breaker(
        name="twilio_api",
        config=twilio_config
    )

    # Database circuit breaker
    db_config = CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=20,      # Quick recovery for DB
        timeout=5.0,             # 5s timeout for DB
        half_open_max_calls=2
    )

    circuit_manager.register_breaker(
        name="database",
        config=db_config
    )

    logger.info("Circuit breakers initialized for critical services")

# Auto-initialize on module import
initialize_circuit_breakers()
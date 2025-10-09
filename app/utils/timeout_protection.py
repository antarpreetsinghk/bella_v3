# app/utils/timeout_protection.py
"""
Timeout protection utilities for call flow to prevent Twilio disconnections.
Ensures all processing completes within 3 seconds to maintain call quality.
"""
import asyncio
import logging
from typing import Optional, Any, Callable
from functools import wraps

logger = logging.getLogger(__name__)

class TimeoutError(Exception):
    """Custom timeout error for call flow processing."""
    pass

async def with_timeout(coro, timeout_seconds: float = 3.0, default_value: Any = None):
    """
    Execute a coroutine with a timeout, returning default_value if timeout occurs.

    Args:
        coro: The coroutine to execute
        timeout_seconds: Maximum time to wait (default 3.0 seconds)
        default_value: Value to return if timeout occurs

    Returns:
        Result of coroutine or default_value if timeout
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout_seconds)
    except asyncio.TimeoutError:
        logger.warning(f"Operation timed out after {timeout_seconds}s, using default value")
        return default_value
    except Exception as e:
        logger.error(f"Operation failed with error: {e}, using default value")
        return default_value

def with_sync_timeout(func, timeout_seconds: float = 3.0, default_value: Any = None):
    """
    Execute a synchronous function with a timeout.

    Args:
        func: The function to execute
        timeout_seconds: Maximum time to wait (default 3.0 seconds)
        default_value: Value to return if timeout occurs

    Returns:
        Result of function or default_value if timeout
    """
    try:
        # For sync functions, we'll use asyncio to run them with timeout
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(
            asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(None, func),
                timeout=timeout_seconds
            )
        )
    except asyncio.TimeoutError:
        logger.warning(f"Sync operation timed out after {timeout_seconds}s, using default value")
        return default_value
    except Exception as e:
        logger.error(f"Sync operation failed with error: {e}, using default value")
        return default_value

def timeout_protected(timeout_seconds: float = 3.0, default_value: Any = None):
    """
    Decorator to add timeout protection to functions.

    Usage:
        @timeout_protected(timeout_seconds=2.0, default_value="")
        def extract_name(speech):
            # Complex processing that might take too long
            return processed_name
    """
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await with_timeout(
                    func(*args, **kwargs),
                    timeout_seconds,
                    default_value
                )
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                return with_sync_timeout(
                    lambda: func(*args, **kwargs),
                    timeout_seconds,
                    default_value
                )
            return sync_wrapper
    return decorator

# Fast response helpers for voice calls
def quick_fallback_response(step: str, missing_info: str = "") -> str:
    """
    Generate quick fallback responses for when extraction fails.
    Optimized for Red Deer's diverse accent community.
    """
    quick_prompts = {
        "ask_name": "I didn't catch your name clearly. Could you spell it for me, or say it slowly?",
        "ask_mobile": "I missed your phone number. Could you say it digit by digit?",
        "ask_time": "I didn't get that time. Could you try saying it differently, like 'Monday at 2 PM'?",
        "confirm_name": "Could you say Yes or No? I want to make sure I have your name right.",
        "confirm": "Should I book this appointment? Please say Yes or No.",
        "general": f"I'm sorry, I didn't catch that. {missing_info}".strip()
    }

    return quick_prompts.get(step, quick_prompts["general"])

def is_processing_too_slow(start_time: float, max_seconds: float = 2.5) -> bool:
    """
    Check if processing is taking too long and we should return a quick response.

    Args:
        start_time: Time when processing started (from time.time())
        max_seconds: Maximum allowed processing time

    Returns:
        True if processing should be stopped and quick response returned
    """
    import time
    return (time.time() - start_time) > max_seconds

class CallFlowTimer:
    """
    Context manager to track call flow timing and automatically timeout.

    Usage:
        with CallFlowTimer("name_extraction") as timer:
            name = complex_extraction(speech)
            if timer.should_timeout():
                return quick_response()
    """

    def __init__(self, operation_name: str, max_seconds: float = 3.0):
        self.operation_name = operation_name
        self.max_seconds = max_seconds
        self.start_time = None

    def __enter__(self):
        import time
        self.start_time = time.time()
        logger.debug(f"Starting {self.operation_name} with {self.max_seconds}s timeout")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            import time
            duration = time.time() - self.start_time
            if duration > self.max_seconds:
                logger.warning(f"{self.operation_name} took {duration:.2f}s (>{self.max_seconds}s)")
            else:
                logger.debug(f"{self.operation_name} completed in {duration:.2f}s")

    def should_timeout(self) -> bool:
        """Check if operation should timeout and return quick response."""
        if not self.start_time:
            return False
        import time
        return (time.time() - self.start_time) > self.max_seconds

    def elapsed(self) -> float:
        """Get elapsed time since start."""
        if not self.start_time:
            return 0.0
        import time
        return time.time() - self.start_time
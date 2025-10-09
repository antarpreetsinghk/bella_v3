"""
Structured logging with correlation IDs and token-efficient design.
"""
import json
import logging
import uuid
from contextvars import ContextVar
from datetime import datetime
from typing import Any, Dict, Optional

try:
    import structlog
    STRUCTLOG_AVAILABLE = True
except ImportError:
    STRUCTLOG_AVAILABLE = False
    structlog = None

from fastapi import Request

# Request correlation context
request_id: ContextVar[str] = ContextVar('request_id', default="")
user_context: ContextVar[Dict[str, Any]] = ContextVar('user_context', default={})

class TokenEfficientProcessor:
    """Processor to keep logs concise and token-efficient."""

    def __init__(self, max_length: int = 200):
        self.max_length = max_length

    def __call__(self, logger, method_name, event_dict):
        # Truncate long messages
        if 'message' in event_dict:
            event_dict['message'] = str(event_dict['message'])[:self.max_length]

        # Truncate error messages
        if 'error' in event_dict:
            event_dict['error'] = str(event_dict['error'])[:self.max_length]

        # Remove verbose stack traces in production
        if 'exc_info' in event_dict and STRUCTLOG_AVAILABLE and not structlog.is_configured():
            del event_dict['exc_info']

        return event_dict

class CorrelationProcessor:
    """Add correlation ID and user context to all logs."""

    def __call__(self, logger, method_name, event_dict):
        # Add correlation ID
        correlation_id = request_id.get("")
        if correlation_id:
            event_dict['correlation_id'] = correlation_id

        # Add user context
        context = user_context.get({})
        if context:
            event_dict.update(context)

        return event_dict

def setup_logging(debug: bool = False, max_log_length: int = 200):
    """Configure structured logging for the application."""

    if not STRUCTLOG_AVAILABLE:
        # Fallback to standard logging for Lambda
        logging.basicConfig(
            level=logging.INFO if not debug else logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        )
        return

    processors = [
        structlog.stdlib.filter_by_level,
        CorrelationProcessor(),
        TokenEfficientProcessor(max_length=max_log_length),
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
    ]

    if debug:
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        context_class=structlog.threadlocal.wrap_dict(dict),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    logging.basicConfig(
        level=logging.INFO if not debug else logging.DEBUG,
        format="%(message)s",
    )

def get_logger(name: str = __name__):
    """Get a structured logger instance."""
    if STRUCTLOG_AVAILABLE:
        return structlog.get_logger(name)
    else:
        # Fallback to standard logging for Lambda
        return logging.getLogger(name)

def set_correlation_id(correlation_id: str):
    """Set correlation ID for current request context."""
    request_id.set(correlation_id)

def set_user_context(user_id: Optional[str] = None, endpoint: Optional[str] = None,
                    method: Optional[str] = None, **kwargs):
    """Set user context for current request."""
    context = {}
    if user_id:
        context['user_id'] = user_id
    if endpoint:
        context['endpoint'] = endpoint
    if method:
        context['method'] = method
    context.update(kwargs)
    user_context.set(context)

def clear_context():
    """Clear correlation ID and user context."""
    request_id.set("")
    user_context.set({})

class LoggingMiddleware:
    """FastAPI middleware for request logging with correlation IDs."""

    def __init__(self, log_requests: bool = False, log_responses: bool = False):
        self.log_requests = log_requests
        self.log_responses = log_responses
        self.logger = get_logger("middleware")

    async def __call__(self, request: Request, call_next):
        # Generate correlation ID
        correlation_id = str(uuid.uuid4())[:8]
        set_correlation_id(correlation_id)

        # Set request context
        set_user_context(
            endpoint=request.url.path,
            method=request.method,
            user_agent=request.headers.get("user-agent", "")[:50]
        )

        # Add to request state for downstream use
        request.state.correlation_id = correlation_id

        start_time = datetime.utcnow()

        # Log request (if enabled)
        if self.log_requests:
            self.logger.info(
                "request_start",
                path=request.url.path,
                method=request.method,
                query_params=dict(request.query_params)
            )

        try:
            response = await call_next(request)

            # Calculate response time
            duration = (datetime.utcnow() - start_time).total_seconds()

            # Log response (conditional)
            if self.log_responses or duration > 2.0 or response.status_code >= 400:
                self.logger.info(
                    "request_complete",
                    status_code=response.status_code,
                    duration=round(duration, 3),
                    slow=duration > 2.0
                )

            return response

        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            self.logger.error(
                "request_error",
                error=str(e),
                duration=round(duration, 3),
                error_type=type(e).__name__
            )
            raise
        finally:
            clear_context()
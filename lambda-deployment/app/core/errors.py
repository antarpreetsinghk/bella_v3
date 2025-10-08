"""
Error aggregation and smart alerting to reduce noise and save tokens.
"""
import hashlib
import time
from collections import defaultdict
from enum import Enum
from typing import Any, Dict, Optional

import structlog
from fastapi import HTTPException

logger = structlog.get_logger(__name__)

class ErrorSeverity(Enum):
    """Error severity levels for smart alerting."""
    LOW = "low"           # 404s, validation errors, expected failures
    MEDIUM = "medium"     # 500s, timeouts, recoverable errors
    HIGH = "high"         # Auth failures, data corruption, service degradation
    CRITICAL = "critical" # Service down, security breaches, data loss

class ErrorPattern:
    """Track error patterns to reduce duplicate logging."""

    def __init__(self, error_type: str, message: str, context: Dict[str, Any]):
        self.error_type = error_type
        self.message = message[:100]  # Truncate for fingerprinting
        self.context = {k: v for k, v in context.items() if k in ['endpoint', 'user_id', 'method']}
        self.fingerprint = self._generate_fingerprint()
        self.first_seen = time.time()
        self.last_seen = time.time()
        self.count = 1

    def _generate_fingerprint(self) -> str:
        """Generate unique fingerprint for error deduplication."""
        content = f"{self.error_type}:{self.message}:{self.context.get('endpoint', '')}"
        return hashlib.md5(content.encode(), usedforsecurity=False).hexdigest()[:8]  # Safe for error correlation

    def update(self):
        """Update last seen time and increment count."""
        self.last_seen = time.time()
        self.count += 1

class ErrorAggregator:
    """Aggregate and deduplicate errors for token-efficient logging."""

    def __init__(self, log_threshold: int = 10, time_window: int = 300):
        self.log_threshold = log_threshold  # Log every Nth occurrence
        self.time_window = time_window      # 5 minutes
        self.patterns: Dict[str, ErrorPattern] = {}
        self.severity_override = {
            "ValidationError": ErrorSeverity.LOW,
            "HTTPException": ErrorSeverity.LOW,
            "TimeoutError": ErrorSeverity.MEDIUM,
            "ConnectionError": ErrorSeverity.MEDIUM,
            "AuthenticationError": ErrorSeverity.HIGH,
            "PermissionError": ErrorSeverity.HIGH,
            "DatabaseError": ErrorSeverity.HIGH,
        }

    def _determine_severity(self, error: Exception, context: Dict[str, Any]) -> ErrorSeverity:
        """Determine error severity based on type and context."""
        error_type = type(error).__name__

        # Check override table
        if error_type in self.severity_override:
            return self.severity_override[error_type]

        # HTTPException severity based on status code
        if isinstance(error, HTTPException):
            if error.status_code < 500:
                return ErrorSeverity.LOW
            elif error.status_code < 503:
                return ErrorSeverity.MEDIUM
            else:
                return ErrorSeverity.HIGH

        # Default severity based on error type
        if "timeout" in str(error).lower():
            return ErrorSeverity.MEDIUM
        elif "auth" in str(error).lower() or "permission" in str(error).lower():
            return ErrorSeverity.HIGH
        else:
            return ErrorSeverity.MEDIUM

    def should_log(self, pattern: ErrorPattern, severity: ErrorSeverity) -> bool:
        """Determine if error should be logged based on frequency and severity."""
        # Always log high/critical severity
        if severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            return True

        # Log first occurrence
        if pattern.count == 1:
            return True

        # Log every Nth occurrence for medium severity
        if severity == ErrorSeverity.MEDIUM and pattern.count % self.log_threshold == 0:
            return True

        # Log every 50th occurrence for low severity
        if severity == ErrorSeverity.LOW and pattern.count % (self.log_threshold * 5) == 0:
            return True

        return False

    def log_error(self, error: Exception, context: Optional[Dict[str, Any]] = None,
                  severity: Optional[ErrorSeverity] = None) -> str:
        """Log error with deduplication and smart frequency control."""
        context = context or {}

        # Determine severity if not provided
        if severity is None:
            severity = self._determine_severity(error, context)

        # Create or update error pattern
        error_type = type(error).__name__
        message = str(error)

        pattern = ErrorPattern(error_type, message, context)
        fingerprint = pattern.fingerprint

        if fingerprint in self.patterns:
            self.patterns[fingerprint].update()
            pattern = self.patterns[fingerprint]
        else:
            self.patterns[fingerprint] = pattern

        # Decide whether to log
        if self.should_log(pattern, severity):
            logger.error(
                "aggregated_error",
                error_hash=fingerprint,
                error_type=error_type,
                message=message[:200],  # Truncate for token efficiency
                count=pattern.count,
                severity=severity.value,
                first_seen=pattern.first_seen,
                **context
            )

        return fingerprint

    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of recent errors for monitoring."""
        now = time.time()
        recent_errors = {
            fp: pattern for fp, pattern in self.patterns.items()
            if now - pattern.last_seen < self.time_window
        }

        summary = {
            "total_unique_errors": len(recent_errors),
            "total_error_count": sum(p.count for p in recent_errors.values()),
            "by_severity": defaultdict(int),
            "top_errors": []
        }

        # Group by severity
        for pattern in recent_errors.values():
            # Estimate severity for summary
            if pattern.count > 100:
                severity = "high"
            elif pattern.count > 10:
                severity = "medium"
            else:
                severity = "low"
            summary["by_severity"][severity] += pattern.count

        # Top errors by count
        top_errors = sorted(recent_errors.values(), key=lambda p: p.count, reverse=True)[:5]
        summary["top_errors"] = [
            {
                "fingerprint": p.fingerprint,
                "type": p.error_type,
                "message": p.message,
                "count": p.count
            }
            for p in top_errors
        ]

        return summary

    def cleanup_old_patterns(self):
        """Remove old error patterns to prevent memory leaks."""
        now = time.time()
        cutoff = now - (self.time_window * 10)  # Keep 10x time window

        old_patterns = [
            fp for fp, pattern in self.patterns.items()
            if pattern.last_seen < cutoff
        ]

        for fp in old_patterns:
            del self.patterns[fp]

        if old_patterns:
            logger.info("error_cleanup", removed_patterns=len(old_patterns))

# Global error aggregator instance
error_aggregator = ErrorAggregator()

def log_error(error: Exception, context: Optional[Dict[str, Any]] = None,
              severity: Optional[ErrorSeverity] = None) -> str:
    """Convenience function to log errors through the global aggregator."""
    return error_aggregator.log_error(error, context, severity)

def get_error_summary() -> Dict[str, Any]:
    """Get error summary from global aggregator."""
    return error_aggregator.get_error_summary()
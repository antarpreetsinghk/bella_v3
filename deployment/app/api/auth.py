#!/usr/bin/env python3
"""
Authentication utilities for Bella V3 API.
Provides API key authentication for protected endpoints.
"""

import os
from fastapi import HTTPException, Header, Query
from typing import Optional

# Get API key from environment
EXPECTED_API_KEY = os.getenv("BELLA_API_KEY", "")

def require_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    api_key: Optional[str] = Query(None, description="API key for authentication")
) -> str:
    """
    Require valid API key for access.

    Checks for API key in:
    1. X-API-Key header (preferred)
    2. api_key query parameter (fallback)

    Args:
        x_api_key: API key from X-API-Key header
        api_key: API key from query parameter

    Returns:
        str: Valid API key

    Raises:
        HTTPException: If API key is missing or invalid
    """
    # Try header first, then query parameter
    provided_key = x_api_key or api_key

    if not provided_key:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "API key required",
                "message": "Provide API key via 'X-API-Key' header or 'api_key' query parameter",
                "example_header": "X-API-Key: your-api-key-here",
                "example_query": "?api_key=your-api-key-here"
            }
        )

    if provided_key != EXPECTED_API_KEY:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "Invalid API key",
                "message": "The provided API key is not valid",
                "hint": "Check your BELLA_API_KEY environment variable"
            }
        )

    return provided_key

def get_api_key_info() -> dict:
    """Get information about API key configuration."""
    return {
        "api_key_configured": bool(EXPECTED_API_KEY and EXPECTED_API_KEY != ""),
        "api_key_source": "environment" if os.getenv("BELLA_API_KEY") else "default",
        "expected_length": len(EXPECTED_API_KEY) if EXPECTED_API_KEY else 0,
        "authentication_methods": [
            "X-API-Key header (recommended)",
            "api_key query parameter"
        ]
    }
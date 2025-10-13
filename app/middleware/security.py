# app/middleware/security.py
"""
Security headers middleware to protect against common web vulnerabilities.

Adds the following security headers to all responses:
- X-Frame-Options: Prevents clickjacking attacks
- X-Content-Type-Options: Prevents MIME type sniffing
- X-XSS-Protection: Enables browser XSS protection
- Referrer-Policy: Controls referrer information
- Strict-Transport-Security: Forces HTTPS connections (only on HTTPS)
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses."""

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process the request and add security headers to the response.

        Args:
            request: The incoming request
            call_next: The next middleware/endpoint in the chain

        Returns:
            Response with added security headers
        """
        response = await call_next(request)

        # Prevent clickjacking by not allowing the page to be framed
        response.headers["X-Frame-Options"] = "DENY"

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Enable XSS protection in older browsers
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Only add HSTS header if using HTTPS (prevents browser warnings on HTTP)
        if request.url.scheme == "https":
            # Force HTTPS for 1 year, including subdomains
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response

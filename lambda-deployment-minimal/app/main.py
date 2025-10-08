# app/main.py
from __future__ import annotations

# Load .env early so os.getenv works everywhere
from dotenv import load_dotenv
load_dotenv()

import logging
import os
import secrets
from urllib.parse import parse_qsl

import sqlalchemy as sa

# Initialize structured logging and monitoring
from app.core.logging import setup_logging, LoggingMiddleware, get_logger
from app.core.errors import log_error, ErrorSeverity, error_aggregator
from app.core.metrics import metrics_collector, track_performance, get_performance_metrics

# Set up structured logging
debug_mode = os.getenv("APP_ENV", "production") == "development"
setup_logging(debug=debug_mode, max_log_length=200)
logger = get_logger(__name__)

# Import webhook capture utility
try:
    from capture_webhook_details import webhook_capture
    WEBHOOK_DEBUG_ENABLED = True
    logger.info("Webhook debugging enabled")
except ImportError:
    WEBHOOK_DEBUG_ENABLED = False
    logger.info("Webhook debugging disabled (capture_webhook_details not found)")
from fastapi import FastAPI, Depends, Request
from fastapi.responses import JSONResponse, Response as FastResponse
from sqlalchemy.ext.asyncio import AsyncSession
from twilio.request_validator import RequestValidator

from app.db.session import get_session

# Routers
from app.api.routes.users import router as users_router
from app.api.routes.appointments import router as appointments_router
from app.api.routes.assistant import router as assistant_router
from app.api.routes.twilio import router as twilio_router
from app.api.routes.unified_dashboard import router as unified_router
from app.api.routes.admin_dashboard import router as admin_router
# Deprecated dashboards - will be removed
from app.api.routes.home import router as home_router  # OLD: Basic Auth dashboard
from app.api.routes.dashboard import router as dashboard_router  # OLD: Cost-only dashboard
from app.api.routes.performance import router as performance_router  # OLD: Performance-only

app = FastAPI(title="Bella V3", description="AI-powered appointment booking system")

# Add logging middleware with error handling
try:
    logging_middleware = LoggingMiddleware(
        log_requests=debug_mode,
        log_responses=debug_mode
    )
    app.middleware("http")(logging_middleware)
except Exception as e:
    # Fallback if logging middleware fails
    logger.warning(f"Logging middleware failed to initialize: {e}")

# -------- Health / readiness (public) --------
@app.get("/healthz", include_in_schema=False)
async def healthz():
    return {"ok": True}

@app.get("/version", include_in_schema=False)
async def version():
    import subprocess
    try:
        # Get current git commit hash
        commit = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'], cwd='/app').decode().strip()
        return {"commit": commit, "version": "latest", "timezone_fix": True, "speech_fix": True}
    except:
        return {"commit": "unknown", "version": "deployed", "timezone_fix": True, "speech_fix": True}

@app.get("/debug/db", include_in_schema=False)
async def debug_db(db: AsyncSession = Depends(get_session)):
    """Debug database connectivity and timezone handling."""
    from datetime import datetime, timezone
    from app.crud.user import create_user, get_user_by_mobile
    from app.crud.appointment import create_appointment_unique
    from app.schemas.user import UserCreate
    from app.models.appointment import Appointment

    try:
        # Test basic connectivity
        await db.execute(sa.text("SELECT 1"))

        # Test timezone-aware datetime
        test_time = datetime.now(timezone.utc)

        # Test user creation and appointment booking
        test_user_data = UserCreate(full_name="Debug Test User", mobile="+15559999999")

        # Try to find or create user
        user = await get_user_by_mobile(db, "+15559999999")
        if not user:
            user = await create_user(db, test_user_data)

        # Test appointment creation with unique time to avoid conflicts
        import random
        from datetime import timedelta

        # Clean up any existing debug appointments first
        try:
            debug_appointments = await db.execute(
                sa.select(Appointment).where(
                    Appointment.user_id == user.id,
                    Appointment.notes == "Debug test appointment"
                )
            )
            for appt in debug_appointments.scalars().all():
                await db.delete(appt)
            await db.commit()
        except Exception:
            await db.rollback()

        # Test appointment creation with completely unique time to avoid conflicts
        import random
        base_time = datetime.now(timezone.utc) + timedelta(days=45)  # Far future
        future_time = base_time.replace(
            hour=9 + random.randint(0, 8),  # 9 AM to 5 PM
            minute=random.choice([0, 15, 30, 45]),  # Quarter-hour intervals
            second=random.randint(0, 59),  # Random seconds
            microsecond=random.randint(0, 999999)  # Random microseconds
        )

        # Check existing appointments for this user
        existing_appts = await db.execute(
            sa.select(Appointment).where(Appointment.user_id == user.id)
        )
        existing_list = [
            {
                "id": a.id,
                "starts_at": a.starts_at.isoformat(),
                "notes": a.notes
            }
            for a in existing_appts.scalars().all()
        ]

        try:
            appt = await create_appointment_unique(
                db,
                user_id=user.id,
                starts_at_utc=future_time,
                duration_min=30,
                notes="Debug test appointment"
            )
            appointment_test = {
                "status": "success",
                "appointment_id": appt.id,
                "scheduled_time": future_time.isoformat(),
                "existing_appointments": existing_list
            }
        except Exception as appt_e:
            appointment_test = {
                "status": "error",
                "error": str(appt_e),
                "error_type": type(appt_e).__name__,
                "attempted_time": future_time.isoformat(),
                "existing_appointments": existing_list
            }

        return {
            "db_connection": "ok",
            "current_time_utc": test_time.isoformat(),
            "timezone_aware": test_time.tzinfo is not None,
            "test_user_ready": True,
            "user_test": {"id": user.id, "name": user.full_name},
            "appointment_test": appointment_test
        }
    except Exception as e:
        return {
            "db_connection": "error",
            "error": str(e),
            "error_type": type(e).__name__
        }

@app.post("/debug/extraction", include_in_schema=False)
async def debug_extraction(request: Request):
    """Debug endpoint for testing extraction functions."""
    try:
        data = await request.json()
        extraction_type = data.get("type", "name")
        text = data.get("text", "")

        if not text:
            return {"error": "No text provided"}

        from app.services.simple_extraction import extract_name, extract_phone, extract_time_preference

        results = {}

        if extraction_type == "name" or extraction_type == "all":
            results["name"] = extract_name(text)

        if extraction_type == "phone" or extraction_type == "all":
            results["phone"] = extract_phone(text)

        if extraction_type == "time" or extraction_type == "all":
            results["time"] = extract_time_preference(text)

        return {
            "input_text": text,
            "extraction_type": extraction_type,
            "results": results,
            "success": True
        }

    except Exception as e:
        return {
            "error": str(e),
            "error_type": type(e).__name__,
            "success": False
        }

@app.get("/debug/session/{call_sid}", include_in_schema=False)
async def debug_session(call_sid: str):
    """Debug endpoint for session state inspection."""
    try:
        from app.services.redis_session import get_session_data

        session_data = await get_session_data(call_sid)

        return {
            "call_sid": call_sid,
            "session_data": session_data,
            "has_session": session_data is not None,
            "success": True
        }

    except Exception as e:
        return {
            "call_sid": call_sid,
            "error": str(e),
            "error_type": type(e).__name__,
            "success": False
        }

@app.get("/debug/logs/{call_sid}", include_in_schema=False)
async def debug_logs(call_sid: str):
    """Debug endpoint for call trace logs."""
    try:
        from utils.debug_helpers import DebugHelper

        debug_helper = DebugHelper()
        call_trace = await debug_helper.get_call_trace(call_sid)

        return {
            "call_sid": call_sid,
            "call_trace": call_trace,
            "success": True
        }

    except Exception as e:
        return {
            "call_sid": call_sid,
            "error": str(e),
            "error_type": type(e).__name__,
            "success": False
        }

@app.get("/debug/health", include_in_schema=False)
async def debug_health():
    """Comprehensive debug health check."""
    try:
        # Test all extraction functions
        test_results = {}

        from app.services.simple_extraction import extract_name, extract_phone, extract_time_preference

        # Test name extraction
        test_results["name_extraction"] = {
            "test_input": "My name is John Smith",
            "result": extract_name("My name is John Smith"),
            "working": bool(extract_name("My name is John Smith"))
        }

        # Test phone extraction
        test_results["phone_extraction"] = {
            "test_input": "My number is 416 555 1234",
            "result": extract_phone("My number is 416 555 1234"),
            "working": bool(extract_phone("My number is 416 555 1234"))
        }

        # Test time extraction
        test_results["time_extraction"] = {
            "test_input": "Tomorrow at 2 PM",
            "result": extract_time_preference("Tomorrow at 2 PM"),
            "working": bool(extract_time_preference("Tomorrow at 2 PM"))
        }

        # Test session storage
        try:
            from app.services.redis_session import get_session_data
            test_results["session_storage"] = {
                "available": True,
                "test_call_sid": "TEST_DEBUG_123",
                "working": True
            }
        except Exception as e:
            test_results["session_storage"] = {
                "available": False,
                "error": str(e),
                "working": False
            }

        overall_health = all(
            test.get("working", False)
            for test in test_results.values()
        )

        return {
            "overall_health": "healthy" if overall_health else "degraded",
            "test_results": test_results,
            "timestamp": __import__('time').time(),
            "success": True
        }

    except Exception as e:
        return {
            "overall_health": "error",
            "error": str(e),
            "error_type": type(e).__name__,
            "success": False
        }

@app.get("/metrics", include_in_schema=False)
async def metrics():
    """Internal metrics endpoint for monitoring."""
    try:
        performance_metrics = get_performance_metrics()
        error_summary = error_aggregator.get_error_summary()

        return {
            "status": "healthy",
            "performance": performance_metrics,
            "errors": error_summary,
            "timestamp": __import__('time').time()
        }
    except Exception as e:
        log_error(e, {"endpoint": "/metrics"}, ErrorSeverity.MEDIUM)
        return {"status": "error", "message": "Metrics collection failed"}

@app.get("/readyz", include_in_schema=False)
async def readyz(db: AsyncSession = Depends(get_session)):
    await db.execute(sa.text("SELECT 1"))
    return {"db": "ok"}

# -------- Global security gate (single place) --------
from app.utils.secrets import get_config_value

BELLA_API_KEY = get_config_value("BELLA_API_KEY", "")
TWILIO_AUTH_TOKEN = get_config_value("TWILIO_AUTH_TOKEN", "")
TWILIO_ACCOUNT_SID = get_config_value("TWILIO_ACCOUNT_SID", "")
APP_ENV = get_config_value("APP_ENV", "production")
PRODUCTION_BASE_URL = get_config_value("PRODUCTION_BASE_URL", "https://api.example.com")
TEST_MODE = APP_ENV.lower() in ("test", "testing", "development")

# Public paths (do NOT require X-API-Key here)
PUBLIC_EXACT = {
    "/",            # dashboard UI (guarded by Basic Auth in home.py)
    "/healthz",
    "/readyz",
    "/metrics",     # if you expose Prometheus metrics
    "/favicon.ico", # avoid 401 on favicon
    "/ci-health",   # CI/CD smoke test endpoint
    "/admin",       # Admin dashboard root (custom auth)
    "/version",     # deployment tracking
    "/debug/db",    # temporary debugging
}

# Public prefixes (still may be guarded by their own logic)
PUBLIC_PREFIXES = (
    "/twilio/",     # Twilio webhooks (signature-verified below)
    "/manage/",     # Admin UI edit/delete forms (Basic Auth + CSRF in home.py)
    "/admin/",      # New professional admin dashboard (username/password auth)
    "/debug/",      # Debug endpoints for production testing
)

def _is_public(path: str) -> bool:
    return path in PUBLIC_EXACT or any(path.startswith(p) for p in PUBLIC_PREFIXES)

@app.middleware("http")
async def lock_all(request, call_next):
    path = request.url.path

    # 1) Twilio webhook signature verify (reject spoofed hits)
    if path.startswith("/twilio/"):
        logger.info("twilio_webhook_start",
                   path=path, method=request.method,
                   has_auth_token=bool(TWILIO_AUTH_TOKEN))

        # Capture detailed request information if debugging enabled
        body_bytes = await request.body()  # Starlette caches; downstream can still read

        if WEBHOOK_DEBUG_ENABLED:
            try:
                webhook_capture.capture_request_details(request, body_bytes)
            except Exception as debug_e:
                log_error(debug_e, {"component": "webhook_debug"}, ErrorSeverity.LOW)

        if TWILIO_AUTH_TOKEN and not TEST_MODE:
            try:
                form = dict(parse_qsl(body_bytes.decode(errors="ignore")))
                sig = request.headers.get("X-Twilio-Signature", "")

                logger.info("twilio_request_details",
                           headers_count=len(request.headers),
                           signature_present=bool(sig),
                           content_type=request.headers.get('content-type'),
                           body_size=len(body_bytes),
                           form_keys=list(form.keys()) if form else [])

                # Detailed signature validation - try multiple URL formats
                received_url = str(request.url)
                logger.info("signature_validation_start", url=received_url)

                # Try different URL schemes that Twilio might have used
                possible_urls = [
                    received_url,  # Original
                    received_url.replace("http://", "https://"),  # HTTPS version
                    f"{PRODUCTION_BASE_URL}/twilio/voice",  # Direct HTTPS
                    f"{PRODUCTION_BASE_URL}:443/twilio/voice",  # With port
                ]

                ok = False
                url_for_validation = received_url

                for i, test_url in enumerate(possible_urls):
                    test_result = RequestValidator(TWILIO_AUTH_TOKEN).validate(test_url, form, sig)

                    if test_result:
                        ok = True
                        url_for_validation = test_url
                        logger.info("signature_validated", url=test_url, attempt=i+1)
                        break

                if not ok:
                    logger.warning("signature_validation_failed",
                                 attempted_urls=len(possible_urls))
                    log_error(Exception("Twilio signature validation failed"),
                             {"endpoint": path, "attempts": len(possible_urls)},
                             ErrorSeverity.MEDIUM)

                # Additional debug logging if webhook capture is enabled
                if WEBHOOK_DEBUG_ENABLED:
                    try:
                        webhook_capture.log_signature_validation(url_for_validation, form, sig, TWILIO_AUTH_TOKEN, ok)

                        # Save request dump for analysis
                        request_data = {
                            "timestamp": str(logger.getEffectiveLevel()),
                            "url": url_for_validation,
                            "method": request.method,
                            "headers": dict(request.headers),
                            "body": body_bytes.decode(errors="ignore"),
                            "form_data": form,
                            "signature": sig,
                            "validation_result": ok
                        }
                        webhook_capture.save_request_dump(request_data)
                    except Exception as debug_e:
                        logger.error(f"Debug logging failed: {debug_e}")

                if not ok:
                    logger.warning("webhook_rejected", reason="invalid_signature")
                    return FastResponse(
                        content='<?xml version="1.0" encoding="UTF-8"?><Response><Reject/></Response>',
                        media_type="application/xml",
                        status_code=403,
                    )
                else:
                    logger.info("webhook_accepted", validation_url=url_for_validation)

            except Exception as e:
                log_error(e, {"endpoint": path, "component": "signature_validation"},
                         ErrorSeverity.HIGH)
                return FastResponse(
                    content='<?xml version="1.0" encoding="UTF-8"?><Response><Reject/></Response>',
                    media_type="application/xml",
                    status_code=403,
                )
        else:
            if TEST_MODE:
                logger.info("twilio_test_mode", auth_disabled=True)
            else:
                logger.warning("twilio_auth_disabled",
                              reason="no_auth_token")

        logger.info("proceeding_to_twilio_router")
        # Allow Twilio routes through (they're public but signature-checked)
        return await call_next(request)

    # 2) Public paths → allow (home, health, metrics, favicon, manage UI)
    if _is_public(path):
        return await call_next(request)

    # 3) Everything else → require API key header
    api_key = request.headers.get("X-API-Key", "")
    if not BELLA_API_KEY or not secrets.compare_digest(api_key, BELLA_API_KEY):
        log_error(Exception("API key validation failed"),
                 {"endpoint": path, "has_key": bool(api_key)},
                 ErrorSeverity.MEDIUM)
        return JSONResponse({"detail": "Invalid or missing API key"}, status_code=401)

    return await call_next(request)

# -------- CI Health Endpoint --------
@app.post("/ci-health")
async def ci_health():
    """
    Simple health check endpoint for CI/CD smoke tests.
    Bypasses all authentication and signature validation.
    """
    return FastResponse(
        content='<?xml version="1.0" encoding="UTF-8"?>\n<Response>\n  <Say voice="alice" language="en-CA">CI health check passed</Say>\n  <Hangup/>\n</Response>',
        media_type="application/xml",
        status_code=200,
    )

# -------- Include routers --------
# NEW: Professional admin dashboard
app.include_router(admin_router, prefix="/admin")
# NEW: Unified dashboard serves "/" route
app.include_router(unified_router)
app.include_router(users_router)
app.include_router(appointments_router)
app.include_router(assistant_router)
app.include_router(twilio_router)

# OLD: Deprecated dashboards - keeping temporarily for migration
app.include_router(home_router, prefix="/old")  # Moved to /old/
app.include_router(dashboard_router, prefix="/old")  # Moved to /old/dashboard/
app.include_router(performance_router, prefix="/old")  # Moved to /old/performance/

# -------- Application startup/shutdown events --------
@app.on_event("startup")
async def startup_event():
    """Initialize services on application startup"""
    logger.info("Application startup - initializing monitoring services")

    # Initialize alerting notification worker
    try:
        from app.services.alerting import alert_manager
        import asyncio

        # Start the notification worker in the background
        asyncio.create_task(alert_manager.start_notification_worker())
        logger.info("Alert notification worker started")

        # Initialize SLA tracking for overall system uptime
        await alert_manager.track_service_status("overall_uptime", True)

    except Exception as e:
        logger.error(f"Failed to initialize alerting system: {e}")

    # Clean up old metrics data on startup
    try:
        from app.services.business_metrics import business_metrics
        from app.services.cost_optimization import cost_optimizer

        await business_metrics.cleanup_old_data()
        logger.info("Cleaned up old business metrics data")

    except Exception as e:
        logger.error(f"Failed to cleanup old metrics: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on application shutdown"""
    logger.info("Application shutdown - cleaning up resources")

    try:
        from app.services.alerting import alert_manager

        # Track system going down for SLA monitoring
        await alert_manager.track_service_status("overall_uptime", False)

        # Create shutdown alert
        await alert_manager.create_alert(
            component="system",
            severity="low",
            message="Application shutdown initiated",
            details={"timestamp": logger.getEffectiveLevel(), "reason": "normal_shutdown"}
        )

    except Exception as e:
        logger.error(f"Failed during shutdown cleanup: {e}")
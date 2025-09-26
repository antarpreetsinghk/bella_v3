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

# Set up enhanced logger for debugging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import webhook capture utility
try:
    from capture_webhook_details import webhook_capture
    WEBHOOK_DEBUG_ENABLED = True
    logger.info("Webhook debugging enabled")
except ImportError:
    WEBHOOK_DEBUG_ENABLED = False
    logger.info("Webhook debugging disabled (capture_webhook_details not found)")
from fastapi import FastAPI, Depends
from fastapi.responses import JSONResponse, Response as FastResponse
from sqlalchemy.ext.asyncio import AsyncSession
from twilio.request_validator import RequestValidator

from app.db.session import get_session

# Routers
from app.api.routes.users import router as users_router
from app.api.routes.appointments import router as appointments_router
from app.api.routes.assistant import router as assistant_router
from app.api.routes.twilio import router as twilio_router
from app.api.routes.home import router as home_router  # dashboard (Basic Auth + CSRF live there)

app = FastAPI()

# -------- Health / readiness (public) --------
@app.get("/healthz", include_in_schema=False)
async def healthz():
    return {"ok": True}

@app.get("/readyz", include_in_schema=False)
async def readyz(db: AsyncSession = Depends(get_session)):
    await db.execute(sa.text("SELECT 1"))
    return {"db": "ok"}

# -------- Global security gate (single place) --------
BELLA_API_KEY = os.getenv("BELLA_API_KEY", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")

# Public paths (do NOT require X-API-Key here)
PUBLIC_EXACT = {
    "/",            # dashboard UI (guarded by Basic Auth in home.py)
    "/healthz",
    "/readyz",
    "/metrics",     # if you expose Prometheus metrics
    "/favicon.ico", # avoid 401 on favicon
}

# Public prefixes (still may be guarded by their own logic)
PUBLIC_PREFIXES = (
    "/twilio/",     # Twilio webhooks (signature-verified below)
    "/manage/",     # Admin UI edit/delete forms (Basic Auth + CSRF in home.py)
)

def _is_public(path: str) -> bool:
    return path in PUBLIC_EXACT or any(path.startswith(p) for p in PUBLIC_PREFIXES)

@app.middleware("http")
async def lock_all(request, call_next):
    path = request.url.path

    # 1) Twilio webhook signature verify (reject spoofed hits)
    if path.startswith("/twilio/"):
        logger.info(f"=== TWILIO WEBHOOK REQUEST ===")
        logger.info(f"Path: {path}")
        logger.info(f"Full URL: {str(request.url)}")
        logger.info(f"Method: {request.method}")
        logger.info(f"TWILIO_AUTH_TOKEN present: {bool(TWILIO_AUTH_TOKEN)}")

        # Capture detailed request information if debugging enabled
        body_bytes = await request.body()  # Starlette caches; downstream can still read

        if WEBHOOK_DEBUG_ENABLED:
            try:
                webhook_capture.capture_request_details(request, body_bytes)
            except Exception as debug_e:
                logger.error(f"Debug capture failed: {debug_e}")

        if TWILIO_AUTH_TOKEN:
            try:
                form = dict(parse_qsl(body_bytes.decode(errors="ignore")))
                sig = request.headers.get("X-Twilio-Signature", "")

                logger.info(f"Request headers count: {len(request.headers)}")
                logger.info(f"X-Twilio-Signature: {sig}")
                logger.info(f"Content-Type: {request.headers.get('content-type', 'NOT_SET')}")
                logger.info(f"User-Agent: {request.headers.get('user-agent', 'NOT_SET')}")
                logger.info(f"Body size: {len(body_bytes)} bytes")
                logger.info(f"Form data: {form}")

                # Detailed signature validation
                url_for_validation = str(request.url)
                logger.info(f"URL for validation: {url_for_validation}")

                ok = RequestValidator(TWILIO_AUTH_TOKEN).validate(url_for_validation, form, sig)
                logger.info(f"Signature validation result: {ok}")

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
                    logger.warning("=== SIGNATURE VALIDATION FAILED ===")
                    logger.warning("Rejecting webhook call due to invalid signature")
                    return FastResponse(
                        content='<?xml version="1.0" encoding="UTF-8"?><Response><Reject/></Response>',
                        media_type="application/xml",
                        status_code=403,
                    )
                else:
                    logger.info("=== SIGNATURE VALIDATION PASSED ===")

            except Exception as e:
                logger.error(f"=== SIGNATURE VALIDATION EXCEPTION ===")
                logger.error(f"Exception: {str(e)}")
                logger.error(f"Exception type: {type(e).__name__}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                return FastResponse(
                    content='<?xml version="1.0" encoding="UTF-8"?><Response><Reject/></Response>',
                    media_type="application/xml",
                    status_code=403,
                )
        else:
            logger.warning("No TWILIO_AUTH_TOKEN configured - allowing request through")

        logger.info("=== PROCEEDING TO TWILIO ROUTER ===")
        # Allow Twilio routes through (they're public but signature-checked)
        return await call_next(request)

    # 2) Public paths → allow (home, health, metrics, favicon, manage UI)
    if _is_public(path):
        return await call_next(request)

    # 3) Everything else → require API key header
    api_key = request.headers.get("X-API-Key", "")
    if not BELLA_API_KEY or not secrets.compare_digest(api_key, BELLA_API_KEY):
        return JSONResponse({"detail": "Invalid or missing API key"}, status_code=401)

    return await call_next(request)

# -------- Include routers --------
# Put home first so "/" is served by it
app.include_router(home_router)
app.include_router(users_router)
app.include_router(appointments_router)
app.include_router(assistant_router)
app.include_router(twilio_router)
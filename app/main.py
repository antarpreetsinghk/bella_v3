# app/main.py
from __future__ import annotations

# Load .env early so os.getenv works everywhere
from dotenv import load_dotenv
load_dotenv()

import os
import secrets
from urllib.parse import parse_qsl

import sqlalchemy as sa
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
        logger.info(f"Twilio webhook request to: {path}")
        logger.info(f"TWILIO_AUTH_TOKEN present: {bool(TWILIO_AUTH_TOKEN)}")

        if TWILIO_AUTH_TOKEN:
            try:
                body_bytes = await request.body()  # Starlette caches; downstream can still read
                form = dict(parse_qsl(body_bytes.decode(errors="ignore")))
                sig = request.headers.get("X-Twilio-Signature", "")

                logger.info(f"X-Twilio-Signature present: {bool(sig)}")
                logger.info(f"Form data keys: {list(form.keys())}")

                ok = RequestValidator(TWILIO_AUTH_TOKEN).validate(str(request.url), form, sig)
                logger.info(f"Signature validation result: {ok}")

                if not ok:
                    logger.warning("Signature validation failed - rejecting call")
                    return FastResponse(
                        content='<?xml version="1.0" encoding="UTF-8"?><Response><Reject/></Response>',
                        media_type="application/xml",
                        status_code=403,
                    )
            except Exception as e:
                logger.error(f"Signature validation exception: {e}")
                return FastResponse(
                    content='<?xml version="1.0" encoding="UTF-8"?><Response><Reject/></Response>',
                    media_type="application/xml",
                    status_code=403,
                )
        # Allow Twilio routes through (they’re public but signature-checked)
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
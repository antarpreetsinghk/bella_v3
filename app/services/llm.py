# app/services/llm.py
from __future__ import annotations

import asyncio
import json
import os
import re
from typing import Any, Dict, Optional

import httpx
from pydantic import BaseModel, Field, ValidationError

from app.core.config import settings


# ---------- Public contract ----------

class ExtractedAppointment(BaseModel):
    full_name: Optional[str] = Field(None, description="Caller name (string)")
    mobile: Optional[str] = Field(None, description="E.164 or raw string; will be normalized later")
    starts_at: Optional[str] = Field(
        None,
        description="ISO8601 preferred; if natural language, model should convert to ISO"
    )
    duration_min: Optional[int] = Field(30, ge=1, le=240)
    notes: Optional[str] = None

    # helpful metadata for UX (not strictly required)
    missing: list[str] = Field(default_factory=list, description="Fields the model is unsure about")
    confidence: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Optional model self-estimate"
    )


# ---------- Helpers ----------

_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL | re.IGNORECASE)

def _strip_json_fences(s: str) -> str:
    m = _JSON_FENCE_RE.match(s.strip())
    return m.group(1) if m else s.strip()

def _coerce_json(s: str) -> Dict[str, Any]:
    s = _strip_json_fences(s)
    try:
        return json.loads(s)
    except Exception:
        brace_start = s.find("{")
        brace_end = s.rfind("}")
        if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
            candidate = s[brace_start: brace_end + 1]
            try:
                return json.loads(candidate)
            except Exception:
                pass
    return {}

def _build_messages(transcript: str) -> list[dict[str, str]]:
    SYSTEM = (
        "You are an assistant that extracts dental appointment details from informal speech.\n"
        "Return ONLY a single JSON object with fields:\n"
        '{ "full_name": string|null, "mobile": string|null, "starts_at": string|null,'
        '  "duration_min": number|null, "notes": string|null, "missing": string[], "confidence": number|null }.\n'
        "Rules: Do not include any extra keys, commentary, or formatting. No markdown. No code fences."
    )
    USER = (
        "Transcript:\n"
        f"{transcript}\n\n"
        "Output requirements:\n"
        "- Normalize dates into ISO8601 if possible; if uncertain, set the field to null and list it in `missing`.\n"
        "- If phone number is spoken with words/spaces, keep as a single string; do not format beyond removing obvious delimiters.\n"
        "- Default duration_min to 30 if not specified.\n"
        "- Respond with JSON ONLY."
    )
    return [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": USER},
    ]

def _openai_base_url() -> str:
    return (settings.OPENAI_BASE_URL or "https://api.openai.com").rstrip("/")


# ---------- Core call ----------

async def extract_appointment_fields(transcript: str) -> ExtractedAppointment:
    """
    Single entrypoint for LLM extraction.

    Behavior:
      - If LLM_ENABLED=false (env), returns a safe placeholder (good for CI).
      - If enabled and OPENAI_API_KEY missing -> raises with a clear error.
      - Otherwise calls OpenAI and validates output.
    """
    if not transcript or not transcript.strip():
        raise ValueError("Transcript is empty.")

    # LLM toggle (env can be "true"/"false"/"1"/"0")
    llm_enabled = str(os.getenv("LLM_ENABLED", "true")).lower() in {"1", "true", "yes", "on"}
    if not llm_enabled:
        # Safe CI/dev fallback: no network, no key needed
        return ExtractedAppointment(
            full_name=None,
            mobile=None,
            starts_at=None,
            duration_min=30,
            notes="[LLM disabled]",
            missing=["full_name", "mobile", "starts_at"],
            confidence=None,
        )

    base_url = _openai_base_url()
    model = getattr(settings, "OPENAI_MODEL", None) or "gpt-4o-mini"
    api_key = getattr(settings, "OPENAI_API_KEY", None)
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set but LLM is enabled. Set LLM_ENABLED=false to disable in CI.")

    max_output_tokens = int(getattr(settings, "RESPONSE_MAX_TOKENS", 512))

    payload = {
        "model": model,
        "messages": _build_messages(transcript),
        "temperature": 0,
        "max_tokens": max_output_tokens,
        "response_format": {"type": "json_object"},
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        resp = await client.post("/v1/chat/completions", headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        text = (data.get("choices") or [{}])[0].get("message", {}).get("content", "") or ""
        obj = _coerce_json(text)

        if not obj:
            retry_payload = {**payload}
            retry_payload.pop("response_format", None)
            resp2 = await client.post("/v1/chat/completions", headers=headers, json=retry_payload)
            resp2.raise_for_status()
            data2 = resp2.json()
            text2 = (data2.get("choices") or [{}])[0].get("message", {}).get("content", "") or ""
            obj = _coerce_json(text2)

    obj.setdefault("full_name", None)
    obj.setdefault("mobile", None)
    obj.setdefault("starts_at", None)
    obj.setdefault("duration_min", 30)
    obj.setdefault("notes", None)
    obj.setdefault("missing", [])
    obj.setdefault("confidence", None)

    try:
        parsed = ExtractedAppointment(**obj)
    except ValidationError as ve:
        minimal = {
            "full_name": obj.get("full_name"),
            "mobile": obj.get("mobile"),
            "starts_at": obj.get("starts_at"),
            "duration_min": obj.get("duration_min") if isinstance(obj.get("duration_min"), (int, float)) else 30,
            "notes": obj.get("notes"),
            "missing": obj.get("missing") if isinstance(obj.get("missing"), list) else [],
            "confidence": obj.get("confidence") if isinstance(obj.get("confidence"), (int, float)) else None,
        }
        try:
            parsed = ExtractedAppointment(**minimal)
        except Exception as inner:
            raise RuntimeError(f"LLM extraction validation failed: {ve}") from inner

    return parsed


# ---------- Simple CLI for local dev (optional) ----------

if __name__ == "__main__":
    example = (
        "Hey, this is John Smith. I'd like to book next Tuesday at 10 in the morning. "
        "My number is 587 555 0199. Make it a regular 30 minute cleaning."
    )

    async def _demo():
        result = await extract_appointment_fields(example)
        print(result.model_dump())

    asyncio.run(_demo())

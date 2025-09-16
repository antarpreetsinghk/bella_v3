# app/services/llm.py
from __future__ import annotations

import asyncio
import json
import re
from typing import Any, Dict, Optional

import httpx
from pydantic import BaseModel, Field, ValidationError

from app.core.config import settings


# ---------- Public contract (what we return to the orchestrator) ----------

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
    """
    If the model wraps JSON in ```json ...```, strip the fence.
    """
    m = _JSON_FENCE_RE.match(s.strip())
    return m.group(1) if m else s.strip()


def _coerce_json(s: str) -> Dict[str, Any]:
    """
    Attempt to coerce a string into JSON. Falls back to {} on failure.
    """
    s = _strip_json_fences(s)
    try:
        return json.loads(s)
    except Exception:
        # last-ditch: try to extract the first {...} block
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
    """
    Compose a minimal, robust prompt that strongly biases toward strict JSON output.
    """
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
    """
    Allow overriding the base URL (useful for proxies/self-hosted gateways).
    """
    return (settings.OPENAI_BASE_URL or "https://api.openai.com").rstrip("/")


# ---------- Core call ----------

async def extract_appointment_fields(transcript: str) -> ExtractedAppointment:
    """
    Single entrypoint for LLM extraction.
    - Enforces JSON-only via response_format
    - Retries once if the model returns non-JSON
    - Validates into ExtractedAppointment
    """
    if not transcript or not transcript.strip():
        raise ValueError("Transcript is empty.")

    base_url = _openai_base_url()
    model = getattr(settings, "OPENAI_MODEL", None) or "gpt-4o-mini"
    api_key = getattr(settings, "OPENAI_API_KEY", None)
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set.")

    # Safety bounds; fallbacks if not present in settings
    max_input_tokens = int(getattr(settings, "REQUEST_MAX_TOKENS", 4000))
    max_output_tokens = int(getattr(settings, "RESPONSE_MAX_TOKENS", 512))

    # Build payload for Chat Completions with JSON mode
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
        # Primary attempt
        resp = await client.post("/v1/chat/completions", headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        text = (data.get("choices") or [{}])[0].get("message", {}).get("content", "") or ""
        obj = _coerce_json(text)

        # If empty/non-JSON sneaks through, do one guarded retry without response_format
        if not obj:
            retry_payload = {
                **payload,
                "response_format": None,  # remove hard JSON mode
            }
            resp2 = await client.post("/v1/chat/completions", headers=headers, json=retry_payload)
            resp2.raise_for_status()
            data2 = resp2.json()
            text2 = (data2.get("choices") or [{}])[0].get("message", {}).get("content", "") or ""
            obj = _coerce_json(text2)

    # Ensure required keys exist even if model omitted them
    obj.setdefault("full_name", None)
    obj.setdefault("mobile", None)
    obj.setdefault("starts_at", None)
    obj.setdefault("duration_min", 30)
    obj.setdefault("notes", None)
    obj.setdefault("missing", [])
    obj.setdefault("confidence", None)

    # Final validation into our dataclass
    try:
        parsed = ExtractedAppointment(**obj)
    except ValidationError as ve:
        # If model produced junk types, degrade gracefully but surface something usable
        # Attempt a minimal salvage by stripping extraneous keys then re-validating
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
            # Surface a concise error; the orchestrator can decide to ask a follow-up question
            raise RuntimeError(f"LLM extraction validation failed: {ve}") from inner

    return parsed


# ---------- Simple CLI for local dev (optional) ----------

if __name__ == "__main__":
    # Quick manual test:
    example = (
        "Hey, this is John Smith. I'd like to book next Tuesday at 10 in the morning. "
        "My number is 587 555 0199. Make it a regular 30 minute cleaning."
    )

    async def _demo():
        result = await extract_appointment_fields(example)
        print(result.model_dump())

    asyncio.run(_demo())

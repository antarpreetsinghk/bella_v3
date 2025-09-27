# app/services/canadian_extraction.py
"""
Rock-solid information extraction optimized for Canadian voice systems.
Uses specialized libraries with LLM fallback for maximum accuracy and speed.
"""
import logging
import re
from datetime import datetime, timezone
from typing import Optional

import phonenumbers
from phonenumbers import PhoneNumberFormat, geocoder
import parsedatetime
from dateutil import parser

logger = logging.getLogger(__name__)

# Lazy loading for optional dependencies
_spacy_nlp = None

def _get_spacy():
    """Lazy load spaCy to avoid startup time if not needed"""
    global _spacy_nlp
    if _spacy_nlp is None:
        try:
            import spacy
            _spacy_nlp = spacy.load("en_core_web_sm")
            logger.info("spaCy model loaded successfully")
        except (ImportError, OSError) as e:
            logger.warning("spaCy not available (%s), falling back to regex for names", e)
            _spacy_nlp = False
    return _spacy_nlp if _spacy_nlp else None


async def extract_canadian_phone(speech: str, llm_fallback=None) -> Optional[str]:
    """
    Rock-solid Canadian phone number extraction.

    Returns:
        E.164 formatted phone number (+14165551234) or None
    """
    if not speech or not speech.strip():
        return None

    speech = speech.strip()
    logger.info("[phone_canadian] processing: '%s'", speech)

    # Layer 1: Direct phonenumbers parsing (handles 95% of cases)
    for region in ["CA", "US"]:
        try:
            parsed = phonenumbers.parse(speech, region)
            if phonenumbers.is_valid_number(parsed):
                # Verify it's North American
                country = geocoder.country_name_for_number(parsed, "en")
                if country in ["Canada", "United States"]:
                    result = phonenumbers.format_number(parsed, PhoneNumberFormat.E164)
                    logger.info("[phone_canadian] direct success: '%s' -> %s", speech, result)
                    return result
        except phonenumbers.phonenumberutil.NumberParseException:
            continue

    # Layer 2: Extract digits and try again (speech-to-text "four one six...")
    digits = re.sub(r'\D+', '', speech)
    if digits and len(digits) >= 7:
        try:
            # Format as North American number
            if len(digits) == 10:
                candidate = f"+1{digits}"
            elif len(digits) == 11 and digits.startswith("1"):
                candidate = f"+{digits}"
            else:
                candidate = f"+1{digits[-10:]}"  # Take last 10 digits

            parsed = phonenumbers.parse(candidate, "CA")
            if phonenumbers.is_valid_number(parsed):
                result = phonenumbers.format_number(parsed, PhoneNumberFormat.E164)
                logger.info("[phone_canadian] digits fallback: '%s' -> %s", speech, result)
                return result
        except phonenumbers.phonenumberutil.NumberParseException:
            pass

    # Layer 3: LLM fallback if provided
    if llm_fallback:
        try:
            llm_result = await llm_fallback(speech)
            if llm_result and llm_result != speech:
                return await extract_canadian_phone(llm_result, None)  # Recursive without LLM
        except Exception as e:
            logger.warning("[phone_canadian] LLM fallback failed: %s", e)

    logger.warning("[phone_canadian] all methods failed for: '%s'", speech)
    return None


async def extract_canadian_time(speech: str, llm_fallback=None) -> Optional[datetime]:
    """
    Rock-solid Canadian time extraction with timezone awareness.

    Returns:
        UTC datetime object or None
    """
    if not speech or not speech.strip():
        return None

    speech = speech.strip()
    logger.info("[time_canadian] processing: '%s'", speech)

    # Layer 1: parsedatetime (excellent for Canadian English)
    try:
        cal = parsedatetime.Calendar()
        time_struct, parse_status = cal.parse(speech)
        if parse_status:
            # Convert to datetime and assume local timezone
            dt = datetime(*time_struct[:6])
            # Assume Canada/Eastern for now (can be configurable)
            from zoneinfo import ZoneInfo
            local_dt = dt.replace(tzinfo=ZoneInfo("America/Toronto"))
            result = local_dt.astimezone(timezone.utc)
            logger.info("[time_canadian] parsedatetime success: '%s' -> %s", speech, result)
            return result
    except Exception as e:
        logger.debug("[time_canadian] parsedatetime failed: %s", e)

    # Layer 2: dateutil parser (robust fallback)
    try:
        # Try fuzzy parsing
        dt = parser.parse(speech, fuzzy=True)
        if dt.tzinfo is None:
            from zoneinfo import ZoneInfo
            dt = dt.replace(tzinfo=ZoneInfo("America/Toronto"))
        result = dt.astimezone(timezone.utc)
        logger.info("[time_canadian] dateutil success: '%s' -> %s", speech, result)
        return result
    except Exception as e:
        logger.debug("[time_canadian] dateutil failed: %s", e)

    # Layer 3: LLM fallback if provided
    if llm_fallback:
        try:
            llm_result = await llm_fallback(speech)
            if llm_result and llm_result != speech:
                # Try to parse LLM result as ISO format first
                try:
                    dt = datetime.fromisoformat(llm_result.replace('Z', '+00:00'))
                    logger.info("[time_canadian] LLM ISO success: '%s' -> %s", speech, dt)
                    return dt.astimezone(timezone.utc)
                except:
                    # Recursive parse of LLM result
                    return await extract_canadian_time(llm_result, None)
        except Exception as e:
            logger.warning("[time_canadian] LLM fallback failed: %s", e)

    logger.warning("[time_canadian] all methods failed for: '%s'", speech)
    return None


async def extract_canadian_name(speech: str, llm_fallback=None) -> Optional[str]:
    """
    Fast Canadian name extraction with timeout protection.

    Returns:
        Properly formatted "First Last" name or None
    """
    if not speech or not speech.strip():
        return None

    speech = speech.strip()
    logger.info("[name_canadian] processing: '%s'", speech)

    # Fast pattern matching for Canadian name patterns (no heavy dependencies)
    patterns = [
        r"(?:my name is|i'm|this is|i am)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
        r"(?:my name is|i'm|this is|i am)\s+([a-z]+(?:\s+[a-z]+)+)",  # lowercase
        r"^([A-Z][a-z]+\s+[A-Z][a-z]+)(?:\s+calling|$|\s*$)",
        r"^([a-z]+\s+[a-z]+)(?:\s+calling|$|\s*$)",  # lowercase
        r"([A-Z][a-z]+\s+[A-Z][a-z]+)",  # Simple pattern
        r"([a-z]+\s+[a-z]+)",  # Simple pattern lowercase
    ]

    for pattern in patterns:
        try:
            match = re.search(pattern, speech, re.IGNORECASE)
            if match:
                candidate = match.group(1).strip().title()
                # Simple validation - must have at least 2 words with 2+ chars each
                words = candidate.split()
                if len(words) >= 2 and all(len(w) >= 2 for w in words):
                    result = " ".join(words[:2])  # Take first two words
                    logger.info("[name_canadian] pattern success: '%s' -> %s", speech, result)
                    return result
        except Exception as e:
            logger.debug("[name_canadian] pattern failed: %s", e)

    # Simple fallback - try spaCy only if fast patterns failed
    nlp = _get_spacy()
    if nlp:
        try:
            # Quick timeout protection
            import signal
            def timeout_handler(signum, frame):
                raise TimeoutError("spaCy processing timeout")

            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(2)  # 2 second timeout

            doc = nlp(speech)
            for ent in doc.ents:
                if ent.label_ == "PERSON":
                    result = ent.text.strip().title()
                    words = result.split()
                    if len(words) >= 2:
                        result = " ".join(words[:2])
                        logger.info("[name_canadian] spacy success: '%s' -> %s", speech, result)
                        return result

            signal.alarm(0)  # Cancel timeout
        except (Exception, TimeoutError) as e:
            signal.alarm(0)  # Cancel timeout
            logger.debug("[name_canadian] spaCy failed: %s", e)

    # LLM fallback if provided
    if llm_fallback:
        try:
            llm_result = await llm_fallback(speech)
            if llm_result and llm_result != speech and len(llm_result) > 3:
                # Extract just the name part from LLM result
                words = llm_result.strip().title().split()
                if len(words) >= 2:
                    result = " ".join(words[:2])
                    logger.info("[name_canadian] LLM success: '%s' -> %s", speech, result)
                    return result
        except Exception as e:
            logger.warning("[name_canadian] LLM fallback failed: %s", e)

    logger.warning("[name_canadian] all methods failed for: '%s'", speech)
    return None


# Convenience functions that match existing API
async def extract_phone_fast(speech: str) -> Optional[str]:
    """Alias for backwards compatibility"""
    return await extract_canadian_phone(speech)


async def extract_time_fast(speech: str) -> Optional[datetime]:
    """Alias for backwards compatibility"""
    return await extract_canadian_time(speech)


async def extract_name_fast(speech: str) -> Optional[str]:
    """Alias for backwards compatibility"""
    return await extract_canadian_name(speech)
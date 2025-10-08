# app/services/simple_extraction.py
"""
Simple, cost-effective extraction functions to replace expensive LLM calls.
Focus on speed and reliability over complex AI processing.
"""
import re
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import phonenumbers
from phonenumbers import PhoneNumberFormat

logger = logging.getLogger(__name__)

def extract_name_simple(speech: str) -> str:
    """
    Enhanced name extraction that properly handles name introduction phrases.
    Fixes the bug where "Hi. My name is Johnny rocker." became "Hi My Name".
    """
    if not speech or not speech.strip():
        return ""

    text = speech.strip()
    text_lower = text.lower()

    # Enhanced patterns for name introduction - using regex to find anywhere in text
    name_patterns = [
        # Standard patterns
        r'\bmy name is\s+(.+?)(?:\.|$)',           # "my name is Johnny"
        r'\bi am\s+(.+?)(?:\.|$)',                 # "i am Johnny"
        r'\bthis is\s+(.+?)(?:\.|$)',              # "this is Johnny"
        r'\bcall me\s+(.+?)(?:\.|$)',              # "call me Johnny"
        r'\byou can call me\s+(.+?)(?:\.|$)',      # "you can call me Johnny"
        r'\bit\'s\s+(.+?)(?:\.|$)',                # "it's Johnny"
        r'\bi\'m\s+(.+?)(?:\.|$)',                 # "i'm Johnny"

        # Casual variations that might be preceded by greetings
        r'(?:hi|hello|hey|well)[.,]?\s+my name is\s+(.+?)(?:\.|$)',  # "Hi, my name is Johnny"
        r'(?:hi|hello|hey|well)[.,]?\s+i am\s+(.+?)(?:\.|$)',        # "Hello, I am Johnny"
        r'(?:hi|hello|hey|well)[.,]?\s+this is\s+(.+?)(?:\.|$)',     # "Hey, this is Johnny"

        # Direct name patterns after greetings
        r'(?:hi|hello|hey)[.,]?\s+i\'m\s+(.+?)(?:\.|$)',            # "Hi, I'm Johnny"
        r'(?:hi|hello|hey)[.,]?\s+it\'s\s+(.+?)(?:\.|$)',           # "Hello, it's Johnny"
    ]

    # Try each pattern to extract the name portion
    for pattern in name_patterns:
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if match:
            extracted_text = match.group(1).strip()
            if extracted_text:
                # Clean and format the extracted name
                return _clean_and_format_name(extracted_text)

    # If no pattern matches, try removing simple prefixes from the beginning
    simple_prefixes = ["name", "name is", "i'm", "it's"]
    for prefix in simple_prefixes:
        if text_lower.startswith(prefix):
            remaining = text[len(prefix):].strip()
            if remaining:
                return _clean_and_format_name(remaining)

    # Final fallback: clean and format the whole input
    return _clean_and_format_name(text)


def _clean_and_format_name(text: str) -> str:
    """
    Helper function to clean and properly format extracted name text.
    """
    if not text:
        return ""

    # Remove common punctuation and clean up
    text = re.sub(r'^[.,;:!?\s]+', '', text)  # Remove leading punctuation
    text = re.sub(r'[.,;:!?\s]+$', '', text)  # Remove trailing punctuation

    # Split into words and clean each word
    words = text.split()
    clean_words = []

    for word in words[:4]:  # Limit to 4 words for full names
        # Remove non-alphabetic characters except apostrophes and hyphens (preserve Unicode letters)
        clean_word = re.sub(r"[^\w'\-]", "", word, flags=re.UNICODE)
        if clean_word:  # Accept any non-empty word including single letters and numbers
            # Properly capitalize hyphenated names like "Jean-Pierre"
            if '-' in clean_word:
                parts = clean_word.split('-')
                clean_word = '-'.join([part.capitalize() for part in parts])
            else:
                clean_word = clean_word.capitalize()
            clean_words.append(clean_word)

    if clean_words:
        return " ".join(clean_words)

    # Special case: if input is a single character or number, return it
    cleaned_single = re.sub(r"[^a-zA-Z0-9]", "", text)
    if cleaned_single:
        return cleaned_single.upper()

    # If nothing meaningful extracted, return empty
    return ""

def extract_phone_simple(speech: str) -> Optional[str]:
    """
    Extract phone number using built-in patterns and phonenumbers library.
    Fast and reliable for North American numbers.
    """
    if not speech or not speech.strip():
        return None

    original_speech = speech
    logger.debug(f"[phone_simple] processing: '{speech}'")

    # Enhanced preprocessing for speech artifacts
    text = speech.lower()

    # Handle speech artifacts and patterns
    speech_patterns = [
        # Remove common prefixes
        (r'\b(my|number|is|phone|mobile|cell|it\'s|its|the)\b', ''),
        # Handle spelled out numbers
        (r'\bzero\b', '0'),
        (r'\bone\b', '1'),
        (r'\btwo\b', '2'),
        (r'\bthree\b', '3'),
        (r'\bfour\b', '4'),
        (r'\bfive\b', '5'),
        (r'\bsix\b', '6'),
        (r'\bseven\b', '7'),
        (r'\beight\b', '8'),
        (r'\bnine\b', '9'),
        # Handle speech artifacts
        (r'\boh\b', '0'),
        (r'\bdouble\s+(\w+)', r'\1\1'),  # "double five" -> "55"
        (r'\btriple\s+(\w+)', r'\1\1\1'),  # "triple six" -> "666"
    ]

    for pattern, replacement in speech_patterns:
        text = re.sub(pattern, replacement, text)

    # Clean up extra spaces
    text = re.sub(r'\s+', ' ', text).strip()

    if text != speech.lower():
        logger.debug(f"[phone_simple] preprocessed: '{speech}' -> '{text}'")

    # Method 1: Extract phone-like patterns and try phonenumbers library
    phone_patterns = [
        r'(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})',  # 416-555-1234, 416.555.1234, 416 555 1234
        r'(\d{1}[-.\s]?\d{3}[-.\s]?\d{3}[-.\s]?\d{4})',  # 1-416-555-1234
        r'(\d{10,11})',  # 4165551234 or 14165551234
    ]

    for pattern in phone_patterns:
        match = re.search(pattern, text)
        if match:
            phone_candidate = match.group(1)
            try:
                parsed = phonenumbers.parse(phone_candidate, "CA")
                if phonenumbers.is_valid_number(parsed) or phonenumbers.is_possible_number(parsed):
                    result = phonenumbers.format_number(parsed, PhoneNumberFormat.E164)
                    logger.debug(f"[phone_simple] phonenumbers pattern success: '{phone_candidate}' -> {result}")
                    return result
            except Exception as e:
                logger.debug(f"[phone_simple] phonenumbers pattern parsing failed for '{phone_candidate}': {e}")

    # Method 1b: Try phonenumbers library on full input as fallback
    try:
        parsed = phonenumbers.parse(speech, "CA")
        if phonenumbers.is_valid_number(parsed) or phonenumbers.is_possible_number(parsed):
            result = phonenumbers.format_number(parsed, PhoneNumberFormat.E164)
            logger.debug(f"[phone_simple] phonenumbers success: '{original_speech}' -> {result}")
            return result
    except Exception as e:
        logger.debug(f"[phone_simple] phonenumbers parsing failed: {e}")

    # Method 2: Extract all digits (most reliable for speech)
    digits = re.findall(r'\d', text)

    logger.debug(f"[phone_simple] extracted digits: {digits} (count: {len(digits)})")

    if len(digits) == 10:
        # Canadian/US number without country code
        phone = "".join(digits)
        result = f"+1{phone}"
        logger.debug(f"[phone_simple] 10-digit success: '{original_speech}' -> {result}")
        return result
    elif len(digits) == 11 and digits[0] == '1':
        # Number with country code
        phone = "".join(digits)
        result = f"+{phone}"
        logger.debug(f"[phone_simple] 11-digit success: '{original_speech}' -> {result}")
        return result

    # Method 3: Pattern matching for common spoken formats
    patterns = [
        # "four one six five five five one two three four"
        r'(\w+)\s+(\w+)\s+(\w+)\s+(\w+)\s+(\w+)\s+(\w+)\s+(\w+)\s+(\w+)\s+(\w+)\s+(\w+)',
        # "416 555 1234" or "four one six five five five one two three four"
        r'(\d{3}|\w+)\s+(\d{3}|\w+)\s+(\d{4}|\w+\s+\w+\s+\w+\s+\w+)',
        # "4165551234" in words
        r'(\w+\s+\w+\s+\w+\s+\w+\s+\w+\s+\w+\s+\w+\s+\w+\s+\w+\s+\w+)',
    ]

    word_to_digit = {
        'zero': '0', 'one': '1', 'two': '2', 'three': '3', 'four': '4',
        'five': '5', 'six': '6', 'seven': '7', 'eight': '8', 'nine': '9',
        'oh': '0'
    }

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            # Convert words to digits
            digits_from_words = []
            for group in match.groups():
                if group:
                    words = group.split()
                    for word in words:
                        word_clean = word.strip().lower()
                        if word_clean in word_to_digit:
                            digits_from_words.append(word_to_digit[word_clean])
                        elif word_clean.isdigit():
                            digits_from_words.extend(list(word_clean))

            if len(digits_from_words) == 10:
                phone = "".join(digits_from_words)
                result = f"+1{phone}"
                logger.debug(f"[phone_simple] pattern success: '{original_speech}' -> {result}")
                return result
            elif len(digits_from_words) == 11 and digits_from_words[0] == '1':
                phone = "".join(digits_from_words)
                result = f"+{phone}"
                logger.debug(f"[phone_simple] pattern success: '{original_speech}' -> {result}")
                return result

    logger.debug(f"[phone_simple] all methods failed for: '{original_speech}'")
    return None

def extract_key_phrases(speech: str, context: str) -> str:
    """
    Extract key information based on context using pattern matching.
    Much faster than LLM calls.
    """
    if not speech:
        return speech

    speech_lower = speech.lower()

    patterns = {
        "confirm": {
            "yes": r'\b(yes|yeah|yep|sure|okay|correct|right|confirm|good|fine|ok)\b',
            "no": r'\b(no|nope|wrong|incorrect|negative|not|cancel)\b'
        },
        "time": {
            "morning": r'\b(morning|am|before noon|9|10|11)\b',
            "afternoon": r'\b(afternoon|pm|after noon|1|2|3|4|5)\b',
            "evening": r'\b(evening|night|after 5|6|7|8)\b'
        },
        "duration": {
            "30": r'\b(thirty|30|half hour|half)\b',
            "45": r'\b(forty five|45|three quarter)\b',
            "60": r'\b(sixty|60|one hour|hour|full hour)\b'
        },
        "day": {
            "today": r'\b(today|now|this day)\b',
            "tomorrow": r'\b(tomorrow|tmrw|next day)\b',
            "monday": r'\bmonda?y\b',
            "tuesday": r'\btuesda?y\b',
            "wednesday": r'\bwednesda?y\b',
            "thursday": r'\bthursda?y\b',
            "friday": r'\bfrida?y\b',
        }
    }

    if context in patterns:
        for key, pattern in patterns[context].items():
            if re.search(pattern, speech_lower):
                return key

    # Return original if no pattern matches
    return speech

def clean_speech_basic(speech: str) -> str:
    """
    Basic speech cleaning without expensive LLM calls.
    Handles common transcription issues.
    """
    if not speech:
        return ""

    # Common transcription corrections
    corrections = {
        # Common mis-transcriptions
        "tmrw": "tomorrow",
        "tommorrow": "tomorrow",
        "tomorow": "tomorrow",
        "apointment": "appointment",
        "appoinment": "appointment",
        "por": "four",
        "tree": "three",
        "sirty": "thirty",
        "turty": "thirty",

        # Time corrections
        "10 am": "10 AM",
        "2 pm": "2 PM",
        "3 pm": "3 PM",

        # Common number corrections
        "won": "one",
        "to": "two",
        "ate": "eight",
    }

    cleaned = speech
    for wrong, correct in corrections.items():
        cleaned = re.sub(r'\b' + re.escape(wrong) + r'\b', correct, cleaned, flags=re.IGNORECASE)

    return cleaned.strip()

def word_to_number_simple(text: str) -> str:
    """
    Simple word to number conversion for common cases.
    Replaces the word2number library.
    """
    word_map = {
        "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4",
        "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
        "ten": "10", "eleven": "11", "twelve": "12", "thirteen": "13",
        "fourteen": "14", "fifteen": "15", "sixteen": "16", "seventeen": "17",
        "eighteen": "18", "nineteen": "19", "twenty": "20", "thirty": "30",
        "forty": "40", "fifty": "50", "sixty": "60"
    }

    result = text.lower()
    for word, number in word_map.items():
        result = re.sub(r'\b' + word + r'\b', number, result)

    return result

# Compatibility functions to replace LLM service
async def clean_and_enhance_speech(speech: str, context: str = None) -> str:
    """Drop-in replacement for LLM speech enhancement"""
    return clean_speech_basic(speech)

async def extract_appointment_fields(speech: str) -> Dict[str, Any]:
    """Drop-in replacement for LLM field extraction"""
    return {
        "name": extract_name_simple(speech),
        "phone": extract_phone_simple(speech),
        "confidence": 0.8  # Assume good confidence for simple patterns
    }

async def unified_appointment_extraction(speech: str, context: str = None) -> Dict[str, Any]:
    """Drop-in replacement for unified LLM extraction"""
    return await extract_appointment_fields(speech)

# Simple caching for transcription (replace whisper_stt)
_transcription_cache = {}

async def transcribe_with_cache(call_sid: str, speech_result: str, redis_client=None, cache_ttl: int = 1800) -> str:
    """
    Simple passthrough 'transcription' that just cleans Twilio's speech result.
    Replaces expensive Whisper API calls.
    """
    if not speech_result:
        return ""

    # Use Redis cache if available
    cache_key = f"speech:{call_sid}:{hash(speech_result)}"

    if redis_client:
        try:
            cached = await redis_client.get(cache_key)
            if cached:
                return cached
        except Exception:
            pass

    # Basic cleaning (no expensive API calls)
    cleaned = clean_speech_basic(speech_result)

    # Cache the result
    if redis_client:
        try:
            await redis_client.setex(cache_key, cache_ttl, cleaned)
        except Exception:
            pass

    return cleaned
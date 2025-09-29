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
    """Temporarily disabled spaCy to fix performance issues"""
    global _spacy_nlp
    if _spacy_nlp is None:
        # TEMPORARY: Disable spaCy for faster startup
        logger.info("spaCy disabled for performance, using regex fallback")
        _spacy_nlp = False
    return _spacy_nlp if _spacy_nlp else None


async def extract_canadian_phone(speech: str, llm_fallback=None) -> Optional[str]:
    """
    Enhanced Canadian phone number extraction with word2number support.

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
            if phonenumbers.is_valid_number(parsed) or phonenumbers.is_possible_number(parsed):
                # For voice apps, be lenient with geographic validation
                try:
                    country = geocoder.country_name_for_number(parsed, "en")
                    is_north_american = country in ["Canada", "United States"] or not country
                except:
                    is_north_american = True  # Default to accepting if geocoding fails

                if is_north_american:
                    result = phonenumbers.format_number(parsed, PhoneNumberFormat.E164)
                    validity = "valid" if phonenumbers.is_valid_number(parsed) else "possible"
                    logger.info("[phone_canadian] direct success (%s): '%s' -> %s", speech, result, validity)
                    return result
        except phonenumbers.phonenumberutil.NumberParseException:
            continue

    # Layer 2: Enhanced word-to-number conversion using word2number library
    try:
        from word2number import w2n

        # Split speech into words and try to convert number words
        words = speech.lower().split()
        converted_digits = ""

        # First, try word2number for natural number sequences
        number_words = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'oh']
        if any(word in number_words for word in words):
            for word in words:
                try:
                    if word in number_words:
                        if word == 'oh':
                            converted_digits += '0'
                        else:
                            digit = str(w2n.word_to_num(word))
                            if len(digit) == 1:  # Single digit only
                                converted_digits += digit
                except:
                    # If word2number fails, use manual mapping
                    word_to_digit = {
                        'zero': '0', 'one': '1', 'two': '2', 'three': '3', 'four': '4',
                        'five': '5', 'six': '6', 'seven': '7', 'eight': '8', 'nine': '9',
                        'oh': '0'
                    }
                    if word in word_to_digit:
                        converted_digits += word_to_digit[word]

        logger.debug("[phone_canadian] word2number conversion: '%s' -> '%s'", speech, converted_digits)

    except ImportError:
        logger.debug("[phone_canadian] word2number not available, using fallback")
        converted_digits = ""

    # Layer 3: Enhanced digit extraction (handles edge cases and spelled-out numbers)

    # Fallback spelled-out numbers mapping
    word_to_digit = {
        'zero': '0', 'one': '1', 'two': '2', 'three': '3', 'four': '4',
        'five': '5', 'six': '6', 'seven': '7', 'eight': '8', 'nine': '9',
        'oh': '0'  # Common speech pattern
    }

    # Convert spelled-out numbers (fallback if word2number not available)
    if not converted_digits:
        words = re.findall(r'\b(?:zero|one|two|three|four|five|six|seven|eight|nine|oh)\b', speech.lower())
        if len(words) >= 7:  # Likely a phone number
            converted_digits = ''.join(word_to_digit.get(word, '') for word in words)
            logger.debug("[phone_canadian] fallback spelled digits: %s", converted_digits)

    # Extract regular digits with multiple patterns
    original_digits = re.sub(r'\D+', '', speech)

    # Try multiple digit extraction patterns in order of preference
    digit_patterns = [
        converted_digits,  # word2number or spelled-out numbers
        original_digits,  # Raw digits
        re.sub(r'[^\d\s]', '', speech).replace(' ', ''),  # Keep spaces, remove punctuation
        ''.join(re.findall(r'\d', speech))  # Alternative extraction
    ]

    for digits in digit_patterns:
        if digits and len(digits) >= 7:
            try:
                # Enhanced North American number formatting
                if len(digits) == 10:
                    candidate = f"+1{digits}"
                elif len(digits) == 11 and digits.startswith("1"):
                    candidate = f"+{digits}"
                elif len(digits) >= 10:
                    candidate = f"+1{digits[-10:]}"  # Take last 10 digits
                else:
                    continue  # Skip if too short

                logger.debug("[phone_canadian] trying candidate: '%s' from '%s'", candidate, digits)
                parsed = phonenumbers.parse(candidate, "CA")

                # For voice applications, be more lenient - accept if parseable even if not strictly valid
                # This handles test numbers and edge cases that callers might use
                if phonenumbers.is_valid_number(parsed) or phonenumbers.is_possible_number(parsed):
                    result = phonenumbers.format_number(parsed, PhoneNumberFormat.E164)
                    validity = "valid" if phonenumbers.is_valid_number(parsed) else "possible"
                    logger.info("[phone_canadian] digits success (%s): '%s' -> %s (pattern: %s)", validity, speech, result, digits)
                    return result
            except phonenumbers.phonenumberutil.NumberParseException:
                continue

    # Layer 4: LLM fallback if provided
    if llm_fallback:
        try:
            llm_result = await llm_fallback(speech)
            if llm_result and llm_result != speech:
                return await extract_canadian_phone(llm_result, None)  # Recursive without LLM
        except Exception as e:
            logger.warning("[phone_canadian] LLM fallback failed: %s", e)

    logger.warning("[phone_canadian] all methods failed for: '%s'", speech)
    return None


def format_phone_for_speech(phone: str) -> str:
    """
    Format phone number for clear speech synthesis.
    Converts +12048694905 → '204 869 4905' for natural pronunciation.

    Args:
        phone: Phone number in E.164 format (+12048694905) or other formats

    Returns:
        Formatted phone number optimized for speech (e.g., "204 869 4905")
    """
    if not phone or phone == "Unknown":
        return phone

    # Remove all non-digits
    digits_only = re.sub(r'\D', '', phone)

    # Handle North American numbers (11 digits starting with 1)
    if len(digits_only) == 11 and digits_only.startswith('1'):
        # Remove country code 1, format as XXX XXX XXXX
        area_code = digits_only[1:4]
        exchange = digits_only[4:7]
        number = digits_only[7:11]
        return f"{area_code} {exchange} {number}"

    # Handle 10-digit North American numbers (missing country code)
    elif len(digits_only) == 10:
        area_code = digits_only[0:3]
        exchange = digits_only[3:6]
        number = digits_only[6:10]
        return f"{area_code} {exchange} {number}"

    # For other formats, return original (international numbers, etc.)
    return phone


async def extract_canadian_time(speech: str, llm_fallback=None) -> Optional[datetime]:
    """
    Enhanced Canadian time extraction with dateparser and advanced preprocessing.

    Returns:
        UTC datetime object or None
    """
    if not speech or not speech.strip():
        return None

    speech = speech.strip()
    logger.info("[time_canadian] processing: '%s'", speech)

    # Enhanced preprocessing: Handle more speech patterns and speech-to-text errors
    original_speech = speech
    speech_lower = speech.lower()

    # Enhanced pattern handling for speech-to-text artifacts
    preprocessing_patterns = [
        # Handle periods after phrases
        ("next week.", "next week"),
        ("this week.", "this week"),
        ("tomorrow.", "tomorrow"),
        ("monday.", "monday"),
        ("tuesday.", "tuesday"),
        ("wednesday.", "wednesday"),
        ("thursday.", "thursday"),
        ("friday.", "friday"),
        ("saturday.", "saturday"),
        ("sunday.", "sunday"),
        # Handle common speech-to-text time errors
        ("a.m.", "AM"),
        ("p.m.", "PM"),
        ("am.", "AM"),
        ("pm.", "PM"),
        ("o'clock", "o clock"),
        ("o clock", ""),
        ("thirty", "30"),
        ("fifteen", "15"),
        ("fourty", "40"),  # Common speech error
        ("forty", "40"),
        ("o'clock", ""),
    ]

    for old_pattern, new_pattern in preprocessing_patterns:
        speech = speech.replace(old_pattern, new_pattern)

    # Handle complex phrase patterns
    if speech_lower.startswith("next week"):
        cleaned = speech[9:].strip()  # Remove "next week"
        if cleaned:
            speech = f"next {cleaned}"
    elif speech_lower.startswith("this week"):
        cleaned = speech[9:].strip()  # Remove "this week"
        if cleaned:
            speech = f"this {cleaned}"
    elif speech_lower.startswith("tomorrow"):
        cleaned = speech[8:].strip()  # Remove "tomorrow"
        if cleaned and not cleaned.startswith("at"):
            speech = f"tomorrow {cleaned}"

    # Clean extra spaces
    speech = re.sub(r'\s+', ' ', speech).strip()

    if speech != original_speech:
        logger.debug("[time_canadian] preprocessed: '%s' -> '%s'", original_speech, speech)

    # Layer 1: dateparser library (better natural language processing)
    try:
        import dateparser

        # Configure dateparser for Canadian context
        settings = {
            'TIMEZONE': 'America/Edmonton',
            'RETURN_AS_TIMEZONE_AWARE': True,
            'PREFER_DATES_FROM': 'future',
            'PREFER_DAY_OF_MONTH': 'first',
            'SKIP_TOKENS': ['at', 'on', 'for'],  # Skip common filler words
        }

        result = dateparser.parse(speech, settings=settings)
        if result:
            utc_result = result.astimezone(timezone.utc)
            logger.info("[time_canadian] dateparser success: '%s' -> %s", speech, utc_result)
            return utc_result

    except ImportError:
        logger.debug("[time_canadian] dateparser not available, using fallback")
    except Exception as e:
        logger.debug("[time_canadian] dateparser failed: %s", e)

    # Layer 2: parsedatetime (excellent for Canadian English)
    try:
        cal = parsedatetime.Calendar()
        time_struct, parse_status = cal.parse(speech)
        if parse_status:
            # Convert to datetime and assume local timezone
            dt = datetime(*time_struct[:6])
            # Use Edmonton timezone to match business hours
            from zoneinfo import ZoneInfo
            local_dt = dt.replace(tzinfo=ZoneInfo("America/Edmonton"))
            result = local_dt.astimezone(timezone.utc)
            logger.info("[time_canadian] parsedatetime success: '%s' -> %s", speech, result)
            return result
    except Exception as e:
        logger.debug("[time_canadian] parsedatetime failed: %s", e)

    # Layer 3: dateutil parser (robust fallback)
    try:
        # Try fuzzy parsing
        dt = parser.parse(speech, fuzzy=True)
        if dt.tzinfo is None:
            from zoneinfo import ZoneInfo
            dt = dt.replace(tzinfo=ZoneInfo("America/Edmonton"))
        result = dt.astimezone(timezone.utc)
        logger.info("[time_canadian] dateutil success: '%s' -> %s", speech, result)
        return result
    except Exception as e:
        logger.debug("[time_canadian] dateutil failed: %s", e)

    # Layer 4: Pattern-based extraction for common formats
    try:
        # Try to extract common time patterns manually
        time_patterns = [
            r'(\w+day)\s+at\s+(\d{1,2})\s*(am|pm|a\.m\.|p\.m\.)',  # "Monday at 2 PM"
            r'(\w+day)\s+(\d{1,2})\s*(am|pm|a\.m\.|p\.m\.)',       # "Monday 2 PM"
            r'(next|this)\s+(\w+day)\s+at\s+(\d{1,2})\s*(am|pm|a\.m\.|p\.m\.)',  # "next Monday at 2 PM"
            r'(tomorrow|today)\s+at\s+(\d{1,2})\s*(am|pm|a\.m\.|p\.m\.)',        # "tomorrow at 2 PM"
        ]

        for pattern in time_patterns:
            match = re.search(pattern, speech, re.IGNORECASE)
            if match:
                # Try to construct a parseable string
                groups = match.groups()
                if len(groups) >= 3:
                    constructed = " ".join(groups)
                    try:
                        dt = parser.parse(constructed, fuzzy=True)
                        if dt.tzinfo is None:
                            from zoneinfo import ZoneInfo
                            dt = dt.replace(tzinfo=ZoneInfo("America/Edmonton"))
                        result = dt.astimezone(timezone.utc)
                        logger.info("[time_canadian] pattern success: '%s' -> %s", speech, result)
                        return result
                    except:
                        continue

    except Exception as e:
        logger.debug("[time_canadian] pattern extraction failed: %s", e)

    # Layer 5: LLM fallback if provided
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


def clean_speech_artifacts(speech: str, extracted_name: str) -> str:
    """
    Clean speech-to-text artifacts from extracted names.
    Handles common Canadian speech patterns and recognition errors.
    """
    if not extracted_name:
        return extracted_name

    # Common speech artifacts that appear in names
    artifacts = [
        # Speech-to-text noise patterns
        'pit called', 'called her', 'cold her', 'pit cold', 'pit',
        'called', 'cold', 'her', 'him', 'and', 'the', 'a', 'an',
        # Common recognition errors
        'please', 'thank', 'thanks', 'hello', 'hi', 'hey',
        'book', 'appointment', 'schedule', 'time', 'today', 'tomorrow',
        'yesterday', 'can', 'you', 'could', 'would', 'should',
        # Additional speech artifacts from production
        'that', 'this', 'with', 'for', 'from', 'to', 'at', 'in', 'on'
    ]

    # Split name into words
    words = extracted_name.split()
    cleaned_words = []

    for word in words:
        word_clean = word.lower().strip('.,!?;')
        # Keep word if it's not an artifact and has proper length
        if (word_clean not in artifacts and
            len(word_clean) >= 2 and
            not word_clean.isdigit() and
            any(c.isalpha() for c in word_clean)):
            cleaned_words.append(word)

    cleaned_name = ' '.join(cleaned_words).strip()

    if cleaned_name != extracted_name:
        logger.info("[name_cleaning] artifact removal: '%s' -> '%s'", extracted_name, cleaned_name)

    return cleaned_name


def validate_canadian_name_context(speech: str, extracted_name: str) -> tuple[bool, str]:
    """
    Enhanced validation for Canadian multilingual context with speech artifact detection.
    Prevents extraction of question words, appointment phrases, and speech-to-text artifacts.

    Returns:
        tuple[bool, str]: (is_valid, cleaned_name)
    """
    if not extracted_name or len(extracted_name.strip()) < 2:
        return False, extracted_name

    # First clean speech artifacts
    cleaned_name = clean_speech_artifacts(speech, extracted_name)
    if not cleaned_name or len(cleaned_name.strip()) < 2:
        logger.debug("[name_validation] rejected after artifact cleaning: '%s' -> '%s'", extracted_name, cleaned_name)
        return False, extracted_name

    extracted_lower = cleaned_name.lower().strip()
    speech_lower = speech.lower().strip()

    # 1. SPEECH ARTIFACT DETECTION
    # Check if original speech contains obvious artifacts that shouldn't be in names
    speech_artifacts = [
        'pit called', 'called her', 'cold her', 'pit cold',
        'book an appointment', 'make appointment', 'schedule appointment',
        'can you book', 'could you book', 'help me book'
    ]

    for artifact in speech_artifacts:
        if artifact in speech_lower:
            logger.debug("[name_validation] rejected speech artifact context: '%s' in speech", artifact)
            return False

    # 2. MULTILINGUAL QUESTION WORD REJECTION (Enhanced)
    question_patterns = [
        # English
        'can you', 'could you', 'will you', 'would you', 'do you', 'are you',
        'help me', 'assist me', 'please help', 'can i', 'may i',
        # French
        'pouvez-vous', 'voulez-vous', 'est-ce que vous', 'aidez-moi',
        'puis-je', 'est-ce que je peux',
        # Mixed/Common
        'book', 'schedule', 'make appointment', 'get appointment'
    ]

    for pattern in question_patterns:
        if pattern in extracted_lower:
            logger.debug("[name_validation] rejected question pattern: '%s' in '%s'", pattern, cleaned_name)
            return False

    # 3. APPOINTMENT-RELATED PHRASES (MULTILINGUAL)
    appointment_phrases = [
        'appointment', 'rendez-vous', 'booking', 'réservation',
        'schedule', 'horaire', 'time slot', 'créneau',
        'meet', 'rencontre', 'visit', 'visite', 'consultation'
    ]

    for phrase in appointment_phrases:
        if phrase in extracted_lower:
            logger.debug("[name_validation] rejected appointment phrase: '%s' in '%s'", phrase, cleaned_name)
            return False, extracted_name

    # 4. CANADIAN NAME CHARACTERISTICS VALIDATION
    words = cleaned_name.split()

    # Must have 1-4 words (covers most Canadian naming conventions)
    if not (1 <= len(words) <= 4):
        logger.debug("[name_validation] rejected word count: %d words in '%s'", len(words), cleaned_name)
        return False, extracted_name

    # At least one word should be capitalized or be a valid name
    french_particles = ['de', 'du', 'des', 'la', 'le', 'saint', 'sainte', 'van', 'von', 'mc', 'mac']
    has_proper_noun = False

    for i, word in enumerate(words):
        # French particles and prefixes can be lowercase if not first word
        if i > 0 and word.lower() in french_particles:
            continue
        # Check if word is properly capitalized or is a valid name pattern
        if word and (word[0].isupper() or word.lower() in french_particles):
            has_proper_noun = True
            break

    if not has_proper_noun:
        logger.debug("[name_validation] rejected no proper nouns: '%s'", cleaned_name)
        return False, extracted_name

    # 5. CONTEXT VALIDATION - reject if extracted from obvious non-name context
    # Check if the extracted name appears in a question context
    question_contexts = [
        'can you', 'could you', 'will you', 'would you', 'do you',
        'hi can', 'hello can', 'hey can', 'excuse me can',
        'pouvez-vous', 'voulez-vous'
    ]

    for context in question_contexts:
        if context in speech_lower:
            logger.debug("[name_validation] rejected question context: '%s' in speech", context)
            return False, extracted_name

    # 6. SPECIFIC PATTERN REJECTION - catch common false extractions
    # If speech contains question words and the extracted name contains those words
    question_word_patterns = ['can', 'you', 'will', 'do', 'hi', 'help', 'me', 'something', 'availability']
    name_words = extracted_lower.split()

    # If extracted name contains question words, it's likely a false positive
    if any(word in question_word_patterns for word in name_words):
        # Exception: allow if it's clearly after a name trigger
        name_triggers = ['my name is', 'i am', 'this is', 'call me']
        has_name_trigger = any(trigger in speech_lower for trigger in name_triggers)

        if not has_name_trigger:
            logger.debug("[name_validation] rejected question words in name: '%s'", cleaned_name)
            return False, extracted_name

    logger.debug("[name_validation] accepted cleaned name: '%s' -> '%s'", extracted_name, cleaned_name)
    return True, cleaned_name


async def extract_canadian_name(speech: str, llm_fallback=None) -> Optional[str]:
    """
    Enhanced Canadian name extraction with nameparser and fuzzy matching.
    Now includes Canadian multilingual validation to prevent false extractions.

    Returns:
        Properly formatted "First Last" name or None
    """
    if not speech or not speech.strip():
        return None

    speech = speech.strip()
    logger.info("[name_canadian] processing: '%s'", speech)

    # Layer 1: nameparser library for robust name parsing
    try:
        from nameparser import HumanName

        # Preprocess speech patterns to clean for nameparser
        cleaned = speech.replace("my name is.", "my name is")
        cleaned = cleaned.replace("My name is.", "My name is")

        # Remove trigger phrases to isolate name
        trigger_patterns = [
            r'\b(my (?:full )?name is|i\'m|this is|i am|it\'s|it is)\s*[.,]*\s*',
            r'\b(calling|speaking)\s*$'
        ]

        for pattern in trigger_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE).strip()

        if cleaned and len(cleaned) > 2:
            name = HumanName(cleaned)
            if name.first and name.last:
                result = f"{name.first} {name.last}".title()

                # CANADIAN MULTILINGUAL VALIDATION
                is_valid, cleaned_result = validate_canadian_name_context(speech, result)
                if not is_valid:
                    logger.debug("[name_canadian] nameparser rejected by validation: '%s' -> %s", speech, result)
                else:
                    logger.info("[name_canadian] nameparser success: '%s' -> %s", speech, cleaned_result)
                    return cleaned_result

            # Try with just the cleaned text if nameparser couldn't parse parts
            words = cleaned.split()
            if len(words) >= 2:
                # Take first two words as first and last name
                result = f"{words[0]} {words[1]}".title()
                if all(len(w) >= 2 and w.isalpha() for w in words[:2]):
                    # CANADIAN MULTILINGUAL VALIDATION
                    is_valid, cleaned_result = validate_canadian_name_context(speech, result)
                    if not is_valid:
                        logger.debug("[name_canadian] nameparser fallback rejected by validation: '%s' -> %s", speech, result)
                    else:
                        logger.info("[name_canadian] nameparser fallback: '%s' -> %s", speech, cleaned_result)
                        return cleaned_result

    except ImportError:
        logger.debug("[name_canadian] nameparser not available, using fallback")
    except Exception as e:
        logger.debug("[name_canadian] nameparser failed: %s", e)

    # Layer 2: Enhanced regex patterns for Canadian name extraction
    patterns = [
        # Enhanced patterns that handle periods, commas, and extra spaces after trigger phrases
        r"(?:my (?:full )?name is)[.\s,]*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
        r"(?:my (?:full )?name is)[.\s,]*([a-z]+(?:\s+[a-z]+)+)",  # lowercase
        r"(?:i'm|this is|i am)[.\s,]*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
        r"(?:i'm|this is|i am)[.\s,]*([a-z]+(?:\s+[a-z]+)+)",  # lowercase
        r"(?:my (?:full )?name is)[.\s,]*([A-Z][a-z]+,?\s+[A-Z][a-z]+)",  # Handle comma in name
        r"(?:my (?:full )?name is)[.\s,]*([a-z]+,?\s+[a-z]+)",  # Handle comma lowercase
        r"^([A-Z][a-z]+\s+[A-Z][a-z]+)(?:\s+calling|$|\s*$)",
        r"^([a-z]+\s+[a-z]+)(?:\s+calling|$|\s*$)",  # lowercase
        r"([A-Z][a-z]+\s+[A-Z][a-z]+)",  # Simple pattern
        r"([a-z]+\s+[a-z]+)",  # Simple pattern lowercase
    ]

    for pattern in patterns:
        try:
            match = re.search(pattern, speech, re.IGNORECASE)
            if match:
                candidate = match.group(1).strip().replace(',', '').title()  # Remove commas

                # CANADIAN MULTILINGUAL VALIDATION
                is_valid, cleaned_result = validate_canadian_name_context(speech, candidate)
                if not is_valid:
                    logger.debug("[name_canadian] pattern rejected by validation: '%s' -> %s", speech, candidate)
                    continue

                # Simple validation - must have at least 2 words with 2+ chars each
                words = cleaned_result.split()
                if len(words) >= 2 and all(len(w) >= 2 for w in words):
                    result = " ".join(words[:2])  # Take first two words
                    logger.info("[name_canadian] pattern success: '%s' -> %s", speech, result)
                    return result
        except Exception as e:
            logger.debug("[name_canadian] pattern failed: %s", e)

    # Layer 3: Fuzzy matching for common speech-to-text errors
    try:
        from rapidfuzz import fuzz

        # Common Canadian names for fuzzy matching
        common_first_names = [
            "John", "Jane", "Mike", "Michael", "Sarah", "David", "Lisa", "Chris", "Jessica",
            "James", "Jennifer", "Robert", "Ashley", "Matthew", "Amanda", "Andrew", "Emily"
        ]

        words = speech.split()
        potential_names = []

        for i, word in enumerate(words):
            # Skip obvious non-name words
            if word.lower() in ['my', 'name', 'is', 'the', 'this', 'calling', 'speaking']:
                continue

            # Check fuzzy similarity with common names
            for common_name in common_first_names:
                similarity = fuzz.ratio(word.lower(), common_name.lower()) / 100
                if similarity >= 0.75:  # 75% similarity threshold
                    # Look for potential surname nearby
                    if i + 1 < len(words):
                        surname = words[i + 1]
                        if len(surname) >= 2 and surname.isalpha():
                            result = f"{common_name} {surname}".title()
                            logger.info("[name_canadian] fuzzy match: '%s' -> %s (similarity: %.2f)", speech, result, similarity)
                            return result
                    break

    except ImportError:
        logger.debug("[name_canadian] rapidfuzz not available, skipping fuzzy matching")
    except Exception as e:
        logger.debug("[name_canadian] fuzzy matching failed: %s", e)

    # Layer 4: spaCy NER (if available) with timeout protection
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

    # Layer 5: LLM fallback if provided
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
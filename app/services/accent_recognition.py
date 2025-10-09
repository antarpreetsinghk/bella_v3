# app/services/accent_recognition.py
"""
Accent-aware speech recognition for Red Deer's diverse English-speaking community.
Handles Filipino, Ukrainian, German, Indigenous, Asian, and European accents.
"""
import re
import logging
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class AccentVariation:
    """Represents common accent pronunciation variations."""
    original: str
    variations: List[str]
    confidence: float = 0.8

class RedDeerAccentProcessor:
    """
    Processes speech with awareness of Red Deer's diverse accent patterns.
    Optimized for common accent groups in Alberta.
    """

    def __init__(self):
        # Common phonetic substitutions by accent group
        self.accent_patterns = {
            # Asian accents (Filipino, Chinese, Korean, etc.)
            "asian": [
                AccentVariation("th", ["d", "t"], 0.9),  # "think" → "dink"
                AccentVariation("r", ["l"], 0.8),        # "Robert" → "Lobert"
                AccentVariation("v", ["w", "b"], 0.8),   # "David" → "Dawid"
                AccentVariation("f", ["p"], 0.7),        # "Philip" → "Prilip"
            ],

            # European accents (Ukrainian, German, Dutch, etc.)
            "european": [
                AccentVariation("w", ["v"], 0.9),        # "William" → "Villiam"
                AccentVariation("th", ["z", "s"], 0.8),  # "this" → "zis"
                AccentVariation("j", ["y"], 0.8),        # "John" → "Yohn"
                AccentVariation("ch", ["sh"], 0.7),      # "Charles" → "Sharles"
            ],

            # Indigenous Canadian accents
            "indigenous": [
                AccentVariation("th", ["d"], 0.8),       # Common substitution
                AccentVariation("r", [""], 0.7),         # R-dropping in some dialects
            ],

            # General non-native patterns
            "general": [
                AccentVariation("ing", ["een", "ink"], 0.8),  # "running" → "runeen"
                AccentVariation("er", ["ar", "or"], 0.7),     # "Peter" → "Petar"
            ]
        }

        # Common name patterns in Red Deer
        self.cultural_names = {
            "filipino": ["Maria", "Jose", "Ana", "Juan", "Rosa", "Carlos", "Elena"],
            "ukrainian": ["Oleksandr", "Oksana", "Viktor", "Natalia", "Andriy", "Iryna"],
            "german": ["Hans", "Greta", "Klaus", "Ingrid", "Stefan", "Monika"],
            "indigenous": ["Joseph", "Mary", "Robert", "Sarah", "David", "Lisa"],
            "asian": ["Chen", "Wong", "Singh", "Patel", "Kim", "Nguyen", "Li"]
        }

    def extract_accent_aware_name(self, speech: str) -> Optional[str]:
        """
        Extract names with accent-aware phonetic matching.

        Args:
            speech: Raw speech text from Twilio

        Returns:
            Best guess at the intended name, or None if unclear
        """
        if not speech or not speech.strip():
            return None

        speech = speech.strip()
        logger.info("[accent_name] processing: '%s'", speech)

        # Step 1: Try standard extraction first
        standard_name = self._extract_standard_name(speech)
        if self._is_valid_name(standard_name):
            logger.info("[accent_name] standard extraction worked: '%s'", standard_name)
            return standard_name

        # Step 2: Apply accent-aware corrections
        corrected_speech = self._apply_accent_corrections(speech)
        if corrected_speech != speech:
            logger.info("[accent_name] trying accent corrections: '%s' → '%s'", speech, corrected_speech)
            corrected_name = self._extract_standard_name(corrected_speech)
            if self._is_valid_name(corrected_name):
                return corrected_name

        # Step 3: Phonetic similarity matching
        phonetic_name = self._phonetic_name_match(speech)
        if phonetic_name:
            logger.info("[accent_name] phonetic match found: '%s'", phonetic_name)
            return phonetic_name

        # Step 4: Cultural name matching
        cultural_name = self._cultural_name_match(speech)
        if cultural_name:
            logger.info("[accent_name] cultural match found: '%s'", cultural_name)
            return cultural_name

        logger.info("[accent_name] no clear name extracted from: '%s'", speech)
        return None

    def _extract_standard_name(self, speech: str) -> Optional[str]:
        """Standard name extraction patterns."""
        text_lower = speech.lower()

        # Standard name introduction patterns
        patterns = [
            r'\bmy name is\s+(.+?)(?:\.|$)',
            r'\bi am\s+(.+?)(?:\.|$)',
            r'\bthis is\s+(.+?)(?:\.|$)',
            r'\bcall me\s+(.+?)(?:\.|$)',
            r'\bi\'m\s+(.+?)(?:\.|$)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                name_part = match.group(1).strip()
                cleaned = self._clean_name_text(name_part)
                if cleaned:
                    return cleaned

        # Direct name extraction (no intro phrase)
        cleaned_direct = self._clean_name_text(speech)
        return cleaned_direct if self._is_valid_name(cleaned_direct) else None

    def _clean_name_text(self, text: str) -> str:
        """Clean and format name text."""
        if not text:
            return ""

        # Remove punctuation and extra spaces
        text = re.sub(r'[.,;:!?\s]+$', '', text)
        text = re.sub(r'^[.,;:!?\s]+', '', text)
        text = re.sub(r'\s+', ' ', text)

        # Split into words and capitalize properly
        words = text.split()
        clean_words = []

        for word in words[:3]:  # Limit to 3 words for full names
            # Keep only alphabetic characters (including Unicode)
            clean_word = re.sub(r"[^a-zA-ZÀ-ÿĀ-žА-я\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff'\-]", "", word)
            if len(clean_word) >= 2:  # Minimum 2 characters
                clean_words.append(clean_word.capitalize())

        return " ".join(clean_words)

    def _is_valid_name(self, name: str) -> bool:
        """Check if extracted text looks like a valid name."""
        if not name or len(name.strip()) < 2:
            return False

        words = name.split()
        if len(words) > 4:  # Too many words
            return False

        # Check for non-name patterns
        lower_name = name.lower()
        bad_patterns = [
            "yes", "no", "okay", "hello", "hi", "appointment",
            "book", "time", "um", "uh", "what", "how"
        ]

        if any(bad in lower_name for bad in bad_patterns):
            return False

        # Must contain mostly alphabetic characters
        alpha_ratio = sum(c.isalpha() for c in name) / len(name)
        return alpha_ratio > 0.7

    def _apply_accent_corrections(self, speech: str) -> str:
        """Apply common accent corrections to improve recognition."""
        corrected = speech.lower()

        # Apply all accent patterns
        for accent_group, patterns in self.accent_patterns.items():
            for pattern in patterns:
                for variation in pattern.variations:
                    # Replace variation with original
                    corrected = corrected.replace(variation, pattern.original)

        return corrected.title()

    def _phonetic_name_match(self, speech: str) -> Optional[str]:
        """Match against phonetically similar common names."""
        speech_lower = speech.lower()

        # Common phonetic name mappings for accents
        phonetic_names = {
            # Asian accent variations
            "lobert": "Robert", "lichald": "Richard", "dawid": "David",
            "mary": "Mary", "marlene": "Marlene", "micheal": "Michael",

            # European accent variations
            "villiam": "William", "yohn": "John", "sharles": "Charles",
            "katarina": "Catherine", "nikolai": "Nicholas",

            # Common mispronunciations
            "steven": "Stephen", "katherine": "Catherine", "cristopher": "Christopher"
        }

        # Check for direct matches
        for variant, correct in phonetic_names.items():
            if variant in speech_lower:
                return correct

        return None

    def _cultural_name_match(self, speech: str) -> Optional[str]:
        """Match against common cultural names in Red Deer."""
        speech_lower = speech.lower()

        # Check all cultural name lists
        for culture, names in self.cultural_names.items():
            for name in names:
                # Simple substring matching for now
                if name.lower() in speech_lower:
                    return name

        return None

    def extract_accent_aware_phone(self, speech: str) -> Optional[str]:
        """
        Extract phone numbers with accent-aware digit recognition.
        Handles common digit pronunciation variations.
        """
        if not speech:
            return None

        logger.info("[accent_phone] processing: '%s'", speech)

        # Step 1: Standard phone extraction
        from app.services.simple_extraction import extract_phone_simple
        standard_phone = extract_phone_simple(speech)
        if standard_phone:
            return standard_phone

        # Step 2: Accent-aware digit mapping
        digit_variations = {
            # Asian accent patterns
            "tree": "3", "sree": "3", "twee": "2",
            "vive": "5", "vour": "4", "sero": "0",
            "vun": "1", "ate": "8",

            # European accent patterns
            "zree": "3", "zeven": "7", "nein": "9",
            "fife": "5", "vour": "4",

            # General variations
            "oh": "0", "zero": "0", "nought": "0",
            "won": "1", "too": "2", "fore": "4",
            "fife": "5", "sex": "6", "ate": "8", "niner": "9"
        }

        # Replace digit words with numbers
        corrected_speech = speech.lower()
        for word, digit in digit_variations.items():
            corrected_speech = corrected_speech.replace(word, digit)

        # Try extraction again with corrected speech
        return extract_phone_simple(corrected_speech)

# Global instance for use in routes
accent_processor = RedDeerAccentProcessor()
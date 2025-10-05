"""
Appointment Information Extractor
Integrates with existing Canadian extraction and LLM services
"""

import logging
from datetime import datetime
from typing import Dict, Optional
import phonenumbers
from phonenumbers import PhoneNumberFormat

logger = logging.getLogger(__name__)

class AppointmentExtractor:
    def __init__(self):
        pass

    async def extract_appointment_info(self, text: str) -> Dict:
        """
        Extract appointment information from speech text
        Uses existing Canadian extraction and LLM services
        """
        result = {
            'original_text': text,
            'datetime': None,
            'duration': 30,  # default
            'name': None,
            'phone': None,
            'is_valid': False
        }

        try:
            # Use existing Canadian extraction services
            from app.services.canadian_extraction import (
                extract_canadian_name,
                extract_canadian_phone,
                extract_canadian_time
            )

            # Extract name using existing service
            result['name'] = await extract_canadian_name(text)

            # Extract phone using existing service
            result['phone'] = await extract_canadian_phone(text)

            # Extract datetime using existing service
            result['datetime'] = await extract_canadian_time(text)

            # Check if extraction was successful
            if result['datetime']:
                result['is_valid'] = True

            # Extract duration keywords
            if 'hour' in text.lower():
                result['duration'] = 60
            elif 'forty' in text.lower() or '45' in text:
                result['duration'] = 45

        except ImportError as e:
            logger.warning(f"Canadian extraction service not available: {e}")
            # Fallback to basic extraction
            result = await self._basic_extraction(text)
        except Exception as e:
            logger.error(f"Appointment extraction failed: {e}")
            result = await self._basic_extraction(text)

        return result

    async def _basic_extraction(self, text: str) -> Dict:
        """Basic fallback extraction without advanced services"""
        result = {
            'original_text': text,
            'datetime': None,
            'duration': 30,
            'name': None,
            'phone': None,
            'is_valid': False
        }

        try:
            # Try to use existing LLM service if available
            from app.services.llm import extract_appointment_fields

            llm_result = await extract_appointment_fields(text)
            if isinstance(llm_result, dict):
                result.update(llm_result)
                if result.get('datetime'):
                    result['is_valid'] = True

        except ImportError:
            logger.info("LLM service not available, using basic parsing")
            # Very basic parsing as last resort
            result['name'] = self._extract_name_basic(text)
            result['phone'] = self._extract_phone_basic(text)

        return result

    def _extract_name_basic(self, text: str) -> Optional[str]:
        """Basic name extraction"""
        import re

        # Look for "my name is" or "I'm" patterns
        patterns = [
            r'\bmy name is ([A-Za-z\s]+)',
            r'\bi\'?m ([A-Za-z\s]+)',
            r'\bthis is ([A-Za-z\s]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip().title()
                if len(name) > 1 and name.replace(' ', '').isalpha():
                    return name

        return None

    def _extract_phone_basic(self, text: str) -> Optional[str]:
        """Basic phone extraction"""
        import re

        # Remove common speech-to-text artifacts
        cleaned = re.sub(r'[^\d\s\-\(\)\.]+', '', text)

        phone_patterns = [
            r'\b(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})\b',
            r'\b(\(\d{3}\)\s?\d{3}[-.\s]?\d{4})\b',
        ]

        for pattern in phone_patterns:
            match = re.search(pattern, cleaned)
            if match:
                try:
                    parsed = phonenumbers.parse(match.group(1), "US")
                    if phonenumbers.is_valid_number(parsed):
                        return phonenumbers.format_number(parsed, PhoneNumberFormat.E164)
                except:
                    continue

        return None
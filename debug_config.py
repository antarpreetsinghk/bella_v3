#!/usr/bin/env python3
"""
Debug configuration loading for Google Calendar.
"""

import sys
import os

# Add app to Python path
sys.path.append('/home/antarpreet/Projects/bella_v3')

from dotenv import load_dotenv
from app.utils.secrets import get_config_value

# Load environment variables
load_dotenv()

def debug_config():
    """Debug the configuration loading"""
    print("🔍 Debug Configuration Loading")
    print("=" * 40)

    # Check direct environment variable access
    print(f"Direct os.getenv('GOOGLE_CALENDAR_ID'): {os.getenv('GOOGLE_CALENDAR_ID')}")

    # Check via utils function
    calendar_id = get_config_value("GOOGLE_CALENDAR_ID", "primary")
    print(f"get_config_value('GOOGLE_CALENDAR_ID', 'primary'): {calendar_id}")

    # Check other related configs
    print(f"GOOGLE_CALENDAR_ENABLED: {get_config_value('GOOGLE_CALENDAR_ENABLED')}")
    print(f"BUSINESS_EMAIL: {get_config_value('BUSINESS_EMAIL')}")

    # Show calendar ID type and length
    if calendar_id:
        print(f"Calendar ID type: {type(calendar_id)}")
        print(f"Calendar ID length: {len(calendar_id)}")
        print(f"Is it 'primary'?: {calendar_id == 'primary'}")
        print(f"Calendar ID preview: {calendar_id[:50]}...")

if __name__ == "__main__":
    debug_config()
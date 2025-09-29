#!/usr/bin/env python3
"""
Google Calendar integration setup helper.
Creates service account and provides setup instructions.
"""

import json
import os
import sys
from pathlib import Path

def create_sample_service_account():
    """Create a sample service account JSON template"""
    sample_account = {
        "type": "service_account",
        "project_id": "bella-voice-booking",
        "private_key_id": "YOUR_PRIVATE_KEY_ID",
        "private_key": "-----BEGIN PRIVATE KEY-----\nYOUR_PRIVATE_KEY_HERE\n-----END PRIVATE KEY-----\n",
        "client_email": "bella-calendar@bella-voice-booking.iam.gserviceaccount.com",
        "client_id": "YOUR_CLIENT_ID",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/bella-calendar%40bella-voice-booking.iam.gserviceaccount.com"
    }

    return json.dumps(sample_account, indent=2)

def setup_instructions():
    """Print setup instructions"""
    print("""
🔧 GOOGLE CALENDAR SETUP INSTRUCTIONS
=====================================

1. CREATE GOOGLE CLOUD PROJECT:
   - Go to https://console.cloud.google.com/
   - Create new project: "bella-voice-booking"
   - Enable Google Calendar API

2. CREATE SERVICE ACCOUNT:
   - Go to IAM & Admin > Service Accounts
   - Click "Create Service Account"
   - Name: "bella-calendar"
   - Role: "Editor" (or custom role with calendar access)

3. GENERATE SERVICE ACCOUNT KEY:
   - Click on the created service account
   - Go to "Keys" tab
   - Click "Add Key" > "Create new key" > "JSON"
   - Download the JSON file

4. SHARE CALENDAR:
   - In Google Calendar, go to calendar settings
   - Share with service account email: bella-calendar@bella-voice-booking.iam.gserviceaccount.com
   - Grant "Make changes to events" permission

5. SET ENVIRONMENT VARIABLES:
   export GOOGLE_CALENDAR_ENABLED=true
   export GOOGLE_SERVICE_ACCOUNT_JSON='[paste downloaded JSON here]'
   export GOOGLE_CALENDAR_ID=your-calendar-id
   export BUSINESS_EMAIL=your-business@email.com

6. RESTART THE SERVICE:
   # The integration will automatically start working
   # Bookings will create calendar events seamlessly

🧪 TEST THE INTEGRATION:
   python test_google_calendar.py --setup

📋 SAMPLE SERVICE ACCOUNT JSON TEMPLATE:
""")

    print(create_sample_service_account())

    print("""

⚡ PRODUCTION DEPLOYMENT:
   - Add these environment variables to your AWS ECS task definition
   - Or set them in your deployment secrets
   - Integration is non-blocking: bookings work with or without calendar
""")

if __name__ == "__main__":
    setup_instructions()
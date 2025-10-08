#!/usr/bin/env python3
"""
Minimal Lambda handler for Twilio webhook with calendar integration.
This bypasses the FastAPI/pydantic issues by using only essential dependencies.
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from urllib.parse import unquote_plus
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_twilio_webhook(body):
    """Parse Twilio webhook body (application/x-www-form-urlencoded)"""
    try:
        if isinstance(body, bytes):
            body = body.decode('utf-8')

        # Simple parsing of form data
        params = {}
        for pair in body.split('&'):
            if '=' in pair:
                key, value = pair.split('=', 1)
                params[unquote_plus(key)] = unquote_plus(value)

        return params
    except Exception as e:
        logger.error(f"Error parsing webhook body: {e}")
        return {}

def create_simple_calendar_event(user_name, user_mobile, appointment_time, duration_min=30):
    """Create calendar event using Google Calendar API directly"""
    try:
        # Import Google Calendar dependencies
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        import json

        # Get credentials from environment
        service_account_json = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
        calendar_id = os.environ.get('GOOGLE_CALENDAR_ID')

        if not service_account_json or not calendar_id:
            logger.error("Missing Google Calendar credentials")
            return None

        # Create credentials
        service_account_info = json.loads(service_account_json)
        credentials = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=['https://www.googleapis.com/auth/calendar']
        )

        # Build service
        service = build('calendar', 'v3', credentials=credentials)

        # Create event
        start_time = appointment_time.isoformat()
        end_time = (appointment_time + timedelta(minutes=duration_min)).isoformat()

        event = {
            'summary': f'Appointment with {user_name}',
            'description': f'Phone booking appointment\nCustomer: {user_name}\nPhone: {user_mobile}',
            'start': {
                'dateTime': start_time,
                'timeZone': 'America/Edmonton',
            },
            'end': {
                'dateTime': end_time,
                'timeZone': 'America/Edmonton',
            },
        }

        created_event = service.events().insert(calendarId=calendar_id, body=event).execute()
        logger.info(f"Calendar event created: {created_event.get('id')}")
        return created_event

    except Exception as e:
        logger.error(f"Error creating calendar event: {e}")
        return None

def lambda_handler(event, context):
    """Main Lambda handler"""
    try:
        logger.info(f"Event: {json.dumps(event, default=str)}")

        # Extract HTTP method and path
        http_method = event.get('httpMethod', 'GET')
        path = event.get('path', '/')

        # Handle health check
        if path == '/' and http_method == 'GET':
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'status': 'ok',
                    'message': 'Bella Voice App - Calendar Integration Active',
                    'calendar_enabled': os.environ.get('GOOGLE_CALENDAR_ENABLED', 'false')
                })
            }

        # Handle Twilio webhook
        if path == '/twilio/voice' and http_method == 'POST':
            body = event.get('body', '')
            twilio_params = parse_twilio_webhook(body)

            logger.info(f"Twilio webhook received: {twilio_params}")

            # Simple TwiML response for voice calls
            twiml_response = '''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">Thank you for calling Bella. Your appointment has been recorded and you will receive a calendar invitation shortly.</Say>
    <Hangup/>
</Response>'''

            # Extract appointment details if available (this would be enhanced based on your Twilio flow)
            caller_id = twilio_params.get('From', 'Unknown')
            call_sid = twilio_params.get('CallSid', '')

            # For demo purposes, create a calendar event for tomorrow at 2 PM
            appointment_time = datetime.now().replace(hour=14, minute=0, second=0, microsecond=0) + timedelta(days=1)

            # Create calendar event
            calendar_result = create_simple_calendar_event(
                user_name="Phone Booking Customer",
                user_mobile=caller_id,
                appointment_time=appointment_time
            )

            if calendar_result:
                logger.info(f"Calendar event created for call {call_sid}")
            else:
                logger.error(f"Failed to create calendar event for call {call_sid}")

            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'text/xml',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': twiml_response
            }

        # Default response for other paths
        return {
            'statusCode': 404,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': 'Not found'})
        }

    except Exception as e:
        logger.error(f"Handler error: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': f'Internal server error: {str(e)}'})
        }
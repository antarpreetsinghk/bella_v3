#!/usr/bin/env python3
"""
Get list of available calendars for the service account
"""
import os
import sys
from dotenv import load_dotenv
load_dotenv()

sys.path.append('/home/antarpreet/Projects/bella_v3')
from app.services.google_calendar import get_calendar_service

def list_calendars():
    """List all calendars accessible to the service account"""
    service = get_calendar_service()
    if not service:
        print("❌ Google Calendar service not available")
        return

    try:
        print("📅 Available Calendars:")
        print("=" * 50)

        calendar_list = service.calendarList().list().execute()
        calendars = calendar_list.get('items', [])

        if not calendars:
            print("No calendars found.")
        else:
            for calendar in calendars:
                cal_id = calendar['id']
                summary = calendar.get('summary', 'No title')
                access_role = calendar.get('accessRole', 'Unknown')

                print(f"📋 {summary}")
                print(f"   ID: {cal_id}")
                print(f"   Access: {access_role}")
                print()

    except Exception as e:
        print(f"❌ Error listing calendars: {e}")

if __name__ == "__main__":
    list_calendars()
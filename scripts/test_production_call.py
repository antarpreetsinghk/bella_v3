#!/usr/bin/env python3
"""
Production Test Call Script
Makes a single test call to production to verify logging and appointment creation.

This script simulates a complete voice call flow and allows you to monitor
production logs to verify:
- Voice webhook processing
- Name/phone/time extraction
- Appointment creation
- Database insertion (is_test_data=true)
- Google Calendar sync

Usage:
    python scripts/test_production_call.py [--url URL] [--api-key KEY]
"""

import asyncio
import httpx
import sys
import os
from datetime import datetime, timedelta, timezone
import time

# Configuration
PRODUCTION_URL = os.getenv("PRODUCTION_TEST_URL", "http://15.157.56.64")
API_KEY = os.getenv("PRODUCTION_API_KEY", "tq6fJVZgqGchLcJ4yHdlQx3hl4eDaf9QgTvfUjGVWnMKiZqEKCaJUYSd1SYb79WI")
TIMEOUT = 30

# Color codes
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
CYAN = '\033[0;36m'
NC = '\033[0m'  # No Color


def print_header(text):
    """Print colored header"""
    print(f"\n{BLUE}{'='*70}{NC}")
    print(f"{BLUE}  {text}{NC}")
    print(f"{BLUE}{'='*70}{NC}\n")


def print_step(step_num, total, text):
    """Print step progress"""
    print(f"{CYAN}[Step {step_num}/{total}]{NC} {text}")


def print_success(text):
    """Print success message"""
    print(f"{GREEN}✅ {text}{NC}")


def print_error(text):
    """Print error message"""
    print(f"{RED}❌ {text}{NC}")


def print_info(text):
    """Print info message"""
    print(f"{YELLOW}ℹ️  {text}{NC}")


async def make_test_call():
    """Execute a complete test call flow"""

    # Generate unique test identifiers
    timestamp = int(time.time())
    call_sid = f"TEST_CALL_{timestamp}"
    test_phone = f"+1416555{str(timestamp % 10000).zfill(4)}"
    test_name = f"Test User {timestamp % 1000}"

    # Calculate appointment time (tomorrow at 2 PM)
    tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
    appointment_time = tomorrow.replace(hour=20, minute=0, second=0, microsecond=0)  # 2 PM MST = 20:00 UTC

    print_header("Production Test Call - Log Verification")

    print(f"Production URL: {PRODUCTION_URL}")
    print(f"Call SID:       {call_sid}")
    print(f"Test Phone:     {test_phone}")
    print(f"Test Name:      {test_name}")
    print(f"Appointment:    {appointment_time.strftime('%Y-%m-%d %H:%M UTC')}")
    print()

    print_info("⚠️  IMPORTANT: Open a separate terminal and run:")
    print(f"    ssh user@15.157.56.64 \"docker logs -f bella_app 2>&1 | grep -iE 'appointment|{call_sid}'\"")
    print()
    input(f"{YELLOW}Press ENTER when you're ready to start monitoring...{NC}")

    print_header("Executing Test Call Flow")

    steps = [
        ("Initial call webhook", {"CallSid": call_sid, "From": test_phone, "To": "+14165551234", "CallStatus": "in-progress"}),
        ("Provide name", {"CallSid": call_sid, "SpeechResult": test_name, "Confidence": "0.95"}),
        ("Confirm name (Yes)", {"CallSid": call_sid, "SpeechResult": "yes", "Confidence": "0.98"}),
        ("Provide appointment time", {"CallSid": call_sid, "SpeechResult": "tomorrow at 2 PM", "Confidence": "0.92"}),
        ("Confirm booking (Yes)", {"CallSid": call_sid, "SpeechResult": "yes", "Confidence": "0.99"}),
    ]

    total_steps = len(steps)

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        for i, (description, payload) in enumerate(steps, 1):
            print_step(i, total_steps, description)

            # Add API key header
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            if API_KEY:
                headers["X-API-Key"] = API_KEY

            try:
                start_time = time.time()
                response = await client.post(
                    f"{PRODUCTION_URL}/twilio/voice",
                    headers=headers,
                    data=payload
                )
                duration = time.time() - start_time

                if response.status_code == 200:
                    print_success(f"Response received in {duration:.2f}s (Status: {response.status_code})")

                    # Show response preview
                    content = response.text[:200]
                    if "Say" in content:
                        # Extract what the system said
                        import re
                        say_match = re.search(r'<Say[^>]*>([^<]+)</Say>', content)
                        if say_match:
                            print(f"    System said: \"{say_match.group(1)[:100]}...\"")
                else:
                    print_error(f"Unexpected status code: {response.status_code}")
                    print(f"    Response: {response.text[:200]}")
                    return False

                # Brief pause between steps
                if i < total_steps:
                    await asyncio.sleep(0.5)

            except httpx.TimeoutException:
                print_error(f"Request timeout after {TIMEOUT}s")
                return False
            except Exception as e:
                print_error(f"Request failed: {e}")
                return False

    print_header("Test Call Completed Successfully")

    print_info("Now check your production logs for:")
    print(f"  1. Call processing: grep '{call_sid}'")
    print(f"  2. Name extraction: grep '{test_name}'")
    print(f"  3. Phone extraction: grep '{test_phone}'")
    print(f"  4. Appointment creation: grep 'appointment created'")
    print(f"  5. Test data flag: grep 'is_test_data=true'")
    print(f"  6. Database insert: grep 'INSERT INTO appointments'")
    print(f"  7. Google Calendar: grep 'google_event_id'")
    print()

    print_header("Database Verification")
    print_info("To verify in production database (SSH into server):")
    print()
    print(f"  docker exec -it bella_db psql -U bella_user -d bella_db -c \\")
    print(f"    \"SELECT id, user_id, starts_at, is_test_data, google_event_id \\")
    print(f"     FROM appointments \\")
    print(f"     WHERE created_at > NOW() - INTERVAL '5 minutes' \\")
    print(f"     ORDER BY created_at DESC LIMIT 5;\"")
    print()

    print_header("Cleanup Commands")
    print_info("To cleanup this test appointment:")
    print()
    print(f"  # Using cleanup utility (dry-run first)")
    print(f"  python tests/production/cleanup.py cleanup --older-than=0 --db-url=<PROD_DB_URL>")
    print()
    print(f"  # Or manual SQL")
    print(f"  DELETE FROM appointments WHERE is_test_data = true AND created_at > NOW() - INTERVAL '10 minutes';")
    print()

    return True


async def main():
    """Main entry point"""
    import argparse

    global PRODUCTION_URL, API_KEY

    parser = argparse.ArgumentParser(description="Production test call for log verification")
    parser.add_argument("--url", help="Production URL", default=PRODUCTION_URL)
    parser.add_argument("--api-key", help="API key", default=API_KEY)
    args = parser.parse_args()

    PRODUCTION_URL = args.url
    API_KEY = args.api_key

    try:
        success = await make_test_call()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print_error("\nTest call interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

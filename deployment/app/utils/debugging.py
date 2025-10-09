"""
Call Flow Debugging Utilities
Integrates with existing logging and metrics systems
"""

import json
import functools
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
import logging

# Ensure logs directory exists
Path("logs/calls").mkdir(parents=True, exist_ok=True)

logger = logging.getLogger(__name__)

class CallLogger:
    def __init__(self):
        self.log_file = Path("logs/calls") / f"calls_{datetime.now().strftime('%Y-%m-%d')}.jsonl"

    async def log_call_event(self, call_sid: str, event_type: str, data: Any):
        """Log call events to JSONL file"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "call_sid": call_sid,
            "event_type": event_type,
            "data": data
        }

        try:
            # Integrate with existing business metrics if available
            from app.services.business_metrics import business_metrics
            await business_metrics.track_call_event(call_sid, event_type, data)
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"Failed to track business metrics: {e}")

        # Write to log file
        try:
            with open(self.log_file, "a") as f:
                f.write(json.dumps(log_entry, default=str) + "\n")
        except Exception as e:
            logger.error(f"Failed to write call log: {e}")

def debug_call_flow(step_name: str):
    """Decorator to debug call flow steps"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            call_logger = CallLogger()
            start_time = datetime.now()

            # Extract call_sid from various possible locations
            call_sid = kwargs.get('call_sid')
            if not call_sid and args:
                # Try to extract from first argument if it's a request-like object
                try:
                    if hasattr(args[0], 'form'):
                        form_data = await args[0].form() if asyncio.iscoroutine(args[0].form()) else args[0].form()
                        call_sid = form_data.get('CallSid', 'unknown')
                    elif hasattr(args[0], 'get'):
                        call_sid = args[0].get('CallSid', 'unknown')
                except:
                    call_sid = 'unknown'

            if not call_sid:
                call_sid = 'unknown'

            try:
                # Log step start
                await call_logger.log_call_event(
                    call_sid,
                    f"{step_name}_start",
                    {"args_count": len(args), "kwargs_keys": list(kwargs.keys())}
                )

                # Execute function
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)

                # Log step completion
                duration = (datetime.now() - start_time).total_seconds()
                await call_logger.log_call_event(
                    call_sid,
                    f"{step_name}_complete",
                    {"duration_seconds": duration, "success": True}
                )

                return result

            except Exception as e:
                # Log step error
                duration = (datetime.now() - start_time).total_seconds()
                await call_logger.log_call_event(
                    call_sid,
                    f"{step_name}_error",
                    {"duration_seconds": duration, "error": str(e), "success": False}
                )
                raise

        return wrapper
    return decorator

# Call flow analyzer
class CallFlowAnalyzer:
    @staticmethod
    def analyze_daily_calls(date: str = None) -> Dict[str, Any]:
        """Analyze call patterns for a specific date"""
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')

        log_file = Path("logs/calls") / f"calls_{date}.jsonl"

        if not log_file.exists():
            return {"error": "No call data for this date"}

        calls = {}
        with open(log_file, "r") as f:
            for line in f:
                try:
                    event = json.loads(line)
                    call_sid = event['call_sid']

                    if call_sid not in calls:
                        calls[call_sid] = {
                            "events": [],
                            "start_time": None,
                            "end_time": None,
                            "success": False,
                            "errors": []
                        }

                    calls[call_sid]["events"].append(event)

                    if event['event_type'] == 'call_started':
                        calls[call_sid]["start_time"] = event['timestamp']
                    elif 'error' in event['event_type']:
                        calls[call_sid]["errors"].append(event)
                    elif event['event_type'] == 'appointment_booked':
                        calls[call_sid]["success"] = True
                        calls[call_sid]["end_time"] = event['timestamp']

                except json.JSONDecodeError:
                    continue

        # Calculate statistics
        total_calls = len(calls)
        successful_bookings = sum(1 for call in calls.values() if call['success'])
        conversion_rate = (successful_bookings / total_calls * 100) if total_calls > 0 else 0

        return {
            "date": date,
            "total_calls": total_calls,
            "successful_bookings": successful_bookings,
            "conversion_rate": f"{conversion_rate:.1f}%",
            "calls": calls
        }
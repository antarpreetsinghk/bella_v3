#!/usr/bin/env python3
"""
Debug Helper Utilities for Production Troubleshooting
Comprehensive debugging tools for call flow analysis
"""

import json
import boto3
import logging
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import re
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class CallEvent:
    """Represents a single call event"""
    timestamp: str
    call_sid: str
    event_type: str
    message: str
    level: str
    details: Dict[str, Any] = None


@dataclass
class CallTrace:
    """Complete call trace analysis"""
    call_sid: str
    start_time: str
    end_time: Optional[str]
    duration_seconds: Optional[float]
    events: List[CallEvent]
    errors: List[CallEvent]
    status: str
    summary: Dict[str, Any]


class DebugHelper:
    """Main debug utility class"""

    def __init__(self, region: str = "us-east-1"):
        self.region = region
        self.lambda_client = boto3.client('lambda', region_name=region)
        self.logs_client = boto3.client('logs', region_name=region)
        self.cloudwatch_client = boto3.client('cloudwatch', region_name=region)
        self.dynamodb_client = boto3.client('dynamodb', region_name=region)

        self.function_name = "bella-voice-app"
        self.log_group = f"/aws/lambda/{self.function_name}"
        self.session_table = "bella-voice-app-sessions"

    def get_call_trace(self, call_sid: str, hours_back: int = 24) -> CallTrace:
        """Get complete call trace for a specific CallSid"""
        logger.info(f"Fetching call trace for {call_sid}")

        # Calculate time range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours_back)

        try:
            # Fetch logs from CloudWatch
            response = self.logs_client.filter_log_events(
                logGroupName=self.log_group,
                startTime=int(start_time.timestamp() * 1000),
                endTime=int(end_time.timestamp() * 1000),
                filterPattern=f'"{call_sid}"'
            )

            events = []
            errors = []

            for event in response.get('events', []):
                message = event['message']
                timestamp = datetime.fromtimestamp(event['timestamp'] / 1000).isoformat()

                # Parse log level
                level = "INFO"
                if "ERROR" in message:
                    level = "ERROR"
                elif "WARNING" in message or "WARN" in message:
                    level = "WARNING"
                elif "DEBUG" in message:
                    level = "DEBUG"

                # Determine event type
                event_type = self._determine_event_type(message)

                call_event = CallEvent(
                    timestamp=timestamp,
                    call_sid=call_sid,
                    event_type=event_type,
                    message=message,
                    level=level,
                    details=self._extract_event_details(message)
                )

                events.append(call_event)

                if level == "ERROR":
                    errors.append(call_event)

            # Sort events by timestamp
            events.sort(key=lambda x: x.timestamp)

            # Calculate duration and status
            duration = None
            status = "UNKNOWN"

            if events:
                first_event = datetime.fromisoformat(events[0].timestamp)
                last_event = datetime.fromisoformat(events[-1].timestamp)
                duration = (last_event - first_event).total_seconds()

                if errors:
                    status = "ERROR"
                elif any("appointment booked" in e.message.lower() for e in events):
                    status = "SUCCESS"
                elif any("call ended" in e.message.lower() for e in events):
                    status = "COMPLETED"
                else:
                    status = "IN_PROGRESS"

            # Generate summary
            summary = self._generate_call_summary(events, errors)

            return CallTrace(
                call_sid=call_sid,
                start_time=events[0].timestamp if events else start_time.isoformat(),
                end_time=events[-1].timestamp if events else None,
                duration_seconds=duration,
                events=events,
                errors=errors,
                status=status,
                summary=summary
            )

        except Exception as e:
            logger.error(f"Failed to get call trace: {e}")
            raise

    def _determine_event_type(self, message: str) -> str:
        """Determine event type from log message"""
        message_lower = message.lower()

        if "twilio" in message_lower and "voice" in message_lower:
            return "VOICE_WEBHOOK"
        elif "extraction" in message_lower:
            return "EXTRACTION"
        elif "appointment" in message_lower:
            return "APPOINTMENT"
        elif "session" in message_lower:
            return "SESSION"
        elif "error" in message_lower:
            return "ERROR"
        elif "response" in message_lower:
            return "RESPONSE"
        else:
            return "GENERAL"

    def _extract_event_details(self, message: str) -> Dict[str, Any]:
        """Extract structured details from log message"""
        details = {}

        # Try to extract JSON from message
        json_match = re.search(r'\{.*\}', message)
        if json_match:
            try:
                details.update(json.loads(json_match.group()))
            except json.JSONDecodeError:
                pass

        # Extract common patterns
        phone_match = re.search(r'\+?1?(\d{10})', message)
        if phone_match:
            details['phone'] = phone_match.group()

        name_match = re.search(r'name.*?([A-Z][a-z]+ [A-Z][a-z]+)', message)
        if name_match:
            details['name'] = name_match.group(1)

        time_match = re.search(r'(\d{1,2}:\d{2}(?:\s*[APap][Mm])?)', message)
        if time_match:
            details['time'] = time_match.group(1)

        return details

    def _generate_call_summary(self, events: List[CallEvent], errors: List[CallEvent]) -> Dict[str, Any]:
        """Generate summary statistics for call trace"""
        summary = {
            "total_events": len(events),
            "error_count": len(errors),
            "event_types": {},
            "extracted_data": {},
            "response_times": [],
            "issues": []
        }

        # Count event types
        for event in events:
            event_type = event.event_type
            summary["event_types"][event_type] = summary["event_types"].get(event_type, 0) + 1

        # Extract key data
        for event in events:
            if event.details:
                for key, value in event.details.items():
                    if key in ['phone', 'name', 'time'] and value:
                        summary["extracted_data"][key] = value

        # Identify common issues
        if len(errors) > 3:
            summary["issues"].append("High error count")

        if summary["total_events"] > 50:
            summary["issues"].append("Excessive interactions (possible loop)")

        if not summary["extracted_data"]:
            summary["issues"].append("No data extracted")

        return summary

    def analyze_session_state(self, phone_or_call_sid: str) -> Dict[str, Any]:
        """Analyze current session state from DynamoDB"""
        logger.info(f"Analyzing session state for {phone_or_call_sid}")

        try:
            # Try as CallSid first
            response = self.dynamodb_client.get_item(
                TableName=self.session_table,
                Key={'call_sid': {'S': phone_or_call_sid}}
            )

            if 'Item' not in response:
                # If not found as CallSid, search by phone number
                # Note: This requires a GSI on phone number, which may not exist
                logger.warning(f"No session found for CallSid {phone_or_call_sid}")
                return {"status": "NOT_FOUND", "message": "No session data found"}

            item = response['Item']

            # Parse DynamoDB item
            session_data = {}
            for key, value in item.items():
                if 'S' in value:
                    session_data[key] = value['S']
                elif 'N' in value:
                    session_data[key] = float(value['N'])
                elif 'M' in value:
                    session_data[key] = self._parse_dynamodb_map(value['M'])

            # Add analysis
            analysis = {
                "session_data": session_data,
                "ttl_remaining": self._calculate_ttl_remaining(session_data.get('ttl')),
                "call_stage": self._determine_call_stage(session_data),
                "data_completeness": self._analyze_data_completeness(session_data),
                "recommendations": self._generate_session_recommendations(session_data)
            }

            return analysis

        except Exception as e:
            logger.error(f"Failed to analyze session state: {e}")
            return {"status": "ERROR", "message": str(e)}

    def _parse_dynamodb_map(self, dynamodb_map: Dict) -> Dict:
        """Parse DynamoDB map format to regular dict"""
        result = {}
        for key, value in dynamodb_map.items():
            if 'S' in value:
                result[key] = value['S']
            elif 'N' in value:
                result[key] = float(value['N'])
            elif 'BOOL' in value:
                result[key] = value['BOOL']
            # Add more type handling as needed
        return result

    def _calculate_ttl_remaining(self, ttl_timestamp: Optional[str]) -> Optional[int]:
        """Calculate TTL remaining in seconds"""
        if not ttl_timestamp:
            return None

        try:
            ttl_time = datetime.fromtimestamp(float(ttl_timestamp))
            remaining = (ttl_time - datetime.utcnow()).total_seconds()
            return max(0, int(remaining))
        except:
            return None

    def _determine_call_stage(self, session_data: Dict) -> str:
        """Determine what stage the call is in"""
        data = session_data.get('data', {})

        if isinstance(data, str):
            try:
                data = json.loads(data)
            except:
                data = {}

        if data.get('appointment_booked'):
            return "COMPLETED"
        elif data.get('time_confirmed'):
            return "BOOKING"
        elif data.get('time'):
            return "TIME_COLLECTION"
        elif data.get('phone'):
            return "PHONE_COLLECTION"
        elif data.get('name'):
            return "NAME_COLLECTION"
        else:
            return "INITIAL"

    def _analyze_data_completeness(self, session_data: Dict) -> Dict[str, Any]:
        """Analyze how complete the appointment data is"""
        data = session_data.get('data', {})

        if isinstance(data, str):
            try:
                data = json.loads(data)
            except:
                data = {}

        required_fields = ['name', 'phone', 'time']
        present_fields = [field for field in required_fields if data.get(field)]
        missing_fields = [field for field in required_fields if not data.get(field)]

        return {
            "completion_percentage": (len(present_fields) / len(required_fields)) * 100,
            "present_fields": present_fields,
            "missing_fields": missing_fields,
            "extracted_data": data
        }

    def _generate_session_recommendations(self, session_data: Dict) -> List[str]:
        """Generate recommendations based on session analysis"""
        recommendations = []

        data = session_data.get('data', {})
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except:
                data = {}

        # Check for stuck sessions
        ttl_remaining = self._calculate_ttl_remaining(session_data.get('ttl'))
        if ttl_remaining and ttl_remaining < 300:  # Less than 5 minutes
            recommendations.append("Session expiring soon - may need to restart")

        # Check for incomplete data
        if not data.get('name'):
            recommendations.append("Name not collected - check speech recognition")
        if not data.get('phone'):
            recommendations.append("Phone not collected - may need manual input")
        if not data.get('time'):
            recommendations.append("Time not collected - check time parsing")

        # Check for retry patterns
        retry_count = data.get('retry_count', 0)
        if retry_count > 3:
            recommendations.append("High retry count - consider alternative input method")

        if not recommendations:
            recommendations.append("Session appears healthy")

        return recommendations

    def get_recent_errors(self, hours_back: int = 1, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent errors from Lambda logs"""
        logger.info(f"Fetching recent errors (last {hours_back} hours)")

        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours_back)

        try:
            response = self.logs_client.filter_log_events(
                logGroupName=self.log_group,
                startTime=int(start_time.timestamp() * 1000),
                endTime=int(end_time.timestamp() * 1000),
                filterPattern="ERROR",
                limit=limit
            )

            errors = []
            for event in response.get('events', []):
                error_info = {
                    "timestamp": datetime.fromtimestamp(event['timestamp'] / 1000).isoformat(),
                    "message": event['message'],
                    "call_sid": self._extract_call_sid(event['message']),
                    "error_type": self._classify_error(event['message']),
                    "severity": self._assess_error_severity(event['message'])
                }
                errors.append(error_info)

            return errors

        except Exception as e:
            logger.error(f"Failed to get recent errors: {e}")
            raise

    def _extract_call_sid(self, message: str) -> Optional[str]:
        """Extract CallSid from log message"""
        # Look for Twilio CallSid pattern
        call_sid_match = re.search(r'CA[a-f0-9]{32}', message)
        if call_sid_match:
            return call_sid_match.group()

        # Look for test CallSid pattern
        test_call_match = re.search(r'TEST[_\w]*\d+', message)
        if test_call_match:
            return test_call_match.group()

        return None

    def _classify_error(self, message: str) -> str:
        """Classify error type from message"""
        message_lower = message.lower()

        if "timeout" in message_lower:
            return "TIMEOUT"
        elif "extraction" in message_lower:
            return "EXTRACTION_ERROR"
        elif "database" in message_lower or "dynamodb" in message_lower:
            return "DATABASE_ERROR"
        elif "api" in message_lower or "http" in message_lower:
            return "API_ERROR"
        elif "twilio" in message_lower:
            return "TWILIO_ERROR"
        elif "openai" in message_lower:
            return "OPENAI_ERROR"
        elif "calendar" in message_lower:
            return "CALENDAR_ERROR"
        else:
            return "UNKNOWN_ERROR"

    def _assess_error_severity(self, message: str) -> str:
        """Assess error severity"""
        message_lower = message.lower()

        # Critical errors that stop the call
        if any(word in message_lower for word in ["fatal", "critical", "crash", "exception"]):
            return "CRITICAL"

        # Errors that affect functionality
        if any(word in message_lower for word in ["failed", "error", "cannot", "unable"]):
            return "HIGH"

        # Warnings that might be recoverable
        if any(word in message_lower for word in ["warning", "retry", "fallback"]):
            return "MEDIUM"

        return "LOW"

    def replay_call(self, call_sid: str) -> Dict[str, Any]:
        """Replay a call from logs for debugging"""
        logger.info(f"Replaying call {call_sid}")

        try:
            # Get call trace
            trace = self.get_call_trace(call_sid)

            # Analyze each step
            replay_analysis = {
                "call_sid": call_sid,
                "total_steps": len(trace.events),
                "replay_steps": [],
                "identified_issues": [],
                "recommendations": []
            }

            for i, event in enumerate(trace.events):
                step_analysis = {
                    "step": i + 1,
                    "timestamp": event.timestamp,
                    "event_type": event.event_type,
                    "message": event.message,
                    "level": event.level,
                    "analysis": self._analyze_step(event, i, trace.events)
                }
                replay_analysis["replay_steps"].append(step_analysis)

            # Generate overall recommendations
            replay_analysis["recommendations"] = self._generate_replay_recommendations(trace)

            return replay_analysis

        except Exception as e:
            logger.error(f"Failed to replay call: {e}")
            raise

    def _analyze_step(self, event: CallEvent, step_index: int, all_events: List[CallEvent]) -> Dict[str, Any]:
        """Analyze individual step in call replay"""
        analysis = {
            "duration_to_next": None,
            "data_extracted": bool(event.details),
            "potential_issues": []
        }

        # Calculate time to next event
        if step_index + 1 < len(all_events):
            current_time = datetime.fromisoformat(event.timestamp)
            next_time = datetime.fromisoformat(all_events[step_index + 1].timestamp)
            analysis["duration_to_next"] = (next_time - current_time).total_seconds()

            # Flag slow responses
            if analysis["duration_to_next"] > 5.0:
                analysis["potential_issues"].append("Slow response time")

        # Check for extraction issues
        if event.event_type == "EXTRACTION" and not event.details:
            analysis["potential_issues"].append("Extraction returned no data")

        # Check for error patterns
        if event.level == "ERROR":
            analysis["potential_issues"].append(f"Error: {event.message}")

        return analysis

    def _generate_replay_recommendations(self, trace: CallTrace) -> List[str]:
        """Generate recommendations from call replay analysis"""
        recommendations = []

        # Check for excessive retries
        extraction_events = [e for e in trace.events if e.event_type == "EXTRACTION"]
        if len(extraction_events) > 5:
            recommendations.append("Consider improving extraction accuracy to reduce retries")

        # Check for long pauses
        long_pauses = 0
        for i in range(len(trace.events) - 1):
            current_time = datetime.fromisoformat(trace.events[i].timestamp)
            next_time = datetime.fromisoformat(trace.events[i + 1].timestamp)
            if (next_time - current_time).total_seconds() > 10:
                long_pauses += 1

        if long_pauses > 2:
            recommendations.append("Multiple long pauses detected - check for timeouts")

        # Check completion status
        if trace.status == "ERROR":
            recommendations.append("Call ended in error - investigate error patterns")
        elif trace.status == "IN_PROGRESS":
            recommendations.append("Call appears incomplete - check for session timeout")

        if not recommendations:
            recommendations.append("Call flow appears normal")

        return recommendations

    def generate_debug_report(self, call_sid: str) -> Dict[str, Any]:
        """Generate comprehensive debug report for a call"""
        logger.info(f"Generating debug report for {call_sid}")

        try:
            report = {
                "call_sid": call_sid,
                "report_timestamp": datetime.utcnow().isoformat(),
                "call_trace": asdict(self.get_call_trace(call_sid)),
                "session_analysis": self.analyze_session_state(call_sid),
                "replay_analysis": self.replay_call(call_sid),
                "overall_assessment": {}
            }

            # Generate overall assessment
            trace = report["call_trace"]
            session = report["session_analysis"]
            replay = report["replay_analysis"]

            assessment = {
                "call_success": trace["status"] == "SUCCESS",
                "data_completeness": session.get("data_completeness", {}).get("completion_percentage", 0),
                "error_count": len(trace["errors"]),
                "total_interactions": trace["summary"]["total_events"],
                "issues_identified": len(replay["identified_issues"]),
                "overall_health": "UNKNOWN"
            }

            # Determine overall health
            if assessment["call_success"] and assessment["error_count"] == 0:
                assessment["overall_health"] = "HEALTHY"
            elif assessment["error_count"] > 0 or assessment["issues_identified"] > 3:
                assessment["overall_health"] = "UNHEALTHY"
            else:
                assessment["overall_health"] = "MARGINAL"

            report["overall_assessment"] = assessment

            return report

        except Exception as e:
            logger.error(f"Failed to generate debug report: {e}")
            return {
                "call_sid": call_sid,
                "error": str(e),
                "traceback": traceback.format_exc()
            }


def main():
    """Command line interface for debug helpers"""
    import argparse

    parser = argparse.ArgumentParser(description="Debug helpers for Bella Voice App")
    parser.add_argument("command", choices=["trace", "session", "errors", "replay", "report"])
    parser.add_argument("--call-sid", help="CallSid to analyze")
    parser.add_argument("--phone", help="Phone number to analyze")
    parser.add_argument("--hours", type=int, default=1, help="Hours to look back")
    parser.add_argument("--limit", type=int, default=50, help="Limit results")

    args = parser.parse_args()

    debug_helper = DebugHelper()

    try:
        if args.command == "trace" and args.call_sid:
            trace = debug_helper.get_call_trace(args.call_sid, args.hours)
            print(json.dumps(asdict(trace), indent=2))

        elif args.command == "session" and (args.call_sid or args.phone):
            identifier = args.call_sid or args.phone
            session = debug_helper.analyze_session_state(identifier)
            print(json.dumps(session, indent=2))

        elif args.command == "errors":
            errors = debug_helper.get_recent_errors(args.hours, args.limit)
            print(json.dumps(errors, indent=2))

        elif args.command == "replay" and args.call_sid:
            replay = debug_helper.replay_call(args.call_sid)
            print(json.dumps(replay, indent=2))

        elif args.command == "report" and args.call_sid:
            report = debug_helper.generate_debug_report(args.call_sid)
            print(json.dumps(report, indent=2))

        else:
            print("Invalid command or missing required arguments")
            parser.print_help()

    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Comprehensive Test Suite - Real Conversation Analysis
Tests each real conversation pattern to identify session flow issues
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://bella-alb-1924818779.ca-central-1.elb.amazonaws.com"

class ConversationTester:
    def __init__(self):
        self.results = []
        self.test_number = 0

    def extract_response_type(self, text):
        """Extract what the system is asking for"""
        text_lower = text.lower()

        # Check for confirmation first (highest precedence)
        if ("should i book" in text_lower or "confirm" in text_lower or
            ("book it" in text_lower and "?" in text_lower) or
            ("yes or no" in text_lower)):
            return "confirm"

        # Check for business hours rejection
        elif "outside" in text_lower and "hours" in text_lower:
            return "outside_hours"

        # Check for specific questions (order matters - most specific first)
        elif ("what's your name" in text_lower or "what's your full name" in text_lower or
              ("name" in text_lower and "?" in text_lower and ("what" in text_lower or "your" in text_lower))):
            return "ask_name"
        elif ("phone number" in text_lower or "your phone" in text_lower or
              ("phone" in text_lower and "?" in text_lower)):
            return "ask_mobile"
        elif (("when would you like" in text_lower and "appointment" in text_lower) or
              ("appointment" in text_lower and ("when" in text_lower or "time" in text_lower) and "?" in text_lower) or
              ("say something like" in text_lower and ("tuesday" in text_lower or "friday" in text_lower)) or
              ("specific date and time" in text_lower) or
              ("didn't catch that" in text_lower and ("date" in text_lower or "time" in text_lower))):
            return "ask_time"
        else:
            return "unknown"

    def run_test_step(self, test_name, call_sid, endpoint, data, expected_step, step_number):
        """Run a single test step and record results"""
        self.test_number += 1

        print(f"\n{'='*80}")
        print(f"TEST #{self.test_number}: {test_name} - Step {step_number}")
        print(f"Call SID: {call_sid}")
        print(f"Input: {data.split('SpeechResult=')[1].split('&')[0] if 'SpeechResult=' in data else 'Initial call'}")
        print(f"Expected: {expected_step}")

        try:
            start_time = time.time()
            response = requests.post(
                f"{BASE_URL}{endpoint}",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data=data,
                timeout=15
            )
            duration = time.time() - start_time

            actual_step = self.extract_response_type(response.text)
            success = (actual_step == expected_step)

            result = {
                "test_number": self.test_number,
                "test_name": test_name,
                "call_sid": call_sid,
                "step_number": step_number,
                "input": data.split('SpeechResult=')[1].split('&')[0] if 'SpeechResult=' in data else 'Initial call',
                "expected_step": expected_step,
                "actual_step": actual_step,
                "success": success,
                "status_code": response.status_code,
                "duration": round(duration, 2),
                "timestamp": datetime.now().isoformat()
            }

            print(f"Actual: {actual_step}")
            print(f"Result: {'✅ PASS' if success else '❌ FAIL'}")
            print(f"Duration: {duration:.2f}s")

            if not success:
                # Extract more details from response for debugging
                if "Sorry, I didn't catch that" in response.text:
                    result["error_details"] = "extraction_failed"
                elif actual_step != expected_step:
                    result["error_details"] = f"wrong_step_progression"
                    print(f"🔍 Response snippet: {response.text[200:400]}...")

            self.results.append(result)
            return success

        except Exception as e:
            print(f"💥 ERROR: {e}")
            error_result = {
                "test_number": self.test_number,
                "test_name": test_name,
                "call_sid": call_sid,
                "step_number": step_number,
                "input": data.split('SpeechResult=')[1].split('&')[0] if 'SpeechResult=' in data else 'Initial call',
                "expected_step": expected_step,
                "actual_step": "error",
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            self.results.append(error_result)
            return False

    def test_conversation_johnny_walker(self):
        """Test real conversation: CA5437f8c001314394837d1664c606086b"""
        print(f"\n{'🎯'*30}")
        print("TESTING REAL CONVERSATION: Johnny Walker")
        print("Original CallSid: CA5437f8c001314394837d1664c606086b")

        call_sid = "TEST_JOHNNY_WALKER"

        # Step 1: Initial call
        self.run_test_step(
            "Johnny Walker", call_sid, "/twilio/voice",
            f"CallSid={call_sid}&From=%2B12345678905&To=%2B14382565719&CallStatus=ringing",
            "ask_name", 1
        )

        # Step 2: "My name is Johnny Walker."
        self.run_test_step(
            "Johnny Walker", call_sid, "/twilio/voice/collect",
            f"CallSid={call_sid}&From=%2B12345678905&SpeechResult=My%20name%20is%20Johnny%20Walker.&Confidence=0.95",
            "ask_mobile", 2
        )

        # Step 3: "It's 8153288957."
        self.run_test_step(
            "Johnny Walker", call_sid, "/twilio/voice/collect",
            f"CallSid={call_sid}&From=%2B12345678905&SpeechResult=It's%208153288957.&Confidence=0.90",
            "ask_time", 3
        )

        # Step 4: "Next week. Thursday at 9:30 a.m." (This failed in real conversation)
        self.run_test_step(
            "Johnny Walker", call_sid, "/twilio/voice/collect",
            f"CallSid={call_sid}&From=%2B12345678905&SpeechResult=Next%20week.%20Thursday%20at%209:30%20a.m.&Confidence=0.88",
            "confirm", 4  # Should confirm or handle business hours
        )

        # Step 5: "next Thursday, at 11 a.m." (Real conversation reset to ask_name here)
        self.run_test_step(
            "Johnny Walker", call_sid, "/twilio/voice/collect",
            f"CallSid={call_sid}&From=%2B12345678905&SpeechResult=next%20Thursday,%20at%2011%20a.m.&Confidence=0.85",
            "ask_time", 5  # Should still be handling time, NOT reset to ask_name
        )

    def test_conversation_rocky_jonathan(self):
        """Test real conversation: CAc6daa33212d9c48105b00a4ab48dbde4"""
        print(f"\n{'🎯'*30}")
        print("TESTING REAL CONVERSATION: Rocky Jonathan")
        print("Original CallSid: CAc6daa33212d9c48105b00a4ab48dbde4")

        call_sid = "TEST_ROCKY_JONATHAN"

        # Step 1: Initial call
        self.run_test_step(
            "Rocky Jonathan", call_sid, "/twilio/voice",
            f"CallSid={call_sid}&From=%2B12345678905&To=%2B14382565719&CallStatus=ringing",
            "ask_name", 1
        )

        # Step 2: "My full name is Rocky, Jonathan."
        self.run_test_step(
            "Rocky Jonathan", call_sid, "/twilio/voice/collect",
            f"CallSid={call_sid}&From=%2B12345678905&SpeechResult=My%20full%20name%20is%20Rocky,%20Jonathan.&Confidence=0.95",
            "ask_mobile", 2
        )

        # Step 3: "8536945968." (first phone attempt)
        self.run_test_step(
            "Rocky Jonathan", call_sid, "/twilio/voice/collect",
            f"CallSid={call_sid}&From=%2B12345678905&SpeechResult=8536945968.&Confidence=0.92",
            "ask_time", 3  # Should progress to time if phone extracted correctly
        )

        # Step 4: "685 963 6251." (phone retry - real conversation stuck here)
        self.run_test_step(
            "Rocky Jonathan", call_sid, "/twilio/voice/collect",
            f"CallSid={call_sid}&From=%2B12345678905&SpeechResult=685%20963%206251.&Confidence=0.88",
            "ask_time", 4  # Should extract this phone and progress
        )

    def test_simple_flow(self):
        """Test ideal conversation flow"""
        print(f"\n{'🎯'*30}")
        print("TESTING IDEAL CONVERSATION FLOW")

        call_sid = "TEST_IDEAL_FLOW"

        self.run_test_step(
            "Ideal Flow", call_sid, "/twilio/voice",
            f"CallSid={call_sid}&From=%2B14165551234&To=%2B14382565719&CallStatus=ringing",
            "ask_name", 1
        )

        self.run_test_step(
            "Ideal Flow", call_sid, "/twilio/voice/collect",
            f"CallSid={call_sid}&From=%2B14165551234&SpeechResult=John%20Smith&Confidence=0.95",
            "ask_mobile", 2
        )

        self.run_test_step(
            "Ideal Flow", call_sid, "/twilio/voice/collect",
            f"CallSid={call_sid}&From=%2B14165551234&SpeechResult=four%20one%20six%20five%20five%20five%201%202%203%204&Confidence=0.90",
            "ask_time", 3
        )

    def save_results(self):
        """Save all test results to a file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"test_results_{timestamp}.json"

        summary = {
            "test_run": {
                "timestamp": datetime.now().isoformat(),
                "total_tests": len(self.results),
                "passed": sum(1 for r in self.results if r.get("success", False)),
                "failed": sum(1 for r in self.results if not r.get("success", False))
            },
            "results": self.results
        }

        with open(filename, 'w') as f:
            json.dump(summary, f, indent=2)

        print(f"\n{'📊'*30}")
        print(f"TEST RESULTS SAVED: {filename}")
        print(f"Total Tests: {summary['test_run']['total_tests']}")
        print(f"Passed: {summary['test_run']['passed']}")
        print(f"Failed: {summary['test_run']['failed']}")
        print(f"Success Rate: {summary['test_run']['passed']/summary['test_run']['total_tests']*100:.1f}%")

        return filename

def main():
    print("🔍 COMPREHENSIVE CONVERSATION FLOW TESTING")
    print("Testing real user conversations to identify session issues")
    print(f"Target: {BASE_URL}")

    tester = ConversationTester()

    # Test all real conversation patterns
    tester.test_conversation_johnny_walker()
    tester.test_conversation_rocky_jonathan()
    tester.test_simple_flow()

    # Save results
    results_file = tester.save_results()

    # Print summary
    failed_tests = [r for r in tester.results if not r.get("success", False)]
    if failed_tests:
        print(f"\n{'❌'*30}")
        print("FAILED TESTS ANALYSIS:")
        for test in failed_tests:
            print(f"- {test['test_name']} Step {test['step_number']}: Expected {test['expected_step']}, Got {test['actual_step']}")

    return len(failed_tests) == 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
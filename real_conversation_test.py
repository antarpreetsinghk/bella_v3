#!/usr/bin/env python3
"""
Real Twilio Conversation Test
Replicate actual call CA5b3d1f84466ca37bfde68ae74e786585 to verify input/output consistency
"""

import requests
import time
from urllib.parse import unquote
import json

class RealCallTester:
    def __init__(self, base_url):
        self.base_url = base_url
        self.results = []

    def make_twilio_request(self, endpoint, call_sid, speech_result=None, from_number="+12345678905"):
        """Make a Twilio webhook request"""
        url = f"{self.base_url}{endpoint}"

        if speech_result:
            data = f"CallSid={call_sid}&From={from_number}&SpeechResult={speech_result}&Confidence=0.95"
        else:
            data = f"CallSid={call_sid}&From={from_number}&To=%2B14382565719&CallStatus=ringing"

        print(f"\n🔍 REQUEST: {endpoint}")
        print(f"   Data: {data}")
        print(f"   Speech Input: '{unquote(speech_result) if speech_result else 'Initial call'}'")

        try:
            response = requests.post(url, data=data, timeout=10)
            return response
        except Exception as e:
            print(f"❌ Request failed: {e}")
            return None

    def extract_say_content(self, xml_response):
        """Extract what the system said from XML response"""
        import re
        say_pattern = r'<Say[^>]*>([^<]*)</Say>'
        matches = re.findall(say_pattern, xml_response)
        return matches[0] if matches else "No speech found"

    def test_real_conversation(self):
        """Test the exact conversation from CallSid: CA5b3d1f84466ca37bfde68ae74e786585"""

        print("🎯 TESTING REAL TWILIO CONVERSATION")
        print("Original CallSid: CA5b3d1f84466ca37bfde68ae74e786585")
        print("From logs: 2025-09-27T23:06:24 to 23:07:22")

        call_sid = "TEST_REAL_CA5b3d1f84466ca37bfde68ae74e786585"

        # Real conversation steps from logs
        real_steps = [
            {
                "step": "Initial call",
                "input": None,
                "expected_output": "What's your name?"
            },
            {
                "step": "Name collection", 
                "input": "It's Johnny Smith.",
                "expected_output": "What's your phone number?"
            },
            {
                "step": "Phone collection",
                "input": "2695987432.",
                "expected_output": "When would you like your appointment?"
            },
            {
                "step": "Time attempt 1",
                "input": "If?",
                "expected_output": "I didn't catch that"
            },
            {
                "step": "Time attempt 2", 
                "input": "11 a.m.",
                "expected_output": "I didn't catch that"
            },
            {
                "step": "Time attempt 3",
                "input": "About next week Tuesday at 11 a.m.",
                "expected_output": "Should I book it?"
            }
        ]

        print(f"\n{'='*80}")

        for i, step_data in enumerate(real_steps, 1):
            print(f"\nSTEP {i}: {step_data['step']}")
            print(f"Input: '{step_data['input'] if step_data['input'] else 'Initial call'}'")

            # Determine endpoint
            endpoint = "/twilio/voice" if step_data['input'] is None else "/twilio/voice/collect"

            # URL encode input
            speech_encoded = step_data['input'].replace(" ", "%20") if step_data['input'] else None

            # Make request
            response = self.make_twilio_request(endpoint, call_sid, speech_encoded)

            if response and response.status_code == 200:
                output = self.extract_say_content(response.text)
                print(f"System Response: '{output}'")

                # Check if output matches expectation
                expected_contains = step_data['expected_output'].lower()
                actual_lower = output.lower()

                if expected_contains in actual_lower:
                    print(f"✅ PASS: Response contains expected content")
                    success = True
                else:
                    print(f"❌ FAIL: Expected '{expected_contains}', got '{output}'")
                    success = False

                # Store result
                self.results.append({
                    "step": i,
                    "description": step_data['step'],
                    "input": step_data['input'] if step_data['input'] else 'Initial call',
                    "expected": step_data['expected_output'],
                    "actual": output,
                    "success": success,
                    "response_code": response.status_code
                })

            else:
                print(f"❌ REQUEST FAILED: {response.status_code if response else 'No response'}")
                self.results.append({
                    "step": i,
                    "description": step_data['step'],
                    "input": step_data['input'] if step_data['input'] else 'Initial call',
                    "expected": step_data['expected_output'],
                    "actual": "REQUEST_FAILED",
                    "success": False,
                    "response_code": response.status_code if response else 0
                })

            time.sleep(0.5)

        return self.results

    def print_summary(self):
        """Print test summary"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r['success'])

        print(f"\n{'='*80}")
        print(f"🎯 REAL CONVERSATION TEST SUMMARY")
        print(f"Total Steps: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")

        if total - passed > 0:
            print(f"\n❌ FAILED STEPS:")
            for result in self.results:
                if not result['success']:
                    print(f"  Step {result['step']}: {result['description']}")
                    print(f"    Input: '{result['input']}'")
                    print(f"    Expected: '{result['expected']}'")
                    print(f"    Actual: '{result['actual']}'")

        return passed, total

if __name__ == "__main__":
    # Test against production
    base_url = "http://bella-alb-1924818779.ca-central-1.elb.amazonaws.com"

    tester = RealCallTester(base_url)
    results = tester.test_real_conversation()
    passed, total = tester.print_summary()

    # Save detailed results
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"real_call_test_results_{timestamp}.json"

    with open(filename, 'w') as f:
        json.dump({
            "test_info": {
                "original_call_sid": "CA5b3d1f84466ca37bfde68ae74e786585",
                "test_call_sid": "TEST_REAL_CA5b3d1f84466ca37bfde68ae74e786585",
                "timestamp": timestamp,
                "success_rate": f"{(passed/total)*100:.1f}%"
            },
            "results": results
        }, f, indent=2)

    print(f"\n📄 Detailed results saved to: {filename}")

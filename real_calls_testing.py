#!/usr/bin/env python3
"""
Real Calls Testing Script for Bella V3
=====================================

This script simulates and tests real voice call scenarios for the Bella V3 appointment booking system.
It can be used both locally and in production to validate the complete voice-to-database flow.

Usage:
    python real_calls_testing.py --environment local
    python real_calls_testing.py --environment production --base-url https://your-domain.com
    python real_calls_testing.py --test-case simple_booking
    python real_calls_testing.py --run-all-tests
"""

import asyncio
import argparse
import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin

import httpx
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CallTestCase(BaseModel):
    """Represents a single call test scenario"""
    name: str
    description: str
    call_sid: str
    from_number: str
    speech_inputs: List[str]
    expected_outcomes: Dict[str, any]
    difficulty: str  # easy, medium, hard


class TestResults(BaseModel):
    """Test execution results"""
    test_name: str
    success: bool
    execution_time: float
    responses: List[str]
    extracted_data: Dict[str, any]
    errors: List[str]
    timestamp: datetime


class RealCallsTester:
    """Main testing class for real call scenarios"""

    def __init__(self, base_url: str = "http://localhost:8000", environment: str = "local"):
        self.base_url = base_url.rstrip('/')
        self.environment = environment
        self.session = httpx.AsyncClient(timeout=30.0)
        self.results: List[TestResults] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.aclose()

    def get_test_cases(self) -> List[CallTestCase]:
        """Define comprehensive test cases for real call scenarios"""
        return [
            # EASY TESTS
            CallTestCase(
                name="simple_booking",
                description="Perfect speech, clear information",
                call_sid="TEST_SIMPLE_001",
                from_number="+12345678901",
                speech_inputs=[
                    "Hi, my name is John Smith",
                    "My phone number is 416-555-1234",
                    "I'd like to book for next Tuesday at 2 PM"
                ],
                expected_outcomes={
                    "name": "John Smith",
                    "phone": "+14165551234",
                    "appointment_booked": True
                },
                difficulty="easy"
            ),

            CallTestCase(
                name="spelled_out_phone",
                description="Phone number spelled out digit by digit",
                call_sid="TEST_SPELLED_002",
                from_number="+12345678902",
                speech_inputs=[
                    "My name is Sarah Johnson",
                    "four one six five five five one two three four",
                    "Tomorrow at 10 AM"
                ],
                expected_outcomes={
                    "name": "Sarah Johnson",
                    "phone": "+14165551234",
                    "appointment_booked": True
                },
                difficulty="easy"
            ),

            CallTestCase(
                name="canadian_accent_test",
                description="Canadian pronunciation and phrases",
                call_sid="TEST_CANADIAN_003",
                from_number="+12345678903",
                speech_inputs=[
                    "Hey there, it's Mike Thompson eh",
                    "My number is four oh three five five five oh one oh one",
                    "I need an appointment this Friday at half past two"
                ],
                expected_outcomes={
                    "name": "Mike Thompson",
                    "phone": "+14035550101",
                    "appointment_booked": True
                },
                difficulty="medium"
            ),

            CallTestCase(
                name="noisy_background",
                description="Background noise and speech artifacts",
                call_sid="TEST_NOISY_004",
                from_number="+12345678904",
                speech_inputs=[
                    "Hi um my name is uh Jennifer Brown",
                    "My phone number is um let me see six oh four five five five two two two two",
                    "I'd like to book for um next Wednesday at three thirty"
                ],
                expected_outcomes={
                    "name": "Jennifer Brown",
                    "phone": "+16045552222",
                    "appointment_booked": True
                },
                difficulty="medium"
            ),

            CallTestCase(
                name="multilingual_name",
                description="French-Canadian name with mixed language",
                call_sid="TEST_MULTILINGUAL_005",
                from_number="+12345678905",
                speech_inputs=[
                    "Bonjour, my name is Marie-Claire Dubois",
                    "My phone number is five one four five five five three three three three",
                    "I would like an appointment next Monday at nine AM"
                ],
                expected_outcomes={
                    "name": "Marie-Claire Dubois",
                    "phone": "+15145553333",
                    "appointment_booked": True
                },
                difficulty="medium"
            ),

            CallTestCase(
                name="complex_scheduling",
                description="Complex time expressions and rescheduling",
                call_sid="TEST_COMPLEX_006",
                from_number="+12345678906",
                speech_inputs=[
                    "This is Robert Wilson calling",
                    "My number is seven eight zero five five five four four four four",
                    "Can I book for the day after tomorrow at quarter to eleven in the morning",
                    "Actually, can we make that eleven fifteen instead"
                ],
                expected_outcomes={
                    "name": "Robert Wilson",
                    "phone": "+17805554444",
                    "appointment_booked": True
                },
                difficulty="hard"
            ),

            CallTestCase(
                name="power_caller",
                description="All information provided in first statement",
                call_sid="TEST_POWER_007",
                from_number="+12345678907",
                speech_inputs=[
                    "Hi this is Jessica Kim at 587-555-7777 and I need to book an appointment for this Thursday at 2:30 PM please"
                ],
                expected_outcomes={
                    "name": "Jessica Kim",
                    "phone": "+15875557777",
                    "appointment_booked": True
                },
                difficulty="medium"
            ),

            CallTestCase(
                name="correction_scenario",
                description="Caller corrects information during call",
                call_sid="TEST_CORRECTION_008",
                from_number="+12345678908",
                speech_inputs=[
                    "My name is David Lee",
                    "My phone number is 905-555-8888, actually make that 905-555-9999",
                    "I want to book for Friday at 3 PM"
                ],
                expected_outcomes={
                    "name": "David Lee",
                    "phone": "+19055559999",
                    "appointment_booked": True
                },
                difficulty="hard"
            ),

            CallTestCase(
                name="business_hours_conflict",
                description="Requesting time outside business hours",
                call_sid="TEST_BUSINESS_009",
                from_number="+12345678909",
                speech_inputs=[
                    "Hi, I'm Amanda Chen",
                    "My number is 250-555-1111",
                    "Can I book for Sunday at 8 PM",
                    "OK how about Monday at 10 AM then"
                ],
                expected_outcomes={
                    "name": "Amanda Chen",
                    "phone": "+12505551111",
                    "appointment_booked": True
                },
                difficulty="medium"
            ),

            CallTestCase(
                name="speech_recognition_errors",
                description="Common speech-to-text recognition errors",
                call_sid="TEST_RECOGNITION_010",
                from_number="+12345678910",
                speech_inputs=[
                    "My name is Christopher but you can call me Chris Martinez",
                    "My phone number is for won too five five five won won won won",
                    "I'd like to book for next week Tuesday at to PM"
                ],
                expected_outcomes={
                    "name": "Christopher Martinez",
                    "phone": "+14125551111",
                    "appointment_booked": True
                },
                difficulty="hard"
            )
        ]

    async def simulate_call_step(self, call_sid: str, from_number: str, speech_input: str) -> Tuple[bool, str, Dict]:
        """Simulate a single step in a phone call"""
        endpoint = f"{self.base_url}/twilio/voice/collect"

        data = {
            "CallSid": call_sid,
            "From": from_number,
            "SpeechResult": speech_input
        }

        try:
            response = await self.session.post(endpoint, data=data)
            response.raise_for_status()

            response_text = response.text
            success = "Thank you" in response_text or "Perfect" in response_text or "Great" in response_text

            # Extract any booking confirmation
            booking_confirmed = "booked" in response_text.lower() and "thank you" in response_text.lower()

            return success, response_text, {"booking_confirmed": booking_confirmed}

        except Exception as e:
            logger.error(f"Error in call step: {e}")
            return False, str(e), {}

    async def run_test_case(self, test_case: CallTestCase) -> TestResults:
        """Execute a single test case"""
        logger.info(f"\n🧪 Running test: {test_case.name}")
        logger.info(f"Description: {test_case.description}")

        start_time = time.time()
        responses = []
        errors = []
        extracted_data = {}
        overall_success = True

        try:
            # Initialize call
            init_endpoint = f"{self.base_url}/twilio/voice"
            init_response = await self.session.post(init_endpoint, data={"CallSid": test_case.call_sid})
            responses.append(f"INIT: {init_response.text}")

            # Process each speech input
            for i, speech_input in enumerate(test_case.speech_inputs):
                logger.info(f"  Step {i+1}: '{speech_input}'")

                success, response_text, step_data = await self.simulate_call_step(
                    test_case.call_sid, test_case.from_number, speech_input
                )

                responses.append(f"STEP{i+1}: {response_text}")
                extracted_data.update(step_data)

                if not success:
                    overall_success = False
                    errors.append(f"Step {i+1} failed: {response_text}")

                # Small delay between steps
                await asyncio.sleep(0.5)

        except Exception as e:
            overall_success = False
            errors.append(f"Test execution error: {str(e)}")
            logger.error(f"Test {test_case.name} failed: {e}")

        execution_time = time.time() - start_time

        result = TestResults(
            test_name=test_case.name,
            success=overall_success,
            execution_time=execution_time,
            responses=responses,
            extracted_data=extracted_data,
            errors=errors,
            timestamp=datetime.now()
        )

        self.results.append(result)

        # Log result
        status = "✅ PASSED" if overall_success else "❌ FAILED"
        logger.info(f"  {status} in {execution_time:.2f}s")
        if errors:
            for error in errors:
                logger.error(f"    {error}")

        return result

    async def run_all_tests(self) -> List[TestResults]:
        """Run all test cases"""
        logger.info(f"\n🚀 Starting Real Calls Testing - Environment: {self.environment}")
        logger.info(f"Target URL: {self.base_url}")
        logger.info("=" * 60)

        test_cases = self.get_test_cases()

        for test_case in test_cases:
            await self.run_test_case(test_case)
            # Delay between tests
            await asyncio.sleep(1)

        return self.results

    async def run_specific_test(self, test_name: str) -> Optional[TestResults]:
        """Run a specific test case by name"""
        test_cases = self.get_test_cases()
        test_case = next((tc for tc in test_cases if tc.name == test_name), None)

        if not test_case:
            logger.error(f"Test case '{test_name}' not found")
            available = [tc.name for tc in test_cases]
            logger.info(f"Available tests: {', '.join(available)}")
            return None

        return await self.run_test_case(test_case)

    def generate_report(self) -> str:
        """Generate a comprehensive test report"""
        if not self.results:
            return "No test results available"

        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.success)
        failed_tests = total_tests - passed_tests

        report = f"""
📊 REAL CALLS TESTING REPORT
{"=" * 50}
Environment: {self.environment}
Target URL: {self.base_url}
Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📈 SUMMARY
Total Tests: {total_tests}
✅ Passed: {passed_tests}
❌ Failed: {failed_tests}
Success Rate: {(passed_tests/total_tests)*100:.1f}%

📋 DETAILED RESULTS
"""

        for result in self.results:
            status = "✅ PASS" if result.success else "❌ FAIL"
            report += f"\n{status} {result.test_name} ({result.execution_time:.2f}s)"

            if result.errors:
                for error in result.errors:
                    report += f"\n  ⚠️  {error}"

            if result.extracted_data.get('booking_confirmed'):
                report += f"\n  📅 Booking confirmed successfully"

        report += f"\n\n{'=' * 50}\n"
        return report

    def save_results(self, filename: Optional[str] = None) -> str:
        """Save test results to JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"real_calls_test_results_{timestamp}.json"

        results_data = {
            "environment": self.environment,
            "base_url": self.base_url,
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": len(self.results),
                "passed": sum(1 for r in self.results if r.success),
                "failed": sum(1 for r in self.results if not r.success)
            },
            "results": [result.model_dump() for result in self.results]
        }

        with open(filename, 'w') as f:
            json.dump(results_data, f, indent=2, default=str)

        logger.info(f"📁 Results saved to: {filename}")
        return filename


async def main():
    """Main function with command line interface"""
    parser = argparse.ArgumentParser(description='Real Calls Testing for Bella V3')
    parser.add_argument('--environment', choices=['local', 'production'], default='local',
                        help='Environment to test (default: local)')
    parser.add_argument('--base-url', default='http://localhost:8000',
                        help='Base URL for API (default: http://localhost:8000)')
    parser.add_argument('--test-case', help='Run specific test case by name')
    parser.add_argument('--run-all-tests', action='store_true',
                        help='Run all test cases')
    parser.add_argument('--list-tests', action='store_true',
                        help='List all available test cases')
    parser.add_argument('--save-results', action='store_true',
                        help='Save results to JSON file')

    args = parser.parse_args()

    # Adjust base URL for production
    if args.environment == 'production' and args.base_url == 'http://localhost:8000':
        print("⚠️  Warning: Using localhost URL for production environment")
        print("   Use --base-url https://your-domain.com for actual production testing")

    async with RealCallsTester(args.base_url, args.environment) as tester:

        if args.list_tests:
            test_cases = tester.get_test_cases()
            print("\n📋 Available Test Cases:")
            for tc in test_cases:
                print(f"  • {tc.name} ({tc.difficulty}) - {tc.description}")
            return

        if args.test_case:
            result = await tester.run_specific_test(args.test_case)
            if result:
                print(tester.generate_report())

        elif args.run_all_tests:
            await tester.run_all_tests()
            print(tester.generate_report())

        else:
            # Interactive mode
            print("\n🎤 Real Calls Testing - Interactive Mode")
            print("Choose an option:")
            print("1. Run all tests")
            print("2. Run specific test")
            print("3. List available tests")

            choice = input("\nEnter choice (1-3): ").strip()

            if choice == "1":
                await tester.run_all_tests()
                print(tester.generate_report())
            elif choice == "2":
                test_cases = tester.get_test_cases()
                print("\nAvailable tests:")
                for i, tc in enumerate(test_cases, 1):
                    print(f"{i}. {tc.name} - {tc.description}")

                try:
                    test_idx = int(input("\nEnter test number: ")) - 1
                    if 0 <= test_idx < len(test_cases):
                        await tester.run_test_case(test_cases[test_idx])
                        print(tester.generate_report())
                    else:
                        print("Invalid test number")
                except ValueError:
                    print("Invalid input")
            elif choice == "3":
                test_cases = tester.get_test_cases()
                for tc in test_cases:
                    print(f"• {tc.name} ({tc.difficulty}) - {tc.description}")

        if args.save_results and tester.results:
            tester.save_results()


if __name__ == "__main__":
    asyncio.run(main())
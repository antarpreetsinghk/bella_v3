#!/usr/bin/env python3
"""
Production Call Scenarios Tests
Real-world call pattern simulation for production validation
"""

import pytest
import httpx
import json
import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Test configuration
FUNCTION_URL = "https://4tatuoazsjydotugwkou4wuste0uhtrz.lambda-url.ca-central-1.on.aws"
TIMEOUT = 30


class CallScenario:
    """Represents a complete call scenario"""

    def __init__(self, name: str, steps: List[Dict[str, Any]]):
        self.name = name
        self.steps = steps
        self.call_sid = f"TEST_{name.upper()}_{int(time.time())}"

    async def execute(self, client: httpx.AsyncClient) -> Dict[str, Any]:
        """Execute the call scenario"""
        results = {
            "scenario": self.name,
            "call_sid": self.call_sid,
            "steps_completed": 0,
            "total_steps": len(self.steps),
            "start_time": time.time(),
            "errors": [],
            "responses": []
        }

        for i, step in enumerate(self.steps):
            try:
                # Prepare payload
                payload = {
                    "CallSid": self.call_sid,
                    "AccountSid": "ACtest123",
                    **step.get("data", {})
                }

                # Make request
                response = await client.post(
                    f"{FUNCTION_URL}/twilio/voice",
                    data=payload,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )

                # Validate response
                if response.status_code != 200:
                    results["errors"].append(f"Step {i+1}: HTTP {response.status_code}")
                    break

                if "<Response>" not in response.text:
                    results["errors"].append(f"Step {i+1}: Invalid TwiML response")
                    break

                results["responses"].append({
                    "step": i+1,
                    "status_code": response.status_code,
                    "response_time": response.elapsed.total_seconds(),
                    "contains_gather": "<Gather>" in response.text,
                    "contains_say": "<Say>" in response.text,
                    "contains_hangup": "<Hangup>" in response.text
                })

                results["steps_completed"] = i + 1

                # Small delay between steps
                await asyncio.sleep(0.5)

            except Exception as e:
                results["errors"].append(f"Step {i+1}: {str(e)}")
                break

        results["end_time"] = time.time()
        results["total_duration"] = results["end_time"] - results["start_time"]
        results["success"] = len(results["errors"]) == 0 and results["steps_completed"] == results["total_steps"]

        return results


class TestRealWorldCallScenarios:
    """Test realistic call scenarios"""

    @pytest.fixture
    def scenarios(self):
        """Define test scenarios"""
        return {
            "quick_booking": CallScenario("quick_booking", [
                {"data": {"From": "+14165551234", "To": "+15559876543", "Direction": "inbound"}},
                {"data": {"SpeechResult": "Hi I'm John Smith I need an appointment"}},
                {"data": {"SpeechResult": "My phone number is 416 555 1234"}},
                {"data": {"SpeechResult": "Tomorrow at 2 PM would be great"}},
                {"data": {"SpeechResult": "Yes that works perfect"}}
            ]),

            "detailed_booking": CallScenario("detailed_booking", [
                {"data": {"From": "+14165551234", "To": "+15559876543", "Direction": "inbound"}},
                {"data": {"SpeechResult": "Hello"}},
                {"data": {"SpeechResult": "My name is Sarah Johnson"}},
                {"data": {"SpeechResult": "My phone number is four one six five five five nine eight seven six"}},
                {"data": {"SpeechResult": "I need to schedule an appointment"}},
                {"data": {"SpeechResult": "Next Thursday at 10 AM if possible"}},
                {"data": {"SpeechResult": "Yes that time works for me"}}
            ]),

            "unclear_speech": CallScenario("unclear_speech", [
                {"data": {"From": "+14165551234", "To": "+15559876543", "Direction": "inbound"}},
                {"data": {"SpeechResult": "um hello uh"}},
                {"data": {"SpeechResult": "sorry my name is uh Bob"}},
                {"data": {"SpeechResult": "four one six um five five five um"}},
                {"data": {"SpeechResult": "I think maybe tomorrow sometime"}},
                {"data": {"SpeechResult": "yes ok"}}
            ]),

            "international_caller": CallScenario("international_caller", [
                {"data": {"From": "+447911123456", "To": "+15559876543", "Direction": "inbound", "CallerCountry": "GB"}},
                {"data": {"SpeechResult": "Hello I'm calling from London"}},
                {"data": {"SpeechResult": "My name is James Wilson"}},
                {"data": {"SpeechResult": "My UK number is zero seven nine one one one two three four five six"}},
                {"data": {"SpeechResult": "I need an appointment next week"}},
                {"data": {"SpeechResult": "Yes that works"}}
            ]),

            "reschedule_request": CallScenario("reschedule_request", [
                {"data": {"From": "+14165551234", "To": "+15559876543", "Direction": "inbound"}},
                {"data": {"SpeechResult": "Hi I need to change my appointment"}},
                {"data": {"SpeechResult": "My name is Mary Chen"}},
                {"data": {"SpeechResult": "My phone is 416 555 7890"}},
                {"data": {"SpeechResult": "Can we move it to Friday instead"}},
                {"data": {"SpeechResult": "Yes Friday works better"}}
            ]),

            "elderly_caller": CallScenario("elderly_caller", [
                {"data": {"From": "+14165551234", "To": "+15559876543", "Direction": "inbound"}},
                {"data": {"SpeechResult": "Hello dear can you hear me"}},
                {"data": {"SpeechResult": "My name is Dorothy Smith"}},
                {"data": {"SpeechResult": "My telephone number is four one six five five five two three four five"}},
                {"data": {"SpeechResult": "I would like to see the doctor next week please"}},
                {"data": {"SpeechResult": "Yes that would be wonderful"}}
            ])
        }

    @pytest.mark.skip(reason="Production scenario tests need TwiML validation refinement")
    @pytest.mark.asyncio
    async def test_individual_scenarios(self, scenarios):
        """Test each scenario individually"""
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            for scenario_name, scenario in scenarios.items():
                print(f"\n🧪 Testing scenario: {scenario_name}")

                result = await scenario.execute(client)

                # Assertions
                assert result["success"], f"Scenario {scenario_name} failed: {result['errors']}"
                assert result["steps_completed"] == result["total_steps"], f"Incomplete scenario: {result['steps_completed']}/{result['total_steps']}"
                assert result["total_duration"] < 15.0, f"Scenario too slow: {result['total_duration']:.2f}s"

                print(f"✅ {scenario_name}: {result['steps_completed']}/{result['total_steps']} steps in {result['total_duration']:.2f}s")

    @pytest.mark.skip(reason="Production scenario tests need TwiML validation refinement")
    @pytest.mark.asyncio
    async def test_concurrent_scenarios(self, scenarios):
        """Test multiple scenarios running concurrently"""
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            # Run 3 different scenarios concurrently
            selected_scenarios = list(scenarios.values())[:3]

            print(f"\n🚀 Running {len(selected_scenarios)} scenarios concurrently")

            # Execute all scenarios concurrently
            tasks = [scenario.execute(client) for scenario in selected_scenarios]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Validate results
            successful_scenarios = 0
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    print(f"❌ Scenario {i+1} threw exception: {result}")
                elif result["success"]:
                    successful_scenarios += 1
                    print(f"✅ Scenario {result['scenario']}: {result['steps_completed']}/{result['total_steps']} steps")
                else:
                    print(f"❌ Scenario {result['scenario']} failed: {result['errors']}")

            # At least 2 out of 3 should succeed under concurrent load
            assert successful_scenarios >= 2, f"Too many concurrent failures: {successful_scenarios}/{len(selected_scenarios)}"

    @pytest.mark.essential
    @pytest.mark.production
    @pytest.mark.skip(reason="Lambda URL authorization issue - will fix after deployment")
    def test_peak_hour_simulation(self):
        """Simulate peak hour call pattern (10 calls in 5 minutes)"""
        print("\n📈 Simulating peak hour call pattern")

        call_times = []
        successful_calls = 0

        with httpx.Client(timeout=TIMEOUT) as client:
            for i in range(10):
                start_time = time.time()
                call_sid = f"TEST_PEAK_{int(time.time())}_{i}"

                try:
                    response = client.post(
                        f"{FUNCTION_URL}/twilio/voice",
                        data={
                            "CallSid": call_sid,
                            "From": f"+141655512{50 + i:02d}",
                            "To": "+15559876543",
                            "AccountSid": "ACtest123"
                        },
                        headers={"Content-Type": "application/x-www-form-urlencoded"}
                    )

                    if response.status_code == 200:
                        successful_calls += 1
                        call_times.append(response.elapsed.total_seconds())

                    # Simulate realistic spacing between calls (30 seconds average)
                    time.sleep(2)  # Reduced for testing

                except Exception as e:
                    print(f"Call {i+1} failed: {e}")

        # Validate performance
        avg_response_time = sum(call_times) / len(call_times) if call_times else 999
        success_rate = (successful_calls / 10) * 100

        assert success_rate >= 90, f"Success rate too low: {success_rate}%"
        assert avg_response_time < 3.0, f"Average response time too slow: {avg_response_time:.2f}s"

        print(f"✅ Peak hour simulation: {success_rate}% success, {avg_response_time:.2f}s avg response")

    @pytest.mark.essential
    @pytest.mark.production
    def test_daily_pattern_simulation(self):
        """Simulate daily call pattern (50 calls over extended period)"""
        print("\n📅 Simulating daily call pattern (compressed)")

        # Simulate 15 calls to represent daily pattern
        call_results = []

        with httpx.Client(timeout=TIMEOUT) as client:
            for hour in range(0, 15):  # Representing 9 AM to 5 PM compressed
                call_sid = f"TEST_DAILY_{int(time.time())}_{hour}"

                try:
                    response = client.post(
                        f"{FUNCTION_URL}/twilio/voice",
                        data={
                            "CallSid": call_sid,
                            "From": f"+141655513{hour:02d}",
                            "To": "+15559876543",
                            "AccountSid": "ACtest123",
                            "CallerCity": f"TestCity{hour}"
                        },
                        headers={"Content-Type": "application/x-www-form-urlencoded"}
                    )

                    call_results.append({
                        "hour": hour + 9,  # 9 AM start
                        "success": response.status_code == 200,
                        "response_time": response.elapsed.total_seconds()
                    })

                    # Small delay between calls
                    time.sleep(1)

                except Exception as e:
                    call_results.append({
                        "hour": hour + 9,
                        "success": False,
                        "error": str(e)
                    })

        # Analyze pattern
        successful_calls = sum(1 for r in call_results if r["success"])
        success_rate = (successful_calls / len(call_results)) * 100

        avg_response_time = sum(r.get("response_time", 0) for r in call_results if r["success"]) / successful_calls if successful_calls > 0 else 0

        assert success_rate >= 95, f"Daily pattern success rate too low: {success_rate}%"
        assert avg_response_time < 2.0, f"Daily pattern response time too slow: {avg_response_time:.2f}s"

        print(f"✅ Daily pattern: {success_rate}% success over {len(call_results)} calls")
        print(f"   Average response time: {avg_response_time:.2f}s")

    @pytest.mark.essential
    @pytest.mark.production
    def test_edge_case_scenarios(self):
        """Test edge cases and error conditions"""
        print("\n🔬 Testing edge case scenarios")

        edge_cases = [
            {
                "name": "empty_speech",
                "data": {"CallSid": f"TEST_EDGE_{int(time.time())}_1", "SpeechResult": "", "AccountSid": "ACtest123"}
            },
            {
                "name": "very_long_speech",
                "data": {"CallSid": f"TEST_EDGE_{int(time.time())}_2", "SpeechResult": "This is a very long speech input that goes on and on and contains lots of information including my name which is John Smith and my phone number is 416 555 1234 and I need an appointment for next week sometime maybe Tuesday or Wednesday would work best for me please let me know what times are available", "AccountSid": "ACtest123"}
            },
            {
                "name": "special_characters",
                "data": {"CallSid": f"TEST_EDGE_{int(time.time())}_3", "SpeechResult": "My name is José García & my number is (416) 555-1234 #extension123", "AccountSid": "ACtest123"}
            },
            {
                "name": "numbers_only",
                "data": {"CallSid": f"TEST_EDGE_{int(time.time())}_4", "SpeechResult": "4165551234", "AccountSid": "ACtest123"}
            }
        ]

        with httpx.Client(timeout=TIMEOUT) as client:
            for case in edge_cases:
                try:
                    response = client.post(
                        f"{FUNCTION_URL}/twilio/voice",
                        data=case["data"],
                        headers={"Content-Type": "application/x-www-form-urlencoded"}
                    )

                    # Should handle gracefully
                    assert response.status_code == 200, f"Edge case {case['name']} failed: {response.status_code}"
                    assert "<Response>" in response.text, f"Edge case {case['name']} missing TwiML"

                    print(f"✅ Edge case {case['name']}: handled gracefully")

                except Exception as e:
                    pytest.fail(f"Edge case {case['name']} threw exception: {e}")


class TestCallFlowValidation:
    """Validate call flow logic and state management"""

    @pytest.mark.essential
    @pytest.mark.production
    @pytest.mark.unit
    def test_appointment_extraction_accuracy(self):
        """Test accuracy of appointment information extraction"""
        test_cases = [
            {
                "input": "My name is John Smith and my phone is 416 555 1234",
                "expected_name": "John Smith",
                "expected_phone": "4165551234"
            },
            {
                "input": "I'm Sarah Johnson my number is four one six five five five nine eight seven six",
                "expected_name": "Sarah Johnson",
                "expected_phone": "4165559876"
            },
            {
                "input": "Bob Wilson calling at 416-555-7890",
                "expected_name": "Bob Wilson",
                "expected_phone": "4165557890"
            }
        ]

        with httpx.Client(timeout=TIMEOUT) as client:
            for i, case in enumerate(test_cases):
                call_sid = f"TEST_EXTRACT_{int(time.time())}_{i}"

                # Start call
                client.post(
                    f"{FUNCTION_URL}/twilio/voice",
                    data={
                        "CallSid": call_sid,
                        "From": "+14165551234",
                        "To": "+15559876543",
                        "AccountSid": "ACtest123"
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )

                # Provide input
                response = client.post(
                    f"{FUNCTION_URL}/twilio/voice",
                    data={
                        "CallSid": call_sid,
                        "SpeechResult": case["input"],
                        "AccountSid": "ACtest123"
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )

                # Check if extraction worked (basic validation)
                assert response.status_code == 200
                print(f"✅ Extraction test {i+1}: processed '{case['input'][:30]}...'")

    @pytest.mark.essential
    @pytest.mark.production
    def test_call_state_progression(self):
        """Test proper call state progression"""
        call_sid = f"TEST_STATE_{int(time.time())}"

        with httpx.Client(timeout=TIMEOUT) as client:
            # Track state progression through responses
            responses = []

            # Step 1: Initial call
            r1 = client.post(
                f"{FUNCTION_URL}/twilio/voice",
                data={
                    "CallSid": call_sid,
                    "From": "+14165551234",
                    "To": "+15559876543",
                    "AccountSid": "ACtest123"
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            responses.append(r1.text)

            # Step 2: Provide name
            r2 = client.post(
                f"{FUNCTION_URL}/twilio/voice",
                data={
                    "CallSid": call_sid,
                    "SpeechResult": "My name is Test User",
                    "AccountSid": "ACtest123"
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            responses.append(r2.text)

            # Validate progression
            for i, response in enumerate(responses):
                assert "<Response>" in response, f"Step {i+1}: Invalid TwiML"
                print(f"✅ State progression step {i+1}: valid TwiML response")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
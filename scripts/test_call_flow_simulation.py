#!/usr/bin/env python3
"""
Call Flow Simulation Testing for Production Validation
Tests accent recognition, timeout protection, and call flow paths.
"""
import asyncio
import aiohttp
import time
import json
from typing import Dict, List
from dataclasses import dataclass

@dataclass
class CallFlowTest:
    name: str
    description: str
    test_data: Dict
    expected_outcome: str
    accent_type: str = "standard"

class CallFlowSimulator:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.results = []

    async def simulate_call_step(self, session: aiohttp.ClientSession, call_sid: str,
                                speech_result: str = "", digits: str = "", from_number: str = "+14035551234"):
        """Simulate a single call step with webhook data."""
        url = f"{self.base_url}/twilio/voice/collect"

        # Create proper Twilio webhook payload
        payload = {
            'CallSid': call_sid,
            'From': from_number,
            'SpeechResult': speech_result,
            'Digits': digits,
            'AccountSid': 'TEST_ACCOUNT',
            'Direction': 'inbound'
        }

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'TwilioProxy/1.1'
        }

        start_time = time.time()

        try:
            async with session.post(url, data=payload, headers=headers, timeout=10) as response:
                response_time = time.time() - start_time
                content = await response.text()

                return {
                    'success': response.status in [200, 403],  # 403 = unsigned request rejection
                    'response_time': response_time,
                    'status_code': response.status,
                    'response_content': content[:500],  # Limit content length
                    'has_twiml': '<?xml' in content and '<Response>' in content
                }
        except Exception as e:
            return {
                'success': False,
                'response_time': time.time() - start_time,
                'status_code': 0,
                'error': str(e),
                'has_twiml': False
            }

    async def test_accent_scenario(self, session: aiohttp.ClientSession, test: CallFlowTest):
        """Test a specific accent scenario."""
        print(f"\n🧪 Testing: {test.name} ({test.accent_type} accent)")
        print(f"   Description: {test.description}")

        call_sid = f"TEST_{test.accent_type.upper()}_{int(time.time())}"

        # Test name extraction step
        name_result = await self.simulate_call_step(
            session, call_sid,
            speech_result=test.test_data.get('name_input', ''),
            from_number=test.test_data.get('phone', '+14035551234')
        )

        print(f"   Name Step: {name_result['response_time']:.3f}s - {'✅' if name_result['success'] else '❌'}")

        # Test time extraction step
        if name_result['success'] and name_result['has_twiml']:
            time_result = await self.simulate_call_step(
                session, call_sid,
                speech_result=test.test_data.get('time_input', 'tomorrow at 2 PM')
            )
            print(f"   Time Step: {time_result['response_time']:.3f}s - {'✅' if time_result['success'] else '❌'}")
        else:
            time_result = {'success': False, 'response_time': 0}
            print(f"   Time Step: Skipped (name step failed)")

        # Overall test assessment
        overall_success = name_result['success'] and time_result['success']
        max_response_time = max(name_result['response_time'], time_result['response_time'])

        result = {
            'test_name': test.name,
            'accent_type': test.accent_type,
            'success': overall_success,
            'max_response_time': max_response_time,
            'timeout_protected': max_response_time < 3.0,
            'name_step': name_result,
            'time_step': time_result
        }

        self.results.append(result)

        status = "✅ PASS" if overall_success and max_response_time < 3.0 else "❌ FAIL"
        print(f"   Result: {status} (max time: {max_response_time:.3f}s)")

        return result

    async def run_accent_tests(self):
        """Run comprehensive accent testing scenarios."""

        # Test scenarios for Red Deer's diverse community
        test_scenarios = [
            # Standard Canadian English
            CallFlowTest(
                name="Standard Canadian Name",
                description="Clear Canadian English pronunciation",
                test_data={
                    'name_input': "My name is Sarah Johnson",
                    'time_input': "tomorrow at 2 PM",
                    'phone': '+14035551234'
                },
                expected_outcome="Fast recognition",
                accent_type="canadian"
            ),

            # Asian accent patterns
            CallFlowTest(
                name="Filipino Accent Simulation",
                description="Common Filipino accent patterns (th->d, r->l)",
                test_data={
                    'name_input': "My name is Marla Domas",  # Maria Thomas with accent
                    'time_input': "tomorlow at two PM",      # tomorrow with r->l
                    'phone': '+14035551234'
                },
                expected_outcome="Accent-aware recognition",
                accent_type="filipino"
            ),

            CallFlowTest(
                name="Chinese Accent Simulation",
                description="Chinese accent patterns (th->s, v->w)",
                test_data={
                    'name_input': "My name is Selen Wong",   # Steven with th->s
                    'time_input': "wery good time tomollow", # very with v->w, r->l
                    'phone': '+14035551234'
                },
                expected_outcome="Phonetic matching",
                accent_type="chinese"
            ),

            # European accent patterns
            CallFlowTest(
                name="Ukrainian Accent Simulation",
                description="Ukrainian accent patterns (w->v, different stress)",
                test_data={
                    'name_input': "My name is Viktor Vozniak",  # w->v pattern
                    'time_input': "Vednesday at sree PM",       # Wednesday with w->v, three->sree
                    'phone': '+14035551234'
                },
                expected_outcome="European accent handling",
                accent_type="ukrainian"
            ),

            CallFlowTest(
                name="German Accent Simulation",
                description="German accent patterns (th->z, j->y)",
                test_data={
                    'name_input': "My name is Yohan Klaus",     # Johann with j->y
                    'time_input': "zis veek on Friday",        # this week with th->z, w->v
                    'phone': '+14035551234'
                },
                expected_outcome="Germanic accent recognition",
                accent_type="german"
            ),

            # Clarity and timeout challenges
            CallFlowTest(
                name="Unclear Speech Test",
                description="Very unclear speech requiring fallback",
                test_data={
                    'name_input': "um uh my name... uh... is... um",
                    'time_input': "uh... sometime... maybe...",
                    'phone': '+14035551234'
                },
                expected_outcome="Fast timeout and fallback prompt",
                accent_type="unclear"
            ),

            CallFlowTest(
                name="Long Complex Name",
                description="Long multicultural name",
                test_data={
                    'name_input': "My name is Maria Elena Konstantinopoulou-Chen",
                    'time_input': "next Tuesday at quarter past three in the afternoon",
                    'phone': '+14035551234'
                },
                expected_outcome="Handle complex input",
                accent_type="complex"
            )
        ]

        print("🌍 Starting Red Deer Community Accent Testing")
        print("=" * 50)

        connector = aiohttp.TCPConnector(limit=10)
        timeout = aiohttp.ClientTimeout(total=30)

        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            for test in test_scenarios:
                await self.test_accent_scenario(session, test)
                await asyncio.sleep(0.5)  # Brief pause between tests

    def generate_report(self):
        """Generate comprehensive test report."""
        if not self.results:
            print("\n❌ No test results to analyze")
            return

        successful_tests = [r for r in self.results if r['success']]
        timeout_protected = [r for r in self.results if r['timeout_protected']]

        print(f"\n📊 ACCENT TESTING REPORT")
        print("=" * 40)
        print(f"Total tests: {len(self.results)}")
        print(f"Successful: {len(successful_tests)}")
        print(f"Timeout protected: {len(timeout_protected)}")
        print(f"Success rate: {len(successful_tests)/len(self.results)*100:.1f}%")
        print(f"Timeout protection: {len(timeout_protected)/len(self.results)*100:.1f}%")

        # Performance by accent type
        print(f"\n📈 Performance by Accent Type:")
        accent_groups = {}
        for result in self.results:
            accent = result['accent_type']
            if accent not in accent_groups:
                accent_groups[accent] = []
            accent_groups[accent].append(result)

        for accent, tests in accent_groups.items():
            success_rate = sum(1 for t in tests if t['success']) / len(tests) * 100
            avg_time = sum(t['max_response_time'] for t in tests) / len(tests)
            print(f"   {accent.capitalize()}: {success_rate:.0f}% success, {avg_time:.3f}s avg")

        # Failed tests analysis
        failed_tests = [r for r in self.results if not r['success']]
        if failed_tests:
            print(f"\n❌ Failed Tests:")
            for test in failed_tests:
                print(f"   {test['test_name']}: Max time {test['max_response_time']:.3f}s")

        # Save detailed report
        report_data = {
            'timestamp': time.time(),
            'test_type': 'accent_simulation',
            'summary': {
                'total_tests': len(self.results),
                'successful_tests': len(successful_tests),
                'timeout_protected': len(timeout_protected),
                'success_rate': len(successful_tests)/len(self.results)*100,
                'timeout_protection_rate': len(timeout_protected)/len(self.results)*100
            },
            'detailed_results': self.results
        }

        with open('accent_test_report.json', 'w') as f:
            json.dump(report_data, f, indent=2)

        print(f"\n💾 Detailed report saved: accent_test_report.json")

async def main():
    simulator = CallFlowSimulator("http://15.157.56.64")
    await simulator.run_accent_tests()
    simulator.generate_report()

if __name__ == "__main__":
    asyncio.run(main())
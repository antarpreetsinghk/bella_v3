#!/usr/bin/env python3
"""
Load testing simulation for production call flow validation
Tests concurrent calls and response times under load
"""
import asyncio
import aiohttp
import time
import json
from datetime import datetime
from typing import List, Dict

class LoadTestSimulator:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.results = []

    async def simulate_concurrent_call(self, session: aiohttp.ClientSession,
                                     call_id: int, semaphore: asyncio.Semaphore):
        """Simulate a single concurrent call"""
        async with semaphore:
            call_sid = f"LOAD_TEST_{call_id}_{int(time.time())}"
            start_time = time.time()

            try:
                # Step 1: Name collection
                name_start = time.time()
                async with session.post(
                    f"{self.base_url}/twilio/voice/collect",
                    data={
                        'CallSid': call_sid,
                        'From': f'+1403555{call_id:04d}',
                        'SpeechResult': f'My name is Load Test User {call_id}',
                        'AccountSid': 'TEST_ACCOUNT',
                        'Direction': 'inbound'
                    },
                    headers={'Content-Type': 'application/x-www-form-urlencoded'},
                    timeout=10
                ) as response:
                    name_time = time.time() - name_start
                    name_success = response.status in [200, 403]

                # Step 2: Time collection (if name succeeded)
                time_response_time = 0
                time_success = False
                if name_success:
                    time_start = time.time()
                    async with session.post(
                        f"{self.base_url}/twilio/voice/collect",
                        data={
                            'CallSid': call_sid,
                            'From': f'+1403555{call_id:04d}',
                            'SpeechResult': 'tomorrow at 2 PM',
                            'AccountSid': 'TEST_ACCOUNT',
                            'Direction': 'inbound'
                        },
                        headers={'Content-Type': 'application/x-www-form-urlencoded'},
                        timeout=10
                    ) as response:
                        time_response_time = time.time() - time_start
                        time_success = response.status in [200, 403]

                total_time = time.time() - start_time

                return {
                    'call_id': call_id,
                    'success': name_success and time_success,
                    'total_time': total_time,
                    'name_step_time': name_time,
                    'time_step_time': time_response_time,
                    'max_step_time': max(name_time, time_response_time),
                    'timeout_protected': max(name_time, time_response_time) < 3.0
                }

            except Exception as e:
                return {
                    'call_id': call_id,
                    'success': False,
                    'total_time': time.time() - start_time,
                    'error': str(e),
                    'timeout_protected': False
                }

    async def run_load_test(self, concurrent_calls: int = 10, total_batches: int = 3):
        """Run load testing with concurrent calls"""
        print(f"🚀 Starting Load Test: {concurrent_calls} concurrent calls x {total_batches} batches")
        print("=" * 60)

        all_results = []
        semaphore = asyncio.Semaphore(concurrent_calls)

        connector = aiohttp.TCPConnector(limit=50)
        timeout = aiohttp.ClientTimeout(total=30)

        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            for batch in range(total_batches):
                print(f"\n📊 Batch {batch + 1}/{total_batches} - {concurrent_calls} concurrent calls")
                batch_start = time.time()

                # Create concurrent call tasks
                tasks = []
                for call_id in range(batch * concurrent_calls, (batch + 1) * concurrent_calls):
                    task = self.simulate_concurrent_call(session, call_id, semaphore)
                    tasks.append(task)

                # Execute all calls concurrently
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)

                # Process results
                valid_results = []
                for result in batch_results:
                    if isinstance(result, dict):
                        valid_results.append(result)
                        all_results.append(result)
                    else:
                        print(f"   ❌ Task failed: {result}")

                batch_time = time.time() - batch_start
                successful = [r for r in valid_results if r['success']]
                timeout_protected = [r for r in valid_results if r['timeout_protected']]

                if valid_results:
                    avg_response = sum(r['max_step_time'] for r in valid_results) / len(valid_results)
                    max_response = max(r['max_step_time'] for r in valid_results)
                    min_response = min(r['max_step_time'] for r in valid_results)

                    print(f"   ✅ Success: {len(successful)}/{len(valid_results)} calls")
                    print(f"   ⚡ Timeout protected: {len(timeout_protected)}/{len(valid_results)} calls")
                    print(f"   📈 Response times: {avg_response:.3f}s avg, {max_response:.3f}s max, {min_response:.3f}s min")
                    print(f"   🕒 Batch completed in: {batch_time:.2f}s")

                # Brief pause between batches
                if batch < total_batches - 1:
                    await asyncio.sleep(2)

        self.results = all_results
        return all_results

    def generate_load_report(self):
        """Generate comprehensive load testing report"""
        if not self.results:
            print("\\n❌ No load test results to analyze")
            return

        successful = [r for r in self.results if r['success']]
        timeout_protected = [r for r in self.results if r['timeout_protected']]

        print(f"\\n📊 LOAD TESTING REPORT")
        print("=" * 50)
        print(f"Total calls simulated: {len(self.results)}")
        print(f"Successful calls: {len(successful)}")
        print(f"Success rate: {len(successful)/len(self.results)*100:.1f}%")
        print(f"Timeout protection rate: {len(timeout_protected)/len(self.results)*100:.1f}%")

        if successful:
            response_times = [r['max_step_time'] for r in successful]
            total_times = [r['total_time'] for r in successful]

            print(f"\\n⚡ Performance Metrics:")
            print(f"   Step response time: {sum(response_times)/len(response_times):.3f}s avg")
            print(f"   Total call time: {sum(total_times)/len(total_times):.3f}s avg")
            print(f"   Fastest response: {min(response_times):.3f}s")
            print(f"   Slowest response: {max(response_times):.3f}s")

            # Performance thresholds
            fast_calls = [r for r in successful if r['max_step_time'] < 1.0]
            acceptable_calls = [r for r in successful if r['max_step_time'] < 3.0]

            print(f"\\n🎯 Performance Distribution:")
            print(f"   < 1.0s (excellent): {len(fast_calls)} calls ({len(fast_calls)/len(successful)*100:.1f}%)")
            print(f"   < 3.0s (acceptable): {len(acceptable_calls)} calls ({len(acceptable_calls)/len(successful)*100:.1f}%)")

        failed = [r for r in self.results if not r['success']]
        if failed:
            print(f"\\n❌ Failed Calls: {len(failed)}")
            for fail in failed[:5]:  # Show first 5 failures
                print(f"   Call {fail['call_id']}: {fail.get('error', 'Unknown error')}")

        # Save detailed report
        report_data = {
            'timestamp': time.time(),
            'test_type': 'load_testing',
            'summary': {
                'total_calls': len(self.results),
                'successful_calls': len(successful),
                'timeout_protected_calls': len(timeout_protected),
                'success_rate': len(successful)/len(self.results)*100,
                'timeout_protection_rate': len(timeout_protected)/len(self.results)*100
            },
            'detailed_results': self.results
        }

        with open('load_test_report.json', 'w') as f:
            json.dump(report_data, f, indent=2)

        print(f"\\n💾 Detailed report saved: load_test_report.json")

async def main():
    # Test with moderate load first
    simulator = LoadTestSimulator("http://15.157.56.64")

    print("🔥 PRODUCTION LOAD TESTING")
    print("Testing concurrent call handling and response times")
    print("=" * 60)

    # Run progressive load tests
    await simulator.run_load_test(concurrent_calls=5, total_batches=2)   # 10 calls
    await asyncio.sleep(3)
    await simulator.run_load_test(concurrent_calls=10, total_batches=2)  # 20 calls

    simulator.generate_load_report()

if __name__ == "__main__":
    asyncio.run(main())
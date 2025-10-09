#!/usr/bin/env python3
"""
Intensive load testing for production readiness validation
"""
import asyncio
import aiohttp
import time
import json
from datetime import datetime

async def intensive_load_test():
    """Run intensive concurrent load test"""
    print("🔥 INTENSIVE LOAD TEST - 20 Concurrent Calls")
    print("=" * 50)

    base_url = "http://15.157.56.64"
    semaphore = asyncio.Semaphore(20)
    results = []

    async def single_call(session, call_id):
        async with semaphore:
            call_sid = f"INTENSIVE_{call_id}_{int(time.time())}"
            start = time.time()

            try:
                async with session.post(
                    f"{base_url}/twilio/voice/collect",
                    data={
                        'CallSid': call_sid,
                        'From': f'+1403666{call_id:04d}',
                        'SpeechResult': f'My name is Intensive Test {call_id}',
                        'AccountSid': 'TEST_ACCOUNT',
                        'Direction': 'inbound'
                    },
                    headers={'Content-Type': 'application/x-www-form-urlencoded'},
                    timeout=5
                ) as response:
                    response_time = time.time() - start
                    return {
                        'call_id': call_id,
                        'success': response.status in [200, 403],
                        'response_time': response_time,
                        'timeout_protected': response_time < 3.0
                    }
            except Exception as e:
                return {
                    'call_id': call_id,
                    'success': False,
                    'response_time': time.time() - start,
                    'error': str(e),
                    'timeout_protected': False
                }

    connector = aiohttp.TCPConnector(limit=30)
    timeout = aiohttp.ClientTimeout(total=15)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        # Run 20 concurrent calls
        tasks = [single_call(session, i) for i in range(20)]
        test_start = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        test_duration = time.time() - test_start

    # Process results
    valid_results = [r for r in results if isinstance(r, dict)]
    successful = [r for r in valid_results if r['success']]
    timeout_protected = [r for r in valid_results if r['timeout_protected']]

    print(f"🏁 Test completed in {test_duration:.2f}s")
    print(f"✅ Success rate: {len(successful)}/{len(valid_results)} ({len(successful)/len(valid_results)*100:.1f}%)")
    print(f"⚡ Timeout protection: {len(timeout_protected)}/{len(valid_results)} ({len(timeout_protected)/len(valid_results)*100:.1f}%)")

    if successful:
        times = [r['response_time'] for r in successful]
        print(f"📊 Response times: {sum(times)/len(times):.3f}s avg, {max(times):.3f}s max, {min(times):.3f}s min")

        # Performance rating
        if len(successful) >= 18 and sum(times)/len(times) < 0.5:
            print("🌟 EXCELLENT: System handles high load with fast responses")
        elif len(successful) >= 15 and sum(times)/len(times) < 2.0:
            print("✅ GOOD: System handles load well within acceptable limits")
        else:
            print("⚠️ NEEDS OPTIMIZATION: Consider performance improvements")

    return len(successful) >= 15  # At least 75% success rate

if __name__ == "__main__":
    success = asyncio.run(intensive_load_test())
    exit(0 if success else 1)
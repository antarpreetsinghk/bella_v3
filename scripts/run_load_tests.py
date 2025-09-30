#!/usr/bin/env python3
"""
Quick load testing script for Bella V3.
"""

import asyncio
import aiohttp
import time
import sys
import os

async def test_endpoint(session, url, data=None):
    """Test a single endpoint"""
    start = time.time()
    try:
        if data:
            async with session.post(url, data=data) as response:
                await response.text()
                return time.time() - start, response.status
        else:
            async with session.get(url) as response:
                await response.text()
                return time.time() - start, response.status
    except Exception as e:
        return time.time() - start, 0

async def run_concurrent_tests(base_url, api_key, num_concurrent=10):
    """Run concurrent tests"""
    print(f"🔥 Testing {num_concurrent} concurrent requests...")

    timeout = aiohttp.ClientTimeout(total=30)
    headers = {'X-API-Key': api_key}

    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
        # Test dashboard endpoint
        tasks = []
        for i in range(num_concurrent):
            task = test_endpoint(session, f"{base_url}/api/unified/status")
            tasks.append(task)

        start_time = time.time()
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time

        response_times = [r[0] for r in results]
        status_codes = [r[1] for r in results]

        successful = len([s for s in status_codes if s == 200])
        avg_response = sum(response_times) / len(response_times)
        max_response = max(response_times)

        print(f"   ✅ {successful}/{num_concurrent} successful")
        print(f"   ⚡ Avg response: {avg_response:.3f}s")
        print(f"   📊 Max response: {max_response:.3f}s")
        print(f"   🚀 Total time: {total_time:.2f}s")

        return avg_response < 2.0 and successful >= num_concurrent * 0.9

async def main():
    base_url = "http://localhost:8002"
    api_key = "bella-dev-key-2024"

    print("🚀 Bella V3 Quick Performance Test")
    print("=" * 40)

    # Test increasing load
    for concurrent in [5, 10, 20]:
        success = await run_concurrent_tests(base_url, api_key, concurrent)
        if not success:
            print(f"❌ Performance degraded at {concurrent} concurrent requests")
            break
        else:
            print(f"✅ Passed {concurrent} concurrent requests test")

        await asyncio.sleep(1)  # Brief pause between tests

    print("\n✨ Load testing complete!")

if __name__ == "__main__":
    asyncio.run(main())
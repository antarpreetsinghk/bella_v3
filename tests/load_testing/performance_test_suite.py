#!/usr/bin/env python3
"""
Comprehensive load testing suite for Bella V3 voice appointment booking system.
Tests concurrent call handling, response times, and system stability under load.
"""

import asyncio
import aiohttp
import time
import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import statistics
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class LoadTestResult:
    """Individual test result"""
    test_name: str
    start_time: float
    end_time: float
    status_code: int
    response_time: float
    success: bool
    error_message: Optional[str] = None
    response_size: int = 0

@dataclass
class LoadTestSummary:
    """Load test summary statistics"""
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    p95_response_time: float
    p99_response_time: float
    requests_per_second: float
    total_duration: float
    error_rate: float
    errors: Dict[str, int] = field(default_factory=dict)

class VoiceCallSimulator:
    """Simulates Twilio voice call webhooks for load testing"""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=30, connect=5)
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            headers={'X-API-Key': self.api_key}
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def simulate_call_start(self, call_sid: str) -> LoadTestResult:
        """Simulate initial call webhook"""
        start_time = time.time()
        test_name = f"call_start_{call_sid}"

        try:
            url = f"{self.base_url}/twilio/voice"
            data = {
                'CallSid': call_sid,
                'From': '+15551234567',
                'To': '+15559876543',
                'CallStatus': 'in-progress',
                'Direction': 'inbound'
            }

            async with self.session.post(url, data=data) as response:
                end_time = time.time()
                response_text = await response.text()

                return LoadTestResult(
                    test_name=test_name,
                    start_time=start_time,
                    end_time=end_time,
                    status_code=response.status,
                    response_time=end_time - start_time,
                    success=response.status == 200,
                    response_size=len(response_text)
                )

        except Exception as e:
            end_time = time.time()
            return LoadTestResult(
                test_name=test_name,
                start_time=start_time,
                end_time=end_time,
                status_code=0,
                response_time=end_time - start_time,
                success=False,
                error_message=str(e)
            )

    async def simulate_speech_input(self, call_sid: str, speech_text: str) -> LoadTestResult:
        """Simulate speech input webhook with gather results"""
        start_time = time.time()
        test_name = f"speech_input_{call_sid}"

        try:
            url = f"{self.base_url}/twilio/voice/collect"
            data = {
                'CallSid': call_sid,
                'SpeechResult': speech_text,
                'Confidence': '0.95',
                'From': '+15551234567',
                'To': '+15559876543'
            }

            async with self.session.post(url, data=data) as response:
                end_time = time.time()
                response_text = await response.text()

                return LoadTestResult(
                    test_name=test_name,
                    start_time=start_time,
                    end_time=end_time,
                    status_code=response.status,
                    response_time=end_time - start_time,
                    success=response.status == 200,
                    response_size=len(response_text)
                )

        except Exception as e:
            end_time = time.time()
            return LoadTestResult(
                test_name=test_name,
                start_time=start_time,
                end_time=end_time,
                status_code=0,
                response_time=end_time - start_time,
                success=False,
                error_message=str(e)
            )

    async def simulate_dashboard_access(self) -> LoadTestResult:
        """Simulate dashboard access for concurrent load"""
        start_time = time.time()
        test_name = "dashboard_access"

        try:
            url = f"{self.base_url}/api/unified/status"

            async with self.session.get(url) as response:
                end_time = time.time()
                response_text = await response.text()

                return LoadTestResult(
                    test_name=test_name,
                    start_time=start_time,
                    end_time=end_time,
                    status_code=response.status,
                    response_time=end_time - start_time,
                    success=response.status == 200,
                    response_size=len(response_text)
                )

        except Exception as e:
            end_time = time.time()
            return LoadTestResult(
                test_name=test_name,
                start_time=start_time,
                end_time=end_time,
                status_code=0,
                response_time=end_time - start_time,
                success=False,
                error_message=str(e)
            )

class LoadTestRunner:
    """Orchestrates load testing scenarios"""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key
        self.results: List[LoadTestResult] = []

    async def run_concurrent_calls_test(self, num_calls: int, call_duration: float = 10.0) -> LoadTestSummary:
        """Test concurrent call handling capacity"""
        logger.info(f"Starting concurrent calls test: {num_calls} simultaneous calls")

        async with VoiceCallSimulator(self.base_url, self.api_key) as simulator:
            tasks = []

            # Create concurrent call simulation tasks
            for i in range(num_calls):
                call_sid = f"CA_load_test_{i}_{int(time.time())}"
                task = self._simulate_full_call(simulator, call_sid, call_duration)
                tasks.append(task)

            # Execute all calls concurrently
            start_time = time.time()
            call_results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()

            # Process results
            results = []
            for result_set in call_results:
                if isinstance(result_set, Exception):
                    logger.error(f"Call simulation failed: {result_set}")
                    continue
                if isinstance(result_set, list):
                    results.extend(result_set)

            return self._calculate_summary(results, end_time - start_time)

    async def _simulate_full_call(self, simulator: VoiceCallSimulator, call_sid: str, duration: float) -> List[LoadTestResult]:
        """Simulate a complete call flow"""
        results = []

        # 1. Call start
        result = await simulator.simulate_call_start(call_sid)
        results.append(result)

        if not result.success:
            return results

        # 2. Simulate natural call progression with delays
        speech_inputs = [
            "Hi, I'd like to book an appointment",
            "John Smith",
            "555-123-4567",
            "Tomorrow at 2 PM",
            "Yes, that works perfect"
        ]

        for i, speech in enumerate(speech_inputs):
            # Realistic delay between speech inputs (1-3 seconds)
            await asyncio.sleep(0.5 + (i * 0.3))

            result = await simulator.simulate_speech_input(call_sid, speech)
            results.append(result)

            if not result.success:
                break

        return results

    async def run_dashboard_load_test(self, concurrent_users: int, duration_seconds: float = 30.0) -> LoadTestSummary:
        """Test dashboard under concurrent user load"""
        logger.info(f"Starting dashboard load test: {concurrent_users} concurrent users for {duration_seconds}s")

        async with VoiceCallSimulator(self.base_url, self.api_key) as simulator:
            tasks = []
            end_time = time.time() + duration_seconds

            # Create concurrent dashboard access tasks
            for i in range(concurrent_users):
                task = self._simulate_dashboard_user(simulator, end_time)
                tasks.append(task)

            # Execute all user simulations concurrently
            start_time = time.time()
            user_results = await asyncio.gather(*tasks, return_exceptions=True)
            actual_end_time = time.time()

            # Process results
            results = []
            for result_set in user_results:
                if isinstance(result_set, Exception):
                    logger.error(f"Dashboard user simulation failed: {result_set}")
                    continue
                if isinstance(result_set, list):
                    results.extend(result_set)

            return self._calculate_summary(results, actual_end_time - start_time)

    async def _simulate_dashboard_user(self, simulator: VoiceCallSimulator, end_time: float) -> List[LoadTestResult]:
        """Simulate a dashboard user session"""
        results = []

        while time.time() < end_time:
            # Simulate realistic dashboard usage pattern
            result = await simulator.simulate_dashboard_access()
            results.append(result)

            # Realistic user interaction delay (2-5 seconds)
            await asyncio.sleep(2 + (time.time() % 3))

        return results

    async def run_stress_test(self, max_concurrent: int, ramp_up_time: float = 10.0) -> Dict[int, LoadTestSummary]:
        """Run stress test with gradually increasing load"""
        logger.info(f"Starting stress test: ramping up to {max_concurrent} concurrent calls over {ramp_up_time}s")

        results = {}
        step_size = max(1, max_concurrent // 10)  # 10 steps

        for concurrent_level in range(step_size, max_concurrent + 1, step_size):
            logger.info(f"Testing {concurrent_level} concurrent calls...")

            summary = await self.run_concurrent_calls_test(concurrent_level, call_duration=5.0)
            results[concurrent_level] = summary

            # Brief pause between stress levels
            await asyncio.sleep(2.0)

            # Stop if error rate becomes too high
            if summary.error_rate > 0.2:  # 20% error rate threshold
                logger.warning(f"High error rate ({summary.error_rate:.1%}) at {concurrent_level} concurrent calls")
                break

        return results

    def _calculate_summary(self, results: List[LoadTestResult], total_duration: float) -> LoadTestSummary:
        """Calculate summary statistics from test results"""
        if not results:
            return LoadTestSummary(
                total_requests=0,
                successful_requests=0,
                failed_requests=0,
                avg_response_time=0.0,
                min_response_time=0.0,
                max_response_time=0.0,
                p95_response_time=0.0,
                p99_response_time=0.0,
                requests_per_second=0.0,
                total_duration=total_duration,
                error_rate=1.0
            )

        successful_results = [r for r in results if r.success]
        failed_results = [r for r in results if not r.success]

        response_times = [r.response_time for r in successful_results]

        # Calculate percentiles
        if response_times:
            response_times.sort()
            p95_index = int(0.95 * len(response_times))
            p99_index = int(0.99 * len(response_times))

            avg_response_time = statistics.mean(response_times)
            min_response_time = min(response_times)
            max_response_time = max(response_times)
            p95_response_time = response_times[p95_index] if p95_index < len(response_times) else max_response_time
            p99_response_time = response_times[p99_index] if p99_index < len(response_times) else max_response_time
        else:
            avg_response_time = min_response_time = max_response_time = 0.0
            p95_response_time = p99_response_time = 0.0

        # Count error types
        errors = {}
        for result in failed_results:
            error_key = f"HTTP_{result.status_code}" if result.status_code > 0 else "Connection_Error"
            errors[error_key] = errors.get(error_key, 0) + 1

        return LoadTestSummary(
            total_requests=len(results),
            successful_requests=len(successful_results),
            failed_requests=len(failed_results),
            avg_response_time=avg_response_time,
            min_response_time=min_response_time,
            max_response_time=max_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            requests_per_second=len(results) / total_duration if total_duration > 0 else 0,
            total_duration=total_duration,
            error_rate=len(failed_results) / len(results),
            errors=errors
        )

    def print_summary(self, summary: LoadTestSummary, test_name: str):
        """Print formatted test summary"""
        print(f"\n🔥 {test_name} Results:")
        print(f"   Total Requests: {summary.total_requests}")
        print(f"   Successful: {summary.successful_requests} ({(1-summary.error_rate):.1%})")
        print(f"   Failed: {summary.failed_requests} ({summary.error_rate:.1%})")
        print(f"   Requests/sec: {summary.requests_per_second:.1f}")
        print(f"   Duration: {summary.total_duration:.1f}s")
        print(f"\n⚡ Response Times:")
        print(f"   Average: {summary.avg_response_time:.3f}s")
        print(f"   Min: {summary.min_response_time:.3f}s")
        print(f"   Max: {summary.max_response_time:.3f}s")
        print(f"   95th percentile: {summary.p95_response_time:.3f}s")
        print(f"   99th percentile: {summary.p99_response_time:.3f}s")

        if summary.errors:
            print(f"\n❌ Errors:")
            for error_type, count in summary.errors.items():
                print(f"   {error_type}: {count}")

async def run_performance_tests():
    """Main test execution function"""
    base_url = "http://localhost:8002"  # Use local test server
    api_key = "bella-dev-key-2024"

    runner = LoadTestRunner(base_url, api_key)

    print("🚀 Starting Bella V3 Performance Test Suite")
    print("=" * 50)

    # Test 1: Basic concurrent calls (target: handle 10 concurrent calls)
    summary = await runner.run_concurrent_calls_test(num_calls=10, call_duration=8.0)
    runner.print_summary(summary, "10 Concurrent Calls Test")

    # Test 2: Dashboard load (target: 20 concurrent users)
    summary = await runner.run_dashboard_load_test(concurrent_users=20, duration_seconds=15.0)
    runner.print_summary(summary, "Dashboard Load Test (20 users)")

    # Test 3: Stress test (find breaking point)
    print(f"\n🔬 Running Stress Test...")
    stress_results = await runner.run_stress_test(max_concurrent=50, ramp_up_time=5.0)

    print(f"\n📊 Stress Test Results:")
    for concurrent_level, summary in stress_results.items():
        status = "✅" if summary.error_rate < 0.1 else "⚠️" if summary.error_rate < 0.2 else "❌"
        print(f"   {status} {concurrent_level} concurrent: {summary.avg_response_time:.2f}s avg, {summary.error_rate:.1%} errors")

    # Performance recommendations
    print(f"\n💡 Performance Analysis:")
    if stress_results:
        max_stable = max([level for level, summary in stress_results.items() if summary.error_rate < 0.1], default=0)
        print(f"   Maximum stable load: {max_stable} concurrent calls")

        best_summary = stress_results.get(max_stable)
        if best_summary and best_summary.avg_response_time < 2.0:
            print(f"   ✅ Target achieved: <2s average response time ({best_summary.avg_response_time:.2f}s)")
        else:
            print(f"   ⚠️ Target missed: >2s average response time")

if __name__ == "__main__":
    asyncio.run(run_performance_tests())
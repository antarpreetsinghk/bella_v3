#!/usr/bin/env python3
"""
Performance and load testing suite for call flow system.
Tests response times, throughput, and resource usage under load.
"""

import pytest
import sys
import os
import time
import threading
import asyncio
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# Add app to Python path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.main import app


class TestResponseTimeRequirements:
    """Test response time requirements for Twilio webhooks"""

    @pytest.mark.performance
    @pytest.mark.slow
    def test_voice_entry_response_time(self):
        """Test that voice entry responds within Twilio timeout"""
        client = TestClient(app)

        # Test multiple calls to get average
        response_times = []
        for i in range(10):
            start_time = time.time()
            response = client.post("/twilio/voice", data={
                "CallSid": f"TEST_TIMING_{i}",
                "From": "+14165551234",
                "AccountSid": "TEST_ACCOUNT"
            })
            end_time = time.time()

            assert response.status_code == 200
            response_times.append(end_time - start_time)

        # All responses should be well under Twilio's 10-second timeout
        max_time = max(response_times)
        avg_time = sum(response_times) / len(response_times)

        assert max_time < 1.0  # Maximum 1 second
        assert avg_time < 0.5  # Average under 500ms

    @pytest.mark.performance
    @pytest.mark.slow
    def test_voice_collect_response_time(self):
        """Test that voice collection responds quickly"""
        client = TestClient(app)

        # Establish session first
        client.post("/twilio/voice", data={
            "CallSid": "TEST_COLLECT_TIMING",
            "From": "+14165551234",
            "AccountSid": "TEST_ACCOUNT"
        })

        # Test collection response times
        response_times = []
        for i in range(10):
            start_time = time.time()
            response = client.post("/twilio/voice/collect", data={
                "CallSid": "TEST_COLLECT_TIMING",
                "SpeechResult": f"Test speech {i}",
                "Confidence": "0.95"
            })
            end_time = time.time()

            assert response.status_code == 200
            response_times.append(end_time - start_time)

        max_time = max(response_times)
        avg_time = sum(response_times) / len(response_times)

        assert max_time < 1.0  # Maximum 1 second
        assert avg_time < 0.3  # Average under 300ms

    @pytest.mark.essential
    @pytest.mark.performance
    @pytest.mark.slow
    @pytest.mark.unit
    def test_extraction_function_performance(self):
        """Test extraction function performance"""
        from app.services.simple_extraction import extract_name_simple, extract_phone_simple
        from app.api.routes.twilio import _extract_phone_fast

        test_inputs = [
            "John Smith",
            "my name is Mary Elizabeth Johnson-Wilson",
            "416-555-1234",
            "four one six five five five one two three four",
            "I need to book an appointment for tomorrow at 2 PM"
        ]

        # Test individual function performance
        start_time = time.time()
        for _ in range(1000):
            for input_text in test_inputs:
                extract_name_simple(input_text)
                extract_phone_simple(input_text)
                _extract_phone_fast(input_text)
        end_time = time.time()

        total_operations = 1000 * len(test_inputs) * 3  # 3 functions
        operations_per_second = total_operations / (end_time - start_time)

        # Should handle thousands of operations per second
        assert operations_per_second > 5000

    @patch('app.services.redis_session.get_redis_client')
    @pytest.mark.essential
    @pytest.mark.performance
    @pytest.mark.slow
    def test_session_operations_performance(self, mock_redis):
        """Test session storage/retrieval performance"""
        from app.services.redis_session import get_session, save_session

        mock_client = MagicMock()
        mock_client.get.return_value = None
        mock_redis.return_value = mock_client

        # Test Redis session operations
        start_time = time.time()
        for i in range(100):
            session = get_session(f"TEST_PERF_{i}")
            session.data["test"] = f"value_{i}"
            save_session(session)
        end_time = time.time()

        operations_per_second = (100 * 2) / (end_time - start_time)  # get + save
        assert operations_per_second > 200  # Should handle 200+ ops/sec

    @pytest.mark.essential
    @pytest.mark.performance
    @pytest.mark.slow
    def test_memory_session_performance(self):
        """Test in-memory session performance"""
        from app.services.redis_session import get_session

        with patch('app.services.redis_session.get_redis_client') as mock_redis:
            mock_redis.return_value = None  # Force memory storage

            start_time = time.time()
            for i in range(500):
                session = get_session(f"TEST_MEM_PERF_{i}")
                session.step = "ask_mobile"
                session.data["test"] = f"data_{i}"
            end_time = time.time()

            operations_per_second = 500 / (end_time - start_time)
            assert operations_per_second > 1000  # Memory should be very fast


class TestConcurrentCallHandling:
    """Test system behavior under concurrent load"""

    @pytest.mark.performance
    @pytest.mark.slow
    def test_concurrent_new_calls(self):
        """Test handling multiple simultaneous new calls"""
        client = TestClient(app)
        num_concurrent = 20
        results = []

        def make_call(call_id):
            try:
                start_time = time.time()
                response = client.post("/twilio/voice", data={
                    "CallSid": f"TEST_CONCURRENT_{call_id}",
                    "From": f"+141655512{call_id:02d}",
                    "AccountSid": "TEST_ACCOUNT"
                })
                end_time = time.time()
                results.append({
                    "call_id": call_id,
                    "status": response.status_code,
                    "response_time": end_time - start_time,
                    "success": response.status_code == 200
                })
            except Exception as e:
                results.append({
                    "call_id": call_id,
                    "status": "ERROR",
                    "error": str(e),
                    "success": False
                })

        # Start concurrent calls
        threads = []
        start_time = time.time()

        for i in range(num_concurrent):
            thread = threading.Thread(target=make_call, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all to complete
        for thread in threads:
            thread.join(timeout=10)

        end_time = time.time()
        total_time = end_time - start_time

        # Verify results
        assert len(results) == num_concurrent
        successful_calls = [r for r in results if r["success"]]
        success_rate = len(successful_calls) / num_concurrent

        assert success_rate >= 0.95  # 95% success rate
        assert total_time < 5.0  # All calls complete within 5 seconds

        # Check individual response times
        response_times = [r["response_time"] for r in successful_calls if "response_time" in r]
        if response_times:
            max_response_time = max(response_times)
            avg_response_time = sum(response_times) / len(response_times)

            assert max_response_time < 2.0  # No call takes more than 2 seconds
            assert avg_response_time < 1.0  # Average under 1 second

    @pytest.mark.essential
    @pytest.mark.performance
    @pytest.mark.slow
    def test_concurrent_session_operations(self):
        """Test concurrent session operations"""
        client = TestClient(app)
        num_sessions = 50
        results = []

        def session_workflow(session_id):
            try:
                call_sid = f"TEST_SESSION_{session_id}"

                # Initial call
                start_time = time.time()
                response1 = client.post("/twilio/voice", data={
                    "CallSid": call_sid,
                    "From": f"+141655512{session_id:02d}",
                    "AccountSid": "TEST_ACCOUNT"
                })

                # Follow-up interaction
                response2 = client.post("/twilio/voice/collect", data={
                    "CallSid": call_sid,
                    "SpeechResult": f"Test Name {session_id}",
                    "Confidence": "0.95"
                })

                end_time = time.time()
                results.append({
                    "session_id": session_id,
                    "success": response1.status_code == 200 and response2.status_code == 200,
                    "total_time": end_time - start_time
                })
            except Exception as e:
                results.append({
                    "session_id": session_id,
                    "success": False,
                    "error": str(e)
                })

        # Run concurrent session workflows
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(session_workflow, i) for i in range(num_sessions)]

            # Wait for completion
            for future in futures:
                future.result(timeout=30)

        # Verify results
        assert len(results) == num_sessions
        successful_sessions = [r for r in results if r["success"]]
        success_rate = len(successful_sessions) / num_sessions

        assert success_rate >= 0.90  # 90% success rate for concurrent sessions

    @patch('app.services.redis_session.get_redis_client')
    @pytest.mark.integration
    @pytest.mark.performance
    @pytest.mark.slow
    def test_redis_connection_pool_stress(self, mock_redis):
        """Test Redis connection handling under stress"""
        # Mock Redis client with realistic latency
        mock_client = MagicMock()

        def mock_get(key):
            time.sleep(0.001)  # Simulate 1ms Redis latency
            return None

        def mock_setex(key, ttl, value):
            time.sleep(0.001)  # Simulate 1ms Redis latency
            return True

        mock_client.get.side_effect = mock_get
        mock_client.setex.side_effect = mock_setex
        mock_redis.return_value = mock_client

        from app.services.redis_session import get_session

        # Stress test Redis operations
        num_operations = 100
        results = []

        def redis_operations(op_id):
            try:
                start_time = time.time()
                session = get_session(f"STRESS_TEST_{op_id}")
                session.data["test"] = f"value_{op_id}"
                end_time = time.time()

                results.append({
                    "op_id": op_id,
                    "success": True,
                    "time": end_time - start_time
                })
            except Exception as e:
                results.append({
                    "op_id": op_id,
                    "success": False,
                    "error": str(e)
                })

        # Run concurrent Redis operations
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(redis_operations, i) for i in range(num_operations)]

            for future in futures:
                future.result(timeout=10)

        # Verify Redis stress handling
        assert len(results) == num_operations
        successful_ops = [r for r in results if r["success"]]
        success_rate = len(successful_ops) / num_operations

        assert success_rate >= 0.95  # Should handle Redis load well


class TestMemoryAndResourceUsage:
    """Test memory usage and resource consumption"""

    @pytest.mark.performance
    @pytest.mark.slow
    def test_memory_usage_during_load(self):
        """Test memory usage under sustained load"""
        try:
            import psutil
            import os

            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss
        except ImportError:
            pytest.skip("psutil not available for memory testing")

        client = TestClient(app)

        # Create sustained load
        for i in range(200):
            # Create session
            response = client.post("/twilio/voice", data={
                "CallSid": f"TEST_MEMORY_{i}",
                "From": f"+141655512{i:03d}",
                "AccountSid": "TEST_ACCOUNT"
            })
            assert response.status_code == 200

            # Interact with session
            client.post("/twilio/voice/collect", data={
                "CallSid": f"TEST_MEMORY_{i}",
                "SpeechResult": f"Customer Name {i}",
                "Confidence": "0.95"
            })

            # Check memory periodically
            if i % 50 == 0:
                current_memory = process.memory_info().rss
                memory_growth = current_memory - initial_memory

                # Memory growth should be reasonable (less than 50MB per 50 sessions)
                assert memory_growth < 50 * 1024 * 1024

        # Final memory check
        final_memory = process.memory_info().rss
        total_growth = final_memory - initial_memory

        # Total memory growth should be under 200MB for 200 sessions
        assert total_growth < 200 * 1024 * 1024

    @pytest.mark.essential
    @pytest.mark.performance
    @pytest.mark.slow
    def test_session_cleanup_effectiveness(self):
        """Test that old sessions are properly cleaned up"""
        from app.services.redis_session import _sessions_memory, get_session

        with patch('app.services.redis_session.get_redis_client') as mock_redis:
            mock_redis.return_value = None  # Force memory storage

            initial_session_count = len(_sessions_memory)

            # Create many sessions
            for i in range(100):
                get_session(f"TEST_CLEANUP_{i}")

            mid_session_count = len(_sessions_memory)
            assert mid_session_count > initial_session_count

            # Simulate time passing and create new session to trigger cleanup
            from datetime import datetime, timedelta
            from app.services.redis_session import TTL_MINUTES

            # Age all sessions
            for session in _sessions_memory.values():
                session.updated_at = datetime.utcnow() - timedelta(minutes=TTL_MINUTES + 1)

            # Create new session to trigger cleanup
            get_session("TRIGGER_CLEANUP")

            final_session_count = len(_sessions_memory)

            # Should have cleaned up old sessions
            assert final_session_count < mid_session_count

    @pytest.mark.performance
    @pytest.mark.slow
    def test_garbage_collection_impact(self):
        """Test impact of garbage collection on response times"""
        import gc
        client = TestClient(app)

        # Create objects that might need GC
        large_objects = []
        for i in range(100):
            large_objects.append([f"data_{j}" for j in range(1000)])

        # Disable automatic GC
        gc.disable()

        try:
            # Measure response time with GC disabled
            start_time = time.time()
            response = client.post("/twilio/voice", data={
                "CallSid": "TEST_GC_DISABLED",
                "From": "+14165551234",
                "AccountSid": "TEST_ACCOUNT"
            })
            gc_disabled_time = time.time() - start_time

            assert response.status_code == 200

            # Force GC and measure again
            gc.collect()

            start_time = time.time()
            response = client.post("/twilio/voice", data={
                "CallSid": "TEST_GC_ENABLED",
                "From": "+14165551234",
                "AccountSid": "TEST_ACCOUNT"
            })
            gc_enabled_time = time.time() - start_time

            assert response.status_code == 200

            # GC shouldn't significantly impact response time
            assert abs(gc_enabled_time - gc_disabled_time) < 0.1

        finally:
            gc.enable()
            del large_objects


class TestScalabilityLimits:
    """Test system behavior at scalability limits"""

    @pytest.mark.performance
    @pytest.mark.slow
    def test_maximum_concurrent_calls(self):
        """Test system behavior at maximum expected concurrent load"""
        client = TestClient(app)
        max_concurrent = 50  # Adjust based on expected system limits
        results = []

        def heavy_call_workflow(call_id):
            try:
                call_sid = f"TEST_MAX_LOAD_{call_id}"
                start_time = time.time()

                # Initial call
                response1 = client.post("/twilio/voice", data={
                    "CallSid": call_sid,
                    "From": f"+141655512{call_id:02d}",
                    "AccountSid": "TEST_ACCOUNT"
                })

                # Multiple interactions
                for step in range(5):
                    client.post("/twilio/voice/collect", data={
                        "CallSid": call_sid,
                        "SpeechResult": f"Step {step} data for call {call_id}",
                        "Confidence": "0.85"
                    })

                end_time = time.time()
                results.append({
                    "call_id": call_id,
                    "success": response1.status_code == 200,
                    "total_time": end_time - start_time
                })

            except Exception as e:
                results.append({
                    "call_id": call_id,
                    "success": False,
                    "error": str(e)
                })

        # Launch maximum load
        with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            futures = [executor.submit(heavy_call_workflow, i) for i in range(max_concurrent)]

            # Wait for completion with generous timeout
            for future in futures:
                try:
                    future.result(timeout=60)
                except Exception as e:
                    print(f"Future failed: {e}")

        # Analyze results
        assert len(results) == max_concurrent
        successful_calls = [r for r in results if r["success"]]
        success_rate = len(successful_calls) / max_concurrent

        # Should maintain reasonable success rate even under max load
        assert success_rate >= 0.80  # 80% success rate under max load

    @pytest.mark.performance
    @pytest.mark.slow
    def test_sustained_load_stability(self):
        """Test system stability under sustained load over time"""
        client = TestClient(app)
        duration_seconds = 30  # Run for 30 seconds
        calls_per_second = 2
        total_calls = duration_seconds * calls_per_second

        results = []
        start_time = time.time()

        for i in range(total_calls):
            call_start = time.time()

            try:
                response = client.post("/twilio/voice", data={
                    "CallSid": f"TEST_SUSTAINED_{i}",
                    "From": f"+141655512{i:03d}",
                    "AccountSid": "TEST_ACCOUNT"
                })

                call_end = time.time()
                results.append({
                    "call_id": i,
                    "success": response.status_code == 200,
                    "response_time": call_end - call_start,
                    "timestamp": call_end - start_time
                })

            except Exception as e:
                results.append({
                    "call_id": i,
                    "success": False,
                    "error": str(e),
                    "timestamp": time.time() - start_time
                })

            # Rate limiting to maintain calls_per_second
            elapsed = time.time() - call_start
            sleep_time = (1.0 / calls_per_second) - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

        # Analyze sustained performance
        successful_calls = [r for r in results if r["success"]]
        success_rate = len(successful_calls) / len(results)

        assert success_rate >= 0.95  # Should maintain high success rate

        # Check for performance degradation over time
        first_half = [r for r in successful_calls if r["timestamp"] < duration_seconds / 2]
        second_half = [r for r in successful_calls if r["timestamp"] >= duration_seconds / 2]

        if first_half and second_half:
            first_half_avg = sum(r["response_time"] for r in first_half) / len(first_half)
            second_half_avg = sum(r["response_time"] for r in second_half) / len(second_half)

            # Performance shouldn't degrade significantly over time
            degradation_ratio = second_half_avg / first_half_avg
            assert degradation_ratio < 2.0  # Less than 2x degradation


class TestPerformanceBenchmarks:
    """Establish performance benchmarks for the system"""

    @pytest.mark.performance
    @pytest.mark.slow
    def test_single_call_benchmark(self):
        """Establish baseline performance for single call"""
        client = TestClient(app)

        # Warm up
        for _ in range(5):
            client.post("/twilio/voice", data={
                "CallSid": "WARMUP",
                "From": "+14165551234",
                "AccountSid": "TEST_ACCOUNT"
            })

        # Benchmark single call
        response_times = []
        for i in range(20):
            start_time = time.time()
            response = client.post("/twilio/voice", data={
                "CallSid": f"BENCHMARK_{i}",
                "From": "+14165551234",
                "AccountSid": "TEST_ACCOUNT"
            })
            end_time = time.time()

            assert response.status_code == 200
            response_times.append(end_time - start_time)

        # Calculate statistics
        avg_time = sum(response_times) / len(response_times)
        min_time = min(response_times)
        max_time = max(response_times)
        p95_time = sorted(response_times)[int(len(response_times) * 0.95)]

        print(f"\nSingle Call Benchmark:")
        print(f"  Average: {avg_time:.3f}s")
        print(f"  Minimum: {min_time:.3f}s")
        print(f"  Maximum: {max_time:.3f}s")
        print(f"  95th percentile: {p95_time:.3f}s")

        # Assertions for acceptable performance
        assert avg_time < 0.1  # Average under 100ms
        assert p95_time < 0.2  # 95% under 200ms
        assert max_time < 0.5  # Maximum under 500ms

    @pytest.mark.performance
    @pytest.mark.slow
    def test_throughput_benchmark(self):
        """Establish throughput benchmark"""
        client = TestClient(app)
        num_calls = 100
        start_time = time.time()

        # Sequential calls to measure throughput
        successful_calls = 0
        for i in range(num_calls):
            response = client.post("/twilio/voice", data={
                "CallSid": f"THROUGHPUT_{i}",
                "From": f"+141655512{i:02d}",
                "AccountSid": "TEST_ACCOUNT"
            })
            if response.status_code == 200:
                successful_calls += 1

        end_time = time.time()
        total_time = end_time - start_time
        calls_per_second = successful_calls / total_time

        print(f"\nThroughput Benchmark:")
        print(f"  Total calls: {num_calls}")
        print(f"  Successful calls: {successful_calls}")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Calls per second: {calls_per_second:.1f}")

        # Should handle at least 50 calls per second
        assert calls_per_second >= 50
        assert successful_calls >= num_calls * 0.99  # 99% success rate


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
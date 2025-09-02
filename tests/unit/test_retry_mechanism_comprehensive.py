#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Comprehensive tests for retry mechanism functionality.
"""
import asyncio
import unittest
import time
import sys
import os
from unittest.mock import patch, MagicMock, AsyncMock
import httpx

# Add parent directory to path to allow importing from project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils import retry, async_retry, get_retry_stats_summary, reset_retry_stats, RetryConfig
from rate_limiter import RateLimiter, RateLimitConfig, TokenBucket

class TestRetryMechanism(unittest.TestCase):
    """Comprehensive tests for retry mechanism"""
    
    def setUp(self):
        """Reset statistics before each test"""
        reset_retry_stats()
        self.failure_counter = 0
    
    def test_retry_config_creation(self):
        """Test RetryConfig creation and validation"""
        # Test default config
        config = RetryConfig()
        self.assertEqual(config.max_attempts, 3)
        self.assertEqual(config.base_delay, 1.0)
        self.assertEqual(config.max_delay, 30.0)
        self.assertTrue(config.jitter)
        
        # Test custom config
        config = RetryConfig(
            max_attempts=5,
            base_delay=0.5,
            max_delay=60.0,
            jitter=False
        )
        self.assertEqual(config.max_attempts, 5)
        self.assertEqual(config.base_delay, 0.5)
        self.assertEqual(config.max_delay, 60.0)
        self.assertFalse(config.jitter)
    
    def test_retry_with_connection_error(self):
        """Test retry mechanism with connection errors"""
        retry_config = RetryConfig(max_attempts=3, base_delay=0.1, max_delay=1.0)
        
        @retry(retry_config=retry_config)
        def failing_function():
            self.failure_counter += 1
            if self.failure_counter < 3:
                raise ConnectionError(f"Connection failed {self.failure_counter}")
            return "Success"
        
        result = failing_function()
        self.assertEqual(result, "Success")
        self.assertEqual(self.failure_counter, 3)
        
        # Check retry statistics
        summary = get_retry_stats_summary()
        self.assertIn("Operations with retries: 1", summary)
        self.assertIn("Total retry attempts: 2", summary)
    
    def test_retry_with_timeout_error(self):
        """Test retry mechanism with timeout errors"""
        retry_config = RetryConfig(max_attempts=4, base_delay=0.1)
        
        @retry(retry_config=retry_config)
        def timeout_function():
            self.failure_counter += 1
            if self.failure_counter < 3:
                raise TimeoutError(f"Timeout {self.failure_counter}")
            return "Timeout resolved"
        
        result = timeout_function()
        self.assertEqual(result, "Timeout resolved")
        self.assertEqual(self.failure_counter, 3)
    
    def test_retry_with_http_status_codes(self):
        """Test retry mechanism with HTTP status codes"""
        retry_config = RetryConfig(max_attempts=4, base_delay=0.1)
        
        @retry(retry_config=retry_config)
        def http_function():
            self.failure_counter += 1
            # Create proper httpx.Response mock
            response = MagicMock()
            response.status_code = 500 if self.failure_counter == 1 else 200
            response.reason_phrase = "Internal Server Error" if self.failure_counter == 1 else "OK"
            response.headers = {}
            
            # For httpx.Response, we need to simulate the actual response behavior
            if self.failure_counter == 1:
                response.status_code = 500
                return response
            else:
                response.status_code = 200
                return response
        
        result = http_function()
        self.assertEqual(result.status_code, 200)
        self.assertGreaterEqual(self.failure_counter, 1)  # At least one attempt
    
    def test_retry_exhaustion(self):
        """Test retry exhaustion when all attempts fail"""
        retry_config = RetryConfig(max_attempts=3, base_delay=0.1)
        
        @retry(retry_config=retry_config)
        def always_failing_function():
            self.failure_counter += 1
            raise ConnectionError(f"Always fails {self.failure_counter}")  # Use retryable exception
        
        with self.assertRaises(ConnectionError):
            always_failing_function()
        
        self.assertEqual(self.failure_counter, 3)
        
        # Check retry statistics
        summary = get_retry_stats_summary()
        self.assertIn("Failed retries: 1", summary)
    
    def test_retry_with_jitter(self):
        """Test retry mechanism with jitter enabled"""
        retry_config = RetryConfig(max_attempts=3, base_delay=0.1, jitter=True)
        
        delays = []
        original_sleep = time.sleep
        
        def mock_sleep(duration):
            delays.append(duration)
            # Use a very short sleep for testing
            original_sleep(0.01)
        
        @retry(retry_config=retry_config)
        def jitter_function():
            self.failure_counter += 1
            if self.failure_counter < 3:
                raise ConnectionError("Jitter test")
            return "Success with jitter"
        
        with patch('time.sleep', side_effect=mock_sleep):
            result = jitter_function()
        
        self.assertEqual(result, "Success with jitter")
        self.assertEqual(len(delays), 2)  # Two retry delays
        
        # With jitter, delays should vary slightly
        # We can't test exact values due to randomness, but we can check they're reasonable
        for delay in delays:
            self.assertGreater(delay, 0.05)  # Should be at least half base delay
            self.assertLess(delay, 0.25)     # Allow for more jitter variance
    
    def test_retry_without_jitter(self):
        """Test retry mechanism with jitter disabled"""
        retry_config = RetryConfig(max_attempts=3, base_delay=0.1, jitter=False)
        
        delays = []
        original_sleep = time.sleep
        
        def mock_sleep(duration):
            delays.append(duration)
            original_sleep(0.01)
        
        @retry(retry_config=retry_config)
        def no_jitter_function():
            self.failure_counter += 1
            if self.failure_counter < 3:
                raise ConnectionError("No jitter test")
            return "Success without jitter"
        
        with patch('time.sleep', side_effect=mock_sleep):
            result = no_jitter_function()
        
        self.assertEqual(result, "Success without jitter")
        self.assertEqual(len(delays), 2)
        
        # Without jitter, delays should follow exponential backoff exactly
        expected_delays = [0.1, 0.2]  # base_delay * (2 ** attempt)
        for i, delay in enumerate(delays):
            self.assertAlmostEqual(delay, expected_delays[i], places=2)
    
    def test_retry_max_delay_limit(self):
        """Test that retry delays don't exceed max_delay"""
        retry_config = RetryConfig(max_attempts=5, base_delay=1.0, max_delay=2.0, jitter=False)
        
        delays = []
        original_sleep = time.sleep
        
        def mock_sleep(duration):
            delays.append(duration)
            original_sleep(0.01)
        
        @retry(retry_config=retry_config)
        def max_delay_function():
            self.failure_counter += 1
            if self.failure_counter < 5:
                raise ConnectionError("Max delay test")
            return "Success with max delay"
        
        with patch('time.sleep', side_effect=mock_sleep):
            result = max_delay_function()
        
        self.assertEqual(result, "Success with max delay")
        
        # Check that no delay exceeds max_delay
        for delay in delays:
            self.assertLessEqual(delay, 2.0)
        
        # Later delays should be capped at max_delay
        self.assertEqual(delays[-1], 2.0)  # Should be capped at max_delay

class TestAsyncRetryMechanism(unittest.IsolatedAsyncioTestCase):
    """Tests for async retry mechanism"""
    
    def setUp(self):
        """Reset statistics before each test"""
        reset_retry_stats()
        self.failure_counter = 0
    
    async def test_async_retry_with_connection_error(self):
        """Test async retry mechanism with connection errors"""
        retry_config = RetryConfig(max_attempts=3, base_delay=0.1)
        
        @async_retry(retry_config=retry_config)
        async def async_failing_function():
            self.failure_counter += 1
            if self.failure_counter < 3:
                raise ConnectionError(f"Async connection failed {self.failure_counter}")
            return "Async success"
        
        result = await async_failing_function()
        self.assertEqual(result, "Async success")
        self.assertEqual(self.failure_counter, 3)
    
    async def test_async_retry_with_httpx_errors(self):
        """Test async retry mechanism with httpx-specific errors"""
        retry_config = RetryConfig(max_attempts=4, base_delay=0.1)
        
        @async_retry(retry_config=retry_config)
        async def async_http_function():
            self.failure_counter += 1
            if self.failure_counter == 1:
                raise httpx.ConnectError("Connection failed")
            elif self.failure_counter == 2:
                # Create a proper timeout exception
                raise httpx.TimeoutException("Request timeout")
            elif self.failure_counter == 3:
                # Create a proper HTTP status error
                request = MagicMock()
                response = MagicMock()
                response.status_code = 429
                raise httpx.HTTPStatusError("Rate limited", request=request, response=response)
            else:
                return "HTTP success"
        
        result = await async_http_function()
        self.assertEqual(result, "HTTP success")
        self.assertEqual(self.failure_counter, 4)
    
    async def test_async_retry_exhaustion(self):
        """Test async retry exhaustion"""
        retry_config = RetryConfig(max_attempts=2, base_delay=0.1)
        
        @async_retry(retry_config=retry_config)
        async def always_failing_async():
            self.failure_counter += 1
            raise ConnectionError(f"Always fails async {self.failure_counter}")  # Use retryable exception
        
        with self.assertRaises(ConnectionError):
            await always_failing_async()
        
        self.assertEqual(self.failure_counter, 2)
    
    async def test_async_retry_timing(self):
        """Test that async retry respects timing delays"""
        retry_config = RetryConfig(max_attempts=3, base_delay=0.1, jitter=False)
        
        start_time = time.time()
        
        @async_retry(retry_config=retry_config)
        async def timed_async_function():
            self.failure_counter += 1
            if self.failure_counter < 3:
                raise ConnectionError("Timing test")
            return "Timed success"
        
        result = await timed_async_function()
        elapsed = time.time() - start_time
        
        self.assertEqual(result, "Timed success")
        # Should have waited at least 0.1 + 0.2 = 0.3 seconds for retries
        self.assertGreater(elapsed, 0.25)  # Allow for some timing variance

class TestRetryStatistics(unittest.TestCase):
    """Tests for retry statistics tracking"""
    
    def setUp(self):
        """Reset statistics before each test"""
        reset_retry_stats()
    
    def test_retry_stats_tracking(self):
        """Test that retry statistics are tracked correctly"""
        retry_config = RetryConfig(max_attempts=3, base_delay=0.1)
        
        @retry(retry_config=retry_config)
        def stats_test_function():
            if not hasattr(self, 'call_count'):
                self.call_count = 0
            self.call_count += 1
            
            if self.call_count < 3:
                raise ConnectionError(f"Stats test {self.call_count}")
            return "Stats success"
        
        # First successful retry
        result1 = stats_test_function()
        self.assertEqual(result1, "Stats success")
        
        # Reset for second test
        self.call_count = 0
        
        # Second successful retry
        result2 = stats_test_function()
        self.assertEqual(result2, "Stats success")
        
        # Check statistics
        summary = get_retry_stats_summary()
        self.assertIn("Operations with retries: 2", summary)
        self.assertIn("Total retry attempts: 4", summary)  # 2 attempts per operation
        self.assertIn("Successful retries: 2", summary)
    
    def test_retry_stats_reset(self):
        """Test that retry statistics can be reset"""
        retry_config = RetryConfig(max_attempts=2, base_delay=0.1)
        
        @retry(retry_config=retry_config)
        def reset_test_function():
            raise ConnectionError("Reset test")
        
        # Generate some statistics
        try:
            reset_test_function()
        except ConnectionError:
            pass
        
        # Verify stats exist
        summary = get_retry_stats_summary()
        self.assertIn("Operations with retries: 1", summary)
        
        # Reset statistics
        reset_retry_stats()
        
        # Verify stats are reset
        summary = get_retry_stats_summary()
        # After reset, the summary should indicate no operations
        self.assertTrue("No operations recorded" in summary or "Operations with retries: 0" in summary)

if __name__ == "__main__":
    unittest.main()
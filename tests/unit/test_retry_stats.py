#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Test script to demonstrate retry statistics tracking functionality.
"""
import asyncio
import random
import sys
import os
import unittest
import httpx

# Add parent directory to path to allow importing from project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils import retry, async_retry, get_retry_stats_summary, reset_retry_stats, RetryConfig

# Configure a retry config with more attempts for testing
test_retry_config = RetryConfig(
    max_attempts=5,
    base_delay=0.1,  # Short delays for testing
    max_delay=1.0,
    jitter=True
)

# Counter for simulating failures
failure_counter = 0

@retry(retry_config=test_retry_config)
def test_sync_retry(fail_count=3):
    """Test function that fails a specified number of times before succeeding"""
    global failure_counter
    
    if failure_counter < fail_count:
        failure_counter += 1
        raise ConnectionError(f"Simulated failure {failure_counter}/{fail_count}")
    
    return "Success after retries"

@async_retry(retry_config=test_retry_config)
async def test_async_retry(fail_count=3):
    """Test async function that fails a specified number of times before succeeding"""
    global failure_counter
    
    if failure_counter < fail_count:
        failure_counter += 1
        raise ConnectionError(f"Simulated failure {failure_counter}/{fail_count}")
    
    return "Success after retries"

@retry(retry_config=test_retry_config)
def test_http_status_retry():
    """Test function that returns HTTP responses with retry-triggering status codes"""
    global failure_counter
    
    # Simulate different HTTP status codes
    status_codes = [500, 503, 429, 200]
    
    if failure_counter < len(status_codes) - 1:
        status_code = status_codes[failure_counter]
        failure_counter += 1
        
        # Create a mock response with the status code
        response = httpx.Response(status_code=status_code)
        return response
    
    # Return a successful response
    return httpx.Response(status_code=200)

class TestRetryStats(unittest.TestCase):
    """Test cases for retry statistics functionality"""
    
    def setUp(self):
        """Reset statistics before each test"""
        reset_retry_stats()
        global failure_counter
        failure_counter = 0
    
    def test_sync_retry_with_exceptions(self):
        """Test synchronous retry with exceptions"""
        global failure_counter
        
        result = test_sync_retry(fail_count=3)
        self.assertEqual(result, "Success after retries")
        
        # Get statistics summary for verification
        summary = get_retry_stats_summary()
        self.assertIn("Operations with retries: 1", summary)
        self.assertIn("Total retry attempts: 3", summary)
        self.assertIn("Successful retries: 1", summary)
    
    def test_http_status_retry(self):
        """Test retry with HTTP status codes"""
        global failure_counter
        
        result = test_http_status_retry()
        self.assertEqual(result.status_code, 200)
        
        # Get statistics summary for verification
        summary = get_retry_stats_summary()
        self.assertIn("Operations with retries: 1", summary)
        self.assertIn("Successful retries: 1", summary)
    
    def test_retry_exhaustion(self):
        """Test retry exhaustion (all attempts fail)"""
        global failure_counter
        
        with self.assertRaises(ConnectionError):
            test_sync_retry(fail_count=10)  # More failures than max_attempts
        
        # Get statistics summary for verification
        summary = get_retry_stats_summary()
        self.assertIn("Failed retries: 1", summary)
    
    async def async_test_async_retry(self):
        """Helper for testing async retry"""
        global failure_counter
        
        result = await test_async_retry(fail_count=3)
        self.assertEqual(result, "Success after retries")
        
        # Get statistics summary for verification
        summary = get_retry_stats_summary()
        self.assertIn("Operations with retries: 1", summary)
        self.assertIn("Total retry attempts: 3", summary)
        self.assertIn("Successful retries: 1", summary)
    
    def test_async_retry(self):
        """Test asynchronous retry with exceptions"""
        asyncio.run(self.async_test_async_retry())

# Manual test functions for direct script execution
async def run_async_tests():
    """Run async retry tests"""
    global failure_counter
    
    print("\n=== Testing async retry with exceptions ===")
    failure_counter = 0
    try:
        result = await test_async_retry(fail_count=3)
        print(f"Result: {result}")
    except Exception as e:
        print(f"Exception: {e}")
    
    print("\n=== Retry Statistics after async test ===")
    print(get_retry_stats_summary())

def run_sync_tests():
    """Run synchronous retry tests"""
    global failure_counter
    
    print("\n=== Testing sync retry with exceptions ===")
    failure_counter = 0
    try:
        result = test_sync_retry(fail_count=3)
        print(f"Result: {result}")
    except Exception as e:
        print(f"Exception: {e}")
    
    print("\n=== Testing sync retry with HTTP status codes ===")
    failure_counter = 0
    try:
        result = test_http_status_retry()
        print(f"Result status: {result.status_code}")
    except Exception as e:
        print(f"Exception: {e}")
    
    print("\n=== Retry Statistics after sync tests ===")
    print(get_retry_stats_summary())

def run_failure_test():
    """Run a test that exhausts all retry attempts"""
    global failure_counter
    
    print("\n=== Testing retry exhaustion ===")
    failure_counter = 0
    try:
        result = test_sync_retry(fail_count=10)  # More failures than max_attempts
        print(f"Result: {result}")
    except Exception as e:
        print(f"Expected exception after retry exhaustion: {e}")
    
    print("\n=== Final Retry Statistics ===")
    print(get_retry_stats_summary())

if __name__ == "__main__":
    # Option 1: Run as unittest
    unittest.main()
    
    # Option 2: Run manual tests (uncomment to use)
    # reset_retry_stats()
    # run_sync_tests()
    # asyncio.run(run_async_tests())
    # run_failure_test()
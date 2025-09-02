#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Simple test script to verify retry_stats.py functionality directly.
"""
import sys
import os
import unittest

# Add parent directory to path to allow importing from project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from retry_stats import RetryStats, retry_stats, get_retry_stats_summary, reset_retry_stats

class TestRetryStatsDirect(unittest.TestCase):
    """Test cases for direct retry_stats functionality"""
    
    def setUp(self):
        """Reset statistics before each test"""
        reset_retry_stats()
    
    def test_global_stats(self):
        """Test global retry stats tracking"""
        # Record some operations
        retry_stats.record_operation(
            retried=True,
            attempts=3,
            success=True,
            function_name="test_function",
            retry_time=1.5
        )
        
        retry_stats.record_operation(
            retried=True,
            attempts=4,
            success=False,
            exception_type=ValueError,
            function_name="another_function",
            retry_time=2.5
        )
        
        # Get summary
        summary = get_retry_stats_summary()
        
        # Verify stats
        self.assertIn("Total operations: 2", summary)
        self.assertIn("Operations with retries: 2", summary)
        self.assertIn("Total retry attempts: 5", summary)
        self.assertIn("Successful retries: 1", summary)
        self.assertIn("Failed retries: 1", summary)
        self.assertIn("ValueError", summary)
    
    def test_local_stats_instance(self):
        """Test local RetryStats instance"""
        local_stats = RetryStats()
        local_stats.record_operation(
            retried=True,
            attempts=2,
            success=True,
            function_name="local_function",
            retry_time=0.5
        )
        
        # Get summary
        summary = local_stats.get_summary()
        
        # Verify stats
        self.assertIn("Total operations: 1", summary)
        self.assertIn("Operations with retries: 1", summary)
        self.assertIn("Total retry attempts: 1", summary)
        self.assertIn("Successful retries: 1", summary)
        self.assertIn("local_function", summary)
    
    def test_reset_stats(self):
        """Test resetting statistics"""
        # Record an operation
        retry_stats.record_operation(
            retried=True,
            attempts=3,
            success=True,
            function_name="test_function"
        )
        
        # Verify stats are recorded
        self.assertEqual(retry_stats.total_operations, 1)
        self.assertEqual(retry_stats.retried_operations, 1)
        
        # Reset stats
        reset_retry_stats()
        
        # Verify stats are reset
        self.assertEqual(retry_stats.total_operations, 0)
        self.assertEqual(retry_stats.retried_operations, 0)

def manual_test():
    """Manual test function for direct script execution"""
    # Reset global stats
    reset_retry_stats()
    
    # Record some operations
    retry_stats.record_operation(
        retried=True,
        attempts=3,
        success=True,
        function_name="test_function",
        retry_time=1.5
    )
    
    retry_stats.record_operation(
        retried=True,
        attempts=4,
        success=False,
        exception_type=ValueError,
        function_name="another_function",
        retry_time=2.5
    )
    
    # Print summary
    print("=== Global Retry Stats ===")
    print(get_retry_stats_summary())
    
    # Test local instance
    local_stats = RetryStats()
    local_stats.record_operation(
        retried=True,
        attempts=2,
        success=True,
        function_name="local_function",
        retry_time=0.5
    )
    
    print("\n=== Local Retry Stats ===")
    print(local_stats.get_summary())

if __name__ == "__main__":
    # Option 1: Run as unittest
    unittest.main()
    
    # Option 2: Run manual test (uncomment to use)
    # manual_test()
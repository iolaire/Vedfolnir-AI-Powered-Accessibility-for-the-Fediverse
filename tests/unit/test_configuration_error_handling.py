# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for ConfigurationErrorHandler
"""

import unittest
import os
import sys
import time
import threading
from datetime import datetime, timezone

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.core.configuration.error_handling.configuration_error_handling import (
    ConfigurationErrorHandler, ErrorSeverity, FallbackSource,
    ConfigurationError, FallbackAttempt, RecoveryAction,
    get_error_handler, set_error_handler
)


class TestConfigurationErrorHandler(unittest.TestCase):
    """Test cases for ConfigurationErrorHandler"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.error_handler = ConfigurationErrorHandler(
            max_retries=2,
            base_retry_delay=0.1,
            max_retry_delay=1.0,
            circuit_breaker_threshold=3
        )
    
    def tearDown(self):
        """Clean up after tests"""
        pass
    
    def test_error_creation_and_tracking(self):
        """Test error creation and tracking"""
        # Handle different severity errors
        error1 = self.error_handler.handle_error(
            error_type="database_error",
            message="Connection failed",
            key="test_key",
            severity=ErrorSeverity.HIGH,
            source="database"
        )
        
        error2 = self.error_handler.handle_error(
            error_type="validation_error",
            message="Invalid value",
            key="test_key2",
            severity=ErrorSeverity.MEDIUM,
            source="validation"
        )
        
        # Verify error objects
        self.assertEqual(error1.error_type, "database_error")
        self.assertEqual(error1.message, "Connection failed")
        self.assertEqual(error1.key, "test_key")
        self.assertEqual(error1.severity, ErrorSeverity.HIGH)
        self.assertEqual(error1.source, "database")
        self.assertIsInstance(error1.timestamp, datetime)
        
        # Verify statistics
        stats = self.error_handler.get_statistics()
        self.assertEqual(stats['total_errors'], 2)
        self.assertEqual(stats['errors_by_type']['database_error'], 1)
        self.assertEqual(stats['errors_by_type']['validation_error'], 1)
        self.assertEqual(stats['errors_by_severity']['high'], 1)
        self.assertEqual(stats['errors_by_severity']['medium'], 1)
    
    def test_fallback_chain_execution(self):
        """Test fallback chain execution"""
        call_count = 0
        
        def primary_func():
            nonlocal call_count
            call_count += 1
            raise Exception("Primary failed")
        
        def fallback1():
            nonlocal call_count
            call_count += 1
            raise Exception("Fallback 1 failed")
        
        def fallback2():
            nonlocal call_count
            call_count += 1
            return "fallback2_value"
        
        def fallback3():
            nonlocal call_count
            call_count += 1
            return "fallback3_value"
        
        # Execute with fallback chain
        result, attempts = self.error_handler.execute_with_fallback(
            key="test_key",
            primary_func=primary_func,
            fallback_chain=[fallback1, fallback2, fallback3],
            fallback_sources=[FallbackSource.ENVIRONMENT, FallbackSource.DATABASE, FallbackSource.SCHEMA_DEFAULT]
        )
        
        # Verify result
        self.assertEqual(result, "fallback2_value")
        self.assertEqual(call_count, 3)  # Primary + fallback1 + fallback2
        
        # Verify attempts
        self.assertEqual(len(attempts), 2)  # fallback1 and fallback2
        self.assertFalse(attempts[0].success)
        self.assertTrue(attempts[1].success)
        self.assertEqual(attempts[1].value, "fallback2_value")
        self.assertEqual(attempts[1].source, FallbackSource.DATABASE)
        
        # Verify statistics
        stats = self.error_handler.get_statistics()
        self.assertEqual(stats['fallback_attempts'], 2)
        self.assertEqual(stats['successful_fallbacks'], 1)
    
    def test_fallback_all_fail(self):
        """Test fallback chain when all fallbacks fail"""
        def failing_func():
            raise Exception("Function failed")
        
        # Execute with all failing fallbacks
        with self.assertRaises(Exception) as context:
            self.error_handler.execute_with_fallback(
                key="test_key",
                primary_func=failing_func,
                fallback_chain=[failing_func, failing_func],
                fallback_sources=[FallbackSource.ENVIRONMENT, FallbackSource.DATABASE]
            )
        
        self.assertIn("All fallback attempts failed", str(context.exception))
        
        # Verify statistics
        stats = self.error_handler.get_statistics()
        self.assertEqual(stats['fallback_attempts'], 2)
        self.assertEqual(stats['successful_fallbacks'], 0)
    
    def test_retry_mechanism(self):
        """Test retry mechanism with exponential backoff"""
        attempt_count = 0
        
        def failing_then_succeeding_func():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise Exception(f"Attempt {attempt_count} failed")
            return f"success_on_attempt_{attempt_count}"
        
        start_time = time.time()
        result = self.error_handler.execute_with_retry(
            func=failing_then_succeeding_func,
            operation_name="test_operation"
        )
        end_time = time.time()
        
        # Verify result
        self.assertEqual(result, "success_on_attempt_3")
        self.assertEqual(attempt_count, 3)
        
        # Verify retry delays were applied (should take at least 0.3 seconds: 0.1 + 0.2)
        self.assertGreater(end_time - start_time, 0.25)
    
    def test_retry_max_attempts_exceeded(self):
        """Test retry when max attempts are exceeded"""
        attempt_count = 0
        
        def always_failing_func():
            nonlocal attempt_count
            attempt_count += 1
            raise Exception(f"Attempt {attempt_count} failed")
        
        with self.assertRaises(Exception) as context:
            self.error_handler.execute_with_retry(
                func=always_failing_func,
                operation_name="test_operation",
                max_retries=2
            )
        
        self.assertIn("Attempt 3 failed", str(context.exception))
        self.assertEqual(attempt_count, 3)  # Initial attempt + 2 retries
    
    def test_circuit_breaker(self):
        """Test circuit breaker functionality"""
        source = "test_source"
        
        # Initially circuit breaker should be closed
        self.assertFalse(self.error_handler.is_circuit_breaker_open(source))
        
        # Generate failures to trip circuit breaker
        for i in range(3):
            self.error_handler.handle_error(
                error_type="test_error",
                message=f"Error {i}",
                key="test_key",
                severity=ErrorSeverity.MEDIUM,
                source=source
            )
        
        # Circuit breaker should now be open
        self.assertTrue(self.error_handler.is_circuit_breaker_open(source))
        
        # Verify circuit breaker status
        status = self.error_handler.get_circuit_breaker_status()
        self.assertIn(source, status)
        self.assertTrue(status[source]['is_open'])
        self.assertEqual(status[source]['failure_count'], 3)
        
        # Reset circuit breaker
        success = self.error_handler.reset_circuit_breaker(source)
        self.assertTrue(success)
        self.assertFalse(self.error_handler.is_circuit_breaker_open(source))
        
        # Verify statistics
        stats = self.error_handler.get_statistics()
        self.assertEqual(stats['circuit_breaker_trips'], 1)
    
    def test_fallback_value_caching(self):
        """Test fallback value caching"""
        key = "test_key"
        value = "cached_value"
        source = FallbackSource.DATABASE
        
        # Initially no cached value
        cached = self.error_handler.get_fallback_value(key)
        self.assertIsNone(cached)
        
        # Cache a value
        self.error_handler.cache_fallback_value(key, value, source)
        
        # Retrieve cached value
        cached = self.error_handler.get_fallback_value(key)
        self.assertIsNotNone(cached)
        self.assertEqual(cached['value'], value)
        self.assertEqual(cached['source'], source)
        self.assertIsInstance(cached['cached_at'], datetime)
    
    def test_recovery_actions(self):
        """Test recovery action execution"""
        def successful_recovery():
            return "recovery_successful"
        
        def failing_recovery():
            raise Exception("Recovery failed")
        
        # Execute successful recovery
        action1 = self.error_handler.execute_recovery_action(
            action_type="cache_clear",
            description="Clear configuration cache",
            action_func=successful_recovery
        )
        
        self.assertTrue(action1.success)
        self.assertEqual(action1.result, "recovery_successful")
        self.assertEqual(action1.action_type, "cache_clear")
        
        # Execute failing recovery
        action2 = self.error_handler.execute_recovery_action(
            action_type="database_reconnect",
            description="Reconnect to database",
            action_func=failing_recovery
        )
        
        self.assertFalse(action2.success)
        self.assertIn("Failed: Recovery failed", action2.result)
        
        # Verify recovery history
        history = self.error_handler.get_recovery_history()
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]['action_type'], "cache_clear")
        self.assertTrue(history[0]['success'])
        self.assertEqual(history[1]['action_type'], "database_reconnect")
        self.assertFalse(history[1]['success'])
        
        # Verify statistics
        stats = self.error_handler.get_statistics()
        self.assertEqual(stats['recovery_attempts'], 2)
        self.assertEqual(stats['successful_recoveries'], 1)
        self.assertEqual(stats['recovery_success_rate'], 0.5)
    
    def test_error_summary(self):
        """Test error summary generation"""
        # Generate various errors
        self.error_handler.handle_error("type1", "msg1", "key1", ErrorSeverity.HIGH, "source1")
        self.error_handler.handle_error("type1", "msg2", "key1", ErrorSeverity.MEDIUM, "source1")
        self.error_handler.handle_error("type2", "msg3", "key2", ErrorSeverity.LOW, "source2")
        
        # Get error summary
        summary = self.error_handler.get_error_summary(hours=24)
        
        # Verify summary
        self.assertEqual(summary['total_errors'], 3)
        self.assertEqual(summary['errors_by_type']['type1'], 2)
        self.assertEqual(summary['errors_by_type']['type2'], 1)
        self.assertEqual(summary['errors_by_severity']['high'], 1)
        self.assertEqual(summary['errors_by_severity']['medium'], 1)
        self.assertEqual(summary['errors_by_severity']['low'], 1)
        self.assertEqual(summary['errors_by_key']['key1'], 2)
        self.assertEqual(summary['errors_by_key']['key2'], 1)
        
        # Most problematic keys should be sorted by error count
        self.assertEqual(summary['most_problematic_keys'][0], ('key1', 2))
        self.assertEqual(summary['most_problematic_keys'][1], ('key2', 1))
    
    def test_thread_safety(self):
        """Test thread safety of error handler operations"""
        results = []
        errors = []
        
        def worker(worker_id):
            try:
                for i in range(10):
                    # Handle errors
                    self.error_handler.handle_error(
                        error_type=f"worker_{worker_id}_error",
                        message=f"Worker {worker_id} error {i}",
                        key=f"worker_{worker_id}_key_{i}",
                        severity=ErrorSeverity.MEDIUM,
                        source=f"worker_{worker_id}"
                    )
                    
                    # Cache fallback values
                    self.error_handler.cache_fallback_value(
                        f"worker_{worker_id}_key_{i}",
                        f"worker_{worker_id}_value_{i}",
                        FallbackSource.DATABASE
                    )
                    
                    # Execute recovery actions
                    action = self.error_handler.execute_recovery_action(
                        action_type="test_recovery",
                        description=f"Worker {worker_id} recovery {i}",
                        action_func=lambda: f"worker_{worker_id}_recovery_{i}"
                    )
                    results.append(action.success)
                    
            except Exception as e:
                errors.append(e)
        
        # Start multiple threads
        threads = []
        for worker_id in range(3):
            thread = threading.Thread(target=worker, args=(worker_id,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify no errors occurred
        self.assertEqual(len(errors), 0, f"Errors occurred: {errors}")
        
        # Verify results
        self.assertEqual(len(results), 30)  # 3 workers * 10 operations each
        self.assertTrue(all(results))  # All recovery actions should succeed
        
        # Verify statistics
        stats = self.error_handler.get_statistics()
        self.assertEqual(stats['total_errors'], 30)
        self.assertEqual(stats['recovery_attempts'], 30)
        self.assertEqual(stats['successful_recoveries'], 30)
    
    def test_global_error_handler(self):
        """Test global error handler singleton"""
        # Get global handler
        handler1 = get_error_handler()
        handler2 = get_error_handler()
        
        # Should be the same instance
        self.assertIs(handler1, handler2)
        
        # Set custom handler
        custom_handler = ConfigurationErrorHandler()
        set_error_handler(custom_handler)
        
        handler3 = get_error_handler()
        self.assertIs(handler3, custom_handler)
        self.assertIsNot(handler3, handler1)
    
    def test_statistics_calculation(self):
        """Test statistics calculation"""
        # Generate some test data
        self.error_handler.handle_error("test", "msg", "key", ErrorSeverity.HIGH, "source")
        
        # Execute fallbacks
        try:
            self.error_handler.execute_with_fallback(
                "key",
                lambda: None,  # This will return None, not raise
                [lambda: "fallback_value"],
                [FallbackSource.DATABASE]
            )
        except:
            pass
        
        # Execute recovery
        self.error_handler.execute_recovery_action(
            "test_recovery",
            "Test recovery",
            lambda: "success"
        )
        
        # Get statistics
        stats = self.error_handler.get_statistics()
        
        # Verify calculated fields
        self.assertIn('fallback_success_rate', stats)
        self.assertIn('recovery_success_rate', stats)
        self.assertIn('recent_errors_count', stats)
        self.assertIn('active_circuit_breakers', stats)
        self.assertIn('total_circuit_breakers', stats)
        
        # Verify values
        self.assertEqual(stats['total_errors'], 1)
        self.assertEqual(stats['recovery_attempts'], 1)
        self.assertEqual(stats['successful_recoveries'], 1)
        self.assertEqual(stats['recovery_success_rate'], 1.0)
    
    def test_error_with_exception(self):
        """Test error handling with exception object"""
        try:
            raise ValueError("Test exception")
        except Exception as e:
            error = self.error_handler.handle_error(
                error_type="exception_test",
                message="Exception occurred",
                key="test_key",
                severity=ErrorSeverity.HIGH,
                source="test",
                exception=e
            )
        
        # Verify traceback was captured
        self.assertIsNotNone(error.traceback)
        self.assertIn("ValueError: Test exception", error.traceback)
    
    def test_cache_size_limits(self):
        """Test cache size limits"""
        # Fill fallback cache beyond limit
        for i in range(600):  # More than the 500 limit
            self.error_handler.cache_fallback_value(
                f"key_{i}",
                f"value_{i}",
                FallbackSource.DATABASE
            )
        
        # Cache should be limited to 500 entries
        # We can't directly access the cache size, but we can verify
        # that older entries are evicted by checking if early keys are gone
        cached = self.error_handler.get_fallback_value("key_0")
        self.assertIsNone(cached)  # Should be evicted
        
        cached = self.error_handler.get_fallback_value("key_550")
        self.assertIsNotNone(cached)  # Should still be there


if __name__ == '__main__':
    unittest.main()
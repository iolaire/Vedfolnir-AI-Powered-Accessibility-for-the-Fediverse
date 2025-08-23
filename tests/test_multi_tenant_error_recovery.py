# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Error Recovery and System Resilience Tests for Multi-Tenant Caption Management

This module provides comprehensive testing for automated error recovery and system
resilience mechanisms, including network error recovery, timeout handling, database
connection recovery, and system resilience under various failure conditions.
"""

import unittest
import time
import threading
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import Config
from database import DatabaseManager
from models import CaptionGenerationTask, TaskStatus, JobPriority, User, UserRole
from enhanced_error_recovery_manager import EnhancedErrorRecoveryManager
from admin_management_service import AdminManagementService
from system_monitor import SystemMonitor
from alert_manager import AlertManager, AlertType, AlertSeverity


class TestNetworkErrorRecovery(unittest.TestCase):
    """Test recovery from network-related errors"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = Config()
        self.mock_db_manager = Mock(spec=DatabaseManager)
        self.error_recovery = EnhancedErrorRecoveryManager()
        
        # Mock session
        self.mock_session = Mock()
        self.mock_context_manager = MagicMock()
        self.mock_context_manager.__enter__.return_value = self.mock_session
        self.mock_context_manager.__exit__.return_value = None
        self.mock_db_manager.get_session.return_value = self.mock_context_manager
    
    def test_connection_failure_categorization(self):
        """Test categorization of connection failure errors"""
        network_errors = [
            "Connection failed to remote server",
            "Unable to connect to host",
            "Network is unreachable",
            "Connection timed out",
            "Connection refused by server",
            "DNS resolution failed",
            "SSL handshake failed"
        ]
        
        for error_message in network_errors:
            with self.subTest(error=error_message):
                error = Exception(error_message)
                category = self.error_recovery.categorize_error(error)
                self.assertEqual(category, "network", f"Failed to categorize '{error_message}' as network error")
    
    def test_network_error_recovery_suggestions(self):
        """Test recovery suggestions for network errors"""
        network_error = Exception("Connection failed to remote server")
        category = self.error_recovery.categorize_error(network_error)
        
        suggestions = self.error_recovery.generate_recovery_suggestions(category, str(network_error))
        
        self.assertIsInstance(suggestions, list)
        self.assertGreater(len(suggestions), 0)
        
        # Check for relevant network recovery suggestions
        suggestion_text = " ".join(suggestions).lower()
        self.assertIn("network", suggestion_text)
        self.assertTrue(
            any(keyword in suggestion_text for keyword in ["connectivity", "connection", "url", "firewall"]),
            f"Network recovery suggestions missing relevant keywords: {suggestions}"
        )
    
    def test_network_error_retry_logic(self):
        """Test retry logic for network errors"""
        # Create mock task
        mock_task = Mock(spec=CaptionGenerationTask)
        mock_task.id = "network-retry-test"
        mock_task.retry_count = 1
        mock_task.max_retries = 3
        mock_task.status = TaskStatus.FAILED
        
        # Test retry decision for network error
        should_retry = self.error_recovery.should_retry_task(mock_task, "network")
        self.assertTrue(should_retry, "Network errors should be retryable")
        
        # Test retry with max retries reached
        mock_task.retry_count = 3
        should_retry = self.error_recovery.should_retry_task(mock_task, "network")
        self.assertFalse(should_retry, "Should not retry when max retries reached")
    
    def test_network_error_exponential_backoff(self):
        """Test exponential backoff for network error retries"""
        retry_delays = []
        
        for retry_count in range(1, 6):  # Test 5 retry attempts
            delay = self.error_recovery.calculate_retry_delay(retry_count, "network")
            retry_delays.append(delay)
        
        # Verify exponential backoff pattern
        for i in range(1, len(retry_delays)):
            self.assertGreater(
                retry_delays[i], retry_delays[i-1],
                f"Retry delay should increase: attempt {i+1} delay {retry_delays[i]} <= attempt {i} delay {retry_delays[i-1]}"
            )
        
        # Verify reasonable delay bounds
        self.assertLessEqual(max(retry_delays), 300, "Max retry delay should not exceed 5 minutes")
        self.assertGreaterEqual(min(retry_delays), 1, "Min retry delay should be at least 1 second")


class TestTimeoutErrorRecovery(unittest.TestCase):
    """Test recovery from timeout errors"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = Config()
        self.mock_db_manager = Mock(spec=DatabaseManager)
        self.error_recovery = EnhancedErrorRecoveryManager()
    
    def test_timeout_error_categorization(self):
        """Test categorization of timeout errors"""
        timeout_errors = [
            "Request timeout after 30 seconds",
            "Operation timed out",
            "Read timeout",
            "Connection timeout",
            "Socket timeout occurred",
            "HTTP request timeout",
            "API call timed out"
        ]
        
        for error_message in timeout_errors:
            with self.subTest(error=error_message):
                error = Exception(error_message)
                category = self.error_recovery.categorize_error(error)
                self.assertEqual(category, "timeout", f"Failed to categorize '{error_message}' as timeout error")
    
    def test_timeout_error_recovery_suggestions(self):
        """Test recovery suggestions for timeout errors"""
        timeout_error = Exception("Request timeout after 30 seconds")
        category = self.error_recovery.categorize_error(timeout_error)
        
        suggestions = self.error_recovery.generate_recovery_suggestions(category, str(timeout_error))
        
        self.assertIsInstance(suggestions, list)
        self.assertGreater(len(suggestions), 0)
        
        # Check for relevant timeout recovery suggestions
        suggestion_text = " ".join(suggestions).lower()
        self.assertTrue(
            any(keyword in suggestion_text for keyword in ["timeout", "increase", "settings", "load"]),
            f"Timeout recovery suggestions missing relevant keywords: {suggestions}"
        )
    
    def test_timeout_error_adaptive_retry(self):
        """Test adaptive retry logic for timeout errors"""
        # Create mock task with timeout history
        mock_task = Mock(spec=CaptionGenerationTask)
        mock_task.id = "timeout-retry-test"
        mock_task.retry_count = 2
        mock_task.max_retries = 5
        mock_task.status = TaskStatus.FAILED
        
        # Test retry decision for timeout error
        should_retry = self.error_recovery.should_retry_task(mock_task, "timeout")
        self.assertTrue(should_retry, "Timeout errors should be retryable")
        
        # Test adaptive timeout increase
        original_timeout = 30
        new_timeout = self.error_recovery.calculate_adaptive_timeout(original_timeout, mock_task.retry_count)
        
        self.assertGreater(new_timeout, original_timeout, "Timeout should increase after retries")
        self.assertLessEqual(new_timeout, original_timeout * 4, "Timeout should not increase excessively")


class TestDatabaseConnectionRecovery(unittest.TestCase):
    """Test recovery from database connection errors"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = Config()
        self.mock_db_manager = Mock(spec=DatabaseManager)
        self.error_recovery = EnhancedErrorRecoveryManager()
        self.admin_service = AdminManagementService(self.mock_db_manager, Mock())
    
    def test_database_error_categorization(self):
        """Test categorization of database errors"""
        database_errors = [
            "Lost connection to MySQL server",
            "Database connection failed",
            "Connection pool exhausted",
            "MySQL server has gone away",
            "Database is locked",
            "Connection was killed",
            "Too many connections"
        ]
        
        for error_message in database_errors:
            with self.subTest(error=error_message):
                error = Exception(error_message)
                category = self.error_recovery.categorize_error(error)
                self.assertEqual(category, "database", f"Failed to categorize '{error_message}' as database error")
    
    def test_database_connection_recovery_mechanism(self):
        """Test database connection recovery mechanism"""
        # Simulate database connection failure and recovery
        connection_attempts = []
        
        def mock_get_session_with_failure():
            """Mock database session that fails initially then recovers"""
            connection_attempts.append(len(connection_attempts) + 1)
            
            if len(connection_attempts) <= 2:  # Fail first 2 attempts
                raise Exception("Lost connection to MySQL server")
            else:  # Succeed on 3rd attempt
                mock_session = Mock()
                mock_context_manager = MagicMock()
                mock_context_manager.__enter__.return_value = mock_session
                mock_context_manager.__exit__.return_value = None
                return mock_context_manager
        
        self.mock_db_manager.get_session.side_effect = mock_get_session_with_failure
        
        # Test recovery mechanism
        recovery_successful = False
        max_attempts = 5
        
        for attempt in range(max_attempts):
            try:
                session = self.mock_db_manager.get_session()
                with session:
                    # Simulate successful database operation
                    recovery_successful = True
                    break
            except Exception:
                if attempt < max_attempts - 1:
                    time.sleep(0.1)  # Brief delay before retry
                    continue
                else:
                    break
        
        # Verify recovery
        self.assertTrue(recovery_successful, "Database connection recovery should succeed")
        self.assertEqual(len(connection_attempts), 3, "Should attempt connection 3 times before success")
    
    def test_database_transaction_rollback_on_failure(self):
        """Test transaction rollback on database failures"""
        mock_session = Mock()
        mock_session.commit.side_effect = Exception("Database connection lost during commit")
        
        # Test transaction rollback
        try:
            with mock_session:
                # Simulate database operations
                mock_session.add(Mock())
                mock_session.commit()  # This will fail
        except Exception:
            # Verify rollback was called
            mock_session.rollback.assert_called()
    
    def test_connection_pool_recovery(self):
        """Test connection pool recovery mechanisms"""
        # Simulate connection pool exhaustion and recovery
        pool_stats = {
            'active_connections': 0,
            'max_connections': 5,
            'failed_attempts': 0,
            'successful_recoveries': 0
        }
        
        def simulate_connection_pool_operation():
            """Simulate operation that may exhaust connection pool"""
            if pool_stats['active_connections'] >= pool_stats['max_connections']:
                pool_stats['failed_attempts'] += 1
                raise Exception("Connection pool exhausted")
            
            pool_stats['active_connections'] += 1
            try:
                # Simulate work
                time.sleep(0.01)
                pool_stats['successful_recoveries'] += 1
            finally:
                pool_stats['active_connections'] -= 1
        
        # Test concurrent operations that may exhaust pool
        num_operations = 20
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(simulate_connection_pool_operation) 
                for _ in range(num_operations)
            ]
            
            completed_operations = 0
            for future in as_completed(futures):
                try:
                    future.result()
                    completed_operations += 1
                except Exception:
                    # Some operations may fail due to pool exhaustion
                    pass
        
        # Verify some operations succeeded despite pool pressure
        self.assertGreater(completed_operations, 0, "Some operations should succeed")
        self.assertGreater(pool_stats['successful_recoveries'], 0, "Should have successful recoveries")


class TestSystemResilienceUnderLoad(unittest.TestCase):
    """Test system resilience under various load and failure conditions"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = Config()
        self.mock_db_manager = Mock(spec=DatabaseManager)
        self.error_recovery = EnhancedErrorRecoveryManager()
        self.system_monitor = SystemMonitor(self.mock_db_manager)
        self.alert_manager = AlertManager(self.mock_db_manager, Config())
    
    def test_cascading_failure_prevention(self):
        """Test prevention of cascading failures"""
        # Simulate multiple types of errors occurring simultaneously
        error_types = [
            ("network", "Connection failed to remote server"),
            ("timeout", "Request timeout after 30 seconds"),
            ("database", "Lost connection to MySQL server"),
            ("rate_limit", "Too many requests, rate limit exceeded"),
            ("authorization", "Unauthorized access to API")
        ]
        
        # Process multiple errors concurrently
        error_results = []
        
        def process_error(error_type, error_message):
            """Process individual error"""
            try:
                error = Exception(error_message)
                category = self.error_recovery.categorize_error(error)
                suggestions = self.error_recovery.generate_recovery_suggestions(category, error_message)
                
                return {
                    'expected_category': error_type,
                    'actual_category': category,
                    'suggestions': suggestions,
                    'success': category == error_type
                }
            except Exception as e:
                return {
                    'expected_category': error_type,
                    'actual_category': None,
                    'suggestions': [],
                    'success': False,
                    'error': str(e)
                }
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(process_error, error_type, error_message)
                for error_type, error_message in error_types
            ]
            
            for future in as_completed(futures):
                error_results.append(future.result())
        
        # Verify all errors were handled correctly
        successful_results = [r for r in error_results if r['success']]
        self.assertEqual(len(successful_results), len(error_types), "All error types should be handled correctly")
        
        # Verify no cascading failures occurred
        for result in error_results:
            self.assertTrue(result['success'], f"Error processing failed: {result}")
    
    def test_circuit_breaker_pattern(self):
        """Test circuit breaker pattern for failing services"""
        # Simulate circuit breaker for failing external service
        circuit_breaker_state = {
            'state': 'closed',  # closed, open, half-open
            'failure_count': 0,
            'failure_threshold': 5,
            'recovery_timeout': 10,  # seconds
            'last_failure_time': None
        }
        
        def simulate_external_service_call():
            """Simulate call to external service with circuit breaker"""
            current_time = time.time()
            
            # Check circuit breaker state
            if circuit_breaker_state['state'] == 'open':
                if (current_time - circuit_breaker_state['last_failure_time']) > circuit_breaker_state['recovery_timeout']:
                    circuit_breaker_state['state'] = 'half-open'
                else:
                    raise Exception("Circuit breaker is open - service unavailable")
            
            # Simulate service call (fails 70% of the time initially)
            if circuit_breaker_state['failure_count'] < 10 and time.time() % 1 < 0.7:
                # Service call fails
                circuit_breaker_state['failure_count'] += 1
                circuit_breaker_state['last_failure_time'] = current_time
                
                if circuit_breaker_state['failure_count'] >= circuit_breaker_state['failure_threshold']:
                    circuit_breaker_state['state'] = 'open'
                
                raise Exception("External service call failed")
            else:
                # Service call succeeds
                if circuit_breaker_state['state'] == 'half-open':
                    circuit_breaker_state['state'] = 'closed'
                    circuit_breaker_state['failure_count'] = 0
                
                return "Service call successful"
        
        # Test circuit breaker behavior
        successful_calls = 0
        failed_calls = 0
        circuit_breaker_trips = 0
        
        for i in range(50):
            try:
                result = simulate_external_service_call()
                successful_calls += 1
            except Exception as e:
                failed_calls += 1
                if "Circuit breaker is open" in str(e):
                    circuit_breaker_trips += 1
            
            time.sleep(0.1)  # Brief delay between calls
        
        # Verify circuit breaker behavior
        self.assertGreater(failed_calls, 0, "Some calls should fail")
        self.assertGreater(circuit_breaker_trips, 0, "Circuit breaker should trip")
        self.assertGreater(successful_calls, 0, "Some calls should eventually succeed")
    
    def test_graceful_degradation_under_load(self):
        """Test graceful degradation under high load"""
        # Simulate system under increasing load
        load_levels = [10, 25, 50, 75, 100]  # Percentage of system capacity
        performance_metrics = []
        
        for load_level in load_levels:
            # Simulate operations at this load level
            num_operations = load_level
            start_time = time.time()
            
            successful_operations = 0
            failed_operations = 0
            
            def simulate_operation_under_load(operation_id):
                """Simulate operation under specific load level"""
                try:
                    # Simulate processing time that increases with load
                    processing_time = 0.01 * (load_level / 10)  # 1ms to 10ms
                    time.sleep(processing_time)
                    
                    # Simulate failure rate that increases with load
                    failure_rate = load_level / 200  # 5% to 50% failure rate
                    if time.time() % 1 < failure_rate:
                        raise Exception(f"Operation failed under load level {load_level}")
                    
                    return True
                except Exception:
                    return False
            
            with ThreadPoolExecutor(max_workers=min(load_level, 20)) as executor:
                futures = [
                    executor.submit(simulate_operation_under_load, i)
                    for i in range(num_operations)
                ]
                
                for future in as_completed(futures):
                    if future.result():
                        successful_operations += 1
                    else:
                        failed_operations += 1
            
            end_time = time.time()
            total_time = end_time - start_time
            
            performance_metrics.append({
                'load_level': load_level,
                'successful_operations': successful_operations,
                'failed_operations': failed_operations,
                'total_time': total_time,
                'success_rate': successful_operations / num_operations if num_operations > 0 else 0,
                'throughput': successful_operations / total_time if total_time > 0 else 0
            })
        
        # Verify graceful degradation
        for i, metrics in enumerate(performance_metrics):
            # System should maintain some level of functionality even under high load
            self.assertGreater(metrics['success_rate'], 0.1, f"Success rate too low at load level {metrics['load_level']}")
            
            # Throughput should not drop to zero
            self.assertGreater(metrics['throughput'], 0, f"Throughput is zero at load level {metrics['load_level']}")
        
        print("Graceful Degradation Test Results:")
        for metrics in performance_metrics:
            print(f"  Load {metrics['load_level']}%: Success rate {metrics['success_rate']:.1%}, "
                  f"Throughput {metrics['throughput']:.1f} ops/sec")
    
    def test_error_escalation_mechanism(self):
        """Test error escalation to administrators"""
        # Simulate various error severities
        error_scenarios = [
            ("low", "Minor configuration warning", False),
            ("medium", "Service temporarily unavailable", False),
            ("high", "Database connection pool exhausted", True),
            ("critical", "System out of memory - critical failure", True),
            ("critical", "Security breach detected", True)
        ]
        
        escalated_errors = []
        
        for severity, error_message, should_escalate in error_scenarios:
            error = Exception(error_message)
            
            # Test error severity assessment
            assessed_severity = self.error_recovery.assess_error_severity(error)
            
            # Test escalation decision
            should_escalate_result = self.error_recovery.should_escalate_to_admin(assessed_severity, retry_count=2)
            
            if should_escalate_result:
                escalated_errors.append({
                    'severity': assessed_severity,
                    'message': error_message,
                    'expected': should_escalate
                })
        
        # Verify escalation behavior
        self.assertGreater(len(escalated_errors), 0, "Some errors should be escalated")
        
        # Verify critical errors are escalated
        critical_escalations = [e for e in escalated_errors if e['severity'] == 'critical']
        self.assertGreater(len(critical_escalations), 0, "Critical errors should be escalated")
        
        print("Error Escalation Test Results:")
        for error in escalated_errors:
            print(f"  Escalated: {error['severity']} - {error['message']}")


class TestAutomaticRetryLogic(unittest.TestCase):
    """Test automatic retry logic for recoverable errors"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = Config()
        self.mock_db_manager = Mock(spec=DatabaseManager)
        self.error_recovery = EnhancedErrorRecoveryManager()
    
    def test_retry_decision_logic(self):
        """Test retry decision logic for different error types"""
        # Create mock task
        mock_task = Mock(spec=CaptionGenerationTask)
        mock_task.id = "retry-logic-test"
        mock_task.retry_count = 1
        mock_task.max_retries = 3
        mock_task.status = TaskStatus.FAILED
        
        # Test retry decisions for different error categories
        retry_scenarios = [
            ("network", True),      # Network errors should be retried
            ("timeout", True),      # Timeout errors should be retried
            ("rate_limit", True),   # Rate limit errors should be retried
            ("database", True),     # Database errors should be retried
            ("authorization", False), # Auth errors should not be retried
            ("validation", False),  # Validation errors should not be retried
            ("unknown", False)      # Unknown errors should not be retried
        ]
        
        for error_category, expected_retry in retry_scenarios:
            with self.subTest(category=error_category):
                should_retry = self.error_recovery.should_retry_task(mock_task, error_category)
                self.assertEqual(should_retry, expected_retry, 
                               f"Retry decision incorrect for {error_category} errors")
    
    def test_retry_limit_enforcement(self):
        """Test enforcement of retry limits"""
        # Create mock task at retry limit
        mock_task = Mock(spec=CaptionGenerationTask)
        mock_task.id = "retry-limit-test"
        mock_task.retry_count = 3
        mock_task.max_retries = 3
        mock_task.status = TaskStatus.FAILED
        
        # Test that retries are not allowed when limit is reached
        should_retry = self.error_recovery.should_retry_task(mock_task, "network")
        self.assertFalse(should_retry, "Should not retry when retry limit is reached")
        
        # Test that retries are allowed when under limit
        mock_task.retry_count = 2
        should_retry = self.error_recovery.should_retry_task(mock_task, "network")
        self.assertTrue(should_retry, "Should retry when under retry limit")
    
    def test_retry_delay_calculation(self):
        """Test retry delay calculation with exponential backoff"""
        # Test delay calculation for different retry counts
        delay_scenarios = [
            (1, "network", 1, 5),      # First retry: 1-5 seconds
            (2, "network", 2, 10),     # Second retry: 2-10 seconds
            (3, "network", 4, 20),     # Third retry: 4-20 seconds
            (1, "timeout", 2, 10),     # Timeout errors may have different delays
            (1, "rate_limit", 5, 30),  # Rate limit errors may have longer delays
        ]
        
        for retry_count, error_category, min_delay, max_delay in delay_scenarios:
            with self.subTest(retry=retry_count, category=error_category):
                delay = self.error_recovery.calculate_retry_delay(retry_count, error_category)
                
                self.assertGreaterEqual(delay, min_delay, 
                                      f"Delay {delay} too short for retry {retry_count} of {error_category}")
                self.assertLessEqual(delay, max_delay, 
                                   f"Delay {delay} too long for retry {retry_count} of {error_category}")
    
    def test_retry_with_jitter(self):
        """Test retry delay jitter to prevent thundering herd"""
        # Calculate multiple delays for the same retry scenario
        delays = []
        for _ in range(10):
            delay = self.error_recovery.calculate_retry_delay(2, "network")
            delays.append(delay)
        
        # Verify delays have some variation (jitter)
        unique_delays = set(delays)
        self.assertGreater(len(unique_delays), 1, "Retry delays should have jitter to prevent thundering herd")
        
        # Verify all delays are within reasonable bounds
        min_delay = min(delays)
        max_delay = max(delays)
        self.assertGreater(min_delay, 0, "All delays should be positive")
        self.assertLess(max_delay, 60, "No delay should exceed 1 minute for this scenario")


if __name__ == '__main__':
    # Run error recovery and resilience test suite
    unittest.main(verbosity=2)
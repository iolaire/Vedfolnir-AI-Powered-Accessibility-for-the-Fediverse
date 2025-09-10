# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Responsiveness Validation Suite Integration Tests

Comprehensive validation tests that ensure all responsiveness testing components
work together correctly and provide accurate results.
"""

import unittest
import sys
import os
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

# Add project root for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config import Config
from app.core.database.core.database_manager import DatabaseManager
from tests.test_helpers import (
    create_test_user_with_platforms,
    cleanup_test_user,
    ResponsivenessTestConfig,
    ResponsivenessTestDataFactory,
    ResponsivenessMockFactory,
    ResponsivenessPerformanceTester,
    ResponsivenessTestValidator,
    create_responsiveness_test_suite,
    patch_responsiveness_components,
    run_responsiveness_performance_test
)
from models import UserRole


class TestResponsivenessValidationSuite(unittest.TestCase):
    """Test responsiveness validation suite integration"""
    
    def setUp(self):
        """Set up validation test environment"""
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        self.test_config = ResponsivenessTestConfig()
        self.validator = ResponsivenessTestValidator()
        
        # Create test user
        self.test_user, self.user_helper = create_test_user_with_platforms(
            self.db_manager,
            username="test_responsiveness_validation",
            email="validation@example.com",
            password="test123",
            role=UserRole.ADMIN
        )
    
    def tearDown(self):
        """Clean up test environment"""
        cleanup_test_user(self.user_helper)
    
    def test_responsiveness_test_data_factory_integration(self):
        """Test ResponsivenessTestDataFactory integration"""
        # Test healthy system metrics
        healthy_metrics = ResponsivenessTestDataFactory.create_healthy_system_metrics()
        validation_result = self.validator.validate_system_metrics(healthy_metrics)
        
        self.assertTrue(validation_result['valid'])
        self.assertEqual(len(validation_result['errors']), 0)
        self.assertEqual(healthy_metrics['responsiveness_status'], 'healthy')
        
        # Test warning system metrics
        warning_metrics = ResponsivenessTestDataFactory.create_warning_system_metrics()
        validation_result = self.validator.validate_system_metrics(warning_metrics)
        
        self.assertTrue(validation_result['valid'])
        self.assertGreater(len(validation_result['warnings']), 0)
        self.assertEqual(warning_metrics['responsiveness_status'], 'warning')
        
        # Test critical system metrics
        critical_metrics = ResponsivenessTestDataFactory.create_critical_system_metrics()
        validation_result = self.validator.validate_system_metrics(critical_metrics)
        
        self.assertTrue(validation_result['valid'])
        self.assertGreater(len(validation_result['warnings']), 0)
        self.assertEqual(critical_metrics['responsiveness_status'], 'critical')
    
    def test_responsiveness_mock_factory_integration(self):
        """Test ResponsivenessMockFactory integration"""
        # Test system optimizer mock
        system_optimizer = ResponsivenessMockFactory.create_system_optimizer_mock('healthy')
        
        # Verify mock functionality
        metrics = system_optimizer.get_performance_metrics()
        self.assertIn('memory_usage_percent', metrics)
        self.assertIn('responsiveness_status', metrics)
        self.assertEqual(metrics['responsiveness_status'], 'healthy')
        
        responsiveness_check = system_optimizer.check_responsiveness()
        self.assertTrue(responsiveness_check['responsive'])
        self.assertEqual(responsiveness_check['overall_status'], 'healthy')
        
        # Test cleanup manager mock
        cleanup_manager = ResponsivenessMockFactory.create_cleanup_manager_mock()
        
        cleanup_stats = cleanup_manager.get_cleanup_stats()
        self.assertIn('summary', cleanup_stats)
        self.assertIn('responsiveness_metrics', cleanup_stats)
        
        # Test session monitor mock
        session_monitor = ResponsivenessMockFactory.create_session_monitor_mock()
        
        session_metrics = session_monitor.get_session_metrics()
        self.assertIn('active_sessions', session_metrics)
        self.assertIn('memory_leak_indicators', session_metrics)
        
        # Test database manager mock
        db_manager = ResponsivenessMockFactory.create_database_manager_mock()
        
        mysql_stats = db_manager.get_mysql_performance_stats()
        self.assertIn('responsiveness_metrics', mysql_stats)
        
        connection_health = db_manager.monitor_connection_health()
        self.assertIn('overall_health', connection_health)
    
    def test_responsiveness_performance_tester_integration(self):
        """Test ResponsivenessPerformanceTester integration"""
        tester = ResponsivenessPerformanceTester(self.test_config)
        
        # Define test function
        def mock_responsiveness_operation():
            """Mock responsiveness operation for testing"""
            time.sleep(0.001)  # 1ms simulated work
            return {'operation': 'completed', 'duration': 0.001}
        
        # Run performance test
        performance_result = tester.run_performance_test(mock_responsiveness_operation, iterations=10)
        
        # Validate performance result
        validation_result = self.validator.validate_performance_result(performance_result)
        self.assertTrue(validation_result['valid'])
        
        # Verify performance metrics
        self.assertEqual(performance_result['iterations'], 10)
        self.assertEqual(performance_result['successful_iterations'], 10)
        self.assertGreater(performance_result['avg_execution_time'], 0)
        self.assertLess(performance_result['avg_execution_time'], 0.1)  # Should be fast
        
        # Run concurrent test
        concurrent_result = tester.run_concurrent_test(mock_responsiveness_operation, concurrent_users=5)
        
        # Verify concurrent results
        self.assertEqual(concurrent_result['concurrent_users'], 5)
        self.assertEqual(concurrent_result['successful_operations'], 5)
        self.assertGreater(concurrent_result['throughput_ops_per_second'], 0)
        
        # Get performance summary
        summary = tester.get_performance_summary()
        self.assertIn('total_tests', summary)
        self.assertIn('test_success_rate', summary)
        self.assertEqual(summary['successful_tests'], 2)  # 2 tests run
    
    def test_responsiveness_test_suite_creation(self):
        """Test responsiveness test suite creation"""
        # Create healthy test suite
        healthy_suite = create_responsiveness_test_suite('healthy')
        
        self.assertIn('system_optimizer', healthy_suite)
        self.assertIn('cleanup_manager', healthy_suite)
        self.assertIn('session_monitor', healthy_suite)
        self.assertIn('database_manager', healthy_suite)
        
        # Test system optimizer
        system_optimizer = healthy_suite['system_optimizer']
        metrics = system_optimizer.get_performance_metrics()
        self.assertEqual(metrics['responsiveness_status'], 'healthy')
        
        # Create warning test suite
        warning_suite = create_responsiveness_test_suite('warning')
        system_optimizer = warning_suite['system_optimizer']
        metrics = system_optimizer.get_performance_metrics()
        self.assertEqual(metrics['responsiveness_status'], 'warning')
        
        # Create critical test suite
        critical_suite = create_responsiveness_test_suite('critical')
        system_optimizer = critical_suite['system_optimizer']
        metrics = system_optimizer.get_performance_metrics()
        self.assertEqual(metrics['responsiveness_status'], 'critical')
    
    def test_responsiveness_component_patching(self):
        """Test responsiveness component patching"""
        # Test patching with healthy status
        with patch_responsiveness_components('healthy') as patched_components:
            # Verify components are patched
            self.assertIsNotNone(patched_components)
            
            # Test that patched components work
            # (In real implementation, this would test actual patched components)
    
    def test_responsiveness_performance_test_runner(self):
        """Test responsiveness performance test runner"""
        def mock_test_function():
            """Mock test function for performance testing"""
            # Simulate responsiveness monitoring operation
            time.sleep(0.002)  # 2ms simulated work
            return {
                'memory_usage_percent': 50.0,
                'cpu_usage_percent': 30.0,
                'responsiveness_status': 'healthy'
            }
        
        # Run performance test
        performance_results = run_responsiveness_performance_test(
            mock_test_function,
            self.test_config
        )
        
        # Verify performance test results
        self.assertIn('sequential_performance', performance_results)
        self.assertIn('concurrent_performance', performance_results)
        self.assertIn('performance_summary', performance_results)
        
        # Validate sequential performance
        sequential = performance_results['sequential_performance']
        self.assertGreater(sequential['successful_iterations'], 0)
        self.assertLess(sequential['avg_execution_time'], 0.1)
        
        # Validate concurrent performance
        concurrent = performance_results['concurrent_performance']
        self.assertGreater(concurrent['successful_operations'], 0)
        self.assertGreater(concurrent['throughput_ops_per_second'], 0)
        
        # Validate performance summary
        summary = performance_results['performance_summary']
        self.assertGreater(summary['successful_tests'], 0)
        self.assertGreater(summary['test_success_rate'], 0)
    
    def test_responsiveness_validator_comprehensive(self):
        """Test ResponsivenessTestValidator comprehensive validation"""
        # Test system metrics validation with various scenarios
        test_scenarios = [
            {
                'name': 'valid_healthy',
                'metrics': ResponsivenessTestDataFactory.create_healthy_system_metrics(),
                'expected_valid': True,
                'expected_warnings': 0
            },
            {
                'name': 'valid_warning',
                'metrics': ResponsivenessTestDataFactory.create_warning_system_metrics(),
                'expected_valid': True,
                'expected_warnings': 2  # High memory and CPU
            },
            {
                'name': 'valid_critical',
                'metrics': ResponsivenessTestDataFactory.create_critical_system_metrics(),
                'expected_valid': True,
                'expected_warnings': 3  # High memory, CPU, and connection pool
            },
            {
                'name': 'invalid_metrics',
                'metrics': {
                    'memory_usage_percent': 150.0,  # Invalid
                    'cpu_usage_percent': -10.0,     # Invalid
                    'connection_pool_utilization': 2.0,  # Invalid
                    'responsiveness_status': 'unknown'   # Invalid
                },
                'expected_valid': False,
                'expected_errors': 4
            }
        ]
        
        for scenario in test_scenarios:
            with self.subTest(scenario=scenario['name']):
                validation_result = self.validator.validate_system_metrics(scenario['metrics'])
                
                self.assertEqual(validation_result['valid'], scenario['expected_valid'])
                
                if 'expected_warnings' in scenario:
                    self.assertEqual(len(validation_result['warnings']), scenario['expected_warnings'])
                
                if 'expected_errors' in scenario:
                    self.assertEqual(len(validation_result['errors']), scenario['expected_errors'])
    
    def test_responsiveness_test_integration_end_to_end(self):
        """Test end-to-end responsiveness test integration"""
        # Create complete test environment
        test_suite = create_responsiveness_test_suite('healthy')
        tester = ResponsivenessPerformanceTester(self.test_config)
        
        # Define comprehensive test function
        def comprehensive_responsiveness_test():
            """Comprehensive responsiveness test"""
            start_time = time.time()
            
            # Test system metrics
            system_optimizer = test_suite['system_optimizer']
            metrics = system_optimizer.get_performance_metrics()
            
            # Validate metrics
            validation_result = self.validator.validate_system_metrics(metrics)
            if not validation_result['valid']:
                raise Exception(f"Invalid metrics: {validation_result['errors']}")
            
            # Test responsiveness check
            responsiveness_result = system_optimizer.check_responsiveness()
            
            # Validate responsiveness check
            check_validation = self.validator.validate_responsiveness_check(responsiveness_result)
            if not check_validation['valid']:
                raise Exception(f"Invalid responsiveness check: {check_validation['errors']}")
            
            # Test cleanup operations
            cleanup_manager = test_suite['cleanup_manager']
            cleanup_stats = cleanup_manager.get_cleanup_stats()
            
            # Test session monitoring
            session_monitor = test_suite['session_monitor']
            session_metrics = session_monitor.get_session_metrics()
            
            # Test database operations
            database_manager = test_suite['database_manager']
            mysql_stats = database_manager.get_mysql_performance_stats()
            
            execution_time = time.time() - start_time
            
            return {
                'metrics': metrics,
                'responsiveness_result': responsiveness_result,
                'cleanup_stats': cleanup_stats,
                'session_metrics': session_metrics,
                'mysql_stats': mysql_stats,
                'execution_time': execution_time,
                'success': True
            }
        
        # Run comprehensive test
        test_result = comprehensive_responsiveness_test()
        
        # Verify comprehensive test results
        self.assertTrue(test_result['success'])
        self.assertIn('metrics', test_result)
        self.assertIn('responsiveness_result', test_result)
        self.assertIn('cleanup_stats', test_result)
        self.assertIn('session_metrics', test_result)
        self.assertIn('mysql_stats', test_result)
        self.assertLess(test_result['execution_time'], 1.0)  # Should complete quickly
        
        # Run performance test on comprehensive function
        performance_results = tester.run_performance_test(comprehensive_responsiveness_test, iterations=5)
        
        # Validate performance results
        performance_validation = self.validator.validate_performance_result(performance_results)
        self.assertTrue(performance_validation['valid'])
        
        # Verify performance is acceptable
        self.assertEqual(performance_results['successful_iterations'], 5)
        self.assertLess(performance_results['avg_execution_time'], 1.0)
    
    def test_responsiveness_test_error_handling(self):
        """Test responsiveness test error handling"""
        # Create test suite with failing components
        failing_system_optimizer = Mock()
        failing_system_optimizer.get_performance_metrics.side_effect = Exception("System optimizer error")
        failing_system_optimizer.check_responsiveness.side_effect = Exception("Responsiveness check error")
        
        # Test error handling in performance tester
        tester = ResponsivenessPerformanceTester(self.test_config)
        
        def failing_test_function():
            """Test function that fails"""
            failing_system_optimizer.get_performance_metrics()
            return {'result': 'should not reach here'}
        
        # Run performance test with failing function
        performance_result = tester.run_performance_test(failing_test_function, iterations=5)
        
        # Verify error handling
        self.assertEqual(performance_result['successful_iterations'], 0)
        self.assertEqual(performance_result['failed_iterations'], 5)
        self.assertEqual(len(performance_result['errors']), 5)
        
        # Test validator error handling
        invalid_metrics = {'invalid': 'data'}
        validation_result = self.validator.validate_system_metrics(invalid_metrics)
        
        self.assertFalse(validation_result['valid'])
        self.assertGreater(len(validation_result['errors']), 0)
    
    def test_responsiveness_test_configuration_validation(self):
        """Test responsiveness test configuration validation"""
        # Test default configuration
        default_config = ResponsivenessTestConfig()
        
        self.assertEqual(default_config.memory_warning_threshold, 0.8)
        self.assertEqual(default_config.memory_critical_threshold, 0.9)
        self.assertEqual(default_config.cpu_warning_threshold, 0.8)
        self.assertEqual(default_config.cpu_critical_threshold, 0.9)
        self.assertTrue(default_config.cleanup_enabled)
        
        # Test custom configuration
        custom_config = ResponsivenessTestConfig(
            memory_warning_threshold=0.75,
            memory_critical_threshold=0.85,
            test_duration_seconds=120,
            concurrent_users=20
        )
        
        self.assertEqual(custom_config.memory_warning_threshold, 0.75)
        self.assertEqual(custom_config.memory_critical_threshold, 0.85)
        self.assertEqual(custom_config.test_duration_seconds, 120)
        self.assertEqual(custom_config.concurrent_users, 20)
        
        # Test configuration validation logic
        self.assertLess(custom_config.memory_warning_threshold, custom_config.memory_critical_threshold)
        self.assertLess(custom_config.cpu_warning_threshold, custom_config.cpu_critical_threshold)


class TestResponsivenessTestFrameworkIntegration(unittest.TestCase):
    """Test responsiveness test framework integration with existing testing infrastructure"""
    
    def setUp(self):
        """Set up framework integration test environment"""
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
    
    def test_integration_with_existing_test_helpers(self):
        """Test integration with existing test helpers"""
        # Test that responsiveness helpers work with existing helpers
        test_user, user_helper = create_test_user_with_platforms(
            self.db_manager,
            username="test_responsiveness_framework",
            email="framework@example.com",
            password="test123",
            role=UserRole.ADMIN
        )
        
        try:
            # Test responsiveness helpers with real user
            test_suite = create_responsiveness_test_suite('healthy')
            
            # Verify test suite works with real database manager
            self.assertIsNotNone(test_suite['system_optimizer'])
            self.assertIsNotNone(test_suite['database_manager'])
            
            # Test performance testing with real components
            tester = ResponsivenessPerformanceTester()
            
            def test_with_real_user():
                """Test function using real user"""
                return {
                    'user_id': test_user.id,
                    'username': test_user.username,
                    'role': test_user.role.value
                }
            
            performance_result = tester.run_performance_test(test_with_real_user, iterations=3)
            
            # Verify performance test worked
            self.assertEqual(performance_result['successful_iterations'], 3)
            self.assertGreater(performance_result['avg_execution_time'], 0)
            
        finally:
            cleanup_test_user(user_helper)
    
    def test_responsiveness_tests_with_existing_infrastructure(self):
        """Test responsiveness tests with existing testing infrastructure"""
        # Test that responsiveness tests can use existing MySQL test base
        try:
            from tests.performance.mysql_performance_testing import MySQLPerformanceTestBase
            
            # Create mock test class
            class MockResponsivenessTest(MySQLPerformanceTestBase):
                def setUp(self):
                    super().setUp()
                    self.responsiveness_config = ResponsivenessTestConfig()
                
                def test_responsiveness_with_mysql(self):
                    # Test responsiveness features with MySQL infrastructure
                    test_suite = create_responsiveness_test_suite('healthy')
                    
                    # Use existing database manager
                    db_manager = test_suite['database_manager']
                    mysql_stats = db_manager.get_mysql_performance_stats()
                    
                    # Verify responsiveness metrics are included
                    self.assertIn('responsiveness_metrics', mysql_stats)
                    
                    return True
            
            # Create and run mock test
            mock_test = MockResponsivenessTest()
            mock_test.setUp()
            result = mock_test.test_responsiveness_with_mysql()
            
            self.assertTrue(result)
            
        except ImportError:
            # Skip if MySQL performance testing base is not available
            self.skipTest("MySQL performance testing base not available")


if __name__ == '__main__':
    unittest.main()
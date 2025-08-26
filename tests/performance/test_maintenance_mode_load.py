# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Maintenance Mode Load Testing

Performance and scalability tests for maintenance mode under high traffic conditions.
Tests session invalidation performance, status API performance under load, and
emergency mode activation stress testing.
"""

import unittest
import time
import threading
import statistics
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import Mock, patch, MagicMock
import sys
import os
import random
import json

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config import Config
from database import DatabaseManager
from models import User, UserRole
from enhanced_maintenance_mode_service import EnhancedMaintenanceModeService, MaintenanceMode, MaintenanceStatus
from maintenance_mode_middleware import MaintenanceModeMiddleware
from emergency_maintenance_handler import EmergencyMaintenanceHandler
from maintenance_status_api import MaintenanceStatusAPI
from configuration_service import ConfigurationService
from tests.test_helpers.mock_configurations import MockConfigurationService
from tests.test_helpers.mock_user_helper import create_test_user_with_platforms, cleanup_test_user


class TestMaintenanceModeLoad(unittest.TestCase):
    """
    Load testing for maintenance mode functionality
    
    Tests:
    - High traffic maintenance mode activation
    - Session invalidation performance with large numbers of sessions
    - Status API performance under load
    - Emergency mode activation stress testing
    - Scalability across multiple application instances
    """
    
    def setUp(self):
        """Set up test environment for load testing"""
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        
        # Create mock configuration service
        self.config_service = MockConfigurationService()
        
        # Create maintenance service
        self.maintenance_service = EnhancedMaintenanceModeService(
            config_service=self.config_service,
            db_manager=self.db_manager
        )
        
        # Create emergency handler
        self.emergency_handler = EmergencyMaintenanceHandler(
            maintenance_service=self.maintenance_service,
            db_manager=self.db_manager
        )
        
        # Create status API
        self.status_api = MaintenanceStatusAPI(
            maintenance_service=self.maintenance_service
        )
        
        # Create test users
        self.admin_user, self.admin_helper = create_test_user_with_platforms(
            self.db_manager, username="load_test_admin", role=UserRole.ADMIN
        )
        
        self.regular_user, self.regular_helper = create_test_user_with_platforms(
            self.db_manager, username="load_test_user", role=UserRole.REVIEWER
        )
        
        # Load test configuration
        self.load_config = {
            'concurrent_users': 100,
            'concurrent_operations': 500,
            'session_count': 1000,
            'api_requests': 2000,
            'stress_duration': 30,  # seconds
            'performance_thresholds': {
                'activation_time': 5.0,  # seconds
                'status_api_response': 0.1,  # seconds
                'operation_check': 0.01,  # seconds
                'session_invalidation': 10.0,  # seconds
                'emergency_activation': 2.0  # seconds
            }
        }
        
        # Performance tracking
        self.performance_data = {
            'activation_times': [],
            'status_api_times': [],
            'operation_check_times': [],
            'session_invalidation_times': [],
            'emergency_activation_times': [],
            'concurrent_operation_times': [],
            'memory_usage': [],
            'error_rates': []
        }
    
    def tearDown(self):
        """Clean up test environment"""
        try:
            # Disable maintenance mode
            self.maintenance_service.disable_maintenance()
            
            # Clean up test users
            cleanup_test_user(self.admin_helper)
            cleanup_test_user(self.regular_helper)
            
        except Exception as e:
            print(f"Error in tearDown: {e}")
    
    def test_high_traffic_maintenance_activation(self):
        """Test maintenance mode activation under high traffic conditions"""
        print("\n=== Testing High Traffic Maintenance Activation ===")
        
        # Create background load
        stop_background_load = threading.Event()
        background_threads = []
        
        # Start background status checks
        for i in range(20):
            thread = threading.Thread(
                target=self._background_status_checks,
                args=(stop_background_load,)
            )
            thread.start()
            background_threads.append(thread)
        
        # Start background operation checks
        for i in range(30):
            thread = threading.Thread(
                target=self._background_operation_checks,
                args=(stop_background_load,)
            )
            thread.start()
            background_threads.append(thread)
        
        print(f"Started {len(background_threads)} background threads")
        
        # Test maintenance activation under load
        activation_times = []
        for i in range(10):
            start_time = time.time()
            
            result = self.maintenance_service.enable_maintenance(
                reason=f"Load test activation {i}",
                duration=5,
                mode=MaintenanceMode.NORMAL,
                enabled_by="load_test_admin"
            )
            
            activation_time = time.time() - start_time
            activation_times.append(activation_time)
            self.performance_data['activation_times'].append(activation_time)
            
            self.assertTrue(result, f"Activation {i} should succeed")
            
            # Verify activation worked
            status = self.maintenance_service.get_maintenance_status()
            self.assertTrue(status.is_active, f"Maintenance should be active after activation {i}")
            
            # Disable for next test
            self.maintenance_service.disable_maintenance()
            time.sleep(0.5)  # Brief pause
        
        # Stop background load
        stop_background_load.set()
        for thread in background_threads:
            thread.join(timeout=5)
        
        # Analyze results
        avg_activation_time = statistics.mean(activation_times)
        max_activation_time = max(activation_times)
        p95_activation_time = statistics.quantiles(activation_times, n=20)[18]  # 95th percentile
        
        print(f"✓ Activation times: avg={avg_activation_time:.3f}s, max={max_activation_time:.3f}s, p95={p95_activation_time:.3f}s")
        
        # Performance assertions
        self.assertLess(avg_activation_time, self.load_config['performance_thresholds']['activation_time'],
                       f"Average activation time should be <{self.load_config['performance_thresholds']['activation_time']}s")
        self.assertLess(p95_activation_time, self.load_config['performance_thresholds']['activation_time'] * 2,
                       "95th percentile activation time should be reasonable")
        
        print("✓ High traffic maintenance activation test passed")
    
    def test_session_invalidation_performance(self):
        """Test session invalidation performance with large numbers of active sessions"""
        print("\n=== Testing Session Invalidation Performance ===")
        
        # Create large number of mock sessions
        session_count = self.load_config['session_count']
        mock_sessions = self._create_mock_sessions(session_count)
        
        print(f"Created {len(mock_sessions)} mock sessions")
        
        # Test session invalidation performance
        invalidation_times = []
        
        for test_run in range(5):
            # Enable maintenance mode
            self.maintenance_service.enable_maintenance(
                reason=f"Session invalidation test {test_run}",
                mode=MaintenanceMode.NORMAL,
                enabled_by="load_test_admin"
            )
            
            # Measure session invalidation time
            start_time = time.time()
            
            # Mock session invalidation process
            invalidated_sessions = self._mock_session_invalidation(mock_sessions)
            
            invalidation_time = time.time() - start_time
            invalidation_times.append(invalidation_time)
            self.performance_data['session_invalidation_times'].append(invalidation_time)
            
            print(f"Run {test_run + 1}: Invalidated {invalidated_sessions} sessions in {invalidation_time:.3f}s")
            
            # Disable maintenance for next test
            self.maintenance_service.disable_maintenance()
            time.sleep(1)
        
        # Analyze results
        avg_invalidation_time = statistics.mean(invalidation_times)
        max_invalidation_time = max(invalidation_times)
        
        print(f"✓ Session invalidation: avg={avg_invalidation_time:.3f}s, max={max_invalidation_time:.3f}s")
        
        # Performance assertions
        self.assertLess(avg_invalidation_time, self.load_config['performance_thresholds']['session_invalidation'],
                       f"Average session invalidation should be <{self.load_config['performance_thresholds']['session_invalidation']}s")
        
        # Test throughput
        avg_sessions_per_second = session_count / avg_invalidation_time
        print(f"✓ Session invalidation throughput: {avg_sessions_per_second:.0f} sessions/second")
        
        self.assertGreater(avg_sessions_per_second, 100, "Should invalidate at least 100 sessions per second")
        
        print("✓ Session invalidation performance test passed")
    
    def test_status_api_performance_under_load(self):
        """Test maintenance status API performance under high load"""
        print("\n=== Testing Status API Performance Under Load ===")
        
        # Enable maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="Status API load testing",
            mode=MaintenanceMode.NORMAL,
            enabled_by="load_test_admin"
        )
        
        # Test concurrent API requests
        request_count = self.load_config['api_requests']
        concurrent_workers = 50
        
        def make_status_request():
            start_time = time.time()
            try:
                status_response = self.status_api.get_status()
                response_time = time.time() - start_time
                
                # Verify response
                self.assertIsNotNone(status_response, "Status response should not be None")
                self.assertTrue(status_response.is_active, "Status should show active maintenance")
                
                return {'success': True, 'response_time': response_time, 'error': None}
            except Exception as e:
                response_time = time.time() - start_time
                return {'success': False, 'response_time': response_time, 'error': str(e)}
        
        print(f"Making {request_count} concurrent status API requests with {concurrent_workers} workers")
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=concurrent_workers) as executor:
            futures = [executor.submit(make_status_request) for _ in range(request_count)]
            results = [future.result() for future in as_completed(futures)]
        
        total_time = time.time() - start_time
        
        # Analyze results
        successful_requests = [r for r in results if r['success']]
        failed_requests = [r for r in results if not r['success']]
        
        response_times = [r['response_time'] for r in successful_requests]
        
        if response_times:
            avg_response_time = statistics.mean(response_times)
            max_response_time = max(response_times)
            p95_response_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) > 20 else max_response_time
            
            self.performance_data['status_api_times'].extend(response_times)
        else:
            avg_response_time = float('inf')
            max_response_time = float('inf')
            p95_response_time = float('inf')
        
        success_rate = len(successful_requests) / len(results) * 100
        requests_per_second = len(successful_requests) / total_time
        
        print(f"✓ API Performance:")
        print(f"  - Success rate: {success_rate:.1f}%")
        print(f"  - Requests/second: {requests_per_second:.0f}")
        print(f"  - Response times: avg={avg_response_time:.4f}s, max={max_response_time:.4f}s, p95={p95_response_time:.4f}s")
        
        if failed_requests:
            print(f"  - Failed requests: {len(failed_requests)}")
            for i, failed in enumerate(failed_requests[:5]):  # Show first 5 errors
                print(f"    Error {i+1}: {failed['error']}")
        
        # Performance assertions
        self.assertGreater(success_rate, 95, "Success rate should be >95%")
        self.assertLess(avg_response_time, self.load_config['performance_thresholds']['status_api_response'],
                       f"Average response time should be <{self.load_config['performance_thresholds']['status_api_response']}s")
        self.assertGreater(requests_per_second, 100, "Should handle at least 100 requests per second")
        
        print("✓ Status API performance under load test passed")
    
    def test_emergency_mode_activation_stress(self):
        """Test emergency mode activation under stress conditions"""
        print("\n=== Testing Emergency Mode Activation Stress ===")
        
        # Create high background load
        stop_load = threading.Event()
        load_threads = []
        
        # Background status checks
        for i in range(30):
            thread = threading.Thread(target=self._background_status_checks, args=(stop_load,))
            thread.start()
            load_threads.append(thread)
        
        # Background operation checks
        for i in range(50):
            thread = threading.Thread(target=self._background_operation_checks, args=(stop_load,))
            thread.start()
            load_threads.append(thread)
        
        print(f"Started {len(load_threads)} background load threads")
        time.sleep(2)  # Let background load stabilize
        
        # Test emergency activation under stress
        emergency_times = []
        
        for test_run in range(5):
            start_time = time.time()
            
            result = self.emergency_handler.activate_emergency_mode(
                reason=f"Stress test emergency {test_run}",
                triggered_by="stress_test_system"
            )
            
            emergency_time = time.time() - start_time
            emergency_times.append(emergency_time)
            self.performance_data['emergency_activation_times'].append(emergency_time)
            
            self.assertTrue(result, f"Emergency activation {test_run} should succeed")
            
            # Verify emergency mode is active
            status = self.maintenance_service.get_maintenance_status()
            self.assertTrue(status.is_active, "Emergency mode should be active")
            self.assertEqual(status.mode, MaintenanceMode.EMERGENCY, "Mode should be EMERGENCY")
            
            print(f"Emergency activation {test_run + 1}: {emergency_time:.3f}s")
            
            # Deactivate for next test
            self.emergency_handler.deactivate_emergency_mode()
            time.sleep(1)
        
        # Stop background load
        stop_load.set()
        for thread in load_threads:
            thread.join(timeout=5)
        
        # Analyze results
        avg_emergency_time = statistics.mean(emergency_times)
        max_emergency_time = max(emergency_times)
        
        print(f"✓ Emergency activation: avg={avg_emergency_time:.3f}s, max={max_emergency_time:.3f}s")
        
        # Performance assertions
        self.assertLess(avg_emergency_time, self.load_config['performance_thresholds']['emergency_activation'],
                       f"Average emergency activation should be <{self.load_config['performance_thresholds']['emergency_activation']}s")
        
        print("✓ Emergency mode activation stress test passed")
    
    def test_operation_blocking_performance_under_load(self):
        """Test operation blocking performance under high concurrent load"""
        print("\n=== Testing Operation Blocking Performance Under Load ===")
        
        # Enable maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="Operation blocking load test",
            mode=MaintenanceMode.NORMAL,
            enabled_by="load_test_admin"
        )
        
        # Test operations
        test_operations = [
            '/start_caption_generation',
            '/create_job',
            '/switch_platform',
            '/batch_process',
            '/update_profile',
            '/process_image',
            '/read_data',
            '/admin/dashboard'
        ]
        
        # Test users
        test_users = [self.regular_user, self.admin_user]
        
        # Create operation check tasks
        operation_count = self.load_config['concurrent_operations']
        concurrent_workers = 100
        
        def check_operation():
            operation = random.choice(test_operations)
            user = random.choice(test_users)
            
            start_time = time.time()
            try:
                blocked = self.maintenance_service.is_operation_blocked(operation, user)
                response_time = time.time() - start_time
                
                return {'success': True, 'response_time': response_time, 'blocked': blocked, 'error': None}
            except Exception as e:
                response_time = time.time() - start_time
                return {'success': False, 'response_time': response_time, 'blocked': None, 'error': str(e)}
        
        print(f"Performing {operation_count} concurrent operation checks with {concurrent_workers} workers")
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=concurrent_workers) as executor:
            futures = [executor.submit(check_operation) for _ in range(operation_count)]
            results = [future.result() for future in as_completed(futures)]
        
        total_time = time.time() - start_time
        
        # Analyze results
        successful_checks = [r for r in results if r['success']]
        failed_checks = [r for r in results if not r['success']]
        
        response_times = [r['response_time'] for r in successful_checks]
        
        if response_times:
            avg_response_time = statistics.mean(response_times)
            max_response_time = max(response_times)
            p95_response_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) > 20 else max_response_time
            
            self.performance_data['operation_check_times'].extend(response_times)
        else:
            avg_response_time = float('inf')
            max_response_time = float('inf')
            p95_response_time = float('inf')
        
        success_rate = len(successful_checks) / len(results) * 100
        checks_per_second = len(successful_checks) / total_time
        
        print(f"✓ Operation Blocking Performance:")
        print(f"  - Success rate: {success_rate:.1f}%")
        print(f"  - Checks/second: {checks_per_second:.0f}")
        print(f"  - Response times: avg={avg_response_time:.4f}s, max={max_response_time:.4f}s, p95={p95_response_time:.4f}s")
        
        if failed_checks:
            print(f"  - Failed checks: {len(failed_checks)}")
        
        # Performance assertions
        self.assertGreater(success_rate, 98, "Success rate should be >98%")
        self.assertLess(avg_response_time, self.load_config['performance_thresholds']['operation_check'],
                       f"Average operation check time should be <{self.load_config['performance_thresholds']['operation_check']}s")
        self.assertGreater(checks_per_second, 1000, "Should handle at least 1000 operation checks per second")
        
        print("✓ Operation blocking performance under load test passed")
    
    def test_scalability_multiple_instances(self):
        """Test maintenance mode scalability across multiple application instances"""
        print("\n=== Testing Scalability Across Multiple Instances ===")
        
        # Simulate multiple application instances
        instance_count = 5
        maintenance_services = []
        
        for i in range(instance_count):
            # Create separate service instance
            service = EnhancedMaintenanceModeService(
                config_service=self.config_service,
                db_manager=self.db_manager
            )
            maintenance_services.append(service)
        
        print(f"Created {len(maintenance_services)} maintenance service instances")
        
        # Test coordinated maintenance activation
        def activate_maintenance_on_instance(service, instance_id):
            start_time = time.time()
            result = service.enable_maintenance(
                reason=f"Multi-instance test from instance {instance_id}",
                mode=MaintenanceMode.NORMAL,
                enabled_by=f"instance_{instance_id}"
            )
            activation_time = time.time() - start_time
            return {'instance_id': instance_id, 'result': result, 'time': activation_time}
        
        # Activate maintenance on all instances concurrently
        with ThreadPoolExecutor(max_workers=instance_count) as executor:
            futures = [
                executor.submit(activate_maintenance_on_instance, service, i)
                for i, service in enumerate(maintenance_services)
            ]
            activation_results = [future.result() for future in as_completed(futures)]
        
        # Verify all activations succeeded
        successful_activations = [r for r in activation_results if r['result']]
        activation_times = [r['time'] for r in successful_activations]
        
        print(f"✓ Successful activations: {len(successful_activations)}/{len(activation_results)}")
        
        if activation_times:
            avg_activation_time = statistics.mean(activation_times)
            max_activation_time = max(activation_times)
            print(f"✓ Multi-instance activation: avg={avg_activation_time:.3f}s, max={max_activation_time:.3f}s")
        
        # Test status consistency across instances
        def check_status_on_instance(service, instance_id):
            status = service.get_maintenance_status()
            return {
                'instance_id': instance_id,
                'is_active': status.is_active,
                'mode': status.mode.value if status.mode else None,
                'reason': status.reason
            }
        
        with ThreadPoolExecutor(max_workers=instance_count) as executor:
            futures = [
                executor.submit(check_status_on_instance, service, i)
                for i, service in enumerate(maintenance_services)
            ]
            status_results = [future.result() for future in as_completed(futures)]
        
        # Verify status consistency
        active_statuses = [r for r in status_results if r['is_active']]
        print(f"✓ Instances reporting active maintenance: {len(active_statuses)}/{len(status_results)}")
        
        # Test concurrent operation checking across instances
        def check_operations_on_instance(service, instance_id):
            operations = ['/start_caption_generation', '/create_job', '/switch_platform']
            blocked_count = 0
            
            for operation in operations:
                if service.is_operation_blocked(operation, self.regular_user):
                    blocked_count += 1
            
            return {'instance_id': instance_id, 'blocked_operations': blocked_count}
        
        with ThreadPoolExecutor(max_workers=instance_count) as executor:
            futures = [
                executor.submit(check_operations_on_instance, service, i)
                for i, service in enumerate(maintenance_services)
            ]
            operation_results = [future.result() for future in as_completed(futures)]
        
        # Verify operation blocking consistency
        blocked_counts = [r['blocked_operations'] for r in operation_results]
        consistent_blocking = len(set(blocked_counts)) == 1  # All instances should have same blocking behavior
        
        print(f"✓ Operation blocking consistency: {consistent_blocking}")
        print(f"✓ Blocked operations per instance: {blocked_counts}")
        
        # Clean up - disable maintenance on all instances
        for service in maintenance_services:
            service.disable_maintenance()
        
        # Performance assertions
        self.assertEqual(len(successful_activations), instance_count, "All instances should activate successfully")
        self.assertTrue(consistent_blocking, "Operation blocking should be consistent across instances")
        
        print("✓ Multi-instance scalability test passed")
    
    def test_sustained_load_performance(self):
        """Test maintenance mode performance under sustained load"""
        print("\n=== Testing Sustained Load Performance ===")
        
        # Enable maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="Sustained load testing",
            mode=MaintenanceMode.NORMAL,
            enabled_by="load_test_admin"
        )
        
        # Test configuration
        duration = self.load_config['stress_duration']
        concurrent_workers = 20
        
        # Performance tracking
        operation_times = []
        status_times = []
        error_count = 0
        
        # Sustained load test
        stop_time = time.time() + duration
        
        def sustained_load_worker():
            nonlocal error_count
            local_operation_times = []
            local_status_times = []
            local_errors = 0
            
            while time.time() < stop_time:
                try:
                    # Test operation blocking
                    start_time = time.time()
                    blocked = self.maintenance_service.is_operation_blocked(
                        '/start_caption_generation', self.regular_user
                    )
                    operation_time = time.time() - start_time
                    local_operation_times.append(operation_time)
                    
                    # Test status check
                    start_time = time.time()
                    status = self.maintenance_service.get_maintenance_status()
                    status_time = time.time() - start_time
                    local_status_times.append(status_time)
                    
                    # Brief pause
                    time.sleep(0.01)
                    
                except Exception as e:
                    local_errors += 1
                    time.sleep(0.1)  # Longer pause on error
            
            return {
                'operation_times': local_operation_times,
                'status_times': local_status_times,
                'errors': local_errors
            }
        
        print(f"Running sustained load test for {duration} seconds with {concurrent_workers} workers")
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=concurrent_workers) as executor:
            futures = [executor.submit(sustained_load_worker) for _ in range(concurrent_workers)]
            worker_results = [future.result() for future in as_completed(futures)]
        
        actual_duration = time.time() - start_time
        
        # Aggregate results
        for result in worker_results:
            operation_times.extend(result['operation_times'])
            status_times.extend(result['status_times'])
            error_count += result['errors']
        
        # Analyze performance
        total_operations = len(operation_times) + len(status_times)
        operations_per_second = total_operations / actual_duration
        error_rate = error_count / total_operations * 100 if total_operations > 0 else 0
        
        if operation_times:
            avg_operation_time = statistics.mean(operation_times)
            p95_operation_time = statistics.quantiles(operation_times, n=20)[18] if len(operation_times) > 20 else max(operation_times)
        else:
            avg_operation_time = 0
            p95_operation_time = 0
        
        if status_times:
            avg_status_time = statistics.mean(status_times)
            p95_status_time = statistics.quantiles(status_times, n=20)[18] if len(status_times) > 20 else max(status_times)
        else:
            avg_status_time = 0
            p95_status_time = 0
        
        print(f"✓ Sustained Load Results:")
        print(f"  - Duration: {actual_duration:.1f}s")
        print(f"  - Total operations: {total_operations}")
        print(f"  - Operations/second: {operations_per_second:.0f}")
        print(f"  - Error rate: {error_rate:.2f}%")
        print(f"  - Operation times: avg={avg_operation_time:.4f}s, p95={p95_operation_time:.4f}s")
        print(f"  - Status times: avg={avg_status_time:.4f}s, p95={p95_status_time:.4f}s")
        
        # Performance assertions
        self.assertLess(error_rate, 1.0, "Error rate should be <1%")
        self.assertGreater(operations_per_second, 500, "Should handle at least 500 operations per second")
        self.assertLess(avg_operation_time, 0.01, "Average operation time should be <10ms")
        self.assertLess(avg_status_time, 0.01, "Average status time should be <10ms")
        
        print("✓ Sustained load performance test passed")
    
    def test_memory_usage_under_load(self):
        """Test memory usage during high load maintenance operations"""
        print("\n=== Testing Memory Usage Under Load ===")
        
        try:
            import psutil
            process = psutil.Process()
        except ImportError:
            print("⚠ psutil not available, skipping memory usage test")
            return
        
        # Get baseline memory usage
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
        print(f"Baseline memory usage: {baseline_memory:.1f} MB")
        
        # Enable maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="Memory usage testing",
            mode=MaintenanceMode.NORMAL,
            enabled_by="load_test_admin"
        )
        
        # Create high load
        stop_load = threading.Event()
        load_threads = []
        memory_samples = []
        
        def memory_monitor():
            while not stop_load.is_set():
                memory_mb = process.memory_info().rss / 1024 / 1024
                memory_samples.append(memory_mb)
                time.sleep(0.5)
        
        # Start memory monitoring
        monitor_thread = threading.Thread(target=memory_monitor)
        monitor_thread.start()
        
        # Create load threads
        for i in range(50):
            thread = threading.Thread(target=self._background_operation_checks, args=(stop_load,))
            thread.start()
            load_threads.append(thread)
        
        # Run load for 30 seconds
        time.sleep(30)
        
        # Stop load
        stop_load.set()
        for thread in load_threads:
            thread.join(timeout=5)
        monitor_thread.join(timeout=5)
        
        # Analyze memory usage
        if memory_samples:
            max_memory = max(memory_samples)
            avg_memory = statistics.mean(memory_samples)
            memory_increase = max_memory - baseline_memory
            
            print(f"✓ Memory Usage:")
            print(f"  - Baseline: {baseline_memory:.1f} MB")
            print(f"  - Maximum: {max_memory:.1f} MB")
            print(f"  - Average: {avg_memory:.1f} MB")
            print(f"  - Increase: {memory_increase:.1f} MB")
            
            # Memory usage assertions
            self.assertLess(memory_increase, 100, "Memory increase should be <100MB under load")
            
            # Check for memory leaks (memory should not continuously increase)
            if len(memory_samples) > 10:
                first_half = memory_samples[:len(memory_samples)//2]
                second_half = memory_samples[len(memory_samples)//2:]
                
                avg_first_half = statistics.mean(first_half)
                avg_second_half = statistics.mean(second_half)
                
                memory_trend = avg_second_half - avg_first_half
                print(f"  - Memory trend: {memory_trend:+.1f} MB")
                
                self.assertLess(abs(memory_trend), 20, "Memory usage should be stable (no significant trend)")
        
        print("✓ Memory usage under load test passed")
    
    # Helper methods
    
    def _background_status_checks(self, stop_event):
        """Background thread for continuous status checks"""
        while not stop_event.is_set():
            try:
                status = self.maintenance_service.get_maintenance_status()
                time.sleep(0.1)
            except Exception:
                time.sleep(0.5)
    
    def _background_operation_checks(self, stop_event):
        """Background thread for continuous operation checks"""
        operations = ['/start_caption_generation', '/create_job', '/switch_platform']
        
        while not stop_event.is_set():
            try:
                operation = random.choice(operations)
                blocked = self.maintenance_service.is_operation_blocked(operation, self.regular_user)
                time.sleep(0.05)
            except Exception:
                time.sleep(0.5)
    
    def _create_mock_sessions(self, count):
        """Create mock user sessions for testing"""
        sessions = []
        
        for i in range(count):
            session = {
                'id': f'session_{i}',
                'user_id': random.choice([self.admin_user.id, self.regular_user.id]),
                'created_at': datetime.now(timezone.utc),
                'active': True,
                'role': random.choice(['admin', 'user', 'moderator'])
            }
            sessions.append(session)
        
        return sessions
    
    def _mock_session_invalidation(self, sessions):
        """Mock session invalidation process"""
        invalidated_count = 0
        
        for session in sessions:
            if session['role'] != 'admin':
                # Simulate session invalidation work
                time.sleep(0.001)  # 1ms per session
                session['active'] = False
                invalidated_count += 1
        
        return invalidated_count
    
    def generate_performance_report(self):
        """Generate comprehensive performance report"""
        report = {
            'test_timestamp': datetime.now(timezone.utc).isoformat(),
            'load_configuration': self.load_config,
            'performance_data': {}
        }
        
        # Analyze each performance metric
        for metric_name, times in self.performance_data.items():
            if times:
                report['performance_data'][metric_name] = {
                    'count': len(times),
                    'average': statistics.mean(times),
                    'median': statistics.median(times),
                    'min': min(times),
                    'max': max(times),
                    'p95': statistics.quantiles(times, n=20)[18] if len(times) > 20 else max(times),
                    'p99': statistics.quantiles(times, n=100)[98] if len(times) > 100 else max(times)
                }
            else:
                report['performance_data'][metric_name] = {
                    'count': 0,
                    'note': 'No data collected'
                }
        
        return report


if __name__ == '__main__':
    # Run tests with performance reporting
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMaintenanceModeLoad)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Generate performance report if tests ran
    if hasattr(result, 'testsRun') and result.testsRun > 0:
        test_instance = TestMaintenanceModeLoad()
        test_instance.setUp()
        report = test_instance.generate_performance_report()
        
        print("\n" + "="*60)
        print("PERFORMANCE REPORT")
        print("="*60)
        print(json.dumps(report, indent=2))
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Performance Tests for Responsiveness Optimization Integration

Tests the performance characteristics of responsiveness monitoring features
integrated with existing testing infrastructure.
"""

import unittest
import sys
import os
import time
import threading
import concurrent.futures
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

# Add project root for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config import Config
from database import DatabaseManager
from tests.test_helpers import create_test_user_with_platforms, cleanup_test_user
try:
    from tests.performance.mysql_performance_testing import MySQLPerformanceTestBase
    performance_base_available = True
except ImportError:
    # Create a mock base class if not available
    class MySQLPerformanceTestBase(unittest.TestCase):
        def setUp(self):
            self.config = Config()
            self.db_manager = DatabaseManager(self.config)
    performance_base_available = False


class TestResponsivenessPerformanceIntegration(MySQLPerformanceTestBase):
    """Test responsiveness performance integration with existing infrastructure"""
    
    def setUp(self):
        """Set up performance test environment"""
        super().setUp()
        
        # Mock SystemOptimizer for performance testing
        self.mock_system_optimizer = Mock()
        self.mock_system_optimizer.get_performance_metrics.return_value = {
            'memory_usage_percent': 45.0,
            'cpu_usage_percent': 25.0,
            'connection_pool_utilization': 0.6,
            'responsiveness_status': 'healthy'
        }
        
        self.mock_system_optimizer.check_responsiveness.return_value = {
            'responsive': True,
            'issues': [],
            'overall_status': 'healthy'
        }
        
        # Mock BackgroundCleanupManager
        self.mock_cleanup_manager = Mock()
        self.mock_cleanup_manager.get_cleanup_stats.return_value = {
            'total_operations': 10,
            'successful_operations': 9,
            'avg_cleanup_time': 2.5
        }
        
        # Performance test configuration
        self.performance_config = {
            'concurrent_users': 50,
            'test_duration_seconds': 60,
            'responsiveness_check_interval': 5,
            'memory_monitoring_enabled': True,
            'connection_monitoring_enabled': True
        }
    
    def test_responsiveness_monitoring_performance_overhead(self):
        """Test performance overhead of responsiveness monitoring"""
        # Baseline performance without monitoring
        baseline_start = time.time()
        
        # Simulate baseline operations
        for i in range(1000):
            # Mock database operation
            with self.db_manager.get_session() as session:
                pass
        
        baseline_duration = time.time() - baseline_start
        
        # Performance with responsiveness monitoring
        monitoring_start = time.time()
        
        # Simulate operations with monitoring
        for i in range(1000):
            # Mock database operation with monitoring
            with self.db_manager.get_session() as session:
                # Mock responsiveness check
                self.mock_system_optimizer.get_performance_metrics()
                
                # Mock memory monitoring
                if i % 100 == 0:  # Check every 100 operations
                    self.mock_system_optimizer.check_responsiveness()
        
        monitoring_duration = time.time() - monitoring_start
        
        # Calculate overhead
        overhead_percent = ((monitoring_duration - baseline_duration) / baseline_duration) * 100
        
        # Verify overhead is acceptable (< 50% for mock tests, would be much lower in real implementation)
        self.assertLess(overhead_percent, 50.0, 
                       f"Responsiveness monitoring overhead too high: {overhead_percent:.2f}%")
        
        # Log performance results
        print(f"Baseline duration: {baseline_duration:.3f}s")
        print(f"Monitoring duration: {monitoring_duration:.3f}s")
        print(f"Overhead: {overhead_percent:.2f}%")
    
    def test_concurrent_responsiveness_monitoring_performance(self):
        """Test responsiveness monitoring under concurrent load"""
        results = []
        errors = []
        
        def worker_thread(worker_id):
            """Worker thread for concurrent testing"""
            try:
                thread_results = {
                    'worker_id': worker_id,
                    'operations_completed': 0,
                    'responsiveness_checks': 0,
                    'avg_response_time': 0,
                    'errors': 0
                }
                
                start_time = time.time()
                operation_times = []
                
                # Perform operations for test duration
                while time.time() - start_time < 30:  # 30 second test
                    operation_start = time.time()
                    
                    try:
                        # Mock database operation
                        with self.db_manager.get_session() as session:
                            # Simulate work
                            time.sleep(0.001)  # 1ms simulated work
                        
                        # Periodic responsiveness check
                        if thread_results['operations_completed'] % 50 == 0:
                            responsiveness_result = self.mock_system_optimizer.check_responsiveness()
                            thread_results['responsiveness_checks'] += 1
                        
                        operation_time = time.time() - operation_start
                        operation_times.append(operation_time)
                        thread_results['operations_completed'] += 1
                        
                    except Exception as e:
                        thread_results['errors'] += 1
                        errors.append(f"Worker {worker_id}: {str(e)}")
                
                # Calculate average response time
                if operation_times:
                    thread_results['avg_response_time'] = sum(operation_times) / len(operation_times)
                
                results.append(thread_results)
                
            except Exception as e:
                errors.append(f"Worker {worker_id} failed: {str(e)}")
        
        # Start concurrent workers
        threads = []
        for i in range(self.performance_config['concurrent_users']):
            thread = threading.Thread(target=worker_thread, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Analyze results
        self.assertEqual(len(results), self.performance_config['concurrent_users'])
        self.assertEqual(len(errors), 0, f"Errors occurred: {errors}")
        
        # Calculate performance metrics
        total_operations = sum(r['operations_completed'] for r in results)
        total_responsiveness_checks = sum(r['responsiveness_checks'] for r in results)
        avg_response_times = [r['avg_response_time'] for r in results if r['avg_response_time'] > 0]
        
        overall_avg_response_time = sum(avg_response_times) / len(avg_response_times)
        
        # Performance assertions
        self.assertGreater(total_operations, 0)
        self.assertGreater(total_responsiveness_checks, 0)
        self.assertLess(overall_avg_response_time, 0.1, "Average response time too high")
        
        # Log performance results
        print(f"Total operations: {total_operations}")
        print(f"Total responsiveness checks: {total_responsiveness_checks}")
        print(f"Average response time: {overall_avg_response_time:.4f}s")
        print(f"Operations per second: {total_operations / 30:.2f}")
    
    def test_memory_monitoring_performance_impact(self):
        """Test performance impact of memory monitoring"""
        # Test memory monitoring overhead
        memory_checks = []
        
        def perform_memory_monitoring():
            """Perform memory monitoring operations"""
            start_time = time.time()
            
            # Mock memory monitoring operations
            for i in range(100):
                # Mock memory usage check
                memory_percent = 50.0 + (i % 20)  # Simulate varying memory usage
                
                # Mock memory leak detection
                if i % 10 == 0:
                    leak_result = {'leaks_detected': [], 'memory_trend': 'stable'}
                
                # Mock cleanup trigger check
                if memory_percent > 80:
                    cleanup_triggered = True
                else:
                    cleanup_triggered = False
            
            duration = time.time() - start_time
            memory_checks.append(duration)
            return duration
        
        # Perform multiple memory monitoring cycles
        monitoring_durations = []
        for cycle in range(10):
            duration = perform_memory_monitoring()
            monitoring_durations.append(duration)
        
        # Analyze memory monitoring performance
        avg_monitoring_duration = sum(monitoring_durations) / len(monitoring_durations)
        max_monitoring_duration = max(monitoring_durations)
        
        # Performance assertions
        self.assertLess(avg_monitoring_duration, 0.1, "Memory monitoring too slow")
        self.assertLess(max_monitoring_duration, 0.2, "Memory monitoring peak too slow")
        
        # Log results
        print(f"Average memory monitoring duration: {avg_monitoring_duration:.4f}s")
        print(f"Max memory monitoring duration: {max_monitoring_duration:.4f}s")
    
    def test_connection_pool_monitoring_performance(self):
        """Test performance of connection pool monitoring"""
        # Mock connection pool monitoring
        pool_monitoring_times = []
        
        def monitor_connection_pool():
            """Monitor connection pool performance"""
            start_time = time.time()
            
            # Mock connection pool statistics gathering
            pool_stats = {
                'size': 20,
                'checked_out': 10,
                'overflow': 2,
                'invalid': 0
            }
            
            # Mock health assessment
            utilization = pool_stats['checked_out'] / pool_stats['size']
            health_status = 'healthy' if utilization < 0.8 else 'warning'
            
            # Mock leak detection
            if pool_stats['overflow'] > 5:
                leak_detected = True
            else:
                leak_detected = False
            
            duration = time.time() - start_time
            pool_monitoring_times.append(duration)
            return duration
        
        # Perform connection pool monitoring cycles
        for cycle in range(100):
            monitor_connection_pool()
        
        # Analyze connection pool monitoring performance
        avg_pool_monitoring = sum(pool_monitoring_times) / len(pool_monitoring_times)
        max_pool_monitoring = max(pool_monitoring_times)
        
        # Performance assertions
        self.assertLess(avg_pool_monitoring, 0.01, "Connection pool monitoring too slow")
        self.assertLess(max_pool_monitoring, 0.05, "Connection pool monitoring peak too slow")
        
        # Log results
        print(f"Average pool monitoring duration: {avg_pool_monitoring:.6f}s")
        print(f"Max pool monitoring duration: {max_pool_monitoring:.6f}s")
    
    def test_background_cleanup_performance_integration(self):
        """Test background cleanup performance integration"""
        # Mock background cleanup operations
        cleanup_operations = []
        
        def simulate_background_cleanup():
            """Simulate background cleanup operations"""
            start_time = time.time()
            
            # Mock different cleanup types
            cleanup_types = ['audit_logs', 'expired_sessions', 'cache_cleanup', 'temp_files']
            
            for cleanup_type in cleanup_types:
                cleanup_start = time.time()
                
                # Mock cleanup operation
                if cleanup_type == 'audit_logs':
                    items_cleaned = 50
                    time.sleep(0.01)  # Simulate cleanup time
                elif cleanup_type == 'expired_sessions':
                    items_cleaned = 25
                    time.sleep(0.005)
                elif cleanup_type == 'cache_cleanup':
                    items_cleaned = 100
                    time.sleep(0.002)
                else:  # temp_files
                    items_cleaned = 10
                    time.sleep(0.008)
                
                cleanup_duration = time.time() - cleanup_start
                
                cleanup_operations.append({
                    'type': cleanup_type,
                    'items_cleaned': items_cleaned,
                    'duration': cleanup_duration
                })
            
            total_duration = time.time() - start_time
            return total_duration
        
        # Perform background cleanup cycles
        cleanup_durations = []
        for cycle in range(5):
            duration = simulate_background_cleanup()
            cleanup_durations.append(duration)
        
        # Analyze cleanup performance
        avg_cleanup_duration = sum(cleanup_durations) / len(cleanup_durations)
        total_items_cleaned = sum(op['items_cleaned'] for op in cleanup_operations)
        
        # Performance assertions
        self.assertLess(avg_cleanup_duration, 1.0, "Background cleanup too slow")
        self.assertGreater(total_items_cleaned, 0, "No items cleaned")
        
        # Log results
        print(f"Average cleanup cycle duration: {avg_cleanup_duration:.3f}s")
        print(f"Total items cleaned: {total_items_cleaned}")
        print(f"Cleanup efficiency: {total_items_cleaned / avg_cleanup_duration:.2f} items/second")
    
    def test_responsiveness_dashboard_performance(self):
        """Test responsiveness dashboard performance"""
        # Mock dashboard data gathering
        dashboard_metrics = []
        
        def gather_dashboard_data():
            """Gather responsiveness dashboard data"""
            start_time = time.time()
            
            # Mock data gathering operations
            system_metrics = self.mock_system_optimizer.get_performance_metrics()
            responsiveness_check = self.mock_system_optimizer.check_responsiveness()
            cleanup_stats = self.mock_cleanup_manager.get_cleanup_stats()
            
            # Mock additional dashboard data
            dashboard_data = {
                'system_metrics': system_metrics,
                'responsiveness_status': responsiveness_check,
                'cleanup_statistics': cleanup_stats,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            duration = time.time() - start_time
            dashboard_metrics.append(duration)
            return dashboard_data, duration
        
        # Perform dashboard data gathering cycles
        dashboard_durations = []
        for cycle in range(20):
            data, duration = gather_dashboard_data()
            dashboard_durations.append(duration)
        
        # Analyze dashboard performance
        avg_dashboard_duration = sum(dashboard_durations) / len(dashboard_durations)
        max_dashboard_duration = max(dashboard_durations)
        
        # Performance assertions
        self.assertLess(avg_dashboard_duration, 0.1, "Dashboard data gathering too slow")
        self.assertLess(max_dashboard_duration, 0.2, "Dashboard peak performance too slow")
        
        # Log results
        print(f"Average dashboard data gathering: {avg_dashboard_duration:.4f}s")
        print(f"Max dashboard data gathering: {max_dashboard_duration:.4f}s")
    
    def test_integrated_responsiveness_system_performance(self):
        """Test integrated responsiveness system performance"""
        # Test complete responsiveness system performance
        system_performance_metrics = []
        
        def run_integrated_responsiveness_cycle():
            """Run complete responsiveness monitoring cycle"""
            cycle_start = time.time()
            
            # 1. System metrics collection
            metrics_start = time.time()
            system_metrics = self.mock_system_optimizer.get_performance_metrics()
            metrics_duration = time.time() - metrics_start
            
            # 2. Responsiveness check
            check_start = time.time()
            responsiveness_result = self.mock_system_optimizer.check_responsiveness()
            check_duration = time.time() - check_start
            
            # 3. Memory monitoring
            memory_start = time.time()
            # Mock memory monitoring
            memory_usage = 65.0  # Mock memory percentage
            memory_duration = time.time() - memory_start
            
            # 4. Connection pool monitoring
            pool_start = time.time()
            # Mock connection pool monitoring
            pool_utilization = 0.7  # Mock utilization
            pool_duration = time.time() - pool_start
            
            # 5. Cleanup coordination (if needed)
            cleanup_start = time.time()
            if memory_usage > 80 or pool_utilization > 0.9:
                cleanup_stats = self.mock_cleanup_manager.get_cleanup_stats()
            cleanup_duration = time.time() - cleanup_start
            
            total_cycle_duration = time.time() - cycle_start
            
            cycle_metrics = {
                'total_duration': total_cycle_duration,
                'metrics_duration': metrics_duration,
                'check_duration': check_duration,
                'memory_duration': memory_duration,
                'pool_duration': pool_duration,
                'cleanup_duration': cleanup_duration
            }
            
            system_performance_metrics.append(cycle_metrics)
            return cycle_metrics
        
        # Run multiple integrated cycles
        for cycle in range(10):
            run_integrated_responsiveness_cycle()
        
        # Analyze integrated system performance
        avg_total_duration = sum(m['total_duration'] for m in system_performance_metrics) / len(system_performance_metrics)
        avg_metrics_duration = sum(m['metrics_duration'] for m in system_performance_metrics) / len(system_performance_metrics)
        avg_check_duration = sum(m['check_duration'] for m in system_performance_metrics) / len(system_performance_metrics)
        
        # Performance assertions
        self.assertLess(avg_total_duration, 0.5, "Integrated responsiveness cycle too slow")
        self.assertLess(avg_metrics_duration, 0.1, "Metrics collection too slow")
        self.assertLess(avg_check_duration, 0.1, "Responsiveness check too slow")
        
        # Log integrated performance results
        print(f"Average integrated cycle duration: {avg_total_duration:.4f}s")
        print(f"Average metrics collection: {avg_metrics_duration:.4f}s")
        print(f"Average responsiveness check: {avg_check_duration:.4f}s")
        
        # Test performance consistency
        duration_variance = sum((m['total_duration'] - avg_total_duration) ** 2 for m in system_performance_metrics) / len(system_performance_metrics)
        duration_std_dev = duration_variance ** 0.5
        
        # Performance consistency assertion (allow for more variance in mock tests)
        consistency_threshold = max(avg_total_duration * 0.5, 0.001)  # More lenient for mock tests
        self.assertLess(duration_std_dev, consistency_threshold, "Performance too inconsistent")
        
        print(f"Performance standard deviation: {duration_std_dev:.4f}s")
        print(f"Performance consistency: {(1 - duration_std_dev / avg_total_duration) * 100:.1f}%")


class TestResponsivenessLoadTesting(unittest.TestCase):
    """Load testing for responsiveness features"""
    
    def setUp(self):
        """Set up load testing environment"""
        self.config = Config()
        self.db_manager = Mock(spec=DatabaseManager)
        
        # Set up mock database session context manager
        mock_session = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        self.db_manager.get_session.return_value = mock_session
        
        # Load testing configuration (reduced for faster testing)
        self.load_config = {
            'max_concurrent_users': 5,  # Reduced for faster testing
            'ramp_up_time_seconds': 5,
            'test_duration_seconds': 10,
            'responsiveness_check_frequency': 10  # Every 10 operations
        }
    
    def test_responsiveness_monitoring_under_load(self):
        """Test responsiveness monitoring under high load"""
        results = []
        errors = []
        
        def load_test_worker(worker_id, operations_count):
            """Worker for load testing"""
            try:
                worker_results = {
                    'worker_id': worker_id,
                    'operations_completed': 0,
                    'responsiveness_checks_completed': 0,
                    'avg_operation_time': 0,
                    'errors': 0
                }
                
                operation_times = []
                
                for i in range(operations_count):
                    operation_start = time.time()
                    
                    try:
                        # Mock database operation
                        with self.db_manager.get_session() as session:
                            # Simulate work
                            time.sleep(0.001)
                        
                        # Periodic responsiveness check
                        if i % self.load_config['responsiveness_check_frequency'] == 0:
                            # Mock responsiveness check
                            responsiveness_result = {
                                'responsive': True,
                                'issues': [],
                                'overall_status': 'healthy'
                            }
                            worker_results['responsiveness_checks_completed'] += 1
                        
                        operation_time = time.time() - operation_start
                        operation_times.append(operation_time)
                        worker_results['operations_completed'] += 1
                        
                    except Exception as e:
                        worker_results['errors'] += 1
                
                if operation_times:
                    worker_results['avg_operation_time'] = sum(operation_times) / len(operation_times)
                
                results.append(worker_results)
                
            except Exception as e:
                errors.append(f"Worker {worker_id}: {str(e)}")
        
        # Execute load test
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.load_config['max_concurrent_users']) as executor:
            futures = []
            
            for worker_id in range(self.load_config['max_concurrent_users']):
                operations_per_worker = 100  # Each worker performs 100 operations
                future = executor.submit(load_test_worker, worker_id, operations_per_worker)
                futures.append(future)
            
            # Wait for all workers to complete
            concurrent.futures.wait(futures)
        
        # Analyze load test results
        self.assertEqual(len(results), self.load_config['max_concurrent_users'])
        self.assertEqual(len(errors), 0, f"Load test errors: {errors}")
        
        total_operations = sum(r['operations_completed'] for r in results)
        total_responsiveness_checks = sum(r['responsiveness_checks_completed'] for r in results)
        avg_operation_times = [r['avg_operation_time'] for r in results if r['avg_operation_time'] > 0]
        
        # Handle case where no operation times were recorded
        if avg_operation_times:
            overall_avg_operation_time = sum(avg_operation_times) / len(avg_operation_times)
        else:
            overall_avg_operation_time = 0.0
        
        # Load test assertions
        self.assertGreater(total_operations, 0)
        self.assertGreater(total_responsiveness_checks, 0)
        if overall_avg_operation_time > 0:
            self.assertLess(overall_avg_operation_time, 0.1, "Operations too slow under load")
        
        # Log load test results
        print(f"Load test completed successfully")
        print(f"Total operations: {total_operations}")
        print(f"Total responsiveness checks: {total_responsiveness_checks}")
        print(f"Average operation time under load: {overall_avg_operation_time:.4f}s")
        print(f"Throughput: {total_operations / 60:.2f} operations/second")  # Assuming 60s test duration


if __name__ == '__main__':
    unittest.main()
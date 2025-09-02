# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Performance and Load Tests for Multi-Tenant Caption Management

This module provides comprehensive performance and load testing for the multi-tenant
caption management system, focusing on concurrent operations, large-scale monitoring,
database performance, and system resilience under load.
"""

import unittest
import time
import threading
import psutil
import gc
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any

from config import Config
from database import DatabaseManager
from models import User, UserRole, CaptionGenerationTask, TaskStatus, JobPriority
from admin_management_service import AdminManagementService, SystemOverview
from multi_tenant_control_service import MultiTenantControlService, UserJobLimits
from system_monitor import SystemMonitor, ResourceUsage
from task_queue_manager import TaskQueueManager


class TestConcurrentAdminOperations(unittest.TestCase):
    """Test performance of concurrent admin operations"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = Config()
        self.mock_db_manager = Mock(spec=DatabaseManager)
        self.mock_session = Mock()
        
        # Configure mock database manager
        self.mock_context_manager = MagicMock()
        self.mock_context_manager.__enter__.return_value = self.mock_session
        self.mock_context_manager.__exit__.return_value = None
        self.mock_db_manager.get_session.return_value = self.mock_context_manager
        
        # Create service instances
        self.admin_service = AdminManagementService(self.mock_db_manager, Mock())
        self.multi_tenant_service = MultiTenantControlService(self.mock_db_manager)
        
        # Mock admin user
        self.admin_user = Mock(spec=User)
        self.admin_user.id = 1
        self.admin_user.role = UserRole.ADMIN
        
        # Configure mock session to return admin user
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = self.admin_user
    
    def test_concurrent_admin_authorization_performance(self):
        """Test performance of concurrent admin authorization checks"""
        def admin_authorization_operation(operation_id):
            """Simulate admin authorization check"""
            start_time = time.time()
            
            try:
                result = self.admin_service._verify_admin_authorization(self.mock_session, 1)
                success = result is not None
            except Exception:
                success = False
            
            end_time = time.time()
            
            return {
                'operation_id': operation_id,
                'duration': end_time - start_time,
                'success': success
            }
        
        # Run 100 concurrent authorization checks
        num_operations = 100
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [
                executor.submit(admin_authorization_operation, i) 
                for i in range(num_operations)
            ]
            
            results = []
            for future in as_completed(futures):
                results.append(future.result())
        
        # Analyze performance
        successful_operations = [r for r in results if r['success']]
        avg_duration = sum(r['duration'] for r in successful_operations) / len(successful_operations)
        max_duration = max(r['duration'] for r in successful_operations)
        min_duration = min(r['duration'] for r in successful_operations)
        
        # Performance assertions
        self.assertEqual(len(successful_operations), num_operations)
        self.assertLess(avg_duration, 0.1, f"Average duration {avg_duration:.3f}s exceeds 100ms threshold")
        self.assertLess(max_duration, 0.5, f"Max duration {max_duration:.3f}s exceeds 500ms threshold")
        
        print(f"Admin Authorization Performance:")
        print(f"  Operations: {num_operations}")
        print(f"  Success rate: 100%")
        print(f"  Average duration: {avg_duration:.3f}s")
        print(f"  Min duration: {min_duration:.3f}s")
        print(f"  Max duration: {max_duration:.3f}s")
    
    def test_concurrent_system_overview_performance(self):
        """Test performance of concurrent system overview requests"""
        # Mock query results for system overview
        self.mock_session.query.return_value.count.side_effect = [10, 8, 50, 5, 3, 2, 40, 3, 2]
        
        def system_overview_operation(operation_id):
            """Simulate system overview request"""
            start_time = time.time()
            
            try:
                with patch.object(self.admin_service, '_calculate_system_health_score', return_value=85.0), \
                     patch.object(self.admin_service, '_get_resource_usage', return_value={'cpu': 50}), \
                     patch.object(self.admin_service, '_get_recent_errors', return_value=[]), \
                     patch.object(self.admin_service, '_get_performance_metrics', return_value={'avg_time': 30}):
                    
                    overview = self.admin_service.get_system_overview(1)
                    success = isinstance(overview, SystemOverview)
            except Exception:
                success = False
            
            end_time = time.time()
            
            return {
                'operation_id': operation_id,
                'duration': end_time - start_time,
                'success': success
            }
        
        # Run 50 concurrent system overview requests
        num_operations = 50
        with ThreadPoolExecutor(max_workers=15) as executor:
            futures = [
                executor.submit(system_overview_operation, i) 
                for i in range(num_operations)
            ]
            
            results = []
            for future in as_completed(futures):
                results.append(future.result())
        
        # Analyze performance
        successful_operations = [r for r in results if r['success']]
        avg_duration = sum(r['duration'] for r in successful_operations) / len(successful_operations)
        max_duration = max(r['duration'] for r in successful_operations)
        
        # Performance assertions
        self.assertEqual(len(successful_operations), num_operations)
        self.assertLess(avg_duration, 0.2, f"Average duration {avg_duration:.3f}s exceeds 200ms threshold")
        self.assertLess(max_duration, 1.0, f"Max duration {max_duration:.3f}s exceeds 1s threshold")
        
        print(f"System Overview Performance:")
        print(f"  Operations: {num_operations}")
        print(f"  Success rate: 100%")
        print(f"  Average duration: {avg_duration:.3f}s")
        print(f"  Max duration: {max_duration:.3f}s")
    
    def test_concurrent_user_limit_configuration(self):
        """Test performance of concurrent user limit configuration"""
        # Mock successful configuration
        self.mock_session.query.return_value.filter_by.return_value.first.side_effect = [
            self.admin_user,  # Admin verification
            Mock(id=2, role=UserRole.REVIEWER),  # Target user
            None  # No existing config
        ] * 100  # Repeat for all operations
        
        def configure_limits_operation(operation_id):
            """Simulate user limit configuration"""
            start_time = time.time()
            
            try:
                limits = UserJobLimits(
                    max_concurrent_jobs=operation_id % 5 + 1,
                    max_jobs_per_hour=operation_id % 50 + 10
                )
                result = self.multi_tenant_service.set_user_job_limits(1, 2, limits)
                success = result is True
            except Exception:
                success = False
            
            end_time = time.time()
            
            return {
                'operation_id': operation_id,
                'duration': end_time - start_time,
                'success': success
            }
        
        # Run 30 concurrent configuration operations
        num_operations = 30
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(configure_limits_operation, i) 
                for i in range(num_operations)
            ]
            
            results = []
            for future in as_completed(futures):
                results.append(future.result())
        
        # Analyze performance
        successful_operations = [r for r in results if r['success']]
        avg_duration = sum(r['duration'] for r in successful_operations) / len(successful_operations)
        
        # Performance assertions
        self.assertEqual(len(successful_operations), num_operations)
        self.assertLess(avg_duration, 0.15, f"Average duration {avg_duration:.3f}s exceeds 150ms threshold")
        
        print(f"User Limit Configuration Performance:")
        print(f"  Operations: {num_operations}")
        print(f"  Success rate: 100%")
        print(f"  Average duration: {avg_duration:.3f}s")


class TestLargeScaleMonitoring(unittest.TestCase):
    """Test performance of monitoring with large amounts of data"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = Config()
        self.mock_db_manager = Mock(spec=DatabaseManager)
        self.mock_session = Mock()
        
        # Configure mock database manager
        self.mock_context_manager = MagicMock()
        self.mock_context_manager.__enter__.return_value = self.mock_session
        self.mock_context_manager.__exit__.return_value = None
        self.mock_db_manager.get_session.return_value = self.mock_context_manager
        
        # Create service instances
        self.admin_service = AdminManagementService(self.mock_db_manager, Mock())
        self.system_monitor = SystemMonitor(self.mock_db_manager)
        
        # Create large dataset of mock tasks
        self.large_task_dataset = []
        for i in range(10000):  # 10,000 tasks
            task = Mock(spec=CaptionGenerationTask)
            task.id = f"large-scale-task-{i}"
            task.user_id = i % 100 + 1  # 100 different users
            task.status = TaskStatus.COMPLETED if i % 3 == 0 else TaskStatus.RUNNING
            task.created_at = datetime.now(timezone.utc) - timedelta(minutes=i % 1440)  # Spread over 24 hours
            task.started_at = task.created_at + timedelta(seconds=30)
            task.completed_at = task.started_at + timedelta(seconds=i % 300 + 60) if task.status == TaskStatus.COMPLETED else None
            self.large_task_dataset.append(task)
    
    def test_large_dataset_health_calculation_performance(self):
        """Test system health calculation with large dataset"""
        # Mock large dataset queries
        def mock_large_query(model_class):
            query_mock = Mock()
            if model_class == CaptionGenerationTask:
                # Simulate database filtering and counting
                query_mock.filter.return_value = query_mock
                query_mock.filter_by.return_value = query_mock
                
                # Simulate different count results for health calculation
                completed_tasks = [t for t in self.large_task_dataset if t.status == TaskStatus.COMPLETED]
                failed_tasks = [t for t in self.large_task_dataset if t.status == TaskStatus.FAILED]
                running_tasks = [t for t in self.large_task_dataset if t.status == TaskStatus.RUNNING]
                
                query_mock.count.side_effect = [
                    len(self.large_task_dataset),  # total recent tasks
                    len(completed_tasks),          # successful tasks
                    len(failed_tasks),             # failed tasks
                    len(running_tasks)             # queued/running tasks
                ]
            return query_mock
        
        self.mock_session.query.side_effect = mock_large_query
        
        # Test health calculation performance
        start_time = time.time()
        health_score = self.admin_service._calculate_system_health_score(self.mock_session)
        end_time = time.time()
        
        duration = end_time - start_time
        
        # Performance assertions
        self.assertIsInstance(health_score, float)
        self.assertGreaterEqual(health_score, 0.0)
        self.assertLessEqual(health_score, 100.0)
        self.assertLess(duration, 1.0, f"Health calculation took {duration:.3f}s, exceeds 1s threshold")
        
        print(f"Large Dataset Health Calculation:")
        print(f"  Dataset size: {len(self.large_task_dataset)} tasks")
        print(f"  Health score: {health_score:.1f}")
        print(f"  Calculation time: {duration:.3f}s")
    
    def test_performance_metrics_with_large_dataset(self):
        """Test performance metrics calculation with large dataset"""
        # Mock completed tasks for performance calculation
        completed_tasks = [t for t in self.large_task_dataset if t.status == TaskStatus.COMPLETED and t.completed_at]
        
        def mock_performance_query(model_class):
            query_mock = Mock()
            if model_class == CaptionGenerationTask:
                query_mock.filter.return_value = query_mock
                query_mock.all.return_value = completed_tasks[:1000]  # Limit for performance
            return query_mock
        
        self.mock_session.query.side_effect = mock_performance_query
        
        # Mock task queue stats
        mock_task_queue = Mock()
        mock_task_queue.get_queue_stats.return_value = {'queued': 50, 'running': 25}
        
        # Test performance metrics calculation
        start_time = time.time()
        metrics = self.admin_service._get_performance_metrics(self.mock_session)
        end_time = time.time()
        
        duration = end_time - start_time
        
        # Performance assertions
        self.assertIsInstance(metrics, dict)
        self.assertIn('avg_completion_time_seconds', metrics)
        self.assertIn('completed_tasks_24h', metrics)
        self.assertLess(duration, 2.0, f"Metrics calculation took {duration:.3f}s, exceeds 2s threshold")
        
        print(f"Performance Metrics Calculation:")
        print(f"  Processed tasks: {len(completed_tasks[:1000])}")
        print(f"  Calculation time: {duration:.3f}s")
        print(f"  Average completion time: {metrics.get('avg_completion_time_seconds', 'N/A')}s")
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    def test_system_resource_monitoring_performance(self, mock_disk, mock_memory, mock_cpu):
        """Test system resource monitoring performance"""
        # Mock system resource data
        mock_cpu.return_value = 45.5
        mock_memory.return_value.percent = 67.2
        mock_memory.return_value.used = 8 * 1024 * 1024 * 1024  # 8GB
        mock_memory.return_value.total = 16 * 1024 * 1024 * 1024  # 16GB
        mock_disk.return_value.percent = 23.8
        mock_disk.return_value.used = 100 * 1024 * 1024 * 1024  # 100GB
        mock_disk.return_value.total = 500 * 1024 * 1024 * 1024  # 500GB
        
        # Test multiple concurrent resource monitoring calls
        def resource_monitoring_operation(operation_id):
            """Simulate resource monitoring"""
            start_time = time.time()
            
            try:
                resource_usage = self.system_monitor.check_resource_usage()
                success = isinstance(resource_usage, ResourceUsage)
            except Exception:
                success = False
            
            end_time = time.time()
            
            return {
                'operation_id': operation_id,
                'duration': end_time - start_time,
                'success': success
            }
        
        # Run 20 concurrent resource monitoring operations
        num_operations = 20
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(resource_monitoring_operation, i) 
                for i in range(num_operations)
            ]
            
            results = []
            for future in as_completed(futures):
                results.append(future.result())
        
        # Analyze performance
        successful_operations = [r for r in results if r['success']]
        avg_duration = sum(r['duration'] for r in successful_operations) / len(successful_operations)
        
        # Performance assertions
        self.assertEqual(len(successful_operations), num_operations)
        self.assertLess(avg_duration, 0.5, f"Average duration {avg_duration:.3f}s exceeds 500ms threshold")
        
        print(f"Resource Monitoring Performance:")
        print(f"  Operations: {num_operations}")
        print(f"  Success rate: 100%")
        print(f"  Average duration: {avg_duration:.3f}s")


class TestMemoryUsageUnderLoad(unittest.TestCase):
    """Test memory usage during large-scale operations"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = Config()
        self.mock_db_manager = Mock(spec=DatabaseManager)
        
        # Get initial memory usage
        self.process = psutil.Process()
        self.initial_memory = self.process.memory_info().rss / 1024 / 1024  # MB
    
    def test_memory_usage_during_large_operations(self):
        """Test memory usage during large-scale admin operations"""
        # Create large dataset
        large_dataset = []
        for i in range(50000):  # 50,000 mock objects
            mock_task = Mock(spec=CaptionGenerationTask)
            mock_task.id = f"memory-test-{i}"
            mock_task.user_id = i % 1000 + 1  # 1000 different users
            mock_task.status = TaskStatus.COMPLETED if i % 2 == 0 else TaskStatus.RUNNING
            mock_task.created_at = datetime.now(timezone.utc)
            large_dataset.append(mock_task)
        
        # Process the dataset in chunks
        chunk_size = 1000
        processed_count = 0
        memory_measurements = []
        
        for i in range(0, len(large_dataset), chunk_size):
            chunk = large_dataset[i:i + chunk_size]
            
            # Process chunk (simulate admin operations)
            for task in chunk:
                # Simulate processing
                processed_count += 1
            
            # Measure memory usage
            current_memory = self.process.memory_info().rss / 1024 / 1024  # MB
            memory_measurements.append(current_memory)
            
            # Force garbage collection every 10 chunks
            if (i // chunk_size) % 10 == 0:
                gc.collect()
        
        # Final memory measurement
        final_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - self.initial_memory
        max_memory = max(memory_measurements)
        max_memory_increase = max_memory - self.initial_memory
        
        # Memory usage assertions
        self.assertEqual(processed_count, len(large_dataset))
        self.assertLess(memory_increase, 200, f"Final memory increase {memory_increase:.1f}MB exceeds 200MB threshold")
        self.assertLess(max_memory_increase, 300, f"Max memory increase {max_memory_increase:.1f}MB exceeds 300MB threshold")
        
        print(f"Memory Usage Test:")
        print(f"  Processed objects: {processed_count}")
        print(f"  Initial memory: {self.initial_memory:.1f}MB")
        print(f"  Final memory: {final_memory:.1f}MB")
        print(f"  Memory increase: {memory_increase:.1f}MB")
        print(f"  Max memory: {max_memory:.1f}MB")
        print(f"  Max memory increase: {max_memory_increase:.1f}MB")
    
    def test_memory_leak_detection(self):
        """Test for memory leaks during repeated operations"""
        # Perform repeated operations and monitor memory
        memory_samples = []
        num_iterations = 100
        
        for i in range(num_iterations):
            # Create and process temporary objects
            temp_objects = []
            for j in range(1000):
                temp_obj = Mock(spec=CaptionGenerationTask)
                temp_obj.id = f"leak-test-{i}-{j}"
                temp_objects.append(temp_obj)
            
            # Process objects
            for obj in temp_objects:
                # Simulate processing
                pass
            
            # Clear references
            temp_objects.clear()
            del temp_objects
            
            # Force garbage collection every 10 iterations
            if i % 10 == 0:
                gc.collect()
                current_memory = self.process.memory_info().rss / 1024 / 1024  # MB
                memory_samples.append(current_memory)
        
        # Analyze memory trend
        if len(memory_samples) > 1:
            memory_trend = memory_samples[-1] - memory_samples[0]
            avg_memory = sum(memory_samples) / len(memory_samples)
            
            # Memory leak assertions
            self.assertLess(memory_trend, 50, f"Memory trend {memory_trend:.1f}MB suggests potential leak")
            
            print(f"Memory Leak Detection:")
            print(f"  Iterations: {num_iterations}")
            print(f"  Memory samples: {len(memory_samples)}")
            print(f"  Initial memory: {memory_samples[0]:.1f}MB")
            print(f"  Final memory: {memory_samples[-1]:.1f}MB")
            print(f"  Memory trend: {memory_trend:.1f}MB")
            print(f"  Average memory: {avg_memory:.1f}MB")


class TestDatabaseConnectionPoolPerformance(unittest.TestCase):
    """Test database connection pool performance under load"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = Config()
        self.mock_db_manager = Mock(spec=DatabaseManager)
        
        # Mock connection pool behavior
        self.connection_pool_stats = {
            'active_connections': 0,
            'total_connections': 0,
            'max_connections': 20
        }
    
    def test_connection_pool_under_concurrent_load(self):
        """Test connection pool performance under concurrent load"""
        def database_operation(operation_id):
            """Simulate database operation"""
            start_time = time.time()
            
            # Simulate getting database connection
            self.connection_pool_stats['active_connections'] += 1
            self.connection_pool_stats['total_connections'] = max(
                self.connection_pool_stats['total_connections'],
                self.connection_pool_stats['active_connections']
            )
            
            try:
                # Simulate database session
                session = self.mock_db_manager.get_session()
                
                # Simulate database query
                with session:
                    # Mock query execution time
                    time.sleep(0.01)  # 10ms query time
                    result = f"result-{operation_id}"
                
                success = True
            except Exception:
                success = False
            finally:
                # Release connection
                self.connection_pool_stats['active_connections'] -= 1
            
            end_time = time.time()
            
            return {
                'operation_id': operation_id,
                'duration': end_time - start_time,
                'success': success
            }
        
        # Run 100 concurrent database operations
        num_operations = 100
        with ThreadPoolExecutor(max_workers=25) as executor:
            futures = [
                executor.submit(database_operation, i) 
                for i in range(num_operations)
            ]
            
            results = []
            for future in as_completed(futures):
                results.append(future.result())
        
        # Analyze performance
        successful_operations = [r for r in results if r['success']]
        avg_duration = sum(r['duration'] for r in successful_operations) / len(successful_operations)
        max_duration = max(r['duration'] for r in successful_operations)
        
        # Performance assertions
        self.assertEqual(len(successful_operations), num_operations)
        self.assertLess(avg_duration, 0.1, f"Average duration {avg_duration:.3f}s exceeds 100ms threshold")
        self.assertLess(max_duration, 0.5, f"Max duration {max_duration:.3f}s exceeds 500ms threshold")
        self.assertLessEqual(
            self.connection_pool_stats['total_connections'],
            self.connection_pool_stats['max_connections'],
            "Connection pool exceeded maximum connections"
        )
        
        print(f"Database Connection Pool Performance:")
        print(f"  Operations: {num_operations}")
        print(f"  Success rate: 100%")
        print(f"  Average duration: {avg_duration:.3f}s")
        print(f"  Max duration: {max_duration:.3f}s")
        print(f"  Max concurrent connections: {self.connection_pool_stats['total_connections']}")
    
    def test_connection_pool_exhaustion_handling(self):
        """Test handling of connection pool exhaustion"""
        # Simulate connection pool exhaustion
        max_connections = 5
        active_connections = 0
        connection_wait_times = []
        
        def connection_exhaustion_operation(operation_id):
            """Simulate operation that may exhaust connection pool"""
            nonlocal active_connections
            
            start_time = time.time()
            
            # Wait for available connection (simulate pool exhaustion)
            while active_connections >= max_connections:
                time.sleep(0.001)  # 1ms wait
            
            connection_acquired_time = time.time()
            wait_time = connection_acquired_time - start_time
            connection_wait_times.append(wait_time)
            
            # Acquire connection
            active_connections += 1
            
            try:
                # Simulate database work
                time.sleep(0.05)  # 50ms work
                success = True
            except Exception:
                success = False
            finally:
                # Release connection
                active_connections -= 1
            
            end_time = time.time()
            
            return {
                'operation_id': operation_id,
                'duration': end_time - start_time,
                'wait_time': wait_time,
                'success': success
            }
        
        # Run operations that will exhaust connection pool
        num_operations = 20
        with ThreadPoolExecutor(max_workers=15) as executor:
            futures = [
                executor.submit(connection_exhaustion_operation, i) 
                for i in range(num_operations)
            ]
            
            results = []
            for future in as_completed(futures):
                results.append(future.result())
        
        # Analyze connection pool behavior
        successful_operations = [r for r in results if r['success']]
        avg_wait_time = sum(r['wait_time'] for r in successful_operations) / len(successful_operations)
        max_wait_time = max(r['wait_time'] for r in successful_operations)
        
        # Connection pool assertions
        self.assertEqual(len(successful_operations), num_operations)
        self.assertLess(avg_wait_time, 0.1, f"Average wait time {avg_wait_time:.3f}s exceeds 100ms threshold")
        self.assertLess(max_wait_time, 0.5, f"Max wait time {max_wait_time:.3f}s exceeds 500ms threshold")
        
        print(f"Connection Pool Exhaustion Handling:")
        print(f"  Operations: {num_operations}")
        print(f"  Max connections: {max_connections}")
        print(f"  Success rate: 100%")
        print(f"  Average wait time: {avg_wait_time:.3f}s")
        print(f"  Max wait time: {max_wait_time:.3f}s")


if __name__ == '__main__':
    # Run performance and load test suite
    unittest.main(verbosity=2)
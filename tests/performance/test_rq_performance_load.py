# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Performance and Load Tests for RQ System

Tests high-volume task processing scenarios, queue operations performance,
worker scaling behavior, and memory usage under load.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import time
import threading
import statistics
import psutil
import gc
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import redis
from rq import Queue, Job

from app.core.database.core.database_manager import DatabaseManager
from app.core.security.features.caption_security import CaptionSecurityManager
from app.services.task.rq.rq_queue_manager import RQQueueManager
from app.services.task.rq.rq_worker_manager import RQWorkerManager
from app.services.task.rq.task_serializer import TaskSerializer, RQTaskData
from app.services.task.rq.priority_queue_handler import PriorityQueueHandler
from app.services.task.rq.rq_config import RQConfig, TaskPriority
from models import CaptionGenerationTask, TaskStatus, JobPriority


class PerformanceTestBase(unittest.TestCase):
    """Base class for performance tests with common setup"""
    
    def setUp(self):
        """Set up performance test fixtures"""
        # Mock dependencies
        self.mock_db_manager = Mock(spec=DatabaseManager)
        self.mock_session = Mock()
        self.mock_db_manager.get_session.return_value = self.mock_session
        
        self.mock_security_manager = Mock(spec=CaptionSecurityManager)
        self.mock_security_manager.generate_secure_task_id.side_effect = lambda: f"perf-task-{int(time.time() * 1000000)}"
        
        # Mock Redis connection
        self.mock_redis = Mock(spec=redis.Redis)
        self.mock_redis.ping.return_value = True
        
        # Create test configuration
        self.config = RQConfig()
        
        # Performance tracking
        self.performance_metrics = {
            'start_time': None,
            'end_time': None,
            'operations': 0,
            'errors': 0,
            'memory_usage': [],
            'response_times': []
        }
    
    def start_performance_tracking(self):
        """Start performance tracking"""
        self.performance_metrics['start_time'] = time.time()
        self.performance_metrics['operations'] = 0
        self.performance_metrics['errors'] = 0
        self.performance_metrics['memory_usage'] = []
        self.performance_metrics['response_times'] = []
        
        # Initial memory measurement
        process = psutil.Process()
        self.performance_metrics['memory_usage'].append(process.memory_info().rss / 1024 / 1024)  # MB
    
    def end_performance_tracking(self):
        """End performance tracking and calculate metrics"""
        self.performance_metrics['end_time'] = time.time()
        
        # Final memory measurement
        process = psutil.Process()
        self.performance_metrics['memory_usage'].append(process.memory_info().rss / 1024 / 1024)  # MB
        
        # Calculate derived metrics
        duration = self.performance_metrics['end_time'] - self.performance_metrics['start_time']
        operations = self.performance_metrics['operations']
        
        return {
            'duration': duration,
            'operations': operations,
            'operations_per_second': operations / duration if duration > 0 else 0,
            'errors': self.performance_metrics['errors'],
            'error_rate': self.performance_metrics['errors'] / operations if operations > 0 else 0,
            'avg_response_time': statistics.mean(self.performance_metrics['response_times']) if self.performance_metrics['response_times'] else 0,
            'median_response_time': statistics.median(self.performance_metrics['response_times']) if self.performance_metrics['response_times'] else 0,
            'p95_response_time': self._calculate_percentile(self.performance_metrics['response_times'], 95) if self.performance_metrics['response_times'] else 0,
            'memory_start': self.performance_metrics['memory_usage'][0] if self.performance_metrics['memory_usage'] else 0,
            'memory_end': self.performance_metrics['memory_usage'][-1] if self.performance_metrics['memory_usage'] else 0,
            'memory_peak': max(self.performance_metrics['memory_usage']) if self.performance_metrics['memory_usage'] else 0
        }
    
    def _calculate_percentile(self, data, percentile):
        """Calculate percentile of data"""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    def record_operation(self, response_time=None, error=False):
        """Record a single operation"""
        self.performance_metrics['operations'] += 1
        if error:
            self.performance_metrics['errors'] += 1
        if response_time is not None:
            self.performance_metrics['response_times'].append(response_time)
        
        # Periodic memory measurement
        if self.performance_metrics['operations'] % 100 == 0:
            process = psutil.Process()
            self.performance_metrics['memory_usage'].append(process.memory_info().rss / 1024 / 1024)


class TestRQQueuePerformance(PerformanceTestBase):
    """Test RQ queue operations performance"""
    
    def setUp(self):
        """Set up queue performance test fixtures"""
        super().setUp()
        
        # Initialize queue manager with mocks
        with patch('app.services.task.rq.rq_queue_manager.RedisConnectionManager'):
            with patch('app.services.task.rq.rq_queue_manager.Queue') as mock_queue_class:
                # Mock queues
                self.mock_queues = {}
                for priority in ['urgent', 'high', 'normal', 'low']:
                    mock_queue = Mock(spec=Queue)
                    mock_queue.name = priority
                    mock_queue.count = 0
                    self.mock_queues[priority] = mock_queue
                
                mock_queue_class.side_effect = lambda name, **kwargs: self.mock_queues[name]
                
                self.queue_manager = RQQueueManager(
                    self.mock_db_manager,
                    self.config,
                    self.mock_security_manager
                )
                self.queue_manager.redis_connection = self.mock_redis
                self.queue_manager.queues = self.mock_queues
                self.queue_manager._redis_available = True
    
    def test_high_volume_task_enqueuing(self):
        """Test performance of high-volume task enqueuing"""
        num_tasks = 1000
        
        # Mock user task tracker
        mock_user_tracker = Mock()
        mock_user_tracker.has_active_task.return_value = False
        mock_user_tracker.set_user_active_task.return_value = True
        self.queue_manager.user_task_tracker = mock_user_tracker
        
        # Mock queue enqueue
        mock_job = Mock(spec=Job)
        mock_job.id = "perf-job"
        for queue in self.mock_queues.values():
            queue.enqueue.return_value = mock_job
        
        # Start performance tracking
        self.start_performance_tracking()
        
        # Enqueue tasks
        for i in range(num_tasks):
            start_time = time.time()
            
            try:
                task = CaptionGenerationTask(
                    id=f"perf-task-{i}",
                    user_id=i + 1,  # Different user for each task
                    platform_connection_id=1,
                    status=TaskStatus.QUEUED
                )
                
                result = self.queue_manager.enqueue_task(task, TaskPriority.NORMAL)
                
                response_time = (time.time() - start_time) * 1000  # ms
                self.record_operation(response_time=response_time)
                
                # Verify task was enqueued
                self.assertIsNotNone(result)
                
            except Exception as e:
                response_time = (time.time() - start_time) * 1000  # ms
                self.record_operation(response_time=response_time, error=True)
        
        # End performance tracking
        metrics = self.end_performance_tracking()
        
        # Performance assertions
        self.assertGreater(metrics['operations_per_second'], 100)  # At least 100 ops/sec
        self.assertLess(metrics['avg_response_time'], 50)  # Less than 50ms average
        self.assertLess(metrics['error_rate'], 0.01)  # Less than 1% error rate
        
        # Memory usage should be reasonable
        memory_growth = metrics['memory_end'] - metrics['memory_start']
        self.assertLess(memory_growth, 100)  # Less than 100MB growth
        
        print(f"High Volume Enqueuing Performance:")
        print(f"  Operations/sec: {metrics['operations_per_second']:.2f}")
        print(f"  Avg response time: {metrics['avg_response_time']:.2f}ms")
        print(f"  P95 response time: {metrics['p95_response_time']:.2f}ms")
        print(f"  Error rate: {metrics['error_rate']:.4f}")
        print(f"  Memory growth: {memory_growth:.2f}MB")
    
    def test_concurrent_queue_operations(self):
        """Test performance of concurrent queue operations"""
        num_threads = 10
        tasks_per_thread = 100
        
        # Mock user task tracker
        mock_user_tracker = Mock()
        mock_user_tracker.has_active_task.return_value = False
        mock_user_tracker.set_user_active_task.return_value = True
        self.queue_manager.user_task_tracker = mock_user_tracker
        
        # Mock queue operations
        mock_job = Mock(spec=Job)
        mock_job.id = "concurrent-job"
        for queue in self.mock_queues.values():
            queue.enqueue.return_value = mock_job
        
        # Start performance tracking
        self.start_performance_tracking()
        
        # Concurrent task enqueuing
        def enqueue_tasks(thread_id):
            thread_results = []
            for i in range(tasks_per_thread):
                start_time = time.time()
                
                try:
                    task = CaptionGenerationTask(
                        id=f"concurrent-task-{thread_id}-{i}",
                        user_id=thread_id * 1000 + i,  # Unique user per task
                        platform_connection_id=1,
                        status=TaskStatus.QUEUED
                    )
                    
                    result = self.queue_manager.enqueue_task(task, TaskPriority.NORMAL)
                    
                    response_time = (time.time() - start_time) * 1000  # ms
                    thread_results.append(('success', response_time))
                    
                except Exception as e:
                    response_time = (time.time() - start_time) * 1000  # ms
                    thread_results.append(('error', response_time))
            
            return thread_results
        
        # Execute concurrent operations
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(enqueue_tasks, i) for i in range(num_threads)]
            
            for future in as_completed(futures):
                thread_results = future.result()
                for result_type, response_time in thread_results:
                    error = result_type == 'error'
                    self.record_operation(response_time=response_time, error=error)
        
        # End performance tracking
        metrics = self.end_performance_tracking()
        
        # Performance assertions for concurrent operations
        self.assertGreater(metrics['operations_per_second'], 200)  # Higher throughput expected
        self.assertLess(metrics['avg_response_time'], 100)  # Reasonable response time under load
        self.assertLess(metrics['error_rate'], 0.05)  # Less than 5% error rate
        
        print(f"Concurrent Operations Performance:")
        print(f"  Operations/sec: {metrics['operations_per_second']:.2f}")
        print(f"  Avg response time: {metrics['avg_response_time']:.2f}ms")
        print(f"  P95 response time: {metrics['p95_response_time']:.2f}ms")
        print(f"  Error rate: {metrics['error_rate']:.4f}")
    
    def test_queue_statistics_performance(self):
        """Test performance of queue statistics operations"""
        # Mock queue counts
        for i, queue in enumerate(self.mock_queues.values()):
            queue.count = (i + 1) * 100  # Different counts for each queue
        
        # Mock Redis operations
        self.mock_redis.hgetall.return_value = {
            b'total_processed': b'10000',
            b'total_failed': b'50'
        }
        
        # Start performance tracking
        self.start_performance_tracking()
        
        # Perform multiple statistics operations
        num_operations = 1000
        for i in range(num_operations):
            start_time = time.time()
            
            try:
                stats = self.queue_manager.get_queue_stats()
                
                response_time = (time.time() - start_time) * 1000  # ms
                self.record_operation(response_time=response_time)
                
                # Verify stats structure
                self.assertIn('queues', stats)
                self.assertIn('total_pending', stats)
                
            except Exception as e:
                response_time = (time.time() - start_time) * 1000  # ms
                self.record_operation(response_time=response_time, error=True)
        
        # End performance tracking
        metrics = self.end_performance_tracking()
        
        # Performance assertions
        self.assertGreater(metrics['operations_per_second'], 500)  # Fast read operations
        self.assertLess(metrics['avg_response_time'], 10)  # Very fast response
        self.assertLess(metrics['error_rate'], 0.001)  # Minimal errors
        
        print(f"Queue Statistics Performance:")
        print(f"  Operations/sec: {metrics['operations_per_second']:.2f}")
        print(f"  Avg response time: {metrics['avg_response_time']:.2f}ms")


class TestTaskSerializationPerformance(PerformanceTestBase):
    """Test task serialization performance"""
    
    def setUp(self):
        """Set up serialization performance test fixtures"""
        super().setUp()
        self.serializer_msgpack = TaskSerializer(use_msgpack=True)
        self.serializer_json = TaskSerializer(use_msgpack=False)
    
    def test_serialization_performance_comparison(self):
        """Test performance comparison between msgpack and JSON serialization"""
        # Create test task data with varying complexity
        test_cases = [
            # Simple task
            RQTaskData(
                task_id='simple-task',
                user_id=1,
                platform_connection_id=1,
                priority='normal',
                settings={'max_length': 500},
                created_at=datetime.now(timezone.utc).isoformat()
            ),
            # Complex task
            RQTaskData(
                task_id='complex-task',
                user_id=1,
                platform_connection_id=1,
                priority='high',
                settings={
                    'max_length': 500,
                    'style': 'descriptive',
                    'keywords': ['nature', 'landscape', 'photography'],
                    'nested_config': {
                        'ai_model': 'llava-7b',
                        'temperature': 0.7,
                        'parameters': {
                            'top_p': 0.9,
                            'frequency_penalty': 0.1
                        }
                    },
                    'large_list': list(range(100))
                },
                created_at=datetime.now(timezone.utc).isoformat()
            )
        ]
        
        num_operations = 1000
        
        for test_case_name, task_data in [('Simple', test_cases[0]), ('Complex', test_cases[1])]:
            print(f"\n{test_case_name} Task Serialization Performance:")
            
            # Test msgpack performance
            self.start_performance_tracking()
            
            for i in range(num_operations):
                start_time = time.time()
                
                try:
                    # Serialize
                    serialized = self.serializer_msgpack.serialize_task(task_data)
                    # Deserialize
                    deserialized = self.serializer_msgpack.deserialize_task(serialized)
                    
                    response_time = (time.time() - start_time) * 1000  # ms
                    self.record_operation(response_time=response_time)
                    
                    # Verify data integrity
                    self.assertEqual(deserialized.task_id, task_data.task_id)
                    
                except Exception as e:
                    response_time = (time.time() - start_time) * 1000  # ms
                    self.record_operation(response_time=response_time, error=True)
            
            msgpack_metrics = self.end_performance_tracking()
            
            # Test JSON performance
            self.start_performance_tracking()
            
            for i in range(num_operations):
                start_time = time.time()
                
                try:
                    # Serialize
                    serialized = self.serializer_json.serialize_task(task_data)
                    # Deserialize
                    deserialized = self.serializer_json.deserialize_task(serialized)
                    
                    response_time = (time.time() - start_time) * 1000  # ms
                    self.record_operation(response_time=response_time)
                    
                    # Verify data integrity
                    self.assertEqual(deserialized.task_id, task_data.task_id)
                    
                except Exception as e:
                    response_time = (time.time() - start_time) * 1000  # ms
                    self.record_operation(response_time=response_time, error=True)
            
            json_metrics = self.end_performance_tracking()
            
            # Compare performance
            print(f"  Msgpack - Ops/sec: {msgpack_metrics['operations_per_second']:.2f}, "
                  f"Avg time: {msgpack_metrics['avg_response_time']:.3f}ms")
            print(f"  JSON    - Ops/sec: {json_metrics['operations_per_second']:.2f}, "
                  f"Avg time: {json_metrics['avg_response_time']:.3f}ms")
            
            # Performance assertions
            self.assertGreater(msgpack_metrics['operations_per_second'], 100)
            self.assertGreater(json_metrics['operations_per_second'], 100)
            self.assertLess(msgpack_metrics['error_rate'], 0.001)
            self.assertLess(json_metrics['error_rate'], 0.001)
    
    def test_large_data_serialization_performance(self):
        """Test serialization performance with large data sets"""
        # Create task with large data
        large_settings = {
            'large_array': list(range(10000)),
            'large_dict': {f'key_{i}': f'value_{i}' * 100 for i in range(1000)},
            'nested_structure': {
                'level1': {
                    'level2': {
                        'level3': {
                            'data': [{'id': i, 'content': 'x' * 1000} for i in range(100)]
                        }
                    }
                }
            }
        }
        
        large_task_data = RQTaskData(
            task_id='large-task',
            user_id=1,
            platform_connection_id=1,
            priority='normal',
            settings=large_settings,
            created_at=datetime.now(timezone.utc).isoformat()
        )
        
        # Test serialization performance with large data
        num_operations = 100  # Fewer operations due to large data
        
        self.start_performance_tracking()
        
        for i in range(num_operations):
            start_time = time.time()
            
            try:
                # Serialize
                serialized = self.serializer_msgpack.serialize_task(large_task_data)
                # Deserialize
                deserialized = self.serializer_msgpack.deserialize_task(serialized)
                
                response_time = (time.time() - start_time) * 1000  # ms
                self.record_operation(response_time=response_time)
                
                # Verify data integrity
                self.assertEqual(len(deserialized.settings['large_array']), 10000)
                
            except Exception as e:
                response_time = (time.time() - start_time) * 1000  # ms
                self.record_operation(response_time=response_time, error=True)
        
        metrics = self.end_performance_tracking()
        
        # Performance assertions for large data
        self.assertGreater(metrics['operations_per_second'], 10)  # Lower threshold for large data
        self.assertLess(metrics['avg_response_time'], 500)  # Reasonable time for large data
        self.assertLess(metrics['error_rate'], 0.01)
        
        print(f"Large Data Serialization Performance:")
        print(f"  Operations/sec: {metrics['operations_per_second']:.2f}")
        print(f"  Avg response time: {metrics['avg_response_time']:.2f}ms")
        print(f"  Memory peak: {metrics['memory_peak']:.2f}MB")


class TestWorkerScalingPerformance(PerformanceTestBase):
    """Test worker scaling performance and behavior"""
    
    def setUp(self):
        """Set up worker scaling test fixtures"""
        super().setUp()
        
        self.worker_manager = RQWorkerManager(
            self.mock_db_manager,
            self.mock_redis,
            self.config,
            {}
        )
    
    @patch('app.services.task.rq.rq_worker_manager.IntegratedRQWorker')
    def test_worker_startup_performance(self, mock_integrated_worker_class):
        """Test performance of worker startup operations"""
        # Mock worker instances
        mock_workers = []
        for i in range(20):  # Test scaling up to 20 workers
            mock_worker = Mock()
            mock_worker.start.return_value = None
            mock_workers.append(mock_worker)
        
        mock_integrated_worker_class.side_effect = mock_workers
        
        # Test worker startup performance
        self.start_performance_tracking()
        
        num_workers_to_start = 20
        for i in range(num_workers_to_start):
            start_time = time.time()
            
            try:
                # Scale workers (add one worker)
                result = self.worker_manager.scale_workers('normal', i + 1)
                
                response_time = (time.time() - start_time) * 1000  # ms
                self.record_operation(response_time=response_time)
                
                # Verify scaling succeeded
                self.assertTrue(result)
                
            except Exception as e:
                response_time = (time.time() - start_time) * 1000  # ms
                self.record_operation(response_time=response_time, error=True)
        
        metrics = self.end_performance_tracking()
        
        # Performance assertions
        self.assertGreater(metrics['operations_per_second'], 5)  # Worker startup is slower
        self.assertLess(metrics['avg_response_time'], 1000)  # Less than 1 second per worker
        self.assertLess(metrics['error_rate'], 0.05)
        
        print(f"Worker Startup Performance:")
        print(f"  Workers/sec: {metrics['operations_per_second']:.2f}")
        print(f"  Avg startup time: {metrics['avg_response_time']:.2f}ms")
    
    def test_worker_health_check_performance(self):
        """Test performance of worker health checking"""
        # Mock multiple workers
        num_workers = 50
        mock_workers = []
        
        for i in range(num_workers):
            mock_worker = Mock()
            mock_worker.is_healthy.return_value = i % 10 != 0  # 10% unhealthy
            mock_worker.get_health_status.return_value = {
                'status': 'healthy' if i % 10 != 0 else 'unhealthy',
                'memory_usage': 100 + i,
                'active_jobs': i % 5
            }
            mock_workers.append(mock_worker)
        
        # Add workers to manager
        for i, worker in enumerate(mock_workers):
            self.worker_manager.integrated_workers.append({
                'worker': worker,
                'worker_id': f'health-test-worker-{i}',
                'health_check_enabled': True
            })
        
        # Test health check performance
        self.start_performance_tracking()
        
        num_health_checks = 100
        for i in range(num_health_checks):
            start_time = time.time()
            
            try:
                health_report = self.worker_manager.check_worker_health()
                
                response_time = (time.time() - start_time) * 1000  # ms
                self.record_operation(response_time=response_time)
                
                # Verify health report structure
                self.assertIn('healthy_workers', health_report)
                self.assertIn('unhealthy_workers', health_report)
                
            except Exception as e:
                response_time = (time.time() - start_time) * 1000  # ms
                self.record_operation(response_time=response_time, error=True)
        
        metrics = self.end_performance_tracking()
        
        # Performance assertions
        self.assertGreater(metrics['operations_per_second'], 50)  # Fast health checks
        self.assertLess(metrics['avg_response_time'], 100)  # Quick health assessment
        self.assertLess(metrics['error_rate'], 0.01)
        
        print(f"Worker Health Check Performance:")
        print(f"  Checks/sec: {metrics['operations_per_second']:.2f}")
        print(f"  Avg check time: {metrics['avg_response_time']:.2f}ms")


class TestMemoryUsageAndResourceUtilization(PerformanceTestBase):
    """Test memory usage and resource utilization under load"""
    
    def setUp(self):
        """Set up memory usage test fixtures"""
        super().setUp()
        
        # Force garbage collection before tests
        gc.collect()
        
        # Initialize components
        self.serializer = TaskSerializer(use_msgpack=True)
        
        with patch('app.services.task.rq.rq_queue_manager.RedisConnectionManager'):
            with patch('app.services.task.rq.rq_queue_manager.Queue') as mock_queue_class:
                mock_queues = {}
                for priority in ['urgent', 'high', 'normal', 'low']:
                    mock_queue = Mock(spec=Queue)
                    mock_queue.name = priority
                    mock_queues[priority] = mock_queue
                
                mock_queue_class.side_effect = lambda name, **kwargs: mock_queues[name]
                
                self.queue_manager = RQQueueManager(
                    self.mock_db_manager,
                    self.config,
                    self.mock_security_manager
                )
                self.queue_manager.redis_connection = self.mock_redis
                self.queue_manager.queues = mock_queues
    
    def test_memory_usage_under_load(self):
        """Test memory usage during high-load operations"""
        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create many task objects
        num_tasks = 10000
        tasks = []
        
        print(f"Initial memory usage: {initial_memory:.2f}MB")
        
        # Create tasks and measure memory growth
        for i in range(num_tasks):
            task_data = RQTaskData(
                task_id=f'memory-test-task-{i}',
                user_id=i % 100,  # 100 different users
                platform_connection_id=1,
                priority='normal',
                settings={
                    'max_length': 500,
                    'data': list(range(i % 50)),  # Variable size data
                    'metadata': {'index': i, 'batch': i // 100}
                },
                created_at=datetime.now(timezone.utc).isoformat()
            )
            tasks.append(task_data)
            
            # Measure memory every 1000 tasks
            if (i + 1) % 1000 == 0:
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_growth = current_memory - initial_memory
                print(f"After {i + 1} tasks: {current_memory:.2f}MB (+{memory_growth:.2f}MB)")
        
        # Measure memory after creating all tasks
        peak_memory = process.memory_info().rss / 1024 / 1024
        peak_growth = peak_memory - initial_memory
        
        # Perform serialization operations
        serialization_start_memory = peak_memory
        
        for i in range(0, len(tasks), 100):  # Serialize every 100th task
            task = tasks[i]
            serialized = self.serializer.serialize_task(task)
            deserialized = self.serializer.deserialize_task(serialized)
            
            # Verify data integrity
            self.assertEqual(deserialized.task_id, task.task_id)
        
        # Measure memory after serialization
        serialization_end_memory = process.memory_info().rss / 1024 / 1024
        serialization_growth = serialization_end_memory - serialization_start_memory
        
        # Clean up tasks and force garbage collection
        del tasks
        gc.collect()
        
        # Measure memory after cleanup
        final_memory = process.memory_info().rss / 1024 / 1024
        cleanup_reduction = peak_memory - final_memory
        
        print(f"Peak memory usage: {peak_memory:.2f}MB (+{peak_growth:.2f}MB)")
        print(f"Serialization memory growth: {serialization_growth:.2f}MB")
        print(f"Memory after cleanup: {final_memory:.2f}MB (-{cleanup_reduction:.2f}MB)")
        
        # Memory usage assertions
        self.assertLess(peak_growth, 500)  # Less than 500MB growth for 10k tasks
        self.assertLess(serialization_growth, 100)  # Serialization shouldn't use too much memory
        self.assertGreater(cleanup_reduction, peak_growth * 0.5)  # At least 50% memory recovered
    
    def test_memory_leak_detection(self):
        """Test for memory leaks in repeated operations"""
        process = psutil.Process()
        
        # Baseline memory measurement
        gc.collect()
        baseline_memory = process.memory_info().rss / 1024 / 1024
        
        memory_measurements = [baseline_memory]
        
        # Perform repeated operations
        num_cycles = 10
        operations_per_cycle = 1000
        
        for cycle in range(num_cycles):
            # Create and process tasks
            for i in range(operations_per_cycle):
                task_data = RQTaskData(
                    task_id=f'leak-test-{cycle}-{i}',
                    user_id=i,
                    platform_connection_id=1,
                    priority='normal',
                    settings={'data': list(range(100))},
                    created_at=datetime.now(timezone.utc).isoformat()
                )
                
                # Serialize and deserialize
                serialized = self.serializer.serialize_task(task_data)
                deserialized = self.serializer.deserialize_task(serialized)
                
                # Simulate task processing
                del task_data, serialized, deserialized
            
            # Force garbage collection
            gc.collect()
            
            # Measure memory
            current_memory = process.memory_info().rss / 1024 / 1024
            memory_measurements.append(current_memory)
            
            print(f"Cycle {cycle + 1}: {current_memory:.2f}MB")
        
        # Analyze memory trend
        memory_growth_per_cycle = []
        for i in range(1, len(memory_measurements)):
            growth = memory_measurements[i] - memory_measurements[i-1]
            memory_growth_per_cycle.append(growth)
        
        avg_growth_per_cycle = statistics.mean(memory_growth_per_cycle)
        max_growth_per_cycle = max(memory_growth_per_cycle)
        
        print(f"Average memory growth per cycle: {avg_growth_per_cycle:.2f}MB")
        print(f"Maximum memory growth per cycle: {max_growth_per_cycle:.2f}MB")
        
        # Memory leak assertions
        self.assertLess(avg_growth_per_cycle, 5)  # Less than 5MB average growth per cycle
        self.assertLess(max_growth_per_cycle, 20)  # Less than 20MB max growth per cycle
        
        # Total memory growth should be reasonable
        total_growth = memory_measurements[-1] - memory_measurements[0]
        self.assertLess(total_growth, 50)  # Less than 50MB total growth
    
    def test_resource_utilization_monitoring(self):
        """Test resource utilization monitoring"""
        process = psutil.Process()
        
        # Monitor CPU and memory during intensive operations
        cpu_measurements = []
        memory_measurements = []
        
        # Perform CPU-intensive operations
        start_time = time.time()
        
        while time.time() - start_time < 10:  # Run for 10 seconds
            # CPU-intensive task simulation
            for i in range(1000):
                task_data = RQTaskData(
                    task_id=f'cpu-test-{i}',
                    user_id=i,
                    platform_connection_id=1,
                    priority='normal',
                    settings={'data': [j**2 for j in range(100)]},  # CPU work
                    created_at=datetime.now(timezone.utc).isoformat()
                )
                
                serialized = self.serializer.serialize_task(task_data)
                deserialized = self.serializer.deserialize_task(serialized)
            
            # Measure resources
            cpu_percent = process.cpu_percent()
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            cpu_measurements.append(cpu_percent)
            memory_measurements.append(memory_mb)
            
            time.sleep(0.1)  # Small delay for measurements
        
        # Analyze resource utilization
        avg_cpu = statistics.mean(cpu_measurements)
        max_cpu = max(cpu_measurements)
        avg_memory = statistics.mean(memory_measurements)
        max_memory = max(memory_measurements)
        
        print(f"Resource Utilization:")
        print(f"  Average CPU: {avg_cpu:.2f}%")
        print(f"  Peak CPU: {max_cpu:.2f}%")
        print(f"  Average Memory: {avg_memory:.2f}MB")
        print(f"  Peak Memory: {max_memory:.2f}MB")
        
        # Resource utilization assertions
        self.assertLess(avg_cpu, 80)  # Should not consistently max out CPU
        self.assertLess(max_memory - min(memory_measurements), 100)  # Memory growth should be controlled


if __name__ == '__main__':
    # Run performance tests with detailed output
    unittest.main(verbosity=2)
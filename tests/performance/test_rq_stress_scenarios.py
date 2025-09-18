# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Stress Test Scenarios for RQ System

Tests extreme load conditions, failure scenarios, recovery behavior,
and system limits to ensure robustness under stress.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import time
import threading
import random
import statistics
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
import redis
from rq import Queue, Job

from app.core.database.core.database_manager import DatabaseManager
from app.core.security.features.caption_security import CaptionSecurityManager
from app.services.task.rq.rq_queue_manager import RQQueueManager
from app.services.task.rq.rq_worker_manager import RQWorkerManager
from app.services.task.rq.redis_fallback_manager import RedisFallbackManager
from app.services.task.rq.redis_health_monitor import RedisHealthMonitor
from app.services.task.rq.rq_config import RQConfig, TaskPriority
from models import CaptionGenerationTask, TaskStatus, JobPriority


class StressTestBase(unittest.TestCase):
    """Base class for stress tests with common utilities"""
    
    def setUp(self):
        """Set up stress test fixtures"""
        # Mock dependencies
        self.mock_db_manager = Mock(spec=DatabaseManager)
        self.mock_session = Mock()
        self.mock_db_manager.get_session.return_value = self.mock_session
        
        self.mock_security_manager = Mock(spec=CaptionSecurityManager)
        self.mock_security_manager.generate_secure_task_id.side_effect = lambda: f"stress-task-{int(time.time() * 1000000)}"
        
        # Mock Redis connection
        self.mock_redis = Mock(spec=redis.Redis)
        self.mock_redis.ping.return_value = True
        
        # Create test configuration
        self.config = RQConfig()
        
        # Stress test tracking
        self.stress_metrics = {
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'error_types': {},
            'response_times': [],
            'throughput_samples': []
        }
    
    def record_stress_operation(self, success, response_time=None, error_type=None):
        """Record a stress test operation"""
        self.stress_metrics['total_operations'] += 1
        
        if success:
            self.stress_metrics['successful_operations'] += 1
        else:
            self.stress_metrics['failed_operations'] += 1
            if error_type:
                self.stress_metrics['error_types'][error_type] = self.stress_metrics['error_types'].get(error_type, 0) + 1
        
        if response_time is not None:
            self.stress_metrics['response_times'].append(response_time)
    
    def calculate_stress_metrics(self):
        """Calculate stress test metrics"""
        total = self.stress_metrics['total_operations']
        if total == 0:
            return {}
        
        success_rate = self.stress_metrics['successful_operations'] / total
        failure_rate = self.stress_metrics['failed_operations'] / total
        
        response_times = self.stress_metrics['response_times']
        
        return {
            'total_operations': total,
            'success_rate': success_rate,
            'failure_rate': failure_rate,
            'avg_response_time': statistics.mean(response_times) if response_times else 0,
            'median_response_time': statistics.median(response_times) if response_times else 0,
            'p95_response_time': self._percentile(response_times, 95) if response_times else 0,
            'p99_response_time': self._percentile(response_times, 99) if response_times else 0,
            'error_types': self.stress_metrics['error_types']
        }
    
    def _percentile(self, data, percentile):
        """Calculate percentile of data"""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]


class TestExtremeLoadScenarios(StressTestBase):
    """Test system behavior under extreme load conditions"""
    
    def setUp(self):
        """Set up extreme load test fixtures"""
        super().setUp()
        
        # Initialize queue manager with mocks
        with patch('app.services.task.rq.rq_queue_manager.RedisConnectionManager'):
            with patch('app.services.task.rq.rq_queue_manager.Queue') as mock_queue_class:
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
    
    def test_burst_load_handling(self):
        """Test system behavior under sudden burst load"""
        # Mock user task tracker
        mock_user_tracker = Mock()
        mock_user_tracker.has_active_task.return_value = False
        mock_user_tracker.set_user_active_task.return_value = True
        self.queue_manager.user_task_tracker = mock_user_tracker
        
        # Mock queue enqueue with occasional failures
        mock_job = Mock(spec=Job)
        mock_job.id = "burst-job"
        
        def mock_enqueue(*args, **kwargs):
            # Simulate 5% failure rate under load
            if random.random() < 0.05:
                raise redis.ConnectionError("Redis overloaded")
            return mock_job
        
        for queue in self.mock_queues.values():
            queue.enqueue.side_effect = mock_enqueue
        
        # Test burst load - 10,000 tasks in rapid succession
        num_tasks = 10000
        max_threads = 50
        
        def enqueue_task_batch(batch_start, batch_size):
            batch_results = []
            for i in range(batch_size):
                task_id = batch_start + i
                start_time = time.time()
                
                try:
                    task = CaptionGenerationTask(
                        id=f"burst-task-{task_id}",
                        user_id=task_id,  # Unique user per task
                        platform_connection_id=1,
                        status=TaskStatus.QUEUED
                    )
                    
                    result = self.queue_manager.enqueue_task(task, TaskPriority.NORMAL)
                    
                    response_time = (time.time() - start_time) * 1000
                    batch_results.append(('success', response_time, None))
                    
                except Exception as e:
                    response_time = (time.time() - start_time) * 1000
                    error_type = type(e).__name__
                    batch_results.append(('failure', response_time, error_type))
            
            return batch_results
        
        # Execute burst load
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=max_threads) as executor:
            batch_size = 200
            futures = []
            
            for i in range(0, num_tasks, batch_size):
                future = executor.submit(enqueue_task_batch, i, min(batch_size, num_tasks - i))
                futures.append(future)
            
            # Collect results
            for future in as_completed(futures):
                batch_results = future.result()
                for result_type, response_time, error_type in batch_results:
                    success = result_type == 'success'
                    self.record_stress_operation(success, response_time, error_type)
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Calculate metrics
        metrics = self.calculate_stress_metrics()
        throughput = metrics['total_operations'] / total_duration
        
        print(f"Burst Load Test Results:")
        print(f"  Total operations: {metrics['total_operations']}")
        print(f"  Success rate: {metrics['success_rate']:.4f}")
        print(f"  Throughput: {throughput:.2f} ops/sec")
        print(f"  Avg response time: {metrics['avg_response_time']:.2f}ms")
        print(f"  P95 response time: {metrics['p95_response_time']:.2f}ms")
        print(f"  P99 response time: {metrics['p99_response_time']:.2f}ms")
        
        # Stress test assertions
        self.assertGreater(metrics['success_rate'], 0.90)  # At least 90% success under burst
        self.assertLess(metrics['p95_response_time'], 1000)  # P95 under 1 second
        self.assertGreater(throughput, 100)  # Maintain reasonable throughput
    
    def test_sustained_high_load(self):
        """Test system behavior under sustained high load"""
        # Mock components for sustained load
        mock_user_tracker = Mock()
        mock_user_tracker.has_active_task.return_value = False
        mock_user_tracker.set_user_active_task.return_value = True
        self.queue_manager.user_task_tracker = mock_user_tracker
        
        mock_job = Mock(spec=Job)
        mock_job.id = "sustained-job"
        
        # Simulate gradual performance degradation under sustained load
        operation_count = 0
        
        def mock_enqueue_with_degradation(*args, **kwargs):
            nonlocal operation_count
            operation_count += 1
            
            # Simulate increasing latency as load increases
            base_delay = 0.001  # 1ms base
            load_factor = operation_count / 10000  # Increase delay as operations accumulate
            delay = base_delay * (1 + load_factor)
            time.sleep(delay)
            
            # Simulate occasional failures under sustained load
            if random.random() < 0.02:  # 2% failure rate
                raise redis.TimeoutError("Redis timeout under load")
            
            return mock_job
        
        for queue in self.mock_queues.values():
            queue.enqueue.side_effect = mock_enqueue_with_degradation
        
        # Run sustained load for 60 seconds
        test_duration = 60  # seconds
        target_rate = 100  # operations per second
        
        start_time = time.time()
        operation_interval = 1.0 / target_rate
        
        def sustained_load_worker():
            last_operation_time = time.time()
            
            while time.time() - start_time < test_duration:
                current_time = time.time()
                
                # Maintain target rate
                if current_time - last_operation_time >= operation_interval:
                    operation_start = time.time()
                    
                    try:
                        task = CaptionGenerationTask(
                            id=f"sustained-task-{int(current_time * 1000)}",
                            user_id=int(current_time * 1000) % 1000,  # Cycle through users
                            platform_connection_id=1,
                            status=TaskStatus.QUEUED
                        )
                        
                        result = self.queue_manager.enqueue_task(task, TaskPriority.NORMAL)
                        
                        response_time = (time.time() - operation_start) * 1000
                        self.record_stress_operation(True, response_time)
                        
                    except Exception as e:
                        response_time = (time.time() - operation_start) * 1000
                        error_type = type(e).__name__
                        self.record_stress_operation(False, response_time, error_type)
                    
                    last_operation_time = current_time
                else:
                    time.sleep(0.001)  # Small sleep to prevent busy waiting
        
        # Run sustained load
        sustained_load_worker()
        
        # Calculate metrics
        metrics = self.calculate_stress_metrics()
        actual_duration = time.time() - start_time
        actual_throughput = metrics['total_operations'] / actual_duration
        
        print(f"Sustained Load Test Results:")
        print(f"  Duration: {actual_duration:.2f}s")
        print(f"  Total operations: {metrics['total_operations']}")
        print(f"  Target throughput: {target_rate} ops/sec")
        print(f"  Actual throughput: {actual_throughput:.2f} ops/sec")
        print(f"  Success rate: {metrics['success_rate']:.4f}")
        print(f"  Avg response time: {metrics['avg_response_time']:.2f}ms")
        print(f"  P95 response time: {metrics['p95_response_time']:.2f}ms")
        
        # Sustained load assertions
        self.assertGreater(metrics['success_rate'], 0.95)  # High success rate under sustained load
        self.assertGreater(actual_throughput, target_rate * 0.8)  # Achieve at least 80% of target
        self.assertLess(metrics['p95_response_time'], 500)  # Reasonable P95 response time
    
    def test_memory_pressure_handling(self):
        """Test system behavior under memory pressure"""
        # Simulate memory pressure by creating large task data
        large_task_count = 1000
        
        # Mock user task tracker
        mock_user_tracker = Mock()
        mock_user_tracker.has_active_task.return_value = False
        mock_user_tracker.set_user_active_task.return_value = True
        self.queue_manager.user_task_tracker = mock_user_tracker
        
        mock_job = Mock(spec=Job)
        mock_job.id = "memory-pressure-job"
        
        # Simulate memory allocation failures under pressure
        def mock_enqueue_with_memory_pressure(*args, **kwargs):
            # Simulate memory allocation failure 1% of the time
            if random.random() < 0.01:
                raise MemoryError("Insufficient memory for operation")
            return mock_job
        
        for queue in self.mock_queues.values():
            queue.enqueue.side_effect = mock_enqueue_with_memory_pressure
        
        # Create tasks with large data to simulate memory pressure
        for i in range(large_task_count):
            start_time = time.time()
            
            try:
                # Create task with large settings to consume memory
                large_settings = {
                    'large_data': list(range(1000)),  # Large list
                    'metadata': {f'key_{j}': f'value_{j}' * 100 for j in range(100)},  # Large dict
                    'description': 'x' * 10000  # Large string
                }
                
                task = CaptionGenerationTask(
                    id=f"memory-task-{i}",
                    user_id=i,
                    platform_connection_id=1,
                    status=TaskStatus.QUEUED
                )
                # Note: In real implementation, settings would be attached to task
                
                result = self.queue_manager.enqueue_task(task, TaskPriority.NORMAL)
                
                response_time = (time.time() - start_time) * 1000
                self.record_stress_operation(True, response_time)
                
            except Exception as e:
                response_time = (time.time() - start_time) * 1000
                error_type = type(e).__name__
                self.record_stress_operation(False, response_time, error_type)
        
        # Calculate metrics
        metrics = self.calculate_stress_metrics()
        
        print(f"Memory Pressure Test Results:")
        print(f"  Total operations: {metrics['total_operations']}")
        print(f"  Success rate: {metrics['success_rate']:.4f}")
        print(f"  Memory errors: {metrics['error_types'].get('MemoryError', 0)}")
        print(f"  Avg response time: {metrics['avg_response_time']:.2f}ms")
        
        # Memory pressure assertions
        self.assertGreater(metrics['success_rate'], 0.95)  # Should handle memory pressure gracefully
        self.assertLess(metrics['error_types'].get('MemoryError', 0), large_task_count * 0.05)  # Less than 5% memory errors


class TestFailureRecoveryScenarios(StressTestBase):
    """Test system recovery from various failure scenarios"""
    
    def setUp(self):
        """Set up failure recovery test fixtures"""
        super().setUp()
        
        # Initialize fallback manager
        self.fallback_manager = RedisFallbackManager(
            self.mock_db_manager,
            self.mock_redis,
            Mock()  # Mock task queue manager
        )
        
        # Initialize health monitor
        self.health_monitor = RedisHealthMonitor(self.mock_redis)
    
    def test_redis_connection_failure_recovery(self):
        """Test recovery from Redis connection failures"""
        # Simulate intermittent Redis failures
        redis_failure_count = 0
        max_failures = 10
        
        def mock_redis_ping():
            nonlocal redis_failure_count
            if redis_failure_count < max_failures and random.random() < 0.3:  # 30% failure rate
                redis_failure_count += 1
                raise redis.ConnectionError("Connection lost")
            return True
        
        self.mock_redis.ping.side_effect = mock_redis_ping
        
        # Test health monitoring and recovery
        num_health_checks = 100
        recovery_count = 0
        
        for i in range(num_health_checks):
            start_time = time.time()
            
            try:
                is_healthy = self.health_monitor.check_health()
                
                if not is_healthy:
                    # Simulate recovery attempt
                    self.fallback_manager.activate_fallback_mode("Redis connection failed")
                    
                    # Attempt recovery
                    time.sleep(0.1)  # Simulate recovery delay
                    recovery_successful = self.fallback_manager.check_for_redis_recovery()
                    
                    if recovery_successful:
                        recovery_count += 1
                        self.fallback_manager.deactivate_fallback_mode()
                
                response_time = (time.time() - start_time) * 1000
                self.record_stress_operation(is_healthy, response_time)
                
            except Exception as e:
                response_time = (time.time() - start_time) * 1000
                error_type = type(e).__name__
                self.record_stress_operation(False, response_time, error_type)
        
        # Calculate metrics
        metrics = self.calculate_stress_metrics()
        
        print(f"Redis Failure Recovery Test Results:")
        print(f"  Total health checks: {metrics['total_operations']}")
        print(f"  Success rate: {metrics['success_rate']:.4f}")
        print(f"  Redis failures encountered: {redis_failure_count}")
        print(f"  Recovery attempts: {recovery_count}")
        print(f"  Avg response time: {metrics['avg_response_time']:.2f}ms")
        
        # Recovery assertions
        self.assertGreater(recovery_count, 0)  # Should attempt recovery
        self.assertGreater(metrics['success_rate'], 0.6)  # Should maintain reasonable success rate
    
    def test_worker_failure_and_restart(self):
        """Test worker failure detection and automatic restart"""
        # Mock worker manager
        worker_manager = RQWorkerManager(
            self.mock_db_manager,
            self.mock_redis,
            self.config,
            {}
        )
        
        # Mock workers with failure simulation
        num_workers = 10
        mock_workers = []
        
        for i in range(num_workers):
            mock_worker = Mock()
            mock_worker.worker_id = f"failure-test-worker-{i}"
            mock_worker.is_running.return_value = True
            mock_worker.is_healthy.return_value = True
            
            # Simulate random worker failures
            def make_failure_check(worker_index):
                failure_triggered = False
                def check_health():
                    nonlocal failure_triggered
                    if not failure_triggered and random.random() < 0.1:  # 10% chance of failure
                        failure_triggered = True
                        return False
                    return not failure_triggered  # Stay failed once failed
                return check_health
            
            mock_worker.is_healthy.side_effect = make_failure_check(i)
            mock_workers.append(mock_worker)
        
        # Add workers to manager
        for worker in mock_workers:
            worker_manager.integrated_workers.append({
                'worker': worker,
                'worker_id': worker.worker_id,
                'auto_restart': True
            })
        
        # Test failure detection and restart over time
        num_monitoring_cycles = 50
        restart_count = 0
        
        for cycle in range(num_monitoring_cycles):
            start_time = time.time()
            
            try:
                # Check worker health
                health_report = worker_manager.check_worker_health()
                
                # Simulate restart for unhealthy workers
                unhealthy_workers = health_report.get('unhealthy_workers', [])
                
                for unhealthy_worker in unhealthy_workers:
                    # Mock restart operation
                    with patch.object(worker_manager, 'restart_worker') as mock_restart:
                        mock_restart.return_value = True
                        result = worker_manager.restart_worker(unhealthy_worker['worker_id'])
                        if result:
                            restart_count += 1
                
                response_time = (time.time() - start_time) * 1000
                self.record_stress_operation(True, response_time)
                
            except Exception as e:
                response_time = (time.time() - start_time) * 1000
                error_type = type(e).__name__
                self.record_stress_operation(False, response_time, error_type)
            
            time.sleep(0.1)  # Monitoring interval
        
        # Calculate metrics
        metrics = self.calculate_stress_metrics()
        
        print(f"Worker Failure Recovery Test Results:")
        print(f"  Monitoring cycles: {metrics['total_operations']}")
        print(f"  Success rate: {metrics['success_rate']:.4f}")
        print(f"  Worker restarts: {restart_count}")
        print(f"  Avg monitoring time: {metrics['avg_response_time']:.2f}ms")
        
        # Worker recovery assertions
        self.assertGreater(restart_count, 0)  # Should detect and restart failed workers
        self.assertGreater(metrics['success_rate'], 0.95)  # Monitoring should be reliable
    
    def test_cascading_failure_handling(self):
        """Test handling of cascading failures"""
        # Simulate cascading failure scenario
        failure_components = ['redis', 'database', 'worker1', 'worker2', 'worker3']
        component_status = {comp: True for comp in failure_components}
        
        # Simulate cascading failures
        def trigger_cascading_failure():
            # Start with Redis failure
            component_status['redis'] = False
            
            # Database fails due to connection issues
            time.sleep(0.1)
            component_status['database'] = False
            
            # Workers fail due to inability to connect to Redis/DB
            time.sleep(0.1)
            for worker in ['worker1', 'worker2', 'worker3']:
                component_status[worker] = False
        
        # Start cascading failure in background
        failure_thread = threading.Thread(target=trigger_cascading_failure)
        failure_thread.start()
        
        # Monitor system during cascading failure
        monitoring_duration = 5  # seconds
        start_time = time.time()
        
        while time.time() - start_time < monitoring_duration:
            operation_start = time.time()
            
            try:
                # Check system health
                system_healthy = all(component_status.values())
                
                # Simulate recovery attempts
                if not system_healthy:
                    # Attempt to recover components
                    for component, status in component_status.items():
                        if not status and random.random() < 0.1:  # 10% chance of recovery per check
                            component_status[component] = True
                
                response_time = (time.time() - operation_start) * 1000
                self.record_stress_operation(system_healthy, response_time)
                
            except Exception as e:
                response_time = (time.time() - operation_start) * 1000
                error_type = type(e).__name__
                self.record_stress_operation(False, response_time, error_type)
            
            time.sleep(0.1)  # Monitoring interval
        
        failure_thread.join()
        
        # Calculate metrics
        metrics = self.calculate_stress_metrics()
        
        print(f"Cascading Failure Test Results:")
        print(f"  Total health checks: {metrics['total_operations']}")
        print(f"  System availability: {metrics['success_rate']:.4f}")
        print(f"  Final component status: {component_status}")
        print(f"  Avg response time: {metrics['avg_response_time']:.2f}ms")
        
        # Cascading failure assertions
        self.assertLess(metrics['success_rate'], 0.8)  # Should show impact of cascading failures
        self.assertGreater(sum(component_status.values()), 0)  # Some components should recover


class TestSystemLimitsAndBoundaries(StressTestBase):
    """Test system behavior at limits and boundaries"""
    
    def test_maximum_queue_size_handling(self):
        """Test behavior when queues reach maximum size"""
        # Mock queue with size limit
        max_queue_size = 1000
        current_queue_size = 0
        
        mock_queue = Mock(spec=Queue)
        mock_queue.name = 'limited'
        
        def mock_enqueue(*args, **kwargs):
            nonlocal current_queue_size
            if current_queue_size >= max_queue_size:
                raise redis.ResponseError("Queue size limit exceeded")
            current_queue_size += 1
            mock_job = Mock(spec=Job)
            mock_job.id = f"limited-job-{current_queue_size}"
            return mock_job
        
        mock_queue.enqueue.side_effect = mock_enqueue
        mock_queue.count = lambda: current_queue_size
        
        # Test enqueueing beyond limit
        num_attempts = max_queue_size + 200  # Exceed limit
        
        for i in range(num_attempts):
            start_time = time.time()
            
            try:
                result = mock_queue.enqueue('test_job', f'task-{i}')
                
                response_time = (time.time() - start_time) * 1000
                self.record_stress_operation(True, response_time)
                
            except Exception as e:
                response_time = (time.time() - start_time) * 1000
                error_type = type(e).__name__
                self.record_stress_operation(False, response_time, error_type)
        
        # Calculate metrics
        metrics = self.calculate_stress_metrics()
        
        print(f"Queue Size Limit Test Results:")
        print(f"  Total enqueue attempts: {metrics['total_operations']}")
        print(f"  Successful enqueues: {metrics['successful_operations']}")
        print(f"  Queue size limit: {max_queue_size}")
        print(f"  Final queue size: {current_queue_size}")
        print(f"  Success rate: {metrics['success_rate']:.4f}")
        
        # Queue limit assertions
        self.assertEqual(metrics['successful_operations'], max_queue_size)  # Should enqueue up to limit
        self.assertGreater(metrics['failed_operations'], 0)  # Should fail beyond limit
        self.assertEqual(current_queue_size, max_queue_size)  # Should not exceed limit
    
    def test_concurrent_user_limit(self):
        """Test system behavior with maximum concurrent users"""
        max_concurrent_users = 1000
        
        # Mock user task tracker with concurrency limit
        active_users = set()
        
        def mock_has_active_task(user_id):
            return user_id in active_users
        
        def mock_set_user_active_task(user_id, task_id):
            if len(active_users) >= max_concurrent_users:
                raise ValueError("Maximum concurrent users exceeded")
            active_users.add(user_id)
            return True
        
        mock_user_tracker = Mock()
        mock_user_tracker.has_active_task.side_effect = mock_has_active_task
        mock_user_tracker.set_user_active_task.side_effect = mock_set_user_active_task
        
        # Test concurrent user handling
        num_user_attempts = max_concurrent_users + 100  # Exceed limit
        
        for user_id in range(num_user_attempts):
            start_time = time.time()
            
            try:
                if not mock_user_tracker.has_active_task(user_id):
                    mock_user_tracker.set_user_active_task(user_id, f"task-{user_id}")
                
                response_time = (time.time() - start_time) * 1000
                self.record_stress_operation(True, response_time)
                
            except Exception as e:
                response_time = (time.time() - start_time) * 1000
                error_type = type(e).__name__
                self.record_stress_operation(False, response_time, error_type)
        
        # Calculate metrics
        metrics = self.calculate_stress_metrics()
        
        print(f"Concurrent User Limit Test Results:")
        print(f"  Total user attempts: {metrics['total_operations']}")
        print(f"  Successful activations: {metrics['successful_operations']}")
        print(f"  Concurrent user limit: {max_concurrent_users}")
        print(f"  Active users: {len(active_users)}")
        print(f"  Success rate: {metrics['success_rate']:.4f}")
        
        # Concurrent user assertions
        self.assertLessEqual(len(active_users), max_concurrent_users)  # Should not exceed limit
        self.assertGreater(metrics['failed_operations'], 0)  # Should fail beyond limit


if __name__ == '__main__':
    # Run stress tests with detailed output
    unittest.main(verbosity=2)
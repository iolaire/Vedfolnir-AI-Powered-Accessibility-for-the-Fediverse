# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for RQ Queue Manager

Tests the core RQ queue management functionality including task enqueuing,
priority handling, user task enforcement, and Redis health monitoring.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, call
import redis
from rq import Queue, Job
from datetime import datetime, timezone
import threading
import time

from app.core.database.core.database_manager import DatabaseManager
from app.core.security.features.caption_security import CaptionSecurityManager
from app.services.task.rq.rq_queue_manager import RQQueueManager
from app.services.task.rq.rq_config import RQConfig, TaskPriority, QueueConfig
from app.services.task.rq.redis_connection_manager import RedisConnectionManager
from app.services.task.rq.user_task_tracker import UserTaskTracker
from app.services.task.rq.redis_health_monitor import RedisHealthMonitor
from models import CaptionGenerationTask, TaskStatus, JobPriority, User, UserRole


class TestRQQueueManager(unittest.TestCase):
    """Test RQ Queue Manager functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock dependencies
        self.mock_db_manager = Mock(spec=DatabaseManager)
        self.mock_session = Mock()
        self.mock_db_manager.get_session.return_value = self.mock_session
        
        self.mock_security_manager = Mock(spec=CaptionSecurityManager)
        self.mock_security_manager.generate_secure_task_id.return_value = "test-task-123"
        
        # Create test configuration
        self.config = RQConfig()
        
        # Mock Redis connection
        self.mock_redis = Mock(spec=redis.Redis)
        self.mock_redis.ping.return_value = True
        
        # Mock Redis connection manager
        self.mock_redis_manager = Mock(spec=RedisConnectionManager)
        self.mock_redis_manager.initialize.return_value = True
        self.mock_redis_manager.get_connection.return_value = self.mock_redis
        
        # Initialize queue manager with mocked dependencies
        with patch('app.services.task.rq.rq_queue_manager.RedisConnectionManager') as mock_redis_manager_class:
            mock_redis_manager_class.return_value = self.mock_redis_manager
            
            with patch('app.services.task.rq.rq_queue_manager.Queue') as mock_queue_class:
                self.mock_queues = {}
                for priority in ['urgent', 'high', 'normal', 'low']:
                    mock_queue = Mock(spec=Queue)
                    mock_queue.name = priority
                    self.mock_queues[priority] = mock_queue
                
                mock_queue_class.side_effect = lambda name, **kwargs: self.mock_queues[name]
                
                self.queue_manager = RQQueueManager(
                    self.mock_db_manager,
                    self.config,
                    self.mock_security_manager
                )
                
                # Set up the mocked components
                self.queue_manager.redis_connection = self.mock_redis
                self.queue_manager.queues = self.mock_queues
                self.queue_manager._redis_available = True
                self.queue_manager._fallback_mode = False
    
    def test_initialization_success(self):
        """Test successful initialization of RQ Queue Manager"""
        # Verify initialization completed successfully
        self.assertTrue(self.queue_manager._redis_available)
        self.assertFalse(self.queue_manager._fallback_mode)
        self.assertEqual(self.queue_manager.redis_connection, self.mock_redis)
        self.assertEqual(len(self.queue_manager.queues), 4)  # urgent, high, normal, low
    
    def test_initialization_redis_failure(self):
        """Test initialization with Redis failure"""
        # Mock Redis connection failure
        mock_redis_manager = Mock(spec=RedisConnectionManager)
        mock_redis_manager.initialize.return_value = False
        
        with patch('app.services.task.rq.rq_queue_manager.RedisConnectionManager') as mock_redis_manager_class:
            mock_redis_manager_class.return_value = mock_redis_manager
            
            queue_manager = RQQueueManager(
                self.mock_db_manager,
                self.config,
                self.mock_security_manager
            )
            
            # Verify fallback mode is activated
            self.assertFalse(queue_manager._redis_available)
            self.assertTrue(queue_manager._fallback_mode)
    
    def test_enqueue_task_success(self):
        """Test successful task enqueuing"""
        # Create test task
        task = CaptionGenerationTask(
            id="test-task-123",
            user_id=1,
            platform_connection_id=1,
            status=TaskStatus.QUEUED
        )
        
        # Mock user task tracker
        mock_user_tracker = Mock(spec=UserTaskTracker)
        mock_user_tracker.has_active_task.return_value = False
        mock_user_tracker.set_user_active_task.return_value = True
        self.queue_manager.user_task_tracker = mock_user_tracker
        
        # Mock queue enqueue
        mock_job = Mock(spec=Job)
        mock_job.id = "rq-job-123"
        self.mock_queues['normal'].enqueue.return_value = mock_job
        
        # Test enqueuing
        result = self.queue_manager.enqueue_task(task, TaskPriority.NORMAL)
        
        # Verify task was enqueued
        self.assertEqual(result, "test-task-123")
        mock_user_tracker.set_user_active_task.assert_called_once_with(1, "test-task-123")
        self.mock_queues['normal'].enqueue.assert_called_once()
    
    def test_enqueue_task_user_has_active_task(self):
        """Test enqueuing when user already has active task"""
        # Create test task
        task = CaptionGenerationTask(
            id="test-task-123",
            user_id=1,
            platform_connection_id=1,
            status=TaskStatus.QUEUED
        )
        
        # Mock user task tracker to return existing task
        mock_user_tracker = Mock(spec=UserTaskTracker)
        mock_user_tracker.has_active_task.return_value = True
        mock_user_tracker.get_user_active_task.return_value = "existing-task-456"
        self.queue_manager.user_task_tracker = mock_user_tracker
        
        # Test enqueuing should raise ValueError
        with self.assertRaises(ValueError) as context:
            self.queue_manager.enqueue_task(task, TaskPriority.NORMAL)
        
        self.assertIn("already has an active task", str(context.exception))
    
    def test_enqueue_task_priority_assignment(self):
        """Test task priority assignment"""
        # Create test task without priority
        task = CaptionGenerationTask(
            id="test-task-123",
            user_id=1,
            platform_connection_id=1,
            status=TaskStatus.QUEUED
        )
        
        # Mock user task tracker
        mock_user_tracker = Mock(spec=UserTaskTracker)
        mock_user_tracker.has_active_task.return_value = False
        mock_user_tracker.set_user_active_task.return_value = True
        self.queue_manager.user_task_tracker = mock_user_tracker
        
        # Mock queue enqueue
        mock_job = Mock(spec=Job)
        mock_job.id = "rq-job-123"
        self.mock_queues['high'].enqueue.return_value = mock_job
        
        # Test enqueuing with HIGH priority
        result = self.queue_manager.enqueue_task(task, TaskPriority.HIGH)
        
        # Verify task was enqueued to high priority queue
        self.assertEqual(result, "test-task-123")
        self.mock_queues['high'].enqueue.assert_called_once()
        self.mock_queues['normal'].enqueue.assert_not_called()
    
    def test_enqueue_task_redis_unavailable(self):
        """Test task enqueuing when Redis is unavailable"""
        # Set Redis as unavailable
        self.queue_manager._redis_available = False
        self.queue_manager._fallback_mode = True
        
        # Create test task
        task = CaptionGenerationTask(
            id="test-task-123",
            user_id=1,
            platform_connection_id=1,
            status=TaskStatus.QUEUED
        )
        
        # Test enqueuing should raise exception for Redis unavailability
        with self.assertRaises(Exception) as context:
            self.queue_manager.enqueue_task(task, TaskPriority.NORMAL)
        
        self.assertIn("Redis unavailable", str(context.exception))
    
    def test_get_queue_stats(self):
        """Test getting queue statistics"""
        # Mock queue lengths
        self.mock_queues['urgent'].count = 2
        self.mock_queues['high'].count = 5
        self.mock_queues['normal'].count = 10
        self.mock_queues['low'].count = 3
        
        # Mock Redis operations for additional stats
        self.mock_redis.hgetall.return_value = {
            b'total_processed': b'100',
            b'total_failed': b'5'
        }
        
        # Get stats
        stats = self.queue_manager.get_queue_stats()
        
        # Verify stats structure
        self.assertIn('queues', stats)
        self.assertIn('urgent', stats['queues'])
        self.assertIn('high', stats['queues'])
        self.assertIn('normal', stats['queues'])
        self.assertIn('low', stats['queues'])
        self.assertIn('total_pending', stats)
        self.assertIn('redis_health', stats)
    
    def test_check_redis_health(self):
        """Test Redis health checking"""
        # Test healthy Redis
        self.mock_redis.ping.return_value = True
        result = self.queue_manager.check_redis_health()
        self.assertTrue(result)
        
        # Test unhealthy Redis
        self.mock_redis.ping.side_effect = redis.ConnectionError("Connection failed")
        result = self.queue_manager.check_redis_health()
        self.assertFalse(result)
    
    def test_migrate_database_tasks(self):
        """Test migration of database tasks to RQ"""
        # Mock database tasks
        mock_tasks = [
            Mock(id="task-1", user_id=1, platform_connection_id=1, status=TaskStatus.QUEUED),
            Mock(id="task-2", user_id=2, platform_connection_id=2, status=TaskStatus.QUEUED)
        ]
        
        self.mock_session.query.return_value.filter_by.return_value.all.return_value = mock_tasks
        
        # Mock user task tracker
        mock_user_tracker = Mock(spec=UserTaskTracker)
        mock_user_tracker.has_active_task.return_value = False
        mock_user_tracker.set_user_active_task.return_value = True
        self.queue_manager.user_task_tracker = mock_user_tracker
        
        # Mock queue enqueue
        mock_job = Mock(spec=Job)
        mock_job.id = "rq-job-123"
        for queue in self.mock_queues.values():
            queue.enqueue.return_value = mock_job
        
        # Test migration
        migrated_count = self.queue_manager.migrate_database_tasks()
        
        # Verify migration
        self.assertEqual(migrated_count, 2)
        self.assertEqual(mock_user_tracker.set_user_active_task.call_count, 2)
    
    def test_cleanup_completed_jobs(self):
        """Test cleanup of completed jobs"""
        # Mock Redis scan for completed jobs
        self.mock_redis.scan_iter.return_value = [
            b'rq:job:completed:job1',
            b'rq:job:completed:job2',
            b'rq:job:failed:job3'
        ]
        
        # Mock TTL checks (expired jobs)
        self.mock_redis.ttl.side_effect = [0, -1, 3600]  # job1 expired, job2 expired, job3 not expired
        self.mock_redis.delete.return_value = 1
        
        # Test cleanup
        cleanup_result = self.queue_manager.cleanup_completed_jobs()
        
        # Verify cleanup
        self.assertIn('jobs_cleaned', cleanup_result)
        self.assertIn('memory_freed', cleanup_result)
        self.assertEqual(self.mock_redis.delete.call_count, 2)  # Only expired jobs deleted
    
    def test_enforce_single_task_per_user(self):
        """Test single task per user enforcement"""
        user_id = 1
        
        # Mock user task tracker
        mock_user_tracker = Mock(spec=UserTaskTracker)
        self.queue_manager.user_task_tracker = mock_user_tracker
        
        # Test when user has no active task
        mock_user_tracker.has_active_task.return_value = False
        result = self.queue_manager.enforce_single_task_per_user(user_id)
        self.assertTrue(result)
        
        # Test when user has active task
        mock_user_tracker.has_active_task.return_value = True
        result = self.queue_manager.enforce_single_task_per_user(user_id)
        self.assertFalse(result)
    
    def test_generate_secure_task_id(self):
        """Test secure task ID generation"""
        task_id = self.queue_manager.generate_secure_task_id()
        
        self.assertEqual(task_id, "test-task-123")
        self.mock_security_manager.generate_secure_task_id.assert_called_once()
    
    def test_handle_redis_failure(self):
        """Test Redis failure handling"""
        # Mock Redis health monitor
        mock_health_monitor = Mock(spec=RedisHealthMonitor)
        mock_health_monitor.handle_failure.return_value = None
        self.queue_manager.redis_health_monitor = mock_health_monitor
        
        # Test Redis failure handling
        self.queue_manager.handle_redis_failure()
        
        # Verify fallback mode is activated
        self.assertTrue(self.queue_manager._fallback_mode)
        mock_health_monitor.handle_failure.assert_called_once()
    
    def test_concurrent_enqueue_operations(self):
        """Test concurrent task enqueuing operations"""
        # Mock user task tracker
        mock_user_tracker = Mock(spec=UserTaskTracker)
        mock_user_tracker.has_active_task.return_value = False
        mock_user_tracker.set_user_active_task.return_value = True
        self.queue_manager.user_task_tracker = mock_user_tracker
        
        # Mock queue enqueue
        mock_job = Mock(spec=Job)
        mock_job.id = "rq-job-123"
        for queue in self.mock_queues.values():
            queue.enqueue.return_value = mock_job
        
        # Create multiple tasks for different users
        tasks = []
        for i in range(5):
            task = CaptionGenerationTask(
                id=f"test-task-{i}",
                user_id=i + 1,
                platform_connection_id=1,
                status=TaskStatus.QUEUED
            )
            tasks.append(task)
        
        # Test concurrent enqueuing
        results = []
        threads = []
        
        def enqueue_task(task):
            try:
                result = self.queue_manager.enqueue_task(task, TaskPriority.NORMAL)
                results.append(result)
            except Exception as e:
                results.append(str(e))
        
        # Start threads
        for task in tasks:
            thread = threading.Thread(target=enqueue_task, args=(task,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Verify all tasks were enqueued successfully
        self.assertEqual(len(results), 5)
        for i, result in enumerate(results):
            self.assertEqual(result, f"test-task-{i}")
    
    def test_queue_memory_monitoring(self):
        """Test queue memory usage monitoring"""
        # Mock Redis memory info
        self.mock_redis.info.return_value = {
            'used_memory': 1024 * 1024 * 100,  # 100 MB
            'maxmemory': 1024 * 1024 * 1024    # 1 GB
        }
        
        # Test memory monitoring
        memory_status = self.queue_manager.get_memory_usage()
        
        # Verify memory status
        self.assertIn('used_memory_mb', memory_status)
        self.assertIn('max_memory_mb', memory_status)
        self.assertIn('usage_percentage', memory_status)
        self.assertEqual(memory_status['used_memory_mb'], 100.0)
        self.assertEqual(memory_status['usage_percentage'], 10.0)  # 100MB / 1GB = 10%


class TestRQQueueManagerIntegration(unittest.TestCase):
    """Integration tests for RQ Queue Manager with real Redis operations"""
    
    def setUp(self):
        """Set up integration test fixtures"""
        # These tests would require a real Redis instance for full integration testing
        # For now, we'll use mocks but structure them for real Redis integration
        self.mock_db_manager = Mock(spec=DatabaseManager)
        self.mock_security_manager = Mock(spec=CaptionSecurityManager)
        self.config = RQConfig()
    
    @unittest.skip("Requires real Redis instance for integration testing")
    def test_real_redis_integration(self):
        """Test with real Redis instance (skipped in unit tests)"""
        # This test would be enabled for integration testing with real Redis
        pass
    
    def test_error_recovery_scenarios(self):
        """Test various error recovery scenarios"""
        # Mock Redis connection that fails intermittently
        mock_redis = Mock(spec=redis.Redis)
        mock_redis.ping.side_effect = [True, redis.ConnectionError(), True]  # Fail on second call
        
        with patch('app.services.task.rq.rq_queue_manager.RedisConnectionManager') as mock_redis_manager_class:
            mock_redis_manager = Mock(spec=RedisConnectionManager)
            mock_redis_manager.initialize.return_value = True
            mock_redis_manager.get_connection.return_value = mock_redis
            mock_redis_manager_class.return_value = mock_redis_manager
            
            queue_manager = RQQueueManager(
                self.mock_db_manager,
                self.config,
                self.mock_security_manager
            )
            
            # First health check should pass
            self.assertTrue(queue_manager.check_redis_health())
            
            # Second health check should fail and trigger fallback
            self.assertFalse(queue_manager.check_redis_health())
            
            # Third health check should pass (recovery)
            self.assertTrue(queue_manager.check_redis_health())


if __name__ == '__main__':
    unittest.main()
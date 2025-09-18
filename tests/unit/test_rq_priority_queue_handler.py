# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for RQ Priority Queue Handler

Tests the priority-based task distribution and processing order with round-robin
processing within same priority level and retry logic with exponential backoff.
"""

import unittest
from unittest.mock import Mock, patch, call
import redis
from rq import Queue, Job
from rq.exceptions import NoSuchJobError
import time
from datetime import datetime, timezone, timedelta

from app.services.task.rq.priority_queue_handler import PriorityQueueHandler
from app.services.task.rq.rq_config import TaskPriority, RetryPolicy
from app.services.task.rq.task_serializer import RQTaskData


class TestPriorityQueueHandler(unittest.TestCase):
    """Test Priority Queue Handler functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock Redis connection
        self.mock_redis = Mock(spec=redis.Redis)
        
        # Mock queues for each priority
        self.mock_queues = {}
        for priority in ['urgent', 'high', 'normal', 'low']:
            mock_queue = Mock(spec=Queue)
            mock_queue.name = priority
            mock_queue.count = 0
            self.mock_queues[priority] = mock_queue
        
        # Initialize priority queue handler
        self.handler = PriorityQueueHandler(self.mock_redis, self.mock_queues)
    
    def test_initialization(self):
        """Test PriorityQueueHandler initialization"""
        # Verify priority order is correct
        expected_order = ['urgent', 'high', 'normal', 'low']
        self.assertEqual(self.handler.priority_order, expected_order)
        
        # Verify round-robin state is initialized
        for priority in expected_order:
            self.assertIn(priority, self.handler._round_robin_state)
            self.assertEqual(self.handler._round_robin_state[priority], 0)
        
        # Verify Redis connection and queues are set
        self.assertEqual(self.handler.redis, self.mock_redis)
        self.assertEqual(self.handler.queues, self.mock_queues)
    
    def test_get_next_task_priority_order(self):
        """Test that tasks are retrieved in strict priority order"""
        # Mock jobs for different priorities
        urgent_job = Mock(spec=Job)
        urgent_job.id = "urgent-job-1"
        
        normal_job = Mock(spec=Job)
        normal_job.id = "normal-job-1"
        
        # Set up queue dequeue behavior
        self.mock_queues['urgent'].dequeue.return_value = urgent_job
        self.mock_queues['high'].dequeue.return_value = None
        self.mock_queues['normal'].dequeue.return_value = normal_job
        self.mock_queues['low'].dequeue.return_value = None
        
        # Worker can process all queues
        worker_queues = ['urgent', 'high', 'normal', 'low']
        
        # Get next task - should return urgent job first
        job = self.handler.get_next_task(worker_queues)
        
        self.assertEqual(job, urgent_job)
        self.mock_queues['urgent'].dequeue.assert_called_once()
        # Normal queue should not be called since urgent had a job
        self.mock_queues['normal'].dequeue.assert_not_called()
    
    def test_get_next_task_no_urgent_jobs(self):
        """Test task retrieval when no urgent jobs are available"""
        # Mock empty urgent and high queues, job in normal queue
        normal_job = Mock(spec=Job)
        normal_job.id = "normal-job-1"
        
        self.mock_queues['urgent'].dequeue.return_value = None
        self.mock_queues['high'].dequeue.return_value = None
        self.mock_queues['normal'].dequeue.return_value = normal_job
        self.mock_queues['low'].dequeue.return_value = None
        
        worker_queues = ['urgent', 'high', 'normal', 'low']
        
        # Get next task - should return normal job
        job = self.handler.get_next_task(worker_queues)
        
        self.assertEqual(job, normal_job)
        self.mock_queues['urgent'].dequeue.assert_called_once()
        self.mock_queues['high'].dequeue.assert_called_once()
        self.mock_queues['normal'].dequeue.assert_called_once()
    
    def test_get_next_task_worker_queue_restrictions(self):
        """Test task retrieval with worker queue restrictions"""
        # Mock jobs in all queues
        urgent_job = Mock(spec=Job)
        urgent_job.id = "urgent-job-1"
        
        normal_job = Mock(spec=Job)
        normal_job.id = "normal-job-1"
        
        self.mock_queues['urgent'].dequeue.return_value = urgent_job
        self.mock_queues['normal'].dequeue.return_value = normal_job
        
        # Worker can only process normal and low queues
        worker_queues = ['normal', 'low']
        
        # Get next task - should skip urgent and return normal
        job = self.handler.get_next_task(worker_queues)
        
        self.assertEqual(job, normal_job)
        # Urgent queue should not be called since worker can't process it
        self.mock_queues['urgent'].dequeue.assert_not_called()
        self.mock_queues['normal'].dequeue.assert_called_once()
    
    def test_get_next_task_no_jobs_available(self):
        """Test task retrieval when no jobs are available"""
        # Mock all queues as empty
        for queue in self.mock_queues.values():
            queue.dequeue.return_value = None
        
        worker_queues = ['urgent', 'high', 'normal', 'low']
        
        # Get next task - should return None
        job = self.handler.get_next_task(worker_queues)
        
        self.assertIsNone(job)
        
        # All queues should have been checked
        for queue in self.mock_queues.values():
            queue.dequeue.assert_called_once()
    
    def test_round_robin_within_same_priority(self):
        """Test round-robin processing within same priority level"""
        # This test verifies the round-robin state tracking
        # In a real implementation, this would involve multiple jobs in the same queue
        
        normal_job1 = Mock(spec=Job)
        normal_job1.id = "normal-job-1"
        
        normal_job2 = Mock(spec=Job)
        normal_job2.id = "normal-job-2"
        
        # Mock queue to return different jobs on subsequent calls
        self.mock_queues['normal'].dequeue.side_effect = [normal_job1, normal_job2, None]
        
        # Mock empty higher priority queues
        self.mock_queues['urgent'].dequeue.return_value = None
        self.mock_queues['high'].dequeue.return_value = None
        self.mock_queues['low'].dequeue.return_value = None
        
        worker_queues = ['urgent', 'high', 'normal', 'low']
        
        # Get first job
        job1 = self.handler.get_next_task(worker_queues)
        self.assertEqual(job1, normal_job1)
        
        # Reset mock call counts
        for queue in self.mock_queues.values():
            queue.dequeue.reset_mock()
        
        # Get second job
        job2 = self.handler.get_next_task(worker_queues)
        self.assertEqual(job2, normal_job2)
    
    def test_enqueue_by_priority(self):
        """Test enqueuing tasks by priority"""
        # Create test task data
        task_data = RQTaskData(
            task_id='test-task-123',
            user_id=1,
            platform_connection_id=1,
            priority='high',
            settings={},
            created_at=datetime.now(timezone.utc).isoformat()
        )
        
        # Mock job creation
        mock_job = Mock(spec=Job)
        mock_job.id = "rq-job-123"
        self.mock_queues['high'].enqueue.return_value = mock_job
        
        # Test enqueuing
        result = self.handler.enqueue_by_priority(task_data, TaskPriority.HIGH)
        
        # Verify task was enqueued to correct queue
        self.assertEqual(result, mock_job)
        self.mock_queues['high'].enqueue.assert_called_once()
        
        # Verify other queues were not called
        self.mock_queues['urgent'].enqueue.assert_not_called()
        self.mock_queues['normal'].enqueue.assert_not_called()
        self.mock_queues['low'].enqueue.assert_not_called()
    
    def test_requeue_failed_task_first_retry(self):
        """Test requeuing a failed task for first retry"""
        # Create failed task data
        task_data = RQTaskData(
            task_id='failed-task-123',
            user_id=1,
            platform_connection_id=1,
            priority='normal',
            settings={},
            created_at=datetime.now(timezone.utc).isoformat(),
            retry_count=0,
            max_retries=3
        )
        
        # Mock Redis operations for retry tracking
        self.mock_redis.hset.return_value = True
        self.mock_redis.expire.return_value = True
        
        # Mock job creation for requeue
        mock_job = Mock(spec=Job)
        mock_job.id = "retry-job-123"
        self.mock_queues['normal'].enqueue.return_value = mock_job
        
        # Test requeuing
        result = self.handler.requeue_failed_task(task_data, 1)
        
        # Verify task was requeued
        self.assertTrue(result)
        self.mock_queues['normal'].enqueue.assert_called_once()
        
        # Verify retry tracking in Redis
        self.mock_redis.hset.assert_called()
        self.mock_redis.expire.assert_called()
    
    def test_requeue_failed_task_max_retries_exceeded(self):
        """Test requeuing when max retries are exceeded"""
        # Create task that has exceeded max retries
        task_data = RQTaskData(
            task_id='exhausted-task-123',
            user_id=1,
            platform_connection_id=1,
            priority='normal',
            settings={},
            created_at=datetime.now(timezone.utc).isoformat(),
            retry_count=3,
            max_retries=3
        )
        
        # Mock Redis operations for dead letter queue
        self.mock_redis.lpush.return_value = 1
        self.mock_redis.expire.return_value = True
        
        # Test requeuing - should move to dead letter queue
        result = self.handler.requeue_failed_task(task_data, 4)
        
        # Verify task was not requeued but moved to dead letter queue
        self.assertFalse(result)
        for queue in self.mock_queues.values():
            queue.enqueue.assert_not_called()
        
        # Verify dead letter queue operations
        self.mock_redis.lpush.assert_called()
    
    def test_exponential_backoff_calculation(self):
        """Test exponential backoff delay calculation"""
        # Test backoff for different retry counts
        delay1 = self.handler._calculate_backoff_delay(1)
        delay2 = self.handler._calculate_backoff_delay(2)
        delay3 = self.handler._calculate_backoff_delay(3)
        
        # Verify exponential increase
        self.assertGreater(delay2, delay1)
        self.assertGreater(delay3, delay2)
        
        # Verify delays are reasonable (not too large)
        self.assertLess(delay1, 300)  # Less than 5 minutes
        self.assertLess(delay3, 3600)  # Less than 1 hour
    
    def test_get_job_from_queue_success(self):
        """Test successful job retrieval from queue"""
        mock_job = Mock(spec=Job)
        mock_job.id = "test-job-123"
        
        queue = self.mock_queues['normal']
        queue.dequeue.return_value = mock_job
        
        # Test job retrieval
        result = self.handler._get_job_from_queue(queue, 'normal')
        
        self.assertEqual(result, mock_job)
        queue.dequeue.assert_called_once()
    
    def test_get_job_from_queue_empty(self):
        """Test job retrieval from empty queue"""
        queue = self.mock_queues['normal']
        queue.dequeue.return_value = None
        
        # Test job retrieval from empty queue
        result = self.handler._get_job_from_queue(queue, 'normal')
        
        self.assertIsNone(result)
        queue.dequeue.assert_called_once()
    
    def test_get_job_from_queue_exception(self):
        """Test job retrieval with queue exception"""
        queue = self.mock_queues['normal']
        queue.dequeue.side_effect = redis.ConnectionError("Redis connection failed")
        
        # Test job retrieval with exception
        result = self.handler._get_job_from_queue(queue, 'normal')
        
        self.assertIsNone(result)
        queue.dequeue.assert_called_once()
    
    def test_retry_policy_application(self):
        """Test application of retry policies"""
        # Create custom retry policy
        retry_policy = RetryPolicy(
            max_retries=5,
            backoff_strategy='exponential',
            base_delay=30,
            max_delay=1800
        )
        
        # Apply retry policy to handler
        self.handler.retry_policy = retry_policy
        
        # Test backoff calculation with custom policy
        delay = self.handler._calculate_backoff_delay(2, retry_policy)
        
        # Verify delay respects policy settings
        self.assertGreaterEqual(delay, retry_policy.base_delay)
        self.assertLessEqual(delay, retry_policy.max_delay)
    
    def test_queue_statistics_collection(self):
        """Test collection of queue statistics"""
        # Mock queue counts
        self.mock_queues['urgent'].count = 2
        self.mock_queues['high'].count = 5
        self.mock_queues['normal'].count = 10
        self.mock_queues['low'].count = 3
        
        # Mock Redis operations for additional stats
        self.mock_redis.hgetall.return_value = {
            b'total_processed': b'150',
            b'total_failed': b'8',
            b'total_retried': b'12'
        }
        
        # Get statistics
        stats = self.handler.get_queue_statistics()
        
        # Verify statistics structure
        self.assertIn('queue_counts', stats)
        self.assertIn('total_pending', stats)
        self.assertIn('processing_stats', stats)
        
        # Verify queue counts
        self.assertEqual(stats['queue_counts']['urgent'], 2)
        self.assertEqual(stats['queue_counts']['high'], 5)
        self.assertEqual(stats['queue_counts']['normal'], 10)
        self.assertEqual(stats['queue_counts']['low'], 3)
        
        # Verify total pending
        self.assertEqual(stats['total_pending'], 20)  # 2+5+10+3
    
    def test_failed_job_tracking(self):
        """Test tracking of failed jobs"""
        task_id = "failed-task-456"
        error_message = "Processing failed due to network error"
        
        # Mock Redis operations
        self.mock_redis.hset.return_value = True
        self.mock_redis.expire.return_value = True
        
        # Track failed job
        self.handler.track_failed_job(task_id, error_message)
        
        # Verify Redis operations
        expected_key = f"{self.handler._failed_job_prefix}{task_id}"
        self.mock_redis.hset.assert_called_with(
            expected_key,
            mapping={
                'task_id': task_id,
                'error_message': error_message,
                'failed_at': unittest.mock.ANY,
                'retry_count': 0
            }
        )
        self.mock_redis.expire.assert_called_with(expected_key, 86400)  # 24 hours
    
    def test_cleanup_expired_retry_data(self):
        """Test cleanup of expired retry tracking data"""
        # Mock Redis scan for retry keys
        self.mock_redis.scan_iter.return_value = [
            b'vedfolnir:rq:retry:task1',
            b'vedfolnir:rq:retry:task2',
            b'vedfolnir:rq:retry:task3'
        ]
        
        # Mock TTL checks (some expired, some not)
        self.mock_redis.ttl.side_effect = [0, 3600, -1]  # task1 expired, task2 active, task3 expired
        self.mock_redis.delete.return_value = 1
        
        # Test cleanup
        cleaned_count = self.handler.cleanup_expired_retry_data()
        
        # Verify cleanup
        self.assertEqual(cleaned_count, 2)  # task1 and task3 should be cleaned
        self.assertEqual(self.mock_redis.delete.call_count, 2)
    
    def test_priority_queue_balancing(self):
        """Test balancing across priority queues"""
        # Mock multiple jobs in high priority queue
        high_jobs = [Mock(spec=Job) for _ in range(3)]
        for i, job in enumerate(high_jobs):
            job.id = f"high-job-{i}"
        
        # Mock normal priority job
        normal_job = Mock(spec=Job)
        normal_job.id = "normal-job-1"
        
        # Set up queue behavior - high queue has multiple jobs
        self.mock_queues['urgent'].dequeue.return_value = None
        self.mock_queues['high'].dequeue.side_effect = high_jobs + [None]
        self.mock_queues['normal'].dequeue.return_value = normal_job
        self.mock_queues['low'].dequeue.return_value = None
        
        worker_queues = ['urgent', 'high', 'normal', 'low']
        
        # Get multiple jobs - should prioritize high queue
        jobs = []
        for _ in range(4):  # Try to get 4 jobs
            # Reset mock call counts for each iteration
            for queue in self.mock_queues.values():
                queue.dequeue.reset_mock()
            
            # Set up fresh side effects
            if len(jobs) < 3:
                self.mock_queues['high'].dequeue.return_value = high_jobs[len(jobs)]
            else:
                self.mock_queues['high'].dequeue.return_value = None
                self.mock_queues['normal'].dequeue.return_value = normal_job if len(jobs) == 3 else None
            
            job = self.handler.get_next_task(worker_queues)
            if job:
                jobs.append(job)
            else:
                break
        
        # Verify we got all high priority jobs first, then normal
        self.assertEqual(len(jobs), 4)
        for i in range(3):
            self.assertEqual(jobs[i], high_jobs[i])
        self.assertEqual(jobs[3], normal_job)


class TestPriorityQueueHandlerIntegration(unittest.TestCase):
    """Integration tests for Priority Queue Handler"""
    
    def setUp(self):
        """Set up integration test fixtures"""
        self.mock_redis = Mock(spec=redis.Redis)
        self.mock_queues = {}
        
        for priority in ['urgent', 'high', 'normal', 'low']:
            mock_queue = Mock(spec=Queue)
            mock_queue.name = priority
            self.mock_queues[priority] = mock_queue
        
        self.handler = PriorityQueueHandler(self.mock_redis, self.mock_queues)
    
    def test_full_task_lifecycle_with_retries(self):
        """Test complete task lifecycle including retries"""
        # Create initial task
        task_data = RQTaskData(
            task_id='lifecycle-task-123',
            user_id=1,
            platform_connection_id=1,
            priority='normal',
            settings={'max_length': 500},
            created_at=datetime.now(timezone.utc).isoformat(),
            retry_count=0,
            max_retries=3
        )
        
        # Mock Redis operations
        self.mock_redis.hset.return_value = True
        self.mock_redis.expire.return_value = True
        self.mock_redis.lpush.return_value = 1
        
        # Mock job creation
        mock_jobs = [Mock(spec=Job) for _ in range(4)]
        for i, job in enumerate(mock_jobs):
            job.id = f"job-attempt-{i}"
        
        self.mock_queues['normal'].enqueue.side_effect = mock_jobs
        
        # Test initial enqueue
        job1 = self.handler.enqueue_by_priority(task_data, TaskPriority.NORMAL)
        self.assertEqual(job1, mock_jobs[0])
        
        # Test first retry
        task_data.retry_count = 1
        retry_result1 = self.handler.requeue_failed_task(task_data, 1)
        self.assertTrue(retry_result1)
        
        # Test second retry
        task_data.retry_count = 2
        retry_result2 = self.handler.requeue_failed_task(task_data, 2)
        self.assertTrue(retry_result2)
        
        # Test final retry
        task_data.retry_count = 3
        retry_result3 = self.handler.requeue_failed_task(task_data, 3)
        self.assertTrue(retry_result3)
        
        # Test exceeding max retries (should go to dead letter queue)
        task_data.retry_count = 4
        final_result = self.handler.requeue_failed_task(task_data, 4)
        self.assertFalse(final_result)
        
        # Verify dead letter queue was used
        self.mock_redis.lpush.assert_called()


if __name__ == '__main__':
    unittest.main()
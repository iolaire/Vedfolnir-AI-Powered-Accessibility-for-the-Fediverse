# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Unit tests for TaskQueueManager admin control methods
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta, timezone
import uuid

from task_queue_manager import TaskQueueManager
from models import CaptionGenerationTask, TaskStatus, User, UserRole, CaptionGenerationSettings, JobPriority
from database import DatabaseManager


class TestTaskQueueManagerAdmin(unittest.TestCase):
    """Test cases for TaskQueueManager admin control methods"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_db_manager = Mock(spec=DatabaseManager)
        self.mock_session = Mock()
        self.mock_db_manager.get_session.return_value = self.mock_session
        
        self.queue_manager = TaskQueueManager(self.mock_db_manager, max_concurrent_tasks=2)
        
        # Create test admin user
        self.admin_user = User(
            id=1,
            username="admin",
            email="admin@test.com",
            role=UserRole.ADMIN
        )
        
        # Create test regular user
        self.regular_user = User(
            id=2,
            username="user",
            email="user@test.com",
            role=UserRole.REVIEWER
        )
        
        # Create test tasks
        self.test_task_1 = CaptionGenerationTask(
            id=str(uuid.uuid4()),
            user_id=2,
            platform_connection_id=1,
            status=TaskStatus.QUEUED,
            priority=JobPriority.NORMAL,
            retry_count=0,
            max_retries=3
        )
        
        self.test_task_2 = CaptionGenerationTask(
            id=str(uuid.uuid4()),
            user_id=2,
            platform_connection_id=1,
            status=TaskStatus.RUNNING,
            priority=JobPriority.HIGH,
            retry_count=0,
            max_retries=3
        )
    
    def _setup_admin_user_mock(self):
        """Helper to setup admin user mock"""
        admin_query_mock = Mock()
        admin_query_mock.filter_by.return_value.first.return_value = self.admin_user
        return admin_query_mock
    
    def _setup_regular_user_mock(self):
        """Helper to setup regular user mock"""
        user_query_mock = Mock()
        user_query_mock.filter_by.return_value.first.return_value = self.regular_user
        return user_query_mock
    
    def test_get_all_tasks_success(self):
        """Test successful retrieval of all tasks by admin"""
        # Create separate mock sessions for different queries
        admin_query_mock = Mock()
        admin_query_mock.filter_by.return_value.first.return_value = self.admin_user
        
        tasks_query_mock = Mock()
        join_mock = Mock()
        order_by_mock = Mock()
        limit_mock = Mock()
        
        tasks_query_mock.join.return_value = join_mock
        join_mock.order_by.return_value = order_by_mock
        order_by_mock.limit.return_value = limit_mock
        limit_mock.all.return_value = [self.test_task_1, self.test_task_2]
        
        # Mock session.query to return different mocks for different calls
        self.mock_session.query.side_effect = [admin_query_mock, tasks_query_mock]
        
        # Test
        result = self.queue_manager.get_all_tasks(admin_user_id=1)
        
        # Verify
        self.assertEqual(len(result), 2)
        self.mock_session.expunge.assert_called()
    
    def test_get_all_tasks_unauthorized(self):
        """Test get_all_tasks with non-admin user"""
        # Mock regular user query
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = self.regular_user
        
        # Test
        with self.assertRaises(ValueError) as context:
            self.queue_manager.get_all_tasks(admin_user_id=2)
        
        self.assertIn("not authorized for admin operations", str(context.exception))
    
    def test_get_all_tasks_with_status_filter(self):
        """Test get_all_tasks with status filter"""
        # Create separate mock sessions for different queries
        admin_query_mock = Mock()
        admin_query_mock.filter_by.return_value.first.return_value = self.admin_user
        
        tasks_query_mock = Mock()
        join_mock = Mock()
        filter_mock = Mock()
        order_by_mock = Mock()
        limit_mock = Mock()
        
        tasks_query_mock.join.return_value = join_mock
        join_mock.filter.return_value = filter_mock
        filter_mock.order_by.return_value = order_by_mock
        order_by_mock.limit.return_value = limit_mock
        limit_mock.all.return_value = [self.test_task_1]
        
        # Mock session.query to return different mocks for different calls
        self.mock_session.query.side_effect = [admin_query_mock, tasks_query_mock]
        
        # Test
        result = self.queue_manager.get_all_tasks(
            admin_user_id=1, 
            status_filter=[TaskStatus.QUEUED]
        )
        
        # Verify filter was applied
        join_mock.filter.assert_called()
        self.assertEqual(len(result), 1)
    
    def test_cancel_task_as_admin_success(self):
        """Test successful admin task cancellation"""
        # Create separate mocks for admin and task queries
        admin_query_mock = Mock()
        admin_query_mock.filter_by.return_value.first.return_value = self.admin_user
        
        task_query_mock = Mock()
        task_query_mock.filter_by.return_value.first.return_value = self.test_task_1
        
        # Mock session.query to return different mocks for different calls
        self.mock_session.query.side_effect = [admin_query_mock, task_query_mock]
        
        # Mock can_be_cancelled
        self.test_task_1.can_be_cancelled = Mock(return_value=True)
        
        # Test
        result = self.queue_manager.cancel_task_as_admin(
            task_id=self.test_task_1.id,
            admin_user_id=1,
            reason="Test cancellation"
        )
        
        # Verify
        self.assertTrue(result)
        self.assertEqual(self.test_task_1.status, TaskStatus.CANCELLED)
        self.assertTrue(self.test_task_1.cancelled_by_admin)
        self.assertEqual(self.test_task_1.admin_user_id, 1)
        self.assertEqual(self.test_task_1.cancellation_reason, "Test cancellation")
        self.mock_session.commit.assert_called()
    
    def test_cancel_task_as_admin_unauthorized(self):
        """Test admin task cancellation with non-admin user"""
        # Mock regular user query
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = self.regular_user
        
        # Test
        with self.assertRaises(ValueError) as context:
            self.queue_manager.cancel_task_as_admin(
                task_id=self.test_task_1.id,
                admin_user_id=2,
                reason="Test"
            )
        
        self.assertIn("not authorized for admin operations", str(context.exception))
    
    def test_cancel_task_as_admin_task_not_found(self):
        """Test admin task cancellation with non-existent task"""
        # Mock admin user query and task not found
        self.mock_session.query.return_value.filter_by.return_value.first.side_effect = [
            self.admin_user,  # Admin verification
            None  # Task not found
        ]
        
        # Test
        result = self.queue_manager.cancel_task_as_admin(
            task_id="nonexistent",
            admin_user_id=1,
            reason="Test"
        )
        
        # Verify
        self.assertFalse(result)
    
    def test_cancel_task_as_admin_cannot_be_cancelled(self):
        """Test admin task cancellation with non-cancellable task"""
        # Mock admin user query
        self.mock_session.query.return_value.filter_by.return_value.first.side_effect = [
            self.admin_user,  # Admin verification
            self.test_task_1  # Task lookup
        ]
        
        # Mock can_be_cancelled to return False
        self.test_task_1.can_be_cancelled = Mock(return_value=False)
        
        # Test
        result = self.queue_manager.cancel_task_as_admin(
            task_id=self.test_task_1.id,
            admin_user_id=1,
            reason="Test"
        )
        
        # Verify
        self.assertFalse(result)
    
    def test_pause_user_jobs_success(self):
        """Test successful pausing of user jobs"""
        # Setup admin user mock
        admin_query_mock = self._setup_admin_user_mock()
        
        # Mock active tasks query
        tasks_query_mock = Mock()
        filter_mock = Mock()
        
        tasks_query_mock.filter.return_value = filter_mock
        filter_mock.all.return_value = [self.test_task_1, self.test_task_2]
        
        # Mock session.query to return different mocks for different calls
        self.mock_session.query.side_effect = [admin_query_mock, tasks_query_mock]
        
        # Test
        result = self.queue_manager.pause_user_jobs(admin_user_id=1, target_user_id=2)
        
        # Verify
        self.assertEqual(result, 2)  # Both tasks should be paused
        self.assertEqual(self.test_task_1.status, TaskStatus.CANCELLED)  # Queued task cancelled
        self.assertTrue(self.test_task_1.cancelled_by_admin)
        self.assertIsNotNone(self.test_task_2.admin_notes)  # Running task marked
        self.mock_session.commit.assert_called()
    
    def test_pause_user_jobs_unauthorized(self):
        """Test pause user jobs with non-admin user"""
        # Mock regular user query
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = self.regular_user
        
        # Test
        with self.assertRaises(ValueError) as context:
            self.queue_manager.pause_user_jobs(admin_user_id=2, target_user_id=1)
        
        self.assertIn("not authorized for admin operations", str(context.exception))
    
    def test_resume_user_jobs_success(self):
        """Test successful resuming of user jobs"""
        # Setup admin user mock
        admin_query_mock = self._setup_admin_user_mock()
        
        # Mock tasks with pause notes
        paused_task = Mock()
        paused_task.admin_notes = "Marked for cancellation by admin 1"
        
        tasks_query_mock = Mock()
        filter_mock = Mock()
        
        tasks_query_mock.filter.return_value = filter_mock
        filter_mock.all.return_value = [paused_task]
        
        # Mock session.query to return different mocks for different calls
        self.mock_session.query.side_effect = [admin_query_mock, tasks_query_mock]
        
        # Test
        result = self.queue_manager.resume_user_jobs(admin_user_id=1, target_user_id=2)
        
        # Verify
        self.assertTrue(result)
        self.assertIsNone(paused_task.admin_notes)
        self.mock_session.commit.assert_called()
    
    def test_resume_user_jobs_unauthorized(self):
        """Test resume user jobs with non-admin user"""
        # Mock regular user query
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = self.regular_user
        
        # Test
        with self.assertRaises(ValueError) as context:
            self.queue_manager.resume_user_jobs(admin_user_id=2, target_user_id=1)
        
        self.assertIn("not authorized for admin operations", str(context.exception))
    
    def test_clear_stuck_tasks_success(self):
        """Test successful clearing of stuck tasks"""
        # Setup admin user mock
        admin_query_mock = self._setup_admin_user_mock()
        
        # Create stuck task (started more than 60 minutes ago)
        stuck_task = Mock()
        stuck_task.started_at = datetime.now(timezone.utc) - timedelta(minutes=90)
        stuck_task.status = TaskStatus.RUNNING
        
        # Mock stuck tasks query
        tasks_query_mock = Mock()
        filter_mock = Mock()
        
        tasks_query_mock.filter.return_value = filter_mock
        filter_mock.all.return_value = [stuck_task]
        
        # Mock session.query to return different mocks for different calls
        self.mock_session.query.side_effect = [admin_query_mock, tasks_query_mock]
        
        # Test
        result = self.queue_manager.clear_stuck_tasks(admin_user_id=1, stuck_threshold_minutes=60)
        
        # Verify
        self.assertEqual(result, 1)
        self.assertEqual(stuck_task.status, TaskStatus.FAILED)
        self.assertTrue(stuck_task.cancelled_by_admin)
        self.assertEqual(stuck_task.admin_user_id, 1)
        self.assertIn("stuck", stuck_task.error_message)
        self.mock_session.commit.assert_called()
    
    def test_clear_stuck_tasks_unauthorized(self):
        """Test clear stuck tasks with non-admin user"""
        # Mock regular user query
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = self.regular_user
        
        # Test
        with self.assertRaises(ValueError) as context:
            self.queue_manager.clear_stuck_tasks(admin_user_id=2)
        
        self.assertIn("not authorized for admin operations", str(context.exception))
    
    def test_set_task_priority_success(self):
        """Test successful task priority setting"""
        # Setup admin user mock
        admin_query_mock = self._setup_admin_user_mock()
        
        # Setup task query mock
        task_query_mock = Mock()
        task_query_mock.filter_by.return_value.first.return_value = self.test_task_1
        
        # Mock session.query to return different mocks for different calls
        self.mock_session.query.side_effect = [admin_query_mock, task_query_mock]
        
        # Test
        result = self.queue_manager.set_task_priority(
            task_id=self.test_task_1.id,
            admin_user_id=1,
            priority=JobPriority.HIGH
        )
        
        # Verify
        self.assertTrue(result)
        self.assertEqual(self.test_task_1.priority, JobPriority.HIGH)
        self.assertIn("Priority changed", self.test_task_1.admin_notes)
        self.mock_session.commit.assert_called()
    
    def test_set_task_priority_unauthorized(self):
        """Test set task priority with non-admin user"""
        # Mock regular user query
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = self.regular_user
        
        # Test
        with self.assertRaises(ValueError) as context:
            self.queue_manager.set_task_priority(
                task_id=self.test_task_1.id,
                admin_user_id=2,
                priority=JobPriority.HIGH
            )
        
        self.assertIn("not authorized for admin operations", str(context.exception))
    
    def test_set_task_priority_task_not_found(self):
        """Test set task priority with non-existent task"""
        # Mock admin user query and task not found
        self.mock_session.query.return_value.filter_by.return_value.first.side_effect = [
            self.admin_user,  # Admin verification
            None  # Task not found
        ]
        
        # Test
        result = self.queue_manager.set_task_priority(
            task_id="nonexistent",
            admin_user_id=1,
            priority=JobPriority.HIGH
        )
        
        # Verify
        self.assertFalse(result)
    
    @patch('security.features.caption_security.CaptionSecurityManager')
    def test_requeue_failed_task_success(self, mock_security_manager_class):
        """Test successful requeuing of failed task"""
        # Mock security manager
        mock_security_manager = Mock()
        mock_security_manager.generate_secure_task_id.return_value = "new-task-id"
        mock_security_manager_class.return_value = mock_security_manager
        
        # Setup admin user mock
        admin_query_mock = self._setup_admin_user_mock()
        
        # Setup original task query mock
        task_query_mock = Mock()
        task_query_mock.filter_by.return_value.first.return_value = self.test_task_1
        
        # Set original task as failed
        self.test_task_1.status = TaskStatus.FAILED
        
        # Mock no existing active task
        active_task_query_mock = Mock()
        filter_mock = Mock()
        
        active_task_query_mock.filter.return_value = filter_mock
        filter_mock.first.return_value = None  # No existing active task
        
        # Mock session.query to return different mocks for different calls
        self.mock_session.query.side_effect = [admin_query_mock, task_query_mock, active_task_query_mock]
        
        # Test
        result = self.queue_manager.requeue_failed_task(
            task_id=self.test_task_1.id,
            admin_user_id=1
        )
        
        # Verify
        self.assertEqual(result, "new-task-id")
        self.mock_session.add.assert_called()
        self.mock_session.commit.assert_called()
    
    def test_requeue_failed_task_unauthorized(self):
        """Test requeue failed task with non-admin user"""
        # Mock regular user query
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = self.regular_user
        
        # Test
        with self.assertRaises(ValueError) as context:
            self.queue_manager.requeue_failed_task(
                task_id=self.test_task_1.id,
                admin_user_id=2
            )
        
        self.assertIn("not authorized for admin operations", str(context.exception))
    
    def test_requeue_failed_task_not_failed(self):
        """Test requeue task that is not failed"""
        # Mock admin user query
        self.mock_session.query.return_value.filter_by.return_value.first.side_effect = [
            self.admin_user,  # Admin verification
            self.test_task_1  # Task lookup (still queued)
        ]
        
        # Test
        result = self.queue_manager.requeue_failed_task(
            task_id=self.test_task_1.id,
            admin_user_id=1
        )
        
        # Verify
        self.assertIsNone(result)
    
    def test_requeue_failed_task_user_has_active_task(self):
        """Test requeue failed task when user already has active task"""
        # Setup admin user mock
        admin_query_mock = self._setup_admin_user_mock()
        
        # Setup original task query mock
        task_query_mock = Mock()
        task_query_mock.filter_by.return_value.first.return_value = self.test_task_1
        
        # Set original task as failed
        self.test_task_1.status = TaskStatus.FAILED
        
        # Mock existing active task
        active_task = Mock()
        active_task.id = "active-task-id"
        
        active_task_query_mock = Mock()
        filter_mock = Mock()
        
        active_task_query_mock.filter.return_value = filter_mock
        filter_mock.first.return_value = active_task  # Existing active task
        
        # Mock session.query to return different mocks for different calls
        self.mock_session.query.side_effect = [admin_query_mock, task_query_mock, active_task_query_mock]
        
        # Test
        result = self.queue_manager.requeue_failed_task(
            task_id=self.test_task_1.id,
            admin_user_id=1
        )
        
        # Verify
        self.assertIsNone(result)
    
    def test_get_queue_statistics_success(self):
        """Test successful queue statistics retrieval"""
        # Setup admin user mock
        admin_query_mock = self._setup_admin_user_mock()
        
        # Mock queued tasks for wait time calculation
        queued_task = Mock()
        queued_task.created_at = datetime.now(timezone.utc) - timedelta(minutes=30)
        
        # Create a comprehensive mock that handles all the different query patterns
        def create_count_mock(count_value=2):
            mock = Mock()
            mock.filter_by.return_value.count.return_value = count_value
            mock.filter.return_value.count.return_value = count_value
            mock.filter_by.return_value.all.return_value = [queued_task]
            return mock
        
        # Create enough mocks for all the queries in get_queue_statistics
        # The method queries: TaskStatus counts (5), JobPriority counts (4), admin_cancelled, retried_tasks, queued_tasks
        query_mocks = [create_count_mock() for _ in range(15)]
        
        # Mock session.query to return different mocks for different calls
        self.mock_session.query.side_effect = [admin_query_mock] + query_mocks
        
        # Test
        result = self.queue_manager.get_queue_statistics(admin_user_id=1)
        
        # Verify
        self.assertIsInstance(result, dict)
        self.assertIn('queued_count', result)
        self.assertIn('running_count', result)
        self.assertIn('priority_breakdown', result)
        self.assertIn('admin_cancelled_count', result)
        self.assertIn('average_wait_time_seconds', result)
        self.assertIn('total_tasks', result)
        self.assertIn('active_tasks', result)
    
    def test_get_queue_statistics_unauthorized(self):
        """Test get queue statistics with non-admin user"""
        # Mock regular user query
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = self.regular_user
        
        # Test
        with self.assertRaises(ValueError) as context:
            self.queue_manager.get_queue_statistics(admin_user_id=2)
        
        self.assertIn("not authorized for admin operations", str(context.exception))
    
    def test_enqueue_task_with_priority_override(self):
        """Test enqueuing task with priority override"""
        # Mock existing task check
        query_mock = Mock()
        filter_by_mock = Mock()
        filter_mock = Mock()
        
        self.mock_session.query.return_value = query_mock
        query_mock.filter_by.return_value = filter_by_mock
        filter_by_mock.filter.return_value = filter_mock
        filter_mock.first.return_value = None  # No existing active task
        
        # Mock security manager
        with patch('security.features.caption_security.CaptionSecurityManager') as mock_security_class:
            mock_security_manager = Mock()
            mock_security_manager.generate_secure_task_id.return_value = "test-task-id"
            mock_security_class.return_value = mock_security_manager
            
            # Test
            result = self.queue_manager.enqueue_task(
                self.test_task_1, 
                priority_override=JobPriority.URGENT
            )
            
            # Verify
            self.assertEqual(result, self.test_task_1.id)
            self.assertEqual(self.test_task_1.priority, JobPriority.URGENT)
            self.mock_session.add.assert_called_with(self.test_task_1)
            self.mock_session.commit.assert_called()
    
    def test_cancel_task_with_admin_parameters(self):
        """Test cancel_task method with admin parameters"""
        # Mock the session.query calls in the order they happen in cancel_task
        # First call: query for task
        task_query_mock = Mock()
        task_filter_by_mock = Mock()
        
        task_query_mock.filter_by.return_value = task_filter_by_mock
        task_filter_by_mock.first.return_value = self.test_task_1
        
        # Second call: query for admin user
        admin_query_mock = Mock()
        admin_filter_by_mock = Mock()
        
        admin_query_mock.filter_by.return_value = admin_filter_by_mock
        admin_filter_by_mock.first.return_value = self.admin_user
        
        # Set up the side_effect to return the right mock for each call
        self.mock_session.query.side_effect = [task_query_mock, admin_query_mock]
        
        # Mock can_be_cancelled
        self.test_task_1.can_be_cancelled = Mock(return_value=True)
        
        # Test
        result = self.queue_manager.cancel_task(
            task_id=self.test_task_1.id,
            admin_user_id=1,
            reason="Admin test cancellation"
        )
        
        # Verify
        self.assertTrue(result)
        self.assertEqual(self.test_task_1.status, TaskStatus.CANCELLED)
        self.assertTrue(self.test_task_1.cancelled_by_admin)
        self.assertEqual(self.test_task_1.admin_user_id, 1)
        self.assertEqual(self.test_task_1.cancellation_reason, "Admin test cancellation")
        self.mock_session.commit.assert_called()


if __name__ == '__main__':
    unittest.main()
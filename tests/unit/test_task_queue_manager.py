# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Unit tests for Task Queue Manager
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime, timedelta, timezone
import uuid

from task_queue_manager import TaskQueueManager
from models import CaptionGenerationTask, TaskStatus, User, UserRole, CaptionGenerationSettings
from database import DatabaseManager

class TestTaskQueueManager(unittest.TestCase):
    """Test cases for TaskQueueManager"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_db_manager = Mock(spec=DatabaseManager)
        self.mock_session = Mock()
        self.mock_db_manager.get_session.return_value = self.mock_session
        
        self.queue_manager = TaskQueueManager(self.mock_db_manager, max_concurrent_tasks=2)
        
        # Create test task
        self.test_task = CaptionGenerationTask(
            id=str(uuid.uuid4()),
            user_id=1,
            platform_connection_id=1,
            status=TaskStatus.QUEUED
        )
        self.test_task.settings = CaptionGenerationSettings()
    
    def test_enqueue_task_success(self):
        """Test successful task enqueueing"""
        # Configure the mock chain properly for checking existing active tasks
        query_mock = Mock()
        filter_by_mock = Mock()
        filter_mock = Mock()
        
        self.mock_session.query.return_value = query_mock
        query_mock.filter_by.return_value = filter_by_mock
        filter_by_mock.filter.return_value = filter_mock
        filter_mock.first.return_value = None  # No existing active task
        
        # Test enqueueing
        result = self.queue_manager.enqueue_task(self.test_task)
        
        # Verify task was added and committed
        self.mock_session.add.assert_called_once_with(self.test_task)
        self.mock_session.commit.assert_called_once()
        self.assertEqual(result, self.test_task.id)
    
    def test_enqueue_task_user_has_active_task(self):
        """Test enqueueing fails when user has active task"""
        # Mock existing active task
        existing_task = Mock()
        existing_task.id = "existing-task-id"
        
        # Configure the mock chain properly
        query_mock = Mock()
        filter_by_mock = Mock()
        filter_mock = Mock()
        
        self.mock_session.query.return_value = query_mock
        query_mock.filter_by.return_value = filter_by_mock
        filter_by_mock.filter.return_value = filter_mock
        filter_mock.first.return_value = existing_task
        
        # Test enqueueing should raise ValueError
        with self.assertRaises(ValueError) as context:
            self.queue_manager.enqueue_task(self.test_task)
        
        self.assertIn("already has an active task", str(context.exception))
        self.mock_session.add.assert_not_called()
    
    def test_get_task_status_found(self):
        """Test getting task status when task exists"""
        # Mock task found
        mock_task = Mock()
        mock_task.status = TaskStatus.RUNNING
        
        # Configure the mock chain properly
        query_mock = Mock()
        filter_by_mock = Mock()
        
        self.mock_session.query.return_value = query_mock
        query_mock.filter_by.return_value = filter_by_mock
        filter_by_mock.first.return_value = mock_task
        
        result = self.queue_manager.get_task_status("test-task-id")
        
        self.assertEqual(result, TaskStatus.RUNNING)
    
    def test_get_task_status_not_found(self):
        """Test getting task status when task doesn't exist"""
        # Configure the mock chain properly
        query_mock = Mock()
        filter_by_mock = Mock()
        
        self.mock_session.query.return_value = query_mock
        query_mock.filter_by.return_value = filter_by_mock
        filter_by_mock.first.return_value = None
        
        result = self.queue_manager.get_task_status("nonexistent-task-id")
        
        self.assertIsNone(result)
    
    def test_cancel_task_success(self):
        """Test successful task cancellation"""
        # Mock task found and can be cancelled
        mock_task = Mock()
        mock_task.user_id = 1
        mock_task.can_be_cancelled.return_value = True
        mock_task.status = TaskStatus.QUEUED  # Initial status
        
        # Configure the mock chain properly
        query_mock = Mock()
        filter_by_mock = Mock()
        first_mock = Mock()
        
        self.mock_session.query.return_value = query_mock
        query_mock.filter_by.return_value = filter_by_mock
        filter_by_mock.first.return_value = mock_task
        
        result = self.queue_manager.cancel_task("test-task-id", user_id=1)
        
        self.assertTrue(result)
        self.assertEqual(mock_task.status, TaskStatus.CANCELLED)
        self.assertIsNotNone(mock_task.completed_at)
        self.mock_session.commit.assert_called_once()
    
    def test_cancel_task_unauthorized(self):
        """Test task cancellation fails for unauthorized user"""
        # Mock task found but different user
        mock_task = Mock()
        mock_task.user_id = 2
        
        # Configure the mock chain properly
        query_mock = Mock()
        filter_by_mock = Mock()
        
        self.mock_session.query.return_value = query_mock
        query_mock.filter_by.return_value = filter_by_mock
        filter_by_mock.first.return_value = mock_task
        
        result = self.queue_manager.cancel_task("test-task-id", user_id=1)
        
        self.assertFalse(result)
        self.mock_session.commit.assert_not_called()
    
    def test_cancel_task_cannot_be_cancelled(self):
        """Test task cancellation fails when task cannot be cancelled"""
        # Mock task found but cannot be cancelled
        mock_task = Mock()
        mock_task.user_id = 1
        mock_task.can_be_cancelled.return_value = False
        mock_task.status = TaskStatus.COMPLETED  # Task already completed
        
        # Configure the mock chain properly
        query_mock = Mock()
        filter_by_mock = Mock()
        
        self.mock_session.query.return_value = query_mock
        query_mock.filter_by.return_value = filter_by_mock
        filter_by_mock.first.return_value = mock_task
        
        result = self.queue_manager.cancel_task("test-task-id", user_id=1)
        
        self.assertFalse(result)
        self.mock_session.commit.assert_not_called()
    
    def test_get_next_task_at_max_concurrent(self):
        """Test getting next task when at max concurrent tasks"""
        # Configure the mock chain properly
        query_mock = Mock()
        filter_by_mock = Mock()
        
        self.mock_session.query.return_value = query_mock
        query_mock.filter_by.return_value = filter_by_mock
        filter_by_mock.count.return_value = 2  # At max concurrent tasks
        
        result = self.queue_manager.get_next_task()
        
        self.assertIsNone(result)
    
    def test_get_next_task_success(self):
        """Test successful next task retrieval"""
        # Create a proper mock task with all required attributes
        mock_task = Mock()
        mock_task.id = "next-task-id"
        mock_task.user_id = 1
        mock_task.platform_connection_id = 1
        mock_task.status = TaskStatus.QUEUED
        mock_task.created_at = datetime.now(timezone.utc)
        mock_task.started_at = None
        mock_task.settings = CaptionGenerationSettings()
        
        # Configure the mock chain for counting running tasks
        count_query_mock = Mock()
        count_filter_by_mock = Mock()
        count_filter_by_mock.count.return_value = 1  # Not at max concurrent tasks
        count_query_mock.filter_by.return_value = count_filter_by_mock
        
        # Configure the mock chain for finding queued tasks
        task_query_mock = Mock()
        join_mock = Mock()
        filter_mock = Mock()
        order_by_mock = Mock()
        first_mock = Mock()
        
        task_query_mock.join.return_value = join_mock
        join_mock.filter.return_value = filter_mock
        filter_mock.order_by.return_value = order_by_mock
        order_by_mock.first.return_value = mock_task
        
        # Configure session.query to return different mocks for different calls
        query_call_count = 0
        def query_side_effect(*args):
            nonlocal query_call_count
            query_call_count += 1
            if query_call_count == 1:
                return count_query_mock  # First call for counting running tasks
            else:
                return task_query_mock   # Second call for finding queued tasks
        
        self.mock_session.query.side_effect = query_side_effect
        
        result = self.queue_manager.get_next_task()
        
        # The result should be a new CaptionGenerationTask instance, not the mock
        self.assertIsInstance(result, CaptionGenerationTask)
        self.assertEqual(result.id, "next-task-id")
        self.assertEqual(result.user_id, 1)
        self.assertEqual(result.platform_connection_id, 1)
        self.assertEqual(result.status, TaskStatus.RUNNING)
        self.assertIsNotNone(result.started_at)
        
        # Verify the original mock task was updated
        self.assertEqual(mock_task.status, TaskStatus.RUNNING)
        self.assertIsNotNone(mock_task.started_at)
        self.mock_session.commit.assert_called()
    
    def test_complete_task_success(self):
        """Test successful task completion"""
        # Mock task found
        mock_task = Mock()
        mock_task.status = TaskStatus.RUNNING  # Initial status
        
        # Configure the mock chain properly
        query_mock = Mock()
        filter_by_mock = Mock()
        
        self.mock_session.query.return_value = query_mock
        query_mock.filter_by.return_value = filter_by_mock
        filter_by_mock.first.return_value = mock_task
        
        result = self.queue_manager.complete_task("test-task-id", success=True)
        
        self.assertTrue(result)
        self.assertEqual(mock_task.status, TaskStatus.COMPLETED)
        self.assertIsNotNone(mock_task.completed_at)
        self.mock_session.commit.assert_called_once()
    
    def test_complete_task_with_error(self):
        """Test task completion with error"""
        # Mock task found
        mock_task = Mock()
        mock_task.status = TaskStatus.RUNNING  # Initial status
        
        # Configure the mock chain properly
        query_mock = Mock()
        filter_by_mock = Mock()
        
        self.mock_session.query.return_value = query_mock
        query_mock.filter_by.return_value = filter_by_mock
        filter_by_mock.first.return_value = mock_task
        
        error_message = "Test error"
        result = self.queue_manager.complete_task("test-task-id", success=False, error_message=error_message)
        
        self.assertTrue(result)
        self.assertEqual(mock_task.status, TaskStatus.FAILED)
        self.assertEqual(mock_task.error_message, error_message)
        self.mock_session.commit.assert_called_once()
    
    def test_complete_task_not_found(self):
        """Test task completion fails when task doesn't exist"""
        # Mock task not found
        query_mock = Mock()
        filter_by_mock = Mock()
        
        self.mock_session.query.return_value = query_mock
        query_mock.filter_by.return_value = filter_by_mock
        filter_by_mock.first.return_value = None
        
        result = self.queue_manager.complete_task("nonexistent-task-id", success=True)
        
        self.assertFalse(result)
        self.mock_session.commit.assert_not_called()
    
    def test_cancel_task_not_found(self):
        """Test task cancellation fails when task doesn't exist"""
        # Mock task not found
        query_mock = Mock()
        filter_by_mock = Mock()
        
        self.mock_session.query.return_value = query_mock
        query_mock.filter_by.return_value = filter_by_mock
        filter_by_mock.first.return_value = None
        
        result = self.queue_manager.cancel_task("nonexistent-task-id", user_id=1)
        
        self.assertFalse(result)
        self.mock_session.commit.assert_not_called()
    
    def test_cancel_task_database_error(self):
        """Test task cancellation handles database errors gracefully"""
        from sqlalchemy.exc import SQLAlchemyError
        
        # Mock database error
        self.mock_session.query.side_effect = SQLAlchemyError("Database connection failed")
        
        result = self.queue_manager.cancel_task("test-task-id", user_id=1)
        
        self.assertFalse(result)
        self.mock_session.rollback.assert_called_once()
    
    def test_complete_task_database_error(self):
        """Test task completion handles database errors gracefully"""
        from sqlalchemy.exc import SQLAlchemyError
        
        # Mock database error
        self.mock_session.query.side_effect = SQLAlchemyError("Database connection failed")
        
        result = self.queue_manager.complete_task("test-task-id", success=True)
        
        self.assertFalse(result)
        self.mock_session.rollback.assert_called_once()
    
    def test_enqueue_task_database_error(self):
        """Test task enqueueing handles database errors gracefully"""
        from sqlalchemy.exc import SQLAlchemyError
        
        # Mock successful check for existing tasks, but error on add
        query_mock = Mock()
        filter_by_mock = Mock()
        filter_mock = Mock()
        
        self.mock_session.query.return_value = query_mock
        query_mock.filter_by.return_value = filter_by_mock
        filter_by_mock.filter.return_value = filter_mock
        filter_mock.first.return_value = None  # No existing task
        
        # Mock database error on add
        self.mock_session.add.side_effect = SQLAlchemyError("Database connection failed")
        
        with self.assertRaises(SQLAlchemyError):
            self.queue_manager.enqueue_task(self.test_task)
        
        self.mock_session.rollback.assert_called_once()
    
    def test_cleanup_completed_tasks(self):
        """Test cleanup of old completed tasks"""
        # Mock old tasks found
        old_task1 = Mock()
        old_task2 = Mock()
        old_tasks = [old_task1, old_task2]
        
        query_mock = self.mock_session.query.return_value
        query_mock.filter.return_value.all.return_value = old_tasks
        
        result = self.queue_manager.cleanup_completed_tasks(older_than_hours=24)
        
        self.assertEqual(result, 2)
        self.mock_session.delete.assert_any_call(old_task1)
        self.mock_session.delete.assert_any_call(old_task2)
        self.mock_session.commit.assert_called_once()
    
    def test_get_user_active_task(self):
        """Test getting user's active task"""
        # Mock active task found
        mock_task = Mock()
        
        # Configure the mock chain properly
        query_mock = Mock()
        filter_by_mock = Mock()
        filter_mock = Mock()
        
        self.mock_session.query.return_value = query_mock
        query_mock.filter_by.return_value = filter_by_mock
        filter_by_mock.filter.return_value = filter_mock
        filter_mock.first.return_value = mock_task
        
        result = self.queue_manager.get_user_active_task(user_id=1)
        
        self.assertEqual(result, mock_task)
        self.mock_session.expunge.assert_called_once_with(mock_task)
    
    def test_get_queue_stats(self):
        """Test getting queue statistics"""
        # Mock counts for different statuses
        count_side_effects = [1, 2, 3, 0, 1]  # queued, running, completed, failed, cancelled
        self.mock_session.query.return_value.filter_by.return_value.count.side_effect = count_side_effects
        
        result = self.queue_manager.get_queue_stats()
        
        expected = {
            'queued': 1,
            'running': 2,
            'completed': 3,
            'failed': 0,
            'cancelled': 1,
            'total': 7,
            'active': 3
        }
        self.assertEqual(result, expected)
    
    def test_get_user_task_history(self):
        """Test getting user task history"""
        # Mock task history
        mock_tasks = [Mock(), Mock()]
        
        # Configure the mock chain properly
        query_mock = Mock()
        filter_by_mock = Mock()
        order_by_mock = Mock()
        limit_mock = Mock()
        
        self.mock_session.query.return_value = query_mock
        query_mock.filter_by.return_value = filter_by_mock
        filter_by_mock.order_by.return_value = order_by_mock
        order_by_mock.limit.return_value = limit_mock
        limit_mock.all.return_value = mock_tasks
        
        result = self.queue_manager.get_user_task_history(user_id=1, limit=10)
        
        self.assertEqual(result, mock_tasks)
        # Verify tasks were detached from session
        for task in mock_tasks:
            self.mock_session.expunge.assert_any_call(task)
    
    def test_get_task_status_database_error(self):
        """Test get task status handles database errors gracefully"""
        from sqlalchemy.exc import SQLAlchemyError
        
        # Mock database error
        self.mock_session.query.side_effect = SQLAlchemyError("Database connection failed")
        
        result = self.queue_manager.get_task_status("test-task-id")
        
        self.assertIsNone(result)
    
    def test_get_next_task_database_error(self):
        """Test get next task handles database errors gracefully"""
        from sqlalchemy.exc import SQLAlchemyError
        
        # Mock database error
        self.mock_session.query.side_effect = SQLAlchemyError("Database connection failed")
        
        result = self.queue_manager.get_next_task()
        
        self.assertIsNone(result)
        self.mock_session.rollback.assert_called_once()
    
    def test_task_ownership_validation(self):
        """Test that task ownership is properly validated"""
        # Create a task with specific user ID
        task_with_owner = CaptionGenerationTask(
            id=str(uuid.uuid4()),
            user_id=123,  # Specific user ID
            platform_connection_id=1,
            status=TaskStatus.QUEUED
        )
        task_with_owner.settings = CaptionGenerationSettings()
        
        # Mock task found
        mock_task = Mock()
        mock_task.user_id = 123
        mock_task.can_be_cancelled.return_value = True
        mock_task.status = TaskStatus.QUEUED
        
        # Configure the mock chain properly
        query_mock = Mock()
        filter_by_mock = Mock()
        
        self.mock_session.query.return_value = query_mock
        query_mock.filter_by.return_value = filter_by_mock
        filter_by_mock.first.return_value = mock_task
        
        # Test cancellation by correct user
        result = self.queue_manager.cancel_task("test-task-id", user_id=123)
        self.assertTrue(result)
        
        # Reset mock
        self.mock_session.reset_mock()
        mock_task.reset_mock()
        mock_task.user_id = 123
        mock_task.can_be_cancelled.return_value = True
        mock_task.status = TaskStatus.QUEUED
        
        # Configure mock chain again
        self.mock_session.query.return_value = query_mock
        query_mock.filter_by.return_value = filter_by_mock
        filter_by_mock.first.return_value = mock_task
        
        # Test cancellation by wrong user
        result = self.queue_manager.cancel_task("test-task-id", user_id=456)
        self.assertFalse(result)

if __name__ == '__main__':
    unittest.main()
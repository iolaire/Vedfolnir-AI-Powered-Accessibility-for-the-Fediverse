# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Unit tests for Task Queue Manager
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
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
        # Mock no existing active task
        self.mock_session.query.return_value.filter_by.return_value.filter.return_value.first.return_value = None
        
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
        self.mock_session.query.return_value.filter_by.return_value.filter.return_value.first.return_value = existing_task
        
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
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = mock_task
        
        result = self.queue_manager.get_task_status("test-task-id")
        
        self.assertEqual(result, TaskStatus.RUNNING)
    
    def test_get_task_status_not_found(self):
        """Test getting task status when task doesn't exist"""
        # Mock task not found
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = None
        
        result = self.queue_manager.get_task_status("nonexistent-task-id")
        
        self.assertIsNone(result)
    
    def test_cancel_task_success(self):
        """Test successful task cancellation"""
        # Mock task found and can be cancelled
        mock_task = Mock()
        mock_task.user_id = 1
        mock_task.can_be_cancelled.return_value = True
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = mock_task
        
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
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = mock_task
        
        result = self.queue_manager.cancel_task("test-task-id", user_id=1)
        
        self.assertFalse(result)
        self.mock_session.commit.assert_not_called()
    
    def test_cancel_task_cannot_be_cancelled(self):
        """Test task cancellation fails when task cannot be cancelled"""
        # Mock task found but cannot be cancelled
        mock_task = Mock()
        mock_task.user_id = 1
        mock_task.can_be_cancelled.return_value = False
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = mock_task
        
        result = self.queue_manager.cancel_task("test-task-id", user_id=1)
        
        self.assertFalse(result)
        self.mock_session.commit.assert_not_called()
    
    def test_get_next_task_at_max_concurrent(self):
        """Test getting next task when at max concurrent tasks"""
        # Mock running tasks at max
        self.mock_session.query.return_value.filter_by.return_value.count.return_value = 2
        
        result = self.queue_manager.get_next_task()
        
        self.assertIsNone(result)
    
    def test_get_next_task_success(self):
        """Test successful next task retrieval"""
        # Mock not at max concurrent tasks
        query_mock = self.mock_session.query.return_value
        query_mock.filter_by.return_value.count.return_value = 1
        
        # Mock queued task found
        mock_task = Mock()
        mock_task.id = "next-task-id"
        query_mock.join.return_value.filter.return_value.order_by.return_value.first.return_value = mock_task
        
        result = self.queue_manager.get_next_task()
        
        self.assertEqual(result, mock_task)
        self.assertEqual(mock_task.status, TaskStatus.RUNNING)
        self.assertIsNotNone(mock_task.started_at)
        self.mock_session.commit.assert_called()
    
    def test_complete_task_success(self):
        """Test successful task completion"""
        # Mock task found
        mock_task = Mock()
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = mock_task
        
        result = self.queue_manager.complete_task("test-task-id", success=True)
        
        self.assertTrue(result)
        self.assertEqual(mock_task.status, TaskStatus.COMPLETED)
        self.assertIsNotNone(mock_task.completed_at)
        self.mock_session.commit.assert_called_once()
    
    def test_complete_task_with_error(self):
        """Test task completion with error"""
        # Mock task found
        mock_task = Mock()
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = mock_task
        
        error_message = "Test error"
        result = self.queue_manager.complete_task("test-task-id", success=False, error_message=error_message)
        
        self.assertTrue(result)
        self.assertEqual(mock_task.status, TaskStatus.FAILED)
        self.assertEqual(mock_task.error_message, error_message)
        self.mock_session.commit.assert_called_once()
    
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
        query_mock = self.mock_session.query.return_value
        query_mock.filter_by.return_value.filter.return_value.first.return_value = mock_task
        
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
        query_mock = self.mock_session.query.return_value
        query_mock.filter_by.return_value.order_by.return_value.limit.return_value.all.return_value = mock_tasks
        
        result = self.queue_manager.get_user_task_history(user_id=1, limit=10)
        
        self.assertEqual(result, mock_tasks)
        # Verify tasks were detached from session
        for task in mock_tasks:
            self.mock_session.expunge.assert_any_call(task)

if __name__ == '__main__':
    unittest.main()
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Refactored Task Queue Manager Tests Using Standardized Mock Configurations

This demonstrates how to refactor existing tests to use the standardized mock
configurations for better reliability and maintainability.
"""

import unittest
from unittest.mock import patch
from datetime import datetime, timezone
import uuid

from task_queue_manager import TaskQueueManager
from models import CaptionGenerationTask, TaskStatus, User, UserRole, CaptionGenerationSettings

# Import standardized mock helpers
from tests.test_helpers import (
    DatabaseMockHelper,
    StandardizedMockFactory,
    QueryMockBuilder
)


class TestTaskQueueManagerRefactored(unittest.TestCase):
    """Refactored test cases using standardized mock configurations"""
    
    def setUp(self):
        """Set up test fixtures with standardized mocks"""
        # Create standardized database mocks
        self.session_mock = DatabaseMockHelper.create_session_mock()
        self.db_manager_mock = DatabaseMockHelper.create_database_manager_mock(self.session_mock)
        
        self.queue_manager = TaskQueueManager(self.db_manager_mock, max_concurrent_tasks=2)
        
        # Create standardized task mock
        self.test_task = StandardizedMockFactory.create_task_mock(
            task_id=str(uuid.uuid4()),
            user_id=1,
            status=TaskStatus.QUEUED
        )
        # Add settings attribute that the real task would have
        self.test_task.settings = CaptionGenerationSettings()
    
    def test_enqueue_task_success_refactored(self):
        """Test successful task enqueueing using standardized mocks"""
        # Use QueryMockBuilder for clean query chain configuration
        query_mock = (QueryMockBuilder()
                     .filter_by()
                     .filter()
                     .first(None))  # No existing active task
        
        self.session_mock.query.return_value = query_mock
        
        # Test enqueueing
        result = self.queue_manager.enqueue_task(self.test_task)
        
        # Verify task was added and committed
        self.session_mock.add.assert_called_once_with(self.test_task)
        self.session_mock.commit.assert_called_once()
        self.assertEqual(result, self.test_task.id)
    
    def test_enqueue_task_user_has_active_task_refactored(self):
        """Test enqueueing fails when user has active task using standardized mocks"""
        # Create existing task mock
        existing_task = StandardizedMockFactory.create_task_mock(
            task_id="existing-task-id",
            user_id=1,
            status=TaskStatus.RUNNING
        )
        
        # Use QueryMockBuilder for clean configuration
        query_mock = (QueryMockBuilder()
                     .filter_by()
                     .filter()
                     .first(existing_task))  # Return existing task
        
        self.session_mock.query.return_value = query_mock
        
        # Test enqueueing should raise ValueError
        with self.assertRaises(ValueError) as context:
            self.queue_manager.enqueue_task(self.test_task)
        
        self.assertIn("already has an active task", str(context.exception))
        self.session_mock.add.assert_not_called()
    
    def test_get_task_status_found_refactored(self):
        """Test getting task status when task exists using standardized mocks"""
        # Create task mock with specific status
        task_mock = StandardizedMockFactory.create_task_mock(
            task_id="test-task-id",
            status=TaskStatus.RUNNING
        )
        
        # Use QueryMockBuilder for clean configuration
        query_mock = (QueryMockBuilder()
                     .filter_by()
                     .first(task_mock))
        
        self.session_mock.query.return_value = query_mock
        
        result = self.queue_manager.get_task_status("test-task-id")
        
        self.assertEqual(result, TaskStatus.RUNNING)
    
    def test_get_task_status_not_found_refactored(self):
        """Test getting task status when task doesn't exist using standardized mocks"""
        # Use QueryMockBuilder for clean configuration
        query_mock = (QueryMockBuilder()
                     .filter_by()
                     .first(None))  # No task found
        
        self.session_mock.query.return_value = query_mock
        
        result = self.queue_manager.get_task_status("nonexistent-task-id")
        
        self.assertIsNone(result)
    
    def test_cancel_task_success_refactored(self):
        """Test successful task cancellation using standardized mocks"""
        # Create cancellable task mock
        task_mock = StandardizedMockFactory.create_task_mock(
            task_id="test-task-id",
            user_id=1,
            status=TaskStatus.QUEUED,
            can_be_cancelled=True
        )
        
        # Use QueryMockBuilder for clean configuration
        query_mock = (QueryMockBuilder()
                     .filter_by()
                     .first(task_mock))
        
        self.session_mock.query.return_value = query_mock
        
        result = self.queue_manager.cancel_task("test-task-id", user_id=1)
        
        self.assertTrue(result)
        self.assertEqual(task_mock.status, TaskStatus.CANCELLED)
        self.assertIsNotNone(task_mock.completed_at)
        self.session_mock.commit.assert_called_once()
    
    def test_cancel_task_unauthorized_refactored(self):
        """Test task cancellation fails for unauthorized user using standardized mocks"""
        # Create task owned by different user
        task_mock = StandardizedMockFactory.create_task_mock(
            task_id="test-task-id",
            user_id=2,  # Different user
            status=TaskStatus.QUEUED
        )
        
        # Use QueryMockBuilder for clean configuration
        query_mock = (QueryMockBuilder()
                     .filter_by()
                     .first(task_mock))
        
        self.session_mock.query.return_value = query_mock
        
        result = self.queue_manager.cancel_task("test-task-id", user_id=1)
        
        self.assertFalse(result)
        self.session_mock.commit.assert_not_called()
    
    def test_get_next_task_at_max_concurrent_refactored(self):
        """Test getting next task when at max concurrent tasks using standardized mocks"""
        # Use QueryMockBuilder for clean configuration
        query_mock = (QueryMockBuilder()
                     .filter_by()
                     .count(2))  # At max concurrent tasks
        
        self.session_mock.query.return_value = query_mock
        
        result = self.queue_manager.get_next_task()
        
        self.assertIsNone(result)
    
    def test_get_next_task_success_refactored(self):
        """Test successful next task retrieval using standardized mocks"""
        # Create task mock for queued task
        queued_task = StandardizedMockFactory.create_task_mock(
            task_id="next-task-id",
            user_id=1,
            status=TaskStatus.QUEUED
        )
        queued_task.settings = CaptionGenerationSettings()
        
        # Configure session.query to handle multiple calls
        def query_side_effect(model):
            if hasattr(model, '__name__') and 'Task' in model.__name__:
                # First call: count running tasks
                if not hasattr(query_side_effect, 'call_count'):
                    query_side_effect.call_count = 0
                query_side_effect.call_count += 1
                
                if query_side_effect.call_count == 1:
                    # Return count query for running tasks
                    return (QueryMockBuilder()
                           .filter_by()
                           .count(1))  # Not at max concurrent
                else:
                    # Return query for finding queued tasks
                    return (QueryMockBuilder()
                           .join()
                           .filter()
                           .order_by()
                           .first(queued_task))
            else:
                return DatabaseMockHelper.create_query_chain_mock()
        
        self.session_mock.query.side_effect = query_side_effect
        
        result = self.queue_manager.get_next_task()
        
        # Verify result is a new task instance with updated status
        self.assertIsInstance(result, CaptionGenerationTask)
        self.assertEqual(result.id, "next-task-id")
        self.assertEqual(result.status, TaskStatus.RUNNING)
        self.assertIsNotNone(result.started_at)
        
        # Verify original mock was updated
        self.assertEqual(queued_task.status, TaskStatus.RUNNING)
        self.session_mock.commit.assert_called()
    
    def test_complete_task_success_refactored(self):
        """Test successful task completion using standardized mocks"""
        # Create running task mock
        task_mock = StandardizedMockFactory.create_task_mock(
            task_id="test-task-id",
            status=TaskStatus.RUNNING
        )
        
        # Use QueryMockBuilder for clean configuration
        query_mock = (QueryMockBuilder()
                     .filter_by()
                     .first(task_mock))
        
        self.session_mock.query.return_value = query_mock
        
        result = self.queue_manager.complete_task("test-task-id", success=True)
        
        self.assertTrue(result)
        self.assertEqual(task_mock.status, TaskStatus.COMPLETED)
        self.assertIsNotNone(task_mock.completed_at)
        self.session_mock.commit.assert_called_once()
    
    def test_complete_task_with_error_refactored(self):
        """Test task completion with error using standardized mocks"""
        # Create running task mock
        task_mock = StandardizedMockFactory.create_task_mock(
            task_id="test-task-id",
            status=TaskStatus.RUNNING
        )
        
        # Use QueryMockBuilder for clean configuration
        query_mock = (QueryMockBuilder()
                     .filter_by()
                     .first(task_mock))
        
        self.session_mock.query.return_value = query_mock
        
        error_message = "Test error"
        result = self.queue_manager.complete_task("test-task-id", success=False, error_message=error_message)
        
        self.assertTrue(result)
        self.assertEqual(task_mock.status, TaskStatus.FAILED)
        self.assertEqual(task_mock.error_message, error_message)
        self.session_mock.commit.assert_called_once()
    
    def test_database_error_handling_refactored(self):
        """Test database error handling using standardized mocks"""
        from sqlalchemy.exc import SQLAlchemyError
        
        # Configure session to raise database error
        self.session_mock.query.side_effect = SQLAlchemyError("Database connection failed")
        
        result = self.queue_manager.cancel_task("test-task-id", user_id=1)
        
        self.assertFalse(result)
        self.session_mock.rollback.assert_called_once()
    
    def test_cleanup_completed_tasks_refactored(self):
        """Test cleanup of old completed tasks using standardized mocks"""
        # Create old task mocks
        old_task1 = StandardizedMockFactory.create_task_mock(
            task_id="old-task-1",
            status=TaskStatus.COMPLETED
        )
        old_task2 = StandardizedMockFactory.create_task_mock(
            task_id="old-task-2", 
            status=TaskStatus.COMPLETED
        )
        old_tasks = [old_task1, old_task2]
        
        # Use QueryMockBuilder for clean configuration
        query_mock = (QueryMockBuilder()
                     .filter()
                     .all(old_tasks))
        
        self.session_mock.query.return_value = query_mock
        
        result = self.queue_manager.cleanup_completed_tasks(older_than_hours=24)
        
        self.assertEqual(result, 2)
        self.session_mock.delete.assert_any_call(old_task1)
        self.session_mock.delete.assert_any_call(old_task2)
        self.session_mock.commit.assert_called_once()
    
    def test_get_queue_stats_refactored(self):
        """Test getting queue statistics using standardized mocks"""
        # Configure different count results for each status
        count_results = [1, 2, 3, 0, 1]  # queued, running, completed, failed, cancelled
        
        def query_side_effect(model):
            if not hasattr(query_side_effect, 'call_count'):
                query_side_effect.call_count = 0
            
            count = count_results[query_side_effect.call_count]
            query_side_effect.call_count += 1
            
            return (QueryMockBuilder()
                   .filter_by()
                   .count(count))
        
        self.session_mock.query.side_effect = query_side_effect
        
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


if __name__ == '__main__':
    unittest.main()
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Unit tests for Progress Tracker
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
import uuid

from progress_tracker import ProgressTracker, ProgressStatus
from models import CaptionGenerationTask, TaskStatus, GenerationResults
from database import DatabaseManager

class TestProgressTracker(unittest.TestCase):
    """Test cases for ProgressTracker"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_db_manager = Mock(spec=DatabaseManager)
        self.mock_session = Mock()
        self.mock_db_manager.get_session.return_value = self.mock_session
        
        self.progress_tracker = ProgressTracker(self.mock_db_manager)
        
        # Create test task
        self.test_task = Mock(spec=CaptionGenerationTask)
        self.test_task.id = str(uuid.uuid4())
        self.test_task.user_id = 1
        self.test_task.status = TaskStatus.RUNNING
        self.test_task.current_step = "Processing"
        self.test_task.progress_percent = 50
        self.test_task.started_at = datetime.now(timezone.utc)
        self.test_task.created_at = datetime.now(timezone.utc)
        self.test_task.error_message = None
    
    def test_create_progress_session_success(self):
        """Test successful progress session creation"""
        # Mock task found
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = self.test_task
        
        result = self.progress_tracker.create_progress_session(self.test_task.id, self.test_task.user_id)
        
        self.assertEqual(result, self.test_task.id)
    
    def test_create_progress_session_unauthorized(self):
        """Test progress session creation fails for unauthorized user"""
        # Mock task not found (due to user mismatch)
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = None
        
        with self.assertRaises(ValueError) as context:
            self.progress_tracker.create_progress_session(self.test_task.id, 999)
        
        self.assertIn("not found or user", str(context.exception))
    
    def test_update_progress_success(self):
        """Test successful progress update"""
        # Mock task found
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = self.test_task
        
        result = self.progress_tracker.update_progress(
            self.test_task.id, 
            "Processing images", 
            75, 
            {"images_processed": 10}
        )
        
        self.assertTrue(result)
        self.assertEqual(self.test_task.current_step, "Processing images")
        self.assertEqual(self.test_task.progress_percent, 75)
        self.mock_session.commit.assert_called_once()
    
    def test_update_progress_task_not_found(self):
        """Test progress update fails when task not found"""
        # Mock task not found
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = None
        
        result = self.progress_tracker.update_progress("nonexistent-task", "Step", 50)
        
        self.assertFalse(result)
        self.mock_session.commit.assert_not_called()
    
    def test_update_progress_clamps_percentage(self):
        """Test progress percentage is clamped to 0-100 range"""
        # Mock task found
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = self.test_task
        
        # Test negative percentage
        self.progress_tracker.update_progress(self.test_task.id, "Step", -10)
        self.assertEqual(self.test_task.progress_percent, 0)
        
        # Test percentage over 100
        self.progress_tracker.update_progress(self.test_task.id, "Step", 150)
        self.assertEqual(self.test_task.progress_percent, 100)
    
    def test_get_progress_success(self):
        """Test successful progress retrieval"""
        # Mock task found - need to mock the chained filter_by calls
        query_mock = self.mock_session.query.return_value
        query_mock.filter_by.return_value.filter_by.return_value.first.return_value = self.test_task
        
        result = self.progress_tracker.get_progress(self.test_task.id, self.test_task.user_id)
        
        self.assertIsInstance(result, ProgressStatus)
        self.assertEqual(result.task_id, self.test_task.id)
        self.assertEqual(result.user_id, self.test_task.user_id)
        self.assertEqual(result.current_step, self.test_task.current_step)
        self.assertEqual(result.progress_percent, self.test_task.progress_percent)
    
    def test_get_progress_unauthorized(self):
        """Test progress retrieval fails for unauthorized user"""
        # Mock task not found (due to user filter)
        self.mock_session.query.return_value.filter_by.return_value.filter_by.return_value.first.return_value = None
        
        result = self.progress_tracker.get_progress(self.test_task.id, 999)
        
        self.assertIsNone(result)
    
    def test_get_progress_no_user_filter(self):
        """Test progress retrieval without user authorization"""
        # Mock task found
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = self.test_task
        
        result = self.progress_tracker.get_progress(self.test_task.id)
        
        self.assertIsInstance(result, ProgressStatus)
        self.assertEqual(result.task_id, self.test_task.id)
    
    def test_complete_progress_success(self):
        """Test successful progress completion"""
        # Mock task found
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = self.test_task
        
        # Create test results
        results = GenerationResults(
            task_id=self.test_task.id,
            posts_processed=5,
            images_processed=10,
            captions_generated=8
        )
        
        result = self.progress_tracker.complete_progress(self.test_task.id, results)
        
        self.assertTrue(result)
        self.assertEqual(self.test_task.current_step, "Completed")
        self.assertEqual(self.test_task.progress_percent, 100)
        self.assertEqual(self.test_task.results, results)
        self.mock_session.commit.assert_called_once()
    
    def test_complete_progress_task_not_found(self):
        """Test progress completion fails when task not found"""
        # Mock task not found
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = None
        
        results = GenerationResults(task_id="nonexistent")
        result = self.progress_tracker.complete_progress("nonexistent", results)
        
        self.assertFalse(result)
        self.mock_session.commit.assert_not_called()
    
    def test_register_callback(self):
        """Test callback registration"""
        callback = Mock()
        
        self.progress_tracker.register_callback(self.test_task.id, callback)
        
        # Verify callback is stored
        self.assertIn(self.test_task.id, self.progress_tracker._progress_callbacks)
        self.assertIn(callback, self.progress_tracker._progress_callbacks[self.test_task.id])
    
    def test_unregister_callback(self):
        """Test callback unregistration"""
        callback = Mock()
        
        # Register then unregister
        self.progress_tracker.register_callback(self.test_task.id, callback)
        self.progress_tracker.unregister_callback(self.test_task.id, callback)
        
        # Verify callback is removed
        self.assertNotIn(self.test_task.id, self.progress_tracker._progress_callbacks)
    
    def test_cleanup_callbacks(self):
        """Test callback cleanup"""
        callback1 = Mock()
        callback2 = Mock()
        
        # Register callbacks
        self.progress_tracker.register_callback(self.test_task.id, callback1)
        self.progress_tracker.register_callback(self.test_task.id, callback2)
        
        # Cleanup
        self.progress_tracker.cleanup_callbacks(self.test_task.id)
        
        # Verify all callbacks removed
        self.assertNotIn(self.test_task.id, self.progress_tracker._progress_callbacks)
    
    def test_notify_callbacks(self):
        """Test callback notification"""
        callback1 = Mock()
        callback2 = Mock()
        
        # Register callbacks
        self.progress_tracker.register_callback(self.test_task.id, callback1)
        self.progress_tracker.register_callback(self.test_task.id, callback2)
        
        # Create progress status
        progress_status = ProgressStatus(
            task_id=self.test_task.id,
            user_id=self.test_task.user_id,
            current_step="Test step",
            progress_percent=50,
            details={}
        )
        
        # Notify callbacks
        self.progress_tracker._notify_callbacks(self.test_task.id, progress_status)
        
        # Verify callbacks were called
        callback1.assert_called_once_with(progress_status)
        callback2.assert_called_once_with(progress_status)
    
    def test_notify_callbacks_handles_exceptions(self):
        """Test callback notification handles exceptions gracefully"""
        callback_good = Mock()
        callback_bad = Mock(side_effect=Exception("Test error"))
        
        # Register callbacks
        self.progress_tracker.register_callback(self.test_task.id, callback_good)
        self.progress_tracker.register_callback(self.test_task.id, callback_bad)
        
        # Create progress status
        progress_status = ProgressStatus(
            task_id=self.test_task.id,
            user_id=self.test_task.user_id,
            current_step="Test step",
            progress_percent=50,
            details={}
        )
        
        # Notify callbacks - should not raise exception
        self.progress_tracker._notify_callbacks(self.test_task.id, progress_status)
        
        # Verify good callback was still called
        callback_good.assert_called_once_with(progress_status)
    
    def test_get_active_progress_sessions(self):
        """Test getting active progress sessions"""
        # Mock active tasks
        task1 = Mock(spec=CaptionGenerationTask)
        task1.id = "task1"
        task1.user_id = 1
        task1.status = TaskStatus.RUNNING
        task1.current_step = "Processing"
        task1.progress_percent = 50
        task1.started_at = datetime.now(timezone.utc)
        task1.created_at = datetime.now(timezone.utc)
        
        task2 = Mock(spec=CaptionGenerationTask)
        task2.id = "task2"
        task2.user_id = 2
        task2.status = TaskStatus.QUEUED
        task2.current_step = None
        task2.progress_percent = 0
        task2.started_at = None
        task2.created_at = datetime.now(timezone.utc)
        
        self.mock_session.query.return_value.filter.return_value.all.return_value = [task1, task2]
        
        result = self.progress_tracker.get_active_progress_sessions()
        
        self.assertEqual(len(result), 2)
        self.assertIn("task1", result)
        self.assertIn("task2", result)
        self.assertEqual(result["task1"].current_step, "Processing")
        self.assertEqual(result["task2"].current_step, "Initializing")
    
    def test_create_progress_callback(self):
        """Test creating a progress callback function"""
        # Mock task found for update
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = self.test_task
        
        callback = self.progress_tracker.create_progress_callback(self.test_task.id)
        
        # Test the callback
        callback("Test step", 75, {"detail": "value"})
        
        # Verify task was updated
        self.assertEqual(self.test_task.current_step, "Test step")
        self.assertEqual(self.test_task.progress_percent, 75)
    
    def test_progress_status_to_dict(self):
        """Test ProgressStatus to_dict method"""
        progress_status = ProgressStatus(
            task_id="test-task",
            user_id=1,
            current_step="Test step",
            progress_percent=50,
            details={"key": "value"},
            started_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        result = progress_status.to_dict()
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result['task_id'], "test-task")
        self.assertEqual(result['user_id'], 1)
        self.assertEqual(result['current_step'], "Test step")
        self.assertEqual(result['progress_percent'], 50)
        self.assertIn('started_at', result)
        self.assertIn('updated_at', result)

if __name__ == '__main__':
    unittest.main()
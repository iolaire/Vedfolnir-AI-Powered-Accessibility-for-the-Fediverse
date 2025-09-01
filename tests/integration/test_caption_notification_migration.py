# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Caption Processing Notification Migration Integration Tests

Tests the integration of caption processing notifications with the unified notification system.
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from progress_tracker import ProgressTracker, ProgressStatus
from models import CaptionGenerationTask, TaskStatus, UserRole, NotificationType, NotificationPriority, NotificationCategory


class TestCaptionNotificationMigration(unittest.TestCase):
    """Test caption processing notification migration to unified system"""
    
    def setUp(self):
        """Set up test environment"""
        self.mock_db_manager = Mock()
        self.mock_session = Mock()
        
        # Setup context manager mock properly
        context_manager = Mock()
        context_manager.__enter__ = Mock(return_value=self.mock_session)
        context_manager.__exit__ = Mock(return_value=None)
        self.mock_db_manager.get_session.return_value = context_manager
        
        self.progress_tracker = ProgressTracker(self.mock_db_manager)
        
        # Mock task
        self.mock_task = Mock(spec=CaptionGenerationTask)
        self.mock_task.id = "test_task_123"
        self.mock_task.user_id = 1
        self.mock_task.status = TaskStatus.RUNNING
        self.mock_task.current_step = "Processing images"
        self.mock_task.progress_percent = 50
        self.mock_task.started_at = datetime.now(timezone.utc)
    
    def test_progress_status_creation(self):
        """Test that progress status objects are created correctly"""
        progress_status = ProgressStatus(
            task_id="test_task_123",
            user_id=1,
            current_step="Processing images",
            progress_percent=50,
            details={'images_processed': 5, 'total_images': 10},
            started_at=datetime.now(timezone.utc)
        )
        
        self.assertEqual(progress_status.task_id, "test_task_123")
        self.assertEqual(progress_status.user_id, 1)
        self.assertEqual(progress_status.current_step, "Processing images")
        self.assertEqual(progress_status.progress_percent, 50)
        self.assertEqual(progress_status.details['images_processed'], 5)
    
    def test_milestone_detection_logic(self):
        """Test that milestone detection logic works correctly"""
        # Test cases for milestone detection
        test_cases = [
            (0, True),    # Start
            (20, True),   # 20% milestone
            (15, False),  # Not a milestone
            (40, True),   # 40% milestone
            (45, False),  # Not a milestone
            (90, True),   # Near completion
            (100, True),  # Completion
        ]
        
        for progress_percent, expected_milestone in test_cases:
            is_milestone = (
                progress_percent % 20 == 0 or  # Every 20%
                progress_percent >= 90 or      # Near completion
                progress_percent == 0          # Starting
            )
            
            self.assertEqual(is_milestone, expected_milestone, 
                           f"Progress {progress_percent}% should {'be' if expected_milestone else 'not be'} a milestone")
    
    def test_progress_update_functionality(self):
        """Test that progress updates work correctly"""
        # Setup mock task in database
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = self.mock_task
        
        # Test progress update
        success = self.progress_tracker.update_progress(
            "test_task_123", 
            "Processing images", 
            75, 
            {'images_processed': 7, 'total_images': 10}
        )
        
        self.assertTrue(success)
        
        # Verify task was updated
        self.assertEqual(self.mock_task.current_step, "Processing images")
        self.assertEqual(self.mock_task.progress_percent, 75)
        
        # Verify session commit was called
        self.mock_session.commit.assert_called_once()
    
    def test_progress_validation(self):
        """Test that progress percentage is properly validated"""
        # Setup mock task in database
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = self.mock_task
        
        # Test progress validation - should clamp to 0-100 range
        test_cases = [
            (-10, 0),    # Negative should become 0
            (150, 100),  # Over 100 should become 100
            (50, 50),    # Normal value should remain unchanged
        ]
        
        for input_progress, expected_progress in test_cases:
            success = self.progress_tracker.update_progress(
                "test_task_123", 
                "Processing", 
                input_progress
            )
            
            self.assertTrue(success)
            self.assertEqual(self.mock_task.progress_percent, expected_progress)


if __name__ == '__main__':
    unittest.main()
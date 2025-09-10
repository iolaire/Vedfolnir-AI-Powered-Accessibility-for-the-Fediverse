# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for Maintenance Operation Completion Tracker

Tests the operation completion tracking functionality during maintenance mode,
including job monitoring, completion notifications, and statistics tracking.
"""

import unittest
import threading
import time
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone, timedelta

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.services.maintenance.components.maintenance_operation_completion_tracker import (
    MaintenanceOperationCompletionTracker,
    ActiveJobInfo,
    CompletionNotification
)
from models import CaptionGenerationTask, TaskStatus


class TestMaintenanceOperationCompletionTracker(unittest.TestCase):
    """Test cases for MaintenanceOperationCompletionTracker"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_db_manager = Mock()
        self.mock_maintenance_service = Mock()
        
        # Create tracker with short monitoring interval for testing
        self.tracker = MaintenanceOperationCompletionTracker(
            db_manager=self.mock_db_manager,
            maintenance_service=self.mock_maintenance_service,
            monitoring_interval=1  # 1 second for fast testing
        )
    
    def tearDown(self):
        """Clean up after tests"""
        try:
            self.tracker.stop_monitoring()
        except:
            pass
    
    def test_initialization(self):
        """Test tracker initialization"""
        self.assertEqual(self.tracker.db_manager, self.mock_db_manager)
        self.assertEqual(self.tracker.maintenance_service, self.mock_maintenance_service)
        self.assertEqual(self.tracker.monitoring_interval, 1)
        self.assertFalse(self.tracker._monitoring_active)
        self.assertEqual(self.tracker.get_active_jobs_count(), 0)
    
    def test_start_stop_monitoring(self):
        """Test starting and stopping monitoring"""
        # Test start monitoring
        self.tracker.start_monitoring()
        self.assertTrue(self.tracker._monitoring_active)
        self.assertIsNotNone(self.tracker._monitoring_thread)
        
        # Test stop monitoring
        self.tracker.stop_monitoring()
        self.assertFalse(self.tracker._monitoring_active)
        
        # Test starting already active monitoring
        self.tracker._monitoring_active = True
        with patch('maintenance_operation_completion_tracker.logger') as mock_logger:
            self.tracker.start_monitoring()
            mock_logger.warning.assert_called_with("Job monitoring is already active")
    
    def test_get_active_jobs_count(self):
        """Test getting active jobs count"""
        # Initially should be 0
        self.assertEqual(self.tracker.get_active_jobs_count(), 0)
        
        # Add some mock active jobs
        job1 = ActiveJobInfo(
            job_id="job1",
            user_id=1,
            job_type="caption_generation",
            started_at=datetime.now(timezone.utc),
            estimated_completion=None,
            status="running",
            progress_percent=50,
            current_step="processing",
            platform_connection_id=1
        )
        
        job2 = ActiveJobInfo(
            job_id="job2",
            user_id=2,
            job_type="caption_generation",
            started_at=datetime.now(timezone.utc),
            estimated_completion=None,
            status="queued",
            progress_percent=0,
            current_step="waiting",
            platform_connection_id=2
        )
        
        with self.tracker._jobs_lock:
            self.tracker._active_jobs["job1"] = job1
            self.tracker._active_jobs["job2"] = job2
        
        self.assertEqual(self.tracker.get_active_jobs_count(), 2)
    
    def test_get_active_jobs(self):
        """Test getting list of active jobs"""
        # Initially should be empty
        self.assertEqual(len(self.tracker.get_active_jobs()), 0)
        
        # Add mock active job
        job = ActiveJobInfo(
            job_id="test_job",
            user_id=1,
            job_type="caption_generation",
            started_at=datetime.now(timezone.utc),
            estimated_completion=None,
            status="running",
            progress_percent=75,
            current_step="generating",
            platform_connection_id=1
        )
        
        with self.tracker._jobs_lock:
            self.tracker._active_jobs["test_job"] = job
        
        active_jobs = self.tracker.get_active_jobs()
        self.assertEqual(len(active_jobs), 1)
        self.assertEqual(active_jobs[0].job_id, "test_job")
        self.assertEqual(active_jobs[0].progress_percent, 75)
    
    def test_completion_notifications(self):
        """Test completion notification handling"""
        # Create mock completion notification
        notification = CompletionNotification(
            job_id="completed_job",
            user_id=1,
            job_type="caption_generation",
            completion_status="completed",
            completed_at=datetime.now(timezone.utc),
            duration_seconds=120
        )
        
        # Add to completed jobs
        with self.tracker._jobs_lock:
            self.tracker._completed_jobs.append(notification)
        
        # Test getting completed jobs
        completed = self.tracker.get_completed_jobs(limit=10)
        self.assertEqual(len(completed), 1)
        self.assertEqual(completed[0].job_id, "completed_job")
        self.assertEqual(completed[0].duration_seconds, 120)
    
    def test_completion_subscription(self):
        """Test completion notification subscription"""
        callback_called = threading.Event()
        received_notification = None
        
        def test_callback(notification):
            nonlocal received_notification
            received_notification = notification
            callback_called.set()
        
        # Subscribe to completions
        subscription_id = self.tracker.subscribe_to_completions(test_callback)
        self.assertIsNotNone(subscription_id)
        
        # Create and notify completion
        notification = CompletionNotification(
            job_id="test_job",
            user_id=1,
            job_type="caption_generation",
            completion_status="completed",
            completed_at=datetime.now(timezone.utc),
            duration_seconds=60
        )
        
        self.tracker._notify_completion_subscribers(notification)
        
        # Wait for callback
        self.assertTrue(callback_called.wait(timeout=1))
        self.assertIsNotNone(received_notification)
        self.assertEqual(received_notification.job_id, "test_job")
        
        # Test unsubscribe
        self.assertTrue(self.tracker.unsubscribe_from_completions(subscription_id))
        self.assertFalse(self.tracker.unsubscribe_from_completions("nonexistent"))
    
    def test_force_refresh_active_jobs(self):
        """Test force refresh of active jobs from database"""
        # Mock database session and query results
        mock_session = Mock()
        mock_task1 = Mock()
        mock_task1.id = "task1"
        mock_task1.user_id = 1
        mock_task1.status = TaskStatus.RUNNING
        mock_task1.progress_percent = 50
        mock_task1.current_step = "processing"
        mock_task1.platform_connection_id = 1
        mock_task1.started_at = datetime.now(timezone.utc)
        mock_task1.created_at = datetime.now(timezone.utc)
        
        mock_task2 = Mock()
        mock_task2.id = "task2"
        mock_task2.user_id = 2
        mock_task2.status = TaskStatus.QUEUED
        mock_task2.progress_percent = 0
        mock_task2.current_step = None
        mock_task2.platform_connection_id = 2
        mock_task2.started_at = None
        mock_task2.created_at = datetime.now(timezone.utc)
        
        mock_query = Mock()
        mock_query.filter.return_value.all.return_value = [mock_task1, mock_task2]
        mock_session.query.return_value = mock_query
        
        self.mock_db_manager.get_session.return_value.__enter__ = Mock(return_value=mock_session)
        self.mock_db_manager.get_session.return_value.__exit__ = Mock(return_value=None)
        
        # Test force refresh
        count = self.tracker.force_refresh_active_jobs()
        
        self.assertEqual(count, 2)
        self.assertEqual(self.tracker.get_active_jobs_count(), 2)
        self.mock_maintenance_service.update_active_jobs_count.assert_called_with(2)
    
    def test_query_active_jobs(self):
        """Test querying active jobs from database"""
        # Mock database session and query results
        mock_session = Mock()
        mock_task = Mock()
        mock_task.id = "test_task"
        mock_task.user_id = 1
        mock_task.status = TaskStatus.RUNNING
        mock_task.progress_percent = 25
        mock_task.current_step = "analyzing"
        mock_task.platform_connection_id = 1
        mock_task.started_at = datetime.now(timezone.utc) - timedelta(minutes=5)
        mock_task.created_at = datetime.now(timezone.utc) - timedelta(minutes=10)
        
        mock_query = Mock()
        mock_query.filter.return_value.all.return_value = [mock_task]
        mock_session.query.return_value = mock_query
        
        self.mock_db_manager.get_session.return_value.__enter__ = Mock(return_value=mock_session)
        self.mock_db_manager.get_session.return_value.__exit__ = Mock(return_value=None)
        
        # Test query
        active_jobs = self.tracker._query_active_jobs()
        
        self.assertEqual(len(active_jobs), 1)
        job = active_jobs[0]
        self.assertEqual(job.job_id, "test_task")
        self.assertEqual(job.user_id, 1)
        self.assertEqual(job.job_type, "caption_generation")
        self.assertEqual(job.progress_percent, 25)
        self.assertIsNotNone(job.estimated_completion)  # Should be calculated
    
    def test_get_completion_stats(self):
        """Test getting completion statistics"""
        # Add some mock statistics
        with self.tracker._stats_lock:
            self.tracker._stats.update({
                'jobs_completed': 5,
                'jobs_failed': 2,
                'jobs_cancelled': 1,
                'total_completion_time': 600,
                'average_completion_time': 120
            })
        
        # Add mock active job
        job = ActiveJobInfo(
            job_id="active_job",
            user_id=1,
            job_type="caption_generation",
            started_at=datetime.now(timezone.utc),
            estimated_completion=None,
            status="running",
            progress_percent=30,
            current_step="processing",
            platform_connection_id=1
        )
        
        with self.tracker._jobs_lock:
            self.tracker._active_jobs["active_job"] = job
        
        stats = self.tracker.get_completion_stats()
        
        self.assertEqual(stats['jobs_completed'], 5)
        self.assertEqual(stats['jobs_failed'], 2)
        self.assertEqual(stats['current_active_jobs'], 1)
        self.assertIn('caption_generation', stats['active_job_types'])
        self.assertEqual(stats['active_job_types']['caption_generation'], 1)
    
    def test_user_job_filtering(self):
        """Test filtering jobs by user"""
        # Add jobs for different users
        job1 = ActiveJobInfo(
            job_id="user1_job",
            user_id=1,
            job_type="caption_generation",
            started_at=datetime.now(timezone.utc),
            estimated_completion=None,
            status="running",
            progress_percent=40,
            current_step="processing",
            platform_connection_id=1
        )
        
        job2 = ActiveJobInfo(
            job_id="user2_job",
            user_id=2,
            job_type="caption_generation",
            started_at=datetime.now(timezone.utc),
            estimated_completion=None,
            status="queued",
            progress_percent=0,
            current_step="waiting",
            platform_connection_id=2
        )
        
        with self.tracker._jobs_lock:
            self.tracker._active_jobs["user1_job"] = job1
            self.tracker._active_jobs["user2_job"] = job2
        
        # Test getting jobs by user
        user1_jobs = self.tracker.get_jobs_by_user(1)
        self.assertEqual(len(user1_jobs), 1)
        self.assertEqual(user1_jobs[0].job_id, "user1_job")
        
        user2_jobs = self.tracker.get_jobs_by_user(2)
        self.assertEqual(len(user2_jobs), 1)
        self.assertEqual(user2_jobs[0].job_id, "user2_job")
        
        # Test user job activity check
        self.assertTrue(self.tracker.is_user_job_active(1))
        self.assertTrue(self.tracker.is_user_job_active(2))
        self.assertFalse(self.tracker.is_user_job_active(3))
    
    def test_platform_job_filtering(self):
        """Test filtering jobs by platform"""
        # Add jobs for different platforms
        job1 = ActiveJobInfo(
            job_id="platform1_job",
            user_id=1,
            job_type="caption_generation",
            started_at=datetime.now(timezone.utc),
            estimated_completion=None,
            status="running",
            progress_percent=60,
            current_step="processing",
            platform_connection_id=1
        )
        
        job2 = ActiveJobInfo(
            job_id="platform2_job",
            user_id=2,
            job_type="caption_generation",
            started_at=datetime.now(timezone.utc),
            estimated_completion=None,
            status="running",
            progress_percent=30,
            current_step="analyzing",
            platform_connection_id=2
        )
        
        with self.tracker._jobs_lock:
            self.tracker._active_jobs["platform1_job"] = job1
            self.tracker._active_jobs["platform2_job"] = job2
        
        # Test getting jobs by platform
        platform1_jobs = self.tracker.get_jobs_by_platform(1)
        self.assertEqual(len(platform1_jobs), 1)
        self.assertEqual(platform1_jobs[0].job_id, "platform1_job")
        
        platform2_jobs = self.tracker.get_jobs_by_platform(2)
        self.assertEqual(len(platform2_jobs), 1)
        self.assertEqual(platform2_jobs[0].job_id, "platform2_job")
        
        # Test non-existent platform
        platform3_jobs = self.tracker.get_jobs_by_platform(3)
        self.assertEqual(len(platform3_jobs), 0)
    
    def test_longest_running_job(self):
        """Test getting longest running job"""
        # No jobs initially
        self.assertIsNone(self.tracker.get_longest_running_job())
        
        # Add jobs with different start times
        now = datetime.now(timezone.utc)
        job1 = ActiveJobInfo(
            job_id="recent_job",
            user_id=1,
            job_type="caption_generation",
            started_at=now - timedelta(minutes=5),
            estimated_completion=None,
            status="running",
            progress_percent=20,
            current_step="starting",
            platform_connection_id=1
        )
        
        job2 = ActiveJobInfo(
            job_id="old_job",
            user_id=2,
            job_type="caption_generation",
            started_at=now - timedelta(minutes=30),
            estimated_completion=None,
            status="running",
            progress_percent=80,
            current_step="finishing",
            platform_connection_id=2
        )
        
        with self.tracker._jobs_lock:
            self.tracker._active_jobs["recent_job"] = job1
            self.tracker._active_jobs["old_job"] = job2
        
        # Should return the oldest job
        longest_running = self.tracker.get_longest_running_job()
        self.assertIsNotNone(longest_running)
        self.assertEqual(longest_running.job_id, "old_job")
    
    def test_estimated_completion_time(self):
        """Test getting estimated completion time for all jobs"""
        # No jobs initially
        self.assertIsNone(self.tracker.get_estimated_completion_time())
        
        # Add jobs with different completion estimates
        now = datetime.now(timezone.utc)
        job1 = ActiveJobInfo(
            job_id="job1",
            user_id=1,
            job_type="caption_generation",
            started_at=now - timedelta(minutes=5),
            estimated_completion=now + timedelta(minutes=10),
            status="running",
            progress_percent=50,
            current_step="processing",
            platform_connection_id=1
        )
        
        job2 = ActiveJobInfo(
            job_id="job2",
            user_id=2,
            job_type="caption_generation",
            started_at=now - timedelta(minutes=2),
            estimated_completion=now + timedelta(minutes=20),
            status="running",
            progress_percent=25,
            current_step="analyzing",
            platform_connection_id=2
        )
        
        with self.tracker._jobs_lock:
            self.tracker._active_jobs["job1"] = job1
            self.tracker._active_jobs["job2"] = job2
        
        # Should return the latest completion estimate
        estimated_completion = self.tracker.get_estimated_completion_time()
        self.assertIsNotNone(estimated_completion)
        self.assertEqual(estimated_completion, job2.estimated_completion)
    
    def test_cleanup_old_completions(self):
        """Test cleaning up old completion notifications"""
        now = datetime.now(timezone.utc)
        
        # Add old and recent completions
        old_completion = CompletionNotification(
            job_id="old_job",
            user_id=1,
            job_type="caption_generation",
            completion_status="completed",
            completed_at=now - timedelta(hours=25),  # Older than 24 hours
            duration_seconds=120
        )
        
        recent_completion = CompletionNotification(
            job_id="recent_job",
            user_id=2,
            job_type="caption_generation",
            completion_status="completed",
            completed_at=now - timedelta(hours=1),  # Recent
            duration_seconds=90
        )
        
        with self.tracker._jobs_lock:
            self.tracker._completed_jobs.extend([old_completion, recent_completion])
        
        # Clean up old completions (older than 24 hours)
        removed_count = self.tracker.cleanup_old_completions(hours=24)
        
        self.assertEqual(removed_count, 1)
        remaining_completions = self.tracker.get_completed_jobs()
        self.assertEqual(len(remaining_completions), 1)
        self.assertEqual(remaining_completions[0].job_id, "recent_job")
    
    def test_error_handling(self):
        """Test error handling in various methods"""
        # Test with database error
        self.mock_db_manager.get_session.side_effect = Exception("Database error")
        
        # Should handle errors gracefully
        active_jobs = self.tracker._query_active_jobs()
        self.assertEqual(len(active_jobs), 0)
        
        count = self.tracker.force_refresh_active_jobs()
        self.assertEqual(count, 0)
    
    @patch('maintenance_operation_completion_tracker.logger')
    def test_monitoring_loop_error_handling(self, mock_logger):
        """Test error handling in monitoring loop"""
        # Mock database error in _query_active_jobs
        self.mock_db_manager.get_session.side_effect = Exception("Database connection error")
        
        # Call _monitor_active_jobs directly to test error handling
        self.tracker._monitor_active_jobs()
        
        # Should log the error
        mock_logger.error.assert_called()


class TestActiveJobInfo(unittest.TestCase):
    """Test cases for ActiveJobInfo dataclass"""
    
    def test_active_job_info_creation(self):
        """Test creating ActiveJobInfo objects"""
        now = datetime.now(timezone.utc)
        estimated = now + timedelta(minutes=30)
        
        job_info = ActiveJobInfo(
            job_id="test_job",
            user_id=1,
            job_type="caption_generation",
            started_at=now,
            estimated_completion=estimated,
            status="running",
            progress_percent=75,
            current_step="processing images",
            platform_connection_id=1
        )
        
        self.assertEqual(job_info.job_id, "test_job")
        self.assertEqual(job_info.user_id, 1)
        self.assertEqual(job_info.job_type, "caption_generation")
        self.assertEqual(job_info.started_at, now)
        self.assertEqual(job_info.estimated_completion, estimated)
        self.assertEqual(job_info.status, "running")
        self.assertEqual(job_info.progress_percent, 75)
        self.assertEqual(job_info.current_step, "processing images")
        self.assertEqual(job_info.platform_connection_id, 1)


class TestCompletionNotification(unittest.TestCase):
    """Test cases for CompletionNotification dataclass"""
    
    def test_completion_notification_creation(self):
        """Test creating CompletionNotification objects"""
        completed_at = datetime.now(timezone.utc)
        
        notification = CompletionNotification(
            job_id="completed_job",
            user_id=2,
            job_type="caption_generation",
            completion_status="completed",
            completed_at=completed_at,
            duration_seconds=180,
            error_message=None
        )
        
        self.assertEqual(notification.job_id, "completed_job")
        self.assertEqual(notification.user_id, 2)
        self.assertEqual(notification.job_type, "caption_generation")
        self.assertEqual(notification.completion_status, "completed")
        self.assertEqual(notification.completed_at, completed_at)
        self.assertEqual(notification.duration_seconds, 180)
        self.assertIsNone(notification.error_message)
    
    def test_completion_notification_with_error(self):
        """Test creating CompletionNotification with error"""
        completed_at = datetime.now(timezone.utc)
        
        notification = CompletionNotification(
            job_id="failed_job",
            user_id=3,
            job_type="caption_generation",
            completion_status="failed",
            completed_at=completed_at,
            duration_seconds=60,
            error_message="Processing failed due to network error"
        )
        
        self.assertEqual(notification.completion_status, "failed")
        self.assertEqual(notification.error_message, "Processing failed due to network error")


if __name__ == '__main__':
    unittest.main()
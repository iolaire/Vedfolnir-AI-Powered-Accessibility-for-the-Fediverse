# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integration tests for Enhanced Maintenance Mode Service with Completion Tracking

Tests the integration between the enhanced maintenance mode service and the
operation completion tracker, including job monitoring during maintenance.
"""

import unittest
import threading
import time
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone, timedelta

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.services.maintenance.enhanced.enhanced_maintenance_mode_service import (
    EnhancedMaintenanceModeService,
    MaintenanceMode,
    MaintenanceStatus
)
from app.services.maintenance.components.maintenance_operation_completion_tracker import (
    MaintenanceOperationCompletionTracker,
    ActiveJobInfo,
    CompletionNotification
)
from models import CaptionGenerationTask, TaskStatus, User, UserRole


class TestEnhancedMaintenanceModeCompletionTracking(unittest.TestCase):
    """Integration tests for maintenance mode with completion tracking"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_config_service = Mock()
        self.mock_db_manager = Mock()
        
        # Create enhanced maintenance service with database manager
        self.maintenance_service = EnhancedMaintenanceModeService(
            config_service=self.mock_config_service,
            db_manager=self.mock_db_manager
        )
        
        # Mock admin user
        self.admin_user = Mock()
        self.admin_user.role = UserRole.ADMIN
        self.admin_user.id = 1
        self.admin_user.username = "admin"
    
    def tearDown(self):
        """Clean up after tests"""
        try:
            self.maintenance_service.disable_maintenance()
        except:
            pass
    
    def test_maintenance_service_with_completion_tracker_initialization(self):
        """Test that maintenance service initializes completion tracker"""
        # Should have completion tracker if db_manager is provided
        self.assertIsNotNone(self.maintenance_service._completion_tracker)
        self.assertIsInstance(
            self.maintenance_service._completion_tracker,
            MaintenanceOperationCompletionTracker
        )
    
    def test_maintenance_service_without_db_manager(self):
        """Test maintenance service without database manager"""
        service = EnhancedMaintenanceModeService(
            config_service=self.mock_config_service,
            db_manager=None
        )
        
        # Should not have completion tracker
        self.assertIsNone(service._completion_tracker)
    
    @patch('enhanced_maintenance_mode_service.logger')
    def test_enable_maintenance_starts_completion_tracking(self, mock_logger):
        """Test that enabling maintenance starts completion tracking"""
        # Mock completion tracker methods
        mock_tracker = Mock()
        self.maintenance_service._completion_tracker = mock_tracker
        mock_tracker.start_monitoring.return_value = None
        mock_tracker.force_refresh_active_jobs.return_value = 3
        
        # Enable maintenance mode
        result = self.maintenance_service.enable_maintenance(
            reason="System update",
            duration=30,
            mode=MaintenanceMode.NORMAL,
            enabled_by="admin"
        )
        
        self.assertTrue(result)
        
        # Should start monitoring and refresh active jobs
        mock_tracker.start_monitoring.assert_called_once()
        mock_tracker.force_refresh_active_jobs.assert_called_once()
        
        # Should update active jobs count in status
        status = self.maintenance_service.get_maintenance_status()
        self.assertEqual(status.active_jobs_count, 3)
    
    def test_enable_test_mode_does_not_start_tracking(self):
        """Test that test mode does not start completion tracking"""
        # Mock completion tracker
        mock_tracker = Mock()
        self.maintenance_service._completion_tracker = mock_tracker
        
        # Enable test mode
        result = self.maintenance_service.enable_maintenance(
            reason="Testing maintenance procedures",
            mode=MaintenanceMode.TEST,
            enabled_by="admin"
        )
        
        self.assertTrue(result)
        
        # Should not start monitoring in test mode
        mock_tracker.start_monitoring.assert_not_called()
    
    def test_disable_maintenance_stops_completion_tracking(self):
        """Test that disabling maintenance stops completion tracking"""
        # Mock completion tracker
        mock_tracker = Mock()
        self.maintenance_service._completion_tracker = mock_tracker
        
        # Enable maintenance first
        self.maintenance_service.enable_maintenance(
            reason="System update",
            mode=MaintenanceMode.NORMAL,
            enabled_by="admin"
        )
        
        # Reset mock calls
        mock_tracker.reset_mock()
        
        # Disable maintenance
        result = self.maintenance_service.disable_maintenance(disabled_by="admin")
        
        self.assertTrue(result)
        
        # Should stop monitoring
        mock_tracker.stop_monitoring.assert_called_once()
    
    def test_get_active_jobs_info(self):
        """Test getting active jobs information"""
        # Mock completion tracker with active jobs
        mock_tracker = Mock()
        self.maintenance_service._completion_tracker = mock_tracker
        
        # Mock active jobs
        job1 = ActiveJobInfo(
            job_id="job1",
            user_id=1,
            job_type="caption_generation",
            started_at=datetime.now(timezone.utc),
            estimated_completion=datetime.now(timezone.utc) + timedelta(minutes=10),
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
        
        mock_tracker.get_active_jobs.return_value = [job1, job2]
        mock_tracker.get_completion_stats.return_value = {
            'jobs_completed': 5,
            'jobs_failed': 1,
            'average_completion_time': 120
        }
        mock_tracker.get_estimated_completion_time.return_value = job1.estimated_completion
        
        # Get active jobs info
        jobs_info = self.maintenance_service.get_active_jobs_info()
        
        self.assertTrue(jobs_info['completion_tracker_available'])
        self.assertEqual(jobs_info['active_jobs_count'], 2)
        self.assertEqual(len(jobs_info['active_jobs']), 2)
        
        # Check job details
        job_data = jobs_info['active_jobs'][0]
        self.assertEqual(job_data['job_id'], 'job1')
        self.assertEqual(job_data['user_id'], 1)
        self.assertEqual(job_data['progress_percent'], 50)
        self.assertIsNotNone(job_data['estimated_completion'])
        
        # Check completion stats
        self.assertIn('completion_stats', jobs_info)
        self.assertEqual(jobs_info['completion_stats']['jobs_completed'], 5)
        
        # Check estimated completion time
        self.assertIsNotNone(jobs_info['estimated_all_jobs_completion'])
    
    def test_get_active_jobs_info_without_tracker(self):
        """Test getting active jobs info when tracker is not available"""
        # Remove completion tracker
        self.maintenance_service._completion_tracker = None
        
        jobs_info = self.maintenance_service.get_active_jobs_info()
        
        self.assertFalse(jobs_info['completion_tracker_available'])
        self.assertEqual(jobs_info['active_jobs_count'], 0)
        self.assertEqual(len(jobs_info['active_jobs']), 0)
    
    def test_get_job_completion_notifications(self):
        """Test getting job completion notifications"""
        # Mock completion tracker with completed jobs
        mock_tracker = Mock()
        self.maintenance_service._completion_tracker = mock_tracker
        
        # Mock completion notifications
        notification1 = CompletionNotification(
            job_id="completed_job1",
            user_id=1,
            job_type="caption_generation",
            completion_status="completed",
            completed_at=datetime.now(timezone.utc),
            duration_seconds=120
        )
        
        notification2 = CompletionNotification(
            job_id="failed_job1",
            user_id=2,
            job_type="caption_generation",
            completion_status="failed",
            completed_at=datetime.now(timezone.utc),
            duration_seconds=60,
            error_message="Processing error"
        )
        
        mock_tracker.get_completed_jobs.return_value = [notification1, notification2]
        
        # Get completion notifications
        notifications = self.maintenance_service.get_job_completion_notifications(limit=10)
        
        self.assertEqual(len(notifications), 2)
        
        # Check first notification
        notif_data = notifications[0]
        self.assertEqual(notif_data['job_id'], 'completed_job1')
        self.assertEqual(notif_data['completion_status'], 'completed')
        self.assertEqual(notif_data['duration_seconds'], 120)
        self.assertIsNone(notif_data['error_message'])
        
        # Check second notification
        notif_data = notifications[1]
        self.assertEqual(notif_data['job_id'], 'failed_job1')
        self.assertEqual(notif_data['completion_status'], 'failed')
        self.assertEqual(notif_data['error_message'], 'Processing error')
    
    def test_job_completion_subscription(self):
        """Test subscribing to job completion notifications"""
        # Mock completion tracker
        mock_tracker = Mock()
        self.maintenance_service._completion_tracker = mock_tracker
        mock_tracker.subscribe_to_completions.return_value = "subscription_id_123"
        mock_tracker.unsubscribe_from_completions.return_value = True
        
        # Test subscription
        callback = Mock()
        subscription_id = self.maintenance_service.subscribe_to_job_completions(callback)
        
        self.assertEqual(subscription_id, "subscription_id_123")
        mock_tracker.subscribe_to_completions.assert_called_once_with(callback)
        
        # Test unsubscription
        result = self.maintenance_service.unsubscribe_from_job_completions(subscription_id)
        
        self.assertTrue(result)
        mock_tracker.unsubscribe_from_completions.assert_called_once_with(subscription_id)
    
    def test_allow_operation_completion(self):
        """Test allowing specific operation to complete"""
        # Mock completion tracker with active jobs
        mock_tracker = Mock()
        self.maintenance_service._completion_tracker = mock_tracker
        
        # Mock active job
        active_job = ActiveJobInfo(
            job_id="operation_123",
            user_id=1,
            job_type="caption_generation",
            started_at=datetime.now(timezone.utc),
            estimated_completion=None,
            status="running",
            progress_percent=75,
            current_step="finalizing",
            platform_connection_id=1
        )
        
        mock_tracker.get_active_jobs.return_value = [active_job]
        
        # Test allowing existing operation
        result = self.maintenance_service.allow_operation_completion("operation_123")
        self.assertTrue(result)
        
        # Test allowing non-existent operation
        result = self.maintenance_service.allow_operation_completion("nonexistent_operation")
        self.assertFalse(result)
    
    def test_get_user_active_jobs(self):
        """Test getting active jobs for specific user"""
        # Mock completion tracker
        mock_tracker = Mock()
        self.maintenance_service._completion_tracker = mock_tracker
        
        # Mock user jobs
        user_job = ActiveJobInfo(
            job_id="user_job_1",
            user_id=1,
            job_type="caption_generation",
            started_at=datetime.now(timezone.utc),
            estimated_completion=datetime.now(timezone.utc) + timedelta(minutes=5),
            status="running",
            progress_percent=90,
            current_step="completing",
            platform_connection_id=1
        )
        
        mock_tracker.get_jobs_by_user.return_value = [user_job]
        
        # Get user jobs
        user_jobs = self.maintenance_service.get_user_active_jobs(user_id=1)
        
        self.assertEqual(len(user_jobs), 1)
        job_data = user_jobs[0]
        self.assertEqual(job_data['job_id'], 'user_job_1')
        self.assertEqual(job_data['progress_percent'], 90)
        self.assertIsNotNone(job_data['estimated_completion'])
        
        mock_tracker.get_jobs_by_user.assert_called_once_with(1)
    
    def test_is_user_job_active(self):
        """Test checking if user has active jobs"""
        # Mock completion tracker
        mock_tracker = Mock()
        self.maintenance_service._completion_tracker = mock_tracker
        mock_tracker.is_user_job_active.return_value = True
        
        # Test user with active jobs
        result = self.maintenance_service.is_user_job_active(user_id=1)
        self.assertTrue(result)
        mock_tracker.is_user_job_active.assert_called_once_with(1)
        
        # Test user without active jobs
        mock_tracker.is_user_job_active.return_value = False
        result = self.maintenance_service.is_user_job_active(user_id=2)
        self.assertFalse(result)
    
    def test_update_active_jobs_count(self):
        """Test updating active jobs count in maintenance status"""
        # Enable maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="System update",
            mode=MaintenanceMode.NORMAL,
            enabled_by="admin"
        )
        
        # Update active jobs count
        self.maintenance_service.update_active_jobs_count(5)
        
        # Check that status reflects updated count
        status = self.maintenance_service.get_maintenance_status()
        self.assertEqual(status.active_jobs_count, 5)
    
    def test_maintenance_report_includes_completion_info(self):
        """Test that maintenance report includes completion tracking information"""
        # Mock completion tracker
        mock_tracker = Mock()
        self.maintenance_service._completion_tracker = mock_tracker
        mock_tracker.get_active_jobs.return_value = []
        mock_tracker.get_completion_stats.return_value = {
            'jobs_completed': 10,
            'jobs_failed': 2,
            'average_completion_time': 150
        }
        mock_tracker.get_estimated_completion_time.return_value = None
        
        # Enable maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="System maintenance",
            mode=MaintenanceMode.NORMAL,
            enabled_by="admin"
        )
        
        # Create maintenance report
        report = self.maintenance_service.create_maintenance_report()
        
        # Check that report includes completion information
        self.assertIn('system_impact', report)
        self.assertIn('active_jobs_count', report['system_impact'])
        
        # The active jobs count should be included in the status
        self.assertIn('maintenance_status', report)
    
    @patch('enhanced_maintenance_mode_service.logger')
    def test_error_handling_in_completion_tracking(self, mock_logger):
        """Test error handling when completion tracking fails"""
        # Mock completion tracker that raises errors
        mock_tracker = Mock()
        mock_tracker.start_monitoring.side_effect = Exception("Tracking error")
        self.maintenance_service._completion_tracker = mock_tracker
        
        # Enable maintenance mode (should handle error gracefully)
        result = self.maintenance_service.enable_maintenance(
            reason="System update",
            mode=MaintenanceMode.NORMAL,
            enabled_by="admin"
        )
        
        # Should still succeed despite tracking error
        self.assertTrue(result)
        
        # Should log the error
        mock_logger.error.assert_called()
    
    def test_completion_tracking_integration_with_real_tracker(self):
        """Test integration with real completion tracker (not mocked)"""
        # Create service with real tracker
        service = EnhancedMaintenanceModeService(
            config_service=self.mock_config_service,
            db_manager=self.mock_db_manager
        )
        
        # Mock database session for tracker
        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.all.return_value = []
        self.mock_db_manager.get_session.return_value.__enter__ = Mock(return_value=mock_session)
        self.mock_db_manager.get_session.return_value.__exit__ = Mock(return_value=None)
        
        # Enable maintenance mode
        result = service.enable_maintenance(
            reason="Integration test",
            mode=MaintenanceMode.NORMAL,
            enabled_by="admin"
        )
        
        self.assertTrue(result)
        
        # Should have real completion tracker
        self.assertIsNotNone(service._completion_tracker)
        
        # Should be able to get active jobs info
        jobs_info = service.get_active_jobs_info()
        self.assertTrue(jobs_info['completion_tracker_available'])
        self.assertEqual(jobs_info['active_jobs_count'], 0)  # No active jobs in mock
        
        # Clean up
        service.disable_maintenance()


class TestMaintenanceStatusWithCompletionTracking(unittest.TestCase):
    """Test maintenance status integration with completion tracking"""
    
    def test_maintenance_status_includes_active_jobs_count(self):
        """Test that maintenance status includes active jobs count"""
        mock_config_service = Mock()
        mock_db_manager = Mock()
        
        service = EnhancedMaintenanceModeService(
            config_service=mock_config_service,
            db_manager=mock_db_manager
        )
        
        # Enable maintenance
        service.enable_maintenance(
            reason="Test maintenance",
            mode=MaintenanceMode.NORMAL,
            enabled_by="admin"
        )
        
        # Update active jobs count
        service.update_active_jobs_count(3)
        
        # Get status
        status = service.get_maintenance_status()
        
        self.assertTrue(status.is_active)
        self.assertEqual(status.active_jobs_count, 3)
        self.assertEqual(status.mode, MaintenanceMode.NORMAL)
        self.assertEqual(status.reason, "Test maintenance")


if __name__ == '__main__':
    unittest.main()
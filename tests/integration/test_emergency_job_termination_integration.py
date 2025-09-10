# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integration tests for Emergency Job Termination and Recovery

Tests the complete workflow of emergency job termination, notification,
and recovery mechanisms during emergency maintenance scenarios.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone, timedelta
import time

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.services.task.emergency.emergency_job_termination_manager import (
    EmergencyJobTerminationManager,
    JobTerminationRecord,
    JobRecoveryInfo,
    TerminationStatus
)
from app.services.maintenance.emergency.emergency_maintenance_handler import EmergencyMaintenanceHandler
from models import User, UserRole, TaskStatus, CaptionGenerationTask


class TestEmergencyJobTerminationIntegration(unittest.TestCase):
    """Integration tests for emergency job termination and recovery"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock dependencies
        self.mock_task_queue_manager = Mock()
        self.mock_db_manager = Mock()
        self.mock_maintenance_service = Mock()
        self.mock_session_manager = Mock()
        
        # Create managers
        self.termination_manager = EmergencyJobTerminationManager(
            task_queue_manager=self.mock_task_queue_manager,
            db_manager=self.mock_db_manager
        )
        
        self.emergency_handler = EmergencyMaintenanceHandler(
            maintenance_service=self.mock_maintenance_service,
            session_manager=self.mock_session_manager,
            task_queue_manager=self.mock_task_queue_manager,
            db_manager=self.mock_db_manager
        )
        
        # Mock system admin user
        self.mock_admin_user = Mock()
        self.mock_admin_user.id = 1
        self.mock_admin_user.role = UserRole.ADMIN
        self.mock_admin_user.username = "admin"
        
        # Mock regular user
        self.mock_user = Mock()
        self.mock_user.id = 2
        self.mock_user.role = UserRole.REVIEWER
        self.mock_user.username = "test_user"
        
        # Mock database session
        self.mock_db_session = Mock()
        self.mock_context_manager = MagicMock()
        self.mock_context_manager.__enter__.return_value = self.mock_db_session
        self.mock_context_manager.__exit__.return_value = None
        self.mock_db_manager.get_session.return_value = self.mock_context_manager
        
        # Setup user queries
        def mock_user_query(user_id):
            if user_id == 1:
                return self.mock_admin_user
            elif user_id == 2:
                return self.mock_user
            return None
        
        self.mock_db_session.query.return_value.filter_by.return_value.first.side_effect = lambda: self.mock_admin_user
        
        # Mock running jobs
        self.mock_job1 = Mock()
        self.mock_job1.id = "job1"
        self.mock_job1.user_id = 2
        self.mock_job1.platform_connection_id = 1
        self.mock_job1.settings = {"test": "settings"}
        
        self.mock_job2 = Mock()
        self.mock_job2.id = "job2"
        self.mock_job2.user_id = 2
        self.mock_job2.platform_connection_id = 1
        self.mock_job2.settings = {"test": "settings2"}
    
    def test_complete_emergency_termination_workflow(self):
        """Test complete emergency termination workflow with job recovery"""
        # Setup running jobs
        self.mock_task_queue_manager.get_all_tasks.return_value = [self.mock_job1, self.mock_job2]
        self.mock_task_queue_manager.cancel_task_as_admin.return_value = True
        self.mock_task_queue_manager.get_task.side_effect = lambda job_id: (
            self.mock_job1 if job_id == "job1" else self.mock_job2 if job_id == "job2" else None
        )
        
        # Step 1: Terminate jobs safely
        termination_records = self.termination_manager.terminate_jobs_safely(
            grace_period=1,  # Short grace period for testing
            reason="Emergency maintenance test",
            triggered_by="test_admin"
        )
        
        # Verify termination results
        self.assertEqual(len(termination_records), 2)
        
        # Check termination records
        for record in termination_records:
            self.assertEqual(record.status, TerminationStatus.TERMINATED)
            self.assertEqual(record.termination_reason, "Emergency maintenance test (triggered by: test_admin)")
            self.assertEqual(record.grace_period_seconds, 1)
            self.assertFalse(record.recovery_attempted)
        
        # Verify task queue manager was called correctly
        self.mock_task_queue_manager.get_all_tasks.assert_called_once_with(
            admin_user_id=1,
            status_filter=[TaskStatus.RUNNING],
            limit=1000
        )
        
        # Verify both jobs were cancelled
        self.assertEqual(self.mock_task_queue_manager.cancel_task_as_admin.call_count, 2)
        
        # Step 2: Check recovery queue
        recovery_plan = self.termination_manager.create_job_recovery_plan()
        self.assertEqual(len(recovery_plan), 2)
        
        # Verify recovery info
        for recovery_info in recovery_plan:
            self.assertIn(recovery_info.original_job_id, ["job1", "job2"])
            self.assertEqual(recovery_info.user_id, 2)
            self.assertEqual(recovery_info.recovery_priority, "high")
        
        # Step 3: Attempt job recovery
        recovered_count = self.termination_manager.recover_terminated_jobs(max_recoveries=5)
        self.assertEqual(recovered_count, 2)
        
        # Verify recovery status updated
        for record in termination_records:
            updated_record = self.termination_manager.get_termination_status(record.job_id)
            self.assertTrue(updated_record.recovery_attempted)
            self.assertTrue(updated_record.recovery_successful)
            self.assertEqual(updated_record.status, TerminationStatus.RECOVERED)
    
    def test_emergency_termination_with_failures(self):
        """Test emergency termination handling job cancellation failures"""
        # Setup one successful and one failed job cancellation
        self.mock_task_queue_manager.get_all_tasks.return_value = [self.mock_job1, self.mock_job2]
        
        def mock_cancel_task(task_id, admin_user_id, reason):
            return task_id == "job1"  # Only job1 succeeds
        
        self.mock_task_queue_manager.cancel_task_as_admin.side_effect = mock_cancel_task
        self.mock_task_queue_manager.get_task.side_effect = lambda job_id: (
            self.mock_job1 if job_id == "job1" else self.mock_job2 if job_id == "job2" else None
        )
        
        # Terminate jobs
        termination_records = self.termination_manager.terminate_jobs_safely(
            grace_period=1,
            reason="Test with failures",
            triggered_by="test_admin"
        )
        
        # Verify results
        self.assertEqual(len(termination_records), 2)
        
        # Check individual results
        job1_record = next(r for r in termination_records if r.job_id == "job1")
        job2_record = next(r for r in termination_records if r.job_id == "job2")
        
        self.assertEqual(job1_record.status, TerminationStatus.TERMINATED)
        self.assertEqual(job2_record.status, TerminationStatus.FAILED)
        self.assertEqual(job2_record.error_message, "Job cancellation failed")
        
        # Verify statistics
        stats = self.termination_manager.get_termination_statistics()
        self.assertEqual(stats['statistics']['jobs_terminated'], 1)
        self.assertEqual(stats['statistics']['termination_failures'], 1)
        
        # Only successful job should be in recovery queue
        recovery_plan = self.termination_manager.create_job_recovery_plan()
        self.assertEqual(len(recovery_plan), 1)
        self.assertEqual(recovery_plan[0].original_job_id, "job1")
    
    def test_job_recovery_with_partial_failures(self):
        """Test job recovery with some recovery failures"""
        # Setup successful termination
        self.mock_task_queue_manager.get_all_tasks.return_value = [self.mock_job1, self.mock_job2]
        self.mock_task_queue_manager.cancel_task_as_admin.return_value = True
        self.mock_task_queue_manager.get_task.side_effect = lambda job_id: (
            self.mock_job1 if job_id == "job1" else self.mock_job2 if job_id == "job2" else None
        )
        
        # Terminate jobs
        termination_records = self.termination_manager.terminate_jobs_safely(
            grace_period=1,
            reason="Test recovery failures",
            triggered_by="test_admin"
        )
        
        # Mock recovery to fail for one job
        original_recreate = self.termination_manager._recreate_job
        def mock_recreate_job(recovery_info):
            return recovery_info.original_job_id == "job1"  # Only job1 recovery succeeds
        
        self.termination_manager._recreate_job = mock_recreate_job
        
        # Attempt recovery
        recovered_count = self.termination_manager.recover_terminated_jobs(max_recoveries=5)
        self.assertEqual(recovered_count, 1)
        
        # Check recovery status
        job1_record = self.termination_manager.get_termination_status("job1")
        job2_record = self.termination_manager.get_termination_status("job2")
        
        self.assertTrue(job1_record.recovery_successful)
        self.assertEqual(job1_record.status, TerminationStatus.RECOVERED)
        
        self.assertTrue(job2_record.recovery_attempted)
        self.assertFalse(job2_record.recovery_successful)
        self.assertEqual(job2_record.error_message, "Job recovery failed")
        
        # Verify statistics
        stats = self.termination_manager.get_termination_statistics()
        self.assertEqual(stats['statistics']['jobs_recovered'], 1)
        self.assertEqual(stats['statistics']['recovery_failures'], 1)
        
        # Restore original method
        self.termination_manager._recreate_job = original_recreate
    
    def test_notification_system_integration(self):
        """Test job termination notification system"""
        # Setup successful termination
        self.mock_task_queue_manager.get_all_tasks.return_value = [self.mock_job1]
        self.mock_task_queue_manager.cancel_task_as_admin.return_value = True
        self.mock_task_queue_manager.get_task.return_value = self.mock_job1
        
        # Mock notification sending
        original_send_notification = self.termination_manager._send_notification_to_user
        self.termination_manager._send_notification_to_user = Mock(return_value=True)
        
        # Terminate job
        termination_records = self.termination_manager.terminate_jobs_safely(
            grace_period=1,
            reason="Test notifications",
            triggered_by="test_admin"
        )
        
        # Verify notification was sent
        self.assertEqual(len(termination_records), 1)
        record = termination_records[0]
        self.assertTrue(record.notification_sent)
        
        # Verify notification method was called
        self.termination_manager._send_notification_to_user.assert_called_once()
        
        # Verify statistics
        stats = self.termination_manager.get_termination_statistics()
        self.assertEqual(stats['statistics']['notifications_sent'], 1)
        
        # Restore original method
        self.termination_manager._send_notification_to_user = original_send_notification
    
    def test_integration_with_emergency_handler(self):
        """Test integration between emergency handler and job termination manager"""
        # Setup emergency handler with termination manager
        self.emergency_handler.termination_manager = self.termination_manager
        
        # Setup mocks for emergency activation
        self.mock_maintenance_service.enable_maintenance.return_value = True
        self.mock_session_manager.invalidate_non_admin_sessions.return_value = ['session1']
        self.mock_task_queue_manager.get_queue_stats.return_value = {'running': 2}
        self.mock_task_queue_manager.get_all_tasks.return_value = [self.mock_job1, self.mock_job2]
        self.mock_task_queue_manager.cancel_task_as_admin.return_value = True
        
        # Activate emergency mode
        result = self.emergency_handler.activate_emergency_mode(
            reason="Integration test",
            triggered_by="test_admin"
        )
        
        # Verify emergency activation succeeded
        self.assertTrue(result)
        
        # Verify job termination was called
        self.mock_task_queue_manager.cancel_task_as_admin.assert_called()
        
        # Check emergency status includes job information
        status = self.emergency_handler.get_emergency_status()
        self.assertTrue(status['is_active'])
        self.assertEqual(status['terminated_jobs_count'], 2)
    
    def test_termination_statistics_and_reporting(self):
        """Test comprehensive termination statistics and reporting"""
        # Setup multiple termination scenarios
        self.mock_task_queue_manager.get_all_tasks.return_value = [self.mock_job1, self.mock_job2]
        
        # First termination - all successful
        self.mock_task_queue_manager.cancel_task_as_admin.return_value = True
        self.mock_task_queue_manager.get_task.side_effect = lambda job_id: (
            self.mock_job1 if job_id == "job1" else self.mock_job2 if job_id == "job2" else None
        )
        
        termination_records1 = self.termination_manager.terminate_jobs_safely(
            grace_period=2,
            reason="First termination",
            triggered_by="admin1"
        )
        
        # Second termination - one failure
        mock_job3 = Mock()
        mock_job3.id = "job3"
        mock_job3.user_id = 2
        mock_job3.platform_connection_id = 1
        mock_job3.settings = {"test": "settings3"}
        
        self.mock_task_queue_manager.get_all_tasks.return_value = [mock_job3]
        self.mock_task_queue_manager.cancel_task_as_admin.return_value = False  # Simulate failure
        
        termination_records2 = self.termination_manager.terminate_jobs_safely(
            grace_period=1,
            reason="Second termination",
            triggered_by="admin2"
        )
        
        # Get comprehensive statistics
        stats = self.termination_manager.get_termination_statistics()
        
        # Verify statistics
        self.assertEqual(stats['statistics']['jobs_terminated'], 2)  # Only successful ones
        self.assertEqual(stats['statistics']['termination_failures'], 1)
        self.assertEqual(stats['total_termination_records'], 3)
        self.assertEqual(stats['recovery_queue_size'], 2)  # Only successful jobs in queue
        
        # Verify status counts
        self.assertEqual(stats['status_counts']['terminated'], 2)
        self.assertEqual(stats['status_counts']['failed'], 1)
        
        # Test recovery and verify recovery rate
        recovered_count = self.termination_manager.recover_terminated_jobs(max_recoveries=5)
        self.assertEqual(recovered_count, 2)
        
        # Get updated statistics
        updated_stats = self.termination_manager.get_termination_statistics()
        self.assertEqual(updated_stats['statistics']['jobs_recovered'], 2)
        self.assertEqual(updated_stats['recovery_rate_percent'], 100.0)  # 2/2 recovered
    
    def test_cleanup_and_maintenance_operations(self):
        """Test cleanup and maintenance operations for termination records"""
        # Create some termination records
        self.mock_task_queue_manager.get_all_tasks.return_value = [self.mock_job1]
        self.mock_task_queue_manager.cancel_task_as_admin.return_value = True
        self.mock_task_queue_manager.get_task.return_value = self.mock_job1
        
        # Terminate job
        termination_records = self.termination_manager.terminate_jobs_safely(
            grace_period=1,
            reason="Cleanup test",
            triggered_by="test_admin"
        )
        
        # Verify record exists
        self.assertEqual(len(termination_records), 1)
        record = self.termination_manager.get_termination_status("job1")
        self.assertIsNotNone(record)
        
        # Manually set old termination time for cleanup test
        old_time = datetime.now(timezone.utc) - timedelta(hours=25)
        record.termination_time = old_time
        
        # Test cleanup
        cleaned_count = self.termination_manager.cleanup_old_records(older_than_hours=24)
        self.assertEqual(cleaned_count, 1)
        
        # Verify record was removed
        cleaned_record = self.termination_manager.get_termination_status("job1")
        self.assertIsNone(cleaned_record)
    
    @patch('time.sleep')  # Mock sleep to speed up tests
    def test_grace_period_handling(self, mock_sleep):
        """Test grace period handling during job termination"""
        # Setup job termination
        self.mock_task_queue_manager.get_all_tasks.return_value = [self.mock_job1]
        self.mock_task_queue_manager.cancel_task_as_admin.return_value = True
        self.mock_task_queue_manager.get_task.return_value = self.mock_job1
        
        # Test different grace periods
        grace_periods = [0, 5, 30]
        
        for grace_period in grace_periods:
            # Reset mock
            mock_sleep.reset_mock()
            
            # Terminate with specific grace period
            termination_records = self.termination_manager.terminate_jobs_safely(
                grace_period=grace_period,
                reason=f"Grace period test {grace_period}",
                triggered_by="test_admin"
            )
            
            # Verify grace period was recorded
            self.assertEqual(len(termination_records), 1)
            record = termination_records[0]
            self.assertEqual(record.grace_period_seconds, grace_period)
            
            # Verify sleep was called with correct duration (if > 0)
            if grace_period > 0:
                mock_sleep.assert_called_once_with(grace_period)
            else:
                mock_sleep.assert_not_called()


if __name__ == '__main__':
    unittest.main()
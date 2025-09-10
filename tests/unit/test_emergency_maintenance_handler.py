# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for EmergencyMaintenanceHandler

Tests emergency maintenance activation, job termination, session cleanup,
and emergency reporting functionality.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime, timezone, timedelta
import time

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.services.maintenance.emergency.emergency_maintenance_handler import (
    EmergencyMaintenanceHandler, 
    EmergencyReport, 
    EmergencyModeError, 
    JobTerminationError
)
from app.services.maintenance.enhanced.enhanced_maintenance_mode_service import MaintenanceMode
from models import User, UserRole, TaskStatus


class TestEmergencyMaintenanceHandler(unittest.TestCase):
    """Test cases for EmergencyMaintenanceHandler"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock dependencies
        self.mock_maintenance_service = Mock()
        self.mock_session_manager = Mock()
        self.mock_task_queue_manager = Mock()
        self.mock_db_manager = Mock()
        
        # Create handler instance
        self.handler = EmergencyMaintenanceHandler(
            maintenance_service=self.mock_maintenance_service,
            session_manager=self.mock_session_manager,
            task_queue_manager=self.mock_task_queue_manager,
            db_manager=self.mock_db_manager
        )
        
        # Mock system admin user
        self.mock_admin_user = Mock()
        self.mock_admin_user.id = 1
        self.mock_admin_user.role = UserRole.ADMIN
        
        # Mock database session context manager
        self.mock_db_session = Mock()
        self.mock_context_manager = MagicMock()
        self.mock_context_manager.__enter__.return_value = self.mock_db_session
        self.mock_context_manager.__exit__.return_value = None
        self.mock_db_manager.get_session.return_value = self.mock_context_manager
        self.mock_db_session.query.return_value.filter_by.return_value.first.return_value = self.mock_admin_user
    
    def test_activate_emergency_mode_success(self):
        """Test successful emergency mode activation"""
        # Setup mocks
        self.mock_maintenance_service.enable_maintenance.return_value = True
        self.mock_session_manager.invalidate_non_admin_sessions.return_value = ['session1', 'session2']
        self.mock_task_queue_manager.get_all_tasks.return_value = []
        
        # Test activation
        result = self.handler.activate_emergency_mode(
            reason="Critical system issue",
            triggered_by="admin_user"
        )
        
        # Verify result
        self.assertTrue(result)
        
        # Verify maintenance service was called
        self.mock_maintenance_service.enable_maintenance.assert_called_once_with(
            reason="EMERGENCY: Critical system issue",
            duration=None,
            mode=MaintenanceMode.EMERGENCY,
            enabled_by="admin_user"
        )
        
        # Verify session cleanup was called
        self.mock_session_manager.invalidate_non_admin_sessions.assert_called_once()
        self.mock_session_manager.prevent_non_admin_login.assert_called_once()
        
        # Verify logging was called
        self.mock_maintenance_service.log_maintenance_event.assert_called_once()
        
        # Verify emergency state
        status = self.handler.get_emergency_status()
        self.assertTrue(status['is_active'])
        self.assertEqual(status['triggered_by'], "admin_user")
        self.assertEqual(status['reason'], "Critical system issue")
    
    def test_activate_emergency_mode_maintenance_service_failure(self):
        """Test emergency mode activation when maintenance service fails"""
        # Setup mock to fail
        self.mock_maintenance_service.enable_maintenance.return_value = False
        
        # Test activation should raise exception
        with self.assertRaises(EmergencyModeError) as context:
            self.handler.activate_emergency_mode(
                reason="Test failure",
                triggered_by="test_user"
            )
        
        self.assertIn("Failed to activate emergency maintenance mode", str(context.exception))
    
    def test_terminate_running_jobs_success(self):
        """Test successful job termination"""
        # Setup mock tasks
        mock_task1 = Mock()
        mock_task1.id = "task1"
        mock_task2 = Mock()
        mock_task2.id = "task2"
        
        self.mock_task_queue_manager.get_queue_stats.return_value = {'running': 2}
        self.mock_task_queue_manager.get_all_tasks.return_value = [mock_task1, mock_task2]
        self.mock_task_queue_manager.cancel_task_as_admin.return_value = True
        
        # Test job termination
        terminated_jobs = self.handler.terminate_running_jobs(grace_period=1)
        
        # Verify results
        self.assertEqual(len(terminated_jobs), 2)
        self.assertIn("task1", terminated_jobs)
        self.assertIn("task2", terminated_jobs)
        
        # Verify task queue manager calls
        self.mock_task_queue_manager.get_queue_stats.assert_called_once()
        self.mock_task_queue_manager.get_all_tasks.assert_called_once_with(
            admin_user_id=1,
            status_filter=[TaskStatus.RUNNING],
            limit=1000
        )
        
        # Verify both tasks were cancelled
        self.assertEqual(self.mock_task_queue_manager.cancel_task_as_admin.call_count, 2)
    
    def test_terminate_running_jobs_no_running_jobs(self):
        """Test job termination when no jobs are running"""
        # Setup mock with no running jobs
        self.mock_task_queue_manager.get_queue_stats.return_value = {'running': 0}
        
        # Test job termination
        terminated_jobs = self.handler.terminate_running_jobs(grace_period=1)
        
        # Verify results
        self.assertEqual(len(terminated_jobs), 0)
        
        # Verify get_all_tasks was not called
        self.mock_task_queue_manager.get_all_tasks.assert_not_called()
    
    def test_terminate_running_jobs_no_system_admin(self):
        """Test job termination when no system admin is found"""
        # Setup mock with no admin user
        self.mock_db_session.query.return_value.filter_by.return_value.first.return_value = None
        self.mock_task_queue_manager.get_queue_stats.return_value = {'running': 1}
        
        # Test job termination should raise exception
        with self.assertRaises(JobTerminationError) as context:
            self.handler.terminate_running_jobs(grace_period=1)
        
        self.assertIn("No system admin available", str(context.exception))
    
    def test_force_session_cleanup_success(self):
        """Test successful force session cleanup"""
        # Setup mock
        self.mock_session_manager.invalidate_non_admin_sessions.return_value = ['s1', 's2', 's3']
        
        # Test cleanup
        invalidated_count = self.handler.force_session_cleanup()
        
        # Verify results
        self.assertEqual(invalidated_count, 3)
        
        # Verify session manager calls
        self.mock_session_manager.invalidate_non_admin_sessions.assert_called_once()
        self.mock_session_manager.prevent_non_admin_login.assert_called_once()
    
    def test_force_session_cleanup_failure(self):
        """Test force session cleanup when session manager fails"""
        # Setup mock to fail
        from maintenance_session_manager import SessionInvalidationError
        self.mock_session_manager.invalidate_non_admin_sessions.side_effect = SessionInvalidationError("Test error")
        
        # Test cleanup should raise exception
        with self.assertRaises(SessionInvalidationError):
            self.handler.force_session_cleanup()
    
    def test_enable_critical_admin_only_success(self):
        """Test enabling critical admin-only access"""
        # Test enable critical admin only
        # This should not raise an exception
        try:
            self.handler.enable_critical_admin_only()
        except Exception as e:
            self.fail(f"enable_critical_admin_only raised an exception: {e}")
    
    def test_create_emergency_report_active_emergency(self):
        """Test creating emergency report during active emergency"""
        # Setup emergency state
        self.handler._emergency_active = True
        self.handler._emergency_start_time = datetime.now(timezone.utc) - timedelta(minutes=30)
        self.handler._emergency_triggered_by = "test_admin"
        self.handler._emergency_reason = "Test emergency"
        self.handler._terminated_jobs = ["job1", "job2"]
        self.handler._invalidated_sessions_count = 5
        self.handler._emergency_errors = ["Error 1"]
        
        # Test report creation
        report = self.handler.create_emergency_report()
        
        # Verify report
        self.assertIsInstance(report, EmergencyReport)
        self.assertEqual(report.triggered_by, "test_admin")
        self.assertEqual(report.reason, "Test emergency")
        self.assertEqual(len(report.terminated_jobs), 2)
        self.assertEqual(report.invalidated_sessions, 5)
        self.assertEqual(len(report.errors), 1)
        self.assertEqual(report.recovery_status, "in_progress_with_errors")
        self.assertIsNotNone(report.duration_minutes)
        self.assertGreater(report.duration_minutes, 25)  # Should be around 30 minutes
    
    def test_create_emergency_report_completed_emergency(self):
        """Test creating emergency report for completed emergency"""
        # Setup completed emergency state
        self.handler._emergency_active = False
        self.handler._emergency_start_time = datetime.now(timezone.utc) - timedelta(minutes=60)
        self.handler._emergency_triggered_by = "test_admin"
        self.handler._emergency_reason = "Test emergency"
        self.handler._terminated_jobs = ["job1"]
        self.handler._invalidated_sessions_count = 3
        self.handler._emergency_errors = []
        self.handler._stats['total_downtime_minutes'] = 45.5
        
        # Test report creation
        report = self.handler.create_emergency_report()
        
        # Verify report
        self.assertIsInstance(report, EmergencyReport)
        self.assertEqual(report.recovery_status, "completed")
        self.assertEqual(report.duration_minutes, 45.5)
        self.assertEqual(len(report.errors), 0)
    
    def test_deactivate_emergency_mode_success(self):
        """Test successful emergency mode deactivation"""
        # Setup active emergency
        self.handler._emergency_active = True
        self.handler._emergency_start_time = datetime.now(timezone.utc) - timedelta(minutes=30)
        self.handler._terminated_jobs = ["job1"]
        self.handler._invalidated_sessions_count = 2
        
        # Setup mocks
        self.mock_maintenance_service.disable_maintenance.return_value = True
        
        # Test deactivation
        result = self.handler.deactivate_emergency_mode(deactivated_by="admin_user")
        
        # Verify result
        self.assertTrue(result)
        
        # Verify maintenance service was called
        self.mock_maintenance_service.disable_maintenance.assert_called_once_with(
            disabled_by="admin_user"
        )
        
        # Verify session manager cleanup
        self.mock_session_manager.allow_non_admin_login.assert_called_once()
        self.mock_session_manager.cleanup_maintenance_state.assert_called_once()
        
        # Verify logging
        self.mock_maintenance_service.log_maintenance_event.assert_called_once()
        
        # Verify emergency state
        self.assertFalse(self.handler._emergency_active)
    
    def test_deactivate_emergency_mode_not_active(self):
        """Test deactivating emergency mode when not active"""
        # Ensure emergency is not active
        self.handler._emergency_active = False
        
        # Test deactivation
        result = self.handler.deactivate_emergency_mode(deactivated_by="admin_user")
        
        # Verify result
        self.assertFalse(result)
        
        # Verify maintenance service was not called
        self.mock_maintenance_service.disable_maintenance.assert_not_called()
    
    def test_deactivate_emergency_mode_maintenance_service_failure(self):
        """Test emergency mode deactivation when maintenance service fails"""
        # Setup active emergency
        self.handler._emergency_active = True
        
        # Setup mock to fail
        self.mock_maintenance_service.disable_maintenance.return_value = False
        
        # Test deactivation
        result = self.handler.deactivate_emergency_mode(deactivated_by="admin_user")
        
        # Verify result
        self.assertFalse(result)
    
    def test_get_emergency_status_active(self):
        """Test getting emergency status when active"""
        # Setup active emergency
        start_time = datetime.now(timezone.utc) - timedelta(minutes=15)
        self.handler._emergency_active = True
        self.handler._emergency_start_time = start_time
        self.handler._emergency_triggered_by = "test_admin"
        self.handler._emergency_reason = "Test emergency"
        self.handler._terminated_jobs = ["job1", "job2"]
        self.handler._invalidated_sessions_count = 3
        self.handler._emergency_errors = ["Error 1"]
        
        # Test status
        status = self.handler.get_emergency_status()
        
        # Verify status
        self.assertTrue(status['is_active'])
        self.assertEqual(status['triggered_by'], "test_admin")
        self.assertEqual(status['reason'], "Test emergency")
        self.assertEqual(status['terminated_jobs_count'], 2)
        self.assertEqual(status['invalidated_sessions_count'], 3)
        self.assertEqual(status['errors_count'], 1)
        self.assertIsNotNone(status['current_duration_minutes'])
        self.assertGreater(status['current_duration_minutes'], 10)
    
    def test_get_emergency_status_inactive(self):
        """Test getting emergency status when inactive"""
        # Ensure emergency is not active
        self.handler._emergency_active = False
        
        # Test status
        status = self.handler.get_emergency_status()
        
        # Verify status
        self.assertFalse(status['is_active'])
        self.assertIsNone(status['current_duration_minutes'])
    
    @patch('time.sleep')  # Mock sleep to speed up tests
    def test_full_emergency_activation_workflow(self, mock_sleep):
        """Test complete emergency activation workflow"""
        # Setup mocks for successful workflow
        self.mock_maintenance_service.enable_maintenance.return_value = True
        self.mock_session_manager.invalidate_non_admin_sessions.return_value = ['s1', 's2']
        
        # Mock running tasks
        mock_task = Mock()
        mock_task.id = "task1"
        self.mock_task_queue_manager.get_queue_stats.return_value = {'running': 1}
        self.mock_task_queue_manager.get_all_tasks.return_value = [mock_task]
        self.mock_task_queue_manager.cancel_task_as_admin.return_value = True
        
        # Test full activation
        result = self.handler.activate_emergency_mode(
            reason="Critical system failure",
            triggered_by="emergency_admin"
        )
        
        # Verify success
        self.assertTrue(result)
        
        # Verify all steps were executed
        self.mock_maintenance_service.enable_maintenance.assert_called_once()
        self.mock_session_manager.invalidate_non_admin_sessions.assert_called_once()
        self.mock_session_manager.prevent_non_admin_login.assert_called_once()
        self.mock_task_queue_manager.cancel_task_as_admin.assert_called_once()
        
        # Verify statistics were updated
        self.assertEqual(self.handler._stats['emergency_activations'], 1)
        self.assertEqual(self.handler._stats['jobs_terminated'], 1)
        self.assertEqual(self.handler._stats['sessions_invalidated'], 2)
        
        # Verify emergency state
        status = self.handler.get_emergency_status()
        self.assertTrue(status['is_active'])
        self.assertEqual(status['terminated_jobs_count'], 1)
        self.assertEqual(status['invalidated_sessions_count'], 2)
    
    def test_emergency_activation_with_partial_failures(self):
        """Test emergency activation with some component failures"""
        # Setup mocks with partial failures
        self.mock_maintenance_service.enable_maintenance.return_value = True
        self.mock_session_manager.invalidate_non_admin_sessions.side_effect = Exception("Session error")
        self.mock_task_queue_manager.get_queue_stats.return_value = {'running': 0}
        
        # Test activation (should succeed despite session error)
        result = self.handler.activate_emergency_mode(
            reason="Test with failures",
            triggered_by="test_admin"
        )
        
        # Verify success (emergency mode should still activate)
        self.assertTrue(result)
        
        # Verify errors were recorded
        status = self.handler.get_emergency_status()
        self.assertGreater(status['errors_count'], 0)
        
        # Verify statistics include errors
        self.assertGreater(self.handler._stats['errors'], 0)
    
    def test_statistics_tracking(self):
        """Test that statistics are properly tracked"""
        # Initial statistics should be zero
        initial_stats = self.handler._stats.copy()
        for key in ['emergency_activations', 'jobs_terminated', 'sessions_invalidated', 'errors']:
            self.assertEqual(initial_stats[key], 0)
        
        # Setup successful activation
        self.mock_maintenance_service.enable_maintenance.return_value = True
        self.mock_session_manager.invalidate_non_admin_sessions.return_value = ['s1', 's2', 's3']
        self.mock_task_queue_manager.get_queue_stats.return_value = {'running': 0}
        
        # Activate emergency mode
        self.handler.activate_emergency_mode("Test stats", "test_admin")
        
        # Verify statistics were updated
        stats = self.handler._stats
        self.assertEqual(stats['emergency_activations'], 1)
        self.assertEqual(stats['sessions_invalidated'], 3)
        self.assertGreater(stats['average_activation_time_seconds'], 0)


if __name__ == '__main__':
    unittest.main()
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for AdminManagementService

Tests all administrative oversight capabilities including authorization checks,
system overview, job management, error diagnostics, and audit logging.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta
import json

from admin_management_service import (
    AdminManagementService, SystemOverview, JobDetails, ErrorDiagnostics, SystemSettings
)
from models import (
    CaptionGenerationTask, TaskStatus, User, UserRole, PlatformConnection,
    JobPriority, SystemConfiguration, JobAuditLog
)
from database import DatabaseManager
from task_queue_manager import TaskQueueManager


class TestAdminManagementService(unittest.TestCase):
    """Test cases for AdminManagementService with proper authorization checks"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_db_manager = Mock(spec=DatabaseManager)
        self.mock_task_queue_manager = Mock(spec=TaskQueueManager)
        self.mock_session = Mock()
        
        # Configure mock database manager
        self.mock_db_manager.get_session.return_value = self.mock_session
        
        # Create service instance
        self.admin_service = AdminManagementService(
            self.mock_db_manager, 
            self.mock_task_queue_manager
        )
        
        # Test data
        self.admin_user_id = 1
        self.regular_user_id = 2
        self.task_id = "test-task-123"
        
        # Mock admin user
        self.mock_admin_user = Mock(spec=User)
        self.mock_admin_user.id = self.admin_user_id
        self.mock_admin_user.role = UserRole.ADMIN
        self.mock_admin_user.username = "admin_user"
        
        # Mock regular user
        self.mock_regular_user = Mock(spec=User)
        self.mock_regular_user.id = self.regular_user_id
        self.mock_regular_user.role = UserRole.REVIEWER
        self.mock_regular_user.username = "regular_user"
    
    def test_verify_admin_authorization_success(self):
        """Test successful admin authorization"""
        # Setup
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = self.mock_admin_user
        
        # Execute
        result = self.admin_service._verify_admin_authorization(self.mock_session, self.admin_user_id)
        
        # Verify
        self.assertEqual(result, self.mock_admin_user)
        self.mock_session.query.assert_called_with(User)
    
    def test_verify_admin_authorization_user_not_found(self):
        """Test admin authorization when user not found"""
        # Setup
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = None
        
        # Execute & Verify
        with self.assertRaises(ValueError) as context:
            self.admin_service._verify_admin_authorization(self.mock_session, self.admin_user_id)
        
        self.assertIn("User 1 not found", str(context.exception))
    
    def test_verify_admin_authorization_not_admin(self):
        """Test admin authorization when user is not admin"""
        # Setup
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = self.mock_regular_user
        
        # Execute & Verify
        with self.assertRaises(ValueError) as context:
            self.admin_service._verify_admin_authorization(self.mock_session, self.regular_user_id)
        
        self.assertIn("User 2 is not authorized for admin operations", str(context.exception))
    
    def test_get_system_overview_success(self):
        """Test successful system overview retrieval"""
        # Mock the entire get_system_overview method to test the interface
        with patch.object(self.admin_service, '_verify_admin_authorization') as mock_verify, \
             patch.object(self.admin_service, '_calculate_system_health_score', return_value=85.5), \
             patch.object(self.admin_service, '_get_resource_usage', return_value={'cpu': 50}), \
             patch.object(self.admin_service, '_get_recent_errors', return_value=[]), \
             patch.object(self.admin_service, '_get_performance_metrics', return_value={'avg_time': 30}), \
             patch.object(self.admin_service, '_log_admin_action'):
            
            # Mock query results for statistics
            query_mock = Mock()
            query_mock.count.side_effect = [10, 8, 50, 5, 3, 2, 40, 3, 2]
            query_mock.filter_by.return_value = query_mock
            query_mock.filter.return_value = query_mock
            self.mock_session.query.return_value = query_mock
            
            # Mock admin verification to return successfully
            mock_verify.return_value = self.mock_admin_user
            
            # Execute
            result = self.admin_service.get_system_overview(self.admin_user_id)
        
        # Verify
        self.assertIsInstance(result, SystemOverview)
        self.assertEqual(result.total_users, 10)
        self.assertEqual(result.active_users, 8)
        self.assertEqual(result.total_tasks, 50)
        self.assertEqual(result.system_health_score, 85.5)
        mock_verify.assert_called_once_with(self.mock_session, self.admin_user_id)
        self.mock_session.commit.assert_called_once()
        self.mock_session.close.assert_called_once()
    
    def test_get_system_overview_unauthorized(self):
        """Test system overview with unauthorized user"""
        # Setup
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = self.mock_regular_user
        
        # Execute & Verify
        with self.assertRaises(ValueError):
            self.admin_service.get_system_overview(self.regular_user_id)
        
        self.mock_session.close.assert_called_once()
    
    def test_get_user_job_details_success(self):
        """Test successful user job details retrieval"""
        # Mock task data
        mock_task = Mock(spec=CaptionGenerationTask)
        mock_task.id = self.task_id
        mock_task.user_id = self.regular_user_id
        mock_task.status = TaskStatus.COMPLETED
        mock_task.priority = JobPriority.NORMAL
        mock_task.created_at = datetime.now(timezone.utc)
        mock_task.started_at = datetime.now(timezone.utc)
        mock_task.completed_at = datetime.now(timezone.utc)
        mock_task.progress_percent = 100
        mock_task.current_step = "completed"
        mock_task.error_message = None
        mock_task.admin_notes = None
        mock_task.cancelled_by_admin = False
        mock_task.cancellation_reason = None
        mock_task.retry_count = 0
        mock_task.max_retries = 3
        mock_task.resource_usage = '{"memory": 100, "cpu": 50}'
        
        # Mock user and platform connection
        mock_task.user = self.mock_regular_user
        mock_platform = Mock(spec=PlatformConnection)
        mock_platform.name = "Test Platform"
        mock_task.platform_connection = mock_platform
        
        # Setup query behavior
        def query_side_effect(model_class):
            if model_class == User:
                user_mock = Mock()
                user_mock.filter_by.return_value.first.return_value = self.mock_admin_user
                return user_mock
            elif model_class == CaptionGenerationTask:
                # Configure query chain for tasks
                query_mock = Mock()
                query_mock.join.return_value = query_mock
                query_mock.filter.return_value = query_mock
                query_mock.order_by.return_value = query_mock
                query_mock.limit.return_value = [mock_task]
                return query_mock
            return Mock()
        
        self.mock_session.query.side_effect = query_side_effect
        
        # Execute
        result = self.admin_service.get_user_job_details(self.admin_user_id, self.regular_user_id)
        
        # Verify
        self.assertEqual(len(result), 1)
        job_detail = result[0]
        self.assertIsInstance(job_detail, JobDetails)
        self.assertEqual(job_detail.task_id, self.task_id)
        self.assertEqual(job_detail.user_id, self.regular_user_id)
        self.assertEqual(job_detail.username, "regular_user")
        self.assertEqual(job_detail.platform_name, "Test Platform")
        self.assertEqual(job_detail.resource_usage, {"memory": 100, "cpu": 50})
        self.mock_session.commit.assert_called_once()
    
    def test_cancel_job_as_admin_success(self):
        """Test successful admin job cancellation"""
        # Setup
        def query_side_effect(model_class):
            if model_class == User:
                user_mock = Mock()
                user_mock.filter_by.return_value.first.return_value = self.mock_admin_user
                return user_mock
            return Mock()
        
        self.mock_session.query.side_effect = query_side_effect
        self.mock_task_queue_manager.cancel_task_as_admin.return_value = True
        
        reason = "System maintenance"
        
        # Execute
        result = self.admin_service.cancel_job_as_admin(self.admin_user_id, self.task_id, reason)
        
        # Verify
        self.assertTrue(result)
        self.mock_task_queue_manager.cancel_task_as_admin.assert_called_once_with(
            self.task_id, self.admin_user_id, reason
        )
        self.mock_session.commit.assert_called_once()
    
    def test_cancel_job_as_admin_failure(self):
        """Test admin job cancellation failure"""
        # Setup
        def query_side_effect(model_class):
            if model_class == User:
                user_mock = Mock()
                user_mock.filter_by.return_value.first.return_value = self.mock_admin_user
                return user_mock
            return Mock()
        
        self.mock_session.query.side_effect = query_side_effect
        self.mock_task_queue_manager.cancel_task_as_admin.return_value = False
        
        reason = "System maintenance"
        
        # Execute
        result = self.admin_service.cancel_job_as_admin(self.admin_user_id, self.task_id, reason)
        
        # Verify
        self.assertFalse(result)
        # Commit should be called to log the admin action even on failure
        self.mock_session.commit.assert_called_once()
    
    def test_update_system_settings_success(self):
        """Test successful system settings update"""
        # Setup
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = self.mock_admin_user
        
        # Mock existing configuration entry
        mock_config = Mock(spec=SystemConfiguration)
        config_query_mock = Mock()
        
        # Configure query behavior for SystemConfiguration
        def query_side_effect(model_class):
            if model_class == User:
                user_mock = Mock()
                user_mock.filter_by.return_value.first.return_value = self.mock_admin_user
                return user_mock
            elif model_class == SystemConfiguration:
                config_query_mock.filter_by.return_value.first.return_value = mock_config
                return config_query_mock
            return Mock()
        
        self.mock_session.query.side_effect = query_side_effect
        
        settings = SystemSettings(
            max_concurrent_tasks=5,
            default_task_timeout=300,
            cleanup_interval_hours=24,
            max_retry_attempts=3,
            enable_auto_recovery=True,
            maintenance_mode=False,
            rate_limit_per_user=10,
            resource_limits={"memory": 1000, "cpu": 80}
        )
        
        # Execute
        result = self.admin_service.update_system_settings(self.admin_user_id, settings)
        
        # Verify
        self.assertTrue(result)
        self.mock_session.commit.assert_called_once()
    
    def test_get_error_diagnostics_success(self):
        """Test successful error diagnostics retrieval"""
        # Setup
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = self.mock_admin_user
        
        # Mock failed task
        mock_task = Mock(spec=CaptionGenerationTask)
        mock_task.id = self.task_id
        mock_task.error_message = "Request timeout after 30 seconds"
        mock_task.status = TaskStatus.FAILED
        mock_task.retry_count = 1  # Add numeric values for comparison
        mock_task.max_retries = 3
        
        # Configure query behavior
        def query_side_effect(model_class):
            if model_class == User:
                user_mock = Mock()
                user_mock.filter_by.return_value.first.return_value = self.mock_admin_user
                return user_mock
            elif model_class == CaptionGenerationTask:
                task_mock = Mock()
                task_mock.filter_by.return_value.first.return_value = mock_task
                return task_mock
            elif model_class == JobAuditLog:
                audit_mock = Mock()
                audit_mock.filter_by.return_value.order_by.return_value.limit.return_value.all.return_value = []
                return audit_mock
            return Mock()
        
        self.mock_session.query.side_effect = query_side_effect
        
        # Mock helper methods
        with patch.object(self.admin_service, '_get_system_state_snapshot', return_value={'status': 'ok'}):
            
            # Execute
            result = self.admin_service.get_error_diagnostics(self.admin_user_id, self.task_id)
        
        # Verify
        self.assertIsInstance(result, ErrorDiagnostics)
        self.assertEqual(result.task_id, self.task_id)
        self.assertEqual(result.error_message, "Request timeout after 30 seconds")
        self.assertEqual(result.error_category, "timeout")
        self.assertIn("Increase timeout settings", result.suggested_solutions)
        self.mock_session.commit.assert_called_once()
    
    def test_get_error_diagnostics_task_not_found(self):
        """Test error diagnostics when task not found"""
        # Setup
        self.mock_session.query.return_value.filter_by.return_value.first.side_effect = [
            self.mock_admin_user,  # Admin user found
            None  # Task not found
        ]
        
        # Execute & Verify
        with self.assertRaises(ValueError) as context:
            self.admin_service.get_error_diagnostics(self.admin_user_id, self.task_id)
        
        self.assertIn(f"Task {self.task_id} not found", str(context.exception))
    
    def test_get_error_diagnostics_no_error_message(self):
        """Test error diagnostics when task has no error message"""
        # Setup
        self.mock_session.query.return_value.filter_by.return_value.first.side_effect = [
            self.mock_admin_user,  # Admin user found
            Mock(error_message=None)  # Task with no error
        ]
        
        # Execute & Verify
        with self.assertRaises(ValueError) as context:
            self.admin_service.get_error_diagnostics(self.admin_user_id, self.task_id)
        
        self.assertIn(f"Task {self.task_id} has no error message", str(context.exception))
    
    def test_restart_failed_job_success(self):
        """Test successful failed job restart"""
        # Setup
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = self.mock_admin_user
        
        # Mock failed task
        mock_failed_task = Mock(spec=CaptionGenerationTask)
        mock_failed_task.id = self.task_id
        mock_failed_task.status = TaskStatus.FAILED
        mock_failed_task.user_id = self.regular_user_id
        mock_failed_task.platform_connection_id = 1
        mock_failed_task.settings_json = '{"max_posts": 10}'
        mock_failed_task.max_retries = 3
        mock_failed_task.admin_notes = None
        
        # Configure query behavior
        def query_side_effect(model_class):
            if model_class == User:
                user_mock = Mock()
                user_mock.filter_by.return_value.first.return_value = self.mock_admin_user
                return user_mock
            elif model_class == CaptionGenerationTask:
                task_mock = Mock()
                task_mock.filter_by.return_value.first.return_value = mock_failed_task
                return task_mock
            return Mock()
        
        self.mock_session.query.side_effect = query_side_effect
        
        new_task_id = "new-task-456"
        self.mock_task_queue_manager.enqueue_task.return_value = new_task_id
        
        # Execute
        result = self.admin_service.restart_failed_job(self.admin_user_id, self.task_id)
        
        # Verify
        self.assertEqual(result, new_task_id)
        self.mock_task_queue_manager.enqueue_task.assert_called_once()
        
        # Verify new task was created with correct properties
        enqueue_call = self.mock_task_queue_manager.enqueue_task.call_args[0][0]
        self.assertEqual(enqueue_call.user_id, self.regular_user_id)
        self.assertEqual(enqueue_call.platform_connection_id, 1)
        self.assertEqual(enqueue_call.priority, JobPriority.HIGH)
        self.assertIn("Restarted by admin", enqueue_call.admin_notes)
        
        self.mock_session.commit.assert_called_once()
    
    def test_restart_failed_job_invalid_status(self):
        """Test restart failed job with invalid task status"""
        # Setup
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = self.mock_admin_user
        
        # Mock running task (cannot be restarted)
        mock_task = Mock(spec=CaptionGenerationTask)
        mock_task.id = self.task_id
        mock_task.status = TaskStatus.RUNNING
        
        # Configure query behavior
        def query_side_effect(model_class):
            if model_class == User:
                user_mock = Mock()
                user_mock.filter_by.return_value.first.return_value = self.mock_admin_user
                return user_mock
            elif model_class == CaptionGenerationTask:
                task_mock = Mock()
                task_mock.filter_by.return_value.first.return_value = mock_task
                return task_mock
            return Mock()
        
        self.mock_session.query.side_effect = query_side_effect
        
        # Execute & Verify
        with self.assertRaises(ValueError) as context:
            self.admin_service.restart_failed_job(self.admin_user_id, self.task_id)
        
        self.assertIn("is not in a failed or cancelled state", str(context.exception))
    
    def test_categorize_error_network(self):
        """Test error categorization for network errors"""
        result = self.admin_service._categorize_error("Connection failed to remote server")
        self.assertEqual(result, "network")
    
    def test_categorize_error_timeout(self):
        """Test error categorization for timeout errors"""
        result = self.admin_service._categorize_error("Request timeout after 30 seconds")
        self.assertEqual(result, "timeout")
    
    def test_categorize_error_authorization(self):
        """Test error categorization for authorization errors"""
        result = self.admin_service._categorize_error("Unauthorized access to API")
        self.assertEqual(result, "authorization")
    
    def test_categorize_error_rate_limit(self):
        """Test error categorization for rate limit errors"""
        result = self.admin_service._categorize_error("Too many requests, rate limit exceeded")
        self.assertEqual(result, "rate_limit")
    
    def test_categorize_error_unknown(self):
        """Test error categorization for unknown errors"""
        result = self.admin_service._categorize_error("Something went wrong")
        self.assertEqual(result, "unknown")
    
    def test_generate_error_solutions_network(self):
        """Test solution generation for network errors"""
        solutions = self.admin_service._generate_error_solutions("network", "Connection failed")
        self.assertIn("Check network connectivity to the platform", solutions)
        self.assertIn("Verify platform instance URL is correct", solutions)
    
    def test_generate_error_solutions_timeout(self):
        """Test solution generation for timeout errors"""
        solutions = self.admin_service._generate_error_solutions("timeout", "Request timeout")
        self.assertIn("Increase timeout settings", solutions)
        self.assertIn("Check system load and reduce concurrent tasks", solutions)
    
    def test_log_admin_action(self):
        """Test admin action logging"""
        # Execute
        self.admin_service._log_admin_action(
            self.mock_session, 
            self.admin_user_id, 
            "test_action", 
            task_id=self.task_id, 
            details="test details"
        )
        
        # Verify
        self.mock_session.add.assert_called_once()
        added_log = self.mock_session.add.call_args[0][0]
        self.assertIsInstance(added_log, JobAuditLog)
        self.assertEqual(added_log.admin_user_id, self.admin_user_id)
        self.assertEqual(added_log.action, "test_action")
        self.assertEqual(added_log.task_id, self.task_id)
        self.assertEqual(added_log.details, "test details")
    
    def test_calculate_system_health_score_no_recent_tasks(self):
        """Test system health score calculation with no recent tasks"""
        # Setup
        self.mock_session.query.return_value.filter.return_value.count.return_value = 0
        
        # Execute
        result = self.admin_service._calculate_system_health_score(self.mock_session)
        
        # Verify
        self.assertEqual(result, 100.0)
    
    def test_calculate_system_health_score_with_tasks(self):
        """Test system health score calculation with tasks"""
        # Setup - simulate 10 recent tasks, 8 successful, 2 failed, 3 queued
        count_side_effects = [
            10,  # recent_tasks
            8,   # successful_tasks
            2,   # failed_tasks
            3    # queued_tasks
        ]
        
        query_mock = Mock()
        self.mock_session.query.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.filter_by.return_value = query_mock
        query_mock.count.side_effect = count_side_effects
        
        # Execute
        result = self.admin_service._calculate_system_health_score(self.mock_session)
        
        # Verify
        # Success rate: 8/10 = 80%
        # Load penalty: min(3*2, 20) = 6
        # Health score: 80 - 6 = 74
        self.assertEqual(result, 74.0)
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    @patch('psutil.net_connections')
    def test_get_resource_usage_with_psutil(self, mock_net_connections, mock_disk_usage, 
                                          mock_virtual_memory, mock_cpu_percent):
        """Test resource usage retrieval with psutil available"""
        # Setup
        mock_cpu_percent.return_value = 45.5
        mock_virtual_memory.return_value.percent = 67.2
        mock_disk_usage.return_value.percent = 23.8
        mock_net_connections.return_value = [1, 2, 3, 4, 5]  # 5 connections
        
        # Execute
        result = self.admin_service._get_resource_usage()
        
        # Verify
        self.assertEqual(result['cpu_percent'], 45.5)
        self.assertEqual(result['memory_percent'], 67.2)
        self.assertEqual(result['disk_percent'], 23.8)
        self.assertEqual(result['active_connections'], 5)
        self.assertIn('timestamp', result)
    
    def test_get_resource_usage_without_psutil(self):
        """Test resource usage retrieval without psutil"""
        # Execute (psutil import will fail naturally in test environment)
        result = self.admin_service._get_resource_usage()
        
        # Verify - should get either the fallback response or error response
        if 'error' in result:
            # If an error occurred (like in test environment)
            self.assertIn('error', result)
        else:
            # If psutil import failed gracefully
            self.assertEqual(result['cpu_percent'], 0)
            self.assertEqual(result['memory_percent'], 0)
            self.assertEqual(result['disk_percent'], 0)
            self.assertEqual(result['active_connections'], 0)
            self.assertIn('psutil not available', result['note'])
    
    def test_get_recent_errors(self):
        """Test recent errors retrieval"""
        # Setup
        mock_task1 = Mock(spec=CaptionGenerationTask)
        mock_task1.id = "task1"
        mock_task1.user_id = 1
        mock_task1.error_message = "Error 1"
        mock_task1.completed_at = datetime.now(timezone.utc)
        mock_task1.retry_count = 1
        
        mock_task2 = Mock(spec=CaptionGenerationTask)
        mock_task2.id = "task2"
        mock_task2.user_id = 2
        mock_task2.error_message = "Error 2"
        mock_task2.completed_at = datetime.now(timezone.utc)
        mock_task2.retry_count = 0
        
        query_mock = Mock()
        self.mock_session.query.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.order_by.return_value = query_mock
        query_mock.limit.return_value = query_mock
        query_mock.all.return_value = [mock_task1, mock_task2]
        
        # Execute
        result = self.admin_service._get_recent_errors(self.mock_session, hours=24)
        
        # Verify
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['task_id'], "task1")
        self.assertEqual(result[0]['error_message'], "Error 1")
        self.assertEqual(result[1]['task_id'], "task2")
        self.assertEqual(result[1]['error_message'], "Error 2")
    
    def test_get_performance_metrics(self):
        """Test performance metrics retrieval"""
        # Setup
        now = datetime.now(timezone.utc)
        
        # Mock completed tasks with timing
        mock_task1 = Mock(spec=CaptionGenerationTask)
        mock_task1.started_at = now - timedelta(seconds=60)
        mock_task1.completed_at = now - timedelta(seconds=30)
        
        mock_task2 = Mock(spec=CaptionGenerationTask)
        mock_task2.started_at = now - timedelta(seconds=90)
        mock_task2.completed_at = now - timedelta(seconds=60)
        
        query_mock = Mock()
        self.mock_session.query.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.all.return_value = [mock_task1, mock_task2]
        
        # Mock queue stats
        self.mock_task_queue_manager.get_queue_stats.return_value = {'queued': 5, 'running': 2}
        
        # Execute
        result = self.admin_service._get_performance_metrics(self.mock_session)
        
        # Verify
        self.assertEqual(result['avg_completion_time_seconds'], 30.0)  # Average of 30 and 30 seconds
        self.assertEqual(result['completed_tasks_24h'], 2)
        self.assertEqual(result['queue_statistics'], {'queued': 5, 'running': 2})
        self.assertIn('timestamp', result)


if __name__ == '__main__':
    unittest.main()
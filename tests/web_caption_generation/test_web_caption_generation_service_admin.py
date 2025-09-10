# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for WebCaptionGenerationService admin capabilities

Tests the enhanced admin methods added to WebCaptionGenerationService for
multi-tenant caption management.
"""

import unittest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any

from config import Config
from app.core.database.core.database_manager import DatabaseManager
from models import (
    User, UserRole, CaptionGenerationTask, TaskStatus, PlatformConnection,
    JobPriority, JobAuditLog
)
from sqlalchemy import or_
from app.utils.processing.web_caption_generation_service import WebCaptionGenerationService
from tests.test_helpers import create_test_user_with_platforms, cleanup_test_user


class TestWebCaptionGenerationServiceAdmin(unittest.TestCase):
    """Test cases for WebCaptionGenerationService admin capabilities"""
    
    def setUp(self):
        """Set up test environment"""
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        self.service = WebCaptionGenerationService(self.db_manager)
        
        # Create test users with unique names
        import uuid
        unique_suffix = str(uuid.uuid4())[:8]
        
        self.admin_user, self.admin_helper = create_test_user_with_platforms(
            self.db_manager, username=f"test_admin_{unique_suffix}", role=UserRole.ADMIN
        )
        self.regular_user, self.regular_helper = create_test_user_with_platforms(
            self.db_manager, username=f"test_user_{unique_suffix}", role=UserRole.REVIEWER
        )
        self.non_admin_user, self.non_admin_helper = create_test_user_with_platforms(
            self.db_manager, username=f"test_non_admin_{unique_suffix}", role=UserRole.VIEWER
        )
        
        # Create test tasks
        self.test_tasks = self._create_test_tasks()
    
    def tearDown(self):
        """Clean up test environment"""
        # Clean up test tasks and audit logs
        session = self.db_manager.get_session()
        try:
            # Clean up audit logs first (due to foreign key constraints)
            audit_logs = session.query(JobAuditLog).filter(
                or_(
                    JobAuditLog.admin_user_id == self.admin_user.id,
                    JobAuditLog.user_id == self.regular_user.id,
                    JobAuditLog.user_id == self.non_admin_user.id
                )
            ).all()
            for audit_log in audit_logs:
                session.delete(audit_log)
            
            # Clean up test tasks
            for task in self.test_tasks:
                session.delete(task)
            session.commit()
        except Exception:
            session.rollback()
        finally:
            session.close()
        
        # Clean up test users
        cleanup_test_user(self.admin_helper)
        cleanup_test_user(self.regular_helper)
        cleanup_test_user(self.non_admin_helper)
    
    def _create_test_tasks(self) -> List[CaptionGenerationTask]:
        """Create test tasks for testing"""
        session = self.db_manager.get_session()
        try:
            tasks = []
            
            # Get the first platform connection for the regular user
            platform_connection_id = self.regular_user.platform_connections[0].id
            
            # Active task for regular user
            active_task = CaptionGenerationTask(
                id="test-active-task",
                user_id=self.regular_user.id,
                platform_connection_id=platform_connection_id,
                status=TaskStatus.RUNNING,
                priority=JobPriority.NORMAL,
                created_at=datetime.now(timezone.utc),
                started_at=datetime.now(timezone.utc),
                progress_percent=50,
                current_step="Processing images"
            )
            session.add(active_task)
            tasks.append(active_task)
            
            # Queued task for regular user
            queued_task = CaptionGenerationTask(
                id="test-queued-task",
                user_id=self.regular_user.id,
                platform_connection_id=platform_connection_id,
                status=TaskStatus.QUEUED,
                priority=JobPriority.HIGH,
                created_at=datetime.now(timezone.utc)
            )
            session.add(queued_task)
            tasks.append(queued_task)
            
            # Completed task for regular user
            completed_task = CaptionGenerationTask(
                id="test-completed-task",
                user_id=self.regular_user.id,
                platform_connection_id=platform_connection_id,
                status=TaskStatus.COMPLETED,
                priority=JobPriority.NORMAL,
                created_at=datetime.now(timezone.utc) - timedelta(hours=2),
                started_at=datetime.now(timezone.utc) - timedelta(hours=2),
                completed_at=datetime.now(timezone.utc) - timedelta(hours=1),
                progress_percent=100,
                current_step="Completed"
            )
            session.add(completed_task)
            tasks.append(completed_task)
            
            # Failed task for regular user
            failed_task = CaptionGenerationTask(
                id="test-failed-task",
                user_id=self.regular_user.id,
                platform_connection_id=platform_connection_id,
                status=TaskStatus.FAILED,
                priority=JobPriority.NORMAL,
                created_at=datetime.now(timezone.utc) - timedelta(hours=3),
                started_at=datetime.now(timezone.utc) - timedelta(hours=3),
                completed_at=datetime.now(timezone.utc) - timedelta(hours=2, minutes=30),
                progress_percent=75,
                current_step="Failed",
                error_message="Test error message",
                retry_count=2,
                max_retries=3
            )
            session.add(failed_task)
            tasks.append(failed_task)
            
            session.commit()
            return tasks
            
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def test_verify_admin_authorization_success(self):
        """Test successful admin authorization verification"""
        session = self.db_manager.get_session()
        try:
            admin_user = self.service._verify_admin_authorization(session, self.admin_user.id)
            self.assertEqual(admin_user.id, self.admin_user.id)
            self.assertEqual(admin_user.role, UserRole.ADMIN)
        finally:
            session.close()
    
    def test_verify_admin_authorization_non_admin_fails(self):
        """Test admin authorization verification fails for non-admin user"""
        session = self.db_manager.get_session()
        try:
            with self.assertRaises(ValueError) as context:
                self.service._verify_admin_authorization(session, self.non_admin_user.id)
            
            self.assertIn("not authorized for admin operations", str(context.exception))
        finally:
            session.close()
    
    def test_verify_admin_authorization_nonexistent_user_fails(self):
        """Test admin authorization verification fails for nonexistent user"""
        session = self.db_manager.get_session()
        try:
            with self.assertRaises(ValueError) as context:
                self.service._verify_admin_authorization(session, 99999)
            
            self.assertIn("not found", str(context.exception))
        finally:
            session.close()
    
    def test_log_admin_action(self):
        """Test admin action logging"""
        session = self.db_manager.get_session()
        try:
            # Create a test task first with unique ID
            import uuid
            test_task_id = f"test-audit-task-{str(uuid.uuid4())[:8]}"
            test_task = CaptionGenerationTask(
                id=test_task_id,
                user_id=self.regular_user.id,
                platform_connection_id=self.regular_user.platform_connections[0].id,
                status=TaskStatus.COMPLETED
            )
            session.add(test_task)
            session.commit()
            
            # Log an admin action
            self.service._log_admin_action(
                session, 
                self.admin_user.id, 
                "test_action",
                task_id=test_task_id,
                details="test details"
            )
            session.commit()
            
            # Verify the audit log was created
            audit_log = session.query(JobAuditLog).filter_by(
                admin_user_id=self.admin_user.id,
                action="test_action"
            ).first()
            
            self.assertIsNotNone(audit_log)
            self.assertEqual(audit_log.task_id, test_task_id)
            self.assertEqual(audit_log.details, "test details")
            self.assertEqual(audit_log.admin_user_id, self.admin_user.id)
            
        finally:
            session.close()
    
    def test_get_all_active_jobs_success(self):
        """Test successful retrieval of all active jobs"""
        jobs = self.service.get_all_active_jobs(self.admin_user.id)
        
        # Should return active (queued and running) tasks
        self.assertIsInstance(jobs, list)
        self.assertGreaterEqual(len(jobs), 2)  # At least the queued and running tasks
        
        # Check that only active jobs are returned
        for job in jobs:
            self.assertIn(job['status'], ['queued', 'running'])
            self.assertIn('task_id', job)
            self.assertIn('username', job)
            self.assertIn('platform_name', job)
            self.assertIn('priority', job)
            self.assertIn('created_at', job)
            self.assertIn('progress_percent', job)
    
    def test_get_all_active_jobs_non_admin_fails(self):
        """Test get_all_active_jobs fails for non-admin user"""
        with self.assertRaises(ValueError) as context:
            self.service.get_all_active_jobs(self.non_admin_user.id)
        
        self.assertIn("not authorized for admin operations", str(context.exception))
    
    def test_cancel_user_job_success(self):
        """Test successful cancellation of user job by admin"""
        # Mock the task queue manager's cancel method
        with patch.object(self.service.task_queue_manager, 'cancel_task_as_admin', return_value=True):
            success = self.service.cancel_user_job(
                self.admin_user.id, 
                "test-active-task", 
                "Admin cancellation for testing"
            )
            
            self.assertTrue(success)
    
    def test_cancel_user_job_non_admin_fails(self):
        """Test cancel_user_job fails for non-admin user"""
        with self.assertRaises(ValueError) as context:
            self.service.cancel_user_job(
                self.non_admin_user.id, 
                "test-active-task", 
                "Unauthorized cancellation"
            )
        
        self.assertIn("not authorized for admin operations", str(context.exception))
    
    def test_cancel_user_job_failure(self):
        """Test cancel_user_job handles failure gracefully"""
        # Mock the task queue manager's cancel method to return False
        with patch.object(self.service.task_queue_manager, 'cancel_task_as_admin', return_value=False):
            success = self.service.cancel_user_job(
                self.admin_user.id, 
                "nonexistent-task", 
                "Admin cancellation for testing"
            )
            
            self.assertFalse(success)
    
    def test_get_system_metrics_success(self):
        """Test successful retrieval of system metrics"""
        # Mock the task queue manager's get_queue_statistics method
        mock_queue_stats = {
            'total_tasks': 10,
            'queued_tasks': 2,
            'running_tasks': 1,
            'completed_tasks': 6,
            'failed_tasks': 1
        }
        
        with patch.object(self.service.task_queue_manager, 'get_queue_statistics', return_value=mock_queue_stats):
            metrics = self.service.get_system_metrics(self.admin_user.id)
            
            self.assertIsInstance(metrics, dict)
            self.assertIn('timestamp', metrics)
            self.assertIn('queue_statistics', metrics)
            self.assertIn('service_statistics', metrics)
            self.assertIn('performance_metrics', metrics)
            self.assertIn('resource_usage', metrics)
            
            # Check performance metrics structure
            perf_metrics = metrics['performance_metrics']
            self.assertIn('completed_tasks_24h', perf_metrics)
            self.assertIn('failed_tasks_24h', perf_metrics)
            self.assertIn('success_rate_percent', perf_metrics)
            self.assertIn('avg_completion_time_seconds', perf_metrics)
    
    def test_get_system_metrics_non_admin_fails(self):
        """Test get_system_metrics fails for non-admin user"""
        with self.assertRaises(ValueError) as context:
            self.service.get_system_metrics(self.non_admin_user.id)
        
        self.assertIn("not authorized for admin operations", str(context.exception))
    
    def test_get_job_history_success(self):
        """Test successful retrieval of job history"""
        history = self.service.get_job_history(self.admin_user.id, limit=50)
        
        self.assertIsInstance(history, list)
        self.assertGreaterEqual(len(history), 4)  # Should include all test tasks
        
        # Check job history structure
        for job in history:
            self.assertIn('task_id', job)
            self.assertIn('username', job)
            self.assertIn('platform_name', job)
            self.assertIn('status', job)
            self.assertIn('created_at', job)
            self.assertIn('priority', job)
    
    def test_get_job_history_with_filters(self):
        """Test job history retrieval with filters"""
        # Filter by user ID
        filters = {'user_id': self.regular_user.id}
        history = self.service.get_job_history(self.admin_user.id, filters=filters)
        
        self.assertIsInstance(history, list)
        for job in history:
            self.assertEqual(job['user_id'], self.regular_user.id)
        
        # Filter by status
        filters = {'status': ['completed', 'failed']}
        history = self.service.get_job_history(self.admin_user.id, filters=filters)
        
        for job in history:
            self.assertIn(job['status'], ['completed', 'failed'])
    
    def test_get_job_history_non_admin_fails(self):
        """Test get_job_history fails for non-admin user"""
        with self.assertRaises(ValueError) as context:
            self.service.get_job_history(self.non_admin_user.id)
        
        self.assertIn("not authorized for admin operations", str(context.exception))
    
    def test_get_generation_status_with_admin_access(self):
        """Test get_generation_status with admin access bypasses authorization"""
        # Admin should be able to access any user's task
        status = self.service.get_generation_status(
            "test-active-task", 
            user_id=self.admin_user.id,  # Different user than task owner
            admin_access=True
        )
        
        self.assertIsNotNone(status)
        self.assertEqual(status['task_id'], "test-active-task")
        self.assertEqual(status['status'], 'running')
    
    def test_get_generation_status_without_admin_access_fails(self):
        """Test get_generation_status without admin access enforces authorization"""
        # Non-owner should not be able to access task without admin access
        status = self.service.get_generation_status(
            "test-active-task", 
            user_id=self.admin_user.id,  # Different user than task owner
            admin_access=False
        )
        
        self.assertIsNone(status)
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    @patch('psutil.net_connections')
    def test_get_system_metrics_with_psutil(self, mock_net_connections, mock_disk_usage, mock_virtual_memory, mock_cpu_percent):
        """Test system metrics with psutil available"""
        # Mock psutil functions
        mock_cpu_percent.return_value = 25.5
        mock_virtual_memory.return_value.percent = 60.2
        mock_disk_usage.return_value.percent = 45.8
        mock_net_connections.return_value = ['conn1', 'conn2', 'conn3']
        
        # Mock queue statistics
        mock_queue_stats = {'total_tasks': 5}
        with patch.object(self.service.task_queue_manager, 'get_queue_statistics', return_value=mock_queue_stats):
            metrics = self.service.get_system_metrics(self.admin_user.id)
            
            resource_usage = metrics['resource_usage']
            self.assertEqual(resource_usage['cpu_percent'], 25.5)
            self.assertEqual(resource_usage['memory_percent'], 60.2)
            self.assertEqual(resource_usage['disk_percent'], 45.8)
            self.assertEqual(resource_usage['active_connections'], 3)
    
    def test_get_system_metrics_without_psutil(self):
        """Test system metrics without psutil available"""
        # Mock ImportError for psutil
        with patch('builtins.__import__', side_effect=lambda name, *args: ImportError() if name == 'psutil' else __import__(name, *args)):
            with patch.object(self.service.task_queue_manager, 'get_queue_statistics', return_value={}):
                metrics = self.service.get_system_metrics(self.admin_user.id)
                
                resource_usage = metrics['resource_usage']
                self.assertEqual(resource_usage['cpu_percent'], 0)
                self.assertEqual(resource_usage['memory_percent'], 0)
                self.assertEqual(resource_usage['disk_percent'], 0)
                self.assertIn('note', resource_usage)
    
    def test_enhanced_error_recovery_integration(self):
        """Test integration with enhanced error recovery system"""
        # This test verifies that the enhanced error recovery manager is properly integrated
        self.assertIsNotNone(self.service.enhanced_error_recovery)
        
        # Test that the enhanced error recovery manager has the expected methods
        self.assertTrue(hasattr(self.service.enhanced_error_recovery, 'create_enhanced_error_info'))
        self.assertTrue(hasattr(self.service.enhanced_error_recovery, '_get_user_friendly_message'))


if __name__ == '__main__':
    unittest.main()
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
End-to-End Tests for Multi-Tenant Caption Management

This module provides comprehensive end-to-end testing for the multi-tenant caption
management system, testing complete user and admin workflows from start to finish.
"""

import unittest
import time
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta

from config import Config
from app.core.database.core.database_manager import DatabaseManager
from models import User, UserRole, CaptionGenerationTask, TaskStatus, JobPriority, PlatformConnection
from app.services.admin.components.admin_management_service import AdminManagementService, SystemOverview
from app.services.batch.components.multi_tenant_control_service import MultiTenantControlService, UserJobLimits, RateLimits
from web_caption_generation_service import WebCaptionGenerationService
from app.services.task.core.task_queue_manager import TaskQueueManager
from app.services.monitoring.system.system_monitor import SystemMonitor
from app.services.alerts.components.alert_manager import AlertManager
from audit_logger import AuditLogger

# Import test helpers
from tests.test_helpers.mock_user_helper import MockUserHelper, create_test_user_with_platforms, cleanup_test_user
from tests.test_helpers.database_mock_helpers import DatabaseMockHelper


class TestCompleteUserWorkflow(unittest.TestCase):
    """Test complete user workflow from job creation to completion"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = Config()
        
        # Try to use real database for E2E tests
        try:
            self.db_manager = DatabaseManager(self.config)
            self.use_real_db = True
        except Exception:
            self.db_manager = Mock(spec=DatabaseManager)
            self.use_real_db = False
        
        # Create user helper and services
        self.user_helper = MockUserHelper(self.db_manager)
        self.task_queue_manager = Mock(spec=TaskQueueManager)
        self.web_service = WebCaptionGenerationService(self.db_manager, self.task_queue_manager)
        
        # Create test user if using real database
        if self.use_real_db:
            self.test_user = self.user_helper.create_mock_user(
                username="e2e_user_workflow",
                role=UserRole.REVIEWER,
                with_platforms=True
            )
        else:
            # Create mock user for mock database
            self.test_user = Mock(spec=User)
            self.test_user.id = 1
            self.test_user.username = "e2e_user_workflow"
            self.test_user.role = UserRole.REVIEWER
            
            # Mock platform connection
            mock_platform = Mock(spec=PlatformConnection)
            mock_platform.id = 1
            mock_platform.user_id = 1
            mock_platform.name = "Test Platform"
            self.test_user.platform_connections = [mock_platform]
    
    def tearDown(self):
        """Clean up test fixtures"""
        if self.use_real_db:
            self.user_helper.cleanup_mock_users()
    
    def test_user_job_creation_workflow(self):
        """Test complete user job creation workflow"""
        if not self.use_real_db:
            self.skipTest("Requires real database for E2E testing")
        
        # Step 1: User starts caption generation job
        job_settings = {
            "max_posts": 5,
            "include_replies": False,
            "min_image_size": 100
        }
        
        task_id = self.web_service.start_caption_generation(
            user_id=self.test_user.id,
            platform_connection_id=self.test_user.platform_connections[0].id,
            settings=job_settings
        )
        
        self.assertIsNotNone(task_id, "Task ID should be returned")
        self.assertIsInstance(task_id, str, "Task ID should be a string")
        
        # Step 2: User checks initial job status
        initial_status = self.web_service.get_generation_status(task_id, self.test_user.id)
        
        self.assertIsNotNone(initial_status, "Initial status should be available")
        self.assertIn('status', initial_status, "Status should contain 'status' field")
        self.assertIn('progress', initial_status, "Status should contain 'progress' field")
        self.assertIn('task_id', initial_status, "Status should contain 'task_id' field")
        self.assertEqual(initial_status['task_id'], task_id, "Task ID should match")
        
        # Step 3: Simulate job progress updates
        time.sleep(0.1)  # Brief delay to simulate processing
        
        progress_status = self.web_service.get_generation_status(task_id, self.test_user.id)
        self.assertIsNotNone(progress_status, "Progress status should be available")
        
        # Step 4: User views job history
        job_history = self.web_service.get_user_job_history(self.test_user.id)
        
        self.assertIsInstance(job_history, list, "Job history should be a list")
        self.assertGreater(len(job_history), 0, "Job history should contain at least one job")
        
        # Verify the current job is in history
        current_job_in_history = any(job['task_id'] == task_id for job in job_history)
        self.assertTrue(current_job_in_history, "Current job should appear in history")
        
        # Step 5: User cancels the job
        cancel_result = self.web_service.cancel_generation(task_id, self.test_user.id)
        self.assertTrue(cancel_result, "Job cancellation should succeed")
        
        # Step 6: Verify job was cancelled
        final_status = self.web_service.get_generation_status(task_id, self.test_user.id)
        self.assertEqual(final_status['status'], TaskStatus.CANCELLED.value, "Job should be cancelled")
    
    def test_user_job_completion_workflow(self):
        """Test user workflow when job completes successfully"""
        if not self.use_real_db:
            self.skipTest("Requires real database for E2E testing")
        
        # Step 1: Start a job that will complete quickly
        task_id = self.web_service.start_caption_generation(
            user_id=self.test_user.id,
            platform_connection_id=self.test_user.platform_connections[0].id,
            settings={"max_posts": 1}  # Small job for quick completion
        )
        
        # Step 2: Monitor job until completion (with timeout)
        max_wait_time = 30  # 30 seconds timeout
        start_time = time.time()
        final_status = None
        
        while time.time() - start_time < max_wait_time:
            status = self.web_service.get_generation_status(task_id, self.test_user.id)
            
            if status['status'] in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value, TaskStatus.CANCELLED.value]:
                final_status = status
                break
            
            time.sleep(1)  # Wait 1 second before checking again
        
        self.assertIsNotNone(final_status, "Job should complete within timeout period")
        
        # Step 3: Verify completion details
        if final_status['status'] == TaskStatus.COMPLETED.value:
            self.assertIn('results', final_status, "Completed job should have results")
            self.assertIn('completion_time', final_status, "Completed job should have completion time")
        
        # Step 4: Check job appears correctly in history
        job_history = self.web_service.get_user_job_history(self.test_user.id)
        completed_job = next((job for job in job_history if job['task_id'] == task_id), None)
        
        self.assertIsNotNone(completed_job, "Completed job should appear in history")
        self.assertEqual(completed_job['status'], final_status['status'], "History status should match final status")
    
    def test_user_multiple_jobs_workflow(self):
        """Test user workflow with multiple concurrent jobs (should be prevented)"""
        if not self.use_real_db:
            self.skipTest("Requires real database for E2E testing")
        
        # Step 1: Start first job
        first_task_id = self.web_service.start_caption_generation(
            user_id=self.test_user.id,
            platform_connection_id=self.test_user.platform_connections[0].id,
            settings={"max_posts": 3}
        )
        
        self.assertIsNotNone(first_task_id, "First job should start successfully")
        
        # Step 2: Attempt to start second job (should be prevented)
        second_task_id = self.web_service.start_caption_generation(
            user_id=self.test_user.id,
            platform_connection_id=self.test_user.platform_connections[0].id,
            settings={"max_posts": 2}
        )
        
        # Depending on implementation, this might return None or raise an exception
        if second_task_id is not None:
            # If second job was allowed, verify it's queued appropriately
            second_status = self.web_service.get_generation_status(second_task_id, self.test_user.id)
            self.assertIn(second_status['status'], [TaskStatus.QUEUED.value, TaskStatus.PENDING.value])
        
        # Step 3: Cancel first job to clean up
        cancel_result = self.web_service.cancel_generation(first_task_id, self.test_user.id)
        self.assertTrue(cancel_result, "First job cancellation should succeed")
        
        # Step 4: If second job exists, cancel it too
        if second_task_id is not None:
            cancel_result = self.web_service.cancel_generation(second_task_id, self.test_user.id)
            self.assertTrue(cancel_result, "Second job cancellation should succeed")


class TestCompleteAdminWorkflow(unittest.TestCase):
    """Test complete admin workflow from monitoring to job management"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = Config()
        
        # Try to use real database for E2E tests
        try:
            self.db_manager = DatabaseManager(self.config)
            self.use_real_db = True
        except Exception:
            self.db_manager = Mock(spec=DatabaseManager)
            self.use_real_db = False
        
        # Create user helper and services
        self.user_helper = MockUserHelper(self.db_manager)
        self.task_queue_manager = Mock(spec=TaskQueueManager)
        self.admin_service = AdminManagementService(self.db_manager, self.task_queue_manager)
        self.multi_tenant_service = MultiTenantControlService(self.db_manager)
        self.web_service = WebCaptionGenerationService(self.db_manager, self.task_queue_manager)
        self.system_monitor = SystemMonitor(self.db_manager)
        
        # Create test users if using real database
        if self.use_real_db:
            self.admin_user = self.user_helper.create_mock_user(
                username="e2e_admin_workflow",
                role=UserRole.ADMIN,
                with_platforms=True
            )
            self.regular_user = self.user_helper.create_mock_user(
                username="e2e_regular_user",
                role=UserRole.REVIEWER,
                with_platforms=True
            )
        else:
            # Create mock users for mock database
            self.admin_user = Mock(spec=User)
            self.admin_user.id = 1
            self.admin_user.role = UserRole.ADMIN
            
            self.regular_user = Mock(spec=User)
            self.regular_user.id = 2
            self.regular_user.role = UserRole.REVIEWER
    
    def tearDown(self):
        """Clean up test fixtures"""
        if self.use_real_db:
            self.user_helper.cleanup_mock_users()
    
    def test_admin_system_monitoring_workflow(self):
        """Test complete admin system monitoring workflow"""
        if not self.use_real_db:
            self.skipTest("Requires real database for E2E testing")
        
        # Step 1: Admin views system overview
        overview = self.admin_service.get_system_overview(self.admin_user.id)
        
        self.assertIsInstance(overview, SystemOverview, "Should return SystemOverview object")
        self.assertGreaterEqual(overview.total_users, 2, "Should show at least 2 users (admin + regular)")
        self.assertIsNotNone(overview.system_health_score, "Should have system health score")
        self.assertIsNotNone(overview.active_tasks, "Should have active tasks count")
        
        # Step 2: Admin checks system resource usage
        resource_usage = self.multi_tenant_service.get_resource_usage()
        
        self.assertIsNotNone(resource_usage, "Should return resource usage data")
        self.assertHasAttr(resource_usage, 'cpu_percent', "Should have CPU percentage")
        self.assertHasAttr(resource_usage, 'memory_percent', "Should have memory percentage")
        
        # Step 3: Admin configures system settings
        rate_limits = RateLimits(
            global_max_concurrent_jobs=15,
            max_jobs_per_minute=8,
            max_jobs_per_hour=200
        )
        
        config_result = self.multi_tenant_service.configure_rate_limits(self.admin_user.id, rate_limits)
        self.assertTrue(config_result, "Rate limit configuration should succeed")
        
        # Step 4: Admin sets user-specific limits
        user_limits = UserJobLimits(
            max_concurrent_jobs=2,
            max_jobs_per_hour=20,
            max_jobs_per_day=100
        )
        
        user_config_result = self.multi_tenant_service.set_user_job_limits(
            self.admin_user.id,
            self.regular_user.id,
            user_limits
        )
        self.assertTrue(user_config_result, "User limit configuration should succeed")
        
        # Step 5: Admin verifies configuration was applied
        retrieved_limits = self.multi_tenant_service.get_user_job_limits(self.regular_user.id)
        self.assertEqual(retrieved_limits.max_concurrent_jobs, 2, "User limits should be applied")
        self.assertEqual(retrieved_limits.max_jobs_per_hour, 20, "User limits should be applied")
    
    def test_admin_job_management_workflow(self):
        """Test complete admin job management workflow"""
        if not self.use_real_db:
            self.skipTest("Requires real database for E2E testing")
        
        # Step 1: Regular user starts a job
        user_task_id = self.web_service.start_caption_generation(
            user_id=self.regular_user.id,
            platform_connection_id=self.regular_user.platform_connections[0].id,
            settings={"max_posts": 3}
        )
        
        self.assertIsNotNone(user_task_id, "User job should start successfully")
        
        # Step 2: Admin views all user jobs
        user_job_details = self.admin_service.get_user_job_details(
            self.admin_user.id,
            self.regular_user.id
        )
        
        self.assertIsInstance(user_job_details, list, "Should return list of job details")
        self.assertGreater(len(user_job_details), 0, "Should show at least one job")
        
        # Find the current job in the details
        current_job = next((job for job in user_job_details if job.task_id == user_task_id), None)
        self.assertIsNotNone(current_job, "Current job should appear in admin view")
        
        # Step 3: Admin gets error diagnostics (if job has errors)
        try:
            diagnostics = self.admin_service.get_error_diagnostics(self.admin_user.id, user_task_id)
            # If this succeeds, the job has errors
            self.assertIsNotNone(diagnostics.error_message, "Diagnostics should have error message")
            self.assertIsNotNone(diagnostics.suggested_solutions, "Diagnostics should have solutions")
        except ValueError:
            # Job doesn't have errors, which is fine
            pass
        
        # Step 4: Admin cancels the user's job
        cancel_reason = "E2E test admin cancellation"
        cancel_result = self.admin_service.cancel_job_as_admin(
            self.admin_user.id,
            user_task_id,
            cancel_reason
        )
        
        self.assertTrue(cancel_result, "Admin job cancellation should succeed")
        
        # Step 5: Verify job was cancelled and user can see the cancellation
        final_status = self.web_service.get_generation_status(user_task_id, self.regular_user.id)
        self.assertEqual(final_status['status'], TaskStatus.CANCELLED.value, "Job should be cancelled")
        
        # Step 6: Admin views updated system overview
        updated_overview = self.admin_service.get_system_overview(self.admin_user.id)
        self.assertIsInstance(updated_overview, SystemOverview, "Should return updated overview")
    
    def test_admin_maintenance_mode_workflow(self):
        """Test admin maintenance mode workflow"""
        # Step 1: Admin enables maintenance mode
        pause_result = self.multi_tenant_service.pause_system_jobs(
            self.admin_user.id,
            "E2E test maintenance mode"
        )
        self.assertTrue(pause_result, "Maintenance mode activation should succeed")
        
        # Step 2: Verify maintenance mode is active
        is_maintenance = self.multi_tenant_service.is_maintenance_mode()
        self.assertTrue(is_maintenance, "System should be in maintenance mode")
        
        # Step 3: Get maintenance reason
        maintenance_reason = self.multi_tenant_service.get_maintenance_reason()
        self.assertEqual(maintenance_reason, "E2E test maintenance mode", "Maintenance reason should match")
        
        # Step 4: Admin disables maintenance mode
        resume_result = self.multi_tenant_service.resume_system_jobs(self.admin_user.id)
        self.assertTrue(resume_result, "Maintenance mode deactivation should succeed")
        
        # Step 5: Verify maintenance mode is disabled
        is_maintenance = self.multi_tenant_service.is_maintenance_mode()
        self.assertFalse(is_maintenance, "System should not be in maintenance mode")


class TestMultiUserAdminScenario(unittest.TestCase):
    """Test scenario with multiple users and admin oversight"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = Config()
        
        # Try to use real database for E2E tests
        try:
            self.db_manager = DatabaseManager(self.config)
            self.use_real_db = True
        except Exception:
            self.db_manager = Mock(spec=DatabaseManager)
            self.use_real_db = False
        
        # Create user helper and services
        self.user_helper = MockUserHelper(self.db_manager)
        self.task_queue_manager = Mock(spec=TaskQueueManager)
        self.admin_service = AdminManagementService(self.db_manager, self.task_queue_manager)
        self.multi_tenant_service = MultiTenantControlService(self.db_manager)
        self.web_service = WebCaptionGenerationService(self.db_manager, self.task_queue_manager)
        
        # Create test users if using real database
        if self.use_real_db:
            self.admin_user = self.user_helper.create_mock_user(
                username="e2e_multi_admin",
                role=UserRole.ADMIN,
                with_platforms=True
            )
            
            # Create multiple regular users
            self.regular_users = []
            for i in range(3):
                user = self.user_helper.create_mock_user(
                    username=f"e2e_multi_user_{i}",
                    role=UserRole.REVIEWER,
                    with_platforms=True
                )
                self.regular_users.append(user)
        else:
            # Create mock users for mock database
            self.admin_user = Mock(spec=User)
            self.admin_user.id = 1
            self.admin_user.role = UserRole.ADMIN
            
            self.regular_users = []
            for i in range(3):
                user = Mock(spec=User)
                user.id = i + 2
                user.role = UserRole.REVIEWER
                self.regular_users.append(user)
    
    def tearDown(self):
        """Clean up test fixtures"""
        if self.use_real_db:
            self.user_helper.cleanup_mock_users()
    
    def test_multi_user_job_management_scenario(self):
        """Test scenario with multiple users creating jobs and admin managing them"""
        if not self.use_real_db:
            self.skipTest("Requires real database for E2E testing")
        
        # Step 1: Multiple users start jobs
        user_task_ids = []
        for i, user in enumerate(self.regular_users):
            task_id = self.web_service.start_caption_generation(
                user_id=user.id,
                platform_connection_id=user.platform_connections[0].id,
                settings={"max_posts": 2 + i}  # Different job sizes
            )
            user_task_ids.append((user.id, task_id))
        
        self.assertEqual(len(user_task_ids), 3, "All users should have started jobs")
        
        # Step 2: Admin views system overview with multiple active jobs
        overview = self.admin_service.get_system_overview(self.admin_user.id)
        self.assertGreaterEqual(overview.active_tasks, 3, "Should show at least 3 active tasks")
        
        # Step 3: Admin sets different limits for different users
        for i, user in enumerate(self.regular_users):
            limits = UserJobLimits(
                max_concurrent_jobs=i + 1,  # Different limits for each user
                max_jobs_per_hour=10 * (i + 1)
            )
            
            result = self.multi_tenant_service.set_user_job_limits(
                self.admin_user.id,
                user.id,
                limits
            )
            self.assertTrue(result, f"Should set limits for user {i}")
        
        # Step 4: Admin manages individual user jobs
        for user_id, task_id in user_task_ids[:2]:  # Cancel first 2 jobs
            cancel_result = self.admin_service.cancel_job_as_admin(
                self.admin_user.id,
                task_id,
                f"Multi-user test cancellation for user {user_id}"
            )
            self.assertTrue(cancel_result, f"Should cancel job {task_id}")
        
        # Step 5: Admin enables maintenance mode
        pause_result = self.multi_tenant_service.pause_system_jobs(
            self.admin_user.id,
            "Multi-user test maintenance"
        )
        self.assertTrue(pause_result, "Should enable maintenance mode")
        
        # Step 6: Verify remaining job is affected by maintenance mode
        remaining_user_id, remaining_task_id = user_task_ids[2]
        remaining_status = self.web_service.get_generation_status(remaining_task_id, remaining_user_id)
        
        # Job might be paused or continue running depending on implementation
        self.assertIsNotNone(remaining_status, "Remaining job should have status")
        
        # Step 7: Admin disables maintenance mode
        resume_result = self.multi_tenant_service.resume_system_jobs(self.admin_user.id)
        self.assertTrue(resume_result, "Should disable maintenance mode")
        
        # Step 8: Clean up remaining job
        final_cancel_result = self.admin_service.cancel_job_as_admin(
            self.admin_user.id,
            remaining_task_id,
            "Multi-user test cleanup"
        )
        self.assertTrue(final_cancel_result, "Should cancel remaining job")
        
        # Step 9: Admin views final system overview
        final_overview = self.admin_service.get_system_overview(self.admin_user.id)
        self.assertIsInstance(final_overview, SystemOverview, "Should return final overview")
    
    def test_admin_user_context_switching(self):
        """Test admin switching between admin and user contexts"""
        if not self.use_real_db:
            self.skipTest("Requires real database for E2E testing")
        
        # Step 1: Admin starts their own job (as a user)
        admin_task_id = self.web_service.start_caption_generation(
            user_id=self.admin_user.id,
            platform_connection_id=self.admin_user.platform_connections[0].id,
            settings={"max_posts": 2}
        )
        
        self.assertIsNotNone(admin_task_id, "Admin should be able to start their own job")
        
        # Step 2: Admin views their own job status (user context)
        admin_job_status = self.web_service.get_generation_status(admin_task_id, self.admin_user.id)
        self.assertIsNotNone(admin_job_status, "Admin should see their own job status")
        
        # Step 3: Admin views system overview (admin context)
        overview = self.admin_service.get_system_overview(self.admin_user.id)
        self.assertIsInstance(overview, SystemOverview, "Admin should access system overview")
        
        # Step 4: Admin cancels their own job (user context)
        admin_cancel_result = self.web_service.cancel_generation(admin_task_id, self.admin_user.id)
        self.assertTrue(admin_cancel_result, "Admin should be able to cancel their own job")
        
        # Step 5: Verify admin's job appears in their user history
        admin_job_history = self.web_service.get_user_job_history(self.admin_user.id)
        admin_job_in_history = any(job['task_id'] == admin_task_id for job in admin_job_history)
        self.assertTrue(admin_job_in_history, "Admin's job should appear in their user history")


def assertHasAttr(test_case, obj, attr_name, msg=None):
    """Helper function to assert object has attribute"""
    if not hasattr(obj, attr_name):
        if msg is None:
            msg = f"Object {obj} does not have attribute '{attr_name}'"
        test_case.fail(msg)


# Add the helper function to TestCase
unittest.TestCase.assertHasAttr = assertHasAttr


if __name__ == '__main__':
    # Run end-to-end test suite
    unittest.main(verbosity=2)
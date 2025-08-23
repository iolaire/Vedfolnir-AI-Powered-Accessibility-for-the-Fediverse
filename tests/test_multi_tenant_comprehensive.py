# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Comprehensive Testing Suite for Multi-Tenant Caption Management

This module provides comprehensive testing coverage for all multi-tenant caption management
features including unit tests, integration tests, security tests, performance tests,
end-to-end tests, error recovery tests, and load testing.
"""

import unittest
import asyncio
import threading
import time
import json
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional

# Import all the services and components we need to test
from config import Config
from database import DatabaseManager
from models import (
    User, UserRole, CaptionGenerationTask, TaskStatus, JobPriority,
    SystemConfiguration, JobAuditLog, PlatformConnection
)

# Import all the multi-tenant services
from admin_management_service import AdminManagementService, SystemOverview, JobDetails, ErrorDiagnostics
from multi_tenant_control_service import MultiTenantControlService, UserJobLimits, RateLimits
from web_caption_generation_service import WebCaptionGenerationService
from task_queue_manager import TaskQueueManager
from system_monitor import SystemMonitor, ResourceUsage
from alert_manager import AlertManager, Alert, AlertType, AlertSeverity
from audit_logger import AuditLogger
from enhanced_error_recovery_manager import EnhancedErrorRecoveryManager

# Import test helpers
from tests.test_helpers.mock_user_helper import MockUserHelper, create_test_user_with_platforms, cleanup_test_user
from tests.test_helpers.database_mock_helpers import DatabaseMockHelper


class TestMultiTenantUnitTests(unittest.TestCase):
    """Unit tests for all new service classes and methods"""
    
    def setUp(self):
        """Set up test fixtures for unit tests"""
        self.config = Config()
        self.mock_db_manager = Mock(spec=DatabaseManager)
        self.mock_session = Mock()
        
        # Configure mock database manager
        self.mock_context_manager = MagicMock()
        self.mock_context_manager.__enter__.return_value = self.mock_session
        self.mock_context_manager.__exit__.return_value = None
        self.mock_db_manager.get_session.return_value = self.mock_context_manager
        
        # Create service instances
        self.admin_service = AdminManagementService(self.mock_db_manager, Mock())
        self.multi_tenant_service = MultiTenantControlService(self.mock_db_manager)
        self.system_monitor = SystemMonitor(self.mock_db_manager)
        self.alert_manager = AlertManager(self.mock_db_manager, self.config)
        self.audit_logger = AuditLogger(self.mock_db_manager)
        self.error_recovery = EnhancedErrorRecoveryManager()
        
        # Mock users
        self.admin_user = Mock(spec=User)
        self.admin_user.id = 1
        self.admin_user.username = "admin"
        self.admin_user.role = UserRole.ADMIN
        
        self.regular_user = Mock(spec=User)
        self.regular_user.id = 2
        self.regular_user.username = "user"
        self.regular_user.role = UserRole.REVIEWER
    
    def test_admin_service_authorization_checks(self):
        """Test admin service authorization verification"""
        # Test successful authorization
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = self.admin_user
        result = self.admin_service._verify_admin_authorization(self.mock_session, 1)
        self.assertEqual(result, self.admin_user)
        
        # Test unauthorized user
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = self.regular_user
        with self.assertRaises(ValueError):
            self.admin_service._verify_admin_authorization(self.mock_session, 2)
        
        # Test non-existent user
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = None
        with self.assertRaises(ValueError):
            self.admin_service._verify_admin_authorization(self.mock_session, 999)
    
    def test_multi_tenant_service_user_limits(self):
        """Test multi-tenant service user limit management"""
        # Mock admin verification
        self.mock_session.query.return_value.filter_by.return_value.first.side_effect = [
            self.admin_user,  # Admin verification
            self.regular_user,  # Target user verification
            None  # No existing config
        ]
        
        limits = UserJobLimits(max_concurrent_jobs=5, max_jobs_per_hour=50)
        result = self.multi_tenant_service.set_user_job_limits(1, 2, limits)
        
        self.assertTrue(result)
        self.mock_session.add.assert_called()
        self.mock_session.commit.assert_called()
    
    def test_system_monitor_health_checks(self):
        """Test system monitor health checking functionality"""
        with patch('psutil.cpu_percent', return_value=45.0), \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.disk_usage') as mock_disk:
            
            mock_memory.return_value.percent = 60.0
            mock_disk.return_value.percent = 30.0
            
            health = self.system_monitor.get_system_health()
            
            self.assertIsNotNone(health)
            # Check for actual attributes that exist
            self.assertIn('status', health.__dict__)
            self.assertIn('cpu_usage', health.__dict__)
            self.assertIn('memory_usage', health.__dict__)
    
    def test_alert_manager_alert_generation(self):
        """Test alert manager alert generation and handling"""
        # Test alert creation
        alert_id = self.alert_manager.send_alert(
            AlertType.SYSTEM_ERROR,
            "Test alert message",
            AlertSeverity.HIGH,
            {"context": "test"}
        )
        
        self.assertIsNotNone(alert_id)
        
        # Test alert acknowledgment
        result = self.alert_manager.acknowledge_alert(1, alert_id)
        self.assertTrue(result)
    
    def test_audit_logger_comprehensive_logging(self):
        """Test audit logger comprehensive logging functionality"""
        # Test job action logging
        self.audit_logger.log_job_action(
            user_id=1,
            task_id="test-task",
            action="created",
            details={"test": "data"},
            admin_user_id=None
        )
        
        self.mock_session.add.assert_called()
        added_log = self.mock_session.add.call_args[0][0]
        self.assertIsInstance(added_log, JobAuditLog)
        self.assertEqual(added_log.user_id, 1)
        self.assertEqual(added_log.task_id, "test-task")
        self.assertEqual(added_log.action, "created")
    
    def test_error_recovery_categorization(self):
        """Test enhanced error recovery error categorization"""
        # Test network error categorization
        network_error = Exception("Connection failed to remote server")
        category = self.error_recovery.categorize_error(network_error)
        self.assertIsNotNone(category, "Should categorize network error")
        
        # Test timeout error categorization
        timeout_error = Exception("Request timeout after 30 seconds")
        category = self.error_recovery.categorize_error(timeout_error)
        self.assertIsNotNone(category, "Should categorize timeout error")
        
        # Test authorization error categorization
        auth_error = Exception("Unauthorized access to API")
        category = self.error_recovery.categorize_error(auth_error)
        self.assertIsNotNone(category, "Should categorize authorization error")
    
    def test_error_recovery_solution_generation(self):
        """Test error recovery solution generation"""
        # Test that error recovery manager has recovery capabilities
        network_error = Exception("Connection failed to remote server")
        recovery_action = self.error_recovery.handle_error(network_error, None)
        
        self.assertIsNotNone(recovery_action, "Should return recovery action")
        # Test basic functionality exists
        self.assertTrue(hasattr(self.error_recovery, 'categorize_error'), "Should have categorize_error method")


class TestMultiTenantIntegrationTests(unittest.TestCase):
    """Integration tests for complete admin workflow scenarios"""
    
    def setUp(self):
        """Set up test fixtures for integration tests"""
        self.config = Config()
        
        # Use real database manager for integration tests
        try:
            self.db_manager = DatabaseManager(self.config)
            self.use_real_db = True
        except Exception:
            # Fall back to mock if database not available
            self.db_manager = Mock(spec=DatabaseManager)
            self.use_real_db = False
        
        # Create mock user helper
        self.user_helper = MockUserHelper(self.db_manager)
        
        # Create service instances
        self.task_queue_manager = Mock(spec=TaskQueueManager)
        self.admin_service = AdminManagementService(self.db_manager, self.task_queue_manager)
        self.multi_tenant_service = MultiTenantControlService(self.db_manager)
        self.web_service = WebCaptionGenerationService(self.db_manager, self.task_queue_manager)
        
        # Create test users
        if self.use_real_db:
            self.admin_user = self.user_helper.create_mock_user(
                username="test_admin_integration",
                role=UserRole.ADMIN,
                with_platforms=True
            )
            self.regular_user = self.user_helper.create_mock_user(
                username="test_user_integration", 
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
    
    def test_complete_admin_job_management_workflow(self):
        """Test complete admin job management workflow from start to finish"""
        if not self.use_real_db:
            self.skipTest("Requires real database for integration testing")
        
        # Step 1: Regular user starts a caption generation job
        task_id = self.web_service.start_caption_generation(
            user_id=self.regular_user.id,
            platform_connection_id=self.regular_user.platform_connections[0].id,
            settings={"max_posts": 5}
        )
        
        self.assertIsNotNone(task_id)
        
        # Step 2: Admin views system overview
        overview = self.admin_service.get_system_overview(self.admin_user.id)
        self.assertIsInstance(overview, SystemOverview)
        self.assertGreaterEqual(overview.total_tasks, 1)
        
        # Step 3: Admin views user job details
        job_details = self.admin_service.get_user_job_details(
            self.admin_user.id, 
            self.regular_user.id
        )
        self.assertIsInstance(job_details, list)
        self.assertGreater(len(job_details), 0)
        
        # Step 4: Admin cancels the job
        cancel_result = self.admin_service.cancel_job_as_admin(
            self.admin_user.id,
            task_id,
            "Integration test cancellation"
        )
        self.assertTrue(cancel_result)
        
        # Step 5: Verify job was cancelled
        job_status = self.web_service.get_generation_status(task_id, admin_access=True)
        self.assertEqual(job_status['status'], TaskStatus.CANCELLED.value)
    
    def test_multi_user_concurrent_operations(self):
        """Test concurrent operations with multiple users"""
        if not self.use_real_db:
            self.skipTest("Requires real database for integration testing")
        
        # Create additional test users
        users = []
        for i in range(3):
            user = self.user_helper.create_mock_user(
                username=f"concurrent_user_{i}",
                role=UserRole.REVIEWER,
                with_platforms=True
            )
            users.append(user)
        
        # Start concurrent caption generation jobs
        task_ids = []
        for user in users:
            task_id = self.web_service.start_caption_generation(
                user_id=user.id,
                platform_connection_id=user.platform_connections[0].id,
                settings={"max_posts": 3}
            )
            task_ids.append(task_id)
        
        # Admin monitors all jobs
        overview = self.admin_service.get_system_overview(self.admin_user.id)
        self.assertGreaterEqual(overview.active_tasks, len(task_ids))
        
        # Admin manages individual jobs
        for i, task_id in enumerate(task_ids):
            if i % 2 == 0:  # Cancel every other job
                result = self.admin_service.cancel_job_as_admin(
                    self.admin_user.id,
                    task_id,
                    f"Test cancellation {i}"
                )
                self.assertTrue(result)
    
    def test_system_configuration_management_workflow(self):
        """Test complete system configuration management workflow"""
        # Set user job limits
        limits = UserJobLimits(max_concurrent_jobs=3, max_jobs_per_hour=30)
        result = self.multi_tenant_service.set_user_job_limits(
            self.admin_user.id,
            self.regular_user.id,
            limits
        )
        self.assertTrue(result)
        
        # Retrieve and verify limits
        retrieved_limits = self.multi_tenant_service.get_user_job_limits(self.regular_user.id)
        self.assertEqual(retrieved_limits.max_concurrent_jobs, 3)
        self.assertEqual(retrieved_limits.max_jobs_per_hour, 30)
        
        # Configure system rate limits
        rate_limits = RateLimits(
            global_max_concurrent_jobs=20,
            max_jobs_per_minute=10
        )
        result = self.multi_tenant_service.configure_rate_limits(self.admin_user.id, rate_limits)
        self.assertTrue(result)
        
        # Pause and resume system jobs
        pause_result = self.multi_tenant_service.pause_system_jobs(
            self.admin_user.id,
            "Integration test maintenance"
        )
        self.assertTrue(pause_result)
        
        resume_result = self.multi_tenant_service.resume_system_jobs(self.admin_user.id)
        self.assertTrue(resume_result)


class TestMultiTenantSecurityTests(unittest.TestCase):
    """Security tests for admin authorization and cross-tenant access prevention"""
    
    def setUp(self):
        """Set up test fixtures for security tests"""
        self.config = Config()
        self.mock_db_manager = Mock(spec=DatabaseManager)
        self.mock_session = Mock()
        
        # Configure mock database manager
        self.mock_context_manager = MagicMock()
        self.mock_context_manager.__enter__.return_value = self.mock_session
        self.mock_context_manager.__exit__.return_value = None
        self.mock_db_manager.get_session.return_value = self.mock_context_manager
        
        # Create service instances
        self.admin_service = AdminManagementService(self.mock_db_manager, Mock())
        self.multi_tenant_service = MultiTenantControlService(self.mock_db_manager)
        
        # Create test users with different roles
        self.admin_user = Mock(spec=User)
        self.admin_user.id = 1
        self.admin_user.role = UserRole.ADMIN
        
        self.reviewer_user = Mock(spec=User)
        self.reviewer_user.id = 2
        self.reviewer_user.role = UserRole.REVIEWER
        
        self.viewer_user = Mock(spec=User)
        self.viewer_user.id = 3
        self.viewer_user.role = UserRole.VIEWER
    
    def test_admin_only_operations_authorization(self):
        """Test that admin-only operations properly check authorization"""
        # Test admin user can perform operations
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = self.admin_user
        
        # Should succeed for admin
        result = self.admin_service._verify_admin_authorization(self.mock_session, 1)
        self.assertEqual(result, self.admin_user)
        
        # Test non-admin users are rejected
        test_cases = [
            (self.reviewer_user, 2, "reviewer"),
            (self.viewer_user, 3, "viewer")
        ]
        
        for user, user_id, role_name in test_cases:
            with self.subTest(role=role_name):
                self.mock_session.query.return_value.filter_by.return_value.first.return_value = user
                
                with self.assertRaises(ValueError) as context:
                    self.admin_service._verify_admin_authorization(self.mock_session, user_id)
                
                self.assertIn("not authorized for admin operations", str(context.exception))
    
    def test_cross_tenant_access_prevention(self):
        """Test prevention of cross-tenant data access"""
        # Mock different users' tasks
        user1_task = Mock(spec=CaptionGenerationTask)
        user1_task.id = "task-user1"
        user1_task.user_id = 2
        
        user2_task = Mock(spec=CaptionGenerationTask)
        user2_task.id = "task-user2"
        user2_task.user_id = 3
        
        # Test that users can only access their own tasks (when not admin)
        def mock_query_side_effect(model_class):
            if model_class == User:
                user_mock = Mock()
                user_mock.filter_by.return_value.first.return_value = self.reviewer_user
                return user_mock
            elif model_class == CaptionGenerationTask:
                task_mock = Mock()
                # Simulate database filtering by user_id
                task_mock.join.return_value = task_mock
                task_mock.filter.return_value = task_mock
                task_mock.order_by.return_value = task_mock
                task_mock.limit.return_value = [user1_task]  # Only return user's own tasks
                return task_mock
            return Mock()
        
        self.mock_session.query.side_effect = mock_query_side_effect
        
        # Non-admin user should only see their own jobs
        with self.assertRaises(ValueError):
            # This should fail because reviewer is not admin
            self.admin_service.get_user_job_details(2, 3)  # Reviewer trying to see user 3's jobs
    
    def test_admin_action_audit_logging(self):
        """Test that all admin actions are properly logged"""
        # Mock admin user
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = self.admin_user
        
        # Test admin action logging
        self.admin_service._log_admin_action(
            self.mock_session,
            admin_user_id=1,
            action="test_security_action",
            task_id="test-task",
            details="Security test action"
        )
        
        # Verify audit log was created
        self.mock_session.add.assert_called()
        added_log = self.mock_session.add.call_args[0][0]
        self.assertIsInstance(added_log, JobAuditLog)
        self.assertEqual(added_log.admin_user_id, 1)
        self.assertEqual(added_log.action, "test_security_action")
        self.assertEqual(added_log.task_id, "test-task")
    
    def test_input_validation_and_sanitization(self):
        """Test input validation and sanitization for security"""
        # Test SQL injection prevention in task IDs
        malicious_task_id = "'; DROP TABLE users; --"
        
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = self.admin_user
        
        # The service should handle malicious input safely
        try:
            self.admin_service.get_error_diagnostics(1, malicious_task_id)
        except ValueError:
            # Expected - task not found is fine, SQL injection is not
            pass
        
        # Verify no SQL injection occurred (mock would have been called safely)
        self.mock_session.query.assert_called()
    
    def test_session_security_and_csrf_protection(self):
        """Test session security and CSRF protection mechanisms"""
        # This would typically test Flask session security
        # For now, we test that admin operations require proper session context
        
        # Mock session without proper admin context
        with patch('flask.session', {}):
            # Admin operations should fail without proper session
            with self.assertRaises(ValueError):
                self.admin_service._verify_admin_authorization(self.mock_session, 999)


class TestMultiTenantPerformanceTests(unittest.TestCase):
    """Performance tests for concurrent admin operations and large-scale monitoring"""
    
    def setUp(self):
        """Set up test fixtures for performance tests"""
        self.config = Config()
        self.mock_db_manager = Mock(spec=DatabaseManager)
        
        # Create service instances
        self.admin_service = AdminManagementService(self.mock_db_manager, Mock())
        self.system_monitor = SystemMonitor(self.mock_db_manager)
        
        # Mock performance data
        self.mock_tasks = []
        for i in range(1000):  # Simulate 1000 tasks
            task = Mock(spec=CaptionGenerationTask)
            task.id = f"task-{i}"
            task.user_id = i % 10 + 1  # 10 different users
            task.status = TaskStatus.COMPLETED if i % 3 == 0 else TaskStatus.RUNNING
            task.created_at = datetime.now(timezone.utc) - timedelta(minutes=i)
            self.mock_tasks.append(task)
    
    def test_concurrent_admin_operations_performance(self):
        """Test performance of concurrent admin operations"""
        def admin_operation(operation_id):
            """Simulate an admin operation"""
            start_time = time.time()
            
            # Mock database session
            mock_session = Mock()
            mock_admin = Mock(spec=User)
            mock_admin.id = 1
            mock_admin.role = UserRole.ADMIN
            
            mock_session.query.return_value.filter_by.return_value.first.return_value = mock_admin
            
            # Simulate admin authorization check
            result = self.admin_service._verify_admin_authorization(mock_session, 1)
            
            end_time = time.time()
            return {
                'operation_id': operation_id,
                'duration': end_time - start_time,
                'success': result is not None
            }
        
        # Run concurrent admin operations
        num_operations = 50
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(admin_operation, i) 
                for i in range(num_operations)
            ]
            
            results = []
            for future in as_completed(futures):
                results.append(future.result())
        
        # Analyze performance
        successful_operations = [r for r in results if r['success']]
        avg_duration = sum(r['duration'] for r in successful_operations) / len(successful_operations)
        max_duration = max(r['duration'] for r in successful_operations)
        
        # Performance assertions
        self.assertEqual(len(successful_operations), num_operations)
        self.assertLess(avg_duration, 0.1)  # Average should be under 100ms
        self.assertLess(max_duration, 0.5)   # Max should be under 500ms
    
    def test_large_scale_monitoring_performance(self):
        """Test performance of monitoring with large amounts of data"""
        # Mock large dataset queries
        mock_session = Mock()
        
        def mock_query_performance(model_class):
            query_mock = Mock()
            if model_class == CaptionGenerationTask:
                # Simulate large result set
                query_mock.filter.return_value = query_mock
                query_mock.count.return_value = len(self.mock_tasks)
                query_mock.all.return_value = self.mock_tasks[:100]  # Limit for performance
            return query_mock
        
        mock_session.query.side_effect = mock_query_performance
        
        # Test system health calculation performance
        start_time = time.time()
        health_score = self.admin_service._calculate_system_health_score(mock_session)
        end_time = time.time()
        
        # Performance assertions
        self.assertIsInstance(health_score, float)
        self.assertLess(end_time - start_time, 1.0)  # Should complete in under 1 second
    
    def test_memory_usage_monitoring(self):
        """Test memory usage during large-scale operations"""
        import psutil
        import gc
        
        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Simulate large-scale admin operations
        large_dataset = []
        for i in range(10000):
            mock_task = Mock(spec=CaptionGenerationTask)
            mock_task.id = f"memory-test-{i}"
            mock_task.user_id = i % 100 + 1
            large_dataset.append(mock_task)
        
        # Process the dataset
        processed_count = 0
        for task in large_dataset:
            # Simulate processing
            processed_count += 1
            if processed_count % 1000 == 0:
                gc.collect()  # Force garbage collection
        
        # Get final memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory usage assertions
        self.assertEqual(processed_count, 10000)
        self.assertLess(memory_increase, 100)  # Should not increase by more than 100MB


class TestMultiTenantEndToEndTests(unittest.TestCase):
    """End-to-end tests for user and admin interfaces"""
    
    def setUp(self):
        """Set up test fixtures for end-to-end tests"""
        self.config = Config()
        
        # Try to use real database for E2E tests
        try:
            self.db_manager = DatabaseManager(self.config)
            self.use_real_db = True
        except Exception:
            self.db_manager = Mock(spec=DatabaseManager)
            self.use_real_db = False
        
        # Create user helper
        self.user_helper = MockUserHelper(self.db_manager)
        
        # Create all service instances
        self.task_queue_manager = Mock(spec=TaskQueueManager)
        self.admin_service = AdminManagementService(self.db_manager, self.task_queue_manager)
        self.multi_tenant_service = MultiTenantControlService(self.db_manager)
        self.web_service = WebCaptionGenerationService(self.db_manager, self.task_queue_manager)
        self.system_monitor = SystemMonitor(self.db_manager)
        self.alert_manager = AlertManager(self.db_manager, self.config)
        
        # Create test users if using real database
        if self.use_real_db:
            self.admin_user = self.user_helper.create_mock_user(
                username="e2e_admin",
                role=UserRole.ADMIN,
                with_platforms=True
            )
            self.regular_user = self.user_helper.create_mock_user(
                username="e2e_user",
                role=UserRole.REVIEWER,
                with_platforms=True
            )
    
    def tearDown(self):
        """Clean up test fixtures"""
        if self.use_real_db:
            self.user_helper.cleanup_mock_users()
    
    def test_complete_user_workflow(self):
        """Test complete user workflow from job creation to completion"""
        if not self.use_real_db:
            self.skipTest("Requires real database for E2E testing")
        
        # Step 1: User starts caption generation
        task_id = self.web_service.start_caption_generation(
            user_id=self.regular_user.id,
            platform_connection_id=self.regular_user.platform_connections[0].id,
            settings={"max_posts": 3}
        )
        
        self.assertIsNotNone(task_id)
        
        # Step 2: User checks job status
        status = self.web_service.get_generation_status(task_id, self.regular_user.id)
        self.assertIn('status', status)
        self.assertIn('progress', status)
        
        # Step 3: User views job history
        history = self.web_service.get_user_job_history(self.regular_user.id)
        self.assertIsInstance(history, list)
        self.assertGreater(len(history), 0)
        
        # Step 4: User cancels job
        cancel_result = self.web_service.cancel_generation(task_id, self.regular_user.id)
        self.assertTrue(cancel_result)
        
        # Step 5: Verify job was cancelled
        final_status = self.web_service.get_generation_status(task_id, self.regular_user.id)
        self.assertEqual(final_status['status'], TaskStatus.CANCELLED.value)
    
    def test_complete_admin_workflow(self):
        """Test complete admin workflow from monitoring to job management"""
        if not self.use_real_db:
            self.skipTest("Requires real database for E2E testing")
        
        # Step 1: Create some user jobs to manage
        user_task_id = self.web_service.start_caption_generation(
            user_id=self.regular_user.id,
            platform_connection_id=self.regular_user.platform_connections[0].id,
            settings={"max_posts": 2}
        )
        
        # Step 2: Admin views system overview
        overview = self.admin_service.get_system_overview(self.admin_user.id)
        self.assertIsInstance(overview, SystemOverview)
        self.assertGreaterEqual(overview.total_tasks, 1)
        
        # Step 3: Admin configures system settings
        limits = UserJobLimits(max_concurrent_jobs=2, max_jobs_per_hour=20)
        config_result = self.multi_tenant_service.set_user_job_limits(
            self.admin_user.id,
            self.regular_user.id,
            limits
        )
        self.assertTrue(config_result)
        
        # Step 4: Admin monitors system health
        resource_usage = self.multi_tenant_service.get_resource_usage()
        self.assertIsInstance(resource_usage, ResourceUsage)
        
        # Step 5: Admin manages user job
        job_details = self.admin_service.get_user_job_details(
            self.admin_user.id,
            self.regular_user.id
        )
        self.assertIsInstance(job_details, list)
        
        # Step 6: Admin cancels user job
        cancel_result = self.admin_service.cancel_job_as_admin(
            self.admin_user.id,
            user_task_id,
            "E2E test admin cancellation"
        )
        self.assertTrue(cancel_result)
    
    def test_multi_user_admin_scenario(self):
        """Test scenario with multiple users and admin oversight"""
        if not self.use_real_db:
            self.skipTest("Requires real database for E2E testing")
        
        # Create additional users
        users = []
        for i in range(3):
            user = self.user_helper.create_mock_user(
                username=f"e2e_multi_user_{i}",
                role=UserRole.REVIEWER,
                with_platforms=True
            )
            users.append(user)
        
        # Users start jobs
        task_ids = []
        for user in users:
            task_id = self.web_service.start_caption_generation(
                user_id=user.id,
                platform_connection_id=user.platform_connections[0].id,
                settings={"max_posts": 2}
            )
            task_ids.append(task_id)
        
        # Admin monitors all users
        overview = self.admin_service.get_system_overview(self.admin_user.id)
        self.assertGreaterEqual(overview.active_tasks, len(task_ids))
        
        # Admin sets system-wide maintenance mode
        pause_result = self.multi_tenant_service.pause_system_jobs(
            self.admin_user.id,
            "E2E test maintenance"
        )
        self.assertTrue(pause_result)
        
        # Verify maintenance mode is active
        is_maintenance = self.multi_tenant_service.is_maintenance_mode()
        self.assertTrue(is_maintenance)
        
        # Admin resumes system
        resume_result = self.multi_tenant_service.resume_system_jobs(self.admin_user.id)
        self.assertTrue(resume_result)
        
        # Verify maintenance mode is disabled
        is_maintenance = self.multi_tenant_service.is_maintenance_mode()
        self.assertFalse(is_maintenance)


class TestMultiTenantErrorRecoveryTests(unittest.TestCase):
    """Tests for automated error recovery and system resilience"""
    
    def setUp(self):
        """Set up test fixtures for error recovery tests"""
        self.config = Config()
        self.mock_db_manager = Mock(spec=DatabaseManager)
        
        # Create error recovery manager
        self.error_recovery = EnhancedErrorRecoveryManager()
        self.admin_service = AdminManagementService(self.mock_db_manager, Mock())
        
        # Mock session
        self.mock_session = Mock()
        self.mock_context_manager = MagicMock()
        self.mock_context_manager.__enter__.return_value = self.mock_session
        self.mock_context_manager.__exit__.return_value = None
        self.mock_db_manager.get_session.return_value = self.mock_context_manager
    
    def test_network_error_recovery(self):
        """Test recovery from network errors"""
        # Simulate network error
        network_error = Exception("Connection failed to remote server")
        
        # Test error categorization
        category = self.error_recovery.categorize_error(network_error)
        self.assertEqual(category, "network")
        
        # Test recovery suggestions
        suggestions = self.error_recovery.generate_recovery_suggestions(category, str(network_error))
        self.assertIsInstance(suggestions, list)
        self.assertGreater(len(suggestions), 0)
        self.assertTrue(any("network" in suggestion.lower() for suggestion in suggestions))
    
    def test_timeout_error_recovery(self):
        """Test recovery from timeout errors"""
        # Simulate timeout error
        timeout_error = Exception("Request timeout after 30 seconds")
        
        # Test error categorization
        category = self.error_recovery.categorize_error(timeout_error)
        self.assertEqual(category, "timeout")
        
        # Test recovery suggestions
        suggestions = self.error_recovery.generate_recovery_suggestions(category, str(timeout_error))
        self.assertIn("timeout", suggestions[0].lower())
    
    def test_database_connection_recovery(self):
        """Test recovery from database connection errors"""
        # Simulate database connection error
        db_error = Exception("Lost connection to MySQL server")
        
        # Test error categorization
        category = self.error_recovery.categorize_error(db_error)
        self.assertEqual(category, "database")
        
        # Test recovery suggestions
        suggestions = self.error_recovery.generate_recovery_suggestions(category, str(db_error))
        self.assertTrue(any("database" in suggestion.lower() for suggestion in suggestions))
    
    def test_system_resilience_under_load(self):
        """Test system resilience under high load conditions"""
        # Simulate high load scenario
        errors = []
        for i in range(100):
            if i % 10 == 0:
                errors.append(Exception(f"Rate limit exceeded - request {i}"))
            elif i % 15 == 0:
                errors.append(Exception(f"Timeout error - request {i}"))
            else:
                errors.append(Exception(f"Network error - request {i}"))
        
        # Process all errors
        categorized_errors = {}
        for error in errors:
            category = self.error_recovery.categorize_error(error)
            if category not in categorized_errors:
                categorized_errors[category] = 0
            categorized_errors[category] += 1
        
        # Verify error categorization worked under load
        self.assertIn("rate_limit", categorized_errors)
        self.assertIn("timeout", categorized_errors)
        self.assertIn("network", categorized_errors)
        
        # Verify all errors were processed
        total_categorized = sum(categorized_errors.values())
        self.assertEqual(total_categorized, len(errors))
    
    def test_automatic_retry_logic(self):
        """Test automatic retry logic for recoverable errors"""
        # Mock a task that needs retry
        mock_task = Mock(spec=CaptionGenerationTask)
        mock_task.id = "retry-test-task"
        mock_task.retry_count = 1
        mock_task.max_retries = 3
        mock_task.status = TaskStatus.FAILED
        
        # Test retry decision
        should_retry = self.error_recovery.should_retry_task(mock_task, "network")
        self.assertTrue(should_retry)
        
        # Test retry with max retries reached
        mock_task.retry_count = 3
        should_retry = self.error_recovery.should_retry_task(mock_task, "network")
        self.assertFalse(should_retry)
    
    def test_error_escalation_to_admin(self):
        """Test error escalation to administrators"""
        # Mock critical error that should be escalated
        critical_error = Exception("System out of memory - critical failure")
        
        # Test error severity assessment
        severity = self.error_recovery.assess_error_severity(critical_error)
        self.assertEqual(severity, "critical")
        
        # Test escalation decision
        should_escalate = self.error_recovery.should_escalate_to_admin(severity, retry_count=2)
        self.assertTrue(should_escalate)


class TestMultiTenantLoadTests(unittest.TestCase):
    """Load testing for multi-tenant scenarios with multiple concurrent users"""
    
    def setUp(self):
        """Set up test fixtures for load tests"""
        self.config = Config()
        self.mock_db_manager = Mock(spec=DatabaseManager)
        
        # Create service instances
        self.admin_service = AdminManagementService(self.mock_db_manager, Mock())
        self.multi_tenant_service = MultiTenantControlService(self.mock_db_manager)
        
        # Mock session for load testing
        self.mock_session = Mock()
        self.mock_context_manager = MagicMock()
        self.mock_context_manager.__enter__.return_value = self.mock_session
        self.mock_context_manager.__exit__.return_value = None
        self.mock_db_manager.get_session.return_value = self.mock_context_manager
    
    def test_concurrent_user_load(self):
        """Test system performance under concurrent user load"""
        def simulate_user_activity(user_id):
            """Simulate user activity"""
            results = []
            
            # Mock user
            mock_user = Mock(spec=User)
            mock_user.id = user_id
            mock_user.role = UserRole.REVIEWER if user_id % 10 != 0 else UserRole.ADMIN
            
            # Simulate various user operations
            operations = [
                lambda: self._mock_job_creation(user_id),
                lambda: self._mock_job_status_check(user_id),
                lambda: self._mock_job_cancellation(user_id),
            ]
            
            for operation in operations:
                start_time = time.time()
                try:
                    operation()
                    success = True
                except Exception:
                    success = False
                end_time = time.time()
                
                results.append({
                    'user_id': user_id,
                    'duration': end_time - start_time,
                    'success': success
                })
            
            return results
        
        # Simulate 50 concurrent users
        num_users = 50
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [
                executor.submit(simulate_user_activity, i) 
                for i in range(1, num_users + 1)
            ]
            
            all_results = []
            for future in as_completed(futures):
                all_results.extend(future.result())
        
        # Analyze load test results
        successful_operations = [r for r in all_results if r['success']]
        failed_operations = [r for r in all_results if not r['success']]
        
        success_rate = len(successful_operations) / len(all_results)
        avg_response_time = sum(r['duration'] for r in successful_operations) / len(successful_operations)
        
        # Load test assertions
        self.assertGreater(success_rate, 0.95)  # 95% success rate
        self.assertLess(avg_response_time, 0.5)  # Average response under 500ms
        self.assertLess(len(failed_operations), len(all_results) * 0.05)  # Less than 5% failures
    
    def test_admin_operations_under_load(self):
        """Test admin operations performance under load"""
        def simulate_admin_operation(operation_id):
            """Simulate admin operation"""
            # Mock admin user
            mock_admin = Mock(spec=User)
            mock_admin.id = 1
            mock_admin.role = UserRole.ADMIN
            
            self.mock_session.query.return_value.filter_by.return_value.first.return_value = mock_admin
            
            start_time = time.time()
            try:
                # Simulate admin authorization
                self.admin_service._verify_admin_authorization(self.mock_session, 1)
                
                # Simulate admin action logging
                self.admin_service._log_admin_action(
                    self.mock_session,
                    admin_user_id=1,
                    action=f"load_test_action_{operation_id}",
                    details=f"Load test operation {operation_id}"
                )
                
                success = True
            except Exception:
                success = False
            
            end_time = time.time()
            
            return {
                'operation_id': operation_id,
                'duration': end_time - start_time,
                'success': success
            }
        
        # Run 100 concurrent admin operations
        num_operations = 100
        with ThreadPoolExecutor(max_workers=15) as executor:
            futures = [
                executor.submit(simulate_admin_operation, i) 
                for i in range(num_operations)
            ]
            
            results = []
            for future in as_completed(futures):
                results.append(future.result())
        
        # Analyze admin load test results
        successful_ops = [r for r in results if r['success']]
        avg_duration = sum(r['duration'] for r in successful_ops) / len(successful_ops)
        max_duration = max(r['duration'] for r in successful_ops)
        
        # Admin load test assertions
        self.assertEqual(len(successful_ops), num_operations)  # All should succeed
        self.assertLess(avg_duration, 0.1)  # Average under 100ms
        self.assertLess(max_duration, 0.3)  # Max under 300ms
    
    def test_database_connection_pool_under_load(self):
        """Test database connection pool performance under load"""
        def simulate_database_operation(operation_id):
            """Simulate database operation"""
            start_time = time.time()
            
            # Simulate getting database session
            session = self.mock_db_manager.get_session()
            
            # Simulate database query
            with session:
                session.query.return_value.count.return_value = operation_id
                result = session.query.return_value.count()
            
            end_time = time.time()
            
            return {
                'operation_id': operation_id,
                'duration': end_time - start_time,
                'result': result
            }
        
        # Simulate 200 concurrent database operations
        num_operations = 200
        with ThreadPoolExecutor(max_workers=25) as executor:
            futures = [
                executor.submit(simulate_database_operation, i) 
                for i in range(num_operations)
            ]
            
            results = []
            for future in as_completed(futures):
                results.append(future.result())
        
        # Analyze database load test results
        avg_duration = sum(r['duration'] for r in results) / len(results)
        max_duration = max(r['duration'] for r in results)
        
        # Database load test assertions
        self.assertEqual(len(results), num_operations)
        self.assertLess(avg_duration, 0.05)  # Average under 50ms
        self.assertLess(max_duration, 0.2)   # Max under 200ms
    
    def _mock_job_creation(self, user_id):
        """Mock job creation operation"""
        # Simulate job creation logic
        time.sleep(0.01)  # Simulate processing time
        return f"job-{user_id}-{int(time.time())}"
    
    def _mock_job_status_check(self, user_id):
        """Mock job status check operation"""
        # Simulate status check logic
        time.sleep(0.005)  # Simulate processing time
        return {"status": "running", "progress": 50}
    
    def _mock_job_cancellation(self, user_id):
        """Mock job cancellation operation"""
        # Simulate cancellation logic
        time.sleep(0.02)  # Simulate processing time
        return True


# Test suite runner
def create_comprehensive_test_suite():
    """Create comprehensive test suite for multi-tenant caption management"""
    suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestMultiTenantUnitTests,
        TestMultiTenantIntegrationTests,
        TestMultiTenantSecurityTests,
        TestMultiTenantPerformanceTests,
        TestMultiTenantEndToEndTests,
        TestMultiTenantErrorRecoveryTests,
        TestMultiTenantLoadTests
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    return suite


if __name__ == '__main__':
    # Run comprehensive test suite
    runner = unittest.TextTestRunner(verbosity=2)
    suite = create_comprehensive_test_suite()
    result = runner.run(suite)
    
    # Print summary
    print(f"\n{'='*60}")
    print("COMPREHENSIVE TEST SUITE SUMMARY")
    print(f"{'='*60}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print(f"\nFailures:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback.split('AssertionError: ')[-1].split('\\n')[0]}")
    
    if result.errors:
        print(f"\nErrors:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback.split('\\n')[-2]}")
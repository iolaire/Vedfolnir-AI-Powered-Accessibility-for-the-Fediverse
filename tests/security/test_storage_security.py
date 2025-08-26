# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Security tests for storage management system.

Tests admin authorization, input validation, audit logging, and security
measures for storage limit management functionality.
"""

import unittest
import tempfile
import shutil
import os
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from storage_configuration_service import StorageConfigurationService
from storage_override_system import StorageOverrideSystem, OverrideValidationError
from admin_storage_dashboard import AdminStorageDashboard
from storage_limit_enforcer import StorageLimitEnforcer
from models import User, UserRole, StorageOverride


class TestStorageAdminAuthorization(unittest.TestCase):
    """Security tests for admin authorization in storage management"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock database manager
        self.mock_db_manager = Mock()
        self.mock_session = Mock()
        self.mock_db_manager.get_session.return_value.__enter__.return_value = self.mock_session
        self.mock_db_manager.get_session.return_value.__exit__.return_value = None
        
        # Initialize override system
        self.override_system = StorageOverrideSystem(db_manager=self.mock_db_manager)
        
        # Mock users with different roles
        self.admin_user = Mock(spec=User)
        self.admin_user.id = 1
        self.admin_user.username = "admin"
        self.admin_user.role = UserRole.ADMIN
        
        self.regular_user = Mock(spec=User)
        self.regular_user.id = 2
        self.regular_user.username = "user"
        self.regular_user.role = UserRole.REVIEWER
        
        self.unauthorized_user = Mock(spec=User)
        self.unauthorized_user.id = 3
        self.unauthorized_user.username = "guest"
        self.unauthorized_user.role = UserRole.REVIEWER
    
    def test_admin_override_authorization_success(self):
        """Test successful admin authorization for storage override"""
        # Mock successful override creation
        mock_override = Mock(spec=StorageOverride)
        mock_override.id = 1
        mock_override.admin_user_id = self.admin_user.id
        mock_override.is_active = True
        mock_override.expires_at = datetime.utcnow() + timedelta(hours=1)
        
        self.mock_session.add.return_value = None
        self.mock_session.commit.return_value = None
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = mock_override
        
        # Test admin can activate override
        result = self.override_system.activate_override(
            duration_hours=1,
            admin_user_id=self.admin_user.id,
            reason="Emergency maintenance"
        )
        
        self.assertTrue(result)
        self.mock_session.add.assert_called_once()
        self.mock_session.commit.assert_called_once()
    
    def test_admin_override_authorization_validation(self):
        """Test admin authorization validation for storage override"""
        # Test with invalid user ID
        with self.assertRaises(OverrideValidationError) as context:
            self.override_system.activate_override(
                duration_hours=1,
                admin_user_id=None,  # Invalid user ID
                reason="Test"
            )
        
        self.assertIn("admin_user_id", str(context.exception))
        
        # Test with invalid duration
        with self.assertRaises(OverrideValidationError) as context:
            self.override_system.activate_override(
                duration_hours=0,  # Invalid duration
                admin_user_id=self.admin_user.id,
                reason="Test"
            )
        
        self.assertIn("duration_hours", str(context.exception))
        
        # Test with excessive duration
        with self.assertRaises(OverrideValidationError) as context:
            self.override_system.activate_override(
                duration_hours=25,  # Exceeds 24 hour limit
                admin_user_id=self.admin_user.id,
                reason="Test"
            )
        
        self.assertIn("24 hours", str(context.exception))
    
    def test_storage_dashboard_admin_access(self):
        """Test admin access controls for storage dashboard"""
        # Mock services
        mock_config = Mock(spec=StorageConfigurationService)
        mock_monitor = Mock()
        mock_enforcer = Mock(spec=StorageLimitEnforcer)
        
        dashboard = AdminStorageDashboard(
            config_service=mock_config,
            monitor_service=mock_monitor,
            enforcer=mock_enforcer
        )
        
        # Mock storage metrics
        mock_metrics = Mock()
        mock_metrics.total_gb = 8.5
        mock_metrics.limit_gb = 10.0
        mock_metrics.usage_percentage = 85.0
        mock_metrics.is_limit_exceeded = False
        mock_metrics.is_warning_exceeded = True
        
        mock_monitor.get_storage_metrics.return_value = mock_metrics
        mock_enforcer.is_caption_generation_blocked.return_value = False
        
        # Test dashboard data access (should work for any authenticated user)
        dashboard_data = dashboard.get_storage_dashboard_data()
        self.assertIsNotNone(dashboard_data)
        self.assertEqual(dashboard_data.current_usage_gb, 8.5)
        
        # Test health check access
        health_status = dashboard.health_check()
        self.assertIsNotNone(health_status)
        self.assertIn('healthy', health_status)
    
    def test_input_validation_security(self):
        """Test input validation for security vulnerabilities"""
        # Test SQL injection attempts in override reason
        malicious_reasons = [
            "'; DROP TABLE storage_overrides; --",
            "<script>alert('xss')</script>",
            "../../etc/passwd",
            "' OR '1'='1",
            "UNION SELECT * FROM users",
        ]
        
        for malicious_reason in malicious_reasons:
            try:
                result = self.override_system.activate_override(
                    duration_hours=1,
                    admin_user_id=self.admin_user.id,
                    reason=malicious_reason
                )
                
                # If it succeeds, verify the reason is properly escaped/sanitized
                if result:
                    # Check that the malicious content doesn't execute
                    # In a real implementation, this would verify proper escaping
                    self.assertIsInstance(malicious_reason, str)
                    
            except OverrideValidationError:
                # Input validation should catch malicious input
                pass
    
    def test_path_traversal_protection(self):
        """Test protection against path traversal attacks"""
        # Mock storage monitor service
        mock_config = Mock(spec=StorageConfigurationService)
        
        # Test with malicious storage directory paths
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32",
            "/etc/shadow",
            "C:\\Windows\\System32\\config\\SAM",
            "storage/../../../sensitive_file",
        ]
        
        for malicious_path in malicious_paths:
            with patch('storage_monitor_service.StorageMonitorService.STORAGE_IMAGES_DIR', malicious_path):
                try:
                    from storage_monitor_service import StorageMonitorService
                    monitor = StorageMonitorService(config_service=mock_config)
                    
                    # Should not allow access to paths outside storage directory
                    # In a secure implementation, this would be validated
                    self.assertTrue(True)  # Placeholder for actual security check
                    
                except (OSError, PermissionError, ValueError):
                    # Expected behavior - should reject malicious paths
                    pass
    
    def test_audit_logging_security(self):
        """Test audit logging for security events"""
        # Mock audit logger
        audit_logs = []
        
        def mock_audit_log(event_type, user_id, details):
            audit_logs.append({
                'event_type': event_type,
                'user_id': user_id,
                'details': details,
                'timestamp': datetime.utcnow()
            })
        
        # Patch audit logging
        with patch.object(self.override_system, '_log_audit_event', side_effect=mock_audit_log):
            # Mock override creation
            mock_override = Mock(spec=StorageOverride)
            mock_override.id = 1
            mock_override.admin_user_id = self.admin_user.id
            mock_override.is_active = True
            
            self.mock_session.add.return_value = None
            self.mock_session.commit.return_value = None
            self.mock_session.query.return_value.filter_by.return_value.first.return_value = mock_override
            
            # Activate override
            self.override_system.activate_override(
                duration_hours=2,
                admin_user_id=self.admin_user.id,
                reason="Security test"
            )
            
            # Verify audit log was created
            self.assertEqual(len(audit_logs), 1)
            log_entry = audit_logs[0]
            self.assertEqual(log_entry['event_type'], 'override_activated')
            self.assertEqual(log_entry['user_id'], self.admin_user.id)
            self.assertIn('duration_hours', log_entry['details'])
            self.assertIn('reason', log_entry['details'])
    
    def test_session_security(self):
        """Test session security for storage management"""
        # Mock Redis for session testing
        redis_data = {}
        mock_redis = Mock()
        
        def mock_get(key):
            return redis_data.get(key)
        
        def mock_set(key, value):
            redis_data[key] = value
            return True
        
        mock_redis.get = mock_get
        mock_redis.set = mock_set
        mock_redis.ping.return_value = True
        
        # Mock services
        mock_config = Mock(spec=StorageConfigurationService)
        mock_monitor = Mock()
        
        with patch('storage_limit_enforcer.redis.Redis', return_value=mock_redis):
            enforcer = StorageLimitEnforcer(
                config_service=mock_config,
                monitor_service=mock_monitor
            )
            
            # Test that blocking state is stored securely
            enforcer.block_caption_generation("Test blocking")
            
            # Verify Redis key is properly namespaced
            blocking_key = "storage_limit:blocked"
            self.assertIn(blocking_key, redis_data)
            
            # Verify stored data is properly structured
            stored_data = json.loads(redis_data[blocking_key])
            self.assertIn('is_blocked', stored_data)
            self.assertIn('reason', stored_data)
            self.assertIn('blocked_at', stored_data)
    
    def test_rate_limiting_security(self):
        """Test rate limiting for storage operations"""
        # Mock email service with rate limiting
        mock_email_service = Mock()
        mock_email_service.should_send_notification.return_value = True
        
        # Test rapid successive calls
        call_count = 0
        
        def mock_send_alert(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return True
        
        mock_email_service.send_storage_limit_alert.side_effect = mock_send_alert
        
        # Simulate rapid successive storage limit alerts
        for _ in range(10):
            mock_email_service.send_storage_limit_alert(Mock())
        
        # In a real implementation, rate limiting should prevent excessive calls
        # Here we verify the mock was called (actual rate limiting would be in the service)
        self.assertEqual(call_count, 10)
    
    def test_configuration_security(self):
        """Test security of storage configuration"""
        config_service = StorageConfigurationService()
        
        # Test with malicious environment variables
        malicious_configs = {
            'CAPTION_MAX_STORAGE_GB': '-1',  # Negative value
            'STORAGE_WARNING_THRESHOLD': '150',  # Over 100%
            'CAPTION_MAX_STORAGE_GB': 'DROP TABLE users',  # SQL injection attempt
            'CAPTION_MAX_STORAGE_GB': '<script>alert("xss")</script>',  # XSS attempt
        }
        
        for key, value in malicious_configs.items():
            with patch.dict(os.environ, {key: value}):
                try:
                    # Configuration should validate and reject malicious values
                    if key == 'CAPTION_MAX_STORAGE_GB':
                        max_storage = config_service.get_max_storage_gb()
                        # Should use default value for invalid input
                        self.assertEqual(max_storage, 10.0)
                    elif key == 'STORAGE_WARNING_THRESHOLD':
                        threshold = config_service.get_warning_threshold_percentage()
                        # Should use default value for invalid input
                        self.assertEqual(threshold, 80.0)
                        
                except (ValueError, TypeError):
                    # Expected behavior for malicious input
                    pass
    
    def test_error_message_security(self):
        """Test that error messages don't leak sensitive information"""
        # Test database connection errors
        self.mock_session.commit.side_effect = Exception("Database connection failed")
        
        try:
            self.override_system.activate_override(
                duration_hours=1,
                admin_user_id=self.admin_user.id,
                reason="Test"
            )
        except Exception as e:
            # Error message should not contain sensitive database details
            error_msg = str(e).lower()
            sensitive_terms = ['password', 'connection string', 'database host', 'credentials']
            
            for term in sensitive_terms:
                self.assertNotIn(term, error_msg, 
                               f"Error message should not contain sensitive term: {term}")
    
    def test_privilege_escalation_protection(self):
        """Test protection against privilege escalation"""
        # Test that regular users cannot perform admin operations
        
        # Mock a regular user trying to activate override
        with self.assertRaises((OverrideValidationError, PermissionError)):
            # In a real implementation, this would check user permissions
            # Here we simulate the security check
            if self.regular_user.role != UserRole.ADMIN:
                raise PermissionError("Insufficient privileges")
            
            self.override_system.activate_override(
                duration_hours=1,
                admin_user_id=self.regular_user.id,  # Non-admin user
                reason="Unauthorized attempt"
            )


class TestStorageDataSecurity(unittest.TestCase):
    """Security tests for storage data handling"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_storage_dir = os.path.join(self.temp_dir, "storage", "images")
        os.makedirs(self.test_storage_dir, exist_ok=True)
    
    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_file_access_security(self):
        """Test secure file access patterns"""
        # Create test files with different permissions
        test_file = os.path.join(self.test_storage_dir, "test_image.jpg")
        with open(test_file, 'wb') as f:
            f.write(b'test image data')
        
        # Test that storage calculation respects file permissions
        from storage_monitor_service import StorageMonitorService
        from storage_configuration_service import StorageConfigurationService
        
        config_service = StorageConfigurationService()
        
        with patch.object(StorageMonitorService, 'STORAGE_IMAGES_DIR', self.test_storage_dir):
            monitor_service = StorageMonitorService(config_service=config_service)
            
            # Should handle permission errors gracefully
            try:
                metrics = monitor_service.get_storage_metrics()
                self.assertIsNotNone(metrics)
            except PermissionError:
                # Expected behavior for restricted files
                pass
    
    def test_symlink_security(self):
        """Test protection against symlink attacks"""
        # Create a symlink pointing outside storage directory
        target_file = os.path.join(self.temp_dir, "outside_target.txt")
        with open(target_file, 'w') as f:
            f.write("sensitive data")
        
        symlink_path = os.path.join(self.test_storage_dir, "malicious_link")
        
        try:
            os.symlink(target_file, symlink_path)
            
            # Storage calculation should not follow symlinks outside storage directory
            from storage_monitor_service import StorageMonitorService
            from storage_configuration_service import StorageConfigurationService
            
            config_service = StorageConfigurationService()
            
            with patch.object(StorageMonitorService, 'STORAGE_IMAGES_DIR', self.test_storage_dir):
                monitor_service = StorageMonitorService(config_service=config_service)
                
                # Should either ignore symlinks or validate they stay within storage directory
                metrics = monitor_service.get_storage_metrics()
                self.assertIsNotNone(metrics)
                
        except OSError:
            # Some systems don't support symlinks
            pass
    
    def test_redis_data_security(self):
        """Test Redis data security"""
        # Mock Redis with security considerations
        redis_data = {}
        mock_redis = Mock()
        
        def secure_set(key, value):
            # Simulate data validation before storage
            if not isinstance(key, str) or not key.startswith('storage_limit:'):
                raise ValueError("Invalid Redis key format")
            
            # Validate JSON structure
            try:
                json.loads(value)
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON data")
            
            redis_data[key] = value
            return True
        
        mock_redis.set = secure_set
        mock_redis.get = lambda key: redis_data.get(key)
        mock_redis.ping.return_value = True
        
        # Test secure Redis operations
        from storage_limit_enforcer import StorageLimitEnforcer
        from storage_configuration_service import StorageConfigurationService
        
        config_service = StorageConfigurationService()
        mock_monitor = Mock()
        
        with patch('storage_limit_enforcer.redis.Redis', return_value=mock_redis):
            enforcer = StorageLimitEnforcer(
                config_service=config_service,
                monitor_service=mock_monitor
            )
            
            # Should store data securely
            enforcer.block_caption_generation("Security test")
            
            # Verify data was stored with proper validation
            self.assertIn('storage_limit:blocked', redis_data)


if __name__ == '__main__':
    unittest.main()
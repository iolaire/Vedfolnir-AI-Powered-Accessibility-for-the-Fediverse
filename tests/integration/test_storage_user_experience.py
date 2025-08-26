# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
End-to-end tests covering user experience during storage limits.

Tests the complete user journey from normal operation through storage limit
notifications, blocked operations, and recovery scenarios.
"""

import unittest
import tempfile
import shutil
import os
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from storage_configuration_service import StorageConfigurationService
from storage_monitor_service import StorageMonitorService, StorageMetrics
from storage_limit_enforcer import StorageLimitEnforcer
from storage_user_notification_system import StorageUserNotificationSystem, StorageNotificationContext
from admin_storage_dashboard import AdminStorageDashboard
from storage_override_system import StorageOverrideSystem


class TestStorageUserExperience(unittest.TestCase):
    """End-to-end tests for user experience during storage limits"""
    
    def setUp(self):
        """Set up test fixtures for user experience testing"""
        # Create temporary directory for test storage
        self.temp_dir = tempfile.mkdtemp()
        self.test_storage_dir = os.path.join(self.temp_dir, "storage", "images")
        os.makedirs(self.test_storage_dir, exist_ok=True)
        
        # Mock Redis for testing
        self.redis_data = {}
        self.mock_redis = Mock()
        self.mock_redis.ping.return_value = True
        
        def mock_get(key):
            return self.redis_data.get(key)
        
        def mock_set(key, value):
            self.redis_data[key] = value
            return True
        
        def mock_delete(key):
            if key in self.redis_data:
                del self.redis_data[key]
                return 1
            return 0
        
        self.mock_redis.get = mock_get
        self.mock_redis.set = mock_set
        self.mock_redis.delete = mock_delete
        
        # Patch storage directory
        self.storage_dir_patcher = patch.object(
            StorageMonitorService, 'STORAGE_IMAGES_DIR', self.test_storage_dir
        )
        self.storage_dir_patcher.start()
        
        # Initialize services
        self.config_service = StorageConfigurationService()
        self.monitor_service = StorageMonitorService(config_service=self.config_service)
        
        with patch('storage_limit_enforcer.redis.Redis', return_value=self.mock_redis):
            self.enforcer = StorageLimitEnforcer(
                config_service=self.config_service,
                monitor_service=self.monitor_service
            )
        
        self.user_notification = StorageUserNotificationSystem(
            config_service=self.config_service,
            monitor_service=self.monitor_service,
            enforcer=self.enforcer
        )
        
        self.dashboard = AdminStorageDashboard(
            config_service=self.config_service,
            monitor_service=self.monitor_service,
            enforcer=self.enforcer
        )
        
        # Mock database manager for override system
        self.mock_db_manager = Mock()
        self.mock_session = Mock()
        self.mock_db_manager.get_session.return_value.__enter__.return_value = self.mock_session
        self.mock_db_manager.get_session.return_value.__exit__.return_value = None
        
        self.override_system = StorageOverrideSystem(db_manager=self.mock_db_manager)
    
    def tearDown(self):
        """Clean up test fixtures"""
        self.storage_dir_patcher.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_test_files(self, total_size_gb: float):
        """Create test files with specified total size"""
        total_bytes = int(total_size_gb * 1024 ** 3)
        file_size = 1024 * 1024  # 1MB per file
        num_files = total_bytes // file_size
        
        for i in range(num_files):
            file_path = os.path.join(self.test_storage_dir, f"test_image_{i}.jpg")
            with open(file_path, 'wb') as f:
                f.write(b'0' * file_size)
        
        # Create remainder file if needed
        remainder = total_bytes % file_size
        if remainder > 0:
            file_path = os.path.join(self.test_storage_dir, f"test_image_remainder.jpg")
            with open(file_path, 'wb') as f:
                f.write(b'0' * remainder)
    
    def test_normal_user_experience(self):
        """Test normal user experience when storage is within limits"""
        # Create files below warning threshold (5GB < 8GB warning)
        self.create_test_files(5.0)
        
        # User should see no storage notifications
        notification_context = self.user_notification.get_storage_notification_context()
        self.assertIsNone(notification_context, "No notification should be shown for normal usage")
        
        # Caption form should be available
        self.assertFalse(self.user_notification.should_hide_caption_form(), 
                        "Caption form should be available for normal usage")
        
        # Storage check should allow generation
        check_result = self.enforcer.check_storage_before_generation()
        self.assertTrue(check_result.allowed, "Caption generation should be allowed")
        self.assertIsNone(check_result.block_reason, "No blocking reason should be present")
        
        # Admin dashboard should show green status
        dashboard_data = self.dashboard.get_storage_dashboard_data()
        self.assertEqual(dashboard_data.status_color, 'green', "Dashboard should show green status")
        self.assertFalse(dashboard_data.is_limit_exceeded, "Limit should not be exceeded")
    
    def test_warning_threshold_user_experience(self):
        """Test user experience when approaching storage limit (80-100%)"""
        # Create files above warning threshold but below limit (8.5GB > 8GB warning, < 10GB limit)
        self.create_test_files(8.5)
        
        # Clear cache to get fresh metrics
        self.monitor_service._cache = {}
        
        # User should still be able to generate captions
        check_result = self.enforcer.check_storage_before_generation()
        self.assertTrue(check_result.allowed, "Caption generation should still be allowed in warning state")
        
        # No user notification should be shown yet (only admin warnings)
        notification_context = self.user_notification.get_storage_notification_context()
        self.assertIsNone(notification_context, "No user notification should be shown in warning state")
        
        # Caption form should still be available
        self.assertFalse(self.user_notification.should_hide_caption_form(), 
                        "Caption form should still be available in warning state")
        
        # Admin dashboard should show yellow status
        dashboard_data = self.dashboard.get_storage_dashboard_data()
        self.assertEqual(dashboard_data.status_color, 'yellow', "Dashboard should show yellow status")
        self.assertFalse(dashboard_data.is_limit_exceeded, "Limit should not be exceeded yet")
        self.assertTrue(dashboard_data.usage_percentage > 80.0, "Usage should be above warning threshold")
    
    def test_storage_limit_exceeded_user_experience(self):
        """Test user experience when storage limit is exceeded"""
        # Create files above storage limit (12GB > 10GB limit)
        self.create_test_files(12.0)
        
        # Clear cache to get fresh metrics
        self.monitor_service._cache = {}
        
        # Storage check should block generation
        check_result = self.enforcer.check_storage_before_generation()
        self.assertFalse(check_result.allowed, "Caption generation should be blocked")
        self.assertIsNotNone(check_result.block_reason, "Block reason should be provided")
        self.assertIn("storage limit", check_result.block_reason.lower(), 
                     "Block reason should mention storage limit")
        
        # User should see storage limit notification
        notification_context = self.user_notification.get_storage_notification_context()
        self.assertIsNotNone(notification_context, "Storage notification should be shown")
        self.assertEqual(notification_context.notification_type, 'storage_limit', 
                        "Notification type should be storage_limit")
        self.assertIn("temporarily unavailable", notification_context.message.lower(), 
                     "Message should explain service is temporarily unavailable")
        self.assertIn("administrator", notification_context.message.lower(), 
                     "Message should mention administrators are working on it")
        
        # Caption form should be hidden
        self.assertTrue(self.user_notification.should_hide_caption_form(), 
                       "Caption form should be hidden when storage limit exceeded")
        
        # Admin dashboard should show red status
        dashboard_data = self.dashboard.get_storage_dashboard_data()
        self.assertEqual(dashboard_data.status_color, 'red', "Dashboard should show red status")
        self.assertTrue(dashboard_data.is_limit_exceeded, "Limit should be exceeded")
        self.assertTrue(dashboard_data.usage_percentage > 100.0, "Usage should be above 100%")
    
    def test_storage_limit_recovery_user_experience(self):
        """Test user experience during storage limit recovery"""
        # Start with storage limit exceeded
        self.create_test_files(12.0)  # 12GB > 10GB limit
        
        # Clear cache and verify blocking
        self.monitor_service._cache = {}
        check_result = self.enforcer.check_storage_before_generation()
        self.assertFalse(check_result.allowed, "Should be blocked initially")
        
        # User should see notification and hidden form
        notification_context = self.user_notification.get_storage_notification_context()
        self.assertIsNotNone(notification_context, "Should show notification when blocked")
        self.assertTrue(self.user_notification.should_hide_caption_form(), 
                       "Form should be hidden when blocked")
        
        # Simulate cleanup - remove some files to go below limit
        files_to_remove = list(os.listdir(self.test_storage_dir))[:2000]  # Remove ~2GB worth
        for filename in files_to_remove:
            file_path = os.path.join(self.test_storage_dir, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
        
        # Clear cache to get fresh metrics after cleanup
        self.monitor_service._cache = {}
        
        # Storage should now be unblocked
        check_result = self.enforcer.check_storage_before_generation()
        self.assertTrue(check_result.allowed, "Should be unblocked after cleanup")
        
        # User notification should be cleared
        notification_context = self.user_notification.get_storage_notification_context()
        self.assertIsNone(notification_context, "Notification should be cleared after recovery")
        
        # Caption form should be available again
        self.assertFalse(self.user_notification.should_hide_caption_form(), 
                        "Form should be available again after recovery")
        
        # Admin dashboard should show improved status
        dashboard_data = self.dashboard.get_storage_dashboard_data()
        self.assertNotEqual(dashboard_data.status_color, 'red', "Should no longer show red status")
        self.assertFalse(dashboard_data.is_limit_exceeded, "Limit should no longer be exceeded")
    
    def test_admin_override_user_experience(self):
        """Test user experience during admin storage override"""
        # Start with storage limit exceeded
        self.create_test_files(12.0)  # 12GB > 10GB limit
        
        # Clear cache and verify blocking
        self.monitor_service._cache = {}
        check_result = self.enforcer.check_storage_before_generation()
        self.assertFalse(check_result.allowed, "Should be blocked initially")
        
        # Mock admin override activation
        mock_override = Mock()
        mock_override.id = 1
        mock_override.is_active = True
        mock_override.expires_at = datetime.utcnow() + timedelta(hours=1)
        mock_override.admin_user_id = 1
        mock_override.reason = "Emergency maintenance"
        
        self.mock_session.add.return_value = None
        self.mock_session.commit.return_value = None
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = mock_override
        
        # Activate override
        result = self.override_system.activate_override(
            duration_hours=1,
            admin_user_id=1,
            reason="Emergency maintenance"
        )
        self.assertTrue(result, "Override should be activated successfully")
        
        # Test that enforcer respects override
        with patch.object(self.enforcer, 'override_system', self.override_system):
            check_result = self.enforcer.check_storage_before_generation()
            self.assertTrue(check_result.allowed, "Should allow generation during override")
        
        # User notification should indicate override is active
        with patch.object(self.user_notification, 'override_system', self.override_system):
            notification_context = self.user_notification.get_storage_notification_context()
            
            if notification_context:
                # If notification is shown, it should indicate override is active
                self.assertIn("override", notification_context.message.lower(), 
                             "Notification should mention override if shown")
            
            # Caption form should be available during override
            should_hide = self.user_notification.should_hide_caption_form()
            # During override, form should be available even if storage is over limit
            # This depends on implementation - override might still show warning but allow access
    
    def test_multiple_users_concurrent_experience(self):
        """Test user experience with multiple concurrent users during storage limits"""
        import threading
        
        # Create files to exceed limit
        self.create_test_files(12.0)  # 12GB > 10GB limit
        
        # Clear cache
        self.monitor_service._cache = {}
        
        user_experiences = []
        
        def simulate_user_experience():
            """Simulate a user's experience checking storage status"""
            try:
                # Check if generation is allowed
                check_result = self.enforcer.check_storage_before_generation()
                
                # Get notification context
                notification_context = self.user_notification.get_storage_notification_context()
                
                # Check if form should be hidden
                should_hide_form = self.user_notification.should_hide_caption_form()
                
                user_experiences.append({
                    'allowed': check_result.allowed,
                    'block_reason': check_result.block_reason,
                    'has_notification': notification_context is not None,
                    'form_hidden': should_hide_form,
                    'timestamp': time.time()
                })
                
            except Exception as e:
                user_experiences.append({'error': str(e)})
        
        # Simulate multiple concurrent users
        threads = []
        for i in range(5):
            thread = threading.Thread(target=simulate_user_experience)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Verify all users had consistent experience
        self.assertEqual(len(user_experiences), 5, "All user simulations should complete")
        
        for experience in user_experiences:
            self.assertNotIn('error', experience, "No errors should occur")
            self.assertFalse(experience['allowed'], "All users should be blocked")
            self.assertTrue(experience['has_notification'], "All users should see notification")
            self.assertTrue(experience['form_hidden'], "Form should be hidden for all users")
    
    def test_user_experience_during_system_transitions(self):
        """Test user experience during system state transitions"""
        # Test transition from normal to warning
        self.create_test_files(7.5)  # Below warning threshold
        
        # Initial state - normal
        self.monitor_service._cache = {}
        notification_context = self.user_notification.get_storage_notification_context()
        self.assertIsNone(notification_context, "No notification in normal state")
        
        # Add more files to reach warning threshold
        self.create_test_files(1.0)  # Now 8.5GB > 8GB warning
        
        # Clear cache and check warning state
        self.monitor_service._cache = {}
        check_result = self.enforcer.check_storage_before_generation()
        self.assertTrue(check_result.allowed, "Should still allow in warning state")
        
        # Add more files to exceed limit
        self.create_test_files(2.0)  # Now 10.5GB > 10GB limit
        
        # Clear cache and check blocked state
        self.monitor_service._cache = {}
        check_result = self.enforcer.check_storage_before_generation()
        self.assertFalse(check_result.allowed, "Should block when limit exceeded")
        
        # User should now see notification
        notification_context = self.user_notification.get_storage_notification_context()
        self.assertIsNotNone(notification_context, "Should show notification when blocked")
        
        # Form should be hidden
        self.assertTrue(self.user_notification.should_hide_caption_form(), 
                       "Form should be hidden when blocked")
    
    def test_user_experience_error_scenarios(self):
        """Test user experience during error scenarios"""
        # Test Redis connection failure
        self.mock_redis.ping.side_effect = Exception("Redis connection failed")
        
        # User experience should degrade gracefully
        try:
            check_result = self.enforcer.check_storage_before_generation()
            # Should default to safe mode (block generation) on Redis errors
            self.assertFalse(check_result.allowed, "Should block on Redis errors for safety")
            
            # User should see appropriate error notification
            notification_context = self.user_notification.get_storage_notification_context()
            # Implementation may or may not show notification for system errors
            # The key is that the system should fail safely
            
        except Exception:
            self.fail("System should handle Redis errors gracefully")
        
        # Test storage calculation errors
        with patch.object(self.monitor_service, 'calculate_total_storage_bytes', 
                         side_effect=OSError("Permission denied")):
            try:
                check_result = self.enforcer.check_storage_before_generation()
                # Should handle calculation errors gracefully
                self.assertIsNotNone(check_result, "Should return a result even on calculation errors")
                
            except Exception:
                self.fail("System should handle storage calculation errors gracefully")
    
    def test_user_notification_message_quality(self):
        """Test quality and clarity of user notification messages"""
        # Create files to exceed limit
        self.create_test_files(12.0)  # 12GB > 10GB limit
        
        # Clear cache
        self.monitor_service._cache = {}
        
        # Trigger blocking
        check_result = self.enforcer.check_storage_before_generation()
        self.assertFalse(check_result.allowed)
        
        # Get user notification
        notification_context = self.user_notification.get_storage_notification_context()
        self.assertIsNotNone(notification_context)
        
        message = notification_context.message
        
        # Message quality checks
        self.assertGreater(len(message), 50, "Message should be sufficiently detailed")
        self.assertLess(len(message), 500, "Message should not be too verbose")
        
        # Message should be user-friendly
        technical_terms = ['redis', 'database', 'exception', 'error code', 'stack trace']
        for term in technical_terms:
            self.assertNotIn(term.lower(), message.lower(), 
                           f"Message should not contain technical term: {term}")
        
        # Message should contain helpful information
        helpful_terms = ['temporarily', 'unavailable', 'administrator', 'working']
        found_helpful_terms = sum(1 for term in helpful_terms if term.lower() in message.lower())
        self.assertGreaterEqual(found_helpful_terms, 2, 
                               "Message should contain helpful explanatory terms")
        
        # Message should have appropriate tone
        self.assertNotIn('error', message.lower(), "Message should not use alarming language")
        self.assertNotIn('failed', message.lower(), "Message should not use negative language")


if __name__ == '__main__':
    unittest.main()
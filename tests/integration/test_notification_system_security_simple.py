# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Simple Security Testing for Notification System

This test focuses specifically on security aspects without complex integration
that might cause hanging issues.
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from models import UserRole, NotificationType, NotificationPriority, NotificationCategory
from unified_notification_manager import (
    UnifiedNotificationManager, NotificationMessage, AdminNotificationMessage
)


class TestNotificationSystemSecuritySimple(unittest.TestCase):
    """
    Simple security testing for notification system
    
    Tests core security functionality without complex integration
    """
    
    def setUp(self):
        """Set up test environment with minimal mocking"""
        # Create minimal mocks
        self.mock_db_manager = Mock()
        self.mock_websocket_factory = Mock()
        self.mock_auth_handler = Mock()
        self.mock_namespace_manager = Mock()
        
        # Mock database session
        self.mock_session = Mock()
        context_manager = Mock()
        context_manager.__enter__ = Mock(return_value=self.mock_session)
        context_manager.__exit__ = Mock(return_value=None)
        self.mock_db_manager.get_session.return_value = context_manager
        
        # Create notification manager
        self.notification_manager = UnifiedNotificationManager(
            websocket_factory=self.mock_websocket_factory,
            auth_handler=self.mock_auth_handler,
            namespace_manager=self.mock_namespace_manager,
            db_manager=self.mock_db_manager
        )
        
        # Mock user data for testing
        self.admin_user = Mock()
        self.admin_user.role = UserRole.ADMIN
        self.regular_user = Mock()
        self.regular_user.role = UserRole.VIEWER
        
        # Mock database user lookup
        def mock_session_get(model_class, user_id):
            if user_id == 1:
                return self.admin_user
            elif user_id == 2:
                return self.regular_user
            return None
        
        self.mock_session.get = mock_session_get
        
        # Disable rate limiting for testing
        self.notification_manager._is_rate_limited = lambda user_id: False
        self.notification_manager._check_priority_rate_limit = lambda user_id, message: True
        
        # Mock delivery methods to prevent hanging
        self.notification_manager._deliver_to_online_user = Mock(return_value=True)
        self.notification_manager._store_message_in_database = Mock()
        self.notification_manager._add_to_message_history = Mock()
    
    def test_admin_notification_access_control(self):
        """Test that only admin users can receive admin notifications"""
        admin_message = AdminNotificationMessage(
            id="test_admin_001",
            type=NotificationType.ERROR,
            title="Admin Only Message",
            message="This should only go to admin users",
            category=NotificationCategory.ADMIN,
            priority=NotificationPriority.HIGH
        )
        
        # Test admin user can receive admin notifications
        admin_success = self.notification_manager.send_user_notification(1, admin_message)
        self.assertTrue(admin_success, "Admin user should receive admin notifications")
        
        # Test regular user cannot receive admin notifications
        regular_success = self.notification_manager.send_user_notification(2, admin_message)
        self.assertFalse(regular_success, "Regular user should not receive admin notifications")
    
    def test_security_notification_access_control(self):
        """Test that only authorized users can receive security notifications"""
        security_message = NotificationMessage(
            id="test_security_001",
            type=NotificationType.WARNING,
            title="Security Alert",
            message="Security event detected",
            category=NotificationCategory.SECURITY,
            priority=NotificationPriority.HIGH
        )
        
        # Test admin user can receive security notifications
        admin_success = self.notification_manager.send_user_notification(1, security_message)
        self.assertTrue(admin_success, "Admin user should receive security notifications")
        
        # Test regular user cannot receive security notifications
        regular_success = self.notification_manager.send_user_notification(2, security_message)
        self.assertFalse(regular_success, "Regular user should not receive security notifications")
    
    def test_system_notification_access_allowed(self):
        """Test that all users can receive system notifications"""
        system_message = NotificationMessage(
            id="test_system_001",
            type=NotificationType.INFO,
            title="System Update",
            message="System maintenance scheduled",
            category=NotificationCategory.SYSTEM,
            priority=NotificationPriority.NORMAL
        )
        
        # Test admin user can receive system notifications
        admin_success = self.notification_manager.send_user_notification(1, system_message)
        self.assertTrue(admin_success, "Admin user should receive system notifications")
        
        # Test regular user can receive system notifications
        regular_success = self.notification_manager.send_user_notification(2, system_message)
        self.assertTrue(regular_success, "Regular user should receive system notifications")
    
    def test_user_permission_validation(self):
        """Test user permission validation logic"""
        # Test with valid admin user
        admin_valid = self.notification_manager._validate_user_permissions(1, NotificationMessage(
            id="test_001",
            type=NotificationType.INFO,
            title="Test",
            message="Test message",
            category=NotificationCategory.ADMIN
        ))
        self.assertTrue(admin_valid, "Admin should have permission for admin messages")
        
        # Test with regular user for admin message
        regular_invalid = self.notification_manager._validate_user_permissions(2, NotificationMessage(
            id="test_002",
            type=NotificationType.INFO,
            title="Test",
            message="Test message",
            category=NotificationCategory.ADMIN
        ))
        self.assertFalse(regular_invalid, "Regular user should not have permission for admin messages")
        
        # Test with regular user for system message
        regular_valid = self.notification_manager._validate_user_permissions(2, NotificationMessage(
            id="test_003",
            type=NotificationType.INFO,
            title="Test",
            message="Test message",
            category=NotificationCategory.SYSTEM
        ))
        self.assertTrue(regular_valid, "Regular user should have permission for system messages")
    
    def test_message_data_structure_integrity(self):
        """Test that message data structures maintain integrity"""
        message = NotificationMessage(
            id="test_integrity_001",
            type=NotificationType.INFO,
            title="Integrity Test",
            message="Testing message integrity",
            category=NotificationCategory.SYSTEM,
            priority=NotificationPriority.NORMAL
        )
        
        # Test serialization and deserialization
        message_dict = message.to_dict()
        self.assertIsInstance(message_dict, dict)
        self.assertEqual(message_dict['id'], "test_integrity_001")
        self.assertEqual(message_dict['type'], NotificationType.INFO.value)
        
        # Test reconstruction from dict
        reconstructed = NotificationMessage.from_dict(message_dict)
        self.assertEqual(reconstructed.id, message.id)
        self.assertEqual(reconstructed.type, message.type)
        self.assertEqual(reconstructed.title, message.title)
    
    def test_invalid_user_handling(self):
        """Test handling of invalid user IDs"""
        message = NotificationMessage(
            id="test_invalid_001",
            type=NotificationType.INFO,
            title="Invalid User Test",
            message="Testing invalid user handling",
            category=NotificationCategory.SYSTEM
        )
        
        # Test with non-existent user ID
        invalid_success = self.notification_manager.send_user_notification(999, message)
        self.assertFalse(invalid_success, "Should fail for non-existent user")
        
        # Test with None user ID
        none_success = self.notification_manager.send_user_notification(None, message)
        self.assertFalse(none_success, "Should fail for None user ID")


if __name__ == '__main__':
    unittest.main()
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test Admin User Management Notifications

This module tests the admin user management notification system integration
with the unified WebSocket notification framework.
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from admin_user_management_notification_handler import (
    AdminUserManagementNotificationHandler, UserOperationContext
)
from admin_user_management_integration import (
    AdminUserManagementIntegration, create_admin_user_management_integration
)
from unified_notification_manager import (
    UnifiedNotificationManager, AdminNotificationMessage, 
    NotificationType, NotificationPriority, NotificationCategory
)
from models import UserRole


class TestAdminUserManagementNotificationHandler(unittest.TestCase):
    """Test cases for admin user management notification handler"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock notification manager
        self.mock_notification_manager = Mock(spec=UnifiedNotificationManager)
        self.mock_notification_manager.send_admin_notification.return_value = True
        
        # Create handler
        self.handler = AdminUserManagementNotificationHandler(self.mock_notification_manager)
        
        # Create test context
        self.test_context = UserOperationContext(
            operation_type='test_operation',
            target_user_id=123,
            target_username='testuser',
            admin_user_id=1,
            admin_username='admin',
            ip_address='127.0.0.1',
            user_agent='Test Agent'
        )
    
    def test_handler_initialization(self):
        """Test handler initialization"""
        self.assertIsNotNone(self.handler)
        self.assertEqual(self.handler.notification_manager, self.mock_notification_manager)
        self.assertIn('user_created', self.handler.operation_types)
        self.assertIn('user_deleted', self.handler.operation_types)
        self.assertIn('user_role_changed', self.handler.operation_types)
    
    def test_notify_user_created(self):
        """Test user creation notification"""
        user_data = {
            'id': 123,
            'username': 'testuser',
            'email': 'test@example.com',
            'role': 'viewer',
            'email_verified': True
        }
        
        result = self.handler.notify_user_created(self.test_context, user_data)
        
        self.assertTrue(result)
        self.mock_notification_manager.send_admin_notification.assert_called_once()
        
        # Verify notification content
        call_args = self.mock_notification_manager.send_admin_notification.call_args[0][0]
        self.assertIsInstance(call_args, AdminNotificationMessage)
        self.assertEqual(call_args.type, NotificationType.SUCCESS)
        self.assertEqual(call_args.title, "User Created")
        self.assertTrue(call_args.admin_only)
        self.assertEqual(call_args.category, NotificationCategory.ADMIN)
        
        # Verify user action data
        user_action_data = call_args.user_action_data
        self.assertEqual(user_action_data['operation'], 'user_created')
        self.assertEqual(user_action_data['target_user_id'], 123)
        self.assertEqual(user_action_data['target_username'], 'testuser')
        self.assertEqual(user_action_data['admin_user_id'], 1)
        self.assertEqual(user_action_data['admin_username'], 'admin')
    
    def test_notify_user_updated(self):
        """Test user update notification"""
        changes = {
            'email': {'old': 'old@example.com', 'new': 'new@example.com'},
            'role': {'old': 'viewer', 'new': 'reviewer'},
            'password': 'updated'
        }
        
        result = self.handler.notify_user_updated(self.test_context, changes)
        
        self.assertTrue(result)
        self.mock_notification_manager.send_admin_notification.assert_called_once()
        
        # Verify notification content
        call_args = self.mock_notification_manager.send_admin_notification.call_args[0][0]
        self.assertIsInstance(call_args, AdminNotificationMessage)
        self.assertEqual(call_args.type, NotificationType.INFO)
        self.assertEqual(call_args.title, "User Updated")
        
        # Verify changes are included
        user_action_data = call_args.user_action_data
        self.assertEqual(user_action_data['changes'], changes)
    
    def test_notify_user_deleted(self):
        """Test user deletion notification"""
        deletion_reason = "Policy violation"
        
        result = self.handler.notify_user_deleted(self.test_context, deletion_reason)
        
        self.assertTrue(result)
        self.mock_notification_manager.send_admin_notification.assert_called_once()
        
        # Verify notification content
        call_args = self.mock_notification_manager.send_admin_notification.call_args[0][0]
        self.assertIsInstance(call_args, AdminNotificationMessage)
        self.assertEqual(call_args.type, NotificationType.WARNING)
        self.assertEqual(call_args.title, "User Deleted")
        self.assertEqual(call_args.priority, NotificationPriority.HIGH)
        
        # Verify deletion reason is included
        user_action_data = call_args.user_action_data
        self.assertEqual(user_action_data['deletion_reason'], deletion_reason)
    
    def test_notify_user_role_changed(self):
        """Test user role change notification"""
        old_role = UserRole.VIEWER
        new_role = UserRole.ADMIN
        reason = "Promotion to admin"
        
        result = self.handler.notify_user_role_changed(
            self.test_context, old_role, new_role, reason
        )
        
        self.assertTrue(result)
        self.mock_notification_manager.send_admin_notification.assert_called_once()
        
        # Verify notification content
        call_args = self.mock_notification_manager.send_admin_notification.call_args[0][0]
        self.assertIsInstance(call_args, AdminNotificationMessage)
        self.assertEqual(call_args.type, NotificationType.INFO)
        self.assertEqual(call_args.title, "User Role Changed")
        self.assertEqual(call_args.priority, NotificationPriority.CRITICAL)  # Admin role change
        self.assertTrue(call_args.requires_admin_action)  # Admin role changes require attention
        
        # Verify role change data
        user_action_data = call_args.user_action_data
        self.assertEqual(user_action_data['old_role'], old_role.value)
        self.assertEqual(user_action_data['new_role'], new_role.value)
        self.assertEqual(user_action_data['reason'], reason)
    
    def test_notify_user_status_changed(self):
        """Test user status change notification"""
        status_changes = {
            'is_active': {'old': True, 'new': False},
            'account_locked': {'old': False, 'new': True},
            'email_verified': {'old': False, 'new': True}
        }
        
        result = self.handler.notify_user_status_changed(self.test_context, status_changes)
        
        self.assertTrue(result)
        self.mock_notification_manager.send_admin_notification.assert_called_once()
        
        # Verify notification content
        call_args = self.mock_notification_manager.send_admin_notification.call_args[0][0]
        self.assertIsInstance(call_args, AdminNotificationMessage)
        self.assertEqual(call_args.type, NotificationType.INFO)
        self.assertEqual(call_args.title, "User Status Changed")
        self.assertEqual(call_args.priority, NotificationPriority.HIGH)  # Account status changes
        
        # Verify status changes are included
        user_action_data = call_args.user_action_data
        self.assertEqual(user_action_data['status_changes'], status_changes)
    
    def test_notify_user_password_reset(self):
        """Test user password reset notification"""
        reset_method = "generate"
        temp_password_generated = True
        
        result = self.handler.notify_user_password_reset(
            self.test_context, reset_method, temp_password_generated
        )
        
        self.assertTrue(result)
        self.mock_notification_manager.send_admin_notification.assert_called_once()
        
        # Verify notification content
        call_args = self.mock_notification_manager.send_admin_notification.call_args[0][0]
        self.assertIsInstance(call_args, AdminNotificationMessage)
        self.assertEqual(call_args.type, NotificationType.WARNING)
        self.assertEqual(call_args.title, "Password Reset")
        self.assertEqual(call_args.priority, NotificationPriority.HIGH)
        
        # Verify password reset data
        user_action_data = call_args.user_action_data
        self.assertEqual(user_action_data['reset_method'], reset_method)
        self.assertEqual(user_action_data['temp_password_generated'], temp_password_generated)
    
    def test_notify_bulk_user_operation(self):
        """Test bulk user operation notification"""
        operation_type = "user_deletion"
        admin_context = {
            'admin_user_id': 1,
            'admin_username': 'admin',
            'ip_address': '127.0.0.1'
        }
        results = [
            {'success': True, 'user_id': 1},
            {'success': True, 'user_id': 2},
            {'success': False, 'user_id': 3, 'error': 'Cannot delete admin'}
        ]
        
        result = self.handler.notify_bulk_user_operation(
            operation_type, admin_context, results
        )
        
        self.assertTrue(result)
        self.mock_notification_manager.send_admin_notification.assert_called_once()
        
        # Verify notification content
        call_args = self.mock_notification_manager.send_admin_notification.call_args[0][0]
        self.assertIsInstance(call_args, AdminNotificationMessage)
        self.assertEqual(call_args.type, NotificationType.WARNING)  # Some failures
        self.assertEqual(call_args.title, "Bulk User_Deletion")
        self.assertTrue(call_args.requires_admin_action)  # Has failures
        
        # Verify bulk operation data
        user_action_data = call_args.user_action_data
        self.assertEqual(user_action_data['total_operations'], 3)
        self.assertEqual(user_action_data['successful_operations'], 2)
        self.assertEqual(user_action_data['failed_operations'], 1)
    
    def test_notification_failure_handling(self):
        """Test handling of notification failures"""
        # Mock notification manager to return False
        self.mock_notification_manager.send_admin_notification.return_value = False
        
        user_data = {'id': 123, 'username': 'testuser'}
        result = self.handler.notify_user_created(self.test_context, user_data)
        
        self.assertFalse(result)
        self.mock_notification_manager.send_admin_notification.assert_called_once()
    
    def test_notification_exception_handling(self):
        """Test handling of notification exceptions"""
        # Mock notification manager to raise exception
        self.mock_notification_manager.send_admin_notification.side_effect = Exception("Test error")
        
        user_data = {'id': 123, 'username': 'testuser'}
        result = self.handler.notify_user_created(self.test_context, user_data)
        
        self.assertFalse(result)
    
    def test_get_notification_stats(self):
        """Test getting notification statistics"""
        # Mock notification manager stats
        mock_stats = {
            'total_messages': 100,
            'delivered_messages': 95,
            'failed_messages': 5
        }
        self.mock_notification_manager.get_notification_stats.return_value = mock_stats
        
        stats = self.handler.get_notification_stats()
        
        self.assertEqual(stats['handler_type'], 'admin_user_management')
        self.assertIn('supported_operations', stats)
        self.assertEqual(stats['notification_manager_stats'], mock_stats)
        self.assertEqual(stats['handler_status'], 'active')


class TestAdminUserManagementIntegration(unittest.TestCase):
    """Test cases for admin user management integration"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock notification manager
        self.mock_notification_manager = Mock(spec=UnifiedNotificationManager)
        
        # Create integration
        self.integration = AdminUserManagementIntegration(self.mock_notification_manager)
        
        # Mock Flask app
        self.mock_app = Mock()
        self.mock_app.config = {}
    
    def test_integration_initialization(self):
        """Test integration initialization"""
        self.assertIsNotNone(self.integration)
        self.assertEqual(self.integration.notification_manager, self.mock_notification_manager)
        self.assertIsInstance(
            self.integration.notification_handler, 
            AdminUserManagementNotificationHandler
        )
    
    def test_initialize_app_integration(self):
        """Test Flask app integration initialization"""
        result = self.integration.initialize_app_integration(self.mock_app)
        
        self.assertTrue(result['success'])
        self.assertTrue(result['handler_registered'])
        self.assertTrue(result['integration_active'])
        self.assertIn('supported_operations', result)
        
        # Verify handler is registered in app config
        self.assertIn('admin_user_management_notification_handler', self.mock_app.config)
        self.assertIn('admin_user_management_integration', self.mock_app.config)
    
    def test_get_notification_handler(self):
        """Test getting notification handler"""
        handler = self.integration.get_notification_handler()
        
        self.assertIsInstance(handler, AdminUserManagementNotificationHandler)
        self.assertEqual(handler, self.integration.notification_handler)
    
    def test_get_integration_status(self):
        """Test getting integration status"""
        # Mock handler stats
        mock_stats = {'handler_type': 'admin_user_management'}
        self.integration.notification_handler.get_notification_stats = Mock(return_value=mock_stats)
        
        status = self.integration.get_integration_status()
        
        self.assertTrue(status['integration_active'])
        self.assertEqual(status['notification_handler_status'], 'active')
        self.assertEqual(status['handler_stats'], mock_stats)
        self.assertIn('supported_operations', status)
    
    def test_factory_function(self):
        """Test factory function"""
        integration = create_admin_user_management_integration(self.mock_notification_manager)
        
        self.assertIsInstance(integration, AdminUserManagementIntegration)
        self.assertEqual(integration.notification_manager, self.mock_notification_manager)


class TestUserOperationContext(unittest.TestCase):
    """Test cases for user operation context"""
    
    def test_context_creation(self):
        """Test operation context creation"""
        context = UserOperationContext(
            operation_type='user_created',
            target_user_id=123,
            target_username='testuser',
            admin_user_id=1,
            admin_username='admin',
            ip_address='127.0.0.1',
            user_agent='Test Agent',
            additional_data={'key': 'value'}
        )
        
        self.assertEqual(context.operation_type, 'user_created')
        self.assertEqual(context.target_user_id, 123)
        self.assertEqual(context.target_username, 'testuser')
        self.assertEqual(context.admin_user_id, 1)
        self.assertEqual(context.admin_username, 'admin')
        self.assertEqual(context.ip_address, '127.0.0.1')
        self.assertEqual(context.user_agent, 'Test Agent')
        self.assertEqual(context.additional_data, {'key': 'value'})
    
    def test_context_optional_fields(self):
        """Test operation context with optional fields"""
        context = UserOperationContext(
            operation_type='user_updated',
            target_user_id=456,
            target_username='testuser2',
            admin_user_id=2,
            admin_username='admin2'
        )
        
        self.assertEqual(context.operation_type, 'user_updated')
        self.assertEqual(context.target_user_id, 456)
        self.assertIsNone(context.ip_address)
        self.assertIsNone(context.user_agent)
        self.assertIsNone(context.additional_data)


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)
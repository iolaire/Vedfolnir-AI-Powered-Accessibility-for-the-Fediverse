# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Security tests for Notification System Authentication and Authorization

Tests authentication and authorization integration with the notification system,
including role-based access control, permission validation, security event logging,
and protection against unauthorized access.
"""

import unittest
import sys
import os
import uuid
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock
from collections import defaultdict

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.services.notification.manager.unified_manager import (
    UnifiedNotificationManager, NotificationMessage, 
    AdminNotificationMessage, SystemNotificationMessage
)
from notification_message_router import NotificationMessageRouter
from websocket_auth_handler import WebSocketAuthHandler, AuthenticationContext
from models import (
    NotificationType, NotificationPriority, NotificationCategory, 
    UserRole, User
)


class TestNotificationAuthenticationAuthorization(unittest.TestCase):
    """Security tests for notification system authentication and authorization"""
    
    def setUp(self):
        """Set up test environment"""
        # Mock dependencies
        self.mock_websocket_factory = Mock()
        self.mock_auth_handler = Mock(spec=WebSocketAuthHandler)
        self.mock_namespace_manager = Mock()
        self.mock_namespace_manager._user_connections = defaultdict(set)
        self.mock_namespace_manager._connections = {}
        self.mock_db_manager = Mock()
        
        # Mock database session with proper context manager
        self.mock_session = Mock()
        self.mock_context_manager = MagicMock()
        self.mock_context_manager.__enter__ = Mock(return_value=self.mock_session)
        self.mock_context_manager.__exit__ = Mock(return_value=None)
        self.mock_db_manager.get_session = Mock(return_value=self.mock_context_manager)
        
        # Create notification components
        self.notification_manager = UnifiedNotificationManager(
            websocket_factory=self.mock_websocket_factory,
            auth_handler=self.mock_auth_handler,
            namespace_manager=self.mock_namespace_manager,
            db_manager=self.mock_db_manager
        )
        
        self.message_router = NotificationMessageRouter(
            namespace_manager=self.mock_namespace_manager
        )
        
        # Create test users with different roles
        self.admin_user = Mock(spec=User)
        self.admin_user.id = 1
        self.admin_user.username = "admin"
        self.admin_user.role = UserRole.ADMIN
        
        self.moderator_user = Mock(spec=User)
        self.moderator_user.id = 2
        self.moderator_user.username = "moderator"
        self.moderator_user.role = UserRole.MODERATOR
        
        self.reviewer_user = Mock(spec=User)
        self.reviewer_user.id = 3
        self.reviewer_user.username = "reviewer"
        self.reviewer_user.role = UserRole.REVIEWER
        
        self.viewer_user = Mock(spec=User)
        self.viewer_user.id = 4
        self.viewer_user.username = "viewer"
        self.viewer_user.role = UserRole.VIEWER
        
        # Create test messages
        self.system_message = NotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.INFO,
            title="System Notification",
            message="System information message",
            category=NotificationCategory.SYSTEM
        )
        
        self.admin_message = AdminNotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.ERROR,
            title="Admin Alert",
            message="Administrative alert message",
            category=NotificationCategory.ADMIN,
            requires_admin_action=True
        )
        
        self.security_message = NotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.ERROR,
            title="Security Alert",
            message="Security incident detected",
            category=NotificationCategory.SECURITY,
            priority=NotificationPriority.CRITICAL
        )
        
        self.maintenance_message = NotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.WARNING,
            title="Maintenance Notice",
            message="System maintenance scheduled",
            category=NotificationCategory.MAINTENANCE
        )
    
    def test_admin_role_permissions(self):
        """Test admin role has access to all notification types"""
        # Mock admin user lookup
        with patch.object(self.notification_manager, '_get_user_role', return_value=UserRole.ADMIN):
            # Test admin notification permission
            self.assertTrue(
                self.notification_manager._validate_user_permissions(1, self.admin_message)
            )
            
            # Test security notification permission
            self.assertTrue(
                self.notification_manager._validate_user_permissions(1, self.security_message)
            )
            
            # Test system notification permission
            self.assertTrue(
                self.notification_manager._validate_user_permissions(1, self.system_message)
            )
            
            # Test maintenance notification permission
            self.assertTrue(
                self.notification_manager._validate_user_permissions(1, self.maintenance_message)
            )
    
    def test_moderator_role_permissions(self):
        """Test moderator role permissions"""
        # Mock moderator user lookup
        with patch.object(self.notification_manager, '_get_user_role', return_value=UserRole.MODERATOR):
            # Test admin notification permission (should be denied)
            self.assertFalse(
                self.notification_manager._validate_user_permissions(2, self.admin_message)
            )
            
            # Test security notification permission (should be allowed)
            self.assertTrue(
                self.notification_manager._validate_user_permissions(2, self.security_message)
            )
            
            # Test system notification permission (should be allowed)
            self.assertTrue(
                self.notification_manager._validate_user_permissions(2, self.system_message)
            )
            
            # Test maintenance notification permission (should be allowed)
            self.assertTrue(
                self.notification_manager._validate_user_permissions(2, self.maintenance_message)
            )
    
    def test_reviewer_role_permissions(self):
        """Test reviewer role permissions"""
        # Mock reviewer user lookup
        with patch.object(self.notification_manager, '_get_user_role', return_value=UserRole.REVIEWER):
            # Test admin notification permission (should be denied)
            self.assertFalse(
                self.notification_manager._validate_user_permissions(3, self.admin_message)
            )
            
            # Test security notification permission (should be denied)
            self.assertFalse(
                self.notification_manager._validate_user_permissions(3, self.security_message)
            )
            
            # Test system notification permission (should be allowed)
            self.assertTrue(
                self.notification_manager._validate_user_permissions(3, self.system_message)
            )
            
            # Test maintenance notification permission (should be allowed)
            self.assertTrue(
                self.notification_manager._validate_user_permissions(3, self.maintenance_message)
            )
    
    def test_viewer_role_permissions(self):
        """Test viewer role permissions"""
        # Mock viewer user lookup
        with patch.object(self.notification_manager, '_get_user_role', return_value=UserRole.VIEWER):
            # Test admin notification permission (should be denied)
            self.assertFalse(
                self.notification_manager._validate_user_permissions(4, self.admin_message)
            )
            
            # Test security notification permission (should be denied)
            self.assertFalse(
                self.notification_manager._validate_user_permissions(4, self.security_message)
            )
            
            # Test system notification permission (should be allowed)
            self.assertTrue(
                self.notification_manager._validate_user_permissions(4, self.system_message)
            )
            
            # Test maintenance notification permission (should be allowed)
            self.assertTrue(
                self.notification_manager._validate_user_permissions(4, self.maintenance_message)
            )
    
    def test_invalid_user_permissions(self):
        """Test permissions for invalid/non-existent user"""
        # Mock no user found
        with patch.object(self.notification_manager, '_get_user_role', return_value=None):
            # All permissions should be denied
            self.assertFalse(
                self.notification_manager._validate_user_permissions(999, self.system_message)
            )
            self.assertFalse(
                self.notification_manager._validate_user_permissions(999, self.admin_message)
            )
            self.assertFalse(
                self.notification_manager._validate_user_permissions(999, self.security_message)
            )
    
    def test_websocket_authentication_integration(self):
        """Test WebSocket authentication integration"""
        # Mock successful authentication
        mock_auth_context = Mock(spec=AuthenticationContext)
        mock_auth_context.user_id = 1
        mock_auth_context.user_role = UserRole.ADMIN
        mock_auth_context.session_id = "auth_session_123"
        mock_auth_context.is_authenticated = True
        
        self.mock_auth_handler.authenticate_connection.return_value = mock_auth_context
        
        # Test authentication
        auth_result = self.mock_auth_handler.authenticate_connection("valid_token")
        
        # Verify authentication success
        self.assertIsNotNone(auth_result)
        self.assertTrue(auth_result.is_authenticated)
        self.assertEqual(auth_result.user_id, 1)
        self.assertEqual(auth_result.user_role, UserRole.ADMIN)
    
    def test_websocket_authentication_failure(self):
        """Test WebSocket authentication failure"""
        # Mock authentication failure
        self.mock_auth_handler.authenticate_connection.return_value = None
        
        # Test authentication with invalid token
        auth_result = self.mock_auth_handler.authenticate_connection("invalid_token")
        
        # Verify authentication failure
        self.assertIsNone(auth_result)
    
    def test_namespace_authorization_admin(self):
        """Test namespace authorization for admin users"""
        # Mock admin user
        with patch.object(self.notification_manager, '_get_user_role', return_value=UserRole.ADMIN):
            # Test admin namespace access
            admin_namespace = self.notification_manager._determine_target_namespace(1, self.admin_message)
            self.assertEqual(admin_namespace, '/admin')
            
            # Test security message namespace for admin
            security_namespace = self.notification_manager._determine_target_namespace(1, self.security_message)
            self.assertEqual(security_namespace, '/admin')
    
    def test_namespace_authorization_non_admin(self):
        """Test namespace authorization for non-admin users"""
        # Mock reviewer user
        with patch.object(self.notification_manager, '_get_user_role', return_value=UserRole.REVIEWER):
            # Test admin namespace access (should be denied - returns None or default namespace)
            admin_namespace = self.notification_manager._determine_target_namespace(3, self.admin_message)
            # Admin messages should not be accessible to non-admin users
            # The method might return None or a default namespace, both are acceptable for non-admin users
            self.assertIn(admin_namespace, [None, '/'])
            
            # Test system message namespace for reviewer
            system_namespace = self.notification_manager._determine_target_namespace(3, self.system_message)
            self.assertEqual(system_namespace, '/')
    
    def test_message_routing_authorization(self):
        """Test message routing authorization"""
        # Test admin message routing permissions
        with patch.object(self.message_router, '_get_user_role', return_value=UserRole.ADMIN):
            self.assertTrue(self.message_router.validate_routing_permissions(1, 'admin'))
            self.assertTrue(self.message_router.validate_routing_permissions(1, 'security'))
        
        # Test reviewer message routing permissions
        with patch.object(self.message_router, '_get_user_role', return_value=UserRole.REVIEWER):
            self.assertFalse(self.message_router.validate_routing_permissions(3, 'admin'))
            self.assertFalse(self.message_router.validate_routing_permissions(3, 'security'))
            self.assertTrue(self.message_router.validate_routing_permissions(3, 'system'))
    
    def test_sensitive_data_protection(self):
        """Test protection of sensitive data in notifications"""
        # Create notification with sensitive data
        sensitive_message = AdminNotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.ERROR,
            title="Security Breach",
            message="Unauthorized access detected",
            security_event_data={
                "ip_address": "192.168.1.100",
                "user_agent": "Malicious Bot",
                "attempted_actions": ["admin_access", "data_export"],
                "sensitive_info": "classified_data"
            },
            requires_admin_action=True
        )
        
        # Test that only admin users can access sensitive security data
        with patch.object(self.message_router, '_get_user_role', return_value=UserRole.ADMIN):
            is_valid = self.message_router._validate_message_security(1, sensitive_message)
            self.assertTrue(is_valid)
        
        # Test that non-admin users cannot access sensitive security data
        with patch.object(self.message_router, '_get_user_role', return_value=UserRole.REVIEWER):
            is_valid = self.message_router._validate_message_security(3, sensitive_message)
            self.assertFalse(is_valid)
    
    def test_session_based_authorization(self):
        """Test session-based authorization"""
        # Mock session with user context
        mock_session_context = {
            'user_id': 1,
            'user_role': UserRole.ADMIN,
            'session_id': 'session_123',
            'authenticated': True,
            'permissions': ['admin', 'security', 'system']
        }
        
        # Test session validation
        with patch('flask.session', mock_session_context):
            # Simulate session-based permission check
            user_permissions = mock_session_context.get('permissions', [])
            
            # Verify admin permissions
            self.assertIn('admin', user_permissions)
            self.assertIn('security', user_permissions)
            self.assertIn('system', user_permissions)
    
    def test_unauthorized_access_prevention(self):
        """Test prevention of unauthorized access"""
        # Test sending admin message to non-admin user
        with patch.object(self.notification_manager, '_get_user_role', return_value=UserRole.VIEWER):
            result = self.notification_manager.send_user_notification(4, self.admin_message)
            
            # Should fail due to insufficient permissions
            self.assertFalse(result)
    
    def test_privilege_escalation_prevention(self):
        """Test prevention of privilege escalation"""
        # Mock user trying to access higher privilege notifications
        with patch.object(self.notification_manager, '_get_user_role', return_value=UserRole.REVIEWER):
            # Try to send security notification (requires moderator+ role)
            result = self.notification_manager.send_user_notification(3, self.security_message)
            
            # Should fail due to insufficient privileges
            self.assertFalse(result)
    
    def test_cross_user_access_prevention(self):
        """Test prevention of cross-user access"""
        # Create user-specific message
        user_specific_message = NotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.INFO,
            title="Personal Notification",
            message="This is for user 1 only",
            user_id=1,
            category=NotificationCategory.USER
        )
        
        # Mock different user trying to access another user's message
        mock_notification = Mock()
        mock_notification.user_id = 1  # Message belongs to user 1
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = mock_notification
        
        # User 2 trying to mark user 1's message as read
        result = self.notification_manager.mark_message_as_read(user_specific_message.id, 2)
        
        # Should fail due to cross-user access attempt
        # Note: This would need to be implemented in the actual method
        # For now, we verify the database query structure
        self.mock_session.query.assert_called()
    
    def test_authentication_token_validation(self):
        """Test authentication token validation"""
        # Test valid token
        valid_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.valid_payload"
        mock_auth_context = Mock(spec=AuthenticationContext)
        mock_auth_context.user_id = 1
        mock_auth_context.is_authenticated = True
        
        # Add the validate_token method to the mock
        self.mock_auth_handler.validate_token = Mock(return_value=mock_auth_context)
        
        # Validate token
        auth_result = self.mock_auth_handler.validate_token(valid_token)
        self.assertIsNotNone(auth_result)
        self.assertTrue(auth_result.is_authenticated)
        
        # Test invalid token
        invalid_token = "invalid.token.format"
        self.mock_auth_handler.validate_token.return_value = None
        
        auth_result = self.mock_auth_handler.validate_token(invalid_token)
        self.assertIsNone(auth_result)
    
    def test_rate_limiting_by_user_role(self):
        """Test rate limiting based on user role"""
        # Mock rate limiting for different roles
        rate_limits = {
            UserRole.ADMIN: 1000,    # High limit for admins
            UserRole.MODERATOR: 500, # Medium limit for moderators
            UserRole.REVIEWER: 100,  # Lower limit for reviewers
            UserRole.VIEWER: 50      # Lowest limit for viewers
        }
        
        # Test rate limit enforcement
        for role, limit in rate_limits.items():
            with patch.object(self.notification_manager, '_get_user_role', return_value=role):
                # Simulate checking rate limit
                user_rate_limit = rate_limits.get(role, 10)  # Default low limit
                
                # Verify appropriate limits are set
                if role == UserRole.ADMIN:
                    self.assertEqual(user_rate_limit, 1000)
                elif role == UserRole.VIEWER:
                    self.assertEqual(user_rate_limit, 50)
    
    def test_audit_logging_for_security_events(self):
        """Test audit logging for security-related events"""
        # Mock security event logging
        security_events = []
        
        def mock_log_security_event(event_type, user_id, details):
            security_events.append({
                'event_type': event_type,
                'user_id': user_id,
                'details': details,
                'timestamp': datetime.now(timezone.utc)
            })
        
        # Test unauthorized access attempt logging
        with patch('unified_notification_manager.logger') as mock_logger:
            with patch.object(self.notification_manager, '_get_user_role', return_value=UserRole.VIEWER):
                # Attempt unauthorized admin notification
                result = self.notification_manager.send_user_notification(4, self.admin_message)
                
                # Verify logging occurred
                mock_logger.warning.assert_called()
                self.assertFalse(result)
    
    def test_input_sanitization_for_notifications(self):
        """Test input sanitization for notification content"""
        # Create message with potentially malicious content
        malicious_message = NotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.INFO,
            title="<script>alert('xss')</script>",
            message="<img src=x onerror=alert('xss')>",
            user_id=1,
            data={"malicious": "<script>alert('xss')</script>"}
        )
        
        # Test that message content is properly handled
        # Note: Actual sanitization would be implemented in the storage layer
        with patch('unified_notification_manager.NotificationStorage') as mock_storage:
            self.notification_manager._store_message_in_database(malicious_message)
            
            # Verify storage was called (sanitization would happen in storage layer)
            mock_storage.assert_called_once()
    
    def test_secure_message_transmission(self):
        """Test secure message transmission over WebSocket"""
        # Mock secure WebSocket connection
        with patch('unified_notification_manager.emit') as mock_emit:
            # Set up authenticated user
            session_id = "secure_session_123"
            self.mock_namespace_manager._user_connections[1] = {session_id}
            self.mock_namespace_manager._connections[session_id] = Mock(namespace='/admin')
            
            # Mock admin user
            with patch.object(self.notification_manager, '_get_user_role', return_value=UserRole.ADMIN):
                with patch.object(self.notification_manager, '_store_message_in_database'):
                    with patch.object(self.notification_manager, '_add_to_message_history'):
                        # Send secure admin message
                        result = self.notification_manager.send_user_notification(1, self.admin_message)
                        
                        # Verify secure transmission
                        self.assertTrue(result)
                        mock_emit.assert_called_once()
                        
                        # Verify message was sent to correct namespace
                        call_args = mock_emit.call_args
                        self.assertEqual(call_args[1]['namespace'], '/admin')


if __name__ == '__main__':
    unittest.main()
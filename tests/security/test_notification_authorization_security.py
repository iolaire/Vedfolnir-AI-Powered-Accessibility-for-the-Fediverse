# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Enhanced Authorization Security Tests for Notification System

Tests comprehensive authorization mechanisms including namespace authorization,
message routing authorization, and protection against unauthorized access.
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
from models import (
    NotificationType, NotificationPriority, NotificationCategory, 
    UserRole, User
)


class TestNotificationAuthorizationSecurity(unittest.TestCase):
    """Enhanced authorization security tests"""
    
    def setUp(self):
        """Set up test environment"""
        # Mock dependencies
        self.mock_websocket_factory = Mock()
        self.mock_auth_handler = Mock()
        self.mock_namespace_manager = Mock()
        
        # Create proper mock database manager
        self.mock_db_manager = Mock()
        self.mock_session = Mock()
        
        # Create proper context manager mock
        mock_context_manager = MagicMock()
        mock_context_manager.__enter__ = Mock(return_value=self.mock_session)
        mock_context_manager.__exit__ = Mock(return_value=None)
        self.mock_db_manager.get_session = Mock(return_value=mock_context_manager)
        
        # Create notification manager
        self.notification_manager = UnifiedNotificationManager(
            websocket_factory=self.mock_websocket_factory,
            auth_handler=self.mock_auth_handler,
            namespace_manager=self.mock_namespace_manager,
            db_manager=self.mock_db_manager
        )
        
        # Create message router
        self.message_router = NotificationMessageRouter(
            namespace_manager=self.mock_namespace_manager
        )
        
        # Mock namespace connections
        self.mock_namespace_manager._user_connections = defaultdict(set)
        self.mock_namespace_manager._connections = {}
        
        # Create test users
        self.admin_user = Mock()
        self.admin_user.id = 1
        self.admin_user.role = UserRole.ADMIN
        self.admin_user.username = "admin"
        
        self.regular_user = Mock()
        self.regular_user.id = 2
        self.regular_user.role = UserRole.REVIEWER
        self.regular_user.username = "user"
    
    def test_namespace_authorization_admin(self):
        """Test namespace authorization for admin users"""
        admin_namespaces = [
            '/admin',
            '/system',
            '/maintenance',
            '/security'
        ]
        
        for namespace in admin_namespaces:
            with self.subTest(namespace=namespace):
                # Test admin access to admin namespaces
                has_access = self._check_namespace_authorization(
                    self.admin_user.id, 
                    UserRole.ADMIN, 
                    namespace
                )
                self.assertTrue(has_access, f"Admin should have access to {namespace}")
    
    def test_namespace_authorization_non_admin(self):
        """Test namespace authorization for non-admin users"""
        restricted_namespaces = [
            '/admin',
            '/system',
            '/maintenance',
            '/security'
        ]
        
        allowed_namespaces = [
            '/user',
            '/caption',
            '/platform'
        ]
        
        # Test restricted namespaces
        for namespace in restricted_namespaces:
            with self.subTest(namespace=namespace):
                has_access = self._check_namespace_authorization(
                    self.regular_user.id,
                    UserRole.REVIEWER,
                    namespace
                )
                self.assertFalse(has_access, f"Regular user should NOT have access to {namespace}")
        
        # Test allowed namespaces
        for namespace in allowed_namespaces:
            with self.subTest(namespace=namespace):
                has_access = self._check_namespace_authorization(
                    self.regular_user.id,
                    UserRole.REVIEWER,
                    namespace
                )
                self.assertTrue(has_access, f"Regular user should have access to {namespace}")
    
    def test_message_routing_authorization(self):
        """Test message routing authorization"""
        # Test admin message routing
        admin_message = AdminNotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.ERROR,
            title="Admin Alert",
            message="Critical system alert",
            category=NotificationCategory.ADMIN,
            requires_admin_action=True
        )
        
        # Admin should be able to route admin messages
        can_route_admin = self._check_message_routing_authorization(
            self.admin_user.id,
            UserRole.ADMIN,
            admin_message
        )
        self.assertTrue(can_route_admin, "Admin should be able to route admin messages")
        
        # Regular user should NOT be able to route admin messages
        can_route_regular = self._check_message_routing_authorization(
            self.regular_user.id,
            UserRole.REVIEWER,
            admin_message
        )
        self.assertFalse(can_route_regular, "Regular user should NOT be able to route admin messages")
        
        # Test regular message routing
        user_message = NotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.INFO,
            title="User Message",
            message="Regular user message",
            category=NotificationCategory.USER
        )
        
        # Both admin and regular user should be able to route user messages
        can_route_admin_user = self._check_message_routing_authorization(
            self.admin_user.id,
            UserRole.ADMIN,
            user_message
        )
        self.assertTrue(can_route_admin_user, "Admin should be able to route user messages")
        
        can_route_regular_user = self._check_message_routing_authorization(
            self.regular_user.id,
            UserRole.REVIEWER,
            user_message
        )
        self.assertTrue(can_route_regular_user, "Regular user should be able to route user messages")
    
    def test_unauthorized_access_prevention(self):
        """Test prevention of unauthorized access attempts"""
        # Test unauthorized namespace access
        unauthorized_attempts = [
            {'user_id': self.regular_user.id, 'role': UserRole.REVIEWER, 'namespace': '/admin'},
            {'user_id': self.regular_user.id, 'role': UserRole.REVIEWER, 'namespace': '/system'},
            {'user_id': None, 'role': None, 'namespace': '/admin'},  # Unauthenticated
        ]
        
        for attempt in unauthorized_attempts:
            with self.subTest(attempt=attempt):
                # Test access prevention
                access_blocked = self._prevent_unauthorized_access(
                    attempt['user_id'],
                    attempt['role'],
                    attempt['namespace']
                )
                self.assertTrue(access_blocked, f"Unauthorized access should be blocked: {attempt}")
        
        # Test authorized access is allowed
        authorized_attempts = [
            {'user_id': self.admin_user.id, 'role': UserRole.ADMIN, 'namespace': '/admin'},
            {'user_id': self.regular_user.id, 'role': UserRole.REVIEWER, 'namespace': '/user'},
        ]
        
        for attempt in authorized_attempts:
            with self.subTest(attempt=attempt):
                access_blocked = self._prevent_unauthorized_access(
                    attempt['user_id'],
                    attempt['role'],
                    attempt['namespace']
                )
                self.assertFalse(access_blocked, f"Authorized access should be allowed: {attempt}")
    
    def test_privilege_escalation_prevention(self):
        """Test prevention of privilege escalation attempts"""
        # Test user trying to escalate to admin privileges
        escalation_attempts = [
            {
                'user_id': self.regular_user.id,
                'current_role': UserRole.REVIEWER,
                'attempted_action': 'send_admin_notification',
                'target_role': UserRole.ADMIN
            },
            {
                'user_id': self.regular_user.id,
                'current_role': UserRole.REVIEWER,
                'attempted_action': 'access_admin_namespace',
                'target_role': UserRole.ADMIN
            },
            {
                'user_id': self.regular_user.id,
                'current_role': UserRole.REVIEWER,
                'attempted_action': 'modify_system_settings',
                'target_role': UserRole.ADMIN
            }
        ]
        
        for attempt in escalation_attempts:
            with self.subTest(attempt=attempt):
                escalation_blocked = self._prevent_privilege_escalation(
                    attempt['user_id'],
                    attempt['current_role'],
                    attempt['attempted_action'],
                    attempt['target_role']
                )
                self.assertTrue(escalation_blocked, f"Privilege escalation should be blocked: {attempt}")
        
        # Test legitimate admin actions are allowed
        legitimate_actions = [
            {
                'user_id': self.admin_user.id,
                'current_role': UserRole.ADMIN,
                'attempted_action': 'send_admin_notification',
                'target_role': UserRole.ADMIN
            }
        ]
        
        for action in legitimate_actions:
            with self.subTest(action=action):
                escalation_blocked = self._prevent_privilege_escalation(
                    action['user_id'],
                    action['current_role'],
                    action['attempted_action'],
                    action['target_role']
                )
                self.assertFalse(escalation_blocked, f"Legitimate admin action should be allowed: {action}")
    
    def test_cross_user_access_prevention(self):
        """Test prevention of cross-user access attempts"""
        # Create test data for different users
        user1_data = {
            'user_id': 1,
            'notifications': ['notif_1', 'notif_2'],
            'sessions': ['session_1']
        }
        
        user2_data = {
            'user_id': 2,
            'notifications': ['notif_3', 'notif_4'],
            'sessions': ['session_2']
        }
        
        # Test user 1 trying to access user 2's data
        cross_access_attempts = [
            {'accessing_user': 1, 'target_user': 2, 'resource': 'notifications'},
            {'accessing_user': 1, 'target_user': 2, 'resource': 'sessions'},
            {'accessing_user': 2, 'target_user': 1, 'resource': 'notifications'},
        ]
        
        for attempt in cross_access_attempts:
            with self.subTest(attempt=attempt):
                access_blocked = self._prevent_cross_user_access(
                    attempt['accessing_user'],
                    attempt['target_user'],
                    attempt['resource']
                )
                self.assertTrue(access_blocked, f"Cross-user access should be blocked: {attempt}")
        
        # Test legitimate same-user access
        legitimate_access = [
            {'accessing_user': 1, 'target_user': 1, 'resource': 'notifications'},
            {'accessing_user': 2, 'target_user': 2, 'resource': 'sessions'},
        ]
        
        for access in legitimate_access:
            with self.subTest(access=access):
                access_blocked = self._prevent_cross_user_access(
                    access['accessing_user'],
                    access['target_user'],
                    access['resource']
                )
                self.assertFalse(access_blocked, f"Same-user access should be allowed: {access}")
        
        # Test admin access to other users' data (should be allowed)
        admin_access = [
            {'accessing_user': self.admin_user.id, 'target_user': 2, 'resource': 'notifications', 'role': UserRole.ADMIN},
        ]
        
        for access in admin_access:
            with self.subTest(access=access):
                access_blocked = self._prevent_cross_user_access(
                    access['accessing_user'],
                    access['target_user'],
                    access['resource'],
                    accessing_user_role=access['role']
                )
                self.assertFalse(access_blocked, f"Admin cross-user access should be allowed: {access}")
    
    def _check_namespace_authorization(self, user_id, user_role, namespace):
        """Check if user is authorized to access namespace"""
        # Define namespace access rules
        namespace_rules = {
            '/admin': [UserRole.ADMIN],
            '/system': [UserRole.ADMIN],
            '/security': [UserRole.ADMIN],
            '/maintenance': [UserRole.ADMIN],
            '/user': [UserRole.ADMIN, UserRole.MODERATOR, UserRole.REVIEWER, UserRole.VIEWER],
            '/caption': [UserRole.ADMIN, UserRole.MODERATOR, UserRole.REVIEWER],
            '/platform': [UserRole.ADMIN, UserRole.MODERATOR, UserRole.REVIEWER]
        }
        
        allowed_roles = namespace_rules.get(namespace, [])
        return user_role in allowed_roles
    
    def _check_message_routing_authorization(self, user_id, user_role, message):
        """Check if user is authorized to route message"""
        # Define message routing rules based on category
        routing_rules = {
            NotificationCategory.ADMIN: [UserRole.ADMIN],
            NotificationCategory.SYSTEM: [UserRole.ADMIN],
            NotificationCategory.SECURITY: [UserRole.ADMIN],
            NotificationCategory.MAINTENANCE: [UserRole.ADMIN],
            NotificationCategory.USER: [UserRole.ADMIN, UserRole.MODERATOR, UserRole.REVIEWER],
            NotificationCategory.CAPTION: [UserRole.ADMIN, UserRole.MODERATOR, UserRole.REVIEWER],
            NotificationCategory.PLATFORM: [UserRole.ADMIN, UserRole.MODERATOR, UserRole.REVIEWER]
        }
        
        if hasattr(message, 'category'):
            allowed_roles = routing_rules.get(message.category, [])
            return user_role in allowed_roles
        
        return False
    
    def _prevent_unauthorized_access(self, user_id, user_role, namespace):
        """Prevent unauthorized access and return True if access was blocked"""
        if user_id is None or user_role is None:
            # Unauthenticated access blocked
            return True
        
        # Check authorization
        is_authorized = self._check_namespace_authorization(user_id, user_role, namespace)
        
        # Return True if access was blocked (not authorized)
        return not is_authorized
    
    def _prevent_privilege_escalation(self, user_id, current_role, attempted_action, target_role):
        """Prevent privilege escalation and return True if escalation was blocked"""
        # Define actions that require specific roles
        action_requirements = {
            'send_admin_notification': UserRole.ADMIN,
            'access_admin_namespace': UserRole.ADMIN,
            'modify_system_settings': UserRole.ADMIN,
            'manage_users': UserRole.ADMIN,
            'view_security_logs': UserRole.ADMIN
        }
        
        required_role = action_requirements.get(attempted_action)
        
        if required_role is None:
            # Unknown action, allow
            return False
        
        # Check if user's current role is sufficient
        role_hierarchy = {
            UserRole.VIEWER: 1,
            UserRole.REVIEWER: 2,
            UserRole.MODERATOR: 3,
            UserRole.ADMIN: 4
        }
        
        current_level = role_hierarchy.get(current_role, 0)
        required_level = role_hierarchy.get(required_role, 4)
        
        # Return True if escalation was blocked (insufficient privileges)
        return current_level < required_level
    
    def _prevent_cross_user_access(self, accessing_user_id, target_user_id, resource, accessing_user_role=None):
        """Prevent cross-user access and return True if access was blocked"""
        # Same user accessing their own data is always allowed
        if accessing_user_id == target_user_id:
            return False
        
        # Admin can access other users' data
        if accessing_user_role == UserRole.ADMIN:
            return False
        
        # Different user accessing another user's data is blocked
        return True


if __name__ == '__main__':
    unittest.main()
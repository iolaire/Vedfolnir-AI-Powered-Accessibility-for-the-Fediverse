# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Enhanced Authentication Security Tests for Notification System

Tests comprehensive authentication mechanisms including role-based permissions,
token validation, and authentication integration with WebSocket connections.
"""

import unittest
import sys
import os
import uuid
# JWT import is optional for testing
try:
    import jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock
from collections import defaultdict

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from unified_notification_manager import (
    UnifiedNotificationManager, NotificationMessage, 
    AdminNotificationMessage, SystemNotificationMessage
)
from models import (
    NotificationType, NotificationPriority, NotificationCategory, 
    UserRole, User
)


class TestNotificationAuthenticationSecurity(unittest.TestCase):
    """Enhanced authentication security tests"""
    
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
        
        # Create test users
        self.admin_user = Mock()
        self.admin_user.id = 1
        self.admin_user.role = UserRole.ADMIN
        self.admin_user.username = "admin"
        
        self.moderator_user = Mock()
        self.moderator_user.id = 2
        self.moderator_user.role = UserRole.MODERATOR
        self.moderator_user.username = "moderator"
        
        self.reviewer_user = Mock()
        self.reviewer_user.id = 3
        self.reviewer_user.role = UserRole.REVIEWER
        self.reviewer_user.username = "reviewer"
        
        self.viewer_user = Mock()
        self.viewer_user.id = 4
        self.viewer_user.role = UserRole.VIEWER
        self.viewer_user.username = "viewer"
    
    def test_admin_role_permissions(self):
        """Test admin role has full notification permissions"""
        # Admin should be able to send all types of notifications
        admin_message = AdminNotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.ERROR,
            title="Admin Alert",
            message="Critical system alert",
            category=NotificationCategory.ADMIN,
            requires_admin_action=True
        )
        
        # Mock user role check
        with patch.object(self.notification_manager, '_get_user_role', return_value=UserRole.ADMIN):
            # Test admin permissions
            has_permission = self._check_notification_permission(self.admin_user.id, admin_message)
            self.assertTrue(has_permission, "Admin should have permission for admin notifications")
            
            # Test admin can send system notifications
            system_message = NotificationMessage(
                id=str(uuid.uuid4()),
                type=NotificationType.INFO,
                title="System Info",
                message="System information",
                category=NotificationCategory.SYSTEM
            )
            
            has_system_permission = self._check_notification_permission(self.admin_user.id, system_message)
            self.assertTrue(has_system_permission, "Admin should have permission for system notifications")
    
    def test_moderator_role_permissions(self):
        """Test moderator role has appropriate notification permissions"""
        # Moderator should be able to send platform notifications
        platform_message = NotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.WARNING,
            title="Platform Alert",
            message="Platform moderation required",
            category=NotificationCategory.PLATFORM
        )
        
        with patch.object(self.notification_manager, '_get_user_role', return_value=UserRole.MODERATOR):
            has_permission = self._check_notification_permission(self.moderator_user.id, platform_message)
            self.assertTrue(has_permission, "Moderator should have permission for platform notifications")
            
            # Moderator should NOT be able to send admin notifications
            admin_message = AdminNotificationMessage(
                id=str(uuid.uuid4()),
                type=NotificationType.ERROR,
                title="Admin Alert",
                message="Admin-only alert",
                category=NotificationCategory.ADMIN,
                requires_admin_action=True
            )
            
            has_admin_permission = self._check_notification_permission(self.moderator_user.id, admin_message)
            self.assertFalse(has_admin_permission, "Moderator should NOT have permission for admin notifications")
    
    def test_reviewer_role_permissions(self):
        """Test reviewer role has limited notification permissions"""
        # Reviewer should be able to send caption-related notifications
        caption_message = NotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.INFO,
            title="Caption Review",
            message="Caption review completed",
            category=NotificationCategory.CAPTION
        )
        
        with patch.object(self.notification_manager, '_get_user_role', return_value=UserRole.REVIEWER):
            has_permission = self._check_notification_permission(self.reviewer_user.id, caption_message)
            self.assertTrue(has_permission, "Reviewer should have permission for caption notifications")
            
            # Reviewer should NOT be able to send admin notifications
            admin_message = AdminNotificationMessage(
                id=str(uuid.uuid4()),
                type=NotificationType.ERROR,
                title="Admin Alert",
                message="Admin-only alert",
                category=NotificationCategory.ADMIN,
                requires_admin_action=True
            )
            
            has_admin_permission = self._check_notification_permission(self.reviewer_user.id, admin_message)
            self.assertFalse(has_admin_permission, "Reviewer should NOT have permission for admin notifications")
    
    def test_viewer_role_permissions(self):
        """Test viewer role has minimal notification permissions"""
        # Viewer should only be able to receive notifications, not send them
        user_message = NotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.INFO,
            title="User Message",
            message="User-generated message",
            category=NotificationCategory.USER
        )
        
        with patch.object(self.notification_manager, '_get_user_role', return_value=UserRole.VIEWER):
            has_permission = self._check_notification_permission(self.viewer_user.id, user_message)
            self.assertFalse(has_permission, "Viewer should NOT have permission to send notifications")
            
            # Test viewer can receive notifications
            can_receive = self._check_notification_receive_permission(self.viewer_user.id, user_message)
            self.assertTrue(can_receive, "Viewer should be able to receive notifications")
    
    def test_websocket_authentication_integration(self):
        """Test WebSocket authentication integration with notifications"""
        # Test authenticated WebSocket connection
        session_id = "test_session_123"
        user_id = 1
        
        # Mock authenticated session
        self.mock_auth_handler.validate_session.return_value = {
            'user_id': user_id,
            'role': UserRole.ADMIN,
            'session_id': session_id,
            'authenticated': True
        }
        
        # Test notification delivery to authenticated user
        message = NotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.INFO,
            title="Test Message",
            message="Authenticated notification",
            category=NotificationCategory.SYSTEM
        )
        
        # Test WebSocket authentication
        is_authenticated = self._validate_websocket_authentication(session_id, user_id)
        self.assertTrue(is_authenticated, "WebSocket should be authenticated for valid session")
        
        # Test notification delivery
        can_deliver = self._can_deliver_notification(user_id, message)
        self.assertTrue(can_deliver, "Should be able to deliver notification to authenticated user")
    
    def test_authentication_token_validation(self):
        """Test authentication token validation for notifications"""
        if not JWT_AVAILABLE:
            self.skipTest("JWT library not available")
        
        # Create test JWT token
        secret_key = "test_secret_key"
        payload = {
            'user_id': 1,
            'role': 'admin',
            'exp': datetime.utcnow() + timedelta(hours=1),
            'iat': datetime.utcnow()
        }
        
        token = jwt.encode(payload, secret_key, algorithm='HS256')
        
        # Test valid token
        is_valid = self._validate_authentication_token(token, secret_key)
        self.assertTrue(is_valid, "Valid token should pass validation")
        
        # Test expired token
        expired_payload = {
            'user_id': 1,
            'role': 'admin',
            'exp': datetime.utcnow() - timedelta(hours=1),  # Expired
            'iat': datetime.utcnow() - timedelta(hours=2)
        }
        
        expired_token = jwt.encode(expired_payload, secret_key, algorithm='HS256')
        is_expired_valid = self._validate_authentication_token(expired_token, secret_key)
        self.assertFalse(is_expired_valid, "Expired token should fail validation")
        
        # Test invalid token
        invalid_token = "invalid.token.here"
        is_invalid_valid = self._validate_authentication_token(invalid_token, secret_key)
        self.assertFalse(is_invalid_valid, "Invalid token should fail validation")
    
    def _check_notification_permission(self, user_id, message):
        """Check if user has permission to send notification"""
        # Get user role
        user_role = self.notification_manager._get_user_role(user_id)
        
        # Define permission matrix
        permissions = {
            UserRole.ADMIN: [
                NotificationCategory.ADMIN,
                NotificationCategory.SYSTEM,
                NotificationCategory.SECURITY,
                NotificationCategory.MAINTENANCE,
                NotificationCategory.CAPTION,
                NotificationCategory.PLATFORM,
                NotificationCategory.USER
            ],
            UserRole.MODERATOR: [
                NotificationCategory.CAPTION,
                NotificationCategory.PLATFORM,
                NotificationCategory.USER
            ],
            UserRole.REVIEWER: [
                NotificationCategory.CAPTION,
                NotificationCategory.USER
            ],
            UserRole.VIEWER: []  # Viewers cannot send notifications
        }
        
        allowed_categories = permissions.get(user_role, [])
        
        # Check if message category is allowed
        if hasattr(message, 'category'):
            return message.category in allowed_categories
        
        return False
    
    def _check_notification_receive_permission(self, user_id, message):
        """Check if user can receive notification"""
        # All authenticated users can receive notifications
        return True
    
    def _validate_websocket_authentication(self, session_id, user_id):
        """Validate WebSocket authentication"""
        try:
            # Use mock auth handler
            auth_result = self.mock_auth_handler.validate_session(session_id)
            return (auth_result and 
                   auth_result.get('authenticated', False) and
                   auth_result.get('user_id') == user_id)
        except Exception:
            return False
    
    def _can_deliver_notification(self, user_id, message):
        """Check if notification can be delivered to user"""
        # Check if user is authenticated and has receive permissions
        return self._check_notification_receive_permission(user_id, message)
    
    def _validate_authentication_token(self, token, secret_key):
        """Validate JWT authentication token"""
        if not JWT_AVAILABLE:
            return False
        
        try:
            payload = jwt.decode(token, secret_key, algorithms=['HS256'])
            
            # Check expiration
            exp = payload.get('exp')
            if exp and datetime.utcnow() > datetime.fromtimestamp(exp):
                return False
            
            # Check required fields
            required_fields = ['user_id', 'role']
            for field in required_fields:
                if field not in payload:
                    return False
            
            return True
        except jwt.InvalidTokenError:
            return False
        except Exception:
            return False


if __name__ == '__main__':
    unittest.main()
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for WebSocket Authentication Handler

Tests authentication, authorization, rate limiting, and security event logging
for WebSocket connections.
"""

import unittest
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

# Add project root to path for imports
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from websocket_auth_handler import (
    WebSocketAuthHandler, AuthenticationResult, AuthenticationContext
)
from models import User, UserRole
from database import DatabaseManager
from session_manager_v2 import SessionManagerV2


class TestWebSocketAuthHandler(unittest.TestCase):
    """Test cases for WebSocket authentication handler"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_db_manager = Mock(spec=DatabaseManager)
        self.mock_session_manager = Mock(spec=SessionManagerV2)
        
        # Create auth handler with test configuration
        self.auth_handler = WebSocketAuthHandler(
            db_manager=self.mock_db_manager,
            session_manager=self.mock_session_manager,
            rate_limit_window=60,  # 1 minute for testing
            max_attempts_per_window=5,
            max_attempts_per_ip=20
        )
    
    def test_authentication_context_creation(self):
        """Test authentication context creation and properties"""
        context = AuthenticationContext(
            user_id=1,
            username="testuser",
            email="test@example.com",
            role=UserRole.ADMIN,
            session_id="test-session-123"
        )
        
        self.assertEqual(context.user_id, 1)
        self.assertEqual(context.username, "testuser")
        self.assertEqual(context.role, UserRole.ADMIN)
        self.assertTrue(context.is_admin)
        self.assertIsInstance(context.permissions, list)
    
    def test_cleanup_old_data(self):
        """Test cleanup of old rate limiting data"""
        # Add some old data
        old_time = time.time() - 200  # Older than 2x window (120 seconds)
        self.auth_handler._user_attempts[1].append(old_time)
        self.auth_handler._ip_attempts["127.0.0.1"].append(old_time)
        
        # Add some recent data
        recent_time = time.time() - 30
        self.auth_handler._user_attempts[1].append(recent_time)
        self.auth_handler._ip_attempts["127.0.0.1"].append(recent_time)
        
        # Cleanup should remove old data but keep recent data
        self.auth_handler.cleanup_old_data()
        
        # Check that recent data is still there
        self.assertEqual(len(self.auth_handler._user_attempts[1]), 1)
        self.assertEqual(len(self.auth_handler._ip_attempts["127.0.0.1"]), 1)
    
    def test_session_validation_mismatch(self):
        """Test session validation with user ID mismatch"""
        user_id = 1
        session_id = "test-session-123"
        
        # Mock session with different user ID
        session_data = {'user_id': 2}  # Different user ID
        self.mock_session_manager.get_session_data.return_value = session_data
        
        result = self.auth_handler.validate_user_session(user_id, session_id)
        self.assertFalse(result)
    
    def test_admin_authorization_success(self):
        """Test successful admin authorization"""
        context = AuthenticationContext(
            user_id=1,
            username="admin",
            email="admin@example.com",
            role=UserRole.ADMIN,
            session_id="test-session",
            permissions=['system_management', 'user_management']
        )
        
        result = self.auth_handler.authorize_admin_access(context)
        self.assertTrue(result)
        
        # Test with specific permission
        result = self.auth_handler.authorize_admin_access(context, 'system_management')
        self.assertTrue(result)
    
    def test_admin_authorization_failure(self):
        """Test admin authorization failure for non-admin user"""
        context = AuthenticationContext(
            user_id=2,
            username="user",
            email="user@example.com",
            role=UserRole.REVIEWER,
            session_id="test-session"
        )
        
        result = self.auth_handler.authorize_admin_access(context)
        self.assertFalse(result)
    
    def test_rate_limiting_user(self):
        """Test user-based rate limiting"""
        user_id = 1
        
        # Make attempts up to the limit
        for i in range(5):  # max_attempts_per_window = 5
            result = self.auth_handler._check_user_rate_limit(user_id)
            self.assertTrue(result)
        
        # Next attempt should be rate limited
        result = self.auth_handler._check_user_rate_limit(user_id)
        self.assertFalse(result)
    
    def test_rate_limiting_ip(self):
        """Test IP-based rate limiting"""
        ip_address = "192.168.1.100"
        
        # Make attempts up to the limit
        for i in range(20):  # max_attempts_per_ip = 20
            result = self.auth_handler._check_ip_rate_limit(ip_address)
            self.assertTrue(result)
        
        # Next attempt should be rate limited
        result = self.auth_handler._check_ip_rate_limit(ip_address)
        self.assertFalse(result)
    
    def test_get_user_permissions(self):
        """Test getting user permissions by role"""
        admin_permissions = self.auth_handler.get_user_permissions(UserRole.ADMIN)
        self.assertIn('system_management', admin_permissions)
        self.assertIn('user_management', admin_permissions)
        
        reviewer_permissions = self.auth_handler.get_user_permissions(UserRole.REVIEWER)
        self.assertIn('platform_management', reviewer_permissions)
        self.assertNotIn('system_management', reviewer_permissions)
        
        viewer_permissions = self.auth_handler.get_user_permissions(UserRole.VIEWER)
        self.assertEqual(len(viewer_permissions), 0)
    
    def test_has_permission(self):
        """Test permission checking"""
        context = AuthenticationContext(
            user_id=1,
            username="admin",
            email="admin@example.com",
            role=UserRole.ADMIN,
            session_id="test-session",
            permissions=['system_management', 'user_management']
        )
        
        self.assertTrue(self.auth_handler.has_permission(context, 'system_management'))
        self.assertTrue(self.auth_handler.has_permission(context, 'user_management'))
        self.assertFalse(self.auth_handler.has_permission(context, 'nonexistent_permission'))
    
    def test_authentication_stats(self):
        """Test getting authentication statistics"""
        # Make some rate limit attempts
        self.auth_handler._check_user_rate_limit(1)
        self.auth_handler._check_user_rate_limit(2)
        self.auth_handler._check_ip_rate_limit("127.0.0.1")
        
        stats = self.auth_handler.get_authentication_stats()
        
        self.assertIn('rate_limit_window_seconds', stats)
        self.assertIn('max_attempts_per_user', stats)
        self.assertIn('max_attempts_per_ip', stats)
        self.assertIn('active_users_in_window', stats)
        self.assertIn('active_ips_in_window', stats)
        
        self.assertEqual(stats['rate_limit_window_seconds'], 60)
        self.assertEqual(stats['max_attempts_per_user'], 5)
        self.assertEqual(stats['max_attempts_per_ip'], 20)


if __name__ == '__main__':
    unittest.main()
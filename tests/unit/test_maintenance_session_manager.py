# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for MaintenanceSessionManager
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.services.maintenance.components.maintenance_session_manager import (
    MaintenanceSessionManager, SessionInfo, SessionInvalidationError
)
from models import User, UserRole


class TestMaintenanceSessionManager(unittest.TestCase):
    """Test cases for MaintenanceSessionManager"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_redis_session_manager = Mock()
        self.mock_db_manager = Mock()
        self.session_manager = MaintenanceSessionManager(
            self.mock_redis_session_manager,
            self.mock_db_manager
        )
        
        # Mock users
        self.admin_user = Mock(spec=User)
        self.admin_user.id = 1
        self.admin_user.username = "admin"
        self.admin_user.role = UserRole.ADMIN
        
        self.regular_user = Mock(spec=User)
        self.regular_user.id = 2
        self.regular_user.username = "user"
        self.regular_user.role = UserRole.REVIEWER
        
        # Mock session info
        self.admin_session_info = SessionInfo(
            session_id="admin-session-123",
            user_id=1,
            username="admin",
            user_role=UserRole.ADMIN.value,
            created_at=datetime.now(timezone.utc),
            last_activity=datetime.now(timezone.utc),
            platform_connection_id=1
        )
        
        self.user_session_info = SessionInfo(
            session_id="user-session-456",
            user_id=2,
            username="user",
            user_role=UserRole.REVIEWER.value,
            created_at=datetime.now(timezone.utc),
            last_activity=datetime.now(timezone.utc),
            platform_connection_id=2
        )
    
    def test_invalidate_non_admin_sessions_success(self):
        """Test successful invalidation of non-admin sessions"""
        # Mock active sessions
        self.session_manager._get_all_active_sessions = Mock(return_value=[
            self.admin_session_info,
            self.user_session_info
        ])
        
        # Mock session destruction
        self.mock_redis_session_manager.destroy_session.return_value = True
        
        result = self.session_manager.invalidate_non_admin_sessions()
        
        # Should return list with user session ID
        self.assertEqual(result, ["user-session-456"])
        
        # Should not destroy admin session
        self.mock_redis_session_manager.destroy_session.assert_called_once_with("user-session-456")
        
        # Check statistics
        stats = self.session_manager.get_session_stats()
        self.assertEqual(stats['statistics']['sessions_invalidated'], 1)
        self.assertEqual(stats['statistics']['admin_sessions_preserved'], 1)
    
    def test_invalidate_non_admin_sessions_no_sessions(self):
        """Test invalidation when no sessions exist"""
        self.session_manager._get_all_active_sessions = Mock(return_value=[])
        
        result = self.session_manager.invalidate_non_admin_sessions()
        
        self.assertEqual(result, [])
        self.mock_redis_session_manager.destroy_session.assert_not_called()
    
    def test_invalidate_non_admin_sessions_only_admin_sessions(self):
        """Test invalidation when only admin sessions exist"""
        self.session_manager._get_all_active_sessions = Mock(return_value=[
            self.admin_session_info
        ])
        
        result = self.session_manager.invalidate_non_admin_sessions()
        
        self.assertEqual(result, [])
        self.mock_redis_session_manager.destroy_session.assert_not_called()
        
        # Check statistics
        stats = self.session_manager.get_session_stats()
        self.assertEqual(stats['statistics']['admin_sessions_preserved'], 1)
    
    def test_invalidate_non_admin_sessions_destruction_failure(self):
        """Test handling of session destruction failures"""
        self.session_manager._get_all_active_sessions = Mock(return_value=[
            self.user_session_info
        ])
        
        # Mock session destruction failure
        self.mock_redis_session_manager.destroy_session.return_value = False
        
        result = self.session_manager.invalidate_non_admin_sessions()
        
        # Should return empty list when destruction fails
        self.assertEqual(result, [])
    
    def test_invalidate_non_admin_sessions_exception(self):
        """Test exception handling during session invalidation"""
        self.session_manager._get_all_active_sessions = Mock(side_effect=Exception("Test error"))
        
        with self.assertRaises(SessionInvalidationError):
            self.session_manager.invalidate_non_admin_sessions()
    
    def test_prevent_non_admin_login(self):
        """Test enabling login prevention"""
        # Mock Redis client
        mock_redis_client = Mock()
        self.mock_redis_session_manager.redis_client = mock_redis_client
        
        self.session_manager.prevent_non_admin_login()
        
        # Should set internal flag
        self.assertTrue(self.session_manager._login_prevention_active)
        
        # Should set Redis flag
        mock_redis_client.set.assert_called_once_with(
            "vedfolnir:maintenance:login_prevention",
            "true",
            ex=7200
        )
    
    def test_allow_non_admin_login(self):
        """Test disabling login prevention"""
        # Mock Redis client
        mock_redis_client = Mock()
        self.mock_redis_session_manager.redis_client = mock_redis_client
        
        # First enable prevention
        self.session_manager.prevent_non_admin_login()
        
        # Then disable it
        self.session_manager.allow_non_admin_login()
        
        # Should clear internal flag
        self.assertFalse(self.session_manager._login_prevention_active)
        
        # Should delete Redis flag
        mock_redis_client.delete.assert_called_once_with("vedfolnir:maintenance:login_prevention")
    
    def test_is_login_prevented_for_admin_user(self):
        """Test login prevention check for admin user"""
        # Enable login prevention
        self.session_manager.prevent_non_admin_login()
        
        result = self.session_manager.is_login_prevented_for_user(self.admin_user)
        
        # Admin should never be prevented
        self.assertFalse(result)
    
    def test_is_login_prevented_for_regular_user_active(self):
        """Test login prevention check for regular user when prevention is active"""
        # Enable login prevention
        self.session_manager.prevent_non_admin_login()
        
        result = self.session_manager.is_login_prevented_for_user(self.regular_user)
        
        # Regular user should be prevented
        self.assertTrue(result)
        
        # Check statistics
        stats = self.session_manager.get_session_stats()
        self.assertEqual(stats['statistics']['login_attempts_blocked'], 1)
    
    def test_is_login_prevented_for_regular_user_inactive(self):
        """Test login prevention check for regular user when prevention is inactive"""
        result = self.session_manager.is_login_prevented_for_user(self.regular_user)
        
        # Regular user should not be prevented
        self.assertFalse(result)
    
    def test_is_login_prevented_redis_state_sync(self):
        """Test login prevention syncs with Redis state"""
        # Mock Redis client
        mock_redis_client = Mock()
        mock_redis_client.get.return_value = "true"
        self.mock_redis_session_manager.redis_client = mock_redis_client
        
        result = self.session_manager.is_login_prevented_for_user(self.regular_user)
        
        # Should be prevented based on Redis state
        self.assertTrue(result)
        
        # Should sync local state
        self.assertTrue(self.session_manager._login_prevention_active)
    
    def test_get_active_non_admin_sessions(self):
        """Test getting active non-admin sessions"""
        self.session_manager._get_all_active_sessions = Mock(return_value=[
            self.admin_session_info,
            self.user_session_info
        ])
        
        result = self.session_manager.get_active_non_admin_sessions()
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].session_id, "user-session-456")
        self.assertEqual(result[0].user_role, UserRole.REVIEWER.value)
    
    def test_get_active_admin_sessions(self):
        """Test getting active admin sessions"""
        self.session_manager._get_all_active_sessions = Mock(return_value=[
            self.admin_session_info,
            self.user_session_info
        ])
        
        result = self.session_manager.get_active_admin_sessions()
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].session_id, "admin-session-123")
        self.assertEqual(result[0].user_role, UserRole.ADMIN.value)
    
    def test_get_session_stats(self):
        """Test getting session statistics"""
        # Setup mock sessions
        self.session_manager._get_all_active_sessions = Mock(return_value=[
            self.admin_session_info,
            self.user_session_info
        ])
        
        # Enable login prevention and invalidate some sessions
        self.session_manager.prevent_non_admin_login()
        self.session_manager._invalidated_sessions_count = 5
        
        stats = self.session_manager.get_session_stats()
        
        self.assertEqual(stats['total_active_sessions'], 2)
        self.assertEqual(stats['admin_sessions'], 1)
        self.assertEqual(stats['non_admin_sessions'], 1)
        self.assertTrue(stats['login_prevention_active'])
        self.assertEqual(stats['invalidated_sessions_count'], 5)
        self.assertIn('statistics', stats)
    
    def test_cleanup_maintenance_state(self):
        """Test cleaning up maintenance state"""
        # Mock Redis client
        mock_redis_client = Mock()
        self.mock_redis_session_manager.redis_client = mock_redis_client
        
        # Set some state
        self.session_manager._login_prevention_active = True
        self.session_manager._invalidated_sessions_count = 10
        
        result = self.session_manager.cleanup_maintenance_state()
        
        self.assertTrue(result)
        self.assertFalse(self.session_manager._login_prevention_active)
        self.assertEqual(self.session_manager._invalidated_sessions_count, 0)
        
        # Should delete Redis state
        mock_redis_client.delete.assert_called_once_with("vedfolnir:maintenance:login_prevention")
    
    def test_get_all_active_sessions(self):
        """Test getting all active sessions with user information"""
        # Mock Redis session data
        mock_redis_client = Mock()
        mock_redis_client.smembers.return_value = ["session-1", "session-2"]
        self.mock_redis_session_manager.redis_client = mock_redis_client
        
        # Mock session contexts
        session_contexts = {
            "session-1": {
                'user_id': 1,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'last_activity': datetime.now(timezone.utc).isoformat(),
                'platform_connection_id': 1
            },
            "session-2": {
                'user_id': 2,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'last_activity': datetime.now(timezone.utc).isoformat(),
                'platform_connection_id': None
            }
        }
        
        def mock_get_session_context(session_id):
            return session_contexts.get(session_id)
        
        self.mock_redis_session_manager.get_session_context.side_effect = mock_get_session_context
        
        # Mock database session and users
        mock_db_session = Mock()
        mock_db_session.query.return_value.all.return_value = [
            self.admin_user,
            self.regular_user
        ]
        self.mock_db_manager.get_session.return_value.__enter__ = Mock(return_value=mock_db_session)
        self.mock_db_manager.get_session.return_value.__exit__ = Mock(return_value=None)
        
        result = self.session_manager._get_all_active_sessions()
        
        self.assertEqual(len(result), 2)
        
        # Check first session (admin)
        admin_session = next(s for s in result if s.user_id == 1)
        self.assertEqual(admin_session.session_id, "session-1")
        self.assertEqual(admin_session.username, "admin")
        self.assertEqual(admin_session.user_role, UserRole.ADMIN.value)
        
        # Check second session (regular user)
        user_session = next(s for s in result if s.user_id == 2)
        self.assertEqual(user_session.session_id, "session-2")
        self.assertEqual(user_session.username, "user")
        self.assertEqual(user_session.user_role, UserRole.REVIEWER.value)
    
    def test_get_all_active_sessions_with_invalid_session(self):
        """Test getting active sessions handles invalid session data"""
        # Mock Redis session data
        mock_redis_client = Mock()
        mock_redis_client.smembers.return_value = ["valid-session", "invalid-session"]
        self.mock_redis_session_manager.redis_client = mock_redis_client
        
        # Mock session contexts - one valid, one invalid
        def mock_get_session_context(session_id):
            if session_id == "valid-session":
                return {
                    'user_id': 1,
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'last_activity': datetime.now(timezone.utc).isoformat(),
                    'platform_connection_id': 1
                }
            return None  # Invalid session
        
        self.mock_redis_session_manager.get_session_context.side_effect = mock_get_session_context
        
        # Mock database session and users
        mock_db_session = Mock()
        mock_db_session.query.return_value.all.return_value = [self.admin_user]
        self.mock_db_manager.get_session.return_value.__enter__ = Mock(return_value=mock_db_session)
        self.mock_db_manager.get_session.return_value.__exit__ = Mock(return_value=None)
        
        result = self.session_manager._get_all_active_sessions()
        
        # Should only return valid session
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].session_id, "valid-session")
    
    def test_error_handling_in_session_stats(self):
        """Test error handling in session statistics"""
        self.session_manager._get_all_active_sessions = Mock(side_effect=Exception("Test error"))
        
        stats = self.session_manager.get_session_stats()
        
        # Should return default values with error
        self.assertEqual(stats['total_active_sessions'], 0)
        self.assertEqual(stats['admin_sessions'], 0)
        self.assertEqual(stats['non_admin_sessions'], 0)
        self.assertIn('error', stats)


if __name__ == '__main__':
    unittest.main()
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Tests for session cleanup data integrity
"""

import unittest
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import patch

from config import Config
from database import DatabaseManager
from models import User, PlatformConnection, UserSession, UserRole
from unified_session_manager import UnifiedSessionManager as SessionManager


class TestSessionCleanup(unittest.TestCase):
    """Test session cleanup maintains data integrity"""
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary database
        self.db_fd, self.db_path = tempfile.mkstemp()
        
        # Create test config
        self.config = Config()
        self.config.storage.database_url = f'sqlite:///{self.db_path}'
        
        # Initialize database manager
        self.db_manager = DatabaseManager(self.config)
        self.db_manager.create_tables()
        
        # Initialize session manager
        self.session_manager = UnifiedSessionManager(self.db_manager)
        
        # Create test data
        self._create_test_data()
    
    def tearDown(self):
        """Clean up test environment"""
        os.close(self.db_fd)
        os.unlink(self.db_path)
    
    def _create_test_data(self):
        """Create test user and platform data"""
        session = self.db_manager.get_session()
        try:
            # Create test users
            self.user1 = User(
                username='user1',
                email='user1@test.com',
                role=UserRole.REVIEWER,
                is_active=True
            )
            self.user1.set_password('pass1')
            session.add(self.user1)
            
            self.user2 = User(
                username='user2',
                email='user2@test.com',
                role=UserRole.REVIEWER,
                is_active=True
            )
            self.user2.set_password('pass2')
            session.add(self.user2)
            session.flush()  # Get the user IDs
            
            # Create platforms for user1
            self.platform1_user1 = PlatformConnection(
                user_id=self.user1.id,
                name='User1 Platform1',
                platform_type='pixelfed',
                instance_url='https://user1.pixelfed.social',
                username='user1',
                access_token='token1',
                is_default=True,
                is_active=True
            )
            session.add(self.platform1_user1)
            
            self.platform2_user1 = PlatformConnection(
                user_id=self.user1.id,
                name='User1 Platform2',
                platform_type='mastodon',
                instance_url='https://user1.mastodon.social',
                username='user1_masto',
                access_token='token2',
                is_default=False,
                is_active=True
            )
            session.add(self.platform2_user1)
            
            # Create platform for user2
            self.platform1_user2 = PlatformConnection(
                user_id=self.user2.id,
                name='User2 Platform1',
                platform_type='pixelfed',
                instance_url='https://user2.pixelfed.social',
                username='user2',
                access_token='token3',
                is_default=True,
                is_active=True
            )
            session.add(self.platform1_user2)
            session.commit()
            
            # Store IDs for tests
            self.user1_id = self.user1.id
            self.user2_id = self.user2.id
            self.platform1_user1_id = self.platform1_user1.id
            self.platform2_user1_id = self.platform2_user1.id
            self.platform1_user2_id = self.platform1_user2.id
            
        finally:
            session.close()
    
    def test_cleanup_expired_sessions_preserves_active_sessions(self):
        """Test that expired session cleanup doesn't affect active sessions"""
        # Create multiple sessions for different users
        session1_user1 = self.session_manager.create_user_session(self.user1_id, self.platform1_user1_id)
        session2_user1 = self.session_manager.create_user_session(self.user1_id, self.platform2_user1_id)
        session1_user2 = self.session_manager.create_user_session(self.user2_id, self.platform1_user2_id)
        
        # Manually expire one session
        db_session = self.db_manager.get_session()
        try:
            expired_session = db_session.query(UserSession).filter_by(session_id=session1_user1).first()
            expired_session.updated_at = datetime.now(timezone.utc) - timedelta(days=2)
            db_session.commit()
        finally:
            db_session.close()
        
        # Verify active sessions exist before cleanup (don't check expired one as it gets auto-cleaned)
        self.assertIsNotNone(self.session_manager.get_session_context(session2_user1))
        self.assertIsNotNone(self.session_manager.get_session_context(session1_user2))
        
        # Run cleanup (the expired session should be found and cleaned)
        cleaned_count = self.session_manager.cleanup_expired_sessions()
        self.assertGreaterEqual(cleaned_count, 1)  # At least 1 (the manually expired one)
        
        # Verify only expired session was removed
        self.assertIsNone(self.session_manager.get_session_context(session1_user1))  # Expired
        self.assertIsNotNone(self.session_manager.get_session_context(session2_user1))  # Active
        self.assertIsNotNone(self.session_manager.get_session_context(session1_user2))  # Active
        
        # Verify active sessions still have correct platform context
        context2 = self.session_manager.get_session_context(session2_user1)
        context3 = self.session_manager.get_session_context(session1_user2)
        
        self.assertEqual(context2['user_id'], self.user1_id)
        self.assertEqual(context2['platform_connection_id'], self.platform2_user1_id)
        self.assertEqual(context3['user_id'], self.user2_id)
        self.assertEqual(context3['platform_connection_id'], self.platform1_user2_id)
    
    def test_cleanup_user_sessions_preserves_other_users(self):
        """Test that user session cleanup doesn't affect other users' sessions"""
        # Create sessions for both users
        session1_user1 = self.session_manager.create_user_session(self.user1_id, self.platform1_user1_id)
        session2_user1 = self.session_manager.create_user_session(self.user1_id, self.platform2_user1_id)
        session1_user2 = self.session_manager.create_user_session(self.user2_id, self.platform1_user2_id)
        
        # Verify all sessions exist
        self.assertIsNotNone(self.session_manager.get_session_context(session1_user1))
        self.assertIsNotNone(self.session_manager.get_session_context(session2_user1))
        self.assertIsNotNone(self.session_manager.get_session_context(session1_user2))
        
        # Clean up user1's sessions
        cleaned_count = self.session_manager.cleanup_user_sessions(self.user1_id)
        self.assertEqual(cleaned_count, 2)
        
        # Verify user1's sessions are gone but user2's session remains
        self.assertIsNone(self.session_manager.get_session_context(session1_user1))
        self.assertIsNone(self.session_manager.get_session_context(session2_user1))
        self.assertIsNotNone(self.session_manager.get_session_context(session1_user2))
        
        # Verify user2's session still has correct context
        context = self.session_manager.get_session_context(session1_user2)
        self.assertEqual(context['user_id'], self.user2_id)
        self.assertEqual(context['platform_connection_id'], self.platform1_user2_id)
    
    def test_cleanup_user_sessions_keep_current_preserves_specified_session(self):
        """Test that cleanup with keep_current preserves the specified session"""
        # Create multiple sessions for user1
        session1 = self.session_manager.create_user_session(self.user1_id, self.platform1_user1_id)
        session2 = self.session_manager.create_user_session(self.user1_id, self.platform2_user1_id)
        session3 = self.session_manager.create_user_session(self.user1_id, self.platform1_user1_id)
        
        # Verify all sessions exist
        self.assertIsNotNone(self.session_manager.get_session_context(session1))
        self.assertIsNotNone(self.session_manager.get_session_context(session2))
        self.assertIsNotNone(self.session_manager.get_session_context(session3))
        
        # Clean up all except session2
        cleaned_count = self.session_manager.cleanup_user_sessions(self.user1_id, keep_current=session2)
        self.assertEqual(cleaned_count, 2)
        
        # Verify only session2 remains
        self.assertIsNone(self.session_manager.get_session_context(session1))
        self.assertIsNotNone(self.session_manager.get_session_context(session2))
        self.assertIsNone(self.session_manager.get_session_context(session3))
        
        # Verify kept session has correct context
        context = self.session_manager.get_session_context(session2)
        self.assertEqual(context['user_id'], self.user1_id)
        self.assertEqual(context['platform_connection_id'], self.platform2_user1_id)
    
    def test_cleanup_maintains_platform_connection_integrity(self):
        """Test that session cleanup doesn't affect platform connections"""
        # Create sessions
        session1 = self.session_manager.create_user_session(self.user1_id, self.platform1_user1_id)
        session2 = self.session_manager.create_user_session(self.user1_id, self.platform2_user1_id)
        
        # Verify platform connections exist before cleanup
        db_session = self.db_manager.get_session()
        try:
            platforms_before = db_session.query(PlatformConnection).filter_by(user_id=self.user1_id).count()
            self.assertEqual(platforms_before, 2)
        finally:
            db_session.close()
        
        # Clean up all user sessions
        cleaned_count = self.session_manager.cleanup_user_sessions(self.user1_id)
        self.assertEqual(cleaned_count, 2)
        
        # Verify platform connections still exist after cleanup
        db_session = self.db_manager.get_session()
        try:
            platforms_after = db_session.query(PlatformConnection).filter_by(user_id=self.user1_id).count()
            self.assertEqual(platforms_after, 2)
            
            # Verify platform data is intact
            platform1 = db_session.query(PlatformConnection).get(self.platform1_user1_id)
            platform2 = db_session.query(PlatformConnection).get(self.platform2_user1_id)
            
            self.assertEqual(platform1.name, 'User1 Platform1')
            self.assertEqual(platform1.platform_type, 'pixelfed')
            self.assertTrue(platform1.is_active)
            
            self.assertEqual(platform2.name, 'User1 Platform2')
            self.assertEqual(platform2.platform_type, 'mastodon')
            self.assertTrue(platform2.is_active)
        finally:
            db_session.close()
    
    def test_cleanup_maintains_user_integrity(self):
        """Test that session cleanup doesn't affect user data"""
        # Create sessions
        session1 = self.session_manager.create_user_session(self.user1_id, self.platform1_user1_id)
        session2 = self.session_manager.create_user_session(self.user2_id, self.platform1_user2_id)
        
        # Verify users exist before cleanup
        db_session = self.db_manager.get_session()
        try:
            users_before = db_session.query(User).count()
            self.assertEqual(users_before, 2)
        finally:
            db_session.close()
        
        # Clean up all sessions
        self.session_manager.cleanup_user_sessions(self.user1_id)
        self.session_manager.cleanup_user_sessions(self.user2_id)
        
        # Verify users still exist after cleanup
        db_session = self.db_manager.get_session()
        try:
            users_after = db_session.query(User).count()
            self.assertEqual(users_after, 2)
            
            # Verify user data is intact
            user1 = db_session.query(User).get(self.user1_id)
            user2 = db_session.query(User).get(self.user2_id)
            
            self.assertEqual(user1.username, 'user1')
            self.assertEqual(user1.email, 'user1@test.com')
            self.assertTrue(user1.is_active)
            
            self.assertEqual(user2.username, 'user2')
            self.assertEqual(user2.email, 'user2@test.com')
            self.assertTrue(user2.is_active)
        finally:
            db_session.close()
    
    def test_cleanup_handles_database_constraints(self):
        """Test that cleanup properly handles database constraints and relationships"""
        # Create sessions
        session1 = self.session_manager.create_user_session(self.user1_id, self.platform1_user1_id)
        session2 = self.session_manager.create_user_session(self.user1_id, self.platform2_user1_id)
        
        # Verify sessions are properly linked to users and platforms
        db_session = self.db_manager.get_session()
        try:
            user_session1 = db_session.query(UserSession).filter_by(session_id=session1).first()
            user_session2 = db_session.query(UserSession).filter_by(session_id=session2).first()
            
            # Verify foreign key relationships
            self.assertEqual(user_session1.user_id, self.user1_id)
            self.assertEqual(user_session1.active_platform_id, self.platform1_user1_id)
            self.assertEqual(user_session2.user_id, self.user1_id)
            self.assertEqual(user_session2.active_platform_id, self.platform2_user1_id)
            
            # Verify relationships work
            self.assertIsNotNone(user_session1.user)
            self.assertIsNotNone(user_session1.active_platform)
            self.assertEqual(user_session1.user.username, 'user1')
            self.assertEqual(user_session1.active_platform.name, 'User1 Platform1')
        finally:
            db_session.close()
        
        # Clean up sessions
        cleaned_count = self.session_manager.cleanup_user_sessions(self.user1_id)
        self.assertEqual(cleaned_count, 2)
        
        # Verify cleanup was successful and didn't violate constraints
        db_session = self.db_manager.get_session()
        try:
            remaining_sessions = db_session.query(UserSession).filter_by(user_id=self.user1_id).count()
            self.assertEqual(remaining_sessions, 0)
            
            # Verify referenced entities still exist
            user_count = db_session.query(User).filter_by(id=self.user1_id).count()
            platform_count = db_session.query(PlatformConnection).filter_by(user_id=self.user1_id).count()
            
            self.assertEqual(user_count, 1)
            self.assertEqual(platform_count, 2)
        finally:
            db_session.close()
    
    def test_cleanup_concurrent_operations(self):
        """Test that cleanup works correctly with concurrent session operations"""
        # Create initial sessions
        session1 = self.session_manager.create_user_session(self.user1_id, self.platform1_user1_id)
        session2 = self.session_manager.create_user_session(self.user1_id, self.platform2_user1_id)
        
        # Simulate concurrent operations: create new session while cleaning up
        # This tests that cleanup doesn't interfere with new session creation
        
        # Start cleanup (but don't complete it yet by mocking)
        with patch.object(self.session_manager, 'cleanup_user_sessions') as mock_cleanup:
            # Create new session during "cleanup"
            session3 = self.session_manager.create_user_session(self.user1_id, self.platform1_user1_id)
            
            # Now actually run cleanup
            mock_cleanup.side_effect = lambda *args, **kwargs: self.session_manager.__class__.cleanup_user_sessions(self.session_manager, *args, **kwargs)
            cleaned_count = self.session_manager.cleanup_user_sessions(self.user1_id, keep_current=session3)
        
        # Verify cleanup worked correctly
        self.assertEqual(cleaned_count, 2)  # Should clean up session1 and session2
        
        # Verify session3 (created during cleanup) still exists
        context = self.session_manager.get_session_context(session3)
        self.assertIsNotNone(context)
        self.assertEqual(context['user_id'], self.user1_id)
        self.assertEqual(context['platform_connection_id'], self.platform1_user1_id)


if __name__ == '__main__':
    unittest.main()
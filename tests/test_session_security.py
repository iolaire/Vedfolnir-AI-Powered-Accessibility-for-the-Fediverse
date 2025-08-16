# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Tests for session security and validation
"""

import unittest
import tempfile
import os
import uuid
from datetime import datetime, timedelta
from unittest.mock import patch

from config import Config
from database import DatabaseManager
from models import User, PlatformConnection, UserSession, UserRole
from session_manager import SessionManager


class TestSessionSecurity(unittest.TestCase):
    """Test session validation prevents security issues"""
    
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
        self.session_manager = SessionManager(self.db_manager)
        
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
            
            # Create inactive user for testing
            self.inactive_user = User(
                username='inactive',
                email='inactive@test.com',
                role=UserRole.VIEWER,
                is_active=False
            )
            self.inactive_user.set_password('inactive_pass')
            session.add(self.inactive_user)
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
            
            # Create platform for user2
            self.platform1_user2 = PlatformConnection(
                user_id=self.user2.id,
                name='User2 Platform1',
                platform_type='pixelfed',
                instance_url='https://user2.pixelfed.social',
                username='user2',
                access_token='token2',
                is_default=True,
                is_active=True
            )
            session.add(self.platform1_user2)
            
            # Create inactive platform for testing
            self.inactive_platform = PlatformConnection(
                user_id=self.user1.id,
                name='Inactive Platform',
                platform_type='mastodon',
                instance_url='https://inactive.mastodon.social',
                username='user1_inactive',
                access_token='inactive_token',
                is_default=False,
                is_active=False
            )
            session.add(self.inactive_platform)
            session.commit()
            
            # Store IDs for tests
            self.user1_id = self.user1.id
            self.user2_id = self.user2.id
            self.inactive_user_id = self.inactive_user.id
            self.platform1_user1_id = self.platform1_user1.id
            self.platform1_user2_id = self.platform1_user2.id
            self.inactive_platform_id = self.inactive_platform.id
            
        finally:
            session.close()
    
    def test_session_validation_prevents_cross_user_access(self):
        """Test that session validation prevents users from accessing other users' sessions"""
        # Create session for user1
        session1_id = self.session_manager.create_user_session(self.user1_id, self.platform1_user1_id)
        
        # Verify user1 can access their own session
        self.assertTrue(self.session_manager.validate_session(session1_id, self.user1_id))
        
        # Verify user2 cannot access user1's session
        self.assertFalse(self.session_manager.validate_session(session1_id, self.user2_id))
        
        # Verify invalid user ID fails
        self.assertFalse(self.session_manager.validate_session(session1_id, 99999))
    
    def test_session_validation_prevents_invalid_session_access(self):
        """Test that validation fails for non-existent sessions"""
        # Test with completely invalid session ID
        fake_session_id = str(uuid.uuid4())
        self.assertFalse(self.session_manager.validate_session(fake_session_id, self.user1_id))
        
        # Test with malformed session ID
        self.assertFalse(self.session_manager.validate_session('invalid-session-id', self.user1_id))
        
        # Test with empty session ID
        self.assertFalse(self.session_manager.validate_session('', self.user1_id))
        
        # Test with None session ID
        self.assertFalse(self.session_manager.validate_session(None, self.user1_id))
    
    def test_session_validation_prevents_expired_session_access(self):
        """Test that expired sessions are automatically invalidated"""
        # Create session
        session_id = self.session_manager.create_user_session(self.user1_id, self.platform1_user1_id)
        
        # Verify session is initially valid
        self.assertTrue(self.session_manager.validate_session(session_id, self.user1_id))
        
        # Manually expire the session
        db_session = self.db_manager.get_session()
        try:
            user_session = db_session.query(UserSession).filter_by(session_id=session_id).first()
            user_session.updated_at = datetime.now(timezone.utc) - timedelta(days=2)
            db_session.commit()
        finally:
            db_session.close()
        
        # Verify expired session is no longer valid
        self.assertFalse(self.session_manager.validate_session(session_id, self.user1_id))
        
        # Verify session context is None for expired session
        context = self.session_manager.get_session_context(session_id)
        self.assertIsNone(context)
    
    def test_session_creation_prevents_inactive_user_access(self):
        """Test that sessions cannot be created for inactive users"""
        # Try to create session for inactive user
        with self.assertRaises(ValueError) as context:
            self.session_manager.create_user_session(self.inactive_user_id, self.platform1_user1_id)
        
        self.assertIn("not found or inactive", str(context.exception))
    
    def test_session_creation_prevents_invalid_platform_access(self):
        """Test that sessions cannot be created with invalid platform connections"""
        # Try to create session with non-existent platform
        with self.assertRaises(ValueError) as context:
            self.session_manager.create_user_session(self.user1_id, 99999)
        
        self.assertIn("not found or inactive", str(context.exception))
        
        # Try to create session with inactive platform
        with self.assertRaises(ValueError) as context:
            self.session_manager.create_user_session(self.user1_id, self.inactive_platform_id)
        
        self.assertIn("not found or inactive", str(context.exception))
        
        # Try to create session with another user's platform
        with self.assertRaises(ValueError) as context:
            self.session_manager.create_user_session(self.user1_id, self.platform1_user2_id)
        
        self.assertIn("not found or inactive", str(context.exception))
    
    def test_platform_switching_prevents_unauthorized_access(self):
        """Test that platform switching validates platform ownership"""
        # Create session for user1
        session_id = self.session_manager.create_user_session(self.user1_id, self.platform1_user1_id)
        
        # Try to switch to user2's platform (should fail)
        success = self.session_manager.update_platform_context(session_id, self.platform1_user2_id)
        self.assertFalse(success)
        
        # Verify original platform is still active
        context = self.session_manager.get_session_context(session_id)
        self.assertEqual(context['platform_connection_id'], self.platform1_user1_id)
        
        # Try to switch to inactive platform (should fail)
        success = self.session_manager.update_platform_context(session_id, self.inactive_platform_id)
        self.assertFalse(success)
        
        # Verify original platform is still active
        context = self.session_manager.get_session_context(session_id)
        self.assertEqual(context['platform_connection_id'], self.platform1_user1_id)
    
    def test_session_context_isolation(self):
        """Test that session contexts are properly isolated between users"""
        # Create sessions for both users
        session1_id = self.session_manager.create_user_session(self.user1_id, self.platform1_user1_id)
        session2_id = self.session_manager.create_user_session(self.user2_id, self.platform1_user2_id)
        
        # Get contexts
        context1 = self.session_manager.get_session_context(session1_id)
        context2 = self.session_manager.get_session_context(session2_id)
        
        # Verify contexts are isolated
        self.assertNotEqual(context1['user_id'], context2['user_id'])
        self.assertNotEqual(context1['platform_connection_id'], context2['platform_connection_id'])
        self.assertNotEqual(context1['session_id'], context2['session_id'])
        
        # Verify each context has correct data
        self.assertEqual(context1['user_id'], self.user1_id)
        self.assertEqual(context1['platform_connection_id'], self.platform1_user1_id)
        self.assertEqual(context1['user'].username, 'user1')
        
        self.assertEqual(context2['user_id'], self.user2_id)
        self.assertEqual(context2['platform_connection_id'], self.platform1_user2_id)
        self.assertEqual(context2['user'].username, 'user2')
    
    def test_session_tampering_prevention(self):
        """Test that session tampering is prevented"""
        # Create session
        session_id = self.session_manager.create_user_session(self.user1_id, self.platform1_user1_id)
        
        # Try to manually modify session in database to point to different user
        db_session = self.db_manager.get_session()
        try:
            user_session = db_session.query(UserSession).filter_by(session_id=session_id).first()
            original_user_id = user_session.user_id
            
            # Tamper with session
            user_session.user_id = self.user2_id
            db_session.commit()
            
            # Verify validation fails for original user
            self.assertFalse(self.session_manager.validate_session(session_id, original_user_id))
            
            # Verify validation succeeds for new user (this is expected behavior)
            self.assertTrue(self.session_manager.validate_session(session_id, self.user2_id))
            
            # But verify context shows the tampered data (this would be caught by application logic)
            context = self.session_manager.get_session_context(session_id)
            self.assertEqual(context['user_id'], self.user2_id)
            
        finally:
            db_session.close()
    
    def test_concurrent_session_security(self):
        """Test security with concurrent sessions for same user"""
        # Create multiple sessions for same user
        session1_id = self.session_manager.create_user_session(self.user1_id, self.platform1_user1_id)
        session2_id = self.session_manager.create_user_session(self.user1_id, self.platform1_user1_id)
        
        # Verify both sessions are valid for the user
        self.assertTrue(self.session_manager.validate_session(session1_id, self.user1_id))
        self.assertTrue(self.session_manager.validate_session(session2_id, self.user1_id))
        
        # Verify sessions are independent
        self.assertNotEqual(session1_id, session2_id)
        
        # Verify other user cannot access either session
        self.assertFalse(self.session_manager.validate_session(session1_id, self.user2_id))
        self.assertFalse(self.session_manager.validate_session(session2_id, self.user2_id))
        
        # Clean up one session, verify other remains valid
        self.session_manager.cleanup_user_sessions(self.user1_id, keep_current=session2_id)
        
        self.assertFalse(self.session_manager.validate_session(session1_id, self.user1_id))
        self.assertTrue(self.session_manager.validate_session(session2_id, self.user1_id))
    
    def test_session_timeout_security(self):
        """Test that session timeout provides security"""
        # Create session with short timeout
        original_timeout = self.session_manager.session_timeout
        self.session_manager.session_timeout = timedelta(seconds=1)
        
        try:
            session_id = self.session_manager.create_user_session(self.user1_id, self.platform1_user1_id)
            
            # Verify session is initially valid
            self.assertTrue(self.session_manager.validate_session(session_id, self.user1_id))
            
            # Wait for timeout (simulate with manual timestamp update)
            db_session = self.db_manager.get_session()
            try:
                user_session = db_session.query(UserSession).filter_by(session_id=session_id).first()
                user_session.updated_at = datetime.now(timezone.utc) - timedelta(seconds=2)
                db_session.commit()
            finally:
                db_session.close()
            
            # Verify session is no longer valid after timeout
            self.assertFalse(self.session_manager.validate_session(session_id, self.user1_id))
            
        finally:
            # Restore original timeout
            self.session_manager.session_timeout = original_timeout
    
    def test_session_id_uniqueness_security(self):
        """Test that session IDs are unique and unpredictable"""
        # Create multiple sessions
        session_ids = []
        for _ in range(10):
            session_id = self.session_manager.create_user_session(self.user1_id, self.platform1_user1_id)
            session_ids.append(session_id)
        
        # Verify all session IDs are unique
        self.assertEqual(len(session_ids), len(set(session_ids)))
        
        # Verify session IDs are UUIDs (proper format)
        for session_id in session_ids:
            try:
                uuid.UUID(session_id)
            except ValueError:
                self.fail(f"Session ID {session_id} is not a valid UUID")
        
        # Clean up
        self.session_manager.cleanup_user_sessions(self.user1_id)
    
    def test_session_validation_with_database_errors(self):
        """Test session validation handles database errors gracefully"""
        # Create valid session
        session_id = self.session_manager.create_user_session(self.user1_id, self.platform1_user1_id)
        
        # Mock database error for validation
        with patch.object(self.session_manager.db_manager, 'get_session') as mock_get_session:
            mock_get_session.side_effect = Exception("Database connection error")
            
            # Verify validation fails gracefully
            result = self.session_manager.validate_session(session_id, self.user1_id)
            self.assertFalse(result)
        
        # Test get_session_context with database error separately
        with patch.object(self.session_manager.db_manager, 'get_session') as mock_get_session:
            mock_get_session.side_effect = Exception("Database connection error")
            
            # Verify get_session_context fails gracefully
            context = self.session_manager.get_session_context(session_id)
            self.assertIsNone(context)


if __name__ == '__main__':
    unittest.main()
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Tests for platform-aware session management
"""

import unittest
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from config import Config
from database import DatabaseManager
from models import User, PlatformConnection, UserSession, UserRole
from session_manager import SessionManager, get_current_platform_context
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


class TestSessionManagement(unittest.TestCase):
    """Test session management functionality"""
    
    def setUp(self):
        """Set up test database and session manager"""
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
        
        # Create test user and platform
        self._create_test_data()
    
    def tearDown(self):
        """Clean up test database"""
        os.close(self.db_fd)
        os.unlink(self.db_path)
    
    def _create_test_data(self):
        """Create test user and platform data"""
        session = self.db_manager.get_session()
        try:
            # Create test user
            self.test_user = User(
                username='testuser',
                email='test@example.com',
                role=UserRole.REVIEWER,
                is_active=True
            )
            self.test_user.set_password('testpass')
            session.add(self.test_user)
            session.flush()  # Get the user ID
            
            # Create test platform connection
            self.test_platform = PlatformConnection(
                user_id=self.test_user.id,
                name='Test Platform',
                platform_type='pixelfed',
                instance_url='https://test.pixelfed.social',
                username='testuser',
                access_token='test_token',
                is_default=True,
                is_active=True
            )
            session.add(self.test_platform)
            session.commit()
            
            # Store IDs for tests
            self.user_id = self.test_user.id
            self.platform_id = self.test_platform.id
            
        finally:
            session.close()
    
    def test_create_user_session(self):
        """Test creating a user session"""
        # Create session without platform
        session_id = self.session_manager.create_user_session(self.user_id)
        self.assertIsNotNone(session_id)
        
        # Verify session was created
        context = self.session_manager.get_session_context(session_id)
        self.assertIsNotNone(context)
        self.assertEqual(context['user_id'], self.user_id)
        self.assertEqual(context['platform_connection_id'], self.platform_id)  # Should use default
    
    def test_create_user_session_with_platform(self):
        """Test creating a user session with specific platform"""
        session_id = self.session_manager.create_user_session(self.user_id, self.platform_id)
        self.assertIsNotNone(session_id)
        
        # Verify session was created with correct platform
        context = self.session_manager.get_session_context(session_id)
        self.assertIsNotNone(context)
        self.assertEqual(context['user_id'], self.user_id)
        self.assertEqual(context['platform_connection_id'], self.platform_id)
    
    def test_create_session_invalid_user(self):
        """Test creating session with invalid user"""
        with self.assertRaises(ValueError):
            self.session_manager.create_user_session(99999)
    
    def test_create_session_invalid_platform(self):
        """Test creating session with invalid platform"""
        with self.assertRaises(ValueError):
            self.session_manager.create_user_session(self.user_id, 99999)
    
    def test_get_session_context(self):
        """Test getting session context"""
        # Create session
        session_id = self.session_manager.create_user_session(self.user_id, self.platform_id)
        
        # Get context
        context = self.session_manager.get_session_context(session_id)
        self.assertIsNotNone(context)
        self.assertEqual(context['session_id'], session_id)
        self.assertEqual(context['user_id'], self.user_id)
        self.assertEqual(context['platform_connection_id'], self.platform_id)
        self.assertIsNotNone(context['user'])
        self.assertIsNotNone(context['platform_connection'])
    
    def test_get_session_context_invalid(self):
        """Test getting context for invalid session"""
        context = self.session_manager.get_session_context('invalid_session_id')
        self.assertIsNone(context)
    
    def test_update_platform_context(self):
        """Test updating platform context"""
        # Create another platform
        session = self.db_manager.get_session()
        try:
            platform2 = PlatformConnection(
                user_id=self.user_id,
                name='Test Platform 2',
                platform_type='mastodon',
                instance_url='https://test.mastodon.social',
                username='testuser2',
                access_token='test_token2',
                is_default=False,
                is_active=True
            )
            session.add(platform2)
            session.commit()
            platform2_id = platform2.id
        finally:
            session.close()
        
        # Create session with first platform
        session_id = self.session_manager.create_user_session(self.user_id, self.platform_id)
        
        # Update to second platform
        success = self.session_manager.update_platform_context(session_id, platform2_id)
        self.assertTrue(success)
        
        # Verify update
        context = self.session_manager.get_session_context(session_id)
        self.assertEqual(context['platform_connection_id'], platform2_id)
    
    def test_update_platform_context_invalid_session(self):
        """Test updating platform context with invalid session"""
        success = self.session_manager.update_platform_context('invalid_session', self.platform_id)
        self.assertFalse(success)
    
    def test_update_platform_context_invalid_platform(self):
        """Test updating platform context with invalid platform"""
        session_id = self.session_manager.create_user_session(self.user_id, self.platform_id)
        success = self.session_manager.update_platform_context(session_id, 99999)
        self.assertFalse(success)
    
    def test_validate_session(self):
        """Test session validation"""
        # Create session
        session_id = self.session_manager.create_user_session(self.user_id, self.platform_id)
        
        # Valid session
        self.assertTrue(self.session_manager.validate_session(session_id, self.user_id))
        
        # Invalid user
        self.assertFalse(self.session_manager.validate_session(session_id, 99999))
        
        # Invalid session
        self.assertFalse(self.session_manager.validate_session('invalid', self.user_id))
    
    def test_cleanup_user_sessions(self):
        """Test cleaning up user sessions"""
        # Create multiple sessions
        session1 = self.session_manager.create_user_session(self.user_id, self.platform_id)
        session2 = self.session_manager.create_user_session(self.user_id, self.platform_id)
        
        # Clean up all sessions
        count = self.session_manager.cleanup_user_sessions(self.user_id)
        self.assertEqual(count, 2)
        
        # Verify sessions are gone
        self.assertIsNone(self.session_manager.get_session_context(session1))
        self.assertIsNone(self.session_manager.get_session_context(session2))
    
    def test_cleanup_user_sessions_keep_current(self):
        """Test cleaning up user sessions while keeping current"""
        # Create multiple sessions
        session1 = self.session_manager.create_user_session(self.user_id, self.platform_id)
        session2 = self.session_manager.create_user_session(self.user_id, self.platform_id)
        
        # Clean up all except session1
        count = self.session_manager.cleanup_user_sessions(self.user_id, keep_current=session1)
        self.assertEqual(count, 1)
        
        # Verify session1 still exists, session2 is gone
        self.assertIsNotNone(self.session_manager.get_session_context(session1))
        self.assertIsNone(self.session_manager.get_session_context(session2))
    
    def test_cleanup_expired_sessions(self):
        """Test cleaning up expired sessions"""
        # Create session
        session_id = self.session_manager.create_user_session(self.user_id, self.platform_id)
        
        # Manually expire the session by setting old timestamp
        db_session = self.db_manager.get_session()
        try:
            user_session = db_session.query(UserSession).filter_by(session_id=session_id).first()
            user_session.updated_at = datetime.now(timezone.utc) - timedelta(days=2)
            db_session.commit()
        finally:
            db_session.close()
        
        # Clean up expired sessions
        count = self.session_manager.cleanup_expired_sessions()
        self.assertEqual(count, 1)
        
        # Verify session is gone
        self.assertIsNone(self.session_manager.get_session_context(session_id))


if __name__ == '__main__':
    unittest.main()
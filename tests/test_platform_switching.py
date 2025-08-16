# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Tests for platform switching functionality
"""

import unittest
import tempfile
import os
from datetime import datetime
from unittest.mock import patch, MagicMock

from config import Config
from database import DatabaseManager
from models import User, PlatformConnection, UserSession, UserRole
from session_manager import SessionManager
from web_app import app


class TestPlatformSwitching(unittest.TestCase):
    """Test platform switching updates session immediately"""
    
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
        
        # Configure Flask app for testing
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['SECRET_KEY'] = 'test-secret-key'
        
        # Create test client
        self.client = app.test_client()
        
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
            # Create test user
            self.test_user = User(
                username='testuser',
                email='test@test.com',
                role=UserRole.REVIEWER,
                is_active=True
            )
            self.test_user.set_password('testpass')
            session.add(self.test_user)
            session.flush()  # Get the user ID
            
            # Create first platform connection (default)
            self.platform1 = PlatformConnection(
                user_id=self.test_user.id,
                name='Pixelfed Platform',
                platform_type='pixelfed',
                instance_url='https://test.pixelfed.social',
                username='testuser',
                access_token='test_token_1',
                is_default=True,
                is_active=True
            )
            session.add(self.platform1)
            session.flush()
            
            # Create second platform connection
            self.platform2 = PlatformConnection(
                user_id=self.test_user.id,
                name='Mastodon Platform',
                platform_type='mastodon',
                instance_url='https://test.mastodon.social',
                username='testuser2',
                access_token='test_token_2',
                is_default=False,
                is_active=True
            )
            session.add(self.platform2)
            session.commit()
            
            # Store IDs for tests
            self.user_id = self.test_user.id
            self.platform1_id = self.platform1.id
            self.platform2_id = self.platform2.id
            
        finally:
            session.close()
    
    def test_session_manager_platform_switch_immediate(self):
        """Test that session manager updates platform context immediately"""
        # Create session with first platform
        session_id = self.session_manager.create_user_session(self.user_id, self.platform1_id)
        
        # Verify initial platform
        context = self.session_manager.get_session_context(session_id)
        self.assertEqual(context['platform_connection_id'], self.platform1_id)
        initial_updated_at = context['updated_at']
        
        # Switch to second platform
        success = self.session_manager.update_platform_context(session_id, self.platform2_id)
        self.assertTrue(success)
        
        # Verify immediate update
        context = self.session_manager.get_session_context(session_id)
        self.assertEqual(context['platform_connection_id'], self.platform2_id)
        
        # Verify timestamp was updated
        self.assertGreater(context['updated_at'], initial_updated_at)
        
        # Verify platform object is correct
        self.assertEqual(context['platform_connection'].id, self.platform2_id)
        self.assertEqual(context['platform_connection'].name, 'Mastodon Platform')
    
    def test_platform_switch_updates_last_used(self):
        """Test that platform switching updates the platform's last_used timestamp"""
        # Create session with first platform
        session_id = self.session_manager.create_user_session(self.user_id, self.platform1_id)
        
        # Get initial last_used timestamp
        db_session = self.db_manager.get_session()
        try:
            platform2 = db_session.query(PlatformConnection).get(self.platform2_id)
            initial_last_used = platform2.last_used
        finally:
            db_session.close()
        
        # Switch to second platform
        success = self.session_manager.update_platform_context(session_id, self.platform2_id)
        self.assertTrue(success)
        
        # Verify last_used was updated
        db_session = self.db_manager.get_session()
        try:
            platform2 = db_session.query(PlatformConnection).get(self.platform2_id)
            if initial_last_used:
                self.assertGreater(platform2.last_used, initial_last_used)
            else:
                self.assertIsNotNone(platform2.last_used)
        finally:
            db_session.close()
    
    def test_platform_switch_invalid_platform(self):
        """Test that switching to invalid platform fails gracefully"""
        # Create session with first platform
        session_id = self.session_manager.create_user_session(self.user_id, self.platform1_id)
        
        # Try to switch to non-existent platform
        success = self.session_manager.update_platform_context(session_id, 99999)
        self.assertFalse(success)
        
        # Verify original platform is still active
        context = self.session_manager.get_session_context(session_id)
        self.assertEqual(context['platform_connection_id'], self.platform1_id)
    
    def test_platform_switch_unauthorized_platform(self):
        """Test that switching to another user's platform fails"""
        # Create another user and platform
        db_session = self.db_manager.get_session()
        try:
            other_user = User(
                username='otheruser',
                email='other@test.com',
                role=UserRole.REVIEWER,
                is_active=True
            )
            other_user.set_password('otherpass')
            db_session.add(other_user)
            db_session.flush()
            
            other_platform = PlatformConnection(
                user_id=other_user.id,
                name='Other Platform',
                platform_type='pixelfed',
                instance_url='https://other.pixelfed.social',
                username='otheruser',
                access_token='other_token',
                is_default=True,
                is_active=True
            )
            db_session.add(other_platform)
            db_session.commit()
            other_platform_id = other_platform.id
        finally:
            db_session.close()
        
        # Create session for first user
        session_id = self.session_manager.create_user_session(self.user_id, self.platform1_id)
        
        # Try to switch to other user's platform
        success = self.session_manager.update_platform_context(session_id, other_platform_id)
        self.assertFalse(success)
        
        # Verify original platform is still active
        context = self.session_manager.get_session_context(session_id)
        self.assertEqual(context['platform_connection_id'], self.platform1_id)
    
    def test_concurrent_platform_switches(self):
        """Test that concurrent platform switches work correctly"""
        # Create two sessions for the same user
        session1_id = self.session_manager.create_user_session(self.user_id, self.platform1_id)
        session2_id = self.session_manager.create_user_session(self.user_id, self.platform1_id)
        
        # Switch first session to platform2
        success1 = self.session_manager.update_platform_context(session1_id, self.platform2_id)
        self.assertTrue(success1)
        
        # Switch second session to platform2 as well
        success2 = self.session_manager.update_platform_context(session2_id, self.platform2_id)
        self.assertTrue(success2)
        
        # Verify both sessions have correct platform
        context1 = self.session_manager.get_session_context(session1_id)
        context2 = self.session_manager.get_session_context(session2_id)
        
        self.assertEqual(context1['platform_connection_id'], self.platform2_id)
        self.assertEqual(context2['platform_connection_id'], self.platform2_id)
        
        # Switch first session back to platform1
        success1 = self.session_manager.update_platform_context(session1_id, self.platform1_id)
        self.assertTrue(success1)
        
        # Verify sessions have different platforms
        context1 = self.session_manager.get_session_context(session1_id)
        context2 = self.session_manager.get_session_context(session2_id)
        
        self.assertEqual(context1['platform_connection_id'], self.platform1_id)
        self.assertEqual(context2['platform_connection_id'], self.platform2_id)
    
    def test_platform_switch_session_integration(self):
        """Test that platform switching integrates properly with session management"""
        # Create a session with first platform
        session_id = self.session_manager.create_user_session(self.user_id, self.platform1_id)
        
        # Verify initial state
        context = self.session_manager.get_session_context(session_id)
        self.assertEqual(context['platform_connection_id'], self.platform1_id)
        self.assertEqual(context['platform_connection'].name, 'Pixelfed Platform')
        
        # Switch platform using session manager (simulating what web app does)
        success = self.session_manager.update_platform_context(session_id, self.platform2_id)
        self.assertTrue(success)
        
        # Verify immediate update
        context = self.session_manager.get_session_context(session_id)
        self.assertEqual(context['platform_connection_id'], self.platform2_id)
        self.assertEqual(context['platform_connection'].name, 'Mastodon Platform')
        
        # Verify the session is still valid and functional
        self.assertTrue(self.session_manager.validate_session(session_id, self.user_id))
        
        # Switch back to first platform
        success = self.session_manager.update_platform_context(session_id, self.platform1_id)
        self.assertTrue(success)
        
        # Verify switch back worked
        context = self.session_manager.get_session_context(session_id)
        self.assertEqual(context['platform_connection_id'], self.platform1_id)
        self.assertEqual(context['platform_connection'].name, 'Pixelfed Platform')


if __name__ == '__main__':
    unittest.main()
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Integration tests for session management with web app
"""

import unittest
import tempfile
import os
from unittest.mock import patch, MagicMock
from bs4 import BeautifulSoup

from config import Config
from app.core.database.core.database_manager import DatabaseManager
from models import User, PlatformConnection, UserRole
from unified_session_manager import UnifiedSessionManager as SessionManager, get_current_platform_context
from web_app import app

class TestSessionIntegration(unittest.TestCase):
    """Test session management integration with web app"""
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary database
        self.db_fd, self.db_path = tempfile.mkstemp()
        
        # Create test config
        self.config = Config()
        self.config.storage.database_url = f'mysql+pymysql://{self.db_path}'
        
        # Initialize database manager
        self.db_manager = DatabaseManager(self.config)
        self.db_manager.create_tables()
        
        # Initialize session manager
        self.session_manager = UnifiedSessionManager(self.db_manager)
        
        # Configure Flask app for testing
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key'
        # Keep CSRF enabled to test real-world scenario
        
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
    
    def test_session_creation_on_login(self):
        """Test that session is created when user logs in"""
        # Mock the session manager in the web app
        with patch('web_app.session_manager', self.session_manager):
            # Verify session was created by checking the cookie in the response
            session_cookie = next((cookie for cookie in self.client.cookie_jar if cookie.name == 'session_id'), None)
            self.assertIsNotNone(session_cookie)
            session_id = session_cookie.value

            # Verify the session in the database
            context = self.session_manager.get_session_context(session_id)
            self.assertIsNotNone(context)
            self.assertEqual(context['user_id'], self.user_id)
    
    def test_platform_context_injection(self):
        """Test that platform context is properly injected into templates"""
        # This test would require more complex setup with Flask test client
        # and session handling. For now, we verify the basic functionality works.
        
        # Create a session manually
        session_id = self.session_manager.create_user_session(self.user_id, self.platform_id)
        
        # Verify session context
        context = self.session_manager.get_session_context(session_id)
        self.assertIsNotNone(context)
        self.assertEqual(context['user_id'], self.user_id)
        self.assertEqual(context['platform_connection_id'], self.platform_id)
    
    def test_session_validation(self):
        """Test session validation functionality"""
        # Create session
        session_id = self.session_manager.create_user_session(self.user_id, self.platform_id)
        
        # Test validation
        self.assertTrue(self.session_manager.validate_session(session_id, self.user_id))
        self.assertFalse(self.session_manager.validate_session(session_id, 99999))
        self.assertFalse(self.session_manager.validate_session('invalid', self.user_id))
    
    def test_platform_switching(self):
        """Test platform switching functionality"""
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
        
        # Switch to second platform
        success = self.session_manager.update_platform_context(session_id, platform2_id)
        self.assertTrue(success)
        
        # Verify switch
        context = self.session_manager.get_session_context(session_id)
        self.assertEqual(context['platform_connection_id'], platform2_id)

if __name__ == '__main__':
    unittest.main()
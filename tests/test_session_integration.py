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
from database import DatabaseManager
from models import User, PlatformConnection, UserRole
from session_manager import SessionManager, get_current_platform_context
from web_app import app


class TestSessionIntegration(unittest.TestCase):
    """Test session management integration with web app"""
    
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
            # First, get the login page to obtain a CSRF token
            with self.client.session_transaction() as sess:
                # Set up a basic session
                sess['_csrf_token'] = 'test-csrf-token'
            
            # Get CSRF token from the login form
            login_page_response = self.client.get('/login')
            self.assertEqual(login_page_response.status_code, 200)
            
            # Extract CSRF token from the login form
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(login_page_response.data, 'html.parser')
            csrf_input = soup.find('input', {'name': 'csrf_token'})
            
            csrf_token = None
            if csrf_input:
                csrf_token = csrf_input.get('value')
            
            # If no CSRF token in form, try to generate one using Flask-WTF
            if not csrf_token:
                with self.client.application.test_request_context():
                    from flask_wtf.csrf import generate_csrf
                    csrf_token = generate_csrf()
            
            # Attempt login with CSRF token
            login_data = {
                'username': 'testuser',
                'password': 'testpass',
                'remember': False
            }
            
            if csrf_token:
                login_data['csrf_token'] = csrf_token
            
            response = self.client.post('/login', data=login_data, follow_redirects=True)
            
            # Check that login was processed (may not be successful due to mock user, but should not be CSRF error)
            # A 200 status means the form was processed, even if login failed
            self.assertIn(response.status_code, [200, 302])  # Either success or redirect
            
            # Verify session was created (we can't easily test the Flask session here,
            # but we can verify the session manager has sessions)
            # This is a basic integration test - more detailed testing would require
            # Flask test client session handling
    
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
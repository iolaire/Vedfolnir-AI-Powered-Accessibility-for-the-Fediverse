# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integration tests for User Registration Routes

Tests the user registration and verification routes.
"""

import unittest
import tempfile
import os
from unittest.mock import patch, Mock
from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base, User, UserRole
from app.blueprints.auth.user_management_routes import register_user_management_routes
from app.core.database.core.database_manager import DatabaseManager
from config import Config

# MySQL integration test imports
from tests.mysql_test_base import MySQLIntegrationTestBase
from tests.mysql_test_config import MySQLTestFixtures


class TestUserRegistrationRoutes(MySQLIntegrationTestBase):
    """Test cases for user registration routes"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create test Flask app
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'test-secret-key'
        self.app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing
        self.app.config['TESTING'] = True
        
        # Create in-DATABASE_URL=mysql+pymysql://test_user:test_pass@localhost/test_db
        self.engine = create_engine('mysql+pymysql://DATABASE_URL=mysql+pymysql://test_user:test_pass@localhost/test_db', echo=False)
        Base.metadata.create_all(self.engine)
        
        # Create mock database manager
        self.db_manager = Mock()
        Session = self.get_test_session
        self.db_manager.get_session.return_value = Session()
        
        # Store in app config
        self.app.config['db_manager'] = self.db_manager
        
        # Mock email service to avoid sending real emails
        with patch('services.email_service.email_service') as mock_email:
            mock_email.is_configured.return_value = True
            mock_email.send_verification_email = Mock(return_value=True)
            
            # Register routes
            register_user_management_routes(self.app)
        
        # Create test client
        self.client = self.app.test_client()
        
        # Create app context
        self.app_context = self.app.app_context()
        self.app_context.push()
    
    def tearDown(self):
        """Clean up test fixtures"""
        self.app_context.pop()
    
    def test_register_route_get(self):
        """Test GET request to registration route"""
        response = self.client.get('/register')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Create Account', response.data)
        self.assertIn(b'Username', response.data)
        self.assertIn(b'Email Address', response.data)
    
    def test_register_route_post_invalid_data(self):
        """Test POST request to registration route with invalid data"""
        response = self.client.post('/register', data={
            'username': 'ab',  # Too short
            'email': 'invalid-email',
            'password': '123',  # Too short
            'confirm_password': '456',  # Doesn't match
            'data_processing_consent': False
        })
        
        self.assertEqual(response.status_code, 200)
        # Should return form with errors
        self.assertIn(b'Create Account', response.data)
    
    @patch('routes.user_management_routes.asyncio.new_event_loop')
    @patch('routes.user_management_routes.RequestScopedSessionManager')
    def test_register_route_post_valid_data(self, mock_session_manager, mock_event_loop):
        """Test POST request to registration route with valid data"""
        # Mock the session manager
        mock_session = Mock()
        mock_session_manager.return_value.session_scope.return_value.__enter__.return_value = mock_session
        mock_session_manager.return_value.session_scope.return_value.__exit__.return_value = None
        
        # Mock the event loop for async email sending
        mock_loop = Mock()
        mock_event_loop.return_value = mock_loop
        mock_loop.run_until_complete.return_value = (True, "Email sent")
        
        response = self.client.post('/register', data={
            'username': 'testuser',
            'email': 'test@gmail.com',
            'password': 'password123',
            'confirm_password': 'password123',
            'first_name': 'Test',
            'last_name': 'User',
            'data_processing_consent': True
        })
        
        # Should redirect to login page
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.location)
    
    def test_login_route_get(self):
        """Test GET request to login route"""
        response = self.client.get('/login')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Sign In', response.data)
        self.assertIn(b'Username or Email', response.data)
        self.assertIn(b'Password', response.data)
    
    def test_verify_email_invalid_token(self):
        """Test email verification with invalid token"""
        response = self.client.get('/verify-email/invalid_token')
        
        # Should redirect to login with error message
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.location)
    
    def test_forgot_password_route(self):
        """Test forgot password route"""
        response = self.client.get('/forgot-password')
        
        # Should redirect to login with info message (placeholder implementation)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.location)

if __name__ == '__main__':
    unittest.main()
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import unittest
import os
import sys
import tempfile
from unittest.mock import patch, MagicMock

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from database import DatabaseManager
from models import User, UserRole, PlatformConnection
from config import Config
from flask_login import login_user

class TestAddUserFunctionality(unittest.TestCase):
    """Test the add user functionality"""
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary database
        self.db_fd, self.db_path = tempfile.mkstemp()
        
        # Initialize database
        self.config = Config()
        self.config.storage.database_url = f'mysql+pymysql://{self.db_path}'
        self.db_manager = DatabaseManager(self.config)
        
        # Create tables
        from models import Base
        from sqlalchemy import text
        with self.db_manager.engine.connect() as conn:
            conn.execute(text('-- MySQL foreign keys are always enabled=ON'))
        Base.metadata.create_all(self.db_manager.engine)
        
        # Create admin user for testing
        session = self.db_manager.get_session()
        try:
            admin_user = User(
                username='admin',
                email='admin@test.com',
                role=UserRole.ADMIN,
                is_active=True
            )
            admin_user.set_password('admin123')
            session.add(admin_user)
            session.commit()
            self.admin_user_id = admin_user.id
            
            # Create a dummy platform connection
            platform_connection = PlatformConnection(
                user_id=admin_user.id,
                name='Test Platform',
                platform_type='pixelfed',
                instance_url='https://test.example.com',
                username='testuser',
                access_token='test_token',
                is_default=True,
                is_active=True
            )
            session.add(platform_connection)
            session.commit()
        finally:
            session.close()
        
        # Import app first
        from web_app import app
        
        # Patch multiple database manager references
        self.db_patcher = patch('web_app.db_manager', self.db_manager)
        self.request_session_patcher = patch('web_app.request_session_manager.db_manager', self.db_manager)
        self.db_patcher.start()
        self.request_session_patcher.start()
        
        # Configure app for testing
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = True
        app.config['db_manager'] = self.db_manager
        
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
    
    def tearDown(self):
        """Clean up test environment"""
        self.db_patcher.stop()
        self.request_session_patcher.stop()
        self.app_context.pop()
        os.close(self.db_fd)
        os.unlink(self.db_path)
    
    def login_as_admin(self):
        """Helper method to log in as admin"""
        # Set session data directly to simulate logged-in admin
        with self.client.session_transaction() as sess:
            sess['user_id'] = str(self.admin_user_id)
            sess['_user_id'] = str(self.admin_user_id)
            sess['_fresh'] = True
            sess['authenticated'] = True
            sess['platform_connection_id'] = 1
        return True
    
    def extract_csrf_token(self, html_data):
        """Extract CSRF token from HTML"""
        import re
        # Try multiple patterns for CSRF token extraction
        patterns = [
            rb'name="csrf_token"[^>]*value="([^"]+)"',
            rb'value="([^"]+)"[^>]*name="csrf_token"',
            rb'<input[^>]*name="csrf_token"[^>]*value="([^"]+)"[^>]*>',
            rb'<input[^>]*value="([^"]+)"[^>]*name="csrf_token"[^>]*>'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html_data)
            if match:
                return match.group(1).decode('utf-8')
        return None
    
    def get_csrf_token(self):
        """Get CSRF token from a form page"""
        # Get CSRF token from any page that has forms
        response = self.client.get('/user_management')
        if response.status_code == 200:
            token = self.extract_csrf_token(response.data)
            if token:
                return token
        
        # Fallback: get from login page
        response = self.client.get('/login')
        if response.status_code == 200:
            return self.extract_csrf_token(response.data)
        
        return None
    
    def test_user_management_page_has_add_button(self):
        """Test that the user management page has an add user button"""
        # Login as admin
        self.login_as_admin()
        
        # Get user management page
        response = self.client.get('/user_management')
        self.assertEqual(response.status_code, 200)
        
        # Check for add user button
        self.assertIn(b'Add User', response.data)
        self.assertIn(b'id="add-user-btn"', response.data)
    
    def test_add_user_modal_exists(self):
        """Test that the add user modal exists in the template"""
        # Login as admin
        self.login_as_admin()
        
        # Get user management page
        response = self.client.get('/user_management')
        self.assertEqual(response.status_code, 200)
        
        # Check for modal elements
        self.assertIn(b'addUserModal', response.data)
        self.assertIn(b'add-user-form', response.data)
        self.assertIn(b'Add New User', response.data)
    
    def test_add_user_api_success(self):
        """Test successful user creation via API"""
        # Login as admin
        self.login_as_admin()
        
        # Test data
        user_data = {
            'username': 'testuser',
            'email': 'test@test.com',
            'password': 'password123',
            'confirm_password': 'password123',
            'role': 'viewer',
            'is_active': 'on'
        }
        
        # Get CSRF token
        csrf_token = self.get_csrf_token()
        if csrf_token:
            user_data['csrf_token'] = csrf_token
        
        # Make API request
        response = self.client.post('/api/add_user', data=user_data)
        
        # Debug output
        print(f"API response status: {response.status_code}")
        if response.status_code == 302:
            print(f"Redirect location: {response.headers.get('Location', 'N/A')}")
        print(f"Response data: {response.data[:200]}")
        
        self.assertEqual(response.status_code, 200)
        
        # Check response
        data = response.get_json()
        self.assertTrue(data['success'])
        self.assertIn('created successfully', data['message'])
        self.assertEqual(data['user']['username'], 'testuser')
        self.assertEqual(data['user']['email'], 'test@test.com')
        self.assertEqual(data['user']['role'], 'viewer')
        self.assertTrue(data['user']['is_active'])
        
        # Verify user was created in database
        session = self.db_manager.get_session()
        try:
            user = session.query(User).filter_by(username='testuser').first()
            self.assertIsNotNone(user)
            self.assertEqual(user.email, 'test@test.com')
            self.assertEqual(user.role, UserRole.VIEWER)
            self.assertTrue(user.is_active)
            self.assertTrue(user.check_password('password123'))
        finally:
            session.close()
    
    def test_add_user_api_duplicate_username(self):
        """Test adding user with duplicate username"""
        # Login as admin
        self.login_as_admin()
        
        # Try to create user with existing username
        user_data = {
            'username': 'admin',  # Already exists
            'email': 'newadmin@test.com',
            'password': 'password123',
            'confirm_password': 'password123',
            'role': 'admin'
        }
        
        # Get CSRF token
        csrf_token = self.get_csrf_token()
        if csrf_token:
            user_data['csrf_token'] = csrf_token
        
        response = self.client.post('/api/add_user', data=user_data)
        self.assertEqual(response.status_code, 400)
        
        data = response.get_json()
        self.assertFalse(data['success'])
        self.assertIn('already exists', data['error'])
    
    def test_add_user_api_duplicate_email(self):
        """Test adding user with duplicate email"""
        # Login as admin
        self.login_as_admin()
        
        # Try to create user with existing email
        user_data = {
            'username': 'newuser',
            'email': 'admin@test.com',  # Already exists
            'password': 'password123',
            'confirm_password': 'password123',
            'role': 'viewer'
        }
        
        # Get CSRF token
        csrf_token = self.get_csrf_token()
        if csrf_token:
            user_data['csrf_token'] = csrf_token
        
        response = self.client.post('/api/add_user', data=user_data)
        self.assertEqual(response.status_code, 400)
        
        data = response.get_json()
        self.assertFalse(data['success'])
        self.assertIn('already registered', data['error'])
    
    def test_add_user_api_password_mismatch(self):
        """Test adding user with mismatched passwords"""
        # Login as admin
        self.login_as_admin()
        
        user_data = {
            'username': 'testuser',
            'email': 'test@test.com',
            'password': 'password123',
            'confirm_password': 'different123',  # Different password
            'role': 'viewer'
        }
        
        # Get CSRF token
        csrf_token = self.get_csrf_token()
        if csrf_token:
            user_data['csrf_token'] = csrf_token
        
        response = self.client.post('/api/add_user', data=user_data)
        self.assertEqual(response.status_code, 400)
        
        data = response.get_json()
        self.assertFalse(data['success'])
        self.assertIn('do not match', data['error'])
    
    def test_add_user_api_invalid_role(self):
        """Test adding user with invalid role"""
        # Login as admin
        self.login_as_admin()
        
        user_data = {
            'username': 'testuser',
            'email': 'test@test.com',
            'password': 'password123',
            'confirm_password': 'password123',
            'role': 'invalid_role'
        }
        
        # Get CSRF token
        csrf_token = self.get_csrf_token()
        if csrf_token:
            user_data['csrf_token'] = csrf_token
        
        response = self.client.post('/api/add_user', data=user_data)
        self.assertEqual(response.status_code, 400)
        
        data = response.get_json()
        self.assertFalse(data['success'])
        self.assertIn('Invalid role', data['error'])
    
    def test_add_user_api_missing_fields(self):
        """Test adding user with missing required fields"""
        # Login as admin
        self.login_as_admin()
        
        # Missing username
        user_data = {
            'email': 'test@test.com',
            'password': 'password123',
            'confirm_password': 'password123',
            'role': 'viewer'
        }
        
        # Get CSRF token
        csrf_token = self.get_csrf_token()
        if csrf_token:
            user_data['csrf_token'] = csrf_token
        
        response = self.client.post('/api/add_user', data=user_data)
        self.assertEqual(response.status_code, 400)
        
        data = response.get_json()
        self.assertFalse(data['success'])
        self.assertIn('required', data['error'])
    
    def test_add_user_api_short_password(self):
        """Test adding user with too short password"""
        # Login as admin
        self.login_as_admin()
        
        user_data = {
            'username': 'testuser',
            'email': 'test@test.com',
            'password': '123',  # Too short
            'confirm_password': '123',
            'role': 'viewer'
        }
        
        # Get CSRF token
        csrf_token = self.get_csrf_token()
        if csrf_token:
            user_data['csrf_token'] = csrf_token
        
        response = self.client.post('/api/add_user', data=user_data)
        self.assertEqual(response.status_code, 400)
        
        data = response.get_json()
        self.assertFalse(data['success'])
        self.assertIn('at least 6 characters', data['error'])
    
    def test_add_user_api_requires_admin_role(self):
        """Test that add user API requires admin role"""
        # Create non-admin user
        session = self.db_manager.get_session()
        try:
            viewer_user = User(
                username='viewer',
                email='viewer@test.com',
                role=UserRole.VIEWER,
                is_active=True
            )
            viewer_user.set_password('password123')
            session.add(viewer_user)
            session.commit()
        finally:
            session.close()
        
        # Get login page for CSRF token
        response = self.client.get('/login')
        csrf_token = self.extract_csrf_token(response.data)
        
        # Login as viewer
        login_data = {
            'username': 'viewer',
            'password': 'password123'
        }
        if csrf_token:
            login_data['csrf_token'] = csrf_token
        
        self.client.post('/login', data=login_data)
        
        # Try to add user
        user_data = {
            'username': 'testuser',
            'email': 'test@test.com',
            'password': 'password123',
            'confirm_password': 'password123',
            'role': 'viewer'
        }
        
        # Get CSRF token for API call
        csrf_token = self.get_csrf_token()
        if csrf_token:
            user_data['csrf_token'] = csrf_token
        
        response = self.client.post('/api/add_user', data=user_data)
        # Should redirect or return 403/401
        self.assertIn(response.status_code, [302, 401, 403])
    
    def test_add_user_api_requires_authentication(self):
        """Test that add user API requires authentication"""
        user_data = {
            'username': 'testuser',
            'email': 'test@test.com',
            'password': 'password123',
            'confirm_password': 'password123',
            'role': 'viewer'
        }
        
        response = self.client.post('/api/add_user', data=user_data)
        # Should return 403 due to CSRF or redirect to login
        self.assertIn(response.status_code, [302, 401, 403])
    
    def test_add_user_creates_all_roles(self):
        """Test creating users with different roles"""
        # Login as admin
        self.login_as_admin()
        
        roles_to_test = ['viewer', 'reviewer', 'moderator', 'admin']
        
        for i, role in enumerate(roles_to_test):
            user_data = {
                'username': f'user_{role}',
                'email': f'{role}@test.com',
                'password': 'password123',
                'confirm_password': 'password123',
                'role': role,
                'is_active': 'on'
            }
            
            # Get CSRF token for each request
            csrf_token = self.get_csrf_token()
            if csrf_token:
                user_data['csrf_token'] = csrf_token
            
            response = self.client.post('/api/add_user', data=user_data)
            self.assertEqual(response.status_code, 200)
            
            data = response.get_json()
            self.assertTrue(data['success'])
            self.assertEqual(data['user']['role'], role)
            
            # Verify in database
            session = self.db_manager.get_session()
            try:
                user = session.query(User).filter_by(username=f'user_{role}').first()
                self.assertIsNotNone(user)
                self.assertEqual(user.role.value, role)
            finally:
                session.close()

if __name__ == '__main__':
    unittest.main()
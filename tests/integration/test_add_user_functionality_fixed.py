#!/usr/bin/env python3

import unittest
import os
import sys
import tempfile
from unittest.mock import patch

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from database_manager_test_utils import patch_web_app_database_manager, create_mock_user, create_mock_platform_connection
from models import User, UserRole, PlatformConnection
from database import DatabaseManager
from config import Config

class TestAddUserFunctionalityFixed(unittest.TestCase):
    """Test the add user functionality with proper database manager patching"""
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary database
        self.db_fd, self.db_path = tempfile.mkstemp()
        
        # Create real database manager for test data
        self.config = Config()
        self.config.storage.database_url = f'sqlite:///{self.db_path}'
        self.real_db_manager = DatabaseManager(self.config)
        
        # Create tables
        from models import Base
        Base.metadata.create_all(self.real_db_manager.engine)
        
        # Create admin user for testing
        session = self.real_db_manager.get_session()
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
    
    def tearDown(self):
        """Clean up test environment"""
        os.close(self.db_fd)
        os.unlink(self.db_path)
    
    def test_add_user_api_success(self):
        """Test successful user creation via API"""
        
        # Create mock admin user and platform
        mock_admin = create_mock_user(user_id=1, username="admin", email="admin@test.com")
        mock_admin.role = UserRole.ADMIN
        mock_admin.check_password.return_value = True
        
        mock_platform = create_mock_platform_connection(connection_id=1, user_id=1)
        
        with patch_web_app_database_manager() as mock_db_manager:
            # Configure mock to return our test admin user
            mock_session = mock_db_manager.get_session.return_value
            mock_session.query.return_value.filter_by.return_value.first.return_value = mock_admin
            mock_session.query.return_value.get.return_value = mock_admin
            
            # Configure user creation
            mock_db_manager.create_user.return_value = 2  # New user ID
            
            # Import web_app after patching
            import web_app
            
            with web_app.app.test_client() as client:
                # Configure test app
                web_app.app.config['TESTING'] = True
                web_app.app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing
                
                # Login as admin
                with client.session_transaction() as sess:
                    sess['user_id'] = 1
                    sess['authenticated'] = True
                    sess['platform_connection_id'] = 1
                
                # Test data
                user_data = {
                    'username': 'testuser',
                    'email': 'test@example.com',
                    'password': 'password123',
                    'confirm_password': 'password123',
                    'role': 'viewer',
                    'is_active': 'on'
                }
                
                # Make API request
                response = client.post('/api/add_user', 
                                     data=user_data,
                                     content_type='application/x-www-form-urlencoded')
                
                # Check response
                self.assertEqual(response.status_code, 200)
                data = response.get_json()
                self.assertTrue(data['success'])
                self.assertIn('created successfully', data['message'])
    
    def test_add_user_requires_authentication(self):
        """Test that add user API requires authentication"""
        
        with patch_web_app_database_manager():
            import web_app
            
            with web_app.app.test_client() as client:
                web_app.app.config['TESTING'] = True
                
                user_data = {
                    'username': 'testuser',
                    'email': 'test@example.com',
                    'password': 'password123',
                    'confirm_password': 'password123',
                    'role': 'viewer'
                }
                
                response = client.post('/api/add_user', data=user_data)
                # Should redirect to login or return 401/403
                self.assertIn(response.status_code, [302, 401, 403])

def run_tests():
    """Run the fixed tests"""
    unittest.main(verbosity=2)

if __name__ == '__main__':
    run_tests()
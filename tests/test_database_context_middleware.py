# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import unittest
from unittest.mock import Mock, patch, MagicMock
from flask import Flask, g, session
from database_context_middleware import DatabaseContextMiddleware
from request_scoped_session_manager import RequestScopedSessionManager
from models import User, PlatformConnection
from sqlalchemy.orm.exc import DetachedInstanceError


class TestDatabaseContextMiddleware(unittest.TestCase):
    """Test cases for DatabaseContextMiddleware"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'test-secret-key'
        self.app.config['TESTING'] = True
        
        # Mock session manager
        self.mock_session_manager = Mock(spec=RequestScopedSessionManager)
        self.mock_session_manager.get_session_info.return_value = {
            'has_request_context': True,
            'has_session': True,
            'session_active': True
        }
        
        # Create middleware
        self.middleware = DatabaseContextMiddleware(self.app, self.mock_session_manager)
        
        # Create test client
        self.client = self.app.test_client()
    
    def test_middleware_initialization(self):
        """Test that middleware initializes correctly"""
        self.assertEqual(self.middleware.app, self.app)
        self.assertEqual(self.middleware.session_manager, self.mock_session_manager)
    
    def test_before_request_handler(self):
        """Test that before_request handler initializes session"""
        with self.app.test_request_context():
            # Trigger before_request handlers
            self.app.preprocess_request()
            
            # Verify session manager was called
            self.mock_session_manager.get_request_session.assert_called_once()
            self.mock_session_manager.get_session_info.assert_called_once()
    
    def test_teardown_request_handler_normal(self):
        """Test teardown_request handler with normal completion"""
        with self.app.test_request_context():
            # Manually call teardown handler (normal case)
            for handler in self.app.teardown_request_funcs[None]:
                handler(None)
            
            # Verify session cleanup was called
            self.mock_session_manager.close_request_session.assert_called_once()
    
    def test_teardown_request_handler_with_exception(self):
        """Test teardown_request handler with exception"""
        mock_session = Mock()
        self.mock_session_manager.get_request_session.return_value = mock_session
        
        with self.app.test_request_context():
            # Set up mock session in g
            g.db_session = mock_session
            
            # Simulate request with exception
            exception = Exception("Test exception")
            
            # Manually call teardown handler
            for handler in self.app.teardown_request_funcs[None]:
                handler(exception)
            
            # Verify rollback was called
            mock_session.rollback.assert_called_once()
            self.mock_session_manager.close_request_session.assert_called_once()
    
    def test_safe_user_dict_creation(self):
        """Test safe user dictionary creation"""
        # Mock user object
        mock_user = Mock()
        mock_user.id = 1
        mock_user.username = 'testuser'
        mock_user.email = 'test@example.com'
        mock_user.role = 'user'
        mock_user.is_active = True
        mock_user.last_login = None
        
        result = self.middleware._get_safe_user_dict(mock_user)
        
        expected = {
            'id': 1,
            'username': 'testuser',
            'email': 'test@example.com',
            'role': 'user',
            'is_active': True,
            'last_login': None
        }
        
        self.assertEqual(result, expected)
    
    def test_safe_user_dict_with_detached_instance_error(self):
        """Test safe user dictionary creation with DetachedInstanceError"""
        # Create a mock user that simulates DetachedInstanceError behavior
        class MockUserWithError:
            def __init__(self):
                self._user_id = 1
            
            @property
            def id(self):
                raise DetachedInstanceError()
            
            @property
            def username(self):
                raise DetachedInstanceError()
            
            @property
            def email(self):
                raise DetachedInstanceError()
            
            @property
            def role(self):
                raise DetachedInstanceError()
            
            @property
            def is_active(self):
                raise DetachedInstanceError()
            
            @property
            def last_login(self):
                raise DetachedInstanceError()
        
        mock_user = MockUserWithError()
        result = self.middleware._get_safe_user_dict(mock_user)
        
        # Should return fallback data
        self.assertEqual(result['id'], 1)
        self.assertEqual(result['username'], 'Unknown')
    
    def test_platform_to_dict_conversion(self):
        """Test platform to dictionary conversion"""
        # Mock platform object
        mock_platform = Mock(spec=PlatformConnection)
        mock_platform.id = 1
        mock_platform.name = 'Test Platform'
        mock_platform.platform_type = 'mastodon'
        mock_platform.instance_url = 'https://example.com'
        mock_platform.username = 'testuser'
        mock_platform.is_default = True
        mock_platform.is_active = True
        mock_platform.created_at = None
        mock_platform.last_used = None
        
        result = self.middleware._platform_to_dict(mock_platform)
        
        expected = {
            'id': 1,
            'name': 'Test Platform',
            'platform_type': 'mastodon',
            'instance_url': 'https://example.com',
            'username': 'testuser',
            'is_default': True,
            'is_active': True,
            'created_at': None,
            'last_used': None
        }
        
        self.assertEqual(result, expected)
    
    def test_platform_to_dict_with_detached_instance_error(self):
        """Test platform to dictionary conversion with DetachedInstanceError"""
        # Create a mock platform that simulates DetachedInstanceError behavior
        class MockPlatformWithError:
            @property
            def id(self):
                raise DetachedInstanceError()
            
            @property
            def name(self):
                return 'Test Platform'  # This one works
            
            @property
            def platform_type(self):
                raise DetachedInstanceError()
            
            @property
            def instance_url(self):
                raise DetachedInstanceError()
            
            @property
            def username(self):
                raise DetachedInstanceError()
            
            @property
            def is_default(self):
                raise DetachedInstanceError()
            
            @property
            def is_active(self):
                raise DetachedInstanceError()
            
            @property
            def created_at(self):
                raise DetachedInstanceError()
            
            @property
            def last_used(self):
                raise DetachedInstanceError()
        
        mock_platform = MockPlatformWithError()
        result = self.middleware._platform_to_dict(mock_platform)
        
        # Should return fallback data
        self.assertEqual(result['name'], 'Test Platform')
        self.assertEqual(result['platform_type'], 'unknown')
    
    @patch('database_context_middleware.current_user')
    def test_template_context_unauthenticated_user(self, mock_current_user):
        """Test template context creation for unauthenticated user"""
        mock_current_user.is_authenticated = False
        
        result = self.middleware._create_safe_template_context()
        
        expected = {
            'current_user_safe': None,
            'user_platforms': [],
            'active_platform': None,
            'platform_count': 0,
            'template_error': False,
            'session_context': None
        }
        
        self.assertEqual(result, expected)
    
    @patch('database_context_middleware.current_user')
    def test_template_context_authenticated_user(self, mock_current_user):
        """Test template context creation for authenticated user"""
        mock_current_user.is_authenticated = True
        mock_current_user.id = 1
        mock_current_user.username = 'testuser'
        mock_current_user.platforms = []
        
        # Mock the methods
        with patch.object(self.middleware, '_get_safe_user_dict') as mock_get_user_dict, \
             patch.object(self.middleware, '_get_safe_user_platforms') as mock_get_platforms, \
             patch.object(self.middleware, '_get_session_context_info') as mock_get_context:
            
            mock_get_user_dict.return_value = {'id': 1, 'username': 'testuser'}
            mock_get_platforms.return_value = {
                'user_platforms': [],
                'active_platform': None,
                'platform_count': 0
            }
            mock_get_context.return_value = {'test': 'context'}
            
            result = self.middleware._create_safe_template_context()
            
            self.assertEqual(result['current_user_safe'], {'id': 1, 'username': 'testuser'})
            self.assertEqual(result['user_platforms'], [])
            self.assertEqual(result['session_context'], {'test': 'context'})
    
    def test_load_platforms_from_database(self):
        """Test loading platforms directly from database"""
        # Mock session and query
        mock_session = Mock()
        mock_platform = Mock(spec=PlatformConnection)
        mock_platform.id = 1
        mock_platform.name = 'Test Platform'
        mock_platform.is_default = True
        
        mock_query = Mock()
        mock_query.filter_by.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [mock_platform]
        
        mock_session.query.return_value = mock_query
        self.mock_session_manager.get_request_session.return_value = mock_session
        
        with patch.object(self.middleware, '_platform_to_dict') as mock_to_dict:
            mock_to_dict.return_value = {'id': 1, 'name': 'Test Platform', 'is_default': True}
            
            result = self.middleware._load_platforms_from_database(1)
            
            self.assertEqual(result['platform_count'], 1)
            self.assertEqual(result['active_platform'], {'id': 1, 'name': 'Test Platform', 'is_default': True})
    
    def test_get_middleware_status(self):
        """Test middleware status reporting"""
        self.mock_session_manager.is_session_active.return_value = True
        
        result = self.middleware.get_middleware_status()
        
        expected_keys = [
            'middleware_active',
            'session_manager_active',
            'session_info',
            'app_name',
            'handlers_registered'
        ]
        
        for key in expected_keys:
            self.assertIn(key, result)
        
        self.assertTrue(result['middleware_active'])
        self.assertTrue(result['handlers_registered'])
    
    def test_handle_detached_instance_error(self):
        """Test DetachedInstanceError handling"""
        error = DetachedInstanceError()
        
        # Mock current_user with refresh_platforms method
        mock_user = Mock()
        mock_user.is_authenticated = True
        mock_user.refresh_platforms = Mock()
        
        with patch('database_context_middleware.current_user', mock_user):
            self.middleware.handle_detached_instance_error(error, "test_context")
            
            # Verify refresh_platforms was called
            mock_user.refresh_platforms.assert_called_once()


if __name__ == '__main__':
    unittest.main()
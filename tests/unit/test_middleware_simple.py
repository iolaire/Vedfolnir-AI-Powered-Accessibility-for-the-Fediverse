# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Simple tests for middleware platform context application
"""

import unittest
import tempfile
import os
from unittest.mock import patch, MagicMock
from flask import g

from config import Config
from database import DatabaseManager
from models import User, PlatformConnection, UserSession, UserRole
from unified_session_manager import UnifiedSessionManager as SessionManager, get_current_platform_context, get_current_platform
from redis_session_middleware import get_current_session_context, get_current_session_id
from web_app import app

class TestMiddlewareSimple(unittest.TestCase):
    """Test middleware applies context to all requests - simplified version"""
    
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
    
    def test_middleware_class_initialization(self):
        """Test that DatabaseSessionMiddleware can be initialized"""
        from unified_session_manager import UnifiedSessionManager
        from session_cookie_manager import create_session_cookie_manager
        
        unified_session_manager = UnifiedSessionManager(self.db_manager)
        cookie_manager = create_session_cookie_manager({})
        
        middleware = DatabaseSessionMiddleware(app, unified_session_manager, cookie_manager)
        self.assertIsNotNone(middleware)
        self.assertEqual(middleware.session_manager, unified_session_manager)
    
    def test_get_current_platform_context_utility(self):
        """Test the get_current_platform_context utility function"""
        with app.test_request_context():
            # Test without platform context set
            context = get_current_platform_context()
            self.assertIsNone(context)
            
            # Set platform context in g
            test_context = {
                'user_id': self.user_id,
                'platform_connection_id': self.platform_id,
                'session_id': 'test-session'
            }
            g.platform_context = test_context
            
            # Test with platform context set
            context = get_current_platform_context()
            self.assertEqual(context, test_context)
    
    def test_get_current_platform_utility(self):
        """Test the get_current_platform utility function"""
        with app.test_request_context():
            # Test without platform context set
            platform = get_current_platform()
            self.assertIsNone(platform)
            
            # Set platform context in g
            test_context = {
                'user_id': self.user_id,
                'platform_connection_id': self.platform_id,
                'platform_connection': self.test_platform,
                'session_id': 'test-session'
            }
            g.platform_context = test_context
            
            # Test with platform context set
            platform = get_current_platform()
            self.assertEqual(platform, self.test_platform)
    
    def test_middleware_before_request_method(self):
        """Test the middleware before_request method directly"""
        from unified_session_manager import UnifiedSessionManager
        from session_cookie_manager import create_session_cookie_manager
        
        unified_session_manager = UnifiedSessionManager(self.db_manager)
        cookie_manager = create_session_cookie_manager({})
        middleware = DatabaseSessionMiddleware(app, unified_session_manager, cookie_manager)
        
        with app.test_request_context():
            # Call before_request method
            result = middleware.before_request()
            
            # Should not raise an exception
            self.assertIsNone(result)
            
            # Should set g.session_context to None when no session
            self.assertIsNone(getattr(g, 'session_context', None))
    
    def test_middleware_after_request_method(self):
        """Test the middleware after_request method directly"""
        from unified_session_manager import UnifiedSessionManager
        from session_cookie_manager import create_session_cookie_manager
        
        unified_session_manager = UnifiedSessionManager(self.db_manager)
        cookie_manager = create_session_cookie_manager({})
        middleware = DatabaseSessionMiddleware(app, unified_session_manager, cookie_manager)
        
        with app.test_request_context():
            # Set some context
            g.session_context = {'test': 'context'}
            
            # Mock response
            mock_response = MagicMock()
            
            # Call after_request method
            result = middleware.after_request(mock_response)
            
            # Should return the response
            self.assertEqual(result, mock_response)
            
            # Should clean up context
            self.assertIsNone(getattr(g, 'session_context', None))
    
    def test_middleware_handles_session_manager_errors(self):
        """Test that middleware handles session manager errors gracefully"""
        from session_cookie_manager import create_session_cookie_manager
        
        # Create middleware with mocked session manager that raises errors
        mock_session_manager = MagicMock()
        mock_session_manager.get_session_context.side_effect = Exception("Session error")
        cookie_manager = create_session_cookie_manager({})
        
        middleware = DatabaseSessionMiddleware(app, mock_session_manager, cookie_manager)
        
        with app.test_request_context():
            # Mock cookie manager to return a session ID
            with patch.object(cookie_manager, 'get_session_id_from_cookie', return_value='test-session-id'):
                # Call before_request method - should not raise exception
                result = middleware.before_request()
                
                # Should not raise an exception
                self.assertIsNone(result)
                
                # Context should be None due to error
                self.assertIsNone(getattr(g, 'session_context', None))
    
    def test_middleware_skips_static_and_health_endpoints(self):
        """Test that middleware skips processing for certain endpoints"""
        from unified_session_manager import UnifiedSessionManager
        from session_cookie_manager import create_session_cookie_manager
        
        unified_session_manager = UnifiedSessionManager(self.db_manager)
        cookie_manager = create_session_cookie_manager({})
        middleware = DatabaseSessionMiddleware(app, unified_session_manager, cookie_manager)
        
        with app.test_request_context():
            # Mock request endpoint as 'static'
            with patch('database_session_middleware.request') as mock_request:
                mock_request.endpoint = 'static'
                
                # Call before_request method
                result = middleware.before_request()
                
                # Should return early (None) and not set context
                self.assertIsNone(result)
                self.assertIsNone(getattr(g, 'session_context', None))
            
            # Mock request endpoint as 'health'
            with patch('database_session_middleware.request') as mock_request:
                mock_request.endpoint = 'health'
                
                # Call before_request method
                result = middleware.before_request()
                
                # Should return early (None) and not set context
                self.assertIsNone(result)
                self.assertIsNone(getattr(g, 'session_context', None))
    
    def test_middleware_sets_session_manager_in_g(self):
        """Test that middleware sets session manager in g"""
        from unified_session_manager import UnifiedSessionManager
        from session_cookie_manager import create_session_cookie_manager
        
        unified_session_manager = UnifiedSessionManager(self.db_manager)
        cookie_manager = create_session_cookie_manager({})
        middleware = DatabaseSessionMiddleware(app, unified_session_manager, cookie_manager)
        
        with app.test_request_context():
            # Call before_request method
            middleware.before_request()
            
            # Should set session manager in g
            self.assertEqual(getattr(g, 'session_manager', None), unified_session_manager)
    
    def test_middleware_integration_with_existing_routes(self):
        """Test that middleware works with existing routes"""
        # Test with health endpoint (which exists in the app)
        response = self.client.get('/health')
        
        # Should get a response without errors
        self.assertEqual(response.status_code, 200)
        
        # The middleware should have processed this request without errors
        # (even though it skips processing for health endpoint)
    
    def test_session_context_functions_work_correctly(self):
        """Test that session context utility functions work as expected"""
        from unified_session_manager import UnifiedSessionManager
        from redis_session_middleware import get_current_session_context
        
        # Create unified session manager
        unified_session_manager = UnifiedSessionManager(self.db_manager)
        
        # Create a real session
        session_id = unified_session_manager.create_session(self.user_id, self.platform_id)
        
        # Test that session manager can get context
        context = unified_session_manager.get_session_context(session_id)
        self.assertIsNotNone(context)
        self.assertEqual(context['user_id'], self.user_id)
        self.assertEqual(context['platform_connection_id'], self.platform_id)
        
        # Test utility functions with mocked Flask context
        with app.test_request_context():
            # Set the context in g (simulating what middleware would do)
            g.session_context = context
            
            # Test get_current_session_context
            current_context = get_current_session_context()
            self.assertEqual(current_context, context)
            
            # Test get_current_platform_context (should work with session context)
            platform_context = get_current_platform_context()
            self.assertIsNotNone(platform_context)
            
            # Test get_current_platform
            current_platform = get_current_platform()
            self.assertEqual(current_platform.id, self.platform_id)
            self.assertEqual(current_platform.name, 'Test Platform')

if __name__ == '__main__':
    unittest.main()
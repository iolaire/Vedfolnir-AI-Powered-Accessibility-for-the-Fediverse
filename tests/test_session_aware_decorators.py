# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import unittest
from unittest.mock import Mock, patch, MagicMock, PropertyMock
from flask import Flask, g, url_for
from flask_login import LoginManager, login_user
from sqlalchemy.orm.exc import DetachedInstanceError
from sqlalchemy.exc import SQLAlchemyError

from session_aware_decorators import (
    with_db_session,
    require_platform_context,
    handle_detached_instance_error,
    ensure_user_session_attachment
)


class TestSessionAwareDecorators(unittest.TestCase):
    
    def setUp(self):
        """Set up test Flask app and mocks"""
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'test-secret-key'
        self.app.config['TESTING'] = True
        
        # Set up Flask-Login
        self.login_manager = LoginManager()
        self.login_manager.init_app(self.app)
        
        # Add user loader to prevent Flask-Login errors
        @self.login_manager.user_loader
        def load_user(user_id):
            return None
        
        # Mock session manager
        self.mock_session_manager = Mock()
        self.mock_session = Mock()
        self.mock_session_manager.get_request_session.return_value = self.mock_session
        self.app.request_session_manager = self.mock_session_manager
        
        # Mock user
        self.mock_user = Mock()
        self.mock_user.is_authenticated = True
        self.mock_user.id = 1
        self.mock_user._user_id = 1
        self.mock_user._session_manager = self.mock_session_manager
        self.mock_user._user = Mock()
        self.mock_user._invalidate_cache = Mock()
        self.mock_user.platforms = [Mock()]
        self.mock_user.get_active_platform.return_value = Mock()
        
        # Add test routes
        @self.app.route('/test')
        @with_db_session
        def test_route():
            return 'success'
        
        @self.app.route('/test-platform')
        @require_platform_context
        def test_platform_route():
            return 'platform-success'
        
        @self.app.route('/test-error')
        @handle_detached_instance_error
        def test_error_route():
            raise DetachedInstanceError()
        
        @self.app.route('/test-user')
        @ensure_user_session_attachment
        def test_user_route():
            return 'user-success'
        
        @self.app.route('/login')
        def login():
            return 'login'
        
        @self.app.route('/index')
        def index():
            return 'index'
        
        @self.app.route('/platform_management')
        def platform_management():
            return 'platform_management'
        
        @self.app.route('/first_time_setup')
        def first_time_setup():
            return 'first_time_setup'
        
        self.client = self.app.test_client()
    
    @patch('session_aware_decorators.current_user')
    def test_with_db_session_success(self, mock_current_user):
        """Test with_db_session decorator with successful execution"""
        mock_current_user.is_authenticated = True
        mock_current_user.id = 1
        mock_current_user._user_id = 1
        mock_current_user._session_manager = self.mock_session_manager
        mock_current_user._user = Mock()
        mock_current_user._invalidate_cache = Mock()
        
        # Mock session contains user
        self.mock_session.__contains__ = Mock(return_value=True)
        
        with self.app.test_request_context():
            response = self.client.get('/test')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data.decode(), 'success')
    
    @patch('session_aware_decorators.current_user')
    def test_with_db_session_user_reattachment(self, mock_current_user):
        """Test with_db_session decorator reattaches detached user"""
        mock_current_user.is_authenticated = True
        mock_current_user.id = 1
        mock_current_user._user_id = 1
        mock_current_user._session_manager = self.mock_session_manager
        mock_current_user._user = Mock()
        mock_current_user._invalidate_cache = Mock()
        
        # Mock session does not contain user (detached)
        self.mock_session.__contains__ = Mock(return_value=False)
        
        with self.app.test_request_context():
            response = self.client.get('/test')
            self.assertEqual(response.status_code, 200)
            self.mock_session_manager.ensure_session_attachment.assert_called_once()
            mock_current_user._invalidate_cache.assert_called_once()
    
    @patch('session_aware_decorators.current_user')
    def test_with_db_session_detached_error(self, mock_current_user):
        """Test with_db_session decorator handles DetachedInstanceError"""
        mock_current_user.configure_mock(is_authenticated=True)
        type(mock_current_user).id = PropertyMock(side_effect=DetachedInstanceError())
        
        with self.app.test_request_context():
            response = self.client.get('/test')
            self.assertEqual(response.status_code, 302)  # Redirect
            self.assertIn('/login', response.location)
    
    @patch('session_aware_decorators.current_user')
    def test_with_db_session_no_session_manager(self, mock_current_user):
        """Test with_db_session decorator when session manager is missing"""
        mock_current_user.is_authenticated = True
        
        # Remove session manager
        delattr(self.app, 'request_session_manager')
        
        with self.app.test_request_context():
            response = self.client.get('/test')
            self.assertEqual(response.status_code, 302)  # Redirect to login
    
    @patch('session_aware_decorators.current_user')
    def test_require_platform_context_success(self, mock_current_user):
        """Test require_platform_context decorator with valid platform"""
        mock_current_user.is_authenticated = True
        mock_current_user.id = 1
        mock_current_user._user_id = 1
        mock_current_user._session_manager = self.mock_session_manager
        mock_current_user._user = Mock()
        mock_current_user._invalidate_cache = Mock()
        mock_current_user.platforms = [Mock()]
        mock_current_user.get_active_platform.return_value = Mock()
        
        self.mock_session.__contains__ = Mock(return_value=True)
        
        with self.app.test_request_context():
            response = self.client.get('/test-platform')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data.decode(), 'platform-success')
    
    @patch('session_aware_decorators.current_user')
    def test_require_platform_context_unauthenticated(self, mock_current_user):
        """Test require_platform_context decorator with unauthenticated user"""
        mock_current_user.is_authenticated = False
        
        with self.app.test_request_context():
            response = self.client.get('/test-platform')
            self.assertEqual(response.status_code, 302)  # Redirect to login
    
    @patch('session_aware_decorators.current_user')
    def test_require_platform_context_no_platforms(self, mock_current_user):
        """Test require_platform_context decorator when user has no platforms"""
        mock_current_user.is_authenticated = True
        mock_current_user.id = 1
        mock_current_user._user_id = 1
        mock_current_user._session_manager = self.mock_session_manager
        mock_current_user._user = Mock()
        mock_current_user._invalidate_cache = Mock()
        mock_current_user.platforms = []  # No platforms
        
        self.mock_session.__contains__ = Mock(return_value=True)
        
        with self.app.test_request_context():
            response = self.client.get('/test-platform')
            self.assertEqual(response.status_code, 302)  # Redirect to setup
            self.assertIn('/first_time_setup', response.location)
    
    @patch('session_aware_decorators.current_user')
    def test_require_platform_context_no_active_platform(self, mock_current_user):
        """Test require_platform_context decorator when no active platform"""
        # Use regular Mock instead of AsyncMock
        mock_current_user.configure_mock(
            is_authenticated=True,
            id=1,
            _user_id=1,
            _session_manager=self.mock_session_manager,
            _user=Mock(),
            _invalidate_cache=Mock(),
            platforms=[Mock()]
        )
        mock_current_user.get_active_platform.return_value = None  # No active platform
        
        self.mock_session.__contains__ = Mock(return_value=True)
        
        with self.app.test_request_context():
            response = self.client.get('/test-platform')
            self.assertEqual(response.status_code, 302)  # Redirect to platform management
            self.assertIn('/platform_management', response.location)
    
    @patch('session_aware_decorators.current_user')
    def test_require_platform_context_detached_platforms(self, mock_current_user):
        """Test require_platform_context decorator handles detached platforms"""
        mock_current_user.configure_mock(
            is_authenticated=True,
            id=1,
            _user_id=1,
            _session_manager=self.mock_session_manager,
            _user=Mock(),
            _invalidate_cache=Mock()
        )
        
        # Create a property that raises DetachedInstanceError
        type(mock_current_user).platforms = PropertyMock(side_effect=DetachedInstanceError())
        
        self.mock_session.__contains__ = Mock(return_value=True)
        
        with self.app.test_request_context():
            response = self.client.get('/test-platform')
            self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_handle_detached_instance_error_decorator(self):
        """Test handle_detached_instance_error decorator catches and handles errors"""
        with self.app.test_request_context():
            response = self.client.get('/test-error')
            self.assertEqual(response.status_code, 302)  # Redirect
    
    @patch('session_aware_decorators.current_user')
    def test_handle_detached_instance_error_with_cache_invalidation(self, mock_current_user):
        """Test handle_detached_instance_error decorator invalidates cache"""
        mock_current_user.is_authenticated = True
        mock_current_user._invalidate_cache = Mock()
        
        # Create a route that raises DetachedInstanceError
        @self.app.route('/test-error-cache')
        @handle_detached_instance_error
        def test_error_cache_route():
            raise DetachedInstanceError()
        
        with self.app.test_request_context():
            response = self.client.get('/test-error-cache')
            self.assertEqual(response.status_code, 302)
            mock_current_user._invalidate_cache.assert_called_once()
    
    @patch('session_aware_decorators.current_user')
    def test_ensure_user_session_attachment_success(self, mock_current_user):
        """Test ensure_user_session_attachment decorator with authenticated user"""
        mock_current_user.is_authenticated = True
        mock_current_user.id = 1
        mock_current_user._session_manager = self.mock_session_manager
        mock_current_user._user = Mock()
        mock_current_user._invalidate_cache = Mock()
        
        self.mock_session.__contains__ = Mock(return_value=True)
        
        with self.app.test_request_context():
            response = self.client.get('/test-user')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data.decode(), 'user-success')
    
    @patch('session_aware_decorators.current_user')
    def test_ensure_user_session_attachment_detached_user(self, mock_current_user):
        """Test ensure_user_session_attachment decorator handles detached user"""
        mock_current_user.configure_mock(is_authenticated=True)
        # Create a property that raises DetachedInstanceError
        type(mock_current_user).id = PropertyMock(side_effect=DetachedInstanceError())
        
        with self.app.test_request_context():
            response = self.client.get('/test-user')
            self.assertEqual(response.status_code, 302)  # Redirect to login
    
    @patch('session_aware_decorators.current_user')
    def test_ensure_user_session_attachment_unauthenticated(self, mock_current_user):
        """Test ensure_user_session_attachment decorator with unauthenticated user"""
        mock_current_user.is_authenticated = False
        
        with self.app.test_request_context():
            response = self.client.get('/test-user')
            self.assertEqual(response.status_code, 200)  # Should proceed normally
    
    @patch('session_aware_decorators.current_user')
    def test_ensure_user_session_attachment_reattachment(self, mock_current_user):
        """Test ensure_user_session_attachment decorator reattaches user"""
        mock_current_user.is_authenticated = True
        mock_current_user.id = 1
        mock_current_user._session_manager = self.mock_session_manager
        mock_current_user._user = Mock()
        mock_current_user._invalidate_cache = Mock()
        
        # Mock session does not contain user
        self.mock_session.__contains__ = Mock(return_value=False)
        
        with self.app.test_request_context():
            response = self.client.get('/test-user')
            self.assertEqual(response.status_code, 200)
            self.mock_session_manager.ensure_session_attachment.assert_called_once()
            mock_current_user._invalidate_cache.assert_called_once()
    
    def test_decorator_stacking(self):
        """Test that decorators can be stacked properly"""
        @self.app.route('/test-stacked')
        @handle_detached_instance_error
        @with_db_session
        def test_stacked_route():
            return 'stacked-success'
        
        with self.app.test_request_context():
            response = self.client.get('/test-stacked')
            # Should handle any errors gracefully
            self.assertIn(response.status_code, [200, 302])
    
    @patch('session_aware_decorators.current_user')
    def test_sqlalchemy_error_handling(self, mock_current_user):
        """Test that decorators handle general SQLAlchemy errors"""
        mock_current_user.configure_mock(is_authenticated=True)
        type(mock_current_user).id = PropertyMock(side_effect=SQLAlchemyError())
        
        with self.app.test_request_context():
            response = self.client.get('/test')
            self.assertEqual(response.status_code, 302)  # Should redirect
    
    @patch('session_aware_decorators.logger')
    def test_logging_on_errors(self, mock_logger):
        """Test that errors are properly logged"""
        with self.app.test_request_context():
            response = self.client.get('/test-error')
            self.assertEqual(response.status_code, 302)
            mock_logger.warning.assert_called()


if __name__ == '__main__':
    unittest.main()
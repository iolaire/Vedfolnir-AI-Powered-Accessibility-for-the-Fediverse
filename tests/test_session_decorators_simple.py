# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import unittest
from unittest.mock import Mock, patch, MagicMock
from flask import Flask, g
from flask_login import LoginManager
from sqlalchemy.orm.exc import DetachedInstanceError
from sqlalchemy.exc import SQLAlchemyError

from session_aware_decorators import (
    with_db_session,
    require_platform_context,
    handle_detached_instance_error,
    ensure_user_session_attachment
)


class MockUser:
    """Simple mock user class to avoid AsyncMock issues"""
    def __init__(self, authenticated=True, user_id=1, platforms=None, active_platform=None, raise_detached=False):
        self.is_authenticated = authenticated
        self._id = user_id
        self._user_id = user_id
        self._session_manager = Mock()
        self._user = Mock()
        self._invalidate_cache = Mock()
        self.platforms = platforms or []
        self._active_platform = active_platform
        self._raise_detached = raise_detached
    
    @property
    def id(self):
        if self._raise_detached:
            raise DetachedInstanceError()
        return self._id
    
    def get_active_platform(self):
        return self._active_platform


class TestSessionDecoratorsSimple(unittest.TestCase):
    
    def setUp(self):
        """Set up test Flask app"""
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'test-secret-key'
        self.app.config['TESTING'] = True
        
        # Set up Flask-Login
        self.login_manager = LoginManager()
        self.login_manager.init_app(self.app)
        
        @self.login_manager.user_loader
        def load_user(user_id):
            return None
        
        # Mock session manager
        self.mock_session_manager = Mock()
        self.mock_session = Mock()
        self.mock_session.__contains__ = Mock(return_value=True)
        self.mock_session_manager.get_request_session.return_value = self.mock_session
        self.mock_session_manager.ensure_session_attachment = Mock(side_effect=lambda x: x)
        self.app.request_session_manager = self.mock_session_manager
        
        # Add test routes
        @self.app.route('/test')
        @with_db_session
        def test_route():
            return 'success'
        
        @self.app.route('/test-platform')
        @require_platform_context
        def test_platform_route():
            return 'platform-success'
        
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
    
    def test_with_db_session_success(self):
        """Test with_db_session decorator with authenticated user"""
        mock_user = MockUser()
        
        with patch('session_aware_decorators.current_user', mock_user):
            with self.app.test_request_context():
                response = self.client.get('/test')
                self.assertEqual(response.status_code, 200)
    
    def test_with_db_session_detached_error(self):
        """Test with_db_session decorator handles DetachedInstanceError"""
        mock_user = MockUser(raise_detached=True)
        
        with patch('session_aware_decorators.current_user', mock_user):
            with self.app.test_request_context():
                response = self.client.get('/test')
                self.assertEqual(response.status_code, 302)  # Should redirect
    
    def test_require_platform_context_success(self):
        """Test require_platform_context decorator with valid platform"""
        mock_platform = Mock()
        mock_user = MockUser(platforms=[mock_platform], active_platform=mock_platform)
        self.mock_session.__contains__ = Mock(return_value=True)
        
        with patch('session_aware_decorators.current_user', mock_user):
            with self.app.test_request_context():
                response = self.client.get('/test-platform')
                self.assertEqual(response.status_code, 200)
    
    def test_require_platform_context_no_platforms(self):
        """Test require_platform_context decorator when user has no platforms"""
        mock_user = MockUser(platforms=[])
        self.mock_session.__contains__ = Mock(return_value=True)
        
        with patch('session_aware_decorators.current_user', mock_user):
            with self.app.test_request_context():
                response = self.client.get('/test-platform')
                self.assertEqual(response.status_code, 302)  # Should redirect
                self.assertIn('/first_time_setup', response.location)
    
    def test_require_platform_context_no_active_platform(self):
        """Test require_platform_context decorator when no active platform"""
        mock_platform = Mock()
        mock_user = MockUser(platforms=[mock_platform], active_platform=None)
        self.mock_session.__contains__ = Mock(return_value=True)
        
        with patch('session_aware_decorators.current_user', mock_user):
            with self.app.test_request_context():
                response = self.client.get('/test-platform')
                self.assertEqual(response.status_code, 302)  # Should redirect
                self.assertIn('/platform_management', response.location)
    
    def test_require_platform_context_unauthenticated(self):
        """Test require_platform_context decorator with unauthenticated user"""
        mock_user = MockUser(authenticated=False)
        
        with patch('session_aware_decorators.current_user', mock_user):
            with self.app.test_request_context():
                response = self.client.get('/test-platform')
                self.assertEqual(response.status_code, 302)  # Should redirect to login
    
    def test_handle_detached_instance_error(self):
        """Test handle_detached_instance_error decorator"""
        @self.app.route('/test-error')
        @handle_detached_instance_error
        def test_error_route():
            raise DetachedInstanceError()
        
        with self.app.test_request_context():
            response = self.client.get('/test-error')
            self.assertEqual(response.status_code, 302)  # Should redirect
    
    def test_ensure_user_session_attachment_success(self):
        """Test ensure_user_session_attachment decorator"""
        mock_user = MockUser()
        self.mock_session.__contains__ = Mock(return_value=True)
        
        @self.app.route('/test-user')
        @ensure_user_session_attachment
        def test_user_route():
            return 'user-success'
        
        with patch('session_aware_decorators.current_user', mock_user):
            with self.app.test_request_context():
                response = self.client.get('/test-user')
                self.assertEqual(response.status_code, 200)
    
    def test_missing_session_manager(self):
        """Test behavior when session manager is missing"""
        # Remove session manager
        delattr(self.app, 'request_session_manager')
        
        mock_user = MockUser()
        
        with patch('session_aware_decorators.current_user', mock_user):
            with self.app.test_request_context():
                response = self.client.get('/test')
                self.assertEqual(response.status_code, 302)  # Should redirect to login


if __name__ == '__main__':
    unittest.main()
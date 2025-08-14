# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import unittest
from unittest.mock import Mock, patch, MagicMock
from flask import Flask, g, redirect, url_for
from flask_login import LoginManager, login_user, current_user
from sqlalchemy.orm.exc import DetachedInstanceError

from session_aware_decorators import with_db_session, require_platform_context
from request_scoped_session_manager import RequestScopedSessionManager
from session_aware_user import SessionAwareUser


class TestSessionDecoratorsIntegration(unittest.TestCase):
    
    def setUp(self):
        """Set up integration test environment"""
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'test-secret-key'
        self.app.config['TESTING'] = True
        
        # Set up Flask-Login
        self.login_manager = LoginManager()
        self.login_manager.init_app(self.app)
        
        # Mock database manager and session manager
        self.mock_db_manager = Mock()
        self.mock_engine = Mock()
        self.mock_db_manager.engine = self.mock_engine
        
        # Create real session manager for integration testing
        self.session_manager = RequestScopedSessionManager(self.mock_db_manager)
        self.app.request_session_manager = self.session_manager
        
        # Mock session factory
        self.mock_session = Mock()
        self.session_manager.session_factory = Mock(return_value=self.mock_session)
        
        # Create test routes
        @self.app.route('/dashboard')
        @require_platform_context
        def dashboard():
            return f'Dashboard for user {current_user.id}'
        
        @self.app.route('/app_management')
        @with_db_session
        def app_management():
            if not current_user.is_authenticated:
                return redirect(url_for('login'))
            return f'App Management for user {current_user.username}'
        
        @self.app.route('/login')
        def login():
            return 'login'
        
        @self.app.route('/platform_management')
        def platform_management():
            return 'platform_management'
        
        @self.app.route('/first_time_setup')
        def first_time_setup():
            return 'first_time_setup'
        
        @self.app.route('/index')
        def index():
            return 'index'
        
        # User loader
        @self.login_manager.user_loader
        def load_user(user_id):
            mock_user = Mock()
            mock_user.id = int(user_id)
            mock_user.username = f'user{user_id}'
            mock_user.is_active = True
            return SessionAwareUser(mock_user, self.session_manager)
        
        self.client = self.app.test_client()
    
    def test_dashboard_access_with_platform_context(self):
        """Test dashboard access with proper platform context"""
        # Mock user with platforms
        mock_user = Mock()
        mock_user.id = 1
        mock_user.username = 'testuser'
        mock_user.is_active = True
        mock_user.get_id = Mock(return_value='1')
        
        mock_platform = Mock()
        mock_platform.id = 1
        mock_platform.name = 'Test Platform'
        mock_platform.is_default = True
        mock_platform.is_active = True
        
        # Create SessionAwareUser
        session_aware_user = SessionAwareUser(mock_user, self.session_manager)
        session_aware_user._platforms_cache = [mock_platform]
        session_aware_user._cache_valid = True
        
        # Mock the database query
        mock_query = Mock()
        mock_query.filter_by.return_value.all.return_value = [mock_platform]
        self.mock_session.query.return_value = mock_query
        
        # Mock session merge to return the original user
        self.mock_session.merge.return_value = mock_user
        
        with self.app.test_request_context():
            # Log in the user using Flask-Login
            login_user(session_aware_user)
            
            # Mock platform context
            with patch('platform_context_utils.get_current_platform_context') as mock_context:
                mock_context.return_value = {'platform_connection_id': 1}
                
                response = self.client.get('/dashboard')
                self.assertEqual(response.status_code, 200)
                self.assertIn('Dashboard for user 1', response.data.decode())
    
    def test_dashboard_access_without_platforms(self):
        """Test dashboard access when user has no platforms"""
        # Mock user without platforms
        mock_user = Mock()
        mock_user.id = 1
        mock_user.username = 'testuser'
        mock_user.is_active = True
        mock_user.get_id = Mock(return_value='1')
        
        session_aware_user = SessionAwareUser(mock_user, self.session_manager)
        session_aware_user._platforms_cache = []  # No platforms
        session_aware_user._cache_valid = True
        
        # Mock the database query to return no platforms
        mock_query = Mock()
        mock_query.filter_by.return_value.all.return_value = []  # No platforms
        self.mock_session.query.return_value = mock_query
        
        # Mock session merge to return the original user
        self.mock_session.merge.return_value = mock_user
        
        with self.app.test_request_context():
            # Log in the user using Flask-Login
            login_user(session_aware_user)
            
            response = self.client.get('/dashboard')
            self.assertEqual(response.status_code, 302)  # Redirect
            self.assertIn('/first_time_setup', response.location)
    
    def test_app_management_access_with_session_attachment(self):
        """Test app management access with proper session attachment"""
        # Mock user
        mock_user = Mock()
        mock_user.id = 1
        mock_user.username = 'testuser'
        mock_user.is_active = True
        mock_user.get_id = Mock(return_value='1')
        
        session_aware_user = SessionAwareUser(mock_user, self.session_manager)
        
        # Mock session contains user
        self.mock_session.__contains__ = Mock(return_value=True)
        
        with self.app.test_request_context():
            # Log in the user using Flask-Login
            login_user(session_aware_user)
            
            # Now make the request
            response = self.client.get('/app_management')
            self.assertEqual(response.status_code, 200)
            self.assertIn('App Management for user testuser', response.data.decode())
    
    def test_app_management_access_with_detached_user(self):
        """Test app management access when user becomes detached"""
        # Mock user
        mock_user = Mock()
        mock_user.id = 1
        mock_user.username = 'testuser'
        mock_user.is_active = True
        mock_user.get_id = Mock(return_value='1')
        
        session_aware_user = SessionAwareUser(mock_user, self.session_manager)
        
        # Mock session does not contain user (detached)
        self.mock_session.__contains__ = Mock(return_value=False)
        
        # Mock ensure_session_attachment
        reattached_user = Mock()
        reattached_user.id = 1
        reattached_user.username = 'testuser'
        self.session_manager.ensure_session_attachment = Mock(return_value=reattached_user)
        
        with self.app.test_request_context():
            # Log in the user using Flask-Login
            login_user(session_aware_user)
            
            response = self.client.get('/app_management')
            self.assertEqual(response.status_code, 200)
            # Verify reattachment was called (may be called multiple times during request processing)
            self.assertTrue(self.session_manager.ensure_session_attachment.called)
    
    def test_session_manager_integration(self):
        """Test integration with RequestScopedSessionManager"""
        with self.app.test_request_context():
            # Test that session manager is properly integrated
            self.assertIsNotNone(self.app.request_session_manager)
            self.assertIsInstance(self.app.request_session_manager, RequestScopedSessionManager)
            
            # Test session creation
            session = self.session_manager.get_request_session()
            self.assertIsNotNone(session)
            
            # Test that g object has session
            self.assertTrue(hasattr(g, 'db_session'))
    
    def test_decorator_error_recovery(self):
        """Test error recovery in decorators"""
        with self.app.test_request_context():
            # Create a route that will cause DetachedInstanceError
            @self.app.route('/test-recovery')
            @with_db_session
            def test_recovery():
                # Simulate accessing detached user
                raise DetachedInstanceError()
            
            response = self.client.get('/test-recovery')
            self.assertEqual(response.status_code, 302)  # Should redirect
            self.assertIn('/index', response.location)
    
    def test_platform_context_error_handling(self):
        """Test platform context error handling"""
        # Mock user with platform access that raises error
        mock_user = Mock()
        mock_user.id = 1
        mock_user.username = 'testuser'
        mock_user.is_active = True
        mock_user.get_id = Mock(return_value='1')
        
        session_aware_user = SessionAwareUser(mock_user, self.session_manager)
        # Mock platforms property to raise DetachedInstanceError
        session_aware_user.platforms = Mock(side_effect=DetachedInstanceError())
        
        # Mock the database query to raise an error
        mock_query = Mock()
        mock_query.filter_by.return_value.all.side_effect = DetachedInstanceError()
        self.mock_session.query.return_value = mock_query
        
        # Mock session merge to return the original user
        self.mock_session.merge.return_value = mock_user
        
        with self.app.test_request_context():
            # Log in the user using Flask-Login
            login_user(session_aware_user)
            
            response = self.client.get('/dashboard')
            self.assertEqual(response.status_code, 302)  # Should redirect due to error
            # The decorator catches the database error and redirects to platform_management
            self.assertIn('/platform_management', response.location)
    
    def test_multiple_decorator_interaction(self):
        """Test interaction between multiple decorators"""
        # Create route with multiple decorators
        @self.app.route('/test-multiple')
        @require_platform_context  # This includes @with_db_session
        def test_multiple():
            return 'success'
        
        # Mock authenticated user with platform
        mock_user = Mock()
        mock_user.id = 1
        mock_user.username = 'testuser'
        mock_user.is_active = True
        mock_user.get_id = Mock(return_value='1')
        
        mock_platform = Mock()
        mock_platform.id = 1
        mock_platform.is_default = True
        mock_platform.is_active = True
        
        session_aware_user = SessionAwareUser(mock_user, self.session_manager)
        session_aware_user._platforms_cache = [mock_platform]
        session_aware_user._cache_valid = True
        
        # Mock the database query
        mock_query = Mock()
        mock_query.filter_by.return_value.all.return_value = [mock_platform]
        self.mock_session.query.return_value = mock_query
        
        # Mock session merge to return the original user
        self.mock_session.merge.return_value = mock_user
        self.mock_session.__contains__ = Mock(return_value=True)
        
        with self.app.test_request_context():
            # Log in the user using Flask-Login
            login_user(session_aware_user)
            
            # Mock platform context
            with patch('platform_context_utils.get_current_platform_context') as mock_context:
                mock_context.return_value = {'platform_connection_id': 1}
                
                response = self.client.get('/test-multiple')
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data.decode(), 'success')
    
    def test_session_cleanup_on_error(self):
        """Test that sessions are properly cleaned up on errors"""
        with self.app.test_request_context():
            # Create route that raises error
            @self.app.route('/test-cleanup')
            @with_db_session
            def test_cleanup():
                raise Exception("Test error")
            
            response = self.client.get('/test-cleanup')
            self.assertEqual(response.status_code, 302)  # Should redirect due to error
    
    def test_unauthenticated_user_handling(self):
        """Test handling of unauthenticated users"""
        with self.app.test_request_context():
            # Mock unauthenticated user
            mock_user = Mock()
            mock_user.is_authenticated = False
            
            with patch('session_aware_decorators.current_user', mock_user):
                response = self.client.get('/dashboard')
                self.assertEqual(response.status_code, 302)  # Should redirect to login
                self.assertIn('/login', response.location)
    
    def test_session_manager_missing(self):
        """Test behavior when session manager is missing"""
        with self.app.test_request_context():
            # Remove session manager
            delattr(self.app, 'request_session_manager')
            
            mock_user = Mock()
            mock_user.is_authenticated = True
            mock_user.id = 1
            
            with patch('session_aware_decorators.current_user', mock_user):
                response = self.client.get('/app_management')
                self.assertEqual(response.status_code, 302)  # Should redirect to login


if __name__ == '__main__':
    unittest.main()
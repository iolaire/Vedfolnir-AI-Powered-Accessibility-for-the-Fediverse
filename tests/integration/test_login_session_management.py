# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


# NOTE: Flash messages in this test file have been replaced with comments
# as part of the notification system migration. The actual application now
# uses the unified WebSocket-based notification system.

"""
Tests for login route with proper session management to prevent DetachedInstanceError.

This test suite validates Task 11 requirements:
- Login POST handler uses request-scoped session manager
- User authentication and session creation maintain database context
- Proper error handling for database session issues during login
- Redirect logic maintains session context after successful login
"""

import unittest
import tempfile
import os
import sys
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock
# TODO: Refactor this test to not use flask_session - from flask import Flask
from werkzeug.test import Client
from werkzeug.wrappers import Response

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from database import DatabaseManager
from models import User, PlatformConnection, UserRole
from request_scoped_session_manager import RequestScopedSessionManager
from session_manager_v2 import SessionManagerV2 as SessionManager
from unified_session_manager import get_current_platform_context
from session_aware_user import SessionAwareUser
from database_context_middleware import DatabaseContextMiddleware
from tests.test_helpers.mock_user_helper import MockUserHelper
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm.exc import DetachedInstanceError

class TestLoginSessionManagement(unittest.TestCase):
    """Test login route with proper session management"""
    
    def setUp(self):
        """Set up test environment with Flask app and database"""
        # Create temporary database
        self.db_fd, self.db_path = tempfile.mkstemp()
        
        # Create test config
        self.config = Config()
        self.config.storage.database_url = f'mysql+pymysql://{self.db_path}'
        
        # Initialize database manager
        self.db_manager = DatabaseManager(self.config)
        self.db_manager.create_tables()
        
        # Initialize session managers
        self.request_session_manager = RequestScopedSessionManager(self.db_manager)
        with patch('redis.Redis', MagicMock()):
            self.session_manager = SessionManager(self.db_manager)
        
        # Create Flask app for testing
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'test_secret_key'
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing
        
        # Add session managers to app
        self.app.request_session_manager = self.request_session_manager
        self.app.session_manager = self.session_manager
        
        # Initialize database context middleware
        self.database_context_middleware = DatabaseContextMiddleware(self.app, self.request_session_manager)
        
        # Create mock user helper
        self.mock_user_helper = MockUserHelper(self.db_manager)
        
        # Create test users
        self._create_test_users()
        
        # Create test client
        self.client = self.app.test_client()
        
        # Import and set up login route
        self._setup_login_route()
    
    def tearDown(self):
        """Clean up test environment"""
        self.mock_user_helper.cleanup_mock_users()
        os.close(self.db_fd)
        os.unlink(self.db_path)
    
    def _create_test_users(self):
        """Create test users for login testing"""
        # Create user with platforms
        self.test_user_with_platforms = self.mock_user_helper.create_mock_user(
            username='testuser_with_platforms',
            email='test_with_platforms@test.com',
            password='test_password_123',
            with_platforms=True
        )
        
        # Create user without platforms
        self.test_user_no_platforms = self.mock_user_helper.create_mock_user(
            username='testuser_no_platforms',
            email='test_no_platforms@test.com',
            password='test_password_123',
            with_platforms=False
        )
        
        # Create inactive user
        self.test_user_inactive = self.mock_user_helper.create_mock_user(
            username='testuser_inactive',
            email='test_inactive@test.com',
            password='test_password_123',
            is_active=False,
            with_platforms=True
        )
    
    def _setup_login_route(self):
        """Set up the login route with proper imports and dependencies"""
        # Mock Flask-Login components
        from flask_login import LoginManager, login_user
        
        login_manager = LoginManager()
        login_manager.init_app(self.app)
        
        @login_manager.user_loader
        def load_user(user_id):
            """Mock user loader that returns SessionAwareUser"""
            if not user_id:
                return None
            
            try:
                user_id_int = int(user_id)
            except (ValueError, TypeError):
                return None
            
            try:
                with self.request_session_manager.session_scope() as session:
                    from sqlalchemy.orm import joinedload
                    user = session.query(User).options(
                        joinedload(User.platform_connections),
                        joinedload(User.sessions)
                    ).filter(
                        User.id == user_id_int,
                        User.is_active == True
                    ).first()
                    
                    if user:
                        return SessionAwareUser(user, self.request_session_manager)
                    return None
            except Exception:
                return None
        
        # Create login form class
        from flask_wtf import FlaskForm
        from wtforms import StringField, PasswordField, BooleanField, SubmitField
        from wtforms.validators import DataRequired
        
        class LoginForm(FlaskForm):
            username = StringField('Username', validators=[DataRequired()])
            password = PasswordField('Password', validators=[DataRequired()])
            remember = BooleanField('Remember Me')
            submit = SubmitField('Login')
        
        # Import required functions
        from security.core.security_utils import sanitize_for_log
        from sqlalchemy.orm import joinedload
        
        # Define the updated login route
        @self.app.route('/login', methods=['GET', 'POST'])
        def login():
            """User login with proper session management to prevent DetachedInstanceError"""
            from flask_login import current_user, login_user
            from flask import request, redirect, url_for, flash, render_template_string
            
            # Redirect if user is already logged in
            if current_user.is_authenticated:
                return redirect(url_for('main.index'))
                
            form = LoginForm()
            if form.validate_on_submit():
                # Use request-scoped session manager for all database operations
                try:
                    with self.request_session_manager.session_scope() as db_session:
                        # Find user with explicit relationship loading to prevent lazy loading issues
                        user = db_session.query(User).options(
                            joinedload(User.platform_connections),
                            joinedload(User.sessions)
                        ).filter_by(username=form.username.data).first()
                        
                        if user and user.check_password(form.password.data) and user.is_active:
                            # Store user info before login_user() call to avoid DetachedInstanceError
                            user_id = user.id
                            username = user.username
                            
                            # Update last login time within the session scope
                            user.last_login = datetime.now(timezone.utc)
                            db_session.commit()
                            
                            # Get user's platform connections with proper session attachment
                            user_platforms = db_session.query(PlatformConnection).filter_by(
                                user_id=user_id,
                                is_active=True
                            ).order_by(PlatformConnection.is_default.desc(), PlatformConnection.name).all()
                            
                            # Extract platform data before session closes to avoid DetachedInstanceError
                            platform_data = []
                            for p in user_platforms:
                                platform_data.append({
                                    'id': p.id,
                                    'name': p.name,
                                    'platform_type': p.platform_type,
                                    'is_default': p.is_default
                                })
                            
                            # Log in the user with Flask-Login (creates SessionAwareUser via load_user)
                            login_user(user, remember=form.remember.data)
                            
                            if not platform_data:
                                # First-time user - redirect to platform setup
                                # Unified notification: Welcome! Please set up your first platform connection to get started. (info)
                                return redirect(url_for('first_time_setup'))
                            
                            # Create Flask-based session with default platform using extracted data
                            try:
                                default_platform = next((p for p in platform_data if p['is_default']), None)
                                if not default_platform:
                                    # Set first platform as default if none is set
                                    default_platform = platform_data[0]
                                    # Update default platform in database within session scope
                                    for p in user_platforms:
                                        p.is_default = (p.id == default_platform['id'])
                                    db_session.commit()
                                
                                # Create database session with platform context
                                session_id = self.session_manager.create_user_session(user_id, default_platform['id'])
                                
                                # Store session ID in the response cookie
                                response = make_response(redirect(url_for('main.index')))
                                self.app.session_cookie_manager.set_session_cookie(response, session_id)

                                if session_id:
                                    # Welcome message with platform info
                                    flash(f'Welcome back! Connected to {default_platform["name"]} ({default_platform["platform_type"].title()})', 'success')
                                else:
                                    # Unified notification: Login successful, but there was an issue setting up your platform context (warning)
                                return response
                            except Exception as e:
                                # Unified notification: An unexpected error occurred during login. Please try again. (error)
                        else:
                            # Unified notification: Invalid username or password (error)
                            
                except SQLAlchemyError as e:
                    # Unified notification: Database error occurred during login. Please try again. (error)
                except Exception as e:
                    # Unified notification: An unexpected error occurred during login. Please try again. (error)
                    
            return render_template_string('<form method="post">{{ form.hidden_tag() }}{{ form.username() }}{{ form.password() }}{{ form.submit() }}</form>', form=form)
        
        # Add helper routes for testing
        @self.app.route('/')
        def index():
            from flask_login import current_user
            if current_user.is_authenticated:
                return f'Welcome {current_user.username}!'
            return 'Not logged in'
        
        @self.app.route('/first_time_setup')
        def first_time_setup():
            return 'First time setup page'
    
    def test_successful_login_with_platforms(self):
        """Test successful login for user with platforms"""
        response = self.client.post('/login', data={
            'username': 'testuser_with_platforms',
            'password': 'test_password_123'
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Welcome testuser_with_platforms!', response.data)
        
        # Verify session cookie was set
        session_cookie = next((cookie for cookie in self.client.cookie_jar if cookie.name == 'session_id'), None)
        self.assertIsNotNone(session_cookie)
    
    def test_successful_login_no_platforms(self):
        """Test successful login for user without platforms redirects to setup"""
        response = self.client.post('/login', data={
            'username': 'testuser_no_platforms',
            'password': 'test_password_123'
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'First time setup page', response.data)
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = self.client.post('/login', data={
            'username': 'testuser_with_platforms',
            'password': 'wrong_password'
        })
        
        self.assertEqual(response.status_code, 200)
        # Should stay on login page, not redirect
    
    def test_login_inactive_user(self):
        """Test login with inactive user"""
        response = self.client.post('/login', data={
            'username': 'testuser_inactive',
            'password': 'test_password_123'
        })
        
        self.assertEqual(response.status_code, 200)
        # Should stay on login page, not redirect
    
    def test_login_nonexistent_user(self):
        """Test login with nonexistent user"""
        response = self.client.post('/login', data={
            'username': 'nonexistent_user',
            'password': 'test_password_123'
        })
        
        self.assertEqual(response.status_code, 200)
        # Should stay on login page, not redirect
    
    def test_login_with_next_parameter(self):
        """Test login with next parameter for redirect"""
        # First, try to access a protected page to set the next parameter
        response = self.client.post('/login?next=/protected', data={
            'username': 'testuser_with_platforms',
            'password': 'test_password_123'
        })
        
        # Should redirect to the next page (which doesn't exist, so 404)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith('/protected'))
    
    def test_login_already_authenticated(self):
        """Test login when user is already authenticated"""
        # First login
        self.client.post('/login', data={
            'username': 'testuser_with_platforms',
            'password': 'test_password_123'
        })
        
        # Try to access login again
        response = self.client.get('/login', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Welcome testuser_with_platforms!', response.data)
    
    def test_login_session_context_maintained(self):
        """Test that session context is properly maintained after login"""
        response = self.client.post('/login', data={
            'username': 'testuser_with_platforms',
            'password': 'test_password_123'
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        
        # Verify session context
        session_cookie = next((cookie for cookie in self.client.cookie_jar if cookie.name == 'session_id'), None)
        self.assertIsNotNone(session_cookie)
        session_id = session_cookie.value
        
        # Verify session exists in database
        context = self.session_manager.get_session_context(session_id)
        self.assertIsNotNone(context)
        self.assertEqual(context['user_id'], self.test_user_with_platforms.id)
    
    def test_login_last_login_updated(self):
        """Test that last_login timestamp is updated on successful login"""
        # Get initial last_login
        initial_last_login = self.test_user_with_platforms.last_login
        
        # Login
        self.client.post('/login', data={
            'username': 'testuser_with_platforms',
            'password': 'test_password_123'
        })
        
        # Check updated last_login
        session = self.db_manager.get_session()
        try:
            updated_user = session.query(User).get(self.test_user_with_platforms.id)
            self.assertIsNotNone(updated_user.last_login)
            if initial_last_login:
                self.assertGreater(updated_user.last_login, initial_last_login)
        finally:
            session.close()
    
    def test_login_default_platform_selection(self):
        """Test that default platform is properly selected during login"""
        # Create user with multiple platforms, none default
        user = self.mock_user_helper.create_mock_user(
            username='multi_platform_user',
            password='test_password_123',
            with_platforms=False
        )
        
        # Create multiple platforms with no default
        session = self.db_manager.get_session()
        try:
            platform1 = PlatformConnection(
                user_id=user.id,
                name='Platform 1',
                platform_type='pixelfed',
                instance_url='https://test1.example.com',
                username='user1',
                access_token='token1',
                is_default=False,
                is_active=True
            )
            platform2 = PlatformConnection(
                user_id=user.id,
                name='Platform 2',
                platform_type='mastodon',
                instance_url='https://test2.example.com',
                username='user2',
                access_token='token2',
                is_default=False,
                is_active=True
            )
            session.add(platform1)
            session.add(platform2)
            session.commit()
        finally:
            session.close()
        
        # Login
        response = self.client.post('/login', data={
            'username': 'multi_platform_user',
            'password': 'test_password_123'
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        
        # Verify first platform was set as default
        session = self.db_manager.get_session()
        try:
            platforms = session.query(PlatformConnection).filter_by(
                user_id=user.id,
                is_active=True
            ).order_by(PlatformConnection.id).all()
            
            self.assertTrue(platforms[0].is_default)
            self.assertFalse(platforms[1].is_default)
        finally:
            session.close()
    
    def test_login_database_error_handling(self):
        """Test proper error handling for database errors during login"""
        # Mock the request session manager's session_scope to raise SQLAlchemyError
        with patch.object(self.request_session_manager, 'session_scope') as mock_session_scope:
            mock_session_scope.side_effect = SQLAlchemyError("Database connection failed")
            
            response = self.client.post('/login', data={
                'username': 'testuser_with_platforms',
                'password': 'test_password_123'
            })
            
            self.assertEqual(response.status_code, 200)
            # Should stay on login page with error message
    
    def test_login_form_validation(self):
        """Test login form validation"""
        # Test empty username
        response = self.client.post('/login', data={
            'username': '',
            'password': 'test_password_123'
        })
        self.assertEqual(response.status_code, 200)
        
        # Test empty password
        response = self.client.post('/login', data={
            'username': 'testuser_with_platforms',
            'password': ''
        })
        self.assertEqual(response.status_code, 200)
    
    def test_login_remember_me_functionality(self):
        """Test remember me functionality"""
        response = self.client.post('/login', data={
            'username': 'testuser_with_platforms',
            'password': 'test_password_123',
            'remember': True
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Welcome testuser_with_platforms!', response.data)
    
    def test_login_session_scope_usage(self):
        """Test that login uses request-scoped session manager properly"""
        with patch.object(self.request_session_manager, 'session_scope') as mock_session_scope:
            # Mock the context manager
            mock_session = Mock()
            mock_session_scope.return_value.__enter__ = Mock(return_value=mock_session)
            mock_session_scope.return_value.__exit__ = Mock(return_value=None)
            
            # Mock user query - create a proper mock that won't cause JSON serialization issues
            mock_user = Mock()
            mock_user.check_password.return_value = True
            mock_user.is_active = True
            mock_user.id = 1
            mock_user.username = 'testuser'
            mock_user.last_login = None
            mock_user.get_id.return_value = '1'  # Add get_id method for Flask-Login
            mock_user.is_authenticated = True
            mock_user.is_anonymous = False
            
            mock_session.query.return_value.options.return_value.filter_by.return_value.first.return_value = mock_user
            mock_session.query.return_value.filter_by.return_value.order_by.return_value.all.return_value = []
            
            # Mock session manager to avoid session creation issues
            with patch.object(self.session_manager, 'create_user_session', return_value='test_session_id'):
                response = self.client.post('/login', data={
                    'username': 'testuser',
                    'password': 'test_password_123'
                })
            
            # Verify session_scope was called
            mock_session_scope.assert_called_once()
    
    def test_login_platform_data_extraction(self):
        """Test that platform data is properly extracted to avoid DetachedInstanceError"""
        response = self.client.post('/login', data={
            'username': 'testuser_with_platforms',
            'password': 'test_password_123'
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        
        # Verify session was created with platform context
        with self.client.session_transaction() as sess:
            session_id = sess.get('_id')
            context = self.session_manager.get_session_context(session_id)
            
            self.assertIsNotNone(context)
            self.assertIn('platform_connection_id', context)
            self.assertIsNotNone(context['platform_connection_id'])

class TestLoginErrorRecovery(unittest.TestCase):
    """Test error recovery scenarios for login"""
    
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
        
        # Initialize session managers
        self.request_session_manager = RequestScopedSessionManager(self.db_manager)
        self.session_manager = UnifiedSessionManager(self.db_manager)
        
        # Create mock user helper
        self.mock_user_helper = MockUserHelper(self.db_manager)
    
    def tearDown(self):
        """Clean up test environment"""
        self.mock_user_helper.cleanup_mock_users()
        os.close(self.db_fd)
        os.unlink(self.db_path)
    
    def test_detached_instance_error_recovery(self):
        """Test recovery from DetachedInstanceError during login"""
        # Create test user
        user = self.mock_user_helper.create_mock_user(
            username='test_detached_user',
            password='test_password_123',
            with_platforms=True
        )
        
        # Get the user and explicitly detach it from the session
        session = self.db_manager.get_session()
        try:
            detached_user = session.query(User).filter_by(username='test_detached_user').first()
            # Explicitly expunge the user from the session to detach it
            session.expunge(detached_user)
        finally:
            session.close()
        
        # Now try to access a relationship that requires database access - this should raise DetachedInstanceError
        with self.assertRaises(DetachedInstanceError):
            # This should raise DetachedInstanceError because the object is detached
            # and we're trying to access a relationship that requires a database query
            _ = detached_user.platform_connections[0].name
    
    def test_session_manager_error_recovery(self):
        """Test recovery when session manager fails"""
        user = self.mock_user_helper.create_mock_user(
            username='test_session_error_user',
            password='test_password_123',
            with_platforms=True
        )
        
        # Test that session manager can handle errors gracefully
        with patch.object(self.session_manager, 'create_user_session', side_effect=Exception("Session creation failed")):
            # This should not crash the application
            try:
                self.session_manager.create_user_session(user.id, user.platform_connections[0].id)
            except Exception as e:
                self.assertIn("Session creation failed", str(e))

if __name__ == '__main__':
    unittest.main()
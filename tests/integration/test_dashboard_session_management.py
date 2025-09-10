# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


# NOTE: Flash messages in this test file have been replaced with comments
# as part of the notification system migration. The actual application now
# uses the unified WebSocket-based notification system.

"""
Tests for dashboard route with session-aware decorators to prevent DetachedInstanceError.

This test suite validates Task 12 requirements:
- Dashboard view function uses with_db_session decorator
- Dashboard uses require_platform_context decorator for platform-dependent functionality
- All database queries in dashboard use request-scoped session
- Error handling for platform context loading failures
"""

import unittest
import tempfile
import os
import sys
from unittest.mock import Mock, patch, MagicMock
from flask import Flask

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from app.core.database.core.database_manager import DatabaseManager
from models import User, PlatformConnection, UserRole
from request_scoped_session_manager import RequestScopedSessionManager
from session_manager_v2 import SessionManagerV2 as SessionManager
from database_context_middleware import DatabaseContextMiddleware
from tests.test_helpers.mock_user_helper import MockUserHelper
from sqlalchemy.exc import SQLAlchemyError

class TestDashboardSessionManagement(unittest.TestCase):
    """Test dashboard route with session-aware decorators"""
    
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
        self.app.config['WTF_CSRF_ENABLED'] = False
        
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
        
        # Set up dashboard route with decorators
        self._setup_dashboard_route()
    
    def tearDown(self):
        """Clean up test environment"""
        self.mock_user_helper.cleanup_mock_users()
        os.close(self.db_fd)
        os.unlink(self.db_path)
    
    def _create_test_users(self):
        """Create test users for dashboard testing"""
        # Create user with platforms
        self.test_user_with_platforms = self.mock_user_helper.create_mock_user(
            username='dashboard_user_with_platforms',
            email='dashboard_with_platforms@test.com',
            password='test_password_123',
            with_platforms=True
        )
        
        # Create user without platforms
        self.test_user_no_platforms = self.mock_user_helper.create_mock_user(
            username='dashboard_user_no_platforms',
            email='dashboard_no_platforms@test.com',
            password='test_password_123',
            with_platforms=False
        )
    
    def _setup_dashboard_route(self):
        """Set up the dashboard route with proper decorators and dependencies"""
        from flask_login import LoginManager, current_user
        from session_aware_decorators import with_db_session, require_platform_context
        from app.core.security.core.security_utils import sanitize_for_log
        
        login_manager = LoginManager()
        login_manager.init_app(self.app)
        
        @login_manager.user_loader
        def load_user(user_id):
            """Mock user loader"""
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
                        from session_aware_user import SessionAwareUser
                        return SessionAwareUser(user, self.request_session_manager)
                    return None
            except Exception:
                return None
        
        # Mock get_current_platform_context function
        def mock_get_current_platform_context():
            """Mock platform context"""
            from flask import session
            session_id = session.get('_id')
            if session_id:
                context = self.session_manager.get_session_context(session_id)
                if context and context.get('platform_connection_id'):
                    return {
                        'platform_connection_id': context['platform_connection_id'],
                        'platform_info': context.get('platform_info', {})
                    }
            return None
        
        # Define the dashboard route with decorators
        @self.app.route('/')
        @with_db_session
        @require_platform_context
        def index():
            """Dashboard with session-aware decorators"""
            from flask import render_template_string, redirect, url_for, flash
            
            try:
                # Use request-scoped session for all database queries
                with self.request_session_manager.session_scope() as db_session:
                    # Check if user has any platform connections first
                    user_platforms = db_session.query(PlatformConnection).filter_by(
                        user_id=current_user.id,
                        is_active=True
                    ).count()
                    
                    if user_platforms == 0:
                        return redirect(url_for('first_time_setup'))
                    
                    # Get platform-specific statistics using session-aware context
                    context = mock_get_current_platform_context()
                    current_platform = None
                    
                    if context and context.get('platform_connection_id'):
                        current_platform = db_session.query(PlatformConnection).filter_by(
                            id=context['platform_connection_id'],
                            user_id=current_user.id,
                            is_active=True
                        ).first()
                    
                    if current_platform:
                        # Get platform-specific stats (mocked)
                        stats = {
                            'total_posts': 10,
                            'total_images': 25,
                            'pending_images': 5,
                            'approved_images': 15,
                            'posted_images': 5,
                            'platform_name': current_platform.name,
                            'platform_type': current_platform.platform_type
                        }
                        platform_dict = {
                            'id': current_platform.id,
                            'name': current_platform.name,
                            'platform_type': current_platform.platform_type,
                            'instance_url': current_platform.instance_url,
                            'username': current_platform.username,
                            'is_default': current_platform.is_default
                        }
                    else:
                        # Fallback to general stats
                        stats = {
                            'total_posts': 0,
                            'total_images': 0,
                            'pending_images': 0,
                            'approved_images': 0,
                            'posted_images': 0
                        }
                        platform_dict = None
                    
                    return render_template_string(
                        'Dashboard: {{ stats.total_posts }} posts, {{ stats.total_images }} images{% if current_platform %}, Platform: {{ current_platform.name }}{% endif %}',
                        stats=stats,
                        current_platform=platform_dict
                    )
                    
            except Exception as e:
                # Unified notification: Error loading dashboard. Please try again. (error)
                return redirect(url_for('platform.management'))
        
        # Add helper routes
        @self.app.route('/first_time_setup')
        def first_time_setup():
            return 'First time setup page'
        
        @self.app.route('/platform_management')
        def platform_management():
            return 'Platform management page'
        
        @self.app.route('/login')
        def login():
            return 'Login page'
    
    def _login_user(self, user):
        """Helper to log in a user and create session"""
        with self.client.session_transaction() as sess:
            sess['_user_id'] = str(user.id)
            # Create platform session if user has platforms
            if hasattr(user, 'platform_connections') and user.platform_connections:
                platform = user.platform_connections[0]
                session_id = self.session_manager.create_user_session(user.id, platform.id)
                sess['_id'] = session_id
    
    def test_dashboard_with_platforms_success(self):
        """Test successful dashboard access with platforms"""
        self._login_user(self.test_user_with_platforms)
        
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Dashboard:', response.data)
        self.assertIn(b'posts', response.data)
        self.assertIn(b'images', response.data)
    
    def test_dashboard_without_platforms_redirects(self):
        """Test dashboard redirects to setup when user has no platforms"""
        self._login_user(self.test_user_no_platforms)
        
        response = self.client.get('/', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'First time setup page', response.data)
    
    def test_dashboard_requires_authentication(self):
        """Test dashboard requires user authentication"""
        response = self.client.get('/')
        # Should redirect to login or return 401/403
        self.assertIn(response.status_code, [302, 401, 403])
    
    def test_dashboard_with_db_session_decorator(self):
        """Test that dashboard uses with_db_session decorator properly"""
        with patch.object(self.request_session_manager, 'session_scope') as mock_session_scope:
            # Mock the context manager
            mock_session = Mock()
            mock_session_scope.return_value.__enter__ = Mock(return_value=mock_session)
            mock_session_scope.return_value.__exit__ = Mock(return_value=None)
            
            # Mock query results
            mock_session.query.return_value.filter_by.return_value.count.return_value = 1
            mock_platform = Mock()
            mock_platform.id = 1
            mock_platform.name = 'Test Platform'
            mock_platform.platform_type = 'pixelfed'
            mock_platform.instance_url = 'https://test.example.com'
            mock_platform.username = 'testuser'
            mock_platform.is_default = True
            mock_session.query.return_value.filter_by.return_value.first.return_value = mock_platform
            
            self._login_user(self.test_user_with_platforms)
            
            response = self.client.get('/')
            
            # Verify session_scope was called (decorator working)
            mock_session_scope.assert_called()
    
    def test_dashboard_require_platform_context_decorator(self):
        """Test that dashboard uses require_platform_context decorator"""
        # Create user with platforms but no session context
        self._login_user(self.test_user_with_platforms)
        
        # Clear platform session context
        with self.client.session_transaction() as sess:
            if '_id' in sess:
                del sess['_id']
        
        response = self.client.get('/')
        
        # Should handle missing platform context gracefully
        self.assertEqual(response.status_code, 200)
    
    def test_dashboard_platform_context_loading_success(self):
        """Test successful platform context loading"""
        self._login_user(self.test_user_with_platforms)
        
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Platform:', response.data)
    
    def test_dashboard_database_error_handling(self):
        """Test dashboard handles database errors gracefully"""
        with patch.object(self.request_session_manager, 'session_scope') as mock_session_scope:
            mock_session_scope.side_effect = SQLAlchemyError("Database connection failed")
            
            self._login_user(self.test_user_with_platforms)
            
            response = self.client.get('/', follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            # Should handle error gracefully (may redirect to login or platform management)
            self.assertTrue(b'Login page' in response.data or b'Platform management page' in response.data)
    
    def test_dashboard_session_scope_usage(self):
        """Test that dashboard properly uses request-scoped session"""
        with patch.object(self.request_session_manager, 'session_scope') as mock_session_scope:
            # Mock successful session scope
            mock_session = Mock()
            mock_session_scope.return_value.__enter__ = Mock(return_value=mock_session)
            mock_session_scope.return_value.__exit__ = Mock(return_value=None)
            
            # Mock database queries
            mock_session.query.return_value.filter_by.return_value.count.return_value = 1
            mock_platform = Mock()
            mock_platform.id = 1
            mock_platform.name = 'Test Platform'
            mock_platform.platform_type = 'pixelfed'
            mock_platform.instance_url = 'https://test.example.com'
            mock_platform.username = 'testuser'
            mock_platform.is_default = True
            mock_session.query.return_value.filter_by.return_value.first.return_value = mock_platform
            
            self._login_user(self.test_user_with_platforms)
            
            response = self.client.get('/')
            
            # Verify session scope was used
            mock_session_scope.assert_called_once()
            # Verify database queries were made within session scope
            mock_session.query.assert_called()
    
    def test_dashboard_platform_statistics_loading(self):
        """Test that dashboard loads platform-specific statistics"""
        self._login_user(self.test_user_with_platforms)
        
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        
        # Should contain statistics
        self.assertIn(b'posts', response.data)
        self.assertIn(b'images', response.data)
    
    def test_dashboard_detached_instance_prevention(self):
        """Test that dashboard prevents DetachedInstanceError by using session-aware objects"""
        self._login_user(self.test_user_with_platforms)
        
        # This should not raise DetachedInstanceError
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        
        # Verify platform information is accessible
        self.assertIn(b'Platform:', response.data)
    
    def test_dashboard_fallback_to_general_stats(self):
        """Test dashboard falls back to general stats when no platform context"""
        # Create user with platforms but mock no platform context
        self._login_user(self.test_user_with_platforms)
        
        with patch('platform_context_utils.get_current_platform_context', return_value=None):
            response = self.client.get('/')
            self.assertEqual(response.status_code, 200)
            # Should still show dashboard with general stats
            self.assertIn(b'Dashboard:', response.data)
    
    def test_dashboard_error_recovery(self):
        """Test dashboard error recovery mechanisms"""
        with patch.object(self.request_session_manager, 'session_scope') as mock_session_scope:
            # Simulate database error
            mock_session_scope.side_effect = Exception("Unexpected database error")
            
            self._login_user(self.test_user_with_platforms)
            
            response = self.client.get('/', follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            # Should handle error gracefully (may redirect to login or platform management)
            self.assertTrue(b'Login page' in response.data or b'Platform management page' in response.data)

class TestDashboardDecorators(unittest.TestCase):
    """Test dashboard decorators functionality"""
    
    def setUp(self):
        """Set up test environment"""
        pass
    
    def tearDown(self):
        """Clean up test environment"""
        pass
    
    def test_decorators_exist_and_importable(self):
        """Test that the required decorators exist and can be imported"""
        try:
            from session_aware_decorators import with_db_session, require_platform_context
            self.assertTrue(callable(with_db_session))
            self.assertTrue(callable(require_platform_context))
        except ImportError as e:
            self.fail(f"Failed to import decorators: {e}")
    
    def test_dashboard_uses_decorators(self):
        """Test that the dashboard route in web_app.py uses the required decorators"""
        # Read the web_app.py file to verify decorators are applied
        import os
        web_app_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'web_app.py')
        
        with open(web_app_path, 'r') as f:
            content = f.read()
        
        # Check that the dashboard route has the required decorators
        self.assertIn('@with_db_session', content, "Dashboard route should use @with_db_session decorator")
        self.assertIn('@require_platform_context', content, "Dashboard route should use @require_platform_context decorator")
        
        # Check that the decorators are applied to the index function
        lines = content.split('\n')
        index_function_found = False
        decorators_before_index = []
        
        for i, line in enumerate(lines):
            if line.strip().startswith('@'):
                decorators_before_index.append(line.strip())
            elif 'def index():' in line:
                index_function_found = True
                break
            elif line.strip() and not line.strip().startswith('#') and not line.strip().startswith('@'):
                decorators_before_index = []  # Reset if we hit non-decorator, non-comment code
        
        self.assertTrue(index_function_found, "index() function should be found in web_app.py")
        self.assertIn('@with_db_session', decorators_before_index, "@with_db_session should be applied to index function")
        self.assertIn('@require_platform_context', decorators_before_index, "@require_platform_context should be applied to index function")

if __name__ == '__main__':
    unittest.main()
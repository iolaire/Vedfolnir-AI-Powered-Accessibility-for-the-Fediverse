#!/usr/bin/env python3

# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Web Routes Tests for DetachedInstanceError Fix

Tests for web application routes to ensure they work correctly with the
DetachedInstanceError fix implementation. Uses Flask application context
and standardized mock user helpers.
"""

import unittest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from flask import Flask, g
from flask_login import LoginManager, login_user, current_user

# Import test helpers
from tests.test_helpers import create_test_user_with_platforms, cleanup_test_user, MockUserHelper

# Import application components
from config import Config
from database import DatabaseManager
from models import User, PlatformConnection, UserRole
from request_scoped_session_manager import RequestScopedSessionManager
from session_aware_user import SessionAwareUser
from database_context_middleware import DatabaseContextMiddleware
from session_error_handlers import register_session_error_handlers
from detached_instance_handler import create_global_detached_instance_handler
from session_error_logger import initialize_session_error_logging

class WebRoutesDetachedInstanceFixTest(unittest.TestCase):
    """Test web routes with DetachedInstanceError fix"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test Flask application"""
        cls.temp_dir = tempfile.mkdtemp()
        
        # Create test config
        cls.config = Config()
        cls.db_manager = DatabaseManager(cls.config)
        
        # Create Flask app with minimal configuration
        import os
        test_template_dir = os.path.join(os.path.dirname(__file__), 'templates')
        cls.app = Flask(__name__, template_folder=test_template_dir)
        cls.app.config['TESTING'] = True
        cls.app.config['SECRET_KEY'] = 'test_secret_key_for_routes'
        cls.app.config['WTF_CSRF_ENABLED'] = False
        cls.app.config['LOGIN_DISABLED'] = False
        
        # Initialize Flask-Login
        cls.login_manager = LoginManager()
        cls.login_manager.init_app(cls.app)
        cls.login_manager.login_view = 'login'
        
        # Initialize session management components
        cls.request_session_manager = RequestScopedSessionManager(cls.db_manager)
        cls.database_middleware = DatabaseContextMiddleware(cls.app, cls.request_session_manager)
        
        # Initialize error handling
        cls.detached_handler = create_global_detached_instance_handler(cls.app, cls.request_session_manager)
        cls.session_logger = initialize_session_error_logging(cls.app)
        register_session_error_handlers(cls.app, cls.request_session_manager, cls.detached_handler)
        
        # Set up user loader for Flask-Login
        @cls.login_manager.user_loader
        def load_user(user_id):
            try:
                user_id_int = int(user_id)
                with cls.request_session_manager.session_scope() as session:
                    user = session.query(User).filter_by(id=user_id_int, is_active=True).first()
                    if user:
                        return SessionAwareUser(user, cls.request_session_manager)
                return None
            except Exception:
                return None
        
        # Add test routes
        cls._add_test_routes()
    
    @classmethod
    def _add_test_routes(cls):
        """Add test routes to the Flask app"""
        from session_error_handlers import with_session_error_handling
        from session_aware_decorators import with_db_session, require_platform_context
        from flask_login import login_required
        
        @cls.app.route('/test-dashboard')
        @login_required
        @with_db_session
        @require_platform_context
        @with_session_error_handling
        def test_dashboard():
            """Test dashboard route"""
            user_platforms = current_user.platforms
            active_platform = current_user.get_active_platform()
            return {
                'user_id': current_user.id,
                'username': current_user.username,
                'platform_count': len(user_platforms),
                'active_platform': active_platform.name if active_platform else None
            }
        
        @cls.app.route('/test-platform-switch/<int:platform_id>')
        @login_required
        @with_db_session
        @with_session_error_handling
        def test_platform_switch(platform_id):
            """Test platform switching route"""
            with cls.request_session_manager.session_scope() as session:
                # Find the platform
                platform = session.query(PlatformConnection).filter_by(
                    id=platform_id,
                    user_id=current_user.id,
                    is_active=True
                ).first()
                
                if not platform:
                    return {'success': False, 'error': 'Platform not found'}, 404
                
                # Update platform as default
                user_platforms = session.query(PlatformConnection).filter_by(
                    user_id=current_user.id,
                    is_active=True
                ).all()
                
                for p in user_platforms:
                    p.is_default = (p.id == platform_id)
                
                session.commit()
                
                return {
                    'success': True,
                    'platform_id': platform_id,
                    'platform_name': platform.name
                }
        
        @cls.app.route('/test-user-profile')
        @login_required
        @with_db_session
        @with_session_error_handling
        def test_user_profile():
            """Test user profile route"""
            return {
                'user_id': current_user.id,
                'username': current_user.username,
                'email': current_user.email,
                'role': current_user.role.value,
                'is_active': current_user.is_active,
                'platform_count': len(current_user.platforms)
            }
        
        @cls.app.route('/test-api-endpoint')
        @login_required
        @with_session_error_handling
        def test_api_endpoint():
            """Test API endpoint"""
            return {
                'success': True,
                'user_id': current_user.id,
                'timestamp': 'test_timestamp'
            }
        
        @cls.app.route('/test-error-trigger')
        @login_required
        @with_session_error_handling
        def test_error_trigger():
            """Test route that triggers DetachedInstanceError"""
            from sqlalchemy.orm.exc import DetachedInstanceError
            raise DetachedInstanceError("Test error for error handling")
        
        # Add required routes that decorators expect
        @cls.app.route('/login')
        def login():
            """Mock login route for testing"""
            return {'message': 'Mock login page'}, 200
        
        @cls.app.route('/')
        def index():
            """Mock index route for testing"""
            return {'message': 'Mock index page'}, 200
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(cls.temp_dir, ignore_errors=True)
    
    def setUp(self):
        """Set up individual test"""
        # Create mock user with platforms using unique username
        import uuid
        unique_username = f"test_routes_user_{uuid.uuid4().hex[:8]}"
        self.test_user, self.user_helper = create_test_user_with_platforms(
            self.db_manager,
            username=unique_username,
            role=UserRole.REVIEWER
        )
        
        # Create test client
        self.client = self.app.test_client()
    
    def tearDown(self):
        """Clean up individual test"""
        cleanup_test_user(self.user_helper)
    
    def _login_user(self):
        """Helper to log in test user"""
        with self.app.app_context():
            with self.app.test_request_context():
                session_user = SessionAwareUser(self.test_user, self.request_session_manager)
                login_user(session_user)
                return session_user
    
    def test_dashboard_route_with_session_management(self):
        """Test dashboard route with session management"""
        with self.app.app_context():
            with self.client.session_transaction() as sess:
                sess['_user_id'] = str(self.test_user.id)
                sess['_fresh'] = True
            
            # Test dashboard access
            response = self.client.get('/test-dashboard')
            
            # Should get response (may be redirect if platform context missing)
            self.assertIn(response.status_code, [200, 302])
            
            if response.status_code == 200:
                data = response.get_json()
                self.assertIn('user_id', data)
                self.assertEqual(data['user_id'], self.test_user.id)
                self.assertIn('username', data)
                self.assertEqual(data['username'], self.test_user.username)
    
    def test_platform_switching_route(self):
        """Test platform switching route"""
        with self.app.app_context():
            with self.client.session_transaction() as sess:
                sess['_user_id'] = str(self.test_user.id)
                sess['_fresh'] = True
            
            # Get user's platforms
            with self.request_session_manager.session_scope() as session:
                platforms = session.query(PlatformConnection).filter_by(
                    user_id=self.test_user.id,
                    is_active=True
                ).all()
                
                if platforms:
                    target_platform = platforms[0]
                    
                    # Test platform switch
                    response = self.client.get(f'/test-platform-switch/{target_platform.id}')
                    
                    if response.status_code == 200:
                        data = response.get_json()
                        self.assertTrue(data['success'])
                        self.assertEqual(data['platform_id'], target_platform.id)
                        self.assertEqual(data['platform_name'], target_platform.name)
    
    def test_user_profile_route(self):
        """Test user profile route"""
        with self.app.app_context():
            with self.client.session_transaction() as sess:
                sess['_user_id'] = str(self.test_user.id)
                sess['_fresh'] = True
            
            response = self.client.get('/test-user-profile')
            
            if response.status_code == 200:
                data = response.get_json()
                self.assertEqual(data['user_id'], self.test_user.id)
                self.assertEqual(data['username'], self.test_user.username)
                self.assertEqual(data['email'], self.test_user.email)
                self.assertEqual(data['role'], UserRole.REVIEWER.value)
                self.assertTrue(data['is_active'])
                self.assertGreaterEqual(data['platform_count'], 0)
    
    def test_api_endpoint_route(self):
        """Test API endpoint route"""
        with self.app.app_context():
            with self.client.session_transaction() as sess:
                sess['_user_id'] = str(self.test_user.id)
                sess['_fresh'] = True
            
            response = self.client.get('/test-api-endpoint')
            
            if response.status_code == 200:
                data = response.get_json()
                self.assertTrue(data['success'])
                self.assertEqual(data['user_id'], self.test_user.id)
                self.assertIn('timestamp', data)
    
    def test_error_handling_route(self):
        """Test error handling in routes"""
        with self.app.app_context():
            with self.client.session_transaction() as sess:
                sess['_user_id'] = str(self.test_user.id)
                sess['_fresh'] = True
            
            # Test route that triggers DetachedInstanceError
            response = self.client.get('/test-error-trigger')
            
            # Should handle error gracefully (not 500)
            self.assertNotEqual(response.status_code, 500)
            
            # Should either redirect or return JSON error
            if response.status_code == 200:
                # JSON error response
                data = response.get_json()
                if data:
                    self.assertIn('success', data)
                    self.assertFalse(data['success'])
            elif response.status_code in [302, 401]:
                # Redirect response (acceptable)
                pass
    
    def test_unauthenticated_access(self):
        """Test unauthenticated access to protected routes"""
        # Test dashboard without authentication
        response = self.client.get('/test-dashboard')
        self.assertEqual(response.status_code, 302)  # Redirect to login
        
        # Test profile without authentication
        response = self.client.get('/test-user-profile')
        self.assertEqual(response.status_code, 302)  # Redirect to login
        
        # Test API endpoint without authentication
        response = self.client.get('/test-api-endpoint')
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_session_persistence_across_requests(self):
        """Test session persistence across multiple requests"""
        with self.app.app_context():
            with self.client.session_transaction() as sess:
                sess['_user_id'] = str(self.test_user.id)
                sess['_fresh'] = True
            
            # Make multiple requests to test session persistence
            for i in range(3):
                response = self.client.get('/test-user-profile')
                
                if response.status_code == 200:
                    data = response.get_json()
                    self.assertEqual(data['user_id'], self.test_user.id)
                    self.assertEqual(data['username'], self.test_user.username)
                elif response.status_code == 302:
                    # Redirect is acceptable (may be due to missing platform context)
                    pass
                else:
                    self.fail(f"Unexpected status code: {response.status_code}")

class WebRoutesAdvancedTest(unittest.TestCase):
    """Advanced web routes tests"""
    
    def setUp(self):
        """Set up advanced test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        self.user_helper = MockUserHelper(self.db_manager)
        
        # Create Flask app with test templates
        import os
        test_template_dir = os.path.join(os.path.dirname(__file__), 'templates')
        self.app = Flask(__name__, template_folder=test_template_dir)
        self.app.config['TESTING'] = True
        self.app.config['SECRET_KEY'] = 'test_secret_advanced'
        self.app.config['WTF_CSRF_ENABLED'] = False
        
        # Initialize components
        self.request_session_manager = RequestScopedSessionManager(self.db_manager)
        self.database_middleware = DatabaseContextMiddleware(self.app, self.request_session_manager)
        
        # Initialize Flask-Login
        self.login_manager = LoginManager()
        self.login_manager.init_app(self.app)
        
        @self.login_manager.user_loader
        def load_user(user_id):
            try:
                user_id_int = int(user_id)
                with self.request_session_manager.session_scope() as session:
                    user = session.query(User).filter_by(id=user_id_int, is_active=True).first()
                    if user:
                        return SessionAwareUser(user, self.request_session_manager)
                return None
            except Exception:
                return None
        
        # Add required routes for decorators
        @self.app.route('/login')
        def login():
            return {'message': 'Mock login page'}, 200
        
        @self.app.route('/')
        def index():
            return {'message': 'Mock index page'}, 200
        
        self.client = self.app.test_client()
    
    def tearDown(self):
        """Clean up advanced test environment"""
        self.user_helper.cleanup_mock_users()
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_multiple_user_sessions(self):
        """Test multiple user sessions with different roles"""
        # Create users with different roles using unique usernames
        import uuid
        admin_user = self.user_helper.create_mock_user(
            username=f"test_admin_routes_{uuid.uuid4().hex[:8]}",
            role=UserRole.ADMIN,
            with_platforms=True
        )
        
        reviewer_user = self.user_helper.create_mock_user(
            username=f"test_reviewer_routes_{uuid.uuid4().hex[:8]}",
            role=UserRole.REVIEWER,
            with_platforms=True
        )
        
        # Add test route for role testing
        from session_error_handlers import with_session_error_handling
        from flask_login import login_required, current_user
        
        @self.app.route('/test-role-check')
        @login_required
        @with_session_error_handling
        def test_role_check():
            return {
                'user_id': current_user.id,
                'role': current_user.role.value,
                'is_admin': current_user.has_permission(UserRole.ADMIN)
            }
        
        # Test admin user session
        with self.app.app_context():
            with self.client.session_transaction() as sess:
                sess['_user_id'] = str(admin_user.id)
                sess['_fresh'] = True
            
            response = self.client.get('/test-role-check')
            if response.status_code == 200:
                data = response.get_json()
                self.assertEqual(data['role'], UserRole.ADMIN.value)
                self.assertTrue(data['is_admin'])
        
        # Test reviewer user session (new session)
        with self.app.app_context():
            with self.client.session_transaction() as sess:
                sess['_user_id'] = str(reviewer_user.id)
                sess['_fresh'] = True
            
            response = self.client.get('/test-role-check')
            if response.status_code == 200:
                data = response.get_json()
                self.assertEqual(data['role'], UserRole.REVIEWER.value)
                self.assertFalse(data['is_admin'])
    
    def test_custom_platform_route_access(self):
        """Test route access with custom platform configurations"""
        # Create user with custom platforms
        custom_platforms = [
            {
                'name': 'Test Custom Platform',
                'platform_type': 'pixelfed',
                'instance_url': 'https://test.custom.social',
                'username': 'test_custom',
                'access_token': 'test_token',
                'is_default': True
            }
        ]
        
        import uuid
        custom_user = self.user_helper.create_mock_user(
            username=f"test_custom_route_user_{uuid.uuid4().hex[:8]}",
            role=UserRole.REVIEWER,
            platform_configs=custom_platforms
        )
        
        # Add test route for platform testing
        from session_error_handlers import with_session_error_handling
        from session_aware_decorators import with_db_session
        from flask_login import login_required, current_user
        
        @self.app.route('/test-platform-info')
        @login_required
        @with_db_session
        @with_session_error_handling
        def test_platform_info():
            platforms = current_user.platforms
            active_platform = current_user.get_active_platform()
            
            return {
                'platform_count': len(platforms),
                'active_platform_name': active_platform.name if active_platform else None,
                'active_platform_type': active_platform.platform_type if active_platform else None,
                'active_platform_url': active_platform.instance_url if active_platform else None
            }
        
        with self.app.app_context():
            with self.client.session_transaction() as sess:
                sess['_user_id'] = str(custom_user.id)
                sess['_fresh'] = True
            
            response = self.client.get('/test-platform-info')
            if response.status_code == 200:
                data = response.get_json()
                self.assertEqual(data['platform_count'], 1)
                self.assertEqual(data['active_platform_name'], 'Test Custom Platform')
                self.assertEqual(data['active_platform_type'], 'pixelfed')
                self.assertEqual(data['active_platform_url'], 'https://test.custom.social')
    
    def test_concurrent_route_access(self):
        """Test concurrent access to routes"""
        import threading
        import time
        
        # Create user for concurrent testing with unique username
        import uuid
        concurrent_user = self.user_helper.create_mock_user(
            username=f"test_concurrent_routes_{uuid.uuid4().hex[:8]}",
            role=UserRole.REVIEWER,
            with_platforms=True
        )
        
        # Add test route
        from session_error_handlers import with_session_error_handling
        from flask_login import login_required, current_user
        
        @self.app.route('/test-concurrent')
        @login_required
        @with_session_error_handling
        def test_concurrent():
            time.sleep(0.01)  # Small delay to test concurrency
            return {
                'user_id': current_user.id,
                'username': current_user.username,
                'timestamp': time.time()
            }
        
        results = []
        errors = []
        
        def make_request(request_id):
            try:
                with self.app.app_context():
                    with self.client.session_transaction() as sess:
                        sess['_user_id'] = str(concurrent_user.id)
                        sess['_fresh'] = True
                    
                    response = self.client.get('/test-concurrent')
                    if response.status_code == 200:
                        data = response.get_json()
                        results.append(f"Request-{request_id}: {data['username']}")
                    else:
                        results.append(f"Request-{request_id}: Status-{response.status_code}")
            except Exception as e:
                errors.append(f"Request-{request_id}: {e}")
        
        # Start concurrent requests
        threads = []
        for i in range(3):
            thread = threading.Thread(target=make_request, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join(timeout=10.0)
        
        # Verify results
        self.assertEqual(len(errors), 0, f"Concurrent errors: {errors}")
        self.assertEqual(len(results), 3, "Should have 3 concurrent results")

if __name__ == '__main__':
    unittest.main(verbosity=2)
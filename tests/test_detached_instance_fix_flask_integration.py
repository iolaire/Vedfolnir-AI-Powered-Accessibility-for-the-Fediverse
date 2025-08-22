#!/usr/bin/env python3

# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Flask Integration Tests for DetachedInstanceError Fix

Comprehensive tests for the DetachedInstanceError fix implementation that require
Flask application context. Uses standardized mock user helpers for consistent
test data and proper cleanup.
"""

import unittest
import tempfile
import os
import sys
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm.exc import DetachedInstanceError
from sqlalchemy.exc import SQLAlchemyError

# Import test helpers
from tests.test_helpers import create_test_user_with_platforms, cleanup_test_user, MockUserHelper

# Import application components
from config import Config
from database import DatabaseManager
from models import User, PlatformConnection, UserRole
from request_scoped_session_manager import RequestScopedSessionManager
from session_aware_user import SessionAwareUser
from database_context_middleware import DatabaseContextMiddleware
from session_error_handlers import SessionErrorHandler, with_session_error_handling
from detached_instance_handler import DetachedInstanceHandler
from session_error_logger import SessionErrorLogger

class FlaskDetachedInstanceFixTest(unittest.TestCase):
    """Test DetachedInstanceError fix with Flask application context"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        cls.temp_dir = tempfile.mkdtemp()
        
        # Create test config
        cls.config = Config()
        cls.db_manager = DatabaseManager(cls.config)
        
        # Create Flask app for testing
        from flask import Flask
        cls.app = Flask(__name__)
        cls.app.config['TESTING'] = True
        cls.app.config['SECRET_KEY'] = 'test_secret_key'
        cls.app.config['WTF_CSRF_ENABLED'] = False
        
        # Add basic routes to prevent url_for errors
        @cls.app.route('/login')
        def login():
            return "Login page"
        
        @cls.app.route('/health_dashboard')
        def health_dashboard():
            return "Health dashboard"
        
        @cls.app.route('/platform_management')
        def platform_management():
            return "Platform management"
        
        # Initialize session management components
        cls.request_session_manager = RequestScopedSessionManager(cls.db_manager)
        cls.database_middleware = DatabaseContextMiddleware(cls.app, cls.request_session_manager)
        
        # Initialize error handling components
        cls.detached_handler = DetachedInstanceHandler(cls.request_session_manager)
        cls.session_error_handler = SessionErrorHandler(cls.request_session_manager, cls.detached_handler)
        cls.session_logger = SessionErrorLogger(log_dir=cls.temp_dir)
        
        # Store components in app for access
        cls.app.request_session_manager = cls.request_session_manager
        cls.app.session_error_handler = cls.session_error_handler
        cls.app.detached_instance_handler = cls.detached_handler
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(cls.temp_dir, ignore_errors=True)
    
    def setUp(self):
        """Set up individual test"""
        # Create mock user with platforms using standardized helpers with unique username
        import uuid
        unique_username = f"test_detached_fix_user_{uuid.uuid4().hex[:8]}"
        self.test_user, self.user_helper = create_test_user_with_platforms(
            self.db_manager,
            username=unique_username,
            role=UserRole.REVIEWER
        )
        
        # Create test client
        self.client = self.app.test_client()
        
        # Initialize session isolation
        from tests.test_helpers.session_test_isolation import SessionTestIsolation
        self.session_isolation = SessionTestIsolation(self.app)
        self.session_isolation.setup_test_context()
    
    def tearDown(self):
        """Clean up individual test"""
        # Clean up session isolation
        if hasattr(self, 'session_isolation'):
            self.session_isolation.teardown_contexts()
        
        # Clean up mock user
        cleanup_test_user(self.user_helper)
    
    def test_request_scoped_session_manager_with_flask_context(self):
        """Test RequestScopedSessionManager with proper Flask context"""
        with self.app.app_context():
            with self.app.test_request_context():
                # Test session creation
                session1 = self.request_session_manager.get_request_session()
                self.assertIsNotNone(session1)
                
                # Test that same session is returned within request
                session2 = self.request_session_manager.get_request_session()
                self.assertEqual(session1, session2)
                
                # Test session scope context manager
                with self.request_session_manager.session_scope() as scoped_session:
                    self.assertIsNotNone(scoped_session)
                    
                    # Test database operations within scope
                    user_count = scoped_session.query(User).count()
                    self.assertGreaterEqual(user_count, 1)  # At least our test user
                
                # Test session cleanup
                self.request_session_manager.close_request_session()
    
    def test_session_aware_user_with_flask_context(self):
        """Test SessionAwareUser with Flask application context"""
        with self.app.app_context():
            with self.app.test_request_context():
                # Create SessionAwareUser
                session_user = SessionAwareUser(self.test_user, self.request_session_manager)
                
                # Test basic properties
                self.assertEqual(session_user.id, self.test_user.id)
                self.assertEqual(session_user.username, self.test_user.username)
                self.assertEqual(session_user.email, self.test_user.email)
                self.assertTrue(session_user.is_active)
                self.assertEqual(session_user.role, UserRole.REVIEWER)
                
                # Test Flask-Login interface
                self.assertTrue(session_user.is_authenticated)
                self.assertFalse(session_user.is_anonymous)
                self.assertEqual(session_user.get_id(), str(self.test_user.id))
                
                # Test platform access (should not raise DetachedInstanceError)
                platforms = session_user.platforms
                self.assertIsNotNone(platforms)
                self.assertGreater(len(platforms), 0)
                
                # Test active platform access
                active_platform = session_user.get_active_platform()
                self.assertIsNotNone(active_platform)
    
    def test_database_context_middleware_lifecycle(self):
        """Test DatabaseContextMiddleware request lifecycle"""
        with self.app.app_context():
            # Test before_request handler
            with self.app.test_request_context():
                # Middleware should initialize session
                session = self.request_session_manager.get_request_session()
                self.assertIsNotNone(session)
                
                # Test template context injection
                context = self.database_middleware._create_safe_template_context()
                self.assertIn('current_user_safe', context)
                self.assertIn('user_platforms', context)
                self.assertIn('template_error', context)
                
                # Test that context is safe (no DetachedInstanceError)
                self.assertFalse(context['template_error'])
    
    def test_session_error_handler_with_flask_context(self):
        """Test SessionErrorHandler with Flask context"""
        with self.app.app_context():
            with self.app.test_request_context('/test-endpoint'):
                # Test DetachedInstanceError handling
                error = DetachedInstanceError("Test detached instance error")
                
                with patch('session_error_handlers.current_user') as mock_user:
                    mock_user.is_authenticated = True
                    mock_user.id = self.test_user.id
                    
                    # Test API endpoint error handling
                    with patch('session_error_handlers.jsonify') as mock_jsonify:
                        result = self.session_error_handler.handle_detached_instance_error(
                            error, 'api_test'
                        )
                        mock_jsonify.assert_called_once()
                        
                        # Verify JSON response structure
                        call_args = mock_jsonify.call_args[0][0]
                        self.assertIn('success', call_args)
                        self.assertFalse(call_args['success'])
                        self.assertIn('error', call_args)
                        self.assertIn('message', call_args)
                
                # Test error count tracking
                stats = self.session_error_handler.get_error_statistics()
                self.assertIn('detached_instance:api_test', stats)
    
    def test_detached_instance_handler_recovery_with_flask_context(self):
        """Test DetachedInstanceHandler recovery with Flask context"""
        with self.app.app_context():
            with self.app.test_request_context():
                # Test safe access with normal object
                result = self.detached_handler.safe_access(self.test_user, 'username', 'default')
                self.assertEqual(result, self.test_user.username)
                
                # Test safe relationship access
                platforms = self.detached_handler.safe_relationship_access(
                    self.test_user, 'platform_connections', []
                )
                self.assertIsNotNone(platforms)
                self.assertGreater(len(platforms), 0)
                
                # Test ensure_attached
                with self.request_session_manager.session_scope() as session:
                    attached_user = self.detached_handler.ensure_attached(self.test_user, session)
                    self.assertIsNotNone(attached_user)
                    self.assertEqual(attached_user.id, self.test_user.id)
    
    def test_session_error_logging_with_flask_context(self):
        """Test session error logging with Flask context"""
        with self.app.app_context():
            with self.app.test_request_context('/test-logging'):
                # Test logging DetachedInstanceError
                error = DetachedInstanceError("Test logging error")
                self.session_logger.log_detached_instance_error(error, 'test_endpoint')
                
                # Test logging SQLAlchemy error
                sql_error = SQLAlchemyError("Test SQL error")
                self.session_logger.log_sqlalchemy_error(sql_error, 'test_endpoint')
                
                # Test logging session recovery
                self.session_logger.log_session_recovery('User', 0.123, True, 'test_endpoint')
                
                # Test logging session validation failure
                self.session_logger.log_session_validation_failure(
                    'test_endpoint', 'Test validation failure'
                )
                
                # Verify log files were created
                log_files = os.listdir(self.temp_dir)
                self.assertGreater(len(log_files), 0)
                
                # Check for expected log files
                expected_files = ['session_errors.log', 'session_debug.log', 'session_errors.json']
                for expected_file in expected_files:
                    self.assertIn(expected_file, log_files)
    
    def test_session_error_handling_decorator_with_flask_context(self):
        """Test @with_session_error_handling decorator with Flask context"""
        
        @with_session_error_handling
        def test_view_function():
            return "success"
        
        @with_session_error_handling
        def test_view_with_error():
            raise DetachedInstanceError("Test decorator error")
        
        with self.app.app_context():
            with self.app.test_request_context('/test-decorator'):
                # Test successful view function
                result = test_view_function()
                self.assertEqual(result, "success")
                
                # Test view function with DetachedInstanceError
                with patch('session_error_handlers.jsonify') as mock_jsonify:
                    result = test_view_with_error()
                    mock_jsonify.assert_called_once()
                    
                    # Verify error response
                    call_args = mock_jsonify.call_args[0][0]
                    self.assertIn('success', call_args)
                    self.assertFalse(call_args['success'])
    
    def test_user_login_workflow_with_session_management(self):
        """Test complete user login workflow with session management"""
        with self.app.app_context():
            with self.app.test_request_context():
                # Simulate user login process
                with self.request_session_manager.session_scope() as session:
                    # Find user (simulates login authentication)
                    user = session.query(User).filter_by(
                        username=self.test_user.username
                    ).first()
                    self.assertIsNotNone(user)
                    
                    # Create SessionAwareUser (simulates Flask-Login user_loader)
                    session_user = SessionAwareUser(user, self.request_session_manager)
                    
                    # Test user properties are accessible
                    self.assertEqual(session_user.username, self.test_user.username)
                    self.assertTrue(session_user.is_authenticated)
                    
                    # Test platform access (common in dashboard)
                    platforms = session_user.platforms
                    self.assertGreater(len(platforms), 0)
                    
                    # Test active platform (common in platform switching)
                    active_platform = session_user.get_active_platform()
                    self.assertIsNotNone(active_platform)
    
    def test_platform_switching_workflow_with_session_management(self):
        """Test platform switching workflow with session management"""
        with self.app.app_context():
            with self.app.test_request_context():
                # Get user's platforms
                with self.request_session_manager.session_scope() as session:
                    user = session.query(User).filter_by(
                        username=self.test_user.username
                    ).first()
                    platforms = user.platform_connections
                    self.assertGreater(len(platforms), 0)
                    
                    # Test platform switching (simulates API endpoint)
                    target_platform = platforms[0]
                    
                    # Update platform as default (simulates platform switch)
                    for platform in platforms:
                        platform.is_default = (platform.id == target_platform.id)
                    
                    session.commit()
                    
                    # Verify switch was successful
                    updated_user = session.query(User).filter_by(
                        username=self.test_user.username
                    ).first()
                    
                    default_platform = next(
                        (p for p in updated_user.platform_connections if p.is_default),
                        None
                    )
                    self.assertIsNotNone(default_platform)
                    self.assertEqual(default_platform.id, target_platform.id)
    
    def test_dashboard_access_workflow_with_session_management(self):
        """Test dashboard access workflow with session management"""
        with self.app.app_context():
            with self.app.test_request_context():
                # Simulate dashboard access
                session_user = SessionAwareUser(self.test_user, self.request_session_manager)
                
                # Test user statistics access (common in dashboard)
                with self.request_session_manager.session_scope() as session:
                    # Test platform statistics
                    user_platforms = session.query(PlatformConnection).filter_by(
                        user_id=session_user.id,
                        is_active=True
                    ).all()
                    self.assertGreater(len(user_platforms), 0)
                    
                    # Test that platform data can be safely serialized
                    platform_data = []
                    for platform in user_platforms:
                        platform_dict = {
                            'id': platform.id,
                            'name': platform.name,
                            'platform_type': platform.platform_type,
                            'is_default': platform.is_default
                        }
                        platform_data.append(platform_dict)
                    
                    self.assertGreater(len(platform_data), 0)
                    
                    # Verify no DetachedInstanceError when accessing platform properties
                    for platform_dict in platform_data:
                        self.assertIsNotNone(platform_dict['name'])
                        self.assertIsNotNone(platform_dict['platform_type'])
    
    def test_template_context_with_session_management(self):
        """Test template context with session management"""
        with self.app.app_context():
            with self.app.test_request_context():
                # Test safe template context creation
                context = self.database_middleware._create_safe_template_context()
                
                # Verify context contains expected keys
                expected_keys = ['current_user_safe', 'user_platforms', 'template_error']
                for key in expected_keys:
                    self.assertIn(key, context)
                
                # Test that template_error is False (no errors)
                self.assertFalse(context['template_error'])
                
                # Test user_platforms is accessible
                user_platforms = context['user_platforms']
                self.assertIsNotNone(user_platforms)
                
                # Test that platform data is safe for templates
                if user_platforms:
                    for platform in user_platforms:
                        self.assertIn('id', platform)
                        self.assertIn('name', platform)
                        self.assertIn('platform_type', platform)
    
    def test_concurrent_request_handling(self):
        """Test concurrent request handling with session management"""
        import threading
        import time
        
        results = []
        errors = []
        
        def simulate_request(request_id):
            try:
                with self.app.app_context():
                    with self.app.test_request_context(f'/test-concurrent-{request_id}'):
                        # Simulate database operations
                        with self.request_session_manager.session_scope() as session:
                            user_count = session.query(User).count()
                            results.append(f"Request-{request_id}: {user_count} users")
                            time.sleep(0.01)  # Small delay to test concurrency
            except Exception as e:
                errors.append(f"Request-{request_id}: {e}")
        
        # Start multiple concurrent requests
        threads = []
        for i in range(5):
            thread = threading.Thread(target=simulate_request, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=10.0)
        
        # Verify results
        self.assertEqual(len(errors), 0, f"Concurrent request errors: {errors}")
        self.assertEqual(len(results), 5, "Should have 5 successful concurrent requests")

class FlaskDetachedInstanceFixAdvancedTest(unittest.TestCase):
    """Advanced Flask integration tests for DetachedInstanceError fix"""
    
    def setUp(self):
        """Set up advanced test environment"""
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        self.user_helper = MockUserHelper(self.db_manager)
        
        # Create Flask app
        from flask import Flask
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.config['SECRET_KEY'] = 'test_secret_key'
        self.app.config['WTF_CSRF_ENABLED'] = False
        
        # Initialize components
        self.request_session_manager = RequestScopedSessionManager(self.db_manager)
        self.database_middleware = DatabaseContextMiddleware(self.app, self.request_session_manager)
    
    def tearDown(self):
        """Clean up advanced test environment"""
        self.user_helper.cleanup_mock_users()
    
    def test_multiple_users_session_isolation(self):
        """Test session isolation with multiple users"""
        with self.app.app_context():
            # Create multiple users with different roles using unique usernames
            import uuid
            admin_user = self.user_helper.create_mock_user(
                username=f"test_admin_session_{uuid.uuid4().hex[:8]}",
                role=UserRole.ADMIN,
                with_platforms=True
            )
            
            reviewer_user = self.user_helper.create_mock_user(
                username=f"test_reviewer_session_{uuid.uuid4().hex[:8]}",
                role=UserRole.REVIEWER,
                with_platforms=True
            )
            
            # Test admin user session
            with self.app.test_request_context('/admin-test'):
                admin_session_user = SessionAwareUser(admin_user, self.request_session_manager)
                self.assertEqual(admin_session_user.role, UserRole.ADMIN)
                self.assertTrue(admin_session_user.has_permission(UserRole.ADMIN))
                
                admin_platforms = admin_session_user.platforms
                self.assertGreater(len(admin_platforms), 0)
            
            # Test reviewer user session (separate request context)
            with self.app.test_request_context('/reviewer-test'):
                reviewer_session_user = SessionAwareUser(reviewer_user, self.request_session_manager)
                self.assertEqual(reviewer_session_user.role, UserRole.REVIEWER)
                self.assertFalse(reviewer_session_user.has_permission(UserRole.ADMIN))
                
                reviewer_platforms = reviewer_session_user.platforms
                self.assertGreater(len(reviewer_platforms), 0)
                
                # Verify users are isolated (different platform sets)
                admin_platform_ids = {p.id for p in admin_platforms}
                reviewer_platform_ids = {p.id for p in reviewer_platforms}
                self.assertNotEqual(admin_platform_ids, reviewer_platform_ids)
    
    def test_custom_platform_configurations(self):
        """Test custom platform configurations with session management"""
        with self.app.app_context():
            # Create user with custom platform configurations
            custom_platform_configs = [
                {
                    'name': 'Custom Pixelfed Instance',
                    'platform_type': 'pixelfed',
                    'instance_url': 'https://custom.pixelfed.social',
                    'username': 'custom_user',
                    'access_token': 'custom_token_123',
                    'is_default': True
                },
                {
                    'name': 'Custom Mastodon Instance',
                    'platform_type': 'mastodon',
                    'instance_url': 'https://custom.mastodon.social',
                    'username': 'custom_mastodon_user',
                    'access_token': 'custom_mastodon_token_456',
                    'is_default': False
                }
            ]
            
            import uuid
            custom_user = self.user_helper.create_mock_user(
                username=f"test_custom_platforms_{uuid.uuid4().hex[:8]}",
                role=UserRole.REVIEWER,
                platform_configs=custom_platform_configs
            )
            
            with self.app.test_request_context('/custom-platform-test'):
                session_user = SessionAwareUser(custom_user, self.request_session_manager)
                
                # Test platform access
                platforms = session_user.platforms
                self.assertEqual(len(platforms), 2)
                
                # Test default platform
                default_platform = session_user.get_active_platform()
                self.assertIsNotNone(default_platform)
                self.assertEqual(default_platform.name, 'Custom Pixelfed Instance')
                self.assertTrue(default_platform.is_default)
                
                # Test platform properties
                pixelfed_platform = next(
                    (p for p in platforms if p.platform_type == 'pixelfed'),
                    None
                )
                self.assertIsNotNone(pixelfed_platform)
                self.assertEqual(pixelfed_platform.instance_url, 'https://custom.pixelfed.social')
                self.assertEqual(pixelfed_platform.username, 'custom_user')
    
    def test_error_recovery_scenarios(self):
        """Test various error recovery scenarios"""
        with self.app.app_context():
            import uuid
            user = self.user_helper.create_mock_user(
                username=f"test_error_recovery_{uuid.uuid4().hex[:8]}",
                role=UserRole.REVIEWER,
                with_platforms=True
            )
            
            with self.app.test_request_context('/error-recovery-test'):
                # Test DetachedInstanceError recovery
                detached_handler = DetachedInstanceHandler(self.request_session_manager)
                
                # Test safe access with valid attribute
                result = detached_handler.safe_access(user, 'username', 'default')
                self.assertEqual(result, user.username)
                
                # Test safe access with invalid attribute
                result = detached_handler.safe_access(user, 'nonexistent_attr', 'default_value')
                self.assertEqual(result, 'default_value')
                
                # Test safe relationship access
                platforms = detached_handler.safe_relationship_access(
                    user, 'platform_connections', []
                )
                self.assertGreater(len(platforms), 0)
                
                # Test safe relationship access with invalid relationship
                invalid_rel = detached_handler.safe_relationship_access(
                    user, 'nonexistent_relationship', []
                )
                self.assertEqual(invalid_rel, [])
    
    def test_session_performance_under_load(self):
        """Test session performance under load"""
        import time
        
        with self.app.app_context():
            # Create user for load testing with unique username
            import uuid
            load_user = self.user_helper.create_mock_user(
                username=f"test_load_user_{uuid.uuid4().hex[:8]}",
                role=UserRole.REVIEWER,
                with_platforms=True
            )
            
            # Measure performance of session operations
            start_time = time.time()
            operations_count = 0
            
            for i in range(50):  # 50 simulated operations
                with self.app.test_request_context(f'/load-test-{i}'):
                    # Simulate typical request operations
                    session_user = SessionAwareUser(load_user, self.request_session_manager)
                    
                    # Access user properties
                    _ = session_user.username
                    _ = session_user.email
                    _ = session_user.role
                    
                    # Access platforms
                    platforms = session_user.platforms
                    _ = len(platforms)
                    
                    # Get active platform
                    active_platform = session_user.get_active_platform()
                    if active_platform:
                        _ = active_platform.name
                    
                    operations_count += 1
            
            duration = time.time() - start_time
            ops_per_second = operations_count / duration
            
            # Should handle at least 10 operations per second
            self.assertGreater(ops_per_second, 10, 
                             f"Performance too slow: {ops_per_second:.1f} ops/sec")

if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)
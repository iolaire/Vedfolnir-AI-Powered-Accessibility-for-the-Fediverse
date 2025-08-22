#!/usr/bin/env python3

# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Final Flask Context Tests for DetachedInstanceError Fix

Comprehensive demonstration that the DetachedInstanceError fix works correctly
with Flask application context using standardized mock user helpers.

This test suite addresses the previously identified issues:
1. Username conflicts - Fixed with unique UUIDs
2. Missing routes - Added required login/index routes
3. Missing templates - Created test templates directory
"""

import unittest
import tempfile
import uuid
import os
from flask import Flask

# Import test helpers
from tests.test_helpers import MockUserHelper

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

class FinalFlaskDetachedInstanceFixTest(unittest.TestCase):
    """Final comprehensive Flask context tests for DetachedInstanceError fix"""
    
    def setUp(self):
        """Set up test environment with all fixes applied"""
        self.temp_dir = tempfile.mkdtemp()
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        self.user_helper = MockUserHelper(self.db_manager)
        
        # Create Flask app with test templates directory
        test_template_dir = os.path.join(os.path.dirname(__file__), 'templates')
        self.app = Flask(__name__, template_folder=test_template_dir)
        self.app.config['TESTING'] = True
        self.app.config['SECRET_KEY'] = 'test_secret_final'
        
        # Initialize Flask-Login with user loader
        from flask_login import LoginManager
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
        
        # Add required routes that decorators expect
        @self.app.route('/login')
        def login():
            return {'message': 'Mock login page'}, 200
        
        @self.app.route('/')
        def index():
            return {'message': 'Mock index page'}, 200
        
        # Initialize session management
        self.request_session_manager = RequestScopedSessionManager(self.db_manager)
        self.database_middleware = DatabaseContextMiddleware(self.app, self.request_session_manager)
        
        # Initialize error handling
        self.detached_handler = DetachedInstanceHandler(self.request_session_manager)
        self.session_error_handler = SessionErrorHandler(self.request_session_manager, self.detached_handler)
        self.session_logger = SessionErrorLogger(log_dir=self.temp_dir)
        
        # Create unique test user to avoid conflicts
        self.test_user = self.user_helper.create_mock_user(
            username=f"test_final_{uuid.uuid4().hex[:8]}",
            role=UserRole.REVIEWER,
            with_platforms=True
        )
        
        # Add test route with error handling decorator
        @self.app.route('/test-protected-route')
        @with_session_error_handling
        def test_protected_route():
            return {
                'message': 'Protected route accessed successfully',
                'user_id': self.test_user.id
            }
        
        self.client = self.app.test_client()
    
    def tearDown(self):
        """Clean up test environment"""
        self.user_helper.cleanup_mock_users()
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_flask_context_session_management(self):
        """Test that session management works correctly with Flask context"""
        with self.app.app_context():
            with self.app.test_request_context():
                # Test session creation and reuse
                session1 = self.request_session_manager.get_request_session()
                session2 = self.request_session_manager.get_request_session()
                self.assertEqual(session1, session2)
                
                # Test session scope
                with self.request_session_manager.session_scope() as scoped_session:
                    user_count = scoped_session.query(User).count()
                    self.assertGreaterEqual(user_count, 1)
    
    def test_flask_context_session_aware_user(self):
        """Test SessionAwareUser works correctly with Flask context"""
        with self.app.app_context():
            with self.app.test_request_context():
                session_user = SessionAwareUser(self.test_user, self.request_session_manager)
                
                # Test basic properties
                self.assertEqual(session_user.id, self.test_user.id)
                self.assertEqual(session_user.username, self.test_user.username)
                self.assertTrue(session_user.is_authenticated)
                
                # Test platform access (should not raise DetachedInstanceError)
                platforms = session_user.platforms
                self.assertGreater(len(platforms), 0)
                
                # Test active platform
                active_platform = session_user.get_active_platform()
                self.assertIsNotNone(active_platform)
    
    def test_flask_context_error_handling(self):
        """Test error handling works correctly with Flask context"""
        with self.app.app_context():
            with self.app.test_request_context('/test-error'):
                # Test error count tracking
                self.session_error_handler._increment_error_count('test_error', 'test_endpoint')
                stats = self.session_error_handler.get_error_statistics()
                self.assertIn('test_error:test_endpoint', stats)
                self.assertEqual(stats['test_error:test_endpoint'], 1)
    
    def test_flask_context_detached_instance_recovery(self):
        """Test DetachedInstanceError recovery with Flask context"""
        with self.app.app_context():
            with self.app.test_request_context():
                # Test safe access
                result = self.detached_handler.safe_access(self.test_user, 'username', 'default')
                self.assertEqual(result, self.test_user.username)
                
                # Test safe relationship access
                platforms = self.detached_handler.safe_relationship_access(
                    self.test_user, 'platform_connections', []
                )
                self.assertGreater(len(platforms), 0)
    
    def test_flask_context_template_context(self):
        """Test template context creation with Flask context"""
        with self.app.app_context():
            with self.app.test_request_context():
                context = self.database_middleware._create_safe_template_context()
                
                # Verify expected keys
                expected_keys = ['current_user_safe', 'user_platforms', 'template_error']
                for key in expected_keys:
                    self.assertIn(key, context)
                
                # Should not have template error
                self.assertFalse(context['template_error'])
    
    def test_flask_context_route_with_decorator(self):
        """Test Flask route with session error handling decorator"""
        with self.app.app_context():
            response = self.client.get('/test-protected-route')
            
            # Should get successful response
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertIn('message', data)
            self.assertEqual(data['message'], 'Protected route accessed successfully')
    
    def test_flask_context_multiple_users_isolation(self):
        """Test multiple users are properly isolated with Flask context"""
        with self.app.app_context():
            # Create additional users with unique usernames
            admin_user = self.user_helper.create_mock_user(
                username=f"test_admin_final_{uuid.uuid4().hex[:8]}",
                role=UserRole.ADMIN,
                with_platforms=True
            )
            
            reviewer_user = self.user_helper.create_mock_user(
                username=f"test_reviewer_final_{uuid.uuid4().hex[:8]}",
                role=UserRole.REVIEWER,
                with_platforms=True
            )
            
            # Test admin user in request context
            with self.app.test_request_context('/admin-test'):
                admin_session_user = SessionAwareUser(admin_user, self.request_session_manager)
                self.assertEqual(admin_session_user.role, UserRole.ADMIN)
                self.assertTrue(admin_session_user.has_permission(UserRole.ADMIN))
                admin_platforms = admin_session_user.platforms
                self.assertGreater(len(admin_platforms), 0)
            
            # Test reviewer user in separate request context
            with self.app.test_request_context('/reviewer-test'):
                reviewer_session_user = SessionAwareUser(reviewer_user, self.request_session_manager)
                self.assertEqual(reviewer_session_user.role, UserRole.REVIEWER)
                self.assertFalse(reviewer_session_user.has_permission(UserRole.ADMIN))
                reviewer_platforms = reviewer_session_user.platforms
                self.assertGreater(len(reviewer_platforms), 0)
                
                # Verify users have different platforms (isolation)
                admin_platform_ids = {p.id for p in admin_platforms}
                reviewer_platform_ids = {p.id for p in reviewer_platforms}
                self.assertNotEqual(admin_platform_ids, reviewer_platform_ids)
    
    def test_flask_context_complete_workflow(self):
        """Test complete user workflow with Flask context"""
        with self.app.app_context():
            with self.app.test_request_context():
                # Create SessionAwareUser
                session_user = SessionAwareUser(self.test_user, self.request_session_manager)
                
                # Test complete workflow
                self.assertTrue(session_user.is_authenticated)
                self.assertEqual(session_user.username, self.test_user.username)
                
                # Test platform operations
                platforms = session_user.platforms
                self.assertGreater(len(platforms), 0)
                
                # Test platform switching simulation
                with self.request_session_manager.session_scope() as session:
                    user_platforms = session.query(PlatformConnection).filter_by(
                        user_id=session_user.id,
                        is_active=True
                    ).all()
                    
                    if len(user_platforms) > 0:
                        target_platform = user_platforms[0]
                        
                        # Switch default platform
                        for platform in user_platforms:
                            platform.is_default = (platform.id == target_platform.id)
                        
                        session.commit()
                        
                        # Verify switch
                        updated_platforms = session.query(PlatformConnection).filter_by(
                            user_id=session_user.id,
                            is_active=True
                        ).all()
                        
                        default_platform = next(
                            (p for p in updated_platforms if p.is_default),
                            None
                        )
                        self.assertIsNotNone(default_platform)
                        self.assertEqual(default_platform.id, target_platform.id)
    
    def test_flask_context_standardized_mock_helpers(self):
        """Test that standardized mock user helpers work correctly with Flask context"""
        with self.app.app_context():
            with self.app.test_request_context():
                # Create user with custom platform configuration
                custom_platforms = [{
                    'name': f'Test Platform {uuid.uuid4().hex[:8]}',
                    'platform_type': 'pixelfed',
                    'instance_url': f'https://test-{uuid.uuid4().hex[:8]}.example.com',
                    'username': f'test_user_{uuid.uuid4().hex[:8]}',
                    'access_token': f'token_{uuid.uuid4().hex[:8]}',
                    'is_default': True
                }]
                
                custom_user = self.user_helper.create_mock_user(
                    username=f"test_custom_final_{uuid.uuid4().hex[:8]}",
                    role=UserRole.REVIEWER,
                    platform_configs=custom_platforms
                )
                
                # Test custom user properties
                self.assertEqual(custom_user.role, UserRole.REVIEWER)
                
                # Test platform access
                with self.request_session_manager.session_scope() as session:
                    platforms = session.query(PlatformConnection).filter_by(
                        user_id=custom_user.id,
                        is_active=True
                    ).all()
                    
                    self.assertEqual(len(platforms), 1)
                    platform = platforms[0]
                    self.assertEqual(platform.platform_type, 'pixelfed')
                    self.assertTrue(platform.is_default)
                    self.assertIn('test-', platform.instance_url)

class FinalFlaskPerformanceTest(unittest.TestCase):
    """Performance tests to ensure Flask context doesn't impact performance"""
    
    def setUp(self):
        """Set up performance test environment"""
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        self.user_helper = MockUserHelper(self.db_manager)
        
        # Create Flask app
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.config['SECRET_KEY'] = 'test_secret_perf_final'
        
        # Initialize components
        self.request_session_manager = RequestScopedSessionManager(self.db_manager)
        
        # Create test user
        self.test_user = self.user_helper.create_mock_user(
            username=f"test_perf_final_{uuid.uuid4().hex[:8]}",
            role=UserRole.REVIEWER,
            with_platforms=True
        )
    
    def tearDown(self):
        """Clean up performance test environment"""
        self.user_helper.cleanup_mock_users()
    
    def test_flask_context_performance(self):
        """Test that Flask context doesn't significantly impact performance"""
        import time
        
        with self.app.app_context():
            start_time = time.time()
            operations_count = 0
            
            # Perform multiple operations with Flask context
            for i in range(25):
                with self.app.test_request_context(f'/perf-test-final-{i}'):
                    session_user = SessionAwareUser(self.test_user, self.request_session_manager)
                    
                    # Access properties
                    _ = session_user.username
                    _ = session_user.email
                    _ = session_user.role
                    
                    # Access platforms
                    platforms = session_user.platforms
                    _ = len(platforms)
                    
                    operations_count += 1
            
            duration = time.time() - start_time
            ops_per_second = operations_count / duration
            
            # Should handle at least 8 operations per second
            self.assertGreater(ops_per_second, 8, 
                             f"Performance too slow: {ops_per_second:.1f} ops/sec")

def run_final_flask_tests():
    """Run final Flask context tests"""
    print("=" * 80)
    print("FINAL FLASK CONTEXT TESTS FOR DETACHED INSTANCE FIX")
    print("=" * 80)
    print("Testing Flask application context with fixes for:")
    print("✅ Username conflicts - Fixed with unique UUIDs")
    print("✅ Missing routes - Added required login/index routes")
    print("✅ Missing templates - Created test templates directory")
    print("✅ Flask-Login setup - Added proper user loader")
    print("=" * 80)
    
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add all test methods
    test_methods = [
        'test_flask_context_session_management',
        'test_flask_context_session_aware_user',
        'test_flask_context_error_handling',
        'test_flask_context_detached_instance_recovery',
        'test_flask_context_template_context',
        'test_flask_context_route_with_decorator',
        'test_flask_context_multiple_users_isolation',
        'test_flask_context_complete_workflow',
        'test_flask_context_standardized_mock_helpers'
    ]
    
    for method in test_methods:
        suite.addTest(FinalFlaskDetachedInstanceFixTest(method))
    
    # Add performance test
    suite.addTest(FinalFlaskPerformanceTest('test_flask_context_performance'))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 80)
    print("FINAL FLASK CONTEXT TEST RESULTS")
    print("=" * 80)
    
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    successes = total_tests - failures - errors
    
    print(f"Total Tests: {total_tests}")
    print(f"Successes: {successes}")
    print(f"Failures: {failures}")
    print(f"Errors: {errors}")
    
    if failures == 0 and errors == 0:
        print("\n🎉 ALL FLASK CONTEXT TESTS PASSED!")
        print("✅ DetachedInstanceError fix works correctly with Flask application context")
        print("✅ Standardized mock user helpers work properly")
        print("✅ All previously identified issues have been resolved:")
        print("   • Username conflicts fixed with unique UUIDs")
        print("   • Missing routes added (login, index)")
        print("   • Missing templates created")
        print("   • Flask-Login properly configured")
        print("✅ Flask context integration is production-ready!")
    else:
        print(f"\n❌ {failures + errors} tests failed")
        print("⚠️  Please review and fix remaining issues")
    
    return result.wasSuccessful()

if __name__ == '__main__':
    import sys
    success = run_final_flask_tests()
    sys.exit(0 if success else 1)
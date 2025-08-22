# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Session Management Fixes Integration Tests

Tests to verify that all session management fixes work together properly,
including session isolation, error handling, and meaningful error messages.
"""

import unittest
import tempfile
import shutil
from unittest.mock import Mock, patch
from flask import Flask
from sqlalchemy.orm.exc import DetachedInstanceError
from sqlalchemy.exc import SQLAlchemyError, InvalidRequestError

from config import Config
from database import DatabaseManager
from models import UserRole
from tests.test_helpers import create_test_user_with_platforms, cleanup_test_user
from tests.test_helpers.session_test_isolation import SessionTestIsolation
from tests.test_helpers.session_error_helpers import SessionErrorTestHelper
from session_error_logger import SessionErrorLogger
from session_error_handlers import SessionErrorHandler
from request_scoped_session_manager import RequestScopedSessionManager
from detached_instance_handler import DetachedInstanceHandler
from session_state_manager import SessionStateManager, get_session_state_manager

class SessionManagementFixesIntegrationTest(unittest.TestCase):
    """Integration tests for session management fixes"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        cls.config = Config()
        cls.db_manager = DatabaseManager(cls.config)
        cls.temp_dir = tempfile.mkdtemp()
        
        # Create Flask app for testing
        cls.app = Flask(__name__)
        cls.app.config.update({
            'TESTING': True,
            'SECRET_KEY': 'test_secret_key_session_fixes',
            'WTF_CSRF_ENABLED': False
        })
        
        # Add basic routes
        @cls.app.route('/login')
        def login():
            return "Login page"
        
        @cls.app.route('/health_dashboard')
        def health_dashboard():
            return "Health dashboard"
        
        # Initialize session management components
        cls.request_session_manager = RequestScopedSessionManager(cls.db_manager)
        cls.detached_handler = DetachedInstanceHandler(cls.request_session_manager)
        cls.session_error_logger = SessionErrorLogger(log_dir=cls.temp_dir)
        cls.session_error_handler = SessionErrorHandler(cls.request_session_manager, cls.detached_handler)
        cls.session_state_manager = get_session_state_manager()
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment"""
        shutil.rmtree(cls.temp_dir, ignore_errors=True)
    
    def setUp(self):
        """Set up individual test"""
        # Create mock user with platforms
        import uuid
        unique_username = f"test_session_fixes_user_{uuid.uuid4().hex[:8]}"
        self.test_user, self.user_helper = create_test_user_with_platforms(
            self.db_manager,
            username=unique_username,
            role=UserRole.REVIEWER
        )
        
        # Initialize session isolation
        self.session_isolation = SessionTestIsolation(self.app)
        self.session_isolation.setup_test_context()
        
        # Initialize error test helper
        self.error_helper = SessionErrorTestHelper(self)
    
    def tearDown(self):
        """Clean up individual test"""
        # Clean up session isolation
        self.session_isolation.teardown_contexts()
        
        # Clean up mock user
        cleanup_test_user(self.user_helper)
    
    def test_session_isolation_prevents_test_interference(self):
        """Test that session isolation prevents tests from interfering with each other"""
        with self.session_isolation.isolated_test_context():
            # Create a session state
            session_id = "test_session_isolation_123"
            session_info = self.session_state_manager.create_session_state(
                session_id, self.test_user.id
            )
            
            # Verify session state exists
            retrieved_info = self.session_state_manager.get_session_state(session_id)
            self.assertIsNotNone(retrieved_info)
            self.assertEqual(retrieved_info.session_id, session_id)
            
            # Clean up session state
            self.session_state_manager.cleanup_session_state(session_id)
            
            # Verify cleanup worked
            retrieved_info = self.session_state_manager.get_session_state(session_id)
            self.assertIsNone(retrieved_info)
    
    def test_session_error_logging_with_meaningful_messages(self):
        """Test that session error logging provides meaningful error messages"""
        with self.session_isolation.isolated_test_context():
            # Test DetachedInstanceError logging
            error = DetachedInstanceError("Test detached instance error")
            self.session_error_logger.log_detached_instance_error(
                error, 'test_endpoint', {'user_id': self.test_user.id}
            )
            
            # Test SQLAlchemy error logging
            sql_error = InvalidRequestError("Test SQL error")
            self.session_error_logger.log_sqlalchemy_error(
                sql_error, 'test_endpoint', {'user_id': self.test_user.id}
            )
            
            # Test session recovery logging
            self.session_error_logger.log_session_recovery(
                'User', 0.123, True, 'test_endpoint'
            )
            
            # Test session validation failure logging
            self.session_error_logger.log_session_validation_failure(
                'test_endpoint', 'Test validation failure'
            )
            
            # Verify log files were created
            import os
            log_files = os.listdir(self.temp_dir)
            self.assertGreater(len(log_files), 0)
    
    def test_session_error_handler_provides_meaningful_responses(self):
        """Test that session error handler provides meaningful error responses"""
        with self.session_isolation.isolated_test_context():
            # Test DetachedInstanceError handling
            error = self.error_helper.create_detached_instance_error("Test error")
            
            # Test API endpoint error handling
            with patch('session_error_handlers.current_user') as mock_user:
                mock_user.is_authenticated = True
                mock_user.id = self.test_user.id
                
                result = self.session_error_handler.handle_detached_instance_error(
                    error, 'api_test'
                )
                
                # Should return JSON response for API endpoints
                self.assertIsNotNone(result)
    
    def test_concurrent_session_state_management(self):
        """Test that concurrent session states are properly managed"""
        with self.session_isolation.isolated_test_context():
            # Create multiple session states
            session_ids = []
            for i in range(3):
                session_id = f"concurrent_session_{i}"
                session_info = self.session_state_manager.create_session_state(
                    session_id, self.test_user.id
                )
                session_ids.append(session_id)
            
            # Verify all sessions exist
            user_sessions = self.session_state_manager.get_user_sessions(self.test_user.id)
            self.assertEqual(len(user_sessions), 3)
            
            # Test concurrent session detection
            concurrent_sessions = self.session_state_manager.get_concurrent_sessions()
            self.assertIn(self.test_user.id, concurrent_sessions)
            self.assertEqual(len(concurrent_sessions[self.test_user.id]), 3)
            
            # Clean up sessions
            for session_id in session_ids:
                self.session_state_manager.cleanup_session_state(session_id)
    
    def test_session_error_recovery_with_meaningful_messages(self):
        """Test that session error recovery provides meaningful error messages"""
        with self.session_isolation.isolated_test_context():
            session_id = "test_recovery_session"
            
            # Create session state
            session_info = self.session_state_manager.create_session_state(
                session_id, self.test_user.id
            )
            
            # Test meaningful error message generation
            error = DetachedInstanceError("Test recovery error")
            message = self.session_state_manager.generate_meaningful_error_message(
                error, session_id, 'test_endpoint'
            )
            
            # Verify message is meaningful
            self.error_helper.assert_meaningful_error_message(message, "recovery test")
            
            # Clean up
            self.session_state_manager.cleanup_session_state(session_id)
    
    def test_session_conflict_detection(self):
        """Test that session conflicts are properly detected"""
        with self.session_isolation.isolated_test_context():
            # Create multiple sessions for same user
            session_ids = []
            for i in range(3):
                session_id = f"conflict_session_{i}"
                session_info = self.session_state_manager.create_session_state(
                    session_id, self.test_user.id
                )
                session_ids.append(session_id)
            
            # Detect conflicts
            conflicts = self.session_state_manager.detect_session_conflicts()
            
            # Should detect multiple sessions for same user
            multiple_session_conflicts = [
                c for c in conflicts if c['type'] == 'multiple_sessions'
            ]
            self.assertGreater(len(multiple_session_conflicts), 0)
            
            # Verify conflict details
            conflict = multiple_session_conflicts[0]
            self.assertEqual(conflict['user_id'], self.test_user.id)
            self.assertEqual(conflict['session_count'], 3)
            
            # Clean up
            for session_id in session_ids:
                self.session_state_manager.cleanup_session_state(session_id)
    
    def test_session_isolation_context_manager(self):
        """Test that session isolation context manager works properly"""
        session_id = "test_isolation_context"
        
        # Create session state
        session_info = self.session_state_manager.create_session_state(
            session_id, self.test_user.id
        )
        
        # Test isolation context
        try:
            with self.session_state_manager.session_isolation_context(session_id):
                # Session should be marked as active
                updated_info = self.session_state_manager.get_session_state(session_id)
                from session_state_manager import SessionState
                self.assertEqual(updated_info.state, SessionState.ACTIVE)
                
                # Test error handling within context - this should be caught by context manager
                raise DetachedInstanceError("Test context error")
        except DetachedInstanceError:
            pass  # Expected - context manager should catch and log this
        
        # Verify error was logged
        final_info = self.session_state_manager.get_session_state(session_id)
        self.assertGreater(final_info.error_count, 0)
        
        # Clean up
        self.session_state_manager.cleanup_session_state(session_id)
    
    def test_session_statistics_tracking(self):
        """Test that session statistics are properly tracked"""
        with self.session_isolation.isolated_test_context():
            # Create some sessions
            session_ids = []
            for i in range(2):
                session_id = f"stats_session_{i}"
                session_info = self.session_state_manager.create_session_state(
                    session_id, self.test_user.id
                )
                session_ids.append(session_id)
            
            # Get statistics
            stats = self.session_state_manager.get_session_statistics()
            
            # Verify statistics
            self.assertGreater(stats['total_sessions'], 0)
            self.assertGreater(stats['users_with_sessions'], 0)
            self.assertIn('state_distribution', stats)
            
            # Clean up
            for session_id in session_ids:
                self.session_state_manager.cleanup_session_state(session_id)
    
    def test_request_scoped_session_manager_integration(self):
        """Test that RequestScopedSessionManager integrates properly with fixes"""
        with self.session_isolation.isolated_test_context('/test-request'):
            # Test session creation
            session = self.request_session_manager.get_request_session()
            self.assertIsNotNone(session)
            
            # Test session info
            info = self.request_session_manager.get_session_info()
            self.assertTrue(info['has_request_context'])
            self.assertTrue(info['has_session'])
            
            # Test session scope
            with self.request_session_manager.session_scope() as scoped_session:
                self.assertIsNotNone(scoped_session)
                # Session should be the same as the request session
                self.assertEqual(scoped_session, session)
    
    def test_error_summary_generation(self):
        """Test that error summaries are properly generated"""
        with self.session_isolation.isolated_test_context():
            # Generate some errors
            error1 = self.error_helper.create_detached_instance_error("Error 1")
            error2 = self.error_helper.create_sqlalchemy_error("Error 2")
            
            # Handle errors
            self.error_helper.assert_error_handled_gracefully(
                self.session_error_handler, error1, 'test_endpoint_1'
            )
            self.error_helper.assert_error_handled_gracefully(
                self.session_error_handler, error2, 'test_endpoint_2'
            )
            
            # Get error summary
            summary = self.error_helper.get_error_summary()
            
            # Verify summary
            self.assertEqual(summary['total_errors'], 2)
            self.assertEqual(summary['errors_handled'], 2)
            self.assertGreater(len(summary['error_details']), 0)

if __name__ == '__main__':
    unittest.main()
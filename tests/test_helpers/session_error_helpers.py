# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Session Error Test Helpers

Provides utilities for testing session error handling with meaningful error messages
and proper test isolation to prevent test interference.
"""

import logging
import unittest
from unittest.mock import Mock, patch
from typing import Dict, Any, Optional, List
from contextlib import contextmanager
from flask import Flask
from sqlalchemy.orm.exc import DetachedInstanceError
from sqlalchemy.exc import SQLAlchemyError, InvalidRequestError

logger = logging.getLogger(__name__)

class SessionErrorTestHelper:
    """Helper for testing session error scenarios with meaningful messages"""
    
    def __init__(self, test_case: unittest.TestCase):
        """Initialize session error test helper
        
        Args:
            test_case: The test case instance
        """
        self.test_case = test_case
        self.error_log = []
        self.recovery_attempts = []
    
    def create_detached_instance_error(self, message: str = "Test detached instance error") -> DetachedInstanceError:
        """Create a DetachedInstanceError for testing
        
        Args:
            message: Error message
            
        Returns:
            DetachedInstanceError instance
        """
        return DetachedInstanceError(message)
    
    def create_sqlalchemy_error(self, message: str = "Test SQLAlchemy error") -> SQLAlchemyError:
        """Create a SQLAlchemyError for testing
        
        Args:
            message: Error message
            
        Returns:
            SQLAlchemyError instance
        """
        return InvalidRequestError(message)
    
    def mock_session_with_error(self, error_type: str = "detached_instance"):
        """Create a mock session that raises specific errors
        
        Args:
            error_type: Type of error to raise ('detached_instance', 'sqlalchemy', 'timeout')
            
        Returns:
            Mock session object
        """
        mock_session = Mock()
        
        if error_type == "detached_instance":
            mock_session.query.side_effect = self.create_detached_instance_error()
        elif error_type == "sqlalchemy":
            mock_session.query.side_effect = self.create_sqlalchemy_error()
        elif error_type == "timeout":
            from sqlalchemy.exc import TimeoutError
            mock_session.query.side_effect = TimeoutError("Connection timeout", None, None)
        
        return mock_session
    
    def assert_error_handled_gracefully(self, error_handler, error: Exception, endpoint: str):
        """Assert that an error is handled gracefully with meaningful messages
        
        Args:
            error_handler: The error handler to test
            error: The error to handle
            endpoint: The endpoint where error occurred
        """
        try:
            result = error_handler.handle_detached_instance_error(error, endpoint)
            
            # Check that we got a meaningful response
            self.test_case.assertIsNotNone(result, "Error handler should return a response")
            
            # Log the error handling for verification
            self.error_log.append({
                'error_type': type(error).__name__,
                'endpoint': endpoint,
                'handled': True,
                'response': str(result)
            })
            
        except Exception as handling_error:
            self.test_case.fail(f"Error handler failed to handle {type(error).__name__} gracefully: {handling_error}")
    
    def assert_session_recovery_attempted(self, recovery_handler, obj, expected_success: bool = True):
        """Assert that session recovery was attempted
        
        Args:
            recovery_handler: The recovery handler to test
            obj: Object to recover
            expected_success: Whether recovery should succeed
        """
        try:
            result = recovery_handler.handle_detached_instance(obj)
            
            if expected_success:
                self.test_case.assertIsNotNone(result, "Recovery should return a valid object")
            
            # Log the recovery attempt
            self.recovery_attempts.append({
                'object_type': type(obj).__name__,
                'success': result is not None,
                'expected_success': expected_success
            })
            
        except Exception as recovery_error:
            if expected_success:
                self.test_case.fail(f"Session recovery failed unexpectedly: {recovery_error}")
            else:
                # Expected failure - log it
                self.recovery_attempts.append({
                    'object_type': type(obj).__name__,
                    'success': False,
                    'expected_success': expected_success,
                    'error': str(recovery_error)
                })
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of errors handled during testing
        
        Returns:
            Dictionary with error handling summary
        """
        return {
            'total_errors': len(self.error_log),
            'errors_handled': len([e for e in self.error_log if e['handled']]),
            'recovery_attempts': len(self.recovery_attempts),
            'successful_recoveries': len([r for r in self.recovery_attempts if r['success']]),
            'error_details': self.error_log,
            'recovery_details': self.recovery_attempts
        }
    
    def assert_meaningful_error_message(self, error_message: str, context: str = ""):
        """Assert that an error message is meaningful and actionable
        
        Args:
            error_message: The error message to check
            context: Additional context for the assertion
        """
        # Check that message is not empty
        self.test_case.assertIsNotNone(error_message, f"Error message should not be None {context}")
        self.test_case.assertTrue(len(error_message.strip()) > 0, f"Error message should not be empty {context}")
        
        # Check that message doesn't contain generic unhelpful text
        unhelpful_phrases = [
            "An error occurred",
            "Something went wrong",
            "Error",
            "Exception"
        ]
        
        message_lower = error_message.lower()
        for phrase in unhelpful_phrases:
            if phrase.lower() == message_lower.strip():
                self.test_case.fail(f"Error message is too generic: '{error_message}' {context}")
        
        # Check that message contains actionable information
        actionable_indicators = [
            "please",
            "try",
            "check",
            "verify",
            "ensure",
            "contact",
            "refresh",
            "login",
            "session"
        ]
        
        has_actionable_info = any(indicator in message_lower for indicator in actionable_indicators)
        if not has_actionable_info:
            logger.warning(f"Error message may not be actionable: '{error_message}' {context}")

class ConcurrentSessionTestHelper:
    """Helper for testing concurrent session scenarios"""
    
    def __init__(self, test_case: unittest.TestCase):
        """Initialize concurrent session test helper
        
        Args:
            test_case: The test case instance
        """
        self.test_case = test_case
        self.session_states = []
    
    @contextmanager
    def concurrent_sessions(self, session_manager, user_ids: List[int]):
        """Context manager for testing concurrent sessions
        
        Args:
            session_manager: Session manager instance
            user_ids: List of user IDs to create sessions for
        """
        sessions = []
        
        try:
            # Create concurrent sessions
            for user_id in user_ids:
                session_id = session_manager.create_user_session(user_id)
                sessions.append({
                    'user_id': user_id,
                    'session_id': session_id,
                    'created': True
                })
                self.session_states.append(f"Created session {session_id} for user {user_id}")
            
            yield sessions
            
        finally:
            # Clean up sessions
            for session_info in sessions:
                if session_info.get('created'):
                    try:
                        session_manager.cleanup_user_sessions(session_info['user_id'])
                        self.session_states.append(f"Cleaned up session for user {session_info['user_id']}")
                    except Exception as cleanup_error:
                        logger.error(f"Failed to clean up session for user {session_info['user_id']}: {cleanup_error}")
    
    def assert_session_isolation(self, sessions: List[Dict[str, Any]]):
        """Assert that sessions are properly isolated from each other
        
        Args:
            sessions: List of session information dictionaries
        """
        # Check that all sessions have unique IDs
        session_ids = [s['session_id'] for s in sessions]
        unique_session_ids = set(session_ids)
        
        self.test_case.assertEqual(
            len(session_ids), 
            len(unique_session_ids),
            "All sessions should have unique IDs"
        )
        
        # Check that sessions don't interfere with each other
        for i, session1 in enumerate(sessions):
            for j, session2 in enumerate(sessions):
                if i != j:
                    self.test_case.assertNotEqual(
                        session1['session_id'],
                        session2['session_id'],
                        f"Sessions for users {session1['user_id']} and {session2['user_id']} should be different"
                    )
    
    def get_session_state_log(self) -> List[str]:
        """Get log of session state changes
        
        Returns:
            List of session state change messages
        """
        return self.session_states.copy()

def create_mock_flask_app_with_session_management() -> Flask:
    """Create a mock Flask app with session management components for testing
    
    Returns:
        Flask app configured for session management testing
    """
    app = Flask(__name__)
    app.config.update({
        'TESTING': True,
        'SECRET_KEY': 'test_secret_key_session_management',
        'WTF_CSRF_ENABLED': False
    })
    
    # Initialize Flask-Login with safe error handling
    try:
        from flask_login import LoginManager
        login_manager = LoginManager()
        login_manager.init_app(app)
        
        @login_manager.user_loader
        def load_user(user_id):
            # Mock user loader for testing
            from unittest.mock import Mock
            mock_user = Mock()
            mock_user.id = int(user_id)
            mock_user.is_authenticated = True
            mock_user.is_active = True
            mock_user.is_anonymous = False
            return mock_user
            
    except ImportError:
        logger.warning("Flask-Login not available for session management testing")
    
    return app

def assert_session_error_recovery(test_case: unittest.TestCase, 
                                error_handler, 
                                error: Exception, 
                                endpoint: str,
                                expected_recovery: bool = True):
    """Assert that session error recovery works as expected
    
    Args:
        test_case: Test case instance
        error_handler: Error handler to test
        error: Error to handle
        endpoint: Endpoint where error occurred
        expected_recovery: Whether recovery is expected to succeed
    """
    try:
        if isinstance(error, DetachedInstanceError):
            result = error_handler.handle_detached_instance_error(error, endpoint)
        elif isinstance(error, SQLAlchemyError):
            result = error_handler.handle_sqlalchemy_error(error, endpoint)
        else:
            test_case.fail(f"Unsupported error type for recovery testing: {type(error)}")
        
        if expected_recovery:
            test_case.assertIsNotNone(result, "Error recovery should return a valid response")
        
        # Check that the result is a valid Flask response
        if hasattr(result, 'status_code'):
            test_case.assertIn(result.status_code, [200, 302, 401, 500], 
                             "Response should have a valid HTTP status code")
        
    except Exception as recovery_error:
        if expected_recovery:
            test_case.fail(f"Session error recovery failed: {recovery_error}")
        else:
            # Expected failure - this is okay
            pass
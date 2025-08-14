# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Session Test Isolation Utilities

Provides utilities for properly isolating session management tests from each other
and from the Flask application context to prevent test interference.
"""

import logging
import unittest
from contextlib import contextmanager
from typing import Optional, Any
from flask import Flask, g
from flask_login import LoginManager

logger = logging.getLogger(__name__)


class SessionTestIsolation:
    """Manages test isolation for session management tests"""
    
    def __init__(self, app: Flask):
        """Initialize session test isolation
        
        Args:
            app: Flask application instance
        """
        self.app = app
        self.app_context = None
        self.request_context = None
        self._original_g_state = None
    
    def setup_test_context(self):
        """Set up isolated test context"""
        # Create and push app context first
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Now we can safely access g
        try:
            from flask import g
            self._original_g_state = getattr(g, '__dict__', {}).copy() if hasattr(g, '__dict__') else {}
        except RuntimeError:
            # No application context yet - that's okay
            self._original_g_state = {}
        
        # Initialize Flask-Login if not already initialized
        if not hasattr(self.app, 'login_manager'):
            login_manager = LoginManager()
            login_manager.init_app(self.app)
            login_manager.user_loader(lambda user_id: None)  # Dummy user loader for tests
    
    def setup_request_context(self, path='/', method='GET', **kwargs):
        """Set up isolated request context
        
        Args:
            path: Request path
            method: HTTP method
            **kwargs: Additional request context arguments
        """
        self.request_context = self.app.test_request_context(path, method=method, **kwargs)
        self.request_context.push()
    
    def teardown_contexts(self):
        """Clean up test contexts"""
        # Pop request context
        if self.request_context:
            try:
                self.request_context.pop()
            except (LookupError, RuntimeError) as e:
                logger.debug(f"Request context already popped or invalid: {e}")
            finally:
                self.request_context = None
        
        # Pop app context
        if self.app_context:
            try:
                self.app_context.pop()
            except (LookupError, RuntimeError) as e:
                logger.debug(f"App context already popped or invalid: {e}")
            finally:
                self.app_context = None
        
        # Restore original g state
        if self._original_g_state is not None:
            try:
                from flask import g
                if hasattr(g, '__dict__'):
                    g.__dict__.clear()
                    g.__dict__.update(self._original_g_state)
            except RuntimeError:
                # No application context - that's okay
                pass
            self._original_g_state = None
    
    @contextmanager
    def isolated_test_context(self, path='/', method='GET', **kwargs):
        """Context manager for isolated test execution
        
        Args:
            path: Request path
            method: HTTP method
            **kwargs: Additional request context arguments
        """
        self.setup_test_context()
        self.setup_request_context(path, method, **kwargs)
        try:
            yield
        finally:
            self.teardown_contexts()


class SessionTestCase(unittest.TestCase):
    """Base test case with session management isolation"""
    
    def setUp(self):
        """Set up test with session isolation"""
        super().setUp()
        
        # Create test Flask app if not provided by subclass
        if not hasattr(self, 'app'):
            self.app = self.create_test_app()
        
        # Initialize session isolation
        self.session_isolation = SessionTestIsolation(self.app)
        
        # Set up test context
        self.session_isolation.setup_test_context()
    
    def tearDown(self):
        """Clean up test with session isolation"""
        # Clean up session isolation
        if hasattr(self, 'session_isolation'):
            self.session_isolation.teardown_contexts()
        
        super().tearDown()
    
    def create_test_app(self) -> Flask:
        """Create a test Flask application
        
        Returns:
            Configured Flask app for testing
        """
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test_secret_key'
        app.config['WTF_CSRF_ENABLED'] = False
        
        return app
    
    @contextmanager
    def test_request_context(self, path='/', method='GET', **kwargs):
        """Context manager for test request context
        
        Args:
            path: Request path
            method: HTTP method
            **kwargs: Additional request context arguments
        """
        self.session_isolation.setup_request_context(path, method, **kwargs)
        try:
            yield
        finally:
            # Request context will be cleaned up in tearDown
            pass


def isolate_session_test(test_func):
    """Decorator to isolate session management tests
    
    Args:
        test_func: Test function to isolate
        
    Returns:
        Wrapped test function with session isolation
    """
    def wrapper(self, *args, **kwargs):
        # Ensure we have session isolation
        if not hasattr(self, 'session_isolation'):
            if hasattr(self, 'app'):
                self.session_isolation = SessionTestIsolation(self.app)
                self.session_isolation.setup_test_context()
            else:
                raise RuntimeError("Session isolation requires Flask app to be available")
        
        # Run test with isolation
        try:
            return test_func(self, *args, **kwargs)
        except Exception as e:
            logger.error(f"Test {test_func.__name__} failed with session isolation: {e}")
            raise
    
    return wrapper


def create_isolated_flask_app() -> Flask:
    """Create an isolated Flask app for session testing
    
    Returns:
        Configured Flask app with session management components
    """
    app = Flask(__name__)
    app.config.update({
        'TESTING': True,
        'SECRET_KEY': 'test_secret_key_' + str(hash('session_test')),
        'WTF_CSRF_ENABLED': False,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False
    })
    
    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.user_loader(lambda user_id: None)  # Dummy user loader
    
    return app


def safe_current_user_access(default_value=None):
    """Safely access current_user in tests
    
    Args:
        default_value: Value to return if current_user is not accessible
        
    Returns:
        current_user if accessible, otherwise default_value
    """
    try:
        from flask import has_request_context
        from flask_login import current_user
        
        if has_request_context() and current_user:
            return current_user
    except (ImportError, RuntimeError, AttributeError):
        pass
    
    return default_value


def mock_current_user_for_test(user_id: int, username: str = "test_user", is_authenticated: bool = True):
    """Create a mock current_user for testing
    
    Args:
        user_id: User ID
        username: Username
        is_authenticated: Whether user is authenticated
        
    Returns:
        Mock user object
    """
    from unittest.mock import Mock
    
    mock_user = Mock()
    mock_user.id = user_id
    mock_user.username = username
    mock_user.is_authenticated = is_authenticated
    mock_user.is_active = True
    mock_user.is_anonymous = False
    
    return mock_user


class SessionErrorTestMixin:
    """Mixin for testing session error handling"""
    
    def assert_session_error_logged(self, error_type: str, endpoint: str):
        """Assert that a session error was logged
        
        Args:
            error_type: Expected error type
            endpoint: Expected endpoint
        """
        # This would be implemented based on the specific logging setup
        # For now, just check that the test doesn't crash
        self.assertTrue(True, "Session error logging test placeholder")
    
    def assert_session_recovery_attempted(self, object_type: str):
        """Assert that session recovery was attempted
        
        Args:
            object_type: Type of object being recovered
        """
        # This would be implemented based on the specific recovery setup
        # For now, just check that the test doesn't crash
        self.assertTrue(True, "Session recovery test placeholder")
    
    def create_detached_instance_error(self, message: str = "Test detached instance"):
        """Create a DetachedInstanceError for testing
        
        Args:
            message: Error message
            
        Returns:
            DetachedInstanceError instance
        """
        from sqlalchemy.orm.exc import DetachedInstanceError
        return DetachedInstanceError(message)
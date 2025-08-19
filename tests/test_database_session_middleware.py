# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for DatabaseSessionMiddleware

Tests the Redis session middleware that provides session context from Redis sessions.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from flask import Flask, g
from redis_session_middleware import (
    DatabaseSessionMiddleware,  # Compatibility class
    get_current_session_context,
    get_current_session_id,
    get_current_user_id,
    get_current_platform_id,
    update_session_platform,
    is_session_authenticated
)
from unified_session_manager import SessionValidationError, SessionExpiredError


class TestDatabaseSessionMiddleware(unittest.TestCase):
    """Test cases for DatabaseSessionMiddleware"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'test-secret-key'
        
        # Mock dependencies
        self.mock_session_manager = Mock()
        self.mock_cookie_manager = Mock()
        
        # Create middleware
        self.middleware = DatabaseSessionMiddleware(
            self.app,
            self.mock_session_manager,
            self.mock_cookie_manager
        )
    
    def test_middleware_initialization(self):
        """Test middleware initialization"""
        self.assertEqual(self.middleware.session_manager, self.mock_session_manager)
        self.assertEqual(self.middleware.cookie_manager, self.mock_cookie_manager)
    
    def test_before_request_no_session_cookie(self):
        """Test before_request when no session cookie exists"""
        self.mock_cookie_manager.get_session_id_from_cookie.return_value = None
        
        with self.app.test_request_context('/'):
            self.middleware.before_request()
            
            # Should set safe defaults
            self.assertIsNone(g.session_context)
            self.assertIsNone(g.session_id)
            self.assertEqual(g.session_manager, self.mock_session_manager)
            self.assertEqual(g.cookie_manager, self.mock_cookie_manager)
    
    def test_before_request_valid_session(self):
        """Test before_request with valid session"""
        session_id = 'test_session_123'
        session_context = {
            'session_id': session_id,
            'user_id': 1,
            'platform_connection_id': 2,
            'user_info': {'username': 'testuser'},
            'platform_info': {'name': 'Test Platform'}
        }
        
        self.mock_cookie_manager.get_session_id_from_cookie.return_value = session_id
        self.mock_session_manager.get_session_context.return_value = session_context
        
        with self.app.test_request_context('/'):
            self.middleware.before_request()
            
            # Should load session context
            self.assertEqual(g.session_context, session_context)
            self.assertEqual(g.session_id, session_id)
    
    def test_before_request_invalid_session(self):
        """Test before_request with invalid session"""
        session_id = 'invalid_session'
        
        self.mock_cookie_manager.get_session_id_from_cookie.return_value = session_id
        self.mock_session_manager.get_session_context.return_value = None
        
        with self.app.test_request_context('/'):
            self.middleware.before_request()
            
            # Should set safe defaults
            self.assertIsNone(g.session_context)
            self.assertIsNone(g.session_id)
    
    def test_before_request_session_validation_error(self):
        """Test before_request when session validation raises error"""
        session_id = 'test_session_123'
        
        self.mock_cookie_manager.get_session_id_from_cookie.return_value = session_id
        self.mock_session_manager.get_session_context.side_effect = SessionValidationError("Invalid session")
        
        with self.app.test_request_context('/'):
            self.middleware.before_request()
            
            # Should handle error gracefully
            self.assertIsNone(g.session_context)
            self.assertIsNone(g.session_id)
            self.assertTrue(hasattr(g, 'session_error'))
            self.assertTrue(g.clear_session_cookie)
    
    def test_before_request_skip_static_files(self):
        """Test before_request skips static files"""
        with self.app.test_request_context('/static/css/style.css'):
            with patch.object(self.middleware, '_should_skip_session_loading', return_value=True):
                self.middleware.before_request()
                
                # Should not call cookie manager
                self.mock_cookie_manager.get_session_id_from_cookie.assert_not_called()
    
    def test_after_request_clear_cookie(self):
        """Test after_request clears cookie when requested"""
        with self.app.test_request_context('/'):
            g.clear_session_cookie = True
            response = Mock()
            
            result = self.middleware.after_request(response)
            
            # Should clear cookie
            self.mock_cookie_manager.clear_session_cookie.assert_called_with(response)
            self.assertEqual(result, response)
    
    def test_after_request_refresh_cookie(self):
        """Test after_request refreshes cookie for active session"""
        session_id = 'test_session_123'
        
        with self.app.test_request_context('/'):
            g.session_id = session_id
            g.session_context = {'user_id': 1}
            response = Mock()
            
            result = self.middleware.after_request(response)
            
            # Should refresh cookie
            self.mock_cookie_manager.refresh_session_cookie.assert_called_with(response, session_id)
            self.assertEqual(result, response)
    
    def test_after_request_cleanup(self):
        """Test after_request cleans up g object"""
        with self.app.test_request_context('/'):
            g.session_context = {'user_id': 1}
            g.session_id = 'test_session'
            g.session_error = Exception("test")
            g.clear_session_cookie = True
            
            response = Mock()
            self.middleware.after_request(response)
            
            # Should clean up g object
            self.assertIsNone(g.session_context)
            self.assertIsNone(g.session_id)
            self.assertIsNone(g.session_error)
            self.assertIsNone(g.clear_session_cookie)
    
    def test_should_skip_session_loading(self):
        """Test _should_skip_session_loading logic"""
        # Test static files
        with self.app.test_request_context('/static/css/style.css'):
            with patch('database_session_middleware.request') as mock_request:
                mock_request.endpoint = 'static'
                self.assertTrue(self.middleware._should_skip_session_loading())
        
        # Test health check
        with self.app.test_request_context('/health'):
            with patch('database_session_middleware.request') as mock_request:
                mock_request.endpoint = 'health'
                self.assertTrue(self.middleware._should_skip_session_loading())
        
        # Test favicon
        with self.app.test_request_context('/favicon.ico'):
            with patch('database_session_middleware.request') as mock_request:
                mock_request.path = '/favicon.ico'
                self.assertTrue(self.middleware._should_skip_session_loading())
        
        # Test normal request
        with self.app.test_request_context('/dashboard'):
            with patch('database_session_middleware.request') as mock_request:
                mock_request.endpoint = 'dashboard'
                mock_request.path = '/dashboard'
                self.assertFalse(self.middleware._should_skip_session_loading())


class TestSessionContextAccessFunctions(unittest.TestCase):
    """Test cases for session context access functions"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.app = Flask(__name__)
    
    def test_get_current_session_context(self):
        """Test get_current_session_context function"""
        with self.app.test_request_context('/'):
            # Test with no context
            self.assertIsNone(get_current_session_context())
            
            # Test with context
            test_context = {'user_id': 1, 'platform_id': 2}
            g.session_context = test_context
            self.assertEqual(get_current_session_context(), test_context)
    
    def test_get_current_session_id(self):
        """Test get_current_session_id function"""
        with self.app.test_request_context('/'):
            # Test with no session ID
            self.assertIsNone(get_current_session_id())
            
            # Test with session ID
            test_session_id = 'test_session_123'
            g.session_id = test_session_id
            self.assertEqual(get_current_session_id(), test_session_id)
    
    def test_get_current_user_id(self):
        """Test get_current_user_id function"""
        with self.app.test_request_context('/'):
            # Test with no context
            self.assertIsNone(get_current_user_id())
            
            # Test with context
            g.session_context = {'user_id': 123}
            self.assertEqual(get_current_user_id(), 123)
            
            # Test with context but no user_id
            g.session_context = {'platform_id': 456}
            self.assertIsNone(get_current_user_id())
    
    def test_get_current_platform_id(self):
        """Test get_current_platform_id function"""
        with self.app.test_request_context('/'):
            # Test with no context
            self.assertIsNone(get_current_platform_id())
            
            # Test with context
            g.session_context = {'platform_connection_id': 456}
            self.assertEqual(get_current_platform_id(), 456)
            
            # Test with context but no platform_id
            g.session_context = {'user_id': 123}
            self.assertIsNone(get_current_platform_id())
    
    def test_is_session_authenticated(self):
        """Test is_session_authenticated function"""
        with self.app.test_request_context('/'):
            # Test with no context
            self.assertFalse(is_session_authenticated())
            
            # Test with context but no user_id
            g.session_context = {'platform_id': 456}
            self.assertFalse(is_session_authenticated())
            
            # Test with authenticated context
            g.session_context = {'user_id': 123, 'platform_id': 456}
            self.assertTrue(is_session_authenticated())
    
    def test_update_session_platform(self):
        """Test update_session_platform function"""
        with self.app.test_request_context('/'):
            # Test with no session
            self.assertFalse(update_session_platform(123))
            
            # Test with session but no manager
            g.session_id = 'test_session'
            self.assertFalse(update_session_platform(123))
            
            # Test with session and manager
            mock_session_manager = Mock()
            mock_session_manager.update_platform_context.return_value = True
            mock_session_manager.get_session_context.return_value = {
                'user_id': 1,
                'platform_connection_id': 123
            }
            
            g.session_id = 'test_session'
            g.session_manager = mock_session_manager
            
            result = update_session_platform(123)
            self.assertTrue(result)
            
            # Should update context
            mock_session_manager.update_platform_context.assert_called_with('test_session', 123)
            mock_session_manager.get_session_context.assert_called_with('test_session')
    
    def test_get_session_created_at(self):
        """Test get_session_created_at function"""
        from redis_session_middleware import get_session_created_at
        
        with self.app.test_request_context('/'):
            # Test with no context
            self.assertIsNone(get_session_created_at())
            
            # Test with context
            g.session_context = {'created_at': '2025-01-01T12:00:00Z'}
            self.assertEqual(get_session_created_at(), '2025-01-01T12:00:00Z')
    
    def test_get_session_last_activity(self):
        """Test get_session_last_activity function"""
        from redis_session_middleware import get_session_last_activity
        
        with self.app.test_request_context('/'):
            # Test with no context
            self.assertIsNone(get_session_last_activity())
            
            # Test with context
            g.session_context = {'last_activity': '2025-01-01T12:30:00Z'}
            self.assertEqual(get_session_last_activity(), '2025-01-01T12:30:00Z')


if __name__ == '__main__':
    unittest.main()
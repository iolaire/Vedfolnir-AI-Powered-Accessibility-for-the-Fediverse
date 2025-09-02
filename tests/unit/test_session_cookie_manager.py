# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for SessionCookieManager

Tests the secure session cookie management system that stores only session IDs.
"""

import unittest
from unittest.mock import Mock, patch
from flask import Flask, Response
from session_cookie_manager import SessionCookieManager, create_session_cookie_manager

class TestSessionCookieManager(unittest.TestCase):
    """Test cases for SessionCookieManager"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'test-secret-key'
        
        # Create cookie manager
        self.cookie_manager = SessionCookieManager(
            cookie_name='test_session_id',
            max_age=3600,  # 1 hour
            secure=False   # For testing
        )
    
    def test_cookie_manager_initialization(self):
        """Test cookie manager initialization"""
        self.assertEqual(self.cookie_manager.cookie_name, 'test_session_id')
        self.assertEqual(self.cookie_manager.max_age, 3600)
        self.assertFalse(self.cookie_manager.secure)
    
    def test_set_session_cookie(self):
        """Test setting session cookie"""
        with self.app.test_request_context():
            response = Response()
            session_id = 'test_session_123'
            
            # Set cookie
            self.cookie_manager.set_session_cookie(response, session_id)
            
            # Verify cookie was set
            cookies = response.headers.getlist('Set-Cookie')
            self.assertEqual(len(cookies), 1)
            
            cookie_header = cookies[0]
            self.assertIn('test_session_id=test_session_123', cookie_header)
            self.assertIn('HttpOnly', cookie_header)
            self.assertIn('SameSite=Lax', cookie_header)
            self.assertIn('Path=/', cookie_header)
    
    def test_set_session_cookie_secure(self):
        """Test setting secure session cookie"""
        secure_manager = SessionCookieManager(secure=True)
        
        with self.app.test_request_context():
            response = Response()
            session_id = 'test_session_123'
            
            # Set cookie
            secure_manager.set_session_cookie(response, session_id)
            
            # Verify secure flag is set
            cookies = response.headers.getlist('Set-Cookie')
            cookie_header = cookies[0]
            self.assertIn('Secure', cookie_header)
    
    def test_get_session_id_from_cookie(self):
        """Test getting session ID from cookie"""
        with self.app.test_request_context('/', headers={'Cookie': 'test_session_id=test_session_123'}):
            session_id = self.cookie_manager.get_session_id_from_cookie()
            self.assertEqual(session_id, 'test_session_123')
    
    def test_get_session_id_from_cookie_missing(self):
        """Test getting session ID when cookie is missing"""
        with self.app.test_request_context('/'):
            session_id = self.cookie_manager.get_session_id_from_cookie()
            self.assertIsNone(session_id)
    
    def test_get_session_id_from_cookie_different_name(self):
        """Test getting session ID with different cookie name"""
        with self.app.test_request_context('/', headers={'Cookie': 'other_cookie=value; test_session_id=test_session_123'}):
            session_id = self.cookie_manager.get_session_id_from_cookie()
            self.assertEqual(session_id, 'test_session_123')
    
    def test_clear_session_cookie(self):
        """Test clearing session cookie"""
        with self.app.test_request_context():
            response = Response()
            
            # Clear cookie
            self.cookie_manager.clear_session_cookie(response)
            
            # Verify cookie was cleared
            cookies = response.headers.getlist('Set-Cookie')
            self.assertEqual(len(cookies), 1)
            
            cookie_header = cookies[0]
            self.assertIn('test_session_id=', cookie_header)
            self.assertIn('expires=', cookie_header)
    
    def test_validate_cookie_security_valid(self):
        """Test cookie security validation with valid settings"""
        valid_manager = SessionCookieManager(max_age=3600, secure=True)
        self.assertTrue(valid_manager.validate_cookie_security())
    
    def test_validate_cookie_security_too_short(self):
        """Test cookie security validation with too short max_age"""
        short_manager = SessionCookieManager(max_age=60)  # 1 minute
        self.assertFalse(short_manager.validate_cookie_security())
    
    def test_validate_cookie_security_too_long(self):
        """Test cookie security validation with too long max_age"""
        long_manager = SessionCookieManager(max_age=700000)  # > 7 days
        self.assertFalse(long_manager.validate_cookie_security())
    
    def test_refresh_session_cookie(self):
        """Test refreshing session cookie"""
        with self.app.test_request_context():
            response = Response()
            session_id = 'test_session_123'
            
            # Refresh cookie (should be same as setting)
            self.cookie_manager.refresh_session_cookie(response, session_id)
            
            # Verify cookie was set
            cookies = response.headers.getlist('Set-Cookie')
            self.assertEqual(len(cookies), 1)
            
            cookie_header = cookies[0]
            self.assertIn('test_session_id=test_session_123', cookie_header)
    
    @patch('session_cookie_manager.logger')
    def test_error_handling_set_cookie(self, mock_logger):
        """Test error handling when setting cookie fails"""
        with self.app.test_request_context():
            # Mock response that raises exception
            response = Mock()
            response.set_cookie.side_effect = Exception("Cookie error")
            
            # Should not raise exception
            self.cookie_manager.set_session_cookie(response, 'test_session')
            
            # Should log error
            mock_logger.error.assert_called()
    
    @patch('session_cookie_manager.logger')
    def test_error_handling_get_cookie(self, mock_logger):
        """Test error handling when getting cookie fails"""
        with patch('session_cookie_manager.request') as mock_request:
            mock_request.cookies.get.side_effect = Exception("Request error")
            
            # Should not raise exception
            session_id = self.cookie_manager.get_session_id_from_cookie()
            self.assertIsNone(session_id)
            
            # Should log error
            mock_logger.error.assert_called()
    
    @patch('session_cookie_manager.logger')
    def test_error_handling_clear_cookie(self, mock_logger):
        """Test error handling when clearing cookie fails"""
        with self.app.test_request_context():
            # Mock response that raises exception
            response = Mock()
            response.set_cookie.side_effect = Exception("Cookie error")
            
            # Should not raise exception
            self.cookie_manager.clear_session_cookie(response)
            
            # Should log error
            mock_logger.error.assert_called()

class TestCreateSessionCookieManager(unittest.TestCase):
    """Test cases for create_session_cookie_manager function"""
    
    def test_create_with_defaults(self):
        """Test creating cookie manager with default configuration"""
        config = {}
        manager = create_session_cookie_manager(config)
        
        self.assertEqual(manager.cookie_name, 'session_id')
        self.assertEqual(manager.max_age, 86400)  # 24 hours
        self.assertTrue(manager.secure)
    
    def test_create_with_custom_config(self):
        """Test creating cookie manager with custom configuration"""
        from datetime import timedelta
        
        config = {
            'SESSION_COOKIE_NAME': 'custom_session',
            'PERMANENT_SESSION_LIFETIME': timedelta(hours=12),
            'SESSION_COOKIE_SECURE': False
        }
        
        manager = create_session_cookie_manager(config)
        
        self.assertEqual(manager.cookie_name, 'custom_session')
        self.assertEqual(manager.max_age, 43200)  # 12 hours
        self.assertFalse(manager.secure)
    
    @patch('session_cookie_manager.logger')
    def test_create_with_invalid_security(self, mock_logger):
        """Test creating cookie manager with invalid security settings"""
        config = {
            'PERMANENT_SESSION_LIFETIME': 60  # Too short
        }
        
        manager = create_session_cookie_manager(config)
        
        # Should still create manager but log warning
        self.assertIsNotNone(manager)
        mock_logger.warning.assert_called()

if __name__ == '__main__':
    unittest.main()
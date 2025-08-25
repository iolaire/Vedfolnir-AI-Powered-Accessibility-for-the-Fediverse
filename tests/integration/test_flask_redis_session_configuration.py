# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integration tests for Flask Redis Session Interface with Configuration Service

Tests the integration between Flask session interface and configuration service
for dynamic session timeout configuration.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
import redis
from datetime import datetime, timedelta, timezone
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from flask_redis_session_interface import FlaskRedisSessionInterface, RedisSession


class TestFlaskRedisSessionConfiguration(unittest.TestCase):
    """Test cases for Flask Redis session interface with configuration service"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock Redis client
        self.mock_redis = Mock()
        self.mock_redis.get.return_value = None
        self.mock_redis.setex.return_value = True
        self.mock_redis.delete.return_value = 1
        
        # Mock configuration service
        self.mock_config_service = Mock()
        self.mock_config_service.get_config.return_value = 120  # Default 120 minutes
        
        # Create session interface
        self.session_interface = FlaskRedisSessionInterface(
            redis_client=self.mock_redis,
            key_prefix='test:session:',
            session_timeout=7200,  # Default 2 hours
            config_service=self.mock_config_service
        )
    
    def test_initialization_with_config_service(self):
        """Test session interface initialization with configuration service"""
        # Verify configuration service was called during initialization
        self.mock_config_service.get_config.assert_called_with('session_timeout_minutes', 120)
        
        # Verify timeout was set from configuration (120 minutes = 7200 seconds)
        self.assertEqual(self.session_interface.session_timeout, 7200)
    
    def test_initialization_without_config_service(self):
        """Test session interface initialization without configuration service"""
        interface = FlaskRedisSessionInterface(
            redis_client=self.mock_redis,
            session_timeout=3600  # 1 hour
        )
        
        # Should use default timeout when no config service
        self.assertEqual(interface.session_timeout, 3600)
    
    def test_get_configured_session_timeout(self):
        """Test getting session timeout from configuration"""
        # Test with different timeout values
        self.mock_config_service.get_config.return_value = 180  # 3 hours
        timeout = self.session_interface._get_configured_session_timeout()
        self.assertEqual(timeout, 10800)  # 180 * 60 = 10800 seconds
        
        # Test with configuration service error
        self.mock_config_service.get_config.side_effect = Exception("Config error")
        timeout = self.session_interface._get_configured_session_timeout()
        self.assertEqual(timeout, 7200)  # Should fall back to default
    
    def test_update_session_timeout_from_config(self):
        """Test updating session timeout from configuration"""
        # Initial timeout
        self.assertEqual(self.session_interface.session_timeout, 7200)
        
        # Update configuration to return different timeout
        self.mock_config_service.get_config.return_value = 240  # 4 hours
        
        # Update timeout from config
        self.session_interface.update_session_timeout_from_config()
        
        # Verify timeout was updated
        self.assertEqual(self.session_interface.session_timeout, 14400)  # 240 * 60
    
    def test_update_session_timeout_no_change(self):
        """Test updating session timeout when value hasn't changed"""
        # Set up to return same timeout
        self.mock_config_service.get_config.return_value = 120  # Same as current
        
        original_timeout = self.session_interface.session_timeout
        
        # Update timeout from config
        self.session_interface.update_session_timeout_from_config()
        
        # Verify timeout remained the same
        self.assertEqual(self.session_interface.session_timeout, original_timeout)
    
    @patch('flask_redis_session_interface.datetime')
    def test_save_session_uses_current_timeout(self, mock_datetime):
        """Test that save_session uses current configured timeout"""
        # Mock datetime
        mock_now = datetime(2025, 8, 25, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
        
        # Create a mock session
        session = RedisSession({'user_id': 1}, sid='test-session-id', new=True)
        session.modified = True
        
        # Mock Flask app with all required config
        mock_app = Mock()
        mock_app.session_cookie_name = 'session'
        mock_app.config = {
            'SESSION_COOKIE_NAME': 'session',
            'SESSION_COOKIE_DOMAIN': None,
            'SESSION_COOKIE_PATH': '/',
            'SESSION_COOKIE_HTTPONLY': True,
            'SESSION_COOKIE_SECURE': False,
            'SESSION_COOKIE_SAMESITE': 'Lax'
        }
        
        # Mock response
        mock_response = Mock()
        
        # Update configuration to return different timeout
        self.mock_config_service.get_config.return_value = 180  # 3 hours
        
        # Save session
        self.session_interface.save_session(mock_app, session, mock_response)
        
        # Verify Redis setex was called with new timeout (180 * 60 = 10800)
        self.mock_redis.setex.assert_called()
        call_args = self.mock_redis.setex.call_args
        self.assertEqual(call_args[0][1], 10800)  # Second argument should be the timeout
    
    @patch('flask_redis_session_interface.datetime')
    def test_open_session_uses_current_timeout_for_expiration(self, mock_datetime):
        """Test that open_session uses current configured timeout for expiration check"""
        # Mock datetime
        mock_now = datetime(2025, 8, 25, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        mock_datetime.fromisoformat.return_value = mock_now - timedelta(hours=2, minutes=30)  # 2.5 hours ago
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
        
        # Mock session data in Redis
        session_data = {
            'user_id': 1,
            '_last_activity': (mock_now - timedelta(hours=2, minutes=30)).isoformat(),
            '_created_at': mock_now.isoformat()
        }
        import json
        self.mock_redis.get.return_value = json.dumps(session_data)
        
        # Mock Flask request
        mock_request = Mock()
        mock_request.cookies = {'session': 'test-session-id'}
        
        # Mock Flask app
        mock_app = Mock()
        mock_app.session_cookie_name = 'session'
        mock_app.config = {'SESSION_COOKIE_NAME': 'session'}
        
        # Test with timeout of 2 hours (session should be expired)
        self.mock_config_service.get_config.return_value = 120  # 2 hours
        
        session = self.session_interface.open_session(mock_app, mock_request)
        
        # Should create new session since old one expired
        self.assertTrue(session.new)
        
        # Test with timeout of 4 hours (session should be valid)
        self.mock_config_service.get_config.return_value = 240  # 4 hours
        self.mock_redis.get.return_value = json.dumps(session_data)  # Reset mock
        
        session = self.session_interface.open_session(mock_app, mock_request)
        
        # Should load existing session since it's not expired
        self.assertFalse(session.new)
        self.assertEqual(session.get('user_id'), 1)
    
    def test_backward_compatibility_without_config_service(self):
        """Test backward compatibility when no configuration service is provided"""
        interface = FlaskRedisSessionInterface(
            redis_client=self.mock_redis,
            session_timeout=3600
        )
        
        # Should work without configuration service
        self.assertEqual(interface.session_timeout, 3600)
        
        # Update method should not fail
        interface.update_session_timeout_from_config()
        self.assertEqual(interface.session_timeout, 3600)  # Should remain unchanged
    
    def test_configuration_service_failure_handling(self):
        """Test handling of configuration service failures"""
        # Mock configuration service to raise exception
        self.mock_config_service.get_config.side_effect = Exception("Service unavailable")
        
        # Should fall back to default timeout
        timeout = self.session_interface._get_configured_session_timeout()
        self.assertEqual(timeout, 7200)  # Default timeout
        
        # Update method should handle errors gracefully
        self.session_interface.update_session_timeout_from_config()
        self.assertEqual(self.session_interface.session_timeout, 7200)
    
    def test_session_timeout_conversion(self):
        """Test conversion from minutes to seconds"""
        test_cases = [
            (60, 3600),    # 1 hour
            (120, 7200),   # 2 hours
            (180, 10800),  # 3 hours
            (1440, 86400), # 24 hours
        ]
        
        for minutes, expected_seconds in test_cases:
            self.mock_config_service.get_config.return_value = minutes
            timeout = self.session_interface._get_configured_session_timeout()
            self.assertEqual(timeout, expected_seconds)
    
    def test_dynamic_timeout_updates(self):
        """Test that timeout can be updated dynamically during runtime"""
        # Start with 2 hours
        self.assertEqual(self.session_interface.session_timeout, 7200)
        
        # Update to 1 hour
        self.mock_config_service.get_config.return_value = 60
        self.session_interface.update_session_timeout_from_config()
        self.assertEqual(self.session_interface.session_timeout, 3600)
        
        # Update to 4 hours
        self.mock_config_service.get_config.return_value = 240
        self.session_interface.update_session_timeout_from_config()
        self.assertEqual(self.session_interface.session_timeout, 14400)
    
    def test_configuration_key_usage(self):
        """Test that correct configuration key is used"""
        # Verify the correct configuration key is requested
        self.session_interface._get_configured_session_timeout()
        self.mock_config_service.get_config.assert_called_with('session_timeout_minutes', 120)
    
    def test_default_fallback_values(self):
        """Test default fallback values when configuration is not available"""
        # Test with no configuration service
        interface = FlaskRedisSessionInterface(
            redis_client=self.mock_redis,
            session_timeout=5400  # 1.5 hours
        )
        
        self.assertEqual(interface._get_configured_session_timeout(), 5400)
        
        # Test with configuration service returning None
        self.mock_config_service.get_config.return_value = None
        timeout = self.session_interface._get_configured_session_timeout()
        self.assertEqual(timeout, 7200)  # Should use default


if __name__ == '__main__':
    unittest.main()
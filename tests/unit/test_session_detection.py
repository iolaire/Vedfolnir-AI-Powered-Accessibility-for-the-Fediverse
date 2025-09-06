# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit Tests for Session Detection Utility

Tests the session detection functionality that determines if a user
has previously logged in based on various session indicators.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add project root for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Mock Flask objects before importing our module
with patch('utils.session_detection.request'), patch('utils.session_detection.session'), patch('utils.session_detection.current_app'):
    from utils.session_detection import (
        has_previous_session,
        detect_previous_session,
        SessionDetectionResult,
        _check_flask_login_remember_token,
        _check_flask_session_data,
        _check_redis_session_data,
        _check_custom_session_cookies,
        _check_session_id_indicators,
        clear_session_indicators,
        get_session_detection_summary
    )

class TestSessionDetectionResult(unittest.TestCase):
    """Test SessionDetectionResult class"""
    
    def test_session_detection_result_creation(self):
        """Test creating SessionDetectionResult objects"""
        # Test default creation
        result = SessionDetectionResult()
        self.assertFalse(result.has_previous_session)
        self.assertEqual(result.detection_methods, [])
        self.assertEqual(result.session_indicators, {})
        
        # Test creation with parameters
        result = SessionDetectionResult(
            has_previous_session=True,
            detection_methods=['flask_session'],
            session_indicators={'user_id': 123}
        )
        self.assertTrue(result.has_previous_session)
        self.assertEqual(result.detection_methods, ['flask_session'])
        self.assertEqual(result.session_indicators, {'user_id': 123})
    
    def test_session_detection_result_boolean_evaluation(self):
        """Test boolean evaluation of SessionDetectionResult"""
        # False result
        result = SessionDetectionResult(has_previous_session=False)
        self.assertFalse(bool(result))
        
        # True result
        result = SessionDetectionResult(has_previous_session=True)
        self.assertTrue(bool(result))
    
    def test_session_detection_result_repr(self):
        """Test string representation of SessionDetectionResult"""
        result = SessionDetectionResult(
            has_previous_session=True,
            detection_methods=['flask_session']
        )
        repr_str = repr(result)
        self.assertIn('SessionDetectionResult', repr_str)
        self.assertIn('has_previous_session=True', repr_str)
        self.assertIn('flask_session', repr_str)

class TestFlaskLoginRememberToken(unittest.TestCase):
    """Test Flask-Login remember token detection"""
    
    @patch('utils.session_detection.request')
    def test_check_flask_login_remember_token_with_remember_token(self, mock_request):
        """Test detection of Flask-Login remember token cookie"""
        mock_request.cookies = {'remember_token': 'abc123def456ghi789'}
        
        result = _check_flask_login_remember_token()
        
        self.assertIsNotNone(result)
        self.assertEqual(result['source'], 'remember_token_cookie')
        self.assertIn('token', result)
        # Token should be truncated for security
        self.assertTrue(result['token'].endswith('...'))
    
    @patch('utils.session_detection.request')
    def test_check_flask_login_remember_token_with_session_cookie(self, mock_request):
        """Test detection of Flask session cookie"""
        mock_request.cookies = {'session': 'very_long_session_cookie_value_here'}
        
        result = _check_flask_login_remember_token()
        
        self.assertIsNotNone(result)
        self.assertEqual(result['source'], 'session_cookie')
        self.assertIn('token', result)
    
    @patch('utils.session_detection.request')
    def test_check_flask_login_remember_token_no_token(self, mock_request):
        """Test when no remember token is present"""
        mock_request.cookies = {}
        
        result = _check_flask_login_remember_token()
        
        self.assertIsNone(result)
    
    @patch('utils.session_detection.request')
    def test_check_flask_login_remember_token_short_session_cookie(self, mock_request):
        """Test with short session cookie (should be ignored)"""
        mock_request.cookies = {'session': 'short'}
        
        result = _check_flask_login_remember_token()
        
        self.assertIsNone(result)
    
    @patch('utils.session_detection.request')
    def test_check_flask_login_remember_token_exception_handling(self, mock_request):
        """Test exception handling in remember token check"""
        mock_request.cookies.get.side_effect = Exception("Cookie error")
        
        result = _check_flask_login_remember_token()
        
        self.assertIsNone(result)

class TestFlaskSessionData(unittest.TestCase):
    """Test Flask session data detection"""
    
    @patch('utils.session_detection.session')
    def test_check_flask_session_data_with_user_id(self, mock_session):
        """Test detection of user_id in Flask session"""
        mock_session.get.side_effect = lambda key: {
            'user_id': 123,
            'username': 'testuser'
        }.get(key)
        
        result = _check_flask_session_data()
        
        self.assertIsNotNone(result)
        self.assertEqual(result['user_id'], 123)
        self.assertEqual(result['username'], 'testuser')
    
    @patch('utils.session_detection.session')
    def test_check_flask_session_data_with_flask_login_user_id(self, mock_session):
        """Test detection of Flask-Login internal _user_id"""
        mock_session.get.side_effect = lambda key: {
            '_user_id': '456'
        }.get(key)
        
        result = _check_flask_session_data()
        
        self.assertIsNotNone(result)
        self.assertEqual(result['_user_id'], '456')
    
    @patch('utils.session_detection.session')
    def test_check_flask_session_data_with_platform_data(self, mock_session):
        """Test detection of platform connection data"""
        mock_session.get.side_effect = lambda key: {
            'platform_connection_id': 789,
            'csrf_token': 'csrf123'
        }.get(key)
        
        result = _check_flask_session_data()
        
        self.assertIsNotNone(result)
        self.assertEqual(result['platform_connection_id'], 789)
        self.assertTrue(result['has_csrf_token'])
    
    @patch('utils.session_detection.session')
    def test_check_flask_session_data_with_timestamps(self, mock_session):
        """Test detection of session timestamps"""
        mock_session.get.side_effect = lambda key: {
            'last_activity': '2025-01-01T12:00:00Z',
            'created_at': '2025-01-01T10:00:00Z'
        }.get(key)
        
        result = _check_flask_session_data()
        
        self.assertIsNotNone(result)
        self.assertEqual(result['last_activity'], '2025-01-01T12:00:00Z')
        self.assertEqual(result['created_at'], '2025-01-01T10:00:00Z')
    
    @patch('utils.session_detection.session')
    def test_check_flask_session_data_empty_session(self, mock_session):
        """Test with empty Flask session"""
        mock_session.get.return_value = None
        
        result = _check_flask_session_data()
        
        self.assertIsNone(result)
    
    @patch('utils.session_detection.session')
    def test_check_flask_session_data_exception_handling(self, mock_session):
        """Test exception handling in Flask session check"""
        mock_session.get.side_effect = Exception("Session error")
        
        result = _check_flask_session_data()
        
        self.assertIsNone(result)

class TestRedisSessionData(unittest.TestCase):
    """Test Redis session data detection"""
    
    @patch('utils.session_detection.current_app')
    @patch('utils.session_detection.session')
    def test_check_redis_session_data_with_active_session(self, mock_session, mock_current_app):
        """Test detection of active Redis session"""
        # Mock session manager
        mock_session_manager = Mock()
        mock_session_manager.get_session_data.return_value = {
            'user_id': 123,
            'platform_connection_id': 456,
            '_last_updated': '2025-01-01T12:00:00Z'
        }
        mock_current_app.session_manager = mock_session_manager
        
        # Mock Flask session with session ID
        mock_session.sid = 'test_session_id'
        
        result = _check_redis_session_data()
        
        self.assertIsNotNone(result)
        self.assertEqual(result['session_id'], 'test_session_id')
        self.assertTrue(result['has_user_id'])
        self.assertTrue(result['has_platform_data'])
        self.assertEqual(result['last_updated'], '2025-01-01T12:00:00Z')
    
    @patch('utils.session_detection.current_app')
    @patch('utils.session_detection.session')
    def test_check_redis_session_data_no_session_manager(self, mock_session, mock_current_app):
        """Test when no session manager is available"""
        mock_current_app.session_manager = None
        
        result = _check_redis_session_data()
        
        self.assertIsNone(result)
    
    @patch('utils.session_detection.current_app')
    @patch('utils.session_detection.session')
    def test_check_redis_session_data_no_session_id(self, mock_session, mock_current_app):
        """Test when no session ID is available"""
        mock_session_manager = Mock()
        mock_current_app.session_manager = mock_session_manager
        
        # No session ID
        mock_session.sid = None
        
        result = _check_redis_session_data()
        
        self.assertIsNone(result)
    
    @patch('utils.session_detection.current_app')
    @patch('utils.session_detection.session')
    def test_check_redis_session_data_no_redis_data(self, mock_session, mock_current_app):
        """Test when Redis returns no session data"""
        mock_session_manager = Mock()
        mock_session_manager.get_session_data.return_value = None
        mock_current_app.session_manager = mock_session_manager
        
        mock_session.sid = 'test_session_id'
        
        result = _check_redis_session_data()
        
        self.assertIsNone(result)
    
    @patch('utils.session_detection.current_app')
    @patch('utils.session_detection.session')
    def test_check_redis_session_data_exception_handling(self, mock_session, mock_current_app):
        """Test exception handling in Redis session check"""
        mock_session_manager = Mock()
        mock_session_manager.get_session_data.side_effect = Exception("Redis error")
        mock_current_app.session_manager = mock_session_manager
        
        mock_session.sid = 'test_session_id'
        
        result = _check_redis_session_data()
        
        self.assertIsNone(result)

class TestCustomSessionCookies(unittest.TestCase):
    """Test custom session cookie detection"""
    
    @patch('utils.session_detection.request')
    def test_check_custom_session_cookies_with_returning_user(self, mock_request):
        """Test detection of returning user cookie"""
        mock_request.cookies = {'vedfolnir_returning_user': 'true'}
        
        result = _check_custom_session_cookies()
        
        self.assertIsNotNone(result)
        self.assertEqual(result['returning_user'], 'true')
    
    @patch('utils.session_detection.request')
    def test_check_custom_session_cookies_with_last_visit(self, mock_request):
        """Test detection of last visit cookie"""
        mock_request.cookies = {'vedfolnir_last_visit': '2025-01-01T12:00:00Z'}
        
        result = _check_custom_session_cookies()
        
        self.assertIsNotNone(result)
        self.assertEqual(result['last_visit'], '2025-01-01T12:00:00Z')
    
    @patch('utils.session_detection.request')
    def test_check_custom_session_cookies_with_platform_preference(self, mock_request):
        """Test detection of platform preference cookie"""
        mock_request.cookies = {'vedfolnir_platform_preference': 'pixelfed'}
        
        result = _check_custom_session_cookies()
        
        self.assertIsNotNone(result)
        self.assertEqual(result['platform_preference'], 'pixelfed')
    
    @patch('utils.session_detection.request')
    def test_check_custom_session_cookies_with_other_vedfolnir_cookies(self, mock_request):
        """Test detection of other vedfolnir-prefixed cookies"""
        mock_request.cookies = {
            'vedfolnir_custom_setting': 'some_very_long_value_that_should_be_truncated',
            'other_cookie': 'ignored'
        }
        mock_request.cookies.items.return_value = [
            ('vedfolnir_custom_setting', 'some_very_long_value_that_should_be_truncated'),
            ('other_cookie', 'ignored')
        ]
        
        result = _check_custom_session_cookies()
        
        self.assertIsNotNone(result)
        self.assertIn('vedfolnir_custom_setting', result)
        self.assertTrue(result['vedfolnir_custom_setting'].endswith('...'))
        self.assertNotIn('other_cookie', result)
    
    @patch('utils.session_detection.request')
    def test_check_custom_session_cookies_no_cookies(self, mock_request):
        """Test when no custom cookies are present"""
        mock_request.cookies = {}
        
        result = _check_custom_session_cookies()
        
        self.assertIsNone(result)
    
    @patch('utils.session_detection.request')
    def test_check_custom_session_cookies_exception_handling(self, mock_request):
        """Test exception handling in custom cookie check"""
        mock_request.cookies.get.side_effect = Exception("Cookie error")
        
        result = _check_custom_session_cookies()
        
        self.assertIsNone(result)

class TestSessionIdIndicators(unittest.TestCase):
    """Test session ID indicator detection"""
    
    @patch('utils.session_detection.session')
    def test_check_session_id_indicators_with_flask_session_id(self, mock_session):
        """Test detection of Flask session ID"""
        mock_session.sid = 'flask_session_123'
        mock_session.get.return_value = None
        mock_session.permanent = False
        
        result = _check_session_id_indicators()
        
        self.assertIsNotNone(result)
        self.assertEqual(result['flask_session_id'], 'flask_session_123')
    
    @patch('utils.session_detection.session')
    def test_check_session_id_indicators_with_session_data_id(self, mock_session):
        """Test detection of session ID in session data"""
        mock_session.sid = None
        mock_session.get.side_effect = lambda key: {
            'session_id': 'data_session_456'
        }.get(key)
        mock_session.permanent = False
        
        result = _check_session_id_indicators()
        
        self.assertIsNotNone(result)
        self.assertEqual(result['session_data_id'], 'data_session_456')
    
    @patch('utils.session_detection.session')
    def test_check_session_id_indicators_with_permanent_session(self, mock_session):
        """Test detection of permanent session (remember me)"""
        mock_session.sid = None
        mock_session.get.return_value = None
        mock_session.permanent = True
        
        result = _check_session_id_indicators()
        
        self.assertIsNotNone(result)
        self.assertTrue(result['is_permanent'])
    
    @patch('utils.session_detection.session')
    def test_check_session_id_indicators_no_indicators(self, mock_session):
        """Test when no session ID indicators are present"""
        mock_session.sid = None
        mock_session.get.return_value = None
        mock_session.permanent = False
        
        result = _check_session_id_indicators()
        
        self.assertIsNone(result)
    
    @patch('utils.session_detection.session')
    def test_check_session_id_indicators_exception_handling(self, mock_session):
        """Test exception handling in session ID check"""
        mock_session.sid = None
        mock_session.get.side_effect = Exception("Session error")
        
        result = _check_session_id_indicators()
        
        self.assertIsNone(result)

class TestMainSessionDetection(unittest.TestCase):
    """Test main session detection functions"""
    
    @patch('utils.session_detection._check_flask_login_remember_token')
    @patch('utils.session_detection._check_flask_session_data')
    @patch('utils.session_detection._check_redis_session_data')
    @patch('utils.session_detection._check_custom_session_cookies')
    @patch('utils.session_detection._check_session_id_indicators')
    def test_detect_previous_session_with_multiple_indicators(self, mock_session_id, mock_custom, mock_redis, mock_flask_session, mock_remember):
        """Test detection with multiple session indicators"""
        mock_remember.return_value = {'token': 'abc...', 'source': 'remember_token_cookie'}
        mock_flask_session.return_value = {'user_id': 123}
        mock_redis.return_value = None
        mock_custom.return_value = None
        mock_session_id.return_value = None
        
        result = detect_previous_session()
        
        self.assertTrue(result.has_previous_session)
        self.assertIn('flask_login_remember_token', result.detection_methods)
        self.assertIn('flask_session_data', result.detection_methods)
        self.assertEqual(len(result.detection_methods), 2)
    
    @patch('utils.session_detection._check_flask_login_remember_token')
    @patch('utils.session_detection._check_flask_session_data')
    @patch('utils.session_detection._check_redis_session_data')
    @patch('utils.session_detection._check_custom_session_cookies')
    @patch('utils.session_detection._check_session_id_indicators')
    def test_detect_previous_session_no_indicators(self, mock_session_id, mock_custom, mock_redis, mock_flask_session, mock_remember):
        """Test detection with no session indicators"""
        mock_remember.return_value = None
        mock_flask_session.return_value = None
        mock_redis.return_value = None
        mock_custom.return_value = None
        mock_session_id.return_value = None
        
        result = detect_previous_session()
        
        self.assertFalse(result.has_previous_session)
        self.assertEqual(len(result.detection_methods), 0)
        self.assertEqual(result.session_indicators, {})
    
    @patch('utils.session_detection._check_flask_login_remember_token')
    def test_detect_previous_session_exception_handling(self, mock_remember):
        """Test exception handling in main detection function"""
        mock_remember.side_effect = Exception("Detection error")
        
        result = detect_previous_session()
        
        self.assertFalse(result.has_previous_session)
    
    @patch('utils.session_detection.detect_previous_session')
    def test_has_previous_session_true(self, mock_detect):
        """Test has_previous_session returns True"""
        mock_detect.return_value = SessionDetectionResult(has_previous_session=True)
        
        result = has_previous_session()
        
        self.assertTrue(result)
    
    @patch('utils.session_detection.detect_previous_session')
    def test_has_previous_session_false(self, mock_detect):
        """Test has_previous_session returns False"""
        mock_detect.return_value = SessionDetectionResult(has_previous_session=False)
        
        result = has_previous_session()
        
        self.assertFalse(result)

class TestUtilityFunctions(unittest.TestCase):
    """Test utility functions"""
    
    @patch('utils.session_detection.session')
    def test_clear_session_indicators(self, mock_session):
        """Test clearing session indicators"""
        result = clear_session_indicators()
        
        self.assertTrue(result)
        mock_session.clear.assert_called_once()
    
    @patch('utils.session_detection.session')
    def test_clear_session_indicators_exception_handling(self, mock_session):
        """Test exception handling in clear session indicators"""
        mock_session.clear.side_effect = Exception("Clear error")
        
        result = clear_session_indicators()
        
        self.assertFalse(result)
    
    @patch('utils.session_detection.detect_previous_session')
    @patch('utils.session_detection.request')
    @patch('utils.session_detection.session')
    def test_get_session_detection_summary(self, mock_session, mock_request, mock_detect):
        """Test getting session detection summary"""
        mock_detect.return_value = SessionDetectionResult(
            has_previous_session=True,
            detection_methods=['flask_session'],
            session_indicators={'user_id': 123}
        )
        mock_request.cookies = {'test': 'cookie'}
        mock_session.keys.return_value = ['user_id', 'csrf_token']
        mock_session.__len__.return_value = 2
        
        result = get_session_detection_summary()
        
        self.assertTrue(result['has_previous_session'])
        self.assertEqual(result['detection_methods'], ['flask_session'])
        self.assertEqual(result['method_count'], 1)
        self.assertTrue(result['request_info']['has_cookies'])
        self.assertEqual(result['request_info']['cookie_count'], 1)
        self.assertTrue(result['request_info']['has_flask_session'])
    
    @patch('utils.session_detection.detect_previous_session')
    def test_get_session_detection_summary_exception_handling(self, mock_detect):
        """Test exception handling in session detection summary"""
        mock_detect.side_effect = Exception("Summary error")
        
        result = get_session_detection_summary()
        
        self.assertFalse(result['has_previous_session'])
        self.assertIn('error', result)

if __name__ == '__main__':
    unittest.main()
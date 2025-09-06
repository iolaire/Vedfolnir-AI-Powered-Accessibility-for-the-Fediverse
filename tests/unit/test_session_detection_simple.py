# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Simple Unit Tests for Session Detection Utility

Tests the core session detection functionality without Flask context dependencies.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add project root for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from utils.session_detection import SessionDetectionResult

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

class TestSessionDetectionWithMocks(unittest.TestCase):
    """Test session detection with proper Flask mocking"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_request_patcher = patch('utils.session_detection.request')
        self.mock_session_patcher = patch('utils.session_detection.session')
        self.mock_current_app_patcher = patch('utils.session_detection.current_app')
        
        self.mock_request = self.mock_request_patcher.start()
        self.mock_session = self.mock_session_patcher.start()
        self.mock_current_app = self.mock_current_app_patcher.start()
    
    def tearDown(self):
        """Clean up test fixtures"""
        self.mock_request_patcher.stop()
        self.mock_session_patcher.stop()
        self.mock_current_app_patcher.stop()
    
    def test_has_previous_session_with_remember_token(self):
        """Test has_previous_session with remember token"""
        from utils.session_detection import has_previous_session
        
        # Mock request cookies with remember token
        self.mock_request.cookies = {'remember_token': 'abc123def456'}
        
        result = has_previous_session()
        
        self.assertTrue(result)
    
    def test_has_previous_session_with_flask_session_data(self):
        """Test has_previous_session with Flask session data"""
        from utils.session_detection import has_previous_session
        
        # Mock Flask session with user data
        self.mock_session.get.side_effect = lambda key: {
            'user_id': 123,
            'username': 'testuser'
        }.get(key)
        
        result = has_previous_session()
        
        self.assertTrue(result)
    
    def test_has_previous_session_no_indicators(self):
        """Test has_previous_session with no session indicators"""
        from utils.session_detection import has_previous_session
        
        # Mock empty request and session
        self.mock_request.cookies = {}
        self.mock_session.get.return_value = None
        self.mock_current_app.session_manager = None
        
        result = has_previous_session()
        
        self.assertFalse(result)
    
    def test_detect_previous_session_comprehensive(self):
        """Test comprehensive session detection"""
        from utils.session_detection import detect_previous_session
        
        # Mock multiple session indicators
        self.mock_request.cookies = {
            'remember_token': 'abc123',
            'vedfolnir_returning_user': 'true'
        }
        self.mock_session.get.side_effect = lambda key: {
            'user_id': 123,
            'csrf_token': 'csrf123'
        }.get(key)
        
        result = detect_previous_session()
        
        self.assertTrue(result.has_previous_session)
        self.assertIn('flask_login_remember_token', result.detection_methods)
        self.assertIn('flask_session_data', result.detection_methods)
        self.assertIn('custom_session_cookies', result.detection_methods)
        self.assertGreater(len(result.detection_methods), 1)
    
    def test_detect_previous_session_exception_handling(self):
        """Test exception handling in session detection"""
        from utils.session_detection import detect_previous_session
        
        # Mock exception in request.cookies
        self.mock_request.cookies.get.side_effect = Exception("Cookie error")
        
        result = detect_previous_session()
        
        # Should return safe default (no previous session)
        self.assertFalse(result.has_previous_session)
        self.assertEqual(len(result.detection_methods), 0)

class TestSessionDetectionHelpers(unittest.TestCase):
    """Test individual session detection helper functions"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_request_patcher = patch('utils.session_detection.request')
        self.mock_session_patcher = patch('utils.session_detection.session')
        self.mock_current_app_patcher = patch('utils.session_detection.current_app')
        
        self.mock_request = self.mock_request_patcher.start()
        self.mock_session = self.mock_session_patcher.start()
        self.mock_current_app = self.mock_current_app_patcher.start()
    
    def tearDown(self):
        """Clean up test fixtures"""
        self.mock_request_patcher.stop()
        self.mock_session_patcher.stop()
        self.mock_current_app_patcher.stop()
    
    def test_check_flask_login_remember_token_success(self):
        """Test successful remember token detection"""
        from utils.session_detection import _check_flask_login_remember_token
        
        self.mock_request.cookies = {'remember_token': 'abc123def456ghi789'}
        
        result = _check_flask_login_remember_token()
        
        self.assertIsNotNone(result)
        self.assertEqual(result['source'], 'remember_token_cookie')
        self.assertIn('token', result)
        self.assertTrue(result['token'].endswith('...'))
    
    def test_check_flask_session_data_success(self):
        """Test successful Flask session data detection"""
        from utils.session_detection import _check_flask_session_data
        
        self.mock_session.get.side_effect = lambda key: {
            'user_id': 123,
            'username': 'testuser',
            'platform_connection_id': 456
        }.get(key)
        
        result = _check_flask_session_data()
        
        self.assertIsNotNone(result)
        self.assertEqual(result['user_id'], 123)
        self.assertEqual(result['username'], 'testuser')
        self.assertEqual(result['platform_connection_id'], 456)
    
    def test_check_custom_session_cookies_success(self):
        """Test successful custom cookie detection"""
        from utils.session_detection import _check_custom_session_cookies
        
        self.mock_request.cookies = {
            'vedfolnir_returning_user': 'true',
            'vedfolnir_last_visit': '2025-01-01T12:00:00Z',
            'other_cookie': 'ignored'
        }
        self.mock_request.cookies.items.return_value = [
            ('vedfolnir_returning_user', 'true'),
            ('vedfolnir_last_visit', '2025-01-01T12:00:00Z'),
            ('other_cookie', 'ignored')
        ]
        
        result = _check_custom_session_cookies()
        
        self.assertIsNotNone(result)
        self.assertEqual(result['returning_user'], 'true')
        self.assertEqual(result['last_visit'], '2025-01-01T12:00:00Z')
        self.assertNotIn('other_cookie', result)
    
    def test_check_redis_session_data_success(self):
        """Test successful Redis session data detection"""
        from utils.session_detection import _check_redis_session_data
        
        # Mock session manager
        mock_session_manager = Mock()
        mock_session_manager.get_session_data.return_value = {
            'user_id': 123,
            'platform_connection_id': 456,
            '_last_updated': '2025-01-01T12:00:00Z'
        }
        self.mock_current_app.session_manager = mock_session_manager
        
        # Mock Flask session with session ID
        self.mock_session.sid = 'test_session_id'
        
        result = _check_redis_session_data()
        
        self.assertIsNotNone(result)
        self.assertEqual(result['session_id'], 'test_session_id')
        self.assertTrue(result['has_user_id'])
        self.assertTrue(result['has_platform_data'])
    
    def test_check_session_id_indicators_success(self):
        """Test successful session ID indicator detection"""
        from utils.session_detection import _check_session_id_indicators
        
        self.mock_session.sid = 'flask_session_123'
        self.mock_session.get.side_effect = lambda key: {
            'session_id': 'data_session_456'
        }.get(key)
        self.mock_session.permanent = True
        
        result = _check_session_id_indicators()
        
        self.assertIsNotNone(result)
        self.assertEqual(result['flask_session_id'], 'flask_session_123')
        self.assertEqual(result['session_data_id'], 'data_session_456')
        self.assertTrue(result['is_permanent'])

if __name__ == '__main__':
    unittest.main()
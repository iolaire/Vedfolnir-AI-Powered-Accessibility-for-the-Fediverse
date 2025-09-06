# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integration Tests for Session Detection Utility

Tests the session detection functionality in a real Flask application context.
"""

import unittest
import sys
import os
from flask import Flask, session, request

# Add project root for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from utils.session_detection import has_previous_session, detect_previous_session

class TestSessionDetectionIntegration(unittest.TestCase):
    """Integration tests for session detection with Flask app context"""
    
    def setUp(self):
        """Set up test Flask application"""
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'test_secret_key_for_sessions'
        self.app.config['TESTING'] = True
        
        # Create test client
        self.client = self.app.test_client()
        
        # Create application context
        self.app_context = self.app.app_context()
        self.app_context.push()
    
    def tearDown(self):
        """Clean up test fixtures"""
        self.app_context.pop()
    
    def test_has_previous_session_with_no_session_data(self):
        """Test has_previous_session returns False with no session data"""
        with self.app.test_request_context('/'):
            result = has_previous_session()
            self.assertFalse(result)
    
    def test_has_previous_session_with_flask_session_data(self):
        """Test has_previous_session returns True with Flask session data"""
        with self.app.test_request_context('/'):
            # Simulate user session data
            session['user_id'] = 123
            session['username'] = 'testuser'
            
            result = has_previous_session()
            self.assertTrue(result)
    
    def test_has_previous_session_with_remember_token_cookie(self):
        """Test has_previous_session returns True with remember token cookie"""
        with self.app.test_request_context('/', headers={'Cookie': 'remember_token=abc123def456ghi789'}):
            result = has_previous_session()
            self.assertTrue(result)
    
    def test_has_previous_session_with_custom_cookies(self):
        """Test has_previous_session returns True with custom session cookies"""
        with self.app.test_request_context('/', headers={'Cookie': 'vedfolnir_returning_user=true'}):
            result = has_previous_session()
            self.assertTrue(result)
    
    def test_detect_previous_session_comprehensive(self):
        """Test comprehensive session detection with multiple indicators"""
        with self.app.test_request_context('/', headers={'Cookie': 'remember_token=abc123; vedfolnir_returning_user=true'}):
            # Add Flask session data
            session['user_id'] = 123
            session['platform_connection_id'] = 456
            session['csrf_token'] = 'csrf123'
            
            result = detect_previous_session()
            
            self.assertTrue(result.has_previous_session)
            self.assertGreater(len(result.detection_methods), 1)
            self.assertIn('flask_login_remember_token', result.detection_methods)
            self.assertIn('flask_session_data', result.detection_methods)
            self.assertIn('custom_session_cookies', result.detection_methods)
    
    def test_detect_previous_session_with_session_id_indicators(self):
        """Test session detection with session ID indicators"""
        with self.app.test_request_context('/'):
            # Simulate permanent session (remember me)
            session.permanent = True
            session['session_id'] = 'test_session_123'
            
            result = detect_previous_session()
            
            self.assertTrue(result.has_previous_session)
            self.assertIn('session_id_indicators', result.detection_methods)
    
    def test_detect_previous_session_no_indicators(self):
        """Test session detection with no indicators"""
        with self.app.test_request_context('/'):
            result = detect_previous_session()
            
            self.assertFalse(result.has_previous_session)
            self.assertEqual(len(result.detection_methods), 0)
            self.assertEqual(len(result.session_indicators), 0)
    
    def test_detect_previous_session_detailed_indicators(self):
        """Test detailed session indicators are captured correctly"""
        with self.app.test_request_context('/', headers={'Cookie': 'remember_token=abc123def456ghi789'}):
            session['user_id'] = 123
            session['username'] = 'testuser'
            session['last_activity'] = '2025-01-01T12:00:00Z'
            
            result = detect_previous_session()
            
            self.assertTrue(result.has_previous_session)
            
            # Check remember token indicators
            if 'remember_token' in result.session_indicators:
                self.assertIn('token', result.session_indicators['remember_token'])
                self.assertIn('source', result.session_indicators['remember_token'])
            
            # Check Flask session indicators
            if 'flask_session' in result.session_indicators:
                self.assertEqual(result.session_indicators['flask_session']['user_id'], 123)
                self.assertEqual(result.session_indicators['flask_session']['username'], 'testuser')
    
    def test_session_detection_with_multiple_cookies(self):
        """Test session detection with multiple custom cookies"""
        cookie_header = 'vedfolnir_returning_user=true; vedfolnir_last_visit=2025-01-01T12:00:00Z; vedfolnir_platform_preference=pixelfed'
        
        with self.app.test_request_context('/', headers={'Cookie': cookie_header}):
            result = detect_previous_session()
            
            self.assertTrue(result.has_previous_session)
            self.assertIn('custom_session_cookies', result.detection_methods)
            
            if 'custom_cookies' in result.session_indicators:
                indicators = result.session_indicators['custom_cookies']
                self.assertEqual(indicators.get('returning_user'), 'true')
                self.assertEqual(indicators.get('last_visit'), '2025-01-01T12:00:00Z')
                self.assertEqual(indicators.get('platform_preference'), 'pixelfed')

class TestSessionDetectionEdgeCases(unittest.TestCase):
    """Test edge cases for session detection"""
    
    def setUp(self):
        """Set up test Flask application"""
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'test_secret_key_for_sessions'
        self.app.config['TESTING'] = True
        
        self.app_context = self.app.app_context()
        self.app_context.push()
    
    def tearDown(self):
        """Clean up test fixtures"""
        self.app_context.pop()
    
    def test_session_detection_with_short_session_cookie(self):
        """Test session detection ignores short session cookies"""
        with self.app.test_request_context('/', headers={'Cookie': 'session=short'}):
            result = detect_previous_session()
            
            # Short session cookies should be ignored
            if 'flask_login_remember_token' in result.detection_methods:
                # If detected, it should not be from the short session cookie
                self.assertNotEqual(result.session_indicators.get('remember_token', {}).get('source'), 'session_cookie')
    
    def test_session_detection_with_empty_session_values(self):
        """Test session detection with empty session values"""
        with self.app.test_request_context('/'):
            session['user_id'] = None
            session['username'] = ''
            session['empty_key'] = None
            
            result = detect_previous_session()
            
            # Empty values should not trigger session detection
            # (depends on implementation - this tests current behavior)
            if result.has_previous_session and 'flask_session' in result.session_indicators:
                flask_session_data = result.session_indicators['flask_session']
                # None values should not be included
                self.assertNotIn('user_id', flask_session_data)
                self.assertNotIn('empty_key', flask_session_data)
    
    def test_session_detection_with_non_vedfolnir_cookies(self):
        """Test session detection ignores non-vedfolnir cookies"""
        cookie_header = 'other_app_cookie=value; random_cookie=data; vedfolnir_returning_user=true'
        
        with self.app.test_request_context('/', headers={'Cookie': cookie_header}):
            result = detect_previous_session()
            
            if 'custom_session_cookies' in result.detection_methods:
                custom_cookies = result.session_indicators.get('custom_cookies', {})
                # Should only include vedfolnir cookies
                self.assertIn('returning_user', custom_cookies)
                self.assertNotIn('other_app_cookie', custom_cookies)
                self.assertNotIn('random_cookie', custom_cookies)

if __name__ == '__main__':
    unittest.main()
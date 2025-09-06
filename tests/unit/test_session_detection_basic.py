# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Basic Unit Tests for Session Detection Utility

Tests the core session detection functionality without Flask context dependencies.
This focuses on testing the SessionDetectionResult class and basic functionality.
"""

import unittest
import sys
import os

# Add project root for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from utils.session_detection import SessionDetectionResult

class TestSessionDetectionResult(unittest.TestCase):
    """Test SessionDetectionResult class"""
    
    def test_session_detection_result_creation_default(self):
        """Test creating SessionDetectionResult with default values"""
        result = SessionDetectionResult()
        self.assertFalse(result.has_previous_session)
        self.assertEqual(result.detection_methods, [])
        self.assertEqual(result.session_indicators, {})
    
    def test_session_detection_result_creation_with_data(self):
        """Test creating SessionDetectionResult with data"""
        result = SessionDetectionResult(
            has_previous_session=True,
            detection_methods=['flask_session', 'remember_token'],
            session_indicators={'user_id': 123, 'username': 'testuser'}
        )
        self.assertTrue(result.has_previous_session)
        self.assertEqual(result.detection_methods, ['flask_session', 'remember_token'])
        self.assertEqual(result.session_indicators, {'user_id': 123, 'username': 'testuser'})
    
    def test_session_detection_result_boolean_evaluation_false(self):
        """Test boolean evaluation returns False for no previous session"""
        result = SessionDetectionResult(has_previous_session=False)
        self.assertFalse(bool(result))
        self.assertFalse(result)  # Direct boolean evaluation
    
    def test_session_detection_result_boolean_evaluation_true(self):
        """Test boolean evaluation returns True for previous session"""
        result = SessionDetectionResult(has_previous_session=True)
        self.assertTrue(bool(result))
        self.assertTrue(result)  # Direct boolean evaluation
    
    def test_session_detection_result_repr(self):
        """Test string representation of SessionDetectionResult"""
        result = SessionDetectionResult(
            has_previous_session=True,
            detection_methods=['flask_session', 'remember_token']
        )
        repr_str = repr(result)
        self.assertIn('SessionDetectionResult', repr_str)
        self.assertIn('has_previous_session=True', repr_str)
        self.assertIn('flask_session', repr_str)
        self.assertIn('remember_token', repr_str)
    
    def test_session_detection_result_repr_empty(self):
        """Test string representation of empty SessionDetectionResult"""
        result = SessionDetectionResult()
        repr_str = repr(result)
        self.assertIn('SessionDetectionResult', repr_str)
        self.assertIn('has_previous_session=False', repr_str)
        self.assertIn('methods=[]', repr_str)

class TestSessionDetectionLogic(unittest.TestCase):
    """Test session detection logic without Flask dependencies"""
    
    def test_session_detection_result_with_multiple_methods(self):
        """Test SessionDetectionResult with multiple detection methods"""
        methods = ['flask_login_remember_token', 'flask_session_data', 'custom_session_cookies']
        indicators = {
            'remember_token': {'token': 'abc...', 'source': 'remember_token_cookie'},
            'flask_session': {'user_id': 123, 'username': 'testuser'},
            'custom_cookies': {'returning_user': 'true'}
        }
        
        result = SessionDetectionResult(
            has_previous_session=True,
            detection_methods=methods,
            session_indicators=indicators
        )
        
        self.assertTrue(result.has_previous_session)
        self.assertEqual(len(result.detection_methods), 3)
        self.assertIn('flask_login_remember_token', result.detection_methods)
        self.assertIn('flask_session_data', result.detection_methods)
        self.assertIn('custom_session_cookies', result.detection_methods)
        self.assertEqual(result.session_indicators['remember_token']['token'], 'abc...')
        self.assertEqual(result.session_indicators['flask_session']['user_id'], 123)
        self.assertEqual(result.session_indicators['custom_cookies']['returning_user'], 'true')
    
    def test_session_detection_result_with_single_method(self):
        """Test SessionDetectionResult with single detection method"""
        result = SessionDetectionResult(
            has_previous_session=True,
            detection_methods=['flask_session_data'],
            session_indicators={'user_id': 456}
        )
        
        self.assertTrue(result.has_previous_session)
        self.assertEqual(len(result.detection_methods), 1)
        self.assertEqual(result.detection_methods[0], 'flask_session_data')
        self.assertEqual(result.session_indicators['user_id'], 456)
    
    def test_session_detection_result_no_methods_no_session(self):
        """Test SessionDetectionResult with no methods means no session"""
        result = SessionDetectionResult(
            has_previous_session=False,
            detection_methods=[],
            session_indicators={}
        )
        
        self.assertFalse(result.has_previous_session)
        self.assertEqual(len(result.detection_methods), 0)
        self.assertEqual(len(result.session_indicators), 0)
    
    def test_session_detection_result_consistency(self):
        """Test consistency between has_previous_session and detection_methods"""
        # If we have detection methods, we should have a previous session
        result_with_methods = SessionDetectionResult(
            has_previous_session=True,
            detection_methods=['flask_session_data'],
            session_indicators={'user_id': 123}
        )
        
        self.assertTrue(result_with_methods.has_previous_session)
        self.assertGreater(len(result_with_methods.detection_methods), 0)
        
        # If we have no detection methods, we should have no previous session
        result_no_methods = SessionDetectionResult(
            has_previous_session=False,
            detection_methods=[],
            session_indicators={}
        )
        
        self.assertFalse(result_no_methods.has_previous_session)
        self.assertEqual(len(result_no_methods.detection_methods), 0)

class TestSessionDetectionDataStructures(unittest.TestCase):
    """Test session detection data structures and edge cases"""
    
    def test_session_indicators_various_data_types(self):
        """Test session indicators with various data types"""
        indicators = {
            'string_value': 'test_string',
            'integer_value': 123,
            'boolean_value': True,
            'dict_value': {'nested': 'data'},
            'list_value': ['item1', 'item2'],
            'none_value': None
        }
        
        result = SessionDetectionResult(
            has_previous_session=True,
            detection_methods=['test_method'],
            session_indicators=indicators
        )
        
        self.assertEqual(result.session_indicators['string_value'], 'test_string')
        self.assertEqual(result.session_indicators['integer_value'], 123)
        self.assertTrue(result.session_indicators['boolean_value'])
        self.assertEqual(result.session_indicators['dict_value']['nested'], 'data')
        self.assertEqual(result.session_indicators['list_value'], ['item1', 'item2'])
        self.assertIsNone(result.session_indicators['none_value'])
    
    def test_detection_methods_list_operations(self):
        """Test detection methods list operations"""
        methods = ['method1', 'method2', 'method3']
        result = SessionDetectionResult(
            has_previous_session=True,
            detection_methods=methods,
            session_indicators={}
        )
        
        # Test list operations
        self.assertIn('method1', result.detection_methods)
        self.assertIn('method2', result.detection_methods)
        self.assertIn('method3', result.detection_methods)
        self.assertNotIn('method4', result.detection_methods)
        self.assertEqual(len(result.detection_methods), 3)
        self.assertEqual(result.detection_methods[0], 'method1')
        self.assertEqual(result.detection_methods[-1], 'method3')
    
    def test_empty_session_indicators(self):
        """Test handling of empty session indicators"""
        result = SessionDetectionResult(
            has_previous_session=False,
            detection_methods=[],
            session_indicators={}
        )
        
        self.assertEqual(len(result.session_indicators), 0)
        self.assertNotIn('any_key', result.session_indicators)
        self.assertEqual(list(result.session_indicators.keys()), [])
        self.assertEqual(list(result.session_indicators.values()), [])

if __name__ == '__main__':
    unittest.main()
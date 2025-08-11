#!/usr/bin/env python3

"""
Simplified Tests for Safe Template Context Processor

This module tests the safe template context processor functionality
with simplified mocking to avoid Flask context issues.
"""

import unittest
from unittest.mock import Mock, patch

# Import the module under test
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from safe_template_context import (
    _get_safe_user_data,
    _get_safe_platforms_data,
    _platform_to_safe_dict,
    _query_platforms_fallback,
    _handle_detached_error_fallback,
    create_safe_template_context_processor
)


class MockUser:
    """Mock user class for testing"""
    def __init__(self, user_id=1, username="testuser", email="test@example.com", role="user", is_active=True):
        self.id = user_id
        self.username = username
        self.email = email
        self.role = role
        self.is_active = is_active
        self.platforms = []
    
    def get_id(self):
        return str(self.id)


class MockPlatform:
    """Mock platform class for testing"""
    def __init__(self, platform_id=1, name="Test Platform", platform_type="mastodon", 
                 instance_url="https://test.social", username="testuser", 
                 is_active=True, is_default=False):
        self.id = platform_id
        self.name = name
        self.platform_type = platform_type
        self.instance_url = instance_url
        self.username = username
        self.is_active = is_active
        self.is_default = is_default
        self.created_at = "2024-01-01"
        self.updated_at = "2024-01-01"
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'platform_type': self.platform_type,
            'instance_url': self.instance_url,
            'username': self.username,
            'is_active': self.is_active,
            'is_default': self.is_default,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }


class TestSafeTemplateContextSimple(unittest.TestCase):
    """Simplified test cases for safe template context processor"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_handler = Mock()
        self.mock_session_manager = Mock()
        self.mock_session = Mock()
        
        self.mock_session_manager.get_request_session.return_value = self.mock_session
        
        # Create test user and platforms
        self.test_user = MockUser()
        self.test_platform = MockPlatform()
        self.test_user.platforms = [self.test_platform]
    
    def test_get_safe_user_data_success(self):
        """Test successful user data extraction"""
        self.mock_handler.safe_access.side_effect = lambda obj, attr, default=None: getattr(obj, attr, default)
        
        result = _get_safe_user_data(self.test_user, self.mock_handler)
        
        expected = {
            'id': 1,
            'username': 'testuser',
            'email': 'test@example.com',
            'role': 'user',
            'is_active': True
        }
        
        self.assertEqual(result, expected)
    
    def test_get_safe_user_data_with_error(self):
        """Test user data extraction with error"""
        self.mock_handler.safe_access.side_effect = Exception("Test error")
        
        result = _get_safe_user_data(self.test_user, self.mock_handler)
        
        # Should return fallback data
        self.assertEqual(result['username'], 'Unknown')
        self.assertEqual(result['role'], 'user')
        self.assertTrue(result['is_active'])
    
    def test_get_safe_platforms_data_success(self):
        """Test successful platform data extraction"""
        self.mock_handler.safe_relationship_access.return_value = [self.test_platform]
        self.mock_handler.safe_access.side_effect = lambda obj, attr, default=None: getattr(obj, attr, default)
        
        result = _get_safe_platforms_data(self.test_user, self.mock_handler, self.mock_session_manager)
        
        self.assertEqual(len(result['user_platforms']), 1)
        self.assertEqual(result['platform_count'], 1)
        self.assertIsNotNone(result['active_platform'])  # First active platform becomes active
    
    def test_get_safe_platforms_data_with_default(self):
        """Test platform data extraction with default platform"""
        default_platform = MockPlatform(platform_id=2, name="Default Platform", is_default=True)
        self.mock_handler.safe_relationship_access.return_value = [self.test_platform, default_platform]
        self.mock_handler.safe_access.side_effect = lambda obj, attr, default=None: getattr(obj, attr, default)
        
        result = _get_safe_platforms_data(self.test_user, self.mock_handler, self.mock_session_manager)
        
        self.assertEqual(len(result['user_platforms']), 2)
        self.assertEqual(result['platform_count'], 2)
        self.assertIsNotNone(result['active_platform'])
        self.assertEqual(result['active_platform']['name'], 'Default Platform')
    
    def test_get_safe_platforms_data_fallback_query(self):
        """Test platform data extraction with fallback query"""
        self.mock_handler.safe_relationship_access.return_value = []
        
        # Mock the fallback query
        with patch('safe_template_context._query_platforms_fallback') as mock_fallback:
            mock_fallback.return_value = [self.test_platform]
            self.mock_handler.safe_access.side_effect = lambda obj, attr, default=None: getattr(obj, attr, default)
            
            result = _get_safe_platforms_data(self.test_user, self.mock_handler, self.mock_session_manager)
            
            self.assertEqual(len(result['user_platforms']), 1)
            mock_fallback.assert_called_once()
    
    def test_platform_to_safe_dict_with_to_dict_method(self):
        """Test platform conversion using to_dict method"""
        result = _platform_to_safe_dict(self.test_platform, self.mock_handler)
        
        expected = {
            'id': 1,
            'name': 'Test Platform',
            'platform_type': 'mastodon',
            'instance_url': 'https://test.social',
            'username': 'testuser',
            'is_active': True,
            'is_default': False,
            'created_at': '2024-01-01',
            'updated_at': '2024-01-01'
        }
        
        self.assertEqual(result, expected)
    
    def test_platform_to_safe_dict_manual_extraction(self):
        """Test platform conversion with manual extraction"""
        # Create platform without to_dict method
        platform = Mock()
        platform.to_dict = None
        
        self.mock_handler.safe_access.side_effect = lambda obj, attr, default=None: {
            'id': 1,
            'name': 'Manual Platform',
            'platform_type': 'pixelfed',
            'instance_url': 'https://pixelfed.social',
            'username': 'testuser',
            'is_active': True,
            'is_default': False,
            'created_at': '2024-01-01',
            'updated_at': '2024-01-01'
        }.get(attr, default)
        
        result = _platform_to_safe_dict(platform, self.mock_handler)
        
        self.assertEqual(result['name'], 'Manual Platform')
        self.assertEqual(result['platform_type'], 'pixelfed')
    
    def test_platform_to_safe_dict_with_detached_error(self):
        """Test platform conversion handles DetachedInstanceError"""
        from sqlalchemy.orm.exc import DetachedInstanceError
        
        platform = Mock()
        platform.to_dict.side_effect = DetachedInstanceError("Test error")
        
        self.mock_handler.safe_access.side_effect = lambda obj, attr, default=None: getattr(self.test_platform, attr, default)
        
        result = _platform_to_safe_dict(platform, self.mock_handler)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['name'], 'Test Platform')
    
    def test_platform_to_safe_dict_with_error(self):
        """Test platform conversion handles general errors"""
        platform = Mock()
        platform.to_dict.side_effect = Exception("Test error")
        self.mock_handler.safe_access.side_effect = Exception("Handler error")
        
        result = _platform_to_safe_dict(platform, self.mock_handler)
        
        self.assertIsNone(result)
    
    @patch('safe_template_context.PlatformConnection', create=True)
    def test_query_platforms_fallback_success(self, mock_platform_connection):
        """Test successful fallback platform query"""
        self.mock_handler.safe_access.return_value = 1
        mock_platforms = [self.test_platform]
        self.mock_session.query.return_value.filter_by.return_value.all.return_value = mock_platforms
        
        result = _query_platforms_fallback(self.test_user, self.mock_handler, self.mock_session_manager)
        
        self.assertEqual(result, mock_platforms)
        self.mock_session.query.assert_called_once()
    
    @patch('safe_template_context.PlatformConnection', create=True)
    def test_query_platforms_fallback_no_user_id(self, mock_platform_connection):
        """Test fallback query when user ID is not available"""
        self.mock_handler.safe_access.return_value = None
        
        result = _query_platforms_fallback(self.test_user, self.mock_handler, self.mock_session_manager)
        
        self.assertEqual(result, [])
    
    @patch('safe_template_context.PlatformConnection', create=True)
    def test_query_platforms_fallback_with_error(self, mock_platform_connection):
        """Test fallback query handles errors"""
        self.mock_handler.safe_access.return_value = 1
        self.mock_session.query.side_effect = Exception("Query error")
        
        result = _query_platforms_fallback(self.test_user, self.mock_handler, self.mock_session_manager)
        
        self.assertEqual(result, [])
    
    def test_handle_detached_error_fallback(self):
        """Test detached error fallback handling"""
        # Create a simple mock user that doesn't cause Flask context issues
        mock_current_user = Mock()
        mock_current_user.get_id.return_value = "1"
        
        context = {
            'template_error': True,
            'current_user_safe': None,
            'user_platforms': ['old_data'],
            'active_platform': 'old_platform',
            'platform_count': 1
        }
        
        with patch('safe_template_context.current_user', mock_current_user):
            _handle_detached_error_fallback(context, self.mock_session_manager)
        
        self.assertIsNotNone(context['current_user_safe'])
        self.assertEqual(context['current_user_safe']['id'], "1")
        self.assertEqual(context['user_platforms'], [])
        self.assertIsNone(context['active_platform'])
        self.assertEqual(context['platform_count'], 0)
    
    def test_handle_detached_error_fallback_with_error(self):
        """Test detached error fallback handling when get_id fails"""
        mock_current_user = Mock()
        mock_current_user.get_id.side_effect = Exception("Error getting ID")
        
        context = {
            'template_error': True,
            'current_user_safe': None,
            'user_platforms': ['old_data'],
            'active_platform': 'old_platform',
            'platform_count': 1
        }
        
        with patch('safe_template_context.current_user', mock_current_user):
            _handle_detached_error_fallback(context, self.mock_session_manager)
        
        # Should still clear platform data even if user ID fails
        self.assertEqual(context['user_platforms'], [])
        self.assertIsNone(context['active_platform'])
        self.assertEqual(context['platform_count'], 0)
    
    def test_create_safe_template_context_processor(self):
        """Test template context processor registration"""
        mock_app = Mock()
        
        create_safe_template_context_processor(mock_app)
        
        mock_app.context_processor.assert_called_once()
    
    def test_get_safe_platforms_data_empty_platforms(self):
        """Test platform data extraction with no platforms"""
        self.mock_handler.safe_relationship_access.return_value = []
        
        with patch('safe_template_context._query_platforms_fallback') as mock_fallback:
            mock_fallback.return_value = []
            
            result = _get_safe_platforms_data(self.test_user, self.mock_handler, self.mock_session_manager)
            
            self.assertEqual(len(result['user_platforms']), 0)
            self.assertEqual(result['platform_count'], 0)
            self.assertIsNone(result['active_platform'])
    
    def test_get_safe_platforms_data_with_error(self):
        """Test platform data extraction handles errors gracefully"""
        self.mock_handler.safe_relationship_access.side_effect = Exception("Relationship error")
        
        with patch('safe_template_context._query_platforms_fallback') as mock_fallback:
            mock_fallback.side_effect = Exception("Fallback error")
            
            result = _get_safe_platforms_data(self.test_user, self.mock_handler, self.mock_session_manager)
            
            self.assertEqual(len(result['user_platforms']), 0)
            self.assertEqual(result['platform_count'], 0)
            self.assertIsNone(result['active_platform'])
    
    def test_platform_to_safe_dict_missing_to_dict(self):
        """Test platform conversion when to_dict method is missing"""
        platform = Mock()
        del platform.to_dict  # Remove the method entirely
        
        self.mock_handler.safe_access.side_effect = lambda obj, attr, default=None: getattr(self.test_platform, attr, default)
        
        result = _platform_to_safe_dict(platform, self.mock_handler)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['name'], 'Test Platform')


if __name__ == '__main__':
    unittest.main()
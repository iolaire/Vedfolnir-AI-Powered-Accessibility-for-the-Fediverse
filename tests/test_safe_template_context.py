#!/usr/bin/env python3

"""
Tests for Safe Template Context Processor

This module tests the safe template context processor functionality,
including error handling and fallback mechanisms.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch, create_autospec
from sqlalchemy.orm.exc import DetachedInstanceError
from sqlalchemy.exc import SQLAlchemyError

# Import the module under test
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from safe_template_context import (
    safe_template_context,
    _get_safe_user_data,
    _get_safe_platforms_data,
    _platform_to_safe_dict,
    _query_platforms_fallback,
    _handle_detached_error_fallback,
    create_safe_template_context_processor,
    get_safe_user_context
)


class MockUser:
    """Mock user class for testing"""
    def __init__(self, user_id=1, username="testuser", email="test@test.com", role="user", is_active=True):
        self.id = user_id
        self.username = username
        self.email = email
        self.role = role
        self.is_active = is_active
        self.platforms = []
        self.is_authenticated = True
    
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


class TestSafeTemplateContext(unittest.TestCase):
    """Test cases for safe template context processor"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_app = Mock()
        self.mock_session_manager = Mock()
        self.mock_handler = Mock()
        self.mock_session = Mock()
        
        # Configure mocks
        self.mock_app.request_session_manager = self.mock_session_manager
        self.mock_app.detached_instance_handler = self.mock_handler
        self.mock_session_manager.get_request_session.return_value = self.mock_session
        
        # Create test user and platforms
        self.test_user = MockUser()
        self.test_platform = MockPlatform()
        self.test_user.platforms = [self.test_platform]
    
    @patch('safe_template_context.current_app')
    @patch('safe_template_context.current_user')
    def test_safe_template_context_unauthenticated(self, mock_current_user, mock_current_app):
        """Test template context for unauthenticated user"""
        # Create a proper mock that doesn't trigger Flask context issues
        mock_current_user.is_authenticated = False
        mock_current_user.configure_mock(**{'is_authenticated': False})
        
        result = safe_template_context()
        
        expected = {
            'template_error': False,
            'current_user_safe': None,
            'user_platforms': [],
            'active_platform': None,
            'platform_count': 0
        }
        
        self.assertEqual(result, expected)
    
    @patch('safe_template_context.current_app')
    @patch('safe_template_context.current_user')
    def test_safe_template_context_authenticated_success(self, mock_current_user, mock_current_app):
        """Test successful template context for authenticated user"""
        # Create a proper mock user
        mock_current_user.configure_mock(**{
            'is_authenticated': True,
            'id': 1,
            'username': 'testuser',
            'email': 'test@test.com',
            'role': 'user',
            'is_active': True
        })
        
        mock_current_app.configure_mock(**{
            'request_session_manager': self.mock_session_manager,
            'detached_instance_handler': self.mock_handler
        })
        
        # Configure handler to return safe data
        self.mock_handler.safe_access.side_effect = lambda obj, attr, default=None: getattr(obj, attr, default)
        self.mock_handler.safe_relationship_access.return_value = [self.test_platform]
        
        result = safe_template_context()
        
        self.assertFalse(result['template_error'])
        self.assertIsNotNone(result['current_user_safe'])
        self.assertEqual(len(result['user_platforms']), 1)
        self.assertEqual(result['platform_count'], 1)
    
    @patch('safe_template_context.current_app')
    @patch('safe_template_context.current_user')
    def test_safe_template_context_missing_dependencies(self, mock_current_user, mock_current_app):
        """Test template context when session manager or handler is missing"""
        mock_current_user.configure_mock(**{'is_authenticated': True})
        mock_current_app.configure_mock(**{
            'request_session_manager': None,
            'detached_instance_handler': None
        })
        
        result = safe_template_context()
        
        self.assertTrue(result['template_error'])
        self.assertIsNone(result['current_user_safe'])
    
    @patch('safe_template_context.current_app')
    @patch('safe_template_context.current_user')
    def test_safe_template_context_detached_instance_error(self, mock_current_user, mock_current_app):
        """Test template context handles DetachedInstanceError"""
        mock_current_user.configure_mock(**{
            'is_authenticated': True,
            'get_id.return_value': "1"
        })
        mock_current_app.configure_mock(**{
            'request_session_manager': self.mock_session_manager,
            'detached_instance_handler': self.mock_handler
        })
        
        # Configure handler to raise DetachedInstanceError
        self.mock_handler.safe_access.side_effect = DetachedInstanceError("Test error")
        
        result = safe_template_context()
        
        self.assertTrue(result['template_error'])
        self.assertIsNotNone(result['current_user_safe'])  # Fallback data
        self.assertEqual(result['user_platforms'], [])
    
    def test_get_safe_user_data_success(self):
        """Test successful user data extraction"""
        self.mock_handler.safe_access.side_effect = lambda obj, attr, default=None: getattr(obj, attr, default)
        
        result = _get_safe_user_data(self.test_user, self.mock_handler)
        
        expected = {
            'id': 1,
            'username': 'testuser',
            'email': 'test@test.com',
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
    
    @patch('safe_template_context.current_user')
    def test_handle_detached_error_fallback(self, mock_current_user):
        """Test detached error fallback handling"""
        # Use regular Mock instead of AsyncMock to avoid coroutine issues
        mock_current_user.configure_mock(**{
            'get_id.return_value': "1"
        })
        
        context = {
            'template_error': True,
            'current_user_safe': None,
            'user_platforms': ['old_data'],
            'active_platform': 'old_platform',
            'platform_count': 1
        }
        
        _handle_detached_error_fallback(context, self.mock_session_manager)
        
        self.assertIsNotNone(context['current_user_safe'])
        self.assertEqual(context['current_user_safe']['id'], "1")
        self.assertEqual(context['user_platforms'], [])
        self.assertIsNone(context['active_platform'])
        self.assertEqual(context['platform_count'], 0)
    
    def test_create_safe_template_context_processor(self):
        """Test template context processor registration"""
        mock_app = Mock()
        
        create_safe_template_context_processor(mock_app)
        
        mock_app.context_processor.assert_called_once()
    
    @patch('safe_template_context.current_app')
    @patch('safe_template_context.current_user')
    def test_get_safe_user_context_current_user(self, mock_current_user, mock_current_app):
        """Test get_safe_user_context for current user"""
        mock_current_user.configure_mock(**{'is_authenticated': True})
        mock_current_app.configure_mock(**{
            'request_session_manager': self.mock_session_manager,
            'detached_instance_handler': self.mock_handler
        })
        
        self.mock_handler.safe_access.side_effect = lambda obj, attr, default=None: getattr(obj, attr, default)
        self.mock_handler.safe_relationship_access.return_value = []
        
        result = get_safe_user_context()
        
        self.assertFalse(result['template_error'])
        self.assertIsNotNone(result['current_user_safe'])
    
    @patch('safe_template_context.current_user')
    def test_get_safe_user_context_unauthenticated(self, mock_current_user):
        """Test get_safe_user_context for unauthenticated user"""
        mock_current_user.configure_mock(**{'is_authenticated': False})
        
        result = get_safe_user_context()
        
        expected = {
            'template_error': False,
            'current_user_safe': None,
            'user_platforms': [],
            'active_platform': None,
            'platform_count': 0
        }
        
        self.assertEqual(result, expected)
    
    @patch('safe_template_context.User', create=True)
    @patch('safe_template_context.current_app')
    def test_get_safe_user_context_specific_user(self, mock_current_app, mock_user_model):
        """Test get_safe_user_context for specific user ID"""
        mock_current_app.configure_mock(**{
            'request_session_manager': self.mock_session_manager,
            'detached_instance_handler': self.mock_handler
        })
        
        # Mock user query
        mock_user = MockUser(user_id=2, username="specificuser")
        self.mock_session.query.return_value.get.return_value = mock_user
        
        self.mock_handler.safe_access.side_effect = lambda obj, attr, default=None: getattr(obj, attr, default)
        self.mock_handler.safe_relationship_access.return_value = []
        
        result = get_safe_user_context(user_id=2)
        
        self.assertFalse(result['template_error'])
        self.assertEqual(result['current_user_safe']['username'], 'specificuser')
    
    @patch('safe_template_context.User', create=True)
    @patch('safe_template_context.current_app')
    def test_get_safe_user_context_user_not_found(self, mock_current_app, mock_user_model):
        """Test get_safe_user_context when user is not found"""
        mock_current_app.configure_mock(**{
            'request_session_manager': self.mock_session_manager,
            'detached_instance_handler': self.mock_handler
        })
        
        # Mock user query returning None
        self.mock_session.query.return_value.get.return_value = None
        
        result = get_safe_user_context(user_id=999)
        
        self.assertTrue(result['template_error'])
        self.assertIsNone(result['current_user_safe'])
    
    @patch('safe_template_context.current_app')
    def test_get_safe_user_context_missing_dependencies(self, mock_current_app):
        """Test get_safe_user_context with missing dependencies"""
        mock_current_app.configure_mock(**{
            'request_session_manager': None,
            'detached_instance_handler': None
        })
        
        result = get_safe_user_context(user_id=1)
        
        self.assertTrue(result['template_error'])
        self.assertIsNone(result['current_user_safe'])


if __name__ == '__main__':
    unittest.main()
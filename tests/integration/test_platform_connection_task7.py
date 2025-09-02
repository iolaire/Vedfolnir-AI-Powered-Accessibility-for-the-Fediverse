#!/usr/bin/env python3

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
from datetime import datetime

# Add the parent directory to the path so we can import the modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import PlatformConnection, User
from sqlalchemy.orm.exc import DetachedInstanceError

class TestPlatformConnectionTask7(unittest.TestCase):
    """Test Task 7: Enhanced PlatformConnection model for session safety"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.platform = PlatformConnection()
        self.platform.id = 1
        self.platform.user_id = 1
        self.platform.name = "Test Platform"
        self.platform.platform_type = "pixelfed"
        self.platform.instance_url = "https://pixelfed.example.com"
        self.platform.username = "testuser"
        self.platform.is_active = True
        self.platform.is_default = True
        self.platform.created_at = datetime.utcnow()
        self.platform.updated_at = datetime.utcnow()
        self.platform.last_used = datetime.utcnow()
        self.platform._access_token = "encrypted_token"
        self.platform._client_key = "encrypted_key"
        self.platform._client_secret = "encrypted_secret"
    
    def test_to_dict_basic(self):
        """Test to_dict method without sensitive data"""
        result = self.platform.to_dict()
        
        expected_keys = {
            'id', 'name', 'platform_type', 'instance_url', 'username',
            'is_active', 'is_default', 'created_at', 'updated_at', 'last_used'
        }
        
        self.assertEqual(set(result.keys()), expected_keys)
        self.assertEqual(result['id'], 1)
        self.assertEqual(result['name'], "Test Platform")
        self.assertEqual(result['platform_type'], "pixelfed")
        self.assertEqual(result['instance_url'], "https://pixelfed.example.com")
        self.assertEqual(result['username'], "testuser")
        self.assertTrue(result['is_active'])
        self.assertTrue(result['is_default'])
        self.assertIsNotNone(result['created_at'])
        self.assertIsNotNone(result['updated_at'])
        self.assertIsNotNone(result['last_used'])
    
    def test_to_dict_with_sensitive_data(self):
        """Test to_dict method with sensitive data included"""
        result = self.platform.to_dict(include_sensitive=True)
        
        # Should include all basic keys plus sensitive indicators
        expected_keys = {
            'id', 'name', 'platform_type', 'instance_url', 'username',
            'is_active', 'is_default', 'created_at', 'updated_at', 'last_used',
            'has_access_token', 'has_client_key', 'has_client_secret'
        }
        
        self.assertEqual(set(result.keys()), expected_keys)
        self.assertTrue(result['has_access_token'])
        self.assertTrue(result['has_client_key'])
        self.assertTrue(result['has_client_secret'])
    
    def test_to_dict_handles_none_dates(self):
        """Test to_dict method handles None dates gracefully"""
        self.platform.created_at = None
        self.platform.updated_at = None
        self.platform.last_used = None
        
        result = self.platform.to_dict()
        
        self.assertIsNone(result['created_at'])
        self.assertIsNone(result['updated_at'])
        self.assertIsNone(result['last_used'])
    
    def test_safe_get_user_success(self):
        """Test safe_get_user method with successful access"""
        mock_user = Mock(spec=User)
        mock_user.id = 1
        mock_user.username = "testuser"
        
        with patch.object(self.platform, 'user', mock_user):
            result = self.platform.safe_get_user()
            self.assertEqual(result, mock_user)
    
    def test_safe_get_user_detached_instance_error(self):
        """Test safe_get_user method handles DetachedInstanceError"""
        with patch.object(self.platform, 'user', side_effect=DetachedInstanceError("Test error")):
            result = self.platform.safe_get_user()
            self.assertIsNone(result)
    
    def test_safe_get_user_general_exception(self):
        """Test safe_get_user method handles general exceptions"""
        with patch.object(self.platform, 'user', side_effect=RuntimeError("Test error")):
            result = self.platform.safe_get_user()
            self.assertIsNone(result)
    
    def test_safe_get_posts_count_success(self):
        """Test safe_get_posts_count method with successful access"""
        mock_posts = [Mock(), Mock(), Mock()]
        
        with patch.object(self.platform, 'posts', mock_posts):
            result = self.platform.safe_get_posts_count()
            self.assertEqual(result, 3)
    
    def test_safe_get_posts_count_empty(self):
        """Test safe_get_posts_count method with empty posts"""
        with patch.object(self.platform, 'posts', []):
            result = self.platform.safe_get_posts_count()
            self.assertEqual(result, 0)
    
    def test_safe_get_posts_count_none(self):
        """Test safe_get_posts_count method with None posts"""
        with patch.object(self.platform, 'posts', None):
            result = self.platform.safe_get_posts_count()
            self.assertEqual(result, 0)
    
    def test_safe_get_posts_count_detached_instance_error(self):
        """Test safe_get_posts_count method handles DetachedInstanceError"""
        with patch.object(self.platform, 'posts', side_effect=DetachedInstanceError("Test error")):
            result = self.platform.safe_get_posts_count()
            self.assertEqual(result, 0)
    
    def test_safe_get_images_count_success(self):
        """Test safe_get_images_count method with successful access"""
        mock_images = [Mock(), Mock()]
        
        with patch.object(self.platform, 'images', mock_images):
            result = self.platform.safe_get_images_count()
            self.assertEqual(result, 2)
    
    def test_safe_get_images_count_detached_instance_error(self):
        """Test safe_get_images_count method handles DetachedInstanceError"""
        with patch.object(self.platform, 'images', side_effect=DetachedInstanceError("Test error")):
            result = self.platform.safe_get_images_count()
            self.assertEqual(result, 0)
    
    def test_is_accessible_true(self):
        """Test is_accessible method returns True for active platform with token"""
        self.platform.is_active = True
        self.platform._access_token = "encrypted_token"
        
        result = self.platform.is_accessible()
        self.assertTrue(result)
    
    def test_is_accessible_false_inactive(self):
        """Test is_accessible method returns False for inactive platform"""
        self.platform.is_active = False
        self.platform._access_token = "encrypted_token"
        
        result = self.platform.is_accessible()
        self.assertFalse(result)
    
    def test_is_accessible_false_no_token(self):
        """Test is_accessible method returns False for platform without token"""
        self.platform.is_active = True
        self.platform._access_token = None
        
        result = self.platform.is_accessible()
        self.assertFalse(result)
    
    def test_get_display_name_with_name(self):
        """Test get_display_name method when name is set"""
        self.platform.name = "My Platform"
        self.platform.platform_type = "pixelfed"
        
        result = self.platform.get_display_name()
        self.assertEqual(result, "My Platform (pixelfed)")
    
    def test_get_display_name_without_name(self):
        """Test get_display_name method when name is not set"""
        self.platform.name = None
        self.platform.username = "testuser"
        self.platform.instance_url = "https://pixelfed.example.com"
        self.platform.platform_type = "pixelfed"
        
        result = self.platform.get_display_name()
        self.assertEqual(result, "testuser@https://pixelfed.example.com (pixelfed)")
    
    def test_matches_platform_true(self):
        """Test matches_platform method returns True for matching platform"""
        result = self.platform.matches_platform("pixelfed", "https://pixelfed.example.com")
        self.assertTrue(result)
    
    def test_matches_platform_false_different_type(self):
        """Test matches_platform method returns False for different platform type"""
        result = self.platform.matches_platform("mastodon", "https://pixelfed.example.com")
        self.assertFalse(result)
    
    def test_matches_platform_false_different_url(self):
        """Test matches_platform method returns False for different instance URL"""
        result = self.platform.matches_platform("pixelfed", "https://other.example.com")
        self.assertFalse(result)
    
    def test_can_be_default_true(self):
        """Test can_be_default method returns True for active platform with token"""
        self.platform.is_active = True
        self.platform._access_token = "encrypted_token"
        
        result = self.platform.can_be_default()
        self.assertTrue(result)
    
    def test_can_be_default_false_inactive(self):
        """Test can_be_default method returns False for inactive platform"""
        self.platform.is_active = False
        self.platform._access_token = "encrypted_token"
        
        result = self.platform.can_be_default()
        self.assertFalse(result)
    
    def test_can_be_default_false_no_token(self):
        """Test can_be_default method returns False for platform without token"""
        self.platform.is_active = True
        self.platform._access_token = None
        
        result = self.platform.can_be_default()
        self.assertFalse(result)
    
    def test_test_connection_not_accessible(self):
        """Test test_connection method when platform is not accessible"""
        self.platform.is_active = False
        
        success, message = self.platform.test_connection()
        
        self.assertFalse(success)
        self.assertIn("not accessible", message)
    
    @patch('models.ActivityPubClient')
    @patch('models.asyncio')
    def test_test_connection_success(self, mock_asyncio, mock_client_class):
        """Test test_connection method with successful connection"""
        # Setup mocks
        mock_client = Mock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.test_connection.return_value = (True, "Connection successful")
        
        mock_loop = Mock()
        mock_asyncio.new_event_loop.return_value = mock_loop
        mock_loop.run_until_complete.return_value = (True, "Connection successful")
        
        # Mock to_activitypub_config to return a valid config
        with patch.object(self.platform, 'to_activitypub_config', return_value=Mock()):
            success, message = self.platform.test_connection()
        
        self.assertTrue(success)
        self.assertEqual(message, "Connection successful")
    
    @patch('models.ActivityPubClient')
    def test_test_connection_config_failure(self, mock_client_class):
        """Test test_connection method when config creation fails"""
        with patch.object(self.platform, 'to_activitypub_config', return_value=None):
            success, message = self.platform.test_connection()
        
        self.assertFalse(success)
        self.assertIn("Failed to create configuration", message)
    
    def test_to_activitypub_config_missing_data(self):
        """Test to_activitypub_config method with missing required data"""
        self.platform.instance_url = None
        
        result = self.platform.to_activitypub_config()
        self.assertIsNone(result)
    
    @patch('models.ActivityPubConfig')
    @patch('models.RetryConfig')
    @patch('models.RateLimitConfig')
    def test_to_activitypub_config_success(self, mock_rate_limit, mock_retry, mock_config):
        """Test to_activitypub_config method with successful config creation"""
        # Setup mocks
        mock_retry.from_env.return_value = Mock()
        mock_rate_limit.from_env.return_value = Mock()
        mock_config_instance = Mock()
        mock_config.return_value = mock_config_instance
        
        # Mock property access to avoid encryption issues in tests
        with patch.object(self.platform, 'access_token', 'test_token'), \
             patch.object(self.platform, 'client_key', 'test_key'), \
             patch.object(self.platform, 'client_secret', 'test_secret'):
            
            result = self.platform.to_activitypub_config()
        
        self.assertEqual(result, mock_config_instance)
        mock_config.assert_called_once()
    
    def test_platform_connection_indexes_exist(self):
        """Test that proper indexes are defined for efficient queries"""
        table_args = PlatformConnection.__table_args__
        
        # Check that we have the expected number of constraints and indexes
        self.assertGreaterEqual(len(table_args), 5)  # 2 unique constraints + 3 indexes
        
        # Check for specific indexes by examining their names/columns
        index_names = []
        for arg in table_args:
            if hasattr(arg, 'name'):
                index_names.append(arg.name)
        
        expected_indexes = [
            'uq_user_platform_name',
            'uq_user_instance_username', 
            'ix_platform_user_active',
            'ix_platform_type_active',
            'ix_platform_instance_type'
        ]
        
        for expected_index in expected_indexes:
            self.assertIn(expected_index, index_names)
    
    def test_platform_connection_repr(self):
        """Test PlatformConnection __repr__ method"""
        repr_str = repr(self.platform)
        self.assertEqual(repr_str, "<PlatformConnection Test Platform (pixelfed)>")

class TestPlatformConnectionSessionSafety(unittest.TestCase):
    """Test session safety features of PlatformConnection model"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.platform = PlatformConnection()
        self.platform.id = 1
        self.platform.name = "Test Platform"
        self.platform.platform_type = "pixelfed"
        self.platform.instance_url = "https://pixelfed.example.com"
        self.platform.username = "testuser"
        self.platform.is_active = True
        self.platform._access_token = "encrypted_token"
    
    def test_all_methods_work_with_detached_instances(self):
        """Test that all new methods work with detached instances"""
        # These methods should work even if the object is detached from session
        methods_to_test = [
            ('is_accessible', []),
            ('get_display_name', []),
            ('matches_platform', ['pixelfed', 'https://pixelfed.example.com']),
            ('can_be_default', []),
            ('to_dict', []),
            ('to_dict', [True]),  # with include_sensitive=True
        ]
        
        for method_name, args in methods_to_test:
            with self.subTest(method=method_name, args=args):
                method = getattr(self.platform, method_name)
                try:
                    result = method(*args)
                    # Method should not raise an exception
                    self.assertIsNotNone(result)
                except Exception as e:
                    self.fail(f"Method {method_name} raised {type(e).__name__}: {e}")
    
    def test_safe_methods_handle_relationship_errors(self):
        """Test that safe methods handle relationship access errors gracefully"""
        safe_methods = [
            ('safe_get_user', None),
            ('safe_get_posts_count', 0),
            ('safe_get_images_count', 0),
        ]
        
        for method_name, expected_fallback in safe_methods:
            with self.subTest(method=method_name):
                method = getattr(self.platform, method_name)
                result = method()
                
                # Should return fallback value without raising exception
                if expected_fallback is not None:
                    self.assertEqual(result, expected_fallback)
                else:
                    self.assertIsNone(result)

if __name__ == '__main__':
    unittest.main()
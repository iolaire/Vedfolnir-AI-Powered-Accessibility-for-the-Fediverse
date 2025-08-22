#!/usr/bin/env python3

import unittest
from unittest.mock import Mock, patch
import sys
import os
from datetime import datetime

# Add the parent directory to the path so we can import the modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import PlatformConnection
from sqlalchemy.orm.exc import DetachedInstanceError

class TestPlatformConnectionTask7Simple(unittest.TestCase):
    """Test Task 7: Enhanced PlatformConnection model for session safety (simplified)"""
    
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
    
    def test_to_activitypub_config_missing_data(self):
        """Test to_activitypub_config method with missing required data"""
        self.platform.instance_url = None
        
        result = self.platform.to_activitypub_config()
        self.assertIsNone(result)
    
    def test_safe_get_user_method_exists(self):
        """Test that safe_get_user method exists and is callable"""
        self.assertTrue(hasattr(self.platform, 'safe_get_user'))
        self.assertTrue(callable(self.platform.safe_get_user))
        
        # Should return None when no user relationship is set
        result = self.platform.safe_get_user()
        self.assertIsNone(result)
    
    def test_safe_get_posts_count_method_exists(self):
        """Test that safe_get_posts_count method exists and is callable"""
        self.assertTrue(hasattr(self.platform, 'safe_get_posts_count'))
        self.assertTrue(callable(self.platform.safe_get_posts_count))
        
        # Should return 0 when no posts relationship is set
        result = self.platform.safe_get_posts_count()
        self.assertEqual(result, 0)
    
    def test_safe_get_images_count_method_exists(self):
        """Test that safe_get_images_count method exists and is callable"""
        self.assertTrue(hasattr(self.platform, 'safe_get_images_count'))
        self.assertTrue(callable(self.platform.safe_get_images_count))
        
        # Should return 0 when no images relationship is set
        result = self.platform.safe_get_images_count()
        self.assertEqual(result, 0)
    
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
    
    def test_all_session_safe_methods_work_without_session(self):
        """Test that all session-safe methods work without database session"""
        # These methods should work even if the object is detached from session
        methods_to_test = [
            ('is_accessible', [], lambda x: x is not None),
            ('get_display_name', [], lambda x: x is not None),
            ('matches_platform', ['pixelfed', 'https://pixelfed.example.com'], lambda x: x is not None),
            ('can_be_default', [], lambda x: x is not None),
            ('to_dict', [], lambda x: x is not None),
            ('to_dict', [True], lambda x: x is not None),  # with include_sensitive=True
            ('safe_get_user', [], lambda x: True),  # Can return None, that's expected
            ('safe_get_posts_count', [], lambda x: isinstance(x, int)),
            ('safe_get_images_count', [], lambda x: isinstance(x, int)),
        ]
        
        for method_name, args, validator in methods_to_test:
            with self.subTest(method=method_name, args=args):
                method = getattr(self.platform, method_name)
                try:
                    result = method(*args)
                    # Method should not raise an exception and should pass validation
                    self.assertTrue(validator(result), f"Method {method_name} returned invalid result: {result}")
                except Exception as e:
                    self.fail(f"Method {method_name} raised {type(e).__name__}: {e}")
    
    def test_enhanced_to_dict_includes_sensitive_flags(self):
        """Test that enhanced to_dict method includes sensitive data flags"""
        # Test with no sensitive data
        self.platform._access_token = None
        self.platform._client_key = None
        self.platform._client_secret = None
        
        result = self.platform.to_dict(include_sensitive=True)
        
        self.assertFalse(result['has_access_token'])
        self.assertFalse(result['has_client_key'])
        self.assertFalse(result['has_client_secret'])
        
        # Test with sensitive data
        self.platform._access_token = "token"
        self.platform._client_key = "key"
        self.platform._client_secret = "secret"
        
        result = self.platform.to_dict(include_sensitive=True)
        
        self.assertTrue(result['has_access_token'])
        self.assertTrue(result['has_client_key'])
        self.assertTrue(result['has_client_secret'])

if __name__ == '__main__':
    unittest.main()
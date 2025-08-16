# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test Mock User Helpers

This test file demonstrates and validates the mock user helper functionality.
It serves as both a test and an example of how to use the helpers properly.
"""

import unittest
import os
from config import Config
from database import DatabaseManager
from models import UserRole, User, PlatformConnection
from tests.test_helpers import (
    MockUserHelper, 
    create_test_user_with_platforms, 
    cleanup_test_user,
    TEST_USER_DEFAULTS,
    TEST_PLATFORM_DEFAULTS
)


class TestMockUserHelpers(unittest.TestCase):
    """Test cases for mock user helper functionality"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test configuration"""
        # Skip tests if no environment configuration
        if not os.path.exists('.env'):
            raise unittest.SkipTest("No .env file found - skipping database-dependent tests")
        
        try:
            cls.config = Config()
            cls.db_manager = DatabaseManager(cls.config)
        except Exception as e:
            raise unittest.SkipTest(f"Database configuration error: {e}")
    
    def setUp(self):
        """Set up test fixtures"""
        self.helper = MockUserHelper(self.db_manager)
    
    def tearDown(self):
        """Clean up test fixtures"""
        # Always clean up any created users
        self.helper.cleanup_mock_users()
    
    def test_create_basic_mock_user(self):
        """Test creating a basic mock user"""
        user = self.helper.create_mock_user(
            username="test_basic_user",
            with_platforms=False
        )
        
        self.assertIsNotNone(user)
        self.assertEqual(user.username, "test_basic_user")
        self.assertTrue(user.email.startswith("test_"))
        self.assertTrue(user.email.endswith("@test.com"))
        self.assertEqual(user.role, UserRole.REVIEWER)  # Default role
        self.assertTrue(user.is_active)
        
        # Verify user is tracked for cleanup
        self.assertIn(user.id, self.helper.created_users)
        self.assertEqual(self.helper.get_created_user_count(), 1)
        self.assertEqual(self.helper.get_created_platform_count(), 0)
    
    def test_create_user_with_platforms(self):
        """Test creating a user with platform connections"""
        user = self.helper.create_mock_user(
            username="test_platform_user",
            role=UserRole.ADMIN,
            with_platforms=True
        )
        
        self.assertIsNotNone(user)
        self.assertEqual(user.username, "test_platform_user")
        self.assertEqual(user.role, UserRole.ADMIN)
        
        # Check platforms were created
        self.assertEqual(self.helper.get_created_platform_count(), 2)  # Default: Pixelfed + Mastodon
        
        # Verify platforms are associated with user
        platforms = user.platform_connections
        self.assertEqual(len(platforms), 2)
        
        # Check platform types
        platform_types = [p.platform_type for p in platforms]
        self.assertIn('pixelfed', platform_types)
        self.assertIn('mastodon', platform_types)
        
        # Check default platform
        default_platforms = [p for p in platforms if p.is_default]
        self.assertEqual(len(default_platforms), 1)
        self.assertEqual(default_platforms[0].platform_type, 'pixelfed')
    
    def test_create_user_with_custom_platforms(self):
        """Test creating a user with custom platform configurations"""
        custom_platforms = [
            {
                'name': 'Custom Test Platform',
                'platform_type': 'mastodon',
                'instance_url': 'https://custom.mastodon.social',
                'username': 'custom_test_user',
                'access_token': 'custom_test_token',
                'is_default': True
            }
        ]
        
        user = self.helper.create_mock_user(
            username="test_custom_platform_user",
            with_platforms=True,
            platform_configs=custom_platforms
        )
        
        self.assertIsNotNone(user)
        self.assertEqual(self.helper.get_created_platform_count(), 1)
        
        platform = user.platform_connections[0]
        self.assertEqual(platform.name, 'Custom Test Platform')
        self.assertEqual(platform.platform_type, 'mastodon')
        self.assertEqual(platform.instance_url, 'https://custom.mastodon.social')
        self.assertEqual(platform.username, 'custom_test_user')
        self.assertTrue(platform.is_default)
        
        # Test encrypted access token
        self.assertEqual(platform.access_token, 'custom_test_token')
    
    def test_convenience_functions(self):
        """Test the convenience functions for easy test setup"""
        user, helper = create_test_user_with_platforms(
            self.db_manager,
            username="test_convenience_user",
            role=UserRole.MODERATOR
        )
        
        try:
            self.assertIsNotNone(user)
            self.assertEqual(user.username, "test_convenience_user")
            self.assertEqual(user.role, UserRole.MODERATOR)
            self.assertTrue(len(user.platform_connections) > 0)
            
            # Verify helper is properly set up
            self.assertEqual(helper.get_created_user_count(), 1)
            self.assertTrue(helper.get_created_platform_count() > 0)
            
        finally:
            # Clean up using convenience function
            cleanup_test_user(helper)
            
            # Verify cleanup worked
            self.assertEqual(helper.get_created_user_count(), 0)
            self.assertEqual(helper.get_created_platform_count(), 0)
    
    def test_user_retrieval(self):
        """Test retrieving created users"""
        user = self.helper.create_mock_user(
            username="test_retrieval_user",
            with_platforms=False
        )
        
        # Test retrieval by username
        retrieved_user = self.helper.get_mock_user_by_username("test_retrieval_user")
        self.assertIsNotNone(retrieved_user)
        self.assertEqual(retrieved_user.id, user.id)
        self.assertEqual(retrieved_user.username, user.username)
        
        # Test retrieval of non-existent user
        non_existent = self.helper.get_mock_user_by_username("non_existent_user")
        self.assertIsNone(non_existent)
    
    def test_specific_user_cleanup(self):
        """Test cleaning up specific users"""
        user1 = self.helper.create_mock_user(username="test_user_1", with_platforms=True)
        user2 = self.helper.create_mock_user(username="test_user_2", with_platforms=True)
        
        # Verify both users were created
        self.assertEqual(self.helper.get_created_user_count(), 2)
        self.assertTrue(self.helper.get_created_platform_count() > 0)
        
        # Clean up only user1
        self.helper.cleanup_specific_user(user1.id)
        
        # Verify user1 is gone but user2 remains
        user1_check = self.helper.get_mock_user_by_username("test_user_1")
        user2_check = self.helper.get_mock_user_by_username("test_user_2")
        
        self.assertIsNone(user1_check)
        self.assertIsNotNone(user2_check)
        
        # Verify tracking was updated
        self.assertNotIn(user1.id, self.helper.created_users)
        self.assertIn(user2.id, self.helper.created_users)
    
    def test_password_functionality(self):
        """Test that user passwords work correctly"""
        user = self.helper.create_mock_user(
            username="test_password_user",
            password="custom_test_password",
            with_platforms=False
        )
        
        # Test password verification
        self.assertTrue(user.check_password("custom_test_password"))
        self.assertFalse(user.check_password("wrong_password"))
        self.assertFalse(user.check_password(""))
    
    def test_user_roles_and_permissions(self):
        """Test different user roles and their permissions"""
        roles_to_test = [
            (UserRole.ADMIN, UserRole.MODERATOR, True),
            (UserRole.MODERATOR, UserRole.REVIEWER, True),
            (UserRole.REVIEWER, UserRole.VIEWER, True),
            (UserRole.VIEWER, UserRole.ADMIN, False),
        ]
        
        for user_role, required_role, should_have_permission in roles_to_test:
            with self.subTest(user_role=user_role, required_role=required_role):
                user = self.helper.create_mock_user(
                    username=f"test_{user_role.value}_user",
                    role=user_role,
                    with_platforms=False
                )
                
                self.assertEqual(user.role, user_role)
                self.assertEqual(
                    user.has_permission(required_role), 
                    should_have_permission,
                    f"{user_role.value} should {'have' if should_have_permission else 'not have'} {required_role.value} permission"
                )
    
    def test_constants_and_defaults(self):
        """Test that the constants and defaults are properly defined"""
        # Test that constants exist and have expected structure
        self.assertIsInstance(TEST_USER_DEFAULTS, dict)
        self.assertIn('password', TEST_USER_DEFAULTS)
        self.assertIn('role', TEST_USER_DEFAULTS)
        self.assertIn('is_active', TEST_USER_DEFAULTS)
        
        self.assertIsInstance(TEST_PLATFORM_DEFAULTS, dict)
        self.assertIn('pixelfed', TEST_PLATFORM_DEFAULTS)
        self.assertIn('mastodon', TEST_PLATFORM_DEFAULTS)
        
        # Test default values
        self.assertEqual(TEST_USER_DEFAULTS['password'], 'test_password_123')
        self.assertEqual(TEST_USER_DEFAULTS['role'], UserRole.REVIEWER)
        self.assertTrue(TEST_USER_DEFAULTS['is_active'])


if __name__ == '__main__':
    unittest.main()
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Example Test Using Mock User Helpers

This test demonstrates the proper way to use mock user helpers in tests
that involve user sessions and platform connections.
"""

import unittest
import os
from config import Config
from database import DatabaseManager
from models import UserRole
from tests.test_helpers import create_test_user_with_platforms, cleanup_test_user


class TestMockUserExample(unittest.TestCase):
    """Example test class showing proper mock user usage"""
    
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
        """Set up test fixtures using mock user helpers"""
        # Create mock user with platforms using the convenience function
        self.test_user, self.user_helper = create_test_user_with_platforms(
            self.db_manager,
            username=None,  # Let it auto-generate to avoid conflicts
            role=UserRole.REVIEWER
        )
    
    def tearDown(self):
        """Clean up test fixtures"""
        # Always clean up mock users
        cleanup_test_user(self.user_helper)
    
    def test_user_has_correct_properties(self):
        """Test that the mock user has the expected properties"""
        self.assertIsNotNone(self.test_user)
        self.assertTrue(self.test_user.username.startswith("test_user_"))
        self.assertTrue(self.test_user.email.startswith("test_"))
        self.assertTrue(self.test_user.email.endswith("@example.com"))
        self.assertEqual(self.test_user.role, UserRole.REVIEWER)
        self.assertTrue(self.test_user.is_active)
    
    def test_user_has_platforms(self):
        """Test that the mock user has platform connections"""
        platforms = self.test_user.platform_connections
        self.assertTrue(len(platforms) > 0)
        
        # Check that we have the expected platform types
        platform_types = [p.platform_type for p in platforms]
        self.assertIn('pixelfed', platform_types)
        self.assertIn('mastodon', platform_types)
        
        # Check that one platform is marked as default
        default_platforms = [p for p in platforms if p.is_default]
        self.assertEqual(len(default_platforms), 1)
    
    def test_user_password_functionality(self):
        """Test that user password functionality works"""
        # Default password from TEST_USER_DEFAULTS
        self.assertTrue(self.test_user.check_password("test_password_123"))
        self.assertFalse(self.test_user.check_password("wrong_password"))
    
    def test_user_permissions(self):
        """Test that user permissions work correctly"""
        # Reviewer should have viewer permissions but not admin
        self.assertTrue(self.test_user.has_permission(UserRole.VIEWER))
        self.assertFalse(self.test_user.has_permission(UserRole.ADMIN))
    
    def test_platform_credentials(self):
        """Test that platform credentials are properly encrypted/decrypted"""
        platforms = self.test_user.platform_connections
        
        for platform in platforms:
            # Access token should be decrypted properly
            self.assertIsNotNone(platform.access_token)
            self.assertTrue(platform.access_token.startswith("test_token_"))
            
            # Platform should have proper URLs
            self.assertTrue(platform.instance_url.startswith("https://"))
            self.assertTrue("example.com" in platform.instance_url)


if __name__ == '__main__':
    unittest.main()
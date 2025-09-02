# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Unit tests for platform context management

Tests the PlatformContextManager functionality including:
- Context setting and validation
- Platform filtering
- Data injection
- Error handling
"""

import unittest
from unittest.mock import Mock, patch

from tests.fixtures.platform_fixtures import PlatformTestCase
from platform_context import PlatformContextManager, PlatformContextError
from models import User, PlatformConnection, Post, Image

class TestPlatformContextManager(PlatformTestCase):
    """Test PlatformContextManager functionality"""
    
    def setUp(self):
        """Set up test with context manager"""
        super().setUp()
        self.context_manager = PlatformContextManager(self.session)
    
    def test_set_context_valid(self):
        """Test setting valid platform context"""
        user = self.get_test_user()
        platform = self.get_test_platform()
        
        # Set context
        context = self.context_manager.set_context(user.id, platform.id)
        
        self.assertIsNotNone(context)
        self.assertEqual(context.user_id, user.id)
        self.assertEqual(context.platform_connection_id, platform.id)
        self.assertIsNotNone(context.platform_info)
    
    def test_set_context_invalid_user(self):
        """Test setting context with invalid user"""
        platform = self.get_test_platform()
        
        with self.assertRaises(PlatformContextError):
            self.context_manager.set_context(99999, platform.id)
    
    def test_set_context_invalid_platform(self):
        """Test setting context with invalid platform"""
        user = self.get_test_user()
        
        with self.assertRaises(PlatformContextError):
            self.context_manager.set_context(user.id, 99999)
    
    def test_set_context_platform_not_owned(self):
        """Test setting context with platform not owned by user"""
        user1 = self.get_test_user()
        user2 = self.users[1]  # Different user
        
        # Create platform for user2
        platform = PlatformConnection(
            user_id=user2.id,
            name='Other User Platform',
            platform_type='pixelfed',
            instance_url='https://other.test',
            username='otheruser',
            access_token='other_token'
        )
        self.session.add(platform)
        self.session.commit()
        
        # Try to set context for user1 with user2's platform
        with self.assertRaises(PlatformContextError):
            self.context_manager.set_context(user1.id, platform.id)
    
    def test_require_context_with_context(self):
        """Test requiring context when context is set"""
        user = self.get_test_user()
        platform = self.get_test_platform()
        
        # Set context first
        self.context_manager.set_context(user.id, platform.id)
        
        # Should not raise exception
        context = self.context_manager.require_context()
        self.assertIsNotNone(context)
    
    def test_require_context_without_context(self):
        """Test requiring context when no context is set"""
        with self.assertRaises(PlatformContextError):
            self.context_manager.require_context()
    
    def test_clear_context(self):
        """Test clearing platform context"""
        user = self.get_test_user()
        platform = self.get_test_platform()
        
        # Set context
        self.context_manager.set_context(user.id, platform.id)
        
        # Clear context
        self.context_manager.clear_context()
        
        # Should raise exception when requiring context
        with self.assertRaises(PlatformContextError):
            self.context_manager.require_context()
    
    def test_apply_platform_filter_post(self):
        """Test applying platform filter to Post queries"""
        user = self.get_test_user()
        platform = self.get_test_platform()
        
        # Set context
        self.context_manager.set_context(user.id, platform.id)
        
        # Create query
        query = self.session.query(Post)
        
        # Apply filter
        filtered_query = self.context_manager.apply_platform_filter(query, Post)
        
        # Execute query
        posts = filtered_query.all()
        
        # All posts should belong to the platform
        for post in posts:
            self.assertEqual(post.platform_connection_id, platform.id)
    
    def test_apply_platform_filter_image(self):
        """Test applying platform filter to Image queries"""
        user = self.get_test_user()
        platform = self.get_test_platform()
        
        # Set context
        self.context_manager.set_context(user.id, platform.id)
        
        # Create query
        query = self.session.query(Image)
        
        # Apply filter
        filtered_query = self.context_manager.apply_platform_filter(query, Image)
        
        # Execute query
        images = filtered_query.all()
        
        # All images should belong to the platform
        for image in images:
            self.assertEqual(image.platform_connection_id, platform.id)
    
    def test_apply_platform_filter_without_context(self):
        """Test applying platform filter without context"""
        query = self.session.query(Post)
        
        with self.assertRaises(PlatformContextError):
            self.context_manager.apply_platform_filter(query, Post)
    
    def test_inject_platform_data(self):
        """Test injecting platform data into dictionaries"""
        user = self.get_test_user()
        platform = self.get_test_platform()
        
        # Set context
        self.context_manager.set_context(user.id, platform.id)
        
        # Test data
        data = {
            'post_id': 'test_post',
            'content': 'test content'
        }
        
        # Inject platform data
        injected_data = self.context_manager.inject_platform_data(data)
        
        # Should contain platform information
        self.assertIn('platform_connection_id', injected_data)
        self.assertEqual(injected_data['platform_connection_id'], platform.id)
        
        # Original data should be preserved
        self.assertEqual(injected_data['post_id'], 'test_post')
        self.assertEqual(injected_data['content'], 'test content')
    
    def test_inject_platform_data_without_context(self):
        """Test injecting platform data without context"""
        data = {'test': 'data'}
        
        with self.assertRaises(PlatformContextError):
            self.context_manager.inject_platform_data(data)
    
    def test_get_activitypub_config(self):
        """Test getting ActivityPub config from context"""
        user = self.get_test_user()
        platform = self.get_test_platform()
        
        # Set context
        self.context_manager.set_context(user.id, platform.id)
        
        # Get config
        config = self.context_manager.get_activitypub_config()
        
        self.assertIsNotNone(config)
        self.assertEqual(config.instance_url, platform.instance_url)
        self.assertEqual(config.access_token, platform.access_token)
        self.assertEqual(config.api_type, platform.platform_type)
    
    def test_get_activitypub_config_without_context(self):
        """Test getting ActivityPub config without context"""
        with self.assertRaises(PlatformContextError):
            self.context_manager.get_activitypub_config()
    
    def test_context_scope_manager(self):
        """Test context scope manager"""
        user = self.get_test_user()
        platform1 = self.get_test_platform('pixelfed')
        platform2 = self.get_test_platform('mastodon')
        
        # Set initial context
        self.context_manager.set_context(user.id, platform1.id)
        
        # Use scope manager to temporarily change context
        with self.context_manager.context_scope(user.id, platform2.id):
            context = self.context_manager.require_context()
            self.assertEqual(context.platform_connection_id, platform2.id)
        
        # Context should be restored
        context = self.context_manager.require_context()
        self.assertEqual(context.platform_connection_id, platform1.id)
    
    def test_context_scope_manager_exception(self):
        """Test context scope manager with exception"""
        user = self.get_test_user()
        platform1 = self.get_test_platform('pixelfed')
        platform2 = self.get_test_platform('mastodon')
        
        # Set initial context
        self.context_manager.set_context(user.id, platform1.id)
        
        # Use scope manager with exception
        try:
            with self.context_manager.context_scope(user.id, platform2.id):
                raise ValueError("Test exception")
        except ValueError:
            pass
        
        # Context should still be restored
        context = self.context_manager.require_context()
        self.assertEqual(context.platform_connection_id, platform1.id)
    
    def test_validate_platform_access(self):
        """Test platform access validation"""
        user = self.get_test_user()
        platform = self.get_test_platform()
        
        # Set context
        self.context_manager.set_context(user.id, platform.id)
        
        # Should validate successfully
        is_valid = self.context_manager.validate_platform_access(
            platform.platform_type,
            platform.instance_url
        )
        self.assertTrue(is_valid)
        
        # Should fail for different platform
        is_valid = self.context_manager.validate_platform_access(
            'other_type',
            'https://other.instance'
        )
        self.assertFalse(is_valid)
    
    def test_get_platform_statistics(self):
        """Test getting platform-specific statistics"""
        user = self.get_test_user()
        platform = self.get_test_platform()
        
        # Set context
        self.context_manager.set_context(user.id, platform.id)
        
        # Get statistics
        stats = self.context_manager.get_platform_statistics()
        
        self.assertIsInstance(stats, dict)
        self.assertIn('total_posts', stats)
        self.assertIn('total_images', stats)
        
        # Statistics should be for current platform only
        self.assertGreaterEqual(stats['total_posts'], 0)
        self.assertGreaterEqual(stats['total_images'], 0)

class TestPlatformContextError(unittest.TestCase):
    """Test PlatformContextError exception"""
    
    def test_error_creation(self):
        """Test creating PlatformContextError"""
        error = PlatformContextError("Test error message")
        
        self.assertEqual(str(error), "Test error message")
        self.assertIsInstance(error, Exception)
    
    def test_error_with_context(self):
        """Test error with additional context"""
        error = PlatformContextError("Test error", user_id=123, platform_id=456)
        
        self.assertEqual(str(error), "Test error")
        # Additional context should be accessible if needed
        self.assertTrue(hasattr(error, 'args'))

class TestPlatformContextIntegration(PlatformTestCase):
    """Test platform context integration with other components"""
    
    def test_context_with_database_operations(self):
        """Test context integration with database operations"""
        user = self.get_test_user()
        platform = self.get_test_platform()
        
        # Set context
        context_manager = PlatformContextManager(self.session)
        context_manager.set_context(user.id, platform.id)
        
        # Perform database operations
        posts = self.session.query(Post).all()
        
        # Apply platform filtering
        filtered_query = context_manager.apply_platform_filter(
            self.session.query(Post), Post
        )
        filtered_posts = filtered_query.all()
        
        # Filtered results should be subset of all results
        self.assertLessEqual(len(filtered_posts), len(posts))
        
        # All filtered posts should belong to platform
        for post in filtered_posts:
            self.assertEqual(post.platform_connection_id, platform.id)
    
    def test_context_switching_performance(self):
        """Test performance of context switching"""
        user = self.get_test_user()
        platforms = [self.get_test_platform('pixelfed'), self.get_test_platform('mastodon')]
        
        context_manager = PlatformContextManager(self.session)
        
        # Switch contexts multiple times
        for i in range(10):
            platform = platforms[i % 2]
            context_manager.set_context(user.id, platform.id)
            
            # Verify context is correct
            context = context_manager.require_context()
            self.assertEqual(context.platform_connection_id, platform.id)
    
    def test_concurrent_context_isolation(self):
        """Test that contexts are isolated between instances"""
        user = self.get_test_user()
        platform1 = self.get_test_platform('pixelfed')
        platform2 = self.get_test_platform('mastodon')
        
        # Create separate context managers
        context_manager1 = PlatformContextManager(self.session)
        context_manager2 = PlatformContextManager(self.session)
        
        # Set different contexts
        context_manager1.set_context(user.id, platform1.id)
        context_manager2.set_context(user.id, platform2.id)
        
        # Verify contexts are independent
        context1 = context_manager1.require_context()
        context2 = context_manager2.require_context()
        
        self.assertEqual(context1.platform_connection_id, platform1.id)
        self.assertEqual(context2.platform_connection_id, platform2.id)

if __name__ == '__main__':
    unittest.main()
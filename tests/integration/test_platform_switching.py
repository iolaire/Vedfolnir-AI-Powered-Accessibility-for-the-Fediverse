# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Integration tests for platform switching workflows

Tests complete platform switching scenarios with data isolation validation.
"""

import unittest
from tests.fixtures.platform_fixtures import PlatformTestCase
from models import Post, Image, ProcessingStatus
from platform_context import PlatformContextManager


class TestPlatformSwitchingWorkflows(PlatformTestCase):
    """Test complete platform switching workflows"""
    
    def setUp(self):
        """Set up test with context manager"""
        super().setUp()
        self.context_manager = PlatformContextManager(self.session)
    
    def test_complete_platform_switching_workflow(self):
        """Test complete platform switching maintains data isolation"""
        user = self.get_test_user()
        platform1 = self.get_test_platform('pixelfed')
        platform2 = self.get_test_platform('mastodon')
        
        # Switch to platform1 and get data
        self.context_manager.set_context(user.id, platform1.id)
        platform1_posts = self.context_manager.apply_platform_filter(
            self.session.query(Post), Post
        ).all()
        platform1_images = self.context_manager.apply_platform_filter(
            self.session.query(Image), Image
        ).all()
        
        # Switch to platform2 and get data
        self.context_manager.set_context(user.id, platform2.id)
        platform2_posts = self.context_manager.apply_platform_filter(
            self.session.query(Post), Post
        ).all()
        platform2_images = self.context_manager.apply_platform_filter(
            self.session.query(Image), Image
        ).all()
        
        # Verify complete data isolation
        platform1_post_ids = {post.id for post in platform1_posts}
        platform2_post_ids = {post.id for post in platform2_posts}
        self.assertEqual(len(platform1_post_ids.intersection(platform2_post_ids)), 0)
        
        platform1_image_ids = {image.id for image in platform1_images}
        platform2_image_ids = {image.id for image in platform2_images}
        self.assertEqual(len(platform1_image_ids.intersection(platform2_image_ids)), 0)
    
    def test_platform_switching_preserves_context(self):
        """Test that platform switching preserves proper context"""
        user = self.get_test_user()
        platform1 = self.get_test_platform('pixelfed')
        platform2 = self.get_test_platform('mastodon')
        
        # Set initial context
        self.context_manager.set_context(user.id, platform1.id)
        context1 = self.context_manager.require_context()
        
        # Switch platforms
        self.context_manager.set_context(user.id, platform2.id)
        context2 = self.context_manager.require_context()
        
        # Switch back
        self.context_manager.set_context(user.id, platform1.id)
        context3 = self.context_manager.require_context()
        
        # Verify contexts are correct
        self.assertEqual(context1.platform_connection_id, platform1.id)
        self.assertEqual(context2.platform_connection_id, platform2.id)
        self.assertEqual(context3.platform_connection_id, platform1.id)
    
    def test_rapid_platform_switching(self):
        """Test rapid platform switching doesn't cause issues"""
        user = self.get_test_user()
        platforms = [self.get_test_platform('pixelfed'), self.get_test_platform('mastodon')]
        
        # Rapidly switch between platforms
        for i in range(20):
            platform = platforms[i % 2]
            self.context_manager.set_context(user.id, platform.id)
            
            # Verify context is correct
            context = self.context_manager.require_context()
            self.assertEqual(context.platform_connection_id, platform.id)
            
            # Verify data filtering works
            posts = self.context_manager.apply_platform_filter(
                self.session.query(Post), Post
            ).all()
            
            for post in posts:
                self.assertEqual(post.platform_connection_id, platform.id)


class TestDataIsolationValidation(PlatformTestCase):
    """Test data isolation between platforms"""
    
    def setUp(self):
        """Set up test with context manager"""
        super().setUp()
        self.context_manager = PlatformContextManager(self.session)
    
    def test_cross_platform_data_access_prevention(self):
        """Test that cross-platform data access is prevented"""
        user = self.get_test_user()
        platform1 = self.get_test_platform('pixelfed')
        platform2 = self.get_test_platform('mastodon')
        
        # Create data in platform1 context
        self.context_manager.set_context(user.id, platform1.id)
        platform1_data = self.context_manager.inject_platform_data({
            'post_id': 'platform1_post',
            'content': 'Platform 1 content'
        })
        
        # Switch to platform2 context
        self.context_manager.set_context(user.id, platform2.id)
        
        # Try to access platform1 data - should not be visible
        posts = self.context_manager.apply_platform_filter(
            self.session.query(Post), Post
        ).filter(Post.post_id == 'platform1_post').all()
        
        self.assertEqual(len(posts), 0)
    
    def test_platform_statistics_isolation(self):
        """Test that statistics are isolated per platform"""
        user = self.get_test_user()
        platform1 = self.get_test_platform('pixelfed')
        platform2 = self.get_test_platform('mastodon')
        
        # Get stats for platform1
        self.context_manager.set_context(user.id, platform1.id)
        stats1 = self.context_manager.get_platform_statistics()
        
        # Get stats for platform2
        self.context_manager.set_context(user.id, platform2.id)
        stats2 = self.context_manager.get_platform_statistics()
        
        # Stats should be different (isolated)
        self.assertNotEqual(stats1, stats2)
        
        # Each should only reflect their platform's data
        self.assertGreaterEqual(stats1['total_posts'], 0)
        self.assertGreaterEqual(stats2['total_posts'], 0)
    
    def test_concurrent_platform_operations(self):
        """Test concurrent operations on different platforms"""
        user = self.get_test_user()
        platform1 = self.get_test_platform('pixelfed')
        platform2 = self.get_test_platform('mastodon')
        
        # Create separate context managers for concurrent operations
        context_mgr1 = PlatformContextManager(self.session)
        context_mgr2 = PlatformContextManager(self.session)
        
        # Set different contexts
        context_mgr1.set_context(user.id, platform1.id)
        context_mgr2.set_context(user.id, platform2.id)
        
        # Perform operations concurrently
        posts1 = context_mgr1.apply_platform_filter(
            self.session.query(Post), Post
        ).all()
        posts2 = context_mgr2.apply_platform_filter(
            self.session.query(Post), Post
        ).all()
        
        # Verify isolation is maintained
        post_ids1 = {post.id for post in posts1}
        post_ids2 = {post.id for post in posts2}
        self.assertEqual(len(post_ids1.intersection(post_ids2)), 0)


class TestPlatformWorkflowIntegration(PlatformTestCase):
    """Test integration of platform workflows with database operations"""
    
    def setUp(self):
        """Set up test with context manager"""
        super().setUp()
        self.context_manager = PlatformContextManager(self.session)
    
    def test_end_to_end_platform_workflow(self):
        """Test complete end-to-end platform workflow"""
        user = self.get_test_user()
        platform = self.get_test_platform()
        
        # Set platform context
        self.context_manager.set_context(user.id, platform.id)
        
        # Create post with platform context
        post_data = self.context_manager.inject_platform_data({
            'post_id': 'workflow_test_post',
            'user_id': 'testuser',
            'post_url': 'https://test.com/post/workflow',
            'post_content': 'Workflow test content'
        })
        
        # Verify platform data was injected
        self.assertIn('platform_connection_id', post_data)
        self.assertEqual(post_data['platform_connection_id'], platform.id)
        
        # Create image with platform context
        image_data = self.context_manager.inject_platform_data({
            'image_url': 'https://test.com/workflow_image.jpg',
            'local_path': '/tmp/workflow_image.jpg',
            'attachment_index': 0,
            'media_type': 'image/jpeg',
            'generated_caption': 'Workflow test image'
        })
        
        # Verify platform data was injected
        self.assertIn('platform_connection_id', image_data)
        self.assertEqual(image_data['platform_connection_id'], platform.id)
        
        # Verify ActivityPub config generation
        config = self.context_manager.get_activitypub_config()
        self.assertEqual(config.instance_url, platform.instance_url)
        self.assertEqual(config.access_token, platform.access_token)
    
    def test_platform_switching_with_database_operations(self):
        """Test platform switching integrated with database operations"""
        user = self.get_test_user()
        platform1 = self.get_test_platform('pixelfed')
        platform2 = self.get_test_platform('mastodon')
        
        # Perform operations on platform1
        self.context_manager.set_context(user.id, platform1.id)
        
        # Get platform1 data
        platform1_posts = self.context_manager.apply_platform_filter(
            self.session.query(Post), Post
        ).all()
        
        # Switch to platform2
        self.context_manager.set_context(user.id, platform2.id)
        
        # Get platform2 data
        platform2_posts = self.context_manager.apply_platform_filter(
            self.session.query(Post), Post
        ).all()
        
        # Verify data is different
        platform1_ids = {post.id for post in platform1_posts}
        platform2_ids = {post.id for post in platform2_posts}
        
        # Should have no overlap
        self.assertEqual(len(platform1_ids.intersection(platform2_ids)), 0)
        
        # Switch back to platform1
        self.context_manager.set_context(user.id, platform1.id)
        
        # Get data again
        platform1_posts_again = self.context_manager.apply_platform_filter(
            self.session.query(Post), Post
        ).all()
        
        # Should be same as before
        platform1_ids_again = {post.id for post in platform1_posts_again}
        self.assertEqual(platform1_ids, platform1_ids_again)
    
    def test_platform_context_scope_integration(self):
        """Test platform context scope manager integration"""
        user = self.get_test_user()
        platform1 = self.get_test_platform('pixelfed')
        platform2 = self.get_test_platform('mastodon')
        
        # Set initial context
        self.context_manager.set_context(user.id, platform1.id)
        
        # Get initial data
        initial_posts = self.context_manager.apply_platform_filter(
            self.session.query(Post), Post
        ).all()
        initial_ids = {post.id for post in initial_posts}
        
        # Use scope manager to temporarily switch
        with self.context_manager.context_scope(user.id, platform2.id):
            scoped_posts = self.context_manager.apply_platform_filter(
                self.session.query(Post), Post
            ).all()
            scoped_ids = {post.id for post in scoped_posts}
            
            # Should be different data
            self.assertEqual(len(initial_ids.intersection(scoped_ids)), 0)
        
        # Context should be restored
        restored_posts = self.context_manager.apply_platform_filter(
            self.session.query(Post), Post
        ).all()
        restored_ids = {post.id for post in restored_posts}
        
        # Should match initial data
        self.assertEqual(initial_ids, restored_ids)


if __name__ == '__main__':
    unittest.main()
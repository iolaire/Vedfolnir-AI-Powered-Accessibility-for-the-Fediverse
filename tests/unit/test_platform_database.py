# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Unit tests for platform-aware database operations

Tests DatabaseManager platform functionality including:
- Platform connection CRUD operations
- Platform filtering in queries
- Platform-specific statistics
- Data isolation between platforms
"""

import unittest
from unittest.mock import Mock, patch

from tests.fixtures.platform_fixtures import PlatformTestCase
from app.core.database.core.database_manager import DatabaseManager, PlatformValidationError, DatabaseOperationError
from models import User, PlatformConnection, Post, Image, ProcessingStatus

class TestPlatformConnectionCRUD(PlatformTestCase):
    """Test platform connection CRUD operations"""
    
    def test_create_platform_connection(self):
        """Test creating platform connections"""
        user = self.get_test_user()
        
        platform = self.db_manager.create_platform_connection(
            user_id=user.id,
            name='New Test Platform',
            platform_type='pixelfed',
            instance_url='https://new.test.com',
            username='newuser',
            access_token='new_token_123',
            is_default=False
        )
        
        self.assertIsNotNone(platform)
        self.assertEqual(platform.name, 'New Test Platform')
        self.assertEqual(platform.platform_type, 'pixelfed')
        self.assertEqual(platform.user_id, user.id)
        self.assertFalse(platform.is_default)
    
    def test_create_platform_connection_validation(self):
        """Test platform connection creation validation"""
        user = self.get_test_user()
        
        # Test invalid user ID
        with self.assertRaises(PlatformValidationError):
            self.db_manager.create_platform_connection(
                user_id=99999,
                name='Invalid User',
                platform_type='pixelfed',
                instance_url='https://test.com',
                username='user',
                access_token='token'
            )
        
        # Test invalid platform type
        with self.assertRaises(PlatformValidationError):
            self.db_manager.create_platform_connection(
                user_id=user.id,
                name='Invalid Type',
                platform_type='invalid_type',
                instance_url='https://test.com',
                username='user',
                access_token='token'
            )
        
        # Test empty name
        with self.assertRaises(PlatformValidationError):
            self.db_manager.create_platform_connection(
                user_id=user.id,
                name='',
                platform_type='pixelfed',
                instance_url='https://test.com',
                username='user',
                access_token='token'
            )
    
    def test_get_platform_connection(self):
        """Test getting platform connection by ID"""
        platform = self.get_test_platform()
        
        retrieved_platform = self.db_manager.get_platform_connection(platform.id)
        
        self.assertIsNotNone(retrieved_platform)
        self.assertEqual(retrieved_platform.id, platform.id)
        self.assertEqual(retrieved_platform.name, platform.name)
    
    def test_get_user_platform_connections(self):
        """Test getting user's platform connections"""
        user = self.get_test_user()
        
        platforms = self.db_manager.get_user_platform_connections(user.id)
        
        self.assertGreater(len(platforms), 0)
        for platform in platforms:
            self.assertEqual(platform.user_id, user.id)
            self.assertTrue(platform.is_active)
    
    def test_update_platform_connection(self):
        """Test updating platform connection"""
        platform = self.get_test_platform()
        
        success = self.db_manager.update_platform_connection(
            connection_id=platform.id,
            user_id=platform.user_id,
            name='Updated Name',
            instance_url='https://updated.test.com'
        )
        
        self.assertTrue(success)
        
        # Verify update
        updated_platform = self.db_manager.get_platform_connection(platform.id)
        self.assertEqual(updated_platform.name, 'Updated Name')
        self.assertEqual(updated_platform.instance_url, 'https://updated.test.com')
    
    def test_update_platform_connection_validation(self):
        """Test platform connection update validation"""
        platform = self.get_test_platform()
        
        # Test invalid connection ID
        with self.assertRaises(PlatformValidationError):
            self.db_manager.update_platform_connection(
                connection_id=99999,
                name='Invalid ID'
            )
        
        # Test unauthorized user
        other_user = self.users[1]
        with self.assertRaises(PlatformValidationError):
            self.db_manager.update_platform_connection(
                connection_id=platform.id,
                user_id=other_user.id,
                name='Unauthorized'
            )
    
    def test_delete_platform_connection(self):
        """Test deleting platform connection"""
        user = self.get_test_user()
        
        # Create additional platform for deletion
        platform = self.db_manager.create_platform_connection(
            user_id=user.id,
            name='To Delete',
            platform_type='pixelfed',
            instance_url='https://delete.test.com',
            username='deleteuser',
            access_token='delete_token'
        )
        
        success = self.db_manager.delete_platform_connection(
            connection_id=platform.id,
            user_id=user.id
        )
        
        self.assertTrue(success)
        
        # Verify deletion
        deleted_platform = self.db_manager.get_platform_connection(platform.id)
        self.assertIsNone(deleted_platform)
    
    def test_set_default_platform(self):
        """Test setting default platform"""
        user = self.get_test_user()
        platforms = self.db_manager.get_user_platform_connections(user.id)
        
        # Set second platform as default
        new_default = platforms[1]
        success = self.db_manager.set_default_platform(user.id, new_default.id)
        
        self.assertTrue(success)
        
        # Verify default was changed
        updated_platforms = self.db_manager.get_user_platform_connections(user.id)
        default_platforms = [p for p in updated_platforms if p.is_default]
        
        self.assertEqual(len(default_platforms), 1)
        self.assertEqual(default_platforms[0].id, new_default.id)

class TestPlatformFiltering(PlatformTestCase):
    """Test platform filtering in database queries"""
    
    def test_platform_aware_post_queries(self):
        """Test platform filtering for posts"""
        user = self.get_test_user()
        platform = self.get_test_platform()
        
        # Set platform context
        self.db_manager.set_platform_context(user.id, platform.id)
        
        # Get posts with platform filtering
        posts = self.db_manager.get_session().query(Post).all()
        platform_posts = self.db_manager._apply_platform_filter(
            self.db_manager.get_session().query(Post), Post
        ).all()
        
        # Platform-filtered results should be subset
        self.assertLessEqual(len(platform_posts), len(posts))
        
        # All filtered posts should belong to platform
        for post in platform_posts:
            self.assertEqual(post.platform_connection_id, platform.id)
    
    def test_platform_aware_image_queries(self):
        """Test platform filtering for images"""
        user = self.get_test_user()
        platform = self.get_test_platform()
        
        # Set platform context
        self.db_manager.set_platform_context(user.id, platform.id)
        
        # Get images with platform filtering
        images = self.db_manager.get_session().query(Image).all()
        platform_images = self.db_manager._apply_platform_filter(
            self.db_manager.get_session().query(Image), Image
        ).all()
        
        # Platform-filtered results should be subset
        self.assertLessEqual(len(platform_images), len(images))
        
        # All filtered images should belong to platform
        for image in platform_images:
            self.assertEqual(image.platform_connection_id, platform.id)
    
    def test_get_pending_images_platform_aware(self):
        """Test getting pending images with platform filtering"""
        user = self.get_test_user()
        platform = self.get_test_platform()
        
        # Set platform context
        self.db_manager.set_platform_context(user.id, platform.id)
        
        # Get pending images
        pending_images = self.db_manager.get_pending_images()
        
        # All should belong to current platform
        for image in pending_images:
            self.assertEqual(image.platform_connection_id, platform.id)
            self.assertEqual(image.status, ProcessingStatus.PENDING)
    
    def test_get_approved_images_platform_aware(self):
        """Test getting approved images with platform filtering"""
        user = self.get_test_user()
        platform = self.get_test_platform()
        
        # Set platform context
        self.db_manager.set_platform_context(user.id, platform.id)
        
        # Get approved images
        approved_images = self.db_manager.get_approved_images()
        
        # All should belong to current platform
        for image in approved_images:
            self.assertEqual(image.platform_connection_id, platform.id)
            self.assertEqual(image.status, ProcessingStatus.APPROVED)

class TestPlatformStatistics(PlatformTestCase):
    """Test platform-specific statistics"""
    
    def test_get_platform_processing_stats(self):
        """Test getting statistics for specific platform"""
        platform = self.get_test_platform()
        
        stats = self.db_manager.get_platform_processing_stats(platform.id)
        
        self.assertIsInstance(stats, dict)
        self.assertIn('total_posts', stats)
        self.assertIn('total_images', stats)
        self.assertIn('pending_review', stats)
        self.assertIn('approved', stats)
        self.assertIn('posted', stats)
        self.assertIn('rejected', stats)
        
        # All counts should be non-negative
        for key, value in stats.items():
            self.assertGreaterEqual(value, 0)
    
    def test_get_processing_stats_platform_aware(self):
        """Test getting processing statistics with platform context"""
        user = self.get_test_user()
        platform = self.get_test_platform()
        
        # Set platform context
        self.db_manager.set_platform_context(user.id, platform.id)
        
        # Get platform-aware stats
        stats = self.db_manager.get_processing_stats(platform_aware=True)
        
        self.assertIsInstance(stats, dict)
        self.assertIn('platform_info', stats)
        
        # Platform info should match current context
        if stats['platform_info']:
            self.assertEqual(stats['platform_info']['platform_type'], platform.platform_type)
    
    def test_get_user_platform_summary(self):
        """Test getting user platform summary"""
        user = self.get_test_user()
        
        summary = self.db_manager.get_user_platform_summary(user.id)
        
        self.assertIsInstance(summary, dict)
        self.assertIn('total_platforms', summary)
        self.assertIn('platforms', summary)
        self.assertIn('combined_stats', summary)
        
        # Should have platforms from fixtures
        self.assertGreater(summary['total_platforms'], 0)
        self.assertEqual(len(summary['platforms']), summary['total_platforms'])
        
        # Each platform should have stats
        for platform_info in summary['platforms']:
            self.assertIn('stats', platform_info)
            self.assertIn('name', platform_info)
            self.assertIn('platform_type', platform_info)
    
    def test_get_platform_statistics(self):
        """Test getting statistics for all platforms"""
        user = self.get_test_user()
        
        stats = self.db_manager.get_platform_statistics(user_id=user.id)
        
        self.assertIsInstance(stats, dict)
        self.assertGreater(len(stats), 0)
        
        # Each platform should have statistics
        for platform_name, platform_stats in stats.items():
            self.assertIsInstance(platform_stats, dict)
            self.assertIn('total_posts', platform_stats)
            self.assertIn('total_images', platform_stats)

class TestDataIsolation(PlatformTestCase):
    """Test data isolation between platforms"""
    
    def test_platform_data_isolation(self):
        """Test that data is isolated between platforms"""
        user = self.get_test_user()
        platform1 = self.get_test_platform('pixelfed')
        platform2 = self.get_test_platform('mastodon')
        
        # Set context to platform1
        self.db_manager.set_platform_context(user.id, platform1.id)
        
        # Get platform1 data
        platform1_posts = self.db_manager._apply_platform_filter(
            self.db_manager.get_session().query(Post), Post
        ).all()
        
        # Set context to platform2
        self.db_manager.set_platform_context(user.id, platform2.id)
        
        # Get platform2 data
        platform2_posts = self.db_manager._apply_platform_filter(
            self.db_manager.get_session().query(Post), Post
        ).all()
        
        # Data should be different
        platform1_ids = {post.id for post in platform1_posts}
        platform2_ids = {post.id for post in platform2_posts}
        
        # Should have no overlap (complete isolation)
        self.assertEqual(len(platform1_ids.intersection(platform2_ids)), 0)
    
    def test_cross_platform_access_prevention(self):
        """Test that users cannot access other platforms' data"""
        user1 = self.get_test_user()
        user2 = self.users[1]
        
        # Create platform for user2
        user2_platform = self.db_manager.create_platform_connection(
            user_id=user2.id,
            name='User2 Platform',
            platform_type='pixelfed',
            instance_url='https://user2.test.com',
            username='user2',
            access_token='user2_token'
        )
        
        # Try to set user1's context to user2's platform
        with self.assertRaises(Exception):
            self.db_manager.set_platform_context(user1.id, user2_platform.id)
    
    def test_validate_data_isolation(self):
        """Test data isolation validation"""
        user = self.get_test_user()
        
        validation_results = self.db_manager.validate_data_isolation(user.id)
        
        self.assertIsInstance(validation_results, dict)
        self.assertIn('validation_passed', validation_results)
        self.assertIn('platforms_tested', validation_results)
        self.assertIn('isolation_issues', validation_results)
        
        # Should pass validation
        self.assertTrue(validation_results['validation_passed'])
        self.assertEqual(len(validation_results['isolation_issues']), 0)

class TestPlatformOperations(PlatformTestCase):
    """Test platform-aware database operations"""
    
    def test_get_or_create_post_platform_aware(self):
        """Test creating posts with platform context"""
        user = self.get_test_user()
        platform = self.get_test_platform()
        
        # Set platform context
        self.db_manager.set_platform_context(user.id, platform.id)
        
        # Create post
        post = self.db_manager.get_or_create_post(
            post_id='new_post_123',
            user_id='testuser',
            post_url='https://test.com/post/123',
            post_content='New test post'
        )
        
        self.assertIsNotNone(post)
        self.assertEqual(post.platform_connection_id, platform.id)
        self.assertEqual(post.post_id, 'new_post_123')
    
    def test_save_image_platform_aware(self):
        """Test saving images with platform context"""
        user = self.get_test_user()
        platform = self.get_test_platform()
        post = self.posts[0]
        
        # Set platform context
        self.db_manager.set_platform_context(user.id, platform.id)
        
        # Save image
        image_id = self.db_manager.save_image(
            post_id=post.id,
            image_url='https://test.com/new_image.jpg',
            local_path='/tmp/new_image.jpg',
            attachment_index=0,
            media_type='image/jpeg'
        )
        
        self.assertIsNotNone(image_id)
        
        # Verify image has platform context
        session = self.db_manager.get_session()
        try:
            image = session.query(Image).get(image_id)
            self.assertEqual(image.platform_connection_id, platform.id)
        finally:
            session.close()
    
    def test_update_image_caption_platform_aware(self):
        """Test updating image captions with platform validation"""
        user = self.get_test_user()
        platform = self.get_test_platform()
        image = self.images[0]
        
        # Set platform context
        self.db_manager.set_platform_context(user.id, platform.id)
        
        # Update caption
        success = self.db_manager.update_image_caption(
            image_id=image.id,
            generated_caption='Updated test caption',
            prompt_used='test_prompt'
        )
        
        self.assertTrue(success)
        
        # Verify update
        session = self.db_manager.get_session()
        try:
            updated_image = session.query(Image).get(image.id)
            self.assertEqual(updated_image.generated_caption, 'Updated test caption')
        finally:
            session.close()
    
    def test_is_image_processed_platform_aware(self):
        """Test checking if image is processed with platform context"""
        user = self.get_test_user()
        platform = self.get_test_platform()
        image = self.images[0]
        
        # Set platform context
        self.db_manager.set_platform_context(user.id, platform.id)
        
        # Check if processed
        is_processed = self.db_manager.is_image_processed(image.image_url)
        
        # Should return boolean
        self.assertIsInstance(is_processed, bool)

if __name__ == '__main__':
    unittest.main()
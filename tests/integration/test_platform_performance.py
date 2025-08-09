# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Integration tests for platform performance

Tests performance characteristics of platform-aware operations.
"""

import unittest
import time
from tests.fixtures.platform_fixtures import PlatformTestCase
from models import Post, Image, PlatformConnection
from platform_context import PlatformContextManager


class TestPlatformQueryPerformance(PlatformTestCase):
    """Test performance of platform-filtered queries"""
    
    def setUp(self):
        """Set up test with context manager and performance data"""
        super().setUp()
        self.context_manager = PlatformContextManager(self.session)
        self._create_performance_test_data()
    
    def _create_performance_test_data(self):
        """Create additional data for performance testing"""
        user = self.get_test_user()
        platform = self.get_test_platform()
        
        # Create additional posts for performance testing
        for i in range(100):
            post = Post(
                post_id=f'perf_post_{i}',
                user_id='perfuser',
                post_url=f'https://perf.test/post/{i}',
                post_content=f'Performance test post {i}',
                platform_connection_id=platform.id
            )
            self.session.add(post)
        
        self.session.commit()
        
        # Create additional images
        posts = self.session.query(Post).filter(
            Post.post_id.like('perf_post_%')
        ).all()
        
        for i, post in enumerate(posts[:50]):  # Create images for first 50 posts
            image = Image(
                post_id=post.id,
                image_url=f'https://perf.test/image_{i}.jpg',
                local_path=f'/tmp/perf_image_{i}.jpg',
                attachment_index=0,
                media_type='image/jpeg',
                image_post_id=f'perf_media_{i}',
                generated_caption=f'Performance test image {i}',
                platform_connection_id=platform.id
            )
            self.session.add(image)
        
        self.session.commit()
    
    def test_platform_filtered_query_performance(self):
        """Test performance of platform-filtered queries"""
        user = self.get_test_user()
        platform = self.get_test_platform()
        
        # Set platform context
        self.context_manager.set_context(user.id, platform.id)
        
        # Measure query performance
        start_time = time.time()
        
        posts = self.context_manager.apply_platform_filter(
            self.session.query(Post), Post
        ).all()
        
        end_time = time.time()
        query_time = end_time - start_time
        
        # Query should complete quickly (under 1 second for test data)
        self.assertLess(query_time, 1.0)
        
        # Verify results are correct
        self.assertGreater(len(posts), 0)
        for post in posts:
            self.assertEqual(post.platform_connection_id, platform.id)
    
    def test_concurrent_platform_query_performance(self):
        """Test performance with concurrent platform queries"""
        user = self.get_test_user()
        platforms = [self.get_test_platform('pixelfed'), self.get_test_platform('mastodon')]
        
        # Create separate context managers for concurrent operations
        context_managers = [
            PlatformContextManager(self.session),
            PlatformContextManager(self.session)
        ]
        
        # Set different contexts
        for i, (context_mgr, platform) in enumerate(zip(context_managers, platforms)):
            context_mgr.set_context(user.id, platform.id)
        
        # Measure concurrent query performance
        start_time = time.time()
        
        results = []
        for context_mgr in context_managers:
            posts = context_mgr.apply_platform_filter(
                self.session.query(Post), Post
            ).all()
            results.append(posts)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Concurrent queries should complete quickly
        self.assertLess(total_time, 2.0)
        
        # Verify results are isolated
        if len(results) >= 2:
            posts1_ids = {post.id for post in results[0]}
            posts2_ids = {post.id for post in results[1]}
            self.assertEqual(len(posts1_ids.intersection(posts2_ids)), 0)
    
    def test_platform_statistics_performance(self):
        """Test performance of platform statistics calculation"""
        user = self.get_test_user()
        platform = self.get_test_platform()
        
        # Set platform context
        self.context_manager.set_context(user.id, platform.id)
        
        # Measure statistics calculation performance
        start_time = time.time()
        
        stats = self.context_manager.get_platform_statistics()
        
        end_time = time.time()
        stats_time = end_time - start_time
        
        # Statistics calculation should be fast
        self.assertLess(stats_time, 0.5)
        
        # Verify statistics structure
        self.assertIsInstance(stats, dict)
        self.assertIn('total_posts', stats)
        self.assertIn('total_images', stats)
    
    def test_platform_switching_performance(self):
        """Test performance of platform switching operations"""
        user = self.get_test_user()
        platforms = [self.get_test_platform('pixelfed'), self.get_test_platform('mastodon')]
        
        # Measure platform switching performance
        start_time = time.time()
        
        # Perform multiple platform switches
        for i in range(20):
            platform = platforms[i % 2]
            self.context_manager.set_context(user.id, platform.id)
            
            # Verify context is correct
            context = self.context_manager.require_context()
            self.assertEqual(context.platform_connection_id, platform.id)
        
        end_time = time.time()
        switching_time = end_time - start_time
        
        # Platform switching should be fast
        self.assertLess(switching_time, 1.0)


class TestPlatformLoadTesting(PlatformTestCase):
    """Test system performance under load"""
    
    def test_multiple_users_platform_operations(self):
        """Test performance with multiple users and platforms"""
        # Create additional users and platforms
        additional_users = []
        additional_platforms = []
        
        for i in range(5):  # Create 5 additional users
            from models import User, UserRole
            user = User(
                username=f'loadtest_user_{i}',
                email=f'loadtest{i}@test.com',
                role=UserRole.REVIEWER,
                is_active=True
            )
            user.set_password('testpass123')
            self.session.add(user)
            additional_users.append(user)
        
        self.session.commit()
        
        # Create platforms for each user
        for i, user in enumerate(additional_users):
            platform = PlatformConnection(
                user_id=user.id,
                name=f'Load Test Platform {i}',
                platform_type='pixelfed',
                instance_url=f'https://loadtest{i}.com',
                username=f'loaduser{i}',
                access_token=f'loadtest_token_{i}',
                is_default=True
            )
            self.session.add(platform)
            additional_platforms.append(platform)
        
        self.session.commit()
        
        # Test concurrent operations
        start_time = time.time()
        
        context_managers = []
        for user, platform in zip(additional_users, additional_platforms):
            context_mgr = PlatformContextManager(self.session)
            context_mgr.set_context(user.id, platform.id)
            context_managers.append(context_mgr)
        
        # Perform operations for each user/platform
        for context_mgr in context_managers:
            posts = context_mgr.apply_platform_filter(
                self.session.query(Post), Post
            ).all()
            
            # Verify isolation
            for post in posts:
                context = context_mgr.require_context()
                self.assertEqual(post.platform_connection_id, context.platform_connection_id)
        
        end_time = time.time()
        load_time = end_time - start_time
        
        # Load test should complete in reasonable time
        self.assertLess(load_time, 5.0)
    
    def test_large_dataset_performance(self):
        """Test performance with larger datasets"""
        user = self.get_test_user()
        platform = self.get_test_platform()
        
        # Create larger dataset
        large_posts = []
        for i in range(500):  # Create 500 posts
            post = Post(
                post_id=f'large_dataset_post_{i}',
                user_id='largeuser',
                post_url=f'https://large.test/post/{i}',
                post_content=f'Large dataset test post {i}',
                platform_connection_id=platform.id
            )
            self.session.add(post)
            large_posts.append(post)
            
            # Commit in batches to avoid memory issues
            if i % 100 == 0:
                self.session.commit()
        
        self.session.commit()
        
        # Test query performance with large dataset
        self.context_manager.set_context(user.id, platform.id)
        
        start_time = time.time()
        
        posts = self.context_manager.apply_platform_filter(
            self.session.query(Post), Post
        ).filter(Post.post_id.like('large_dataset_post_%')).all()
        
        end_time = time.time()
        query_time = end_time - start_time
        
        # Should handle large dataset efficiently
        self.assertLess(query_time, 2.0)
        self.assertEqual(len(posts), 500)
    
    def test_memory_usage_platform_operations(self):
        """Test memory usage during platform operations"""
        import psutil
        import os
        
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        user = self.get_test_user()
        platforms = [self.get_test_platform('pixelfed'), self.get_test_platform('mastodon')]
        
        # Perform memory-intensive operations
        for i in range(50):
            platform = platforms[i % 2]
            self.context_manager.set_context(user.id, platform.id)
            
            # Query data
            posts = self.context_manager.apply_platform_filter(
                self.session.query(Post), Post
            ).all()
            
            images = self.context_manager.apply_platform_filter(
                self.session.query(Image), Image
            ).all()
            
            # Get statistics
            stats = self.context_manager.get_platform_statistics()
        
        # Get final memory usage
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 50MB for test operations)
        self.assertLess(memory_increase, 50 * 1024 * 1024)


class TestPlatformConcurrencyPerformance(PlatformTestCase):
    """Test performance under concurrent access"""
    
    def test_concurrent_context_switching(self):
        """Test performance of concurrent context switching"""
        user = self.get_test_user()
        platforms = [self.get_test_platform('pixelfed'), self.get_test_platform('mastodon')]
        
        # Create multiple context managers for concurrent access
        context_managers = [
            PlatformContextManager(self.session) for _ in range(10)
        ]
        
        start_time = time.time()
        
        # Perform concurrent context switching
        for i, context_mgr in enumerate(context_managers):
            platform = platforms[i % 2]
            context_mgr.set_context(user.id, platform.id)
            
            # Verify context
            context = context_mgr.require_context()
            self.assertEqual(context.platform_connection_id, platform.id)
        
        end_time = time.time()
        concurrent_time = end_time - start_time
        
        # Concurrent operations should complete quickly
        self.assertLess(concurrent_time, 2.0)
    
    def test_concurrent_data_access(self):
        """Test performance of concurrent data access"""
        user = self.get_test_user()
        platforms = [self.get_test_platform('pixelfed'), self.get_test_platform('mastodon')]
        
        # Create context managers for concurrent access
        context_managers = [
            PlatformContextManager(self.session),
            PlatformContextManager(self.session)
        ]
        
        # Set different contexts
        for context_mgr, platform in zip(context_managers, platforms):
            context_mgr.set_context(user.id, platform.id)
        
        start_time = time.time()
        
        # Perform concurrent data access
        results = []
        for context_mgr in context_managers:
            posts = context_mgr.apply_platform_filter(
                self.session.query(Post), Post
            ).all()
            
            images = context_mgr.apply_platform_filter(
                self.session.query(Image), Image
            ).all()
            
            results.append((posts, images))
        
        end_time = time.time()
        access_time = end_time - start_time
        
        # Concurrent access should be efficient
        self.assertLess(access_time, 1.5)
        
        # Verify data isolation
        if len(results) >= 2:
            posts1, images1 = results[0]
            posts2, images2 = results[1]
            
            posts1_ids = {post.id for post in posts1}
            posts2_ids = {post.id for post in posts2}
            self.assertEqual(len(posts1_ids.intersection(posts2_ids)), 0)


if __name__ == '__main__':
    unittest.main()
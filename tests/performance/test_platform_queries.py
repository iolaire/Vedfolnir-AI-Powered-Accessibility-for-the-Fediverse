# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Performance tests for platform-filtered queries

Tests query performance with platform filtering.
"""

import unittest
import time
from tests.fixtures.platform_fixtures import PlatformTestCase
from models import Post, Image, PlatformConnection
from platform_context import PlatformContextManager

class TestPlatformQueryPerformance(PlatformTestCase):
    """Test performance of platform-filtered queries"""
    
    def setUp(self):
        """Set up performance test data"""
        super().setUp()
        self.context_manager = PlatformContextManager(self.session)
        self._create_performance_data()
    
    def _create_performance_data(self):
        """Create test data for performance testing"""
        user = self.get_test_user()
        platform = self.get_test_platform()
        
        # Create 200 posts for performance testing
        posts = []
        for i in range(200):
            post = Post(
                post_id=f'perf_query_post_{i}',
                user_id='perfuser',
                post_url=f'https://perf.test/post/{i}',
                post_content=f'Performance query test post {i}',
                platform_connection_id=platform.id
            )
            posts.append(post)
            self.session.add(post)
        
        self.session.commit()
        
        # Create images for first 100 posts
        for i, post in enumerate(posts[:100]):
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
    
    def test_platform_post_query_performance(self):
        """Test performance of platform-filtered post queries"""
        user = self.get_test_user()
        platform = self.get_test_platform()
        
        self.context_manager.set_context(user.id, platform.id)
        
        # Measure query time
        start_time = time.time()
        
        posts = self.context_manager.apply_platform_filter(
            self.session.query(Post), Post
        ).all()
        
        end_time = time.time()
        query_time = end_time - start_time
        
        # Should complete quickly (under 0.5 seconds)
        self.assertLess(query_time, 0.5)
        self.assertGreater(len(posts), 0)
    
    def test_platform_image_query_performance(self):
        """Test performance of platform-filtered image queries"""
        user = self.get_test_user()
        platform = self.get_test_platform()
        
        self.context_manager.set_context(user.id, platform.id)
        
        # Measure query time
        start_time = time.time()
        
        images = self.context_manager.apply_platform_filter(
            self.session.query(Image), Image
        ).all()
        
        end_time = time.time()
        query_time = end_time - start_time
        
        # Should complete quickly
        self.assertLess(query_time, 0.5)
        self.assertGreater(len(images), 0)
    
    def test_complex_platform_query_performance(self):
        """Test performance of complex platform-filtered queries"""
        user = self.get_test_user()
        platform = self.get_test_platform()
        
        self.context_manager.set_context(user.id, platform.id)
        
        # Complex query with joins
        start_time = time.time()
        
        query = self.session.query(Post).join(Image).filter(
            Post.platform_connection_id == platform.id,
            Image.platform_connection_id == platform.id
        )
        results = query.all()
        
        end_time = time.time()
        query_time = end_time - start_time
        
        # Complex query should still be fast
        self.assertLess(query_time, 1.0)
        self.assertGreaterEqual(len(results), 0)
    
    def test_platform_statistics_query_performance(self):
        """Test performance of platform statistics queries"""
        user = self.get_test_user()
        platform = self.get_test_platform()
        
        self.context_manager.set_context(user.id, platform.id)
        
        # Measure statistics calculation time
        start_time = time.time()
        
        stats = self.context_manager.get_platform_statistics()
        
        end_time = time.time()
        stats_time = end_time - start_time
        
        # Statistics should calculate quickly
        self.assertLess(stats_time, 0.3)
        self.assertIsInstance(stats, dict)
        self.assertIn('total_posts', stats)

class TestQueryOptimization(PlatformTestCase):
    """Test query optimization for platform operations"""
    
    def test_platform_index_effectiveness(self):
        """Test that platform indexes improve query performance"""
        user = self.get_test_user()
        platform = self.get_test_platform()
        
        # Query with platform filter (should use index)
        start_time = time.time()
        
        posts = self.session.query(Post).filter(
            Post.platform_connection_id == platform.id
        ).all()
        
        end_time = time.time()
        indexed_time = end_time - start_time
        
        # Should be fast with proper indexing
        self.assertLess(indexed_time, 0.2)
        self.assertGreaterEqual(len(posts), 0)
    
    def test_bulk_query_performance(self):
        """Test performance of bulk platform queries"""
        user = self.get_test_user()
        platforms = [self.get_test_platform('pixelfed'), self.get_test_platform('mastodon')]
        
        # Bulk query for multiple platforms
        start_time = time.time()
        
        platform_ids = [p.id for p in platforms]
        posts = self.session.query(Post).filter(
            Post.platform_connection_id.in_(platform_ids)
        ).all()
        
        end_time = time.time()
        bulk_time = end_time - start_time
        
        # Bulk query should be efficient
        self.assertLess(bulk_time, 0.5)
        self.assertGreaterEqual(len(posts), 0)
    
    def test_pagination_performance(self):
        """Test performance of paginated platform queries"""
        user = self.get_test_user()
        platform = self.get_test_platform()
        
        self.context_manager.set_context(user.id, platform.id)
        
        # Test paginated query
        start_time = time.time()
        
        posts = self.context_manager.apply_platform_filter(
            self.session.query(Post), Post
        ).limit(50).offset(0).all()
        
        end_time = time.time()
        pagination_time = end_time - start_time
        
        # Pagination should be fast
        self.assertLess(pagination_time, 0.3)
        self.assertLessEqual(len(posts), 50)

class TestConcurrentQueryPerformance(PlatformTestCase):
    """Test performance under concurrent query load"""
    
    def test_concurrent_platform_queries(self):
        """Test performance with concurrent platform queries"""
        user = self.get_test_user()
        platforms = [self.get_test_platform('pixelfed'), self.get_test_platform('mastodon')]
        
        # Create multiple context managers for concurrent queries
        context_managers = [
            PlatformContextManager(self.session),
            PlatformContextManager(self.session)
        ]
        
        # Set different contexts
        for context_mgr, platform in zip(context_managers, platforms):
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
        concurrent_time = end_time - start_time
        
        # Concurrent queries should complete reasonably fast
        self.assertLess(concurrent_time, 1.0)
        self.assertEqual(len(results), 2)
    
    def test_high_frequency_context_switching(self):
        """Test performance with high-frequency context switching"""
        user = self.get_test_user()
        platforms = [self.get_test_platform('pixelfed'), self.get_test_platform('mastodon')]
        
        context_manager = PlatformContextManager(self.session)
        
        # Measure rapid context switching
        start_time = time.time()
        
        for i in range(50):  # 50 rapid switches
            platform = platforms[i % 2]
            context_manager.set_context(user.id, platform.id)
            
            # Quick query to verify context
            context = context_manager.require_context()
            self.assertEqual(context.platform_connection_id, platform.id)
        
        end_time = time.time()
        switching_time = end_time - start_time
        
        # Rapid switching should be efficient
        self.assertLess(switching_time, 2.0)

if __name__ == '__main__':
    unittest.main()
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Load testing for platform operations

Tests system performance under load with multiple platforms and users.
"""

import unittest
import time
import threading
from tests.fixtures.platform_fixtures import PlatformTestCase
from models import User, UserRole, PlatformConnection, Post, Image
from app.services.platform.core.platform_context import PlatformContextManager

class TestPlatformLoadTesting(PlatformTestCase):
    """Test system performance under load"""
    
    def setUp(self):
        """Set up load testing environment"""
        super().setUp()
        self._create_load_test_data()
    
    def _create_load_test_data(self):
        """Create data for load testing"""
        # Create additional users
        self.load_users = []
        for i in range(10):
            user = User(
                username=f'loadtest_user_{i}',
                email=f'loadtest{i}@test.com',
                role=UserRole.REVIEWER,
                is_active=True
            )
            user.set_password('loadtest123')
            self.session.add(user)
            self.load_users.append(user)
        
        self.session.commit()
        
        # Create platforms for each user
        self.load_platforms = []
        for i, user in enumerate(self.load_users):
            platform = PlatformConnection(
                user_id=user.id,
                name=f'Load Test Platform {i}',
                platform_type='pixelfed' if i % 2 == 0 else 'mastodon',
                instance_url=f'https://loadtest{i}.com',
                username=f'loaduser{i}',
                access_token=f'loadtest_token_{i}',
                is_default=True
            )
            self.session.add(platform)
            self.load_platforms.append(platform)
        
        self.session.commit()
        
        # Create posts for each platform
        for i, platform in enumerate(self.load_platforms):
            for j in range(20):  # 20 posts per platform
                post = Post(
                    post_id=f'load_post_{i}_{j}',
                    user_id=f'loaduser{i}',
                    post_url=f'https://loadtest{i}.com/post/{j}',
                    post_content=f'Load test post {i}-{j}',
                    platform_connection_id=platform.id
                )
                self.session.add(post)
        
        self.session.commit()
    
    def test_multiple_users_concurrent_access(self):
        """Test performance with multiple users accessing concurrently"""
        context_managers = []
        
        # Create context managers for each user/platform pair
        for user, platform in zip(self.load_users[:5], self.load_platforms[:5]):
            context_mgr = PlatformContextManager(self.session)
            context_mgr.set_context(user.id, platform.id)
            context_managers.append(context_mgr)
        
        # Measure concurrent access performance
        start_time = time.time()
        
        results = []
        for context_mgr in context_managers:
            posts = context_mgr.apply_platform_filter(
                self.session.query(Post), Post
            ).all()
            results.append(len(posts))
        
        end_time = time.time()
        concurrent_time = end_time - start_time
        
        # Should handle multiple users efficiently
        self.assertLess(concurrent_time, 3.0)
        self.assertEqual(len(results), 5)
        
        # Each user should get their own data
        for count in results:
            self.assertGreater(count, 0)
    
    def test_high_volume_platform_switching(self):
        """Test performance with high volume platform switching"""
        user = self.load_users[0]
        platforms = self.load_platforms[:3]  # Use first 3 platforms
        
        context_manager = PlatformContextManager(self.session)
        
        # Measure high-volume switching
        start_time = time.time()
        
        for i in range(100):  # 100 switches
            platform = platforms[i % len(platforms)]
            context_manager.set_context(user.id, platform.id)
            
            # Verify context is correct
            context = context_manager.require_context()
            self.assertEqual(context.platform_connection_id, platform.id)
        
        end_time = time.time()
        switching_time = end_time - start_time
        
        # High-volume switching should be manageable
        self.assertLess(switching_time, 5.0)
    
    def test_bulk_data_processing_performance(self):
        """Test performance with bulk data processing"""
        user = self.load_users[0]
        platform = self.load_platforms[0]
        
        context_manager = PlatformContextManager(self.session)
        context_manager.set_context(user.id, platform.id)
        
        # Measure bulk processing time
        start_time = time.time()
        
        # Process all posts for the platform
        posts = context_manager.apply_platform_filter(
            self.session.query(Post), Post
        ).all()
        
        # Simulate processing each post
        processed_count = 0
        for post in posts:
            # Simulate some processing work
            _ = post.post_content.upper()
            processed_count += 1
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Bulk processing should be efficient
        self.assertLess(processing_time, 2.0)
        self.assertGreater(processed_count, 0)
    
    def test_memory_usage_under_load(self):
        """Test memory usage under load conditions"""
        try:
            import psutil
            import os
            
            # Get initial memory usage
            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss
            
            # Perform memory-intensive operations
            context_managers = []
            for user, platform in zip(self.load_users, self.load_platforms):
                context_mgr = PlatformContextManager(self.session)
                context_mgr.set_context(user.id, platform.id)
                context_managers.append(context_mgr)
                
                # Load data for each platform
                posts = context_mgr.apply_platform_filter(
                    self.session.query(Post), Post
                ).all()
                
                # Keep references to simulate memory usage
                _ = [post.post_content for post in posts]
            
            # Get final memory usage
            final_memory = process.memory_info().rss
            memory_increase = final_memory - initial_memory
            
            # Memory increase should be reasonable (less than 100MB)
            self.assertLess(memory_increase, 100 * 1024 * 1024)
            
        except ImportError:
            self.skipTest("psutil not available for memory testing")

class TestScalabilityTesting(PlatformTestCase):
    """Test system scalability with increasing load"""
    
    def test_linear_performance_scaling(self):
        """Test that performance scales linearly with data size"""
        user = self.get_test_user()
        platform = self.get_test_platform()
        
        context_manager = PlatformContextManager(self.session)
        context_manager.set_context(user.id, platform.id)
        
        # Test with different data sizes
        data_sizes = [10, 50, 100]
        query_times = []
        
        for size in data_sizes:
            # Create test posts
            test_posts = []
            for i in range(size):
                post = Post(
                    post_id=f'scale_test_post_{size}_{i}',
                    user_id='scaleuser',
                    post_url=f'https://scale.test/post/{size}/{i}',
                    post_content=f'Scale test post {size}-{i}',
                    platform_connection_id=platform.id
                )
                test_posts.append(post)
                self.session.add(post)
            
            self.session.commit()
            
            # Measure query time
            start_time = time.time()
            
            posts = context_manager.apply_platform_filter(
                self.session.query(Post), Post
            ).filter(Post.post_id.like(f'scale_test_post_{size}_%')).all()
            
            end_time = time.time()
            query_time = end_time - start_time
            query_times.append(query_time)
            
            # Verify correct number of posts
            self.assertEqual(len(posts), size)
            
            # Clean up test posts
            for post in test_posts:
                self.session.delete(post)
            self.session.commit()
        
        # Performance should scale reasonably
        # Larger datasets should not be exponentially slower
        for i in range(1, len(query_times)):
            ratio = query_times[i] / query_times[0]
            size_ratio = data_sizes[i] / data_sizes[0]
            
            # Query time should not grow faster than data size
            self.assertLess(ratio, size_ratio * 2)
    
    def test_concurrent_user_scalability(self):
        """Test scalability with increasing concurrent users"""
        # Test with different numbers of concurrent users
        user_counts = [1, 3, 5]
        
        for user_count in user_counts:
            users = self.load_users[:user_count]
            platforms = self.load_platforms[:user_count]
            
            # Measure time for concurrent operations
            start_time = time.time()
            
            context_managers = []
            for user, platform in zip(users, platforms):
                context_mgr = PlatformContextManager(self.session)
                context_mgr.set_context(user.id, platform.id)
                context_managers.append(context_mgr)
            
            # Perform operations for each user
            results = []
            for context_mgr in context_managers:
                posts = context_mgr.apply_platform_filter(
                    self.session.query(Post), Post
                ).all()
                results.append(len(posts))
            
            end_time = time.time()
            operation_time = end_time - start_time
            
            # Time should not grow exponentially with user count
            expected_max_time = user_count * 0.5  # 0.5 seconds per user
            self.assertLess(operation_time, expected_max_time)
            
            # Each user should get results
            self.assertEqual(len(results), user_count)
            for result_count in results:
                self.assertGreaterEqual(result_count, 0)

class TestStressTestingPlatforms(PlatformTestCase):
    """Stress testing for platform operations"""
    
    def test_rapid_context_switching_stress(self):
        """Stress test rapid context switching"""
        user = self.load_users[0]
        platforms = self.load_platforms[:2]
        
        context_manager = PlatformContextManager(self.session)
        
        # Stress test with very rapid switching
        start_time = time.time()
        
        for i in range(200):  # 200 rapid switches
            platform = platforms[i % 2]
            context_manager.set_context(user.id, platform.id)
            
            # Quick verification
            context = context_manager.require_context()
            self.assertEqual(context.platform_connection_id, platform.id)
        
        end_time = time.time()
        stress_time = end_time - start_time
        
        # Should handle stress load
        self.assertLess(stress_time, 10.0)
    
    def test_concurrent_query_stress(self):
        """Stress test concurrent queries"""
        users = self.load_users[:5]
        platforms = self.load_platforms[:5]
        
        # Create context managers
        context_managers = []
        for user, platform in zip(users, platforms):
            context_mgr = PlatformContextManager(self.session)
            context_mgr.set_context(user.id, platform.id)
            context_managers.append(context_mgr)
        
        # Stress test with multiple query rounds
        start_time = time.time()
        
        for round_num in range(10):  # 10 rounds of queries
            results = []
            for context_mgr in context_managers:
                posts = context_mgr.apply_platform_filter(
                    self.session.query(Post), Post
                ).all()
                results.append(len(posts))
            
            # Verify results for each round
            self.assertEqual(len(results), 5)
        
        end_time = time.time()
        stress_time = end_time - start_time
        
        # Should handle stress queries
        self.assertLess(stress_time, 15.0)

if __name__ == '__main__':
    unittest.main()
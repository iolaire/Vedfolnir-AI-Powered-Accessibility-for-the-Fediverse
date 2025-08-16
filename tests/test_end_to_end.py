#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
End-to-end tests for Vedfolnir complete workflows.
"""
import unittest
import asyncio
import tempfile
import os
import sys
import json
import time
import threading
import subprocess
from unittest.mock import patch, MagicMock, AsyncMock, mock_open
from datetime import datetime, timedelta
import requests
import sqlite3

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import DatabaseManager
from models import Post, Image, ProcessingStatus, User, UserRole
from config import Config
from activitypub_client import ActivityPubClient
from ollama_caption_generator import OllamaCaptionGenerator
from post_service import PostingService
from image_processor import ImageProcessor
import main


class EndToEndTestBase(unittest.TestCase):
    """Base class for end-to-end tests"""
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        # Create temporary image directory
        self.temp_images_dir = tempfile.mkdtemp()
        
        # Create test config
        self.config = Config()
        self.config.storage.database_url = f"sqlite:///{self.temp_db.name}"
        self.config.storage.images_dir = self.temp_images_dir
        
        # Initialize database
        self.db_manager = DatabaseManager(self.config)
        
        # Create test user with environment-based credentials
        test_password = os.getenv('TEST_USER_PASSWORD', 'test_password_123')
        self.test_user = self.db_manager.create_user(
            username="testuser",
            email="test@test.com", 
            password=test_password,
            role=UserRole.ADMIN
        )
    
    def tearDown(self):
        """Clean up test environment"""
        self.db_manager.close_session()
        os.unlink(self.temp_db.name)
        
        # Clean up temp images directory
        import shutil
        shutil.rmtree(self.temp_images_dir, ignore_errors=True)


class TestCompleteWorkflows(EndToEndTestBase):
    """Test complete end-to-end workflows"""
    
    def test_single_user_processing_workflow(self):
        """Test complete workflow for processing a single user"""
        # Mock external dependencies
        with patch('activitypub_client.ActivityPubClient') as mock_client_class:
            with patch('ollama_caption_generator.OllamaCaptionGenerator') as mock_generator_class:
                with patch('image_processor.ImageProcessor.download_image') as mock_download:
                    
                    # Set up mocks
                    mock_client = AsyncMock()
                    mock_client_class.return_value = mock_client
                    
                    mock_generator = AsyncMock()
                    mock_generator_class.return_value = mock_generator
                    
                    # Mock API responses
                    mock_client.get_user_posts.return_value = [{
                        "id": "test_post_1",
                        "account": {"id": "test_user", "username": "testuser"},
                        "content": "Test post with image",
                        "url": "https://test.pixelfed.social/p/test_post_1",
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "media_attachments": [{
                            "id": "test_media_1",
                            "type": "image",
                            "url": "https://test.pixelfed.social/storage/test_image.jpg",
                            "description": None  # No alt text
                        }]
                    }]
                    
                    # Mock caption generation
                    mock_generator.generate_caption.return_value = (
                        "A beautiful sunset over the mountains",
                        {
                            "overall_score": 85,
                            "quality_level": "good",
                            "needs_review": False,
                            "feedback": "High quality caption"
                        }
                    )
                    
                    # Mock image download
                    mock_download.return_value = os.path.join(self.temp_images_dir, "test_image.jpg")
                    
                    # Create a fake image file
                    test_image_path = os.path.join(self.temp_images_dir, "test_image.jpg")
                    with open(test_image_path, 'wb') as f:
                        f.write(b"fake_image_data")
                    
                    # Run the main processing logic
                    async def run_processing():
                        # Simulate main.py processing logic
                        client = ActivityPubClient(self.config.activitypub)
                        generator = OllamaCaptionGenerator(self.config.ollama)
                        processor = ImageProcessor(self.config.storage)
                        
                        # Get user posts
                        posts_data = await client.get_user_posts("testuser", limit=10)
                        
                        processed_images = 0
                        for post_data in posts_data:
                            # Create post in database
                            post = self.db_manager.get_or_create_post(
                                post_id=post_data["id"],
                                user_id=post_data["account"]["id"],
                                post_url=post_data["url"],
                                post_content=post_data["content"]
                            )
                            
                            # Process media attachments
                            for i, media in enumerate(post_data["media_attachments"]):
                                if not media.get("description"):  # No alt text
                                    # Download image
                                    local_path = processor.download_image(
                                        media["url"], 
                                        media["id"]
                                    )
                                    
                                    # Save to database
                                    image_id = self.db_manager.save_image(
                                        post_id=post.id,
                                        image_url=media["url"],
                                        local_path=local_path,
                                        attachment_index=i,
                                        media_type="image/jpeg",
                                        image_post_id=media["id"]
                                    )
                                    
                                    # Generate caption
                                    caption_result = await generator.generate_caption(local_path)
                                    if caption_result:
                                        caption, quality_metrics = caption_result
                                        
                                        # Update database
                                        self.db_manager.update_image_caption(
                                            image_id=image_id,
                                            generated_caption=caption,
                                            quality_metrics=quality_metrics
                                        )
                                        processed_images += 1
                        
                        return processed_images
                    
                    # Run the processing
                    processed_count = asyncio.run(run_processing())
                    
                    # Verify results
                    self.assertEqual(processed_count, 1)
                    
                    # Check database state
                    stats = self.db_manager.get_processing_stats()
                    self.assertEqual(stats['total_posts'], 1)
                    self.assertEqual(stats['total_images'], 1)
                    self.assertEqual(stats['pending_review'], 1)
                    
                    # Verify image data
                    pending_images = self.db_manager.get_pending_images(limit=10)
                    self.assertEqual(len(pending_images), 1)
                    
                    image = pending_images[0]
                    self.assertEqual(image.generated_caption, "A beautiful sunset over the mountains")
                    self.assertEqual(image.caption_quality_score, 85)
                    self.assertFalse(image.needs_special_review)
    
    def test_multi_user_batch_processing(self):
        """Test batch processing of multiple users"""
        # Mock external dependencies
        with patch('activitypub_client.ActivityPubClient') as mock_client_class:
            with patch('ollama_caption_generator.OllamaCaptionGenerator') as mock_generator_class:
                with patch('image_processor.ImageProcessor.download_image') as mock_download:
                    
                    # Set up mocks
                    mock_client = AsyncMock()
                    mock_client_class.return_value = mock_client
                    
                    mock_generator = AsyncMock()
                    mock_generator_class.return_value = mock_generator
                    
                    # Mock API responses for multiple users
                    def mock_get_user_posts(username, limit=None):
                        return [{
                            "id": f"{username}_post_1",
                            "account": {"id": username, "username": username},
                            "content": f"Test post from {username}",
                            "url": f"https://test.pixelfed.social/p/{username}_post_1",
                            "created_at": datetime.now(timezone.utc).isoformat(),
                            "media_attachments": [{
                                "id": f"{username}_media_1",
                                "type": "image",
                                "url": f"https://test.pixelfed.social/storage/{username}_image.jpg",
                                "description": None
                            }]
                        }]
                    
                    mock_client.get_user_posts.side_effect = mock_get_user_posts
                    
                    # Mock caption generation
                    mock_generator.generate_caption.return_value = (
                        "Generated caption",
                        {"overall_score": 80, "quality_level": "good", "needs_review": False}
                    )
                    
                    # Mock image download
                    def mock_download_image(url, media_id):
                        image_path = os.path.join(self.temp_images_dir, f"{media_id}.jpg")
                        with open(image_path, 'wb') as f:
                            f.write(b"fake_image_data")
                        return image_path
                    
                    mock_download.side_effect = mock_download_image
                    
                    # Process multiple users
                    users = ["user1", "user2", "user3", "user4", "user5"]
                    
                    async def process_users():
                        client = ActivityPubClient(self.config.activitypub)
                        generator = OllamaCaptionGenerator(self.config.ollama)
                        processor = ImageProcessor(self.config.storage)
                        
                        total_processed = 0
                        for username in users:
                            posts_data = await client.get_user_posts(username, limit=10)
                            
                            for post_data in posts_data:
                                post = self.db_manager.get_or_create_post(
                                    post_id=post_data["id"],
                                    user_id=post_data["account"]["id"],
                                    post_url=post_data["url"],
                                    post_content=post_data["content"]
                                )
                                
                                for i, media in enumerate(post_data["media_attachments"]):
                                    if not media.get("description"):
                                        local_path = processor.download_image(
                                            media["url"], 
                                            media["id"]
                                        )
                                        
                                        image_id = self.db_manager.save_image(
                                            post_id=post.id,
                                            image_url=media["url"],
                                            local_path=local_path,
                                            attachment_index=i,
                                            media_type="image/jpeg",
                                            image_post_id=media["id"]
                                        )
                                        
                                        caption_result = await generator.generate_caption(local_path)
                                        if caption_result:
                                            caption, quality_metrics = caption_result
                                            self.db_manager.update_image_caption(
                                                image_id=image_id,
                                                generated_caption=caption,
                                                quality_metrics=quality_metrics
                                            )
                                            total_processed += 1
                        
                        return total_processed
                    
                    # Run processing
                    total_processed = asyncio.run(process_users())
                    
                    # Verify results
                    self.assertEqual(total_processed, 5)  # One image per user
                    
                    stats = self.db_manager.get_processing_stats()
                    self.assertEqual(stats['total_posts'], 5)
                    self.assertEqual(stats['total_images'], 5)
                    self.assertEqual(stats['pending_review'], 5)
    
    def test_review_and_approval_workflow(self):
        """Test the complete review and approval workflow"""
        # Create test data
        post = self.db_manager.get_or_create_post(
            post_id="review_test",
            user_id="test_user",
            post_url="https://test.com/post",
            post_content="Test post for review"
        )
        
        image_id = self.db_manager.save_image(
            post_id=post.id,
            image_url="https://test.com/image.jpg",
            local_path="/tmp/test_image.jpg",
            attachment_index=0,
            media_type="image/jpeg",
            image_post_id="test_media"
        )
        
        # Add generated caption
        self.db_manager.update_image_caption(
            image_id=image_id,
            generated_caption="Generated caption for review",
            quality_metrics={
                "overall_score": 75,
                "quality_level": "good",
                "needs_review": False
            }
        )
        
        # Test review workflow
        # 1. Get pending images
        pending_images = self.db_manager.get_pending_images(limit=10)
        self.assertEqual(len(pending_images), 1)
        
        image = pending_images[0]
        self.assertEqual(image.generated_caption, "Generated caption for review")
        self.assertEqual(image.status, ProcessingStatus.PENDING)
        
        # 2. Review and approve
        self.db_manager.review_image(
            image_id=image.id,
            reviewed_caption="Reviewed and approved caption",
            status=ProcessingStatus.APPROVED,
            reviewer_notes="Looks good, approved"
        )
        
        # 3. Verify approval
        approved_images = self.db_manager.get_approved_images(limit=10)
        self.assertEqual(len(approved_images), 1)
        
        approved_image = approved_images[0]
        self.assertEqual(approved_image.reviewed_caption, "Reviewed and approved caption")
        self.assertEqual(approved_image.final_caption, "Reviewed and approved caption")
        self.assertEqual(approved_image.status, ProcessingStatus.APPROVED)
        self.assertEqual(approved_image.reviewer_notes, "Looks good, approved")
        
        # 4. Test rejection workflow
        # Create another image for rejection
        image_id_2 = self.db_manager.save_image(
            post_id=post.id,
            image_url="https://test.com/image2.jpg",
            local_path="/tmp/test_image2.jpg",
            attachment_index=1,
            media_type="image/jpeg",
            image_post_id="test_media_2"
        )
        
        self.db_manager.update_image_caption(
            image_id=image_id_2,
            generated_caption="Poor quality caption",
            quality_metrics={
                "overall_score": 30,
                "quality_level": "poor",
                "needs_review": True
            }
        )
        
        # Reject the image
        self.db_manager.review_image(
            image_id=image_id_2,
            reviewed_caption="",
            status=ProcessingStatus.REJECTED,
            reviewer_notes="Caption quality too low"
        )
        
        # Verify rejection
        stats = self.db_manager.get_processing_stats()
        self.assertEqual(stats['approved'], 1)
        self.assertEqual(stats['rejected'], 1)
        self.assertEqual(stats['pending_review'], 0)
    
    def test_error_recovery_workflow(self):
        """Test error recovery and retry mechanisms"""
        # Mock external dependencies with failures
        with patch('activitypub_client.ActivityPubClient') as mock_client_class:
            with patch('ollama_caption_generator.OllamaCaptionGenerator') as mock_generator_class:
                
                mock_client = AsyncMock()
                mock_client_class.return_value = mock_client
                
                mock_generator = AsyncMock()
                mock_generator_class.return_value = mock_generator
                
                # Test API failure and recovery
                call_count = 0
                async def mock_get_user_posts_with_failure(username, limit=None):
                    nonlocal call_count
                    call_count += 1
                    if call_count == 1:
                        # First call fails
                        raise ConnectionError("API temporarily unavailable")
                    else:
                        # Second call succeeds
                        return [{
                            "id": "recovery_test",
                            "account": {"id": username, "username": username},
                            "content": "Recovery test post",
                            "url": f"https://test.pixelfed.social/p/recovery_test",
                            "created_at": datetime.now(timezone.utc).isoformat(),
                            "media_attachments": [{
                                "id": "recovery_media",
                                "type": "image",
                                "url": "https://test.pixelfed.social/storage/recovery.jpg",
                                "description": None
                            }]
                        }]
                
                mock_client.get_user_posts.side_effect = mock_get_user_posts_with_failure
                
                # Test caption generation failure and fallback
                generation_call_count = 0
                async def mock_generate_caption_with_fallback(image_path):
                    nonlocal generation_call_count
                    generation_call_count += 1
                    if generation_call_count == 1:
                        # First attempt fails
                        return None
                    else:
                        # Fallback succeeds
                        return (
                            "Fallback generated caption",
                            {"overall_score": 70, "quality_level": "acceptable", "needs_review": False}
                        )
                
                mock_generator.generate_caption.side_effect = mock_generate_caption_with_fallback
                
                # Test the recovery workflow
                async def test_recovery():
                    client = ActivityPubClient(self.config.activitypub)
                    generator = OllamaCaptionGenerator(self.config.ollama)
                    
                    # First attempt should fail, second should succeed
                    try:
                        posts_data = await client.get_user_posts("testuser", limit=10)
                        self.fail("Expected ConnectionError on first call")
                    except ConnectionError:
                        pass  # Expected failure
                    
                    # Retry should succeed
                    posts_data = await client.get_user_posts("testuser", limit=10)
                    self.assertEqual(len(posts_data), 1)
                    
                    # Test caption generation with fallback
                    caption_result = await generator.generate_caption("/tmp/test.jpg")
                    self.assertIsNone(caption_result)  # First attempt fails
                    
                    # Retry should succeed with fallback
                    caption_result = await generator.generate_caption("/tmp/test.jpg")
                    self.assertIsNotNone(caption_result)
                    self.assertEqual(caption_result[0], "Fallback generated caption")
                
                asyncio.run(test_recovery())
                
                # Verify retry attempts were made
                self.assertEqual(call_count, 2)
                self.assertEqual(generation_call_count, 2)


class TestPerformanceBenchmarks(EndToEndTestBase):
    """Performance benchmark tests"""
    
    def test_processing_performance_benchmark(self):
        """Benchmark processing performance with various dataset sizes"""
        # Test with different dataset sizes
        dataset_sizes = [10, 50, 100]
        results = {}
        
        for size in dataset_sizes:
            start_time = time.time()
            
            # Create test dataset
            posts = []
            for i in range(size):
                post = self.db_manager.get_or_create_post(
                    post_id=f"perf_post_{i}",
                    user_id=f"user_{i % 10}",  # 10 different users
                    post_url=f"https://test.com/post_{i}",
                    post_content=f"Performance test post {i}"
                )
                posts.append(post)
                
                # Add 1-3 images per post
                num_images = (i % 3) + 1
                for j in range(num_images):
                    image_id = self.db_manager.save_image(
                        post_id=post.id,
                        image_url=f"https://test.com/image_{i}_{j}.jpg",
                        local_path=f"/tmp/image_{i}_{j}.jpg",
                        attachment_index=j,
                        media_type="image/jpeg",
                        image_post_id=f"media_{i}_{j}"
                    )
                    
                    # Add generated caption
                    self.db_manager.update_image_caption(
                        image_id=image_id,
                        generated_caption=f"Generated caption for image {i}_{j}",
                        quality_metrics={
                            "overall_score": 80,
                            "quality_level": "good",
                            "needs_review": False
                        }
                    )
            
            processing_time = time.time() - start_time
            
            # Benchmark query performance
            query_start = time.time()
            stats = self.db_manager.get_processing_stats()
            pending_images = self.db_manager.get_pending_images(limit=100)
            query_time = time.time() - query_start
            
            results[size] = {
                'processing_time': processing_time,
                'query_time': query_time,
                'posts_created': len(posts),
                'images_created': stats['total_images'],
                'posts_per_second': len(posts) / processing_time,
                'images_per_second': stats['total_images'] / processing_time
            }
            
            # Clean up for next iteration
            self.tearDown()
            self.setUp()
        
        # Verify performance meets expectations
        for size, result in results.items():
            # Processing should be reasonably fast
            self.assertLess(result['processing_time'], size * 0.1)  # Less than 0.1s per post
            self.assertLess(result['query_time'], 1.0)  # Queries should be fast
            
            # Throughput should be reasonable
            self.assertGreater(result['posts_per_second'], 10)  # At least 10 posts/second
            self.assertGreater(result['images_per_second'], 10)  # At least 10 images/second
        
        # Print benchmark results for reference
        print("\nPerformance Benchmark Results:")
        print("Dataset Size | Processing Time | Query Time | Posts/sec | Images/sec")
        print("-" * 70)
        for size, result in results.items():
            print(f"{size:11d} | {result['processing_time']:14.2f}s | {result['query_time']:9.2f}s | "
                  f"{result['posts_per_second']:8.1f} | {result['images_per_second']:9.1f}")
    
    def test_concurrent_processing_benchmark(self):
        """Benchmark concurrent processing performance"""
        import concurrent.futures
        
        def create_posts_batch(batch_id, batch_size):
            """Create a batch of posts"""
            posts_created = 0
            for i in range(batch_size):
                post_id = f"concurrent_batch_{batch_id}_post_{i}"
                post = self.db_manager.get_or_create_post(
                    post_id=post_id,
                    user_id=f"batch_user_{batch_id}",
                    post_url=f"https://test.com/{post_id}",
                    post_content=f"Concurrent test post {batch_id}_{i}"
                )
                
                # Add image
                image_id = self.db_manager.save_image(
                    post_id=post.id,
                    image_url=f"https://test.com/image_{batch_id}_{i}.jpg",
                    local_path=f"/tmp/image_{batch_id}_{i}.jpg",
                    attachment_index=0,
                    media_type="image/jpeg",
                    image_post_id=f"media_{batch_id}_{i}"
                )
                posts_created += 1
            
            return posts_created
        
        # Test concurrent processing
        num_threads = 4
        batch_size = 25  # 25 posts per thread = 100 total
        
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(create_posts_batch, batch_id, batch_size)
                for batch_id in range(num_threads)
            ]
            
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        concurrent_time = time.time() - start_time
        total_posts = sum(results)
        
        # Verify results
        self.assertEqual(total_posts, num_threads * batch_size)
        
        # Check database consistency
        stats = self.db_manager.get_processing_stats()
        self.assertEqual(stats['total_posts'], total_posts)
        self.assertEqual(stats['total_images'], total_posts)
        
        # Performance should be better than sequential
        concurrent_throughput = total_posts / concurrent_time
        self.assertGreater(concurrent_throughput, 20)  # At least 20 posts/second
        
        print(f"\nConcurrent Processing Benchmark:")
        print(f"Threads: {num_threads}")
        print(f"Total Posts: {total_posts}")
        print(f"Processing Time: {concurrent_time:.2f}s")
        print(f"Throughput: {concurrent_throughput:.1f} posts/second")
    
    def test_memory_usage_benchmark(self):
        """Benchmark memory usage during processing"""
        try:
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss
            
            # Process a large dataset
            dataset_size = 200
            memory_samples = []
            
            for i in range(dataset_size):
                post = self.db_manager.get_or_create_post(
                    post_id=f"memory_test_{i}",
                    user_id=f"user_{i % 20}",
                    post_url=f"https://test.com/post_{i}",
                    post_content=f"Memory test post {i}"
                )
                
                # Add multiple images per post
                for j in range(3):
                    image_id = self.db_manager.save_image(
                        post_id=post.id,
                        image_url=f"https://test.com/image_{i}_{j}.jpg",
                        local_path=f"/tmp/image_{i}_{j}.jpg",
                        attachment_index=j,
                        media_type="image/jpeg",
                        image_post_id=f"media_{i}_{j}"
                    )
                    
                    self.db_manager.update_image_caption(
                        image_id=image_id,
                        generated_caption=f"Caption for image {i}_{j}",
                        quality_metrics={
                            "overall_score": 80,
                            "quality_level": "good",
                            "needs_review": False
                        }
                    )
                
                # Sample memory usage every 50 iterations
                if i % 50 == 0:
                    current_memory = process.memory_info().rss
                    memory_samples.append(current_memory)
            
            final_memory = process.memory_info().rss
            memory_increase = final_memory - initial_memory
            max_memory = max(memory_samples) if memory_samples else final_memory
            
            # Memory usage should be reasonable
            # Allow up to 100MB increase for processing 200 posts with 600 images
            max_allowed_increase = 100 * 1024 * 1024  # 100MB
            self.assertLess(memory_increase, max_allowed_increase)
            
            print(f"\nMemory Usage Benchmark:")
            print(f"Dataset Size: {dataset_size} posts, {dataset_size * 3} images")
            print(f"Initial Memory: {initial_memory / 1024 / 1024:.1f} MB")
            print(f"Final Memory: {final_memory / 1024 / 1024:.1f} MB")
            print(f"Memory Increase: {memory_increase / 1024 / 1024:.1f} MB")
            print(f"Max Memory: {max_memory / 1024 / 1024:.1f} MB")
            
        except ImportError:
            self.skipTest("psutil not available for memory benchmarking")


class TestWebInterfaceEndToEnd(EndToEndTestBase):
    """End-to-end tests for web interface (without browser automation)"""
    
    def setUp(self):
        """Set up test environment with web app"""
        super().setUp()
        
        # Start web app in a separate thread
        self.web_app_process = None
        self.web_app_port = 5555  # Use different port for testing
        
        # Update config for web app
        self.config.webapp.port = self.web_app_port
        self.config.webapp.host = "127.0.0.1"
        
    def tearDown(self):
        """Clean up web app"""
        if self.web_app_process:
            self.web_app_process.terminate()
            self.web_app_process.wait()
        super().tearDown()
    
    def test_web_interface_api_endpoints(self):
        """Test web interface API endpoints"""
        # Create test data
        post = self.db_manager.get_or_create_post(
            post_id="web_test",
            user_id="test_user",
            post_url="https://test.com/post",
            post_content="Web interface test post"
        )
        
        image_id = self.db_manager.save_image(
            post_id=post.id,
            image_url="https://test.com/image.jpg",
            local_path="/tmp/test_image.jpg",
            attachment_index=0,
            media_type="image/jpeg",
            image_post_id="web_test_media"
        )
        
        self.db_manager.update_image_caption(
            image_id=image_id,
            generated_caption="Web interface test caption",
            quality_metrics={
                "overall_score": 80,
                "quality_level": "good",
                "needs_review": False
            }
        )
        
        # Test database queries that web interface would use
        # (Since we can't easily start the actual web server in tests,
        # we test the underlying database operations)
        
        # Test getting pending images (main page)
        pending_images = self.db_manager.get_pending_images(limit=10)
        self.assertEqual(len(pending_images), 1)
        
        image = pending_images[0]
        self.assertEqual(image.generated_caption, "Web interface test caption")
        
        # Test review operation (review form submission)
        success = self.db_manager.review_image(
            image_id=image.id,
            reviewed_caption="Reviewed via web interface",
            status=ProcessingStatus.APPROVED,
            reviewer_notes="Approved through web interface"
        )
        self.assertTrue(success)
        
        # Test getting approved images (approved page)
        approved_images = self.db_manager.get_approved_images(limit=10)
        self.assertEqual(len(approved_images), 1)
        
        approved_image = approved_images[0]
        self.assertEqual(approved_image.reviewed_caption, "Reviewed via web interface")
        
        # Test statistics (dashboard)
        stats = self.db_manager.get_processing_stats()
        self.assertEqual(stats['approved'], 1)
        self.assertEqual(stats['pending_review'], 0)
    
    def test_user_authentication_workflow(self):
        """Test user authentication workflow"""
        # Test user creation with environment-based credentials
        test_web_password = os.getenv('TEST_WEB_PASSWORD', 'web_test_password_456')
        user = self.db_manager.create_user(
            username="webuser",
            email="web@test.com",
            password=test_web_password,
            role=UserRole.REVIEWER
        )
        self.assertIsNotNone(user)
        
        # Test user lookup (login)
        found_user = self.db_manager.get_user_by_username("webuser")
        self.assertIsNotNone(found_user)
        self.assertTrue(found_user.check_password(test_web_password))
        self.assertFalse(found_user.check_password("invalid_password"))
        
        # Test user permissions
        self.assertEqual(found_user.role, UserRole.REVIEWER)
        self.assertTrue(found_user.is_active)
        
        # Test user update (profile changes)
        success = self.db_manager.update_user(
            user_id=found_user.id,
            email="newemail@test.com",
            role=UserRole.ADMIN
        )
        self.assertTrue(success)
        
        # Verify update
        updated_user = self.db_manager.get_user_by_username("webuser")
        self.assertEqual(updated_user.email, "newemail@test.com")
        self.assertEqual(updated_user.role, UserRole.ADMIN)


if __name__ == "__main__":
    # Run tests with verbose output
    unittest.main(verbosity=2)
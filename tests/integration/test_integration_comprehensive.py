#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Comprehensive integration tests for Vedfolnir components.
"""
import unittest
import asyncio
import tempfile
import os
import sys
import json
import time
from unittest.mock import patch, MagicMock, AsyncMock, mock_open
from datetime import datetime, timedelta
import httpx

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database.core.database_manager import DatabaseManager
from models import Post, Image, ProcessingStatus, User, UserRole
from config import Config
from app.services.activitypub.components.activitypub_client import ActivityPubClient
from ollama_caption_generator import OllamaCaptionGenerator
from app.services.activitypub.posts.service import PostingService
from image_processor import ImageProcessor

class MockPixelfedAPI:
    """Mock Pixelfed API for testing"""
    
    def __init__(self):
        self.posts = {}
        self.media = {}
        self.users = {}
        self.request_count = 0
        self.rate_limit_triggered = False
        
    def add_mock_post(self, post_id: str, user_id: str, content: str, media_attachments: list = None):
        """Add a mock post to the API"""
        self.posts[post_id] = {
            "id": post_id,
            "account": {"id": user_id, "username": f"user_{user_id}"},
            "content": content,
            "media_attachments": media_attachments or [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "url": f"https://test.pixelfed.social/p/{post_id}"
        }
        
    def add_mock_media(self, media_id: str, url: str, alt_text: str = None):
        """Add mock media to the API"""
        self.media[media_id] = {
            "id": media_id,
            "type": "image",
            "url": url,
            "preview_url": url,
            "description": alt_text,
            "meta": {"original": {"width": 800, "height": 600}}
        }
    
    async def mock_request(self, method: str, url: str, **kwargs):
        """Mock HTTP request handler"""
        self.request_count += 1
        
        # Simulate rate limiting
        if self.rate_limit_triggered:
            response = MagicMock()
            response.status_code = 429
            response.headers = {"retry-after": "1"}
            response.json.return_value = {"error": "Rate limit exceeded"}
            return response
        
        # Parse URL to determine endpoint
        if "/api/v1/accounts/" in url and "/statuses" in url:
            # Get user posts
            user_id = url.split("/accounts/")[1].split("/")[0]
            user_posts = [post for post in self.posts.values() 
                         if post["account"]["id"] == user_id]
            
            response = MagicMock()
            response.status_code = 200
            response.json.return_value = user_posts
            return response
            
        elif "/api/v1/media/" in url and method == "PUT":
            # Update media alt text
            media_id = url.split("/media/")[1]
            if media_id in self.media:
                # Extract alt text from request data
                if "json" in kwargs:
                    alt_text = kwargs["json"].get("description", "")
                    self.media[media_id]["description"] = alt_text
                
                response = MagicMock()
                response.status_code = 200
                response.json.return_value = self.media[media_id]
                return response
        
        elif "/api/v1/accounts/lookup" in url:
            # Account lookup
            username = kwargs.get("params", {}).get("acct", "")
            user_id = username.replace("user_", "") if username.startswith("user_") else "1"
            
            response = MagicMock()
            response.status_code = 200
            response.json.return_value = {
                "id": user_id,
                "username": username,
                "display_name": f"Test User {user_id}",
                "url": f"https://test.pixelfed.social/users/{username}"
            }
            return response
        
        # Default response
        response = MagicMock()
        response.status_code = 404
        response.json.return_value = {"error": "Not found"}
        return response

class TestComponentIntegration(unittest.IsolatedAsyncioTestCase):
    """Test integration between different components"""
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix="MySQL database")
        self.temp_db.close()
        
        # Create test config
        self.config = Config()
        self.config.storage.database_url = f"mysql+pymysql://{self.temp_db.name}"
        
        # Initialize components
        self.db_manager = DatabaseManager(self.config)
        self.mock_api = MockPixelfedAPI()
        
        # Create mock components
        self.activitypub_client = ActivityPubClient(self.config.activitypub)
        self.ollama_generator = OllamaCaptionGenerator(self.config.ollama)
        self.posting_service = PostingService(self.config, self.db_manager)
        self.image_processor = ImageProcessor(self.config.storage)
        
        # Mock external dependencies
        self.activitypub_client.client = AsyncMock()
        self.activitypub_client.client.request = self.mock_api.mock_request
        
        self.ollama_generator.connection_validated = True
        self.ollama_generator._try_generate_caption = AsyncMock()
        
        # Set up test data
        self._setup_test_data()
    
    def tearDown(self):
        """Clean up test environment"""
        self.db_manager.close_session()
        os.unlink(self.temp_db.name)
    
    def _setup_test_data(self):
        """Set up test data in mock API and database"""
        # Add mock posts to API
        self.mock_api.add_mock_post(
            post_id="post_1",
            user_id="user_1",
            content="Test post with image",
            media_attachments=[{
                "id": "media_1",
                "type": "image",
                "url": "https://test.pixelfed.social/storage/media_1.jpg",
                "description": None  # No alt text
            }]
        )
        
        self.mock_api.add_mock_post(
            post_id="post_2", 
            user_id="user_1",
            content="Another test post",
            media_attachments=[{
                "id": "media_2",
                "type": "image", 
                "url": "https://test.pixelfed.social/storage/media_2.jpg",
                "description": "Existing alt text"  # Already has alt text
            }]
        )
        
        # Add corresponding media
        self.mock_api.add_mock_media("media_1", "https://test.pixelfed.social/storage/media_1.jpg")
        self.mock_api.add_mock_media("media_2", "https://test.pixelfed.social/storage/media_2.jpg", "Existing alt text")
    
    async def test_full_workflow_integration(self):
        """Test the complete workflow from fetching posts to updating alt text"""
        # Mock caption generation
        self.ollama_generator._try_generate_caption.return_value = (
            "A beautiful landscape photo",
            {"overall_score": 85, "quality_level": "good", "needs_review": False}
        )
        
        # Mock image download
        with patch('image_processor.ImageProcessor.download_image') as mock_download:
            mock_download.return_value = "/tmp/test_image.jpg"
            
            with patch('builtins.open', mock_open(read_data=b"fake_image_data")):
                with patch('base64.b64encode', return_value=b"encoded_data"):
                    # Step 1: Fetch user posts
                    posts_data = await self.activitypub_client.get_user_posts("user_1", limit=10)
                    self.assertEqual(len(posts_data), 2)
                    
                    # Step 2: Process posts and identify images without alt text
                    processed_posts = []
                    for post_data in posts_data:
                        # Create post in database
                        post = self.db_manager.get_or_create_post(
                            post_id=post_data["id"],
                            user_id=post_data["account"]["id"],
                            post_url=post_data["url"],
                            post_content=post_data["content"]
                        )
                        processed_posts.append(post)
                        
                        # Process media attachments
                        for i, media in enumerate(post_data["media_attachments"]):
                            if not media.get("description"):  # No alt text
                                # Save image to database
                                image_id = self.db_manager.save_image(
                                    post_id=post.id,
                                    image_url=media["url"],
                                    local_path=f"/tmp/{media['id']}.jpg",
                                    attachment_index=i,
                                    media_type="image/jpeg",
                                    image_post_id=media["id"]
                                )
                                
                                # Generate caption
                                caption_result = await self.ollama_generator.generate_caption(f"/tmp/{media['id']}.jpg")
                                self.assertIsNotNone(caption_result)
                                
                                caption, quality_metrics = caption_result
                                
                                # Update database with caption
                                self.db_manager.update_image_caption(
                                    image_id=image_id,
                                    generated_caption=caption,
                                    quality_metrics=quality_metrics
                                )
                    
                    # Step 3: Verify database state
                    stats = self.db_manager.get_processing_stats()
                    self.assertEqual(stats['total_posts'], 2)
                    self.assertEqual(stats['total_images'], 1)  # Only one image without alt text
                    self.assertEqual(stats['pending_review'], 1)
                    
                    # Step 4: Simulate review and approval
                    pending_images = self.db_manager.get_pending_images(limit=10)
                    self.assertEqual(len(pending_images), 1)
                    
                    image = pending_images[0]
                    self.assertEqual(image.generated_caption, "A beautiful landscape photo")
                    
                    # Approve the caption
                    self.db_manager.review_image(
                        image_id=image.id,
                        reviewed_caption="A beautiful landscape photo",
                        status=ProcessingStatus.APPROVED
                    )
                    
                    # Step 5: Update alt text via API
                    approved_images = self.db_manager.get_approved_images(limit=10)
                    self.assertEqual(len(approved_images), 1)
                    
                    approved_image = approved_images[0]
                    
                    # Mock the API update
                    update_response = await self.activitypub_client.client.request(
                        "PUT",
                        f"https://test.pixelfed.social/api/v1/media/{approved_image.image_post_id}",
                        json={"description": approved_image.final_caption}
                    )
                    
                    self.assertEqual(update_response.status_code, 200)
                    
                    # Mark as posted
                    self.db_manager.mark_image_posted(approved_image.id)
                    
                    # Step 6: Verify final state
                    final_stats = self.db_manager.get_processing_stats()
                    self.assertEqual(final_stats['posted'], 1)
                    self.assertEqual(final_stats['pending_review'], 0)
                    self.assertEqual(final_stats['approved'], 0)
    
    async def test_error_handling_integration(self):
        """Test error handling across components"""
        # Test API rate limiting
        self.mock_api.rate_limit_triggered = True
        
        with self.assertRaises(Exception):
            await self.activitypub_client.get_user_posts("user_1", limit=10)
        
        # Reset rate limiting
        self.mock_api.rate_limit_triggered = False
        
        # Test caption generation failure
        self.ollama_generator._try_generate_caption.return_value = None
        
        with patch('builtins.open', mock_open(read_data=b"fake_image_data")):
            with patch('base64.b64encode', return_value=b"encoded_data"):
                result = await self.ollama_generator.generate_caption("/tmp/test.jpg")
                self.assertIsNone(result)
        
        # Test database error handling
        with patch.object(self.db_manager, 'get_session') as mock_session:
            mock_session.side_effect = Exception("Database connection failed")
            
            with self.assertRaises(Exception):
                self.db_manager.get_processing_stats()
    
    async def test_concurrent_processing(self):
        """Test concurrent processing of multiple users"""
        # Add more test data
        for i in range(3, 6):  # Add users 3, 4, 5
            self.mock_api.add_mock_post(
                post_id=f"post_{i}",
                user_id=f"user_{i}",
                content=f"Test post {i}",
                media_attachments=[{
                    "id": f"media_{i}",
                    "type": "image",
                    "url": f"https://test.pixelfed.social/storage/media_{i}.jpg",
                    "description": None
                }]
            )
            self.mock_api.add_mock_media(f"media_{i}", f"https://test.pixelfed.social/storage/media_{i}.jpg")
        
        # Mock caption generation
        self.ollama_generator._try_generate_caption.return_value = (
            "Generated caption",
            {"overall_score": 80, "quality_level": "good", "needs_review": False}
        )
        
        async def process_user(user_id: str):
            """Process a single user"""
            posts_data = await self.activitypub_client.get_user_posts(user_id, limit=10)
            processed_count = 0
            
            for post_data in posts_data:
                post = self.db_manager.get_or_create_post(
                    post_id=post_data["id"],
                    user_id=post_data["account"]["id"],
                    post_url=post_data["url"],
                    post_content=post_data["content"]
                )
                
                for i, media in enumerate(post_data["media_attachments"]):
                    if not media.get("description"):
                        image_id = self.db_manager.save_image(
                            post_id=post.id,
                            image_url=media["url"],
                            local_path=f"/tmp/{media['id']}.jpg",
                            attachment_index=i,
                            media_type="image/jpeg",
                            image_post_id=media["id"]
                        )
                        processed_count += 1
            
            return processed_count
        
        # Process multiple users concurrently
        tasks = [process_user(f"user_{i}") for i in range(1, 6)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify results
        successful_results = [r for r in results if isinstance(r, int)]
        self.assertEqual(len(successful_results), 5)  # All users processed
        self.assertEqual(sum(successful_results), 5)  # Total images processed
        
        # Verify database state
        stats = self.db_manager.get_processing_stats()
        self.assertEqual(stats['total_posts'], 5)
        self.assertEqual(stats['total_images'], 5)
    
    async def test_data_consistency(self):
        """Test data consistency across components"""
        # Create a post with image
        post_data = {
            "id": "consistency_test",
            "account": {"id": "user_test", "username": "test_user"},
            "content": "Consistency test post",
            "url": "https://test.pixelfed.social/p/consistency_test",
            "media_attachments": [{
                "id": "media_test",
                "type": "image",
                "url": "https://test.pixelfed.social/storage/media_test.jpg",
                "description": None
            }]
        }
        
        # Add to mock API
        self.mock_api.posts["consistency_test"] = post_data
        self.mock_api.add_mock_media("media_test", "https://test.pixelfed.social/storage/media_test.jpg")
        
        # Process through the system
        post = self.db_manager.get_or_create_post(
            post_id=post_data["id"],
            user_id=post_data["account"]["id"],
            post_url=post_data["url"],
            post_content=post_data["content"]
        )
        
        media = post_data["media_attachments"][0]
        image_id = self.db_manager.save_image(
            post_id=post.id,
            image_url=media["url"],
            local_path=f"/tmp/{media['id']}.jpg",
            attachment_index=0,
            media_type="image/jpeg",
            image_post_id=media["id"]
        )
        
        # Verify data consistency
        # 1. Post exists in database
        session = self.db_manager.get_session()
        try:
            db_post = session.query(Post).filter_by(post_id="consistency_test").first()
            self.assertIsNotNone(db_post)
            self.assertEqual(db_post.user_id, "user_test")
            
            # 2. Image is linked to correct post
            db_image = session.query(Image).filter_by(id=image_id).first()
            self.assertIsNotNone(db_image)
            self.assertEqual(db_image.post_id, db_post.id)
            self.assertEqual(db_image.image_post_id, "media_test")
            
            # 3. No duplicate posts created
            duplicate_posts = session.query(Post).filter_by(post_id="consistency_test").all()
            self.assertEqual(len(duplicate_posts), 1)
            
            # 4. No duplicate images created
            duplicate_images = session.query(Image).filter_by(image_url=media["url"]).all()
            self.assertEqual(len(duplicate_images), 1)
            
        finally:
            session.close()

class TestDatabaseIntegration(unittest.TestCase):
    """Test database integration with various components"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix="MySQL database")
        self.temp_db.close()
        
        self.config = Config()
        self.config.storage.database_url = f"mysql+pymysql://{self.temp_db.name}"
        
        self.db_manager = DatabaseManager(self.config)
    
    def tearDown(self):
        """Clean up test environment"""
        self.db_manager.close_session()
        os.unlink(self.temp_db.name)
    
    def test_database_transaction_integrity(self):
        """Test database transaction integrity"""
        session = self.db_manager.get_session()
        
        try:
            # Start a transaction
            post = Post(
                post_id="transaction_test",
                user_id="test_user",
                post_url="https://test.com/post",
                post_content="Test content"
            )
            session.add(post)
            session.flush()  # Get the post ID
            
            # Add related image
            image = Image(
                post_id=post.id,
                image_url="https://test.com/image.jpg",
                local_path="/tmp/image.jpg",
                attachment_index=0,
                status=ProcessingStatus.PENDING
            )
            session.add(image)
            
            # Commit transaction
            session.commit()
            
            # Verify both records exist
            db_post = session.query(Post).filter_by(post_id="transaction_test").first()
            db_image = session.query(Image).filter_by(post_id=post.id).first()
            
            self.assertIsNotNone(db_post)
            self.assertIsNotNone(db_image)
            self.assertEqual(db_image.post_id, db_post.id)
            
        finally:
            session.close()
    
    def test_database_constraint_enforcement(self):
        """Test that database constraints are properly enforced"""
        session = self.db_manager.get_session()
        
        try:
            # Test unique constraint on post_id
            post1 = Post(
                post_id="unique_test",
                user_id="user1",
                post_url="https://test.com/post1",
                post_content="Content 1"
            )
            session.add(post1)
            session.commit()
            
            # Try to add duplicate post_id
            post2 = Post(
                post_id="unique_test",  # Same post_id
                user_id="user2",
                post_url="https://test.com/post2",
                post_content="Content 2"
            )
            session.add(post2)
            
            with self.assertRaises(Exception):  # Should raise integrity error
                session.commit()
                
        except Exception:
            session.rollback()
        finally:
            session.close()
    
    def test_database_relationship_integrity(self):
        """Test database relationship integrity"""
        # Create post and image with proper relationship
        post = self.db_manager.get_or_create_post(
            post_id="relationship_test",
            user_id="test_user",
            post_url="https://test.com/post",
            post_content="Test content"
        )
        
        image_id = self.db_manager.save_image(
            post_id=post.id,
            image_url="https://test.com/image.jpg",
            local_path="/tmp/image.jpg",
            attachment_index=0,
            media_type="image/jpeg",
            image_post_id="img_123"
        )
        
        # Verify relationship
        session = self.db_manager.get_session()
        try:
            db_image = session.query(Image).filter_by(id=image_id).first()
            db_post = session.query(Post).filter_by(id=db_image.post_id).first()
            
            self.assertIsNotNone(db_image)
            self.assertIsNotNone(db_post)
            self.assertEqual(db_post.post_id, "relationship_test")
            self.assertEqual(db_image.post_id, db_post.id)
            
        finally:
            session.close()
    
    def test_database_performance_with_large_dataset(self):
        """Test database performance with larger datasets"""
        start_time = time.time()
        
        # Create a larger dataset
        posts = []
        for i in range(100):
            post = self.db_manager.get_or_create_post(
                post_id=f"perf_test_{i}",
                user_id=f"user_{i % 10}",  # 10 different users
                post_url=f"https://test.com/post_{i}",
                post_content=f"Performance test post {i}"
            )
            posts.append(post)
            
            # Add 2 images per post
            for j in range(2):
                self.db_manager.save_image(
                    post_id=post.id,
                    image_url=f"https://test.com/image_{i}_{j}.jpg",
                    local_path=f"/tmp/image_{i}_{j}.jpg",
                    attachment_index=j,
                    media_type="image/jpeg",
                    image_post_id=f"img_{i}_{j}"
                )
        
        creation_time = time.time() - start_time
        
        # Test query performance
        start_time = time.time()
        stats = self.db_manager.get_processing_stats()
        query_time = time.time() - start_time
        
        # Verify data was created correctly
        self.assertEqual(stats['total_posts'], 100)
        self.assertEqual(stats['total_images'], 200)
        
        # Performance should be reasonable
        self.assertLess(creation_time, 10.0)  # Creation should take less than 10 seconds
        self.assertLess(query_time, 1.0)      # Query should take less than 1 second
    
    def test_user_management_integration(self):
        """Test user management integration with database"""
        # Create test user with secure test credentials
        test_password = os.getenv('TEST_USER_PASSWORD', 'secure_test_password_123!')
        user = self.db_manager.create_user(
            username="integration_test",
            email="test@test.com",
            password=test_password,
            role=UserRole.REVIEWER
        )
        
        self.assertIsNotNone(user)
        self.assertEqual(user.username, "integration_test")
        self.assertEqual(user.role, UserRole.REVIEWER)
        
        # Test user lookup
        found_user = self.db_manager.get_user_by_username("integration_test")
        self.assertIsNotNone(found_user)
        self.assertEqual(found_user.id, user.id)
        
        # Test user update
        success = self.db_manager.update_user(
            user_id=user.id,
            role=UserRole.ADMIN,
            is_active=False
        )
        self.assertTrue(success)
        
        # Verify update
        updated_user = self.db_manager.get_user_by_username("integration_test")
        self.assertEqual(updated_user.role, UserRole.ADMIN)
        self.assertFalse(updated_user.is_active)
        
        # Test user deletion
        success = self.db_manager.delete_user(user.id)
        self.assertTrue(success)
        
        # Verify deletion
        deleted_user = self.db_manager.get_user_by_username("integration_test")
        self.assertIsNone(deleted_user)

if __name__ == "__main__":
    unittest.main()
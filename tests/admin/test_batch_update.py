# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
import unittest
import asyncio
import os
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

from config import Config, BatchUpdateConfig
from app.services.batch.components.batch_update_service import BatchUpdateService
from models import Post, Image, ProcessingStatus

class TestBatchUpdateService(unittest.TestCase):
    """Test the batch update service functionality"""
    
    def setUp(self):
        """Set up test environment"""
        # Create a test config
        self.config = Config()
        self.config.batch_update = BatchUpdateConfig(
            enabled=True,
            batch_size=3,
            max_concurrent_batches=2,
            verification_delay=0,  # No delay for tests
            rollback_on_failure=True
        )
        
        # Create the service with mocked database
        self.db_mock = MagicMock()
        self.service = BatchUpdateService(self.config)
        self.service.db = self.db_mock
        
        # Create test data
        self.create_test_data()
    
    def create_test_data(self):
        """Create test data for the tests"""
        # Create test posts
        self.post1 = MagicMock(spec=Post)
        self.post1.id = 1
        self.post1.post_id = "post1"
        
        self.post2 = MagicMock(spec=Post)
        self.post2.id = 2
        self.post2.post_id = "post2"
        
        # Create test images
        self.image1 = MagicMock(spec=Image)
        self.image1.id = 1
        self.image1.post = self.post1
        self.image1.image_post_id = "media1"
        self.image1.attachment_index = 0
        self.image1.final_caption = "Test caption 1"
        self.image1.reviewed_caption = "Test caption 1"
        self.image1.original_caption = None
        
        self.image2 = MagicMock(spec=Image)
        self.image2.id = 2
        self.image2.post = self.post1
        self.image2.image_post_id = "media2"
        self.image2.attachment_index = 1
        self.image2.final_caption = "Test caption 2"
        self.image2.reviewed_caption = "Test caption 2"
        self.image2.original_caption = "Original caption 2"
        
        self.image3 = MagicMock(spec=Image)
        self.image3.id = 3
        self.image3.post = self.post2
        self.image3.image_post_id = None  # No direct media ID
        self.image3.attachment_index = 0
        self.image3.final_caption = "Test caption 3"
        self.image3.reviewed_caption = "Test caption 3"
        self.image3.original_caption = None
        
        self.image4 = MagicMock(spec=Image)
        self.image4.id = 4
        self.image4.post = self.post2
        self.image4.image_post_id = None  # No direct media ID
        self.image4.attachment_index = 1
        self.image4.final_caption = "Test caption 4"
        self.image4.reviewed_caption = "Test caption 4"
        self.image4.original_caption = None
        
        # Set up approved images
        self.approved_images = [self.image1, self.image2, self.image3, self.image4]
        
        # Set up post attachments
        self.post1_attachments = [
            {"url": "http://example.com/image1.jpg", "name": ""},
            {"url": "http://example.com/image2.jpg", "name": "Original caption 2"}
        ]
        
        self.post2_attachments = [
            {"url": "http://example.com/image3.jpg", "name": ""},
            {"url": "http://example.com/image4.jpg", "name": ""}
        ]
    
    @patch('app.services.batch.components.batch_update_service.ActivityPubClient')
    def test_batch_update_captions(self, mock_client_class):
        """Test batch updating captions"""
        # Set up the database mock
        self.db_mock.get_approved_images.return_value = self.approved_images
        
        # Set up the client mock
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        # Mock get_post_by_id to return different posts
        async def mock_get_post_by_id(post_id):
            if post_id == "post1":
                return {"id": "post1", "attachment": self.post1_attachments}
            elif post_id == "post2":
                return {"id": "post2", "attachment": self.post2_attachments}
            return None
        
        mock_client.get_post_by_id.side_effect = mock_get_post_by_id
        
        # Mock update_media_caption to succeed
        mock_client.update_media_caption.return_value = True
        
        # Mock update_post to succeed
        mock_client.update_post.return_value = True
        
        # Run the batch update
        result = asyncio.run(self.service.batch_update_captions())
        
        # Verify the results
        self.assertEqual(result['processed'], 4)
        self.assertEqual(result['successful'], 2)  # Only direct media updates are counted as successful
        self.assertEqual(result['failed'], 2)  # Post updates are not counted as successful
        self.assertEqual(result['verified'], 4)  # All are verified
        self.assertEqual(result['rollbacks'], 0)
        
        # Verify the API calls
        # Should have 2 direct media updates for image1 and image2
        self.assertEqual(mock_client.update_media_caption.call_count, 2)
        
        # Should have 1 post update for post2 (images 3 and 4)
        self.assertEqual(mock_client.update_post.call_count, 1)
        
        # Verify the database was updated
        self.assertEqual(self.db_mock.mark_image_posted.call_count, 4)
    
    @patch('app.services.batch.components.batch_update_service.ActivityPubClient')
    def test_batch_update_with_failures(self, mock_client_class):
        """Test batch updating with some failures"""
        # Set up the database mock
        self.db_mock.get_approved_images.return_value = self.approved_images
        
        # Set up the client mock
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        # Mock get_post_by_id to return different posts
        async def mock_get_post_by_id(post_id):
            if post_id == "post1":
                return {"id": "post1", "attachment": self.post1_attachments}
            elif post_id == "post2":
                return {"id": "post2", "attachment": self.post2_attachments}
            return None
        
        mock_client.get_post_by_id.side_effect = mock_get_post_by_id
        
        # Mock update_media_caption to fail for image2
        async def mock_update_media_caption(image_post_id, caption):
            return image_post_id != "media2"
        
        mock_client.update_media_caption.side_effect = mock_update_media_caption
        
        # Mock update_post to succeed
        mock_client.update_post.return_value = True
        
        # Run the batch update
        result = asyncio.run(self.service.batch_update_captions())
        
        # Verify the results
        self.assertEqual(result['processed'], 4)
        self.assertEqual(result['successful'], 1)  # Only image1 succeeded
        self.assertEqual(result['failed'], 3)  # image2 failed, image3 and image4 are not counted as successful
        
        # Verify the API calls
        self.assertEqual(mock_client.update_media_caption.call_count, 2)
        self.assertEqual(mock_client.update_post.call_count, 1)
        
        # Verify the database was updated for successful images only
        self.assertEqual(self.db_mock.mark_image_posted.call_count, 3)
    
    @patch('app.services.batch.components.batch_update_service.ActivityPubClient')
    def test_verification_and_rollback(self, mock_client_class):
        """Test verification and rollback functionality"""
        # Set up the database mock
        self.db_mock.get_approved_images.return_value = [self.image3, self.image4]
        
        # Set up the client mock
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        # Override the _verify_updates method to simulate verification failure
        async def mock_verify_updates(ap_client, post_id, updated_images):
            return {
                'verified': 0,
                'failed': len(updated_images),
                'verified_ids': []
            }
        
        # Apply the mock to the service instance
        self.service._verify_updates = mock_verify_updates
        
        # Mock get_post_by_id to return post2
        async def mock_get_post_by_id(post_id):
            if post_id == "post2":
                return {"id": "post2", "attachment": self.post2_attachments}
            return None
        
        mock_client.get_post_by_id.side_effect = mock_get_post_by_id
        
        # Mock update_post to succeed
        mock_client.update_post.return_value = True
        
        # Run the batch update
        result = asyncio.run(self.service.batch_update_captions())
        
        # Verify the results
        self.assertEqual(result['processed'], 2)
        self.assertEqual(result['successful'], 0)  # All failed verification
        self.assertEqual(result['failed'], 2)
        self.assertEqual(result['verified'], 0)
        self.assertEqual(result['rollbacks'], 1)  # One rollback for the post
        
        # Verify the API calls
        self.assertEqual(mock_client.update_post.call_count, 2)  # Original update + rollback
        
        # Verify no images were marked as posted
        self.db_mock.mark_image_posted.assert_not_called()

if __name__ == '__main__':
    unittest.main()
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Tests for caption review integration system
"""

import unittest
from unittest.mock import Mock, patch, AsyncMock
import uuid
from datetime import datetime, timezone

from caption_review_integration import CaptionReviewIntegration
from models import (
    CaptionGenerationTask, TaskStatus, Post, Image, 
    GenerationResults, User, PlatformConnection
)
from database import DatabaseManager

class TestCaptionReviewIntegration(unittest.TestCase):
    """Tests for caption review integration system"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_db_manager = Mock(spec=DatabaseManager)
        self.mock_session = Mock()
        self.mock_db_manager.get_session.return_value = self.mock_session
        
        self.review_integration = CaptionReviewIntegration(self.mock_db_manager)
        
        # Test data
        self.test_task_id = str(uuid.uuid4())
        self.test_user_id = 1
        self.test_platform_id = 1
        self.test_batch_id = str(uuid.uuid4())
        
        # Mock task
        self.mock_task = Mock(spec=CaptionGenerationTask)
        self.mock_task.id = self.test_task_id
        self.mock_task.user_id = self.test_user_id
        self.mock_task.platform_connection_id = self.test_platform_id
        self.mock_task.status = TaskStatus.COMPLETED
        self.mock_task.completed_at = datetime.now(timezone.utc)
    
    def test_create_review_batch_from_task(self):
        """Test creating review batch from completed task"""
        # Mock generated images
        mock_images = []
        for i in range(3):
            mock_image = Mock(spec=Image)
            mock_image.id = i + 1
            mock_image.generated_caption = f"Generated caption {i}"
            mock_image.needs_review = True
            mock_image.generation_task_id = self.test_task_id
            mock_images.append(mock_image)
        
        query_mock = self.mock_session.query.return_value
        query_mock.filter_by.return_value.all.return_value = mock_images
        
        batch_id = self.review_integration.create_review_batch_from_task(self.test_task_id)
        
        # Verify batch creation
        self.assertIsNotNone(batch_id)
        self.mock_session.add.assert_called()
        self.mock_session.commit.assert_called()
        
        # Verify images were updated with batch ID
        for image in mock_images:
            self.assertEqual(image.review_batch_id, batch_id)
    
    def test_get_review_batches_for_user(self):
        """Test getting review batches for user"""
        # Mock review batches
        mock_batches = []
        for i in range(2):
            mock_batch = Mock()
            mock_batch.id = f"batch-{i}"
            mock_batch.user_id = self.test_user_id
            mock_batch.platform_connection_id = self.test_platform_id
            mock_batch.created_at = datetime.now(timezone.utc)
            mock_batch.total_images = 5 + i
            mock_batch.reviewed_images = i * 2
            mock_batch.approved_images = i
            mock_batches.append(mock_batch)
        
        query_mock = self.mock_session.query.return_value
        query_mock.filter_by.return_value.order_by.return_value.all.return_value = mock_batches
        
        batches = self.review_integration.get_review_batches_for_user(
            self.test_user_id, self.test_platform_id
        )
        
        # Verify batch data
        self.assertEqual(len(batches), 2)
        for i, batch in enumerate(batches):
            self.assertEqual(batch['batch_id'], f"batch-{i}")
            self.assertEqual(batch['total_images'], 5 + i)
            self.assertEqual(batch['reviewed_images'], i * 2)
    
    def test_get_batch_images_for_review(self):
        """Test getting batch images for review"""
        # Mock batch images
        mock_images = []
        for i in range(3):
            mock_image = Mock(spec=Image)
            mock_image.id = i + 1
            mock_image.generated_caption = f"Generated caption {i}"
            mock_image.approved_caption = None
            mock_image.needs_review = True
            mock_image.review_status = "pending"
            
            # Mock post relationship
            mock_post = Mock(spec=Post)
            mock_post.id = f"post-{i}"
            mock_post.url = f"https://example.com/post/{i}"
            mock_image.post = mock_post
            
            mock_images.append(mock_image)
        
        query_mock = self.mock_session.query.return_value
        query_mock.filter_by.return_value.options.return_value.all.return_value = mock_images
        
        images = self.review_integration.get_batch_images_for_review(self.test_batch_id)
        
        # Verify image data
        self.assertEqual(len(images), 3)
        for i, image in enumerate(images):
            self.assertEqual(image['image_id'], i + 1)
            self.assertEqual(image['generated_caption'], f"Generated caption {i}")
            self.assertEqual(image['post_url'], f"https://example.com/post/{i}")
            self.assertTrue(image['needs_review'])
    
    def test_update_image_review_status(self):
        """Test updating image review status"""
        # Mock image
        mock_image = Mock(spec=Image)
        mock_image.id = 1
        mock_image.generated_caption = "Original caption"
        mock_image.needs_review = True
        
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = mock_image
        
        # Update review status
        result = self.review_integration.update_image_review_status(
            image_id=1,
            user_id=self.test_user_id,
            approved=True,
            edited_caption="Edited caption",
            review_notes="Looks good"
        )
        
        # Verify update
        self.assertTrue(result)
        self.assertEqual(mock_image.approved_caption, "Edited caption")
        self.assertEqual(mock_image.review_status, "approved")
        self.assertEqual(mock_image.review_notes, "Looks good")
        self.assertFalse(mock_image.needs_review)
        self.mock_session.commit.assert_called_once()
    
    def test_bulk_approve_images(self):
        """Test bulk approval of images"""
        # Mock images
        image_ids = [1, 2, 3]
        mock_images = []
        for image_id in image_ids:
            mock_image = Mock(spec=Image)
            mock_image.id = image_id
            mock_image.needs_review = True
            mock_images.append(mock_image)
        
        self.mock_session.query.return_value.filter.return_value.all.return_value = mock_images
        
        # Bulk approve
        result = self.review_integration.bulk_approve_images(
            image_ids, self.test_user_id
        )
        
        # Verify bulk approval
        self.assertEqual(result, 3)
        for image in mock_images:
            self.assertEqual(image.review_status, "approved")
            self.assertFalse(image.needs_review)
        self.mock_session.commit.assert_called_once()
    
    def test_bulk_reject_images(self):
        """Test bulk rejection of images"""
        # Mock images
        image_ids = [1, 2, 3]
        mock_images = []
        for image_id in image_ids:
            mock_image = Mock(spec=Image)
            mock_image.id = image_id
            mock_image.needs_review = True
            mock_images.append(mock_image)
        
        self.mock_session.query.return_value.filter.return_value.all.return_value = mock_images
        
        # Bulk reject
        result = self.review_integration.bulk_reject_images(
            image_ids, self.test_user_id, "Not suitable"
        )
        
        # Verify bulk rejection
        self.assertEqual(result, 3)
        for image in mock_images:
            self.assertEqual(image.review_status, "rejected")
            self.assertEqual(image.review_notes, "Not suitable")
            self.assertFalse(image.needs_review)
        self.mock_session.commit.assert_called_once()
    
    def test_get_batch_statistics(self):
        """Test getting batch statistics"""
        # Mock batch with statistics
        mock_batch = Mock()
        mock_batch.id = self.test_batch_id
        mock_batch.total_images = 10
        mock_batch.reviewed_images = 7
        mock_batch.approved_images = 5
        mock_batch.rejected_images = 2
        mock_batch.created_at = datetime.now(timezone.utc)
        
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = mock_batch
        
        stats = self.review_integration.get_batch_statistics(self.test_batch_id)
        
        # Verify statistics
        self.assertEqual(stats['total_images'], 10)
        self.assertEqual(stats['reviewed_images'], 7)
        self.assertEqual(stats['approved_images'], 5)
        self.assertEqual(stats['rejected_images'], 2)
        self.assertEqual(stats['pending_images'], 3)
        self.assertEqual(stats['completion_percentage'], 70.0)
    
    def test_finalize_batch_review(self):
        """Test finalizing batch review"""
        # Mock batch with all images reviewed
        mock_batch = Mock()
        mock_batch.id = self.test_batch_id
        mock_batch.is_completed = False
        
        # Mock approved images
        mock_approved_images = []
        for i in range(3):
            mock_image = Mock(spec=Image)
            mock_image.id = i + 1
            mock_image.approved_caption = f"Approved caption {i}"
            mock_image.review_status = "approved"
            
            # Mock post relationship
            mock_post = Mock(spec=Post)
            mock_post.id = f"post-{i}"
            mock_image.post = mock_post
            
            mock_approved_images.append(mock_image)
        
        query_mock = self.mock_session.query.return_value
        query_mock.filter_by.return_value.first.return_value = mock_batch
        query_mock.filter.return_value.options.return_value.all.return_value = mock_approved_images
        
        # Mock platform update service
        with patch('caption_review_integration.PlatformUpdateService') as mock_update_service:
            mock_service_instance = Mock()
            mock_update_service.return_value = mock_service_instance
            mock_service_instance.update_post_captions = AsyncMock(return_value=True)
            
            result = asyncio.run(self.review_integration.finalize_batch_review(
                self.test_batch_id, self.test_user_id
            ))
        
        # Verify finalization
        self.assertTrue(result)
        self.assertTrue(mock_batch.is_completed)
        self.assertIsNotNone(mock_batch.completed_at)
        mock_service_instance.update_post_captions.assert_called_once()
    
    def test_get_review_history(self):
        """Test getting review history for user"""
        # Mock completed batches
        mock_batches = []
        for i in range(2):
            mock_batch = Mock()
            mock_batch.id = f"batch-{i}"
            mock_batch.created_at = datetime.now(timezone.utc)
            mock_batch.completed_at = datetime.now(timezone.utc)
            mock_batch.total_images = 5 + i
            mock_batch.approved_images = 3 + i
            mock_batch.rejected_images = 2 - i
            mock_batches.append(mock_batch)
        
        query_mock = self.mock_session.query.return_value
        query_mock.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_batches
        
        history = self.review_integration.get_review_history(
            self.test_user_id, self.test_platform_id, limit=10
        )
        
        # Verify history
        self.assertEqual(len(history), 2)
        for i, batch in enumerate(history):
            self.assertEqual(batch['batch_id'], f"batch-{i}")
            self.assertEqual(batch['total_images'], 5 + i)
            self.assertEqual(batch['approved_images'], 3 + i)
    
    def test_search_and_filter_images(self):
        """Test searching and filtering images in batch"""
        # Mock filtered images
        mock_images = []
        for i in range(2):
            mock_image = Mock(spec=Image)
            mock_image.id = i + 1
            mock_image.generated_caption = f"Caption with keyword {i}"
            mock_image.review_status = "pending"
            mock_images.append(mock_image)
        
        query_mock = self.mock_session.query.return_value
        query_mock.filter.return_value.all.return_value = mock_images
        
        # Search with filters
        results = self.review_integration.search_and_filter_images(
            batch_id=self.test_batch_id,
            search_term="keyword",
            status_filter="pending",
            limit=10
        )
        
        # Verify search results
        self.assertEqual(len(results), 2)
        for i, image in enumerate(results):
            self.assertEqual(image['image_id'], i + 1)
            self.assertIn("keyword", image['generated_caption'])
    
    def test_export_batch_data(self):
        """Test exporting batch data"""
        # Mock batch data
        mock_batch = Mock()
        mock_batch.id = self.test_batch_id
        mock_batch.created_at = datetime.now(timezone.utc)
        
        mock_images = []
        for i in range(3):
            mock_image = Mock(spec=Image)
            mock_image.id = i + 1
            mock_image.generated_caption = f"Generated {i}"
            mock_image.approved_caption = f"Approved {i}"
            mock_image.review_status = "approved"
            
            mock_post = Mock(spec=Post)
            mock_post.url = f"https://example.com/post/{i}"
            mock_image.post = mock_post
            
            mock_images.append(mock_image)
        
        query_mock = self.mock_session.query.return_value
        query_mock.filter_by.return_value.first.return_value = mock_batch
        query_mock.filter_by.return_value.options.return_value.all.return_value = mock_images
        
        export_data = self.review_integration.export_batch_data(self.test_batch_id)
        
        # Verify export data
        self.assertIn('batch_info', export_data)
        self.assertIn('images', export_data)
        self.assertEqual(len(export_data['images']), 3)
        
        for i, image in enumerate(export_data['images']):
            self.assertEqual(image['generated_caption'], f"Generated {i}")
            self.assertEqual(image['approved_caption'], f"Approved {i}")

# Import asyncio for async test
import asyncio

if __name__ == '__main__':
    unittest.main()
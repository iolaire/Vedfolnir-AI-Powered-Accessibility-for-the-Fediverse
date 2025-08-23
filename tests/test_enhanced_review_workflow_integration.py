# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integration Tests for Enhanced Review Workflow

Tests the enhanced review workflow integration including:
- Automatic redirection to review interface after job completion
- Job-specific caption identification in review interface
- Bulk review tools for large caption generation batches
- Caption regeneration queue for individual image re-processing
- Job result quality metrics and improvement suggestions
- Approval rate tracking and feedback for job optimization
"""

import unittest
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from config import Config
from database import DatabaseManager
from models import (
    User, UserRole, PlatformConnection, CaptionGenerationTask, TaskStatus,
    Image, ProcessingStatus, GenerationResults
)
from web_caption_generation_service import WebCaptionGenerationService
from caption_review_integration import CaptionReviewIntegration
from tests.test_helpers import create_test_user_with_platforms, cleanup_test_user


class TestEnhancedReviewWorkflowIntegration(unittest.TestCase):
    """Test enhanced review workflow integration functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        
        # Create test user with platforms
        import uuid
        unique_username = f"test_reviewer_{uuid.uuid4().hex[:8]}"
        self.test_user, self.user_helper = create_test_user_with_platforms(
            self.db_manager, username=unique_username, role=UserRole.REVIEWER
        )
        
        # Create services
        self.web_caption_service = WebCaptionGenerationService(self.db_manager)
        self.review_integration = CaptionReviewIntegration(self.db_manager)
        
        # Create test data
        self._create_test_data()
    
    def tearDown(self):
        """Clean up test environment"""
        cleanup_test_user(self.user_helper)
    
    def _create_test_data(self):
        """Create test data for integration tests"""
        with self.db_manager.get_session() as session:
            # Create a test post first
            from models import Post
            test_post = Post(
                post_id="test_post_123",
                user_id="test_user_123",
                post_url="https://example.com/posts/test_post_123",
                platform_connection_id=self.test_user.platform_connections[0].id,
                post_content="Test post content"
            )
            session.add(test_post)
            session.flush()  # Get the post ID
            
            # Create test images
            self.test_images = []
            for i in range(1, 6):
                image = Image(
                    post_id=test_post.id,
                    image_url=f"https://example.com/image{i}.jpg",
                    local_path=f"storage/images/image{i}.jpg",
                    generated_caption=f"Generated caption for image {i}",
                    caption_quality_score=min(60 + (i * 10), 100),  # Scores: 70, 80, 90, 100, 100 (capped at 100)
                    status=ProcessingStatus.PENDING,
                    platform_connection_id=self.test_user.platform_connections[0].id,
                    needs_special_review=(i == 1),  # First image needs special review
                    attachment_index=i - 1  # 0-based index
                )
                self.test_images.append(image)
                session.add(image)
            
            session.flush()  # Get the image IDs
            
            # Create completed task with results
            self.test_task = CaptionGenerationTask(
                user_id=self.test_user.id,
                platform_connection_id=self.test_user.platform_connections[0].id,
                status=TaskStatus.COMPLETED,
                completed_at=datetime.now(timezone.utc)
            )
            
            # Create generation results
            image_ids = [img.id for img in self.test_images]
            results = GenerationResults(
                task_id=self.test_task.id,  # Use the actual task object here before commit
                captions_generated=5,
                images_processed=5,
                processing_time_seconds=120.5,
                generated_image_ids=image_ids
            )
            self.test_task.results = results
            
            session.add(self.test_task)
            session.commit()
            
            # Store task ID and image IDs for later use (avoid detached instance issues)
            self.test_task_id = self.test_task.id
            self.test_image_ids = [img.id for img in self.test_images]
    
    def test_job_completion_redirect_integration(self):
        """Test automatic redirection to review interface after job completion"""
        # Test redirect info storage
        batch_info = {
            'batch_id': self.test_task_id,
            'total_images': 5,
            'task_id': self.test_task_id
        }
        
        self.web_caption_service._store_review_redirect_info(
            self.test_user.id, 
            self.test_task_id, 
            batch_info
        )
        
        # Test redirect info retrieval
        redirect_info = self.web_caption_service.get_review_redirect_info(
            self.test_user.id, 
            self.test_task_id
        )
        
        self.assertIsNotNone(redirect_info)
        self.assertEqual(redirect_info['task_id'], self.test_task_id)
        self.assertEqual(redirect_info['batch_id'], self.test_task_id)
        self.assertEqual(redirect_info['total_images'], 5)
        self.assertIn('/review/batch/', redirect_info['redirect_url'])
    
    def test_review_batch_creation_from_task(self):
        """Test creating review batch from completed caption generation task"""
        batch_info = self.review_integration.create_review_batch_from_task(
            self.test_task_id, 
            self.test_user.id
        )
        
        self.assertIsNotNone(batch_info)
        self.assertEqual(batch_info['batch_id'], self.test_task_id)
        self.assertEqual(batch_info['task_id'], self.test_task_id)
        self.assertEqual(batch_info['total_images'], 5)
        self.assertEqual(batch_info['user_id'], self.test_user.id)
        self.assertEqual(len(batch_info['images']), 5)
        
        # Verify image data structure
        first_image = batch_info['images'][0]
        self.assertIn('id', first_image)
        self.assertIn('generated_caption', first_image)
        self.assertIn('status', first_image)
        self.assertIn('caption_quality_score', first_image)
    
    def test_job_specific_caption_identification(self):
        """Test job-specific caption identification in review interface"""
        # Get batch images
        batch_data = self.review_integration.get_batch_images(
            self.test_task_id,
            self.test_user.id,
            page=1,
            per_page=10
        )
        
        self.assertEqual(len(batch_data['images']), 5)
        self.assertEqual(batch_data['total'], 5)
        self.assertEqual(batch_data['batch_info']['batch_id'], self.test_task_id)
        
        # Verify each image is properly identified with the batch
        for image_data in batch_data['images']:
            self.assertIn('id', image_data)
            self.assertIn('generated_caption', image_data)
            self.assertEqual(image_data['status'], 'pending')
    
    def test_bulk_review_tools(self):
        """Test bulk review tools optimized for large caption generation batches"""
        # Test bulk approve
        approve_result = self.review_integration.bulk_approve_batch(
            self.test_task_id,
            self.test_user.id,
            image_ids=self.test_image_ids[:3],  # First 3 images
            reviewer_notes="Bulk approved for testing"
        )
        
        self.assertTrue(approve_result['success'])
        self.assertEqual(approve_result['approved_count'], 3)
        
        # Verify images were approved
        with self.db_manager.get_session() as session:
            approved_images = session.query(Image).filter(
                Image.id.in_(self.test_image_ids[:3]),
                Image.status == ProcessingStatus.APPROVED
            ).count()
            self.assertEqual(approved_images, 3)
        
        # Test bulk reject
        reject_result = self.review_integration.bulk_reject_batch(
            self.test_task_id,
            self.test_user.id,
            image_ids=self.test_image_ids[3:],  # Last 2 images
            reviewer_notes="Bulk rejected for testing"
        )
        
        self.assertTrue(reject_result['success'])
        self.assertEqual(reject_result['rejected_count'], 2)
        
        # Verify images were rejected
        with self.db_manager.get_session() as session:
            rejected_images = session.query(Image).filter(
                Image.id.in_(self.test_image_ids[3:]),
                Image.status == ProcessingStatus.REJECTED
            ).count()
            self.assertEqual(rejected_images, 2)
    
    def test_caption_regeneration_queue(self):
        """Test caption regeneration queue for individual image re-processing"""
        # Queue images for regeneration
        result = self.review_integration.queue_caption_regeneration(
            image_ids=self.test_image_ids[:2],  # First 2 images
            user_id=self.test_user.id,
            reason="Testing regeneration queue"
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['queued_count'], 2)
        self.assertEqual(result['image_ids'], self.test_image_ids[:2])
        
        # Verify images were reset for regeneration
        with self.db_manager.get_session() as session:
            regenerated_images = session.query(Image).filter(
                Image.id.in_(self.test_image_ids[:2])
            ).all()
            
            for image in regenerated_images:
                self.assertEqual(image.status, ProcessingStatus.PENDING)
                self.assertIsNone(image.generated_caption)
                self.assertIsNone(image.reviewed_caption)
                self.assertIsNone(image.final_caption)
                self.assertIsNone(image.caption_quality_score)
                self.assertFalse(image.needs_special_review)
                self.assertIn("Testing regeneration queue", image.reviewer_notes)
    
    def test_job_quality_metrics(self):
        """Test job result quality metrics and improvement suggestions"""
        quality_metrics = self.review_integration.get_job_quality_metrics(
            self.test_task_id,
            self.test_user.id
        )
        
        self.assertIsNotNone(quality_metrics)
        self.assertEqual(quality_metrics['batch_id'], self.test_task_id)
        self.assertEqual(quality_metrics['total_images'], 5)
        
        # Check quality metrics structure
        metrics = quality_metrics['quality_metrics']
        self.assertIn('average_quality', metrics)
        self.assertIn('min_quality', metrics)
        self.assertIn('max_quality', metrics)
        self.assertIn('quality_distribution', metrics)
        
        # Check quality distribution
        distribution = metrics['quality_distribution']
        self.assertIn('excellent', distribution)
        self.assertIn('good', distribution)
        self.assertIn('fair', distribution)
        self.assertIn('poor', distribution)
        
        # Check improvement suggestions
        self.assertIn('improvement_suggestions', quality_metrics)
        self.assertIsInstance(quality_metrics['improvement_suggestions'], list)
        
        # Check special review count
        self.assertEqual(quality_metrics['special_review_count'], 1)
    
    def test_approval_rate_tracking(self):
        """Test approval rate tracking and feedback for job optimization"""
        # First, approve and reject some images to create tracking data
        with self.db_manager.get_session() as session:
            # Approve first 3 images
            session.query(Image).filter(Image.id.in_(self.test_image_ids[:3])).update({
                'status': ProcessingStatus.APPROVED,
                'reviewed_at': datetime.now(timezone.utc)
            }, synchronize_session=False)
            
            # Reject last 2 images
            session.query(Image).filter(Image.id.in_(self.test_image_ids[3:])).update({
                'status': ProcessingStatus.REJECTED,
                'reviewed_at': datetime.now(timezone.utc)
            }, synchronize_session=False)
            
            session.commit()
        
        # Get approval rate tracking
        tracking_data = self.review_integration.get_approval_rate_tracking(
            self.test_user.id,
            days_back=30
        )
        
        self.assertEqual(tracking_data['total_batches'], 1)
        self.assertEqual(tracking_data['total_images'], 5)
        
        # Check approval rates
        approval_rates = tracking_data['approval_rates']
        self.assertEqual(approval_rates['approved_percent'], 60.0)  # 3/5 = 60%
        self.assertEqual(approval_rates['rejected_percent'], 40.0)  # 2/5 = 40%
        self.assertEqual(approval_rates['pending_percent'], 0.0)    # 0/5 = 0%
        self.assertEqual(approval_rates['reviewed_percent'], 100.0) # 5/5 = 100%
        
        # Check status counts
        status_counts = tracking_data['status_counts']
        self.assertEqual(status_counts['approved'], 3)
        self.assertEqual(status_counts['rejected'], 2)
        self.assertEqual(status_counts['pending'], 0)
        
        # Check recommendations
        self.assertIn('recommendations', tracking_data)
        self.assertIsInstance(tracking_data['recommendations'], list)
    
    def test_batch_statistics(self):
        """Test batch statistics functionality"""
        # First, set some images to different statuses
        with self.db_manager.get_session() as session:
            session.query(Image).filter(Image.id.in_(self.test_image_ids[:2])).update({
                'status': ProcessingStatus.APPROVED
            }, synchronize_session=False)
            
            session.query(Image).filter(Image.id == self.test_image_ids[2]).update({
                'status': ProcessingStatus.REJECTED
            }, synchronize_session=False)
            
            session.commit()
        
        # Get batch statistics
        batch_stats = self.review_integration.get_batch_statistics(
            self.test_task_id,
            self.test_user.id
        )
        
        self.assertIsNotNone(batch_stats)
        self.assertEqual(batch_stats['batch_id'], self.test_task_id)
        self.assertEqual(batch_stats['total_images'], 5)
        
        # Check status counts
        status_counts = batch_stats['status_counts']
        self.assertEqual(status_counts['approved'], 2)
        self.assertEqual(status_counts['rejected'], 1)
        self.assertEqual(status_counts['pending'], 2)
        
        # Check quality metrics
        self.assertGreater(batch_stats['average_quality_score'], 0)
        self.assertEqual(batch_stats['special_review_count'], 1)
        self.assertEqual(batch_stats['generation_time'], 120.5)
    
    def test_update_batch_image_caption(self):
        """Test updating caption for individual image in batch context"""
        result = self.review_integration.update_batch_image_caption(
            image_id=self.test_image_ids[0],
            user_id=self.test_user.id,
            new_caption="Updated caption for testing",
            batch_id=self.test_task_id
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['image_id'], self.test_image_ids[0])
        self.assertEqual(result['updated_caption'], "Updated caption for testing")
        
        # Verify caption was updated
        with self.db_manager.get_session() as session:
            image = session.query(Image).filter(Image.id == self.test_image_ids[0]).first()
            self.assertEqual(image.reviewed_caption, "Updated caption for testing")
            self.assertEqual(image.final_caption, "Updated caption for testing")
    
    def test_authorization_checks(self):
        """Test authorization checks in review workflow integration"""
        # Create another user
        import uuid
        other_unique_username = f"other_user_{uuid.uuid4().hex[:8]}"
        other_user, other_helper = create_test_user_with_platforms(
            self.db_manager, username=other_unique_username, role=UserRole.REVIEWER
        )
        
        try:
            # Test unauthorized access to batch
            batch_info = self.review_integration.create_review_batch_from_task(
                self.test_task_id,
                other_user.id  # Wrong user
            )
            self.assertIsNone(batch_info)
            
            # Test unauthorized bulk operations
            approve_result = self.review_integration.bulk_approve_batch(
                self.test_task_id,
                other_user.id,  # Wrong user
                image_ids=self.test_image_ids[:2]
            )
            self.assertFalse(approve_result['success'])
            self.assertIn('access denied', approve_result['error'].lower())
            
            # Test unauthorized regeneration queue
            regen_result = self.review_integration.queue_caption_regeneration(
                image_ids=self.test_image_ids[:2],
                user_id=other_user.id,  # Wrong user
                reason="Unauthorized test"
            )
            self.assertFalse(regen_result['success'])
            self.assertIn('access denied', regen_result['error'].lower())
            
        finally:
            cleanup_test_user(other_helper)
    
    def test_error_handling(self):
        """Test error handling in review workflow integration"""
        # Test with non-existent batch
        batch_info = self.review_integration.create_review_batch_from_task(
            "non-existent-task-id",
            self.test_user.id
        )
        self.assertIsNone(batch_info)
        
        # Test with non-existent images
        regen_result = self.review_integration.queue_caption_regeneration(
            image_ids=[999, 1000],  # Non-existent images
            user_id=self.test_user.id,
            reason="Error test"
        )
        self.assertFalse(regen_result['success'])
        
        # Test quality metrics for non-existent batch
        quality_metrics = self.review_integration.get_job_quality_metrics(
            "non-existent-batch",
            self.test_user.id
        )
        self.assertIsNone(quality_metrics)


if __name__ == '__main__':
    unittest.main()
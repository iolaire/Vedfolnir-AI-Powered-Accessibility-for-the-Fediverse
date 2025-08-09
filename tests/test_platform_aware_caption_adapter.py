# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Unit tests for Platform-Aware Caption Generator Adapter
"""

import unittest
from unittest.mock import Mock, patch, AsyncMock
import asyncio
from datetime import datetime, timezone

from platform_aware_caption_adapter import PlatformAwareCaptionAdapter
from models import PlatformConnection, CaptionGenerationSettings, GenerationResults
from database import DatabaseManager
from config import Config

class TestPlatformAwareCaptionAdapter(unittest.TestCase):
    """Test cases for PlatformAwareCaptionAdapter"""
    
    @patch('platform_aware_caption_adapter.DatabaseManager')
    def setUp(self, mock_db_manager_class):
        """Set up test fixtures"""
        # Mock platform connection
        self.mock_platform_connection = Mock(spec=PlatformConnection)
        self.mock_platform_connection.id = 1
        self.mock_platform_connection.name = "Test Platform"
        self.mock_platform_connection.platform_type = "pixelfed"
        self.mock_platform_connection.instance_url = "https://test.example.com"
        self.mock_platform_connection.username = "testuser"
        self.mock_platform_connection.is_active = True
        
        # Mock config
        self.mock_config = Mock(spec=Config)
        
        # Mock DatabaseManager instance
        self.mock_db_manager = Mock(spec=DatabaseManager)
        mock_db_manager_class.return_value = self.mock_db_manager
        
        # Create adapter
        self.adapter = PlatformAwareCaptionAdapter(
            self.mock_platform_connection,
            self.mock_config
        )
        
        # Test settings
        self.test_settings = CaptionGenerationSettings(
            max_posts_per_run=10,
            max_caption_length=500,
            reprocess_existing=False,
            processing_delay=0.1
        )
    
    @patch('platform_aware_caption_adapter.ActivityPubClient')
    @patch('platform_aware_caption_adapter.ImageProcessor')
    @patch('platform_aware_caption_adapter.OllamaCaptionGenerator')
    async def test_initialize_success(self, mock_caption_gen, mock_image_proc, mock_ap_client):
        """Test successful initialization"""
        # Mock to_activitypub_config
        self.mock_platform_connection.to_activitypub_config.return_value = Mock()
        
        # Mock initialize methods
        mock_caption_gen.return_value.initialize = AsyncMock()
        
        result = await self.adapter.initialize()
        
        self.assertTrue(result)
        self.assertIsNotNone(self.adapter.activitypub_client)
        self.assertIsNotNone(self.adapter.image_processor)
        self.assertIsNotNone(self.adapter.caption_generator)
    
    async def test_initialize_config_failure(self):
        """Test initialization failure when config creation fails"""
        # Mock to_activitypub_config to return None
        self.mock_platform_connection.to_activitypub_config.return_value = None
        
        result = await self.adapter.initialize()
        
        self.assertFalse(result)
    
    @patch('platform_aware_caption_adapter.ActivityPubClient')
    @patch('platform_aware_caption_adapter.ImageProcessor')
    @patch('platform_aware_caption_adapter.OllamaCaptionGenerator')
    async def test_generate_captions_for_user_success(self, mock_caption_gen, mock_image_proc, mock_ap_client):
        """Test successful caption generation"""
        # Mock initialization
        self.mock_platform_connection.to_activitypub_config.return_value = Mock()
        mock_caption_gen.return_value.initialize = AsyncMock()
        
        # Mock get_user_posts
        mock_posts = [
            {'id': 'post1', 'attributedTo': 'https://test.com/users/testuser', 'content': 'Test post 1'},
            {'id': 'post2', 'attributedTo': 'https://test.com/users/testuser', 'content': 'Test post 2'}
        ]
        mock_ap_client.return_value.get_user_posts = AsyncMock(return_value=mock_posts)
        
        # Mock _process_post
        self.adapter._process_post = AsyncMock(return_value={
            'images_processed': 1,
            'captions_generated': 1,
            'errors': 0,
            'skipped_existing': 0,
            'generated_image_ids': [1],
            'error_details': []
        })
        
        # Mock _cleanup
        self.adapter._cleanup = AsyncMock()
        
        # Mock progress callback
        progress_callback = Mock()
        
        result = await self.adapter.generate_captions_for_user(self.test_settings, progress_callback)
        
        self.assertIsInstance(result, GenerationResults)
        self.assertEqual(result.posts_processed, 2)
        self.assertEqual(result.images_processed, 2)
        self.assertEqual(result.captions_generated, 2)
        self.assertEqual(result.errors_count, 0)
        
        # Verify progress callback was called
        self.assertTrue(progress_callback.called)
    
    @patch('platform_aware_caption_adapter.ActivityPubClient')
    @patch('platform_aware_caption_adapter.ImageProcessor')
    @patch('platform_aware_caption_adapter.OllamaCaptionGenerator')
    async def test_generate_captions_no_posts(self, mock_caption_gen, mock_image_proc, mock_ap_client):
        """Test caption generation when no posts are found"""
        # Mock initialization
        self.mock_platform_connection.to_activitypub_config.return_value = Mock()
        mock_caption_gen.return_value.initialize = AsyncMock()
        
        # Mock get_user_posts to return empty list
        mock_ap_client.return_value.get_user_posts = AsyncMock(return_value=[])
        
        # Mock _cleanup
        self.adapter._cleanup = AsyncMock()
        
        result = await self.adapter.generate_captions_for_user(self.test_settings)
        
        self.assertIsInstance(result, GenerationResults)
        self.assertEqual(result.posts_processed, 0)
        self.assertEqual(result.images_processed, 0)
        self.assertEqual(result.captions_generated, 0)
    
    async def test_process_post_success(self):
        """Test successful post processing"""
        # Mock database operations
        mock_db_post = Mock()
        mock_db_post.id = 1
        self.mock_db_manager.get_or_create_post.return_value = mock_db_post
        
        # Mock ActivityPub client
        self.adapter.activitypub_client = Mock()
        self.adapter.activitypub_client.extract_images_from_post.return_value = [
            {
                'url': 'https://test.com/image1.jpg',
                'mediaType': 'image/jpeg',
                'attachment_index': 0,
                'image_post_id': 'img1'
            }
        ]
        
        # Mock _process_image
        self.adapter._process_image = AsyncMock(return_value={
            'image_id': 1,
            'caption_generated': True,
            'skipped': False
        })
        
        post = {
            'id': 'test-post',
            'attributedTo': 'https://test.com/users/testuser',
            'content': 'Test post content'
        }
        
        result = await self.adapter._process_post(post, self.test_settings)
        
        self.assertEqual(result['images_processed'], 1)
        self.assertEqual(result['captions_generated'], 1)
        self.assertEqual(result['errors'], 0)
        self.assertEqual(result['generated_image_ids'], [1])
    
    async def test_process_post_no_images(self):
        """Test post processing when no images are found"""
        # Mock database operations
        mock_db_post = Mock()
        mock_db_post.id = 1
        self.mock_db_manager.get_or_create_post.return_value = mock_db_post
        
        # Mock ActivityPub client to return no images
        self.adapter.activitypub_client = Mock()
        self.adapter.activitypub_client.extract_images_from_post.return_value = []
        
        post = {
            'id': 'test-post',
            'attributedTo': 'https://test.com/users/testuser',
            'content': 'Test post content'
        }
        
        result = await self.adapter._process_post(post, self.test_settings)
        
        self.assertEqual(result['images_processed'], 0)
        self.assertEqual(result['captions_generated'], 0)
        self.assertEqual(result['errors'], 0)
    
    async def test_process_image_success(self):
        """Test successful image processing"""
        # Mock database operations
        self.mock_db_manager.is_image_processed.return_value = False
        self.mock_db_manager.save_image.return_value = 1
        self.mock_db_manager.update_image_caption.return_value = True
        
        # Mock image processor
        self.adapter.image_processor = Mock()
        self.adapter.image_processor.download_and_store_image = AsyncMock(return_value='/path/to/image.jpg')
        
        # Mock caption generator
        self.adapter.caption_generator = Mock()
        self.adapter.caption_generator.generate_caption = AsyncMock(return_value=('Test caption', None))
        
        mock_db_post = Mock()
        mock_db_post.id = 1
        
        image_info = {
            'url': 'https://test.com/image.jpg',
            'mediaType': 'image/jpeg',
            'attachment_index': 0,
            'image_post_id': 'img1'
        }
        
        result = await self.adapter._process_image(image_info, mock_db_post, self.test_settings)
        
        self.assertEqual(result['image_id'], 1)
        self.assertTrue(result['caption_generated'])
        self.assertFalse(result['skipped'])
    
    async def test_process_image_already_processed(self):
        """Test image processing when image is already processed"""
        # Mock database to indicate image is already processed
        self.mock_db_manager.is_image_processed.return_value = True
        
        mock_db_post = Mock()
        mock_db_post.id = 1
        
        image_info = {
            'url': 'https://test.com/image.jpg',
            'mediaType': 'image/jpeg',
            'attachment_index': 0,
            'image_post_id': 'img1'
        }
        
        result = await self.adapter._process_image(image_info, mock_db_post, self.test_settings)
        
        self.assertIsNone(result['image_id'])
        self.assertFalse(result['caption_generated'])
        self.assertTrue(result['skipped'])
    
    async def test_process_image_reprocess_existing(self):
        """Test image processing with reprocess_existing enabled"""
        # Mock database operations
        self.mock_db_manager.is_image_processed.return_value = True  # Already processed
        self.mock_db_manager.save_image.return_value = 1
        self.mock_db_manager.update_image_caption.return_value = True
        
        # Mock image processor
        self.adapter.image_processor = Mock()
        self.adapter.image_processor.download_and_store_image = AsyncMock(return_value='/path/to/image.jpg')
        
        # Mock caption generator
        self.adapter.caption_generator = Mock()
        self.adapter.caption_generator.generate_caption = AsyncMock(return_value='Test caption')
        
        # Enable reprocessing
        settings = CaptionGenerationSettings(reprocess_existing=True)
        
        mock_db_post = Mock()
        mock_db_post.id = 1
        
        image_info = {
            'url': 'https://test.com/image.jpg',
            'mediaType': 'image/jpeg',
            'attachment_index': 0,
            'image_post_id': 'img1'
        }
        
        result = await self.adapter._process_image(image_info, mock_db_post, settings)
        
        self.assertEqual(result['image_id'], 1)
        self.assertTrue(result['caption_generated'])
        self.assertFalse(result['skipped'])
    
    async def test_cleanup(self):
        """Test resource cleanup"""
        # Mock components
        self.adapter.caption_generator = Mock()
        self.adapter.caption_generator.cleanup = Mock()
        
        self.adapter.activitypub_client = Mock()
        self.adapter.activitypub_client.close = AsyncMock()
        
        self.adapter.image_processor = Mock()
        self.adapter.image_processor.close = AsyncMock()
        
        await self.adapter._cleanup()
        
        # Verify cleanup methods were called
        self.adapter.caption_generator.cleanup.assert_called_once()
        self.adapter.activitypub_client.close.assert_called_once()
        self.adapter.image_processor.close.assert_called_once()
    
    def test_get_platform_info(self):
        """Test getting platform information"""
        result = self.adapter.get_platform_info()
        
        expected = {
            'name': 'Test Platform',
            'platform_type': 'pixelfed',
            'instance_url': 'https://test.example.com',
            'username': 'testuser',
            'is_active': True
        }
        
        self.assertEqual(result, expected)
    
    @patch('platform_aware_caption_adapter.ActivityPubClient')
    @patch('platform_aware_caption_adapter.ImageProcessor')
    @patch('platform_aware_caption_adapter.OllamaCaptionGenerator')
    async def test_test_connection_success(self, mock_caption_gen, mock_image_proc, mock_ap_client):
        """Test successful connection test"""
        # Mock initialization
        self.mock_platform_connection.to_activitypub_config.return_value = Mock()
        mock_caption_gen.return_value.initialize = AsyncMock()
        
        # Mock test_connection
        mock_ap_client.return_value.test_connection = AsyncMock(return_value=(True, "Connection successful"))
        
        # Mock _cleanup
        self.adapter._cleanup = AsyncMock()
        
        success, message = await self.adapter.test_connection()
        
        self.assertTrue(success)
        self.assertEqual(message, "Connection successful")
    
    async def test_test_connection_init_failure(self):
        """Test connection test when initialization fails"""
        # Mock initialization failure
        self.mock_platform_connection.to_activitypub_config.return_value = None
        
        success, message = await self.adapter.test_connection()
        
        self.assertFalse(success)
        self.assertEqual(message, "Failed to initialize components")

if __name__ == '__main__':
    unittest.main()
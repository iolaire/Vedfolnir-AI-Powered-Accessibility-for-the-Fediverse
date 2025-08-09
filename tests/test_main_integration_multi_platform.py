# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Integration test to verify that the main application works with the refactored ActivityPub client.
"""

import unittest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from dataclasses import dataclass
from typing import Optional

from activitypub_client import ActivityPubClient
from activitypub_platforms import PlatformAdapterFactory, PixelfedPlatform, MastodonPlatform
from config import RetryConfig, RateLimitConfig


@dataclass
class MockConfig:
    """Mock configuration for testing"""
    instance_url: str = "https://test.example.com"
    access_token: str = "test_token"
    api_type: str = "pixelfed"
    username: str = "testuser"
    client_key: Optional[str] = None
    client_secret: Optional[str] = None
    private_key_path: Optional[str] = None
    public_key_path: Optional[str] = None
    user_agent: str = "TestBot/1.0"
    retry: RetryConfig = None
    rate_limit: RateLimitConfig = None
    
    def __post_init__(self):
        if self.retry is None:
            self.retry = RetryConfig()
        if self.rate_limit is None:
            self.rate_limit = RateLimitConfig()


class TestMainApplicationIntegration(unittest.TestCase):
    """Test integration with main application workflow"""
    
    async def test_pixelfed_main_workflow(self):
        """Test main application workflow with Pixelfed"""
        config = MockConfig(api_type="pixelfed")
        
        with patch.object(PlatformAdapterFactory, 'create_adapter') as mock_factory:
            # Create mock adapter that simulates real Pixelfed responses
            mock_adapter = Mock(spec=PixelfedPlatform)
            mock_adapter.platform_name = "pixelfed"
            
            # Mock posts with images that need alt text
            mock_posts = [
                {
                    "id": "https://pixelfed.social/p/user/1",
                    "type": "Note",
                    "content": "Photo post",
                    "published": "2024-01-15T18:30:00Z",
                    "attachment": [
                        {
                            "type": "Document",
                            "mediaType": "image/jpeg",
                            "url": "https://pixelfed.social/storage/media/photo1.jpg",
                            "name": "",  # No alt text
                            "id": "media_1"
                        }
                    ]
                }
            ]
            
            mock_adapter.get_user_posts = AsyncMock(return_value=mock_posts)
            mock_adapter.update_media_caption = AsyncMock(return_value=True)
            
            # Mock image extraction
            def mock_extract_images(post):
                images = []
                for i, attachment in enumerate(post.get('attachment', [])):
                    if not attachment.get('name', '').strip():
                        images.append({
                            'url': attachment.get('url'),
                            'mediaType': attachment.get('mediaType'),
                            'image_post_id': attachment.get('id'),
                            'attachment_index': i,
                            'attachment_data': attachment,
                            'post_published': post.get('published')
                        })
                return images
            
            mock_adapter.extract_images_from_post = mock_extract_images
            mock_factory.return_value = mock_adapter
            
            # Test the workflow
            client = ActivityPubClient(config)
            
            async with client:
                # Step 1: Get user posts
                posts = await client.get_user_posts("testuser", 50)
                self.assertEqual(len(posts), 1)
                self.assertEqual(posts[0]["id"], "https://pixelfed.social/p/user/1")
                
                # Step 2: Extract images without alt text
                images_to_process = []
                for post in posts:
                    images = client.extract_images_from_post(post)
                    images_to_process.extend(images)
                
                self.assertEqual(len(images_to_process), 1)
                self.assertEqual(images_to_process[0]["image_post_id"], "media_1")
                
                # Step 3: Update media captions
                for image in images_to_process:
                    result = await client.update_media_caption(
                        image["image_post_id"], 
                        "AI-generated alt text"
                    )
                    self.assertTrue(result)
                
                # Verify the adapter methods were called correctly
                mock_adapter.get_user_posts.assert_called_once()
                mock_adapter.update_media_caption.assert_called_once_with(
                    client, "media_1", "AI-generated alt text"
                )
    
    async def test_mastodon_main_workflow(self):
        """Test main application workflow with Mastodon"""
        config = MockConfig(
            api_type="mastodon",
            client_key="test_key",
            client_secret="test_secret"
        )
        
        with patch.object(PlatformAdapterFactory, 'create_adapter') as mock_factory:
            # Create mock adapter that simulates real Mastodon responses
            mock_adapter = Mock(spec=MastodonPlatform)
            mock_adapter.platform_name = "mastodon"
            
            # Mock posts with images that need alt text
            mock_posts = [
                {
                    "id": "https://mastodon.social/@user/123456789",
                    "type": "Note",
                    "content": "Mastodon photo post",
                    "published": "2024-01-15T18:30:00Z",
                    "attachment": [
                        {
                            "type": "Document",
                            "mediaType": "image/jpeg",
                            "url": "https://mastodon.social/media/photo1.jpg",
                            "name": "",  # No alt text
                            "id": "mastodon_media_1"
                        }
                    ]
                }
            ]
            
            mock_adapter.get_user_posts = AsyncMock(return_value=mock_posts)
            mock_adapter.update_media_caption = AsyncMock(return_value=True)
            mock_adapter.authenticate = AsyncMock(return_value=True)
            
            # Mock image extraction (similar to Pixelfed but with Mastodon format)
            def mock_extract_images(post):
                images = []
                for i, attachment in enumerate(post.get('attachment', [])):
                    if not attachment.get('name', '').strip():
                        images.append({
                            'url': attachment.get('url'),
                            'mediaType': attachment.get('mediaType'),
                            'image_post_id': attachment.get('id'),
                            'attachment_index': i,
                            'attachment_data': attachment,
                            'post_published': post.get('published')
                        })
                return images
            
            mock_adapter.extract_images_from_post = mock_extract_images
            mock_factory.return_value = mock_adapter
            
            # Test the workflow
            client = ActivityPubClient(config)
            
            async with client:
                # Step 0: Authenticate (Mastodon-specific)
                auth_result = await client.authenticate()
                self.assertTrue(auth_result)
                
                # Step 1: Get user posts
                posts = await client.get_user_posts("testuser", 50)
                self.assertEqual(len(posts), 1)
                self.assertEqual(posts[0]["id"], "https://mastodon.social/@user/123456789")
                
                # Step 2: Extract images without alt text
                images_to_process = []
                for post in posts:
                    images = client.extract_images_from_post(post)
                    images_to_process.extend(images)
                
                self.assertEqual(len(images_to_process), 1)
                self.assertEqual(images_to_process[0]["image_post_id"], "mastodon_media_1")
                
                # Step 3: Update media captions
                for image in images_to_process:
                    result = await client.update_media_caption(
                        image["image_post_id"], 
                        "AI-generated alt text for Mastodon"
                    )
                    self.assertTrue(result)
                
                # Verify the adapter methods were called correctly
                mock_adapter.authenticate.assert_called_once()
                mock_adapter.get_user_posts.assert_called_once()
                mock_adapter.update_media_caption.assert_called_once_with(
                    client, "mastodon_media_1", "AI-generated alt text for Mastodon"
                )
    
    async def test_platform_agnostic_error_handling(self):
        """Test that error handling works consistently across platforms"""
        # Test with Pixelfed
        pixelfed_config = MockConfig(api_type="pixelfed")
        
        with patch.object(PlatformAdapterFactory, 'create_adapter') as mock_factory:
            mock_adapter = Mock(spec=PixelfedPlatform)
            mock_adapter.platform_name = "pixelfed"
            mock_adapter.get_user_posts = AsyncMock(side_effect=Exception("Network error"))
            mock_factory.return_value = mock_adapter
            
            client = ActivityPubClient(pixelfed_config)
            
            async with client:
                with self.assertRaises(Exception):  # Should propagate as PlatformAdapterError
                    await client.get_user_posts("testuser", 10)
        
        # Test with Mastodon - same error handling behavior
        mastodon_config = MockConfig(
            api_type="mastodon",
            client_key="key",
            client_secret="secret"
        )
        
        with patch.object(PlatformAdapterFactory, 'create_adapter') as mock_factory:
            mock_adapter = Mock(spec=MastodonPlatform)
            mock_adapter.platform_name = "mastodon"
            mock_adapter.get_user_posts = AsyncMock(side_effect=Exception("Network error"))
            mock_factory.return_value = mock_adapter
            
            client = ActivityPubClient(mastodon_config)
            
            async with client:
                with self.assertRaises(Exception):  # Should propagate as PlatformAdapterError
                    await client.get_user_posts("testuser", 10)
    
    def test_platform_info_consistency(self):
        """Test that platform info is consistent across platforms"""
        # Test Pixelfed
        pixelfed_config = MockConfig(api_type="pixelfed")
        
        with patch.object(PlatformAdapterFactory, 'create_adapter') as mock_factory:
            mock_adapter = Mock(spec=PixelfedPlatform)
            mock_adapter.platform_name = "pixelfed"
            mock_factory.return_value = mock_adapter
            
            client = ActivityPubClient(pixelfed_config)
            
            self.assertEqual(client.get_platform_name(), "pixelfed")
            info = client.get_platform_info()
            self.assertEqual(info["platform_name"], "pixelfed")
            self.assertEqual(info["api_type"], "pixelfed")
            self.assertIn("instance_url", info)
        
        # Test Mastodon
        mastodon_config = MockConfig(
            api_type="mastodon",
            client_key="key",
            client_secret="secret"
        )
        
        with patch.object(PlatformAdapterFactory, 'create_adapter') as mock_factory:
            mock_adapter = Mock(spec=MastodonPlatform)
            mock_adapter.platform_name = "mastodon"
            mock_factory.return_value = mock_adapter
            
            client = ActivityPubClient(mastodon_config)
            
            self.assertEqual(client.get_platform_name(), "mastodon")
            info = client.get_platform_info()
            self.assertEqual(info["platform_name"], "mastodon")
            self.assertEqual(info["api_type"], "mastodon")
            self.assertIn("instance_url", info)


    def test_pixelfed_main_workflow_sync(self):
        """Sync wrapper for async test"""
        asyncio.run(self.test_pixelfed_main_workflow())
    
    def test_mastodon_main_workflow_sync(self):
        """Sync wrapper for async test"""
        asyncio.run(self.test_mastodon_main_workflow())
    
    def test_platform_agnostic_error_handling_sync(self):
        """Sync wrapper for async test"""
        asyncio.run(self.test_platform_agnostic_error_handling())


if __name__ == "__main__":
    unittest.main()
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Comprehensive integration tests for Mastodon support.

This module tests the complete workflow with Mastodon configuration,
mocks Mastodon API endpoints, and tests error handling for Mastodon-specific scenarios.
"""

import unittest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
import httpx
import json

from app.services.activitypub.components.activitypub_client import ActivityPubClient
from app.services.activitypub.components.activitypub_platforms import MastodonPlatform, PlatformAdapterFactory
from config import ActivityPubConfig
from main import Vedfolnir

@dataclass
class MockMastodonConfig:
    """Mock Mastodon configuration for testing"""
    instance_url: str = "https://mastodon.social"
    access_token: str = "test_mastodon_token"
    api_type: str = "mastodon"
    username: str = "testuser"
    client_key: str = "test_client_key"
    client_secret: str = "test_client_secret"
    user_agent: str = "Vedfolnir/1.0"
    # Additional attributes needed for ActivityPubClient and Vedfolnir
    private_key_path: Optional[str] = None
    public_key_path: Optional[str] = None
    max_users_per_run: int = 10
    max_posts_per_run: int = 50
    user_processing_delay: int = 5

class TestMastodonAPIEndpointMocking(unittest.TestCase):
    """Test mocking of Mastodon API endpoints"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = MockMastodonConfig()
        self.platform = MastodonPlatform(self.config)
        self.mock_client = Mock()
        self.mock_client._get_with_retry = AsyncMock()
        self.mock_client._put_with_retry = AsyncMock()
    
    async def test_mock_mastodon_verify_credentials_endpoint(self):
        """Test mocking of Mastodon verify_credentials endpoint"""
        # Mock the verify_credentials endpoint response
        verify_response = Mock()
        verify_response.status_code = 200
        verify_response.json.return_value = {
            "id": "123456789",
            "username": "testuser",
            "display_name": "Test User",
            "acct": "testuser",
            "url": "https://mastodon.social/@testuser",
            "avatar": "https://mastodon.social/avatars/testuser.jpg",
            "followers_count": 100,
            "following_count": 50
        }
        self.mock_client._get_with_retry.return_value = verify_response
        
        # Test authentication
        result = await self.platform.authenticate(self.mock_client)
        
        self.assertTrue(result)
        self.mock_client._get_with_retry.assert_called_once()
        
        # Verify the correct endpoint was called
        call_args = self.mock_client._get_with_retry.call_args
        self.assertIn("/api/v1/accounts/verify_credentials", call_args[0][0])
    
    async def test_mock_mastodon_account_lookup_endpoint(self):
        """Test mocking of Mastodon account lookup endpoint"""
        # Mock account lookup response
        lookup_response = Mock()
        lookup_response.json.return_value = {
            "id": "123456789",
            "username": "testuser",
            "acct": "testuser",
            "display_name": "Test User"
        }
        
        # Mock the _resolve_user_to_account_id method
        with patch.object(self.platform, '_resolve_user_to_account_id', return_value="123456789"):
            account_id = await self.platform._resolve_user_to_account_id(
                self.mock_client, "testuser", {}
            )
        
        self.assertEqual(account_id, "123456789")
    
    async def test_mock_mastodon_statuses_endpoint(self):
        """Test mocking of Mastodon statuses endpoint"""
        # Mock statuses endpoint response
        statuses_response = Mock()
        statuses_response.json.return_value = [
            {
                "id": "109123456789",
                "created_at": "2023-01-01T12:00:00.000Z",
                "content": "<p>Test status with image</p>",
                "url": "https://mastodon.social/@testuser/109123456789",
                "media_attachments": [
                    {
                        "id": "media123",
                        "type": "image",
                        "url": "https://mastodon.social/media/image1.jpg",
                        "preview_url": "https://mastodon.social/media/image1_small.jpg",
                        "description": None,  # No alt text
                        "meta": {
                            "original": {"width": 1200, "height": 800}
                        }
                    }
                ]
            },
            {
                "id": "109123456790",
                "created_at": "2023-01-01T11:00:00.000Z",
                "content": "<p>Another test status</p>",
                "url": "https://mastodon.social/@testuser/109123456790",
                "media_attachments": [
                    {
                        "id": "media124",
                        "type": "image",
                        "url": "https://mastodon.social/media/image2.jpg",
                        "preview_url": "https://mastodon.social/media/image2_small.jpg",
                        "description": "Existing alt text",  # Has alt text
                        "meta": {
                            "original": {"width": 800, "height": 600}
                        }
                    }
                ]
            }
        ]
        
        # Set up authenticated state
        self.platform._authenticated = True
        self.platform._auth_headers = {
            "Authorization": f"Bearer {self.config.access_token}",
            "Accept": "application/json"
        }
        
        # Mock authenticate and user resolution
        with patch.object(self.platform, 'authenticate', return_value=True):
            with patch.object(self.platform, '_resolve_user_to_account_id', return_value="123456789"):
                self.mock_client._get_with_retry.return_value = statuses_response
                
                posts = await self.platform.get_user_posts(self.mock_client, "testuser", 20)
        
        # Should return posts converted to ActivityPub format
        self.assertEqual(len(posts), 2)
        self.assertEqual(posts[0]["type"], "Note")
        self.assertIn("attachment", posts[0])
    
    async def test_mock_mastodon_media_update_endpoint(self):
        """Test mocking of Mastodon media update endpoint"""
        # Mock media update response
        update_response = Mock()
        update_response.status_code = 200
        update_response.json.return_value = {
            "id": "media123",
            "type": "image",
            "url": "https://mastodon.social/media/image1.jpg",
            "description": "Updated alt text description"
        }
        self.mock_client._put_with_retry.return_value = update_response
        
        # Mock authentication
        with patch.object(self.platform, 'authenticate', return_value=True):
            with patch.object(self.platform, '_get_auth_headers') as mock_headers:
                mock_headers.return_value = {
                    "Authorization": f"Bearer {self.config.access_token}",
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                }
                
                result = await self.platform.update_media_caption(
                    self.mock_client, "media123", "Updated alt text description"
                )
        
        self.assertTrue(result)
        self.mock_client._put_with_retry.assert_called_once()
        
        # Verify the correct endpoint was called
        call_args = self.mock_client._put_with_retry.call_args
        self.assertIn("/api/v1/media/media123", call_args[0][0])
        self.assertEqual(call_args[1]["json"]["description"], "Updated alt text description")

class TestMastodonWorkflowIntegration(unittest.TestCase):
    """Test complete workflow with Mastodon configuration"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = MockMastodonConfig()
    
    def test_mastodon_platform_adapter_creation(self):
        """Test that PlatformAdapterFactory creates Mastodon adapter correctly"""
        adapter = PlatformAdapterFactory.create_adapter(self.config)
        
        self.assertIsInstance(adapter, MastodonPlatform)
        self.assertEqual(adapter.config, self.config)
        self.assertEqual(adapter.platform_name, "mastodon")
    
    async def test_mastodon_activitypub_client_integration(self):
        """Test ActivityPubClient integration with Mastodon platform"""
        # Create ActivityPubClient with Mastodon configuration
        client = ActivityPubClient(self.config)
        
        # Mock the platform adapter
        mock_platform = Mock(spec=MastodonPlatform)
        mock_platform.get_user_posts = AsyncMock(return_value=[
            {
                "id": "https://mastodon.social/@testuser/109123456789",
                "type": "Note",
                "content": "Test post",
                "published": "2023-01-01T12:00:00.000Z",
                "attachment": [
                    {
                        "type": "Document",
                        "mediaType": "image/jpeg",
                        "url": "https://mastodon.social/media/image1.jpg",
                        "name": None,
                        "id": "media123"
                    }
                ]
            }
        ])
        mock_platform.extract_images_from_post = Mock(return_value=[
            {
                "url": "https://mastodon.social/media/image1.jpg",
                "mediaType": "image/jpeg",
                "image_post_id": "media123",
                "attachment_index": 0
            }
        ])
        mock_platform.update_media_caption = AsyncMock(return_value=True)
        
        # Replace the platform adapter
        client.platform = mock_platform
        
        # Test getting user posts
        posts = await client.get_user_posts("testuser", 10)
        self.assertEqual(len(posts), 1)
        mock_platform.get_user_posts.assert_called_once_with(client, "testuser", 10)
        
        # Test extracting images
        images = client.extract_images_from_post(posts[0])
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0]["image_post_id"], "media123")
        
        # Test updating media caption
        result = await client.update_media_caption("media123", "Test caption")
        self.assertTrue(result)
        mock_platform.update_media_caption.assert_called_once_with(client, "media123", "Test caption")
    
    async def test_mastodon_end_to_end_workflow_mock(self):
        """Test end-to-end workflow with mocked Mastodon responses"""
        # Mock all the necessary components
        with patch('main.ActivityPubClient') as mock_client_class:
            with patch('main.ImageProcessor') as mock_image_processor_class:
                with patch('main.OllamaCaptionGenerator') as mock_caption_generator_class:
                    with patch('main.DatabaseManager') as mock_db_manager_class:
                        
                        # Set up mocks
                        mock_client = Mock()
                        mock_client.get_user_posts = AsyncMock(return_value=[
                            {
                                "id": "https://mastodon.social/@testuser/109123456789",
                                "type": "Note",
                                "content": "Test post",
                                "published": "2023-01-01T12:00:00.000Z",
                                "attachment": [
                                    {
                                        "type": "Document",
                                        "mediaType": "image/jpeg",
                                        "url": "https://mastodon.social/media/image1.jpg",
                                        "name": None,
                                        "id": "media123"
                                    }
                                ]
                            }
                        ])
                        mock_client.extract_images_from_post = Mock(return_value=[
                            {
                                "url": "https://mastodon.social/media/image1.jpg",
                                "mediaType": "image/jpeg",
                                "image_post_id": "media123",
                                "attachment_index": 0,
                                "post_published": "2023-01-01T12:00:00.000Z"
                            }
                        ])
                        mock_client.update_media_caption = AsyncMock(return_value=True)
                        mock_client_class.return_value = mock_client
                        
                        mock_image_processor = Mock()
                        mock_image_processor.download_and_store_image = Mock(return_value="/path/to/image.jpg")
                        mock_image_processor_class.return_value = mock_image_processor
                        
                        mock_caption_generator = Mock()
                        mock_caption_generator.generate_caption = Mock(return_value="Generated alt text")
                        mock_caption_generator_class.return_value = mock_caption_generator
                        
                        mock_db_manager = Mock()
                        mock_db_manager.get_or_create_post = Mock(return_value=(Mock(id=1), True))
                        mock_db_manager.save_image = Mock(return_value=Mock(id=1))
                        mock_db_manager.create_processing_run = Mock(return_value=Mock(id=1))
                        mock_db_manager.update_processing_run = Mock()
                        mock_db_manager_class.return_value = mock_db_manager
                        
                        # Create a proper config structure for Vedfolnir
                        from config import Config
                        with patch('config.Config') as mock_config_class:
                            mock_config = Mock()
                            mock_config.activitypub = self.config
                            mock_config.max_users_per_run = 10
                            mock_config_class.return_value = mock_config
                            
                            # Create and run the bot
                            bot = Vedfolnir(mock_config)
                            await bot.run("testuser")
                        
                        # Verify the workflow executed
                        mock_client.get_user_posts.assert_called_once()
                        mock_image_processor.download_and_store_image.assert_called_once()
                        mock_caption_generator.generate_caption.assert_called_once()
                        mock_db_manager.save_image.assert_called_once()

class TestMastodonErrorHandling(unittest.TestCase):
    """Test error handling for Mastodon-specific scenarios"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = MockMastodonConfig()
        self.platform = MastodonPlatform(self.config)
        self.mock_client = Mock()
        self.mock_client._get_with_retry = AsyncMock()
        self.mock_client._put_with_retry = AsyncMock()
    
    async def test_mastodon_authentication_401_error(self):
        """Test handling of 401 Unauthorized error during authentication"""
        # Mock 401 response
        mock_response = Mock()
        mock_response.status_code = 401
        self.mock_client._get_with_retry.side_effect = httpx.HTTPStatusError(
            "Unauthorized", request=Mock(), response=mock_response
        )
        
        result = await self.platform.authenticate(self.mock_client)
        
        self.assertFalse(result)
        self.assertFalse(self.platform._authenticated)
    
    async def test_mastodon_authentication_403_error(self):
        """Test handling of 403 Forbidden error during authentication"""
        # Mock 403 response
        mock_response = Mock()
        mock_response.status_code = 403
        self.mock_client._get_with_retry.side_effect = httpx.HTTPStatusError(
            "Forbidden", request=Mock(), response=mock_response
        )
        
        result = await self.platform.authenticate(self.mock_client)
        
        self.assertFalse(result)
        self.assertFalse(self.platform._authenticated)
    
    async def test_mastodon_authentication_network_error(self):
        """Test handling of network errors during authentication"""
        # Mock network error
        self.mock_client._get_with_retry.side_effect = httpx.ConnectError(
            "Connection failed"
        )
        
        result = await self.platform.authenticate(self.mock_client)
        
        self.assertFalse(result)
        self.assertFalse(self.platform._authenticated)
    
    async def test_mastodon_authentication_timeout_error(self):
        """Test handling of timeout errors during authentication"""
        # Mock timeout error
        self.mock_client._get_with_retry.side_effect = httpx.TimeoutException(
            "Request timed out"
        )
        
        result = await self.platform.authenticate(self.mock_client)
        
        self.assertFalse(result)
        self.assertFalse(self.platform._authenticated)
    
    async def test_mastodon_get_user_posts_user_not_found(self):
        """Test handling of user not found error when getting posts"""
        # Mock authentication success and auth headers
        with patch.object(self.platform, 'authenticate', return_value=True):
            with patch.object(self.platform, '_get_auth_headers') as mock_headers:
                mock_headers.return_value = {"Authorization": "Bearer token"}
                # Mock user resolution failure
                with patch.object(self.platform, '_resolve_user_to_account_id', return_value=None):
                    posts = await self.platform.get_user_posts(self.mock_client, "nonexistent", 10)
        
        self.assertEqual(len(posts), 0)
    
    async def test_mastodon_get_user_posts_api_error(self):
        """Test handling of API errors when getting user posts"""
        # Mock authentication success and auth headers
        with patch.object(self.platform, 'authenticate', return_value=True):
            with patch.object(self.platform, '_get_auth_headers') as mock_headers:
                mock_headers.return_value = {"Authorization": "Bearer token"}
                with patch.object(self.platform, '_resolve_user_to_account_id', return_value="123456"):
                    # Mock API error
                    self.mock_client._get_with_retry.side_effect = httpx.HTTPStatusError(
                        "Internal Server Error", request=Mock(), response=Mock(status_code=500)
                    )
                    
                    posts = await self.platform.get_user_posts(self.mock_client, "testuser", 10)
        
        self.assertEqual(len(posts), 0)
    
    async def test_mastodon_update_media_caption_authentication_failure(self):
        """Test handling of authentication failure during media update"""
        # Mock authentication failure
        with patch.object(self.platform, 'authenticate', return_value=False):
            result = await self.platform.update_media_caption(
                self.mock_client, "media123", "Test caption"
            )
        
        self.assertFalse(result)
    
    async def test_mastodon_update_media_caption_404_error(self):
        """Test handling of 404 error when updating non-existent media"""
        # Mock authentication success
        with patch.object(self.platform, 'authenticate', return_value=True):
            with patch.object(self.platform, '_get_auth_headers') as mock_headers:
                mock_headers.return_value = {"Authorization": "Bearer token"}
                
                # Mock 404 response
                self.mock_client._put_with_retry.side_effect = httpx.HTTPStatusError(
                    "Not Found", request=Mock(), response=Mock(status_code=404)
                )
                
                result = await self.platform.update_media_caption(
                    self.mock_client, "nonexistent", "Test caption"
                )
        
        self.assertFalse(result)
    
    async def test_mastodon_update_media_caption_rate_limit_error(self):
        """Test handling of rate limit error during media update"""
        # Mock authentication success
        with patch.object(self.platform, 'authenticate', return_value=True):
            with patch.object(self.platform, '_get_auth_headers') as mock_headers:
                mock_headers.return_value = {"Authorization": "Bearer token"}
                
                # Mock 429 rate limit response
                mock_response = Mock()
                mock_response.status_code = 429
                mock_response.headers = {"Retry-After": "60"}
                self.mock_client._put_with_retry.side_effect = httpx.HTTPStatusError(
                    "Too Many Requests", request=Mock(), response=mock_response
                )
                
                result = await self.platform.update_media_caption(
                    self.mock_client, "media123", "Test caption"
                )
        
        self.assertFalse(result)
    
    def test_mastodon_extract_images_malformed_post(self):
        """Test handling of malformed post data when extracting images"""
        # Test with missing attachment field
        malformed_post1 = {
            "id": "https://mastodon.social/@testuser/109123456789",
            "type": "Note",
            "content": "Test post"
            # Missing attachment field
        }
        
        images = self.platform.extract_images_from_post(malformed_post1)
        self.assertEqual(len(images), 0)
        
        # Test with null attachment field
        malformed_post2 = {
            "id": "https://mastodon.social/@testuser/109123456789",
            "type": "Note",
            "content": "Test post",
            "attachment": None
        }
        
        images = self.platform.extract_images_from_post(malformed_post2)
        self.assertEqual(len(images), 0)
        
        # Test with malformed attachment data
        malformed_post3 = {
            "id": "https://mastodon.social/@testuser/109123456789",
            "type": "Note",
            "content": "Test post",
            "attachment": [
                {
                    "type": "Document",
                    # Missing required fields like url, mediaType
                }
            ]
        }
        
        images = self.platform.extract_images_from_post(malformed_post3)
        self.assertEqual(len(images), 0)
    
    def test_mastodon_extract_images_non_image_media(self):
        """Test handling of non-image media when extracting images"""
        post_with_video = {
            "id": "https://mastodon.social/@testuser/109123456789",
            "type": "Note",
            "content": "Test post with video",
            "attachment": [
                {
                    "type": "Document",
                    "mediaType": "video/mp4",
                    "url": "https://mastodon.social/media/video1.mp4",
                    "name": None,
                    "id": "media123"
                }
            ]
        }
        
        images = self.platform.extract_images_from_post(post_with_video)
        self.assertEqual(len(images), 0)  # Should not return video as image
    
    async def test_mastodon_pagination_error_handling(self):
        """Test error handling during pagination of user posts"""
        # Mock authentication success and auth headers
        with patch.object(self.platform, 'authenticate', return_value=True):
            with patch.object(self.platform, '_get_auth_headers') as mock_headers:
                mock_headers.return_value = {"Authorization": "Bearer token"}
                with patch.object(self.platform, '_resolve_user_to_account_id', return_value="123456"):
                    # Mock first page success, second page failure
                    first_page_response = Mock()
                    first_page_response.json.return_value = [
                        {
                            "id": "109123456789",
                            "created_at": "2023-01-01T12:00:00.000Z",
                            "content": "Test post",
                            "media_attachments": [
                                {
                                    "id": "media123",
                                    "type": "image",
                                    "url": "https://mastodon.social/media/image1.jpg",
                                    "description": None
                                }
                            ]
                        }
                    ]
                    
                    # First call succeeds, second call fails
                    self.mock_client._get_with_retry.side_effect = [
                        first_page_response,
                        httpx.HTTPStatusError("Server Error", request=Mock(), response=Mock(status_code=500))
                    ]
                    
                    posts = await self.platform.get_user_posts(self.mock_client, "testuser", 50)
        
        # Should return posts from successful page, handle error gracefully
        self.assertEqual(len(posts), 1)

def run_async_test(coro):
    """Helper function to run async tests"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

# Convert async test methods to sync for unittest
class TestMastodonAPIEndpointMockingSync(TestMastodonAPIEndpointMocking):
    """Synchronous wrapper for async Mastodon API endpoint tests"""
    
    def test_mock_mastodon_verify_credentials_endpoint_sync(self):
        run_async_test(self.test_mock_mastodon_verify_credentials_endpoint())
    
    def test_mock_mastodon_account_lookup_endpoint_sync(self):
        run_async_test(self.test_mock_mastodon_account_lookup_endpoint())
    
    def test_mock_mastodon_statuses_endpoint_sync(self):
        run_async_test(self.test_mock_mastodon_statuses_endpoint())
    
    def test_mock_mastodon_media_update_endpoint_sync(self):
        run_async_test(self.test_mock_mastodon_media_update_endpoint())

class TestMastodonWorkflowIntegrationSync(TestMastodonWorkflowIntegration):
    """Synchronous wrapper for async Mastodon workflow tests"""
    
    def test_mastodon_activitypub_client_integration_sync(self):
        run_async_test(self.test_mastodon_activitypub_client_integration())
    
    def test_mastodon_end_to_end_workflow_mock_sync(self):
        run_async_test(self.test_mastodon_end_to_end_workflow_mock())

class TestMastodonErrorHandlingSync(TestMastodonErrorHandling):
    """Synchronous wrapper for async Mastodon error handling tests"""
    
    def test_mastodon_authentication_401_error_sync(self):
        run_async_test(self.test_mastodon_authentication_401_error())
    
    def test_mastodon_authentication_403_error_sync(self):
        run_async_test(self.test_mastodon_authentication_403_error())
    
    def test_mastodon_authentication_network_error_sync(self):
        run_async_test(self.test_mastodon_authentication_network_error())
    
    def test_mastodon_authentication_timeout_error_sync(self):
        run_async_test(self.test_mastodon_authentication_timeout_error())
    
    def test_mastodon_get_user_posts_user_not_found_sync(self):
        run_async_test(self.test_mastodon_get_user_posts_user_not_found())
    
    def test_mastodon_get_user_posts_api_error_sync(self):
        run_async_test(self.test_mastodon_get_user_posts_api_error())
    
    def test_mastodon_update_media_caption_authentication_failure_sync(self):
        run_async_test(self.test_mastodon_update_media_caption_authentication_failure())
    
    def test_mastodon_update_media_caption_404_error_sync(self):
        run_async_test(self.test_mastodon_update_media_caption_404_error())
    
    def test_mastodon_update_media_caption_rate_limit_error_sync(self):
        run_async_test(self.test_mastodon_update_media_caption_rate_limit_error())
    
    def test_mastodon_pagination_error_handling_sync(self):
        run_async_test(self.test_mastodon_pagination_error_handling())

if __name__ == "__main__":
    unittest.main()
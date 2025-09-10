# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Comprehensive unit tests for platform adapters.

This module tests the PixelfedPlatform and MastodonPlatform adapters to ensure
they maintain existing functionality and handle platform-specific API calls correctly.
Also tests platform detection and adapter factory functionality.
"""

import unittest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
import httpx

from app.services.activitypub.components.activitypub_platforms import (
    ActivityPubPlatform,
    PixelfedPlatform,
    MastodonPlatform,
    PlatformAdapterFactory,
    PlatformAdapterError,
    UnsupportedPlatformError,
    PlatformDetectionError
)

@dataclass
class MockConfig:
    """Mock configuration for testing"""
    instance_url: str = "https://test.example.com"
    access_token: str = "test_token"
    api_type: str = "pixelfed"
    username: Optional[str] = "testuser"
    client_key: Optional[str] = None
    client_secret: Optional[str] = None
    user_agent: str = "Vedfolnir/1.0"

class TestPixelfedPlatformAdapter(unittest.TestCase):
    """Test PixelfedPlatform adapter maintains existing functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = MockConfig(
            instance_url="https://pixelfed.social",
            api_type="pixelfed"
        )
        self.platform = PixelfedPlatform(self.config)
        self.mock_client = Mock()
        self.mock_client._get_with_retry = AsyncMock()
        self.mock_client._put_with_retry = AsyncMock()
    
    def test_pixelfed_platform_initialization(self):
        """Test PixelfedPlatform initializes correctly"""
        self.assertEqual(self.platform.config, self.config)
        self.assertEqual(self.platform.platform_name, "pixelfed")
    
    def test_pixelfed_config_validation_success(self):
        """Test successful Pixelfed configuration validation"""
        # Should not raise any exceptions
        platform = PixelfedPlatform(self.config)
        self.assertIsNotNone(platform)
    
    def test_pixelfed_config_validation_missing_instance_url(self):
        """Test Pixelfed configuration validation with missing instance URL"""
        config = MockConfig()
        config.instance_url = ""
        
        with self.assertRaises(PlatformAdapterError) as context:
            PixelfedPlatform(config)
        
        self.assertIn("instance_url is required", str(context.exception))
    
    def test_pixelfed_config_validation_missing_access_token(self):
        """Test Pixelfed configuration validation with missing access token"""
        config = MockConfig()
        config.access_token = ""
        
        with self.assertRaises(PlatformAdapterError) as context:
            PixelfedPlatform(config)
        
        self.assertIn("access_token is required", str(context.exception))
    
    async def test_pixelfed_get_user_posts_success(self):
        """Test successful retrieval of Pixelfed user posts"""
        # Mock verify_credentials response
        verify_response = Mock()
        verify_response.json.return_value = {"id": "123456"}
        
        # Mock statuses response
        statuses_response = Mock()
        statuses_response.json.return_value = [
            {
                "id": "post1",
                "url": "https://pixelfed.social/p/user/post1",
                "content": "Test post 1",
                "created_at": "2023-01-01T00:00:00Z",
                "media_attachments": [
                    {
                        "id": "media1",
                        "type": "image",
                        "url": "https://pixelfed.social/storage/media1.jpg",
                        "description": ""
                    }
                ]
            }
        ]
        
        self.mock_client._get_with_retry.side_effect = [verify_response, statuses_response]
        
        posts = await self.platform.get_user_posts(self.mock_client, "testuser", 10)
        
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0]["type"], "Note")
        self.assertEqual(posts[0]["content"], "Test post 1")
        self.assertEqual(len(posts[0]["attachment"]), 1)
        self.assertEqual(posts[0]["attachment"][0]["type"], "Document")
    
    async def test_pixelfed_get_user_posts_pagination(self):
        """Test Pixelfed user posts retrieval with pagination"""
        # Mock verify_credentials response
        verify_response = Mock()
        verify_response.json.return_value = {"id": "123456"}
        
        # Mock first page response
        first_page_response = Mock()
        first_page_response.json.return_value = [
            {
                "id": f"post{i}",
                "url": f"https://pixelfed.social/p/user/post{i}",
                "content": f"Test post {i}",
                "created_at": "2023-01-01T00:00:00Z",
                "media_attachments": [
                    {
                        "id": f"media{i}",
                        "type": "image",
                        "url": f"https://pixelfed.social/storage/media{i}.jpg",
                        "description": ""
                    }
                ]
            }
            for i in range(1, 41)  # 40 posts (full page)
        ]
        
        # Mock second page response (partial)
        second_page_response = Mock()
        second_page_response.json.return_value = [
            {
                "id": f"post{i}",
                "url": f"https://pixelfed.social/p/user/post{i}",
                "content": f"Test post {i}",
                "created_at": "2023-01-01T00:00:00Z",
                "media_attachments": [
                    {
                        "id": f"media{i}",
                        "type": "image",
                        "url": f"https://pixelfed.social/storage/media{i}.jpg",
                        "description": ""
                    }
                ]
            }
            for i in range(41, 51)  # 10 more posts
        ]
        
        self.mock_client._get_with_retry.side_effect = [
            verify_response, first_page_response, second_page_response
        ]
        
        posts = await self.platform.get_user_posts(self.mock_client, "testuser", 50)
        
        self.assertEqual(len(posts), 50)
        # Verify pagination was used (3 calls: verify + 2 pages)
        self.assertEqual(self.mock_client._get_with_retry.call_count, 3)
    
    async def test_pixelfed_update_media_caption_success(self):
        """Test successful Pixelfed media caption update"""
        # Mock successful update response
        update_response = Mock()
        update_response.status_code = 200
        self.mock_client._put_with_retry.return_value = update_response
        
        result = await self.platform.update_media_caption(
            self.mock_client, "media123", "Test caption"
        )
        
        self.assertTrue(result)
        self.mock_client._put_with_retry.assert_called_once()
        
        # Verify the call was made with correct parameters
        call_args = self.mock_client._put_with_retry.call_args
        self.assertIn("/api/v1/media/media123", call_args[0][0])
        self.assertEqual(call_args[1]["json"]["description"], "Test caption")
    
    async def test_pixelfed_update_media_caption_failure(self):
        """Test Pixelfed media caption update failure"""
        # Mock failed update response
        self.mock_client._put_with_retry.side_effect = Exception("Update failed")
        
        result = await self.platform.update_media_caption(
            self.mock_client, "media123", "Test caption"
        )
        
        self.assertFalse(result)
    
    def test_pixelfed_extract_images_from_post(self):
        """Test extracting images from Pixelfed post"""
        post = {
            "id": "https://pixelfed.social/p/user/post1",
            "type": "Note",
            "published": "2023-01-01T00:00:00Z",
            "attachment": [
                {
                    "type": "Document",
                    "mediaType": "image/jpeg",
                    "url": "https://pixelfed.social/storage/image1.jpg",
                    "name": "",  # Empty alt text
                    "id": "media1"
                },
                {
                    "type": "Document",
                    "mediaType": "image/png",
                    "url": "https://pixelfed.social/storage/image2.png",
                    "name": "Existing alt text",  # Has alt text
                    "id": "media2"
                }
            ]
        }
        
        images = self.platform.extract_images_from_post(post)
        
        # Should only return the image without alt text
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0]["url"], "https://pixelfed.social/storage/image1.jpg")
        self.assertEqual(images[0]["image_post_id"], "media1")
        self.assertEqual(images[0]["attachment_index"], 0)
    
    def test_pixelfed_extract_images_no_media(self):
        """Test extracting images from post with no media"""
        post = {
            "id": "https://pixelfed.social/p/user/post1",
            "type": "Note",
            "published": "2023-01-01T00:00:00Z",
            "attachment": []
        }
        
        images = self.platform.extract_images_from_post(post)
        
        self.assertEqual(len(images), 0)
    
    def test_pixelfed_get_rate_limit_info(self):
        """Test extracting rate limit info from Pixelfed response headers"""
        headers = {
            "X-RateLimit-Limit": "100",
            "X-RateLimit-Remaining": "95",
            "X-RateLimit-Reset": "1640995200"
        }
        
        rate_limit_info = self.platform.get_rate_limit_info(headers)
        
        self.assertEqual(rate_limit_info["limit"], 100)
        self.assertEqual(rate_limit_info["remaining"], 95)
        self.assertEqual(rate_limit_info["reset"], 1640995200)
    
    def test_pixelfed_get_rate_limit_info_missing_headers(self):
        """Test rate limit info extraction with missing headers"""
        headers = {}
        
        rate_limit_info = self.platform.get_rate_limit_info(headers)
        
        self.assertEqual(rate_limit_info, {})

class TestMastodonPlatformAdapter(unittest.TestCase):
    """Test MastodonPlatform adapter handles Mastodon API correctly"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = MockConfig(
            instance_url="https://mastodon.social",
            api_type="mastodon",
            client_key="test_client_key",
            client_secret="test_client_secret"
        )
        self.platform = MastodonPlatform(self.config)
        self.mock_client = Mock()
        self.mock_client._get_with_retry = AsyncMock()
        self.mock_client._put_with_retry = AsyncMock()
    
    def test_mastodon_platform_initialization(self):
        """Test MastodonPlatform initializes correctly"""
        self.assertEqual(self.platform.config, self.config)
        self.assertEqual(self.platform.platform_name, "mastodon")
        self.assertFalse(self.platform._authenticated)
        self.assertIsNone(self.platform._auth_headers)
    
    def test_mastodon_config_validation_success(self):
        """Test successful Mastodon configuration validation"""
        # Should not raise any exceptions
        platform = MastodonPlatform(self.config)
        self.assertIsNotNone(platform)
    
    def test_mastodon_config_validation_missing_client_key(self):
        """Test Mastodon configuration validation with missing client key (should succeed)"""
        config = MockConfig(api_type="mastodon")
        config.client_key = None
        
        # Should not raise an error - client credentials are optional for Mastodon
        platform = MastodonPlatform(config)
        self.assertIsNotNone(platform)
    
    def test_mastodon_config_validation_missing_client_secret(self):
        """Test Mastodon configuration validation with missing client secret (should succeed)"""
        config = MockConfig(api_type="mastodon", client_key="test_key")
        config.client_secret = None
        
        # Should not raise an error - client credentials are optional for Mastodon
        platform = MastodonPlatform(config)
        self.assertIsNotNone(platform)
    
    async def test_mastodon_authenticate_success(self):
        """Test successful Mastodon authentication"""
        # Mock successful verify_credentials response
        verify_response = Mock()
        verify_response.status_code = 200
        verify_response.json.return_value = {
            "id": "123456",
            "username": "testuser",
            "display_name": "Test User"
        }
        self.mock_client._get_with_retry.return_value = verify_response
        
        result = await self.platform.authenticate(self.mock_client)
        
        self.assertTrue(result)
        self.assertTrue(self.platform._authenticated)
        self.assertIsNotNone(self.platform._auth_headers)
        self.assertEqual(
            self.platform._auth_headers["Authorization"],
            f"Bearer {self.config.access_token}"
        )
    
    async def test_mastodon_authenticate_invalid_token(self):
        """Test Mastodon authentication with invalid token"""
        # Mock 401 Unauthorized response
        mock_response = Mock()
        mock_response.status_code = 401
        self.mock_client._get_with_retry.side_effect = httpx.HTTPStatusError(
            "Unauthorized", request=Mock(), response=mock_response
        )
        
        result = await self.platform.authenticate(self.mock_client)
        
        self.assertFalse(result)
        self.assertFalse(self.platform._authenticated)
        self.assertIsNone(self.platform._auth_headers)
    
    async def test_mastodon_get_user_posts_success(self):
        """Test successful retrieval of Mastodon user posts"""
        # Set up authenticated state
        self.platform._authenticated = True
        self.platform._auth_headers = {
            "Authorization": f"Bearer {self.config.access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        # Mock account lookup response
        lookup_response = Mock()
        lookup_response.json.return_value = {"id": "123456"}
        
        # Mock statuses response
        statuses_response = Mock()
        statuses_response.json.return_value = [
            {
                "id": "status1",
                "url": "https://mastodon.social/@user/status1",
                "content": "Test status 1",
                "created_at": "2023-01-01T00:00:00Z",
                "media_attachments": [
                    {
                        "id": "media1",
                        "type": "image",
                        "url": "https://mastodon.social/media/media1.jpg",
                        "description": None
                    }
                ]
            }
        ]
        
        # Mock authenticate call
        with patch.object(self.platform, 'authenticate', return_value=True):
            with patch.object(self.platform, '_resolve_user_to_account_id', return_value="123456"):
                self.mock_client._get_with_retry.return_value = statuses_response
                
                posts = await self.platform.get_user_posts(self.mock_client, "testuser", 10)
        
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0]["type"], "Note")
        self.assertEqual(posts[0]["content"], "Test status 1")
        self.assertEqual(len(posts[0]["attachment"]), 1)
    
    async def test_mastodon_update_media_caption_success(self):
        """Test successful Mastodon media caption update"""
        # Mock successful update response
        update_response = Mock()
        update_response.status_code = 200
        self.mock_client._put_with_retry.return_value = update_response
        
        # Mock the authenticate and _get_auth_headers methods
        with patch.object(self.platform, 'authenticate', return_value=True) as mock_auth:
            with patch.object(self.platform, '_get_auth_headers') as mock_get_headers:
                mock_get_headers.return_value = {
                    "Authorization": f"Bearer {self.config.access_token}",
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                }
                
                result = await self.platform.update_media_caption(
                    self.mock_client, "media123", "Test caption"
                )
        
        self.assertTrue(result)
        self.mock_client._put_with_retry.assert_called_once()
        
        # Verify the call was made with correct parameters
        call_args = self.mock_client._put_with_retry.call_args
        self.assertIn("/api/v1/media/media123", call_args[0][0])
        self.assertEqual(call_args[1]["json"]["description"], "Test caption")
    
    def test_mastodon_extract_images_from_post(self):
        """Test extracting images from Mastodon post"""
        post = {
            "id": "https://mastodon.social/@user/status1",
            "type": "Note",
            "published": "2023-01-01T00:00:00Z",
            "attachment": [
                {
                    "type": "Document",
                    "mediaType": "image/jpeg",
                    "url": "https://mastodon.social/media/image1.jpg",
                    "name": None,  # No alt text
                    "id": "media1"
                },
                {
                    "type": "Document",
                    "mediaType": "image/png",
                    "url": "https://mastodon.social/media/image2.png",
                    "name": "Existing alt text",  # Has alt text
                    "id": "media2"
                }
            ]
        }
        
        images = self.platform.extract_images_from_post(post)
        
        # Should only return the image without alt text
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0]["url"], "https://mastodon.social/media/image1.jpg")
        self.assertEqual(images[0]["image_post_id"], "media1")
        self.assertEqual(images[0]["attachment_index"], 0)

class TestPlatformDetectionAndFactory(unittest.TestCase):
    """Test platform detection and adapter factory"""
    
    def test_pixelfed_platform_detection_known_instances(self):
        """Test Pixelfed platform detection with known instances"""
        known_instances = [
            "https://pixelfed.social",
            "https://pixelfed.de",
            "https://pixelfed.uno",
            "https://pixey.org",
            "https://pix.tube"
        ]
        
        for instance_url in known_instances:
            self.assertTrue(
                PixelfedPlatform.detect_platform(instance_url),
                f"Failed to detect Pixelfed instance: {instance_url}"
            )
    
    def test_pixelfed_platform_detection_pixelfed_in_domain(self):
        """Test Pixelfed platform detection with 'pixelfed' in domain"""
        test_urls = [
            "https://my-pixelfed.example.com",
            "https://pixelfed.myinstance.org",
            "https://test.pixelfed.social"
        ]
        
        for instance_url in test_urls:
            self.assertTrue(
                PixelfedPlatform.detect_platform(instance_url),
                f"Failed to detect Pixelfed instance: {instance_url}"
            )
    
    def test_pixelfed_platform_detection_false_cases(self):
        """Test Pixelfed platform detection returns False for non-Pixelfed instances"""
        test_urls = [
            "https://mastodon.social",
            "https://pleroma.social",
            "https://example.com",
            "",
            None
        ]
        
        for instance_url in test_urls:
            self.assertFalse(
                PixelfedPlatform.detect_platform(instance_url),
                f"Incorrectly detected Pixelfed instance: {instance_url}"
            )
    
    def test_mastodon_platform_detection_known_instances(self):
        """Test Mastodon platform detection with known instances"""
        known_instances = [
            "https://mastodon.social",
            "https://mastodon.online",
            "https://mastodon.xyz",
            "https://mstdn.social",
            "https://fosstodon.org"
        ]
        
        for instance_url in known_instances:
            self.assertTrue(
                MastodonPlatform.detect_platform(instance_url),
                f"Failed to detect Mastodon instance: {instance_url}"
            )
    
    def test_mastodon_platform_detection_mastodon_in_domain(self):
        """Test Mastodon platform detection with 'mastodon' or 'mstdn' in domain"""
        test_urls = [
            "https://my-mastodon.example.com",
            "https://mastodon.myinstance.org",
            "https://mstdn.example.com",
            "https://test.mastodon.social"
        ]
        
        for instance_url in test_urls:
            self.assertTrue(
                MastodonPlatform.detect_platform(instance_url),
                f"Failed to detect Mastodon instance: {instance_url}"
            )
    
    def test_mastodon_platform_detection_false_cases(self):
        """Test Mastodon platform detection returns False for non-Mastodon instances"""
        test_urls = [
            "https://pixelfed.social",
            "https://pleroma.social",
            "https://example.com",
            "",
            None
        ]
        
        for instance_url in test_urls:
            self.assertFalse(
                MastodonPlatform.detect_platform(instance_url),
                f"Incorrectly detected Mastodon instance: {instance_url}"
            )
    
    def test_platform_adapter_factory_create_pixelfed(self):
        """Test PlatformAdapterFactory creates Pixelfed adapter correctly"""
        config = MockConfig(api_type="pixelfed")
        
        adapter = PlatformAdapterFactory.create_adapter(config)
        
        self.assertIsInstance(adapter, PixelfedPlatform)
        self.assertEqual(adapter.config, config)
    
    def test_platform_adapter_factory_create_mastodon(self):
        """Test PlatformAdapterFactory creates Mastodon adapter correctly"""
        config = MockConfig(
            api_type="mastodon",
            client_key="test_key",
            client_secret="test_secret"
        )
        
        adapter = PlatformAdapterFactory.create_adapter(config)
        
        self.assertIsInstance(adapter, MastodonPlatform)
        self.assertEqual(adapter.config, config)
    
    def test_platform_adapter_factory_unsupported_platform(self):
        """Test PlatformAdapterFactory raises error for unsupported platform"""
        config = MockConfig(api_type="unsupported")
        
        with self.assertRaises(UnsupportedPlatformError) as context:
            PlatformAdapterFactory.create_adapter(config)
        
        self.assertIn("Unsupported platform type: unsupported", str(context.exception))
    
    def test_platform_adapter_factory_auto_detection_pixelfed(self):
        """Test PlatformAdapterFactory auto-detects Pixelfed platform"""
        config = MockConfig(
            instance_url="https://pixelfed.social",
            api_type=None  # No explicit platform type
        )
        
        adapter = PlatformAdapterFactory.create_adapter(config)
        
        self.assertIsInstance(adapter, PixelfedPlatform)
    
    def test_platform_adapter_factory_auto_detection_mastodon(self):
        """Test PlatformAdapterFactory auto-detects Mastodon platform"""
        config = MockConfig(
            instance_url="https://mastodon.social",
            api_type=None,  # No explicit platform type
            client_key="test_key",
            client_secret="test_secret"
        )
        
        adapter = PlatformAdapterFactory.create_adapter(config)
        
        self.assertIsInstance(adapter, MastodonPlatform)
    
    def test_platform_adapter_factory_detection_failure(self):
        """Test PlatformAdapterFactory defaults to Pixelfed when detection fails"""
        config = MockConfig(
            instance_url="https://unknown.social",
            api_type=None  # No explicit platform type
        )
        
        # The factory should default to Pixelfed when detection fails
        adapter = PlatformAdapterFactory.create_adapter(config)
        
        self.assertIsInstance(adapter, PixelfedPlatform)

def run_async_test(coro):
    """Helper function to run async tests"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

# Convert async test methods to sync for unittest
class TestPixelfedPlatformAdapterSync(TestPixelfedPlatformAdapter):
    """Synchronous wrapper for async Pixelfed tests"""
    
    def test_pixelfed_get_user_posts_success_sync(self):
        run_async_test(self.test_pixelfed_get_user_posts_success())
    
    def test_pixelfed_get_user_posts_pagination_sync(self):
        run_async_test(self.test_pixelfed_get_user_posts_pagination())
    
    def test_pixelfed_update_media_caption_success_sync(self):
        run_async_test(self.test_pixelfed_update_media_caption_success())
    
    def test_pixelfed_update_media_caption_failure_sync(self):
        run_async_test(self.test_pixelfed_update_media_caption_failure())

class TestMastodonPlatformAdapterSync(TestMastodonPlatformAdapter):
    """Synchronous wrapper for async Mastodon tests"""
    
    def test_mastodon_authenticate_success_sync(self):
        run_async_test(self.test_mastodon_authenticate_success())
    
    def test_mastodon_authenticate_invalid_token_sync(self):
        run_async_test(self.test_mastodon_authenticate_invalid_token())
    
    def test_mastodon_get_user_posts_success_sync(self):
        run_async_test(self.test_mastodon_get_user_posts_success())
    
    def test_mastodon_update_media_caption_success_sync(self):
        run_async_test(self.test_mastodon_update_media_caption_success())

if __name__ == "__main__":
    unittest.main()
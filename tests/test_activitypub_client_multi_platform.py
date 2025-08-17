# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Tests for ActivityPub client multi-platform support.

This module tests the refactored ActivityPubClient to ensure it works correctly
with both Pixelfed and Mastodon platform adapters, maintains existing functionality,
and handles platform-specific error scenarios properly.
"""

import pytest
import asyncio
import httpx
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from dataclasses import dataclass
from typing import Dict, List, Any, Optional

# Import the classes we're testing
from activitypub_client import ActivityPubClient
from activitypub_platforms import (
    PlatformAdapterFactory, 
    PlatformAdapterError, 
    PixelfedPlatform, 
    MastodonPlatform,
    ActivityPubPlatform
)
from config import ActivityPubConfig, RetryConfig, RateLimitConfig


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


class MockPlatformAdapter(ActivityPubPlatform):
    """Mock platform adapter for testing"""
    
    def __init__(self, config, platform_name="mock"):
        super().__init__(config)
        self._platform_name = platform_name
        self.get_user_posts_mock = AsyncMock()
        self.update_media_caption_mock = AsyncMock()
        self.extract_images_from_post_mock = Mock()
        self.get_post_by_id_mock = AsyncMock()
        self.update_post_mock = AsyncMock()
        self.authenticate_mock = AsyncMock()
        self.cleanup_mock = AsyncMock()
    
    @property
    def platform_name(self) -> str:
        return self._platform_name
    
    async def get_user_posts(self, client, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        return await self.get_user_posts_mock(client, user_id, limit)
    
    async def update_media_caption(self, client, image_post_id: str, caption: str) -> bool:
        return await self.update_media_caption_mock(client, image_post_id, caption)
    
    def extract_images_from_post(self, post: Dict[str, Any]) -> List[Dict[str, Any]]:
        return self.extract_images_from_post_mock(post)
    
    async def get_post_by_id(self, client, post_id: str) -> Optional[Dict[str, Any]]:
        return await self.get_post_by_id_mock(client, post_id)
    
    async def update_post(self, client, post_id: str, updated_post: Dict[str, Any]) -> bool:
        return await self.update_post_mock(client, post_id, updated_post)
    
    async def authenticate(self, client) -> bool:
        return await self.authenticate_mock(client)
    
    async def cleanup(self):
        return await self.cleanup_mock()
    
    @classmethod
    def detect_platform(cls, instance_url: str) -> bool:
        return True


class TestActivityPubClientInitialization:
    """Test ActivityPub client initialization with different platforms"""
    
    def test_client_initialization_with_pixelfed_config(self):
        """Test client initialization with Pixelfed configuration"""
        config = MockConfig(api_type="pixelfed")
        
        with patch.object(PlatformAdapterFactory, 'create_adapter') as mock_factory:
            mock_adapter = MockPlatformAdapter(config, "pixelfed")
            mock_factory.return_value = mock_adapter
            
            client = ActivityPubClient(config)
            
            self.assertEqual(client.config, config)
            self.assertEqual(client.platform, mock_adapter)
            mock_factory.assert_called_once_with(config)
    
    def test_client_initialization_with_mastodon_config(self):
        """Test client initialization with Mastodon configuration"""
        config = MockConfig(
            api_type="mastodon",
            client_key="test_key",
            client_secret="test_secret"
        )
        
        with patch.object(PlatformAdapterFactory, 'create_adapter') as mock_factory:
            mock_adapter = MockPlatformAdapter(config, "mastodon")
            mock_factory.return_value = mock_adapter
            
            client = ActivityPubClient(config)
            
            self.assertEqual(client.config, config)
            self.assertEqual(client.platform, mock_adapter)
            mock_factory.assert_called_once_with(config)
    
    def test_client_initialization_failure(self):
        """Test client initialization failure when platform adapter creation fails"""
        config = MockConfig()
        
        with patch.object(PlatformAdapterFactory, 'create_adapter') as mock_factory:
            mock_factory.side_effect = PlatformAdapterError("Test error")
            
            with self.assertRaisesRegex(PlatformAdapterError, r"Failed to initialize platform adapter"):
                ActivityPubClient(config)


class TestActivityPubClientMethods:
    """Test ActivityPub client methods with platform adapters"""
    
    def mock_client(self):
        """Create a mock client for testing"""
        config = MockConfig()
        
        with patch.object(PlatformAdapterFactory, 'create_adapter') as mock_factory:
            mock_adapter = MockPlatformAdapter(config)
            mock_factory.return_value = mock_adapter
            
            client = ActivityPubClient(config)
            return client, mock_adapter
    
    async def test_get_user_posts_success(self):
        """Test successful user posts retrieval"""
        client, mock_adapter = self.mock_client()
        
        expected_posts = [
            {"id": "1", "type": "Note", "content": "Test post 1"},
            {"id": "2", "type": "Note", "content": "Test post 2"}
        ]
        mock_adapter.get_user_posts_mock.return_value = expected_posts
        
        async with client:
            posts = await client.get_user_posts("testuser", 10)
        
        self.assertEqual(posts, expected_posts)
        mock_adapter.get_user_posts_mock.assert_called_once_with(client, "testuser", 10)
    
    async def test_get_user_posts_platform_error(self):
        """Test user posts retrieval with platform adapter error"""
        client, mock_adapter = self.mock_client()
        
        mock_adapter.get_user_posts_mock.side_effect = PlatformAdapterError("Test error")
        
        async with client:
            with self.assertRaisesRegex(PlatformAdapterError, r"Test error"):
                await client.get_user_posts("testuser", 10)
    
    async def test_get_user_posts_generic_error(self):
        """Test user posts retrieval with generic error"""
        client, mock_adapter = self.mock_client()
        
        mock_adapter.get_user_posts_mock.side_effect = Exception("Generic error")
        
        async with client:
            with self.assertRaisesRegex(PlatformAdapterError, r"Failed to retrieve posts for user testuser"):
                await client.get_user_posts("testuser", 10)
    
    async def test_update_media_caption_success(self):
        """Test successful media caption update"""
        client, mock_adapter = self.mock_client()
        
        mock_adapter.update_media_caption_mock.return_value = True
        
        async with client:
            result = await client.update_media_caption("media123", "Test caption")
        
        self.assertTrue(result)
        mock_adapter.update_media_caption_mock.assert_called_once_with(client, "media123", "Test caption")
    
    async def test_update_media_caption_empty_id(self):
        """Test media caption update with empty image_post_id"""
        client, mock_adapter = self.mock_client()
        
        async with client:
            result = await client.update_media_caption("", "Test caption")
        
        self.assertFalse(result)
        mock_adapter.update_media_caption_mock.assert_not_called()
    
    async def test_update_media_caption_platform_error(self):
        """Test media caption update with platform adapter error"""
        client, mock_adapter = self.mock_client()
        
        mock_adapter.update_media_caption_mock.side_effect = PlatformAdapterError("Test error")
        
        async with client:
            with self.assertRaisesRegex(PlatformAdapterError, r"Test error"):
                await client.update_media_caption("media123", "Test caption")
    
    def test_extract_images_from_post_success(self, mock_client):
        """Test successful image extraction from post"""
        client, mock_adapter = self.mock_client()
        
        test_post = {"id": "1", "attachment": [{"type": "Document", "url": "test.jpg"}]}
        expected_images = [{"url": "test.jpg", "mediaType": "image/jpeg"}]
        mock_adapter.extract_images_from_post_mock.return_value = expected_images
        
        images = client.extract_images_from_post(test_post)
        
        self.assertEqual(images, expected_images)
        mock_adapter.extract_images_from_post_mock.assert_called_once_with(test_post)
    
    def test_extract_images_from_post_error(self, mock_client):
        """Test image extraction with error"""
        client, mock_adapter = self.mock_client()
        
        test_post = {"id": "1", "attachment": []}
        mock_adapter.extract_images_from_post_mock.side_effect = Exception("Test error")
        
        with self.assertRaisesRegex(PlatformAdapterError, r"Failed to extract images from post"):
            client.extract_images_from_post(test_post)
    
    async def test_get_post_by_id_success(self):
        """Test successful post retrieval by ID"""
        client, mock_adapter = self.mock_client()
        
        expected_post = {"id": "1", "type": "Note", "content": "Test post"}
        mock_adapter.get_post_by_id_mock.return_value = expected_post
        
        async with client:
            post = await client.get_post_by_id("1")
        
        self.assertEqual(post, expected_post)
        mock_adapter.get_post_by_id_mock.assert_called_once_with(client, "1")
    
    async def test_get_post_by_id_not_found(self):
        """Test post retrieval when post not found"""
        client, mock_adapter = self.mock_client()
        
        mock_adapter.get_post_by_id_mock.return_value = None
        
        async with client:
            post = await client.get_post_by_id("nonexistent")
        
        self.assertIsNone(post)
        mock_adapter.get_post_by_id_mock.assert_called_once_with(client, "nonexistent")
    
    async def test_update_post_success(self):
        """Test successful post update"""
        client, mock_adapter = self.mock_client()
        
        mock_adapter.update_post_mock.return_value = True
        updated_post = {"content": "Updated content"}
        
        async with client:
            result = await client.update_post("1", updated_post)
        
        self.assertTrue(result)
        mock_adapter.update_post_mock.assert_called_once_with(client, "1", updated_post)
    
    async def test_authenticate_success(self):
        """Test successful authentication"""
        client, mock_adapter = self.mock_client()
        
        mock_adapter.authenticate_mock.return_value = True
        
        async with client:
            result = await client.authenticate()
        
        self.assertTrue(result)
        mock_adapter.authenticate_mock.assert_called_once_with(client)
    
    async def test_authenticate_no_method(self):
        """Test authentication when platform doesn't have authenticate method"""
        client, mock_adapter = self.mock_client()
        
        # Remove the authenticate method from the mock
        delattr(mock_adapter, 'authenticate')
        
        async with client:
            result = await client.authenticate()
        
        self.assertTrue(result)  # Should return True when no authentication required


class TestActivityPubClientPlatformSpecific:
    """Test platform-specific functionality"""
    
    def test_get_platform_name(self):
        """Test getting platform name"""
        config = MockConfig()
        
        with patch.object(PlatformAdapterFactory, 'create_adapter') as mock_factory:
            mock_adapter = MockPlatformAdapter(config, "test_platform")
            mock_factory.return_value = mock_adapter
            
            client = ActivityPubClient(config)
            self.assertEqual(client.get_platform_name(), "test_platform")
    
    def test_get_platform_info(self):
        """Test getting platform information"""
        config = MockConfig(api_type="mastodon")
        
        with patch.object(PlatformAdapterFactory, 'create_adapter') as mock_factory:
            mock_adapter = MockPlatformAdapter(config, "mastodon")
            mock_factory.return_value = mock_adapter
            
            client = ActivityPubClient(config)
            info = client.get_platform_info()
            
            expected_info = {
                "platform_name": "mastodon",
                "platform_class": "MockPlatformAdapter",
                "instance_url": "https://test.example.com",
                "api_type": "mastodon"
            }
            self.assertEqual(info, expected_info)


class TestActivityPubClientCleanup:
    """Test client cleanup and resource management"""
    
    async def test_cleanup_with_platform_cleanup(self):
        """Test cleanup when platform adapter has cleanup method"""
        config = MockConfig()
        
        with patch.object(PlatformAdapterFactory, 'create_adapter') as mock_factory:
            mock_adapter = MockPlatformAdapter(config)
            mock_factory.return_value = mock_adapter
            
            client = ActivityPubClient(config)
            
            async with client:
                pass  # Context manager should call cleanup
            
            mock_adapter.cleanup_mock.assert_called_once()
    
    async def test_cleanup_without_platform_cleanup(self):
        """Test cleanup when platform adapter doesn't have cleanup method"""
        config = MockConfig()
        
        with patch.object(PlatformAdapterFactory, 'create_adapter') as mock_factory:
            mock_adapter = MockPlatformAdapter(config)
            # Remove cleanup method
            delattr(mock_adapter, 'cleanup')
            mock_factory.return_value = mock_adapter
            
            client = ActivityPubClient(config)
            
            # Should not raise an error
            async with client:
                pass
    
    async def test_cleanup_with_platform_cleanup_error(self):
        """Test cleanup when platform cleanup raises an error"""
        config = MockConfig()
        
        with patch.object(PlatformAdapterFactory, 'create_adapter') as mock_factory:
            mock_adapter = MockPlatformAdapter(config)
            mock_adapter.cleanup_mock.side_effect = Exception("Cleanup error")
            mock_factory.return_value = mock_adapter
            
            client = ActivityPubClient(config)
            
            # Should not raise an error, just log a warning
            async with client:
                pass
            
            mock_adapter.cleanup_mock.assert_called_once()


class TestActivityPubClientRetryAndStats:
    """Test retry mechanisms and statistics"""
    
    def test_get_platform_specific_retry_info(self):
        """Test getting platform-specific retry information"""
        config = MockConfig()
        
        with patch.object(PlatformAdapterFactory, 'create_adapter') as mock_factory:
            mock_adapter = MockPlatformAdapter(config, "pixelfed")
            mock_factory.return_value = mock_adapter
            
            client = ActivityPubClient(config)
            
            with patch('activitypub_client.get_retry_stats_detailed') as mock_stats:
                mock_stats.return_value = {
                    "summary": {
                        "retried_operations": 5,
                        "successful_retries": 4
                    },
                    "by_endpoint": {
                        "/api/v1/statuses": 10,
                        "/api/v1/media": 5
                    },
                    "by_status_code": {
                        "429": 2,
                        "500": 1
                    },
                    "by_exception": {
                        "TimeoutError": 2
                    }
                }
                
                stats = client.get_platform_specific_retry_info()
                
                self.assertTrue("pixelfed_api_calls" in stats)
                self.assertEqual(stats["pixelfed_api_calls"]["total"], 15  )# 10 + 5
                self.assertEqual(stats["pixelfed_api_calls"]["retried"], 5)
                self.assertEqual(stats["pixelfed_api_calls"]["success_rate"], 80.0  )# 4/5 * 100
                self.assertEqual(stats["endpoints"], {"/api/v1/statuses": 10, "/api/v1/media": 5})
                self.assertEqual(stats["status_codes"], {"429": 2, "500": 1})
                self.assertEqual(stats["common_errors"], {"TimeoutError": 2})


class TestActivityPubClientRegressionTests:
    """Regression tests to ensure existing functionality is maintained"""
    
    async def test_pixelfed_functionality_maintained(self):
        """Test that existing Pixelfed functionality is maintained"""
        config = MockConfig(api_type="pixelfed")
        
        with patch.object(PlatformAdapterFactory, 'create_adapter') as mock_factory:
            # Use a real PixelfedPlatform mock to ensure interface compatibility
            mock_adapter = Mock(spec=PixelfedPlatform)
            mock_adapter.platform_name = "pixelfed"
            mock_adapter.get_user_posts = AsyncMock(return_value=[])
            mock_adapter.update_media_caption = AsyncMock(return_value=True)
            mock_adapter.extract_images_from_post = Mock(return_value=[])
            mock_adapter.get_post_by_id = AsyncMock(return_value=None)
            mock_adapter.update_post = AsyncMock(return_value=True)
            mock_factory.return_value = mock_adapter
            
            client = ActivityPubClient(config)
            
            async with client:
                # Test all methods work
                posts = await client.get_user_posts("user", 10)
                self.assertEqual(posts, [])
                
                result = await client.update_media_caption("media", "caption")
                self.assertTrue(result)
                
                images = client.extract_images_from_post({"attachment": []})
                self.assertEqual(images, [])
                
                post = await client.get_post_by_id("1")
                self.assertIsNone(post)
                
                update_result = await client.update_post("1", {})
                self.assertTrue(update_result)
    
    async def test_mastodon_functionality_works(self):
        """Test that Mastodon functionality works correctly"""
        config = MockConfig(
            api_type="mastodon",
            client_key="test_key",
            client_secret="test_secret"
        )
        
        with patch.object(PlatformAdapterFactory, 'create_adapter') as mock_factory:
            # Use a real MastodonPlatform mock to ensure interface compatibility
            mock_adapter = Mock(spec=MastodonPlatform)
            mock_adapter.platform_name = "mastodon"
            mock_adapter.get_user_posts = AsyncMock(return_value=[])
            mock_adapter.update_media_caption = AsyncMock(return_value=True)
            mock_adapter.extract_images_from_post = Mock(return_value=[])
            mock_adapter.get_post_by_id = AsyncMock(return_value=None)
            mock_adapter.update_post = AsyncMock(return_value=True)
            mock_adapter.authenticate = AsyncMock(return_value=True)
            mock_factory.return_value = mock_adapter
            
            client = ActivityPubClient(config)
            
            async with client:
                # Test authentication
                auth_result = await client.authenticate()
                self.assertTrue(auth_result)
                
                # Test all methods work
                posts = await client.get_user_posts("user", 10)
                self.assertEqual(posts, [])
                
                result = await client.update_media_caption("media", "caption")
                self.assertTrue(result)
                
                images = client.extract_images_from_post({"attachment": []})
                self.assertEqual(images, [])


if __name__ == "__main__":
    unittest.main()
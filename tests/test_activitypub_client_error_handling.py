# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Tests for ActivityPub client error handling and retry logic.

This module tests error propagation, retry mechanisms, and platform-specific
error handling scenarios for both Pixelfed and Mastodon platforms.
"""

import unittest
import asyncio
import httpx
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from dataclasses import dataclass
from typing import Dict, List, Any, Optional

from activitypub_client import ActivityPubClient
from activitypub_platforms import (
    PlatformAdapterFactory,
    PlatformAdapterError,
    PixelfedPlatform,
    MastodonPlatform
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

class TestActivityPubClientErrorHandling(unittest.TestCase):
    """Test error handling in ActivityPub client"""
    
    def setUp(self):
        """Set up test fixtures"""
        pass
    
    def mock_pixelfed_client(self):
        """Create a mock client with Pixelfed adapter"""
        config = MockConfig(api_type="pixelfed")
        
        with patch.object(PlatformAdapterFactory, 'create_adapter') as mock_factory:
            mock_adapter = Mock(spec=PixelfedPlatform)
            mock_adapter.platform_name = "pixelfed"
            mock_factory.return_value = mock_adapter
            
            client = ActivityPubClient(config)
            return client, mock_adapter
    
    def mock_mastodon_client(self):
        """Create a mock client with Mastodon adapter"""
        config = MockConfig(
            api_type="mastodon",
            client_key="test_key",
            client_secret="test_secret"
        )
        
        with patch.object(PlatformAdapterFactory, 'create_adapter') as mock_factory:
            mock_adapter = Mock(spec=MastodonPlatform)
            mock_adapter.platform_name = "mastodon"
            mock_factory.return_value = mock_adapter
            
            client = ActivityPubClient(config)
            return client, mock_adapter
    
    async def test_get_user_posts_http_error(self):
        """Test get_user_posts with HTTP error"""
        client, mock_adapter = self.mock_pixelfed_client()
        
        # Simulate HTTP error
        http_error = httpx.HTTPStatusError(
            "404 Not Found",
            request=Mock(),
            response=Mock(status_code=404)
        )
        mock_adapter.get_user_posts = AsyncMock(side_effect=http_error)
        
        async with client:
            with self.assertRaisesRegex(PlatformAdapterError, "Failed to retrieve posts for user testuser"):
                await client.get_user_posts("testuser", 10)
    
    async def test_get_user_posts_timeout_error(self):
        """Test get_user_posts with timeout error"""
        client, mock_adapter = self.mock_mastodon_client()
        
        # Simulate timeout error
        timeout_error = httpx.TimeoutException("Request timed out")
        mock_adapter.get_user_posts = AsyncMock(side_effect=timeout_error)
        
        async with client:
            with self.assertRaisesRegex(PlatformAdapterError, r"Failed to retrieve posts for user testuser"):
                await client.get_user_posts("testuser", 10)
    
    async def test_get_user_posts_connection_error(self):
        """Test get_user_posts with connection error"""
        client, mock_adapter = self.mock_pixelfed_client()
        
        # Simulate connection error
        connection_error = httpx.ConnectError("Connection failed")
        mock_adapter.get_user_posts = AsyncMock(side_effect=connection_error)
        
        async with client:
            with self.assertRaisesRegex(PlatformAdapterError, r"Failed to retrieve posts for user testuser"):
                await client.get_user_posts("testuser", 10)
    
    async def test_update_media_caption_platform_error_propagation(self):
        """Test that platform adapter errors are properly propagated"""
        client, mock_adapter = self.mock_mastodon_client()
        
        # Simulate platform adapter error
        platform_error = PlatformAdapterError("Mastodon API error")
        mock_adapter.update_media_caption = AsyncMock(side_effect=platform_error)
        
        async with client:
            with self.assertRaisesRegex(PlatformAdapterError, r"Mastodon API error"):
                await client.update_media_caption("media123", "Test caption")
    
    async def test_update_media_caption_authentication_error(self):
        """Test update_media_caption with authentication error"""
        client, mock_adapter = self.mock_mastodon_client()
        
        # Simulate authentication error
        auth_error = httpx.HTTPStatusError(
            "401 Unauthorized",
            request=Mock(),
            response=Mock(status_code=401)
        )
        mock_adapter.update_media_caption = AsyncMock(side_effect=auth_error)
        
        async with client:
            with self.assertRaisesRegex(PlatformAdapterError, r"Failed to update media caption for media123"):
                await client.update_media_caption("media123", "Test caption")
    
    async def test_get_post_by_id_rate_limit_error(self):
        """Test get_post_by_id with rate limit error"""
        client, mock_adapter = self.mock_pixelfed_client()
        
        # Simulate rate limit error
        rate_limit_error = httpx.HTTPStatusError(
            "429 Too Many Requests",
            request=Mock(),
            response=Mock(status_code=429)
        )
        mock_adapter.get_post_by_id = AsyncMock(side_effect=rate_limit_error)
        
        async with client:
            with self.assertRaisesRegex(PlatformAdapterError, r"Failed to retrieve post post123"):
                await client.get_post_by_id("post123")
    
    async def test_update_post_server_error(self):
        """Test update_post with server error"""
        client, mock_adapter = self.mock_mastodon_client()
        
        # Simulate server error
        server_error = httpx.HTTPStatusError(
            "500 Internal Server Error",
            request=Mock(),
            response=Mock(status_code=500)
        )
        mock_adapter.update_post = AsyncMock(side_effect=server_error)
        
        async with client:
            with self.assertRaisesRegex(PlatformAdapterError, r"Failed to update post post123"):
                await client.update_post("post123", {"content": "Updated"})
    
    def test_extract_images_from_post_json_decode_error(self, mock_pixelfed_client):
        """Test extract_images_from_post with JSON decode error"""
        client, mock_adapter = self.mock_pixelfed_client()
        
        # Simulate JSON decode error
        json_error = ValueError("Invalid JSON")
        mock_adapter.extract_images_from_post = Mock(side_effect=json_error)
        
        with self.assertRaisesRegex(PlatformAdapterError, r"Failed to extract images from post"):
            client.extract_images_from_post({"attachment": []})
    
    def test_extract_images_from_post_key_error(self, mock_mastodon_client):
        """Test extract_images_from_post with key error"""
        client, mock_adapter = self.mock_mastodon_client()
        
        # Simulate key error
        key_error = KeyError("attachment")
        mock_adapter.extract_images_from_post = Mock(side_effect=key_error)
        
        with self.assertRaisesRegex(PlatformAdapterError, r"Failed to extract images from post"):
            client.extract_images_from_post({})

class TestActivityPubClientRetryLogic(unittest.TestCase):
    """Test retry logic for different platforms"""
    
    def mock_client_with_retry(self):
        """Create a mock client with retry configuration"""
        retry_config = RetryConfig(
            max_attempts=3,
            base_delay=0.1,
            max_delay=1.0,
            backoff_factor=2.0
        )
        config = MockConfig(api_type="pixelfed")
        config.retry = retry_config
        
        with patch.object(PlatformAdapterFactory, 'create_adapter') as mock_factory:
            mock_adapter = Mock(spec=PixelfedPlatform)
            mock_adapter.platform_name = "pixelfed"
            mock_factory.return_value = mock_adapter
            
            client = ActivityPubClient(config)
            return client, mock_adapter
    
    async def test_retry_on_temporary_failure(self):
        """Test retry logic on temporary failures"""
        client, mock_adapter = self.mock_client_with_retry()
        
        # First two calls fail, third succeeds
        mock_adapter.get_user_posts = AsyncMock(side_effect=[
            httpx.TimeoutException("Timeout"),
            httpx.ConnectError("Connection failed"),
            [{"id": "1", "type": "Note"}]  # Success on third attempt
        ])
        
        async with client:
            posts = await client.get_user_posts("testuser", 10)
        
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0]["id"], "1")
        self.assertEqual(mock_adapter.get_user_posts.call_count, 3)
    
    async def test_retry_exhaustion(self):
        """Test behavior when retry attempts are exhausted"""
        client, mock_adapter = self.mock_client_with_retry()
        
        # All attempts fail
        mock_adapter.update_media_caption = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
        
        async with client:
            with self.assertRaises(PlatformAdapterError):
                await client.update_media_caption("media123", "Test caption")
        
        # Should have tried max_attempts times
        self.assertEqual(mock_adapter.update_media_caption.call_count, 3)
    
    async def test_no_retry_on_client_error(self):
        """Test that client errors (4xx) are not retried"""
        client, mock_adapter = self.mock_client_with_retry()
        
        # 404 error should not be retried
        client_error = httpx.HTTPStatusError(
            "404 Not Found",
            request=Mock(),
            response=Mock(status_code=404)
        )
        mock_adapter.get_post_by_id = AsyncMock(side_effect=client_error)
        
        async with client:
            with self.assertRaises(PlatformAdapterError):
                await client.get_post_by_id("nonexistent")
        
        # Should only be called once (no retries)
        self.assertEqual(mock_adapter.get_post_by_id.call_count, 1)
    
    async def test_retry_on_server_error(self):
        """Test that server errors (5xx) are retried"""
        client, mock_adapter = self.mock_client_with_retry()
        
        # 500 error should be retried
        server_error = httpx.HTTPStatusError(
            "500 Internal Server Error",
            request=Mock(),
            response=Mock(status_code=500)
        )
        mock_adapter.update_post = AsyncMock(side_effect=server_error)
        
        async with client:
            with self.assertRaises(PlatformAdapterError):
                await client.update_post("post123", {"content": "Updated"})
        
        # Should have tried max_attempts times
        self.assertEqual(mock_adapter.update_post.call_count, 3)

class TestActivityPubClientPlatformSpecificErrors(unittest.TestCase):
    """Test platform-specific error scenarios"""
    
    async def test_pixelfed_specific_error_handling(self):
        """Test Pixelfed-specific error handling"""
        config = MockConfig(api_type="pixelfed")
        
        with patch.object(PlatformAdapterFactory, 'create_adapter') as mock_factory:
            mock_adapter = Mock(spec=PixelfedPlatform)
            mock_adapter.platform_name = "pixelfed"
            
            # Simulate Pixelfed-specific error
            pixelfed_error = PlatformAdapterError("Pixelfed media not found")
            mock_adapter.update_media_caption = AsyncMock(side_effect=pixelfed_error)
            mock_factory.return_value = mock_adapter
            
            client = ActivityPubClient(config)
            
            async with client:
                with self.assertRaisesRegex(PlatformAdapterError, r"Pixelfed media not found"):
                    await client.update_media_caption("media123", "Test caption")
    
    async def test_mastodon_authentication_error_handling(self):
        """Test Mastodon authentication error handling"""
        config = MockConfig(
            api_type="mastodon",
            client_key="test_key",
            client_secret="test_secret"
        )
        
        with patch.object(PlatformAdapterFactory, 'create_adapter') as mock_factory:
            mock_adapter = Mock(spec=MastodonPlatform)
            mock_adapter.platform_name = "mastodon"
            
            # Simulate Mastodon authentication error
            auth_error = PlatformAdapterError("Invalid Mastodon credentials")
            mock_adapter.authenticate = AsyncMock(side_effect=auth_error)
            mock_factory.return_value = mock_adapter
            
            client = ActivityPubClient(config)
            
            async with client:
                with self.assertRaises(Exception):  # Should propagate the authentication error
                    await client.authenticate()
    
    async def test_mastodon_oauth_token_expired(self):
        """Test handling of expired OAuth tokens in Mastodon"""
        config = MockConfig(
            api_type="mastodon",
            client_key="test_key",
            client_secret="test_secret"
        )
        
        with patch.object(PlatformAdapterFactory, 'create_adapter') as mock_factory:
            mock_adapter = Mock(spec=MastodonPlatform)
            mock_adapter.platform_name = "mastodon"
            
            # Simulate expired token error
            token_error = httpx.HTTPStatusError(
                "401 Unauthorized: Token expired",
                request=Mock(),
                response=Mock(status_code=401, text="Token expired")
            )
            mock_adapter.get_user_posts = AsyncMock(side_effect=token_error)
            mock_factory.return_value = mock_adapter
            
            client = ActivityPubClient(config)
            
            async with client:
                with self.assertRaisesRegex(PlatformAdapterError, r"Failed to retrieve posts for user testuser"):
                    await client.get_user_posts("testuser", 10)
    
    async def test_pixelfed_media_not_found_error(self):
        """Test handling of media not found errors in Pixelfed"""
        config = MockConfig(api_type="pixelfed")
        
        with patch.object(PlatformAdapterFactory, 'create_adapter') as mock_factory:
            mock_adapter = Mock(spec=PixelfedPlatform)
            mock_adapter.platform_name = "pixelfed"
            
            # Simulate media not found error
            not_found_error = httpx.HTTPStatusError(
                "404 Not Found: Media not found",
                request=Mock(),
                response=Mock(status_code=404, text="Media not found")
            )
            mock_adapter.update_media_caption = AsyncMock(side_effect=not_found_error)
            mock_factory.return_value = mock_adapter
            
            client = ActivityPubClient(config)
            
            async with client:
                with self.assertRaisesRegex(PlatformAdapterError, r"Failed to update media caption for media123"):
                    await client.update_media_caption("media123", "Test caption")

class TestActivityPubClientConcurrentErrors(unittest.TestCase):
    """Test error handling in concurrent scenarios"""
    
    async def test_concurrent_requests_with_mixed_results(self):
        """Test concurrent requests where some succeed and some fail"""
        config = MockConfig(api_type="pixelfed")
        
        with patch.object(PlatformAdapterFactory, 'create_adapter') as mock_factory:
            mock_adapter = Mock(spec=PixelfedPlatform)
            mock_adapter.platform_name = "pixelfed"
            
            # Set up different responses for different calls
            async def mock_update_media_caption(client, media_id, caption):
                if media_id == "success":
                    return True
                elif media_id == "failure":
                    raise PlatformAdapterError("Update failed")
                else:
                    raise httpx.TimeoutException("Timeout")
            
            mock_adapter.update_media_caption = mock_update_media_caption
            mock_factory.return_value = mock_adapter
            
            client = ActivityPubClient(config)
            
            async with client:
                # Run concurrent requests
                tasks = [
                    client.update_media_caption("success", "Caption 1"),
                    asyncio.create_task(self._expect_error(client, "failure", "Caption 2")),
                    asyncio.create_task(self._expect_error(client, "timeout", "Caption 3"))
                ]
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # First should succeed
                self.assertTrue(results[0])
                
                # Second and third should be exceptions
                self.assertTrue(isinstance(results[1], PlatformAdapterError))
                self.assertTrue(isinstance(results[2], PlatformAdapterError))
    
    async def _expect_error(self, client, media_id, caption):
        """Helper method to expect an error"""
        try:
            await client.update_media_caption(media_id, caption)
            self.fail("Expected an error but none was raised")
        except PlatformAdapterError as e:
            return e

if __name__ == "__main__":
    unittest.main()
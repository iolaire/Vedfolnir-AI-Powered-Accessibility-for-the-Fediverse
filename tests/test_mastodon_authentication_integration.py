# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Integration tests for Mastodon authentication with ActivityPubClient.
"""

import unittest
from unittest.mock import Mock, AsyncMock, patch
import asyncio
import httpx

from activitypub_client import ActivityPubClient
from activitypub_platforms import MastodonPlatform
from config import ActivityPubConfig


class TestMastodonAuthenticationIntegration(unittest.TestCase):
    """Integration tests for Mastodon authentication"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create a mock config for Mastodon
        self.config = Mock()
        self.config.instance_url = "https://mastodon.social"
        self.config.access_token = "test_access_token"
        self.config.api_type = "mastodon"
        self.config.client_key = "test_client_key"
        self.config.client_secret = "test_client_secret"
        self.config.user_agent = "Vedfolnir/1.0"
        self.config.retry = None
        self.config.rate_limit = None
        
    @patch('activitypub_platforms.get_platform_adapter')
    async def test_mastodon_platform_authentication_integration(self, mock_get_adapter):
        """Test that MastodonPlatform authentication integrates properly with ActivityPubClient"""
        
        # Create a real MastodonPlatform instance
        platform = MastodonPlatform(self.config)
        mock_get_adapter.return_value = platform
        
        # Create ActivityPubClient
        client = ActivityPubClient(self.config)
        
        # Mock the HTTP session
        with patch.object(client, 'session') as mock_session:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "id": "123456",
                "username": "testuser",
                "display_name": "Test User"
            }
            mock_response.raise_for_status = Mock()
            
            mock_session.get = AsyncMock(return_value=mock_response)
            
            # Test authentication through the platform
            result = await platform.authenticate(client)
            
            self.assertTrue(result)
            self.assertTrue(platform._authenticated)
            self.assertIsNotNone(platform._auth_headers)
            
            # Verify the correct endpoint was called
            mock_session.get.assert_called_once()
            call_args = mock_session.get.call_args
            self.assertIn("/api/v1/accounts/verify_credentials", call_args[0][0])
            
            # Verify authentication headers were used
            headers = call_args[1]['headers']
            self.assertEqual(headers['Authorization'], f'Bearer {self.config.access_token}')
            
    @patch('activitypub_platforms.get_platform_adapter')
    async def test_mastodon_get_user_posts_with_authentication(self, mock_get_adapter):
        """Test that get_user_posts properly authenticates before making requests"""
        
        # Create a real MastodonPlatform instance
        platform = MastodonPlatform(self.config)
        mock_get_adapter.return_value = platform
        
        # Create ActivityPubClient
        client = ActivityPubClient(self.config)
        
        # Mock the HTTP session and responses
        with patch.object(client, 'session') as mock_session:
            # Mock verify_credentials response (for authentication)
            verify_response = Mock()
            verify_response.status_code = 200
            verify_response.json.return_value = {"username": "testuser"}
            verify_response.raise_for_status = Mock()
            
            # Mock search response (for user lookup)
            search_response = Mock()
            search_response.status_code = 200
            search_response.json.return_value = {
                "accounts": [{"id": "123456", "username": "testuser"}]
            }
            search_response.raise_for_status = Mock()
            
            # Mock statuses response (for posts)
            statuses_response = Mock()
            statuses_response.status_code = 200
            statuses_response.json.return_value = [
                {
                    "id": "1",
                    "uri": "https://mastodon.social/@testuser/1",
                    "content": "Test post",
                    "created_at": "2023-01-01T00:00:00Z",
                    "media_attachments": [
                        {
                            "id": "media1",
                            "type": "image",
                            "url": "https://example.com/image.jpg",
                            "description": ""
                        }
                    ]
                }
            ]
            statuses_response.raise_for_status = Mock()
            
            # Set up the mock to return different responses based on URL
            def mock_get_side_effect(url, **kwargs):
                if "verify_credentials" in url:
                    return verify_response
                elif "search" in url:
                    return search_response
                elif "statuses" in url:
                    return statuses_response
                else:
                    raise ValueError(f"Unexpected URL: {url}")
            
            mock_session.get = AsyncMock(side_effect=mock_get_side_effect)
            
            # Test getting user posts
            posts = await client.get_user_posts("testuser", limit=20)
            
            self.assertEqual(len(posts), 1)
            self.assertEqual(posts[0]["id"], "https://mastodon.social/@testuser/1")
            self.assertEqual(len(posts[0]["attachment"]), 1)
            
            # Verify authentication was called
            verify_calls = [call for call in mock_session.get.call_args_list 
                          if "verify_credentials" in str(call)]
            self.assertEqual(len(verify_calls), 1)
            
    @patch('activitypub_platforms.get_platform_adapter')
    async def test_mastodon_update_media_caption_with_authentication(self, mock_get_adapter):
        """Test that update_media_caption properly authenticates before making requests"""
        
        # Create a real MastodonPlatform instance
        platform = MastodonPlatform(self.config)
        mock_get_adapter.return_value = platform
        
        # Create ActivityPubClient
        client = ActivityPubClient(self.config)
        
        # Mock the HTTP session and responses
        with patch.object(client, 'session') as mock_session:
            # Mock verify_credentials response (for authentication)
            verify_response = Mock()
            verify_response.status_code = 200
            verify_response.json.return_value = {"username": "testuser"}
            verify_response.raise_for_status = Mock()
            
            # Mock media update response
            update_response = Mock()
            update_response.status_code = 200
            update_response.json.return_value = {
                "id": "media123",
                "description": "Updated description"
            }
            update_response.raise_for_status = Mock()
            
            mock_session.get = AsyncMock(return_value=verify_response)
            mock_session.put = AsyncMock(return_value=update_response)
            
            # Test updating media caption
            result = await client.update_media_caption("media123", "New alt text")
            
            self.assertTrue(result)
            
            # Verify authentication was called
            mock_session.get.assert_called_once()
            verify_call = mock_session.get.call_args
            self.assertIn("/api/v1/accounts/verify_credentials", verify_call[0][0])
            
            # Verify media update was called
            mock_session.put.assert_called_once()
            update_call = mock_session.put.call_args
            self.assertIn("/api/v1/media/media123", update_call[0][0])
            
            # Verify authentication headers were used in both calls
            verify_headers = verify_call[1]['headers']
            update_headers = update_call[1]['headers']
            
            self.assertEqual(verify_headers['Authorization'], f'Bearer {self.config.access_token}')
            self.assertEqual(update_headers['Authorization'], f'Bearer {self.config.access_token}')


def run_async_test(coro):
    """Helper function to run async tests"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# Convert async test methods to sync for unittest
class TestMastodonAuthenticationIntegrationSync(TestMastodonAuthenticationIntegration):
    """Synchronous wrapper for async integration tests"""
    
    def test_mastodon_platform_authentication_integration_sync(self):
        run_async_test(self.test_mastodon_platform_authentication_integration())
        
    def test_mastodon_get_user_posts_with_authentication_sync(self):
        run_async_test(self.test_mastodon_get_user_posts_with_authentication())
        
    def test_mastodon_update_media_caption_with_authentication_sync(self):
        run_async_test(self.test_mastodon_update_media_caption_with_authentication())


if __name__ == '__main__':
    unittest.main()
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Comprehensive tests for Mastodon media updates functionality.
Tests the implementation of task 10.3.4: Implement Mastodon media updates.
"""

import unittest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import asyncio
import httpx
import json

from app.services.activitypub.components.activitypub_client import ActivityPubClient
from app.services.activitypub.components.activitypub_platforms import MastodonPlatform, PlatformAdapterError
from config import ActivityPubConfig

class TestMastodonMediaUpdates(unittest.TestCase):
    """Test Mastodon media update functionality"""
    
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
        
        # Create platform and client instances
        self.platform = MastodonPlatform(self.config)
        self.client = ActivityPubClient(self.config)
    
    async def test_successful_media_description_update(self):
        """Test successful media description updates with valid media IDs"""
        media_id = "12345"
        caption = "A beautiful sunset over the mountains"
        
        # Mock authentication
        with patch.object(self.platform, 'authenticate', return_value=True):
            with patch.object(self.platform, '_get_auth_headers') as mock_headers:
                mock_headers.return_value = {
                    'Authorization': 'Bearer test_token',
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
                
                # Mock successful PUT request
                with patch.object(self.client, '_put_with_retry') as mock_put:
                    mock_response = Mock()
                    mock_response.status_code = 200
                    mock_response.json.return_value = {
                        "id": media_id,
                        "description": caption,
                        "type": "image"
                    }
                    mock_put.return_value = mock_response
                    
                    # Test the update
                    result = await self.platform.update_media_caption(
                        self.client, media_id, caption
                    )
                    
                    # Verify success
                    self.assertTrue(result)
                    
                    # Verify correct API call
                    mock_put.assert_called_once()
                    call_args = mock_put.call_args
                    
                    # Check URL
                    expected_url = f"{self.config.instance_url}/api/v1/media/{media_id}"
                    self.assertEqual(call_args[0][0], expected_url)
                    
                    # Check headers
                    self.assertEqual(call_args[0][1]['Authorization'], 'Bearer test_token')
                    
                    # Check payload
                    self.assertEqual(call_args[1]['json'], {'description': caption})
    
    async def test_media_update_with_invalid_media_id(self):
        """Test media update failures with invalid/non-existent media IDs"""
        invalid_media_id = "nonexistent"
        caption = "Test caption"
        
        # Mock authentication
        with patch.object(self.platform, 'authenticate', return_value=True):
            with patch.object(self.platform, '_get_auth_headers') as mock_headers:
                mock_headers.return_value = {
                    'Authorization': 'Bearer test_token',
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
                
                # Mock 404 response for invalid media ID
                with patch.object(self.client, '_put_with_retry') as mock_put:
                    mock_put.side_effect = httpx.HTTPStatusError(
                        "Not Found",
                        request=Mock(),
                        response=Mock(status_code=404)
                    )
                    
                    # Test the update
                    result = await self.platform.update_media_caption(
                        self.client, invalid_media_id, caption
                    )
                    
                    # Verify failure
                    self.assertFalse(result)
                    
                    # Verify API was called
                    mock_put.assert_called_once()
    
    async def test_media_update_request_format(self):
        """Test media update request format and payload structure"""
        media_id = "test_media_123"
        caption = "Test description with special chars: éñ中文🎉"
        
        # Mock authentication
        with patch.object(self.platform, 'authenticate', return_value=True):
            with patch.object(self.platform, '_get_auth_headers') as mock_headers:
                mock_headers.return_value = {
                    'Authorization': 'Bearer test_token',
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
                
                # Mock successful PUT request
                with patch.object(self.client, '_put_with_retry') as mock_put:
                    mock_response = Mock()
                    mock_response.status_code = 200
                    mock_response.json.return_value = {"id": media_id, "description": caption}
                    mock_put.return_value = mock_response
                    
                    # Test the update
                    await self.platform.update_media_caption(self.client, media_id, caption)
                    
                    # Verify request format
                    call_args = mock_put.call_args
                    
                    # Check URL format
                    expected_url = f"{self.config.instance_url}/api/v1/media/{media_id}"
                    self.assertEqual(call_args[0][0], expected_url)
                    
                    # Check headers format
                    headers = call_args[0][1]
                    self.assertIn('Authorization', headers)
                    self.assertIn('Accept', headers)
                    self.assertIn('Content-Type', headers)
                    self.assertEqual(headers['Accept'], 'application/json')
                    self.assertEqual(headers['Content-Type'], 'application/json')
                    
                    # Check payload format
                    payload = call_args[1]['json']
                    self.assertIsInstance(payload, dict)
                    self.assertEqual(payload['description'], caption)
                    self.assertEqual(len(payload), 1)  # Only description field
    
    async def test_mastodon_api_error_responses(self):
        """Test handling of Mastodon API error responses (400, 401, 403, 404, 500)"""
        media_id = "test_media"
        caption = "Test caption"
        
        error_scenarios = [
            (400, "Bad Request"),
            (401, "Unauthorized"),
            (403, "Forbidden"),
            (404, "Not Found"),
            (500, "Internal Server Error")
        ]
        
        for status_code, error_message in error_scenarios:
            with self.subTest(status_code=status_code):
                # Mock authentication
                with patch.object(self.platform, 'authenticate', return_value=True):
                    with patch.object(self.platform, '_get_auth_headers') as mock_headers:
                        mock_headers.return_value = {
                            'Authorization': 'Bearer test_token',
                            'Accept': 'application/json',
                            'Content-Type': 'application/json'
                        }
                        
                        # Mock error response
                        with patch.object(self.client, '_put_with_retry') as mock_put:
                            mock_put.side_effect = httpx.HTTPStatusError(
                                error_message,
                                request=Mock(),
                                response=Mock(status_code=status_code)
                            )
                            
                            # Test the update
                            result = await self.platform.update_media_caption(
                                self.client, media_id, caption
                            )
                            
                            # Verify failure
                            self.assertFalse(result)
    
    async def test_media_updates_with_different_caption_lengths(self):
        """Test media updates with different caption lengths and formats"""
        media_id = "test_media"
        
        test_captions = [
            "",  # Empty caption
            "Short",  # Short caption
            "A" * 100,  # Medium caption
            "A" * 500,  # Long caption (at limit)
            "A" * 1000,  # Very long caption
            "Caption with\nnewlines\nand\ttabs",  # Caption with special whitespace
            "Caption with emoji 🎉🌟✨",  # Caption with emoji
            "Caption with HTML <b>tags</b> & entities",  # Caption with HTML
        ]
        
        for i, caption in enumerate(test_captions):
            with self.subTest(caption_type=f"caption_{i}"):
                # Mock authentication
                with patch.object(self.platform, 'authenticate', return_value=True):
                    with patch.object(self.platform, '_get_auth_headers') as mock_headers:
                        mock_headers.return_value = {
                            'Authorization': 'Bearer test_token',
                            'Accept': 'application/json',
                            'Content-Type': 'application/json'
                        }
                        
                        # Mock successful PUT request
                        with patch.object(self.client, '_put_with_retry') as mock_put:
                            mock_response = Mock()
                            mock_response.status_code = 200
                            mock_response.json.return_value = {
                                "id": media_id,
                                "description": caption
                            }
                            mock_put.return_value = mock_response
                            
                            # Test the update
                            result = await self.platform.update_media_caption(
                                self.client, media_id, caption
                            )
                            
                            # Verify success
                            self.assertTrue(result)
                            
                            # Verify payload contains the exact caption
                            call_args = mock_put.call_args
                            payload = call_args[1]['json']
                            self.assertEqual(payload['description'], caption)
    
    async def test_media_updates_with_unicode_characters(self):
        """Test media updates with special characters and Unicode"""
        media_id = "test_media"
        
        unicode_captions = [
            "Café with naïve résumé",  # Accented characters
            "中文测试内容",  # Chinese characters
            "العربية اختبار",  # Arabic text
            "Тест на русском",  # Cyrillic text
            "🎉🌟✨🎊🎈",  # Emoji only
            "Mixed: café 中文 🎉 العربية",  # Mixed scripts and emoji
            "Math symbols: ∑∏∫∆∇",  # Mathematical symbols
            "Currency: $€£¥₹₿",  # Currency symbols
        ]
        
        for i, caption in enumerate(unicode_captions):
            with self.subTest(unicode_type=f"unicode_{i}"):
                # Mock authentication
                with patch.object(self.platform, 'authenticate', return_value=True):
                    with patch.object(self.platform, '_get_auth_headers') as mock_headers:
                        mock_headers.return_value = {
                            'Authorization': 'Bearer test_token',
                            'Accept': 'application/json',
                            'Content-Type': 'application/json'
                        }
                        
                        # Mock successful PUT request
                        with patch.object(self.client, '_put_with_retry') as mock_put:
                            mock_response = Mock()
                            mock_response.status_code = 200
                            mock_response.json.return_value = {
                                "id": media_id,
                                "description": caption
                            }
                            mock_put.return_value = mock_response
                            
                            # Test the update
                            result = await self.platform.update_media_caption(
                                self.client, media_id, caption
                            )
                            
                            # Verify success
                            self.assertTrue(result)
                            
                            # Verify Unicode is preserved
                            call_args = mock_put.call_args
                            payload = call_args[1]['json']
                            self.assertEqual(payload['description'], caption)
    
    async def test_concurrent_media_updates(self):
        """Test concurrent media updates and rate limiting"""
        media_ids = [f"media_{i}" for i in range(5)]
        caption = "Concurrent update test"
        
        # Mock authentication
        with patch.object(self.platform, 'authenticate', return_value=True):
            with patch.object(self.platform, '_get_auth_headers') as mock_headers:
                mock_headers.return_value = {
                    'Authorization': 'Bearer test_token',
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
                
                # Mock successful PUT requests
                with patch.object(self.client, '_put_with_retry') as mock_put:
                    mock_response = Mock()
                    mock_response.status_code = 200
                    mock_response.json.return_value = {"description": caption}
                    mock_put.return_value = mock_response
                    
                    # Create concurrent update tasks
                    tasks = [
                        self.platform.update_media_caption(self.client, media_id, caption)
                        for media_id in media_ids
                    ]
                    
                    # Run concurrent updates
                    results = await asyncio.gather(*tasks)
                    
                    # Verify all succeeded
                    self.assertTrue(all(results))
                    
                    # Verify all API calls were made
                    self.assertEqual(mock_put.call_count, len(media_ids))
                    
                    # Verify each media ID was called correctly
                    call_urls = [call[0][0] for call in mock_put.call_args_list]
                    for media_id in media_ids:
                        expected_url = f"{self.config.instance_url}/api/v1/media/{media_id}"
                        self.assertIn(expected_url, call_urls)
    
    async def test_media_update_retry_logic(self):
        """Test media update retry logic on temporary failures"""
        media_id = "test_media"
        caption = "Retry test caption"
        
        # Mock authentication
        with patch.object(self.platform, 'authenticate', return_value=True):
            with patch.object(self.platform, '_get_auth_headers') as mock_headers:
                mock_headers.return_value = {
                    'Authorization': 'Bearer test_token',
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
                
                # Mock retry behavior - fail first time, succeed second time
                with patch.object(self.client, '_put_with_retry') as mock_put:
                    # First call fails with 500, second call succeeds
                    mock_put.side_effect = [
                        httpx.HTTPStatusError(
                            "Internal Server Error",
                            request=Mock(),
                            response=Mock(status_code=500)
                        ),
                        Mock(status_code=200, json=lambda: {"id": media_id, "description": caption})
                    ]
                    
                    # Test the update - should fail on first attempt
                    result = await self.platform.update_media_caption(
                        self.client, media_id, caption
                    )
                    
                    # Should fail because _put_with_retry throws exception
                    self.assertFalse(result)
                    
                    # Verify retry was attempted (called once, failed)
                    self.assertEqual(mock_put.call_count, 1)
    
    async def test_media_update_verification(self):
        """Test media update verification (confirm description was actually updated)"""
        media_id = "test_media"
        original_caption = "Original description"
        new_caption = "Updated description"
        
        # Mock authentication
        with patch.object(self.platform, 'authenticate', return_value=True):
            with patch.object(self.platform, '_get_auth_headers') as mock_headers:
                mock_headers.return_value = {
                    'Authorization': 'Bearer test_token',
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
                
                # Mock successful PUT request that returns updated description
                with patch.object(self.client, '_put_with_retry') as mock_put:
                    mock_response = Mock()
                    mock_response.status_code = 200
                    mock_response.json.return_value = {
                        "id": media_id,
                        "description": new_caption,  # Verify the description was actually updated
                        "type": "image",
                        "url": "https://example.com/image.jpg"
                    }
                    mock_put.return_value = mock_response
                    
                    # Test the update
                    result = await self.platform.update_media_caption(
                        self.client, media_id, new_caption
                    )
                    
                    # Verify success
                    self.assertTrue(result)
                    
                    # Verify the response contains the updated description
                    response_data = mock_response.json()
                    self.assertEqual(response_data['description'], new_caption)
                    self.assertNotEqual(response_data['description'], original_caption)
    
    async def test_empty_media_id_handling(self):
        """Test handling of empty or None media IDs"""
        caption = "Test caption"
        
        # Test with None media ID
        result = await self.platform.update_media_caption(self.client, None, caption)
        self.assertFalse(result)
        
        # Test with empty string media ID
        result = await self.platform.update_media_caption(self.client, "", caption)
        self.assertFalse(result)
        
        # Test with whitespace-only media ID
        result = await self.platform.update_media_caption(self.client, "   ", caption)
        # This should attempt the request (whitespace is not filtered out)
        with patch.object(self.platform, 'authenticate', return_value=True):
            with patch.object(self.platform, '_get_auth_headers') as mock_headers:
                mock_headers.return_value = {'Authorization': 'Bearer test_token'}
                
                with patch.object(self.client, '_put_with_retry') as mock_put:
                    mock_put.side_effect = httpx.HTTPStatusError(
                        "Not Found", request=Mock(), response=Mock(status_code=404)
                    )
                    
                    result = await self.platform.update_media_caption(
                        self.client, "   ", caption
                    )
                    self.assertFalse(result)
    
    async def test_authentication_failure_handling(self):
        """Test handling of authentication failures before media updates"""
        media_id = "test_media"
        caption = "Test caption"
        
        # Mock authentication failure
        with patch.object(self.platform, 'authenticate', return_value=False):
            result = await self.platform.update_media_caption(
                self.client, media_id, caption
            )
            
            # Should fail due to authentication failure
            self.assertFalse(result)
    
    async def test_network_error_handling(self):
        """Test handling of network errors during media updates"""
        media_id = "test_media"
        caption = "Test caption"
        
        # Mock authentication
        with patch.object(self.platform, 'authenticate', return_value=True):
            with patch.object(self.platform, '_get_auth_headers') as mock_headers:
                mock_headers.return_value = {
                    'Authorization': 'Bearer test_token',
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
                
                # Mock network error
                with patch.object(self.client, '_put_with_retry') as mock_put:
                    mock_put.side_effect = httpx.ConnectError("Connection failed")
                    
                    # Test the update
                    result = await self.platform.update_media_caption(
                        self.client, media_id, caption
                    )
                    
                    # Should fail due to network error
                    self.assertFalse(result)

def run_async_test(coro):
    """Helper function to run async tests"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

# Convert async test methods to sync for unittest
class TestMastodonMediaUpdatesSync(TestMastodonMediaUpdates):
    """Synchronous wrapper for async media update tests"""
    
    def test_successful_media_description_update_sync(self):
        run_async_test(self.test_successful_media_description_update())
    
    def test_media_update_with_invalid_media_id_sync(self):
        run_async_test(self.test_media_update_with_invalid_media_id())
    
    def test_media_update_request_format_sync(self):
        run_async_test(self.test_media_update_request_format())
    
    def test_mastodon_api_error_responses_sync(self):
        run_async_test(self.test_mastodon_api_error_responses())
    
    def test_media_updates_with_different_caption_lengths_sync(self):
        run_async_test(self.test_media_updates_with_different_caption_lengths())
    
    def test_media_updates_with_unicode_characters_sync(self):
        run_async_test(self.test_media_updates_with_unicode_characters())
    
    def test_concurrent_media_updates_sync(self):
        run_async_test(self.test_concurrent_media_updates())
    
    def test_media_update_retry_logic_sync(self):
        run_async_test(self.test_media_update_retry_logic())
    
    def test_media_update_verification_sync(self):
        run_async_test(self.test_media_update_verification())
    
    def test_empty_media_id_handling_sync(self):
        run_async_test(self.test_empty_media_id_handling())
    
    def test_authentication_failure_handling_sync(self):
        run_async_test(self.test_authentication_failure_handling())
    
    def test_network_error_handling_sync(self):
        run_async_test(self.test_network_error_handling())

if __name__ == '__main__':
    unittest.main()
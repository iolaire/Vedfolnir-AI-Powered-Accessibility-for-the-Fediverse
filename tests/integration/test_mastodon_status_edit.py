# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Test for Mastodon status edit API functionality.
Tests the fix for "Text can't be blank" error when updating media captions.
"""

import unittest
from unittest.mock import Mock, AsyncMock, patch
import asyncio
from app.services.activitypub.components.activitypub_platforms import MastodonPlatform

class TestMastodonStatusEdit(unittest.TestCase):
    """Test Mastodon status edit functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.config = Mock()
        self.config.instance_url = "https://mastodon.example"
        self.config.access_token = "test_token"
        
        self.platform = MastodonPlatform(self.config)
        self.platform._authenticated = True
        self.platform._auth_headers = {"Authorization": "Bearer test_token"}
        
        self.client = Mock()
        self.client._get_with_retry = AsyncMock()
        self.client._put_with_retry = AsyncMock()
        
        # Mock the authenticate method to always return True
        self.platform.authenticate = AsyncMock(return_value=True)

    def test_update_status_media_caption_success(self):
        """Test successful media caption update with original text preserved"""
        async def run_test():
            # Mock the current status response
            current_status = {
                "text": "Original post text",
                "content": "<p>Original post text</p>"
            }
            mock_response = Mock()
            mock_response.json.return_value = current_status
            self.client._get_with_retry.return_value = mock_response
            
            # Mock successful PUT response
            self.client._put_with_retry.return_value = Mock()
            
            # Test the update
            result = await self.platform.update_status_media_caption(
                self.client, "123456", "media789", "New alt text"
            )
            
            # Verify success
            self.assertTrue(result)
            
            # Verify GET request was made to fetch current status
            self.client._get_with_retry.assert_called_once_with(
                "https://mastodon.example/api/v1/statuses/123456",
                {"Authorization": "Bearer test_token"}
            )
            
            # Verify PUT request was made with correct data
            expected_data = {
                "status": "Original post text",
                "media_ids": ["media789"],
                "media_attributes": [
                    {
                        "id": "media789",
                        "description": "New alt text"
                    }
                ]
            }
            self.client._put_with_retry.assert_called_once_with(
                "https://mastodon.example/api/v1/statuses/123456",
                {"Authorization": "Bearer test_token"},
                json=expected_data
            )
        
        asyncio.run(run_test())

    def test_update_status_media_caption_html_stripping(self):
        """Test that HTML tags are stripped from status text"""
        async def run_test():
            # Mock status with HTML content
            current_status = {
                "content": "<p>Post with <strong>HTML</strong> tags</p>",
                "text": ""
            }
            mock_response = Mock()
            mock_response.json.return_value = current_status
            self.client._get_with_retry.return_value = mock_response
            self.client._put_with_retry.return_value = Mock()
            
            result = await self.platform.update_status_media_caption(
                self.client, "123456", "media789", "Alt text"
            )
            
            self.assertTrue(result)
            
            # Verify HTML was stripped
            call_args = self.client._put_with_retry.call_args
            sent_data = call_args[1]['json']
            self.assertEqual(sent_data['status'], "Post with HTML tags")
        
        asyncio.run(run_test())

    def test_update_status_media_caption_missing_params(self):
        """Test failure when required parameters are missing"""
        async def run_test():
            # Test missing status_id
            result = await self.platform.update_status_media_caption(
                self.client, "", "media789", "Alt text"
            )
            self.assertFalse(result)
            
            # Test missing media_id
            result = await self.platform.update_status_media_caption(
                self.client, "123456", "", "Alt text"
            )
            self.assertFalse(result)
        
        asyncio.run(run_test())

    def test_update_status_media_caption_get_status_fails(self):
        """Test failure when getting current status fails"""
        async def run_test():
            # Mock GET request failure
            self.client._get_with_retry.side_effect = Exception("API Error")
            
            result = await self.platform.update_status_media_caption(
                self.client, "123456", "media789", "Alt text"
            )
            
            self.assertFalse(result)
        
        asyncio.run(run_test())

    def test_update_status_media_caption_put_fails(self):
        """Test failure when PUT request fails"""
        async def run_test():
            # Mock successful GET but failed PUT
            current_status = {"text": "Original text"}
            mock_response = Mock()
            mock_response.json.return_value = current_status
            self.client._get_with_retry.return_value = mock_response
            self.client._put_with_retry.side_effect = Exception("Update failed")
            
            result = await self.platform.update_status_media_caption(
                self.client, "123456", "media789", "Alt text"
            )
            
            self.assertFalse(result)
        
        asyncio.run(run_test())

    def test_update_status_media_caption_auth_required(self):
        """Test that authentication is required"""
        async def run_test():
            # Mock authentication failure
            self.platform.authenticate = AsyncMock(return_value=False)
            
            result = await self.platform.update_status_media_caption(
                self.client, "123456", "media789", "Alt text"
            )
            
            self.assertFalse(result)
            self.platform.authenticate.assert_called_once_with(self.client)
        
        asyncio.run(run_test())

if __name__ == '__main__':
    unittest.main()
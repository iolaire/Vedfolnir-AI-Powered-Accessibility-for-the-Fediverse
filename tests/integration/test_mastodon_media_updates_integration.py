# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Integration tests for Mastodon media updates with mock server responses.
Tests the complete workflow with realistic Mastodon API responses.
"""

import unittest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import asyncio
import httpx
import json

from app.services.activitypub.components.activitypub_client import ActivityPubClient
from app.services.activitypub.components.activitypub_platforms import MastodonPlatform, PlatformAdapterError
from config import ActivityPubConfig

class TestMastodonMediaUpdatesIntegration(unittest.TestCase):
    """Integration tests for Mastodon media updates with mock server responses"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create a mock config for Mastodon
        self.config = Mock()
        self.config.instance_url = "https://mastodon.social"
        self.config.access_token = "test_access_token_12345"
        self.config.api_type = "mastodon"
        self.config.client_key = "test_client_key"
        self.config.client_secret = "test_client_secret"
        self.config.user_agent = "Vedfolnir/1.0"
        self.config.retry = None
        self.config.rate_limit = None
        
        # Create platform and client instances
        self.platform = MastodonPlatform(self.config)
        self.client = ActivityPubClient(self.config)
    
    def _create_mock_mastodon_media_response(self, media_id: str, description: str = "", 
                                           media_type: str = "image") -> dict:
        """Create a realistic Mastodon media response"""
        return {
            "id": media_id,
            "type": media_type,
            "url": f"https://files.mastodon.social/media_attachments/files/{media_id}/original/image.jpg",
            "preview_url": f"https://files.mastodon.social/media_attachments/files/{media_id}/small/image.jpg",
            "remote_url": None,
            "text_url": f"https://mastodon.social/media/{media_id}",
            "meta": {
                "original": {
                    "width": 1200,
                    "height": 800,
                    "size": "1200x800",
                    "aspect": 1.5
                },
                "small": {
                    "width": 400,
                    "height": 267,
                    "size": "400x267",
                    "aspect": 1.4981273408239701
                }
            },
            "description": description,
            "blurhash": "UeKUzKxu4nM{~qRjWBof4nWB%MayIUj[WBj["
        }
    
    def _create_mock_verify_credentials_response(self) -> dict:
        """Create a realistic Mastodon verify_credentials response"""
        return {
            "id": "123456789",
            "username": "testuser",
            "acct": "testuser",
            "display_name": "Test User",
            "locked": False,
            "bot": False,
            "discoverable": True,
            "group": False,
            "created_at": "2023-01-01T00:00:00.000Z",
            "note": "Test account for vedfolnir",
            "url": "https://mastodon.social/@testuser",
            "avatar": "https://mastodon.social/avatars/original/missing.png",
            "avatar_static": "https://mastodon.social/avatars/original/missing.png",
            "header": "https://mastodon.social/headers/original/missing.png",
            "header_static": "https://mastodon.social/headers/original/missing.png",
            "followers_count": 100,
            "following_count": 50,
            "statuses_count": 25,
            "last_status_at": "2023-12-01",
            "source": {
                "privacy": "public",
                "sensitive": False,
                "language": "en",
                "note": "Test account for vedfolnir",
                "fields": []
            },
            "emojis": [],
            "fields": []
        }
    
    async def test_complete_media_update_workflow(self):
        """Test complete media update workflow with realistic responses"""
        media_id = "110123456789012345"
        original_description = ""
        new_description = "A beautiful landscape photo showing mountains at sunset"
        
        # Mock HTTP session
        with patch.object(self.client, 'session') as mock_session:
            # Mock verify_credentials response (for authentication)
            verify_response = Mock()
            verify_response.status_code = 200
            verify_response.json.return_value = self._create_mock_verify_credentials_response()
            verify_response.raise_for_status = Mock()
            
            # Mock media update response
            update_response = Mock()
            update_response.status_code = 200
            update_response.json.return_value = self._create_mock_mastodon_media_response(
                media_id, new_description
            )
            update_response.raise_for_status = Mock()
            
            # Set up mock responses
            mock_session.get = AsyncMock(return_value=verify_response)
            mock_session.put = AsyncMock(return_value=update_response)
            
            # Test the complete workflow
            result = await self.platform.update_media_caption(
                self.client, media_id, new_description
            )
            
            # Verify success
            self.assertTrue(result)
            
            # Verify authentication was called
            mock_session.get.assert_called_once()
            verify_call = mock_session.get.call_args
            self.assertIn("/api/v1/accounts/verify_credentials", verify_call[0][0])
            
            # Verify media update was called with correct parameters
            mock_session.put.assert_called_once()
            update_call = mock_session.put.call_args
            
            # Check URL
            expected_url = f"{self.config.instance_url}/api/v1/media/{media_id}"
            self.assertEqual(update_call[0][0], expected_url)
            
            # Check headers
            headers = update_call[1]['headers']
            self.assertEqual(headers['Authorization'], f'Bearer {self.config.access_token}')
            self.assertEqual(headers['Content-Type'], 'application/json')
            
            # Check payload
            payload = update_call[1]['json']
            self.assertEqual(payload, {'description': new_description})
    
    async def test_media_update_with_rate_limiting(self):
        """Test media update with rate limiting headers"""
        media_id = "110123456789012345"
        description = "Test description"
        
        # Mock HTTP session
        with patch.object(self.client, 'session') as mock_session:
            # Mock verify_credentials response
            verify_response = Mock()
            verify_response.status_code = 200
            verify_response.json.return_value = self._create_mock_verify_credentials_response()
            verify_response.raise_for_status = Mock()
            
            # Mock media update response with rate limit headers
            update_response = Mock()
            update_response.status_code = 200
            update_response.json.return_value = self._create_mock_mastodon_media_response(
                media_id, description
            )
            update_response.headers = {
                'X-RateLimit-Limit': '300',
                'X-RateLimit-Remaining': '299',
                'X-RateLimit-Reset': '1640995200'
            }
            update_response.raise_for_status = Mock()
            
            mock_session.get = AsyncMock(return_value=verify_response)
            mock_session.put = AsyncMock(return_value=update_response)
            
            # Test the update
            result = await self.platform.update_media_caption(
                self.client, media_id, description
            )
            
            # Verify success
            self.assertTrue(result)
            
            # Verify rate limit headers are available
            rate_limit_info = self.platform.get_rate_limit_info(update_response.headers)
            self.assertEqual(rate_limit_info['limit'], 300)
            self.assertEqual(rate_limit_info['remaining'], 299)
            self.assertEqual(rate_limit_info['reset'], 1640995200)
    
    async def test_media_update_with_mastodon_error_responses(self):
        """Test media update with various Mastodon error responses"""
        media_id = "110123456789012345"
        description = "Test description"
        
        # Test different error scenarios
        error_scenarios = [
            {
                'status_code': 401,
                'error': 'invalid_token',
                'error_description': 'The access token is invalid'
            },
            {
                'status_code': 403,
                'error': 'forbidden',
                'error_description': 'This action is not allowed'
            },
            {
                'status_code': 404,
                'error': 'record_not_found',
                'error_description': 'Record not found'
            },
            {
                'status_code': 422,
                'error': 'validation_failed',
                'error_description': 'Description is too long'
            },
            {
                'status_code': 500,
                'error': 'internal_server_error',
                'error_description': 'Something went wrong on our end'
            }
        ]
        
        for scenario in error_scenarios:
            with self.subTest(status_code=scenario['status_code']):
                # Mock HTTP session
                with patch.object(self.client, 'session') as mock_session:
                    # Mock verify_credentials response (successful authentication)
                    verify_response = Mock()
                    verify_response.status_code = 200
                    verify_response.json.return_value = self._create_mock_verify_credentials_response()
                    verify_response.raise_for_status = Mock()
                    
                    # Mock error response for media update
                    error_response = Mock()
                    error_response.status_code = scenario['status_code']
                    error_response.json.return_value = {
                        'error': scenario['error'],
                        'error_description': scenario['error_description']
                    }
                    
                    mock_session.get = AsyncMock(return_value=verify_response)
                    mock_session.put = AsyncMock(side_effect=httpx.HTTPStatusError(
                        scenario['error_description'],
                        request=Mock(),
                        response=error_response
                    ))
                    
                    # Test the update
                    result = await self.platform.update_media_caption(
                        self.client, media_id, description
                    )
                    
                    # Verify failure
                    self.assertFalse(result)
    
    async def test_media_update_with_long_description(self):
        """Test media update with very long description (testing Mastodon limits)"""
        media_id = "110123456789012345"
        
        # Mastodon typically allows up to 1500 characters for media descriptions
        long_description = "A" * 1500
        very_long_description = "A" * 2000  # Exceeds typical limit
        
        # Test with maximum allowed length
        with patch.object(self.client, 'session') as mock_session:
            # Mock successful responses
            verify_response = Mock()
            verify_response.status_code = 200
            verify_response.json.return_value = self._create_mock_verify_credentials_response()
            verify_response.raise_for_status = Mock()
            
            update_response = Mock()
            update_response.status_code = 200
            update_response.json.return_value = self._create_mock_mastodon_media_response(
                media_id, long_description
            )
            update_response.raise_for_status = Mock()
            
            mock_session.get = AsyncMock(return_value=verify_response)
            mock_session.put = AsyncMock(return_value=update_response)
            
            # Test with long description (should succeed)
            result = await self.platform.update_media_caption(
                self.client, media_id, long_description
            )
            self.assertTrue(result)
            
            # Verify the full description was sent
            update_call = mock_session.put.call_args
            payload = update_call[1]['json']
            self.assertEqual(payload['description'], long_description)
        
        # Test with very long description (should fail with 422)
        with patch.object(self.client, 'session') as mock_session:
            verify_response = Mock()
            verify_response.status_code = 200
            verify_response.json.return_value = self._create_mock_verify_credentials_response()
            verify_response.raise_for_status = Mock()
            
            error_response = Mock()
            error_response.status_code = 422
            error_response.json.return_value = {
                'error': 'validation_failed',
                'error_description': 'Description is too long (maximum is 1500 characters)'
            }
            
            mock_session.get = AsyncMock(return_value=verify_response)
            mock_session.put = AsyncMock(side_effect=httpx.HTTPStatusError(
                "Validation failed",
                request=Mock(),
                response=error_response
            ))
            
            # Test with very long description (should fail)
            result = await self.platform.update_media_caption(
                self.client, media_id, very_long_description
            )
            self.assertFalse(result)
    
    async def test_media_update_with_special_content_types(self):
        """Test media update with different content types and special characters"""
        media_id = "110123456789012345"
        
        special_descriptions = [
            "Description with JSON: {\"key\": \"value\"}",
            "Description with XML: <tag>content</tag>",
            "Description with quotes: \"quoted text\" and 'single quotes'",
            "Description with backslashes: C:\\path\\to\\file",
            "Description with newlines:\nLine 1\nLine 2\nLine 3",
            "Description with tabs:\tTabbed\tcontent\there",
            "Mixed special chars: @#$%^&*()_+-=[]{}|;':\",./<>?",
        ]
        
        for i, description in enumerate(special_descriptions):
            with self.subTest(description_type=f"special_{i}"):
                # Mock HTTP session
                with patch.object(self.client, 'session') as mock_session:
                    # Mock successful responses
                    verify_response = Mock()
                    verify_response.status_code = 200
                    verify_response.json.return_value = self._create_mock_verify_credentials_response()
                    verify_response.raise_for_status = Mock()
                    
                    update_response = Mock()
                    update_response.status_code = 200
                    update_response.json.return_value = self._create_mock_mastodon_media_response(
                        media_id, description
                    )
                    update_response.raise_for_status = Mock()
                    
                    mock_session.get = AsyncMock(return_value=verify_response)
                    mock_session.put = AsyncMock(return_value=update_response)
                    
                    # Test the update
                    result = await self.platform.update_media_caption(
                        self.client, media_id, description
                    )
                    
                    # Verify success
                    self.assertTrue(result)
                    
                    # Verify the exact description was sent
                    update_call = mock_session.put.call_args
                    payload = update_call[1]['json']
                    self.assertEqual(payload['description'], description)
    
    async def test_media_update_authentication_flow(self):
        """Test the complete authentication flow during media updates"""
        media_id = "110123456789012345"
        description = "Test description"
        
        # Mock HTTP session
        with patch.object(self.client, 'session') as mock_session:
            # Mock verify_credentials response with detailed user info
            verify_response = Mock()
            verify_response.status_code = 200
            verify_response.json.return_value = self._create_mock_verify_credentials_response()
            verify_response.raise_for_status = Mock()
            
            # Mock media update response
            update_response = Mock()
            update_response.status_code = 200
            update_response.json.return_value = self._create_mock_mastodon_media_response(
                media_id, description
            )
            update_response.raise_for_status = Mock()
            
            mock_session.get = AsyncMock(return_value=verify_response)
            mock_session.put = AsyncMock(return_value=update_response)
            
            # Test the update (should trigger authentication)
            result = await self.platform.update_media_caption(
                self.client, media_id, description
            )
            
            # Verify success
            self.assertTrue(result)
            
            # Verify authentication flow
            self.assertTrue(self.platform._authenticated)
            self.assertIsNotNone(self.platform._auth_headers)
            
            # Verify authentication headers are correct
            auth_headers = self.platform._auth_headers
            self.assertEqual(auth_headers['Authorization'], f'Bearer {self.config.access_token}')
            self.assertEqual(auth_headers['Accept'], 'application/json')
            self.assertEqual(auth_headers['Content-Type'], 'application/json')
            
            # Test second update (should reuse authentication)
            mock_session.reset_mock()
            
            result2 = await self.platform.update_media_caption(
                self.client, media_id, "Second description"
            )
            
            # Verify success
            self.assertTrue(result2)
            
            # Verify authentication was reused (verify_credentials called only once more for validation)
            verify_calls = [call for call in mock_session.get.call_args_list 
                          if "verify_credentials" in str(call)]
            self.assertEqual(len(verify_calls), 1)  # Only one additional validation call
    
    async def test_media_update_with_network_issues(self):
        """Test media update handling of various network issues"""
        media_id = "110123456789012345"
        description = "Test description"
        
        network_errors = [
            httpx.ConnectError("Connection failed"),
            httpx.TimeoutException("Request timed out"),
            httpx.NetworkError("Network unreachable"),
            httpx.ProtocolError("Protocol error"),
        ]
        
        for error in network_errors:
            with self.subTest(error_type=type(error).__name__):
                # Mock HTTP session
                with patch.object(self.client, 'session') as mock_session:
                    # Mock successful authentication
                    verify_response = Mock()
                    verify_response.status_code = 200
                    verify_response.json.return_value = self._create_mock_verify_credentials_response()
                    verify_response.raise_for_status = Mock()
                    
                    mock_session.get = AsyncMock(return_value=verify_response)
                    mock_session.put = AsyncMock(side_effect=error)
                    
                    # Test the update
                    result = await self.platform.update_media_caption(
                        self.client, media_id, description
                    )
                    
                    # Verify failure
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
class TestMastodonMediaUpdatesIntegrationSync(TestMastodonMediaUpdatesIntegration):
    """Synchronous wrapper for async integration tests"""
    
    def test_complete_media_update_workflow_sync(self):
        run_async_test(self.test_complete_media_update_workflow())
    
    def test_media_update_with_rate_limiting_sync(self):
        run_async_test(self.test_media_update_with_rate_limiting())
    
    def test_media_update_with_mastodon_error_responses_sync(self):
        run_async_test(self.test_media_update_with_mastodon_error_responses())
    
    def test_media_update_with_long_description_sync(self):
        run_async_test(self.test_media_update_with_long_description())
    
    def test_media_update_with_special_content_types_sync(self):
        run_async_test(self.test_media_update_with_special_content_types())
    
    def test_media_update_authentication_flow_sync(self):
        run_async_test(self.test_media_update_authentication_flow())
    
    def test_media_update_with_network_issues_sync(self):
        run_async_test(self.test_media_update_with_network_issues())

if __name__ == '__main__':
    unittest.main()
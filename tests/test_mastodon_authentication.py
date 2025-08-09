# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Tests for Mastodon authentication functionality.
"""

import unittest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import asyncio
import httpx
from dataclasses import dataclass

from activitypub_platforms import MastodonPlatform, PlatformAdapterError
from config import ActivityPubConfig


@dataclass
class MockConfig:
    """Mock configuration for testing"""
    instance_url: str = "https://mastodon.social"
    access_token: str = "test_access_token"
    api_type: str = "mastodon"
    client_key: str = "test_client_key"
    client_secret: str = "test_client_secret"
    user_agent: str = "Vedfolnir/1.0"


class TestMastodonAuthentication(unittest.TestCase):
    """Test cases for Mastodon authentication"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = MockConfig()
        self.platform = MastodonPlatform(self.config)
        self.mock_client = Mock()
        self.mock_client._get_with_retry = AsyncMock()
        
    def test_config_validation_success(self):
        """Test successful configuration validation"""
        # Should not raise any exceptions
        platform = MastodonPlatform(self.config)
        self.assertIsNotNone(platform)
        
    def test_config_validation_missing_client_key(self):
        """Test configuration validation with missing client key"""
        config = MockConfig()
        config.client_key = None
        
        with self.assertRaises(PlatformAdapterError) as context:
            MastodonPlatform(config)
        
        self.assertIn("client_key is required", str(context.exception))
        
    def test_config_validation_missing_client_secret(self):
        """Test configuration validation with missing client secret"""
        config = MockConfig()
        config.client_secret = None
        
        with self.assertRaises(PlatformAdapterError) as context:
            MastodonPlatform(config)
        
        self.assertIn("client_secret is required", str(context.exception))
        
    def test_config_validation_missing_access_token(self):
        """Test configuration validation with missing access token"""
        config = MockConfig()
        config.access_token = None
        
        with self.assertRaises(PlatformAdapterError) as context:
            MastodonPlatform(config)
        
        self.assertIn("access_token is required", str(context.exception))
        
    def test_config_validation_missing_instance_url(self):
        """Test configuration validation with missing instance URL"""
        config = MockConfig()
        config.instance_url = None
        
        with self.assertRaises(PlatformAdapterError) as context:
            MastodonPlatform(config)
        
        self.assertIn("instance_url is required", str(context.exception))
        
    async def test_authenticate_success(self):
        """Test successful authentication"""
        # Mock successful verify_credentials response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "123456",
            "username": "testuser",
            "display_name": "Test User"
        }
        self.mock_client._get_with_retry.return_value = mock_response
        
        result = await self.platform.authenticate(self.mock_client)
        
        self.assertTrue(result)
        self.assertTrue(self.platform._authenticated)
        self.assertIsNotNone(self.platform._auth_headers)
        self.assertEqual(
            self.platform._auth_headers['Authorization'],
            f'Bearer {self.config.access_token}'
        )
        
    async def test_authenticate_invalid_token(self):
        """Test authentication with invalid access token"""
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
        
    async def test_authenticate_forbidden_token(self):
        """Test authentication with token lacking permissions"""
        # Mock 403 Forbidden response
        mock_response = Mock()
        mock_response.status_code = 403
        self.mock_client._get_with_retry.side_effect = httpx.HTTPStatusError(
            "Forbidden", request=Mock(), response=mock_response
        )
        
        result = await self.platform.authenticate(self.mock_client)
        
        self.assertFalse(result)
        self.assertFalse(self.platform._authenticated)
        self.assertIsNone(self.platform._auth_headers)
        
    async def test_authenticate_network_error(self):
        """Test authentication with network error"""
        # Mock network error
        self.mock_client._get_with_retry.side_effect = httpx.ConnectError(
            "Connection failed"
        )
        
        result = await self.platform.authenticate(self.mock_client)
        
        self.assertFalse(result)
        self.assertFalse(self.platform._authenticated)
        self.assertIsNone(self.platform._auth_headers)
        
    async def test_authenticate_timeout_error(self):
        """Test authentication with timeout error"""
        # Mock timeout error
        self.mock_client._get_with_retry.side_effect = httpx.TimeoutException(
            "Request timed out"
        )
        
        result = await self.platform.authenticate(self.mock_client)
        
        self.assertFalse(result)
        self.assertFalse(self.platform._authenticated)
        self.assertIsNone(self.platform._auth_headers)
        
    async def test_authenticate_missing_access_token(self):
        """Test authentication with missing access token"""
        # Create a platform with valid config first
        platform = MastodonPlatform(self.config)
        
        # Then modify the config to have empty access token
        platform.config.access_token = ""
        
        result = await platform.authenticate(self.mock_client)
        
        self.assertFalse(result)
        self.assertFalse(platform._authenticated)
        self.assertIsNone(platform._auth_headers)
        
    async def test_validate_token_success(self):
        """Test successful token validation"""
        # Set up authenticated state
        self.platform._auth_headers = {
            'Authorization': f'Bearer {self.config.access_token}',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "123456",
            "username": "testuser"
        }
        self.mock_client._get_with_retry.return_value = mock_response
        
        result = await self.platform._validate_token(self.mock_client)
        
        self.assertTrue(result)
        self.mock_client._get_with_retry.assert_called_once()
        
    async def test_validate_token_invalid(self):
        """Test token validation with invalid token"""
        # Set up authenticated state
        self.platform._auth_headers = {
            'Authorization': 'Bearer invalid_token',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        # Mock 401 response
        mock_response = Mock()
        mock_response.status_code = 401
        self.mock_client._get_with_retry.side_effect = httpx.HTTPStatusError(
            "Unauthorized", request=Mock(), response=mock_response
        )
        
        result = await self.platform._validate_token(self.mock_client)
        
        self.assertFalse(result)
        
    async def test_validate_token_no_headers(self):
        """Test token validation with no auth headers"""
        result = await self.platform._validate_token(self.mock_client)
        
        self.assertFalse(result)
        self.mock_client._get_with_retry.assert_not_called()
        
    def test_get_auth_headers_success(self):
        """Test getting auth headers when authenticated"""
        # Set up authenticated state
        self.platform._authenticated = True
        self.platform._auth_headers = {
            'Authorization': f'Bearer {self.config.access_token}',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        headers = self.platform._get_auth_headers()
        
        self.assertEqual(headers['Authorization'], f'Bearer {self.config.access_token}')
        self.assertEqual(headers['Accept'], 'application/json')
        self.assertEqual(headers['Content-Type'], 'application/json')
        
    def test_get_auth_headers_not_authenticated(self):
        """Test getting auth headers when not authenticated"""
        with self.assertRaises(PlatformAdapterError) as context:
            self.platform._get_auth_headers()
        
        self.assertIn("Not authenticated", str(context.exception))
        
    async def test_refresh_token_if_needed_valid(self):
        """Test token refresh when token is still valid"""
        # Set up authenticated state
        self.platform._auth_headers = {
            'Authorization': f'Bearer {self.config.access_token}',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        # Mock successful validation
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"username": "testuser"}
        self.mock_client._get_with_retry.return_value = mock_response
        
        result = await self.platform._refresh_token_if_needed(self.mock_client)
        
        self.assertTrue(result)
        
    async def test_refresh_token_if_needed_invalid(self):
        """Test token refresh when token is invalid"""
        # Set up authenticated state
        self.platform._auth_headers = {
            'Authorization': 'Bearer invalid_token',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        # Mock 401 response
        mock_response = Mock()
        mock_response.status_code = 401
        self.mock_client._get_with_retry.side_effect = httpx.HTTPStatusError(
            "Unauthorized", request=Mock(), response=mock_response
        )
        
        result = await self.platform._refresh_token_if_needed(self.mock_client)
        
        self.assertFalse(result)
        
    async def test_authenticate_with_different_mastodon_instances(self):
        """Test authentication with different Mastodon instance configurations"""
        instances = [
            "https://mastodon.social",
            "https://fosstodon.org",
            "https://mas.to",
            "https://mstdn.social"
        ]
        
        for instance_url in instances:
            config = MockConfig()
            config.instance_url = instance_url
            platform = MastodonPlatform(config)
            
            # Mock successful response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"username": "testuser"}
            self.mock_client._get_with_retry.return_value = mock_response
            
            result = await platform.authenticate(self.mock_client)
            
            self.assertTrue(result, f"Authentication failed for {instance_url}")
            self.assertTrue(platform._authenticated)
            
    async def test_authenticate_reuse_valid_token(self):
        """Test that authentication reuses valid existing token"""
        # First authentication
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"username": "testuser"}
        self.mock_client._get_with_retry.return_value = mock_response
        
        result1 = await self.platform.authenticate(self.mock_client)
        self.assertTrue(result1)
        
        # Reset mock to track second call
        self.mock_client._get_with_retry.reset_mock()
        
        # Second authentication should reuse token
        result2 = await self.platform.authenticate(self.mock_client)
        self.assertTrue(result2)
        
        # Should have called verify_credentials only once for validation
        self.assertEqual(self.mock_client._get_with_retry.call_count, 1)


def run_async_test(coro):
    """Helper function to run async tests"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# Convert async test methods to sync for unittest
class TestMastodonAuthenticationSync(TestMastodonAuthentication):
    """Synchronous wrapper for async tests"""
    
    def test_authenticate_success_sync(self):
        run_async_test(self.test_authenticate_success())
        
    def test_authenticate_invalid_token_sync(self):
        run_async_test(self.test_authenticate_invalid_token())
        
    def test_authenticate_forbidden_token_sync(self):
        run_async_test(self.test_authenticate_forbidden_token())
        
    def test_authenticate_network_error_sync(self):
        run_async_test(self.test_authenticate_network_error())
        
    def test_authenticate_timeout_error_sync(self):
        run_async_test(self.test_authenticate_timeout_error())
        
    def test_authenticate_missing_access_token_sync(self):
        run_async_test(self.test_authenticate_missing_access_token())
        
    def test_validate_token_success_sync(self):
        run_async_test(self.test_validate_token_success())
        
    def test_validate_token_invalid_sync(self):
        run_async_test(self.test_validate_token_invalid())
        
    def test_validate_token_no_headers_sync(self):
        run_async_test(self.test_validate_token_no_headers())
        
    def test_refresh_token_if_needed_valid_sync(self):
        run_async_test(self.test_refresh_token_if_needed_valid())
        
    def test_refresh_token_if_needed_invalid_sync(self):
        run_async_test(self.test_refresh_token_if_needed_invalid())
        
    def test_authenticate_with_different_mastodon_instances_sync(self):
        run_async_test(self.test_authenticate_with_different_mastodon_instances())
        
    def test_authenticate_reuse_valid_token_sync(self):
        run_async_test(self.test_authenticate_reuse_valid_token())


if __name__ == '__main__':
    unittest.main()
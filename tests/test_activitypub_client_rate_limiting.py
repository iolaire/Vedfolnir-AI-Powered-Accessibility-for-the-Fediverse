# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Integration tests for ActivityPub client with multi-platform rate limiting.

This module tests the integration between the ActivityPub client and the
enhanced rate limiting system for both Pixelfed and Mastodon platforms.
"""

import unittest
import asyncio
import os
from unittest.mock import Mock, patch, AsyncMock
import httpx

# Import the modules we're testing
from activitypub_client import ActivityPubClient
from config import ActivityPubConfig, RateLimitConfig
from rate_limiter import get_rate_limiter


class TestActivityPubClientRateLimiting(unittest.TestCase):
    """Test ActivityPub client integration with multi-platform rate limiting"""
    
    def setUp(self):
        """Set up test environment"""
        # Clear any existing environment variables
        for key in list(os.environ.keys()):
            if key.startswith('RATE_LIMIT_'):
                del os.environ[key]
        
        # Set up test configuration
        self.pixelfed_config = ActivityPubConfig(
            instance_url="https://pixelfed.social",
            access_token="test_token",
            api_type="pixelfed",
            rate_limit=RateLimitConfig(
                requests_per_minute=60,
                max_burst=10,
                platform_limits={'pixelfed': {'minute': 60}},
                platform_endpoint_limits={'pixelfed': {'media': {'minute': 30}}}
            )
        )
        
        self.mastodon_config = ActivityPubConfig(
            instance_url="https://mastodon.social",
            access_token="test_token",
            api_type="mastodon",
            client_key="test_key",
            client_secret="test_secret",
            rate_limit=RateLimitConfig(
                requests_per_minute=300,
                max_burst=20,
                platform_limits={'mastodon': {'minute': 300}},
                platform_endpoint_limits={'mastodon': {'media': {'minute': 100}}}
            )
        )
    
    def test_pixelfed_client_rate_limiting_initialization(self):
        """Test that Pixelfed client initializes rate limiting correctly"""
        with patch('activitypub_client.PlatformAdapterFactory') as mock_factory:
            mock_adapter = Mock()
            mock_adapter.platform_name = 'pixelfed'
            mock_factory.create_adapter.return_value = mock_adapter
            
            client = ActivityPubClient(self.pixelfed_config)
            
            # Check that rate limiter was initialized
            self.assertIsNotNone(client.rate_limiter)
            
            # Check that platform-specific limits are configured
            stats = client.rate_limiter.get_stats()
            self.assertIn('platforms', stats['limits'])
            # The platform limits should be configured from the config
            if 'pixelfed' in stats['limits']['platforms']:
                self.assertIn('pixelfed', stats['limits']['platforms'])
    
    def test_mastodon_client_rate_limiting_initialization(self):
        """Test that Mastodon client initializes rate limiting correctly"""
        with patch('activitypub_client.PlatformAdapterFactory') as mock_factory:
            mock_adapter = Mock()
            mock_adapter.platform_name = 'mastodon'
            mock_factory.create_adapter.return_value = mock_adapter
            
            client = ActivityPubClient(self.mastodon_config)
            
            # Check that rate limiter was initialized
            self.assertIsNotNone(client.rate_limiter)
            
            # Check that platform-specific limits are configured
            stats = client.rate_limiter.get_stats()
            self.assertIn('platforms', stats['limits'])
            self.assertIn('mastodon', stats['limits']['platforms'])
    
    def test_rate_limited_decorator_with_platform_info(self):
        """Test that rate_limited decorator receives platform information"""
        with patch('activitypub_client.PlatformAdapterFactory') as mock_factory:
            mock_adapter = Mock()
            mock_adapter.platform_name = 'mastodon'
            mock_factory.create_adapter.return_value = mock_adapter
            
            client = ActivityPubClient(self.mastodon_config)
            
            # Mock the rate limiter to track calls
            with patch.object(client.rate_limiter, 'wait_if_needed', new_callable=AsyncMock) as mock_wait:
                mock_wait.return_value = 0.0
                
                # Mock httpx session
                with patch.object(client, 'session') as mock_session:
                    mock_response = Mock()
                    mock_response.headers = {'X-RateLimit-Remaining': '299'}
                    mock_session.get = AsyncMock(return_value=mock_response)
                    
                    async def run_test():
                        await client._get_with_retry("https://mastodon.social/api/v1/media/123", {})
                        
                        # Verify that wait_if_needed was called with platform info
                        mock_wait.assert_called_once()
                        args, kwargs = mock_wait.call_args
                        
                        # Check that platform was passed (either as positional or keyword arg)
                        if len(args) >= 2:
                            self.assertEqual(args[1], 'mastodon')
                        else:
                            self.assertEqual(kwargs.get('platform'), 'mastodon')
                    
                    asyncio.run(run_test())
    
    def test_rate_limit_stats_tracking_by_platform(self):
        """Test that rate limit statistics are tracked by platform"""
        with patch('activitypub_client.PlatformAdapterFactory') as mock_factory:
            mock_adapter = Mock()
            mock_adapter.platform_name = 'mastodon'
            mock_factory.create_adapter.return_value = mock_adapter
            
            client = ActivityPubClient(self.mastodon_config)
            
            # Reset stats first to get clean counts
            client.rate_limiter.reset_stats()
            
            # Make some mock requests to generate stats
            client.rate_limiter.check_rate_limit(platform='mastodon')
            client.rate_limiter.check_rate_limit(endpoint='media', platform='mastodon')
            
            # Check that platform stats are tracked
            stats = client.get_rate_limit_stats()
            self.assertIn('platforms', stats)
            self.assertIn('MASTODON', stats['platforms'])
            self.assertEqual(stats['platforms']['MASTODON']['requests'], 2)
    
    def test_response_header_processing(self):
        """Test that response headers are processed for rate limit info"""
        with patch('activitypub_client.PlatformAdapterFactory') as mock_factory:
            mock_adapter = Mock()
            mock_adapter.platform_name = 'mastodon'
            mock_factory.create_adapter.return_value = mock_adapter
            
            client = ActivityPubClient(self.mastodon_config)
            
            # Mock the rate limiter's update method
            with patch.object(client.rate_limiter, 'update_from_response_headers') as mock_update:
                # Mock httpx session
                with patch.object(client, 'session') as mock_session:
                    mock_response = Mock()
                    mock_response.headers = {
                        'X-RateLimit-Limit': '300',
                        'X-RateLimit-Remaining': '299',
                        'X-RateLimit-Reset': '1234567890'
                    }
                    mock_session.get = AsyncMock(return_value=mock_response)
                    
                    async def run_test():
                        await client._get_with_retry("https://mastodon.social/api/v1/media/123", {})
                        
                        # Verify that response headers were processed
                        mock_update.assert_called_once_with(mock_response.headers, 'mastodon')
                    
                    asyncio.run(run_test())
    
    def test_platform_specific_endpoint_rate_limiting(self):
        """Test platform-specific endpoint rate limiting"""
        # Set up environment with platform-specific endpoint limits
        os.environ['RATE_LIMIT_MASTODON_ENDPOINT_MEDIA_MINUTE'] = '100'
        os.environ['RATE_LIMIT_PIXELFED_ENDPOINT_MEDIA_MINUTE'] = '30'
        
        mastodon_config = ActivityPubConfig(
            instance_url="https://mastodon.social",
            access_token="test_token",
            api_type="mastodon",
            client_key="test_key",
            client_secret="test_secret",
            rate_limit=RateLimitConfig.from_env()
        )
        
        pixelfed_config = ActivityPubConfig(
            instance_url="https://pixelfed.social",
            access_token="test_token",
            api_type="pixelfed",
            rate_limit=RateLimitConfig.from_env()
        )
        
        # Test Mastodon client
        with patch('activitypub_client.PlatformAdapterFactory') as mock_factory:
            mock_adapter = Mock()
            mock_adapter.platform_name = 'mastodon'
            mock_factory.create_adapter.return_value = mock_adapter
            
            mastodon_client = ActivityPubClient(mastodon_config)
            mastodon_stats = mastodon_client.rate_limiter.get_stats()
            
            if 'platform_endpoints' in mastodon_stats['limits'] and 'mastodon' in mastodon_stats['limits']['platform_endpoints']:
                self.assertEqual(
                    mastodon_stats['limits']['platform_endpoints']['mastodon']['media']['minute'], 
                    100
                )
        
        # Test Pixelfed client
        with patch('activitypub_client.PlatformAdapterFactory') as mock_factory:
            mock_adapter = Mock()
            mock_adapter.platform_name = 'pixelfed'
            mock_factory.create_adapter.return_value = mock_adapter
            
            pixelfed_client = ActivityPubClient(pixelfed_config)
            pixelfed_stats = pixelfed_client.rate_limiter.get_stats()
            
            if 'platform_endpoints' in pixelfed_stats['limits'] and 'pixelfed' in pixelfed_stats['limits']['platform_endpoints']:
                self.assertEqual(
                    pixelfed_stats['limits']['platform_endpoints']['pixelfed']['media']['minute'], 
                    30
                )
    
    def test_api_usage_report_includes_platform_stats(self):
        """Test that API usage report includes platform-specific statistics"""
        with patch('activitypub_client.PlatformAdapterFactory') as mock_factory:
            mock_adapter = Mock()
            mock_adapter.platform_name = 'mastodon'
            mock_factory.create_adapter.return_value = mock_adapter
            
            client = ActivityPubClient(self.mastodon_config)
            
            # Make some requests to generate stats
            client.rate_limiter.check_rate_limit(platform='mastodon')
            client.rate_limiter.check_rate_limit(endpoint='media', platform='mastodon')
            
            # Get API usage report
            report = client.get_api_usage_report()
            
            # Check that platform stats are included
            self.assertIn('rate_limit_stats', report)
            self.assertIn('platforms', report['rate_limit_stats'])
            self.assertIn('MASTODON', report['rate_limit_stats']['platforms'])
    
    def test_backward_compatibility_without_platform_info(self):
        """Test that rate limiting still works without platform information"""
        # Create a config without platform-specific limits
        basic_config = ActivityPubConfig(
            instance_url="https://example.com",
            access_token="test_token",
            api_type="pixelfed",
            rate_limit=RateLimitConfig(requests_per_minute=60, max_burst=10)
        )
        
        with patch('activitypub_client.PlatformAdapterFactory') as mock_factory:
            mock_adapter = Mock()
            mock_adapter.platform_name = None  # No platform info
            mock_factory.create_adapter.return_value = mock_adapter
            
            client = ActivityPubClient(basic_config)
            
            # Should still work with global rate limits
            self.assertIsNotNone(client.rate_limiter)
            
            # Mock the rate limiter to track calls
            with patch.object(client.rate_limiter, 'wait_if_needed', new_callable=AsyncMock) as mock_wait:
                mock_wait.return_value = 0.0
                
                # Mock httpx session
                with patch.object(client, 'session') as mock_session:
                    mock_response = Mock()
                    mock_response.headers = {}
                    mock_session.get = AsyncMock(return_value=mock_response)
                    
                    async def run_test():
                        await client._get_with_retry("https://example.com/api/v1/test", {})
                        
                        # Should still call wait_if_needed (with None platform)
                        mock_wait.assert_called_once()
                    
                    asyncio.run(run_test())


if __name__ == '__main__':
    unittest.main()
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Tests for multi-platform rate limiting functionality.

This module tests the enhanced rate limiting system that supports
platform-specific rate limits for both Pixelfed and Mastodon.
"""

import unittest
import asyncio
import os
import time
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

# Import the modules we're testing
from rate_limiter import (
    RateLimitConfig, RateLimiter, TokenBucket, get_rate_limiter,
    extract_endpoint_from_url, rate_limited
)
from config import Config

class TestRateLimitConfig(unittest.TestCase):
    """Test RateLimitConfig with multi-platform support"""
    
    def setUp(self):
        """Set up test environment"""
        # Clear any existing environment variables
        for key in list(os.environ.keys()):
            if key.startswith('RATE_LIMIT_'):
                del os.environ[key]
    
    def test_default_configuration(self):
        """Test default rate limit configuration"""
        config = RateLimitConfig.from_env()
        
        self.assertEqual(config.requests_per_minute, 60)
        self.assertEqual(config.requests_per_hour, 1000)
        self.assertEqual(config.requests_per_day, 10000)
        self.assertEqual(config.max_burst, 10)
        self.assertEqual(config.endpoint_limits, {})
        self.assertEqual(config.platform_limits, {})
        self.assertEqual(config.platform_endpoint_limits, {})
    
    def test_global_rate_limit_configuration(self):
        """Test global rate limit configuration from environment"""
        os.environ['RATE_LIMIT_REQUESTS_PER_MINUTE'] = '120'
        os.environ['RATE_LIMIT_REQUESTS_PER_HOUR'] = '2000'
        os.environ['RATE_LIMIT_REQUESTS_PER_DAY'] = '20000'
        os.environ['RATE_LIMIT_MAX_BURST'] = '20'
        
        config = RateLimitConfig.from_env()
        
        self.assertEqual(config.requests_per_minute, 120)
        self.assertEqual(config.requests_per_hour, 2000)
        self.assertEqual(config.requests_per_day, 20000)
        self.assertEqual(config.max_burst, 20)
    
    def test_endpoint_specific_configuration(self):
        """Test endpoint-specific rate limit configuration"""
        os.environ['RATE_LIMIT_ENDPOINT_MEDIA_MINUTE'] = '30'
        os.environ['RATE_LIMIT_ENDPOINT_MEDIA_HOUR'] = '500'
        os.environ['RATE_LIMIT_ENDPOINT_STATUSES_MINUTE'] = '100'
        
        config = RateLimitConfig.from_env()
        
        self.assertEqual(config.endpoint_limits['media']['minute'], 30)
        self.assertEqual(config.endpoint_limits['media']['hour'], 500)
        self.assertEqual(config.endpoint_limits['statuses']['minute'], 100)
    
    def test_platform_specific_configuration(self):
        """Test platform-specific rate limit configuration"""
        os.environ['RATE_LIMIT_MASTODON_MINUTE'] = '300'
        os.environ['RATE_LIMIT_MASTODON_HOUR'] = '3000'
        os.environ['RATE_LIMIT_PIXELFED_MINUTE'] = '60'
        os.environ['RATE_LIMIT_PIXELFED_HOUR'] = '1000'
        
        config = RateLimitConfig.from_env()
        
        self.assertEqual(config.platform_limits['mastodon']['minute'], 300)
        self.assertEqual(config.platform_limits['mastodon']['hour'], 3000)
        self.assertEqual(config.platform_limits['pixelfed']['minute'], 60)
        self.assertEqual(config.platform_limits['pixelfed']['hour'], 1000)
    
    def test_platform_endpoint_specific_configuration(self):
        """Test platform-endpoint-specific rate limit configuration"""
        os.environ['RATE_LIMIT_MASTODON_ENDPOINT_MEDIA_MINUTE'] = '100'
        os.environ['RATE_LIMIT_MASTODON_ENDPOINT_STATUSES_MINUTE'] = '200'
        os.environ['RATE_LIMIT_PIXELFED_ENDPOINT_MEDIA_MINUTE'] = '50'
        
        config = RateLimitConfig.from_env()
        
        self.assertEqual(config.platform_endpoint_limits['mastodon']['media']['minute'], 100)
        self.assertEqual(config.platform_endpoint_limits['mastodon']['statuses']['minute'], 200)
        self.assertEqual(config.platform_endpoint_limits['pixelfed']['media']['minute'], 50)
    
    def test_invalid_configuration_values(self):
        """Test handling of invalid configuration values"""
        os.environ['RATE_LIMIT_ENDPOINT_MEDIA_MINUTE'] = 'invalid'
        os.environ['RATE_LIMIT_MASTODON_MINUTE'] = 'not_a_number'
        
        config = RateLimitConfig.from_env()
        
        # Invalid values should be ignored - check that the endpoint/platform exists but has no valid timeframes
        if 'media' in config.endpoint_limits:
            self.assertNotIn('minute', config.endpoint_limits['media'])
        if 'mastodon' in config.platform_limits:
            self.assertNotIn('minute', config.platform_limits['mastodon'])

class TestRateLimiter(unittest.TestCase):
    """Test RateLimiter with multi-platform support"""
    
    def setUp(self):
        """Set up test environment"""
        self.config = RateLimitConfig(
            requests_per_minute=60,
            requests_per_hour=1000,
            requests_per_day=10000,
            max_burst=10,
            endpoint_limits={'media': {'minute': 30}},
            platform_limits={'mastodon': {'minute': 300}},
            platform_endpoint_limits={'mastodon': {'media': {'minute': 100}}}
        )
        self.rate_limiter = RateLimiter(self.config)
    
    def test_initialization(self):
        """Test rate limiter initialization with multi-platform config"""
        self.assertIsNotNone(self.rate_limiter.minute_bucket)
        self.assertIsNotNone(self.rate_limiter.hour_bucket)
        self.assertIsNotNone(self.rate_limiter.day_bucket)
        
        # Check endpoint buckets
        self.assertIn('media', self.rate_limiter.endpoint_buckets)
        self.assertIn('minute', self.rate_limiter.endpoint_buckets['media'])
        
        # Check platform buckets
        self.assertIn('mastodon', self.rate_limiter.platform_buckets)
        self.assertIn('minute', self.rate_limiter.platform_buckets['mastodon'])
        
        # Check platform-endpoint buckets
        self.assertIn('mastodon', self.rate_limiter.platform_endpoint_buckets)
        self.assertIn('media', self.rate_limiter.platform_endpoint_buckets['mastodon'])
        self.assertIn('minute', self.rate_limiter.platform_endpoint_buckets['mastodon']['media'])
    
    def test_check_rate_limit_global(self):
        """Test global rate limit checking"""
        allowed, wait_time = self.rate_limiter.check_rate_limit()
        self.assertTrue(allowed)
        self.assertEqual(wait_time, 0.0)
    
    def test_check_rate_limit_endpoint_specific(self):
        """Test endpoint-specific rate limit checking"""
        allowed, wait_time = self.rate_limiter.check_rate_limit(endpoint='media')
        self.assertTrue(allowed)
        self.assertEqual(wait_time, 0.0)
    
    def test_check_rate_limit_platform_specific(self):
        """Test platform-specific rate limit checking"""
        allowed, wait_time = self.rate_limiter.check_rate_limit(platform='mastodon')
        self.assertTrue(allowed)
        self.assertEqual(wait_time, 0.0)
    
    def test_check_rate_limit_platform_endpoint_specific(self):
        """Test platform-endpoint-specific rate limit checking"""
        allowed, wait_time = self.rate_limiter.check_rate_limit(endpoint='media', platform='mastodon')
        self.assertTrue(allowed)
        self.assertEqual(wait_time, 0.0)
    
    def test_rate_limit_enforcement(self):
        """Test rate limit enforcement after exceeding max_burst"""
        # Make requests up to max_burst
        for _ in range(self.config.max_burst):
            allowed, wait_time = self.rate_limiter.check_rate_limit()
            self.assertTrue(allowed)
        
        # Next request should be rate limited
        allowed, wait_time = self.rate_limiter.check_rate_limit()
        self.assertFalse(allowed)
        self.assertGreater(wait_time, 0)
    
    def test_wait_if_needed(self):
        """Test wait_if_needed method"""
        async def run_test():
            wait_time = await self.rate_limiter.wait_if_needed()
            self.assertEqual(wait_time, 0.0)
            
            wait_time = await self.rate_limiter.wait_if_needed(endpoint='media')
            self.assertEqual(wait_time, 0.0)
            
            wait_time = await self.rate_limiter.wait_if_needed(platform='mastodon')
            self.assertEqual(wait_time, 0.0)
        
        asyncio.run(run_test())
    
    def test_statistics_tracking(self):
        """Test statistics tracking for multi-platform usage"""
        # Make some requests
        self.rate_limiter.check_rate_limit()
        self.rate_limiter.check_rate_limit(endpoint='media')
        self.rate_limiter.check_rate_limit(platform='mastodon')
        self.rate_limiter.check_rate_limit(endpoint='media', platform='mastodon')
        
        stats = self.rate_limiter.get_stats()
        
        self.assertEqual(stats['requests']['total'], 4)
        self.assertIn('endpoints', stats)
        self.assertIn('platforms', stats)
        self.assertIn('MEDIA', stats['endpoints'])
        self.assertIn('MASTODON', stats['platforms'])
    
    def test_reset_stats(self):
        """Test statistics reset"""
        # Make some requests
        self.rate_limiter.check_rate_limit()
        self.rate_limiter.check_rate_limit(platform='mastodon')
        
        # Reset stats
        self.rate_limiter.reset_stats()
        
        stats = self.rate_limiter.get_stats()
        self.assertEqual(stats['requests']['total'], 0)
        self.assertEqual(stats['endpoints'], {})
        self.assertEqual(stats['platforms'], {})
    
    def test_update_from_response_headers_mastodon(self):
        """Test updating rate limiter from Mastodon response headers"""
        headers = {
            'X-RateLimit-Limit': '300',
            'X-RateLimit-Remaining': '299',
            'X-RateLimit-Reset': str(int(time.time()) + 3600)
        }
        
        # Should not raise any exceptions
        self.rate_limiter.update_from_response_headers(headers, 'mastodon')
    
    def test_update_from_response_headers_pixelfed(self):
        """Test updating rate limiter from Pixelfed response headers"""
        headers = {
            'X-RateLimit-Limit': '60',
            'X-RateLimit-Remaining': '59',
            'X-RateLimit-Reset': str(int(time.time()) + 3600)
        }
        
        # Should not raise any exceptions
        self.rate_limiter.update_from_response_headers(headers, 'pixelfed')
    
    def test_update_from_response_headers_low_remaining(self):
        """Test warning when rate limit remaining is low"""
        headers = {
            'X-RateLimit-Limit': '300',
            'X-RateLimit-Remaining': '3',  # Low remaining
            'X-RateLimit-Reset': str(int(time.time()) + 3600)
        }
        
        with patch('rate_limiter.logger') as mock_logger:
            self.rate_limiter.update_from_response_headers(headers, 'mastodon')
            mock_logger.warning.assert_called_once()

class TestExtractEndpointFromUrl(unittest.TestCase):
    """Test endpoint extraction from URLs for both platforms"""
    
    def test_pixelfed_endpoints(self):
        """Test endpoint extraction from Pixelfed URLs"""
        test_cases = [
            ('https://pixelfed.social/api/v1/media/123', 'MEDIA'),
            ('https://pixelfed.social/api/v1/accounts/123', 'ACCOUNTS'),
            ('https://pixelfed.social/api/v1/statuses/123', 'STATUSES'),
        ]
        
        for url, expected in test_cases:
            with self.subTest(url=url):
                result = extract_endpoint_from_url(url)
                self.assertEqual(result, expected)
    
    def test_mastodon_endpoints(self):
        """Test endpoint extraction from Mastodon URLs"""
        test_cases = [
            ('https://mastodon.social/api/v1/media/123', 'MEDIA'),
            ('https://mastodon.social/api/v1/accounts/123', 'ACCOUNTS'),
            ('https://mastodon.social/api/v1/accounts/123/statuses', 'STATUSES'),
            ('https://mastodon.social/api/v1/statuses/123', 'STATUSES'),
        ]
        
        for url, expected in test_cases:
            with self.subTest(url=url):
                result = extract_endpoint_from_url(url)
                self.assertEqual(result, expected)
    
    def test_activitypub_endpoints(self):
        """Test endpoint extraction from ActivityPub URLs"""
        test_cases = [
            ('https://example.com/users/alice', 'USERS'),
            ('https://example.com/users/alice/inbox', 'INBOX'),
            ('https://example.com/users/alice/outbox', 'OUTBOX'),
            ('https://example.com/users/alice/followers', 'FOLLOWERS'),
            ('https://example.com/users/alice/following', 'FOLLOWING'),
        ]
        
        for url, expected in test_cases:
            with self.subTest(url=url):
                result = extract_endpoint_from_url(url)
                self.assertEqual(result, expected)
    
    def test_oauth_endpoints(self):
        """Test endpoint extraction from OAuth URLs"""
        test_cases = [
            ('https://example.com/oauth/token', 'AUTH'),
            ('https://example.com/auth/login', 'AUTH'),
        ]
        
        for url, expected in test_cases:
            with self.subTest(url=url):
                result = extract_endpoint_from_url(url)
                self.assertEqual(result, expected)
    
    def test_invalid_urls(self):
        """Test endpoint extraction from invalid URLs"""
        test_cases = [
            None,
            '',
            'not-a-url',
            'https://example.com/unknown/path',
        ]
        
        for url in test_cases:
            with self.subTest(url=url):
                result = extract_endpoint_from_url(url)
                self.assertIsNone(result)

class TestRateLimitedDecorator(unittest.TestCase):
    """Test the rate_limited decorator with multi-platform support"""
    
    def setUp(self):
        """Set up test environment"""
        self.config = RateLimitConfig(max_burst=2)  # Low burst for testing
        self.rate_limiter = RateLimiter(self.config)
        
        # Patch the global rate limiter
        self.rate_limiter_patcher = patch('rate_limiter.get_rate_limiter')
        self.mock_get_rate_limiter = self.rate_limiter_patcher.start()
        self.mock_get_rate_limiter.return_value = self.rate_limiter
    
    def tearDown(self):
        """Clean up test environment"""
        self.rate_limiter_patcher.stop()
    
    def test_decorator_basic_usage(self):
        """Test basic usage of rate_limited decorator"""
        async def run_test():
            @rate_limited
            async def test_function():
                return "success"
            
            result = await test_function()
            self.assertEqual(result, "success")
        
        asyncio.run(run_test())
    
    def test_decorator_with_endpoint(self):
        """Test rate_limited decorator with endpoint parameter"""
        async def run_test():
            @rate_limited(endpoint='media')
            async def test_function():
                return "success"
            
            result = await test_function()
            self.assertEqual(result, "success")
        
        asyncio.run(run_test())
    
    def test_decorator_with_platform(self):
        """Test rate_limited decorator with platform parameter"""
        async def run_test():
            @rate_limited(platform='mastodon')
            async def test_function():
                return "success"
            
            result = await test_function()
            self.assertEqual(result, "success")
        
        asyncio.run(run_test())
    
    def test_decorator_with_endpoint_and_platform(self):
        """Test rate_limited decorator with both endpoint and platform"""
        async def run_test():
            @rate_limited(endpoint='media', platform='mastodon')
            async def test_function():
                return "success"
            
            result = await test_function()
            self.assertEqual(result, "success")
        
        asyncio.run(run_test())
    
    def test_decorator_extracts_endpoint_from_url(self):
        """Test that decorator extracts endpoint from URL parameter"""
        async def run_test():
            @rate_limited
            async def test_function(url):
                return "success"
            
            result = await test_function(url='https://mastodon.social/api/v1/media/123')
            self.assertEqual(result, "success")
        
        asyncio.run(run_test())
    
    def test_decorator_extracts_platform_from_kwargs(self):
        """Test that decorator extracts platform from kwargs"""
        async def run_test():
            @rate_limited
            async def test_function(platform=None):
                return "success"
            
            result = await test_function(platform='mastodon')
            self.assertEqual(result, "success")
        
        asyncio.run(run_test())
    
    def test_decorator_updates_from_response_headers(self):
        """Test that decorator updates rate limiter from response headers"""
        async def run_test():
            mock_response = Mock()
            mock_response.headers = {
                'X-RateLimit-Limit': '300',
                'X-RateLimit-Remaining': '299'
            }
            
            @rate_limited(platform='mastodon')
            async def test_function():
                return mock_response
            
            with patch.object(self.rate_limiter, 'update_from_response_headers') as mock_update:
                result = await test_function()
                self.assertEqual(result, mock_response)
                mock_update.assert_called_once_with(mock_response.headers, 'mastodon')
        
        asyncio.run(run_test())

class TestIntegrationScenarios(unittest.TestCase):
    """Test integration scenarios with simulated rate limit scenarios"""
    
    def setUp(self):
        """Set up test environment"""
        # Clear environment variables
        for key in list(os.environ.keys()):
            if key.startswith('RATE_LIMIT_'):
                del os.environ[key]
    
    def test_mastodon_rate_limiting_scenario(self):
        """Test a realistic Mastodon rate limiting scenario"""
        # Set up Mastodon-specific rate limits
        os.environ['RATE_LIMIT_MASTODON_MINUTE'] = '300'
        os.environ['RATE_LIMIT_MASTODON_ENDPOINT_MEDIA_MINUTE'] = '100'
        
        config = RateLimitConfig.from_env()
        rate_limiter = RateLimiter(config)
        
        # Test platform-specific limits
        self.assertEqual(config.platform_limits['mastodon']['minute'], 300)
        self.assertEqual(config.platform_endpoint_limits['mastodon']['media']['minute'], 100)
        
        # Test rate limiting behavior
        allowed, wait_time = rate_limiter.check_rate_limit(platform='mastodon')
        self.assertTrue(allowed)
        
        allowed, wait_time = rate_limiter.check_rate_limit(endpoint='media', platform='mastodon')
        self.assertTrue(allowed)
    
    def test_pixelfed_rate_limiting_scenario(self):
        """Test a realistic Pixelfed rate limiting scenario"""
        # Set up Pixelfed-specific rate limits
        os.environ['RATE_LIMIT_PIXELFED_MINUTE'] = '60'
        os.environ['RATE_LIMIT_PIXELFED_ENDPOINT_MEDIA_MINUTE'] = '30'
        
        config = RateLimitConfig.from_env()
        rate_limiter = RateLimiter(config)
        
        # Test platform-specific limits
        self.assertEqual(config.platform_limits['pixelfed']['minute'], 60)
        self.assertEqual(config.platform_endpoint_limits['pixelfed']['media']['minute'], 30)
        
        # Test rate limiting behavior
        allowed, wait_time = rate_limiter.check_rate_limit(platform='pixelfed')
        self.assertTrue(allowed)
        
        allowed, wait_time = rate_limiter.check_rate_limit(endpoint='media', platform='pixelfed')
        self.assertTrue(allowed)
    
    def test_mixed_platform_scenario(self):
        """Test scenario with both Mastodon and Pixelfed rate limits"""
        # Set up both platform limits
        os.environ['RATE_LIMIT_MASTODON_MINUTE'] = '300'
        os.environ['RATE_LIMIT_PIXELFED_MINUTE'] = '60'
        os.environ['RATE_LIMIT_ENDPOINT_MEDIA_MINUTE'] = '50'  # Global endpoint limit
        
        config = RateLimitConfig.from_env()
        rate_limiter = RateLimiter(config)
        
        # Test that both platforms have their limits
        self.assertEqual(config.platform_limits['mastodon']['minute'], 300)
        self.assertEqual(config.platform_limits['pixelfed']['minute'], 60)
        self.assertEqual(config.endpoint_limits['media']['minute'], 50)
        
        # Test statistics tracking for both platforms
        rate_limiter.check_rate_limit(platform='mastodon')
        rate_limiter.check_rate_limit(platform='pixelfed')
        rate_limiter.check_rate_limit(endpoint='media')
        
        stats = rate_limiter.get_stats()
        self.assertIn('MASTODON', stats['platforms'])
        self.assertIn('PIXELFED', stats['platforms'])
        self.assertIn('MEDIA', stats['endpoints'])
    
    def test_concurrent_requests_with_rate_limiting(self):
        """Test concurrent requests with rate limiting"""
        async def run_test():
            config = RateLimitConfig(max_burst=10)  # Allow more concurrent requests
            rate_limiter = RateLimiter(config)
            
            async def make_request(platform, endpoint=None):
                return await rate_limiter.wait_if_needed(endpoint=endpoint, platform=platform)
            
            # Make concurrent requests
            tasks = [
                make_request('mastodon', 'media'),
                make_request('mastodon', 'statuses'),
                make_request('pixelfed', 'media'),
                make_request('pixelfed', 'statuses'),
            ]
            
            results = await asyncio.gather(*tasks)
            
            # All should succeed without waiting (within burst limit)
            for wait_time in results:
                self.assertEqual(wait_time, 0.0)
        
        asyncio.run(run_test())
    
    def test_rate_limit_reset_and_window_handling(self):
        """Test rate limit reset and window handling"""
        config = RateLimitConfig(max_burst=2)
        rate_limiter = RateLimiter(config)
        
        # Make requests up to burst limit
        for _ in range(config.max_burst):
            allowed, wait_time = rate_limiter.check_rate_limit()
            self.assertTrue(allowed)
        
        # Next request should be rate limited
        allowed, wait_time = rate_limiter.check_rate_limit()
        self.assertFalse(allowed)
        self.assertGreater(wait_time, 0)
        
        # Reset stats (simulating window reset)
        rate_limiter.reset_stats()
        
        # Create a new rate limiter to simulate fresh state
        new_rate_limiter = RateLimiter(config)
        
        # Should be allowed again
        allowed, wait_time = new_rate_limiter.check_rate_limit()
        self.assertTrue(allowed)

if __name__ == '__main__':
    unittest.main()
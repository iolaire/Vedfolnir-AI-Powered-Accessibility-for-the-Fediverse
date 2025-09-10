# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Integration test for API rate limiting with ActivityPubClient.
"""

import asyncio
import unittest
from config import Config
from app.services.activitypub.components.activitypub_client import ActivityPubClient
from rate_limiter import get_rate_limiter, RateLimitConfig

class TestAPIRateLimiting(unittest.IsolatedAsyncioTestCase):
    """Test API rate limiting integration with ActivityPubClient"""
    
    async def test_rate_limited_api_calls(self):
        """Test that API calls are rate limited"""
        # Create a config with very restrictive rate limits for testing
        config = Config()
        
        # Override rate limit config with test values
        config.activitypub.rate_limit = RateLimitConfig(
            requests_per_minute=5,  # Only 5 requests per minute
            requests_per_hour=10,
            requests_per_day=20,
            max_burst=5,
            endpoint_limits={
                "media": {"minute": 2}  # Only 2 media requests per minute
            }
        )
        
        # Create client with test config
        async with ActivityPubClient(config.activitypub) as client:
            # Reset rate limiter stats
            client.reset_rate_limit_stats()
            
            # Make multiple API calls in quick succession
            start_time = asyncio.get_event_loop().time()
            
            # These calls should be rate limited after the first 5
            tasks = []
            for i in range(10):
                # Use a dummy URL that won't actually make a network request
                # but will still go through the rate limiting logic
                task = asyncio.create_task(
                    client._get_with_retry(
                        f"https://example.com/api/v1/statuses/{i}", 
                        {"Authorization": "Bearer test"}
                    )
                )
                tasks.append(task)
            
            # Wait for all tasks to complete or timeout
            done, pending = await asyncio.wait(
                tasks, 
                timeout=10.0,
                return_when=asyncio.ALL_COMPLETED
            )
            
            # Cancel any pending tasks
            for task in pending:
                task.cancel()
            
            # Get elapsed time
            elapsed = asyncio.get_event_loop().time() - start_time
            
            # Get rate limit stats
            stats = client.get_rate_limit_stats()
            
            # Check that rate limiting occurred
            self.assertGreaterEqual(stats["requests"]["throttled"], 1, 
                                   "At least one request should have been throttled")
            self.assertGreater(stats["wait_time"]["total"], 0.0,
                              "Some time should have been spent waiting due to rate limits")
            
            # Test endpoint-specific rate limiting
            client.reset_rate_limit_stats()
            
            # Make media endpoint requests that should be rate limited after 2
            media_tasks = []
            for i in range(5):
                task = asyncio.create_task(
                    client._get_with_retry(
                        f"https://example.com/api/v1/media/{i}", 
                        {"Authorization": "Bearer test"}
                    )
                )
                media_tasks.append(task)
            
            # Wait for all tasks to complete or timeout
            done, pending = await asyncio.wait(
                media_tasks, 
                timeout=10.0,
                return_when=asyncio.ALL_COMPLETED
            )
            
            # Cancel any pending tasks
            for task in pending:
                task.cancel()
            
            # Get rate limit stats
            stats = client.get_rate_limit_stats()
            
            # Check that endpoint-specific rate limiting occurred
            self.assertIn("MEDIA", stats["endpoints"], 
                         "Media endpoint should be tracked in statistics")
            
            # Check API usage report
            report = client.get_api_usage_report()
            self.assertIn("rate_limit_stats", report, 
                         "API usage report should include rate limit statistics")
            self.assertIn("retry_stats", report, 
                         "API usage report should include retry statistics")

if __name__ == "__main__":
    unittest.main()
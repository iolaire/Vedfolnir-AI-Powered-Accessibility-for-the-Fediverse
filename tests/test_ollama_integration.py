# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
import unittest
import asyncio
import os
import sys
from unittest.mock import patch, MagicMock, AsyncMock
import httpx
from dataclasses import dataclass

# Add parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ollama_caption_generator import OllamaCaptionGenerator
from config import OllamaConfig, RetryConfig

class TestOllamaIntegration(unittest.TestCase):
    """Test cases for Ollama integration"""

    def setUp(self):
        """Set up test environment"""
        # Create a test config
        self.retry_config = RetryConfig(
            max_attempts=3,
            base_delay=0.1,
            max_delay=1.0,
            backoff_factor=2.0,
            jitter=True,
            jitter_factor=0.1
        )
        
        self.config = OllamaConfig(
            url="http://test-ollama-url:11434",
            model_name="test-model",
            timeout=1.0,
            retry=self.retry_config
        )
        
        # Create the caption generator with the test config
        self.caption_generator = OllamaCaptionGenerator(self.config)

    @patch('httpx.AsyncClient.get')
    @patch('httpx.AsyncClient.post')
    async def test_initialize_success(self, mock_post, mock_get):
        """Test successful initialization of Ollama caption generator"""
        # Mock the API responses
        mock_get.return_value = AsyncMock()
        mock_get.return_value.status_code = 200
        mock_get.return_value.raise_for_status = AsyncMock()
        mock_get.return_value.json.return_value = {
            "models": [
                {"name": "test-model", "size": 123456789}
            ]
        }
        
        mock_post.return_value = AsyncMock()
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status = AsyncMock()
        mock_post.return_value.json.return_value = {
            "name": "test-model",
            "size": 123456789,
            "modified_at": "2023-01-01T00:00:00Z"
        }
        
        # Call initialize
        await self.caption_generator.initialize()
        
        # Verify the connection was validated
        self.assertTrue(self.caption_generator.connection_validated)
        self.assertIsNotNone(self.caption_generator.model_info)
        
        # Verify the API calls
        mock_get.assert_called_once_with(f"{self.config.url}/api/tags")
        mock_post.assert_called_once()

    @patch('httpx.AsyncClient.get')
    async def test_initialize_connection_error(self, mock_get):
        """Test initialization with connection error"""
        # Mock the API response to raise an error
        mock_get.side_effect = httpx.ConnectError("Connection refused")
        
        # Call initialize and expect an exception
        with self.assertRaises(httpx.ConnectError):
            await self.caption_generator.initialize()
        
        # Verify the connection was not validated
        self.assertFalse(self.caption_generator.connection_validated)

    @patch('httpx.AsyncClient.post')
    async def test_generate_caption_success(self, mock_post):
        """Test successful caption generation"""
        # Set up the caption generator
        self.caption_generator.connection_validated = True
        # Classification removed - using general prompt only
        
        # Mock the API response
        mock_post.return_value = AsyncMock()
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status = AsyncMock()
        mock_post.return_value.json.return_value = {
            "response": "This is a test caption",
            "eval_count": 100,
            "eval_duration": 500
        }
        
        # Create a temporary test image file
        test_image_path = "test_image.jpg"
        with open(test_image_path, "wb") as f:
            f.write(b"test image data")
        
        try:
            # Call generate_caption
            caption = await self.caption_generator.generate_caption(test_image_path)
            
            # Verify the caption was generated
            self.assertEqual(caption, "This is a test caption")
            
            # Verify the API call
            mock_post.assert_called_once()
            
            # Verify retry stats
            stats = self.caption_generator.get_retry_stats()
            self.assertEqual(stats["attempts"], 1)
            self.assertEqual(stats["successes"], 1)
            self.assertEqual(stats["failures"], 0)
        finally:
            # Clean up the test image
            if os.path.exists(test_image_path):
                os.remove(test_image_path)

    @patch('httpx.AsyncClient.post')
    async def test_generate_caption_with_retry(self, mock_post):
        """Test caption generation with retry"""
        # Set up the caption generator
        self.caption_generator.connection_validated = True
        # Classification removed - using general prompt only
        
        # Mock the API response to fail once then succeed
        mock_post.side_effect = [
            httpx.ConnectError("Connection reset"),
            AsyncMock(
                status_code=200,
                raise_for_status=AsyncMock(),
                json=AsyncMock(return_value={
                    "response": "This is a test caption after retry",
                    "eval_count": 100,
                    "eval_duration": 500
                })
            )
        ]
        
        # Create a temporary test image file
        test_image_path = "test_image.jpg"
        with open(test_image_path, "wb") as f:
            f.write(b"test image data")
        
        try:
            # Call generate_caption
            caption = await self.caption_generator.generate_caption(test_image_path)
            
            # Verify the caption was generated
            self.assertEqual(caption, "This is a test caption after retry")
            
            # Verify the API was called twice (once for the error, once for success)
            self.assertEqual(mock_post.call_count, 2)
            
            # Verify retry stats
            stats = self.caption_generator.get_retry_stats()
            self.assertEqual(stats["attempts"], 2)
            self.assertEqual(stats["successes"], 1)
            self.assertEqual(stats["failures"], 0)
        finally:
            # Clean up the test image
            if os.path.exists(test_image_path):
                os.remove(test_image_path)

    @patch('httpx.AsyncClient.post')
    async def test_generate_caption_max_retries_exceeded(self, mock_post):
        """Test caption generation with max retries exceeded"""
        # Set up the caption generator
        self.caption_generator.connection_validated = True
        # Classification removed - using general prompt only
        
        # Mock the API response to always fail
        mock_post.side_effect = httpx.ConnectError("Connection refused")
        
        # Create a temporary test image file
        test_image_path = "test_image.jpg"
        with open(test_image_path, "wb") as f:
            f.write(b"test image data")
        
        try:
            # Call generate_caption
            caption = await self.caption_generator.generate_caption(test_image_path)
            
            # Verify no caption was generated
            self.assertIsNone(caption)
            
            # Verify the API was called max_attempts times
            self.assertEqual(mock_post.call_count, self.config.retry.max_attempts)
            
            # Verify retry stats
            stats = self.caption_generator.get_retry_stats()
            self.assertEqual(stats["attempts"], self.config.retry.max_attempts)
            self.assertEqual(stats["successes"], 0)
            self.assertEqual(stats["failures"], 1)
        finally:
            # Clean up the test image
            if os.path.exists(test_image_path):
                os.remove(test_image_path)

    def test_get_retry_stats_summary(self):
        """Test getting retry stats summary"""
        # Set up some retry stats
        self.caption_generator.retry_stats = {
            "attempts": 10,
            "successes": 8,
            "failures": 2,
            "total_retry_time": 5.5
        }
        
        # Get the summary
        summary = self.caption_generator.get_retry_stats_summary()
        
        # Verify the summary contains the expected information
        self.assertIn("10 attempts", summary)
        self.assertIn("8 successes", summary)
        self.assertIn("2 failures", summary)
        self.assertIn("80.0%", summary)  # Success rate

def run_tests():
    """Run the tests"""
    unittest.main()

if __name__ == "__main__":
    # Run the async tests
    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(asyncio.gather(
        *[test() for test in [
            TestOllamaIntegration().test_initialize_success,
            TestOllamaIntegration().test_initialize_connection_error,
            TestOllamaIntegration().test_generate_caption_success,
            TestOllamaIntegration().test_generate_caption_with_retry,
            TestOllamaIntegration().test_generate_caption_max_retries_exceeded
        ]]
    ))
    
    # Run the sync tests
    unittest.main()
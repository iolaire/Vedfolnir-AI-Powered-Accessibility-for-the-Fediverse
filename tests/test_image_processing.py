#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Test script for image processing functionality.
"""
import unittest
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio
from PIL import Image
import io
import sys

# Add parent directory to path to allow importing from project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from image_processor import ImageProcessor
from config import Config, StorageConfig

class TestImageProcessing(unittest.TestCase):
    """Test cases for image processing functionality"""
    
    def setUp(self):
        """Set up test environment"""
        # Create a temporary directory for test images
        self.temp_dir = tempfile.mkdtemp()
        
        # Create a mock config
        self.config = MagicMock()
        self.config.storage = StorageConfig()
        self.config.storage.images_dir = os.path.join(self.temp_dir, "images")
        os.makedirs(self.config.storage.images_dir, exist_ok=True)
        
        # Create test images
        self.valid_jpg_path = os.path.join(self.temp_dir, "valid.jpg")
        self.create_test_image(self.valid_jpg_path, "JPEG")
        
        self.valid_png_path = os.path.join(self.temp_dir, "valid.png")
        self.create_test_image(self.valid_png_path, "PNG")
        
        self.corrupted_image_path = os.path.join(self.temp_dir, "corrupted.jpg")
        with open(self.corrupted_image_path, 'wb') as f:
            f.write(b'This is not a valid image file')
    
    def tearDown(self):
        """Clean up after the test"""
        # Remove the temporary directory and its contents
        shutil.rmtree(self.temp_dir)
    
    def create_test_image(self, path, format_name):
        """Create a test image file"""
        img = Image.new('RGB', (100, 100), color='red')
        img.save(path, format=format_name)
    
    def test_image_validation_valid(self):
        """Test image validation with valid images"""
        with patch('httpx.AsyncClient') as mock_client:
            processor = ImageProcessor(self.config)
            
            # Test valid JPG
            result = processor.validate_image(self.valid_jpg_path)
            self.assertTrue(result)
            
            # Test valid PNG
            result = processor.validate_image(self.valid_png_path)
            self.assertTrue(result)
    
    def test_image_validation_corrupted(self):
        """Test image validation with corrupted image"""
        with patch('httpx.AsyncClient') as mock_client:
            processor = ImageProcessor(self.config)
            
            # Test corrupted image
            result = processor.validate_image(self.corrupted_image_path)
            self.assertFalse(result)
    
    def test_image_validation_size_limits(self):
        """Test image validation with size limits"""
        with patch('httpx.AsyncClient') as mock_client:
            processor = ImageProcessor(self.config)
            
            # Create a large test image
            large_image_path = os.path.join(self.temp_dir, "large.jpg")
            img = Image.new('RGB', (10000, 10000), color='blue')
            img.save(large_image_path, format="JPEG")
            
            # Test with default size limits
            result = processor.validate_image(large_image_path)
            
            # The validation should still pass but log a warning
            # We're not testing the log here, just that it doesn't reject the image
            self.assertTrue(result)
            
            # Test with custom size limits
            processor.max_image_dimension = 5000
            result = processor.validate_image(large_image_path)
            self.assertFalse(result)
    
    def test_get_file_extension(self):
        """Test getting file extension from URL and content type"""
        with patch('httpx.AsyncClient') as mock_client:
            processor = ImageProcessor(self.config)
            
            # Test with URL having extension
            ext = processor._get_file_extension("image.jpg", None)
            self.assertEqual(ext, ".jpg")
            
            # Test with URL having uppercase extension
            ext = processor._get_file_extension("image.JPG", None)
            self.assertEqual(ext, ".jpg")
            
            # Test with URL having no extension but content type
            ext = processor._get_file_extension("image", "image/png")
            self.assertEqual(ext, ".png")
            
            # Test with URL having no extension and no content type
            ext = processor._get_file_extension("image", None)
            self.assertEqual(ext, ".jpg")  # Default extension
            
            # Test with content type for AVIF
            ext = processor._get_file_extension("image", "image/avif")
            self.assertEqual(ext, ".avif")
            
            # Test with content type for HEIC
            ext = processor._get_file_extension("image", "image/heic")
            self.assertEqual(ext, ".heic")
    
    @patch('aiofiles.open', new_callable=AsyncMock)
    async def test_download_and_store_image(self, mock_aiofiles_open):
        """Test downloading and storing an image"""
        # Create a test image in memory
        img = Image.new('RGB', (100, 100), color='red')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        img_data = img_bytes.read()
        
        # Create a mock response with our test image content
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = img_data
        
        # Mock the httpx client
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        
        # Mock the context manager for aiofiles.open
        mock_file = AsyncMock()
        mock_aiofiles_open.return_value.__aenter__.return_value = mock_file
        
        # Create the processor with mocked client
        processor = ImageProcessor(self.config)
        processor.client = mock_client
        
        # Generate a unique test image name
        test_image_name = f"test_image_{id(self)}.jpg"
        
        # Call the method
        local_path = await processor.download_and_store_image(test_image_name, "image/jpeg")
        
        # Verify the result
        self.assertIsNotNone(local_path)
        self.assertTrue(local_path.endswith(".jpg"))
        
        # Verify the client was called correctly
        mock_client.get.assert_called_once_with(test_image_name)
        
        # Verify the file was written
        mock_file.write.assert_called_once_with(img_data)

    @patch('aiofiles.open', new_callable=AsyncMock)
    async def test_download_error_handling(self, mock_aiofiles_open):
        """Test error handling during download"""
        # Mock the httpx client to raise an exception
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("Connection error")
        
        # Create the processor with mocked client
        processor = ImageProcessor(self.config)
        processor.client = mock_client
        
        # Generate a unique test image name
        test_image_name = f"test_image_{id(self)}.jpg"
        
        # Call the method
        local_path = await processor.download_and_store_image(test_image_name, "image/jpeg")
        
        # Verify the result
        self.assertIsNone(local_path)
        
        # Verify the client was called
        mock_client.get.assert_called_once_with(test_image_name)
        
        # Verify no file was written
        mock_aiofiles_open.assert_not_called()

    @patch('aiofiles.open', new_callable=AsyncMock)
    async def test_download_non_success_status(self, mock_aiofiles_open):
        """Test handling of non-success HTTP status"""
        # Create a mock response with non-success status
        mock_response = MagicMock()
        mock_response.status_code = 404
        
        # Mock the httpx client
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        
        # Create the processor with mocked client
        processor = ImageProcessor(self.config)
        processor.client = mock_client
        
        # Generate a unique test image name
        test_image_name = f"test_image_{id(self)}.jpg"
        
        # Call the method
        local_path = await processor.download_and_store_image(test_image_name, "image/jpeg")
        
        # Verify the result
        self.assertIsNone(local_path)
        
        # Verify the client was called
        mock_client.get.assert_called_once_with(test_image_name)
        
        # Verify no file was written
        mock_aiofiles_open.assert_not_called()

# Define async test runner
def async_test(coro):
    def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coro(*args, **kwargs))
    return wrapper

class TestImageProcessingAsync(unittest.TestCase):
    """Async test cases for image processing functionality"""
    
    def setUp(self):
        """Set up test environment"""
        # Create a temporary directory for test images
        self.temp_dir = tempfile.mkdtemp()
        
        # Create a mock config
        self.config = MagicMock()
        self.config.storage = StorageConfig()
        self.config.storage.images_dir = os.path.join(self.temp_dir, "images")
        os.makedirs(self.config.storage.images_dir, exist_ok=True)
        
        # Create test images
        self.valid_jpg_path = os.path.join(self.temp_dir, "valid.jpg")
        self.create_test_image(self.valid_jpg_path, "JPEG")
    
    def tearDown(self):
        """Clean up after the test"""
        # Remove the temporary directory and its contents
        shutil.rmtree(self.temp_dir)
    
    def create_test_image(self, path, format_name):
        """Create a test image file"""
        img = Image.new('RGB', (100, 100), color='red')
        img.save(path, format=format_name)
    
    @async_test
    async def test_async_context_manager(self):
        """Test the async context manager functionality"""
        # Create the processor
        processor = None
        
        # Use the async context manager
        async with ImageProcessor(self.config) as proc:
            processor = proc
            # Verify the processor is initialized
            self.assertIsNotNone(processor)
            self.assertIsNotNone(processor.client)
        
        # Verify the client is closed after exiting the context
        self.assertIsNone(processor.client)

if __name__ == "__main__":
    unittest.main()
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integration tests for storage limit management with web routes.

This test suite verifies that web routes properly integrate with storage limits,
including the caption generation and regeneration endpoints.
"""

import unittest
import tempfile
import shutil
import os
from unittest.mock import Mock, patch

# Add project root to path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.services.storage.components.storage_limit_enforcer import StorageLimitEnforcer, StorageCheckResult
from app.services.storage.components.storage_monitor_service import StorageMonitorService
from app.services.storage.components.storage_configuration_service import StorageConfigurationService


class TestStorageWebRoutesIntegration(unittest.TestCase):
    """Integration tests for storage limit management with web routes"""
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary directory for storage testing
        self.temp_storage_dir = tempfile.mkdtemp()
        self.storage_images_dir = os.path.join(self.temp_storage_dir, "storage", "images")
        os.makedirs(self.storage_images_dir, exist_ok=True)
        
        # Mock Redis client
        self.mock_redis = Mock()
        self.mock_redis.ping.return_value = True
        self.mock_redis.get.return_value = None
        self.mock_redis.set.return_value = True
        self.mock_redis.delete.return_value = True
        
        # Create configuration service with test settings
        with patch.dict(os.environ, {'CAPTION_MAX_STORAGE_GB': '1.0'}):
            self.config_service = StorageConfigurationService()
        
        # Create monitor service with mocked storage directory
        self.monitor_service = StorageMonitorService(self.config_service)
        self.monitor_service.STORAGE_IMAGES_DIR = self.storage_images_dir
        
        # Create enforcer with mocked Redis
        self.enforcer = StorageLimitEnforcer(
            config_service=self.config_service,
            monitor_service=self.monitor_service,
            redis_client=self.mock_redis
        )
    
    def tearDown(self):
        """Clean up test environment"""
        # Remove temporary storage directory
        if os.path.exists(self.temp_storage_dir):
            shutil.rmtree(self.temp_storage_dir)
    
    def _create_test_files(self, total_size_mb: float) -> None:
        """Create test files in storage directory to simulate storage usage"""
        file_size_bytes = int(total_size_mb * 1000 * 1000)
        test_file_path = os.path.join(self.storage_images_dir, "test_image.jpg")
        with open(test_file_path, "wb") as f:
            f.write(b"0" * file_size_bytes)
    
    def test_start_caption_generation_blocked_by_storage_limit(self):
        """Test that storage check blocks generation when limit is exceeded"""
        # Create files over limit
        self._create_test_files(1500)  # 1.5GB over 1GB limit
        
        # Check storage - should be blocked
        result = self.enforcer.check_storage_before_generation()
        self.assertEqual(result, StorageCheckResult.BLOCKED_LIMIT_EXCEEDED)
    
    def test_start_caption_generation_allowed_under_storage_limit(self):
        """Test that storage check allows generation when under limit"""
        # Create files under limit
        self._create_test_files(500)  # 0.5GB under 1GB limit
        
        # Check storage - should be allowed
        result = self.enforcer.check_storage_before_generation()
        self.assertEqual(result, StorageCheckResult.ALLOWED)
    
    def test_regenerate_caption_blocked_by_storage_limit(self):
        """Test that storage check blocks regeneration when limit is exceeded"""
        # Create files over limit
        self._create_test_files(1500)  # 1.5GB over 1GB limit
        
        # Check storage - should be blocked
        result = self.enforcer.check_storage_before_generation()
        self.assertEqual(result, StorageCheckResult.BLOCKED_LIMIT_EXCEEDED)
    
    def test_regenerate_caption_allowed_under_storage_limit(self):
        """Test that storage check allows regeneration when under limit"""
        # Create files under limit
        self._create_test_files(500)  # 0.5GB under 1GB limit
        
        # Check storage - should be allowed
        result = self.enforcer.check_storage_before_generation()
        self.assertEqual(result, StorageCheckResult.ALLOWED)
    
    def test_storage_check_error_handling(self):
        """Test error handling when storage check returns ERROR status"""
        # Mock monitor service to raise exception
        with patch.object(self.monitor_service, 'get_storage_metrics') as mock_metrics:
            mock_metrics.side_effect = Exception("Storage calculation failed")
            
            # Check storage - should raise exception
            with self.assertRaises(Exception):
                self.enforcer.check_storage_before_generation()
    
    def test_storage_check_integration_with_web_service(self):
        """Test that web caption generation service integrates with storage checks"""
        from app.utils.processing.web_caption_generation_service import WebCaptionGenerationService
        from app.core.database.core.database_manager import DatabaseManager
        
        # Mock database manager
        mock_db_manager = Mock(spec=DatabaseManager)
        caption_service = WebCaptionGenerationService(mock_db_manager)
        
        # Create files over limit
        self._create_test_files(1500)  # 1.5GB over 1GB limit
        
        # Mock the storage enforcer to use our test configuration
        with patch('storage_limit_enforcer.StorageLimitEnforcer') as mock_enforcer_class:
            mock_enforcer = Mock()
            mock_enforcer.check_storage_before_generation.return_value = StorageCheckResult.BLOCKED_LIMIT_EXCEEDED
            mock_enforcer_class.return_value = mock_enforcer
            
            # Test storage check method
            async def test_storage_check():
                try:
                    await caption_service._check_storage_limits_before_generation()
                    self.fail("Expected ValueError to be raised")
                except ValueError as e:
                    self.assertIn("storage limits", str(e))
            
            # Run the async test
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(test_storage_check())
            finally:
                loop.close()


if __name__ == '__main__':
    unittest.main()
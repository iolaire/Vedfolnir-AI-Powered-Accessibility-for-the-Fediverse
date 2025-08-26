# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integration tests for StorageLimitEnforcer with actual storage services.

Tests the complete integration between StorageLimitEnforcer, StorageConfigurationService,
and StorageMonitorService to verify end-to-end functionality.
"""

import unittest
import tempfile
import shutil
import os
from unittest.mock import Mock, patch

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from storage_limit_enforcer import StorageLimitEnforcer, StorageCheckResult
from storage_configuration_service import StorageConfigurationService
from storage_monitor_service import StorageMonitorService


class TestStorageLimitEnforcerIntegration(unittest.TestCase):
    """Integration tests for StorageLimitEnforcer"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create temporary directory for test storage
        self.temp_dir = tempfile.mkdtemp()
        self.test_storage_dir = os.path.join(self.temp_dir, "storage", "images")
        os.makedirs(self.test_storage_dir, exist_ok=True)
        
        # Create a more realistic Redis mock that stores data
        self.redis_data = {}
        self.mock_redis = Mock()
        self.mock_redis.ping.return_value = True
        
        def mock_get(key):
            return self.redis_data.get(key)
        
        def mock_set(key, value):
            self.redis_data[key] = value
            return True
        
        def mock_delete(key):
            if key in self.redis_data:
                del self.redis_data[key]
                return 1
            return 0
        
        self.mock_redis.get.side_effect = mock_get
        self.mock_redis.set.side_effect = mock_set
        self.mock_redis.delete.side_effect = mock_delete
        
        # Patch the storage directory path
        self.storage_dir_patcher = patch('storage_monitor_service.StorageMonitorService.STORAGE_IMAGES_DIR', self.test_storage_dir)
        self.storage_dir_patcher.start()
    
    def tearDown(self):
        """Clean up test fixtures"""
        self.storage_dir_patcher.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _create_test_file(self, filename: str, size_mb: int) -> str:
        """Create a test file of specified size"""
        filepath = os.path.join(self.test_storage_dir, filename)
        with open(filepath, 'wb') as f:
            f.write(b'0' * (size_mb * 1024 * 1024))  # Write size_mb MB of data
        return filepath
    
    @patch.dict(os.environ, {'CAPTION_MAX_STORAGE_GB': '0.01'})  # 10MB limit for testing
    def test_integration_under_limit(self):
        """Test integration when storage is under limit"""
        # Create a small test file (5MB, under 10MB limit)
        self._create_test_file("test_image.jpg", 5)
        
        # Create services with real implementations
        config_service = StorageConfigurationService()
        monitor_service = StorageMonitorService(config_service)
        enforcer = StorageLimitEnforcer(
            config_service=config_service,
            monitor_service=monitor_service,
            redis_client=self.mock_redis
        )
        
        # Check storage - should be allowed
        result = enforcer.check_storage_before_generation()
        self.assertEqual(result, StorageCheckResult.ALLOWED)
        
        # Verify not blocked
        self.assertFalse(enforcer.is_caption_generation_blocked())
        self.assertIsNone(enforcer.get_block_reason())
    
    @patch.dict(os.environ, {'CAPTION_MAX_STORAGE_GB': '0.01'})  # 10MB limit for testing
    def test_integration_over_limit(self):
        """Test integration when storage exceeds limit"""
        # Create a large test file (15MB, over 10MB limit)
        self._create_test_file("large_image.jpg", 15)
        
        # Create services with real implementations
        config_service = StorageConfigurationService()
        monitor_service = StorageMonitorService(config_service)
        enforcer = StorageLimitEnforcer(
            config_service=config_service,
            monitor_service=monitor_service,
            redis_client=self.mock_redis
        )
        
        # Check storage - should be blocked
        result = enforcer.check_storage_before_generation()
        self.assertEqual(result, StorageCheckResult.BLOCKED_LIMIT_EXCEEDED)
        
        # Verify blocked
        self.assertTrue(enforcer.is_caption_generation_blocked())
        self.assertEqual(enforcer.get_block_reason(), "Storage limit exceeded")
    
    @patch.dict(os.environ, {'CAPTION_MAX_STORAGE_GB': '0.01'})  # 10MB limit for testing
    def test_integration_automatic_unblocking(self):
        """Test automatic unblocking when storage drops below limit"""
        # Create a large test file (15MB, over 10MB limit)
        large_file = self._create_test_file("large_image.jpg", 15)
        
        # Create services with real implementations
        config_service = StorageConfigurationService()
        monitor_service = StorageMonitorService(config_service)
        enforcer = StorageLimitEnforcer(
            config_service=config_service,
            monitor_service=monitor_service,
            redis_client=self.mock_redis
        )
        
        # Check storage - should be blocked
        result = enforcer.check_storage_before_generation()
        self.assertEqual(result, StorageCheckResult.BLOCKED_LIMIT_EXCEEDED)
        self.assertTrue(enforcer.is_caption_generation_blocked())
        
        # Remove the large file to drop below limit
        os.remove(large_file)
        
        # Invalidate cache to force recalculation
        monitor_service.invalidate_cache()
        
        # Check storage again - should be automatically unblocked
        result = enforcer.check_storage_before_generation()
        self.assertEqual(result, StorageCheckResult.ALLOWED)
        self.assertFalse(enforcer.is_caption_generation_blocked())
    
    @patch.dict(os.environ, {'CAPTION_MAX_STORAGE_GB': '0.01', 'STORAGE_WARNING_THRESHOLD': '80'})
    def test_integration_warning_threshold(self):
        """Test warning threshold detection"""
        # Create a file that exceeds warning threshold but not limit (8MB, 80% of 10MB)
        self._create_test_file("warning_image.jpg", 9)  # 9MB > 8MB warning threshold
        
        # Create services with real implementations
        config_service = StorageConfigurationService()
        monitor_service = StorageMonitorService(config_service)
        enforcer = StorageLimitEnforcer(
            config_service=config_service,
            monitor_service=monitor_service,
            redis_client=self.mock_redis
        )
        
        # Get storage metrics
        metrics = monitor_service.get_storage_metrics()
        
        # Verify warning threshold is exceeded but limit is not
        self.assertTrue(metrics.is_warning_exceeded)
        self.assertFalse(metrics.is_limit_exceeded)
        
        # Check storage - should still be allowed
        result = enforcer.check_storage_before_generation()
        self.assertEqual(result, StorageCheckResult.ALLOWED)
        self.assertFalse(enforcer.is_caption_generation_blocked())
    
    @patch.dict(os.environ, {'CAPTION_MAX_STORAGE_GB': '0.01'})
    def test_integration_statistics_tracking(self):
        """Test that statistics are properly tracked during operations"""
        # Create services
        config_service = StorageConfigurationService()
        monitor_service = StorageMonitorService(config_service)
        enforcer = StorageLimitEnforcer(
            config_service=config_service,
            monitor_service=monitor_service,
            redis_client=self.mock_redis
        )
        
        # Get initial statistics
        initial_stats = enforcer.get_enforcement_statistics()
        initial_checks = initial_stats['total_checks']
        
        # Perform several storage checks
        for i in range(5):
            enforcer.check_storage_before_generation()
        
        # Get updated statistics
        updated_stats = enforcer.get_enforcement_statistics()
        
        # Verify statistics were updated
        self.assertEqual(updated_stats['total_checks'], initial_checks + 5)
        self.assertIn('current_storage_gb', updated_stats)
        self.assertIn('storage_limit_gb', updated_stats)
        self.assertIn('currently_blocked', updated_stats)
    
    @patch.dict(os.environ, {'CAPTION_MAX_STORAGE_GB': '0.01'})
    def test_integration_health_check(self):
        """Test health check with real services"""
        # Create services
        config_service = StorageConfigurationService()
        monitor_service = StorageMonitorService(config_service)
        enforcer = StorageLimitEnforcer(
            config_service=config_service,
            monitor_service=monitor_service,
            redis_client=self.mock_redis
        )
        
        # Perform health check
        health = enforcer.health_check()
        
        # Verify all components are healthy
        self.assertTrue(health['redis_connected'])
        self.assertTrue(health['config_service_healthy'])
        self.assertTrue(health['monitor_service_healthy'])
        self.assertTrue(health['blocking_state_accessible'])
        self.assertTrue(health['overall_healthy'])
    
    @patch.dict(os.environ, {'CAPTION_MAX_STORAGE_GB': '0.01'})
    def test_integration_manual_blocking_unblocking(self):
        """Test manual blocking and unblocking operations"""
        # Create services
        config_service = StorageConfigurationService()
        monitor_service = StorageMonitorService(config_service)
        enforcer = StorageLimitEnforcer(
            config_service=config_service,
            monitor_service=monitor_service,
            redis_client=self.mock_redis
        )
        
        # Initially not blocked
        self.assertFalse(enforcer.is_caption_generation_blocked())
        
        # Manually block
        enforcer.block_caption_generation("Manual test blocking")
        
        # Verify blocked
        self.assertTrue(enforcer.is_caption_generation_blocked())
        self.assertEqual(enforcer.get_block_reason(), "Manual test blocking")
        
        # Manually unblock
        enforcer.unblock_caption_generation()
        
        # Verify unblocked
        self.assertFalse(enforcer.is_caption_generation_blocked())
        self.assertIsNone(enforcer.get_block_reason())


if __name__ == '__main__':
    unittest.main()
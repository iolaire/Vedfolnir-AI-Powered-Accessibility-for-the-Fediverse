# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integration tests for storage limit management with caption generation workflow.

This test suite verifies the complete blocking/unblocking workflow when storage
limits are reached, including automatic re-enabling when storage drops below limit.
"""

import unittest
import tempfile
import shutil
import os
import json
import redis
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

# Add project root to path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from storage_limit_enforcer import StorageLimitEnforcer, StorageCheckResult, StorageBlockingState
from storage_monitor_service import StorageMonitorService, StorageMetrics
from storage_configuration_service import StorageConfigurationService
from web_caption_generation_service import WebCaptionGenerationService
from database import DatabaseManager
from config import Config
from models import CaptionGenerationSettings


class TestStorageCaptionGenerationIntegration(unittest.TestCase):
    """Integration tests for storage limit management with caption generation"""
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary directory for storage testing
        self.temp_storage_dir = tempfile.mkdtemp()
        self.storage_images_dir = os.path.join(self.temp_storage_dir, "storage", "images")
        os.makedirs(self.storage_images_dir, exist_ok=True)
        
        # Mock Redis client
        self.mock_redis = Mock(spec=redis.Redis)
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
        
        # Mock database manager and web caption generation service
        self.mock_db_manager = Mock(spec=DatabaseManager)
        self.mock_config = Mock(spec=Config)
        
        # Create web caption generation service
        self.caption_service = WebCaptionGenerationService(self.mock_db_manager)
    
    def tearDown(self):
        """Clean up test environment"""
        # Remove temporary storage directory
        if os.path.exists(self.temp_storage_dir):
            shutil.rmtree(self.temp_storage_dir)
    
    def _create_test_files(self, total_size_mb: float) -> None:
        """
        Create test files in storage directory to simulate storage usage.
        
        Args:
            total_size_mb: Total size of files to create in MB
        """
        # Create files to reach the desired total size
        # Use 1000*1000 instead of 1024*1024 for more predictable results
        file_size_bytes = int(total_size_mb * 1000 * 1000)
        
        # Create a single large file
        test_file_path = os.path.join(self.storage_images_dir, "test_image.jpg")
        with open(test_file_path, "wb") as f:
            f.write(b"0" * file_size_bytes)
    
    def test_storage_check_allows_generation_under_limit(self):
        """Test that caption generation is allowed when storage is under limit"""
        # Create files using 500MB (under 1GB limit)
        self._create_test_files(500)
        
        # Check storage before generation
        result = self.enforcer.check_storage_before_generation()
        
        # Should be allowed
        self.assertEqual(result, StorageCheckResult.ALLOWED)
        
        # Verify no blocking state is set
        self.assertFalse(self.enforcer.is_caption_generation_blocked())
    
    def test_storage_check_blocks_generation_over_limit(self):
        """Test that caption generation is blocked when storage exceeds limit"""
        # Create files using 1.5GB (over 1GB limit)
        self._create_test_files(1500)
        
        # Mock Redis to return no existing blocking state initially
        self.mock_redis.get.return_value = None
        
        # Check storage before generation
        result = self.enforcer.check_storage_before_generation()
        
        # Should be blocked
        self.assertEqual(result, StorageCheckResult.BLOCKED_LIMIT_EXCEEDED)
        
        # Verify Redis was called to save blocking state
        self.mock_redis.set.assert_called()
        
        # Verify Redis was called to save blocking state
        self.mock_redis.set.assert_called()
    
    def test_automatic_unblocking_when_storage_drops(self):
        """Test automatic unblocking when storage drops below limit"""
        # First, create files over limit and establish blocking
        self._create_test_files(1500)
        
        # Mock Redis to return no existing blocking state initially
        self.mock_redis.get.return_value = None
        
        # Check storage - should block
        result = self.enforcer.check_storage_before_generation()
        self.assertEqual(result, StorageCheckResult.BLOCKED_LIMIT_EXCEEDED)
        
        # Now simulate storage cleanup - reduce files to under limit
        shutil.rmtree(self.storage_images_dir)
        os.makedirs(self.storage_images_dir, exist_ok=True)
        self._create_test_files(500)  # 500MB - under limit
        
        # Mock Redis to return existing blocking state
        blocking_state = StorageBlockingState(
            is_blocked=True,
            reason="Storage limit exceeded",
            blocked_at=datetime.now(timezone.utc),
            storage_gb=1.5,
            limit_gb=1.0,
            usage_percentage=150.0,
            last_checked=datetime.now(timezone.utc)
        )
        
        # Mock Redis to return blocking state on first call, then None after deletion
        call_count = 0
        def mock_redis_get(key):
            nonlocal call_count
            call_count += 1
            if call_count == 1 and key == self.enforcer.STORAGE_BLOCKING_KEY:
                return json.dumps(blocking_state.to_dict())
            return None
        
        self.mock_redis.get.side_effect = mock_redis_get
        
        # Check storage again - should automatically unblock
        result = self.enforcer.check_storage_before_generation()
        self.assertEqual(result, StorageCheckResult.ALLOWED)
        
        # Verify Redis was called to clear blocking state
        self.mock_redis.delete.assert_called()
    
    def test_web_service_storage_integration_blocks_generation(self):
        """Test that web caption generation service respects storage limits"""
        # Create files over limit to trigger blocking
        self._create_test_files(1500)
        
        # Mock the storage enforcer to return blocked status
        with patch('storage_limit_enforcer.StorageLimitEnforcer') as mock_enforcer_class:
            mock_enforcer = Mock()
            mock_enforcer.check_storage_before_generation.return_value = StorageCheckResult.BLOCKED_LIMIT_EXCEEDED
            mock_enforcer_class.return_value = mock_enforcer
            
            # Mock the async method
            async def test_start_generation():
                try:
                    await self.caption_service._check_storage_limits_before_generation()
                    self.fail("Expected ValueError to be raised")
                except ValueError as e:
                    self.assertIn("storage limits", str(e))
            
            # Run the async test
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(test_start_generation())
            finally:
                loop.close()
    
    def test_web_service_storage_integration_allows_generation(self):
        """Test that web caption generation service allows generation when storage is OK"""
        # Create files under limit
        self._create_test_files(500)
        
        # Mock the async method
        async def test_start_generation():
            # This should not raise an exception
            await self.caption_service._check_storage_limits_before_generation()
        
        # Run the async test
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(test_start_generation())
        finally:
            loop.close()
    
    def test_storage_metrics_calculation_accuracy(self):
        """Test that storage metrics are calculated accurately"""
        # Create files with known sizes
        self._create_test_files(750)  # 750MB
        
        # Get storage metrics
        metrics = self.monitor_service.get_storage_metrics()
        
        # Verify metrics accuracy
        self.assertAlmostEqual(metrics.total_gb, 0.75, places=2)  # 750MB = 0.75GB
        self.assertEqual(metrics.limit_gb, 1.0)
        self.assertAlmostEqual(metrics.usage_percentage, 75.0, places=1)
        self.assertFalse(metrics.is_limit_exceeded)
        self.assertFalse(metrics.is_warning_exceeded)  # 75% < 80% warning threshold
    
    def test_warning_threshold_detection(self):
        """Test that warning threshold is properly detected"""
        # Create files at 85% of limit (850MB)
        self._create_test_files(850)
        
        # Get storage metrics
        metrics = self.monitor_service.get_storage_metrics()
        
        # Verify warning threshold detection
        self.assertAlmostEqual(metrics.usage_percentage, 85.0, places=1)
        self.assertFalse(metrics.is_limit_exceeded)
        self.assertTrue(metrics.is_warning_exceeded)  # 85% > 80% warning threshold
    
    def test_storage_caching_mechanism(self):
        """Test that storage calculation caching works correctly"""
        # Create initial files
        self._create_test_files(500)
        
        # Get metrics first time - should calculate
        metrics1 = self.monitor_service.get_storage_metrics()
        self.assertAlmostEqual(metrics1.total_gb, 0.5, places=2)
        
        # Add more files
        test_file_path = os.path.join(self.storage_images_dir, "test_image2.jpg")
        with open(test_file_path, "wb") as f:
            f.write(b"0" * (250 * 1024 * 1024))  # 250MB
        
        # Get metrics second time - should use cache (still 500MB)
        metrics2 = self.monitor_service.get_storage_metrics()
        self.assertAlmostEqual(metrics2.total_gb, 0.5, places=2)
        
        # Invalidate cache and get metrics - should recalculate (now 750MB)
        self.monitor_service.invalidate_cache()
        metrics3 = self.monitor_service.get_storage_metrics()
        self.assertAlmostEqual(metrics3.total_gb, 0.75, places=2)
    
    def test_error_handling_during_storage_check(self):
        """Test error handling when storage check fails"""
        # Mock monitor service to raise exception
        with patch.object(self.monitor_service, 'get_storage_metrics') as mock_metrics:
            mock_metrics.side_effect = Exception("Storage calculation failed")
            
            # Check storage - should raise StorageCheckError
            with self.assertRaises(Exception):
                self.enforcer.check_storage_before_generation()
    
    def test_redis_connection_failure_handling(self):
        """Test handling of Redis connection failures"""
        # Mock Redis to raise connection error
        self.mock_redis.ping.side_effect = redis.ConnectionError("Redis connection failed")
        
        # Should raise RedisConnectionError during initialization
        with self.assertRaises(Exception):
            StorageLimitEnforcer(
                config_service=self.config_service,
                monitor_service=self.monitor_service,
                redis_client=self.mock_redis
            )
    
    def test_enforcement_statistics_tracking(self):
        """Test that enforcement statistics are properly tracked"""
        # Create files over limit
        self._create_test_files(1500)
        
        # Mock Redis for statistics
        def mock_redis_get(key):
            if key == self.enforcer.STORAGE_BLOCKING_KEY:
                # Return blocking state after first call
                return json.dumps({
                    'is_blocked': True,
                    'reason': 'Storage limit exceeded',
                    'blocked_at': datetime.now(timezone.utc).isoformat(),
                    'storage_gb': 1.5,
                    'limit_gb': 1.0,
                    'usage_percentage': 150.0,
                    'last_checked': datetime.now(timezone.utc).isoformat()
                })
            else:
                return "{}"
        
        self.mock_redis.get.side_effect = mock_redis_get
        
        # Perform multiple storage checks
        for _ in range(3):
            result = self.enforcer.check_storage_before_generation()
            self.assertEqual(result, StorageCheckResult.BLOCKED_LIMIT_EXCEEDED)
        
        # Get statistics
        stats = self.enforcer.get_enforcement_statistics()
        
        # Verify statistics
        self.assertEqual(stats['total_checks'], 3)
        self.assertEqual(stats['blocks_enforced'], 3)
        self.assertEqual(stats['limit_exceeded_count'], 3)
        self.assertTrue(stats['currently_blocked'])
    
    def test_health_check_functionality(self):
        """Test that health check properly validates all components"""
        # Perform health check
        health = self.enforcer.health_check()
        
        # Verify health check results
        self.assertTrue(health['redis_connected'])
        self.assertTrue(health['config_service_healthy'])
        self.assertTrue(health['monitor_service_healthy'])
        self.assertTrue(health['blocking_state_accessible'])
        self.assertTrue(health['overall_healthy'])


if __name__ == '__main__':
    unittest.main()
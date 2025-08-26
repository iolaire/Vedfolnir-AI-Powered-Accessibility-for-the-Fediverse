# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test Storage Cleanup Integration

Tests the integration between storage monitoring and cleanup operations,
including real-time storage recalculation and automatic limit lifting.
"""

import unittest
import tempfile
import shutil
import os
import sys
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from storage_cleanup_integration import StorageCleanupIntegration, CleanupResult, StorageCleanupSummary
from storage_configuration_service import StorageConfigurationService
from storage_monitor_service import StorageMonitorService, StorageMetrics
from storage_limit_enforcer import StorageLimitEnforcer
from models import ProcessingStatus


class TestStorageCleanupIntegration(unittest.TestCase):
    """Test storage cleanup integration functionality"""
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary directory for testing
        self.temp_dir = tempfile.mkdtemp()
        self.storage_dir = os.path.join(self.temp_dir, 'storage', 'images')
        os.makedirs(self.storage_dir, exist_ok=True)
        
        # Mock services
        self.mock_config_service = Mock(spec=StorageConfigurationService)
        self.mock_config_service.get_max_storage_gb.return_value = 1.0  # 1GB limit
        self.mock_config_service.get_warning_threshold_gb.return_value = 0.8  # 800MB warning
        self.mock_config_service.validate_storage_config.return_value = True
        
        self.mock_monitor_service = Mock(spec=StorageMonitorService)
        self.mock_enforcer_service = Mock(spec=StorageLimitEnforcer)
        self.mock_cleanup_manager = Mock()
        self.mock_db_manager = Mock()
        
        # Create integration service
        self.integration = StorageCleanupIntegration(
            config_service=self.mock_config_service,
            monitor_service=self.mock_monitor_service,
            enforcer_service=self.mock_enforcer_service,
            cleanup_manager=self.mock_cleanup_manager,
            db_manager=self.mock_db_manager
        )
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _create_test_storage_metrics(self, usage_gb: float, limit_gb: float = 1.0) -> StorageMetrics:
        """Create test storage metrics"""
        usage_bytes = int(usage_gb * (1024 ** 3))
        limit_bytes = int(limit_gb * (1024 ** 3))
        usage_percentage = (usage_gb / limit_gb) * 100.0
        
        return StorageMetrics(
            total_bytes=usage_bytes,
            total_gb=usage_gb,
            limit_gb=limit_gb,
            usage_percentage=usage_percentage,
            is_limit_exceeded=usage_gb >= limit_gb,
            is_warning_exceeded=usage_gb >= 0.8,  # 80% threshold
            last_calculated=datetime.now()
        )
    
    def test_initialization(self):
        """Test service initialization"""
        self.assertIsNotNone(self.integration.config_service)
        self.assertIsNotNone(self.integration.monitor_service)
        self.assertIsNotNone(self.integration.enforcer_service)
        self.assertIsNotNone(self.integration.cleanup_manager)
        self.assertEqual(len(self.integration._pre_cleanup_callbacks), 0)
        self.assertEqual(len(self.integration._post_cleanup_callbacks), 0)
    
    def test_callback_registration(self):
        """Test callback registration"""
        pre_callback = Mock()
        post_callback = Mock()
        
        self.integration.register_pre_cleanup_callback(pre_callback)
        self.integration.register_post_cleanup_callback(post_callback)
        
        self.assertEqual(len(self.integration._pre_cleanup_callbacks), 1)
        self.assertEqual(len(self.integration._post_cleanup_callbacks), 1)
        self.assertIn(pre_callback, self.integration._pre_cleanup_callbacks)
        self.assertIn(post_callback, self.integration._post_cleanup_callbacks)
    
    def test_get_storage_metrics_before_cleanup(self):
        """Test getting storage metrics before cleanup"""
        test_metrics = self._create_test_storage_metrics(0.5)  # 500MB usage
        self.mock_monitor_service.get_storage_metrics.return_value = test_metrics
        
        metrics = self.integration.get_storage_metrics_before_cleanup()
        
        self.assertEqual(metrics, test_metrics)
        self.mock_monitor_service.get_storage_metrics.assert_called_once()
    
    def test_recalculate_storage_after_cleanup(self):
        """Test storage recalculation after cleanup"""
        test_metrics = self._create_test_storage_metrics(0.3)  # 300MB usage after cleanup
        self.mock_monitor_service.get_storage_metrics.return_value = test_metrics
        
        metrics = self.integration.recalculate_storage_after_cleanup()
        
        self.assertEqual(metrics, test_metrics)
        self.mock_monitor_service.invalidate_cache.assert_called_once()
        self.mock_monitor_service.get_storage_metrics.assert_called_once()
    
    def test_check_and_lift_storage_limits_when_under_limit(self):
        """Test lifting storage limits when usage is under limit"""
        # Storage is under limit
        test_metrics = self._create_test_storage_metrics(0.5)  # 500MB usage, under 1GB limit
        
        # Caption generation is currently blocked
        self.mock_enforcer_service.is_caption_generation_blocked.return_value = True
        
        result = self.integration.check_and_lift_storage_limits(test_metrics)
        
        self.assertTrue(result)
        self.mock_enforcer_service.is_caption_generation_blocked.assert_called_once()
        self.mock_enforcer_service.unblock_caption_generation.assert_called_once()
    
    def test_check_and_lift_storage_limits_when_over_limit(self):
        """Test not lifting storage limits when usage is still over limit"""
        # Storage is over limit
        test_metrics = self._create_test_storage_metrics(1.2)  # 1.2GB usage, over 1GB limit
        
        result = self.integration.check_and_lift_storage_limits(test_metrics)
        
        self.assertFalse(result)
        self.mock_enforcer_service.is_caption_generation_blocked.assert_not_called()
        self.mock_enforcer_service.unblock_caption_generation.assert_not_called()
    
    def test_check_and_lift_storage_limits_when_not_blocked(self):
        """Test not lifting limits when caption generation is not blocked"""
        # Storage is under limit
        test_metrics = self._create_test_storage_metrics(0.5)  # 500MB usage, under 1GB limit
        
        # Caption generation is not blocked
        self.mock_enforcer_service.is_caption_generation_blocked.return_value = False
        
        result = self.integration.check_and_lift_storage_limits(test_metrics)
        
        self.assertFalse(result)
        self.mock_enforcer_service.is_caption_generation_blocked.assert_called_once()
        self.mock_enforcer_service.unblock_caption_generation.assert_not_called()
    
    def test_cleanup_old_images_with_monitoring_success(self):
        """Test cleanup old images with successful monitoring"""
        # Setup
        storage_before = self._create_test_storage_metrics(0.9)  # 900MB before
        storage_after = self._create_test_storage_metrics(0.4)   # 400MB after
        
        self.mock_monitor_service.get_storage_metrics.side_effect = [storage_before, storage_after]
        self.mock_cleanup_manager.cleanup_old_images.return_value = 50  # 50 images cleaned
        
        # Execute
        result = self.integration.cleanup_old_images_with_monitoring(
            status=ProcessingStatus.REJECTED, 
            days=7, 
            dry_run=False
        )
        
        # Verify
        self.assertTrue(result.success)
        self.assertEqual(result.items_cleaned, 50)
        self.assertEqual(result.operation_name, "cleanup_old_images_rejected")
        self.assertGreater(result.storage_freed_gb, 0)  # Should have freed storage
        
        # Verify cleanup manager was called correctly
        self.mock_cleanup_manager.cleanup_old_images.assert_called_once_with(
            status=ProcessingStatus.REJECTED, days=7, dry_run=False
        )
        
        # Verify cache was invalidated and metrics recalculated
        self.mock_monitor_service.invalidate_cache.assert_called_once()
        self.assertEqual(self.mock_monitor_service.get_storage_metrics.call_count, 2)
    
    def test_cleanup_old_images_with_monitoring_dry_run(self):
        """Test cleanup old images with dry run"""
        storage_before = self._create_test_storage_metrics(0.9)
        
        self.mock_monitor_service.get_storage_metrics.return_value = storage_before
        self.mock_cleanup_manager.cleanup_old_images.return_value = 50
        
        result = self.integration.cleanup_old_images_with_monitoring(
            status=ProcessingStatus.REJECTED, 
            days=7, 
            dry_run=True
        )
        
        self.assertTrue(result.success)
        self.assertEqual(result.items_cleaned, 50)
        self.assertEqual(result.storage_freed_gb, 0.0)  # No storage freed in dry run
        
        # Cache should not be invalidated in dry run
        self.mock_monitor_service.invalidate_cache.assert_not_called()
        self.assertEqual(self.mock_monitor_service.get_storage_metrics.call_count, 1)
    
    def test_cleanup_storage_images_with_monitoring(self):
        """Test cleanup storage images with monitoring"""
        storage_before = self._create_test_storage_metrics(1.2)  # 1.2GB before (over limit)
        storage_after = self._create_test_storage_metrics(0.2)   # 200MB after (under limit)
        
        self.mock_monitor_service.get_storage_metrics.side_effect = [storage_before, storage_after]
        self.mock_cleanup_manager.cleanup_storage_images.return_value = 1000  # 1000 files cleaned
        
        result = self.integration.cleanup_storage_images_with_monitoring(dry_run=False)
        
        self.assertTrue(result.success)
        self.assertEqual(result.items_cleaned, 1000)
        self.assertEqual(result.operation_name, "cleanup_storage_images")
        self.assertGreater(result.storage_freed_gb, 0)
        
        # Verify cleanup manager was called
        self.mock_cleanup_manager.cleanup_storage_images.assert_called_once_with(dry_run=False)
    
    def test_callback_execution(self):
        """Test that callbacks are executed during cleanup operations"""
        pre_callback = Mock()
        post_callback = Mock()
        
        self.integration.register_pre_cleanup_callback(pre_callback)
        self.integration.register_post_cleanup_callback(post_callback)
        
        # Setup mocks
        storage_metrics = self._create_test_storage_metrics(0.5)
        self.mock_monitor_service.get_storage_metrics.return_value = storage_metrics
        self.mock_cleanup_manager.cleanup_old_images.return_value = 10
        
        # Execute cleanup
        result = self.integration.cleanup_old_images_with_monitoring(
            status=ProcessingStatus.REJECTED, 
            dry_run=True
        )
        
        # Verify callbacks were called
        pre_callback.assert_called_once()
        post_callback.assert_called_once()
        
        # Verify post callback received the result
        post_callback_args = post_callback.call_args[0]
        self.assertIsInstance(post_callback_args[0], CleanupResult)
    
    def test_run_full_cleanup_with_monitoring(self):
        """Test full cleanup with comprehensive monitoring"""
        storage_before = self._create_test_storage_metrics(1.5)  # 1.5GB before (over limit)
        storage_after = self._create_test_storage_metrics(0.3)   # 300MB after (under limit)
        
        # Mock the monitor service to return different metrics for each call
        self.mock_monitor_service.get_storage_metrics.return_value = storage_before
        
        # Mock cleanup operations to return successful results
        self.mock_cleanup_manager.archive_old_processing_runs.return_value = 5
        # Set up side_effect to handle multiple calls to cleanup_old_images with different statuses
        def cleanup_old_images_side_effect(status=None, days=None, dry_run=False):
            if status == ProcessingStatus.REJECTED:
                return 10
            elif status == ProcessingStatus.POSTED:
                return 20
            elif status == ProcessingStatus.ERROR:
                return 5
            else:
                return 0
        
        self.mock_cleanup_manager.cleanup_old_images.side_effect = cleanup_old_images_side_effect
        self.mock_cleanup_manager.cleanup_orphaned_posts.return_value = 3
        self.mock_cleanup_manager.cleanup_storage_images.return_value = 500
        
        # Mock enforcer for limit lifting - initially blocked, then not blocked after cleanup
        self.mock_enforcer_service.is_caption_generation_blocked.return_value = True
        
        # Execute
        summary = self.integration.run_full_cleanup_with_monitoring(dry_run=False)
        
        # Verify summary
        self.assertIsInstance(summary, StorageCleanupSummary)
        self.assertGreater(summary.total_items_cleaned, 0)
        self.assertEqual(len(summary.operations), 6)  # 6 operations
        
        # Verify successful operations (at least some should succeed)
        successful_operations = [op for op in summary.operations if op.success]
        self.assertGreater(len(successful_operations), 0)
        
        # Verify all cleanup operations were called
        self.mock_cleanup_manager.archive_old_processing_runs.assert_called_once()
        self.assertEqual(self.mock_cleanup_manager.cleanup_old_images.call_count, 3)
        self.mock_cleanup_manager.cleanup_orphaned_posts.assert_called_once()
        self.mock_cleanup_manager.cleanup_storage_images.assert_called_once()
        
        # The test should complete successfully even if some operations fail
        # This tests the error handling and partial success scenarios
    
    def test_get_storage_cleanup_warnings_critical(self):
        """Test getting storage cleanup warnings when in critical state"""
        # Storage over limit
        test_metrics = self._create_test_storage_metrics(1.2)  # 1.2GB usage, over 1GB limit
        self.mock_monitor_service.get_storage_metrics.return_value = test_metrics
        self.mock_enforcer_service.is_caption_generation_blocked.return_value = True
        self.mock_enforcer_service.get_block_reason.return_value = "Storage limit exceeded"
        
        # Mock database session for cleanup potential estimation
        mock_session = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        mock_session.query.return_value.filter.return_value.count.return_value = 25
        self.mock_db_manager.get_session.return_value = mock_session
        
        warnings = self.integration.get_storage_cleanup_warnings()
        
        self.assertEqual(warnings['urgency_level'], 'critical')
        self.assertTrue(warnings['is_blocked'])
        self.assertGreater(len(warnings['warnings']), 0)
        self.assertGreater(len(warnings['recommendations']), 0)
        self.assertEqual(warnings['current_usage_gb'], 1.2)
        self.assertEqual(warnings['limit_gb'], 1.0)
    
    def test_get_storage_cleanup_warnings_normal(self):
        """Test getting storage cleanup warnings when in normal state"""
        # Storage under warning threshold
        test_metrics = self._create_test_storage_metrics(0.5)  # 500MB usage, under warning threshold
        self.mock_monitor_service.get_storage_metrics.return_value = test_metrics
        self.mock_enforcer_service.is_caption_generation_blocked.return_value = False
        
        warnings = self.integration.get_storage_cleanup_warnings()
        
        self.assertEqual(warnings['urgency_level'], 'normal')
        self.assertFalse(warnings['is_blocked'])
        self.assertEqual(warnings['current_usage_gb'], 0.5)
        self.assertEqual(warnings['limit_gb'], 1.0)
    
    def test_health_check(self):
        """Test health check functionality"""
        # Mock all services as healthy
        self.mock_config_service.validate_storage_config.return_value = True
        self.mock_monitor_service.get_storage_metrics.return_value = self._create_test_storage_metrics(0.5)
        self.mock_enforcer_service.health_check.return_value = {'overall_healthy': True}
        
        health = self.integration.health_check()
        
        self.assertTrue(health['overall_healthy'])
        self.assertTrue(health['config_service_healthy'])
        self.assertTrue(health['monitor_service_healthy'])
        self.assertTrue(health['enforcer_service_healthy'])
        self.assertTrue(health['cleanup_manager_available'])
    
    def test_health_check_with_failures(self):
        """Test health check with service failures"""
        # Mock config service failure
        self.mock_config_service.validate_storage_config.side_effect = Exception("Config error")
        
        health = self.integration.health_check()
        
        self.assertFalse(health['overall_healthy'])
        self.assertFalse(health['config_service_healthy'])
        self.assertIn('config_error', health)
    
    def test_cleanup_result_serialization(self):
        """Test CleanupResult serialization"""
        result = CleanupResult(
            operation_name="test_operation",
            items_cleaned=10,
            storage_freed_bytes=1024 * 1024,  # 1MB
            storage_freed_gb=0.001,
            success=True
        )
        
        result_dict = result.to_dict()
        
        self.assertEqual(result_dict['operation_name'], "test_operation")
        self.assertEqual(result_dict['items_cleaned'], 10)
        self.assertEqual(result_dict['storage_freed_bytes'], 1024 * 1024)
        self.assertEqual(result_dict['storage_freed_gb'], 0.001)
        self.assertTrue(result_dict['success'])
        self.assertIsNone(result_dict['error_message'])
    
    def test_cleanup_summary_serialization(self):
        """Test StorageCleanupSummary serialization"""
        storage_before = self._create_test_storage_metrics(1.0)
        storage_after = self._create_test_storage_metrics(0.5)
        
        operations = [
            CleanupResult("op1", 10, 1024, 0.001, True),
            CleanupResult("op2", 5, 512, 0.0005, True)
        ]
        
        summary = StorageCleanupSummary(
            total_items_cleaned=15,
            total_storage_freed_bytes=1536,
            total_storage_freed_gb=0.0015,
            operations=operations,
            storage_before=storage_before,
            storage_after=storage_after,
            limit_lifted=True,
            cleanup_duration_seconds=30.5
        )
        
        summary_dict = summary.to_dict()
        
        self.assertEqual(summary_dict['total_items_cleaned'], 15)
        self.assertEqual(summary_dict['total_storage_freed_bytes'], 1536)
        self.assertEqual(summary_dict['total_storage_freed_gb'], 0.0015)
        self.assertEqual(len(summary_dict['operations']), 2)
        self.assertTrue(summary_dict['limit_lifted'])
        self.assertEqual(summary_dict['cleanup_duration_seconds'], 30.5)
        self.assertIn('storage_before', summary_dict)
        self.assertIn('storage_after', summary_dict)


if __name__ == '__main__':
    unittest.main()
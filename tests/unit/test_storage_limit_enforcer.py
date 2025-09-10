# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for StorageLimitEnforcer class.

Tests enforcement logic, state management, Redis integration, and error handling
as specified in task 3 requirements.
"""

import unittest
import json
import threading
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from typing import Dict, Any

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.services.storage.components.storage_limit_enforcer import (
    StorageLimitEnforcer, 
    StorageCheckResult, 
    StorageBlockingState,
    StorageLimitEnforcerError,
    StorageCheckError,
    RedisConnectionError
)
from app.services.storage.components.storage_configuration_service import StorageConfigurationService
from app.services.storage.components.storage_monitor_service import StorageMonitorService, StorageMetrics


class TestStorageBlockingState(unittest.TestCase):
    """Test StorageBlockingState data class"""
    
    def test_to_dict_conversion(self):
        """Test conversion to dictionary for Redis storage"""
        blocked_at = datetime.now(timezone.utc)
        last_checked = datetime.now(timezone.utc)
        
        state = StorageBlockingState(
            is_blocked=True,
            reason="Test blocking",
            blocked_at=blocked_at,
            storage_gb=12.5,
            limit_gb=10.0,
            usage_percentage=125.0,
            last_checked=last_checked
        )
        
        result = state.to_dict()
        
        self.assertEqual(result['is_blocked'], True)
        self.assertEqual(result['reason'], "Test blocking")
        self.assertEqual(result['blocked_at'], blocked_at.isoformat())
        self.assertEqual(result['storage_gb'], 12.5)
        self.assertEqual(result['limit_gb'], 10.0)
        self.assertEqual(result['usage_percentage'], 125.0)
        self.assertEqual(result['last_checked'], last_checked.isoformat())
    
    def test_from_dict_conversion(self):
        """Test creation from dictionary loaded from Redis"""
        blocked_at = datetime.now(timezone.utc)
        last_checked = datetime.now(timezone.utc)
        
        data = {
            'is_blocked': True,
            'reason': "Test blocking",
            'blocked_at': blocked_at.isoformat(),
            'storage_gb': 12.5,
            'limit_gb': 10.0,
            'usage_percentage': 125.0,
            'last_checked': last_checked.isoformat()
        }
        
        state = StorageBlockingState.from_dict(data)
        
        self.assertEqual(state.is_blocked, True)
        self.assertEqual(state.reason, "Test blocking")
        self.assertEqual(state.blocked_at, blocked_at)
        self.assertEqual(state.storage_gb, 12.5)
        self.assertEqual(state.limit_gb, 10.0)
        self.assertEqual(state.usage_percentage, 125.0)
        self.assertEqual(state.last_checked, last_checked)
    
    def test_none_blocked_at_handling(self):
        """Test handling of None blocked_at value"""
        last_checked = datetime.now(timezone.utc)
        
        state = StorageBlockingState(
            is_blocked=False,
            reason="Not blocked",
            blocked_at=None,
            storage_gb=8.0,
            limit_gb=10.0,
            usage_percentage=80.0,
            last_checked=last_checked
        )
        
        result = state.to_dict()
        self.assertIsNone(result['blocked_at'])
        
        # Test round-trip conversion
        restored_state = StorageBlockingState.from_dict(result)
        self.assertIsNone(restored_state.blocked_at)


class TestStorageLimitEnforcer(unittest.TestCase):
    """Test StorageLimitEnforcer class"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock Redis client
        self.mock_redis = Mock()
        self.mock_redis.ping.return_value = True
        self.mock_redis.get.return_value = None
        self.mock_redis.set.return_value = True
        self.mock_redis.delete.return_value = True
        
        # Mock configuration service
        self.mock_config = Mock(spec=StorageConfigurationService)
        self.mock_config.get_max_storage_gb.return_value = 10.0
        self.mock_config.get_warning_threshold_gb.return_value = 8.0
        self.mock_config.validate_storage_config.return_value = True
        
        # Mock monitor service
        self.mock_monitor = Mock(spec=StorageMonitorService)
        
        # Create test metrics
        self.test_metrics_under_limit = StorageMetrics(
            total_bytes=8 * 1024**3,  # 8GB
            total_gb=8.0,
            limit_gb=10.0,
            usage_percentage=80.0,
            is_limit_exceeded=False,
            is_warning_exceeded=True,
            last_calculated=datetime.now(timezone.utc)
        )
        
        self.test_metrics_over_limit = StorageMetrics(
            total_bytes=12 * 1024**3,  # 12GB
            total_gb=12.0,
            limit_gb=10.0,
            usage_percentage=120.0,
            is_limit_exceeded=True,
            is_warning_exceeded=True,
            last_calculated=datetime.now(timezone.utc)
        )
        
        self.mock_monitor.get_storage_metrics.return_value = self.test_metrics_under_limit
    
    def test_initialization_with_provided_services(self):
        """Test initialization with provided service instances"""
        enforcer = StorageLimitEnforcer(
            config_service=self.mock_config,
            monitor_service=self.mock_monitor,
            redis_client=self.mock_redis
        )
        
        self.assertEqual(enforcer.config_service, self.mock_config)
        self.assertEqual(enforcer.monitor_service, self.mock_monitor)
        self.assertEqual(enforcer.redis_client, self.mock_redis)
        
        # Verify Redis connection was tested
        self.mock_redis.ping.assert_called_once()
    
    def test_initialization_with_default_services(self):
        """Test initialization with default service creation"""
        with patch('storage_limit_enforcer.StorageConfigurationService') as mock_config_class, \
             patch('storage_limit_enforcer.StorageMonitorService') as mock_monitor_class, \
             patch('storage_limit_enforcer.redis.Redis') as mock_redis_class:
            
            mock_config_instance = Mock()
            mock_monitor_instance = Mock()
            mock_redis_instance = Mock()
            mock_redis_instance.ping.return_value = True
            
            mock_config_class.return_value = mock_config_instance
            mock_monitor_class.return_value = mock_monitor_instance
            mock_redis_class.return_value = mock_redis_instance
            
            enforcer = StorageLimitEnforcer()
            
            # Verify services were created
            mock_config_class.assert_called_once()
            mock_monitor_class.assert_called_once_with(mock_config_instance)
            mock_redis_class.assert_called_once()
    
    def test_redis_connection_failure(self):
        """Test handling of Redis connection failure"""
        mock_failing_redis = Mock()
        mock_failing_redis.ping.side_effect = Exception("Connection failed")
        
        with patch('storage_limit_enforcer.redis.Redis', return_value=mock_failing_redis):
            with self.assertRaises(RedisConnectionError):
                StorageLimitEnforcer(
                    config_service=self.mock_config,
                    monitor_service=self.mock_monitor
                )
    
    def test_check_storage_before_generation_allowed(self):
        """Test storage check when generation should be allowed"""
        enforcer = StorageLimitEnforcer(
            config_service=self.mock_config,
            monitor_service=self.mock_monitor,
            redis_client=self.mock_redis
        )
        
        # Mock no existing blocking state
        self.mock_redis.get.return_value = None
        
        result = enforcer.check_storage_before_generation()
        
        self.assertEqual(result, StorageCheckResult.ALLOWED)
        self.mock_monitor.get_storage_metrics.assert_called_once()
    
    def test_check_storage_before_generation_blocked_limit_exceeded(self):
        """Test storage check when limit is exceeded"""
        enforcer = StorageLimitEnforcer(
            config_service=self.mock_config,
            monitor_service=self.mock_monitor,
            redis_client=self.mock_redis
        )
        
        # Reset mock to clear initialization calls
        self.mock_redis.set.reset_mock()
        
        # Set metrics to over limit
        self.mock_monitor.get_storage_metrics.return_value = self.test_metrics_over_limit
        
        result = enforcer.check_storage_before_generation()
        
        self.assertEqual(result, StorageCheckResult.BLOCKED_LIMIT_EXCEEDED)
        
        # Verify blocking state was saved to Redis
        self.mock_redis.set.assert_called()
        
        # Find the call that saved the blocking state
        blocking_state_saved = False
        for call in self.mock_redis.set.call_args_list:
            if call[0][0] == enforcer.STORAGE_BLOCKING_KEY:
                saved_state_json = call[0][1]
                saved_state = json.loads(saved_state_json)
                self.assertTrue(saved_state['is_blocked'])
                self.assertEqual(saved_state['reason'], "Storage limit exceeded")
                blocking_state_saved = True
                break
        
        self.assertTrue(blocking_state_saved, "Blocking state was not saved to Redis")
    
    def test_check_storage_automatic_unblocking(self):
        """Test automatic unblocking when storage drops below limit"""
        enforcer = StorageLimitEnforcer(
            config_service=self.mock_config,
            monitor_service=self.mock_monitor,
            redis_client=self.mock_redis
        )
        
        # Mock existing blocking state
        existing_state = StorageBlockingState(
            is_blocked=True,
            reason="Previous limit exceeded",
            blocked_at=datetime.now(timezone.utc),
            storage_gb=12.0,
            limit_gb=10.0,
            usage_percentage=120.0,
            last_checked=datetime.now(timezone.utc)
        )
        self.mock_redis.get.return_value = json.dumps(existing_state.to_dict())
        
        # Storage is now under limit
        self.mock_monitor.get_storage_metrics.return_value = self.test_metrics_under_limit
        
        result = enforcer.check_storage_before_generation()
        
        self.assertEqual(result, StorageCheckResult.ALLOWED)
        
        # Verify blocking state was cleared from Redis
        self.mock_redis.delete.assert_called_with(enforcer.STORAGE_BLOCKING_KEY)
    
    def test_check_storage_error_handling(self):
        """Test error handling during storage check"""
        enforcer = StorageLimitEnforcer(
            config_service=self.mock_config,
            monitor_service=self.mock_monitor,
            redis_client=self.mock_redis
        )
        
        # Mock monitor service failure
        self.mock_monitor.get_storage_metrics.side_effect = Exception("Monitor failed")
        
        with self.assertRaises(StorageCheckError):
            enforcer.check_storage_before_generation()
    
    def test_block_caption_generation(self):
        """Test manual blocking of caption generation"""
        enforcer = StorageLimitEnforcer(
            config_service=self.mock_config,
            monitor_service=self.mock_monitor,
            redis_client=self.mock_redis
        )
        
        # Reset mock to clear initialization calls
        self.mock_redis.set.reset_mock()
        
        reason = "Manual test blocking"
        enforcer.block_caption_generation(reason)
        
        # Verify blocking state was saved to Redis (should be the first call after reset)
        self.mock_redis.set.assert_called()
        
        # Find the call that saved the blocking state
        blocking_state_saved = False
        for call in self.mock_redis.set.call_args_list:
            if call[0][0] == enforcer.STORAGE_BLOCKING_KEY:
                saved_state_json = call[0][1]
                saved_state = json.loads(saved_state_json)
                self.assertTrue(saved_state['is_blocked'])
                self.assertEqual(saved_state['reason'], reason)
                blocking_state_saved = True
                break
        
        self.assertTrue(blocking_state_saved, "Blocking state was not saved to Redis")
    
    def test_block_caption_generation_redis_failure(self):
        """Test blocking failure when Redis save fails"""
        enforcer = StorageLimitEnforcer(
            config_service=self.mock_config,
            monitor_service=self.mock_monitor,
            redis_client=self.mock_redis
        )
        
        # Mock Redis save failure - Redis.set() returns None on failure
        self.mock_redis.set.return_value = None
        
        with self.assertRaises(StorageLimitEnforcerError):
            enforcer.block_caption_generation("Test blocking")
    
    def test_unblock_caption_generation(self):
        """Test manual unblocking of caption generation"""
        enforcer = StorageLimitEnforcer(
            config_service=self.mock_config,
            monitor_service=self.mock_monitor,
            redis_client=self.mock_redis
        )
        
        enforcer.unblock_caption_generation()
        
        # Verify blocking state was cleared from Redis
        self.mock_redis.delete.assert_called_with(enforcer.STORAGE_BLOCKING_KEY)
    
    def test_unblock_caption_generation_redis_failure(self):
        """Test unblocking failure when Redis delete fails"""
        enforcer = StorageLimitEnforcer(
            config_service=self.mock_config,
            monitor_service=self.mock_monitor,
            redis_client=self.mock_redis
        )
        
        # Mock Redis delete failure - Redis.delete() returns 0 when key doesn't exist
        self.mock_redis.delete.return_value = 0
        
        with self.assertRaises(StorageLimitEnforcerError):
            enforcer.unblock_caption_generation()
    
    def test_is_caption_generation_blocked_true(self):
        """Test checking blocking status when blocked"""
        enforcer = StorageLimitEnforcer(
            config_service=self.mock_config,
            monitor_service=self.mock_monitor,
            redis_client=self.mock_redis
        )
        
        # Mock existing blocking state
        blocking_state = StorageBlockingState(
            is_blocked=True,
            reason="Test blocking",
            blocked_at=datetime.now(timezone.utc),
            storage_gb=12.0,
            limit_gb=10.0,
            usage_percentage=120.0,
            last_checked=datetime.now(timezone.utc)
        )
        self.mock_redis.get.return_value = json.dumps(blocking_state.to_dict())
        
        result = enforcer.is_caption_generation_blocked()
        
        self.assertTrue(result)
    
    def test_is_caption_generation_blocked_false(self):
        """Test checking blocking status when not blocked"""
        enforcer = StorageLimitEnforcer(
            config_service=self.mock_config,
            monitor_service=self.mock_monitor,
            redis_client=self.mock_redis
        )
        
        # Mock no blocking state
        self.mock_redis.get.return_value = None
        
        result = enforcer.is_caption_generation_blocked()
        
        self.assertFalse(result)
    
    def test_is_caption_generation_blocked_error_handling(self):
        """Test error handling when checking blocking status"""
        # Create a new mock that will raise an exception
        error_redis = Mock()
        error_redis.ping.return_value = True
        error_redis.get.side_effect = Exception("Redis error")
        
        enforcer = StorageLimitEnforcer(
            config_service=self.mock_config,
            monitor_service=self.mock_monitor,
            redis_client=error_redis
        )
        
        # Should default to blocked (safe mode) on error
        result = enforcer.is_caption_generation_blocked()
        
        self.assertTrue(result)
    
    def test_get_block_reason_with_blocking(self):
        """Test getting block reason when blocked"""
        enforcer = StorageLimitEnforcer(
            config_service=self.mock_config,
            monitor_service=self.mock_monitor,
            redis_client=self.mock_redis
        )
        
        reason = "Test blocking reason"
        blocking_state = StorageBlockingState(
            is_blocked=True,
            reason=reason,
            blocked_at=datetime.now(timezone.utc),
            storage_gb=12.0,
            limit_gb=10.0,
            usage_percentage=120.0,
            last_checked=datetime.now(timezone.utc)
        )
        self.mock_redis.get.return_value = json.dumps(blocking_state.to_dict())
        
        result = enforcer.get_block_reason()
        
        self.assertEqual(result, reason)
    
    def test_get_block_reason_without_blocking(self):
        """Test getting block reason when not blocked"""
        enforcer = StorageLimitEnforcer(
            config_service=self.mock_config,
            monitor_service=self.mock_monitor,
            redis_client=self.mock_redis
        )
        
        # Mock no blocking state
        self.mock_redis.get.return_value = None
        
        result = enforcer.get_block_reason()
        
        self.assertIsNone(result)
    
    def test_get_block_reason_error_handling(self):
        """Test error handling when getting block reason"""
        # Create a new mock that will raise an exception
        error_redis = Mock()
        error_redis.ping.return_value = True
        error_redis.get.side_effect = Exception("Redis error")
        
        enforcer = StorageLimitEnforcer(
            config_service=self.mock_config,
            monitor_service=self.mock_monitor,
            redis_client=error_redis
        )
        
        result = enforcer.get_block_reason()
        
        self.assertEqual(result, "Error retrieving block reason")
    
    def test_trigger_limit_reached_actions_with_limit_exceeded(self):
        """Test triggering actions when limit is exceeded"""
        enforcer = StorageLimitEnforcer(
            config_service=self.mock_config,
            monitor_service=self.mock_monitor,
            redis_client=self.mock_redis
        )
        
        # Reset mock to clear initialization calls
        self.mock_redis.set.reset_mock()
        
        # Set metrics to over limit
        self.mock_monitor.get_storage_metrics.return_value = self.test_metrics_over_limit
        
        enforcer.trigger_limit_reached_actions()
        
        # Verify blocking state was saved
        self.mock_redis.set.assert_called()
        
        # Find the call that saved the blocking state
        blocking_state_saved = False
        for call in self.mock_redis.set.call_args_list:
            if call[0][0] == enforcer.STORAGE_BLOCKING_KEY:
                saved_state_json = call[0][1]
                saved_state = json.loads(saved_state_json)
                self.assertTrue(saved_state['is_blocked'])
                self.assertEqual(saved_state['reason'], "Automatic enforcement - storage limit reached")
                blocking_state_saved = True
                break
        
        self.assertTrue(blocking_state_saved, "Blocking state was not saved to Redis")
    
    def test_trigger_limit_reached_actions_under_limit(self):
        """Test triggering actions when under limit"""
        enforcer = StorageLimitEnforcer(
            config_service=self.mock_config,
            monitor_service=self.mock_monitor,
            redis_client=self.mock_redis
        )
        
        # Storage is under limit
        self.mock_monitor.get_storage_metrics.return_value = self.test_metrics_under_limit
        
        enforcer.trigger_limit_reached_actions()
        
        # Verify no blocking state was saved
        self.mock_redis.set.assert_not_called()
    
    def test_get_enforcement_statistics(self):
        """Test getting enforcement statistics"""
        enforcer = StorageLimitEnforcer(
            config_service=self.mock_config,
            monitor_service=self.mock_monitor,
            redis_client=self.mock_redis
        )
        
        # Mock no blocking state
        self.mock_redis.get.return_value = None
        
        stats = enforcer.get_enforcement_statistics()
        
        # Verify basic statistics structure
        self.assertIn('total_checks', stats)
        self.assertIn('blocks_enforced', stats)
        self.assertIn('automatic_unblocks', stats)
        self.assertIn('currently_blocked', stats)
        self.assertIn('current_storage_gb', stats)
        self.assertIn('storage_limit_gb', stats)
        
        # Verify current state
        self.assertFalse(stats['currently_blocked'])
        self.assertEqual(stats['current_storage_gb'], 8.0)
        self.assertEqual(stats['storage_limit_gb'], 10.0)
    
    def test_reset_statistics(self):
        """Test resetting enforcement statistics"""
        enforcer = StorageLimitEnforcer(
            config_service=self.mock_config,
            monitor_service=self.mock_monitor,
            redis_client=self.mock_redis
        )
        
        # Modify some statistics
        with enforcer._stats_lock:
            enforcer._stats['total_checks'] = 100
            enforcer._stats['blocks_enforced'] = 5
        
        enforcer.reset_statistics()
        
        # Verify statistics were reset
        stats = enforcer.get_enforcement_statistics()
        self.assertEqual(stats['total_checks'], 0)
        self.assertEqual(stats['blocks_enforced'], 0)
        
        # Verify stats were saved to Redis
        self.mock_redis.set.assert_called()
    
    def test_health_check_all_healthy(self):
        """Test health check when all components are healthy"""
        enforcer = StorageLimitEnforcer(
            config_service=self.mock_config,
            monitor_service=self.mock_monitor,
            redis_client=self.mock_redis
        )
        
        health = enforcer.health_check()
        
        self.assertTrue(health['redis_connected'])
        self.assertTrue(health['config_service_healthy'])
        self.assertTrue(health['monitor_service_healthy'])
        self.assertTrue(health['blocking_state_accessible'])
        self.assertTrue(health['overall_healthy'])
    
    def test_health_check_redis_unhealthy(self):
        """Test health check when Redis is unhealthy"""
        enforcer = StorageLimitEnforcer(
            config_service=self.mock_config,
            monitor_service=self.mock_monitor,
            redis_client=self.mock_redis
        )
        
        # Mock Redis failure
        self.mock_redis.ping.side_effect = Exception("Redis down")
        
        health = enforcer.health_check()
        
        self.assertFalse(health['redis_connected'])
        self.assertFalse(health['overall_healthy'])
        self.assertIn('redis_error', health)
    
    def test_health_check_config_unhealthy(self):
        """Test health check when config service is unhealthy"""
        enforcer = StorageLimitEnforcer(
            config_service=self.mock_config,
            monitor_service=self.mock_monitor,
            redis_client=self.mock_redis
        )
        
        # Mock config validation failure
        self.mock_config.validate_storage_config.side_effect = Exception("Config invalid")
        
        health = enforcer.health_check()
        
        self.assertFalse(health['config_service_healthy'])
        self.assertFalse(health['overall_healthy'])
        self.assertIn('config_error', health)
    
    def test_thread_safety_concurrent_checks(self):
        """Test thread safety with concurrent storage checks"""
        enforcer = StorageLimitEnforcer(
            config_service=self.mock_config,
            monitor_service=self.mock_monitor,
            redis_client=self.mock_redis
        )
        
        results = []
        errors = []
        
        def check_storage():
            try:
                result = enforcer.check_storage_before_generation()
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Run multiple concurrent checks
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=check_storage)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify no errors occurred
        self.assertEqual(len(errors), 0, f"Errors occurred: {errors}")
        
        # Verify all checks completed
        self.assertEqual(len(results), 10)
        
        # All should be allowed (under limit)
        for result in results:
            self.assertEqual(result, StorageCheckResult.ALLOWED)
    
    def test_thread_safety_concurrent_block_unblock(self):
        """Test thread safety with concurrent blocking/unblocking operations"""
        enforcer = StorageLimitEnforcer(
            config_service=self.mock_config,
            monitor_service=self.mock_monitor,
            redis_client=self.mock_redis
        )
        
        errors = []
        
        def block_operation():
            try:
                enforcer.block_caption_generation("Test concurrent blocking")
            except Exception as e:
                errors.append(e)
        
        def unblock_operation():
            try:
                enforcer.unblock_caption_generation()
            except Exception as e:
                errors.append(e)
        
        # Run concurrent block/unblock operations
        threads = []
        for i in range(5):
            block_thread = threading.Thread(target=block_operation)
            unblock_thread = threading.Thread(target=unblock_operation)
            threads.extend([block_thread, unblock_thread])
            block_thread.start()
            unblock_thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify no errors occurred (operations should be thread-safe)
        self.assertEqual(len(errors), 0, f"Errors occurred: {errors}")


if __name__ == '__main__':
    unittest.main()
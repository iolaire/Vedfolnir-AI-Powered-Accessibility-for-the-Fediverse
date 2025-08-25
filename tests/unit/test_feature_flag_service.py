# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for FeatureFlagService

Tests feature flag management, caching, change notifications,
and usage metrics collection.
"""

import unittest
import sys
import os
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone
import threading
import time

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from feature_flag_service import (
    FeatureFlagService, FeatureFlagState, FeatureFlagInfo, FeatureFlagUsageMetrics,
    FeatureFlagError, FeatureFlagNotFoundError
)
from configuration_service import ConfigurationValue, ConfigurationSource
from configuration_event_bus import ConfigurationChangeEvent, EventType


class TestFeatureFlagService(unittest.TestCase):
    """Test cases for FeatureFlagService"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock configuration service
        self.mock_config_service = Mock()
        self.mock_event_bus = Mock()
        
        # Create feature flag service
        self.feature_service = FeatureFlagService(
            config_service=self.mock_config_service,
            event_bus=self.mock_event_bus,
            cache_ttl=60,
            metrics_enabled=True
        )
    
    def test_initialization(self):
        """Test FeatureFlagService initialization"""
        # Test basic initialization
        self.assertIsNotNone(self.feature_service)
        self.assertEqual(self.feature_service.cache_ttl, 60)
        self.assertTrue(self.feature_service.metrics_enabled)
        
        # Test default flags are initialized
        self.assertGreater(len(self.feature_service.DEFAULT_FEATURE_FLAGS), 0)
        
        # Test event bus subscription was set up
        self.mock_event_bus.subscribe.assert_called_once()
    
    def test_is_enabled_with_cached_value(self):
        """Test is_enabled with cached feature flag"""
        # Setup cached flag
        flag_info = FeatureFlagInfo(
            key='enable_batch_processing',
            enabled=True,
            state=FeatureFlagState.ENABLED,
            last_updated=datetime.now(timezone.utc),
            source='database',
            usage_count=0
        )
        
        with self.feature_service._cache_lock:
            self.feature_service._flag_cache['enable_batch_processing'] = flag_info
        
        # Test enabled flag
        result = self.feature_service.is_enabled('enable_batch_processing')
        self.assertTrue(result)
        
        # Verify usage count was updated
        self.assertEqual(flag_info.usage_count, 1)
        self.assertIsNotNone(flag_info.last_accessed)
    
    def test_is_enabled_with_config_service(self):
        """Test is_enabled fetching from configuration service"""
        # Clear the cache first to ensure fresh lookup
        with self.feature_service._cache_lock:
            self.feature_service._flag_cache.clear()
        
        # Mock configuration service response
        config_value = ConfigurationValue(
            key='enable_advanced_monitoring',
            value=True,
            data_type='boolean',
            source=ConfigurationSource.DATABASE,
            requires_restart=False,
            last_updated=datetime.now(timezone.utc),
            cached_at=datetime.now(timezone.utc),
            ttl=300
        )
        
        self.mock_config_service.get_config_with_metadata.return_value = config_value
        
        # Test feature flag
        result = self.feature_service.is_enabled('enable_advanced_monitoring')
        self.assertTrue(result)
        
        # Verify configuration service was called
        self.mock_config_service.get_config_with_metadata.assert_called_with('enable_advanced_monitoring')
        
        # Verify flag was cached
        with self.feature_service._cache_lock:
            cached_flag = self.feature_service._flag_cache.get('enable_advanced_monitoring')
            self.assertIsNotNone(cached_flag)
            self.assertTrue(cached_flag.enabled)
    
    def test_is_enabled_with_default_value(self):
        """Test is_enabled falling back to default value"""
        # Mock configuration service to return None
        self.mock_config_service.get_config_with_metadata.return_value = None
        
        # Test known default flag
        result = self.feature_service.is_enabled('enable_batch_processing')
        expected = self.feature_service.DEFAULT_FEATURE_FLAGS['enable_batch_processing']['default']
        self.assertEqual(result, expected)
    
    def test_is_enabled_unknown_flag(self):
        """Test is_enabled with unknown feature flag"""
        # Mock configuration service to return None
        self.mock_config_service.get_config_with_metadata.return_value = None
        
        # Test unknown flag
        result = self.feature_service.is_enabled('unknown_feature')
        self.assertFalse(result)  # Should default to False
    
    def test_is_enabled_with_error(self):
        """Test is_enabled handling errors gracefully"""
        # Mock configuration service to raise exception
        self.mock_config_service.get_config_with_metadata.side_effect = Exception("Database error")
        
        # Test known flag - should return default
        result = self.feature_service.is_enabled('enable_batch_processing')
        expected = self.feature_service.DEFAULT_FEATURE_FLAGS['enable_batch_processing']['default']
        self.assertEqual(result, expected)
        
        # Test unknown flag - should return False
        result = self.feature_service.is_enabled('unknown_feature')
        self.assertFalse(result)
    
    def test_get_all_flags(self):
        """Test get_all_flags method"""
        # Clear cache first
        with self.feature_service._cache_lock:
            self.feature_service._flag_cache.clear()
        
        # Mock configuration service to return specific values for each call
        def mock_get_config(key):
            if key == 'enable_batch_processing':
                return ConfigurationValue(
                    key='enable_batch_processing',
                    value=True,
                    data_type='boolean',
                    source=ConfigurationSource.DATABASE,
                    requires_restart=False,
                    last_updated=datetime.now(timezone.utc),
                    cached_at=datetime.now(timezone.utc),
                    ttl=300
                )
            elif key == 'enable_auto_retry':
                return ConfigurationValue(
                    key='enable_auto_retry',
                    value=False,
                    data_type='boolean',
                    source=ConfigurationSource.ENVIRONMENT,
                    requires_restart=False,
                    last_updated=datetime.now(timezone.utc),
                    cached_at=datetime.now(timezone.utc),
                    ttl=300
                )
            else:
                return None  # enable_advanced_monitoring and others not found
        
        self.mock_config_service.get_config_with_metadata.side_effect = mock_get_config
        
        # Get all flags
        flags = self.feature_service.get_all_flags()
        
        # Verify results
        self.assertIsInstance(flags, dict)
        self.assertIn('enable_batch_processing', flags)
        self.assertIn('enable_advanced_monitoring', flags)
        self.assertIn('enable_auto_retry', flags)
        
        # Verify values
        self.assertTrue(flags['enable_batch_processing'])
        self.assertFalse(flags['enable_advanced_monitoring'])  # Default value
        self.assertFalse(flags['enable_auto_retry'])
    
    def test_get_flag_info(self):
        """Test get_flag_info method"""
        # Clear cache first
        with self.feature_service._cache_lock:
            self.feature_service._flag_cache.clear()
        
        # Mock configuration service response
        config_value = ConfigurationValue(
            key='enable_batch_processing',
            value=True,
            data_type='boolean',
            source=ConfigurationSource.DATABASE,
            requires_restart=False,
            last_updated=datetime.now(timezone.utc),
            cached_at=datetime.now(timezone.utc),
            ttl=300
        )
        
        self.mock_config_service.get_config_with_metadata.return_value = config_value
        
        # Get flag info
        flag_info = self.feature_service.get_flag_info('enable_batch_processing')
        
        # Verify result
        self.assertIsNotNone(flag_info)
        self.assertEqual(flag_info.key, 'enable_batch_processing')
        self.assertTrue(flag_info.enabled)
        self.assertEqual(flag_info.state, FeatureFlagState.ENABLED)
        self.assertEqual(flag_info.source, 'database')
        self.assertIsNotNone(flag_info.description)
    
    def test_get_flag_info_not_found(self):
        """Test get_flag_info with non-existent flag"""
        # Mock configuration service to return None
        self.mock_config_service.get_config_with_metadata.return_value = None
        
        # Test unknown flag
        flag_info = self.feature_service.get_flag_info('unknown_feature')
        self.assertIsNone(flag_info)
    
    def test_refresh_flags(self):
        """Test refresh_flags method"""
        # Add some cached flags
        with self.feature_service._cache_lock:
            self.feature_service._flag_cache['test_flag'] = FeatureFlagInfo(
                key='test_flag',
                enabled=True,
                state=FeatureFlagState.ENABLED,
                last_updated=datetime.now(timezone.utc),
                source='cache'
            )
        
        # Refresh flags
        result = self.feature_service.refresh_flags()
        
        # Verify success
        self.assertTrue(result)
        
        # Verify cache was cleared and config service was refreshed
        self.mock_config_service.refresh_config.assert_called_once()
        
        # Verify default flags were re-initialized
        with self.feature_service._cache_lock:
            self.assertIn('enable_batch_processing', self.feature_service._flag_cache)
    
    def test_subscribe_to_flag_changes(self):
        """Test subscribe_to_flag_changes method"""
        # Create callback
        callback_called = []
        
        def test_callback(feature, old_value, new_value):
            callback_called.append((feature, old_value, new_value))
        
        # Subscribe to changes
        subscription_id = self.feature_service.subscribe_to_flag_changes('enable_batch_processing', test_callback)
        
        # Verify subscription was created
        self.assertIsNotNone(subscription_id)
        
        with self.feature_service._subscribers_lock:
            self.assertIn('enable_batch_processing', self.feature_service._change_subscribers)
            self.assertIn(subscription_id, self.feature_service._change_subscribers['enable_batch_processing'])
    
    def test_unsubscribe_from_flag_changes(self):
        """Test unsubscribe_from_flag_changes method"""
        # Create subscription
        def test_callback(feature, old_value, new_value):
            pass
        
        subscription_id = self.feature_service.subscribe_to_flag_changes('enable_batch_processing', test_callback)
        
        # Unsubscribe
        result = self.feature_service.unsubscribe_from_flag_changes(subscription_id)
        
        # Verify unsubscription
        self.assertTrue(result)
        
        with self.feature_service._subscribers_lock:
            subscribers = self.feature_service._change_subscribers.get('enable_batch_processing', {})
            self.assertNotIn(subscription_id, subscribers)
    
    def test_unsubscribe_nonexistent_subscription(self):
        """Test unsubscribing from non-existent subscription"""
        result = self.feature_service.unsubscribe_from_flag_changes('nonexistent-id')
        self.assertFalse(result)
    
    def test_usage_metrics_collection(self):
        """Test usage metrics collection"""
        # Enable metrics
        self.feature_service.metrics_enabled = True
        
        # Mock configuration service
        self.mock_config_service.get_config_with_metadata.return_value = ConfigurationValue(
            key='enable_batch_processing',
            value=True,
            data_type='boolean',
            source=ConfigurationSource.DATABASE,
            requires_restart=False,
            last_updated=datetime.now(timezone.utc),
            cached_at=datetime.now(timezone.utc),
            ttl=300
        )
        
        # Make several flag checks
        self.feature_service.is_enabled('enable_batch_processing')  # enabled
        self.feature_service.is_enabled('enable_advanced_monitoring')  # disabled (default)
        self.feature_service.is_enabled('enable_batch_processing')  # enabled (cached)
        
        # Get metrics
        metrics = self.feature_service.get_usage_metrics()
        
        # Verify metrics
        self.assertGreater(metrics.total_checks, 0)
        self.assertGreater(metrics.enabled_checks, 0)
        self.assertGreater(metrics.disabled_checks, 0)
        self.assertGreater(metrics.cache_hits, 0)
        self.assertIsNotNone(metrics.last_reset)
    
    def test_reset_usage_metrics(self):
        """Test reset_usage_metrics method"""
        # Generate some metrics
        self.feature_service.is_enabled('enable_batch_processing')
        
        # Get initial metrics
        initial_metrics = self.feature_service.get_usage_metrics()
        self.assertGreater(initial_metrics.total_checks, 0)
        
        # Reset metrics
        self.feature_service.reset_usage_metrics()
        
        # Get new metrics
        new_metrics = self.feature_service.get_usage_metrics()
        self.assertEqual(new_metrics.total_checks, 0)
        self.assertEqual(new_metrics.enabled_checks, 0)
        self.assertEqual(new_metrics.disabled_checks, 0)
    
    def test_get_feature_list(self):
        """Test get_feature_list method"""
        # Mock configuration service
        self.mock_config_service.get_config_with_metadata.side_effect = [
            ConfigurationValue(
                key='enable_batch_processing',
                value=True,
                data_type='boolean',
                source=ConfigurationSource.DATABASE,
                requires_restart=False,
                last_updated=datetime.now(timezone.utc),
                cached_at=datetime.now(timezone.utc),
                ttl=300
            ),
            None  # Other flags return None
        ] * 10  # Repeat for multiple calls
        
        # Get feature list
        features = self.feature_service.get_feature_list()
        
        # Verify results
        self.assertIsInstance(features, list)
        self.assertGreater(len(features), 0)
        
        # Check feature structure
        for feature in features:
            self.assertIn('key', feature)
            self.assertIn('enabled', feature)
            self.assertIn('description', feature)
            self.assertIn('default_value', feature)
            self.assertIn('source', feature)
    
    def test_convert_to_boolean(self):
        """Test _convert_to_boolean method"""
        # Test boolean values
        self.assertTrue(self.feature_service._convert_to_boolean(True))
        self.assertFalse(self.feature_service._convert_to_boolean(False))
        
        # Test string values
        self.assertTrue(self.feature_service._convert_to_boolean('true'))
        self.assertTrue(self.feature_service._convert_to_boolean('True'))
        self.assertTrue(self.feature_service._convert_to_boolean('1'))
        self.assertTrue(self.feature_service._convert_to_boolean('yes'))
        self.assertTrue(self.feature_service._convert_to_boolean('on'))
        self.assertTrue(self.feature_service._convert_to_boolean('enabled'))
        
        self.assertFalse(self.feature_service._convert_to_boolean('false'))
        self.assertFalse(self.feature_service._convert_to_boolean('0'))
        self.assertFalse(self.feature_service._convert_to_boolean('no'))
        self.assertFalse(self.feature_service._convert_to_boolean('off'))
        
        # Test numeric values
        self.assertTrue(self.feature_service._convert_to_boolean(1))
        self.assertTrue(self.feature_service._convert_to_boolean(1.5))
        self.assertFalse(self.feature_service._convert_to_boolean(0))
        self.assertFalse(self.feature_service._convert_to_boolean(0.0))
        
        # Test other values
        self.assertTrue(self.feature_service._convert_to_boolean([1, 2, 3]))
        self.assertFalse(self.feature_service._convert_to_boolean([]))
        self.assertFalse(self.feature_service._convert_to_boolean(None))
    
    def test_is_feature_flag(self):
        """Test _is_feature_flag method"""
        # Test known feature flags
        self.assertTrue(self.feature_service._is_feature_flag('enable_batch_processing'))
        self.assertTrue(self.feature_service._is_feature_flag('enable_advanced_monitoring'))
        
        # Test feature flag prefixes
        self.assertTrue(self.feature_service._is_feature_flag('enable_new_feature'))
        self.assertTrue(self.feature_service._is_feature_flag('disable_old_feature'))
        self.assertTrue(self.feature_service._is_feature_flag('feature_experimental'))
        self.assertTrue(self.feature_service._is_feature_flag('flag_debug'))
        
        # Test non-feature flags
        self.assertFalse(self.feature_service._is_feature_flag('max_concurrent_jobs'))
        self.assertFalse(self.feature_service._is_feature_flag('database_url'))
        self.assertFalse(self.feature_service._is_feature_flag('session_timeout'))
    
    def test_handle_configuration_change(self):
        """Test _handle_configuration_change method"""
        # Setup subscription
        callback_called = []
        
        def test_callback(feature, old_value, new_value):
            callback_called.append((feature, old_value, new_value))
        
        self.feature_service.subscribe_to_flag_changes('enable_batch_processing', test_callback)
        
        # Setup cached flag
        flag_info = FeatureFlagInfo(
            key='enable_batch_processing',
            enabled=True,
            state=FeatureFlagState.ENABLED,
            last_updated=datetime.now(timezone.utc),
            source='database'
        )
        
        with self.feature_service._cache_lock:
            self.feature_service._flag_cache['enable_batch_processing'] = flag_info
        
        # Create configuration change event
        event = ConfigurationChangeEvent(
            event_type=EventType.CONFIGURATION_CHANGED,
            key='enable_batch_processing',
            old_value=True,
            new_value=False,
            source='admin',
            timestamp=datetime.now(timezone.utc)
        )
        
        # Handle the change
        self.feature_service._handle_configuration_change(event)
        
        # Verify callback was called
        self.assertEqual(len(callback_called), 1)
        self.assertEqual(callback_called[0], ('enable_batch_processing', True, False))
        
        # Verify cache was cleared
        with self.feature_service._cache_lock:
            self.assertNotIn('enable_batch_processing', self.feature_service._flag_cache)
    
    def test_handle_non_feature_flag_change(self):
        """Test handling configuration change for non-feature flag"""
        # Setup subscription
        callback_called = []
        
        def test_callback(feature, old_value, new_value):
            callback_called.append((feature, old_value, new_value))
        
        self.feature_service.subscribe_to_flag_changes('max_concurrent_jobs', test_callback)
        
        # Create configuration change event for non-feature flag
        event = ConfigurationChangeEvent(
            event_type=EventType.CONFIGURATION_CHANGED,
            key='max_concurrent_jobs',
            old_value=5,
            new_value=10,
            source='admin',
            timestamp=datetime.now(timezone.utc)
        )
        
        # Handle the change
        self.feature_service._handle_configuration_change(event)
        
        # Verify callback was NOT called (not a feature flag)
        self.assertEqual(len(callback_called), 0)
    
    def test_cache_expiration(self):
        """Test cache entry expiration"""
        # Create service with short TTL
        short_ttl_service = FeatureFlagService(
            config_service=self.mock_config_service,
            event_bus=self.mock_event_bus,
            cache_ttl=1,  # 1 second TTL
            metrics_enabled=True
        )
        
        # Clear cache to ensure clean state
        with short_ttl_service._cache_lock:
            short_ttl_service._flag_cache.clear()
        
        # Reset mock call count
        self.mock_config_service.reset_mock()
        
        # Mock configuration service
        self.mock_config_service.get_config_with_metadata.return_value = ConfigurationValue(
            key='enable_batch_processing',
            value=True,
            data_type='boolean',
            source=ConfigurationSource.DATABASE,
            requires_restart=False,
            last_updated=datetime.now(timezone.utc),
            cached_at=datetime.now(timezone.utc),
            ttl=300
        )
        
        # First call should cache the value
        result1 = short_ttl_service.is_enabled('enable_batch_processing')
        self.assertTrue(result1)
        
        # Verify it's cached
        with short_ttl_service._cache_lock:
            self.assertIn('enable_batch_processing', short_ttl_service._flag_cache)
        
        # Wait for cache to expire
        time.sleep(1.1)
        
        # Second call should fetch from config service again
        result2 = short_ttl_service.is_enabled('enable_batch_processing')
        self.assertTrue(result2)
        
        # Verify config service was called twice
        self.assertEqual(self.mock_config_service.get_config_with_metadata.call_count, 2)
    
    def test_thread_safety(self):
        """Test thread safety of feature flag service"""
        # Mock configuration service
        self.mock_config_service.get_config_with_metadata.return_value = ConfigurationValue(
            key='enable_batch_processing',
            value=True,
            data_type='boolean',
            source=ConfigurationSource.DATABASE,
            requires_restart=False,
            last_updated=datetime.now(timezone.utc),
            cached_at=datetime.now(timezone.utc),
            ttl=300
        )
        
        results = []
        errors = []
        
        def worker():
            try:
                for _ in range(100):
                    result = self.feature_service.is_enabled('enable_batch_processing')
                    results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify no errors occurred
        self.assertEqual(len(errors), 0)
        
        # Verify all results are consistent
        self.assertEqual(len(results), 1000)  # 10 threads * 100 calls each
        self.assertTrue(all(result == True for result in results))


if __name__ == '__main__':
    unittest.main()
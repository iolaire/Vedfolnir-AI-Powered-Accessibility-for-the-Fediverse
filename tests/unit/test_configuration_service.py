# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for ConfigurationService
"""

import unittest
import os
import sys
import json
import time
import threading
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from configuration_service import (
    ConfigurationService, ConfigurationValue, ConfigurationSource,
    ConfigurationError, ConfigurationNotFoundError, ConfigurationValidationError
)
from system_configuration_manager import ConfigurationSchema, ConfigurationDataType, ConfigurationCategory


class TestConfigurationService(unittest.TestCase):
    """Test cases for ConfigurationService"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_db_manager = Mock()
        self.mock_session = Mock()
        
        # Mock the context manager properly
        mock_context_manager = Mock()
        mock_context_manager.__enter__ = Mock(return_value=self.mock_session)
        mock_context_manager.__exit__ = Mock(return_value=None)
        self.mock_db_manager.get_session.return_value = mock_context_manager
        
        # Create service with small cache for testing
        self.service = ConfigurationService(
            db_manager=self.mock_db_manager,
            cache_size=10,
            default_ttl=1,  # Short TTL for testing
            environment_prefix="TEST_CONFIG_"
        )
        
        # Mock schema
        self.mock_schema = ConfigurationSchema(
            key="test_key",
            data_type=ConfigurationDataType.STRING,
            category=ConfigurationCategory.SYSTEM,
            description="Test configuration",
            default_value="default_value",
            requires_restart=False
        )
    
    def tearDown(self):
        """Clean up after tests"""
        # Clear environment variables
        for key in list(os.environ.keys()):
            if key.startswith("TEST_CONFIG_"):
                del os.environ[key]
    
    def test_get_config_from_cache(self):
        """Test getting configuration from cache"""
        # Pre-populate cache
        config_value = ConfigurationValue(
            key="test_key",
            value="cached_value",
            data_type="string",
            source=ConfigurationSource.DATABASE,
            requires_restart=False,
            last_updated=datetime.now(timezone.utc),
            cached_at=datetime.now(timezone.utc),
            ttl=300
        )
        
        with self.service._cache_lock:
            self.service._cache["test_key"] = config_value
        
        # Get configuration
        result = self.service.get_config("test_key")
        
        # Verify cache hit
        self.assertEqual(result, "cached_value")
        self.assertEqual(self.service._stats['cache_hits'], 1)
        self.assertEqual(self.service._stats['cache_misses'], 0)
    
    def test_get_config_from_environment(self):
        """Test getting configuration from environment variable"""
        # Set environment variable
        os.environ["TEST_CONFIG_TEST_KEY"] = "env_value"
        
        # Mock schema
        self.service.system_config_manager.get_configuration_schema = Mock(return_value=self.mock_schema)
        
        # Get configuration
        result = self.service.get_config("test_key")
        
        # Verify environment override
        self.assertEqual(result, "env_value")
        self.assertEqual(self.service._stats['environment_overrides'], 1)
        self.assertEqual(self.service._stats['cache_misses'], 1)
    
    def test_get_config_from_database(self):
        """Test getting configuration from database"""
        # Mock database configuration
        mock_db_config = Mock()
        mock_db_config.get_typed_value.return_value = "db_value"
        mock_db_config.data_type = "string"
        mock_db_config.updated_at = datetime.now(timezone.utc)
        
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = mock_db_config
        self.service.system_config_manager.get_configuration_schema = Mock(return_value=self.mock_schema)
        
        # Get configuration
        result = self.service.get_config("test_key")
        
        # Verify database read
        self.assertEqual(result, "db_value")
        self.assertEqual(self.service._stats['database_reads'], 1)
        self.assertEqual(self.service._stats['cache_misses'], 1)
    
    def test_get_config_from_schema_default(self):
        """Test getting configuration from schema default"""
        # Mock no database result
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = None
        self.service.system_config_manager.get_configuration_schema = Mock(return_value=self.mock_schema)
        
        # Get configuration
        result = self.service.get_config("test_key")
        
        # Verify default fallback
        self.assertEqual(result, "default_value")
        self.assertEqual(self.service._stats['default_fallbacks'], 1)
        self.assertEqual(self.service._stats['cache_misses'], 1)
    
    def test_get_config_not_found(self):
        """Test getting non-existent configuration"""
        # Mock no database result and no schema
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = None
        self.service.system_config_manager.get_configuration_schema = Mock(return_value=None)
        
        # Get configuration with default
        result = self.service.get_config("nonexistent_key", "fallback_default")
        
        # Verify fallback default
        self.assertEqual(result, "fallback_default")
    
    def test_get_config_with_metadata(self):
        """Test getting configuration with full metadata"""
        # Mock database configuration
        mock_db_config = Mock()
        mock_db_config.get_typed_value.return_value = "db_value"
        mock_db_config.data_type = "string"
        mock_db_config.updated_at = datetime.now(timezone.utc)
        
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = mock_db_config
        self.service.system_config_manager.get_configuration_schema = Mock(return_value=self.mock_schema)
        
        # Get configuration with metadata
        result = self.service.get_config_with_metadata("test_key")
        
        # Verify metadata
        self.assertIsInstance(result, ConfigurationValue)
        self.assertEqual(result.key, "test_key")
        self.assertEqual(result.value, "db_value")
        self.assertEqual(result.data_type, "string")
        self.assertEqual(result.source, ConfigurationSource.DATABASE)
        self.assertFalse(result.requires_restart)
    
    def test_type_conversion(self):
        """Test configuration value type conversion"""
        # Test integer conversion
        os.environ["TEST_CONFIG_INT_KEY"] = "42"
        
        int_schema = ConfigurationSchema(
            key="int_key",
            data_type=ConfigurationDataType.INTEGER,
            category=ConfigurationCategory.SYSTEM,
            description="Integer test",
            default_value=0
        )
        
        self.service.system_config_manager.get_configuration_schema = Mock(return_value=int_schema)
        
        result = self.service.get_config("int_key")
        self.assertEqual(result, 42)
        self.assertIsInstance(result, int)
        
        # Test boolean conversion
        os.environ["TEST_CONFIG_BOOL_KEY"] = "true"
        
        bool_schema = ConfigurationSchema(
            key="bool_key",
            data_type=ConfigurationDataType.BOOLEAN,
            category=ConfigurationCategory.SYSTEM,
            description="Boolean test",
            default_value=False
        )
        
        self.service.system_config_manager.get_configuration_schema = Mock(return_value=bool_schema)
        
        result = self.service.get_config("bool_key")
        self.assertEqual(result, True)
        self.assertIsInstance(result, bool)
        
        # Test JSON conversion
        os.environ["TEST_CONFIG_JSON_KEY"] = '{"key": "value"}'
        
        json_schema = ConfigurationSchema(
            key="json_key",
            data_type=ConfigurationDataType.JSON,
            category=ConfigurationCategory.SYSTEM,
            description="JSON test",
            default_value={}
        )
        
        self.service.system_config_manager.get_configuration_schema = Mock(return_value=json_schema)
        
        result = self.service.get_config("json_key")
        self.assertEqual(result, {"key": "value"})
        self.assertIsInstance(result, dict)
    
    def test_cache_ttl_expiration(self):
        """Test cache TTL expiration"""
        # Mock database configuration
        mock_db_config = Mock()
        mock_db_config.get_typed_value.return_value = "db_value"
        mock_db_config.data_type = "string"
        mock_db_config.updated_at = datetime.now(timezone.utc)
        
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = mock_db_config
        self.service.system_config_manager.get_configuration_schema = Mock(return_value=self.mock_schema)
        
        # First access - should cache
        result1 = self.service.get_config("test_key")
        self.assertEqual(result1, "db_value")
        self.assertEqual(self.service._stats['cache_misses'], 1)
        
        # Second access immediately - should hit cache
        result2 = self.service.get_config("test_key")
        self.assertEqual(result2, "db_value")
        self.assertEqual(self.service._stats['cache_hits'], 1)
        
        # Wait for TTL expiration
        time.sleep(1.1)
        
        # Third access - should miss cache due to TTL
        result3 = self.service.get_config("test_key")
        self.assertEqual(result3, "db_value")
        self.assertEqual(self.service._stats['cache_misses'], 2)
    
    def test_refresh_config(self):
        """Test configuration cache refresh"""
        # Pre-populate cache
        config_value = ConfigurationValue(
            key="test_key",
            value="cached_value",
            data_type="string",
            source=ConfigurationSource.DATABASE,
            requires_restart=False,
            last_updated=datetime.now(timezone.utc),
            cached_at=datetime.now(timezone.utc),
            ttl=300
        )
        
        with self.service._cache_lock:
            self.service._cache["test_key"] = config_value
        
        # Verify cache has value
        self.assertIn("test_key", self.service._cache)
        
        # Refresh specific key
        result = self.service.refresh_config("test_key")
        self.assertTrue(result)
        self.assertNotIn("test_key", self.service._cache)
        
        # Add value back and refresh all
        with self.service._cache_lock:
            self.service._cache["test_key"] = config_value
        
        result = self.service.refresh_config()
        self.assertTrue(result)
        self.assertEqual(len(self.service._cache), 0)
    
    def test_restart_requirement_tracking(self):
        """Test restart requirement tracking"""
        # Mock schema requiring restart
        restart_schema = ConfigurationSchema(
            key="restart_key",
            data_type=ConfigurationDataType.STRING,
            category=ConfigurationCategory.SYSTEM,
            description="Restart required config",
            default_value="default",
            requires_restart=True
        )
        
        self.service.system_config_manager.get_configuration_schema = Mock(return_value=restart_schema)
        
        # Initially no restart required
        self.assertFalse(self.service.is_restart_required())
        self.assertEqual(len(self.service.get_pending_restart_configs()), 0)
        
        # Notify change for restart-required config
        self.service.notify_change("restart_key", "old_value", "new_value")
        
        # Should now require restart
        self.assertTrue(self.service.is_restart_required())
        self.assertIn("restart_key", self.service.get_pending_restart_configs())
    
    def test_change_subscription(self):
        """Test configuration change subscription"""
        callback_called = []
        
        def test_callback(key, old_value, new_value):
            callback_called.append((key, old_value, new_value))
        
        # Subscribe to changes
        subscription_id = self.service.subscribe_to_changes("test_key", test_callback)
        self.assertIsInstance(subscription_id, str)
        
        # Notify change
        self.service.notify_change("test_key", "old_value", "new_value")
        
        # Verify callback was called
        self.assertEqual(len(callback_called), 1)
        self.assertEqual(callback_called[0], ("test_key", "old_value", "new_value"))
        
        # Unsubscribe
        result = self.service.unsubscribe(subscription_id)
        self.assertTrue(result)
        
        # Notify change again
        self.service.notify_change("test_key", "old_value2", "new_value2")
        
        # Callback should not be called again
        self.assertEqual(len(callback_called), 1)
    
    def test_cache_invalidation_on_change(self):
        """Test cache invalidation when configuration changes"""
        # Pre-populate cache
        config_value = ConfigurationValue(
            key="test_key",
            value="cached_value",
            data_type="string",
            source=ConfigurationSource.DATABASE,
            requires_restart=False,
            last_updated=datetime.now(timezone.utc),
            cached_at=datetime.now(timezone.utc),
            ttl=300
        )
        
        with self.service._cache_lock:
            self.service._cache["test_key"] = config_value
        
        # Verify cache has value
        self.assertIn("test_key", self.service._cache)
        
        # Notify change
        self.service.notify_change("test_key", "old_value", "new_value")
        
        # Cache should be invalidated
        self.assertNotIn("test_key", self.service._cache)
    
    def test_thread_safety(self):
        """Test thread safety of cache operations"""
        # Mock database configuration
        mock_db_config = Mock()
        mock_db_config.get_typed_value.return_value = "db_value"
        mock_db_config.data_type = "string"
        mock_db_config.updated_at = datetime.now(timezone.utc)
        
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = mock_db_config
        self.service.system_config_manager.get_configuration_schema = Mock(return_value=self.mock_schema)
        
        results = []
        errors = []
        
        def worker():
            try:
                for i in range(10):
                    result = self.service.get_config(f"test_key_{i % 3}")
                    results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Start multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify no errors and results
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(results), 50)  # 5 threads * 10 operations each
    
    def test_cache_statistics(self):
        """Test cache statistics collection"""
        # Mock database configuration
        mock_db_config = Mock()
        mock_db_config.get_typed_value.return_value = "db_value"
        mock_db_config.data_type = "string"
        mock_db_config.updated_at = datetime.now(timezone.utc)
        
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = mock_db_config
        self.service.system_config_manager.get_configuration_schema = Mock(return_value=self.mock_schema)
        
        # Perform various operations
        self.service.get_config("test_key1")  # Cache miss, database read
        self.service.get_config("test_key1")  # Cache hit
        
        os.environ["TEST_CONFIG_TEST_KEY2"] = "env_value"
        self.service.get_config("test_key2")  # Environment override
        
        # Mock no database result for default fallback
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = None
        self.service.get_config("test_key3")  # Default fallback
        
        # Get statistics
        stats = self.service.get_cache_stats()
        
        # Verify statistics
        self.assertEqual(stats['statistics']['cache_hits'], 1)
        self.assertEqual(stats['statistics']['cache_misses'], 3)
        self.assertEqual(stats['statistics']['database_reads'], 2)  # test_key1 and test_key3
        self.assertEqual(stats['statistics']['environment_overrides'], 1)
        self.assertEqual(stats['statistics']['default_fallbacks'], 1)
        self.assertEqual(stats['hit_rate'], 0.25)  # 1 hit out of 4 total requests
        self.assertEqual(stats['total_requests'], 4)
    
    def test_error_handling(self):
        """Test error handling in various scenarios"""
        # Test database error
        self.mock_session.query.side_effect = Exception("Database error")
        self.service.system_config_manager.get_configuration_schema = Mock(return_value=self.mock_schema)
        
        # Should fall back to schema default
        result = self.service.get_config("test_key")
        self.assertEqual(result, "default_value")
        self.assertEqual(self.service._stats['default_fallbacks'], 1)
        
        # Test configuration not found
        self.mock_session.query.side_effect = None
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = None
        self.service.system_config_manager.get_configuration_schema = Mock(return_value=None)
        
        # Should raise ConfigurationNotFoundError when getting with metadata
        with self.assertRaises(ConfigurationNotFoundError):
            self.service.get_config_with_metadata("nonexistent_key")
        
        # Should return default when using get_config
        result = self.service.get_config("nonexistent_key", "fallback")
        self.assertEqual(result, "fallback")
    
    def test_callback_error_handling(self):
        """Test error handling in subscription callbacks"""
        def failing_callback(key, old_value, new_value):
            raise Exception("Callback error")
        
        # Subscribe with failing callback
        subscription_id = self.service.subscribe_to_changes("test_key", failing_callback)
        
        # Notify change - should not raise exception
        try:
            self.service.notify_change("test_key", "old_value", "new_value")
        except Exception:
            self.fail("notify_change raised exception despite callback error")
        
        # Cleanup
        self.service.unsubscribe(subscription_id)


if __name__ == '__main__':
    unittest.main()
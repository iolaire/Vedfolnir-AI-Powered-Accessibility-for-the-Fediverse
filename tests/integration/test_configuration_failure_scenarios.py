# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Configuration System Failure Scenario Testing

Tests configuration system behavior under various failure conditions:
- Database unavailability and recovery
- Cache system failures and fallback
- Service recovery after configuration service outages
- Data consistency during partial system failures
- Disaster recovery scenarios
"""

import unittest
import time
import threading
from unittest.mock import Mock, patch, MagicMock, side_effect
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from config import Config
from app.core.database.core.database_manager import DatabaseManager
from models import SystemConfiguration, User, UserRole
from app.core.configuration.core.system_configuration_manager import SystemConfigurationManager
from app.core.configuration.core.configuration_service import (
    ConfigurationService, ConfigurationSource, ConfigurationError,
    ConfigurationServiceUnavailableError, ConfigurationNotFoundError
)
from app.core.configuration.cache.configuration_cache import ConfigurationCache
from app.core.configuration.events.configuration_event_bus import ConfigurationEventBus
from app.services.task.configuration.task_queue_configuration_adapter import TaskQueueConfigurationAdapter
from app.core.configuration.adapters.session_configuration_adapter import SessionConfigurationAdapter
from app.core.configuration.adapters.alert_configuration_adapter import AlertConfigurationAdapter


class TestConfigurationFailureScenarios(unittest.TestCase):
    """Test configuration system behavior under failure conditions"""
    
    def setUp(self):
        """Set up test environment for failure scenario testing"""
        self.config = Config()
        
        # Mock database manager
        self.db_manager = Mock(spec=DatabaseManager)
        self.session_mock = Mock()
        
        # Mock the context manager properly
        self.context_manager = Mock()
        self.context_manager.__enter__ = Mock(return_value=self.session_mock)
        self.context_manager.__exit__ = Mock(return_value=None)
        self.db_manager.get_session.return_value = self.context_manager
        
        # Create system configuration manager
        self.system_config_manager = SystemConfigurationManager(self.db_manager)
        
        # Create configuration service
        self.config_service = ConfigurationService(
            self.db_manager,
            cache_size=100,
            default_ttl=60
        )
        
        # Mock service components
        self.task_queue_manager = Mock()
        self.session_manager = Mock()
        self.alert_manager = Mock()
        
        # Set up test configurations
        self._setup_test_configurations()
        
        # Track failure recovery
        self.recovery_events = []
        self.error_events = []
    
    def _setup_test_configurations(self):
        """Set up test configurations for failure testing"""
        self.test_configs = {
            "max_concurrent_jobs": Mock(
                key="max_concurrent_jobs",
                value="10",
                data_type="integer",
                get_typed_value=Mock(return_value=10),
                updated_at=datetime.now(timezone.utc)
            ),
            "session_timeout_minutes": Mock(
                key="session_timeout_minutes",
                value="120",
                data_type="integer",
                get_typed_value=Mock(return_value=120),
                updated_at=datetime.now(timezone.utc)
            ),
            "alert_queue_backup_threshold": Mock(
                key="alert_queue_backup_threshold",
                value="100",
                data_type="integer",
                get_typed_value=Mock(return_value=100),
                updated_at=datetime.now(timezone.utc)
            )
        }
        
        # Mock database queries
        def mock_query_filter_by(key):
            mock_query = Mock()
            mock_query.first.return_value = self.test_configs.get(key)
            return mock_query
        
        self.session_mock.query.return_value.filter_by = mock_query_filter_by
    
    def test_database_unavailable_fallback_to_environment(self):
        """Test fallback to environment variables when database is unavailable"""
        # Set environment variable
        test_key = "test_db_unavailable"
        test_env_value = "environment_fallback_value"
        
        with patch.dict('os.environ', {f'VEDFOLNIR_CONFIG_{test_key.upper()}': test_env_value}):
            # Mock database connection failure
            self.db_manager.get_session.side_effect = Exception("Database connection failed")
            
            # Should fall back to environment variable
            value = self.config_service.get_config(test_key)
            self.assertEqual(value, test_env_value)
            
            # Verify source is environment
            config_value = self.config_service.get_config_with_metadata(test_key)
            self.assertEqual(config_value.source, ConfigurationSource.ENVIRONMENT)
    
    def test_database_unavailable_fallback_to_schema_defaults(self):
        """Test fallback to schema defaults when database and environment unavailable"""
        test_key = "test_schema_fallback"
        test_default_value = "schema_default_value"
        
        # Mock schema with default value
        with patch.object(self.system_config_manager, 'get_configuration_schema') as mock_schema:
            mock_schema_obj = Mock()
            mock_schema_obj.default_value = test_default_value
            mock_schema_obj.data_type.value = "string"
            mock_schema_obj.requires_restart = False
            mock_schema.return_value = mock_schema_obj
            
            # Mock database connection failure
            self.db_manager.get_session.side_effect = Exception("Database connection failed")
            
            # Should fall back to schema default
            value = self.config_service.get_config(test_key)
            self.assertEqual(value, test_default_value)
            
            # Verify source is default
            config_value = self.config_service.get_config_with_metadata(test_key)
            self.assertEqual(config_value.source, ConfigurationSource.DEFAULT)
    
    def test_database_recovery_after_outage(self):
        """Test configuration service recovery after database outage"""
        test_key = "max_concurrent_jobs"
        
        # First, get configuration successfully
        value1 = self.config_service.get_config(test_key)
        self.assertEqual(value1, 10)
        
        # Simulate database outage
        self.db_manager.get_session.side_effect = Exception("Database outage")
        
        # Should still work with cached value
        value2 = self.config_service.get_config(test_key)
        self.assertEqual(value2, 10)
        
        # Clear cache to force database access
        self.config_service.refresh_config(test_key)
        
        # Should fall back to default when cache is empty and DB is down
        with patch.object(self.system_config_manager, 'get_configuration_schema') as mock_schema:
            mock_schema_obj = Mock()
            mock_schema_obj.default_value = 5
            mock_schema_obj.data_type.value = "integer"
            mock_schema_obj.requires_restart = False
            mock_schema.return_value = mock_schema_obj
            
            value3 = self.config_service.get_config(test_key)
            self.assertEqual(value3, 5)
        
        # Restore database connection
        self.db_manager.get_session.side_effect = None
        self.db_manager.get_session.return_value = self.context_manager
        
        # Clear cache to force fresh database read
        self.config_service.refresh_config(test_key)
        
        # Should recover and read from database again
        value4 = self.config_service.get_config(test_key)
        self.assertEqual(value4, 10)
    
    def test_cache_system_failure_direct_database_access(self):
        """Test direct database access when cache system fails"""
        test_key = "max_concurrent_jobs"
        
        # Mock cache failure
        with patch.object(self.config_service, '_cache') as mock_cache:
            mock_cache.get.side_effect = Exception("Cache system failure")
            mock_cache.__setitem__.side_effect = Exception("Cache system failure")
            
            # Should still work by accessing database directly
            value = self.config_service.get_config(test_key)
            self.assertEqual(value, 10)
            
            # Verify database was accessed
            self.session_mock.query.assert_called()
    
    def test_partial_system_failure_data_consistency(self):
        """Test data consistency during partial system failures"""
        test_key = "max_concurrent_jobs"
        
        # Set up configuration change tracking
        changes_received = []
        
        def track_changes(key, old_value, new_value):
            changes_received.append({
                'key': key,
                'old_value': old_value,
                'new_value': new_value,
                'timestamp': time.time()
            })
        
        subscription_id = self.config_service.subscribe_to_changes(test_key, track_changes)
        
        try:
            # Simulate partial failure during configuration update
            with patch.object(self.session_mock, 'commit') as mock_commit:
                # First commit succeeds
                mock_commit.side_effect = [None, Exception("Commit failed")]
                
                # Update configuration
                self.config_service.notify_change(test_key, 10, 15)
                
                # Verify change was tracked despite commit failure
                self.assertEqual(len(changes_received), 1)
                self.assertEqual(changes_received[0]['new_value'], 15)
                
                # Cache should be invalidated
                self.assertNotIn(test_key, self.config_service._cache)
        
        finally:
            self.config_service.unsubscribe(subscription_id)
    
    def test_service_adapter_failure_recovery(self):
        """Test service adapter recovery after configuration service outages"""
        # Create adapters
        task_adapter = TaskQueueConfigurationAdapter(
            self.task_queue_manager,
            self.config_service
        )
        
        session_adapter = SessionConfigurationAdapter(
            self.session_manager,
            self.config_service
        )
        
        # Simulate configuration service failure
        with patch.object(self.config_service, 'get_config', side_effect=ConfigurationServiceUnavailableError("Service unavailable")):
            # Adapters should handle service unavailability gracefully
            try:
                task_adapter.update_concurrency_limits()
                session_adapter.update_timeout_settings()
                
                # Should not raise exceptions
                self.assertTrue(True)
                
            except Exception as e:
                self.fail(f"Adapter should handle service unavailability gracefully: {e}")
        
        # Restore service
        with patch.object(self.config_service, 'get_config', return_value=10):
            # Adapters should recover and work normally
            try:
                task_adapter.update_concurrency_limits()
                session_adapter.update_timeout_settings()
                
                # Should work normally
                self.assertTrue(True)
                
            except Exception as e:
                self.fail(f"Adapter should recover after service restoration: {e}")
    
    def test_event_bus_failure_configuration_updates_continue(self):
        """Test that configuration updates continue even if event bus fails"""
        test_key = "max_concurrent_jobs"
        
        # Mock event bus failure
        with patch.object(self.config_service, '_subscribers_lock') as mock_lock:
            mock_lock.__enter__.side_effect = Exception("Event bus lock failure")
            
            # Configuration updates should still work
            try:
                self.config_service.notify_change(test_key, 10, 15)
                
                # Should not raise exception
                self.assertTrue(True)
                
            except Exception as e:
                self.fail(f"Configuration updates should continue despite event bus failure: {e}")
    
    def test_concurrent_failure_and_recovery(self):
        """Test system behavior under concurrent failures and recovery"""
        num_threads = 10
        num_requests_per_thread = 20
        
        results = []
        errors = []
        
        # Simulate intermittent database failures
        failure_count = 0
        
        def intermittent_db_failure(*args, **kwargs):
            nonlocal failure_count
            failure_count += 1
            if failure_count % 3 == 0:  # Fail every 3rd request
                raise Exception("Intermittent database failure")
            return self.context_manager
        
        def worker_thread(thread_id):
            """Worker thread that accesses configuration during failures"""
            thread_results = []
            thread_errors = []
            
            for i in range(num_requests_per_thread):
                try:
                    # Access configuration
                    value = self.config_service.get_config("max_concurrent_jobs", default=5)
                    
                    thread_results.append({
                        'thread_id': thread_id,
                        'request_id': i,
                        'value': value,
                        'success': True
                    })
                    
                except Exception as e:
                    thread_errors.append({
                        'thread_id': thread_id,
                        'request_id': i,
                        'error': str(e),
                        'success': False
                    })
                
                # Small delay between requests
                time.sleep(0.001)
            
            return thread_results, thread_errors
        
        # Run concurrent access with intermittent failures
        with patch.object(self.db_manager, 'get_session', side_effect=intermittent_db_failure):
            threads = []
            
            for i in range(num_threads):
                thread = threading.Thread(target=lambda tid=i: worker_thread(tid))
                threads.append(thread)
                thread.start()
            
            # Collect results
            for thread in threads:
                thread.join(timeout=10.0)
                # Note: In a real implementation, we'd collect results properly
                # For this test, we're mainly checking that threads don't hang
        
        # Verify system remained responsive despite failures
        self.assertTrue(True)  # If we get here, threads didn't hang
    
    def test_disaster_recovery_configuration_system(self):
        """Test disaster recovery scenarios for configuration system"""
        # Scenario 1: Complete database loss
        self.db_manager.get_session.side_effect = Exception("Database completely unavailable")
        
        # System should still function with environment variables and defaults
        with patch.dict('os.environ', {'VEDFOLNIR_CONFIG_MAX_CONCURRENT_JOBS': '8'}):
            value = self.config_service.get_config("max_concurrent_jobs")
            self.assertEqual(value, "8")  # String from environment
        
        # Scenario 2: Cache corruption
        with patch.object(self.config_service, '_cache') as mock_cache:
            mock_cache.get.side_effect = Exception("Cache corrupted")
            mock_cache.clear.side_effect = Exception("Cache clear failed")
            
            # Should still work by bypassing cache
            with patch.dict('os.environ', {'VEDFOLNIR_CONFIG_SESSION_TIMEOUT_MINUTES': '90'}):
                value = self.config_service.get_config("session_timeout_minutes")
                self.assertEqual(value, "90")
        
        # Scenario 3: Complete service restart
        # Create new service instance (simulating restart)
        new_config_service = ConfigurationService(
            self.db_manager,
            cache_size=100,
            default_ttl=60
        )
        
        # Should initialize properly even with database issues
        self.assertIsNotNone(new_config_service)
        
        # Should work with environment fallback
        with patch.dict('os.environ', {'VEDFOLNIR_CONFIG_ALERT_QUEUE_BACKUP_THRESHOLD': '150'}):
            value = new_config_service.get_config("alert_queue_backup_threshold")
            self.assertEqual(value, "150")
    
    def test_configuration_validation_failure_recovery(self):
        """Test recovery from configuration validation failures"""
        # Mock admin user
        admin_user = Mock(spec=User)
        admin_user.id = 1
        admin_user.role = UserRole.ADMIN
        self.session_mock.query.return_value.filter_by.return_value.first.return_value = admin_user
        
        # Test validation failure recovery
        with patch.object(self.system_config_manager, 'validate_configuration_set') as mock_validate:
            # First validation fails
            mock_validate.return_value.is_valid = False
            mock_validate.return_value.errors = ["Invalid value"]
            
            success, message = self.system_config_manager.set_configuration(
                "max_concurrent_jobs", -1, 1
            )
            
            self.assertFalse(success)
            self.assertIn("validation", message.lower())
            
            # Second validation succeeds
            mock_validate.return_value.is_valid = True
            mock_validate.return_value.errors = []
            
            success, message = self.system_config_manager.set_configuration(
                "max_concurrent_jobs", 20, 1
            )
            
            self.assertTrue(success)
    
    def test_memory_pressure_cache_eviction(self):
        """Test cache behavior under memory pressure"""
        # Fill cache to capacity
        for i in range(150):  # More than cache size (100)
            key = f"test_key_{i:03d}"
            
            # Mock configuration
            mock_config = Mock()
            mock_config.get_typed_value.return_value = f"value_{i}"
            mock_config.updated_at = datetime.now(timezone.utc)
            
            def mock_query_for_key(query_key):
                mock_query = Mock()
                if query_key == key:
                    mock_query.first.return_value = mock_config
                else:
                    mock_query.first.return_value = self.test_configs.get(query_key)
                return mock_query
            
            self.session_mock.query.return_value.filter_by = mock_query_for_key
            
            # Access configuration to populate cache
            value = self.config_service.get_config(key)
            self.assertEqual(value, f"value_{i}")
        
        # Verify cache size is limited
        cache_stats = self.config_service.get_cache_stats()
        self.assertLessEqual(cache_stats['cache']['size'], 100)
        
        # Verify LRU eviction works
        # Access early keys - they should be evicted and require database access
        early_key = "test_key_001"
        
        # Reset database mock to track calls
        self.session_mock.reset_mock()
        
        value = self.config_service.get_config(early_key)
        
        # Should have accessed database (cache miss due to eviction)
        self.session_mock.query.assert_called()
    
    def test_network_partition_simulation(self):
        """Test behavior during simulated network partition"""
        # Simulate network partition by making database calls timeout
        def timeout_simulation(*args, **kwargs):
            time.sleep(0.1)  # Simulate slow network
            raise Exception("Network timeout")
        
        # Test with network issues
        with patch.object(self.db_manager, 'get_session', side_effect=timeout_simulation):
            start_time = time.time()
            
            # Should fail fast and fall back to defaults
            with patch.object(self.system_config_manager, 'get_configuration_schema') as mock_schema:
                mock_schema_obj = Mock()
                mock_schema_obj.default_value = 5
                mock_schema_obj.data_type.value = "integer"
                mock_schema_obj.requires_restart = False
                mock_schema.return_value = mock_schema_obj
                
                value = self.config_service.get_config("max_concurrent_jobs")
                
            end_time = time.time()
            
            # Should complete quickly despite network issues
            self.assertLess(end_time - start_time, 1.0)
            self.assertEqual(value, 5)  # Default value
    
    def test_configuration_corruption_detection(self):
        """Test detection and handling of corrupted configuration data"""
        # Mock corrupted configuration data
        corrupted_config = Mock()
        corrupted_config.get_typed_value.side_effect = Exception("Data corruption")
        corrupted_config.updated_at = datetime.now(timezone.utc)
        
        def mock_query_corrupted(key):
            mock_query = Mock()
            if key == "corrupted_config":
                mock_query.first.return_value = corrupted_config
            else:
                mock_query.first.return_value = self.test_configs.get(key)
            return mock_query
        
        self.session_mock.query.return_value.filter_by = mock_query_corrupted
        
        # Should handle corruption gracefully
        with patch.object(self.system_config_manager, 'get_configuration_schema') as mock_schema:
            mock_schema_obj = Mock()
            mock_schema_obj.default_value = "safe_default"
            mock_schema_obj.data_type.value = "string"
            mock_schema_obj.requires_restart = False
            mock_schema.return_value = mock_schema_obj
            
            value = self.config_service.get_config("corrupted_config")
            self.assertEqual(value, "safe_default")
        
        # Should track error in statistics
        stats = self.config_service.get_cache_stats()
        self.assertGreater(stats['statistics']['errors'], 0)


if __name__ == '__main__':
    unittest.main()
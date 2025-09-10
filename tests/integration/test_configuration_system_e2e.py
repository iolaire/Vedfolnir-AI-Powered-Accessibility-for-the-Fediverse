# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
End-to-End Configuration System Integration Tests

Tests the complete configuration flow from Admin UI → Database → Service → Application behavior.
Validates configuration change propagation, restart requirements, and fallback mechanisms.
"""

import unittest
import os
import time
import threading
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from typing import Dict, Any, List

from config import Config
from app.core.database.core.database_manager import DatabaseManager
from models import SystemConfiguration, User, UserRole
from app.core.configuration.core.system_configuration_manager import SystemConfigurationManager, ConfigurationCategory, ConfigurationDataType
from app.core.configuration.core.configuration_service import ConfigurationService, ConfigurationSource
from app.services.task.configuration.task_queue_configuration_adapter import TaskQueueConfigurationAdapter
from app.core.configuration.adapters.session_configuration_adapter import SessionConfigurationAdapter
from app.core.configuration.adapters.alert_configuration_adapter import AlertConfigurationAdapter
from feature_flag_service import FeatureFlagService
from app.services.maintenance.components.maintenance_mode_service import MaintenanceModeService


class TestConfigurationSystemE2E(unittest.TestCase):
    """End-to-end tests for the complete configuration system"""
    
    def setUp(self):
        """Set up test environment with all components"""
        self.config = Config()
        
        # Mock database manager
        self.db_manager = Mock(spec=DatabaseManager)
        self.session_mock = Mock()
        
        # Mock the context manager properly
        context_manager = Mock()
        context_manager.__enter__ = Mock(return_value=self.session_mock)
        context_manager.__exit__ = Mock(return_value=None)
        self.db_manager.get_session.return_value = context_manager
        
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
        
        # Create service adapters
        self.task_queue_adapter = TaskQueueConfigurationAdapter(
            self.task_queue_manager,
            self.config_service
        )
        
        self.session_adapter = SessionConfigurationAdapter(
            self.session_manager,
            self.config_service
        )
        
        self.alert_adapter = AlertConfigurationAdapter(
            self.alert_manager,
            self.config_service
        )
        
        # Create feature services
        self.feature_flag_service = FeatureFlagService(self.config_service)
        self.maintenance_service = MaintenanceModeService(self.config_service)
        
        # Create mock admin user
        self.admin_user = Mock(spec=User)
        self.admin_user.id = 1
        self.admin_user.role = UserRole.ADMIN
        
        # Track configuration changes for testing
        self.configuration_changes = []
        self.restart_notifications = []
        
        # Set up test configurations in database
        self._setup_test_configurations()
    
    def _setup_test_configurations(self):
        """Set up test configurations in mock database"""
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
            ),
            "enable_batch_processing": Mock(
                key="enable_batch_processing",
                value="true",
                data_type="boolean",
                get_typed_value=Mock(return_value=True),
                updated_at=datetime.now(timezone.utc)
            ),
            "maintenance_mode": Mock(
                key="maintenance_mode",
                value="false",
                data_type="boolean",
                get_typed_value=Mock(return_value=False),
                updated_at=datetime.now(timezone.utc)
            )
        }
        
        # Mock database queries
        def mock_query_filter_by(key):
            mock_query = Mock()
            mock_query.first.return_value = self.test_configs.get(key)
            return mock_query
        
        self.session_mock.query.return_value.filter_by = mock_query_filter_by
    
    def test_admin_ui_to_database_flow(self):
        """Test configuration flow from Admin UI to Database"""
        # Mock admin user query
        self.session_mock.query.return_value.filter_by.return_value.first.return_value = self.admin_user
        
        # Test configuration update through system manager
        success, message = self.system_config_manager.set_configuration(
            "max_concurrent_jobs", 20, 1
        )
        
        self.assertTrue(success)
        self.assertIn("successfully", message.lower())
        
        # Verify database interaction
        self.session_mock.query.assert_called()
        self.session_mock.commit.assert_called()
    
    def test_database_to_service_propagation(self):
        """Test configuration propagation from Database to ConfigurationService"""
        # Test getting configuration from service
        value = self.config_service.get_config("max_concurrent_jobs")
        self.assertEqual(value, 10)
        
        # Test cache behavior
        stats = self.config_service.get_cache_stats()
        self.assertGreater(stats['statistics']['cache_misses'], 0)
        
        # Test second access hits cache
        value2 = self.config_service.get_config("max_concurrent_jobs")
        self.assertEqual(value2, 10)
        
        stats2 = self.config_service.get_cache_stats()
        self.assertGreater(stats2['statistics']['cache_hits'], stats['statistics']['cache_hits'])
    
    def test_service_to_application_behavior(self):
        """Test configuration propagation from Service to Application behavior"""
        # Test task queue configuration update
        with patch.object(self.task_queue_adapter, 'update_concurrency_limits') as mock_update:
            # Simulate configuration change
            self.config_service.notify_change("max_concurrent_jobs", 10, 15)
            
            # Verify adapter was called
            mock_update.assert_called()
        
        # Test session configuration update
        with patch.object(self.session_adapter, 'update_timeout_settings') as mock_update:
            # Simulate configuration change
            self.config_service.notify_change("session_timeout_minutes", 120, 180)
            
            # Verify adapter was called
            mock_update.assert_called()
        
        # Test alert configuration update
        with patch.object(self.alert_adapter, 'update_thresholds') as mock_update:
            # Simulate configuration change
            self.config_service.notify_change("alert_queue_backup_threshold", 100, 150)
            
            # Verify adapter was called
            mock_update.assert_called()
    
    def test_configuration_change_propagation_timing(self):
        """Test that configuration changes propagate within required timeframes"""
        change_detected = threading.Event()
        change_value = None
        
        def change_callback(key, old_value, new_value):
            nonlocal change_value
            change_value = new_value
            change_detected.set()
        
        # Subscribe to changes
        subscription_id = self.config_service.subscribe_to_changes(
            "max_concurrent_jobs", change_callback
        )
        
        try:
            # Simulate configuration change
            start_time = time.time()
            self.config_service.notify_change("max_concurrent_jobs", 10, 20)
            
            # Wait for change notification (should be immediate)
            self.assertTrue(change_detected.wait(timeout=1.0))
            
            # Verify timing (should be under 1 second for in-memory notification)
            elapsed_time = time.time() - start_time
            self.assertLess(elapsed_time, 1.0)
            
            # Verify change value
            self.assertEqual(change_value, 20)
            
        finally:
            self.config_service.unsubscribe(subscription_id)
    
    def test_restart_requirement_handling(self):
        """Test restart requirement tracking and notification"""
        # Mock a configuration that requires restart
        with patch.object(self.config_service, '_requires_restart', return_value=True):
            # Simulate configuration change
            self.config_service.notify_change("some_restart_config", "old", "new")
            
            # Verify restart is required
            self.assertTrue(self.config_service.is_restart_required())
            
            # Verify pending restart configs
            pending = self.config_service.get_pending_restart_configs()
            self.assertIn("some_restart_config", pending)
    
    def test_environment_variable_override(self):
        """Test environment variable override functionality"""
        test_key = "test_env_override"
        test_value = "environment_value"
        
        # Set environment variable
        with patch.dict(os.environ, {f'VEDFOLNIR_CONFIG_{test_key.upper()}': test_value}):
            # Mock database config
            db_config = Mock()
            db_config.get_typed_value.return_value = "database_value"
            
            def mock_query_with_env(key):
                mock_query = Mock()
                if key == test_key:
                    mock_query.first.return_value = db_config
                else:
                    mock_query.first.return_value = self.test_configs.get(key)
                return mock_query
            
            self.session_mock.query.return_value.filter_by = mock_query_with_env
            
            # Get configuration - should return environment value
            value = self.config_service.get_config(test_key)
            self.assertEqual(value, test_value)
            
            # Verify source is environment
            config_value = self.config_service.get_config_with_metadata(test_key)
            self.assertEqual(config_value.source, ConfigurationSource.ENVIRONMENT)
    
    def test_schema_default_fallback(self):
        """Test fallback to schema defaults when database is unavailable"""
        # Mock schema with default value
        with patch.object(self.system_config_manager, 'get_configuration_schema') as mock_schema:
            mock_schema_obj = Mock()
            mock_schema_obj.default_value = "default_value"
            mock_schema_obj.data_type.value = "string"
            mock_schema_obj.requires_restart = False
            mock_schema.return_value = mock_schema_obj
            
            # Mock database error
            def mock_query_with_error(key):
                mock_query = Mock()
                if key == "test_default":
                    mock_query.first.side_effect = Exception("Database error")
                else:
                    mock_query.first.return_value = self.test_configs.get(key)
                return mock_query
            
            self.session_mock.query.return_value.filter_by = mock_query_with_error
            
            # Get configuration - should return default value
            value = self.config_service.get_config("test_default")
            self.assertEqual(value, "default_value")
            
            # Verify source is default
            config_value = self.config_service.get_config_with_metadata("test_default")
            self.assertEqual(config_value.source, ConfigurationSource.DEFAULT)
    
    def test_feature_flag_integration(self):
        """Test feature flag service integration with configuration system"""
        # Test feature flag enabled
        enabled = self.feature_flag_service.is_enabled("enable_batch_processing")
        self.assertTrue(enabled)
        
        # Test getting all flags
        all_flags = self.feature_flag_service.get_all_flags()
        self.assertIn("enable_batch_processing", all_flags)
        self.assertTrue(all_flags["enable_batch_processing"])
    
    def test_maintenance_mode_integration(self):
        """Test maintenance mode service integration with configuration system"""
        # Test maintenance mode disabled
        is_maintenance = self.maintenance_service.is_maintenance_mode()
        self.assertFalse(is_maintenance)
        
        # Test maintenance status
        status = self.maintenance_service.get_maintenance_status()
        self.assertIsNotNone(status)
        self.assertFalse(status.enabled)
    
    def test_configuration_validation_integration(self):
        """Test configuration validation integration across the system"""
        # Test valid configuration set
        valid_configs = {
            "max_concurrent_jobs": 15,
            "session_timeout_minutes": 180,
            "alert_queue_backup_threshold": 200
        }
        
        result = self.system_config_manager.validate_configuration_set(valid_configs)
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.errors), 0)
        
        # Test invalid configuration set
        invalid_configs = {
            "max_concurrent_jobs": 0,  # Below minimum
            "session_timeout_minutes": -1  # Invalid value
        }
        
        result = self.system_config_manager.validate_configuration_set(invalid_configs)
        self.assertFalse(result.is_valid)
        self.assertGreater(len(result.errors), 0)
    
    def test_configuration_cache_performance(self):
        """Test configuration cache performance under load"""
        # Warm up cache
        for _ in range(10):
            self.config_service.get_config("max_concurrent_jobs")
        
        # Measure cache performance
        start_time = time.time()
        for _ in range(100):
            value = self.config_service.get_config("max_concurrent_jobs")
            self.assertEqual(value, 10)
        
        elapsed_time = time.time() - start_time
        
        # Should be very fast with cache hits
        self.assertLess(elapsed_time, 0.1)  # 100 requests in under 100ms
        
        # Verify high cache hit rate
        stats = self.config_service.get_cache_stats()
        self.assertGreater(stats['hit_rate'], 0.9)  # >90% hit rate
    
    def test_concurrent_configuration_access(self):
        """Test concurrent configuration access and updates"""
        results = []
        errors = []
        
        def worker_thread(thread_id):
            try:
                for i in range(10):
                    value = self.config_service.get_config("max_concurrent_jobs")
                    results.append((thread_id, i, value))
                    time.sleep(0.001)  # Small delay
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        # Start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker_thread, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=5.0)
        
        # Verify no errors occurred
        self.assertEqual(len(errors), 0, f"Errors in concurrent access: {errors}")
        
        # Verify all threads got results
        self.assertEqual(len(results), 50)  # 5 threads * 10 requests each
        
        # Verify all results are consistent
        for thread_id, request_id, value in results:
            self.assertEqual(value, 10)
    
    def test_configuration_error_handling(self):
        """Test error handling throughout the configuration system"""
        # Test configuration service error handling
        with patch.object(self.db_manager, 'get_session', side_effect=Exception("DB Error")):
            # Should return default value without raising exception
            value = self.config_service.get_config("nonexistent_key", "default")
            self.assertEqual(value, "default")
            
            # Should track error in statistics
            stats = self.config_service.get_cache_stats()
            self.assertGreater(stats['statistics']['errors'], 0)
    
    def test_configuration_subscription_cleanup(self):
        """Test proper cleanup of configuration subscriptions"""
        callback_called = False
        
        def test_callback(key, old_value, new_value):
            nonlocal callback_called
            callback_called = True
        
        # Subscribe to changes
        subscription_id = self.config_service.subscribe_to_changes(
            "test_key", test_callback
        )
        
        # Verify subscription exists
        self.assertIsNotNone(subscription_id)
        
        # Trigger change
        self.config_service.notify_change("test_key", "old", "new")
        self.assertTrue(callback_called)
        
        # Unsubscribe
        success = self.config_service.unsubscribe(subscription_id)
        self.assertTrue(success)
        
        # Verify callback no longer called
        callback_called = False
        self.config_service.notify_change("test_key", "new", "newer")
        self.assertFalse(callback_called)
    
    def test_end_to_end_configuration_workflow(self):
        """Test complete end-to-end configuration workflow"""
        # Step 1: Admin updates configuration through UI (simulated)
        self.session_mock.query.return_value.filter_by.return_value.first.return_value = self.admin_user
        
        success, message = self.system_config_manager.set_configuration(
            "max_concurrent_jobs", 25, 1
        )
        self.assertTrue(success)
        
        # Step 2: Update mock database value
        self.test_configs["max_concurrent_jobs"].get_typed_value.return_value = 25
        
        # Step 3: Clear cache to force database read
        self.config_service.refresh_config("max_concurrent_jobs")
        
        # Step 4: Service reads new value
        value = self.config_service.get_config("max_concurrent_jobs")
        self.assertEqual(value, 25)
        
        # Step 5: Verify change propagation to adapters
        with patch.object(self.task_queue_adapter, 'update_concurrency_limits') as mock_update:
            self.config_service.notify_change("max_concurrent_jobs", 10, 25)
            mock_update.assert_called()
        
        # Step 6: Verify configuration metadata
        config_value = self.config_service.get_config_with_metadata("max_concurrent_jobs")
        self.assertEqual(config_value.value, 25)
        self.assertEqual(config_value.source, ConfigurationSource.DATABASE)


if __name__ == '__main__':
    unittest.main()
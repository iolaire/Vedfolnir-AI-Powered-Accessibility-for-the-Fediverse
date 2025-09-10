# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for AlertConfigurationAdapter

Tests the adapter functionality for connecting AlertManager with ConfigurationService
including threshold updates, notification channel configuration, and validation.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch, call
import sys
import os
from datetime import datetime, timezone

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from alert_configuration_adapter import AlertConfigurationAdapter, AlertConfigurationMapping
from app.services.alerts.components.alert_manager import AlertManager, AlertThresholds, NotificationChannel, NotificationConfig
from app.core.configuration.core.configuration_service import ConfigurationService, ConfigurationError
from app.core.configuration.events.configuration_event_bus import ConfigurationEventBus, ConfigurationChangeEvent, EventType


class TestAlertConfigurationAdapter(unittest.TestCase):
    """Test cases for AlertConfigurationAdapter"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock dependencies
        self.mock_alert_manager = Mock(spec=AlertManager)
        self.mock_config_service = Mock(spec=ConfigurationService)
        self.mock_event_bus = Mock(spec=ConfigurationEventBus)
        
        # Set up alert manager with default thresholds
        self.default_thresholds = AlertThresholds()
        self.mock_alert_manager.thresholds = self.default_thresholds
        self.mock_alert_manager.notification_configs = {
            NotificationChannel.EMAIL: NotificationConfig(
                channel=NotificationChannel.EMAIL,
                enabled=True,
                config={'admin_emails': ['admin@example.com']}
            ),
            NotificationChannel.WEBHOOK: NotificationConfig(
                channel=NotificationChannel.WEBHOOK,
                enabled=False,
                config={'webhook_url': 'https://example.com/webhook'}
            ),
            NotificationChannel.IN_APP: NotificationConfig(
                channel=NotificationChannel.IN_APP,
                enabled=True
            )
        }
        
        # Mock event bus subscription
        self.mock_event_bus.subscribe.return_value = "test-subscription-id"
        
        # Create adapter
        self.adapter = AlertConfigurationAdapter(
            self.mock_alert_manager,
            self.mock_config_service,
            self.mock_event_bus
        )
        
        # Reset statistics after initialization
        self.adapter._stats = {
            'threshold_updates': 0,
            'notification_updates': 0,
            'validation_failures': 0,
            'rollbacks': 0,
            'configuration_errors': 0,
            'validation_warnings': 0,
            'safe_fallbacks': 0
        }
    
    def test_initialization(self):
        """Test adapter initialization"""
        # Verify initialization completed
        self.assertIsNotNone(self.adapter.alert_manager)
        self.assertIsNotNone(self.adapter.config_service)
        self.assertIsNotNone(self.adapter.event_bus)
        
        # Verify subscriptions were created
        expected_subscription_count = len(AlertConfigurationAdapter.THRESHOLD_MAPPINGS) + len(AlertConfigurationAdapter.NOTIFICATION_MAPPINGS)
        self.assertEqual(self.mock_event_bus.subscribe.call_count, expected_subscription_count)
        
        # Verify last good values were stored
        self.assertIsNotNone(self.adapter._last_good_thresholds)
        self.assertIsNotNone(self.adapter._last_good_notification_configs)
    
    def test_threshold_mappings_configuration(self):
        """Test threshold mappings are properly configured"""
        mappings = AlertConfigurationAdapter.THRESHOLD_MAPPINGS
        
        # Verify all expected mappings exist
        expected_keys = [
            "alert_job_failure_rate_threshold",
            "alert_repeated_failure_count_threshold", 
            "alert_resource_usage_threshold",
            "alert_queue_backup_threshold",
            "alert_ai_service_timeout_threshold",
            "alert_performance_degradation_threshold"
        ]
        
        actual_keys = [mapping.config_key for mapping in mappings]
        for key in expected_keys:
            self.assertIn(key, actual_keys)
        
        # Verify validators are present for critical thresholds
        for mapping in mappings:
            if mapping.data_type in ['float', 'integer']:
                self.assertIsNotNone(mapping.validator, f"Validator missing for {mapping.config_key}")
    
    def test_notification_mappings_configuration(self):
        """Test notification mappings are properly configured"""
        mappings = AlertConfigurationAdapter.NOTIFICATION_MAPPINGS
        
        # Verify all expected mappings exist
        expected_keys = [
            "alert_email_enabled",
            "alert_webhook_enabled",
            "alert_in_app_enabled",
            "alert_notification_channels"
        ]
        
        actual_keys = [mapping.config_key for mapping in mappings]
        for key in expected_keys:
            self.assertIn(key, actual_keys)
    
    def test_update_alert_thresholds_success(self):
        """Test successful alert threshold updates"""
        # Mock configuration values
        config_values = {
            "alert_job_failure_rate_threshold": 0.15,
            "alert_repeated_failure_count_threshold": 5,
            "alert_resource_usage_threshold": 0.85,
            "alert_queue_backup_threshold": 150,
            "alert_ai_service_timeout_threshold": 45,
            "alert_performance_degradation_threshold": 2.5
        }
        
        def mock_get_config(key):
            return config_values.get(key)
        
        self.mock_config_service.get_config.side_effect = mock_get_config
        
        # Update thresholds
        result = self.adapter.update_alert_thresholds()
        
        # Verify success
        self.assertTrue(result)
        
        # Verify thresholds were updated
        updated_thresholds = self.mock_alert_manager.thresholds
        self.assertEqual(updated_thresholds.job_failure_rate, 0.15)
        self.assertEqual(updated_thresholds.repeated_failure_count, 5)
        self.assertEqual(updated_thresholds.resource_usage_threshold, 0.85)
        self.assertEqual(updated_thresholds.queue_backup_threshold, 150)
        self.assertEqual(updated_thresholds.ai_service_timeout, 45)
        self.assertEqual(updated_thresholds.performance_degradation_threshold, 2.5)
        
        # Verify statistics
        self.assertEqual(self.adapter._stats['threshold_updates'], 1)
    
    def test_update_alert_thresholds_validation_failure(self):
        """Test alert threshold update with validation failure"""
        # Mock invalid configuration values
        config_values = {
            "alert_job_failure_rate_threshold": 1.5,  # Invalid: > 1.0
            "alert_repeated_failure_count_threshold": 0,  # Invalid: < 1
            "alert_resource_usage_threshold": -0.1  # Invalid: < 0.0
        }
        
        def mock_get_config(key):
            return config_values.get(key)
        
        self.mock_config_service.get_config.side_effect = mock_get_config
        
        # Update thresholds
        result = self.adapter.update_alert_thresholds()
        
        # Verify failure due to validation
        self.assertFalse(result)
        
        # Verify validation failure statistics
        self.assertGreater(self.adapter._stats['validation_failures'], 0)
    
    def test_update_alert_thresholds_configuration_error(self):
        """Test alert threshold update with configuration service error"""
        # Mock configuration service error
        self.mock_config_service.get_config.side_effect = ConfigurationError("Service unavailable")
        
        # Update thresholds
        result = self.adapter.update_alert_thresholds()
        
        # Verify error handling
        self.assertFalse(result)
        self.assertEqual(self.adapter._stats['configuration_errors'], 1)
    
    def test_update_notification_channels_success(self):
        """Test successful notification channel updates"""
        # Mock configuration values
        config_values = {
            "alert_email_enabled": True,
            "alert_webhook_enabled": True,
            "alert_in_app_enabled": False,
            "alert_notification_channels": ["email", "webhook"]
        }
        
        def mock_get_config(key):
            return config_values.get(key)
        
        self.mock_config_service.get_config.side_effect = mock_get_config
        
        # Update notification channels
        result = self.adapter.update_notification_channels()
        
        # Verify success
        self.assertTrue(result)
        
        # Verify notification configs were updated
        email_config = self.mock_alert_manager.notification_configs[NotificationChannel.EMAIL]
        webhook_config = self.mock_alert_manager.notification_configs[NotificationChannel.WEBHOOK]
        in_app_config = self.mock_alert_manager.notification_configs[NotificationChannel.IN_APP]
        
        self.assertTrue(email_config.enabled)
        self.assertTrue(webhook_config.enabled)
        self.assertFalse(in_app_config.enabled)
        
        # Verify statistics
        self.assertEqual(self.adapter._stats['notification_updates'], 1)
    
    def test_handle_threshold_change_success(self):
        """Test successful individual threshold change"""
        # Test updating job failure rate threshold
        result = self.adapter.handle_threshold_change("alert_job_failure_rate_threshold", 0.2)
        
        # Verify success
        self.assertTrue(result)
        
        # Verify threshold was updated
        self.assertEqual(self.mock_alert_manager.thresholds.job_failure_rate, 0.2)
        
        # Verify statistics
        self.assertEqual(self.adapter._stats['threshold_updates'], 1)
    
    def test_handle_threshold_change_validation_failure(self):
        """Test threshold change with validation failure"""
        # Test updating with invalid value
        result = self.adapter.handle_threshold_change("alert_job_failure_rate_threshold", 2.0)
        
        # Verify failure
        self.assertFalse(result)
        
        # Verify statistics
        self.assertEqual(self.adapter._stats['validation_failures'], 1)
    
    def test_handle_threshold_change_unknown_type(self):
        """Test threshold change with unknown threshold type"""
        # Test updating unknown threshold
        result = self.adapter.handle_threshold_change("unknown_threshold", 0.5)
        
        # Verify failure
        self.assertFalse(result)
    
    def test_threshold_validation_success(self):
        """Test successful threshold validation"""
        # Create valid thresholds
        thresholds = AlertThresholds(
            job_failure_rate=0.1,
            repeated_failure_count=3,
            resource_usage_threshold=0.9,
            queue_backup_threshold=100,
            ai_service_timeout=30,
            performance_degradation_threshold=2.0
        )
        
        # Validate thresholds using the validator
        result = self.adapter._validator.validate_thresholds(thresholds)
        
        # Verify success
        self.assertTrue(result.is_valid)
    
    def test_threshold_validation_failure(self):
        """Test threshold validation failure"""
        # Create invalid thresholds
        thresholds = AlertThresholds(
            job_failure_rate=1.5,  # Invalid: > 1.0
            repeated_failure_count=0,  # Invalid: < 1
            resource_usage_threshold=-0.1,  # Invalid: < 0.0
            queue_backup_threshold=0,  # Invalid: < 1
            ai_service_timeout=0,  # Invalid: < 1
            performance_degradation_threshold=0.5  # Invalid: < 1.0
        )
        
        # Validate thresholds using the validator
        result = self.adapter._validator.validate_thresholds(thresholds)
        
        # Verify failure
        self.assertFalse(result.is_valid)
    
    def test_rollback_to_safe_values(self):
        """Test rollback to safe configuration values"""
        # Store original thresholds
        original_thresholds = AlertThresholds(
            job_failure_rate=0.05,
            repeated_failure_count=2,
            resource_usage_threshold=0.8,
            queue_backup_threshold=50,
            ai_service_timeout=20,
            performance_degradation_threshold=1.5
        )
        
        self.adapter._last_good_thresholds = original_thresholds
        
        # Perform rollback
        result = self.adapter.rollback_to_safe_values()
        
        # Verify success
        self.assertTrue(result)
        
        # Verify thresholds were rolled back
        self.assertEqual(self.mock_alert_manager.thresholds, original_thresholds)
        
        # Verify statistics
        self.assertEqual(self.adapter._stats['rollbacks'], 1)
    
    def test_get_current_configuration(self):
        """Test getting current configuration values"""
        # Get current configuration
        config = self.adapter.get_current_configuration()
        
        # Verify structure
        self.assertIn('thresholds', config)
        self.assertIn('notification_channels', config)
        
        # Verify threshold values
        thresholds = config['thresholds']
        self.assertIn('job_failure_rate', thresholds)
        self.assertIn('repeated_failure_count', thresholds)
        self.assertIn('resource_usage_threshold', thresholds)
        self.assertIn('queue_backup_threshold', thresholds)
        self.assertIn('ai_service_timeout', thresholds)
        self.assertIn('performance_degradation_threshold', thresholds)
        
        # Verify notification channels
        channels = config['notification_channels']
        self.assertIn('email', channels)
        self.assertIn('webhook', channels)
        self.assertIn('in_app', channels)
    
    def test_get_adapter_statistics(self):
        """Test getting adapter statistics"""
        # Update some statistics
        self.adapter._stats['threshold_updates'] = 5
        self.adapter._stats['validation_failures'] = 2
        
        # Get statistics
        stats = self.adapter.get_adapter_statistics()
        
        # Verify structure
        self.assertIn('statistics', stats)
        self.assertIn('subscriptions', stats)
        self.assertIn('last_good_thresholds_available', stats)
        self.assertIn('last_good_notification_configs_count', stats)
        
        # Verify values
        self.assertEqual(stats['statistics']['threshold_updates'], 5)
        self.assertEqual(stats['statistics']['validation_failures'], 2)
        self.assertTrue(stats['last_good_thresholds_available'])
    
    def test_configuration_change_event_handling(self):
        """Test handling of configuration change events"""
        # Create a configuration change event
        event = ConfigurationChangeEvent(
            event_type=EventType.CONFIGURATION_CHANGED,
            key="alert_job_failure_rate_threshold",
            old_value=0.1,
            new_value=0.15,
            source="admin",
            timestamp=datetime.now(timezone.utc),
            requires_restart=False
        )
        
        # Handle the event
        self.adapter._handle_threshold_change(event)
        
        # Verify threshold was updated
        self.assertEqual(self.mock_alert_manager.thresholds.job_failure_rate, 0.15)
    
    def test_cleanup(self):
        """Test adapter cleanup"""
        # Add some subscriptions
        self.adapter._subscriptions = ["sub1", "sub2", "sub3"]
        
        # Perform cleanup
        self.adapter.cleanup()
        
        # Verify subscriptions were removed
        self.assertEqual(len(self.adapter._subscriptions), 0)
        
        # Verify event bus unsubscribe was called
        expected_calls = [call("sub1"), call("sub2"), call("sub3")]
        self.mock_event_bus.unsubscribe.assert_has_calls(expected_calls)
    
    def test_adapter_without_event_bus(self):
        """Test adapter functionality without event bus"""
        # Create adapter without event bus
        adapter = AlertConfigurationAdapter(
            self.mock_alert_manager,
            self.mock_config_service,
            None  # No event bus
        )
        
        # Verify adapter works without event bus
        self.assertIsNotNone(adapter)
        self.assertIsNone(adapter.event_bus)
        self.assertEqual(len(adapter._subscriptions), 0)
    
    def test_threshold_mapping_validators(self):
        """Test threshold mapping validators"""
        mappings = AlertConfigurationAdapter.THRESHOLD_MAPPINGS
        
        for mapping in mappings:
            if mapping.validator:
                # Test valid values
                if mapping.data_type == 'float':
                    if 'performance_degradation' in mapping.config_key:
                        # Performance degradation threshold must be >= 1.0
                        self.assertTrue(mapping.validator(2.0))
                        self.assertTrue(mapping.validator(1.0))
                        self.assertFalse(mapping.validator(0.5))
                        self.assertFalse(mapping.validator(-0.1))
                    elif 'rate' in mapping.config_key or 'usage' in mapping.config_key:
                        # Rate and usage thresholds must be 0.0-1.0
                        self.assertTrue(mapping.validator(0.5))
                        self.assertTrue(mapping.validator(0.0))
                        self.assertTrue(mapping.validator(1.0))
                        self.assertFalse(mapping.validator(-0.1))
                        self.assertFalse(mapping.validator(1.1))
                
                elif mapping.data_type == 'integer':
                    self.assertTrue(mapping.validator(1))
                    self.assertTrue(mapping.validator(100))
                    self.assertFalse(mapping.validator(0))
                    self.assertFalse(mapping.validator(-1))


if __name__ == '__main__':
    unittest.main()
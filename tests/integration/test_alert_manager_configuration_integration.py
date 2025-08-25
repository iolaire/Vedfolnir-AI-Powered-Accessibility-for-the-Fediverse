# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integration tests for AlertManager configuration service integration

Tests the integration between AlertManager and ConfigurationService for
dynamic alert threshold updates and notification channel configuration.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
import sys
import os
from datetime import datetime, timezone

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from alert_manager import AlertManager, AlertThresholds, NotificationChannel, NotificationConfig
from configuration_service import ConfigurationService
from configuration_event_bus import ConfigurationEventBus, ConfigurationChangeEvent, EventType
from database import DatabaseManager
from config import Config


class TestAlertManagerConfigurationIntegration(unittest.TestCase):
    """Test cases for AlertManager configuration integration"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock dependencies
        self.mock_db_manager = Mock(spec=DatabaseManager)
        self.mock_config = Mock(spec=Config)
        self.mock_config_service = Mock(spec=ConfigurationService)
        self.mock_event_bus = Mock(spec=ConfigurationEventBus)
        
        # Set up configuration service mock
        self.config_values = {
            'alert_job_failure_rate_threshold': 0.15,
            'alert_repeated_failure_count_threshold': 5,
            'alert_resource_usage_threshold': 0.85,
            'alert_queue_backup_threshold': 150,
            'alert_ai_service_timeout_threshold': 45,
            'alert_performance_degradation_threshold': 2.5,
            'alert_email_enabled': True,
            'alert_webhook_enabled': False,
            'alert_in_app_enabled': True
        }
        
        def mock_get_config(key, default=None):
            return self.config_values.get(key, default)
        
        self.mock_config_service.get_config.side_effect = mock_get_config
        
        # Set up config mock attributes
        self.mock_config.SMTP_SERVER = 'localhost'
        self.mock_config.SMTP_PORT = 587
        self.mock_config.ALERT_FROM_EMAIL = 'alerts@test.com'
        self.mock_config.ADMIN_ALERT_EMAILS = 'admin@test.com'
        self.mock_config.WEBHOOK_ALERTS_ENABLED = False
        self.mock_config.ALERT_WEBHOOK_URL = ''
        self.mock_config.ALERT_WEBHOOK_SECRET = ''
    
    def test_alert_manager_initialization_with_configuration_service(self):
        """Test AlertManager initialization with configuration service"""
        # Create AlertManager with configuration service
        alert_manager = AlertManager(
            self.mock_db_manager,
            self.mock_config,
            self.mock_config_service
        )
        
        # Verify configuration service is set
        self.assertEqual(alert_manager.configuration_service, self.mock_config_service)
        
        # Verify thresholds were loaded from configuration
        self.assertEqual(alert_manager.thresholds.job_failure_rate, 0.15)
        self.assertEqual(alert_manager.thresholds.repeated_failure_count, 5)
        self.assertEqual(alert_manager.thresholds.resource_usage_threshold, 0.85)
        self.assertEqual(alert_manager.thresholds.queue_backup_threshold, 150)
        self.assertEqual(alert_manager.thresholds.ai_service_timeout, 45)
        self.assertEqual(alert_manager.thresholds.performance_degradation_threshold, 2.5)
        
        # Verify notification configurations were loaded
        email_config = alert_manager.notification_configs[NotificationChannel.EMAIL]
        webhook_config = alert_manager.notification_configs[NotificationChannel.WEBHOOK]
        in_app_config = alert_manager.notification_configs[NotificationChannel.IN_APP]
        
        self.assertTrue(email_config.enabled)
        self.assertFalse(webhook_config.enabled)
        self.assertTrue(in_app_config.enabled)
    
    def test_alert_manager_initialization_without_configuration_service(self):
        """Test AlertManager initialization without configuration service"""
        # Create AlertManager without configuration service
        alert_manager = AlertManager(
            self.mock_db_manager,
            self.mock_config
        )
        
        # Verify configuration service is None
        self.assertIsNone(alert_manager.configuration_service)
        
        # Verify default thresholds are used
        self.assertEqual(alert_manager.thresholds.job_failure_rate, 0.1)
        self.assertEqual(alert_manager.thresholds.repeated_failure_count, 3)
        self.assertEqual(alert_manager.thresholds.resource_usage_threshold, 0.9)
        self.assertEqual(alert_manager.thresholds.queue_backup_threshold, 100)
        self.assertEqual(alert_manager.thresholds.ai_service_timeout, 30)
        self.assertEqual(alert_manager.thresholds.performance_degradation_threshold, 2.0)
    
    @patch('alert_manager.AlertConfigurationAdapter')
    def test_configuration_adapter_initialization(self, mock_adapter_class):
        """Test configuration adapter initialization"""
        mock_adapter = Mock()
        mock_adapter_class.return_value = mock_adapter
        
        # Create AlertManager with configuration service
        alert_manager = AlertManager(
            self.mock_db_manager,
            self.mock_config,
            self.mock_config_service
        )
        
        # Verify adapter was created
        mock_adapter_class.assert_called_once()
        self.assertEqual(alert_manager._config_adapter, mock_adapter)
    
    def test_get_threshold_from_config(self):
        """Test getting threshold values from configuration"""
        # Create AlertManager with configuration service
        alert_manager = AlertManager(
            self.mock_db_manager,
            self.mock_config,
            self.mock_config_service
        )
        
        # Test getting existing configuration
        value = alert_manager.get_threshold_from_config('alert_job_failure_rate_threshold', 0.1)
        self.assertEqual(value, 0.15)
        
        # Test getting non-existent configuration
        value = alert_manager.get_threshold_from_config('non_existent_key', 0.5)
        self.assertEqual(value, 0.5)
    
    def test_get_threshold_from_config_without_service(self):
        """Test getting threshold values without configuration service"""
        # Create AlertManager without configuration service
        alert_manager = AlertManager(
            self.mock_db_manager,
            self.mock_config
        )
        
        # Test getting configuration returns default
        value = alert_manager.get_threshold_from_config('alert_job_failure_rate_threshold', 0.1)
        self.assertEqual(value, 0.1)
    
    def test_get_notification_config_from_service(self):
        """Test getting notification configuration from service"""
        # Create AlertManager with configuration service
        alert_manager = AlertManager(
            self.mock_db_manager,
            self.mock_config,
            self.mock_config_service
        )
        
        # Test getting existing configuration
        value = alert_manager.get_notification_config_from_service('alert_email_enabled', False)
        self.assertTrue(value)
        
        # Test getting non-existent configuration
        value = alert_manager.get_notification_config_from_service('non_existent_key', True)
        self.assertTrue(value)
    
    def test_update_thresholds_from_configuration(self):
        """Test updating thresholds from configuration"""
        with patch('alert_manager.AlertConfigurationAdapter') as mock_adapter_class:
            mock_adapter = Mock()
            mock_adapter.update_alert_thresholds.return_value = True
            mock_adapter_class.return_value = mock_adapter
            
            # Create AlertManager with configuration service
            alert_manager = AlertManager(
                self.mock_db_manager,
                self.mock_config,
                self.mock_config_service
            )
            
            # Test updating thresholds
            result = alert_manager.update_thresholds_from_configuration()
            
            # Verify success
            self.assertTrue(result)
            mock_adapter.update_alert_thresholds.assert_called_once()
    
    def test_update_thresholds_from_configuration_without_adapter(self):
        """Test updating thresholds without configuration adapter"""
        # Create AlertManager without configuration service
        alert_manager = AlertManager(
            self.mock_db_manager,
            self.mock_config
        )
        
        # Test updating thresholds
        result = alert_manager.update_thresholds_from_configuration()
        
        # Verify failure
        self.assertFalse(result)
    
    def test_update_notification_channels_from_configuration(self):
        """Test updating notification channels from configuration"""
        with patch('alert_manager.AlertConfigurationAdapter') as mock_adapter_class:
            mock_adapter = Mock()
            mock_adapter.update_notification_channels.return_value = True
            mock_adapter_class.return_value = mock_adapter
            
            # Create AlertManager with configuration service
            alert_manager = AlertManager(
                self.mock_db_manager,
                self.mock_config,
                self.mock_config_service
            )
            
            # Test updating notification channels
            result = alert_manager.update_notification_channels_from_configuration()
            
            # Verify success
            self.assertTrue(result)
            mock_adapter.update_notification_channels.assert_called_once()
    
    def test_update_notification_channels_from_configuration_without_adapter(self):
        """Test updating notification channels without configuration adapter"""
        # Create AlertManager without configuration service
        alert_manager = AlertManager(
            self.mock_db_manager,
            self.mock_config
        )
        
        # Test updating notification channels
        result = alert_manager.update_notification_channels_from_configuration()
        
        # Verify failure
        self.assertFalse(result)
    
    def test_alert_thresholds_from_configuration_service(self):
        """Test AlertThresholds creation from configuration service"""
        # Test with configuration service
        thresholds = AlertThresholds.from_configuration_service(self.mock_config_service)
        
        # Verify values from configuration
        self.assertEqual(thresholds.job_failure_rate, 0.15)
        self.assertEqual(thresholds.repeated_failure_count, 5)
        self.assertEqual(thresholds.resource_usage_threshold, 0.85)
        self.assertEqual(thresholds.queue_backup_threshold, 150)
        self.assertEqual(thresholds.ai_service_timeout, 45)
        self.assertEqual(thresholds.performance_degradation_threshold, 2.5)
    
    def test_alert_thresholds_from_configuration_service_none(self):
        """Test AlertThresholds creation without configuration service"""
        # Test without configuration service
        thresholds = AlertThresholds.from_configuration_service(None)
        
        # Verify default values
        self.assertEqual(thresholds.job_failure_rate, 0.1)
        self.assertEqual(thresholds.repeated_failure_count, 3)
        self.assertEqual(thresholds.resource_usage_threshold, 0.9)
        self.assertEqual(thresholds.queue_backup_threshold, 100)
        self.assertEqual(thresholds.ai_service_timeout, 30)
        self.assertEqual(thresholds.performance_degradation_threshold, 2.0)
    
    def test_alert_thresholds_from_configuration_service_error(self):
        """Test AlertThresholds creation with configuration service error"""
        # Mock configuration service error
        error_config_service = Mock()
        error_config_service.get_config.side_effect = Exception("Configuration error")
        
        # Test with error
        thresholds = AlertThresholds.from_configuration_service(error_config_service)
        
        # Verify default values are used
        self.assertEqual(thresholds.job_failure_rate, 0.1)
        self.assertEqual(thresholds.repeated_failure_count, 3)
        self.assertEqual(thresholds.resource_usage_threshold, 0.9)
        self.assertEqual(thresholds.queue_backup_threshold, 100)
        self.assertEqual(thresholds.ai_service_timeout, 30)
        self.assertEqual(thresholds.performance_degradation_threshold, 2.0)
    
    def test_cleanup(self):
        """Test AlertManager cleanup"""
        with patch('alert_manager.AlertConfigurationAdapter') as mock_adapter_class:
            mock_adapter = Mock()
            mock_adapter_class.return_value = mock_adapter
            
            # Create AlertManager with configuration service
            alert_manager = AlertManager(
                self.mock_db_manager,
                self.mock_config,
                self.mock_config_service
            )
            
            # Test cleanup
            alert_manager.cleanup()
            
            # Verify adapter cleanup was called
            mock_adapter.cleanup.assert_called_once()
            self.assertIsNone(alert_manager._config_adapter)
    
    def test_dynamic_threshold_updates(self):
        """Test dynamic threshold updates through configuration changes"""
        with patch('alert_manager.AlertConfigurationAdapter') as mock_adapter_class:
            mock_adapter = Mock()
            mock_adapter_class.return_value = mock_adapter
            
            # Create AlertManager with configuration service
            alert_manager = AlertManager(
                self.mock_db_manager,
                self.mock_config,
                self.mock_config_service
            )
            
            # Simulate configuration change
            new_config_values = self.config_values.copy()
            new_config_values['alert_job_failure_rate_threshold'] = 0.2
            
            def new_mock_get_config(key, default=None):
                return new_config_values.get(key, default)
            
            self.mock_config_service.get_config.side_effect = new_mock_get_config
            
            # Update thresholds
            mock_adapter.update_alert_thresholds.return_value = True
            result = alert_manager.update_thresholds_from_configuration()
            
            # Verify update was called
            self.assertTrue(result)
            mock_adapter.update_alert_thresholds.assert_called()
    
    def test_dynamic_notification_updates(self):
        """Test dynamic notification channel updates through configuration changes"""
        with patch('alert_manager.AlertConfigurationAdapter') as mock_adapter_class:
            mock_adapter = Mock()
            mock_adapter_class.return_value = mock_adapter
            
            # Create AlertManager with configuration service
            alert_manager = AlertManager(
                self.mock_db_manager,
                self.mock_config,
                self.mock_config_service
            )
            
            # Simulate configuration change
            new_config_values = self.config_values.copy()
            new_config_values['alert_webhook_enabled'] = True
            
            def new_mock_get_config(key, default=None):
                return new_config_values.get(key, default)
            
            self.mock_config_service.get_config.side_effect = new_mock_get_config
            
            # Update notification channels
            mock_adapter.update_notification_channels.return_value = True
            result = alert_manager.update_notification_channels_from_configuration()
            
            # Verify update was called
            self.assertTrue(result)
            mock_adapter.update_notification_channels.assert_called()


if __name__ == '__main__':
    unittest.main()
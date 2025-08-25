# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for MaintenanceModeService

Tests maintenance mode functionality including status checking,
configuration integration, and change notifications.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
import sys
import os
from datetime import datetime, timezone
import threading
import time

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from maintenance_mode_service import (
    MaintenanceModeService, MaintenanceStatus, MaintenanceInfo, 
    MaintenanceChangeEvent, MaintenanceModeError
)
from configuration_service import ConfigurationValue, ConfigurationSource


class TestMaintenanceModeService(unittest.TestCase):
    """Test cases for MaintenanceModeService"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_config_service = Mock()
        self.mock_event_bus = Mock()
        
        # Create service instance
        self.service = MaintenanceModeService(
            config_service=self.mock_config_service,
            event_bus=self.mock_event_bus
        )
    
    def tearDown(self):
        """Clean up after tests"""
        # Clear any subscribers
        with self.service._subscribers_lock:
            self.service._change_subscribers.clear()
    
    def test_initialization(self):
        """Test service initialization"""
        # Test basic initialization
        service = MaintenanceModeService(self.mock_config_service)
        self.assertIsNotNone(service)
        self.assertEqual(service.config_service, self.mock_config_service)
        self.assertIsNone(service.event_bus)
        
        # Test initialization with event bus
        service_with_bus = MaintenanceModeService(
            self.mock_config_service, 
            self.mock_event_bus
        )
        self.assertEqual(service_with_bus.event_bus, self.mock_event_bus)
    
    def test_is_maintenance_mode_enabled(self):
        """Test maintenance mode check when enabled"""
        # Mock configuration service to return enabled
        mock_config = ConfigurationValue(
            key="maintenance_mode",
            value=True,
            data_type="boolean",
            source=ConfigurationSource.DATABASE,
            requires_restart=False,
            last_updated=datetime.now(timezone.utc),
            cached_at=datetime.now(timezone.utc),
            ttl=300
        )
        
        def mock_get_config(key):
            if key == "maintenance_mode":
                return mock_config
            elif key == "maintenance_reason":
                return None
            return None
        
        self.mock_config_service.get_config_with_metadata.side_effect = mock_get_config
        
        # Test maintenance mode check
        result = self.service.is_maintenance_mode()
        
        self.assertTrue(result)
    
    def test_is_maintenance_mode_disabled(self):
        """Test maintenance mode check when disabled"""
        # Mock configuration service to return disabled
        mock_config = ConfigurationValue(
            key="maintenance_mode",
            value=False,
            data_type="boolean",
            source=ConfigurationSource.DATABASE,
            requires_restart=False,
            last_updated=datetime.now(timezone.utc),
            cached_at=datetime.now(timezone.utc),
            ttl=300
        )
        self.mock_config_service.get_config_with_metadata.return_value = mock_config
        
        # Test maintenance mode check
        result = self.service.is_maintenance_mode()
        
        self.assertFalse(result)
    
    def test_is_maintenance_mode_no_config(self):
        """Test maintenance mode check when no configuration exists"""
        # Mock configuration service to return None
        self.mock_config_service.get_config_with_metadata.return_value = None
        
        # Test maintenance mode check
        result = self.service.is_maintenance_mode()
        
        self.assertFalse(result)
    
    def test_is_maintenance_mode_error_handling(self):
        """Test maintenance mode check error handling"""
        # Mock configuration service to raise exception
        self.mock_config_service.get_config_with_metadata.side_effect = Exception("Config error")
        
        # Test maintenance mode check
        result = self.service.is_maintenance_mode()
        
        # Should return False on error
        self.assertFalse(result)
    
    def test_get_maintenance_reason_with_reason(self):
        """Test getting maintenance reason when reason exists"""
        # Mock maintenance mode enabled
        mode_config = ConfigurationValue(
            key="maintenance_mode",
            value=True,
            data_type="boolean",
            source=ConfigurationSource.DATABASE,
            requires_restart=False,
            last_updated=datetime.now(timezone.utc),
            cached_at=datetime.now(timezone.utc),
            ttl=300
        )
        
        # Mock maintenance reason
        reason_config = ConfigurationValue(
            key="maintenance_reason",
            value="Database maintenance in progress",
            data_type="string",
            source=ConfigurationSource.DATABASE,
            requires_restart=False,
            last_updated=datetime.now(timezone.utc),
            cached_at=datetime.now(timezone.utc),
            ttl=300
        )
        
        def mock_get_config(key):
            if key == "maintenance_mode":
                return mode_config
            elif key == "maintenance_reason":
                return reason_config
            return None
        
        self.mock_config_service.get_config_with_metadata.side_effect = mock_get_config
        
        # Test getting maintenance reason
        result = self.service.get_maintenance_reason()
        
        self.assertEqual(result, "Database maintenance in progress")
    
    def test_get_maintenance_reason_no_reason(self):
        """Test getting maintenance reason when no reason exists"""
        # Mock maintenance mode enabled
        mode_config = ConfigurationValue(
            key="maintenance_mode",
            value=True,
            data_type="boolean",
            source=ConfigurationSource.DATABASE,
            requires_restart=False,
            last_updated=datetime.now(timezone.utc),
            cached_at=datetime.now(timezone.utc),
            ttl=300
        )
        
        def mock_get_config(key):
            if key == "maintenance_mode":
                return mode_config
            elif key == "maintenance_reason":
                return None
            return None
        
        self.mock_config_service.get_config_with_metadata.side_effect = mock_get_config
        
        # Test getting maintenance reason
        result = self.service.get_maintenance_reason()
        
        self.assertIsNone(result)
    
    def test_get_maintenance_reason_empty_string(self):
        """Test getting maintenance reason when reason is empty string"""
        # Mock maintenance mode enabled
        mode_config = ConfigurationValue(
            key="maintenance_mode",
            value=True,
            data_type="boolean",
            source=ConfigurationSource.DATABASE,
            requires_restart=False,
            last_updated=datetime.now(timezone.utc),
            cached_at=datetime.now(timezone.utc),
            ttl=300
        )
        
        # Mock empty maintenance reason
        reason_config = ConfigurationValue(
            key="maintenance_reason",
            value="",
            data_type="string",
            source=ConfigurationSource.DATABASE,
            requires_restart=False,
            last_updated=datetime.now(timezone.utc),
            cached_at=datetime.now(timezone.utc),
            ttl=300
        )
        
        def mock_get_config(key):
            if key == "maintenance_mode":
                return mode_config
            elif key == "maintenance_reason":
                return reason_config
            return None
        
        self.mock_config_service.get_config_with_metadata.side_effect = mock_get_config
        
        # Test getting maintenance reason
        result = self.service.get_maintenance_reason()
        
        self.assertIsNone(result)
    
    def test_get_maintenance_status_enabled(self):
        """Test getting comprehensive maintenance status when enabled"""
        test_time = datetime.now(timezone.utc)
        
        # Mock maintenance mode enabled
        mode_config = ConfigurationValue(
            key="maintenance_mode",
            value=True,
            data_type="boolean",
            source=ConfigurationSource.DATABASE,
            requires_restart=False,
            last_updated=test_time,
            cached_at=test_time,
            ttl=300
        )
        
        # Mock maintenance reason
        reason_config = ConfigurationValue(
            key="maintenance_reason",
            value="System upgrade",
            data_type="string",
            source=ConfigurationSource.DATABASE,
            requires_restart=False,
            last_updated=test_time,
            cached_at=test_time,
            ttl=300
        )
        
        def mock_get_config(key):
            if key == "maintenance_mode":
                return mode_config
            elif key == "maintenance_reason":
                return reason_config
            return None
        
        self.mock_config_service.get_config_with_metadata.side_effect = mock_get_config
        
        # Test getting maintenance status
        result = self.service.get_maintenance_status()
        
        self.assertIsInstance(result, MaintenanceInfo)
        self.assertTrue(result.enabled)
        self.assertEqual(result.reason, "System upgrade")
        self.assertEqual(result.status, MaintenanceStatus.ACTIVE)
        self.assertEqual(result.source, "database")
        self.assertIsNotNone(result.enabled_at)
        self.assertIsNone(result.disabled_at)
    
    def test_get_maintenance_status_disabled(self):
        """Test getting comprehensive maintenance status when disabled"""
        test_time = datetime.now(timezone.utc)
        
        # Mock maintenance mode disabled
        mode_config = ConfigurationValue(
            key="maintenance_mode",
            value=False,
            data_type="boolean",
            source=ConfigurationSource.DATABASE,
            requires_restart=False,
            last_updated=test_time,
            cached_at=test_time,
            ttl=300
        )
        
        def mock_get_config(key):
            if key == "maintenance_mode":
                return mode_config
            elif key == "maintenance_reason":
                return None
            return None
        
        self.mock_config_service.get_config_with_metadata.side_effect = mock_get_config
        
        # Test getting maintenance status
        result = self.service.get_maintenance_status()
        
        self.assertIsInstance(result, MaintenanceInfo)
        self.assertFalse(result.enabled)
        self.assertIsNone(result.reason)
        self.assertEqual(result.status, MaintenanceStatus.INACTIVE)
        self.assertEqual(result.source, "database")
        self.assertIsNone(result.enabled_at)
        self.assertIsNotNone(result.disabled_at)
    
    def test_get_maintenance_status_error_handling(self):
        """Test maintenance status error handling"""
        # Mock configuration service to raise exception
        self.mock_config_service.get_config_with_metadata.side_effect = Exception("Config error")
        
        # Test getting maintenance status
        result = self.service.get_maintenance_status()
        
        # Should return safe default status
        self.assertIsInstance(result, MaintenanceInfo)
        self.assertFalse(result.enabled)
        self.assertIsNone(result.reason)
        self.assertEqual(result.status, MaintenanceStatus.INACTIVE)
        self.assertEqual(result.source, "error_fallback")
    
    def test_enable_maintenance(self):
        """Test enabling maintenance mode"""
        # Test enabling maintenance
        result = self.service.enable_maintenance("System upgrade", "admin")
        
        self.assertTrue(result)
    
    def test_disable_maintenance(self):
        """Test disabling maintenance mode"""
        # Test disabling maintenance
        result = self.service.disable_maintenance("admin")
        
        self.assertTrue(result)
    
    def test_subscribe_to_changes(self):
        """Test subscribing to maintenance mode changes"""
        callback = Mock()
        
        # Subscribe to changes
        subscription_id = self.service.subscribe_to_changes(callback)
        
        self.assertIsNotNone(subscription_id)
        self.assertIn(subscription_id, self.service._change_subscribers)
    
    def test_unsubscribe_from_changes(self):
        """Test unsubscribing from maintenance mode changes"""
        callback = Mock()
        
        # Subscribe first
        subscription_id = self.service.subscribe_to_changes(callback)
        
        # Then unsubscribe
        result = self.service.unsubscribe_from_changes(subscription_id)
        
        self.assertTrue(result)
        self.assertNotIn(subscription_id, self.service._change_subscribers)
    
    def test_unsubscribe_nonexistent(self):
        """Test unsubscribing from non-existent subscription"""
        result = self.service.unsubscribe_from_changes("nonexistent-id")
        
        self.assertFalse(result)
    
    def test_get_status_summary(self):
        """Test getting status summary"""
        # Mock maintenance status
        test_time = datetime.now(timezone.utc)
        mode_config = ConfigurationValue(
            key="maintenance_mode",
            value=True,
            data_type="boolean",
            source=ConfigurationSource.DATABASE,
            requires_restart=False,
            last_updated=test_time,
            cached_at=test_time,
            ttl=300
        )
        
        reason_config = ConfigurationValue(
            key="maintenance_reason",
            value="Test maintenance",
            data_type="string",
            source=ConfigurationSource.DATABASE,
            requires_restart=False,
            last_updated=test_time,
            cached_at=test_time,
            ttl=300
        )
        
        def mock_get_config(key):
            if key == "maintenance_mode":
                return mode_config
            elif key == "maintenance_reason":
                return reason_config
            return None
        
        self.mock_config_service.get_config_with_metadata.side_effect = mock_get_config
        
        # Add a subscriber
        callback = Mock()
        self.service.subscribe_to_changes(callback)
        
        # Test getting status summary
        result = self.service.get_status_summary()
        
        self.assertIsInstance(result, dict)
        self.assertIn('maintenance_mode', result)
        self.assertIn('subscribers', result)
        self.assertIn('last_check', result)
        
        maintenance_info = result['maintenance_mode']
        self.assertTrue(maintenance_info['enabled'])
        self.assertEqual(maintenance_info['reason'], "Test maintenance")
        self.assertEqual(maintenance_info['status'], "active")
        self.assertEqual(result['subscribers'], 1)
    
    def test_get_status_summary_error_handling(self):
        """Test status summary error handling"""
        # Mock configuration service to raise exception
        self.mock_config_service.get_config_with_metadata.side_effect = Exception("Config error")
        
        # Test getting status summary
        result = self.service.get_status_summary()
        
        self.assertIsInstance(result, dict)
        self.assertIn('maintenance_mode', result)
        maintenance_info = result['maintenance_mode']
        self.assertFalse(maintenance_info['enabled'])
        # The service returns 'inactive' status when there's an error, not 'error'
        # because get_maintenance_status() handles errors and returns a safe default
        self.assertEqual(maintenance_info['status'], 'inactive')
        self.assertEqual(maintenance_info['source'], 'error_fallback')
    
    def test_refresh_status(self):
        """Test refreshing maintenance status"""
        # Test refresh
        result = self.service.refresh_status()
        
        self.assertTrue(result)
        
        # Verify configuration service refresh was called
        self.mock_config_service.refresh_config.assert_any_call("maintenance_mode")
        self.mock_config_service.refresh_config.assert_any_call("maintenance_reason")
    
    def test_refresh_status_error_handling(self):
        """Test refresh status error handling"""
        # Mock configuration service to raise exception
        self.mock_config_service.refresh_config.side_effect = Exception("Refresh error")
        
        # Test refresh
        result = self.service.refresh_status()
        
        self.assertFalse(result)
    
    def test_convert_to_boolean(self):
        """Test boolean conversion utility"""
        # Test various boolean conversions
        test_cases = [
            (True, True),
            (False, False),
            ("true", True),
            ("false", False),
            ("TRUE", True),
            ("FALSE", False),
            ("1", True),
            ("0", False),
            ("yes", True),
            ("no", False),
            ("on", True),
            ("off", False),
            ("enabled", True),
            ("disabled", False),
            (1, True),
            (0, False),
            (42, True),
            (-1, True),
            (0.0, False),
            (1.5, True),
            ("", False),
            ("other", False),
            (None, False),
            ([], False),
            ([1], True)
        ]
        
        for input_value, expected in test_cases:
            with self.subTest(input_value=input_value):
                result = self.service._convert_to_boolean(input_value)
                self.assertEqual(result, expected, f"Failed for input: {input_value}")
    
    def test_change_notification_threading(self):
        """Test change notifications work correctly with threading"""
        callback_results = []
        callback_lock = threading.Lock()
        
        def test_callback(event):
            with callback_lock:
                callback_results.append(event)
        
        # Subscribe to changes
        subscription_id = self.service.subscribe_to_changes(test_callback)
        
        # Create change event
        change_event = MaintenanceChangeEvent(
            enabled=True,
            reason="Test reason",
            changed_at=datetime.now(timezone.utc)
        )
        
        # Notify subscribers
        self.service._notify_change_subscribers(change_event)
        
        # Give time for callback to execute
        time.sleep(0.1)
        
        # Check results
        with callback_lock:
            self.assertEqual(len(callback_results), 1)
            self.assertEqual(callback_results[0].enabled, True)
            self.assertEqual(callback_results[0].reason, "Test reason")
    
    def test_change_notification_error_handling(self):
        """Test change notification error handling"""
        def failing_callback(event):
            raise Exception("Callback error")
        
        # Subscribe with failing callback
        subscription_id = self.service.subscribe_to_changes(failing_callback)
        
        # Create change event
        change_event = MaintenanceChangeEvent(
            enabled=True,
            reason="Test reason",
            changed_at=datetime.now(timezone.utc)
        )
        
        # This should not raise an exception
        try:
            self.service._notify_change_subscribers(change_event)
        except Exception as e:
            self.fail(f"Change notification should handle callback errors gracefully: {e}")
    
    def test_configuration_change_handlers(self):
        """Test configuration change handlers"""
        # Test maintenance mode change handler
        self.service._handle_maintenance_mode_change("maintenance_mode", False, True)
        
        # Test maintenance reason change handler
        # First enable maintenance mode
        mode_config = ConfigurationValue(
            key="maintenance_mode",
            value=True,
            data_type="boolean",
            source=ConfigurationSource.DATABASE,
            requires_restart=False,
            last_updated=datetime.now(timezone.utc),
            cached_at=datetime.now(timezone.utc),
            ttl=300
        )
        
        def mock_get_config(key):
            if key == "maintenance_mode":
                return mode_config
            return None
        
        self.mock_config_service.get_config_with_metadata.side_effect = mock_get_config
        
        # Now test reason change
        self.service._handle_maintenance_reason_change("maintenance_reason", "Old reason", "New reason")


if __name__ == '__main__':
    unittest.main()
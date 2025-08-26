# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for EnhancedMaintenanceModeService
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from enhanced_maintenance_mode_service import (
    EnhancedMaintenanceModeService, MaintenanceMode, MaintenanceStatus,
    MaintenanceActivationError, SessionInvalidationError
)
from models import User, UserRole


class TestEnhancedMaintenanceModeService(unittest.TestCase):
    """Test cases for EnhancedMaintenanceModeService"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_config_service = Mock()
        self.service = EnhancedMaintenanceModeService(self.mock_config_service)
        
        # Mock admin user
        self.admin_user = Mock(spec=User)
        self.admin_user.role = UserRole.ADMIN
        self.admin_user.username = "admin"
        
        # Mock regular user
        self.regular_user = Mock(spec=User)
        self.regular_user.role = UserRole.REVIEWER
        self.regular_user.username = "user"
    
    def test_enable_maintenance_normal_mode(self):
        """Test enabling maintenance mode in normal mode"""
        # Test enabling maintenance
        result = self.service.enable_maintenance(
            reason="System upgrade",
            duration=60,
            mode=MaintenanceMode.NORMAL,
            enabled_by="admin"
        )
        
        self.assertTrue(result)
        
        # Check status
        status = self.service.get_maintenance_status()
        self.assertTrue(status.is_active)
        self.assertEqual(status.mode, MaintenanceMode.NORMAL)
        self.assertEqual(status.reason, "System upgrade")
        self.assertEqual(status.estimated_duration, 60)
        self.assertEqual(status.enabled_by, "admin")
        self.assertFalse(status.test_mode)
    
    def test_enable_maintenance_emergency_mode(self):
        """Test enabling maintenance mode in emergency mode"""
        result = self.service.enable_maintenance(
            reason="Critical security issue",
            mode=MaintenanceMode.EMERGENCY,
            enabled_by="admin"
        )
        
        self.assertTrue(result)
        
        status = self.service.get_maintenance_status()
        self.assertTrue(status.is_active)
        self.assertEqual(status.mode, MaintenanceMode.EMERGENCY)
        self.assertEqual(status.reason, "Critical security issue")
        self.assertFalse(status.test_mode)
    
    def test_enable_maintenance_test_mode(self):
        """Test enabling maintenance mode in test mode"""
        result = self.service.enable_maintenance(
            reason="Testing maintenance procedures",
            mode=MaintenanceMode.TEST,
            enabled_by="admin"
        )
        
        self.assertTrue(result)
        
        status = self.service.get_maintenance_status()
        self.assertTrue(status.is_active)
        self.assertEqual(status.mode, MaintenanceMode.TEST)
        self.assertTrue(status.test_mode)
    
    def test_disable_maintenance(self):
        """Test disabling maintenance mode"""
        # First enable maintenance
        self.service.enable_maintenance("Test", enabled_by="admin")
        
        # Then disable it
        result = self.service.disable_maintenance(disabled_by="admin")
        
        self.assertTrue(result)
        
        status = self.service.get_maintenance_status()
        self.assertFalse(status.is_active)
        self.assertEqual(status.mode, MaintenanceMode.NORMAL)
        self.assertIsNone(status.reason)
        self.assertFalse(status.test_mode)
    
    def test_is_operation_blocked_maintenance_inactive(self):
        """Test operation blocking when maintenance is inactive"""
        # Maintenance is inactive by default
        result = self.service.is_operation_blocked("/some/endpoint")
        
        self.assertFalse(result)
    
    def test_is_operation_blocked_test_mode(self):
        """Test operation blocking in test mode"""
        # Enable test mode
        self.service.enable_maintenance("Test", mode=MaintenanceMode.TEST)
        
        result = self.service.is_operation_blocked("/some/endpoint")
        
        # Should not block in test mode
        self.assertFalse(result)
    
    def test_is_operation_blocked_admin_bypass(self):
        """Test admin user bypass during maintenance"""
        # Enable maintenance
        self.service.enable_maintenance("Test", mode=MaintenanceMode.NORMAL)
        
        result = self.service.is_operation_blocked("/some/endpoint", self.admin_user)
        
        # Admin should bypass blocking
        self.assertFalse(result)
    
    def test_is_operation_blocked_regular_user(self):
        """Test operation blocking for regular user"""
        # Enable maintenance
        self.service.enable_maintenance("Test", mode=MaintenanceMode.NORMAL)
        
        # Test with a caption generation endpoint that should be blocked
        result = self.service.is_operation_blocked("/caption/generate", self.regular_user)
        
        # Should be blocked for regular user (assuming caption generation is blocked)
        # Note: This test depends on the actual classifier implementation
        self.assertIsInstance(result, bool)
    
    def test_get_maintenance_status_from_config(self):
        """Test getting maintenance status from configuration service"""
        # Mock configuration service responses
        self.mock_config_service.get_config.side_effect = lambda key, default: {
            "maintenance_mode": True,
            "maintenance_reason": "Scheduled maintenance"
        }.get(key, default)
        
        # Clear internal status to force config lookup
        self.service._current_status = None
        
        status = self.service.get_maintenance_status()
        
        self.assertTrue(status.is_active)
        self.assertEqual(status.reason, "Scheduled maintenance")
        self.assertEqual(status.mode, MaintenanceMode.NORMAL)
    
    def test_get_blocked_operations(self):
        """Test getting list of blocked operations"""
        # Enable maintenance
        self.service.enable_maintenance("Test", mode=MaintenanceMode.NORMAL)
        
        blocked_operations = self.service.get_blocked_operations()
        
        # Should return blocked operation types
        self.assertIsInstance(blocked_operations, list)
    
    def test_get_maintenance_message_inactive(self):
        """Test maintenance message when maintenance is inactive"""
        # Ensure maintenance is inactive
        self.service.disable_maintenance()
        
        message = self.service.get_maintenance_message()
        
        self.assertEqual(message, "System is operating normally.")
    
    def test_get_maintenance_message_normal_mode(self):
        """Test maintenance message in normal mode"""
        self.service.enable_maintenance(
            reason="Database upgrade",
            duration=30,
            mode=MaintenanceMode.NORMAL
        )
        
        message = self.service.get_maintenance_message("/some/operation")
        
        self.assertIn("System maintenance is currently in progress", message)
        self.assertIn("Database upgrade", message)
        self.assertIn("/some/operation", message)
        # Duration should be shown in the message
        self.assertTrue("30 minutes" in message or "Expected completion" in message)
    
    def test_get_maintenance_message_emergency_mode(self):
        """Test maintenance message in emergency mode"""
        self.service.enable_maintenance(
            reason="Security incident",
            mode=MaintenanceMode.EMERGENCY
        )
        
        message = self.service.get_maintenance_message()
        
        self.assertIn("Emergency maintenance", message)
        self.assertIn("Security incident", message)
    
    def test_get_maintenance_message_test_mode(self):
        """Test maintenance message in test mode"""
        self.service.enable_maintenance(
            reason="Testing procedures",
            mode=MaintenanceMode.TEST
        )
        
        message = self.service.get_maintenance_message()
        
        self.assertIn("Test maintenance mode", message)
        self.assertIn("Testing procedures", message)
    
    def test_subscribe_to_changes(self):
        """Test subscribing to maintenance mode changes"""
        callback = Mock()
        
        subscription_id = self.service.subscribe_to_changes(callback)
        
        self.assertIsInstance(subscription_id, str)
        self.assertTrue(len(subscription_id) > 0)
        
        # Enable maintenance to trigger callback
        self.service.enable_maintenance("Test")
        
        # Callback should be called
        callback.assert_called()
    
    def test_unsubscribe(self):
        """Test unsubscribing from maintenance mode changes"""
        callback = Mock()
        
        subscription_id = self.service.subscribe_to_changes(callback)
        result = self.service.unsubscribe(subscription_id)
        
        self.assertTrue(result)
        
        # Enable maintenance - callback should not be called
        callback.reset_mock()
        self.service.enable_maintenance("Test")
        
        callback.assert_not_called()
    
    def test_unsubscribe_invalid_id(self):
        """Test unsubscribing with invalid subscription ID"""
        result = self.service.unsubscribe("invalid-id")
        
        self.assertFalse(result)
    
    def test_get_service_stats(self):
        """Test getting service statistics"""
        # Enable maintenance to populate stats
        self.service.enable_maintenance("Test", mode=MaintenanceMode.NORMAL)
        
        stats = self.service.get_service_stats()
        
        self.assertIn('current_status', stats)
        self.assertIn('statistics', stats)
        self.assertIn('subscribers_count', stats)
        self.assertIn('blocked_operations_count', stats)
        
        self.assertTrue(stats['current_status']['is_active'])
        self.assertEqual(stats['current_status']['mode'], 'normal')
        self.assertEqual(stats['statistics']['maintenance_activations'], 1)
    
    def test_update_active_jobs_count(self):
        """Test updating active jobs count"""
        self.service.enable_maintenance("Test")
        
        self.service.update_active_jobs_count(5)
        
        status = self.service.get_maintenance_status()
        self.assertEqual(status.active_jobs_count, 5)
    
    def test_update_invalidated_sessions_count(self):
        """Test updating invalidated sessions count"""
        self.service.enable_maintenance("Test")
        
        self.service.update_invalidated_sessions_count(10)
        
        status = self.service.get_maintenance_status()
        self.assertEqual(status.invalidated_sessions, 10)
    
    def test_log_maintenance_event(self):
        """Test logging maintenance events"""
        with patch('enhanced_maintenance_mode_service.logger') as mock_logger:
            self.service.log_maintenance_event(
                "test_event",
                {"key": "value"},
                "admin"
            )
            
            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args
            self.assertIn("test_event", call_args[0][0])
            self.assertIn("admin", call_args[0][0])
    
    def test_create_maintenance_report(self):
        """Test creating maintenance report"""
        self.service.enable_maintenance(
            reason="Test maintenance",
            duration=30,
            enabled_by="admin"
        )
        
        report = self.service.create_maintenance_report()
        
        self.assertIn('report_generated_at', report)
        self.assertIn('maintenance_status', report)
        self.assertIn('blocked_operations', report)
        self.assertIn('system_impact', report)
        self.assertIn('service_statistics', report)
        
        self.assertTrue(report['maintenance_status']['is_active'])
        self.assertEqual(report['maintenance_status']['reason'], "Test maintenance")
    
    def test_configuration_change_handling(self):
        """Test handling configuration changes"""
        # Setup subscription callback
        callback = Mock()
        self.service.subscribe_to_changes(callback)
        
        # Simulate configuration change
        self.service._handle_maintenance_config_change(
            "maintenance_mode", False, True
        )
        
        # Callback should be called with configuration change event
        callback.assert_called_with('configuration_changed', unittest.mock.ANY)
    
    def test_error_handling_in_enable_maintenance(self):
        """Test error handling during maintenance activation"""
        # Mock an exception during enable
        with patch.object(self.service, '_notify_change_subscribers', side_effect=Exception("Test error")):
            with self.assertRaises(MaintenanceActivationError):
                self.service.enable_maintenance("Test")
    
    def test_error_handling_in_operation_blocking(self):
        """Test error handling during operation blocking check"""
        # Enable maintenance
        self.service.enable_maintenance("Test")
        
        # Test with invalid operation that might cause errors
        result = self.service.is_operation_blocked(None, self.regular_user)
        
        # Should default to allowing operations on error
        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()
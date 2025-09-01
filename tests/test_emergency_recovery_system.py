# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Emergency Recovery System Tests

Comprehensive tests for the notification system emergency recovery mechanisms,
including failure detection, recovery procedures, and rollback capabilities.
"""

import unittest
import sys
import os
import tempfile
import shutil
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from notification_emergency_recovery import (
    NotificationEmergencyRecovery, EmergencyLevel, RecoveryAction, FailureType,
    EmergencyEvent, RecoveryPlan
)
from unified_notification_manager import UnifiedNotificationManager
from websocket_factory import WebSocketFactory
from websocket_auth_handler import WebSocketAuthHandler
from websocket_namespace_manager import WebSocketNamespaceManager
from database import DatabaseManager


class TestEmergencyRecoverySystem(unittest.TestCase):
    """Test cases for emergency recovery system"""
    
    def setUp(self):
        """Set up test environment"""
        # Create mock dependencies
        self.mock_notification_manager = Mock(spec=UnifiedNotificationManager)
        self.mock_websocket_factory = Mock(spec=WebSocketFactory)
        self.mock_auth_handler = Mock(spec=WebSocketAuthHandler)
        self.mock_namespace_manager = Mock(spec=WebSocketNamespaceManager)
        self.mock_db_manager = Mock(spec=DatabaseManager)
        
        # Create emergency recovery system
        self.emergency_recovery = NotificationEmergencyRecovery(
            self.mock_notification_manager,
            self.mock_websocket_factory,
            self.mock_auth_handler,
            self.mock_namespace_manager,
            self.mock_db_manager
        )
    
    def test_emergency_recovery_initialization(self):
        """Test emergency recovery system initialization"""
        self.assertIsNotNone(self.emergency_recovery)
        self.assertFalse(self.emergency_recovery._emergency_active)
        self.assertEqual(len(self.emergency_recovery._emergency_events), 0)
        self.assertTrue(self.emergency_recovery._fallback_enabled)
        self.assertEqual(self.emergency_recovery._health_status, "healthy")
    
    def test_failure_classification(self):
        """Test failure type classification"""
        # Test WebSocket connection failure
        websocket_error = Exception("WebSocket connection failed")
        failure_type = self.emergency_recovery._classify_failure(websocket_error, {})
        self.assertEqual(failure_type, FailureType.WEBSOCKET_CONNECTION_FAILURE)
        
        # Test message delivery failure
        delivery_error = Exception("Failed to emit message")
        failure_type = self.emergency_recovery._classify_failure(delivery_error, {})
        self.assertEqual(failure_type, FailureType.MESSAGE_DELIVERY_FAILURE)
        
        # Test database failure (use 'database' keyword without 'connection')
        db_error = Exception("Database query failed")
        failure_type = self.emergency_recovery._classify_failure(db_error, {})
        self.assertEqual(failure_type, FailureType.DATABASE_PERSISTENCE_FAILURE)
        
        # Test SQL failure (use 'sql' keyword)
        sql_error = Exception("SQL query failed")
        failure_type = self.emergency_recovery._classify_failure(sql_error, {})
        self.assertEqual(failure_type, FailureType.DATABASE_PERSISTENCE_FAILURE)
        
        # Test authentication failure
        auth_error = Exception("Authentication failed")
        failure_type = self.emergency_recovery._classify_failure(auth_error, {})
        self.assertEqual(failure_type, FailureType.AUTHENTICATION_FAILURE)
    
    def test_emergency_level_assessment(self):
        """Test emergency level assessment"""
        # Test critical system overload
        level = self.emergency_recovery._assess_emergency_level(
            FailureType.SYSTEM_OVERLOAD, {'affected_users': 50}
        )
        self.assertEqual(level, EmergencyLevel.CRITICAL)
        
        # Test high priority WebSocket failure with many users
        level = self.emergency_recovery._assess_emergency_level(
            FailureType.WEBSOCKET_CONNECTION_FAILURE, {'affected_users': 15}
        )
        self.assertEqual(level, EmergencyLevel.HIGH)
        
        # Test medium priority WebSocket failure with few users
        level = self.emergency_recovery._assess_emergency_level(
            FailureType.WEBSOCKET_CONNECTION_FAILURE, {'affected_users': 5}
        )
        self.assertEqual(level, EmergencyLevel.MEDIUM)
        
        # Test low priority authentication failure
        level = self.emergency_recovery._assess_emergency_level(
            FailureType.AUTHENTICATION_FAILURE, {'affected_users': 1}
        )
        self.assertEqual(level, EmergencyLevel.LOW)
    
    def test_emergency_event_creation(self):
        """Test emergency event creation"""
        error = Exception("Test error")
        context = {'affected_users': [1, 2, 3], 'component': 'test'}
        
        event = self.emergency_recovery._create_emergency_event(
            FailureType.MESSAGE_DELIVERY_FAILURE,
            EmergencyLevel.MEDIUM,
            error,
            context
        )
        
        self.assertIsInstance(event, EmergencyEvent)
        self.assertEqual(event.failure_type, FailureType.MESSAGE_DELIVERY_FAILURE)
        self.assertEqual(event.emergency_level, EmergencyLevel.MEDIUM)
        self.assertEqual(event.error_message, "Test error")
        self.assertEqual(event.affected_users, [1, 2, 3])
        self.assertFalse(event.recovery_success)
        self.assertIsNone(event.resolution_time)
    
    def test_detect_and_recover(self):
        """Test failure detection and recovery"""
        # Mock successful recovery actions
        self.emergency_recovery._execute_recovery_action = Mock(return_value=True)
        
        error = Exception("WebSocket connection failed")
        context = {'affected_users': 2, 'component': 'websocket'}  # Use integer instead of list
        
        success = self.emergency_recovery.detect_and_recover(error, context)
        
        self.assertTrue(success)
        self.assertEqual(len(self.emergency_recovery._emergency_events), 1)
        
        event = self.emergency_recovery._emergency_events[0]
        self.assertEqual(event.failure_type, FailureType.WEBSOCKET_CONNECTION_FAILURE)
        self.assertTrue(event.recovery_success)
        self.assertIsNotNone(event.resolution_time)
    
    def test_activate_emergency_mode(self):
        """Test emergency mode activation"""
        # Mock notification sending
        self.emergency_recovery._send_emergency_notification = Mock()
        
        success = self.emergency_recovery.activate_emergency_mode(
            "Test emergency", "test_user"
        )
        
        self.assertTrue(success)
        self.assertTrue(self.emergency_recovery._emergency_active)
        self.assertTrue(self.emergency_recovery._fallback_enabled)
        self.assertTrue(self.emergency_recovery._flash_fallback_enabled)
        self.assertTrue(self.emergency_recovery._emergency_broadcast_enabled)
        
        # Verify emergency notification was sent
        self.emergency_recovery._send_emergency_notification.assert_called_once()
    
    def test_deactivate_emergency_mode(self):
        """Test emergency mode deactivation"""
        # First activate emergency mode
        self.emergency_recovery._emergency_active = True
        
        # Mock successful restoration
        self.emergency_recovery._restore_normal_operations = Mock(return_value=True)
        self.emergency_recovery._send_emergency_notification = Mock()
        
        success = self.emergency_recovery.deactivate_emergency_mode("test_user")
        
        self.assertTrue(success)
        self.assertFalse(self.emergency_recovery._emergency_active)
        
        # Verify restoration was attempted
        self.emergency_recovery._restore_normal_operations.assert_called_once()
        
        # Verify recovery notification was sent
        self.emergency_recovery._send_emergency_notification.assert_called_once()
    
    def test_send_emergency_notification(self):
        """Test emergency notification sending"""
        # Mock successful WebSocket notification
        self.mock_notification_manager.send_admin_notification.return_value = True
        
        success = self.emergency_recovery.send_emergency_notification(
            "Test Alert", "Test message"
        )
        
        self.assertTrue(success)
        self.mock_notification_manager.send_admin_notification.assert_called_once()
    
    def test_send_emergency_notification_fallback(self):
        """Test emergency notification fallback to flash messages"""
        # Mock WebSocket failure
        self.mock_notification_manager.send_admin_notification.side_effect = Exception("WebSocket failed")
        
        # Mock Flask flash (would normally be imported from flask)
        with patch('notification_emergency_recovery.flash') as mock_flash:
            success = self.emergency_recovery.send_emergency_notification(
                "Test Alert", "Test message"
            )
            
            self.assertTrue(success)
            mock_flash.assert_called_once()
    
    def test_health_check(self):
        """Test system health check"""
        # Add health_check method to mock WebSocket factory
        self.mock_websocket_factory.health_check = Mock(return_value={'status': 'healthy'})
        
        # Add get_notification_stats method to mock notification manager
        self.mock_notification_manager.get_notification_stats = Mock(return_value={
            'messages_sent': 100,
            'success_rate': 0.95
        })
        
        # Mock database session context manager
        mock_session = Mock()
        mock_context_manager = Mock()
        mock_context_manager.__enter__ = Mock(return_value=mock_session)
        mock_context_manager.__exit__ = Mock(return_value=None)
        self.mock_db_manager.get_session.return_value = mock_context_manager
        
        health_results = self.emergency_recovery.run_health_check()
        
        self.assertIsInstance(health_results, dict)
        self.assertIn('timestamp', health_results)
        self.assertIn('overall_status', health_results)
        self.assertIn('components', health_results)
        
        # Verify components were checked
        self.assertIn('websocket_factory', health_results['components'])
        self.assertIn('notification_manager', health_results['components'])
        self.assertIn('database', health_results['components'])
    
    def test_recovery_plan_execution(self):
        """Test recovery plan execution"""
        # Create test event
        event = EmergencyEvent(
            event_id="test_event",
            timestamp=datetime.now(timezone.utc),
            failure_type=FailureType.WEBSOCKET_CONNECTION_FAILURE,
            emergency_level=EmergencyLevel.HIGH,
            affected_users=[1, 2, 3],
            error_message="Test error",
            stack_trace=None,
            recovery_actions=[],
            recovery_success=False,
            resolution_time=None,
            manual_intervention_required=False
        )
        
        # Mock successful recovery actions
        self.emergency_recovery._execute_recovery_action = Mock(return_value=True)
        
        success = self.emergency_recovery._execute_recovery_plan(event)
        
        self.assertTrue(success)
        self.assertGreater(len(event.recovery_actions), 0)
    
    def test_get_emergency_status(self):
        """Test emergency status reporting"""
        # Add some test events
        test_event = EmergencyEvent(
            event_id="test_event",
            timestamp=datetime.now(timezone.utc),
            failure_type=FailureType.MESSAGE_DELIVERY_FAILURE,
            emergency_level=EmergencyLevel.MEDIUM,
            affected_users=[1],
            error_message="Test error",
            stack_trace=None,
            recovery_actions=[RecoveryAction.FALLBACK_TO_FLASH],
            recovery_success=True,
            resolution_time=datetime.now(timezone.utc),
            manual_intervention_required=False
        )
        
        self.emergency_recovery._emergency_events.append(test_event)
        self.emergency_recovery._stats['emergency_events'] = 1
        self.emergency_recovery._stats['automatic_recoveries'] = 1
        
        status = self.emergency_recovery.get_emergency_status()
        
        self.assertIsInstance(status, dict)
        self.assertIn('emergency_active', status)
        self.assertIn('health_status', status)
        self.assertIn('fallback_systems', status)
        self.assertIn('statistics', status)
        self.assertIn('recent_events', status)
        
        # Verify statistics
        self.assertEqual(status['statistics']['emergency_events'], 1)
        self.assertEqual(status['statistics']['automatic_recoveries'], 1)
        
        # Verify recent events
        self.assertEqual(len(status['recent_events']), 1)
        self.assertEqual(status['recent_events'][0]['event_id'], 'test_event')
    
    def test_recovery_action_execution(self):
        """Test individual recovery action execution"""
        event = Mock()
        
        # Test restart WebSocket action
        self.mock_websocket_factory.restart = Mock(return_value=True)
        success = self.emergency_recovery._execute_recovery_action(
            RecoveryAction.RESTART_WEBSOCKET, event
        )
        self.assertTrue(success)
        
        # Test fallback activation
        success = self.emergency_recovery._execute_recovery_action(
            RecoveryAction.FALLBACK_TO_FLASH, event
        )
        self.assertTrue(success)
        self.assertTrue(self.emergency_recovery._flash_fallback_enabled)
        
        # Test emergency broadcast
        self.emergency_recovery.send_emergency_notification = Mock(return_value=True)
        success = self.emergency_recovery._execute_recovery_action(
            RecoveryAction.EMERGENCY_BROADCAST, event
        )
        self.assertTrue(success)
    
    def test_statistics_tracking(self):
        """Test emergency statistics tracking"""
        # Initial statistics
        initial_stats = self.emergency_recovery._stats.copy()
        
        # Simulate successful recovery
        error = Exception("Test error")
        context = {'affected_users': [1]}
        
        # Mock successful recovery
        self.emergency_recovery._execute_recovery_action = Mock(return_value=True)
        
        success = self.emergency_recovery.detect_and_recover(error, context)
        
        self.assertTrue(success)
        
        # Check updated statistics
        updated_stats = self.emergency_recovery._stats
        self.assertEqual(updated_stats['emergency_events'], initial_stats['emergency_events'] + 1)
        self.assertEqual(updated_stats['automatic_recoveries'], initial_stats['automatic_recoveries'] + 1)
        self.assertGreater(updated_stats['recovery_success_rate'], 0)


class TestEmergencyCLI(unittest.TestCase):
    """Test cases for emergency CLI tool"""
    
    def setUp(self):
        """Set up CLI test environment"""
        # Import CLI after setting up path
        from scripts.notification_emergency_cli import NotificationEmergencyCLI
        
        # Mock the CLI initialization to avoid real system dependencies
        with patch('scripts.notification_emergency_cli.Config'), \
             patch('scripts.notification_emergency_cli.DatabaseManager'), \
             patch('scripts.notification_emergency_cli.WebSocketFactory'), \
             patch('scripts.notification_emergency_cli.WebSocketAuthHandler'), \
             patch('scripts.notification_emergency_cli.WebSocketNamespaceManager'), \
             patch('scripts.notification_emergency_cli.UnifiedNotificationManager'), \
             patch('scripts.notification_emergency_cli.NotificationEmergencyRecovery') as mock_recovery:
            
            self.cli = NotificationEmergencyCLI()
            self.mock_emergency_recovery = Mock()
            self.cli.emergency_recovery = self.mock_emergency_recovery
    
    def test_cli_status_command(self):
        """Test CLI status command"""
        # Mock emergency status
        mock_status = {
            'emergency_active': False,
            'health_status': 'healthy',
            'last_health_check': '2025-08-30T12:00:00Z',
            'fallback_systems': {
                'fallback_enabled': True,
                'flash_fallback_enabled': True,
                'emergency_broadcast_enabled': True
            },
            'statistics': {
                'emergency_events': 5,
                'automatic_recoveries': 4,
                'manual_interventions': 1,
                'recovery_success_rate': 0.8
            },
            'recent_events': []
        }
        
        self.mock_emergency_recovery.get_emergency_status.return_value = mock_status
        
        result = self.cli.status()
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result, mock_status)
        self.mock_emergency_recovery.get_emergency_status.assert_called_once()
    
    def test_cli_health_check_command(self):
        """Test CLI health check command"""
        # Mock health check results
        mock_health = {
            'overall_status': 'healthy',
            'timestamp': '2025-08-30T12:00:00Z',
            'components': {
                'websocket_factory': {'status': 'healthy'},
                'notification_manager': {'status': 'healthy'},
                'database': {'status': 'healthy'}
            },
            'issues': [],
            'recommendations': []
        }
        
        self.mock_emergency_recovery.run_health_check.return_value = mock_health
        
        result = self.cli.health_check()
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result['overall_status'], 'healthy')
        self.mock_emergency_recovery.run_health_check.assert_called_once()
    
    def test_cli_activate_emergency_command(self):
        """Test CLI emergency activation command"""
        self.mock_emergency_recovery.activate_emergency_mode.return_value = True
        
        success = self.cli.activate_emergency(
            "Test emergency activation", "test_user"
        )
        
        self.assertTrue(success)
        self.mock_emergency_recovery.activate_emergency_mode.assert_called_once_with(
            "Test emergency activation", "test_user"
        )
    
    def test_cli_deactivate_emergency_command(self):
        """Test CLI emergency deactivation command"""
        self.mock_emergency_recovery.deactivate_emergency_mode.return_value = True
        
        success = self.cli.deactivate_emergency("test_user")
        
        self.assertTrue(success)
        self.mock_emergency_recovery.deactivate_emergency_mode.assert_called_once_with(
            "test_user"
        )
    
    def test_cli_send_notification_command(self):
        """Test CLI notification sending command"""
        self.mock_emergency_recovery.send_emergency_notification.return_value = True
        
        success = self.cli.send_notification(
            "Test Alert", "Test message", "high", "admins"
        )
        
        self.assertTrue(success)
        self.mock_emergency_recovery.send_emergency_notification.assert_called_once_with(
            "Test Alert", "Test message", None
        )
    
    def test_cli_auto_recover_command(self):
        """Test CLI auto recovery command"""
        self.mock_emergency_recovery.detect_and_recover.return_value = True
        
        success = self.cli.auto_recover()
        
        self.assertTrue(success)
        self.mock_emergency_recovery.detect_and_recover.assert_called_once()


def run_emergency_recovery_tests():
    """Run all emergency recovery tests"""
    print("Running Emergency Recovery System Tests...")
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_suite.addTest(unittest.makeSuite(TestEmergencyRecoverySystem))
    test_suite.addTest(unittest.makeSuite(TestEmergencyCLI))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print(f"\nTest Results:")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    success = len(result.failures) == 0 and len(result.errors) == 0
    print(f"\nOverall: {'✅ PASSED' if success else '❌ FAILED'}")
    
    return success


if __name__ == '__main__':
    success = run_emergency_recovery_tests()
    sys.exit(0 if success else 1)
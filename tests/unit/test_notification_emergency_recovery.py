# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for Notification Emergency Recovery System

Tests emergency detection, recovery procedures, rollback mechanisms,
and emergency mode activation/deactivation.
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
import json

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.services.notification.components.notification_emergency_recovery import (
    NotificationEmergencyRecovery, EmergencyLevel, FailureType, RecoveryAction,
    EmergencyEvent, RecoveryPlan
)
from app.services.notification.manager.unified_manager import NotificationMessage
from models import NotificationType, NotificationPriority, NotificationCategory


class TestNotificationEmergencyRecovery(unittest.TestCase):
    """Test cases for NotificationEmergencyRecovery"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock dependencies
        self.mock_notification_manager = Mock()
        self.mock_websocket_factory = Mock()
        self.mock_auth_handler = Mock()
        self.mock_namespace_manager = Mock()
        self.mock_db_manager = Mock()
        
        # Create recovery system
        self.recovery = NotificationEmergencyRecovery(
            self.mock_notification_manager,
            self.mock_websocket_factory,
            self.mock_auth_handler,
            self.mock_namespace_manager,
            self.mock_db_manager
        )
    
    def test_initialization(self):
        """Test emergency recovery system initialization"""
        self.assertIsNotNone(self.recovery)
        self.assertFalse(self.recovery._emergency_active)
        self.assertEqual(len(self.recovery._emergency_events), 0)
        self.assertTrue(self.recovery._fallback_enabled)
        self.assertIsInstance(self.recovery._recovery_plans, dict)
    
    def test_classify_failure_websocket(self):
        """Test failure classification for WebSocket errors"""
        error = Exception("WebSocket connection failed")
        context = {"affected_users": 5}
        
        failure_type = self.recovery._classify_failure(error, context)
        self.assertEqual(failure_type, FailureType.WEBSOCKET_CONNECTION_FAILURE)
    
    def test_classify_failure_database(self):
        """Test failure classification for database errors"""
        error = Exception("Database connection timeout")
        context = {"affected_users": 10}
        
        failure_type = self.recovery._classify_failure(error, context)
        self.assertEqual(failure_type, FailureType.DATABASE_PERSISTENCE_FAILURE)
    
    def test_classify_failure_delivery(self):
        """Test failure classification for delivery errors"""
        error = Exception("Message delivery failed")
        context = {"affected_users": 3}
        
        failure_type = self.recovery._classify_failure(error, context)
        self.assertEqual(failure_type, FailureType.MESSAGE_DELIVERY_FAILURE)
    
    def test_assess_emergency_level_critical(self):
        """Test emergency level assessment for critical failures"""
        failure_type = FailureType.SYSTEM_OVERLOAD
        context = {"affected_users": 50}
        
        level = self.recovery._assess_emergency_level(failure_type, context)
        self.assertEqual(level, EmergencyLevel.CRITICAL)
    
    def test_assess_emergency_level_high(self):
        """Test emergency level assessment for high priority failures"""
        failure_type = FailureType.WEBSOCKET_CONNECTION_FAILURE
        context = {"affected_users": 15}
        
        level = self.recovery._assess_emergency_level(failure_type, context)
        self.assertEqual(level, EmergencyLevel.HIGH)
    
    def test_assess_emergency_level_medium(self):
        """Test emergency level assessment for medium priority failures"""
        failure_type = FailureType.MESSAGE_DELIVERY_FAILURE
        context = {"affected_users": 5}
        
        level = self.recovery._assess_emergency_level(failure_type, context)
        self.assertEqual(level, EmergencyLevel.MEDIUM)
    
    def test_create_emergency_event(self):
        """Test emergency event creation"""
        failure_type = FailureType.WEBSOCKET_CONNECTION_FAILURE
        emergency_level = EmergencyLevel.HIGH
        error = Exception("Test error")
        context = {"affected_users": [1, 2, 3]}
        
        event = self.recovery._create_emergency_event(
            failure_type, emergency_level, error, context
        )
        
        self.assertIsInstance(event, EmergencyEvent)
        self.assertEqual(event.failure_type, failure_type)
        self.assertEqual(event.emergency_level, emergency_level)
        self.assertEqual(event.error_message, "Test error")
        self.assertEqual(event.affected_users, [1, 2, 3])
        self.assertIsNotNone(event.timestamp)
        self.assertFalse(event.recovery_success)
    
    def test_detect_and_recover_success(self):
        """Test successful emergency detection and recovery"""
        error = Exception("WebSocket connection failed")
        context = {"affected_users": [1, 2]}
        
        # Mock successful recovery actions
        with patch.object(self.recovery, '_execute_recovery_action', return_value=True):
            success = self.recovery.detect_and_recover(error, context)
        
        self.assertTrue(success)
        self.assertEqual(len(self.recovery._emergency_events), 1)
        self.assertEqual(self.recovery._stats['emergency_events'], 1)
        self.assertEqual(self.recovery._stats['automatic_recoveries'], 1)
    
    def test_detect_and_recover_failure(self):
        """Test failed emergency detection and recovery"""
        error = Exception("Critical system failure")
        context = {"affected_users": [1, 2, 3, 4, 5]}
        
        # Mock failed recovery actions
        with patch.object(self.recovery, '_execute_recovery_action', return_value=False):
            success = self.recovery.detect_and_recover(error, context)
        
        self.assertFalse(success)
        self.assertEqual(len(self.recovery._emergency_events), 1)
        self.assertEqual(self.recovery._stats['emergency_events'], 1)
        self.assertEqual(self.recovery._stats['manual_interventions'], 1)
    
    def test_activate_emergency_mode(self):
        """Test emergency mode activation"""
        reason = "Critical system failure"
        triggered_by = "Administrator"
        
        with patch.object(self.recovery, '_activate_fallback_systems'):
            with patch.object(self.recovery, '_send_emergency_notification'):
                success = self.recovery.activate_emergency_mode(reason, triggered_by)
        
        self.assertTrue(success)
        self.assertTrue(self.recovery._emergency_active)
    
    def test_deactivate_emergency_mode_success(self):
        """Test successful emergency mode deactivation"""
        # First activate emergency mode
        self.recovery._emergency_active = True
        
        resolved_by = "Administrator"
        
        with patch.object(self.recovery, '_restore_normal_operations', return_value=True):
            with patch.object(self.recovery, '_send_emergency_notification'):
                success = self.recovery.deactivate_emergency_mode(resolved_by)
        
        self.assertTrue(success)
        self.assertFalse(self.recovery._emergency_active)
    
    def test_deactivate_emergency_mode_failure(self):
        """Test failed emergency mode deactivation"""
        # First activate emergency mode
        self.recovery._emergency_active = True
        
        resolved_by = "Administrator"
        
        with patch.object(self.recovery, '_restore_normal_operations', return_value=False):
            success = self.recovery.deactivate_emergency_mode(resolved_by)
        
        self.assertFalse(success)
        self.assertTrue(self.recovery._emergency_active)  # Should remain active
    
    def test_send_emergency_notification_websocket_success(self):
        """Test emergency notification via WebSocket"""
        title = "Emergency Alert"
        message = "System experiencing issues"
        
        # Mock successful WebSocket delivery
        self.mock_notification_manager.send_admin_notification.return_value = True
        
        success = self.recovery.send_emergency_notification(title, message, None)
        
        self.assertTrue(success)
        self.mock_notification_manager.send_admin_notification.assert_called_once()
    
    def test_send_emergency_notification_fallback(self):
        """Test emergency notification fallback to flash messages"""
        title = "Emergency Alert"
        message = "System experiencing issues"
        
        # Mock WebSocket failure
        self.mock_notification_manager.send_admin_notification.return_value = False
        
        with patch('notification_emergency_recovery.flash') as mock_flash:
            success = self.recovery.send_emergency_notification(title, message, None)
        
        self.assertTrue(success)
        mock_flash.assert_called_once()
    
    def test_run_health_check(self):
        """Test system health check"""
        # Mock database session
        mock_session = Mock()
        mock_session.execute.return_value = None
        self.mock_db_manager.get_session.return_value.__enter__.return_value = mock_session
        
        # Mock WebSocket factory health check
        self.mock_websocket_factory.health_check.return_value = {'status': 'healthy'}
        
        # Mock notification manager stats
        self.mock_notification_manager.get_notification_stats.return_value = {
            'total_messages': 100,
            'delivered_messages': 95
        }
        
        health_results = self.recovery.run_health_check()
        
        self.assertIsInstance(health_results, dict)
        self.assertIn('timestamp', health_results)
        self.assertIn('overall_status', health_results)
        self.assertIn('components', health_results)
    
    def test_get_emergency_status(self):
        """Test getting emergency system status"""
        # Add some test events
        test_event = EmergencyEvent(
            event_id="test_001",
            timestamp=datetime.now(timezone.utc),
            failure_type=FailureType.WEBSOCKET_CONNECTION_FAILURE,
            emergency_level=EmergencyLevel.HIGH,
            affected_users=[1, 2],
            error_message="Test error",
            stack_trace=None,
            recovery_actions=[RecoveryAction.RESTART_WEBSOCKET],
            recovery_success=True,
            resolution_time=datetime.now(timezone.utc),
            manual_intervention_required=False
        )
        self.recovery._emergency_events.append(test_event)
        
        status = self.recovery.get_emergency_status()
        
        self.assertIsInstance(status, dict)
        self.assertIn('emergency_active', status)
        self.assertIn('health_status', status)
        self.assertIn('fallback_systems', status)
        self.assertIn('statistics', status)
        self.assertIn('recent_events', status)
        self.assertEqual(len(status['recent_events']), 1)
    
    def test_execute_recovery_action_restart_websocket(self):
        """Test WebSocket restart recovery action"""
        event = Mock()
        
        # Mock WebSocket factory restart
        self.mock_websocket_factory.restart.return_value = True
        
        success = self.recovery._execute_recovery_action(RecoveryAction.RESTART_WEBSOCKET, event)
        
        self.assertTrue(success)
        self.mock_websocket_factory.restart.assert_called_once()
    
    def test_execute_recovery_action_fallback_flash(self):
        """Test flash fallback recovery action"""
        event = Mock()
        
        success = self.recovery._execute_recovery_action(RecoveryAction.FALLBACK_TO_FLASH, event)
        
        self.assertTrue(success)
        self.assertTrue(self.recovery._flash_fallback_enabled)
    
    def test_execute_recovery_action_emergency_broadcast(self):
        """Test emergency broadcast recovery action"""
        event = Mock()
        event.emergency_level = EmergencyLevel.HIGH
        
        with patch.object(self.recovery, 'send_emergency_notification', return_value=True):
            success = self.recovery._execute_recovery_action(RecoveryAction.EMERGENCY_BROADCAST, event)
        
        self.assertTrue(success)
    
    def test_recovery_plans_initialization(self):
        """Test recovery plans are properly initialized"""
        plans = self.recovery._recovery_plans
        
        self.assertIn(FailureType.WEBSOCKET_CONNECTION_FAILURE, plans)
        self.assertIn(FailureType.MESSAGE_DELIVERY_FAILURE, plans)
        self.assertIn(FailureType.DATABASE_PERSISTENCE_FAILURE, plans)
        self.assertIn(FailureType.SYSTEM_OVERLOAD, plans)
        
        # Check WebSocket failure plan
        ws_plan = plans[FailureType.WEBSOCKET_CONNECTION_FAILURE]
        self.assertEqual(ws_plan.emergency_level, EmergencyLevel.HIGH)
        self.assertIn(RecoveryAction.RESTART_WEBSOCKET, ws_plan.automatic_actions)
        self.assertIn(RecoveryAction.FALLBACK_TO_FLASH, ws_plan.automatic_actions)
        self.assertTrue(ws_plan.fallback_enabled)
    
    def test_statistics_tracking(self):
        """Test statistics tracking during operations"""
        initial_stats = self.recovery._stats.copy()
        
        # Simulate emergency event
        error = Exception("Test error")
        context = {"affected_users": [1]}
        
        with patch.object(self.recovery, '_execute_recovery_action', return_value=True):
            self.recovery.detect_and_recover(error, context)
        
        # Check statistics updated
        self.assertEqual(self.recovery._stats['emergency_events'], 
                        initial_stats['emergency_events'] + 1)
        self.assertEqual(self.recovery._stats['automatic_recoveries'], 
                        initial_stats['automatic_recoveries'] + 1)
    
    def test_fallback_system_activation(self):
        """Test fallback system activation"""
        self.recovery._activate_fallback_systems()
        
        self.assertTrue(self.recovery._fallback_enabled)
        self.assertTrue(self.recovery._flash_fallback_enabled)
        self.assertTrue(self.recovery._emergency_broadcast_enabled)
    
    def test_normal_operations_restoration(self):
        """Test normal operations restoration"""
        # Mock healthy system
        with patch.object(self.recovery, 'run_health_check') as mock_health:
            mock_health.return_value = {'overall_status': 'healthy'}
            
            success = self.recovery._restore_normal_operations()
        
        self.assertTrue(success)
        self.assertFalse(self.recovery._fallback_enabled)
        self.assertFalse(self.recovery._flash_fallback_enabled)
    
    def test_normal_operations_restoration_unhealthy(self):
        """Test normal operations restoration with unhealthy system"""
        # Mock unhealthy system
        with patch.object(self.recovery, 'run_health_check') as mock_health:
            mock_health.return_value = {'overall_status': 'critical'}
            
            success = self.recovery._restore_normal_operations()
        
        self.assertFalse(success)
    
    def test_emergency_escalation(self):
        """Test emergency escalation"""
        event = EmergencyEvent(
            event_id="test_escalation",
            timestamp=datetime.now(timezone.utc),
            failure_type=FailureType.SYSTEM_OVERLOAD,
            emergency_level=EmergencyLevel.CRITICAL,
            affected_users=[1, 2, 3],
            error_message="Critical system failure",
            stack_trace=None,
            recovery_actions=[],
            recovery_success=False,
            resolution_time=None,
            manual_intervention_required=True
        )
        
        with patch.object(self.recovery, 'send_emergency_notification') as mock_notify:
            self.recovery._escalate_emergency(event)
        
        mock_notify.assert_called_once()
        args = mock_notify.call_args[0]
        self.assertIn("Emergency Escalation Required", args[0])
    
    def test_success_rate_calculation(self):
        """Test recovery success rate calculation"""
        # Add successful event
        successful_event = Mock()
        successful_event.recovery_success = True
        self.recovery._emergency_events.append(successful_event)
        
        # Add failed event
        failed_event = Mock()
        failed_event.recovery_success = False
        self.recovery._emergency_events.append(failed_event)
        
        self.recovery._update_success_rate()
        
        # Should be 50% (1 success out of 2 events)
        self.assertEqual(self.recovery._stats['recovery_success_rate'], 0.5)
    
    def test_configuration_loading(self):
        """Test emergency configuration loading"""
        custom_config = {
            'health_check_interval': 60,
            'max_emergency_events': 200,
            'auto_recovery_enabled': False
        }
        
        recovery = NotificationEmergencyRecovery(
            self.mock_notification_manager,
            self.mock_websocket_factory,
            self.mock_auth_handler,
            self.mock_namespace_manager,
            self.mock_db_manager,
            custom_config
        )
        
        self.assertEqual(recovery.config['health_check_interval'], 60)
        self.assertEqual(recovery.config['max_emergency_events'], 200)
        self.assertFalse(recovery.config['auto_recovery_enabled'])


class TestEmergencyRecoveryIntegration(unittest.TestCase):
    """Integration tests for emergency recovery system"""
    
    def setUp(self):
        """Set up integration test fixtures"""
        # Mock all dependencies for integration testing
        self.mock_notification_manager = Mock()
        self.mock_websocket_factory = Mock()
        self.mock_auth_handler = Mock()
        self.mock_namespace_manager = Mock()
        self.mock_db_manager = Mock()
        
        # Mock database session
        mock_session = Mock()
        self.mock_db_manager.get_session.return_value.__enter__.return_value = mock_session
        
        self.recovery = NotificationEmergencyRecovery(
            self.mock_notification_manager,
            self.mock_websocket_factory,
            self.mock_auth_handler,
            self.mock_namespace_manager,
            self.mock_db_manager
        )
    
    def test_full_emergency_workflow(self):
        """Test complete emergency detection and recovery workflow"""
        # Simulate WebSocket connection failure
        error = Exception("WebSocket connection timeout")
        context = {"affected_users": [1, 2, 3]}
        
        # Mock recovery actions
        self.mock_websocket_factory.restart.return_value = True
        
        with patch('notification_emergency_recovery.flash'):
            success = self.recovery.detect_and_recover(error, context)
        
        # Verify workflow
        self.assertTrue(success)
        self.assertEqual(len(self.recovery._emergency_events), 1)
        
        event = self.recovery._emergency_events[0]
        self.assertEqual(event.failure_type, FailureType.WEBSOCKET_CONNECTION_FAILURE)
        self.assertEqual(event.emergency_level, EmergencyLevel.MEDIUM)
        self.assertTrue(event.recovery_success)
    
    def test_emergency_mode_full_cycle(self):
        """Test full emergency mode activation and deactivation cycle"""
        # Activate emergency mode
        with patch.object(self.recovery, '_send_emergency_notification'):
            activate_success = self.recovery.activate_emergency_mode(
                "System overload detected", "Monitoring System"
            )
        
        self.assertTrue(activate_success)
        self.assertTrue(self.recovery._emergency_active)
        
        # Deactivate emergency mode
        with patch.object(self.recovery, 'run_health_check') as mock_health:
            mock_health.return_value = {'overall_status': 'healthy'}
            with patch.object(self.recovery, '_send_emergency_notification'):
                deactivate_success = self.recovery.deactivate_emergency_mode("Administrator")
        
        self.assertTrue(deactivate_success)
        self.assertFalse(self.recovery._emergency_active)
    
    def test_multiple_failure_handling(self):
        """Test handling multiple concurrent failures"""
        failures = [
            (Exception("WebSocket failed"), {"affected_users": [1, 2]}),
            (Exception("Database timeout"), {"affected_users": [3, 4]}),
            (Exception("Memory overflow"), {"affected_users": [5, 6, 7]})
        ]
        
        # Mock recovery actions
        self.mock_websocket_factory.restart.return_value = True
        
        with patch('notification_emergency_recovery.flash'):
            with patch.object(self.recovery, '_send_emergency_notification'):
                results = []
                for error, context in failures:
                    success = self.recovery.detect_and_recover(error, context)
                    results.append(success)
        
        # All should be handled
        self.assertEqual(len(self.recovery._emergency_events), 3)
        self.assertEqual(self.recovery._stats['emergency_events'], 3)
    
    def test_health_monitoring_integration(self):
        """Test health monitoring integration"""
        # Mock component health checks
        self.mock_websocket_factory.health_check.return_value = {'status': 'healthy'}
        self.mock_notification_manager.get_notification_stats.return_value = {
            'total_messages': 100,
            'delivered_messages': 98
        }
        
        health_results = self.recovery.run_health_check()
        
        self.assertEqual(health_results['overall_status'], 'healthy')
        self.assertIn('websocket_factory', health_results['components'])
        self.assertIn('notification_manager', health_results['components'])
        self.assertIn('database', health_results['components'])


if __name__ == '__main__':
    unittest.main()
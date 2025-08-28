# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test suite for WebSocket Real-Time Notification System

Tests the standardized notification system, delivery confirmation,
priority handling, filtering, and offline persistence functionality.
"""

import unittest
import json
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, MagicMock, patch
from threading import Event

from websocket_notification_system import (
    WebSocketNotificationSystem, StandardizedNotification, NotificationTarget,
    NotificationFilter, NotificationPriority, NotificationType, DeliveryStatus
)
from websocket_notification_delivery import (
    WebSocketNotificationDeliverySystem, NotificationDeliveryTracker,
    NotificationRetryManager, NotificationFallbackManager,
    DeliveryAttemptResult, FallbackMethod
)
from websocket_notification_integration import (
    NotificationIntegrationManager, initialize_notification_integration
)
from models import UserRole


class TestStandardizedNotification(unittest.TestCase):
    """Test StandardizedNotification class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.notification = StandardizedNotification(
            event_name='test_event',
            title='Test Notification',
            message='This is a test notification',
            notification_type=NotificationType.INFO,
            priority=NotificationPriority.NORMAL
        )
    
    def test_notification_creation(self):
        """Test notification creation with default values"""
        self.assertIsNotNone(self.notification.id)
        self.assertEqual(self.notification.event_name, 'test_event')
        self.assertEqual(self.notification.title, 'Test Notification')
        self.assertEqual(self.notification.message, 'This is a test notification')
        self.assertEqual(self.notification.notification_type, NotificationType.INFO)
        self.assertEqual(self.notification.priority, NotificationPriority.NORMAL)
        self.assertEqual(self.notification.delivery_status, DeliveryStatus.PENDING)
        self.assertTrue(self.notification.persist_offline)
    
    def test_notification_serialization(self):
        """Test notification to_dict and from_dict methods"""
        # Add some complex data
        self.notification.target.user_ids = {1, 2, 3}
        self.notification.target.roles = {UserRole.ADMIN, UserRole.REVIEWER}
        self.notification.tags = {'test', 'important'}
        
        # Serialize to dict
        data = self.notification.to_dict()
        
        # Verify serialization
        self.assertIsInstance(data, dict)
        self.assertEqual(data['event_name'], 'test_event')
        self.assertEqual(data['notification_type'], 'info')
        self.assertEqual(data['priority'], 'normal')
        self.assertIsInstance(data['target']['user_ids'], list)
        self.assertIsInstance(data['target']['roles'], list)
        self.assertIsInstance(data['tags'], list)
        
        # Deserialize from dict
        restored_notification = StandardizedNotification.from_dict(data)
        
        # Verify deserialization
        self.assertEqual(restored_notification.id, self.notification.id)
        self.assertEqual(restored_notification.event_name, self.notification.event_name)
        self.assertEqual(restored_notification.notification_type, self.notification.notification_type)
        self.assertEqual(restored_notification.priority, self.notification.priority)
        self.assertEqual(restored_notification.target.user_ids, self.notification.target.user_ids)
        self.assertEqual(restored_notification.target.roles, self.notification.target.roles)
        self.assertEqual(restored_notification.tags, self.notification.tags)
    
    def test_notification_expiration(self):
        """Test notification expiration logic"""
        # Test non-expiring notification
        self.assertFalse(self.notification.is_expired())
        
        # Test expired notification
        self.notification.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        self.assertTrue(self.notification.is_expired())
        
        # Test future expiration
        self.notification.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        self.assertFalse(self.notification.is_expired())
    
    def test_notification_persistence(self):
        """Test notification persistence logic"""
        # Test should persist
        self.assertTrue(self.notification.should_persist())
        
        # Test disabled persistence
        self.notification.persist_offline = False
        self.assertFalse(self.notification.should_persist())
        
        # Test expired persistence duration
        self.notification.persist_offline = True
        self.notification.created_at = datetime.now(timezone.utc) - timedelta(hours=25)
        self.notification.persist_duration_hours = 24
        self.assertFalse(self.notification.should_persist())
    
    def test_client_payload(self):
        """Test client payload generation"""
        payload = self.notification.get_client_payload()
        
        # Verify payload structure
        self.assertIn('id', payload)
        self.assertIn('event_name', payload)
        self.assertIn('title', payload)
        self.assertIn('message', payload)
        self.assertIn('type', payload)
        self.assertIn('priority', payload)
        self.assertIn('created_at', payload)
        
        # Verify no internal tracking data
        self.assertNotIn('delivery_status', payload)
        self.assertNotIn('delivered_to', payload)
        self.assertNotIn('acknowledged_by', payload)


class TestNotificationFilter(unittest.TestCase):
    """Test NotificationFilter class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.notification = StandardizedNotification(
            event_name='test_event',
            title='Test Notification',
            message='Test message',
            notification_type=NotificationType.INFO,
            priority=NotificationPriority.NORMAL,
            source='test_system',
            tags={'test', 'important'}
        )
    
    def test_type_filter(self):
        """Test filtering by notification type"""
        # Filter that matches
        filter_match = NotificationFilter(types={NotificationType.INFO})
        self.assertTrue(filter_match.matches(self.notification))
        
        # Filter that doesn't match
        filter_no_match = NotificationFilter(types={NotificationType.ERROR})
        self.assertFalse(filter_no_match.matches(self.notification))
    
    def test_priority_filter(self):
        """Test filtering by priority"""
        # Filter that matches
        filter_match = NotificationFilter(priorities={NotificationPriority.NORMAL})
        self.assertTrue(filter_match.matches(self.notification))
        
        # Minimum priority filter
        filter_min = NotificationFilter(min_priority=NotificationPriority.LOW)
        self.assertTrue(filter_min.matches(self.notification))
        
        filter_min_high = NotificationFilter(min_priority=NotificationPriority.HIGH)
        self.assertFalse(filter_min_high.matches(self.notification))
    
    def test_source_filter(self):
        """Test filtering by source"""
        # Filter that matches
        filter_match = NotificationFilter(sources={'test_system'})
        self.assertTrue(filter_match.matches(self.notification))
        
        # Filter that doesn't match
        filter_no_match = NotificationFilter(sources={'other_system'})
        self.assertFalse(filter_no_match.matches(self.notification))
    
    def test_tags_filter(self):
        """Test filtering by tags"""
        # Filter that matches (intersection)
        filter_match = NotificationFilter(tags={'test'})
        self.assertTrue(filter_match.matches(self.notification))
        
        # Filter that doesn't match
        filter_no_match = NotificationFilter(tags={'nonexistent'})
        self.assertFalse(filter_no_match.matches(self.notification))
    
    def test_age_filter(self):
        """Test filtering by age"""
        # Recent notification should match
        filter_recent = NotificationFilter(max_age_hours=1)
        self.assertTrue(filter_recent.matches(self.notification))
        
        # Old notification should not match
        self.notification.created_at = datetime.now(timezone.utc) - timedelta(hours=2)
        self.assertFalse(filter_recent.matches(self.notification))


class TestWebSocketNotificationSystem(unittest.TestCase):
    """Test WebSocketNotificationSystem class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_socketio = Mock()
        self.mock_db_manager = Mock()
        self.notification_system = WebSocketNotificationSystem(self.mock_socketio, self.mock_db_manager)
        
        # Mock connection tracker
        self.mock_connection_tracker = Mock()
        self.notification_system.set_connection_tracker(self.mock_connection_tracker)
    
    def test_system_initialization(self):
        """Test notification system initialization"""
        self.assertIsNotNone(self.notification_system.router)
        self.assertIsNotNone(self.notification_system.persistence)
        self.assertEqual(self.notification_system._stats['notifications_sent'], 0)
    
    def test_create_notification(self):
        """Test notification creation"""
        notification = self.notification_system.create_notification(
            event_name='test_event',
            title='Test Title',
            message='Test Message',
            notification_type=NotificationType.INFO,
            priority=NotificationPriority.HIGH
        )
        
        self.assertEqual(notification.event_name, 'test_event')
        self.assertEqual(notification.title, 'Test Title')
        self.assertEqual(notification.message, 'Test Message')
        self.assertEqual(notification.notification_type, NotificationType.INFO)
        self.assertEqual(notification.priority, NotificationPriority.HIGH)
    
    def test_send_notification_validation(self):
        """Test notification validation before sending"""
        # Valid notification
        valid_notification = StandardizedNotification(
            event_name='test_event',
            title='Test Title',
            message='Test Message'
        )
        valid_notification.target.user_ids = {1}
        
        # Mock router to return empty sessions (no online users)
        self.notification_system.router.route_notification = Mock(return_value=[])
        
        result = self.notification_system.send_notification(valid_notification)
        self.assertTrue(result)
        
        # Invalid notification (no event name)
        invalid_notification = StandardizedNotification(
            title='Test Title',
            message='Test Message'
        )
        invalid_notification.target.user_ids = {1}
        
        result = self.notification_system.send_notification(invalid_notification)
        self.assertFalse(result)
    
    def test_broadcast_to_all(self):
        """Test broadcasting to all users"""
        # Mock router
        self.notification_system.router.route_notification = Mock(return_value=['session1', 'session2'])
        
        result = self.notification_system.broadcast_to_all(
            event_name='broadcast_event',
            title='Broadcast Title',
            message='Broadcast Message'
        )
        
        self.assertTrue(result)
        self.assertEqual(self.notification_system._stats['notifications_sent'], 1)
    
    def test_send_to_user(self):
        """Test sending notification to specific user"""
        # Mock router
        self.notification_system.router.route_notification = Mock(return_value=['user_session'])
        
        result = self.notification_system.send_to_user(
            user_id=123,
            event_name='user_event',
            title='User Title',
            message='User Message'
        )
        
        self.assertTrue(result)
        self.assertEqual(self.notification_system._stats['notifications_sent'], 1)
    
    def test_send_to_role(self):
        """Test sending notification to specific role"""
        # Mock router
        self.notification_system.router.route_notification = Mock(return_value=['admin_session'])
        
        result = self.notification_system.send_to_role(
            role=UserRole.ADMIN,
            event_name='admin_event',
            title='Admin Title',
            message='Admin Message'
        )
        
        self.assertTrue(result)
        self.assertEqual(self.notification_system._stats['notifications_sent'], 1)
    
    def test_user_filters(self):
        """Test user notification filters"""
        user_id = 123
        notification_filter = NotificationFilter(
            types={NotificationType.INFO},
            min_priority=NotificationPriority.NORMAL
        )
        
        # Set filter
        self.notification_system.set_user_filter(user_id, notification_filter)
        
        # Get filter
        retrieved_filter = self.notification_system.get_user_filter(user_id)
        self.assertEqual(retrieved_filter, notification_filter)
    
    def test_user_preferences(self):
        """Test user notification preferences"""
        user_id = 123
        preferences = {
            'disabled_types': ['error'],
            'min_priority': 'high',
            'quiet_hours': {'start': '22:00', 'end': '08:00'}
        }
        
        # Set preferences
        self.notification_system.set_user_preferences(user_id, preferences)
        
        # Verify preferences are stored
        self.assertEqual(self.notification_system._user_preferences[user_id], preferences)
    
    def test_statistics(self):
        """Test statistics collection"""
        stats = self.notification_system.get_statistics()
        
        self.assertIn('notifications_sent', stats)
        self.assertIn('notifications_delivered', stats)
        self.assertIn('notifications_acknowledged', stats)
        self.assertIn('notifications_failed', stats)
        self.assertIn('pending_notifications', stats)


class TestNotificationDeliveryTracker(unittest.TestCase):
    """Test NotificationDeliveryTracker class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.tracker = NotificationDeliveryTracker()
        self.notification = StandardizedNotification(
            event_name='test_event',
            title='Test Notification',
            message='Test message',
            requires_acknowledgment=True
        )
    
    def test_delivery_tracking_start(self):
        """Test starting delivery tracking"""
        target_sessions = {'session1', 'session2'}
        
        self.tracker.start_delivery_tracking(self.notification, target_sessions)
        
        # Verify tracking started
        self.assertIn(self.notification.id, self.tracker._delivery_start_times)
        self.assertIn(self.notification.id, self.tracker._pending_confirmations)
        self.assertEqual(
            self.tracker._pending_confirmations[self.notification.id],
            target_sessions
        )
    
    def test_delivery_attempt_recording(self):
        """Test recording delivery attempts"""
        self.tracker.start_delivery_tracking(self.notification, {'session1'})
        
        # Record successful attempt
        self.tracker.record_delivery_attempt(
            self.notification.id, 'session1', DeliveryAttemptResult.SUCCESS
        )
        
        # Verify attempt recorded
        attempts = self.tracker._delivery_attempts[self.notification.id]
        self.assertEqual(len(attempts), 1)
        self.assertEqual(attempts[0].result, DeliveryAttemptResult.SUCCESS)
        self.assertEqual(attempts[0].session_id, 'session1')
        
        # Verify statistics updated
        self.assertEqual(self.tracker._delivery_stats['total_attempts'], 1)
        self.assertEqual(self.tracker._delivery_stats['successful_deliveries'], 1)
    
    def test_delivery_confirmation_recording(self):
        """Test recording delivery confirmations"""
        self.tracker.start_delivery_tracking(self.notification, {'session1'})
        
        # Record confirmation
        success = self.tracker.record_delivery_confirmation(
            self.notification.id, 'session1', 123
        )
        
        self.assertTrue(success)
        
        # Verify confirmation recorded
        confirmations = self.tracker._delivery_confirmations[self.notification.id]
        self.assertEqual(len(confirmations), 1)
        self.assertEqual(confirmations[0].session_id, 'session1')
        self.assertEqual(confirmations[0].user_id, 123)
        
        # Verify pending confirmations updated
        self.assertEqual(len(self.tracker._pending_confirmations[self.notification.id]), 0)
    
    def test_delivery_status(self):
        """Test getting delivery status"""
        self.tracker.start_delivery_tracking(self.notification, {'session1'})
        self.tracker.record_delivery_attempt(
            self.notification.id, 'session1', DeliveryAttemptResult.SUCCESS
        )
        self.tracker.record_delivery_confirmation(
            self.notification.id, 'session1', 123
        )
        
        status = self.tracker.get_delivery_status(self.notification.id)
        
        self.assertEqual(status['notification_id'], self.notification.id)
        self.assertEqual(status['total_attempts'], 1)
        self.assertEqual(status['successful_attempts'], 1)
        self.assertEqual(status['confirmations_received'], 1)
        self.assertTrue(status['is_complete'])


class TestNotificationRetryManager(unittest.TestCase):
    """Test NotificationRetryManager class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_socketio = Mock()
        self.mock_tracker = Mock()
        self.retry_manager = NotificationRetryManager(self.mock_socketio, self.mock_tracker)
        
        self.notification = StandardizedNotification(
            event_name='test_event',
            title='Test Notification',
            message='Test message',
            priority=NotificationPriority.NORMAL
        )
    
    def test_retry_scheduling(self):
        """Test retry scheduling"""
        # Schedule retry
        success = self.retry_manager.schedule_retry(
            self.notification, 'session1', 1, DeliveryAttemptResult.FAILED_TEMPORARY
        )
        
        self.assertTrue(success)
        self.assertGreater(self.retry_manager._retry_queue.qsize(), 0)
    
    def test_retry_policy_limits(self):
        """Test retry policy limits"""
        # Test max attempts exceeded
        success = self.retry_manager.schedule_retry(
            self.notification, 'session1', 10, DeliveryAttemptResult.FAILED_TEMPORARY
        )
        
        self.assertFalse(success)
    
    def test_retry_policy_by_priority(self):
        """Test retry policies vary by priority"""
        # Critical priority should have more retries
        critical_notification = StandardizedNotification(
            event_name='critical_event',
            title='Critical Notification',
            message='Critical message',
            priority=NotificationPriority.CRITICAL
        )
        
        # Should allow more retries for critical notifications
        success = self.retry_manager.schedule_retry(
            critical_notification, 'session1', 3, DeliveryAttemptResult.FAILED_TEMPORARY
        )
        
        self.assertTrue(success)  # Critical allows up to 5 attempts
        
        # Low priority should have fewer retries
        low_notification = StandardizedNotification(
            event_name='low_event',
            title='Low Notification',
            message='Low message',
            priority=NotificationPriority.LOW
        )
        
        success = self.retry_manager.schedule_retry(
            low_notification, 'session1', 1, DeliveryAttemptResult.FAILED_TEMPORARY
        )
        
        self.assertFalse(success)  # Low priority allows only 1 attempt


class TestNotificationFallbackManager(unittest.TestCase):
    """Test NotificationFallbackManager class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.fallback_manager = NotificationFallbackManager()
        self.notification = StandardizedNotification(
            event_name='test_event',
            title='Test Notification',
            message='Test message',
            priority=NotificationPriority.HIGH
        )
    
    def test_fallback_handler_registration(self):
        """Test registering fallback handlers"""
        mock_handler = Mock(return_value=True)
        
        self.fallback_manager.register_fallback_handler(FallbackMethod.EMAIL, mock_handler)
        
        self.assertIn(FallbackMethod.EMAIL, self.fallback_manager._fallback_handlers)
        self.assertEqual(self.fallback_manager._fallback_handlers[FallbackMethod.EMAIL], mock_handler)
    
    def test_fallback_trigger(self):
        """Test triggering fallback delivery"""
        # Register mock handler
        mock_handler = Mock(return_value=True)
        self.fallback_manager.register_fallback_handler(FallbackMethod.EMAIL, mock_handler)
        
        # Trigger fallback
        failed_user_ids = {123, 456}
        success = self.fallback_manager.trigger_fallback(
            self.notification, failed_user_ids, "WebSocket delivery failed"
        )
        
        self.assertTrue(success)
        mock_handler.assert_called_once_with(
            self.notification, failed_user_ids, "WebSocket delivery failed"
        )
    
    def test_fallback_policy_by_priority(self):
        """Test fallback policies vary by priority"""
        # Critical notifications should have more fallback methods
        critical_notification = StandardizedNotification(
            event_name='critical_event',
            title='Critical Notification',
            message='Critical message',
            priority=NotificationPriority.CRITICAL
        )
        
        critical_methods = self.fallback_manager._fallback_policies[NotificationPriority.CRITICAL]
        normal_methods = self.fallback_manager._fallback_policies[NotificationPriority.NORMAL]
        
        self.assertGreater(len(critical_methods), len(normal_methods))
        self.assertIn(FallbackMethod.EMAIL, critical_methods)
        self.assertIn(FallbackMethod.SMS, critical_methods)


class TestNotificationIntegration(unittest.TestCase):
    """Test NotificationIntegrationManager class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_socketio = Mock()
        self.mock_db_manager = Mock()
        self.integration_manager = NotificationIntegrationManager(self.mock_socketio, self.mock_db_manager)
    
    def test_integration_initialization(self):
        """Test integration manager initialization"""
        self.assertIsNotNone(self.integration_manager.notification_system)
        self.assertIsNotNone(self.integration_manager.delivery_system)
        self.assertIn('progress_update', self.integration_manager._event_mappings)
    
    def test_progress_notification(self):
        """Test sending progress notifications"""
        # Mock the notification system
        self.integration_manager.notification_system.send_notification = Mock(return_value=True)
        
        success = self.integration_manager.send_progress_notification(
            task_id='task123',
            user_id=456,
            progress_data={'progress': 50, 'status': 'running'}
        )
        
        self.assertTrue(success)
        self.integration_manager.notification_system.send_notification.assert_called_once()
    
    def test_system_alert(self):
        """Test sending system alerts"""
        # Mock the notification system
        self.integration_manager.notification_system.send_notification = Mock(return_value=True)
        
        success = self.integration_manager.send_system_alert(
            title='System Alert',
            message='System maintenance required',
            priority=NotificationPriority.URGENT
        )
        
        self.assertTrue(success)
        self.integration_manager.notification_system.send_notification.assert_called_once()
    
    def test_admin_notification(self):
        """Test sending admin notifications"""
        # Mock the notification system
        self.integration_manager.notification_system.send_notification = Mock(return_value=True)
        
        success = self.integration_manager.send_admin_notification(
            title='Admin Alert',
            message='Admin action required'
        )
        
        self.assertTrue(success)
        self.integration_manager.notification_system.send_notification.assert_called_once()
    
    def test_security_alert(self):
        """Test sending security alerts"""
        # Mock the notification system
        self.integration_manager.notification_system.send_notification = Mock(return_value=True)
        
        success = self.integration_manager.send_security_alert(
            title='Security Alert',
            message='Suspicious activity detected',
            severity='high'
        )
        
        self.assertTrue(success)
        self.integration_manager.notification_system.send_notification.assert_called_once()
    
    def test_user_notification_preferences(self):
        """Test user notification preferences"""
        user_id = 123
        preferences = {
            'filter': {
                'types': ['info', 'warning'],
                'min_priority': 'normal'
            },
            'preferences': {
                'disabled_types': ['error'],
                'quiet_hours': {'start': '22:00', 'end': '08:00'}
            }
        }
        
        # Set preferences
        success = self.integration_manager.set_user_notification_preferences(user_id, preferences)
        self.assertTrue(success)
        
        # Get preferences
        retrieved_prefs = self.integration_manager.get_user_notification_preferences(user_id)
        self.assertIsNotNone(retrieved_prefs)
    
    def test_offline_notifications(self):
        """Test getting offline notifications"""
        user_id = 123
        
        # Mock the notification system
        self.integration_manager.notification_system.get_offline_notifications = Mock(return_value=[])
        
        notifications = self.integration_manager.get_offline_notifications(user_id)
        
        self.assertIsInstance(notifications, list)
        self.integration_manager.notification_system.get_offline_notifications.assert_called_once()
    
    def test_system_statistics(self):
        """Test getting system statistics"""
        # Mock the systems
        self.integration_manager.notification_system.get_statistics = Mock(return_value={})
        self.integration_manager.delivery_system.get_system_statistics = Mock(return_value={})
        
        stats = self.integration_manager.get_system_statistics()
        
        self.assertIn('notification_system', stats)
        self.assertIn('delivery_system', stats)
        self.assertIn('integration_status', stats)


class TestNotificationSystemIntegration(unittest.TestCase):
    """Integration tests for the complete notification system"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_socketio = Mock()
        self.mock_db_manager = Mock()
        
        # Initialize complete system
        self.integration_manager = initialize_notification_integration(
            self.mock_socketio, self.mock_db_manager
        )
    
    def test_end_to_end_notification_flow(self):
        """Test complete notification flow from creation to delivery"""
        # Mock connection tracker
        mock_connection_tracker = Mock()
        mock_connection_tracker.get_user_sessions.return_value = ['session123']
        mock_connection_tracker.get_namespace_sessions.return_value = ['session123']
        
        self.integration_manager.set_namespace_manager(mock_connection_tracker)
        
        # Send notification
        success = self.integration_manager.send_user_notification(
            user_id=123,
            title='Test Notification',
            message='This is a test notification',
            notification_type=NotificationType.INFO,
            priority=NotificationPriority.NORMAL
        )
        
        self.assertTrue(success)
        
        # Verify statistics updated
        stats = self.integration_manager.get_system_statistics()
        self.assertGreater(stats['notification_system']['notifications_sent'], 0)
    
    def test_notification_with_acknowledgment(self):
        """Test notification requiring acknowledgment"""
        # Mock connection tracker
        mock_connection_tracker = Mock()
        mock_connection_tracker.get_user_sessions.return_value = ['session123']
        
        self.integration_manager.set_namespace_manager(mock_connection_tracker)
        
        # Send high-priority notification (requires acknowledgment)
        success = self.integration_manager.send_user_notification(
            user_id=123,
            title='Important Notification',
            message='This requires acknowledgment',
            notification_type=NotificationType.WARNING,
            priority=NotificationPriority.HIGH
        )
        
        self.assertTrue(success)
    
    def test_notification_filtering(self):
        """Test notification filtering by user preferences"""
        user_id = 123
        
        # Set user filter to only allow high priority notifications
        preferences = {
            'filter': {
                'min_priority': 'high'
            }
        }
        
        self.integration_manager.set_user_notification_preferences(user_id, preferences)
        
        # Mock connection tracker
        mock_connection_tracker = Mock()
        mock_connection_tracker.get_user_sessions.return_value = ['session123']
        
        self.integration_manager.set_namespace_manager(mock_connection_tracker)
        
        # Send low priority notification (should be filtered)
        success = self.integration_manager.send_user_notification(
            user_id=user_id,
            title='Low Priority',
            message='This should be filtered',
            priority=NotificationPriority.LOW
        )
        
        # Should still succeed (notification sent to system, filtering happens at delivery)
        self.assertTrue(success)
    
    def test_system_cleanup(self):
        """Test system cleanup functionality"""
        # Add some test data
        self.integration_manager.send_user_notification(
            user_id=123,
            title='Test Notification',
            message='Test message'
        )
        
        # Run cleanup
        cleanup_results = self.integration_manager.cleanup_old_notifications(max_age_hours=0)
        
        self.assertIsInstance(cleanup_results, dict)
        self.assertIn('notifications_cleaned', cleanup_results)
    
    def tearDown(self):
        """Clean up after tests"""
        self.integration_manager.shutdown()


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)
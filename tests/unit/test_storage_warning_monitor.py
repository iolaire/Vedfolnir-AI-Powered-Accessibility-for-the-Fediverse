# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for Storage Warning Monitor.

Tests the 80% warning threshold detection, admin dashboard notifications,
background periodic monitoring, and comprehensive logging functionality.
"""

import unittest
import json
import time
import threading
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.services.storage.components.storage_warning_monitor import (
    StorageWarningMonitor, StorageEvent, WarningNotification, 
    StorageEventType
)
from app.services.storage.components.storage_configuration_service import StorageConfigurationService
from app.services.storage.components.storage_monitor_service import StorageMonitorService, StorageMetrics


class TestStorageWarningMonitor(unittest.TestCase):
    """Test cases for Storage Warning Monitor"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock Redis client
        self.mock_redis = Mock()
        self.mock_redis.ping.return_value = True
        self.mock_redis.get.return_value = None
        self.mock_redis.set.return_value = True
        self.mock_redis.setex.return_value = True
        self.mock_redis.delete.return_value = True
        self.mock_redis.keys.return_value = []
        self.mock_redis.ttl.return_value = 3600
        
        # Mock configuration service
        self.mock_config = Mock(spec=StorageConfigurationService)
        self.mock_config.get_max_storage_gb.return_value = 10.0
        self.mock_config.get_warning_threshold_gb.return_value = 8.0
        self.mock_config.validate_storage_config.return_value = True
        self.mock_config._config = Mock()
        self.mock_config._config.warning_threshold_percentage = 80.0
        
        # Mock monitor service
        self.mock_monitor = Mock(spec=StorageMonitorService)
        
        # Mock notification callback
        self.notification_callback = Mock()
        
        # Create test metrics
        self.normal_metrics = StorageMetrics(
            total_bytes=5 * 1024**3,  # 5GB
            total_gb=5.0,
            limit_gb=10.0,
            usage_percentage=50.0,
            is_limit_exceeded=False,
            is_warning_exceeded=False,
            last_calculated=datetime.now()
        )
        
        self.warning_metrics = StorageMetrics(
            total_bytes=8.5 * 1024**3,  # 8.5GB
            total_gb=8.5,
            limit_gb=10.0,
            usage_percentage=85.0,
            is_limit_exceeded=False,
            is_warning_exceeded=True,
            last_calculated=datetime.now()
        )
        
        self.limit_exceeded_metrics = StorageMetrics(
            total_bytes=10.5 * 1024**3,  # 10.5GB
            total_gb=10.5,
            limit_gb=10.0,
            usage_percentage=105.0,
            is_limit_exceeded=True,
            is_warning_exceeded=True,
            last_calculated=datetime.now()
        )
        
        self.mock_monitor.get_storage_metrics.return_value = self.normal_metrics
    
    def create_monitor(self, **kwargs):
        """Create a StorageWarningMonitor instance with mocked dependencies"""
        defaults = {
            'config_service': self.mock_config,
            'monitor_service': self.mock_monitor,
            'redis_client': self.mock_redis,
            'notification_callback': self.notification_callback
        }
        defaults.update(kwargs)
        return StorageWarningMonitor(**defaults)
    
    def test_initialization(self):
        """Test storage warning monitor initialization"""
        monitor = self.create_monitor()
        
        # Verify initialization
        self.assertIsNotNone(monitor)
        self.assertEqual(monitor.config_service, self.mock_config)
        self.assertEqual(monitor.monitor_service, self.mock_monitor)
        self.assertEqual(monitor.redis_client, self.mock_redis)
        self.assertEqual(monitor.notification_callback, self.notification_callback)
        
        # Verify default configuration
        self.assertEqual(monitor.check_interval_seconds, 300)  # 5 minutes
        self.assertEqual(monitor.event_retention_hours, 168)   # 7 days
        self.assertEqual(monitor.notification_retention_hours, 72)  # 3 days
        
        # Verify Redis ping was called
        self.mock_redis.ping.assert_called_once()
    
    def test_redis_connection_failure(self):
        """Test handling of Redis connection failure"""
        self.mock_redis.ping.side_effect = Exception("Redis connection failed")
        
        with self.assertRaises(Exception):
            self.create_monitor()
    
    def test_warning_threshold_detection_normal(self):
        """Test warning threshold detection with normal usage"""
        monitor = self.create_monitor()
        
        # Test with normal metrics (50% usage)
        self.mock_monitor.get_storage_metrics.return_value = self.normal_metrics
        
        result = monitor.check_warning_threshold()
        
        # Should return False (no warning)
        self.assertFalse(result)
        
        # Verify metrics were retrieved (may be called multiple times for logging)
        self.assertTrue(self.mock_monitor.get_storage_metrics.called)
        
        # Verify event was logged (periodic check)
        self.mock_redis.setex.assert_called()
    
    def test_warning_threshold_detection_exceeded(self):
        """Test warning threshold detection when threshold is exceeded"""
        monitor = self.create_monitor()
        
        # Test with warning metrics (85% usage)
        self.mock_monitor.get_storage_metrics.return_value = self.warning_metrics
        
        result = monitor.check_warning_threshold()
        
        # Should return True (warning exceeded)
        self.assertTrue(result)
        
        # Verify warning event was logged
        self.mock_redis.setex.assert_called()
        
        # Verify notification callback was called
        self.notification_callback.assert_called_once()
        
        # Verify notification was created with correct severity
        call_args = self.notification_callback.call_args[0]
        notification = call_args[0]
        self.assertEqual(notification.severity, 'warning')
        self.assertIn('WARNING', notification.message)
    
    def test_limit_exceeded_detection(self):
        """Test detection when storage limit is exceeded"""
        monitor = self.create_monitor()
        
        # Test with limit exceeded metrics (105% usage)
        self.mock_monitor.get_storage_metrics.return_value = self.limit_exceeded_metrics
        
        result = monitor.check_warning_threshold()
        
        # Should return True (warning exceeded)
        self.assertTrue(result)
        
        # Verify notifications were created (both warning and critical)
        self.assertTrue(self.notification_callback.called)
        self.assertGreaterEqual(self.notification_callback.call_count, 1)
        
        # Check that at least one critical notification was created
        call_args_list = self.notification_callback.call_args_list
        critical_notifications = [call for call in call_args_list 
                                if call[0][0].severity == 'critical']
        self.assertGreater(len(critical_notifications), 0)
        
        # Verify critical notification content
        critical_notification = critical_notifications[0][0][0]
        self.assertEqual(critical_notification.severity, 'critical')
        self.assertIn('CRITICAL', critical_notification.message)
    
    def test_state_change_detection(self):
        """Test detection of state changes for proper event logging"""
        monitor = self.create_monitor()
        
        # First check with normal usage
        self.mock_monitor.get_storage_metrics.return_value = self.normal_metrics
        monitor.check_warning_threshold()
        
        # Reset mock calls
        self.mock_redis.setex.reset_mock()
        self.notification_callback.reset_mock()
        
        # Second check with warning exceeded
        self.mock_monitor.get_storage_metrics.return_value = self.warning_metrics
        monitor.check_warning_threshold()
        
        # Should have logged warning threshold exceeded event
        self.mock_redis.setex.assert_called()
        self.notification_callback.assert_called_once()
        
        # Reset mock calls
        self.mock_redis.setex.reset_mock()
        self.notification_callback.reset_mock()
        
        # Third check back to normal
        self.mock_monitor.get_storage_metrics.return_value = self.normal_metrics
        monitor.check_warning_threshold()
        
        # Should have logged warning threshold cleared event
        self.mock_redis.setex.assert_called()
        # No new notification should be created for clearing
        self.notification_callback.assert_not_called()
    
    def test_monitoring_error_handling(self):
        """Test handling of monitoring errors"""
        monitor = self.create_monitor()
        
        # Mock monitor service to raise exception
        self.mock_monitor.get_storage_metrics.side_effect = Exception("Monitor error")
        
        result = monitor.check_warning_threshold()
        
        # Should return False on error
        self.assertFalse(result)
        
        # Should have logged error event
        self.mock_redis.setex.assert_called()
    
    def test_create_warning_notification(self):
        """Test creation of warning notifications"""
        monitor = self.create_monitor()
        
        # Create warning notification
        monitor._create_warning_notification(self.warning_metrics, 'warning')
        
        # Verify notification was stored in Redis
        self.mock_redis.setex.assert_called()
        
        # Verify callback was called
        self.notification_callback.assert_called_once()
        
        # Verify notification content
        call_args = self.notification_callback.call_args[0]
        notification = call_args[0]
        self.assertEqual(notification.severity, 'warning')
        self.assertEqual(notification.storage_gb, 8.5)
        self.assertEqual(notification.limit_gb, 10.0)
        self.assertEqual(notification.usage_percentage, 85.0)
        self.assertFalse(notification.acknowledged)
    
    def test_create_critical_notification(self):
        """Test creation of critical notifications"""
        monitor = self.create_monitor()
        
        # Create critical notification
        monitor._create_warning_notification(self.limit_exceeded_metrics, 'critical')
        
        # Verify notification was stored in Redis
        self.mock_redis.setex.assert_called()
        
        # Verify callback was called
        self.notification_callback.assert_called_once()
        
        # Verify notification content
        call_args = self.notification_callback.call_args[0]
        notification = call_args[0]
        self.assertEqual(notification.severity, 'critical')
        self.assertIn('CRITICAL', notification.message)
        self.assertIn('blocked', notification.message.lower())
    
    def test_get_active_notifications(self):
        """Test retrieval of active notifications"""
        monitor = self.create_monitor()
        
        # Mock Redis to return notification keys and data
        notification_data = {
            'id': 'test_notification_1',
            'created_at': datetime.now(timezone.utc).isoformat(),
            'storage_gb': 8.5,
            'limit_gb': 10.0,
            'warning_threshold_gb': 8.0,
            'usage_percentage': 85.0,
            'message': 'Test warning message',
            'severity': 'warning',
            'acknowledged': False,
            'acknowledged_at': None,
            'acknowledged_by': None
        }
        
        self.mock_redis.keys.return_value = ['vedfolnir:storage:warning_notifications:test_notification_1']
        self.mock_redis.get.return_value = json.dumps(notification_data)
        
        notifications = monitor.get_active_notifications()
        
        # Verify notification was retrieved
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0].id, 'test_notification_1')
        self.assertEqual(notifications[0].severity, 'warning')
        self.assertFalse(notifications[0].acknowledged)
    
    def test_acknowledge_notification(self):
        """Test acknowledgment of notifications"""
        monitor = self.create_monitor()
        
        # Mock existing notification
        notification_data = {
            'id': 'test_notification_1',
            'created_at': datetime.now(timezone.utc).isoformat(),
            'storage_gb': 8.5,
            'limit_gb': 10.0,
            'warning_threshold_gb': 8.0,
            'usage_percentage': 85.0,
            'message': 'Test warning message',
            'severity': 'warning',
            'acknowledged': False,
            'acknowledged_at': None,
            'acknowledged_by': None
        }
        
        self.mock_redis.get.return_value = json.dumps(notification_data)
        self.mock_redis.ttl.return_value = 3600
        
        result = monitor.acknowledge_notification('test_notification_1', 'admin_user')
        
        # Verify acknowledgment was successful
        self.assertTrue(result)
        
        # Verify Redis was updated
        self.mock_redis.setex.assert_called()
        
        # Verify acknowledgment data was set
        call_args = self.mock_redis.setex.call_args[0]
        updated_data = json.loads(call_args[2])
        self.assertTrue(updated_data['acknowledged'])
        self.assertEqual(updated_data['acknowledged_by'], 'admin_user')
        self.assertIsNotNone(updated_data['acknowledged_at'])
    
    def test_acknowledge_nonexistent_notification(self):
        """Test acknowledgment of non-existent notification"""
        monitor = self.create_monitor()
        
        # Mock Redis to return None (notification not found)
        self.mock_redis.get.return_value = None
        
        result = monitor.acknowledge_notification('nonexistent_id', 'admin_user')
        
        # Should return False
        self.assertFalse(result)
    
    def test_background_monitoring_start_stop(self):
        """Test starting and stopping background monitoring"""
        monitor = self.create_monitor()
        
        # Start background monitoring
        result = monitor.start_background_monitoring()
        self.assertTrue(result)
        self.assertTrue(monitor._monitoring_active)
        self.assertIsNotNone(monitor._monitoring_thread)
        
        # Try to start again (should fail)
        result = monitor.start_background_monitoring()
        self.assertFalse(result)
        
        # Stop background monitoring
        result = monitor.stop_background_monitoring()
        self.assertTrue(result)
        self.assertFalse(monitor._monitoring_active)
        
        # Try to stop again (should fail)
        result = monitor.stop_background_monitoring()
        self.assertFalse(result)
    
    def test_background_monitoring_loop(self):
        """Test background monitoring loop functionality"""
        monitor = self.create_monitor()
        
        # Set short check interval for testing
        monitor.check_interval_seconds = 0.1
        
        # Start monitoring
        monitor.start_background_monitoring()
        
        # Wait for a few checks
        time.sleep(0.3)
        
        # Stop monitoring
        monitor.stop_background_monitoring()
        
        # Verify metrics were checked multiple times
        self.assertGreater(self.mock_monitor.get_storage_metrics.call_count, 1)
    
    def test_get_storage_events(self):
        """Test retrieval of storage events"""
        monitor = self.create_monitor()
        
        # Mock Redis to return event keys and data
        event_data = {
            'event_type': 'warning_threshold_exceeded',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'storage_gb': 8.5,
            'limit_gb': 10.0,
            'warning_threshold_gb': 8.0,
            'usage_percentage': 85.0,
            'is_warning_exceeded': True,
            'is_limit_exceeded': False,
            'message': 'Test warning event',
            'additional_data': None
        }
        
        self.mock_redis.keys.return_value = ['vedfolnir:storage:events:2025-01-01T12:00:00']
        self.mock_redis.get.return_value = json.dumps(event_data)
        
        events = monitor.get_storage_events(limit=10)
        
        # Verify event was retrieved
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, StorageEventType.WARNING_THRESHOLD_EXCEEDED)
        self.assertEqual(events[0].storage_gb, 8.5)
        self.assertEqual(events[0].message, 'Test warning event')
    
    def test_get_storage_events_with_filter(self):
        """Test retrieval of storage events with type filter"""
        monitor = self.create_monitor()
        
        # Mock multiple events
        warning_event = {
            'event_type': 'warning_threshold_exceeded',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'storage_gb': 8.5,
            'limit_gb': 10.0,
            'warning_threshold_gb': 8.0,
            'usage_percentage': 85.0,
            'is_warning_exceeded': True,
            'is_limit_exceeded': False,
            'message': 'Warning event',
            'additional_data': None
        }
        
        periodic_event = {
            'event_type': 'periodic_check',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'storage_gb': 5.0,
            'limit_gb': 10.0,
            'warning_threshold_gb': 8.0,
            'usage_percentage': 50.0,
            'is_warning_exceeded': False,
            'is_limit_exceeded': False,
            'message': 'Periodic check',
            'additional_data': None
        }
        
        self.mock_redis.keys.return_value = [
            'vedfolnir:storage:events:2025-01-01T12:00:00',
            'vedfolnir:storage:events:2025-01-01T12:05:00'
        ]
        
        # Mock Redis to return different data for different keys
        def mock_get(key):
            if '12:00:00' in key:
                return json.dumps(warning_event)
            else:
                return json.dumps(periodic_event)
        
        self.mock_redis.get.side_effect = mock_get
        
        # Get all events
        all_events = monitor.get_storage_events(limit=10)
        self.assertEqual(len(all_events), 2)
        
        # Get only warning events
        warning_events = monitor.get_storage_events(
            limit=10, 
            event_type_filter=StorageEventType.WARNING_THRESHOLD_EXCEEDED
        )
        self.assertEqual(len(warning_events), 1)
        self.assertEqual(warning_events[0].event_type, StorageEventType.WARNING_THRESHOLD_EXCEEDED)
    
    def test_get_monitoring_status(self):
        """Test retrieval of monitoring status"""
        monitor = self.create_monitor()
        
        # Mock active notifications
        self.mock_redis.keys.return_value = ['vedfolnir:storage:warning_notifications:test1']
        notification_data = {
            'id': 'test1',
            'created_at': datetime.now(timezone.utc).isoformat(),
            'storage_gb': 8.5,
            'limit_gb': 10.0,
            'warning_threshold_gb': 8.0,
            'usage_percentage': 85.0,
            'message': 'Test notification',
            'severity': 'warning',
            'acknowledged': False,
            'acknowledged_at': None,
            'acknowledged_by': None
        }
        self.mock_redis.get.return_value = json.dumps(notification_data)
        
        status = monitor.get_monitoring_status()
        
        # Verify status information
        self.assertIn('monitoring_active', status)
        self.assertIn('check_interval_seconds', status)
        self.assertIn('current_storage_gb', status)
        self.assertIn('storage_limit_gb', status)
        self.assertIn('warning_threshold_gb', status)
        self.assertIn('usage_percentage', status)
        self.assertIn('is_warning_exceeded', status)
        self.assertIn('is_limit_exceeded', status)
        self.assertIn('active_notifications_count', status)
        self.assertIn('unacknowledged_notifications_count', status)
        
        # Verify values
        self.assertEqual(status['current_storage_gb'], 5.0)
        self.assertEqual(status['storage_limit_gb'], 10.0)
        self.assertEqual(status['warning_threshold_gb'], 8.0)
        self.assertEqual(status['active_notifications_count'], 1)
        self.assertEqual(status['unacknowledged_notifications_count'], 1)
    
    def test_update_monitoring_config(self):
        """Test updating monitoring configuration"""
        monitor = self.create_monitor()
        
        # Update configuration
        result = monitor.update_monitoring_config(
            check_interval_seconds=600,
            event_retention_hours=240,
            notification_retention_hours=96
        )
        
        self.assertTrue(result)
        self.assertEqual(monitor.check_interval_seconds, 600)
        self.assertEqual(monitor.event_retention_hours, 240)
        self.assertEqual(monitor.notification_retention_hours, 96)
        
        # Verify configuration was saved to Redis
        self.mock_redis.set.assert_called()
    
    def test_update_monitoring_config_invalid(self):
        """Test updating monitoring configuration with invalid values"""
        monitor = self.create_monitor()
        
        # Try to update with invalid values
        result = monitor.update_monitoring_config(
            check_interval_seconds=-1,
            event_retention_hours=0
        )
        
        self.assertFalse(result)
        # Configuration should remain unchanged
        self.assertEqual(monitor.check_interval_seconds, 300)
        self.assertEqual(monitor.event_retention_hours, 168)
    
    def test_health_check(self):
        """Test health check functionality"""
        monitor = self.create_monitor()
        
        health = monitor.health_check()
        
        # Verify health check components
        self.assertIn('redis_connected', health)
        self.assertIn('config_service_healthy', health)
        self.assertIn('monitor_service_healthy', health)
        self.assertIn('background_monitoring_active', health)
        self.assertIn('overall_healthy', health)
        
        # All should be healthy with mocked services
        self.assertTrue(health['redis_connected'])
        self.assertTrue(health['config_service_healthy'])
        self.assertTrue(health['monitor_service_healthy'])
        self.assertTrue(health['overall_healthy'])
    
    def test_health_check_with_failures(self):
        """Test health check with service failures"""
        monitor = self.create_monitor()
        
        # Mock Redis failure
        self.mock_redis.ping.side_effect = Exception("Redis down")
        
        # Mock config service failure
        self.mock_config.validate_storage_config.side_effect = Exception("Config error")
        
        health = monitor.health_check()
        
        # Should detect failures
        self.assertFalse(health['redis_connected'])
        self.assertFalse(health['config_service_healthy'])
        self.assertFalse(health['overall_healthy'])
        self.assertIn('redis_error', health)
        self.assertIn('config_error', health)
    
    def test_notification_callback_failure(self):
        """Test handling of notification callback failures"""
        monitor = self.create_monitor()
        
        # Mock callback to raise exception
        self.notification_callback.side_effect = Exception("Callback failed")
        
        # Test with warning metrics
        self.mock_monitor.get_storage_metrics.return_value = self.warning_metrics
        
        # Should not raise exception despite callback failure
        result = monitor.check_warning_threshold()
        self.assertTrue(result)
        
        # Should have logged notification failure event
        self.mock_redis.setex.assert_called()
    
    def test_cleanup_old_data(self):
        """Test cleanup of old events and notifications"""
        monitor = self.create_monitor()
        
        # Mock old event and notification keys
        old_timestamp = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
        recent_timestamp = datetime.now(timezone.utc).isoformat()
        
        self.mock_redis.keys.side_effect = [
            [f'vedfolnir:storage:events:{old_timestamp}', f'vedfolnir:storage:events:{recent_timestamp}'],
            [f'vedfolnir:storage:warning_notifications:old', f'vedfolnir:storage:warning_notifications:recent']
        ]
        
        # Mock notification data
        old_notification = {
            'created_at': (datetime.now(timezone.utc) - timedelta(days=4)).isoformat()
        }
        recent_notification = {
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        def mock_get(key):
            if 'old' in key:
                return json.dumps(old_notification)
            else:
                return json.dumps(recent_notification)
        
        self.mock_redis.get.side_effect = mock_get
        
        # Run cleanup
        monitor._cleanup_old_data()
        
        # Verify delete was called for old items
        self.mock_redis.delete.assert_called()


class TestStorageEvent(unittest.TestCase):
    """Test cases for StorageEvent data structure"""
    
    def test_storage_event_creation(self):
        """Test creation of storage event"""
        event = StorageEvent(
            event_type=StorageEventType.WARNING_THRESHOLD_EXCEEDED,
            timestamp=datetime.now(timezone.utc),
            storage_gb=8.5,
            limit_gb=10.0,
            warning_threshold_gb=8.0,
            usage_percentage=85.0,
            is_warning_exceeded=True,
            is_limit_exceeded=False,
            message="Test warning event"
        )
        
        self.assertEqual(event.event_type, StorageEventType.WARNING_THRESHOLD_EXCEEDED)
        self.assertEqual(event.storage_gb, 8.5)
        self.assertEqual(event.message, "Test warning event")
        self.assertTrue(event.is_warning_exceeded)
        self.assertFalse(event.is_limit_exceeded)
    
    def test_storage_event_serialization(self):
        """Test serialization and deserialization of storage event"""
        original_event = StorageEvent(
            event_type=StorageEventType.LIMIT_EXCEEDED,
            timestamp=datetime.now(timezone.utc),
            storage_gb=10.5,
            limit_gb=10.0,
            warning_threshold_gb=8.0,
            usage_percentage=105.0,
            is_warning_exceeded=True,
            is_limit_exceeded=True,
            message="Test limit event",
            additional_data={'test_key': 'test_value'}
        )
        
        # Serialize to dict
        event_dict = original_event.to_dict()
        
        # Verify dict structure
        self.assertEqual(event_dict['event_type'], 'limit_exceeded')
        self.assertEqual(event_dict['storage_gb'], 10.5)
        self.assertEqual(event_dict['message'], 'Test limit event')
        self.assertEqual(event_dict['additional_data']['test_key'], 'test_value')
        
        # Deserialize from dict
        restored_event = StorageEvent.from_dict(event_dict)
        
        # Verify restored event
        self.assertEqual(restored_event.event_type, StorageEventType.LIMIT_EXCEEDED)
        self.assertEqual(restored_event.storage_gb, 10.5)
        self.assertEqual(restored_event.message, 'Test limit event')
        self.assertEqual(restored_event.additional_data['test_key'], 'test_value')


class TestWarningNotification(unittest.TestCase):
    """Test cases for WarningNotification data structure"""
    
    def test_warning_notification_creation(self):
        """Test creation of warning notification"""
        notification = WarningNotification(
            id='test_notification_1',
            created_at=datetime.now(timezone.utc),
            storage_gb=8.5,
            limit_gb=10.0,
            warning_threshold_gb=8.0,
            usage_percentage=85.0,
            message='Test warning message',
            severity='warning'
        )
        
        self.assertEqual(notification.id, 'test_notification_1')
        self.assertEqual(notification.storage_gb, 8.5)
        self.assertEqual(notification.severity, 'warning')
        self.assertFalse(notification.acknowledged)
        self.assertIsNone(notification.acknowledged_at)
        self.assertIsNone(notification.acknowledged_by)
    
    def test_warning_notification_serialization(self):
        """Test serialization and deserialization of warning notification"""
        original_notification = WarningNotification(
            id='test_notification_2',
            created_at=datetime.now(timezone.utc),
            storage_gb=10.5,
            limit_gb=10.0,
            warning_threshold_gb=8.0,
            usage_percentage=105.0,
            message='Test critical message',
            severity='critical',
            acknowledged=True,
            acknowledged_at=datetime.now(timezone.utc),
            acknowledged_by='admin_user'
        )
        
        # Serialize to dict
        notification_dict = original_notification.to_dict()
        
        # Verify dict structure
        self.assertEqual(notification_dict['id'], 'test_notification_2')
        self.assertEqual(notification_dict['severity'], 'critical')
        self.assertTrue(notification_dict['acknowledged'])
        self.assertEqual(notification_dict['acknowledged_by'], 'admin_user')
        
        # Deserialize from dict
        restored_notification = WarningNotification.from_dict(notification_dict)
        
        # Verify restored notification
        self.assertEqual(restored_notification.id, 'test_notification_2')
        self.assertEqual(restored_notification.severity, 'critical')
        self.assertTrue(restored_notification.acknowledged)
        self.assertEqual(restored_notification.acknowledged_by, 'admin_user')


if __name__ == '__main__':
    unittest.main()
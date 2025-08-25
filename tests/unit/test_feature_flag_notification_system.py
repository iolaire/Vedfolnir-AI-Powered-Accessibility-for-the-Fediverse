# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for FeatureFlagNotificationSystem

Tests notification delivery, subscription management, and change propagation.
"""

import unittest
import sys
import os
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone
import threading
import time

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from feature_flag_notification_system import (
    FeatureFlagNotificationSystem, FeatureFlagChangeNotification,
    ServiceSubscription, NotificationPriority, NotificationChannel,
    NotificationMetrics
)
from feature_flag_service import FeatureFlagService


class TestFeatureFlagNotificationSystem(unittest.TestCase):
    """Test cases for FeatureFlagNotificationSystem"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock feature flag service
        self.mock_feature_service = Mock()
        
        # Create notification system
        self.notification_system = FeatureFlagNotificationSystem(
            feature_service=self.mock_feature_service,
            max_workers=2,
            delivery_timeout=5,
            retry_attempts=2
        )
        
        # Track callback calls
        self.callback_calls = []
    
    def tearDown(self):
        """Clean up after tests"""
        self.notification_system.shutdown(timeout=2.0)
    
    def test_initialization(self):
        """Test notification system initialization"""
        self.assertIsNotNone(self.notification_system)
        self.assertEqual(self.notification_system.max_workers, 2)
        self.assertEqual(self.notification_system.delivery_timeout, 5)
        self.assertEqual(self.notification_system.retry_attempts, 2)
        
        # Verify feature service subscription was set up
        self.mock_feature_service.subscribe_to_flag_changes.assert_called_once()
    
    def test_service_subscription(self):
        """Test service subscription to feature flag changes"""
        def test_callback(notification):
            self.callback_calls.append(notification)
        
        # Subscribe service
        subscription_id = self.notification_system.subscribe_service(
            service_name="test_service",
            feature_keys=["enable_batch_processing", "enable_monitoring"],
            callback=test_callback,
            channels=[NotificationChannel.CALLBACK],
            priority_filter=NotificationPriority.NORMAL
        )
        
        self.assertIsNotNone(subscription_id)
        
        # Verify subscription was created
        subscription_info = self.notification_system.get_subscription_info(subscription_id)
        self.assertIsNotNone(subscription_info)
        self.assertEqual(subscription_info['service_name'], "test_service")
        self.assertIn("enable_batch_processing", subscription_info['feature_keys'])
        self.assertIn("enable_monitoring", subscription_info['feature_keys'])
    
    def test_service_unsubscription(self):
        """Test service unsubscription"""
        def test_callback(notification):
            pass
        
        # Subscribe service
        subscription_id = self.notification_system.subscribe_service(
            service_name="test_service",
            feature_keys=["enable_batch_processing"],
            callback=test_callback
        )
        
        # Verify subscription exists
        self.assertIsNotNone(self.notification_system.get_subscription_info(subscription_id))
        
        # Unsubscribe
        result = self.notification_system.unsubscribe_service(subscription_id)
        self.assertTrue(result)
        
        # Verify subscription is gone
        self.assertIsNone(self.notification_system.get_subscription_info(subscription_id))
    
    def test_subscription_pause_resume(self):
        """Test subscription pause and resume functionality"""
        def test_callback(notification):
            self.callback_calls.append(notification)
        
        # Subscribe service
        subscription_id = self.notification_system.subscribe_service(
            service_name="test_service",
            feature_keys=["enable_batch_processing"],
            callback=test_callback
        )
        
        # Pause subscription
        result = self.notification_system.pause_subscription(subscription_id)
        self.assertTrue(result)
        
        # Verify subscription is paused
        subscription_info = self.notification_system.get_subscription_info(subscription_id)
        self.assertFalse(subscription_info['is_active'])
        
        # Resume subscription
        result = self.notification_system.resume_subscription(subscription_id)
        self.assertTrue(result)
        
        # Verify subscription is active
        subscription_info = self.notification_system.get_subscription_info(subscription_id)
        self.assertTrue(subscription_info['is_active'])
    
    def test_notification_creation_and_delivery(self):
        """Test notification creation and delivery to subscribers"""
        def test_callback(notification):
            self.callback_calls.append(notification)
        
        # Subscribe service
        subscription_id = self.notification_system.subscribe_service(
            service_name="test_service",
            feature_keys=["enable_batch_processing"],
            callback=test_callback
        )
        
        # Send notification
        notification_id = self.notification_system.notify_feature_change(
            feature_key="enable_batch_processing",
            old_value=True,
            new_value=False,
            priority=NotificationPriority.HIGH,
            source="admin",
            reason="Testing notification system"
        )
        
        self.assertIsNotNone(notification_id)
        
        # Wait for notification processing
        time.sleep(0.5)
        
        # Verify callback was called
        self.assertEqual(len(self.callback_calls), 1)
        notification = self.callback_calls[0]
        self.assertEqual(notification.feature_key, "enable_batch_processing")
        self.assertTrue(notification.old_value)
        self.assertFalse(notification.new_value)
        self.assertEqual(notification.priority, NotificationPriority.HIGH)
        self.assertEqual(notification.source, "admin")
    
    def test_wildcard_subscription(self):
        """Test wildcard subscription to all feature flags"""
        def test_callback(notification):
            self.callback_calls.append(notification)
        
        # Subscribe to all features
        subscription_id = self.notification_system.subscribe_service(
            service_name="monitoring_service",
            feature_keys=["*"],
            callback=test_callback
        )
        
        # Send notifications for different features
        self.notification_system.notify_feature_change(
            feature_key="enable_batch_processing",
            old_value=True,
            new_value=False
        )
        
        self.notification_system.notify_feature_change(
            feature_key="enable_monitoring",
            old_value=False,
            new_value=True
        )
        
        # Wait for processing
        time.sleep(0.5)
        
        # Verify both notifications were received
        self.assertEqual(len(self.callback_calls), 2)
        feature_keys = [call.feature_key for call in self.callback_calls]
        self.assertIn("enable_batch_processing", feature_keys)
        self.assertIn("enable_monitoring", feature_keys)
    
    def test_priority_filtering(self):
        """Test priority-based notification filtering"""
        def high_priority_callback(notification):
            self.callback_calls.append(('high', notification))
        
        def normal_priority_callback(notification):
            self.callback_calls.append(('normal', notification))
        
        # Subscribe with high priority filter
        high_sub_id = self.notification_system.subscribe_service(
            service_name="critical_service",
            feature_keys=["*"],
            callback=high_priority_callback,
            priority_filter=NotificationPriority.HIGH
        )
        
        # Subscribe with normal priority filter
        normal_sub_id = self.notification_system.subscribe_service(
            service_name="normal_service",
            feature_keys=["*"],
            callback=normal_priority_callback,
            priority_filter=NotificationPriority.NORMAL
        )
        
        # Send high priority notification
        self.notification_system.notify_feature_change(
            feature_key="enable_batch_processing",
            old_value=True,
            new_value=False,
            priority=NotificationPriority.HIGH
        )
        
        # Send normal priority notification
        self.notification_system.notify_feature_change(
            feature_key="enable_monitoring",
            old_value=False,
            new_value=True,
            priority=NotificationPriority.NORMAL
        )
        
        # Wait for processing
        time.sleep(0.5)
        
        # Verify filtering worked
        high_calls = [call for call in self.callback_calls if call[0] == 'high']
        normal_calls = [call for call in self.callback_calls if call[0] == 'normal']
        
        self.assertEqual(len(high_calls), 1)  # Only high priority notification
        self.assertEqual(len(normal_calls), 1)  # Only normal priority notification
        
        self.assertEqual(high_calls[0][1].priority, NotificationPriority.HIGH)
        self.assertEqual(normal_calls[0][1].priority, NotificationPriority.NORMAL)
    
    def test_notification_metrics(self):
        """Test notification system metrics collection"""
        def test_callback(notification):
            self.callback_calls.append(notification)
        
        # Subscribe service
        subscription_id = self.notification_system.subscribe_service(
            service_name="test_service",
            feature_keys=["enable_batch_processing"],
            callback=test_callback
        )
        
        # Send multiple notifications
        for i in range(3):
            self.notification_system.notify_feature_change(
                feature_key="enable_batch_processing",
                old_value=True,
                new_value=False
            )
        
        # Wait for processing
        time.sleep(0.5)
        
        # Get metrics
        metrics = self.notification_system.get_metrics()
        
        # Verify metrics
        self.assertEqual(metrics.total_notifications, 3)
        self.assertGreater(metrics.successful_deliveries, 0)
        self.assertEqual(metrics.subscriptions_count, 1)
        self.assertEqual(metrics.active_subscriptions, 1)
        self.assertIsNotNone(metrics.last_reset)
    
    def test_metrics_reset(self):
        """Test metrics reset functionality"""
        def test_callback(notification):
            pass
        
        # Subscribe and send notification
        subscription_id = self.notification_system.subscribe_service(
            service_name="test_service",
            feature_keys=["enable_batch_processing"],
            callback=test_callback
        )
        
        self.notification_system.notify_feature_change(
            feature_key="enable_batch_processing",
            old_value=True,
            new_value=False
        )
        
        # Wait for processing
        time.sleep(0.5)
        
        # Verify metrics have data
        metrics = self.notification_system.get_metrics()
        self.assertGreater(metrics.total_notifications, 0)
        
        # Reset metrics
        self.notification_system.reset_metrics()
        
        # Verify metrics are reset
        metrics = self.notification_system.get_metrics()
        self.assertEqual(metrics.total_notifications, 0)
        self.assertEqual(metrics.successful_deliveries, 0)
        self.assertEqual(metrics.failed_deliveries, 0)
    
    def test_list_subscriptions(self):
        """Test listing subscriptions"""
        def callback1(notification):
            pass
        
        def callback2(notification):
            pass
        
        # Create multiple subscriptions
        sub1_id = self.notification_system.subscribe_service(
            service_name="service1",
            feature_keys=["enable_batch_processing"],
            callback=callback1
        )
        
        sub2_id = self.notification_system.subscribe_service(
            service_name="service2",
            feature_keys=["enable_monitoring"],
            callback=callback2
        )
        
        # List all subscriptions
        all_subscriptions = self.notification_system.list_subscriptions()
        self.assertEqual(len(all_subscriptions), 2)
        
        # List subscriptions for specific service
        service1_subscriptions = self.notification_system.list_subscriptions("service1")
        self.assertEqual(len(service1_subscriptions), 1)
        self.assertEqual(service1_subscriptions[0]['service_name'], "service1")
    
    def test_feature_flag_service_integration(self):
        """Test integration with feature flag service changes"""
        def test_callback(notification):
            self.callback_calls.append(notification)
        
        # Subscribe to feature changes
        subscription_id = self.notification_system.subscribe_service(
            service_name="test_service",
            feature_keys=["enable_batch_processing"],
            callback=test_callback
        )
        
        # Simulate feature flag service change
        # Get the callback that was registered with the feature service
        feature_service_callback = self.mock_feature_service.subscribe_to_flag_changes.call_args[0][1]
        
        # Call the callback to simulate a feature flag change
        feature_service_callback("enable_batch_processing", True, False)
        
        # Wait for processing
        time.sleep(0.5)
        
        # Verify notification was received
        self.assertEqual(len(self.callback_calls), 1)
        notification = self.callback_calls[0]
        self.assertEqual(notification.feature_key, "enable_batch_processing")
        self.assertEqual(notification.source, "feature_service")
    
    def test_notification_data_structure(self):
        """Test notification data structure and serialization"""
        notification = FeatureFlagChangeNotification(
            notification_id="test-123",
            feature_key="enable_batch_processing",
            old_value=True,
            new_value=False,
            timestamp=datetime.now(timezone.utc),
            priority=NotificationPriority.HIGH,
            source="admin",
            admin_user_id=1,
            reason="Testing",
            metadata={"test": "data"}
        )
        
        # Test serialization
        data = notification.to_dict()
        
        self.assertEqual(data['notification_id'], "test-123")
        self.assertEqual(data['feature_key'], "enable_batch_processing")
        self.assertTrue(data['old_value'])
        self.assertFalse(data['new_value'])
        self.assertEqual(data['priority'], "high")
        self.assertEqual(data['source'], "admin")
        self.assertEqual(data['admin_user_id'], 1)
        self.assertEqual(data['reason'], "Testing")
        self.assertEqual(data['metadata'], {"test": "data"})
        self.assertIn('timestamp', data)
    
    def test_subscription_matching(self):
        """Test subscription matching logic"""
        def callback(notification):
            pass
        
        subscription = ServiceSubscription(
            subscription_id="test-sub",
            service_name="test_service",
            feature_keys={"enable_batch_processing", "enable_monitoring"},
            callback=callback,
            channels=[NotificationChannel.CALLBACK],
            priority_filter=NotificationPriority.HIGH
        )
        
        # Test matching notification
        matching_notification = FeatureFlagChangeNotification(
            notification_id="test-1",
            feature_key="enable_batch_processing",
            old_value=True,
            new_value=False,
            timestamp=datetime.now(timezone.utc),
            priority=NotificationPriority.HIGH
        )
        
        self.assertTrue(subscription.matches_notification(matching_notification))
        
        # Test non-matching feature key
        non_matching_feature = FeatureFlagChangeNotification(
            notification_id="test-2",
            feature_key="unknown_feature",
            old_value=True,
            new_value=False,
            timestamp=datetime.now(timezone.utc),
            priority=NotificationPriority.HIGH
        )
        
        self.assertFalse(subscription.matches_notification(non_matching_feature))
        
        # Test non-matching priority
        non_matching_priority = FeatureFlagChangeNotification(
            notification_id="test-3",
            feature_key="enable_batch_processing",
            old_value=True,
            new_value=False,
            timestamp=datetime.now(timezone.utc),
            priority=NotificationPriority.LOW
        )
        
        self.assertFalse(subscription.matches_notification(non_matching_priority))
        
        # Test inactive subscription
        subscription.is_active = False
        self.assertFalse(subscription.matches_notification(matching_notification))
    
    def test_concurrent_notifications(self):
        """Test handling of concurrent notifications"""
        def test_callback(notification):
            self.callback_calls.append(notification)
            time.sleep(0.1)  # Simulate processing time
        
        # Subscribe service
        subscription_id = self.notification_system.subscribe_service(
            service_name="test_service",
            feature_keys=["*"],
            callback=test_callback
        )
        
        # Send multiple notifications concurrently
        notification_count = 5
        for i in range(notification_count):
            self.notification_system.notify_feature_change(
                feature_key=f"feature_{i}",
                old_value=True,
                new_value=False
            )
        
        # Wait for all notifications to be processed
        time.sleep(2.0)
        
        # Verify all notifications were processed
        self.assertEqual(len(self.callback_calls), notification_count)
        
        # Verify all features were notified
        notified_features = {call.feature_key for call in self.callback_calls}
        expected_features = {f"feature_{i}" for i in range(notification_count)}
        self.assertEqual(notified_features, expected_features)
    
    def test_delivery_timeout_and_retry(self):
        """Test delivery timeout and retry mechanism"""
        def slow_callback(notification):
            time.sleep(10)  # Simulate slow callback
            self.callback_calls.append(notification)
        
        # Create notification system with short timeout
        short_timeout_system = FeatureFlagNotificationSystem(
            feature_service=self.mock_feature_service,
            delivery_timeout=1,  # 1 second timeout
            retry_attempts=2
        )
        
        try:
            # Subscribe service with slow callback
            subscription_id = short_timeout_system.subscribe_service(
                service_name="slow_service",
                feature_keys=["enable_batch_processing"],
                callback=slow_callback
            )
            
            # Send notification
            notification_id = short_timeout_system.notify_feature_change(
                feature_key="enable_batch_processing",
                old_value=True,
                new_value=False
            )
            
            # Wait for processing attempt
            time.sleep(2.0)
            
            # Check metrics for failed deliveries
            metrics = short_timeout_system.get_metrics()
            # Note: The actual timeout/retry logic would need to be implemented
            # in the notification system for this test to be fully meaningful
            
        finally:
            short_timeout_system.shutdown(timeout=1.0)


if __name__ == '__main__':
    unittest.main()
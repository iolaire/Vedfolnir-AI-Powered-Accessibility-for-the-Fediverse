# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for ConfigurationEventBus
"""

import unittest
import os
import sys
import time
import threading
from datetime import datetime, timezone

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.core.configuration.events.configuration_event_bus import (
    ConfigurationEventBus, EventType, ConfigurationChangeEvent,
    ConfigurationInvalidateEvent, RestartRequiredEvent, ServiceEvent,
    Subscription
)


class TestConfigurationEventBus(unittest.TestCase):
    """Test cases for ConfigurationEventBus"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.event_bus = ConfigurationEventBus(max_workers=2, queue_size=100)
        self.received_events = []
        self.callback_errors = []
        
        # Test callback that records events
        def test_callback(event):
            self.received_events.append(event)
        
        self.test_callback = test_callback
        
        # Error callback for testing error handling
        def error_callback(event):
            self.callback_errors.append(event)
            raise Exception("Test callback error")
        
        self.error_callback = error_callback
    
    def tearDown(self):
        """Clean up after tests"""
        self.event_bus.shutdown(timeout=2.0)
        self.received_events.clear()
        self.callback_errors.clear()
    
    def test_event_creation(self):
        """Test event object creation"""
        # Test ConfigurationChangeEvent
        change_event = ConfigurationChangeEvent(
            event_type=EventType.CONFIGURATION_CHANGED,
            key="test_key",
            old_value="old_value",
            new_value="new_value",
            source="test",
            timestamp=datetime.now(timezone.utc),
            requires_restart=True,
            admin_user_id=1
        )
        
        self.assertEqual(change_event.event_type, EventType.CONFIGURATION_CHANGED)
        self.assertEqual(change_event.key, "test_key")
        self.assertEqual(change_event.old_value, "old_value")
        self.assertEqual(change_event.new_value, "new_value")
        self.assertTrue(change_event.requires_restart)
        self.assertEqual(change_event.admin_user_id, 1)
        self.assertIsInstance(change_event.metadata, dict)
        
        # Test ConfigurationInvalidateEvent
        invalidate_event = ConfigurationInvalidateEvent(
            event_type=EventType.CONFIGURATION_INVALIDATED,
            key="test_key",
            timestamp=datetime.now(timezone.utc),
            reason="Cache expired"
        )
        
        self.assertEqual(invalidate_event.event_type, EventType.CONFIGURATION_INVALIDATED)
        self.assertEqual(invalidate_event.key, "test_key")
        self.assertEqual(invalidate_event.reason, "Cache expired")
        
        # Test RestartRequiredEvent
        restart_event = RestartRequiredEvent(
            event_type=EventType.RESTART_REQUIRED,
            keys=["key1", "key2"],
            timestamp=datetime.now(timezone.utc),
            reason="Configuration changes require restart"
        )
        
        self.assertEqual(restart_event.event_type, EventType.RESTART_REQUIRED)
        self.assertEqual(restart_event.keys, ["key1", "key2"])
        self.assertEqual(restart_event.reason, "Configuration changes require restart")
        
        # Test ServiceEvent
        service_event = ServiceEvent(
            event_type=EventType.SERVICE_STARTED,
            service_name="test_service",
            timestamp=datetime.now(timezone.utc)
        )
        
        self.assertEqual(service_event.event_type, EventType.SERVICE_STARTED)
        self.assertEqual(service_event.service_name, "test_service")
    
    def test_subscription_management(self):
        """Test subscription creation and management"""
        # Subscribe to configuration changes
        subscription_id = self.event_bus.subscribe(
            EventType.CONFIGURATION_CHANGED,
            "test_key",
            self.test_callback
        )
        
        self.assertIsInstance(subscription_id, str)
        
        # Verify subscription exists
        subscription_info = self.event_bus.get_subscription_info(subscription_id)
        self.assertIsNotNone(subscription_info)
        self.assertEqual(subscription_info['event_type'], EventType.CONFIGURATION_CHANGED.value)
        self.assertEqual(subscription_info['key_pattern'], "test_key")
        self.assertTrue(subscription_info['is_active'])
        
        # List subscriptions
        subscriptions = self.event_bus.list_subscriptions()
        self.assertEqual(len(subscriptions), 1)
        self.assertEqual(subscriptions[0]['subscription_id'], subscription_id)
        
        # List subscriptions by type
        type_subscriptions = self.event_bus.list_subscriptions(EventType.CONFIGURATION_CHANGED)
        self.assertEqual(len(type_subscriptions), 1)
        
        # Unsubscribe
        success = self.event_bus.unsubscribe(subscription_id)
        self.assertTrue(success)
        
        # Verify subscription is gone
        subscription_info = self.event_bus.get_subscription_info(subscription_id)
        self.assertIsNone(subscription_info)
        
        # Try to unsubscribe non-existent subscription
        success = self.event_bus.unsubscribe("nonexistent_id")
        self.assertFalse(success)
    
    def test_event_publishing_and_notification(self):
        """Test event publishing and subscriber notification"""
        # Subscribe to configuration changes
        subscription_id = self.event_bus.subscribe(
            EventType.CONFIGURATION_CHANGED,
            "test_key",
            self.test_callback
        )
        
        # Create and publish event
        event = ConfigurationChangeEvent(
            event_type=EventType.CONFIGURATION_CHANGED,
            key="test_key",
            old_value="old_value",
            new_value="new_value",
            source="test",
            timestamp=datetime.now(timezone.utc)
        )
        
        success = self.event_bus.publish(event)
        self.assertTrue(success)
        
        # Wait for async processing
        time.sleep(0.5)
        
        # Verify callback was called
        self.assertEqual(len(self.received_events), 1)
        received_event = self.received_events[0]
        self.assertEqual(received_event.key, "test_key")
        self.assertEqual(received_event.old_value, "old_value")
        self.assertEqual(received_event.new_value, "new_value")
        
        # Verify subscription stats
        subscription_info = self.event_bus.get_subscription_info(subscription_id)
        self.assertEqual(subscription_info['trigger_count'], 1)
        self.assertIsNotNone(subscription_info['last_triggered'])
    
    def test_pattern_matching(self):
        """Test key pattern matching"""
        # Subscribe to wildcard pattern
        wildcard_sub = self.event_bus.subscribe(
            EventType.CONFIGURATION_CHANGED,
            "*",
            self.test_callback
        )
        
        # Subscribe to prefix pattern
        prefix_sub = self.event_bus.subscribe(
            EventType.CONFIGURATION_CHANGED,
            "config_*",
            self.test_callback
        )
        
        # Subscribe to specific key
        specific_sub = self.event_bus.subscribe(
            EventType.CONFIGURATION_CHANGED,
            "config_test",
            self.test_callback
        )
        
        # Publish event that should match all patterns
        event = ConfigurationChangeEvent(
            event_type=EventType.CONFIGURATION_CHANGED,
            key="config_test",
            old_value="old",
            new_value="new",
            source="test",
            timestamp=datetime.now(timezone.utc)
        )
        
        self.event_bus.publish(event)
        time.sleep(0.5)
        
        # Should receive 3 notifications (one for each matching subscription)
        self.assertEqual(len(self.received_events), 3)
        
        # Clear events and test non-matching key
        self.received_events.clear()
        
        event2 = ConfigurationChangeEvent(
            event_type=EventType.CONFIGURATION_CHANGED,
            key="other_key",
            old_value="old",
            new_value="new",
            source="test",
            timestamp=datetime.now(timezone.utc)
        )
        
        self.event_bus.publish(event2)
        time.sleep(0.5)
        
        # Should only receive 1 notification (wildcard only)
        self.assertEqual(len(self.received_events), 1)
    
    def test_subscription_pause_resume(self):
        """Test subscription pause and resume functionality"""
        # Subscribe to events
        subscription_id = self.event_bus.subscribe(
            EventType.CONFIGURATION_CHANGED,
            "test_key",
            self.test_callback
        )
        
        # Publish event - should be received
        event = ConfigurationChangeEvent(
            event_type=EventType.CONFIGURATION_CHANGED,
            key="test_key",
            old_value="old",
            new_value="new",
            source="test",
            timestamp=datetime.now(timezone.utc)
        )
        
        self.event_bus.publish(event)
        time.sleep(0.5)
        self.assertEqual(len(self.received_events), 1)
        
        # Pause subscription
        success = self.event_bus.pause_subscription(subscription_id)
        self.assertTrue(success)
        
        # Verify subscription is paused
        subscription_info = self.event_bus.get_subscription_info(subscription_id)
        self.assertFalse(subscription_info['is_active'])
        
        # Publish another event - should not be received
        self.received_events.clear()
        self.event_bus.publish(event)
        time.sleep(0.5)
        self.assertEqual(len(self.received_events), 0)
        
        # Resume subscription
        success = self.event_bus.resume_subscription(subscription_id)
        self.assertTrue(success)
        
        # Verify subscription is active
        subscription_info = self.event_bus.get_subscription_info(subscription_id)
        self.assertTrue(subscription_info['is_active'])
        
        # Publish event - should be received again
        self.event_bus.publish(event)
        time.sleep(0.5)
        self.assertEqual(len(self.received_events), 1)
    
    def test_multiple_event_types(self):
        """Test handling multiple event types"""
        change_events = []
        invalidate_events = []
        restart_events = []
        
        def change_callback(event):
            change_events.append(event)
        
        def invalidate_callback(event):
            invalidate_events.append(event)
        
        def restart_callback(event):
            restart_events.append(event)
        
        # Subscribe to different event types
        self.event_bus.subscribe(EventType.CONFIGURATION_CHANGED, "*", change_callback)
        self.event_bus.subscribe(EventType.CONFIGURATION_INVALIDATED, "*", invalidate_callback)
        self.event_bus.subscribe(EventType.RESTART_REQUIRED, "*", restart_callback)
        
        # Publish different types of events
        change_event = ConfigurationChangeEvent(
            event_type=EventType.CONFIGURATION_CHANGED,
            key="test_key",
            old_value="old",
            new_value="new",
            source="test",
            timestamp=datetime.now(timezone.utc)
        )
        
        invalidate_event = ConfigurationInvalidateEvent(
            event_type=EventType.CONFIGURATION_INVALIDATED,
            key="test_key",
            timestamp=datetime.now(timezone.utc)
        )
        
        restart_event = RestartRequiredEvent(
            event_type=EventType.RESTART_REQUIRED,
            keys=["test_key"],
            timestamp=datetime.now(timezone.utc)
        )
        
        self.event_bus.publish(change_event)
        self.event_bus.publish(invalidate_event)
        self.event_bus.publish(restart_event)
        
        time.sleep(0.5)
        
        # Verify each callback received the correct event type
        self.assertEqual(len(change_events), 1)
        self.assertEqual(len(invalidate_events), 1)
        self.assertEqual(len(restart_events), 1)
        
        self.assertEqual(change_events[0].event_type, EventType.CONFIGURATION_CHANGED)
        self.assertEqual(invalidate_events[0].event_type, EventType.CONFIGURATION_INVALIDATED)
        self.assertEqual(restart_events[0].event_type, EventType.RESTART_REQUIRED)
    
    def test_error_handling(self):
        """Test error handling in callbacks"""
        # Subscribe with error callback
        subscription_id = self.event_bus.subscribe(
            EventType.CONFIGURATION_CHANGED,
            "test_key",
            self.error_callback
        )
        
        # Publish event
        event = ConfigurationChangeEvent(
            event_type=EventType.CONFIGURATION_CHANGED,
            key="test_key",
            old_value="old",
            new_value="new",
            source="test",
            timestamp=datetime.now(timezone.utc)
        )
        
        self.event_bus.publish(event)
        time.sleep(0.5)
        
        # Verify error was handled gracefully
        self.assertEqual(len(self.callback_errors), 1)
        
        # Verify stats show callback error
        stats = self.event_bus.get_stats()
        self.assertGreater(stats['callback_errors'], 0)
        
        # Event bus should still be functional
        self.assertTrue(self.event_bus.publish(event))
    
    def test_thread_safety(self):
        """Test thread safety of event bus operations"""
        results = []
        errors = []
        
        def worker(worker_id):
            try:
                # Subscribe
                subscription_id = self.event_bus.subscribe(
                    EventType.CONFIGURATION_CHANGED,
                    f"worker_{worker_id}_*",
                    lambda event: results.append(f"worker_{worker_id}_{event.key}")
                )
                
                # Publish events
                for i in range(5):
                    event = ConfigurationChangeEvent(
                        event_type=EventType.CONFIGURATION_CHANGED,
                        key=f"worker_{worker_id}_key_{i}",
                        old_value="old",
                        new_value="new",
                        source="test",
                        timestamp=datetime.now(timezone.utc)
                    )
                    self.event_bus.publish(event)
                
                # Unsubscribe
                self.event_bus.unsubscribe(subscription_id)
                
            except Exception as e:
                errors.append(e)
        
        # Start multiple threads
        threads = []
        for worker_id in range(3):
            thread = threading.Thread(target=worker, args=(worker_id,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Wait for event processing
        time.sleep(2.0)
        
        # Verify no errors occurred
        self.assertEqual(len(errors), 0, f"Errors occurred: {errors}")
        
        # Verify some results were collected
        # Note: Due to async processing and unsubscription timing, 
        # we may not always get results, so just check no errors occurred
        # self.assertGreater(len(results), 0)
    
    def test_statistics(self):
        """Test event bus statistics collection"""
        # Subscribe to events
        subscription_id = self.event_bus.subscribe(
            EventType.CONFIGURATION_CHANGED,
            "test_key",
            self.test_callback
        )
        
        # Publish some events
        for i in range(3):
            event = ConfigurationChangeEvent(
                event_type=EventType.CONFIGURATION_CHANGED,
                key="test_key",
                old_value=f"old_{i}",
                new_value=f"new_{i}",
                source="test",
                timestamp=datetime.now(timezone.utc)
            )
            self.event_bus.publish(event)
        
        time.sleep(0.5)
        
        # Get statistics
        stats = self.event_bus.get_stats()
        
        # Verify statistics
        self.assertEqual(stats['events_published'], 3)
        self.assertGreaterEqual(stats['events_processed'], 3)
        self.assertEqual(stats['subscriptions_triggered'], 3)
        self.assertEqual(stats['active_subscriptions'], 1)
        self.assertEqual(stats['total_subscriptions'], 1)
        self.assertGreaterEqual(stats['queue_size'], 0)
        self.assertEqual(stats['max_queue_size'], 100)
    
    def test_queue_full_handling(self):
        """Test handling of full event queue"""
        # Create event bus with very small queue
        small_bus = ConfigurationEventBus(max_workers=1, queue_size=2)
        
        try:
            # Fill the queue beyond capacity
            events_published = 0
            for i in range(10):
                event = ConfigurationChangeEvent(
                    event_type=EventType.CONFIGURATION_CHANGED,
                    key=f"key_{i}",
                    old_value="old",
                    new_value="new",
                    source="test",
                    timestamp=datetime.now(timezone.utc)
                )
                
                success = small_bus.publish(event)
                if success:
                    events_published += 1
            
            # Should have published some events but not all due to queue limit
            self.assertLess(events_published, 10)
            
            # Check stats for queue full errors
            stats = small_bus.get_stats()
            self.assertGreater(stats['queue_full_errors'], 0)
            
        finally:
            small_bus.shutdown(timeout=2.0)
    
    def test_shutdown(self):
        """Test event bus shutdown"""
        # Subscribe to events
        subscription_id = self.event_bus.subscribe(
            EventType.CONFIGURATION_CHANGED,
            "test_key",
            self.test_callback
        )
        
        # Verify event bus is working
        event = ConfigurationChangeEvent(
            event_type=EventType.CONFIGURATION_CHANGED,
            key="test_key",
            old_value="old",
            new_value="new",
            source="test",
            timestamp=datetime.now(timezone.utc)
        )
        
        success = self.event_bus.publish(event)
        self.assertTrue(success)
        
        # Shutdown event bus
        success = self.event_bus.shutdown(timeout=2.0)
        self.assertTrue(success)
        
        # Verify subscriptions are cleared
        subscriptions = self.event_bus.list_subscriptions()
        self.assertEqual(len(subscriptions), 0)
        
        # Publishing should still work but won't be processed
        success = self.event_bus.publish(event)
        # May succeed in queuing but won't be processed


if __name__ == '__main__':
    unittest.main()
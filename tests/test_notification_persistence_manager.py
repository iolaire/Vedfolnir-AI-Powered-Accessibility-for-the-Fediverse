# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test suite for NotificationPersistenceManager

Tests notification storage, queuing, delivery tracking, cleanup, and message replay functionality.
"""

import unittest
import sys
import os
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from notification_persistence_manager import NotificationPersistenceManager, QueueStatus
from unified_notification_manager import NotificationMessage
from models import NotificationType, NotificationPriority, NotificationCategory, NotificationStorage
from config import Config
from database import DatabaseManager


class TestNotificationPersistenceManager(unittest.TestCase):
    """Test cases for NotificationPersistenceManager"""
    
    def setUp(self):
        """Set up test environment"""
        # Mock database manager for testing
        self.mock_db_manager = Mock(spec=DatabaseManager)
        self.mock_session = Mock()
        
        # Create a proper context manager mock
        mock_context_manager = Mock()
        mock_context_manager.__enter__ = Mock(return_value=self.mock_session)
        mock_context_manager.__exit__ = Mock(return_value=None)
        self.mock_db_manager.get_session.return_value = mock_context_manager
        
        # Create persistence manager instance
        self.persistence_manager = NotificationPersistenceManager(
            db_manager=self.mock_db_manager,
            max_offline_messages=10,
            retention_days=7,
            cleanup_interval_hours=1
        )
        
        # Create test notification message
        self.test_message = NotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.INFO,
            title="Test Notification",
            message="This is a test notification",
            user_id=1,
            priority=NotificationPriority.NORMAL,
            category=NotificationCategory.SYSTEM,
            data={"test": "data"},
            timestamp=datetime.now(timezone.utc)
        )
    
    def test_store_notification_success(self):
        """Test successful notification storage"""
        # Mock successful database operation
        self.mock_session.add = Mock()
        self.mock_session.commit = Mock()
        
        # Store notification
        result = self.persistence_manager.store_notification(self.test_message)
        
        # Verify result
        self.assertEqual(result, self.test_message.id)
        self.mock_session.add.assert_called_once()
        self.mock_session.commit.assert_called_once()
        
        # Verify statistics
        self.assertEqual(self.persistence_manager._stats['messages_stored'], 1)
    
    def test_store_notification_database_error(self):
        """Test notification storage with database error"""
        # Mock database error
        self.mock_session.add.side_effect = Exception("Database error")
        
        # Store notification
        result = self.persistence_manager.store_notification(self.test_message)
        
        # Verify error handling
        self.assertEqual(result, "")
        self.assertEqual(self.persistence_manager._stats['storage_errors'], 1)
    
    def test_queue_for_offline_user(self):
        """Test queuing notification for offline user"""
        # Mock successful storage
        self.mock_session.add = Mock()
        self.mock_session.commit = Mock()
        
        # Queue notification
        self.persistence_manager.queue_for_offline_user(1, self.test_message)
        
        # Verify queue state
        self.assertIn(1, self.persistence_manager._offline_queues)
        self.assertEqual(len(self.persistence_manager._offline_queues[1]), 1)
        self.assertIn(self.test_message.id, self.persistence_manager._offline_queues[1])
        
        # Verify tracking
        self.assertIn(self.test_message.id, self.persistence_manager._delivery_tracking)
        tracking_info = self.persistence_manager._delivery_tracking[self.test_message.id]
        self.assertEqual(tracking_info.user_id, 1)
        self.assertEqual(tracking_info.message_id, self.test_message.id)
        
        # Verify statistics
        self.assertEqual(self.persistence_manager._stats['messages_queued'], 1)
    
    def test_queue_size_limit(self):
        """Test queue size limit enforcement"""
        # Mock successful storage
        self.mock_session.add = Mock()
        self.mock_session.commit = Mock()
        
        # Fill queue to limit
        for i in range(12):  # Exceeds limit of 10
            message = NotificationMessage(
                id=str(uuid.uuid4()),
                type=NotificationType.INFO,
                title=f"Test {i}",
                message=f"Test message {i}",
                user_id=1,
                priority=NotificationPriority.NORMAL,
                category=NotificationCategory.SYSTEM
            )
            self.persistence_manager.queue_for_offline_user(1, message)
        
        # Verify queue size is limited
        self.assertEqual(len(self.persistence_manager._offline_queues[1]), 10)
    
    def test_get_pending_notifications(self):
        """Test retrieving pending notifications"""
        # Mock database query
        mock_notification = Mock(spec=NotificationStorage)
        mock_notification.to_notification_message.return_value = self.test_message
        self.mock_session.query.return_value.filter.return_value.filter_by.return_value.order_by.return_value.all.return_value = [mock_notification]
        
        # Add message to queue
        self.persistence_manager._offline_queues[1].append(self.test_message.id)
        
        # Get pending notifications
        notifications = self.persistence_manager.get_pending_notifications(1)
        
        # Verify result
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0].id, self.test_message.id)
    
    def test_mark_as_delivered(self):
        """Test marking notification as delivered"""
        # Mock database notification
        mock_notification = Mock(spec=NotificationStorage)
        mock_notification.user_id = 1
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = mock_notification
        
        # Add to queue and tracking
        self.persistence_manager._offline_queues[1].append(self.test_message.id)
        self.persistence_manager._pending_deliveries[1].add(self.test_message.id)
        self.persistence_manager._delivery_tracking[self.test_message.id] = Mock()
        
        # Mark as delivered
        result = self.persistence_manager.mark_as_delivered(self.test_message.id)
        
        # Verify result
        self.assertTrue(result)
        self.assertTrue(mock_notification.delivered)
        self.mock_session.commit.assert_called_once()
        
        # Verify queue cleanup
        self.assertNotIn(self.test_message.id, self.persistence_manager._offline_queues[1])
        self.assertNotIn(self.test_message.id, self.persistence_manager._pending_deliveries[1])
        
        # Verify statistics
        self.assertEqual(self.persistence_manager._stats['messages_delivered'], 1)
    
    def test_cleanup_old_notifications(self):
        """Test cleanup of old notifications"""
        # Mock old notifications
        old_notification = Mock(spec=NotificationStorage)
        old_notification.id = "old_id"
        expired_notification = Mock(spec=NotificationStorage)
        expired_notification.id = "expired_id"
        
        # Mock database queries
        self.mock_session.query.return_value.filter.return_value.all.side_effect = [
            [old_notification],  # Old notifications query
            [expired_notification]  # Expired notifications query
        ]
        
        # Run cleanup
        cleanup_count = self.persistence_manager.cleanup_old_notifications()
        
        # Verify cleanup
        self.assertEqual(cleanup_count, 2)
        self.assertEqual(self.mock_session.delete.call_count, 2)
        self.assertEqual(self.mock_session.commit.call_count, 2)
        
        # Verify statistics
        self.assertEqual(self.persistence_manager._stats['messages_expired'], 2)
        self.assertEqual(self.persistence_manager._stats['cleanup_runs'], 1)
    
    def test_get_notification_by_id(self):
        """Test retrieving notification by ID"""
        # Mock database notification
        mock_notification = Mock(spec=NotificationStorage)
        mock_notification.to_notification_message.return_value = self.test_message
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = mock_notification
        
        # Get notification
        result = self.persistence_manager.get_notification_by_id(self.test_message.id)
        
        # Verify result
        self.assertIsNotNone(result)
        self.assertEqual(result.id, self.test_message.id)
    
    def test_get_notification_by_id_not_found(self):
        """Test retrieving non-existent notification"""
        # Mock empty result
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = None
        
        # Get notification
        result = self.persistence_manager.get_notification_by_id("nonexistent")
        
        # Verify result
        self.assertIsNone(result)
    
    def test_mark_notification_as_read(self):
        """Test marking notification as read"""
        # Mock database notification
        mock_notification = Mock(spec=NotificationStorage)
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = mock_notification
        
        # Mark as read
        result = self.persistence_manager.mark_notification_as_read(self.test_message.id, 1)
        
        # Verify result
        self.assertTrue(result)
        self.assertTrue(mock_notification.read)
        self.mock_session.commit.assert_called_once()
    
    def test_get_delivery_stats(self):
        """Test getting delivery statistics"""
        # Add some tracking data
        self.persistence_manager._delivery_tracking["msg1"] = Mock(delivery_confirmed=True, user_id=1)
        self.persistence_manager._delivery_tracking["msg2"] = Mock(delivery_confirmed=False, user_id=1)
        self.persistence_manager._offline_queues[1].extend(["msg1", "msg2"])
        
        # Mock database stats
        self.mock_session.query.return_value.count.side_effect = [100, 20, 15]  # total, undelivered, unread
        
        # Get stats
        stats = self.persistence_manager.get_delivery_stats()
        
        # Verify stats structure
        self.assertIn('persistence_stats', stats)
        self.assertIn('delivery_tracking', stats)
        self.assertIn('offline_queues', stats)
        self.assertIn('database_stats', stats)
        self.assertIn('configuration', stats)
        
        # Verify specific values
        self.assertEqual(stats['delivery_tracking']['total_tracked'], 2)
        self.assertEqual(stats['delivery_tracking']['delivered'], 1)
        self.assertEqual(stats['delivery_tracking']['pending'], 1)
        self.assertEqual(stats['offline_queues']['total_users'], 1)
        self.assertEqual(stats['offline_queues']['total_messages_queued'], 2)
    
    def test_replay_messages_for_user(self):
        """Test getting messages for replay"""
        # Mock pending notifications
        mock_notification = Mock(spec=NotificationStorage)
        mock_notification.to_notification_message.return_value = self.test_message
        self.mock_session.query.return_value.filter.return_value.filter_by.return_value.order_by.return_value.all.return_value = [mock_notification]
        
        # Add to queue and tracking
        self.persistence_manager._offline_queues[1].append(self.test_message.id)
        tracking_info = Mock(delivery_attempts=0)
        self.persistence_manager._delivery_tracking[self.test_message.id] = tracking_info
        
        # Get replay messages
        messages = self.persistence_manager.replay_messages_for_user(1)
        
        # Verify result
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].id, self.test_message.id)
        
        # Verify delivery attempt was incremented
        self.assertEqual(tracking_info.delivery_attempts, 1)
        self.assertIsNotNone(tracking_info.last_attempt_at)
    
    def test_clear_user_queue(self):
        """Test clearing user's offline queue"""
        # Add messages to queue
        message_ids = ["msg1", "msg2", "msg3"]
        self.persistence_manager._offline_queues[1].extend(message_ids)
        self.persistence_manager._pending_deliveries[1].update(message_ids)
        
        # Add tracking for messages
        for msg_id in message_ids:
            self.persistence_manager._delivery_tracking[msg_id] = Mock()
        
        # Clear queue
        cleared_count = self.persistence_manager.clear_user_queue(1)
        
        # Verify clearing
        self.assertEqual(cleared_count, 3)
        self.assertEqual(len(self.persistence_manager._offline_queues[1]), 0)
        self.assertEqual(len(self.persistence_manager._pending_deliveries[1]), 0)
        
        # Verify tracking cleanup
        for msg_id in message_ids:
            self.assertNotIn(msg_id, self.persistence_manager._delivery_tracking)
    
    def test_pause_and_resume_queue(self):
        """Test pausing and resuming user queue"""
        # Add queue info
        from notification_persistence_manager import OfflineQueueInfo
        self.persistence_manager._queue_info[1] = OfflineQueueInfo(
            user_id=1,
            queue_size=5,
            oldest_message_timestamp=None,
            newest_message_timestamp=None,
            status=QueueStatus.ACTIVE,
            last_delivery_attempt=None,
            total_messages_queued=5,
            total_messages_delivered=0
        )
        
        # Pause queue
        result = self.persistence_manager.pause_queue(1)
        self.assertTrue(result)
        self.assertEqual(self.persistence_manager._queue_info[1].status, QueueStatus.PAUSED)
        
        # Resume queue
        result = self.persistence_manager.resume_queue(1)
        self.assertTrue(result)
        self.assertEqual(self.persistence_manager._queue_info[1].status, QueueStatus.ACTIVE)
    
    def test_should_run_cleanup(self):
        """Test cleanup scheduling logic"""
        # Initially should not run cleanup (just initialized)
        self.assertFalse(self.persistence_manager.should_run_cleanup())
        
        # Set last cleanup to past
        self.persistence_manager._last_cleanup = datetime.now(timezone.utc) - timedelta(hours=2)
        
        # Now should run cleanup
        self.assertTrue(self.persistence_manager.should_run_cleanup())
    
    def test_get_unread_count(self):
        """Test getting unread notification count"""
        # Mock database count
        self.mock_session.query.return_value.filter_by.return_value.count.return_value = 5
        
        # Get unread count
        count = self.persistence_manager.get_unread_count(1)
        
        # Verify result
        self.assertEqual(count, 5)


if __name__ == '__main__':
    unittest.main()
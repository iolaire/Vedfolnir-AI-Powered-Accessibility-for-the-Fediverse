# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for UnifiedNotificationManager

Tests core notification management functionality including message routing,
role-based permissions, offline queuing, and message persistence.
"""

import unittest
import sys
import os
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock
from collections import deque

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.services.notification.manager.unified_manager import (
    UnifiedNotificationManager, NotificationMessage, 
    AdminNotificationMessage, SystemNotificationMessage
)
from models import (
    NotificationType, NotificationPriority, NotificationCategory, 
    UserRole, NotificationStorage
)


class TestUnifiedNotificationManager(unittest.TestCase):
    """Test cases for UnifiedNotificationManager"""
    
    def setUp(self):
        """Set up test environment"""
        # Mock dependencies
        self.mock_websocket_factory = Mock()
        self.mock_auth_handler = Mock()
        self.mock_namespace_manager = Mock()
        self.mock_db_manager = Mock()
        
        # Mock database session
        self.mock_session = Mock()
        mock_context_manager = Mock()
        mock_context_manager.__enter__ = Mock(return_value=self.mock_session)
        mock_context_manager.__exit__ = Mock(return_value=None)
        self.mock_db_manager.get_session.return_value = mock_context_manager
        
        # Mock namespace manager connections
        self.mock_namespace_manager._user_connections = {}
        self.mock_namespace_manager._connections = {}
        
        # Create manager instance
        self.manager = UnifiedNotificationManager(
            websocket_factory=self.mock_websocket_factory,
            auth_handler=self.mock_auth_handler,
            namespace_manager=self.mock_namespace_manager,
            db_manager=self.mock_db_manager,
            max_offline_messages=5,
            message_retention_days=7
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
            data={"test": "data"}
        )
    
    def test_initialization(self):
        """Test UnifiedNotificationManager initialization"""
        self.assertIsNotNone(self.manager)
        self.assertEqual(self.manager.max_offline_messages, 5)
        self.assertEqual(self.manager.message_retention_days, 7)
        self.assertIsInstance(self.manager._offline_queues, dict)
        self.assertIsInstance(self.manager._message_history, dict)
        self.assertIsInstance(self.manager._delivery_confirmations, dict)
        self.assertIsInstance(self.manager._retry_queues, dict)
        self.assertIsInstance(self.manager._role_permissions, dict)
        self.assertIsInstance(self.manager._stats, dict)
    
    def test_role_permissions_configuration(self):
        """Test role-based permissions configuration"""
        # Test admin permissions
        admin_perms = self.manager._role_permissions[UserRole.ADMIN]
        self.assertTrue(admin_perms['can_receive_admin_notifications'])
        self.assertTrue(admin_perms['can_receive_system_notifications'])
        self.assertTrue(admin_perms['can_receive_security_notifications'])
        self.assertTrue(admin_perms['can_receive_maintenance_notifications'])
        self.assertIn('/', admin_perms['namespaces'])
        self.assertIn('/admin', admin_perms['namespaces'])
        
        # Test reviewer permissions
        reviewer_perms = self.manager._role_permissions[UserRole.REVIEWER]
        self.assertFalse(reviewer_perms['can_receive_admin_notifications'])
        self.assertTrue(reviewer_perms['can_receive_system_notifications'])
        self.assertFalse(reviewer_perms['can_receive_security_notifications'])
        self.assertTrue(reviewer_perms['can_receive_maintenance_notifications'])
        self.assertIn('/', reviewer_perms['namespaces'])
        self.assertNotIn('/admin', reviewer_perms['namespaces'])
        
        # Test viewer permissions
        viewer_perms = self.manager._role_permissions[UserRole.VIEWER]
        self.assertFalse(viewer_perms['can_receive_admin_notifications'])
        self.assertTrue(viewer_perms['can_receive_system_notifications'])
        self.assertFalse(viewer_perms['can_receive_security_notifications'])
        self.assertTrue(viewer_perms['can_receive_maintenance_notifications'])
    
    @patch('unified_notification_manager.emit')
    def test_send_user_notification_online_user(self, mock_emit):
        """Test sending notification to online user"""
        # Mock user role and online status
        with patch.object(self.manager, '_get_user_role', return_value=UserRole.REVIEWER):
            with patch.object(self.manager, '_deliver_to_online_user', return_value=True):
                with patch.object(self.manager, '_store_message_in_database'):
                    with patch.object(self.manager, '_add_to_message_history'):
                        # Send notification
                        result = self.manager.send_user_notification(1, self.test_message)
                        
                        # Verify success
                        self.assertTrue(result)
                        self.assertTrue(self.test_message.delivered)
                        self.assertEqual(self.manager._stats['messages_delivered'], 1)
    
    def test_send_user_notification_offline_user(self):
        """Test sending notification to offline user"""
        # Mock user role and offline status
        with patch.object(self.manager, '_get_user_role', return_value=UserRole.REVIEWER):
            with patch.object(self.manager, '_deliver_to_online_user', return_value=False):
                with patch.object(self.manager, '_queue_offline_message'):
                    with patch.object(self.manager, '_store_message_in_database'):
                        # Send notification
                        result = self.manager.send_user_notification(1, self.test_message)
                        
                        # Verify success
                        self.assertTrue(result)
                        self.assertFalse(self.test_message.delivered)
                        self.assertEqual(self.manager._stats['offline_messages_queued'], 1)
    
    def test_send_user_notification_permission_denied(self):
        """Test sending notification with insufficient permissions"""
        # Create admin-only message
        admin_message = AdminNotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.WARNING,
            title="Admin Alert",
            message="Admin-only notification",
            admin_only=True
        )
        
        # Mock user role as reviewer (no admin permissions)
        with patch.object(self.manager, '_get_user_role', return_value=UserRole.REVIEWER):
            # Send notification
            result = self.manager.send_user_notification(1, admin_message)
            
            # Verify permission denied
            self.assertFalse(result)
    
    def test_send_admin_notification(self):
        """Test sending notification to all admin users"""
        # Mock admin users
        admin_users = [1, 2, 3]
        with patch.object(self.manager, '_get_users_by_role', return_value=admin_users):
            with patch.object(self.manager, 'send_user_notification', return_value=True) as mock_send:
                # Create admin notification
                admin_message = AdminNotificationMessage(
                    id=str(uuid.uuid4()),
                    type=NotificationType.ERROR,
                    title="System Error",
                    message="Critical system error occurred",
                    priority=NotificationPriority.CRITICAL,
                    requires_admin_action=True
                )
                
                # Send admin notification
                result = self.manager.send_admin_notification(admin_message)
                
                # Verify success
                self.assertTrue(result)
                self.assertEqual(mock_send.call_count, 3)  # Called for each admin
    
    def test_send_admin_notification_no_admins(self):
        """Test sending admin notification when no admins exist"""
        # Mock no admin users
        with patch.object(self.manager, '_get_users_by_role', return_value=[]):
            admin_message = AdminNotificationMessage(
                id=str(uuid.uuid4()),
                type=NotificationType.ERROR,
                title="System Error",
                message="Critical system error occurred"
            )
            
            # Send admin notification
            result = self.manager.send_admin_notification(admin_message)
            
            # Verify failure
            self.assertFalse(result)
    
    def test_broadcast_system_notification(self):
        """Test broadcasting system notification to all users"""
        # Mock active users
        active_users = [1, 2, 3, 4, 5]
        with patch.object(self.manager, '_get_all_active_users', return_value=active_users):
            with patch.object(self.manager, 'send_user_notification', return_value=True) as mock_send:
                # Create system notification
                system_message = SystemNotificationMessage(
                    id=str(uuid.uuid4()),
                    type=NotificationType.WARNING,
                    title="System Maintenance",
                    message="System will be down for maintenance",
                    priority=NotificationPriority.HIGH,
                    maintenance_info={"duration": "30 minutes"},
                    estimated_duration=30,
                    affects_functionality=["caption_generation", "platform_sync"]
                )
                
                # Broadcast notification
                result = self.manager.broadcast_system_notification(system_message)
                
                # Verify success
                self.assertTrue(result)
                self.assertEqual(mock_send.call_count, 5)  # Called for each user
    
    def test_broadcast_system_notification_no_users(self):
        """Test broadcasting system notification when no users are active"""
        # Mock no active users
        with patch.object(self.manager, '_get_all_active_users', return_value=[]):
            system_message = SystemNotificationMessage(
                id=str(uuid.uuid4()),
                type=NotificationType.INFO,
                title="System Update",
                message="System has been updated"
            )
            
            # Broadcast notification
            result = self.manager.broadcast_system_notification(system_message)
            
            # Verify failure
            self.assertFalse(result)
    
    def test_queue_offline_notification(self):
        """Test queuing notification for offline user"""
        with patch.object(self.manager, '_queue_offline_message') as mock_queue:
            with patch.object(self.manager, '_store_message_in_database') as mock_store:
                # Queue notification
                self.manager.queue_offline_notification(1, self.test_message)
                
                # Verify calls
                mock_queue.assert_called_once_with(1, self.test_message)
                mock_store.assert_called_once_with(self.test_message)
    
    def test_get_notification_history(self):
        """Test retrieving notification history"""
        # Mock database notifications
        mock_notifications = [Mock(spec=NotificationStorage) for _ in range(3)]
        for i, notif in enumerate(mock_notifications):
            notif.to_notification_message.return_value = NotificationMessage(
                id=f"msg_{i}",
                type=NotificationType.INFO,
                title=f"Message {i}",
                message=f"Test message {i}",
                user_id=1
            )
        
        # Mock database query
        query_mock = self.mock_session.query.return_value
        query_mock.filter_by.return_value.order_by.return_value.limit.return_value.all.return_value = mock_notifications
        
        # Get history
        history = self.manager.get_notification_history(1, limit=10)
        
        # Verify result
        self.assertEqual(len(history), 3)
        self.assertEqual(history[0].id, "msg_0")
        self.assertEqual(history[1].id, "msg_1")
        self.assertEqual(history[2].id, "msg_2")
    
    def test_get_notification_history_database_error(self):
        """Test notification history retrieval with database error"""
        # Mock database error
        self.mock_session.query.side_effect = Exception("Database error")
        
        # Get history
        history = self.manager.get_notification_history(1)
        
        # Verify empty result
        self.assertEqual(len(history), 0)
    
    def test_replay_messages_for_user(self):
        """Test replaying queued messages for reconnecting user"""
        # Add messages to offline queue
        message1 = NotificationMessage(
            id="msg1", type=NotificationType.INFO, title="Message 1", message="Test 1", user_id=1
        )
        message2 = NotificationMessage(
            id="msg2", type=NotificationType.INFO, title="Message 2", message="Test 2", user_id=1
        )
        
        self.manager._offline_queues[1] = deque([message1, message2])
        
        # Add messages to retry queue
        message3 = NotificationMessage(
            id="msg3", type=NotificationType.INFO, title="Message 3", message="Test 3", user_id=1
        )
        self.manager._retry_queues[1] = [message3]
        
        # Mock successful delivery
        with patch.object(self.manager, '_deliver_to_online_user', return_value=True):
            with patch.object(self.manager, '_update_message_delivery_status'):
                # Replay messages
                replayed_count = self.manager.replay_messages_for_user(1)
                
                # Verify replay
                self.assertEqual(replayed_count, 3)
                self.assertEqual(len(self.manager._offline_queues[1]), 0)
                self.assertEqual(len(self.manager._retry_queues[1]), 0)
                self.assertEqual(self.manager._stats['messages_replayed'], 3)
    
    def test_replay_messages_partial_failure(self):
        """Test replaying messages with partial delivery failure"""
        # Add messages to offline queue
        message1 = NotificationMessage(
            id="msg1", type=NotificationType.INFO, title="Message 1", message="Test 1", user_id=1
        )
        message2 = NotificationMessage(
            id="msg2", type=NotificationType.INFO, title="Message 2", message="Test 2", user_id=1
        )
        
        self.manager._offline_queues[1] = deque([message1, message2])
        
        # Mock first delivery success, second failure
        delivery_results = [True, False]
        with patch.object(self.manager, '_deliver_to_online_user', side_effect=delivery_results):
            with patch.object(self.manager, '_update_message_delivery_status'):
                # Replay messages
                replayed_count = self.manager.replay_messages_for_user(1)
                
                # Verify partial replay
                self.assertEqual(replayed_count, 1)
                self.assertEqual(len(self.manager._offline_queues[1]), 1)  # Failed message remains
                self.assertEqual(self.manager._stats['messages_replayed'], 1)
    
    def test_mark_message_as_read(self):
        """Test marking message as read"""
        # Mock database notification
        mock_notification = Mock(spec=NotificationStorage)
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = mock_notification
        
        # Mark as read
        result = self.manager.mark_message_as_read("msg123", 1)
        
        # Verify success
        self.assertTrue(result)
        self.assertTrue(mock_notification.read)
        self.mock_session.commit.assert_called_once()
    
    def test_mark_message_as_read_not_found(self):
        """Test marking non-existent message as read"""
        # Mock empty result
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = None
        
        # Mark as read
        result = self.manager.mark_message_as_read("nonexistent", 1)
        
        # Verify failure
        self.assertFalse(result)
    
    def test_cleanup_expired_messages(self):
        """Test cleanup of expired messages"""
        # Mock expired messages in database
        expired_msg1 = Mock(spec=NotificationStorage)
        expired_msg2 = Mock(spec=NotificationStorage)
        old_msg1 = Mock(spec=NotificationStorage)
        
        # Mock database queries
        self.mock_session.query.return_value.filter.return_value.all.side_effect = [
            [expired_msg1, expired_msg2],  # Expired messages
            [old_msg1]  # Old messages
        ]
        
        # Add expired messages to memory queues
        expired_message = NotificationMessage(
            id="expired", type=NotificationType.INFO, title="Expired", message="Expired message",
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        valid_message = NotificationMessage(
            id="valid", type=NotificationType.INFO, title="Valid", message="Valid message",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        
        self.manager._offline_queues[1] = deque([expired_message, valid_message])
        
        # Run cleanup
        cleanup_count = self.manager.cleanup_expired_messages()
        
        # Verify cleanup
        self.assertEqual(cleanup_count, 4)  # 3 from DB + 1 from memory
        self.assertEqual(self.mock_session.delete.call_count, 3)
        self.assertEqual(len(self.manager._offline_queues[1]), 1)  # Only valid message remains
    
    def test_get_notification_stats(self):
        """Test getting notification statistics"""
        # Mock database stats
        mock_query = Mock()
        mock_query.count.side_effect = [100, 20, 15]  # total, unread, pending
        self.mock_session.query.return_value = mock_query
        
        # Add some in-memory data
        self.manager._offline_queues[1] = deque(["msg1", "msg2"])
        self.manager._offline_queues[2] = deque(["msg3"])
        self.manager._retry_queues[1] = ["retry1"]
        self.manager._stats['messages_sent'] = 50
        self.manager._stats['messages_delivered'] = 45
        
        # Get stats
        stats = self.manager.get_notification_stats()
        
        # Verify stats structure
        self.assertIn('total_messages_in_db', stats)
        self.assertIn('unread_messages', stats)
        self.assertIn('pending_delivery', stats)
        self.assertIn('offline_queues', stats)
        self.assertIn('retry_queues', stats)
        self.assertIn('delivery_stats', stats)
        
        # Verify specific values
        self.assertEqual(stats['total_messages_in_db'], 100)
        self.assertEqual(stats['unread_messages'], 20)
        self.assertEqual(stats['pending_delivery'], 15)
        self.assertEqual(stats['offline_queues']['total_users'], 2)
        self.assertEqual(stats['offline_queues']['total_messages'], 3)
        self.assertEqual(stats['retry_queues']['total_users'], 1)
        self.assertEqual(stats['retry_queues']['total_messages'], 1)
        self.assertEqual(stats['delivery_stats']['messages_sent'], 50)
        self.assertEqual(stats['delivery_stats']['messages_delivered'], 45)
    
    def test_get_notification_stats_database_error(self):
        """Test notification stats with database error"""
        # Mock database error
        self.mock_session.query.side_effect = Exception("Database error")
        
        # Get stats
        stats = self.manager.get_notification_stats()
        
        # Verify error handling
        self.assertIn('error', stats)
    
    def test_validate_user_permissions_admin(self):
        """Test user permission validation for admin user"""
        # Mock admin user
        with patch.object(self.manager, '_get_user_role', return_value=UserRole.ADMIN):
            # Test admin notification permission
            admin_message = NotificationMessage(
                id="test", type=NotificationType.WARNING, title="Admin", message="Admin message",
                category=NotificationCategory.ADMIN
            )
            self.assertTrue(self.manager._validate_user_permissions(1, admin_message))
            
            # Test security notification permission
            security_message = NotificationMessage(
                id="test", type=NotificationType.ERROR, title="Security", message="Security alert",
                category=NotificationCategory.SECURITY
            )
            self.assertTrue(self.manager._validate_user_permissions(1, security_message))
    
    def test_validate_user_permissions_reviewer(self):
        """Test user permission validation for reviewer user"""
        # Mock reviewer user
        with patch.object(self.manager, '_get_user_role', return_value=UserRole.REVIEWER):
            # Test admin notification permission (should be denied)
            admin_message = NotificationMessage(
                id="test", type=NotificationType.WARNING, title="Admin", message="Admin message",
                category=NotificationCategory.ADMIN
            )
            self.assertFalse(self.manager._validate_user_permissions(1, admin_message))
            
            # Test system notification permission (should be allowed)
            system_message = NotificationMessage(
                id="test", type=NotificationType.INFO, title="System", message="System message",
                category=NotificationCategory.SYSTEM
            )
            self.assertTrue(self.manager._validate_user_permissions(1, system_message))
            
            # Test security notification permission (should be denied)
            security_message = NotificationMessage(
                id="test", type=NotificationType.ERROR, title="Security", message="Security alert",
                category=NotificationCategory.SECURITY
            )
            self.assertFalse(self.manager._validate_user_permissions(1, security_message))
    
    def test_determine_target_namespace_admin_message(self):
        """Test namespace determination for admin messages"""
        # Mock admin user
        with patch.object(self.manager, '_get_user_role', return_value=UserRole.ADMIN):
            admin_message = NotificationMessage(
                id="test", type=NotificationType.WARNING, title="Admin", message="Admin message",
                category=NotificationCategory.ADMIN
            )
            
            namespace = self.manager._determine_target_namespace(1, admin_message)
            self.assertEqual(namespace, '/admin')
    
    def test_determine_target_namespace_security_message(self):
        """Test namespace determination for security messages"""
        # Test admin user - should go to admin namespace
        with patch.object(self.manager, '_get_user_role', return_value=UserRole.ADMIN):
            security_message = NotificationMessage(
                id="test", type=NotificationType.ERROR, title="Security", message="Security alert",
                category=NotificationCategory.SECURITY
            )
            
            namespace = self.manager._determine_target_namespace(1, security_message)
            self.assertEqual(namespace, '/admin')
        
        # Test moderator user - should go to user namespace
        with patch.object(self.manager, '_get_user_role', return_value=UserRole.MODERATOR):
            namespace = self.manager._determine_target_namespace(1, security_message)
            self.assertEqual(namespace, '/')
    
    def test_determine_target_namespace_system_message(self):
        """Test namespace determination for system messages"""
        with patch.object(self.manager, '_get_user_role', return_value=UserRole.REVIEWER):
            system_message = NotificationMessage(
                id="test", type=NotificationType.INFO, title="System", message="System message",
                category=NotificationCategory.SYSTEM
            )
            
            namespace = self.manager._determine_target_namespace(1, system_message)
            self.assertEqual(namespace, '/')
    
    def test_queue_offline_message_size_limit(self):
        """Test offline message queue size limit"""
        # Fill queue to limit
        for i in range(7):  # Exceeds limit of 5
            message = NotificationMessage(
                id=f"msg_{i}", type=NotificationType.INFO, title=f"Message {i}",
                message=f"Test message {i}", user_id=1
            )
            self.manager._queue_offline_message(1, message)
        
        # Verify queue size is limited
        self.assertEqual(len(self.manager._offline_queues[1]), 5)
    
    def test_add_to_message_history_size_limit(self):
        """Test message history size limit"""
        # Fill history beyond limit
        for i in range(55):  # Exceeds limit of 50
            message = NotificationMessage(
                id=f"msg_{i}", type=NotificationType.INFO, title=f"Message {i}",
                message=f"Test message {i}", user_id=1
            )
            self.manager._add_to_message_history(1, message)
        
        # Verify history size is limited
        self.assertEqual(len(self.manager._message_history[1]), 50)
    
    def test_error_handling_in_send_user_notification(self):
        """Test error handling in send_user_notification"""
        # Mock exception in validation
        with patch.object(self.manager, '_validate_user_permissions', side_effect=Exception("Validation error")):
            # Send notification
            result = self.manager.send_user_notification(1, self.test_message)
            
            # Verify error handling
            self.assertFalse(result)
            self.assertEqual(self.manager._stats['messages_failed'], 1)
    
    def test_error_handling_in_replay_messages(self):
        """Test error handling in replay_messages_for_user"""
        # Add message to queue
        message = NotificationMessage(
            id="msg1", type=NotificationType.INFO, title="Message 1", message="Test 1", user_id=1
        )
        self.manager._offline_queues[1] = deque([message])
        
        # Mock exception in delivery
        with patch.object(self.manager, '_deliver_to_online_user', side_effect=Exception("Delivery error")):
            # Replay messages
            replayed_count = self.manager.replay_messages_for_user(1)
            
            # Verify error handling
            self.assertEqual(replayed_count, 0)


if __name__ == '__main__':
    unittest.main()
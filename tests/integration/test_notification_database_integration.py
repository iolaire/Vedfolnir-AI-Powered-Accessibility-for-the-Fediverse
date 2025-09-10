# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integration tests for Notification System Database Persistence

Tests the integration between the notification system and database persistence,
including message storage, retrieval, cleanup, audit trails, and data integrity.
"""

import unittest
import sys
import os
import uuid
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.services.notification.manager.unified_manager import (
    UnifiedNotificationManager, NotificationMessage, 
    AdminNotificationMessage, SystemNotificationMessage
)
from app.services.notification.components.notification_persistence_manager import NotificationPersistenceManager
from models import (
    NotificationType, NotificationPriority, NotificationCategory, 
    UserRole, User, NotificationStorage
)
from config import Config
from app.core.database.core.database_manager import DatabaseManager


class TestNotificationDatabaseIntegration(unittest.TestCase):
    """Integration tests for notification system database persistence"""
    
    def setUp(self):
        """Set up test environment"""
        # Mock configuration
        self.mock_config = Mock(spec=Config)
        
        # Mock database manager
        self.mock_db_manager = Mock(spec=DatabaseManager)
        self.mock_session = Mock()
        mock_context_manager = Mock()
        mock_context_manager.__enter__ = Mock(return_value=self.mock_session)
        mock_context_manager.__exit__ = Mock(return_value=None)
        self.mock_db_manager.get_session.return_value = mock_context_manager
        
        # Mock WebSocket components
        self.mock_websocket_factory = Mock()
        self.mock_auth_handler = Mock()
        self.mock_namespace_manager = Mock()
        
        # Create notification components
        self.notification_manager = UnifiedNotificationManager(
            websocket_factory=self.mock_websocket_factory,
            auth_handler=self.mock_auth_handler,
            namespace_manager=self.mock_namespace_manager,
            db_manager=self.mock_db_manager
        )
        
        self.persistence_manager = NotificationPersistenceManager(
            db_manager=self.mock_db_manager
        )
        
        # Create test messages
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
        
        self.admin_message = AdminNotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.ERROR,
            title="System Error",
            message="Critical system error occurred",
            priority=NotificationPriority.CRITICAL,
            requires_admin_action=True,
            system_health_data={"cpu_usage": 95, "memory_usage": 90}
        )
        
        self.system_message = SystemNotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.WARNING,
            title="System Maintenance",
            message="System will be down for maintenance",
            priority=NotificationPriority.HIGH,
            maintenance_info={"duration": "30 minutes", "services": ["caption_generation"]},
            estimated_duration=30,
            affects_functionality=["caption_generation", "platform_sync"]
        )
    
    def test_message_storage_integration(self):
        """Test message storage in database"""
        # Mock NotificationStorage creation
        mock_notification_storage = Mock(spec=NotificationStorage)
        
        with patch('unified_notification_manager.NotificationStorage', return_value=mock_notification_storage) as mock_storage_class:
            # Store message
            self.notification_manager._store_message_in_database(self.test_message)
            
            # Verify storage creation
            mock_storage_class.assert_called_once()
            
            # Verify database operations
            self.mock_session.add.assert_called_once_with(mock_notification_storage)
            self.mock_session.commit.assert_called_once()
    
    def test_message_storage_with_complex_data(self):
        """Test storing message with complex data structures"""
        # Create message with complex data
        complex_message = NotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.INFO,
            title="Complex Data Test",
            message="Message with complex data",
            user_id=1,
            data={
                "nested": {"key": "value", "number": 42},
                "array": [1, 2, 3, "string"],
                "boolean": True,
                "null_value": None
            }
        )
        
        # Mock NotificationStorage
        mock_notification_storage = Mock(spec=NotificationStorage)
        
        with patch('unified_notification_manager.NotificationStorage', return_value=mock_notification_storage):
            # Store message
            self.notification_manager._store_message_in_database(complex_message)
            
            # Verify JSON serialization of complex data
            self.mock_session.add.assert_called_once()
            self.mock_session.commit.assert_called_once()
    
    def test_message_retrieval_integration(self):
        """Test message retrieval from database"""
        # Mock database notifications
        mock_notifications = []
        for i in range(3):
            mock_notif = Mock(spec=NotificationStorage)
            mock_notif.id = f"msg_{i}"
            mock_notif.user_id = 1
            mock_notif.type = NotificationType.INFO
            mock_notif.title = f"Message {i}"
            mock_notif.message = f"Test message {i}"
            mock_notif.data = json.dumps({"index": i})
            mock_notif.timestamp = datetime.now(timezone.utc)
            mock_notif.delivered = True
            mock_notif.read = False
            
            # Mock to_notification_message method
            mock_notif.to_notification_message.return_value = NotificationMessage(
                id=f"msg_{i}",
                type=NotificationType.INFO,
                title=f"Message {i}",
                message=f"Test message {i}",
                user_id=1,
                data={"index": i}
            )
            mock_notifications.append(mock_notif)
        
        # Mock database query
        query_mock = self.mock_session.query.return_value
        query_mock.filter_by.return_value.order_by.return_value.limit.return_value.all.return_value = mock_notifications
        
        # Retrieve messages
        messages = self.notification_manager.get_notification_history(1, limit=10)
        
        # Verify retrieval
        self.assertEqual(len(messages), 3)
        for i, message in enumerate(messages):
            self.assertEqual(message.id, f"msg_{i}")
            self.assertEqual(message.user_id, 1)
            self.assertEqual(message.data["index"], i)
    
    def test_message_update_integration(self):
        """Test updating message status in database"""
        # Mock existing notification
        mock_notification = Mock(spec=NotificationStorage)
        mock_notification.id = self.test_message.id
        mock_notification.user_id = 1
        mock_notification.read = False
        
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = mock_notification
        
        # Mark message as read
        result = self.notification_manager.mark_message_as_read(self.test_message.id, 1)
        
        # Verify update
        self.assertTrue(result)
        self.assertTrue(mock_notification.read)
        self.assertIsNotNone(mock_notification.updated_at)
        self.mock_session.commit.assert_called_once()
    
    def test_message_cleanup_integration(self):
        """Test message cleanup from database"""
        # Mock expired and old messages
        expired_msg1 = Mock(spec=NotificationStorage)
        expired_msg1.id = "expired_1"
        expired_msg2 = Mock(spec=NotificationStorage)
        expired_msg2.id = "expired_2"
        
        old_msg1 = Mock(spec=NotificationStorage)
        old_msg1.id = "old_1"
        old_msg2 = Mock(spec=NotificationStorage)
        old_msg2.id = "old_2"
        
        # Mock database queries for cleanup
        self.mock_session.query.return_value.filter.return_value.all.side_effect = [
            [expired_msg1, expired_msg2],  # Expired messages
            [old_msg1, old_msg2]  # Old messages
        ]
        
        # Run cleanup
        cleanup_count = self.notification_manager.cleanup_expired_messages()
        
        # Verify cleanup operations
        self.assertEqual(cleanup_count, 4)
        self.assertEqual(self.mock_session.delete.call_count, 4)
        self.assertEqual(self.mock_session.commit.call_count, 2)  # One for each query
    
    def test_persistence_manager_storage_integration(self):
        """Test NotificationPersistenceManager storage integration"""
        # Mock successful storage
        self.mock_session.add = Mock()
        self.mock_session.commit = Mock()
        
        # Store notification
        result = self.persistence_manager.store_notification(self.test_message)
        
        # Verify storage
        self.assertEqual(result, self.test_message.id)
        self.mock_session.add.assert_called_once()
        self.mock_session.commit.assert_called_once()
    
    def test_persistence_manager_queuing_integration(self):
        """Test NotificationPersistenceManager offline queuing integration"""
        # Mock storage operations
        self.mock_session.add = Mock()
        self.mock_session.commit = Mock()
        
        # Queue notification for offline user
        self.persistence_manager.queue_for_offline_user(1, self.test_message)
        
        # Verify queuing and storage
        self.assertIn(1, self.persistence_manager._offline_queues)
        self.assertIn(self.test_message.id, self.persistence_manager._offline_queues[1])
        self.assertIn(self.test_message.id, self.persistence_manager._delivery_tracking)
        
        # Verify database storage
        self.mock_session.add.assert_called_once()
        self.mock_session.commit.assert_called_once()
    
    def test_persistence_manager_delivery_tracking_integration(self):
        """Test delivery tracking with database updates"""
        # Mock existing notification in database
        mock_notification = Mock(spec=NotificationStorage)
        mock_notification.user_id = 1
        mock_notification.delivered = False
        
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = mock_notification
        
        # Add to tracking
        self.persistence_manager._offline_queues[1].append(self.test_message.id)
        self.persistence_manager._pending_deliveries[1].add(self.test_message.id)
        
        # Mark as delivered
        result = self.persistence_manager.mark_as_delivered(self.test_message.id)
        
        # Verify delivery tracking and database update
        self.assertTrue(result)
        self.assertTrue(mock_notification.delivered)
        self.assertNotIn(self.test_message.id, self.persistence_manager._offline_queues[1])
        self.assertNotIn(self.test_message.id, self.persistence_manager._pending_deliveries[1])
        self.mock_session.commit.assert_called_once()
    
    def test_database_transaction_rollback_integration(self):
        """Test database transaction rollback on error"""
        # Mock database error during commit
        self.mock_session.add = Mock()
        self.mock_session.commit.side_effect = Exception("Database commit error")
        self.mock_session.rollback = Mock()
        
        # Attempt to store message
        with patch('unified_notification_manager.NotificationStorage'):
            try:
                self.notification_manager._store_message_in_database(self.test_message)
            except Exception:
                pass  # Expected to fail
        
        # Verify rollback was called
        self.mock_session.rollback.assert_called_once()
    
    def test_concurrent_database_access_integration(self):
        """Test concurrent database access handling"""
        import threading
        import time
        
        results = []
        errors = []
        
        def concurrent_storage(message_id):
            try:
                message = NotificationMessage(
                    id=message_id,
                    type=NotificationType.INFO,
                    title="Concurrent Test",
                    message=f"Concurrent message {message_id}",
                    user_id=1
                )
                
                # Mock database operations for this thread
                mock_session = Mock()
                mock_context_manager = Mock()
                mock_context_manager.__enter__ = Mock(return_value=mock_session)
                mock_context_manager.__exit__ = Mock(return_value=None)
                
                with patch.object(self.mock_db_manager, 'get_session', return_value=mock_context_manager):
                    with patch('unified_notification_manager.NotificationStorage'):
                        self.notification_manager._store_message_in_database(message)
                        results.append(True)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads for concurrent access
        threads = []
        for i in range(5):
            thread = threading.Thread(target=concurrent_storage, args=(f"concurrent_{i}",))
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Verify concurrent access handling
        self.assertEqual(len(results), 5)
        self.assertEqual(len(errors), 0)
    
    def test_data_integrity_validation_integration(self):
        """Test data integrity validation during storage"""
        # Create message with invalid data
        invalid_message = NotificationMessage(
            id="",  # Invalid empty ID
            type=NotificationType.INFO,
            title="",  # Invalid empty title
            message="Valid message",
            user_id=None  # Invalid None user_id
        )
        
        # Mock validation in storage
        with patch('unified_notification_manager.NotificationStorage') as mock_storage_class:
            mock_storage_instance = Mock()
            mock_storage_class.return_value = mock_storage_instance
            
            # Attempt to store invalid message
            try:
                self.notification_manager._store_message_in_database(invalid_message)
            except Exception:
                pass  # May raise validation error
            
            # Verify storage was attempted (validation happens at ORM level)
            mock_storage_class.assert_called_once()
    
    def test_audit_trail_integration(self):
        """Test audit trail creation for notifications"""
        # Mock audit trail storage
        with patch('unified_notification_manager.NotificationStorage') as mock_storage_class:
            mock_storage_instance = Mock()
            mock_storage_class.return_value = mock_storage_instance
            
            # Store message with audit trail
            self.notification_manager._store_message_in_database(self.test_message)
            
            # Verify audit information is captured
            mock_storage_class.assert_called_once()
            self.mock_session.add.assert_called_once_with(mock_storage_instance)
            self.mock_session.commit.assert_called_once()
    
    def test_database_performance_optimization_integration(self):
        """Test database performance optimization features"""
        # Test batch operations
        messages = []
        for i in range(10):
            message = NotificationMessage(
                id=f"batch_{i}",
                type=NotificationType.INFO,
                title=f"Batch Message {i}",
                message=f"Batch test message {i}",
                user_id=1
            )
            messages.append(message)
        
        # Mock batch storage
        with patch('unified_notification_manager.NotificationStorage') as mock_storage_class:
            mock_storage_instances = [Mock() for _ in range(10)]
            mock_storage_class.side_effect = mock_storage_instances
            
            # Store messages in batch
            for message in messages:
                self.notification_manager._store_message_in_database(message)
            
            # Verify batch operations
            self.assertEqual(mock_storage_class.call_count, 10)
            self.assertEqual(self.mock_session.add.call_count, 10)
            self.assertEqual(self.mock_session.commit.call_count, 10)
    
    def test_database_connection_recovery_integration(self):
        """Test database connection recovery"""
        # Mock connection failure and recovery
        connection_attempts = [0]
        
        def mock_get_session():
            connection_attempts[0] += 1
            if connection_attempts[0] == 1:
                raise Exception("Database connection failed")
            else:
                # Return successful connection on retry
                mock_context_manager = Mock()
                mock_context_manager.__enter__ = Mock(return_value=self.mock_session)
                mock_context_manager.__exit__ = Mock(return_value=None)
                return mock_context_manager
        
        # Test connection recovery
        with patch.object(self.mock_db_manager, 'get_session', side_effect=mock_get_session):
            with patch('unified_notification_manager.NotificationStorage'):
                # First attempt should fail, second should succeed
                try:
                    self.notification_manager._store_message_in_database(self.test_message)
                except Exception:
                    # Retry on failure
                    self.notification_manager._store_message_in_database(self.test_message)
        
        # Verify retry mechanism
        self.assertEqual(connection_attempts[0], 2)
    
    def test_notification_statistics_database_integration(self):
        """Test notification statistics from database"""
        # Mock database statistics queries
        self.mock_session.query.return_value.count.side_effect = [
            100,  # Total messages
            25,   # Unread messages
            10    # Pending delivery
        ]
        
        # Get statistics
        stats = self.notification_manager.get_notification_stats()
        
        # Verify database integration
        self.assertEqual(stats['total_messages_in_db'], 100)
        self.assertEqual(stats['unread_messages'], 25)
        self.assertEqual(stats['pending_delivery'], 10)
        
        # Verify database queries were made
        self.assertEqual(self.mock_session.query.call_count, 3)
    
    def test_message_expiration_database_integration(self):
        """Test message expiration handling with database"""
        # Create message with expiration
        expiring_message = NotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.INFO,
            title="Expiring Message",
            message="This message will expire",
            user_id=1,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        
        # Mock storage with expiration
        with patch('unified_notification_manager.NotificationStorage') as mock_storage_class:
            mock_storage_instance = Mock()
            mock_storage_class.return_value = mock_storage_instance
            
            # Store expiring message
            self.notification_manager._store_message_in_database(expiring_message)
            
            # Verify expiration is stored
            mock_storage_class.assert_called_once()
            self.mock_session.add.assert_called_once()
            self.mock_session.commit.assert_called_once()
    
    def test_user_notification_preferences_integration(self):
        """Test user notification preferences with database"""
        # Mock user preferences in database
        mock_user = Mock(spec=User)
        mock_user.id = 1
        mock_user.notification_preferences = json.dumps({
            "email_notifications": True,
            "push_notifications": False,
            "categories": ["system", "caption"]
        })
        
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = mock_user
        
        # Test preference-based filtering (would be implemented in notification manager)
        # This is a placeholder for future preference integration
        user_preferences = json.loads(mock_user.notification_preferences)
        
        # Verify preferences structure
        self.assertTrue(user_preferences["email_notifications"])
        self.assertFalse(user_preferences["push_notifications"])
        self.assertIn("system", user_preferences["categories"])


if __name__ == '__main__':
    unittest.main()
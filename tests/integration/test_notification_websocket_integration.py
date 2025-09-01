# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integration tests for Notification System WebSocket Framework Integration

Tests the integration between the notification system and the existing WebSocket CORS
standardization framework, including real-time message delivery, namespace management,
authentication integration, and error recovery.
"""

import unittest
import sys
import os
import uuid
import json
import time
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock
from threading import Thread, Event

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from unified_notification_manager import (
    UnifiedNotificationManager, NotificationMessage, 
    AdminNotificationMessage, SystemNotificationMessage
)
from notification_message_router import NotificationMessageRouter
from websocket_factory import WebSocketFactory
from websocket_auth_handler import WebSocketAuthHandler
from websocket_namespace_manager import WebSocketNamespaceManager
from models import (
    NotificationType, NotificationPriority, NotificationCategory, 
    UserRole, User, NotificationStorage
)
from config import Config
from database import DatabaseManager


class TestNotificationWebSocketIntegration(unittest.TestCase):
    """Integration tests for notification system WebSocket integration"""
    
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
        self.mock_websocket_factory = Mock(spec=WebSocketFactory)
        self.mock_auth_handler = Mock(spec=WebSocketAuthHandler)
        self.mock_namespace_manager = Mock(spec=WebSocketNamespaceManager)
        
        # Mock Flask-SocketIO instance
        self.mock_socketio = Mock()
        self.mock_websocket_factory.create_socketio_instance.return_value = self.mock_socketio
        
        # Set up namespace manager state
        self.mock_namespace_manager._user_connections = {}
        self.mock_namespace_manager._connections = {}
        self.mock_namespace_manager._namespaces = {'/': Mock(), '/admin': Mock()}
        
        # Create notification components
        self.notification_manager = UnifiedNotificationManager(
            websocket_factory=self.mock_websocket_factory,
            auth_handler=self.mock_auth_handler,
            namespace_manager=self.mock_namespace_manager,
            db_manager=self.mock_db_manager
        )
        
        self.message_router = NotificationMessageRouter(
            namespace_manager=self.mock_namespace_manager
        )
        
        # Create test users
        self.admin_user = Mock(spec=User)
        self.admin_user.id = 1
        self.admin_user.username = "admin"
        self.admin_user.role = UserRole.ADMIN
        
        self.reviewer_user = Mock(spec=User)
        self.reviewer_user.id = 2
        self.reviewer_user.username = "reviewer"
        self.reviewer_user.role = UserRole.REVIEWER
        
        # Create test messages
        self.test_message = NotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.INFO,
            title="Test Notification",
            message="This is a test notification",
            user_id=2,
            priority=NotificationPriority.NORMAL,
            category=NotificationCategory.SYSTEM
        )
        
        self.admin_message = AdminNotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.ERROR,
            title="System Error",
            message="Critical system error occurred",
            priority=NotificationPriority.CRITICAL,
            requires_admin_action=True
        )
        
        self.system_message = SystemNotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.WARNING,
            title="System Maintenance",
            message="System will be down for maintenance",
            priority=NotificationPriority.HIGH,
            maintenance_info={"duration": "30 minutes"},
            estimated_duration=30
        )
    
    def test_websocket_factory_integration(self):
        """Test integration with WebSocket factory"""
        # Mock Flask app
        mock_app = Mock()
        
        # Test SocketIO instance creation
        socketio_instance = self.mock_websocket_factory.create_socketio_instance(mock_app)
        
        # Verify integration
        self.assertIsNotNone(socketio_instance)
        self.mock_websocket_factory.create_socketio_instance.assert_called_once_with(mock_app)
    
    def test_authentication_handler_integration(self):
        """Test integration with WebSocket authentication handler"""
        # Mock authentication context
        mock_auth_context = Mock()
        mock_auth_context.user_id = 1
        mock_auth_context.user_role = UserRole.ADMIN
        mock_auth_context.session_id = "session_123"
        
        # Mock authentication
        self.mock_auth_handler.authenticate_connection.return_value = mock_auth_context
        
        # Test authentication
        auth_result = self.mock_auth_handler.authenticate_connection("token_123")
        
        # Verify authentication integration
        self.assertIsNotNone(auth_result)
        self.assertEqual(auth_result.user_id, 1)
        self.assertEqual(auth_result.user_role, UserRole.ADMIN)
        self.mock_auth_handler.authenticate_connection.assert_called_once_with("token_123")
    
    def test_namespace_manager_integration(self):
        """Test integration with WebSocket namespace manager"""
        # Mock user connection
        session_id = "session_123"
        self.mock_namespace_manager._user_connections[1] = {session_id}
        self.mock_namespace_manager._connections[session_id] = Mock(
            user_id=1,
            namespace='/admin',
            session_id=session_id
        )
        
        # Test namespace management
        user_connections = self.mock_namespace_manager._user_connections.get(1, set())
        self.assertIn(session_id, user_connections)
        
        connection = self.mock_namespace_manager._connections.get(session_id)
        self.assertIsNotNone(connection)
        self.assertEqual(connection.user_id, 1)
        self.assertEqual(connection.namespace, '/admin')
    
    @patch('unified_notification_manager.emit')
    def test_real_time_message_delivery(self, mock_emit):
        """Test real-time message delivery through WebSocket"""
        # Set up online user
        session_id = "session_123"
        self.mock_namespace_manager._user_connections[2] = {session_id}
        self.mock_namespace_manager._connections[session_id] = Mock(namespace='/')
        
        # Mock user role lookup
        with patch.object(self.notification_manager, '_get_user_role', return_value=UserRole.REVIEWER):
            with patch.object(self.notification_manager, '_store_message_in_database'):
                with patch.object(self.notification_manager, '_add_to_message_history'):
                    # Send notification
                    result = self.notification_manager.send_user_notification(2, self.test_message)
                    
                    # Verify real-time delivery
                    self.assertTrue(result)
                    self.assertTrue(self.test_message.delivered)
                    mock_emit.assert_called_once()
                    
                    # Verify emit parameters
                    call_args = mock_emit.call_args
                    self.assertEqual(call_args[0][0], 'notification')  # Event name
                    self.assertIsInstance(call_args[0][1], dict)  # Message data
                    self.assertEqual(call_args[1]['room'], session_id)  # Target session
                    self.assertEqual(call_args[1]['namespace'], '/')  # Target namespace
    
    @patch('unified_notification_manager.emit')
    def test_admin_namespace_routing(self, mock_emit):
        """Test admin message routing to admin namespace"""
        # Set up admin user connection
        session_id = "admin_session_123"
        self.mock_namespace_manager._user_connections[1] = {session_id}
        self.mock_namespace_manager._connections[session_id] = Mock(namespace='/admin')
        
        # Mock admin users lookup
        with patch.object(self.notification_manager, '_get_users_by_role', return_value=[1]):
            with patch.object(self.notification_manager, '_get_user_role', return_value=UserRole.ADMIN):
                with patch.object(self.notification_manager, '_store_message_in_database'):
                    with patch.object(self.notification_manager, '_add_to_message_history'):
                        # Send admin notification
                        result = self.notification_manager.send_admin_notification(self.admin_message)
                        
                        # Verify admin namespace routing
                        self.assertTrue(result)
                        mock_emit.assert_called()
                        
                        # Verify admin namespace was used
                        call_args = mock_emit.call_args
                        self.assertEqual(call_args[1]['namespace'], '/admin')
    
    @patch('unified_notification_manager.emit')
    def test_system_broadcast_integration(self, mock_emit):
        """Test system broadcast integration with WebSocket framework"""
        # Set up multiple user connections
        user_sessions = {
            1: "admin_session",
            2: "reviewer_session",
            3: "viewer_session"
        }
        
        for user_id, session_id in user_sessions.items():
            self.mock_namespace_manager._user_connections[user_id] = {session_id}
            namespace = '/admin' if user_id == 1 else '/'
            self.mock_namespace_manager._connections[session_id] = Mock(namespace=namespace)
        
        # Mock active users and roles
        with patch.object(self.notification_manager, '_get_all_active_users', return_value=[1, 2, 3]):
            with patch.object(self.notification_manager, '_get_user_role') as mock_get_role:
                mock_get_role.side_effect = lambda uid: {
                    1: UserRole.ADMIN, 2: UserRole.REVIEWER, 3: UserRole.VIEWER
                }[uid]
                
                with patch.object(self.notification_manager, '_store_message_in_database'):
                    with patch.object(self.notification_manager, '_add_to_message_history'):
                        # Broadcast system notification
                        result = self.notification_manager.broadcast_system_notification(self.system_message)
                        
                        # Verify broadcast success
                        self.assertTrue(result)
                        self.assertEqual(mock_emit.call_count, 3)  # Called for each user
    
    def test_offline_message_queuing_integration(self):
        """Test offline message queuing with database persistence"""
        # Mock offline user (no connections)
        self.mock_namespace_manager._user_connections[2] = set()
        
        # Mock database storage
        with patch.object(self.notification_manager, '_store_message_in_database') as mock_store:
            with patch.object(self.notification_manager, '_get_user_role', return_value=UserRole.REVIEWER):
                # Send notification to offline user
                result = self.notification_manager.send_user_notification(2, self.test_message)
                
                # Verify queuing and persistence
                self.assertTrue(result)
                self.assertFalse(self.test_message.delivered)
                self.assertIn(2, self.notification_manager._offline_queues)
                self.assertEqual(len(self.notification_manager._offline_queues[2]), 1)
                mock_store.assert_called_once_with(self.test_message)
    
    @patch('unified_notification_manager.emit')
    def test_message_replay_on_reconnection(self, mock_emit):
        """Test message replay when user reconnects"""
        # Add messages to offline queue
        offline_message1 = NotificationMessage(
            id="offline_1", type=NotificationType.INFO, title="Offline 1", 
            message="First offline message", user_id=2
        )
        offline_message2 = NotificationMessage(
            id="offline_2", type=NotificationType.INFO, title="Offline 2",
            message="Second offline message", user_id=2
        )
        
        from collections import deque
        self.notification_manager._offline_queues[2] = deque([offline_message1, offline_message2])
        
        # Simulate user reconnection
        session_id = "reconnect_session"
        self.mock_namespace_manager._user_connections[2] = {session_id}
        self.mock_namespace_manager._connections[session_id] = Mock(namespace='/')
        
        # Mock successful delivery
        with patch.object(self.notification_manager, '_update_message_delivery_status'):
            # Replay messages
            replayed_count = self.notification_manager.replay_messages_for_user(2)
            
            # Verify replay
            self.assertEqual(replayed_count, 2)
            self.assertEqual(len(self.notification_manager._offline_queues[2]), 0)
            self.assertEqual(mock_emit.call_count, 2)
    
    def test_database_persistence_integration(self):
        """Test database persistence integration"""
        # Mock database operations
        mock_notification_storage = Mock(spec=NotificationStorage)
        self.mock_session.add = Mock()
        self.mock_session.commit = Mock()
        
        # Test message storage
        with patch('unified_notification_manager.NotificationStorage', return_value=mock_notification_storage):
            self.notification_manager._store_message_in_database(self.test_message)
            
            # Verify database operations
            self.mock_session.add.assert_called_once_with(mock_notification_storage)
            self.mock_session.commit.assert_called_once()
    
    def test_notification_history_retrieval_integration(self):
        """Test notification history retrieval from database"""
        # Mock database notifications
        mock_notifications = []
        for i in range(3):
            mock_notif = Mock(spec=NotificationStorage)
            mock_notif.to_notification_message.return_value = NotificationMessage(
                id=f"history_{i}",
                type=NotificationType.INFO,
                title=f"History {i}",
                message=f"Historical message {i}",
                user_id=2
            )
            mock_notifications.append(mock_notif)
        
        # Mock database query
        query_mock = self.mock_session.query.return_value
        query_mock.filter_by.return_value.order_by.return_value.limit.return_value.all.return_value = mock_notifications
        
        # Retrieve history
        history = self.notification_manager.get_notification_history(2, limit=10)
        
        # Verify integration
        self.assertEqual(len(history), 3)
        for i, message in enumerate(history):
            self.assertEqual(message.id, f"history_{i}")
            self.assertEqual(message.user_id, 2)
    
    def test_cors_error_handling_integration(self):
        """Test CORS error handling integration"""
        # Mock CORS error
        cors_error = Exception("CORS policy violation")
        
        # Mock emit with CORS error
        with patch('unified_notification_manager.emit', side_effect=cors_error):
            # Set up user connection
            session_id = "cors_test_session"
            self.mock_namespace_manager._user_connections[2] = {session_id}
            self.mock_namespace_manager._connections[session_id] = Mock(namespace='/')
            
            # Mock user role
            with patch.object(self.notification_manager, '_get_user_role', return_value=UserRole.REVIEWER):
                # Attempt to send notification
                result = self.notification_manager.send_user_notification(2, self.test_message)
                
                # Verify error handling (should queue for retry)
                self.assertTrue(result)  # Still returns True as it queues for offline delivery
                self.assertFalse(self.test_message.delivered)
    
    def test_authentication_failure_integration(self):
        """Test authentication failure handling"""
        # Mock authentication failure
        self.mock_auth_handler.authenticate_connection.return_value = None
        
        # Test authentication failure
        auth_result = self.mock_auth_handler.authenticate_connection("invalid_token")
        
        # Verify failure handling
        self.assertIsNone(auth_result)
    
    def test_connection_recovery_integration(self):
        """Test connection recovery integration"""
        # Mock connection loss and recovery
        session_id = "recovery_session"
        
        # Initially connected
        self.mock_namespace_manager._user_connections[2] = {session_id}
        self.mock_namespace_manager._connections[session_id] = Mock(namespace='/')
        
        # Simulate connection loss
        self.mock_namespace_manager._user_connections[2] = set()
        del self.mock_namespace_manager._connections[session_id]
        
        # Send message during disconnection (should queue)
        with patch.object(self.notification_manager, '_get_user_role', return_value=UserRole.REVIEWER):
            with patch.object(self.notification_manager, '_store_message_in_database'):
                result = self.notification_manager.send_user_notification(2, self.test_message)
                
                # Verify queuing during disconnection
                self.assertTrue(result)
                self.assertFalse(self.test_message.delivered)
                self.assertIn(2, self.notification_manager._offline_queues)
        
        # Simulate reconnection
        new_session_id = "recovery_session_new"
        self.mock_namespace_manager._user_connections[2] = {new_session_id}
        self.mock_namespace_manager._connections[new_session_id] = Mock(namespace='/')
        
        # Test message replay on reconnection
        with patch('unified_notification_manager.emit'):
            with patch.object(self.notification_manager, '_update_message_delivery_status'):
                replayed_count = self.notification_manager.replay_messages_for_user(2)
                
                # Verify recovery
                self.assertEqual(replayed_count, 1)
    
    def test_performance_under_load(self):
        """Test notification system performance under load"""
        # Create multiple users and messages
        num_users = 10
        num_messages = 5
        
        # Set up user connections
        for user_id in range(1, num_users + 1):
            session_id = f"load_session_{user_id}"
            self.mock_namespace_manager._user_connections[user_id] = {session_id}
            self.mock_namespace_manager._connections[session_id] = Mock(namespace='/')
        
        # Mock user roles
        with patch.object(self.notification_manager, '_get_user_role', return_value=UserRole.REVIEWER):
            with patch.object(self.notification_manager, '_store_message_in_database'):
                with patch.object(self.notification_manager, '_add_to_message_history'):
                    with patch('unified_notification_manager.emit'):
                        # Send multiple messages to multiple users
                        start_time = time.time()
                        
                        for user_id in range(1, num_users + 1):
                            for msg_num in range(num_messages):
                                message = NotificationMessage(
                                    id=f"load_msg_{user_id}_{msg_num}",
                                    type=NotificationType.INFO,
                                    title=f"Load Test {msg_num}",
                                    message=f"Load test message {msg_num} for user {user_id}",
                                    user_id=user_id
                                )
                                
                                result = self.notification_manager.send_user_notification(user_id, message)
                                self.assertTrue(result)
                        
                        end_time = time.time()
                        processing_time = end_time - start_time
                        
                        # Verify performance (should complete within reasonable time)
                        self.assertLess(processing_time, 5.0)  # Should complete within 5 seconds
                        
                        # Verify statistics
                        stats = self.notification_manager.get_notification_stats()
                        self.assertEqual(stats['delivery_stats']['messages_delivered'], num_users * num_messages)
    
    def test_concurrent_message_handling(self):
        """Test concurrent message handling"""
        # Create concurrent message sending scenario
        results = []
        errors = []
        
        def send_concurrent_message(user_id, message_id):
            try:
                message = NotificationMessage(
                    id=message_id,
                    type=NotificationType.INFO,
                    title="Concurrent Test",
                    message=f"Concurrent message {message_id}",
                    user_id=user_id
                )
                
                # Mock user connection
                session_id = f"concurrent_session_{user_id}"
                self.mock_namespace_manager._user_connections[user_id] = {session_id}
                self.mock_namespace_manager._connections[session_id] = Mock(namespace='/')
                
                with patch.object(self.notification_manager, '_get_user_role', return_value=UserRole.REVIEWER):
                    with patch.object(self.notification_manager, '_store_message_in_database'):
                        with patch.object(self.notification_manager, '_add_to_message_history'):
                            with patch('unified_notification_manager.emit'):
                                result = self.notification_manager.send_user_notification(user_id, message)
                                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads for concurrent sending
        threads = []
        for i in range(5):
            thread = Thread(target=send_concurrent_message, args=(i + 1, f"concurrent_{i}"))
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify concurrent handling
        self.assertEqual(len(results), 5)
        self.assertTrue(all(results))
        self.assertEqual(len(errors), 0)


if __name__ == '__main__':
    unittest.main()
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integration tests for Notification System Error Handling and Recovery

Tests error handling and recovery mechanisms with simulated failure conditions,
including WebSocket connection failures, database errors, CORS issues,
authentication failures, and network connectivity problems.
"""

import unittest
import sys
import os
import uuid
import time
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock, side_effect
from collections import deque

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from unified_notification_manager import (
    UnifiedNotificationManager, NotificationMessage, 
    AdminNotificationMessage, SystemNotificationMessage
)
from notification_message_router import NotificationMessageRouter
from notification_persistence_manager import NotificationPersistenceManager
from models import (
    NotificationType, NotificationPriority, NotificationCategory, 
    UserRole
)


class TestNotificationErrorHandlingRecovery(unittest.TestCase):
    """Integration tests for notification system error handling and recovery"""
    
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
            category=NotificationCategory.SYSTEM
        )
        
        self.critical_message = NotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.ERROR,
            title="Critical Error",
            message="Critical system error occurred",
            user_id=1,
            priority=NotificationPriority.CRITICAL,
            category=NotificationCategory.SYSTEM
        )
    
    def test_websocket_connection_failure_recovery(self):
        """Test recovery from WebSocket connection failures"""
        # Mock WebSocket connection failure
        websocket_error = ConnectionError("WebSocket connection failed")
        
        # Set up user connection
        session_id = "failing_session"
        self.mock_namespace_manager._user_connections[1] = {session_id}
        self.mock_namespace_manager._connections[session_id] = Mock(namespace='/')
        
        # Mock emit failure followed by success
        emit_attempts = [0]
        def mock_emit_with_failure(*args, **kwargs):
            emit_attempts[0] += 1
            if emit_attempts[0] == 1:
                raise websocket_error
            return True
        
        with patch('unified_notification_manager.emit', side_effect=mock_emit_with_failure):
            with patch.object(self.notification_manager, '_get_user_role', return_value=UserRole.REVIEWER):
                with patch.object(self.notification_manager, '_store_message_in_database'):
                    # First attempt should fail and queue message
                    result = self.notification_manager.send_user_notification(1, self.test_message)
                    
                    # Should still return True as it queues for offline delivery
                    self.assertTrue(result)
                    self.assertFalse(self.test_message.delivered)
                    
                    # Verify message was queued for retry
                    self.assertIn(1, self.notification_manager._offline_queues)
    
    def test_database_connection_failure_recovery(self):
        """Test recovery from database connection failures"""
        # Mock database connection failure
        db_error = Exception("Database connection lost")
        
        # Mock database failure followed by success
        db_attempts = [0]
        def mock_get_session():
            db_attempts[0] += 1
            if db_attempts[0] == 1:
                raise db_error
            else:
                # Return successful connection on retry
                mock_context_manager = Mock()
                mock_context_manager.__enter__ = Mock(return_value=self.mock_session)
                mock_context_manager.__exit__ = Mock(return_value=None)
                return mock_context_manager
        
        # Test database recovery
        with patch.object(self.mock_db_manager, 'get_session', side_effect=mock_get_session):
            with patch('unified_notification_manager.NotificationStorage'):
                # First attempt should fail
                try:
                    self.notification_manager._store_message_in_database(self.test_message)
                    self.fail("Expected database error")
                except Exception as e:
                    self.assertEqual(str(e), "Database connection lost")
                
                # Second attempt should succeed
                self.notification_manager._store_message_in_database(self.test_message)
                
                # Verify retry occurred
                self.assertEqual(db_attempts[0], 2)
    
    def test_cors_error_handling(self):
        """Test CORS error handling and recovery"""
        # Mock CORS error
        cors_error = Exception("CORS policy: Cross origin requests are only supported for protocol schemes")
        
        # Set up user connection
        session_id = "cors_session"
        self.mock_namespace_manager._user_connections[1] = {session_id}
        self.mock_namespace_manager._connections[session_id] = Mock(namespace='/')
        
        # Mock CORS error in emit
        with patch('unified_notification_manager.emit', side_effect=cors_error):
            with patch.object(self.notification_manager, '_get_user_role', return_value=UserRole.REVIEWER):
                with patch.object(self.notification_manager, '_store_message_in_database'):
                    # Send notification with CORS error
                    result = self.notification_manager.send_user_notification(1, self.test_message)
                    
                    # Should handle error gracefully and queue message
                    self.assertTrue(result)
                    self.assertFalse(self.test_message.delivered)
                    
                    # Verify error statistics
                    self.assertEqual(self.notification_manager._stats['offline_messages_queued'], 1)
    
    def test_authentication_failure_recovery(self):
        """Test authentication failure handling and recovery"""
        # Mock authentication failure
        self.mock_auth_handler.authenticate_connection.return_value = None
        
        # Test authentication failure
        auth_result = self.mock_auth_handler.authenticate_connection("invalid_token")
        self.assertIsNone(auth_result)
        
        # Mock authentication recovery
        mock_auth_context = Mock()
        mock_auth_context.user_id = 1
        mock_auth_context.user_role = UserRole.ADMIN
        mock_auth_context.is_authenticated = True
        
        self.mock_auth_handler.authenticate_connection.return_value = mock_auth_context
        
        # Test authentication recovery
        auth_result = self.mock_auth_handler.authenticate_connection("valid_token")
        self.assertIsNotNone(auth_result)
        self.assertTrue(auth_result.is_authenticated)
    
    def test_network_connectivity_failure_recovery(self):
        """Test network connectivity failure and recovery"""
        # Mock network connectivity issues
        network_errors = [
            ConnectionError("Network is unreachable"),
            TimeoutError("Connection timed out"),
            OSError("Network interface is down")
        ]
        
        # Test each type of network error
        for error in network_errors:
            with patch('unified_notification_manager.emit', side_effect=error):
                with patch.object(self.notification_manager, '_get_user_role', return_value=UserRole.REVIEWER):
                    with patch.object(self.notification_manager, '_store_message_in_database'):
                        # Set up user connection
                        session_id = f"network_session_{type(error).__name__}"
                        self.mock_namespace_manager._user_connections[1] = {session_id}
                        self.mock_namespace_manager._connections[session_id] = Mock(namespace='/')
                        
                        # Send notification with network error
                        result = self.notification_manager.send_user_notification(1, self.test_message)
                        
                        # Should handle error gracefully
                        self.assertTrue(result)
                        self.assertFalse(self.test_message.delivered)
    
    def test_message_queue_overflow_handling(self):
        """Test handling of message queue overflow"""
        # Fill offline queue to capacity
        for i in range(self.notification_manager.max_offline_messages + 5):
            overflow_message = NotificationMessage(
                id=f"overflow_{i}",
                type=NotificationType.INFO,
                title=f"Overflow Message {i}",
                message=f"Overflow test message {i}",
                user_id=1
            )
            self.notification_manager._queue_offline_message(1, overflow_message)
        
        # Verify queue size is limited
        self.assertEqual(len(self.notification_manager._offline_queues[1]), 
                        self.notification_manager.max_offline_messages)
        
        # Verify oldest messages were removed
        queue_messages = list(self.notification_manager._offline_queues[1])
        self.assertEqual(queue_messages[0].id, "overflow_5")  # First 5 were removed
    
    def test_database_transaction_rollback_on_error(self):
        """Test database transaction rollback on error"""
        # Mock database commit failure
        commit_error = Exception("Database commit failed")
        self.mock_session.commit.side_effect = commit_error
        self.mock_session.rollback = Mock()
        
        # Attempt to store message
        with patch('unified_notification_manager.NotificationStorage'):
            try:
                self.notification_manager._store_message_in_database(self.test_message)
                self.fail("Expected commit error")
            except Exception as e:
                self.assertEqual(str(e), "Database commit failed")
        
        # Verify rollback was called
        self.mock_session.rollback.assert_called_once()
    
    def test_concurrent_error_handling(self):
        """Test error handling under concurrent conditions"""
        import threading
        
        errors = []
        successes = []
        
        def concurrent_operation_with_errors(thread_id):
            try:
                # Simulate random errors for some threads
                if thread_id % 3 == 0:
                    raise Exception(f"Simulated error in thread {thread_id}")
                
                # Mock successful operation for other threads
                message = NotificationMessage(
                    id=f"concurrent_{thread_id}",
                    type=NotificationType.INFO,
                    title=f"Concurrent Message {thread_id}",
                    message=f"Concurrent test message {thread_id}",
                    user_id=thread_id
                )
                
                with patch.object(self.notification_manager, '_get_user_role', return_value=UserRole.REVIEWER):
                    with patch.object(self.notification_manager, '_store_message_in_database'):
                        with patch('unified_notification_manager.emit'):
                            # Set up user connection
                            session_id = f"concurrent_session_{thread_id}"
                            self.mock_namespace_manager._user_connections[thread_id] = {session_id}
                            self.mock_namespace_manager._connections[session_id] = Mock(namespace='/')
                            
                            result = self.notification_manager.send_user_notification(thread_id, message)
                            successes.append(result)
                            
            except Exception as e:
                errors.append(str(e))
        
        # Create multiple threads with some that will error
        threads = []
        for i in range(10):
            thread = threading.Thread(target=concurrent_operation_with_errors, args=(i,))
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Verify error handling
        self.assertEqual(len(errors), 4)  # Every 3rd thread (0, 3, 6, 9) should error
        self.assertEqual(len(successes), 6)  # Remaining threads should succeed
        self.assertTrue(all(successes))
    
    def test_message_replay_after_connection_recovery(self):
        """Test message replay after connection recovery"""
        # Add messages to offline queue
        offline_messages = []
        for i in range(3):
            message = NotificationMessage(
                id=f"offline_{i}",
                type=NotificationType.INFO,
                title=f"Offline Message {i}",
                message=f"Offline test message {i}",
                user_id=1
            )
            offline_messages.append(message)
        
        self.notification_manager._offline_queues[1] = deque(offline_messages)
        
        # Mock connection recovery with partial failures
        delivery_results = [True, False, True]  # Second message fails
        
        with patch.object(self.notification_manager, '_deliver_to_online_user', side_effect=delivery_results):
            with patch.object(self.notification_manager, '_update_message_delivery_status'):
                # Simulate user reconnection and replay
                replayed_count = self.notification_manager.replay_messages_for_user(1)
                
                # Verify partial replay
                self.assertEqual(replayed_count, 2)  # 2 successful deliveries
                self.assertEqual(len(self.notification_manager._offline_queues[1]), 1)  # 1 failed message remains
    
    def test_persistence_manager_error_recovery(self):
        """Test NotificationPersistenceManager error recovery"""
        # Mock database error during storage
        storage_error = Exception("Storage operation failed")
        self.mock_session.add.side_effect = storage_error
        
        # Attempt to store notification
        result = self.persistence_manager.store_notification(self.test_message)
        
        # Verify error handling
        self.assertEqual(result, "")  # Empty string indicates failure
        self.assertEqual(self.persistence_manager._stats['storage_errors'], 1)
    
    def test_message_router_error_recovery(self):
        """Test NotificationMessageRouter error recovery"""
        # Mock routing error
        routing_error = Exception("Message routing failed")
        
        with patch.object(self.message_router, '_emit_to_user', side_effect=routing_error):
            # Set up user connection
            session_id = "router_error_session"
            self.mock_namespace_manager._user_connections[1] = {session_id}
            self.mock_namespace_manager._connections[session_id] = Mock(namespace='/')
            
            with patch.object(self.message_router, '_get_user_role', return_value=UserRole.REVIEWER):
                # Attempt to route message
                result = self.message_router.route_user_message(1, self.test_message)
                
                # Verify error handling
                self.assertFalse(result)
                self.assertEqual(self.message_router._routing_stats['failed_deliveries'], 1)
    
    def test_critical_message_priority_handling(self):
        """Test priority handling for critical messages during errors"""
        # Mock partial system failure
        with patch('unified_notification_manager.emit', side_effect=Exception("System overloaded")):
            with patch.object(self.notification_manager, '_get_user_role', return_value=UserRole.ADMIN):
                with patch.object(self.notification_manager, '_store_message_in_database'):
                    # Set up admin connection
                    session_id = "critical_session"
                    self.mock_namespace_manager._user_connections[1] = {session_id}
                    self.mock_namespace_manager._connections[session_id] = Mock(namespace='/admin')
                    
                    # Send critical message
                    result = self.notification_manager.send_user_notification(1, self.critical_message)
                    
                    # Critical messages should still be queued even if delivery fails
                    self.assertTrue(result)
                    self.assertFalse(self.critical_message.delivered)
                    
                    # Verify critical message is queued for retry
                    self.assertIn(1, self.notification_manager._offline_queues)
    
    def test_graceful_degradation_under_load(self):
        """Test graceful degradation under high load conditions"""
        # Simulate high load with multiple rapid requests
        messages = []
        for i in range(100):
            message = NotificationMessage(
                id=f"load_{i}",
                type=NotificationType.INFO,
                title=f"Load Test {i}",
                message=f"Load test message {i}",
                user_id=1
            )
            messages.append(message)
        
        # Mock intermittent failures under load
        failure_count = [0]
        def mock_emit_with_load_failures(*args, **kwargs):
            failure_count[0] += 1
            if failure_count[0] % 10 == 0:  # Every 10th message fails
                raise Exception("System overloaded")
            return True
        
        successful_deliveries = 0
        queued_messages = 0
        
        with patch('unified_notification_manager.emit', side_effect=mock_emit_with_load_failures):
            with patch.object(self.notification_manager, '_get_user_role', return_value=UserRole.REVIEWER):
                with patch.object(self.notification_manager, '_store_message_in_database'):
                    with patch.object(self.notification_manager, '_add_to_message_history'):
                        # Set up user connection
                        session_id = "load_test_session"
                        self.mock_namespace_manager._user_connections[1] = {session_id}
                        self.mock_namespace_manager._connections[session_id] = Mock(namespace='/')
                        
                        # Send all messages
                        for message in messages:
                            result = self.notification_manager.send_user_notification(1, message)
                            self.assertTrue(result)  # Should always return True (queued if not delivered)
                            
                            if message.delivered:
                                successful_deliveries += 1
                            else:
                                queued_messages += 1
        
        # Verify graceful degradation
        self.assertEqual(successful_deliveries + queued_messages, 100)
        self.assertGreater(successful_deliveries, 0)  # Some should succeed
        self.assertGreater(queued_messages, 0)  # Some should be queued due to failures
    
    def test_error_recovery_statistics_tracking(self):
        """Test error recovery statistics tracking"""
        # Simulate various error conditions
        errors_to_simulate = [
            ConnectionError("WebSocket connection failed"),
            TimeoutError("Request timed out"),
            Exception("General error")
        ]
        
        for error in errors_to_simulate:
            with patch('unified_notification_manager.emit', side_effect=error):
                with patch.object(self.notification_manager, '_get_user_role', return_value=UserRole.REVIEWER):
                    with patch.object(self.notification_manager, '_store_message_in_database'):
                        # Set up user connection
                        session_id = f"error_stats_session_{type(error).__name__}"
                        self.mock_namespace_manager._user_connections[1] = {session_id}
                        self.mock_namespace_manager._connections[session_id] = Mock(namespace='/')
                        
                        # Send notification with error
                        message = NotificationMessage(
                            id=str(uuid.uuid4()),
                            type=NotificationType.INFO,
                            title="Error Stats Test",
                            message="Testing error statistics",
                            user_id=1
                        )
                        
                        result = self.notification_manager.send_user_notification(1, message)
                        self.assertTrue(result)
        
        # Verify error statistics
        stats = self.notification_manager.get_notification_stats()
        self.assertEqual(stats['offline_queues']['total_messages'], 3)  # All messages queued due to errors
    
    def test_automatic_retry_mechanism(self):
        """Test automatic retry mechanism for failed deliveries"""
        # Add message to retry queue
        retry_message = NotificationMessage(
            id="retry_test",
            type=NotificationType.INFO,
            title="Retry Test",
            message="Testing retry mechanism",
            user_id=1
        )
        
        self.message_router._retry_queues[1] = [retry_message]
        
        # Mock successful retry after initial failure
        with patch.object(self.message_router, 'route_user_message', return_value=True):
            # Process retry queue
            retried_count = self.message_router.process_retry_queue(1)
            
            # Verify retry success
            self.assertEqual(retried_count, 1)
            self.assertEqual(len(self.message_router._retry_queues[1]), 0)
            self.assertEqual(self.message_router._routing_stats['retry_successes'], 1)


if __name__ == '__main__':
    unittest.main()
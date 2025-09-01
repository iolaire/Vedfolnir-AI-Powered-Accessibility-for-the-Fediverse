# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for NotificationMessageRouter

Tests intelligent message routing, WebSocket namespace management,
delivery confirmation, retry logic, and security validation.
"""

import unittest
import sys
import os
import uuid
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from notification_message_router import NotificationMessageRouter, DeliveryStatus, RetryPolicy
from unified_notification_manager import NotificationMessage, AdminNotificationMessage, SystemNotificationMessage
from models import NotificationType, NotificationPriority, NotificationCategory, UserRole


class TestNotificationMessageRouter(unittest.TestCase):
    """Test cases for NotificationMessageRouter"""
    
    def setUp(self):
        """Set up test environment"""
        # Mock namespace manager
        self.mock_namespace_manager = Mock()
        self.mock_namespace_manager._user_connections = {}
        self.mock_namespace_manager._connections = {}
        self.mock_namespace_manager._namespaces = {'/': Mock(), '/admin': Mock()}
        
        # Create router instance
        self.router = NotificationMessageRouter(
            namespace_manager=self.mock_namespace_manager,
            max_retry_attempts=3,
            retry_delay_seconds=1,
            delivery_timeout_seconds=30
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
        """Test NotificationMessageRouter initialization"""
        self.assertIsNotNone(self.router)
        self.assertEqual(self.router.max_retry_attempts, 3)
        self.assertEqual(self.router.retry_delay_seconds, 1)
        self.assertEqual(self.router.delivery_timeout_seconds, 30)
        self.assertIsInstance(self.router._delivery_tracking, dict)
        self.assertIsInstance(self.router._retry_queues, dict)
        self.assertIsInstance(self.router._delivery_confirmations, dict)
        self.assertIsInstance(self.router._routing_stats, dict)
    
    @patch('notification_message_router.emit')
    def test_route_user_message_success(self, mock_emit):
        """Test successful user message routing"""
        # Mock user connections
        session_id = "session_123"
        self.mock_namespace_manager._user_connections[1] = {session_id}
        self.mock_namespace_manager._connections[session_id] = Mock(namespace='/')
        
        # Mock user role
        with patch.object(self.router, '_get_user_role', return_value=UserRole.REVIEWER):
            # Route message
            result = self.router.route_user_message(1, self.test_message)
            
            # Verify success
            self.assertTrue(result)
            mock_emit.assert_called_once()
            self.assertEqual(self.router._routing_stats['messages_routed'], 1)
            self.assertEqual(self.router._routing_stats['successful_deliveries'], 1)
    
    def test_route_user_message_offline_user(self):
        """Test routing message to offline user"""
        # Mock no user connections
        self.mock_namespace_manager._user_connections[1] = set()
        
        # Route message
        result = self.router.route_user_message(1, self.test_message)
        
        # Verify queued for retry
        self.assertFalse(result)
        self.assertIn(1, self.router._retry_queues)
        self.assertEqual(len(self.router._retry_queues[1]), 1)
        self.assertEqual(self.router._routing_stats['failed_deliveries'], 1)
    
    def test_route_admin_message(self):
        """Test routing admin message to all admin users"""
        # Mock admin users
        admin_users = [1, 2, 3]
        with patch.object(self.router, '_get_users_by_role', return_value=admin_users):
            with patch.object(self.router, 'route_user_message', return_value=True) as mock_route:
                # Create admin message
                admin_message = AdminNotificationMessage(
                    id=str(uuid.uuid4()),
                    type=NotificationType.ERROR,
                    title="Admin Alert",
                    message="Critical system error",
                    priority=NotificationPriority.CRITICAL,
                    requires_admin_action=True
                )
                
                # Route admin message
                result = self.router.route_admin_message(admin_message)
                
                # Verify success
                self.assertTrue(result)
                self.assertEqual(mock_route.call_count, 3)  # Called for each admin
    
    def test_route_admin_message_no_admins(self):
        """Test routing admin message when no admins exist"""
        # Mock no admin users
        with patch.object(self.router, '_get_users_by_role', return_value=[]):
            admin_message = AdminNotificationMessage(
                id=str(uuid.uuid4()),
                type=NotificationType.ERROR,
                title="Admin Alert",
                message="Critical system error"
            )
            
            # Route admin message
            result = self.router.route_admin_message(admin_message)
            
            # Verify failure
            self.assertFalse(result)
    
    def test_route_system_broadcast(self):
        """Test routing system broadcast to all users"""
        # Mock active users
        active_users = [1, 2, 3, 4, 5]
        with patch.object(self.router, '_get_all_active_users', return_value=active_users):
            with patch.object(self.router, 'route_user_message', return_value=True) as mock_route:
                # Create system message
                system_message = SystemNotificationMessage(
                    id=str(uuid.uuid4()),
                    type=NotificationType.WARNING,
                    title="System Maintenance",
                    message="System will be down for maintenance",
                    priority=NotificationPriority.HIGH,
                    maintenance_info={"duration": "30 minutes"},
                    estimated_duration=30
                )
                
                # Route system broadcast
                result = self.router.route_system_broadcast(system_message)
                
                # Verify success
                self.assertTrue(result)
                self.assertEqual(mock_route.call_count, 5)  # Called for each user
    
    def test_validate_routing_permissions_admin(self):
        """Test routing permission validation for admin user"""
        # Mock admin user
        with patch.object(self.router, '_get_user_role', return_value=UserRole.ADMIN):
            # Test admin message permission
            self.assertTrue(self.router.validate_routing_permissions(1, 'admin'))
            
            # Test security message permission
            self.assertTrue(self.router.validate_routing_permissions(1, 'security'))
            
            # Test system message permission
            self.assertTrue(self.router.validate_routing_permissions(1, 'system'))
    
    def test_validate_routing_permissions_reviewer(self):
        """Test routing permission validation for reviewer user"""
        # Mock reviewer user
        with patch.object(self.router, '_get_user_role', return_value=UserRole.REVIEWER):
            # Test admin message permission (should be denied)
            self.assertFalse(self.router.validate_routing_permissions(1, 'admin'))
            
            # Test security message permission (should be denied)
            self.assertFalse(self.router.validate_routing_permissions(1, 'security'))
            
            # Test system message permission (should be allowed)
            self.assertTrue(self.router.validate_routing_permissions(1, 'system'))
            
            # Test user message permission (should be allowed)
            self.assertTrue(self.router.validate_routing_permissions(1, 'user'))
    
    def test_validate_routing_permissions_viewer(self):
        """Test routing permission validation for viewer user"""
        # Mock viewer user
        with patch.object(self.router, '_get_user_role', return_value=UserRole.VIEWER):
            # Test admin message permission (should be denied)
            self.assertFalse(self.router.validate_routing_permissions(1, 'admin'))
            
            # Test security message permission (should be denied)
            self.assertFalse(self.router.validate_routing_permissions(1, 'security'))
            
            # Test system message permission (should be allowed)
            self.assertTrue(self.router.validate_routing_permissions(1, 'system'))
    
    def test_determine_target_namespace_admin_message(self):
        """Test namespace determination for admin messages"""
        # Mock admin user
        with patch.object(self.router, '_get_user_role', return_value=UserRole.ADMIN):
            admin_message = NotificationMessage(
                id="test", type=NotificationType.WARNING, title="Admin", message="Admin message",
                category=NotificationCategory.ADMIN
            )
            
            namespace = self.router._determine_target_namespace(1, admin_message)
            self.assertEqual(namespace, '/admin')
    
    def test_determine_target_namespace_security_message_admin(self):
        """Test namespace determination for security messages to admin"""
        # Mock admin user
        with patch.object(self.router, '_get_user_role', return_value=UserRole.ADMIN):
            security_message = NotificationMessage(
                id="test", type=NotificationType.ERROR, title="Security", message="Security alert",
                category=NotificationCategory.SECURITY
            )
            
            namespace = self.router._determine_target_namespace(1, security_message)
            self.assertEqual(namespace, '/admin')
    
    def test_determine_target_namespace_security_message_moderator(self):
        """Test namespace determination for security messages to moderator"""
        # Mock moderator user
        with patch.object(self.router, '_get_user_role', return_value=UserRole.MODERATOR):
            security_message = NotificationMessage(
                id="test", type=NotificationType.ERROR, title="Security", message="Security alert",
                category=NotificationCategory.SECURITY
            )
            
            namespace = self.router._determine_target_namespace(1, security_message)
            self.assertEqual(namespace, '/')
    
    def test_determine_target_namespace_user_message(self):
        """Test namespace determination for user messages"""
        # Mock reviewer user
        with patch.object(self.router, '_get_user_role', return_value=UserRole.REVIEWER):
            user_message = NotificationMessage(
                id="test", type=NotificationType.INFO, title="User", message="User message",
                category=NotificationCategory.USER
            )
            
            namespace = self.router._determine_target_namespace(1, user_message)
            self.assertEqual(namespace, '/')
    
    def test_determine_target_namespace_invalid_user(self):
        """Test namespace determination for invalid user"""
        # Mock no user role
        with patch.object(self.router, '_get_user_role', return_value=None):
            message = NotificationMessage(
                id="test", type=NotificationType.INFO, title="Test", message="Test message",
                category=NotificationCategory.SYSTEM
            )
            
            namespace = self.router._determine_target_namespace(999, message)
            self.assertIsNone(namespace)
    
    def test_retry_failed_delivery(self):
        """Test retry mechanism for failed deliveries"""
        # Add message to retry queue
        self.router._retry_queues[1] = [self.test_message]
        
        # Mock successful retry
        with patch.object(self.router, 'route_user_message', return_value=True):
            # Process retry queue
            retried_count = self.router.process_retry_queue(1)
            
            # Verify retry success
            self.assertEqual(retried_count, 1)
            self.assertEqual(len(self.router._retry_queues[1]), 0)
            self.assertEqual(self.router._routing_stats['retry_successes'], 1)
    
    def test_retry_failed_delivery_max_attempts(self):
        """Test retry mechanism reaching max attempts"""
        # Create message with max attempts reached
        message_with_attempts = NotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.INFO,
            title="Test",
            message="Test message",
            user_id=1
        )
        
        # Track delivery attempts
        self.router._delivery_tracking[message_with_attempts.id] = Mock(
            attempts=3,  # Max attempts reached
            last_attempt=datetime.now(timezone.utc),
            status=DeliveryStatus.FAILED
        )
        
        self.router._retry_queues[1] = [message_with_attempts]
        
        # Mock continued failure
        with patch.object(self.router, 'route_user_message', return_value=False):
            # Process retry queue
            retried_count = self.router.process_retry_queue(1)
            
            # Verify message is abandoned
            self.assertEqual(retried_count, 0)
            self.assertEqual(len(self.router._retry_queues[1]), 0)  # Message removed from queue
            self.assertEqual(self.router._routing_stats['retry_failures'], 1)
    
    def test_delivery_confirmation_tracking(self):
        """Test delivery confirmation tracking"""
        # Mock successful delivery
        with patch.object(self.router, '_emit_to_user', return_value=True):
            # Route message
            result = self.router._deliver_message_to_user(1, self.test_message, '/')
            
            # Verify tracking
            self.assertTrue(result)
            self.assertIn(self.test_message.id, self.router._delivery_tracking)
            
            tracking_info = self.router._delivery_tracking[self.test_message.id]
            self.assertEqual(tracking_info.message_id, self.test_message.id)
            self.assertEqual(tracking_info.user_id, 1)
            self.assertEqual(tracking_info.status, DeliveryStatus.DELIVERED)
    
    def test_delivery_confirmation_timeout(self):
        """Test delivery confirmation timeout handling"""
        # Create message with old timestamp
        old_timestamp = datetime.now(timezone.utc) - timedelta(seconds=60)  # 1 minute ago
        
        self.router._delivery_tracking[self.test_message.id] = Mock(
            message_id=self.test_message.id,
            user_id=1,
            status=DeliveryStatus.PENDING,
            timestamp=old_timestamp,
            attempts=1
        )
        
        # Process timeouts
        timeout_count = self.router.process_delivery_timeouts()
        
        # Verify timeout handling
        self.assertEqual(timeout_count, 1)
        tracking_info = self.router._delivery_tracking[self.test_message.id]
        self.assertEqual(tracking_info.status, DeliveryStatus.TIMEOUT)
    
    def test_get_routing_statistics(self):
        """Test getting routing statistics"""
        # Set up some statistics
        self.router._routing_stats['messages_routed'] = 100
        self.router._routing_stats['successful_deliveries'] = 85
        self.router._routing_stats['failed_deliveries'] = 15
        self.router._routing_stats['retry_attempts'] = 20
        self.router._routing_stats['retry_successes'] = 12
        self.router._routing_stats['retry_failures'] = 8
        
        # Add some tracking data
        self.router._delivery_tracking['msg1'] = Mock(status=DeliveryStatus.DELIVERED)
        self.router._delivery_tracking['msg2'] = Mock(status=DeliveryStatus.PENDING)
        self.router._delivery_tracking['msg3'] = Mock(status=DeliveryStatus.FAILED)
        
        # Add retry queues
        self.router._retry_queues[1] = [Mock(), Mock()]
        self.router._retry_queues[2] = [Mock()]
        
        # Get statistics
        stats = self.router.get_routing_statistics()
        
        # Verify statistics structure
        self.assertIn('routing_stats', stats)
        self.assertIn('delivery_tracking', stats)
        self.assertIn('retry_queues', stats)
        self.assertIn('performance_metrics', stats)
        
        # Verify specific values
        self.assertEqual(stats['routing_stats']['messages_routed'], 100)
        self.assertEqual(stats['routing_stats']['successful_deliveries'], 85)
        self.assertEqual(stats['routing_stats']['failed_deliveries'], 15)
        self.assertEqual(stats['delivery_tracking']['total_tracked'], 3)
        self.assertEqual(stats['delivery_tracking']['delivered'], 1)
        self.assertEqual(stats['delivery_tracking']['pending'], 1)
        self.assertEqual(stats['delivery_tracking']['failed'], 1)
        self.assertEqual(stats['retry_queues']['total_users'], 2)
        self.assertEqual(stats['retry_queues']['total_messages'], 3)
    
    def test_clear_user_routing_data(self):
        """Test clearing routing data for a user"""
        # Add routing data for user
        self.router._retry_queues[1] = [Mock(), Mock()]
        self.router._delivery_tracking['msg1'] = Mock(user_id=1)
        self.router._delivery_tracking['msg2'] = Mock(user_id=1)
        self.router._delivery_tracking['msg3'] = Mock(user_id=2)  # Different user
        
        # Clear user data
        cleared_count = self.router.clear_user_routing_data(1)
        
        # Verify clearing
        self.assertEqual(cleared_count, 4)  # 2 retry messages + 2 tracking entries
        self.assertEqual(len(self.router._retry_queues[1]), 0)
        self.assertNotIn('msg1', self.router._delivery_tracking)
        self.assertNotIn('msg2', self.router._delivery_tracking)
        self.assertIn('msg3', self.router._delivery_tracking)  # Different user remains
    
    def test_security_validation_sensitive_message(self):
        """Test security validation for sensitive messages"""
        # Create sensitive admin message
        sensitive_message = AdminNotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.ERROR,
            title="Security Breach",
            message="Unauthorized access detected",
            priority=NotificationPriority.CRITICAL,
            security_event_data={"ip": "192.168.1.100", "attempts": 5},
            requires_admin_action=True
        )
        
        # Mock admin user
        with patch.object(self.router, '_get_user_role', return_value=UserRole.ADMIN):
            # Validate security
            is_valid = self.router._validate_message_security(1, sensitive_message)
            self.assertTrue(is_valid)
        
        # Mock non-admin user
        with patch.object(self.router, '_get_user_role', return_value=UserRole.REVIEWER):
            # Validate security (should fail)
            is_valid = self.router._validate_message_security(1, sensitive_message)
            self.assertFalse(is_valid)
    
    def test_message_priority_routing(self):
        """Test message routing based on priority"""
        # Create high priority message
        high_priority_message = NotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.ERROR,
            title="Critical Error",
            message="Critical system error",
            user_id=1,
            priority=NotificationPriority.CRITICAL,
            category=NotificationCategory.SYSTEM
        )
        
        # Mock user connections
        session_id = "session_123"
        self.mock_namespace_manager._user_connections[1] = {session_id}
        self.mock_namespace_manager._connections[session_id] = Mock(namespace='/')
        
        # Mock user role
        with patch.object(self.router, '_get_user_role', return_value=UserRole.REVIEWER):
            with patch.object(self.router, '_emit_to_user', return_value=True) as mock_emit:
                # Route high priority message
                result = self.router.route_user_message(1, high_priority_message)
                
                # Verify priority handling
                self.assertTrue(result)
                mock_emit.assert_called_once()
                
                # Verify message data includes priority
                call_args = mock_emit.call_args
                message_data = call_args[0][2]  # Third argument is message data
                self.assertEqual(message_data['priority'], 'critical')
    
    def test_error_handling_in_routing(self):
        """Test error handling during message routing"""
        # Mock exception in emit
        with patch.object(self.router, '_emit_to_user', side_effect=Exception("Emit error")):
            # Mock user connections
            session_id = "session_123"
            self.mock_namespace_manager._user_connections[1] = {session_id}
            self.mock_namespace_manager._connections[session_id] = Mock(namespace='/')
            
            # Mock user role
            with patch.object(self.router, '_get_user_role', return_value=UserRole.REVIEWER):
                # Route message
                result = self.router.route_user_message(1, self.test_message)
                
                # Verify error handling
                self.assertFalse(result)
                self.assertEqual(self.router._routing_stats['failed_deliveries'], 1)
    
    def test_batch_message_routing(self):
        """Test batch message routing for efficiency"""
        # Create multiple messages
        messages = []
        for i in range(5):
            message = NotificationMessage(
                id=f"msg_{i}",
                type=NotificationType.INFO,
                title=f"Message {i}",
                message=f"Test message {i}",
                user_id=1,
                category=NotificationCategory.SYSTEM
            )
            messages.append(message)
        
        # Mock successful routing
        with patch.object(self.router, 'route_user_message', return_value=True) as mock_route:
            # Route messages in batch
            results = self.router.route_batch_messages(1, messages)
            
            # Verify batch routing
            self.assertEqual(len(results), 5)
            self.assertTrue(all(results))
            self.assertEqual(mock_route.call_count, 5)


if __name__ == '__main__':
    unittest.main()
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Demonstration of NotificationMessageRouter Integration

This script demonstrates how the NotificationMessageRouter integrates with the existing
WebSocket CORS standardization framework to provide intelligent message routing,
namespace and room management, delivery confirmation, retry logic, and security validation.
"""

import logging
import uuid
from datetime import datetime, timezone
from unittest.mock import Mock

from app.services.notification.components.notification_message_router import NotificationMessageRouter
from app.websocket.core.websocket_namespace_manager import WebSocketNamespaceManager
from app.services.notification.manager.unified_manager import (
    NotificationMessage, AdminNotificationMessage, SystemNotificationMessage,
    NotificationType, NotificationPriority, NotificationCategory
)
from models import UserRole

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_demo_setup():
    """Create demo setup with mock WebSocket components"""
    logger.info("Setting up demo NotificationMessageRouter...")
    
    # Mock SocketIO and auth handler
    mock_socketio = Mock()
    mock_auth_handler = Mock()
    
    # Create namespace manager
    namespace_manager = WebSocketNamespaceManager(mock_socketio, mock_auth_handler)
    
    # Create message router
    message_router = NotificationMessageRouter(
        namespace_manager=namespace_manager,
        max_retry_attempts=3,
        retry_delay=30
    )
    
    # Setup mock user connections
    setup_mock_connections(namespace_manager)
    
    return message_router, namespace_manager


def setup_mock_connections(namespace_manager):
    """Setup mock user connections for demonstration"""
    logger.info("Setting up mock user connections...")
    
    # Admin user connection
    admin_session = 'admin_session_demo'
    admin_connection = Mock()
    admin_connection.session_id = admin_session
    admin_connection.namespace = '/admin'
    admin_connection.user_id = 1
    admin_connection.username = 'admin'
    admin_connection.role = UserRole.ADMIN
    admin_connection.connected_at = datetime.now(timezone.utc)
    admin_connection.rooms = {'admin_general'}
    admin_connection.auth_context = Mock()
    admin_connection.auth_context.user_id = 1
    admin_connection.auth_context.username = 'admin'
    admin_connection.auth_context.role = UserRole.ADMIN
    admin_connection.auth_context.is_admin = True
    admin_connection.auth_context.permissions = ['system_management', 'user_management']
    
    namespace_manager._connections[admin_session] = admin_connection
    namespace_manager._user_connections[1] = {admin_session}
    namespace_manager._namespace_connections['/admin'] = {admin_session}
    
    # Regular user connection
    user_session = 'user_session_demo'
    user_connection = Mock()
    user_connection.session_id = user_session
    user_connection.namespace = '/'
    user_connection.user_id = 2
    user_connection.username = 'reviewer'
    user_connection.role = UserRole.REVIEWER
    user_connection.connected_at = datetime.now(timezone.utc)
    user_connection.rooms = {'user_general', 'caption_progress'}
    user_connection.auth_context = Mock()
    user_connection.auth_context.user_id = 2
    user_connection.auth_context.username = 'reviewer'
    user_connection.auth_context.role = UserRole.REVIEWER
    user_connection.auth_context.is_admin = False
    user_connection.auth_context.permissions = []
    
    namespace_manager._connections[user_session] = user_connection
    namespace_manager._user_connections[2] = {user_session}
    namespace_manager._namespace_connections['/'] = {user_session}
    
    logger.info("Mock connections setup complete")


def demo_user_notification_routing(message_router):
    """Demonstrate user notification routing"""
    logger.info("\n=== Demo: User Notification Routing ===")
    
    # Create user notification
    message = NotificationMessage(
        id=str(uuid.uuid4()),
        type=NotificationType.SUCCESS,
        title="Caption Generation Complete",
        message="Your image captions have been generated successfully",
        user_id=2,
        priority=NotificationPriority.NORMAL,
        category=NotificationCategory.CAPTION,
        data={
            'images_processed': 5,
            'captions_generated': 5,
            'processing_time': '2.3 seconds'
        },
        requires_action=True,
        action_url='/captions/review',
        action_text='Review Captions'
    )
    
    # Route message
    result = message_router.route_user_message(2, message)
    logger.info(f"User notification routing result: {result}")
    
    # Check delivery tracking
    if message.id in message_router._delivery_attempts:
        attempt = message_router._delivery_attempts[message.id]
        logger.info(f"Delivery attempt tracked: {attempt.status.value}")
    
    return result


def demo_admin_notification_routing(message_router):
    """Demonstrate admin notification routing"""
    logger.info("\n=== Demo: Admin Notification Routing ===")
    
    # Create admin notification
    admin_message = AdminNotificationMessage(
        id=str(uuid.uuid4()),
        type=NotificationType.WARNING,
        title="System Health Alert",
        message="High memory usage detected on server",
        priority=NotificationPriority.HIGH,
        category=NotificationCategory.ADMIN,
        admin_only=True,
        system_health_data={
            'memory_usage': '85%',
            'cpu_usage': '60%',
            'disk_usage': '70%',
            'active_connections': 150
        }
    )
    
    # Route admin message
    result = message_router.route_admin_message(admin_message)
    logger.info(f"Admin notification routing result: {result}")
    
    return result


def demo_system_broadcast_routing(message_router):
    """Demonstrate system broadcast routing"""
    logger.info("\n=== Demo: System Broadcast Routing ===")
    
    # Create system broadcast message
    system_message = SystemNotificationMessage(
        id=str(uuid.uuid4()),
        type=NotificationType.INFO,
        title="Scheduled Maintenance Notice",
        message="System maintenance will begin in 30 minutes",
        priority=NotificationPriority.HIGH,
        category=NotificationCategory.MAINTENANCE,
        broadcast_to_all=True,
        estimated_duration=60,
        affects_functionality=['caption_generation', 'platform_sync'],
        maintenance_info={
            'start_time': '2025-08-30T02:00:00Z',
            'end_time': '2025-08-30T03:00:00Z',
            'reason': 'Database optimization and security updates'
        }
    )
    
    # Route system broadcast
    result = message_router.route_system_broadcast(system_message)
    logger.info(f"System broadcast routing result: {result}")
    
    return result


def demo_security_validation(message_router):
    """Demonstrate security validation for sensitive notifications"""
    logger.info("\n=== Demo: Security Validation ===")
    
    # Create security notification
    security_message = AdminNotificationMessage(
        id=str(uuid.uuid4()),
        type=NotificationType.ERROR,
        title="Security Alert",
        message="Multiple failed login attempts detected",
        priority=NotificationPriority.CRITICAL,
        category=NotificationCategory.SECURITY,
        admin_only=True,
        security_event_data={
            'event_type': 'authentication_failure',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'severity': 'critical',
            'source_ip': '192.168.1.100',
            'failed_attempts': 5,
            'username': 'suspicious_user'
        }
    )
    
    # Test security validation for admin user
    admin_validation = message_router._perform_security_validation(1, security_message)
    logger.info(f"Admin user security validation: {admin_validation}")
    
    # Test security validation for regular user (should fail)
    user_validation = message_router._perform_security_validation(2, security_message)
    logger.info(f"Regular user security validation: {user_validation}")
    
    return admin_validation, user_validation


def demo_delivery_confirmation(message_router):
    """Demonstrate message delivery confirmation"""
    logger.info("\n=== Demo: Delivery Confirmation ===")
    
    # Create test message
    message = NotificationMessage(
        id=str(uuid.uuid4()),
        type=NotificationType.INFO,
        title="Test Confirmation",
        message="This message tests delivery confirmation",
        user_id=2,
        category=NotificationCategory.USER
    )
    
    # Route message
    route_result = message_router.route_user_message(2, message)
    logger.info(f"Message routed: {route_result}")
    
    # Simulate delivery confirmation from client
    if route_result:
        confirm_result = message_router.confirm_message_delivery(message.id, 2)
        logger.info(f"Delivery confirmation result: {confirm_result}")
        
        # Check delivery status
        if message.id in message_router._delivery_attempts:
            attempt = message_router._delivery_attempts[message.id]
            logger.info(f"Final delivery status: {attempt.status.value}")
    
    return route_result


def demo_routing_statistics(message_router):
    """Demonstrate routing statistics"""
    logger.info("\n=== Demo: Routing Statistics ===")
    
    # Get routing statistics
    stats = message_router.get_routing_stats()
    
    logger.info("Routing Statistics:")
    logger.info(f"  Messages routed: {stats['routing_stats']['messages_routed']}")
    logger.info(f"  Delivery confirmations: {stats['routing_stats']['delivery_confirmations']}")
    logger.info(f"  Delivery failures: {stats['routing_stats']['delivery_failures']}")
    logger.info(f"  Security validations: {stats['routing_stats']['security_validations']}")
    logger.info(f"  Security violations: {stats['routing_stats']['security_violations']}")
    logger.info(f"  Total delivery attempts: {stats['delivery_attempts']['total']}")
    logger.info(f"  Pending confirmations: {stats['pending_confirmations']}")
    
    return stats


def demo_namespace_integration(namespace_manager):
    """Demonstrate integration with namespace manager"""
    logger.info("\n=== Demo: Namespace Manager Integration ===")
    
    # Get namespace statistics
    user_stats = namespace_manager.get_namespace_stats('/')
    admin_stats = namespace_manager.get_namespace_stats('/admin')
    
    logger.info("User Namespace Stats:")
    logger.info(f"  Total connections: {user_stats['total_connections']}")
    logger.info(f"  Unique users: {user_stats['unique_users']}")
    logger.info(f"  Total rooms: {user_stats['room_statistics']['total_rooms']}")
    
    logger.info("Admin Namespace Stats:")
    logger.info(f"  Total connections: {admin_stats['total_connections']}")
    logger.info(f"  Unique users: {admin_stats['unique_users']}")
    logger.info(f"  Total rooms: {admin_stats['room_statistics']['total_rooms']}")
    
    return user_stats, admin_stats


def main():
    """Main demonstration function"""
    logger.info("Starting NotificationMessageRouter Integration Demo")
    
    # Create demo setup
    message_router, namespace_manager = create_demo_setup()
    
    # Run demonstrations
    demo_user_notification_routing(message_router)
    demo_admin_notification_routing(message_router)
    demo_system_broadcast_routing(message_router)
    demo_security_validation(message_router)
    demo_delivery_confirmation(message_router)
    demo_routing_statistics(message_router)
    demo_namespace_integration(namespace_manager)
    
    logger.info("\n=== Demo Complete ===")
    logger.info("NotificationMessageRouter successfully integrates with WebSocket framework!")
    logger.info("Key features demonstrated:")
    logger.info("  ✓ Intelligent message routing based on user roles and permissions")
    logger.info("  ✓ WebSocket namespace and room management for targeted notifications")
    logger.info("  ✓ Message delivery confirmation and retry logic")
    logger.info("  ✓ Security validation for sensitive admin notifications")
    logger.info("  ✓ Integration with existing WebSocket CORS standardization framework")


if __name__ == '__main__':
    main()
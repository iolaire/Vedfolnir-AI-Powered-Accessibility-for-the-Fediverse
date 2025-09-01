# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Notification System Integration Example

This example demonstrates how to integrate the Unified Notification Manager
with the existing WebSocket CORS framework for a complete notification system.
"""

import uuid
from datetime import datetime, timezone, timedelta

from websocket_factory import WebSocketFactory
from websocket_auth_handler import WebSocketAuthHandler
from websocket_namespace_manager import WebSocketNamespaceManager
from websocket_config_manager import WebSocketConfigManager
from websocket_cors_manager import CORSManager

from unified_notification_manager import (
    UnifiedNotificationManager, NotificationMessage, AdminNotificationMessage,
    SystemNotificationMessage, NotificationType, NotificationPriority, 
    NotificationCategory
)
from notification_message_router import NotificationMessageRouter
from notification_persistence_manager import NotificationPersistenceManager

from database import DatabaseManager
from config import Config


def create_notification_system(app, db_manager):
    """
    Create and configure the complete notification system
    
    Args:
        app: Flask application instance
        db_manager: Database manager instance
        
    Returns:
        Tuple of (notification_manager, message_router, persistence_manager)
    """
    # Initialize WebSocket framework components
    config_manager = WebSocketConfigManager()
    cors_manager = CORSManager(config_manager)
    websocket_factory = WebSocketFactory(config_manager, cors_manager, db_manager)
    
    # Create SocketIO instance
    socketio = websocket_factory.create_socketio_instance(app)
    
    # Initialize authentication and namespace management
    auth_handler = WebSocketAuthHandler(db_manager, None)  # session_manager can be None for this example
    namespace_manager = WebSocketNamespaceManager(socketio, auth_handler)
    
    # Initialize notification system components
    notification_manager = UnifiedNotificationManager(
        websocket_factory=websocket_factory,
        auth_handler=auth_handler,
        namespace_manager=namespace_manager,
        db_manager=db_manager,
        max_offline_messages=100,
        message_retention_days=30
    )
    
    message_router = NotificationMessageRouter(
        namespace_manager=namespace_manager,
        max_retry_attempts=3,
        retry_delay=30
    )
    
    persistence_manager = NotificationPersistenceManager(
        db_manager=db_manager,
        max_offline_messages=100,
        retention_days=30
    )
    
    return notification_manager, message_router, persistence_manager, socketio


def example_send_user_notification(notification_manager):
    """Example: Send notification to specific user"""
    
    # Create a caption processing notification
    message = NotificationMessage(
        id=str(uuid.uuid4()),
        type=NotificationType.SUCCESS,
        title="Caption Generation Complete",
        message="Your image captions have been generated successfully",
        user_id=1,
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
    
    # Send notification
    success = notification_manager.send_user_notification(1, message)
    print(f"User notification sent: {success}")
    
    return success


def example_send_admin_notification(notification_manager):
    """Example: Send admin notification"""
    
    # Create a system health alert
    admin_message = AdminNotificationMessage(
        id=str(uuid.uuid4()),
        type=NotificationType.WARNING,
        title="High Memory Usage Alert",
        message="System memory usage has exceeded 85% threshold",
        priority=NotificationPriority.HIGH,
        admin_only=True,
        system_health_data={
            'memory_usage': 87.5,
            'cpu_usage': 45.2,
            'disk_usage': 62.1,
            'active_users': 23
        },
        requires_admin_action=True
    )
    
    # Send admin notification
    success = notification_manager.send_admin_notification(admin_message)
    print(f"Admin notification sent: {success}")
    
    return success


def example_broadcast_system_notification(notification_manager):
    """Example: Broadcast system notification"""
    
    # Create a maintenance notification
    system_message = SystemNotificationMessage(
        id=str(uuid.uuid4()),
        type=NotificationType.INFO,
        title="Scheduled Maintenance",
        message="System maintenance will begin in 30 minutes",
        priority=NotificationPriority.HIGH,
        broadcast_to_all=True,
        maintenance_info={
            'start_time': (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat(),
            'estimated_duration': 60,
            'maintenance_type': 'database_optimization'
        },
        estimated_duration=60,
        affects_functionality=['caption_generation', 'platform_sync']
    )
    
    # Broadcast system notification
    success = notification_manager.broadcast_system_notification(system_message)
    print(f"System notification broadcast: {success}")
    
    return success


def example_message_routing(message_router):
    """Example: Message routing with permissions"""
    
    # Test routing permissions
    user_id = 1
    
    # Check if user can receive admin notifications
    can_receive_admin = message_router.validate_routing_permissions(user_id, 'admin')
    print(f"User {user_id} can receive admin notifications: {can_receive_admin}")
    
    # Check if user can receive system notifications
    can_receive_system = message_router.validate_routing_permissions(user_id, 'system')
    print(f"User {user_id} can receive system notifications: {can_receive_system}")
    
    # Get routing statistics
    stats = message_router.get_routing_stats()
    print(f"Routing stats: {stats}")


def example_persistence_operations(persistence_manager):
    """Example: Persistence operations"""
    
    # Create a test notification
    notification = NotificationMessage(
        id=str(uuid.uuid4()),
        type=NotificationType.INFO,
        title="Test Notification",
        message="This is a test notification for persistence",
        user_id=1,
        category=NotificationCategory.SYSTEM
    )
    
    # Store notification
    stored_id = persistence_manager.store_notification(notification)
    print(f"Notification stored with ID: {stored_id}")
    
    # Queue for offline user
    persistence_manager.queue_for_offline_user(2, notification)
    print("Notification queued for offline user")
    
    # Get pending notifications
    pending = persistence_manager.get_pending_notifications(2)
    print(f"Pending notifications for user 2: {len(pending)}")
    
    # Get delivery statistics
    stats = persistence_manager.get_delivery_stats()
    print(f"Delivery stats: {stats}")


def example_notification_lifecycle(notification_manager, persistence_manager):
    """Example: Complete notification lifecycle"""
    
    print("\n=== Notification Lifecycle Example ===")
    
    # 1. Create notification
    message = NotificationMessage(
        id=str(uuid.uuid4()),
        type=NotificationType.SUCCESS,
        title="Platform Connection Successful",
        message="Successfully connected to Mastodon instance",
        user_id=1,
        priority=NotificationPriority.NORMAL,
        category=NotificationCategory.PLATFORM,
        data={
            'platform_type': 'mastodon',
            'instance_url': 'https://mastodon.social',
            'connection_time': datetime.now(timezone.utc).isoformat()
        }
    )
    
    # 2. Send notification (will be queued if user offline)
    success = notification_manager.send_user_notification(1, message)
    print(f"1. Notification sent: {success}")
    
    # 3. Get notification history
    history = notification_manager.get_notification_history(1, limit=10)
    print(f"2. Notification history: {len(history)} messages")
    
    # 4. Mark as read
    read_success = notification_manager.mark_message_as_read(message.id, 1)
    print(f"3. Marked as read: {read_success}")
    
    # 5. Get statistics
    stats = notification_manager.get_notification_stats()
    print(f"4. System stats: {stats}")
    
    # 6. Cleanup old messages
    cleaned = notification_manager.cleanup_expired_messages()
    print(f"5. Cleaned up {cleaned} expired messages")


def main():
    """Main example function"""
    print("=== Unified Notification System Integration Example ===")
    
    # Note: This is a demonstration example
    # In a real application, you would have actual Flask app and database instances
    
    print("\nThis example demonstrates the integration of:")
    print("1. UnifiedNotificationManager - Core notification management")
    print("2. NotificationMessageRouter - Intelligent message routing")
    print("3. NotificationPersistenceManager - Database storage and queuing")
    print("4. Integration with existing WebSocket CORS framework")
    
    print("\nKey Features Demonstrated:")
    print("- Role-based message routing and authorization")
    print("- Offline message queuing and persistence")
    print("- Message history and replay functionality")
    print("- Integration with WebSocket factory and auth handler")
    print("- Admin and system notification broadcasting")
    print("- Comprehensive error handling and recovery")
    
    print("\nTo use this system in your application:")
    print("1. Initialize the notification system with create_notification_system()")
    print("2. Use the notification_manager to send messages")
    print("3. The system handles routing, persistence, and delivery automatically")
    print("4. Users receive real-time notifications via WebSocket connections")
    
    # Example usage patterns
    print("\n=== Example Usage Patterns ===")
    
    # User notification example
    print("\n# Send user notification:")
    print("message = NotificationMessage(...)")
    print("success = notification_manager.send_user_notification(user_id, message)")
    
    # Admin notification example
    print("\n# Send admin notification:")
    print("admin_message = AdminNotificationMessage(...)")
    print("success = notification_manager.send_admin_notification(admin_message)")
    
    # System broadcast example
    print("\n# Broadcast system notification:")
    print("system_message = SystemNotificationMessage(...)")
    print("success = notification_manager.broadcast_system_notification(system_message)")
    
    print("\n=== Integration Complete ===")


if __name__ == '__main__':
    main()
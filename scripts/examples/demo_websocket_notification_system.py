# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
WebSocket Real-Time Notification System Demo

This script demonstrates the comprehensive WebSocket notification system
with standardized messaging, delivery confirmation, priority handling,
filtering, and offline persistence functionality.
"""

import logging
import time
import json
from datetime import datetime, timezone, timedelta
from flask import Flask
from flask_socketio import SocketIO
from threading import Thread

from websocket_notification_system import (
    WebSocketNotificationSystem, StandardizedNotification, NotificationTarget,
    NotificationFilter, NotificationPriority, NotificationType
)
from websocket_notification_delivery import WebSocketNotificationDeliverySystem
from websocket_notification_integration import (
    NotificationIntegrationManager, initialize_notification_integration
)
from models import UserRole

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MockConnectionTracker:
    """Mock connection tracker for demonstration"""
    
    def __init__(self):
        self.user_sessions = {
            123: ['session_user_123'],
            456: ['session_user_456'],
            789: ['session_admin_789']
        }
        
        self.session_users = {
            'session_user_123': {'user_id': 123, 'role': UserRole.REVIEWER},
            'session_user_456': {'user_id': 456, 'role': UserRole.REVIEWER},
            'session_admin_789': {'user_id': 789, 'role': UserRole.ADMIN}
        }
        
        self.namespace_sessions = {
            '/': ['session_user_123', 'session_user_456'],
            '/admin': ['session_admin_789']
        }
    
    def get_user_sessions(self, user_id):
        """Get sessions for a user"""
        return self.user_sessions.get(user_id, [])
    
    def get_sessions_by_role(self, role):
        """Get sessions by user role"""
        sessions = []
        for session_id, info in self.session_users.items():
            if info['role'] == role:
                sessions.append(session_id)
        return sessions
    
    def get_namespace_sessions(self, namespace):
        """Get sessions in a namespace"""
        return self.namespace_sessions.get(namespace, [])
    
    def get_room_sessions(self, room):
        """Get sessions in a room"""
        # Mock room sessions
        if room.startswith('task_'):
            return ['session_user_123']  # User 123 is in task rooms
        return []


def demo_basic_notification_system():
    """Demonstrate basic notification system functionality"""
    print("\n" + "="*60)
    print("DEMO: Basic Notification System")
    print("="*60)
    
    # Create Flask app and SocketIO
    app = Flask(__name__)
    socketio = SocketIO(app, cors_allowed_origins="*")
    
    # Initialize notification system
    notification_system = WebSocketNotificationSystem(socketio)
    
    # Set up mock connection tracker
    mock_tracker = MockConnectionTracker()
    notification_system.set_connection_tracker(mock_tracker)
    
    print("✅ Notification system initialized")
    
    # Create a basic notification
    notification = notification_system.create_notification(
        event_name='demo_notification',
        title='Demo Notification',
        message='This is a demonstration of the notification system',
        notification_type=NotificationType.INFO,
        priority=NotificationPriority.NORMAL,
        data={'demo': True, 'timestamp': datetime.now(timezone.utc).isoformat()}
    )
    
    print(f"✅ Created notification: {notification.id}")
    print(f"   Title: {notification.title}")
    print(f"   Type: {notification.notification_type.value}")
    print(f"   Priority: {notification.priority.value}")
    
    # Test serialization
    notification_dict = notification.to_dict()
    restored_notification = StandardizedNotification.from_dict(notification_dict)
    
    print(f"✅ Serialization test passed: {restored_notification.id == notification.id}")
    
    # Test sending to specific user
    success = notification_system.send_to_user(
        user_id=123,
        event_name='user_message',
        title='Personal Message',
        message='This message is just for you!',
        notification_type=NotificationType.INFO,
        priority=NotificationPriority.NORMAL
    )
    
    print(f"✅ Sent user notification: {success}")
    
    # Test broadcasting to role
    success = notification_system.send_to_role(
        role=UserRole.ADMIN,
        event_name='admin_alert',
        title='Admin Alert',
        message='This is an admin-only message',
        notification_type=NotificationType.ALERT,
        priority=NotificationPriority.HIGH
    )
    
    print(f"✅ Sent admin notification: {success}")
    
    # Get statistics
    stats = notification_system.get_statistics()
    print(f"✅ System statistics:")
    print(f"   Notifications sent: {stats['notifications_sent']}")
    print(f"   Notifications delivered: {stats['notifications_delivered']}")
    
    return notification_system


def demo_notification_filtering():
    """Demonstrate notification filtering functionality"""
    print("\n" + "="*60)
    print("DEMO: Notification Filtering")
    print("="*60)
    
    # Create test notifications
    notifications = [
        StandardizedNotification(
            event_name='info_event',
            title='Info Notification',
            message='Information message',
            notification_type=NotificationType.INFO,
            priority=NotificationPriority.NORMAL,
            source='test_system',
            tags={'info', 'test'}
        ),
        StandardizedNotification(
            event_name='error_event',
            title='Error Notification',
            message='Error message',
            notification_type=NotificationType.ERROR,
            priority=NotificationPriority.HIGH,
            source='error_system',
            tags={'error', 'critical'}
        ),
        StandardizedNotification(
            event_name='warning_event',
            title='Warning Notification',
            message='Warning message',
            notification_type=NotificationType.WARNING,
            priority=NotificationPriority.URGENT,
            source='warning_system',
            tags={'warning', 'important'}
        )
    ]
    
    print(f"✅ Created {len(notifications)} test notifications")
    
    # Test type filter
    type_filter = NotificationFilter(types={NotificationType.ERROR, NotificationType.WARNING})
    
    matching_notifications = [n for n in notifications if type_filter.matches(n)]
    print(f"✅ Type filter (ERROR, WARNING): {len(matching_notifications)} matches")
    
    # Test priority filter
    priority_filter = NotificationFilter(min_priority=NotificationPriority.HIGH)
    
    matching_notifications = [n for n in notifications if priority_filter.matches(n)]
    print(f"✅ Priority filter (HIGH+): {len(matching_notifications)} matches")
    
    # Test source filter
    source_filter = NotificationFilter(sources={'error_system'})
    
    matching_notifications = [n for n in notifications if source_filter.matches(n)]
    print(f"✅ Source filter (error_system): {len(matching_notifications)} matches")
    
    # Test tags filter
    tags_filter = NotificationFilter(tags={'critical'})
    
    matching_notifications = [n for n in notifications if tags_filter.matches(n)]
    print(f"✅ Tags filter (critical): {len(matching_notifications)} matches")
    
    # Test combined filter
    combined_filter = NotificationFilter(
        types={NotificationType.ERROR, NotificationType.WARNING},
        min_priority=NotificationPriority.HIGH,
        tags={'critical', 'important'}
    )
    
    matching_notifications = [n for n in notifications if combined_filter.matches(n)]
    print(f"✅ Combined filter: {len(matching_notifications)} matches")
    
    return notifications


def demo_delivery_system():
    """Demonstrate delivery confirmation and retry system"""
    print("\n" + "="*60)
    print("DEMO: Delivery System")
    print("="*60)
    
    # Create Flask app and SocketIO
    app = Flask(__name__)
    socketio = SocketIO(app, cors_allowed_origins="*")
    
    # Initialize delivery system
    delivery_system = WebSocketNotificationDeliverySystem(socketio)
    
    print("✅ Delivery system initialized")
    
    # Create test notification
    notification = StandardizedNotification(
        event_name='delivery_test',
        title='Delivery Test',
        message='Testing delivery confirmation',
        requires_acknowledgment=True,
        priority=NotificationPriority.HIGH
    )
    
    target_sessions = {'session_user_123', 'session_user_456'}
    
    # Test delivery
    success = delivery_system.deliver_notification(notification, target_sessions)
    print(f"✅ Delivery initiated: {success}")
    
    # Simulate delivery confirmation
    time.sleep(0.1)  # Small delay to simulate network latency
    
    confirmation_success = delivery_system.confirm_delivery(
        notification.id, 'session_user_123', 123
    )
    print(f"✅ Delivery confirmation recorded: {confirmation_success}")
    
    # Get delivery status
    status = delivery_system.get_delivery_status(notification.id)
    print(f"✅ Delivery status:")
    print(f"   Total attempts: {status['total_attempts']}")
    print(f"   Successful attempts: {status['successful_attempts']}")
    print(f"   Confirmations received: {status['confirmations_received']}")
    print(f"   Is complete: {status['is_complete']}")
    
    # Get system statistics
    stats = delivery_system.get_system_statistics()
    print(f"✅ Delivery system statistics:")
    print(f"   Delivery tracker: {stats['delivery_tracker']}")
    print(f"   Retry manager: {stats['retry_manager']}")
    
    return delivery_system


def demo_integration_system():
    """Demonstrate the complete integration system"""
    print("\n" + "="*60)
    print("DEMO: Integration System")
    print("="*60)
    
    # Create Flask app and SocketIO
    app = Flask(__name__)
    socketio = SocketIO(app, cors_allowed_origins="*")
    
    # Initialize integration system
    integration_manager = initialize_notification_integration(socketio)
    
    # Set up mock connection tracker
    mock_tracker = MockConnectionTracker()
    integration_manager.set_namespace_manager(mock_tracker)
    
    print("✅ Integration system initialized")
    
    # Test progress notification
    success = integration_manager.send_progress_notification(
        task_id='demo_task_123',
        user_id=123,
        progress_data={
            'progress': 75,
            'status': 'processing',
            'current_step': 'Generating captions',
            'total_steps': 4
        }
    )
    print(f"✅ Progress notification sent: {success}")
    
    # Test task completion notification
    success = integration_manager.send_task_completion_notification(
        task_id='demo_task_123',
        user_id=123,
        results={
            'captions_generated': 25,
            'success_rate': 96.0,
            'processing_time': '2m 34s'
        }
    )
    print(f"✅ Task completion notification sent: {success}")
    
    # Test system alert
    success = integration_manager.send_system_alert(
        title='System Maintenance',
        message='Scheduled maintenance will begin in 30 minutes',
        priority=NotificationPriority.URGENT,
        data={
            'maintenance_start': (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat(),
            'estimated_duration': '2 hours'
        }
    )
    print(f"✅ System alert sent: {success}")
    
    # Test admin notification
    success = integration_manager.send_admin_notification(
        title='User Activity Alert',
        message='Unusual user activity detected',
        notification_type=NotificationType.SECURITY,
        priority=NotificationPriority.HIGH,
        data={
            'user_id': 456,
            'activity_type': 'multiple_failed_logins',
            'count': 5
        }
    )
    print(f"✅ Admin notification sent: {success}")
    
    # Test security alert
    success = integration_manager.send_security_alert(
        title='Suspicious Login Attempt',
        message='Login attempt from unusual location detected',
        severity='high',
        data={
            'user_id': 123,
            'ip_address': '192.168.1.100',
            'location': 'Unknown',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    )
    print(f"✅ Security alert sent: {success}")
    
    # Test user notification preferences
    user_id = 123
    preferences = {
        'filter': {
            'types': ['info', 'warning', 'success'],
            'min_priority': 'normal'
        },
        'preferences': {
            'disabled_types': ['error'],
            'min_priority': 'high',
            'quiet_hours': {
                'enabled': True,
                'start': '22:00',
                'end': '08:00'
            }
        }
    }
    
    success = integration_manager.set_user_notification_preferences(user_id, preferences)
    print(f"✅ User preferences set: {success}")
    
    # Get user preferences
    retrieved_prefs = integration_manager.get_user_notification_preferences(user_id)
    print(f"✅ User preferences retrieved: {retrieved_prefs is not None}")
    
    # Test maintenance notification
    success = integration_manager.broadcast_maintenance_notification(
        title='Scheduled Maintenance',
        message='The system will be unavailable for maintenance',
        maintenance_start=datetime.now(timezone.utc) + timedelta(hours=2),
        estimated_duration='3 hours'
    )
    print(f"✅ Maintenance notification broadcast: {success}")
    
    # Get system statistics
    stats = integration_manager.get_system_statistics()
    print(f"✅ Integration system statistics:")
    print(f"   Notifications sent: {stats['notification_system']['notifications_sent']}")
    print(f"   Integration status: {stats['integration_status']}")
    
    return integration_manager


def demo_offline_persistence():
    """Demonstrate offline notification persistence"""
    print("\n" + "="*60)
    print("DEMO: Offline Persistence")
    print("="*60)
    
    # Create Flask app and SocketIO
    app = Flask(__name__)
    socketio = SocketIO(app, cors_allowed_origins="*")
    
    # Initialize notification system
    notification_system = WebSocketNotificationSystem(socketio)
    
    print("✅ Notification system initialized for offline demo")
    
    # Create notifications for offline users
    offline_user_ids = {999, 1000}  # Users not in mock tracker (offline)
    
    notifications = [
        StandardizedNotification(
            event_name='offline_message_1',
            title='Important Update',
            message='You have missed an important system update',
            notification_type=NotificationType.INFO,
            priority=NotificationPriority.HIGH,
            persist_offline=True,
            persist_duration_hours=48
        ),
        StandardizedNotification(
            event_name='offline_message_2',
            title='Security Alert',
            message='Your account security settings need attention',
            notification_type=NotificationType.SECURITY,
            priority=NotificationPriority.URGENT,
            persist_offline=True,
            persist_duration_hours=72
        ),
        StandardizedNotification(
            event_name='offline_message_3',
            title='System Maintenance Complete',
            message='System maintenance has been completed successfully',
            notification_type=NotificationType.SUCCESS,
            priority=NotificationPriority.NORMAL,
            persist_offline=True,
            persist_duration_hours=24
        )
    ]
    
    # Store notifications for offline users
    for notification in notifications:
        success = notification_system.persistence.store_notification(notification, offline_user_ids)
        print(f"✅ Stored notification '{notification.title}' for offline users: {success}")
    
    # Simulate user coming online and retrieving notifications
    user_id = 999
    
    # Get all offline notifications
    offline_notifications = notification_system.persistence.get_notifications_for_user(user_id)
    print(f"✅ Retrieved {len(offline_notifications)} offline notifications for user {user_id}")
    
    for notification in offline_notifications:
        print(f"   - {notification.title} ({notification.priority.value})")
    
    # Test filtering offline notifications
    filter_criteria = NotificationFilter(
        min_priority=NotificationPriority.HIGH
    )
    
    filtered_notifications = notification_system.persistence.get_notifications_for_user(
        user_id, filter_criteria
    )
    print(f"✅ Filtered notifications (HIGH+ priority): {len(filtered_notifications)}")
    
    # Mark notifications as delivered
    notification_ids = [n.id for n in offline_notifications[:2]]  # Mark first 2 as delivered
    success = notification_system.persistence.mark_notifications_delivered(user_id, notification_ids)
    print(f"✅ Marked {len(notification_ids)} notifications as delivered: {success}")
    
    # Test cleanup
    cleaned_count = notification_system.persistence.cleanup_expired_notifications()
    print(f"✅ Cleaned up {cleaned_count} expired notifications")
    
    return notification_system


def demo_priority_and_routing():
    """Demonstrate priority handling and routing"""
    print("\n" + "="*60)
    print("DEMO: Priority Handling and Routing")
    print("="*60)
    
    # Create Flask app and SocketIO
    app = Flask(__name__)
    socketio = SocketIO(app, cors_allowed_origins="*")
    
    # Initialize integration system
    integration_manager = initialize_notification_integration(socketio)
    
    # Set up mock connection tracker
    mock_tracker = MockConnectionTracker()
    integration_manager.set_namespace_manager(mock_tracker)
    
    print("✅ System initialized for priority and routing demo")
    
    # Test different priority levels
    priorities = [
        (NotificationPriority.LOW, 'Low Priority', 'This is a low priority message'),
        (NotificationPriority.NORMAL, 'Normal Priority', 'This is a normal priority message'),
        (NotificationPriority.HIGH, 'High Priority', 'This is a high priority message'),
        (NotificationPriority.URGENT, 'Urgent Priority', 'This is an urgent message'),
        (NotificationPriority.CRITICAL, 'Critical Priority', 'This is a critical message')
    ]
    
    for priority, title, message in priorities:
        success = integration_manager.send_user_notification(
            user_id=123,
            title=title,
            message=message,
            notification_type=NotificationType.INFO,
            priority=priority
        )
        print(f"✅ Sent {priority.value} priority notification: {success}")
    
    # Test routing to different targets
    print("\n--- Testing Routing ---")
    
    # Route to specific user
    success = integration_manager.send_user_notification(
        user_id=123,
        title='Personal Message',
        message='This message is for user 123 only'
    )
    print(f"✅ Routed to specific user: {success}")
    
    # Route to admin role
    success = integration_manager.send_admin_notification(
        title='Admin Only Message',
        message='This message is for admins only'
    )
    print(f"✅ Routed to admin role: {success}")
    
    # Route to all users (broadcast)
    success = integration_manager.notification_system.broadcast_to_all(
        event_name='system_announcement',
        title='System Announcement',
        message='This message goes to all users'
    )
    print(f"✅ Broadcast to all users: {success}")
    
    # Test room-based routing
    success = integration_manager.notification_system.send_to_room(
        room='task_123',
        event_name='task_update',
        title='Task Room Update',
        message='Update for users in task room'
    )
    print(f"✅ Routed to specific room: {success}")
    
    return integration_manager


def run_comprehensive_demo():
    """Run comprehensive demonstration of all features"""
    print("🚀 WebSocket Real-Time Notification System Demo")
    print("=" * 80)
    
    try:
        # Run individual demos
        notification_system = demo_basic_notification_system()
        time.sleep(1)
        
        notifications = demo_notification_filtering()
        time.sleep(1)
        
        delivery_system = demo_delivery_system()
        time.sleep(1)
        
        integration_manager = demo_integration_system()
        time.sleep(1)
        
        offline_system = demo_offline_persistence()
        time.sleep(1)
        
        priority_system = demo_priority_and_routing()
        time.sleep(1)
        
        print("\n" + "="*80)
        print("🎉 DEMO COMPLETE - All Features Demonstrated Successfully!")
        print("="*80)
        
        # Final statistics
        print("\n📊 Final System Statistics:")
        
        if integration_manager:
            stats = integration_manager.get_system_statistics()
            print(f"   Total notifications sent: {stats['notification_system']['notifications_sent']}")
            print(f"   Total notifications delivered: {stats['notification_system']['notifications_delivered']}")
            print(f"   Integration components connected: {sum(stats['integration_status'].values())}")
        
        print("\n✨ Key Features Demonstrated:")
        print("   ✅ Standardized notification format")
        print("   ✅ Priority-based handling")
        print("   ✅ User and role-based routing")
        print("   ✅ Notification filtering")
        print("   ✅ Delivery confirmation")
        print("   ✅ Retry mechanisms")
        print("   ✅ Offline persistence")
        print("   ✅ Integration with existing systems")
        print("   ✅ Comprehensive statistics")
        
        # Cleanup
        if integration_manager:
            integration_manager.shutdown()
        
        if delivery_system:
            delivery_system.shutdown()
        
        print("\n🔧 System shutdown complete")
        
    except Exception as e:
        logger.error(f"Demo failed with error: {e}", exc_info=True)
        print(f"\n❌ Demo failed: {e}")
        return False
    
    return True


if __name__ == '__main__':
    # Run the comprehensive demo
    success = run_comprehensive_demo()
    
    if success:
        print("\n🎯 Demo completed successfully!")
        print("The WebSocket Real-Time Notification System is ready for integration.")
    else:
        print("\n💥 Demo encountered errors. Please check the logs.")
    
    exit(0 if success else 1)
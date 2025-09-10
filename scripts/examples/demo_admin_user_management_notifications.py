# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Demo: Admin User Management Notifications

This script demonstrates the admin user management notification system
integration with the unified WebSocket notification framework.
"""

import logging
import json
from datetime import datetime, timezone
from unittest.mock import Mock

from app.services.admin.components.admin_user_management_notification_handler import (
    AdminUserManagementNotificationHandler, UserOperationContext
)
from app.services.admin.components.admin_user_management_integration import (
    AdminUserManagementIntegration, create_admin_user_management_integration
)
from app.services.notification.manager.unified_manager import (
    UnifiedNotificationManager, AdminNotificationMessage,
    NotificationType, NotificationPriority, NotificationCategory
)
from models import UserRole

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def demo_notification_handler():
    """Demonstrate the admin user management notification handler"""
    print("\n" + "=" * 60)
    print("DEMO: Admin User Management Notification Handler")
    print("=" * 60)
    
    # Create mock notification manager
    mock_notification_manager = Mock(spec=UnifiedNotificationManager)
    mock_notification_manager.send_admin_notification.return_value = True
    
    # Create notification handler
    handler = AdminUserManagementNotificationHandler(mock_notification_manager)
    
    # Create test operation context
    context = UserOperationContext(
        operation_type='demo_operation',
        target_user_id=123,
        target_username='demo_user',
        admin_user_id=1,
        admin_username='admin_demo',
        ip_address='192.168.1.100',
        user_agent='Demo Browser/1.0'
    )
    
    print(f"✅ Created notification handler")
    print(f"✅ Created operation context for user: {context.target_username}")
    
    # Demo 1: User Creation Notification
    print("\n📝 Demo 1: User Creation Notification")
    user_data = {
        'id': 123,
        'username': 'demo_user',
        'email': 'demo@example.com',
        'role': 'reviewer',
        'email_verified': True
    }
    
    success = handler.notify_user_created(context, user_data)
    print(f"   Result: {'✅ Success' if success else '❌ Failed'}")
    
    if mock_notification_manager.send_admin_notification.called:
        call_args = mock_notification_manager.send_admin_notification.call_args[0][0]
        print(f"   Notification Type: {call_args.type.value}")
        print(f"   Title: {call_args.title}")
        print(f"   Message: {call_args.message}")
        print(f"   Priority: {call_args.priority.value}")
        print(f"   Admin Only: {call_args.admin_only}")
    
    # Demo 2: User Role Change Notification
    print("\n🔄 Demo 2: User Role Change Notification")
    mock_notification_manager.reset_mock()
    
    old_role = UserRole.REVIEWER
    new_role = UserRole.ADMIN
    reason = "Promoted due to excellent performance"
    
    success = handler.notify_user_role_changed(context, old_role, new_role, reason)
    print(f"   Result: {'✅ Success' if success else '❌ Failed'}")
    
    if mock_notification_manager.send_admin_notification.called:
        call_args = mock_notification_manager.send_admin_notification.call_args[0][0]
        print(f"   Notification Type: {call_args.type.value}")
        print(f"   Title: {call_args.title}")
        print(f"   Message: {call_args.message}")
        print(f"   Priority: {call_args.priority.value}")
        print(f"   Requires Admin Action: {call_args.requires_admin_action}")
        print(f"   Role Change: {old_role.value} → {new_role.value}")
    
    # Demo 3: User Deletion Notification
    print("\n🗑️ Demo 3: User Deletion Notification")
    mock_notification_manager.reset_mock()
    
    deletion_reason = "Account violation - spam activity"
    success = handler.notify_user_deleted(context, deletion_reason)
    print(f"   Result: {'✅ Success' if success else '❌ Failed'}")
    
    if mock_notification_manager.send_admin_notification.called:
        call_args = mock_notification_manager.send_admin_notification.call_args[0][0]
        print(f"   Notification Type: {call_args.type.value}")
        print(f"   Title: {call_args.title}")
        print(f"   Message: {call_args.message}")
        print(f"   Priority: {call_args.priority.value}")
        print(f"   Deletion Reason: {deletion_reason}")
    
    # Demo 4: User Status Change Notification
    print("\n⚙️ Demo 4: User Status Change Notification")
    mock_notification_manager.reset_mock()
    
    status_changes = {
        'is_active': {'old': True, 'new': False},
        'account_locked': {'old': False, 'new': True},
        'email_verified': {'old': False, 'new': True}
    }
    
    success = handler.notify_user_status_changed(context, status_changes)
    print(f"   Result: {'✅ Success' if success else '❌ Failed'}")
    
    if mock_notification_manager.send_admin_notification.called:
        call_args = mock_notification_manager.send_admin_notification.call_args[0][0]
        print(f"   Notification Type: {call_args.type.value}")
        print(f"   Title: {call_args.title}")
        print(f"   Message: {call_args.message}")
        print(f"   Priority: {call_args.priority.value}")
        print(f"   Status Changes: {len(status_changes)} fields updated")
    
    # Demo 5: Bulk Operation Notification
    print("\n📊 Demo 5: Bulk Operation Notification")
    mock_notification_manager.reset_mock()
    
    operation_type = "user_activation"
    admin_context = {
        'admin_user_id': 1,
        'admin_username': 'admin_demo',
        'ip_address': '192.168.1.100'
    }
    results = [
        {'success': True, 'user_id': 101, 'username': 'user1'},
        {'success': True, 'user_id': 102, 'username': 'user2'},
        {'success': False, 'user_id': 103, 'username': 'user3', 'error': 'Already active'},
        {'success': True, 'user_id': 104, 'username': 'user4'}
    ]
    
    success = handler.notify_bulk_user_operation(operation_type, admin_context, results)
    print(f"   Result: {'✅ Success' if success else '❌ Failed'}")
    
    if mock_notification_manager.send_admin_notification.called:
        call_args = mock_notification_manager.send_admin_notification.call_args[0][0]
        print(f"   Notification Type: {call_args.type.value}")
        print(f"   Title: {call_args.title}")
        print(f"   Message: {call_args.message}")
        print(f"   Total Operations: {len(results)}")
        print(f"   Successful: {len([r for r in results if r.get('success')])}")
        print(f"   Failed: {len([r for r in results if not r.get('success')])}")
        print(f"   Requires Admin Action: {call_args.requires_admin_action}")


def demo_integration_service():
    """Demonstrate the admin user management integration service"""
    print("\n" + "=" * 60)
    print("DEMO: Admin User Management Integration Service")
    print("=" * 60)
    
    # Create mock notification manager
    mock_notification_manager = Mock(spec=UnifiedNotificationManager)
    mock_notification_manager.get_notification_stats.return_value = {
        'total_messages': 150,
        'delivered_messages': 145,
        'failed_messages': 5,
        'admin_notifications': 25
    }
    
    # Create integration service
    integration = create_admin_user_management_integration(mock_notification_manager)
    
    print(f"✅ Created integration service")
    
    # Demo Flask app integration
    print("\n🌐 Demo: Flask App Integration")
    mock_app = Mock()
    mock_app.config = {}
    
    result = integration.initialize_app_integration(mock_app)
    print(f"   Integration Result: {'✅ Success' if result['success'] else '❌ Failed'}")
    print(f"   Handler Registered: {result['handler_registered']}")
    print(f"   Integration Active: {result['integration_active']}")
    print(f"   Supported Operations: {len(result['supported_operations'])}")
    
    # Demo getting integration status
    print("\n📊 Demo: Integration Status")
    status = integration.get_integration_status()
    print(f"   Integration Active: {status['integration_active']}")
    print(f"   Handler Status: {status['notification_handler_status']}")
    print(f"   Supported Operations: {len(status['supported_operations'])}")
    
    # Demo getting notification handler
    print("\n🔧 Demo: Getting Notification Handler")
    handler = integration.get_notification_handler()
    print(f"   Handler Type: {type(handler).__name__}")
    print(f"   Handler Available: {handler is not None}")


def demo_notification_message_structure():
    """Demonstrate the notification message structure"""
    print("\n" + "=" * 60)
    print("DEMO: Notification Message Structure")
    print("=" * 60)
    
    # Create a sample admin notification message
    notification = AdminNotificationMessage(
        id="demo_notification_123",
        type=NotificationType.INFO,
        title="Demo User Management Notification",
        message="This is a demonstration of the admin notification structure",
        priority=NotificationPriority.HIGH,
        category=NotificationCategory.ADMIN,
        admin_only=True,
        user_action_data={
            'operation': 'user_role_changed',
            'target_user_id': 456,
            'target_username': 'demo_target_user',
            'admin_user_id': 1,
            'admin_username': 'demo_admin',
            'old_role': 'viewer',
            'new_role': 'moderator',
            'reason': 'Demonstration purposes',
            'ip_address': '192.168.1.100',
            'timestamp': datetime.now(timezone.utc).isoformat()
        },
        requires_admin_action=True
    )
    
    print("📋 Sample Admin Notification Message:")
    print(f"   ID: {notification.id}")
    print(f"   Type: {notification.type.value}")
    print(f"   Title: {notification.title}")
    print(f"   Message: {notification.message}")
    print(f"   Priority: {notification.priority.value}")
    print(f"   Category: {notification.category.value}")
    print(f"   Admin Only: {notification.admin_only}")
    print(f"   Requires Admin Action: {notification.requires_admin_action}")
    
    print("\n📊 User Action Data:")
    for key, value in notification.user_action_data.items():
        print(f"   {key}: {value}")
    
    # Convert to dictionary for WebSocket transmission
    print("\n🌐 WebSocket Message Format:")
    message_dict = notification.to_dict()
    print(json.dumps(message_dict, indent=2, default=str))


def demo_error_handling():
    """Demonstrate error handling in notifications"""
    print("\n" + "=" * 60)
    print("DEMO: Error Handling")
    print("=" * 60)
    
    # Create mock notification manager that fails
    mock_notification_manager = Mock(spec=UnifiedNotificationManager)
    mock_notification_manager.send_admin_notification.return_value = False
    
    # Create notification handler
    handler = AdminUserManagementNotificationHandler(mock_notification_manager)
    
    # Create test context
    context = UserOperationContext(
        operation_type='error_demo',
        target_user_id=999,
        target_username='error_user',
        admin_user_id=1,
        admin_username='admin_demo'
    )
    
    print("🚨 Demo: Notification Delivery Failure")
    user_data = {'id': 999, 'username': 'error_user'}
    success = handler.notify_user_created(context, user_data)
    print(f"   Result: {'✅ Success' if success else '❌ Failed (Expected)'}")
    print(f"   Handler gracefully handled delivery failure")
    
    # Demo exception handling
    print("\n💥 Demo: Exception Handling")
    mock_notification_manager.send_admin_notification.side_effect = Exception("Network error")
    
    success = handler.notify_user_created(context, user_data)
    print(f"   Result: {'✅ Success' if success else '❌ Failed (Expected)'}")
    print(f"   Handler gracefully handled exception")


def main():
    """Run all demonstrations"""
    print("🚀 Admin User Management Notifications Demonstration")
    print("Task 13: Migrate User Management Admin Notifications")
    print("Implementing real-time admin notifications for user operations")
    
    try:
        # Run demonstrations
        demo_notification_handler()
        demo_integration_service()
        demo_notification_message_structure()
        demo_error_handling()
        
        print("\n" + "=" * 60)
        print("✅ DEMONSTRATION COMPLETE")
        print("=" * 60)
        
        print("\nKey Features Implemented:")
        print("• Real-time admin notifications for user operations")
        print("• WebSocket-based notification delivery via admin namespace")
        print("• Comprehensive user operation tracking and logging")
        print("• Role-based notification authorization and security")
        print("• Graceful error handling and delivery confirmation")
        print("• Integration with existing unified notification framework")
        
        print("\nSupported User Operations:")
        print("• User creation with detailed user data")
        print("• User updates with change tracking")
        print("• User deletion with reason logging")
        print("• User role changes with security validation")
        print("• User status changes with field-level tracking")
        print("• Password resets with method tracking")
        print("• Bulk operations with success/failure reporting")
        
        print("\nSecurity Features:")
        print("• Admin-only notification delivery")
        print("• IP address and user agent logging")
        print("• Operation context tracking")
        print("• Audit trail integration")
        print("• Authorization validation")
        
        print("\nIntegration Benefits:")
        print("• Replaces legacy Flask flash messages")
        print("• Real-time WebSocket delivery")
        print("• Consistent notification format")
        print("• Centralized notification management")
        print("• Enhanced admin monitoring capabilities")
        
    except Exception as e:
        print(f"\n❌ Error during demonstration: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
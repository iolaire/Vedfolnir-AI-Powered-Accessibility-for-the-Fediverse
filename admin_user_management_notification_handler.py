# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Admin User Management Notification Handler

This module provides real-time user management notifications for administrators
via the unified WebSocket notification system. It replaces legacy Flask flash
messages with real-time admin notifications for user operations.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from unified_notification_manager import (
    UnifiedNotificationManager, AdminNotificationMessage, 
    NotificationType, NotificationPriority, NotificationCategory
)
from models import UserRole, User

logger = logging.getLogger(__name__)


@dataclass
class UserOperationContext:
    """Context information for user management operations"""
    operation_type: str
    target_user_id: int
    target_username: str
    admin_user_id: int
    admin_username: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None


class AdminUserManagementNotificationHandler:
    """
    Handler for admin user management notifications
    
    Provides real-time notifications for user operations including creation,
    modification, deletion, role changes, and status updates via the unified
    WebSocket notification system.
    """
    
    def __init__(self, notification_manager: UnifiedNotificationManager):
        """
        Initialize admin user management notification handler
        
        Args:
            notification_manager: Unified notification manager instance
        """
        self.notification_manager = notification_manager
        
        # Operation type mappings for notifications
        self.operation_types = {
            'user_created': {
                'title': 'User Created',
                'type': NotificationType.SUCCESS,
                'priority': NotificationPriority.NORMAL
            },
            'user_updated': {
                'title': 'User Updated',
                'type': NotificationType.INFO,
                'priority': NotificationPriority.NORMAL
            },
            'user_deleted': {
                'title': 'User Deleted',
                'type': NotificationType.WARNING,
                'priority': NotificationPriority.HIGH
            },
            'user_role_changed': {
                'title': 'User Role Changed',
                'type': NotificationType.INFO,
                'priority': NotificationPriority.HIGH
            },
            'user_status_changed': {
                'title': 'User Status Changed',
                'type': NotificationType.INFO,
                'priority': NotificationPriority.NORMAL
            },
            'user_password_reset': {
                'title': 'Password Reset',
                'type': NotificationType.WARNING,
                'priority': NotificationPriority.HIGH
            },
            'user_permissions_changed': {
                'title': 'Permissions Changed',
                'type': NotificationType.INFO,
                'priority': NotificationPriority.HIGH
            }
        }
        
        logger.info("Admin User Management Notification Handler initialized")
    
    def notify_user_created(self, context: UserOperationContext, user_data: Dict[str, Any]) -> bool:
        """
        Send notification for user creation
        
        Args:
            context: Operation context
            user_data: Created user data
            
        Returns:
            True if notification sent successfully
        """
        try:
            message = f"New user '{context.target_username}' created by {context.admin_username}"
            
            notification = AdminNotificationMessage(
                id=str(uuid.uuid4()),
                type=NotificationType.SUCCESS,
                title="User Created",
                message=message,
                priority=NotificationPriority.NORMAL,
                category=NotificationCategory.ADMIN,
                admin_only=True,
                user_action_data={
                    'operation': 'user_created',
                    'target_user_id': context.target_user_id,
                    'target_username': context.target_username,
                    'admin_user_id': context.admin_user_id,
                    'admin_username': context.admin_username,
                    'user_role': user_data.get('role', 'viewer'),
                    'user_email': user_data.get('email'),
                    'email_verified': user_data.get('email_verified', False),
                    'ip_address': context.ip_address,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                },
                requires_admin_action=False
            )
            
            success = self.notification_manager.send_admin_notification(notification)
            
            if success:
                logger.info(f"Sent user creation notification for user {context.target_username}")
            else:
                logger.error(f"Failed to send user creation notification for user {context.target_username}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending user creation notification: {e}")
            return False
    
    def notify_user_updated(self, context: UserOperationContext, changes: Dict[str, Any]) -> bool:
        """
        Send notification for user update
        
        Args:
            context: Operation context
            changes: Dictionary of changes made
            
        Returns:
            True if notification sent successfully
        """
        try:
            # Create human-readable change summary
            change_summary = []
            for field, change_info in changes.items():
                if isinstance(change_info, dict) and 'old' in change_info and 'new' in change_info:
                    change_summary.append(f"{field}: {change_info['old']} → {change_info['new']}")
                else:
                    change_summary.append(f"{field}: {change_info}")
            
            message = f"User '{context.target_username}' updated by {context.admin_username}"
            if change_summary:
                message += f" - Changes: {', '.join(change_summary)}"
            
            notification = AdminNotificationMessage(
                id=str(uuid.uuid4()),
                type=NotificationType.INFO,
                title="User Updated",
                message=message,
                priority=NotificationPriority.NORMAL,
                category=NotificationCategory.ADMIN,
                admin_only=True,
                user_action_data={
                    'operation': 'user_updated',
                    'target_user_id': context.target_user_id,
                    'target_username': context.target_username,
                    'admin_user_id': context.admin_user_id,
                    'admin_username': context.admin_username,
                    'changes': changes,
                    'ip_address': context.ip_address,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                },
                requires_admin_action=False
            )
            
            success = self.notification_manager.send_admin_notification(notification)
            
            if success:
                logger.info(f"Sent user update notification for user {context.target_username}")
            else:
                logger.error(f"Failed to send user update notification for user {context.target_username}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending user update notification: {e}")
            return False
    
    def notify_user_deleted(self, context: UserOperationContext, deletion_reason: Optional[str] = None) -> bool:
        """
        Send notification for user deletion
        
        Args:
            context: Operation context
            deletion_reason: Optional reason for deletion
            
        Returns:
            True if notification sent successfully
        """
        try:
            message = f"User '{context.target_username}' deleted by {context.admin_username}"
            if deletion_reason:
                message += f" - Reason: {deletion_reason}"
            
            notification = AdminNotificationMessage(
                id=str(uuid.uuid4()),
                type=NotificationType.WARNING,
                title="User Deleted",
                message=message,
                priority=NotificationPriority.HIGH,
                category=NotificationCategory.ADMIN,
                admin_only=True,
                user_action_data={
                    'operation': 'user_deleted',
                    'target_user_id': context.target_user_id,
                    'target_username': context.target_username,
                    'admin_user_id': context.admin_user_id,
                    'admin_username': context.admin_username,
                    'deletion_reason': deletion_reason,
                    'ip_address': context.ip_address,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                },
                requires_admin_action=False
            )
            
            success = self.notification_manager.send_admin_notification(notification)
            
            if success:
                logger.info(f"Sent user deletion notification for user {context.target_username}")
            else:
                logger.error(f"Failed to send user deletion notification for user {context.target_username}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending user deletion notification: {e}")
            return False
    
    def notify_user_role_changed(self, context: UserOperationContext, old_role: UserRole, 
                               new_role: UserRole, reason: Optional[str] = None) -> bool:
        """
        Send notification for user role change
        
        Args:
            context: Operation context
            old_role: Previous user role
            new_role: New user role
            reason: Optional reason for role change
            
        Returns:
            True if notification sent successfully
        """
        try:
            message = f"User '{context.target_username}' role changed from {old_role.value} to {new_role.value} by {context.admin_username}"
            if reason:
                message += f" - Reason: {reason}"
            
            # Determine priority based on role change
            priority = NotificationPriority.HIGH
            if new_role == UserRole.ADMIN or old_role == UserRole.ADMIN:
                priority = NotificationPriority.CRITICAL
            
            notification = AdminNotificationMessage(
                id=str(uuid.uuid4()),
                type=NotificationType.INFO,
                title="User Role Changed",
                message=message,
                priority=priority,
                category=NotificationCategory.ADMIN,
                admin_only=True,
                user_action_data={
                    'operation': 'user_role_changed',
                    'target_user_id': context.target_user_id,
                    'target_username': context.target_username,
                    'admin_user_id': context.admin_user_id,
                    'admin_username': context.admin_username,
                    'old_role': old_role.value,
                    'new_role': new_role.value,
                    'reason': reason,
                    'ip_address': context.ip_address,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                },
                requires_admin_action=new_role == UserRole.ADMIN  # Admin role changes may require attention
            )
            
            success = self.notification_manager.send_admin_notification(notification)
            
            if success:
                logger.info(f"Sent role change notification for user {context.target_username}")
            else:
                logger.error(f"Failed to send role change notification for user {context.target_username}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending role change notification: {e}")
            return False
    
    def notify_user_status_changed(self, context: UserOperationContext, status_changes: Dict[str, Any]) -> bool:
        """
        Send notification for user status change
        
        Args:
            context: Operation context
            status_changes: Dictionary of status changes
            
        Returns:
            True if notification sent successfully
        """
        try:
            # Create human-readable status change summary
            change_summary = []
            for field, change_info in status_changes.items():
                if isinstance(change_info, dict) and 'old' in change_info and 'new' in change_info:
                    change_summary.append(f"{field}: {change_info['old']} → {change_info['new']}")
                else:
                    change_summary.append(f"{field}: {change_info}")
            
            message = f"User '{context.target_username}' status updated by {context.admin_username}"
            if change_summary:
                message += f" - Changes: {', '.join(change_summary)}"
            
            # Determine priority based on status changes
            priority = NotificationPriority.NORMAL
            if 'account_locked' in status_changes or 'is_active' in status_changes:
                priority = NotificationPriority.HIGH
            
            notification = AdminNotificationMessage(
                id=str(uuid.uuid4()),
                type=NotificationType.INFO,
                title="User Status Changed",
                message=message,
                priority=priority,
                category=NotificationCategory.ADMIN,
                admin_only=True,
                user_action_data={
                    'operation': 'user_status_changed',
                    'target_user_id': context.target_user_id,
                    'target_username': context.target_username,
                    'admin_user_id': context.admin_user_id,
                    'admin_username': context.admin_username,
                    'status_changes': status_changes,
                    'ip_address': context.ip_address,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                },
                requires_admin_action=False
            )
            
            success = self.notification_manager.send_admin_notification(notification)
            
            if success:
                logger.info(f"Sent status change notification for user {context.target_username}")
            else:
                logger.error(f"Failed to send status change notification for user {context.target_username}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending status change notification: {e}")
            return False
    
    def notify_user_password_reset(self, context: UserOperationContext, reset_method: str,
                                 temp_password_generated: bool = False) -> bool:
        """
        Send notification for user password reset
        
        Args:
            context: Operation context
            reset_method: Method used for password reset
            temp_password_generated: Whether a temporary password was generated
            
        Returns:
            True if notification sent successfully
        """
        try:
            message = f"Password reset for user '{context.target_username}' by {context.admin_username}"
            if temp_password_generated:
                message += " - Temporary password generated"
            
            notification = AdminNotificationMessage(
                id=str(uuid.uuid4()),
                type=NotificationType.WARNING,
                title="Password Reset",
                message=message,
                priority=NotificationPriority.HIGH,
                category=NotificationCategory.ADMIN,
                admin_only=True,
                user_action_data={
                    'operation': 'user_password_reset',
                    'target_user_id': context.target_user_id,
                    'target_username': context.target_username,
                    'admin_user_id': context.admin_user_id,
                    'admin_username': context.admin_username,
                    'reset_method': reset_method,
                    'temp_password_generated': temp_password_generated,
                    'ip_address': context.ip_address,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                },
                requires_admin_action=False
            )
            
            success = self.notification_manager.send_admin_notification(notification)
            
            if success:
                logger.info(f"Sent password reset notification for user {context.target_username}")
            else:
                logger.error(f"Failed to send password reset notification for user {context.target_username}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending password reset notification: {e}")
            return False
    
    def notify_bulk_user_operation(self, operation_type: str, admin_context: Dict[str, Any],
                                 results: List[Dict[str, Any]]) -> bool:
        """
        Send notification for bulk user operations
        
        Args:
            operation_type: Type of bulk operation
            admin_context: Admin user context
            results: List of operation results
            
        Returns:
            True if notification sent successfully
        """
        try:
            success_count = len([r for r in results if r.get('success', False)])
            total_count = len(results)
            
            message = f"Bulk {operation_type} completed by {admin_context.get('admin_username')}: "
            message += f"{success_count}/{total_count} operations successful"
            
            notification = AdminNotificationMessage(
                id=str(uuid.uuid4()),
                type=NotificationType.INFO if success_count == total_count else NotificationType.WARNING,
                title=f"Bulk {operation_type.title()}",
                message=message,
                priority=NotificationPriority.NORMAL,
                category=NotificationCategory.ADMIN,
                admin_only=True,
                user_action_data={
                    'operation': f'bulk_{operation_type}',
                    'admin_user_id': admin_context.get('admin_user_id'),
                    'admin_username': admin_context.get('admin_username'),
                    'total_operations': total_count,
                    'successful_operations': success_count,
                    'failed_operations': total_count - success_count,
                    'results': results,
                    'ip_address': admin_context.get('ip_address'),
                    'timestamp': datetime.now(timezone.utc).isoformat()
                },
                requires_admin_action=success_count < total_count
            )
            
            success = self.notification_manager.send_admin_notification(notification)
            
            if success:
                logger.info(f"Sent bulk operation notification: {operation_type}")
            else:
                logger.error(f"Failed to send bulk operation notification: {operation_type}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending bulk operation notification: {e}")
            return False
    
    def notify_user_permission_change(self, context: UserOperationContext, 
                                    permission_changes: Dict[str, Any]) -> bool:
        """
        Send notification for user permission changes
        
        Args:
            context: Operation context
            permission_changes: Dictionary of permission changes
            
        Returns:
            True if notification sent successfully
        """
        try:
            message = f"Permissions updated for user '{context.target_username}' by {context.admin_username}"
            
            notification = AdminNotificationMessage(
                id=str(uuid.uuid4()),
                type=NotificationType.INFO,
                title="Permissions Changed",
                message=message,
                priority=NotificationPriority.HIGH,
                category=NotificationCategory.ADMIN,
                admin_only=True,
                user_action_data={
                    'operation': 'user_permissions_changed',
                    'target_user_id': context.target_user_id,
                    'target_username': context.target_username,
                    'admin_user_id': context.admin_user_id,
                    'admin_username': context.admin_username,
                    'permission_changes': permission_changes,
                    'ip_address': context.ip_address,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                },
                requires_admin_action=False
            )
            
            success = self.notification_manager.send_admin_notification(notification)
            
            if success:
                logger.info(f"Sent permission change notification for user {context.target_username}")
            else:
                logger.error(f"Failed to send permission change notification for user {context.target_username}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending permission change notification: {e}")
            return False
    
    def get_notification_stats(self) -> Dict[str, Any]:
        """
        Get user management notification statistics
        
        Returns:
            Dictionary containing notification statistics
        """
        try:
            # Get stats from the notification manager
            manager_stats = self.notification_manager.get_notification_stats()
            
            return {
                'handler_type': 'admin_user_management',
                'supported_operations': list(self.operation_types.keys()),
                'notification_manager_stats': manager_stats,
                'handler_status': 'active'
            }
            
        except Exception as e:
            logger.error(f"Error getting notification stats: {e}")
            return {'error': str(e)}


def create_admin_user_management_notification_handler(
    notification_manager: UnifiedNotificationManager
) -> AdminUserManagementNotificationHandler:
    """
    Factory function to create admin user management notification handler
    
    Args:
        notification_manager: Unified notification manager instance
        
    Returns:
        AdminUserManagementNotificationHandler instance
    """
    return AdminUserManagementNotificationHandler(notification_manager)
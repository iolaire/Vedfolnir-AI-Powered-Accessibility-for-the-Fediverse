# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
User Profile Notification Helper

This module provides helper functions for sending user profile and settings notifications
through the unified WebSocket notification system, replacing legacy Flask flash messages.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from flask import current_app
from flask_login import current_user

from unified_notification_manager import (
    UnifiedNotificationManager, NotificationMessage, NotificationType, 
    NotificationPriority, NotificationCategory
)

logger = logging.getLogger(__name__)


class UserProfileNotificationHelper:
    """Helper class for sending user profile and settings notifications"""
    
    def __init__(self, notification_manager: UnifiedNotificationManager):
        """
        Initialize the helper with notification manager
        
        Args:
            notification_manager: Unified notification manager instance
        """
        self.notification_manager = notification_manager
        self.logger = logging.getLogger(__name__)
    
    def send_profile_update_notification(self, user_id: int, success: bool, 
                                       message: str, details: Optional[Dict[str, Any]] = None) -> bool:
        """
        Send profile update notification
        
        Args:
            user_id: User ID to send notification to
            success: Whether the profile update was successful
            message: Notification message
            details: Additional details about the update
            
        Returns:
            True if notification sent successfully
        """
        try:
            notification = NotificationMessage(
                id=str(uuid.uuid4()),
                type=NotificationType.SUCCESS if success else NotificationType.ERROR,
                title="Profile Update" if success else "Profile Update Failed",
                message=message,
                user_id=user_id,
                priority=NotificationPriority.NORMAL,
                category=NotificationCategory.USER,
                data={
                    'action': 'profile_update',
                    'success': success,
                    'details': details or {},
                    'timestamp': datetime.now(timezone.utc).isoformat()
                },
                requires_action=False
            )
            
            result = self.notification_manager.send_user_notification(user_id, notification)
            
            if result:
                self.logger.info(f"Sent profile update notification to user {user_id}: {success}")
            else:
                self.logger.error(f"Failed to send profile update notification to user {user_id}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error sending profile update notification: {e}")
            return False
    
    def send_settings_change_notification(self, user_id: int, setting_name: str, 
                                        success: bool, message: str, 
                                        old_value: Any = None, new_value: Any = None) -> bool:
        """
        Send settings change notification
        
        Args:
            user_id: User ID to send notification to
            setting_name: Name of the setting that changed
            success: Whether the settings change was successful
            message: Notification message
            old_value: Previous setting value
            new_value: New setting value
            
        Returns:
            True if notification sent successfully
        """
        try:
            notification = NotificationMessage(
                id=str(uuid.uuid4()),
                type=NotificationType.SUCCESS if success else NotificationType.ERROR,
                title="Settings Updated" if success else "Settings Update Failed",
                message=message,
                user_id=user_id,
                priority=NotificationPriority.NORMAL,
                category=NotificationCategory.USER,
                data={
                    'action': 'settings_change',
                    'setting_name': setting_name,
                    'success': success,
                    'old_value': str(old_value) if old_value is not None else None,
                    'new_value': str(new_value) if new_value is not None else None,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                },
                requires_action=False
            )
            
            result = self.notification_manager.send_user_notification(user_id, notification)
            
            if result:
                self.logger.info(f"Sent settings change notification to user {user_id}: {setting_name}")
            else:
                self.logger.error(f"Failed to send settings change notification to user {user_id}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error sending settings change notification: {e}")
            return False
    
    def send_password_change_notification(self, user_id: int, success: bool, 
                                        message: str, security_details: Optional[Dict[str, Any]] = None) -> bool:
        """
        Send password change notification
        
        Args:
            user_id: User ID to send notification to
            success: Whether the password change was successful
            message: Notification message
            security_details: Security-related details (IP, user agent, etc.)
            
        Returns:
            True if notification sent successfully
        """
        try:
            notification = NotificationMessage(
                id=str(uuid.uuid4()),
                type=NotificationType.SUCCESS if success else NotificationType.ERROR,
                title="Password Changed" if success else "Password Change Failed",
                message=message,
                user_id=user_id,
                priority=NotificationPriority.HIGH,  # Security-related, higher priority
                category=NotificationCategory.SECURITY,
                data={
                    'action': 'password_change',
                    'success': success,
                    'security_details': security_details or {},
                    'timestamp': datetime.now(timezone.utc).isoformat()
                },
                requires_action=False
            )
            
            result = self.notification_manager.send_user_notification(user_id, notification)
            
            if result:
                self.logger.info(f"Sent password change notification to user {user_id}: {success}")
            else:
                self.logger.error(f"Failed to send password change notification to user {user_id}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error sending password change notification: {e}")
            return False
    
    def send_account_status_notification(self, user_id: int, status_change: str, 
                                       message: str, admin_action: bool = False,
                                       admin_user_id: Optional[int] = None) -> bool:
        """
        Send account status change notification
        
        Args:
            user_id: User ID to send notification to
            status_change: Type of status change (activated, deactivated, locked, etc.)
            message: Notification message
            admin_action: Whether this was an admin action
            admin_user_id: ID of admin who performed the action
            
        Returns:
            True if notification sent successfully
        """
        try:
            # Determine notification type and priority based on status change
            if status_change in ['activated', 'verified', 'unlocked']:
                notification_type = NotificationType.SUCCESS
                priority = NotificationPriority.NORMAL
            elif status_change in ['deactivated', 'locked', 'suspended']:
                notification_type = NotificationType.WARNING
                priority = NotificationPriority.HIGH
            else:
                notification_type = NotificationType.INFO
                priority = NotificationPriority.NORMAL
            
            notification = NotificationMessage(
                id=str(uuid.uuid4()),
                type=notification_type,
                title="Account Status Changed",
                message=message,
                user_id=user_id,
                priority=priority,
                category=NotificationCategory.SECURITY,
                data={
                    'action': 'account_status_change',
                    'status_change': status_change,
                    'admin_action': admin_action,
                    'admin_user_id': admin_user_id,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                },
                requires_action=status_change in ['locked', 'suspended']
            )
            
            result = self.notification_manager.send_user_notification(user_id, notification)
            
            if result:
                self.logger.info(f"Sent account status notification to user {user_id}: {status_change}")
            else:
                self.logger.error(f"Failed to send account status notification to user {user_id}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error sending account status notification: {e}")
            return False
    
    def send_permission_change_notification(self, user_id: int, old_role: str, new_role: str,
                                          message: str, admin_user_id: Optional[int] = None) -> bool:
        """
        Send permission/role change notification
        
        Args:
            user_id: User ID to send notification to
            old_role: Previous user role
            new_role: New user role
            message: Notification message
            admin_user_id: ID of admin who performed the change
            
        Returns:
            True if notification sent successfully
        """
        try:
            # Determine if this is a promotion or demotion
            role_hierarchy = ['viewer', 'reviewer', 'moderator', 'admin']
            old_level = role_hierarchy.index(old_role.lower()) if old_role.lower() in role_hierarchy else 0
            new_level = role_hierarchy.index(new_role.lower()) if new_role.lower() in role_hierarchy else 0
            
            is_promotion = new_level > old_level
            
            notification = NotificationMessage(
                id=str(uuid.uuid4()),
                type=NotificationType.SUCCESS if is_promotion else NotificationType.INFO,
                title="Permissions Updated",
                message=message,
                user_id=user_id,
                priority=NotificationPriority.HIGH,  # Permission changes are important
                category=NotificationCategory.SECURITY,
                data={
                    'action': 'permission_change',
                    'old_role': old_role,
                    'new_role': new_role,
                    'is_promotion': is_promotion,
                    'admin_user_id': admin_user_id,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                },
                requires_action=False
            )
            
            result = self.notification_manager.send_user_notification(user_id, notification)
            
            if result:
                self.logger.info(f"Sent permission change notification to user {user_id}: {old_role} -> {new_role}")
            else:
                self.logger.error(f"Failed to send permission change notification to user {user_id}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error sending permission change notification: {e}")
            return False
    
    def send_email_verification_notification(self, user_id: int, success: bool, 
                                           message: str, email: Optional[str] = None) -> bool:
        """
        Send email verification notification
        
        Args:
            user_id: User ID to send notification to
            success: Whether the email verification was successful
            message: Notification message
            email: Email address that was verified
            
        Returns:
            True if notification sent successfully
        """
        try:
            notification = NotificationMessage(
                id=str(uuid.uuid4()),
                type=NotificationType.SUCCESS if success else NotificationType.ERROR,
                title="Email Verification" if success else "Email Verification Failed",
                message=message,
                user_id=user_id,
                priority=NotificationPriority.NORMAL,
                category=NotificationCategory.SECURITY,
                data={
                    'action': 'email_verification',
                    'success': success,
                    'email': email,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                },
                requires_action=not success
            )
            
            result = self.notification_manager.send_user_notification(user_id, notification)
            
            if result:
                self.logger.info(f"Sent email verification notification to user {user_id}: {success}")
            else:
                self.logger.error(f"Failed to send email verification notification to user {user_id}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error sending email verification notification: {e}")
            return False


def get_profile_notification_helper() -> Optional[UserProfileNotificationHelper]:
    """
    Get the user profile notification helper instance
    
    Returns:
        UserProfileNotificationHelper instance or None if not available
    """
    try:
        # Get the unified notification manager from the Flask app
        notification_manager = getattr(current_app, 'unified_notification_manager', None)
        
        if notification_manager:
            return UserProfileNotificationHelper(notification_manager)
        else:
            logger.warning("Unified notification manager not available in current app")
            return None
            
    except Exception as e:
        logger.error(f"Error getting profile notification helper: {e}")
        return None


def send_profile_notification(notification_type: str, success: bool, message: str, 
                            user_id: Optional[int] = None, **kwargs) -> bool:
    """
    Convenience function to send profile notifications
    
    Args:
        notification_type: Type of notification (profile_update, settings_change, etc.)
        success: Whether the operation was successful
        message: Notification message
        user_id: User ID (defaults to current user)
        **kwargs: Additional arguments for specific notification types
        
    Returns:
        True if notification sent successfully
    """
    try:
        helper = get_profile_notification_helper()
        if not helper:
            logger.warning("Profile notification helper not available, falling back to unified notification")
            # Fallback to unified notification system if profile helper not available
            # from notification_flash_replacement import send_notification  # Removed - using unified notification system
            # Send notification using unified system
            from notification_helpers import send_success_notification, send_error_notification
            if success:
                send_success_notification(message, 'Profile Update')
            else:
                send_error_notification(message, 'Profile Update')
            return False
        
        # Use current user if no user_id provided
        if user_id is None:
            if current_user.is_authenticated:
                user_id = current_user.id
            else:
                logger.warning("No user ID provided and no authenticated user")
                return False
        
        # Route to appropriate notification method
        if notification_type == 'profile_update':
            return helper.send_profile_update_notification(
                user_id, success, message, kwargs.get('details')
            )
        elif notification_type == 'settings_change':
            return helper.send_settings_change_notification(
                user_id, kwargs.get('setting_name', 'unknown'), success, message,
                kwargs.get('old_value'), kwargs.get('new_value')
            )
        elif notification_type == 'password_change':
            return helper.send_password_change_notification(
                user_id, success, message, kwargs.get('security_details')
            )
        elif notification_type == 'account_status':
            return helper.send_account_status_notification(
                user_id, kwargs.get('status_change', 'unknown'), message,
                kwargs.get('admin_action', False), kwargs.get('admin_user_id')
            )
        elif notification_type == 'permission_change':
            return helper.send_permission_change_notification(
                user_id, kwargs.get('old_role', ''), kwargs.get('new_role', ''),
                message, kwargs.get('admin_user_id')
            )
        elif notification_type == 'email_verification':
            return helper.send_email_verification_notification(
                user_id, success, message, kwargs.get('email')
            )
        else:
            logger.warning(f"Unknown notification type: {notification_type}")
            return False
            
    except Exception as e:
        logger.error(f"Error sending profile notification: {e}")
        return False
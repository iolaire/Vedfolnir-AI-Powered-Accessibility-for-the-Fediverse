# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Notification Helper Functions

This module provides convenient helper functions for sending notifications
through the unified notification system from Flask routes and other components.
"""

import uuid
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from flask import current_app, session
from unified_notification_manager import (
    NotificationMessage, AdminNotificationMessage, SystemNotificationMessage
)
from models import NotificationType, NotificationPriority, NotificationCategory

logger = logging.getLogger(__name__)


def send_user_notification(
    message: str,
    notification_type: NotificationType = NotificationType.INFO,
    title: Optional[str] = None,
    user_id: Optional[int] = None,
    category: NotificationCategory = NotificationCategory.USER,
    priority: NotificationPriority = NotificationPriority.NORMAL,
    data: Optional[Dict[str, Any]] = None,
    requires_action: bool = False,
    action_url: Optional[str] = None,
    action_text: Optional[str] = None
) -> bool:
    """
    Send a notification to a specific user
    
    Args:
        message: The notification message text
        notification_type: Type of notification (SUCCESS, ERROR, WARNING, INFO)
        title: Optional title for the notification
        user_id: Target user ID (defaults to current session user)
        category: Notification category
        priority: Notification priority
        data: Optional additional data
        requires_action: Whether notification requires user action
        action_url: URL for action button
        action_text: Text for action button
        
    Returns:
        True if notification was sent successfully, False otherwise
    """
    try:
        # Get notification manager
        notification_manager = getattr(current_app, 'unified_notification_manager', None)
        if not notification_manager:
            logger.warning("Unified notification manager not available")
            return False
        
        # Get user ID from session if not provided
        if user_id is None:
            user_id = session.get('user_id')
            if not user_id:
                logger.warning("No user ID available for notification")
                return False
        
        # Generate title if not provided
        if title is None:
            title_map = {
                NotificationType.SUCCESS: "Success",
                NotificationType.ERROR: "Error", 
                NotificationType.WARNING: "Warning",
                NotificationType.INFO: "Information"
            }
            title = title_map.get(notification_type, "Notification")
        
        # Create notification message
        notification = NotificationMessage(
            id=str(uuid.uuid4()),
            type=notification_type,
            title=title,
            message=message,
            user_id=user_id,
            priority=priority,
            category=category,
            data=data or {},
            requires_action=requires_action,
            action_url=action_url,
            action_text=action_text
        )
        
        # Send notification
        success = notification_manager.send_user_notification(user_id, notification)
        
        if success:
            logger.debug(f"Sent notification to user {user_id}: {message}")
        else:
            logger.warning(f"Failed to send notification to user {user_id}: {message}")
            
        return success
        
    except Exception as e:
        logger.error(f"Error sending user notification: {e}")
        return False


def send_admin_notification(
    message: str,
    notification_type: NotificationType = NotificationType.INFO,
    title: Optional[str] = None,
    priority: NotificationPriority = NotificationPriority.NORMAL,
    data: Optional[Dict[str, Any]] = None,
    system_health_data: Optional[Dict[str, Any]] = None,
    user_action_data: Optional[Dict[str, Any]] = None,
    security_event_data: Optional[Dict[str, Any]] = None,
    requires_admin_action: bool = False
) -> bool:
    """
    Send a notification to all admin users
    
    Args:
        message: The notification message text
        notification_type: Type of notification
        title: Optional title for the notification
        priority: Notification priority
        data: Optional additional data
        system_health_data: System health related data
        user_action_data: User action related data
        security_event_data: Security event related data
        requires_admin_action: Whether notification requires admin action
        
    Returns:
        True if notification was sent successfully, False otherwise
    """
    try:
        # Get notification manager
        notification_manager = getattr(current_app, 'unified_notification_manager', None)
        if not notification_manager:
            logger.warning("Unified notification manager not available")
            return False
        
        # Generate title if not provided
        if title is None:
            title_map = {
                NotificationType.SUCCESS: "Admin Success",
                NotificationType.ERROR: "Admin Error",
                NotificationType.WARNING: "Admin Warning", 
                NotificationType.INFO: "Admin Information"
            }
            title = title_map.get(notification_type, "Admin Notification")
        
        # Create admin notification message
        notification = AdminNotificationMessage(
            id=str(uuid.uuid4()),
            type=notification_type,
            title=title,
            message=message,
            priority=priority,
            category=NotificationCategory.ADMIN,
            data=data or {},
            admin_only=True,
            system_health_data=system_health_data,
            user_action_data=user_action_data,
            security_event_data=security_event_data,
            requires_admin_action=requires_admin_action
        )
        
        # Send admin notification
        success = notification_manager.send_admin_notification(notification)
        
        if success:
            logger.debug(f"Sent admin notification: {message}")
        else:
            logger.warning(f"Failed to send admin notification: {message}")
            
        return success
        
    except Exception as e:
        logger.error(f"Error sending admin notification: {e}")
        return False


def send_system_notification(
    message: str,
    notification_type: NotificationType = NotificationType.INFO,
    title: Optional[str] = None,
    priority: NotificationPriority = NotificationPriority.NORMAL,
    data: Optional[Dict[str, Any]] = None,
    maintenance_info: Optional[Dict[str, Any]] = None,
    system_status: Optional[str] = None,
    estimated_duration: Optional[int] = None,
    affects_functionality: Optional[list] = None
) -> bool:
    """
    Broadcast a system notification to all users
    
    Args:
        message: The notification message text
        notification_type: Type of notification
        title: Optional title for the notification
        priority: Notification priority
        data: Optional additional data
        maintenance_info: Maintenance related information
        system_status: Current system status
        estimated_duration: Estimated duration in minutes
        affects_functionality: List of affected functionality
        
    Returns:
        True if notification was broadcast successfully, False otherwise
    """
    try:
        # Get notification manager
        notification_manager = getattr(current_app, 'unified_notification_manager', None)
        if not notification_manager:
            logger.warning("Unified notification manager not available")
            return False
        
        # Generate title if not provided
        if title is None:
            title_map = {
                NotificationType.SUCCESS: "System Update",
                NotificationType.ERROR: "System Error",
                NotificationType.WARNING: "System Warning",
                NotificationType.INFO: "System Information"
            }
            title = title_map.get(notification_type, "System Notification")
        
        # Create system notification message
        notification = SystemNotificationMessage(
            id=str(uuid.uuid4()),
            type=notification_type,
            title=title,
            message=message,
            priority=priority,
            category=NotificationCategory.SYSTEM,
            data=data or {},
            broadcast_to_all=True,
            maintenance_info=maintenance_info,
            system_status=system_status,
            estimated_duration=estimated_duration,
            affects_functionality=affects_functionality or []
        )
        
        # Broadcast system notification
        success = notification_manager.broadcast_system_notification(notification)
        
        if success:
            logger.debug(f"Broadcast system notification: {message}")
        else:
            logger.warning(f"Failed to broadcast system notification: {message}")
            
        return success
        
    except Exception as e:
        logger.error(f"Error broadcasting system notification: {e}")
        return False


def send_success_notification(message: str, title: str = "Success", user_id: Optional[int] = None) -> bool:
    """Convenience function for success notifications"""
    return send_user_notification(
        message=message,
        notification_type=NotificationType.SUCCESS,
        title=title,
        user_id=user_id,
        category=NotificationCategory.USER
    )


def send_error_notification(message: str, title: str = "Error", user_id: Optional[int] = None) -> bool:
    """Convenience function for error notifications"""
    return send_user_notification(
        message=message,
        notification_type=NotificationType.ERROR,
        title=title,
        user_id=user_id,
        category=NotificationCategory.USER
    )


def send_warning_notification(message: str, title: str = "Warning", user_id: Optional[int] = None) -> bool:
    """Convenience function for warning notifications"""
    return send_user_notification(
        message=message,
        notification_type=NotificationType.WARNING,
        title=title,
        user_id=user_id,
        category=NotificationCategory.USER
    )


def send_info_notification(message: str, title: str = "Information", user_id: Optional[int] = None) -> bool:
    """Convenience function for info notifications"""
    return send_user_notification(
        message=message,
        notification_type=NotificationType.INFO,
        title=title,
        user_id=user_id,
        category=NotificationCategory.USER
    )


def send_security_notification(
    message: str,
    notification_type: NotificationType = NotificationType.WARNING,
    title: str = "Security Alert",
    priority: NotificationPriority = NotificationPriority.HIGH,
    security_event_data: Optional[Dict[str, Any]] = None
) -> bool:
    """Convenience function for security notifications to admins"""
    return send_admin_notification(
        message=message,
        notification_type=notification_type,
        title=title,
        priority=priority,
        security_event_data=security_event_data,
        requires_admin_action=True
    )


def send_maintenance_notification(
    message: str,
    notification_type: NotificationType = NotificationType.INFO,
    title: str = "Maintenance Notice",
    estimated_duration: Optional[int] = None,
    affects_functionality: Optional[list] = None
) -> bool:
    """Convenience function for maintenance notifications"""
    return send_system_notification(
        message=message,
        notification_type=notification_type,
        title=title,
        priority=NotificationPriority.HIGH,
        estimated_duration=estimated_duration,
        affects_functionality=affects_functionality,
        maintenance_info={
            'scheduled': True,
            'start_time': datetime.now(timezone.utc).isoformat()
        }
    )
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# MIGRATION NOTE: Flash messages in this file have been commented out as part of
# the notification system migration. The application now uses the unified
# WebSocket-based notification system. These comments should be replaced with
# appropriate unified notification calls in a future update.


from unified_notification_manager import UnifiedNotificationManager
"""
Dashboard Notification Helpers

Helper functions for sending notifications from route handlers and other parts
of the application to the unified notification system.
"""

import logging
from typing import Dict, Any, Optional, Union
from flask import current_app
from flask_login import current_user
# from notification_flash_replacement import send_notification  # Removed - using unified notification system

from unified_notification_manager import NotificationMessage, NotificationType, NotificationPriority, NotificationCategory

logger = logging.getLogger(__name__)


def send_dashboard_notification(message: str, notification_type: str = 'info', 
                              title: Optional[str] = None, user_id: Optional[int] = None,
                              data: Optional[Dict[str, Any]] = None, 
                              fallback_to_flash: bool = True) -> bool:
    """
    Send notification to user dashboard via unified notification system
    
    Args:
        message: Notification message
        notification_type: Type of notification ('success', 'warning', 'error', 'info', 'progress')
        title: Optional notification title
        user_id: Target user ID (defaults to current user)
        data: Optional additional data
        fallback_to_flash: Whether to fallback to Flask flash messages if notification system unavailable
        
    Returns:
        True if notification sent successfully, False otherwise
    """
    try:
        # Get unified notification manager
        notification_manager = getattr(current_app, 'unified_notification_manager', None)
        
        if not notification_manager:
            if fallback_to_flash:
                # Fallback to Flask flash messages
                flash_category = 'danger' if notification_type == 'error' else notification_type
                flash(message, flash_category)
                logger.debug(f"Sent notification via flash fallback: {message}")
                return True
            else:
                logger.warning("Unified notification manager not available and fallback disabled")
                return False
        
        # Determine target user
        target_user_id = user_id
        if not target_user_id and current_user.is_authenticated:
            target_user_id = current_user.id
        
        if not target_user_id:
            logger.warning("No target user ID available for notification")
            return False
        
        # Convert string type to enum
        try:
            notification_type_enum = NotificationType(notification_type.upper())
        except ValueError:
            notification_type_enum = NotificationType.INFO
            logger.warning(f"Invalid notification type '{notification_type}', using INFO")
        
        # Create notification message
        notification = NotificationMessage(
            id=f"dashboard_{target_user_id}_{int(datetime.now().timestamp() * 1000)}",
            type=notification_type_enum,
            title=title or get_default_title(notification_type_enum),
            message=message,
            user_id=target_user_id,
            priority=NotificationPriority.NORMAL,
            category=NotificationCategory.USER,
            data=data or {}
        )
        
        # Send notification
        success = notification_manager.send_user_notification(target_user_id, notification)
        
        if success:
            logger.debug(f"Sent dashboard notification to user {target_user_id}: {message}")
        else:
            logger.warning(f"Failed to send dashboard notification to user {target_user_id}")
            
            # Fallback to flash if enabled
            if fallback_to_flash:
                flash_category = 'danger' if notification_type == 'error' else notification_type
                flash(message, flash_category)
        
        return success
        
    except Exception as e:
        logger.error(f"Error sending dashboard notification: {e}")
        
        # Fallback to flash if enabled
        if fallback_to_flash:
            try:
                flash_category = 'danger' if notification_type == 'error' else notification_type
                flash(message, flash_category)
                return True
            except Exception as flash_error:
                logger.error(f"Flash fallback also failed: {flash_error}")
        
        return False


def send_caption_progress_notification(progress: int, total: int, message: str = None,
                                     task_id: str = None, user_id: Optional[int] = None) -> bool:
    """
    Send caption processing progress notification
    
    Args:
        progress: Current progress count
        total: Total items to process
        message: Optional custom message
        task_id: Task identifier
        user_id: Target user ID (defaults to current user)
        
    Returns:
        True if notification sent successfully, False otherwise
    """
    try:
        dashboard_handlers = getattr(current_app, 'dashboard_handlers', None)
        
        if not dashboard_handlers:
            logger.warning("Dashboard handlers not available for caption progress notification")
            return False
        
        # Determine target user
        target_user_id = user_id
        if not target_user_id and current_user.is_authenticated:
            target_user_id = current_user.id
        
        if not target_user_id:
            logger.warning("No target user ID available for caption progress notification")
            return False
        
        # Calculate percentage
        percentage = int((progress / total) * 100) if total > 0 else 0
        
        # Create progress data
        progress_data = {
            'progress': percentage,
            'current': progress,
            'total': total,
            'task_id': task_id or 'default',
            'status': 'processing',
            'message': message or f"Processing {progress} of {total} images..."
        }
        
        # Send progress notification
        dashboard_handlers.send_caption_progress_notification(target_user_id, progress_data)
        
        logger.debug(f"Sent caption progress notification to user {target_user_id}: {progress}/{total}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending caption progress notification: {e}")
        return False


def send_caption_status_notification(status: str, message: str = None, count: int = None,
                                   task_id: str = None, error: str = None,
                                   user_id: Optional[int] = None) -> bool:
    """
    Send caption processing status notification
    
    Args:
        status: Status ('completed', 'failed', 'cancelled', etc.)
        message: Optional custom message
        count: Number of items processed
        task_id: Task identifier
        error: Error message if status is 'failed'
        user_id: Target user ID (defaults to current user)
        
    Returns:
        True if notification sent successfully, False otherwise
    """
    try:
        dashboard_handlers = getattr(current_app, 'dashboard_handlers', None)
        
        if not dashboard_handlers:
            logger.warning("Dashboard handlers not available for caption status notification")
            return False
        
        # Determine target user
        target_user_id = user_id
        if not target_user_id and current_user.is_authenticated:
            target_user_id = current_user.id
        
        if not target_user_id:
            logger.warning("No target user ID available for caption status notification")
            return False
        
        # Create status data
        status_data = {
            'status': status,
            'task_id': task_id or 'default',
            'message': message,
            'count': count,
            'error': error
        }
        
        # Send status notification
        dashboard_handlers.send_caption_status_notification(target_user_id, status_data)
        
        logger.info(f"Sent caption status notification to user {target_user_id}: {status}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending caption status notification: {e}")
        return False


def send_platform_status_notification(status: str, platform_name: str, platform_id: int = None,
                                     error: str = None, user_id: Optional[int] = None) -> bool:
    """
    Send platform operation status notification
    
    Args:
        status: Platform status ('connected', 'disconnected', 'error', 'switched')
        platform_name: Name of the platform
        platform_id: Platform ID
        error: Error message if status is 'error'
        user_id: Target user ID (defaults to current user)
        
    Returns:
        True if notification sent successfully, False otherwise
    """
    try:
        dashboard_handlers = getattr(current_app, 'dashboard_handlers', None)
        
        if not dashboard_handlers:
            logger.warning("Dashboard handlers not available for platform status notification")
            return False
        
        # Determine target user
        target_user_id = user_id
        if not target_user_id and current_user.is_authenticated:
            target_user_id = current_user.id
        
        if not target_user_id:
            logger.warning("No target user ID available for platform status notification")
            return False
        
        # Create platform data
        platform_data = {
            'status': status,
            'platform_name': platform_name,
            'platform_id': platform_id,
            'error': error
        }
        
        # Send platform notification
        dashboard_handlers.send_platform_status_notification(target_user_id, platform_data)
        
        logger.info(f"Sent platform status notification to user {target_user_id}: {platform_name} {status}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending platform status notification: {e}")
        return False


def send_system_notification_to_dashboard_users(message: str, notification_type: str = 'info',
                                               title: str = "System Notification") -> bool:
    """
    Send system notification to all dashboard users
    
    Args:
        message: Notification message
        notification_type: Type of notification
        title: Notification title
        
    Returns:
        True if notification sent successfully, False otherwise
    """
    try:
        dashboard_handlers = getattr(current_app, 'dashboard_handlers', None)
        
        if not dashboard_handlers:
            logger.warning("Dashboard handlers not available for system notification")
            return False
        
        # Convert string type to enum
        try:
            notification_type_enum = NotificationType(notification_type.upper())
        except ValueError:
            notification_type_enum = NotificationType.INFO
            logger.warning(f"Invalid notification type '{notification_type}', using INFO")
        
        # Send system notification
        dashboard_handlers.send_system_notification(message, notification_type_enum, title)
        
        logger.info(f"Sent system notification to dashboard users: {title}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending system notification to dashboard users: {e}")
        return False


def get_default_title(notification_type: NotificationType) -> str:
    """
    Get default title for notification type
    
    Args:
        notification_type: Notification type enum
        
    Returns:
        Default title string
    """
    titles = {
        NotificationType.SUCCESS: "Success",
        NotificationType.WARNING: "Warning",
        NotificationType.ERROR: "Error",
        NotificationType.INFO: "Information",
        NotificationType.PROGRESS: "Processing"
    }
    
    return titles.get(notification_type, "Notification")


# Import datetime for timestamp generation
from datetime import datetime
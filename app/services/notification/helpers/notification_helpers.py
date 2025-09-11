# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Notification Helper Functions

This module provides convenient helper functions for sending notifications
through the unified notification system from Flask routes and other components.
Includes consolidated adapters for specialized notification types.
"""

import uuid
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from flask import current_app, has_app_context, session
from app.services.notification.manager.unified_manager import (
    NotificationMessage, AdminNotificationMessage, SystemNotificationMessage
)
from models import NotificationType, NotificationPriority, NotificationCategory

logger = logging.getLogger(__name__)

def _get_notification_manager():
    """Get the unified notification manager from the current Flask app context"""
    if not has_app_context():
        logger.warning("No Flask app context available for notification manager")
        return None
    
    return getattr(current_app, 'unified_notification_manager', None)

# Import adapters for consolidated notification types
try:
    from app.services.notification.adapters.service_adapters import (
        StorageNotificationAdapter,
        PlatformNotificationAdapter, 
        DashboardNotificationAdapter,
        MonitoringNotificationAdapter,
        PerformanceNotificationAdapter,
        HealthNotificationAdapter
    )
    from app.services.notification.manager.unified_manager import UnifiedNotificationManager
    ADAPTERS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Notification service adapters not available: {e}")
    ADAPTERS_AVAILABLE = False


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
            # For anonymous users (like during registration), store notifications in session
            if not user_id:
                logger.debug("No user ID available for notification - storing in session for anonymous user")
                
                # Generate title if not provided
                if title is None:
                    title_map = {
                        NotificationType.SUCCESS: "Success",
                        NotificationType.ERROR: "Error", 
                        NotificationType.WARNING: "Warning",
                        NotificationType.INFO: "Information"
                    }
                    title = title_map.get(notification_type, "Notification")
                
                # Store notification in session for anonymous users
                if 'anonymous_notifications' not in session:
                    session['anonymous_notifications'] = []
                
                notification_data = {
                    'id': str(uuid.uuid4()),
                    'type': notification_type.value,
                    'title': title,
                    'message': message,
                    'priority': priority.value,
                    'category': category.value,
                    'data': data or {},
                    'requires_action': requires_action,
                    'action_url': action_url,
                    'action_text': action_text,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                
                session['anonymous_notifications'].append(notification_data)
                session.modified = True
                
                logger.info(f"Anonymous user notification stored in session: {title} - {message}")
                return True
        
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


# Consolidated notification helper functions

def send_storage_notification(user_id: int, storage_context) -> bool:
    """Convenience function for storage notifications"""
    if not has_app_context():
        return True
    
    if not ADAPTERS_AVAILABLE:
        logger.error("Notification service adapters not available")
        return False
        
    if not isinstance(user_id, int) or user_id <= 0:
        logger.error("Invalid user_id for storage notification")
        return False
        
    try:
        notification_manager = getattr(current_app, 'unified_notification_manager', None)
        if not isinstance(notification_manager, UnifiedNotificationManager):
            logger.error("Unified notification manager not available or invalid type")
            return False
            
        adapter = StorageNotificationAdapter(notification_manager)
        return adapter.send_storage_limit_notification(user_id, storage_context)
    except Exception as e:
        logger.error(f"Error sending storage notification: {e}")
        return False


def send_platform_notification(user_id: int, operation_result) -> bool:
    """Convenience function for platform notifications"""
    if not has_app_context():
        return True
    
    if not ADAPTERS_AVAILABLE:
        logger.error("Notification service adapters not available")
        return False
        
    if not isinstance(user_id, int) or user_id <= 0:
        logger.error("Invalid user_id for platform notification")
        return False
        
    try:
        notification_manager = getattr(current_app, 'unified_notification_manager', None)
        if not isinstance(notification_manager, UnifiedNotificationManager):
            logger.error("Unified notification manager not available or invalid type")
            return False
            
        adapter = PlatformNotificationAdapter(notification_manager)
        return adapter.send_platform_operation_notification(user_id, operation_result)
        
    except Exception as e:
        logger.error(f"Error sending platform notification: {e}")
        return False


def send_email_notification(subject: str, message: str, user_id: int = None, 
                           email_template: str = None, template_data: dict = None) -> bool:
    """
    Send email notification through unified system
    
    Args:
        subject: Email subject line
        message: Email message content
        user_id: Target user ID (uses current_user if not provided)
        email_template: Optional email template name
        template_data: Optional template data
        
    Returns:
        True if notification sent successfully, False otherwise
    """
    try:
        from flask_login import current_user
        from app.services.notification.adapters.service_adapters import EmailNotificationAdapter
        
        target_user_id = user_id or (current_user.id if current_user.is_authenticated else None)
        if not target_user_id:
            logger.error("No user ID provided for email notification")
            return False
        
        # Get unified notification manager
        manager = _get_notification_manager()
        if not manager:
            return False
        
        # Create email adapter and send notification
        email_adapter = EmailNotificationAdapter(manager)
        return email_adapter.send_email_notification(
            user_id=target_user_id,
            subject=subject,
            message=message,
            email_template=email_template,
            template_data=template_data
        )
        
    except Exception as e:
        logger.error(f"Error sending email notification: {e}")
        return False


def send_verification_email(verification_link: str, user_id: int = None) -> bool:
    """Send email verification notification"""
    try:
        from flask_login import current_user
        from app.services.notification.adapters.service_adapters import EmailNotificationAdapter
        
        target_user_id = user_id or (current_user.id if current_user.is_authenticated else None)
        if not target_user_id:
            logger.error("No user ID provided for verification email")
            return False
        
        manager = _get_notification_manager()
        if not manager:
            return False
        
        email_adapter = EmailNotificationAdapter(manager)
        return email_adapter.send_verification_email(target_user_id, verification_link)
        
    except Exception as e:
        logger.error(f"Error sending verification email: {e}")
        return False


def send_password_reset_email(reset_link: str, user_id: int = None) -> bool:
    """Send password reset email notification"""
    try:
        from flask_login import current_user
        from app.services.notification.adapters.service_adapters import EmailNotificationAdapter
        
        target_user_id = user_id or (current_user.id if current_user.is_authenticated else None)
        if not target_user_id:
            logger.error("No user ID provided for password reset email")
            return False
        
        manager = _get_notification_manager()
        if not manager:
            return False
        
        email_adapter = EmailNotificationAdapter(manager)
        return email_adapter.send_password_reset_email(target_user_id, reset_link)
        
    except Exception as e:
        logger.error(f"Error sending password reset email: {e}")
        return False


def send_gdpr_export_email(download_link: str, user_id: int = None) -> bool:
    """Send GDPR data export email notification"""
    try:
        from flask_login import current_user
        from app.services.notification.adapters.service_adapters import EmailNotificationAdapter
        
        target_user_id = user_id or (current_user.id if current_user.is_authenticated else None)
        if not target_user_id:
            logger.error("No user ID provided for GDPR export email")
            return False
        
        manager = _get_notification_manager()
        if not manager:
            return False
        
        email_adapter = EmailNotificationAdapter(manager)
        return email_adapter.send_gdpr_export_email(target_user_id, download_link)
        
    except Exception as e:
        logger.error(f"Error sending GDPR export email: {e}")
        return False


def send_dashboard_notification(user_id: int, update_type: str, message: str, data: Optional[Dict] = None) -> bool:
    """Convenience function for dashboard notifications"""
    if not has_app_context():
        return True
    
    if not DashboardNotificationAdapter:
        logger.error("DashboardNotificationAdapter not available")
        return False
        
    try:
        notification_manager = getattr(current_app, 'unified_notification_manager', None)
        if not notification_manager:
            logger.error("Unified notification manager not available")
            return False
            
        adapter = DashboardNotificationAdapter(notification_manager)
        return adapter.send_dashboard_update_notification(user_id, update_type, message, data)
    except Exception as e:
        logger.error(f"Error sending dashboard notification: {e}")
        return False


def send_monitoring_notification(user_id: int, alert_type: str, message: str, severity: str = "normal", data: Optional[Dict] = None) -> bool:
    """Convenience function for monitoring notifications"""
    if not has_app_context():
        return True
    
    if not MonitoringNotificationAdapter:
        logger.error("MonitoringNotificationAdapter not available")
        return False
        
    try:
        notification_manager = getattr(current_app, 'unified_notification_manager', None)
        if not notification_manager:
            logger.error("Unified notification manager not available")
            return False
            
        adapter = MonitoringNotificationAdapter(notification_manager)
        return adapter.send_monitoring_alert(user_id, alert_type, message, severity, data)
    except Exception as e:
        logger.error(f"Error sending monitoring notification: {e}")
        return False


def send_performance_notification(user_id: int, metrics: Dict[str, float], threshold_exceeded: str, recovery_action: str = None) -> bool:
    """Convenience function for performance notifications"""
    if not has_app_context():
        return True
    
    if not PerformanceNotificationAdapter:
        logger.error("PerformanceNotificationAdapter not available")
        return False
        
    try:
        notification_manager = getattr(current_app, 'unified_notification_manager', None)
        if not notification_manager:
            logger.error("Unified notification manager not available")
            return False
            
        adapter = PerformanceNotificationAdapter(notification_manager)
        return adapter.send_performance_alert(user_id, metrics, threshold_exceeded, recovery_action)
    except Exception as e:
        logger.error(f"Error sending performance notification: {e}")
        return False


def send_health_notification(user_id: int, component: str, status: str, message: str, data: Optional[Dict] = None) -> bool:
    """Convenience function for health check notifications"""
    if not has_app_context():
        return True
    
    if not HealthNotificationAdapter:
        logger.error("HealthNotificationAdapter not available")
        return False
        
    try:
        notification_manager = getattr(current_app, 'unified_notification_manager', None)
        if not notification_manager:
            logger.error("Unified notification manager not available")
            return False
            
        adapter = HealthNotificationAdapter(notification_manager)
        return adapter.send_health_alert(user_id, component, status, message, data)
    except Exception as e:
        logger.error(f"Error sending health notification: {e}")
        return False


def get_anonymous_notifications() -> list:
    """
    Get anonymous user notifications from session and clear them
    
    Returns:
        List of notification dictionaries for anonymous users
    """
    try:
        if not has_app_context():
            return []
        
        anonymous_notifications = session.get('anonymous_notifications', [])
        
        if anonymous_notifications:
            logger.debug(f"Retrieved {len(anonymous_notifications)} anonymous notifications from session")
            # Clear notifications from session after retrieval
            session['anonymous_notifications'] = []
            session.modified = True
        
        return anonymous_notifications
        
    except Exception as e:
        logger.error(f"Error retrieving anonymous notifications: {e}")
        return []


def clear_anonymous_notifications() -> bool:
    """
    Clear all anonymous notifications from session
    
    Returns:
        True if notifications were cleared successfully
    """
    try:
        if not has_app_context():
            return False
        
        if 'anonymous_notifications' in session:
            session['anonymous_notifications'] = []
            session.modified = True
            logger.debug("Cleared anonymous notifications from session")
        
        return True
        
    except Exception as e:
        logger.error(f"Error clearing anonymous notifications: {e}")
        return False
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Notification Service Adapters

Provides adapters for specialized notification services to use the unified notification system.
This consolidates multiple notification systems into a single, consistent interface.
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from dataclasses import dataclass

from app.services.notification.manager.unified_manager import (
    UnifiedNotificationManager, 
    NotificationMessage,
    StorageNotificationMessage,
    PerformanceNotificationMessage,
    DashboardNotificationMessage,
    MonitoringNotificationMessage,
    HealthNotificationMessage
)
from models import NotificationType, NotificationCategory, NotificationPriority

logger = logging.getLogger(__name__)

# Specialized message types are now imported from app.services.notification.manager.unified_manager

class StorageNotificationAdapter:
    """Adapter for storage notifications using UnifiedNotificationManager"""
    
    def __init__(self, notification_manager: UnifiedNotificationManager):
        if not isinstance(notification_manager, UnifiedNotificationManager):
            raise TypeError("notification_manager must be UnifiedNotificationManager instance")
        self.notification_manager = notification_manager
    
    def send_storage_limit_notification(self, user_id: int, storage_context) -> bool:
        """Send storage limit notification via unified system"""
        if not isinstance(user_id, int) or user_id <= 0:
            raise ValueError("user_id must be a positive integer")
            
        try:
            # Validate storage_context attributes with proper defaults
            is_blocked = getattr(storage_context, 'is_blocked', False)
            reason = getattr(storage_context, 'reason', 'Storage limit notification')
            storage_gb = getattr(storage_context, 'storage_gb', None)
            limit_gb = getattr(storage_context, 'limit_gb', None)
            usage_percentage = getattr(storage_context, 'usage_percentage', None)
            blocked_at = getattr(storage_context, 'blocked_at', None)
            should_hide_form = getattr(storage_context, 'should_hide_form', False)
            
            # Validate numeric values
            if storage_gb is not None and not isinstance(storage_gb, (int, float)):
                storage_gb = None
            if limit_gb is not None and not isinstance(limit_gb, (int, float)):
                limit_gb = None
            if usage_percentage is not None and not isinstance(usage_percentage, (int, float)):
                usage_percentage = None
            
            message = StorageNotificationMessage(
                id=str(uuid.uuid4()),
                type=NotificationType.WARNING if is_blocked else NotificationType.INFO,
                title="Storage Limit Alert",
                message=reason,
                user_id=user_id,
                storage_gb=storage_gb,
                limit_gb=limit_gb,
                usage_percentage=usage_percentage,
                blocked_at=blocked_at,
                should_hide_form=bool(should_hide_form),
                priority=NotificationPriority.HIGH if is_blocked else NotificationPriority.NORMAL
            )
            
            return self.notification_manager.send_user_notification(user_id, message)
            
        except Exception as e:
            logger.error(f"Error sending storage notification: {e}")
            return False

class PlatformNotificationAdapter:
    """Adapter for platform notifications using UnifiedNotificationManager"""
    
    def __init__(self, notification_manager: UnifiedNotificationManager):
        if not isinstance(notification_manager, UnifiedNotificationManager):
            raise TypeError("notification_manager must be UnifiedNotificationManager instance")
        self.notification_manager = notification_manager
    
    def send_platform_operation_notification(self, user_id: int, operation_result) -> bool:
        """Send platform operation notification via unified system"""
        if not isinstance(user_id, int) or user_id <= 0:
            raise ValueError("user_id must be a positive integer")
            
        try:
            # Validate operation_result attributes with proper defaults
            success = getattr(operation_result, 'success', False)
            message_text = getattr(operation_result, 'message', 'Platform operation completed')
            operation_type = getattr(operation_result, 'operation_type', 'operation')
            platform_data = getattr(operation_result, 'platform_data', None)
            error_details = getattr(operation_result, 'error_details', None)
            requires_refresh = getattr(operation_result, 'requires_refresh', False)
            
            # Ensure platform_data is a dict or None
            if platform_data is not None and not isinstance(platform_data, dict):
                platform_data = {}
            
            message = NotificationMessage(
                id=str(uuid.uuid4()),
                type=NotificationType.SUCCESS if success else NotificationType.ERROR,
                title=f"Platform {operation_type.title()}",
                message=message_text,
                user_id=user_id,
                category=NotificationCategory.PLATFORM,
                priority=NotificationPriority.NORMAL,
                data={
                    'operation_type': operation_type,
                    'platform_data': platform_data,
                    'error_details': error_details,
                    'requires_refresh': bool(requires_refresh)
                }
            )
            
            return self.notification_manager.send_user_notification(user_id, message)
            
        except Exception as e:
            logger.error(f"Error sending platform notification: {e}")
            return False

class DashboardNotificationAdapter:
    """Adapter for dashboard notifications using UnifiedNotificationManager"""
    
    def __init__(self, notification_manager: UnifiedNotificationManager):
        self.notification_manager = notification_manager
    
    def send_dashboard_update_notification(self, user_id: int, update_type: str, message: str, data: Optional[Dict] = None) -> bool:
        """Send dashboard update notification via unified system"""
        try:
            notification = DashboardNotificationMessage(
                id=str(uuid.uuid4()),
                type=NotificationType.INFO,
                title=f"Dashboard Update: {update_type.title()}",
                message=message,
                user_id=user_id,
                priority=NotificationPriority.LOW,
                update_type=update_type,
                dashboard_data=data or {}
            )
            
            return self.notification_manager.send_user_notification(user_id, notification)
            
        except Exception as e:
            logger.error(f"Error sending dashboard notification: {e}")
            return False

class MonitoringNotificationAdapter:
    """Adapter for monitoring notifications using UnifiedNotificationManager"""
    
    def __init__(self, notification_manager: UnifiedNotificationManager):
        self.notification_manager = notification_manager
    
    def send_monitoring_alert(self, user_id: int, alert_type: str, message: str, severity: str = "normal", data: Optional[Dict] = None) -> bool:
        """Send monitoring alert via unified system"""
        try:
            # Map severity to notification type and priority
            type_mapping = {
                "critical": NotificationType.ERROR,
                "warning": NotificationType.WARNING,
                "info": NotificationType.INFO,
                "normal": NotificationType.INFO
            }
            
            priority_mapping = {
                "critical": NotificationPriority.CRITICAL,
                "warning": NotificationPriority.HIGH,
                "info": NotificationPriority.NORMAL,
                "normal": NotificationPriority.NORMAL
            }
            
            notification = MonitoringNotificationMessage(
                id=str(uuid.uuid4()),
                type=type_mapping.get(severity, NotificationType.INFO),
                title=f"System Alert: {alert_type.title()}",
                message=message,
                user_id=user_id,
                priority=priority_mapping.get(severity, NotificationPriority.NORMAL),
                alert_type=alert_type,
                severity=severity,
                data=data or {}
            )
            
            return self.notification_manager.send_user_notification(user_id, notification)
            
        except Exception as e:
            logger.error(f"Error sending monitoring notification: {e}")
            return False

class PerformanceNotificationAdapter:
    """Adapter for performance notifications using UnifiedNotificationManager"""
    
    def __init__(self, notification_manager: UnifiedNotificationManager):
        self.notification_manager = notification_manager
    
    def send_performance_alert(self, user_id: int, metrics: Dict[str, float], threshold_exceeded: str, recovery_action: str = None) -> bool:
        """Send performance alert via unified system"""
        try:
            message = PerformanceNotificationMessage(
                id=str(uuid.uuid4()),
                type=NotificationType.WARNING,
                title="Performance Alert",
                message=f"Performance threshold exceeded: {threshold_exceeded}",
                user_id=user_id,
                priority=NotificationPriority.HIGH,
                metrics=metrics,
                threshold_exceeded=threshold_exceeded,
                recovery_action=recovery_action
            )
            
            return self.notification_manager.send_user_notification(user_id, message)
            
        except Exception as e:
            logger.error(f"Error sending performance notification: {e}")
            return False

class HealthNotificationAdapter:
    """Adapter for health check notifications using UnifiedNotificationManager"""
    
    def __init__(self, notification_manager: UnifiedNotificationManager):
        self.notification_manager = notification_manager
    
    def send_health_alert(self, user_id: int, component: str, status: str, message: str, data: Optional[Dict] = None) -> bool:
        """Send health check alert via unified system"""
        try:
            # Map health status to notification type
            type_mapping = {
                "healthy": NotificationType.SUCCESS,
                "degraded": NotificationType.WARNING,
                "unhealthy": NotificationType.ERROR,
                "unknown": NotificationType.INFO
            }
            
            priority_mapping = {
                "healthy": NotificationPriority.LOW,
                "degraded": NotificationPriority.NORMAL,
                "unhealthy": NotificationPriority.HIGH,
                "unknown": NotificationPriority.NORMAL
            }
            
            notification = HealthNotificationMessage(
                id=str(uuid.uuid4()),
                type=type_mapping.get(status, NotificationType.INFO),
                title=f"Health Check: {component}",
                message=message,
                user_id=user_id,
                priority=priority_mapping.get(status, NotificationPriority.NORMAL),
                component=component,
                status=status,
                health_data=data or {}
            )
            
            return self.notification_manager.send_user_notification(user_id, notification)
            
        except Exception as e:
            logger.error(f"Error sending health notification: {e}")
            return False


class EmailNotificationAdapter:
    """
    Email notification adapter for the unified notification system
    
    Integrates email functionality with the unified notification manager
    to send email notifications alongside web notifications.
    """
    
    def __init__(self, notification_manager: UnifiedNotificationManager):
        if not isinstance(notification_manager, UnifiedNotificationManager):
            raise TypeError("notification_manager must be UnifiedNotificationManager instance")
        
        self.notification_manager = notification_manager
        self.logger = logging.getLogger(__name__)
    
    def send_email_notification(self, user_id: int, subject: str, message: str, 
                               email_template: str = None, template_data: dict = None) -> bool:
        """
        Send email notification through unified system
        
        Args:
            user_id: Target user ID
            subject: Email subject line
            message: Email message content
            email_template: Optional email template name
            template_data: Optional template data
            
        Returns:
            True if notification sent successfully, False otherwise
        """
        try:
            # Create notification message
            notification_message = NotificationMessage(
                id=str(uuid.uuid4()),
                type=NotificationType.INFO,
                title=subject,
                message=message,
                category=NotificationCategory.USER,
                user_id=user_id,
                priority=NotificationPriority.NORMAL,
                data={
                    'email_template': email_template,
                    'template_data': template_data or {},
                    'delivery_method': 'email'
                }
            )
            
            # Send through unified notification manager
            result = self.notification_manager.send_user_notification(user_id, notification_message)
            
            if result:
                self.logger.info(f"Email notification sent successfully to user {user_id}")
            else:
                self.logger.error(f"Failed to send email notification to user {user_id}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error sending email notification: {e}")
            return False
    
    def send_verification_email(self, user_id: int, verification_link: str) -> bool:
        """Send email verification notification"""
        return self.send_email_notification(
            user_id=user_id,
            subject="Email Verification Required",
            message=f"Please verify your email address by clicking the link: {verification_link}",
            email_template="email_verification",
            template_data={'verification_link': verification_link}
        )
    
    def send_password_reset_email(self, user_id: int, reset_link: str) -> bool:
        """Send password reset notification"""
        return self.send_email_notification(
            user_id=user_id,
            subject="Password Reset Request",
            message=f"Click the following link to reset your password: {reset_link}",
            email_template="password_reset",
            template_data={'reset_link': reset_link}
        )
    
    def send_gdpr_export_email(self, user_id: int, download_link: str) -> bool:
        """Send GDPR data export notification"""
        return self.send_email_notification(
            user_id=user_id,
            subject="Your Data Export is Ready",
            message=f"Your personal data export is ready for download: {download_link}",
            email_template="gdpr_export",
            template_data={'download_link': download_link}
        )

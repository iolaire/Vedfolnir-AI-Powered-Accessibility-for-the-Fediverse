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

from unified_notification_manager import UnifiedNotificationManager, NotificationMessage
from models import NotificationType, NotificationCategory, NotificationPriority

logger = logging.getLogger(__name__)

@dataclass
class StorageNotificationMessage(NotificationMessage):
    """Storage-specific notification message"""
    storage_gb: Optional[float] = None
    limit_gb: Optional[float] = None
    usage_percentage: Optional[float] = None
    blocked_at: Optional[datetime] = None
    should_hide_form: bool = False
    
    def __post_init__(self):
        super().__post_init__()
        self.category = NotificationCategory.STORAGE

@dataclass
class PerformanceNotificationMessage(NotificationMessage):
    """Performance monitoring notification message"""
    metrics: Optional[Dict[str, float]] = None
    threshold_exceeded: Optional[str] = None
    recovery_action: Optional[str] = None
    
    def __post_init__(self):
        super().__post_init__()
        self.category = NotificationCategory.PERFORMANCE

class StorageNotificationAdapter:
    """Adapter for storage notifications using UnifiedNotificationManager"""
    
    def __init__(self, notification_manager: UnifiedNotificationManager):
        self.notification_manager = notification_manager
    
    def send_storage_limit_notification(self, user_id: int, storage_context) -> bool:
        """Send storage limit notification via unified system"""
        try:
            message = StorageNotificationMessage(
                id=str(uuid.uuid4()),
                type=NotificationType.WARNING if getattr(storage_context, 'is_blocked', False) else NotificationType.INFO,
                title="Storage Limit Alert",
                message=getattr(storage_context, 'reason', 'Storage limit notification'),
                user_id=user_id,
                storage_gb=getattr(storage_context, 'storage_gb', None),
                limit_gb=getattr(storage_context, 'limit_gb', None),
                usage_percentage=getattr(storage_context, 'usage_percentage', None),
                blocked_at=getattr(storage_context, 'blocked_at', None),
                should_hide_form=getattr(storage_context, 'should_hide_form', False),
                priority=NotificationPriority.HIGH if getattr(storage_context, 'is_blocked', False) else NotificationPriority.NORMAL
            )
            
            return self.notification_manager.send_user_notification(user_id, message)
            
        except Exception as e:
            logger.error(f"Error sending storage notification: {e}")
            return False

class PlatformNotificationAdapter:
    """Adapter for platform notifications using UnifiedNotificationManager"""
    
    def __init__(self, notification_manager: UnifiedNotificationManager):
        self.notification_manager = notification_manager
    
    def send_platform_operation_notification(self, user_id: int, operation_result) -> bool:
        """Send platform operation notification via unified system"""
        try:
            message = NotificationMessage(
                id=str(uuid.uuid4()),
                type=NotificationType.SUCCESS if getattr(operation_result, 'success', False) else NotificationType.ERROR,
                title=f"Platform {getattr(operation_result, 'operation_type', 'Operation').title()}",
                message=getattr(operation_result, 'message', 'Platform operation completed'),
                user_id=user_id,
                category=NotificationCategory.PLATFORM,
                priority=NotificationPriority.NORMAL,
                data={
                    'operation_type': getattr(operation_result, 'operation_type', None),
                    'platform_data': getattr(operation_result, 'platform_data', None),
                    'error_details': getattr(operation_result, 'error_details', None),
                    'requires_refresh': getattr(operation_result, 'requires_refresh', False)
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
            notification = NotificationMessage(
                id=str(uuid.uuid4()),
                type=NotificationType.INFO,
                title=f"Dashboard Update: {update_type.title()}",
                message=message,
                user_id=user_id,
                category=NotificationCategory.DASHBOARD,
                priority=NotificationPriority.LOW,
                data=data or {}
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
            
            notification = NotificationMessage(
                id=str(uuid.uuid4()),
                type=type_mapping.get(severity, NotificationType.INFO),
                title=f"System Alert: {alert_type.title()}",
                message=message,
                user_id=user_id,
                category=NotificationCategory.MONITORING,
                priority=priority_mapping.get(severity, NotificationPriority.NORMAL),
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
            
            notification = NotificationMessage(
                id=str(uuid.uuid4()),
                type=type_mapping.get(status, NotificationType.INFO),
                title=f"Health Check: {component}",
                message=message,
                user_id=user_id,
                category=NotificationCategory.HEALTH,
                priority=priority_mapping.get(status, NotificationPriority.NORMAL),
                data=data or {'component': component, 'status': status}
            )
            
            return self.notification_manager.send_user_notification(user_id, notification)
            
        except Exception as e:
            logger.error(f"Error sending health notification: {e}")
            return False

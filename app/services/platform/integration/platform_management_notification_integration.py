# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Platform Management Notification Integration

This module provides real-time WebSocket notifications for platform management operations,
replacing legacy flash messages and JavaScript alerts with the unified notification system.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from flask import current_app
from flask_login import current_user

from unified_notification_manager import (
    UnifiedNotificationManager, NotificationMessage, SystemNotificationMessage
)
from models import NotificationType, NotificationPriority, NotificationCategory
from page_notification_integrator import PageNotificationIntegrator, PageType

logger = logging.getLogger(__name__)


@dataclass
class PlatformOperationResult:
    """Result of a platform operation with notification data"""
    success: bool
    message: str
    operation_type: str
    platform_data: Optional[Dict[str, Any]] = None
    error_details: Optional[str] = None
    requires_refresh: bool = False


class PlatformManagementNotificationService:
    """
    Service for sending real-time platform management notifications via WebSocket
    
    Integrates with the unified notification system to provide consistent,
    real-time updates for platform operations including connection, switching,
    testing, and configuration changes.
    """
    
    def __init__(self, notification_manager: UnifiedNotificationManager,
                 page_integrator: PageNotificationIntegrator):
        """
        Initialize platform management notification service
        
        Args:
            notification_manager: Unified notification manager instance
            page_integrator: Page notification integrator instance
        """
        self.notification_manager = notification_manager
        self.page_integrator = page_integrator
        
        # Platform operation types
        self.OPERATION_TYPES = {
            'ADD_PLATFORM': 'add_platform',
            'SWITCH_PLATFORM': 'switch_platform', 
            'TEST_CONNECTION': 'test_connection',
            'EDIT_PLATFORM': 'edit_platform',
            'DELETE_PLATFORM': 'delete_platform',
            'PLATFORM_ERROR': 'platform_error',
            'PLATFORM_AUTH_ERROR': 'platform_auth_error'
        }
        
        logger.info("Platform Management Notification Service initialized")
    
    def send_platform_connection_notification(self, user_id: int, 
                                            result: PlatformOperationResult) -> bool:
        """
        Send platform connection status notification
        
        Args:
            user_id: Target user ID
            result: Platform operation result
            
        Returns:
            True if notification sent successfully
        """
        try:
            # Determine notification type based on operation result
            if result.success:
                notification_type = NotificationType.SUCCESS
                priority = NotificationPriority.NORMAL
                title = "Platform Connection"
            else:
                notification_type = NotificationType.ERROR
                priority = NotificationPriority.HIGH
                title = "Platform Connection Failed"
            
            # Create notification message
            message = NotificationMessage(
                id=str(uuid.uuid4()),
                type=notification_type,
                title=title,
                message=result.message,
                user_id=user_id,
                priority=priority,
                category=NotificationCategory.PLATFORM,
                data={
                    'operation_type': result.operation_type,
                    'platform_data': result.platform_data,
                    'error_details': result.error_details,
                    'requires_refresh': result.requires_refresh,
                    'websocket_event': 'platform_connection'
                }
            )
            
            # Send via unified notification manager
            success = self.notification_manager.send_user_notification(user_id, message)
            
            if success:
                logger.info(f"Sent platform connection notification to user {user_id}: {result.operation_type}")
            else:
                logger.error(f"Failed to send platform connection notification to user {user_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending platform connection notification: {e}")
            return False
    
    def send_platform_status_notification(self, user_id: int, platform_name: str,
                                        status: str, details: Optional[str] = None) -> bool:
        """
        Send platform status update notification
        
        Args:
            user_id: Target user ID
            platform_name: Name of the platform
            status: Platform status (active, inactive, error, testing)
            details: Additional status details
            
        Returns:
            True if notification sent successfully
        """
        try:
            # Determine notification properties based on status
            status_config = {
                'active': {
                    'type': NotificationType.SUCCESS,
                    'priority': NotificationPriority.NORMAL,
                    'title': 'Platform Active',
                    'icon': '✅'
                },
                'inactive': {
                    'type': NotificationType.WARNING,
                    'priority': NotificationPriority.NORMAL,
                    'title': 'Platform Inactive',
                    'icon': '⚠️'
                },
                'error': {
                    'type': NotificationType.ERROR,
                    'priority': NotificationPriority.HIGH,
                    'title': 'Platform Error',
                    'icon': '❌'
                },
                'testing': {
                    'type': NotificationType.INFO,
                    'priority': NotificationPriority.NORMAL,
                    'title': 'Testing Connection',
                    'icon': '🔄'
                }
            }
            
            config = status_config.get(status, status_config['error'])
            
            # Format message
            message_text = f"{config['icon']} {platform_name}: {status.title()}"
            if details:
                message_text += f" - {details}"
            
            # Create notification message
            message = NotificationMessage(
                id=str(uuid.uuid4()),
                type=config['type'],
                title=config['title'],
                message=message_text,
                user_id=user_id,
                priority=config['priority'],
                category=NotificationCategory.PLATFORM,
                data={
                    'platform_name': platform_name,
                    'status': status,
                    'details': details,
                    'websocket_event': 'platform_status'
                }
            )
            
            # Send via unified notification manager
            success = self.notification_manager.send_user_notification(user_id, message)
            
            if success:
                logger.info(f"Sent platform status notification to user {user_id}: {platform_name} - {status}")
            else:
                logger.error(f"Failed to send platform status notification to user {user_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending platform status notification: {e}")
            return False
    
    def send_platform_switch_notification(self, user_id: int, from_platform: Optional[str],
                                        to_platform: str, success: bool,
                                        error_message: Optional[str] = None) -> bool:
        """
        Send platform switching notification
        
        Args:
            user_id: Target user ID
            from_platform: Previous platform name (if any)
            to_platform: New platform name
            success: Whether switch was successful
            error_message: Error message if switch failed
            
        Returns:
            True if notification sent successfully
        """
        try:
            if success:
                notification_type = NotificationType.SUCCESS
                priority = NotificationPriority.NORMAL
                title = "Platform Switched"
                if from_platform:
                    message_text = f"✅ Switched from {from_platform} to {to_platform}"
                else:
                    message_text = f"✅ Switched to {to_platform}"
            else:
                notification_type = NotificationType.ERROR
                priority = NotificationPriority.HIGH
                title = "Platform Switch Failed"
                message_text = f"❌ Failed to switch to {to_platform}"
                if error_message:
                    message_text += f": {error_message}"
            
            # Create notification message
            message = NotificationMessage(
                id=str(uuid.uuid4()),
                type=notification_type,
                title=title,
                message=message_text,
                user_id=user_id,
                priority=priority,
                category=NotificationCategory.PLATFORM,
                data={
                    'operation_type': 'switch_platform',
                    'from_platform': from_platform,
                    'to_platform': to_platform,
                    'success': success,
                    'error_message': error_message,
                    'websocket_event': 'platform_status'
                }
            )
            
            # Send via unified notification manager
            success_sent = self.notification_manager.send_user_notification(user_id, message)
            
            if success_sent:
                logger.info(f"Sent platform switch notification to user {user_id}: {to_platform}")
            else:
                logger.error(f"Failed to send platform switch notification to user {user_id}")
            
            return success_sent
            
        except Exception as e:
            logger.error(f"Error sending platform switch notification: {e}")
            return False
    
    def send_platform_authentication_error(self, user_id: int, platform_name: str,
                                         error_type: str, error_details: str) -> bool:
        """
        Send platform authentication error notification
        
        Args:
            user_id: Target user ID
            platform_name: Name of the platform with auth error
            error_type: Type of authentication error
            error_details: Detailed error message
            
        Returns:
            True if notification sent successfully
        """
        try:
            # Create notification message
            message = NotificationMessage(
                id=str(uuid.uuid4()),
                type=NotificationType.ERROR,
                title="Platform Authentication Error",
                message=f"🔐 Authentication failed for {platform_name}: {error_details}",
                user_id=user_id,
                priority=NotificationPriority.HIGH,
                category=NotificationCategory.PLATFORM,
                data={
                    'operation_type': 'platform_auth_error',
                    'platform_name': platform_name,
                    'error_type': error_type,
                    'error_details': error_details,
                    'websocket_event': 'platform_error',
                    'requires_action': True,
                    'action_text': 'Update Credentials',
                    'action_url': '/platform_management'
                },
                requires_action=True,
                action_text='Update Credentials',
                action_url='/platform_management'
            )
            
            # Send via unified notification manager
            success = self.notification_manager.send_user_notification(user_id, message)
            
            if success:
                logger.info(f"Sent platform auth error notification to user {user_id}: {platform_name}")
            else:
                logger.error(f"Failed to send platform auth error notification to user {user_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending platform authentication error notification: {e}")
            return False
    
    def send_platform_configuration_change_notification(self, user_id: int, 
                                                       platform_name: str,
                                                       change_type: str,
                                                       change_details: str) -> bool:
        """
        Send platform configuration change notification
        
        Args:
            user_id: Target user ID
            platform_name: Name of the platform that was changed
            change_type: Type of configuration change
            change_details: Details of the change
            
        Returns:
            True if notification sent successfully
        """
        try:
            # Create notification message
            message = NotificationMessage(
                id=str(uuid.uuid4()),
                type=NotificationType.INFO,
                title="Platform Configuration Updated",
                message=f"⚙️ {platform_name}: {change_details}",
                user_id=user_id,
                priority=NotificationPriority.NORMAL,
                category=NotificationCategory.PLATFORM,
                data={
                    'operation_type': 'configuration_change',
                    'platform_name': platform_name,
                    'change_type': change_type,
                    'change_details': change_details,
                    'websocket_event': 'platform_status'
                }
            )
            
            # Send via unified notification manager
            success = self.notification_manager.send_user_notification(user_id, message)
            
            if success:
                logger.info(f"Sent platform config change notification to user {user_id}: {platform_name}")
            else:
                logger.error(f"Failed to send platform config change notification to user {user_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending platform configuration change notification: {e}")
            return False
    
    def send_maintenance_mode_notification(self, user_id: int, operation_type: str,
                                         maintenance_info: Dict[str, Any]) -> bool:
        """
        Send maintenance mode notification for platform operations
        
        Args:
            user_id: Target user ID
            operation_type: Type of operation that was blocked
            maintenance_info: Maintenance mode information
            
        Returns:
            True if notification sent successfully
        """
        try:
            # Create system notification for maintenance mode
            message = SystemNotificationMessage(
                id=str(uuid.uuid4()),
                type=NotificationType.WARNING,
                title="Service Temporarily Unavailable",
                message=f"🔧 Platform {operation_type} is temporarily disabled during maintenance",
                user_id=user_id,
                priority=NotificationPriority.HIGH,
                category=NotificationCategory.MAINTENANCE,
                maintenance_info=maintenance_info,
                data={
                    'operation_type': operation_type,
                    'maintenance_active': True,
                    'websocket_event': 'platform_status'
                }
            )
            
            # Send via unified notification manager
            success = self.notification_manager.send_user_notification(user_id, message)
            
            if success:
                logger.info(f"Sent maintenance mode notification to user {user_id}: {operation_type}")
            else:
                logger.error(f"Failed to send maintenance mode notification to user {user_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending maintenance mode notification: {e}")
            return False


def create_platform_operation_result(success: bool, message: str, operation_type: str,
                                   platform_data: Optional[Dict[str, Any]] = None,
                                   error_details: Optional[str] = None,
                                   requires_refresh: bool = False) -> PlatformOperationResult:
    """
    Helper function to create platform operation result
    
    Args:
        success: Whether operation was successful
        message: Operation result message
        operation_type: Type of operation performed
        platform_data: Platform data (if applicable)
        error_details: Detailed error information (if applicable)
        requires_refresh: Whether page refresh is required
        
    Returns:
        PlatformOperationResult instance
    """
    return PlatformOperationResult(
        success=success,
        message=message,
        operation_type=operation_type,
        platform_data=platform_data,
        error_details=error_details,
        requires_refresh=requires_refresh
    )


def get_platform_notification_service() -> Optional[PlatformManagementNotificationService]:
    """
    Get platform notification service from Flask app context
    
    Returns:
        PlatformManagementNotificationService instance or None if not available
    """
    try:
        if hasattr(current_app, 'platform_notification_service'):
            return current_app.platform_notification_service
        else:
            logger.warning("Platform notification service not found in app context")
            return None
    except Exception as e:
        logger.error(f"Error getting platform notification service: {e}")
        return None


def send_platform_notification(operation_type: str, result: PlatformOperationResult,
                             user_id: Optional[int] = None) -> bool:
    """
    Convenience function to send platform notification
    
    Args:
        operation_type: Type of platform operation
        result: Platform operation result
        user_id: Target user ID (defaults to current user)
        
    Returns:
        True if notification sent successfully
    """
    try:
        if user_id is None:
            if hasattr(current_user, 'id'):
                user_id = current_user.id
            else:
                logger.error("No user ID provided and no current user available")
                return False
        
        service = get_platform_notification_service()
        if not service:
            logger.error("Platform notification service not available")
            return False
        
        return service.send_platform_connection_notification(user_id, result)
        
    except Exception as e:
        logger.error(f"Error sending platform notification: {e}")
        return False
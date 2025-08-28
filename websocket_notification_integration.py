# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
WebSocket Notification Integration

This module integrates the notification system with the existing WebSocket
infrastructure, providing seamless real-time notifications across user
and admin interfaces with standardized messaging and delivery confirmation.
"""

import logging
from typing import Dict, Any, Optional, List, Set, Union
from datetime import datetime, timezone, timedelta
from flask_socketio import SocketIO
from flask import current_app

from websocket_notification_system import (
    WebSocketNotificationSystem, StandardizedNotification, NotificationTarget,
    NotificationFilter, NotificationPriority, NotificationType
)
from websocket_notification_delivery import WebSocketNotificationDeliverySystem
from models import UserRole

logger = logging.getLogger(__name__)


class NotificationIntegrationManager:
    """
    Manages integration between notification system and existing WebSocket infrastructure
    """
    
    def __init__(self, socketio: SocketIO, db_manager=None):
        self.socketio = socketio
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)
        
        # Core notification systems
        self.notification_system = WebSocketNotificationSystem(socketio, db_manager)
        self.delivery_system = WebSocketNotificationDeliverySystem(socketio, db_manager)
        
        # Integration with existing systems
        self._namespace_manager = None
        self._progress_handler = None
        self._admin_dashboard = None
        
        # Notification routing mappings
        self._event_mappings = {
            # Progress notifications
            'progress_update': {
                'type': NotificationType.PROGRESS_UPDATE,
                'priority': NotificationPriority.NORMAL,
                'requires_acknowledgment': False
            },
            'task_completed': {
                'type': NotificationType.SUCCESS,
                'priority': NotificationPriority.HIGH,
                'requires_acknowledgment': True
            },
            'task_error': {
                'type': NotificationType.ERROR,
                'priority': NotificationPriority.HIGH,
                'requires_acknowledgment': True
            },
            
            # System notifications
            'system_status': {
                'type': NotificationType.SYSTEM,
                'priority': NotificationPriority.NORMAL,
                'requires_acknowledgment': False
            },
            'maintenance_alert': {
                'type': NotificationType.ALERT,
                'priority': NotificationPriority.URGENT,
                'requires_acknowledgment': True
            },
            'security_alert': {
                'type': NotificationType.SECURITY,
                'priority': NotificationPriority.CRITICAL,
                'requires_acknowledgment': True
            },
            
            # User notifications
            'user_notification': {
                'type': NotificationType.INFO,
                'priority': NotificationPriority.NORMAL,
                'requires_acknowledgment': False
            },
            'user_warning': {
                'type': NotificationType.WARNING,
                'priority': NotificationPriority.HIGH,
                'requires_acknowledgment': True
            },
            
            # Admin notifications
            'admin_alert': {
                'type': NotificationType.ADMIN,
                'priority': NotificationPriority.HIGH,
                'requires_acknowledgment': True
            },
            'system_metrics_update': {
                'type': NotificationType.SYSTEM,
                'priority': NotificationPriority.LOW,
                'requires_acknowledgment': False
            }
        }
        
        self.logger.info("Notification Integration Manager initialized")
    
    def set_namespace_manager(self, namespace_manager):
        """Set the namespace manager for integration"""
        self._namespace_manager = namespace_manager
        
        # Set connection tracker for notification routing
        self.notification_system.set_connection_tracker(namespace_manager)
        self.delivery_system.delivery_tracker.set_connection_tracker = namespace_manager
        
        self.logger.info("Integrated with WebSocket namespace manager")
    
    def set_progress_handler(self, progress_handler):
        """Set the progress handler for integration"""
        self._progress_handler = progress_handler
        
        # Replace progress handler's broadcast methods with notification system
        self._integrate_progress_handler()
        
        self.logger.info("Integrated with WebSocket progress handler")
    
    def set_admin_dashboard(self, admin_dashboard):
        """Set the admin dashboard for integration"""
        self._admin_dashboard = admin_dashboard
        
        # Replace admin dashboard's broadcast methods with notification system
        self._integrate_admin_dashboard()
        
        self.logger.info("Integrated with admin dashboard WebSocket handler")
    
    def send_progress_notification(self, task_id: str, user_id: int, progress_data: Dict[str, Any]) -> bool:
        """
        Send progress update notification
        
        Args:
            task_id: Task ID for progress update
            user_id: User ID to send notification to
            progress_data: Progress data to include
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            notification = self.notification_system.create_notification(
                event_name='progress_update',
                title='Task Progress Update',
                message=f'Progress update for task {task_id}',
                notification_type=NotificationType.PROGRESS_UPDATE,
                priority=NotificationPriority.NORMAL,
                data=progress_data,
                source='task_system',
                tags={'task_id', 'progress'},
                namespace='/',
                room=f'task_{task_id}'
            )
            
            # Target specific user
            notification.target.user_ids = {user_id}
            
            return self.notification_system.send_notification(notification)
            
        except Exception as e:
            self.logger.error(f"Error sending progress notification: {e}")
            return False
    
    def send_task_completion_notification(self, task_id: str, user_id: int, results: Dict[str, Any]) -> bool:
        """
        Send task completion notification
        
        Args:
            task_id: Completed task ID
            user_id: User ID to notify
            results: Task completion results
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            notification = self.notification_system.create_notification(
                event_name='task_completed',
                title='Task Completed',
                message=f'Task {task_id} has been completed successfully',
                notification_type=NotificationType.SUCCESS,
                priority=NotificationPriority.HIGH,
                data={'task_id': task_id, 'results': results},
                source='task_system',
                tags={'task_id', 'completion'},
                requires_acknowledgment=True,
                namespace='/',
                room=f'task_{task_id}'
            )
            
            # Target specific user
            notification.target.user_ids = {user_id}
            
            return self.notification_system.send_notification(notification)
            
        except Exception as e:
            self.logger.error(f"Error sending task completion notification: {e}")
            return False
    
    def send_system_alert(self, title: str, message: str, priority: NotificationPriority = NotificationPriority.HIGH,
                         target_roles: Optional[Set[UserRole]] = None, data: Optional[Dict[str, Any]] = None) -> bool:
        """
        Send system alert notification
        
        Args:
            title: Alert title
            message: Alert message
            priority: Alert priority level
            target_roles: Optional set of roles to target (defaults to all)
            data: Optional additional data
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            notification = self.notification_system.create_notification(
                event_name='system_alert',
                title=title,
                message=message,
                notification_type=NotificationType.ALERT,
                priority=priority,
                data=data or {},
                source='system',
                tags={'system', 'alert'},
                requires_acknowledgment=priority in [NotificationPriority.URGENT, NotificationPriority.CRITICAL],
                persist_offline=True,
                persist_duration_hours=48 if priority == NotificationPriority.CRITICAL else 24
            )
            
            # Target specific roles or all users
            if target_roles:
                notification.target.roles = target_roles
                # Send to both user and admin namespaces for admin roles
                if UserRole.ADMIN in target_roles:
                    notification.target.namespaces = {'/', '/admin'}
                else:
                    notification.target.namespaces = {'/'}
            else:
                notification.target.namespaces = {'/', '/admin'}
            
            return self.notification_system.send_notification(notification)
            
        except Exception as e:
            self.logger.error(f"Error sending system alert: {e}")
            return False
    
    def send_admin_notification(self, title: str, message: str, 
                              notification_type: NotificationType = NotificationType.ADMIN,
                              priority: NotificationPriority = NotificationPriority.HIGH,
                              data: Optional[Dict[str, Any]] = None) -> bool:
        """
        Send notification to admin users
        
        Args:
            title: Notification title
            message: Notification message
            notification_type: Type of notification
            priority: Priority level
            data: Optional additional data
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            notification = self.notification_system.create_notification(
                event_name='admin_notification',
                title=title,
                message=message,
                notification_type=notification_type,
                priority=priority,
                data=data or {},
                source='admin_system',
                tags={'admin'},
                requires_acknowledgment=True,
                namespace='/admin',
                persist_offline=True
            )
            
            # Target admin users only
            notification.target.roles = {UserRole.ADMIN}
            notification.target.namespaces = {'/admin'}
            
            return self.notification_system.send_notification(notification)
            
        except Exception as e:
            self.logger.error(f"Error sending admin notification: {e}")
            return False
    
    def send_security_alert(self, title: str, message: str, 
                          severity: str = 'high', data: Optional[Dict[str, Any]] = None) -> bool:
        """
        Send security alert notification
        
        Args:
            title: Alert title
            message: Alert message
            severity: Security severity level
            data: Optional additional data
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Map severity to priority
            priority_mapping = {
                'low': NotificationPriority.NORMAL,
                'medium': NotificationPriority.HIGH,
                'high': NotificationPriority.URGENT,
                'critical': NotificationPriority.CRITICAL
            }
            priority = priority_mapping.get(severity.lower(), NotificationPriority.HIGH)
            
            notification = self.notification_system.create_notification(
                event_name='security_alert',
                title=f'Security Alert: {title}',
                message=message,
                notification_type=NotificationType.SECURITY,
                priority=priority,
                data={**(data or {}), 'severity': severity},
                source='security_system',
                tags={'security', 'alert', severity},
                requires_acknowledgment=True,
                namespace='/admin',
                persist_offline=True,
                persist_duration_hours=72  # Keep security alerts longer
            )
            
            # Target admin users for security alerts
            notification.target.roles = {UserRole.ADMIN}
            notification.target.namespaces = {'/admin'}
            
            return self.notification_system.send_notification(notification)
            
        except Exception as e:
            self.logger.error(f"Error sending security alert: {e}")
            return False
    
    def send_user_notification(self, user_id: int, title: str, message: str,
                             notification_type: NotificationType = NotificationType.INFO,
                             priority: NotificationPriority = NotificationPriority.NORMAL,
                             data: Optional[Dict[str, Any]] = None) -> bool:
        """
        Send notification to specific user
        
        Args:
            user_id: Target user ID
            title: Notification title
            message: Notification message
            notification_type: Type of notification
            priority: Priority level
            data: Optional additional data
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            notification = self.notification_system.create_notification(
                event_name='user_notification',
                title=title,
                message=message,
                notification_type=notification_type,
                priority=priority,
                data=data or {},
                source='user_system',
                tags={'user'},
                requires_acknowledgment=priority in [NotificationPriority.HIGH, NotificationPriority.URGENT, NotificationPriority.CRITICAL],
                namespace='/',
                persist_offline=True
            )
            
            # Target specific user
            notification.target.user_ids = {user_id}
            
            return self.notification_system.send_notification(notification)
            
        except Exception as e:
            self.logger.error(f"Error sending user notification: {e}")
            return False
    
    def broadcast_maintenance_notification(self, title: str, message: str, 
                                         maintenance_start: Optional[datetime] = None,
                                         estimated_duration: Optional[str] = None) -> bool:
        """
        Broadcast maintenance notification to all users
        
        Args:
            title: Maintenance notification title
            message: Maintenance message
            maintenance_start: Optional maintenance start time
            estimated_duration: Optional estimated duration
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            data = {}
            if maintenance_start:
                data['maintenance_start'] = maintenance_start.isoformat()
            if estimated_duration:
                data['estimated_duration'] = estimated_duration
            
            notification = self.notification_system.create_notification(
                event_name='maintenance_notification',
                title=title,
                message=message,
                notification_type=NotificationType.SYSTEM,
                priority=NotificationPriority.URGENT,
                data=data,
                source='maintenance_system',
                tags={'maintenance', 'system'},
                requires_acknowledgment=True,
                persist_offline=True,
                persist_duration_hours=48
            )
            
            # Broadcast to all users
            notification.target.namespaces = {'/', '/admin'}
            
            return self.notification_system.send_notification(notification)
            
        except Exception as e:
            self.logger.error(f"Error sending maintenance notification: {e}")
            return False
    
    def get_user_notification_preferences(self, user_id: int) -> Dict[str, Any]:
        """Get notification preferences for a user"""
        user_filter = self.notification_system.get_user_filter(user_id)
        user_prefs = self.notification_system._user_preferences.get(user_id, {})
        
        return {
            'filter': user_filter.to_dict() if user_filter else None,
            'preferences': user_prefs
        }
    
    def set_user_notification_preferences(self, user_id: int, preferences: Dict[str, Any]) -> bool:
        """Set notification preferences for a user"""
        try:
            # Extract filter criteria if provided
            if 'filter' in preferences:
                filter_data = preferences['filter']
                notification_filter = NotificationFilter(
                    types={NotificationType(t) for t in filter_data.get('types', [])},
                    priorities={NotificationPriority(p) for p in filter_data.get('priorities', [])},
                    sources=set(filter_data.get('sources', [])),
                    tags=set(filter_data.get('tags', [])),
                    min_priority=NotificationPriority(filter_data['min_priority']) if 'min_priority' in filter_data else None,
                    max_age_hours=filter_data.get('max_age_hours')
                )
                self.notification_system.set_user_filter(user_id, notification_filter)
            
            # Set general preferences
            if 'preferences' in preferences:
                self.notification_system.set_user_preferences(user_id, preferences['preferences'])
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error setting user notification preferences: {e}")
            return False
    
    def get_offline_notifications(self, user_id: int, 
                                filter_criteria: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Get offline notifications for a user"""
        try:
            # Convert filter criteria if provided
            notification_filter = None
            if filter_criteria:
                notification_filter = NotificationFilter(
                    types={NotificationType(t) for t in filter_criteria.get('types', [])},
                    priorities={NotificationPriority(p) for p in filter_criteria.get('priorities', [])},
                    sources=set(filter_criteria.get('sources', [])),
                    tags=set(filter_criteria.get('tags', [])),
                    min_priority=NotificationPriority(filter_criteria['min_priority']) if 'min_priority' in filter_criteria else None,
                    max_age_hours=filter_criteria.get('max_age_hours')
                )
            
            notifications = self.notification_system.get_offline_notifications(user_id, notification_filter)
            return [notification.to_dict() for notification in notifications]
            
        except Exception as e:
            self.logger.error(f"Error getting offline notifications: {e}")
            return []
    
    def mark_notifications_as_read(self, user_id: int, notification_ids: List[str]) -> bool:
        """Mark notifications as read for a user"""
        return self.notification_system.mark_notifications_delivered(user_id, notification_ids)
    
    def get_system_statistics(self) -> Dict[str, Any]:
        """Get comprehensive notification system statistics"""
        return {
            'notification_system': self.notification_system.get_statistics(),
            'delivery_system': self.delivery_system.get_system_statistics(),
            'integration_status': {
                'namespace_manager_connected': self._namespace_manager is not None,
                'progress_handler_connected': self._progress_handler is not None,
                'admin_dashboard_connected': self._admin_dashboard is not None
            }
        }
    
    def cleanup_old_notifications(self, max_age_hours: int = 24) -> Dict[str, int]:
        """Clean up old notifications and tracking data"""
        notification_cleaned = self.notification_system.cleanup_expired_notifications()
        delivery_cleaned = self.delivery_system.cleanup_old_data(max_age_hours)
        
        return {
            'notifications_cleaned': notification_cleaned,
            **delivery_cleaned
        }
    
    def _integrate_progress_handler(self):
        """Integrate with existing progress handler"""
        if not self._progress_handler:
            return
        
        # Replace broadcast methods with notification system
        original_broadcast_progress = self._progress_handler.broadcast_progress_update
        original_broadcast_completion = self._progress_handler.broadcast_task_completion
        original_broadcast_error = self._progress_handler.broadcast_task_error
        
        def enhanced_broadcast_progress(task_id: str, progress_data: dict):
            # Extract user ID from progress data or context
            user_id = progress_data.get('user_id')
            if user_id:
                self.send_progress_notification(task_id, user_id, progress_data)
            else:
                # Fallback to original method
                original_broadcast_progress(task_id, progress_data)
        
        def enhanced_broadcast_completion(task_id: str, results: dict):
            # Extract user ID from results or context
            user_id = results.get('user_id')
            if user_id:
                self.send_task_completion_notification(task_id, user_id, results)
            else:
                # Fallback to original method
                original_broadcast_completion(task_id, results)
        
        def enhanced_broadcast_error(task_id: str, error_message: str):
            # Send as system alert
            self.send_system_alert(
                title='Task Error',
                message=f'Task {task_id} encountered an error: {error_message}',
                priority=NotificationPriority.HIGH,
                data={'task_id': task_id, 'error': error_message}
            )
            # Also call original method
            original_broadcast_error(task_id, error_message)
        
        # Replace methods
        self._progress_handler.broadcast_progress_update = enhanced_broadcast_progress
        self._progress_handler.broadcast_task_completion = enhanced_broadcast_completion
        self._progress_handler.broadcast_task_error = enhanced_broadcast_error
    
    def _integrate_admin_dashboard(self):
        """Integrate with existing admin dashboard"""
        if not self._admin_dashboard:
            return
        
        # Replace broadcast methods with notification system
        original_broadcast_metrics = self._admin_dashboard.broadcast_system_metrics
        original_broadcast_job = self._admin_dashboard.broadcast_job_update
        original_broadcast_alert = self._admin_dashboard.broadcast_alert
        
        def enhanced_broadcast_metrics(metrics: dict):
            # Send as low-priority system notification
            self.send_admin_notification(
                title='System Metrics Update',
                message='System metrics have been updated',
                notification_type=NotificationType.SYSTEM,
                priority=NotificationPriority.LOW,
                data=metrics
            )
            # Also call original method for backward compatibility
            original_broadcast_metrics(metrics)
        
        def enhanced_broadcast_job(job_data: dict):
            # Send as admin notification
            self.send_admin_notification(
                title='Job Update',
                message=f'Job {job_data.get("id", "unknown")} status updated',
                notification_type=NotificationType.ADMIN,
                priority=NotificationPriority.NORMAL,
                data=job_data
            )
            # Also call original method
            original_broadcast_job(job_data)
        
        def enhanced_broadcast_alert(alert_data: dict):
            # Send as admin alert
            self.send_admin_notification(
                title=alert_data.get('title', 'Admin Alert'),
                message=alert_data.get('message', 'Admin alert triggered'),
                notification_type=NotificationType.ALERT,
                priority=NotificationPriority.HIGH,
                data=alert_data
            )
            # Also call original method
            original_broadcast_alert(alert_data)
        
        # Replace methods
        self._admin_dashboard.broadcast_system_metrics = enhanced_broadcast_metrics
        self._admin_dashboard.broadcast_job_update = enhanced_broadcast_job
        self._admin_dashboard.broadcast_alert = enhanced_broadcast_alert
    
    def shutdown(self):
        """Shutdown the integration manager"""
        self.delivery_system.shutdown()
        self.logger.info("Notification Integration Manager shutdown")


# Global integration manager instance
_integration_manager = None


def get_notification_integration_manager() -> Optional[NotificationIntegrationManager]:
    """Get the global notification integration manager instance"""
    return _integration_manager


def initialize_notification_integration(socketio: SocketIO, db_manager=None) -> NotificationIntegrationManager:
    """Initialize the global notification integration manager"""
    global _integration_manager
    
    if _integration_manager is None:
        _integration_manager = NotificationIntegrationManager(socketio, db_manager)
        logger.info("Global notification integration manager initialized")
    
    return _integration_manager


def shutdown_notification_integration():
    """Shutdown the global notification integration manager"""
    global _integration_manager
    
    if _integration_manager:
        _integration_manager.shutdown()
        _integration_manager = None
        logger.info("Global notification integration manager shutdown")


# Convenience functions for common notification operations
def send_progress_update(task_id: str, user_id: int, progress_data: Dict[str, Any]) -> bool:
    """Send progress update notification"""
    manager = get_notification_integration_manager()
    if manager:
        return manager.send_progress_notification(task_id, user_id, progress_data)
    return False


def send_task_completed(task_id: str, user_id: int, results: Dict[str, Any]) -> bool:
    """Send task completion notification"""
    manager = get_notification_integration_manager()
    if manager:
        return manager.send_task_completion_notification(task_id, user_id, results)
    return False


def send_system_alert(title: str, message: str, priority: NotificationPriority = NotificationPriority.HIGH,
                     target_roles: Optional[Set[UserRole]] = None, data: Optional[Dict[str, Any]] = None) -> bool:
    """Send system alert notification"""
    manager = get_notification_integration_manager()
    if manager:
        return manager.send_system_alert(title, message, priority, target_roles, data)
    return False


def send_admin_alert(title: str, message: str, data: Optional[Dict[str, Any]] = None) -> bool:
    """Send admin alert notification"""
    manager = get_notification_integration_manager()
    if manager:
        return manager.send_admin_notification(title, message, NotificationType.ALERT, NotificationPriority.HIGH, data)
    return False


def send_security_alert(title: str, message: str, severity: str = 'high', data: Optional[Dict[str, Any]] = None) -> bool:
    """Send security alert notification"""
    manager = get_notification_integration_manager()
    if manager:
        return manager.send_security_alert(title, message, severity, data)
    return False


def send_user_message(user_id: int, title: str, message: str, 
                     notification_type: NotificationType = NotificationType.INFO,
                     priority: NotificationPriority = NotificationPriority.NORMAL,
                     data: Optional[Dict[str, Any]] = None) -> bool:
    """Send message to specific user"""
    manager = get_notification_integration_manager()
    if manager:
        return manager.send_user_notification(user_id, title, message, notification_type, priority, data)
    return False
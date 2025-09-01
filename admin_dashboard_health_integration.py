# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Admin Dashboard Health Integration

This module integrates the admin dashboard with the unified notification system
for real-time system health monitoring. It replaces legacy notification patterns
with WebSocket-based real-time notifications and provides admin-only access to
sensitive system health information.

Requirements: 4.1, 4.2, 4.4, 4.5, 8.1, 8.3
"""

import logging
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from flask import current_app

from unified_notification_manager import UnifiedNotificationManager
from admin_system_health_notification_handler import AdminSystemHealthNotificationHandler
from system_monitor import SystemMonitor
from page_notification_integrator import PageNotificationIntegrator
from models import UserRole
from database import DatabaseManager

logger = logging.getLogger(__name__)


class AdminDashboardHealthIntegration:
    """
    Integration service for admin dashboard health notifications
    
    Provides seamless integration between the admin dashboard and the unified
    notification system for real-time system health monitoring and alerts.
    """
    
    def __init__(self, notification_manager: UnifiedNotificationManager,
                 system_monitor: SystemMonitor, db_manager: DatabaseManager,
                 page_integrator: PageNotificationIntegrator):
        """
        Initialize admin dashboard health integration
        
        Args:
            notification_manager: Unified notification manager instance
            system_monitor: System monitor instance
            db_manager: Database manager instance
            page_integrator: Page notification integrator instance
        """
        self.notification_manager = notification_manager
        self.system_monitor = system_monitor
        self.db_manager = db_manager
        self.page_integrator = page_integrator
        
        # Initialize health notification handler
        self.health_handler = AdminSystemHealthNotificationHandler(
            notification_manager=notification_manager,
            system_monitor=system_monitor,
            db_manager=db_manager,
            monitoring_interval=60,  # Check every minute
            alert_cooldown=300  # 5 minute cooldown between similar alerts
        )
        
        # Integration status
        self._integration_active = False
        
        logger.info("Admin Dashboard Health Integration initialized")
    
    def initialize_dashboard_notifications(self, user_id: int) -> Dict[str, Any]:
        """
        Initialize real-time health notifications for admin dashboard
        
        Args:
            user_id: Admin user ID
            
        Returns:
            Dictionary containing initialization results
        """
        try:
            # Verify user has admin role
            if not self._verify_admin_access(user_id):
                logger.warning(f"Non-admin user {user_id} attempted to access health notifications")
                return {
                    'success': False,
                    'error': 'Access denied - admin role required',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            
            # Initialize page notifications for admin namespace
            page_config = {
                'page_type': 'admin_dashboard',
                'namespace': '/admin',
                'notification_types': ['admin', 'system', 'security'],
                'real_time_updates': True,
                'health_monitoring': True
            }
            
            # Set up WebSocket connection for admin notifications
            connection_result = self.page_integrator.initialize_page_notifications(
                user_id=user_id,
                page_type='admin_dashboard',
                config=page_config
            )
            
            if not connection_result.get('success', False):
                return {
                    'success': False,
                    'error': 'Failed to initialize WebSocket connection',
                    'details': connection_result,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            
            # Start health monitoring if not already active
            if not self.health_handler._monitoring_active:
                monitoring_started = self.health_handler.start_monitoring()
                if not monitoring_started:
                    logger.warning("Failed to start health monitoring")
            
            # Send initial health status
            initial_health = self._get_current_health_status()
            
            # Send welcome notification
            self._send_dashboard_welcome_notification(user_id, initial_health)
            
            self._integration_active = True
            
            return {
                'success': True,
                'websocket_connected': connection_result.get('websocket_connected', False),
                'health_monitoring_active': self.health_handler._monitoring_active,
                'initial_health_status': initial_health,
                'page_config': page_config,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to initialize dashboard notifications: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def send_health_update_notification(self, user_id: int, force_update: bool = False) -> Dict[str, Any]:
        """
        Send immediate health status update to admin dashboard
        
        Args:
            user_id: Admin user ID
            force_update: Whether to force a new health check
            
        Returns:
            Dictionary containing update results
        """
        try:
            # Verify admin access
            if not self._verify_admin_access(user_id):
                return {
                    'success': False,
                    'error': 'Access denied - admin role required'
                }
            
            # Get current health status
            if force_update:
                # Force new health check
                health = self.system_monitor.get_system_health()
                performance = self.system_monitor.get_performance_metrics()
                resources = self.system_monitor.check_resource_usage()
            else:
                # Use cached health status
                health = self._get_current_health_status()
                performance = None
                resources = None
            
            # Send health update notification
            from unified_notification_manager import AdminNotificationMessage, NotificationType, NotificationPriority, NotificationCategory
            
            notification = AdminNotificationMessage(
                id=f"health_update_{user_id}_{int(datetime.now(timezone.utc).timestamp())}",
                type=NotificationType.INFO,
                title="System Health Update",
                message=f"Current system status: {health.get('status', 'unknown').title()}",
                user_id=user_id,
                priority=NotificationPriority.NORMAL,
                category=NotificationCategory.ADMIN,
                admin_only=True,
                system_health_data={
                    'health_status': health,
                    'performance_metrics': performance.to_dict() if performance else None,
                    'resource_usage': resources.to_dict() if resources else None,
                    'update_type': 'forced' if force_update else 'cached',
                    'monitoring_active': self.health_handler._monitoring_active
                },
                data={
                    'component': 'admin_dashboard_health',
                    'update_requested_by': user_id,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            )
            
            # Send notification
            success = self.notification_manager.send_user_notification(user_id, notification)
            
            return {
                'success': success,
                'health_status': health,
                'notification_sent': success,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to send health update notification: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def configure_health_alerts(self, user_id: int, alert_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Configure health monitoring alerts for admin user
        
        Args:
            user_id: Admin user ID
            alert_config: Alert configuration settings
            
        Returns:
            Dictionary containing configuration results
        """
        try:
            # Verify admin access
            if not self._verify_admin_access(user_id):
                return {
                    'success': False,
                    'error': 'Access denied - admin role required'
                }
            
            # Validate alert configuration
            valid_config = self._validate_alert_config(alert_config)
            if not valid_config['valid']:
                return {
                    'success': False,
                    'error': f"Invalid alert configuration: {valid_config['errors']}",
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            
            # Update health monitoring thresholds
            thresholds_updated = False
            if 'thresholds' in alert_config:
                thresholds_updated = self.health_handler.update_thresholds(alert_config['thresholds'])
            
            # Update monitoring interval if specified
            interval_updated = False
            if 'monitoring_interval' in alert_config:
                new_interval = alert_config['monitoring_interval']
                if isinstance(new_interval, int) and 30 <= new_interval <= 3600:  # 30 seconds to 1 hour
                    self.health_handler.monitoring_interval = new_interval
                    interval_updated = True
            
            # Update alert cooldown if specified
            cooldown_updated = False
            if 'alert_cooldown' in alert_config:
                new_cooldown = alert_config['alert_cooldown']
                if isinstance(new_cooldown, int) and 60 <= new_cooldown <= 7200:  # 1 minute to 2 hours
                    self.health_handler.alert_cooldown = new_cooldown
                    cooldown_updated = True
            
            # Send configuration update notification
            self._send_config_update_notification(user_id, alert_config, {
                'thresholds_updated': thresholds_updated,
                'interval_updated': interval_updated,
                'cooldown_updated': cooldown_updated
            })
            
            return {
                'success': True,
                'thresholds_updated': thresholds_updated,
                'interval_updated': interval_updated,
                'cooldown_updated': cooldown_updated,
                'current_config': self.health_handler.get_monitoring_stats(),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to configure health alerts: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def get_health_monitoring_status(self, user_id: int) -> Dict[str, Any]:
        """
        Get current health monitoring status for admin dashboard
        
        Args:
            user_id: Admin user ID
            
        Returns:
            Dictionary containing monitoring status
        """
        try:
            # Verify admin access
            if not self._verify_admin_access(user_id):
                return {
                    'success': False,
                    'error': 'Access denied - admin role required'
                }
            
            # Get monitoring statistics
            monitoring_stats = self.health_handler.get_monitoring_stats()
            
            # Get current system health
            current_health = self._get_current_health_status()
            
            # Get integration status
            integration_status = {
                'integration_active': self._integration_active,
                'websocket_connected': self._check_websocket_connection(user_id),
                'page_integrator_active': self.page_integrator is not None
            }
            
            return {
                'success': True,
                'monitoring_stats': monitoring_stats,
                'current_health': current_health,
                'integration_status': integration_status,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get health monitoring status: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def stop_health_monitoring(self, user_id: int) -> Dict[str, Any]:
        """
        Stop health monitoring (admin only)
        
        Args:
            user_id: Admin user ID
            
        Returns:
            Dictionary containing stop results
        """
        try:
            # Verify admin access
            if not self._verify_admin_access(user_id):
                return {
                    'success': False,
                    'error': 'Access denied - admin role required'
                }
            
            # Stop health monitoring
            monitoring_stopped = self.health_handler.stop_monitoring()
            
            if monitoring_stopped:
                self._integration_active = False
                
                # Send shutdown notification
                self._send_monitoring_shutdown_notification(user_id)
            
            return {
                'success': monitoring_stopped,
                'monitoring_active': self.health_handler._monitoring_active,
                'integration_active': self._integration_active,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to stop health monitoring: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def _verify_admin_access(self, user_id: int) -> bool:
        """
        Verify user has admin role for health notifications
        
        Args:
            user_id: User ID to verify
            
        Returns:
            True if user has admin access, False otherwise
        """
        try:
            with self.db_manager.get_session() as session:
                from models import User
                user = session.query(User).filter_by(id=user_id).first()
                return user and user.role == UserRole.ADMIN
                
        except Exception as e:
            logger.error(f"Failed to verify admin access for user {user_id}: {e}")
            return False
    
    def _get_current_health_status(self) -> Dict[str, Any]:
        """
        Get current system health status
        
        Returns:
            Dictionary containing current health status
        """
        try:
            health = self.system_monitor.get_system_health()
            return health.to_dict()
            
        except Exception as e:
            logger.error(f"Failed to get current health status: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def _check_websocket_connection(self, user_id: int) -> bool:
        """
        Check if user has active WebSocket connection
        
        Args:
            user_id: User ID to check
            
        Returns:
            True if WebSocket is connected, False otherwise
        """
        try:
            # Check if user has active connections in admin namespace
            if hasattr(self.page_integrator, 'namespace_manager'):
                user_connections = self.page_integrator.namespace_manager._user_connections.get(user_id, set())
                for session_id in user_connections:
                    connection = self.page_integrator.namespace_manager._connections.get(session_id)
                    if connection and connection.namespace == '/admin':
                        return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to check WebSocket connection for user {user_id}: {e}")
            return False
    
    def _validate_alert_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate alert configuration settings
        
        Args:
            config: Alert configuration to validate
            
        Returns:
            Dictionary containing validation results
        """
        errors = []
        
        try:
            # Validate thresholds
            if 'thresholds' in config:
                thresholds = config['thresholds']
                if not isinstance(thresholds, dict):
                    errors.append("Thresholds must be a dictionary")
                else:
                    for key, value in thresholds.items():
                        if not isinstance(value, (int, float)) or value < 0 or value > 100:
                            errors.append(f"Invalid threshold value for {key}: {value}")
            
            # Validate monitoring interval
            if 'monitoring_interval' in config:
                interval = config['monitoring_interval']
                if not isinstance(interval, int) or not (30 <= interval <= 3600):
                    errors.append("Monitoring interval must be between 30 and 3600 seconds")
            
            # Validate alert cooldown
            if 'alert_cooldown' in config:
                cooldown = config['alert_cooldown']
                if not isinstance(cooldown, int) or not (60 <= cooldown <= 7200):
                    errors.append("Alert cooldown must be between 60 and 7200 seconds")
            
            return {
                'valid': len(errors) == 0,
                'errors': errors
            }
            
        except Exception as e:
            logger.error(f"Error validating alert config: {e}")
            return {
                'valid': False,
                'errors': [f"Validation error: {str(e)}"]
            }
    
    def _send_dashboard_welcome_notification(self, user_id: int, health_status: Dict[str, Any]) -> None:
        """
        Send welcome notification to admin dashboard
        
        Args:
            user_id: Admin user ID
            health_status: Current health status
        """
        try:
            from unified_notification_manager import AdminNotificationMessage, NotificationType, NotificationPriority, NotificationCategory
            
            notification = AdminNotificationMessage(
                id=f"dashboard_welcome_{user_id}_{int(datetime.now(timezone.utc).timestamp())}",
                type=NotificationType.SUCCESS,
                title="Admin Dashboard Connected",
                message="Real-time system health monitoring is now active",
                user_id=user_id,
                priority=NotificationPriority.NORMAL,
                category=NotificationCategory.ADMIN,
                admin_only=True,
                system_health_data={
                    'current_health': health_status,
                    'monitoring_active': self.health_handler._monitoring_active,
                    'features_enabled': [
                        'real_time_health_monitoring',
                        'performance_metrics_alerts',
                        'resource_usage_alerts',
                        'critical_system_events'
                    ]
                },
                data={
                    'component': 'admin_dashboard_integration',
                    'event_type': 'dashboard_connected',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            )
            
            self.notification_manager.send_user_notification(user_id, notification)
            
        except Exception as e:
            logger.error(f"Failed to send dashboard welcome notification: {e}")
    
    def _send_config_update_notification(self, user_id: int, config: Dict[str, Any], 
                                       update_results: Dict[str, bool]) -> None:
        """
        Send configuration update notification
        
        Args:
            user_id: Admin user ID
            config: Configuration that was updated
            update_results: Results of the update operations
        """
        try:
            from unified_notification_manager import AdminNotificationMessage, NotificationType, NotificationPriority, NotificationCategory
            
            notification = AdminNotificationMessage(
                id=f"config_update_{user_id}_{int(datetime.now(timezone.utc).timestamp())}",
                type=NotificationType.INFO,
                title="Health Monitoring Configuration Updated",
                message="System health monitoring settings have been updated",
                user_id=user_id,
                priority=NotificationPriority.NORMAL,
                category=NotificationCategory.ADMIN,
                admin_only=True,
                system_health_data={
                    'updated_config': config,
                    'update_results': update_results,
                    'current_settings': self.health_handler.get_monitoring_stats()
                },
                data={
                    'component': 'admin_dashboard_integration',
                    'event_type': 'config_updated',
                    'updated_by': user_id,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            )
            
            self.notification_manager.send_user_notification(user_id, notification)
            
        except Exception as e:
            logger.error(f"Failed to send config update notification: {e}")
    
    def _send_monitoring_shutdown_notification(self, user_id: int) -> None:
        """
        Send monitoring shutdown notification
        
        Args:
            user_id: Admin user ID who stopped monitoring
        """
        try:
            from unified_notification_manager import AdminNotificationMessage, NotificationType, NotificationPriority, NotificationCategory
            
            notification = AdminNotificationMessage(
                id=f"monitoring_shutdown_{user_id}_{int(datetime.now(timezone.utc).timestamp())}",
                type=NotificationType.WARNING,
                title="Health Monitoring Stopped",
                message="Real-time system health monitoring has been deactivated",
                user_id=user_id,
                priority=NotificationPriority.HIGH,
                category=NotificationCategory.ADMIN,
                admin_only=True,
                system_health_data={
                    'shutdown_reason': 'admin_request',
                    'shutdown_by': user_id,
                    'final_stats': self.health_handler.get_monitoring_stats()
                },
                data={
                    'component': 'admin_dashboard_integration',
                    'event_type': 'monitoring_stopped',
                    'stopped_by': user_id,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            )
            
            self.notification_manager.send_user_notification(user_id, notification)
            
        except Exception as e:
            logger.error(f"Failed to send monitoring shutdown notification: {e}")


def create_admin_dashboard_health_integration(notification_manager: UnifiedNotificationManager,
                                            system_monitor: SystemMonitor,
                                            db_manager: DatabaseManager,
                                            page_integrator: PageNotificationIntegrator) -> AdminDashboardHealthIntegration:
    """
    Factory function to create admin dashboard health integration
    
    Args:
        notification_manager: Unified notification manager instance
        system_monitor: System monitor instance
        db_manager: Database manager instance
        page_integrator: Page notification integrator instance
        
    Returns:
        AdminDashboardHealthIntegration instance
    """
    return AdminDashboardHealthIntegration(
        notification_manager=notification_manager,
        system_monitor=system_monitor,
        db_manager=db_manager,
        page_integrator=page_integrator
    )
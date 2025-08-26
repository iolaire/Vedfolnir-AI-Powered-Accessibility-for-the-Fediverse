# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Storage Warning Dashboard Integration for Admin Interface.

This service integrates the storage warning monitor with the admin dashboard,
providing warning notifications, status displays, and management interfaces
for storage monitoring and threshold management.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from storage_warning_monitor import StorageWarningMonitor, WarningNotification, StorageEvent
from storage_configuration_service import StorageConfigurationService
from storage_monitor_service import StorageMonitorService
from storage_limit_enforcer import StorageLimitEnforcer
from admin_storage_dashboard import AdminStorageDashboard

logger = logging.getLogger(__name__)


@dataclass
class DashboardWarningData:
    """Warning data structure for admin dashboard display"""
    has_warnings: bool
    warning_count: int
    critical_count: int
    unacknowledged_count: int
    latest_warning: Optional[WarningNotification]
    storage_status: str  # 'normal', 'warning', 'critical'
    warning_message: Optional[str]
    action_required: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for template rendering"""
        return {
            'has_warnings': self.has_warnings,
            'warning_count': self.warning_count,
            'critical_count': self.critical_count,
            'unacknowledged_count': self.unacknowledged_count,
            'latest_warning': self.latest_warning.to_dict() if self.latest_warning else None,
            'storage_status': self.storage_status,
            'warning_message': self.warning_message,
            'action_required': self.action_required
        }


class StorageWarningDashboardIntegration:
    """
    Integration service for storage warning monitoring and admin dashboard.
    
    This service provides:
    - Admin dashboard warning notifications when approaching limits
    - Integration with existing admin storage dashboard
    - Warning acknowledgment and management interfaces
    - Real-time storage status updates for dashboard display
    """
    
    def __init__(self,
                 warning_monitor: Optional[StorageWarningMonitor] = None,
                 admin_dashboard: Optional[AdminStorageDashboard] = None,
                 config_service: Optional[StorageConfigurationService] = None,
                 monitor_service: Optional[StorageMonitorService] = None,
                 enforcer_service: Optional[StorageLimitEnforcer] = None):
        """
        Initialize the dashboard integration service.
        
        Args:
            warning_monitor: Storage warning monitor instance
            admin_dashboard: Admin storage dashboard instance
            config_service: Storage configuration service instance
            monitor_service: Storage monitor service instance
            enforcer_service: Storage limit enforcer service instance
        """
        self.config_service = config_service or StorageConfigurationService()
        self.monitor_service = monitor_service or StorageMonitorService(self.config_service)
        self.enforcer_service = enforcer_service
        
        # Initialize admin dashboard if not provided
        if admin_dashboard is None:
            self.admin_dashboard = AdminStorageDashboard(
                config_service=self.config_service,
                monitor_service=self.monitor_service,
                enforcer_service=self.enforcer_service
            )
        else:
            self.admin_dashboard = admin_dashboard
        
        # Initialize warning monitor if not provided
        if warning_monitor is None:
            self.warning_monitor = StorageWarningMonitor(
                config_service=self.config_service,
                monitor_service=self.monitor_service,
                enforcer_service=self.enforcer_service,
                notification_callback=self._handle_warning_notification
            )
        else:
            self.warning_monitor = warning_monitor
            # Set notification callback if not already set
            if not self.warning_monitor.notification_callback:
                self.warning_monitor.notification_callback = self._handle_warning_notification
        
        logger.info("Storage warning dashboard integration initialized")
    
    def _handle_warning_notification(self, notification: WarningNotification) -> None:
        """
        Handle warning notifications from the storage monitor.
        
        This method is called when new warning notifications are created
        and can be used to trigger additional dashboard updates or alerts.
        
        Args:
            notification: The warning notification that was created
        """
        try:
            logger.info(f"Received warning notification: {notification.severity} - {notification.message}")
            
            # Log notification for dashboard integration
            if notification.severity == 'critical':
                logger.error(f"CRITICAL storage alert: {notification.message}")
            else:
                logger.warning(f"Storage warning: {notification.message}")
            
            # Additional dashboard-specific handling could be added here
            # For example: real-time updates, email notifications, etc.
            
        except Exception as e:
            logger.error(f"Error handling warning notification: {e}")
    
    def get_dashboard_warning_data(self) -> DashboardWarningData:
        """
        Get warning data formatted for admin dashboard display.
        
        Returns:
            DashboardWarningData with current warning status and notifications
        """
        try:
            # Get active notifications
            notifications = self.warning_monitor.get_active_notifications()
            
            # Count notifications by severity
            warning_count = sum(1 for n in notifications if n.severity == 'warning')
            critical_count = sum(1 for n in notifications if n.severity == 'critical')
            unacknowledged_count = sum(1 for n in notifications if not n.acknowledged)
            
            # Get latest notification
            latest_warning = notifications[0] if notifications else None
            
            # Determine storage status
            storage_status = self._determine_storage_status(notifications)
            
            # Generate warning message
            warning_message = self._generate_warning_message(notifications, storage_status)
            
            # Determine if action is required
            action_required = critical_count > 0 or unacknowledged_count > 0
            
            return DashboardWarningData(
                has_warnings=len(notifications) > 0,
                warning_count=warning_count,
                critical_count=critical_count,
                unacknowledged_count=unacknowledged_count,
                latest_warning=latest_warning,
                storage_status=storage_status,
                warning_message=warning_message,
                action_required=action_required
            )
            
        except Exception as e:
            logger.error(f"Error getting dashboard warning data: {e}")
            return DashboardWarningData(
                has_warnings=False,
                warning_count=0,
                critical_count=0,
                unacknowledged_count=0,
                latest_warning=None,
                storage_status='error',
                warning_message=f"Error retrieving warning data: {str(e)}",
                action_required=True
            )
    
    def _determine_storage_status(self, notifications: List[WarningNotification]) -> str:
        """
        Determine overall storage status based on notifications.
        
        Args:
            notifications: List of active notifications
            
        Returns:
            Storage status string ('normal', 'warning', 'critical', 'error')
        """
        try:
            if not notifications:
                # Check current metrics to determine status
                metrics = self.monitor_service.get_storage_metrics()
                if metrics.is_limit_exceeded:
                    return 'critical'
                elif metrics.is_warning_exceeded:
                    return 'warning'
                else:
                    return 'normal'
            
            # Check for critical notifications
            if any(n.severity == 'critical' for n in notifications):
                return 'critical'
            
            # Check for warning notifications
            if any(n.severity == 'warning' for n in notifications):
                return 'warning'
            
            return 'normal'
            
        except Exception as e:
            logger.error(f"Error determining storage status: {e}")
            return 'error'
    
    def _generate_warning_message(self, notifications: List[WarningNotification], 
                                storage_status: str) -> Optional[str]:
        """
        Generate a warning message for dashboard display.
        
        Args:
            notifications: List of active notifications
            storage_status: Current storage status
            
        Returns:
            Warning message string or None if no warnings
        """
        try:
            if storage_status == 'error':
                return "Error monitoring storage status. Please check system health."
            
            if not notifications:
                if storage_status == 'normal':
                    return None
                else:
                    # Generate message based on current metrics
                    metrics = self.monitor_service.get_storage_metrics()
                    if metrics.is_limit_exceeded:
                        return f"Storage limit exceeded: {metrics.total_gb:.1f}GB of {metrics.limit_gb:.1f}GB used"
                    elif metrics.is_warning_exceeded:
                        return f"Storage approaching limit: {metrics.total_gb:.1f}GB of {metrics.limit_gb:.1f}GB used"
            
            # Get the most recent unacknowledged notification
            unacknowledged = [n for n in notifications if not n.acknowledged]
            if unacknowledged:
                latest = unacknowledged[0]
                return latest.message
            
            # Get the most recent notification
            if notifications:
                return notifications[0].message
            
            return None
            
        except Exception as e:
            logger.error(f"Error generating warning message: {e}")
            return f"Error generating warning message: {str(e)}"
    
    def get_enhanced_dashboard_data(self) -> Dict[str, Any]:
        """
        Get enhanced dashboard data that combines storage metrics with warning information.
        
        Returns:
            Dictionary containing comprehensive dashboard data
        """
        try:
            # Get base dashboard data from admin dashboard
            base_data = self.admin_dashboard.get_storage_dashboard_data()
            
            # Get warning data
            warning_data = self.get_dashboard_warning_data()
            
            # Get monitoring status
            monitoring_status = self.warning_monitor.get_monitoring_status()
            
            # Combine all data
            enhanced_data = {
                # Base storage data
                'storage_gb': base_data.storage_gb,
                'limit_gb': base_data.limit_gb,
                'usage_percentage': base_data.usage_percentage,
                'status_color': base_data.status_color,
                'is_blocked': base_data.is_blocked,
                'block_reason': base_data.block_reason,
                'warning_threshold_gb': base_data.warning_threshold_gb,
                'is_warning_exceeded': base_data.is_warning_exceeded,
                'is_limit_exceeded': base_data.is_limit_exceeded,
                
                # Warning notification data
                'warnings': warning_data.to_dict(),
                
                # Monitoring status
                'monitoring': {
                    'active': monitoring_status.get('monitoring_active', False),
                    'check_interval_seconds': monitoring_status.get('check_interval_seconds', 300),
                    'last_check_time': monitoring_status.get('last_check_time'),
                    'recent_warning_events_count': monitoring_status.get('recent_warning_events_count', 0)
                },
                
                # Enhanced status information
                'overall_status': warning_data.storage_status,
                'action_required': warning_data.action_required,
                'dashboard_message': warning_data.warning_message
            }
            
            return enhanced_data
            
        except Exception as e:
            logger.error(f"Error getting enhanced dashboard data: {e}")
            return {
                'error': str(e),
                'storage_gb': 0.0,
                'limit_gb': 10.0,
                'usage_percentage': 0.0,
                'status_color': 'red',
                'overall_status': 'error',
                'action_required': True,
                'dashboard_message': f"Dashboard error: {str(e)}"
            }
    
    def acknowledge_warning(self, notification_id: str, acknowledged_by: str) -> bool:
        """
        Acknowledge a warning notification.
        
        Args:
            notification_id: ID of the notification to acknowledge
            acknowledged_by: Username or ID of the person acknowledging
            
        Returns:
            bool: True if acknowledgment was successful
        """
        try:
            result = self.warning_monitor.acknowledge_notification(notification_id, acknowledged_by)
            
            if result:
                logger.info(f"Warning notification {notification_id} acknowledged by {acknowledged_by}")
            else:
                logger.warning(f"Failed to acknowledge notification {notification_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error acknowledging warning {notification_id}: {e}")
            return False
    
    def get_warning_notifications_for_display(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get warning notifications formatted for dashboard display.
        
        Args:
            limit: Maximum number of notifications to return
            
        Returns:
            List of notification dictionaries for template rendering
        """
        try:
            notifications = self.warning_monitor.get_active_notifications()
            
            # Limit results
            notifications = notifications[:limit]
            
            # Convert to display format
            display_notifications = []
            for notification in notifications:
                display_data = notification.to_dict()
                
                # Add display-specific formatting
                display_data['created_at_formatted'] = notification.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')
                display_data['acknowledged_at_formatted'] = (
                    notification.acknowledged_at.strftime('%Y-%m-%d %H:%M:%S UTC') 
                    if notification.acknowledged_at else None
                )
                display_data['severity_class'] = 'danger' if notification.severity == 'critical' else 'warning'
                display_data['severity_icon'] = 'exclamation-triangle' if notification.severity == 'critical' else 'exclamation-circle'
                
                display_notifications.append(display_data)
            
            return display_notifications
            
        except Exception as e:
            logger.error(f"Error getting notifications for display: {e}")
            return []
    
    def get_storage_events_for_display(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get storage events formatted for dashboard display.
        
        Args:
            limit: Maximum number of events to return
            
        Returns:
            List of event dictionaries for template rendering
        """
        try:
            events = self.warning_monitor.get_storage_events(limit=limit)
            
            # Convert to display format
            display_events = []
            for event in events:
                display_data = event.to_dict()
                
                # Add display-specific formatting
                display_data['timestamp_formatted'] = event.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')
                display_data['event_type_formatted'] = event.event_type.value.replace('_', ' ').title()
                
                # Add severity class for styling
                if event.event_type.value in ['warning_threshold_exceeded', 'limit_exceeded', 'monitoring_error']:
                    display_data['severity_class'] = 'warning'
                elif event.event_type.value in ['warning_threshold_cleared', 'limit_cleared']:
                    display_data['severity_class'] = 'success'
                else:
                    display_data['severity_class'] = 'info'
                
                display_events.append(display_data)
            
            return display_events
            
        except Exception as e:
            logger.error(f"Error getting events for display: {e}")
            return []
    
    def start_monitoring(self) -> bool:
        """
        Start background storage monitoring.
        
        Returns:
            bool: True if monitoring started successfully
        """
        try:
            result = self.warning_monitor.start_background_monitoring()
            
            if result:
                logger.info("Storage warning monitoring started from dashboard integration")
            else:
                logger.warning("Failed to start storage warning monitoring")
            
            return result
            
        except Exception as e:
            logger.error(f"Error starting monitoring: {e}")
            return False
    
    def stop_monitoring(self) -> bool:
        """
        Stop background storage monitoring.
        
        Returns:
            bool: True if monitoring stopped successfully
        """
        try:
            result = self.warning_monitor.stop_background_monitoring()
            
            if result:
                logger.info("Storage warning monitoring stopped from dashboard integration")
            else:
                logger.warning("Failed to stop storage warning monitoring")
            
            return result
            
        except Exception as e:
            logger.error(f"Error stopping monitoring: {e}")
            return False
    
    def update_monitoring_config(self, check_interval_seconds: Optional[int] = None,
                               event_retention_hours: Optional[int] = None,
                               notification_retention_hours: Optional[int] = None) -> bool:
        """
        Update monitoring configuration from dashboard.
        
        Args:
            check_interval_seconds: New check interval in seconds
            event_retention_hours: New event retention period in hours
            notification_retention_hours: New notification retention period in hours
            
        Returns:
            bool: True if configuration was updated successfully
        """
        try:
            result = self.warning_monitor.update_monitoring_config(
                check_interval_seconds=check_interval_seconds,
                event_retention_hours=event_retention_hours,
                notification_retention_hours=notification_retention_hours
            )
            
            if result:
                logger.info("Monitoring configuration updated from dashboard")
            else:
                logger.warning("Failed to update monitoring configuration")
            
            return result
            
        except Exception as e:
            logger.error(f"Error updating monitoring configuration: {e}")
            return False
    
    def get_dashboard_health_status(self) -> Dict[str, Any]:
        """
        Get health status for dashboard display.
        
        Returns:
            Dictionary containing health status information
        """
        try:
            # Get warning monitor health
            monitor_health = self.warning_monitor.health_check()
            
            # Get admin dashboard health (if available)
            dashboard_health = {}
            if hasattr(self.admin_dashboard, 'health_check'):
                dashboard_health = self.admin_dashboard.health_check()
            
            # Combine health information
            overall_health = {
                'warning_monitor': monitor_health,
                'admin_dashboard': dashboard_health,
                'integration_healthy': True,
                'overall_healthy': monitor_health.get('overall_healthy', False)
            }
            
            return overall_health
            
        except Exception as e:
            logger.error(f"Error getting dashboard health status: {e}")
            return {
                'integration_healthy': False,
                'overall_healthy': False,
                'error': str(e)
            }
    
    def force_warning_check(self) -> bool:
        """
        Force an immediate warning threshold check.
        
        This can be called from the dashboard to manually trigger a check
        without waiting for the next scheduled check.
        
        Returns:
            bool: True if check was performed successfully
        """
        try:
            result = self.warning_monitor.check_warning_threshold()
            logger.info(f"Manual warning check completed: warning_exceeded={result}")
            return True
            
        except Exception as e:
            logger.error(f"Error performing manual warning check: {e}")
            return False
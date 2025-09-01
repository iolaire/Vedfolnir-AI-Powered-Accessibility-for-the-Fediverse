# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Admin Maintenance Notification Handler

Handles real-time maintenance operation notifications for administrators using the unified
WebSocket notification system. Replaces legacy flash messages and provides detailed
progress reporting for maintenance operations.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class MaintenanceNotificationType(Enum):
    """Types of maintenance notifications"""
    MAINTENANCE_STARTED = "maintenance_started"
    MAINTENANCE_COMPLETED = "maintenance_completed"
    MAINTENANCE_PROGRESS = "maintenance_progress"
    MAINTENANCE_ERROR = "maintenance_error"
    MAINTENANCE_WARNING = "maintenance_warning"
    SYSTEM_PAUSE = "system_pause"
    SYSTEM_RESUME = "system_resume"
    CONFIG_CHANGE = "config_change"
    OPERATION_BLOCKED = "operation_blocked"
    OPERATION_RESUMED = "operation_resumed"


@dataclass
class MaintenanceNotificationData:
    """Data structure for maintenance notifications"""
    operation_type: str
    operation_id: str
    status: str
    progress_percentage: Optional[int] = None
    estimated_duration: Optional[int] = None
    estimated_completion: Optional[datetime] = None
    affected_operations: Optional[List[str]] = None
    affected_users_count: Optional[int] = None
    error_details: Optional[str] = None
    admin_action_required: bool = False
    rollback_available: bool = False


class AdminMaintenanceNotificationHandler:
    """
    Handles maintenance notifications for administrators using unified WebSocket system
    """
    
    def __init__(self, notification_manager, db_manager):
        """
        Initialize the maintenance notification handler
        
        Args:
            notification_manager: UnifiedNotificationManager instance
            db_manager: Database manager instance
        """
        self.notification_manager = notification_manager
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)
        
        # Track active maintenance operations for progress updates
        self._active_operations = {}
        
    def send_maintenance_started_notification(self, admin_user_id: int, 
                                            maintenance_data: MaintenanceNotificationData) -> bool:
        """
        Send notification when maintenance operation starts
        
        Args:
            admin_user_id: Administrator user ID
            maintenance_data: Maintenance operation data
            
        Returns:
            True if notification sent successfully, False otherwise
        """
        try:
            from unified_notification_manager import AdminNotificationMessage
            from models import NotificationType, NotificationPriority, NotificationCategory
            
            # Create maintenance started notification
            notification = AdminNotificationMessage(
                id=f"maintenance_started_{maintenance_data.operation_id}_{int(datetime.now(timezone.utc).timestamp())}",
                type=NotificationType.INFO,
                title="🔧 Maintenance Operation Started",
                message=f"Maintenance operation '{maintenance_data.operation_type}' has been initiated.",
                user_id=admin_user_id,
                priority=NotificationPriority.HIGH,
                category=NotificationCategory.MAINTENANCE,
                admin_only=True,
                data={
                    'operation_type': maintenance_data.operation_type,
                    'operation_id': maintenance_data.operation_id,
                    'status': maintenance_data.status,
                    'estimated_duration': maintenance_data.estimated_duration,
                    'estimated_completion': maintenance_data.estimated_completion.isoformat() if maintenance_data.estimated_completion else None,
                    'affected_operations': maintenance_data.affected_operations or [],
                    'affected_users_count': maintenance_data.affected_users_count or 0,
                    'admin_action_required': maintenance_data.admin_action_required,
                    'rollback_available': maintenance_data.rollback_available,
                    'notification_type': MaintenanceNotificationType.MAINTENANCE_STARTED.value
                },
                requires_action=maintenance_data.admin_action_required,
                action_url=f"/admin/maintenance-monitoring?operation_id={maintenance_data.operation_id}",
                action_text="Monitor Progress"
            )
            
            # Send notification to admin
            success = self.notification_manager.send_admin_notification(notification)
            
            if success:
                # Track active operation for progress updates
                self._active_operations[maintenance_data.operation_id] = {
                    'admin_user_id': admin_user_id,
                    'operation_type': maintenance_data.operation_type,
                    'started_at': datetime.now(timezone.utc),
                    'last_progress_update': datetime.now(timezone.utc)
                }
                
                self.logger.info(f"Sent maintenance started notification to admin {admin_user_id}: {maintenance_data.operation_type}")
                
            return success
            
        except Exception as e:
            self.logger.error(f"Error sending maintenance started notification: {e}")
            return False
    
    def send_maintenance_progress_notification(self, operation_id: str,
                                             progress_data: MaintenanceNotificationData) -> bool:
        """
        Send real-time progress update for maintenance operation
        
        Args:
            operation_id: Maintenance operation ID
            progress_data: Progress update data
            
        Returns:
            True if notification sent successfully, False otherwise
        """
        try:
            # Check if operation is being tracked
            if operation_id not in self._active_operations:
                self.logger.warning(f"Progress update for unknown operation: {operation_id}")
                return False
            
            operation_info = self._active_operations[operation_id]
            admin_user_id = operation_info['admin_user_id']
            
            from unified_notification_manager import AdminNotificationMessage
            from models import NotificationType, NotificationPriority, NotificationCategory
            
            # Determine notification type based on progress
            if progress_data.progress_percentage is not None:
                if progress_data.progress_percentage >= 100:
                    notification_type = NotificationType.SUCCESS
                    title = "✅ Maintenance Operation Completed"
                    message = f"Maintenance operation '{progress_data.operation_type}' completed successfully."
                elif progress_data.error_details:
                    notification_type = NotificationType.ERROR
                    title = "❌ Maintenance Operation Error"
                    message = f"Error in maintenance operation '{progress_data.operation_type}': {progress_data.error_details}"
                else:
                    notification_type = NotificationType.INFO
                    title = f"🔄 Maintenance Progress ({progress_data.progress_percentage}%)"
                    message = f"Maintenance operation '{progress_data.operation_type}' is {progress_data.progress_percentage}% complete."
            else:
                notification_type = NotificationType.INFO
                title = "🔄 Maintenance Update"
                message = f"Maintenance operation '{progress_data.operation_type}' status: {progress_data.status}"
            
            # Create progress notification
            notification = AdminNotificationMessage(
                id=f"maintenance_progress_{operation_id}_{int(datetime.now(timezone.utc).timestamp())}",
                type=notification_type,
                title=title,
                message=message,
                user_id=admin_user_id,
                priority=NotificationPriority.NORMAL if not progress_data.error_details else NotificationPriority.HIGH,
                category=NotificationCategory.MAINTENANCE,
                admin_only=True,
                data={
                    'operation_type': progress_data.operation_type,
                    'operation_id': operation_id,
                    'status': progress_data.status,
                    'progress_percentage': progress_data.progress_percentage,
                    'estimated_duration': progress_data.estimated_duration,
                    'estimated_completion': progress_data.estimated_completion.isoformat() if progress_data.estimated_completion else None,
                    'affected_operations': progress_data.affected_operations or [],
                    'affected_users_count': progress_data.affected_users_count or 0,
                    'error_details': progress_data.error_details,
                    'admin_action_required': progress_data.admin_action_required,
                    'rollback_available': progress_data.rollback_available,
                    'notification_type': MaintenanceNotificationType.MAINTENANCE_PROGRESS.value
                },
                requires_action=progress_data.admin_action_required,
                action_url=f"/admin/maintenance-monitoring?operation_id={operation_id}",
                action_text="View Details"
            )
            
            # Send notification to admin
            success = self.notification_manager.send_admin_notification(notification)
            
            if success:
                # Update operation tracking
                operation_info['last_progress_update'] = datetime.now(timezone.utc)
                
                # If operation completed, remove from tracking
                if progress_data.progress_percentage is not None and progress_data.progress_percentage >= 100:
                    del self._active_operations[operation_id]
                
                self.logger.info(f"Sent maintenance progress notification for operation {operation_id}: {progress_data.progress_percentage}%")
                
            return success
            
        except Exception as e:
            self.logger.error(f"Error sending maintenance progress notification: {e}")
            return False
    
    def send_system_pause_notification(self, admin_user_id: int, pause_data: Dict[str, Any]) -> bool:
        """
        Send notification when system is paused for maintenance
        
        Args:
            admin_user_id: Administrator user ID
            pause_data: System pause information
            
        Returns:
            True if notification sent successfully, False otherwise
        """
        try:
            from unified_notification_manager import AdminNotificationMessage
            from models import NotificationType, NotificationPriority, NotificationCategory
            
            # Create system pause notification
            notification = AdminNotificationMessage(
                id=f"system_pause_{int(datetime.now(timezone.utc).timestamp())}",
                type=NotificationType.WARNING,
                title="⏸️ System Paused for Maintenance",
                message=f"System has been paused for maintenance. Reason: {pause_data.get('reason', 'Scheduled maintenance')}",
                user_id=admin_user_id,
                priority=NotificationPriority.HIGH,
                category=NotificationCategory.MAINTENANCE,
                admin_only=True,
                data={
                    'operation_type': 'system_pause',
                    'reason': pause_data.get('reason'),
                    'duration': pause_data.get('duration'),
                    'estimated_completion': pause_data.get('estimated_completion'),
                    'affected_operations': pause_data.get('affected_operations', []),
                    'affected_users_count': pause_data.get('affected_users_count', 0),
                    'maintenance_mode': pause_data.get('mode', 'normal'),
                    'notification_type': MaintenanceNotificationType.SYSTEM_PAUSE.value
                },
                requires_action=False,
                action_url="/admin/maintenance-mode",
                action_text="Manage Maintenance"
            )
            
            # Send notification to admin
            success = self.notification_manager.send_admin_notification(notification)
            
            if success:
                self.logger.info(f"Sent system pause notification to admin {admin_user_id}")
                
            return success
            
        except Exception as e:
            self.logger.error(f"Error sending system pause notification: {e}")
            return False
    
    def send_system_resume_notification(self, admin_user_id: int, resume_data: Dict[str, Any]) -> bool:
        """
        Send notification when system is resumed after maintenance
        
        Args:
            admin_user_id: Administrator user ID
            resume_data: System resume information
            
        Returns:
            True if notification sent successfully, False otherwise
        """
        try:
            from unified_notification_manager import AdminNotificationMessage
            from models import NotificationType, NotificationPriority, NotificationCategory
            
            # Create system resume notification
            notification = AdminNotificationMessage(
                id=f"system_resume_{int(datetime.now(timezone.utc).timestamp())}",
                type=NotificationType.SUCCESS,
                title="▶️ System Resumed After Maintenance",
                message="System maintenance has been completed and normal operations have resumed.",
                user_id=admin_user_id,
                priority=NotificationPriority.NORMAL,
                category=NotificationCategory.MAINTENANCE,
                admin_only=True,
                data={
                    'operation_type': 'system_resume',
                    'maintenance_duration': resume_data.get('maintenance_duration'),
                    'completed_operations': resume_data.get('completed_operations', []),
                    'restored_functionality': resume_data.get('restored_functionality', []),
                    'notification_type': MaintenanceNotificationType.SYSTEM_RESUME.value
                },
                requires_action=False,
                action_url="/admin/maintenance-monitoring",
                action_text="View Report"
            )
            
            # Send notification to admin
            success = self.notification_manager.send_admin_notification(notification)
            
            if success:
                self.logger.info(f"Sent system resume notification to admin {admin_user_id}")
                
            return success
            
        except Exception as e:
            self.logger.error(f"Error sending system resume notification: {e}")
            return False
    
    def send_configuration_change_notification(self, admin_user_id: int, 
                                             config_data: Dict[str, Any]) -> bool:
        """
        Send notification for maintenance-related configuration changes
        
        Args:
            admin_user_id: Administrator user ID
            config_data: Configuration change information
            
        Returns:
            True if notification sent successfully, False otherwise
        """
        try:
            from unified_notification_manager import AdminNotificationMessage
            from models import NotificationType, NotificationPriority, NotificationCategory
            
            # Create configuration change notification
            notification = AdminNotificationMessage(
                id=f"config_change_{int(datetime.now(timezone.utc).timestamp())}",
                type=NotificationType.INFO,
                title="⚙️ Maintenance Configuration Updated",
                message=f"Maintenance configuration has been updated: {config_data.get('change_description', 'Configuration modified')}",
                user_id=admin_user_id,
                priority=NotificationPriority.NORMAL,
                category=NotificationCategory.MAINTENANCE,
                admin_only=True,
                data={
                    'operation_type': 'config_change',
                    'change_type': config_data.get('change_type'),
                    'change_description': config_data.get('change_description'),
                    'changed_settings': config_data.get('changed_settings', []),
                    'requires_restart': config_data.get('requires_restart', False),
                    'notification_type': MaintenanceNotificationType.CONFIG_CHANGE.value
                },
                requires_action=config_data.get('requires_restart', False),
                action_url="/admin/maintenance-mode",
                action_text="Review Changes"
            )
            
            # Send notification to admin
            success = self.notification_manager.send_admin_notification(notification)
            
            if success:
                self.logger.info(f"Sent configuration change notification to admin {admin_user_id}")
                
            return success
            
        except Exception as e:
            self.logger.error(f"Error sending configuration change notification: {e}")
            return False
    
    def send_maintenance_error_notification(self, admin_user_id: int, 
                                          error_data: Dict[str, Any]) -> bool:
        """
        Send notification for maintenance operation errors
        
        Args:
            admin_user_id: Administrator user ID
            error_data: Error information
            
        Returns:
            True if notification sent successfully, False otherwise
        """
        try:
            from unified_notification_manager import AdminNotificationMessage
            from models import NotificationType, NotificationPriority, NotificationCategory
            
            # Create maintenance error notification
            notification = AdminNotificationMessage(
                id=f"maintenance_error_{int(datetime.now(timezone.utc).timestamp())}",
                type=NotificationType.ERROR,
                title="🚨 Maintenance Operation Error",
                message=f"Error in maintenance operation: {error_data.get('error_message', 'Unknown error occurred')}",
                user_id=admin_user_id,
                priority=NotificationPriority.CRITICAL,
                category=NotificationCategory.MAINTENANCE,
                admin_only=True,
                data={
                    'operation_type': 'maintenance_error',
                    'error_message': error_data.get('error_message'),
                    'error_code': error_data.get('error_code'),
                    'operation_id': error_data.get('operation_id'),
                    'failed_operation': error_data.get('failed_operation'),
                    'rollback_required': error_data.get('rollback_required', False),
                    'immediate_action_required': error_data.get('immediate_action_required', True),
                    'notification_type': MaintenanceNotificationType.MAINTENANCE_ERROR.value
                },
                requires_action=True,
                action_url=f"/admin/maintenance-monitoring?error=true&operation_id={error_data.get('operation_id', '')}",
                action_text="Resolve Error"
            )
            
            # Send notification to admin
            success = self.notification_manager.send_admin_notification(notification)
            
            if success:
                self.logger.error(f"Sent maintenance error notification to admin {admin_user_id}: {error_data.get('error_message')}")
                
            return success
            
        except Exception as e:
            self.logger.error(f"Error sending maintenance error notification: {e}")
            return False
    
    def send_maintenance_scheduling_notification(self, admin_user_id: int,
                                               schedule_data: Dict[str, Any]) -> bool:
        """
        Send notification for maintenance scheduling events
        
        Args:
            admin_user_id: Administrator user ID
            schedule_data: Maintenance schedule information
            
        Returns:
            True if notification sent successfully, False otherwise
        """
        try:
            from unified_notification_manager import AdminNotificationMessage
            from models import NotificationType, NotificationPriority, NotificationCategory
            
            # Create maintenance scheduling notification
            notification = AdminNotificationMessage(
                id=f"maintenance_schedule_{int(datetime.now(timezone.utc).timestamp())}",
                type=NotificationType.INFO,
                title="📅 Maintenance Scheduled",
                message=f"Maintenance operation scheduled: {schedule_data.get('operation_type', 'System maintenance')}",
                user_id=admin_user_id,
                priority=NotificationPriority.NORMAL,
                category=NotificationCategory.MAINTENANCE,
                admin_only=True,
                data={
                    'operation_type': 'maintenance_schedule',
                    'scheduled_operation': schedule_data.get('operation_type'),
                    'scheduled_time': schedule_data.get('scheduled_time'),
                    'estimated_duration': schedule_data.get('estimated_duration'),
                    'affected_operations': schedule_data.get('affected_operations', []),
                    'notification_users': schedule_data.get('notification_users', True),
                    'auto_start': schedule_data.get('auto_start', False),
                    'notification_type': 'maintenance_schedule'
                },
                requires_action=False,
                action_url="/admin/maintenance-mode",
                action_text="View Schedule"
            )
            
            # Send notification to admin
            success = self.notification_manager.send_admin_notification(notification)
            
            if success:
                self.logger.info(f"Sent maintenance scheduling notification to admin {admin_user_id}")
                
            return success
            
        except Exception as e:
            self.logger.error(f"Error sending maintenance scheduling notification: {e}")
            return False
    
    def get_active_operations(self) -> Dict[str, Dict[str, Any]]:
        """
        Get currently active maintenance operations
        
        Returns:
            Dictionary of active operations with their details
        """
        return self._active_operations.copy()
    
    def cleanup_stale_operations(self, max_age_hours: int = 24) -> int:
        """
        Clean up stale operation tracking entries
        
        Args:
            max_age_hours: Maximum age in hours for operation tracking
            
        Returns:
            Number of operations cleaned up
        """
        try:
            current_time = datetime.now(timezone.utc)
            stale_operations = []
            
            for operation_id, operation_info in self._active_operations.items():
                age = current_time - operation_info['started_at']
                if age.total_seconds() > (max_age_hours * 3600):
                    stale_operations.append(operation_id)
            
            for operation_id in stale_operations:
                del self._active_operations[operation_id]
            
            if stale_operations:
                self.logger.info(f"Cleaned up {len(stale_operations)} stale maintenance operations")
            
            return len(stale_operations)
            
        except Exception as e:
            self.logger.error(f"Error cleaning up stale operations: {e}")
            return 0
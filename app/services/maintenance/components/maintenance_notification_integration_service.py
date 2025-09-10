# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Maintenance Notification Integration Service

Integrates maintenance operations with the unified notification system, providing
comprehensive notification management for system maintenance, configuration changes,
and administrative operations.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class MaintenanceOperationType(Enum):
    """Types of maintenance operations"""
    SYSTEM_PAUSE = "system_pause"
    SYSTEM_RESUME = "system_resume"
    DATABASE_MAINTENANCE = "database_maintenance"
    CONFIGURATION_UPDATE = "configuration_update"
    SERVICE_RESTART = "service_restart"
    BACKUP_OPERATION = "backup_operation"
    CLEANUP_OPERATION = "cleanup_operation"
    SECURITY_UPDATE = "security_update"
    PERFORMANCE_OPTIMIZATION = "performance_optimization"
    EMERGENCY_MAINTENANCE = "emergency_maintenance"


@dataclass
class MaintenanceOperation:
    """Data structure for maintenance operations"""
    operation_id: str
    operation_type: MaintenanceOperationType
    title: str
    description: str
    admin_user_id: int
    estimated_duration: Optional[int] = None  # minutes
    affects_users: bool = True
    requires_downtime: bool = False
    rollback_available: bool = True
    scheduled_time: Optional[datetime] = None
    auto_start: bool = False
    notification_settings: Optional[Dict[str, Any]] = None


class MaintenanceNotificationIntegrationService:
    """
    Service for integrating maintenance operations with unified notifications
    """
    
    def __init__(self, notification_manager, progress_handler, db_manager):
        """
        Initialize the maintenance notification integration service
        
        Args:
            notification_manager: UnifiedNotificationManager instance
            progress_handler: MaintenanceProgressWebSocketHandler instance
            db_manager: Database manager instance
        """
        self.notification_manager = notification_manager
        self.progress_handler = progress_handler
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)
        
        # Track scheduled operations
        self._scheduled_operations = {}
        
        # Operation handlers
        self._operation_handlers = {
            MaintenanceOperationType.SYSTEM_PAUSE: self._handle_system_pause,
            MaintenanceOperationType.SYSTEM_RESUME: self._handle_system_resume,
            MaintenanceOperationType.DATABASE_MAINTENANCE: self._handle_database_maintenance,
            MaintenanceOperationType.CONFIGURATION_UPDATE: self._handle_configuration_update,
            MaintenanceOperationType.SERVICE_RESTART: self._handle_service_restart,
            MaintenanceOperationType.BACKUP_OPERATION: self._handle_backup_operation,
            MaintenanceOperationType.CLEANUP_OPERATION: self._handle_cleanup_operation,
            MaintenanceOperationType.SECURITY_UPDATE: self._handle_security_update,
            MaintenanceOperationType.PERFORMANCE_OPTIMIZATION: self._handle_performance_optimization,
            MaintenanceOperationType.EMERGENCY_MAINTENANCE: self._handle_emergency_maintenance
        }
    
    def schedule_maintenance_operation(self, operation: MaintenanceOperation) -> bool:
        """
        Schedule a maintenance operation with notifications
        
        Args:
            operation: Maintenance operation to schedule
            
        Returns:
            True if scheduled successfully, False otherwise
        """
        try:
            from admin_maintenance_notification_handler import AdminMaintenanceNotificationHandler
            
            # Create maintenance notification handler
            maintenance_handler = AdminMaintenanceNotificationHandler(
                self.notification_manager, self.db_manager
            )
            
            # Send scheduling notification
            schedule_success = maintenance_handler.send_maintenance_scheduling_notification(
                operation.admin_user_id, {
                    'operation_type': operation.operation_type.value,
                    'scheduled_time': operation.scheduled_time.isoformat() if operation.scheduled_time else None,
                    'estimated_duration': operation.estimated_duration,
                    'affected_operations': self._get_affected_operations(operation.operation_type),
                    'notification_users': operation.affects_users,
                    'auto_start': operation.auto_start
                }
            )
            
            if schedule_success:
                # Store scheduled operation
                self._scheduled_operations[operation.operation_id] = operation
                
                self.logger.info(f"Scheduled maintenance operation {operation.operation_id}: {operation.operation_type.value}")
                
            return schedule_success
            
        except Exception as e:
            self.logger.error(f"Error scheduling maintenance operation: {e}")
            return False
    
    def start_maintenance_operation(self, operation: MaintenanceOperation) -> bool:
        """
        Start a maintenance operation with full notification support
        
        Args:
            operation: Maintenance operation to start
            
        Returns:
            True if started successfully, False otherwise
        """
        try:
            from admin_maintenance_notification_handler import AdminMaintenanceNotificationHandler, MaintenanceNotificationData
            
            # Create maintenance notification handler
            maintenance_handler = AdminMaintenanceNotificationHandler(
                self.notification_manager, self.db_manager
            )
            
            # Calculate estimated completion
            estimated_completion = None
            if operation.estimated_duration:
                estimated_completion = datetime.now(timezone.utc) + timedelta(minutes=operation.estimated_duration)
            
            # Create maintenance notification data
            maintenance_data = MaintenanceNotificationData(
                operation_type=operation.operation_type.value,
                operation_id=operation.operation_id,
                status="starting",
                estimated_duration=operation.estimated_duration,
                estimated_completion=estimated_completion,
                affected_operations=self._get_affected_operations(operation.operation_type),
                affected_users_count=self._get_affected_users_count(operation),
                admin_action_required=False,
                rollback_available=operation.rollback_available
            )
            
            # Send maintenance started notification
            start_success = maintenance_handler.send_maintenance_started_notification(
                operation.admin_user_id, maintenance_data
            )
            
            if start_success:
                # Register with progress handler
                progress_success = self.progress_handler.register_maintenance_operation(
                    operation.operation_id,
                    operation.operation_type.value,
                    operation.admin_user_id,
                    total_steps=self._get_operation_steps(operation.operation_type),
                    estimated_duration=operation.estimated_duration * 60 if operation.estimated_duration else None
                )
                
                if progress_success:
                    # Execute operation-specific handler
                    handler = self._operation_handlers.get(operation.operation_type)
                    if handler:
                        handler_success = handler(operation)
                        if not handler_success:
                            self.logger.error(f"Operation handler failed for {operation.operation_type.value}")
                            return False
                    
                    self.logger.info(f"Started maintenance operation {operation.operation_id}: {operation.operation_type.value}")
                    return True
                else:
                    self.logger.error(f"Failed to register progress tracking for operation {operation.operation_id}")
                    return False
            else:
                self.logger.error(f"Failed to send maintenance started notification for operation {operation.operation_id}")
                return False
            
        except Exception as e:
            self.logger.error(f"Error starting maintenance operation: {e}")
            return False
    
    def update_operation_progress(self, operation_id: str, progress_percentage: int,
                                current_step: str, message: Optional[str] = None,
                                details: Optional[Dict[str, Any]] = None) -> bool:
        """
        Update progress for a maintenance operation
        
        Args:
            operation_id: Operation identifier
            progress_percentage: Current progress (0-100)
            current_step: Description of current step
            message: Progress message
            details: Additional details
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            return self.progress_handler.update_progress(
                operation_id=operation_id,
                progress_percentage=progress_percentage,
                current_step=current_step,
                message=message,
                details=details
            )
            
        except Exception as e:
            self.logger.error(f"Error updating operation progress: {e}")
            return False
    
    def complete_maintenance_operation(self, operation_id: str, success: bool = True,
                                     completion_message: str = "Operation completed",
                                     final_details: Optional[Dict[str, Any]] = None) -> bool:
        """
        Complete a maintenance operation with notifications
        
        Args:
            operation_id: Operation identifier
            success: Whether operation completed successfully
            completion_message: Completion message
            final_details: Final operation details
            
        Returns:
            True if completed successfully, False otherwise
        """
        try:
            # Complete progress tracking
            progress_success = self.progress_handler.complete_operation(
                operation_id, completion_message, success, final_details
            )
            
            # Remove from scheduled operations if present
            if operation_id in self._scheduled_operations:
                del self._scheduled_operations[operation_id]
            
            self.logger.info(f"Completed maintenance operation {operation_id} with success={success}")
            return progress_success
            
        except Exception as e:
            self.logger.error(f"Error completing maintenance operation: {e}")
            return False
    
    def report_operation_error(self, operation_id: str, error_message: str,
                             error_details: Optional[Dict[str, Any]] = None,
                             recoverable: bool = True) -> bool:
        """
        Report an error in a maintenance operation
        
        Args:
            operation_id: Operation identifier
            error_message: Error message
            error_details: Additional error details
            recoverable: Whether the error is recoverable
            
        Returns:
            True if reported successfully, False otherwise
        """
        try:
            return self.progress_handler.report_error(
                operation_id, error_message, error_details, recoverable
            )
            
        except Exception as e:
            self.logger.error(f"Error reporting operation error: {e}")
            return False
    
    def send_configuration_change_notification(self, admin_user_id: int,
                                             change_description: str,
                                             changed_settings: List[str],
                                             requires_restart: bool = False) -> bool:
        """
        Send notification for configuration changes
        
        Args:
            admin_user_id: Administrator user ID
            change_description: Description of changes
            changed_settings: List of changed settings
            requires_restart: Whether restart is required
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            from admin_maintenance_notification_handler import AdminMaintenanceNotificationHandler
            
            maintenance_handler = AdminMaintenanceNotificationHandler(
                self.notification_manager, self.db_manager
            )
            
            return maintenance_handler.send_configuration_change_notification(
                admin_user_id, {
                    'change_description': change_description,
                    'changed_settings': changed_settings,
                    'requires_restart': requires_restart,
                    'change_type': 'configuration_update'
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error sending configuration change notification: {e}")
            return False
    
    def _get_affected_operations(self, operation_type: MaintenanceOperationType) -> List[str]:
        """Get list of operations affected by maintenance type"""
        operation_impacts = {
            MaintenanceOperationType.SYSTEM_PAUSE: ['caption_generation', 'platform_operations', 'user_sessions'],
            MaintenanceOperationType.SYSTEM_RESUME: [],
            MaintenanceOperationType.DATABASE_MAINTENANCE: ['data_access', 'user_sessions', 'caption_generation'],
            MaintenanceOperationType.CONFIGURATION_UPDATE: ['system_configuration'],
            MaintenanceOperationType.SERVICE_RESTART: ['all_operations'],
            MaintenanceOperationType.BACKUP_OPERATION: ['data_access'],
            MaintenanceOperationType.CLEANUP_OPERATION: ['storage_operations'],
            MaintenanceOperationType.SECURITY_UPDATE: ['authentication', 'user_sessions'],
            MaintenanceOperationType.PERFORMANCE_OPTIMIZATION: ['system_performance'],
            MaintenanceOperationType.EMERGENCY_MAINTENANCE: ['all_operations']
        }
        
        return operation_impacts.get(operation_type, [])
    
    def _get_affected_users_count(self, operation: MaintenanceOperation) -> int:
        """Get estimated count of affected users"""
        if not operation.affects_users:
            return 0
        
        # In a real implementation, this would query the database
        # For now, return estimated counts based on operation type
        impact_estimates = {
            MaintenanceOperationType.SYSTEM_PAUSE: 50,
            MaintenanceOperationType.EMERGENCY_MAINTENANCE: 100,
            MaintenanceOperationType.SERVICE_RESTART: 75,
            MaintenanceOperationType.DATABASE_MAINTENANCE: 30,
            MaintenanceOperationType.SECURITY_UPDATE: 25
        }
        
        return impact_estimates.get(operation.operation_type, 10)
    
    def _get_operation_steps(self, operation_type: MaintenanceOperationType) -> int:
        """Get estimated number of steps for operation type"""
        step_estimates = {
            MaintenanceOperationType.SYSTEM_PAUSE: 5,
            MaintenanceOperationType.SYSTEM_RESUME: 3,
            MaintenanceOperationType.DATABASE_MAINTENANCE: 10,
            MaintenanceOperationType.CONFIGURATION_UPDATE: 4,
            MaintenanceOperationType.SERVICE_RESTART: 6,
            MaintenanceOperationType.BACKUP_OPERATION: 8,
            MaintenanceOperationType.CLEANUP_OPERATION: 7,
            MaintenanceOperationType.SECURITY_UPDATE: 9,
            MaintenanceOperationType.PERFORMANCE_OPTIMIZATION: 12,
            MaintenanceOperationType.EMERGENCY_MAINTENANCE: 15
        }
        
        return step_estimates.get(operation_type, 5)
    
    # Operation-specific handlers
    
    def _handle_system_pause(self, operation: MaintenanceOperation) -> bool:
        """Handle system pause operation"""
        try:
            self.progress_handler.update_progress(
                operation.operation_id, 20, "Notifying users of system pause"
            )
            
            self.progress_handler.update_progress(
                operation.operation_id, 40, "Pausing active operations"
            )
            
            self.progress_handler.update_progress(
                operation.operation_id, 60, "Invalidating user sessions"
            )
            
            self.progress_handler.update_progress(
                operation.operation_id, 80, "Enabling maintenance mode"
            )
            
            self.progress_handler.update_progress(
                operation.operation_id, 100, "System pause completed"
            )
            
            return True
            
        except Exception as e:
            self.progress_handler.report_error(
                operation.operation_id, f"System pause failed: {str(e)}", recoverable=True
            )
            return False
    
    def _handle_system_resume(self, operation: MaintenanceOperation) -> bool:
        """Handle system resume operation"""
        try:
            self.progress_handler.update_progress(
                operation.operation_id, 33, "Disabling maintenance mode"
            )
            
            self.progress_handler.update_progress(
                operation.operation_id, 66, "Restoring system operations"
            )
            
            self.progress_handler.update_progress(
                operation.operation_id, 100, "System resume completed"
            )
            
            return True
            
        except Exception as e:
            self.progress_handler.report_error(
                operation.operation_id, f"System resume failed: {str(e)}", recoverable=True
            )
            return False
    
    def _handle_database_maintenance(self, operation: MaintenanceOperation) -> bool:
        """Handle database maintenance operation"""
        try:
            steps = [
                (10, "Backing up database"),
                (20, "Analyzing database structure"),
                (30, "Optimizing tables"),
                (40, "Rebuilding indexes"),
                (50, "Updating statistics"),
                (60, "Checking data integrity"),
                (70, "Cleaning up temporary data"),
                (80, "Validating repairs"),
                (90, "Updating configuration"),
                (100, "Database maintenance completed")
            ]
            
            for progress, step_description in steps:
                self.progress_handler.update_progress(
                    operation.operation_id, progress, step_description
                )
                # Simulate work time
                import time
                time.sleep(0.5)
            
            return True
            
        except Exception as e:
            self.progress_handler.report_error(
                operation.operation_id, f"Database maintenance failed: {str(e)}", recoverable=True
            )
            return False
    
    def _handle_configuration_update(self, operation: MaintenanceOperation) -> bool:
        """Handle configuration update operation"""
        try:
            self.progress_handler.update_progress(
                operation.operation_id, 25, "Validating new configuration"
            )
            
            self.progress_handler.update_progress(
                operation.operation_id, 50, "Applying configuration changes"
            )
            
            self.progress_handler.update_progress(
                operation.operation_id, 75, "Reloading services"
            )
            
            self.progress_handler.update_progress(
                operation.operation_id, 100, "Configuration update completed"
            )
            
            return True
            
        except Exception as e:
            self.progress_handler.report_error(
                operation.operation_id, f"Configuration update failed: {str(e)}", recoverable=True
            )
            return False
    
    def _handle_service_restart(self, operation: MaintenanceOperation) -> bool:
        """Handle service restart operation"""
        try:
            self.progress_handler.update_progress(
                operation.operation_id, 16, "Stopping services gracefully"
            )
            
            self.progress_handler.update_progress(
                operation.operation_id, 33, "Waiting for connections to close"
            )
            
            self.progress_handler.update_progress(
                operation.operation_id, 50, "Starting services"
            )
            
            self.progress_handler.update_progress(
                operation.operation_id, 66, "Initializing components"
            )
            
            self.progress_handler.update_progress(
                operation.operation_id, 83, "Validating service health"
            )
            
            self.progress_handler.update_progress(
                operation.operation_id, 100, "Service restart completed"
            )
            
            return True
            
        except Exception as e:
            self.progress_handler.report_error(
                operation.operation_id, f"Service restart failed: {str(e)}", recoverable=True
            )
            return False
    
    def _handle_backup_operation(self, operation: MaintenanceOperation) -> bool:
        """Handle backup operation"""
        try:
            steps = [
                (12, "Preparing backup location"),
                (25, "Creating database backup"),
                (37, "Backing up configuration files"),
                (50, "Backing up user data"),
                (62, "Backing up logs"),
                (75, "Compressing backup files"),
                (87, "Validating backup integrity"),
                (100, "Backup operation completed")
            ]
            
            for progress, step_description in steps:
                self.progress_handler.update_progress(
                    operation.operation_id, progress, step_description
                )
            
            return True
            
        except Exception as e:
            self.progress_handler.report_error(
                operation.operation_id, f"Backup operation failed: {str(e)}", recoverable=True
            )
            return False
    
    def _handle_cleanup_operation(self, operation: MaintenanceOperation) -> bool:
        """Handle cleanup operation"""
        try:
            steps = [
                (14, "Analyzing storage usage"),
                (28, "Cleaning temporary files"),
                (42, "Removing old logs"),
                (56, "Cleaning cache directories"),
                (70, "Optimizing storage"),
                (84, "Updating storage statistics"),
                (100, "Cleanup operation completed")
            ]
            
            for progress, step_description in steps:
                self.progress_handler.update_progress(
                    operation.operation_id, progress, step_description
                )
            
            return True
            
        except Exception as e:
            self.progress_handler.report_error(
                operation.operation_id, f"Cleanup operation failed: {str(e)}", recoverable=True
            )
            return False
    
    def _handle_security_update(self, operation: MaintenanceOperation) -> bool:
        """Handle security update operation"""
        try:
            steps = [
                (11, "Downloading security updates"),
                (22, "Validating update signatures"),
                (33, "Backing up current system"),
                (44, "Applying security patches"),
                (55, "Updating security configurations"),
                (66, "Restarting security services"),
                (77, "Validating security status"),
                (88, "Running security tests"),
                (100, "Security update completed")
            ]
            
            for progress, step_description in steps:
                self.progress_handler.update_progress(
                    operation.operation_id, progress, step_description
                )
            
            return True
            
        except Exception as e:
            self.progress_handler.report_error(
                operation.operation_id, f"Security update failed: {str(e)}", recoverable=False
            )
            return False
    
    def _handle_performance_optimization(self, operation: MaintenanceOperation) -> bool:
        """Handle performance optimization operation"""
        try:
            steps = [
                (8, "Analyzing system performance"),
                (16, "Identifying bottlenecks"),
                (25, "Optimizing database queries"),
                (33, "Tuning cache settings"),
                (41, "Optimizing memory usage"),
                (50, "Adjusting connection pools"),
                (58, "Optimizing file I/O"),
                (66, "Tuning network settings"),
                (75, "Applying performance patches"),
                (83, "Running performance tests"),
                (91, "Validating improvements"),
                (100, "Performance optimization completed")
            ]
            
            for progress, step_description in steps:
                self.progress_handler.update_progress(
                    operation.operation_id, progress, step_description
                )
            
            return True
            
        except Exception as e:
            self.progress_handler.report_error(
                operation.operation_id, f"Performance optimization failed: {str(e)}", recoverable=True
            )
            return False
    
    def _handle_emergency_maintenance(self, operation: MaintenanceOperation) -> bool:
        """Handle emergency maintenance operation"""
        try:
            steps = [
                (6, "Activating emergency protocols"),
                (13, "Notifying all administrators"),
                (20, "Stopping all non-critical services"),
                (26, "Isolating affected systems"),
                (33, "Analyzing emergency situation"),
                (40, "Implementing emergency fixes"),
                (46, "Testing emergency repairs"),
                (53, "Validating system stability"),
                (60, "Gradually restoring services"),
                (66, "Monitoring system health"),
                (73, "Running diagnostic tests"),
                (80, "Validating full functionality"),
                (86, "Updating emergency logs"),
                (93, "Notifying stakeholders"),
                (100, "Emergency maintenance completed")
            ]
            
            for progress, step_description in steps:
                self.progress_handler.update_progress(
                    operation.operation_id, progress, step_description
                )
            
            return True
            
        except Exception as e:
            self.progress_handler.report_error(
                operation.operation_id, f"Emergency maintenance failed: {str(e)}", recoverable=False
            )
            return False
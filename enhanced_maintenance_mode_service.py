# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Enhanced Maintenance Mode Service

Provides comprehensive maintenance mode functionality with granular operation blocking,
session management, and admin user bypass logic.
"""

import logging
import threading
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import uuid

from configuration_service import ConfigurationService
from models import User, UserRole

logger = logging.getLogger(__name__)


class MaintenanceMode(Enum):
    """Maintenance mode types"""
    NORMAL = "normal"          # Block new operations, allow completion
    EMERGENCY = "emergency"    # Block all non-admin operations immediately
    TEST = "test"             # Simulate maintenance without actual blocking


@dataclass
class MaintenanceStatus:
    """Comprehensive maintenance status information"""
    is_active: bool
    mode: MaintenanceMode
    reason: Optional[str]
    estimated_duration: Optional[int]  # Duration in minutes
    started_at: Optional[datetime]
    estimated_completion: Optional[datetime]
    enabled_by: Optional[str]
    blocked_operations: List[str]
    active_jobs_count: int
    invalidated_sessions: int
    test_mode: bool


class MaintenanceModeError(Exception):
    """Base maintenance mode error"""
    pass


class MaintenanceActivationError(MaintenanceModeError):
    """Maintenance activation failed"""
    pass


class SessionInvalidationError(MaintenanceModeError):
    """Session invalidation failed"""
    pass


class EnhancedMaintenanceModeService:
    """
    Enhanced maintenance mode service with granular operation control
    
    Features:
    - Granular operation blocking based on operation type
    - Admin user bypass functionality
    - Session management integration
    - Emergency mode with immediate blocking
    - Test mode for validation without impact
    - Comprehensive status tracking and reporting
    - Test mode simulation and validation
    """
    
    # Configuration keys
    MAINTENANCE_MODE_KEY = "maintenance_mode"
    MAINTENANCE_REASON_KEY = "maintenance_reason"
    MAINTENANCE_DURATION_KEY = "maintenance_duration"
    MAINTENANCE_ENABLED_BY_KEY = "maintenance_enabled_by"
    
    def __init__(self, config_service: ConfigurationService, db_manager=None):
        """
        Initialize enhanced maintenance mode service
        
        Args:
            config_service: Configuration service instance
            db_manager: Database manager for operation completion tracking (optional)
        """
        self.config_service = config_service
        self.db_manager = db_manager
        
        # Status tracking
        self._current_status: Optional[MaintenanceStatus] = None
        self._status_lock = threading.RLock()
        
        # Change subscribers
        self._change_subscribers: Dict[str, Callable] = {}
        self._subscribers_lock = threading.RLock()
        
        # Operation completion tracker
        self._completion_tracker = None
        if db_manager:
            try:
                from maintenance_operation_completion_tracker import MaintenanceOperationCompletionTracker
                self._completion_tracker = MaintenanceOperationCompletionTracker(
                    db_manager=db_manager,
                    maintenance_service=self
                )
                logger.info("Operation completion tracker initialized")
            except ImportError as e:
                logger.warning(f"Could not initialize completion tracker: {e}")
        
        # Statistics
        self._stats = {
            'maintenance_activations': 0,
            'emergency_activations': 0,
            'test_mode_activations': 0,
            'blocked_operations': 0,
            'admin_bypasses': 0,
            'session_invalidations': 0,
            'test_mode_simulated_blocks': 0,
            'test_mode_operation_attempts': 0
        }
        self._stats_lock = threading.RLock()
        
        # Test mode tracking
        self._test_mode_data = {
            'simulated_blocks': [],
            'operation_attempts': [],
            'validation_results': {},
            'performance_metrics': {},
            'started_at': None,
            'completed_at': None,
            'test_session_id': None,
            'total_operations_tested': 0,
            'blocked_operations_count': 0,
            'allowed_operations_count': 0,
            'admin_bypasses_count': 0,
            'operation_types_tested': set(),
            'errors_encountered': []
        }
        self._test_mode_lock = threading.RLock()
        
        # Subscribe to configuration changes
        self._setup_configuration_subscriptions()
    
    def enable_maintenance(self, reason: str, duration: Optional[int] = None, 
                          mode: MaintenanceMode = MaintenanceMode.NORMAL,
                          enabled_by: Optional[str] = None) -> bool:
        """
        Enable maintenance mode with specified parameters
        
        Args:
            reason: Reason for enabling maintenance mode
            duration: Estimated duration in minutes (optional)
            mode: Maintenance mode type
            enabled_by: Identifier of who enabled maintenance
            
        Returns:
            True if maintenance mode was enabled successfully
            
        Raises:
            MaintenanceActivationError: If activation fails
        """
        try:
            logger.info(f"Enabling maintenance mode: {mode.value} - {reason}")
            
            # Update configuration through the configuration service
            # Note: In a real implementation, this would update the configuration
            # For now, we'll track the status internally and notify subscribers
            
            started_at = datetime.now(timezone.utc)
            estimated_completion = None
            if duration:
                from datetime import timedelta
                estimated_completion = started_at + timedelta(minutes=duration)
            
            # Create maintenance status
            maintenance_status = MaintenanceStatus(
                is_active=True,
                mode=mode,
                reason=reason,
                estimated_duration=duration,
                started_at=started_at,
                estimated_completion=estimated_completion,
                enabled_by=enabled_by,
                blocked_operations=[],  # Will be populated by operation classifier
                active_jobs_count=0,    # Will be updated by job monitoring
                invalidated_sessions=0, # Will be updated by session manager
                test_mode=(mode == MaintenanceMode.TEST)
            )
            
            # Update internal status
            with self._status_lock:
                self._current_status = maintenance_status
            
            # Update statistics
            with self._stats_lock:
                self._stats['maintenance_activations'] += 1
                if mode == MaintenanceMode.EMERGENCY:
                    self._stats['emergency_activations'] += 1
                elif mode == MaintenanceMode.TEST:
                    self._stats['test_mode_activations'] += 1
            
            # Start operation completion tracking if available
            if self._completion_tracker and mode != MaintenanceMode.TEST:
                try:
                    self._completion_tracker.start_monitoring()
                    # Force refresh to get current active jobs count
                    active_count = self._completion_tracker.force_refresh_active_jobs()
                    maintenance_status.active_jobs_count = active_count
                    logger.info(f"Started tracking {active_count} active jobs during maintenance")
                except Exception as e:
                    logger.error(f"Error starting completion tracking: {str(e)}")
            
            # Notify subscribers
            self._notify_change_subscribers('maintenance_enabled', maintenance_status)
            
            logger.info(f"Maintenance mode enabled successfully: {mode.value}")
            return True
            
        except Exception as e:
            logger.error(f"Error enabling maintenance mode: {str(e)}")
            raise MaintenanceActivationError(f"Failed to enable maintenance mode: {str(e)}")
    
    def disable_maintenance(self, disabled_by: Optional[str] = None) -> bool:
        """
        Disable maintenance mode
        
        Args:
            disabled_by: Identifier of who disabled maintenance
            
        Returns:
            True if maintenance mode was disabled successfully
        """
        try:
            logger.info(f"Disabling maintenance mode (by: {disabled_by})")
            
            # Get current status
            current_status = self.get_maintenance_status()
            
            # Create disabled status
            maintenance_status = MaintenanceStatus(
                is_active=False,
                mode=MaintenanceMode.NORMAL,
                reason=None,
                estimated_duration=None,
                started_at=None,
                estimated_completion=None,
                enabled_by=None,
                blocked_operations=[],
                active_jobs_count=0,
                invalidated_sessions=current_status.invalidated_sessions,
                test_mode=False
            )
            
            # Stop operation completion tracking if available
            if self._completion_tracker:
                try:
                    self._completion_tracker.stop_monitoring()
                    logger.info("Stopped operation completion tracking")
                except Exception as e:
                    logger.error(f"Error stopping completion tracking: {str(e)}")
            
            # Update internal status
            with self._status_lock:
                self._current_status = maintenance_status
            
            # Notify subscribers
            self._notify_change_subscribers('maintenance_disabled', maintenance_status)
            
            logger.info("Maintenance mode disabled successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error disabling maintenance mode: {str(e)}")
            return False
    
    def is_operation_blocked(self, operation: str, user: Optional[User] = None) -> bool:
        """
        Check if an operation is blocked by maintenance mode
        
        Args:
            operation: Operation identifier or endpoint
            user: User attempting the operation (optional)
            
        Returns:
            True if operation is blocked, False otherwise
        """
        try:
            # Get current maintenance status
            status = self.get_maintenance_status()
            
            # If maintenance is not active, allow all operations
            if not status.is_active:
                return False
            
            # If in test mode, simulate blocking without actually blocking
            if status.test_mode:
                # Record the simulated block for validation reporting
                self._record_test_mode_simulation(operation, user, True)
                logger.debug(f"Test mode: Would block operation {operation}")
                return False
            
            # Check for admin user bypass
            if user and self._is_admin_user(user):
                with self._stats_lock:
                    self._stats['admin_bypasses'] += 1
                logger.debug(f"Admin user bypass for operation {operation}")
                return False
            
            # Import operation classifier here to avoid circular imports
            from maintenance_operation_classifier import MaintenanceOperationClassifier
            
            # Use operation classifier to determine if operation should be blocked
            classifier = MaintenanceOperationClassifier()
            operation_type = classifier.classify_operation(operation, 'GET')  # Default to GET
            is_blocked = classifier.is_blocked_operation(operation_type, status.mode)
            
            if is_blocked:
                with self._stats_lock:
                    self._stats['blocked_operations'] += 1
                logger.debug(f"Blocking operation {operation} (type: {operation_type.value})")
            
            return is_blocked
            
        except Exception as e:
            logger.error(f"Error checking operation blocking for {operation}: {str(e)}")
            # Default to allowing operations on error to prevent system lockout
            return False
    
    def get_maintenance_status(self) -> MaintenanceStatus:
        """
        Get comprehensive maintenance mode status
        
        Returns:
            MaintenanceStatus object with current status
        """
        with self._status_lock:
            if self._current_status is not None:
                return self._current_status
        
        # If no internal status, check configuration service
        try:
            maintenance_enabled = self.config_service.get_config(self.MAINTENANCE_MODE_KEY, False)
            maintenance_reason = self.config_service.get_config(self.MAINTENANCE_REASON_KEY, None)
            
            # Create status from configuration
            status = MaintenanceStatus(
                is_active=bool(maintenance_enabled),
                mode=MaintenanceMode.NORMAL,
                reason=maintenance_reason,
                estimated_duration=None,
                started_at=datetime.now(timezone.utc) if maintenance_enabled else None,
                estimated_completion=None,
                enabled_by=None,
                blocked_operations=[],
                active_jobs_count=0,
                invalidated_sessions=0,
                test_mode=False
            )
            
            with self._status_lock:
                self._current_status = status
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting maintenance status: {str(e)}")
            # Return safe default status
            return MaintenanceStatus(
                is_active=False,
                mode=MaintenanceMode.NORMAL,
                reason=None,
                estimated_duration=None,
                started_at=None,
                estimated_completion=None,
                enabled_by=None,
                blocked_operations=[],
                active_jobs_count=0,
                invalidated_sessions=0,
                test_mode=False
            )
    
    def get_blocked_operations(self) -> List[str]:
        """
        Get list of currently blocked operation types
        
        Returns:
            List of blocked operation type names
        """
        try:
            status = self.get_maintenance_status()
            
            if not status.is_active:
                return []
            
            # Import operation classifier here to avoid circular imports
            from maintenance_operation_classifier import MaintenanceOperationClassifier, OperationType
            
            classifier = MaintenanceOperationClassifier()
            blocked_operations = []
            
            # Check each operation type
            for operation_type in OperationType:
                if classifier.is_blocked_operation(operation_type, status.mode):
                    blocked_operations.append(operation_type.value)
            
            return blocked_operations
            
        except Exception as e:
            logger.error(f"Error getting blocked operations: {str(e)}")
            return []
    
    def get_maintenance_message(self, operation: str = None) -> str:
        """
        Get user-facing maintenance message
        
        Args:
            operation: Specific operation being blocked (optional)
            
        Returns:
            User-friendly maintenance message
        """
        try:
            status = self.get_maintenance_status()
            
            if not status.is_active:
                return "System is operating normally."
            
            # Build maintenance message
            if status.mode == MaintenanceMode.EMERGENCY:
                message = "🚨 Emergency maintenance is currently in progress."
            elif status.mode == MaintenanceMode.TEST:
                message = "🧪 Test maintenance mode is active."
            else:
                message = "🔧 System maintenance is currently in progress."
            
            if status.reason:
                message += f" Reason: {status.reason}"
            
            if status.estimated_completion:
                completion_str = status.estimated_completion.strftime("%Y-%m-%d %H:%M UTC")
                message += f" Expected completion: {completion_str}"
            elif status.estimated_duration:
                message += f" Estimated duration: {status.estimated_duration} minutes"
            
            if operation:
                # Get user-friendly operation description
                operation_description = self._get_operation_description(operation)
                if operation_description:
                    message += f" The requested operation ({operation_description}) is temporarily unavailable."
                else:
                    message += f" The requested operation ({operation}) is temporarily unavailable."
            
            message += " Please try again later."
            
            return message
            
        except Exception as e:
            logger.error(f"Error getting maintenance message: {str(e)}")
            return "System maintenance is in progress. Please try again later."
    
    def _get_operation_description(self, operation: str) -> str:
        """
        Get user-friendly description for operation
        
        Args:
            operation: Operation name or endpoint
            
        Returns:
            User-friendly description or empty string if not found
        """
        try:
            # Import operation classifier here to avoid circular imports
            from maintenance_operation_classifier import MaintenanceOperationClassifier
            
            # Ensure operation has leading slash for classification
            # (classifier patterns expect URL paths like /start_caption_generation)
            operation_for_classification = operation
            if not operation.startswith('/'):
                operation_for_classification = '/' + operation
            
            # Classify the operation to get its type
            classifier = MaintenanceOperationClassifier()
            operation_type = classifier.classify_operation(operation_for_classification, 'POST')
            
            # Map operation types to user-friendly descriptions
            operation_descriptions = {
                'caption_generation': 'caption generation',
                'job_creation': 'job creation',
                'platform_operations': 'platform operations',
                'batch_operations': 'batch operations',
                'user_data_modification': 'user data modification',
                'image_processing': 'image processing',
                'admin_operations': 'administrative operations',
                'read_operations': 'read operations',
                'authentication': 'authentication',
            }
            
            return operation_descriptions.get(operation_type.value, '')
            
        except Exception as e:
            logger.error(f"Error getting operation description for {operation}: {str(e)}")
            return ''
    
    def subscribe_to_changes(self, callback: Callable[[str, MaintenanceStatus], None]) -> str:
        """
        Subscribe to maintenance mode changes
        
        Args:
            callback: Callback function (event_type, status)
            
        Returns:
            Subscription ID
        """
        subscription_id = str(uuid.uuid4())
        
        with self._subscribers_lock:
            self._change_subscribers[subscription_id] = callback
        
        logger.debug(f"Added maintenance mode subscription {subscription_id}")
        return subscription_id
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """
        Remove maintenance mode change subscription
        
        Args:
            subscription_id: Subscription ID to remove
            
        Returns:
            True if subscription was found and removed
        """
        with self._subscribers_lock:
            if subscription_id in self._change_subscribers:
                del self._change_subscribers[subscription_id]
                logger.debug(f"Removed maintenance mode subscription {subscription_id}")
                return True
        
        return False
    
    def get_service_stats(self) -> Dict[str, Any]:
        """
        Get maintenance mode service statistics
        
        Returns:
            Dictionary with service statistics
        """
        with self._stats_lock:
            stats = self._stats.copy()
        
        status = self.get_maintenance_status()
        
        return {
            'current_status': {
                'is_active': status.is_active,
                'mode': status.mode.value,
                'reason': status.reason,
                'started_at': status.started_at.isoformat() if status.started_at else None,
                'test_mode': status.test_mode
            },
            'statistics': stats,
            'subscribers_count': len(self._change_subscribers),
            'blocked_operations_count': len(self.get_blocked_operations())
        }
    
    def _is_admin_user(self, user: User) -> bool:
        """
        Check if user is an admin and should bypass maintenance mode
        
        Args:
            user: User object to check
            
        Returns:
            True if user is admin, False otherwise
        """
        try:
            return user.role == UserRole.ADMIN
        except Exception as e:
            logger.error(f"Error checking admin user status: {str(e)}")
            return False
    
    def _setup_configuration_subscriptions(self):
        """Setup subscriptions to configuration changes"""
        try:
            # Subscribe to maintenance mode configuration changes
            self.config_service.subscribe_to_changes(
                self.MAINTENANCE_MODE_KEY,
                self._handle_maintenance_config_change
            )
            
            self.config_service.subscribe_to_changes(
                self.MAINTENANCE_REASON_KEY,
                self._handle_maintenance_config_change
            )
            
            logger.debug("Setup enhanced maintenance mode configuration subscriptions")
            
        except Exception as e:
            logger.error(f"Error setting up configuration subscriptions: {str(e)}")
    
    def _handle_maintenance_config_change(self, key: str, old_value: Any, new_value: Any):
        """
        Handle maintenance mode configuration changes
        
        Args:
            key: Configuration key that changed
            old_value: Previous value
            new_value: New value
        """
        try:
            logger.info(f"Maintenance configuration changed: {key} = {new_value}")
            
            # Clear cached status to force refresh
            with self._status_lock:
                self._current_status = None
            
            # Get updated status
            updated_status = self.get_maintenance_status()
            
            # Notify subscribers
            self._notify_change_subscribers('configuration_changed', updated_status)
            
        except Exception as e:
            logger.error(f"Error handling maintenance configuration change: {str(e)}")
    
    def _notify_change_subscribers(self, event_type: str, status: MaintenanceStatus):
        """
        Notify subscribers of maintenance mode changes
        
        Args:
            event_type: Type of change event
            status: Current maintenance status
        """
        with self._subscribers_lock:
            for subscription_id, callback in self._change_subscribers.items():
                try:
                    callback(event_type, status)
                except Exception as e:
                    logger.error(f"Error in maintenance mode change callback {subscription_id}: {str(e)}")
    
    def update_active_jobs_count(self, count: int) -> None:
        """
        Update the count of active jobs during maintenance
        
        Args:
            count: Current number of active jobs
        """
        try:
            with self._status_lock:
                if self._current_status:
                    self._current_status.active_jobs_count = count
                    logger.debug(f"Updated active jobs count to {count}")
        except Exception as e:
            logger.error(f"Error updating active jobs count: {str(e)}")
    
    def update_invalidated_sessions_count(self, count: int) -> None:
        """
        Update the count of invalidated sessions during maintenance
        
        Args:
            count: Number of sessions that were invalidated
        """
        try:
            with self._status_lock:
                if self._current_status:
                    self._current_status.invalidated_sessions = count
                    logger.debug(f"Updated invalidated sessions count to {count}")
        except Exception as e:
            logger.error(f"Error updating invalidated sessions count: {str(e)}")
    
    def log_maintenance_event(self, event_type: str, details: Dict[str, Any], 
                             administrator: Optional[str] = None) -> None:
        """
        Log maintenance event with administrator identification
        
        Args:
            event_type: Type of maintenance event
            details: Event details dictionary
            administrator: Administrator who performed the action
        """
        try:
            event_data = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'event_type': event_type,
                'administrator': administrator,
                'details': details,
                'maintenance_status': {
                    'is_active': self.get_maintenance_status().is_active,
                    'mode': self.get_maintenance_status().mode.value
                }
            }
            
            # Log the event
            logger.info(f"Maintenance event: {event_type} by {administrator}", extra=event_data)
            
            # Here you could also store the event in a database or send to monitoring system
            # For now, we'll just log it
            
        except Exception as e:
            logger.error(f"Error logging maintenance event: {str(e)}")
    
    def get_maintenance_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get maintenance event history
        
        Args:
            limit: Maximum number of events to return
            
        Returns:
            List of maintenance events
        """
        try:
            # In a real implementation, this would query a database or log store
            # For now, return empty list as we're just logging events
            logger.debug(f"Maintenance history requested (limit: {limit})")
            return []
            
        except Exception as e:
            logger.error(f"Error getting maintenance history: {str(e)}")
            return []
    
    def create_maintenance_report(self) -> Dict[str, Any]:
        """
        Create comprehensive maintenance status report
        
        Returns:
            Dictionary with maintenance report data
        """
        try:
            status = self.get_maintenance_status()
            blocked_operations = self.get_blocked_operations()
            service_stats = self.get_service_stats()
            
            report = {
                'report_generated_at': datetime.now(timezone.utc).isoformat(),
                'maintenance_status': {
                    'is_active': status.is_active,
                    'mode': status.mode.value,
                    'reason': status.reason,
                    'estimated_duration': status.estimated_duration,
                    'started_at': status.started_at.isoformat() if status.started_at else None,
                    'estimated_completion': status.estimated_completion.isoformat() if status.estimated_completion else None,
                    'enabled_by': status.enabled_by,
                    'test_mode': status.test_mode
                },
                'blocked_operations': {
                    'count': len(blocked_operations),
                    'operations': blocked_operations
                },
                'system_impact': {
                    'active_jobs_count': status.active_jobs_count,
                    'invalidated_sessions': status.invalidated_sessions
                },
                'service_statistics': service_stats['statistics'],
                'subscribers_count': service_stats['subscribers_count']
            }
            
            logger.debug("Generated maintenance status report")
            return report
            
        except Exception as e:
            logger.error(f"Error creating maintenance report: {str(e)}")
            return {
                'report_generated_at': datetime.now(timezone.utc).isoformat(),
                'error': str(e),
                'maintenance_status': {'is_active': False}
            }
    
    def get_active_jobs_info(self) -> Dict[str, Any]:
        """
        Get detailed information about active jobs during maintenance
        
        Returns:
            Dictionary with active jobs information
        """
        try:
            if not self._completion_tracker:
                return {
                    'active_jobs_count': 0,
                    'active_jobs': [],
                    'completion_tracker_available': False
                }
            
            active_jobs = self._completion_tracker.get_active_jobs()
            completion_stats = self._completion_tracker.get_completion_stats()
            
            return {
                'active_jobs_count': len(active_jobs),
                'active_jobs': [
                    {
                        'job_id': job.job_id,
                        'user_id': job.user_id,
                        'job_type': job.job_type,
                        'status': job.status,
                        'progress_percent': job.progress_percent,
                        'current_step': job.current_step,
                        'started_at': job.started_at.isoformat() if job.started_at else None,
                        'estimated_completion': job.estimated_completion.isoformat() if job.estimated_completion else None,
                        'platform_connection_id': job.platform_connection_id
                    }
                    for job in active_jobs
                ],
                'completion_stats': completion_stats,
                'completion_tracker_available': True,
                'estimated_all_jobs_completion': self._completion_tracker.get_estimated_completion_time().isoformat() if self._completion_tracker.get_estimated_completion_time() else None
            }
            
        except Exception as e:
            logger.error(f"Error getting active jobs info: {str(e)}")
            return {
                'active_jobs_count': 0,
                'active_jobs': [],
                'completion_tracker_available': False,
                'error': str(e)
            }
    
    def get_job_completion_notifications(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get recent job completion notifications
        
        Args:
            limit: Maximum number of notifications to return
            
        Returns:
            List of completion notification dictionaries
        """
        try:
            if not self._completion_tracker:
                return []
            
            notifications = self._completion_tracker.get_completed_jobs(limit)
            
            return [
                {
                    'job_id': notification.job_id,
                    'user_id': notification.user_id,
                    'job_type': notification.job_type,
                    'completion_status': notification.completion_status,
                    'completed_at': notification.completed_at.isoformat(),
                    'duration_seconds': notification.duration_seconds,
                    'error_message': notification.error_message
                }
                for notification in notifications
            ]
            
        except Exception as e:
            logger.error(f"Error getting completion notifications: {str(e)}")
            return []
    
    def subscribe_to_job_completions(self, callback: Callable) -> Optional[str]:
        """
        Subscribe to job completion notifications
        
        Args:
            callback: Callback function to receive notifications
            
        Returns:
            Subscription ID or None if tracker not available
        """
        try:
            if not self._completion_tracker:
                return None
            
            return self._completion_tracker.subscribe_to_completions(callback)
            
        except Exception as e:
            logger.error(f"Error subscribing to job completions: {str(e)}")
            return None
    
    def unsubscribe_from_job_completions(self, subscription_id: str) -> bool:
        """
        Remove job completion subscription
        
        Args:
            subscription_id: Subscription ID to remove
            
        Returns:
            True if subscription was removed
        """
        try:
            if not self._completion_tracker:
                return False
            
            return self._completion_tracker.unsubscribe_from_completions(subscription_id)
            
        except Exception as e:
            logger.error(f"Error unsubscribing from job completions: {str(e)}")
            return False
    
    def allow_operation_completion(self, operation_id: str) -> bool:
        """
        Allow a specific operation to complete during maintenance
        
        Args:
            operation_id: ID of the operation to allow completion
            
        Returns:
            True if operation is allowed to complete
        """
        try:
            # Check if operation is currently active
            if self._completion_tracker:
                active_jobs = self._completion_tracker.get_active_jobs()
                for job in active_jobs:
                    if job.job_id == operation_id:
                        logger.info(f"Allowing operation {operation_id} to complete during maintenance")
                        return True
            
            # If not found in active jobs, it may have already completed or not exist
            logger.debug(f"Operation {operation_id} not found in active jobs")
            return False
            
        except Exception as e:
            logger.error(f"Error checking operation completion allowance: {str(e)}")
            return False
    
    def get_user_active_jobs(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Get active jobs for a specific user
        
        Args:
            user_id: User ID to get jobs for
            
        Returns:
            List of active job dictionaries for the user
        """
        try:
            if not self._completion_tracker:
                return []
            
            user_jobs = self._completion_tracker.get_jobs_by_user(user_id)
            
            return [
                {
                    'job_id': job.job_id,
                    'job_type': job.job_type,
                    'status': job.status,
                    'progress_percent': job.progress_percent,
                    'current_step': job.current_step,
                    'started_at': job.started_at.isoformat() if job.started_at else None,
                    'estimated_completion': job.estimated_completion.isoformat() if job.estimated_completion else None,
                    'platform_connection_id': job.platform_connection_id
                }
                for job in user_jobs
            ]
            
        except Exception as e:
            logger.error(f"Error getting user active jobs: {str(e)}")
            return []
    
    def is_user_job_active(self, user_id: int) -> bool:
        """
        Check if a user has any active jobs during maintenance
        
        Args:
            user_id: User ID to check
            
        Returns:
            True if user has active jobs
        """
        try:
            if not self._completion_tracker:
                return False
            
            return self._completion_tracker.is_user_job_active(user_id)
            
        except Exception as e:
            logger.error(f"Error checking user job activity: {str(e)}")
            return False
    
    # Test Mode Implementation Methods
    
    def enable_test_mode(self, reason: str, duration: Optional[int] = None,
                        enabled_by: Optional[str] = None) -> bool:
        """
        Enable test maintenance mode for validation without affecting operations
        
        Args:
            reason: Reason for enabling test mode
            duration: Estimated duration in minutes (optional)
            enabled_by: Identifier of who enabled test mode
            
        Returns:
            True if test mode was enabled successfully
        """
        try:
            logger.info(f"Enabling test maintenance mode: {reason}")
            
            # Initialize test mode data
            with self._test_mode_lock:
                self._test_mode_data = {
                    'simulated_blocks': [],
                    'operation_attempts': [],
                    'validation_results': {},
                    'performance_metrics': {},
                    'started_at': datetime.now(timezone.utc),
                    'completed_at': None,
                    'test_session_id': str(uuid.uuid4()),
                    'total_operations_tested': 0,
                    'blocked_operations_count': 0,
                    'allowed_operations_count': 0,
                    'admin_bypasses_count': 0,
                    'operation_types_tested': set(),
                    'errors_encountered': []
                }
            
            # Enable maintenance mode in TEST mode
            success = self.enable_maintenance(
                reason=reason,
                duration=duration,
                mode=MaintenanceMode.TEST,
                enabled_by=enabled_by
            )
            
            if success:
                logger.info(f"Test maintenance mode enabled successfully with session ID: {self._test_mode_data['test_session_id']}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error enabling test maintenance mode: {str(e)}")
            return False
    
    def _record_test_mode_simulation(self, operation: str, user: Optional[User], would_block: bool) -> None:
        """
        Record test mode operation simulation for validation reporting
        
        Args:
            operation: Operation that was tested
            user: User attempting the operation (optional)
            would_block: Whether the operation would be blocked in real maintenance
        """
        try:
            with self._test_mode_lock:
                if not self._test_mode_data['started_at']:
                    return  # Test mode not active
                
                # Import operation classifier here to avoid circular imports
                from maintenance_operation_classifier import MaintenanceOperationClassifier
                
                classifier = MaintenanceOperationClassifier()
                operation_type = classifier.classify_operation(operation, 'GET')
                
                # Record the simulation
                simulation_record = {
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'operation': operation,
                    'operation_type': operation_type.value,
                    'user_id': user.id if user else None,
                    'user_role': user.role.value if user else None,
                    'would_block': would_block,
                    'is_admin_bypass': user and self._is_admin_user(user) if user else False
                }
                
                self._test_mode_data['simulated_blocks'].append(simulation_record)
                self._test_mode_data['total_operations_tested'] += 1
                self._test_mode_data['operation_types_tested'].add(operation_type.value)
                
                if would_block:
                    self._test_mode_data['blocked_operations_count'] += 1
                    with self._stats_lock:
                        self._stats['test_mode_simulated_blocks'] += 1
                else:
                    self._test_mode_data['allowed_operations_count'] += 1
                
                if user and self._is_admin_user(user):
                    self._test_mode_data['admin_bypasses_count'] += 1
                
                with self._stats_lock:
                    self._stats['test_mode_operation_attempts'] += 1
                
                logger.debug(f"Test mode simulation recorded: {operation} -> {'blocked' if would_block else 'allowed'}")
                
        except Exception as e:
            logger.error(f"Error recording test mode simulation: {str(e)}")
            with self._test_mode_lock:
                self._test_mode_data['errors_encountered'].append({
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'error': str(e),
                    'operation': operation
                })
    
    def get_test_mode_status(self) -> Dict[str, Any]:
        """
        Get current test mode status and statistics
        
        Returns:
            Dictionary with test mode status information
        """
        try:
            with self._test_mode_lock:
                if not self._test_mode_data['started_at']:
                    return {
                        'active': False,
                        'message': 'Test mode is not currently active'
                    }
                
                # Calculate duration
                started_at = self._test_mode_data['started_at']
                current_time = datetime.now(timezone.utc)
                duration_seconds = (current_time - started_at).total_seconds()
                
                return {
                    'active': True,
                    'test_session_id': self._test_mode_data['test_session_id'],
                    'started_at': started_at.isoformat(),
                    'duration_seconds': duration_seconds,
                    'total_operations_tested': self._test_mode_data['total_operations_tested'],
                    'blocked_operations_count': self._test_mode_data['blocked_operations_count'],
                    'allowed_operations_count': self._test_mode_data['allowed_operations_count'],
                    'admin_bypasses_count': self._test_mode_data['admin_bypasses_count'],
                    'operation_types_tested': list(self._test_mode_data['operation_types_tested']),
                    'errors_count': len(self._test_mode_data['errors_encountered']),
                    'simulations_count': len(self._test_mode_data['simulated_blocks'])
                }
                
        except Exception as e:
            logger.error(f"Error getting test mode status: {str(e)}")
            return {
                'active': False,
                'error': str(e)
            }
    
    def generate_test_mode_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive test mode validation report
        
        Returns:
            Dictionary with complete test mode report
        """
        try:
            with self._test_mode_lock:
                if not self._test_mode_data['started_at']:
                    return {
                        'error': 'No test mode session data available',
                        'report_generated_at': datetime.now(timezone.utc).isoformat()
                    }
                
                # Calculate test session metrics
                started_at = self._test_mode_data['started_at']
                completed_at = self._test_mode_data['completed_at'] or datetime.now(timezone.utc)
                duration_seconds = (completed_at - started_at).total_seconds()
                
                # Analyze operation types tested
                operation_type_stats = {}
                for simulation in self._test_mode_data['simulated_blocks']:
                    op_type = simulation['operation_type']
                    if op_type not in operation_type_stats:
                        operation_type_stats[op_type] = {
                            'total': 0,
                            'blocked': 0,
                            'allowed': 0,
                            'admin_bypasses': 0
                        }
                    
                    operation_type_stats[op_type]['total'] += 1
                    if simulation['would_block']:
                        operation_type_stats[op_type]['blocked'] += 1
                    else:
                        operation_type_stats[op_type]['allowed'] += 1
                    
                    if simulation['is_admin_bypass']:
                        operation_type_stats[op_type]['admin_bypasses'] += 1
                
                # Generate validation results
                validation_results = self._generate_test_validation_results(operation_type_stats)
                
                # Create comprehensive report
                report = {
                    'report_generated_at': datetime.now(timezone.utc).isoformat(),
                    'test_session': {
                        'session_id': self._test_mode_data['test_session_id'],
                        'started_at': started_at.isoformat(),
                        'completed_at': completed_at.isoformat() if self._test_mode_data['completed_at'] else None,
                        'duration_seconds': duration_seconds,
                        'status': 'completed' if self._test_mode_data['completed_at'] else 'active'
                    },
                    'test_summary': {
                        'total_operations_tested': self._test_mode_data['total_operations_tested'],
                        'blocked_operations_count': self._test_mode_data['blocked_operations_count'],
                        'allowed_operations_count': self._test_mode_data['allowed_operations_count'],
                        'admin_bypasses_count': self._test_mode_data['admin_bypasses_count'],
                        'operation_types_tested': list(self._test_mode_data['operation_types_tested']),
                        'errors_encountered': len(self._test_mode_data['errors_encountered'])
                    },
                    'operation_type_analysis': operation_type_stats,
                    'validation_results': validation_results,
                    'performance_metrics': self._calculate_test_performance_metrics(),
                    'detailed_simulations': self._test_mode_data['simulated_blocks'],
                    'errors': self._test_mode_data['errors_encountered']
                }
                
                logger.info(f"Generated test mode report for session {self._test_mode_data['test_session_id']}")
                return report
                
        except Exception as e:
            logger.error(f"Error generating test mode report: {str(e)}")
            return {
                'error': str(e),
                'report_generated_at': datetime.now(timezone.utc).isoformat()
            }
    
    def _generate_test_validation_results(self, operation_type_stats: Dict[str, Dict[str, int]]) -> Dict[str, Any]:
        """
        Generate validation results based on test mode data
        
        Args:
            operation_type_stats: Statistics by operation type
            
        Returns:
            Dictionary with validation results
        """
        try:
            # Import operation classifier here to avoid circular imports
            from maintenance_operation_classifier import MaintenanceOperationClassifier
            
            classifier = MaintenanceOperationClassifier()
            expected_blocked_operations = classifier.get_blocked_operations_for_mode(MaintenanceMode.TEST)
            
            validation_results = {
                'overall_status': 'PASS',
                'issues_found': [],
                'recommendations': [],
                'coverage_analysis': {},
                'blocking_accuracy': {}
            }
            
            # Check coverage of operation types
            expected_operation_types = {op.value for op in expected_blocked_operations}
            tested_operation_types = set(operation_type_stats.keys())
            
            missing_coverage = expected_operation_types - tested_operation_types
            if missing_coverage:
                validation_results['issues_found'].append({
                    'type': 'COVERAGE_GAP',
                    'message': f'Operation types not tested: {list(missing_coverage)}',
                    'severity': 'WARNING'
                })
                validation_results['recommendations'].append(
                    'Test additional operation types to ensure comprehensive coverage'
                )
            
            # Analyze blocking accuracy
            for op_type, stats in operation_type_stats.items():
                expected_blocked = any(op.value == op_type for op in expected_blocked_operations)
                actual_blocked_ratio = stats['blocked'] / stats['total'] if stats['total'] > 0 else 0
                
                validation_results['blocking_accuracy'][op_type] = {
                    'expected_blocked': expected_blocked,
                    'actual_blocked_ratio': actual_blocked_ratio,
                    'total_tests': stats['total'],
                    'status': 'PASS' if (expected_blocked and actual_blocked_ratio > 0.8) or 
                             (not expected_blocked and actual_blocked_ratio < 0.2) else 'FAIL'
                }
                
                if validation_results['blocking_accuracy'][op_type]['status'] == 'FAIL':
                    validation_results['overall_status'] = 'FAIL'
                    validation_results['issues_found'].append({
                        'type': 'BLOCKING_ACCURACY',
                        'message': f'Operation type {op_type} blocking behavior does not match expectations',
                        'severity': 'ERROR'
                    })
            
            # Coverage analysis
            validation_results['coverage_analysis'] = {
                'expected_operation_types': list(expected_operation_types),
                'tested_operation_types': list(tested_operation_types),
                'coverage_percentage': len(tested_operation_types) / len(expected_operation_types) * 100 if expected_operation_types else 100,
                'missing_coverage': list(missing_coverage)
            }
            
            return validation_results
            
        except Exception as e:
            logger.error(f"Error generating test validation results: {str(e)}")
            return {
                'overall_status': 'ERROR',
                'error': str(e)
            }
    
    def _calculate_test_performance_metrics(self) -> Dict[str, Any]:
        """
        Calculate performance metrics for test mode operations
        
        Returns:
            Dictionary with performance metrics
        """
        try:
            with self._test_mode_lock:
                if not self._test_mode_data['simulated_blocks']:
                    return {'message': 'No performance data available'}
                
                # Calculate timing metrics
                timestamps = [
                    datetime.fromisoformat(sim['timestamp'].replace('Z', '+00:00'))
                    for sim in self._test_mode_data['simulated_blocks']
                ]
                
                if len(timestamps) < 2:
                    return {'message': 'Insufficient data for performance analysis'}
                
                # Calculate operation rate
                duration = (timestamps[-1] - timestamps[0]).total_seconds()
                operations_per_second = len(timestamps) / duration if duration > 0 else 0
                
                # Calculate response time simulation (simulated overhead)
                avg_simulation_overhead_ms = 5.0  # Estimated overhead for test mode simulation
                
                return {
                    'total_operations': len(timestamps),
                    'test_duration_seconds': duration,
                    'operations_per_second': operations_per_second,
                    'avg_simulation_overhead_ms': avg_simulation_overhead_ms,
                    'first_operation': timestamps[0].isoformat(),
                    'last_operation': timestamps[-1].isoformat(),
                    'performance_status': 'GOOD' if operations_per_second > 0.1 else 'SLOW'
                }
                
        except Exception as e:
            logger.error(f"Error calculating test performance metrics: {str(e)}")
            return {'error': str(e)}
    
    def complete_test_mode(self) -> Dict[str, Any]:
        """
        Complete test mode session and generate final report
        
        Returns:
            Dictionary with completion status and final report
        """
        try:
            logger.info("Completing test maintenance mode session")
            
            # Mark test mode as completed
            with self._test_mode_lock:
                self._test_mode_data['completed_at'] = datetime.now(timezone.utc)
            
            # Generate final report
            final_report = self.generate_test_mode_report()
            
            # Disable maintenance mode
            self.disable_maintenance(disabled_by="test_mode_completion")
            
            logger.info(f"Test maintenance mode completed successfully. Session ID: {self._test_mode_data.get('test_session_id', 'unknown')}")
            
            return {
                'status': 'completed',
                'completion_time': datetime.now(timezone.utc).isoformat(),
                'final_report': final_report
            }
            
        except Exception as e:
            logger.error(f"Error completing test mode: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def reset_test_mode_data(self) -> bool:
        """
        Reset test mode data for a new test session
        
        Returns:
            True if reset was successful
        """
        try:
            with self._test_mode_lock:
                self._test_mode_data = {
                    'simulated_blocks': [],
                    'operation_attempts': [],
                    'validation_results': {},
                    'performance_metrics': {},
                    'started_at': None,
                    'completed_at': None,
                    'test_session_id': None,
                    'total_operations_tested': 0,
                    'blocked_operations_count': 0,
                    'allowed_operations_count': 0,
                    'admin_bypasses_count': 0,
                    'operation_types_tested': set(),
                    'errors_encountered': []
                }
            
            logger.info("Test mode data reset successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error resetting test mode data: {str(e)}")
            return False
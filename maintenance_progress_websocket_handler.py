# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Maintenance Progress WebSocket Handler

Provides real-time maintenance operation progress updates via WebSocket connections.
Integrates with the unified notification system to deliver detailed progress reporting
for long-running maintenance operations to administrators.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import asyncio
import threading
import time

logger = logging.getLogger(__name__)


class ProgressUpdateType(Enum):
    """Types of progress updates"""
    STARTED = "started"
    PROGRESS = "progress"
    COMPLETED = "completed"
    ERROR = "error"
    WARNING = "warning"
    CANCELLED = "cancelled"


@dataclass
class MaintenanceProgressUpdate:
    """Data structure for maintenance progress updates"""
    operation_id: str
    operation_type: str
    update_type: ProgressUpdateType
    progress_percentage: Optional[int] = None
    current_step: Optional[str] = None
    total_steps: Optional[int] = None
    current_step_number: Optional[int] = None
    estimated_time_remaining: Optional[int] = None  # seconds
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


class MaintenanceProgressWebSocketHandler:
    """
    Handles real-time maintenance progress updates via WebSocket
    """
    
    def __init__(self, notification_manager, socketio_instance=None):
        """
        Initialize the progress WebSocket handler
        
        Args:
            notification_manager: UnifiedNotificationManager instance
            socketio_instance: SocketIO instance for direct WebSocket communication
        """
        self.notification_manager = notification_manager
        self.socketio = socketio_instance
        self.logger = logging.getLogger(__name__)
        
        # Track active progress sessions
        self._active_sessions = {}
        self._progress_callbacks = {}
        
        # Progress update queue for batch processing
        self._update_queue = []
        self._queue_lock = threading.Lock()
        
        # Start background progress processor
        self._start_progress_processor()
        
    def register_maintenance_operation(self, operation_id: str, operation_type: str,
                                     admin_user_id: int, total_steps: Optional[int] = None,
                                     estimated_duration: Optional[int] = None) -> bool:
        """
        Register a new maintenance operation for progress tracking
        
        Args:
            operation_id: Unique operation identifier
            operation_type: Type of maintenance operation
            admin_user_id: Administrator user ID to receive updates
            total_steps: Total number of steps in the operation
            estimated_duration: Estimated duration in seconds
            
        Returns:
            True if registered successfully, False otherwise
        """
        try:
            session_info = {
                'operation_id': operation_id,
                'operation_type': operation_type,
                'admin_user_id': admin_user_id,
                'total_steps': total_steps,
                'estimated_duration': estimated_duration,
                'started_at': datetime.now(timezone.utc),
                'current_step': 0,
                'progress_percentage': 0,
                'last_update': datetime.now(timezone.utc),
                'status': 'started'
            }
            
            self._active_sessions[operation_id] = session_info
            
            # Send initial progress notification
            initial_update = MaintenanceProgressUpdate(
                operation_id=operation_id,
                operation_type=operation_type,
                update_type=ProgressUpdateType.STARTED,
                progress_percentage=0,
                current_step="Initializing maintenance operation",
                total_steps=total_steps,
                current_step_number=0,
                estimated_time_remaining=estimated_duration,
                message=f"Maintenance operation '{operation_type}' has started"
            )
            
            self._queue_progress_update(admin_user_id, initial_update)
            
            self.logger.info(f"Registered maintenance operation {operation_id} for admin {admin_user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error registering maintenance operation: {e}")
            return False
    
    def update_progress(self, operation_id: str, progress_percentage: Optional[int] = None,
                       current_step: Optional[str] = None, current_step_number: Optional[int] = None,
                       message: Optional[str] = None, details: Optional[Dict[str, Any]] = None) -> bool:
        """
        Update progress for a maintenance operation
        
        Args:
            operation_id: Operation identifier
            progress_percentage: Current progress percentage (0-100)
            current_step: Description of current step
            current_step_number: Current step number
            message: Progress message
            details: Additional progress details
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            if operation_id not in self._active_sessions:
                self.logger.warning(f"Progress update for unknown operation: {operation_id}")
                return False
            
            session_info = self._active_sessions[operation_id]
            admin_user_id = session_info['admin_user_id']
            
            # Update session info
            if progress_percentage is not None:
                session_info['progress_percentage'] = progress_percentage
            if current_step_number is not None:
                session_info['current_step'] = current_step_number
            session_info['last_update'] = datetime.now(timezone.utc)
            
            # Calculate estimated time remaining
            estimated_time_remaining = None
            if progress_percentage is not None and progress_percentage > 0:
                elapsed_time = (datetime.now(timezone.utc) - session_info['started_at']).total_seconds()
                if progress_percentage < 100:
                    estimated_total_time = elapsed_time * (100 / progress_percentage)
                    estimated_time_remaining = int(estimated_total_time - elapsed_time)
            
            # Create progress update
            progress_update = MaintenanceProgressUpdate(
                operation_id=operation_id,
                operation_type=session_info['operation_type'],
                update_type=ProgressUpdateType.PROGRESS,
                progress_percentage=progress_percentage,
                current_step=current_step,
                total_steps=session_info.get('total_steps'),
                current_step_number=current_step_number,
                estimated_time_remaining=estimated_time_remaining,
                message=message,
                details=details
            )
            
            self._queue_progress_update(admin_user_id, progress_update)
            
            # Check if operation completed
            if progress_percentage is not None and progress_percentage >= 100:
                self._complete_operation(operation_id, "Operation completed successfully")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating progress for operation {operation_id}: {e}")
            return False
    
    def report_error(self, operation_id: str, error_message: str, 
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
            if operation_id not in self._active_sessions:
                self.logger.warning(f"Error report for unknown operation: {operation_id}")
                return False
            
            session_info = self._active_sessions[operation_id]
            admin_user_id = session_info['admin_user_id']
            
            # Create error update
            error_update = MaintenanceProgressUpdate(
                operation_id=operation_id,
                operation_type=session_info['operation_type'],
                update_type=ProgressUpdateType.ERROR,
                progress_percentage=session_info.get('progress_percentage'),
                current_step=f"Error: {error_message}",
                message=error_message,
                details={
                    'error_details': error_details,
                    'recoverable': recoverable,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            )
            
            self._queue_progress_update(admin_user_id, error_update)
            
            # Update session status
            session_info['status'] = 'error'
            session_info['last_error'] = error_message
            
            # If not recoverable, complete the operation with error
            if not recoverable:
                self._complete_operation(operation_id, f"Operation failed: {error_message}", success=False)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error reporting error for operation {operation_id}: {e}")
            return False
    
    def complete_operation(self, operation_id: str, completion_message: str = "Operation completed",
                          success: bool = True, final_details: Optional[Dict[str, Any]] = None) -> bool:
        """
        Mark a maintenance operation as completed
        
        Args:
            operation_id: Operation identifier
            completion_message: Completion message
            success: Whether the operation completed successfully
            final_details: Final operation details
            
        Returns:
            True if completed successfully, False otherwise
        """
        return self._complete_operation(operation_id, completion_message, success, final_details)
    
    def _complete_operation(self, operation_id: str, completion_message: str,
                           success: bool = True, final_details: Optional[Dict[str, Any]] = None) -> bool:
        """
        Internal method to complete an operation
        """
        try:
            if operation_id not in self._active_sessions:
                self.logger.warning(f"Completion for unknown operation: {operation_id}")
                return False
            
            session_info = self._active_sessions[operation_id]
            admin_user_id = session_info['admin_user_id']
            
            # Calculate final statistics
            total_duration = (datetime.now(timezone.utc) - session_info['started_at']).total_seconds()
            
            # Create completion update
            completion_update = MaintenanceProgressUpdate(
                operation_id=operation_id,
                operation_type=session_info['operation_type'],
                update_type=ProgressUpdateType.COMPLETED if success else ProgressUpdateType.ERROR,
                progress_percentage=100 if success else session_info.get('progress_percentage'),
                current_step="Operation completed" if success else "Operation failed",
                message=completion_message,
                details={
                    'success': success,
                    'total_duration_seconds': int(total_duration),
                    'total_steps_completed': session_info.get('current_step', 0),
                    'final_details': final_details or {}
                }
            )
            
            self._queue_progress_update(admin_user_id, completion_update)
            
            # Remove from active sessions
            del self._active_sessions[operation_id]
            
            self.logger.info(f"Completed maintenance operation {operation_id} with success={success}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error completing operation {operation_id}: {e}")
            return False
    
    def _queue_progress_update(self, admin_user_id: int, progress_update: MaintenanceProgressUpdate) -> None:
        """
        Queue a progress update for processing
        """
        try:
            with self._queue_lock:
                self._update_queue.append((admin_user_id, progress_update))
                
        except Exception as e:
            self.logger.error(f"Error queuing progress update: {e}")
    
    def _start_progress_processor(self) -> None:
        """
        Start the background progress processor thread
        """
        def process_updates():
            while True:
                try:
                    updates_to_process = []
                    
                    # Get queued updates
                    with self._queue_lock:
                        if self._update_queue:
                            updates_to_process = self._update_queue.copy()
                            self._update_queue.clear()
                    
                    # Process updates
                    for admin_user_id, progress_update in updates_to_process:
                        self._send_progress_notification(admin_user_id, progress_update)
                    
                    # Sleep before next processing cycle
                    time.sleep(0.5)  # Process updates every 500ms
                    
                except Exception as e:
                    self.logger.error(f"Error in progress processor: {e}")
                    time.sleep(1)  # Wait longer on error
        
        # Start processor thread
        processor_thread = threading.Thread(target=process_updates, daemon=True)
        processor_thread.start()
        
        self.logger.info("Started maintenance progress processor thread")
    
    def _send_progress_notification(self, admin_user_id: int, 
                                  progress_update: MaintenanceProgressUpdate) -> bool:
        """
        Send progress notification via unified notification system
        """
        try:
            from unified_notification_manager import AdminNotificationMessage
            from models import NotificationType, NotificationPriority, NotificationCategory
            
            # Determine notification type based on update type
            if progress_update.update_type == ProgressUpdateType.STARTED:
                notification_type = NotificationType.INFO
                title = "🔧 Maintenance Started"
            elif progress_update.update_type == ProgressUpdateType.PROGRESS:
                notification_type = NotificationType.INFO
                if progress_update.progress_percentage is not None:
                    title = f"🔄 Progress: {progress_update.progress_percentage}%"
                else:
                    title = "🔄 Maintenance Progress"
            elif progress_update.update_type == ProgressUpdateType.COMPLETED:
                notification_type = NotificationType.SUCCESS
                title = "✅ Maintenance Completed"
            elif progress_update.update_type == ProgressUpdateType.ERROR:
                notification_type = NotificationType.ERROR
                title = "❌ Maintenance Error"
            else:
                notification_type = NotificationType.WARNING
                title = "⚠️ Maintenance Warning"
            
            # Create notification
            notification = AdminNotificationMessage(
                id=f"maintenance_progress_{progress_update.operation_id}_{int(progress_update.timestamp.timestamp())}",
                type=notification_type,
                title=title,
                message=progress_update.message or f"Maintenance operation '{progress_update.operation_type}' update",
                user_id=admin_user_id,
                priority=NotificationPriority.HIGH if progress_update.update_type == ProgressUpdateType.ERROR else NotificationPriority.NORMAL,
                category=NotificationCategory.MAINTENANCE,
                admin_only=True,
                data={
                    'operation_id': progress_update.operation_id,
                    'operation_type': progress_update.operation_type,
                    'update_type': progress_update.update_type.value,
                    'progress_percentage': progress_update.progress_percentage,
                    'current_step': progress_update.current_step,
                    'total_steps': progress_update.total_steps,
                    'current_step_number': progress_update.current_step_number,
                    'estimated_time_remaining': progress_update.estimated_time_remaining,
                    'details': progress_update.details,
                    'timestamp': progress_update.timestamp.isoformat(),
                    'is_progress_update': True
                },
                requires_action=progress_update.update_type == ProgressUpdateType.ERROR,
                action_url=f"/admin/maintenance-monitoring?operation_id={progress_update.operation_id}",
                action_text="View Details"
            )
            
            # Send via unified notification system
            success = self.notification_manager.send_admin_notification(notification)
            
            # Also send via direct WebSocket if available
            if self.socketio and success:
                self._send_direct_websocket_update(admin_user_id, progress_update)
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error sending progress notification: {e}")
            return False
    
    def _send_direct_websocket_update(self, admin_user_id: int, 
                                    progress_update: MaintenanceProgressUpdate) -> None:
        """
        Send direct WebSocket update for real-time progress
        """
        try:
            if not self.socketio:
                return
            
            # Prepare WebSocket data
            websocket_data = {
                'type': 'maintenance_progress',
                'operation_id': progress_update.operation_id,
                'operation_type': progress_update.operation_type,
                'update_type': progress_update.update_type.value,
                'progress_percentage': progress_update.progress_percentage,
                'current_step': progress_update.current_step,
                'total_steps': progress_update.total_steps,
                'current_step_number': progress_update.current_step_number,
                'estimated_time_remaining': progress_update.estimated_time_remaining,
                'message': progress_update.message,
                'details': progress_update.details,
                'timestamp': progress_update.timestamp.isoformat()
            }
            
            # Send to admin namespace
            self.socketio.emit('maintenance_progress_update', websocket_data, 
                             room=f'user_{admin_user_id}', namespace='/admin')
            
            self.logger.debug(f"Sent direct WebSocket progress update for operation {progress_update.operation_id}")
            
        except Exception as e:
            self.logger.error(f"Error sending direct WebSocket update: {e}")
    
    def get_active_operations(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about currently active operations
        
        Returns:
            Dictionary of active operations with their current status
        """
        return {op_id: session_info.copy() for op_id, session_info in self._active_sessions.items()}
    
    def cancel_operation(self, operation_id: str, cancellation_reason: str = "Operation cancelled") -> bool:
        """
        Cancel an active maintenance operation
        
        Args:
            operation_id: Operation identifier
            cancellation_reason: Reason for cancellation
            
        Returns:
            True if cancelled successfully, False otherwise
        """
        try:
            if operation_id not in self._active_sessions:
                self.logger.warning(f"Cancellation for unknown operation: {operation_id}")
                return False
            
            session_info = self._active_sessions[operation_id]
            admin_user_id = session_info['admin_user_id']
            
            # Create cancellation update
            cancellation_update = MaintenanceProgressUpdate(
                operation_id=operation_id,
                operation_type=session_info['operation_type'],
                update_type=ProgressUpdateType.CANCELLED,
                progress_percentage=session_info.get('progress_percentage'),
                current_step="Operation cancelled",
                message=cancellation_reason,
                details={'cancelled_at': datetime.now(timezone.utc).isoformat()}
            )
            
            self._queue_progress_update(admin_user_id, cancellation_update)
            
            # Remove from active sessions
            del self._active_sessions[operation_id]
            
            self.logger.info(f"Cancelled maintenance operation {operation_id}: {cancellation_reason}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error cancelling operation {operation_id}: {e}")
            return False
    
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
            
            for operation_id, operation_info in self._active_sessions.items():
                age = current_time - operation_info['started_at']
                if age.total_seconds() > (max_age_hours * 3600):
                    stale_operations.append(operation_id)
            
            for operation_id in stale_operations:
                del self._active_sessions[operation_id]
            
            if stale_operations:
                self.logger.info(f"Cleaned up {len(stale_operations)} stale maintenance operations")
            
            return len(stale_operations)
            
        except Exception as e:
            self.logger.error(f"Error cleaning up stale operations: {e}")
            return 0
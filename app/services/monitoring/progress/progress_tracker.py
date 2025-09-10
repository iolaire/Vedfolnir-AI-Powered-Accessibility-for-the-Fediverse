# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Progress Tracking System for Caption Generation

This module provides real-time progress tracking for caption generation tasks,
storing progress data and providing retrieval methods with user authorization.
"""

import logging
import threading
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass, asdict
from sqlalchemy.exc import SQLAlchemyError

from database import DatabaseManager
from models import CaptionGenerationTask, TaskStatus, GenerationResults
from security.core.security_utils import sanitize_for_log

logger = logging.getLogger(__name__)

@dataclass
class ProgressStatus:
    """Progress status data structure"""
    task_id: str
    user_id: int
    current_step: str
    progress_percent: int
    details: Dict[str, Any]
    started_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        # Convert datetime objects to ISO strings
        if self.started_at:
            data['started_at'] = self.started_at.isoformat()
        if self.updated_at:
            data['updated_at'] = self.updated_at.isoformat()
        return data

class ProgressTracker:
    """Tracks progress of caption generation tasks with real-time updates"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self._lock = threading.Lock()
        self._progress_callbacks: Dict[str, list] = {}  # task_id -> list of callbacks
        
    def create_progress_session(self, task_id: str, user_id: int) -> str:
        """
        Create a progress tracking session for a task
        
        Args:
            task_id: The task ID to track
            user_id: The user ID for authorization
            
        Returns:
            str: Session ID (same as task_id for simplicity)
            
        Raises:
            ValueError: If task not found or user not authorized
        """
        session = self.db_manager.get_session()
        try:
            # Verify task exists and user is authorized
            task = session.query(CaptionGenerationTask).filter_by(
                id=task_id,
                user_id=user_id
            ).first()
            
            if not task:
                raise ValueError(f"Task {task_id} not found or user {user_id} not authorized")
            
            logger.info(f"Created progress session for task {sanitize_for_log(task_id)}")
            return task_id
            
        except SQLAlchemyError as e:
            logger.error(f"Database error creating progress session: {sanitize_for_log(str(e))}")
            raise
        finally:
            session.close()
    
    def update_progress(
        self, 
        task_id: str, 
        current_step: str, 
        progress_percent: int,
        details: Dict[str, Any] = None
    ) -> bool:
        """
        Update progress for a task
        
        Args:
            task_id: The task ID to update
            current_step: Description of current processing step
            progress_percent: Progress percentage (0-100)
            details: Optional additional details
            
        Returns:
            bool: True if update was successful
        """
        if details is None:
            details = {}
            
        # Validate progress_percent
        progress_percent = max(0, min(100, progress_percent))
        
        session = self.db_manager.get_session()
        try:
            # Update task progress in database
            task = session.query(CaptionGenerationTask).filter_by(id=task_id).first()
            
            if not task:
                logger.warning(f"Task {sanitize_for_log(task_id)} not found for progress update")
                return False
            
            # Update progress fields
            task.current_step = current_step
            task.progress_percent = progress_percent
            session.commit()
            
            # Create progress status
            progress_status = ProgressStatus(
                task_id=task_id,
                user_id=task.user_id,
                current_step=current_step,
                progress_percent=progress_percent,
                details=details,
                started_at=task.started_at,
                updated_at=datetime.now(timezone.utc)
            )
            
            # Send WebSocket notification for real-time updates
            self._send_progress_notification(task.user_id, progress_status)
            
            # Notify callbacks
            self._notify_callbacks(task_id, progress_status)
            
            logger.debug(f"Updated progress for task {sanitize_for_log(task_id)}: {progress_percent}% - {current_step}")
            return True
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error updating progress: {sanitize_for_log(str(e))}")
            return False
        finally:
            session.close()
    
    def _send_progress_notification(self, user_id: int, progress_status: ProgressStatus):
        """
        Send WebSocket notification for progress update using unified notification system
        
        Args:
            user_id: User ID to send notification to
            progress_status: Progress status data
        """
        try:
            # Import here to avoid circular imports
            from unified_notification_manager import UnifiedNotificationManager, NotificationMessage
            from models import NotificationType, NotificationPriority, NotificationCategory
            
            # Get notification manager from Flask app context
            from flask import current_app
            if hasattr(current_app, 'notification_manager'):
                notification_manager = current_app.notification_manager
                
                # Determine if this is a significant progress milestone
                is_milestone = (
                    progress_status.progress_percent % 20 == 0 or  # Every 20%
                    progress_status.progress_percent >= 90 or      # Near completion
                    progress_status.progress_percent == 0 or       # Starting
                    'error' in progress_status.current_step.lower() or  # Error states
                    'complete' in progress_status.current_step.lower()   # Completion
                )
                
                # Create progress notification message
                notification = NotificationMessage(
                    id=f"caption_progress_{progress_status.task_id}_{progress_status.progress_percent}",
                    type=NotificationType.INFO,
                    title="Caption Generation Progress",
                    message=f"{progress_status.current_step} - {progress_status.progress_percent}%",
                    user_id=user_id,
                    priority=NotificationPriority.NORMAL,
                    category=NotificationCategory.CAPTION,
                    data={
                        'task_id': progress_status.task_id,
                        'progress_percent': progress_status.progress_percent,
                        'current_step': progress_status.current_step,
                        'details': progress_status.details,
                        'show_notification': is_milestone,
                        'estimated_completion': self._calculate_estimated_completion(progress_status),
                        'processing_rate': self._calculate_processing_rate(progress_status),
                        'notification_type': 'caption_progress',
                        'persistent': progress_status.progress_percent >= 100,  # Keep completion notifications
                        'auto_hide': progress_status.progress_percent < 100,    # Auto-hide progress updates
                        'category': 'caption'
                    }
                )
                
                # Send notification
                success = notification_manager.send_user_notification(user_id, notification)
                
                if success:
                    logger.debug(f"Sent progress notification for task {sanitize_for_log(progress_status.task_id)}")
                else:
                    logger.warning(f"Failed to send progress notification for task {sanitize_for_log(progress_status.task_id)}")
            else:
                logger.debug("Notification manager not available, skipping WebSocket notification")
                
        except Exception as e:
            logger.error(f"Error sending progress notification: {sanitize_for_log(str(e))}")
    
    def _calculate_estimated_completion(self, progress_status: ProgressStatus) -> str:
        """Calculate estimated completion time based on progress"""
        try:
            if progress_status.started_at and progress_status.progress_percent > 0:
                elapsed = datetime.now(timezone.utc) - progress_status.started_at
                total_estimated = elapsed / (progress_status.progress_percent / 100)
                remaining = total_estimated - elapsed
                
                if remaining.total_seconds() > 0:
                    minutes = int(remaining.total_seconds() / 60)
                    if minutes > 60:
                        hours = minutes // 60
                        minutes = minutes % 60
                        return f"~{hours}h {minutes}m"
                    else:
                        return f"~{minutes}m"
                else:
                    return "Almost done"
            return "Calculating..."
        except Exception:
            return "Unknown"
    
    def _calculate_processing_rate(self, progress_status: ProgressStatus) -> str:
        """Calculate processing rate based on progress"""
        try:
            if (progress_status.started_at and 
                progress_status.details.get('images_processed', 0) > 0):
                
                elapsed = datetime.now(timezone.utc) - progress_status.started_at
                elapsed_minutes = elapsed.total_seconds() / 60
                
                if elapsed_minutes > 0:
                    rate = progress_status.details['images_processed'] / elapsed_minutes
                    return f"{rate:.1f} images/min"
            return "-"
        except Exception:
            return "-"
    
    def complete_progress(self, task_id: str, results: Any):
        """
        Mark progress as complete and send completion notification
        
        Args:
            task_id: The task ID to complete
            results: Generation results
        """
        session = self.db_manager.get_session()
        try:
            task = session.query(CaptionGenerationTask).filter_by(id=task_id).first()
            
            if not task:
                logger.warning(f"Task {sanitize_for_log(task_id)} not found for completion")
                return
            
            # Update task status
            task.current_step = "Completed"
            task.progress_percent = 100
            session.commit()
            
            # Send completion notification
            self._send_completion_notification(task.user_id, task_id, results)
            
            logger.info(f"Completed progress tracking for task {sanitize_for_log(task_id)}")
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error completing progress: {sanitize_for_log(str(e))}")
        finally:
            session.close()
    
    def fail_progress(self, task_id: str, error_message: str, error_details: Dict[str, Any] = None):
        """
        Mark progress as failed and send error notification
        
        Args:
            task_id: The task ID that failed
            error_message: Error message
            error_details: Additional error details
        """
        if error_details is None:
            error_details = {}
            
        session = self.db_manager.get_session()
        try:
            task = session.query(CaptionGenerationTask).filter_by(id=task_id).first()
            
            if not task:
                logger.warning(f"Task {sanitize_for_log(task_id)} not found for failure")
                return
            
            # Update task status
            task.current_step = "Failed"
            task.progress_percent = 100  # Complete but failed
            session.commit()
            
            # Send error notification
            self._send_error_notification(task.user_id, task_id, error_message, error_details)
            
            logger.info(f"Failed progress tracking for task {sanitize_for_log(task_id)}: {sanitize_for_log(error_message)}")
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error failing progress: {sanitize_for_log(str(e))}")
        finally:
            session.close()
    
    def _send_completion_notification(self, user_id: int, task_id: str, results: Any):
        """Send WebSocket notification for task completion"""
        try:
            from unified_notification_manager import UnifiedNotificationManager, NotificationMessage
            from models import NotificationType, NotificationPriority, NotificationCategory
            from flask import current_app
            
            if hasattr(current_app, 'notification_manager'):
                notification_manager = current_app.notification_manager
                
                # Extract results data
                captions_generated = getattr(results, 'captions_generated', 0)
                images_processed = getattr(results, 'images_processed', 0)
                
                notification = NotificationMessage(
                    id=f"caption_complete_{task_id}",
                    type=NotificationType.SUCCESS,
                    title="Caption Generation Complete!",
                    message=f"Successfully generated {captions_generated} captions for {images_processed} images.",
                    user_id=user_id,
                    priority=NotificationPriority.HIGH,
                    category=NotificationCategory.CAPTION,
                    data={
                        'task_id': task_id,
                        'captions_generated': captions_generated,
                        'images_processed': images_processed,
                        'status': 'completed',
                        'redirect_url': '/review/batches',
                        'show_actions': True
                    },
                    requires_action=True,
                    action_url='/review/batches',
                    action_text='Review Captions'
                )
                
                notification_manager.send_user_notification(user_id, notification)
                logger.debug(f"Sent completion notification for task {sanitize_for_log(task_id)}")
                
        except Exception as e:
            logger.error(f"Error sending completion notification: {sanitize_for_log(str(e))}")
    
    def _send_error_notification(self, user_id: int, task_id: str, error_message: str, error_details: Dict[str, Any]):
        """Send WebSocket notification for task error"""
        try:
            from unified_notification_manager import UnifiedNotificationManager, NotificationMessage
            from models import NotificationType, NotificationPriority, NotificationCategory
            from flask import current_app
            
            if hasattr(current_app, 'notification_manager'):
                notification_manager = current_app.notification_manager
                
                notification = NotificationMessage(
                    id=f"caption_error_{task_id}",
                    type=NotificationType.ERROR,
                    title="Caption Generation Failed",
                    message=error_message,
                    user_id=user_id,
                    priority=NotificationPriority.HIGH,
                    category=NotificationCategory.CAPTION,
                    data={
                        'task_id': task_id,
                        'error_message': error_message,
                        'error_category': error_details.get('error_category', 'unknown'),
                        'recovery_suggestions': error_details.get('recovery_suggestions', []),
                        'status': 'failed',
                        'show_retry': True
                    },
                    requires_action=True
                )
                
                notification_manager.send_user_notification(user_id, notification)
                logger.debug(f"Sent error notification for task {sanitize_for_log(task_id)}")
                
        except Exception as e:
            logger.error(f"Error sending error notification: {sanitize_for_log(str(e))}")
    
    def send_maintenance_notification(self, user_id: int, maintenance_data: Dict[str, Any]):
        """
        Send maintenance notification for caption processing interruption
        
        Args:
            user_id: User ID to notify
            maintenance_data: Maintenance information
        """
        try:
            from unified_notification_manager import UnifiedNotificationManager, NotificationMessage
            from models import NotificationType, NotificationPriority, NotificationCategory
            from flask import current_app
            
            if hasattr(current_app, 'notification_manager'):
                notification_manager = current_app.notification_manager
                
                notification = NotificationMessage(
                    id=f"caption_maintenance_{user_id}_{int(datetime.now(timezone.utc).timestamp())}",
                    type=NotificationType.WARNING,
                    title="System Maintenance",
                    message=maintenance_data.get('message', 'Caption generation is temporarily paused for system maintenance.'),
                    user_id=user_id,
                    priority=NotificationPriority.HIGH,
                    category=NotificationCategory.MAINTENANCE,
                    data={
                        'affects_caption_processing': True,
                        'estimated_duration': maintenance_data.get('estimated_duration'),
                        'maintenance_type': maintenance_data.get('maintenance_type', 'system'),
                        'resume_time': maintenance_data.get('resume_time')
                    }
                )
                
                notification_manager.send_user_notification(user_id, notification)
                logger.info(f"Sent maintenance notification to user {user_id}")
                
        except Exception as e:
            logger.error(f"Error sending maintenance notification: {sanitize_for_log(str(e))}")
    
    def handle_maintenance_mode_change(self, maintenance_enabled: bool, maintenance_info: Dict[str, Any]):
        """
        Handle maintenance mode changes that affect caption processing
        
        Args:
            maintenance_enabled: Whether maintenance mode is enabled
            maintenance_info: Maintenance information
        """
        try:
            from flask import current_app
            
            if not hasattr(current_app, 'notification_manager'):
                return
            
            # Get all users with active caption generation tasks
            session = self.db_manager.get_session()
            try:
                active_tasks = session.query(CaptionGenerationTask).filter(
                    CaptionGenerationTask.status.in_([TaskStatus.QUEUED, TaskStatus.RUNNING])
                ).all()
                
                for task in active_tasks:
                    if maintenance_enabled:
                        # Send maintenance notification for task interruption
                        self.send_maintenance_notification(task.user_id, {
                            'message': maintenance_info.get('reason', 'System maintenance is in progress. Caption generation has been paused.'),
                            'estimated_duration': maintenance_info.get('estimated_duration'),
                            'affects_functionality': ['caption_generation'],
                            'maintenance_type': 'system',
                            'task_id': task.id
                        })
                        
                        # Update task status to indicate maintenance pause
                        self.send_caption_status_notification(
                            task.user_id,
                            task.id,
                            'paused',
                            'Caption generation paused for system maintenance'
                        )
                    else:
                        # Send maintenance completion notification
                        self.send_caption_status_notification(
                            task.user_id,
                            task.id,
                            'resumed',
                            'Caption generation resumed after maintenance'
                        )
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Error handling maintenance mode change: {sanitize_for_log(str(e))}")
    
    def get_progress(self, task_id: str, user_id: int = None) -> Optional[ProgressStatus]:
        """
        Get current progress for a task
        
        Args:
            task_id: The task ID to check
            user_id: Optional user ID for authorization check
            
        Returns:
            ProgressStatus or None if not found or unauthorized
        """
        session = self.db_manager.get_session()
        try:
            # Build query
            query = session.query(CaptionGenerationTask).filter_by(id=task_id)
            
            # Add user authorization if provided
            if user_id is not None:
                query = query.filter_by(user_id=user_id)
            
            task = query.first()
            
            if not task:
                return None
            
            # Create progress status from task data
            progress_status = ProgressStatus(
                task_id=task.id,
                user_id=task.user_id,
                current_step=task.current_step or "Initializing",
                progress_percent=task.progress_percent or 0,
                details={
                    'status': task.status.value,
                    'created_at': task.created_at.isoformat() if task.created_at else None,
                    'error_message': task.error_message
                },
                started_at=task.started_at,
                updated_at=datetime.now(timezone.utc)
            )
            
            return progress_status
            
        except SQLAlchemyError as e:
            logger.error(f"Database error getting progress: {sanitize_for_log(str(e))}")
            return None
        finally:
            session.close()
    
    def complete_progress(self, task_id: str, results: GenerationResults) -> bool:
        """
        Mark progress as complete and store results
        
        Args:
            task_id: The task ID to complete
            results: The generation results
            
        Returns:
            bool: True if completion was successful
        """
        session = self.db_manager.get_session()
        try:
            task = session.query(CaptionGenerationTask).filter_by(id=task_id).first()
            
            if not task:
                logger.warning(f"Task {sanitize_for_log(task_id)} not found for completion")
                return False
            
            # Update task with results
            task.results = results
            task.current_step = "Completed"
            task.progress_percent = 100
            session.commit()
            
            # Create final progress status
            progress_status = ProgressStatus(
                task_id=task_id,
                user_id=task.user_id,
                current_step="Completed",
                progress_percent=100,
                details={
                    'status': task.status.value,
                    'results': results.to_dict()
                },
                started_at=task.started_at,
                updated_at=datetime.now(timezone.utc)
            )
            
            # Notify callbacks
            self._notify_callbacks(task_id, progress_status)
            
            logger.info(f"Completed progress tracking for task {sanitize_for_log(task_id)}")
            return True
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error completing progress: {sanitize_for_log(str(e))}")
            return False
        finally:
            session.close()
    
    def register_callback(self, task_id: str, callback: Callable[[ProgressStatus], None]):
        """
        Register a callback for progress updates
        
        Args:
            task_id: The task ID to monitor
            callback: Function to call with progress updates
        """
        with self._lock:
            if task_id not in self._progress_callbacks:
                self._progress_callbacks[task_id] = []
            self._progress_callbacks[task_id].append(callback)
            
        logger.debug(f"Registered progress callback for task {sanitize_for_log(task_id)}")
    
    def unregister_callback(self, task_id: str, callback: Callable[[ProgressStatus], None]):
        """
        Unregister a callback for progress updates
        
        Args:
            task_id: The task ID to stop monitoring
            callback: The callback function to remove
        """
        with self._lock:
            if task_id in self._progress_callbacks:
                try:
                    self._progress_callbacks[task_id].remove(callback)
                    if not self._progress_callbacks[task_id]:
                        del self._progress_callbacks[task_id]
                except ValueError:
                    pass  # Callback not found
                    
        logger.debug(f"Unregistered progress callback for task {sanitize_for_log(task_id)}")
    
    def cleanup_callbacks(self, task_id: str):
        """
        Clean up all callbacks for a task
        
        Args:
            task_id: The task ID to clean up
        """
        with self._lock:
            if task_id in self._progress_callbacks:
                del self._progress_callbacks[task_id]
                
        logger.debug(f"Cleaned up callbacks for task {sanitize_for_log(task_id)}")
    
    def _notify_callbacks(self, task_id: str, progress_status: ProgressStatus):
        """
        Notify all registered callbacks for a task
        
        Args:
            task_id: The task ID
            progress_status: The progress status to send
        """
        with self._lock:
            callbacks = self._progress_callbacks.get(task_id, [])
        
        # Call callbacks outside of lock to avoid deadlocks
        for callback in callbacks:
            try:
                callback(progress_status)
            except Exception as e:
                logger.error(f"Error in progress callback for task {sanitize_for_log(task_id)}: {sanitize_for_log(str(e))}")
    
    def get_active_progress_sessions(self) -> Dict[str, ProgressStatus]:
        """
        Get all active progress sessions
        
        Returns:
            Dict mapping task_id to ProgressStatus for active tasks
        """
        session = self.db_manager.get_session()
        try:
            # Get all active tasks
            active_tasks = session.query(CaptionGenerationTask).filter(
                CaptionGenerationTask.status.in_([TaskStatus.QUEUED, TaskStatus.RUNNING])
            ).all()
            
            progress_sessions = {}
            
            for task in active_tasks:
                progress_status = ProgressStatus(
                    task_id=task.id,
                    user_id=task.user_id,
                    current_step=task.current_step or "Initializing",
                    progress_percent=task.progress_percent or 0,
                    details={
                        'status': task.status.value,
                        'created_at': task.created_at.isoformat() if task.created_at else None
                    },
                    started_at=task.started_at,
                    updated_at=datetime.now(timezone.utc)
                )
                
                progress_sessions[task.id] = progress_status
            
            return progress_sessions
            
        except SQLAlchemyError as e:
            logger.error(f"Database error getting active progress sessions: {sanitize_for_log(str(e))}")
            return {}
        finally:
            session.close()
    
    def create_progress_callback(self, task_id: str) -> Callable[[str, int, Dict[str, Any]], None]:
        """
        Create a progress callback function for use with caption generation
        
        Args:
            task_id: The task ID to update
            
        Returns:
            Callable that can be used as a progress callback
        """
        def progress_callback(step: str, percent: int, details: Dict[str, Any] = None):
            """Progress callback function"""
            self.update_progress(task_id, step, percent, details or {})
        
        return progress_callback
    
    def send_caption_status_notification(self, user_id: int, task_id: str, status: str, message: str = None):
        """
        Send caption generation status notification
        
        Args:
            user_id: User ID to send notification to
            task_id: Task ID
            status: Status (running, paused, resumed)
            message: Optional status message
        """
        try:
            from unified_notification_manager import UnifiedNotificationManager, NotificationMessage
            from models import NotificationType, NotificationPriority, NotificationCategory
            from flask import current_app
            
            if hasattr(current_app, 'notification_manager'):
                notification_manager = current_app.notification_manager
                
                # Determine notification type based on status
                notification_type = NotificationType.INFO
                if status == 'paused':
                    notification_type = NotificationType.WARNING
                elif status == 'resumed':
                    notification_type = NotificationType.SUCCESS
                
                notification = NotificationMessage(
                    id=f"caption_status_{task_id}_{status}",
                    type=notification_type,
                    title="Caption Generation Status",
                    message=message or f"Caption generation {status}",
                    user_id=user_id,
                    priority=NotificationPriority.NORMAL,
                    category=NotificationCategory.CAPTION,
                    data={
                        'task_id': task_id,
                        'status': status,
                        'notification_type': 'caption_status',
                        'auto_hide': True,
                        'category': 'caption'
                    }
                )
                
                notification_manager.send_user_notification(user_id, notification)
                logger.debug(f"Sent status notification for task {sanitize_for_log(task_id)}: {status}")
                
        except Exception as e:
            logger.error(f"Error sending status notification: {sanitize_for_log(str(e))}")
    
    def send_caption_error_notification(self, user_id: int, task_id: str, error_message: str, 
                                      error_category: str = None, recovery_suggestions: List[str] = None):
        """
        Send caption generation error notification with retry options
        
        Args:
            user_id: User ID to send notification to
            task_id: Task ID
            error_message: Error message
            error_category: Optional error category
            recovery_suggestions: Optional recovery suggestions
        """
        try:
            from unified_notification_manager import UnifiedNotificationManager, NotificationMessage
            from models import NotificationType, NotificationPriority, NotificationCategory
            from flask import current_app
            
            if hasattr(current_app, 'notification_manager'):
                notification_manager = current_app.notification_manager
                
                notification = NotificationMessage(
                    id=f"caption_error_{task_id}",
                    type=NotificationType.ERROR,
                    title="Caption Generation Failed",
                    message=error_message,
                    user_id=user_id,
                    priority=NotificationPriority.HIGH,
                    category=NotificationCategory.CAPTION,
                    requires_action=True,
                    action_url=f"/api/caption_generation/retry/{task_id}",
                    action_text="Retry Task",
                    data={
                        'task_id': task_id,
                        'error_message': error_message,
                        'error_category': error_category or 'unknown',
                        'recovery_suggestions': recovery_suggestions or [],
                        'notification_type': 'caption_error',
                        'persistent': True,
                        'auto_hide': False,
                        'category': 'caption',
                        'actions': [
                            {
                                'text': 'Retry Task',
                                'url': f'/api/caption_generation/retry/{task_id}',
                                'method': 'POST',
                                'primary': True
                            },
                            {
                                'text': 'View Details',
                                'url': f'/api/caption_generation/error_details/{task_id}',
                                'primary': False
                            }
                        ]
                    }
                )
                
                notification_manager.send_user_notification(user_id, notification)
                logger.error(f"Sent error notification for task {sanitize_for_log(task_id)}: {sanitize_for_log(error_message)}")
                
        except Exception as e:
            logger.error(f"Error sending error notification: {sanitize_for_log(str(e))}")
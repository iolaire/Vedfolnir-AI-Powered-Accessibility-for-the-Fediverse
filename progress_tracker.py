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
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass, asdict
from sqlalchemy.exc import SQLAlchemyError

from database import DatabaseManager
from models import CaptionGenerationTask, TaskStatus, GenerationResults
from security_utils import sanitize_for_log

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
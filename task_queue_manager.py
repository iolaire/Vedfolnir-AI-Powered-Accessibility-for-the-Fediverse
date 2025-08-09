# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Task Queue Manager for Caption Generation

This module manages the queuing and execution of caption generation tasks,
ensuring single-task-per-user enforcement and proper resource management.
"""

import logging
import threading
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from database import DatabaseManager
from models import CaptionGenerationTask, TaskStatus, User, UserRole, PlatformConnection
from security_utils import sanitize_for_log

logger = logging.getLogger(__name__)

class TaskQueueManager:
    """Manages caption generation task queue with single-task-per-user enforcement"""
    
    def __init__(self, db_manager: DatabaseManager, max_concurrent_tasks: int = 3):
        self.db_manager = db_manager
        self.max_concurrent_tasks = max_concurrent_tasks
        self._lock = threading.Lock()
        
    def enqueue_task(self, task: CaptionGenerationTask) -> str:
        """
        Enqueue a caption generation task
        
        Args:
            task: The CaptionGenerationTask to enqueue
            
        Returns:
            str: The task ID if successful
            
        Raises:
            ValueError: If user already has an active task
            SQLAlchemyError: If database operation fails
        """
        with self._lock:
            session = self.db_manager.get_session()
            try:
                # Generate secure task ID if not already set
                if not task.id:
                    from caption_security import CaptionSecurityManager
                    security_manager = CaptionSecurityManager(self.db_manager)
                    task.id = security_manager.generate_secure_task_id()
                
                # Check if user already has an active task
                existing_task = session.query(CaptionGenerationTask).filter_by(
                    user_id=task.user_id
                ).filter(
                    CaptionGenerationTask.status.in_([TaskStatus.QUEUED, TaskStatus.RUNNING])
                ).first()
                
                if existing_task:
                    raise ValueError(f"User {task.user_id} already has an active task: {existing_task.id}")
                
                # Add the task to the database
                session.add(task)
                session.commit()
                
                logger.info(f"Enqueued task {sanitize_for_log(task.id)} for user {sanitize_for_log(str(task.user_id))}")
                return task.id
                
            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"Database error enqueueing task: {sanitize_for_log(str(e))}")
                raise
            finally:
                session.close()
    
    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """
        Get the status of a task
        
        Args:
            task_id: The task ID to check
            
        Returns:
            TaskStatus or None if task not found
        """
        session = self.db_manager.get_session()
        try:
            task = session.query(CaptionGenerationTask).filter_by(id=task_id).first()
            return task.status if task else None
        except SQLAlchemyError as e:
            logger.error(f"Database error getting task status: {sanitize_for_log(str(e))}")
            return None
        finally:
            session.close()
    
    def get_task(self, task_id: str) -> Optional[CaptionGenerationTask]:
        """
        Get a task by ID
        
        Args:
            task_id: The task ID to retrieve
            
        Returns:
            CaptionGenerationTask or None if not found
        """
        session = self.db_manager.get_session()
        try:
            task = session.query(CaptionGenerationTask).filter_by(id=task_id).first()
            if task:
                # Detach from session to avoid issues
                session.expunge(task)
            return task
        except SQLAlchemyError as e:
            logger.error(f"Database error getting task: {sanitize_for_log(str(e))}")
            return None
        finally:
            session.close()
    
    def cancel_task(self, task_id: str, user_id: int = None) -> bool:
        """
        Cancel a task
        
        Args:
            task_id: The task ID to cancel
            user_id: Optional user ID for authorization check
            
        Returns:
            bool: True if task was cancelled, False otherwise
        """
        with self._lock:
            session = self.db_manager.get_session()
            try:
                task = session.query(CaptionGenerationTask).filter_by(id=task_id).first()
                
                if not task:
                    logger.warning(f"Task {sanitize_for_log(task_id)} not found for cancellation")
                    return False
                
                # Authorization check if user_id provided
                if user_id is not None and task.user_id != user_id:
                    logger.warning(f"User {sanitize_for_log(str(user_id))} attempted to cancel task {sanitize_for_log(task_id)} owned by user {sanitize_for_log(str(task.user_id))}")
                    return False
                
                # Check if task can be cancelled
                if not task.can_be_cancelled():
                    logger.warning(f"Task {sanitize_for_log(task_id)} cannot be cancelled (status: {task.status.value})")
                    return False
                
                # Cancel the task
                task.status = TaskStatus.CANCELLED
                task.completed_at = datetime.now(timezone.utc)
                session.commit()
                
                logger.info(f"Cancelled task {sanitize_for_log(task_id)}")
                return True
                
            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"Database error cancelling task: {sanitize_for_log(str(e))}")
                return False
            finally:
                session.close()
    
    def get_next_task(self) -> Optional[CaptionGenerationTask]:
        """
        Get the next task to execute, considering priority
        
        Returns:
            CaptionGenerationTask or None if no tasks available
        """
        with self._lock:
            session = self.db_manager.get_session()
            try:
                # Check if we're at max concurrent tasks
                running_count = session.query(CaptionGenerationTask).filter_by(
                    status=TaskStatus.RUNNING
                ).count()
                
                if running_count >= self.max_concurrent_tasks:
                    return None
                
                # Get queued tasks with priority (admin users first)
                queued_tasks = session.query(CaptionGenerationTask).join(User).filter(
                    CaptionGenerationTask.status == TaskStatus.QUEUED
                ).order_by(
                    # Admin users get priority
                    User.role == UserRole.ADMIN.value,
                    # Then by creation time (FIFO)
                    CaptionGenerationTask.created_at
                ).first()
                
                if queued_tasks:
                    # Mark as running
                    queued_tasks.status = TaskStatus.RUNNING
                    queued_tasks.started_at = datetime.now(timezone.utc)
                    session.commit()
                    
                    # Create a detached copy to avoid session issues
                    task_copy = CaptionGenerationTask(
                        id=queued_tasks.id,
                        user_id=queued_tasks.user_id,
                        platform_connection_id=queued_tasks.platform_connection_id,
                        status=queued_tasks.status,
                        created_at=queued_tasks.created_at,
                        started_at=queued_tasks.started_at
                    )
                    task_copy.settings = queued_tasks.settings
                    
                    logger.info(f"Retrieved next task {sanitize_for_log(queued_tasks.id)} for execution")
                    return task_copy
                
                return None
                
            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"Database error getting next task: {sanitize_for_log(str(e))}")
                return None
            finally:
                session.close()
    
    def complete_task(self, task_id: str, success: bool, error_message: str = None) -> bool:
        """
        Mark a task as completed
        
        Args:
            task_id: The task ID to complete
            success: Whether the task completed successfully
            error_message: Optional error message if task failed
            
        Returns:
            bool: True if task was marked as completed
        """
        session = self.db_manager.get_session()
        try:
            task = session.query(CaptionGenerationTask).filter_by(id=task_id).first()
            
            if not task:
                logger.warning(f"Task {sanitize_for_log(task_id)} not found for completion")
                return False
            
            # Update task status
            task.status = TaskStatus.COMPLETED if success else TaskStatus.FAILED
            task.completed_at = datetime.now(timezone.utc)
            if error_message:
                task.error_message = error_message
            
            session.commit()
            
            status_str = "completed" if success else "failed"
            logger.info(f"Marked task {sanitize_for_log(task_id)} as {status_str}")
            return True
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error completing task: {sanitize_for_log(str(e))}")
            return False
        finally:
            session.close()
    
    def cleanup_completed_tasks(self, older_than_hours: int = 24) -> int:
        """
        Clean up completed tasks older than specified hours
        
        Args:
            older_than_hours: Remove tasks completed more than this many hours ago
            
        Returns:
            int: Number of tasks cleaned up
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=older_than_hours)
        
        session = self.db_manager.get_session()
        try:
            # Find completed tasks older than cutoff
            old_tasks = session.query(CaptionGenerationTask).filter(
                CaptionGenerationTask.status.in_([
                    TaskStatus.COMPLETED, 
                    TaskStatus.FAILED, 
                    TaskStatus.CANCELLED
                ]),
                CaptionGenerationTask.completed_at < cutoff_time
            ).all()
            
            count = len(old_tasks)
            
            if count > 0:
                # Delete the tasks
                for task in old_tasks:
                    session.delete(task)
                
                session.commit()
                logger.info(f"Cleaned up {count} completed tasks older than {older_than_hours} hours")
            
            return count
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error cleaning up tasks: {sanitize_for_log(str(e))}")
            return 0
        finally:
            session.close()
    
    def get_user_active_task(self, user_id: int) -> Optional[CaptionGenerationTask]:
        """
        Get the active task for a user
        
        Args:
            user_id: The user ID to check
            
        Returns:
            CaptionGenerationTask or None if no active task
        """
        session = self.db_manager.get_session()
        try:
            task = session.query(CaptionGenerationTask).filter_by(
                user_id=user_id
            ).filter(
                CaptionGenerationTask.status.in_([TaskStatus.QUEUED, TaskStatus.RUNNING])
            ).first()
            
            if task:
                session.expunge(task)
            
            return task
            
        except SQLAlchemyError as e:
            logger.error(f"Database error getting user active task: {sanitize_for_log(str(e))}")
            return None
        finally:
            session.close()
    
    def get_queue_stats(self) -> Dict[str, int]:
        """
        Get statistics about the task queue
        
        Returns:
            Dict with queue statistics
        """
        session = self.db_manager.get_session()
        try:
            stats = {}
            
            # Count tasks by status
            for status in TaskStatus:
                count = session.query(CaptionGenerationTask).filter_by(status=status).count()
                stats[status.value] = count
            
            # Total tasks
            stats['total'] = sum(stats.values())
            
            # Active tasks
            stats['active'] = stats.get('queued', 0) + stats.get('running', 0)
            
            return stats
            
        except SQLAlchemyError as e:
            logger.error(f"Database error getting queue stats: {sanitize_for_log(str(e))}")
            return {}
        finally:
            session.close()
    
    def get_user_task_history(self, user_id: int, limit: int = 10) -> List[CaptionGenerationTask]:
        """
        Get task history for a user
        
        Args:
            user_id: The user ID
            limit: Maximum number of tasks to return
            
        Returns:
            List of CaptionGenerationTask objects
        """
        session = self.db_manager.get_session()
        try:
            tasks = session.query(CaptionGenerationTask).filter_by(
                user_id=user_id
            ).order_by(
                CaptionGenerationTask.created_at.desc()
            ).limit(limit).all()
            
            # Detach from session
            for task in tasks:
                session.expunge(task)
            
            return tasks
            
        except SQLAlchemyError as e:
            logger.error(f"Database error getting user task history: {sanitize_for_log(str(e))}")
            return []
        finally:
            session.close()
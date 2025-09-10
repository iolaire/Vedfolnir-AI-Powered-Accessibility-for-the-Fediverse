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
from sqlalchemy import and_, or_

from app.core.database.core.database_manager import DatabaseManager
from models import CaptionGenerationTask, TaskStatus, User, UserRole, PlatformConnection, JobPriority
from app.core.security.core.security_utils import sanitize_for_log

logger = logging.getLogger(__name__)

class TaskQueueManager:
    """Manages caption generation task queue with single-task-per-user enforcement"""
    
    def __init__(self, db_manager: DatabaseManager, max_concurrent_tasks: int = 3):
        self.db_manager = db_manager
        self.max_concurrent_tasks = max_concurrent_tasks
        self._lock = threading.Lock()
        
    def enqueue_task(self, task: CaptionGenerationTask, priority_override: Optional[JobPriority] = None) -> str:
        """
        Enqueue a caption generation task
        
        Args:
            task: The CaptionGenerationTask to enqueue
            priority_override: Optional priority override for admin use
            
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
                    from app.core.security.features.caption_security import CaptionSecurityManager
                    security_manager = CaptionSecurityManager(self.db_manager)
                    task.id = security_manager.generate_secure_task_id()
                
                # Apply priority override if provided
                if priority_override:
                    task.priority = priority_override
                elif not task.priority:
                    task.priority = JobPriority.NORMAL
                
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
    
    def cancel_task(self, task_id: str, user_id: int = None, admin_user_id: int = None, reason: str = None) -> bool:
        """
        Cancel a task
        
        Args:
            task_id: The task ID to cancel
            user_id: Optional user ID for authorization check
            admin_user_id: Optional admin user ID for admin cancellation
            reason: Optional reason for cancellation
            
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
                
                # Authorization check
                if admin_user_id is not None:
                    # Admin cancellation - verify admin role
                    admin_user = session.query(User).filter_by(id=admin_user_id).first()
                    if not admin_user or admin_user.role != UserRole.ADMIN:
                        logger.warning(f"User {sanitize_for_log(str(admin_user_id))} attempted admin cancellation without admin role")
                        return False
                elif user_id is not None and task.user_id != user_id:
                    # Regular user cancellation - check ownership
                    logger.warning(f"User {sanitize_for_log(str(user_id))} attempted to cancel task {sanitize_for_log(task_id)} owned by user {sanitize_for_log(str(task.user_id))}")
                    return False
                
                # Check if task can be cancelled
                if not task.can_be_cancelled():
                    logger.warning(f"Task {sanitize_for_log(task_id)} cannot be cancelled (status: {task.status.value})")
                    return False
                
                # Cancel the task
                task.status = TaskStatus.CANCELLED
                task.completed_at = datetime.now(timezone.utc)
                
                # Track admin cancellation if applicable
                if admin_user_id is not None:
                    task.cancelled_by_admin = True
                    task.admin_user_id = admin_user_id
                    task.cancellation_reason = reason or "Cancelled by administrator"
                
                session.commit()
                
                if admin_user_id:
                    logger.info(f"Admin {sanitize_for_log(str(admin_user_id))} cancelled task {sanitize_for_log(task_id)}")
                else:
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
                
                # Get queued tasks with priority ordering
                queued_tasks = session.query(CaptionGenerationTask).join(User).filter(
                    CaptionGenerationTask.status == TaskStatus.QUEUED
                ).order_by(
                    # Priority order: URGENT, HIGH, NORMAL, LOW
                    CaptionGenerationTask.priority == JobPriority.URGENT.value,
                    CaptionGenerationTask.priority == JobPriority.HIGH.value,
                    CaptionGenerationTask.priority == JobPriority.NORMAL.value,
                    # Admin users get priority within same priority level
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
    
    # Admin Control Methods
    
    def get_all_tasks(self, admin_user_id: int, status_filter: Optional[List[TaskStatus]] = None, 
                     limit: int = 100) -> List[CaptionGenerationTask]:
        """
        Get all tasks across all users for admin visibility
        
        Args:
            admin_user_id: The admin user ID (for authorization)
            status_filter: Optional list of statuses to filter by
            limit: Maximum number of tasks to return
            
        Returns:
            List of CaptionGenerationTask objects
            
        Raises:
            ValueError: If user is not an admin
        """
        session = self.db_manager.get_session()
        try:
            # Verify admin authorization
            admin_user = session.query(User).filter_by(id=admin_user_id).first()
            if not admin_user or admin_user.role != UserRole.ADMIN:
                raise ValueError(f"User {admin_user_id} is not authorized for admin operations")
            
            # Build query with explicit join condition
            query = session.query(CaptionGenerationTask).join(
                User, CaptionGenerationTask.user_id == User.id
            )
            
            if status_filter:
                query = query.filter(CaptionGenerationTask.status.in_(status_filter))
            
            # Order by priority (urgent first), then by creation time
            tasks = query.order_by(
                CaptionGenerationTask.priority == JobPriority.URGENT.value,
                CaptionGenerationTask.priority == JobPriority.HIGH.value,
                CaptionGenerationTask.priority == JobPriority.NORMAL.value,
                CaptionGenerationTask.created_at.desc()
            ).limit(limit).all()
            
            # Detach from session
            for task in tasks:
                session.expunge(task)
            
            logger.info(f"Admin {sanitize_for_log(str(admin_user_id))} retrieved {len(tasks)} tasks")
            return tasks
            
        except SQLAlchemyError as e:
            logger.error(f"Database error getting all tasks: {sanitize_for_log(str(e))}")
            return []
        finally:
            session.close()
    
    def cancel_task_as_admin(self, task_id: str, admin_user_id: int, reason: str) -> bool:
        """
        Cancel a task as an administrator with reason tracking
        
        Args:
            task_id: The task ID to cancel
            admin_user_id: The admin user ID performing the cancellation
            reason: Reason for cancellation
            
        Returns:
            bool: True if task was cancelled, False otherwise
            
        Raises:
            ValueError: If user is not an admin
        """
        with self._lock:
            session = self.db_manager.get_session()
            try:
                # Verify admin authorization
                admin_user = session.query(User).filter_by(id=admin_user_id).first()
                if not admin_user or admin_user.role != UserRole.ADMIN:
                    raise ValueError(f"User {admin_user_id} is not authorized for admin operations")
                
                task = session.query(CaptionGenerationTask).filter_by(id=task_id).first()
                
                if not task:
                    logger.warning(f"Task {sanitize_for_log(task_id)} not found for admin cancellation")
                    return False
                
                # Check if task can be cancelled
                if not task.can_be_cancelled():
                    logger.warning(f"Task {sanitize_for_log(task_id)} cannot be cancelled (status: {task.status.value})")
                    return False
                
                # Cancel the task with admin tracking
                task.status = TaskStatus.CANCELLED
                task.completed_at = datetime.now(timezone.utc)
                task.cancelled_by_admin = True
                task.admin_user_id = admin_user_id
                task.cancellation_reason = reason
                
                session.commit()
                
                logger.info(f"Admin {sanitize_for_log(str(admin_user_id))} cancelled task {sanitize_for_log(task_id)} - Reason: {sanitize_for_log(reason)}")
                
                # TODO: Send notification to user about admin cancellation
                # This would be implemented in a notification service
                
                return True
                
            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"Database error in admin task cancellation: {sanitize_for_log(str(e))}")
                return False
            finally:
                session.close()
    
    def pause_user_jobs(self, admin_user_id: int, target_user_id: int) -> int:
        """
        Pause all active jobs for a specific user
        
        Args:
            admin_user_id: The admin user ID performing the action
            target_user_id: The user whose jobs should be paused
            
        Returns:
            int: Number of jobs paused
            
        Raises:
            ValueError: If user is not an admin
        """
        with self._lock:
            session = self.db_manager.get_session()
            try:
                # Verify admin authorization
                admin_user = session.query(User).filter_by(id=admin_user_id).first()
                if not admin_user or admin_user.role != UserRole.ADMIN:
                    raise ValueError(f"User {admin_user_id} is not authorized for admin operations")
                
                # Find active tasks for the user
                active_tasks = session.query(CaptionGenerationTask).filter(
                    and_(
                        CaptionGenerationTask.user_id == target_user_id,
                        CaptionGenerationTask.status.in_([TaskStatus.QUEUED, TaskStatus.RUNNING])
                    )
                ).all()
                
                paused_count = 0
                for task in active_tasks:
                    if task.status == TaskStatus.QUEUED:
                        # Cancel queued tasks
                        task.status = TaskStatus.CANCELLED
                        task.completed_at = datetime.now(timezone.utc)
                        task.cancelled_by_admin = True
                        task.admin_user_id = admin_user_id
                        task.cancellation_reason = f"User jobs paused by admin"
                        paused_count += 1
                    elif task.status == TaskStatus.RUNNING:
                        # Mark running tasks for cancellation (they'll be handled by the worker)
                        task.admin_notes = f"Marked for cancellation by admin {admin_user_id}"
                        paused_count += 1
                
                session.commit()
                
                logger.info(f"Admin {sanitize_for_log(str(admin_user_id))} paused {paused_count} jobs for user {sanitize_for_log(str(target_user_id))}")
                return paused_count
                
            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"Database error pausing user jobs: {sanitize_for_log(str(e))}")
                return 0
            finally:
                session.close()
    
    def resume_user_jobs(self, admin_user_id: int, target_user_id: int) -> bool:
        """
        Resume jobs for a specific user (remove pause restrictions)
        
        Args:
            admin_user_id: The admin user ID performing the action
            target_user_id: The user whose jobs should be resumed
            
        Returns:
            bool: True if resume was successful
            
        Raises:
            ValueError: If user is not an admin
        """
        session = self.db_manager.get_session()
        try:
            # Verify admin authorization
            admin_user = session.query(User).filter_by(id=admin_user_id).first()
            if not admin_user or admin_user.role != UserRole.ADMIN:
                raise ValueError(f"User {admin_user_id} is not authorized for admin operations")
            
            # Clear admin notes that indicate paused status
            # In a more complex implementation, this might involve a separate user_status table
            # For now, we'll clear admin notes that indicate pause status
            tasks_with_pause_notes = session.query(CaptionGenerationTask).filter(
                and_(
                    CaptionGenerationTask.user_id == target_user_id,
                    CaptionGenerationTask.admin_notes.like('%Marked for cancellation by admin%')
                )
            ).all()
            
            for task in tasks_with_pause_notes:
                task.admin_notes = None
            
            session.commit()
            
            logger.info(f"Admin {sanitize_for_log(str(admin_user_id))} resumed jobs for user {sanitize_for_log(str(target_user_id))}")
            return True
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error resuming user jobs: {sanitize_for_log(str(e))}")
            return False
        finally:
            session.close()
    
    def clear_stuck_tasks(self, admin_user_id: int, stuck_threshold_minutes: int = 60) -> int:
        """
        Clear tasks that have been running for too long (stuck tasks)
        
        Args:
            admin_user_id: The admin user ID performing the action
            stuck_threshold_minutes: Tasks running longer than this are considered stuck
            
        Returns:
            int: Number of stuck tasks cleared
            
        Raises:
            ValueError: If user is not an admin
        """
        with self._lock:
            session = self.db_manager.get_session()
            try:
                # Verify admin authorization
                admin_user = session.query(User).filter_by(id=admin_user_id).first()
                if not admin_user or admin_user.role != UserRole.ADMIN:
                    raise ValueError(f"User {admin_user_id} is not authorized for admin operations")
                
                # Calculate cutoff time for stuck tasks
                cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=stuck_threshold_minutes)
                
                # Find stuck tasks (running for too long)
                stuck_tasks = session.query(CaptionGenerationTask).filter(
                    and_(
                        CaptionGenerationTask.status == TaskStatus.RUNNING,
                        CaptionGenerationTask.started_at < cutoff_time
                    )
                ).all()
                
                cleared_count = 0
                for task in stuck_tasks:
                    task.status = TaskStatus.FAILED
                    task.completed_at = datetime.now(timezone.utc)
                    task.error_message = f"Task cleared as stuck by admin (running for >{stuck_threshold_minutes} minutes)"
                    task.cancelled_by_admin = True
                    task.admin_user_id = admin_user_id
                    task.cancellation_reason = "Stuck task cleanup"
                    cleared_count += 1
                
                session.commit()
                
                logger.info(f"Admin {sanitize_for_log(str(admin_user_id))} cleared {cleared_count} stuck tasks")
                return cleared_count
                
            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"Database error clearing stuck tasks: {sanitize_for_log(str(e))}")
                return 0
            finally:
                session.close()
    
    def set_task_priority(self, task_id: str, admin_user_id: int, priority: JobPriority) -> bool:
        """
        Set the priority of a task (admin override)
        
        Args:
            task_id: The task ID to modify
            admin_user_id: The admin user ID performing the action
            priority: The new priority level
            
        Returns:
            bool: True if priority was set successfully
            
        Raises:
            ValueError: If user is not an admin
        """
        session = self.db_manager.get_session()
        try:
            # Verify admin authorization
            admin_user = session.query(User).filter_by(id=admin_user_id).first()
            if not admin_user or admin_user.role != UserRole.ADMIN:
                raise ValueError(f"User {admin_user_id} is not authorized for admin operations")
            
            task = session.query(CaptionGenerationTask).filter_by(id=task_id).first()
            
            if not task:
                logger.warning(f"Task {sanitize_for_log(task_id)} not found for priority update")
                return False
            
            old_priority = task.priority
            task.priority = priority
            
            # Add admin note about priority change
            priority_note = f"Priority changed from {old_priority.value if old_priority else 'None'} to {priority.value} by admin {admin_user_id}"
            if task.admin_notes:
                task.admin_notes += f"\n{priority_note}"
            else:
                task.admin_notes = priority_note
            
            session.commit()
            
            logger.info(f"Admin {sanitize_for_log(str(admin_user_id))} set priority of task {sanitize_for_log(task_id)} to {priority.value}")
            return True
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error setting task priority: {sanitize_for_log(str(e))}")
            return False
        finally:
            session.close()
    
    def requeue_failed_task(self, task_id: str, admin_user_id: int) -> Optional[str]:
        """
        Requeue a failed task for retry (admin job recovery)
        
        Args:
            task_id: The failed task ID to requeue
            admin_user_id: The admin user ID performing the action
            
        Returns:
            str: New task ID if successful, None otherwise
            
        Raises:
            ValueError: If user is not an admin
        """
        with self._lock:
            session = self.db_manager.get_session()
            try:
                # Verify admin authorization
                admin_user = session.query(User).filter_by(id=admin_user_id).first()
                if not admin_user or admin_user.role != UserRole.ADMIN:
                    raise ValueError(f"User {admin_user_id} is not authorized for admin operations")
                
                original_task = session.query(CaptionGenerationTask).filter_by(id=task_id).first()
                
                if not original_task:
                    logger.warning(f"Task {sanitize_for_log(task_id)} not found for requeue")
                    return None
                
                if original_task.status not in [TaskStatus.FAILED, TaskStatus.CANCELLED]:
                    logger.warning(f"Task {sanitize_for_log(task_id)} cannot be requeued (status: {original_task.status.value})")
                    return None
                
                # Check if user already has an active task
                existing_active = session.query(CaptionGenerationTask).filter(
                    and_(
                        CaptionGenerationTask.user_id == original_task.user_id,
                        CaptionGenerationTask.status.in_([TaskStatus.QUEUED, TaskStatus.RUNNING])
                    )
                ).first()
                
                if existing_active:
                    logger.warning(f"Cannot requeue task for user {original_task.user_id} - active task exists: {existing_active.id}")
                    return None
                
                # Create new task based on the failed one
                new_task = CaptionGenerationTask(
                    user_id=original_task.user_id,
                    platform_connection_id=original_task.platform_connection_id,
                    status=TaskStatus.QUEUED,
                    settings_json=original_task.settings_json,
                    priority=original_task.priority or JobPriority.NORMAL,
                    retry_count=original_task.retry_count + 1,
                    max_retries=original_task.max_retries,
                    admin_notes=f"Requeued by admin {admin_user_id} from failed task {task_id}"
                )
                
                # Generate secure task ID
                from app.core.security.features.caption_security import CaptionSecurityManager
                security_manager = CaptionSecurityManager(self.db_manager)
                new_task.id = security_manager.generate_secure_task_id()
                
                session.add(new_task)
                session.commit()
                
                logger.info(f"Admin {sanitize_for_log(str(admin_user_id))} requeued failed task {sanitize_for_log(task_id)} as {sanitize_for_log(new_task.id)}")
                return new_task.id
                
            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"Database error requeuing failed task: {sanitize_for_log(str(e))}")
                return None
            finally:
                session.close()
    
    def get_queue_statistics(self, admin_user_id: int) -> Dict[str, Any]:
        """
        Get detailed queue statistics for admin dashboard
        
        Args:
            admin_user_id: The admin user ID requesting statistics
            
        Returns:
            Dict with detailed queue statistics
            
        Raises:
            ValueError: If user is not an admin
        """
        session = self.db_manager.get_session()
        try:
            # Verify admin authorization
            admin_user = session.query(User).filter_by(id=admin_user_id).first()
            if not admin_user or admin_user.role != UserRole.ADMIN:
                raise ValueError(f"User {admin_user_id} is not authorized for admin operations")
            
            stats = {}
            
            # Basic status counts
            for status in TaskStatus:
                count = session.query(CaptionGenerationTask).filter_by(status=status).count()
                stats[f'{status.value}_count'] = count
            
            # Priority breakdown for queued tasks
            priority_stats = {}
            for priority in JobPriority:
                count = session.query(CaptionGenerationTask).filter(
                    and_(
                        CaptionGenerationTask.status == TaskStatus.QUEUED,
                        CaptionGenerationTask.priority == priority
                    )
                ).count()
                priority_stats[priority.value] = count
            stats['priority_breakdown'] = priority_stats
            
            # Admin intervention statistics
            admin_cancelled_count = session.query(CaptionGenerationTask).filter_by(
                cancelled_by_admin=True
            ).count()
            stats['admin_cancelled_count'] = admin_cancelled_count
            
            # Retry statistics
            retry_stats = session.query(CaptionGenerationTask).filter(
                CaptionGenerationTask.retry_count > 0
            ).count()
            stats['retried_tasks_count'] = retry_stats
            
            # Average wait time for queued tasks
            queued_tasks = session.query(CaptionGenerationTask).filter_by(
                status=TaskStatus.QUEUED
            ).all()
            
            if queued_tasks:
                now = datetime.now(timezone.utc)
                wait_times = [(now - task.created_at).total_seconds() for task in queued_tasks]
                stats['average_wait_time_seconds'] = sum(wait_times) / len(wait_times)
                stats['max_wait_time_seconds'] = max(wait_times)
            else:
                stats['average_wait_time_seconds'] = 0
                stats['max_wait_time_seconds'] = 0
            
            # Total and active counts
            stats['total_tasks'] = sum(stats[f'{status.value}_count'] for status in TaskStatus)
            stats['active_tasks'] = stats['queued_count'] + stats['running_count']
            
            return stats
            
        except SQLAlchemyError as e:
            logger.error(f"Database error getting queue statistics: {sanitize_for_log(str(e))}")
            return {}
        finally:
            session.close()
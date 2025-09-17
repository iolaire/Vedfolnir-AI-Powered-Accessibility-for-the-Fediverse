# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
RQ Progress Tracker

Integrates RQ task progress with existing WebSocket system for real-time updates.
Provides progress tracking that works both in RQ worker threads and web application context.
"""

import logging
import threading
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass
import redis
from rq import get_current_job

from app.core.database.core.database_manager import DatabaseManager
from app.core.security.core.security_utils import sanitize_for_log
from models import CaptionGenerationTask, TaskStatus
from app.services.monitoring.progress.progress_tracker import ProgressTracker, ProgressStatus

logger = logging.getLogger(__name__)


@dataclass
class RQProgressData:
    """RQ-specific progress data structure"""
    task_id: str
    job_id: str
    worker_id: str
    user_id: int
    current_step: str
    progress_percent: int
    details: Dict[str, Any]
    started_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Redis storage"""
        data = {
            'task_id': self.task_id,
            'job_id': self.job_id,
            'worker_id': self.worker_id,
            'user_id': self.user_id,
            'current_step': self.current_step,
            'progress_percent': self.progress_percent,
            'details': self.details
        }
        
        if self.started_at:
            data['started_at'] = self.started_at.isoformat()
        if self.updated_at:
            data['updated_at'] = self.updated_at.isoformat()
            
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RQProgressData':
        """Create from dictionary loaded from Redis"""
        started_at = None
        updated_at = None
        
        if data.get('started_at'):
            started_at = datetime.fromisoformat(data['started_at'])
        if data.get('updated_at'):
            updated_at = datetime.fromisoformat(data['updated_at'])
        
        return cls(
            task_id=data['task_id'],
            job_id=data['job_id'],
            worker_id=data['worker_id'],
            user_id=data['user_id'],
            current_step=data['current_step'],
            progress_percent=data['progress_percent'],
            details=data.get('details', {}),
            started_at=started_at,
            updated_at=updated_at
        )


class RQProgressTracker:
    """RQ-specific progress tracker with WebSocket integration"""
    
    def __init__(self, db_manager: DatabaseManager, redis_connection: redis.Redis):
        """
        Initialize RQ Progress Tracker
        
        Args:
            db_manager: Database manager instance
            redis_connection: Redis connection for progress storage
        """
        self.db_manager = db_manager
        self.redis_connection = redis_connection
        self.progress_tracker = ProgressTracker(db_manager)
        
        # Redis keys
        self.progress_key_prefix = "rq:progress:"
        self.progress_ttl = 7200  # 2 hours
        
        # Thread-local storage for worker context
        self._local = threading.local()
    
    def create_progress_callback(self, task_id: str) -> Callable:
        """
        Create a progress callback function for RQ tasks
        
        Args:
            task_id: The task ID to track progress for
            
        Returns:
            Callable progress callback function
        """
        def progress_callback(current_step: str, progress_percent: int, 
                            details: Dict[str, Any] = None) -> None:
            """
            Progress callback function for RQ tasks
            
            Args:
                current_step: Description of current processing step
                progress_percent: Progress percentage (0-100)
                details: Optional additional details
            """
            try:
                self.update_rq_progress(task_id, current_step, progress_percent, details)
            except Exception as e:
                logger.error(f"Error in RQ progress callback: {sanitize_for_log(str(e))}")
        
        return progress_callback
    
    def update_rq_progress(self, task_id: str, current_step: str, 
                          progress_percent: int, details: Dict[str, Any] = None) -> bool:
        """
        Update progress for an RQ task
        
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
        
        try:
            # Get current RQ job info
            job = get_current_job()
            job_id = job.id if job else "unknown"
            worker_id = getattr(self._local, 'worker_id', 'unknown')
            
            # Get task info from database
            task_info = self._get_task_info(task_id)
            if not task_info:
                logger.warning(f"Task {sanitize_for_log(task_id)} not found for progress update")
                return False
            
            user_id = task_info['user_id']
            
            # Create RQ progress data
            progress_data = RQProgressData(
                task_id=task_id,
                job_id=job_id,
                worker_id=worker_id,
                user_id=user_id,
                current_step=current_step,
                progress_percent=max(0, min(100, progress_percent)),
                details=details,
                started_at=task_info.get('started_at'),
                updated_at=datetime.now(timezone.utc)
            )
            
            # Store progress in Redis
            self._store_progress_in_redis(progress_data)
            
            # Update database progress
            self._update_database_progress(task_id, current_step, progress_data.progress_percent)
            
            # Send WebSocket notification via existing progress tracker
            self._send_websocket_notification(progress_data)
            
            logger.debug(f"Updated RQ progress for task {sanitize_for_log(task_id)}: {progress_percent}% - {current_step}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update RQ progress: {sanitize_for_log(str(e))}")
            return False
    
    def _get_task_info(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task information from database"""
        session = self.db_manager.get_session()
        try:
            task = session.query(CaptionGenerationTask).filter_by(id=task_id).first()
            if task:
                return {
                    'user_id': task.user_id,
                    'started_at': task.started_at,
                    'status': task.status
                }
            return None
        finally:
            session.close()
    
    def _store_progress_in_redis(self, progress_data: RQProgressData) -> None:
        """Store progress data in Redis"""
        try:
            progress_key = f"{self.progress_key_prefix}{progress_data.task_id}"
            progress_json = json.dumps(progress_data.to_dict())
            
            # Store with TTL
            self.redis_connection.setex(progress_key, self.progress_ttl, progress_json)
            
            # Also store in a user-specific key for easy retrieval
            user_progress_key = f"rq:user_progress:{progress_data.user_id}:{progress_data.task_id}"
            self.redis_connection.setex(user_progress_key, self.progress_ttl, progress_json)
            
        except Exception as e:
            logger.error(f"Failed to store progress in Redis: {sanitize_for_log(str(e))}")
    
    def _update_database_progress(self, task_id: str, current_step: str, progress_percent: int) -> None:
        """Update progress in database for persistence"""
        session = self.db_manager.get_session()
        try:
            task = session.query(CaptionGenerationTask).filter_by(id=task_id).first()
            if task:
                task.current_step = current_step
                task.progress_percent = progress_percent
                session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to update database progress: {sanitize_for_log(str(e))}")
        finally:
            session.close()
    
    def _send_websocket_notification(self, progress_data: RQProgressData) -> None:
        """Send WebSocket notification via existing progress tracker"""
        try:
            # Convert RQ progress data to standard progress status
            progress_status = ProgressStatus(
                task_id=progress_data.task_id,
                user_id=progress_data.user_id,
                current_step=progress_data.current_step,
                progress_percent=progress_data.progress_percent,
                details={
                    **progress_data.details,
                    'job_id': progress_data.job_id,
                    'worker_id': progress_data.worker_id,
                    'source': 'rq_worker'
                },
                started_at=progress_data.started_at,
                updated_at=progress_data.updated_at
            )
            
            # Use existing progress tracker's WebSocket notification
            self.progress_tracker._send_progress_notification(
                progress_data.user_id, 
                progress_status
            )
            
        except Exception as e:
            logger.error(f"Failed to send WebSocket notification: {sanitize_for_log(str(e))}")
    
    def get_rq_progress(self, task_id: str, user_id: int) -> Optional[RQProgressData]:
        """
        Get current progress for an RQ task
        
        Args:
            task_id: The task ID to get progress for
            user_id: User ID for authorization
            
        Returns:
            RQProgressData or None if not found
        """
        try:
            # Check user authorization first
            if not self._check_user_authorization(task_id, user_id):
                logger.warning(f"User {user_id} not authorized for task {sanitize_for_log(task_id)}")
                return None
            
            # Try to get from Redis first
            progress_key = f"{self.progress_key_prefix}{task_id}"
            progress_json = self.redis_connection.get(progress_key)
            
            if progress_json:
                progress_dict = json.loads(progress_json)
                return RQProgressData.from_dict(progress_dict)
            
            # Fallback to database
            return self._get_progress_from_database(task_id)
            
        except Exception as e:
            logger.error(f"Failed to get RQ progress: {sanitize_for_log(str(e))}")
            return None
    
    def _check_user_authorization(self, task_id: str, user_id: int) -> bool:
        """Check if user is authorized to access task progress"""
        session = self.db_manager.get_session()
        try:
            task = session.query(CaptionGenerationTask).filter_by(
                id=task_id,
                user_id=user_id
            ).first()
            return task is not None
        finally:
            session.close()
    
    def _get_progress_from_database(self, task_id: str) -> Optional[RQProgressData]:
        """Get progress from database as fallback"""
        session = self.db_manager.get_session()
        try:
            task = session.query(CaptionGenerationTask).filter_by(id=task_id).first()
            if task:
                return RQProgressData(
                    task_id=task.id,
                    job_id="unknown",
                    worker_id="unknown",
                    user_id=task.user_id,
                    current_step=task.current_step or "Processing",
                    progress_percent=task.progress_percent or 0,
                    details={},
                    started_at=task.started_at,
                    updated_at=datetime.now(timezone.utc)
                )
            return None
        finally:
            session.close()
    
    def complete_rq_progress(self, task_id: str, results: Any) -> None:
        """
        Mark RQ task progress as complete
        
        Args:
            task_id: The task ID to complete
            results: Generation results
        """
        try:
            # Update progress to 100%
            self.update_rq_progress(
                task_id=task_id,
                current_step="Completed",
                progress_percent=100,
                details={
                    'completed': True,
                    'captions_generated': getattr(results, 'captions_generated', 0),
                    'images_processed': getattr(results, 'images_processed', 0),
                    'success_rate': getattr(results, 'success_rate', 0)
                }
            )
            
            # Use existing progress tracker for completion notification
            self.progress_tracker.complete_progress(task_id, results)
            
            # Clean up Redis progress data after a delay
            self._schedule_progress_cleanup(task_id)
            
            logger.info(f"Completed RQ progress tracking for task {sanitize_for_log(task_id)}")
            
        except Exception as e:
            logger.error(f"Failed to complete RQ progress: {sanitize_for_log(str(e))}")
    
    def fail_rq_progress(self, task_id: str, error_message: str, 
                        error_details: Dict[str, Any] = None) -> None:
        """
        Mark RQ task progress as failed
        
        Args:
            task_id: The task ID that failed
            error_message: Error message
            error_details: Optional error details
        """
        try:
            if error_details is None:
                error_details = {}
            
            # Update progress with error
            self.update_rq_progress(
                task_id=task_id,
                current_step=f"Failed: {error_message}",
                progress_percent=0,
                details={
                    'failed': True,
                    'error_message': error_message,
                    'error_details': error_details
                }
            )
            
            # Use existing progress tracker for failure notification
            self.progress_tracker.fail_progress(task_id, error_message, error_details)
            
            # Clean up Redis progress data
            self._schedule_progress_cleanup(task_id)
            
            logger.info(f"Failed RQ progress tracking for task {sanitize_for_log(task_id)}: {error_message}")
            
        except Exception as e:
            logger.error(f"Failed to fail RQ progress: {sanitize_for_log(str(e))}")
    
    def _schedule_progress_cleanup(self, task_id: str, delay_seconds: int = 300) -> None:
        """Schedule cleanup of progress data after delay"""
        try:
            # Set shorter TTL for cleanup
            progress_key = f"{self.progress_key_prefix}{task_id}"
            self.redis_connection.expire(progress_key, delay_seconds)
            
            # Also clean up user-specific key
            # We need to get user_id first
            task_info = self._get_task_info(task_id)
            if task_info:
                user_progress_key = f"rq:user_progress:{task_info['user_id']}:{task_id}"
                self.redis_connection.expire(user_progress_key, delay_seconds)
                
        except Exception as e:
            logger.error(f"Failed to schedule progress cleanup: {sanitize_for_log(str(e))}")
    
    def set_worker_context(self, worker_id: str) -> None:
        """Set worker context for current thread"""
        self._local.worker_id = worker_id
    
    def get_user_active_tasks_progress(self, user_id: int) -> Dict[str, RQProgressData]:
        """
        Get progress for all active tasks for a user
        
        Args:
            user_id: User ID to get tasks for
            
        Returns:
            Dict mapping task_id to RQProgressData
        """
        try:
            # Get active tasks from database
            session = self.db_manager.get_session()
            try:
                active_tasks = session.query(CaptionGenerationTask).filter_by(
                    user_id=user_id
                ).filter(
                    CaptionGenerationTask.status.in_([TaskStatus.QUEUED, TaskStatus.RUNNING])
                ).all()
                
                progress_data = {}
                
                for task in active_tasks:
                    progress = self.get_rq_progress(task.id, user_id)
                    if progress:
                        progress_data[task.id] = progress
                
                return progress_data
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Failed to get user active tasks progress: {sanitize_for_log(str(e))}")
            return {}
    
    def cleanup_expired_progress(self) -> int:
        """
        Clean up expired progress data from Redis
        
        Returns:
            int: Number of progress entries cleaned up
        """
        try:
            # Get all progress keys
            progress_keys = self.redis_connection.keys(f"{self.progress_key_prefix}*")
            user_progress_keys = self.redis_connection.keys("rq:user_progress:*")
            
            all_keys = progress_keys + user_progress_keys
            cleaned_count = 0
            
            for key in all_keys:
                try:
                    # Check if key has expired or task is no longer active
                    ttl = self.redis_connection.ttl(key)
                    if ttl == -1:  # No TTL set, check if task is still active
                        # Extract task_id from key
                        if key.startswith(self.progress_key_prefix):
                            task_id = key[len(self.progress_key_prefix):]
                        else:
                            # User progress key format: rq:user_progress:user_id:task_id
                            task_id = key.split(':')[-1]
                        
                        # Check if task is still active
                        task_info = self._get_task_info(task_id)
                        if not task_info or task_info['status'] not in [TaskStatus.QUEUED, TaskStatus.RUNNING]:
                            self.redis_connection.delete(key)
                            cleaned_count += 1
                            
                except Exception as key_error:
                    logger.debug(f"Error checking key {key}: {sanitize_for_log(str(key_error))}")
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} expired progress entries")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired progress: {sanitize_for_log(str(e))}")
            return 0
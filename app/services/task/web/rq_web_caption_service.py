# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
RQ-Aware Web Caption Generation Service

Enhanced web caption generation service that integrates with RQ for task processing
while maintaining backward compatibility with database queuing.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.exc import SQLAlchemyError

from app.core.database.core.database_manager import DatabaseManager
from app.core.security.core.security_utils import sanitize_for_log
from models import (
    CaptionGenerationTask, CaptionGenerationSettings, CaptionGenerationUserSettings,
    TaskStatus, PlatformConnection, User, UserRole, JobPriority
)
from app.services.task.rq.rq_queue_manager import RQQueueManager
from app.services.task.rq.rq_config import TaskPriority
from app.services.task.core.task_queue_manager import TaskQueueManager
from app.services.task.migration.task_migration_manager import TaskMigrationManager
from app.utils.processing.web_caption_generation_service import WebCaptionGenerationService

logger = logging.getLogger(__name__)


class RQWebCaptionService:
    """RQ-aware web caption generation service with fallback support"""
    
    def __init__(self, db_manager: DatabaseManager, rq_queue_manager: Optional[RQQueueManager] = None):
        """
        Initialize RQ-aware caption service
        
        Args:
            db_manager: Database manager instance
            rq_queue_manager: Optional RQ queue manager (if None, uses database only)
        """
        self.db_manager = db_manager
        self.rq_queue_manager = rq_queue_manager
        
        # Fallback to original service for database operations
        self.fallback_service = WebCaptionGenerationService(db_manager)
        self.database_task_manager = TaskQueueManager(db_manager)
        
        # Migration manager for hybrid operations
        if self.rq_queue_manager:
            self.migration_manager = TaskMigrationManager(db_manager, rq_queue_manager)
        else:
            self.migration_manager = None
    
    def start_caption_generation_sync(
        self, 
        user_id: int, 
        platform_connection_id: int,
        settings: Optional[CaptionGenerationSettings] = None,
        priority: Optional[TaskPriority] = None
    ) -> str:
        """
        Start caption generation with RQ support and database fallback
        
        Args:
            user_id: The user ID
            platform_connection_id: The platform connection ID
            settings: Optional custom settings
            priority: Optional task priority (for RQ)
            
        Returns:
            str: The task ID
            
        Raises:
            ValueError: If validation fails
            RuntimeError: If task creation fails
        """
        try:
            # Check if user already has an active task
            if self._user_has_active_task(user_id):
                raise ValueError(f"User {user_id} already has an active caption generation task")
            
            # Validate user and platform access
            self._validate_user_platform_access_sync(user_id, platform_connection_id)
            
            # Get or create settings
            if settings is None:
                settings = self._get_user_settings_sync(user_id, platform_connection_id)
            
            # Determine priority based on user role
            if priority is None:
                priority = self._determine_task_priority(user_id)
            
            # Try RQ first, fallback to database if needed
            if self.rq_queue_manager and self.rq_queue_manager.check_redis_health():
                return self._enqueue_to_rq(user_id, platform_connection_id, settings, priority)
            else:
                logger.info("RQ unavailable, using database fallback for task creation")
                return self._enqueue_to_database(user_id, platform_connection_id, settings)
                
        except Exception as e:
            logger.error(f"Error in RQ caption generation: {sanitize_for_log(str(e))}")
            raise
    
    def _user_has_active_task(self, user_id: int) -> bool:
        """Check if user has active task in either RQ or database"""
        try:
            # Check RQ first if available
            if self.rq_queue_manager and self.rq_queue_manager.user_task_tracker:
                rq_task = self.rq_queue_manager.user_task_tracker.get_user_active_task(user_id)
                if rq_task:
                    return True
            
            # Check database
            db_task = self.database_task_manager.get_user_active_task(user_id)
            return db_task is not None
            
        except Exception as e:
            logger.error(f"Error checking user active task: {sanitize_for_log(str(e))}")
            # Default to checking database only
            db_task = self.database_task_manager.get_user_active_task(user_id)
            return db_task is not None
    
    def _validate_user_platform_access_sync(self, user_id: int, platform_connection_id: int) -> None:
        """Validate user platform access"""
        session = self.db_manager.get_session()
        try:
            # Check if user exists and is active
            user = session.query(User).filter_by(id=user_id, is_active=True).first()
            if not user:
                raise ValueError(f"User {user_id} not found or inactive")
            
            # Check if platform connection exists and belongs to user
            platform_connection = session.query(PlatformConnection).filter_by(
                id=platform_connection_id,
                user_id=user_id,
                is_active=True
            ).first()
            
            if not platform_connection:
                raise ValueError(f"Platform connection {platform_connection_id} not found or not accessible to user {user_id}")
            
        finally:
            session.close()
    
    def _get_user_settings_sync(self, user_id: int, platform_connection_id: int) -> CaptionGenerationSettings:
        """Get user's caption generation settings"""
        session = self.db_manager.get_session()
        try:
            # Try to get user's custom settings
            user_settings = session.query(CaptionGenerationUserSettings).filter_by(
                user_id=user_id,
                platform_connection_id=platform_connection_id
            ).first()
            
            if user_settings:
                return user_settings.to_settings_dataclass()
            else:
                # Return default settings
                return CaptionGenerationSettings()
                
        finally:
            session.close()
    
    def _determine_task_priority(self, user_id: int) -> TaskPriority:
        """Determine task priority based on user role"""
        session = self.db_manager.get_session()
        try:
            user = session.query(User).filter_by(id=user_id).first()
            if user and user.role == UserRole.ADMIN:
                return TaskPriority.HIGH
            else:
                return TaskPriority.NORMAL
                
        except Exception as e:
            logger.error(f"Error determining task priority: {sanitize_for_log(str(e))}")
            return TaskPriority.NORMAL
        finally:
            session.close()
    
    def _enqueue_to_rq(self, user_id: int, platform_connection_id: int, 
                      settings: CaptionGenerationSettings, priority: TaskPriority) -> str:
        """Enqueue task to RQ"""
        try:
            # Create task object
            task = CaptionGenerationTask(
                user_id=user_id,
                platform_connection_id=platform_connection_id,
                status=TaskStatus.QUEUED
            )
            task.settings = settings
            
            # Convert TaskPriority to JobPriority for database storage
            task.priority = self._convert_task_priority_to_job_priority(priority)
            
            # Enqueue to RQ
            task_id = self.rq_queue_manager.enqueue_task(task, priority)
            
            logger.info(f"Enqueued task {sanitize_for_log(task_id)} to RQ with priority {priority.value}")
            return task_id
            
        except Exception as e:
            logger.error(f"Failed to enqueue task to RQ: {sanitize_for_log(str(e))}")
            # Fallback to database
            logger.info("Falling back to database queuing")
            return self._enqueue_to_database(user_id, platform_connection_id, settings)
    
    def _enqueue_to_database(self, user_id: int, platform_connection_id: int, 
                           settings: CaptionGenerationSettings) -> str:
        """Enqueue task to database (fallback mode)"""
        try:
            # Use the original service for database enqueueing
            return self.fallback_service.start_caption_generation_sync(
                user_id, platform_connection_id, settings
            )
            
        except Exception as e:
            logger.error(f"Failed to enqueue task to database: {sanitize_for_log(str(e))}")
            raise RuntimeError(f"Failed to create caption generation task: {str(e)}")
    
    def _convert_task_priority_to_job_priority(self, task_priority: TaskPriority) -> JobPriority:
        """Convert TaskPriority to JobPriority enum"""
        mapping = {
            TaskPriority.URGENT: JobPriority.URGENT,
            TaskPriority.HIGH: JobPriority.HIGH,
            TaskPriority.NORMAL: JobPriority.NORMAL,
            TaskPriority.LOW: JobPriority.LOW
        }
        return mapping.get(task_priority, JobPriority.NORMAL)
    
    def get_task_status(self, task_id: str, user_id: int) -> Optional[Dict[str, Any]]:
        """Get task status from either RQ or database"""
        try:
            # First check if task exists in database (both RQ and database tasks are stored there)
            session = self.db_manager.get_session()
            try:
                task = session.query(CaptionGenerationTask).filter_by(
                    id=task_id, user_id=user_id
                ).first()
                
                if not task:
                    return None
                
                # Return task status information
                return {
                    'task_id': task.id,
                    'status': task.status.value if hasattr(task.status, 'value') else str(task.status),
                    'progress_percent': task.progress_percent or 0,
                    'current_step': task.current_step,
                    'error_message': task.error_message,
                    'created_at': task.created_at.isoformat() if task.created_at else None,
                    'started_at': task.started_at.isoformat() if task.started_at else None,
                    'completed_at': task.completed_at.isoformat() if task.completed_at else None
                }
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Error getting task status: {sanitize_for_log(str(e))}")
            return None
    
    def cancel_generation(self, task_id: str, user_id: int) -> bool:
        """Cancel caption generation task"""
        try:
            # Try to cancel in RQ first if available
            if self.rq_queue_manager:
                # Check if task is in RQ
                try:
                    # For RQ tasks, we need to cancel the job and update database
                    # This is a simplified implementation - in practice, you'd need to
                    # check which queue the task is in and cancel the RQ job
                    pass
                except Exception as e:
                    logger.debug(f"Task not found in RQ, trying database: {e}")
            
            # Cancel in database (works for both RQ and database tasks)
            success = self.database_task_manager.cancel_task(task_id, user_id=user_id)
            
            if success:
                logger.info(f"Cancelled task {sanitize_for_log(task_id)} for user {sanitize_for_log(str(user_id))}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error cancelling task: {sanitize_for_log(str(e))}")
            return False
    
    def get_active_task_for_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get active task for user from either RQ or database"""
        try:
            # Check database for active tasks (both RQ and database tasks are stored there)
            active_task = self.database_task_manager.get_user_active_task(user_id)
            
            if active_task:
                return {
                    'task_id': active_task.id,
                    'status': active_task.status.value if hasattr(active_task.status, 'value') else str(active_task.status),
                    'progress_percent': active_task.progress_percent or 0,
                    'current_step': active_task.current_step,
                    'created_at': active_task.created_at.isoformat() if active_task.created_at else None,
                    'started_at': active_task.started_at.isoformat() if active_task.started_at else None
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting active task for user: {sanitize_for_log(str(e))}")
            return None
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        status = {
            'rq_available': False,
            'rq_healthy': False,
            'fallback_mode': True,
            'queue_stats': {},
            'migration_stats': {}
        }
        
        try:
            if self.rq_queue_manager:
                status['rq_available'] = True
                status['rq_healthy'] = self.rq_queue_manager.check_redis_health()
                status['fallback_mode'] = not status['rq_healthy']
                status['queue_stats'] = self.rq_queue_manager.get_queue_stats()
                
                if self.migration_manager:
                    status['migration_stats'] = self.migration_manager.get_migration_statistics()
            
            # Add database queue stats
            db_stats = self.database_task_manager.get_queue_stats()
            status['database_stats'] = db_stats
            
        except Exception as e:
            logger.error(f"Error getting system status: {sanitize_for_log(str(e))}")
            status['error'] = str(e)
        
        return status
    
    def migrate_database_tasks_to_rq(self) -> Dict[str, Any]:
        """Migrate database tasks to RQ (admin operation)"""
        if not self.migration_manager:
            return {'error': 'Migration manager not available'}
        
        try:
            return self.migration_manager.migrate_database_tasks_to_rq()
        except Exception as e:
            logger.error(f"Error migrating tasks to RQ: {sanitize_for_log(str(e))}")
            return {'error': str(e)}
    
    def validate_migration_integrity(self) -> Dict[str, Any]:
        """Validate migration integrity (admin operation)"""
        if not self.migration_manager:
            return {'error': 'Migration manager not available'}
        
        try:
            return self.migration_manager.validate_migration_integrity()
        except Exception as e:
            logger.error(f"Error validating migration integrity: {sanitize_for_log(str(e))}")
            return {'error': str(e)}
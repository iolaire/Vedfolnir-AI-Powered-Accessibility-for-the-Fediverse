# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
RQ Queue Manager

Manages Redis Queue operations with priority queues, user task enforcement,
and Redis health monitoring with automatic fallback capabilities.
"""

import logging
import threading
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import redis
from rq import Queue
from rq.exceptions import NoSuchJobError

from app.core.database.core.database_manager import DatabaseManager
from app.core.security.features.caption_security import CaptionSecurityManager
from app.core.security.core.security_utils import sanitize_for_log
from models import CaptionGenerationTask, TaskStatus, JobPriority
from .rq_config import RQConfig, TaskPriority
from .redis_connection_manager import RedisConnectionManager
from .user_task_tracker import UserTaskTracker
from .redis_health_monitor import RedisHealthMonitor
from .rq_security_manager import RQSecurityManager
from .rq_data_retention_manager import RQDataRetentionManager

logger = logging.getLogger(__name__)


class RQQueueManager:
    """Central component for managing Redis queues and task lifecycle with single-task-per-user enforcement"""
    
    def __init__(self, db_manager: DatabaseManager, config: RQConfig, security_manager: CaptionSecurityManager):
        """
        Initialize RQ Queue Manager
        
        Args:
            db_manager: Database manager instance
            config: RQ configuration
            security_manager: Caption security manager for secure task ID generation
        """
        self.db_manager = db_manager
        self.config = config
        self.security_manager = security_manager
        self._lock = threading.Lock()
        
        # Initialize Redis connection manager
        self.redis_manager = RedisConnectionManager(config)
        self.redis_connection: Optional[redis.Redis] = None
        
        # Initialize components
        self.queues: Dict[str, Queue] = {}
        self.user_task_tracker: Optional[UserTaskTracker] = None
        self.redis_health_monitor: Optional[RedisHealthMonitor] = None
        self.rq_security_manager: Optional[RQSecurityManager] = None
        self.data_retention_manager: Optional[RQDataRetentionManager] = None
        
        # Fallback state
        self._redis_available = False
        self._fallback_mode = False
        
        # Initialize the system
        self._initialize()
    
    def _initialize(self) -> None:
        """Initialize RQ queue system"""
        try:
            # Initialize Redis connection
            if self.redis_manager.initialize():
                self.redis_connection = self.redis_manager.get_connection()
                if self.redis_connection:
                    self._redis_available = True
                    self._initialize_priority_queues()
                    self._initialize_components()
                    logger.info("RQ Queue Manager initialized successfully with Redis")
                else:
                    self._handle_redis_unavailable()
            else:
                self._handle_redis_unavailable()
                
        except Exception as e:
            logger.error(f"Failed to initialize RQ Queue Manager: {e}")
            self._handle_redis_unavailable()
    
    def _initialize_priority_queues(self) -> None:
        """Initialize priority queues (urgent, high, normal, low)"""
        if not self.redis_connection:
            return
        
        try:
            queue_names = self.config.get_queue_names()
            
            for priority in queue_names:
                queue_config = self.config.queue_configs[priority]
                queue = Queue(
                    name=queue_config.name,
                    connection=self.redis_connection,
                    default_timeout=queue_config.timeout
                )
                self.queues[priority] = queue
                logger.info(f"Initialized queue: {queue_config.name}")
            
            logger.info(f"Successfully initialized {len(self.queues)} priority queues")
            
        except Exception as e:
            logger.error(f"Failed to initialize priority queues: {e}")
            raise
    
    def _initialize_components(self) -> None:
        """Initialize UserTaskTracker, RedisHealthMonitor, and security components"""
        if not self.redis_connection:
            return
        
        try:
            # Initialize user task tracker
            self.user_task_tracker = UserTaskTracker(self.redis_connection)
            
            # Initialize Redis health monitor
            self.redis_health_monitor = RedisHealthMonitor(self.redis_connection, self.config)
            
            # Initialize RQ security manager
            self.rq_security_manager = RQSecurityManager(
                self.db_manager, 
                self.redis_connection, 
                self.security_manager
            )
            
            # Initialize data retention manager
            self.data_retention_manager = RQDataRetentionManager(
                self.db_manager,
                self.redis_connection,
                self.config,
                self.queues
            )
            
            # Register health callbacks
            self.redis_health_monitor.register_failure_callback(self._handle_redis_failure)
            self.redis_health_monitor.register_recovery_callback(self._handle_redis_recovery)
            
            # Start health monitoring
            self.redis_health_monitor.start_monitoring()
            
            # Start data retention monitoring
            self.data_retention_manager.start_monitoring()
            
            logger.info("RQ components initialized successfully with security and data retention")
            
        except Exception as e:
            logger.error(f"Failed to initialize RQ components: {e}")
            raise
    
    def _handle_redis_unavailable(self) -> None:
        """Handle Redis unavailability by enabling fallback mode"""
        self._redis_available = False
        self._fallback_mode = True
        logger.warning("Redis unavailable - enabling database fallback mode")
    
    def _handle_redis_failure(self) -> None:
        """Handle Redis failure detected by health monitor"""
        logger.warning("Redis failure detected - switching to fallback mode")
        with self._lock:
            self._redis_available = False
            self._fallback_mode = True
    
    def _handle_redis_recovery(self) -> None:
        """Handle Redis recovery detected by health monitor"""
        logger.info("Redis recovery detected - attempting to restore RQ mode")
        with self._lock:
            try:
                # Reinitialize Redis connection
                self.redis_connection = self.redis_manager.get_connection()
                if self.redis_connection:
                    self._initialize_priority_queues()
                    self._redis_available = True
                    self._fallback_mode = False
                    logger.info("Successfully restored RQ mode after Redis recovery")
                    
                    # TODO: Migrate database tasks back to RQ
                    # This will be implemented in task 4.2
                    
            except Exception as e:
                logger.error(f"Failed to restore RQ mode after Redis recovery: {e}")
    
    def enqueue_task(self, task: CaptionGenerationTask, priority: TaskPriority = TaskPriority.NORMAL) -> str:
        """
        Enqueue a caption generation task with security validation
        
        Args:
            task: The CaptionGenerationTask to enqueue
            priority: Task priority level
            
        Returns:
            str: The task ID if successful
            
        Raises:
            ValueError: If user already has an active task or Redis/database operation fails
        """
        with self._lock:
            try:
                # Generate secure task ID if not already set
                if not task.id:
                    if self.rq_security_manager:
                        task.id = self.rq_security_manager.generate_secure_task_id()
                    else:
                        task.id = self.security_manager.generate_secure_task_id()
                
                # Validate task ID format
                if self.rq_security_manager and not self.rq_security_manager.validate_task_id(task.id):
                    raise ValueError(f"Invalid task ID format: {task.id}")
                
                # Set priority
                task.priority = self._convert_priority_to_job_priority(priority)
                
                # Check single-task-per-user constraint
                if not self._enforce_single_task_per_user(task.user_id, task.id):
                    raise ValueError(f"User {task.user_id} already has an active task")
                
                # Log security event
                if self.rq_security_manager:
                    self.rq_security_manager.log_security_event(
                        'task_enqueue_attempt',
                        {
                            'task_id': task.id,
                            'user_id': task.user_id,
                            'priority': priority.value,
                            'platform_connection_id': task.platform_connection_id
                        },
                        user_id=task.user_id
                    )
                
                if self._redis_available and not self._fallback_mode:
                    # Enqueue to Redis with security
                    return self._enqueue_to_redis_secure(task, priority)
                else:
                    # Fallback to database
                    return self._enqueue_to_database(task)
                    
            except Exception as e:
                # Log security event for failed enqueue
                if self.rq_security_manager:
                    self.rq_security_manager.log_security_event(
                        'task_enqueue_failed',
                        {
                            'task_id': getattr(task, 'id', 'unknown'),
                            'user_id': task.user_id,
                            'error': str(e)
                        },
                        severity='ERROR',
                        user_id=task.user_id
                    )
                
                logger.error(f"Failed to enqueue task: {sanitize_for_log(str(e))}")
                raise
    
    def _enforce_single_task_per_user(self, user_id: int, task_id: str) -> bool:
        """Enforce single-task-per-user constraint using Redis or database"""
        try:
            if self._redis_available and self.user_task_tracker:
                # Use Redis-based tracking
                return self.user_task_tracker.set_user_active_task(user_id, task_id)
            else:
                # Use database-based tracking
                return self._check_user_active_task_database(user_id)
                
        except Exception as e:
            logger.error(f"Error enforcing single-task-per-user: {sanitize_for_log(str(e))}")
            return False
    
    def _check_user_active_task_database(self, user_id: int) -> bool:
        """Check for active tasks in database"""
        session = self.db_manager.get_session()
        try:
            existing_task = session.query(CaptionGenerationTask).filter_by(
                user_id=user_id
            ).filter(
                CaptionGenerationTask.status.in_([TaskStatus.QUEUED, TaskStatus.RUNNING])
            ).first()
            
            return existing_task is None
            
        finally:
            session.close()
    
    def _enqueue_to_redis_secure(self, task: CaptionGenerationTask, priority: TaskPriority) -> str:
        """Enqueue task to Redis queue with security measures"""
        try:
            # Get appropriate queue
            queue = self.queues.get(priority.value)
            if not queue:
                raise ValueError(f"Queue not found for priority: {priority.value}")
            
            # Store task authorization if security manager is available
            if self.rq_security_manager:
                self.rq_security_manager.store_task_authorization(
                    task.id, 
                    task.user_id, 
                    task.platform_connection_id
                )
            
            # Enqueue the task
            job = queue.enqueue(
                'app.services.task.rq.rq_job_processor.process_caption_task',
                task.id,
                job_id=task.id,
                job_timeout=self.config.queue_configs[priority.value].timeout
            )
            
            # Update task status in database
            self._update_task_status_database(task.id, TaskStatus.QUEUED)
            
            # Set TTL for task data based on retention policy
            if self.data_retention_manager:
                self.data_retention_manager.set_task_ttl(task.id, TaskStatus.QUEUED)
            
            # Log successful enqueue
            if self.rq_security_manager:
                self.rq_security_manager.log_security_event(
                    'task_enqueued_success',
                    {
                        'task_id': task.id,
                        'queue': priority.value,
                        'job_id': job.id
                    },
                    user_id=task.user_id
                )
            
            logger.info(f"Securely enqueued task {sanitize_for_log(task.id)} to Redis queue {priority.value}")
            return task.id
            
        except Exception as e:
            logger.error(f"Failed to enqueue task to Redis: {sanitize_for_log(str(e))}")
            # Clear user task tracking on failure
            if self.user_task_tracker:
                self.user_task_tracker.clear_user_active_task(task.user_id)
            raise
    
    def _enqueue_to_redis(self, task: CaptionGenerationTask, priority: TaskPriority) -> str:
        """Legacy enqueue method - redirects to secure version"""
        return self._enqueue_to_redis_secure(task, priority)
    
    def _enqueue_to_database(self, task: CaptionGenerationTask) -> str:
        """Enqueue task to database (fallback mode)"""
        session = self.db_manager.get_session()
        try:
            task.status = TaskStatus.QUEUED
            session.add(task)
            session.commit()
            
            logger.info(f"Enqueued task {sanitize_for_log(task.id)} to database (fallback mode)")
            return task.id
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to enqueue task to database: {sanitize_for_log(str(e))}")
            raise
        finally:
            session.close()
    
    def _update_task_status_database(self, task_id: str, status: TaskStatus) -> None:
        """Update task status in database"""
        session = self.db_manager.get_session()
        try:
            task = session.query(CaptionGenerationTask).filter_by(id=task_id).first()
            if task:
                task.status = status
                if status == TaskStatus.RUNNING:
                    task.started_at = datetime.now(timezone.utc)
                elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                    task.completed_at = datetime.now(timezone.utc)
                session.commit()
                
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to update task status in database: {sanitize_for_log(str(e))}")
        finally:
            session.close()
    
    def _convert_priority_to_job_priority(self, priority: TaskPriority) -> JobPriority:
        """Convert TaskPriority to JobPriority enum"""
        mapping = {
            TaskPriority.URGENT: JobPriority.URGENT,
            TaskPriority.HIGH: JobPriority.HIGH,
            TaskPriority.NORMAL: JobPriority.NORMAL,
            TaskPriority.LOW: JobPriority.LOW
        }
        return mapping.get(priority, JobPriority.NORMAL)
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get statistics about the task queues"""
        stats = {
            'redis_available': self._redis_available,
            'fallback_mode': self._fallback_mode,
            'queues': {},
            'total_pending': 0,
            'total_failed': 0
        }
        
        if self._redis_available and self.queues:
            # Get Redis queue statistics
            try:
                for priority, queue in self.queues.items():
                    queue_stats = {
                        'pending': len(queue),
                        'failed': queue.failed_job_registry.count,
                        'finished': queue.finished_job_registry.count,
                        'started': queue.started_job_registry.count
                    }
                    stats['queues'][priority] = queue_stats
                    stats['total_pending'] += queue_stats['pending']
                    stats['total_failed'] += queue_stats['failed']
                    
            except Exception as e:
                logger.error(f"Error getting Redis queue stats: {sanitize_for_log(str(e))}")
        
        # Add database statistics
        stats.update(self._get_database_queue_stats())
        
        return stats
    
    def _get_database_queue_stats(self) -> Dict[str, Any]:
        """Get database task statistics"""
        session = self.db_manager.get_session()
        try:
            db_stats = {}
            
            # Count tasks by status
            for status in TaskStatus:
                count = session.query(CaptionGenerationTask).filter_by(status=status).count()
                db_stats[f'db_{status.value}'] = count
            
            # Total database tasks
            db_stats['db_total'] = sum(db_stats.values())
            
            return db_stats
            
        except Exception as e:
            logger.error(f"Error getting database queue stats: {sanitize_for_log(str(e))}")
            return {}
        finally:
            session.close()
    
    def migrate_database_tasks(self) -> int:
        """
        Migrate existing database tasks to RQ queues
        
        Returns:
            int: Number of tasks migrated
        """
        if not self._redis_available or self._fallback_mode:
            logger.warning("Cannot migrate tasks - Redis not available")
            return 0
        
        migrated_count = 0
        session = self.db_manager.get_session()
        
        try:
            # Get queued tasks from database
            queued_tasks = session.query(CaptionGenerationTask).filter_by(
                status=TaskStatus.QUEUED
            ).all()
            
            for task in queued_tasks:
                try:
                    # Determine priority
                    priority = self._convert_job_priority_to_task_priority(task.priority)
                    
                    # Enqueue to Redis
                    queue = self.queues.get(priority.value)
                    if queue:
                        job = queue.enqueue(
                            'app.services.task.rq.rq_job_processor.process_caption_task',
                            task.id,
                            job_id=task.id,
                            job_timeout=self.config.queue_configs[priority.value].timeout
                        )
                        
                        # Update user task tracking
                        if self.user_task_tracker:
                            self.user_task_tracker.set_user_active_task(task.user_id, task.id)
                        
                        migrated_count += 1
                        logger.info(f"Migrated task {sanitize_for_log(task.id)} to RQ queue {priority.value}")
                        
                except Exception as e:
                    logger.error(f"Failed to migrate task {sanitize_for_log(task.id)}: {sanitize_for_log(str(e))}")
            
            logger.info(f"Successfully migrated {migrated_count} tasks from database to RQ")
            return migrated_count
            
        except Exception as e:
            logger.error(f"Error during task migration: {sanitize_for_log(str(e))}")
            return migrated_count
        finally:
            session.close()
    
    def _convert_job_priority_to_task_priority(self, job_priority: JobPriority) -> TaskPriority:
        """Convert JobPriority to TaskPriority enum"""
        mapping = {
            JobPriority.URGENT: TaskPriority.URGENT,
            JobPriority.HIGH: TaskPriority.HIGH,
            JobPriority.NORMAL: TaskPriority.NORMAL,
            JobPriority.LOW: TaskPriority.LOW
        }
        return mapping.get(job_priority, TaskPriority.NORMAL)
    
    def cleanup_completed_jobs(self) -> None:
        """Clean up completed jobs from Redis queues using data retention manager"""
        if not self._redis_available or not self.queues:
            return
        
        try:
            if self.data_retention_manager:
                # Use data retention manager for comprehensive cleanup
                cleanup_results = self.data_retention_manager.cleanup_expired_data()
                logger.info(f"Data retention cleanup completed: {cleanup_results.get('items_cleaned', 0)} items cleaned")
            else:
                # Fallback to basic cleanup
                for priority, queue in self.queues.items():
                    # Clean up finished jobs
                    finished_count = queue.finished_job_registry.cleanup()
                    
                    # Clean up failed jobs older than TTL
                    failed_count = queue.failed_job_registry.cleanup()
                    
                    if finished_count > 0 or failed_count > 0:
                        logger.info(f"Cleaned up {finished_count} finished and {failed_count} failed jobs from {priority} queue")
                    
        except Exception as e:
            logger.error(f"Error during job cleanup: {sanitize_for_log(str(e))}")
    
    def check_redis_health(self) -> bool:
        """Check Redis health status"""
        if self.redis_health_monitor:
            return self.redis_health_monitor.check_health()
        return self._redis_available
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status"""
        status = {
            'redis_available': self._redis_available,
            'fallback_mode': self._fallback_mode,
            'queues_initialized': len(self.queues) > 0,
            'user_tracker_active': self.user_task_tracker is not None,
            'health_monitor_active': self.redis_health_monitor is not None
        }
        
        # Add Redis connection status
        if self.redis_manager:
            status.update(self.redis_manager.get_health_status())
        
        # Add Redis health monitor status
        if self.redis_health_monitor:
            status.update(self.redis_health_monitor.get_health_status())
        
        return status
    
    def force_health_check(self) -> Dict[str, Any]:
        """Force immediate health check"""
        if self.redis_manager:
            return self.redis_manager.force_health_check()
        return {'error': 'Redis manager not initialized'}
    
    def cleanup(self) -> None:
        """Cleanup resources including security and data retention components"""
        try:
            # Stop data retention monitoring
            if self.data_retention_manager:
                self.data_retention_manager.stop_monitoring()
            
            # Cleanup security manager
            if self.rq_security_manager:
                self.rq_security_manager.cleanup_expired_auth_data()
            
            # Stop Redis health monitoring
            if self.redis_health_monitor:
                self.redis_health_monitor.stop_monitoring()
            
            # Cleanup Redis manager
            if self.redis_manager:
                self.redis_manager.cleanup()
            
            logger.info("RQ Queue Manager cleanup completed with security and data retention")
            
        except Exception as e:
            logger.error(f"Error during RQ Queue Manager cleanup: {sanitize_for_log(str(e))}")
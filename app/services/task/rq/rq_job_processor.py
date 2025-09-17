# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
RQ Job Processor

Processes RQ jobs that integrate with existing CaptionGenerationService.
Handles task processing with database updates and error handling.
"""

import logging
import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from rq import get_current_job
from flask import current_app

from app.core.database.core.database_manager import DatabaseManager
from app.core.security.core.security_utils import sanitize_for_log
from models import CaptionGenerationTask, TaskStatus, PlatformConnection
from app.utils.processing.web_caption_generation_service import WebCaptionGenerationService
from app.services.monitoring.progress.progress_tracker import ProgressTracker
from .rq_progress_tracker import RQProgressTracker
from .rq_security_manager import RQSecurityManager
from app.services.platform.adapters.platform_aware_caption_adapter import PlatformAwareCaptionAdapter

logger = logging.getLogger(__name__)


def process_caption_task(task_id: str) -> Dict[str, Any]:
    """
    Main RQ job function for processing caption generation tasks
    
    Args:
        task_id: The caption generation task ID to process
        
    Returns:
        Dict containing job results
        
    Raises:
        Exception: If task processing fails
    """
    job = get_current_job()
    job_id = job.id if job else "unknown"
    
    logger.info(f"Starting RQ job {job_id} for caption task {sanitize_for_log(task_id)}")
    
    try:
        # Get database manager from Flask app context
        db_manager = current_app.config.get('db_manager')
        if not db_manager:
            raise RuntimeError("Database manager not available in Flask context")
        
        # Get Redis connection and security manager if available
        redis_connection = None
        security_manager = None
        rq_integration = current_app.config.get('rq_integration')
        if rq_integration:
            if hasattr(rq_integration, 'redis_manager'):
                redis_connection = rq_integration.redis_manager.get_connection()
            if hasattr(rq_integration, 'rq_security_manager'):
                security_manager = rq_integration.rq_security_manager
        
        # Create job processor instance
        processor = RQJobProcessor(db_manager, redis_connection, security_manager)
        
        # Process the task
        result = processor.process_task(task_id)
        
        logger.info(f"Completed RQ job {job_id} for caption task {sanitize_for_log(task_id)}")
        return result
        
    except Exception as e:
        logger.error(f"RQ job {job_id} failed for caption task {sanitize_for_log(task_id)}: {sanitize_for_log(str(e))}")
        raise


class RQJobProcessor:
    """Processes caption generation tasks in RQ workers with security validation"""
    
    def __init__(self, db_manager: DatabaseManager, redis_connection=None, security_manager=None):
        """
        Initialize RQ Job Processor
        
        Args:
            db_manager: Database manager instance
            redis_connection: Optional Redis connection for RQ progress tracking
            security_manager: Optional RQ security manager for validation
        """
        self.db_manager = db_manager
        self.progress_tracker = ProgressTracker(db_manager)
        self.security_manager = security_manager
        
        # Initialize RQ progress tracker if Redis is available
        if redis_connection:
            self.rq_progress_tracker = RQProgressTracker(db_manager, redis_connection)
        else:
            self.rq_progress_tracker = None
    
    def process_task(self, task_id: str) -> Dict[str, Any]:
        """
        Process a caption generation task with security validation
        
        Args:
            task_id: The task ID to process
            
        Returns:
            Dict containing processing results
            
        Raises:
            Exception: If task processing fails
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            # Validate task ID format
            if self.security_manager and not self.security_manager.validate_task_id(task_id):
                raise ValueError(f"Invalid task ID format: {task_id}")
            
            # Get task from database
            task = self._get_task(task_id)
            if not task:
                raise ValueError(f"Task {task_id} not found")
            
            # Validate task access if security manager is available
            if self.security_manager and not self.security_manager.validate_task_access(task_id, task.user_id):
                raise PermissionError(f"Access denied for task {task_id}")
            
            # Log security event for task processing start
            if self.security_manager:
                self.security_manager.log_security_event(
                    'task_processing_started',
                    {
                        'task_id': task_id,
                        'user_id': task.user_id,
                        'platform_connection_id': task.platform_connection_id
                    },
                    user_id=task.user_id
                )
            
            # Update task status to running
            self._update_task_status(task_id, TaskStatus.RUNNING, start_time)
            
            # Get platform connection
            platform_connection = self._get_platform_connection(task.platform_connection_id)
            
            # Process the task using existing caption generation logic
            result = self._execute_caption_generation(task, platform_connection)
            
            # Update task status to completed
            end_time = datetime.now(timezone.utc)
            self._update_task_status(task_id, TaskStatus.COMPLETED, end_time)
            
            # Clear user task tracking
            self._clear_user_task_tracking(task.user_id)
            
            # Prepare result
            processing_time = (end_time - start_time).total_seconds()
            
            job_result = {
                'task_id': task_id,
                'success': True,
                'processing_time': processing_time,
                'captions_generated': result.get('captions_generated', 0),
                'images_processed': result.get('images_processed', 0),
                'completed_at': end_time.isoformat()
            }
            
            # Log successful completion
            if self.security_manager:
                self.security_manager.log_security_event(
                    'task_processing_completed',
                    {
                        'task_id': task_id,
                        'processing_time': processing_time,
                        'captions_generated': result.get('captions_generated', 0)
                    },
                    user_id=task.user_id
                )
            
            logger.info(f"Successfully processed task {sanitize_for_log(task_id)} in {processing_time:.2f}s")
            return job_result
            
        except Exception as e:
            # Sanitize error message to prevent information leakage
            if self.security_manager:
                sanitized_error = self.security_manager.sanitize_error_message(str(e), task_id)
            else:
                sanitized_error = sanitize_for_log(str(e))
            
            # Update task status to failed
            end_time = datetime.now(timezone.utc)
            
            try:
                self._update_task_status(task_id, TaskStatus.FAILED, end_time, sanitized_error)
                self._clear_user_task_tracking_by_task_id(task_id)
            except Exception as update_error:
                logger.error(f"Failed to update task status after error: {sanitize_for_log(str(update_error))}")
            
            # Log security event for task failure
            if self.security_manager:
                self.security_manager.log_security_event(
                    'task_processing_failed',
                    {
                        'task_id': task_id,
                        'error_type': type(e).__name__,
                        'sanitized_error': sanitized_error
                    },
                    severity='ERROR',
                    user_id=getattr(task, 'user_id', None) if 'task' in locals() else None
                )
            
            # Prepare error result
            processing_time = (end_time - start_time).total_seconds()
            
            job_result = {
                'task_id': task_id,
                'success': False,
                'processing_time': processing_time,
                'error': sanitized_error,
                'failed_at': end_time.isoformat()
            }
            
            logger.error(f"Failed to process task {sanitize_for_log(task_id)}: {sanitized_error}")
            raise Exception(f"Task processing failed: {sanitized_error}")
    
    def _get_task(self, task_id: str) -> Optional[CaptionGenerationTask]:
        """Get task from database"""
        session = self.db_manager.get_session()
        try:
            task = session.query(CaptionGenerationTask).filter_by(id=task_id).first()
            if task:
                # Detach from session to avoid issues
                session.expunge(task)
            return task
        finally:
            session.close()
    
    def _get_platform_connection(self, platform_connection_id: int) -> PlatformConnection:
        """Get platform connection from database"""
        session = self.db_manager.get_session()
        try:
            platform_connection = session.query(PlatformConnection).filter_by(
                id=platform_connection_id,
                is_active=True
            ).first()
            
            if not platform_connection:
                raise ValueError(f"Platform connection {platform_connection_id} not found or inactive")
            
            # Detach from session to avoid issues
            session.expunge(platform_connection)
            return platform_connection
            
        finally:
            session.close()
    
    def _update_task_status(self, task_id: str, status: TaskStatus, 
                           timestamp: datetime, error_message: Optional[str] = None) -> None:
        """Update task status in database"""
        session = self.db_manager.get_session()
        try:
            task = session.query(CaptionGenerationTask).filter_by(id=task_id).first()
            if task:
                task.status = status
                
                if status == TaskStatus.RUNNING:
                    task.started_at = timestamp
                elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                    task.completed_at = timestamp
                
                if error_message:
                    task.error_message = error_message
                
                session.commit()
                logger.debug(f"Updated task {sanitize_for_log(task_id)} status to {status.value}")
            else:
                logger.warning(f"Task {sanitize_for_log(task_id)} not found for status update")
                
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to update task status: {sanitize_for_log(str(e))}")
            raise
        finally:
            session.close()
    
    def _execute_caption_generation(self, task: CaptionGenerationTask, 
                                   platform_connection: PlatformConnection) -> Dict[str, Any]:
        """
        Execute caption generation using existing service logic
        
        Args:
            task: The caption generation task
            platform_connection: The platform connection
            
        Returns:
            Dict containing generation results
        """
        try:
            # Create progress callback for real-time updates
            if self.rq_progress_tracker:
                # Use RQ-specific progress tracker
                progress_callback = self.rq_progress_tracker.create_progress_callback(task.id)
                
                # Set worker context
                job = get_current_job()
                if job:
                    self.rq_progress_tracker.set_worker_context(job.id)
            else:
                # Fallback to regular progress tracker
                progress_callback = self.progress_tracker.create_progress_callback(task.id)
            
            # Create platform adapter
            adapter = PlatformAwareCaptionAdapter(platform_connection)
            
            # Run caption generation in async context
            # Since we're in a worker thread, we need to create a new event loop
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                # No event loop in current thread, create a new one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            try:
                # Generate captions
                results = loop.run_until_complete(
                    adapter.generate_captions_for_user(task.settings, progress_callback)
                )
                
                # Set task ID in results
                results.task_id = task.id
                
                # Complete progress tracking
                if self.rq_progress_tracker:
                    self.rq_progress_tracker.complete_rq_progress(task.id, results)
                else:
                    self.progress_tracker.complete_progress(task.id, results)
                
                # Send completion notification
                self._send_completion_notification(task, results)
                
                # Return results summary
                return {
                    'captions_generated': results.captions_generated,
                    'images_processed': results.images_processed,
                    'processing_time': results.processing_time_seconds,
                    'success_rate': results.success_rate
                }
                
            finally:
                # Clean up event loop if we created it
                if loop.is_running():
                    loop.close()
                
        except Exception as e:
            logger.error(f"Caption generation failed for task {sanitize_for_log(task.id)}: {sanitize_for_log(str(e))}")
            
            # Send failure notification
            self._send_failure_notification(task, str(e))
            
            raise
    
    def _send_completion_notification(self, task: CaptionGenerationTask, results) -> None:
        """Send completion notification to user"""
        try:
            self.progress_tracker.send_caption_complete_notification(
                task.user_id,
                task.id,
                {
                    'captions_generated': results.captions_generated,
                    'images_processed': results.images_processed,
                    'processing_time': results.processing_time_seconds,
                    'success_rate': results.success_rate
                }
            )
        except Exception as e:
            logger.warning(f"Failed to send completion notification: {sanitize_for_log(str(e))}")
    
    def _send_failure_notification(self, task: CaptionGenerationTask, error_message: str) -> None:
        """Send failure notification to user"""
        try:
            # Send failure notification via progress tracker
            if self.rq_progress_tracker:
                self.rq_progress_tracker.fail_rq_progress(task.id, error_message)
            else:
                self.progress_tracker.send_task_failure_notification(
                    task.user_id,
                    task.id,
                    error_message
                )
        except Exception as e:
            logger.warning(f"Failed to send failure notification: {sanitize_for_log(str(e))}")
    
    def _clear_user_task_tracking(self, user_id: int) -> None:
        """Clear user task tracking (for Redis-based tracking)"""
        try:
            # This will be implemented when Redis user task tracking is available
            # For now, we rely on database status updates
            pass
        except Exception as e:
            logger.warning(f"Failed to clear user task tracking: {sanitize_for_log(str(e))}")
    
    def _clear_user_task_tracking_by_task_id(self, task_id: str) -> None:
        """Clear user task tracking by task ID"""
        try:
            # Get user ID from task and clear tracking
            task = self._get_task(task_id)
            if task:
                self._clear_user_task_tracking(task.user_id)
        except Exception as e:
            logger.warning(f"Failed to clear user task tracking by task ID: {sanitize_for_log(str(e))}")


class RQWorkerHealthMonitor:
    """Monitors RQ worker health and provides restart capabilities"""
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize RQ Worker Health Monitor
        
        Args:
            db_manager: Database manager instance
        """
        self.db_manager = db_manager
        self.health_check_interval = 60  # seconds
        self.max_processing_time = 3600  # 1 hour
    
    def check_worker_health(self) -> Dict[str, Any]:
        """
        Check worker health status
        
        Returns:
            Dict containing health status
        """
        health_status = {
            'healthy': True,
            'issues': [],
            'stuck_tasks': [],
            'recommendations': []
        }
        
        try:
            # Check for stuck tasks
            stuck_tasks = self._find_stuck_tasks()
            if stuck_tasks:
                health_status['healthy'] = False
                health_status['stuck_tasks'] = stuck_tasks
                health_status['issues'].append(f"Found {len(stuck_tasks)} stuck tasks")
                health_status['recommendations'].append("Consider restarting stuck tasks")
            
            # Check database connectivity
            if not self._check_database_connectivity():
                health_status['healthy'] = False
                health_status['issues'].append("Database connectivity issues")
                health_status['recommendations'].append("Check database connection")
            
            return health_status
            
        except Exception as e:
            logger.error(f"Health check failed: {sanitize_for_log(str(e))}")
            return {
                'healthy': False,
                'issues': [f"Health check error: {str(e)}"],
                'recommendations': ["Investigate health check failure"]
            }
    
    def _find_stuck_tasks(self) -> list:
        """Find tasks that have been running too long"""
        session = self.db_manager.get_session()
        try:
            from datetime import timedelta
            
            cutoff_time = datetime.now(timezone.utc) - timedelta(seconds=self.max_processing_time)
            
            stuck_tasks = session.query(CaptionGenerationTask).filter(
                CaptionGenerationTask.status == TaskStatus.RUNNING,
                CaptionGenerationTask.started_at < cutoff_time
            ).all()
            
            return [{'task_id': task.id, 'started_at': task.started_at.isoformat()} 
                   for task in stuck_tasks]
            
        except Exception as e:
            logger.error(f"Failed to find stuck tasks: {sanitize_for_log(str(e))}")
            return []
        finally:
            session.close()
    
    def _check_database_connectivity(self) -> bool:
        """Check if database is accessible"""
        try:
            session = self.db_manager.get_session()
            session.execute("SELECT 1")
            session.close()
            return True
        except Exception as e:
            logger.error(f"Database connectivity check failed: {sanitize_for_log(str(e))}")
            return False
    
    def restart_stuck_tasks(self) -> int:
        """
        Restart stuck tasks by resetting their status to QUEUED
        
        Returns:
            int: Number of tasks restarted
        """
        session = self.db_manager.get_session()
        try:
            from datetime import timedelta
            
            cutoff_time = datetime.now(timezone.utc) - timedelta(seconds=self.max_processing_time)
            
            stuck_tasks = session.query(CaptionGenerationTask).filter(
                CaptionGenerationTask.status == TaskStatus.RUNNING,
                CaptionGenerationTask.started_at < cutoff_time
            ).all()
            
            restarted_count = 0
            for task in stuck_tasks:
                task.status = TaskStatus.QUEUED
                task.started_at = None
                task.error_message = "Restarted due to timeout"
                restarted_count += 1
                
                logger.info(f"Restarted stuck task {sanitize_for_log(task.id)}")
            
            session.commit()
            
            if restarted_count > 0:
                logger.info(f"Restarted {restarted_count} stuck tasks")
            
            return restarted_count
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to restart stuck tasks: {sanitize_for_log(str(e))}")
            return 0
        finally:
            session.close()
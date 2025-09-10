# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
System Recovery Manager

Handles graceful system operations and recovery for caption generation tasks.
Provides startup recovery, shutdown handling, database connection recovery,
AI service outage detection, and concurrent operation handling.
"""

import logging
import asyncio
import signal
import threading
import time
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Callable
from contextlib import contextmanager
from sqlalchemy.exc import SQLAlchemyError, DisconnectionError, OperationalError
from sqlalchemy import text

from app.core.database.core.database_manager import DatabaseManager
from models import CaptionGenerationTask, TaskStatus, User
from app.services.task.core.task_queue_manager import TaskQueueManager
from progress_tracker import ProgressTracker
from app.core.security.core.security_utils import sanitize_for_log

logger = logging.getLogger(__name__)

class SystemRecoveryManager:
    """Manages system recovery and graceful operations"""
    
    def __init__(self, db_manager: DatabaseManager, task_queue_manager: TaskQueueManager, 
                 progress_tracker: ProgressTracker):
        self.db_manager = db_manager
        self.task_queue_manager = task_queue_manager
        self.progress_tracker = progress_tracker
        
        # Recovery state
        self._shutdown_requested = False
        self._recovery_in_progress = False
        self._active_tasks = set()
        self._recovery_lock = threading.Lock()
        
        # AI service monitoring
        self._ai_service_available = True
        self._last_ai_check = None
        self._ai_check_interval = 30  # seconds
        
        # Database connection monitoring
        self._db_connection_healthy = True
        self._last_db_check = None
        self._db_check_interval = 10  # seconds
        
        # Concurrent operation tracking
        self._operation_locks = {}
        self._operation_lock = threading.Lock()
        
        # Recovery callbacks
        self._startup_callbacks = []
        self._shutdown_callbacks = []
        self._recovery_callbacks = []
        
    def register_startup_callback(self, callback: Callable[[], None]):
        """Register a callback to be called during startup recovery"""
        self._startup_callbacks.append(callback)
    
    def register_shutdown_callback(self, callback: Callable[[], None]):
        """Register a callback to be called during shutdown"""
        self._shutdown_callbacks.append(callback)
    
    def register_recovery_callback(self, callback: Callable[[str], None]):
        """Register a callback to be called during recovery operations"""
        self._recovery_callbacks.append(callback)
    
    async def startup_recovery(self) -> Dict[str, Any]:
        """
        Perform system startup recovery to handle interrupted jobs
        
        Returns:
            Dict with recovery statistics
        """
        logger.info("Starting system startup recovery")
        recovery_stats = {
            'interrupted_tasks_found': 0,
            'tasks_recovered': 0,
            'tasks_failed': 0,
            'database_issues_fixed': 0,
            'recovery_time_seconds': 0
        }
        
        start_time = time.time()
        
        try:
            with self._recovery_lock:
                self._recovery_in_progress = True
                
                # Call startup callbacks
                for callback in self._startup_callbacks:
                    try:
                        callback()
                    except Exception as e:
                        logger.error(f"Startup callback failed: {sanitize_for_log(str(e))}")
                
                # Check database connectivity
                await self._check_database_connectivity()
                
                # Recover interrupted tasks
                interrupted_tasks = await self._find_interrupted_tasks()
                recovery_stats['interrupted_tasks_found'] = len(interrupted_tasks)
                
                for task in interrupted_tasks:
                    try:
                        await self._recover_interrupted_task(task)
                        recovery_stats['tasks_recovered'] += 1
                    except Exception as e:
                        logger.error(f"Failed to recover task {sanitize_for_log(task.id)}: {sanitize_for_log(str(e))}")
                        recovery_stats['tasks_failed'] += 1
                
                # Clean up orphaned progress sessions
                await self._cleanup_orphaned_progress()
                
                # Verify AI service availability
                await self._check_ai_service_availability()
                
                # Initialize system monitoring
                await self._initialize_system_monitoring()
                
                self._recovery_in_progress = False
                
        except Exception as e:
            logger.error(f"System startup recovery failed: {sanitize_for_log(str(e))}")
            self._recovery_in_progress = False
            raise
        
        recovery_stats['recovery_time_seconds'] = time.time() - start_time
        logger.info(f"System startup recovery completed: {recovery_stats}")
        
        return recovery_stats
    
    async def graceful_shutdown(self, timeout_seconds: int = 30) -> Dict[str, Any]:
        """
        Perform graceful shutdown that completes or safely cancels running jobs
        
        Args:
            timeout_seconds: Maximum time to wait for jobs to complete
            
        Returns:
            Dict with shutdown statistics
        """
        logger.info(f"Starting graceful shutdown with {timeout_seconds}s timeout")
        shutdown_stats = {
            'active_tasks_found': 0,
            'tasks_completed': 0,
            'tasks_cancelled': 0,
            'shutdown_time_seconds': 0
        }
        
        start_time = time.time()
        
        try:
            self._shutdown_requested = True
            
            # Call shutdown callbacks
            for callback in self._shutdown_callbacks:
                try:
                    callback()
                except Exception as e:
                    logger.error(f"Shutdown callback failed: {sanitize_for_log(str(e))}")
            
            # Find all active tasks
            active_tasks = await self._find_active_tasks()
            shutdown_stats['active_tasks_found'] = len(active_tasks)
            
            if not active_tasks:
                logger.info("No active tasks found, shutdown can proceed immediately")
                return shutdown_stats
            
            # Wait for tasks to complete or timeout
            logger.info(f"Waiting for {len(active_tasks)} active tasks to complete")
            
            end_time = time.time() + timeout_seconds
            while time.time() < end_time and active_tasks:
                # Check task completion
                completed_tasks = []
                for task in active_tasks:
                    current_status = self.task_queue_manager.get_task_status(task.id)
                    if current_status and current_status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                        completed_tasks.append(task)
                        shutdown_stats['tasks_completed'] += 1
                
                # Remove completed tasks
                for task in completed_tasks:
                    active_tasks.remove(task)
                
                if active_tasks:
                    await asyncio.sleep(1)
            
            # Cancel remaining tasks
            for task in active_tasks:
                try:
                    success = self.task_queue_manager.cancel_task(
                        task.id, 
                        reason="System shutdown"
                    )
                    if success:
                        shutdown_stats['tasks_cancelled'] += 1
                        logger.info(f"Cancelled task {sanitize_for_log(task.id)} for shutdown")
                except Exception as e:
                    logger.error(f"Failed to cancel task {sanitize_for_log(task.id)}: {sanitize_for_log(str(e))}")
            
            # Final cleanup
            await self._cleanup_system_resources()
            
        except Exception as e:
            logger.error(f"Graceful shutdown failed: {sanitize_for_log(str(e))}")
            raise
        
        shutdown_stats['shutdown_time_seconds'] = time.time() - start_time
        logger.info(f"Graceful shutdown completed: {shutdown_stats}")
        
        return shutdown_stats
    
    async def recover_database_connection(self) -> bool:
        """
        Implement database connection recovery for job processing continuity
        
        Returns:
            bool: True if recovery was successful
        """
        logger.info("Starting database connection recovery")
        
        try:
            # Test current connection
            if await self._test_database_connection():
                logger.info("Database connection is healthy, no recovery needed")
                self._db_connection_healthy = True
                return True
            
            logger.warning("Database connection issues detected, attempting recovery")
            self._db_connection_healthy = False
            
            # Attempt to recreate connection pool
            try:
                self.db_manager.dispose_engine()
                await asyncio.sleep(1)  # Brief pause
                
                # Test new connection
                if await self._test_database_connection():
                    logger.info("Database connection recovery successful")
                    self._db_connection_healthy = True
                    
                    # Call recovery callbacks
                    for callback in self._recovery_callbacks:
                        try:
                            callback("database_recovered")
                        except Exception as e:
                            logger.error(f"Recovery callback failed: {sanitize_for_log(str(e))}")
                    
                    return True
                
            except Exception as e:
                logger.error(f"Database connection recreation failed: {sanitize_for_log(str(e))}")
            
            # If we get here, recovery failed
            logger.error("Database connection recovery failed")
            return False
            
        except Exception as e:
            logger.error(f"Database connection recovery error: {sanitize_for_log(str(e))}")
            return False
    
    async def detect_ai_service_outage(self) -> bool:
        """
        Create AI service outage detection and automatic job failure handling
        
        Returns:
            bool: True if AI service is available, False if outage detected
        """
        try:
            # Check if we need to test AI service
            now = datetime.now(timezone.utc)
            if (self._last_ai_check and 
                (now - self._last_ai_check).total_seconds() < self._ai_check_interval):
                return self._ai_service_available
            
            # Test AI service availability
            from ollama_caption_generator import OllamaCaptionGenerator
            
            try:
                generator = OllamaCaptionGenerator()
                # Simple health check - this should be quick
                available = await generator.test_connection()
                
                if available != self._ai_service_available:
                    if available:
                        logger.info("AI service is now available")
                        # Call recovery callbacks
                        for callback in self._recovery_callbacks:
                            try:
                                callback("ai_service_recovered")
                            except Exception as e:
                                logger.error(f"Recovery callback failed: {sanitize_for_log(str(e))}")
                    else:
                        logger.warning("AI service outage detected")
                        await self._handle_ai_service_outage()
                
                self._ai_service_available = available
                self._last_ai_check = now
                
                return available
                
            except Exception as e:
                logger.error(f"AI service check failed: {sanitize_for_log(str(e))}")
                if self._ai_service_available:
                    logger.warning("AI service appears to be down")
                    await self._handle_ai_service_outage()
                
                self._ai_service_available = False
                self._last_ai_check = now
                return False
                
        except Exception as e:
            logger.error(f"AI service outage detection failed: {sanitize_for_log(str(e))}")
            return self._ai_service_available
    
    @contextmanager
    def concurrent_operation_lock(self, operation_key: str):
        """
        Add concurrent operation handling to prevent job conflicts and data corruption
        
        Args:
            operation_key: Unique key for the operation
        """
        with self._operation_lock:
            if operation_key in self._operation_locks:
                raise RuntimeError(f"Operation {operation_key} is already in progress")
            
            lock = threading.Lock()
            self._operation_locks[operation_key] = lock
        
        try:
            with lock:
                yield
        finally:
            with self._operation_lock:
                self._operation_locks.pop(operation_key, None)
    
    async def recover_job_state(self, task_id: str) -> bool:
        """
        Implement job state recovery after system restarts with proper status updates
        
        Args:
            task_id: The task ID to recover
            
        Returns:
            bool: True if recovery was successful
        """
        logger.info(f"Starting job state recovery for task {sanitize_for_log(task_id)}")
        
        try:
            # Get task from database
            task = self.task_queue_manager.get_task(task_id)
            if not task:
                logger.warning(f"Task {sanitize_for_log(task_id)} not found for recovery")
                return False
            
            # Determine recovery action based on task state
            if task.status == TaskStatus.RUNNING:
                # Task was running when system went down
                logger.info(f"Recovering running task {sanitize_for_log(task_id)}")
                
                # Check if task has been running too long (stuck)
                if task.started_at:
                    runtime = datetime.now(timezone.utc) - task.started_at
                    if runtime.total_seconds() > 3600:  # 1 hour threshold
                        logger.warning(f"Task {sanitize_for_log(task_id)} appears stuck, marking as failed")
                        success = self.task_queue_manager.complete_task(
                            task_id, 
                            success=False, 
                            error_message="Task failed due to system restart (stuck task recovery)"
                        )
                        return success
                
                # Reset to queued for retry
                logger.info(f"Resetting task {sanitize_for_log(task_id)} to queued for retry")
                with self.db_manager.get_session() as session:
                    db_task = session.query(CaptionGenerationTask).filter_by(id=task_id).first()
                    if db_task:
                        db_task.status = TaskStatus.QUEUED
                        db_task.started_at = None
                        db_task.current_step = "Queued for retry after system restart"
                        db_task.retry_count = (db_task.retry_count or 0) + 1
                        session.commit()
                        
                        # Update progress tracker
                        self.progress_tracker.update_progress(
                            task_id,
                            "Queued for retry",
                            0,
                            {"recovery": "System restart recovery", "retry_count": db_task.retry_count}
                        )
                        
                        return True
            
            elif task.status == TaskStatus.QUEUED:
                # Task was queued, should be fine
                logger.info(f"Task {sanitize_for_log(task_id)} was queued, no recovery needed")
                return True
            
            elif task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                # Task was already completed, no recovery needed
                logger.info(f"Task {sanitize_for_log(task_id)} was already completed, no recovery needed")
                return True
            
            else:
                logger.warning(f"Unknown task status for recovery: {task.status}")
                return False
                
        except Exception as e:
            logger.error(f"Job state recovery failed for task {sanitize_for_log(task_id)}: {sanitize_for_log(str(e))}")
            return False
    
    # Private helper methods
    
    async def _find_interrupted_tasks(self) -> List[CaptionGenerationTask]:
        """Find tasks that were interrupted by system shutdown"""
        try:
            with self.db_manager.get_session() as session:
                # Find tasks that were running when system went down
                interrupted_tasks = session.query(CaptionGenerationTask).filter(
                    CaptionGenerationTask.status == TaskStatus.RUNNING
                ).all()
                
                # Detach from session
                for task in interrupted_tasks:
                    session.expunge(task)
                
                return interrupted_tasks
                
        except SQLAlchemyError as e:
            logger.error(f"Failed to find interrupted tasks: {sanitize_for_log(str(e))}")
            return []
    
    async def _recover_interrupted_task(self, task: CaptionGenerationTask):
        """Recover a single interrupted task"""
        logger.info(f"Recovering interrupted task {sanitize_for_log(task.id)}")
        
        # Check if task should be retried or failed
        max_retries = task.max_retries or 3
        current_retries = task.retry_count or 0
        
        if current_retries >= max_retries:
            # Too many retries, mark as failed
            logger.warning(f"Task {sanitize_for_log(task.id)} exceeded max retries, marking as failed")
            self.task_queue_manager.complete_task(
                task.id,
                success=False,
                error_message=f"Task failed after {current_retries} retries due to system restarts"
            )
        else:
            # Reset to queued for retry
            await self.recover_job_state(task.id)
    
    async def _find_active_tasks(self) -> List[CaptionGenerationTask]:
        """Find all currently active tasks"""
        try:
            with self.db_manager.get_session() as session:
                active_tasks = session.query(CaptionGenerationTask).filter(
                    CaptionGenerationTask.status.in_([TaskStatus.QUEUED, TaskStatus.RUNNING])
                ).all()
                
                # Detach from session
                for task in active_tasks:
                    session.expunge(task)
                
                return active_tasks
                
        except SQLAlchemyError as e:
            logger.error(f"Failed to find active tasks: {sanitize_for_log(str(e))}")
            return []
    
    async def _cleanup_orphaned_progress(self):
        """Clean up orphaned progress tracking sessions"""
        try:
            # This would clean up Redis progress sessions that don't have corresponding tasks
            # Implementation depends on progress tracker internals
            logger.info("Cleaning up orphaned progress sessions")
            # TODO: Implement based on ProgressTracker implementation
            
        except Exception as e:
            logger.error(f"Failed to cleanup orphaned progress: {sanitize_for_log(str(e))}")
    
    async def _check_database_connectivity(self):
        """Check and ensure database connectivity"""
        if not await self._test_database_connection():
            logger.warning("Database connectivity issues detected during startup")
            await self.recover_database_connection()
    
    async def _test_database_connection(self) -> bool:
        """Test database connection health"""
        try:
            with self.db_manager.get_session() as session:
                # Simple query to test connection
                result = session.execute(text("SELECT 1")).fetchone()
                return result is not None
                
        except (SQLAlchemyError, DisconnectionError, OperationalError) as e:
            logger.error(f"Database connection test failed: {sanitize_for_log(str(e))}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error testing database connection: {sanitize_for_log(str(e))}")
            return False
    
    async def _check_ai_service_availability(self):
        """Check AI service availability during startup"""
        available = await self.detect_ai_service_outage()
        if not available:
            logger.warning("AI service not available during startup")
    
    async def _handle_ai_service_outage(self):
        """Handle AI service outage by failing running tasks"""
        try:
            # Find tasks that are currently running and depend on AI service
            with self.db_manager.get_session() as session:
                running_tasks = session.query(CaptionGenerationTask).filter(
                    CaptionGenerationTask.status == TaskStatus.RUNNING
                ).all()
                
                for task in running_tasks:
                    logger.info(f"Failing task {sanitize_for_log(task.id)} due to AI service outage")
                    self.task_queue_manager.complete_task(
                        task.id,
                        success=False,
                        error_message="AI service is currently unavailable. Please try again later."
                    )
                    
                    # Update progress
                    self.progress_tracker.update_progress(
                        task.id,
                        "Failed - AI service unavailable",
                        100,
                        {"error": "AI service outage detected"}
                    )
                    
        except Exception as e:
            logger.error(f"Failed to handle AI service outage: {sanitize_for_log(str(e))}")
    
    async def _initialize_system_monitoring(self):
        """Initialize ongoing system monitoring"""
        logger.info("Initializing system monitoring")
        # This would start background monitoring tasks
        # Implementation depends on monitoring requirements
    
    async def _cleanup_system_resources(self):
        """Clean up system resources during shutdown"""
        try:
            logger.info("Cleaning up system resources")
            
            # Close database connections
            if hasattr(self.db_manager, 'dispose_engine'):
                self.db_manager.dispose_engine()
            
            # Clean up any other resources
            # TODO: Add other resource cleanup as needed
            
        except Exception as e:
            logger.error(f"Failed to cleanup system resources: {sanitize_for_log(str(e))}")

# Global instance for signal handling
_recovery_manager = None

def initialize_system_recovery(db_manager: DatabaseManager, task_queue_manager: TaskQueueManager, 
                             progress_tracker: ProgressTracker) -> SystemRecoveryManager:
    """Initialize the global system recovery manager"""
    global _recovery_manager
    _recovery_manager = SystemRecoveryManager(db_manager, task_queue_manager, progress_tracker)
    
    # Register signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown")
        if _recovery_manager:
            asyncio.create_task(_recovery_manager.graceful_shutdown())
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    return _recovery_manager

def get_system_recovery_manager() -> Optional[SystemRecoveryManager]:
    """Get the global system recovery manager"""
    return _recovery_manager
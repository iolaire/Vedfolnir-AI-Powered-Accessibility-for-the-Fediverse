# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integrated RQ Worker

Runs RQ workers as daemon threads within Gunicorn processes with proper
Flask application context and database session management.
"""

import logging
import threading
import time
import uuid
from typing import List, Optional, Callable
import redis
from rq import Worker
from rq.exceptions import InvalidJobOperation
from flask import Flask

from app.core.database.core.database_manager import DatabaseManager
from app.core.security.core.security_utils import sanitize_for_log
from .worker_session_manager import WorkerSessionManager

logger = logging.getLogger(__name__)


class IntegratedRQWorker:
    """RQ Worker that runs as daemon thread within Gunicorn with Flask app context"""
    
    def __init__(self, queues: List[str], redis_connection: redis.Redis, 
                 app_context: Flask, db_manager: DatabaseManager, 
                 worker_id: Optional[str] = None):
        """
        Initialize IntegratedRQWorker
        
        Args:
            queues: List of queue names to process (in priority order)
            redis_connection: Redis connection instance
            app_context: Flask application instance for context
            db_manager: Database manager instance
            worker_id: Optional worker ID (generated if not provided)
        """
        self.queues = queues
        self.redis_connection = redis_connection
        self.app_context = app_context
        self.db_manager = db_manager
        self.worker_id = worker_id or self._generate_worker_id()
        
        # Initialize session manager
        self.session_manager = WorkerSessionManager(db_manager)
        
        # Worker state
        self.worker: Optional[Worker] = None
        self.thread: Optional[threading.Thread] = None
        self.running = False
        self.stop_requested = False
        
        # Coordination
        self.coordination_key = f"rq:active_workers:{self.worker_id}"
        self.coordination_ttl = 300  # 5 minutes
        
        # Callbacks
        self.job_started_callback: Optional[Callable] = None
        self.job_finished_callback: Optional[Callable] = None
        self.job_failed_callback: Optional[Callable] = None
        
        # Initialize worker
        self._initialize_worker()
    
    def _generate_worker_id(self) -> str:
        """Generate unique worker ID"""
        return f"worker-{uuid.uuid4().hex[:8]}-{int(time.time())}"
    
    def _initialize_worker(self) -> None:
        """Initialize RQ Worker instance"""
        try:
            self.worker = Worker(
                queues=self.queues,
                connection=self.redis_connection,
                name=self.worker_id
            )
            
            # Set up worker callbacks
            self.worker.push_exc_handler(self._handle_worker_exception)
            
            logger.info(f"Initialized RQ worker {self.worker_id} for queues: {self.queues}")
            
        except Exception as e:
            logger.error(f"Failed to initialize RQ worker {self.worker_id}: {sanitize_for_log(str(e))}")
            raise
    
    def start(self) -> bool:
        """
        Start worker in background thread with Flask app context
        
        Returns:
            bool: True if worker started successfully
        """
        if self.running:
            logger.warning(f"Worker {self.worker_id} is already running")
            return False
        
        try:
            # Register worker coordination
            self._register_worker_coordination()
            
            # Start worker thread
            self.thread = threading.Thread(
                target=self._worker_loop,
                daemon=True,
                name=f"RQWorker-{self.worker_id}"
            )
            self.thread.start()
            self.running = True
            
            logger.info(f"Started RQ worker {self.worker_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start RQ worker {self.worker_id}: {sanitize_for_log(str(e))}")
            self._cleanup_worker_coordination()
            return False
    
    def stop(self, timeout: int = 30) -> bool:
        """
        Gracefully stop worker with proper cleanup
        
        Args:
            timeout: Maximum time to wait for graceful shutdown
            
        Returns:
            bool: True if worker stopped gracefully
        """
        if not self.running:
            logger.info(f"Worker {self.worker_id} is not running")
            return True
        
        try:
            logger.info(f"Stopping RQ worker {self.worker_id}")
            
            # Signal worker to stop
            self.stop_requested = True
            if self.worker:
                self.worker.request_stop()
            
            # Wait for thread to finish
            if self.thread and self.thread.is_alive():
                self.thread.join(timeout=timeout)
                
                if self.thread.is_alive():
                    logger.warning(f"Worker {self.worker_id} did not stop gracefully within {timeout}s")
                    return False
            
            self.running = False
            logger.info(f"Successfully stopped RQ worker {self.worker_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping RQ worker {self.worker_id}: {sanitize_for_log(str(e))}")
            return False
        finally:
            # Always clean up resources
            self._cleanup_resources()
    
    def _worker_loop(self) -> None:
        """Main worker loop with Flask app context and proper session management"""
        try:
            # Register this worker as active
            self._update_worker_coordination()
            
            with self.app_context.app_context():
                logger.info(f"Worker {self.worker_id} started processing with Flask context")
                
                # Set up job wrapper for session management
                original_perform_job = self.worker.perform_job
                self.worker.perform_job = self._wrapped_perform_job
                
                # Start worker with scheduler support
                self.worker.work(with_scheduler=True)
                
        except Exception as e:
            logger.error(f"Worker {self.worker_id} encountered error: {sanitize_for_log(str(e))}")
        finally:
            # Clean up coordination key and resources
            self._cleanup_worker_coordination()
            self._cleanup_resources()
            logger.info(f"Worker {self.worker_id} loop ended")
    
    def _wrapped_perform_job(self, job, queue):
        """Wrapper for job execution with session management"""
        job_id = job.id if job else "unknown"
        
        try:
            # Callback: job started
            if self.job_started_callback:
                self.job_started_callback(job_id, self.worker_id)
            
            logger.info(f"Worker {self.worker_id} starting job {sanitize_for_log(job_id)}")
            
            # Execute job with session management
            result = self._execute_job_with_session_management(job, queue)
            
            # Callback: job finished
            if self.job_finished_callback:
                self.job_finished_callback(job_id, self.worker_id, True)
            
            logger.info(f"Worker {self.worker_id} completed job {sanitize_for_log(job_id)}")
            return result
            
        except Exception as e:
            logger.error(f"Worker {self.worker_id} failed job {sanitize_for_log(job_id)}: {sanitize_for_log(str(e))}")
            
            # Callback: job failed
            if self.job_failed_callback:
                self.job_failed_callback(job_id, self.worker_id, str(e))
            
            raise
        finally:
            # Always clean up session after job
            self.session_manager.ensure_session_cleanup()
    
    def _execute_job_with_session_management(self, job, queue):
        """Execute job with proper session lifecycle management"""
        try:
            # Get fresh session for this job
            session = self.session_manager.get_session()
            
            # Execute the original job
            from rq.worker import Worker
            result = Worker.perform_job(self.worker, job, queue)
            
            # Commit session if job succeeded
            self.session_manager.commit_session()
            
            return result
            
        except Exception as e:
            # Rollback session on error
            self.session_manager.rollback_session()
            raise
        finally:
            # Always close session
            self.session_manager.close_session()
    
    def _handle_worker_exception(self, job, exc_type, exc_value, traceback):
        """Handle worker exceptions"""
        job_id = job.id if job else "unknown"
        logger.error(f"Worker {self.worker_id} exception in job {sanitize_for_log(job_id)}: {sanitize_for_log(str(exc_value))}")
        
        # Ensure session cleanup on exception
        self.session_manager.ensure_session_cleanup()
        
        # Return False to use default exception handling
        return False
    
    def _register_worker_coordination(self) -> None:
        """Register this worker as active in Redis"""
        try:
            worker_info = {
                'worker_id': self.worker_id,
                'queues': self.queues,
                'started_at': int(time.time()),
                'pid': threading.get_ident()
            }
            
            self.redis_connection.hset(
                self.coordination_key,
                mapping=worker_info
            )
            self.redis_connection.expire(self.coordination_key, self.coordination_ttl)
            
            logger.debug(f"Registered worker coordination for {self.worker_id}")
            
        except Exception as e:
            logger.error(f"Failed to register worker coordination: {sanitize_for_log(str(e))}")
    
    def _update_worker_coordination(self) -> None:
        """Update worker coordination TTL"""
        try:
            self.redis_connection.expire(self.coordination_key, self.coordination_ttl)
        except Exception as e:
            logger.debug(f"Failed to update worker coordination: {sanitize_for_log(str(e))}")
    
    def _cleanup_worker_coordination(self) -> None:
        """Clean up worker coordination key"""
        try:
            self.redis_connection.delete(self.coordination_key)
            logger.debug(f"Cleaned up worker coordination for {self.worker_id}")
        except Exception as e:
            logger.debug(f"Failed to cleanup worker coordination: {sanitize_for_log(str(e))}")
    
    def _cleanup_resources(self) -> None:
        """Clean up all worker resources"""
        try:
            # Clean up session manager
            self.session_manager.ensure_session_cleanup()
            
            # Reset worker state
            self.running = False
            self.stop_requested = False
            
            logger.debug(f"Cleaned up resources for worker {self.worker_id}")
            
        except Exception as e:
            logger.error(f"Error during resource cleanup: {sanitize_for_log(str(e))}")
    
    def is_running(self) -> bool:
        """Check if worker is running"""
        return self.running and self.thread and self.thread.is_alive()
    
    def get_worker_info(self) -> dict:
        """Get worker information"""
        info = {
            'worker_id': self.worker_id,
            'queues': self.queues,
            'running': self.running,
            'stop_requested': self.stop_requested,
            'thread_alive': self.thread.is_alive() if self.thread else False,
            'coordination_key': self.coordination_key
        }
        
        # Add session manager info
        info.update(self.session_manager.get_session_info())
        
        # Add worker stats if available
        if self.worker:
            try:
                info.update({
                    'worker_name': self.worker.name,
                    'current_job': self.worker.get_current_job_id(),
                    'successful_job_count': self.worker.successful_job_count,
                    'failed_job_count': self.worker.failed_job_count,
                    'total_working_time': self.worker.total_working_time
                })
            except Exception as e:
                info['worker_stats_error'] = str(e)
        
        return info
    
    def set_job_callbacks(self, started: Optional[Callable] = None,
                         finished: Optional[Callable] = None,
                         failed: Optional[Callable] = None) -> None:
        """Set job lifecycle callbacks"""
        self.job_started_callback = started
        self.job_finished_callback = finished
        self.job_failed_callback = failed
    
    def restart(self, timeout: int = 30) -> bool:
        """Restart the worker"""
        logger.info(f"Restarting worker {self.worker_id}")
        
        if not self.stop(timeout):
            logger.error(f"Failed to stop worker {self.worker_id} for restart")
            return False
        
        # Wait a moment before restarting
        time.sleep(1)
        
        # Reinitialize worker
        self._initialize_worker()
        
        return self.start()
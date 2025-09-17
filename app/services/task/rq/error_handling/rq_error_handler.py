# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
RQ Error Handler

Comprehensive error handling system for RQ operations with automatic retry logic,
error categorization, and proper database session management.
"""

import logging
import time
import traceback
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Type, Callable
from enum import Enum
import redis
from rq import Queue, Job
from rq.exceptions import NoSuchJobError, WorkerLostJobError
from sqlalchemy.exc import SQLAlchemyError, DisconnectionError, TimeoutError as SQLTimeoutError

from app.core.database.core.database_manager import DatabaseManager
from app.core.security.core.security_utils import sanitize_for_log
from models import CaptionGenerationTask, TaskStatus
from .rq_session_manager import RQSessionManager
from .dead_letter_queue import DeadLetterQueue

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """Categories of errors for different handling strategies"""
    TRANSIENT_NETWORK = "transient_network"
    REDIS_CONNECTION = "redis_connection"
    DATABASE_CONNECTION = "database_connection"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    TASK_VALIDATION = "task_validation"
    PROCESSING_ERROR = "processing_error"
    SECURITY_ERROR = "security_error"
    SYSTEM_ERROR = "system_error"


class RetryStrategy(Enum):
    """Retry strategies for different error types"""
    IMMEDIATE = "immediate"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    NO_RETRY = "no_retry"


class RQErrorHandler:
    """Comprehensive error handling system for RQ operations"""
    
    def __init__(self, db_manager: DatabaseManager, redis_connection: redis.Redis, 
                 config: Optional[Dict[str, Any]] = None):
        """
        Initialize RQ Error Handler
        
        Args:
            db_manager: Database manager instance
            redis_connection: Redis connection for RQ operations
            config: Optional configuration for error handling
        """
        self.db_manager = db_manager
        self.redis_connection = redis_connection
        self.config = config or {}
        
        # Initialize session manager for proper database session lifecycle
        self.session_manager = RQSessionManager(db_manager)
        
        # Initialize dead letter queue
        self.dead_letter_queue = DeadLetterQueue(redis_connection, db_manager)
        
        # Error handling configuration
        self.max_retries = self.config.get('max_retries', 3)
        self.base_delay = self.config.get('base_delay', 60)  # seconds
        self.max_delay = self.config.get('max_delay', 3600)  # seconds
        self.exponential_base = self.config.get('exponential_base', 2)
        
        # Error categorization mapping
        self.error_categories = self._initialize_error_categories()
        
        # Retry strategies mapping
        self.retry_strategies = self._initialize_retry_strategies()
        
        logger.info("RQ Error Handler initialized with comprehensive error handling")
    
    def _initialize_error_categories(self) -> Dict[Type[Exception], ErrorCategory]:
        """Initialize error categorization mapping"""
        return {
            # Network and connection errors
            redis.ConnectionError: ErrorCategory.REDIS_CONNECTION,
            redis.TimeoutError: ErrorCategory.TRANSIENT_NETWORK,
            redis.BusyLoadingError: ErrorCategory.TRANSIENT_NETWORK,
            
            # Database errors
            DisconnectionError: ErrorCategory.DATABASE_CONNECTION,
            SQLTimeoutError: ErrorCategory.DATABASE_CONNECTION,
            SQLAlchemyError: ErrorCategory.DATABASE_CONNECTION,
            
            # RQ specific errors
            WorkerLostJobError: ErrorCategory.SYSTEM_ERROR,
            NoSuchJobError: ErrorCategory.TASK_VALIDATION,
            
            # Resource errors
            MemoryError: ErrorCategory.RESOURCE_EXHAUSTION,
            OSError: ErrorCategory.SYSTEM_ERROR,
            
            # Security errors
            PermissionError: ErrorCategory.SECURITY_ERROR,
            ValueError: ErrorCategory.TASK_VALIDATION,
            
            # General processing errors
            Exception: ErrorCategory.PROCESSING_ERROR
        }
    
    def _initialize_retry_strategies(self) -> Dict[ErrorCategory, RetryStrategy]:
        """Initialize retry strategies for different error categories"""
        return {
            ErrorCategory.TRANSIENT_NETWORK: RetryStrategy.EXPONENTIAL_BACKOFF,
            ErrorCategory.REDIS_CONNECTION: RetryStrategy.EXPONENTIAL_BACKOFF,
            ErrorCategory.DATABASE_CONNECTION: RetryStrategy.EXPONENTIAL_BACKOFF,
            ErrorCategory.RESOURCE_EXHAUSTION: RetryStrategy.LINEAR_BACKOFF,
            ErrorCategory.TASK_VALIDATION: RetryStrategy.NO_RETRY,
            ErrorCategory.PROCESSING_ERROR: RetryStrategy.EXPONENTIAL_BACKOFF,
            ErrorCategory.SECURITY_ERROR: RetryStrategy.NO_RETRY,
            ErrorCategory.SYSTEM_ERROR: RetryStrategy.EXPONENTIAL_BACKOFF
        }
    
    def handle_job_error(self, job: Job, exception: Exception, traceback_str: str) -> bool:
        """
        Handle job error with automatic retry logic and proper session management
        
        Args:
            job: The RQ job that failed
            exception: The exception that occurred
            traceback_str: The traceback string
            
        Returns:
            bool: True if job should be retried, False if it should fail permanently
        """
        task_id = job.id
        
        try:
            # Ensure proper database session cleanup
            with self.session_manager.get_session_context() as session:
                # Categorize the error
                error_category = self._categorize_error(exception)
                
                # Get retry strategy
                retry_strategy = self.retry_strategies.get(error_category, RetryStrategy.NO_RETRY)
                
                # Get current retry count
                retry_count = self._get_retry_count(job)
                
                # Log error with sanitized information
                sanitized_error = self._sanitize_error_message(str(exception), task_id)
                
                logger.error(
                    f"Job {sanitize_for_log(task_id)} failed with {error_category.value} error "
                    f"(attempt {retry_count + 1}/{self.max_retries + 1}): {sanitized_error}"
                )
                
                # Store error information
                self._store_error_information(session, task_id, exception, error_category, retry_count)
                
                # Determine if retry should be attempted
                should_retry = self._should_retry(retry_strategy, retry_count, exception)
                
                if should_retry:
                    # Calculate retry delay
                    delay = self._calculate_retry_delay(retry_strategy, retry_count)
                    
                    # Schedule retry
                    self._schedule_retry(job, delay, retry_count + 1)
                    
                    logger.info(
                        f"Scheduling retry for job {sanitize_for_log(task_id)} "
                        f"in {delay} seconds (attempt {retry_count + 2})"
                    )
                    
                    return True
                else:
                    # Move to dead letter queue
                    self._handle_permanent_failure(session, job, exception, error_category, retry_count)
                    
                    logger.error(
                        f"Job {sanitize_for_log(task_id)} permanently failed after "
                        f"{retry_count + 1} attempts with {error_category.value} error"
                    )
                    
                    return False
                    
        except Exception as handler_error:
            logger.error(
                f"Error handler itself failed for job {sanitize_for_log(task_id)}: "
                f"{sanitize_for_log(str(handler_error))}"
            )
            
            # Ensure session cleanup even if handler fails
            try:
                self.session_manager.cleanup_session()
            except Exception as cleanup_error:
                logger.error(f"Session cleanup failed: {sanitize_for_log(str(cleanup_error))}")
            
            return False
    
    def _categorize_error(self, exception: Exception) -> ErrorCategory:
        """Categorize error based on exception type and message"""
        exception_type = type(exception)
        
        # Check direct type mapping
        for error_type, category in self.error_categories.items():
            if issubclass(exception_type, error_type):
                return category
        
        # Check error message for specific patterns
        error_message = str(exception).lower()
        
        if any(keyword in error_message for keyword in ['connection', 'timeout', 'network']):
            return ErrorCategory.TRANSIENT_NETWORK
        elif any(keyword in error_message for keyword in ['memory', 'resource', 'limit']):
            return ErrorCategory.RESOURCE_EXHAUSTION
        elif any(keyword in error_message for keyword in ['permission', 'access', 'unauthorized']):
            return ErrorCategory.SECURITY_ERROR
        elif any(keyword in error_message for keyword in ['validation', 'invalid', 'format']):
            return ErrorCategory.TASK_VALIDATION
        
        # Default to processing error
        return ErrorCategory.PROCESSING_ERROR
    
    def _get_retry_count(self, job: Job) -> int:
        """Get current retry count for job"""
        try:
            return job.meta.get('retry_count', 0)
        except Exception:
            return 0
    
    def _should_retry(self, retry_strategy: RetryStrategy, retry_count: int, exception: Exception) -> bool:
        """Determine if job should be retried based on strategy and conditions"""
        if retry_strategy == RetryStrategy.NO_RETRY:
            return False
        
        if retry_count >= self.max_retries:
            return False
        
        # Additional conditions based on error type
        if isinstance(exception, (PermissionError, ValueError)):
            # Don't retry security or validation errors
            return False
        
        if isinstance(exception, MemoryError):
            # Only retry memory errors with longer delays
            return retry_count < 2
        
        return True
    
    def _calculate_retry_delay(self, retry_strategy: RetryStrategy, retry_count: int) -> int:
        """Calculate delay before retry based on strategy"""
        if retry_strategy == RetryStrategy.IMMEDIATE:
            return 0
        elif retry_strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = self.base_delay * (retry_count + 1)
        elif retry_strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = self.base_delay * (self.exponential_base ** retry_count)
        else:
            delay = self.base_delay
        
        # Cap at maximum delay
        return min(delay, self.max_delay)
    
    def _schedule_retry(self, job: Job, delay: int, retry_count: int) -> None:
        """Schedule job retry with delay"""
        try:
            # Update job metadata
            job.meta['retry_count'] = retry_count
            job.meta['last_retry_at'] = datetime.now(timezone.utc).isoformat()
            job.save_meta()
            
            # Requeue job with delay
            job.retry(delay=delay)
            
        except Exception as e:
            logger.error(f"Failed to schedule retry for job {job.id}: {sanitize_for_log(str(e))}")
            raise
    
    def _store_error_information(self, session, task_id: str, exception: Exception, 
                                error_category: ErrorCategory, retry_count: int) -> None:
        """Store error information in database"""
        try:
            # Get task from database
            task = session.query(CaptionGenerationTask).filter_by(id=task_id).first()
            
            if task:
                # Update error information
                error_info = {
                    'error_type': type(exception).__name__,
                    'error_category': error_category.value,
                    'retry_count': retry_count,
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'sanitized_message': self._sanitize_error_message(str(exception), task_id)
                }
                
                # Store in task error_message field (JSON format)
                import json
                if task.error_message:
                    try:
                        existing_errors = json.loads(task.error_message)
                        if not isinstance(existing_errors, list):
                            existing_errors = [existing_errors]
                    except (json.JSONDecodeError, TypeError):
                        existing_errors = []
                else:
                    existing_errors = []
                
                existing_errors.append(error_info)
                task.error_message = json.dumps(existing_errors)
                
                session.commit()
                
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to store error information: {sanitize_for_log(str(e))}")
    
    def _handle_permanent_failure(self, session, job: Job, exception: Exception, 
                                 error_category: ErrorCategory, retry_count: int) -> None:
        """Handle permanent job failure"""
        task_id = job.id
        
        try:
            # Update task status to FAILED
            task = session.query(CaptionGenerationTask).filter_by(id=task_id).first()
            
            if task:
                task.status = TaskStatus.FAILED
                task.completed_at = datetime.now(timezone.utc)
                
                # Add final error information
                final_error = {
                    'final_failure': True,
                    'error_type': type(exception).__name__,
                    'error_category': error_category.value,
                    'total_retries': retry_count,
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'sanitized_message': self._sanitize_error_message(str(exception), task_id)
                }
                
                import json
                if task.error_message:
                    try:
                        existing_errors = json.loads(task.error_message)
                        if not isinstance(existing_errors, list):
                            existing_errors = [existing_errors]
                    except (json.JSONDecodeError, TypeError):
                        existing_errors = []
                else:
                    existing_errors = []
                
                existing_errors.append(final_error)
                task.error_message = json.dumps(existing_errors)
                
                session.commit()
            
            # Move job to dead letter queue
            self.dead_letter_queue.add_failed_job(job, exception, error_category, retry_count)
            
            # Clear user task tracking
            self._clear_user_task_tracking(task_id)
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to handle permanent failure: {sanitize_for_log(str(e))}")
    
    def _sanitize_error_message(self, error_message: str, task_id: str) -> str:
        """Sanitize error message to prevent information leakage"""
        try:
            # Remove sensitive information patterns
            sanitized = error_message
            
            # Remove file paths
            import re
            sanitized = re.sub(r'/[^\s]*', '[PATH_REMOVED]', sanitized)
            
            # Remove IP addresses
            sanitized = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '[IP_REMOVED]', sanitized)
            
            # Remove potential passwords or tokens
            sanitized = re.sub(r'(password|token|key|secret)[\s=:]+[^\s]+', r'\1=[REDACTED]', sanitized, flags=re.IGNORECASE)
            
            # Limit length
            if len(sanitized) > 500:
                sanitized = sanitized[:497] + "..."
            
            return sanitized
            
        except Exception:
            return f"Error processing task {task_id} - details sanitized"
    
    def _clear_user_task_tracking(self, task_id: str) -> None:
        """Clear user task tracking for failed task"""
        try:
            # This will integrate with UserTaskTracker when available
            # For now, we rely on database status updates
            pass
        except Exception as e:
            logger.warning(f"Failed to clear user task tracking: {sanitize_for_log(str(e))}")
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics for monitoring"""
        try:
            with self.session_manager.get_session_context() as session:
                # Get failed tasks from last 24 hours
                cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
                
                failed_tasks = session.query(CaptionGenerationTask).filter(
                    CaptionGenerationTask.status == TaskStatus.FAILED,
                    CaptionGenerationTask.completed_at >= cutoff_time
                ).all()
                
                # Analyze error patterns
                error_stats = {
                    'total_failures': len(failed_tasks),
                    'error_categories': {},
                    'retry_statistics': {
                        'total_retries': 0,
                        'average_retries': 0,
                        'max_retries': 0
                    },
                    'dead_letter_queue_size': self.dead_letter_queue.get_size()
                }
                
                total_retries = 0
                
                for task in failed_tasks:
                    if task.error_message:
                        try:
                            import json
                            errors = json.loads(task.error_message)
                            if isinstance(errors, list):
                                for error in errors:
                                    if isinstance(error, dict):
                                        category = error.get('error_category', 'unknown')
                                        error_stats['error_categories'][category] = \
                                            error_stats['error_categories'].get(category, 0) + 1
                                        
                                        retry_count = error.get('retry_count', 0)
                                        total_retries += retry_count
                                        error_stats['retry_statistics']['max_retries'] = \
                                            max(error_stats['retry_statistics']['max_retries'], retry_count)
                        except (json.JSONDecodeError, TypeError):
                            pass
                
                # Calculate averages
                if failed_tasks:
                    error_stats['retry_statistics']['total_retries'] = total_retries
                    error_stats['retry_statistics']['average_retries'] = total_retries / len(failed_tasks)
                
                return error_stats
                
        except Exception as e:
            logger.error(f"Failed to get error statistics: {sanitize_for_log(str(e))}")
            return {'error': 'Failed to retrieve error statistics'}
    
    def cleanup_old_error_data(self, older_than_days: int = 7) -> int:
        """Clean up old error data to prevent database bloat"""
        try:
            with self.session_manager.get_session_context() as session:
                cutoff_time = datetime.now(timezone.utc) - timedelta(days=older_than_days)
                
                # Clean up old failed tasks
                old_failed_tasks = session.query(CaptionGenerationTask).filter(
                    CaptionGenerationTask.status == TaskStatus.FAILED,
                    CaptionGenerationTask.completed_at < cutoff_time
                ).all()
                
                cleaned_count = len(old_failed_tasks)
                
                for task in old_failed_tasks:
                    session.delete(task)
                
                session.commit()
                
                # Clean up dead letter queue
                dlq_cleaned = self.dead_letter_queue.cleanup_old_entries(older_than_days)
                
                logger.info(f"Cleaned up {cleaned_count} old failed tasks and {dlq_cleaned} DLQ entries")
                return cleaned_count + dlq_cleaned
                
        except Exception as e:
            logger.error(f"Failed to cleanup old error data: {sanitize_for_log(str(e))}")
            return 0
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get error handler health status"""
        try:
            stats = self.get_error_statistics()
            
            health_status = {
                'healthy': True,
                'issues': [],
                'error_rate': 0,
                'dead_letter_queue_size': stats.get('dead_letter_queue_size', 0),
                'session_manager_healthy': self.session_manager.is_healthy()
            }
            
            # Check error rate
            total_failures = stats.get('total_failures', 0)
            if total_failures > 10:  # More than 10 failures in 24 hours
                health_status['healthy'] = False
                health_status['issues'].append(f"High error rate: {total_failures} failures in 24 hours")
                health_status['error_rate'] = total_failures
            
            # Check dead letter queue size
            dlq_size = stats.get('dead_letter_queue_size', 0)
            if dlq_size > 50:  # More than 50 items in DLQ
                health_status['healthy'] = False
                health_status['issues'].append(f"Dead letter queue size too large: {dlq_size}")
            
            return health_status
            
        except Exception as e:
            return {
                'healthy': False,
                'issues': [f"Health check failed: {str(e)}"],
                'error': str(e)
            }
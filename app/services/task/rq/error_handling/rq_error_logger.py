# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
RQ Error Logger

Detailed error logging system for all RQ operations with structured logging,
error correlation, and comprehensive error reporting capabilities.
"""

import logging
import json
import traceback
import threading
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from enum import Enum
import redis
from rq import Job, get_current_job

from app.core.database.core.database_manager import DatabaseManager
from app.core.security.core.security_utils import sanitize_for_log
from .rq_error_handler import ErrorCategory

logger = logging.getLogger(__name__)


class LogLevel(Enum):
    """Log levels for RQ operations"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class RQErrorLogger:
    """Comprehensive error logging system for RQ operations"""
    
    def __init__(self, db_manager: DatabaseManager, redis_connection: redis.Redis,
                 config: Optional[Dict[str, Any]] = None):
        """
        Initialize RQ Error Logger
        
        Args:
            db_manager: Database manager instance
            redis_connection: Redis connection for log storage
            config: Optional configuration for logging
        """
        self.db_manager = db_manager
        self.redis_connection = redis_connection
        self.config = config or {}
        
        # Logging configuration
        self.log_retention_days = self.config.get('log_retention_days', 30)
        self.max_log_entries = self.config.get('max_log_entries', 10000)
        self.enable_detailed_logging = self.config.get('enable_detailed_logging', True)
        self.enable_performance_logging = self.config.get('enable_performance_logging', True)
        
        # Redis keys for log storage
        self.error_log_key = "rq:error_logs"
        self.performance_log_key = "rq:performance_logs"
        self.correlation_key = "rq:error_correlation"
        
        # Thread-local storage for correlation IDs
        self._local = threading.local()
        
        # Initialize structured logger
        self._setup_structured_logger()
        
        logger.info("RQ Error Logger initialized with comprehensive logging")
    
    def _setup_structured_logger(self) -> None:
        """Setup structured logging for RQ operations"""
        # Create RQ-specific logger
        self.rq_logger = logging.getLogger('rq_operations')
        self.rq_logger.setLevel(logging.DEBUG)
        
        # Create formatter for structured logging
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(correlation_id)s - %(message)s'
        )
        
        # Add handler if not already present
        if not self.rq_logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(formatter)
            self.rq_logger.addHandler(handler)
    
    def log_job_start(self, job: Job, worker_info: Optional[Dict[str, Any]] = None) -> str:
        """
        Log job start with correlation ID
        
        Args:
            job: The RQ job starting
            worker_info: Optional worker information
            
        Returns:
            str: Correlation ID for tracking
        """
        correlation_id = self._generate_correlation_id(job.id)
        
        try:
            log_entry = {
                'event_type': 'job_start',
                'job_id': job.id,
                'correlation_id': correlation_id,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'queue_name': getattr(job, 'origin', 'unknown'),
                'function_name': getattr(job, 'func_name', 'unknown'),
                'worker_info': worker_info or {},
                'job_args': self._sanitize_job_args(getattr(job, 'args', [])),
                'job_kwargs': self._sanitize_job_kwargs(getattr(job, 'kwargs', {})),
                'timeout': getattr(job, 'timeout', None),
                'created_at': job.created_at.isoformat() if hasattr(job, 'created_at') and job.created_at else None
            }
            
            # Log to structured logger
            self._log_structured(LogLevel.INFO, "Job started", log_entry, correlation_id)
            
            # Store in Redis for correlation
            self._store_log_entry(self.performance_log_key, log_entry)
            
            # Store correlation mapping
            self._store_correlation_mapping(correlation_id, job.id)
            
            return correlation_id
            
        except Exception as e:
            logger.error(f"Failed to log job start: {sanitize_for_log(str(e))}")
            return correlation_id
    
    def log_job_success(self, job: Job, result: Any, processing_time: float,
                       correlation_id: Optional[str] = None) -> None:
        """
        Log successful job completion
        
        Args:
            job: The completed job
            result: Job result
            processing_time: Time taken to process job
            correlation_id: Optional correlation ID
        """
        if not correlation_id:
            correlation_id = self._get_correlation_id(job.id)
        
        try:
            log_entry = {
                'event_type': 'job_success',
                'job_id': job.id,
                'correlation_id': correlation_id,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'processing_time': processing_time,
                'result_summary': self._summarize_result(result),
                'queue_name': getattr(job, 'origin', 'unknown'),
                'worker_name': getattr(job, 'worker_name', 'unknown')
            }
            
            # Log to structured logger
            self._log_structured(
                LogLevel.INFO, 
                f"Job completed successfully in {processing_time:.2f}s", 
                log_entry, 
                correlation_id
            )
            
            # Store performance metrics
            if self.enable_performance_logging:
                self._store_log_entry(self.performance_log_key, log_entry)
            
        except Exception as e:
            logger.error(f"Failed to log job success: {sanitize_for_log(str(e))}")
    
    def log_job_error(self, job: Job, exception: Exception, error_category: ErrorCategory,
                     retry_count: int, correlation_id: Optional[str] = None) -> None:
        """
        Log job error with detailed information
        
        Args:
            job: The failed job
            exception: The exception that occurred
            error_category: Category of the error
            retry_count: Current retry count
            correlation_id: Optional correlation ID
        """
        if not correlation_id:
            correlation_id = self._get_correlation_id(job.id)
        
        try:
            # Get detailed error information
            error_details = self._extract_error_details(exception)
            
            log_entry = {
                'event_type': 'job_error',
                'job_id': job.id,
                'correlation_id': correlation_id,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'error_type': type(exception).__name__,
                'error_category': error_category.value,
                'error_message': self._sanitize_error_message(str(exception)),
                'error_details': error_details,
                'retry_count': retry_count,
                'queue_name': getattr(job, 'origin', 'unknown'),
                'worker_name': getattr(job, 'worker_name', 'unknown'),
                'job_function': getattr(job, 'func_name', 'unknown'),
                'stack_trace': self._sanitize_stack_trace(traceback.format_exc())
            }
            
            # Determine log level based on error category
            log_level = self._get_log_level_for_error(error_category, retry_count)
            
            # Log to structured logger
            self._log_structured(
                log_level,
                f"Job failed with {error_category.value} error (retry {retry_count})",
                log_entry,
                correlation_id
            )
            
            # Store in error log
            self._store_log_entry(self.error_log_key, log_entry)
            
            # Update error correlation data
            self._update_error_correlation(error_category, error_details)
            
        except Exception as e:
            logger.error(f"Failed to log job error: {sanitize_for_log(str(e))}")
    
    def log_job_retry(self, job: Job, retry_count: int, delay: int,
                     correlation_id: Optional[str] = None) -> None:
        """
        Log job retry attempt
        
        Args:
            job: The job being retried
            retry_count: Current retry count
            delay: Delay before retry
            correlation_id: Optional correlation ID
        """
        if not correlation_id:
            correlation_id = self._get_correlation_id(job.id)
        
        try:
            log_entry = {
                'event_type': 'job_retry',
                'job_id': job.id,
                'correlation_id': correlation_id,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'retry_count': retry_count,
                'retry_delay': delay,
                'queue_name': getattr(job, 'origin', 'unknown')
            }
            
            # Log to structured logger
            self._log_structured(
                LogLevel.WARNING,
                f"Job retry scheduled (attempt {retry_count}, delay {delay}s)",
                log_entry,
                correlation_id
            )
            
            # Store in performance log
            self._store_log_entry(self.performance_log_key, log_entry)
            
        except Exception as e:
            logger.error(f"Failed to log job retry: {sanitize_for_log(str(e))}")
    
    def log_worker_event(self, event_type: str, worker_info: Dict[str, Any],
                        additional_data: Optional[Dict[str, Any]] = None) -> None:
        """
        Log worker-related events
        
        Args:
            event_type: Type of worker event
            worker_info: Worker information
            additional_data: Optional additional data
        """
        try:
            log_entry = {
                'event_type': f'worker_{event_type}',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'worker_info': worker_info,
                'additional_data': additional_data or {}
            }
            
            # Log to structured logger
            self._log_structured(
                LogLevel.INFO,
                f"Worker {event_type}: {worker_info.get('worker_name', 'unknown')}",
                log_entry
            )
            
            # Store in performance log
            self._store_log_entry(self.performance_log_key, log_entry)
            
        except Exception as e:
            logger.error(f"Failed to log worker event: {sanitize_for_log(str(e))}")
    
    def log_queue_event(self, event_type: str, queue_name: str,
                       queue_stats: Optional[Dict[str, Any]] = None) -> None:
        """
        Log queue-related events
        
        Args:
            event_type: Type of queue event
            queue_name: Name of the queue
            queue_stats: Optional queue statistics
        """
        try:
            log_entry = {
                'event_type': f'queue_{event_type}',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'queue_name': queue_name,
                'queue_stats': queue_stats or {}
            }
            
            # Log to structured logger
            self._log_structured(
                LogLevel.INFO,
                f"Queue {event_type}: {queue_name}",
                log_entry
            )
            
            # Store in performance log
            self._store_log_entry(self.performance_log_key, log_entry)
            
        except Exception as e:
            logger.error(f"Failed to log queue event: {sanitize_for_log(str(e))}")
    
    def _generate_correlation_id(self, job_id: str) -> str:
        """Generate correlation ID for job tracking"""
        import uuid
        correlation_id = f"rq_{job_id}_{uuid.uuid4().hex[:8]}"
        
        # Store in thread-local storage
        self._local.correlation_id = correlation_id
        
        return correlation_id
    
    def _get_correlation_id(self, job_id: str) -> str:
        """Get correlation ID for job"""
        # Try thread-local first
        if hasattr(self._local, 'correlation_id'):
            return self._local.correlation_id
        
        # Try Redis storage
        try:
            correlation_id = self.redis_connection.get(f"rq:correlation:{job_id}")
            if correlation_id:
                return correlation_id.decode('utf-8')
        except Exception:
            pass
        
        # Generate new one if not found
        return self._generate_correlation_id(job_id)
    
    def _store_correlation_mapping(self, correlation_id: str, job_id: str) -> None:
        """Store correlation ID mapping in Redis"""
        try:
            self.redis_connection.setex(
                f"rq:correlation:{job_id}",
                3600,  # 1 hour TTL
                correlation_id
            )
        except Exception as e:
            logger.warning(f"Failed to store correlation mapping: {sanitize_for_log(str(e))}")
    
    def _log_structured(self, level: LogLevel, message: str, data: Dict[str, Any],
                       correlation_id: Optional[str] = None) -> None:
        """Log with structured format"""
        try:
            # Add correlation ID to log record
            extra = {'correlation_id': correlation_id or 'unknown'}
            
            # Create structured message
            structured_message = f"{message} | {json.dumps(data, default=str)}"
            
            # Log at appropriate level
            if level == LogLevel.DEBUG:
                self.rq_logger.debug(structured_message, extra=extra)
            elif level == LogLevel.INFO:
                self.rq_logger.info(structured_message, extra=extra)
            elif level == LogLevel.WARNING:
                self.rq_logger.warning(structured_message, extra=extra)
            elif level == LogLevel.ERROR:
                self.rq_logger.error(structured_message, extra=extra)
            elif level == LogLevel.CRITICAL:
                self.rq_logger.critical(structured_message, extra=extra)
                
        except Exception as e:
            logger.error(f"Failed to log structured message: {sanitize_for_log(str(e))}")
    
    def _store_log_entry(self, log_key: str, log_entry: Dict[str, Any]) -> None:
        """Store log entry in Redis"""
        try:
            log_entry_json = json.dumps(log_entry, default=str)
            
            # Store in Redis list
            pipe = self.redis_connection.pipeline()
            pipe.lpush(log_key, log_entry_json)
            pipe.ltrim(log_key, 0, self.max_log_entries - 1)  # Limit log size
            pipe.execute()
            
        except Exception as e:
            logger.warning(f"Failed to store log entry in Redis: {sanitize_for_log(str(e))}")
    
    def _extract_error_details(self, exception: Exception) -> Dict[str, Any]:
        """Extract detailed error information"""
        try:
            error_details = {
                'exception_type': type(exception).__name__,
                'exception_module': type(exception).__module__,
                'args': [str(arg) for arg in exception.args],
                'cause': str(exception.__cause__) if exception.__cause__ else None,
                'context': str(exception.__context__) if exception.__context__ else None
            }
            
            # Add specific error attributes
            if hasattr(exception, 'errno'):
                error_details['errno'] = exception.errno
            
            if hasattr(exception, 'strerror'):
                error_details['strerror'] = exception.strerror
            
            if hasattr(exception, 'filename'):
                error_details['filename'] = exception.filename
            
            return error_details
            
        except Exception as e:
            logger.warning(f"Failed to extract error details: {sanitize_for_log(str(e))}")
            return {'extraction_error': str(e)}
    
    def _sanitize_job_args(self, args: List[Any]) -> List[str]:
        """Sanitize job arguments for logging"""
        try:
            sanitized_args = []
            
            for arg in args:
                if isinstance(arg, str):
                    # Sanitize string arguments
                    sanitized = self._sanitize_string_value(arg)
                    sanitized_args.append(sanitized)
                else:
                    # Convert to string and sanitize
                    sanitized_args.append(str(arg)[:100])  # Limit length
            
            return sanitized_args
            
        except Exception:
            return ['[ARGS_SANITIZATION_ERROR]']
    
    def _sanitize_job_kwargs(self, kwargs: Dict[str, Any]) -> Dict[str, str]:
        """Sanitize job keyword arguments for logging"""
        try:
            sanitized_kwargs = {}
            
            for key, value in kwargs.items():
                # Sanitize key
                sanitized_key = self._sanitize_string_value(str(key))
                
                # Sanitize value
                if isinstance(value, str):
                    sanitized_value = self._sanitize_string_value(value)
                else:
                    sanitized_value = str(value)[:100]  # Limit length
                
                sanitized_kwargs[sanitized_key] = sanitized_value
            
            return sanitized_kwargs
            
        except Exception:
            return {'sanitization_error': 'Failed to sanitize kwargs'}
    
    def _sanitize_string_value(self, value: str) -> str:
        """Sanitize string value for logging"""
        try:
            import re
            
            # Remove potential sensitive information
            sanitized = value
            
            # Remove file paths
            sanitized = re.sub(r'/[^\s]*', '[PATH_REMOVED]', sanitized)
            
            # Remove IP addresses
            sanitized = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '[IP_REMOVED]', sanitized)
            
            # Remove potential credentials
            sanitized = re.sub(
                r'(password|token|key|secret|auth)[\s=:]+[^\s]+',
                r'\1=[REDACTED]',
                sanitized,
                flags=re.IGNORECASE
            )
            
            # Limit length
            if len(sanitized) > 200:
                sanitized = sanitized[:197] + "..."
            
            return sanitized
            
        except Exception:
            return '[SANITIZATION_ERROR]'
    
    def _sanitize_error_message(self, error_message: str) -> str:
        """Sanitize error message for logging"""
        return self._sanitize_string_value(error_message)
    
    def _sanitize_stack_trace(self, stack_trace: str) -> str:
        """Sanitize stack trace for logging"""
        try:
            import re
            
            # Remove file paths but keep line numbers
            sanitized = re.sub(r'File "([^"]*)"', r'File "[PATH_REMOVED]"', stack_trace)
            
            # Remove potential sensitive information from variable values
            sanitized = re.sub(
                r'(password|token|key|secret)[\s=:]+[^\s\n]+',
                r'\1=[REDACTED]',
                sanitized,
                flags=re.IGNORECASE
            )
            
            # Limit total length
            if len(sanitized) > 2000:
                sanitized = sanitized[:1997] + "..."
            
            return sanitized
            
        except Exception:
            return '[STACK_TRACE_SANITIZATION_ERROR]'
    
    def _summarize_result(self, result: Any) -> Dict[str, Any]:
        """Summarize job result for logging"""
        try:
            if result is None:
                return {'type': 'None', 'value': None}
            
            result_type = type(result).__name__
            
            if isinstance(result, dict):
                return {
                    'type': result_type,
                    'keys': list(result.keys())[:10],  # Limit keys
                    'size': len(result)
                }
            elif isinstance(result, (list, tuple)):
                return {
                    'type': result_type,
                    'length': len(result),
                    'sample': str(result[:3]) if len(result) > 0 else None
                }
            elif isinstance(result, str):
                return {
                    'type': result_type,
                    'length': len(result),
                    'preview': result[:100] if len(result) > 100 else result
                }
            else:
                return {
                    'type': result_type,
                    'string_repr': str(result)[:100]
                }
                
        except Exception:
            return {'type': 'unknown', 'error': 'Failed to summarize result'}
    
    def _get_log_level_for_error(self, error_category: ErrorCategory, retry_count: int) -> LogLevel:
        """Determine appropriate log level for error"""
        if error_category in [ErrorCategory.SECURITY_ERROR, ErrorCategory.SYSTEM_ERROR]:
            return LogLevel.CRITICAL
        elif error_category == ErrorCategory.TASK_VALIDATION:
            return LogLevel.ERROR
        elif retry_count >= 2:
            return LogLevel.ERROR
        else:
            return LogLevel.WARNING
    
    def _update_error_correlation(self, error_category: ErrorCategory, error_details: Dict[str, Any]) -> None:
        """Update error correlation data for pattern analysis"""
        try:
            correlation_key = f"{self.correlation_key}:{error_category.value}"
            
            # Get existing correlation data
            correlation_data = self.redis_connection.get(correlation_key)
            
            if correlation_data:
                data = json.loads(correlation_data)
            else:
                data = {
                    'error_category': error_category.value,
                    'total_occurrences': 0,
                    'error_types': {},
                    'first_seen': datetime.now(timezone.utc).isoformat(),
                    'last_seen': None
                }
            
            # Update correlation data
            data['total_occurrences'] += 1
            data['last_seen'] = datetime.now(timezone.utc).isoformat()
            
            error_type = error_details.get('exception_type', 'unknown')
            data['error_types'][error_type] = data['error_types'].get(error_type, 0) + 1
            
            # Store updated correlation data
            self.redis_connection.setex(
                correlation_key,
                86400 * self.log_retention_days,  # TTL based on retention
                json.dumps(data, default=str)
            )
            
        except Exception as e:
            logger.warning(f"Failed to update error correlation: {sanitize_for_log(str(e))}")
    
    def get_error_logs(self, limit: int = 100, error_category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get error logs with optional filtering
        
        Args:
            limit: Maximum number of logs to return
            error_category: Optional error category filter
            
        Returns:
            List of error log entries
        """
        try:
            # Get logs from Redis
            log_entries_json = self.redis_connection.lrange(self.error_log_key, 0, limit - 1)
            
            logs = []
            for entry_json in log_entries_json:
                try:
                    entry = json.loads(entry_json)
                    
                    # Apply category filter if specified
                    if error_category and entry.get('error_category') != error_category:
                        continue
                    
                    logs.append(entry)
                    
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse log entry: {sanitize_for_log(str(e))}")
            
            return logs
            
        except Exception as e:
            logger.error(f"Failed to get error logs: {sanitize_for_log(str(e))}")
            return []
    
    def get_performance_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get performance logs"""
        try:
            log_entries_json = self.redis_connection.lrange(self.performance_log_key, 0, limit - 1)
            
            logs = []
            for entry_json in log_entries_json:
                try:
                    entry = json.loads(entry_json)
                    logs.append(entry)
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse performance log entry: {sanitize_for_log(str(e))}")
            
            return logs
            
        except Exception as e:
            logger.error(f"Failed to get performance logs: {sanitize_for_log(str(e))}")
            return []
    
    def get_error_correlation_data(self) -> Dict[str, Any]:
        """Get error correlation data for analysis"""
        try:
            correlation_data = {}
            
            # Get all correlation keys
            correlation_keys = self.redis_connection.keys(f"{self.correlation_key}:*")
            
            for key in correlation_keys:
                try:
                    data_json = self.redis_connection.get(key)
                    if data_json:
                        data = json.loads(data_json)
                        category = key.decode('utf-8').split(':')[-1]
                        correlation_data[category] = data
                except (json.JSONDecodeError, UnicodeDecodeError) as e:
                    logger.warning(f"Failed to parse correlation data: {sanitize_for_log(str(e))}")
            
            return correlation_data
            
        except Exception as e:
            logger.error(f"Failed to get error correlation data: {sanitize_for_log(str(e))}")
            return {}
    
    def cleanup_old_logs(self, older_than_days: int = None) -> Dict[str, int]:
        """
        Clean up old log entries
        
        Args:
            older_than_days: Remove logs older than this many days
            
        Returns:
            Dict with cleanup statistics
        """
        if older_than_days is None:
            older_than_days = self.log_retention_days
        
        try:
            from datetime import timedelta
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=older_than_days)
            
            cleanup_stats = {
                'error_logs_cleaned': 0,
                'performance_logs_cleaned': 0,
                'correlation_data_cleaned': 0
            }
            
            # Clean error logs
            cleanup_stats['error_logs_cleaned'] = self._cleanup_log_entries(
                self.error_log_key, cutoff_time
            )
            
            # Clean performance logs
            cleanup_stats['performance_logs_cleaned'] = self._cleanup_log_entries(
                self.performance_log_key, cutoff_time
            )
            
            # Clean correlation data
            cleanup_stats['correlation_data_cleaned'] = self._cleanup_correlation_data(cutoff_time)
            
            logger.info(f"Log cleanup completed: {cleanup_stats}")
            return cleanup_stats
            
        except Exception as e:
            logger.error(f"Failed to cleanup old logs: {sanitize_for_log(str(e))}")
            return {'error': 'Cleanup failed'}
    
    def _cleanup_log_entries(self, log_key: str, cutoff_time: datetime) -> int:
        """Clean up log entries older than cutoff time"""
        try:
            # Get all entries
            all_entries = self.redis_connection.lrange(log_key, 0, -1)
            
            entries_to_keep = []
            cleaned_count = 0
            
            for entry_json in all_entries:
                try:
                    entry = json.loads(entry_json)
                    timestamp_str = entry.get('timestamp')
                    
                    if timestamp_str:
                        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        
                        if timestamp > cutoff_time:
                            entries_to_keep.append(entry_json)
                        else:
                            cleaned_count += 1
                    else:
                        # Keep entries without timestamp to avoid data loss
                        entries_to_keep.append(entry_json)
                        
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(f"Failed to parse log entry during cleanup: {sanitize_for_log(str(e))}")
                    # Keep unparseable entries to avoid data loss
                    entries_to_keep.append(entry_json)
            
            # Replace log with cleaned entries
            if cleaned_count > 0:
                pipe = self.redis_connection.pipeline()
                pipe.delete(log_key)
                
                if entries_to_keep:
                    pipe.lpush(log_key, *entries_to_keep)
                
                pipe.execute()
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup log entries: {sanitize_for_log(str(e))}")
            return 0
    
    def _cleanup_correlation_data(self, cutoff_time: datetime) -> int:
        """Clean up old correlation data"""
        try:
            correlation_keys = self.redis_connection.keys(f"{self.correlation_key}:*")
            cleaned_count = 0
            
            for key in correlation_keys:
                try:
                    data_json = self.redis_connection.get(key)
                    if data_json:
                        data = json.loads(data_json)
                        last_seen_str = data.get('last_seen')
                        
                        if last_seen_str:
                            last_seen = datetime.fromisoformat(last_seen_str.replace('Z', '+00:00'))
                            
                            if last_seen < cutoff_time:
                                self.redis_connection.delete(key)
                                cleaned_count += 1
                                
                except (json.JSONDecodeError, ValueError, UnicodeDecodeError) as e:
                    logger.warning(f"Failed to process correlation data during cleanup: {sanitize_for_log(str(e))}")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup correlation data: {sanitize_for_log(str(e))}")
            return 0
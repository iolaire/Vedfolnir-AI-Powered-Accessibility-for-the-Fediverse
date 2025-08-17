# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Session Error Logger

Specialized logging configuration for database session errors and DetachedInstanceError
tracking with comprehensive context and monitoring capabilities.
"""

import logging
import logging.handlers
import os
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from flask import request
from flask_login import current_user
from security.core.security_utils import sanitize_for_log


class SessionErrorLogger:
    """Specialized logger for session-related errors with structured logging"""
    
    def __init__(self, log_dir: str = "logs", max_bytes: int = 10*1024*1024, backup_count: int = 5):
        """Initialize session error logger
        
        Args:
            log_dir: Directory for log files
            max_bytes: Maximum size per log file
            backup_count: Number of backup files to keep
        """
        self.log_dir = log_dir
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        
        # Ensure log directory exists
        os.makedirs(log_dir, exist_ok=True)
        
        # Create specialized logger
        self.logger = logging.getLogger('session_errors')
        self.logger.setLevel(logging.DEBUG)
        
        # Prevent duplicate handlers
        if not self.logger.handlers:
            self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup logging handlers for session errors"""
        
        # Session error file handler (rotating)
        session_error_file = os.path.join(self.log_dir, 'session_errors.log')
        session_handler = logging.handlers.RotatingFileHandler(
            session_error_file,
            maxBytes=self.max_bytes,
            backupCount=self.backup_count
        )
        session_handler.setLevel(logging.WARNING)
        
        # Detailed debug handler for troubleshooting
        debug_file = os.path.join(self.log_dir, 'session_debug.log')
        debug_handler = logging.handlers.RotatingFileHandler(
            debug_file,
            maxBytes=self.max_bytes,
            backupCount=self.backup_count
        )
        debug_handler.setLevel(logging.DEBUG)
        
        # JSON structured logging handler for monitoring
        json_file = os.path.join(self.log_dir, 'session_errors.json')
        json_handler = logging.handlers.RotatingFileHandler(
            json_file,
            maxBytes=self.max_bytes,
            backupCount=self.backup_count
        )
        json_handler.setLevel(logging.ERROR)
        
        # Formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s\n'
            'Context: %(pathname)s:%(lineno)d in %(funcName)s\n'
            '%(stack_info)s\n'
        )
        
        simple_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        
        json_formatter = JsonFormatter()
        
        # Apply formatters
        session_handler.setFormatter(simple_formatter)
        debug_handler.setFormatter(detailed_formatter)
        json_handler.setFormatter(json_formatter)
        
        # Add handlers
        self.logger.addHandler(session_handler)
        self.logger.addHandler(debug_handler)
        self.logger.addHandler(json_handler)
    
    def log_detached_instance_error(self, error: Exception, endpoint: str, context: Dict[str, Any] = None):
        """Log DetachedInstanceError with comprehensive context
        
        Args:
            error: The DetachedInstanceError that occurred
            endpoint: Endpoint where error occurred
            context: Additional context information
        """
        error_context = self._build_error_context(error, endpoint, context)
        
        self.logger.error(
            f"DetachedInstanceError in {endpoint}: {str(error)}",
            extra={
                'error_type': 'DetachedInstanceError',
                'endpoint': endpoint,
                'context': error_context
            },
            stack_info=True
        )
    
    def log_sqlalchemy_error(self, error: Exception, endpoint: str, context: Dict[str, Any] = None):
        """Log SQLAlchemy error with context
        
        Args:
            error: The SQLAlchemy error that occurred
            endpoint: Endpoint where error occurred
            context: Additional context information
        """
        error_context = self._build_error_context(error, endpoint, context)
        
        self.logger.error(
            f"SQLAlchemy error in {endpoint}: {type(error).__name__} - {str(error)}",
            extra={
                'error_type': type(error).__name__,
                'endpoint': endpoint,
                'context': error_context
            },
            stack_info=True
        )
    
    def log_session_recovery(self, object_type: str, recovery_time: float, success: bool, endpoint: str):
        """Log session recovery attempt
        
        Args:
            object_type: Type of object being recovered
            recovery_time: Time taken for recovery attempt
            success: Whether recovery was successful
            endpoint: Endpoint where recovery occurred
        """
        level = logging.INFO if success else logging.WARNING
        status = "successful" if success else "failed"
        
        self.logger.log(
            level,
            f"Session recovery {status} for {object_type} in {endpoint} ({recovery_time:.3f}s)",
            extra={
                'event_type': 'session_recovery',
                'object_type': object_type,
                'recovery_time': recovery_time,
                'success': success,
                'endpoint': endpoint
            }
        )
    
    def log_session_validation_failure(self, endpoint: str, reason: str, context: Dict[str, Any] = None):
        """Log session validation failure
        
        Args:
            endpoint: Endpoint where validation failed
            reason: Reason for validation failure
            context: Additional context information
        """
        error_context = self._build_error_context(None, endpoint, context)
        error_context['validation_failure_reason'] = reason
        
        self.logger.warning(
            f"Session validation failed in {endpoint}: {reason}",
            extra={
                'event_type': 'session_validation_failure',
                'endpoint': endpoint,
                'reason': reason,
                'context': error_context
            }
        )
    
    def log_high_error_frequency(self, error_type: str, endpoint: str, count: int, threshold: int):
        """Log when error frequency exceeds threshold
        
        Args:
            error_type: Type of error
            endpoint: Endpoint with high error count
            count: Current error count
            threshold: Threshold that was exceeded
        """
        self.logger.critical(
            f"High error frequency detected: {error_type} in {endpoint} "
            f"({count} occurrences, threshold: {threshold})",
            extra={
                'event_type': 'high_error_frequency',
                'error_type': error_type,
                'endpoint': endpoint,
                'count': count,
                'threshold': threshold
            }
        )
    
    def _build_error_context(self, error: Optional[Exception], endpoint: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Build comprehensive error context
        
        Args:
            error: The exception that occurred (if any)
            endpoint: Endpoint where error occurred
            context: Additional context information
            
        Returns:
            Dictionary with error context
        """
        error_context = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'endpoint': endpoint,
        }
        
        # Add request context if available
        if request:
            error_context.update({
                'method': request.method,
                'path': request.path,
                'remote_addr': request.remote_addr,
                'user_agent': sanitize_for_log(request.headers.get('User-Agent', 'Unknown')),
                'referrer': sanitize_for_log(request.referrer or 'None')
            })
        
        # Add user context if available (with safe access)
        try:
            from flask import has_request_context
            from flask_login import current_user
            
            if has_request_context() and current_user and hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
                try:
                    user_id = getattr(current_user, 'id', None)
                    username = getattr(current_user, 'username', 'unknown')
                    if user_id:
                        error_context.update({
                            'user_id': user_id,
                            'username': sanitize_for_log(username)
                        })
                except Exception:
                    error_context['user_context_error'] = 'Failed to access current_user attributes'
        except (ImportError, RuntimeError):
            # Flask-Login not available or no request context
            error_context['user_context_error'] = 'Flask-Login not available or no request context'
        
        # Add error details if available
        if error:
            error_context.update({
                'error_message': sanitize_for_log(str(error)),
                'error_class': type(error).__name__
            })
        
        # Add additional context
        if context:
            error_context.update(context)
        
        return error_context


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record):
        """Format log record as JSON"""
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add extra fields if present
        if hasattr(record, 'error_type'):
            log_entry['error_type'] = record.error_type
        if hasattr(record, 'endpoint'):
            log_entry['endpoint'] = record.endpoint
        if hasattr(record, 'context'):
            log_entry['context'] = record.context
        if hasattr(record, 'event_type'):
            log_entry['event_type'] = record.event_type
        
        return json.dumps(log_entry, default=str)


# Global session error logger instance
_session_error_logger = None


def get_session_error_logger() -> SessionErrorLogger:
    """Get the global session error logger instance
    
    Returns:
        SessionErrorLogger instance
    """
    global _session_error_logger
    if _session_error_logger is None:
        _session_error_logger = SessionErrorLogger()
    return _session_error_logger


def initialize_session_error_logging(app):
    """Initialize session error logging for Flask app
    
    Args:
        app: Flask application instance
    """
    # Get logger instance
    session_logger = get_session_error_logger()
    
    # Store in app for access by other components
    app.session_error_logger = session_logger
    
    # Log initialization
    session_logger.logger.info("Session error logging initialized")
    
    return session_logger
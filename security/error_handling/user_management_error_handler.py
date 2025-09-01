# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Comprehensive Error Handling System for User Management

Provides robust error handling with user-friendly messages, security logging, and graceful degradation.
"""

import logging
import traceback
import sys
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, Union
from functools import wraps
from flask import request, jsonify, render_template, flash, redirect, url_for, current_app, g
from werkzeug.exceptions import HTTPException, BadRequest, Unauthorized, Forbidden, NotFound, TooManyRequests
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError, DatabaseError
from sqlalchemy.orm import Session
from security.monitoring.security_event_logger import get_security_event_logger, SecurityEventType, SecurityEventSeverity
from security.core.security_utils import sanitize_for_log

logger = logging.getLogger(__name__)

class UserManagementError(Exception):
    """Base exception for user management operations"""
    
    def __init__(
        self,
        message: str,
        error_code: str = "USER_MANAGEMENT_ERROR",
        user_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        severity: str = "medium"
    ):
        self.message = message
        self.error_code = error_code
        self.user_message = user_message or "An error occurred. Please try again."
        self.details = details or {}
        self.severity = severity
        super().__init__(message)

class ValidationError(UserManagementError):
    """Validation error for user input"""
    
    def __init__(self, message: str, field: str = None, **kwargs):
        self.field = field
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            user_message=message,  # Validation errors are safe to show users
            **kwargs
        )

class AuthenticationError(UserManagementError):
    """Authentication-related errors"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            user_message="Invalid credentials or authentication failed.",
            severity="high",
            **kwargs
        )

class AuthorizationError(UserManagementError):
    """Authorization-related errors"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            user_message="You don't have permission to perform this action.",
            severity="high",
            **kwargs
        )

class RateLimitError(UserManagementError):
    """Rate limiting errors"""
    
    def __init__(self, message: str, retry_after: int = None, **kwargs):
        self.retry_after = retry_after
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_ERROR",
            user_message="Too many requests. Please try again later.",
            severity="medium",
            **kwargs
        )

class DatabaseError(UserManagementError):
    """Database-related errors"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            user_message="A system error occurred. Please try again later.",
            severity="high",
            **kwargs
        )

class EmailError(UserManagementError):
    """Email service errors"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code="EMAIL_ERROR",
            user_message="Failed to send email. Please try again later.",
            severity="medium",
            **kwargs
        )

class SecurityError(UserManagementError):
    """Security-related errors"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code="SECURITY_ERROR",
            user_message="Security validation failed. Please refresh the page and try again.",
            severity="critical",
            **kwargs
        )

class UserManagementErrorHandler:
    """Comprehensive error handler for user management operations"""
    
    def __init__(self, app=None, db_session: Optional[Session] = None):
        self.app = app
        self.db_session = db_session
        self.security_logger = None
        
        # Error message templates
        self.error_templates = {
            'validation': "Please check your input and try again.",
            'authentication': "Invalid credentials. Please check your username/email and password.",
            'authorization': "You don't have permission to perform this action.",
            'rate_limit': "Too many requests. Please wait before trying again.",
            'database': "A system error occurred. Our team has been notified.",
            'email': "Failed to send email. Please try again or contact support.",
            'security': "Security validation failed. Please refresh the page and try again.",
            'system': "An unexpected error occurred. Please try again later.",
            'network': "Network error. Please check your connection and try again.",
            'timeout': "The request timed out. Please try again.",
        }
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize error handler with Flask app"""
        self.app = app
        
        # Register error handlers
        app.register_error_handler(400, self.handle_bad_request)
        app.register_error_handler(401, self.handle_unauthorized)
        app.register_error_handler(403, self.handle_forbidden)
        app.register_error_handler(404, self.handle_not_found)
        app.register_error_handler(429, self.handle_rate_limit)
        app.register_error_handler(500, self.handle_internal_error)
        app.register_error_handler(SQLAlchemyError, self.handle_database_error)
        app.register_error_handler(UserManagementError, self.handle_user_management_error)
        
        # Register teardown handler for cleanup
        app.teardown_appcontext(self.cleanup_error_context)
    
    def handle_bad_request(self, error):
        """Handle 400 Bad Request errors"""
        return self._create_error_response(
            error_type="validation",
            status_code=400,
            user_message=getattr(error, 'description', None) or self.error_templates['validation'],
            system_message=f"Bad request: {error}",
            error_details={'error_type': 'bad_request', 'original_error': str(error)}
        )
    
    def handle_unauthorized(self, error):
        """Handle 401 Unauthorized errors"""
        return self._create_error_response(
            error_type="authentication",
            status_code=401,
            user_message=self.error_templates['authentication'],
            system_message=f"Unauthorized access attempt: {error}",
            error_details={'error_type': 'unauthorized', 'original_error': str(error)},
            severity=SecurityEventSeverity.HIGH
        )
    
    def handle_forbidden(self, error):
        """Handle 403 Forbidden errors"""
        return self._create_error_response(
            error_type="authorization",
            status_code=403,
            user_message=self.error_templates['authorization'],
            system_message=f"Forbidden access attempt: {error}",
            error_details={'error_type': 'forbidden', 'original_error': str(error)},
            severity=SecurityEventSeverity.HIGH
        )
    
    def handle_not_found(self, error):
        """Handle 404 Not Found errors"""
        return self._create_error_response(
            error_type="not_found",
            status_code=404,
            user_message="The requested page or resource was not found.",
            system_message=f"Resource not found: {error}",
            error_details={'error_type': 'not_found', 'original_error': str(error)},
            template_name="errors/404.html"
        )
    
    def handle_rate_limit(self, error):
        """Handle 429 Too Many Requests errors"""
        retry_after = getattr(error, 'retry_after', 60)
        
        return self._create_error_response(
            error_type="rate_limit",
            status_code=429,
            user_message=f"{self.error_templates['rate_limit']} Try again in {retry_after} seconds.",
            system_message=f"Rate limit exceeded: {error}",
            error_details={'error_type': 'rate_limit', 'retry_after': retry_after},
            severity=SecurityEventSeverity.MEDIUM,
            headers={'Retry-After': str(retry_after)}
        )
    
    def handle_internal_error(self, error):
        """Handle 500 Internal Server Error"""
        return self._create_error_response(
            error_type="system",
            status_code=500,
            user_message=self.error_templates['system'],
            system_message=f"Internal server error: {error}",
            error_details={'error_type': 'internal_error', 'original_error': str(error)},
            severity=SecurityEventSeverity.CRITICAL,
            template_name="errors/500.html"
        )
    
    def handle_database_error(self, error):
        """Handle SQLAlchemy database errors"""
        error_type = "database"
        severity = SecurityEventSeverity.HIGH
        
        # Categorize database errors
        if isinstance(error, IntegrityError):
            user_message = "The data you entered conflicts with existing information. Please check your input."
            system_message = f"Database integrity error: {error}"
        elif isinstance(error, OperationalError):
            user_message = self.error_templates['database']
            system_message = f"Database operational error: {error}"
            severity = SecurityEventSeverity.CRITICAL
        else:
            user_message = self.error_templates['database']
            system_message = f"Database error: {error}"
        
        return self._create_error_response(
            error_type=error_type,
            status_code=500,
            user_message=user_message,
            system_message=system_message,
            error_details={'error_type': 'database_error', 'db_error_type': type(error).__name__},
            severity=severity
        )
    
    def handle_user_management_error(self, error: UserManagementError):
        """Handle custom user management errors"""
        severity_map = {
            'low': SecurityEventSeverity.LOW,
            'medium': SecurityEventSeverity.MEDIUM,
            'high': SecurityEventSeverity.HIGH,
            'critical': SecurityEventSeverity.CRITICAL
        }
        
        status_code_map = {
            'VALIDATION_ERROR': 400,
            'AUTHENTICATION_ERROR': 401,
            'AUTHORIZATION_ERROR': 403,
            'RATE_LIMIT_ERROR': 429,
            'DATABASE_ERROR': 500,
            'EMAIL_ERROR': 500,
            'SECURITY_ERROR': 403,
        }
        
        status_code = status_code_map.get(error.error_code, 500)
        severity = severity_map.get(error.severity, SecurityEventSeverity.MEDIUM)
        
        return self._create_error_response(
            error_type=error.error_code.lower(),
            status_code=status_code,
            user_message=error.user_message,
            system_message=error.message,
            error_details=error.details,
            severity=severity
        )
    
    def _create_error_response(
        self,
        error_type: str,
        status_code: int,
        user_message: str,
        system_message: str,
        error_details: Dict[str, Any] = None,
        severity: SecurityEventSeverity = SecurityEventSeverity.MEDIUM,
        template_name: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None
    ):
        """Create a standardized error response"""
        try:
            # Log the error
            self._log_error(error_type, system_message, error_details or {}, severity)
            
            # Prepare response data
            response_data = {
                'error': True,
                'message': user_message,
                'error_code': error_type.upper(),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Add request ID if available
            if hasattr(g, 'request_id'):
                response_data['request_id'] = g.request_id
            
            # Handle JSON requests
            if request.is_json or request.headers.get('Accept', '').startswith('application/json'):
                response = jsonify(response_data)
                response.status_code = status_code
                
                if headers:
                    for key, value in headers.items():
                        response.headers[key] = value
                
                return response
            
            # Handle web requests
            # Send error notification
            from notification_helpers import send_error_notification
            send_error_notification(user_message, 'User Management Error')
            
            # Use custom template if provided
            if template_name:
                try:
                    response = render_template(template_name, error=response_data), status_code
                    if headers:
                        response = (*response, headers)
                    return response
                except Exception:
                    # Fall back to redirect if template fails
                    pass
            
            # Default redirect for web requests
            return redirect(url_for('index'))
            
        except Exception as e:
            # Fallback error handling
            logger.critical(f"Error in error handler: {e}")
            return "An unexpected error occurred", 500
    
    def _log_error(
        self,
        error_type: str,
        message: str,
        details: Dict[str, Any],
        severity: SecurityEventSeverity
    ):
        """Log error with appropriate level and security monitoring"""
        try:
            # Sanitize message for logging
            safe_message = sanitize_for_log(message)
            
            # Log to application logger
            if severity == SecurityEventSeverity.CRITICAL:
                logger.critical(f"CRITICAL ERROR [{error_type}]: {safe_message}")
            elif severity == SecurityEventSeverity.HIGH:
                logger.error(f"HIGH SEVERITY ERROR [{error_type}]: {safe_message}")
            elif severity == SecurityEventSeverity.MEDIUM:
                logger.warning(f"MEDIUM SEVERITY ERROR [{error_type}]: {safe_message}")
            else:
                logger.info(f"LOW SEVERITY ERROR [{error_type}]: {safe_message}")
            
            # Log to security event logger if available
            if self.security_logger:
                user_id = None
                if hasattr(g, 'current_user') and g.current_user:
                    user_id = g.current_user.id
                
                # Map error types to security events
                security_event_map = {
                    'authentication': SecurityEventType.LOGIN_FAILURE,
                    'authorization': SecurityEventType.SUSPICIOUS_ACTIVITY,
                    'rate_limit': SecurityEventType.RATE_LIMIT_EXCEEDED,
                    'security': SecurityEventType.SUSPICIOUS_ACTIVITY,
                    'validation': SecurityEventType.INPUT_VALIDATION_FAILURE,
                }
                
                event_type = security_event_map.get(error_type, SecurityEventType.SUSPICIOUS_ACTIVITY)
                
                self.security_logger.log_security_event(
                    event_type=event_type,
                    severity=severity,
                    user_id=user_id,
                    details=details,
                    additional_context={'error_message': safe_message}
                )
            
            # Log stack trace for critical errors
            if severity == SecurityEventSeverity.CRITICAL:
                logger.critical(f"Stack trace: {traceback.format_exc()}")
                
        except Exception as e:
            # Prevent error logging from causing more errors
            logger.critical(f"Failed to log error: {e}")
    
    def cleanup_error_context(self, exception):
        """Clean up error context after request"""
        # Clean up any error-related context
        if hasattr(g, 'error_context'):
            delattr(g, 'error_context')

def handle_user_management_errors(f):
    """
    Decorator to handle errors in user management operations
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
            
        except UserManagementError as e:
            # Custom user management errors are handled by the error handler
            raise e
            
        except SQLAlchemyError as e:
            # Database errors
            logger.error(f"Database error in {f.__name__}: {e}")
            raise DatabaseError(f"Database operation failed: {e}")
            
        except Exception as e:
            # Unexpected errors
            logger.error(f"Unexpected error in {f.__name__}: {e}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            
            # Don't expose internal error details to users
            raise UserManagementError(
                message=f"Unexpected error in {f.__name__}: {e}",
                error_code="SYSTEM_ERROR",
                user_message="An unexpected error occurred. Please try again later.",
                severity="critical"
            )
    
    return decorated_function

def graceful_degradation(fallback_response=None, log_error=True):
    """
    Decorator for graceful degradation when operations fail
    
    Args:
        fallback_response: Response to return if operation fails
        log_error: Whether to log the error
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except Exception as e:
                if log_error:
                    logger.warning(f"Graceful degradation in {f.__name__}: {e}")
                
                if fallback_response is not None:
                    return fallback_response
                
                # Default fallback
                if request.is_json:
                    return jsonify({'error': True, 'message': 'Service temporarily unavailable'}), 503
                else:
                    # Send warning notification
                    from notification_helpers import send_warning_notification
                    send_warning_notification('Some features may be temporarily unavailable.', 'Service Warning')
                    return redirect(url_for('index'))
        
        return decorated_function
    return decorator

def safe_operation(operation_name: str, default_return=None):
    """
    Decorator for safe operations that shouldn't fail the entire request
    
    Args:
        operation_name: Name of the operation for logging
        default_return: Default value to return on failure
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except Exception as e:
                logger.warning(f"Safe operation '{operation_name}' failed: {e}")
                return default_return
        
        return decorated_function
    return decorator

# Utility functions for error handling
def create_user_friendly_error(error: Exception, context: str = None) -> str:
    """Create a user-friendly error message from an exception"""
    if isinstance(error, UserManagementError):
        return error.user_message
    elif isinstance(error, ValidationError):
        return str(error)
    elif isinstance(error, IntegrityError):
        if 'UNIQUE constraint failed' in str(error):
            return "This information is already in use. Please try different values."
        return "The data you entered conflicts with existing information."
    elif isinstance(error, OperationalError):
        return "The system is temporarily unavailable. Please try again later."
    else:
        return "An unexpected error occurred. Please try again later."

def log_error_with_context(error: Exception, context: Dict[str, Any] = None):
    """Log an error with additional context"""
    context = context or {}
    
    # Add request context if available
    if request:
        context.update({
            'url': request.url,
            'method': request.method,
            'ip_address': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', 'Unknown')
        })
    
    # Add user context if available
    if hasattr(g, 'current_user') and g.current_user:
        context['user_id'] = g.current_user.id
        context['username'] = g.current_user.username
    
    logger.error(f"Error: {error}, Context: {context}")

def is_safe_to_retry(error: Exception) -> bool:
    """Determine if an operation is safe to retry based on the error type"""
    # Network errors, timeouts, and temporary database issues are safe to retry
    safe_to_retry_errors = (
        OperationalError,  # Database connection issues
        ConnectionError,   # Network issues
        TimeoutError,      # Timeout issues
    )
    
    # Don't retry validation errors, authentication errors, or integrity errors
    unsafe_to_retry_errors = (
        ValidationError,
        AuthenticationError,
        AuthorizationError,
        IntegrityError,
    )
    
    if isinstance(error, unsafe_to_retry_errors):
        return False
    
    if isinstance(error, safe_to_retry_errors):
        return True
    
    # For unknown errors, err on the side of caution
    return False
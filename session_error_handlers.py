# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Session Error Handlers

Comprehensive error handling for database session issues, specifically targeting
DetachedInstanceError and related SQLAlchemy session problems throughout the application.
"""

import logging
import traceback
from functools import wraps
from typing import Any, Callable, Optional, Dict, List
from flask import (
    current_app, request, redirect, url_for, flash, jsonify, 
    render_template, session as flask_session
)
from flask_login import current_user, logout_user
from sqlalchemy.exc import SQLAlchemyError, InvalidRequestError
from sqlalchemy.orm.exc import DetachedInstanceError
from security.core.security_utils import sanitize_for_log
from session_error_logger import get_session_error_logger

logger = logging.getLogger(__name__)


class SessionErrorHandler:
    """Comprehensive handler for database session errors and recovery"""
    
    def __init__(self, session_manager, detached_instance_handler):
        """Initialize session error handler
        
        Args:
            session_manager: RequestScopedSessionManager instance
            detached_instance_handler: DetachedInstanceHandler instance
        """
        self.session_manager = session_manager
        self.detached_instance_handler = detached_instance_handler
        self.error_counts = {}  # Track error frequencies for monitoring
    
    def handle_detached_instance_error(self, error: DetachedInstanceError, endpoint: str) -> Any:
        """Handle DetachedInstanceError with context-aware recovery
        
        Args:
            error: The DetachedInstanceError that occurred
            endpoint: The endpoint where the error occurred
            
        Returns:
            Flask response with appropriate redirect and user message
        """
        error_context = {
            'endpoint': endpoint,
            'user_id': current_user.id if current_user.is_authenticated else None,
            'error_type': 'DetachedInstanceError',
            'error_message': str(error)
        }
        
        # Log the error with context using specialized logger
        session_logger = get_session_error_logger()
        session_logger.log_detached_instance_error(error, endpoint, error_context)
        
        # Also log with standard logger for backward compatibility
        self._log_session_error(error_context)
        
        # Increment error count for monitoring
        self._increment_error_count('detached_instance', endpoint)
        
        # Determine appropriate recovery action based on endpoint
        if endpoint == 'login':
            # Login page - clear session and show login form
            flask_session.clear()
            flash('Session expired. Please log in again.', 'warning')
            return redirect(url_for('login'))
            
        elif endpoint in ['health_dashboard', 'index']:
            # Health dashboard/index - try to recover or redirect to platform management
            try:
                # Attempt to recover current user session
                if current_user.is_authenticated:
                    # Check if user has valid platforms
                    with self.session_manager.session_scope() as db_session:
                        from models import PlatformConnection
                        user_platforms = db_session.query(PlatformConnection).filter_by(
                            user_id=current_user.id,
                            is_active=True
                        ).count()
                        
                        if user_platforms == 0:
                            flash('No active platform connections found. Please set up a platform.', 'warning')
                            return redirect(url_for('first_time_setup'))
                        else:
                            flash('Session refreshed. Please select your platform.', 'info')
                            return redirect(url_for('platform_management'))
                            
            except Exception as recovery_error:
                logger.error(f"Recovery failed for {endpoint}: {sanitize_for_log(str(recovery_error))}")
                # Fall back to logout
                return self._force_logout_with_message('Session recovery failed. Please log in again.')
        
        elif 'platform' in endpoint:
            # Platform-related endpoints - redirect to platform management
            flash('Platform connection issue detected. Please verify your platform settings.', 'warning')
            return redirect(url_for('platform_management'))
            
        elif endpoint in ['review', 'batch_review']:
            # Review endpoints - try to recover or redirect to dashboard
            flash('Session issue detected while reviewing. Returning to dashboard.', 'warning')
            return redirect(url_for('health_dashboard'))
            
        elif 'api' in endpoint:
            # API endpoints - return JSON error
            return jsonify({
                'success': False,
                'error': 'session_expired',
                'message': 'Your session has expired. Please refresh the page and log in again.',
                'redirect': url_for('login')
            }), 401
            
        else:
            # Generic fallback - show session error page for better UX
            if 'api' not in endpoint:
                return render_template('errors/session_error.html'), 500
            else:
                return jsonify({
                    'success': False,
                    'error': 'session_error',
                    'message': 'A session issue occurred. Please refresh the page and try again.',
                    'redirect': url_for('login')
                }), 500
    
    def handle_sqlalchemy_error(self, error: SQLAlchemyError, endpoint: str) -> Any:
        """Handle general SQLAlchemy errors with graceful degradation
        
        Args:
            error: The SQLAlchemy error that occurred
            endpoint: The endpoint where the error occurred
            
        Returns:
            Flask response with appropriate error handling
        """
        error_context = {
            'endpoint': endpoint,
            'user_id': current_user.id if current_user.is_authenticated else None,
            'error_type': type(error).__name__,
            'error_message': str(error)
        }
        
        # Log the error with context using specialized logger
        session_logger = get_session_error_logger()
        session_logger.log_sqlalchemy_error(error, endpoint, error_context)
        
        # Also log with standard logger for backward compatibility
        self._log_session_error(error_context)
        
        # Check if it's a DetachedInstanceError wrapped in another exception
        if isinstance(error, DetachedInstanceError) or 'DetachedInstanceError' in str(error):
            return self.handle_detached_instance_error(error, endpoint)
        
        # Increment error count for monitoring
        self._increment_error_count('sqlalchemy', endpoint)
        
        # Handle specific SQLAlchemy error types
        if isinstance(error, InvalidRequestError):
            if 'api' in endpoint:
                return jsonify({
                    'success': False,
                    'error': 'database_error',
                    'message': 'A database error occurred. Please try again.'
                }), 500
            else:
                flash('Database connection issue. Please try again.', 'error')
                return redirect(url_for('health_dashboard') if current_user.is_authenticated else url_for('login'))
        
        # Generic SQLAlchemy error handling
        if 'api' in endpoint:
            return jsonify({
                'success': False,
                'error': 'database_error',
                'message': 'A database error occurred. Please try again.'
            }), 500
        else:
            flash('A database error occurred. Please try again.', 'error')
            return redirect(url_for('health_dashboard') if current_user.is_authenticated else url_for('login'))
    
    def handle_session_timeout(self, endpoint: str) -> Any:
        """Handle session timeout scenarios
        
        Args:
            endpoint: The endpoint where the timeout occurred
            
        Returns:
            Flask response with appropriate timeout handling
        """
        error_context = {
            'endpoint': endpoint,
            'user_id': current_user.id if current_user.is_authenticated else None,
            'error_type': 'SessionTimeout',
            'error_message': 'User session has timed out'
        }
        
        self._log_session_error(error_context)
        self._increment_error_count('session_timeout', endpoint)
        
        # Clear session and redirect to login
        return self._force_logout_with_message('Your session has expired. Please log in again.')
    
    def _force_logout_with_message(self, message: str) -> Any:
        """Force user logout with a specific message
        
        Args:
            message: Message to display to user
            
        Returns:
            Redirect to login page
        """
        try:
            # Clear Flask session
            flask_session.clear()
            
            # Clear database session if exists
            flask_session_id = flask_session.get('_id')
            if flask_session_id:
                from session_manager import SessionManager
                session_manager = SessionManager(current_app.config.get('db_manager'))
                session_manager._cleanup_session(flask_session_id)
            
            # Log out user
            logout_user()
            
        except Exception as logout_error:
            logger.error(f"Error during forced logout: {sanitize_for_log(str(logout_error))}")
        
        flash(message, 'warning')
        return redirect(url_for('login'))
    
    def _log_session_error(self, error_context: Dict[str, Any]):
        """Log session error with comprehensive context
        
        Args:
            error_context: Dictionary containing error details
        """
        log_message = (
            f"Session error in {error_context['endpoint']}: "
            f"{error_context['error_type']} - {error_context['error_message']}"
        )
        
        if error_context['user_id']:
            log_message += f" (User ID: {error_context['user_id']})"
        
        # Add request context
        if request:
            log_message += f" (IP: {request.remote_addr}, Method: {request.method})"
        
        logger.error(log_message)
        
        # Log stack trace for debugging
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Stack trace for session error:\n{traceback.format_exc()}")
    
    def _increment_error_count(self, error_type: str, endpoint: str):
        """Increment error count for monitoring
        
        Args:
            error_type: Type of error (detached_instance, sqlalchemy, etc.)
            endpoint: Endpoint where error occurred
        """
        key = f"{error_type}:{endpoint}"
        self.error_counts[key] = self.error_counts.get(key, 0) + 1
        
        # Log warning if error count is high
        if self.error_counts[key] > 10:
            logger.warning(f"High error count for {key}: {self.error_counts[key]} occurrences")
    
    def get_error_statistics(self) -> Dict[str, int]:
        """Get error statistics for monitoring
        
        Returns:
            Dictionary of error counts by type and endpoint
        """
        return self.error_counts.copy()


def with_session_error_handling(f: Callable) -> Callable:
    """Decorator to add comprehensive session error handling to view functions
    
    Args:
        f: View function to wrap
        
    Returns:
        Wrapped function with error handling
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
            
        except DetachedInstanceError as e:
            handler = current_app.session_error_handler
            return handler.handle_detached_instance_error(e, request.endpoint)
            
        except SQLAlchemyError as e:
            handler = current_app.session_error_handler
            return handler.handle_sqlalchemy_error(e, request.endpoint)
            
        except Exception as e:
            # Log unexpected errors
            logger.error(f"Unexpected error in {request.endpoint}: {sanitize_for_log(str(e))}")
            logger.debug(f"Stack trace:\n{traceback.format_exc()}")
            
            # For API endpoints, return JSON error
            if 'api' in request.endpoint:
                return jsonify({
                    'success': False,
                    'error': 'unexpected_error',
                    'message': 'An unexpected error occurred. Please try again.'
                }), 500
            else:
                flash('An unexpected error occurred. Please try again.', 'error')
                return redirect(url_for('health_dashboard') if current_user.is_authenticated else url_for('login'))
    
    return decorated_function


def register_session_error_handlers(app, session_manager, detached_instance_handler):
    """Register comprehensive session error handlers with Flask app
    
    Args:
        app: Flask application instance
        session_manager: RequestScopedSessionManager instance
        detached_instance_handler: DetachedInstanceHandler instance
    """
    # Create session error handler
    session_error_handler = SessionErrorHandler(session_manager, detached_instance_handler)
    app.session_error_handler = session_error_handler
    
    @app.errorhandler(DetachedInstanceError)
    def handle_detached_instance_error(error):
        """Global handler for DetachedInstanceError"""
        return session_error_handler.handle_detached_instance_error(error, request.endpoint or 'unknown')
    
    @app.errorhandler(SQLAlchemyError)
    def handle_sqlalchemy_error(error):
        """Global handler for SQLAlchemy errors"""
        return session_error_handler.handle_sqlalchemy_error(error, request.endpoint or 'unknown')
    
    # Add session validation middleware
    @app.before_request
    def validate_session_integrity():
        """Validate session integrity before each request"""
        # Skip validation for static files and error handlers
        if request.endpoint in ['static', None] or request.path.startswith('/static/'):
            return
        
        # Skip validation for login/logout endpoints to avoid loops
        if request.endpoint in ['login', 'logout', 'logout_all']:
            return
        
        # Validate authenticated user session
        if current_user.is_authenticated:
            try:
                # Check if user object is accessible
                _ = current_user.id
                _ = current_user.username
                
                # For platform-dependent endpoints, validate platform context
                if request.endpoint in ['health_dashboard', 'review', 'batch_review', 'caption_generation']:
                    from flask_session_manager import get_current_platform_context
                    context = get_current_platform_context()
                    
                    if not context or not context.get('platform_connection_id'):
                        # No platform context - redirect to platform management
                        flash('Please select a platform to continue.', 'info')
                        return redirect(url_for('platform_management'))
                
            except DetachedInstanceError:
                # User object is detached - handle gracefully
                logger.warning(f"DetachedInstanceError detected for user in before_request for {request.endpoint}")
                return session_error_handler.handle_detached_instance_error(
                    DetachedInstanceError("User object detached in before_request"), 
                    request.endpoint or 'unknown'
                )
            except Exception as e:
                # Other session validation errors
                logger.error(f"Session validation error in before_request: {sanitize_for_log(str(e))}")
                if 'api' not in request.endpoint:
                    flash('Session validation failed. Please log in again.', 'warning')
                    return redirect(url_for('login'))
    
    logger.info("Session error handlers registered successfully")


def get_session_error_handler():
    """Get the current application's SessionErrorHandler
    
    Returns:
        SessionErrorHandler instance
        
    Raises:
        RuntimeError: If no handler is configured
    """
    if hasattr(current_app, 'session_error_handler'):
        return current_app.session_error_handler
    
    raise RuntimeError("SessionErrorHandler not configured. Call register_session_error_handlers() during app initialization.")
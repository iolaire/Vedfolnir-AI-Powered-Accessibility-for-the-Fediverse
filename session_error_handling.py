# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Session Error Handling System

This module provides comprehensive error handling for database session management,
including user-friendly error messages, automatic recovery, and proper redirects.
"""

from logging import getLogger
from typing import Optional, Dict, Any, Callable
from flask import request, redirect, url_for, flash, make_response, jsonify, render_template
from unified_session_manager import SessionValidationError, SessionExpiredError, SessionNotFoundError
from session_cookie_manager import SessionCookieManager

logger = getLogger(__name__)

class SessionErrorHandler:
    """Handles session-related errors with user-friendly responses"""
    
    def __init__(self, cookie_manager: SessionCookieManager):
        self.cookie_manager = cookie_manager
        
        # Error message templates
        self.error_messages = {
            'session_expired': 'Your session has expired. Please log in again.',
            'session_not_found': 'Please log in to continue.',
            'session_invalid': 'Your session is invalid. Please log in again.',
            'session_security_error': 'Security validation failed. Please log in again.',
            'session_database_error': 'A database error occurred. Please try again.',
            'session_general_error': 'A session error occurred. Please try again.'
        }
        
        # Flash message categories
        self.flash_categories = {
            'session_expired': 'warning',
            'session_not_found': 'info',
            'session_invalid': 'warning',
            'session_security_error': 'error',
            'session_database_error': 'error',
            'session_general_error': 'error'
        }
    
    def handle_session_expired(self, error: SessionExpiredError, endpoint: Optional[str] = None) -> Any:
        """
        Handle session expiration errors
        
        Args:
            error: SessionExpiredError instance
            endpoint: Current endpoint name
            
        Returns:
            Flask response (redirect or JSON)
        """
        logger.info(f"Session expired: {error}")
        
        # Clear session cookie
        if self._is_api_request():
            response_data = {
                'success': False,
                'error': 'session_expired',
                'message': self.error_messages['session_expired'],
                'redirect': url_for('login')
            }
            response = make_response(jsonify(response_data), 401)
        else:
            flash(self.error_messages['session_expired'], self.flash_categories['session_expired'])
            next_url = request.url if request.url != request.base_url else None
            login_url = url_for('login', next=next_url) if next_url else url_for('login')
            response = make_response(redirect(login_url))
        
        # Clear session cookie
        self.cookie_manager.clear_session_cookie(response)
        return response
    
    def handle_session_not_found(self, error: SessionNotFoundError, endpoint: Optional[str] = None) -> Any:
        """
        Handle session not found errors
        
        Args:
            error: SessionNotFoundError instance
            endpoint: Current endpoint name
            
        Returns:
            Flask response (redirect or JSON)
        """
        logger.debug(f"Session not found: {error}")
        
        if self._is_api_request():
            response_data = {
                'success': False,
                'error': 'session_not_found',
                'message': self.error_messages['session_not_found'],
                'redirect': url_for('login')
            }
            response = make_response(jsonify(response_data), 401)
        else:
            flash(self.error_messages['session_not_found'], self.flash_categories['session_not_found'])
            next_url = request.url if request.url != request.base_url else None
            login_url = url_for('login', next=next_url) if next_url else url_for('login')
            response = make_response(redirect(login_url))
        
        # Clear session cookie
        self.cookie_manager.clear_session_cookie(response)
        return response
    
    def handle_session_validation_error(self, error: SessionValidationError, endpoint: Optional[str] = None) -> Any:
        """
        Handle general session validation errors
        
        Args:
            error: SessionValidationError instance
            endpoint: Current endpoint name
            
        Returns:
            Flask response (redirect or JSON)
        """
        logger.warning(f"Session validation error: {error}")
        
        # Determine error type and message
        error_type = 'session_invalid'
        if 'security' in str(error).lower():
            error_type = 'session_security_error'
        elif 'database' in str(error).lower():
            error_type = 'session_database_error'
        
        if self._is_api_request():
            response_data = {
                'success': False,
                'error': error_type,
                'message': self.error_messages[error_type],
                'redirect': url_for('login')
            }
            response = make_response(jsonify(response_data), 401)
        else:
            flash(self.error_messages[error_type], self.flash_categories[error_type])
            next_url = request.url if request.url != request.base_url else None
            login_url = url_for('login', next=next_url) if next_url else url_for('login')
            response = make_response(redirect(login_url))
        
        # Clear session cookie
        self.cookie_manager.clear_session_cookie(response)
        return response
    
    def handle_general_session_error(self, error: Exception, endpoint: Optional[str] = None) -> Any:
        """
        Handle general session-related errors
        
        Args:
            error: Exception instance
            endpoint: Current endpoint name
            
        Returns:
            Flask response (redirect or JSON)
        """
        logger.error(f"General session error: {error}")
        
        if self._is_api_request():
            response_data = {
                'success': False,
                'error': 'session_general_error',
                'message': self.error_messages['session_general_error']
            }
            response = make_response(jsonify(response_data), 500)
        else:
            flash(self.error_messages['session_general_error'], self.flash_categories['session_general_error'])
            # For general errors, redirect to current page or index
            response = make_response(redirect(request.referrer or url_for('index')))
        
        return response
    
    def create_error_handler_decorator(self, handler_func: Callable) -> Callable:
        """
        Create a decorator that wraps functions with session error handling
        
        Args:
            handler_func: Function to handle errors
            
        Returns:
            Decorator function
        """
        def decorator(func):
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except SessionExpiredError as e:
                    return self.handle_session_expired(e, request.endpoint)
                except SessionNotFoundError as e:
                    return self.handle_session_not_found(e, request.endpoint)
                except SessionValidationError as e:
                    return self.handle_session_validation_error(e, request.endpoint)
                except Exception as e:
                    # Only handle session-related exceptions
                    if 'session' in str(e).lower():
                        return self.handle_general_session_error(e, request.endpoint)
                    else:
                        # Re-raise non-session errors
                        raise
            return wrapper
        return decorator
    
    def _is_api_request(self) -> bool:
        """Check if current request is an API request"""
        try:
            # Check if request path starts with /api/
            if request.path.startswith('/api/'):
                return True
            
            # Check Accept header for JSON
            accept_header = request.headers.get('Accept', '')
            if 'application/json' in accept_header:
                return True
            
            # Check Content-Type for JSON
            content_type = request.headers.get('Content-Type', '')
            if 'application/json' in content_type:
                return True
            
            return False
        except Exception:
            return False
    
    def create_session_error_page(self, error_type: str, error_message: str) -> str:
        """
        Create a custom error page for session errors
        
        Args:
            error_type: Type of error
            error_message: Error message to display
            
        Returns:
            Rendered HTML template
        """
        try:
            return render_template(
                'errors/session_error.html',
                error_type=error_type,
                error_message=error_message,
                login_url=url_for('login')
            )
        except Exception:
            # Fallback to simple HTML if template doesn't exist
            return f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Session Error</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 40px; }}
                    .error-container {{ max-width: 600px; margin: 0 auto; text-align: center; }}
                    .error-message {{ color: #d32f2f; margin: 20px 0; }}
                    .login-button {{ 
                        background-color: #1976d2; 
                        color: white; 
                        padding: 10px 20px; 
                        text-decoration: none; 
                        border-radius: 4px; 
                        display: inline-block; 
                        margin-top: 20px;
                    }}
                </style>
            </head>
            <body>
                <div class="error-container">
                    <h1>Session Error</h1>
                    <p class="error-message">{error_message}</p>
                    <a href="{url_for('login')}" class="login-button">Log In</a>
                </div>
            </body>
            </html>
            """


def create_session_error_handler(cookie_manager: SessionCookieManager) -> SessionErrorHandler:
    """
    Create session error handler
    
    Args:
        cookie_manager: Session cookie manager instance
        
    Returns:
        SessionErrorHandler instance
    """
    return SessionErrorHandler(cookie_manager)


# Decorator for session error handling
def with_session_error_handling(cookie_manager: SessionCookieManager):
    """
    Decorator to add session error handling to routes
    
    Args:
        cookie_manager: Session cookie manager instance
        
    Returns:
        Decorator function
    """
    error_handler = create_session_error_handler(cookie_manager)
    return error_handler.create_error_handler_decorator(error_handler.handle_general_session_error)
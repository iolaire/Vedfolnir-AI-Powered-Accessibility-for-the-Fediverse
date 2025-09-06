# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Session Error Handling System

This module provides comprehensive error handling for database session management,
including user-friendly error messages, automatic recovery, proper redirects,
and memory cleanup recovery mechanisms.
"""

import gc
import asyncio
from logging import getLogger
from typing import Optional, Dict, Any, Callable
from datetime import datetime, timezone
from flask import request, redirect, url_for, make_response, jsonify, render_template
from unified_session_manager import SessionValidationError, SessionExpiredError, SessionNotFoundError
from session_cookie_manager import SessionCookieManager
from responsiveness_error_recovery import ResponsivenessIssueType, with_responsiveness_recovery
from notification_helpers import send_admin_notification
from models import NotificationType, NotificationPriority
# # from notification_flash_replacement import send_notification  # Removed - using unified notification system  # Removed - using unified notification system

logger = getLogger(__name__)

class SessionErrorHandler:
    """Handles session-related errors with user-friendly responses and memory cleanup recovery"""
    
    def __init__(self, cookie_manager: SessionCookieManager):
        self.cookie_manager = cookie_manager
        
        # Error message templates
        self.error_messages = {
            'session_expired': 'Your session has expired. Please log in again.',
            'session_not_found': 'Please log in to continue.',
            'session_invalid': 'Your session is invalid. Please log in again.',
            'session_security_error': 'Security validation failed. Please log in again.',
            'session_database_error': 'A database error occurred. Please try again.',
            'session_general_error': 'A session error occurred. Please try again.',
            'session_memory_error': 'Session memory issue detected. System cleanup initiated.'
        }
        
        # Flash message categories
        self.flash_categories = {
            'session_expired': 'warning',
            'session_not_found': 'info',
            'session_invalid': 'warning',
            'session_security_error': 'error',
            'session_database_error': 'error',
            'session_general_error': 'error',
            'session_memory_error': 'warning'
        }
        
        # Memory cleanup recovery configuration
        self.memory_recovery_config = {
            'cleanup_threshold_mb': 100,  # Trigger cleanup if session memory > 100MB
            'max_cleanup_attempts': 3,
            'cleanup_delay': 2.0  # seconds between cleanup attempts
        }
        
        # Recovery statistics
        self.recovery_stats = {
            'memory_cleanups': 0,
            'successful_cleanups': 0,
            'failed_cleanups': 0,
            'total_memory_freed_mb': 0.0,
            'last_cleanup': None
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
            # Send warning notification
            from notification_helpers import send_warning_notification
            send_warning_notification("Your session has expired. Please log in again.", "Session Expired")
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
            # Send error notification
            from notification_helpers import send_error_notification
            send_error_notification("Session not found. Please log in again.", "Session Not Found")
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
            # Send error notification
            from notification_helpers import send_error_notification
            send_error_notification("Session validation failed. Please log in again.", "Session Validation Failed")
            next_url = request.url if request.url != request.base_url else None
            login_url = url_for('login', next=next_url) if next_url else url_for('login')
            response = make_response(redirect(login_url))
        
        # Clear session cookie
        self.cookie_manager.clear_session_cookie(response)
        return response
    
    def handle_general_session_error(self, error: Exception, endpoint: Optional[str] = None) -> Any:
        """
        Handle general session-related errors with memory cleanup recovery
        
        Args:
            error: Exception instance
            endpoint: Current endpoint name
            
        Returns:
            Flask response (redirect or JSON)
        """
        logger.error(f"General session error: {error}")
        
        # Check if this might be a memory-related session error
        if self._is_memory_related_error(error):
            asyncio.create_task(self._attempt_session_memory_cleanup(error))
        
        if self._is_api_request():
            response_data = {
                'success': False,
                'error': 'session_general_error',
                'message': self.error_messages['session_general_error']
            }
            response = make_response(jsonify(response_data), 500)
        else:
            # Send error notification
            from notification_helpers import send_error_notification
            send_error_notification("A session error occurred. Please try again.", "Session Error")
            # For general errors, redirect to current page or index
            response = make_response(redirect(request.referrer or url_for('main.index')))
        
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
    
    def _is_memory_related_error(self, error: Exception) -> bool:
        """Check if error is related to memory issues"""
        error_message = str(error).lower()
        memory_indicators = [
            'memory',
            'out of memory',
            'memoryerror',
            'allocation',
            'cache',
            'session size',
            'too large',
            'resource exhausted'
        ]
        
        return any(indicator in error_message for indicator in memory_indicators)
    
    async def _attempt_session_memory_cleanup(self, error: Exception) -> Dict[str, Any]:
        """Attempt to clean up session memory issues"""
        cleanup_result = {
            'success': False,
            'actions_taken': [],
            'memory_freed_mb': 0.0,
            'cleanup_time': 0
        }
        
        start_time = datetime.now(timezone.utc)
        
        try:
            logger.info("Starting session memory cleanup recovery")
            self.recovery_stats['memory_cleanups'] += 1
            
            # Step 1: Get initial memory usage
            initial_memory = self._get_process_memory_mb()
            
            # Step 2: Force garbage collection
            gc.collect()
            post_gc_memory = self._get_process_memory_mb()
            memory_freed_gc = initial_memory - post_gc_memory
            
            cleanup_result['actions_taken'].append({
                'action': 'garbage_collection',
                'memory_freed_mb': memory_freed_gc,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            # Step 3: Clear session-related caches (if available)
            cache_cleanup_result = await self._clear_session_caches()
            cleanup_result['actions_taken'].append({
                'action': 'session_cache_cleanup',
                'result': cache_cleanup_result,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            # Step 4: Check final memory usage
            final_memory = self._get_process_memory_mb()
            total_memory_freed = initial_memory - final_memory
            cleanup_result['memory_freed_mb'] = total_memory_freed
            
            # Determine success
            if total_memory_freed > 0:
                cleanup_result['success'] = True
                self.recovery_stats['successful_cleanups'] += 1
                self.recovery_stats['total_memory_freed_mb'] += total_memory_freed
                
                logger.info(f"Session memory cleanup successful - freed {total_memory_freed:.1f}MB")
                
                # Send success notification to admins
                await send_admin_notification(
                    message=f"Session memory cleanup completed successfully - freed {total_memory_freed:.1f}MB",
                    notification_type=NotificationType.SUCCESS,
                    title="Session Memory Cleanup Success",
                    priority=NotificationPriority.NORMAL,
                    system_health_data={
                        'cleanup_type': 'session_memory',
                        'memory_freed_mb': total_memory_freed,
                        'actions_taken': len(cleanup_result['actions_taken']),
                        'original_error': str(error)
                    }
                )
            else:
                self.recovery_stats['failed_cleanups'] += 1
                logger.warning("Session memory cleanup did not free significant memory")
                
                # Send warning notification
                await send_admin_notification(
                    message=f"Session memory cleanup completed but freed minimal memory ({total_memory_freed:.1f}MB)",
                    notification_type=NotificationType.WARNING,
                    title="Session Memory Cleanup Warning",
                    priority=NotificationPriority.NORMAL,
                    system_health_data={
                        'cleanup_type': 'session_memory',
                        'memory_freed_mb': total_memory_freed,
                        'original_error': str(error)
                    }
                )
        
        except Exception as cleanup_error:
            logger.error(f"Session memory cleanup failed: {cleanup_error}")
            self.recovery_stats['failed_cleanups'] += 1
            
            cleanup_result['actions_taken'].append({
                'action': 'cleanup_error',
                'error': str(cleanup_error),
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            # Send error notification
            await send_admin_notification(
                message=f"Session memory cleanup failed: {str(cleanup_error)}",
                notification_type=NotificationType.ERROR,
                title="Session Memory Cleanup Failed",
                priority=NotificationPriority.HIGH,
                system_health_data={
                    'cleanup_type': 'session_memory',
                    'cleanup_error': str(cleanup_error),
                    'original_error': str(error)
                },
                requires_admin_action=True
            )
        
        finally:
            cleanup_result['cleanup_time'] = (datetime.now(timezone.utc) - start_time).total_seconds()
            self.recovery_stats['last_cleanup'] = datetime.now(timezone.utc)
        
        return cleanup_result
    
    async def _clear_session_caches(self) -> Dict[str, Any]:
        """Clear session-related caches to free memory"""
        cache_result = {
            'caches_cleared': [],
            'estimated_memory_freed': 0
        }
        
        try:
            # Clear Flask session cache if available
            try:
                from flask import session
                if hasattr(session, 'clear'):
                    session.clear()
                    cache_result['caches_cleared'].append('flask_session')
            except Exception:
                pass
            
            # Clear any application-specific session caches
            # This would be implemented based on the actual session management system
            
            # Estimate memory freed (rough estimate)
            cache_result['estimated_memory_freed'] = len(cache_result['caches_cleared']) * 0.5  # 0.5MB per cache
            
        except Exception as e:
            cache_result['error'] = str(e)
        
        return cache_result
    
    def _get_process_memory_mb(self) -> float:
        """Get current process memory usage in MB"""
        try:
            import psutil
            import os
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / (1024 * 1024)
        except ImportError:
            return 0.0
        except Exception:
            return 0.0
    
    def get_session_recovery_stats(self) -> Dict[str, Any]:
        """Get session error recovery statistics"""
        return {
            'memory_cleanups': self.recovery_stats['memory_cleanups'],
            'successful_cleanups': self.recovery_stats['successful_cleanups'],
            'failed_cleanups': self.recovery_stats['failed_cleanups'],
            'cleanup_success_rate': (
                self.recovery_stats['successful_cleanups'] / self.recovery_stats['memory_cleanups']
                if self.recovery_stats['memory_cleanups'] > 0 else 0.0
            ),
            'total_memory_freed_mb': self.recovery_stats['total_memory_freed_mb'],
            'last_cleanup': self.recovery_stats['last_cleanup'].isoformat() if self.recovery_stats['last_cleanup'] else None
        }

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
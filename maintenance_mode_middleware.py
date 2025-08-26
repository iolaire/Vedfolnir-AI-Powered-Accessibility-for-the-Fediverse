# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Maintenance Mode Middleware

Flask middleware that automatically applies maintenance mode checks to all requests.
Provides request interception, operation blocking logic, and admin user bypass functionality.
"""

import logging
import time
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from collections import defaultdict
import threading

from flask import Flask, request, jsonify, g, current_app
from flask_login import current_user

from enhanced_maintenance_mode_service import EnhancedMaintenanceModeService
from maintenance_operation_classifier import MaintenanceOperationClassifier, OperationType
from maintenance_response_helper import MaintenanceResponseHelper
from models import User, UserRole

logger = logging.getLogger(__name__)


class MaintenanceModeMiddleware:
    """
    Flask middleware for automatic maintenance mode checking
    
    Features:
    - Automatic request interception with before_request hook
    - Admin user bypass functionality
    - Operation classification and blocking decisions
    - Consistent HTTP 503 maintenance responses
    - Request logging and monitoring
    - Integration with existing authentication systems
    """
    
    def __init__(self, app: Flask, maintenance_service: EnhancedMaintenanceModeService):
        """
        Initialize maintenance mode middleware
        
        Args:
            app: Flask application instance
            maintenance_service: Enhanced maintenance mode service
        """
        self.app = app
        self.maintenance_service = maintenance_service
        self.operation_classifier = MaintenanceOperationClassifier()
        self.response_helper = MaintenanceResponseHelper()
        
        # Request logging and monitoring
        self._blocked_attempts = defaultdict(int)
        self._admin_bypasses = defaultdict(int)
        self._request_stats = {
            'total_requests': 0,
            'blocked_requests': 0,
            'admin_bypasses': 0,
            'maintenance_responses': 0
        }
        self._stats_lock = threading.RLock()
        
        # Register middleware hooks
        self._register_middleware_hooks()
        
        logger.info("Maintenance mode middleware initialized")
    
    def _register_middleware_hooks(self):
        """Register Flask middleware hooks"""
        try:
            # Register before_request hook with high priority
            self.app.before_request(self.before_request)
            
            logger.debug("Maintenance mode middleware hooks registered")
            
        except Exception as e:
            logger.error(f"Error registering maintenance mode middleware hooks: {str(e)}")
            raise
    
    def before_request(self) -> Optional[object]:
        """
        Process request before route handler - main middleware entry point
        
        Returns:
            Response object if request should be blocked, None to continue
        """
        try:
            # Update request statistics
            with self._stats_lock:
                self._request_stats['total_requests'] += 1
            
            # Skip maintenance checks for certain endpoints
            if self._should_skip_maintenance_check():
                return None
            
            # Get current maintenance status
            maintenance_status = self.maintenance_service.get_maintenance_status()
            
            # If maintenance is not active, allow all requests
            if not maintenance_status.is_active:
                return None
            
            # Get current user for admin bypass check
            user = self._get_current_user()
            
            # Check if user is admin and should bypass maintenance
            if self.is_admin_user(user):
                self._log_admin_bypass(user)
                return None
            
            # Get endpoint and method for operation classification
            # Use request.path for classification (patterns expect URL paths like /start_caption_generation)
            # but keep endpoint name for logging
            endpoint_for_classification = request.path
            endpoint_for_logging = request.endpoint or request.path
            method = request.method
            
            # Check if operation is allowed during maintenance
            if self.is_allowed_operation(endpoint_for_classification, user, method):
                return None
            
            # Operation is blocked - log attempt and return maintenance response
            self._log_blocked_attempt(endpoint_for_logging, user, method)
            
            with self._stats_lock:
                self._request_stats['blocked_requests'] += 1
                self._request_stats['maintenance_responses'] += 1
            
            # Use the path for maintenance response (same as used for classification)
            # This ensures consistent operation description in maintenance messages
            return self.create_maintenance_response(endpoint_for_classification)
            
        except Exception as e:
            logger.error(f"Error in maintenance mode middleware: {str(e)}")
            # On error, allow request to continue to prevent system lockout
            return None
    
    def is_admin_user(self, user: Optional[User]) -> bool:
        """
        Identify admin users who should bypass maintenance blocks
        
        Args:
            user: User object to check (can be None)
            
        Returns:
            True if user is admin and should bypass maintenance
        """
        try:
            if user is None:
                return False
            
            # Check if user has admin role
            if hasattr(user, 'role') and user.role == UserRole.ADMIN:
                logger.debug(f"Admin user bypass: {getattr(user, 'username', 'unknown')} (ID: {getattr(user, 'id', 'unknown')})")
                return True
            
            # Additional admin checks if needed
            if hasattr(user, 'is_admin') and callable(user.is_admin):
                return user.is_admin()
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking admin user status: {str(e)}")
            # Default to not admin on error
            return False
    
    def is_allowed_operation(self, endpoint: str, user: Optional[User] = None, method: str = 'GET') -> bool:
        """
        Check if operation is allowed during maintenance using operation classifier
        
        Args:
            endpoint: Flask endpoint or URL path
            user: User attempting the operation (optional)
            method: HTTP method
            
        Returns:
            True if operation is allowed, False if blocked
        """
        try:
            # Use the maintenance service to check if operation is blocked
            # This handles test mode, admin bypass, and all other logic correctly
            is_blocked = self.maintenance_service.is_operation_blocked(endpoint, user)
            
            # Log operation classification for debugging
            operation_type = self.operation_classifier.classify_operation(endpoint, method)
            logger.debug(f"Operation {endpoint} ({method}) classified as {operation_type.value}, blocked: {is_blocked}")
            
            return not is_blocked
            
        except Exception as e:
            logger.error(f"Error checking operation allowance for {endpoint}: {str(e)}")
            # Default to allowing operations on error
            return True
    
    def create_maintenance_response(self, operation: str) -> object:
        """
        Create consistent HTTP 503 maintenance response using response helper
        
        Args:
            operation: Operation that was blocked
            
        Returns:
            Flask Response object with maintenance message
        """
        try:
            # Get maintenance status
            maintenance_status = self.maintenance_service.get_maintenance_status()
            
            # Classify operation for better messaging
            operation_type = self.operation_classifier.classify_operation(operation, 'POST')
            
            # Use response helper to create standardized response
            response = self.response_helper.create_flask_response(operation, maintenance_status, operation_type)
            
            logger.debug(f"Created maintenance response for operation {operation} (type: {operation_type.value})")
            return response
            
        except Exception as e:
            logger.error(f"Error creating maintenance response: {str(e)}")
            
            # Fallback response
            fallback_response = jsonify({
                'error': 'Service Unavailable',
                'message': 'System maintenance is in progress. Please try again later.',
                'maintenance_active': True,
                'operation': operation,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            fallback_response.status_code = 503
            return fallback_response
    
    def log_blocked_attempt(self, endpoint: str, user: Optional[User] = None, method: str = 'GET') -> None:
        """
        Log blocked operation attempt with user context
        
        Args:
            endpoint: Endpoint that was blocked
            user: User who attempted the operation
            method: HTTP method used
        """
        self._log_blocked_attempt(endpoint, user, method)
    
    def _log_blocked_attempt(self, endpoint: str, user: Optional[User] = None, method: str = 'GET') -> None:
        """
        Internal method to log blocked operation attempts
        
        Args:
            endpoint: Endpoint that was blocked
            user: User who attempted the operation
            method: HTTP method used
        """
        try:
            # Update blocked attempts counter
            attempt_key = f"{endpoint}:{method}"
            with self._stats_lock:
                self._blocked_attempts[attempt_key] += 1
            
            # Prepare log context
            log_context = {
                'event_type': 'maintenance_operation_blocked',
                'endpoint': endpoint,
                'method': method,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'user_agent': request.headers.get('User-Agent', 'unknown'),
                'remote_addr': request.remote_addr,
                'attempt_count': self._blocked_attempts[attempt_key]
            }
            
            # Add user context if available
            if user:
                log_context.update({
                    'user_id': getattr(user, 'id', None),
                    'username': getattr(user, 'username', 'unknown'),
                    'user_role': getattr(user, 'role', UserRole.VIEWER).value if hasattr(user, 'role') else 'unknown'
                })
            else:
                log_context.update({
                    'user_id': None,
                    'username': 'anonymous',
                    'user_role': 'anonymous'
                })
            
            # Log the blocked attempt
            logger.info(f"Maintenance mode blocked operation: {method} {endpoint}", extra=log_context)
            
            # Log to maintenance service for centralized tracking
            self.maintenance_service.log_maintenance_event(
                'operation_blocked',
                {
                    'endpoint': endpoint,
                    'method': method,
                    'user_context': {
                        'user_id': log_context.get('user_id'),
                        'username': log_context.get('username'),
                        'role': log_context.get('user_role')
                    },
                    'request_context': {
                        'user_agent': log_context.get('user_agent'),
                        'remote_addr': log_context.get('remote_addr')
                    },
                    'attempt_count': log_context.get('attempt_count')
                }
            )
            
        except Exception as e:
            logger.error(f"Error logging blocked attempt: {str(e)}")
    
    def _log_admin_bypass(self, user: User) -> None:
        """
        Log admin user bypass for monitoring
        
        Args:
            user: Admin user who bypassed maintenance
        """
        try:
            user_key = f"user_{getattr(user, 'id', 'unknown')}"
            with self._stats_lock:
                self._admin_bypasses[user_key] += 1
                self._request_stats['admin_bypasses'] += 1
            
            log_context = {
                'event_type': 'maintenance_admin_bypass',
                'user_id': getattr(user, 'id', None),
                'username': getattr(user, 'username', 'unknown'),
                'endpoint': request.endpoint or request.path,
                'method': request.method,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'bypass_count': self._admin_bypasses[user_key]
            }
            
            logger.info(f"Admin bypass during maintenance: {log_context['username']}", extra=log_context)
            
        except Exception as e:
            logger.error(f"Error logging admin bypass: {str(e)}")
    
    def _should_skip_maintenance_check(self) -> bool:
        """
        Determine if maintenance check should be skipped for current request
        
        Returns:
            True if maintenance check should be skipped
        """
        try:
            # Skip for static files
            if request.endpoint == 'static':
                return True
            
            # Skip for health check endpoints
            if request.endpoint in ['health', 'health_check', 'api.health']:
                return True
            
            # Skip for maintenance status API endpoints
            if request.path and '/api/maintenance/status' in request.path:
                return True
            
            # Skip for certain admin endpoints that should always be accessible
            admin_always_allowed = [
                'admin.maintenance',
                'admin.system_health',
                'admin.emergency_maintenance'
            ]
            
            if request.endpoint in admin_always_allowed:
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking if maintenance check should be skipped: {str(e)}")
            return False
    
    def _get_current_user(self) -> Optional[User]:
        """
        Get current user from Flask-Login or session context
        
        Returns:
            Current user object or None
        """
        try:
            # Try Flask-Login current_user first
            if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
                return current_user
            
            # Try session context as fallback
            if hasattr(g, 'session_context') and g.session_context:
                session_context = g.session_context
                if 'user_id' in session_context:
                    # Create a minimal user object from session context
                    class SessionUser:
                        def __init__(self, session_data):
                            self.id = session_data.get('user_id')
                            self.username = session_data.get('username', 'unknown')
                            self.role = UserRole(session_data.get('role', 'viewer'))
                    
                    return SessionUser(session_context)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting current user: {str(e)}")
            return None
    
    def get_middleware_stats(self) -> Dict[str, Any]:
        """
        Get middleware statistics and monitoring data
        
        Returns:
            Dictionary with middleware statistics
        """
        try:
            with self._stats_lock:
                stats = self._request_stats.copy()
                blocked_attempts = dict(self._blocked_attempts)
                admin_bypasses = dict(self._admin_bypasses)
            
            # Get maintenance service stats
            maintenance_stats = self.maintenance_service.get_service_stats()
            
            return {
                'middleware_stats': stats,
                'blocked_attempts_by_endpoint': blocked_attempts,
                'admin_bypasses_by_user': admin_bypasses,
                'maintenance_service_stats': maintenance_stats,
                'operation_classifier_stats': self.operation_classifier.get_classification_stats(),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting middleware stats: {str(e)}")
            return {
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def reset_stats(self) -> None:
        """Reset middleware statistics (useful for testing)"""
        try:
            with self._stats_lock:
                self._blocked_attempts.clear()
                self._admin_bypasses.clear()
                self._request_stats = {
                    'total_requests': 0,
                    'blocked_requests': 0,
                    'admin_bypasses': 0,
                    'maintenance_responses': 0
                }
            
            logger.info("Maintenance mode middleware statistics reset")
            
        except Exception as e:
            logger.error(f"Error resetting middleware stats: {str(e)}")
    
    def get_blocked_attempts_count(self, endpoint: str = None, method: str = None) -> int:
        """
        Get count of blocked attempts for specific endpoint/method or total
        
        Args:
            endpoint: Specific endpoint to check (optional)
            method: Specific method to check (optional)
            
        Returns:
            Count of blocked attempts
        """
        try:
            with self._stats_lock:
                if endpoint and method:
                    attempt_key = f"{endpoint}:{method}"
                    return self._blocked_attempts.get(attempt_key, 0)
                elif endpoint:
                    # Sum all methods for this endpoint
                    return sum(count for key, count in self._blocked_attempts.items() 
                             if key.startswith(f"{endpoint}:"))
                else:
                    # Return total blocked requests
                    return self._request_stats.get('blocked_requests', 0)
                    
        except Exception as e:
            logger.error(f"Error getting blocked attempts count: {str(e)}")
            return 0
    
    def get_admin_bypasses_count(self, user_id: int = None) -> int:
        """
        Get count of admin bypasses for specific user or total
        
        Args:
            user_id: Specific user ID to check (optional)
            
        Returns:
            Count of admin bypasses
        """
        try:
            with self._stats_lock:
                if user_id:
                    user_key = f"user_{user_id}"
                    return self._admin_bypasses.get(user_key, 0)
                else:
                    return self._request_stats.get('admin_bypasses', 0)
                    
        except Exception as e:
            logger.error(f"Error getting admin bypasses count: {str(e)}")
            return 0
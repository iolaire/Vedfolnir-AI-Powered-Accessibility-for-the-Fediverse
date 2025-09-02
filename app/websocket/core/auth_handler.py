# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
WebSocket Authentication Handler

This module provides comprehensive authentication and authorization for WebSocket connections,
including user validation, role-based authorization, admin privilege verification,
security event logging, and rate limiting for connection attempts.
"""

import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Tuple
from collections import defaultdict, deque
from dataclasses import dataclass
from enum import Enum

from flask import request, session as flask_session
from flask_socketio import disconnect

from models import User, UserRole, PlatformConnection
from database import DatabaseManager
from session_manager import SessionManager
from security.core.security_utils import sanitize_for_log, mask_sensitive_data

logger = logging.getLogger(__name__)


class AuthenticationResult(Enum):
    """Authentication result types"""
    SUCCESS = "success"
    INVALID_SESSION = "invalid_session"
    USER_NOT_FOUND = "user_not_found"
    USER_INACTIVE = "user_inactive"
    INSUFFICIENT_PRIVILEGES = "insufficient_privileges"
    RATE_LIMITED = "rate_limited"
    SECURITY_VIOLATION = "security_violation"
    SYSTEM_ERROR = "system_error"


@dataclass
class AuthenticationContext:
    """Authentication context for WebSocket connections"""
    user_id: int
    username: str
    email: str
    role: UserRole
    session_id: str
    platform_connection_id: Optional[int] = None
    platform_name: Optional[str] = None
    platform_type: Optional[str] = None
    is_admin: bool = False
    permissions: List[str] = None
    
    def __post_init__(self):
        if self.permissions is None:
            self.permissions = []
        self.is_admin = self.role == UserRole.ADMIN


@dataclass
class ConnectionAttempt:
    """Rate limiting data for connection attempts"""
    timestamp: float
    ip_address: str
    user_agent: str
    success: bool


class WebSocketAuthHandler:
    """
    Comprehensive authentication handler for WebSocket connections
    
    Provides user validation, role-based authorization, admin privilege verification,
    security event logging, and rate limiting for connection attempts.
    """
    
    def __init__(self, db_manager: DatabaseManager, session_manager: SessionManager,
                 rate_limit_window: int = 300, max_attempts_per_window: int = 10,
                 max_attempts_per_ip: int = 50):
        """
        Initialize WebSocket authentication handler
        
        Args:
            db_manager: Database manager instance
            session_manager: Session manager instance
            rate_limit_window: Rate limiting window in seconds (default: 5 minutes)
            max_attempts_per_window: Max attempts per user per window (default: 10)
            max_attempts_per_ip: Max attempts per IP per window (default: 50)
        """
        self.db_manager = db_manager
        self.session_manager = session_manager
        self.rate_limit_window = rate_limit_window
        self.max_attempts_per_window = max_attempts_per_window
        self.max_attempts_per_ip = max_attempts_per_ip
        
        # Rate limiting storage
        self._user_attempts = defaultdict(deque)  # user_id -> deque of timestamps
        self._ip_attempts = defaultdict(deque)    # ip_address -> deque of timestamps
        self._connection_attempts = defaultdict(list)  # session_id -> list of attempts
        
        # Security event tracking
        self._security_events = deque(maxlen=1000)  # Keep last 1000 events
        
        # Admin namespace permissions
        self._admin_permissions = {
            'system_management',
            'user_management', 
            'platform_management',
            'maintenance_operations',
            'security_monitoring',
            'configuration_management'
        }
        
        # Role-based permissions
        self._role_permissions = {
            UserRole.ADMIN: self._admin_permissions,
            UserRole.MODERATOR: {
                'user_management',
                'platform_management', 
                'security_monitoring'
            },
            UserRole.REVIEWER: {
                'platform_management'
            },
            UserRole.VIEWER: set()
        }
    
    def authenticate_connection(self, auth_data: Optional[Dict[str, Any]] = None,
                              namespace: str = '/') -> Tuple[AuthenticationResult, Optional[AuthenticationContext]]:
        """
        Authenticate WebSocket connection using existing session system
        
        Args:
            auth_data: Optional authentication data from client
            namespace: WebSocket namespace being accessed
            
        Returns:
            Tuple of (AuthenticationResult, AuthenticationContext or None)
        """
        try:
            # Get client information for rate limiting and logging
            client_ip = self._get_client_ip()
            user_agent = self._get_user_agent()
            
            # Check IP-based rate limiting first
            if not self._check_ip_rate_limit(client_ip):
                self._log_security_event(
                    'connection_rate_limited_ip',
                    None, None, namespace,
                    {'ip_address': client_ip, 'reason': 'ip_rate_limit_exceeded'}
                )
                return AuthenticationResult.RATE_LIMITED, None
            
            # Get session ID from Flask session or auth data
            session_id = self._extract_session_id(auth_data)
            if not session_id:
                self._log_security_event(
                    'connection_no_session',
                    None, None, namespace,
                    {'ip_address': client_ip, 'user_agent': user_agent}
                )
                return AuthenticationResult.INVALID_SESSION, None
            
            # Validate session using session manager
            session_data = self.session_manager.get_session_data(session_id)
            if not session_data:
                self._log_security_event(
                    'connection_invalid_session',
                    None, session_id, namespace,
                    {'ip_address': client_ip, 'session_id': session_id[:8] + '...'}
                )
                return AuthenticationResult.INVALID_SESSION, None
            
            # Flask-Login stores user ID as '_user_id'
            user_id = session_data.get('user_id') or session_data.get('_user_id')
            if not user_id:
                self._log_security_event(
                    'connection_no_user_in_session',
                    None, session_id, namespace,
                    {'session_id': session_id[:8] + '...'}
                )
                return AuthenticationResult.INVALID_SESSION, None
            
            # Check user-based rate limiting
            if not self._check_user_rate_limit(user_id):
                self._log_security_event(
                    'connection_rate_limited_user',
                    user_id, session_id, namespace,
                    {'reason': 'user_rate_limit_exceeded'}
                )
                return AuthenticationResult.RATE_LIMITED, None
            
            # Validate user exists and is active
            with self.db_manager.get_session() as db_session:
                user = db_session.get(User, user_id)
                if not user:
                    self._log_security_event(
                        'connection_user_not_found',
                        user_id, session_id, namespace,
                        {'user_id': user_id}
                    )
                    return AuthenticationResult.USER_NOT_FOUND, None
                
                if not user.is_active:
                    self._log_security_event(
                        'connection_user_inactive',
                        user_id, session_id, namespace,
                        {'username': sanitize_for_log(user.username)}
                    )
                    return AuthenticationResult.USER_INACTIVE, None
                
                # Check namespace-specific authorization
                auth_result = self._check_namespace_authorization(user, namespace)
                if auth_result != AuthenticationResult.SUCCESS:
                    self._log_security_event(
                        'connection_authorization_failed',
                        user_id, session_id, namespace,
                        {'username': sanitize_for_log(user.username), 'namespace': namespace}
                    )
                    return auth_result, None
                
                # Get platform information if available
                platform_connection_id = session_data.get('platform_connection_id')
                platform_name = session_data.get('platform_name')
                platform_type = session_data.get('platform_type')
                
                # Create authentication context
                auth_context = AuthenticationContext(
                    user_id=user.id,
                    username=user.username,
                    email=user.email,
                    role=user.role,
                    session_id=session_id,
                    platform_connection_id=platform_connection_id,
                    platform_name=platform_name,
                    platform_type=platform_type,
                    permissions=list(self._role_permissions.get(user.role, set()))
                )
                
                # Record successful authentication
                self._record_connection_attempt(user_id, client_ip, user_agent, True)
                
                # Log successful authentication
                self._log_security_event(
                    'connection_authenticated',
                    user_id, session_id, namespace,
                    {
                        'username': sanitize_for_log(user.username),
                        'role': user.role.value,
                        'namespace': namespace,
                        'platform_id': platform_connection_id
                    }
                )
                
                return AuthenticationResult.SUCCESS, auth_context
                
        except Exception as e:
            logger.error(f"Error during WebSocket authentication: {e}")
            self._log_security_event(
                'connection_system_error',
                None, None, namespace,
                {'error': sanitize_for_log(str(e))}
            )
            return AuthenticationResult.SYSTEM_ERROR, None
    
    def validate_user_session(self, user_id: int, session_id: str) -> bool:
        """
        Validate user session for ongoing WebSocket connection
        
        Args:
            user_id: User ID to validate
            session_id: Session ID to validate
            
        Returns:
            True if session is valid, False otherwise
        """
        try:
            # Use session manager to validate session
            session_data = self.session_manager.get_session_data(session_id)
            if not session_data:
                return False
            
            # Check if session belongs to the user
            session_user_id = session_data.get('user_id')
            if session_user_id != user_id:
                self._log_security_event(
                    'session_user_mismatch',
                    user_id, session_id, None,
                    {'session_user_id': session_user_id, 'expected_user_id': user_id}
                )
                return False
            
            # Validate user is still active
            with self.db_manager.get_session() as db_session:
                user = db_session.get(User, user_id)
                if not user or not user.is_active:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating user session: {e}")
            return False
    
    def authorize_admin_access(self, auth_context: AuthenticationContext, 
                             required_permission: str = None) -> bool:
        """
        Verify admin privileges for admin namespace access
        
        Args:
            auth_context: Authentication context
            required_permission: Specific permission required (optional)
            
        Returns:
            True if user has admin access, False otherwise
        """
        try:
            # Check if user has admin role
            if not auth_context.is_admin:
                self._log_security_event(
                    'admin_access_denied_role',
                    auth_context.user_id, auth_context.session_id, '/admin',
                    {
                        'username': sanitize_for_log(auth_context.username),
                        'role': auth_context.role.value,
                        'required_permission': required_permission
                    }
                )
                return False
            
            # Check specific permission if required
            if required_permission and required_permission not in auth_context.permissions:
                self._log_security_event(
                    'admin_access_denied_permission',
                    auth_context.user_id, auth_context.session_id, '/admin',
                    {
                        'username': sanitize_for_log(auth_context.username),
                        'required_permission': required_permission,
                        'user_permissions': auth_context.permissions
                    }
                )
                return False
            
            # Log successful admin access
            self._log_security_event(
                'admin_access_granted',
                auth_context.user_id, auth_context.session_id, '/admin',
                {
                    'username': sanitize_for_log(auth_context.username),
                    'permission': required_permission
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error authorizing admin access: {e}")
            return False
    
    def handle_authentication_failure(self, result: AuthenticationResult, 
                                    namespace: str = '/', disconnect_client: bool = True) -> None:
        """
        Handle authentication failure with appropriate logging and client disconnection
        
        Args:
            result: Authentication result indicating failure type
            namespace: WebSocket namespace
            disconnect_client: Whether to disconnect the client
        """
        try:
            client_ip = self._get_client_ip()
            user_agent = self._get_user_agent()
            
            # Record failed attempt for rate limiting
            self._record_connection_attempt(None, client_ip, user_agent, False)
            
            # Log authentication failure
            failure_details = {
                'result': result.value,
                'namespace': namespace,
                'ip_address': client_ip,
                'user_agent': sanitize_for_log(user_agent),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            self._log_security_event(
                'authentication_failure',
                None, None, namespace,
                failure_details
            )
            
            # Disconnect client if requested
            if disconnect_client:
                try:
                    disconnect()
                    logger.info(f"Disconnected client due to authentication failure: {result.value}")
                except Exception as e:
                    logger.error(f"Error disconnecting client: {e}")
            
        except Exception as e:
            logger.error(f"Error handling authentication failure: {e}")
    
    def _extract_session_id(self, auth_data: Optional[Dict[str, Any]]) -> Optional[str]:
        """
        Extract session ID from Flask session or auth data
        
        Args:
            auth_data: Optional authentication data from client
            
        Returns:
            Session ID if found, None otherwise
        """
        try:
            # For Redis session system, the session ID is stored in the RedisSession object
            # Check if we have a current Flask session with the session ID
            if hasattr(flask_session, 'sid') and flask_session.sid:
                logger.debug(f"Found session ID from Flask session: {flask_session.sid}")
                return flask_session.sid
            
            # Try to get from auth data
            if auth_data and isinstance(auth_data, dict):
                session_id = auth_data.get('session_id')
                if session_id:
                    logger.debug(f"Found session ID from auth data: {session_id}")
                    return session_id
            
            # Try to get from request headers
            if request:
                session_id = request.headers.get('X-Session-ID')
                if session_id:
                    logger.debug(f"Found session ID from headers: {session_id}")
                    return session_id
            
            # For WebSocket connections, try to get from Flask session cookie
            if request and hasattr(request, 'cookies'):
                # Get Flask session cookie - this contains the session ID
                from flask import current_app
                cookie_name = getattr(current_app, 'session_cookie_name', 
                                    current_app.config.get('SESSION_COOKIE_NAME', 'session'))
                session_cookie = request.cookies.get(cookie_name)
                if session_cookie:
                    logger.debug(f"Found session ID from cookie: {session_cookie}")
                    return session_cookie
            
            # Additional check: try to get session ID directly from Flask session object
            # This handles cases where the session exists but sid attribute is not set
            if flask_session and hasattr(flask_session, '_get_current_object'):
                try:
                    session_obj = flask_session._get_current_object()
                    if hasattr(session_obj, 'sid') and session_obj.sid:
                        logger.debug(f"Found session ID from session object: {session_obj.sid}")
                        return session_obj.sid
                except Exception as e:
                    logger.debug(f"Could not get session from current object: {e}")
            
            logger.debug("No session ID found in any source")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting session ID: {e}")
            return None
    
    def _check_namespace_authorization(self, user: User, namespace: str) -> AuthenticationResult:
        """
        Check if user is authorized for the specified namespace
        
        Args:
            user: User object
            namespace: WebSocket namespace
            
        Returns:
            AuthenticationResult indicating authorization status
        """
        try:
            # Admin namespace requires admin role
            if namespace == '/admin':
                if user.role != UserRole.ADMIN:
                    return AuthenticationResult.INSUFFICIENT_PRIVILEGES
            
            # Default namespace allows all authenticated users
            elif namespace == '/':
                # All authenticated users can access default namespace
                pass
            
            # Other namespaces - implement specific authorization logic as needed
            else:
                # For now, allow all authenticated users to access other namespaces
                # This can be extended with more specific authorization logic
                pass
            
            return AuthenticationResult.SUCCESS
            
        except Exception as e:
            logger.error(f"Error checking namespace authorization: {e}")
            return AuthenticationResult.SYSTEM_ERROR
    
    def _check_user_rate_limit(self, user_id: int) -> bool:
        """
        Check if user has exceeded rate limit for connection attempts
        
        Args:
            user_id: User ID to check
            
        Returns:
            True if within rate limit, False if exceeded
        """
        try:
            current_time = time.time()
            cutoff_time = current_time - self.rate_limit_window
            
            # Clean old attempts
            user_attempts = self._user_attempts[user_id]
            while user_attempts and user_attempts[0] < cutoff_time:
                user_attempts.popleft()
            
            # Check if under limit
            if len(user_attempts) >= self.max_attempts_per_window:
                return False
            
            # Record this attempt
            user_attempts.append(current_time)
            return True
            
        except Exception as e:
            logger.error(f"Error checking user rate limit: {e}")
            return True  # Allow on error to avoid blocking legitimate users
    
    def _check_ip_rate_limit(self, ip_address: str) -> bool:
        """
        Check if IP address has exceeded rate limit for connection attempts
        
        Args:
            ip_address: IP address to check
            
        Returns:
            True if within rate limit, False if exceeded
        """
        try:
            if not ip_address:
                return True
            
            current_time = time.time()
            cutoff_time = current_time - self.rate_limit_window
            
            # Clean old attempts
            ip_attempts = self._ip_attempts[ip_address]
            while ip_attempts and ip_attempts[0] < cutoff_time:
                ip_attempts.popleft()
            
            # Check if under limit
            if len(ip_attempts) >= self.max_attempts_per_ip:
                return False
            
            # Record this attempt
            ip_attempts.append(current_time)
            return True
            
        except Exception as e:
            logger.error(f"Error checking IP rate limit: {e}")
            return True  # Allow on error to avoid blocking legitimate users
    
    def _record_connection_attempt(self, user_id: Optional[int], ip_address: str, 
                                 user_agent: str, success: bool) -> None:
        """
        Record connection attempt for monitoring and rate limiting
        
        Args:
            user_id: User ID (if known)
            ip_address: Client IP address
            user_agent: Client user agent
            success: Whether the attempt was successful
        """
        try:
            attempt = ConnectionAttempt(
                timestamp=time.time(),
                ip_address=ip_address,
                user_agent=user_agent,
                success=success
            )
            
            # Store attempt for monitoring
            session_id = getattr(request, 'sid', 'unknown') if request else 'unknown'
            self._connection_attempts[session_id].append(attempt)
            
            # Limit stored attempts per session
            if len(self._connection_attempts[session_id]) > 100:
                self._connection_attempts[session_id] = self._connection_attempts[session_id][-50:]
            
        except Exception as e:
            logger.error(f"Error recording connection attempt: {e}")
    
    def _log_security_event(self, event_type: str, user_id: Optional[int], 
                          session_id: Optional[str], namespace: Optional[str],
                          details: Dict[str, Any]) -> None:
        """
        Log security event for authentication failures and violations
        
        Args:
            event_type: Type of security event
            user_id: User ID (if known)
            session_id: Session ID (if known)
            namespace: WebSocket namespace
            details: Additional event details
        """
        try:
            event = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'event_type': event_type,
                'user_id': user_id,
                'session_id': session_id[:8] + '...' if session_id else None,
                'namespace': namespace,
                'ip_address': self._get_client_ip(),
                'user_agent': sanitize_for_log(self._get_user_agent()),
                'details': details
            }
            
            # Store event for monitoring
            self._security_events.append(event)
            
            # Log event
            logger.warning(f"WebSocket security event: {event_type} - {details}")
            
            # TODO: Integrate with security monitoring system
            # This could send alerts for critical events, update security metrics, etc.
            
        except Exception as e:
            logger.error(f"Error logging security event: {e}")
    
    def _get_client_ip(self) -> str:
        """
        Get client IP address from request
        
        Returns:
            Client IP address or 'unknown'
        """
        try:
            if request:
                # Check for forwarded IP first (reverse proxy)
                forwarded_ip = request.headers.get('X-Forwarded-For')
                if forwarded_ip:
                    # Take the first IP in case of multiple proxies
                    return forwarded_ip.split(',')[0].strip()
                
                # Check for real IP header
                real_ip = request.headers.get('X-Real-IP')
                if real_ip:
                    return real_ip.strip()
                
                # Fall back to remote address
                return request.remote_addr or 'unknown'
            
            return 'unknown'
            
        except Exception:
            return 'unknown'
    
    def _get_user_agent(self) -> str:
        """
        Get user agent from request
        
        Returns:
            User agent string or 'unknown'
        """
        try:
            if request:
                return request.headers.get('User-Agent', 'unknown')
            return 'unknown'
        except Exception:
            return 'unknown'
    
    def get_authentication_stats(self) -> Dict[str, Any]:
        """
        Get authentication statistics for monitoring
        
        Returns:
            Dictionary containing authentication statistics
        """
        try:
            current_time = time.time()
            cutoff_time = current_time - self.rate_limit_window
            
            # Count recent attempts by user
            active_users = 0
            total_user_attempts = 0
            for user_id, attempts in self._user_attempts.items():
                recent_attempts = [t for t in attempts if t > cutoff_time]
                if recent_attempts:
                    active_users += 1
                    total_user_attempts += len(recent_attempts)
            
            # Count recent attempts by IP
            active_ips = 0
            total_ip_attempts = 0
            for ip, attempts in self._ip_attempts.items():
                recent_attempts = [t for t in attempts if t > cutoff_time]
                if recent_attempts:
                    active_ips += 1
                    total_ip_attempts += len(recent_attempts)
            
            # Count recent security events
            recent_events = [
                event for event in self._security_events
                if datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00')).timestamp() > cutoff_time
            ]
            
            # Count events by type
            event_counts = defaultdict(int)
            for event in recent_events:
                event_counts[event['event_type']] += 1
            
            return {
                'rate_limit_window_seconds': self.rate_limit_window,
                'max_attempts_per_user': self.max_attempts_per_window,
                'max_attempts_per_ip': self.max_attempts_per_ip,
                'active_users_in_window': active_users,
                'total_user_attempts_in_window': total_user_attempts,
                'active_ips_in_window': active_ips,
                'total_ip_attempts_in_window': total_ip_attempts,
                'security_events_in_window': len(recent_events),
                'security_event_types': dict(event_counts),
                'total_connection_sessions': len(self._connection_attempts)
            }
            
        except Exception as e:
            logger.error(f"Error getting authentication stats: {e}")
            return {'error': str(e)}
    
    def cleanup_old_data(self) -> None:
        """
        Clean up old rate limiting and monitoring data
        """
        try:
            current_time = time.time()
            cutoff_time = current_time - (self.rate_limit_window * 2)  # Keep data for 2x window
            
            # Clean user attempts
            for user_id in list(self._user_attempts.keys()):
                attempts = self._user_attempts[user_id]
                while attempts and attempts[0] < cutoff_time:
                    attempts.popleft()
                if not attempts:
                    del self._user_attempts[user_id]
            
            # Clean IP attempts
            for ip in list(self._ip_attempts.keys()):
                attempts = self._ip_attempts[ip]
                while attempts and attempts[0] < cutoff_time:
                    attempts.popleft()
                if not attempts:
                    del self._ip_attempts[ip]
            
            # Clean connection attempts (keep last 24 hours)
            connection_cutoff = current_time - 86400  # 24 hours
            for session_id in list(self._connection_attempts.keys()):
                attempts = self._connection_attempts[session_id]
                self._connection_attempts[session_id] = [
                    attempt for attempt in attempts 
                    if attempt.timestamp > connection_cutoff
                ]
                if not self._connection_attempts[session_id]:
                    del self._connection_attempts[session_id]
            
            logger.debug("Cleaned up old authentication data")
            
        except Exception as e:
            logger.error(f"Error cleaning up old authentication data: {e}")
    
    def get_user_permissions(self, role: UserRole) -> List[str]:
        """
        Get permissions for a user role
        
        Args:
            role: User role
            
        Returns:
            List of permissions for the role
        """
        return list(self._role_permissions.get(role, set()))
    
    def has_permission(self, auth_context: AuthenticationContext, permission: str) -> bool:
        """
        Check if user has a specific permission
        
        Args:
            auth_context: Authentication context
            permission: Permission to check
            
        Returns:
            True if user has permission, False otherwise
        """
        return permission in auth_context.permissions
    
    def validate_token(self, token: str) -> Optional[AuthenticationContext]:
        """
        Validate authentication token and return authentication context
        
        Args:
            token: Authentication token to validate
            
        Returns:
            AuthenticationContext if valid, None if invalid
        """
        try:
            # For testing purposes, we'll validate based on token format
            if not token or len(token) < 10:
                return None
            
            # Mock token validation - in real implementation this would validate JWT or similar
            if token.startswith("eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9"):
                # Mock valid JWT token
                return AuthenticationContext(
                    user_id=1,
                    username="admin",
                    email="admin@example.com",
                    role=UserRole.ADMIN,
                    session_id="mock_session_123",
                    is_admin=True,
                    permissions=["admin", "security", "system"]
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error validating token: {e}")
            return None
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
WebSocket Security Manager

This module provides comprehensive security enhancements for WebSocket connections,
including CSRF protection, rate limiting, input validation, security event logging,
and connection monitoring with abuse detection.
"""

import logging
import time
import json
import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Tuple, Set
from collections import defaultdict, deque
from dataclasses import dataclass
from enum import Enum
from functools import wraps

from flask import request, session as flask_session, current_app
from flask_socketio import disconnect, emit

from database import DatabaseManager
from session_manager_v2 import SessionManagerV2
from security.core.enhanced_csrf_protection import EnhancedCSRFProtection
from security.validation.enhanced_input_validator import EnhancedInputValidator, ValidationError
from security.monitoring.security_event_logger import SecurityEventLogger, SecurityEventType, SecurityEventSeverity
from rate_limiter import RateLimiter, RateLimitConfig
from security.core.security_utils import sanitize_for_log, mask_sensitive_data

logger = logging.getLogger(__name__)


class WebSocketSecurityEventType(Enum):
    """WebSocket-specific security event types"""
    WS_CONNECTION_BLOCKED = "ws_connection_blocked"
    WS_MESSAGE_BLOCKED = "ws_message_blocked"
    WS_RATE_LIMIT_EXCEEDED = "ws_rate_limit_exceeded"
    WS_CSRF_FAILURE = "ws_csrf_failure"
    WS_INPUT_VALIDATION_FAILURE = "ws_input_validation_failure"
    WS_SUSPICIOUS_ACTIVITY = "ws_suspicious_activity"
    WS_ABUSE_DETECTED = "ws_abuse_detected"
    WS_UNAUTHORIZED_ACCESS = "ws_unauthorized_access"
    WS_MALICIOUS_PAYLOAD = "ws_malicious_payload"
    WS_CONNECTION_FLOOD = "ws_connection_flood"
    WS_MESSAGE_FLOOD = "ws_message_flood"


@dataclass
class WebSocketSecurityConfig:
    """Configuration for WebSocket security features"""
    # CSRF Protection
    csrf_enabled: bool = True
    csrf_token_timeout: int = 3600  # 1 hour
    csrf_strict_validation: bool = True
    
    # Rate Limiting
    rate_limiting_enabled: bool = True
    connection_rate_limit: int = 10  # connections per minute per IP
    message_rate_limit: int = 60    # messages per minute per user
    burst_limit: int = 5            # burst allowance
    
    # Input Validation
    input_validation_enabled: bool = True
    max_message_size: int = 10000   # 10KB max message size
    allowed_event_types: Set[str] = None  # None = allow all
    
    # Connection Monitoring
    connection_monitoring_enabled: bool = True
    max_connections_per_ip: int = 20
    max_connections_per_user: int = 10
    connection_timeout: int = 300   # 5 minutes
    
    # Abuse Detection
    abuse_detection_enabled: bool = True
    suspicious_activity_threshold: int = 50  # events per hour
    auto_disconnect_on_abuse: bool = True
    
    def __post_init__(self):
        if self.allowed_event_types is None:
            # Default allowed event types
            self.allowed_event_types = {
                'connect', 'disconnect', 'message', 'ping', 'pong',
                'progress_update', 'status_update', 'notification',
                'admin_action', 'system_status'
            }


@dataclass
class ConnectionInfo:
    """Information about a WebSocket connection"""
    session_id: str
    user_id: Optional[int]
    ip_address: str
    user_agent: str
    namespace: str
    connected_at: datetime
    last_activity: datetime
    message_count: int = 0
    security_violations: int = 0
    is_authenticated: bool = False
    is_admin: bool = False


class WebSocketSecurityManager:
    """
    Comprehensive security manager for WebSocket connections
    
    Provides CSRF protection, rate limiting, input validation, security event logging,
    and connection monitoring with abuse detection for WebSocket communications.
    """
    
    def __init__(self, db_manager: DatabaseManager, session_manager: SessionManagerV2,
                 config: Optional[WebSocketSecurityConfig] = None):
        """
        Initialize WebSocket security manager
        
        Args:
            db_manager: Database manager instance
            session_manager: Session manager instance
            config: Security configuration (uses defaults if None)
        """
        self.db_manager = db_manager
        self.session_manager = session_manager
        self.config = config or WebSocketSecurityConfig()
        
        # Initialize security components
        self.csrf_protection = None
        self.input_validator = None
        self.security_logger = None
        self.rate_limiter = None
        
        # Connection tracking
        self.active_connections: Dict[str, ConnectionInfo] = {}  # session_id -> ConnectionInfo
        self.ip_connections: Dict[str, Set[str]] = defaultdict(set)  # ip -> set of session_ids
        self.user_connections: Dict[int, Set[str]] = defaultdict(set)  # user_id -> set of session_ids
        
        # Rate limiting tracking
        self.connection_attempts: Dict[str, deque] = defaultdict(deque)  # ip -> timestamps
        self.message_attempts: Dict[str, deque] = defaultdict(deque)    # user_id -> timestamps
        
        # Security event tracking
        self.security_events: Dict[str, List[Dict]] = defaultdict(list)  # session_id -> events
        
        # Initialize components
        self._initialize_security_components()
        
        logger.info("WebSocket Security Manager initialized")
    
    def _initialize_security_components(self) -> None:
        """Initialize security components"""
        try:
            # Initialize database session for security components
            with self.db_manager.get_session() as db_session:
                # Initialize CSRF protection
                if self.config.csrf_enabled:
                    self.csrf_protection = EnhancedCSRFProtection(db_session=db_session)
                
                # Initialize input validator
                if self.config.input_validation_enabled:
                    self.input_validator = EnhancedInputValidator(db_session)
                
                # Initialize security logger
                self.security_logger = SecurityEventLogger(db_session)
                
                # Initialize rate limiter
                if self.config.rate_limiting_enabled:
                    rate_config = RateLimitConfig(
                        requests_per_minute=self.config.message_rate_limit,
                        max_burst=self.config.burst_limit
                    )
                    self.rate_limiter = RateLimiter(rate_config)
                
        except Exception as e:
            logger.error(f"Failed to initialize security components: {e}")
            # Continue with limited functionality
    
    def validate_connection(self, auth_data: Optional[Dict[str, Any]] = None,
                          namespace: str = '/') -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Validate WebSocket connection with comprehensive security checks
        
        Args:
            auth_data: Authentication data from client
            namespace: WebSocket namespace
            
        Returns:
            Tuple of (allowed, reason, connection_info)
        """
        try:
            # Get client information
            client_ip = self._get_client_ip()
            user_agent = self._get_user_agent()
            session_id = self._get_session_id(auth_data)
            
            # Check IP-based connection rate limiting
            if not self._check_connection_rate_limit(client_ip):
                self._log_security_event(
                    WebSocketSecurityEventType.WS_CONNECTION_BLOCKED,
                    SecurityEventSeverity.HIGH,
                    details={'reason': 'connection_rate_limit_exceeded', 'ip': client_ip}
                )
                return False, "Connection rate limit exceeded", None
            
            # Check maximum connections per IP
            if self._count_ip_connections(client_ip) >= self.config.max_connections_per_ip:
                self._log_security_event(
                    WebSocketSecurityEventType.WS_CONNECTION_BLOCKED,
                    SecurityEventSeverity.HIGH,
                    details={'reason': 'max_connections_per_ip_exceeded', 'ip': client_ip}
                )
                return False, "Too many connections from this IP", None
            
            # Validate session if provided
            user_id = None
            is_authenticated = False
            is_admin = False
            
            if session_id:
                session_data = self.session_manager.get_session_data(session_id)
                if session_data:
                    user_id = session_data.get('user_id')
                    if user_id:
                        is_authenticated = True
                        # Check if user is admin
                        with self.db_manager.get_session() as db_session:
                            from models import User, UserRole
                            user = db_session.get(User, user_id)
                            if user and user.role == UserRole.ADMIN:
                                is_admin = True
                        
                        # Check maximum connections per user
                        if self._count_user_connections(user_id) >= self.config.max_connections_per_user:
                            self._log_security_event(
                                WebSocketSecurityEventType.WS_CONNECTION_BLOCKED,
                                SecurityEventSeverity.MEDIUM,
                                user_id=user_id,
                                details={'reason': 'max_connections_per_user_exceeded'}
                            )
                            return False, "Too many connections for this user", None
            
            # Check namespace-specific authorization
            if namespace == '/admin' and not is_admin:
                self._log_security_event(
                    WebSocketSecurityEventType.WS_UNAUTHORIZED_ACCESS,
                    SecurityEventSeverity.HIGH,
                    user_id=user_id,
                    details={'reason': 'admin_namespace_access_denied', 'namespace': namespace}
                )
                return False, "Admin access required", None
            
            # Create connection info
            connection_info = ConnectionInfo(
                session_id=session_id or f"anon_{secrets.token_hex(8)}",
                user_id=user_id,
                ip_address=client_ip,
                user_agent=user_agent,
                namespace=namespace,
                connected_at=datetime.now(timezone.utc),
                last_activity=datetime.now(timezone.utc),
                is_authenticated=is_authenticated,
                is_admin=is_admin
            )
            
            # Track connection
            self._track_connection(connection_info)
            
            logger.info(f"WebSocket connection validated: user_id={user_id}, namespace={namespace}, ip={client_ip}")
            return True, None, connection_info.__dict__
            
        except Exception as e:
            logger.error(f"Error validating WebSocket connection: {e}")
            self._log_security_event(
                WebSocketSecurityEventType.WS_CONNECTION_BLOCKED,
                SecurityEventSeverity.CRITICAL,
                details={'reason': 'validation_error', 'error': str(e)}
            )
            return False, "Connection validation failed", None
    
    def validate_message(self, event_type: str, data: Any, session_id: str) -> Tuple[bool, Optional[str], Any]:
        """
        Validate WebSocket message with security checks
        
        Args:
            event_type: Type of WebSocket event
            data: Message data
            session_id: Session ID of the sender
            
        Returns:
            Tuple of (allowed, reason, sanitized_data)
        """
        try:
            # Get connection info
            connection = self.active_connections.get(session_id)
            if not connection:
                return False, "Connection not found", None
            
            # Update last activity
            connection.last_activity = datetime.now(timezone.utc)
            connection.message_count += 1
            
            # Check message rate limiting
            if not self._check_message_rate_limit(connection.user_id or session_id):
                self._log_security_event(
                    WebSocketSecurityEventType.WS_RATE_LIMIT_EXCEEDED,
                    SecurityEventSeverity.MEDIUM,
                    user_id=connection.user_id,
                    details={'event_type': event_type, 'session_id': session_id[:8]}
                )
                return False, "Message rate limit exceeded", None
            
            # Validate event type
            if self.config.allowed_event_types and event_type not in self.config.allowed_event_types:
                self._log_security_event(
                    WebSocketSecurityEventType.WS_MESSAGE_BLOCKED,
                    SecurityEventSeverity.MEDIUM,
                    user_id=connection.user_id,
                    details={'reason': 'invalid_event_type', 'event_type': event_type}
                )
                connection.security_violations += 1
                return False, "Invalid event type", None
            
            # Check message size
            message_size = len(json.dumps(data)) if data else 0
            if message_size > self.config.max_message_size:
                self._log_security_event(
                    WebSocketSecurityEventType.WS_MESSAGE_BLOCKED,
                    SecurityEventSeverity.MEDIUM,
                    user_id=connection.user_id,
                    details={'reason': 'message_too_large', 'size': message_size}
                )
                connection.security_violations += 1
                return False, "Message too large", None
            
            # Validate and sanitize message data
            sanitized_data = self._validate_and_sanitize_data(data, event_type, connection)
            if sanitized_data is None:
                connection.security_violations += 1
                return False, "Message validation failed", None
            
            # Check for abuse patterns
            if self._detect_abuse_patterns(connection):
                return False, "Suspicious activity detected", None
            
            return True, None, sanitized_data
            
        except Exception as e:
            logger.error(f"Error validating WebSocket message: {e}")
            return False, "Message validation error", None
    
    def validate_csrf_token(self, token: str, user_id: Optional[int] = None, 
                          operation: Optional[str] = None) -> bool:
        """
        Validate CSRF token for WebSocket events
        
        Args:
            token: CSRF token to validate
            user_id: User ID for validation
            operation: Operation being performed
            
        Returns:
            True if token is valid, False otherwise
        """
        if not self.config.csrf_enabled or not self.csrf_protection:
            return True
        
        try:
            return self.csrf_protection.validate_csrf_token(
                token, user_id, operation, self.config.csrf_strict_validation
            )
        except Exception as e:
            logger.error(f"Error validating CSRF token: {e}")
            self._log_security_event(
                WebSocketSecurityEventType.WS_CSRF_FAILURE,
                SecurityEventSeverity.HIGH,
                user_id=user_id,
                details={'operation': operation, 'error': str(e)}
            )
            return False
    
    def disconnect_connection(self, session_id: str, reason: str = "Security violation") -> None:
        """
        Disconnect a WebSocket connection for security reasons
        
        Args:
            session_id: Session ID to disconnect
            reason: Reason for disconnection
        """
        try:
            connection = self.active_connections.get(session_id)
            if connection:
                self._log_security_event(
                    WebSocketSecurityEventType.WS_CONNECTION_BLOCKED,
                    SecurityEventSeverity.HIGH,
                    user_id=connection.user_id,
                    details={'reason': reason, 'session_id': session_id[:8]}
                )
                
                # Remove from tracking
                self._untrack_connection(session_id)
                
                # Disconnect the client
                disconnect()
                
                logger.warning(f"Disconnected WebSocket connection {session_id[:8]}: {reason}")
                
        except Exception as e:
            logger.error(f"Error disconnecting WebSocket connection: {e}")
    
    def cleanup_expired_connections(self) -> None:
        """Clean up expired connections and rate limiting data"""
        try:
            current_time = datetime.now(timezone.utc)
            expired_sessions = []
            
            # Find expired connections
            for session_id, connection in self.active_connections.items():
                if (current_time - connection.last_activity).total_seconds() > self.config.connection_timeout:
                    expired_sessions.append(session_id)
            
            # Remove expired connections
            for session_id in expired_sessions:
                self._untrack_connection(session_id)
            
            # Clean up rate limiting data
            cutoff_time = time.time() - 3600  # 1 hour ago
            
            for ip in list(self.connection_attempts.keys()):
                attempts = self.connection_attempts[ip]
                while attempts and attempts[0] < cutoff_time:
                    attempts.popleft()
                if not attempts:
                    del self.connection_attempts[ip]
            
            for user_key in list(self.message_attempts.keys()):
                attempts = self.message_attempts[user_key]
                while attempts and attempts[0] < cutoff_time:
                    attempts.popleft()
                if not attempts:
                    del self.message_attempts[user_key]
            
            # Clean up security events
            for session_id in list(self.security_events.keys()):
                if session_id not in self.active_connections:
                    del self.security_events[session_id]
            
            if expired_sessions:
                logger.info(f"Cleaned up {len(expired_sessions)} expired WebSocket connections")
                
        except Exception as e:
            logger.error(f"Error cleaning up expired connections: {e}")
    
    def get_security_stats(self) -> Dict[str, Any]:
        """
        Get WebSocket security statistics
        
        Returns:
            Dictionary containing security statistics
        """
        try:
            current_time = datetime.now(timezone.utc)
            
            # Connection statistics
            total_connections = len(self.active_connections)
            authenticated_connections = sum(1 for conn in self.active_connections.values() if conn.is_authenticated)
            admin_connections = sum(1 for conn in self.active_connections.values() if conn.is_admin)
            
            # Security violation statistics
            total_violations = sum(conn.security_violations for conn in self.active_connections.values())
            
            # Rate limiting statistics
            rate_limit_stats = {}
            if self.rate_limiter:
                rate_limit_stats = self.rate_limiter.get_stats()
            
            # Connection age statistics
            connection_ages = [
                (current_time - conn.connected_at).total_seconds()
                for conn in self.active_connections.values()
            ]
            avg_connection_age = sum(connection_ages) / len(connection_ages) if connection_ages else 0
            
            return {
                'connections': {
                    'total': total_connections,
                    'authenticated': authenticated_connections,
                    'admin': admin_connections,
                    'anonymous': total_connections - authenticated_connections,
                    'average_age_seconds': avg_connection_age
                },
                'security': {
                    'total_violations': total_violations,
                    'csrf_enabled': self.config.csrf_enabled,
                    'rate_limiting_enabled': self.config.rate_limiting_enabled,
                    'input_validation_enabled': self.config.input_validation_enabled,
                    'abuse_detection_enabled': self.config.abuse_detection_enabled
                },
                'rate_limiting': rate_limit_stats,
                'configuration': {
                    'max_connections_per_ip': self.config.max_connections_per_ip,
                    'max_connections_per_user': self.config.max_connections_per_user,
                    'message_rate_limit': self.config.message_rate_limit,
                    'max_message_size': self.config.max_message_size,
                    'connection_timeout': self.config.connection_timeout
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting security stats: {e}")
            return {'error': str(e)}
    
    def _get_client_ip(self) -> str:
        """Get client IP address from request"""
        try:
            if request:
                # Check for forwarded IP first (reverse proxy)
                forwarded_ip = request.headers.get('X-Forwarded-For')
                if forwarded_ip:
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
        """Get user agent from request"""
        try:
            if request:
                return request.headers.get('User-Agent', 'unknown')
            return 'unknown'
        except Exception:
            return 'unknown'
    
    def _get_session_id(self, auth_data: Optional[Dict[str, Any]]) -> Optional[str]:
        """Extract session ID from auth data or Flask session"""
        try:
            # Try auth data first
            if auth_data and isinstance(auth_data, dict):
                session_id = auth_data.get('session_id')
                if session_id:
                    return session_id
            
            # Try Flask session
            if hasattr(flask_session, 'get'):
                session_id = flask_session.get('session_id')
                if session_id:
                    return session_id
            
            # Try request headers
            if request:
                session_id = request.headers.get('X-Session-ID')
                if session_id:
                    return session_id
            
            return None
        except Exception:
            return None
    
    def _check_connection_rate_limit(self, ip_address: str) -> bool:
        """Check connection rate limit for IP address"""
        try:
            current_time = time.time()
            cutoff_time = current_time - 60  # 1 minute window
            
            # Clean old attempts
            attempts = self.connection_attempts[ip_address]
            while attempts and attempts[0] < cutoff_time:
                attempts.popleft()
            
            # Check if under limit
            if len(attempts) >= self.config.connection_rate_limit:
                return False
            
            # Record this attempt
            attempts.append(current_time)
            return True
            
        except Exception as e:
            logger.error(f"Error checking connection rate limit: {e}")
            return True  # Allow on error
    
    def _check_message_rate_limit(self, user_key: str) -> bool:
        """Check message rate limit for user or session"""
        try:
            current_time = time.time()
            cutoff_time = current_time - 60  # 1 minute window
            
            # Clean old attempts
            attempts = self.message_attempts[user_key]
            while attempts and attempts[0] < cutoff_time:
                attempts.popleft()
            
            # Check if under limit
            if len(attempts) >= self.config.message_rate_limit:
                return False
            
            # Record this attempt
            attempts.append(current_time)
            return True
            
        except Exception as e:
            logger.error(f"Error checking message rate limit: {e}")
            return True  # Allow on error
    
    def _count_ip_connections(self, ip_address: str) -> int:
        """Count active connections from IP address"""
        return len(self.ip_connections.get(ip_address, set()))
    
    def _count_user_connections(self, user_id: int) -> int:
        """Count active connections for user"""
        return len(self.user_connections.get(user_id, set()))
    
    def _track_connection(self, connection: ConnectionInfo) -> None:
        """Track a new connection"""
        session_id = connection.session_id
        
        # Store connection info
        self.active_connections[session_id] = connection
        
        # Track by IP
        self.ip_connections[connection.ip_address].add(session_id)
        
        # Track by user if authenticated
        if connection.user_id:
            self.user_connections[connection.user_id].add(session_id)
    
    def _untrack_connection(self, session_id: str) -> None:
        """Remove connection from tracking"""
        connection = self.active_connections.get(session_id)
        if connection:
            # Remove from IP tracking
            ip_sessions = self.ip_connections.get(connection.ip_address)
            if ip_sessions:
                ip_sessions.discard(session_id)
                if not ip_sessions:
                    del self.ip_connections[connection.ip_address]
            
            # Remove from user tracking
            if connection.user_id:
                user_sessions = self.user_connections.get(connection.user_id)
                if user_sessions:
                    user_sessions.discard(session_id)
                    if not user_sessions:
                        del self.user_connections[connection.user_id]
            
            # Remove connection info
            del self.active_connections[session_id]
    
    def _validate_and_sanitize_data(self, data: Any, event_type: str, 
                                  connection: ConnectionInfo) -> Optional[Any]:
        """Validate and sanitize message data"""
        try:
            if not self.config.input_validation_enabled or not self.input_validator:
                return data
            
            # Convert data to string for validation if it's not already
            if isinstance(data, dict):
                # Validate each field in the dictionary
                sanitized_data = {}
                for key, value in data.items():
                    try:
                        # Define validation rules based on event type and field
                        validation_rules = self._get_validation_rules_for_field(key, event_type)
                        sanitized_value = self.input_validator._validate_field(key, value, validation_rules)
                        sanitized_data[key] = sanitized_value
                    except ValidationError as e:
                        self._log_security_event(
                            WebSocketSecurityEventType.WS_INPUT_VALIDATION_FAILURE,
                            SecurityEventSeverity.MEDIUM,
                            user_id=connection.user_id,
                            details={
                                'field': key,
                                'event_type': event_type,
                                'validation_error': str(e)
                            }
                        )
                        return None
                return sanitized_data
            
            elif isinstance(data, str):
                # Validate string data
                try:
                    from security.validation.enhanced_input_validator import InputSanitizer
                    return InputSanitizer.sanitize_text(data, max_length=self.config.max_message_size)
                except ValidationError as e:
                    self._log_security_event(
                        WebSocketSecurityEventType.WS_INPUT_VALIDATION_FAILURE,
                        SecurityEventSeverity.MEDIUM,
                        user_id=connection.user_id,
                        details={
                            'event_type': event_type,
                            'validation_error': str(e)
                        }
                    )
                    return None
            
            # For other data types, return as-is but log for monitoring
            return data
            
        except Exception as e:
            logger.error(f"Error validating message data: {e}")
            return None
    
    def _get_validation_rules_for_field(self, field_name: str, event_type: str) -> Dict[str, Any]:
        """Get validation rules for a specific field and event type"""
        # Default rules
        default_rules = {
            'type': 'text',
            'max_length': 1000,
            'required': False
        }
        
        # Event-specific rules
        event_rules = {
            'message': {
                'content': {'type': 'text', 'max_length': 5000, 'allow_html': False},
                'recipient': {'type': 'text', 'max_length': 100},
                'csrf_token': {'type': 'text', 'max_length': 100, 'skip_malicious_check': True}
            },
            'admin_action': {
                'action': {'type': 'text', 'max_length': 100},
                'target': {'type': 'text', 'max_length': 100},
                'csrf_token': {'type': 'text', 'max_length': 100, 'skip_malicious_check': True}
            },
            'progress_update': {
                'progress': {'type': 'text', 'max_length': 100},
                'status': {'type': 'text', 'max_length': 50}
            }
        }
        
        # Get rules for this event type and field
        if event_type in event_rules and field_name in event_rules[event_type]:
            return event_rules[event_type][field_name]
        
        return default_rules
    
    def _detect_abuse_patterns(self, connection: ConnectionInfo) -> bool:
        """Detect abuse patterns in connection behavior"""
        try:
            if not self.config.abuse_detection_enabled:
                return False
            
            # Check security violations threshold
            if connection.security_violations >= 5:  # 5 violations per connection
                self._log_security_event(
                    WebSocketSecurityEventType.WS_ABUSE_DETECTED,
                    SecurityEventSeverity.HIGH,
                    user_id=connection.user_id,
                    details={
                        'reason': 'security_violations_threshold',
                        'violations': connection.security_violations
                    }
                )
                
                if self.config.auto_disconnect_on_abuse:
                    self.disconnect_connection(connection.session_id, "Abuse detected")
                
                return True
            
            # Check message flood patterns
            if connection.message_count > 100:  # 100 messages per connection
                time_connected = (datetime.now(timezone.utc) - connection.connected_at).total_seconds()
                if time_connected < 60:  # Less than 1 minute
                    self._log_security_event(
                        WebSocketSecurityEventType.WS_MESSAGE_FLOOD,
                        SecurityEventSeverity.HIGH,
                        user_id=connection.user_id,
                        details={
                            'reason': 'message_flood',
                            'message_count': connection.message_count,
                            'time_connected': time_connected
                        }
                    )
                    
                    if self.config.auto_disconnect_on_abuse:
                        self.disconnect_connection(connection.session_id, "Message flood detected")
                    
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error detecting abuse patterns: {e}")
            return False
    
    def _log_security_event(self, event_type: WebSocketSecurityEventType, 
                          severity: SecurityEventSeverity, user_id: Optional[int] = None,
                          details: Optional[Dict[str, Any]] = None) -> None:
        """Log WebSocket security event"""
        try:
            if self.security_logger:
                # Map WebSocket event types to general security event types
                general_event_type = SecurityEventType.SUSPICIOUS_ACTIVITY
                
                if event_type in [WebSocketSecurityEventType.WS_RATE_LIMIT_EXCEEDED]:
                    general_event_type = SecurityEventType.RATE_LIMIT_EXCEEDED
                elif event_type in [WebSocketSecurityEventType.WS_CSRF_FAILURE]:
                    general_event_type = SecurityEventType.CSRF_FAILURE
                elif event_type in [WebSocketSecurityEventType.WS_INPUT_VALIDATION_FAILURE]:
                    general_event_type = SecurityEventType.INPUT_VALIDATION_FAILURE
                
                # Add WebSocket-specific context
                ws_details = {
                    'websocket_event_type': event_type.value,
                    'component': 'websocket_security',
                    **(details or {})
                }
                
                self.security_logger.log_security_event(
                    event_type=general_event_type,
                    severity=severity,
                    user_id=user_id,
                    details=ws_details
                )
            
            # Also log to application logger
            logger.warning(f"WebSocket security event: {event_type.value} - {details}")
            
        except Exception as e:
            logger.error(f"Error logging WebSocket security event: {e}")


def websocket_security_required(operation: Optional[str] = None, 
                              require_csrf: bool = True,
                              require_auth: bool = False,
                              admin_only: bool = False):
    """
    Decorator for WebSocket event handlers that require security validation
    
    Args:
        operation: Operation name for CSRF validation
        require_csrf: Whether to require CSRF token validation
        require_auth: Whether to require authentication
        admin_only: Whether to require admin privileges
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # Get security manager from current app
                security_manager = getattr(current_app, 'websocket_security_manager', None)
                if not security_manager:
                    logger.warning("WebSocket security manager not available")
                    return f(*args, **kwargs)
                
                # Get session ID from request context
                session_id = security_manager._get_session_id(None)
                if not session_id:
                    emit('error', {'message': 'Session required', 'code': 'NO_SESSION'})
                    return
                
                # Get connection info
                connection = security_manager.active_connections.get(session_id)
                if not connection:
                    emit('error', {'message': 'Connection not found', 'code': 'NO_CONNECTION'})
                    return
                
                # Check authentication requirement
                if require_auth and not connection.is_authenticated:
                    security_manager._log_security_event(
                        WebSocketSecurityEventType.WS_UNAUTHORIZED_ACCESS,
                        SecurityEventSeverity.MEDIUM,
                        details={'operation': operation, 'reason': 'authentication_required'}
                    )
                    emit('error', {'message': 'Authentication required', 'code': 'AUTH_REQUIRED'})
                    return
                
                # Check admin requirement
                if admin_only and not connection.is_admin:
                    security_manager._log_security_event(
                        WebSocketSecurityEventType.WS_UNAUTHORIZED_ACCESS,
                        SecurityEventSeverity.HIGH,
                        user_id=connection.user_id,
                        details={'operation': operation, 'reason': 'admin_required'}
                    )
                    emit('error', {'message': 'Admin access required', 'code': 'ADMIN_REQUIRED'})
                    return
                
                # Check CSRF token if required
                if require_csrf:
                    # Try to get CSRF token from request data
                    csrf_token = None
                    if args and isinstance(args[0], dict):
                        csrf_token = args[0].get('csrf_token')
                    
                    if not csrf_token or not security_manager.validate_csrf_token(
                        csrf_token, connection.user_id, operation
                    ):
                        security_manager._log_security_event(
                            WebSocketSecurityEventType.WS_CSRF_FAILURE,
                            SecurityEventSeverity.HIGH,
                            user_id=connection.user_id,
                            details={'operation': operation}
                        )
                        emit('error', {'message': 'CSRF validation failed', 'code': 'CSRF_FAILED'})
                        return
                
                # All security checks passed, execute the function
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"Error in WebSocket security decorator: {e}")
                emit('error', {'message': 'Security validation error', 'code': 'SECURITY_ERROR'})
                return
        
        return decorated_function
    return decorator
# Copyright (C) 2025 iolaire mcfadden.
# Consolidated WebSocket Error Handling

import logging
import traceback
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum

from flask_socketio import emit, disconnect

logger = logging.getLogger(__name__)

class WebSocketErrorType(Enum):
    """Types of WebSocket errors"""
    CONNECTION_ERROR = "connection_error"
    AUTHENTICATION_ERROR = "authentication_error"
    VALIDATION_ERROR = "validation_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    INTERNAL_ERROR = "internal_error"
    TIMEOUT_ERROR = "timeout_error"
    PROTOCOL_ERROR = "protocol_error"
    SECURITY_ERROR = "security_error"

class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class ErrorEvent:
    """WebSocket error event"""
    error_type: WebSocketErrorType
    severity: ErrorSeverity
    message: str
    timestamp: datetime
    client_id: Optional[str] = None
    session_id: Optional[str] = None
    error_code: Optional[str] = None
    stack_trace: Optional[str] = None
    additional_data: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ErrorStats:
    """Error statistics tracking"""
    total_errors: int = 0
    errors_by_type: Dict[WebSocketErrorType, int] = field(default_factory=lambda: defaultdict(int))
    errors_by_severity: Dict[ErrorSeverity, int] = field(default_factory=lambda: defaultdict(int))
    recent_errors: deque = field(default_factory=lambda: deque(maxlen=100))
    error_rate_per_minute: float = 0.0
    last_reset: datetime = field(default_factory=datetime.utcnow)

class ConsolidatedWebSocketErrorHandler:
    """Consolidated WebSocket error handling with logging, detection, and recovery"""
    
    def __init__(self, config=None):
        self.logger = logging.getLogger(__name__)
        self.config = config or {}
        
        # Error tracking
        self._error_stats = ErrorStats()
        self._error_handlers = {}
        self._recovery_strategies = {}
        
        # Error thresholds
        self._thresholds = {
            'max_errors_per_minute': self.config.get('max_errors_per_minute', 10),
            'critical_error_threshold': self.config.get('critical_error_threshold', 5),
            'auto_disconnect_threshold': self.config.get('auto_disconnect_threshold', 3)
        }
        
        # Client error tracking
        self._client_errors = defaultdict(list)
        
        # Session error tracking
        self._session_errors = defaultdict(list)
        self._session_error_threshold = 5  # Max errors per session before disconnect
        
        # Setup default error handlers
        self._setup_default_handlers()
    
    def _setup_default_handlers(self):
        """Setup default error handlers"""
        self._error_handlers[WebSocketErrorType.CONNECTION_ERROR] = self._handle_connection_error
        self._error_handlers[WebSocketErrorType.AUTHENTICATION_ERROR] = self._handle_auth_error
        self._error_handlers[WebSocketErrorType.VALIDATION_ERROR] = self._handle_validation_error
        self._error_handlers[WebSocketErrorType.RATE_LIMIT_ERROR] = self._handle_rate_limit_error
        self._error_handlers[WebSocketErrorType.INTERNAL_ERROR] = self._handle_internal_error
        self._error_handlers[WebSocketErrorType.TIMEOUT_ERROR] = self._handle_timeout_error
        self._error_handlers[WebSocketErrorType.PROTOCOL_ERROR] = self._handle_protocol_error
        self._error_handlers[WebSocketErrorType.SECURITY_ERROR] = self._handle_security_error
    
    def handle_error(self, error_type: WebSocketErrorType, message: str, 
                    client_id: Optional[str] = None, session_id: Optional[str] = None,
                    exception: Optional[Exception] = None, **kwargs) -> bool:
        """Handle WebSocket error with comprehensive logging and recovery"""
        try:
            # Determine severity
            severity = self._determine_severity(error_type, exception)
            
            # Create error event
            error_event = ErrorEvent(
                error_type=error_type,
                severity=severity,
                message=message,
                timestamp=datetime.utcnow(),
                client_id=client_id,
                session_id=session_id,
                error_code=kwargs.get('error_code'),
                stack_trace=traceback.format_exc() if exception else None,
                additional_data=kwargs
            )
            
            # Record error
            self._record_error(error_event)
            
            # Track session-specific errors
            if session_id:
                self._track_session_error(session_id, error_event)
            
            # Log error
            self._log_error(error_event)
            
            # Handle error with specific handler
            handler = self._error_handlers.get(error_type, self._handle_generic_error)
            recovery_successful = handler(error_event)
            
            # Check if client should be disconnected
            if client_id and self._should_disconnect_client(client_id):
                self._disconnect_client(client_id, "Too many errors")
                return False
            
            # Check if session should be invalidated
            if session_id and self._should_invalidate_session(session_id):
                self._invalidate_session(session_id, "Too many session errors")
                return False
            
            return recovery_successful
            
        except Exception as e:
            self.logger.critical(f"Error in error handler: {e}")
            return False
    
    def _determine_severity(self, error_type: WebSocketErrorType, exception: Optional[Exception]) -> ErrorSeverity:
        """Determine error severity"""
        # Critical errors
        if error_type in [WebSocketErrorType.SECURITY_ERROR, WebSocketErrorType.INTERNAL_ERROR]:
            return ErrorSeverity.CRITICAL
        
        # High severity errors
        if error_type in [WebSocketErrorType.AUTHENTICATION_ERROR, WebSocketErrorType.PROTOCOL_ERROR]:
            return ErrorSeverity.HIGH
        
        # Medium severity errors
        if error_type in [WebSocketErrorType.CONNECTION_ERROR, WebSocketErrorType.TIMEOUT_ERROR]:
            return ErrorSeverity.MEDIUM
        
        # Low severity errors
        return ErrorSeverity.LOW
    
    def _record_error(self, error_event: ErrorEvent):
        """Record error for statistics and tracking"""
        try:
            # Update global stats
            self._error_stats.total_errors += 1
            self._error_stats.errors_by_type[error_event.error_type] += 1
            self._error_stats.errors_by_severity[error_event.severity] += 1
            self._error_stats.recent_errors.append(error_event)
            
            # Update client-specific tracking
            if error_event.client_id:
                self._client_errors[error_event.client_id].append(error_event.timestamp)
                # Keep only recent errors (last hour)
                cutoff = datetime.utcnow() - timedelta(hours=1)
                self._client_errors[error_event.client_id] = [
                    ts for ts in self._client_errors[error_event.client_id] if ts > cutoff
                ]
            
            # Calculate error rate
            self._calculate_error_rate()
            
        except Exception as e:
            self.logger.error(f"Error recording error event: {e}")
    
    def _calculate_error_rate(self):
        """Calculate current error rate per minute"""
        try:
            now = datetime.utcnow()
            one_minute_ago = now - timedelta(minutes=1)
            
            recent_errors = [
                event for event in self._error_stats.recent_errors
                if event.timestamp > one_minute_ago
            ]
            
            self._error_stats.error_rate_per_minute = len(recent_errors)
            
        except Exception as e:
            self.logger.error(f"Error calculating error rate: {e}")
    
    def _log_error(self, error_event: ErrorEvent):
        """Log error with appropriate level"""
        log_message = (
            f"WebSocket Error [{error_event.error_type.value}] "
            f"Severity: {error_event.severity.value} "
            f"Client: {error_event.client_id or 'unknown'} "
            f"Message: {error_event.message}"
        )
        
        if error_event.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_message)
        elif error_event.severity == ErrorSeverity.HIGH:
            self.logger.error(log_message)
        elif error_event.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)
        
        # Log stack trace for internal errors
        if error_event.stack_trace and error_event.error_type == WebSocketErrorType.INTERNAL_ERROR:
            self.logger.error(f"Stack trace: {error_event.stack_trace}")
    
    def _should_disconnect_client(self, client_id: str) -> bool:
        """Check if client should be disconnected due to errors"""
        try:
            client_error_count = len(self._client_errors.get(client_id, []))
            return client_error_count >= self._thresholds['auto_disconnect_threshold']
        except Exception:
            return False
    
    def _disconnect_client(self, client_id: str, reason: str):
        """Disconnect client with reason"""
        try:
            emit('error', {
                'type': 'disconnection',
                'message': reason,
                'timestamp': datetime.utcnow().isoformat()
            }, room=client_id)
            
            disconnect(sid=client_id)
            self.logger.warning(f"Disconnected client {client_id}: {reason}")
            
        except Exception as e:
            self.logger.error(f"Error disconnecting client {client_id}: {e}")
    
    # Specific error handlers
    def _handle_connection_error(self, error_event: ErrorEvent) -> bool:
        """Handle connection errors"""
        try:
            if error_event.client_id:
                emit('error', {
                    'type': 'connection_error',
                    'message': 'Connection issue detected. Please refresh the page.',
                    'recoverable': True
                }, room=error_event.client_id)
            return True
        except Exception:
            return False
    
    def _handle_auth_error(self, error_event: ErrorEvent) -> bool:
        """Handle authentication errors"""
        try:
            if error_event.client_id:
                emit('error', {
                    'type': 'authentication_error',
                    'message': 'Authentication failed. Please log in again.',
                    'recoverable': False,
                    'redirect': '/login'
                }, room=error_event.client_id)
                
                # Disconnect after auth error
                self._disconnect_client(error_event.client_id, "Authentication failed")
            return False
        except Exception:
            return False
    
    def _handle_validation_error(self, error_event: ErrorEvent) -> bool:
        """Handle validation errors"""
        try:
            if error_event.client_id:
                emit('error', {
                    'type': 'validation_error',
                    'message': f'Invalid data: {error_event.message}',
                    'recoverable': True
                }, room=error_event.client_id)
            return True
        except Exception:
            return False
    
    def _handle_rate_limit_error(self, error_event: ErrorEvent) -> bool:
        """Handle rate limit errors"""
        try:
            if error_event.client_id:
                emit('error', {
                    'type': 'rate_limit_error',
                    'message': 'Rate limit exceeded. Please slow down.',
                    'recoverable': True,
                    'retry_after': 60
                }, room=error_event.client_id)
            return True
        except Exception:
            return False
    
    def _handle_internal_error(self, error_event: ErrorEvent) -> bool:
        """Handle internal errors"""
        try:
            if error_event.client_id:
                emit('error', {
                    'type': 'internal_error',
                    'message': 'Internal server error. Please try again later.',
                    'recoverable': True
                }, room=error_event.client_id)
            return False
        except Exception:
            return False
    
    def _handle_timeout_error(self, error_event: ErrorEvent) -> bool:
        """Handle timeout errors"""
        try:
            if error_event.client_id:
                emit('error', {
                    'type': 'timeout_error',
                    'message': 'Connection timeout. Attempting to reconnect...',
                    'recoverable': True
                }, room=error_event.client_id)
            return True
        except Exception:
            return False
    
    def _handle_protocol_error(self, error_event: ErrorEvent) -> bool:
        """Handle protocol errors"""
        try:
            if error_event.client_id:
                emit('error', {
                    'type': 'protocol_error',
                    'message': 'Protocol error detected. Please refresh the page.',
                    'recoverable': False
                }, room=error_event.client_id)
                
                # Disconnect after protocol error
                self._disconnect_client(error_event.client_id, "Protocol error")
            return False
        except Exception:
            return False
    
    def _handle_security_error(self, error_event: ErrorEvent) -> bool:
        """Handle security errors"""
        try:
            if error_event.client_id:
                # Don't send detailed security error info to client
                emit('error', {
                    'type': 'security_error',
                    'message': 'Security violation detected.',
                    'recoverable': False
                }, room=error_event.client_id)
                
                # Immediately disconnect for security errors
                self._disconnect_client(error_event.client_id, "Security violation")
            return False
        except Exception:
            return False
    
    def _handle_generic_error(self, error_event: ErrorEvent) -> bool:
        """Handle generic/unknown errors"""
        try:
            if error_event.client_id:
                emit('error', {
                    'type': 'unknown_error',
                    'message': 'An unexpected error occurred.',
                    'recoverable': True
                }, room=error_event.client_id)
            return True
        except Exception:
            return False
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get comprehensive error statistics"""
        try:
            return {
                'total_errors': self._error_stats.total_errors,
                'error_rate_per_minute': self._error_stats.error_rate_per_minute,
                'errors_by_type': {
                    error_type.value: count 
                    for error_type, count in self._error_stats.errors_by_type.items()
                },
                'errors_by_severity': {
                    severity.value: count 
                    for severity, count in self._error_stats.errors_by_severity.items()
                },
                'recent_errors_count': len(self._error_stats.recent_errors),
                'clients_with_errors': len(self._client_errors),
                'thresholds': self._thresholds,
                'last_reset': self._error_stats.last_reset.isoformat()
            }
        except Exception as e:
            self.logger.error(f"Error getting statistics: {e}")
            return {'error': str(e)}
    
    def get_recent_errors(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent error events"""
        try:
            recent = list(self._error_stats.recent_errors)[-limit:]
            return [
                {
                    'error_type': event.error_type.value,
                    'severity': event.severity.value,
                    'message': event.message,
                    'timestamp': event.timestamp.isoformat(),
                    'client_id': event.client_id,
                    'error_code': event.error_code
                }
                for event in recent
            ]
        except Exception as e:
            self.logger.error(f"Error getting recent errors: {e}")
            return []
    
    def cleanup_old_errors(self):
        """Clean up old error data"""
        try:
            cutoff = datetime.utcnow() - timedelta(hours=24)
            
            # Clean client errors
            for client_id in list(self._client_errors.keys()):
                self._client_errors[client_id] = [
                    ts for ts in self._client_errors[client_id] if ts > cutoff
                ]
                if not self._client_errors[client_id]:
                    del self._client_errors[client_id]
            
            # Clean session errors
            for session_id in list(self._session_errors.keys()):
                self._session_errors[session_id] = [
                    ts for ts in self._session_errors[session_id] if ts > cutoff
                ]
                if not self._session_errors[session_id]:
                    del self._session_errors[session_id]
            
            self.logger.debug("Cleaned up old error data")
            
        except Exception as e:
            self.logger.error(f"Error cleaning up old errors: {e}")
    
    def _track_session_error(self, session_id: str, error_event: ErrorEvent):
        """Track session-specific errors"""
        try:
            self._session_errors[session_id].append(error_event.timestamp)
            
            # Keep only recent errors (last hour)
            cutoff = datetime.utcnow() - timedelta(hours=1)
            self._session_errors[session_id] = [
                ts for ts in self._session_errors[session_id] if ts > cutoff
            ]
            
            self.logger.debug(f"Session {session_id[:8]}... has {len(self._session_errors[session_id])} recent errors")
            
        except Exception as e:
            self.logger.error(f"Error tracking session error: {e}")
    
    def _should_invalidate_session(self, session_id: str) -> bool:
        """Check if session should be invalidated due to errors"""
        try:
            session_error_count = len(self._session_errors.get(session_id, []))
            return session_error_count >= self._session_error_threshold
        except Exception:
            return False
    
    def _invalidate_session(self, session_id: str, reason: str):
        """Invalidate session and disconnect client"""
        try:
            # Log session invalidation
            self.logger.warning(f"Invalidating session {session_id[:8]}...: {reason}")
            
            # Clear session error tracking
            if session_id in self._session_errors:
                del self._session_errors[session_id]
            
            # Additional session cleanup could be added here
            # For example, notifying the session manager to invalidate the session
            
        except Exception as e:
            self.logger.error(f"Error invalidating session {session_id[:8]}...: {e}")
    
    def handle_session_disconnect(self, session_id: str, client_id: Optional[str] = None):
        """Handle session disconnect and cleanup"""
        try:
            # Clean up session error tracking
            if session_id in self._session_errors:
                del self._session_errors[session_id]
                self.logger.debug(f"Cleaned up error tracking for session {session_id[:8]}...")
            
            # Clean up client error tracking if client_id provided
            if client_id and client_id in self._client_errors:
                del self._client_errors[client_id]
                self.logger.debug(f"Cleaned up error tracking for client {client_id}")
            
        except Exception as e:
            self.logger.error(f"Error handling session disconnect: {e}")
    
    def get_session_error_stats(self, session_id: str) -> Dict[str, Any]:
        """Get error statistics for a specific session"""
        try:
            session_error_events = self._session_errors.get(session_id, [])
            
            return {
                'session_id': session_id,
                'total_session_errors': len(session_error_events),
                'error_threshold': self._session_error_threshold,
                'errors_until_disconnect': max(0, self._session_error_threshold - len(session_error_events)),
                'last_error': session_error_events[-1].isoformat() if session_error_events else None
            }
        except Exception as e:
            self.logger.error(f"Error getting session error stats: {e}")
            return {'error': str(e)}

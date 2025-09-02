# Copyright (C) 2025 iolaire mcfadden.
# Consolidated WebSocket Security Management

import logging
import time
import json
import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Tuple, Set
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps

from flask import request, session as flask_session, current_app
from flask_socketio import disconnect, emit

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

class AbuseType(Enum):
    """Types of WebSocket abuse patterns"""
    CONNECTION_FLOOD = "connection_flood"
    MESSAGE_SPAM = "message_spam"
    RAPID_RECONNECTION = "rapid_reconnection"
    MALICIOUS_PAYLOAD = "malicious_payload"
    SUSPICIOUS_PATTERN = "suspicious_pattern"

@dataclass
class SecurityMetrics:
    """Security metrics tracking"""
    connections_blocked: int = 0
    messages_blocked: int = 0
    rate_limits_exceeded: int = 0
    csrf_failures: int = 0
    validation_failures: int = 0
    abuse_incidents: int = 0
    last_reset: datetime = field(default_factory=datetime.utcnow)

@dataclass
class AbusePattern:
    """Abuse pattern detection data"""
    abuse_type: AbuseType
    client_id: str
    first_occurrence: datetime
    last_occurrence: datetime
    occurrence_count: int = 1
    severity_score: float = 0.0
    is_blocked: bool = False

class ConsolidatedWebSocketSecurityManager:
    """Consolidated WebSocket security management with abuse detection"""
    
    def __init__(self, config=None):
        self.logger = logging.getLogger(__name__)
        self.config = config or {}
        
        # Security tracking
        self._connection_attempts = defaultdict(deque)
        self._message_counts = defaultdict(deque)
        self._blocked_clients = set()
        self._abuse_patterns = {}
        self._security_metrics = SecurityMetrics()
        
        # Rate limiting configuration
        self._rate_limits = {
            'connections_per_minute': self.config.get('connections_per_minute', 10),
            'messages_per_minute': self.config.get('messages_per_minute', 60),
            'max_message_size': self.config.get('max_message_size', 10000),
            'connection_timeout': self.config.get('connection_timeout', 300)
        }
        
        # Abuse detection thresholds
        self._abuse_thresholds = {
            'connection_flood_threshold': 20,
            'message_spam_threshold': 100,
            'rapid_reconnection_threshold': 5,
            'malicious_payload_threshold': 3,
            'block_duration': 3600  # 1 hour
        }
    
    def validate_connection(self, client_id: str, auth_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate WebSocket connection with comprehensive security checks"""
        try:
            # Check if client is blocked
            if self._is_client_blocked(client_id):
                self._log_security_event(
                    WebSocketSecurityEventType.WS_CONNECTION_BLOCKED,
                    f"Blocked client attempted connection: {client_id}"
                )
                return False, "Connection blocked due to security violations"
            
            # Rate limiting check
            if not self._check_connection_rate_limit(client_id):
                self._log_security_event(
                    WebSocketSecurityEventType.WS_RATE_LIMIT_EXCEEDED,
                    f"Connection rate limit exceeded for client: {client_id}"
                )
                return False, "Connection rate limit exceeded"
            
            # Authentication validation
            if not self._validate_authentication(auth_data):
                self._log_security_event(
                    WebSocketSecurityEventType.WS_UNAUTHORIZED_ACCESS,
                    f"Authentication failed for client: {client_id}"
                )
                return False, "Authentication required"
            
            # CSRF validation
            if not self._validate_csrf_token(auth_data):
                self._log_security_event(
                    WebSocketSecurityEventType.WS_CSRF_FAILURE,
                    f"CSRF validation failed for client: {client_id}"
                )
                return False, "CSRF validation failed"
            
            # Record successful connection
            self._record_connection_attempt(client_id)
            
            return True, "Connection validated"
            
        except Exception as e:
            self.logger.error(f"Error validating WebSocket connection: {e}")
            return False, "Internal security error"
    
    def validate_message(self, client_id: str, message_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate WebSocket message with security checks"""
        try:
            # Check if client is blocked
            if self._is_client_blocked(client_id):
                return False, "Client is blocked"
            
            # Message rate limiting
            if not self._check_message_rate_limit(client_id):
                self._log_security_event(
                    WebSocketSecurityEventType.WS_RATE_LIMIT_EXCEEDED,
                    f"Message rate limit exceeded for client: {client_id}"
                )
                return False, "Message rate limit exceeded"
            
            # Message size validation
            message_size = len(json.dumps(message_data))
            if message_size > self._rate_limits['max_message_size']:
                self._log_security_event(
                    WebSocketSecurityEventType.WS_MESSAGE_BLOCKED,
                    f"Message too large from client: {client_id}, size: {message_size}"
                )
                return False, "Message too large"
            
            # Input validation
            if not self._validate_message_content(message_data):
                self._log_security_event(
                    WebSocketSecurityEventType.WS_INPUT_VALIDATION_FAILURE,
                    f"Message validation failed for client: {client_id}"
                )
                return False, "Invalid message content"
            
            # Malicious payload detection
            if self._detect_malicious_payload(message_data):
                self._log_security_event(
                    WebSocketSecurityEventType.WS_MALICIOUS_PAYLOAD,
                    f"Malicious payload detected from client: {client_id}"
                )
                self._record_abuse_pattern(client_id, AbuseType.MALICIOUS_PAYLOAD)
                return False, "Malicious payload detected"
            
            # Record successful message
            self._record_message(client_id)
            
            return True, "Message validated"
            
        except Exception as e:
            self.logger.error(f"Error validating WebSocket message: {e}")
            return False, "Internal security error"
    
    def _is_client_blocked(self, client_id: str) -> bool:
        """Check if client is currently blocked"""
        return client_id in self._blocked_clients
    
    def _check_connection_rate_limit(self, client_id: str) -> bool:
        """Check connection rate limiting"""
        now = time.time()
        window_start = now - 60  # 1 minute window
        
        # Clean old attempts
        attempts = self._connection_attempts[client_id]
        while attempts and attempts[0] < window_start:
            attempts.popleft()
        
        # Check if under limit
        return len(attempts) < self._rate_limits['connections_per_minute']
    
    def _check_message_rate_limit(self, client_id: str) -> bool:
        """Check message rate limiting"""
        now = time.time()
        window_start = now - 60  # 1 minute window
        
        # Clean old messages
        messages = self._message_counts[client_id]
        while messages and messages[0] < window_start:
            messages.popleft()
        
        # Check if under limit
        return len(messages) < self._rate_limits['messages_per_minute']
    
    def _validate_authentication(self, auth_data: Dict[str, Any]) -> bool:
        """Validate WebSocket authentication"""
        # Check for required authentication data
        if not auth_data.get('user_id') and not auth_data.get('session_token'):
            return False
        
        # Additional authentication checks can be added here
        return True
    
    def _validate_csrf_token(self, auth_data: Dict[str, Any]) -> bool:
        """Validate CSRF token for WebSocket connection"""
        csrf_token = auth_data.get('csrf_token')
        if not csrf_token:
            return False
        
        # Basic CSRF validation - can be enhanced with actual CSRF implementation
        return len(csrf_token) > 10  # Placeholder validation
    
    def _validate_message_content(self, message_data: Dict[str, Any]) -> bool:
        """Validate message content for security issues"""
        try:
            # Check for required fields
            if 'type' not in message_data:
                return False
            
            # Validate message type
            allowed_types = ['status', 'progress', 'notification', 'heartbeat']
            if message_data['type'] not in allowed_types:
                return False
            
            # Check for suspicious content
            message_str = json.dumps(message_data).lower()
            suspicious_patterns = ['<script', 'javascript:', 'eval(', 'document.cookie']
            
            for pattern in suspicious_patterns:
                if pattern in message_str:
                    return False
            
            return True
            
        except Exception:
            return False
    
    def _detect_malicious_payload(self, message_data: Dict[str, Any]) -> bool:
        """Detect potentially malicious payloads"""
        try:
            message_str = json.dumps(message_data)
            
            # Check for common attack patterns
            malicious_patterns = [
                r'<script[^>]*>.*?</script>',
                r'javascript:',
                r'eval\s*\(',
                r'document\.cookie',
                r'window\.location',
                r'alert\s*\(',
                r'confirm\s*\(',
                r'prompt\s*\('
            ]
            
            import re
            for pattern in malicious_patterns:
                if re.search(pattern, message_str, re.IGNORECASE):
                    return True
            
            return False
            
        except Exception:
            return True  # Err on the side of caution
    
    def _record_connection_attempt(self, client_id: str):
        """Record connection attempt for rate limiting"""
        now = time.time()
        self._connection_attempts[client_id].append(now)
        
        # Detect connection flooding
        if len(self._connection_attempts[client_id]) >= self._abuse_thresholds['connection_flood_threshold']:
            self._record_abuse_pattern(client_id, AbuseType.CONNECTION_FLOOD)
    
    def _record_message(self, client_id: str):
        """Record message for rate limiting"""
        now = time.time()
        self._message_counts[client_id].append(now)
        
        # Detect message spamming
        if len(self._message_counts[client_id]) >= self._abuse_thresholds['message_spam_threshold']:
            self._record_abuse_pattern(client_id, AbuseType.MESSAGE_SPAM)
    
    def _record_abuse_pattern(self, client_id: str, abuse_type: AbuseType):
        """Record abuse pattern and take action if necessary"""
        now = datetime.utcnow()
        pattern_key = f"{client_id}:{abuse_type.value}"
        
        if pattern_key in self._abuse_patterns:
            pattern = self._abuse_patterns[pattern_key]
            pattern.last_occurrence = now
            pattern.occurrence_count += 1
            pattern.severity_score += 1.0
        else:
            pattern = AbusePattern(
                abuse_type=abuse_type,
                client_id=client_id,
                first_occurrence=now,
                last_occurrence=now,
                severity_score=1.0
            )
            self._abuse_patterns[pattern_key] = pattern
        
        # Check if client should be blocked
        if pattern.severity_score >= 5.0 and not pattern.is_blocked:
            self._block_client(client_id, abuse_type)
            pattern.is_blocked = True
    
    def _block_client(self, client_id: str, abuse_type: AbuseType):
        """Block client due to abuse"""
        self._blocked_clients.add(client_id)
        self._security_metrics.abuse_incidents += 1
        
        self._log_security_event(
            WebSocketSecurityEventType.WS_ABUSE_DETECTED,
            f"Client blocked due to {abuse_type.value}: {client_id}"
        )
        
        # Schedule unblock (in a real implementation, this would use a task queue)
        self.logger.info(f"Client {client_id} blocked for {self._abuse_thresholds['block_duration']} seconds")
    
    def _log_security_event(self, event_type: WebSocketSecurityEventType, message: str):
        """Log security event"""
        self.logger.warning(f"WebSocket Security Event [{event_type.value}]: {message}")
        
        # Update metrics
        if event_type == WebSocketSecurityEventType.WS_CONNECTION_BLOCKED:
            self._security_metrics.connections_blocked += 1
        elif event_type == WebSocketSecurityEventType.WS_MESSAGE_BLOCKED:
            self._security_metrics.messages_blocked += 1
        elif event_type == WebSocketSecurityEventType.WS_RATE_LIMIT_EXCEEDED:
            self._security_metrics.rate_limits_exceeded += 1
        elif event_type == WebSocketSecurityEventType.WS_CSRF_FAILURE:
            self._security_metrics.csrf_failures += 1
        elif event_type == WebSocketSecurityEventType.WS_INPUT_VALIDATION_FAILURE:
            self._security_metrics.validation_failures += 1
    
    def get_security_metrics(self) -> Dict[str, Any]:
        """Get current security metrics"""
        return {
            'connections_blocked': self._security_metrics.connections_blocked,
            'messages_blocked': self._security_metrics.messages_blocked,
            'rate_limits_exceeded': self._security_metrics.rate_limits_exceeded,
            'csrf_failures': self._security_metrics.csrf_failures,
            'validation_failures': self._security_metrics.validation_failures,
            'abuse_incidents': self._security_metrics.abuse_incidents,
            'active_blocks': len(self._blocked_clients),
            'abuse_patterns': len(self._abuse_patterns),
            'last_reset': self._security_metrics.last_reset.isoformat()
        }
    
    def cleanup_expired_data(self):
        """Clean up expired security data"""
        now = time.time()
        cutoff = now - 3600  # 1 hour
        
        # Clean connection attempts
        for client_id in list(self._connection_attempts.keys()):
            attempts = self._connection_attempts[client_id]
            while attempts and attempts[0] < cutoff:
                attempts.popleft()
            if not attempts:
                del self._connection_attempts[client_id]
        
        # Clean message counts
        for client_id in list(self._message_counts.keys()):
            messages = self._message_counts[client_id]
            while messages and messages[0] < cutoff:
                messages.popleft()
            if not messages:
                del self._message_counts[client_id]

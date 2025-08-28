# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
WebSocket Abuse Detection System

This module provides advanced abuse detection and monitoring for WebSocket connections,
including pattern recognition, behavioral analysis, and automated response mechanisms.
"""

import logging
import time
import json
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Set, Tuple
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum

from security.monitoring.security_event_logger import SecurityEventLogger, SecurityEventType, SecurityEventSeverity
from security.core.security_utils import sanitize_for_log

logger = logging.getLogger(__name__)


class AbuseType(Enum):
    """Types of WebSocket abuse patterns"""
    CONNECTION_FLOOD = "connection_flood"
    MESSAGE_FLOOD = "message_flood"
    RAPID_RECONNECTION = "rapid_reconnection"
    SUSPICIOUS_PAYLOAD = "suspicious_payload"
    PATTERN_ABUSE = "pattern_abuse"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    AUTHENTICATION_ABUSE = "authentication_abuse"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DATA_EXFILTRATION = "data_exfiltration"
    MALICIOUS_INJECTION = "malicious_injection"


class AbuseAction(Enum):
    """Actions to take when abuse is detected"""
    LOG_ONLY = "log_only"
    RATE_LIMIT = "rate_limit"
    TEMPORARY_BAN = "temporary_ban"
    DISCONNECT = "disconnect"
    PERMANENT_BAN = "permanent_ban"
    ALERT_ADMIN = "alert_admin"


@dataclass
class AbusePattern:
    """Definition of an abuse pattern"""
    name: str
    abuse_type: AbuseType
    threshold: int
    time_window: int  # seconds
    action: AbuseAction
    severity: SecurityEventSeverity
    description: str
    enabled: bool = True


@dataclass
class AbuseEvent:
    """Record of an abuse event"""
    timestamp: datetime
    abuse_type: AbuseType
    session_id: str
    user_id: Optional[int]
    ip_address: str
    details: Dict[str, Any]
    severity: SecurityEventSeverity
    action_taken: AbuseAction


@dataclass
class ConnectionMetrics:
    """Metrics for a WebSocket connection"""
    session_id: str
    user_id: Optional[int]
    ip_address: str
    user_agent: str
    connected_at: datetime
    last_activity: datetime
    
    # Message metrics
    total_messages: int = 0
    messages_per_minute: List[int] = field(default_factory=list)
    
    # Connection metrics
    connection_attempts: int = 0
    reconnection_count: int = 0
    
    # Security metrics
    failed_auth_attempts: int = 0
    csrf_failures: int = 0
    validation_failures: int = 0
    
    # Behavioral metrics
    unique_event_types: Set[str] = field(default_factory=set)
    payload_sizes: List[int] = field(default_factory=list)
    suspicious_patterns: List[str] = field(default_factory=list)


class WebSocketAbuseDetector:
    """
    Advanced abuse detection system for WebSocket connections
    
    Monitors connection patterns, message behavior, and security events
    to detect and respond to various types of abuse.
    """
    
    def __init__(self, security_logger: SecurityEventLogger):
        """
        Initialize abuse detector
        
        Args:
            security_logger: Security event logger instance
        """
        self.security_logger = security_logger
        
        # Connection tracking
        self.connection_metrics: Dict[str, ConnectionMetrics] = {}  # session_id -> metrics
        self.ip_metrics: Dict[str, Dict[str, Any]] = defaultdict(dict)  # ip -> metrics
        self.user_metrics: Dict[int, Dict[str, Any]] = defaultdict(dict)  # user_id -> metrics
        
        # Abuse pattern definitions
        self.abuse_patterns = self._initialize_abuse_patterns()
        
        # Abuse event history
        self.abuse_events: List[AbuseEvent] = []
        self.blocked_ips: Dict[str, datetime] = {}  # ip -> block_until
        self.blocked_users: Dict[int, datetime] = {}  # user_id -> block_until
        
        # Pattern detection state
        self.pattern_state: Dict[str, Any] = defaultdict(dict)
        
        logger.info("WebSocket Abuse Detector initialized")
    
    def _initialize_abuse_patterns(self) -> Dict[str, AbusePattern]:
        """Initialize abuse pattern definitions"""
        patterns = {
            'connection_flood': AbusePattern(
                name="Connection Flood",
                abuse_type=AbuseType.CONNECTION_FLOOD,
                threshold=20,  # 20 connections
                time_window=60,  # in 1 minute
                action=AbuseAction.TEMPORARY_BAN,
                severity=SecurityEventSeverity.HIGH,
                description="Too many connection attempts from single IP"
            ),
            'message_flood': AbusePattern(
                name="Message Flood",
                abuse_type=AbuseType.MESSAGE_FLOOD,
                threshold=100,  # 100 messages
                time_window=60,  # in 1 minute
                action=AbuseAction.RATE_LIMIT,
                severity=SecurityEventSeverity.MEDIUM,
                description="Excessive message rate from single connection"
            ),
            'rapid_reconnection': AbusePattern(
                name="Rapid Reconnection",
                abuse_type=AbuseType.RAPID_RECONNECTION,
                threshold=10,  # 10 reconnections
                time_window=300,  # in 5 minutes
                action=AbuseAction.TEMPORARY_BAN,
                severity=SecurityEventSeverity.MEDIUM,
                description="Rapid reconnection attempts"
            ),
            'authentication_abuse': AbusePattern(
                name="Authentication Abuse",
                abuse_type=AbuseType.AUTHENTICATION_ABUSE,
                threshold=5,  # 5 failed attempts
                time_window=300,  # in 5 minutes
                action=AbuseAction.DISCONNECT,
                severity=SecurityEventSeverity.HIGH,
                description="Multiple authentication failures"
            ),
            'validation_abuse': AbusePattern(
                name="Validation Abuse",
                abuse_type=AbuseType.MALICIOUS_INJECTION,
                threshold=10,  # 10 validation failures
                time_window=600,  # in 10 minutes
                action=AbuseAction.DISCONNECT,
                severity=SecurityEventSeverity.HIGH,
                description="Multiple input validation failures"
            ),
            'large_payload_abuse': AbusePattern(
                name="Large Payload Abuse",
                abuse_type=AbuseType.RESOURCE_EXHAUSTION,
                threshold=5,  # 5 large payloads
                time_window=300,  # in 5 minutes
                action=AbuseAction.RATE_LIMIT,
                severity=SecurityEventSeverity.MEDIUM,
                description="Repeated large payload submissions"
            )
        }
        
        return patterns
    
    def track_connection(self, session_id: str, user_id: Optional[int], 
                        ip_address: str, user_agent: str) -> None:
        """
        Track a new WebSocket connection
        
        Args:
            session_id: Session ID
            user_id: User ID (if authenticated)
            ip_address: Client IP address
            user_agent: Client user agent
        """
        try:
            current_time = datetime.now(timezone.utc)
            
            # Create connection metrics
            metrics = ConnectionMetrics(
                session_id=session_id,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                connected_at=current_time,
                last_activity=current_time,
                connection_attempts=1
            )
            
            # Check if this is a reconnection
            if session_id in self.connection_metrics:
                old_metrics = self.connection_metrics[session_id]
                metrics.reconnection_count = old_metrics.reconnection_count + 1
                metrics.connection_attempts = old_metrics.connection_attempts + 1
            
            self.connection_metrics[session_id] = metrics
            
            # Update IP metrics
            ip_data = self.ip_metrics[ip_address]
            ip_data['last_connection'] = current_time
            ip_data['total_connections'] = ip_data.get('total_connections', 0) + 1
            ip_data['active_sessions'] = ip_data.get('active_sessions', set())
            ip_data['active_sessions'].add(session_id)
            
            # Update user metrics if authenticated
            if user_id:
                user_data = self.user_metrics[user_id]
                user_data['last_connection'] = current_time
                user_data['total_connections'] = user_data.get('total_connections', 0) + 1
                user_data['active_sessions'] = user_data.get('active_sessions', set())
                user_data['active_sessions'].add(session_id)
            
            # Check for abuse patterns
            self._check_connection_abuse(metrics)
            
        except Exception as e:
            logger.error(f"Error tracking WebSocket connection: {e}")
    
    def track_message(self, session_id: str, event_type: str, payload_size: int,
                     validation_failed: bool = False, csrf_failed: bool = False) -> None:
        """
        Track a WebSocket message
        
        Args:
            session_id: Session ID
            event_type: Type of WebSocket event
            payload_size: Size of message payload
            validation_failed: Whether input validation failed
            csrf_failed: Whether CSRF validation failed
        """
        try:
            metrics = self.connection_metrics.get(session_id)
            if not metrics:
                return
            
            current_time = datetime.now(timezone.utc)
            metrics.last_activity = current_time
            metrics.total_messages += 1
            
            # Track event types
            metrics.unique_event_types.add(event_type)
            
            # Track payload sizes
            metrics.payload_sizes.append(payload_size)
            if len(metrics.payload_sizes) > 100:  # Keep last 100
                metrics.payload_sizes = metrics.payload_sizes[-100:]
            
            # Track security failures
            if validation_failed:
                metrics.validation_failures += 1
            if csrf_failed:
                metrics.csrf_failures += 1
            
            # Update messages per minute tracking
            current_minute = int(current_time.timestamp() // 60)
            if not metrics.messages_per_minute or metrics.messages_per_minute[-1] != current_minute:
                metrics.messages_per_minute.append(current_minute)
                if len(metrics.messages_per_minute) > 60:  # Keep last hour
                    metrics.messages_per_minute = metrics.messages_per_minute[-60:]
            
            # Check for abuse patterns
            self._check_message_abuse(metrics, event_type, payload_size)
            
        except Exception as e:
            logger.error(f"Error tracking WebSocket message: {e}")
    
    def track_authentication_failure(self, session_id: str) -> None:
        """
        Track authentication failure
        
        Args:
            session_id: Session ID
        """
        try:
            metrics = self.connection_metrics.get(session_id)
            if metrics:
                metrics.failed_auth_attempts += 1
                self._check_authentication_abuse(metrics)
                
        except Exception as e:
            logger.error(f"Error tracking authentication failure: {e}")
    
    def disconnect_connection(self, session_id: str) -> None:
        """
        Handle connection disconnection
        
        Args:
            session_id: Session ID being disconnected
        """
        try:
            metrics = self.connection_metrics.get(session_id)
            if not metrics:
                return
            
            # Update IP metrics
            ip_data = self.ip_metrics.get(metrics.ip_address)
            if ip_data and 'active_sessions' in ip_data:
                ip_data['active_sessions'].discard(session_id)
            
            # Update user metrics
            if metrics.user_id:
                user_data = self.user_metrics.get(metrics.user_id)
                if user_data and 'active_sessions' in user_data:
                    user_data['active_sessions'].discard(session_id)
            
            # Keep metrics for analysis but mark as disconnected
            metrics.last_activity = datetime.now(timezone.utc)
            
        except Exception as e:
            logger.error(f"Error handling connection disconnection: {e}")
    
    def is_ip_blocked(self, ip_address: str) -> bool:
        """
        Check if IP address is currently blocked
        
        Args:
            ip_address: IP address to check
            
        Returns:
            True if IP is blocked, False otherwise
        """
        try:
            if ip_address in self.blocked_ips:
                block_until = self.blocked_ips[ip_address]
                if datetime.now(timezone.utc) < block_until:
                    return True
                else:
                    # Block expired, remove it
                    del self.blocked_ips[ip_address]
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking IP block status: {e}")
            return False
    
    def is_user_blocked(self, user_id: int) -> bool:
        """
        Check if user is currently blocked
        
        Args:
            user_id: User ID to check
            
        Returns:
            True if user is blocked, False otherwise
        """
        try:
            if user_id in self.blocked_users:
                block_until = self.blocked_users[user_id]
                if datetime.now(timezone.utc) < block_until:
                    return True
                else:
                    # Block expired, remove it
                    del self.blocked_users[user_id]
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking user block status: {e}")
            return False
    
    def get_abuse_stats(self) -> Dict[str, Any]:
        """
        Get abuse detection statistics
        
        Returns:
            Dictionary containing abuse statistics
        """
        try:
            current_time = datetime.now(timezone.utc)
            
            # Count recent abuse events
            recent_events = [
                event for event in self.abuse_events
                if (current_time - event.timestamp).total_seconds() < 3600  # Last hour
            ]
            
            # Count events by type
            event_counts = defaultdict(int)
            for event in recent_events:
                event_counts[event.abuse_type.value] += 1
            
            # Count active blocks
            active_ip_blocks = sum(
                1 for block_until in self.blocked_ips.values()
                if current_time < block_until
            )
            
            active_user_blocks = sum(
                1 for block_until in self.blocked_users.values()
                if current_time < block_until
            )
            
            # Connection statistics
            active_connections = len(self.connection_metrics)
            total_messages = sum(metrics.total_messages for metrics in self.connection_metrics.values())
            
            return {
                'abuse_events': {
                    'total_recent': len(recent_events),
                    'by_type': dict(event_counts),
                    'total_all_time': len(self.abuse_events)
                },
                'blocks': {
                    'active_ip_blocks': active_ip_blocks,
                    'active_user_blocks': active_user_blocks,
                    'total_ip_blocks': len(self.blocked_ips),
                    'total_user_blocks': len(self.blocked_users)
                },
                'connections': {
                    'active_connections': active_connections,
                    'total_messages': total_messages,
                    'unique_ips': len(self.ip_metrics),
                    'unique_users': len(self.user_metrics)
                },
                'patterns': {
                    'enabled_patterns': len([p for p in self.abuse_patterns.values() if p.enabled]),
                    'total_patterns': len(self.abuse_patterns)
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting abuse stats: {e}")
            return {'error': str(e)}
    
    def _check_connection_abuse(self, metrics: ConnectionMetrics) -> None:
        """Check for connection-related abuse patterns"""
        try:
            current_time = datetime.now(timezone.utc)
            
            # Check connection flood from IP
            pattern = self.abuse_patterns.get('connection_flood')
            if pattern and pattern.enabled:
                ip_data = self.ip_metrics[metrics.ip_address]
                recent_connections = ip_data.get('total_connections', 0)
                
                if recent_connections >= pattern.threshold:
                    self._trigger_abuse_action(
                        pattern, metrics, 
                        {'recent_connections': recent_connections}
                    )
            
            # Check rapid reconnection
            pattern = self.abuse_patterns.get('rapid_reconnection')
            if pattern and pattern.enabled and metrics.reconnection_count >= pattern.threshold:
                time_since_first = (current_time - metrics.connected_at).total_seconds()
                if time_since_first <= pattern.time_window:
                    self._trigger_abuse_action(
                        pattern, metrics,
                        {'reconnection_count': metrics.reconnection_count, 'time_window': time_since_first}
                    )
                    
        except Exception as e:
            logger.error(f"Error checking connection abuse: {e}")
    
    def _check_message_abuse(self, metrics: ConnectionMetrics, event_type: str, payload_size: int) -> None:
        """Check for message-related abuse patterns"""
        try:
            current_time = datetime.now(timezone.utc)
            
            # Check message flood
            pattern = self.abuse_patterns.get('message_flood')
            if pattern and pattern.enabled:
                # Count messages in the last minute
                cutoff_time = current_time - timedelta(seconds=pattern.time_window)
                recent_message_count = sum(
                    1 for minute in metrics.messages_per_minute
                    if datetime.fromtimestamp(minute * 60, timezone.utc) > cutoff_time
                )
                
                if recent_message_count >= pattern.threshold:
                    self._trigger_abuse_action(
                        pattern, metrics,
                        {'recent_messages': recent_message_count, 'event_type': event_type}
                    )
            
            # Check large payload abuse
            pattern = self.abuse_patterns.get('large_payload_abuse')
            if pattern and pattern.enabled and payload_size > 5000:  # 5KB threshold
                large_payloads = sum(1 for size in metrics.payload_sizes[-10:] if size > 5000)
                if large_payloads >= pattern.threshold:
                    self._trigger_abuse_action(
                        pattern, metrics,
                        {'large_payloads': large_payloads, 'payload_size': payload_size}
                    )
            
            # Check validation abuse
            pattern = self.abuse_patterns.get('validation_abuse')
            if pattern and pattern.enabled and metrics.validation_failures >= pattern.threshold:
                self._trigger_abuse_action(
                    pattern, metrics,
                    {'validation_failures': metrics.validation_failures}
                )
                
        except Exception as e:
            logger.error(f"Error checking message abuse: {e}")
    
    def _check_authentication_abuse(self, metrics: ConnectionMetrics) -> None:
        """Check for authentication-related abuse patterns"""
        try:
            pattern = self.abuse_patterns.get('authentication_abuse')
            if pattern and pattern.enabled and metrics.failed_auth_attempts >= pattern.threshold:
                self._trigger_abuse_action(
                    pattern, metrics,
                    {'failed_auth_attempts': metrics.failed_auth_attempts}
                )
                
        except Exception as e:
            logger.error(f"Error checking authentication abuse: {e}")
    
    def _trigger_abuse_action(self, pattern: AbusePattern, metrics: ConnectionMetrics, 
                            details: Dict[str, Any]) -> None:
        """
        Trigger action for detected abuse pattern
        
        Args:
            pattern: Abuse pattern that was triggered
            metrics: Connection metrics
            details: Additional details about the abuse
        """
        try:
            current_time = datetime.now(timezone.utc)
            
            # Create abuse event
            abuse_event = AbuseEvent(
                timestamp=current_time,
                abuse_type=pattern.abuse_type,
                session_id=metrics.session_id,
                user_id=metrics.user_id,
                ip_address=metrics.ip_address,
                details=details,
                severity=pattern.severity,
                action_taken=pattern.action
            )
            
            self.abuse_events.append(abuse_event)
            
            # Keep only recent events (last 24 hours)
            cutoff_time = current_time - timedelta(hours=24)
            self.abuse_events = [
                event for event in self.abuse_events
                if event.timestamp > cutoff_time
            ]
            
            # Log security event
            self.security_logger.log_security_event(
                event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
                severity=pattern.severity,
                user_id=metrics.user_id,
                details={
                    'abuse_type': pattern.abuse_type.value,
                    'pattern_name': pattern.name,
                    'session_id': metrics.session_id[:8],
                    'ip_address': metrics.ip_address,
                    'action_taken': pattern.action.value,
                    **details
                },
                ip_address=metrics.ip_address
            )
            
            # Execute action
            self._execute_abuse_action(pattern.action, metrics, abuse_event)
            
            logger.warning(f"WebSocket abuse detected: {pattern.name} - {pattern.action.value} - "
                          f"Session: {metrics.session_id[:8]}, IP: {metrics.ip_address}")
            
        except Exception as e:
            logger.error(f"Error triggering abuse action: {e}")
    
    def _execute_abuse_action(self, action: AbuseAction, metrics: ConnectionMetrics, 
                            abuse_event: AbuseEvent) -> None:
        """
        Execute the specified abuse action
        
        Args:
            action: Action to execute
            metrics: Connection metrics
            abuse_event: Abuse event details
        """
        try:
            current_time = datetime.now(timezone.utc)
            
            if action == AbuseAction.LOG_ONLY:
                # Already logged above
                pass
            
            elif action == AbuseAction.RATE_LIMIT:
                # Implement rate limiting (could integrate with existing rate limiter)
                logger.info(f"Rate limiting applied to session {metrics.session_id[:8]}")
            
            elif action == AbuseAction.TEMPORARY_BAN:
                # Block IP for 1 hour
                block_until = current_time + timedelta(hours=1)
                self.blocked_ips[metrics.ip_address] = block_until
                logger.info(f"Temporary ban applied to IP {metrics.ip_address} until {block_until}")
            
            elif action == AbuseAction.DISCONNECT:
                # Mark for disconnection (actual disconnection handled by security manager)
                logger.info(f"Disconnect requested for session {metrics.session_id[:8]}")
            
            elif action == AbuseAction.PERMANENT_BAN:
                # Block IP permanently (or for a very long time)
                block_until = current_time + timedelta(days=365)
                self.blocked_ips[metrics.ip_address] = block_until
                if metrics.user_id:
                    self.blocked_users[metrics.user_id] = block_until
                logger.warning(f"Permanent ban applied to IP {metrics.ip_address} and user {metrics.user_id}")
            
            elif action == AbuseAction.ALERT_ADMIN:
                # Send alert to administrators
                logger.critical(f"ADMIN ALERT: WebSocket abuse detected - {abuse_event.abuse_type.value}")
                # Could integrate with admin notification system
            
        except Exception as e:
            logger.error(f"Error executing abuse action {action.value}: {e}")
    
    def cleanup_old_data(self) -> None:
        """Clean up old tracking data"""
        try:
            current_time = datetime.now(timezone.utc)
            cutoff_time = current_time - timedelta(hours=24)
            
            # Clean up old connection metrics
            expired_sessions = [
                session_id for session_id, metrics in self.connection_metrics.items()
                if metrics.last_activity < cutoff_time
            ]
            
            for session_id in expired_sessions:
                del self.connection_metrics[session_id]
            
            # Clean up IP metrics
            for ip_address in list(self.ip_metrics.keys()):
                ip_data = self.ip_metrics[ip_address]
                if 'last_connection' in ip_data and ip_data['last_connection'] < cutoff_time:
                    del self.ip_metrics[ip_address]
            
            # Clean up user metrics
            for user_id in list(self.user_metrics.keys()):
                user_data = self.user_metrics[user_id]
                if 'last_connection' in user_data and user_data['last_connection'] < cutoff_time:
                    del self.user_metrics[user_id]
            
            # Clean up expired blocks
            expired_ip_blocks = [
                ip for ip, block_until in self.blocked_ips.items()
                if current_time >= block_until
            ]
            for ip in expired_ip_blocks:
                del self.blocked_ips[ip]
            
            expired_user_blocks = [
                user_id for user_id, block_until in self.blocked_users.items()
                if current_time >= block_until
            ]
            for user_id in expired_user_blocks:
                del self.blocked_users[user_id]
            
            if expired_sessions or expired_ip_blocks or expired_user_blocks:
                logger.info(f"Cleaned up abuse detector data: {len(expired_sessions)} sessions, "
                           f"{len(expired_ip_blocks)} IP blocks, {len(expired_user_blocks)} user blocks")
                
        except Exception as e:
            logger.error(f"Error cleaning up abuse detector data: {e}")
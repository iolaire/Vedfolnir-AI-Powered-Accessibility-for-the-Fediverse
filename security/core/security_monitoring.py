# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Security monitoring and alerting system

Implements comprehensive security event monitoring, logging, and alerting.
"""

import logging
import json
import hashlib
from datetime import datetime, timedelta, timezone
from collections import defaultdict, deque
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import threading
import time

logger = logging.getLogger(__name__)

class SecurityEventType(Enum):
    """Types of security events"""
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    BRUTE_FORCE_ATTEMPT = "brute_force_attempt"
    SUSPICIOUS_REQUEST = "suspicious_request"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SQL_INJECTION_ATTEMPT = "sql_injection_attempt"
    XSS_ATTEMPT = "xss_attempt"
    PATH_TRAVERSAL_ATTEMPT = "path_traversal_attempt"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DATA_BREACH_ATTEMPT = "data_breach_attempt"
    MALICIOUS_FILE_UPLOAD = "malicious_file_upload"
    SESSION_HIJACKING = "session_hijacking"
    CSRF_ATTACK = "csrf_attack"
    SECURITY_MISCONFIGURATION = "security_misconfiguration"

class SecurityEventSeverity(Enum):
    """Severity levels for security events"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class SecurityEvent:
    """Security event data structure"""
    event_type: SecurityEventType
    severity: SecurityEventSeverity
    timestamp: datetime
    source_ip: str
    user_id: Optional[str]
    endpoint: str
    user_agent: str
    details: Dict[str, Any]
    event_id: str

class SecurityMonitor:
    """Comprehensive security monitoring system"""
    
    def __init__(self, config=None):
        self.config = config or {}
        self.events = deque(maxlen=10000)  # Keep last 10k events
        self.ip_events = defaultdict(list)  # Events by IP
        self.user_events = defaultdict(list)  # Events by user
        self.alert_thresholds = self._get_alert_thresholds()
        self.lock = threading.Lock()
        
        # Start background monitoring thread
        self.monitoring_thread = threading.Thread(target=self._background_monitor, daemon=True)
        self.monitoring_thread.start()
    
    def _get_alert_thresholds(self):
        """Get alert thresholds from configuration"""
        return {
            'failed_logins_per_ip': 5,
            'failed_logins_per_user': 3,
            'suspicious_requests_per_ip': 10,
            'rate_limit_violations_per_ip': 3,
            'time_window_minutes': 15,
        }
    
    def log_security_event(self, event_type: SecurityEventType, severity: SecurityEventSeverity,
                          source_ip: str, endpoint: str, user_agent: str = "",
                          user_id: str = None, details: Dict[str, Any] = None):
        """Log a security event"""
        event = SecurityEvent(
            event_type=event_type,
            severity=severity,
            timestamp=datetime.now(timezone.utc),
            source_ip=source_ip,
            user_id=user_id,
            endpoint=endpoint,
            user_agent=user_agent,
            details=details or {},
            event_id=self._generate_event_id()
        )
        
        with self.lock:
            self.events.append(event)
            self.ip_events[source_ip].append(event)
            if user_id:
                self.user_events[user_id].append(event)
        
        # Log to standard logging
        self._log_event(event)
        
        # Check for alert conditions
        self._check_alert_conditions(event)
    
    def _generate_event_id(self):
        """Generate unique event ID"""
        import uuid
        return str(uuid.uuid4())
    
    def _log_event(self, event: SecurityEvent):
        """Log event to standard logging system"""
        log_data = {
            'event_id': event.event_id,
            'event_type': event.event_type.value,
            'severity': event.severity.value,
            'timestamp': event.timestamp.isoformat(),
            'source_ip': event.source_ip,
            'user_id': event.user_id,
            'endpoint': event.endpoint,
            'user_agent': event.user_agent[:200],  # Truncate long user agents
            'details': event.details
        }
        
        log_message = f"SECURITY_EVENT: {json.dumps(log_data)}"
        
        if event.severity == SecurityEventSeverity.CRITICAL:
            logger.critical(log_message)
        elif event.severity == SecurityEventSeverity.HIGH:
            logger.error(log_message)
        elif event.severity == SecurityEventSeverity.MEDIUM:
            logger.warning(log_message)
        else:
            logger.info(log_message)
    
    def _check_alert_conditions(self, event: SecurityEvent):
        """Check if event triggers any alert conditions"""
        current_time = datetime.now(timezone.utc)
        time_window = timedelta(minutes=self.alert_thresholds['time_window_minutes'])
        
        # Check for brute force attacks
        if event.event_type == SecurityEventType.LOGIN_FAILURE:
            self._check_brute_force_attack(event, current_time, time_window)
        
        # Check for suspicious activity patterns
        self._check_suspicious_patterns(event, current_time, time_window)
        
        # Check for rate limiting violations
        if event.event_type == SecurityEventType.RATE_LIMIT_EXCEEDED:
            self._check_rate_limit_violations(event, current_time, time_window)
    
    def _check_brute_force_attack(self, event: SecurityEvent, current_time: datetime, time_window: timedelta):
        """Check for brute force attack patterns"""
        # Check by IP
        recent_failures_by_ip = [
            e for e in self.ip_events[event.source_ip]
            if e.event_type == SecurityEventType.LOGIN_FAILURE
            and current_time - e.timestamp <= time_window
        ]
        
        if len(recent_failures_by_ip) >= self.alert_thresholds['failed_logins_per_ip']:
            self._trigger_alert(
                SecurityEventType.BRUTE_FORCE_ATTEMPT,
                SecurityEventSeverity.HIGH,
                f"Brute force attack detected from IP {event.source_ip}",
                {
                    'source_ip': event.source_ip,
                    'failed_attempts': len(recent_failures_by_ip),
                    'time_window': self.alert_thresholds['time_window_minutes']
                }
            )
        
        # Check by user
        if event.user_id:
            recent_failures_by_user = [
                e for e in self.user_events[event.user_id]
                if e.event_type == SecurityEventType.LOGIN_FAILURE
                and current_time - e.timestamp <= time_window
            ]
            
            if len(recent_failures_by_user) >= self.alert_thresholds['failed_logins_per_user']:
                self._trigger_alert(
                    SecurityEventType.BRUTE_FORCE_ATTEMPT,
                    SecurityEventSeverity.MEDIUM,
                    f"Multiple failed login attempts for user {event.user_id}",
                    {
                        'user_id': event.user_id,
                        'failed_attempts': len(recent_failures_by_user),
                        'time_window': self.alert_thresholds['time_window_minutes']
                    }
                )
    
    def _check_suspicious_patterns(self, event: SecurityEvent, current_time: datetime, time_window: timedelta):
        """Check for suspicious activity patterns"""
        suspicious_events = [
            SecurityEventType.SQL_INJECTION_ATTEMPT,
            SecurityEventType.XSS_ATTEMPT,
            SecurityEventType.PATH_TRAVERSAL_ATTEMPT,
            SecurityEventType.SUSPICIOUS_REQUEST
        ]
        
        if event.event_type in suspicious_events:
            recent_suspicious = [
                e for e in self.ip_events[event.source_ip]
                if e.event_type in suspicious_events
                and current_time - e.timestamp <= time_window
            ]
            
            if len(recent_suspicious) >= self.alert_thresholds['suspicious_requests_per_ip']:
                self._trigger_alert(
                    SecurityEventType.SUSPICIOUS_REQUEST,
                    SecurityEventSeverity.HIGH,
                    f"Multiple suspicious requests from IP {event.source_ip}",
                    {
                        'source_ip': event.source_ip,
                        'suspicious_requests': len(recent_suspicious),
                        'event_types': list(set(e.event_type.value for e in recent_suspicious))
                    }
                )
    
    def _check_rate_limit_violations(self, event: SecurityEvent, current_time: datetime, time_window: timedelta):
        """Check for repeated rate limit violations"""
        recent_violations = [
            e for e in self.ip_events[event.source_ip]
            if e.event_type == SecurityEventType.RATE_LIMIT_EXCEEDED
            and current_time - e.timestamp <= time_window
        ]
        
        if len(recent_violations) >= self.alert_thresholds['rate_limit_violations_per_ip']:
            self._trigger_alert(
                SecurityEventType.RATE_LIMIT_EXCEEDED,
                SecurityEventSeverity.MEDIUM,
                f"Repeated rate limit violations from IP {event.source_ip}",
                {
                    'source_ip': event.source_ip,
                    'violations': len(recent_violations),
                    'time_window': self.alert_thresholds['time_window_minutes']
                }
            )
    
    def _trigger_alert(self, event_type: SecurityEventType, severity: SecurityEventSeverity,
                      message: str, details: Dict[str, Any]):
        """Trigger a security alert"""
        alert_data = {
            'alert_id': self._generate_event_id(),
            'event_type': event_type.value,
            'severity': severity.value,
            'message': message,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'details': details
        }
        
        # Log the alert
        logger.critical(f"SECURITY_ALERT: {json.dumps(alert_data)}")
        
        # In production, send to alerting system (email, Slack, etc.)
        self._send_alert_notification(alert_data)
    
    def _send_alert_notification(self, alert_data: Dict[str, Any]):
        """Send alert notification (implement based on your alerting system)"""
        # This is where you would integrate with your alerting system
        # Examples: email, Slack, PagerDuty, etc.
        pass
    
    def _background_monitor(self):
        """Background thread for continuous monitoring"""
        while True:
            try:
                self._cleanup_old_events()
                self._generate_security_metrics()
                time.sleep(300)  # Run every 5 minutes
            except Exception as e:
                logger.error(f"Error in security monitoring background thread: {e}")
                time.sleep(60)  # Wait 1 minute before retrying
    
    def _cleanup_old_events(self):
        """Clean up old events to prevent memory issues"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
        
        with self.lock:
            # Clean up IP events
            for ip in list(self.ip_events.keys()):
                self.ip_events[ip] = [
                    event for event in self.ip_events[ip]
                    if event.timestamp > cutoff_time
                ]
                if not self.ip_events[ip]:
                    del self.ip_events[ip]
            
            # Clean up user events
            for user_id in list(self.user_events.keys()):
                self.user_events[user_id] = [
                    event for event in self.user_events[user_id]
                    if event.timestamp > cutoff_time
                ]
                if not self.user_events[user_id]:
                    del self.user_events[user_id]
    
    def _generate_security_metrics(self):
        """Generate security metrics for monitoring"""
        current_time = datetime.now(timezone.utc)
        last_hour = current_time - timedelta(hours=1)
        
        recent_events = [e for e in self.events if e.timestamp > last_hour]
        
        metrics = {
            'total_events_last_hour': len(recent_events),
            'events_by_type': defaultdict(int),
            'events_by_severity': defaultdict(int),
            'unique_ips_last_hour': len(set(e.source_ip for e in recent_events)),
            'top_source_ips': self._get_top_source_ips(recent_events),
        }
        
        for event in recent_events:
            metrics['events_by_type'][event.event_type.value] += 1
            metrics['events_by_severity'][event.severity.value] += 1
        
        logger.info(f"SECURITY_METRICS: {json.dumps(metrics, default=str)}")
    
    def _get_top_source_ips(self, events: List[SecurityEvent], limit: int = 10):
        """Get top source IPs by event count"""
        ip_counts = defaultdict(int)
        for event in events:
            ip_counts[event.source_ip] += 1
        
        return sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)[:limit]
    
    def get_security_dashboard_data(self):
        """Get data for security dashboard"""
        current_time = datetime.now(timezone.utc)
        last_24h = current_time - timedelta(hours=24)
        
        recent_events = [e for e in self.events if e.timestamp > last_24h]
        
        return {
            'total_events_24h': len(recent_events),
            'critical_events_24h': len([e for e in recent_events if e.severity == SecurityEventSeverity.CRITICAL]),
            'high_events_24h': len([e for e in recent_events if e.severity == SecurityEventSeverity.HIGH]),
            'events_by_hour': self._get_events_by_hour(recent_events),
            'top_event_types': self._get_top_event_types(recent_events),
            'top_source_ips': self._get_top_source_ips(recent_events),
            'recent_critical_events': [
                {
                    'event_id': e.event_id,
                    'event_type': e.event_type.value,
                    'timestamp': e.timestamp.isoformat(),
                    'source_ip': e.source_ip,
                    'endpoint': e.endpoint
                }
                for e in recent_events
                if e.severity == SecurityEventSeverity.CRITICAL
            ][-10:]  # Last 10 critical events
        }
    
    def _get_events_by_hour(self, events: List[SecurityEvent]):
        """Get event counts by hour"""
        hourly_counts = defaultdict(int)
        for event in events:
            hour_key = event.timestamp.strftime('%Y-%m-%d %H:00')
            hourly_counts[hour_key] += 1
        
        return dict(hourly_counts)
    
    def _get_top_event_types(self, events: List[SecurityEvent], limit: int = 10):
        """Get top event types by count"""
        type_counts = defaultdict(int)
        for event in events:
            type_counts[event.event_type.value] += 1
        
        return sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:limit]

# Global security monitor instance
security_monitor = SecurityMonitor()

def log_security_event(event_type: SecurityEventType, severity: SecurityEventSeverity,
                      source_ip: str, endpoint: str, user_agent: str = "",
                      user_id: str = None, details: Dict[str, Any] = None):
    """Convenience function to log security events"""
    security_monitor.log_security_event(
        event_type, severity, source_ip, endpoint, user_agent, user_id, details
    )
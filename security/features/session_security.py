# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Session Security Hardening Features

Implements session fingerprinting, suspicious activity detection, and security audit logging
for enhanced session security validation.
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
from flask import request
from security.core.security_utils import sanitize_for_log
from security.core.security_monitoring import SecurityEventType, SecurityEventSeverity, log_security_event

logger = logging.getLogger(__name__)


class SuspiciousActivityType(Enum):
    """Types of suspicious session activities"""
    RAPID_PLATFORM_SWITCHING = "rapid_platform_switching"
    UNUSUAL_ACCESS_PATTERN = "unusual_access_pattern"
    SESSION_FINGERPRINT_MISMATCH = "session_fingerprint_mismatch"
    CONCURRENT_SESSION_ABUSE = "concurrent_session_abuse"
    GEOGRAPHIC_ANOMALY = "geographic_anomaly"
    USER_AGENT_CHANGE = "user_agent_change"
    IP_ADDRESS_CHANGE = "ip_address_change"


@dataclass
class SessionFingerprint:
    """Session fingerprint for enhanced security validation"""
    user_agent_hash: str
    ip_address_hash: str
    accept_language: str
    accept_encoding: str
    timezone_offset: Optional[int]
    screen_resolution: Optional[str]
    created_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'user_agent_hash': self.user_agent_hash,
            'ip_address_hash': self.ip_address_hash,
            'accept_language': self.accept_language,
            'accept_encoding': self.accept_encoding,
            'timezone_offset': self.timezone_offset,
            'screen_resolution': self.screen_resolution,
            'created_at': self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionFingerprint':
        return cls(
            user_agent_hash=data['user_agent_hash'],
            ip_address_hash=data['ip_address_hash'],
            accept_language=data['accept_language'],
            accept_encoding=data['accept_encoding'],
            timezone_offset=data.get('timezone_offset'),
            screen_resolution=data.get('screen_resolution'),
            created_at=datetime.fromisoformat(data['created_at'])
        )


@dataclass
class SecurityAuditEvent:
    """Security audit event for session operations"""
    event_id: str
    session_id: str
    user_id: int
    event_type: str
    severity: str
    timestamp: datetime
    ip_address: str
    user_agent: str
    details: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'event_id': self.event_id,
            'session_id': self.session_id,
            'user_id': self.user_id,
            'event_type': self.event_type,
            'severity': self.severity,
            'timestamp': self.timestamp.isoformat(),
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'details': self.details
        }


class SessionSecurityHardening:
    """Enhanced session security with fingerprinting and suspicious activity detection"""
    
    def __init__(self, session_manager=None):
        self.session_manager = session_manager
        self.fingerprint_cache = {}  # In production, use Redis or database
        self.activity_log = {}  # In production, use persistent storage
        self.suspicious_threshold = 5  # Number of suspicious events before alert
        
    def create_session_fingerprint(self, request_data: Optional[Dict[str, Any]] = None) -> SessionFingerprint:
        """Create session fingerprint from request data"""
        try:
            # Use provided data or extract from Flask request
            if request_data:
                user_agent = request_data.get('user_agent', '')
                ip_address = request_data.get('ip_address', '')
                accept_language = request_data.get('accept_language', '')
                accept_encoding = request_data.get('accept_encoding', '')
                timezone_offset = request_data.get('timezone_offset')
                screen_resolution = request_data.get('screen_resolution')
            else:
                user_agent = request.headers.get('User-Agent', '')
                ip_address = self._get_client_ip()
                accept_language = request.headers.get('Accept-Language', '')
                accept_encoding = request.headers.get('Accept-Encoding', '')
                timezone_offset = None  # Would need client-side JS to provide
                screen_resolution = None  # Would need client-side JS to provide
            
            # Create hashes for sensitive data
            user_agent_hash = self._hash_value(user_agent)
            ip_address_hash = self._hash_value(ip_address)
            
            return SessionFingerprint(
                user_agent_hash=user_agent_hash,
                ip_address_hash=ip_address_hash,
                accept_language=accept_language[:50],  # Truncate to prevent abuse
                accept_encoding=accept_encoding[:100],
                timezone_offset=timezone_offset,
                screen_resolution=screen_resolution,
                created_at=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            logger.error(f"Error creating session fingerprint: {e}")
            # Return minimal fingerprint on error
            return SessionFingerprint(
                user_agent_hash=self._hash_value('unknown'),
                ip_address_hash=self._hash_value('unknown'),
                accept_language='unknown',
                accept_encoding='unknown',
                timezone_offset=None,
                screen_resolution=None,
                created_at=datetime.now(timezone.utc)
            )
    
    def validate_session_fingerprint(self, session_id: str, current_fingerprint: SessionFingerprint) -> Tuple[bool, Optional[str]]:
        """Validate session fingerprint against stored fingerprint"""
        try:
            stored_fingerprint = self.fingerprint_cache.get(session_id)
            if not stored_fingerprint:
                # First time validation - store fingerprint
                self.fingerprint_cache[session_id] = current_fingerprint
                return True, None
            
            # Check for significant changes
            suspicious_changes = []
            
            # User agent change (high severity)
            if stored_fingerprint.user_agent_hash != current_fingerprint.user_agent_hash:
                suspicious_changes.append("user_agent_change")
            
            # IP address change (medium severity - could be legitimate)
            if stored_fingerprint.ip_address_hash != current_fingerprint.ip_address_hash:
                suspicious_changes.append("ip_address_change")
            
            # Language/encoding changes (low severity)
            if stored_fingerprint.accept_language != current_fingerprint.accept_language:
                suspicious_changes.append("language_change")
            
            if suspicious_changes:
                reason = f"Fingerprint mismatch: {', '.join(suspicious_changes)}"
                self._log_suspicious_activity(
                    session_id, 
                    SuspiciousActivityType.SESSION_FINGERPRINT_MISMATCH,
                    {"changes": suspicious_changes, "stored": stored_fingerprint.to_dict(), "current": current_fingerprint.to_dict()}
                )
                
                # Decide if changes are acceptable
                if "user_agent_change" in suspicious_changes:
                    return False, reason  # User agent change is highly suspicious
                
                # Update stored fingerprint for legitimate changes
                self.fingerprint_cache[session_id] = current_fingerprint
                return True, f"Updated fingerprint due to: {reason}"
            
            return True, None
            
        except Exception as e:
            logger.error(f"Error validating session fingerprint: {e}")
            return True, f"Validation error: {e}"  # Allow on error to prevent lockout
    
    def detect_suspicious_session_activity(self, session_id: str, user_id: int, activity_type: str, details: Dict[str, Any] = None) -> bool:
        """Detect suspicious session activity patterns"""
        try:
            current_time = datetime.now(timezone.utc)
            
            # Initialize activity log for session
            if session_id not in self.activity_log:
                self.activity_log[session_id] = []
            
            # Add current activity
            activity_entry = {
                'timestamp': current_time,
                'activity_type': activity_type,
                'details': details or {}
            }
            self.activity_log[session_id].append(activity_entry)
            
            # Clean old entries (keep last 24 hours)
            cutoff_time = current_time - timedelta(hours=24)
            self.activity_log[session_id] = [
                entry for entry in self.activity_log[session_id]
                if entry['timestamp'] > cutoff_time
            ]
            
            # Analyze patterns
            recent_activities = self.activity_log[session_id]
            
            # Check for rapid platform switching
            if activity_type == 'platform_switch':
                platform_switches = [a for a in recent_activities if a['activity_type'] == 'platform_switch']
                if len(platform_switches) > 10:  # More than 10 switches in 24h
                    time_window = timedelta(minutes=5)
                    recent_switches = [
                        a for a in platform_switches
                        if current_time - a['timestamp'] <= time_window
                    ]
                    if len(recent_switches) >= 5:  # 5 switches in 5 minutes
                        self._log_suspicious_activity(
                            session_id,
                            SuspiciousActivityType.RAPID_PLATFORM_SWITCHING,
                            {"switches_in_5min": len(recent_switches), "total_switches_24h": len(platform_switches)}
                        )
                        return True
            
            # Check for unusual access patterns
            if len(recent_activities) > 100:  # More than 100 activities in 24h
                self._log_suspicious_activity(
                    session_id,
                    SuspiciousActivityType.UNUSUAL_ACCESS_PATTERN,
                    {"activities_24h": len(recent_activities)}
                )
                return True
            
            # Check for concurrent session abuse
            if activity_type == 'session_create':
                session_creates = [a for a in recent_activities if a['activity_type'] == 'session_create']
                if len(session_creates) > 5:  # More than 5 session creates in 24h
                    self._log_suspicious_activity(
                        session_id,
                        SuspiciousActivityType.CONCURRENT_SESSION_ABUSE,
                        {"session_creates_24h": len(session_creates)}
                    )
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error detecting suspicious activity: {e}")
            return False
    
    def create_security_audit_event(self, session_id: str, user_id: int, event_type: str, 
                                  severity: str = "info", details: Dict[str, Any] = None) -> SecurityAuditEvent:
        """Create security audit event for session operations"""
        try:
            import uuid
            
            event = SecurityAuditEvent(
                event_id=str(uuid.uuid4()),
                session_id=session_id,
                user_id=user_id,
                event_type=event_type,
                severity=severity,
                timestamp=datetime.now(timezone.utc),
                ip_address=self._get_client_ip(),
                user_agent=request.headers.get('User-Agent', '')[:200],
                details=details or {}
            )
            
            # Log to security monitoring system
            self._log_audit_event(event)
            
            return event
            
        except Exception as e:
            logger.error(f"Error creating security audit event: {e}")
            # Return minimal event on error
            return SecurityAuditEvent(
                event_id="error",
                session_id=session_id,
                user_id=user_id,
                event_type=event_type,
                severity="error",
                timestamp=datetime.now(timezone.utc),
                ip_address="unknown",
                user_agent="unknown",
                details={"error": str(e)}
            )
    
    def validate_session_security(self, session_id: str, user_id: int) -> Tuple[bool, List[str]]:
        """Comprehensive session security validation"""
        try:
            validation_issues = []
            
            # Create and validate fingerprint
            current_fingerprint = self.create_session_fingerprint()
            is_valid, fingerprint_issue = self.validate_session_fingerprint(session_id, current_fingerprint)
            
            if not is_valid:
                validation_issues.append(f"Fingerprint validation failed: {fingerprint_issue}")
            
            # Check for suspicious activity
            is_suspicious = self.detect_suspicious_session_activity(
                session_id, user_id, 'security_validation'
            )
            
            if is_suspicious:
                validation_issues.append("Suspicious activity detected")
            
            # Create audit event
            self.create_security_audit_event(
                session_id, user_id, 'security_validation',
                severity="warning" if validation_issues else "info",
                details={
                    "validation_passed": len(validation_issues) == 0,
                    "issues": validation_issues,
                    "fingerprint_valid": is_valid
                }
            )
            
            return len(validation_issues) == 0, validation_issues
            
        except Exception as e:
            logger.error(f"Error in session security validation: {e}")
            return True, []  # Allow on error to prevent lockout
    
    def invalidate_suspicious_sessions(self, user_id: int, reason: str) -> int:
        """Invalidate all sessions for a user due to suspicious activity"""
        try:
            if not self.session_manager:
                logger.warning("Session manager not available for session invalidation")
                return 0
            
            # Get all user sessions
            user_sessions = self.session_manager.get_user_active_sessions(user_id)
            
            invalidated_count = 0
            for session_info in user_sessions:
                session_id = session_info['session_id']
                
                # Create audit event
                self.create_security_audit_event(
                    session_id, user_id, 'session_invalidated',
                    severity="high",
                    details={"reason": reason, "automatic_invalidation": True}
                )
                
                # Invalidate session
                if self.session_manager.invalidate_session(session_id, reason):
                    invalidated_count += 1
                
                # Clean up fingerprint cache
                if session_id in self.fingerprint_cache:
                    del self.fingerprint_cache[session_id]
                
                # Clean up activity log
                if session_id in self.activity_log:
                    del self.activity_log[session_id]
            
            # Log security event
            log_security_event(
                SecurityEventType.SESSION_HIJACKING,
                SecurityEventSeverity.HIGH,
                self._get_client_ip(),
                request.endpoint or 'unknown',
                request.headers.get('User-Agent', ''),
                str(user_id),
                {
                    "reason": reason,
                    "sessions_invalidated": invalidated_count,
                    "total_sessions": len(user_sessions)
                }
            )
            
            logger.warning(f"Invalidated {invalidated_count} sessions for user {user_id} due to: {reason}")
            return invalidated_count
            
        except Exception as e:
            logger.error(f"Error invalidating suspicious sessions: {e}")
            return 0
    
    def get_session_security_metrics(self, session_id: str) -> Dict[str, Any]:
        """Get security metrics for a session"""
        try:
            metrics = {
                'session_id': session_id,
                'has_fingerprint': session_id in self.fingerprint_cache,
                'activity_count_24h': 0,
                'suspicious_events': 0,
                'last_activity': None,
                'fingerprint_age_hours': None
            }
            
            # Activity metrics
            if session_id in self.activity_log:
                current_time = datetime.now(timezone.utc)
                cutoff_time = current_time - timedelta(hours=24)
                
                recent_activities = [
                    a for a in self.activity_log[session_id]
                    if a['timestamp'] > cutoff_time
                ]
                
                metrics['activity_count_24h'] = len(recent_activities)
                
                if recent_activities:
                    metrics['last_activity'] = max(a['timestamp'] for a in recent_activities).isoformat()
                
                # Count suspicious events
                suspicious_activities = [
                    a for a in recent_activities
                    if 'suspicious' in a.get('details', {})
                ]
                metrics['suspicious_events'] = len(suspicious_activities)
            
            # Fingerprint metrics
            if session_id in self.fingerprint_cache:
                fingerprint = self.fingerprint_cache[session_id]
                age = datetime.now(timezone.utc) - fingerprint.created_at
                metrics['fingerprint_age_hours'] = age.total_seconds() / 3600
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting session security metrics: {e}")
            return {'error': str(e)}
    
    def cleanup_expired_data(self, max_age_hours: int = 24) -> Dict[str, int]:
        """Clean up expired fingerprints and activity logs"""
        try:
            current_time = datetime.now(timezone.utc)
            cutoff_time = current_time - timedelta(hours=max_age_hours)
            
            # Clean fingerprint cache
            expired_fingerprints = []
            for session_id, fingerprint in list(self.fingerprint_cache.items()):
                if fingerprint.created_at < cutoff_time:
                    expired_fingerprints.append(session_id)
            
            for session_id in expired_fingerprints:
                del self.fingerprint_cache[session_id]
            
            # Clean activity logs
            expired_activities = []
            for session_id, activities in list(self.activity_log.items()):
                # Remove old activities
                recent_activities = [
                    a for a in activities
                    if a['timestamp'] > cutoff_time
                ]
                
                if recent_activities:
                    self.activity_log[session_id] = recent_activities
                else:
                    expired_activities.append(session_id)
            
            for session_id in expired_activities:
                del self.activity_log[session_id]
            
            cleanup_stats = {
                'expired_fingerprints': len(expired_fingerprints),
                'expired_activity_logs': len(expired_activities),
                'remaining_fingerprints': len(self.fingerprint_cache),
                'remaining_activity_logs': len(self.activity_log)
            }
            
            logger.info(f"Session security cleanup completed: {cleanup_stats}")
            return cleanup_stats
            
        except Exception as e:
            logger.error(f"Error cleaning up expired session security data: {e}")
            return {'error': str(e)}
    
    def _hash_value(self, value: str) -> str:
        """Create hash of a value for fingerprinting"""
        if not value:
            return hashlib.sha256(b'empty').hexdigest()[:16]
        return hashlib.sha256(value.encode('utf-8')).hexdigest()[:16]
    
    def _get_client_ip(self) -> str:
        """Get client IP address from request"""
        try:
            # Check for forwarded headers first
            forwarded_for = request.headers.get('X-Forwarded-For')
            if forwarded_for:
                return forwarded_for.split(',')[0].strip()
            
            real_ip = request.headers.get('X-Real-IP')
            if real_ip:
                return real_ip.strip()
            
            return request.remote_addr or 'unknown'
            
        except Exception:
            return 'unknown'
    
    def _log_suspicious_activity(self, session_id: str, activity_type: SuspiciousActivityType, details: Dict[str, Any]):
        """Log suspicious activity for monitoring"""
        try:
            # Log to security monitoring system
            log_security_event(
                SecurityEventType.SUSPICIOUS_REQUEST,
                SecurityEventSeverity.MEDIUM,
                self._get_client_ip(),
                request.endpoint or 'unknown',
                request.headers.get('User-Agent', ''),
                details.get('user_id'),
                {
                    'session_id': sanitize_for_log(session_id),
                    'activity_type': activity_type.value,
                    'details': details
                }
            )
            
            # Add to activity log with suspicious flag
            if session_id not in self.activity_log:
                self.activity_log[session_id] = []
            
            self.activity_log[session_id].append({
                'timestamp': datetime.now(timezone.utc),
                'activity_type': 'suspicious_activity',
                'details': {
                    'suspicious': True,
                    'type': activity_type.value,
                    'data': details
                }
            })
            
        except Exception as e:
            logger.error(f"Error logging suspicious activity: {e}")
    
    def _log_audit_event(self, event: SecurityAuditEvent):
        """Log security audit event"""
        try:
            # Log to standard logging
            logger.info(f"SECURITY_AUDIT: {json.dumps(event.to_dict())}")
            
            # Log to security monitoring system
            severity_map = {
                'info': SecurityEventSeverity.LOW,
                'warning': SecurityEventSeverity.MEDIUM,
                'error': SecurityEventSeverity.HIGH,
                'critical': SecurityEventSeverity.CRITICAL
            }
            
            log_security_event(
                SecurityEventType.SECURITY_MISCONFIGURATION,  # Generic security event
                severity_map.get(event.severity, SecurityEventSeverity.LOW),
                event.ip_address,
                request.endpoint or 'unknown',
                event.user_agent,
                str(event.user_id),
                {
                    'audit_event_id': event.event_id,
                    'audit_event_type': event.event_type,
                    'session_id': sanitize_for_log(event.session_id),
                    'details': event.details
                }
            )
            
        except Exception as e:
            logger.error(f"Error logging audit event: {e}")


# Global instance for easy access
session_security = SessionSecurityHardening()


def initialize_session_security(session_manager):
    """Initialize session security with session manager"""
    global session_security
    session_security.session_manager = session_manager
    return session_security


def validate_session_security(session_id: str, user_id: int) -> Tuple[bool, List[str]]:
    """Convenience function for session security validation"""
    return session_security.validate_session_security(session_id, user_id)


def create_session_fingerprint(request_data: Optional[Dict[str, Any]] = None) -> SessionFingerprint:
    """Convenience function for creating session fingerprint"""
    return session_security.create_session_fingerprint(request_data)


def detect_suspicious_activity(session_id: str, user_id: int, activity_type: str, details: Dict[str, Any] = None) -> bool:
    """Convenience function for detecting suspicious activity"""
    return session_security.detect_suspicious_session_activity(session_id, user_id, activity_type, details)
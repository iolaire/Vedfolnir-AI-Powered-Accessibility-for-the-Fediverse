# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Security Event Logger for User Management

Provides comprehensive security event logging and monitoring for user management operations.
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from enum import Enum
from flask import request, g
from sqlalchemy.orm import Session
from models import UserAuditLog, User
from security.core.security_utils import sanitize_for_log, mask_sensitive_data

logger = logging.getLogger(__name__)


class SecurityEventType(Enum):
    """Types of security events"""
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGIN_BLOCKED = "login_blocked"
    REGISTRATION_SUCCESS = "registration_success"
    REGISTRATION_FAILURE = "registration_failure"
    PASSWORD_RESET_REQUEST = "password_reset_request"
    PASSWORD_RESET_SUCCESS = "password_reset_success"
    PASSWORD_RESET_FAILURE = "password_reset_failure"
    PASSWORD_CHANGE_SUCCESS = "password_change_success"
    PASSWORD_CHANGE_FAILURE = "password_change_failure"
    EMAIL_VERIFICATION_SUCCESS = "email_verification_success"
    EMAIL_VERIFICATION_FAILURE = "email_verification_failure"
    PROFILE_UPDATE_SUCCESS = "profile_update_success"
    PROFILE_UPDATE_FAILURE = "profile_update_failure"
    PROFILE_DELETE_SUCCESS = "profile_delete_success"
    PROFILE_DELETE_FAILURE = "profile_delete_failure"
    ADMIN_USER_CREATE = "admin_user_create"
    ADMIN_USER_UPDATE = "admin_user_update"
    ADMIN_USER_DELETE = "admin_user_delete"
    ADMIN_PASSWORD_RESET = "admin_password_reset"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    CSRF_FAILURE = "csrf_failure"
    INPUT_VALIDATION_FAILURE = "input_validation_failure"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    GDPR_DATA_EXPORT = "gdpr_data_export"
    GDPR_DATA_RECTIFICATION = "gdpr_data_rectification"
    GDPR_DATA_ERASURE = "gdpr_data_erasure"
    SESSION_HIJACK_ATTEMPT = "session_hijack_attempt"
    BRUTE_FORCE_ATTEMPT = "brute_force_attempt"


class SecurityEventSeverity(Enum):
    """Severity levels for security events"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityEventLogger:
    """Comprehensive security event logging system"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.logger = logging.getLogger(f"{__name__}.SecurityEventLogger")
        
        # Configure security-specific logger
        self._setup_security_logger()
    
    def _setup_security_logger(self):
        """Set up dedicated security event logger"""
        security_handler = logging.FileHandler('logs/security_events.log')
        security_formatter = logging.Formatter(
            '%(asctime)s - SECURITY - %(levelname)s - %(message)s'
        )
        security_handler.setFormatter(security_formatter)
        
        # Create security logger
        self.security_logger = logging.getLogger('security_events')
        self.security_logger.addHandler(security_handler)
        self.security_logger.setLevel(logging.INFO)
    
    def log_security_event(
        self,
        event_type: SecurityEventType,
        severity: SecurityEventSeverity = SecurityEventSeverity.MEDIUM,
        user_id: Optional[int] = None,
        admin_user_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log a security event with comprehensive details
        
        Args:
            event_type: Type of security event
            severity: Severity level of the event
            user_id: ID of the user involved (if applicable)
            admin_user_id: ID of the admin user performing the action (if applicable)
            details: Specific details about the event
            ip_address: IP address of the request
            user_agent: User agent string
            additional_context: Additional context information
        """
        try:
            # Get request context if available
            if not ip_address and request:
                ip_address = self._get_client_ip()
            if not user_agent and request:
                user_agent = request.headers.get('User-Agent', 'Unknown')
            
            # Sanitize sensitive data
            sanitized_details = self._sanitize_event_details(details or {})
            sanitized_user_agent = sanitize_for_log(user_agent)
            
            # Create audit log entry
            audit_details = {
                'event_type': event_type.value,
                'severity': severity.value,
                'timestamp': datetime.utcnow().isoformat(),
                'details': sanitized_details,
                'additional_context': additional_context or {}
            }
            
            UserAuditLog.log_action(
                session=self.db_session,
                action=f"security_event_{event_type.value}",
                user_id=user_id,
                admin_user_id=admin_user_id,
                details=json.dumps(audit_details),
                ip_address=ip_address,
                user_agent=sanitized_user_agent
            )
            
            # Log to security event file
            log_message = self._format_security_log_message(
                event_type, severity, user_id, admin_user_id, 
                sanitized_details, ip_address, additional_context
            )
            
            # Choose log level based on severity
            if severity == SecurityEventSeverity.CRITICAL:
                self.security_logger.critical(log_message)
            elif severity == SecurityEventSeverity.HIGH:
                self.security_logger.error(log_message)
            elif severity == SecurityEventSeverity.MEDIUM:
                self.security_logger.warning(log_message)
            else:
                self.security_logger.info(log_message)
            
            # Check for patterns that require immediate attention
            self._check_security_patterns(event_type, user_id, ip_address)
            
        except Exception as e:
            self.logger.error(f"Failed to log security event: {e}")
    
    def log_authentication_event(
        self,
        success: bool,
        username_or_email: str,
        user_id: Optional[int] = None,
        failure_reason: Optional[str] = None,
        blocked: bool = False
    ) -> None:
        """Log authentication-related events"""
        if success:
            event_type = SecurityEventType.LOGIN_SUCCESS
            severity = SecurityEventSeverity.LOW
            details = {'username': sanitize_for_log(username_or_email)}
        elif blocked:
            event_type = SecurityEventType.LOGIN_BLOCKED
            severity = SecurityEventSeverity.HIGH
            details = {
                'username': sanitize_for_log(username_or_email),
                'reason': 'account_locked_or_rate_limited'
            }
        else:
            event_type = SecurityEventType.LOGIN_FAILURE
            severity = SecurityEventSeverity.MEDIUM
            details = {
                'username': sanitize_for_log(username_or_email),
                'failure_reason': sanitize_for_log(failure_reason or 'invalid_credentials')
            }
        
        self.log_security_event(
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            details=details
        )
    
    def log_registration_event(
        self,
        success: bool,
        email: str,
        user_id: Optional[int] = None,
        failure_reason: Optional[str] = None
    ) -> None:
        """Log user registration events"""
        event_type = SecurityEventType.REGISTRATION_SUCCESS if success else SecurityEventType.REGISTRATION_FAILURE
        severity = SecurityEventSeverity.LOW if success else SecurityEventSeverity.MEDIUM
        
        details = {
            'email': mask_sensitive_data(email, visible_chars=0),  # Mask email for privacy
            'domain': email.split('@')[-1] if '@' in email else 'unknown'
        }
        
        if not success and failure_reason:
            details['failure_reason'] = sanitize_for_log(failure_reason)
        
        self.log_security_event(
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            details=details
        )
    
    def log_password_event(
        self,
        event_type: SecurityEventType,
        success: bool,
        user_id: Optional[int] = None,
        admin_user_id: Optional[int] = None,
        failure_reason: Optional[str] = None
    ) -> None:
        """Log password-related events"""
        severity = SecurityEventSeverity.LOW if success else SecurityEventSeverity.MEDIUM
        
        details = {'success': success}
        if not success and failure_reason:
            details['failure_reason'] = sanitize_for_log(failure_reason)
        
        self.log_security_event(
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            admin_user_id=admin_user_id,
            details=details
        )
    
    def log_admin_action(
        self,
        action: str,
        target_user_id: Optional[int] = None,
        admin_user_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log administrative actions"""
        event_type_map = {
            'create_user': SecurityEventType.ADMIN_USER_CREATE,
            'update_user': SecurityEventType.ADMIN_USER_UPDATE,
            'delete_user': SecurityEventType.ADMIN_USER_DELETE,
            'reset_password': SecurityEventType.ADMIN_PASSWORD_RESET
        }
        
        event_type = event_type_map.get(action, SecurityEventType.ADMIN_USER_UPDATE)
        
        self.log_security_event(
            event_type=event_type,
            severity=SecurityEventSeverity.MEDIUM,
            user_id=target_user_id,
            admin_user_id=admin_user_id,
            details=details or {}
        )
    
    def log_rate_limit_exceeded(
        self,
        endpoint: str,
        limit_type: str = "general",
        user_id: Optional[int] = None
    ) -> None:
        """Log rate limiting events"""
        self.log_security_event(
            event_type=SecurityEventType.RATE_LIMIT_EXCEEDED,
            severity=SecurityEventSeverity.MEDIUM,
            user_id=user_id,
            details={
                'endpoint': sanitize_for_log(endpoint),
                'limit_type': limit_type
            }
        )
    
    def log_csrf_failure(self, endpoint: str, user_id: Optional[int] = None) -> None:
        """Log CSRF token validation failures"""
        self.log_security_event(
            event_type=SecurityEventType.CSRF_FAILURE,
            severity=SecurityEventSeverity.HIGH,
            user_id=user_id,
            details={'endpoint': sanitize_for_log(endpoint)}
        )
    
    def log_input_validation_failure(
        self,
        field_name: str,
        validation_type: str,
        user_id: Optional[int] = None
    ) -> None:
        """Log input validation failures"""
        self.log_security_event(
            event_type=SecurityEventType.INPUT_VALIDATION_FAILURE,
            severity=SecurityEventSeverity.MEDIUM,
            user_id=user_id,
            details={
                'field_name': sanitize_for_log(field_name),
                'validation_type': validation_type
            }
        )
    
    def log_gdpr_event(
        self,
        action: str,
        user_id: int,
        admin_user_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log GDPR-related events"""
        event_type_map = {
            'data_export': SecurityEventType.GDPR_DATA_EXPORT,
            'data_rectification': SecurityEventType.GDPR_DATA_RECTIFICATION,
            'data_erasure': SecurityEventType.GDPR_DATA_ERASURE
        }
        
        event_type = event_type_map.get(action, SecurityEventType.GDPR_DATA_EXPORT)
        
        self.log_security_event(
            event_type=event_type,
            severity=SecurityEventSeverity.MEDIUM,
            user_id=user_id,
            admin_user_id=admin_user_id,
            details=details or {}
        )
    
    def _get_client_ip(self) -> str:
        """Get the real client IP address"""
        # Check for forwarded headers
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            # Take the first IP in the chain
            return forwarded_for.split(',')[0].strip()
        
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip
        
        return request.remote_addr or 'unknown'
    
    def _sanitize_event_details(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize event details for safe logging"""
        sanitized = {}
        
        # Fields that should be masked
        sensitive_fields = {
            'password', 'token', 'access_token', 'api_key', 'apikey',
            'csrf_token', 'secret', 'private_key', 'session_id'
        }
        
        for key, value in details.items():
            key_lower = key.lower()
            
            if any(sensitive in key_lower for sensitive in sensitive_fields):
                sanitized[key] = mask_sensitive_data(str(value))
            elif key_lower == 'email':
                sanitized[key] = mask_sensitive_data(str(value), visible_chars=0)
            else:
                sanitized[key] = sanitize_for_log(value)
        
        return sanitized
    
    def _format_security_log_message(
        self,
        event_type: SecurityEventType,
        severity: SecurityEventSeverity,
        user_id: Optional[int],
        admin_user_id: Optional[int],
        details: Dict[str, Any],
        ip_address: Optional[str],
        additional_context: Optional[Dict[str, Any]]
    ) -> str:
        """Format security log message"""
        message_parts = [
            f"EVENT={event_type.value}",
            f"SEVERITY={severity.value}",
            f"IP={ip_address or 'unknown'}"
        ]
        
        if user_id:
            message_parts.append(f"USER_ID={user_id}")
        
        if admin_user_id:
            message_parts.append(f"ADMIN_ID={admin_user_id}")
        
        if details:
            details_str = json.dumps(details, separators=(',', ':'))
            message_parts.append(f"DETAILS={details_str}")
        
        if additional_context:
            context_str = json.dumps(additional_context, separators=(',', ':'))
            message_parts.append(f"CONTEXT={context_str}")
        
        return " | ".join(message_parts)
    
    def _check_security_patterns(
        self,
        event_type: SecurityEventType,
        user_id: Optional[int],
        ip_address: Optional[str]
    ) -> None:
        """Check for security patterns that require immediate attention"""
        try:
            # Check for brute force attempts
            if event_type == SecurityEventType.LOGIN_FAILURE and ip_address:
                self._check_brute_force_pattern(ip_address)
            
            # Check for suspicious user activity
            if user_id and event_type in [
                SecurityEventType.LOGIN_FAILURE,
                SecurityEventType.PASSWORD_RESET_FAILURE,
                SecurityEventType.CSRF_FAILURE
            ]:
                self._check_suspicious_user_activity(user_id)
                
        except Exception as e:
            self.logger.error(f"Error checking security patterns: {e}")
    
    def _check_brute_force_pattern(self, ip_address: str) -> None:
        """Check for brute force attack patterns"""
        # Count recent failed login attempts from this IP
        cutoff_time = datetime.utcnow() - timedelta(minutes=15)
        
        recent_failures = self.db_session.query(UserAuditLog).filter(
            UserAuditLog.action.like('security_event_login_failure%'),
            UserAuditLog.ip_address == ip_address,
            UserAuditLog.created_at >= cutoff_time
        ).count()
        
        if recent_failures >= 10:  # 10 failures in 15 minutes
            self.log_security_event(
                event_type=SecurityEventType.BRUTE_FORCE_ATTEMPT,
                severity=SecurityEventSeverity.CRITICAL,
                details={
                    'failure_count': recent_failures,
                    'time_window': '15_minutes',
                    'source_ip': ip_address
                },
                ip_address=ip_address
            )
    
    def _check_suspicious_user_activity(self, user_id: int) -> None:
        """Check for suspicious activity patterns for a specific user"""
        # Count recent security events for this user
        cutoff_time = datetime.utcnow() - timedelta(hours=1)
        
        recent_events = self.db_session.query(UserAuditLog).filter(
            UserAuditLog.user_id == user_id,
            UserAuditLog.action.like('security_event_%'),
            UserAuditLog.created_at >= cutoff_time
        ).count()
        
        if recent_events >= 20:  # 20 security events in 1 hour
            self.log_security_event(
                event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
                severity=SecurityEventSeverity.HIGH,
                user_id=user_id,
                details={
                    'event_count': recent_events,
                    'time_window': '1_hour'
                }
            )


def get_security_event_logger(db_session: Session) -> SecurityEventLogger:
    """Get a security event logger instance"""
    return SecurityEventLogger(db_session)
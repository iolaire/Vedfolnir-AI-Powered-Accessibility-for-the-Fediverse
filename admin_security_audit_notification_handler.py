# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Admin Security and Audit Notification Handler

This module provides real-time security event notifications and audit log notifications
for administrators via the unified WebSocket notification system. It replaces legacy
security notification systems with real-time admin notifications for security events,
authentication failures, suspicious activity alerts, and audit log compliance notifications.

Requirements: 4.5, 8.1, 8.2, 8.3, 8.4, 8.5
"""

import logging
import uuid
import json
import threading
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict, deque

from unified_notification_manager import (
    UnifiedNotificationManager, AdminNotificationMessage, 
    NotificationType, NotificationPriority, NotificationCategory
)
from security.monitoring.security_event_logger import (
    SecurityEventLogger, SecurityEventType, SecurityEventSeverity
)
from security.monitoring.security_alerting import SecurityAlertManager, AlertSeverity
from session_security import SessionSecurityManager
from models import UserRole, UserAuditLog
from database import DatabaseManager

logger = logging.getLogger(__name__)


class SecurityNotificationType(Enum):
    """Types of security notifications"""
    AUTHENTICATION_FAILURE = "authentication_failure"
    AUTHENTICATION_SUCCESS = "authentication_success"
    BRUTE_FORCE_ATTEMPT = "brute_force_attempt"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    SESSION_HIJACK_ATTEMPT = "session_hijack_attempt"
    CSRF_VIOLATION = "csrf_violation"
    INPUT_VALIDATION_FAILURE = "input_validation_failure"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    UNAUTHORIZED_ACCESS_ATTEMPT = "unauthorized_access_attempt"
    PRIVILEGE_ESCALATION_ATTEMPT = "privilege_escalation_attempt"
    AUDIT_LOG_ANOMALY = "audit_log_anomaly"
    COMPLIANCE_VIOLATION = "compliance_violation"
    SECURITY_POLICY_VIOLATION = "security_policy_violation"
    CRITICAL_SYSTEM_ACCESS = "critical_system_access"
    DATA_BREACH_INDICATOR = "data_breach_indicator"


@dataclass
class SecurityEventContext:
    """Context information for security events"""
    event_type: SecurityNotificationType
    severity: SecurityEventSeverity
    user_id: Optional[int] = None
    admin_user_id: Optional[int] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    endpoint: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None


@dataclass
class SecurityThresholds:
    """Security monitoring thresholds"""
    failed_login_threshold: int = 5  # failures per 15 minutes
    brute_force_threshold: int = 10  # failures per 15 minutes from same IP
    suspicious_activity_threshold: int = 20  # events per hour per user
    csrf_violation_threshold: int = 3  # violations per hour
    rate_limit_threshold: int = 50  # rate limit hits per hour
    session_anomaly_threshold: int = 5  # anomalies per hour
    audit_log_gap_threshold: int = 300  # seconds without audit logs (critical systems)


class AdminSecurityAuditNotificationHandler:
    """
    Admin security and audit notification handler for real-time monitoring
    
    Provides real-time security event notifications via admin WebSocket namespace,
    authentication failure and suspicious activity alerts, audit log and compliance
    notifications, and immediate delivery of critical security notifications.
    """
    
    def __init__(self, notification_manager: UnifiedNotificationManager,
                 security_event_logger: SecurityEventLogger,
                 security_alert_manager: SecurityAlertManager,
                 session_security_manager: SessionSecurityManager,
                 db_manager: DatabaseManager,
                 monitoring_interval: int = 30,
                 alert_cooldown: int = 300):
        """
        Initialize admin security and audit notification handler
        
        Args:
            notification_manager: Unified notification manager instance
            security_event_logger: Security event logger instance
            security_alert_manager: Security alert manager instance
            session_security_manager: Session security manager instance
            db_manager: Database manager instance
            monitoring_interval: Security monitoring interval in seconds (default: 30)
            alert_cooldown: Cooldown period between similar alerts in seconds (default: 300)
        """
        self.notification_manager = notification_manager
        self.security_event_logger = security_event_logger
        self.security_alert_manager = security_alert_manager
        self.session_security_manager = session_security_manager
        self.db_manager = db_manager
        self.monitoring_interval = monitoring_interval
        self.alert_cooldown = alert_cooldown
        
        # Security monitoring thresholds
        self.thresholds = SecurityThresholds()
        
        # Event tracking for pattern detection
        self._event_history = defaultdict(deque)  # event_type -> deque of timestamps
        self._ip_failure_tracking = defaultdict(deque)  # ip_address -> deque of failure timestamps
        self._user_activity_tracking = defaultdict(deque)  # user_id -> deque of event timestamps
        
        # Alert tracking to prevent spam
        self._alert_history = {}  # alert_key -> last_sent_timestamp
        self._active_alerts = set()  # active alert types
        
        # Monitoring thread control
        self._monitoring_thread = None
        self._stop_monitoring = threading.Event()
        self._monitoring_active = False
        
        # Statistics tracking
        self._stats = {
            'security_notifications_sent': 0,
            'critical_alerts_sent': 0,
            'authentication_failures_tracked': 0,
            'suspicious_activities_detected': 0,
            'audit_anomalies_detected': 0,
            'compliance_violations_detected': 0
        }
        
        logger.info("Admin Security and Audit Notification Handler initialized")
    
    def start_monitoring(self) -> bool:
        """
        Start real-time security monitoring
        
        Returns:
            True if monitoring started successfully, False otherwise
        """
        try:
            if self._monitoring_active:
                logger.warning("Security monitoring is already active")
                return True
            
            self._stop_monitoring.clear()
            self._monitoring_thread = threading.Thread(
                target=self._security_monitoring_loop,
                name="SecurityAuditMonitoring",
                daemon=True
            )
            self._monitoring_thread.start()
            self._monitoring_active = True
            
            # Send startup notification to admins
            self._send_security_notification(
                SecurityEventContext(
                    event_type=SecurityNotificationType.CRITICAL_SYSTEM_ACCESS,
                    severity=SecurityEventSeverity.LOW,
                    additional_data={
                        'system_event': 'security_monitoring_started',
                        'monitoring_interval': self.monitoring_interval,
                        'alert_cooldown': self.alert_cooldown
                    }
                ),
                title="Security Monitoring Started",
                message="Real-time security and audit monitoring has been activated",
                priority=NotificationPriority.NORMAL
            )
            
            logger.info("Security and audit monitoring started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start security monitoring: {e}")
            return False
    
    def stop_monitoring(self) -> bool:
        """
        Stop real-time security monitoring
        
        Returns:
            True if monitoring stopped successfully, False otherwise
        """
        try:
            if not self._monitoring_active:
                logger.warning("Security monitoring is not active")
                return True
            
            self._stop_monitoring.set()
            
            if self._monitoring_thread and self._monitoring_thread.is_alive():
                self._monitoring_thread.join(timeout=10)
            
            self._monitoring_active = False
            
            # Send shutdown notification to admins
            self._send_security_notification(
                SecurityEventContext(
                    event_type=SecurityNotificationType.CRITICAL_SYSTEM_ACCESS,
                    severity=SecurityEventSeverity.MEDIUM,
                    additional_data={
                        'system_event': 'security_monitoring_stopped',
                        'reason': 'manual_stop'
                    }
                ),
                title="Security Monitoring Stopped",
                message="Real-time security and audit monitoring has been deactivated",
                priority=NotificationPriority.HIGH
            )
            
            logger.info("Security and audit monitoring stopped")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop security monitoring: {e}")
            return False
    
    def notify_authentication_failure(self, username: str, ip_address: str,
                                    failure_reason: str, user_id: Optional[int] = None,
                                    user_agent: Optional[str] = None) -> bool:
        """
        Send notification for authentication failure
        
        Args:
            username: Username that failed authentication
            ip_address: Source IP address
            failure_reason: Reason for authentication failure
            user_id: User ID if known
            user_agent: User agent string
            
        Returns:
            True if notification sent successfully
        """
        try:
            # Track failure for pattern detection
            self._track_authentication_failure(ip_address, user_id)
            
            # Determine severity based on failure patterns
            severity = self._assess_authentication_failure_severity(ip_address, user_id)
            
            context = SecurityEventContext(
                event_type=SecurityNotificationType.AUTHENTICATION_FAILURE,
                severity=severity,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                additional_data={
                    'username': username,
                    'failure_reason': failure_reason,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            )
            
            # Check for brute force patterns
            if self._detect_brute_force_pattern(ip_address):
                self.notify_brute_force_attempt(ip_address, username)
            
            # Send notification based on severity
            if severity in [SecurityEventSeverity.HIGH, SecurityEventSeverity.CRITICAL]:
                title = "Critical Authentication Failure" if severity == SecurityEventSeverity.CRITICAL else "Authentication Failure Alert"
                message = f"Authentication failure for user '{username}' from {ip_address}: {failure_reason}"
                priority = NotificationPriority.CRITICAL if severity == SecurityEventSeverity.CRITICAL else NotificationPriority.HIGH
                
                success = self._send_security_notification(context, title, message, priority)
                
                if success:
                    self._stats['authentication_failures_tracked'] += 1
                
                return success
            
            # For low/medium severity, just log and track
            self._stats['authentication_failures_tracked'] += 1
            return True
            
        except Exception as e:
            logger.error(f"Error sending authentication failure notification: {e}")
            return False
    
    def notify_suspicious_activity(self, user_id: int, activity_type: str,
                                 details: Dict[str, Any], session_id: Optional[str] = None,
                                 ip_address: Optional[str] = None) -> bool:
        """
        Send notification for suspicious activity
        
        Args:
            user_id: User ID involved in suspicious activity
            activity_type: Type of suspicious activity
            details: Additional details about the activity
            session_id: Session ID if applicable
            ip_address: Source IP address
            
        Returns:
            True if notification sent successfully
        """
        try:
            # Track activity for pattern detection
            self._track_user_activity(user_id)
            
            # Assess severity based on activity type and patterns
            severity = self._assess_suspicious_activity_severity(activity_type, user_id)
            
            context = SecurityEventContext(
                event_type=SecurityNotificationType.SUSPICIOUS_ACTIVITY,
                severity=severity,
                user_id=user_id,
                session_id=session_id,
                ip_address=ip_address,
                additional_data={
                    'activity_type': activity_type,
                    'details': details,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            )
            
            title = f"Suspicious Activity Detected: {activity_type}"
            message = f"Suspicious activity detected for user ID {user_id}: {activity_type}"
            if ip_address:
                message += f" from {ip_address}"
            
            priority = NotificationPriority.CRITICAL if severity == SecurityEventSeverity.CRITICAL else NotificationPriority.HIGH
            
            success = self._send_security_notification(context, title, message, priority)
            
            if success:
                self._stats['suspicious_activities_detected'] += 1
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending suspicious activity notification: {e}")
            return False
    
    def notify_brute_force_attempt(self, ip_address: str, target_username: Optional[str] = None) -> bool:
        """
        Send notification for brute force attempt
        
        Args:
            ip_address: Source IP address of brute force attempt
            target_username: Target username if known
            
        Returns:
            True if notification sent successfully
        """
        try:
            # Get failure count for this IP
            failure_count = len(self._ip_failure_tracking[ip_address])
            
            context = SecurityEventContext(
                event_type=SecurityNotificationType.BRUTE_FORCE_ATTEMPT,
                severity=SecurityEventSeverity.CRITICAL,
                ip_address=ip_address,
                additional_data={
                    'failure_count': failure_count,
                    'target_username': target_username,
                    'time_window': '15_minutes',
                    'threshold': self.thresholds.brute_force_threshold,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            )
            
            title = "Brute Force Attack Detected"
            message = f"Brute force attack detected from {ip_address} with {failure_count} failed attempts"
            if target_username:
                message += f" targeting user '{target_username}'"
            
            success = self._send_security_notification(
                context, title, message, NotificationPriority.CRITICAL
            )
            
            if success:
                self._stats['critical_alerts_sent'] += 1
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending brute force notification: {e}")
            return False
    
    def notify_csrf_violation(self, endpoint: str, user_id: Optional[int] = None,
                            ip_address: Optional[str] = None, details: Optional[Dict[str, Any]] = None) -> bool:
        """
        Send notification for CSRF violation
        
        Args:
            endpoint: Endpoint where CSRF violation occurred
            user_id: User ID if known
            ip_address: Source IP address
            details: Additional details about the violation
            
        Returns:
            True if notification sent successfully
        """
        try:
            context = SecurityEventContext(
                event_type=SecurityNotificationType.CSRF_VIOLATION,
                severity=SecurityEventSeverity.HIGH,
                user_id=user_id,
                ip_address=ip_address,
                endpoint=endpoint,
                additional_data={
                    'endpoint': endpoint,
                    'details': details or {},
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            )
            
            title = "CSRF Violation Detected"
            message = f"CSRF token validation failed for endpoint {endpoint}"
            if ip_address:
                message += f" from {ip_address}"
            
            success = self._send_security_notification(
                context, title, message, NotificationPriority.HIGH
            )
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending CSRF violation notification: {e}")
            return False
    
    def notify_audit_log_anomaly(self, anomaly_type: str, details: Dict[str, Any]) -> bool:
        """
        Send notification for audit log anomaly
        
        Args:
            anomaly_type: Type of audit log anomaly
            details: Details about the anomaly
            
        Returns:
            True if notification sent successfully
        """
        try:
            context = SecurityEventContext(
                event_type=SecurityNotificationType.AUDIT_LOG_ANOMALY,
                severity=SecurityEventSeverity.HIGH,
                additional_data={
                    'anomaly_type': anomaly_type,
                    'details': details,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            )
            
            title = f"Audit Log Anomaly: {anomaly_type}"
            message = f"Audit log anomaly detected: {anomaly_type}"
            
            success = self._send_security_notification(
                context, title, message, NotificationPriority.HIGH
            )
            
            if success:
                self._stats['audit_anomalies_detected'] += 1
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending audit log anomaly notification: {e}")
            return False
    
    def notify_compliance_violation(self, violation_type: str, component: str,
                                  compliance_rate: float, details: Optional[Dict[str, Any]] = None) -> bool:
        """
        Send notification for compliance violation
        
        Args:
            violation_type: Type of compliance violation
            component: Component where violation occurred
            compliance_rate: Current compliance rate
            details: Additional details about the violation
            
        Returns:
            True if notification sent successfully
        """
        try:
            severity = SecurityEventSeverity.CRITICAL if compliance_rate < 0.7 else SecurityEventSeverity.HIGH
            
            context = SecurityEventContext(
                event_type=SecurityNotificationType.COMPLIANCE_VIOLATION,
                severity=severity,
                additional_data={
                    'violation_type': violation_type,
                    'component': component,
                    'compliance_rate': compliance_rate,
                    'details': details or {},
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            )
            
            title = f"Compliance Violation: {violation_type}"
            message = f"Compliance violation detected in {component}: {violation_type} (rate: {compliance_rate:.1%})"
            
            priority = NotificationPriority.CRITICAL if severity == SecurityEventSeverity.CRITICAL else NotificationPriority.HIGH
            
            success = self._send_security_notification(context, title, message, priority)
            
            if success:
                self._stats['compliance_violations_detected'] += 1
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending compliance violation notification: {e}")
            return False
    
    def send_immediate_security_alert(self, alert_type: str, details: Dict[str, Any]) -> bool:
        """
        Send immediate security alert to all admins
        
        Args:
            alert_type: Type of security alert
            details: Alert details
            
        Returns:
            True if alert sent successfully
        """
        try:
            context = SecurityEventContext(
                event_type=SecurityNotificationType.CRITICAL_SYSTEM_ACCESS,
                severity=SecurityEventSeverity.CRITICAL,
                additional_data={
                    'alert_type': alert_type,
                    'details': details,
                    'immediate': True,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            )
            
            title = f"IMMEDIATE SECURITY ALERT: {alert_type}"
            message = f"Immediate security alert: {alert_type}"
            
            success = self._send_security_notification(
                context, title, message, NotificationPriority.CRITICAL
            )
            
            if success:
                self._stats['critical_alerts_sent'] += 1
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending immediate security alert: {e}")
            return False
    
    def get_security_monitoring_stats(self) -> Dict[str, Any]:
        """
        Get security monitoring statistics
        
        Returns:
            Dictionary containing security monitoring statistics
        """
        try:
            return {
                'monitoring_active': self._monitoring_active,
                'monitoring_interval': self.monitoring_interval,
                'alert_cooldown': self.alert_cooldown,
                'active_alerts': list(self._active_alerts),
                'statistics': self._stats.copy(),
                'thresholds': {
                    'failed_login_threshold': self.thresholds.failed_login_threshold,
                    'brute_force_threshold': self.thresholds.brute_force_threshold,
                    'suspicious_activity_threshold': self.thresholds.suspicious_activity_threshold,
                    'csrf_violation_threshold': self.thresholds.csrf_violation_threshold
                },
                'event_tracking': {
                    'tracked_ips': len(self._ip_failure_tracking),
                    'tracked_users': len(self._user_activity_tracking),
                    'total_events': sum(len(events) for events in self._event_history.values())
                },
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get security monitoring stats: {e}")
            return {'error': str(e)}
    
    def _security_monitoring_loop(self) -> None:
        """Main security monitoring loop running in background thread"""
        logger.info("Security monitoring loop started")
        
        while not self._stop_monitoring.is_set():
            try:
                # Check for audit log anomalies
                self._check_audit_log_anomalies()
                
                # Check for compliance violations
                self._check_compliance_violations()
                
                # Clean up old tracking data
                self._cleanup_tracking_data()
                
                # Wait for next monitoring cycle
                self._stop_monitoring.wait(self.monitoring_interval)
                
            except Exception as e:
                logger.error(f"Error in security monitoring loop: {e}")
                # Continue monitoring even if there's an error
                self._stop_monitoring.wait(self.monitoring_interval)
        
        logger.info("Security monitoring loop stopped")
    
    def _track_authentication_failure(self, ip_address: str, user_id: Optional[int]) -> None:
        """Track authentication failure for pattern detection"""
        try:
            current_time = time.time()
            
            # Track by IP address
            if ip_address:
                self._ip_failure_tracking[ip_address].append(current_time)
                # Keep only last 15 minutes
                cutoff_time = current_time - 900  # 15 minutes
                while (self._ip_failure_tracking[ip_address] and 
                       self._ip_failure_tracking[ip_address][0] < cutoff_time):
                    self._ip_failure_tracking[ip_address].popleft()
            
            # Track by user
            if user_id:
                self._user_activity_tracking[user_id].append(current_time)
                # Keep only last hour
                cutoff_time = current_time - 3600  # 1 hour
                while (self._user_activity_tracking[user_id] and 
                       self._user_activity_tracking[user_id][0] < cutoff_time):
                    self._user_activity_tracking[user_id].popleft()
            
        except Exception as e:
            logger.error(f"Error tracking authentication failure: {e}")
    
    def _track_user_activity(self, user_id: int) -> None:
        """Track user activity for pattern detection"""
        try:
            current_time = time.time()
            self._user_activity_tracking[user_id].append(current_time)
            
            # Keep only last hour
            cutoff_time = current_time - 3600  # 1 hour
            while (self._user_activity_tracking[user_id] and 
                   self._user_activity_tracking[user_id][0] < cutoff_time):
                self._user_activity_tracking[user_id].popleft()
            
        except Exception as e:
            logger.error(f"Error tracking user activity: {e}")
    
    def _detect_brute_force_pattern(self, ip_address: str) -> bool:
        """Detect brute force attack pattern"""
        try:
            if ip_address not in self._ip_failure_tracking:
                return False
            
            failure_count = len(self._ip_failure_tracking[ip_address])
            return failure_count >= self.thresholds.brute_force_threshold
            
        except Exception as e:
            logger.error(f"Error detecting brute force pattern: {e}")
            return False
    
    def _assess_authentication_failure_severity(self, ip_address: str, user_id: Optional[int]) -> SecurityEventSeverity:
        """Assess severity of authentication failure"""
        try:
            # Check IP-based patterns
            ip_failures = len(self._ip_failure_tracking.get(ip_address, []))
            
            # Check user-based patterns
            user_failures = 0
            if user_id:
                user_failures = len(self._user_activity_tracking.get(user_id, []))
            
            # Determine severity
            if ip_failures >= self.thresholds.brute_force_threshold:
                return SecurityEventSeverity.CRITICAL
            elif ip_failures >= self.thresholds.failed_login_threshold or user_failures >= 10:
                return SecurityEventSeverity.HIGH
            elif ip_failures >= 3 or user_failures >= 5:
                return SecurityEventSeverity.MEDIUM
            else:
                return SecurityEventSeverity.LOW
                
        except Exception as e:
            logger.error(f"Error assessing authentication failure severity: {e}")
            return SecurityEventSeverity.MEDIUM
    
    def _assess_suspicious_activity_severity(self, activity_type: str, user_id: int) -> SecurityEventSeverity:
        """Assess severity of suspicious activity"""
        try:
            # High-risk activity types
            critical_activities = {
                'session_hijack_attempt', 'privilege_escalation', 'data_breach_indicator',
                'unauthorized_admin_access', 'sql_injection_attempt'
            }
            
            high_risk_activities = {
                'rapid_platform_switching', 'unusual_access_pattern', 'suspicious_file_access',
                'multiple_failed_operations', 'anomalous_behavior'
            }
            
            if activity_type in critical_activities:
                return SecurityEventSeverity.CRITICAL
            elif activity_type in high_risk_activities:
                return SecurityEventSeverity.HIGH
            else:
                # Check frequency of activities for this user
                user_activities = len(self._user_activity_tracking.get(user_id, []))
                if user_activities >= self.thresholds.suspicious_activity_threshold:
                    return SecurityEventSeverity.HIGH
                elif user_activities >= 10:
                    return SecurityEventSeverity.MEDIUM
                else:
                    return SecurityEventSeverity.LOW
                    
        except Exception as e:
            logger.error(f"Error assessing suspicious activity severity: {e}")
            return SecurityEventSeverity.MEDIUM
    
    def _check_audit_log_anomalies(self) -> None:
        """Check for audit log anomalies"""
        try:
            with self.db_manager.get_session() as session:
                # Check for gaps in audit logs
                recent_cutoff = datetime.now(timezone.utc) - timedelta(minutes=10)
                recent_audit_count = session.query(UserAuditLog).filter(
                    UserAuditLog.created_at >= recent_cutoff
                ).count()
                
                # If no audit logs in the last 10 minutes during business hours, it might be anomalous
                current_hour = datetime.now().hour
                if 8 <= current_hour <= 18 and recent_audit_count == 0:  # Business hours
                    self.notify_audit_log_anomaly(
                        'audit_log_gap',
                        {
                            'gap_duration_minutes': 10,
                            'expected_activity': True,
                            'business_hours': True
                        }
                    )
                
                # Check for unusual audit log patterns
                hour_cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
                hourly_audit_count = session.query(UserAuditLog).filter(
                    UserAuditLog.created_at >= hour_cutoff
                ).count()
                
                # If unusually high audit activity (potential attack or system issue)
                if hourly_audit_count > 1000:  # More than 1000 audit logs per hour
                    self.notify_audit_log_anomaly(
                        'excessive_audit_activity',
                        {
                            'hourly_count': hourly_audit_count,
                            'threshold': 1000,
                            'potential_causes': ['attack', 'system_malfunction', 'bulk_operation']
                        }
                    )
                
        except Exception as e:
            logger.error(f"Error checking audit log anomalies: {e}")
    
    def _check_compliance_violations(self) -> None:
        """Check for compliance violations"""
        try:
            # This is a placeholder for compliance checking logic
            # In a real implementation, you would check various compliance metrics
            
            # Example: Check CSRF protection compliance
            # (This would integrate with actual CSRF monitoring)
            csrf_compliance_rate = 0.95  # Placeholder value
            
            if csrf_compliance_rate < 0.9:
                self.notify_compliance_violation(
                    'csrf_protection_degraded',
                    'web_application',
                    csrf_compliance_rate,
                    {
                        'threshold': 0.9,
                        'recommendation': 'Review CSRF token implementation'
                    }
                )
            
        except Exception as e:
            logger.error(f"Error checking compliance violations: {e}")
    
    def _cleanup_tracking_data(self) -> None:
        """Clean up old tracking data"""
        try:
            current_time = time.time()
            
            # Clean up IP failure tracking (keep last 15 minutes)
            cutoff_time = current_time - 900
            for ip_address in list(self._ip_failure_tracking.keys()):
                failures = self._ip_failure_tracking[ip_address]
                while failures and failures[0] < cutoff_time:
                    failures.popleft()
                if not failures:
                    del self._ip_failure_tracking[ip_address]
            
            # Clean up user activity tracking (keep last hour)
            cutoff_time = current_time - 3600
            for user_id in list(self._user_activity_tracking.keys()):
                activities = self._user_activity_tracking[user_id]
                while activities and activities[0] < cutoff_time:
                    activities.popleft()
                if not activities:
                    del self._user_activity_tracking[user_id]
            
        except Exception as e:
            logger.error(f"Error cleaning up tracking data: {e}")
    
    def _should_send_alert(self, alert_key: str) -> bool:
        """Check if alert should be sent based on cooldown period"""
        try:
            current_time = time.time()
            last_sent = self._alert_history.get(alert_key, 0)
            
            if current_time - last_sent >= self.alert_cooldown:
                self._alert_history[alert_key] = current_time
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking alert cooldown: {e}")
            return False
    
    def _send_security_notification(self, context: SecurityEventContext, title: str,
                                  message: str, priority: NotificationPriority) -> bool:
        """
        Send security notification to admin users
        
        Args:
            context: Security event context
            title: Notification title
            message: Notification message
            priority: Notification priority
            
        Returns:
            True if notification sent successfully, False otherwise
        """
        try:
            # Create alert key for cooldown checking
            alert_key = f"{context.event_type.value}_{context.ip_address or 'unknown'}"
            
            # Check cooldown for non-critical alerts
            if priority != NotificationPriority.CRITICAL and not self._should_send_alert(alert_key):
                return True  # Skip sending but return success
            
            # Create admin notification message
            notification = AdminNotificationMessage(
                id=f"security_{context.event_type.value}_{int(time.time())}",
                type=self._get_notification_type_for_priority(priority),
                title=title,
                message=message,
                priority=priority,
                category=NotificationCategory.SECURITY,
                admin_only=True,
                security_event_data={
                    'event_type': context.event_type.value,
                    'severity': context.severity.value,
                    'user_id': context.user_id,
                    'admin_user_id': context.admin_user_id,
                    'session_id': context.session_id,
                    'ip_address': context.ip_address,
                    'user_agent': context.user_agent,
                    'endpoint': context.endpoint,
                    'additional_data': context.additional_data or {},
                    'timestamp': datetime.now(timezone.utc).isoformat()
                },
                requires_admin_action=(priority == NotificationPriority.CRITICAL),
                data={
                    'security_event': True,
                    'event_category': 'security_audit',
                    'monitoring_source': 'admin_security_audit_handler',
                    'alert_key': alert_key
                }
            )
            
            # Send notification via unified notification manager
            success = self.notification_manager.send_admin_notification(notification)
            
            if success:
                self._stats['security_notifications_sent'] += 1
                if priority == NotificationPriority.CRITICAL:
                    self._stats['critical_alerts_sent'] += 1
                
                self._active_alerts.add(context.event_type.value)
                logger.info(f"Sent security notification: {context.event_type.value}")
            else:
                logger.error(f"Failed to send security notification: {context.event_type.value}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending security notification: {e}")
            return False
    
    def _get_notification_type_for_priority(self, priority: NotificationPriority) -> NotificationType:
        """Get notification type based on priority"""
        if priority == NotificationPriority.CRITICAL:
            return NotificationType.ERROR
        elif priority == NotificationPriority.HIGH:
            return NotificationType.WARNING
        else:
            return NotificationType.INFO


def create_admin_security_audit_notification_handler(
    notification_manager: UnifiedNotificationManager,
    security_event_logger: SecurityEventLogger,
    security_alert_manager: SecurityAlertManager,
    session_security_manager: SessionSecurityManager,
    db_manager: DatabaseManager
) -> AdminSecurityAuditNotificationHandler:
    """
    Factory function to create admin security and audit notification handler
    
    Args:
        notification_manager: Unified notification manager instance
        security_event_logger: Security event logger instance
        security_alert_manager: Security alert manager instance
        session_security_manager: Session security manager instance
        db_manager: Database manager instance
        
    Returns:
        AdminSecurityAuditNotificationHandler instance
    """
    return AdminSecurityAuditNotificationHandler(
        notification_manager,
        security_event_logger,
        security_alert_manager,
        session_security_manager,
        db_manager
    )
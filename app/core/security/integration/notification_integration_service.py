# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Security Notification Integration Service

This service integrates the admin security and audit notification handler with
existing security systems, providing a unified interface for security event
notifications and replacing legacy security notification mechanisms.

Requirements: 4.5, 8.1, 8.2, 8.3, 8.4, 8.5
"""

"""
⚠️  DEPRECATED: This file is deprecated and will be removed in a future version.
Please use the unified notification system instead:
- unified_notification_manager.py (core system)
- notification_service_adapters.py (service adapters)
- notification_helpers.py (helper functions)
- app/websocket/core/consolidated_handlers.py (WebSocket handling)

Migration guide: docs/implementation/notification-consolidation-final-summary.md
"""

import warnings
warnings.warn(
    "This notification system is deprecated. Use the unified notification system instead.",
    DeprecationWarning,
    stacklevel=2
)


import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from flask import request, g

from app.services.admin.components.admin_security_audit_notification_handler import (
    AdminSecurityAuditNotificationHandler,
    SecurityNotificationType,
    SecurityEventContext
)
from app.core.security.monitoring.security_event_logger import SecurityEventType, SecurityEventSeverity
from app.core.security.monitoring.security_alerting import SecurityAlertManager, AlertSeverity
from models import UserRole

logger = logging.getLogger(__name__)


class SecurityNotificationIntegrationService:
    """
    Integration service for security notifications
    
    Provides a unified interface for all security event notifications,
    integrating with existing security systems and the new admin notification handler.
    """
    
    def __init__(self, security_handler: AdminSecurityAuditNotificationHandler,
                 security_alert_manager: SecurityAlertManager):
        """
        Initialize security notification integration service
        
        Args:
            security_handler: Admin security audit notification handler
            security_alert_manager: Security alert manager
        """
        self.security_handler = security_handler
        self.security_alert_manager = security_alert_manager
        
        # Integration mappings
        self.event_type_mapping = {
            SecurityEventType.LOGIN_FAILURE: SecurityNotificationType.AUTHENTICATION_FAILURE,
            SecurityEventType.LOGIN_BLOCKED: SecurityNotificationType.AUTHENTICATION_FAILURE,
            SecurityEventType.BRUTE_FORCE_ATTEMPT: SecurityNotificationType.BRUTE_FORCE_ATTEMPT,
            SecurityEventType.SUSPICIOUS_ACTIVITY: SecurityNotificationType.SUSPICIOUS_ACTIVITY,
            SecurityEventType.SESSION_HIJACK_ATTEMPT: SecurityNotificationType.SESSION_HIJACK_ATTEMPT,
            SecurityEventType.CSRF_FAILURE: SecurityNotificationType.CSRF_VIOLATION,
            SecurityEventType.INPUT_VALIDATION_FAILURE: SecurityNotificationType.INPUT_VALIDATION_FAILURE,
            SecurityEventType.RATE_LIMIT_EXCEEDED: SecurityNotificationType.RATE_LIMIT_EXCEEDED
        }
        
        logger.info("Security Notification Integration Service initialized")
    
    def handle_authentication_event(self, event_type: SecurityEventType, username: str,
                                   success: bool, user_id: Optional[int] = None,
                                   failure_reason: Optional[str] = None,
                                   ip_address: Optional[str] = None,
                                   user_agent: Optional[str] = None) -> bool:
        """
        Handle authentication events and send appropriate notifications
        
        Args:
            event_type: Type of security event
            username: Username involved in authentication
            success: Whether authentication was successful
            user_id: User ID if known
            failure_reason: Reason for failure if applicable
            ip_address: Source IP address
            user_agent: User agent string
            
        Returns:
            True if handled successfully
        """
        try:
            # Get request context if not provided
            if not ip_address and request:
                ip_address = self._get_client_ip()
            if not user_agent and request:
                user_agent = request.headers.get('User-Agent', 'Unknown')
            
            if success:
                # For successful authentications, we might want to log but not always notify
                # Only notify for admin logins or suspicious successful logins
                if user_id and self._is_admin_user(user_id):
                    return self.security_handler.notify_authentication_failure(
                        username=username,
                        ip_address=ip_address or 'unknown',
                        failure_reason='admin_login_success',
                        user_id=user_id,
                        user_agent=user_agent
                    )
                return True
            else:
                # Handle authentication failures
                return self.security_handler.notify_authentication_failure(
                    username=username,
                    ip_address=ip_address or 'unknown',
                    failure_reason=failure_reason or 'authentication_failed',
                    user_id=user_id,
                    user_agent=user_agent
                )
                
        except Exception as e:
            logger.error(f"Error handling authentication event: {e}")
            return False
    
    def handle_security_violation(self, violation_type: str, endpoint: Optional[str] = None,
                                user_id: Optional[int] = None, details: Optional[Dict[str, Any]] = None,
                                severity: SecurityEventSeverity = SecurityEventSeverity.MEDIUM) -> bool:
        """
        Handle security violations (CSRF, input validation, etc.)
        
        Args:
            violation_type: Type of security violation
            endpoint: Endpoint where violation occurred
            user_id: User ID if known
            details: Additional details about the violation
            severity: Severity of the violation
            
        Returns:
            True if handled successfully
        """
        try:
            ip_address = self._get_client_ip()
            
            if violation_type == 'csrf_violation':
                return self.security_handler.notify_csrf_violation(
                    endpoint=endpoint or 'unknown',
                    user_id=user_id,
                    ip_address=ip_address,
                    details=details
                )
            elif violation_type == 'input_validation_failure':
                # Convert to suspicious activity notification
                return self.security_handler.notify_suspicious_activity(
                    user_id=user_id or 0,
                    activity_type='input_validation_failure',
                    details=details or {},
                    ip_address=ip_address
                )
            elif violation_type == 'rate_limit_exceeded':
                return self.security_handler.notify_suspicious_activity(
                    user_id=user_id or 0,
                    activity_type='rate_limit_exceeded',
                    details={
                        'endpoint': endpoint,
                        'details': details or {}
                    },
                    ip_address=ip_address
                )
            else:
                # Generic security violation
                return self.security_handler.notify_suspicious_activity(
                    user_id=user_id or 0,
                    activity_type=violation_type,
                    details=details or {},
                    ip_address=ip_address
                )
                
        except Exception as e:
            logger.error(f"Error handling security violation: {e}")
            return False
    
    def handle_suspicious_user_activity(self, user_id: int, activity_type: str,
                                      details: Dict[str, Any], session_id: Optional[str] = None) -> bool:
        """
        Handle suspicious user activity detection
        
        Args:
            user_id: User ID involved in suspicious activity
            activity_type: Type of suspicious activity
            details: Details about the activity
            session_id: Session ID if applicable
            
        Returns:
            True if handled successfully
        """
        try:
            ip_address = self._get_client_ip()
            
            return self.security_handler.notify_suspicious_activity(
                user_id=user_id,
                activity_type=activity_type,
                details=details,
                session_id=session_id,
                ip_address=ip_address
            )
            
        except Exception as e:
            logger.error(f"Error handling suspicious user activity: {e}")
            return False
    
    def handle_audit_event(self, event_type: str, details: Dict[str, Any],
                          user_id: Optional[int] = None, admin_user_id: Optional[int] = None) -> bool:
        """
        Handle audit events and check for anomalies
        
        Args:
            event_type: Type of audit event
            details: Event details
            user_id: User ID if applicable
            admin_user_id: Admin user ID if applicable
            
        Returns:
            True if handled successfully
        """
        try:
            # Check for audit anomalies based on event patterns
            if self._detect_audit_anomaly(event_type, details, user_id):
                return self.security_handler.notify_audit_log_anomaly(
                    anomaly_type=f"unusual_{event_type}",
                    details={
                        'original_event': event_type,
                        'event_details': details,
                        'user_id': user_id,
                        'admin_user_id': admin_user_id,
                        'detection_reason': 'pattern_analysis'
                    }
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Error handling audit event: {e}")
            return False
    
    def handle_compliance_check(self, component: str, compliance_metrics: Dict[str, float]) -> bool:
        """
        Handle compliance check results and notify of violations
        
        Args:
            component: Component being checked
            compliance_metrics: Dictionary of compliance metrics
            
        Returns:
            True if handled successfully
        """
        try:
            violations_detected = False
            
            for metric_name, compliance_rate in compliance_metrics.items():
                # Define thresholds for different compliance metrics
                thresholds = {
                    'csrf_protection': 0.95,
                    'input_validation': 0.90,
                    'session_security': 0.95,
                    'authentication_security': 0.98,
                    'authorization_checks': 0.99,
                    'audit_logging': 0.99
                }
                
                threshold = thresholds.get(metric_name, 0.90)
                
                if compliance_rate < threshold:
                    violations_detected = True
                    
                    success = self.security_handler.notify_compliance_violation(
                        violation_type=f"{metric_name}_below_threshold",
                        component=component,
                        compliance_rate=compliance_rate,
                        details={
                            'threshold': threshold,
                            'metric_name': metric_name,
                            'recommendation': self._get_compliance_recommendation(metric_name)
                        }
                    )
                    
                    if not success:
                        logger.error(f"Failed to send compliance violation notification for {metric_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error handling compliance check: {e}")
            return False
    
    def handle_critical_security_incident(self, incident_type: str, details: Dict[str, Any]) -> bool:
        """
        Handle critical security incidents requiring immediate attention
        
        Args:
            incident_type: Type of security incident
            details: Incident details
            
        Returns:
            True if handled successfully
        """
        try:
            return self.security_handler.send_immediate_security_alert(
                alert_type=incident_type,
                details=details
            )
            
        except Exception as e:
            logger.error(f"Error handling critical security incident: {e}")
            return False
    
    def integrate_with_flask_login(self, app):
        """
        Integrate with Flask-Login to monitor authentication events
        
        Args:
            app: Flask application instance
        """
        try:
            from flask_login import user_logged_in, user_logged_out, user_login_confirmed
            
            @user_logged_in.connect_via(app)
            def on_user_logged_in(sender, user, **extra):
                """Handle successful user login"""
                self.handle_authentication_event(
                    event_type=SecurityEventType.LOGIN_SUCCESS,
                    username=getattr(user, 'username', 'unknown'),
                    success=True,
                    user_id=getattr(user, 'id', None)
                )
            
            @user_logged_out.connect_via(app)
            def on_user_logged_out(sender, user, **extra):
                """Handle user logout"""
                # Could be used for session tracking
                pass
            
            logger.info("Integrated with Flask-Login for authentication monitoring")
            
        except ImportError:
            logger.warning("Flask-Login not available for integration")
        except Exception as e:
            logger.error(f"Error integrating with Flask-Login: {e}")
    
    def integrate_with_csrf_protection(self, csrf_manager):
        """
        Integrate with CSRF protection to monitor violations
        
        Args:
            csrf_manager: CSRF protection manager
        """
        try:
            # This would integrate with the existing CSRF protection system
            # to automatically send notifications when CSRF violations occur
            
            # Example integration (would need to be adapted to actual CSRF manager)
            if hasattr(csrf_manager, 'on_csrf_violation'):
                csrf_manager.on_csrf_violation = self._handle_csrf_violation_callback
            
            logger.info("Integrated with CSRF protection for violation monitoring")
            
        except Exception as e:
            logger.error(f"Error integrating with CSRF protection: {e}")
    
    def _handle_csrf_violation_callback(self, endpoint: str, user_id: Optional[int] = None):
        """Callback for CSRF violations"""
        self.handle_security_violation(
            violation_type='csrf_violation',
            endpoint=endpoint,
            user_id=user_id
        )
    
    def _get_client_ip(self) -> str:
        """Get client IP address from request"""
        try:
            if request:
                # Check for forwarded headers
                forwarded_for = request.headers.get('X-Forwarded-For')
                if forwarded_for:
                    return forwarded_for.split(',')[0].strip()
                
                real_ip = request.headers.get('X-Real-IP')
                if real_ip:
                    return real_ip
                
                return request.remote_addr or 'unknown'
        except Exception:
            pass
        return 'unknown'
    
    def _is_admin_user(self, user_id: int) -> bool:
        """Check if user is an admin"""
        try:
            # This would check the user's role in the database
            # For now, return False as a placeholder
            return False
        except Exception:
            return False
    
    def _detect_audit_anomaly(self, event_type: str, details: Dict[str, Any], user_id: Optional[int]) -> bool:
        """Detect if an audit event represents an anomaly"""
        try:
            # Implement anomaly detection logic
            # For now, return False as a placeholder
            
            # Example: Detect unusual admin actions
            admin_actions = ['user_delete', 'role_change', 'system_config_change']
            if event_type in admin_actions and user_id:
                # Could check frequency, time of day, etc.
                pass
            
            return False
            
        except Exception as e:
            logger.error(f"Error detecting audit anomaly: {e}")
            return False
    
    def _get_compliance_recommendation(self, metric_name: str) -> str:
        """Get recommendation for compliance violation"""
        recommendations = {
            'csrf_protection': 'Review and update CSRF token implementation across all forms',
            'input_validation': 'Implement stricter input validation and sanitization',
            'session_security': 'Enhance session security with fingerprinting and timeout controls',
            'authentication_security': 'Strengthen authentication mechanisms and password policies',
            'authorization_checks': 'Review and update authorization checks for all endpoints',
            'audit_logging': 'Ensure comprehensive audit logging for all security-relevant actions'
        }
        
        return recommendations.get(metric_name, 'Review security implementation for this component')
    
    def get_integration_stats(self) -> Dict[str, Any]:
        """Get integration statistics"""
        try:
            security_stats = self.security_handler.get_security_monitoring_stats()
            
            return {
                'integration_service': 'active',
                'security_handler_stats': security_stats,
                'event_type_mappings': len(self.event_type_mapping),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting integration stats: {e}")
            return {'error': str(e)}


def create_security_notification_integration_service(
    security_handler: AdminSecurityAuditNotificationHandler,
    security_alert_manager: SecurityAlertManager
) -> SecurityNotificationIntegrationService:
    """
    Factory function to create security notification integration service
    
    Args:
        security_handler: Admin security audit notification handler
        security_alert_manager: Security alert manager
        
    Returns:
        SecurityNotificationIntegrationService instance
    """
    return SecurityNotificationIntegrationService(security_handler, security_alert_manager)
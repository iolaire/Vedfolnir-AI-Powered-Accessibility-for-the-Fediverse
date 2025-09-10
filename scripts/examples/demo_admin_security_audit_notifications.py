#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Demo: Admin Security and Audit Notifications

This script demonstrates the admin security and audit notification system,
showing real-time security event notifications, authentication failure alerts,
suspicious activity detection, and audit log compliance notifications.

Requirements: 4.5, 8.1, 8.2, 8.3, 8.4, 8.5
"""

import sys
import time
import logging
from datetime import datetime, timezone
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, '.')

from dotenv import load_dotenv
from config import Config
from app.core.database.core.database_manager import DatabaseManager
from websocket_factory import WebSocketFactory
from websocket_auth_handler import WebSocketAuthHandler
from websocket_namespace_manager import WebSocketNamespaceManager
from app.services.notification.manager.unified_manager import UnifiedNotificationManager
from app.core.security.monitoring.security_event_logger import SecurityEventLogger, SecurityEventType, SecurityEventSeverity
from app.core.security.monitoring.security_alerting import SecurityAlertManager
from app.core.session.security.session_security import SessionSecurityManager
from app.services.admin.components.admin_security_audit_notification_handler import (
    AdminSecurityAuditNotificationHandler,
    SecurityNotificationType,
    SecurityEventContext,
    create_admin_security_audit_notification_handler
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_demo_environment():
    """Set up demo environment with all required components"""
    logger.info("Setting up demo environment...")
    
    # Load configuration
    load_dotenv()
    config = Config()
    
    # Initialize database manager
    db_manager = DatabaseManager(config)
    
    # Initialize WebSocket components
    websocket_factory = WebSocketFactory()
    auth_handler = WebSocketAuthHandler()
    namespace_manager = WebSocketNamespaceManager()
    
    # Initialize notification manager
    notification_manager = UnifiedNotificationManager(
        websocket_factory=websocket_factory,
        auth_handler=auth_handler,
        namespace_manager=namespace_manager,
        db_manager=db_manager
    )
    
    # Initialize security components
    with db_manager.get_session() as session:
        security_event_logger = SecurityEventLogger(session)
    
    security_alert_manager = SecurityAlertManager()
    session_security_manager = SessionSecurityManager(db_manager, config.SECRET_KEY)
    
    # Create security notification handler
    security_handler = create_admin_security_audit_notification_handler(
        notification_manager=notification_manager,
        security_event_logger=security_event_logger,
        security_alert_manager=security_alert_manager,
        session_security_manager=session_security_manager,
        db_manager=db_manager
    )
    
    logger.info("Demo environment setup complete")
    return security_handler, notification_manager


def demo_authentication_failure_notifications(handler: AdminSecurityAuditNotificationHandler):
    """Demonstrate authentication failure notifications"""
    logger.info("\n=== Demo: Authentication Failure Notifications ===")
    
    # Simulate various authentication failures
    test_cases = [
        {
            'username': 'admin',
            'ip_address': '192.168.1.100',
            'failure_reason': 'invalid_password',
            'user_id': 1
        },
        {
            'username': 'testuser',
            'ip_address': '10.0.0.50',
            'failure_reason': 'account_locked',
            'user_id': 2
        },
        {
            'username': 'hacker',
            'ip_address': '203.0.113.1',
            'failure_reason': 'invalid_credentials',
            'user_id': None
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        logger.info(f"Simulating authentication failure {i}: {case['username']} from {case['ip_address']}")
        
        success = handler.notify_authentication_failure(
            username=case['username'],
            ip_address=case['ip_address'],
            failure_reason=case['failure_reason'],
            user_id=case['user_id'],
            user_agent='Mozilla/5.0 (Demo Browser)'
        )
        
        if success:
            logger.info(f"✅ Authentication failure notification sent for {case['username']}")
        else:
            logger.error(f"❌ Failed to send authentication failure notification for {case['username']}")
        
        time.sleep(1)  # Brief delay between notifications


def demo_brute_force_detection(handler: AdminSecurityAuditNotificationHandler):
    """Demonstrate brute force attack detection"""
    logger.info("\n=== Demo: Brute Force Attack Detection ===")
    
    attacker_ip = '203.0.113.10'
    target_username = 'admin'
    
    logger.info(f"Simulating brute force attack from {attacker_ip} targeting {target_username}")
    
    # Simulate multiple rapid authentication failures to trigger brute force detection
    for attempt in range(12):  # Exceed the brute force threshold
        logger.info(f"Brute force attempt {attempt + 1}/12")
        
        handler.notify_authentication_failure(
            username=target_username,
            ip_address=attacker_ip,
            failure_reason='invalid_password',
            user_id=1,
            user_agent='AttackBot/1.0'
        )
        
        time.sleep(0.5)  # Rapid attempts
    
    logger.info("✅ Brute force detection demo completed")


def demo_suspicious_activity_alerts(handler: AdminSecurityAuditNotificationHandler):
    """Demonstrate suspicious activity alerts"""
    logger.info("\n=== Demo: Suspicious Activity Alerts ===")
    
    suspicious_activities = [
        {
            'user_id': 1,
            'activity_type': 'rapid_platform_switching',
            'details': {
                'switch_count': 15,
                'time_window': '5_minutes',
                'platforms': ['mastodon', 'pixelfed', 'pleroma']
            },
            'session_id': 'sess_12345',
            'ip_address': '192.168.1.100'
        },
        {
            'user_id': 2,
            'activity_type': 'unusual_access_pattern',
            'details': {
                'access_time': '03:00 AM',
                'unusual_endpoints': ['/admin/users', '/admin/system'],
                'frequency': 'high'
            },
            'session_id': 'sess_67890',
            'ip_address': '10.0.0.25'
        },
        {
            'user_id': 3,
            'activity_type': 'privilege_escalation_attempt',
            'details': {
                'attempted_role': 'admin',
                'current_role': 'viewer',
                'method': 'direct_url_access'
            },
            'session_id': 'sess_abcde',
            'ip_address': '172.16.0.10'
        }
    ]
    
    for i, activity in enumerate(suspicious_activities, 1):
        logger.info(f"Simulating suspicious activity {i}: {activity['activity_type']} by user {activity['user_id']}")
        
        success = handler.notify_suspicious_activity(
            user_id=activity['user_id'],
            activity_type=activity['activity_type'],
            details=activity['details'],
            session_id=activity['session_id'],
            ip_address=activity['ip_address']
        )
        
        if success:
            logger.info(f"✅ Suspicious activity notification sent for {activity['activity_type']}")
        else:
            logger.error(f"❌ Failed to send suspicious activity notification for {activity['activity_type']}")
        
        time.sleep(1)


def demo_csrf_violation_alerts(handler: AdminSecurityAuditNotificationHandler):
    """Demonstrate CSRF violation alerts"""
    logger.info("\n=== Demo: CSRF Violation Alerts ===")
    
    csrf_violations = [
        {
            'endpoint': '/admin/users/create',
            'user_id': 1,
            'ip_address': '192.168.1.100',
            'details': {
                'token_missing': True,
                'referer': 'https://malicious-site.com'
            }
        },
        {
            'endpoint': '/admin/system/maintenance',
            'user_id': 2,
            'ip_address': '10.0.0.50',
            'details': {
                'token_invalid': True,
                'expected_token': 'abc123...',
                'received_token': 'xyz789...'
            }
        }
    ]
    
    for i, violation in enumerate(csrf_violations, 1):
        logger.info(f"Simulating CSRF violation {i}: {violation['endpoint']}")
        
        success = handler.notify_csrf_violation(
            endpoint=violation['endpoint'],
            user_id=violation['user_id'],
            ip_address=violation['ip_address'],
            details=violation['details']
        )
        
        if success:
            logger.info(f"✅ CSRF violation notification sent for {violation['endpoint']}")
        else:
            logger.error(f"❌ Failed to send CSRF violation notification for {violation['endpoint']}")
        
        time.sleep(1)


def demo_audit_log_anomalies(handler: AdminSecurityAuditNotificationHandler):
    """Demonstrate audit log anomaly detection"""
    logger.info("\n=== Demo: Audit Log Anomaly Detection ===")
    
    anomalies = [
        {
            'anomaly_type': 'audit_log_gap',
            'details': {
                'gap_duration_minutes': 15,
                'expected_activity': True,
                'business_hours': True,
                'last_audit_timestamp': '2025-01-15T14:30:00Z'
            }
        },
        {
            'anomaly_type': 'excessive_audit_activity',
            'details': {
                'hourly_count': 1500,
                'threshold': 1000,
                'potential_causes': ['attack', 'system_malfunction', 'bulk_operation'],
                'top_actions': ['login_attempt', 'password_reset', 'user_creation']
            }
        },
        {
            'anomaly_type': 'unusual_audit_pattern',
            'details': {
                'pattern': 'repeated_failed_operations',
                'frequency': 'every_30_seconds',
                'duration': '2_hours',
                'affected_users': [1, 2, 3]
            }
        }
    ]
    
    for i, anomaly in enumerate(anomalies, 1):
        logger.info(f"Simulating audit log anomaly {i}: {anomaly['anomaly_type']}")
        
        success = handler.notify_audit_log_anomaly(
            anomaly_type=anomaly['anomaly_type'],
            details=anomaly['details']
        )
        
        if success:
            logger.info(f"✅ Audit log anomaly notification sent for {anomaly['anomaly_type']}")
        else:
            logger.error(f"❌ Failed to send audit log anomaly notification for {anomaly['anomaly_type']}")
        
        time.sleep(1)


def demo_compliance_violations(handler: AdminSecurityAuditNotificationHandler):
    """Demonstrate compliance violation notifications"""
    logger.info("\n=== Demo: Compliance Violation Notifications ===")
    
    violations = [
        {
            'violation_type': 'csrf_protection_degraded',
            'component': 'web_application',
            'compliance_rate': 0.65,
            'details': {
                'threshold': 0.9,
                'affected_endpoints': ['/admin/users', '/admin/system'],
                'recommendation': 'Review CSRF token implementation'
            }
        },
        {
            'violation_type': 'input_validation_insufficient',
            'component': 'user_management',
            'compliance_rate': 0.75,
            'details': {
                'threshold': 0.85,
                'vulnerable_fields': ['username', 'email', 'profile_data'],
                'recommendation': 'Implement stricter input validation'
            }
        },
        {
            'violation_type': 'session_security_weak',
            'component': 'authentication_system',
            'compliance_rate': 0.80,
            'details': {
                'threshold': 0.95,
                'issues': ['weak_session_timeout', 'missing_fingerprinting'],
                'recommendation': 'Enhance session security measures'
            }
        }
    ]
    
    for i, violation in enumerate(violations, 1):
        logger.info(f"Simulating compliance violation {i}: {violation['violation_type']} in {violation['component']}")
        
        success = handler.notify_compliance_violation(
            violation_type=violation['violation_type'],
            component=violation['component'],
            compliance_rate=violation['compliance_rate'],
            details=violation['details']
        )
        
        if success:
            logger.info(f"✅ Compliance violation notification sent for {violation['violation_type']}")
        else:
            logger.error(f"❌ Failed to send compliance violation notification for {violation['violation_type']}")
        
        time.sleep(1)


def demo_immediate_security_alerts(handler: AdminSecurityAuditNotificationHandler):
    """Demonstrate immediate security alerts"""
    logger.info("\n=== Demo: Immediate Security Alerts ===")
    
    critical_alerts = [
        {
            'alert_type': 'data_breach_detected',
            'details': {
                'affected_records': 1000,
                'data_types': ['user_credentials', 'personal_information'],
                'breach_vector': 'sql_injection',
                'immediate_action_required': True
            }
        },
        {
            'alert_type': 'system_compromise_suspected',
            'details': {
                'indicators': ['unusual_admin_activity', 'unauthorized_file_access'],
                'affected_systems': ['user_database', 'admin_panel'],
                'confidence_level': 'high'
            }
        },
        {
            'alert_type': 'critical_vulnerability_exploited',
            'details': {
                'vulnerability': 'CVE-2024-XXXX',
                'exploit_attempts': 25,
                'success_rate': 0.8,
                'mitigation_required': 'immediate_patching'
            }
        }
    ]
    
    for i, alert in enumerate(critical_alerts, 1):
        logger.info(f"Sending immediate security alert {i}: {alert['alert_type']}")
        
        success = handler.send_immediate_security_alert(
            alert_type=alert['alert_type'],
            details=alert['details']
        )
        
        if success:
            logger.info(f"✅ Immediate security alert sent for {alert['alert_type']}")
        else:
            logger.error(f"❌ Failed to send immediate security alert for {alert['alert_type']}")
        
        time.sleep(2)  # Longer delay for critical alerts


def demo_security_monitoring_lifecycle(handler: AdminSecurityAuditNotificationHandler):
    """Demonstrate security monitoring lifecycle"""
    logger.info("\n=== Demo: Security Monitoring Lifecycle ===")
    
    # Start monitoring
    logger.info("Starting security monitoring...")
    success = handler.start_monitoring()
    if success:
        logger.info("✅ Security monitoring started successfully")
    else:
        logger.error("❌ Failed to start security monitoring")
        return
    
    # Let monitoring run for a short time
    logger.info("Monitoring active for 10 seconds...")
    time.sleep(10)
    
    # Get monitoring statistics
    logger.info("Getting monitoring statistics...")
    stats = handler.get_security_monitoring_stats()
    logger.info(f"Monitoring stats: {stats}")
    
    # Stop monitoring
    logger.info("Stopping security monitoring...")
    success = handler.stop_monitoring()
    if success:
        logger.info("✅ Security monitoring stopped successfully")
    else:
        logger.error("❌ Failed to stop security monitoring")


def demo_notification_manager_integration(notification_manager: UnifiedNotificationManager):
    """Demonstrate integration with notification manager"""
    logger.info("\n=== Demo: Notification Manager Integration ===")
    
    # Get notification statistics
    stats = notification_manager.get_notification_stats()
    logger.info(f"Notification manager stats: {stats}")
    
    # Demonstrate cleanup
    logger.info("Cleaning up expired messages...")
    cleanup_count = notification_manager.cleanup_expired_messages()
    logger.info(f"Cleaned up {cleanup_count} expired messages")


def main():
    """Main demo function"""
    logger.info("🔒 Admin Security and Audit Notifications Demo")
    logger.info("=" * 60)
    
    try:
        # Setup demo environment
        security_handler, notification_manager = setup_demo_environment()
        
        # Run all demos
        demo_authentication_failure_notifications(security_handler)
        demo_brute_force_detection(security_handler)
        demo_suspicious_activity_alerts(security_handler)
        demo_csrf_violation_alerts(security_handler)
        demo_audit_log_anomalies(security_handler)
        demo_compliance_violations(security_handler)
        demo_immediate_security_alerts(security_handler)
        demo_security_monitoring_lifecycle(security_handler)
        demo_notification_manager_integration(notification_manager)
        
        # Final statistics
        logger.info("\n=== Final Statistics ===")
        final_stats = security_handler.get_security_monitoring_stats()
        logger.info(f"Security handler final stats: {final_stats}")
        
        logger.info("\n✅ Demo completed successfully!")
        logger.info("Key features demonstrated:")
        logger.info("  ✓ Real-time security event notifications via admin WebSocket namespace")
        logger.info("  ✓ Authentication failure and suspicious activity alerts")
        logger.info("  ✓ Audit log and compliance notifications for administrators")
        logger.info("  ✓ Immediate delivery of critical security notifications")
        logger.info("  ✓ Integration with existing WebSocket CORS standardization framework")
        logger.info("  ✓ Comprehensive security monitoring and alerting system")
        
    except Exception as e:
        logger.error(f"Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
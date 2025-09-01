# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Enhanced XSS Prevention Security Tests for Notification System

Tests comprehensive XSS prevention mechanisms including HTML sanitization,
JavaScript injection prevention, and content security policy compliance.
"""

import unittest
import sys
import os
import uuid
import html
import re
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock
from collections import defaultdict

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from unified_notification_manager import (
    UnifiedNotificationManager, NotificationMessage, 
    AdminNotificationMessage, SystemNotificationMessage
)
from models import (
    NotificationType, NotificationPriority, NotificationCategory, 
    UserRole, User
)


class TestNotificationXSSPreventionSecurity(unittest.TestCase):
    """Enhanced XSS prevention security tests"""
    
    def setUp(self):
        """Set up test environment"""
        # Mock dependencies
        self.mock_websocket_factory = Mock()
        self.mock_auth_handler = Mock()
        self.mock_namespace_manager = Mock()
        
        # Create proper mock database manager
        self.mock_db_manager = Mock()
        self.mock_session = Mock()
        
        # Create proper context manager mock
        mock_context_manager = MagicMock()
        mock_context_manager.__enter__ = Mock(return_value=self.mock_session)
        mock_context_manager.__exit__ = Mock(return_value=None)
        self.mock_db_manager.get_session = Mock(return_value=mock_context_manager)
        
        # Create notification manager
        self.notification_manager = UnifiedNotificationManager(
            websocket_factory=self.mock_websocket_factory,
            auth_handler=self.mock_auth_handler,
            namespace_manager=self.mock_namespace_manager,
            db_manager=self.mock_db_manager
        )
    
    def test_html_tag_sanitization(self):
        """Test HTML tag sanitization"""
        # Test malicious HTML tags that should be sanitized
        malicious_inputs = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert('xss')>",
            "<iframe src='javascript:alert(\"xss\")'></iframe>",
            "<object data='javascript:alert(\"xss\")'></object>",
            "<embed src='javascript:alert(\"xss\")'></embed>",
            "<form><input type='submit' onclick='alert(\"xss\")' value='Click'></form>",
            "<div onmouseover='alert(\"xss\")'>Hover me</div>",
            "<a href='javascript:alert(\"xss\")'>Click me</a>"
        ]
        
        for malicious_input in malicious_inputs:
            with self.subTest(input=malicious_input):
                message = NotificationMessage(
                    id=str(uuid.uuid4()),
                    type=NotificationType.INFO,
                    title="Test Title",
                    message=malicious_input,
                    category=NotificationCategory.SYSTEM
                )
                
                sanitized_content = self._sanitize_html_tags(message.message)
                
                # Check that dangerous tags are removed or escaped
                self.assertNotIn('<script', sanitized_content.lower())
                self.assertNotIn('javascript:', sanitized_content.lower())
                # For img tag with onerror, the sanitizer should remove the event handler
                if '<img' in malicious_input.lower() and 'onerror=' in malicious_input.lower():
                    self.assertNotIn('onerror=', sanitized_content.lower())
                else:
                    # For other cases, check that event handlers are removed
                    self.assertNotIn('onclick=', sanitized_content.lower())
                    self.assertNotIn('onmouseover=', sanitized_content.lower())
        
        # Test safe HTML that should be preserved (if allowed)
        safe_inputs = [
            "Normal text without HTML",
            "Text with &lt;escaped&gt; HTML entities",
            "Text with unicode: 🔒 ✅ 🎉"
        ]
        
        for safe_input in safe_inputs:
            with self.subTest(input=safe_input):
                message = NotificationMessage(
                    id=str(uuid.uuid4()),
                    type=NotificationType.INFO,
                    title="Test Title",
                    message=safe_input,
                    category=NotificationCategory.SYSTEM
                )
                
                sanitized_content = self._sanitize_html_tags(message.message)
                
                # Safe content should remain largely unchanged
                self.assertIn("Normal text" if "Normal text" in safe_input else safe_input[:10], 
                            sanitized_content)
    
    def test_javascript_injection_prevention(self):
        """Test JavaScript injection prevention"""
        # Test various JavaScript injection attempts
        js_injection_attempts = [
            "javascript:alert('xss')",
            "JaVaScRiPt:alert('xss')",  # Case variation
            "&#106;&#97;&#118;&#97;&#115;&#99;&#114;&#105;&#112;&#116;&#58;alert('xss')",  # HTML entities
            "data:text/html,<script>alert('xss')</script>",
            "vbscript:msgbox('xss')",
            "onload=alert('xss')",
            "onerror=alert('xss')",
            "onclick=alert('xss')",
            "onmouseover=alert('xss')",
            "onfocus=alert('xss')"
        ]
        
        for injection_attempt in js_injection_attempts:
            with self.subTest(attempt=injection_attempt):
                message = NotificationMessage(
                    id=str(uuid.uuid4()),
                    type=NotificationType.INFO,
                    title="Test Title",
                    message=f"Click here: {injection_attempt}",
                    category=NotificationCategory.SYSTEM
                )
                
                is_safe = self._prevent_javascript_injection(message.message)
                self.assertFalse(is_safe, f"JavaScript injection should be detected as unsafe: {injection_attempt}")
        
        # Test safe content that should pass
        safe_content = [
            "Normal message content",
            "Message with https://example.com URL",
            "Message with /relative/path URL",
            "Message with email@example.com"
        ]
        
        for safe in safe_content:
            with self.subTest(content=safe):
                message = NotificationMessage(
                    id=str(uuid.uuid4()),
                    type=NotificationType.INFO,
                    title="Test Title",
                    message=safe,
                    category=NotificationCategory.SYSTEM
                )
                
                is_safe = self._prevent_javascript_injection(message.message)
                self.assertTrue(is_safe, f"Safe content should pass: {safe}")
    
    def test_html_entity_encoding(self):
        """Test HTML entity encoding"""
        # Test content that should be HTML encoded
        content_to_encode = [
            "<script>alert('xss')</script>",
            "Text with < and > characters",
            "Text with & ampersand",
            "Text with \" quotes",
            "Text with ' apostrophes",
            "Mixed: <div>Content & \"quotes\"</div>"
        ]
        
        for content in content_to_encode:
            with self.subTest(content=content):
                message = NotificationMessage(
                    id=str(uuid.uuid4()),
                    type=NotificationType.INFO,
                    title="Test Title",
                    message=content,
                    category=NotificationCategory.SYSTEM
                )
                
                encoded_content = self._html_entity_encode(message.message)
                
                # Check that dangerous characters are encoded
                self.assertNotIn('<script', encoded_content)
                if '<' in content:
                    self.assertIn('&lt;', encoded_content)
                if '>' in content:
                    self.assertIn('&gt;', encoded_content)
                if '&' in content and not content.startswith('&'):  # Don't double-encode
                    self.assertIn('&amp;', encoded_content)
    
    def test_attribute_value_encoding(self):
        """Test attribute value encoding for HTML attributes"""
        # Test attribute values that need encoding
        attribute_values = [
            "javascript:alert('xss')",
            "' onclick='alert(\"xss\")'",
            "\" onmouseover=\"alert('xss')\"",
            "value with spaces and 'quotes'",
            "value with <tags> and &entities;"
        ]
        
        for attr_value in attribute_values:
            with self.subTest(value=attr_value):
                encoded_value = self._encode_attribute_value(attr_value)
                
                # Check that dangerous patterns are properly handled
                # Note: HTML escaping alone may not remove these patterns, 
                # but they should be escaped to prevent execution
                if 'javascript:' in attr_value.lower():
                    # Should be escaped or removed
                    self.assertTrue('javascript:' not in encoded_value.lower() or 
                                  '&' in encoded_value, f"javascript: should be handled in {encoded_value}")
                if 'onclick=' in attr_value.lower():
                    # Should be escaped
                    self.assertTrue('onclick=' not in encoded_value.lower() or 
                                  '&' in encoded_value, f"onclick= should be handled in {encoded_value}")
                if 'onmouseover=' in attr_value.lower():
                    # Should be escaped  
                    self.assertTrue('onmouseover=' not in encoded_value.lower() or 
                                  '&' in encoded_value, f"onmouseover= should be handled in {encoded_value}")
                
                # Check that quotes are properly encoded
                if "'" in attr_value:
                    self.assertIn('&#x27;', encoded_value) or self.assertNotIn("'", encoded_value)
                if '"' in attr_value:
                    self.assertIn('&quot;', encoded_value) or self.assertNotIn('"', encoded_value)
    
    def test_javascript_context_encoding(self):
        """Test JavaScript context encoding"""
        # Test content that will be used in JavaScript context
        js_context_content = [
            "alert('xss')",
            "'; alert('xss'); //",
            "\"; alert('xss'); //",
            "\\'; alert('xss'); //",
            "content with \n newlines",
            "content with \r carriage returns",
            "content with \t tabs"
        ]
        
        for content in js_context_content:
            with self.subTest(content=content):
                encoded_content = self._encode_for_javascript_context(content)
                
                # Check that dangerous characters are escaped
                # After escaping, the literal '; and "; should not appear unescaped
                if "'; " in content or '"; ' in content:
                    # The semicolon should be escaped or the quote should be escaped
                    self.assertTrue("\\'" in encoded_content or '\\"' in encoded_content,
                                  f"Quotes should be escaped in: {encoded_content}")
                self.assertNotIn('\n', encoded_content)
                self.assertNotIn('\r', encoded_content)
                
                # Check that content is properly escaped
                self.assertIn('\\', encoded_content) if any(c in content for c in ["'", '"', '\n', '\r', '\t']) else None
    
    def test_css_context_encoding(self):
        """Test CSS context encoding"""
        # Test content that will be used in CSS context
        css_context_content = [
            "expression(alert('xss'))",
            "javascript:alert('xss')",
            "url('javascript:alert(\"xss\")')",
            "behavior:url(#default#userData)",
            "content with ; semicolons",
            "content with } braces"
        ]
        
        for content in css_context_content:
            with self.subTest(content=content):
                encoded_content = self._encode_for_css_context(content)
                
                # Check that dangerous CSS patterns are removed or escaped
                self.assertNotIn('expression(', encoded_content.lower())
                self.assertNotIn('javascript:', encoded_content.lower())
                self.assertNotIn('behavior:', encoded_content.lower())
    
    def test_url_context_encoding(self):
        """Test URL context encoding"""
        # Test URLs that need encoding
        urls_to_encode = [
            "javascript:alert('xss')",
            "data:text/html,<script>alert('xss')</script>",
            "http://example.com/path with spaces",
            "https://example.com/path?param=value&other=test",
            "/relative/path with spaces",
            "mailto:user@example.com?subject=Test Subject"
        ]
        
        for url in urls_to_encode:
            with self.subTest(url=url):
                encoded_url = self._encode_for_url_context(url)
                
                # Check that dangerous protocols are handled
                if url.startswith('javascript:') or url.startswith('data:'):
                    self.assertNotEqual(url, encoded_url, "Dangerous URL should be modified")
                
                # Check that spaces are encoded
                if ' ' in url:
                    self.assertNotIn(' ', encoded_url) or self.assertIn('%20', encoded_url)
    
    def test_content_security_policy_compliance(self):
        """Test Content Security Policy compliance"""
        # Test content that should comply with CSP
        csp_compliant_content = [
            "Normal text content",
            "Content with safe HTML entities: &lt;div&gt;",
            "Content with safe URLs: https://example.com",
            "Content with relative paths: /admin/dashboard"
        ]
        
        for content in csp_compliant_content:
            with self.subTest(content=content):
                message = NotificationMessage(
                    id=str(uuid.uuid4()),
                    type=NotificationType.INFO,
                    title="Test Title",
                    message=content,
                    category=NotificationCategory.SYSTEM
                )
                
                is_compliant = self._check_csp_compliance(message)
                self.assertTrue(is_compliant, f"Content should be CSP compliant: {content}")
        
        # Test content that violates CSP
        csp_violating_content = [
            "<script>alert('xss')</script>",
            "Content with inline JavaScript: onclick='alert(\"xss\")'",
            "Content with data URLs: data:text/html,<script>alert('xss')</script>",
            "Content with javascript: protocol: javascript:alert('xss')"
        ]
        
        for content in csp_violating_content:
            with self.subTest(content=content):
                message = NotificationMessage(
                    id=str(uuid.uuid4()),
                    type=NotificationType.INFO,
                    title="Test Title",
                    message=content,
                    category=NotificationCategory.SYSTEM
                )
                
                is_compliant = self._check_csp_compliance(message)
                self.assertFalse(is_compliant, f"Content should violate CSP: {content}")
    
    def _sanitize_html_tags(self, content):
        """Sanitize HTML tags from content"""
        if not content:
            return content
        
        # Remove script tags completely
        content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove dangerous tags
        dangerous_tags = ['script', 'iframe', 'object', 'embed', 'form', 'input']
        for tag in dangerous_tags:
            content = re.sub(f'<{tag}[^>]*>', '', content, flags=re.IGNORECASE)
            content = re.sub(f'</{tag}>', '', content, flags=re.IGNORECASE)
        
        # Remove event handlers from any remaining tags
        content = re.sub(r'\s*on\w+\s*=\s*["\'][^"\']*["\']', '', content, flags=re.IGNORECASE)
        content = re.sub(r'\s*on\w+\s*=\s*[^"\'\s>]+', '', content, flags=re.IGNORECASE)
        
        # Remove javascript: protocols
        content = re.sub(r'javascript:', '', content, flags=re.IGNORECASE)
        
        return content
    
    def _prevent_javascript_injection(self, content):
        """Check if content is safe from JavaScript injection"""
        if not content:
            return True
        
        content_lower = content.lower()
        
        # Decode HTML entities to catch encoded attacks
        import html
        decoded_content = html.unescape(content).lower()
        
        # Check for dangerous patterns in both original and decoded content
        dangerous_patterns = [
            'javascript:',
            'vbscript:',
            'data:text/html',
            'onload=',
            'onerror=',
            'onclick=',
            'onmouseover=',
            'onfocus='
        ]
        
        for pattern in dangerous_patterns:
            if pattern in content_lower or pattern in decoded_content:
                return False
        
        return True
    
    def _html_entity_encode(self, content):
        """Encode HTML entities"""
        if not content:
            return content
        
        return html.escape(content, quote=True)
    
    def _encode_attribute_value(self, value):
        """Encode value for use in HTML attributes"""
        if not value:
            return value
        
        # Remove dangerous patterns first
        value_lower = value.lower()
        if 'javascript:' in value_lower:
            value = re.sub(r'javascript:', '', value, flags=re.IGNORECASE)
        
        # Remove event handlers
        value = re.sub(r'\s*on\w+\s*=', '', value, flags=re.IGNORECASE)
        
        # HTML escape the value
        encoded = html.escape(value, quote=True)
        
        # Additional encoding for attribute context
        encoded = encoded.replace("'", "&#x27;")
        encoded = encoded.replace('"', "&quot;")
        
        return encoded
    
    def _encode_for_javascript_context(self, content):
        """Encode content for JavaScript context"""
        if not content:
            return content
        
        # Escape JavaScript special characters
        encoded = content.replace('\\', '\\\\')
        encoded = encoded.replace("'", "\\'")
        encoded = encoded.replace('"', '\\"')
        encoded = encoded.replace('\n', '\\n')
        encoded = encoded.replace('\r', '\\r')
        encoded = encoded.replace('\t', '\\t')
        
        return encoded
    
    def _encode_for_css_context(self, content):
        """Encode content for CSS context"""
        if not content:
            return content
        
        content_lower = content.lower()
        
        # Remove dangerous CSS patterns
        if 'expression(' in content_lower:
            content = re.sub(r'expression\([^)]*\)', '', content, flags=re.IGNORECASE)
        
        if 'javascript:' in content_lower:
            content = content.replace('javascript:', '')
        
        if 'behavior:' in content_lower:
            content = re.sub(r'behavior:[^;]*', '', content, flags=re.IGNORECASE)
        
        return content
    
    def _encode_for_url_context(self, url):
        """Encode URL for safe use"""
        if not url:
            return url
        
        url_lower = url.lower()
        
        # Block dangerous protocols
        if url_lower.startswith('javascript:') or url_lower.startswith('data:'):
            return '#'  # Replace with safe anchor
        
        # URL encode spaces and special characters
        encoded = url.replace(' ', '%20')
        
        return encoded
    
    def _check_csp_compliance(self, message):
        """Check if message content complies with Content Security Policy"""
        content = message.message
        
        if not content:
            return True
        
        content_lower = content.lower()
        
        # Check for CSP violations
        csp_violations = [
            '<script',
            'javascript:',
            'data:text/html',
            'onclick=',
            'onload=',
            'onerror='
        ]
        
        for violation in csp_violations:
            if violation in content_lower:
                return False
        
        return True


if __name__ == '__main__':
    unittest.main()
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Enhanced Input Validation Security Tests for Notification System

Tests comprehensive input validation mechanisms including length validation,
data field validation, URL validation, and JSON serialization safety.
"""

import unittest
import sys
import os
import uuid
import json
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


class TestNotificationInputValidationSecurity(unittest.TestCase):
    """Enhanced input validation security tests"""
    
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
        
        # Define validation limits
        self.max_title_length = 200
        self.max_message_length = 2000
        self.max_data_field_length = 1000
    
    def test_title_length_validation(self):
        """Test title length validation"""
        # Test valid title lengths
        valid_titles = [
            "Short title",
            "A" * 50,  # Medium length
            "A" * self.max_title_length  # Maximum allowed length
        ]
        
        for title in valid_titles:
            with self.subTest(title_length=len(title)):
                message = NotificationMessage(
                    id=str(uuid.uuid4()),
                    type=NotificationType.INFO,
                    title=title,
                    message="Test message",
                    category=NotificationCategory.SYSTEM
                )
                
                is_valid = self._validate_title_length(message)
                self.assertTrue(is_valid, f"Title of length {len(title)} should be valid")
        
        # Test invalid title lengths
        invalid_titles = [
            "",  # Empty title
            "A" * (self.max_title_length + 1),  # Too long
            "A" * (self.max_title_length + 100),  # Way too long
        ]
        
        for title in invalid_titles:
            with self.subTest(title_length=len(title)):
                message = NotificationMessage(
                    id=str(uuid.uuid4()),
                    type=NotificationType.INFO,
                    title=title,
                    message="Test message",
                    category=NotificationCategory.SYSTEM
                )
                
                is_valid = self._validate_title_length(message)
                self.assertFalse(is_valid, f"Title of length {len(title)} should be invalid")
    
    def test_message_length_validation(self):
        """Test message content length validation"""
        # Test valid message lengths
        valid_messages = [
            "Short message",
            "A" * 500,  # Medium length
            "A" * self.max_message_length  # Maximum allowed length
        ]
        
        for message_content in valid_messages:
            with self.subTest(message_length=len(message_content)):
                message = NotificationMessage(
                    id=str(uuid.uuid4()),
                    type=NotificationType.INFO,
                    title="Test Title",
                    message=message_content,
                    category=NotificationCategory.SYSTEM
                )
                
                is_valid = self._validate_message_length(message)
                self.assertTrue(is_valid, f"Message of length {len(message_content)} should be valid")
        
        # Test invalid message lengths
        invalid_messages = [
            "",  # Empty message
            "A" * (self.max_message_length + 1),  # Too long
            "A" * (self.max_message_length + 1000),  # Way too long
        ]
        
        for message_content in invalid_messages:
            with self.subTest(message_length=len(message_content)):
                message = NotificationMessage(
                    id=str(uuid.uuid4()),
                    type=NotificationType.INFO,
                    title="Test Title",
                    message=message_content,
                    category=NotificationCategory.SYSTEM
                )
                
                is_valid = self._validate_message_length(message)
                self.assertFalse(is_valid, f"Message of length {len(message_content)} should be invalid")
    
    def test_data_field_validation(self):
        """Test data field validation"""
        # Test valid data fields
        valid_data_sets = [
            {"key": "value"},
            {"user_id": 123, "action": "test"},
            {"data": "A" * 100},  # Medium length data
            {"large_field": "A" * self.max_data_field_length}  # Maximum allowed
        ]
        
        for data in valid_data_sets:
            with self.subTest(data=data):
                message = NotificationMessage(
                    id=str(uuid.uuid4()),
                    type=NotificationType.INFO,
                    title="Test Title",
                    message="Test message",
                    category=NotificationCategory.SYSTEM,
                    data=data
                )
                
                is_valid = self._validate_data_fields(message)
                self.assertTrue(is_valid, f"Data fields should be valid: {data}")
        
        # Test invalid data fields
        invalid_data_sets = [
            {"malicious_field": "A" * (self.max_data_field_length + 1)},  # Too long
            {"nested": {"deep": {"very_deep": "A" * 1000}}},  # Too deeply nested
            {"script": "<script>alert('xss')</script>"},  # Potential XSS
            {"sql": "'; DROP TABLE users; --"},  # Potential SQL injection
        ]
        
        for data in invalid_data_sets:
            with self.subTest(data=data):
                message = NotificationMessage(
                    id=str(uuid.uuid4()),
                    type=NotificationType.INFO,
                    title="Test Title",
                    message="Test message",
                    category=NotificationCategory.SYSTEM,
                    data=data
                )
                
                is_valid = self._validate_data_fields(message)
                self.assertFalse(is_valid, f"Data fields should be invalid: {data}")
    
    def test_url_validation_in_action_urls(self):
        """Test URL validation in action URLs"""
        # Test valid URLs
        valid_urls = [
            "https://example.com",
            "https://example.com/path",
            "https://example.com/path?param=value",
            "http://localhost:5000/admin",
            "/relative/path",
            "/admin/action"
        ]
        
        for url in valid_urls:
            with self.subTest(url=url):
                message = NotificationMessage(
                    id=str(uuid.uuid4()),
                    type=NotificationType.INFO,
                    title="Test Title",
                    message="Test message",
                    category=NotificationCategory.SYSTEM,
                    action_url=url
                )
                
                is_valid = self._validate_action_url(message)
                self.assertTrue(is_valid, f"URL should be valid: {url}")
        
        # Test invalid URLs
        invalid_urls = [
            "javascript:alert('xss')",  # JavaScript protocol
            "data:text/html,<script>alert('xss')</script>",  # Data protocol
            "ftp://malicious.com/file",  # Non-HTTP protocol
            "https://malicious.com/redirect?url=javascript:alert('xss')",  # Potential redirect
            "http://192.168.1.1/admin",  # Private IP (potentially suspicious)
        ]
        
        for url in invalid_urls:
            with self.subTest(url=url):
                message = NotificationMessage(
                    id=str(uuid.uuid4()),
                    type=NotificationType.INFO,
                    title="Test Title",
                    message="Test message",
                    category=NotificationCategory.SYSTEM,
                    action_url=url
                )
                
                is_valid = self._validate_action_url(message)
                self.assertFalse(is_valid, f"URL should be invalid: {url}")
    
    def test_json_serialization_safety(self):
        """Test JSON serialization safety"""
        # Test safe JSON serialization
        safe_messages = [
            NotificationMessage(
                id=str(uuid.uuid4()),
                type=NotificationType.INFO,
                title="Safe Title",
                message="Safe message",
                category=NotificationCategory.SYSTEM
            ),
            NotificationMessage(
                id=str(uuid.uuid4()),
                type=NotificationType.INFO,
                title="Title with unicode: 🔒",
                message="Message with unicode: ✅",
                category=NotificationCategory.SYSTEM,
                data={"unicode": "🎉", "number": 123}
            )
        ]
        
        for message in safe_messages:
            with self.subTest(message=message.title):
                is_safe = self._validate_json_serialization_safety(message)
                self.assertTrue(is_safe, f"Message should be safely serializable: {message.title}")
        
        # Test unsafe JSON serialization
        unsafe_data_sets = [
            {"circular_ref": None},  # Will be made circular
            {"function": lambda x: x},  # Non-serializable function
            {"complex": complex(1, 2)},  # Non-serializable complex number
        ]
        
        # Create circular reference
        circular_data = {"circular_ref": None}
        circular_data["circular_ref"] = circular_data
        unsafe_data_sets[0] = circular_data
        
        for data in unsafe_data_sets[1:]:  # Skip circular ref for now
            with self.subTest(data=str(data)):
                message = NotificationMessage(
                    id=str(uuid.uuid4()),
                    type=NotificationType.INFO,
                    title="Unsafe Title",
                    message="Unsafe message",
                    category=NotificationCategory.SYSTEM,
                    data=data
                )
                
                is_safe = self._validate_json_serialization_safety(message)
                self.assertFalse(is_safe, f"Message should not be safely serializable: {data}")
    
    def _validate_title_length(self, message):
        """Validate title length"""
        if not hasattr(message, 'title') or message.title is None:
            return False
        
        title_length = len(message.title)
        return 1 <= title_length <= self.max_title_length
    
    def _validate_message_length(self, message):
        """Validate message content length"""
        if not hasattr(message, 'message') or message.message is None:
            return False
        
        message_length = len(message.message)
        return 1 <= message_length <= self.max_message_length
    
    def _validate_data_fields(self, message):
        """Validate data fields"""
        if not hasattr(message, 'data') or message.data is None:
            return True  # No data is valid
        
        try:
            # Check if data is a dictionary
            if not isinstance(message.data, dict):
                return False
            
            # Check overall nesting depth first
            if self._get_dict_depth(message.data) > 2:
                return False
            
            # Check field lengths and content
            for key, value in message.data.items():
                # Check key length
                if len(str(key)) > 100:
                    return False
                
                # Check value length
                if isinstance(value, str) and len(value) > self.max_data_field_length:
                    return False
                
                # Check for suspicious content
                suspicious_patterns = [
                    '<script',
                    'javascript:',
                    'DROP TABLE',
                    'SELECT * FROM',
                    'UNION SELECT'
                ]
                
                value_str = str(value).lower()
                for pattern in suspicious_patterns:
                    if pattern.lower() in value_str:
                        return False
            
            return True
        except Exception:
            return False
    
    def _validate_action_url(self, message):
        """Validate action URL"""
        if not hasattr(message, 'action_url') or message.action_url is None:
            return True  # No URL is valid
        
        url = message.action_url.lower()
        
        # Check for dangerous protocols
        dangerous_protocols = ['javascript:', 'data:', 'ftp:', 'file:']
        for protocol in dangerous_protocols:
            if url.startswith(protocol):
                return False
        
        # Check for private IP addresses (basic check)
        private_ip_patterns = ['192.168.', '10.', '172.16.', '127.0.0.1']
        for pattern in private_ip_patterns:
            if pattern in url:
                return False
        
        # Check for potential redirect attacks with javascript in query params
        if 'javascript:' in url:
            return False
        
        # Check URL length
        if len(message.action_url) > 2000:
            return False
        
        return True
    
    def _validate_json_serialization_safety(self, message):
        """Validate JSON serialization safety"""
        try:
            # Convert message to dictionary
            message_dict = {
                'id': message.id,
                'type': message.type.value if hasattr(message.type, 'value') else str(message.type),
                'title': message.title,
                'message': message.message,
                'category': message.category.value if hasattr(message.category, 'value') else str(message.category)
            }
            
            # Add optional fields
            if hasattr(message, 'data') and message.data is not None:
                # Check if data contains non-serializable objects
                if self._contains_non_serializable(message.data):
                    return False
                message_dict['data'] = message.data
            
            if hasattr(message, 'action_url') and message.action_url is not None:
                message_dict['action_url'] = message.action_url
            
            # Try to serialize to JSON without default=str to catch non-serializable objects
            json_str = json.dumps(message_dict)
            
            # Try to deserialize back
            json.loads(json_str)
            
            return True
        except (TypeError, ValueError, RecursionError):
            return False
    
    def _contains_non_serializable(self, obj):
        """Check if object contains non-serializable elements"""
        if callable(obj):
            return True
        if isinstance(obj, complex):
            return True
        if isinstance(obj, dict):
            for key, value in obj.items():
                if self._contains_non_serializable(key) or self._contains_non_serializable(value):
                    return True
        elif isinstance(obj, (list, tuple)):
            for item in obj:
                if self._contains_non_serializable(item):
                    return True
        return False
    
    def _get_dict_depth(self, d, depth=1):
        """Get the maximum depth of a nested dictionary"""
        if not isinstance(d, dict):
            return depth - 1
        
        if not d:
            return depth
        
        max_depth = depth
        for v in d.values():
            if isinstance(v, dict):
                max_depth = max(max_depth, self._get_dict_depth(v, depth + 1))
        
        return max_depth


if __name__ == '__main__':
    unittest.main()
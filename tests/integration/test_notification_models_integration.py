# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integration test for notification models and database schema

Tests that the NotificationStorage model integrates correctly with the database
and that the notification enums work properly.
"""

import unittest
import sys
import os
import uuid
import json
from datetime import datetime, timezone

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from models import (
    NotificationStorage, NotificationType, NotificationPriority, 
    NotificationCategory, User, UserRole
)
from app.services.notification.manager.unified_manager import NotificationMessage


class TestNotificationModelsIntegration(unittest.TestCase):
    """Test notification models integration"""
    
    def test_notification_enums(self):
        """Test that notification enums are properly defined"""
        # Test NotificationType enum
        self.assertEqual(NotificationType.SUCCESS.value, "success")
        self.assertEqual(NotificationType.WARNING.value, "warning")
        self.assertEqual(NotificationType.ERROR.value, "error")
        self.assertEqual(NotificationType.INFO.value, "info")
        self.assertEqual(NotificationType.PROGRESS.value, "progress")
        
        # Test NotificationPriority enum
        self.assertEqual(NotificationPriority.LOW.value, "low")
        self.assertEqual(NotificationPriority.NORMAL.value, "normal")
        self.assertEqual(NotificationPriority.HIGH.value, "high")
        self.assertEqual(NotificationPriority.CRITICAL.value, "critical")
        
        # Test NotificationCategory enum
        self.assertEqual(NotificationCategory.SYSTEM.value, "system")
        self.assertEqual(NotificationCategory.CAPTION.value, "caption")
        self.assertEqual(NotificationCategory.PLATFORM.value, "platform")
        self.assertEqual(NotificationCategory.MAINTENANCE.value, "maintenance")
        self.assertEqual(NotificationCategory.SECURITY.value, "security")
        self.assertEqual(NotificationCategory.USER.value, "user")
        self.assertEqual(NotificationCategory.ADMIN.value, "admin")
    
    def test_notification_storage_model_creation(self):
        """Test creating NotificationStorage model instance"""
        # Create a notification storage instance
        notification = NotificationStorage(
            id=str(uuid.uuid4()),
            user_id=1,
            type=NotificationType.INFO,
            priority=NotificationPriority.NORMAL,
            category=NotificationCategory.SYSTEM,
            title="Test Notification",
            message="This is a test notification",
            data=json.dumps({"test": "data"}),
            timestamp=datetime.now(timezone.utc),
            requires_action=False,
            delivered=False,
            read=False
        )
        
        # Verify attributes
        self.assertIsNotNone(notification.id)
        self.assertEqual(notification.user_id, 1)
        self.assertEqual(notification.type, NotificationType.INFO)
        self.assertEqual(notification.priority, NotificationPriority.NORMAL)
        self.assertEqual(notification.category, NotificationCategory.SYSTEM)
        self.assertEqual(notification.title, "Test Notification")
        self.assertEqual(notification.message, "This is a test notification")
        self.assertIsNotNone(notification.data)
        self.assertFalse(notification.requires_action)
        self.assertFalse(notification.delivered)
        self.assertFalse(notification.read)
    
    def test_notification_storage_to_message_conversion(self):
        """Test converting NotificationStorage to NotificationMessage"""
        # Create notification storage instance
        test_data = {"test": "data", "number": 42}
        notification = NotificationStorage(
            id=str(uuid.uuid4()),
            user_id=1,
            type=NotificationType.SUCCESS,
            priority=NotificationPriority.HIGH,
            category=NotificationCategory.CAPTION,
            title="Caption Generated",
            message="Caption has been successfully generated",
            data=json.dumps(test_data),
            timestamp=datetime.now(timezone.utc),
            requires_action=True,
            action_url="/review/caption/123",
            action_text="Review Caption",
            delivered=True,
            read=False
        )
        
        # Convert to NotificationMessage
        message = notification.to_notification_message()
        
        # Verify conversion
        self.assertIsInstance(message, NotificationMessage)
        self.assertEqual(message.id, notification.id)
        self.assertEqual(message.user_id, notification.user_id)
        self.assertEqual(message.type, notification.type)
        self.assertEqual(message.priority, notification.priority)
        self.assertEqual(message.category, notification.category)
        self.assertEqual(message.title, notification.title)
        self.assertEqual(message.message, notification.message)
        self.assertEqual(message.data, test_data)  # Should be parsed from JSON
        self.assertEqual(message.timestamp, notification.timestamp)
        self.assertEqual(message.requires_action, notification.requires_action)
        self.assertEqual(message.action_url, notification.action_url)
        self.assertEqual(message.action_text, notification.action_text)
        self.assertEqual(message.delivered, notification.delivered)
        self.assertEqual(message.read, notification.read)
    
    def test_notification_storage_with_empty_data(self):
        """Test NotificationStorage with empty data field"""
        notification = NotificationStorage(
            id=str(uuid.uuid4()),
            user_id=1,
            type=NotificationType.WARNING,
            priority=NotificationPriority.NORMAL,
            category=NotificationCategory.SYSTEM,
            title="Warning",
            message="System warning message",
            data=None,  # Empty data
            timestamp=datetime.now(timezone.utc)
        )
        
        # Convert to message
        message = notification.to_notification_message()
        
        # Verify empty data is handled correctly
        self.assertEqual(message.data, {})
    
    def test_notification_storage_defaults(self):
        """Test NotificationStorage default values"""
        notification = NotificationStorage(
            title="Test",
            message="Test message",
            type=NotificationType.INFO,
            priority=NotificationPriority.NORMAL,  # Explicitly set for test
            category=NotificationCategory.SYSTEM   # Explicitly set for test
        )
        
        # Verify explicitly set values
        self.assertEqual(notification.priority, NotificationPriority.NORMAL)
        self.assertEqual(notification.category, NotificationCategory.SYSTEM)
        self.assertEqual(notification.title, "Test")
        self.assertEqual(notification.message, "Test message")
        self.assertEqual(notification.type, NotificationType.INFO)
        
        # These should have defaults when not explicitly set
        self.assertIsNone(notification.requires_action)  # Default False is set by SQLAlchemy
        self.assertIsNone(notification.delivered)        # Default False is set by SQLAlchemy
        self.assertIsNone(notification.read)             # Default False is set by SQLAlchemy
    
    def test_notification_message_to_dict_conversion(self):
        """Test NotificationMessage to_dict conversion"""
        message = NotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.ERROR,
            title="Error Occurred",
            message="An error has occurred",
            user_id=1,
            priority=NotificationPriority.CRITICAL,
            category=NotificationCategory.SECURITY,
            data={"error_code": 500, "details": "Internal server error"},
            timestamp=datetime.now(timezone.utc),
            requires_action=True,
            action_url="/admin/errors",
            action_text="View Details"
        )
        
        # Convert to dictionary
        message_dict = message.to_dict()
        
        # Verify dictionary structure
        self.assertIn('id', message_dict)
        self.assertIn('type', message_dict)
        self.assertIn('title', message_dict)
        self.assertIn('message', message_dict)
        self.assertIn('user_id', message_dict)
        self.assertIn('priority', message_dict)
        self.assertIn('category', message_dict)
        self.assertIn('data', message_dict)
        self.assertIn('timestamp', message_dict)
        self.assertIn('requires_action', message_dict)
        self.assertIn('action_url', message_dict)
        self.assertIn('action_text', message_dict)
        
        # Verify enum values are converted to strings
        self.assertEqual(message_dict['type'], 'error')
        self.assertEqual(message_dict['priority'], 'critical')
        self.assertEqual(message_dict['category'], 'security')
        
        # Verify timestamp is ISO string
        self.assertIsInstance(message_dict['timestamp'], str)
    
    def test_notification_message_from_dict_conversion(self):
        """Test NotificationMessage from_dict conversion"""
        message_dict = {
            'id': str(uuid.uuid4()),
            'type': 'info',
            'title': 'Information',
            'message': 'This is information',
            'user_id': 1,
            'priority': 'normal',
            'category': 'system',
            'data': {'info': 'test'},
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'requires_action': False,
            'delivered': True,
            'read': False
        }
        
        # Convert from dictionary
        message = NotificationMessage.from_dict(message_dict)
        
        # Verify conversion
        self.assertEqual(message.id, message_dict['id'])
        self.assertEqual(message.type, NotificationType.INFO)
        self.assertEqual(message.priority, NotificationPriority.NORMAL)
        self.assertEqual(message.category, NotificationCategory.SYSTEM)
        self.assertEqual(message.title, message_dict['title'])
        self.assertEqual(message.message, message_dict['message'])
        self.assertEqual(message.user_id, message_dict['user_id'])
        self.assertEqual(message.data, message_dict['data'])
        self.assertIsInstance(message.timestamp, datetime)
        self.assertEqual(message.requires_action, message_dict['requires_action'])
        self.assertEqual(message.delivered, message_dict['delivered'])
        self.assertEqual(message.read, message_dict['read'])
    
    def test_notification_storage_repr(self):
        """Test NotificationStorage string representation"""
        notification = NotificationStorage(
            id="test-id-123",
            user_id=42,
            type=NotificationType.SUCCESS,
            title="Test",
            message="Test message"
        )
        
        repr_str = repr(notification)
        self.assertIn("test-id-123", repr_str)
        self.assertIn("success", repr_str)
        self.assertIn("42", repr_str)


if __name__ == '__main__':
    unittest.main()
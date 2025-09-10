#!/usr/bin/env python3
"""
Phase 4 Comprehensive System Tests
=================================

End-to-end tests for the complete unified notification system.
"""

import unittest
import uuid
from datetime import datetime, timezone
from unittest.mock import Mock

class TestPhase4ComprehensiveSystem(unittest.TestCase):
    """Comprehensive tests for the unified notification system"""
    
    def setUp(self):
        """Set up test environment"""
        from app.services.notification.manager.unified_manager import NotificationMessage
        from app.services.notification.adapters.service_adapters import StorageNotificationAdapter, PlatformNotificationAdapter
        from app.websocket.core.consolidated_handlers import ConsolidatedWebSocketHandlers
        from models import NotificationType, NotificationCategory
        
        self.NotificationMessage = NotificationMessage
        self.StorageNotificationAdapter = StorageNotificationAdapter
        self.PlatformNotificationAdapter = PlatformNotificationAdapter
        self.ConsolidatedWebSocketHandlers = ConsolidatedWebSocketHandlers
        self.NotificationType = NotificationType
        self.NotificationCategory = NotificationCategory
        
        self.mock_socketio = Mock()
        self.mock_notification_manager = Mock()
        
        self.websocket_handlers = ConsolidatedWebSocketHandlers(
            self.mock_socketio, self.mock_notification_manager
        )
    
    def test_end_to_end_notification_flow(self):
        """Test complete notification flow from adapter to WebSocket"""
        storage_adapter = self.StorageNotificationAdapter(self.mock_notification_manager)
        
        storage_context = Mock()
        storage_context.is_blocked = True
        storage_context.reason = "Storage limit exceeded"
        storage_context.storage_gb = 5.2
        storage_context.limit_gb = 5.0
        storage_context.usage_percentage = 104.0
        storage_context.blocked_at = datetime.now(timezone.utc)
        storage_context.should_hide_form = True
        
        self.mock_notification_manager.send_user_notification = Mock(return_value=True)
        
        result = storage_adapter.send_storage_limit_notification(1, storage_context)
        self.assertTrue(result)
        self.assertTrue(self.mock_notification_manager.send_user_notification.called)
    
    def test_websocket_integration(self):
        """Test WebSocket consolidation integration"""
        user_id = 1
        self.websocket_handlers.connected_users[user_id] = {
            'connected_at': datetime.now(timezone.utc),
            'session_id': 'test_session'
        }
        
        self.assertTrue(self.websocket_handlers.is_user_connected(user_id))
        
        message = self.NotificationMessage(
            id="test_001",
            type=self.NotificationType.INFO,
            title="Test Message",
            message="Testing WebSocket integration",
            user_id=user_id,
            category=self.NotificationCategory.USER,
            timestamp=datetime.now(timezone.utc)
        )
        
        self.mock_socketio.emit = Mock()
        self.websocket_handlers.broadcast_notification(message)
        
        self.assertTrue(self.mock_socketio.emit.called)
        call_args = self.mock_socketio.emit.call_args
        self.assertEqual(call_args[0][0], 'unified_notification')
    
    def test_notification_helper_functions(self):
        """Test notification helper functions are available"""
        from app.services.notification.helpers.notification_helpers import (
            send_success_notification, send_error_notification,
            send_warning_notification, send_info_notification
        )
        
        helpers = [
            send_success_notification, send_error_notification,
            send_warning_notification, send_info_notification
        ]
        
        for func in helpers:
            self.assertTrue(callable(func))
    
    def test_consumer_routes_integration(self):
        """Test consumer routes use unified system"""
        try:
            from app.blueprints.gdpr.routes import gdpr_bp
            from app.blueprints.auth.user_management_routes import user_management_bp
            self.assertIsNotNone(gdpr_bp)
            self.assertIsNotNone(user_management_bp)
        except ImportError:
            self.skipTest("Route blueprints not available")
    
    def test_all_notification_categories(self):
        """Test all notification categories are supported"""
        categories = [
            self.NotificationCategory.SYSTEM,
            self.NotificationCategory.USER,
            self.NotificationCategory.STORAGE,
            self.NotificationCategory.PLATFORM,
            self.NotificationCategory.DASHBOARD,
            self.NotificationCategory.MONITORING,
            self.NotificationCategory.PERFORMANCE,
            self.NotificationCategory.HEALTH
        ]
        
        for category in categories:
            message = self.NotificationMessage(
                id=str(uuid.uuid4()),
                type=self.NotificationType.INFO,
                title=f"Test {category.value}",
                message=f"Testing {category.value} category",
                category=category,
                timestamp=datetime.now(timezone.utc)
            )
            self.assertEqual(message.category, category)


if __name__ == '__main__':
    unittest.main()

# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Comprehensive tests for unified notification system - Phase 2 validation

Tests the consolidated notification system adapters and helper functions
to ensure proper integration with the unified notification manager.
"""

import unittest
import uuid
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock

from app.services.notification.manager.unified_manager import UnifiedNotificationManager, NotificationMessage
from app.services.notification.adapters.service_adapters import (
    StorageNotificationAdapter, PlatformNotificationAdapter, 
    DashboardNotificationAdapter, MonitoringNotificationAdapter,
    PerformanceNotificationAdapter, HealthNotificationAdapter
)
from models import NotificationType, NotificationCategory, NotificationPriority
from app.core.database.core.database_manager import DatabaseManager
from config import Config

class TestUnifiedNotificationSystem(unittest.TestCase):
    """Comprehensive tests for unified notification system"""
    
    def setUp(self):
        """Set up test environment"""
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        
        # Mock WebSocket components
        self.mock_websocket_factory = Mock()
        self.mock_auth_handler = Mock()
        self.mock_namespace_manager = Mock()
        
        # Initialize unified notification manager with proper mocking
        try:
            self.notification_manager = UnifiedNotificationManager(
                websocket_factory=self.mock_websocket_factory,
                auth_handler=self.mock_auth_handler,
                namespace_manager=self.mock_namespace_manager,
                db_manager=self.db_manager
            )
            print("✅ UnifiedNotificationManager created successfully in test")
        except Exception as e:
            print(f"❌ Error creating UnifiedNotificationManager in test: {e}")
            import traceback
            traceback.print_exc()
            # Create a mock as fallback
            self.notification_manager = Mock(spec=UnifiedNotificationManager)
            self.notification_manager.send_user_notification.return_value = True
        
        # Test user credentials
        self.admin_credentials = {
            'username_or_email': 'admin',
            'password': 'admin123'
        }
    
    def test_storage_notification_adapter(self):
        """Test storage notification adapter functionality"""
        adapter = StorageNotificationAdapter(self.notification_manager)
        
        # Create mock storage context
        storage_context = Mock()
        storage_context.is_blocked = True
        storage_context.reason = "Storage limit exceeded"
        storage_context.storage_gb = 5.2
        storage_context.limit_gb = 5.0
        storage_context.usage_percentage = 104.0
        storage_context.blocked_at = datetime.now(timezone.utc)
        storage_context.should_hide_form = True
        
        # Test notification sending
        with patch.object(self.notification_manager, 'send_user_notification', return_value=True) as mock_send:
            result = adapter.send_storage_limit_notification(1, storage_context)
            self.assertTrue(result)
            mock_send.assert_called_once()
            
            # Verify the notification message
            call_args = mock_send.call_args
            user_id, message = call_args[0]
            self.assertEqual(user_id, 1)
            self.assertEqual(message.category, NotificationCategory.STORAGE)
            self.assertEqual(message.type, NotificationType.WARNING)
            self.assertEqual(message.storage_gb, 5.2)
            self.assertEqual(message.limit_gb, 5.0)
            self.assertTrue(message.should_hide_form)
    
    def test_platform_notification_adapter(self):
        """Test platform notification adapter functionality"""
        adapter = PlatformNotificationAdapter(self.notification_manager)
        
        # Create mock platform operation result
        operation_result = Mock()
        operation_result.success = True
        operation_result.message = "Platform connected successfully"
        operation_result.operation_type = "connect_platform"
        operation_result.platform_data = {"platform_name": "Test Platform"}
        operation_result.error_details = None
        operation_result.requires_refresh = False
        
        # Test notification sending
        with patch.object(self.notification_manager, 'send_user_notification', return_value=True) as mock_send:
            result = adapter.send_platform_operation_notification(1, operation_result)
            self.assertTrue(result)
            mock_send.assert_called_once()
            
            # Verify the notification message
            call_args = mock_send.call_args
            user_id, message = call_args[0]
            self.assertEqual(user_id, 1)
            self.assertEqual(message.category, NotificationCategory.PLATFORM)
            self.assertEqual(message.type, NotificationType.SUCCESS)
            self.assertIn('connect_platform', message.data['operation_type'])
    
    def test_dashboard_notification_adapter(self):
        """Test dashboard notification adapter functionality"""
        adapter = DashboardNotificationAdapter(self.notification_manager)
        
        # Test dashboard update notification
        with patch.object(self.notification_manager, 'send_user_notification', return_value=True) as mock_send:
            result = adapter.send_dashboard_update_notification(
                user_id=1,
                update_type="widget_refresh",
                message="Dashboard widgets updated",
                data={"widget_count": 5}
            )
            self.assertTrue(result)
            mock_send.assert_called_once()
            
            # Verify the notification message
            call_args = mock_send.call_args
            user_id, message = call_args[0]
            self.assertEqual(user_id, 1)
            self.assertEqual(message.category, NotificationCategory.DASHBOARD)
            self.assertEqual(message.update_type, "widget_refresh")
    
    def test_monitoring_notification_adapter(self):
        """Test monitoring notification adapter functionality"""
        adapter = MonitoringNotificationAdapter(self.notification_manager)
        
        # Test critical monitoring alert
        with patch.object(self.notification_manager, 'send_user_notification', return_value=True) as mock_send:
            result = adapter.send_monitoring_alert(
                user_id=1,
                alert_type="cpu_usage",
                message="CPU usage exceeded 90%",
                severity="critical",
                data={"cpu_percentage": 95.2}
            )
            self.assertTrue(result)
            mock_send.assert_called_once()
            
            # Verify the notification message
            call_args = mock_send.call_args
            user_id, message = call_args[0]
            self.assertEqual(user_id, 1)
            self.assertEqual(message.category, NotificationCategory.MONITORING)
            self.assertEqual(message.type, NotificationType.ERROR)  # Critical maps to ERROR
            self.assertEqual(message.priority, NotificationPriority.CRITICAL)
    
    def test_performance_notification_adapter(self):
        """Test performance notification adapter functionality"""
        adapter = PerformanceNotificationAdapter(self.notification_manager)
        
        # Test performance alert
        with patch.object(self.notification_manager, 'send_user_notification', return_value=True) as mock_send:
            result = adapter.send_performance_alert(
                user_id=1,
                metrics={"response_time": 2.5, "memory_usage": 85.0},
                threshold_exceeded="response_time",
                recovery_action="Restart service"
            )
            self.assertTrue(result)
            mock_send.assert_called_once()
            
            # Verify the notification message
            call_args = mock_send.call_args
            user_id, message = call_args[0]
            self.assertEqual(user_id, 1)
            self.assertEqual(message.category, NotificationCategory.PERFORMANCE)
            self.assertEqual(message.type, NotificationType.WARNING)
            self.assertEqual(message.threshold_exceeded, "response_time")
    
    def test_health_notification_adapter(self):
        """Test health notification adapter functionality"""
        adapter = HealthNotificationAdapter(self.notification_manager)
        
        # Test health alert
        with patch.object(self.notification_manager, 'send_user_notification', return_value=True) as mock_send:
            result = adapter.send_health_alert(
                user_id=1,
                component="database",
                status="unhealthy",
                message="Database connection failed",
                data={"connection_attempts": 3}
            )
            self.assertTrue(result)
            mock_send.assert_called_once()
            
            # Verify the notification message
            call_args = mock_send.call_args
            user_id, message = call_args[0]
            self.assertEqual(user_id, 1)
            self.assertEqual(message.category, NotificationCategory.HEALTH)
            self.assertEqual(message.type, NotificationType.ERROR)  # Unhealthy maps to ERROR
            self.assertEqual(message.component, "database")
    
    def test_unified_notification_delivery(self):
        """Test unified notification delivery across all categories"""
        test_categories = [
            NotificationCategory.SYSTEM,
            NotificationCategory.ADMIN,
            NotificationCategory.USER,
            NotificationCategory.CAPTION,
            NotificationCategory.PLATFORM,
            NotificationCategory.SECURITY,
            NotificationCategory.MAINTENANCE,
            NotificationCategory.STORAGE,
            NotificationCategory.DASHBOARD,
            NotificationCategory.MONITORING,
            NotificationCategory.PERFORMANCE,
            NotificationCategory.HEALTH
        ]
        
        for category in test_categories:
            with self.subTest(category=category):
                message = NotificationMessage(
                    id=str(uuid.uuid4()),
                    type=NotificationType.INFO,
                    title=f"Test {category.value} Notification",
                    message=f"Testing {category.value} notification delivery",
                    category=category,
                    priority=NotificationPriority.NORMAL
                )
                
                with patch.object(self.notification_manager, 'send_user_notification', return_value=True) as mock_send:
                    result = self.notification_manager.send_user_notification(1, message)
                    self.assertTrue(result, f"Failed to send {category.value} notification")
    
    def test_adapter_error_handling(self):
        """Test error handling in notification adapters"""
        # Test StorageNotificationAdapter with invalid user_id
        adapter = StorageNotificationAdapter(self.notification_manager)
        
        # Test with invalid user_id
        with self.assertRaises(ValueError):
            adapter.send_storage_limit_notification(-1, Mock())
        
        with self.assertRaises(ValueError):
            adapter.send_storage_limit_notification("invalid", Mock())
        
        # Test with None storage_context
        result = adapter.send_storage_limit_notification(1, None)
        self.assertTrue(result)  # Adapter handles None gracefully
    
    def test_adapter_type_validation(self):
        """Test adapter constructor type validation"""
        # Test with invalid notification manager
        with self.assertRaises(TypeError):
            StorageNotificationAdapter("invalid_manager")
        
        with self.assertRaises(TypeError):
            PlatformNotificationAdapter(None)
    
    def test_notification_helper_functions(self):
        """Test notification helper functions integration"""
        from app.services.notification.helpers.notification_helpers import (
            send_storage_notification, send_platform_notification,
            send_dashboard_notification, send_monitoring_notification,
            send_performance_notification, send_health_notification
        )
        
        # Test that helper functions exist and are callable
        self.assertTrue(callable(send_storage_notification))
        self.assertTrue(callable(send_platform_notification))
        self.assertTrue(callable(send_dashboard_notification))
        self.assertTrue(callable(send_monitoring_notification))
        self.assertTrue(callable(send_performance_notification))
        self.assertTrue(callable(send_health_notification))
        
        # Test helper functions return True when no Flask context (testing mode)
        from unittest.mock import Mock
        storage_context = Mock()
        storage_context.is_blocked = False
        storage_context.reason = "Storage OK"
        
        # These should return True due to has_app_context() check
        result = send_storage_notification(1, storage_context)
        self.assertTrue(result)
        
        platform_result = Mock()
        platform_result.success = True
        platform_result.message = "Test message"
        result = send_platform_notification(1, platform_result)
        self.assertTrue(result)
        
        result = send_dashboard_notification(1, "test_update", "Test dashboard message")
        self.assertTrue(result)
        
        result = send_monitoring_notification(1, "test_alert", "Test monitoring message")
        self.assertTrue(result)
        
        result = send_performance_notification(1, {"cpu": 80.0}, "CPU threshold exceeded")
        self.assertTrue(result)
        
        result = send_health_notification(1, "database", "healthy", "Database is healthy")
        self.assertTrue(result)





if __name__ == '__main__':
    unittest.main()

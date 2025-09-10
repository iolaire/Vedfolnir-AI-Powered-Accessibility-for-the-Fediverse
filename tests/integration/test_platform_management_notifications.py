# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Platform Management Notification Integration Tests

Tests for the platform management WebSocket notification system integration,
verifying that platform operations send appropriate real-time notifications.
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.services.platform.integration.platform_management_notification_integration import (
    PlatformManagementNotificationService,
    PlatformOperationResult,
    create_platform_operation_result
)
from app.services.platform.integration.platform_management_route_integration import (
    PlatformRouteNotificationIntegrator,
    get_platform_route_integrator
)
from app.services.platform.error_handling.platform_management_error_handling import (
    PlatformErrorHandler,
    PlatformError,
    PlatformErrorType,
    PlatformErrorSeverity
)
from models import NotificationType, NotificationPriority, NotificationCategory, UserRole


class TestPlatformManagementNotificationService(unittest.TestCase):
    """Test platform management notification service"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock dependencies
        self.mock_notification_manager = Mock()
        self.mock_page_integrator = Mock()
        
        # Create service instance
        self.service = PlatformManagementNotificationService(
            self.mock_notification_manager,
            self.mock_page_integrator
        )
    
    def test_send_platform_connection_notification_success(self):
        """Test sending successful platform connection notification"""
        # Arrange
        user_id = 123
        result = create_platform_operation_result(
            success=True,
            message="Platform added successfully",
            operation_type="add_platform",
            platform_data={"name": "Test Platform", "type": "pixelfed"}
        )
        
        self.mock_notification_manager.send_user_notification.return_value = True
        
        # Act
        success = self.service.send_platform_connection_notification(user_id, result)
        
        # Assert
        self.assertTrue(success)
        self.mock_notification_manager.send_user_notification.assert_called_once()
        
        # Verify notification message
        call_args = self.mock_notification_manager.send_user_notification.call_args
        notification = call_args[0][1]  # Second argument is the notification
        
        self.assertEqual(notification.type, NotificationType.SUCCESS)
        self.assertEqual(notification.user_id, user_id)
        self.assertEqual(notification.category, NotificationCategory.PLATFORM)
        self.assertIn("add_platform", notification.data["operation_type"])
    
    def test_send_platform_connection_notification_failure(self):
        """Test sending failed platform connection notification"""
        # Arrange
        user_id = 123
        result = create_platform_operation_result(
            success=False,
            message="Connection failed",
            operation_type="test_connection",
            error_details="Invalid credentials"
        )
        
        self.mock_notification_manager.send_user_notification.return_value = True
        
        # Act
        success = self.service.send_platform_connection_notification(user_id, result)
        
        # Assert
        self.assertTrue(success)
        
        # Verify notification message
        call_args = self.mock_notification_manager.send_user_notification.call_args
        notification = call_args[0][1]
        
        self.assertEqual(notification.type, NotificationType.ERROR)
        self.assertEqual(notification.priority, NotificationPriority.HIGH)
        self.assertIn("Invalid credentials", notification.data["error_details"])
    
    def test_send_platform_status_notification(self):
        """Test sending platform status notification"""
        # Arrange
        user_id = 123
        platform_name = "Test Platform"
        status = "active"
        details = "Connection restored"
        
        self.mock_notification_manager.send_user_notification.return_value = True
        
        # Act
        success = self.service.send_platform_status_notification(
            user_id, platform_name, status, details
        )
        
        # Assert
        self.assertTrue(success)
        
        # Verify notification message
        call_args = self.mock_notification_manager.send_user_notification.call_args
        notification = call_args[0][1]
        
        self.assertEqual(notification.type, NotificationType.SUCCESS)
        self.assertIn("✅", notification.message)
        self.assertIn(platform_name, notification.message)
        self.assertIn(details, notification.message)
    
    def test_send_platform_switch_notification(self):
        """Test sending platform switch notification"""
        # Arrange
        user_id = 123
        from_platform = "Old Platform"
        to_platform = "New Platform"
        
        self.mock_notification_manager.send_user_notification.return_value = True
        
        # Act
        success = self.service.send_platform_switch_notification(
            user_id, from_platform, to_platform, True
        )
        
        # Assert
        self.assertTrue(success)
        
        # Verify notification message
        call_args = self.mock_notification_manager.send_user_notification.call_args
        notification = call_args[0][1]
        
        self.assertEqual(notification.type, NotificationType.SUCCESS)
        self.assertIn("✅", notification.message)
        self.assertIn(from_platform, notification.message)
        self.assertIn(to_platform, notification.message)
    
    def test_send_platform_authentication_error(self):
        """Test sending platform authentication error notification"""
        # Arrange
        user_id = 123
        platform_name = "Test Platform"
        error_type = "invalid_token"
        error_details = "Access token expired"
        
        self.mock_notification_manager.send_user_notification.return_value = True
        
        # Act
        success = self.service.send_platform_authentication_error(
            user_id, platform_name, error_type, error_details
        )
        
        # Assert
        self.assertTrue(success)
        
        # Verify notification message
        call_args = self.mock_notification_manager.send_user_notification.call_args
        notification = call_args[0][1]
        
        self.assertEqual(notification.type, NotificationType.ERROR)
        self.assertEqual(notification.priority, NotificationPriority.HIGH)
        self.assertTrue(notification.requires_action)
        self.assertEqual(notification.action_text, "Update Credentials")
        self.assertIn("🔐", notification.message)


class TestPlatformRouteNotificationIntegrator(unittest.TestCase):
    """Test platform route notification integrator"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.integrator = PlatformRouteNotificationIntegrator()
        
        # Mock the notification service
        self.mock_service = Mock()
        self.integrator.notification_service = self.mock_service
    
    def test_handle_add_platform_response_success(self):
        """Test handling successful add platform response"""
        # Arrange
        platform_data = {
            "id": 123,
            "name": "Test Platform",
            "platform_type": "pixelfed"
        }
        
        self.mock_service.send_platform_connection_notification.return_value = True
        
        # Act
        with patch('platform_management_route_integration.current_user') as mock_user:
            mock_user.id = 456
            response_data, status_code = self.integrator.handle_add_platform_response(
                success=True,
                message="Platform added successfully",
                platform_data=platform_data,
                is_first_platform=True
            )
        
        # Assert
        self.assertEqual(status_code, 200)
        self.assertTrue(response_data["success"])
        self.assertTrue(response_data["is_first_platform"])
        self.assertTrue(response_data["requires_refresh"])
        self.assertEqual(response_data["platform"], platform_data)
        
        # Verify notification was sent
        self.mock_service.send_platform_connection_notification.assert_called_once()
    
    def test_handle_switch_platform_response_success(self):
        """Test handling successful switch platform response"""
        # Arrange
        platform_data = {
            "id": 123,
            "name": "New Platform",
            "platform_type": "mastodon"
        }
        
        self.mock_service.send_platform_switch_notification.return_value = True
        
        # Act
        with patch('platform_management_route_integration.current_user') as mock_user:
            mock_user.id = 456
            response_data, status_code = self.integrator.handle_switch_platform_response(
                success=True,
                message="Platform switched successfully",
                platform_data=platform_data,
                from_platform="Old Platform"
            )
        
        # Assert
        self.assertEqual(status_code, 200)
        self.assertTrue(response_data["success"])
        self.assertEqual(response_data["platform"], platform_data)
        
        # Verify notification was sent
        self.mock_service.send_platform_switch_notification.assert_called_once()
    
    def test_handle_test_platform_response(self):
        """Test handling test platform response"""
        # Arrange
        platform_info = {
            "name": "Test Platform",
            "type": "pixelfed",
            "instance": "https://pixelfed.social"
        }
        
        self.mock_service.send_platform_status_notification.return_value = True
        
        # Act
        with patch('platform_management_route_integration.current_user') as mock_user:
            mock_user.id = 456
            response_data, status_code = self.integrator.handle_test_platform_response(
                success=True,
                message="Connection test successful",
                platform_name="Test Platform",
                platform_info=platform_info
            )
        
        # Assert
        self.assertEqual(status_code, 200)
        self.assertTrue(response_data["success"])
        self.assertEqual(response_data["platform_info"], platform_info)
        
        # Verify notification was sent
        self.mock_service.send_platform_status_notification.assert_called_once()
    
    def test_handle_authentication_error(self):
        """Test handling authentication error"""
        # Arrange
        self.mock_service.send_platform_authentication_error.return_value = True
        
        # Act
        with patch('platform_management_route_integration.current_user') as mock_user:
            mock_user.id = 456
            response_data, status_code = self.integrator.handle_authentication_error(
                platform_name="Test Platform",
                error_type="invalid_token",
                error_details="Token expired"
            )
        
        # Assert
        self.assertEqual(status_code, 401)
        self.assertFalse(response_data["success"])
        self.assertEqual(response_data["error_type"], "authentication")
        self.assertTrue(response_data["requires_action"])
        self.assertEqual(response_data["action_text"], "Update Credentials")
        
        # Verify notification was sent
        self.mock_service.send_platform_authentication_error.assert_called_once()
    
    def test_handle_maintenance_mode_response(self):
        """Test handling maintenance mode response"""
        # Arrange
        maintenance_info = {
            "reason": "Scheduled maintenance",
            "estimated_duration": 30
        }
        
        self.mock_service.send_maintenance_mode_notification.return_value = True
        
        # Act
        with patch('platform_management_route_integration.current_user') as mock_user:
            mock_user.id = 456
            response_data, status_code = self.integrator.handle_maintenance_mode_response(
                operation_type="platform_switching",
                maintenance_info=maintenance_info
            )
        
        # Assert
        self.assertEqual(status_code, 503)
        self.assertFalse(response_data["success"])
        self.assertTrue(response_data["maintenance_active"])
        self.assertEqual(response_data["maintenance_info"], maintenance_info)
        
        # Verify notification was sent
        self.mock_service.send_maintenance_mode_notification.assert_called_once()


class TestPlatformErrorHandler(unittest.TestCase):
    """Test platform error handler"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_notification_service = Mock()
        self.error_handler = PlatformErrorHandler(self.mock_notification_service)
    
    def test_classify_error_authentication(self):
        """Test classifying authentication errors"""
        # Test various authentication error messages
        auth_messages = [
            "Invalid token provided",
            "Authentication failed",
            "Access denied - unauthorized",
            "Token expired"
        ]
        
        for message in auth_messages:
            error_type = self.error_handler.classify_error(message)
            self.assertEqual(error_type, PlatformErrorType.AUTHENTICATION_ERROR)
    
    def test_classify_error_connection(self):
        """Test classifying connection errors"""
        # Test various connection error messages
        connection_messages = [
            "Connection refused",
            "Network unreachable",
            "Connection timeout",
            "DNS resolution failed"
        ]
        
        for message in connection_messages:
            error_type = self.error_handler.classify_error(message)
            self.assertEqual(error_type, PlatformErrorType.CONNECTION_ERROR)
    
    def test_determine_severity(self):
        """Test determining error severity"""
        # Test critical severity
        severity = self.error_handler.determine_severity(
            PlatformErrorType.AUTHENTICATION_ERROR, "add_platform"
        )
        self.assertEqual(severity, PlatformErrorSeverity.CRITICAL)
        
        # Test high severity
        severity = self.error_handler.determine_severity(
            PlatformErrorType.CONNECTION_ERROR, "test_connection"
        )
        self.assertEqual(severity, PlatformErrorSeverity.HIGH)
        
        # Test medium severity
        severity = self.error_handler.determine_severity(
            PlatformErrorType.TIMEOUT_ERROR, "switch_platform"
        )
        self.assertEqual(severity, PlatformErrorSeverity.MEDIUM)
        
        # Test low severity
        severity = self.error_handler.determine_severity(
            PlatformErrorType.VALIDATION_ERROR, "edit_platform"
        )
        self.assertEqual(severity, PlatformErrorSeverity.LOW)
    
    def test_create_platform_error(self):
        """Test creating platform error object"""
        # Act
        platform_error = self.error_handler.create_platform_error(
            error_message="Invalid token provided",
            operation_type="add_platform",
            platform_name="Test Platform",
            error_details="Token has expired"
        )
        
        # Assert
        self.assertEqual(platform_error.error_type, PlatformErrorType.AUTHENTICATION_ERROR)
        self.assertEqual(platform_error.severity, PlatformErrorSeverity.CRITICAL)
        self.assertEqual(platform_error.message, "Invalid token provided")
        self.assertEqual(platform_error.platform_name, "Test Platform")
        self.assertEqual(platform_error.operation_type, "add_platform")
        self.assertTrue(platform_error.requires_user_action)
        self.assertEqual(platform_error.action_text, "Update Credentials")
        self.assertIsNotNone(platform_error.recovery_suggestions)
    
    def test_handle_platform_error(self):
        """Test handling platform error with notification"""
        # Arrange
        test_error = Exception("Connection refused")
        
        self.mock_notification_service.send_platform_connection_notification.return_value = True
        
        # Act
        with patch('platform_management_error_handling.current_user') as mock_user:
            mock_user.id = 456
            platform_error = self.error_handler.handle_platform_error(
                error=test_error,
                operation_type="test_connection",
                platform_name="Test Platform"
            )
        
        # Assert
        self.assertEqual(platform_error.error_type, PlatformErrorType.CONNECTION_ERROR)
        self.assertEqual(platform_error.message, "Connection refused")
        self.assertEqual(platform_error.platform_name, "Test Platform")
        
        # Verify notification was attempted
        self.mock_notification_service.send_platform_connection_notification.assert_called_once()
    
    def test_get_error_recovery_info(self):
        """Test getting error recovery information"""
        # Arrange
        platform_error = PlatformError(
            error_type=PlatformErrorType.AUTHENTICATION_ERROR,
            severity=PlatformErrorSeverity.CRITICAL,
            message="Token expired",
            recovery_suggestions=["Update your access token"],
            requires_user_action=True,
            action_url="/platform_management",
            action_text="Update Credentials"
        )
        
        # Act
        recovery_info = self.error_handler.get_error_recovery_info(platform_error)
        
        # Assert
        self.assertEqual(recovery_info["error_type"], "authentication_error")
        self.assertEqual(recovery_info["severity"], "critical")
        self.assertTrue(recovery_info["requires_user_action"])
        self.assertEqual(recovery_info["action_text"], "Update Credentials")
        self.assertFalse(recovery_info["can_retry"])  # Auth errors shouldn't be retried
        self.assertIn("Update your access token", recovery_info["recovery_suggestions"])


class TestPlatformOperationResult(unittest.TestCase):
    """Test platform operation result helper"""
    
    def test_create_platform_operation_result(self):
        """Test creating platform operation result"""
        # Act
        result = create_platform_operation_result(
            success=True,
            message="Operation successful",
            operation_type="add_platform",
            platform_data={"name": "Test Platform"},
            requires_refresh=True
        )
        
        # Assert
        self.assertTrue(result.success)
        self.assertEqual(result.message, "Operation successful")
        self.assertEqual(result.operation_type, "add_platform")
        self.assertEqual(result.platform_data["name"], "Test Platform")
        self.assertTrue(result.requires_refresh)
        self.assertIsNone(result.error_details)


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)
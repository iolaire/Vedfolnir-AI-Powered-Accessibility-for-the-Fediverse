# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integration tests for user data modification blocking during maintenance mode.

Tests maintenance mode checks for profile updates, settings changes, and password changes.
Validates maintenance status display and messaging for user data modification attempts.
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from enhanced_maintenance_mode_service import EnhancedMaintenanceModeService, MaintenanceMode, MaintenanceStatus
from maintenance_operation_classifier import MaintenanceOperationClassifier, OperationType
from maintenance_mode_middleware import MaintenanceModeMiddleware
from maintenance_response_helper import MaintenanceResponseHelper
from models import User, UserRole


class TestUserDataModificationBlocking(unittest.TestCase):
    """Test cases for user data modification blocking during maintenance mode"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock configuration service
        self.mock_config_service = Mock()
        self.mock_config_service.get_config.return_value = False
        self.mock_config_service.subscribe_to_changes = Mock()
        
        # Mock database manager
        self.mock_db_manager = Mock()
        
        # Create maintenance service
        self.maintenance_service = EnhancedMaintenanceModeService(
            config_service=self.mock_config_service,
            db_manager=self.mock_db_manager
        )
        
        # Create operation classifier
        self.operation_classifier = MaintenanceOperationClassifier()
        
        # Create response helper
        self.response_helper = MaintenanceResponseHelper()
        
        # Create test users
        self.admin_user = Mock(spec=User)
        self.admin_user.id = 1
        self.admin_user.username = "admin"
        self.admin_user.role = UserRole.ADMIN
        
        self.regular_user = Mock(spec=User)
        self.regular_user.id = 2
        self.regular_user.username = "user"
        self.regular_user.role = UserRole.REVIEWER
    
    def test_user_data_modification_endpoints_classification(self):
        """Test that user data modification endpoints are correctly classified"""
        
        # Test caption settings endpoints
        self.assertEqual(
            self.operation_classifier.classify_operation('/caption_settings', 'GET'),
            OperationType.USER_DATA_MODIFICATION
        )
        
        self.assertEqual(
            self.operation_classifier.classify_operation('/api/caption_settings', 'GET'),
            OperationType.USER_DATA_MODIFICATION
        )
        
        self.assertEqual(
            self.operation_classifier.classify_operation('/save_caption_settings', 'POST'),
            OperationType.USER_DATA_MODIFICATION
        )
        
        self.assertEqual(
            self.operation_classifier.classify_operation('/api/validate_caption_settings', 'POST'),
            OperationType.USER_DATA_MODIFICATION
        )
        
        self.assertEqual(
            self.operation_classifier.classify_operation('/api/update_user_settings', 'POST'),
            OperationType.USER_DATA_MODIFICATION
        )
        
        # Test generic user data modification patterns
        self.assertEqual(
            self.operation_classifier.classify_operation('/profile/update', 'POST'),
            OperationType.USER_DATA_MODIFICATION
        )
        
        self.assertEqual(
            self.operation_classifier.classify_operation('/user/settings', 'POST'),
            OperationType.USER_DATA_MODIFICATION
        )
        
        self.assertEqual(
            self.operation_classifier.classify_operation('/password/change', 'POST'),
            OperationType.USER_DATA_MODIFICATION
        )
    
    def test_user_data_modification_blocking_in_normal_maintenance(self):
        """Test that user data modification is blocked in normal maintenance mode"""
        
        # Enable normal maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="Routine maintenance",
            mode=MaintenanceMode.NORMAL,
            enabled_by="admin"
        )
        
        # Test that user data modification operations are blocked for regular users
        user_data_endpoints = [
            '/caption_settings',
            '/api/caption_settings',
            '/save_caption_settings',
            '/api/validate_caption_settings',
            '/api/update_user_settings',
            '/profile/update',
            '/user/settings',
            '/password/change'
        ]
        
        for endpoint in user_data_endpoints:
            with self.subTest(endpoint=endpoint):
                # Regular user should be blocked
                is_blocked = self.maintenance_service.is_operation_blocked(endpoint, self.regular_user)
                self.assertTrue(is_blocked, f"Regular user should be blocked from {endpoint}")
                
                # Admin user should bypass
                is_blocked_admin = self.maintenance_service.is_operation_blocked(endpoint, self.admin_user)
                self.assertFalse(is_blocked_admin, f"Admin user should bypass {endpoint}")
    
    def test_user_data_modification_blocking_in_emergency_maintenance(self):
        """Test that user data modification is blocked in emergency maintenance mode"""
        
        # Enable emergency maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="Critical security update",
            mode=MaintenanceMode.EMERGENCY,
            enabled_by="admin"
        )
        
        # Test that user data modification operations are blocked for regular users
        user_data_endpoints = [
            '/caption_settings',
            '/save_caption_settings',
            '/api/update_user_settings'
        ]
        
        for endpoint in user_data_endpoints:
            with self.subTest(endpoint=endpoint):
                # Regular user should be blocked
                is_blocked = self.maintenance_service.is_operation_blocked(endpoint, self.regular_user)
                self.assertTrue(is_blocked, f"Regular user should be blocked from {endpoint} in emergency mode")
                
                # Admin user should still bypass
                is_blocked_admin = self.maintenance_service.is_operation_blocked(endpoint, self.admin_user)
                self.assertFalse(is_blocked_admin, f"Admin user should bypass {endpoint} in emergency mode")
    
    def test_user_data_modification_not_blocked_when_maintenance_disabled(self):
        """Test that user data modification is not blocked when maintenance is disabled"""
        
        # Ensure maintenance is disabled
        self.maintenance_service.disable_maintenance()
        
        # Test that user data modification operations are allowed
        user_data_endpoints = [
            '/caption_settings',
            '/save_caption_settings',
            '/api/update_user_settings'
        ]
        
        for endpoint in user_data_endpoints:
            with self.subTest(endpoint=endpoint):
                # Regular user should not be blocked
                is_blocked = self.maintenance_service.is_operation_blocked(endpoint, self.regular_user)
                self.assertFalse(is_blocked, f"Regular user should not be blocked from {endpoint} when maintenance is disabled")
                
                # Admin user should not be blocked
                is_blocked_admin = self.maintenance_service.is_operation_blocked(endpoint, self.admin_user)
                self.assertFalse(is_blocked_admin, f"Admin user should not be blocked from {endpoint} when maintenance is disabled")
    
    def test_user_data_modification_maintenance_response_creation(self):
        """Test creation of maintenance responses for user data modification operations"""
        
        # Enable maintenance mode
        maintenance_status = MaintenanceStatus(
            is_active=True,
            mode=MaintenanceMode.NORMAL,
            reason="System updates in progress",
            estimated_duration=30,
            started_at=datetime.now(timezone.utc),
            estimated_completion=None,
            enabled_by="admin",
            blocked_operations=[],
            active_jobs_count=0,
            invalidated_sessions=0,
            test_mode=False
        )
        
        # Test response creation for user data modification
        response_data = self.response_helper.create_json_response(
            operation='/save_caption_settings',
            maintenance_status=maintenance_status,
            operation_type=OperationType.USER_DATA_MODIFICATION
        )
        
        # Verify response structure
        self.assertEqual(response_data['error'], 'Service Unavailable')
        self.assertTrue(response_data['maintenance_active'])
        self.assertEqual(response_data['maintenance_info']['mode'], 'normal')
        self.assertEqual(response_data['maintenance_info']['reason'], 'System updates in progress')
        self.assertEqual(response_data['operation_info']['operation_type'], 'user_data_modification')
        self.assertEqual(response_data['operation_info']['title'], 'Profile Updates Unavailable')
        self.assertIn('User profile and settings updates are temporarily disabled', response_data['operation_info']['description'])
        self.assertEqual(response_data['operation_info']['icon'], '👤')
        self.assertIn('You can still browse and review content', response_data['operation_info']['suggestion'])
    
    def test_user_data_modification_operation_description(self):
        """Test operation description for user data modification"""
        
        description = self.operation_classifier.get_operation_description(OperationType.USER_DATA_MODIFICATION)
        self.assertEqual(description, "User profile and settings updates")
    
    def test_user_data_modification_blocking_rules(self):
        """Test blocking rules for user data modification in different maintenance modes"""
        
        # Test normal mode blocking
        blocked_operations_normal = self.operation_classifier.get_blocked_operations_for_mode(MaintenanceMode.NORMAL)
        self.assertIn(OperationType.USER_DATA_MODIFICATION, blocked_operations_normal)
        
        # Test emergency mode blocking
        blocked_operations_emergency = self.operation_classifier.get_blocked_operations_for_mode(MaintenanceMode.EMERGENCY)
        self.assertIn(OperationType.USER_DATA_MODIFICATION, blocked_operations_emergency)
        
        # Test test mode blocking (simulated)
        blocked_operations_test = self.operation_classifier.get_blocked_operations_for_mode(MaintenanceMode.TEST)
        self.assertIn(OperationType.USER_DATA_MODIFICATION, blocked_operations_test)
    
    def test_user_data_modification_with_flask_middleware(self):
        """Test user data modification blocking with Flask middleware"""
        
        # Mock Flask app
        mock_app = Mock()
        mock_app.before_request = Mock()
        
        # Create middleware
        middleware = MaintenanceModeMiddleware(mock_app, self.maintenance_service)
        
        # Enable maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="Database maintenance",
            mode=MaintenanceMode.NORMAL,
            enabled_by="admin"
        )
        
        # Test middleware operation checking directly (without Flask request context)
        # Regular user should be blocked
        is_allowed = middleware.is_allowed_operation('/save_caption_settings', self.regular_user, 'POST')
        self.assertFalse(is_allowed, "Regular user should not be allowed to save caption settings during maintenance")
        
        # Admin user should be allowed
        is_allowed_admin = middleware.is_allowed_operation('/save_caption_settings', self.admin_user, 'POST')
        self.assertTrue(is_allowed_admin, "Admin user should be allowed to save caption settings during maintenance")
    
    def test_user_data_modification_maintenance_message(self):
        """Test maintenance message generation for user data modification operations"""
        
        # Enable maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="User data migration",
            duration=45,
            mode=MaintenanceMode.NORMAL,
            enabled_by="admin"
        )
        
        # Get maintenance message for user data modification
        message = self.maintenance_service.get_maintenance_message('/save_caption_settings')
        
        # Verify message content
        self.assertIn("System maintenance is currently in progress", message)
        self.assertIn("User data migration", message)
        # The message shows estimated completion time instead of duration when duration is provided
        # So we check for either the duration or completion time format
        self.assertTrue("45 minutes" in message or "Expected completion:" in message, 
                       f"Message should contain duration or completion time: {message}")
        self.assertIn("user data modification", message)
        self.assertIn("Please try again later", message)
    
    def test_user_data_modification_test_mode_simulation(self):
        """Test that user data modification blocking is simulated in test mode"""
        
        # Enable test maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="Testing user data modification blocking",
            mode=MaintenanceMode.TEST,
            enabled_by="admin"
        )
        
        # Test that operations are not actually blocked in test mode
        is_blocked = self.maintenance_service.is_operation_blocked('/save_caption_settings', self.regular_user)
        self.assertFalse(is_blocked, "Operations should not be actually blocked in test mode")
        
        # Verify test mode is active
        status = self.maintenance_service.get_maintenance_status()
        self.assertTrue(status.test_mode, "Test mode should be active")
        self.assertTrue(status.is_active, "Maintenance should be active")
        self.assertEqual(status.mode, MaintenanceMode.TEST, "Mode should be TEST")


if __name__ == '__main__':
    unittest.main()
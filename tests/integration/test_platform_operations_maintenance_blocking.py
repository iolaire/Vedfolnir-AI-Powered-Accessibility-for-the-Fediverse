# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integration tests for platform operations maintenance mode blocking

Tests that platform switching, connection testing, and credential updates
are properly blocked during maintenance mode.
"""

import unittest
import json
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.services.maintenance.enhanced.enhanced_maintenance_mode_service import EnhancedMaintenanceModeService, MaintenanceMode, MaintenanceStatus
from app.services.maintenance.components.maintenance_operation_classifier import MaintenanceOperationClassifier, OperationType
from app.services.maintenance.components.maintenance_mode_middleware import MaintenanceModeMiddleware
from app.services.maintenance.components.maintenance_response_helper import MaintenanceResponseHelper
from models import User, UserRole


class TestPlatformOperationsMaintenanceBlocking(unittest.TestCase):
    """Test platform operations blocking during maintenance mode"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock configuration service
        self.mock_config_service = Mock()
        self.mock_config_service.get_config.return_value = False
        
        # Mock database manager
        self.mock_db_manager = Mock()
        
        # Create maintenance service
        self.maintenance_service = EnhancedMaintenanceModeService(
            self.mock_config_service, 
            self.mock_db_manager
        )
        
        # Create operation classifier
        self.operation_classifier = MaintenanceOperationClassifier()
        
        # Create response helper
        self.response_helper = MaintenanceResponseHelper()
        
        # Mock Flask app
        self.mock_app = Mock()
        
        # Create middleware
        self.middleware = MaintenanceModeMiddleware(self.mock_app, self.maintenance_service)
        
        # Create test users
        self.admin_user = Mock(spec=User)
        self.admin_user.id = 1
        self.admin_user.username = 'admin'
        self.admin_user.role = UserRole.ADMIN
        
        self.regular_user = Mock(spec=User)
        self.regular_user.id = 2
        self.regular_user.username = 'user'
        self.regular_user.role = UserRole.VIEWER
    
    def test_platform_operation_classification(self):
        """Test that platform operations are properly classified"""
        platform_endpoints = [
            '/platform_management',
            '/api/add_platform',
            '/api/switch_platform/123',
            '/api/test_platform/123',
            '/api/get_platform/123',
            '/api/edit_platform/123',
            '/api/delete_platform/123',
            '/switch_platform/123'
        ]
        
        for endpoint in platform_endpoints:
            with self.subTest(endpoint=endpoint):
                operation_type = self.operation_classifier.classify_operation(endpoint, 'POST')
                self.assertEqual(operation_type, OperationType.PLATFORM_OPERATIONS,
                               f"Endpoint {endpoint} should be classified as PLATFORM_OPERATIONS")
    
    def test_platform_operations_blocked_during_normal_maintenance(self):
        """Test that platform operations are blocked during normal maintenance"""
        # Enable normal maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="Routine maintenance",
            duration=30,
            mode=MaintenanceMode.NORMAL,
            enabled_by="admin"
        )
        
        platform_endpoints = [
            '/api/add_platform',
            '/api/switch_platform/123',
            '/api/test_platform/123',
            '/api/edit_platform/123'
        ]
        
        for endpoint in platform_endpoints:
            with self.subTest(endpoint=endpoint):
                # Test with regular user
                is_blocked = self.maintenance_service.is_operation_blocked(endpoint, self.regular_user)
                self.assertTrue(is_blocked, f"Platform operation {endpoint} should be blocked for regular user")
                
                # Test with admin user (should bypass)
                is_blocked_admin = self.maintenance_service.is_operation_blocked(endpoint, self.admin_user)
                self.assertFalse(is_blocked_admin, f"Platform operation {endpoint} should not be blocked for admin user")
    
    def test_platform_operations_blocked_during_emergency_maintenance(self):
        """Test that platform operations are blocked during emergency maintenance"""
        # Enable emergency maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="Critical security update",
            mode=MaintenanceMode.EMERGENCY,
            enabled_by="admin"
        )
        
        platform_endpoints = [
            '/api/add_platform',
            '/api/switch_platform/123',
            '/api/test_platform/123',
            '/api/edit_platform/123'
        ]
        
        for endpoint in platform_endpoints:
            with self.subTest(endpoint=endpoint):
                # Test with regular user
                is_blocked = self.maintenance_service.is_operation_blocked(endpoint, self.regular_user)
                self.assertTrue(is_blocked, f"Platform operation {endpoint} should be blocked for regular user during emergency")
                
                # Test with admin user (should still bypass)
                is_blocked_admin = self.maintenance_service.is_operation_blocked(endpoint, self.admin_user)
                self.assertFalse(is_blocked_admin, f"Platform operation {endpoint} should not be blocked for admin user during emergency")
    
    def test_platform_operations_not_blocked_during_test_mode(self):
        """Test that platform operations are not actually blocked during test mode"""
        # Enable test maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="Testing maintenance procedures",
            mode=MaintenanceMode.TEST,
            enabled_by="admin"
        )
        
        platform_endpoints = [
            '/api/add_platform',
            '/api/switch_platform/123',
            '/api/test_platform/123',
            '/api/edit_platform/123'
        ]
        
        for endpoint in platform_endpoints:
            with self.subTest(endpoint=endpoint):
                # Test mode should not actually block operations
                is_blocked = self.maintenance_service.is_operation_blocked(endpoint, self.regular_user)
                self.assertFalse(is_blocked, f"Platform operation {endpoint} should not be actually blocked in test mode")
    
    def test_platform_operations_allowed_when_maintenance_disabled(self):
        """Test that platform operations are allowed when maintenance is disabled"""
        # Ensure maintenance is disabled
        self.maintenance_service.disable_maintenance()
        
        platform_endpoints = [
            '/api/add_platform',
            '/api/switch_platform/123',
            '/api/test_platform/123',
            '/api/edit_platform/123'
        ]
        
        for endpoint in platform_endpoints:
            with self.subTest(endpoint=endpoint):
                is_blocked = self.maintenance_service.is_operation_blocked(endpoint, self.regular_user)
                self.assertFalse(is_blocked, f"Platform operation {endpoint} should not be blocked when maintenance is disabled")
    
    def test_maintenance_response_for_platform_operations(self):
        """Test maintenance response formatting for platform operations"""
        # Create maintenance status
        maintenance_status = MaintenanceStatus(
            is_active=True,
            mode=MaintenanceMode.NORMAL,
            reason="Routine system maintenance",
            estimated_duration=60,
            started_at=datetime.now(timezone.utc),
            estimated_completion=None,
            enabled_by="admin",
            blocked_operations=[],
            active_jobs_count=0,
            invalidated_sessions=0,
            test_mode=False
        )
        
        # Test response creation
        response_data = self.response_helper.create_json_response(
            '/api/switch_platform/123',
            maintenance_status,
            OperationType.PLATFORM_OPERATIONS
        )
        
        # Verify response structure
        self.assertEqual(response_data['error'], 'Service Unavailable')
        self.assertTrue(response_data['maintenance_active'])
        self.assertEqual(response_data['maintenance_info']['mode'], 'normal')
        self.assertEqual(response_data['maintenance_info']['reason'], 'Routine system maintenance')
        self.assertEqual(response_data['operation_info']['operation_type'], 'platform_operations')
        self.assertEqual(response_data['operation_info']['title'], 'Platform Operations Unavailable')
        self.assertIn('Platform switching, connection testing', response_data['operation_info']['description'])
        self.assertIn('current platform connection', response_data['operation_info']['suggestion'])
    
    def test_middleware_blocks_platform_operations(self):
        """Test that middleware properly blocks platform operations"""
        # Enable maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="System upgrade",
            duration=45,
            mode=MaintenanceMode.NORMAL,
            enabled_by="admin"
        )
        
        # Test that the service correctly identifies blocked operations
        is_blocked = self.maintenance_service.is_operation_blocked('/api/switch_platform/123', self.regular_user)
        self.assertTrue(is_blocked, "Platform operation should be blocked for regular user")
        
        # Test that admin users can bypass
        is_blocked_admin = self.maintenance_service.is_operation_blocked('/api/switch_platform/123', self.admin_user)
        self.assertFalse(is_blocked_admin, "Platform operation should not be blocked for admin user")
    
    def test_middleware_allows_admin_platform_operations(self):
        """Test that middleware allows admin users to perform platform operations"""
        # Enable maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="System upgrade",
            duration=45,
            mode=MaintenanceMode.NORMAL,
            enabled_by="admin"
        )
        
        # Test that admin users can bypass maintenance mode
        is_blocked = self.maintenance_service.is_operation_blocked('/api/switch_platform/123', self.admin_user)
        self.assertFalse(is_blocked, "Platform operation should not be blocked for admin user")
        
        # Test that regular users are blocked
        is_blocked_regular = self.maintenance_service.is_operation_blocked('/api/switch_platform/123', self.regular_user)
        self.assertTrue(is_blocked_regular, "Platform operation should be blocked for regular user")
    
    def test_platform_management_ui_shows_maintenance_status(self):
        """Test that platform management UI includes maintenance status"""
        # Create maintenance status
        maintenance_status = MaintenanceStatus(
            is_active=True,
            mode=MaintenanceMode.NORMAL,
            reason="Scheduled maintenance",
            estimated_duration=30,
            started_at=datetime.now(timezone.utc),
            estimated_completion=None,
            enabled_by="admin",
            blocked_operations=[],
            active_jobs_count=0,
            invalidated_sessions=0,
            test_mode=False
        )
        
        # Test maintenance status dict creation
        status_dict = self.response_helper.create_maintenance_status_dict(maintenance_status)
        
        # Verify status dict structure
        self.assertTrue(status_dict['is_active'])
        self.assertEqual(status_dict['mode'], 'normal')
        self.assertEqual(status_dict['reason'], 'Scheduled maintenance')
        self.assertEqual(status_dict['estimated_duration'], 30)
        self.assertIn('🔧 System Maintenance', status_dict['mode_display'])
        self.assertIn('alert', status_dict['banner_html'])
        # Banner HTML will be fallback due to missing Flask context
        self.assertIn('maintenance', status_dict['banner_html'])
    
    def test_maintenance_message_templates_for_platform_operations(self):
        """Test maintenance message templates for platform operations"""
        # Get platform operations template
        template = self.response_helper.get_operation_message_template(OperationType.PLATFORM_OPERATIONS)
        
        # Verify template content
        self.assertEqual(template['title'], 'Platform Operations Unavailable')
        self.assertEqual(template['icon'], '🔗')
        self.assertIn('Platform switching', template['description'])
        self.assertIn('connection testing', template['description'])
        self.assertIn('credential updates', template['description'])
        self.assertIn('current platform connection', template['suggestion'])
    
    def test_blocked_operations_list_includes_platform_operations(self):
        """Test that blocked operations list includes platform operations during maintenance"""
        # Enable maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="System maintenance",
            mode=MaintenanceMode.NORMAL,
            enabled_by="admin"
        )
        
        # Get blocked operations
        blocked_operations = self.maintenance_service.get_blocked_operations()
        
        # Should include platform operations
        self.assertIn('platform_operations', blocked_operations)
    
    def test_maintenance_logging_for_platform_operations(self):
        """Test that platform operation blocking is properly logged"""
        # Enable maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="System maintenance",
            mode=MaintenanceMode.NORMAL,
            enabled_by="admin"
        )
        
        # Test that maintenance service logs events
        with patch('enhanced_maintenance_mode_service.logger') as mock_logger:
            # Log a maintenance event
            self.maintenance_service.log_maintenance_event(
                'operation_blocked',
                {
                    'endpoint': '/api/switch_platform/123',
                    'method': 'POST',
                    'user_context': {
                        'user_id': self.regular_user.id,
                        'username': self.regular_user.username,
                        'role': self.regular_user.role.value
                    }
                },
                'admin'
            )
            
            # Verify logging was called
            mock_logger.info.assert_called()
            call_args = mock_logger.info.call_args
            self.assertIn('Maintenance event: operation_blocked', call_args[0][0])
    
    def test_retry_after_header_for_platform_operations(self):
        """Test that Retry-After header is set for platform operations"""
        # Create maintenance status with duration
        maintenance_status = MaintenanceStatus(
            is_active=True,
            mode=MaintenanceMode.NORMAL,
            reason="System maintenance",
            estimated_duration=30,  # 30 minutes
            started_at=datetime.now(timezone.utc),
            estimated_completion=None,
            enabled_by="admin",
            blocked_operations=[],
            active_jobs_count=0,
            invalidated_sessions=0,
            test_mode=False
        )
        
        # Create Flask response
        with patch('maintenance_response_helper.jsonify') as mock_jsonify:
            mock_response = Mock()
            mock_response.status_code = 503
            mock_response.headers = {}
            mock_jsonify.return_value = mock_response
            
            response = self.response_helper.create_flask_response(
                '/api/switch_platform/123',
                maintenance_status,
                OperationType.PLATFORM_OPERATIONS
            )
            
            # Verify Retry-After header is set (30 minutes = 1800 seconds)
            self.assertEqual(response.headers.get('Retry-After'), '1800')
            self.assertEqual(response.headers.get('X-Maintenance-Active'), 'true')
            self.assertEqual(response.headers.get('X-Maintenance-Mode'), 'normal')


if __name__ == '__main__':
    unittest.main()
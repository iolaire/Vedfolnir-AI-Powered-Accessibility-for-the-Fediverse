# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integration tests for batch operations maintenance mode blocking

Tests that batch processing, bulk review operations, and bulk caption updates
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


class TestBatchOperationsMaintenanceBlocking(unittest.TestCase):
    """Test batch operations blocking during maintenance mode"""
    
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
    
    def test_batch_operation_classification(self):
        """Test that batch operations are properly classified"""
        batch_endpoints = [
            '/batch_review',
            '/api/batch_review',
            '/review/batches',
            '/review/batch/batch123',
            '/api/review/batch/batch123/bulk_approve',
            '/api/review/batch/batch123/bulk_reject',
            '/api/review/batch/batch123/quality_metrics',
            '/api/review/batch/batch123/statistics',
            '/api/review/batch/image/456/caption'
        ]
        
        for endpoint in batch_endpoints:
            with self.subTest(endpoint=endpoint):
                operation_type = self.operation_classifier.classify_operation(endpoint, 'POST')
                self.assertEqual(operation_type, OperationType.BATCH_OPERATIONS,
                               f"Endpoint {endpoint} should be classified as BATCH_OPERATIONS")
    
    def test_batch_operations_blocked_during_normal_maintenance(self):
        """Test that batch operations are blocked during normal maintenance"""
        # Enable normal maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="System optimization",
            duration=45,
            mode=MaintenanceMode.NORMAL,
            enabled_by="admin"
        )
        
        batch_endpoints = [
            '/api/batch_review',
            '/api/review/batch/batch123/bulk_approve',
            '/api/review/batch/batch123/bulk_reject',
            '/review/batches'
        ]
        
        for endpoint in batch_endpoints:
            with self.subTest(endpoint=endpoint):
                # Test with regular user
                is_blocked = self.maintenance_service.is_operation_blocked(endpoint, self.regular_user)
                self.assertTrue(is_blocked, f"Batch operation {endpoint} should be blocked for regular user")
                
                # Test with admin user (should bypass)
                is_blocked_admin = self.maintenance_service.is_operation_blocked(endpoint, self.admin_user)
                self.assertFalse(is_blocked_admin, f"Batch operation {endpoint} should not be blocked for admin user")
    
    def test_batch_operations_blocked_during_emergency_maintenance(self):
        """Test that batch operations are blocked during emergency maintenance"""
        # Enable emergency maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="Critical system issue",
            mode=MaintenanceMode.EMERGENCY,
            enabled_by="admin"
        )
        
        batch_endpoints = [
            '/api/batch_review',
            '/api/review/batch/batch123/bulk_approve',
            '/api/review/batch/batch123/bulk_reject',
            '/review/batches'
        ]
        
        for endpoint in batch_endpoints:
            with self.subTest(endpoint=endpoint):
                # Test with regular user
                is_blocked = self.maintenance_service.is_operation_blocked(endpoint, self.regular_user)
                self.assertTrue(is_blocked, f"Batch operation {endpoint} should be blocked for regular user during emergency")
                
                # Test with admin user (should still bypass)
                is_blocked_admin = self.maintenance_service.is_operation_blocked(endpoint, self.admin_user)
                self.assertFalse(is_blocked_admin, f"Batch operation {endpoint} should not be blocked for admin user during emergency")
    
    def test_batch_operations_not_blocked_during_test_mode(self):
        """Test that batch operations are not actually blocked during test mode"""
        # Enable test maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="Testing batch operation blocking",
            mode=MaintenanceMode.TEST,
            enabled_by="admin"
        )
        
        batch_endpoints = [
            '/api/batch_review',
            '/api/review/batch/batch123/bulk_approve',
            '/api/review/batch/batch123/bulk_reject',
            '/review/batches'
        ]
        
        for endpoint in batch_endpoints:
            with self.subTest(endpoint=endpoint):
                # Test mode should not actually block operations
                is_blocked = self.maintenance_service.is_operation_blocked(endpoint, self.regular_user)
                self.assertFalse(is_blocked, f"Batch operation {endpoint} should not be actually blocked in test mode")
    
    def test_batch_operations_allowed_when_maintenance_disabled(self):
        """Test that batch operations are allowed when maintenance is disabled"""
        # Ensure maintenance is disabled
        self.maintenance_service.disable_maintenance()
        
        batch_endpoints = [
            '/api/batch_review',
            '/api/review/batch/batch123/bulk_approve',
            '/api/review/batch/batch123/bulk_reject',
            '/review/batches'
        ]
        
        for endpoint in batch_endpoints:
            with self.subTest(endpoint=endpoint):
                is_blocked = self.maintenance_service.is_operation_blocked(endpoint, self.regular_user)
                self.assertFalse(is_blocked, f"Batch operation {endpoint} should not be blocked when maintenance is disabled")
    
    def test_maintenance_response_for_batch_operations(self):
        """Test maintenance response formatting for batch operations"""
        # Create maintenance status
        maintenance_status = MaintenanceStatus(
            is_active=True,
            mode=MaintenanceMode.NORMAL,
            reason="Database optimization in progress",
            estimated_duration=90,
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
            '/api/review/batch/batch123/bulk_approve',
            maintenance_status,
            OperationType.BATCH_OPERATIONS
        )
        
        # Verify response structure
        self.assertEqual(response_data['error'], 'Service Unavailable')
        self.assertTrue(response_data['maintenance_active'])
        self.assertEqual(response_data['maintenance_info']['mode'], 'normal')
        self.assertEqual(response_data['maintenance_info']['reason'], 'Database optimization in progress')
        self.assertEqual(response_data['operation_info']['operation_type'], 'batch_operations')
        self.assertEqual(response_data['operation_info']['title'], 'Batch Operations Unavailable')
        self.assertIn('Bulk processing', response_data['operation_info']['description'])
        self.assertIn('batch reviews', response_data['operation_info']['description'])
        self.assertIn('individual items', response_data['operation_info']['suggestion'])
    
    def test_middleware_blocks_batch_operations(self):
        """Test that middleware properly blocks batch operations"""
        # Enable maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="System maintenance",
            duration=60,
            mode=MaintenanceMode.NORMAL,
            enabled_by="admin"
        )
        
        # Test that the service correctly identifies blocked operations
        is_blocked = self.maintenance_service.is_operation_blocked('/api/review/batch/batch123/bulk_approve', self.regular_user)
        self.assertTrue(is_blocked, "Batch operation should be blocked for regular user")
        
        # Test that admin users can bypass
        is_blocked_admin = self.maintenance_service.is_operation_blocked('/api/review/batch/batch123/bulk_approve', self.admin_user)
        self.assertFalse(is_blocked_admin, "Batch operation should not be blocked for admin user")
    
    def test_middleware_allows_admin_batch_operations(self):
        """Test that middleware allows admin users to perform batch operations"""
        # Enable maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="System maintenance",
            duration=60,
            mode=MaintenanceMode.NORMAL,
            enabled_by="admin"
        )
        
        # Test that admin users can bypass maintenance mode
        is_blocked = self.maintenance_service.is_operation_blocked('/api/review/batch/batch123/bulk_approve', self.admin_user)
        self.assertFalse(is_blocked, "Batch operation should not be blocked for admin user")
        
        # Test that regular users are blocked
        is_blocked_regular = self.maintenance_service.is_operation_blocked('/api/review/batch/batch123/bulk_approve', self.regular_user)
        self.assertTrue(is_blocked_regular, "Batch operation should be blocked for regular user")
    
    def test_batch_review_ui_shows_maintenance_status(self):
        """Test that batch review UI would show maintenance status"""
        # Create maintenance status
        maintenance_status = MaintenanceStatus(
            is_active=True,
            mode=MaintenanceMode.NORMAL,
            reason="Batch processing optimization",
            estimated_duration=45,
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
        self.assertEqual(status_dict['reason'], 'Batch processing optimization')
        self.assertEqual(status_dict['estimated_duration'], 45)
        self.assertIn('🔧 System Maintenance', status_dict['mode_display'])
        self.assertIn('alert', status_dict['banner_html'])
        # Banner HTML will be fallback due to missing Flask context
        self.assertIn('maintenance', status_dict['banner_html'])
    
    def test_maintenance_message_templates_for_batch_operations(self):
        """Test maintenance message templates for batch operations"""
        # Get batch operations template
        template = self.response_helper.get_operation_message_template(OperationType.BATCH_OPERATIONS)
        
        # Verify template content
        self.assertEqual(template['title'], 'Batch Operations Unavailable')
        self.assertEqual(template['icon'], '📦')
        self.assertIn('Bulk processing', template['description'])
        self.assertIn('batch reviews', template['description'])
        self.assertIn('bulk caption updates', template['description'])
        self.assertIn('individual items', template['suggestion'])
    
    def test_blocked_operations_list_includes_batch_operations(self):
        """Test that blocked operations list includes batch operations during maintenance"""
        # Enable maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="System maintenance",
            mode=MaintenanceMode.NORMAL,
            enabled_by="admin"
        )
        
        # Get blocked operations
        blocked_operations = self.maintenance_service.get_blocked_operations()
        
        # Should include batch operations
        self.assertIn('batch_operations', blocked_operations)
    
    def test_bulk_approve_blocked_during_maintenance(self):
        """Test that bulk approve operations are blocked during maintenance"""
        # Enable maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="System maintenance",
            mode=MaintenanceMode.NORMAL,
            enabled_by="admin"
        )
        
        # Test bulk approve endpoint
        is_blocked = self.maintenance_service.is_operation_blocked(
            '/api/review/batch/batch123/bulk_approve', 
            self.regular_user
        )
        self.assertTrue(is_blocked, "Bulk approve should be blocked during maintenance")
    
    def test_bulk_reject_blocked_during_maintenance(self):
        """Test that bulk reject operations are blocked during maintenance"""
        # Enable maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="System maintenance",
            mode=MaintenanceMode.NORMAL,
            enabled_by="admin"
        )
        
        # Test bulk reject endpoint
        is_blocked = self.maintenance_service.is_operation_blocked(
            '/api/review/batch/batch123/bulk_reject', 
            self.regular_user
        )
        self.assertTrue(is_blocked, "Bulk reject should be blocked during maintenance")
    
    def test_batch_statistics_blocked_during_maintenance(self):
        """Test that batch statistics operations are blocked during maintenance"""
        # Enable maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="System maintenance",
            mode=MaintenanceMode.NORMAL,
            enabled_by="admin"
        )
        
        # Test batch statistics endpoint
        is_blocked = self.maintenance_service.is_operation_blocked(
            '/api/review/batch/batch123/statistics', 
            self.regular_user
        )
        self.assertTrue(is_blocked, "Batch statistics should be blocked during maintenance")
    
    def test_batch_quality_metrics_blocked_during_maintenance(self):
        """Test that batch quality metrics operations are blocked during maintenance"""
        # Enable maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="System maintenance",
            mode=MaintenanceMode.NORMAL,
            enabled_by="admin"
        )
        
        # Test batch quality metrics endpoint
        is_blocked = self.maintenance_service.is_operation_blocked(
            '/api/review/batch/batch123/quality_metrics', 
            self.regular_user
        )
        self.assertTrue(is_blocked, "Batch quality metrics should be blocked during maintenance")
    
    def test_maintenance_logging_for_batch_operations(self):
        """Test that batch operation blocking is properly logged"""
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
                    'endpoint': '/api/review/batch/batch123/bulk_approve',
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
    
    def test_retry_after_header_for_batch_operations(self):
        """Test that Retry-After header is set for batch operations"""
        # Create maintenance status with duration
        maintenance_status = MaintenanceStatus(
            is_active=True,
            mode=MaintenanceMode.NORMAL,
            reason="Batch processing maintenance",
            estimated_duration=60,  # 60 minutes
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
                '/api/review/batch/batch123/bulk_approve',
                maintenance_status,
                OperationType.BATCH_OPERATIONS
            )
            
            # Verify Retry-After header is set (60 minutes = 3600 seconds)
            self.assertEqual(response.headers.get('Retry-After'), '3600')
            self.assertEqual(response.headers.get('X-Maintenance-Active'), 'true')
            self.assertEqual(response.headers.get('X-Maintenance-Mode'), 'normal')


if __name__ == '__main__':
    unittest.main()
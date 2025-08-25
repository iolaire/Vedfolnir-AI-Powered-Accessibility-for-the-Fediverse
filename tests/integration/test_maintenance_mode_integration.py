# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integration tests for maintenance mode with job creation endpoints

Tests maintenance mode blocking of job creation endpoints with proper
HTTP responses and admin bypass functionality.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
from datetime import datetime, timezone

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from flask import Flask, jsonify, request
from maintenance_mode_service import MaintenanceModeService, MaintenanceInfo, MaintenanceStatus
from maintenance_mode_decorators import (
    maintenance_mode_check, block_job_creation, block_user_operations,
    maintenance_status_info, inject_maintenance_status
)
from models import UserRole


class TestMaintenanceModeIntegration(unittest.TestCase):
    """Test cases for maintenance mode integration with job endpoints"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.config['SECRET_KEY'] = 'test-secret-key'
        
        # Mock maintenance service
        self.mock_maintenance_service = Mock(spec=MaintenanceModeService)
        
        # Create test routes
        self._create_test_routes()
        
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
    
    def tearDown(self):
        """Clean up after tests"""
        self.app_context.pop()
    
    def _create_test_routes(self):
        """Create test routes for testing decorators"""
        
        @self.app.route('/api/test/job/create', methods=['POST'])
        @block_job_creation()
        def test_job_creation():
            return jsonify({'success': True, 'message': 'Job created'})
        
        @self.app.route('/api/test/job/retry', methods=['POST'])
        @block_job_creation(allow_admin_bypass=True)
        def test_job_retry():
            return jsonify({'success': True, 'message': 'Job retried'})
        
        @self.app.route('/test/user/operation')
        @block_user_operations()
        def test_user_operation():
            return 'Operation completed'
        
        @self.app.route('/api/test/admin/operation', methods=['POST'])
        @maintenance_mode_check(allow_admin_bypass=True, return_json=True)
        def test_admin_operation():
            return jsonify({'success': True, 'message': 'Admin operation completed'})
        
        @self.app.route('/test/no-bypass')
        @maintenance_mode_check(allow_admin_bypass=False)
        def test_no_bypass():
            return 'No bypass operation'
    
    def test_job_creation_blocked_during_maintenance(self):
        """Test job creation is blocked during maintenance mode"""
        # Setup maintenance mode enabled
        maintenance_info = MaintenanceInfo(
            enabled=True,
            reason="System upgrade in progress",
            status=MaintenanceStatus.ACTIVE,
            enabled_at=datetime.now(timezone.utc),
            disabled_at=None,
            last_updated=datetime.now(timezone.utc),
            source="database"
        )
        
        self.mock_maintenance_service.is_maintenance_mode.return_value = True
        self.mock_maintenance_service.get_maintenance_reason.return_value = "System upgrade in progress"
        self.mock_maintenance_service.get_maintenance_status.return_value = maintenance_info
        
        # Attach maintenance service to app
        self.app.maintenance_service = self.mock_maintenance_service
        
        # Test job creation endpoint
        response = self.client.post('/api/test/job/create')
        
        self.assertEqual(response.status_code, 503)
        data = response.get_json()
        self.assertFalse(data['success'])
        self.assertTrue(data['maintenance_mode'])
        self.assertEqual(data['maintenance_reason'], "Job creation is temporarily disabled during maintenance.")
        self.assertIn('temporarily disabled', data['message'])
    
    def test_job_creation_allowed_when_not_in_maintenance(self):
        """Test job creation is allowed when not in maintenance mode"""
        # Setup maintenance mode disabled
        self.mock_maintenance_service.is_maintenance_mode.return_value = False
        
        # Attach maintenance service to app
        self.app.maintenance_service = self.mock_maintenance_service
        
        # Test job creation endpoint
        response = self.client.post('/api/test/job/create')
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['message'], 'Job created')
    
    @patch('flask_login.current_user')
    def test_admin_bypass_during_maintenance(self, mock_current_user):
        """Test admin users can bypass maintenance mode"""
        # Setup admin user
        mock_current_user.id = 1
        mock_current_user.role = UserRole.ADMIN
        
        # Setup maintenance mode enabled
        self.mock_maintenance_service.is_maintenance_mode.return_value = True
        self.mock_maintenance_service.get_maintenance_reason.return_value = "Scheduled maintenance"
        
        # Attach maintenance service to app
        self.app.maintenance_service = self.mock_maintenance_service
        
        # Test admin operation endpoint
        response = self.client.post('/api/test/admin/operation')
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['message'], 'Admin operation completed')
    
    @patch('flask_login.current_user')
    def test_regular_user_blocked_during_maintenance(self, mock_current_user):
        """Test regular users are blocked during maintenance mode"""
        # Setup regular user
        mock_current_user.id = 2
        mock_current_user.role = UserRole.REVIEWER
        
        # Setup maintenance mode enabled
        self.mock_maintenance_service.is_maintenance_mode.return_value = True
        self.mock_maintenance_service.get_maintenance_reason.return_value = "Database maintenance"
        
        # Attach maintenance service to app
        self.app.maintenance_service = self.mock_maintenance_service
        
        # Test admin operation endpoint (should be blocked for regular user)
        response = self.client.post('/api/test/admin/operation')
        
        self.assertEqual(response.status_code, 503)
        data = response.get_json()
        self.assertFalse(data['success'])
        self.assertTrue(data['maintenance_mode'])
        self.assertEqual(data['maintenance_reason'], "Database maintenance")
    
    def test_no_bypass_blocks_all_users(self):
        """Test no bypass option blocks all users including admins"""
        # Setup maintenance mode enabled
        self.mock_maintenance_service.is_maintenance_mode.return_value = True
        self.mock_maintenance_service.get_maintenance_reason.return_value = "Critical maintenance"
        
        # Attach maintenance service to app
        self.app.maintenance_service = self.mock_maintenance_service
        
        with patch('flask_login.current_user') as mock_current_user:
            # Setup admin user
            mock_current_user.id = 1
            mock_current_user.role = UserRole.ADMIN
            
            # Test no-bypass endpoint
            response = self.client.get('/test/no-bypass')
            
            self.assertEqual(response.status_code, 503)
            # This should return HTML response
            self.assertIn(b'maintenance', response.data.lower())
    
    def test_html_response_for_web_endpoints(self):
        """Test HTML response is returned for web endpoints"""
        # Setup maintenance mode enabled
        self.mock_maintenance_service.is_maintenance_mode.return_value = True
        self.mock_maintenance_service.get_maintenance_reason.return_value = "Scheduled downtime"
        
        # Attach maintenance service to app
        self.app.maintenance_service = self.mock_maintenance_service
        
        # Test web endpoint
        response = self.client.get('/test/user/operation')
        
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.content_type, 'text/html; charset=utf-8')
        self.assertIn(b'maintenance', response.data.lower())
    
    def test_custom_maintenance_message(self):
        """Test custom maintenance message override"""
        # Setup maintenance mode enabled
        self.mock_maintenance_service.is_maintenance_mode.return_value = True
        self.mock_maintenance_service.get_maintenance_reason.return_value = "Original reason"
        
        # Create route with custom message
        @self.app.route('/api/test/custom-message', methods=['POST'])
        @maintenance_mode_check(custom_message="Custom maintenance message", return_json=True)
        def test_custom_message():
            return jsonify({'success': True})
        
        # Attach maintenance service to app
        self.app.maintenance_service = self.mock_maintenance_service
        
        # Test endpoint with custom message
        response = self.client.post('/api/test/custom-message')
        
        self.assertEqual(response.status_code, 503)
        data = response.get_json()
        self.assertEqual(data['maintenance_reason'], "Custom maintenance message")
    
    def test_no_maintenance_service_allows_operation(self):
        """Test operations are allowed when maintenance service is not available"""
        # Don't attach maintenance service to app
        
        # Test job creation endpoint
        response = self.client.post('/api/test/job/create')
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['message'], 'Job created')
    
    def test_maintenance_service_error_allows_operation(self):
        """Test operations are allowed when maintenance service raises error"""
        # Setup maintenance service to raise exception
        self.mock_maintenance_service.is_maintenance_mode.side_effect = Exception("Service error")
        
        # Attach maintenance service to app
        self.app.maintenance_service = self.mock_maintenance_service
        
        # Test job creation endpoint
        response = self.client.post('/api/test/job/create')
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['message'], 'Job created')
    
    def test_maintenance_status_info_function(self):
        """Test maintenance status info function"""
        # Setup maintenance mode enabled
        maintenance_info = MaintenanceInfo(
            enabled=True,
            reason="Test maintenance",
            status=MaintenanceStatus.ACTIVE,
            enabled_at=datetime.now(timezone.utc),
            disabled_at=None,
            last_updated=datetime.now(timezone.utc),
            source="database"
        )
        
        self.mock_maintenance_service.get_maintenance_status.return_value = maintenance_info
        
        # Attach maintenance service to app
        self.app.maintenance_service = self.mock_maintenance_service
        
        # Test status info function
        status_info = maintenance_status_info()
        
        self.assertTrue(status_info['maintenance_mode'])
        self.assertEqual(status_info['maintenance_reason'], "Test maintenance")
        self.assertEqual(status_info['maintenance_status'], "active")
        self.assertTrue(status_info['service_available'])
    
    def test_maintenance_status_info_no_service(self):
        """Test maintenance status info when service is not available"""
        # Don't attach maintenance service to app
        
        # Test status info function
        status_info = maintenance_status_info()
        
        self.assertFalse(status_info['maintenance_mode'])
        self.assertIsNone(status_info['maintenance_reason'])
        self.assertFalse(status_info['service_available'])
    
    def test_inject_maintenance_status_context_processor(self):
        """Test template context processor for maintenance status"""
        # Setup maintenance mode enabled
        maintenance_info = MaintenanceInfo(
            enabled=True,
            reason="Template test",
            status=MaintenanceStatus.ACTIVE,
            enabled_at=datetime.now(timezone.utc),
            disabled_at=None,
            last_updated=datetime.now(timezone.utc),
            source="database"
        )
        
        self.mock_maintenance_service.get_maintenance_status.return_value = maintenance_info
        
        # Attach maintenance service to app
        self.app.maintenance_service = self.mock_maintenance_service
        
        # Test context processor
        context = inject_maintenance_status()
        
        self.assertIn('maintenance_status', context)
        maintenance_status = context['maintenance_status']
        self.assertTrue(maintenance_status['maintenance_mode'])
        self.assertEqual(maintenance_status['maintenance_reason'], "Template test")


if __name__ == '__main__':
    unittest.main()
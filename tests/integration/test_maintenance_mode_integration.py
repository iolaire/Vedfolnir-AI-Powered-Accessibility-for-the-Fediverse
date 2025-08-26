# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integration tests for MaintenanceModeMiddleware with Flask application

Tests middleware integration with real Flask routes and existing systems.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
import json

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from flask import Flask, jsonify
from flask_login import login_required
from maintenance_mode_middleware import MaintenanceModeMiddleware
from enhanced_maintenance_mode_service import EnhancedMaintenanceModeService, MaintenanceMode, MaintenanceStatus
from models import User, UserRole


class TestMaintenanceModeIntegration(unittest.TestCase):
    """Integration tests for maintenance mode middleware with Flask application"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create Flask app for testing
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.config['SECRET_KEY'] = 'test-secret-key'
        
        # Mock configuration service
        self.mock_config_service = Mock()
        
        # Create maintenance service
        self.maintenance_service = EnhancedMaintenanceModeService(self.mock_config_service)
        
        # Create middleware and integrate with app
        self.middleware = MaintenanceModeMiddleware(self.app, self.maintenance_service)
        
        # Add test routes
        self._add_test_routes()
        
        # Create test client
        self.client = self.app.test_client()
    
    def _add_test_routes(self):
        """Add test routes to the Flask app"""
        
        @self.app.route('/test/normal')
        def normal_route():
            return jsonify({'message': 'Normal route accessed'})
        
        @self.app.route('/test/caption/generate', methods=['POST'])
        def caption_generate():
            return jsonify({'message': 'Caption generation started'})
        
        @self.app.route('/admin/test')
        def admin_route():
            return jsonify({'message': 'Admin route accessed'})
        
        @self.app.route('/static/test.css')
        def static_file():
            return 'CSS content'
        
        @self.app.route('/health')
        def health_check():
            return jsonify({'status': 'healthy'})
    
    def test_middleware_integration_normal_operation(self):
        """Test middleware integration during normal operation"""
        # Ensure maintenance is inactive
        self.maintenance_service.disable_maintenance()
        
        # Test normal route access
        response = self.client.get('/test/normal')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.get_data(as_text=True))
        self.assertEqual(data['message'], 'Normal route accessed')
    
    def test_middleware_integration_maintenance_active(self):
        """Test middleware integration when maintenance is active"""
        # Enable maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="Test maintenance",
            duration=30,
            mode=MaintenanceMode.NORMAL
        )
        
        # Test that caption generation is blocked
        response = self.client.post('/test/caption/generate')
        self.assertEqual(response.status_code, 503)
        
        data = json.loads(response.get_data(as_text=True))
        self.assertEqual(data['error'], 'Service Unavailable')
        self.assertTrue(data['maintenance_active'])
        self.assertEqual(data['maintenance_mode'], 'normal')
    
    def test_middleware_integration_static_files_allowed(self):
        """Test that static files are allowed during maintenance"""
        # Enable maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="Test maintenance",
            mode=MaintenanceMode.NORMAL
        )
        
        # Test that static files are still accessible
        response = self.client.get('/static/test.css')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_data(as_text=True), 'CSS content')
    
    def test_middleware_integration_health_check_allowed(self):
        """Test that health checks are allowed during maintenance"""
        # Enable maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="Test maintenance",
            mode=MaintenanceMode.NORMAL
        )
        
        # Test that health checks are still accessible
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.get_data(as_text=True))
        self.assertEqual(data['status'], 'healthy')
    
    def test_middleware_integration_admin_bypass(self):
        """Test admin user bypass during maintenance"""
        # Enable maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="Test maintenance",
            mode=MaintenanceMode.NORMAL
        )
        
        # Mock admin user
        admin_user = Mock()
        admin_user.role = UserRole.ADMIN
        admin_user.id = 1
        admin_user.username = 'admin'
        
        # Test admin route access with admin user
        with patch.object(self.middleware, '_get_current_user', return_value=admin_user):
            response = self.client.get('/admin/test')
            self.assertEqual(response.status_code, 200)
            
            data = json.loads(response.get_data(as_text=True))
            self.assertEqual(data['message'], 'Admin route accessed')
    
    def test_middleware_integration_emergency_mode(self):
        """Test middleware integration in emergency maintenance mode"""
        # Enable emergency maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="Emergency maintenance",
            mode=MaintenanceMode.EMERGENCY
        )
        
        # Test that normal routes are blocked in emergency mode
        response = self.client.get('/test/normal')
        self.assertEqual(response.status_code, 503)
        
        data = json.loads(response.get_data(as_text=True))
        self.assertEqual(data['maintenance_mode'], 'emergency')
    
    def test_middleware_integration_test_mode(self):
        """Test middleware integration in test maintenance mode"""
        # Enable test maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="Test maintenance",
            mode=MaintenanceMode.TEST
        )
        
        # Test that operations are allowed in test mode (simulation only)
        response = self.client.post('/test/caption/generate')
        self.assertEqual(response.status_code, 200)  # Should be allowed in test mode
        
        data = json.loads(response.get_data(as_text=True))
        self.assertEqual(data['message'], 'Caption generation started')
    
    def test_middleware_integration_error_handling(self):
        """Test middleware error handling during integration"""
        # Mock maintenance service to raise exception
        with patch.object(self.maintenance_service, 'get_maintenance_status', side_effect=Exception("Test error")):
            # Request should still succeed (fail-safe behavior)
            response = self.client.get('/test/normal')
            self.assertEqual(response.status_code, 200)
            
            data = json.loads(response.get_data(as_text=True))
            self.assertEqual(data['message'], 'Normal route accessed')
    
    def test_middleware_integration_statistics(self):
        """Test middleware statistics collection during integration"""
        # Enable maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="Test maintenance",
            mode=MaintenanceMode.NORMAL
        )
        
        # Make some requests that should be blocked
        self.client.post('/test/caption/generate')
        self.client.post('/test/caption/generate')
        
        # Check middleware statistics
        stats = self.middleware.get_middleware_stats()
        self.assertIn('middleware_stats', stats)
        self.assertGreater(stats['middleware_stats']['total_requests'], 0)
        self.assertGreater(stats['middleware_stats']['blocked_requests'], 0)
    
    def test_middleware_integration_maintenance_response_headers(self):
        """Test maintenance response headers during integration"""
        # Enable maintenance mode with duration
        self.maintenance_service.enable_maintenance(
            reason="Test maintenance",
            duration=60,  # 60 minutes
            mode=MaintenanceMode.NORMAL
        )
        
        # Test blocked request
        response = self.client.post('/test/caption/generate')
        self.assertEqual(response.status_code, 503)
        
        # Check maintenance headers
        self.assertEqual(response.headers.get('X-Maintenance-Active'), 'true')
        self.assertEqual(response.headers.get('X-Maintenance-Mode'), 'normal')
        self.assertEqual(response.headers.get('Retry-After'), '3600')  # 60 minutes in seconds
    
    def test_middleware_integration_with_existing_decorators(self):
        """Test middleware integration with existing route decorators"""
        
        # Add a route with decorators
        @self.app.route('/test/decorated')
        @login_required
        def decorated_route():
            return jsonify({'message': 'Decorated route accessed'})
        
        # Enable maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="Test maintenance",
            mode=MaintenanceMode.NORMAL
        )
        
        # Test that maintenance middleware runs before other decorators
        response = self.client.get('/test/decorated')
        
        # Should get maintenance response, not login redirect
        self.assertEqual(response.status_code, 503)
        
        data = json.loads(response.get_data(as_text=True))
        self.assertTrue(data['maintenance_active'])


if __name__ == '__main__':
    unittest.main()
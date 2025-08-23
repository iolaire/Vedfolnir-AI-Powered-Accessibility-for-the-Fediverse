# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test Admin Dashboard Web Interface for Multi-Tenant Caption Management
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestAdminDashboardInterface(unittest.TestCase):
    """Test the admin dashboard web interface"""
    
    def setUp(self):
        """Set up test environment"""
        self.mock_config = Mock()
        self.mock_config.DATABASE_URL = "sqlite:///:memory:"
        self.mock_config.REDIS_URL = "redis://localhost:6379/0"
        
        self.mock_db_manager = Mock()
        self.mock_session = Mock()
        
        # Mock context manager for get_session
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=self.mock_session)
        mock_context.__exit__ = Mock(return_value=None)
        self.mock_db_manager.get_session.return_value = mock_context
    
    def test_dashboard_template_structure(self):
        """Test that the dashboard template has the required structure"""
        template_path = os.path.join(os.path.dirname(__file__), '..', 'admin', 'templates', 'dashboard.html')
        
        self.assertTrue(os.path.exists(template_path), "Dashboard template should exist")
        
        with open(template_path, 'r') as f:
            content = f.read()
        
        # Check for key dashboard components
        required_elements = [
            'Multi-Tenant Caption Management Dashboard',
            'activeJobsCount',
            'completedTodayCount',
            'failedJobsCount',
            'systemLoadValue',
            'activeJobsTable',
            'alertsList',
            'systemConfigForm',
            'real-time-indicator'
        ]
        
        for element in required_elements:
            self.assertIn(element, content, f"Dashboard should contain {element}")
    
    def test_modal_components_exist(self):
        """Test that all modal components exist"""
        modal_files = [
            'job_details_modal.html',
            'bulk_actions_modal.html',
            'user_limits_modal.html',
            'system_maintenance_modal.html'
        ]
        
        for modal_file in modal_files:
            modal_path = os.path.join(os.path.dirname(__file__), '..', 'admin', 'templates', 'components', modal_file)
            self.assertTrue(os.path.exists(modal_path), f"Modal component {modal_file} should exist")
    
    def test_javascript_file_exists(self):
        """Test that the admin dashboard JavaScript file exists"""
        js_path = os.path.join(os.path.dirname(__file__), '..', 'admin', 'static', 'js', 'admin_dashboard.js')
        
        self.assertTrue(os.path.exists(js_path), "Admin dashboard JavaScript should exist")
        
        with open(js_path, 'r') as f:
            content = f.read()
        
        # Check for key JavaScript functions
        required_functions = [
            'initializeDashboard',
            'connectWebSocket',
            'refreshDashboard',
            'cancelJob',
            'setPriority',
            'restartJob',
            'viewJobDetails',
            'showBulkActions',
            'acknowledgeAlert',
            'saveSystemConfig'
        ]
        
        for function in required_functions:
            self.assertIn(f'function {function}', content, f"JavaScript should contain {function} function")
    
    def test_css_file_exists(self):
        """Test that the admin dashboard CSS file exists"""
        css_path = os.path.join(os.path.dirname(__file__), '..', 'admin', 'static', 'css', 'admin_dashboard.css')
        
        self.assertTrue(os.path.exists(css_path), "Admin dashboard CSS should exist")
        
        with open(css_path, 'r') as f:
            content = f.read()
        
        # Check for key CSS classes
        required_classes = [
            '.real-time-indicator',
            '.system-metric',
            '.job-status-badge',
            '.job-controls',
            '.alert-item',
            '.user-item'
        ]
        
        for css_class in required_classes:
            self.assertIn(css_class, content, f"CSS should contain {css_class} class")
    
    @patch('admin.routes.dashboard.current_app')
    @patch('admin.routes.dashboard.current_user')
    def test_dashboard_route_helper_functions(self, mock_current_user, mock_current_app):
        """Test the dashboard route helper functions"""
        # Mock admin user
        mock_current_user.id = 1
        mock_current_user.role.value = 'admin'
        
        # Mock app config
        mock_current_app.config = {'db_manager': self.mock_db_manager}
        mock_current_app.logger = Mock()
        
        # Import the helper functions
        from admin.routes.dashboard import get_system_metrics, get_active_jobs_for_admin, get_system_alerts, get_system_configuration
        
        # Test get_system_metrics with mocked services
        with patch('admin.routes.dashboard.WebCaptionGenerationService') as mock_service_class:
            with patch('admin.routes.dashboard.SystemMonitor') as mock_monitor_class:
                mock_service = Mock()
                mock_service.get_system_metrics.return_value = {
                    'active_jobs': 5,
                    'queued_jobs': 2,
                    'completed_today': 10,
                    'failed_jobs': 1
                }
                mock_service_class.return_value = mock_service
                
                mock_monitor = Mock()
                mock_monitor.get_system_health.return_value = {'status': 'healthy'}
                mock_monitor.get_performance_metrics.return_value = {'cpu_usage_percent': 25}
                mock_monitor_class.return_value = mock_monitor
                
                metrics = get_system_metrics(1)
                
                self.assertIsInstance(metrics, dict)
                self.assertIn('active_jobs', metrics)
                self.assertEqual(metrics['active_jobs'], 5)
        
        # Test get_active_jobs_for_admin with mocked service
        with patch('admin.routes.dashboard.WebCaptionGenerationService') as mock_service_class:
            mock_service = Mock()
            mock_service.get_all_active_jobs.return_value = [
                {
                    'task_id': 'test-task-123',
                    'username': 'testuser',
                    'user_email': 'test@example.com',
                    'platform_type': 'mastodon',
                    'status': 'running'
                }
            ]
            mock_service_class.return_value = mock_service
            
            jobs = get_active_jobs_for_admin(1)
            
            self.assertIsInstance(jobs, list)
            self.assertEqual(len(jobs), 1)
            self.assertEqual(jobs[0]['task_id'], 'test-task-123')
        
        # Test get_system_alerts with mocked alert manager
        with patch('admin.routes.dashboard.AlertManager') as mock_alert_class:
            mock_alert_manager = Mock()
            mock_alert_manager.get_active_alerts.return_value = [
                {
                    'id': 'alert-1',
                    'title': 'Test Alert',
                    'message': 'Test message',
                    'severity': 'warning'
                }
            ]
            mock_alert_class.return_value = mock_alert_manager
            
            alerts = get_system_alerts()
            
            self.assertIsInstance(alerts, list)
            self.assertEqual(len(alerts), 1)
            self.assertEqual(alerts[0]['title'], 'Test Alert')
        
        # Test get_system_configuration
        from models import SystemConfiguration
        
        # Mock database query
        mock_config_items = [
            Mock(key='max_concurrent_jobs', value='5'),
            Mock(key='job_timeout_minutes', value='30')
        ]
        self.mock_session.query.return_value.all.return_value = mock_config_items
        
        config = get_system_configuration()
        
        self.assertIsInstance(config, dict)
        self.assertEqual(config['max_concurrent_jobs'], 5)
        self.assertEqual(config['job_timeout_minutes'], 30)
    
    def test_websocket_routes_exist(self):
        """Test that WebSocket routes file exists"""
        websocket_path = os.path.join(os.path.dirname(__file__), '..', 'admin', 'routes', 'websocket_routes.py')
        
        self.assertTrue(os.path.exists(websocket_path), "WebSocket routes should exist")
        
        with open(websocket_path, 'r') as f:
            content = f.read()
        
        # Check for WebSocket handler class
        self.assertIn('class AdminDashboardWebSocket', content)
        self.assertIn('def register_websocket_routes', content)
    
    def test_api_routes_enhanced(self):
        """Test that API routes have been enhanced for multi-tenant management"""
        api_path = os.path.join(os.path.dirname(__file__), '..', 'admin', 'routes', 'admin_api.py')
        
        self.assertTrue(os.path.exists(api_path), "Admin API routes should exist")
        
        with open(api_path, 'r') as f:
            content = f.read()
        
        # Check for new API endpoints
        required_endpoints = [
            '/api/system-metrics',
            '/api/jobs/active',
            '/api/jobs/<task_id>/cancel',
            '/api/jobs/<task_id>/priority',
            '/api/jobs/<task_id>/restart',
            '/api/jobs/<task_id>/details',
            '/api/alerts',
            '/api/config'
        ]
        
        for endpoint in required_endpoints:
            self.assertIn(endpoint, content, f"API should contain {endpoint} endpoint")
    
    def test_dashboard_accessibility_features(self):
        """Test that the dashboard includes accessibility features"""
        template_path = os.path.join(os.path.dirname(__file__), '..', 'admin', 'templates', 'dashboard.html')
        
        with open(template_path, 'r') as f:
            content = f.read()
        
        # Check for accessibility attributes
        accessibility_features = [
            'aria-label',
            'aria-labelledby',
            'aria-hidden',
            'role="progressbar"',
            'aria-valuenow',
            'aria-valuemin',
            'aria-valuemax',
            'title='
        ]
        
        for feature in accessibility_features:
            self.assertIn(feature, content, f"Dashboard should include {feature} for accessibility")
    
    def test_responsive_design_classes(self):
        """Test that the dashboard includes responsive design classes"""
        css_path = os.path.join(os.path.dirname(__file__), '..', 'admin', 'static', 'css', 'admin_dashboard.css')
        
        with open(css_path, 'r') as f:
            content = f.read()
        
        # Check for responsive breakpoints
        responsive_features = [
            '@media (max-width: 768px)',
            '@media (max-width: 576px)',
            '@media (prefers-color-scheme: dark)',
            '@media (prefers-contrast: high)',
            '@media (prefers-reduced-motion: reduce)',
            '@media print'
        ]
        
        for feature in responsive_features:
            self.assertIn(feature, content, f"CSS should include {feature} for responsive design")

if __name__ == '__main__':
    unittest.main()
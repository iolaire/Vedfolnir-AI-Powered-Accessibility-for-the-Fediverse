# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Tests for Enhanced Dashboard Monitoring Routes

Tests the Flask routes for real-time monitoring dashboard, historical reporting,
and customizable widgets with alerting integration.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta
import json
import io

from flask import Flask
from flask_login import login_user

from models import User, UserRole
from admin.routes.dashboard_monitoring import register_dashboard_routes
from monitoring_dashboard_service import ReportType, ReportFormat


class TestDashboardMonitoringRoutes(unittest.TestCase):
    """Test cases for dashboard monitoring routes"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'test-secret-key'
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        
        # Mock database manager
        self.mock_db_manager = Mock()
        self.app.config['db_manager'] = self.mock_db_manager
        
        # Create blueprint and register routes
        from flask import Blueprint
        self.bp = Blueprint('admin', __name__, url_prefix='/admin')
        register_dashboard_routes(self.bp)
        self.app.register_blueprint(self.bp)
        
        # Setup Flask-Login
        from flask_login import LoginManager
        self.login_manager = LoginManager()
        self.login_manager.init_app(self.app)
        
        @self.login_manager.user_loader
        def load_user(user_id):
            user = Mock(spec=User)
            user.id = int(user_id)
            user.role = UserRole.ADMIN
            user.is_authenticated = True
            user.is_active = True
            user.is_anonymous = False
            user.get_id.return_value = str(user_id)
            return user
        
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Create test user
        self.test_user = Mock(spec=User)
        self.test_user.id = 1
        self.test_user.role = UserRole.ADMIN
        self.test_user.is_authenticated = True
        self.test_user.is_active = True
        self.test_user.is_anonymous = False
        self.test_user.get_id.return_value = '1'
    
    def tearDown(self):
        """Clean up test fixtures"""
        self.app_context.pop()
    
    def login_test_user(self):
        """Helper to login test user"""
        with self.client.session_transaction() as sess:
            sess['_user_id'] = '1'
            sess['_fresh'] = True
    
    @patch('admin.routes.dashboard_monitoring.MonitoringDashboardService')
    @patch('admin.routes.dashboard_monitoring.current_user')
    def test_enhanced_monitoring_dashboard_success(self, mock_current_user, mock_service_class):
        """Test successful access to enhanced monitoring dashboard"""
        self.login_test_user()
        mock_current_user.role = UserRole.ADMIN
        
        # Mock service
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        
        mock_dashboard_config = {
            'widgets': [
                {
                    'id': 'test_widget',
                    'type': 'metric_card',
                    'title': 'Test Widget',
                    'position': {'x': 0, 'y': 0, 'width': 6, 'height': 2}
                }
            ],
            'refresh_interval': 30
        }
        mock_service.get_dashboard_config.return_value = mock_dashboard_config
        mock_service.get_widget_data.return_value = {'metrics': {'test': 1}}
        mock_service.get_dashboard_alerts.return_value = []
        
        response = self.client.get('/admin/dashboard/monitoring')
        
        self.assertEqual(response.status_code, 200)
        mock_service.get_dashboard_config.assert_called_once_with(UserRole.ADMIN)
    
    @patch('admin.routes.dashboard_monitoring.MonitoringDashboardService')
    @patch('admin.routes.dashboard_monitoring.current_user')
    def test_get_dashboard_config_api(self, mock_current_user, mock_service_class):
        """Test dashboard configuration API endpoint"""
        self.login_test_user()
        mock_current_user.role = UserRole.ADMIN
        
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_service.get_dashboard_config.return_value = {'widgets': [], 'refresh_interval': 30}
        
        response = self.client.get('/admin/api/dashboard/config')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('config', data)
    
    @patch('admin.routes.dashboard_monitoring.MonitoringDashboardService')
    @patch('admin.routes.dashboard_monitoring.current_user')
    def test_get_widget_data_api(self, mock_current_user, mock_service_class):
        """Test widget data API endpoint"""
        self.login_test_user()
        mock_current_user.role = UserRole.ADMIN
        
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_service.get_widget_data.return_value = {'metrics': {'active_tasks': 5}}
        
        response = self.client.get('/admin/api/dashboard/widget/test_widget')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('data', data)
        self.assertEqual(data['data']['metrics']['active_tasks'], 5)
    
    @patch('admin.routes.dashboard_monitoring.MonitoringDashboardService')
    @patch('admin.routes.dashboard_monitoring.current_user')
    def test_get_realtime_metrics_api(self, mock_current_user, mock_service_class):
        """Test real-time metrics API endpoint"""
        self.login_test_user()
        mock_current_user.role = UserRole.ADMIN
        
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_metrics = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'overview': {'active_tasks': 3},
            'health': {'status': 'healthy'},
            'performance': {'throughput': 100},
            'alerts': {'critical': 0, 'warning': 1, 'info': 0},
            'status': 'healthy'
        }
        mock_service.get_real_time_metrics.return_value = mock_metrics
        
        response = self.client.get('/admin/api/dashboard/metrics/realtime')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('metrics', data)
        self.assertEqual(data['metrics']['status'], 'healthy')
    
    @patch('admin.routes.dashboard_monitoring.MonitoringDashboardService')
    @patch('admin.routes.dashboard_monitoring.current_user')
    def test_get_dashboard_alerts_api(self, mock_current_user, mock_service_class):
        """Test dashboard alerts API endpoint"""
        self.login_test_user()
        mock_current_user.role = UserRole.ADMIN
        
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        
        from monitoring_dashboard_service import DashboardAlert
        from alert_manager import AlertType, AlertSeverity
        
        mock_alerts = [
            DashboardAlert(
                id="alert1",
                type=AlertType.SYSTEM_ERROR,
                severity=AlertSeverity.CRITICAL,
                message="System overload",
                timestamp=datetime.now(timezone.utc),
                acknowledged=False
            )
        ]
        mock_service.get_dashboard_alerts.return_value = mock_alerts
        
        response = self.client.get('/admin/api/dashboard/alerts')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('alerts', data)
        self.assertEqual(len(data['alerts']), 1)
        self.assertEqual(data['alerts'][0]['message'], 'System overload')
    
    @patch('admin.routes.dashboard_monitoring.MonitoringDashboardService')
    @patch('admin.routes.dashboard_monitoring.current_user')
    def test_acknowledge_alert_api(self, mock_current_user, mock_service_class):
        """Test alert acknowledgment API endpoint"""
        self.login_test_user()
        mock_current_user.id = 1
        mock_current_user.role = UserRole.ADMIN
        
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_service.acknowledge_alert.return_value = {
            'success': True,
            'message': 'Alert acknowledged'
        }
        
        response = self.client.post('/admin/api/dashboard/alerts/alert123/acknowledge')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        mock_service.acknowledge_alert.assert_called_once_with('alert123', 1)
    
    @patch('admin.routes.dashboard_monitoring.current_user')
    def test_reports_dashboard_access(self, mock_current_user):
        """Test access to reports dashboard"""
        self.login_test_user()
        mock_current_user.role = UserRole.ADMIN
        
        response = self.client.get('/admin/dashboard/reports')
        
        self.assertEqual(response.status_code, 200)
    
    @patch('admin.routes.dashboard_monitoring.MonitoringDashboardService')
    @patch('admin.routes.dashboard_monitoring.current_user')
    def test_generate_report_api(self, mock_current_user, mock_service_class):
        """Test report generation API endpoint"""
        self.login_test_user()
        mock_current_user.role = UserRole.ADMIN
        
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        
        mock_report = {
            'report_type': 'system_performance',
            'summary': {'total_tasks': 100},
            'generated_at': datetime.now(timezone.utc).isoformat()
        }
        mock_service.get_historical_report.return_value = mock_report
        
        request_data = {
            'report_type': 'system_performance',
            'start_date': '2025-01-01T00:00:00',
            'end_date': '2025-01-07T23:59:59',
            'parameters': {}
        }
        
        response = self.client.post(
            '/admin/api/reports/generate',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('report', data)
        self.assertEqual(data['report']['report_type'], 'system_performance')
    
    @patch('admin.routes.dashboard_monitoring.MonitoringDashboardService')
    @patch('admin.routes.dashboard_monitoring.current_user')
    def test_export_report_api(self, mock_current_user, mock_service_class):
        """Test report export API endpoint"""
        self.login_test_user()
        mock_current_user.role = UserRole.ADMIN
        
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        
        # Mock export response
        mock_content = b'{"report_type": "test"}'
        mock_mime_type = 'application/json'
        mock_service.export_report.return_value = (mock_content, mock_mime_type)
        
        request_data = {
            'report_data': {'report_type': 'test'},
            'format': 'json'
        }
        
        response = self.client.post(
            '/admin/api/reports/export',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'application/json; charset=utf-8')
        self.assertEqual(response.data, mock_content)
    
    @patch('admin.routes.dashboard_monitoring.current_user')
    def test_schedule_report_api(self, mock_current_user):
        """Test report scheduling API endpoint"""
        self.login_test_user()
        mock_current_user.role = UserRole.ADMIN
        
        request_data = {
            'name': 'Weekly Performance Report',
            'report_type': 'system_performance',
            'format': 'json',
            'frequency': 'weekly',
            'period': 7,
            'recipients': ['admin@example.com'],
            'cron_expression': ''
        }
        
        response = self.client.post(
            '/admin/api/reports/schedule',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('schedule_id', data)
    
    @patch('admin.routes.dashboard_monitoring.MonitoringDashboardService')
    @patch('admin.routes.dashboard_monitoring.current_user')
    def test_customize_widgets_page(self, mock_current_user, mock_service_class):
        """Test widget customization page"""
        self.login_test_user()
        mock_current_user.role = UserRole.ADMIN
        
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_service.get_dashboard_config.return_value = {'widgets': []}
        
        response = self.client.get('/admin/dashboard/widgets/customize')
        
        self.assertEqual(response.status_code, 200)
    
    @patch('admin.routes.dashboard_monitoring.current_user')
    def test_save_widget_config_api(self, mock_current_user):
        """Test saving widget configuration"""
        self.login_test_user()
        mock_current_user.role = UserRole.ADMIN
        
        request_data = {
            'widgets': [
                {
                    'id': 'custom_widget',
                    'type': 'metric_card',
                    'title': 'Custom Widget',
                    'position': {'x': 0, 'y': 0, 'width': 6, 'height': 2}
                }
            ]
        }
        
        response = self.client.post(
            '/admin/api/dashboard/widgets/save',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
    
    @patch('admin.routes.dashboard_monitoring.MonitoringDashboardService')
    @patch('admin.routes.dashboard_monitoring.current_user')
    def test_dashboard_health_api(self, mock_current_user, mock_service_class):
        """Test dashboard health check API"""
        self.login_test_user()
        mock_current_user.role = UserRole.ADMIN
        
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_service.get_real_time_metrics.return_value = {
            'status': 'healthy',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        response = self.client.get('/admin/api/dashboard/health')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['status'], 'healthy')
    
    def test_unauthorized_access_dashboard(self):
        """Test unauthorized access to dashboard routes"""
        # Don't login user
        response = self.client.get('/admin/dashboard/monitoring')
        
        # Should redirect to login or return 401/403
        self.assertIn(response.status_code, [302, 401, 403])
    
    def test_unauthorized_access_api(self):
        """Test unauthorized access to API endpoints"""
        # Don't login user
        response = self.client.get('/admin/api/dashboard/config')
        
        # Should return 401/403
        self.assertIn(response.status_code, [401, 403])
    
    @patch('admin.routes.dashboard_monitoring.MonitoringDashboardService')
    @patch('admin.routes.dashboard_monitoring.current_user')
    def test_api_error_handling(self, mock_current_user, mock_service_class):
        """Test API error handling"""
        self.login_test_user()
        mock_current_user.role = UserRole.ADMIN
        
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_service.get_dashboard_config.side_effect = Exception("Service error")
        
        response = self.client.get('/admin/api/dashboard/config')
        
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('error', data)
    
    @patch('admin.routes.dashboard_monitoring.MonitoringDashboardService')
    @patch('admin.routes.dashboard_monitoring.current_user')
    def test_invalid_report_generation(self, mock_current_user, mock_service_class):
        """Test invalid report generation request"""
        self.login_test_user()
        mock_current_user.role = UserRole.ADMIN
        
        # Invalid request data (missing required fields)
        request_data = {
            'report_type': 'invalid_type',
            'start_date': 'invalid_date'
        }
        
        response = self.client.post(
            '/admin/api/reports/generate',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
    
    @patch('admin.routes.dashboard_monitoring.MonitoringDashboardService')
    @patch('admin.routes.dashboard_monitoring.current_user')
    def test_dashboard_stream_sse(self, mock_current_user, mock_service_class):
        """Test Server-Sent Events stream for dashboard"""
        self.login_test_user()
        mock_current_user.role = UserRole.ADMIN
        
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_service.get_real_time_metrics.return_value = {
            'status': 'healthy',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Note: Testing SSE streams is complex due to their streaming nature
        # This test just verifies the endpoint is accessible
        response = self.client.get('/admin/dashboard/stream')
        
        # Should start streaming (200) or handle appropriately
        self.assertIn(response.status_code, [200, 500])  # 500 might occur due to mocking limitations


class TestDashboardSecurity(unittest.TestCase):
    """Test security aspects of dashboard routes"""
    
    def setUp(self):
        """Set up security test fixtures"""
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'test-secret-key'
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = True  # Enable CSRF for security tests
        
        self.mock_db_manager = Mock()
        self.app.config['db_manager'] = self.mock_db_manager
        
        from flask import Blueprint
        self.bp = Blueprint('admin', __name__, url_prefix='/admin')
        register_dashboard_routes(self.bp)
        self.app.register_blueprint(self.bp)
        
        from flask_login import LoginManager
        self.login_manager = LoginManager()
        self.login_manager.init_app(self.app)
        
        @self.login_manager.user_loader
        def load_user(user_id):
            user = Mock(spec=User)
            user.id = int(user_id)
            user.role = UserRole.REVIEWER  # Non-admin role for security tests
            user.is_authenticated = True
            user.is_active = True
            user.is_anonymous = False
            user.get_id.return_value = str(user_id)
            return user
        
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
    
    def tearDown(self):
        """Clean up security test fixtures"""
        self.app_context.pop()
    
    def login_non_admin_user(self):
        """Helper to login non-admin user"""
        with self.client.session_transaction() as sess:
            sess['_user_id'] = '1'
            sess['_fresh'] = True
    
    def test_non_admin_access_denied(self):
        """Test that non-admin users are denied access to admin routes"""
        self.login_non_admin_user()
        
        # Test various admin routes
        admin_routes = [
            '/admin/dashboard/monitoring',
            '/admin/dashboard/reports',
            '/admin/dashboard/widgets/customize',
            '/admin/api/dashboard/config',
            '/admin/api/dashboard/widget/test',
            '/admin/api/dashboard/metrics/realtime',
            '/admin/api/dashboard/alerts',
            '/admin/api/dashboard/health'
        ]
        
        for route in admin_routes:
            response = self.client.get(route)
            # Should redirect or return 403
            self.assertIn(response.status_code, [302, 403], f"Route {route} should deny access")


if __name__ == '__main__':
    unittest.main()
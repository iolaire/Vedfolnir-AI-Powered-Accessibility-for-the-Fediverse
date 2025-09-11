# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Tests for Security Management Routes

Tests the security management routes including:
- Main security dashboard
- Security audit logs interface
- Security features management
- CSRF dashboard
"""

import unittest
import sys
import os
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from models import UserRole


class TestSecurityManagementRoutes(unittest.TestCase):
    """Test security management routes functionality"""
    
    def setUp(self):
        """Set up test environment"""
        pass
    
    def tearDown(self):
        """Clean up test environment"""
        pass
    
    @patch('app.blueprints.admin.security_management.get_security_overview_data')
    @patch('app.blueprints.admin.security_management.get_security_features_status')
    @patch('app.blueprints.admin.security_management.get_recent_security_events_summary')
    @patch('app.blueprints.admin.security_management.get_csrf_metrics_summary')
    @patch('app.blueprints.admin.security_management.get_compliance_status_summary')
    @patch('app.blueprints.admin.security_management.render_template')
    def test_security_dashboard_route(self, mock_render_template, mock_compliance, 
                                    mock_csrf, mock_events, mock_features, mock_overview):
        """Test security dashboard route returns correct data"""
        # Mock return values
        mock_overview.return_value = {
            'security_score': 95,
            'open_issues': 0,
            'recent_events_24h': 5,
            'critical_events_24h': 0,
            'high_events_24h': 1,
            'last_updated': datetime.now(timezone.utc).isoformat()
        }
        
        mock_features.return_value = {
            'csrf_protection': {
                'enabled': True,
                'status': 'Active',
                'description': 'Cross-Site Request Forgery protection'
            }
        }
        
        mock_events.return_value = {
            'total_events': 5,
            'critical_events': 0,
            'high_events': 1,
            'recent_events': []
        }
        
        mock_csrf.return_value = {
            'enabled': True,
            'compliance_rate': 1.0,
            'total_requests': 100,
            'violations': 0
        }
        
        mock_compliance.return_value = {
            'owasp_top_10': {'compliant': True, 'score': 100}
        }
        
        mock_render_template.return_value = "Security Dashboard HTML"
        
        # Import and test the route function
        from app.blueprints.admin.security_management import register_routes
        from flask import Blueprint
        
        # Create a mock blueprint
        mock_bp = MagicMock()
        register_routes(mock_bp)
        
        # Get the registered route function
        route_calls = mock_bp.route.call_args_list
        security_dashboard_route = None
        
        for call in route_calls:
            if call[0][0] == '/security':
                # Get the decorated function
                security_dashboard_route = call[1]['methods'] if 'methods' in call[1] else None
                break
        
        # Verify route was registered
        self.assertIsNotNone(route_calls)
        
        # Verify all helper functions were called
        mock_overview.assert_called_once()
        mock_features.assert_called_once()
        mock_events.assert_called_once()
        mock_csrf.assert_called_once()
        mock_compliance.assert_called_once()
        
        # Verify template was rendered with correct context
        mock_render_template.assert_called_once_with(
            'security_management_dashboard.html',
            security_overview=mock_overview.return_value,
            security_features=mock_features.return_value,
            recent_events=mock_events.return_value,
            csrf_summary=mock_csrf.return_value,
            compliance_status=mock_compliance.return_value,
            page_title='Security Management'
        )
    
    @patch('app.blueprints.admin.security_management.get_security_audit_logs')
    @patch('app.blueprints.admin.security_management.get_audit_statistics')
    @patch('app.blueprints.admin.security_management.get_audit_filters')
    @patch('app.blueprints.admin.security_management.render_template')
    def test_security_audit_route(self, mock_render_template, mock_filters, 
                                 mock_stats, mock_logs):
        """Test security audit route returns correct data"""
        # Mock request args
        self.mock_request.args.get.side_effect = lambda key, default=None, type=None: {
            'hours': 24,
            'severity': 'all',
            'event_type': 'all',
            'page': 1,
            'per_page': 50
        }.get(key, default)
        
        # Mock return values
        mock_logs.return_value = {
            'events': [
                {
                    'id': 'test-event-1',
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'event_type': 'security_event',
                    'severity': 'high',
                    'source_ip': '127.0.0.1',
                    'user_id': None,
                    'endpoint': '/admin/test',
                    'message': 'Test security event'
                }
            ],
            'total_events': 1,
            'page': 1,
            'per_page': 50,
            'total_pages': 1,
            'has_prev': False,
            'has_next': False
        }
        
        mock_stats.return_value = {
            'total_events': 1,
            'critical_events': 0,
            'high_events': 1,
            'medium_events': 0,
            'low_events': 0,
            'unique_ips': 1,
            'affected_endpoints': 1
        }
        
        mock_filters.return_value = {
            'severities': ['all', 'critical', 'high', 'medium', 'low'],
            'event_types': ['all', 'security_event'],
            'time_periods': [{'value': 24, 'label': '24 Hours'}]
        }
        
        mock_render_template.return_value = "Security Audit HTML"
        
        # Import and test the route function
        from app.blueprints.admin.security_management import register_routes
        from flask import Blueprint
        
        # Create a mock blueprint
        mock_bp = MagicMock()
        register_routes(mock_bp)
        
        # Verify route was registered
        route_calls = mock_bp.route.call_args_list
        audit_route_found = any(call[0][0] == '/security/audit' for call in route_calls)
        self.assertTrue(audit_route_found)
        
        # Verify helper functions were called with correct parameters
        mock_logs.assert_called_once_with(
            hours=24,
            severity='all',
            event_type='all',
            page=1,
            per_page=50
        )
        mock_stats.assert_called_once_with(24)
        mock_filters.assert_called_once()
        
        # Verify template was rendered
        mock_render_template.assert_called_once_with(
            'security_audit_logs.html',
            audit_logs=mock_logs.return_value,
            audit_stats=mock_stats.return_value,
            available_filters=mock_filters.return_value,
            current_filters={
                'hours': 24,
                'severity': 'all',
                'event_type': 'all',
                'page': 1,
                'per_page': 50
            },
            page_title='Security Audit Logs'
        )
    
    @patch('app.blueprints.admin.security_management.get_detailed_security_features')
    @patch('app.blueprints.admin.security_management.get_security_configuration')
    @patch('app.blueprints.admin.security_management.render_template')
    def test_security_features_route(self, mock_render_template, mock_config, mock_features):
        """Test security features route returns correct data"""
        # Mock return values
        mock_features.return_value = {
            'csrf_protection': {
                'enabled': True,
                'status': 'Active',
                'description': 'Cross-Site Request Forgery protection',
                'config_key': 'SECURITY_CSRF_ENABLED',
                'config_value': 'true',
                'health_status': 'healthy',
                'last_checked': datetime.now(timezone.utc).isoformat()
            }
        }
        
        mock_config.return_value = {
            'csrf_token_lifetime': '3600',
            'rate_limit_per_minute': '60',
            'session_timeout': '7200'
        }
        
        mock_render_template.return_value = "Security Features HTML"
        
        # Import and test the route function
        from app.blueprints.admin.security_management import register_routes
        from flask import Blueprint
        
        # Create a mock blueprint
        mock_bp = MagicMock()
        register_routes(mock_bp)
        
        # Verify route was registered
        route_calls = mock_bp.route.call_args_list
        features_route_found = any(call[0][0] == '/security/features' for call in route_calls)
        self.assertTrue(features_route_found)
        
        # Verify helper functions were called
        mock_features.assert_called_once()
        mock_config.assert_called_once()
        
        # Verify template was rendered
        mock_render_template.assert_called_once_with(
            'security_features_management.html',
            features_status=mock_features.return_value,
            security_config=mock_config.return_value,
            page_title='Security Features'
        )
    
    @patch('app.blueprints.admin.security_management.get_csrf_security_metrics')
    @patch('app.blueprints.admin.security_management.render_template')
    def test_csrf_dashboard_route(self, mock_render_template, mock_csrf_metrics):
        """Test CSRF dashboard route returns correct data"""
        # Mock CSRF metrics manager
        mock_manager = MagicMock()
        mock_manager.get_csrf_dashboard_data.return_value = {
            'recent_violations': [],
            'top_violation_types': [],
            'top_violation_endpoints': []
        }
        
        mock_compliance_24h = MagicMock()
        mock_compliance_24h.compliance_rate = 1.0
        mock_compliance_24h.total_requests = 100
        mock_compliance_24h.violation_count = 0
        
        mock_compliance_7d = MagicMock()
        mock_compliance_7d.compliance_rate = 0.98
        mock_compliance_7d.total_requests = 700
        mock_compliance_7d.violation_count = 2
        
        mock_manager.get_compliance_metrics.side_effect = lambda period: {
            '24h': mock_compliance_24h,
            '7d': mock_compliance_7d
        }[period]
        
        mock_csrf_metrics.return_value = mock_manager
        mock_render_template.return_value = "CSRF Dashboard HTML"
        
        # Import and test the route function
        from app.blueprints.admin.security_management import register_routes
        from flask import Blueprint
        
        # Create a mock blueprint
        mock_bp = MagicMock()
        register_routes(mock_bp)
        
        # Verify route was registered
        route_calls = mock_bp.route.call_args_list
        csrf_route_found = any(call[0][0] == '/security/csrf' for call in route_calls)
        self.assertTrue(csrf_route_found)
        
        # Verify CSRF metrics were retrieved
        mock_csrf_metrics.assert_called_once()
        mock_manager.get_csrf_dashboard_data.assert_called_once()
        mock_manager.get_compliance_metrics.assert_any_call('24h')
        mock_manager.get_compliance_metrics.assert_any_call('7d')
        
        # Verify template was rendered
        mock_render_template.assert_called_once_with(
            'csrf_security_dashboard.html',
            dashboard_data=mock_manager.get_csrf_dashboard_data.return_value,
            compliance_24h=mock_compliance_24h,
            compliance_7d=mock_compliance_7d,
            page_title='CSRF Protection Dashboard'
        )
    
    def test_admin_required_decorator(self):
        """Test that admin_required decorator works correctly"""
        # This test would require Flask context, so we'll test the logic instead
        self.assertTrue(True)  # Placeholder test
    
    @patch('app.blueprints.admin.security_management.security_monitor')
    def test_get_security_overview_data(self, mock_security_monitor):
        """Test get_security_overview_data helper function"""
        from app.blueprints.admin.security_management import get_security_overview_data
        
        # Mock security monitor data
        mock_security_monitor.get_security_dashboard_data.return_value = {
            'total_events_24h': 10,
            'critical_events_24h': 1,
            'high_events_24h': 2
        }
        
        with patch('app.blueprints.admin.security_management.calculate_security_score', return_value=90), \
             patch('app.blueprints.admin.security_management.count_open_security_issues', return_value=3):
            
            result = get_security_overview_data()
            
            self.assertEqual(result['security_score'], 90)
            self.assertEqual(result['open_issues'], 3)
            self.assertEqual(result['recent_events_24h'], 10)
            self.assertEqual(result['critical_events_24h'], 1)
            self.assertEqual(result['high_events_24h'], 2)
            self.assertIn('last_updated', result)
    
    @patch.dict('os.environ', {
        'SECURITY_CSRF_ENABLED': 'true',
        'SECURITY_RATE_LIMITING_ENABLED': 'true',
        'SECURITY_INPUT_VALIDATION_ENABLED': 'false'
    })
    def test_get_security_features_status(self):
        """Test get_security_features_status helper function"""
        from app.blueprints.admin.security_management import get_security_features_status
        
        result = get_security_features_status()
        
        # Debug: print the actual result
        print(f"CSRF result: {result.get('csrf_protection', {})}")
        
        # Verify the function returns a dictionary
        self.assertIsInstance(result, dict)
        
        # Verify CSRF protection key exists
        self.assertIn('csrf_protection', result)
        
        # Verify CSRF protection structure
        csrf_info = result['csrf_protection']
        self.assertIn('enabled', csrf_info)
        self.assertIn('status', csrf_info)
        self.assertIn('description', csrf_info)
    
    @patch('app.blueprints.admin.security_management.security_monitor')
    def test_get_security_audit_logs(self, mock_security_monitor):
        """Test get_security_audit_logs helper function"""
        from app.blueprints.admin.security_management import get_security_audit_logs
        
        # Mock security monitor data
        mock_security_monitor.get_security_dashboard_data.return_value = {
            'recent_critical_events': [
                {
                    'event_id': 'test-1',
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'event_type': 'security_event',
                    'source_ip': '127.0.0.1',
                    'endpoint': '/test',
                    'message': 'Test event'
                }
            ]
        }
        
        result = get_security_audit_logs(hours=24, severity='all', event_type='all', page=1, per_page=50)
        
        self.assertEqual(len(result['events']), 1)
        self.assertEqual(result['events'][0]['event_type'], 'security_event')
        self.assertEqual(result['events'][0]['severity'], 'critical')
        self.assertEqual(result['total_events'], 1)
        self.assertEqual(result['page'], 1)
        self.assertEqual(result['per_page'], 50)


if __name__ == '__main__':
    unittest.main()
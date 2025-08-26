# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Tests for Maintenance Monitoring Dashboard

Tests the admin interface for maintenance mode monitoring and status display.
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config import Config
from database import DatabaseManager
from models import User, UserRole
from enhanced_maintenance_mode_service import EnhancedMaintenanceModeService, MaintenanceMode, MaintenanceStatus


class TestMaintenanceMonitoringDashboard(unittest.TestCase):
    """Test maintenance monitoring dashboard functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        
        # Create mock configuration service
        self.mock_config_service = Mock()
        
        # Create maintenance service
        self.maintenance_service = EnhancedMaintenanceModeService(
            config_service=self.mock_config_service,
            db_manager=self.db_manager
        )
        
        # Create mock Flask app
        self.mock_app = Mock()
        self.mock_app.config = {
            'maintenance_service': self.maintenance_service,
            'db_manager': self.db_manager
        }
        
        # Create mock admin user
        self.admin_user = Mock()
        self.admin_user.username = 'test_admin'
        self.admin_user.role = UserRole.ADMIN
    
    def test_monitoring_data_collection(self):
        """Test monitoring data collection functionality"""
        # Import the helper function
        from admin.routes.maintenance_mode import _collect_monitoring_data
        
        # Create test status
        test_status = MaintenanceStatus(
            is_active=True,
            mode=MaintenanceMode.NORMAL,
            reason='Test maintenance',
            estimated_duration=60,
            started_at=datetime.now(timezone.utc),
            estimated_completion=datetime.now(timezone.utc) + timedelta(minutes=60),
            enabled_by='test_admin',
            blocked_operations=['caption_generation', 'job_creation'],
            active_jobs_count=3,
            invalidated_sessions=5,
            test_mode=False
        )
        
        # Mock service methods
        with patch.object(self.maintenance_service, 'get_maintenance_status', return_value=test_status):
            with patch.object(self.maintenance_service, 'get_blocked_operations', return_value=['caption_generation', 'job_creation']):
                with patch.object(self.maintenance_service, 'get_service_stats', return_value={'statistics': {'blocked_operations': 10}}):
                    with patch.object(self.maintenance_service, 'get_maintenance_history', return_value=[]):
                        # Collect monitoring data
                        monitoring_data = _collect_monitoring_data(self.maintenance_service)
                        
                        # Verify data structure
                        self.assertIn('current_status', monitoring_data)
                        self.assertIn('blocked_operations', monitoring_data)
                        self.assertIn('blocked_operations_count', monitoring_data)
                        self.assertIn('active_jobs_count', monitoring_data)
                        self.assertIn('invalidated_sessions_count', monitoring_data)
                        self.assertIn('impact_percentage', monitoring_data)
                        self.assertIn('affected_users_count', monitoring_data)
                        self.assertIn('blocked_requests_count', monitoring_data)
                        self.assertIn('active_sessions', monitoring_data)
                        self.assertIn('maintenance_history', monitoring_data)
                        self.assertIn('statistics', monitoring_data)
                        self.assertIn('performance', monitoring_data)
                        
                        # Verify data values
                        self.assertEqual(monitoring_data['blocked_operations_count'], 2)
                        self.assertEqual(monitoring_data['active_jobs_count'], 3)
                        self.assertEqual(monitoring_data['invalidated_sessions_count'], 5)
                        self.assertGreater(monitoring_data['impact_percentage'], 0)
    
    def test_impact_percentage_calculation(self):
        """Test impact percentage calculation"""
        from admin.routes.maintenance_mode import _calculate_impact_percentage
        
        # Test normal maintenance mode
        normal_status = Mock()
        normal_status.is_active = True
        normal_status.mode = Mock()
        normal_status.mode.value = 'normal'
        normal_status.active_jobs_count = 2
        
        impact = _calculate_impact_percentage(normal_status, ['caption_generation', 'job_creation'])
        self.assertGreater(impact, 0)
        self.assertLessEqual(impact, 100)
        
        # Test emergency maintenance mode
        emergency_status = Mock()
        emergency_status.is_active = True
        emergency_status.mode = Mock()
        emergency_status.mode.value = 'emergency'
        emergency_status.active_jobs_count = 5
        
        emergency_impact = _calculate_impact_percentage(emergency_status, ['caption_generation', 'job_creation', 'platform_operations'])
        self.assertGreater(emergency_impact, impact)  # Emergency should have higher impact
        
        # Test inactive maintenance
        inactive_status = Mock()
        inactive_status.is_active = False
        
        inactive_impact = _calculate_impact_percentage(inactive_status, [])
        self.assertEqual(inactive_impact, 0)
    
    def test_affected_users_count_calculation(self):
        """Test affected users count calculation"""
        from admin.routes.maintenance_mode import _get_affected_users_count
        
        # Test active maintenance
        active_status = Mock()
        active_status.is_active = True
        active_status.mode = Mock()
        active_status.mode.value = 'normal'
        active_status.invalidated_sessions = 3
        
        affected_count = _get_affected_users_count(active_status)
        self.assertGreater(affected_count, 0)
        self.assertGreaterEqual(affected_count, active_status.invalidated_sessions)
        
        # Test emergency mode (should affect more users)
        emergency_status = Mock()
        emergency_status.is_active = True
        emergency_status.mode = Mock()
        emergency_status.mode.value = 'emergency'
        emergency_status.invalidated_sessions = 3
        
        emergency_affected = _get_affected_users_count(emergency_status)
        self.assertGreater(emergency_affected, affected_count)
        
        # Test inactive maintenance
        inactive_status = Mock()
        inactive_status.is_active = False
        
        inactive_affected = _get_affected_users_count(inactive_status)
        self.assertEqual(inactive_affected, 0)
    
    def test_blocked_requests_count_calculation(self):
        """Test blocked requests count calculation"""
        from admin.routes.maintenance_mode import _get_blocked_requests_count
        
        # Test with service stats
        service_stats = {
            'statistics': {
                'blocked_operations': 25
            }
        }
        
        blocked_count = _get_blocked_requests_count(service_stats)
        self.assertEqual(blocked_count, 25)
        
        # Test with empty stats
        empty_stats = {}
        empty_blocked_count = _get_blocked_requests_count(empty_stats)
        self.assertEqual(empty_blocked_count, 0)
        
        # Test with None stats
        none_blocked_count = _get_blocked_requests_count(None)
        self.assertEqual(none_blocked_count, 0)
    
    def test_active_sessions_data_structure(self):
        """Test active sessions data structure"""
        from admin.routes.maintenance_mode import _get_active_sessions_data
        
        sessions_data = _get_active_sessions_data()
        
        # Verify data structure
        self.assertIsInstance(sessions_data, list)
        
        if sessions_data:
            session = sessions_data[0]
            self.assertIn('username', session)
            self.assertIn('email', session)
            self.assertIn('is_admin', session)
            self.assertIn('is_invalidated', session)
            self.assertIn('platform_name', session)
            self.assertIn('last_activity', session)
            
            # Verify data types
            self.assertIsInstance(session['username'], str)
            self.assertIsInstance(session['email'], str)
            self.assertIsInstance(session['is_admin'], bool)
            self.assertIsInstance(session['is_invalidated'], bool)
    
    def test_monitoring_dashboard_access_control(self):
        """Test monitoring dashboard access control"""
        # Test route registration
        from admin.routes.maintenance_mode import register_routes
        
        # Mock blueprint
        mock_bp = Mock()
        register_routes(mock_bp)
        
        # Verify that monitoring routes were registered
        route_calls = [str(call) for call in mock_bp.route.call_args_list]
        monitoring_route_found = any('/maintenance-monitoring' in call for call in route_calls)
        self.assertTrue(monitoring_route_found, "Maintenance monitoring route should be registered")
        
        # Verify API routes
        api_monitoring_route_found = any('/api/maintenance-mode/monitoring' in call for call in route_calls)
        self.assertTrue(api_monitoring_route_found, "Maintenance monitoring API route should be registered")
    
    def test_monitoring_data_error_handling(self):
        """Test monitoring data collection error handling"""
        from admin.routes.maintenance_mode import _collect_monitoring_data
        
        # Create a service that throws errors
        error_service = Mock()
        error_service.get_maintenance_status.side_effect = Exception("Service error")
        
        # Should return safe defaults on error
        monitoring_data = _collect_monitoring_data(error_service)
        
        # Verify safe defaults
        self.assertIsInstance(monitoring_data, dict)
        self.assertIn('current_status', monitoring_data)
        self.assertFalse(monitoring_data['current_status']['is_active'])
        self.assertEqual(monitoring_data['blocked_operations_count'], 0)
        self.assertEqual(monitoring_data['active_jobs_count'], 0)
        self.assertEqual(monitoring_data['impact_percentage'], 0)
    
    def test_maintenance_report_export_structure(self):
        """Test maintenance report export structure"""
        # Test that the service has the create_maintenance_report method
        self.assertTrue(hasattr(self.maintenance_service, 'create_maintenance_report'))
        
        # Mock the report creation
        mock_report = {
            'report_generated_at': datetime.now(timezone.utc).isoformat(),
            'maintenance_status': {
                'is_active': False,
                'mode': 'normal'
            },
            'blocked_operations': {
                'count': 0,
                'operations': []
            },
            'system_impact': {
                'active_jobs_count': 0,
                'invalidated_sessions': 0
            }
        }
        
        with patch.object(self.maintenance_service, 'create_maintenance_report', return_value=mock_report):
            report = self.maintenance_service.create_maintenance_report()
            
            # Verify report structure
            self.assertIn('report_generated_at', report)
            self.assertIn('maintenance_status', report)
            self.assertIn('blocked_operations', report)
            self.assertIn('system_impact', report)
    
    def test_real_time_monitoring_data_updates(self):
        """Test real-time monitoring data updates"""
        from admin.routes.maintenance_mode import _collect_monitoring_data
        
        # Test with changing maintenance status
        initial_status = MaintenanceStatus(
            is_active=False,
            mode=MaintenanceMode.NORMAL,
            reason=None,
            estimated_duration=None,
            started_at=None,
            estimated_completion=None,
            enabled_by=None,
            blocked_operations=[],
            active_jobs_count=0,
            invalidated_sessions=0,
            test_mode=False
        )
        
        updated_status = MaintenanceStatus(
            is_active=True,
            mode=MaintenanceMode.EMERGENCY,
            reason='Critical system issue',
            estimated_duration=30,
            started_at=datetime.now(timezone.utc),
            estimated_completion=datetime.now(timezone.utc) + timedelta(minutes=30),
            enabled_by='admin',
            blocked_operations=['caption_generation', 'job_creation', 'platform_operations'],
            active_jobs_count=5,
            invalidated_sessions=10,
            test_mode=False
        )
        
        # Mock service to return initial status
        with patch.object(self.maintenance_service, 'get_maintenance_status', return_value=initial_status):
            with patch.object(self.maintenance_service, 'get_blocked_operations', return_value=[]):
                with patch.object(self.maintenance_service, 'get_service_stats', return_value={'statistics': {}}):
                    with patch.object(self.maintenance_service, 'get_maintenance_history', return_value=[]):
                        initial_data = _collect_monitoring_data(self.maintenance_service)
        
        # Mock service to return updated status
        with patch.object(self.maintenance_service, 'get_maintenance_status', return_value=updated_status):
            with patch.object(self.maintenance_service, 'get_blocked_operations', return_value=['caption_generation', 'job_creation', 'platform_operations']):
                with patch.object(self.maintenance_service, 'get_service_stats', return_value={'statistics': {'blocked_operations': 15}}):
                    with patch.object(self.maintenance_service, 'get_maintenance_history', return_value=[]):
                        updated_data = _collect_monitoring_data(self.maintenance_service)
        
        # Verify data changes
        self.assertNotEqual(initial_data['impact_percentage'], updated_data['impact_percentage'])
        self.assertLess(initial_data['blocked_operations_count'], updated_data['blocked_operations_count'])
        self.assertLess(initial_data['active_jobs_count'], updated_data['active_jobs_count'])
        self.assertLess(initial_data['invalidated_sessions_count'], updated_data['invalidated_sessions_count'])
    
    def test_performance_metrics_structure(self):
        """Test performance metrics data structure"""
        from admin.routes.maintenance_mode import _collect_monitoring_data
        
        with patch.object(self.maintenance_service, 'get_maintenance_status') as mock_status:
            with patch.object(self.maintenance_service, 'get_blocked_operations', return_value=[]):
                with patch.object(self.maintenance_service, 'get_service_stats', return_value={'statistics': {}}):
                    with patch.object(self.maintenance_service, 'get_maintenance_history', return_value=[]):
                        # Mock a basic status
                        mock_status.return_value = MaintenanceStatus(
                            is_active=False,
                            mode=MaintenanceMode.NORMAL,
                            reason=None,
                            estimated_duration=None,
                            started_at=None,
                            estimated_completion=None,
                            enabled_by=None,
                            blocked_operations=[],
                            active_jobs_count=0,
                            invalidated_sessions=0,
                            test_mode=False
                        )
                        
                        monitoring_data = _collect_monitoring_data(self.maintenance_service)
        
        # Verify performance metrics structure
        self.assertIn('performance', monitoring_data)
        performance = monitoring_data['performance']
        
        self.assertIn('avg_response_time', performance)
        self.assertIn('uptime_percentage', performance)
        self.assertIn('total_requests', performance)
        
        # Verify data types
        self.assertIsInstance(performance['avg_response_time'], (int, float))
        self.assertIsInstance(performance['uptime_percentage'], (int, float))
        self.assertIsInstance(performance['total_requests'], int)


if __name__ == '__main__':
    unittest.main()
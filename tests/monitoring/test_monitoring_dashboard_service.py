# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Tests for Enhanced Monitoring Dashboard Service

Tests real-time monitoring, historical reporting, customizable widgets,
and alerting integration functionality.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta
import json
import tempfile
import os

from monitoring_dashboard_service import (
    MonitoringDashboardService, DashboardWidgetType, ReportType, 
    ReportFormat, DashboardWidget, ReportConfig, DashboardAlert
)
from models import UserRole, TaskStatus, CaptionGenerationTask, User
from app.services.alerts.components.alert_manager import AlertType, AlertSeverity
from app.core.database.core.database_manager import DatabaseManager


class TestMonitoringDashboardService(unittest.TestCase):
    """Test cases for MonitoringDashboardService"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_db_manager = Mock(spec=DatabaseManager)
        self.mock_session = Mock()
        
        # Mock the context manager properly
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=self.mock_session)
        mock_context.__exit__ = Mock(return_value=None)
        self.mock_db_manager.get_session.return_value = mock_context
        
        # Create service instance
        with patch('monitoring_dashboard_service.AdminMonitoringService'), \
             patch('monitoring_dashboard_service.SystemMonitor'), \
             patch('monitoring_dashboard_service.AlertManager'):
            self.service = MonitoringDashboardService(self.mock_db_manager)
    
    def test_get_dashboard_config_admin_role(self):
        """Test getting dashboard configuration for admin role"""
        config = self.service.get_dashboard_config(UserRole.ADMIN)
        
        self.assertIn('widgets', config)
        self.assertIn('refresh_interval', config)
        self.assertIn('auto_refresh_enabled', config)
        self.assertEqual(config['refresh_interval'], 30)
        self.assertTrue(config['auto_refresh_enabled'])
        
        # Check that admin widgets are included
        widget_ids = [w['id'] for w in config['widgets']]
        self.assertIn('system_overview', widget_ids)
        self.assertIn('resource_monitor', widget_ids)
        self.assertIn('alert_panel', widget_ids)
    
    def test_get_dashboard_config_admin_role_user_activity(self):
        """Test getting dashboard configuration for admin role includes user activity"""
        config = self.service.get_dashboard_config(UserRole.ADMIN)
        
        # Admin should have access to all widgets including user activity
        widget_ids = [w['id'] for w in config['widgets']]
        self.assertIn('user_activity_chart', widget_ids)
    
    def test_get_dashboard_config_reviewer_role(self):
        """Test getting dashboard configuration for reviewer role (should have limited access)"""
        config = self.service.get_dashboard_config(UserRole.REVIEWER)
        
        # Reviewer should have no admin widgets
        self.assertEqual(len(config['widgets']), 0)
    
    def test_get_widget_data_metric_card(self):
        """Test getting data for metric card widget"""
        # Mock admin monitoring service
        mock_overview = {
            'active_tasks': 5,
            'recent_tasks': 20,
            'active_users': 3,
            'queue_stats': {'queue_stats': {'queued_tasks': 2}},
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        self.service.admin_monitoring.get_system_overview.return_value = mock_overview
        
        # Create test widget
        widget = DashboardWidget(
            id="test_metrics",
            type=DashboardWidgetType.METRIC_CARD,
            title="Test Metrics",
            position={"x": 0, "y": 0, "width": 12, "height": 2},
            config={"metrics": ["active_tasks", "recent_tasks", "active_users"]},
            roles=[UserRole.ADMIN]
        )
        self.service.default_widgets = [widget]
        
        data = self.service.get_widget_data("test_metrics", UserRole.ADMIN)
        
        self.assertIn('metrics', data)
        self.assertEqual(data['metrics']['active_tasks'], 5)
        self.assertEqual(data['metrics']['recent_tasks'], 20)
        self.assertEqual(data['metrics']['active_users'], 3)
    
    def test_get_widget_data_access_denied(self):
        """Test widget data access denied for unauthorized role"""
        widget = DashboardWidget(
            id="admin_only",
            type=DashboardWidgetType.METRIC_CARD,
            title="Admin Only",
            position={"x": 0, "y": 0, "width": 6, "height": 2},
            config={"metrics": ["active_tasks"]},
            roles=[UserRole.ADMIN]
        )
        self.service.default_widgets = [widget]
        
        data = self.service.get_widget_data("admin_only", UserRole.REVIEWER)
        
        self.assertIn('error', data)
        self.assertIn('access denied', data['error'].lower())
    
    def test_get_historical_report_system_performance(self):
        """Test generating system performance report"""
        # Mock database query results
        mock_tasks = [
            Mock(
                id="task1",
                user_id=1,
                status=TaskStatus.COMPLETED,
                created_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
                results=Mock(processing_time_seconds=30.5)
            ),
            Mock(
                id="task2",
                user_id=2,
                status=TaskStatus.FAILED,
                created_at=datetime.now(timezone.utc),
                completed_at=None,
                results=None
            )
        ]
        self.mock_session.query.return_value.filter.return_value.all.return_value = mock_tasks
        
        start_date = datetime.now(timezone.utc) - timedelta(days=7)
        end_date = datetime.now(timezone.utc)
        
        report = self.service.get_historical_report(
            ReportType.SYSTEM_PERFORMANCE, start_date, end_date
        )
        
        self.assertEqual(report['report_type'], 'system_performance')
        self.assertIn('summary', report)
        self.assertIn('details', report)
        self.assertEqual(report['summary']['total_tasks'], 2)
        self.assertEqual(report['summary']['completed_tasks'], 1)
        self.assertEqual(report['summary']['failed_tasks'], 1)
        self.assertEqual(report['summary']['success_rate'], 50.0)
    
    def test_get_historical_report_user_activity(self):
        """Test generating user activity report"""
        # Mock database query results
        mock_user_activity = [
            Mock(id=1, username="user1", role=UserRole.REVIEWER, task_count=5),
            Mock(id=2, username="admin1", role=UserRole.ADMIN, task_count=10)
        ]
        self.mock_session.query.return_value.outerjoin.return_value.filter.return_value.group_by.return_value.all.return_value = mock_user_activity
        
        start_date = datetime.now(timezone.utc) - timedelta(days=7)
        end_date = datetime.now(timezone.utc)
        
        report = self.service.get_historical_report(
            ReportType.USER_ACTIVITY, start_date, end_date
        )
        
        self.assertEqual(report['report_type'], 'user_activity')
        self.assertIn('users', report)
        self.assertEqual(len(report['users']), 2)
        self.assertEqual(report['users'][0]['username'], 'user1')
        self.assertEqual(report['users'][0]['task_count'], 5)
    
    def test_get_historical_report_error_analysis(self):
        """Test generating error analysis report"""
        # Mock failed tasks
        mock_failed_tasks = [
            Mock(
                id="task1",
                user_id=1,
                error_message="Connection timeout: API unavailable",
                created_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc)
            ),
            Mock(
                id="task2",
                user_id=2,
                error_message="Connection timeout: Network error",
                created_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc)
            ),
            Mock(
                id="task3",
                user_id=1,
                error_message="Invalid credentials",
                created_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc)
            )
        ]
        self.mock_session.query.return_value.filter.return_value.all.return_value = mock_failed_tasks
        
        start_date = datetime.now(timezone.utc) - timedelta(days=7)
        end_date = datetime.now(timezone.utc)
        
        report = self.service.get_historical_report(
            ReportType.ERROR_ANALYSIS, start_date, end_date
        )
        
        self.assertEqual(report['report_type'], 'error_analysis')
        self.assertIn('error_patterns', report)
        self.assertEqual(report['summary']['total_failed_tasks'], 3)
        
        # Check error pattern analysis
        error_patterns = {pattern['error_type']: pattern['count'] for pattern in report['error_patterns']}
        self.assertEqual(error_patterns['Connection timeout'], 2)
        self.assertEqual(error_patterns['Invalid credentials'], 1)
    
    def test_export_report_json(self):
        """Test exporting report as JSON"""
        report_data = {
            'report_type': 'test_report',
            'summary': {'total': 100},
            'generated_at': datetime.now(timezone.utc).isoformat()
        }
        
        content, mime_type = self.service.export_report(report_data, ReportFormat.JSON)
        
        self.assertEqual(mime_type, 'application/json')
        self.assertIsInstance(content, bytes)
        
        # Verify JSON content
        parsed_data = json.loads(content.decode('utf-8'))
        self.assertEqual(parsed_data['report_type'], 'test_report')
        self.assertEqual(parsed_data['summary']['total'], 100)
    
    def test_export_report_csv(self):
        """Test exporting report as CSV"""
        report_data = {
            'report_type': 'test_report',
            'details': [
                {'id': 'task1', 'status': 'completed', 'duration': 30},
                {'id': 'task2', 'status': 'failed', 'duration': 0}
            ]
        }
        
        content, mime_type = self.service.export_report(report_data, ReportFormat.CSV)
        
        self.assertEqual(mime_type, 'text/csv')
        self.assertIsInstance(content, bytes)
        
        # Verify CSV content
        csv_content = content.decode('utf-8')
        self.assertIn('id,status,duration', csv_content)
        self.assertIn('task1,completed,30', csv_content)
        self.assertIn('task2,failed,0', csv_content)
    
    def test_export_report_html(self):
        """Test exporting report as HTML"""
        report_data = {
            'report_type': 'test_report',
            'summary': {'total': 100},
            'generated_at': datetime.now(timezone.utc).isoformat()
        }
        
        content, mime_type = self.service.export_report(report_data, ReportFormat.HTML)
        
        self.assertEqual(mime_type, 'text/html')
        self.assertIsInstance(content, bytes)
        
        # Verify HTML content
        html_content = content.decode('utf-8')
        self.assertIn('<!DOCTYPE html>', html_content)
        self.assertIn('Test Report', html_content)
        self.assertIn('"total": 100', html_content)
    
    def test_get_dashboard_alerts(self):
        """Test getting dashboard alerts"""
        # Mock alert manager
        mock_alerts = [
            Mock(
                id="alert1",
                type=AlertType.SYSTEM_ERROR,
                severity=AlertSeverity.CRITICAL,
                message="System overload detected",
                timestamp=datetime.now(timezone.utc),
                acknowledged=False,
                auto_dismiss=False,
                dismiss_after=None
            ),
            Mock(
                id="alert2",
                type=AlertType.PERFORMANCE_DEGRADATION,
                severity=AlertSeverity.WARNING,
                message="High response times",
                timestamp=datetime.now(timezone.utc),
                acknowledged=True,
                auto_dismiss=False,
                dismiss_after=None
            )
        ]
        self.service.alert_manager.get_active_alerts.return_value = mock_alerts
        
        # Test getting all alerts
        alerts = self.service.get_dashboard_alerts()
        self.assertEqual(len(alerts), 2)
        
        # Test getting only unacknowledged alerts
        unack_alerts = self.service.get_dashboard_alerts(acknowledged=False)
        self.assertEqual(len(unack_alerts), 1)
        self.assertEqual(unack_alerts[0].id, "alert1")
        
        # Test getting only acknowledged alerts
        ack_alerts = self.service.get_dashboard_alerts(acknowledged=True)
        self.assertEqual(len(ack_alerts), 1)
        self.assertEqual(ack_alerts[0].id, "alert2")
    
    def test_acknowledge_alert_success(self):
        """Test successfully acknowledging an alert"""
        self.service.alert_manager.acknowledge_alert.return_value = True
        
        result = self.service.acknowledge_alert("alert123", 1)
        
        self.assertTrue(result['success'])
        self.assertIn('acknowledged', result['message'])
        self.service.alert_manager.acknowledge_alert.assert_called_once_with(1, "alert123")
    
    def test_acknowledge_alert_failure(self):
        """Test failing to acknowledge an alert"""
        self.service.alert_manager.acknowledge_alert.return_value = False
        
        result = self.service.acknowledge_alert("alert123", 1)
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
    
    def test_get_real_time_metrics(self):
        """Test getting real-time system metrics"""
        # Mock dependencies
        mock_overview = {'active_tasks': 5, 'recent_tasks': 20}
        mock_health = {'overall_status': 'healthy', 'cpu_usage': 45.2}
        mock_performance = {'throughput': 100, 'avg_response_time': 250}
        
        self.service.admin_monitoring.get_system_overview.return_value = mock_overview
        self.service.system_monitor.get_system_health.return_value = mock_health
        self.service.system_monitor.get_performance_metrics.return_value = mock_performance
        
        # Mock alerts
        mock_alerts = [
            DashboardAlert(
                id="alert1",
                type=AlertType.SYSTEM_ERROR,
                severity=AlertSeverity.CRITICAL,
                message="Test alert",
                timestamp=datetime.now(timezone.utc)
            )
        ]
        with patch.object(self.service, 'get_dashboard_alerts', return_value=mock_alerts):
            metrics = self.service.get_real_time_metrics()
        
        self.assertIn('timestamp', metrics)
        self.assertIn('overview', metrics)
        self.assertIn('health', metrics)
        self.assertIn('performance', metrics)
        self.assertIn('alerts', metrics)
        self.assertEqual(metrics['status'], 'healthy')
        self.assertEqual(metrics['alerts']['critical'], 1)
        self.assertEqual(metrics['alerts']['warning'], 0)
        self.assertEqual(metrics['alerts']['info'], 0)
    
    def test_widget_data_error_handling(self):
        """Test error handling in widget data retrieval"""
        # Mock an exception in admin monitoring
        self.service.admin_monitoring.get_system_overview.side_effect = Exception("Database error")
        
        widget = DashboardWidget(
            id="error_widget",
            type=DashboardWidgetType.METRIC_CARD,
            title="Error Widget",
            position={"x": 0, "y": 0, "width": 6, "height": 2},
            config={"metrics": ["active_tasks"]},
            roles=[UserRole.ADMIN]
        )
        self.service.default_widgets = [widget]
        
        data = self.service.get_widget_data("error_widget", UserRole.ADMIN)
        
        self.assertIn('error', data)
        self.assertIn('Database error', data['error'])
    
    def test_report_generation_error_handling(self):
        """Test error handling in report generation"""
        # Mock database exception
        self.mock_session.query.side_effect = Exception("Database connection failed")
        
        start_date = datetime.now(timezone.utc) - timedelta(days=7)
        end_date = datetime.now(timezone.utc)
        
        report = self.service.get_historical_report(
            ReportType.SYSTEM_PERFORMANCE, start_date, end_date
        )
        
        self.assertIn('error', report)
        self.assertIn('Database connection failed', report['error'])
    
    def test_time_series_data_generation(self):
        """Test time series data generation for charts"""
        performance_data = {
            'total_completed_tasks': 100,
            'total_failed_tasks': 10,
            'success_rate': 90.0
        }
        
        data_points = self.service._generate_time_series_data(24, performance_data)
        
        self.assertEqual(len(data_points), 24)  # 24 hours
        
        for point in data_points:
            self.assertIn('timestamp', point)
            self.assertIn('completed', point)
            self.assertIn('failed', point)
            self.assertIn('success_rate', point)
            self.assertIsInstance(point['completed'], int)
            self.assertIsInstance(point['failed'], int)
            self.assertIsInstance(point['success_rate'], (int, float))
    
    def test_resource_status_determination(self):
        """Test resource status determination logic"""
        # Test healthy status
        healthy_resources = {'cpu_percent': 30, 'memory_percent': 40, 'disk_percent': 50}
        status = self.service._get_resource_status(healthy_resources)
        self.assertEqual(status, 'healthy')
        
        # Test warning status
        warning_resources = {'cpu_percent': 75, 'memory_percent': 60, 'disk_percent': 50}
        status = self.service._get_resource_status(warning_resources)
        self.assertEqual(status, 'warning')
        
        # Test critical status
        critical_resources = {'cpu_percent': 95, 'memory_percent': 60, 'disk_percent': 50}
        status = self.service._get_resource_status(critical_resources)
        self.assertEqual(status, 'critical')


class TestDashboardIntegration(unittest.TestCase):
    """Integration tests for dashboard functionality"""
    
    def setUp(self):
        """Set up integration test fixtures"""
        self.mock_db_manager = Mock(spec=DatabaseManager)
        
        with patch('monitoring_dashboard_service.AdminMonitoringService'), \
             patch('monitoring_dashboard_service.SystemMonitor'), \
             patch('monitoring_dashboard_service.AlertManager'):
            self.service = MonitoringDashboardService(self.mock_db_manager)
    
    def test_dashboard_workflow_complete(self):
        """Test complete dashboard workflow from config to data display"""
        # 1. Get dashboard configuration
        config = self.service.get_dashboard_config(UserRole.ADMIN)
        self.assertIn('widgets', config)
        
        # 2. Get data for each widget
        widget_data = {}
        for widget in config['widgets']:
            with patch.object(self.service, '_get_metric_card_data', return_value={'metrics': {'test': 1}}), \
                 patch.object(self.service, '_get_chart_data', return_value={'data': []}), \
                 patch.object(self.service, '_get_table_data', return_value={'rows': []}), \
                 patch.object(self.service, '_get_gauge_data', return_value={'value': 95}), \
                 patch.object(self.service, '_get_alert_panel_data', return_value={'alerts': []}), \
                 patch.object(self.service, '_get_resource_monitor_data', return_value={'resources': {}}):
                
                data = self.service.get_widget_data(widget['id'], UserRole.ADMIN)
                widget_data[widget['id']] = data
        
        # Verify all widgets have data
        self.assertEqual(len(widget_data), len(config['widgets']))
        for widget_id, data in widget_data.items():
            self.assertNotIn('error', data, f"Widget {widget_id} has error: {data.get('error')}")
    
    def test_report_generation_and_export_workflow(self):
        """Test complete report generation and export workflow"""
        # Mock database session
        mock_session = Mock()
        self.mock_db_manager.get_session.return_value.__enter__.return_value = mock_session
        self.mock_db_manager.get_session.return_value.__exit__.return_value = None
        
        # Mock query results
        mock_session.query.return_value.filter.return_value.all.return_value = []
        
        start_date = datetime.now(timezone.utc) - timedelta(days=7)
        end_date = datetime.now(timezone.utc)
        
        # 1. Generate report
        report = self.service.get_historical_report(
            ReportType.SYSTEM_PERFORMANCE, start_date, end_date
        )
        self.assertIn('report_type', report)
        
        # 2. Export in different formats
        for format_type in [ReportFormat.JSON, ReportFormat.CSV, ReportFormat.HTML]:
            content, mime_type = self.service.export_report(report, format_type)
            self.assertIsInstance(content, bytes)
            self.assertIsInstance(mime_type, str)
            self.assertGreater(len(content), 0)


if __name__ == '__main__':
    unittest.main()
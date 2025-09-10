# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for storage health monitoring system.

Tests the storage health checker, health endpoints, dashboard integration,
and alert system functionality.
"""

import unittest
import tempfile
import shutil
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

# Add project root to path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.services.monitoring.health.checkers.storage_health_checker import (
    StorageHealthChecker, StorageHealthStatus, StorageComponentHealth, StorageSystemHealth
)
from app.services.storage.components.storage_monitoring_dashboard_integration import StorageMonitoringDashboardIntegration
from app.services.storage.components.storage_alert_system import StorageAlertSystem, StorageAlertType, StorageAlertSeverity
from app.services.storage.components.storage_configuration_service import StorageConfigurationService
from app.services.storage.components.storage_monitor_service import StorageMonitorService, StorageMetrics


class TestStorageHealthChecker(unittest.TestCase):
    """Test cases for StorageHealthChecker"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.storage_dir = os.path.join(self.temp_dir, 'storage', 'images')
        os.makedirs(self.storage_dir, exist_ok=True)
        
        # Mock services
        self.mock_config_service = Mock(spec=StorageConfigurationService)
        self.mock_monitor_service = Mock(spec=StorageMonitorService)
        self.mock_enforcer_service = Mock()
        
        # Configure mocks
        self.mock_config_service.validate_storage_config.return_value = True
        self.mock_config_service.get_configuration_summary.return_value = {
            'max_storage_gb': 10.0,
            'warning_threshold_gb': 8.0,
            'monitoring_enabled': True,
            'is_valid': True
        }
        
        self.mock_monitor_service.STORAGE_IMAGES_DIR = self.storage_dir
        self.mock_monitor_service.get_storage_metrics.return_value = StorageMetrics(
            total_bytes=1024**3,  # 1GB
            total_gb=1.0,
            limit_gb=10.0,
            usage_percentage=10.0,
            is_limit_exceeded=False,
            is_warning_exceeded=False,
            last_calculated=datetime.now(timezone.utc)
        )
        self.mock_monitor_service.get_cache_info.return_value = {
            'has_cache': True,
            'is_valid': True,
            'cache_age_seconds': 60
        }
        
        self.mock_enforcer_service.health_check.return_value = {
            'overall_healthy': True,
            'redis_connected': True,
            'config_service_healthy': True,
            'monitor_service_healthy': True
        }
        self.mock_enforcer_service.get_enforcement_statistics.return_value = {
            'currently_blocked': False,
            'total_checks': 100,
            'blocks_enforced': 5,
            'automatic_unblocks': 3
        }
        
        self.health_checker = StorageHealthChecker(
            config_service=self.mock_config_service,
            monitor_service=self.mock_monitor_service,
            enforcer_service=self.mock_enforcer_service
        )
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_comprehensive_health_check_healthy(self):
        """Test comprehensive health check with healthy system"""
        health_result = self.health_checker.check_comprehensive_health()
        
        self.assertIsInstance(health_result, StorageSystemHealth)
        self.assertEqual(health_result.overall_status, StorageHealthStatus.HEALTHY)
        self.assertIn('configuration', health_result.components)
        self.assertIn('monitoring', health_result.components)
        self.assertIn('enforcement', health_result.components)
        self.assertIn('storage_directory', health_result.components)
        self.assertIn('performance', health_result.components)
        
        # Check summary
        self.assertGreater(health_result.summary['total_components'], 0)
        self.assertGreaterEqual(health_result.summary['healthy_components'], 4)
        self.assertEqual(health_result.summary['error_components'], 0)
    
    def test_health_check_with_configuration_error(self):
        """Test health check with configuration service error"""
        self.mock_config_service.validate_storage_config.return_value = False
        
        health_result = self.health_checker.check_comprehensive_health()
        
        self.assertEqual(health_result.overall_status, StorageHealthStatus.UNHEALTHY)
        self.assertEqual(health_result.components['configuration'].status, StorageHealthStatus.UNHEALTHY)
    
    def test_health_check_with_monitoring_error(self):
        """Test health check with monitoring service error"""
        self.mock_monitor_service.get_storage_metrics.side_effect = Exception("Monitoring error")
        
        health_result = self.health_checker.check_comprehensive_health()
        
        self.assertEqual(health_result.overall_status, StorageHealthStatus.ERROR)
        self.assertEqual(health_result.components['monitoring'].status, StorageHealthStatus.ERROR)
    
    def test_health_check_with_storage_limit_exceeded(self):
        """Test health check with storage limit exceeded"""
        # Mock storage limit exceeded
        exceeded_metrics = StorageMetrics(
            total_bytes=11 * 1024**3,  # 11GB
            total_gb=11.0,
            limit_gb=10.0,
            usage_percentage=110.0,
            is_limit_exceeded=True,
            is_warning_exceeded=True,
            last_calculated=datetime.now(timezone.utc)
        )
        self.mock_monitor_service.get_storage_metrics.return_value = exceeded_metrics
        
        health_result = self.health_checker.check_comprehensive_health()
        
        self.assertEqual(health_result.overall_status, StorageHealthStatus.DEGRADED)
        self.assertEqual(health_result.components['monitoring'].status, StorageHealthStatus.DEGRADED)
        self.assertIn("limit exceeded", health_result.components['monitoring'].message.lower())
    
    def test_health_check_with_missing_storage_directory(self):
        """Test health check with missing storage directory"""
        # Remove storage directory
        shutil.rmtree(self.storage_dir)
        
        health_result = self.health_checker.check_comprehensive_health()
        
        # Should be unhealthy due to directory issues, but not error
        self.assertIn(health_result.overall_status, [StorageHealthStatus.UNHEALTHY, StorageHealthStatus.DEGRADED])
        
        # Directory should be reported as missing in the health check
        self.assertIn('storage_directory', health_result.components)
    
    def test_health_check_performance_tracking(self):
        """Test that health check tracks performance metrics"""
        health_result = self.health_checker.check_comprehensive_health()
        
        self.assertIn('total_response_time_ms', health_result.performance_metrics)
        self.assertIn('avg_component_response_time_ms', health_result.performance_metrics)
        self.assertGreater(health_result.performance_metrics['total_response_time_ms'], 0)
    
    def test_get_storage_health_metrics(self):
        """Test getting storage health metrics for monitoring"""
        metrics = self.health_checker.get_storage_health_metrics()
        
        self.assertIn('storage_system_healthy', metrics)
        self.assertIn('storage_system_status', metrics)
        self.assertIn('storage_components_total', metrics)
        self.assertIn('storage_components_healthy', metrics)
        self.assertEqual(metrics['storage_system_healthy'], 1)
        self.assertEqual(metrics['storage_system_status'], 'healthy')
    
    def test_get_storage_alerts(self):
        """Test getting storage alerts"""
        # Mock unhealthy enforcer to generate alerts
        self.mock_enforcer_service.health_check.return_value = {
            'overall_healthy': False,
            'redis_connected': False
        }
        
        alerts = self.health_checker.get_storage_alerts()
        
        self.assertIsInstance(alerts, list)
        # Should have alerts due to unhealthy enforcer
        self.assertGreater(len(alerts), 0)


class TestStorageMonitoringDashboardIntegration(unittest.TestCase):
    """Test cases for StorageMonitoringDashboardIntegration"""
    
    def setUp(self):
        """Set up test environment"""
        self.mock_db_manager = Mock()
        self.integration = StorageMonitoringDashboardIntegration(db_manager=self.mock_db_manager)
        
        # Mock the health checker
        self.integration.health_checker = Mock()
        self.integration.health_checker.check_comprehensive_health.return_value = Mock(
            overall_status=StorageHealthStatus.HEALTHY,
            timestamp=datetime.now(timezone.utc),
            summary={
                'total_components': 5,
                'healthy_components': 5,
                'degraded_components': 0,
                'unhealthy_components': 0,
                'error_components': 0,
                'health_percentage': 100.0
            },
            performance_metrics={
                'avg_component_response_time_ms': 50.0,
                'max_component_response_time_ms': 100.0
            }
        )
        
        # Mock the monitor service methods
        self.integration.monitor_service = Mock()
        self.integration.monitor_service.get_storage_metrics.return_value = StorageMetrics(
            total_bytes=2 * 1024**3,  # 2GB
            total_gb=2.0,
            limit_gb=10.0,
            usage_percentage=20.0,
            is_limit_exceeded=False,
            is_warning_exceeded=False,
            last_calculated=datetime.now(timezone.utc)
        )
        self.integration.monitor_service.get_cache_info.return_value = {
            'is_valid': True
        }
        
        # Mock the enforcer service
        if self.integration.enforcer_service:
            self.integration.enforcer_service = Mock()
            self.integration.enforcer_service.get_enforcement_statistics.return_value = {
                'currently_blocked': False,
                'total_checks': 50,
                'blocks_enforced': 2,
                'automatic_unblocks': 1
            }
    
    def test_get_storage_dashboard_metrics(self):
        """Test getting storage dashboard metrics"""
        metrics = self.integration.get_storage_dashboard_metrics()
        
        self.assertIn('storage_usage', metrics)
        self.assertIn('system_health', metrics)
        self.assertIn('enforcement', metrics)
        self.assertIn('performance', metrics)
        self.assertIn('timestamp', metrics)
        
        # Check storage usage
        self.assertEqual(metrics['storage_usage']['current_gb'], 2.0)
        self.assertEqual(metrics['storage_usage']['limit_gb'], 10.0)
        self.assertEqual(metrics['storage_usage']['usage_percentage'], 20.0)
        
        # Check system health
        self.assertEqual(metrics['system_health']['overall_status'], 'healthy')
        self.assertEqual(metrics['system_health']['healthy_components'], 5)
        self.assertEqual(metrics['system_health']['total_components'], 5)
    
    def test_get_storage_dashboard_alerts(self):
        """Test getting storage dashboard alerts"""
        # Mock health checker to return alerts
        self.integration.health_checker.get_storage_alerts.return_value = [
            {
                'type': 'storage_warning',
                'severity': 'warning',
                'message': 'Storage warning threshold exceeded',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'component': 'monitoring'
            }
        ]
        
        alerts = self.integration.get_storage_dashboard_alerts()
        
        self.assertIsInstance(alerts, list)
        self.assertEqual(len(alerts), 1)
        
        alert = alerts[0]
        self.assertIn('id', alert)
        self.assertIn('type', alert)
        self.assertIn('severity', alert)
        self.assertIn('title', alert)
        self.assertIn('message', alert)
        self.assertEqual(alert['type'], 'storage')
        self.assertEqual(alert['severity'], 'warning')
    
    def test_get_storage_widget_data_usage_gauge(self):
        """Test getting storage usage gauge widget data"""
        data = self.integration.get_storage_widget_data('storage_usage_gauge')
        
        self.assertIn('value', data)
        self.assertIn('max', data)
        self.assertIn('color', data)
        self.assertIn('status', data)
        self.assertIn('label', data)
        
        self.assertEqual(data['value'], 20.0)
        self.assertEqual(data['max'], 100)
        self.assertEqual(data['color'], 'green')
        self.assertEqual(data['status'], 'healthy')
    
    def test_get_storage_widget_data_health_status(self):
        """Test getting storage health status widget data"""
        data = self.integration.get_storage_widget_data('storage_health_status')
        
        self.assertIn('status', data)
        self.assertIn('color', data)
        self.assertIn('icon', data)
        self.assertIn('message', data)
        self.assertIn('details', data)
        
        self.assertEqual(data['status'], 'healthy')
        self.assertEqual(data['color'], 'green')
        self.assertEqual(data['icon'], 'check-circle')
    
    def test_get_storage_monitoring_summary(self):
        """Test getting storage monitoring summary"""
        summary = self.integration.get_storage_monitoring_summary()
        
        self.assertIn('storage_system', summary)
        self.assertIn('timestamp', summary)
        
        storage_system = summary['storage_system']
        self.assertIn('status', storage_system)
        self.assertIn('usage_percentage', storage_system)
        self.assertIn('health_percentage', storage_system)
        self.assertIn('alerts_count', storage_system)
        
        self.assertEqual(storage_system['status'], 'healthy')
        self.assertEqual(storage_system['usage_percentage'], 20.0)


class TestStorageAlertSystem(unittest.TestCase):
    """Test cases for StorageAlertSystem"""
    
    def setUp(self):
        """Set up test environment"""
        self.mock_db_manager = Mock()
        self.mock_alert_manager = Mock()
        
        # Mock the services before creating the alert system
        with patch('storage_alert_system.StorageConfigurationService') as mock_config_cls, \
             patch('storage_alert_system.StorageMonitorService') as mock_monitor_cls, \
             patch('storage_alert_system.StorageLimitEnforcer') as mock_enforcer_cls, \
             patch('storage_alert_system.StorageHealthChecker') as mock_health_cls:
            
            # Configure mock classes
            mock_config = Mock()
            mock_config.validate_storage_config.return_value = True
            mock_config_cls.return_value = mock_config
            
            mock_monitor = Mock()
            mock_monitor.get_storage_metrics.return_value = StorageMetrics(
                total_bytes=1024**3,  # 1GB
                total_gb=1.0,
                limit_gb=10.0,
                usage_percentage=10.0,
                is_limit_exceeded=False,
                is_warning_exceeded=False,
                last_calculated=datetime.now(timezone.utc)
            )
            mock_monitor_cls.return_value = mock_monitor
            
            mock_enforcer = Mock()
            mock_enforcer_cls.return_value = mock_enforcer
            
            mock_health_checker = Mock()
            mock_health_cls.return_value = mock_health_checker
            
            self.alert_system = StorageAlertSystem(
                db_manager=self.mock_db_manager,
                alert_manager=self.mock_alert_manager
            )
            
            # Store references to mocks for test use
            self.mock_config = mock_config
            self.mock_monitor = mock_monitor
            self.mock_health_checker = mock_health_checker
    
    def test_check_and_generate_alerts_healthy_system(self):
        """Test alert generation for healthy system"""
        # Mock healthy system
        self.mock_health_checker.check_comprehensive_health.return_value = Mock(
            overall_status=StorageHealthStatus.HEALTHY,
            components={
                'configuration': Mock(status=StorageHealthStatus.HEALTHY),
                'monitoring': Mock(status=StorageHealthStatus.HEALTHY)
            },
            performance_metrics={
                'avg_component_response_time_ms': 100.0,
                'max_component_response_time_ms': 200.0
            }
        )
        
        alerts = self.alert_system.check_and_generate_alerts()
        
        # Should have no alerts for healthy system
        self.assertEqual(len(alerts), 0)
    
    def test_check_and_generate_alerts_limit_exceeded(self):
        """Test alert generation when storage limit is exceeded"""
        # Mock storage limit exceeded
        exceeded_metrics = StorageMetrics(
            total_bytes=11 * 1024**3,  # 11GB
            total_gb=11.0,
            limit_gb=10.0,
            usage_percentage=110.0,
            is_limit_exceeded=True,
            is_warning_exceeded=True,
            last_calculated=datetime.now(timezone.utc)
        )
        self.alert_system.monitor_service.get_storage_metrics.return_value = exceeded_metrics
        
        # Mock healthy health check
        self.alert_system.health_checker.check_comprehensive_health.return_value = Mock(
            overall_status=StorageHealthStatus.HEALTHY,
            components={},
            performance_metrics={}
        )
        
        alerts = self.alert_system.check_and_generate_alerts()
        
        # Should have limit exceeded alert
        self.assertGreater(len(alerts), 0)
        limit_alert = next((a for a in alerts if a['type'] == StorageAlertType.LIMIT_EXCEEDED.value), None)
        self.assertIsNotNone(limit_alert)
        self.assertEqual(limit_alert['severity'], StorageAlertSeverity.CRITICAL.value)
        self.assertIn('limit exceeded', limit_alert['message'].lower())
    
    def test_check_and_generate_alerts_warning_threshold(self):
        """Test alert generation when warning threshold is exceeded"""
        # Mock warning threshold exceeded
        warning_metrics = StorageMetrics(
            total_bytes=9 * 1024**3,  # 9GB
            total_gb=9.0,
            limit_gb=10.0,
            usage_percentage=90.0,
            is_limit_exceeded=False,
            is_warning_exceeded=True,
            last_calculated=datetime.now(timezone.utc)
        )
        self.alert_system.monitor_service.get_storage_metrics.return_value = warning_metrics
        
        # Mock healthy health check
        self.alert_system.health_checker.check_comprehensive_health.return_value = Mock(
            overall_status=StorageHealthStatus.HEALTHY,
            components={},
            performance_metrics={}
        )
        
        alerts = self.alert_system.check_and_generate_alerts()
        
        # Should have warning threshold alert
        self.assertGreater(len(alerts), 0)
        warning_alert = next((a for a in alerts if a['type'] == StorageAlertType.WARNING_THRESHOLD_EXCEEDED.value), None)
        self.assertIsNotNone(warning_alert)
        self.assertEqual(warning_alert['severity'], StorageAlertSeverity.WARNING.value)
    
    def test_check_and_generate_alerts_configuration_error(self):
        """Test alert generation for configuration errors"""
        # Mock configuration error
        self.alert_system.config_service.validate_storage_config.return_value = False
        
        # Mock healthy health check
        self.alert_system.health_checker.check_comprehensive_health.return_value = Mock(
            overall_status=StorageHealthStatus.HEALTHY,
            components={},
            performance_metrics={}
        )
        
        alerts = self.alert_system.check_and_generate_alerts()
        
        # Should have configuration error alert
        self.assertGreater(len(alerts), 0)
        config_alert = next((a for a in alerts if a['type'] == StorageAlertType.CONFIGURATION_ERROR.value), None)
        self.assertIsNotNone(config_alert)
        self.assertEqual(config_alert['severity'], StorageAlertSeverity.CRITICAL.value)
    
    def test_check_and_generate_alerts_performance_degradation(self):
        """Test alert generation for performance degradation"""
        # Mock performance degradation
        self.alert_system.health_checker.check_comprehensive_health.return_value = Mock(
            overall_status=StorageHealthStatus.HEALTHY,
            components={},
            performance_metrics={
                'avg_component_response_time_ms': 3000.0,  # 3 seconds (degraded)
                'max_component_response_time_ms': 6000.0   # 6 seconds (critical)
            }
        )
        
        alerts = self.alert_system.check_and_generate_alerts()
        
        # Should have performance alerts
        self.assertGreater(len(alerts), 0)
        perf_alerts = [a for a in alerts if a['type'] == StorageAlertType.PERFORMANCE_DEGRADATION.value]
        self.assertGreater(len(perf_alerts), 0)
    
    def test_alert_suppression(self):
        """Test alert suppression functionality"""
        # Suppress limit exceeded alerts with the correct key format (type_severity)
        self.alert_system.suppress_alert_type(f"{StorageAlertType.LIMIT_EXCEEDED.value}_critical", duration_minutes=30)
        
        # Mock storage limit exceeded
        exceeded_metrics = StorageMetrics(
            total_bytes=11 * 1024**3,  # 11GB
            total_gb=11.0,
            limit_gb=10.0,
            usage_percentage=110.0,
            is_limit_exceeded=True,
            is_warning_exceeded=True,
            last_calculated=datetime.now(timezone.utc)
        )
        self.alert_system.monitor_service.get_storage_metrics.return_value = exceeded_metrics
        
        # Mock healthy health check
        self.alert_system.health_checker.check_comprehensive_health.return_value = Mock(
            overall_status=StorageHealthStatus.HEALTHY,
            components={},
            performance_metrics={}
        )
        
        alerts = self.alert_system.check_and_generate_alerts()
        
        # Should have no limit exceeded alerts due to suppression
        limit_alerts = [a for a in alerts if a['type'] == StorageAlertType.LIMIT_EXCEEDED.value]
        self.assertEqual(len(limit_alerts), 0)
    
    def test_get_alert_statistics(self):
        """Test getting alert statistics"""
        # Generate some alerts first
        self.alert_system.suppress_alert_type('test_alert', 60)
        
        stats = self.alert_system.get_alert_statistics()
        
        self.assertIn('suppressed_alerts', stats)
        self.assertIn('alert_counts', stats)
        self.assertIn('total_alerts_sent', stats)
        self.assertIn('suppressed_alert_types', stats)
        self.assertIn('timestamp', stats)
        
        self.assertEqual(stats['suppressed_alerts'], 1)
        self.assertIn('test_alert', stats['suppressed_alert_types'])


if __name__ == '__main__':
    unittest.main()
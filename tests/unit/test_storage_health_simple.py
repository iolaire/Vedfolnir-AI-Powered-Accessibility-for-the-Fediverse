# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Simple unit tests for storage health monitoring system.

Tests the core functionality of storage health monitoring components.
"""

import unittest
import tempfile
import shutil
import os
from unittest.mock import Mock, patch
from datetime import datetime, timezone

# Add project root to path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.services.monitoring.health.checkers.storage_health_checker import StorageHealthChecker, StorageHealthStatus
from app.services.storage.components.storage_configuration_service import StorageConfigurationService
from app.services.storage.components.storage_monitor_service import StorageMonitorService, StorageMetrics


class TestStorageHealthCheckerSimple(unittest.TestCase):
    """Simple test cases for StorageHealthChecker"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.storage_dir = os.path.join(self.temp_dir, 'storage', 'images')
        os.makedirs(self.storage_dir, exist_ok=True)
        
        # Create mock services
        self.mock_config_service = Mock(spec=StorageConfigurationService)
        self.mock_monitor_service = Mock(spec=StorageMonitorService)
        
        # Configure mocks with basic responses
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
        
        self.health_checker = StorageHealthChecker(
            config_service=self.mock_config_service,
            monitor_service=self.mock_monitor_service,
            enforcer_service=None  # No enforcer for simple tests
        )
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_health_checker_initialization(self):
        """Test that health checker initializes correctly"""
        self.assertIsNotNone(self.health_checker)
        self.assertEqual(self.health_checker.config_service, self.mock_config_service)
        self.assertEqual(self.health_checker.monitor_service, self.mock_monitor_service)
    
    def test_comprehensive_health_check_basic(self):
        """Test basic comprehensive health check"""
        health_result = self.health_checker.check_comprehensive_health()
        
        # Should return a health result
        self.assertIsNotNone(health_result)
        self.assertIn('configuration', health_result.components)
        self.assertIn('monitoring', health_result.components)
        self.assertIn('storage_directory', health_result.components)
        self.assertIn('performance', health_result.components)
        
        # Should have summary information
        self.assertIn('total_components', health_result.summary)
        self.assertIn('healthy_components', health_result.summary)
        self.assertGreater(health_result.summary['total_components'], 0)
    
    def test_configuration_health_check(self):
        """Test configuration health check component"""
        health_result = self.health_checker.check_comprehensive_health()
        config_health = health_result.components['configuration']
        
        self.assertEqual(config_health.status, StorageHealthStatus.HEALTHY)
        self.assertIn('valid', config_health.message.lower())
        self.assertIsNotNone(config_health.response_time_ms)
        self.assertGreater(config_health.response_time_ms, 0)
    
    def test_monitoring_health_check(self):
        """Test monitoring health check component"""
        health_result = self.health_checker.check_comprehensive_health()
        monitoring_health = health_result.components['monitoring']
        
        self.assertEqual(monitoring_health.status, StorageHealthStatus.HEALTHY)
        self.assertIsNotNone(monitoring_health.response_time_ms)
        self.assertIn('storage_metrics', monitoring_health.details)
        self.assertIn('cache_info', monitoring_health.details)
    
    def test_storage_directory_health_check(self):
        """Test storage directory health check component"""
        health_result = self.health_checker.check_comprehensive_health()
        directory_health = health_result.components['storage_directory']
        
        # Should be healthy since we created the directory
        self.assertEqual(directory_health.status, StorageHealthStatus.HEALTHY)
        self.assertIn('directory_path', directory_health.details)
        self.assertTrue(directory_health.details['exists'])
        self.assertTrue(directory_health.details['is_directory'])
    
    def test_performance_health_check(self):
        """Test performance health check component"""
        health_result = self.health_checker.check_comprehensive_health()
        performance_health = health_result.components['performance']
        
        self.assertIsNotNone(performance_health.response_time_ms)
        self.assertIn('metrics_collected', performance_health.metrics)
    
    def test_get_storage_health_metrics(self):
        """Test getting storage health metrics"""
        metrics = self.health_checker.get_storage_health_metrics()
        
        self.assertIn('storage_system_healthy', metrics)
        self.assertIn('storage_system_status', metrics)
        self.assertIn('storage_components_total', metrics)
        self.assertIn('storage_components_healthy', metrics)
        self.assertIn('storage_last_check_timestamp', metrics)
        
        # Should indicate healthy system
        self.assertEqual(metrics['storage_system_healthy'], 1)
        self.assertEqual(metrics['storage_system_status'], 'healthy')
    
    def test_get_storage_alerts_healthy_system(self):
        """Test getting storage alerts for healthy system"""
        alerts = self.health_checker.get_storage_alerts()
        
        self.assertIsInstance(alerts, list)
        # Healthy system should have no alerts
        self.assertEqual(len(alerts), 0)
    
    def test_configuration_error_handling(self):
        """Test handling of configuration errors"""
        # Mock configuration error
        self.mock_config_service.validate_storage_config.return_value = False
        
        health_result = self.health_checker.check_comprehensive_health()
        config_health = health_result.components['configuration']
        
        self.assertEqual(config_health.status, StorageHealthStatus.UNHEALTHY)
        self.assertIn('validation failed', config_health.message.lower())
    
    def test_monitoring_error_handling(self):
        """Test handling of monitoring errors"""
        # Mock monitoring error
        self.mock_monitor_service.get_storage_metrics.side_effect = Exception("Monitoring error")
        
        health_result = self.health_checker.check_comprehensive_health()
        monitoring_health = health_result.components['monitoring']
        
        self.assertEqual(monitoring_health.status, StorageHealthStatus.ERROR)
        self.assertIn('error', monitoring_health.message.lower())
        self.assertIn('error', monitoring_health.details)
    
    def test_storage_limit_exceeded_detection(self):
        """Test detection of storage limit exceeded"""
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
        monitoring_health = health_result.components['monitoring']
        
        self.assertEqual(monitoring_health.status, StorageHealthStatus.DEGRADED)
        self.assertIn('limit exceeded', monitoring_health.message.lower())
    
    def test_warning_threshold_exceeded_detection(self):
        """Test detection of warning threshold exceeded"""
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
        self.mock_monitor_service.get_storage_metrics.return_value = warning_metrics
        
        health_result = self.health_checker.check_comprehensive_health()
        monitoring_health = health_result.components['monitoring']
        
        self.assertEqual(monitoring_health.status, StorageHealthStatus.DEGRADED)
        self.assertIn('warning threshold exceeded', monitoring_health.message.lower())


class TestStorageHealthEndpointsIntegration(unittest.TestCase):
    """Test storage health endpoints integration"""
    
    def test_health_endpoints_import(self):
        """Test that health endpoints can be imported"""
        try:
            from app.services.storage.components.storage_health_endpoints import storage_health_bp, register_storage_health_endpoints
            self.assertIsNotNone(storage_health_bp)
            self.assertIsNotNone(register_storage_health_endpoints)
        except ImportError as e:
            self.fail(f"Could not import storage health endpoints: {e}")
    
    def test_dashboard_integration_import(self):
        """Test that dashboard integration can be imported"""
        try:
            from app.services.storage.components.storage_monitoring_dashboard_integration import StorageMonitoringDashboardIntegration
            self.assertIsNotNone(StorageMonitoringDashboardIntegration)
        except ImportError as e:
            self.fail(f"Could not import dashboard integration: {e}")
    
    def test_alert_system_import(self):
        """Test that alert system can be imported"""
        try:
            from app.services.storage.components.storage_alert_system import StorageAlertSystem, StorageAlertType, StorageAlertSeverity
            self.assertIsNotNone(StorageAlertSystem)
            self.assertIsNotNone(StorageAlertType)
            self.assertIsNotNone(StorageAlertSeverity)
        except ImportError as e:
            self.fail(f"Could not import alert system: {e}")


if __name__ == '__main__':
    unittest.main()
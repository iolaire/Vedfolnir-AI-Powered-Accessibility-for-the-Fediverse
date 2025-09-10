# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integration tests for Storage Warning Monitor system.

Tests the complete integration of warning threshold monitoring, logging,
admin dashboard notifications, and background monitoring functionality.
"""

import unittest
import tempfile
import shutil
import time
import os
from unittest.mock import Mock, patch
from datetime import datetime, timezone

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.services.storage.components.storage_warning_monitor import StorageWarningMonitor, StorageEventType
from app.services.storage.components.storage_warning_dashboard_integration import StorageWarningDashboardIntegration
from app.services.storage.components.storage_event_logger import StorageEventLogger, get_storage_logger
from app.services.storage.components.storage_configuration_service import StorageConfigurationService
from app.services.storage.components.storage_monitor_service import StorageMonitorService, StorageMetrics


class TestStorageWarningIntegration(unittest.TestCase):
    """Integration tests for storage warning system"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create temporary directory for test logs
        self.temp_dir = tempfile.mkdtemp()
        
        # Mock Redis client
        self.mock_redis = Mock()
        self.mock_redis.ping.return_value = True
        self.mock_redis.get.return_value = None
        self.mock_redis.set.return_value = True
        self.mock_redis.setex.return_value = True
        self.mock_redis.delete.return_value = True
        self.mock_redis.keys.return_value = []
        self.mock_redis.ttl.return_value = 3600
        
        # Mock configuration service
        self.mock_config = Mock(spec=StorageConfigurationService)
        self.mock_config.get_max_storage_gb.return_value = 10.0
        self.mock_config.get_warning_threshold_gb.return_value = 8.0
        self.mock_config.validate_storage_config.return_value = True
        self.mock_config._config = Mock()
        self.mock_config._config.warning_threshold_percentage = 80.0
        
        # Mock monitor service
        self.mock_monitor = Mock(spec=StorageMonitorService)
        
        # Create test metrics
        self.normal_metrics = StorageMetrics(
            total_bytes=5 * 1024**3,  # 5GB
            total_gb=5.0,
            limit_gb=10.0,
            usage_percentage=50.0,
            is_limit_exceeded=False,
            is_warning_exceeded=False,
            last_calculated=datetime.now()
        )
        
        self.warning_metrics = StorageMetrics(
            total_bytes=8.5 * 1024**3,  # 8.5GB
            total_gb=8.5,
            limit_gb=10.0,
            usage_percentage=85.0,
            is_limit_exceeded=False,
            is_warning_exceeded=True,
            last_calculated=datetime.now()
        )
        
        self.mock_monitor.get_storage_metrics.return_value = self.normal_metrics
    
    def tearDown(self):
        """Clean up test fixtures"""
        # Remove temporary directory
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_complete_warning_workflow(self):
        """Test complete warning detection and notification workflow"""
        # Create storage event logger
        event_logger = StorageEventLogger(
            log_dir=self.temp_dir,
            log_file="test_storage_events.log",
            enable_console=False
        )
        
        # Create warning monitor
        notifications_received = []
        
        def notification_callback(notification):
            notifications_received.append(notification)
        
        warning_monitor = StorageWarningMonitor(
            config_service=self.mock_config,
            monitor_service=self.mock_monitor,
            redis_client=self.mock_redis,
            notification_callback=notification_callback
        )
        
        # Test normal usage (no warnings)
        self.mock_monitor.get_storage_metrics.return_value = self.normal_metrics
        result = warning_monitor.check_warning_threshold()
        self.assertFalse(result)
        self.assertEqual(len(notifications_received), 0)
        
        # Test warning threshold exceeded
        self.mock_monitor.get_storage_metrics.return_value = self.warning_metrics
        result = warning_monitor.check_warning_threshold()
        self.assertTrue(result)
        self.assertGreater(len(notifications_received), 0)
        
        # Verify notification content
        warning_notification = notifications_received[0]
        self.assertEqual(warning_notification.severity, 'warning')
        self.assertIn('WARNING', warning_notification.message)
        self.assertEqual(warning_notification.storage_gb, 8.5)
        self.assertEqual(warning_notification.usage_percentage, 85.0)
        
        # Test log file was created
        log_file_path = os.path.join(self.temp_dir, "test_storage_events.log")
        self.assertTrue(os.path.exists(log_file_path))
        
        # Verify log content
        with open(log_file_path, 'r') as f:
            log_content = f.read()
            self.assertIn('warning_threshold_exceeded', log_content)
            self.assertIn('8.5', log_content)  # Storage usage
    
    def test_dashboard_integration(self):
        """Test dashboard integration functionality"""
        # Create warning monitor
        warning_monitor = StorageWarningMonitor(
            config_service=self.mock_config,
            monitor_service=self.mock_monitor,
            redis_client=self.mock_redis
        )
        
        # Mock admin dashboard to avoid Redis connection issues
        mock_admin_dashboard = Mock()
        mock_admin_dashboard.get_storage_dashboard_data.return_value = Mock(
            storage_gb=5.0,
            limit_gb=10.0,
            usage_percentage=50.0,
            status_color='green',
            is_blocked=False,
            block_reason=None,
            warning_threshold_gb=8.0,
            is_warning_exceeded=False,
            is_limit_exceeded=False
        )
        
        # Create dashboard integration
        dashboard_integration = StorageWarningDashboardIntegration(
            warning_monitor=warning_monitor,
            admin_dashboard=mock_admin_dashboard,
            config_service=self.mock_config,
            monitor_service=self.mock_monitor
        )
        
        # Test getting dashboard warning data with normal usage
        self.mock_monitor.get_storage_metrics.return_value = self.normal_metrics
        warning_data = dashboard_integration.get_dashboard_warning_data()
        
        self.assertFalse(warning_data.has_warnings)
        self.assertEqual(warning_data.warning_count, 0)
        self.assertEqual(warning_data.critical_count, 0)
        self.assertEqual(warning_data.storage_status, 'normal')
        self.assertFalse(warning_data.action_required)
        
        # Trigger warning threshold
        self.mock_monitor.get_storage_metrics.return_value = self.warning_metrics
        warning_monitor.check_warning_threshold()
        
        # Mock active notifications
        self.mock_redis.keys.return_value = ['vedfolnir:storage:warning_notifications:test1']
        notification_data = {
            'id': 'test1',
            'created_at': datetime.now(timezone.utc).isoformat(),
            'storage_gb': 8.5,
            'limit_gb': 10.0,
            'warning_threshold_gb': 8.0,
            'usage_percentage': 85.0,
            'message': 'Test warning message',
            'severity': 'warning',
            'acknowledged': False,
            'acknowledged_at': None,
            'acknowledged_by': None
        }
        self.mock_redis.get.return_value = json.dumps(notification_data)
        
        # Test getting dashboard warning data with warnings
        warning_data = dashboard_integration.get_dashboard_warning_data()
        
        self.assertTrue(warning_data.has_warnings)
        self.assertEqual(warning_data.warning_count, 1)
        self.assertEqual(warning_data.critical_count, 0)
        self.assertEqual(warning_data.storage_status, 'warning')
        self.assertTrue(warning_data.action_required)
    
    def test_background_monitoring_integration(self):
        """Test background monitoring integration"""
        # Create warning monitor with short check interval
        warning_monitor = StorageWarningMonitor(
            config_service=self.mock_config,
            monitor_service=self.mock_monitor,
            redis_client=self.mock_redis
        )
        
        # Set short check interval for testing
        warning_monitor.check_interval_seconds = 0.1
        
        # Start background monitoring
        result = warning_monitor.start_background_monitoring()
        self.assertTrue(result)
        self.assertTrue(warning_monitor._monitoring_active)
        
        # Wait for a few monitoring cycles
        time.sleep(0.3)
        
        # Verify metrics were checked multiple times
        self.assertGreater(self.mock_monitor.get_storage_metrics.call_count, 1)
        
        # Stop monitoring
        result = warning_monitor.stop_background_monitoring()
        self.assertTrue(result)
        self.assertFalse(warning_monitor._monitoring_active)
    
    def test_event_logging_integration(self):
        """Test event logging integration"""
        # Create event logger
        event_logger = StorageEventLogger(
            log_dir=self.temp_dir,
            log_file="integration_test.log",
            enable_console=False,
            enable_json_format=True
        )
        
        # Log various storage events
        event_logger.log_info("test_event", "Test info message", self.normal_metrics)
        event_logger.log_warning("warning_event", "Test warning message", self.warning_metrics)
        event_logger.log_threshold_exceeded(self.warning_metrics, "warning")
        
        # Verify log file exists and contains expected content
        log_file_path = os.path.join(self.temp_dir, "integration_test.log")
        self.assertTrue(os.path.exists(log_file_path))
        
        with open(log_file_path, 'r') as f:
            log_content = f.read()
            self.assertIn('test_event', log_content)
            self.assertIn('warning_event', log_content)
            self.assertIn('storage_warning_threshold_exceeded', log_content)
            self.assertIn('8.5', log_content)  # Warning metrics storage
    
    def test_health_check_integration(self):
        """Test health check integration across components"""
        # Create warning monitor
        warning_monitor = StorageWarningMonitor(
            config_service=self.mock_config,
            monitor_service=self.mock_monitor,
            redis_client=self.mock_redis
        )
        
        # Mock admin dashboard to avoid Redis connection issues
        mock_admin_dashboard = Mock()
        mock_admin_dashboard.health_check.return_value = {
            'overall_healthy': True,
            'redis_connected': True
        }
        
        # Create dashboard integration
        dashboard_integration = StorageWarningDashboardIntegration(
            warning_monitor=warning_monitor,
            admin_dashboard=mock_admin_dashboard,
            config_service=self.mock_config,
            monitor_service=self.mock_monitor
        )
        
        # Test health checks
        monitor_health = warning_monitor.health_check()
        dashboard_health = dashboard_integration.get_dashboard_health_status()
        
        # Verify health check results
        self.assertTrue(monitor_health['overall_healthy'])
        self.assertTrue(monitor_health['redis_connected'])
        self.assertTrue(monitor_health['config_service_healthy'])
        self.assertTrue(monitor_health['monitor_service_healthy'])
        
        self.assertTrue(dashboard_health['integration_healthy'])
        self.assertTrue(dashboard_health['overall_healthy'])
    
    def test_configuration_update_integration(self):
        """Test configuration update integration"""
        # Create warning monitor
        warning_monitor = StorageWarningMonitor(
            config_service=self.mock_config,
            monitor_service=self.mock_monitor,
            redis_client=self.mock_redis
        )
        
        # Test configuration update
        result = warning_monitor.update_monitoring_config(
            check_interval_seconds=600,
            event_retention_hours=240
        )
        
        self.assertTrue(result)
        self.assertEqual(warning_monitor.check_interval_seconds, 600)
        self.assertEqual(warning_monitor.event_retention_hours, 240)
        
        # Verify configuration was saved to Redis
        self.mock_redis.set.assert_called()


if __name__ == '__main__':
    # Import json for the test
    import json
    unittest.main()
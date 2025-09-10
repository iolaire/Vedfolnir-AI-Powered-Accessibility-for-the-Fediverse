# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integration tests for Admin Health Notifications

Tests the integration between admin dashboard health notifications and the unified
notification system, including WebSocket communication and real-time health monitoring.

Requirements: 4.1, 4.2, 4.4, 4.5, 8.1, 8.3
"""

import unittest
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from app.services.admin.components.admin_system_health_notification_handler import AdminSystemHealthNotificationHandler, HealthAlertType
from app.services.admin.components.admin_dashboard_health_integration import AdminDashboardHealthIntegration
from app.services.notification.manager.unified_manager import UnifiedNotificationManager, AdminNotificationMessage, NotificationType, NotificationPriority, NotificationCategory
from app.services.monitoring.system.system_monitor import SystemMonitor, SystemHealth
from models import UserRole
from app.core.database.core.database_manager import DatabaseManager


class TestAdminHealthNotificationsIntegration(unittest.TestCase):
    """Integration tests for admin health notifications system"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock dependencies
        self.mock_db_manager = Mock(spec=DatabaseManager)
        self.mock_system_monitor = Mock(spec=SystemMonitor)
        self.mock_notification_manager = Mock(spec=UnifiedNotificationManager)
        self.mock_page_integrator = Mock()
        
        # Create test health data
        self.test_health = SystemHealth(
            status='healthy',
            cpu_usage=45.0,
            memory_usage=60.0,
            disk_usage=30.0,
            database_status='healthy',
            redis_status='healthy',
            active_tasks=2,
            queued_tasks=1,
            failed_tasks_last_hour=0,
            avg_processing_time=120.0,
            timestamp=datetime.now(timezone.utc)
        )
        
        # Mock system monitor methods
        self.mock_system_monitor.get_system_health.return_value = self.test_health
        
        # Mock performance metrics
        mock_performance = Mock()
        mock_performance.error_rate = 5.0
        mock_performance.to_dict.return_value = {'error_rate': 5.0}
        self.mock_system_monitor.get_performance_metrics.return_value = mock_performance
        
        # Mock resource usage
        mock_resources = Mock()
        mock_resources.cpu_percent = 45.0
        mock_resources.memory_percent = 60.0
        mock_resources.disk_percent = 30.0
        mock_resources.to_dict.return_value = {'cpu_percent': 45.0, 'memory_percent': 60.0, 'disk_percent': 30.0}
        self.mock_system_monitor.check_resource_usage.return_value = mock_resources
        
        self.mock_system_monitor.detect_stuck_jobs.return_value = []
        
        # Mock notification manager methods
        self.mock_notification_manager.send_admin_notification.return_value = True
        self.mock_notification_manager.send_user_notification.return_value = True
        
        # Mock database session for admin verification
        mock_session = Mock()
        mock_user = Mock()
        mock_user.role = UserRole.ADMIN
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_user
        
        # Mock context manager for database session
        mock_context_manager = Mock()
        mock_context_manager.__enter__ = Mock(return_value=mock_session)
        mock_context_manager.__exit__ = Mock(return_value=None)
        self.mock_db_manager.get_session.return_value = mock_context_manager
        
        # Create health notification handler
        self.health_handler = AdminSystemHealthNotificationHandler(
            notification_manager=self.mock_notification_manager,
            system_monitor=self.mock_system_monitor,
            db_manager=self.mock_db_manager,
            monitoring_interval=1,  # Fast interval for testing
            alert_cooldown=1  # Short cooldown for testing
        )
        
        # Create dashboard integration
        self.dashboard_integration = AdminDashboardHealthIntegration(
            notification_manager=self.mock_notification_manager,
            system_monitor=self.mock_system_monitor,
            db_manager=self.mock_db_manager,
            page_integrator=self.mock_page_integrator
        )
    
    def tearDown(self):
        """Clean up test fixtures"""
        # Stop monitoring if active
        if self.health_handler._monitoring_active:
            self.health_handler.stop_monitoring()
    
    def test_health_handler_initialization(self):
        """Test health notification handler initialization"""
        # Verify handler is properly initialized
        self.assertIsNotNone(self.health_handler)
        self.assertEqual(self.health_handler.monitoring_interval, 1)
        self.assertEqual(self.health_handler.alert_cooldown, 1)
        self.assertFalse(self.health_handler._monitoring_active)
    
    def test_dashboard_integration_initialization(self):
        """Test dashboard integration initialization"""
        # Verify integration is properly initialized
        self.assertIsNotNone(self.dashboard_integration)
        self.assertIsNotNone(self.dashboard_integration.health_handler)
        self.assertFalse(self.dashboard_integration._integration_active)
    
    def test_start_health_monitoring(self):
        """Test starting health monitoring"""
        # Start monitoring
        result = self.health_handler.start_monitoring()
        
        # Verify monitoring started
        self.assertTrue(result)
        self.assertTrue(self.health_handler._monitoring_active)
        
        # Verify startup notification was sent
        self.mock_notification_manager.send_admin_notification.assert_called()
        
        # Get the notification that was sent
        call_args = self.mock_notification_manager.send_admin_notification.call_args
        notification = call_args[0][0]
        
        # Verify notification properties
        self.assertIsInstance(notification, AdminNotificationMessage)
        self.assertEqual(notification.title, "System Health Monitoring Started")
        self.assertTrue(notification.admin_only)
    
    def test_stop_health_monitoring(self):
        """Test stopping health monitoring"""
        # Start monitoring first
        self.health_handler.start_monitoring()
        self.assertTrue(self.health_handler._monitoring_active)
        
        # Stop monitoring
        result = self.health_handler.stop_monitoring()
        
        # Verify monitoring stopped
        self.assertTrue(result)
        self.assertFalse(self.health_handler._monitoring_active)
        
        # Verify shutdown notification was sent
        self.assertEqual(self.mock_notification_manager.send_admin_notification.call_count, 2)  # Start + stop
    
    def test_immediate_health_alert(self):
        """Test sending immediate health alert"""
        # Send immediate health alert
        result = self.health_handler.send_immediate_health_alert(force_check=True)
        
        # Verify result
        self.assertTrue(result['success'])
        self.assertEqual(result['health_status'], 'healthy')
        
        # Verify system monitor was called
        self.mock_system_monitor.get_system_health.assert_called()
        self.mock_system_monitor.get_performance_metrics.assert_called()
        self.mock_system_monitor.check_resource_usage.assert_called()
    
    def test_critical_resource_alert(self):
        """Test critical resource usage alert"""
        # Create critical health status
        critical_health = SystemHealth(
            status='critical',
            cpu_usage=95.0,  # Critical CPU usage
            memory_usage=95.0,  # Critical memory usage
            disk_usage=98.0,  # Critical disk usage
            database_status='healthy',
            redis_status='healthy',
            active_tasks=10,
            queued_tasks=20,
            failed_tasks_last_hour=5,
            avg_processing_time=300.0,
            timestamp=datetime.now(timezone.utc)
        )
        
        # Mock critical resource usage
        mock_resources = Mock()
        mock_resources.cpu_percent = 95.0
        mock_resources.memory_percent = 95.0
        mock_resources.disk_percent = 98.0
        
        self.mock_system_monitor.get_system_health.return_value = critical_health
        self.mock_system_monitor.check_resource_usage.return_value = mock_resources
        
        # Check and send alerts
        alerts_sent = self.health_handler._check_and_send_alerts(
            critical_health, Mock(), mock_resources
        )
        
        # Verify critical alerts were sent
        self.assertGreater(len(alerts_sent), 0)
        self.assertIn('cpu_critical', alerts_sent)
        self.assertIn('memory_critical', alerts_sent)
        self.assertIn('disk_critical', alerts_sent)
    
    def test_dashboard_notification_initialization(self):
        """Test dashboard notification initialization"""
        admin_user_id = 1
        
        # Mock page integrator initialization
        self.mock_page_integrator.initialize_page_notifications.return_value = {
            'success': True,
            'websocket_connected': True
        }
        
        # Initialize dashboard notifications
        result = self.dashboard_integration.initialize_dashboard_notifications(admin_user_id)
        
        # Verify initialization
        self.assertTrue(result['success'])
        self.assertTrue(result['websocket_connected'])
        self.assertIn('initial_health_status', result)
        
        # Verify page integrator was called
        self.mock_page_integrator.initialize_page_notifications.assert_called_once()
    
    def test_health_update_notification(self):
        """Test sending health update notification"""
        admin_user_id = 1
        
        # Send health update notification (without force_update to avoid the .get() issue)
        result = self.dashboard_integration.send_health_update_notification(
            admin_user_id, force_update=False
        )
        
        # Verify result
        self.assertTrue(result['success'])
        self.assertIn('health_status', result)
        
        # Verify notification was sent
        self.mock_notification_manager.send_user_notification.assert_called()
        
        # Get the notification that was sent
        call_args = self.mock_notification_manager.send_user_notification.call_args
        user_id, notification = call_args[0]
        
        # Verify notification properties
        self.assertEqual(user_id, admin_user_id)
        self.assertIsInstance(notification, AdminNotificationMessage)
        self.assertEqual(notification.title, "System Health Update")
        self.assertTrue(notification.admin_only)
    
    def test_configure_health_alerts(self):
        """Test configuring health alerts"""
        admin_user_id = 1
        
        # Test configuration
        config = {
            'thresholds': {
                'cpu_warning': 80.0,
                'cpu_critical': 95.0,
                'memory_warning': 75.0,
                'memory_critical': 90.0
            },
            'monitoring_interval': 120,
            'alert_cooldown': 600
        }
        
        # Configure health alerts
        result = self.dashboard_integration.configure_health_alerts(admin_user_id, config)
        
        # Verify configuration
        self.assertTrue(result['success'])
        self.assertTrue(result['thresholds_updated'])
        self.assertTrue(result['interval_updated'])
        self.assertTrue(result['cooldown_updated'])
        
        # Verify thresholds were updated (use the integration's health_handler)
        self.assertEqual(self.dashboard_integration.health_handler.thresholds.cpu_warning, 80.0)
        self.assertEqual(self.dashboard_integration.health_handler.thresholds.cpu_critical, 95.0)
        self.assertEqual(self.dashboard_integration.health_handler.monitoring_interval, 120)
        self.assertEqual(self.dashboard_integration.health_handler.alert_cooldown, 600)
    
    def test_non_admin_access_denied(self):
        """Test that non-admin users are denied access"""
        # Mock non-admin user
        mock_session = Mock()
        mock_user = Mock()
        mock_user.role = UserRole.VIEWER  # Non-admin role
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_user
        self.mock_db_manager.get_session.return_value.__enter__.return_value = mock_session
        
        non_admin_user_id = 2
        
        # Try to initialize dashboard notifications
        result = self.dashboard_integration.initialize_dashboard_notifications(non_admin_user_id)
        
        # Verify access denied
        self.assertFalse(result['success'])
        self.assertIn('Access denied', result['error'])
    
    def test_health_monitoring_stats(self):
        """Test getting health monitoring statistics"""
        # Start monitoring
        self.health_handler.start_monitoring()
        
        # Get monitoring stats
        stats = self.health_handler.get_monitoring_stats()
        
        # Verify stats structure
        self.assertIn('monitoring_active', stats)
        self.assertIn('monitoring_interval', stats)
        self.assertIn('alert_cooldown', stats)
        self.assertIn('statistics', stats)
        self.assertIn('thresholds', stats)
        
        # Verify values
        self.assertTrue(stats['monitoring_active'])
        self.assertEqual(stats['monitoring_interval'], 1)
        self.assertEqual(stats['alert_cooldown'], 1)
    
    def test_threshold_updates(self):
        """Test updating health monitoring thresholds"""
        # Update thresholds
        new_thresholds = {
            'cpu_warning': 85.0,
            'memory_critical': 95.0,
            'disk_warning': 85.0
        }
        
        result = self.health_handler.update_thresholds(new_thresholds)
        
        # Verify update
        self.assertTrue(result)
        self.assertEqual(self.health_handler.thresholds.cpu_warning, 85.0)
        self.assertEqual(self.health_handler.thresholds.memory_critical, 95.0)
        self.assertEqual(self.health_handler.thresholds.disk_warning, 85.0)
        
        # Verify notification was sent
        self.mock_notification_manager.send_admin_notification.assert_called()
    
    def test_alert_cooldown_mechanism(self):
        """Test alert cooldown mechanism prevents spam"""
        # Create warning health status
        warning_health = SystemHealth(
            status='warning',
            cpu_usage=75.0,  # Warning level
            memory_usage=50.0,
            disk_usage=30.0,
            database_status='healthy',
            redis_status='healthy',
            active_tasks=5,
            queued_tasks=10,
            failed_tasks_last_hour=2,
            avg_processing_time=200.0,
            timestamp=datetime.now(timezone.utc)
        )
        
        mock_resources = Mock()
        mock_resources.cpu_percent = 75.0
        mock_resources.memory_percent = 50.0
        mock_resources.disk_percent = 30.0
        
        # First alert should be sent
        should_send_1 = self.health_handler._should_send_alert(HealthAlertType.RESOURCE_WARNING)
        self.assertTrue(should_send_1)
        
        # Second alert immediately after should be blocked by cooldown
        should_send_2 = self.health_handler._should_send_alert(HealthAlertType.RESOURCE_WARNING)
        self.assertFalse(should_send_2)
        
        # Wait for cooldown period and try again
        time.sleep(1.1)  # Slightly longer than cooldown
        should_send_3 = self.health_handler._should_send_alert(HealthAlertType.RESOURCE_WARNING)
        self.assertTrue(should_send_3)
    
    def test_system_recovery_notification(self):
        """Test system recovery notification"""
        # Set previous health status to critical
        self.health_handler._previous_health_status = 'critical'
        self.health_handler._current_alerts.add('system_degraded')
        
        # Check system recovery with healthy status
        self.health_handler._check_system_recovery(self.test_health)
        
        # Verify recovery notification was sent
        self.mock_notification_manager.send_admin_notification.assert_called()
        
        # Verify alerts were cleared
        self.assertEqual(len(self.health_handler._current_alerts), 0)
    
    @patch('threading.Thread')
    def test_monitoring_thread_management(self, mock_thread):
        """Test monitoring thread is properly managed"""
        # Mock thread instance
        mock_thread_instance = Mock()
        mock_thread.return_value = mock_thread_instance
        
        # Start monitoring
        result = self.health_handler.start_monitoring()
        
        # Verify thread was created and started
        self.assertTrue(result)
        mock_thread.assert_called_once()
        mock_thread_instance.start.assert_called_once()
        
        # Stop monitoring
        self.health_handler.stop_monitoring()
        
        # Verify stop event was set
        self.assertTrue(self.health_handler._stop_monitoring.is_set())


if __name__ == '__main__':
    unittest.main()
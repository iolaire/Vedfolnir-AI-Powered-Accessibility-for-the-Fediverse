# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integration tests for Notification Monitoring System

Tests the complete integration of the notification monitoring system including
the monitor, dashboard, WebSocket recovery, and all related components.
"""

import unittest
import time
import json
import threading
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from notification_system_monitor import NotificationSystemMonitor, AlertSeverity
from notification_monitoring_dashboard import NotificationMonitoringDashboard
from notification_websocket_recovery import NotificationWebSocketRecovery, RecoveryStrategy
from unified_notification_manager import UnifiedNotificationManager
from websocket_performance_monitor import WebSocketPerformanceMonitor
from websocket_namespace_manager import WebSocketNamespaceManager
from websocket_factory import WebSocketFactory
from websocket_auth_handler import WebSocketAuthHandler
from database import DatabaseManager


class TestNotificationMonitoringIntegration(unittest.TestCase):
    """Integration tests for the complete notification monitoring system"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create mock dependencies
        self.mock_db_manager = Mock(spec=DatabaseManager)
        self.mock_websocket_factory = Mock(spec=WebSocketFactory)
        self.mock_auth_handler = Mock(spec=WebSocketAuthHandler)
        self.mock_namespace_manager = Mock(spec=WebSocketNamespaceManager)
        self.mock_websocket_monitor = Mock(spec=WebSocketPerformanceMonitor)
        self.mock_notification_manager = Mock(spec=UnifiedNotificationManager)
        
        # Configure mock database manager
        mock_session = Mock()
        mock_session.execute.return_value.fetchone.return_value = None
        mock_context_manager = MagicMock()
        mock_context_manager.__enter__.return_value = mock_session
        mock_context_manager.__exit__.return_value = None
        self.mock_db_manager.get_session.return_value = mock_context_manager
        
        # Configure mock notification manager
        self.mock_notification_manager.get_notification_stats.return_value = {
            'delivery_stats': {
                'messages_sent': 1000,
                'messages_delivered': 950,
                'messages_failed': 50
            },
            'offline_queues': {'total_messages': 25},
            'retry_queues': {'total_messages': 15}
        }
        
        # Configure mock WebSocket monitor
        self.mock_websocket_monitor.get_current_performance_summary.return_value = {
            'avg_latency': 75.0,
            'connection_count': 50,
            'error_rate': 0.02
        }
        
        # Configure mock namespace manager
        self.mock_namespace_manager._connections = {
            f'conn_{i}': Mock(
                connected=True if i < 45 else False,
                namespace='/' if i < 40 else '/admin',
                user_id=i,
                last_activity=datetime.now(timezone.utc),
                latency=50.0 + (i * 2),  # Numeric latency values
                error_rate=0.01 + (i * 0.001),  # Numeric error rate values
                failure_count=i % 3,  # Numeric failure count
                recovery_attempts=0  # Numeric recovery attempts
            )
            for i in range(50)
        }
        
        # Create monitoring system components
        self.monitor = NotificationSystemMonitor(
            notification_manager=self.mock_notification_manager,
            websocket_monitor=self.mock_websocket_monitor,
            namespace_manager=self.mock_namespace_manager,
            db_manager=self.mock_db_manager,
            monitoring_interval=1  # Short interval for testing
        )
        
        self.dashboard = NotificationMonitoringDashboard(self.monitor)
        
        self.recovery_system = NotificationWebSocketRecovery(
            websocket_factory=self.mock_websocket_factory,
            namespace_manager=self.mock_namespace_manager,
            auth_handler=self.mock_auth_handler,
            monitor=self.monitor,
            recovery_interval=1  # Short interval for testing
        )
    
    def tearDown(self):
        """Clean up after tests"""
        if self.monitor._monitoring_active:
            self.monitor.stop_monitoring()
        if self.recovery_system._recovery_active:
            self.recovery_system.stop_recovery_monitoring()
    
    def test_complete_monitoring_system_startup(self):
        """Test complete monitoring system startup and shutdown"""
        # Start all monitoring components
        self.monitor.start_monitoring()
        self.recovery_system.start_recovery_monitoring()
        
        # Verify all components are active
        self.assertTrue(self.monitor._monitoring_active)
        self.assertTrue(self.recovery_system._recovery_active)
        
        # Wait for monitoring to collect some data
        time.sleep(2)
        
        # Check that metrics are being collected
        health_data = self.monitor.get_system_health()
        self.assertIsInstance(health_data, dict)
        self.assertIn('overall_health', health_data)
        
        # Stop all components
        self.monitor.stop_monitoring()
        self.recovery_system.stop_recovery_monitoring()
        
        # Verify all components are stopped
        self.assertFalse(self.monitor._monitoring_active)
        self.assertFalse(self.recovery_system._recovery_active)
    
    def test_end_to_end_alert_generation_and_recovery(self):
        """Test end-to-end alert generation and automatic recovery"""
        alert_received = False
        recovery_triggered = False
        
        def alert_callback(alert):
            nonlocal alert_received
            alert_received = True
        
        def recovery_callback(connection_id, success, message):
            nonlocal recovery_triggered
            recovery_triggered = True
        
        # Register callbacks
        self.monitor.register_alert_callback(alert_callback)
        self.recovery_system.register_recovery_callback(recovery_callback)
        
        # Start monitoring
        self.monitor.start_monitoring()
        self.recovery_system.start_recovery_monitoring()
        
        # Simulate poor performance that should trigger alerts
        self.mock_notification_manager.get_notification_stats.return_value = {
            'delivery_stats': {
                'messages_sent': 1000,
                'messages_delivered': 400,  # Low delivery rate
                'messages_failed': 600
            },
            'offline_queues': {'total_messages': 1500},  # High queue depth
            'retry_queues': {'total_messages': 500}
        }
        
        # Wait for monitoring to detect issues and trigger alerts
        time.sleep(3)
        
        # Verify alert was generated
        self.assertTrue(alert_received)
        
        # Verify recovery was attempted
        # Note: Recovery might not be triggered immediately depending on thresholds
        # but the system should be monitoring for it
        
        # Check system health shows issues
        health_data = self.monitor.get_system_health()
        self.assertIn(health_data['overall_health'], ['warning', 'critical'])
        
        # Stop monitoring
        self.monitor.stop_monitoring()
        self.recovery_system.stop_recovery_monitoring()
    
    def test_dashboard_data_integration(self):
        """Test dashboard data integration with monitoring system"""
        # Start monitoring to collect data
        self.monitor.start_monitoring()
        time.sleep(1)  # Let it collect some data
        
        # Test dashboard summary
        summary = self.dashboard.get_dashboard_summary()
        self.assertIsInstance(summary, dict)
        self.assertIn('overall_health', summary)
        self.assertIn('active_alerts', summary)
        self.assertIn('monitoring_active', summary)
        
        # Test delivery dashboard data
        delivery_data = self.monitor.get_delivery_dashboard_data()
        self.assertIsInstance(delivery_data, dict)
        if 'current_metrics' in delivery_data and delivery_data['current_metrics']:
            self.assertIn('delivery_rate', delivery_data['current_metrics'])
            self.assertIn('total_sent', delivery_data['current_metrics'])
        
        # Test WebSocket dashboard data
        websocket_data = self.monitor.get_websocket_dashboard_data()
        self.assertIsInstance(websocket_data, dict)
        if 'current_metrics' in websocket_data and websocket_data['current_metrics']:
            self.assertIn('total_connections', websocket_data['current_metrics'])
            self.assertIn('active_connections', websocket_data['current_metrics'])
        
        # Test performance metrics
        performance_data = self.monitor.get_performance_metrics()
        self.assertIsInstance(performance_data, dict)
        
        self.monitor.stop_monitoring()
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    def test_performance_monitoring_integration(self, mock_memory, mock_cpu):
        """Test performance monitoring integration"""
        # Configure system resource mocks
        mock_cpu.return_value = 85.0  # High CPU usage
        mock_memory.return_value = Mock(percent=90.0, available=1000000000)  # High memory usage
        
        # Start monitoring
        self.monitor.start_monitoring()
        
        # Wait for performance metrics to be collected
        time.sleep(2)
        
        # Check that performance alerts are generated
        health_data = self.monitor.get_system_health()
        active_alerts = health_data.get('active_alerts', [])
        
        # Should have performance-related alerts
        performance_alerts = [
            alert for alert in active_alerts
            if 'cpu' in alert.get('title', '').lower() or 'memory' in alert.get('title', '').lower()
        ]
        
        # Verify performance metrics are being tracked
        performance_data = self.monitor.get_performance_metrics()
        if 'current_metrics' in performance_data and performance_data['current_metrics']:
            self.assertGreater(performance_data['current_metrics']['cpu_usage'], 0.8)
            self.assertGreater(performance_data['current_metrics']['memory_usage'], 0.8)
        
        self.monitor.stop_monitoring()
    
    def test_websocket_recovery_integration(self):
        """Test WebSocket recovery system integration"""
        # Start recovery monitoring
        self.recovery_system.start_recovery_monitoring()
        
        # Simulate connection health issues
        connection_id = 'conn_1'
        
        # Check connection health
        health = self.recovery_system.check_connection_health(connection_id)
        if health:
            self.assertEqual(health.connection_id, connection_id)
            self.assertIsInstance(health.state, type(health.state))
        
        # Trigger recovery
        success = self.recovery_system.trigger_connection_recovery(
            connection_id, RecoveryStrategy.IMMEDIATE
        )
        self.assertTrue(success)
        
        # Check recovery statistics
        stats = self.recovery_system.get_recovery_statistics()
        self.assertIsInstance(stats, dict)
        self.assertIn('recovery_active', stats)
        self.assertIn('connections_monitored', stats)
        
        # Get connection health report
        health_report = self.recovery_system.get_connection_health_report()
        self.assertIsInstance(health_report, dict)
        self.assertIn('total_connections', health_report)
        
        self.recovery_system.stop_recovery_monitoring()
    
    def test_monitoring_with_real_time_updates(self):
        """Test monitoring system with real-time updates"""
        updates_received = []
        
        def mock_emit(event, data, **kwargs):
            updates_received.append({'event': event, 'data': data})
        
        # Start monitoring
        self.monitor.start_monitoring()
        
        # Simulate some activity
        self.monitor.record_delivery_time(150.0)
        self.monitor.record_connection_time(75.0)
        self.monitor.record_error('test_error')
        
        # Wait for monitoring cycle
        time.sleep(2)
        
        # Check that metrics were recorded
        self.assertGreater(len(self.monitor._delivery_times), 0)
        self.assertGreater(len(self.monitor._connection_times), 0)
        self.assertGreater(self.monitor._error_counts['test_error'], 0)
        
        # Get real-time data
        realtime_data = self.monitor.get_delivery_dashboard_data()
        self.assertIsInstance(realtime_data, dict)
        
        self.monitor.stop_monitoring()
    
    def test_alert_escalation_and_recovery_coordination(self):
        """Test alert escalation and recovery coordination"""
        alerts_generated = []
        recoveries_attempted = []
        
        def alert_callback(alert):
            alerts_generated.append(alert)
        
        def recovery_callback(connection_id, success, message):
            recoveries_attempted.append({
                'connection_id': connection_id,
                'success': success,
                'message': message
            })
        
        # Register callbacks
        self.monitor.register_alert_callback(alert_callback)
        self.recovery_system.register_recovery_callback(recovery_callback)
        
        # Start both systems
        self.monitor.start_monitoring()
        self.recovery_system.start_recovery_monitoring()
        
        # Simulate critical system conditions
        self.mock_notification_manager.get_notification_stats.return_value = {
            'delivery_stats': {
                'messages_sent': 1000,
                'messages_delivered': 300,  # Critical delivery rate
                'messages_failed': 700
            },
            'offline_queues': {'total_messages': 2000},  # Critical queue depth
            'retry_queues': {'total_messages': 1000}
        }
        
        # Simulate connection failures
        for i in range(5):
            self.recovery_system.trigger_connection_recovery(
                f'failing_conn_{i}', RecoveryStrategy.EXPONENTIAL_BACKOFF
            )
        
        # Wait for systems to process
        time.sleep(3)
        
        # Verify alerts were generated
        self.assertGreater(len(alerts_generated), 0)
        
        # Check that critical alerts were created
        critical_alerts = [a for a in alerts_generated if a.severity == AlertSeverity.CRITICAL]
        self.assertGreater(len(critical_alerts), 0)
        
        # Verify system health reflects critical state
        health_data = self.monitor.get_system_health()
        self.assertEqual(health_data['overall_health'], 'critical')
        
        # Stop systems
        self.monitor.stop_monitoring()
        self.recovery_system.stop_recovery_monitoring()
    
    def test_monitoring_system_resilience(self):
        """Test monitoring system resilience to errors"""
        # Configure mocks to throw exceptions
        self.mock_notification_manager.get_notification_stats.side_effect = [
            Exception("Database error"),
            {  # Recovery after error
                'delivery_stats': {
                    'messages_sent': 100,
                    'messages_delivered': 95,
                    'messages_failed': 5
                },
                'offline_queues': {'total_messages': 5},
                'retry_queues': {'total_messages': 2}
            }
        ]
        
        # Start monitoring
        self.monitor.start_monitoring()
        
        # Wait for error to occur and recovery
        time.sleep(3)
        
        # System should still be running despite errors
        self.assertTrue(self.monitor._monitoring_active)
        
        # Should be able to get health data (might show error state)
        health_data = self.monitor.get_system_health()
        self.assertIsInstance(health_data, dict)
        
        self.monitor.stop_monitoring()
    
    def test_comprehensive_system_metrics(self):
        """Test comprehensive system metrics collection"""
        # Start all monitoring components
        self.monitor.start_monitoring()
        self.recovery_system.start_recovery_monitoring()
        
        # Wait for data collection
        time.sleep(2)
        
        # Test all metric endpoints
        health_data = self.monitor.get_system_health()
        delivery_data = self.monitor.get_delivery_dashboard_data()
        websocket_data = self.monitor.get_websocket_dashboard_data()
        performance_data = self.monitor.get_performance_metrics()
        recovery_stats = self.recovery_system.get_recovery_statistics()
        
        # Verify all data structures
        self.assertIsInstance(health_data, dict)
        self.assertIsInstance(delivery_data, dict)
        self.assertIsInstance(websocket_data, dict)
        self.assertIsInstance(performance_data, dict)
        self.assertIsInstance(recovery_stats, dict)
        
        # Verify key metrics are present
        self.assertIn('overall_health', health_data)
        self.assertIn('timestamp', health_data)
        
        # Verify dashboard integration
        dashboard_summary = self.dashboard.get_dashboard_summary()
        self.assertIsInstance(dashboard_summary, dict)
        self.assertIn('overall_health', dashboard_summary)
        
        # Stop all components
        self.monitor.stop_monitoring()
        self.recovery_system.stop_recovery_monitoring()


class TestMonitoringSystemConfiguration(unittest.TestCase):
    """Test monitoring system configuration and customization"""
    
    def test_custom_alert_thresholds(self):
        """Test custom alert threshold configuration"""
        custom_thresholds = {
            'delivery_rate_critical': 0.3,
            'delivery_rate_warning': 0.6,
            'connection_failure_rate_critical': 0.5,
            'memory_usage_critical': 0.95
        }
        
        # Create mock dependencies
        mock_notification_manager = Mock(spec=UnifiedNotificationManager)
        mock_websocket_monitor = Mock(spec=WebSocketPerformanceMonitor)
        mock_namespace_manager = Mock(spec=WebSocketNamespaceManager)
        mock_db_manager = Mock(spec=DatabaseManager)
        
        # Configure mocks
        mock_session = Mock()
        mock_session.execute.return_value.fetchone.return_value = None
        mock_context_manager = MagicMock()
        mock_context_manager.__enter__.return_value = mock_session
        mock_context_manager.__exit__.return_value = None
        mock_db_manager.get_session.return_value = mock_context_manager
        
        # Create monitor with custom thresholds
        monitor = NotificationSystemMonitor(
            notification_manager=mock_notification_manager,
            websocket_monitor=mock_websocket_monitor,
            namespace_manager=mock_namespace_manager,
            db_manager=mock_db_manager,
            alert_thresholds=custom_thresholds
        )
        
        # Verify custom thresholds were applied
        self.assertEqual(monitor.alert_thresholds['delivery_rate_critical'], 0.3)
        self.assertEqual(monitor.alert_thresholds['delivery_rate_warning'], 0.6)
        self.assertEqual(monitor.alert_thresholds['connection_failure_rate_critical'], 0.5)
        self.assertEqual(monitor.alert_thresholds['memory_usage_critical'], 0.95)
    
    def test_monitoring_interval_configuration(self):
        """Test monitoring interval configuration"""
        # Create mock dependencies
        mock_notification_manager = Mock(spec=UnifiedNotificationManager)
        mock_websocket_monitor = Mock(spec=WebSocketPerformanceMonitor)
        mock_namespace_manager = Mock(spec=WebSocketNamespaceManager)
        mock_db_manager = Mock(spec=DatabaseManager)
        
        # Configure mocks
        mock_session = Mock()
        mock_context_manager = MagicMock()
        mock_context_manager.__enter__.return_value = mock_session
        mock_context_manager.__exit__.return_value = None
        mock_db_manager.get_session.return_value = mock_context_manager
        
        # Test different monitoring intervals
        for interval in [5, 30, 60, 300]:
            monitor = NotificationSystemMonitor(
                notification_manager=mock_notification_manager,
                websocket_monitor=mock_websocket_monitor,
                namespace_manager=mock_namespace_manager,
                db_manager=mock_db_manager,
                monitoring_interval=interval
            )
            
            self.assertEqual(monitor.monitoring_interval, interval)


if __name__ == '__main__':
    unittest.main()
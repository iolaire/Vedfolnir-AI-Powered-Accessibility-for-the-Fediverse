# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for Notification System Monitor

Tests the monitoring and health check functionality for the unified notification system,
including metrics collection, alerting, and recovery mechanisms.
"""

import unittest
import time
import threading
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone, timedelta
from collections import deque

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from notification_system_monitor import (
    NotificationSystemMonitor, NotificationSystemHealth, AlertSeverity,
    NotificationDeliveryMetrics, WebSocketConnectionMetrics, SystemPerformanceMetrics,
    NotificationSystemAlert, create_notification_system_monitor
)
from unified_notification_manager import UnifiedNotificationManager
from websocket_performance_monitor import WebSocketPerformanceMonitor
from websocket_namespace_manager import WebSocketNamespaceManager
from database import DatabaseManager


class TestNotificationSystemMonitor(unittest.TestCase):
    """Test cases for NotificationSystemMonitor"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create mock dependencies
        self.mock_notification_manager = Mock(spec=UnifiedNotificationManager)
        self.mock_websocket_monitor = Mock(spec=WebSocketPerformanceMonitor)
        self.mock_namespace_manager = Mock(spec=WebSocketNamespaceManager)
        self.mock_db_manager = Mock(spec=DatabaseManager)
        
        # Configure mock notification manager
        self.mock_notification_manager.get_notification_stats.return_value = {
            'delivery_stats': {
                'messages_sent': 100,
                'messages_delivered': 95,
                'messages_failed': 5
            },
            'offline_queues': {'total_messages': 10},
            'retry_queues': {'total_messages': 5}
        }
        
        # Configure mock WebSocket monitor
        self.mock_websocket_monitor.get_current_performance_summary.return_value = {
            'avg_latency': 50.0,
            'connection_count': 25
        }
        
        # Configure mock namespace manager
        self.mock_namespace_manager._connections = {
            'conn1': Mock(connected=True, namespace='/'),
            'conn2': Mock(connected=True, namespace='/admin'),
            'conn3': Mock(connected=False, namespace='/')
        }
        
        # Configure mock database manager
        mock_session = Mock()
        mock_session.execute.return_value.fetchone.return_value = None
        mock_context_manager = MagicMock()
        mock_context_manager.__enter__.return_value = mock_session
        mock_context_manager.__exit__.return_value = None
        self.mock_db_manager.get_session.return_value = mock_context_manager
        
        # Create monitor instance
        self.monitor = NotificationSystemMonitor(
            notification_manager=self.mock_notification_manager,
            websocket_monitor=self.mock_websocket_monitor,
            namespace_manager=self.mock_namespace_manager,
            db_manager=self.mock_db_manager,
            monitoring_interval=1  # Short interval for testing
        )
    
    def tearDown(self):
        """Clean up after tests"""
        if self.monitor._monitoring_active:
            self.monitor.stop_monitoring()
    
    def test_monitor_initialization(self):
        """Test monitor initialization"""
        self.assertIsNotNone(self.monitor)
        self.assertFalse(self.monitor._monitoring_active)
        self.assertEqual(self.monitor.monitoring_interval, 1)
        self.assertIsInstance(self.monitor.alert_thresholds, dict)
        self.assertIn('delivery_rate_critical', self.monitor.alert_thresholds)
    
    def test_start_stop_monitoring(self):
        """Test starting and stopping monitoring"""
        # Test start monitoring
        self.monitor.start_monitoring()
        self.assertTrue(self.monitor._monitoring_active)
        self.assertIsNotNone(self.monitor._monitoring_thread)
        
        # Wait a moment for thread to start
        time.sleep(0.1)
        self.assertTrue(self.monitor._monitoring_thread.is_alive())
        
        # Test stop monitoring
        self.monitor.stop_monitoring()
        self.assertFalse(self.monitor._monitoring_active)
    
    def test_collect_delivery_metrics(self):
        """Test delivery metrics collection"""
        metrics = self.monitor._collect_delivery_metrics()
        
        self.assertIsInstance(metrics, NotificationDeliveryMetrics)
        self.assertEqual(metrics.total_sent, 100)
        self.assertEqual(metrics.total_delivered, 95)
        self.assertEqual(metrics.total_failed, 5)
        self.assertEqual(metrics.delivery_rate, 0.95)
        self.assertEqual(metrics.queue_depth, 15)  # offline + retry queues
    
    def test_collect_connection_metrics(self):
        """Test WebSocket connection metrics collection"""
        # Add some connection times to simulate attempts
        self.monitor._connection_times.extend([100, 200, 300])  # 3 attempts
        
        metrics = self.monitor._collect_connection_metrics()
        
        self.assertIsInstance(metrics, WebSocketConnectionMetrics)
        self.assertEqual(metrics.total_connections, 3)
        self.assertEqual(metrics.active_connections, 2)
        self.assertEqual(metrics.failed_connections, 1)  # 3 attempts - 2 successful = 1 failed
        self.assertIn('/', metrics.namespace_distribution)
        self.assertIn('/admin', metrics.namespace_distribution)
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    def test_collect_performance_metrics(self, mock_memory, mock_cpu):
        """Test system performance metrics collection"""
        # Configure mocks
        mock_cpu.return_value = 45.5
        mock_memory.return_value = Mock(percent=65.0, available=4000000000)
        
        metrics = self.monitor._collect_performance_metrics()
        
        self.assertIsInstance(metrics, SystemPerformanceMetrics)
        self.assertEqual(metrics.cpu_usage, 45.5)
        self.assertEqual(metrics.memory_usage, 0.65)
        self.assertEqual(metrics.memory_available, 4000000000)
    
    def test_determine_health_status(self):
        """Test health status determination"""
        # Create test metrics
        delivery_metrics = NotificationDeliveryMetrics(
            total_sent=100, total_delivered=95, total_failed=5,
            delivery_rate=0.95, avg_delivery_time=100, queue_depth=10,
            offline_queue_size=5, retry_queue_size=5, messages_per_second=2.0,
            timestamp=datetime.now(timezone.utc)
        )
        
        connection_metrics = WebSocketConnectionMetrics(
            total_connections=10, active_connections=9, failed_connections=1,
            connection_success_rate=0.9, avg_connection_time=50, reconnection_count=2,
            namespace_distribution={'/' : 7, '/admin': 2},
            timestamp=datetime.now(timezone.utc)
        )
        
        performance_metrics = SystemPerformanceMetrics(
            cpu_usage=0.5, memory_usage=0.6, memory_available=4000000000,
            notification_latency=100, websocket_latency=50, database_response_time=25,
            error_rate=0.02, timestamp=datetime.now(timezone.utc)
        )
        
        # Test healthy status
        health = self.monitor._determine_health_status(
            delivery_metrics, connection_metrics, performance_metrics
        )
        self.assertEqual(health, NotificationSystemHealth.HEALTHY)
        
        # Test critical status (low delivery rate)
        delivery_metrics.delivery_rate = 0.4  # Below critical threshold
        health = self.monitor._determine_health_status(
            delivery_metrics, connection_metrics, performance_metrics
        )
        self.assertEqual(health, NotificationSystemHealth.CRITICAL)
    
    def test_alert_creation_and_resolution(self):
        """Test alert creation and resolution"""
        # Create an alert
        self.monitor._create_alert(
            'test_alert',
            AlertSeverity.WARNING,
            'Test Alert',
            'This is a test alert',
            'test_component',
            {'test_metric': 123}
        )
        
        # Check alert was created
        self.assertIn('test_alert', self.monitor._active_alerts)
        alert = self.monitor._active_alerts['test_alert']
        self.assertEqual(alert.severity, AlertSeverity.WARNING)
        self.assertEqual(alert.title, 'Test Alert')
        self.assertFalse(alert.resolved)
        
        # Resolve the alert
        self.monitor._resolve_alert('test_alert')
        
        # Check alert was resolved
        self.assertNotIn('test_alert', self.monitor._active_alerts)
    
    def test_recovery_action_trigger(self):
        """Test triggering recovery actions"""
        # Test valid recovery action
        result = self.monitor.trigger_recovery_action('websocket_connection_failure')
        self.assertTrue(result)
        
        # Test invalid recovery action
        result = self.monitor.trigger_recovery_action('invalid_action')
        self.assertFalse(result)
    
    def test_get_system_health(self):
        """Test getting system health status"""
        health_data = self.monitor.get_system_health()
        
        self.assertIsInstance(health_data, dict)
        self.assertIn('overall_health', health_data)
        self.assertIn('delivery_metrics', health_data)
        self.assertIn('connection_metrics', health_data)
        self.assertIn('performance_metrics', health_data)
        self.assertIn('active_alerts', health_data)
        self.assertIn('timestamp', health_data)
    
    def test_get_delivery_dashboard_data(self):
        """Test getting delivery dashboard data"""
        # Add some metrics to history
        metrics = NotificationDeliveryMetrics(
            total_sent=100, total_delivered=95, total_failed=5,
            delivery_rate=0.95, avg_delivery_time=100, queue_depth=10,
            offline_queue_size=5, retry_queue_size=5, messages_per_second=2.0,
            timestamp=datetime.now(timezone.utc)
        )
        self.monitor._delivery_metrics_history.append(metrics)
        
        dashboard_data = self.monitor.get_delivery_dashboard_data()
        
        self.assertIsInstance(dashboard_data, dict)
        self.assertIn('current_metrics', dashboard_data)
        self.assertIn('trends', dashboard_data)
        self.assertIn('time_series', dashboard_data)
        self.assertIn('notification_stats', dashboard_data)
    
    def test_get_websocket_dashboard_data(self):
        """Test getting WebSocket dashboard data"""
        # Add some metrics to history
        metrics = WebSocketConnectionMetrics(
            total_connections=10, active_connections=9, failed_connections=1,
            connection_success_rate=0.9, avg_connection_time=50, reconnection_count=2,
            namespace_distribution={'/' : 7, '/admin': 2},
            timestamp=datetime.now(timezone.utc)
        )
        self.monitor._connection_metrics_history.append(metrics)
        
        dashboard_data = self.monitor.get_websocket_dashboard_data()
        
        self.assertIsInstance(dashboard_data, dict)
        self.assertIn('current_metrics', dashboard_data)
        self.assertIn('trends', dashboard_data)
        self.assertIn('time_series', dashboard_data)
        self.assertIn('websocket_performance', dashboard_data)
    
    def test_get_performance_metrics(self):
        """Test getting performance metrics"""
        # Add some metrics to history
        metrics = SystemPerformanceMetrics(
            cpu_usage=0.5, memory_usage=0.6, memory_available=4000000000,
            notification_latency=100, websocket_latency=50, database_response_time=25,
            error_rate=0.02, timestamp=datetime.now(timezone.utc)
        )
        self.monitor._performance_metrics_history.append(metrics)
        
        performance_data = self.monitor.get_performance_metrics()
        
        self.assertIsInstance(performance_data, dict)
        self.assertIn('current_metrics', performance_data)
        self.assertIn('trends', performance_data)
        self.assertIn('time_series', performance_data)
    
    def test_alert_callback_registration(self):
        """Test alert callback registration and execution"""
        callback_called = False
        callback_alert = None
        
        def test_callback(alert):
            nonlocal callback_called, callback_alert
            callback_called = True
            callback_alert = alert
        
        # Register callback
        self.monitor.register_alert_callback(test_callback)
        
        # Create an alert
        self.monitor._create_alert(
            'callback_test',
            AlertSeverity.CRITICAL,
            'Callback Test',
            'Testing callback functionality',
            'test_component',
            {}
        )
        
        # Check callback was called
        self.assertTrue(callback_called)
        self.assertIsNotNone(callback_alert)
        self.assertEqual(callback_alert.title, 'Callback Test')
    
    def test_record_metrics(self):
        """Test recording delivery and connection times"""
        # Record some delivery times
        self.monitor.record_delivery_time(100.5)
        self.monitor.record_delivery_time(150.0)
        self.monitor.record_delivery_time(75.2)
        
        # Check delivery times were recorded
        self.assertEqual(len(self.monitor._delivery_times), 3)
        self.assertIn(100.5, self.monitor._delivery_times)
        
        # Record some connection times
        self.monitor.record_connection_time(50.0)
        self.monitor.record_connection_time(25.5)
        
        # Check connection times were recorded
        self.assertEqual(len(self.monitor._connection_times), 2)
        self.assertIn(50.0, self.monitor._connection_times)
    
    def test_record_errors(self):
        """Test error recording"""
        # Record some errors
        self.monitor.record_error('connection_error')
        self.monitor.record_error('delivery_error')
        self.monitor.record_error('connection_error')
        
        # Check errors were recorded
        self.assertEqual(self.monitor._error_counts['connection_error'], 2)
        self.assertEqual(self.monitor._error_counts['delivery_error'], 1)
        self.assertEqual(self.monitor._error_counts['total'], 3)
    
    def test_calculate_trend(self):
        """Test trend calculation"""
        # Test increasing trend
        increasing_values = [10, 15, 20, 25, 30]
        trend = self.monitor._calculate_trend(increasing_values)
        self.assertEqual(trend, 'increasing')
        
        # Test decreasing trend
        decreasing_values = [30, 25, 20, 15, 10]
        trend = self.monitor._calculate_trend(decreasing_values)
        self.assertEqual(trend, 'decreasing')
        
        # Test stable trend
        stable_values = [20, 21, 19, 20, 21]
        trend = self.monitor._calculate_trend(stable_values)
        self.assertEqual(trend, 'stable')
        
        # Test empty values
        trend = self.monitor._calculate_trend([])
        self.assertEqual(trend, 'stable')
    
    def test_recovery_mechanisms(self):
        """Test recovery mechanism execution"""
        # Test WebSocket connection recovery
        result = self.monitor._recover_websocket_connections()
        self.assertTrue(result)
        
        # Test notification delivery recovery
        result = self.monitor._recover_notification_delivery()
        self.assertTrue(result)
        
        # Test high error rate recovery
        result = self.monitor._recover_high_error_rate()
        self.assertTrue(result)
        
        # Test memory pressure recovery
        result = self.monitor._recover_memory_pressure()
        self.assertTrue(result)
    
    def test_database_response_time_measurement(self):
        """Test database response time measurement"""
        response_time = self.monitor._measure_database_response_time()
        
        # Should return a numeric value (milliseconds)
        self.assertIsInstance(response_time, (int, float))
        self.assertGreaterEqual(response_time, 0)
    
    def test_monitoring_loop_error_handling(self):
        """Test error handling in monitoring loop"""
        # Mock an exception in metrics collection
        self.mock_notification_manager.get_notification_stats.side_effect = Exception("Test error")
        
        # Start monitoring briefly
        self.monitor.start_monitoring()
        time.sleep(0.1)  # Let it run briefly
        self.monitor.stop_monitoring()
        
        # Monitor should still be functional despite errors
        self.assertFalse(self.monitor._monitoring_active)
    
    def test_alert_threshold_checking(self):
        """Test alert threshold checking logic"""
        # Create metrics that should trigger alerts
        delivery_metrics = NotificationDeliveryMetrics(
            total_sent=100, total_delivered=40, total_failed=60,
            delivery_rate=0.4, avg_delivery_time=6000, queue_depth=1200,
            offline_queue_size=600, retry_queue_size=600, messages_per_second=0.1,
            timestamp=datetime.now(timezone.utc)
        )
        
        connection_metrics = WebSocketConnectionMetrics(
            total_connections=10, active_connections=3, failed_connections=7,
            connection_success_rate=0.2, avg_connection_time=8000, reconnection_count=15,
            namespace_distribution={'/' : 2, '/admin': 1},
            timestamp=datetime.now(timezone.utc)
        )
        
        performance_metrics = SystemPerformanceMetrics(
            cpu_usage=0.95, memory_usage=0.95, memory_available=100000000,
            notification_latency=8000, websocket_latency=5000, database_response_time=10000,
            error_rate=0.15, timestamp=datetime.now(timezone.utc)
        )
        
        # Check alerts
        initial_alert_count = len(self.monitor._active_alerts)
        self.monitor._check_alerts(delivery_metrics, connection_metrics, performance_metrics)
        
        # Should have created multiple alerts
        self.assertGreater(len(self.monitor._active_alerts), initial_alert_count)
        
        # Check for specific alert types
        alert_ids = list(self.monitor._active_alerts.keys())
        self.assertTrue(any('delivery_rate' in alert_id for alert_id in alert_ids))
        self.assertTrue(any('connection_failure' in alert_id for alert_id in alert_ids))
        self.assertTrue(any('memory_usage' in alert_id for alert_id in alert_ids))


class TestNotificationSystemMonitorFactory(unittest.TestCase):
    """Test cases for monitor factory function"""
    
    def test_create_notification_system_monitor(self):
        """Test creating monitor with factory function"""
        # Create mock dependencies
        mock_notification_manager = Mock(spec=UnifiedNotificationManager)
        mock_websocket_monitor = Mock(spec=WebSocketPerformanceMonitor)
        mock_namespace_manager = Mock(spec=WebSocketNamespaceManager)
        mock_db_manager = Mock(spec=DatabaseManager)
        
        # Create monitor using factory
        monitor = create_notification_system_monitor(
            notification_manager=mock_notification_manager,
            websocket_monitor=mock_websocket_monitor,
            namespace_manager=mock_namespace_manager,
            db_manager=mock_db_manager,
            monitoring_interval=60
        )
        
        # Verify monitor was created correctly
        self.assertIsInstance(monitor, NotificationSystemMonitor)
        self.assertEqual(monitor.monitoring_interval, 60)
        self.assertEqual(monitor.notification_manager, mock_notification_manager)
        self.assertEqual(monitor.websocket_monitor, mock_websocket_monitor)


if __name__ == '__main__':
    unittest.main()
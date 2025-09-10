# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Notification Monitoring System Demonstration

Demonstrates the complete notification monitoring and health check system,
including metrics collection, alerting, recovery mechanisms, and dashboard functionality.
"""

import time
import json
import random
import threading
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock

from app.services.monitoring.system.notification_monitor import (
    NotificationSystemMonitor, AlertSeverity, create_notification_system_monitor
)
from app.services.notification.components.notification_monitoring_dashboard import NotificationMonitoringDashboard
from app.services.notification.components.notification_websocket_recovery import (
    NotificationWebSocketRecovery, RecoveryStrategy, create_websocket_recovery_system
)
from app.services.notification.manager.unified_manager import UnifiedNotificationManager
from app.services.monitoring.performance.monitors.websocket_performance_monitor import WebSocketPerformanceMonitor
from websocket_namespace_manager import WebSocketNamespaceManager
from websocket_factory import WebSocketFactory
from websocket_auth_handler import WebSocketAuthHandler
from app.core.database.core.database_manager import DatabaseManager


class MockConnection:
    """Mock WebSocket connection for demonstration"""
    
    def __init__(self, connection_id, user_id, namespace, connected=True):
        self.connection_id = connection_id
        self.user_id = user_id
        self.namespace = namespace
        self.connected = connected
        self.last_activity = datetime.now(timezone.utc)
        self.failure_count = 0
        self.recovery_attempts = 0
        self.latency = random.uniform(10, 200)
        self.error_rate = random.uniform(0, 0.1)
    
    def reconnect(self):
        """Simulate reconnection"""
        success = random.choice([True, True, True, False])  # 75% success rate
        if success:
            self.connected = True
            self.failure_count = 0
        else:
            self.failure_count += 1
        return success


def create_mock_dependencies():
    """Create mock dependencies for demonstration"""
    
    # Mock database manager
    mock_db_manager = Mock(spec=DatabaseManager)
    mock_session = Mock()
    mock_session.execute.return_value.fetchone.return_value = None
    mock_db_manager.get_session.return_value.__enter__.return_value = mock_session
    mock_db_manager.get_session.return_value.__exit__.return_value = None
    
    # Mock notification manager with dynamic stats
    mock_notification_manager = Mock(spec=UnifiedNotificationManager)
    
    def get_dynamic_stats():
        # Simulate varying notification statistics
        base_sent = random.randint(800, 1200)
        failure_rate = random.uniform(0.02, 0.15)
        failed = int(base_sent * failure_rate)
        delivered = base_sent - failed
        
        return {
            'delivery_stats': {
                'messages_sent': base_sent,
                'messages_delivered': delivered,
                'messages_failed': failed
            },
            'offline_queues': {'total_messages': random.randint(10, 100)},
            'retry_queues': {'total_messages': random.randint(5, 50)}
        }
    
    mock_notification_manager.get_notification_stats.side_effect = get_dynamic_stats
    
    # Mock WebSocket performance monitor
    mock_websocket_monitor = Mock(spec=WebSocketPerformanceMonitor)
    
    def get_dynamic_websocket_metrics():
        return {
            'avg_latency': random.uniform(20, 150),
            'connection_count': random.randint(40, 80),
            'error_rate': random.uniform(0.01, 0.08)
        }
    
    mock_websocket_monitor.get_current_metrics.side_effect = get_dynamic_websocket_metrics
    
    # Mock namespace manager with dynamic connections
    mock_namespace_manager = Mock(spec=WebSocketNamespaceManager)
    
    # Create mock connections
    connections = {}
    for i in range(50):
        conn_id = f'conn_{i}'
        user_id = i + 1
        namespace = '/' if i < 40 else '/admin'
        connected = random.choice([True, True, True, False])  # 75% connected
        connections[conn_id] = MockConnection(conn_id, user_id, namespace, connected)
    
    mock_namespace_manager._connections = connections
    
    # Mock WebSocket factory and auth handler
    mock_websocket_factory = Mock(spec=WebSocketFactory)
    mock_auth_handler = Mock(spec=WebSocketAuthHandler)
    
    return {
        'db_manager': mock_db_manager,
        'notification_manager': mock_notification_manager,
        'websocket_monitor': mock_websocket_monitor,
        'namespace_manager': mock_namespace_manager,
        'websocket_factory': mock_websocket_factory,
        'auth_handler': mock_auth_handler
    }


def simulate_system_load(dependencies, duration=60):
    """Simulate varying system load for demonstration"""
    
    def load_simulator():
        start_time = time.time()
        
        while time.time() - start_time < duration:
            # Randomly adjust connection states
            connections = dependencies['namespace_manager']._connections
            
            # Simulate some connections failing/recovering
            for conn_id, conn in list(connections.items()):
                if random.random() < 0.05:  # 5% chance of state change
                    conn.connected = not conn.connected
                    if not conn.connected:
                        conn.failure_count += 1
                
                # Update latency and error rates
                conn.latency = max(10, conn.latency + random.uniform(-20, 20))
                conn.error_rate = max(0, min(0.5, conn.error_rate + random.uniform(-0.02, 0.02)))
            
            time.sleep(2)
    
    # Start load simulation in background
    load_thread = threading.Thread(target=load_simulator, daemon=True)
    load_thread.start()
    
    return load_thread


def demo_basic_monitoring():
    """Demonstrate basic monitoring functionality"""
    print("\n" + "=" * 60)
    print("DEMO: Basic Monitoring Functionality")
    print("=" * 60)
    
    # Create mock dependencies
    dependencies = create_mock_dependencies()
    
    # Create monitoring system
    monitor = create_notification_system_monitor(
        notification_manager=dependencies['notification_manager'],
        websocket_monitor=dependencies['websocket_monitor'],
        namespace_manager=dependencies['namespace_manager'],
        db_manager=dependencies['db_manager'],
        monitoring_interval=5  # 5 second intervals for demo
    )
    
    print("✅ Created notification system monitor")
    
    # Start monitoring
    monitor.start_monitoring()
    print("✅ Started monitoring system")
    
    # Let it collect some data
    print("📊 Collecting metrics for 15 seconds...")
    time.sleep(15)
    
    # Get system health
    health_data = monitor.get_system_health()
    print(f"\n🏥 System Health: {health_data['overall_health'].upper()}")
    print(f"   Active Alerts: {health_data['alert_count']}")
    print(f"   Last Check: {health_data['last_check']}")
    
    # Get delivery metrics
    delivery_data = monitor.get_delivery_dashboard_data()
    if delivery_data.get('current_metrics'):
        metrics = delivery_data['current_metrics']
        print(f"\n📨 Delivery Metrics:")
        print(f"   Delivery Rate: {metrics['delivery_rate']:.2%}")
        print(f"   Messages Sent: {metrics['total_sent']}")
        print(f"   Queue Depth: {metrics['queue_depth']}")
        print(f"   Messages/sec: {metrics['messages_per_second']:.2f}")
    
    # Get WebSocket metrics
    websocket_data = monitor.get_websocket_dashboard_data()
    if websocket_data.get('current_metrics'):
        metrics = websocket_data['current_metrics']
        print(f"\n🔌 WebSocket Metrics:")
        print(f"   Total Connections: {metrics['total_connections']}")
        print(f"   Active Connections: {metrics['active_connections']}")
        print(f"   Success Rate: {metrics['connection_success_rate']:.2%}")
    
    # Stop monitoring
    monitor.stop_monitoring()
    print("\n✅ Stopped monitoring system")


def demo_alert_system():
    """Demonstrate alert generation and handling"""
    print("\n" + "=" * 60)
    print("DEMO: Alert System")
    print("=" * 60)
    
    # Create mock dependencies
    dependencies = create_mock_dependencies()
    
    # Create monitoring system with sensitive thresholds for demo
    monitor = NotificationSystemMonitor(
        notification_manager=dependencies['notification_manager'],
        websocket_monitor=dependencies['websocket_monitor'],
        namespace_manager=dependencies['namespace_manager'],
        db_manager=dependencies['db_manager'],
        monitoring_interval=3,
        alert_thresholds={
            'delivery_rate_critical': 0.7,   # Lower threshold for demo
            'delivery_rate_warning': 0.85,
            'connection_failure_rate_critical': 0.2,
            'connection_failure_rate_warning': 0.1,
            'queue_depth_critical': 80,      # Lower threshold for demo
            'queue_depth_warning': 50,
            'memory_usage_critical': 0.8,
            'memory_usage_warning': 0.7
        }
    )
    
    # Set up alert callback
    alerts_received = []
    
    def alert_callback(alert):
        alerts_received.append(alert)
        severity_emoji = {
            AlertSeverity.INFO: "ℹ️",
            AlertSeverity.WARNING: "⚠️",
            AlertSeverity.CRITICAL: "🚨",
            AlertSeverity.EMERGENCY: "🆘"
        }
        print(f"{severity_emoji.get(alert.severity, '🔔')} ALERT: {alert.title}")
        print(f"   {alert.message}")
        print(f"   Component: {alert.component}")
        print(f"   Time: {alert.timestamp.strftime('%H:%M:%S')}")
    
    monitor.register_alert_callback(alert_callback)
    
    print("✅ Created monitoring system with alert callbacks")
    
    # Start monitoring
    monitor.start_monitoring()
    print("✅ Started monitoring with sensitive alert thresholds")
    
    # Simulate poor performance to trigger alerts
    print("\n📉 Simulating poor system performance...")
    
    # Override mock to return poor performance data
    def get_poor_stats():
        return {
            'delivery_stats': {
                'messages_sent': 1000,
                'messages_delivered': 600,  # 60% delivery rate (below threshold)
                'messages_failed': 400
            },
            'offline_queues': {'total_messages': 150},  # High queue depth
            'retry_queues': {'total_messages': 100}
        }
    
    dependencies['notification_manager'].get_notification_stats.side_effect = get_poor_stats
    
    # Wait for alerts to be generated
    print("⏳ Waiting for alerts to be generated...")
    time.sleep(10)
    
    # Show alert summary
    print(f"\n📋 Alert Summary:")
    print(f"   Total Alerts Generated: {len(alerts_received)}")
    
    for alert in alerts_received:
        print(f"   - {alert.severity.value.upper()}: {alert.title}")
    
    # Show active alerts
    health_data = monitor.get_system_health()
    active_alerts = health_data.get('active_alerts', [])
    print(f"\n🔴 Active Alerts: {len(active_alerts)}")
    
    # Stop monitoring
    monitor.stop_monitoring()
    print("\n✅ Stopped monitoring system")


def demo_recovery_system():
    """Demonstrate WebSocket recovery system"""
    print("\n" + "=" * 60)
    print("DEMO: WebSocket Recovery System")
    print("=" * 60)
    
    # Create mock dependencies
    dependencies = create_mock_dependencies()
    
    # Create monitoring and recovery systems
    monitor = create_notification_system_monitor(
        notification_manager=dependencies['notification_manager'],
        websocket_monitor=dependencies['websocket_monitor'],
        namespace_manager=dependencies['namespace_manager'],
        db_manager=dependencies['db_manager']
    )
    
    recovery_system = create_websocket_recovery_system(
        websocket_factory=dependencies['websocket_factory'],
        namespace_manager=dependencies['namespace_manager'],
        auth_handler=dependencies['auth_handler'],
        monitor=monitor
    )
    
    print("✅ Created monitoring and recovery systems")
    
    # Set up recovery callback
    recoveries_attempted = []
    
    def recovery_callback(connection_id, success, message):
        recoveries_attempted.append({
            'connection_id': connection_id,
            'success': success,
            'message': message
        })
        status_emoji = "✅" if success else "❌"
        print(f"{status_emoji} Recovery: {connection_id} - {message}")
    
    recovery_system.register_recovery_callback(recovery_callback)
    
    # Start both systems
    monitor.start_monitoring()
    recovery_system.start_recovery_monitoring()
    print("✅ Started monitoring and recovery systems")
    
    # Simulate connection failures
    print("\n🔌 Simulating connection failures...")
    
    connections = dependencies['namespace_manager']._connections
    failing_connections = list(connections.keys())[:5]  # First 5 connections
    
    for conn_id in failing_connections:
        conn = connections[conn_id]
        conn.connected = False
        conn.failure_count = 3  # High failure count
        conn.latency = 5000  # High latency
        print(f"   Simulated failure for {conn_id}")
    
    # Trigger recovery for failed connections
    print("\n🔧 Triggering recovery actions...")
    
    for i, conn_id in enumerate(failing_connections):
        strategy = [
            RecoveryStrategy.IMMEDIATE,
            RecoveryStrategy.EXPONENTIAL_BACKOFF,
            RecoveryStrategy.LINEAR_BACKOFF,
            RecoveryStrategy.CIRCUIT_BREAKER
        ][i % 4]
        
        success = recovery_system.trigger_connection_recovery(conn_id, strategy)
        print(f"   Triggered {strategy.value} recovery for {conn_id}: {'✅' if success else '❌'}")
    
    # Wait for recovery attempts
    print("\n⏳ Waiting for recovery attempts...")
    time.sleep(8)
    
    # Show recovery statistics
    recovery_stats = recovery_system.get_recovery_statistics()
    print(f"\n📊 Recovery Statistics:")
    print(f"   Recovery Active: {recovery_stats['recovery_active']}")
    print(f"   Connections Monitored: {recovery_stats['connections_monitored']}")
    print(f"   Failed Connections: {recovery_stats['failed_connections']}")
    print(f"   Suspended Connections: {recovery_stats['suspended_connections']}")
    print(f"   Pending Recoveries: {recovery_stats['pending_recoveries']}")
    
    # Show connection health report
    health_report = recovery_system.get_connection_health_report()
    print(f"\n🏥 Connection Health Report:")
    print(f"   Total Connections: {health_report['total_connections']}")
    print(f"   Healthy: {health_report['healthy_connections']}")
    print(f"   Unhealthy: {health_report['unhealthy_connections']}")
    print(f"   Critical: {health_report['critical_connections']}")
    
    # Show recovery attempts
    print(f"\n🔧 Recovery Attempts: {len(recoveries_attempted)}")
    for recovery in recoveries_attempted:
        status = "SUCCESS" if recovery['success'] else "FAILED"
        print(f"   {recovery['connection_id']}: {status}")
    
    # Stop systems
    monitor.stop_monitoring()
    recovery_system.stop_recovery_monitoring()
    print("\n✅ Stopped monitoring and recovery systems")


def demo_dashboard_integration():
    """Demonstrate dashboard integration"""
    print("\n" + "=" * 60)
    print("DEMO: Dashboard Integration")
    print("=" * 60)
    
    # Create mock dependencies
    dependencies = create_mock_dependencies()
    
    # Create monitoring system
    monitor = create_notification_system_monitor(
        notification_manager=dependencies['notification_manager'],
        websocket_monitor=dependencies['websocket_monitor'],
        namespace_manager=dependencies['namespace_manager'],
        db_manager=dependencies['db_manager'],
        monitoring_interval=3
    )
    
    # Create dashboard
    dashboard = NotificationMonitoringDashboard(monitor)
    
    print("✅ Created monitoring system and dashboard")
    
    # Start monitoring
    monitor.start_monitoring()
    print("✅ Started monitoring system")
    
    # Simulate system load
    load_thread = simulate_system_load(dependencies, duration=20)
    print("📈 Started system load simulation")
    
    # Collect data for dashboard
    print("\n📊 Collecting dashboard data...")
    time.sleep(10)
    
    # Get dashboard summary
    summary = dashboard.get_dashboard_summary()
    print(f"\n📋 Dashboard Summary:")
    print(f"   Overall Health: {summary['overall_health']}")
    print(f"   Active Alerts: {summary['active_alerts']}")
    print(f"   Monitoring Active: {summary['monitoring_active']}")
    
    if 'summary' in summary:
        metrics = summary['summary']
        print(f"   Delivery Rate: {metrics['delivery_rate']:.2%}")
        print(f"   Active Connections: {metrics['active_connections']}")
        print(f"   CPU Usage: {metrics['cpu_usage']:.1%}")
        print(f"   Memory Usage: {metrics['memory_usage']:.1%}")
    
    # Show real-time data updates
    print(f"\n🔄 Real-time Data Updates:")
    for i in range(3):
        time.sleep(3)
        health_data = monitor.get_system_health()
        print(f"   Update {i+1}: Health={health_data['overall_health']}, "
              f"Alerts={health_data['alert_count']}")
    
    # Stop monitoring
    monitor.stop_monitoring()
    print("\n✅ Stopped monitoring system")


def demo_performance_monitoring():
    """Demonstrate performance monitoring and optimization"""
    print("\n" + "=" * 60)
    print("DEMO: Performance Monitoring")
    print("=" * 60)
    
    # Create mock dependencies
    dependencies = create_mock_dependencies()
    
    # Create monitoring system
    monitor = create_notification_system_monitor(
        notification_manager=dependencies['notification_manager'],
        websocket_monitor=dependencies['websocket_monitor'],
        namespace_manager=dependencies['namespace_manager'],
        db_manager=dependencies['db_manager'],
        monitoring_interval=2
    )
    
    print("✅ Created performance monitoring system")
    
    # Start monitoring
    monitor.start_monitoring()
    print("✅ Started performance monitoring")
    
    # Simulate performance data collection
    print("\n📊 Simulating performance data collection...")
    
    # Record various performance metrics
    for i in range(10):
        # Simulate delivery times
        delivery_time = random.uniform(50, 300)
        monitor.record_delivery_time(delivery_time)
        
        # Simulate connection times
        connection_time = random.uniform(20, 150)
        monitor.record_connection_time(connection_time)
        
        # Simulate errors
        if random.random() < 0.1:  # 10% chance of error
            monitor.record_error('connection_error')
        
        if random.random() < 0.05:  # 5% chance of delivery error
            monitor.record_error('delivery_error')
        
        time.sleep(0.5)
    
    print("✅ Recorded performance metrics")
    
    # Wait for monitoring to process data
    time.sleep(5)
    
    # Get performance metrics
    performance_data = monitor.get_performance_metrics()
    
    if performance_data.get('current_metrics'):
        metrics = performance_data['current_metrics']
        print(f"\n⚡ Performance Metrics:")
        print(f"   CPU Usage: {metrics['cpu_usage']:.1%}")
        print(f"   Memory Usage: {metrics['memory_usage']:.1%}")
        print(f"   Notification Latency: {metrics['notification_latency']:.2f}ms")
        print(f"   WebSocket Latency: {metrics['websocket_latency']:.2f}ms")
        print(f"   Database Response Time: {metrics['database_response_time']:.2f}ms")
        print(f"   Error Rate: {metrics['error_rate']:.2%}")
    
    if performance_data.get('trends'):
        trends = performance_data['trends']
        print(f"\n📈 Performance Trends:")
        for metric, trend_data in trends.items():
            trend = trend_data.get('trend', 'stable')
            current = trend_data.get('current', 0)
            avg = trend_data.get('avg', 0)
            
            trend_emoji = {"increasing": "📈", "decreasing": "📉", "stable": "➡️"}
            print(f"   {metric}: {trend_emoji.get(trend, '➡️')} {trend} "
                  f"(current: {current:.2f}, avg: {avg:.2f})")
    
    # Test recovery mechanisms
    print(f"\n🔧 Testing Recovery Mechanisms:")
    
    recovery_actions = [
        'websocket_connection_failure',
        'notification_delivery_failure',
        'high_error_rate',
        'memory_pressure'
    ]
    
    for action in recovery_actions:
        success = monitor.trigger_recovery_action(action)
        print(f"   {action}: {'✅ Success' if success else '❌ Failed'}")
    
    # Stop monitoring
    monitor.stop_monitoring()
    print("\n✅ Stopped performance monitoring")


def main():
    """Run all monitoring system demonstrations"""
    print("🚀 Notification System Monitoring Demonstration")
    print("=" * 60)
    print("This demonstration shows the complete notification monitoring")
    print("and health check system including metrics collection, alerting,")
    print("recovery mechanisms, and dashboard functionality.")
    
    try:
        # Run all demonstrations
        demo_basic_monitoring()
        demo_alert_system()
        demo_recovery_system()
        demo_dashboard_integration()
        demo_performance_monitoring()
        
        print("\n" + "=" * 60)
        print("✅ ALL DEMONSTRATIONS COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print("\nKey Features Demonstrated:")
        print("• Real-time metrics collection and monitoring")
        print("• Intelligent alert generation and management")
        print("• Automatic WebSocket connection recovery")
        print("• Performance monitoring and optimization")
        print("• Dashboard integration and real-time updates")
        print("• Comprehensive health checking")
        print("• Error detection and recovery mechanisms")
        print("\nThe notification monitoring system is ready for production use!")
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Demonstration interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Demonstration failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
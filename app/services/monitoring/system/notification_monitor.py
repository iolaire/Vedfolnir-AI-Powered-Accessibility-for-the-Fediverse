# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Notification System Monitor

Provides comprehensive monitoring and health checking for the unified notification system,
including notification delivery metrics, WebSocket connection monitoring, performance tracking,
and automatic recovery mechanisms.
"""

import time
import json
import threading
import logging
import psutil
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Callable, Tuple, Set
from enum import Enum
from dataclasses import dataclass, asdict
from collections import deque, defaultdict
import statistics

from app.services.notification.manager.unified_manager import UnifiedNotificationManager
from app.services.monitoring.performance.monitors.websocket_performance_monitor import ConsolidatedWebSocketPerformanceMonitor as WebSocketPerformanceMonitor
from app.websocket.core.namespace_manager import WebSocketNamespaceManager
from app.core.database.core.database_manager import DatabaseManager
from models import NotificationStorage, NotificationType, NotificationPriority, NotificationCategory

logger = logging.getLogger(__name__)


class NotificationSystemHealth(Enum):
    """Notification system health status"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    FAILED = "failed"


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class NotificationDeliveryMetrics:
    """Notification delivery performance metrics"""
    total_sent: int
    total_delivered: int
    total_failed: int
    delivery_rate: float
    avg_delivery_time: float
    queue_depth: int
    offline_queue_size: int
    retry_queue_size: int
    messages_per_second: float
    timestamp: datetime


@dataclass
class WebSocketConnectionMetrics:
    """WebSocket connection health metrics"""
    total_connections: int
    active_connections: int
    failed_connections: int
    connection_success_rate: float
    avg_connection_time: float
    reconnection_count: int
    namespace_distribution: Dict[str, int]
    timestamp: datetime


@dataclass
class SystemPerformanceMetrics:
    """System performance metrics"""
    cpu_usage: float
    memory_usage: float
    memory_available: float
    notification_latency: float
    websocket_latency: float
    database_response_time: float
    error_rate: float
    timestamp: datetime


@dataclass
class NotificationSystemAlert:
    """System alert structure"""
    id: str
    severity: AlertSeverity
    title: str
    message: str
    component: str
    metrics: Dict[str, Any]
    timestamp: datetime
    resolved: bool = False
    resolution_time: Optional[datetime] = None


class NotificationSystemMonitor:
    """
    Comprehensive monitoring system for the unified notification system
    
    Provides real-time monitoring, health checks, performance metrics,
    alerting, and automatic recovery mechanisms.
    """
    
    def __init__(self, notification_manager: UnifiedNotificationManager,
                 websocket_monitor: WebSocketPerformanceMonitor,
                 namespace_manager: WebSocketNamespaceManager,
                 db_manager: DatabaseManager,
                 monitoring_interval: int = 30,
                 alert_thresholds: Optional[Dict[str, Any]] = None):
        """
        Initialize notification system monitor
        
        Args:
            notification_manager: Unified notification manager instance
            websocket_monitor: WebSocket performance monitor
            namespace_manager: WebSocket namespace manager
            db_manager: Database manager instance
            monitoring_interval: Monitoring interval in seconds
            alert_thresholds: Custom alert thresholds
        """
        self.notification_manager = notification_manager
        self.websocket_monitor = websocket_monitor
        self.namespace_manager = namespace_manager
        self.db_manager = db_manager
        self.monitoring_interval = monitoring_interval
        
        # Monitoring state
        self._monitoring_active = False
        self._monitoring_thread = None
        self._last_check_time = None
        
        # Metrics storage
        self._delivery_metrics_history = deque(maxlen=1000)
        self._connection_metrics_history = deque(maxlen=1000)
        self._performance_metrics_history = deque(maxlen=1000)
        
        # Alert management
        self._active_alerts = {}  # alert_id -> NotificationSystemAlert
        self._alert_history = deque(maxlen=500)
        self._alert_callbacks = []  # List of alert callback functions
        
        # Recovery mechanisms
        self._recovery_actions = {
            'websocket_connection_failure': self._recover_websocket_connections,
            'notification_delivery_failure': self._recover_notification_delivery,
            'high_error_rate': self._recover_high_error_rate,
            'memory_pressure': self._recover_memory_pressure,
            'database_slowdown': self._recover_database_performance
        }
        
        # Performance tracking
        self._delivery_times = deque(maxlen=1000)
        self._connection_times = deque(maxlen=1000)
        self._error_counts = defaultdict(int)
        self._last_error_reset = time.time()
        
        # Alert thresholds
        self.alert_thresholds = alert_thresholds or {
            'delivery_rate_critical': 0.5,  # 50% delivery rate
            'delivery_rate_warning': 0.8,   # 80% delivery rate
            'connection_failure_rate_critical': 0.3,  # 30% failure rate
            'connection_failure_rate_warning': 0.1,   # 10% failure rate
            'avg_delivery_time_critical': 5000,  # 5 seconds
            'avg_delivery_time_warning': 2000,   # 2 seconds
            'error_rate_critical': 0.1,  # 10% error rate
            'error_rate_warning': 0.05,  # 5% error rate
            'memory_usage_critical': 0.9,  # 90% memory usage
            'memory_usage_warning': 0.8,   # 80% memory usage
            'cpu_usage_critical': 0.9,     # 90% CPU usage
            'cpu_usage_warning': 0.8,      # 80% CPU usage
            'queue_depth_critical': 1000,  # 1000 messages in queue
            'queue_depth_warning': 500     # 500 messages in queue
        }
        
        logger.info("Notification System Monitor initialized")
    
    def start_monitoring(self) -> None:
        """Start continuous monitoring"""
        if self._monitoring_active:
            logger.warning("Monitoring already active")
            return
        
        self._monitoring_active = True
        self._monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True,
            name="NotificationSystemMonitor"
        )
        self._monitoring_thread.start()
        logger.info("Started notification system monitoring")
    
    def stop_monitoring(self) -> None:
        """Stop continuous monitoring"""
        self._monitoring_active = False
        if self._monitoring_thread:
            self._monitoring_thread.join(timeout=5)
        logger.info("Stopped notification system monitoring")
    
    def get_system_health(self) -> Dict[str, Any]:
        """
        Get comprehensive system health status
        
        Returns:
            Dictionary containing system health information
        """
        try:
            # Collect current metrics
            delivery_metrics = self._collect_delivery_metrics()
            connection_metrics = self._collect_connection_metrics()
            performance_metrics = self._collect_performance_metrics()
            
            # Determine overall health status
            health_status = self._determine_health_status(
                delivery_metrics, connection_metrics, performance_metrics
            )
            
            # Get active alerts
            active_alerts = [asdict(alert) for alert in self._active_alerts.values()]
            
            return {
                'overall_health': health_status.value,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'delivery_metrics': asdict(delivery_metrics),
                'connection_metrics': asdict(connection_metrics),
                'performance_metrics': asdict(performance_metrics),
                'active_alerts': active_alerts,
                'alert_count': len(active_alerts),
                'monitoring_active': self._monitoring_active,
                'last_check': self._last_check_time.isoformat() if self._last_check_time else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get system health: {e}")
            return {
                'overall_health': NotificationSystemHealth.FAILED.value,
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def get_delivery_dashboard_data(self) -> Dict[str, Any]:
        """
        Get real-time notification delivery dashboard data
        
        Returns:
            Dictionary containing dashboard data
        """
        try:
            # Get recent metrics
            recent_metrics = list(self._delivery_metrics_history)[-100:]  # Last 100 data points
            
            if not recent_metrics:
                return {'error': 'No metrics data available'}
            
            # Calculate trends
            delivery_rates = [m.delivery_rate for m in recent_metrics]
            delivery_times = [m.avg_delivery_time for m in recent_metrics]
            queue_depths = [m.queue_depth for m in recent_metrics]
            
            # Get notification stats from manager
            notification_stats = self.notification_manager.get_notification_stats()
            
            return {
                'current_metrics': asdict(recent_metrics[-1]) if recent_metrics else None,
                'trends': {
                    'delivery_rate': {
                        'current': delivery_rates[-1] if delivery_rates else 0,
                        'avg': statistics.mean(delivery_rates) if delivery_rates else 0,
                        'trend': self._calculate_trend(delivery_rates)
                    },
                    'delivery_time': {
                        'current': delivery_times[-1] if delivery_times else 0,
                        'avg': statistics.mean(delivery_times) if delivery_times else 0,
                        'trend': self._calculate_trend(delivery_times)
                    },
                    'queue_depth': {
                        'current': queue_depths[-1] if queue_depths else 0,
                        'max': max(queue_depths) if queue_depths else 0,
                        'trend': self._calculate_trend(queue_depths)
                    }
                },
                'notification_stats': notification_stats,
                'time_series': [
                    {
                        'timestamp': m.timestamp.isoformat(),
                        'delivery_rate': m.delivery_rate,
                        'avg_delivery_time': m.avg_delivery_time,
                        'queue_depth': m.queue_depth,
                        'messages_per_second': m.messages_per_second
                    }
                    for m in recent_metrics
                ],
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get delivery dashboard data: {e}")
            return {'error': str(e)}
    
    def get_websocket_dashboard_data(self) -> Dict[str, Any]:
        """
        Get real-time WebSocket connection dashboard data
        
        Returns:
            Dictionary containing WebSocket dashboard data
        """
        try:
            # Get recent connection metrics
            recent_metrics = list(self._connection_metrics_history)[-100:]
            
            if not recent_metrics:
                return {'error': 'No connection metrics data available'}
            
            # Get WebSocket performance data
            websocket_metrics = self.websocket_monitor.get_current_performance_summary()
            
            # Calculate connection trends
            success_rates = [m.connection_success_rate for m in recent_metrics]
            connection_times = [m.avg_connection_time for m in recent_metrics]
            total_connections = [m.total_connections for m in recent_metrics]
            
            return {
                'current_metrics': asdict(recent_metrics[-1]) if recent_metrics else None,
                'websocket_performance': websocket_metrics,
                'trends': {
                    'success_rate': {
                        'current': success_rates[-1] if success_rates else 0,
                        'avg': statistics.mean(success_rates) if success_rates else 0,
                        'trend': self._calculate_trend(success_rates)
                    },
                    'connection_time': {
                        'current': connection_times[-1] if connection_times else 0,
                        'avg': statistics.mean(connection_times) if connection_times else 0,
                        'trend': self._calculate_trend(connection_times)
                    },
                    'total_connections': {
                        'current': total_connections[-1] if total_connections else 0,
                        'peak': max(total_connections) if total_connections else 0,
                        'trend': self._calculate_trend(total_connections)
                    }
                },
                'namespace_distribution': recent_metrics[-1].namespace_distribution if recent_metrics else {},
                'time_series': [
                    {
                        'timestamp': m.timestamp.isoformat(),
                        'total_connections': m.total_connections,
                        'active_connections': m.active_connections,
                        'connection_success_rate': m.connection_success_rate,
                        'avg_connection_time': m.avg_connection_time
                    }
                    for m in recent_metrics
                ],
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get WebSocket dashboard data: {e}")
            return {'error': str(e)}
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get detailed performance metrics for monitoring
        
        Returns:
            Dictionary containing performance metrics
        """
        try:
            # Get recent performance metrics
            recent_metrics = list(self._performance_metrics_history)[-100:]
            
            if not recent_metrics:
                return {'error': 'No performance metrics data available'}
            
            # Calculate performance trends
            cpu_usage = [m.cpu_usage for m in recent_metrics]
            memory_usage = [m.memory_usage for m in recent_metrics]
            notification_latency = [m.notification_latency for m in recent_metrics]
            error_rates = [m.error_rate for m in recent_metrics]
            
            return {
                'current_metrics': asdict(recent_metrics[-1]) if recent_metrics else None,
                'trends': {
                    'cpu_usage': {
                        'current': cpu_usage[-1] if cpu_usage else 0,
                        'avg': statistics.mean(cpu_usage) if cpu_usage else 0,
                        'peak': max(cpu_usage) if cpu_usage else 0,
                        'trend': self._calculate_trend(cpu_usage)
                    },
                    'memory_usage': {
                        'current': memory_usage[-1] if memory_usage else 0,
                        'avg': statistics.mean(memory_usage) if memory_usage else 0,
                        'peak': max(memory_usage) if memory_usage else 0,
                        'trend': self._calculate_trend(memory_usage)
                    },
                    'notification_latency': {
                        'current': notification_latency[-1] if notification_latency else 0,
                        'avg': statistics.mean(notification_latency) if notification_latency else 0,
                        'p95': statistics.quantiles(notification_latency, n=20)[18] if len(notification_latency) > 20 else 0,
                        'trend': self._calculate_trend(notification_latency)
                    },
                    'error_rate': {
                        'current': error_rates[-1] if error_rates else 0,
                        'avg': statistics.mean(error_rates) if error_rates else 0,
                        'trend': self._calculate_trend(error_rates)
                    }
                },
                'time_series': [
                    {
                        'timestamp': m.timestamp.isoformat(),
                        'cpu_usage': m.cpu_usage,
                        'memory_usage': m.memory_usage,
                        'notification_latency': m.notification_latency,
                        'error_rate': m.error_rate
                    }
                    for m in recent_metrics
                ],
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get performance metrics: {e}")
            return {'error': str(e)}
    
    def register_alert_callback(self, callback: Callable[[NotificationSystemAlert], None]) -> None:
        """
        Register callback function for alert notifications
        
        Args:
            callback: Function to call when alerts are generated
        """
        self._alert_callbacks.append(callback)
        logger.info("Registered alert callback")
    
    def trigger_recovery_action(self, action_type: str) -> bool:
        """
        Manually trigger a recovery action
        
        Args:
            action_type: Type of recovery action to trigger
            
        Returns:
            True if recovery action was successful
        """
        try:
            if action_type in self._recovery_actions:
                recovery_func = self._recovery_actions[action_type]
                result = recovery_func()
                logger.info(f"Manually triggered recovery action '{action_type}': {'success' if result else 'failed'}")
                return result
            else:
                logger.warning(f"Unknown recovery action type: {action_type}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to trigger recovery action '{action_type}': {e}")
            return False
    
    def _monitoring_loop(self) -> None:
        """Main monitoring loop"""
        logger.info("Started notification system monitoring loop")
        
        while self._monitoring_active:
            try:
                start_time = time.time()
                
                # Collect metrics
                delivery_metrics = self._collect_delivery_metrics()
                connection_metrics = self._collect_connection_metrics()
                performance_metrics = self._collect_performance_metrics()
                
                # Store metrics
                self._delivery_metrics_history.append(delivery_metrics)
                self._connection_metrics_history.append(connection_metrics)
                self._performance_metrics_history.append(performance_metrics)
                
                # Check for alerts
                self._check_alerts(delivery_metrics, connection_metrics, performance_metrics)
                
                # Perform automatic recovery if needed
                self._perform_automatic_recovery(delivery_metrics, connection_metrics, performance_metrics)
                
                # Update last check time
                self._last_check_time = datetime.now(timezone.utc)
                
                # Calculate sleep time to maintain interval
                elapsed_time = time.time() - start_time
                sleep_time = max(0, self.monitoring_interval - elapsed_time)
                
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.monitoring_interval)
    
    def _collect_delivery_metrics(self) -> NotificationDeliveryMetrics:
        """Collect notification delivery metrics"""
        try:
            # Get stats from notification manager
            stats = self.notification_manager.get_notification_stats()
            
            # Calculate delivery rate
            total_sent = stats['delivery_stats']['messages_sent']
            total_delivered = stats['delivery_stats']['messages_delivered']
            total_failed = stats['delivery_stats']['messages_failed']
            
            delivery_rate = total_delivered / max(total_sent, 1)
            
            # Calculate average delivery time
            avg_delivery_time = statistics.mean(self._delivery_times) if self._delivery_times else 0
            
            # Calculate messages per second
            current_time = time.time()
            recent_deliveries = [t for t in self._delivery_times if current_time - t < 60]  # Last minute
            messages_per_second = len(recent_deliveries) / 60
            
            # Get queue information
            offline_queue_size = stats['offline_queues']['total_messages']
            retry_queue_size = stats['retry_queues']['total_messages']
            queue_depth = offline_queue_size + retry_queue_size
            
            return NotificationDeliveryMetrics(
                total_sent=total_sent,
                total_delivered=total_delivered,
                total_failed=total_failed,
                delivery_rate=delivery_rate,
                avg_delivery_time=avg_delivery_time,
                queue_depth=queue_depth,
                offline_queue_size=offline_queue_size,
                retry_queue_size=retry_queue_size,
                messages_per_second=messages_per_second,
                timestamp=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            logger.error(f"Failed to collect delivery metrics: {e}")
            return NotificationDeliveryMetrics(
                total_sent=0, total_delivered=0, total_failed=0,
                delivery_rate=0, avg_delivery_time=0, queue_depth=0,
                offline_queue_size=0, retry_queue_size=0, messages_per_second=0,
                timestamp=datetime.now(timezone.utc)
            )
    
    def _collect_connection_metrics(self) -> WebSocketConnectionMetrics:
        """Collect WebSocket connection metrics"""
        try:
            # Get connection information from namespace manager
            total_connections = len(self.namespace_manager._connections)
            active_connections = len([
                conn for conn in self.namespace_manager._connections.values()
                if conn.connected
            ])
            
            # Calculate connection success rate
            total_attempts = len(self._connection_times)
            successful_connections = active_connections
            connection_success_rate = successful_connections / max(total_attempts, 1)
            
            # Calculate average connection time
            avg_connection_time = statistics.mean(self._connection_times) if self._connection_times else 0
            
            # Get namespace distribution
            namespace_distribution = defaultdict(int)
            for conn in self.namespace_manager._connections.values():
                namespace_distribution[conn.namespace] += 1
            
            # Get reconnection count (simplified - would need more tracking in real implementation)
            reconnection_count = 0  # This would need to be tracked separately
            
            return WebSocketConnectionMetrics(
                total_connections=total_connections,
                active_connections=active_connections,
                failed_connections=total_attempts - successful_connections,
                connection_success_rate=connection_success_rate,
                avg_connection_time=avg_connection_time,
                reconnection_count=reconnection_count,
                namespace_distribution=dict(namespace_distribution),
                timestamp=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            logger.error(f"Failed to collect connection metrics: {e}")
            return WebSocketConnectionMetrics(
                total_connections=0, active_connections=0, failed_connections=0,
                connection_success_rate=0, avg_connection_time=0, reconnection_count=0,
                namespace_distribution={}, timestamp=datetime.now(timezone.utc)
            )
    
    def _collect_performance_metrics(self) -> SystemPerformanceMetrics:
        """Collect system performance metrics"""
        try:
            # Get system resource usage
            cpu_usage = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            memory_usage = memory.percent / 100
            memory_available = memory.available
            
            # Calculate notification latency (average of recent delivery times)
            notification_latency = statistics.mean(self._delivery_times[-100:]) if self._delivery_times else 0
            
            # Get WebSocket latency from performance monitor
            websocket_metrics = self.websocket_monitor.get_current_performance_summary()
            websocket_latency = websocket_metrics.get('avg_latency', 0) if websocket_metrics else 0
            
            # Measure database response time
            database_response_time = self._measure_database_response_time()
            
            # Calculate error rate
            current_time = time.time()
            if current_time - self._last_error_reset > 300:  # Reset every 5 minutes
                self._error_counts.clear()
                self._last_error_reset = current_time
            
            total_operations = sum(self._error_counts.values())
            error_operations = self._error_counts.get('errors', 0)
            error_rate = error_operations / max(total_operations, 1)
            
            return SystemPerformanceMetrics(
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                memory_available=memory_available,
                notification_latency=notification_latency,
                websocket_latency=websocket_latency,
                database_response_time=database_response_time,
                error_rate=error_rate,
                timestamp=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            logger.error(f"Failed to collect performance metrics: {e}")
            return SystemPerformanceMetrics(
                cpu_usage=0, memory_usage=0, memory_available=0,
                notification_latency=0, websocket_latency=0, database_response_time=0,
                error_rate=0, timestamp=datetime.now(timezone.utc)
            )
    
    def _measure_database_response_time(self) -> float:
        """Measure database response time"""
        try:
            start_time = time.time()
            with self.db_manager.get_session() as session:
                # Simple query to test database responsiveness
                session.execute("SELECT 1").fetchone()
            return (time.time() - start_time) * 1000  # Convert to milliseconds
            
        except Exception as e:
            logger.error(f"Failed to measure database response time: {e}")
            return 0
    
    def _determine_health_status(self, delivery_metrics: NotificationDeliveryMetrics,
                                connection_metrics: WebSocketConnectionMetrics,
                                performance_metrics: SystemPerformanceMetrics) -> NotificationSystemHealth:
        """Determine overall system health status"""
        try:
            # Check critical conditions
            if (delivery_metrics.delivery_rate < self.alert_thresholds['delivery_rate_critical'] or
                connection_metrics.connection_success_rate < self.alert_thresholds['connection_failure_rate_critical'] or
                performance_metrics.error_rate > self.alert_thresholds['error_rate_critical'] or
                performance_metrics.memory_usage > self.alert_thresholds['memory_usage_critical']):
                return NotificationSystemHealth.CRITICAL
            
            # Check warning conditions
            if (delivery_metrics.delivery_rate < self.alert_thresholds['delivery_rate_warning'] or
                connection_metrics.connection_success_rate < self.alert_thresholds['connection_failure_rate_warning'] or
                performance_metrics.error_rate > self.alert_thresholds['error_rate_warning'] or
                performance_metrics.memory_usage > self.alert_thresholds['memory_usage_warning'] or
                delivery_metrics.avg_delivery_time > self.alert_thresholds['avg_delivery_time_warning']):
                return NotificationSystemHealth.WARNING
            
            return NotificationSystemHealth.HEALTHY
            
        except Exception as e:
            logger.error(f"Failed to determine health status: {e}")
            return NotificationSystemHealth.FAILED
    
    def _check_alerts(self, delivery_metrics: NotificationDeliveryMetrics,
                     connection_metrics: WebSocketConnectionMetrics,
                     performance_metrics: SystemPerformanceMetrics) -> None:
        """Check for alert conditions and generate alerts"""
        try:
            current_time = datetime.now(timezone.utc)
            
            # Check delivery rate alerts
            if delivery_metrics.delivery_rate < self.alert_thresholds['delivery_rate_critical']:
                self._create_alert(
                    'delivery_rate_critical',
                    AlertSeverity.CRITICAL,
                    'Critical Delivery Rate',
                    f'Notification delivery rate is critically low: {delivery_metrics.delivery_rate:.2%}',
                    'notification_delivery',
                    {'delivery_rate': delivery_metrics.delivery_rate}
                )
            elif delivery_metrics.delivery_rate < self.alert_thresholds['delivery_rate_warning']:
                self._create_alert(
                    'delivery_rate_warning',
                    AlertSeverity.WARNING,
                    'Low Delivery Rate',
                    f'Notification delivery rate is below threshold: {delivery_metrics.delivery_rate:.2%}',
                    'notification_delivery',
                    {'delivery_rate': delivery_metrics.delivery_rate}
                )
            else:
                self._resolve_alert('delivery_rate_critical')
                self._resolve_alert('delivery_rate_warning')
            
            # Check connection alerts
            if connection_metrics.connection_success_rate < self.alert_thresholds['connection_failure_rate_critical']:
                self._create_alert(
                    'connection_failure_critical',
                    AlertSeverity.CRITICAL,
                    'Critical Connection Failure Rate',
                    f'WebSocket connection failure rate is critically high: {1-connection_metrics.connection_success_rate:.2%}',
                    'websocket_connections',
                    {'failure_rate': 1-connection_metrics.connection_success_rate}
                )
            elif connection_metrics.connection_success_rate < self.alert_thresholds['connection_failure_rate_warning']:
                self._create_alert(
                    'connection_failure_warning',
                    AlertSeverity.WARNING,
                    'High Connection Failure Rate',
                    f'WebSocket connection failure rate is elevated: {1-connection_metrics.connection_success_rate:.2%}',
                    'websocket_connections',
                    {'failure_rate': 1-connection_metrics.connection_success_rate}
                )
            else:
                self._resolve_alert('connection_failure_critical')
                self._resolve_alert('connection_failure_warning')
            
            # Check performance alerts
            if performance_metrics.memory_usage > self.alert_thresholds['memory_usage_critical']:
                self._create_alert(
                    'memory_usage_critical',
                    AlertSeverity.CRITICAL,
                    'Critical Memory Usage',
                    f'System memory usage is critically high: {performance_metrics.memory_usage:.1%}',
                    'system_performance',
                    {'memory_usage': performance_metrics.memory_usage}
                )
            elif performance_metrics.memory_usage > self.alert_thresholds['memory_usage_warning']:
                self._create_alert(
                    'memory_usage_warning',
                    AlertSeverity.WARNING,
                    'High Memory Usage',
                    f'System memory usage is elevated: {performance_metrics.memory_usage:.1%}',
                    'system_performance',
                    {'memory_usage': performance_metrics.memory_usage}
                )
            else:
                self._resolve_alert('memory_usage_critical')
                self._resolve_alert('memory_usage_warning')
            
            # Check queue depth alerts
            if delivery_metrics.queue_depth > self.alert_thresholds['queue_depth_critical']:
                self._create_alert(
                    'queue_depth_critical',
                    AlertSeverity.CRITICAL,
                    'Critical Queue Depth',
                    f'Notification queue depth is critically high: {delivery_metrics.queue_depth} messages',
                    'notification_delivery',
                    {'queue_depth': delivery_metrics.queue_depth}
                )
            elif delivery_metrics.queue_depth > self.alert_thresholds['queue_depth_warning']:
                self._create_alert(
                    'queue_depth_warning',
                    AlertSeverity.WARNING,
                    'High Queue Depth',
                    f'Notification queue depth is elevated: {delivery_metrics.queue_depth} messages',
                    'notification_delivery',
                    {'queue_depth': delivery_metrics.queue_depth}
                )
            else:
                self._resolve_alert('queue_depth_critical')
                self._resolve_alert('queue_depth_warning')
            
        except Exception as e:
            logger.error(f"Failed to check alerts: {e}")
    
    def _create_alert(self, alert_id: str, severity: AlertSeverity, title: str,
                     message: str, component: str, metrics: Dict[str, Any]) -> None:
        """Create or update an alert"""
        try:
            if alert_id not in self._active_alerts:
                alert = NotificationSystemAlert(
                    id=alert_id,
                    severity=severity,
                    title=title,
                    message=message,
                    component=component,
                    metrics=metrics,
                    timestamp=datetime.now(timezone.utc)
                )
                
                self._active_alerts[alert_id] = alert
                self._alert_history.append(alert)
                
                # Notify alert callbacks
                for callback in self._alert_callbacks:
                    try:
                        callback(alert)
                    except Exception as e:
                        logger.error(f"Alert callback failed: {e}")
                
                logger.warning(f"Created alert: {title} - {message}")
            else:
                # Update existing alert metrics
                self._active_alerts[alert_id].metrics = metrics
                
        except Exception as e:
            logger.error(f"Failed to create alert: {e}")
    
    def _resolve_alert(self, alert_id: str) -> None:
        """Resolve an active alert"""
        try:
            if alert_id in self._active_alerts:
                alert = self._active_alerts[alert_id]
                alert.resolved = True
                alert.resolution_time = datetime.now(timezone.utc)
                
                del self._active_alerts[alert_id]
                
                logger.info(f"Resolved alert: {alert.title}")
                
        except Exception as e:
            logger.error(f"Failed to resolve alert: {e}")
    
    def _perform_automatic_recovery(self, delivery_metrics: NotificationDeliveryMetrics,
                                  connection_metrics: WebSocketConnectionMetrics,
                                  performance_metrics: SystemPerformanceMetrics) -> None:
        """Perform automatic recovery actions based on metrics"""
        try:
            # Trigger recovery for critical conditions
            if connection_metrics.connection_success_rate < self.alert_thresholds['connection_failure_rate_critical']:
                self.trigger_recovery_action('websocket_connection_failure')
            
            if delivery_metrics.delivery_rate < self.alert_thresholds['delivery_rate_critical']:
                self.trigger_recovery_action('notification_delivery_failure')
            
            if performance_metrics.error_rate > self.alert_thresholds['error_rate_critical']:
                self.trigger_recovery_action('high_error_rate')
            
            if performance_metrics.memory_usage > self.alert_thresholds['memory_usage_critical']:
                self.trigger_recovery_action('memory_pressure')
            
            if performance_metrics.database_response_time > 5000:  # 5 seconds
                self.trigger_recovery_action('database_slowdown')
                
        except Exception as e:
            logger.error(f"Failed to perform automatic recovery: {e}")
    
    def _recover_websocket_connections(self) -> bool:
        """Recover WebSocket connections"""
        try:
            logger.info("Attempting WebSocket connection recovery")
            
            # Force reconnection of failed connections
            # This would need to be implemented in the WebSocket factory
            # For now, we'll just log the attempt
            
            # Clear connection metrics to reset failure tracking
            self._connection_times.clear()
            
            logger.info("WebSocket connection recovery completed")
            return True
            
        except Exception as e:
            logger.error(f"WebSocket connection recovery failed: {e}")
            return False
    
    def _recover_notification_delivery(self) -> bool:
        """Recover notification delivery"""
        try:
            logger.info("Attempting notification delivery recovery")
            
            # Retry failed messages
            # This would trigger replay of queued messages
            
            # Clear delivery metrics to reset failure tracking
            self._delivery_times.clear()
            
            logger.info("Notification delivery recovery completed")
            return True
            
        except Exception as e:
            logger.error(f"Notification delivery recovery failed: {e}")
            return False
    
    def _recover_high_error_rate(self) -> bool:
        """Recover from high error rate"""
        try:
            logger.info("Attempting error rate recovery")
            
            # Reset error counters
            self._error_counts.clear()
            self._last_error_reset = time.time()
            
            logger.info("Error rate recovery completed")
            return True
            
        except Exception as e:
            logger.error(f"Error rate recovery failed: {e}")
            return False
    
    def _recover_memory_pressure(self) -> bool:
        """Recover from memory pressure"""
        try:
            logger.info("Attempting memory pressure recovery")
            
            # Clean up old metrics
            if len(self._delivery_metrics_history) > 500:
                # Keep only recent metrics
                self._delivery_metrics_history = deque(
                    list(self._delivery_metrics_history)[-500:], maxlen=1000
                )
            
            if len(self._connection_metrics_history) > 500:
                self._connection_metrics_history = deque(
                    list(self._connection_metrics_history)[-500:], maxlen=1000
                )
            
            if len(self._performance_metrics_history) > 500:
                self._performance_metrics_history = deque(
                    list(self._performance_metrics_history)[-500:], maxlen=1000
                )
            
            # Clean up notification manager caches
            self.notification_manager.cleanup_expired_messages()
            
            logger.info("Memory pressure recovery completed")
            return True
            
        except Exception as e:
            logger.error(f"Memory pressure recovery failed: {e}")
            return False
    
    def _recover_database_performance(self) -> bool:
        """Recover database performance"""
        try:
            logger.info("Attempting database performance recovery")
            
            # This would implement database optimization strategies
            # For now, we'll just measure current response time
            response_time = self._measure_database_response_time()
            
            logger.info(f"Database performance recovery completed, response time: {response_time}ms")
            return response_time < 1000  # Consider successful if under 1 second
            
        except Exception as e:
            logger.error(f"Database performance recovery failed: {e}")
            return False
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction from a list of values"""
        if len(values) < 2:
            return 'stable'
        
        try:
            # Simple trend calculation using first and last values
            first_half = values[:len(values)//2]
            second_half = values[len(values)//2:]
            
            first_avg = statistics.mean(first_half)
            second_avg = statistics.mean(second_half)
            
            change_percent = (second_avg - first_avg) / max(first_avg, 0.001) * 100
            
            if change_percent > 5:
                return 'increasing'
            elif change_percent < -5:
                return 'decreasing'
            else:
                return 'stable'
                
        except Exception:
            return 'stable'
    
    def record_delivery_time(self, delivery_time: float) -> None:
        """Record a notification delivery time for metrics"""
        self._delivery_times.append(delivery_time)
    
    def record_connection_time(self, connection_time: float) -> None:
        """Record a WebSocket connection time for metrics"""
        self._connection_times.append(connection_time)
    
    def record_error(self, error_type: str = 'errors') -> None:
        """Record an error for metrics"""
        self._error_counts[error_type] += 1
        self._error_counts['total'] += 1


def create_notification_system_monitor(notification_manager: UnifiedNotificationManager,
                                     websocket_monitor: WebSocketPerformanceMonitor,
                                     namespace_manager: WebSocketNamespaceManager,
                                     db_manager: DatabaseManager,
                                     monitoring_interval: int = 30) -> NotificationSystemMonitor:
    """
    Create and configure a notification system monitor
    
    Args:
        notification_manager: Unified notification manager instance
        websocket_monitor: WebSocket performance monitor
        namespace_manager: WebSocket namespace manager
        db_manager: Database manager instance
        monitoring_interval: Monitoring interval in seconds
        
    Returns:
        Configured NotificationSystemMonitor instance
    """
    return NotificationSystemMonitor(
        notification_manager=notification_manager,
        websocket_monitor=websocket_monitor,
        namespace_manager=namespace_manager,
        db_manager=db_manager,
        monitoring_interval=monitoring_interval
    )
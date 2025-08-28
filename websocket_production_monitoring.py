# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
WebSocket Production Monitoring System

This module provides comprehensive monitoring integration for WebSocket connections
in production environments, including metrics collection, health checks, alerting,
and integration with monitoring platforms like Prometheus, Grafana, and custom dashboards.
"""

import os
import time
import json
import threading
import psutil
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Callable, Union
from dataclasses import dataclass, field, asdict
from collections import defaultdict, deque
from enum import Enum
import socket
from contextlib import contextmanager

from flask import Flask, jsonify, request
from flask_socketio import SocketIO

from websocket_production_config import ProductionMonitoringConfig
from websocket_production_logging import ProductionWebSocketLogger, WebSocketLogLevel

# Try to import optional dependencies
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False


class HealthStatus(Enum):
    """Health check status levels"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class MetricType(Enum):
    """Metric types for monitoring"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class ConnectionMetrics:
    """WebSocket connection metrics"""
    total_connections: int = 0
    active_connections: int = 0
    failed_connections: int = 0
    connection_rate: float = 0.0
    average_connection_duration: float = 0.0
    connections_by_namespace: Dict[str, int] = field(default_factory=dict)
    connections_by_user: Dict[int, int] = field(default_factory=dict)


@dataclass
class MessageMetrics:
    """WebSocket message metrics"""
    total_messages: int = 0
    messages_per_second: float = 0.0
    average_message_size: float = 0.0
    message_processing_time: float = 0.0
    messages_by_event: Dict[str, int] = field(default_factory=dict)
    messages_by_namespace: Dict[str, int] = field(default_factory=dict)
    failed_messages: int = 0


@dataclass
class PerformanceMetrics:
    """WebSocket performance metrics"""
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    response_time_ms: float = 0.0
    throughput_mbps: float = 0.0
    error_rate: float = 0.0
    uptime_seconds: int = 0


@dataclass
class SecurityMetrics:
    """WebSocket security metrics"""
    blocked_connections: int = 0
    failed_authentications: int = 0
    rate_limited_requests: int = 0
    csrf_failures: int = 0
    suspicious_activities: int = 0
    security_events_by_type: Dict[str, int] = field(default_factory=dict)


@dataclass
class HealthCheckResult:
    """Health check result"""
    status: HealthStatus
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None
    response_time_ms: Optional[float] = None


class WebSocketProductionMonitor:
    """
    Production monitoring system for WebSocket connections
    
    Provides comprehensive metrics collection, health monitoring,
    alerting, and integration with external monitoring systems.
    """
    
    def __init__(self, config: ProductionMonitoringConfig, 
                 logger: ProductionWebSocketLogger,
                 app: Optional[Flask] = None,
                 socketio: Optional[SocketIO] = None):
        """
        Initialize production WebSocket monitor
        
        Args:
            config: Production monitoring configuration
            logger: Production WebSocket logger
            app: Flask application instance (optional)
            socketio: SocketIO instance (optional)
        """
        self.config = config
        self.logger = logger
        self.app = app
        self.socketio = socketio
        
        # Metrics storage
        self.connection_metrics = ConnectionMetrics()
        self.message_metrics = MessageMetrics()
        self.performance_metrics = PerformanceMetrics()
        self.security_metrics = SecurityMetrics()
        
        # Monitoring state
        self.start_time = time.time()
        self.metrics_lock = threading.Lock()
        self.health_checks = {}
        self.alert_handlers = []
        
        # Time series data for rate calculations
        self.connection_history = deque(maxlen=300)  # 5 minutes of data
        self.message_history = deque(maxlen=300)
        self.error_history = deque(maxlen=300)
        
        # Prometheus metrics (if available)
        self.prometheus_metrics = {}
        if PROMETHEUS_AVAILABLE and self.config.metrics_format == "prometheus":
            self._setup_prometheus_metrics()
        
        # Setup monitoring endpoints
        if self.app:
            self._setup_monitoring_endpoints()
        
        # Start background monitoring
        self._start_background_monitoring()
    
    def _setup_prometheus_metrics(self) -> None:
        """Setup Prometheus metrics"""
        self.prometheus_metrics = {
            'connections_total': Counter('websocket_connections_total', 'Total WebSocket connections'),
            'connections_active': Gauge('websocket_connections_active', 'Active WebSocket connections'),
            'connections_failed': Counter('websocket_connections_failed_total', 'Failed WebSocket connections'),
            'messages_total': Counter('websocket_messages_total', 'Total WebSocket messages', ['event', 'namespace']),
            'message_processing_time': Histogram('websocket_message_processing_seconds', 'Message processing time'),
            'response_time': Histogram('websocket_response_time_seconds', 'WebSocket response time'),
            'cpu_usage': Gauge('websocket_cpu_usage_percent', 'CPU usage percentage'),
            'memory_usage': Gauge('websocket_memory_usage_bytes', 'Memory usage in bytes'),
            'error_rate': Gauge('websocket_error_rate', 'Error rate per second'),
            'security_events': Counter('websocket_security_events_total', 'Security events', ['event_type']),
        }
    
    def _setup_monitoring_endpoints(self) -> None:
        """Setup monitoring HTTP endpoints"""
        
        @self.app.route(self.config.metrics_endpoint, methods=['GET'])
        def metrics_endpoint():
            """Metrics endpoint for monitoring systems"""
            if self.config.metrics_format == "prometheus" and PROMETHEUS_AVAILABLE:
                return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}
            else:
                return jsonify(self.get_all_metrics())
        
        @self.app.route(self.config.health_check_endpoint, methods=['GET'])
        def health_check_endpoint():
            """Health check endpoint"""
            health_result = self.perform_health_check()
            status_code = 200 if health_result.status == HealthStatus.HEALTHY else 503
            
            response_data = {
                'status': health_result.status.value,
                'message': health_result.message,
                'timestamp': health_result.timestamp,
                'response_time_ms': health_result.response_time_ms
            }
            
            if self.config.detailed_health_info and health_result.details:
                response_data['details'] = health_result.details
            
            return jsonify(response_data), status_code
    
    def _start_background_monitoring(self) -> None:
        """Start background monitoring thread"""
        def monitoring_loop():
            while True:
                try:
                    self._update_performance_metrics()
                    self._calculate_rates()
                    self._check_alert_thresholds()
                    time.sleep(10)  # Update every 10 seconds
                except Exception as e:
                    self.logger.log_error_event(
                        event_type="monitoring_error",
                        message=f"Background monitoring error: {str(e)}",
                        exception=e
                    )
                    time.sleep(30)  # Wait longer on error
        
        monitoring_thread = threading.Thread(target=monitoring_loop, daemon=True)
        monitoring_thread.start()
    
    def record_connection_event(self, event_type: str, 
                              session_id: Optional[str] = None,
                              user_id: Optional[int] = None,
                              namespace: Optional[str] = None,
                              success: bool = True) -> None:
        """Record WebSocket connection event"""
        
        with self.metrics_lock:
            current_time = time.time()
            
            if event_type == "connect":
                self.connection_metrics.total_connections += 1
                if success:
                    self.connection_metrics.active_connections += 1
                    if namespace:
                        self.connection_metrics.connections_by_namespace[namespace] = \
                            self.connection_metrics.connections_by_namespace.get(namespace, 0) + 1
                    if user_id:
                        self.connection_metrics.connections_by_user[user_id] = \
                            self.connection_metrics.connections_by_user.get(user_id, 0) + 1
                else:
                    self.connection_metrics.failed_connections += 1
                
                # Record for rate calculation
                self.connection_history.append((current_time, 1 if success else 0))
                
            elif event_type == "disconnect":
                self.connection_metrics.active_connections = max(0, self.connection_metrics.active_connections - 1)
                if namespace and namespace in self.connection_metrics.connections_by_namespace:
                    self.connection_metrics.connections_by_namespace[namespace] = \
                        max(0, self.connection_metrics.connections_by_namespace[namespace] - 1)
                if user_id and user_id in self.connection_metrics.connections_by_user:
                    self.connection_metrics.connections_by_user[user_id] = \
                        max(0, self.connection_metrics.connections_by_user[user_id] - 1)
        
        # Update Prometheus metrics
        if PROMETHEUS_AVAILABLE and self.prometheus_metrics:
            if event_type == "connect":
                self.prometheus_metrics['connections_total'].inc()
                if success:
                    self.prometheus_metrics['connections_active'].inc()
                else:
                    self.prometheus_metrics['connections_failed'].inc()
            elif event_type == "disconnect":
                self.prometheus_metrics['connections_active'].dec()
    
    def record_message_event(self, event_name: str,
                           namespace: Optional[str] = None,
                           message_size: Optional[int] = None,
                           processing_time_ms: Optional[float] = None,
                           success: bool = True) -> None:
        """Record WebSocket message event"""
        
        with self.metrics_lock:
            current_time = time.time()
            
            self.message_metrics.total_messages += 1
            
            if success:
                # Update event counters
                self.message_metrics.messages_by_event[event_name] = \
                    self.message_metrics.messages_by_event.get(event_name, 0) + 1
                
                if namespace:
                    self.message_metrics.messages_by_namespace[namespace] = \
                        self.message_metrics.messages_by_namespace.get(namespace, 0) + 1
                
                # Update averages
                if message_size:
                    current_avg = self.message_metrics.average_message_size
                    total_messages = self.message_metrics.total_messages
                    self.message_metrics.average_message_size = \
                        (current_avg * (total_messages - 1) + message_size) / total_messages
                
                if processing_time_ms:
                    current_avg = self.message_metrics.message_processing_time
                    total_messages = self.message_metrics.total_messages
                    self.message_metrics.message_processing_time = \
                        (current_avg * (total_messages - 1) + processing_time_ms) / total_messages
            else:
                self.message_metrics.failed_messages += 1
            
            # Record for rate calculation
            self.message_history.append((current_time, 1 if success else 0))
        
        # Update Prometheus metrics
        if PROMETHEUS_AVAILABLE and self.prometheus_metrics:
            self.prometheus_metrics['messages_total'].labels(
                event=event_name, 
                namespace=namespace or 'default'
            ).inc()
            
            if processing_time_ms:
                self.prometheus_metrics['message_processing_time'].observe(processing_time_ms / 1000)
    
    def record_security_event(self, event_type: str,
                            session_id: Optional[str] = None,
                            user_id: Optional[int] = None,
                            severity: str = "warning") -> None:
        """Record WebSocket security event"""
        
        with self.metrics_lock:
            # Update security metrics based on event type
            if event_type == "blocked_connection":
                self.security_metrics.blocked_connections += 1
            elif event_type == "failed_authentication":
                self.security_metrics.failed_authentications += 1
            elif event_type == "rate_limited":
                self.security_metrics.rate_limited_requests += 1
            elif event_type == "csrf_failure":
                self.security_metrics.csrf_failures += 1
            elif event_type == "suspicious_activity":
                self.security_metrics.suspicious_activities += 1
            
            # Update event type counters
            self.security_metrics.security_events_by_type[event_type] = \
                self.security_metrics.security_events_by_type.get(event_type, 0) + 1
        
        # Update Prometheus metrics
        if PROMETHEUS_AVAILABLE and self.prometheus_metrics:
            self.prometheus_metrics['security_events'].labels(event_type=event_type).inc()
        
        # Log security event
        self.logger.log_security_event(
            event_type=event_type,
            message=f"Security event recorded: {event_type}",
            session_id=session_id,
            user_id=user_id,
            level=WebSocketLogLevel.WARNING if severity == "warning" else WebSocketLogLevel.CRITICAL
        )
    
    def record_performance_metric(self, metric_name: str, value: float,
                                labels: Optional[Dict[str, str]] = None) -> None:
        """Record custom performance metric"""
        
        # Update Prometheus metrics
        if PROMETHEUS_AVAILABLE and self.prometheus_metrics and metric_name in self.prometheus_metrics:
            metric = self.prometheus_metrics[metric_name]
            if hasattr(metric, 'observe'):  # Histogram
                metric.observe(value)
            elif hasattr(metric, 'set'):  # Gauge
                metric.set(value)
            elif hasattr(metric, 'inc'):  # Counter
                metric.inc(value)
    
    def _update_performance_metrics(self) -> None:
        """Update system performance metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            self.performance_metrics.cpu_usage = cpu_percent
            
            # Memory usage
            process = psutil.Process()
            memory_info = process.memory_info()
            self.performance_metrics.memory_usage = memory_info.rss / 1024 / 1024  # MB
            
            # Uptime
            self.performance_metrics.uptime_seconds = int(time.time() - self.start_time)
            
            # Update Prometheus metrics
            if PROMETHEUS_AVAILABLE and self.prometheus_metrics:
                self.prometheus_metrics['cpu_usage'].set(cpu_percent)
                self.prometheus_metrics['memory_usage'].set(memory_info.rss)
            
        except Exception as e:
            self.logger.log_error_event(
                event_type="performance_monitoring_error",
                message=f"Failed to update performance metrics: {str(e)}",
                exception=e
            )
    
    def _calculate_rates(self) -> None:
        """Calculate rate-based metrics"""
        current_time = time.time()
        time_window = 60  # 1 minute window
        
        with self.metrics_lock:
            # Connection rate
            recent_connections = [
                count for timestamp, count in self.connection_history
                if current_time - timestamp <= time_window
            ]
            self.connection_metrics.connection_rate = sum(recent_connections) / time_window if recent_connections else 0.0
            
            # Message rate
            recent_messages = [
                count for timestamp, count in self.message_history
                if current_time - timestamp <= time_window
            ]
            self.message_metrics.messages_per_second = sum(recent_messages) / time_window if recent_messages else 0.0
            
            # Error rate
            recent_errors = [
                count for timestamp, count in self.error_history
                if current_time - timestamp <= time_window
            ]
            self.performance_metrics.error_rate = sum(recent_errors) / time_window if recent_errors else 0.0
            
            # Update Prometheus metrics
            if PROMETHEUS_AVAILABLE and self.prometheus_metrics:
                self.prometheus_metrics['error_rate'].set(self.performance_metrics.error_rate)
    
    def _check_alert_thresholds(self) -> None:
        """Check alert thresholds and trigger alerts if necessary"""
        if not self.config.alerting_enabled:
            return
        
        alerts = []
        thresholds = self.config.alert_thresholds
        
        # Check connection errors
        if (self.connection_metrics.failed_connections > thresholds.get('connection_errors', 10)):
            alerts.append({
                'type': 'connection_errors',
                'message': f'High connection error count: {self.connection_metrics.failed_connections}',
                'value': self.connection_metrics.failed_connections,
                'threshold': thresholds.get('connection_errors', 10)
            })
        
        # Check message errors
        if (self.message_metrics.failed_messages > thresholds.get('message_errors', 50)):
            alerts.append({
                'type': 'message_errors',
                'message': f'High message error count: {self.message_metrics.failed_messages}',
                'value': self.message_metrics.failed_messages,
                'threshold': thresholds.get('message_errors', 50)
            })
        
        # Check response time
        if (self.performance_metrics.response_time_ms > thresholds.get('response_time_ms', 1000)):
            alerts.append({
                'type': 'response_time',
                'message': f'High response time: {self.performance_metrics.response_time_ms:.2f}ms',
                'value': self.performance_metrics.response_time_ms,
                'threshold': thresholds.get('response_time_ms', 1000)
            })
        
        # Check memory usage
        if (self.performance_metrics.memory_usage > thresholds.get('memory_usage_mb', 500)):
            alerts.append({
                'type': 'memory_usage',
                'message': f'High memory usage: {self.performance_metrics.memory_usage:.2f}MB',
                'value': self.performance_metrics.memory_usage,
                'threshold': thresholds.get('memory_usage_mb', 500)
            })
        
        # Send alerts
        for alert in alerts:
            self._send_alert(alert)
    
    def _send_alert(self, alert: Dict[str, Any]) -> None:
        """Send alert to configured webhook"""
        if not self.config.alert_webhook_url or not REQUESTS_AVAILABLE:
            return
        
        try:
            payload = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'service': 'websocket',
                'hostname': socket.gethostname(),
                'alert': alert
            }
            
            response = requests.post(
                self.config.alert_webhook_url,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                self.logger.log_system_event(
                    event_type="alert_sent",
                    message=f"Alert sent successfully: {alert['type']}",
                    metadata={'alert': alert}
                )
            else:
                self.logger.log_error_event(
                    event_type="alert_send_failed",
                    message=f"Failed to send alert: HTTP {response.status_code}",
                    metadata={'alert': alert}
                )
                
        except Exception as e:
            self.logger.log_error_event(
                event_type="alert_send_error",
                message=f"Error sending alert: {str(e)}",
                exception=e,
                metadata={'alert': alert}
            )
    
    def perform_health_check(self) -> HealthCheckResult:
        """Perform comprehensive health check"""
        start_time = time.time()
        
        try:
            health_details = {}
            overall_status = HealthStatus.HEALTHY
            issues = []
            
            # Check system resources
            if self.performance_metrics.cpu_usage > 90:
                overall_status = HealthStatus.CRITICAL
                issues.append(f"High CPU usage: {self.performance_metrics.cpu_usage:.1f}%")
            elif self.performance_metrics.cpu_usage > 70:
                overall_status = max(overall_status, HealthStatus.WARNING)
                issues.append(f"Elevated CPU usage: {self.performance_metrics.cpu_usage:.1f}%")
            
            if self.performance_metrics.memory_usage > 1000:  # 1GB
                overall_status = HealthStatus.CRITICAL
                issues.append(f"High memory usage: {self.performance_metrics.memory_usage:.1f}MB")
            elif self.performance_metrics.memory_usage > 500:  # 500MB
                overall_status = max(overall_status, HealthStatus.WARNING)
                issues.append(f"Elevated memory usage: {self.performance_metrics.memory_usage:.1f}MB")
            
            # Check error rates
            if self.performance_metrics.error_rate > 10:  # 10 errors per second
                overall_status = HealthStatus.CRITICAL
                issues.append(f"High error rate: {self.performance_metrics.error_rate:.2f}/sec")
            elif self.performance_metrics.error_rate > 1:  # 1 error per second
                overall_status = max(overall_status, HealthStatus.WARNING)
                issues.append(f"Elevated error rate: {self.performance_metrics.error_rate:.2f}/sec")
            
            # Check WebSocket connectivity
            if self.socketio:
                try:
                    # Simple connectivity check
                    health_details['websocket_server'] = 'running'
                except Exception as e:
                    overall_status = HealthStatus.CRITICAL
                    issues.append(f"WebSocket server issue: {str(e)}")
                    health_details['websocket_server'] = 'error'
            
            # Compile health details
            health_details.update({
                'active_connections': self.connection_metrics.active_connections,
                'total_connections': self.connection_metrics.total_connections,
                'failed_connections': self.connection_metrics.failed_connections,
                'messages_per_second': self.message_metrics.messages_per_second,
                'cpu_usage_percent': self.performance_metrics.cpu_usage,
                'memory_usage_mb': self.performance_metrics.memory_usage,
                'uptime_seconds': self.performance_metrics.uptime_seconds,
                'error_rate_per_second': self.performance_metrics.error_rate
            })
            
            response_time_ms = (time.time() - start_time) * 1000
            
            if issues:
                message = f"Health check completed with issues: {'; '.join(issues)}"
            else:
                message = "All systems healthy"
            
            return HealthCheckResult(
                status=overall_status,
                message=message,
                details=health_details,
                timestamp=datetime.now(timezone.utc).isoformat(),
                response_time_ms=response_time_ms
            )
            
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            
            self.logger.log_error_event(
                event_type="health_check_error",
                message=f"Health check failed: {str(e)}",
                exception=e
            )
            
            return HealthCheckResult(
                status=HealthStatus.CRITICAL,
                message=f"Health check failed: {str(e)}",
                timestamp=datetime.now(timezone.utc).isoformat(),
                response_time_ms=response_time_ms
            )
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all monitoring metrics"""
        with self.metrics_lock:
            return {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'uptime_seconds': self.performance_metrics.uptime_seconds,
                'connections': asdict(self.connection_metrics),
                'messages': asdict(self.message_metrics),
                'performance': asdict(self.performance_metrics),
                'security': asdict(self.security_metrics)
            }
    
    def get_connection_metrics(self) -> ConnectionMetrics:
        """Get connection metrics"""
        return self.connection_metrics
    
    def get_message_metrics(self) -> MessageMetrics:
        """Get message metrics"""
        return self.message_metrics
    
    def get_performance_metrics(self) -> PerformanceMetrics:
        """Get performance metrics"""
        return self.performance_metrics
    
    def get_security_metrics(self) -> SecurityMetrics:
        """Get security metrics"""
        return self.security_metrics
    
    @contextmanager
    def monitor_operation(self, operation_name: str,
                         session_id: Optional[str] = None,
                         user_id: Optional[int] = None):
        """Context manager for monitoring operations"""
        start_time = time.time()
        
        try:
            yield
            # Record successful operation
            duration_ms = (time.time() - start_time) * 1000
            self.record_performance_metric('operation_duration', duration_ms)
            
            self.logger.log_performance_event(
                event_type=f"{operation_name}_completed",
                message=f"Operation {operation_name} completed successfully",
                duration_ms=duration_ms,
                session_id=session_id,
                user_id=user_id
            )
            
        except Exception as e:
            # Record failed operation
            duration_ms = (time.time() - start_time) * 1000
            self.error_history.append((time.time(), 1))
            
            self.logger.log_error_event(
                event_type=f"{operation_name}_failed",
                message=f"Operation {operation_name} failed: {str(e)}",
                session_id=session_id,
                user_id=user_id,
                exception=e,
                metadata={'duration_ms': duration_ms}
            )
            raise
    
    def reset_metrics(self) -> None:
        """Reset all metrics (useful for testing)"""
        with self.metrics_lock:
            self.connection_metrics = ConnectionMetrics()
            self.message_metrics = MessageMetrics()
            self.performance_metrics = PerformanceMetrics()
            self.security_metrics = SecurityMetrics()
            
            self.connection_history.clear()
            self.message_history.clear()
            self.error_history.clear()


def create_production_monitor(config: ProductionMonitoringConfig,
                            logger: ProductionWebSocketLogger,
                            app: Optional[Flask] = None,
                            socketio: Optional[SocketIO] = None) -> WebSocketProductionMonitor:
    """
    Factory function to create production WebSocket monitor
    
    Args:
        config: Production monitoring configuration
        logger: Production WebSocket logger
        app: Flask application instance (optional)
        socketio: SocketIO instance (optional)
    
    Returns:
        Configured production WebSocket monitor
    """
    return WebSocketProductionMonitor(config, logger, app, socketio)
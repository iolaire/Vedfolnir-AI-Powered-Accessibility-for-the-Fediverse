# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Configuration Service Health Monitor

Comprehensive health monitoring system for configuration service components,
including availability checks, error rate monitoring, performance tracking,
and alerting capabilities.
"""

import time
import threading
import logging
import psutil
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import deque, defaultdict
import statistics
import json

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class ComponentType(Enum):
    """Configuration service component types"""
    CONFIGURATION_SERVICE = "configuration_service"
    CONFIGURATION_CACHE = "configuration_cache"
    EVENT_BUS = "event_bus"
    DATABASE_CONNECTION = "database_connection"
    METRICS_COLLECTOR = "metrics_collector"


@dataclass
class HealthCheckResult:
    """Result of a health check"""
    component: str
    component_type: ComponentType
    status: HealthStatus
    timestamp: datetime
    response_time_ms: float
    details: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class AlertThreshold:
    """Alert threshold configuration"""
    metric_name: str
    warning_threshold: float
    critical_threshold: float
    comparison: str = "greater_than"  # greater_than, less_than, equals
    enabled: bool = True


@dataclass
class HealthSummary:
    """Overall health summary"""
    overall_status: HealthStatus
    healthy_components: int
    warning_components: int
    critical_components: int
    unknown_components: int
    last_check_time: datetime
    uptime_seconds: float
    error_rate: float
    performance_score: float


class ConfigurationHealthMonitor:
    """
    Comprehensive health monitoring system for configuration service
    
    Features:
    - Component health checks
    - Performance monitoring
    - Error rate tracking
    - Alerting system
    - Health dashboard data
    - Automatic recovery detection
    """
    
    def __init__(self, check_interval: int = 60, history_retention_hours: int = 24):
        """
        Initialize health monitor
        
        Args:
            check_interval: Health check interval in seconds
            history_retention_hours: How long to retain health history
        """
        self.check_interval = check_interval
        self.history_retention_hours = history_retention_hours
        self.start_time = datetime.now(timezone.utc)
        
        # Health check results storage
        self._health_history: deque = deque(maxlen=10000)
        self._health_lock = threading.RLock()
        
        # Component registry
        self._components: Dict[str, Dict[str, Any]] = {}
        self._components_lock = threading.RLock()
        
        # Alert thresholds
        self._alert_thresholds: Dict[str, AlertThreshold] = {}
        self._alert_callbacks: List[Callable] = []
        self._alert_lock = threading.RLock()
        
        # Performance tracking
        self._performance_metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._performance_lock = threading.RLock()
        
        # Error tracking
        self._error_counts: Dict[str, int] = defaultdict(int)
        self._error_history: deque = deque(maxlen=1000)
        self._error_lock = threading.RLock()
        
        # Monitoring state
        self._monitoring_active = False
        self._monitor_thread: Optional[threading.Thread] = None
        
        # Setup default alert thresholds
        self._setup_default_thresholds()
    
    def register_component(self, name: str, component_type: ComponentType, 
                          health_check_func: Callable[[], Dict[str, Any]],
                          enabled: bool = True):
        """
        Register a component for health monitoring
        
        Args:
            name: Component name
            component_type: Type of component
            health_check_func: Function that returns health status
            enabled: Whether monitoring is enabled for this component
        """
        with self._components_lock:
            self._components[name] = {
                'type': component_type,
                'health_check_func': health_check_func,
                'enabled': enabled,
                'last_check': None,
                'last_status': HealthStatus.UNKNOWN,
                'consecutive_failures': 0,
                'total_checks': 0,
                'successful_checks': 0
            }
        
        logger.info(f"Registered component for health monitoring: {name} ({component_type.value})")
    
    def unregister_component(self, name: str):
        """
        Unregister a component from health monitoring
        
        Args:
            name: Component name to unregister
        """
        with self._components_lock:
            if name in self._components:
                del self._components[name]
                logger.info(f"Unregistered component from health monitoring: {name}")
    
    def set_alert_threshold(self, metric_name: str, warning_threshold: float,
                           critical_threshold: float, comparison: str = "greater_than"):
        """
        Set alert threshold for a metric
        
        Args:
            metric_name: Name of the metric
            warning_threshold: Warning level threshold
            critical_threshold: Critical level threshold
            comparison: Comparison type (greater_than, less_than, equals)
        """
        with self._alert_lock:
            self._alert_thresholds[metric_name] = AlertThreshold(
                metric_name=metric_name,
                warning_threshold=warning_threshold,
                critical_threshold=critical_threshold,
                comparison=comparison,
                enabled=True
            )
        
        logger.info(f"Set alert threshold for {metric_name}: warning={warning_threshold}, critical={critical_threshold}")
    
    def add_alert_callback(self, callback: Callable[[str, HealthStatus, Dict[str, Any]], None]):
        """
        Add callback function for alerts
        
        Args:
            callback: Function to call when alert is triggered
                     Signature: callback(component_name, status, details)
        """
        with self._alert_lock:
            self._alert_callbacks.append(callback)
        
        logger.info("Added alert callback function")
    
    def start_monitoring(self):
        """Start continuous health monitoring"""
        if self._monitoring_active:
            logger.warning("Health monitoring is already active")
            return
        
        self._monitoring_active = True
        self._monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self._monitor_thread.start()
        
        logger.info(f"Started configuration health monitoring (interval: {self.check_interval}s)")
    
    def stop_monitoring(self):
        """Stop continuous health monitoring"""
        self._monitoring_active = False
        
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5)
        
        logger.info("Stopped configuration health monitoring")
    
    def perform_health_check(self, component_name: str = None) -> List[HealthCheckResult]:
        """
        Perform health check on specified component or all components
        
        Args:
            component_name: Specific component to check, or None for all
            
        Returns:
            List of health check results
        """
        results = []
        
        with self._components_lock:
            components_to_check = {}
            if component_name:
                if component_name in self._components:
                    components_to_check[component_name] = self._components[component_name]
            else:
                components_to_check = self._components.copy()
        
        for name, component_info in components_to_check.items():
            if not component_info['enabled']:
                continue
            
            result = self._check_component_health(name, component_info)
            results.append(result)
            
            # Update component stats
            with self._components_lock:
                self._components[name]['last_check'] = result.timestamp
                self._components[name]['last_status'] = result.status
                self._components[name]['total_checks'] += 1
                
                if result.status == HealthStatus.HEALTHY:
                    self._components[name]['successful_checks'] += 1
                    self._components[name]['consecutive_failures'] = 0
                else:
                    self._components[name]['consecutive_failures'] += 1
            
            # Record performance metrics
            self._record_performance_metric(name, result.response_time_ms)
            
            # Check for alerts
            self._check_alerts(name, result)
        
        # Store results in history
        with self._health_lock:
            for result in results:
                self._health_history.append(result)
        
        return results
    
    def get_health_status(self, component_name: str = None) -> Dict[str, Any]:
        """
        Get current health status
        
        Args:
            component_name: Specific component, or None for overall status
            
        Returns:
            Dictionary with health status information
        """
        if component_name:
            return self._get_component_status(component_name)
        else:
            return self._get_overall_status()
    
    def get_health_summary(self) -> HealthSummary:
        """
        Get comprehensive health summary
        
        Returns:
            HealthSummary object with overall system health
        """
        with self._components_lock:
            component_statuses = [comp['last_status'] for comp in self._components.values()]
        
        healthy = sum(1 for status in component_statuses if status == HealthStatus.HEALTHY)
        warning = sum(1 for status in component_statuses if status == HealthStatus.WARNING)
        critical = sum(1 for status in component_statuses if status == HealthStatus.CRITICAL)
        unknown = sum(1 for status in component_statuses if status == HealthStatus.UNKNOWN)
        
        # Determine overall status
        if critical > 0:
            overall_status = HealthStatus.CRITICAL
        elif warning > 0:
            overall_status = HealthStatus.WARNING
        elif healthy > 0:
            overall_status = HealthStatus.HEALTHY
        else:
            overall_status = HealthStatus.UNKNOWN
        
        # Calculate error rate
        error_rate = self._calculate_error_rate()
        
        # Calculate performance score
        performance_score = self._calculate_performance_score()
        
        # Calculate uptime
        uptime = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        
        return HealthSummary(
            overall_status=overall_status,
            healthy_components=healthy,
            warning_components=warning,
            critical_components=critical,
            unknown_components=unknown,
            last_check_time=datetime.now(timezone.utc),
            uptime_seconds=uptime,
            error_rate=error_rate,
            performance_score=performance_score
        )
    
    def get_performance_metrics(self, component_name: str = None, 
                               hours: int = 1) -> Dict[str, Any]:
        """
        Get performance metrics for components
        
        Args:
            component_name: Specific component, or None for all
            hours: Number of hours of data to include
            
        Returns:
            Dictionary with performance metrics
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        with self._performance_lock:
            if component_name:
                if component_name in self._performance_metrics:
                    metrics = list(self._performance_metrics[component_name])
                    return self._analyze_performance_metrics(component_name, metrics)
                else:
                    return {}
            else:
                all_metrics = {}
                for comp_name, metrics in self._performance_metrics.items():
                    all_metrics[comp_name] = self._analyze_performance_metrics(comp_name, list(metrics))
                return all_metrics
    
    def get_error_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get error statistics
        
        Args:
            hours: Number of hours to analyze
            
        Returns:
            Dictionary with error statistics
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        with self._error_lock:
            recent_errors = [error for error in self._error_history 
                           if error['timestamp'] >= cutoff_time]
        
        if not recent_errors:
            return {
                'total_errors': 0,
                'error_rate': 0.0,
                'errors_by_component': {},
                'errors_by_type': {},
                'error_timeline': []
            }
        
        # Analyze errors
        errors_by_component = defaultdict(int)
        errors_by_type = defaultdict(int)
        
        for error in recent_errors:
            errors_by_component[error['component']] += 1
            errors_by_type[error['error_type']] += 1
        
        total_errors = len(recent_errors)
        
        # Calculate error rate (errors per hour)
        error_rate = total_errors / hours if hours > 0 else 0.0
        
        return {
            'total_errors': total_errors,
            'error_rate': error_rate,
            'errors_by_component': dict(errors_by_component),
            'errors_by_type': dict(errors_by_type),
            'error_timeline': [
                {
                    'timestamp': error['timestamp'].isoformat(),
                    'component': error['component'],
                    'error_type': error['error_type'],
                    'message': error['message']
                }
                for error in recent_errors[-50:]  # Last 50 errors
            ]
        }
    
    def get_health_dashboard_data(self) -> Dict[str, Any]:
        """
        Get comprehensive data for health monitoring dashboard
        
        Returns:
            Dictionary with all dashboard data
        """
        summary = self.get_health_summary()
        performance = self.get_performance_metrics(hours=24)
        errors = self.get_error_statistics(hours=24)
        
        # Component details
        component_details = []
        with self._components_lock:
            for name, info in self._components.items():
                uptime_percent = 0.0
                if info['total_checks'] > 0:
                    uptime_percent = (info['successful_checks'] / info['total_checks']) * 100
                
                component_details.append({
                    'name': name,
                    'type': info['type'].value,
                    'status': info['last_status'].value,
                    'enabled': info['enabled'],
                    'last_check': info['last_check'].isoformat() if info['last_check'] else None,
                    'total_checks': info['total_checks'],
                    'successful_checks': info['successful_checks'],
                    'consecutive_failures': info['consecutive_failures'],
                    'uptime_percent': uptime_percent
                })
        
        # Recent health history
        with self._health_lock:
            recent_history = list(self._health_history)[-100:]  # Last 100 checks
        
        health_timeline = []
        for result in recent_history:
            health_timeline.append({
                'timestamp': result.timestamp.isoformat(),
                'component': result.component,
                'status': result.status.value,
                'response_time_ms': result.response_time_ms
            })
        
        return {
            'summary': {
                'overall_status': summary.overall_status.value,
                'healthy_components': summary.healthy_components,
                'warning_components': summary.warning_components,
                'critical_components': summary.critical_components,
                'unknown_components': summary.unknown_components,
                'uptime_seconds': summary.uptime_seconds,
                'error_rate': summary.error_rate,
                'performance_score': summary.performance_score
            },
            'components': component_details,
            'performance_metrics': performance,
            'error_statistics': errors,
            'health_timeline': health_timeline,
            'alert_thresholds': {
                name: {
                    'warning_threshold': threshold.warning_threshold,
                    'critical_threshold': threshold.critical_threshold,
                    'comparison': threshold.comparison,
                    'enabled': threshold.enabled
                }
                for name, threshold in self._alert_thresholds.items()
            }
        }
    
    def export_health_data(self, hours: int = 24, format: str = 'json') -> str:
        """
        Export health monitoring data
        
        Args:
            hours: Number of hours of data to export
            format: Export format ('json' or 'csv')
            
        Returns:
            Exported data as string
        """
        dashboard_data = self.get_health_dashboard_data()
        
        export_data = {
            'export_timestamp': datetime.now(timezone.utc).isoformat(),
            'time_period_hours': hours,
            'monitoring_start_time': self.start_time.isoformat(),
            'dashboard_data': dashboard_data
        }
        
        if format.lower() == 'json':
            return json.dumps(export_data, indent=2, default=str)
        else:
            # Simplified CSV format
            summary = dashboard_data['summary']
            return f"Configuration Health Export - {export_data['export_timestamp']}\n" + \
                   f"Overall Status: {summary['overall_status']}\n" + \
                   f"Healthy Components: {summary['healthy_components']}\n" + \
                   f"Warning Components: {summary['warning_components']}\n" + \
                   f"Critical Components: {summary['critical_components']}\n" + \
                   f"Error Rate: {summary['error_rate']:.2f}\n" + \
                   f"Performance Score: {summary['performance_score']:.2f}\n"
    
    def _setup_default_thresholds(self):
        """Setup default alert thresholds"""
        default_thresholds = [
            ('response_time_ms', 100.0, 500.0, 'greater_than'),
            ('error_rate', 0.05, 0.10, 'greater_than'),
            ('cache_hit_rate', 0.80, 0.60, 'less_than'),
            ('memory_usage_percent', 80.0, 95.0, 'greater_than'),
            ('cpu_usage_percent', 70.0, 90.0, 'greater_than')
        ]
        
        for metric, warning, critical, comparison in default_thresholds:
            self.set_alert_threshold(metric, warning, critical, comparison)
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self._monitoring_active:
            try:
                start_time = time.time()
                
                # Perform health checks
                self.perform_health_check()
                
                # Clean up old data
                self._cleanup_old_data()
                
                # Calculate sleep time to maintain interval
                elapsed = time.time() - start_time
                sleep_time = max(0, self.check_interval - elapsed)
                
                if sleep_time > 0:
                    time.sleep(sleep_time)
                
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {str(e)}")
                time.sleep(self.check_interval)
    
    def _check_component_health(self, name: str, component_info: Dict[str, Any]) -> HealthCheckResult:
        """
        Check health of a specific component
        
        Args:
            name: Component name
            component_info: Component information
            
        Returns:
            HealthCheckResult
        """
        start_time = time.time()
        
        try:
            # Call the component's health check function
            health_data = component_info['health_check_func']()
            
            response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            # Determine status based on health data
            status = self._determine_health_status(health_data)
            
            return HealthCheckResult(
                component=name,
                component_type=component_info['type'],
                status=status,
                timestamp=datetime.now(timezone.utc),
                response_time_ms=response_time,
                details=health_data,
                metrics=self._extract_metrics(health_data)
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            
            # Record error
            self._record_error(name, 'health_check_failure', str(e))
            
            return HealthCheckResult(
                component=name,
                component_type=component_info['type'],
                status=HealthStatus.CRITICAL,
                timestamp=datetime.now(timezone.utc),
                response_time_ms=response_time,
                error_message=str(e),
                details={'error': str(e)}
            )
    
    def _determine_health_status(self, health_data: Dict[str, Any]) -> HealthStatus:
        """
        Determine health status from health check data
        
        Args:
            health_data: Health check data
            
        Returns:
            HealthStatus
        """
        # Check if explicit status is provided
        if 'status' in health_data:
            status_str = health_data['status'].lower()
            if status_str == 'healthy':
                return HealthStatus.HEALTHY
            elif status_str == 'warning':
                return HealthStatus.WARNING
            elif status_str == 'critical':
                return HealthStatus.CRITICAL
            else:
                return HealthStatus.UNKNOWN
        
        # Check for error indicators
        if health_data.get('error') or health_data.get('errors'):
            return HealthStatus.CRITICAL
        
        # Check metrics against thresholds
        metrics = self._extract_metrics(health_data)
        worst_status = HealthStatus.HEALTHY
        
        for metric_name, value in metrics.items():
            if metric_name in self._alert_thresholds:
                threshold = self._alert_thresholds[metric_name]
                if not threshold.enabled:
                    continue
                
                status = self._evaluate_threshold(value, threshold)
                if status == HealthStatus.CRITICAL:
                    worst_status = HealthStatus.CRITICAL
                elif status == HealthStatus.WARNING and worst_status != HealthStatus.CRITICAL:
                    worst_status = HealthStatus.WARNING
        
        return worst_status
    
    def _evaluate_threshold(self, value: float, threshold: AlertThreshold) -> HealthStatus:
        """
        Evaluate a metric value against alert threshold
        
        Args:
            value: Metric value
            threshold: Alert threshold
            
        Returns:
            HealthStatus based on threshold evaluation
        """
        if threshold.comparison == 'greater_than':
            if value >= threshold.critical_threshold:
                return HealthStatus.CRITICAL
            elif value >= threshold.warning_threshold:
                return HealthStatus.WARNING
        elif threshold.comparison == 'less_than':
            if value <= threshold.critical_threshold:
                return HealthStatus.CRITICAL
            elif value <= threshold.warning_threshold:
                return HealthStatus.WARNING
        elif threshold.comparison == 'equals':
            if value == threshold.critical_threshold:
                return HealthStatus.CRITICAL
            elif value == threshold.warning_threshold:
                return HealthStatus.WARNING
        
        return HealthStatus.HEALTHY
    
    def _extract_metrics(self, health_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Extract numeric metrics from health data
        
        Args:
            health_data: Health check data
            
        Returns:
            Dictionary of numeric metrics
        """
        metrics = {}
        
        for key, value in health_data.items():
            if isinstance(value, (int, float)):
                metrics[key] = float(value)
            elif isinstance(value, dict):
                # Recursively extract from nested dictionaries
                nested_metrics = self._extract_metrics(value)
                for nested_key, nested_value in nested_metrics.items():
                    metrics[f"{key}.{nested_key}"] = nested_value
        
        return metrics
    
    def _record_performance_metric(self, component_name: str, response_time_ms: float):
        """Record performance metric for a component"""
        with self._performance_lock:
            self._performance_metrics[component_name].append({
                'timestamp': datetime.now(timezone.utc),
                'response_time_ms': response_time_ms
            })
    
    def _record_error(self, component_name: str, error_type: str, message: str):
        """Record an error for a component"""
        with self._error_lock:
            self._error_counts[component_name] += 1
            self._error_history.append({
                'timestamp': datetime.now(timezone.utc),
                'component': component_name,
                'error_type': error_type,
                'message': message
            })
    
    def _check_alerts(self, component_name: str, result: HealthCheckResult):
        """Check if alerts should be triggered"""
        if result.status in [HealthStatus.WARNING, HealthStatus.CRITICAL]:
            with self._alert_lock:
                for callback in self._alert_callbacks:
                    try:
                        callback(component_name, result.status, result.details)
                    except Exception as e:
                        logger.error(f"Error in alert callback: {str(e)}")
    
    def _get_component_status(self, component_name: str) -> Dict[str, Any]:
        """Get status for a specific component"""
        with self._components_lock:
            if component_name not in self._components:
                return {'error': f'Component {component_name} not found'}
            
            component = self._components[component_name]
            return {
                'name': component_name,
                'type': component['type'].value,
                'status': component['last_status'].value,
                'enabled': component['enabled'],
                'last_check': component['last_check'].isoformat() if component['last_check'] else None,
                'total_checks': component['total_checks'],
                'successful_checks': component['successful_checks'],
                'consecutive_failures': component['consecutive_failures']
            }
    
    def _get_overall_status(self) -> Dict[str, Any]:
        """Get overall system status"""
        summary = self.get_health_summary()
        
        return {
            'overall_status': summary.overall_status.value,
            'component_counts': {
                'healthy': summary.healthy_components,
                'warning': summary.warning_components,
                'critical': summary.critical_components,
                'unknown': summary.unknown_components
            },
            'uptime_seconds': summary.uptime_seconds,
            'error_rate': summary.error_rate,
            'performance_score': summary.performance_score,
            'last_check': summary.last_check_time.isoformat()
        }
    
    def _analyze_performance_metrics(self, component_name: str, metrics: List[Dict]) -> Dict[str, Any]:
        """Analyze performance metrics for a component"""
        if not metrics:
            return {
                'component': component_name,
                'total_checks': 0,
                'average_response_time_ms': 0.0,
                'min_response_time_ms': 0.0,
                'max_response_time_ms': 0.0,
                'response_time_trend': []
            }
        
        response_times = [m['response_time_ms'] for m in metrics]
        
        return {
            'component': component_name,
            'total_checks': len(metrics),
            'average_response_time_ms': statistics.mean(response_times),
            'min_response_time_ms': min(response_times),
            'max_response_time_ms': max(response_times),
            'median_response_time_ms': statistics.median(response_times),
            'response_time_percentiles': {
                'p95': statistics.quantiles(response_times, n=20)[18] if len(response_times) > 20 else max(response_times),
                'p99': statistics.quantiles(response_times, n=100)[98] if len(response_times) > 100 else max(response_times)
            },
            'response_time_trend': [
                {
                    'timestamp': m['timestamp'].isoformat(),
                    'response_time_ms': m['response_time_ms']
                }
                for m in metrics[-50:]  # Last 50 data points
            ]
        }
    
    def _calculate_error_rate(self) -> float:
        """Calculate overall error rate"""
        with self._error_lock:
            recent_errors = [e for e in self._error_history 
                           if e['timestamp'] >= datetime.now(timezone.utc) - timedelta(hours=1)]
        
        # Error rate as errors per hour
        return len(recent_errors)
    
    def _calculate_performance_score(self) -> float:
        """
        Calculate overall performance score (0.0 to 1.0, higher is better)
        """
        with self._components_lock:
            if not self._components:
                return 1.0
            
            total_score = 0.0
            component_count = 0
            
            for name, info in self._components.items():
                if info['total_checks'] > 0:
                    uptime_ratio = info['successful_checks'] / info['total_checks']
                    total_score += uptime_ratio
                    component_count += 1
            
            return total_score / component_count if component_count > 0 else 1.0
    
    def _cleanup_old_data(self):
        """Clean up old monitoring data"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=self.history_retention_hours)
        
        # Clean up health history
        with self._health_lock:
            self._health_history = deque(
                (result for result in self._health_history if result.timestamp >= cutoff_time),
                maxlen=self._health_history.maxlen
            )
        
        # Clean up performance metrics
        with self._performance_lock:
            for component_name in list(self._performance_metrics.keys()):
                metrics = self._performance_metrics[component_name]
                filtered_metrics = deque(
                    (m for m in metrics if m['timestamp'] >= cutoff_time),
                    maxlen=metrics.maxlen
                )
                self._performance_metrics[component_name] = filtered_metrics
        
        # Clean up error history
        with self._error_lock:
            self._error_history = deque(
                (error for error in self._error_history if error['timestamp'] >= cutoff_time),
                maxlen=self._error_history.maxlen
            )
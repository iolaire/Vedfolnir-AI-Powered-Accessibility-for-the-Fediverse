# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Admin System Health Notification Handler

This module provides real-time system health monitoring notifications for administrators
via the unified WebSocket notification system. It integrates with the existing system
monitor and provides admin-only access to sensitive system health information.

Requirements: 4.1, 4.2, 4.4, 4.5, 8.1, 8.3
"""

"""
⚠️  DEPRECATED: This file is deprecated and will be removed in a future version.
Please use the unified notification system instead:
- unified_notification_manager.py (core system)
- notification_service_adapters.py (service adapters)
- notification_helpers.py (helper functions)
- app/websocket/core/consolidated_handlers.py (WebSocket handling)

Migration guide: docs/implementation/notification-consolidation-final-summary.md
"""

import warnings
warnings.warn(
    "This notification system is deprecated. Use the unified notification system instead.",
    DeprecationWarning,
    stacklevel=2
)


import logging
import json
import threading
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass
from enum import Enum

from app.services.notification.manager.unified_manager import (
    UnifiedNotificationManager, AdminNotificationMessage, NotificationType,
    NotificationPriority, NotificationCategory
)
from system_monitor import SystemMonitor, SystemHealth, PerformanceMetrics, ResourceUsage
from models import UserRole
from app.core.database.core.database_manager import DatabaseManager

logger = logging.getLogger(__name__)


class HealthAlertType(Enum):
    """Types of system health alerts"""
    SYSTEM_DEGRADED = "system_degraded"
    RESOURCE_WARNING = "resource_warning"
    RESOURCE_CRITICAL = "resource_critical"
    DATABASE_ERROR = "database_error"
    REDIS_ERROR = "redis_error"
    PERFORMANCE_DEGRADED = "performance_degraded"
    STUCK_JOBS_DETECTED = "stuck_jobs_detected"
    HIGH_ERROR_RATE = "high_error_rate"
    SYSTEM_RECOVERED = "system_recovered"


@dataclass
class HealthThresholds:
    """System health monitoring thresholds"""
    cpu_warning: float = 70.0
    cpu_critical: float = 90.0
    memory_warning: float = 70.0
    memory_critical: float = 90.0
    disk_warning: float = 80.0
    disk_critical: float = 95.0
    error_rate_warning: float = 10.0
    error_rate_critical: float = 25.0
    response_time_warning: float = 5000.0  # milliseconds
    response_time_critical: float = 10000.0  # milliseconds
    stuck_job_threshold: int = 5  # number of stuck jobs


class AdminSystemHealthNotificationHandler:
    """
    Admin system health notification handler for real-time monitoring
    
    Provides real-time system health monitoring notifications via WebSocket,
    performance metrics and resource usage alerts, critical system event notifications,
    and admin-only access to sensitive system health information.
    """
    
    def __init__(self, notification_manager: UnifiedNotificationManager,
                 system_monitor: SystemMonitor, db_manager: DatabaseManager,
                 monitoring_interval: int = 60, alert_cooldown: int = 300):
        """
        Initialize admin system health notification handler
        
        Args:
            notification_manager: Unified notification manager instance
            system_monitor: System monitor instance
            db_manager: Database manager instance
            monitoring_interval: Health check interval in seconds (default: 60)
            alert_cooldown: Cooldown period between similar alerts in seconds (default: 300)
        """
        self.notification_manager = notification_manager
        self.system_monitor = system_monitor
        self.db_manager = db_manager
        self.monitoring_interval = monitoring_interval
        self.alert_cooldown = alert_cooldown
        
        # Health monitoring thresholds
        self.thresholds = HealthThresholds()
        
        # Alert tracking to prevent spam
        self._alert_history = {}  # alert_type -> last_sent_timestamp
        self._current_alerts = set()  # active alert types
        self._previous_health_status = None
        
        # Monitoring thread control
        self._monitoring_thread = None
        self._stop_monitoring = threading.Event()
        self._monitoring_active = False
        
        # Statistics tracking
        self._stats = {
            'alerts_sent': 0,
            'health_checks_performed': 0,
            'critical_alerts': 0,
            'warning_alerts': 0,
            'recovery_notifications': 0
        }
        
        logger.info("Admin System Health Notification Handler initialized")
    
    def start_monitoring(self) -> bool:
        """
        Start real-time system health monitoring
        
        Returns:
            True if monitoring started successfully, False otherwise
        """
        try:
            if self._monitoring_active:
                logger.warning("System health monitoring is already active")
                return True
            
            self._stop_monitoring.clear()
            self._monitoring_thread = threading.Thread(
                target=self._monitoring_loop,
                name="SystemHealthMonitoring",
                daemon=True
            )
            self._monitoring_thread.start()
            self._monitoring_active = True
            
            # Send startup notification to admins
            self._send_system_notification(
                alert_type=HealthAlertType.SYSTEM_RECOVERED,
                title="System Health Monitoring Started",
                message="Real-time system health monitoring has been activated",
                priority=NotificationPriority.NORMAL,
                system_health_data={
                    'monitoring_interval': self.monitoring_interval,
                    'alert_cooldown': self.alert_cooldown,
                    'thresholds': {
                        'cpu_warning': self.thresholds.cpu_warning,
                        'memory_warning': self.thresholds.memory_warning,
                        'disk_warning': self.thresholds.disk_warning
                    }
                }
            )
            
            logger.info("System health monitoring started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start system health monitoring: {e}")
            return False
    
    def stop_monitoring(self) -> bool:
        """
        Stop real-time system health monitoring
        
        Returns:
            True if monitoring stopped successfully, False otherwise
        """
        try:
            if not self._monitoring_active:
                logger.warning("System health monitoring is not active")
                return True
            
            self._stop_monitoring.set()
            
            if self._monitoring_thread and self._monitoring_thread.is_alive():
                self._monitoring_thread.join(timeout=10)
            
            self._monitoring_active = False
            
            # Send shutdown notification to admins
            self._send_system_notification(
                alert_type=HealthAlertType.SYSTEM_DEGRADED,
                title="System Health Monitoring Stopped",
                message="Real-time system health monitoring has been deactivated",
                priority=NotificationPriority.HIGH,
                system_health_data={
                    'reason': 'manual_stop',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            )
            
            logger.info("System health monitoring stopped")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop system health monitoring: {e}")
            return False
    
    def send_immediate_health_alert(self, force_check: bool = True) -> Dict[str, Any]:
        """
        Send immediate system health alert to admins
        
        Args:
            force_check: Whether to force a new health check
            
        Returns:
            Dictionary containing alert results
        """
        try:
            if force_check:
                # Perform immediate health check
                health = self.system_monitor.get_system_health()
                performance = self.system_monitor.get_performance_metrics()
                resources = self.system_monitor.check_resource_usage()
                
                # Check for immediate issues
                alerts_sent = self._check_and_send_alerts(health, performance, resources)
                
                return {
                    'success': True,
                    'alerts_sent': len(alerts_sent),
                    'alert_types': alerts_sent,
                    'health_status': health.status,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            else:
                # Send current status notification
                self._send_system_notification(
                    alert_type=HealthAlertType.SYSTEM_RECOVERED,
                    title="System Health Status Request",
                    message="Current system health status requested by administrator",
                    priority=NotificationPriority.NORMAL,
                    system_health_data={
                        'request_type': 'manual_status_check',
                        'monitoring_active': self._monitoring_active,
                        'current_alerts': list(self._current_alerts)
                    }
                )
                
                return {
                    'success': True,
                    'alerts_sent': 1,
                    'alert_types': ['status_request'],
                    'monitoring_active': self._monitoring_active,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                
        except Exception as e:
            logger.error(f"Failed to send immediate health alert: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def update_thresholds(self, new_thresholds: Dict[str, float]) -> bool:
        """
        Update health monitoring thresholds
        
        Args:
            new_thresholds: Dictionary of threshold values to update
            
        Returns:
            True if thresholds updated successfully, False otherwise
        """
        try:
            # Validate threshold values
            valid_thresholds = {
                'cpu_warning', 'cpu_critical', 'memory_warning', 'memory_critical',
                'disk_warning', 'disk_critical', 'error_rate_warning', 'error_rate_critical',
                'response_time_warning', 'response_time_critical', 'stuck_job_threshold'
            }
            
            for key, value in new_thresholds.items():
                if key not in valid_thresholds:
                    logger.warning(f"Invalid threshold key: {key}")
                    continue
                
                if not isinstance(value, (int, float)) or value < 0:
                    logger.warning(f"Invalid threshold value for {key}: {value}")
                    continue
                
                # Update threshold
                setattr(self.thresholds, key, float(value))
            
            # Send notification about threshold update
            self._send_system_notification(
                alert_type=HealthAlertType.SYSTEM_RECOVERED,
                title="Health Monitoring Thresholds Updated",
                message="System health monitoring thresholds have been updated by administrator",
                priority=NotificationPriority.NORMAL,
                system_health_data={
                    'updated_thresholds': new_thresholds,
                    'current_thresholds': {
                        'cpu_warning': self.thresholds.cpu_warning,
                        'cpu_critical': self.thresholds.cpu_critical,
                        'memory_warning': self.thresholds.memory_warning,
                        'memory_critical': self.thresholds.memory_critical,
                        'disk_warning': self.thresholds.disk_warning,
                        'disk_critical': self.thresholds.disk_critical
                    }
                }
            )
            
            logger.info(f"Updated health monitoring thresholds: {new_thresholds}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update thresholds: {e}")
            return False
    
    def get_monitoring_stats(self) -> Dict[str, Any]:
        """
        Get system health monitoring statistics
        
        Returns:
            Dictionary containing monitoring statistics
        """
        try:
            return {
                'monitoring_active': self._monitoring_active,
                'monitoring_interval': self.monitoring_interval,
                'alert_cooldown': self.alert_cooldown,
                'current_alerts': list(self._current_alerts),
                'alert_history_count': len(self._alert_history),
                'statistics': self._stats.copy(),
                'thresholds': {
                    'cpu_warning': self.thresholds.cpu_warning,
                    'cpu_critical': self.thresholds.cpu_critical,
                    'memory_warning': self.thresholds.memory_warning,
                    'memory_critical': self.thresholds.memory_critical,
                    'disk_warning': self.thresholds.disk_warning,
                    'disk_critical': self.thresholds.disk_critical,
                    'error_rate_warning': self.thresholds.error_rate_warning,
                    'error_rate_critical': self.thresholds.error_rate_critical
                },
                'last_health_status': self._previous_health_status,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get monitoring stats: {e}")
            return {'error': str(e)}
    
    def _monitoring_loop(self) -> None:
        """Main monitoring loop running in background thread"""
        logger.info("System health monitoring loop started")
        
        while not self._stop_monitoring.is_set():
            try:
                # Perform health checks
                health = self.system_monitor.get_system_health()
                performance = self.system_monitor.get_performance_metrics()
                resources = self.system_monitor.check_resource_usage()
                
                self._stats['health_checks_performed'] += 1
                
                # Check for alerts and send notifications
                alerts_sent = self._check_and_send_alerts(health, performance, resources)
                
                # Check for system recovery
                self._check_system_recovery(health)
                
                # Update previous health status
                self._previous_health_status = health.status
                
                # Wait for next monitoring cycle
                self._stop_monitoring.wait(self.monitoring_interval)
                
            except Exception as e:
                logger.error(f"Error in system health monitoring loop: {e}")
                # Continue monitoring even if there's an error
                self._stop_monitoring.wait(self.monitoring_interval)
        
        logger.info("System health monitoring loop stopped")
    
    def _check_and_send_alerts(self, health: SystemHealth, 
                             performance: PerformanceMetrics, 
                             resources: ResourceUsage) -> List[str]:
        """
        Check system health and send alerts if necessary
        
        Args:
            health: Current system health status
            performance: Current performance metrics
            resources: Current resource usage
            
        Returns:
            List of alert types that were sent
        """
        alerts_sent = []
        
        try:
            # Check CPU usage
            if resources.cpu_percent >= self.thresholds.cpu_critical:
                if self._should_send_alert(HealthAlertType.RESOURCE_CRITICAL):
                    self._send_resource_alert(
                        HealthAlertType.RESOURCE_CRITICAL,
                        "Critical CPU Usage",
                        f"CPU usage is critically high: {resources.cpu_percent:.1f}%",
                        NotificationPriority.CRITICAL,
                        {'resource': 'cpu', 'usage': resources.cpu_percent, 'threshold': self.thresholds.cpu_critical}
                    )
                    alerts_sent.append('cpu_critical')
            elif resources.cpu_percent >= self.thresholds.cpu_warning:
                if self._should_send_alert(HealthAlertType.RESOURCE_WARNING):
                    self._send_resource_alert(
                        HealthAlertType.RESOURCE_WARNING,
                        "High CPU Usage",
                        f"CPU usage is high: {resources.cpu_percent:.1f}%",
                        NotificationPriority.HIGH,
                        {'resource': 'cpu', 'usage': resources.cpu_percent, 'threshold': self.thresholds.cpu_warning}
                    )
                    alerts_sent.append('cpu_warning')
            
            # Check memory usage
            if resources.memory_percent >= self.thresholds.memory_critical:
                if self._should_send_alert(HealthAlertType.RESOURCE_CRITICAL):
                    self._send_resource_alert(
                        HealthAlertType.RESOURCE_CRITICAL,
                        "Critical Memory Usage",
                        f"Memory usage is critically high: {resources.memory_percent:.1f}%",
                        NotificationPriority.CRITICAL,
                        {'resource': 'memory', 'usage': resources.memory_percent, 'threshold': self.thresholds.memory_critical}
                    )
                    alerts_sent.append('memory_critical')
            elif resources.memory_percent >= self.thresholds.memory_warning:
                if self._should_send_alert(HealthAlertType.RESOURCE_WARNING):
                    self._send_resource_alert(
                        HealthAlertType.RESOURCE_WARNING,
                        "High Memory Usage",
                        f"Memory usage is high: {resources.memory_percent:.1f}%",
                        NotificationPriority.HIGH,
                        {'resource': 'memory', 'usage': resources.memory_percent, 'threshold': self.thresholds.memory_warning}
                    )
                    alerts_sent.append('memory_warning')
            
            # Check disk usage
            if resources.disk_percent >= self.thresholds.disk_critical:
                if self._should_send_alert(HealthAlertType.RESOURCE_CRITICAL):
                    self._send_resource_alert(
                        HealthAlertType.RESOURCE_CRITICAL,
                        "Critical Disk Usage",
                        f"Disk usage is critically high: {resources.disk_percent:.1f}%",
                        NotificationPriority.CRITICAL,
                        {'resource': 'disk', 'usage': resources.disk_percent, 'threshold': self.thresholds.disk_critical}
                    )
                    alerts_sent.append('disk_critical')
            elif resources.disk_percent >= self.thresholds.disk_warning:
                if self._should_send_alert(HealthAlertType.RESOURCE_WARNING):
                    self._send_resource_alert(
                        HealthAlertType.RESOURCE_WARNING,
                        "High Disk Usage",
                        f"Disk usage is high: {resources.disk_percent:.1f}%",
                        NotificationPriority.HIGH,
                        {'resource': 'disk', 'usage': resources.disk_percent, 'threshold': self.thresholds.disk_warning}
                    )
                    alerts_sent.append('disk_warning')
            
            # Check database status
            if health.database_status == 'error':
                if self._should_send_alert(HealthAlertType.DATABASE_ERROR):
                    self._send_system_notification(
                        HealthAlertType.DATABASE_ERROR,
                        "Database Connection Error",
                        "Database connection is not available",
                        NotificationPriority.CRITICAL,
                        {'component': 'database', 'status': health.database_status}
                    )
                    alerts_sent.append('database_error')
            
            # Check Redis status
            if health.redis_status == 'error':
                if self._should_send_alert(HealthAlertType.REDIS_ERROR):
                    self._send_system_notification(
                        HealthAlertType.REDIS_ERROR,
                        "Redis Connection Error",
                        "Redis connection is not available",
                        NotificationPriority.HIGH,
                        {'component': 'redis', 'status': health.redis_status}
                    )
                    alerts_sent.append('redis_error')
            
            # Check error rate
            if performance.error_rate >= self.thresholds.error_rate_critical:
                if self._should_send_alert(HealthAlertType.HIGH_ERROR_RATE):
                    self._send_system_notification(
                        HealthAlertType.HIGH_ERROR_RATE,
                        "Critical Error Rate",
                        f"System error rate is critically high: {performance.error_rate:.1f}%",
                        NotificationPriority.CRITICAL,
                        {'error_rate': performance.error_rate, 'threshold': self.thresholds.error_rate_critical}
                    )
                    alerts_sent.append('error_rate_critical')
            elif performance.error_rate >= self.thresholds.error_rate_warning:
                if self._should_send_alert(HealthAlertType.HIGH_ERROR_RATE):
                    self._send_system_notification(
                        HealthAlertType.HIGH_ERROR_RATE,
                        "High Error Rate",
                        f"System error rate is high: {performance.error_rate:.1f}%",
                        NotificationPriority.HIGH,
                        {'error_rate': performance.error_rate, 'threshold': self.thresholds.error_rate_warning}
                    )
                    alerts_sent.append('error_rate_warning')
            
            # Check for stuck jobs
            stuck_jobs = self.system_monitor.detect_stuck_jobs()
            if len(stuck_jobs) >= self.thresholds.stuck_job_threshold:
                if self._should_send_alert(HealthAlertType.STUCK_JOBS_DETECTED):
                    self._send_system_notification(
                        HealthAlertType.STUCK_JOBS_DETECTED,
                        "Stuck Jobs Detected",
                        f"Detected {len(stuck_jobs)} stuck jobs that may need attention",
                        NotificationPriority.HIGH,
                        {'stuck_jobs_count': len(stuck_jobs), 'stuck_job_ids': stuck_jobs[:5]}  # Limit to first 5 IDs
                    )
                    alerts_sent.append('stuck_jobs')
            
            # Check overall system health degradation
            if health.status in ['warning', 'critical'] and self._previous_health_status != health.status:
                if self._should_send_alert(HealthAlertType.SYSTEM_DEGRADED):
                    priority = NotificationPriority.CRITICAL if health.status == 'critical' else NotificationPriority.HIGH
                    self._send_system_notification(
                        HealthAlertType.SYSTEM_DEGRADED,
                        f"System Health {health.status.title()}",
                        f"Overall system health status has changed to {health.status}",
                        priority,
                        {
                            'previous_status': self._previous_health_status,
                            'current_status': health.status,
                            'health_data': health.to_dict()
                        }
                    )
                    alerts_sent.append('system_degraded')
            
            return alerts_sent
            
        except Exception as e:
            logger.error(f"Error checking and sending alerts: {e}")
            return alerts_sent
    
    def _check_system_recovery(self, health: SystemHealth) -> None:
        """
        Check if system has recovered from previous issues
        
        Args:
            health: Current system health status
        """
        try:
            # Check if system has recovered to healthy status
            if (health.status == 'healthy' and 
                self._previous_health_status in ['warning', 'critical'] and
                len(self._current_alerts) > 0):
                
                # Send recovery notification
                self._send_system_notification(
                    HealthAlertType.SYSTEM_RECOVERED,
                    "System Health Recovered",
                    f"System health has recovered from {self._previous_health_status} to healthy status",
                    NotificationPriority.NORMAL,
                    {
                        'previous_status': self._previous_health_status,
                        'current_status': health.status,
                        'recovered_alerts': list(self._current_alerts),
                        'recovery_time': datetime.now(timezone.utc).isoformat()
                    }
                )
                
                # Clear current alerts
                self._current_alerts.clear()
                self._stats['recovery_notifications'] += 1
                
        except Exception as e:
            logger.error(f"Error checking system recovery: {e}")
    
    def _should_send_alert(self, alert_type: HealthAlertType) -> bool:
        """
        Check if alert should be sent based on cooldown period
        
        Args:
            alert_type: Type of alert to check
            
        Returns:
            True if alert should be sent, False otherwise
        """
        try:
            current_time = time.time()
            last_sent = self._alert_history.get(alert_type.value, 0)
            
            # Check cooldown period
            if current_time - last_sent >= self.alert_cooldown:
                self._alert_history[alert_type.value] = current_time
                self._current_alerts.add(alert_type.value)
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking alert cooldown: {e}")
            return False
    
    def _send_system_notification(self, alert_type: HealthAlertType, title: str, 
                                message: str, priority: NotificationPriority,
                                system_health_data: Dict[str, Any]) -> bool:
        """
        Send system health notification to admin users
        
        Args:
            alert_type: Type of health alert
            title: Notification title
            message: Notification message
            priority: Notification priority
            system_health_data: System health data to include
            
        Returns:
            True if notification sent successfully, False otherwise
        """
        try:
            # Create admin notification message
            notification = AdminNotificationMessage(
                id=f"health_{alert_type.value}_{int(time.time())}",
                type=NotificationType.WARNING if priority == NotificationPriority.HIGH else NotificationType.ERROR if priority == NotificationPriority.CRITICAL else NotificationType.INFO,
                title=title,
                message=message,
                priority=priority,
                category=NotificationCategory.ADMIN,
                admin_only=True,
                system_health_data=system_health_data,
                requires_admin_action=(priority == NotificationPriority.CRITICAL),
                data={
                    'alert_type': alert_type.value,
                    'component': 'system_health_monitor',
                    'monitoring_interval': self.monitoring_interval,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            )
            
            # Send notification via unified notification manager
            success = self.notification_manager.send_admin_notification(notification)
            
            if success:
                self._stats['alerts_sent'] += 1
                if priority == NotificationPriority.CRITICAL:
                    self._stats['critical_alerts'] += 1
                elif priority == NotificationPriority.HIGH:
                    self._stats['warning_alerts'] += 1
                
                logger.info(f"Sent system health notification: {alert_type.value}")
            else:
                logger.error(f"Failed to send system health notification: {alert_type.value}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending system notification: {e}")
            return False
    
    def _send_resource_alert(self, alert_type: HealthAlertType, title: str,
                           message: str, priority: NotificationPriority,
                           resource_data: Dict[str, Any]) -> bool:
        """
        Send resource usage alert to admin users
        
        Args:
            alert_type: Type of resource alert
            title: Notification title
            message: Notification message
            priority: Notification priority
            resource_data: Resource usage data to include
            
        Returns:
            True if notification sent successfully, False otherwise
        """
        try:
            # Enhance resource data with additional context
            enhanced_data = {
                **resource_data,
                'alert_type': alert_type.value,
                'monitoring_active': self._monitoring_active,
                'recommendations': self._get_resource_recommendations(resource_data['resource'], resource_data['usage'])
            }
            
            return self._send_system_notification(
                alert_type=alert_type,
                title=title,
                message=message,
                priority=priority,
                system_health_data=enhanced_data
            )
            
        except Exception as e:
            logger.error(f"Error sending resource alert: {e}")
            return False
    
    def _get_resource_recommendations(self, resource: str, usage: float) -> List[str]:
        """
        Get recommendations for resource usage issues
        
        Args:
            resource: Resource type (cpu, memory, disk)
            usage: Current usage percentage
            
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        try:
            if resource == 'cpu':
                if usage >= 90:
                    recommendations.extend([
                        "Check for runaway processes or stuck jobs",
                        "Consider scaling up CPU resources",
                        "Review recent system changes"
                    ])
                elif usage >= 70:
                    recommendations.extend([
                        "Monitor CPU usage trends",
                        "Consider optimizing resource-intensive operations"
                    ])
            
            elif resource == 'memory':
                if usage >= 90:
                    recommendations.extend([
                        "Check for memory leaks in applications",
                        "Consider increasing available memory",
                        "Review memory-intensive processes"
                    ])
                elif usage >= 70:
                    recommendations.extend([
                        "Monitor memory usage patterns",
                        "Consider memory optimization"
                    ])
            
            elif resource == 'disk':
                if usage >= 95:
                    recommendations.extend([
                        "Immediate cleanup required - system may become unstable",
                        "Remove old logs and temporary files",
                        "Consider expanding disk space"
                    ])
                elif usage >= 80:
                    recommendations.extend([
                        "Schedule disk cleanup operations",
                        "Monitor disk usage growth trends"
                    ])
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating resource recommendations: {e}")
            return ["Contact system administrator for assistance"]
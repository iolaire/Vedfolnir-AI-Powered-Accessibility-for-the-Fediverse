# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
RQ Monitoring Service

Provides comprehensive monitoring and alerting for Redis Queue system,
including performance metrics tracking, health checks, and alert generation.
"""

import logging
import threading
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum

from app.core.database.core.database_manager import DatabaseManager
from app.core.security.core.security_utils import sanitize_for_log
from models import CaptionGenerationTask, TaskStatus

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class PerformanceMetrics:
    """Performance metrics data structure"""
    timestamp: datetime
    
    # Task processing metrics
    tasks_completed_1h: int = 0
    tasks_failed_1h: int = 0
    tasks_pending: int = 0
    tasks_processing: int = 0
    
    # Processing time metrics
    avg_processing_time: float = 0.0
    min_processing_time: float = 0.0
    max_processing_time: float = 0.0
    p95_processing_time: float = 0.0
    
    # Success rate metrics
    success_rate_1h: float = 0.0
    success_rate_24h: float = 0.0
    
    # Queue metrics
    queue_depths: Dict[str, int] = None
    queue_processing_rates: Dict[str, float] = None
    
    # Worker metrics
    active_workers: int = 0
    worker_utilization: float = 0.0
    
    # Redis metrics
    redis_memory_usage: int = 0
    redis_connection_count: int = 0
    redis_response_time: float = 0.0
    
    def __post_init__(self):
        if self.queue_depths is None:
            self.queue_depths = {}
        if self.queue_processing_rates is None:
            self.queue_processing_rates = {}


@dataclass
class Alert:
    """Alert data structure"""
    id: str
    severity: AlertSeverity
    title: str
    message: str
    timestamp: datetime
    component: str
    metric_name: str
    metric_value: Any
    threshold: Any
    acknowledged: bool = False
    resolved: bool = False


class RQMonitoringService:
    """Comprehensive monitoring service for RQ system"""
    
    def __init__(self, db_manager: DatabaseManager, rq_queue_manager=None):
        """
        Initialize RQ monitoring service
        
        Args:
            db_manager: Database manager instance
            rq_queue_manager: RQ queue manager instance (optional)
        """
        self.db_manager = db_manager
        self.rq_queue_manager = rq_queue_manager
        
        # Monitoring state
        self._monitoring_active = False
        self._monitoring_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # Metrics storage
        self._metrics_history: List[PerformanceMetrics] = []
        self._max_history_size = 1440  # 24 hours of minute-by-minute data
        
        # Alert management
        self._active_alerts: Dict[str, Alert] = {}
        self._alert_callbacks: List[Callable[[Alert], None]] = []
        
        # Thresholds for alerting
        self._thresholds = {
            'queue_backlog_warning': 50,
            'queue_backlog_critical': 100,
            'success_rate_warning': 85.0,
            'success_rate_critical': 70.0,
            'processing_time_warning': 300.0,  # 5 minutes
            'processing_time_critical': 600.0,  # 10 minutes
            'redis_memory_warning': 80.0,  # 80% of max memory
            'redis_memory_critical': 95.0,  # 95% of max memory
            'worker_failure_threshold': 3,
            'redis_response_time_warning': 1.0,  # 1 second
            'redis_response_time_critical': 5.0   # 5 seconds
        }
        
        # Monitoring intervals
        self._monitoring_interval = 60  # 1 minute
        self._metrics_collection_interval = 60  # 1 minute
        
    def start_monitoring(self) -> None:
        """Start the monitoring service"""
        if self._monitoring_active:
            logger.warning("RQ monitoring service is already active")
            return
        
        self._monitoring_active = True
        self._stop_event.clear()
        
        self._monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            name="RQMonitoringService",
            daemon=True
        )
        self._monitoring_thread.start()
        
        logger.info("RQ monitoring service started")
    
    def stop_monitoring(self) -> None:
        """Stop the monitoring service"""
        if not self._monitoring_active:
            return
        
        self._monitoring_active = False
        self._stop_event.set()
        
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            self._monitoring_thread.join(timeout=10)
        
        logger.info("RQ monitoring service stopped")
    
    def _monitoring_loop(self) -> None:
        """Main monitoring loop"""
        logger.info("RQ monitoring loop started")
        
        while not self._stop_event.is_set():
            try:
                # Collect performance metrics
                metrics = self._collect_performance_metrics()
                
                # Store metrics in history
                self._store_metrics(metrics)
                
                # Check for alerts
                self._check_alerts(metrics)
                
                # Clean up old metrics
                self._cleanup_old_metrics()
                
            except Exception as e:
                logger.error(f"Error in RQ monitoring loop: {sanitize_for_log(str(e))}")
            
            # Wait for next iteration
            self._stop_event.wait(self._monitoring_interval)
        
        logger.info("RQ monitoring loop stopped")
    
    def _collect_performance_metrics(self) -> PerformanceMetrics:
        """Collect current performance metrics"""
        now = datetime.now(timezone.utc)
        metrics = PerformanceMetrics(timestamp=now)
        
        try:
            # Collect database task metrics
            self._collect_database_metrics(metrics)
            
            # Collect RQ queue metrics if available
            if self.rq_queue_manager:
                self._collect_rq_metrics(metrics)
            
            # Collect Redis metrics if available
            self._collect_redis_metrics(metrics)
            
        except Exception as e:
            logger.error(f"Error collecting performance metrics: {sanitize_for_log(str(e))}")
        
        return metrics
    
    def _collect_database_metrics(self, metrics: PerformanceMetrics) -> None:
        """Collect metrics from database"""
        session = self.db_manager.get_session()
        try:
            # Time ranges
            one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
            twenty_four_hours_ago = datetime.now(timezone.utc) - timedelta(hours=24)
            
            # Task counts by status
            metrics.tasks_pending = session.query(CaptionGenerationTask).filter_by(
                status=TaskStatus.QUEUED
            ).count()
            
            metrics.tasks_processing = session.query(CaptionGenerationTask).filter_by(
                status=TaskStatus.RUNNING
            ).count()
            
            # Completed tasks in last hour
            metrics.tasks_completed_1h = session.query(CaptionGenerationTask).filter(
                CaptionGenerationTask.status == TaskStatus.COMPLETED,
                CaptionGenerationTask.completed_at >= one_hour_ago
            ).count()
            
            # Failed tasks in last hour
            metrics.tasks_failed_1h = session.query(CaptionGenerationTask).filter(
                CaptionGenerationTask.status == TaskStatus.FAILED,
                CaptionGenerationTask.completed_at >= one_hour_ago
            ).count()
            
            # Calculate success rates
            total_1h = metrics.tasks_completed_1h + metrics.tasks_failed_1h
            if total_1h > 0:
                metrics.success_rate_1h = (metrics.tasks_completed_1h / total_1h) * 100
            
            # 24-hour success rate
            completed_24h = session.query(CaptionGenerationTask).filter(
                CaptionGenerationTask.status == TaskStatus.COMPLETED,
                CaptionGenerationTask.completed_at >= twenty_four_hours_ago
            ).count()
            
            failed_24h = session.query(CaptionGenerationTask).filter(
                CaptionGenerationTask.status == TaskStatus.FAILED,
                CaptionGenerationTask.completed_at >= twenty_four_hours_ago
            ).count()
            
            total_24h = completed_24h + failed_24h
            if total_24h > 0:
                metrics.success_rate_24h = (completed_24h / total_24h) * 100
            
            # Processing time metrics
            self._calculate_processing_time_metrics(session, metrics, one_hour_ago)
            
        finally:
            session.close()
    
    def _calculate_processing_time_metrics(self, session, metrics: PerformanceMetrics, since: datetime) -> None:
        """Calculate processing time metrics"""
        completed_tasks = session.query(CaptionGenerationTask).filter(
            CaptionGenerationTask.status == TaskStatus.COMPLETED,
            CaptionGenerationTask.completed_at >= since,
            CaptionGenerationTask.started_at.isnot(None)
        ).all()
        
        if not completed_tasks:
            return
        
        processing_times = []
        for task in completed_tasks:
            if task.started_at and task.completed_at:
                duration = (task.completed_at - task.started_at).total_seconds()
                processing_times.append(duration)
        
        if processing_times:
            processing_times.sort()
            metrics.avg_processing_time = sum(processing_times) / len(processing_times)
            metrics.min_processing_time = min(processing_times)
            metrics.max_processing_time = max(processing_times)
            
            # Calculate 95th percentile
            p95_index = int(0.95 * len(processing_times))
            metrics.p95_processing_time = processing_times[p95_index] if p95_index < len(processing_times) else processing_times[-1]
    
    def _collect_rq_metrics(self, metrics: PerformanceMetrics) -> None:
        """Collect metrics from RQ queue manager"""
        try:
            if not self.rq_queue_manager:
                return
            
            # Get queue statistics
            queue_stats = self.rq_queue_manager.get_queue_stats()
            
            # Extract queue depths
            if queue_stats.get('queues'):
                for queue_name, queue_data in queue_stats['queues'].items():
                    metrics.queue_depths[queue_name] = queue_data.get('pending', 0)
            
            # Get health status
            health_status = self.rq_queue_manager.get_health_status()
            
            # Worker information (if available)
            # Note: This would need to be implemented in the RQ worker manager
            
        except Exception as e:
            logger.error(f"Error collecting RQ metrics: {sanitize_for_log(str(e))}")
    
    def _collect_redis_metrics(self, metrics: PerformanceMetrics) -> None:
        """Collect Redis performance metrics"""
        try:
            if not self.rq_queue_manager or not hasattr(self.rq_queue_manager, 'redis_connection'):
                return
            
            redis_conn = self.rq_queue_manager.redis_connection
            if not redis_conn:
                return
            
            # Measure Redis response time
            start_time = time.time()
            redis_conn.ping()
            metrics.redis_response_time = time.time() - start_time
            
            # Get Redis info
            redis_info = redis_conn.info()
            
            # Memory usage
            used_memory = redis_info.get('used_memory', 0)
            max_memory = redis_info.get('maxmemory', 0)
            if max_memory > 0:
                metrics.redis_memory_usage = (used_memory / max_memory) * 100
            
            # Connection count
            metrics.redis_connection_count = redis_info.get('connected_clients', 0)
            
        except Exception as e:
            logger.error(f"Error collecting Redis metrics: {sanitize_for_log(str(e))}")
    
    def _store_metrics(self, metrics: PerformanceMetrics) -> None:
        """Store metrics in history"""
        self._metrics_history.append(metrics)
        
        # Keep only recent metrics
        if len(self._metrics_history) > self._max_history_size:
            self._metrics_history = self._metrics_history[-self._max_history_size:]
    
    def _cleanup_old_metrics(self) -> None:
        """Clean up old metrics from history"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
        
        self._metrics_history = [
            m for m in self._metrics_history 
            if m.timestamp > cutoff_time
        ]
    
    def _check_alerts(self, metrics: PerformanceMetrics) -> None:
        """Check metrics against thresholds and generate alerts"""
        # Check queue backlog
        self._check_queue_backlog_alerts(metrics)
        
        # Check success rate
        self._check_success_rate_alerts(metrics)
        
        # Check processing time
        self._check_processing_time_alerts(metrics)
        
        # Check Redis metrics
        self._check_redis_alerts(metrics)
        
        # Check worker health
        self._check_worker_health_alerts(metrics)
    
    def _check_queue_backlog_alerts(self, metrics: PerformanceMetrics) -> None:
        """Check for queue backlog alerts"""
        total_pending = sum(metrics.queue_depths.values()) if metrics.queue_depths else metrics.tasks_pending
        
        if total_pending >= self._thresholds['queue_backlog_critical']:
            self._create_alert(
                'queue_backlog_critical',
                AlertSeverity.CRITICAL,
                'Critical Queue Backlog',
                f'Queue backlog has reached critical level: {total_pending} tasks pending',
                'queue',
                'total_pending',
                total_pending,
                self._thresholds['queue_backlog_critical']
            )
        elif total_pending >= self._thresholds['queue_backlog_warning']:
            self._create_alert(
                'queue_backlog_warning',
                AlertSeverity.WARNING,
                'High Queue Backlog',
                f'Queue backlog is high: {total_pending} tasks pending',
                'queue',
                'total_pending',
                total_pending,
                self._thresholds['queue_backlog_warning']
            )
        else:
            # Resolve existing backlog alerts
            self._resolve_alert('queue_backlog_critical')
            self._resolve_alert('queue_backlog_warning')
    
    def _check_success_rate_alerts(self, metrics: PerformanceMetrics) -> None:
        """Check for success rate alerts"""
        success_rate = metrics.success_rate_1h
        
        if success_rate > 0:  # Only alert if we have data
            if success_rate <= self._thresholds['success_rate_critical']:
                self._create_alert(
                    'success_rate_critical',
                    AlertSeverity.CRITICAL,
                    'Critical Success Rate',
                    f'Task success rate is critically low: {success_rate:.1f}%',
                    'processing',
                    'success_rate_1h',
                    success_rate,
                    self._thresholds['success_rate_critical']
                )
            elif success_rate <= self._thresholds['success_rate_warning']:
                self._create_alert(
                    'success_rate_warning',
                    AlertSeverity.WARNING,
                    'Low Success Rate',
                    f'Task success rate is low: {success_rate:.1f}%',
                    'processing',
                    'success_rate_1h',
                    success_rate,
                    self._thresholds['success_rate_warning']
                )
            else:
                # Resolve existing success rate alerts
                self._resolve_alert('success_rate_critical')
                self._resolve_alert('success_rate_warning')
    
    def _check_processing_time_alerts(self, metrics: PerformanceMetrics) -> None:
        """Check for processing time alerts"""
        avg_time = metrics.avg_processing_time
        p95_time = metrics.p95_processing_time
        
        if avg_time > 0:  # Only alert if we have data
            if avg_time >= self._thresholds['processing_time_critical'] or p95_time >= self._thresholds['processing_time_critical']:
                self._create_alert(
                    'processing_time_critical',
                    AlertSeverity.CRITICAL,
                    'Critical Processing Time',
                    f'Task processing time is critically high: avg {avg_time:.1f}s, p95 {p95_time:.1f}s',
                    'processing',
                    'avg_processing_time',
                    avg_time,
                    self._thresholds['processing_time_critical']
                )
            elif avg_time >= self._thresholds['processing_time_warning'] or p95_time >= self._thresholds['processing_time_warning']:
                self._create_alert(
                    'processing_time_warning',
                    AlertSeverity.WARNING,
                    'High Processing Time',
                    f'Task processing time is high: avg {avg_time:.1f}s, p95 {p95_time:.1f}s',
                    'processing',
                    'avg_processing_time',
                    avg_time,
                    self._thresholds['processing_time_warning']
                )
            else:
                # Resolve existing processing time alerts
                self._resolve_alert('processing_time_critical')
                self._resolve_alert('processing_time_warning')
    
    def _check_redis_alerts(self, metrics: PerformanceMetrics) -> None:
        """Check for Redis-related alerts"""
        # Memory usage alerts
        if metrics.redis_memory_usage > 0:
            if metrics.redis_memory_usage >= self._thresholds['redis_memory_critical']:
                self._create_alert(
                    'redis_memory_critical',
                    AlertSeverity.CRITICAL,
                    'Critical Redis Memory Usage',
                    f'Redis memory usage is critically high: {metrics.redis_memory_usage:.1f}%',
                    'redis',
                    'memory_usage',
                    metrics.redis_memory_usage,
                    self._thresholds['redis_memory_critical']
                )
            elif metrics.redis_memory_usage >= self._thresholds['redis_memory_warning']:
                self._create_alert(
                    'redis_memory_warning',
                    AlertSeverity.WARNING,
                    'High Redis Memory Usage',
                    f'Redis memory usage is high: {metrics.redis_memory_usage:.1f}%',
                    'redis',
                    'memory_usage',
                    metrics.redis_memory_usage,
                    self._thresholds['redis_memory_warning']
                )
            else:
                self._resolve_alert('redis_memory_critical')
                self._resolve_alert('redis_memory_warning')
        
        # Response time alerts
        if metrics.redis_response_time > 0:
            if metrics.redis_response_time >= self._thresholds['redis_response_time_critical']:
                self._create_alert(
                    'redis_response_time_critical',
                    AlertSeverity.CRITICAL,
                    'Critical Redis Response Time',
                    f'Redis response time is critically high: {metrics.redis_response_time:.2f}s',
                    'redis',
                    'response_time',
                    metrics.redis_response_time,
                    self._thresholds['redis_response_time_critical']
                )
            elif metrics.redis_response_time >= self._thresholds['redis_response_time_warning']:
                self._create_alert(
                    'redis_response_time_warning',
                    AlertSeverity.WARNING,
                    'High Redis Response Time',
                    f'Redis response time is high: {metrics.redis_response_time:.2f}s',
                    'redis',
                    'response_time',
                    metrics.redis_response_time,
                    self._thresholds['redis_response_time_warning']
                )
            else:
                self._resolve_alert('redis_response_time_critical')
                self._resolve_alert('redis_response_time_warning')
    
    def _check_worker_health_alerts(self, metrics: PerformanceMetrics) -> None:
        """Check for worker health alerts"""
        # This would be implemented when worker management is available
        # For now, we can check if tasks are stuck in processing state
        
        if metrics.tasks_processing > 0:
            # Check for tasks that have been processing for too long
            session = self.db_manager.get_session()
            try:
                stuck_threshold = datetime.now(timezone.utc) - timedelta(hours=2)
                stuck_tasks = session.query(CaptionGenerationTask).filter(
                    CaptionGenerationTask.status == TaskStatus.RUNNING,
                    CaptionGenerationTask.started_at < stuck_threshold
                ).count()
                
                if stuck_tasks > 0:
                    self._create_alert(
                        'stuck_tasks',
                        AlertSeverity.ERROR,
                        'Stuck Tasks Detected',
                        f'{stuck_tasks} tasks have been processing for over 2 hours',
                        'worker',
                        'stuck_tasks',
                        stuck_tasks,
                        0
                    )
                else:
                    self._resolve_alert('stuck_tasks')
                    
            finally:
                session.close()
    
    def _create_alert(self, alert_id: str, severity: AlertSeverity, title: str, 
                     message: str, component: str, metric_name: str, 
                     metric_value: Any, threshold: Any) -> None:
        """Create or update an alert"""
        if alert_id in self._active_alerts:
            # Update existing alert
            alert = self._active_alerts[alert_id]
            alert.message = message
            alert.metric_value = metric_value
            alert.timestamp = datetime.now(timezone.utc)
        else:
            # Create new alert
            alert = Alert(
                id=alert_id,
                severity=severity,
                title=title,
                message=message,
                timestamp=datetime.now(timezone.utc),
                component=component,
                metric_name=metric_name,
                metric_value=metric_value,
                threshold=threshold
            )
            self._active_alerts[alert_id] = alert
            
            # Notify callbacks
            for callback in self._alert_callbacks:
                try:
                    callback(alert)
                except Exception as e:
                    logger.error(f"Error in alert callback: {sanitize_for_log(str(e))}")
            
            logger.warning(f"RQ Alert [{severity.value.upper()}]: {title} - {message}")
    
    def _resolve_alert(self, alert_id: str) -> None:
        """Resolve an active alert"""
        if alert_id in self._active_alerts:
            alert = self._active_alerts[alert_id]
            alert.resolved = True
            del self._active_alerts[alert_id]
            
            logger.info(f"RQ Alert resolved: {alert.title}")
    
    def register_alert_callback(self, callback: Callable[[Alert], None]) -> None:
        """Register a callback for new alerts"""
        self._alert_callbacks.append(callback)
    
    def get_current_metrics(self) -> Optional[PerformanceMetrics]:
        """Get the most recent performance metrics"""
        return self._metrics_history[-1] if self._metrics_history else None
    
    def get_metrics_history(self, hours: int = 24) -> List[PerformanceMetrics]:
        """Get metrics history for the specified number of hours"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        return [
            m for m in self._metrics_history 
            if m.timestamp > cutoff_time
        ]
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts"""
        return list(self._active_alerts.values())
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert"""
        if alert_id in self._active_alerts:
            self._active_alerts[alert_id].acknowledged = True
            logger.info(f"RQ Alert acknowledged: {alert_id}")
            return True
        return False
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get overall health summary"""
        current_metrics = self.get_current_metrics()
        active_alerts = self.get_active_alerts()
        
        # Determine overall health status
        critical_alerts = [a for a in active_alerts if a.severity == AlertSeverity.CRITICAL]
        error_alerts = [a for a in active_alerts if a.severity == AlertSeverity.ERROR]
        warning_alerts = [a for a in active_alerts if a.severity == AlertSeverity.WARNING]
        
        if critical_alerts:
            health_status = 'critical'
        elif error_alerts:
            health_status = 'error'
        elif warning_alerts:
            health_status = 'warning'
        else:
            health_status = 'healthy'
        
        return {
            'status': health_status,
            'monitoring_active': self._monitoring_active,
            'current_metrics': asdict(current_metrics) if current_metrics else None,
            'active_alerts_count': len(active_alerts),
            'alerts_by_severity': {
                'critical': len(critical_alerts),
                'error': len(error_alerts),
                'warning': len(warning_alerts),
                'info': len([a for a in active_alerts if a.severity == AlertSeverity.INFO])
            },
            'last_update': current_metrics.timestamp.isoformat() if current_metrics else None
        }
    
    def update_thresholds(self, new_thresholds: Dict[str, Any]) -> None:
        """Update alert thresholds"""
        self._thresholds.update(new_thresholds)
        logger.info(f"Updated RQ monitoring thresholds: {sanitize_for_log(str(new_thresholds))}")
    
    def get_thresholds(self) -> Dict[str, Any]:
        """Get current alert thresholds"""
        return self._thresholds.copy()
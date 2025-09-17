# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
RQ Monitoring and Logging Integration

Provides monitoring, metrics collection, and logging integration for RQ workers
in production environments.
"""

import logging
import time
import threading
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
import json
import requests
from dataclasses import dataclass, field

from app.core.security.core.security_utils import sanitize_for_log
from .production_config import ProductionRQConfig, ProductionMonitoringConfig

logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """Single metric data point"""
    name: str
    value: float
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class AlertEvent:
    """Alert event data"""
    alert_id: str
    severity: str  # info, warning, critical
    message: str
    timestamp: datetime
    metric_name: str
    current_value: float
    threshold: float
    labels: Dict[str, str] = field(default_factory=dict)


class RQMetricsCollector:
    """Collects metrics from RQ workers and queues"""
    
    def __init__(self, config: ProductionRQConfig):
        """
        Initialize metrics collector
        
        Args:
            config: Production RQ configuration
        """
        self.config = config
        self.metrics: List[MetricPoint] = []
        self.max_metrics = 10000  # Keep last 10k metrics
        self._lock = threading.Lock()
        
        # Metric collection state
        self._collection_enabled = config.monitoring_config.enable_metrics
        self._collection_interval = 30  # seconds
        self._collection_thread: Optional[threading.Thread] = None
        self._stop_collection = threading.Event()
    
    def start_collection(self) -> None:
        """Start metrics collection"""
        if not self._collection_enabled or self._collection_thread:
            return
        
        self._stop_collection.clear()
        self._collection_thread = threading.Thread(
            target=self._collection_loop,
            daemon=True,
            name="RQMetricsCollector"
        )
        self._collection_thread.start()
        logger.info("RQ metrics collection started")
    
    def stop_collection(self) -> None:
        """Stop metrics collection"""
        if not self._collection_thread:
            return
        
        self._stop_collection.set()
        self._collection_thread.join(timeout=10)
        self._collection_thread = None
        logger.info("RQ metrics collection stopped")
    
    def _collection_loop(self) -> None:
        """Main metrics collection loop"""
        while not self._stop_collection.wait(self._collection_interval):
            try:
                self._collect_metrics()
            except Exception as e:
                logger.error(f"Error collecting metrics: {sanitize_for_log(str(e))}")
    
    def _collect_metrics(self) -> None:
        """Collect current metrics"""
        timestamp = datetime.utcnow()
        
        try:
            # Collect queue metrics
            queue_metrics = self._collect_queue_metrics(timestamp)
            
            # Collect worker metrics
            worker_metrics = self._collect_worker_metrics(timestamp)
            
            # Collect system metrics
            system_metrics = self._collect_system_metrics(timestamp)
            
            # Store metrics
            with self._lock:
                self.metrics.extend(queue_metrics + worker_metrics + system_metrics)
                
                # Trim old metrics
                if len(self.metrics) > self.max_metrics:
                    self.metrics = self.metrics[-self.max_metrics:]
            
        except Exception as e:
            logger.error(f"Failed to collect metrics: {sanitize_for_log(str(e))}")
    
    def _collect_queue_metrics(self, timestamp: datetime) -> List[MetricPoint]:
        """Collect queue-related metrics"""
        metrics = []
        
        try:
            import redis
            from rq import Queue
            
            # Connect to Redis
            redis_conn = redis.from_url(self.config.redis_url)
            
            # Collect metrics for each queue
            for queue_name in self.config.get_queue_names():
                queue = Queue(queue_name, connection=redis_conn)
                
                # Queue length
                metrics.append(MetricPoint(
                    name="rq_queue_length",
                    value=len(queue),
                    timestamp=timestamp,
                    labels={"queue": queue_name}
                ))
                
                # Failed jobs count
                failed_job_registry = queue.failed_job_registry
                metrics.append(MetricPoint(
                    name="rq_queue_failed_jobs",
                    value=len(failed_job_registry),
                    timestamp=timestamp,
                    labels={"queue": queue_name}
                ))
                
                # Deferred jobs count
                deferred_job_registry = queue.deferred_job_registry
                metrics.append(MetricPoint(
                    name="rq_queue_deferred_jobs",
                    value=len(deferred_job_registry),
                    timestamp=timestamp,
                    labels={"queue": queue_name}
                ))
        
        except Exception as e:
            logger.error(f"Failed to collect queue metrics: {sanitize_for_log(str(e))}")
        
        return metrics
    
    def _collect_worker_metrics(self, timestamp: datetime) -> List[MetricPoint]:
        """Collect worker-related metrics"""
        metrics = []
        
        try:
            import redis
            from rq import Worker
            
            # Connect to Redis
            redis_conn = redis.from_url(self.config.redis_url)
            
            # Get all workers
            workers = Worker.all(connection=redis_conn)
            
            # Total workers
            metrics.append(MetricPoint(
                name="rq_workers_total",
                value=len(workers),
                timestamp=timestamp
            ))
            
            # Workers by state
            busy_workers = 0
            idle_workers = 0
            
            for worker in workers:
                if worker.get_current_job():
                    busy_workers += 1
                else:
                    idle_workers += 1
            
            metrics.append(MetricPoint(
                name="rq_workers_busy",
                value=busy_workers,
                timestamp=timestamp
            ))
            
            metrics.append(MetricPoint(
                name="rq_workers_idle",
                value=idle_workers,
                timestamp=timestamp
            ))
        
        except Exception as e:
            logger.error(f"Failed to collect worker metrics: {sanitize_for_log(str(e))}")
        
        return metrics
    
    def _collect_system_metrics(self, timestamp: datetime) -> List[MetricPoint]:
        """Collect system-related metrics"""
        metrics = []
        
        try:
            import psutil
            
            # Memory usage
            memory = psutil.virtual_memory()
            metrics.append(MetricPoint(
                name="system_memory_usage_percent",
                value=memory.percent,
                timestamp=timestamp
            ))
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            metrics.append(MetricPoint(
                name="system_cpu_usage_percent",
                value=cpu_percent,
                timestamp=timestamp
            ))
            
            # Redis memory usage
            try:
                import redis
                redis_conn = redis.from_url(self.config.redis_url)
                redis_info = redis_conn.info('memory')
                
                used_memory = redis_info.get('used_memory', 0)
                max_memory = redis_info.get('maxmemory', 0)
                
                if max_memory > 0:
                    redis_memory_percent = (used_memory / max_memory) * 100
                    metrics.append(MetricPoint(
                        name="redis_memory_usage_percent",
                        value=redis_memory_percent,
                        timestamp=timestamp
                    ))
                
                metrics.append(MetricPoint(
                    name="redis_memory_usage_bytes",
                    value=used_memory,
                    timestamp=timestamp
                ))
            
            except Exception as e:
                logger.debug(f"Failed to collect Redis memory metrics: {sanitize_for_log(str(e))}")
        
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {sanitize_for_log(str(e))}")
        
        return metrics
    
    def get_metrics(self, metric_name: Optional[str] = None, 
                   since: Optional[datetime] = None) -> List[MetricPoint]:
        """
        Get collected metrics
        
        Args:
            metric_name: Filter by metric name
            since: Filter metrics since this timestamp
            
        Returns:
            List of metric points
        """
        with self._lock:
            metrics = self.metrics.copy()
        
        # Apply filters
        if metric_name:
            metrics = [m for m in metrics if m.name == metric_name]
        
        if since:
            metrics = [m for m in metrics if m.timestamp >= since]
        
        return metrics
    
    def get_latest_metric(self, metric_name: str) -> Optional[MetricPoint]:
        """Get latest value for a specific metric"""
        metrics = self.get_metrics(metric_name)
        return max(metrics, key=lambda m: m.timestamp) if metrics else None


class RQAlerting:
    """Handles alerting for RQ metrics"""
    
    def __init__(self, config: ProductionRQConfig, metrics_collector: RQMetricsCollector):
        """
        Initialize alerting system
        
        Args:
            config: Production RQ configuration
            metrics_collector: Metrics collector instance
        """
        self.config = config
        self.metrics_collector = metrics_collector
        self.monitoring_config = config.monitoring_config
        
        # Alert state
        self._alerting_enabled = self.monitoring_config.enable_alerting
        self._alert_history: List[AlertEvent] = []
        self._alert_cooldowns: Dict[str, datetime] = {}
        self._alert_thread: Optional[threading.Thread] = None
        self._stop_alerting = threading.Event()
        
        # Alert configuration
        self._alert_interval = 60  # seconds
        self._alert_cooldown = 300  # 5 minutes
        self._max_alert_history = 1000
    
    def start_alerting(self) -> None:
        """Start alerting system"""
        if not self._alerting_enabled or self._alert_thread:
            return
        
        self._stop_alerting.clear()
        self._alert_thread = threading.Thread(
            target=self._alerting_loop,
            daemon=True,
            name="RQAlerting"
        )
        self._alert_thread.start()
        logger.info("RQ alerting started")
    
    def stop_alerting(self) -> None:
        """Stop alerting system"""
        if not self._alert_thread:
            return
        
        self._stop_alerting.set()
        self._alert_thread.join(timeout=10)
        self._alert_thread = None
        logger.info("RQ alerting stopped")
    
    def _alerting_loop(self) -> None:
        """Main alerting loop"""
        while not self._stop_alerting.wait(self._alert_interval):
            try:
                self._check_alerts()
            except Exception as e:
                logger.error(f"Error checking alerts: {sanitize_for_log(str(e))}")
    
    def _check_alerts(self) -> None:
        """Check for alert conditions"""
        current_time = datetime.utcnow()
        
        # Check each alert threshold
        for metric_name, threshold in self.monitoring_config.alert_thresholds.items():
            try:
                # Get latest metric value
                latest_metric = self.metrics_collector.get_latest_metric(metric_name)
                
                if not latest_metric:
                    continue
                
                # Check if threshold is exceeded
                if latest_metric.value > threshold:
                    alert_id = f"{metric_name}_threshold"
                    
                    # Check cooldown
                    if alert_id in self._alert_cooldowns:
                        if current_time < self._alert_cooldowns[alert_id]:
                            continue  # Still in cooldown
                    
                    # Create alert
                    alert = AlertEvent(
                        alert_id=alert_id,
                        severity=self._get_alert_severity(metric_name, latest_metric.value, threshold),
                        message=f"{metric_name} exceeded threshold: {latest_metric.value:.2f} > {threshold}",
                        timestamp=current_time,
                        metric_name=metric_name,
                        current_value=latest_metric.value,
                        threshold=threshold,
                        labels=latest_metric.labels
                    )
                    
                    # Send alert
                    if self._send_alert(alert):
                        # Set cooldown
                        self._alert_cooldowns[alert_id] = current_time + timedelta(seconds=self._alert_cooldown)
                        
                        # Store in history
                        self._alert_history.append(alert)
                        
                        # Trim history
                        if len(self._alert_history) > self._max_alert_history:
                            self._alert_history = self._alert_history[-self._max_alert_history:]
            
            except Exception as e:
                logger.error(f"Error checking alert for {metric_name}: {sanitize_for_log(str(e))}")
    
    def _get_alert_severity(self, metric_name: str, value: float, threshold: float) -> str:
        """Determine alert severity based on how much threshold is exceeded"""
        excess_ratio = value / threshold
        
        if excess_ratio > 1.5:  # 50% over threshold
            return "critical"
        elif excess_ratio > 1.2:  # 20% over threshold
            return "warning"
        else:
            return "info"
    
    def _send_alert(self, alert: AlertEvent) -> bool:
        """Send alert notification"""
        try:
            if not self.monitoring_config.alert_webhook_url:
                logger.warning("Alert webhook URL not configured")
                return False
            
            # Prepare alert payload
            payload = {
                "alert_id": alert.alert_id,
                "severity": alert.severity,
                "message": alert.message,
                "timestamp": alert.timestamp.isoformat(),
                "metric_name": alert.metric_name,
                "current_value": alert.current_value,
                "threshold": alert.threshold,
                "labels": alert.labels,
                "environment": self.config.environment.value
            }
            
            # Send webhook
            response = requests.post(
                self.monitoring_config.alert_webhook_url,
                json=payload,
                timeout=10,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                logger.info(f"Alert sent successfully: {alert.alert_id}")
                return True
            else:
                logger.error(f"Failed to send alert: HTTP {response.status_code}")
                return False
        
        except Exception as e:
            logger.error(f"Error sending alert: {sanitize_for_log(str(e))}")
            return False
    
    def get_alert_history(self, since: Optional[datetime] = None) -> List[AlertEvent]:
        """Get alert history"""
        alerts = self._alert_history.copy()
        
        if since:
            alerts = [a for a in alerts if a.timestamp >= since]
        
        return alerts


class RQMonitoringIntegration:
    """Main monitoring integration for RQ workers"""
    
    def __init__(self, config: ProductionRQConfig):
        """
        Initialize monitoring integration
        
        Args:
            config: Production RQ configuration
        """
        self.config = config
        self.metrics_collector = RQMetricsCollector(config)
        self.alerting = RQAlerting(config, self.metrics_collector)
        
        # Integration state
        self._started = False
    
    def start(self) -> None:
        """Start monitoring integration"""
        if self._started:
            return
        
        logger.info("Starting RQ monitoring integration")
        
        # Start metrics collection
        self.metrics_collector.start_collection()
        
        # Start alerting
        self.alerting.start_alerting()
        
        self._started = True
        logger.info("RQ monitoring integration started")
    
    def stop(self) -> None:
        """Stop monitoring integration"""
        if not self._started:
            return
        
        logger.info("Stopping RQ monitoring integration")
        
        # Stop alerting
        self.alerting.stop_alerting()
        
        # Stop metrics collection
        self.metrics_collector.stop_collection()
        
        self._started = False
        logger.info("RQ monitoring integration stopped")
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get monitoring system status"""
        return {
            'started': self._started,
            'metrics_collection_enabled': self.config.monitoring_config.enable_metrics,
            'alerting_enabled': self.config.monitoring_config.enable_alerting,
            'total_metrics': len(self.metrics_collector.metrics),
            'total_alerts': len(self.alerting._alert_history),
            'environment': self.config.environment.value
        }
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data for monitoring dashboard"""
        # Get recent metrics (last hour)
        since = datetime.utcnow() - timedelta(hours=1)
        
        # Get key metrics
        queue_lengths = {}
        for queue_name in self.config.get_queue_names():
            metric = self.metrics_collector.get_latest_metric("rq_queue_length")
            if metric and metric.labels.get("queue") == queue_name:
                queue_lengths[queue_name] = metric.value
        
        # Get system metrics
        memory_metric = self.metrics_collector.get_latest_metric("system_memory_usage_percent")
        cpu_metric = self.metrics_collector.get_latest_metric("system_cpu_usage_percent")
        workers_metric = self.metrics_collector.get_latest_metric("rq_workers_total")
        
        # Get recent alerts
        recent_alerts = self.alerting.get_alert_history(since)
        
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'queue_lengths': queue_lengths,
            'system_memory_percent': memory_metric.value if memory_metric else 0,
            'system_cpu_percent': cpu_metric.value if cpu_metric else 0,
            'total_workers': workers_metric.value if workers_metric else 0,
            'recent_alerts': len(recent_alerts),
            'alert_summary': {
                'critical': len([a for a in recent_alerts if a.severity == 'critical']),
                'warning': len([a for a in recent_alerts if a.severity == 'warning']),
                'info': len([a for a in recent_alerts if a.severity == 'info'])
            }
        }
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Advanced Monitoring Service

Provides advanced monitoring and metrics collection with feature flag enforcement.
Only collects advanced metrics when the feature flag is enabled.
"""

import logging
import threading
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from collections import defaultdict, deque
import psutil
import os

from feature_flag_service import FeatureFlagService
from feature_flag_decorators import FeatureFlagMiddleware, advanced_monitoring_required

logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """Single metric data point"""
    timestamp: datetime
    value: float
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class AdvancedMetrics:
    """Advanced metrics collection"""
    system_metrics: Dict[str, List[MetricPoint]] = field(default_factory=dict)
    application_metrics: Dict[str, List[MetricPoint]] = field(default_factory=dict)
    performance_metrics: Dict[str, List[MetricPoint]] = field(default_factory=dict)
    custom_metrics: Dict[str, List[MetricPoint]] = field(default_factory=dict)
    collection_start: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_collection: Optional[datetime] = None


class AdvancedMonitoringService:
    """
    Advanced monitoring service with feature flag enforcement
    
    Collects detailed system and application metrics only when
    the enable_advanced_monitoring feature flag is enabled.
    """
    
    def __init__(self, feature_service: FeatureFlagService, 
                 collection_interval: int = 60,
                 retention_hours: int = 24,
                 max_points_per_metric: int = 1440):  # 24 hours at 1-minute intervals
        """
        Initialize advanced monitoring service
        
        Args:
            feature_service: FeatureFlagService instance
            collection_interval: Metric collection interval in seconds
            retention_hours: How long to retain metrics
            max_points_per_metric: Maximum data points per metric
        """
        self.feature_service = feature_service
        self.feature_middleware = FeatureFlagMiddleware(feature_service)
        self.collection_interval = collection_interval
        self.retention_hours = retention_hours
        self.max_points_per_metric = max_points_per_metric
        
        # Metrics storage
        self.metrics = AdvancedMetrics()
        self._metrics_lock = threading.RLock()
        
        # Collection state
        self._collection_thread = None
        self._stop_collection = threading.Event()
        self._is_collecting = False
        
        # Performance tracking
        self._request_times = deque(maxlen=1000)
        self._error_counts = defaultdict(int)
        self._feature_usage = defaultdict(int)
        
        # Start collection if feature is enabled
        if self.feature_service.is_enabled('enable_advanced_monitoring'):
            self.start_collection()
    
    def start_collection(self) -> bool:
        """
        Start advanced metrics collection
        
        Returns:
            True if collection started successfully
        """
        if not self.feature_middleware.enforce_advanced_monitoring("metrics collection startup"):
            return False
        
        if self._is_collecting:
            logger.warning("Advanced monitoring collection is already running")
            return True
        
        try:
            self._stop_collection.clear()
            self._collection_thread = threading.Thread(target=self._collection_loop, daemon=True)
            self._collection_thread.start()
            self._is_collecting = True
            
            logger.info("Advanced monitoring collection started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start advanced monitoring collection: {e}")
            return False
    
    def stop_collection(self) -> bool:
        """
        Stop advanced metrics collection
        
        Returns:
            True if collection stopped successfully
        """
        if not self._is_collecting:
            return True
        
        try:
            self._stop_collection.set()
            
            if self._collection_thread and self._collection_thread.is_alive():
                self._collection_thread.join(timeout=5.0)
            
            self._is_collecting = False
            logger.info("Advanced monitoring collection stopped")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping advanced monitoring collection: {e}")
            return False
    
    def collect_system_metrics(self) -> Optional[Dict[str, float]]:
        """
        Collect system-level metrics
        
        Returns:
            Dictionary of system metrics or None if feature disabled
        """
        # Check if advanced monitoring is enabled
        if not self.feature_middleware.enforce_advanced_monitoring("system metrics collection"):
            return None
        
        try:
            metrics = {}
            
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            metrics['cpu_usage_percent'] = cpu_percent
            
            cpu_count = psutil.cpu_count()
            metrics['cpu_count'] = cpu_count
            
            # Memory metrics
            memory = psutil.virtual_memory()
            metrics['memory_usage_percent'] = memory.percent
            metrics['memory_used_bytes'] = memory.used
            metrics['memory_available_bytes'] = memory.available
            metrics['memory_total_bytes'] = memory.total
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            metrics['disk_usage_percent'] = (disk.used / disk.total) * 100
            metrics['disk_used_bytes'] = disk.used
            metrics['disk_free_bytes'] = disk.free
            metrics['disk_total_bytes'] = disk.total
            
            # Network metrics (if available)
            try:
                network = psutil.net_io_counters()
                metrics['network_bytes_sent'] = network.bytes_sent
                metrics['network_bytes_recv'] = network.bytes_recv
                metrics['network_packets_sent'] = network.packets_sent
                metrics['network_packets_recv'] = network.packets_recv
            except Exception:
                pass  # Network metrics not available on all systems
            
            # Process metrics
            process = psutil.Process(os.getpid())
            metrics['process_memory_rss'] = process.memory_info().rss
            metrics['process_memory_vms'] = process.memory_info().vms
            metrics['process_cpu_percent'] = process.cpu_percent()
            metrics['process_num_threads'] = process.num_threads()
            
            # Store metrics
            timestamp = datetime.now(timezone.utc)
            with self._metrics_lock:
                for key, value in metrics.items():
                    if key not in self.metrics.system_metrics:
                        self.metrics.system_metrics[key] = []
                    
                    self.metrics.system_metrics[key].append(
                        MetricPoint(timestamp=timestamp, value=float(value))
                    )
                    
                    # Limit data points
                    if len(self.metrics.system_metrics[key]) > self.max_points_per_metric:
                        self.metrics.system_metrics[key] = self.metrics.system_metrics[key][-self.max_points_per_metric:]
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            return None
    
    def collect_application_metrics(self) -> Optional[Dict[str, float]]:
        """
        Collect application-level metrics
        
        Returns:
            Dictionary of application metrics or None if feature disabled
        """
        # Check if advanced monitoring is enabled
        if not self.feature_middleware.enforce_advanced_monitoring("application metrics collection"):
            return None
        
        try:
            metrics = {}
            
            # Request performance metrics
            if self._request_times:
                recent_times = list(self._request_times)
                metrics['avg_request_time_ms'] = sum(recent_times) / len(recent_times) * 1000
                metrics['max_request_time_ms'] = max(recent_times) * 1000
                metrics['min_request_time_ms'] = min(recent_times) * 1000
                metrics['total_requests'] = len(recent_times)
            
            # Error metrics
            total_errors = sum(self._error_counts.values())
            metrics['total_errors'] = total_errors
            
            for error_type, count in self._error_counts.items():
                metrics[f'errors_{error_type}'] = count
            
            # Feature usage metrics
            for feature, usage_count in self._feature_usage.items():
                metrics[f'feature_usage_{feature}'] = usage_count
            
            # Database connection pool metrics (if available)
            try:
                # This would need to be integrated with your database manager
                # metrics['db_pool_size'] = db_manager.get_pool_size()
                # metrics['db_active_connections'] = db_manager.get_active_connections()
                pass
            except Exception:
                pass
            
            # Store metrics
            timestamp = datetime.now(timezone.utc)
            with self._metrics_lock:
                for key, value in metrics.items():
                    if key not in self.metrics.application_metrics:
                        self.metrics.application_metrics[key] = []
                    
                    self.metrics.application_metrics[key].append(
                        MetricPoint(timestamp=timestamp, value=float(value))
                    )
                    
                    # Limit data points
                    if len(self.metrics.application_metrics[key]) > self.max_points_per_metric:
                        self.metrics.application_metrics[key] = self.metrics.application_metrics[key][-self.max_points_per_metric:]
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting application metrics: {e}")
            return None
    
    def record_request_time(self, request_time: float) -> None:
        """
        Record request processing time
        
        Args:
            request_time: Request time in seconds
        """
        if not self.feature_middleware.enforce_advanced_monitoring("request time recording"):
            return
        
        self._request_times.append(request_time)
    
    def record_error(self, error_type: str) -> None:
        """
        Record an error occurrence
        
        Args:
            error_type: Type of error that occurred
        """
        if not self.feature_middleware.enforce_advanced_monitoring("error recording"):
            return
        
        self._error_counts[error_type] += 1
    
    def record_feature_usage(self, feature_name: str) -> None:
        """
        Record feature usage
        
        Args:
            feature_name: Name of the feature used
        """
        if not self.feature_middleware.enforce_advanced_monitoring("feature usage recording"):
            return
        
        self._feature_usage[feature_name] += 1
    
    def add_custom_metric(self, metric_name: str, value: float, tags: Dict[str, str] = None) -> None:
        """
        Add a custom metric
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            tags: Optional tags for the metric
        """
        if not self.feature_middleware.enforce_advanced_monitoring("custom metric recording"):
            return
        
        timestamp = datetime.now(timezone.utc)
        
        with self._metrics_lock:
            if metric_name not in self.metrics.custom_metrics:
                self.metrics.custom_metrics[metric_name] = []
            
            self.metrics.custom_metrics[metric_name].append(
                MetricPoint(timestamp=timestamp, value=value, tags=tags or {})
            )
            
            # Limit data points
            if len(self.metrics.custom_metrics[metric_name]) > self.max_points_per_metric:
                self.metrics.custom_metrics[metric_name] = self.metrics.custom_metrics[metric_name][-self.max_points_per_metric:]
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """
        Get summary of collected metrics
        
        Returns:
            Dictionary with metrics summary
        """
        if not self.feature_middleware.enforce_advanced_monitoring("metrics summary"):
            return {
                'advanced_monitoring_enabled': False,
                'message': 'Advanced monitoring is disabled'
            }
        
        with self._metrics_lock:
            summary = {
                'advanced_monitoring_enabled': True,
                'collection_active': self._is_collecting,
                'collection_start': self.metrics.collection_start,
                'last_collection': self.metrics.last_collection,
                'metrics_count': {
                    'system': len(self.metrics.system_metrics),
                    'application': len(self.metrics.application_metrics),
                    'performance': len(self.metrics.performance_metrics),
                    'custom': len(self.metrics.custom_metrics)
                },
                'data_points': {
                    'system': sum(len(points) for points in self.metrics.system_metrics.values()),
                    'application': sum(len(points) for points in self.metrics.application_metrics.values()),
                    'performance': sum(len(points) for points in self.metrics.performance_metrics.values()),
                    'custom': sum(len(points) for points in self.metrics.custom_metrics.values())
                }
            }
            
            # Add latest values for key metrics
            if self.metrics.system_metrics:
                latest_system = {}
                for metric_name, points in self.metrics.system_metrics.items():
                    if points:
                        latest_system[metric_name] = points[-1].value
                summary['latest_system_metrics'] = latest_system
            
            if self.metrics.application_metrics:
                latest_app = {}
                for metric_name, points in self.metrics.application_metrics.items():
                    if points:
                        latest_app[metric_name] = points[-1].value
                summary['latest_application_metrics'] = latest_app
        
        return summary
    
    def get_metric_history(self, metric_name: str, hours: int = 1) -> List[MetricPoint]:
        """
        Get historical data for a specific metric
        
        Args:
            metric_name: Name of the metric
            hours: Number of hours of history to return
            
        Returns:
            List of MetricPoint objects
        """
        if not self.feature_middleware.enforce_advanced_monitoring("metric history"):
            return []
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        with self._metrics_lock:
            # Search in all metric categories
            all_metrics = {
                **self.metrics.system_metrics,
                **self.metrics.application_metrics,
                **self.metrics.performance_metrics,
                **self.metrics.custom_metrics
            }
            
            if metric_name not in all_metrics:
                return []
            
            # Filter by time
            return [
                point for point in all_metrics[metric_name]
                if point.timestamp >= cutoff_time
            ]
    
    def cleanup_old_metrics(self) -> int:
        """
        Clean up metrics older than retention period
        
        Returns:
            Number of data points removed
        """
        if not self.feature_middleware.enforce_advanced_monitoring("metrics cleanup"):
            return 0
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=self.retention_hours)
        removed_count = 0
        
        with self._metrics_lock:
            # Clean up all metric categories
            for metric_category in [
                self.metrics.system_metrics,
                self.metrics.application_metrics,
                self.metrics.performance_metrics,
                self.metrics.custom_metrics
            ]:
                for metric_name, points in metric_category.items():
                    original_count = len(points)
                    metric_category[metric_name] = [
                        point for point in points
                        if point.timestamp >= cutoff_time
                    ]
                    removed_count += original_count - len(metric_category[metric_name])
        
        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} old metric data points")
        
        return removed_count
    
    def _collection_loop(self):
        """Main collection loop running in background thread"""
        logger.info("Advanced monitoring collection loop started")
        
        while not self._stop_collection.is_set():
            try:
                # Check if feature is still enabled
                if not self.feature_service.is_enabled('enable_advanced_monitoring'):
                    logger.info("Advanced monitoring feature disabled, stopping collection")
                    break
                
                # Collect metrics
                self.collect_system_metrics()
                self.collect_application_metrics()
                
                # Update last collection time
                with self._metrics_lock:
                    self.metrics.last_collection = datetime.now(timezone.utc)
                
                # Periodic cleanup
                if self.metrics.last_collection.minute % 10 == 0:  # Every 10 minutes
                    self.cleanup_old_metrics()
                
                # Wait for next collection
                self._stop_collection.wait(self.collection_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring collection loop: {e}")
                # Continue collecting despite errors
                self._stop_collection.wait(self.collection_interval)
        
        self._is_collecting = False
        logger.info("Advanced monitoring collection loop stopped")
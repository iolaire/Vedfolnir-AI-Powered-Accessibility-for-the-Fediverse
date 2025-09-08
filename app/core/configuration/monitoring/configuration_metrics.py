# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Configuration Metrics Collection

Comprehensive metrics collection system for configuration service operations,
including access patterns, cache performance, change frequency, and performance impact.
"""

import time
import threading
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum
import json
import statistics

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of configuration metrics"""
    ACCESS = "access"
    CACHE = "cache"
    CHANGE = "change"
    PERFORMANCE = "performance"
    ERROR = "error"


@dataclass
class ConfigurationAccessMetric:
    """Metrics for configuration access operations"""
    key: str
    timestamp: datetime
    source: str  # environment, database, cache, default
    access_time_ms: float
    success: bool
    error_message: Optional[str] = None
    user_context: Optional[str] = None


@dataclass
class ConfigurationCacheMetric:
    """Metrics for cache operations"""
    operation: str  # hit, miss, set, invalidate, evict
    key: Optional[str]
    timestamp: datetime
    cache_size: int
    memory_usage_bytes: int
    operation_time_ms: float
    hit_rate: float


@dataclass
class ConfigurationChangeMetric:
    """Metrics for configuration changes"""
    key: str
    timestamp: datetime
    old_value: Any
    new_value: Any
    source: str  # admin_ui, api, environment
    user_id: Optional[int]
    requires_restart: bool
    change_impact: str  # low, medium, high, critical


@dataclass
class ConfigurationPerformanceMetric:
    """Performance impact metrics"""
    operation: str
    timestamp: datetime
    duration_ms: float
    memory_delta_bytes: int
    cpu_usage_percent: float
    affected_services: List[str]
    performance_impact: str  # negligible, low, medium, high


@dataclass
class MetricsSummary:
    """Summary of configuration metrics"""
    total_accesses: int = 0
    cache_hit_rate: float = 0.0
    average_access_time_ms: float = 0.0
    total_changes: int = 0
    change_frequency_per_hour: float = 0.0
    most_accessed_keys: List[Tuple[str, int]] = field(default_factory=list)
    most_changed_keys: List[Tuple[str, int]] = field(default_factory=list)
    error_rate: float = 0.0
    performance_impact_score: float = 0.0
    restart_required_changes: int = 0


class ConfigurationMetricsCollector:
    """
    Comprehensive metrics collection system for configuration operations
    
    Features:
    - Real-time metrics collection
    - Access pattern analysis
    - Cache performance monitoring
    - Change frequency tracking
    - Performance impact assessment
    - Thread-safe operations
    - Configurable retention periods
    """
    
    def __init__(self, retention_hours: int = 24, max_metrics_per_type: int = 10000):
        """
        Initialize metrics collector
        
        Args:
            retention_hours: How long to retain metrics
            max_metrics_per_type: Maximum metrics per type to keep in memory
        """
        self.retention_hours = retention_hours
        self.max_metrics_per_type = max_metrics_per_type
        
        # Thread-safe metric storage
        self._access_metrics: deque = deque(maxlen=max_metrics_per_type)
        self._cache_metrics: deque = deque(maxlen=max_metrics_per_type)
        self._change_metrics: deque = deque(maxlen=max_metrics_per_type)
        self._performance_metrics: deque = deque(maxlen=max_metrics_per_type)
        
        # Thread locks
        self._access_lock = threading.RLock()
        self._cache_lock = threading.RLock()
        self._change_lock = threading.RLock()
        self._performance_lock = threading.RLock()
        
        # Aggregated statistics
        self._stats = {
            'total_accesses': 0,
            'total_cache_hits': 0,
            'total_cache_misses': 0,
            'total_changes': 0,
            'total_errors': 0,
            'key_access_counts': defaultdict(int),
            'key_change_counts': defaultdict(int),
            'source_counts': defaultdict(int),
            'error_counts': defaultdict(int)
        }
        self._stats_lock = threading.RLock()
        
        # Performance tracking
        self._performance_samples: deque = deque(maxlen=1000)
        self._performance_lock_samples = threading.RLock()
        
        # Start cleanup thread
        self._cleanup_thread = threading.Thread(target=self._cleanup_old_metrics, daemon=True)
        self._cleanup_thread.start()
    
    def record_access(self, key: str, source: str, access_time_ms: float, 
                     success: bool = True, error_message: str = None, 
                     user_context: str = None):
        """
        Record configuration access metric
        
        Args:
            key: Configuration key accessed
            source: Source of the value (environment, database, cache, default)
            access_time_ms: Time taken to access in milliseconds
            success: Whether access was successful
            error_message: Error message if access failed
            user_context: User context information
        """
        metric = ConfigurationAccessMetric(
            key=key,
            timestamp=datetime.now(timezone.utc),
            source=source,
            access_time_ms=access_time_ms,
            success=success,
            error_message=error_message,
            user_context=user_context
        )
        
        with self._access_lock:
            self._access_metrics.append(metric)
        
        # Update aggregated stats
        with self._stats_lock:
            self._stats['total_accesses'] += 1
            self._stats['key_access_counts'][key] += 1
            self._stats['source_counts'][source] += 1
            
            if not success:
                self._stats['total_errors'] += 1
                self._stats['error_counts'][key] += 1
        
        logger.debug(f"Recorded access metric for key {key}: {access_time_ms:.2f}ms from {source}")
    
    def record_cache_operation(self, operation: str, key: str = None, 
                              cache_size: int = 0, memory_usage_bytes: int = 0,
                              operation_time_ms: float = 0.0, hit_rate: float = 0.0):
        """
        Record cache operation metric
        
        Args:
            operation: Cache operation (hit, miss, set, invalidate, evict)
            key: Configuration key (if applicable)
            cache_size: Current cache size
            memory_usage_bytes: Current memory usage
            operation_time_ms: Time taken for operation
            hit_rate: Current cache hit rate
        """
        metric = ConfigurationCacheMetric(
            operation=operation,
            key=key,
            timestamp=datetime.now(timezone.utc),
            cache_size=cache_size,
            memory_usage_bytes=memory_usage_bytes,
            operation_time_ms=operation_time_ms,
            hit_rate=hit_rate
        )
        
        with self._cache_lock:
            self._cache_metrics.append(metric)
        
        # Update aggregated stats
        with self._stats_lock:
            if operation == 'hit':
                self._stats['total_cache_hits'] += 1
            elif operation == 'miss':
                self._stats['total_cache_misses'] += 1
        
        logger.debug(f"Recorded cache metric: {operation} for key {key}")
    
    def record_configuration_change(self, key: str, old_value: Any, new_value: Any,
                                   source: str, user_id: int = None, 
                                   requires_restart: bool = False,
                                   change_impact: str = "low"):
        """
        Record configuration change metric
        
        Args:
            key: Configuration key that changed
            old_value: Previous value
            new_value: New value
            source: Source of change (admin_ui, api, environment)
            user_id: User who made the change
            requires_restart: Whether change requires restart
            change_impact: Impact level (low, medium, high, critical)
        """
        metric = ConfigurationChangeMetric(
            key=key,
            timestamp=datetime.now(timezone.utc),
            old_value=old_value,
            new_value=new_value,
            source=source,
            user_id=user_id,
            requires_restart=requires_restart,
            change_impact=change_impact
        )
        
        with self._change_lock:
            self._change_metrics.append(metric)
        
        # Update aggregated stats
        with self._stats_lock:
            self._stats['total_changes'] += 1
            self._stats['key_change_counts'][key] += 1
        
        logger.info(f"Recorded configuration change for key {key}: {old_value} -> {new_value}")
    
    def record_performance_impact(self, operation: str, duration_ms: float,
                                 memory_delta_bytes: int = 0, 
                                 cpu_usage_percent: float = 0.0,
                                 affected_services: List[str] = None,
                                 performance_impact: str = "negligible"):
        """
        Record performance impact metric
        
        Args:
            operation: Operation that was performed
            duration_ms: Duration in milliseconds
            memory_delta_bytes: Memory usage change
            cpu_usage_percent: CPU usage during operation
            affected_services: List of affected services
            performance_impact: Impact level (negligible, low, medium, high)
        """
        metric = ConfigurationPerformanceMetric(
            operation=operation,
            timestamp=datetime.now(timezone.utc),
            duration_ms=duration_ms,
            memory_delta_bytes=memory_delta_bytes,
            cpu_usage_percent=cpu_usage_percent,
            affected_services=affected_services or [],
            performance_impact=performance_impact
        )
        
        with self._performance_lock:
            self._performance_metrics.append(metric)
        
        # Update performance samples for analysis
        with self._performance_lock_samples:
            self._performance_samples.append({
                'timestamp': metric.timestamp,
                'duration_ms': duration_ms,
                'memory_delta': memory_delta_bytes,
                'cpu_usage': cpu_usage_percent
            })
        
        logger.debug(f"Recorded performance metric for {operation}: {duration_ms:.2f}ms")
    
    def get_access_patterns(self, hours: int = 1) -> Dict[str, Any]:
        """
        Get configuration access patterns for the specified time period
        
        Args:
            hours: Number of hours to analyze
            
        Returns:
            Dictionary with access pattern analysis
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        with self._access_lock:
            recent_metrics = [m for m in self._access_metrics if m.timestamp >= cutoff_time]
        
        if not recent_metrics:
            return {
                'total_accesses': 0,
                'unique_keys': 0,
                'average_access_time_ms': 0.0,
                'success_rate': 1.0,
                'top_keys': [],
                'source_distribution': {},
                'error_rate': 0.0
            }
        
        # Analyze patterns
        key_counts = defaultdict(int)
        source_counts = defaultdict(int)
        access_times = []
        successful_accesses = 0
        
        for metric in recent_metrics:
            key_counts[metric.key] += 1
            source_counts[metric.source] += 1
            access_times.append(metric.access_time_ms)
            if metric.success:
                successful_accesses += 1
        
        # Calculate statistics
        total_accesses = len(recent_metrics)
        success_rate = successful_accesses / total_accesses if total_accesses > 0 else 1.0
        avg_access_time = statistics.mean(access_times) if access_times else 0.0
        
        # Top keys by access count
        top_keys = sorted(key_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            'total_accesses': total_accesses,
            'unique_keys': len(key_counts),
            'average_access_time_ms': avg_access_time,
            'success_rate': success_rate,
            'error_rate': 1.0 - success_rate,
            'top_keys': top_keys,
            'source_distribution': dict(source_counts),
            'access_time_percentiles': {
                'p50': statistics.median(access_times) if access_times else 0.0,
                'p95': statistics.quantiles(access_times, n=20)[18] if len(access_times) > 20 else 0.0,
                'p99': statistics.quantiles(access_times, n=100)[98] if len(access_times) > 100 else 0.0
            }
        }
    
    def get_cache_performance(self, hours: int = 1) -> Dict[str, Any]:
        """
        Get cache performance metrics for the specified time period
        
        Args:
            hours: Number of hours to analyze
            
        Returns:
            Dictionary with cache performance analysis
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        with self._cache_lock:
            recent_metrics = [m for m in self._cache_metrics if m.timestamp >= cutoff_time]
        
        if not recent_metrics:
            return {
                'total_operations': 0,
                'hit_rate': 0.0,
                'average_operation_time_ms': 0.0,
                'cache_efficiency': 0.0,
                'memory_usage_trend': []
            }
        
        # Analyze cache performance
        hits = sum(1 for m in recent_metrics if m.operation == 'hit')
        misses = sum(1 for m in recent_metrics if m.operation == 'miss')
        total_ops = hits + misses
        
        hit_rate = hits / total_ops if total_ops > 0 else 0.0
        
        operation_times = [m.operation_time_ms for m in recent_metrics if m.operation_time_ms > 0]
        avg_operation_time = statistics.mean(operation_times) if operation_times else 0.0
        
        # Memory usage trend (sample every 10 minutes)
        memory_trend = []
        if recent_metrics:
            time_buckets = defaultdict(list)
            for metric in recent_metrics:
                bucket = metric.timestamp.replace(minute=(metric.timestamp.minute // 10) * 10, second=0, microsecond=0)
                time_buckets[bucket].append(metric.memory_usage_bytes)
            
            for timestamp in sorted(time_buckets.keys()):
                avg_memory = statistics.mean(time_buckets[timestamp])
                memory_trend.append({
                    'timestamp': timestamp.isoformat(),
                    'memory_usage_bytes': avg_memory
                })
        
        # Cache efficiency score
        latest_metric = recent_metrics[-1] if recent_metrics else None
        cache_efficiency = latest_metric.hit_rate if latest_metric else 0.0
        
        return {
            'total_operations': len(recent_metrics),
            'hit_rate': hit_rate,
            'average_operation_time_ms': avg_operation_time,
            'cache_efficiency': cache_efficiency,
            'memory_usage_trend': memory_trend,
            'operation_distribution': {
                'hits': hits,
                'misses': misses,
                'sets': sum(1 for m in recent_metrics if m.operation == 'set'),
                'invalidations': sum(1 for m in recent_metrics if m.operation == 'invalidate'),
                'evictions': sum(1 for m in recent_metrics if m.operation == 'evict')
            }
        }
    
    def get_change_frequency(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get configuration change frequency analysis
        
        Args:
            hours: Number of hours to analyze
            
        Returns:
            Dictionary with change frequency analysis
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        with self._change_lock:
            recent_changes = [m for m in self._change_metrics if m.timestamp >= cutoff_time]
        
        if not recent_changes:
            return {
                'total_changes': 0,
                'changes_per_hour': 0.0,
                'most_changed_keys': [],
                'change_sources': {},
                'restart_required_changes': 0,
                'impact_distribution': {}
            }
        
        # Analyze change patterns
        key_changes = defaultdict(int)
        source_changes = defaultdict(int)
        impact_changes = defaultdict(int)
        restart_required = 0
        
        for change in recent_changes:
            key_changes[change.key] += 1
            source_changes[change.source] += 1
            impact_changes[change.change_impact] += 1
            if change.requires_restart:
                restart_required += 1
        
        total_changes = len(recent_changes)
        changes_per_hour = total_changes / hours if hours > 0 else 0.0
        
        # Most changed keys
        most_changed = sorted(key_changes.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            'total_changes': total_changes,
            'changes_per_hour': changes_per_hour,
            'most_changed_keys': most_changed,
            'change_sources': dict(source_changes),
            'restart_required_changes': restart_required,
            'impact_distribution': dict(impact_changes),
            'change_timeline': [
                {
                    'timestamp': change.timestamp.isoformat(),
                    'key': change.key,
                    'impact': change.change_impact,
                    'requires_restart': change.requires_restart
                }
                for change in recent_changes[-20:]  # Last 20 changes
            ]
        }
    
    def get_performance_impact(self, hours: int = 1) -> Dict[str, Any]:
        """
        Get performance impact analysis
        
        Args:
            hours: Number of hours to analyze
            
        Returns:
            Dictionary with performance impact analysis
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        with self._performance_lock:
            recent_metrics = [m for m in self._performance_metrics if m.timestamp >= cutoff_time]
        
        with self._performance_lock_samples:
            recent_samples = [s for s in self._performance_samples 
                            if s['timestamp'] >= cutoff_time]
        
        if not recent_metrics and not recent_samples:
            return {
                'total_operations': 0,
                'average_duration_ms': 0.0,
                'performance_impact_score': 0.0,
                'memory_impact': 0,
                'cpu_impact': 0.0
            }
        
        # Analyze performance metrics
        durations = [m.duration_ms for m in recent_metrics]
        memory_deltas = [m.memory_delta_bytes for m in recent_metrics]
        cpu_usages = [m.cpu_usage_percent for m in recent_metrics if m.cpu_usage_percent > 0]
        
        avg_duration = statistics.mean(durations) if durations else 0.0
        total_memory_impact = sum(memory_deltas) if memory_deltas else 0
        avg_cpu_impact = statistics.mean(cpu_usages) if cpu_usages else 0.0
        
        # Performance impact score (0.0 to 1.0, lower is better)
        impact_score = 0.0
        if durations:
            # Normalize duration impact (anything over 100ms is concerning)
            duration_impact = min(1.0, avg_duration / 100.0)
            impact_score += duration_impact * 0.4
        
        if memory_deltas:
            # Normalize memory impact (anything over 10MB is concerning)
            memory_impact = min(1.0, abs(total_memory_impact) / (10 * 1024 * 1024))
            impact_score += memory_impact * 0.3
        
        if cpu_usages:
            # Normalize CPU impact (anything over 50% is concerning)
            cpu_impact = min(1.0, avg_cpu_impact / 50.0)
            impact_score += cpu_impact * 0.3
        
        return {
            'total_operations': len(recent_metrics),
            'average_duration_ms': avg_duration,
            'performance_impact_score': impact_score,
            'memory_impact_bytes': total_memory_impact,
            'cpu_impact_percent': avg_cpu_impact,
            'duration_percentiles': {
                'p50': statistics.median(durations) if durations else 0.0,
                'p95': statistics.quantiles(durations, n=20)[18] if len(durations) > 20 else 0.0,
                'p99': statistics.quantiles(durations, n=100)[98] if len(durations) > 100 else 0.0
            } if durations else {}
        }
    
    def get_comprehensive_summary(self, hours: int = 24) -> MetricsSummary:
        """
        Get comprehensive metrics summary
        
        Args:
            hours: Number of hours to analyze
            
        Returns:
            MetricsSummary object with all key metrics
        """
        access_patterns = self.get_access_patterns(hours)
        cache_performance = self.get_cache_performance(hours)
        change_frequency = self.get_change_frequency(hours)
        performance_impact = self.get_performance_impact(hours)
        
        with self._stats_lock:
            most_accessed = sorted(self._stats['key_access_counts'].items(), 
                                 key=lambda x: x[1], reverse=True)[:10]
            most_changed = sorted(self._stats['key_change_counts'].items(), 
                                key=lambda x: x[1], reverse=True)[:10]
        
        return MetricsSummary(
            total_accesses=access_patterns['total_accesses'],
            cache_hit_rate=cache_performance['hit_rate'],
            average_access_time_ms=access_patterns['average_access_time_ms'],
            total_changes=change_frequency['total_changes'],
            change_frequency_per_hour=change_frequency['changes_per_hour'],
            most_accessed_keys=most_accessed,
            most_changed_keys=most_changed,
            error_rate=access_patterns['error_rate'],
            performance_impact_score=performance_impact['performance_impact_score'],
            restart_required_changes=change_frequency['restart_required_changes']
        )
    
    def export_metrics(self, hours: int = 24, format: str = 'json') -> str:
        """
        Export metrics data for external analysis
        
        Args:
            hours: Number of hours of data to export
            format: Export format ('json' or 'csv')
            
        Returns:
            Exported data as string
        """
        summary = self.get_comprehensive_summary(hours)
        access_patterns = self.get_access_patterns(hours)
        cache_performance = self.get_cache_performance(hours)
        change_frequency = self.get_change_frequency(hours)
        performance_impact = self.get_performance_impact(hours)
        
        export_data = {
            'export_timestamp': datetime.now(timezone.utc).isoformat(),
            'time_period_hours': hours,
            'summary': {
                'total_accesses': summary.total_accesses,
                'cache_hit_rate': summary.cache_hit_rate,
                'average_access_time_ms': summary.average_access_time_ms,
                'total_changes': summary.total_changes,
                'change_frequency_per_hour': summary.change_frequency_per_hour,
                'error_rate': summary.error_rate,
                'performance_impact_score': summary.performance_impact_score
            },
            'access_patterns': access_patterns,
            'cache_performance': cache_performance,
            'change_frequency': change_frequency,
            'performance_impact': performance_impact
        }
        
        if format.lower() == 'json':
            return json.dumps(export_data, indent=2, default=str)
        else:
            # For CSV format, we'd need to flatten the data structure
            # This is a simplified version
            return f"Configuration Metrics Export - {export_data['export_timestamp']}\n" + \
                   f"Total Accesses: {summary.total_accesses}\n" + \
                   f"Cache Hit Rate: {summary.cache_hit_rate:.2%}\n" + \
                   f"Average Access Time: {summary.average_access_time_ms:.2f}ms\n"
    
    def _cleanup_old_metrics(self):
        """Background thread to clean up old metrics"""
        while True:
            try:
                time.sleep(3600)  # Run every hour
                
                cutoff_time = datetime.now(timezone.utc) - timedelta(hours=self.retention_hours)
                
                # Clean up access metrics
                with self._access_lock:
                    self._access_metrics = deque(
                        (m for m in self._access_metrics if m.timestamp >= cutoff_time),
                        maxlen=self.max_metrics_per_type
                    )
                
                # Clean up cache metrics
                with self._cache_lock:
                    self._cache_metrics = deque(
                        (m for m in self._cache_metrics if m.timestamp >= cutoff_time),
                        maxlen=self.max_metrics_per_type
                    )
                
                # Clean up change metrics
                with self._change_lock:
                    self._change_metrics = deque(
                        (m for m in self._change_metrics if m.timestamp >= cutoff_time),
                        maxlen=self.max_metrics_per_type
                    )
                
                # Clean up performance metrics
                with self._performance_lock:
                    self._performance_metrics = deque(
                        (m for m in self._performance_metrics if m.timestamp >= cutoff_time),
                        maxlen=self.max_metrics_per_type
                    )
                
                # Clean up performance samples
                with self._performance_lock_samples:
                    self._performance_samples = deque(
                        (s for s in self._performance_samples if s['timestamp'] >= cutoff_time),
                        maxlen=1000
                    )
                
                logger.debug("Completed metrics cleanup")
                
            except Exception as e:
                logger.error(f"Error during metrics cleanup: {str(e)}")
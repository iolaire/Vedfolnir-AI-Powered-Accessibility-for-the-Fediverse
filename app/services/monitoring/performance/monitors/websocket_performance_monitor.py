# Copyright (C) 2025 iolaire mcfadden.
# Consolidated WebSocket Performance Monitoring

import logging
import time
import json
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

class PerformanceMetricType(Enum):
    """Types of performance metrics"""
    CONNECTION_TIME = "connection_time"
    MESSAGE_LATENCY = "message_latency"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    MEMORY_USAGE = "memory_usage"
    CPU_USAGE = "cpu_usage"

@dataclass
class PerformanceMetric:
    """Performance metric data point"""
    metric_type: PerformanceMetricType
    value: float
    timestamp: datetime
    client_id: Optional[str] = None
    additional_data: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ConnectionStats:
    """Connection statistics"""
    client_id: str
    connect_time: datetime
    last_activity: datetime
    message_count: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    error_count: int = 0
    latency_samples: List[float] = field(default_factory=list)

class ConsolidatedWebSocketPerformanceMonitor:
    """Consolidated WebSocket performance monitoring with dashboard and optimization"""
    
    def __init__(self, config=None):
        self.logger = logging.getLogger(__name__)
        self.config = config or {}
        
        # Performance tracking
        self._metrics = defaultdict(deque)
        self._connection_stats = {}
        self._global_stats = {
            'total_connections': 0,
            'active_connections': 0,
            'total_messages': 0,
            'total_errors': 0,
            'start_time': datetime.utcnow()
        }
        
        # Performance thresholds
        self._thresholds = {
            'max_latency_ms': self.config.get('max_latency_ms', 1000),
            'max_error_rate': self.config.get('max_error_rate', 0.05),
            'max_memory_mb': self.config.get('max_memory_mb', 512),
            'max_cpu_percent': self.config.get('max_cpu_percent', 80)
        }
        
        # Monitoring settings
        self._monitoring_enabled = True
        self._metric_retention_hours = 24
        self._lock = threading.Lock()
    
    def record_connection(self, client_id: str) -> None:
        """Record new WebSocket connection"""
        try:
            with self._lock:
                now = datetime.utcnow()
                
                # Update global stats
                self._global_stats['total_connections'] += 1
                self._global_stats['active_connections'] += 1
                
                # Create connection stats
                self._connection_stats[client_id] = ConnectionStats(
                    client_id=client_id,
                    connect_time=now,
                    last_activity=now
                )
                
                # Record connection time metric
                self._record_metric(
                    PerformanceMetricType.CONNECTION_TIME,
                    time.time(),
                    client_id=client_id
                )
                
                self.logger.debug(f"Recorded connection for client: {client_id}")
                
        except Exception as e:
            self.logger.error(f"Error recording connection: {e}")
    
    def record_disconnection(self, client_id: str) -> None:
        """Record WebSocket disconnection"""
        try:
            with self._lock:
                if client_id in self._connection_stats:
                    # Update global stats
                    self._global_stats['active_connections'] -= 1
                    
                    # Calculate connection duration
                    stats = self._connection_stats[client_id]
                    duration = (datetime.utcnow() - stats.connect_time).total_seconds()
                    
                    self.logger.debug(
                        f"Client {client_id} disconnected after {duration:.2f}s, "
                        f"sent {stats.message_count} messages"
                    )
                    
                    # Remove connection stats
                    del self._connection_stats[client_id]
                
        except Exception as e:
            self.logger.error(f"Error recording disconnection: {e}")
    
    def record_message(self, client_id: str, message_size: int, latency_ms: Optional[float] = None) -> None:
        """Record WebSocket message"""
        try:
            with self._lock:
                now = datetime.utcnow()
                
                # Update global stats
                self._global_stats['total_messages'] += 1
                
                # Update connection stats
                if client_id in self._connection_stats:
                    stats = self._connection_stats[client_id]
                    stats.message_count += 1
                    stats.bytes_sent += message_size
                    stats.last_activity = now
                    
                    # Record latency if provided
                    if latency_ms is not None:
                        stats.latency_samples.append(latency_ms)
                        # Keep only recent samples
                        if len(stats.latency_samples) > 100:
                            stats.latency_samples = stats.latency_samples[-100:]
                        
                        # Record latency metric
                        self._record_metric(
                            PerformanceMetricType.MESSAGE_LATENCY,
                            latency_ms,
                            client_id=client_id
                        )
                
                # Record throughput metric
                self._record_metric(
                    PerformanceMetricType.THROUGHPUT,
                    message_size,
                    client_id=client_id
                )
                
        except Exception as e:
            self.logger.error(f"Error recording message: {e}")
    
    def record_error(self, client_id: str, error_type: str, error_message: str) -> None:
        """Record WebSocket error"""
        try:
            with self._lock:
                # Update global stats
                self._global_stats['total_errors'] += 1
                
                # Update connection stats
                if client_id in self._connection_stats:
                    self._connection_stats[client_id].error_count += 1
                
                # Calculate error rate
                total_messages = self._global_stats['total_messages']
                error_rate = self._global_stats['total_errors'] / max(total_messages, 1)
                
                # Record error rate metric
                self._record_metric(
                    PerformanceMetricType.ERROR_RATE,
                    error_rate,
                    client_id=client_id,
                    additional_data={'error_type': error_type, 'error_message': error_message}
                )
                
                self.logger.warning(f"WebSocket error for {client_id}: {error_type} - {error_message}")
                
        except Exception as e:
            self.logger.error(f"Error recording error: {e}")
    
    def _record_metric(self, metric_type: PerformanceMetricType, value: float, 
                      client_id: Optional[str] = None, additional_data: Optional[Dict[str, Any]] = None) -> None:
        """Record performance metric"""
        if not self._monitoring_enabled:
            return
        
        try:
            metric = PerformanceMetric(
                metric_type=metric_type,
                value=value,
                timestamp=datetime.utcnow(),
                client_id=client_id,
                additional_data=additional_data or {}
            )
            
            # Store metric
            self._metrics[metric_type].append(metric)
            
            # Limit metric storage
            max_metrics = 1000
            if len(self._metrics[metric_type]) > max_metrics:
                self._metrics[metric_type] = deque(
                    list(self._metrics[metric_type])[-max_metrics:],
                    maxlen=max_metrics
                )
            
        except Exception as e:
            self.logger.error(f"Error recording metric: {e}")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        try:
            with self._lock:
                now = datetime.utcnow()
                uptime = (now - self._global_stats['start_time']).total_seconds()
                
                # Calculate averages
                avg_latency = self._calculate_average_latency()
                current_error_rate = self._calculate_current_error_rate()
                messages_per_second = self._global_stats['total_messages'] / max(uptime, 1)
                
                # Get connection statistics
                connection_durations = []
                total_message_count = 0
                
                for stats in self._connection_stats.values():
                    duration = (now - stats.connect_time).total_seconds()
                    connection_durations.append(duration)
                    total_message_count += stats.message_count
                
                avg_connection_duration = (
                    sum(connection_durations) / len(connection_durations)
                    if connection_durations else 0
                )
                
                return {
                    'timestamp': now.isoformat(),
                    'uptime_seconds': uptime,
                    'global_stats': {
                        'total_connections': self._global_stats['total_connections'],
                        'active_connections': self._global_stats['active_connections'],
                        'total_messages': self._global_stats['total_messages'],
                        'total_errors': self._global_stats['total_errors'],
                        'messages_per_second': round(messages_per_second, 2),
                        'error_rate': round(current_error_rate, 4)
                    },
                    'performance_metrics': {
                        'average_latency_ms': round(avg_latency, 2),
                        'average_connection_duration_s': round(avg_connection_duration, 2),
                        'total_message_count': total_message_count
                    },
                    'health_status': self._get_health_status(),
                    'thresholds': self._thresholds
                }
                
        except Exception as e:
            self.logger.error(f"Error getting performance summary: {e}")
            return {'error': str(e)}
    
    def get_client_stats(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for specific client"""
        try:
            with self._lock:
                if client_id not in self._connection_stats:
                    return None
                
                stats = self._connection_stats[client_id]
                now = datetime.utcnow()
                
                # Calculate client-specific metrics
                connection_duration = (now - stats.connect_time).total_seconds()
                avg_latency = sum(stats.latency_samples) / len(stats.latency_samples) if stats.latency_samples else 0
                
                return {
                    'client_id': client_id,
                    'connect_time': stats.connect_time.isoformat(),
                    'connection_duration_s': round(connection_duration, 2),
                    'last_activity': stats.last_activity.isoformat(),
                    'message_count': stats.message_count,
                    'bytes_sent': stats.bytes_sent,
                    'bytes_received': stats.bytes_received,
                    'error_count': stats.error_count,
                    'average_latency_ms': round(avg_latency, 2),
                    'messages_per_minute': round(stats.message_count / max(connection_duration / 60, 1), 2)
                }
                
        except Exception as e:
            self.logger.error(f"Error getting client stats: {e}")
            return None
    
    def _calculate_average_latency(self) -> float:
        """Calculate average latency across all connections"""
        try:
            all_latencies = []
            for stats in self._connection_stats.values():
                all_latencies.extend(stats.latency_samples)
            
            return sum(all_latencies) / len(all_latencies) if all_latencies else 0
            
        except Exception:
            return 0
    
    def _calculate_current_error_rate(self) -> float:
        """Calculate current error rate"""
        try:
            total_messages = self._global_stats['total_messages']
            total_errors = self._global_stats['total_errors']
            
            return total_errors / max(total_messages, 1)
            
        except Exception:
            return 0
    
    def _get_health_status(self) -> Dict[str, Any]:
        """Get health status based on thresholds"""
        try:
            avg_latency = self._calculate_average_latency()
            error_rate = self._calculate_current_error_rate()
            
            issues = []
            
            # Check latency threshold
            if avg_latency > self._thresholds['max_latency_ms']:
                issues.append(f"High latency: {avg_latency:.2f}ms > {self._thresholds['max_latency_ms']}ms")
            
            # Check error rate threshold
            if error_rate > self._thresholds['max_error_rate']:
                issues.append(f"High error rate: {error_rate:.4f} > {self._thresholds['max_error_rate']}")
            
            status = 'healthy' if not issues else 'degraded' if len(issues) < 3 else 'unhealthy'
            
            return {
                'status': status,
                'issues': issues,
                'checks_passed': {
                    'latency_ok': avg_latency <= self._thresholds['max_latency_ms'],
                    'error_rate_ok': error_rate <= self._thresholds['max_error_rate']
                }
            }
            
        except Exception as e:
            return {'status': 'unknown', 'error': str(e)}
    
    def cleanup_old_metrics(self) -> None:
        """Clean up old performance metrics"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=self._metric_retention_hours)
            
            with self._lock:
                for metric_type in self._metrics:
                    # Remove old metrics
                    metrics = self._metrics[metric_type]
                    while metrics and metrics[0].timestamp < cutoff_time:
                        metrics.popleft()
                
                self.logger.debug("Cleaned up old performance metrics")
                
        except Exception as e:
            self.logger.error(f"Error cleaning up metrics: {e}")
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data for performance dashboard"""
        try:
            summary = self.get_performance_summary()
            
            # Get recent metrics for charts
            recent_metrics = {}
            for metric_type in PerformanceMetricType:
                recent_metrics[metric_type.value] = [
                    {
                        'timestamp': metric.timestamp.isoformat(),
                        'value': metric.value,
                        'client_id': metric.client_id
                    }
                    for metric in list(self._metrics[metric_type])[-50:]  # Last 50 data points
                ]
            
            return {
                'summary': summary,
                'metrics': recent_metrics,
                'active_connections': len(self._connection_stats),
                'connection_list': [
                    self.get_client_stats(client_id)
                    for client_id in list(self._connection_stats.keys())[:20]  # Top 20 connections
                ]
            }
            
        except Exception as e:
            self.logger.error(f"Error getting dashboard data: {e}")
            return {'error': str(e)}

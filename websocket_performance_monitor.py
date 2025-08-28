# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
WebSocket Performance Monitor

Provides comprehensive performance monitoring and optimization for WebSocket connections,
including connection pool monitoring, message delivery metrics, and adaptive behavior
under varying load conditions.
"""

import time
import json
import threading
import psutil
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Callable, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
from collections import deque, defaultdict
import statistics
from websocket_debug_logger import get_debug_logger, DebugLevel


class PerformanceLevel(Enum):
    """Performance level indicators"""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    CRITICAL = "critical"


class LoadLevel(Enum):
    """System load level indicators"""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    OVERLOAD = "overload"


@dataclass
class ConnectionPoolMetrics:
    """Connection pool performance metrics"""
    total_connections: int
    active_connections: int
    idle_connections: int
    peak_connections: int
    connection_creation_rate: float
    connection_destruction_rate: float
    avg_connection_lifetime: float
    pool_utilization: float
    timestamp: datetime


@dataclass
class MessageDeliveryMetrics:
    """Message delivery performance metrics"""
    messages_sent: int
    messages_received: int
    messages_per_second: float
    avg_message_size: float
    avg_delivery_time: float
    failed_deliveries: int
    retry_count: int
    queue_depth: int
    timestamp: datetime


@dataclass
class ResourceUsageMetrics:
    """System resource usage metrics"""
    cpu_usage: float
    memory_usage: float
    memory_available: float
    network_io_sent: int
    network_io_received: int
    disk_io_read: int
    disk_io_write: int
    open_file_descriptors: int
    timestamp: datetime


@dataclass
class ConnectionQualityMetrics:
    """Connection quality metrics"""
    avg_latency: float
    packet_loss_rate: float
    jitter: float
    bandwidth_utilization: float
    error_rate: float
    reconnection_rate: float
    transport_efficiency: float
    timestamp: datetime


class WebSocketPerformanceMonitor:
    """Comprehensive WebSocket performance monitoring system"""
    
    def __init__(self, monitoring_interval: int = 30):
        self.monitoring_interval = monitoring_interval
        self.logger = get_debug_logger('performance_monitor', DebugLevel.INFO)
        
        # Performance metrics storage
        self.connection_pool_metrics = deque(maxlen=1000)
        self.message_delivery_metrics = deque(maxlen=1000)
        self.resource_usage_metrics = deque(maxlen=1000)
        self.connection_quality_metrics = deque(maxlen=1000)
        
        # Real-time tracking
        self.active_connections = {}
        self.message_queue = deque()
        self.delivery_times = deque(maxlen=1000)
        self.connection_events = deque(maxlen=5000)
        
        # Performance thresholds
        self.thresholds = {
            'cpu_usage_warning': 70.0,
            'cpu_usage_critical': 90.0,
            'memory_usage_warning': 80.0,
            'memory_usage_critical': 95.0,
            'avg_latency_warning': 100.0,  # ms
            'avg_latency_critical': 500.0,  # ms
            'error_rate_warning': 0.05,    # 5%
            'error_rate_critical': 0.15,   # 15%
            'connection_pool_warning': 0.8, # 80% utilization
            'connection_pool_critical': 0.95 # 95% utilization
        }
        
        # Adaptive behavior settings
        self.adaptive_settings = {
            'max_connections': 1000,
            'message_batch_size': 10,
            'connection_timeout': 30,
            'retry_attempts': 3,
            'backoff_multiplier': 2.0
        }
        
        # Monitoring thread
        self.monitoring_active = False
        self.monitoring_thread = None
        
        # Performance callbacks
        self.performance_callbacks = []
        self.threshold_callbacks = []
        
        # Statistics
        self.stats = {
            'total_connections_created': 0,
            'total_connections_destroyed': 0,
            'total_messages_processed': 0,
            'total_errors': 0,
            'uptime_start': datetime.now(timezone.utc)
        }
        
    def start_monitoring(self):
        """Start performance monitoring"""
        if self.monitoring_active:
            self.logger.warning("Performance monitoring is already active")
            return
            
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        
        self.logger.info(f"Started WebSocket performance monitoring (interval: {self.monitoring_interval}s)")
        
    def stop_monitoring(self):
        """Stop performance monitoring"""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
            
        self.logger.info("Stopped WebSocket performance monitoring")
        
    def register_connection(self, connection_id: str, connection_info: Dict[str, Any]):
        """Register a new connection for monitoring"""
        self.active_connections[connection_id] = {
            'id': connection_id,
            'created_at': datetime.now(timezone.utc),
            'last_activity': datetime.now(timezone.utc),
            'messages_sent': 0,
            'messages_received': 0,
            'bytes_sent': 0,
            'bytes_received': 0,
            'errors': 0,
            'latency_samples': deque(maxlen=100),
            **connection_info
        }
        
        self.stats['total_connections_created'] += 1
        self._record_connection_event('connection_created', connection_id)
        
    def unregister_connection(self, connection_id: str, reason: str = 'disconnect'):
        """Unregister a connection"""
        if connection_id in self.active_connections:
            connection = self.active_connections[connection_id]
            connection['disconnected_at'] = datetime.now(timezone.utc)
            connection['disconnect_reason'] = reason
            
            # Calculate connection lifetime
            lifetime = (connection['disconnected_at'] - connection['created_at']).total_seconds()
            connection['lifetime'] = lifetime
            
            del self.active_connections[connection_id]
            self.stats['total_connections_destroyed'] += 1
            self._record_connection_event('connection_destroyed', connection_id, {'reason': reason, 'lifetime': lifetime})
            
    def record_message_sent(self, connection_id: str, message_size: int, delivery_time: float = None):
        """Record a message sent"""
        if connection_id in self.active_connections:
            conn = self.active_connections[connection_id]
            conn['messages_sent'] += 1
            conn['bytes_sent'] += message_size
            conn['last_activity'] = datetime.now(timezone.utc)
            
        if delivery_time is not None:
            self.delivery_times.append(delivery_time)
            
        self.stats['total_messages_processed'] += 1
        self._record_message_event('message_sent', connection_id, message_size, delivery_time)
        
    def record_message_received(self, connection_id: str, message_size: int):
        """Record a message received"""
        if connection_id in self.active_connections:
            conn = self.active_connections[connection_id]
            conn['messages_received'] += 1
            conn['bytes_received'] += message_size
            conn['last_activity'] = datetime.now(timezone.utc)
            
        self.stats['total_messages_processed'] += 1
        self._record_message_event('message_received', connection_id, message_size)
        
    def record_latency_sample(self, connection_id: str, latency: float):
        """Record a latency sample for a connection"""
        if connection_id in self.active_connections:
            conn = self.active_connections[connection_id]
            conn['latency_samples'].append(latency)
            
    def record_error(self, connection_id: str, error_type: str, error_details: Dict[str, Any] = None):
        """Record an error"""
        if connection_id in self.active_connections:
            self.active_connections[connection_id]['errors'] += 1
            
        self.stats['total_errors'] += 1
        self._record_connection_event('error', connection_id, {'type': error_type, 'details': error_details})
        
    def get_current_performance_summary(self) -> Dict[str, Any]:
        """Get current performance summary"""
        now = datetime.now(timezone.utc)
        
        # Connection pool metrics
        total_connections = len(self.active_connections)
        active_connections = sum(1 for conn in self.active_connections.values() 
                               if (now - conn['last_activity']).total_seconds() < 300)
        
        # Message delivery metrics
        recent_delivery_times = [dt for dt in self.delivery_times if dt is not None]
        avg_delivery_time = statistics.mean(recent_delivery_times) if recent_delivery_times else 0
        
        # Resource usage
        resource_metrics = self._collect_resource_metrics()
        
        # Connection quality
        all_latency_samples = []
        for conn in self.active_connections.values():
            all_latency_samples.extend(conn['latency_samples'])
            
        avg_latency = statistics.mean(all_latency_samples) if all_latency_samples else 0
        
        # Calculate performance level
        performance_level = self._calculate_performance_level(resource_metrics, avg_latency, avg_delivery_time)
        
        return {
            'timestamp': now.isoformat(),
            'performance_level': performance_level.value,
            'connection_pool': {
                'total_connections': total_connections,
                'active_connections': active_connections,
                'peak_connections': max(self.stats['total_connections_created'] - self.stats['total_connections_destroyed'], 0),
                'utilization': total_connections / self.adaptive_settings['max_connections']
            },
            'message_delivery': {
                'avg_delivery_time': avg_delivery_time,
                'messages_per_second': self._calculate_message_rate(),
                'total_messages': self.stats['total_messages_processed']
            },
            'resource_usage': {
                'cpu_usage': resource_metrics.cpu_usage,
                'memory_usage': resource_metrics.memory_usage,
                'memory_available': resource_metrics.memory_available
            },
            'connection_quality': {
                'avg_latency': avg_latency,
                'error_rate': self._calculate_error_rate(),
                'total_errors': self.stats['total_errors']
            },
            'uptime': (now - self.stats['uptime_start']).total_seconds()
        }
        
    def get_performance_history(self, hours: int = 24) -> Dict[str, List[Dict]]:
        """Get performance history"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        return {
            'connection_pool': [
                asdict(metric) for metric in self.connection_pool_metrics
                if metric.timestamp > cutoff_time
            ],
            'message_delivery': [
                asdict(metric) for metric in self.message_delivery_metrics
                if metric.timestamp > cutoff_time
            ],
            'resource_usage': [
                asdict(metric) for metric in self.resource_usage_metrics
                if metric.timestamp > cutoff_time
            ],
            'connection_quality': [
                asdict(metric) for metric in self.connection_quality_metrics
                if metric.timestamp > cutoff_time
            ]
        }
        
    def get_scalability_metrics(self) -> Dict[str, Any]:
        """Get scalability-related metrics"""
        current_load = self._assess_current_load()
        
        # Calculate theoretical maximum capacity
        current_performance = self.get_current_performance_summary()
        cpu_headroom = max(0, 100 - current_performance['resource_usage']['cpu_usage'])
        memory_headroom = max(0, 100 - current_performance['resource_usage']['memory_usage'])
        
        # Estimate scaling capacity
        cpu_scaling_factor = cpu_headroom / 100
        memory_scaling_factor = memory_headroom / 100
        scaling_factor = min(cpu_scaling_factor, memory_scaling_factor)
        
        estimated_max_connections = int(current_performance['connection_pool']['total_connections'] * (1 + scaling_factor * 2))
        
        return {
            'current_load_level': current_load.value,
            'current_connections': current_performance['connection_pool']['total_connections'],
            'estimated_max_connections': estimated_max_connections,
            'scaling_factor': scaling_factor,
            'resource_headroom': {
                'cpu': cpu_headroom,
                'memory': memory_headroom
            },
            'bottlenecks': self._identify_bottlenecks(current_performance),
            'scaling_recommendations': self._generate_scaling_recommendations(current_performance, current_load)
        }
        
    def optimize_performance(self) -> Dict[str, Any]:
        """Perform automatic performance optimization"""
        current_performance = self.get_current_performance_summary()
        current_load = self._assess_current_load()
        
        optimizations_applied = []
        
        # Adjust connection limits based on load
        if current_load == LoadLevel.HIGH:
            old_max = self.adaptive_settings['max_connections']
            self.adaptive_settings['max_connections'] = int(old_max * 0.9)
            optimizations_applied.append(f"Reduced max connections from {old_max} to {self.adaptive_settings['max_connections']}")
            
        elif current_load == LoadLevel.LOW:
            old_max = self.adaptive_settings['max_connections']
            self.adaptive_settings['max_connections'] = min(int(old_max * 1.1), 2000)
            optimizations_applied.append(f"Increased max connections from {old_max} to {self.adaptive_settings['max_connections']}")
            
        # Adjust message batching based on delivery performance
        avg_delivery_time = current_performance['message_delivery']['avg_delivery_time']
        if avg_delivery_time > 100:  # ms
            old_batch = self.adaptive_settings['message_batch_size']
            self.adaptive_settings['message_batch_size'] = max(1, int(old_batch * 0.8))
            optimizations_applied.append(f"Reduced message batch size from {old_batch} to {self.adaptive_settings['message_batch_size']}")
            
        elif avg_delivery_time < 50:  # ms
            old_batch = self.adaptive_settings['message_batch_size']
            self.adaptive_settings['message_batch_size'] = min(int(old_batch * 1.2), 50)
            optimizations_applied.append(f"Increased message batch size from {old_batch} to {self.adaptive_settings['message_batch_size']}")
            
        # Adjust timeouts based on connection quality
        error_rate = current_performance['connection_quality']['error_rate']
        if error_rate > 0.1:  # 10%
            old_timeout = self.adaptive_settings['connection_timeout']
            self.adaptive_settings['connection_timeout'] = min(int(old_timeout * 1.5), 120)
            optimizations_applied.append(f"Increased connection timeout from {old_timeout}s to {self.adaptive_settings['connection_timeout']}s")
            
        # Adjust retry settings based on error patterns
        if error_rate > 0.05:  # 5%
            old_attempts = self.adaptive_settings['retry_attempts']
            self.adaptive_settings['retry_attempts'] = min(old_attempts + 1, 5)
            optimizations_applied.append(f"Increased retry attempts from {old_attempts} to {self.adaptive_settings['retry_attempts']}")
            
        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'optimizations_applied': optimizations_applied,
            'current_settings': self.adaptive_settings.copy(),
            'performance_level': current_performance['performance_level'],
            'load_level': current_load.value
        }
        
    def implement_graceful_degradation(self, load_level: LoadLevel) -> Dict[str, Any]:
        """Implement graceful degradation under high load"""
        degradation_actions = []
        
        if load_level == LoadLevel.HIGH:
            # Reduce connection limits
            self.adaptive_settings['max_connections'] = int(self.adaptive_settings['max_connections'] * 0.8)
            degradation_actions.append("Reduced connection limits by 20%")
            
            # Increase connection timeout to reduce churn
            self.adaptive_settings['connection_timeout'] = min(self.adaptive_settings['connection_timeout'] * 2, 120)
            degradation_actions.append("Doubled connection timeout")
            
            # Reduce message batch size for faster processing
            self.adaptive_settings['message_batch_size'] = max(1, self.adaptive_settings['message_batch_size'] // 2)
            degradation_actions.append("Halved message batch size")
            
        elif load_level == LoadLevel.OVERLOAD:
            # Emergency measures
            self.adaptive_settings['max_connections'] = int(self.adaptive_settings['max_connections'] * 0.5)
            degradation_actions.append("Emergency: Reduced connection limits by 50%")
            
            # Disable non-essential features
            degradation_actions.append("Disabled non-essential monitoring features")
            
            # Prioritize existing connections
            degradation_actions.append("Prioritizing existing connections over new ones")
            
        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'load_level': load_level.value,
            'degradation_actions': degradation_actions,
            'new_settings': self.adaptive_settings.copy()
        }
        
    def add_performance_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Add callback for performance updates"""
        self.performance_callbacks.append(callback)
        
    def add_threshold_callback(self, callback: Callable[[str, float, float], None]):
        """Add callback for threshold violations"""
        self.threshold_callbacks.append(callback)
        
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                # Collect all metrics
                connection_pool_metrics = self._collect_connection_pool_metrics()
                message_delivery_metrics = self._collect_message_delivery_metrics()
                resource_usage_metrics = self._collect_resource_metrics()
                connection_quality_metrics = self._collect_connection_quality_metrics()
                
                # Store metrics
                self.connection_pool_metrics.append(connection_pool_metrics)
                self.message_delivery_metrics.append(message_delivery_metrics)
                self.resource_usage_metrics.append(resource_usage_metrics)
                self.connection_quality_metrics.append(connection_quality_metrics)
                
                # Check thresholds
                self._check_performance_thresholds(resource_usage_metrics, connection_quality_metrics)
                
                # Trigger performance callbacks
                performance_summary = self.get_current_performance_summary()
                for callback in self.performance_callbacks:
                    try:
                        callback(performance_summary)
                    except Exception as e:
                        self.logger.error(f"Performance callback failed: {e}")
                        
                # Auto-optimization if enabled
                current_load = self._assess_current_load()
                if current_load in [LoadLevel.HIGH, LoadLevel.OVERLOAD]:
                    self.optimize_performance()
                    
                # Sleep until next monitoring cycle
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                self.logger.error(f"Error in performance monitoring loop: {e}")
                time.sleep(10)  # Wait before retrying
                
    def _collect_connection_pool_metrics(self) -> ConnectionPoolMetrics:
        """Collect connection pool metrics"""
        now = datetime.now(timezone.utc)
        total_connections = len(self.active_connections)
        
        # Calculate active connections (activity within last 5 minutes)
        active_connections = sum(1 for conn in self.active_connections.values() 
                               if (now - conn['last_activity']).total_seconds() < 300)
        idle_connections = total_connections - active_connections
        
        # Calculate rates from recent events
        recent_events = [event for event in self.connection_events 
                        if (now - event['timestamp']).total_seconds() < 60]
        
        creation_events = [e for e in recent_events if e['type'] == 'connection_created']
        destruction_events = [e for e in recent_events if e['type'] == 'connection_destroyed']
        
        creation_rate = len(creation_events) / 60.0  # per second
        destruction_rate = len(destruction_events) / 60.0  # per second
        
        # Calculate average connection lifetime
        lifetimes = [e['data']['lifetime'] for e in destruction_events if 'lifetime' in e.get('data', {})]
        avg_lifetime = statistics.mean(lifetimes) if lifetimes else 0
        
        # Calculate pool utilization
        pool_utilization = total_connections / self.adaptive_settings['max_connections']
        
        return ConnectionPoolMetrics(
            total_connections=total_connections,
            active_connections=active_connections,
            idle_connections=idle_connections,
            peak_connections=max(self.stats['total_connections_created'] - self.stats['total_connections_destroyed'], 0),
            connection_creation_rate=creation_rate,
            connection_destruction_rate=destruction_rate,
            avg_connection_lifetime=avg_lifetime,
            pool_utilization=pool_utilization,
            timestamp=now
        )
        
    def _collect_message_delivery_metrics(self) -> MessageDeliveryMetrics:
        """Collect message delivery metrics"""
        now = datetime.now(timezone.utc)
        
        # Get recent message events
        recent_events = [event for event in self.connection_events 
                        if (now - event['timestamp']).total_seconds() < 60 and 
                        event['type'] in ['message_sent', 'message_received']]
        
        sent_events = [e for e in recent_events if e['type'] == 'message_sent']
        received_events = [e for e in recent_events if e['type'] == 'message_received']
        
        messages_sent = len(sent_events)
        messages_received = len(received_events)
        messages_per_second = (messages_sent + messages_received) / 60.0
        
        # Calculate average message size
        message_sizes = [e['data']['size'] for e in recent_events if 'size' in e.get('data', {})]
        avg_message_size = statistics.mean(message_sizes) if message_sizes else 0
        
        # Calculate average delivery time
        delivery_times = [e['data']['delivery_time'] for e in sent_events 
                         if 'delivery_time' in e.get('data', {}) and e['data']['delivery_time'] is not None]
        avg_delivery_time = statistics.mean(delivery_times) if delivery_times else 0
        
        return MessageDeliveryMetrics(
            messages_sent=messages_sent,
            messages_received=messages_received,
            messages_per_second=messages_per_second,
            avg_message_size=avg_message_size,
            avg_delivery_time=avg_delivery_time,
            failed_deliveries=0,  # Would need to track this separately
            retry_count=0,        # Would need to track this separately
            queue_depth=len(self.message_queue),
            timestamp=now
        )
        
    def _collect_resource_metrics(self) -> ResourceUsageMetrics:
        """Collect system resource metrics"""
        try:
            # CPU usage
            cpu_usage = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_usage = memory.percent
            memory_available = memory.available
            
            # Network I/O
            network_io = psutil.net_io_counters()
            network_io_sent = network_io.bytes_sent
            network_io_received = network_io.bytes_recv
            
            # Disk I/O
            disk_io = psutil.disk_io_counters()
            disk_io_read = disk_io.read_bytes if disk_io else 0
            disk_io_write = disk_io.write_bytes if disk_io else 0
            
            # File descriptors
            process = psutil.Process()
            open_fds = process.num_fds() if hasattr(process, 'num_fds') else 0
            
            return ResourceUsageMetrics(
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                memory_available=memory_available,
                network_io_sent=network_io_sent,
                network_io_received=network_io_received,
                disk_io_read=disk_io_read,
                disk_io_write=disk_io_write,
                open_file_descriptors=open_fds,
                timestamp=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            self.logger.error(f"Error collecting resource metrics: {e}")
            return ResourceUsageMetrics(
                cpu_usage=0, memory_usage=0, memory_available=0,
                network_io_sent=0, network_io_received=0,
                disk_io_read=0, disk_io_write=0,
                open_file_descriptors=0,
                timestamp=datetime.now(timezone.utc)
            )
            
    def _collect_connection_quality_metrics(self) -> ConnectionQualityMetrics:
        """Collect connection quality metrics"""
        now = datetime.now(timezone.utc)
        
        # Collect latency samples from all connections
        all_latency_samples = []
        for conn in self.active_connections.values():
            all_latency_samples.extend(conn['latency_samples'])
            
        avg_latency = statistics.mean(all_latency_samples) if all_latency_samples else 0
        
        # Calculate jitter (latency variation)
        jitter = statistics.stdev(all_latency_samples) if len(all_latency_samples) > 1 else 0
        
        # Calculate error rate
        error_rate = self._calculate_error_rate()
        
        # Calculate reconnection rate
        recent_events = [event for event in self.connection_events 
                        if (now - event['timestamp']).total_seconds() < 300]  # 5 minutes
        reconnection_events = [e for e in recent_events if e['type'] == 'connection_created']
        reconnection_rate = len(reconnection_events) / 300.0  # per second
        
        return ConnectionQualityMetrics(
            avg_latency=avg_latency,
            packet_loss_rate=0.0,  # Would need network-level monitoring
            jitter=jitter,
            bandwidth_utilization=0.0,  # Would need network-level monitoring
            error_rate=error_rate,
            reconnection_rate=reconnection_rate,
            transport_efficiency=1.0 - error_rate,  # Simplified calculation
            timestamp=now
        )
        
    def _calculate_performance_level(self, resource_metrics: ResourceUsageMetrics, 
                                   avg_latency: float, avg_delivery_time: float) -> PerformanceLevel:
        """Calculate overall performance level"""
        # Score based on different factors (0-100)
        cpu_score = max(0, 100 - resource_metrics.cpu_usage)
        memory_score = max(0, 100 - resource_metrics.memory_usage)
        latency_score = max(0, 100 - min(avg_latency / 10, 100))  # 1000ms = 0 score
        delivery_score = max(0, 100 - min(avg_delivery_time / 10, 100))  # 1000ms = 0 score
        
        overall_score = (cpu_score + memory_score + latency_score + delivery_score) / 4
        
        if overall_score >= 90:
            return PerformanceLevel.EXCELLENT
        elif overall_score >= 75:
            return PerformanceLevel.GOOD
        elif overall_score >= 60:
            return PerformanceLevel.FAIR
        elif overall_score >= 40:
            return PerformanceLevel.POOR
        else:
            return PerformanceLevel.CRITICAL
            
    def _assess_current_load(self) -> LoadLevel:
        """Assess current system load level"""
        resource_metrics = self._collect_resource_metrics()
        connection_metrics = self._collect_connection_pool_metrics()
        
        # Calculate load factors
        cpu_load = resource_metrics.cpu_usage / 100
        memory_load = resource_metrics.memory_usage / 100
        connection_load = connection_metrics.pool_utilization
        
        max_load = max(cpu_load, memory_load, connection_load)
        
        if max_load >= 0.9:
            return LoadLevel.OVERLOAD
        elif max_load >= 0.7:
            return LoadLevel.HIGH
        elif max_load >= 0.4:
            return LoadLevel.MODERATE
        else:
            return LoadLevel.LOW
            
    def _calculate_message_rate(self) -> float:
        """Calculate current message rate"""
        now = datetime.now(timezone.utc)
        recent_events = [event for event in self.connection_events 
                        if (now - event['timestamp']).total_seconds() < 60 and 
                        event['type'] in ['message_sent', 'message_received']]
        return len(recent_events) / 60.0
        
    def _calculate_error_rate(self) -> float:
        """Calculate current error rate"""
        now = datetime.now(timezone.utc)
        recent_events = [event for event in self.connection_events 
                        if (now - event['timestamp']).total_seconds() < 300]  # 5 minutes
        
        total_events = len(recent_events)
        error_events = len([e for e in recent_events if e['type'] == 'error'])
        
        return error_events / total_events if total_events > 0 else 0
        
    def _identify_bottlenecks(self, performance_summary: Dict[str, Any]) -> List[str]:
        """Identify performance bottlenecks"""
        bottlenecks = []
        
        # CPU bottleneck
        if performance_summary['resource_usage']['cpu_usage'] > self.thresholds['cpu_usage_warning']:
            bottlenecks.append("High CPU usage")
            
        # Memory bottleneck
        if performance_summary['resource_usage']['memory_usage'] > self.thresholds['memory_usage_warning']:
            bottlenecks.append("High memory usage")
            
        # Latency bottleneck
        if performance_summary['connection_quality']['avg_latency'] > self.thresholds['avg_latency_warning']:
            bottlenecks.append("High connection latency")
            
        # Connection pool bottleneck
        if performance_summary['connection_pool']['utilization'] > self.thresholds['connection_pool_warning']:
            bottlenecks.append("Connection pool near capacity")
            
        # Error rate bottleneck
        if performance_summary['connection_quality']['error_rate'] > self.thresholds['error_rate_warning']:
            bottlenecks.append("High error rate")
            
        return bottlenecks
        
    def _generate_scaling_recommendations(self, performance_summary: Dict[str, Any], 
                                        load_level: LoadLevel) -> List[str]:
        """Generate scaling recommendations"""
        recommendations = []
        
        if load_level == LoadLevel.HIGH:
            recommendations.append("Consider horizontal scaling - add more application instances")
            recommendations.append("Increase connection pool limits")
            recommendations.append("Optimize message batching")
            
        elif load_level == LoadLevel.OVERLOAD:
            recommendations.append("URGENT: Scale horizontally immediately")
            recommendations.append("Implement load balancing")
            recommendations.append("Consider connection throttling")
            
        elif load_level == LoadLevel.LOW:
            recommendations.append("System has capacity for more connections")
            recommendations.append("Consider reducing resource allocation if cost is a concern")
            
        # Specific bottleneck recommendations
        bottlenecks = self._identify_bottlenecks(performance_summary)
        for bottleneck in bottlenecks:
            if "CPU" in bottleneck:
                recommendations.append("Optimize CPU-intensive operations")
            elif "memory" in bottleneck:
                recommendations.append("Optimize memory usage or increase available memory")
            elif "latency" in bottleneck:
                recommendations.append("Investigate network issues or optimize message handling")
                
        return recommendations
        
    def _check_performance_thresholds(self, resource_metrics: ResourceUsageMetrics, 
                                    quality_metrics: ConnectionQualityMetrics):
        """Check performance thresholds and trigger alerts"""
        # CPU threshold check
        if resource_metrics.cpu_usage > self.thresholds['cpu_usage_critical']:
            self._trigger_threshold_alert('cpu_usage_critical', resource_metrics.cpu_usage, 
                                         self.thresholds['cpu_usage_critical'])
        elif resource_metrics.cpu_usage > self.thresholds['cpu_usage_warning']:
            self._trigger_threshold_alert('cpu_usage_warning', resource_metrics.cpu_usage, 
                                         self.thresholds['cpu_usage_warning'])
            
        # Memory threshold check
        if resource_metrics.memory_usage > self.thresholds['memory_usage_critical']:
            self._trigger_threshold_alert('memory_usage_critical', resource_metrics.memory_usage, 
                                         self.thresholds['memory_usage_critical'])
        elif resource_metrics.memory_usage > self.thresholds['memory_usage_warning']:
            self._trigger_threshold_alert('memory_usage_warning', resource_metrics.memory_usage, 
                                         self.thresholds['memory_usage_warning'])
            
        # Latency threshold check
        if quality_metrics.avg_latency > self.thresholds['avg_latency_critical']:
            self._trigger_threshold_alert('avg_latency_critical', quality_metrics.avg_latency, 
                                         self.thresholds['avg_latency_critical'])
        elif quality_metrics.avg_latency > self.thresholds['avg_latency_warning']:
            self._trigger_threshold_alert('avg_latency_warning', quality_metrics.avg_latency, 
                                         self.thresholds['avg_latency_warning'])
            
        # Error rate threshold check
        if quality_metrics.error_rate > self.thresholds['error_rate_critical']:
            self._trigger_threshold_alert('error_rate_critical', quality_metrics.error_rate, 
                                         self.thresholds['error_rate_critical'])
        elif quality_metrics.error_rate > self.thresholds['error_rate_warning']:
            self._trigger_threshold_alert('error_rate_warning', quality_metrics.error_rate, 
                                         self.thresholds['error_rate_warning'])
            
    def _trigger_threshold_alert(self, threshold_name: str, current_value: float, threshold_value: float):
        """Trigger threshold alert callbacks"""
        for callback in self.threshold_callbacks:
            try:
                callback(threshold_name, current_value, threshold_value)
            except Exception as e:
                self.logger.error(f"Threshold callback failed: {e}")
                
    def _record_connection_event(self, event_type: str, connection_id: str, data: Dict[str, Any] = None):
        """Record a connection event"""
        event = {
            'timestamp': datetime.now(timezone.utc),
            'type': event_type,
            'connection_id': connection_id,
            'data': data or {}
        }
        self.connection_events.append(event)
        
    def _record_message_event(self, event_type: str, connection_id: str, size: int, delivery_time: float = None):
        """Record a message event"""
        data = {'size': size}
        if delivery_time is not None:
            data['delivery_time'] = delivery_time
            
        self._record_connection_event(event_type, connection_id, data)


def create_performance_monitor(monitoring_interval: int = 30) -> WebSocketPerformanceMonitor:
    """Create a WebSocket performance monitor instance"""
    return WebSocketPerformanceMonitor(monitoring_interval)


def setup_performance_monitoring(socketio_instance, performance_monitor: WebSocketPerformanceMonitor):
    """Set up performance monitoring for a SocketIO instance"""
    
    @socketio_instance.on('connect')
    def handle_connect(auth):
        connection_id = request.sid
        connection_info = {
            'namespace': request.namespace,
            'transport': 'websocket',  # Would need to detect actual transport
            'user_agent': request.headers.get('User-Agent', 'unknown'),
            'remote_addr': request.remote_addr
        }
        performance_monitor.register_connection(connection_id, connection_info)
        
    @socketio_instance.on('disconnect')
    def handle_disconnect():
        connection_id = request.sid
        performance_monitor.unregister_connection(connection_id, 'client_disconnect')
        
    # Add message tracking to existing event handlers
    original_emit = socketio_instance.emit
    
    def tracked_emit(*args, **kwargs):
        # Estimate message size (simplified)
        message_size = len(str(args)) + len(str(kwargs))
        start_time = time.time()
        
        result = original_emit(*args, **kwargs)
        
        delivery_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        # Record for all active connections (simplified)
        for connection_id in performance_monitor.active_connections:
            performance_monitor.record_message_sent(connection_id, message_size, delivery_time)
            
        return result
        
    socketio_instance.emit = tracked_emit
    
    return performance_monitor
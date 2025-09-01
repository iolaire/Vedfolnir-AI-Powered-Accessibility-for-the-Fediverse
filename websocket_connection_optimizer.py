# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
WebSocket Connection Optimizer

This module provides advanced WebSocket connection management and resource optimization
for the notification system, including connection pooling, resource cleanup,
idle connection management, and connection health monitoring.
"""

import logging
import time
import threading
import weakref
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum
import json

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """WebSocket connection states"""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    IDLE = "idle"
    ACTIVE = "active"
    DEGRADED = "degraded"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class ConnectionPriority(Enum):
    """Connection priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class ConnectionMetrics:
    """WebSocket connection metrics"""
    session_id: str
    user_id: Optional[int]
    namespace: str
    state: ConnectionState
    priority: ConnectionPriority
    created_at: datetime
    last_activity: datetime
    messages_sent: int = 0
    messages_received: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    error_count: int = 0
    ping_latency_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'session_id': self.session_id,
            'user_id': self.user_id,
            'namespace': self.namespace,
            'state': self.state.value,
            'priority': self.priority.value,
            'created_at': self.created_at.isoformat(),
            'last_activity': self.last_activity.isoformat(),
            'messages_sent': self.messages_sent,
            'messages_received': self.messages_received,
            'bytes_sent': self.bytes_sent,
            'bytes_received': self.bytes_received,
            'error_count': self.error_count,
            'ping_latency_ms': self.ping_latency_ms
        }


@dataclass
class ConnectionPoolConfig:
    """Connection pool configuration"""
    max_connections: int = 1000
    max_connections_per_user: int = 5
    idle_timeout_seconds: int = 300  # 5 minutes
    cleanup_interval_seconds: int = 60  # 1 minute
    health_check_interval_seconds: int = 30
    max_message_queue_size: int = 100
    connection_timeout_seconds: int = 30
    ping_interval_seconds: int = 25
    max_ping_failures: int = 3
    enable_compression: bool = True
    enable_heartbeat: bool = True


@dataclass
class ResourceLimits:
    """Resource usage limits"""
    max_memory_per_connection_mb: float = 10.0
    max_cpu_percent_per_connection: float = 5.0
    max_bandwidth_per_connection_kbps: float = 100.0
    max_total_memory_mb: float = 512.0
    max_total_cpu_percent: float = 50.0
    max_total_bandwidth_kbps: float = 10000.0


class ConnectionPool:
    """Advanced WebSocket connection pool with resource management"""
    
    def __init__(self, config: ConnectionPoolConfig, resource_limits: ResourceLimits):
        self.config = config
        self.resource_limits = resource_limits
        
        # Connection tracking
        self._connections = {}  # session_id -> ConnectionMetrics
        self._user_connections = defaultdict(set)  # user_id -> set of session_ids
        self._namespace_connections = defaultdict(set)  # namespace -> set of session_ids
        self._idle_connections = set()  # session_ids of idle connections
        
        # Message queues for connections
        self._message_queues = defaultdict(deque)  # session_id -> deque of messages
        
        # Resource tracking
        self._resource_usage = {
            'total_memory_mb': 0.0,
            'total_cpu_percent': 0.0,
            'total_bandwidth_kbps': 0.0,
            'connection_count': 0
        }
        
        # Health monitoring
        self._health_checks = {}  # session_id -> last_health_check_time
        self._ping_failures = defaultdict(int)  # session_id -> failure_count
        
        # Statistics
        self._stats = {
            'connections_created': 0,
            'connections_closed': 0,
            'connections_idle_timeout': 0,
            'connections_health_failed': 0,
            'messages_queued': 0,
            'messages_dropped': 0,
            'resource_limit_violations': 0,
            'cleanup_runs': 0
        }
        
        # Threading
        self._lock = threading.RLock()
        self._cleanup_timer = None
        self._health_check_timer = None
        
        # Start background tasks
        self._start_cleanup_timer()
        self._start_health_check_timer()
        
        logger.info("WebSocket Connection Pool initialized")
    
    def add_connection(self, session_id: str, user_id: Optional[int], 
                      namespace: str, priority: ConnectionPriority = ConnectionPriority.NORMAL) -> bool:
        """Add new connection to pool"""
        with self._lock:
            # Check connection limits
            if len(self._connections) >= self.config.max_connections:
                logger.warning(f"Connection pool full, rejecting connection {session_id}")
                self._stats['resource_limit_violations'] += 1
                return False
            
            # Check per-user limits
            if user_id and len(self._user_connections[user_id]) >= self.config.max_connections_per_user:
                logger.warning(f"User {user_id} has too many connections, rejecting {session_id}")
                self._stats['resource_limit_violations'] += 1
                return False
            
            # Check resource limits
            if not self._check_resource_limits():
                logger.warning(f"Resource limits exceeded, rejecting connection {session_id}")
                self._stats['resource_limit_violations'] += 1
                return False
            
            # Create connection metrics
            now = datetime.now(timezone.utc)
            metrics = ConnectionMetrics(
                session_id=session_id,
                user_id=user_id,
                namespace=namespace,
                state=ConnectionState.CONNECTED,
                priority=priority,
                created_at=now,
                last_activity=now
            )
            
            # Add to tracking structures
            self._connections[session_id] = metrics
            if user_id:
                self._user_connections[user_id].add(session_id)
            self._namespace_connections[namespace].add(session_id)
            
            # Initialize health check
            self._health_checks[session_id] = now
            
            # Update statistics
            self._stats['connections_created'] += 1
            self._resource_usage['connection_count'] = len(self._connections)
            
            logger.debug(f"Added connection {session_id} for user {user_id} in namespace {namespace}")
            return True
    
    def remove_connection(self, session_id: str) -> bool:
        """Remove connection from pool"""
        with self._lock:
            metrics = self._connections.get(session_id)
            if not metrics:
                return False
            
            # Remove from tracking structures
            del self._connections[session_id]
            
            if metrics.user_id:
                self._user_connections[metrics.user_id].discard(session_id)
                if not self._user_connections[metrics.user_id]:
                    del self._user_connections[metrics.user_id]
            
            self._namespace_connections[metrics.namespace].discard(session_id)
            if not self._namespace_connections[metrics.namespace]:
                del self._namespace_connections[metrics.namespace]
            
            self._idle_connections.discard(session_id)
            
            # Clean up associated data
            self._message_queues.pop(session_id, None)
            self._health_checks.pop(session_id, None)
            self._ping_failures.pop(session_id, None)
            
            # Update statistics
            self._stats['connections_closed'] += 1
            self._resource_usage['connection_count'] = len(self._connections)
            
            logger.debug(f"Removed connection {session_id}")
            return True
    
    def update_connection_activity(self, session_id: str, message_size: int = 0, 
                                 is_outbound: bool = True) -> None:
        """Update connection activity metrics"""
        with self._lock:
            metrics = self._connections.get(session_id)
            if not metrics:
                return
            
            # Update activity timestamp
            metrics.last_activity = datetime.now(timezone.utc)
            
            # Update message and byte counters
            if is_outbound:
                metrics.messages_sent += 1
                metrics.bytes_sent += message_size
            else:
                metrics.messages_received += 1
                metrics.bytes_received += message_size
            
            # Update connection state
            if metrics.state == ConnectionState.IDLE:
                metrics.state = ConnectionState.ACTIVE
                self._idle_connections.discard(session_id)
    
    def queue_message(self, session_id: str, message: Dict[str, Any]) -> bool:
        """Queue message for connection"""
        with self._lock:
            if session_id not in self._connections:
                return False
            
            queue = self._message_queues[session_id]
            
            # Check queue size limit
            if len(queue) >= self.config.max_message_queue_size:
                # Drop oldest message
                dropped = queue.popleft()
                self._stats['messages_dropped'] += 1
                logger.warning(f"Dropped message for connection {session_id}: queue full")
            
            # Add new message
            queue.append({
                'message': message,
                'timestamp': datetime.now(timezone.utc),
                'size': len(json.dumps(message))
            })
            
            self._stats['messages_queued'] += 1
            return True
    
    def get_queued_messages(self, session_id: str, max_messages: int = 10) -> List[Dict[str, Any]]:
        """Get queued messages for connection"""
        with self._lock:
            queue = self._message_queues.get(session_id, deque())
            messages = []
            
            for _ in range(min(max_messages, len(queue))):
                if queue:
                    queued_item = queue.popleft()
                    messages.append(queued_item['message'])
            
            return messages
    
    def get_connection_metrics(self, session_id: str) -> Optional[ConnectionMetrics]:
        """Get metrics for specific connection"""
        with self._lock:
            return self._connections.get(session_id)
    
    def get_user_connections(self, user_id: int) -> List[ConnectionMetrics]:
        """Get all connections for a user"""
        with self._lock:
            session_ids = self._user_connections.get(user_id, set())
            return [self._connections[sid] for sid in session_ids if sid in self._connections]
    
    def get_namespace_connections(self, namespace: str) -> List[ConnectionMetrics]:
        """Get all connections for a namespace"""
        with self._lock:
            session_ids = self._namespace_connections.get(namespace, set())
            return [self._connections[sid] for sid in session_ids if sid in self._connections]
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        with self._lock:
            # Calculate connection states
            state_counts = defaultdict(int)
            priority_counts = defaultdict(int)
            namespace_counts = defaultdict(int)
            
            for metrics in self._connections.values():
                state_counts[metrics.state.value] += 1
                priority_counts[metrics.priority.value] += 1
                namespace_counts[metrics.namespace] += 1
            
            # Calculate resource usage
            total_messages = sum(m.messages_sent + m.messages_received for m in self._connections.values())
            total_bytes = sum(m.bytes_sent + m.bytes_received for m in self._connections.values())
            
            return {
                'total_connections': len(self._connections),
                'max_connections': self.config.max_connections,
                'utilization_percent': (len(self._connections) / self.config.max_connections) * 100,
                'idle_connections': len(self._idle_connections),
                'active_users': len(self._user_connections),
                'active_namespaces': len(self._namespace_connections),
                'state_distribution': dict(state_counts),
                'priority_distribution': dict(priority_counts),
                'namespace_distribution': dict(namespace_counts),
                'resource_usage': self._resource_usage.copy(),
                'message_stats': {
                    'total_messages': total_messages,
                    'total_bytes': total_bytes,
                    'queued_messages': sum(len(q) for q in self._message_queues.values())
                },
                'performance_stats': self._stats.copy()
            }
    
    def cleanup_idle_connections(self) -> int:
        """Clean up idle connections"""
        with self._lock:
            current_time = datetime.now(timezone.utc)
            idle_threshold = current_time - timedelta(seconds=self.config.idle_timeout_seconds)
            
            connections_to_remove = []
            
            for session_id, metrics in self._connections.items():
                # Check if connection is idle
                if metrics.last_activity < idle_threshold:
                    if metrics.state not in [ConnectionState.DISCONNECTING, ConnectionState.DISCONNECTED]:
                        connections_to_remove.append(session_id)
                        metrics.state = ConnectionState.IDLE
                        self._idle_connections.add(session_id)
            
            # Remove idle connections
            removed_count = 0
            for session_id in connections_to_remove:
                if self._should_remove_idle_connection(session_id):
                    self.remove_connection(session_id)
                    removed_count += 1
                    self._stats['connections_idle_timeout'] += 1
            
            self._stats['cleanup_runs'] += 1
            
            if removed_count > 0:
                logger.info(f"Cleaned up {removed_count} idle connections")
            
            return removed_count
    
    def perform_health_checks(self) -> Dict[str, Any]:
        """Perform health checks on all connections"""
        with self._lock:
            current_time = datetime.now(timezone.utc)
            health_results = {
                'healthy': 0,
                'degraded': 0,
                'failed': 0,
                'checked': 0
            }
            
            for session_id, metrics in self._connections.items():
                # Check if health check is due
                last_check = self._health_checks.get(session_id, current_time)
                if (current_time - last_check).total_seconds() < self.config.health_check_interval_seconds:
                    continue
                
                health_results['checked'] += 1
                
                # Perform health check
                if self._perform_connection_health_check(session_id, metrics):
                    if metrics.state == ConnectionState.DEGRADED:
                        metrics.state = ConnectionState.CONNECTED
                    health_results['healthy'] += 1
                    self._ping_failures[session_id] = 0
                else:
                    self._ping_failures[session_id] += 1
                    
                    if self._ping_failures[session_id] >= self.config.max_ping_failures:
                        metrics.state = ConnectionState.ERROR
                        health_results['failed'] += 1
                        self._stats['connections_health_failed'] += 1
                    else:
                        metrics.state = ConnectionState.DEGRADED
                        health_results['degraded'] += 1
                
                self._health_checks[session_id] = current_time
            
            return health_results
    
    def optimize_connections(self) -> Dict[str, Any]:
        """Optimize connection pool performance"""
        optimization_results = {
            'connections_optimized': 0,
            'memory_saved_mb': 0,
            'messages_processed': 0,
            'idle_connections_cleaned': 0
        }
        
        with self._lock:
            # Clean up idle connections
            idle_cleaned = self.cleanup_idle_connections()
            optimization_results['idle_connections_cleaned'] = idle_cleaned
            
            # Process message queues efficiently
            messages_processed = 0
            for session_id, queue in self._message_queues.items():
                if len(queue) > 0:
                    # Process messages in batches
                    batch_size = min(10, len(queue))
                    for _ in range(batch_size):
                        if queue:
                            queue.popleft()
                            messages_processed += 1
            
            optimization_results['messages_processed'] = messages_processed
            
            # Optimize memory usage
            memory_saved = self._optimize_memory_usage()
            optimization_results['memory_saved_mb'] = memory_saved
            
            # Count optimized connections
            optimization_results['connections_optimized'] = len(self._connections)
        
        return optimization_results
    
    def get_connection_health_report(self) -> Dict[str, Any]:
        """Get comprehensive connection health report"""
        with self._lock:
            current_time = datetime.now(timezone.utc)
            
            # Analyze connection health
            healthy_connections = 0
            degraded_connections = 0
            error_connections = 0
            avg_latency = 0
            total_errors = 0
            
            latencies = []
            
            for metrics in self._connections.values():
                if metrics.state == ConnectionState.CONNECTED:
                    healthy_connections += 1
                elif metrics.state == ConnectionState.DEGRADED:
                    degraded_connections += 1
                elif metrics.state == ConnectionState.ERROR:
                    error_connections += 1
                
                if metrics.ping_latency_ms > 0:
                    latencies.append(metrics.ping_latency_ms)
                
                total_errors += metrics.error_count
            
            if latencies:
                avg_latency = sum(latencies) / len(latencies)
            
            # Calculate uptime statistics
            connection_ages = []
            for metrics in self._connections.values():
                age_seconds = (current_time - metrics.created_at).total_seconds()
                connection_ages.append(age_seconds)
            
            avg_connection_age = sum(connection_ages) / len(connection_ages) if connection_ages else 0
            
            return {
                'timestamp': current_time.isoformat(),
                'total_connections': len(self._connections),
                'health_distribution': {
                    'healthy': healthy_connections,
                    'degraded': degraded_connections,
                    'error': error_connections
                },
                'performance_metrics': {
                    'average_latency_ms': avg_latency,
                    'total_errors': total_errors,
                    'average_connection_age_seconds': avg_connection_age
                },
                'resource_utilization': {
                    'connection_pool_utilization': (len(self._connections) / self.config.max_connections) * 100,
                    'memory_usage': self._resource_usage['total_memory_mb'],
                    'cpu_usage': self._resource_usage['total_cpu_percent'],
                    'bandwidth_usage': self._resource_usage['total_bandwidth_kbps']
                },
                'queue_statistics': {
                    'total_queued_messages': sum(len(q) for q in self._message_queues.values()),
                    'average_queue_size': sum(len(q) for q in self._message_queues.values()) / max(len(self._message_queues), 1),
                    'max_queue_size': max((len(q) for q in self._message_queues.values()), default=0)
                }
            }
    
    def _check_resource_limits(self) -> bool:
        """Check if resource limits allow new connection"""
        # Check total memory limit
        if self._resource_usage['total_memory_mb'] >= self.resource_limits.max_total_memory_mb:
            return False
        
        # Check total CPU limit
        if self._resource_usage['total_cpu_percent'] >= self.resource_limits.max_total_cpu_percent:
            return False
        
        # Check total bandwidth limit
        if self._resource_usage['total_bandwidth_kbps'] >= self.resource_limits.max_total_bandwidth_kbps:
            return False
        
        return True
    
    def _should_remove_idle_connection(self, session_id: str) -> bool:
        """Determine if idle connection should be removed"""
        metrics = self._connections.get(session_id)
        if not metrics:
            return True
        
        # Don't remove high priority connections immediately
        if metrics.priority in [ConnectionPriority.HIGH, ConnectionPriority.CRITICAL]:
            return False
        
        # Remove if truly idle and no queued messages
        return len(self._message_queues.get(session_id, deque())) == 0
    
    def _perform_connection_health_check(self, session_id: str, metrics: ConnectionMetrics) -> bool:
        """Perform health check on specific connection"""
        try:
            # Simulate ping check (in real implementation, would send actual ping)
            current_time = time.time()
            
            # Check if connection is responsive based on recent activity
            last_activity_seconds = (datetime.now(timezone.utc) - metrics.last_activity).total_seconds()
            
            # Consider connection healthy if recent activity or low error count
            if last_activity_seconds < 60 or metrics.error_count < 3:
                # Simulate latency measurement
                metrics.ping_latency_ms = 10.0 + (metrics.error_count * 5.0)  # Simulate increasing latency with errors
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Health check failed for connection {session_id}: {e}")
            metrics.error_count += 1
            return False
    
    def _optimize_memory_usage(self) -> float:
        """Optimize memory usage and return MB saved"""
        memory_saved = 0.0
        
        try:
            # Clear empty message queues
            empty_queues = [sid for sid, queue in self._message_queues.items() if len(queue) == 0]
            for session_id in empty_queues:
                del self._message_queues[session_id]
                memory_saved += 0.1  # Estimate
            
            # Compress large message queues
            for session_id, queue in self._message_queues.items():
                if len(queue) > 50:
                    # Keep only recent messages
                    while len(queue) > 25:
                        queue.popleft()
                        memory_saved += 0.01  # Estimate
            
            return memory_saved
            
        except Exception as e:
            logger.error(f"Memory optimization failed: {e}")
            return 0.0
    
    def _start_cleanup_timer(self) -> None:
        """Start periodic cleanup timer"""
        if self._cleanup_timer:
            self._cleanup_timer.cancel()
        
        self._cleanup_timer = threading.Timer(
            self.config.cleanup_interval_seconds,
            self._periodic_cleanup
        )
        self._cleanup_timer.daemon = True
        self._cleanup_timer.start()
    
    def _start_health_check_timer(self) -> None:
        """Start periodic health check timer"""
        if self._health_check_timer:
            self._health_check_timer.cancel()
        
        self._health_check_timer = threading.Timer(
            self.config.health_check_interval_seconds,
            self._periodic_health_check
        )
        self._health_check_timer.daemon = True
        self._health_check_timer.start()
    
    def _periodic_cleanup(self) -> None:
        """Periodic cleanup task"""
        try:
            self.cleanup_idle_connections()
        except Exception as e:
            logger.error(f"Periodic cleanup failed: {e}")
        finally:
            self._start_cleanup_timer()
    
    def _periodic_health_check(self) -> None:
        """Periodic health check task"""
        try:
            self.perform_health_checks()
        except Exception as e:
            logger.error(f"Periodic health check failed: {e}")
        finally:
            self._start_health_check_timer()
    
    def shutdown(self) -> None:
        """Shutdown connection pool"""
        with self._lock:
            # Cancel timers
            if self._cleanup_timer:
                self._cleanup_timer.cancel()
            if self._health_check_timer:
                self._health_check_timer.cancel()
            
            # Close all connections
            connection_ids = list(self._connections.keys())
            for session_id in connection_ids:
                self.remove_connection(session_id)
            
            logger.info("WebSocket Connection Pool shutdown complete")


class WebSocketConnectionOptimizer:
    """Main WebSocket connection optimizer"""
    
    def __init__(self, namespace_manager, config: Optional[ConnectionPoolConfig] = None,
                 resource_limits: Optional[ResourceLimits] = None):
        self.namespace_manager = namespace_manager
        self.config = config or ConnectionPoolConfig()
        self.resource_limits = resource_limits or ResourceLimits()
        
        # Initialize connection pool
        self.connection_pool = ConnectionPool(self.config, self.resource_limits)
        
        # Integration with namespace manager
        self._integrate_with_namespace_manager()
        
        logger.info("WebSocket Connection Optimizer initialized")
    
    def optimize_connection_management(self) -> Dict[str, Any]:
        """Optimize WebSocket connection management"""
        try:
            # Perform connection pool optimization
            pool_results = self.connection_pool.optimize_connections()
            
            # Get health report
            health_report = self.connection_pool.get_connection_health_report()
            
            # Get pool statistics
            pool_stats = self.connection_pool.get_pool_stats()
            
            return {
                'optimization_results': pool_results,
                'health_report': health_report,
                'pool_statistics': pool_stats,
                'recommendations': self._generate_optimization_recommendations(pool_stats, health_report)
            }
            
        except Exception as e:
            logger.error(f"Failed to optimize connection management: {e}")
            return {'error': str(e)}
    
    def get_connection_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive connection performance report"""
        try:
            pool_stats = self.connection_pool.get_pool_stats()
            health_report = self.connection_pool.get_connection_health_report()
            
            return {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'pool_statistics': pool_stats,
                'health_report': health_report,
                'configuration': {
                    'max_connections': self.config.max_connections,
                    'max_connections_per_user': self.config.max_connections_per_user,
                    'idle_timeout_seconds': self.config.idle_timeout_seconds,
                    'health_check_interval_seconds': self.config.health_check_interval_seconds
                },
                'resource_limits': {
                    'max_total_memory_mb': self.resource_limits.max_total_memory_mb,
                    'max_total_cpu_percent': self.resource_limits.max_total_cpu_percent,
                    'max_total_bandwidth_kbps': self.resource_limits.max_total_bandwidth_kbps
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to generate performance report: {e}")
            return {'error': str(e)}
    
    def _integrate_with_namespace_manager(self) -> None:
        """Integrate with existing namespace manager"""
        try:
            # Hook into namespace manager events if available
            if hasattr(self.namespace_manager, 'on_connect'):
                original_on_connect = self.namespace_manager.on_connect
                
                def optimized_on_connect(session_id, namespace, user_id=None):
                    # Add to connection pool
                    self.connection_pool.add_connection(session_id, user_id, namespace)
                    # Call original handler
                    return original_on_connect(session_id, namespace, user_id)
                
                self.namespace_manager.on_connect = optimized_on_connect
            
            if hasattr(self.namespace_manager, 'on_disconnect'):
                original_on_disconnect = self.namespace_manager.on_disconnect
                
                def optimized_on_disconnect(session_id):
                    # Remove from connection pool
                    self.connection_pool.remove_connection(session_id)
                    # Call original handler
                    return original_on_disconnect(session_id)
                
                self.namespace_manager.on_disconnect = optimized_on_disconnect
            
        except Exception as e:
            logger.error(f"Failed to integrate with namespace manager: {e}")
    
    def _generate_optimization_recommendations(self, pool_stats: Dict[str, Any], 
                                            health_report: Dict[str, Any]) -> List[str]:
        """Generate optimization recommendations"""
        recommendations = []
        
        # Connection pool utilization
        utilization = pool_stats.get('utilization_percent', 0)
        if utilization > 90:
            recommendations.append("Consider increasing max_connections limit - pool utilization is very high")
        elif utilization > 75:
            recommendations.append("Monitor connection pool usage - approaching capacity")
        
        # Idle connections
        idle_count = pool_stats.get('idle_connections', 0)
        total_connections = pool_stats.get('total_connections', 1)
        idle_ratio = idle_count / total_connections if total_connections > 0 else 0
        
        if idle_ratio > 0.3:
            recommendations.append("Consider reducing idle_timeout_seconds - many connections are idle")
        
        # Health issues
        health_dist = health_report.get('health_distribution', {})
        degraded = health_dist.get('degraded', 0)
        error = health_dist.get('error', 0)
        
        if degraded > 0 or error > 0:
            recommendations.append("Investigate connection health issues - some connections are degraded or in error state")
        
        # Resource usage
        resource_usage = pool_stats.get('resource_usage', {})
        memory_usage = resource_usage.get('total_memory_mb', 0)
        
        if memory_usage > self.resource_limits.max_total_memory_mb * 0.8:
            recommendations.append("Memory usage is high - consider increasing limits or optimizing connection memory usage")
        
        # Queue statistics
        queue_stats = health_report.get('queue_statistics', {})
        avg_queue_size = queue_stats.get('average_queue_size', 0)
        
        if avg_queue_size > 10:
            recommendations.append("Message queues are growing - consider increasing processing capacity")
        
        return recommendations
    
    def shutdown(self) -> None:
        """Shutdown connection optimizer"""
        self.connection_pool.shutdown()
        logger.info("WebSocket Connection Optimizer shutdown complete")
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Notification Performance Optimizer

This module provides comprehensive performance optimization for the notification system,
including WebSocket connection management, notification batching and throttling,
memory management, database query optimization, and caching strategies.
"""

import logging
import time
import threading
import weakref
import gc
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Set, Tuple, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum
import json
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.services.notification.manager.unified_manager import NotificationMessage, NotificationType, NotificationPriority, NotificationCategory
from notification_message_router import NotificationMessageRouter
from app.services.notification.components.notification_persistence_manager import NotificationPersistenceManager

logger = logging.getLogger(__name__)


class OptimizationLevel(Enum):
    """Performance optimization levels"""
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"
    MAXIMUM = "maximum"


class ConnectionPoolStatus(Enum):
    """WebSocket connection pool status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    OVERLOADED = "overloaded"
    CRITICAL = "critical"


@dataclass
class PerformanceMetrics:
    """Performance metrics tracking"""
    timestamp: datetime
    websocket_connections: int
    active_sessions: int
    message_throughput: float  # messages per second
    memory_usage_mb: float
    cpu_usage_percent: float
    database_query_time_ms: float
    cache_hit_rate: float
    batch_efficiency: float
    throttle_rate: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp.isoformat(),
            'websocket_connections': self.websocket_connections,
            'active_sessions': self.active_sessions,
            'message_throughput': self.message_throughput,
            'memory_usage_mb': self.memory_usage_mb,
            'cpu_usage_percent': self.cpu_usage_percent,
            'database_query_time_ms': self.database_query_time_ms,
            'cache_hit_rate': self.cache_hit_rate,
            'batch_efficiency': self.batch_efficiency,
            'throttle_rate': self.throttle_rate
        }


@dataclass
class BatchConfiguration:
    """Notification batching configuration"""
    max_batch_size: int = 50
    batch_timeout_ms: int = 100
    priority_batching: bool = True
    category_batching: bool = True
    user_batching: bool = True
    compression_enabled: bool = True
    compression_threshold: int = 1024  # bytes


@dataclass
class ThrottleConfiguration:
    """Notification throttling configuration"""
    max_messages_per_second: int = 100
    burst_capacity: int = 200
    user_rate_limit: int = 10  # per user per second
    priority_multipliers: Dict[NotificationPriority, float] = field(default_factory=lambda: {
        NotificationPriority.LOW: 0.5,
        NotificationPriority.NORMAL: 1.0,
        NotificationPriority.HIGH: 1.5,
        NotificationPriority.CRITICAL: 2.0
    })
    backpressure_threshold: float = 0.8  # 80% of capacity


@dataclass
class CacheConfiguration:
    """Notification caching configuration"""
    enabled: bool = True
    max_cache_size: int = 10000  # number of messages
    ttl_seconds: int = 3600  # 1 hour
    user_cache_size: int = 100  # per user
    compression_enabled: bool = True
    eviction_policy: str = "lru"  # lru, lfu, fifo


@dataclass
class MemoryConfiguration:
    """Memory management configuration"""
    max_memory_mb: int = 512
    gc_threshold: float = 0.8  # 80% of max memory
    cleanup_interval_seconds: int = 300  # 5 minutes
    weak_references: bool = True
    object_pooling: bool = True
    memory_profiling: bool = False


class NotificationCache:
    """High-performance notification cache with compression and eviction"""
    
    def __init__(self, config: CacheConfiguration):
        self.config = config
        self._cache = {}  # message_id -> (data, timestamp, access_count)
        self._user_caches = defaultdict(dict)  # user_id -> {message_id: data}
        self._access_order = deque()  # for LRU eviction
        self._lock = threading.RLock()
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'compressions': 0
        }
    
    def get(self, message_id: str, user_id: Optional[int] = None) -> Optional[NotificationMessage]:
        """Get message from cache"""
        if not self.config.enabled:
            return None
        
        with self._lock:
            # Check user cache first
            if user_id and message_id in self._user_caches[user_id]:
                self._stats['hits'] += 1
                return self._decompress_message(self._user_caches[user_id][message_id])
            
            # Check global cache
            if message_id in self._cache:
                data, timestamp, access_count = self._cache[message_id]
                
                # Check TTL
                if (datetime.now(timezone.utc) - timestamp).total_seconds() > self.config.ttl_seconds:
                    del self._cache[message_id]
                    self._stats['misses'] += 1
                    return None
                
                # Update access info
                self._cache[message_id] = (data, timestamp, access_count + 1)
                self._update_access_order(message_id)
                self._stats['hits'] += 1
                
                return self._decompress_message(data)
            
            self._stats['misses'] += 1
            return None
    
    def put(self, message: NotificationMessage, user_id: Optional[int] = None) -> None:
        """Put message in cache"""
        if not self.config.enabled:
            return
        
        with self._lock:
            # Compress message if needed
            compressed_data = self._compress_message(message)
            timestamp = datetime.now(timezone.utc)
            
            # Add to global cache
            self._cache[message.id] = (compressed_data, timestamp, 1)
            self._access_order.append(message.id)
            
            # Add to user cache if specified
            if user_id:
                user_cache = self._user_caches[user_id]
                user_cache[message.id] = compressed_data
                
                # Evict from user cache if needed
                if len(user_cache) > self.config.user_cache_size:
                    oldest_id = next(iter(user_cache))
                    del user_cache[oldest_id]
            
            # Evict from global cache if needed
            self._evict_if_needed()
    
    def invalidate(self, message_id: str, user_id: Optional[int] = None) -> None:
        """Invalidate cached message"""
        with self._lock:
            if message_id in self._cache:
                del self._cache[message_id]
            
            if user_id and message_id in self._user_caches[user_id]:
                del self._user_caches[user_id][message_id]
    
    def clear_user_cache(self, user_id: int) -> None:
        """Clear cache for specific user"""
        with self._lock:
            self._user_caches[user_id].clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            total_requests = self._stats['hits'] + self._stats['misses']
            hit_rate = self._stats['hits'] / total_requests if total_requests > 0 else 0
            
            return {
                'hit_rate': hit_rate,
                'total_entries': len(self._cache),
                'user_caches': len(self._user_caches),
                'stats': self._stats.copy()
            }
    
    def _compress_message(self, message: NotificationMessage) -> bytes:
        """Compress message data"""
        if not self.config.compression_enabled:
            return json.dumps(message.to_dict()).encode('utf-8')
        
        import gzip
        data = json.dumps(message.to_dict()).encode('utf-8')
        
        if len(data) > 1024:  # Only compress larger messages
            compressed = gzip.compress(data)
            self._stats['compressions'] += 1
            return b'GZIP:' + compressed
        
        return data
    
    def _decompress_message(self, data: bytes) -> NotificationMessage:
        """Decompress message data"""
        if data.startswith(b'GZIP:'):
            import gzip
            decompressed = gzip.decompress(data[5:])
            message_dict = json.loads(decompressed.decode('utf-8'))
        else:
            message_dict = json.loads(data.decode('utf-8'))
        
        return NotificationMessage.from_dict(message_dict)
    
    def _evict_if_needed(self) -> None:
        """Evict entries if cache is full"""
        while len(self._cache) > self.config.max_cache_size:
            if self.config.eviction_policy == "lru":
                oldest_id = self._access_order.popleft()
                if oldest_id in self._cache:
                    del self._cache[oldest_id]
                    self._stats['evictions'] += 1
            else:
                # Simple FIFO for now
                oldest_id = next(iter(self._cache))
                del self._cache[oldest_id]
                self._stats['evictions'] += 1
    
    def _update_access_order(self, message_id: str) -> None:
        """Update access order for LRU"""
        if self.config.eviction_policy == "lru":
            try:
                self._access_order.remove(message_id)
            except ValueError:
                pass
            self._access_order.append(message_id)


class NotificationBatcher:
    """High-performance notification batching system"""
    
    def __init__(self, config: BatchConfiguration, router: NotificationMessageRouter):
        self.config = config
        self.router = router
        self._batches = defaultdict(list)  # batch_key -> list of messages
        self._batch_timers = {}  # batch_key -> timer
        self._lock = threading.RLock()
        self._stats = {
            'batches_created': 0,
            'batches_sent': 0,
            'messages_batched': 0,
            'compression_savings': 0
        }
    
    def add_message(self, message: NotificationMessage, user_id: int) -> None:
        """Add message to batch"""
        batch_key = self._get_batch_key(message, user_id)
        
        with self._lock:
            batch = self._batches[batch_key]
            batch.append((message, user_id))
            self._stats['messages_batched'] += 1
            
            # Check if batch is full
            if len(batch) >= self.config.max_batch_size:
                self._send_batch(batch_key)
            else:
                # Set timer if not already set
                if batch_key not in self._batch_timers:
                    timer = threading.Timer(
                        self.config.batch_timeout_ms / 1000.0,
                        self._send_batch,
                        args=[batch_key]
                    )
                    timer.start()
                    self._batch_timers[batch_key] = timer
    
    def flush_all_batches(self) -> int:
        """Flush all pending batches"""
        with self._lock:
            batch_count = 0
            for batch_key in list(self._batches.keys()):
                if self._batches[batch_key]:
                    self._send_batch(batch_key)
                    batch_count += 1
            return batch_count
    
    def get_stats(self) -> Dict[str, Any]:
        """Get batching statistics"""
        with self._lock:
            pending_batches = len([b for b in self._batches.values() if b])
            pending_messages = sum(len(b) for b in self._batches.values())
            
            return {
                'pending_batches': pending_batches,
                'pending_messages': pending_messages,
                'stats': self._stats.copy()
            }
    
    def _get_batch_key(self, message: NotificationMessage, user_id: int) -> str:
        """Generate batch key for message grouping"""
        key_parts = []
        
        if self.config.user_batching:
            key_parts.append(f"user:{user_id}")
        
        if self.config.priority_batching:
            key_parts.append(f"priority:{message.priority.value}")
        
        if self.config.category_batching:
            key_parts.append(f"category:{message.category.value}")
        
        return "|".join(key_parts) if key_parts else "default"
    
    def _send_batch(self, batch_key: str) -> None:
        """Send batch of messages"""
        with self._lock:
            batch = self._batches.get(batch_key, [])
            if not batch:
                return
            
            # Clear batch and timer
            self._batches[batch_key] = []
            timer = self._batch_timers.pop(batch_key, None)
            if timer:
                timer.cancel()
            
            self._stats['batches_sent'] += 1
        
        # Send messages in batch (outside lock)
        try:
            if self.config.compression_enabled and len(batch) > 1:
                self._send_compressed_batch(batch)
            else:
                self._send_individual_messages(batch)
        except Exception as e:
            logger.error(f"Failed to send batch {batch_key}: {e}")
    
    def _send_compressed_batch(self, batch: List[Tuple[NotificationMessage, int]]) -> None:
        """Send batch with compression optimization"""
        # Group by user for efficient delivery
        user_messages = defaultdict(list)
        for message, user_id in batch:
            user_messages[user_id].append(message)
        
        # Send to each user
        for user_id, messages in user_messages.items():
            try:
                # Create batch message
                batch_data = {
                    'type': 'batch',
                    'messages': [msg.to_dict() for msg in messages],
                    'count': len(messages),
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                
                # Compress if beneficial
                if len(json.dumps(batch_data)) > self.config.compression_threshold:
                    import gzip
                    compressed_data = gzip.compress(json.dumps(batch_data).encode('utf-8'))
                    self._stats['compression_savings'] += len(json.dumps(batch_data)) - len(compressed_data)
                
                # Route batch (simplified - would need router enhancement)
                for message in messages:
                    self.router.route_user_message(user_id, message)
                
            except Exception as e:
                logger.error(f"Failed to send compressed batch to user {user_id}: {e}")
    
    def _send_individual_messages(self, batch: List[Tuple[NotificationMessage, int]]) -> None:
        """Send messages individually"""
        for message, user_id in batch:
            try:
                self.router.route_user_message(user_id, message)
            except Exception as e:
                logger.error(f"Failed to send message {message.id} to user {user_id}: {e}")


class NotificationThrottler:
    """Advanced notification throttling with backpressure handling"""
    
    def __init__(self, config: ThrottleConfiguration):
        self.config = config
        self._rate_limiters = defaultdict(deque)  # user_id -> deque of timestamps
        self._global_rate = deque()  # global rate limiting
        self._burst_tokens = self.config.burst_capacity
        self._last_refill = time.time()
        self._lock = threading.RLock()
        self._stats = {
            'messages_throttled': 0,
            'users_throttled': 0,
            'backpressure_events': 0,
            'burst_used': 0
        }
    
    def should_allow_message(self, message: NotificationMessage, user_id: int) -> bool:
        """Check if message should be allowed through throttle"""
        current_time = time.time()
        
        with self._lock:
            # Refill burst tokens
            self._refill_burst_tokens(current_time)
            
            # Check global rate limit
            if not self._check_global_rate(current_time):
                self._stats['messages_throttled'] += 1
                return False
            
            # Check user rate limit
            if not self._check_user_rate(user_id, current_time, message.priority):
                self._stats['messages_throttled'] += 1
                self._stats['users_throttled'] += 1
                return False
            
            # Check backpressure
            if self._is_backpressure_active():
                # Only allow high priority messages during backpressure
                if message.priority not in [NotificationPriority.HIGH, NotificationPriority.CRITICAL]:
                    self._stats['backpressure_events'] += 1
                    return False
            
            # Use burst token if available
            if self._burst_tokens > 0:
                self._burst_tokens -= 1
                self._stats['burst_used'] += 1
            
            # Record message
            self._global_rate.append(current_time)
            self._rate_limiters[user_id].append(current_time)
            
            return True
    
    def get_throttle_stats(self) -> Dict[str, Any]:
        """Get throttling statistics"""
        with self._lock:
            current_time = time.time()
            
            # Calculate current rates
            global_rate = len([t for t in self._global_rate if current_time - t <= 1.0])
            user_rates = {
                user_id: len([t for t in timestamps if current_time - t <= 1.0])
                for user_id, timestamps in self._rate_limiters.items()
            }
            
            return {
                'current_global_rate': global_rate,
                'max_global_rate': self.config.max_messages_per_second,
                'burst_tokens_available': self._burst_tokens,
                'burst_capacity': self.config.burst_capacity,
                'active_users': len(self._rate_limiters),
                'backpressure_active': self._is_backpressure_active(),
                'user_rates': user_rates,
                'stats': self._stats.copy()
            }
    
    def _refill_burst_tokens(self, current_time: float) -> None:
        """Refill burst tokens based on time elapsed"""
        time_elapsed = current_time - self._last_refill
        tokens_to_add = int(time_elapsed * self.config.max_messages_per_second)
        
        if tokens_to_add > 0:
            self._burst_tokens = min(
                self.config.burst_capacity,
                self._burst_tokens + tokens_to_add
            )
            self._last_refill = current_time
    
    def _check_global_rate(self, current_time: float) -> bool:
        """Check global rate limit"""
        # Clean old entries
        while self._global_rate and current_time - self._global_rate[0] > 1.0:
            self._global_rate.popleft()
        
        return len(self._global_rate) < self.config.max_messages_per_second
    
    def _check_user_rate(self, user_id: int, current_time: float, priority: NotificationPriority) -> bool:
        """Check user-specific rate limit"""
        user_timestamps = self._rate_limiters[user_id]
        
        # Clean old entries
        while user_timestamps and current_time - user_timestamps[0] > 1.0:
            user_timestamps.popleft()
        
        # Apply priority multiplier
        multiplier = self.config.priority_multipliers.get(priority, 1.0)
        effective_limit = int(self.config.user_rate_limit * multiplier)
        
        return len(user_timestamps) < effective_limit
    
    def _is_backpressure_active(self) -> bool:
        """Check if backpressure should be applied"""
        current_rate = len(self._global_rate)
        threshold = self.config.max_messages_per_second * self.config.backpressure_threshold
        return current_rate >= threshold


class MemoryManager:
    """Advanced memory management for notification system"""
    
    def __init__(self, config: MemoryConfiguration):
        self.config = config
        self._object_pools = defaultdict(list)  # type -> list of objects
        self._weak_refs = weakref.WeakSet()
        self._memory_stats = {
            'current_usage_mb': 0,
            'peak_usage_mb': 0,
            'gc_runs': 0,
            'objects_pooled': 0,
            'objects_reused': 0
        }
        self._cleanup_timer = None
        self._start_cleanup_timer()
    
    def get_pooled_object(self, obj_type: str, factory: Callable) -> Any:
        """Get object from pool or create new one"""
        if not self.config.object_pooling:
            return factory()
        
        pool = self._object_pools[obj_type]
        if pool:
            obj = pool.pop()
            self._memory_stats['objects_reused'] += 1
            return obj
        else:
            obj = factory()
            if self.config.weak_references:
                self._weak_refs.add(obj)
            return obj
    
    def return_to_pool(self, obj_type: str, obj: Any) -> None:
        """Return object to pool for reuse"""
        if not self.config.object_pooling:
            return
        
        # Reset object state if it has a reset method
        if hasattr(obj, 'reset'):
            obj.reset()
        
        pool = self._object_pools[obj_type]
        if len(pool) < 100:  # Limit pool size
            pool.append(obj)
            self._memory_stats['objects_pooled'] += 1
    
    def check_memory_usage(self) -> Dict[str, Any]:
        """Check current memory usage"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        current_mb = memory_info.rss / 1024 / 1024
        
        self._memory_stats['current_usage_mb'] = current_mb
        if current_mb > self._memory_stats['peak_usage_mb']:
            self._memory_stats['peak_usage_mb'] = current_mb
        
        return {
            'current_mb': current_mb,
            'max_mb': self.config.max_memory_mb,
            'usage_percent': (current_mb / self.config.max_memory_mb) * 100,
            'gc_threshold_reached': current_mb >= (self.config.max_memory_mb * self.config.gc_threshold),
            'stats': self._memory_stats.copy()
        }
    
    def cleanup_memory(self) -> Dict[str, int]:
        """Perform memory cleanup"""
        cleanup_stats = {
            'objects_collected': 0,
            'pools_cleared': 0,
            'weak_refs_cleared': 0
        }
        
        # Force garbage collection
        collected = gc.collect()
        cleanup_stats['objects_collected'] = collected
        self._memory_stats['gc_runs'] += 1
        
        # Clear object pools if memory pressure is high
        memory_info = self.check_memory_usage()
        if memory_info['usage_percent'] > 80:
            for pool in self._object_pools.values():
                cleanup_stats['pools_cleared'] += len(pool)
                pool.clear()
        
        # Clean up weak references
        if self.config.weak_references:
            initial_count = len(self._weak_refs)
            # Weak references clean themselves up automatically
            cleanup_stats['weak_refs_cleared'] = initial_count - len(self._weak_refs)
        
        logger.info(f"Memory cleanup completed: {cleanup_stats}")
        return cleanup_stats
    
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
    
    def _periodic_cleanup(self) -> None:
        """Periodic memory cleanup"""
        try:
            memory_info = self.check_memory_usage()
            if memory_info['gc_threshold_reached']:
                self.cleanup_memory()
        except Exception as e:
            logger.error(f"Periodic memory cleanup failed: {e}")
        finally:
            self._start_cleanup_timer()


class NotificationPerformanceOptimizer:
    """Main performance optimizer coordinating all optimization components"""
    
    def __init__(self, 
                 notification_manager,
                 message_router: NotificationMessageRouter,
                 persistence_manager: NotificationPersistenceManager,
                 optimization_level: OptimizationLevel = OptimizationLevel.BALANCED):
        
        self.notification_manager = notification_manager
        self.message_router = message_router
        self.persistence_manager = persistence_manager
        self.optimization_level = optimization_level
        
        # Initialize configurations based on optimization level
        self._init_configurations()
        
        # Initialize optimization components
        self.cache = NotificationCache(self.cache_config)
        self.batcher = NotificationBatcher(self.batch_config, message_router)
        self.throttler = NotificationThrottler(self.throttle_config)
        self.memory_manager = MemoryManager(self.memory_config)
        
        # Performance monitoring
        self._metrics_history = deque(maxlen=1000)
        self._monitoring_enabled = True
        self._monitoring_interval = 30  # seconds
        self._start_monitoring()
        
        # Statistics
        self._optimization_stats = {
            'messages_optimized': 0,
            'cache_hits': 0,
            'batches_sent': 0,
            'throttled_messages': 0,
            'memory_cleanups': 0,
            'performance_improvements': 0
        }
        
        logger.info(f"Notification Performance Optimizer initialized with {optimization_level.value} level")
    
    def optimize_message_delivery(self, message: NotificationMessage, user_id: int) -> bool:
        """Optimize message delivery through all optimization layers"""
        try:
            # Check cache first
            cached_message = self.cache.get(message.id, user_id)
            if cached_message:
                self._optimization_stats['cache_hits'] += 1
                return True
            
            # Check throttling
            if not self.throttler.should_allow_message(message, user_id):
                self._optimization_stats['throttled_messages'] += 1
                # Queue for later delivery
                self.persistence_manager.queue_for_offline_user(user_id, message)
                return False
            
            # Add to batch if batching is enabled
            if self.batch_config.max_batch_size > 1:
                self.batcher.add_message(message, user_id)
                self._optimization_stats['batches_sent'] += 1
            else:
                # Direct delivery
                success = self.message_router.route_user_message(user_id, message)
                if success:
                    # Cache successful delivery
                    self.cache.put(message, user_id)
            
            self._optimization_stats['messages_optimized'] += 1
            return True
            
        except Exception as e:
            logger.error(f"Failed to optimize message delivery: {e}")
            return False
    
    def optimize_database_queries(self) -> Dict[str, Any]:
        """Optimize database queries for notification persistence"""
        try:
            optimization_results = {
                'queries_optimized': 0,
                'performance_improvement': 0,
                'cache_efficiency': 0
            }
            
            # Batch database operations
            if hasattr(self.persistence_manager, '_batch_operations'):
                batch_count = self.persistence_manager._batch_operations()
                optimization_results['queries_optimized'] = batch_count
            
            # Optimize query patterns
            stats = self.persistence_manager.get_delivery_stats()
            if 'database_stats' in stats:
                # Calculate cache efficiency
                total_requests = self._optimization_stats['messages_optimized']
                cache_hits = self._optimization_stats['cache_hits']
                if total_requests > 0:
                    optimization_results['cache_efficiency'] = cache_hits / total_requests
            
            return optimization_results
            
        except Exception as e:
            logger.error(f"Failed to optimize database queries: {e}")
            return {'error': str(e)}
    
    def optimize_websocket_connections(self) -> Dict[str, Any]:
        """Optimize WebSocket connection management"""
        try:
            optimization_results = {
                'connections_optimized': 0,
                'memory_saved_mb': 0,
                'connection_pool_status': ConnectionPoolStatus.HEALTHY.value
            }
            
            # Get current connection stats
            if hasattr(self.message_router, 'namespace_manager'):
                ns_manager = self.message_router.namespace_manager
                
                # Count active connections
                active_connections = len(getattr(ns_manager, '_connections', {}))
                user_connections = len(getattr(ns_manager, '_user_connections', {}))
                
                # Determine pool status
                if active_connections > 1000:
                    optimization_results['connection_pool_status'] = ConnectionPoolStatus.OVERLOADED.value
                elif active_connections > 500:
                    optimization_results['connection_pool_status'] = ConnectionPoolStatus.DEGRADED.value
                
                optimization_results['connections_optimized'] = active_connections
            
            # Memory optimization for connections
            memory_stats = self.memory_manager.check_memory_usage()
            if memory_stats['gc_threshold_reached']:
                cleanup_stats = self.memory_manager.cleanup_memory()
                optimization_results['memory_saved_mb'] = cleanup_stats.get('objects_collected', 0) * 0.001  # Estimate
                self._optimization_stats['memory_cleanups'] += 1
            
            return optimization_results
            
        except Exception as e:
            logger.error(f"Failed to optimize WebSocket connections: {e}")
            return {'error': str(e)}
    
    def get_performance_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics"""
        try:
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            cpu_percent = process.cpu_percent()
            
            # Get component stats
            cache_stats = self.cache.get_stats()
            throttle_stats = self.throttler.get_throttle_stats()
            batch_stats = self.batcher.get_stats()
            
            # Calculate throughput
            current_time = datetime.now(timezone.utc)
            recent_metrics = [m for m in self._metrics_history 
                            if (current_time - m.timestamp).total_seconds() <= 60]
            
            if len(recent_metrics) >= 2:
                time_diff = (recent_metrics[-1].timestamp - recent_metrics[0].timestamp).total_seconds()
                message_diff = recent_metrics[-1].message_throughput - recent_metrics[0].message_throughput
                throughput = message_diff / time_diff if time_diff > 0 else 0
            else:
                throughput = 0
            
            metrics = PerformanceMetrics(
                timestamp=current_time,
                websocket_connections=len(getattr(self.message_router.namespace_manager, '_connections', {})),
                active_sessions=len(getattr(self.message_router.namespace_manager, '_user_connections', {})),
                message_throughput=throughput,
                memory_usage_mb=memory_info.rss / 1024 / 1024,
                cpu_usage_percent=cpu_percent,
                database_query_time_ms=0,  # Would need database timing
                cache_hit_rate=cache_stats.get('hit_rate', 0),
                batch_efficiency=batch_stats.get('pending_messages', 0) / max(batch_stats.get('pending_batches', 1), 1),
                throttle_rate=throttle_stats.get('current_global_rate', 0) / throttle_stats.get('max_global_rate', 1)
            )
            
            self._metrics_history.append(metrics)
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get performance metrics: {e}")
            return PerformanceMetrics(
                timestamp=datetime.now(timezone.utc),
                websocket_connections=0, active_sessions=0, message_throughput=0,
                memory_usage_mb=0, cpu_usage_percent=0, database_query_time_ms=0,
                cache_hit_rate=0, batch_efficiency=0, throttle_rate=0
            )
    
    def get_optimization_report(self) -> Dict[str, Any]:
        """Get comprehensive optimization report"""
        try:
            current_metrics = self.get_performance_metrics()
            
            return {
                'optimization_level': self.optimization_level.value,
                'current_metrics': current_metrics.to_dict(),
                'optimization_stats': self._optimization_stats.copy(),
                'component_stats': {
                    'cache': self.cache.get_stats(),
                    'throttler': self.throttler.get_throttle_stats(),
                    'batcher': self.batcher.get_stats(),
                    'memory_manager': self.memory_manager.check_memory_usage()
                },
                'recommendations': self._generate_recommendations(current_metrics),
                'configuration': {
                    'batch_config': {
                        'max_batch_size': self.batch_config.max_batch_size,
                        'batch_timeout_ms': self.batch_config.batch_timeout_ms,
                        'compression_enabled': self.batch_config.compression_enabled
                    },
                    'throttle_config': {
                        'max_messages_per_second': self.throttle_config.max_messages_per_second,
                        'burst_capacity': self.throttle_config.burst_capacity,
                        'user_rate_limit': self.throttle_config.user_rate_limit
                    },
                    'cache_config': {
                        'max_cache_size': self.cache_config.max_cache_size,
                        'ttl_seconds': self.cache_config.ttl_seconds,
                        'compression_enabled': self.cache_config.compression_enabled
                    },
                    'memory_config': {
                        'max_memory_mb': self.memory_config.max_memory_mb,
                        'gc_threshold': self.memory_config.gc_threshold,
                        'object_pooling': self.memory_config.object_pooling
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to generate optimization report: {e}")
            return {'error': str(e)}
    
    def adjust_optimization_level(self, new_level: OptimizationLevel) -> bool:
        """Adjust optimization level and reconfigure components"""
        try:
            self.optimization_level = new_level
            self._init_configurations()
            
            # Reconfigure components
            self.cache.config = self.cache_config
            self.batcher.config = self.batch_config
            self.throttler.config = self.throttle_config
            self.memory_manager.config = self.memory_config
            
            logger.info(f"Adjusted optimization level to {new_level.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to adjust optimization level: {e}")
            return False
    
    def _init_configurations(self) -> None:
        """Initialize configurations based on optimization level"""
        if self.optimization_level == OptimizationLevel.CONSERVATIVE:
            self.batch_config = BatchConfiguration(
                max_batch_size=10, batch_timeout_ms=200, compression_enabled=False
            )
            self.throttle_config = ThrottleConfiguration(
                max_messages_per_second=50, burst_capacity=100, user_rate_limit=5
            )
            self.cache_config = CacheConfiguration(
                max_cache_size=1000, ttl_seconds=1800, compression_enabled=False
            )
            self.memory_config = MemoryConfiguration(
                max_memory_mb=256, gc_threshold=0.9, object_pooling=False
            )
        
        elif self.optimization_level == OptimizationLevel.BALANCED:
            self.batch_config = BatchConfiguration(
                max_batch_size=25, batch_timeout_ms=100, compression_enabled=True
            )
            self.throttle_config = ThrottleConfiguration(
                max_messages_per_second=100, burst_capacity=200, user_rate_limit=10
            )
            self.cache_config = CacheConfiguration(
                max_cache_size=5000, ttl_seconds=3600, compression_enabled=True
            )
            self.memory_config = MemoryConfiguration(
                max_memory_mb=512, gc_threshold=0.8, object_pooling=True
            )
        
        elif self.optimization_level == OptimizationLevel.AGGRESSIVE:
            self.batch_config = BatchConfiguration(
                max_batch_size=50, batch_timeout_ms=50, compression_enabled=True
            )
            self.throttle_config = ThrottleConfiguration(
                max_messages_per_second=200, burst_capacity=400, user_rate_limit=20
            )
            self.cache_config = CacheConfiguration(
                max_cache_size=10000, ttl_seconds=7200, compression_enabled=True
            )
            self.memory_config = MemoryConfiguration(
                max_memory_mb=1024, gc_threshold=0.7, object_pooling=True
            )
        
        else:  # MAXIMUM
            self.batch_config = BatchConfiguration(
                max_batch_size=100, batch_timeout_ms=25, compression_enabled=True
            )
            self.throttle_config = ThrottleConfiguration(
                max_messages_per_second=500, burst_capacity=1000, user_rate_limit=50
            )
            self.cache_config = CacheConfiguration(
                max_cache_size=20000, ttl_seconds=14400, compression_enabled=True
            )
            self.memory_config = MemoryConfiguration(
                max_memory_mb=2048, gc_threshold=0.6, object_pooling=True
            )
    
    def _generate_recommendations(self, metrics: PerformanceMetrics) -> List[str]:
        """Generate performance optimization recommendations"""
        recommendations = []
        
        # Memory recommendations
        if metrics.memory_usage_mb > self.memory_config.max_memory_mb * 0.8:
            recommendations.append("Consider increasing memory limit or enabling more aggressive garbage collection")
        
        # Throughput recommendations
        if metrics.message_throughput > self.throttle_config.max_messages_per_second * 0.8:
            recommendations.append("Consider increasing throttle limits or enabling more aggressive batching")
        
        # Cache recommendations
        if metrics.cache_hit_rate < 0.7:
            recommendations.append("Consider increasing cache size or TTL to improve hit rate")
        
        # Connection recommendations
        if metrics.websocket_connections > 500:
            recommendations.append("Consider implementing connection pooling or load balancing")
        
        # Batch recommendations
        if metrics.batch_efficiency < 0.5:
            recommendations.append("Consider adjusting batch size or timeout for better efficiency")
        
        return recommendations
    
    def _start_monitoring(self) -> None:
        """Start performance monitoring"""
        if not self._monitoring_enabled:
            return
        
        def monitor():
            try:
                metrics = self.get_performance_metrics()
                # Log metrics periodically
                if len(self._metrics_history) % 10 == 0:  # Every 10 collections
                    logger.info(f"Performance metrics: throughput={metrics.message_throughput:.2f} msg/s, "
                              f"memory={metrics.memory_usage_mb:.1f}MB, cache_hit_rate={metrics.cache_hit_rate:.2f}")
            except Exception as e:
                logger.error(f"Performance monitoring error: {e}")
            
            # Schedule next monitoring
            if self._monitoring_enabled:
                threading.Timer(self._monitoring_interval, monitor).start()
        
        # Start monitoring
        threading.Timer(self._monitoring_interval, monitor).start()
    
    def stop_monitoring(self) -> None:
        """Stop performance monitoring"""
        self._monitoring_enabled = False
    
    def flush_all_optimizations(self) -> Dict[str, int]:
        """Flush all pending optimizations"""
        try:
            results = {
                'batches_flushed': self.batcher.flush_all_batches(),
                'cache_entries_cleared': len(self.cache._cache),
                'memory_cleaned': 0
            }
            
            # Clear cache
            self.cache._cache.clear()
            self.cache._user_caches.clear()
            
            # Clean memory
            cleanup_stats = self.memory_manager.cleanup_memory()
            results['memory_cleaned'] = cleanup_stats.get('objects_collected', 0)
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to flush optimizations: {e}")
            return {'error': str(e)}
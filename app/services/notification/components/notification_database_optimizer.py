# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Notification Database Optimizer

This module provides advanced database query optimization for notification persistence,
including query batching, connection pooling optimization, index management,
and query performance monitoring.
"""

import logging
import time
import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum
import json
from contextlib import contextmanager

from sqlalchemy import text, func, and_, or_, desc, asc
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from sqlalchemy.engine import Engine

from app.core.database.core.database_manager import DatabaseManager
from models import NotificationStorage, NotificationType, NotificationPriority, NotificationCategory

logger = logging.getLogger(__name__)


class QueryType(Enum):
    """Database query types"""
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"
    SELECT = "select"
    BATCH_INSERT = "batch_insert"
    BATCH_UPDATE = "batch_update"
    BATCH_DELETE = "batch_delete"


class OptimizationStrategy(Enum):
    """Query optimization strategies"""
    BATCHING = "batching"
    CACHING = "caching"
    INDEXING = "indexing"
    PARTITIONING = "partitioning"
    CONNECTION_POOLING = "connection_pooling"


@dataclass
class QueryMetrics:
    """Query performance metrics"""
    query_type: QueryType
    execution_time_ms: float
    rows_affected: int
    timestamp: datetime
    query_hash: str
    optimization_applied: List[OptimizationStrategy] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'query_type': self.query_type.value,
            'execution_time_ms': self.execution_time_ms,
            'rows_affected': self.rows_affected,
            'timestamp': self.timestamp.isoformat(),
            'query_hash': self.query_hash,
            'optimization_applied': [opt.value for opt in self.optimization_applied]
        }


@dataclass
class BatchOperation:
    """Batch database operation"""
    operation_type: QueryType
    data: List[Dict[str, Any]]
    timestamp: datetime
    max_batch_size: int = 100
    timeout_seconds: int = 5
    
    def is_ready(self) -> bool:
        """Check if batch is ready for execution"""
        return (len(self.data) >= self.max_batch_size or 
                (datetime.now(timezone.utc) - self.timestamp).total_seconds() >= self.timeout_seconds)


@dataclass
class DatabaseOptimizationConfig:
    """Database optimization configuration"""
    enable_query_batching: bool = True
    enable_query_caching: bool = True
    enable_connection_pooling: bool = True
    enable_performance_monitoring: bool = True
    
    # Batching configuration
    max_batch_size: int = 100
    batch_timeout_seconds: int = 5
    max_concurrent_batches: int = 5
    
    # Caching configuration
    query_cache_size: int = 1000
    query_cache_ttl_seconds: int = 300
    result_cache_size: int = 500
    result_cache_ttl_seconds: int = 60
    
    # Connection pooling configuration
    pool_size: int = 20
    max_overflow: int = 30
    pool_timeout: int = 30
    pool_recycle: int = 3600
    
    # Performance monitoring
    slow_query_threshold_ms: float = 1000.0
    monitor_interval_seconds: int = 60
    keep_metrics_days: int = 7


class QueryCache:
    """High-performance query result cache"""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 300):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache = {}  # query_hash -> (result, timestamp)
        self._access_order = deque()  # for LRU eviction
        self._lock = threading.RLock()
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'size': 0
        }
    
    def get(self, query_hash: str) -> Optional[Any]:
        """Get cached query result"""
        with self._lock:
            if query_hash in self._cache:
                result, timestamp = self._cache[query_hash]
                
                # Check TTL
                if (datetime.now(timezone.utc) - timestamp).total_seconds() <= self.ttl_seconds:
                    # Update access order
                    try:
                        self._access_order.remove(query_hash)
                    except ValueError:
                        pass
                    self._access_order.append(query_hash)
                    
                    self._stats['hits'] += 1
                    return result
                else:
                    # Expired
                    del self._cache[query_hash]
                    self._stats['evictions'] += 1
            
            self._stats['misses'] += 1
            return None
    
    def put(self, query_hash: str, result: Any) -> None:
        """Cache query result"""
        with self._lock:
            # Evict if cache is full
            while len(self._cache) >= self.max_size:
                if self._access_order:
                    oldest = self._access_order.popleft()
                    self._cache.pop(oldest, None)
                    self._stats['evictions'] += 1
                else:
                    break
            
            # Add new result
            self._cache[query_hash] = (result, datetime.now(timezone.utc))
            self._access_order.append(query_hash)
            self._stats['size'] = len(self._cache)
    
    def invalidate(self, pattern: str = None) -> int:
        """Invalidate cache entries"""
        with self._lock:
            if pattern is None:
                # Clear all
                count = len(self._cache)
                self._cache.clear()
                self._access_order.clear()
                self._stats['size'] = 0
                return count
            else:
                # Clear matching pattern
                keys_to_remove = [k for k in self._cache.keys() if pattern in k]
                for key in keys_to_remove:
                    del self._cache[key]
                    try:
                        self._access_order.remove(key)
                    except ValueError:
                        pass
                
                self._stats['size'] = len(self._cache)
                return len(keys_to_remove)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            total_requests = self._stats['hits'] + self._stats['misses']
            hit_rate = self._stats['hits'] / total_requests if total_requests > 0 else 0
            
            return {
                'hit_rate': hit_rate,
                'size': self._stats['size'],
                'max_size': self.max_size,
                'stats': self._stats.copy()
            }


class BatchProcessor:
    """Database batch operation processor"""
    
    def __init__(self, db_manager: DatabaseManager, config: DatabaseOptimizationConfig):
        self.db_manager = db_manager
        self.config = config
        
        # Batch queues
        self._batch_queues = defaultdict(lambda: BatchOperation(
            operation_type=QueryType.INSERT,
            data=[],
            timestamp=datetime.now(timezone.utc),
            max_batch_size=config.max_batch_size,
            timeout_seconds=config.batch_timeout_seconds
        ))
        
        # Processing state
        self._processing_lock = threading.RLock()
        self._batch_timers = {}  # operation_key -> timer
        self._stats = {
            'batches_processed': 0,
            'operations_batched': 0,
            'batch_efficiency': 0.0,
            'processing_errors': 0
        }
        
        # Background processing
        self._executor = None
        if config.max_concurrent_batches > 0:
            from concurrent.futures import ThreadPoolExecutor
            self._executor = ThreadPoolExecutor(max_workers=config.max_concurrent_batches)
    
    def add_operation(self, operation_type: QueryType, data: Dict[str, Any]) -> None:
        """Add operation to batch queue"""
        if not self.config.enable_query_batching:
            # Execute immediately
            self._execute_single_operation(operation_type, data)
            return
        
        operation_key = f"{operation_type.value}_{self._get_operation_key(data)}"
        
        with self._processing_lock:
            batch = self._batch_queues[operation_key]
            batch.data.append(data)
            self._stats['operations_batched'] += 1
            
            # Check if batch is ready
            if batch.is_ready():
                self._process_batch(operation_key)
            else:
                # Set timer if not already set
                if operation_key not in self._batch_timers:
                    timer = threading.Timer(
                        batch.timeout_seconds,
                        self._process_batch,
                        args=[operation_key]
                    )
                    timer.start()
                    self._batch_timers[operation_key] = timer
    
    def flush_all_batches(self) -> int:
        """Flush all pending batches"""
        with self._processing_lock:
            batch_count = 0
            for operation_key in list(self._batch_queues.keys()):
                if self._batch_queues[operation_key].data:
                    self._process_batch(operation_key)
                    batch_count += 1
            return batch_count
    
    def get_batch_stats(self) -> Dict[str, Any]:
        """Get batch processing statistics"""
        with self._processing_lock:
            pending_operations = sum(len(batch.data) for batch in self._batch_queues.values())
            pending_batches = len([b for b in self._batch_queues.values() if b.data])
            
            return {
                'pending_batches': pending_batches,
                'pending_operations': pending_operations,
                'stats': self._stats.copy()
            }
    
    def _process_batch(self, operation_key: str) -> None:
        """Process batch operation"""
        with self._processing_lock:
            batch = self._batch_queues.get(operation_key)
            if not batch or not batch.data:
                return
            
            # Clear batch and timer
            data_to_process = batch.data.copy()
            batch.data.clear()
            batch.timestamp = datetime.now(timezone.utc)
            
            timer = self._batch_timers.pop(operation_key, None)
            if timer:
                timer.cancel()
        
        # Process batch (outside lock)
        if self._executor:
            self._executor.submit(self._execute_batch_operation, batch.operation_type, data_to_process)
        else:
            self._execute_batch_operation(batch.operation_type, data_to_process)
    
    def _execute_batch_operation(self, operation_type: QueryType, data: List[Dict[str, Any]]) -> None:
        """Execute batch operation"""
        try:
            start_time = time.time()
            
            with self.db_manager.get_session() as session:
                if operation_type == QueryType.BATCH_INSERT:
                    self._execute_batch_insert(session, data)
                elif operation_type == QueryType.BATCH_UPDATE:
                    self._execute_batch_update(session, data)
                elif operation_type == QueryType.BATCH_DELETE:
                    self._execute_batch_delete(session, data)
                
                session.commit()
            
            execution_time = (time.time() - start_time) * 1000
            
            # Update statistics
            with self._processing_lock:
                self._stats['batches_processed'] += 1
                self._stats['batch_efficiency'] = len(data) / max(execution_time / 1000, 0.001)
            
            logger.debug(f"Processed batch of {len(data)} {operation_type.value} operations in {execution_time:.2f}ms")
            
        except Exception as e:
            logger.error(f"Batch operation failed: {e}")
            with self._processing_lock:
                self._stats['processing_errors'] += 1
    
    def _execute_single_operation(self, operation_type: QueryType, data: Dict[str, Any]) -> None:
        """Execute single operation immediately"""
        try:
            with self.db_manager.get_session() as session:
                if operation_type == QueryType.INSERT:
                    notification = NotificationStorage(**data)
                    session.add(notification)
                elif operation_type == QueryType.UPDATE:
                    session.query(NotificationStorage).filter_by(id=data['id']).update(data)
                elif operation_type == QueryType.DELETE:
                    session.query(NotificationStorage).filter_by(id=data['id']).delete()
                
                session.commit()
                
        except Exception as e:
            logger.error(f"Single operation failed: {e}")
    
    def _execute_batch_insert(self, session, data: List[Dict[str, Any]]) -> None:
        """Execute batch insert operation"""
        notifications = [NotificationStorage(**item) for item in data]
        session.bulk_save_objects(notifications)
    
    def _execute_batch_update(self, session, data: List[Dict[str, Any]]) -> None:
        """Execute batch update operation"""
        for item in data:
            session.query(NotificationStorage).filter_by(id=item['id']).update(
                {k: v for k, v in item.items() if k != 'id'}
            )
    
    def _execute_batch_delete(self, session, data: List[Dict[str, Any]]) -> None:
        """Execute batch delete operation"""
        ids = [item['id'] for item in data if 'id' in item]
        if ids:
            session.query(NotificationStorage).filter(NotificationStorage.id.in_(ids)).delete(synchronize_session=False)
    
    def _get_operation_key(self, data: Dict[str, Any]) -> str:
        """Generate operation key for batching similar operations"""
        # Group by user_id and category for better batching
        user_id = data.get('user_id', 'none')
        category = data.get('category', 'default')
        return f"{user_id}_{category}"
    
    def shutdown(self) -> None:
        """Shutdown batch processor"""
        # Flush all pending batches
        self.flush_all_batches()
        
        # Shutdown executor
        if self._executor:
            self._executor.shutdown(wait=True)
        
        # Cancel all timers
        with self._processing_lock:
            for timer in self._batch_timers.values():
                timer.cancel()
            self._batch_timers.clear()


class QueryPerformanceMonitor:
    """Database query performance monitoring"""
    
    def __init__(self, config: DatabaseOptimizationConfig):
        self.config = config
        self._metrics = deque(maxlen=10000)  # Keep last 10k queries
        self._slow_queries = deque(maxlen=1000)  # Keep last 1k slow queries
        self._lock = threading.RLock()
        
        # Aggregated statistics
        self._stats = {
            'total_queries': 0,
            'slow_queries': 0,
            'average_execution_time': 0.0,
            'queries_by_type': defaultdict(int),
            'optimization_impact': defaultdict(float)
        }
        
        # Monitoring timer
        self._monitoring_timer = None
        if config.enable_performance_monitoring:
            self._start_monitoring()
    
    def record_query(self, query_type: QueryType, execution_time_ms: float, 
                    rows_affected: int, query_hash: str, 
                    optimizations: List[OptimizationStrategy] = None) -> None:
        """Record query execution metrics"""
        if not self.config.enable_performance_monitoring:
            return
        
        metrics = QueryMetrics(
            query_type=query_type,
            execution_time_ms=execution_time_ms,
            rows_affected=rows_affected,
            timestamp=datetime.now(timezone.utc),
            query_hash=query_hash,
            optimization_applied=optimizations or []
        )
        
        with self._lock:
            self._metrics.append(metrics)
            
            # Update statistics
            self._stats['total_queries'] += 1
            self._stats['queries_by_type'][query_type.value] += 1
            
            # Update average execution time
            total_time = sum(m.execution_time_ms for m in self._metrics)
            self._stats['average_execution_time'] = total_time / len(self._metrics)
            
            # Track slow queries
            if execution_time_ms >= self.config.slow_query_threshold_ms:
                self._slow_queries.append(metrics)
                self._stats['slow_queries'] += 1
            
            # Track optimization impact
            for opt in (optimizations or []):
                self._stats['optimization_impact'][opt.value] += execution_time_ms
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report"""
        with self._lock:
            current_time = datetime.now(timezone.utc)
            
            # Calculate recent performance (last hour)
            hour_ago = current_time - timedelta(hours=1)
            recent_metrics = [m for m in self._metrics if m.timestamp >= hour_ago]
            
            recent_stats = {
                'query_count': len(recent_metrics),
                'average_execution_time': 0.0,
                'slow_query_count': 0,
                'queries_by_type': defaultdict(int)
            }
            
            if recent_metrics:
                recent_stats['average_execution_time'] = sum(m.execution_time_ms for m in recent_metrics) / len(recent_metrics)
                recent_stats['slow_query_count'] = len([m for m in recent_metrics if m.execution_time_ms >= self.config.slow_query_threshold_ms])
                
                for metrics in recent_metrics:
                    recent_stats['queries_by_type'][metrics.query_type.value] += 1
            
            # Top slow queries
            slow_query_summary = []
            for metrics in list(self._slow_queries)[-10:]:  # Last 10 slow queries
                slow_query_summary.append({
                    'query_type': metrics.query_type.value,
                    'execution_time_ms': metrics.execution_time_ms,
                    'rows_affected': metrics.rows_affected,
                    'timestamp': metrics.timestamp.isoformat(),
                    'optimizations': [opt.value for opt in metrics.optimization_applied]
                })
            
            return {
                'timestamp': current_time.isoformat(),
                'overall_stats': self._stats.copy(),
                'recent_performance': dict(recent_stats),
                'slow_queries': slow_query_summary,
                'performance_trends': self._calculate_performance_trends(),
                'optimization_recommendations': self._generate_optimization_recommendations()
            }
    
    def _calculate_performance_trends(self) -> Dict[str, Any]:
        """Calculate performance trends"""
        if len(self._metrics) < 100:
            return {'insufficient_data': True}
        
        # Split metrics into time buckets
        current_time = datetime.now(timezone.utc)
        hour_ago = current_time - timedelta(hours=1)
        day_ago = current_time - timedelta(days=1)
        
        recent_hour = [m for m in self._metrics if m.timestamp >= hour_ago]
        recent_day = [m for m in self._metrics if m.timestamp >= day_ago]
        
        trends = {}
        
        # Execution time trend
        if recent_hour and recent_day:
            hour_avg = sum(m.execution_time_ms for m in recent_hour) / len(recent_hour)
            day_avg = sum(m.execution_time_ms for m in recent_day) / len(recent_day)
            trends['execution_time_trend'] = ((hour_avg - day_avg) / day_avg) * 100 if day_avg > 0 else 0
        
        # Query volume trend
        hour_count = len(recent_hour)
        day_count = len(recent_day)
        if day_count > 0:
            trends['query_volume_trend'] = ((hour_count * 24 - day_count) / day_count) * 100
        
        return trends
    
    def _generate_optimization_recommendations(self) -> List[str]:
        """Generate optimization recommendations based on performance data"""
        recommendations = []
        
        # Check slow query ratio
        if self._stats['total_queries'] > 0:
            slow_ratio = self._stats['slow_queries'] / self._stats['total_queries']
            if slow_ratio > 0.1:  # More than 10% slow queries
                recommendations.append("High percentage of slow queries detected - consider query optimization")
        
        # Check average execution time
        if self._stats['average_execution_time'] > self.config.slow_query_threshold_ms / 2:
            recommendations.append("Average query execution time is high - consider database indexing")
        
        # Check query type distribution
        query_types = self._stats['queries_by_type']
        total_queries = sum(query_types.values())
        
        if total_queries > 0:
            select_ratio = query_types.get('select', 0) / total_queries
            if select_ratio > 0.8:
                recommendations.append("High SELECT query ratio - consider implementing query caching")
            
            insert_ratio = query_types.get('insert', 0) / total_queries
            if insert_ratio > 0.3:
                recommendations.append("High INSERT query ratio - consider batch operations")
        
        return recommendations
    
    def _start_monitoring(self) -> None:
        """Start performance monitoring timer"""
        if self._monitoring_timer:
            self._monitoring_timer.cancel()
        
        self._monitoring_timer = threading.Timer(
            self.config.monitor_interval_seconds,
            self._periodic_monitoring
        )
        self._monitoring_timer.daemon = True
        self._monitoring_timer.start()
    
    def _periodic_monitoring(self) -> None:
        """Periodic monitoring task"""
        try:
            # Clean old metrics
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=self.config.keep_metrics_days)
            
            with self._lock:
                # Remove old metrics
                while self._metrics and self._metrics[0].timestamp < cutoff_time:
                    self._metrics.popleft()
                
                while self._slow_queries and self._slow_queries[0].timestamp < cutoff_time:
                    self._slow_queries.popleft()
            
            # Log performance summary
            if self._stats['total_queries'] > 0:
                logger.info(f"Query performance: {self._stats['total_queries']} total queries, "
                          f"{self._stats['average_execution_time']:.2f}ms avg, "
                          f"{self._stats['slow_queries']} slow queries")
        
        except Exception as e:
            logger.error(f"Performance monitoring error: {e}")
        finally:
            self._start_monitoring()
    
    def shutdown(self) -> None:
        """Shutdown performance monitor"""
        if self._monitoring_timer:
            self._monitoring_timer.cancel()


class NotificationDatabaseOptimizer:
    """Main database optimizer for notification system"""
    
    def __init__(self, db_manager: DatabaseManager, 
                 config: Optional[DatabaseOptimizationConfig] = None):
        self.db_manager = db_manager
        self.config = config or DatabaseOptimizationConfig()
        
        # Initialize optimization components
        self.query_cache = QueryCache(
            max_size=self.config.query_cache_size,
            ttl_seconds=self.config.query_cache_ttl_seconds
        ) if self.config.enable_query_caching else None
        
        self.batch_processor = BatchProcessor(
            db_manager, self.config
        ) if self.config.enable_query_batching else None
        
        self.performance_monitor = QueryPerformanceMonitor(
            self.config
        ) if self.config.enable_performance_monitoring else None
        
        # Optimization statistics
        self._optimization_stats = {
            'queries_optimized': 0,
            'cache_hits': 0,
            'batches_processed': 0,
            'performance_improvements': 0
        }
        
        logger.info("Notification Database Optimizer initialized")
    
    def optimize_notification_storage(self, notification_data: Dict[str, Any]) -> bool:
        """Optimize notification storage operation"""
        try:
            start_time = time.time()
            
            # Use batch processing if available
            if self.batch_processor:
                self.batch_processor.add_operation(QueryType.INSERT, notification_data)
                success = True
            else:
                # Direct storage
                with self.db_manager.get_session() as session:
                    notification = NotificationStorage(**notification_data)
                    session.add(notification)
                    session.commit()
                    success = True
            
            # Record performance metrics
            execution_time = (time.time() - start_time) * 1000
            if self.performance_monitor:
                query_hash = self._generate_query_hash('insert_notification', notification_data)
                optimizations = [OptimizationStrategy.BATCHING] if self.batch_processor else []
                self.performance_monitor.record_query(
                    QueryType.INSERT, execution_time, 1, query_hash, optimizations
                )
            
            self._optimization_stats['queries_optimized'] += 1
            return success
            
        except Exception as e:
            logger.error(f"Failed to optimize notification storage: {e}")
            return False
    
    def optimize_notification_retrieval(self, user_id: int, limit: int = 50, 
                                      include_read: bool = True) -> List[Dict[str, Any]]:
        """Optimize notification retrieval with caching"""
        try:
            start_time = time.time()
            
            # Generate cache key
            cache_key = f"notifications_{user_id}_{limit}_{include_read}"
            query_hash = self._generate_query_hash('select_notifications', {
                'user_id': user_id, 'limit': limit, 'include_read': include_read
            })
            
            # Check cache first
            if self.query_cache:
                cached_result = self.query_cache.get(query_hash)
                if cached_result is not None:
                    self._optimization_stats['cache_hits'] += 1
                    return cached_result
            
            # Execute optimized query
            with self.db_manager.get_session() as session:
                query = session.query(NotificationStorage).filter_by(user_id=user_id)
                
                if not include_read:
                    query = query.filter_by(read=False)
                
                # Use optimized ordering and limiting
                notifications = query.order_by(desc(NotificationStorage.timestamp))\
                    .limit(limit)\
                    .all()
                
                # Convert to dictionaries
                result = [notif.to_notification_message().to_dict() for notif in notifications]
            
            # Cache result
            if self.query_cache:
                self.query_cache.put(query_hash, result)
            
            # Record performance metrics
            execution_time = (time.time() - start_time) * 1000
            if self.performance_monitor:
                optimizations = []
                if self.query_cache:
                    optimizations.append(OptimizationStrategy.CACHING)
                
                self.performance_monitor.record_query(
                    QueryType.SELECT, execution_time, len(result), query_hash, optimizations
                )
            
            self._optimization_stats['queries_optimized'] += 1
            return result
            
        except Exception as e:
            logger.error(f"Failed to optimize notification retrieval: {e}")
            return []
    
    def optimize_notification_cleanup(self, retention_days: int = 30) -> int:
        """Optimize notification cleanup with batching"""
        try:
            start_time = time.time()
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
            
            # Use batch processing for large deletions
            if self.batch_processor:
                # Get IDs to delete in batches
                with self.db_manager.get_session() as session:
                    old_notifications = session.query(NotificationStorage.id)\
                        .filter(NotificationStorage.created_at < cutoff_date)\
                        .limit(1000)\
                        .all()
                    
                    # Add to batch processor
                    for notification in old_notifications:
                        self.batch_processor.add_operation(
                            QueryType.DELETE, 
                            {'id': notification.id}
                        )
                    
                    cleanup_count = len(old_notifications)
            else:
                # Direct deletion
                with self.db_manager.get_session() as session:
                    cleanup_count = session.query(NotificationStorage)\
                        .filter(NotificationStorage.created_at < cutoff_date)\
                        .delete()
                    session.commit()
            
            # Invalidate related cache entries
            if self.query_cache:
                self.query_cache.invalidate('notifications_')
            
            # Record performance metrics
            execution_time = (time.time() - start_time) * 1000
            if self.performance_monitor:
                query_hash = self._generate_query_hash('cleanup_notifications', {'retention_days': retention_days})
                optimizations = [OptimizationStrategy.BATCHING] if self.batch_processor else []
                self.performance_monitor.record_query(
                    QueryType.DELETE, execution_time, cleanup_count, query_hash, optimizations
                )
            
            self._optimization_stats['queries_optimized'] += 1
            return cleanup_count
            
        except Exception as e:
            logger.error(f"Failed to optimize notification cleanup: {e}")
            return 0
    
    def optimize_batch_operations(self) -> Dict[str, Any]:
        """Optimize pending batch operations"""
        try:
            if not self.batch_processor:
                return {'error': 'Batch processing not enabled'}
            
            # Flush all pending batches
            batches_processed = self.batch_processor.flush_all_batches()
            
            # Get batch statistics
            batch_stats = self.batch_processor.get_batch_stats()
            
            self._optimization_stats['batches_processed'] += batches_processed
            
            return {
                'batches_processed': batches_processed,
                'batch_stats': batch_stats,
                'optimization_impact': 'Improved throughput through batch processing'
            }
            
        except Exception as e:
            logger.error(f"Failed to optimize batch operations: {e}")
            return {'error': str(e)}
    
    def get_optimization_report(self) -> Dict[str, Any]:
        """Get comprehensive database optimization report"""
        try:
            report = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'optimization_stats': self._optimization_stats.copy(),
                'configuration': {
                    'query_batching_enabled': self.config.enable_query_batching,
                    'query_caching_enabled': self.config.enable_query_caching,
                    'performance_monitoring_enabled': self.config.enable_performance_monitoring,
                    'max_batch_size': self.config.max_batch_size,
                    'cache_size': self.config.query_cache_size
                }
            }
            
            # Add cache statistics
            if self.query_cache:
                report['cache_stats'] = self.query_cache.get_stats()
            
            # Add batch processing statistics
            if self.batch_processor:
                report['batch_stats'] = self.batch_processor.get_batch_stats()
            
            # Add performance monitoring report
            if self.performance_monitor:
                report['performance_report'] = self.performance_monitor.get_performance_report()
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate optimization report: {e}")
            return {'error': str(e)}
    
    def _generate_query_hash(self, operation: str, params: Dict[str, Any]) -> str:
        """Generate hash for query caching"""
        import hashlib
        
        # Create consistent string representation
        param_str = json.dumps(params, sort_keys=True, default=str)
        query_string = f"{operation}:{param_str}"
        
        return hashlib.md5(query_string.encode()).hexdigest()
    
    def shutdown(self) -> None:
        """Shutdown database optimizer"""
        if self.batch_processor:
            self.batch_processor.shutdown()
        
        if self.performance_monitor:
            self.performance_monitor.shutdown()
        
        logger.info("Notification Database Optimizer shutdown complete")